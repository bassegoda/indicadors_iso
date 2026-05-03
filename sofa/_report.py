"""Salida CSV + HTML básica del reporting SOFA."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_cohort_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_summary_csv(summary: pd.DataFrame, path: Path) -> None:
    summary.to_csv(path, index=False, encoding="utf-8-sig")


def write_html_report(df: pd.DataFrame, summary: pd.DataFrame,
                      title: str, path: Path) -> None:
    """HTML autocontenido con resumen + distribución por unidad."""
    by_unit = (df.groupby("ou_loc_ref")["sofa_total"]
                 .describe(percentiles=[0.25, 0.5, 0.75])
                 .round(2))
    components = (df[["ou_loc_ref", "sofa_resp", "sofa_coag", "sofa_liver",
                      "sofa_cardio", "sofa_neuro", "sofa_renal"]]
                  .groupby("ou_loc_ref").mean().round(2))

    html = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; margin: 32px;
        max-width: 1200px; color: #222; }}
h1 {{ color: #003a70; }}
h2 {{ color: #003a70; border-bottom: 1px solid #ccc; padding-bottom: 4px;
      margin-top: 32px; }}
table {{ border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: right; }}
th {{ background: #f0f4f8; }}
td:first-child, th:first-child {{ text-align: left; }}
.note {{ color: #666; font-size: 0.9em; margin-top: 24px; }}
</style></head><body>
<h1>{title}</h1>
<p>Pacientes UCI Hospital Clínic — SOFA al ingreso (peor valor en las
primeras 24 h desde admission_date).</p>

<h2>Resumen por unidad y año</h2>
{summary.to_html(index=False, float_format=lambda x: f"{x:.2f}")}

<h2>Distribución del SOFA total por unidad</h2>
{by_unit.to_html(float_format=lambda x: f"{x:.2f}")}

<h2>Media de cada componente por unidad</h2>
{components.to_html(float_format=lambda x: f"{x:.2f}")}

<p class="note">
<b>Política de datos faltantes:</b> si un componente no es evaluable
(p.ej. no hay Glasgow porque no se hizo ventana neurológica) se trata
como NA y suma 0 al SOFA total. La columna
<code>sofa_components_available</code> indica cuántos de los 6
componentes se han podido puntuar realmente.<br>
<b>Limitaciones v1:</b> cardiovascular sin dosis exacta de vasopresor
(presencia binaria); renal sin diuresis (sólo creatinina); respiratorio
asume FiO2=21% si no hay registro. Se incluyen también los componentes
precalculados del form SOFA de DataNex (<code>sofa_form_*</code>) cuando
están disponibles, para validación cruzada.
</p>
</body></html>
"""
    path.write_text(html, encoding="utf-8")
