"""Registro de las fuentes crudas del proyecto (fuente, archivo, fecha, hash).

Todas las descargas se hacen manualmente desde los portales oficiales y se guardan
en data/raw con los nombres de la tabla FUENTES. Este script verifica que existan
y deja constancia en data/raw/registro_descargas.csv (URL, fecha, hash SHA-256).

Uso:  python src/ingest.py
"""
from __future__ import annotations
import csv, hashlib
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
REGISTRO = RAW / "registro_descargas.csv"

FUENTES = {
    "F1_pqrd*": ("PQRD por EPS, departamento y mes, 2022 a 2025 (Supersalud, Datos Abiertos)", "https://www.supersalud.gov.co (Datos abiertos, PQRD)"),
    "F2_giro_contributivo_ips_2020_2026.*": ("Giro directo contributivo por EPS e IPS, 2020-01 a 2026-04 (ADRES vía Así Vamos en Salud)", "https://www.asivamosensalud.org"),
    "F2_giro_contributivo_adres_2026_*.xlsx": ("Giro directo contributivo mensual, mayo a julio 2026 (ADRES, hoja Giro a IPS - Proceso)", "https://www.adres.gov.co/eps/giro-directo/regimen-contributivo"),
    "F2_giro_subsidiado_ips_2020_2024.*": ("Giro directo subsidiado por EPS e IPS, 2020-01 a 2024-10 (ADRES vía Así Vamos en Salud)", "https://www.asivamosensalud.org"),
    "F2_giro_subsidiado_eps_2019_2026.*": ("LMA subsidiado por EPS: UPC neta, giro directo a prestadores y giro neto, 2019 a 2026-05", "https://www.asivamosensalud.org"),
    "F2_lma_certificacion_2026_*.xlsx": ("Certificación de giro a EPS régimen subsidiado, junio a septiembre 2026 (ADRES)", "https://www.adres.gov.co/eps/procesos/regimen-subsidiado"),
    "F3_bdua_contributivo.*": ("Afiliados BDUA contributivo por EPS, departamento y municipio (corte único, datos abiertos)", "https://www.datos.gov.co"),
    "F3_bdua_subsidiado.*": ("Afiliados BDUA subsidiado por EPS, departamento y municipio (corte único, datos abiertos)", "https://www.datos.gov.co"),
    "F3_lma_detalle_*": ("LMA subsidiado detallada por municipio, EPS y mes, 2022 a 2026 (ADRES, Resumen consolidado)", "https://www.adres.gov.co/eps/procesos/regimen-subsidiado"),
    "F4_reps_prestadores.*": ("Registro Especial de Prestadores: NIT, departamento y municipio de cada IPS (MinSalud REPS)", "https://prestadores.minsalud.gov.co/habilitacion/"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    nuevo = not REGISTRO.exists()
    pendientes = []
    with REGISTRO.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["patron", "descripcion", "url", "archivo", "fecha_utc", "sha256", "bytes"])
        for patron, (desc, url) in FUENTES.items():
            archivos = sorted(RAW.glob(patron))
            if not archivos:
                pendientes.append((patron, url)); continue
            for a in archivos:
                w.writerow([patron, desc, url, a.name, datetime.now(timezone.utc).isoformat(timespec="seconds"), sha256(a), a.stat().st_size])
                print(f"[ok] {a.name}")
    for patron, url in pendientes:
        print(f"[pendiente] {patron}: descargar desde {url}")
    if pendientes:
        print(f"\nFaltan {len(pendientes)} fuente(s). El pipeline continúa, pero los análisis que "
              "dependan de ellas quedarán incompletos.")
    else:
        print("\nTodas las fuentes están presentes y registradas.")
    return 0


if __name__ == "__main__":
    main()  # sin sys.exit: en un cuaderno, SystemExit interrumpe la celda
