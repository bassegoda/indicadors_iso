import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query
from demographics._sql import SQL_TEMPLATE
from demographics._metrics import (
    _format_median_iqr,
    _fmt_n_pct,
    _classify_aisbe,
    _mortality,
)
from demographics._report import _CSS

# ---------------------------------------------------------------------------
# Row / section definitions
# ---------------------------------------------------------------------------

_ROW_DEFS = [
    # (key, label, section)
    ("n_stays",   "N estancias",                        "demo"),
    ("n_patients","N pacientes",                        "demo"),
    ("age",       "Edad, mediana [IQR]",                "demo"),
    ("male",      "Sexo masculino (n, %)",              "demo"),
    ("female",    "Sexo femenino (n, %)",               "demo"),
    ("spain",     "Nacionalidad española (n, %)",       "demo"),
    ("aisbe",     "Pacientes AISBE (n, %)",             "demo"),
    ("los",       "Estancia (días), mediana [IQR]",     "clinical"),
    ("cirr",      "Cirrosis (n, %)",                    "clinical"),
    ("readm24",   "Reingreso 24h (n, %)",               "clinical"),
    ("readm72",   "Reingreso 72h (n, %)",               "clinical"),
    ("mort_stay", "Mortalidad en estancia (n, %)",      "mortality"),
    ("mort_30",   "Mortalidad a 30 días (n, %)",        "mortality"),
    ("mort_90",   "Mortalidad a 90 días (n, %)",        "mortality"),
]

_SECTION_DEFS = [
    ("demo",      "Demografía",   "demo"),
    ("clinical",  "Clínica",      "clinical"),
    ("mortality", "Mortalidad",   "mortality"),
]


# ---------------------------------------------------------------------------
# Metric computation for one group
# ---------------------------------------------------------------------------

def compute_group_metrics(df: pd.DataFrame) -> dict[str, str]:
    """Compute all metrics for a DataFrame subset; return formatted strings."""
    if df.empty:
        return {key: "" for key, *_ in _ROW_DEFS}

    df = df.copy()
    if "days_stay" not in df.columns and "hours_stay" in df.columns:
        df["days_stay"] = df["hours_stay"] / 24.0

    n_stays = len(df)
    patients = df.drop_duplicates(subset=["patient_ref"])
    n_pat = len(patients)

    age = pd.to_numeric(df["age_at_admission"], errors="coerce")
    age_fmt = _format_median_iqr(age)

    sex_counts = patients["sex"].value_counts(dropna=False)
    male = int(sex_counts.get("Male", 0))
    female = int(sex_counts.get("Female", 0))

    natio = patients["natio_ref"].fillna("").astype(str)
    n_spain = int((natio == "ES").sum())

    patient_health = (
        patients[["patient_ref", "health_area", "postcode"]].set_index("patient_ref")
    )
    is_aisbe = _classify_aisbe(patient_health)
    n_aisbe = int(is_aisbe.sum())

    los = pd.to_numeric(df["days_stay"], errors="coerce")
    los_fmt = _format_median_iqr(los)

    cirr_col = pd.to_numeric(df["has_cirrhosis"], errors="coerce").fillna(0)
    n_cirr = int((cirr_col == 1).sum())

    readm24_col = pd.to_numeric(df["readmission_24h"], errors="coerce").fillna(0)
    n_readm24 = int((readm24_col == 1).sum())

    readm72_col = pd.to_numeric(df["readmission_72h"], errors="coerce").fillna(0)
    n_readm72 = int((readm72_col == 1).sum())

    mort = _mortality(df)

    return {
        "n_stays":   str(n_stays),
        "n_patients": str(n_pat),
        "age":       age_fmt,
        "male":      _fmt_n_pct(male, n_pat),
        "female":    _fmt_n_pct(female, n_pat),
        "spain":     _fmt_n_pct(n_spain, n_pat),
        "aisbe":     _fmt_n_pct(n_aisbe, n_pat),
        "los":       los_fmt,
        "cirr":      _fmt_n_pct(n_cirr, n_stays),
        "readm24":   _fmt_n_pct(n_readm24, n_stays),
        "readm72":   _fmt_n_pct(n_readm72, n_stays),
        "mort_stay": mort["stay_fmt"],
        "mort_30":   mort["d30_fmt"],
        "mort_90":   mort["d90_fmt"],
    }


# ---------------------------------------------------------------------------
# Build comparison table
# ---------------------------------------------------------------------------

def build_comparison_table(df: pd.DataFrame) -> pd.DataFrame:
    """Split df into Global / Sin cirrosis / Cirrosis and compute metrics."""
    cirr_col = pd.to_numeric(df["has_cirrhosis"], errors="coerce").fillna(0)
    global_df  = df
    no_cirr_df = df[cirr_col == 0]
    cirr_df    = df[cirr_col == 1]

    global_m  = compute_group_metrics(global_df)
    no_cirr_m = compute_group_metrics(no_cirr_df)
    cirr_m    = compute_group_metrics(cirr_df)

    # Cirrhosis row is meaningless for the cirrotic group (always 100%)
    cirr_m["cirr"] = "—"

    labels = [label for _, label, _ in _ROW_DEFS]
    keys   = [key   for key, _, _   in _ROW_DEFS]

    table = pd.DataFrame(
        {
            "Global":       [global_m[k]  for k in keys],
            "Sin cirrosis": [no_cirr_m[k] for k in keys],
            "Cirrosis":     [cirr_m[k]    for k in keys],
        },
        index=labels,
    )
    table.index.name = "Variable"
    return table


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(
    table_df: pd.DataFrame,
    n_global: int,
    n_nocirr: int,
    n_cirr: int,
    output_path: Path,
) -> None:
    col_global  = f"Global (N={n_global})"
    col_nocirr  = f"Sin cirrosis (N={n_nocirr})"
    col_cirr    = f"Cirrosis (N={n_cirr})"

    thead = (
        "<thead><tr>"
        "<th>Variable</th>"
        f"<th>{col_global}</th>"
        f"<th>{col_nocirr}</th>"
        f'<th class="col-total">{col_cirr}</th>'
        "</tr></thead>"
    )

    # Build section → rows mapping
    section_rows: dict[str, list[str]] = {k: [] for k, *_ in _SECTION_DEFS}
    for key, label, section in _ROW_DEFS:
        section_rows[section].append(label)

    body_rows = []
    n_cols = 4  # Variable + 3 data columns

    for section_key, section_title, css_class in _SECTION_DEFS:
        body_rows.append(
            f'<tr class="section-header section-{css_class}">'
            f'<td colspan="{n_cols}">{section_title}</td>'
            f"</tr>"
        )
        for label in section_rows[section_key]:
            global_val  = table_df.at[label, "Global"]
            nocirr_val  = table_df.at[label, "Sin cirrosis"]
            cirr_val    = table_df.at[label, "Cirrosis"]
            body_rows.append(
                f"<tr>"
                f"<td>{label}</td>"
                f"<td>{global_val}</td>"
                f"<td>{nocirr_val}</td>"
                f'<td class="col-total">{cirr_val}</td>'
                f"</tr>"
            )

    tbody = "<tbody>" + "\n".join(body_rows) + "</tbody>"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = "Comparación por cirrosis — E073, I073 (2018–2024)"

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
    <p class="subtitle">Hospital Clínic de Barcelona &mdash; Unidades E073, I073 &mdash; 2018–2024</p>
</div>

<div class="table-wrapper">
<table>
{thead}
{tbody}
</table>
</div>

<div class="report-footer">
    <h3>Notas metodológicas</h3>
    <ul>
        <li><strong>Período:</strong> 2018–2024 (años de ingreso).</li>
        <li><strong>Unidades analizadas:</strong> E073, I073 (movimientos con place_ref válido).</li>
        <li><strong>Estancia:</strong> movimientos consecutivos agrupados con tolerancia de 5 min; unidad predominante por tiempo.</li>
        <li><strong>Filtro de prescripción:</strong> solo estancias con al menos una prescripción activa durante la estancia.</li>
        <li><strong>Sexo y nacionalidad:</strong> calculados a nivel de paciente único (no de estancia).</li>
        <li><strong>AISBE:</strong> pacientes con área básica de salud del área de influencia del hospital o código postal correspondiente.</li>
        <li><strong>Cirrosis:</strong> diagnóstico ICD-9/ICD-10 en cualquier episodio del paciente (condición crónica). La columna Cirrosis muestra "—" para la fila de cirrosis (100% trivial).</li>
        <li><strong>Mortalidad a 30/90 días:</strong> acumulada desde la fecha de ingreso (incluye muertes intrahospitalarias).</li>
        <li><strong>Reingresos:</strong> siguiente ingreso en E073/I073 dentro del plazo indicado tras el alta.</li>
    </ul>
    <p class="timestamp">Informe generado el {now_str}</p>
</div>

</div>
<script>
(function () {{
    function updateStickyOffset() {{
        var header = document.querySelector('.report-header');
        var thead = document.querySelector('thead');
        var headerH = header ? header.offsetHeight : 0;
        var theadH = thead ? thead.offsetHeight : 0;
        document.documentElement.style.setProperty('--thead-top', headerH + 'px');
        document.documentElement.style.setProperty('--sticky-row-top', (headerH + theadH) + 'px');
    }}
    document.addEventListener('DOMContentLoaded', updateStickyOffset);
    window.addEventListener('resize', updateStickyOffset);
}})();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# Plain-text generation
# ---------------------------------------------------------------------------

def generate_txt(
    table_df: pd.DataFrame,
    n_global: int,
    n_nocirr: int,
    n_cirr: int,
    output_path: Path,
) -> None:
    col_headers = [
        "Variable",
        f"Global (N={n_global})",
        f"Sin cirrosis (N={n_nocirr})",
        f"Cirrosis (N={n_cirr})",
    ]

    # Gather all rows in order: section header + data rows
    rows: list[tuple[str, str, str, str]] = []
    section_rows: dict[str, list[str]] = {k: [] for k, *_ in _SECTION_DEFS}
    for key, label, section in _ROW_DEFS:
        section_rows[section].append(label)

    for section_key, section_title, _ in _SECTION_DEFS:
        rows.append((f"--- {section_title} ---", "", "", ""))
        for label in section_rows[section_key]:
            rows.append((
                label,
                table_df.at[label, "Global"],
                table_df.at[label, "Sin cirrosis"],
                table_df.at[label, "Cirrosis"],
            ))

    # Compute column widths
    all_rows_with_header = [tuple(col_headers)] + rows
    col_widths = [
        max(len(str(r[i])) for r in all_rows_with_header)
        for i in range(4)
    ]

    def fmt_row(cells, widths):
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))

    sep = "-" * (sum(col_widths) + 2 * 3)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "Comparación por cirrosis — E073, I073 (2018–2024)",
        f"Generado el {now_str}",
        sep,
        fmt_row(col_headers, col_widths),
        sep,
    ]
    for row in rows:
        if row[1] == "" and row[2] == "" and row[3] == "":
            lines.append(row[0])
        else:
            lines.append(fmt_row(row, col_widths))
    lines.append(sep)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("  CIRRHOSIS COMPARISON TABLE — E073+I073 (2018–2024)")
    print("=" * 50)

    query = SQL_TEMPLATE.format(min_year=2018, max_year=2024)
    df = execute_query(query)
    print(f"Cohorte obtenida: {len(df)} estancias")

    cirr_col = pd.to_numeric(df["has_cirrhosis"], errors="coerce").fillna(0)
    n_global = len(df)
    n_nocirr = int((cirr_col == 0).sum())
    n_cirr   = int((cirr_col == 1).sum())
    print(f"  Global: {n_global} | Sin cirrosis: {n_nocirr} | Cirrosis: {n_cirr}")

    table = build_comparison_table(df)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    csv_path  = output_dir / "cirrhosis_comparison_2018-2024.csv"
    html_path = output_dir / "cirrhosis_comparison_2018-2024.html"
    txt_path  = output_dir / "cirrhosis_comparison_2018-2024.txt"

    table.to_csv(csv_path, encoding="utf-8-sig")
    print(f"CSV guardado en:  {csv_path}")

    generate_html(table, n_global, n_nocirr, n_cirr, html_path)
    print(f"HTML guardado en: {html_path}")

    generate_txt(table, n_global, n_nocirr, n_cirr, txt_path)
    print(f"TXT guardado en:  {txt_path}")


if __name__ == "__main__":
    main()
