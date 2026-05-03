from datetime import datetime
from pathlib import Path

import pandas as pd

_CSS = """
:root {
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    --color-text: #1f2937;
    --color-text-muted: #6b7280;
    --color-border: #e5e7eb;
    --color-border-thick: #d1d5db;
    --color-bg: #ffffff;
    --color-bg-header: #f8fafc;
    --color-bg-total: #f8fafc;
    --section-demo: #eef2f7;
    --section-demo-text: #1e3a5f;
    --section-demo-accent: #3b82f6;
    --section-clinical: #eef2f7;
    --section-clinical-text: #1e3a5f;
    --section-clinical-accent: #3b82f6;
    --section-mortality: #fef2f2;
    --section-mortality-text: #991b1b;
    --section-mortality-accent: #ef4444;
    --section-mortality-cirr: #faf5ff;
    --section-mortality-cirr-text: #581c87;
    --section-mortality-cirr-accent: #a855f7;
    --section-mortality-noaisbe: #f3f4f6;
    --section-mortality-noaisbe-text: #374151;
    --section-mortality-noaisbe-accent: #6b7280;
    --section-mortality-otherhosp: #fff7ed;
    --section-mortality-otherhosp-text: #9a3412;
    --section-mortality-otherhosp-accent: #f97316;
}

* { box-sizing: border-box; }

body {
    font-family: var(--font-sans);
    color: var(--color-text);
    margin: 0;
    padding: 16px;
    background: #f9fafb;
    line-height: 1.5;
}

.container {
    max-width: min(1700px, calc(100vw - 32px));
    margin: 0 auto;
    background: var(--color-bg);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    overflow: clip;
}

/* Header */
.report-header {
    padding: 32px 40px 24px;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg);
}
.report-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--color-text);
    margin: 0 0 6px;
}
.report-header .subtitle {
    font-size: 14px;
    color: var(--color-text-muted);
    margin: 0;
}

/* Table wrapper for horizontal scroll */
.table-wrapper {
    overflow-x: auto;
    padding: 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    min-width: 800px;
}

thead th {
    background: var(--color-bg-header);
    padding: 12px 10px;
    text-align: center;
    font-weight: 600;
    font-size: 13px;
    color: var(--color-text);
    border-bottom: 2px solid var(--color-border-thick);
    white-space: nowrap;
}
thead th:first-child {
    text-align: left;
    min-width: 200px;
    padding-left: 16px;
    background: var(--color-bg-header);
}
thead th.col-total {
    border-left: 2px solid var(--color-border-thick);
    background: var(--color-bg-total);
    font-weight: 700;
}

/* Section header rows */
tr.section-header td {
    padding: 10px 16px 10px 16px;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--color-border);
    border-top: 1px solid var(--color-border);
}
tr.section-header td:first-child {
    border-left: 4px solid transparent;
}

tr.section-demo td { background: var(--section-demo); color: var(--section-demo-text); }
tr.section-demo td:first-child { border-left-color: var(--section-demo-accent); }
tr.section-clinical td { background: var(--section-clinical); color: var(--section-clinical-text); }
tr.section-clinical td:first-child { border-left-color: var(--section-clinical-accent); }
tr.section-mortality td { background: var(--section-mortality); color: var(--section-mortality-text); }
tr.section-mortality td:first-child { border-left-color: var(--section-mortality-accent); }
tr.section-mortality-cirr td { background: var(--section-mortality-cirr); color: var(--section-mortality-cirr-text); }
tr.section-mortality-cirr td:first-child { border-left-color: var(--section-mortality-cirr-accent); }
tr.section-mortality-noaisbe td { background: var(--section-mortality-noaisbe); color: var(--section-mortality-noaisbe-text); }
tr.section-mortality-noaisbe td:first-child { border-left-color: var(--section-mortality-noaisbe-accent); }
tr.section-mortality-otherhosp td { background: var(--section-mortality-otherhosp); color: var(--section-mortality-otherhosp-text); }
tr.section-mortality-otherhosp td:first-child { border-left-color: var(--section-mortality-otherhosp-accent); }

/* Data rows */
tbody td {
    padding: 9px 10px;
    text-align: center;
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
tbody td:first-child {
    text-align: left;
    padding-left: 16px;
    padding-right: 12px;
    color: var(--color-text);
    background: var(--color-bg);
}
tbody td.col-total {
    border-left: 2px solid var(--color-border-thick);
    background: var(--color-bg-total);
    font-weight: 600;
}
tbody tr:hover td {
    background-color: #f1f5f9;
}
tbody tr:hover td:first-child {
    background-color: #f1f5f9;
}
tbody tr:hover td.col-total {
    background-color: #eef2f6;
}

/* Row styles */
tr.row-bold td:first-child { font-weight: 700; }
tr.row-bold td { font-weight: 600; }
tr.row-indent td:first-child { padding-left: 32px; color: var(--color-text-muted); }

/* Footer */
.report-footer {
    padding: 24px 40px;
    border-top: 1px solid var(--color-border);
    background: #fafbfc;
}
.report-footer h3 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin: 0 0 10px;
    font-weight: 600;
}
.report-footer ul {
    margin: 0;
    padding: 0 0 0 18px;
    font-size: 12px;
    color: var(--color-text-muted);
    line-height: 1.7;
}
.report-footer .timestamp {
    margin-top: 14px;
    font-size: 11px;
    color: #9ca3af;
}

/* Print */
@media print {
    body { background: #fff; padding: 0; margin: 0; }
    .container { box-shadow: none; border-radius: 0; }
    .report-header { padding: 20px; }
    table { font-size: 10px; min-width: 0; }
    thead th, tbody td { padding: 5px 8px; }
    thead { display: table-header-group; }
    .report-footer { padding: 16px 20px; }
    @page { size: landscape; margin: 1cm; }
}

@media (max-width: 768px) {
    body { padding: 16px; }
    .report-header { padding: 20px; }
    .report-header h1 { font-size: 18px; }
    table { font-size: 11px; }
    thead th, tbody td { padding: 6px 10px; }
}
"""


def to_dataframe(sections: list[dict], years: list[int]) -> pd.DataFrame:
    """Flatten structured sections into a DataFrame for CSV export."""
    index: list[str] = []
    data: dict[int, list[str]] = {y: [] for y in years}

    for sec in sections:
        for row in sec["rows"]:
            label = row.get("csv_label", row["label"])
            index.append(label)
            for y in years:
                data[y].append(row["values"].get(y, ""))

    summary_df = pd.DataFrame(data, index=index)
    summary_df.index.name = "Variable"
    return summary_df


def generate_html(
    sections: list[dict],
    years: list[int],
    title: str,
    output_path: Path,
    subtitle: str = "Hospital Cl\u00ednic de Barcelona \u2014 Unidades E073, I073",
) -> None:
    """Generate a professional HTML report from structured summary data."""

    n_cols = len(years) + 2  # Variable + years + Total

    year_ths = "".join(f'<th>{y}</th>' for y in years)
    thead = (
        f'<thead><tr>'
        f'<th>Variable</th>'
        f'{year_ths}'
        f'<th class="col-total">Total</th>'
        f'</tr></thead>'
    )

    body_rows = []
    for sec in sections:
        body_rows.append(
            f'<tr class="section-header section-{sec["css"]}">'
            f'<td colspan="{n_cols}">{sec["section"]}</td>'
            f'</tr>'
        )
        for row in sec["rows"]:
            style = row.get("style", "")
            classes = [f'row-{style}'] if style else []
            if row.get("sticky"):
                classes.append("row-sticky")
            row_class = " ".join(classes)
            cells = [f'<td>{row["label"]}</td>']
            for y in years:
                cells.append(f'<td>{row["values"].get(y, "")}</td>')
            cells.append(f'<td class="col-total">{row.get("total", "")}</td>')
            body_rows.append(
                f'<tr class="{row_class}">' + "".join(cells) + '</tr>'
            )

    tbody = '<tbody>' + "\n".join(body_rows) + '</tbody>'
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">

<div class="report-header">
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
</div>

<div class="table-wrapper">
<table>
{thead}
{tbody}
</table>
</div>

<div class="report-footer">
    <h3>Notas metodol\u00f3gicas</h3>
    <ul>
        <li><strong>Unidades analizadas:</strong> E073, I073 (movimientos con place_ref v\u00e1lido).</li>
        <li><strong>Estancia:</strong> movimientos consecutivos agrupados con tolerancia de 5 min; unidad predominante por tiempo.</li>
        <li><strong>Filtro de prescripci\u00f3n:</strong> solo estancias con al menos una prescripci\u00f3n activa durante la estancia.</li>
        <li><strong>Sexo y nacionalidad:</strong> calculados a nivel de paciente \u00fanico (no de estancia).</li>
        <li><strong>AISBE:</strong> pacientes con \u00e1rea b\u00e1sica de salud del \u00e1rea de influencia del hospital o c\u00f3digo postal correspondiente.</li>
        <li><strong>Mortalidad a 30/90 d\u00edas:</strong> acumulada desde la fecha de ingreso (incluye muertes intrahospitalarias).</li>
        <li><strong>Cirrosis:</strong> diagn\u00f3stico ICD-9/ICD-10 en cualquier episodio del paciente (condici\u00f3n cr\u00f3nica). <strong>Excluidos los pacientes con trasplante hep\u00e1tico realizado durante el episodio</strong> (ICD-10-PCS <code>0FY0\u2026</code>, ICD-9-CM <code>50.5x</code>): ingresan electivamente para trasplante y su mortalidad depende del proceso del trasplante, no de la cirrosis subyacente; mantenerlos en la cohorte infraestimaba la mortalidad atribuible a cirrosis.</li>
        <li><strong>Reingresos:</strong> siguiente ingreso en E073/I073 dentro del plazo indicado tras el alta.</li>
        <li><strong>SOFA al ingreso:</strong> SOFA original (Vincent 1996) calculado sobre las primeras 24 h desde la entrada a la unidad. Solo se evalúa en unidades de UCI (p.ej. E073). Componentes faltantes suman 0 al total; la fila <em>SOFA cobertura completa 6/6</em> indica qué fracción de estancias tienen los 6 componentes evaluables. Subgrupos <em>cirrosis</em> y <em>otro hospital</em> usan las mismas definiciones que las filas correspondientes de mortalidad. Detalle metodológico en <code>demographics/sofa/README.md</code>.</li>
        <li><strong>Ocupaci\u00f3n de camas:</strong> numerador = horas-cama ocupadas (suma de solapamientos de cada movimiento con cada mes, excluyendo la cama auxiliar de procedimientos de E073). Denominador = camas nominales \u00d7 horas del mes seg\u00fan la \u00e9poca: I073=4 y E073=8 hasta 2020-02; UCI agregada=12 entre 2020-03 y 2022-03 (\u00e9poca COVID); I073=4 y E073=10 desde 2022-04. <em>(*)</em> en un a\u00f1o indica que incluye meses de la \u00e9poca COVID, durante la cual el etiquetado E073/I073 no es interpretable (camas reasignadas administrativamente y <code>place_ref</code> pseudo-anonimizados): el % se calcula sobre la UCI agregada y puede superar el 100% en periodos de expansi\u00f3n.</li>
        <li><strong>Total:</strong> pacientes \u00fanicos se cuentan una vez; porcentajes se calculan sobre la suma de los denominadores anuales.</li>
    </ul>
    <p class="timestamp">Informe generado el {now_str}</p>
</div>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
