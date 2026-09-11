"""Limpieza y agregación de los archivos PQRD de la Supersalud (fuente F1).

Lee todos los archivos data/raw/F1_pqrd*.csv, *.txt o *.zip (uno por año o semestre),
armoniza los tres esquemas conocidos (2022, 2024 en adelante y 2025-II) y produce un
agregado por EPS, régimen, departamento, año, mes, motivo y riesgo, sin datos
identificables. Escribe además data/processed/quality_log.md.

Uso:  python src/clean.py
"""
from __future__ import annotations
import csv, io, zipfile
from datetime import datetime
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW, PROC = BASE / "data" / "raw", BASE / "data" / "processed"
CHUNK = 250_000

# nombre canónico -> posibles nombres en los archivos (comparados en minúscula)
MAPA = {
    "anio": ["año", "anio", "periodo", "ano"],
    "mes": ["mes"],
    "ent_nombre": ["ent_nombre"],
    "ent_cod_sns": ["ent_cod_sns"],
    "ent_tipovig": ["ent_tipovig_sns"],
    "cod_depto": ["afec_cod_depto"],
    "cod_macromot": ["cod_macromot"],
    "cod_motgen": ["cod_motgen"],
    "riesgo_2022": ["riesgo_vida"],
    "riesgo_2024": ["clasificacion_de_riesgo"],
}
LLAVE = ["anio", "mes", "ent_cod_sns", "ent_nombre", "regimen", "cod_depto", "cod_macromot", "cod_motgen", "riesgo"]


def abrir(path: Path):
    if path.suffix.lower() == ".zip":
        z = zipfile.ZipFile(path)
        nombre = [n for n in z.namelist() if not n.endswith("/")][0]
        return z.open(nombre)
    return path.open("rb")


def detectar(path: Path) -> tuple[str, str]:
    """Devuelve (delimitador, codificación) a partir del inicio del archivo."""
    raw = abrir(path).read(200_000)
    enc = "utf-8-sig"
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    primera = texto.splitlines()[0]
    sep = max(["\t", ";", ",", "|"], key=primera.count)
    return sep, enc


def normalizar_columnas(cols) -> dict:
    inv = {}
    for canon, opciones in MAPA.items():
        for c in cols:
            if c.strip().lower() in opciones:
                inv[c] = canon; break
    return inv


def procesar_archivo(path: Path, log: list[str]) -> pd.DataFrame:
    sep, enc = detectar(path)
    with io.TextIOWrapper(abrir(path), encoding=enc, errors="replace") as fh:
        cabecera = pd.read_csv(io.StringIO(fh.readline()), sep=sep, dtype=str).columns
    mapeo = normalizar_columnas(cabecera)
    faltan = [k for k in ("anio", "mes", "ent_cod_sns", "cod_depto", "cod_macromot") if k not in mapeo.values()]
    if faltan:
        log.append(f"* {path.name}: columnas obligatorias ausentes {faltan}; archivo omitido.")
        return pd.DataFrame()
    partes, filas = [], 0
    fh = io.TextIOWrapper(abrir(path), encoding=enc, errors="replace")
    lector = pd.read_csv(fh, sep=sep, dtype=str, usecols=list(mapeo.keys()), chunksize=CHUNK,
                         quoting=csv.QUOTE_MINIMAL, on_bad_lines="skip", engine="c")
    for ch in lector:
        ch = ch.rename(columns=mapeo)
        filas += len(ch)
        ch["anio"] = pd.to_numeric(ch["anio"], errors="coerce")
        ch["mes"] = pd.to_numeric(ch["mes"], errors="coerce")
        ch["cod_depto"] = ch["cod_depto"].astype(str).str.strip().str.zfill(2)
        ch["ent_cod_sns"] = ch["ent_cod_sns"].astype(str).str.strip().str.upper()
        ch["ent_nombre"] = ch["ent_nombre"].astype(str).str.strip().str.upper() if "ent_nombre" in ch else ""
        tipovig = ch["ent_tipovig"].astype(str).str.upper() if "ent_tipovig" in ch else pd.Series("", index=ch.index)
        reg = tipovig.str.replace("RÉGIMEN ", "", regex=False).str.replace("REGIMEN ", "", regex=False)
        ch["regimen"] = reg.where(tipovig.str.contains("GIMEN", na=False), "OTRO")
        if "riesgo_2024" in ch:
            ch["riesgo"] = ch["riesgo_2024"].astype(str).str.strip().str.upper()
        elif "riesgo_2022" in ch:
            ch["riesgo"] = ch["riesgo_2022"].astype(str).str.strip().str.upper().map({"SI": "RIESGO VITAL", "NO": "SIMPLE"})
        else:
            ch["riesgo"] = "SIN DATO"
        for c in ("cod_macromot", "cod_motgen"):
            ch[c] = pd.to_numeric(ch[c], errors="coerce").astype("Int64")
        partes.append(ch.groupby(LLAVE, dropna=False).size().rename("pqrd").reset_index())
    agg = pd.concat(partes).groupby(LLAVE, dropna=False)["pqrd"].sum().reset_index() if partes else pd.DataFrame()
    anios = sorted(int(a) for a in agg["anio"].dropna().unique()) if len(agg) else []
    log.append(f"* {path.name}: {filas:,} filas leídas; sep='{sep}' enc={enc}; años {anios}")
    return agg


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    archivos = sorted(p for p in RAW.glob("F1_pqrd*") if p.suffix.lower() in (".csv", ".txt", ".zip"))
    log = [f"# Registro de calidad F1 PQRD ({datetime.now():%Y-%m-%d %H:%M})", ""]
    if not archivos:
        log.append("* No hay archivos F1_pqrd* en data/raw."); (PROC / "quality_log.md").write_text("\n".join(log)); return
    agg = pd.concat([procesar_archivo(p, log) for p in archivos], ignore_index=True)
    agg = agg.groupby(LLAVE, dropna=False)["pqrd"].sum().reset_index()
    agg = agg[agg["anio"] >= 2022]
    agg.to_csv(PROC / "F1_pqrd_clean.csv", index=False)
    por_anio = agg.groupby("anio")["pqrd"].sum()
    neps = agg[agg["ent_cod_sns"].isin(["EPS037", "EPSS41"])].groupby("anio")["pqrd"].sum()
    meses = agg.groupby("anio")["mes"].nunique()
    sin_depto = int(agg.loc[~agg["cod_depto"].str.match(r"^\d{2}$", na=False), "pqrd"].sum())
    log += ["", f"* Total PQRD 2022 en adelante: {int(agg['pqrd'].sum()):,}",
            "* PQRD por año (todas las entidades): " + ", ".join(f"{int(a)}={int(v):,}" for a, v in por_anio.items()),
            "* PQRD Nueva EPS (EPS037 + EPSS41) por año: " + ", ".join(f"{int(a)}={int(v):,}" for a, v in neps.items()),
            "* Meses con datos por año: " + ", ".join(f"{int(a)}={int(v)}" for a, v in meses.items()),
            "* Referencia externa (Contraloría): Nueva EPS 177.479 PQR en 2022, 446.520 en 2025-I y 518.211 en 2025 completo.",
            f"* PQRD sin departamento válido: {sin_depto:,}"]
    (PROC / "quality_log.md").write_text("\n".join(log), encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main()
