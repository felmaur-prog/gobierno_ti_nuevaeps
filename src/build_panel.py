"""Integración del panel: PQRD (F1), giro directo (F2), afiliados (F3) y REPS (F4).

Produce en data/processed:
  * panel_eps_mes.csv    : EPS x régimen x mes (2022-01 a 2025-12 para PQRD; giro hasta 2026)
  * panel_depto_mes.csv  : Nueva EPS y EPS de comparación x departamento x régimen x mes
  * pqrd_motivos_neps.csv: PQRD de Nueva EPS por motivo general, riesgo y mes
  * catalogo_eps.csv     : códigos de EPS y agrupación usada

Uso:  python src/build_panel.py
"""
from __future__ import annotations
import csv, re, unicodedata
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW, PROC = BASE / "data" / "raw", BASE / "data" / "processed"
INICIO, FIN_PQRD = "2022-01", "2025-12"

# ----------------------------------------------------------------- catálogos
DEPTOS = {  # código DANE -> nombre normalizado
    "05": "ANTIOQUIA", "08": "ATLANTICO", "11": "BOGOTA", "13": "BOLIVAR", "15": "BOYACA", "17": "CALDAS", "18": "CAQUETA",
    "19": "CAUCA", "20": "CESAR", "23": "CORDOBA", "25": "CUNDINAMARCA", "27": "CHOCO", "41": "HUILA", "44": "LA GUAJIRA",
    "47": "MAGDALENA", "50": "META", "52": "NARINO", "54": "NORTE DE SANTANDER", "63": "QUINDIO", "66": "RISARALDA",
    "68": "SANTANDER", "70": "SUCRE", "73": "TOLIMA", "76": "VALLE DEL CAUCA", "81": "ARAUCA", "85": "CASANARE",
    "86": "PUTUMAYO", "88": "SAN ANDRES", "91": "AMAZONAS", "94": "GUAINIA", "95": "GUAVIARE", "97": "VAUPES", "99": "VICHADA",
}
ALIAS = {"VALLE": "76", "BOGOTA D C": "11", "BOGOTA DC": "11", "SAN ANDRES Y PROVIDENCIA": "88",
         "ARCHIPIELAGO DE SAN ANDRES": "88", "NARINO": "52", "GUAJIRA": "44", "N DE SANTANDER": "54", "NORTE SANTANDER": "54"}
NOMBRE_A_COD = {v: k for k, v in DEPTOS.items()}

# Agrupación de códigos de EPS a una sola entidad (contributivo, subsidiado y movilidad)
GRUPOS_EPS = {
    "NUEVA EPS": ["EPS037", "EPSS41", "EPS041"],
    "SANITAS": ["EPS005", "EPSS05", "EPS005"],
    "SURA": ["EPS010", "EPSS10"],
    "SALUD TOTAL": ["EPS002", "EPSS02"],
    "COMPENSAR": ["EPS008", "EPSS08"],
    "FAMISANAR": ["EPS017", "EPSS17"],
    "COOSALUD": ["ESS024", "ESSC24", "EPSC24"],
    "MUTUAL SER": ["ESS207", "ESSC07", "EPSC07"],
    "ASMET SALUD": ["ESS062", "ESSC62", "EPSC62"],
    "EMSSANAR": ["ESS118", "ESSC18", "EPSC18"],
    "SAVIA SALUD": ["EPSS40", "EPS040", "EPSC40"],
    "CAPITAL SALUD": ["EPSS34", "EPS034", "EPSC34"],
}
COD_A_GRUPO = {c: g for g, cs in GRUPOS_EPS.items() for c in cs}
# Intervenidas por Supersalud (fecha de inicio) para definir el grupo de comparación
INTERVENIDAS = {"NUEVA EPS": "2024-04", "SANITAS": "2024-04", "SAVIA SALUD": "2023-06", "ASMET SALUD": "2023-05",
                "EMSSANAR": "2022-11", "FAMISANAR": "2023-09", "COOSALUD": "2024-10", "CAPITAL SALUD": "2024-12"}
# Nota: verificar fechas de intervención en actos administrativos de Supersalud antes del Entregable 2.


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()
    s = s.strip('"').strip("'").strip()  # campos entrecomillados leídos sin interpretar comillas
    return re.sub(r"\s+", " ", s)


def depto_a_cod(nombre) -> str | None:
    n = norm(nombre)
    n = re.sub(r"[.,]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    if not n or len(n) < 3:  # evita que un campo vacío "coincida" con cualquier nombre
        return None
    if n in ALIAS:
        return ALIAS[n]
    if n in NOMBRE_A_COD:
        return NOMBRE_A_COD[n]
    for k, v in NOMBRE_A_COD.items():  # p. ej. "BOGOTA D C" contiene a "BOGOTA"; exige longitud mínima
        if len(n) >= 4 and (n.startswith(k) or k.startswith(n)):
            return v
    return None


def grupo_eps(cod: str, nombre: str = "") -> str:
    cod = str(cod).strip().upper()
    if cod in COD_A_GRUPO:
        return COD_A_GRUPO[cod]
    n = norm(nombre)
    for g in GRUPOS_EPS:
        if g in n:
            return g
    return n or cod


def periodo(anio, mes) -> pd.Series:
    """Devuelve 'YYYY-MM' a partir de año y mes (numérico o nombre en español)."""
    meses = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
             "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}
    m = pd.Series(mes).map(lambda x: meses.get(norm(x), x) if isinstance(x, str) else x)
    m = pd.to_numeric(m, errors="coerce")
    a = pd.to_numeric(pd.Series(anio), errors="coerce")
    return a.astype("Int64").astype(str) + "-" + m.astype("Int64").astype(str).str.zfill(2)


# ----------------------------------------------------------------- F1 PQRD
def cargar_pqrd() -> pd.DataFrame:
    df = pd.read_csv(PROC / "F1_pqrd_clean.csv", dtype={"cod_depto": str})
    df["periodo"] = periodo(df["anio"], df["mes"]).values
    df["eps"] = [grupo_eps(c, n) for c, n in zip(df["ent_cod_sns"], df["ent_nombre"])]
    return df


# ----------------------------------------------------------------- F4 REPS
def leer_csv_robusto(path: Path) -> pd.DataFrame:
    """Lee un CSV detectando el delimitador manualmente y sin dejar que comillas
    sueltas dentro de un campo (frecuentes en exportaciones del REPS) rompan el parser."""
    raw = path.read_bytes()[:300_000]
    texto, enc = None, "utf-8-sig"
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    primera = texto.splitlines()[0]
    sep = max([";", ",", "\t", "|"], key=primera.count)
    try:
        return pd.read_csv(path, sep=sep, dtype=str, encoding=enc, engine="python",
                            quoting=csv.QUOTE_MINIMAL, on_bad_lines="skip")
    except Exception:
        # Segundo intento: ignora las comillas por completo (QUOTE_NONE) en vez de
        # tratarlas como delimitadoras de texto; esto es lo que falla con comillas sueltas.
        return pd.read_csv(path, sep=sep, dtype=str, encoding=enc, engine="python",
                            quoting=csv.QUOTE_NONE, on_bad_lines="skip")


def _es_html(path: Path) -> bool:
    """El REPS se descarga a veces como .xls o .csv que en realidad es una tabla HTML."""
    ini = path.read_bytes()[:2000].lower()
    return b"<table" in ini or b"<html" in ini or ini.lstrip().startswith(b"<")


def _leer_reps_html(path: Path) -> pd.DataFrame:
    """Extrae departamento y NIT de una tabla HTML del REPS.

    Recorre el archivo por bloques y conserva solo las columnas necesarias, en vez de
    cargar toda la tabla en memoria: la exportación completa pesa decenas de megabytes.
    """
    fila_re = re.compile(rb"<tr[^>]*>(.*?)</tr>", re.I | re.S)
    celda_re = re.compile(rb"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
    etiqueta_re = re.compile(rb"<[^>]+>")

    def celdas(bloque):
        out = []
        for c in celda_re.findall(bloque):
            t = etiqueta_re.sub(b"", c).decode("latin-1", errors="replace")
            out.append(t.replace("&amp;", "&").replace("&nbsp;", " ").strip())
        return out

    i_dep = i_nit = None
    datos, resto = [], b""
    with path.open("rb") as fh:
        while True:
            trozo = fh.read(4 << 20)
            if not trozo:
                break
            resto += trozo
            filas = fila_re.findall(resto)
            corte = resto.rfind(b"</tr>")
            resto = resto[corte + 5:] if corte != -1 else resto
            for f in filas:
                vals = celdas(f)
                if i_dep is None:
                    bajos = [v.strip().lower() for v in vals]
                    if "depa_nombre" in bajos and "nits_nit" in bajos:
                        i_dep, i_nit = bajos.index("depa_nombre"), bajos.index("nits_nit")
                    continue
                if len(vals) > max(i_dep, i_nit):
                    datos.append((vals[i_dep], vals[i_nit]))
    if i_dep is None:
        return pd.DataFrame()
    return pd.DataFrame(datos, columns=["depa_nombre", "nits_nit"])


def _puntaje_reps(df: pd.DataFrame) -> tuple[float, str, str]:
    """Evalúa una lectura del REPS: devuelve (proporción de filas utilizables, col NIT, col departamento).

    Sirve para elegir entre varias formas de parsear el archivo: la lectura correcta
    produce departamentos reconocibles y NIT de longitud plausible; una lectura con las
    columnas desalineadas produce basura y puntúa cerca de cero.
    """
    cols = {c: norm(c) for c in df.columns}
    c_nit = "nits_nit" if "nits_nit" in df.columns else next((c for c, n in cols.items() if "NIT" in n and "DV" not in n), None)
    c_dep = "depa_nombre" if "depa_nombre" in df.columns else next((c for c, n in cols.items() if "DEPA" in n), None)
    if c_nit is None or c_dep is None or df.empty:
        return 0.0, c_nit, c_dep
    dep_ok = df[c_dep].map(depto_a_cod).notna()
    nit_ok = df[c_nit].astype(str).str.replace(r"\D", "", regex=True).str.len().between(5, 11)
    return float((dep_ok & nit_ok).mean()), c_nit, c_dep


def cargar_reps() -> pd.DataFrame:
    """NIT -> departamento (código DANE) desde la exportación "por prestador" del REPS.

    El archivo puede venir tabulado o con punto y coma, con comillas sueltas dentro de
    nombres y, en algunos casos, saltos de línea dentro de campos entrecomillados. En vez
    de asumir un formato, se prueban varias combinaciones y se elige la que produzca la
    mayor proporción de filas con departamento reconocible y NIT plausible.
    """
    cand = list(RAW.glob("F4_reps_prestadores.*"))
    if not cand:
        return pd.DataFrame(columns=["nit", "cod_depto"])
    p = cand[0]

    if _es_html(p):
        df = _leer_reps_html(p)
        print(f"  [reps] archivo detectado como tabla HTML: {len(df):,} filas leídas")
        if df.empty:
            print("  [reps] No se encontró la cabecera esperada (depa_nombre, nits_nit).")
            return pd.DataFrame(columns=["nit", "cod_depto"])
        out = pd.DataFrame({"nit": df["nits_nit"].astype(str).str.replace(r"\D", "", regex=True),
                            "cod_depto": df["depa_nombre"].map(depto_a_cod)})
        total = len(out)
        out = out[out["nit"].str.len().between(5, 11)].dropna(subset=["cod_depto"]).drop_duplicates("nit")
        print(f"  [reps] {len(out):,} de {total:,} prestadores con NIT y departamento válidos ({len(out)/total:.1%})")
        return out

    def limpiar(df: pd.DataFrame) -> pd.DataFrame:
        """Quita comillas envolventes de nombres de columna y de valores de texto."""
        df = df.rename(columns=lambda c: str(c).strip().strip('"').strip("'").strip())
        return df

    intentos = []
    if p.suffix.lower() in (".csv", ".txt"):
        raw = p.read_bytes()[:300_000]
        enc = "utf-8-sig"
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                texto = raw.decode(enc); break
            except UnicodeDecodeError:
                continue
        primera = texto.splitlines()[0]
        seps = sorted([";", ",", "\t", "|"], key=primera.count, reverse=True)[:2]
        for sep in seps:
            for etiqueta, kw in [("comillas estándar", {"quoting": csv.QUOTE_MINIMAL}),
                                 ("sin comillas", {"quoting": csv.QUOTE_NONE})]:
                try:
                    df = limpiar(pd.read_csv(p, sep=sep, dtype=str, encoding=enc, engine="python",
                                              on_bad_lines="skip", **kw))
                    intentos.append((f"sep={sep!r} {etiqueta}", df))
                except Exception as e:
                    intentos.append((f"sep={sep!r} {etiqueta} (falló: {type(e).__name__})", pd.DataFrame()))
    else:
        try:
            intentos.append(("excel", limpiar(pd.read_excel(p, dtype=str))))
        except Exception as e:
            intentos.append((f"excel (falló: {type(e).__name__})", pd.DataFrame()))

    # Se elige por número de filas utilizables (proporción x filas), no solo por proporción:
    # una lectura puede ser 100% limpia pero haber descartado la mitad del archivo.
    mejor = (-1.0, -1.0, None, None, None, "")
    for etiqueta, df in intentos:
        punt, c_nit, c_dep = _puntaje_reps(df)
        utiles = punt * len(df)
        print(f"  [reps] {etiqueta}: {len(df):,} filas, {punt:.1%} utilizables ({utiles:,.0f})")
        if utiles > mejor[0]:
            mejor = (utiles, punt, df, c_nit, c_dep, etiqueta)

    _, punt, df, c_nit, c_dep, etiqueta = mejor
    if df is None or df.empty or c_nit is None or c_dep is None:
        print("  [reps] No se pudo leer el archivo de forma utilizable. El panel quedará sin desagregación territorial del giro.")
        return pd.DataFrame(columns=["nit", "cod_depto"])
    print(f"  [reps] lectura elegida: {etiqueta} ({len(df):,} filas)")

    out = pd.DataFrame({"nit": df[c_nit].astype(str).str.replace(r"\D", "", regex=True),
                        "cod_depto": df[c_dep].map(depto_a_cod)})
    total = len(out)
    out = out[out["nit"].str.len().between(5, 11)]
    out = out.dropna(subset=["cod_depto"]).drop_duplicates("nit")
    print(f"  [reps] {len(out):,} de {total:,} prestadores con NIT y departamento válidos ({len(out)/total:.1%})" if total else "  [reps] archivo vacío")
    if punt < 0.5:
        print(f"  [reps] Advertencia: lectura de baja calidad. Columnas detectadas: {list(df.columns)[:12]}")
        print(f"  [reps] Valores crudos de '{c_dep}': {df[c_dep].head(5).tolist()}")
        print(f"  [reps] Valores crudos de '{c_nit}': {df[c_nit].head(5).tolist()}")
    return out


# ----------------------------------------------------------------- F2 giro directo
def cargar_giro_contributivo() -> pd.DataFrame:
    partes = []
    p = RAW / "F2_giro_contributivo_ips_2020_2026.xlsx"
    if p.exists():
        df = pd.read_excel(p, dtype={"NIT": str})
        df.columns = [norm(c) for c in df.columns]
        df = df.rename(columns={"ANO": "anio", "MES": "mes", "NIT": "nit", "CODIGO EPS": "cod_eps", "NOMBRE EPS": "nombre_eps",
                                "VALOR GIRO IPS": "valor_girado"})
        partes.append(df[["anio", "mes", "nit", "cod_eps", "nombre_eps", "valor_girado"]])
    for p in sorted(RAW.glob("F2_giro_contributivo_adres_*.xlsx")):
        anio, mes = re.findall(r"(\d{4})_(\d{2})", p.name)[0]
        df = pd.read_excel(p, sheet_name=0, header=None, skiprows=10, dtype=str)
        df = df.dropna(how="all", axis=1); df = df.dropna(how="all")
        df.columns = ["nit", "razon_social", "cod_eps", "nombre_eps", "valor_ordenado", "valor_girado", "observacion", "fecha_proceso", "fecha_giro"][: df.shape[1]]
        df = df[df["nit"].astype(str).str.match(r"^\d+$", na=False)]
        df["anio"], df["mes"] = int(anio), int(mes)
        partes.append(df[["anio", "mes", "nit", "cod_eps", "nombre_eps", "valor_girado"]])
    if not partes:
        return pd.DataFrame()
    g = pd.concat(partes, ignore_index=True)
    g["regimen"] = "CONTRIBUTIVO"
    return g


def cargar_giro_subsidiado_ips() -> pd.DataFrame:
    p = RAW / "F2_giro_subsidiado_ips_2020_2024.xlsx"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_excel(p, dtype=str)
    df.columns = [norm(c).replace("*", "").strip() for c in df.columns]
    ren = {}
    for c in df.columns:
        if c.startswith("ANO"): ren[c] = "anio"
        elif c.startswith("MES"): ren[c] = "mes"
        elif "NIT" in c: ren[c] = "nit"
        elif "CODIGO" in c and "EPS" in c: ren[c] = "cod_eps"
        elif c == "EPS": ren[c] = "nombre_eps"
        elif "GIRADO" in c: ren[c] = "valor_girado"
    df = df.rename(columns=ren)
    df["regimen"] = "SUBSIDIADO"
    return df[["anio", "mes", "nit", "cod_eps", "nombre_eps", "valor_girado", "regimen"]]


def cargar_lma_eps() -> pd.DataFrame:
    """Giro directo a prestadores por EPS y mes (subsidiado), 2019 a 2026."""
    p = RAW / "F2_giro_subsidiado_eps_2019_2026.xlsx"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_excel(p, dtype=str)
    df.columns = [norm(c) for c in df.columns]
    c_gd = next(c for c in df.columns if "PRESTADORES" in c)
    c_upc = next(c for c in df.columns if c.startswith("UPC NETA"))
    out = pd.DataFrame({"periodo": periodo(df["ANO"], df["MES"]).values,
                        "eps": [grupo_eps(c, n) for c, n in zip(df["CODIGO EPS"], df["EPS"])],
                        "giro_directo_eps_sub": pd.to_numeric(df[c_gd], errors="coerce"),
                        "upc_neta_sub": pd.to_numeric(df[c_upc], errors="coerce")})
    return out.groupby(["eps", "periodo"], as_index=False).sum()


# ----------------------------------------------------------------- F3 afiliados
def cargar_bdua() -> pd.DataFrame:
    partes = []
    for reg in ("contributivo", "subsidiado"):
        p = RAW / f"F3_bdua_{reg}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, sep=None, engine="python", dtype=str, encoding="utf-8", encoding_errors="replace")
        cols = {c: norm(c) for c in df.columns}
        c_cod = next(c for c, n in cols.items() if "CODIGO" in n and "ENTIDAD" in n)
        c_nom = next(c for c, n in cols.items() if "NOMBRE" in n and "ENTIDAD" in n)
        c_dep = next(c for c, n in cols.items() if n == "DEPARTAMENTO")
        c_est = next((c for c, n in cols.items() if "ESTADO" in n), None)
        c_can = next(c for c, n in cols.items() if "CANTIDAD" in n)
        if c_est:
            df = df[df[c_est].map(norm) == "ACTIVO"]
        out = pd.DataFrame({"eps": [grupo_eps(c, n) for c, n in zip(df[c_cod], df[c_nom])],
                            "cod_depto": df[c_dep].map(depto_a_cod),
                            "regimen": reg.upper(),
                            "afiliados_bdua": pd.to_numeric(df[c_can], errors="coerce")})
        partes.append(out)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes).groupby(["eps", "regimen", "cod_depto"], as_index=False)["afiliados_bdua"].sum()


def cargar_lma_detalle() -> pd.DataFrame:
    """UPC neta subsidiada por departamento, EPS y mes (proxy mensual de afiliación subsidiada)."""
    partes = []
    for p in sorted(RAW.glob("F3_lma_detalle_*")):
        eng = "pyxlsb" if p.suffix == ".xlsb" else None
        df = pd.read_excel(p, engine=eng, header=None, skiprows=9, usecols=range(0, 11), dtype=str)
        df = df.dropna(how="all")
        df.columns = ["mes", "dane", "departamento", "municipio", "cod_eps", "nombre_eps"] + [f"c{i}" for i in range(6, 11)]
        df = df[df["dane"].astype(str).str.match(r"^\d{4,5}$", na=False)]
        if pd.api.types.is_datetime64_any_dtype(df["mes"]):
            mes = df["mes"]
        else:
            mes = pd.to_datetime(df["mes"], errors="coerce", format="mixed")
            if mes.isna().mean() > 0.5:  # xlsb entrega fechas como serial de Excel
                mes = pd.to_datetime(pd.to_numeric(df["mes"], errors="coerce"), unit="D", origin="1899-12-30")
        upc_neta = pd.to_numeric(df["c10"], errors="coerce")  # columna UPC NETA (índice 10)
        out = pd.DataFrame({"periodo": mes.dt.strftime("%Y-%m"), "cod_depto": df["dane"].str.zfill(5).str[:2],
                            "eps": [grupo_eps(c, n) for c, n in zip(df["cod_eps"], df["nombre_eps"])], "upc_neta_sub": upc_neta})
        partes.append(out)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes).groupby(["eps", "cod_depto", "periodo"], as_index=False)["upc_neta_sub"].sum()


# ----------------------------------------------------------------- integración
def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    pqrd = cargar_pqrd()
    reps = cargar_reps()
    giro = pd.concat([cargar_giro_contributivo(), cargar_giro_subsidiado_ips()], ignore_index=True)
    bdua = cargar_bdua()
    lma_eps = cargar_lma_eps()
    lma_det = cargar_lma_detalle()

    # --- giro directo con departamento (vía REPS), tolerante al dígito de verificación (DV)
    # El NIT colombiano se reporta a veces con DV (10 dígitos) y a veces sin él (9 dígitos);
    # si un lado lo incluye y el otro no, un cruce exacto no encuentra ninguna coincidencia.
    if len(giro) and len(reps):
        giro["periodo"] = periodo(giro["anio"], giro["mes"]).values
        giro["nit"] = giro["nit"].astype(str).str.replace(r"\D", "", regex=True)
        giro["valor_girado"] = pd.to_numeric(giro["valor_girado"], errors="coerce")
        giro["eps"] = [grupo_eps(c, n) for c, n in zip(giro["cod_eps"], giro["nombre_eps"])]

        def base_nit(s: pd.Series) -> pd.Series:
            """Quita el último dígito (probable DV) cuando el NIT tiene 10 u 11 dígitos."""
            return s.where(~s.str.len().isin([10, 11]), s.str[:-1])

        reps_dep = reps.drop_duplicates("nit").set_index("nit")["cod_depto"]
        reps_dep_base = reps.assign(nit=base_nit(reps["nit"])).drop_duplicates("nit").set_index("nit")["cod_depto"]

        cod_directo = giro["nit"].map(reps_dep)
        cod_por_base_propia = giro["nit"].map(reps_dep_base)  # el giro trae DV, el REPS no
        cod_por_base_reps = base_nit(giro["nit"]).map(reps_dep)  # el REPS trae DV, el giro no
        giro["cod_depto"] = cod_directo.fillna(cod_por_base_propia).fillna(cod_por_base_reps)

        n = len(giro)
        print(f"Cruce NIT-REPS: exacto {cod_directo.notna().mean():.1%} | "
              f"sin DV en giro {(cod_directo.isna() & cod_por_base_propia.notna()).mean():.1%} | "
              f"sin DV en REPS {(cod_directo.isna() & cod_por_base_propia.isna() & cod_por_base_reps.notna()).mean():.1%} | "
              f"sin coincidencia {giro['cod_depto'].isna().mean():.1%} (de {n:,} registros)")
        if giro["cod_depto"].isna().all():
            ej_giro = giro["nit"].dropna().unique()[:5].tolist()
            ej_reps = reps["nit"].dropna().unique()[:5].tolist()
            print(f"  Ningún NIT coincidió ni con ni sin DV. Ejemplos NIT giro: {ej_giro}")
            print(f"  Ejemplos NIT REPS: {ej_reps}  (revisar si corresponden al mismo universo de prestadores)")

        sin_depto = giro["cod_depto"].isna().mean()
        giro_eps = giro.groupby(["eps", "regimen", "periodo"], as_index=False).agg(giro_directo=("valor_girado", "sum"), n_ips=("nit", "nunique"))
        giro_dep = giro.dropna(subset=["cod_depto"]).groupby(["eps", "regimen", "cod_depto", "periodo"], as_index=False).agg(giro_directo=("valor_girado", "sum"), n_ips=("nit", "nunique"))
    elif len(giro):
        # Hay giro directo pero no se pudo cargar el REPS: se agrega por EPS, sin desagregar por departamento.
        giro["periodo"] = periodo(giro["anio"], giro["mes"]).values
        giro["valor_girado"] = pd.to_numeric(giro["valor_girado"], errors="coerce")
        giro["eps"] = [grupo_eps(c, n) for c, n in zip(giro["cod_eps"], giro["nombre_eps"])]
        sin_depto = 1.0
        giro_eps = giro.groupby(["eps", "regimen", "periodo"], as_index=False).agg(giro_directo=("valor_girado", "sum"), n_ips=("nit", "nunique"))
        giro_dep = pd.DataFrame(columns=["eps", "regimen", "cod_depto", "periodo", "giro_directo", "n_ips"])
    else:
        sin_depto, giro_eps, giro_dep = None, pd.DataFrame(), pd.DataFrame(columns=["eps", "regimen", "cod_depto", "periodo", "giro_directo", "n_ips"])

    # --- panel EPS x régimen x mes
    p_eps = pqrd.groupby(["eps", "regimen", "periodo"], as_index=False)["pqrd"].sum()
    if len(giro_eps): p_eps = p_eps.merge(giro_eps, on=["eps", "regimen", "periodo"], how="outer")
    if len(lma_eps): p_eps = p_eps.merge(lma_eps.assign(regimen="SUBSIDIADO"), on=["eps", "regimen", "periodo"], how="left")
    if len(bdua):
        af = bdua.groupby(["eps", "regimen"], as_index=False)["afiliados_bdua"].sum()
        p_eps = p_eps.merge(af, on=["eps", "regimen"], how="left")
        p_eps["tasa_pqrd_x1000"] = 1000 * p_eps["pqrd"] / p_eps["afiliados_bdua"]
    p_eps["intervenida"] = p_eps["eps"].isin(INTERVENIDAS).astype(int)
    p_eps["fecha_intervencion"] = p_eps["eps"].map(INTERVENIDAS)
    p_eps["post_intervencion"] = ((p_eps["fecha_intervencion"].notna()) & (p_eps["periodo"] >= p_eps["fecha_intervencion"])).astype(int)
    p_eps["tratada"] = (p_eps["eps"] == "NUEVA EPS").astype(int)
    p_eps["post_abr24"] = (p_eps["periodo"] >= "2024-04").astype(int)
    p_eps["post_factramed"] = (p_eps["periodo"] >= "2025-09").astype(int)
    p_eps = p_eps[p_eps["periodo"] >= INICIO].sort_values(["eps", "regimen", "periodo"])
    p_eps.to_csv(PROC / "panel_eps_mes.csv", index=False)

    # --- panel departamento x régimen x mes (Nueva EPS y comparadores)
    p_dep = pqrd.groupby(["eps", "regimen", "cod_depto", "periodo"], as_index=False)["pqrd"].sum()
    p_dep = p_dep.merge(giro_dep, on=["eps", "regimen", "cod_depto", "periodo"], how="left")
    if len(bdua): p_dep = p_dep.merge(bdua, on=["eps", "regimen", "cod_depto"], how="left")
    if len(lma_det): p_dep = p_dep.merge(lma_det.assign(regimen="SUBSIDIADO"), on=["eps", "regimen", "cod_depto", "periodo"], how="left")
    if "afiliados_bdua" in p_dep:
        p_dep["tasa_pqrd_x1000"] = 1000 * p_dep["pqrd"] / p_dep["afiliados_bdua"]
    if "giro_directo" in p_dep and "afiliados_bdua" in p_dep:
        p_dep["giro_pc"] = p_dep["giro_directo"] / p_dep["afiliados_bdua"]
    p_dep["departamento"] = p_dep["cod_depto"].map(DEPTOS)
    p_dep["tratada"] = (p_dep["eps"] == "NUEVA EPS").astype(int)
    p_dep["post_abr24"] = (p_dep["periodo"] >= "2024-04").astype(int)
    p_dep["post_factramed"] = (p_dep["periodo"] >= "2025-09").astype(int)
    p_dep = p_dep[(p_dep["periodo"] >= INICIO) & (p_dep["periodo"] <= FIN_PQRD)].sort_values(["eps", "regimen", "cod_depto", "periodo"])
    p_dep.to_csv(PROC / "panel_depto_mes.csv", index=False)

    # --- motivos de Nueva EPS
    mot = pqrd[pqrd["eps"] == "NUEVA EPS"].groupby(["periodo", "regimen", "cod_macromot", "cod_motgen", "riesgo"], as_index=False)["pqrd"].sum()
    mot.to_csv(PROC / "pqrd_motivos_neps.csv", index=False)
    pd.DataFrame([(g, c) for g, cs in GRUPOS_EPS.items() for c in cs], columns=["eps", "codigo"]).to_csv(PROC / "catalogo_eps.csv", index=False)

    # --- resumen
    print(f"panel_eps_mes.csv: {len(p_eps):,} filas | EPS: {p_eps['eps'].nunique()} | periodos: {p_eps['periodo'].min()} a {p_eps['periodo'].max()}")
    print(f"panel_depto_mes.csv: {len(p_dep):,} filas | deptos: {p_dep['cod_depto'].nunique()}")
    if sin_depto is not None:
        print(f"Giro directo: {len(giro):,} registros; sin departamento (NIT no encontrado en REPS): {sin_depto:.1%}")
    ne = p_eps[p_eps["eps"] == "NUEVA EPS"]
    cols = [c for c in ["pqrd", "giro_directo", "afiliados_bdua", "tasa_pqrd_x1000"] if c in ne]
    print(ne.groupby(["regimen", ne["periodo"].str[:4]])[cols].agg({"pqrd": "sum", "giro_directo": "sum", "afiliados_bdua": "first", "tasa_pqrd_x1000": "sum"} if len(cols) == 4 else "sum").round(1).to_string())


if __name__ == "__main__":
    main()
