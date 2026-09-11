"""Modelado: series de tiempo interrumpidas, diferencias en diferencias, panel e índice.

Enfoque explicativo e interpretable (ver Sección 7.3 del Entregable 1). El uso de
gradient boosting queda reservado a pruebas de robustez, no a la estimación principal.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import statsmodels.formula.api as smf

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"


def diferencias_en_diferencias(panel: pd.DataFrame):
    """tasa_pqrd ~ tratada * post_intervencion + efectos fijos de departamento y mes."""
    modelo = smf.ols("tasa_pqrd ~ tratada * post_intervencion + C(codigo_dane) + C(mes)", data=panel)
    return modelo.fit(cov_type="cluster", cov_kwds={"groups": panel["codigo_dane"]})


def indice_priorizacion(panel: pd.DataFrame, pesos: dict[str, float] | None = None) -> pd.DataFrame:
    """Índice transparente por departamento: ponderación pública de indicadores normalizados."""
    pesos = pesos or {"tasa_pqrd": 0.5, "giro_pc": 0.3, "variabilidad_giro": 0.2}
    ne = panel[panel["tratada"] == 1]
    agg = ne.groupby("codigo_dane").agg(tasa_pqrd=("tasa_pqrd", "mean"), giro_pc=("giro_pc", "mean"),
                                       variabilidad_giro=("giro_pc", "std"))
    norm = (agg - agg.min()) / (agg.max() - agg.min())
    norm["giro_pc"] = 1 - norm["giro_pc"]  # menor giro per cápita implica mayor prioridad
    agg["indice"] = sum(norm[k] * w for k, w in pesos.items())
    return agg.sort_values("indice", ascending=False)


def main() -> None:
    p = PROC / "panel_depto_mes.csv"
    if not p.exists():
        print("No existe panel_depto_mes.csv. Ejecute src/build_panel.py")
        return
    panel = pd.read_csv(p).dropna(subset=["tasa_pqrd"])
    res = diferencias_en_diferencias(panel)
    print(res.summary().tables[1])
    indice_priorizacion(panel).to_csv(PROC / "indice_priorizacion.csv")
    print("indice_priorizacion.csv generado")


if __name__ == "__main__":
    main()
