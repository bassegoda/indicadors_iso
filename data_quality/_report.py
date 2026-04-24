"""HTML report + matplotlib charts for the 2024 vs 2025 completeness analysis.

Charts are rendered in-memory with matplotlib and embedded as base64 PNGs so
the resulting HTML is a single standalone file (same pattern used in other
modules but extended with charts).
"""

from __future__ import annotations

import base64
import io
from datetime import date, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data_quality._metrics import MONTH_NAMES_ES


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
    --accent-blue: #3b82f6;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-green: #10b981;
}

* { box-sizing: border-box; }

body {
    font-family: var(--font-sans);
    color: var(--color-text);
    margin: 0;
    padding: 40px;
    background: #f9fafb;
    line-height: 1.5;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: var(--color-bg);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    overflow: clip;
}

.report-header {
    padding: 32px 40px 24px;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg);
}
.report-header h1 {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 6px;
}
.report-header .subtitle {
    font-size: 14px;
    color: var(--color-text-muted);
    margin: 0;
}

section {
    padding: 28px 40px;
    border-bottom: 1px solid var(--color-border);
}
section:last-of-type { border-bottom: 0; }

section h2 {
    font-size: 16px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text);
    margin: 0 0 16px;
    padding-left: 10px;
    border-left: 4px solid var(--accent-blue);
}

.table-wrapper { overflow-x: auto; }

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    margin-bottom: 8px;
}
thead th {
    background: var(--color-bg-header);
    padding: 10px 14px;
    text-align: center;
    font-weight: 600;
    color: var(--color-text);
    border-bottom: 2px solid var(--color-border-thick);
    white-space: nowrap;
}
thead th:first-child { text-align: left; }
tbody td {
    padding: 8px 14px;
    text-align: center;
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
tbody td:first-child {
    text-align: left;
    color: var(--color-text);
}
tbody tr:hover td { background-color: #f1f5f9; }
td.num-positive { color: var(--accent-green); font-weight: 600; }
td.num-negative { color: var(--accent-red); font-weight: 600; }

ul.flags {
    list-style: none;
    padding: 0;
    margin: 0;
}
ul.flags li {
    padding: 10px 14px;
    margin-bottom: 8px;
    border-radius: 8px;
    border-left: 4px solid var(--color-border);
    background: var(--color-bg-header);
    font-size: 13px;
}
ul.flags li.flag-info    { border-left-color: var(--accent-blue); background: #eff6ff; }
ul.flags li.flag-warning { border-left-color: var(--accent-amber); background: #fef3c7; }
ul.flags li.flag-alert   { border-left-color: var(--accent-red); background: #fee2e2; }

.chart { text-align: center; margin: 8px 0 16px; }
.chart img { max-width: 100%; height: auto; border: 1px solid var(--color-border); border-radius: 8px; }

.chart-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
    gap: 16px;
}

.report-footer {
    padding: 24px 40px;
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

@media print {
    body { background: #fff; padding: 0; }
    .container { box-shadow: none; border-radius: 0; }
    .chart-grid { grid-template-columns: 1fr; }
    @page { size: landscape; margin: 1cm; }
}
"""


# -----------------------------------------------------------------------------
# Chart helpers (matplotlib -> base64 PNG)
# -----------------------------------------------------------------------------

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def chart_monthly_lines(monthly: pd.DataFrame, y1: int, y2: int,
                        title: str) -> str:
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(1, 13)
    if y1 in monthly.columns:
        ax.plot(x, monthly[y1].values, marker="o", label=str(y1), color="#3b82f6")
    if y2 in monthly.columns:
        ax.plot(x, monthly[y2].values, marker="o", label=str(y2), color="#ef4444")
    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_NAMES_ES)
    ax.set_ylabel("filas")
    ax.set_title(title, fontsize=11)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_daily_heatmap(daily: pd.DataFrame, y1: int, y2: int,
                        title: str) -> str:
    """Day-of-year x year heatmap, highlighting zero-row days."""
    if daily.empty:
        fig, ax = plt.subplots(figsize=(7.5, 2.4))
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_base64(fig)

    years = [y1, y2]
    matrix = np.full((2, 366), np.nan, dtype=float)
    for yi, y in enumerate(years):
        sub = daily[daily["yr"] == y]
        for _, row in sub.iterrows():
            doy = int(row["day_of_year"]) - 1
            matrix[yi, doy] = row["n_rows"]

    fig, ax = plt.subplots(figsize=(11, 2.2))
    cmap = plt.cm.viridis.copy()
    cmap.set_bad(color="#fee2e2")  # nan -> red (no data pulled)
    masked = np.ma.masked_invalid(matrix)
    im = ax.imshow(masked, aspect="auto", cmap=cmap, interpolation="nearest")

    month_starts = [
        date(2024, m, 1).timetuple().tm_yday for m in range(1, 13)
    ]
    ax.set_xticks([d - 1 for d in month_starts])
    ax.set_xticklabels(MONTH_NAMES_ES)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([str(y1), str(y2)])
    ax.set_title(title, fontsize=11)
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    cbar.set_label("filas/dia", fontsize=9)

    zero_mask = (matrix == 0)
    ys, xs = np.where(zero_mask)
    if xs.size:
        ax.scatter(xs, ys, s=6, c="#dc2626", marker="s", edgecolors="none",
                   label="0 filas")
        ax.legend(loc="lower right", fontsize=8, frameon=False)

    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_ratio_bars(ratios: pd.DataFrame, y1: int, y2: int,
                     title: str) -> str:
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    if ratios.empty:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_base64(fig)
    pv = ratios.pivot(index="mth", columns="yr",
                      values="rows_per_episode").reindex(range(1, 13))
    x = np.arange(1, 13)
    width = 0.38
    if y1 in pv.columns:
        ax.bar(x - width / 2, pv[y1].fillna(0).values, width,
               label=str(y1), color="#3b82f6")
    if y2 in pv.columns:
        ax.bar(x + width / 2, pv[y2].fillna(0).values, width,
               label=str(y2), color="#ef4444")
    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_NAMES_ES)
    ax.set_ylabel("filas / episodio")
    ax.set_title(title, fontsize=11)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    return _fig_to_base64(fig)


def chart_load_freshness(load: pd.DataFrame, y1: int, y2: int,
                         title: str) -> str:
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    if load.empty:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_base64(fig)
    pv = load.pivot(index="mth", columns="yr",
                    values="lag_days").reindex(range(1, 13))
    x = np.arange(1, 13)
    width = 0.38
    if y1 in pv.columns:
        ax.bar(x - width / 2, pv[y1].fillna(0).values, width,
               label=str(y1), color="#3b82f6")
    if y2 in pv.columns:
        ax.bar(x + width / 2, pv[y2].fillna(0).values, width,
               label=str(y2), color="#ef4444")
    ax.axhline(0, color="#374151", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_NAMES_ES)
    ax.set_ylabel("dias entre fin de mes y max(load_date)")
    ax.set_title(title, fontsize=11)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    return _fig_to_base64(fig)


# -----------------------------------------------------------------------------
# HTML builders
# -----------------------------------------------------------------------------

def _format_cell(val) -> str:
    if pd.isna(val):
        return "-"
    if isinstance(val, (int, np.integer)):
        return f"{int(val):,}".replace(",", ".")
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:,.0f}".replace(",", ".")
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(val)


def _delta_cell(val) -> str:
    if pd.isna(val):
        return '<td>-</td>'
    pct = float(val)
    cls = "num-positive" if pct >= 0 else "num-negative"
    return f'<td class="{cls}">{pct:+.1f}%</td>'


def _df_to_html_table(df: pd.DataFrame, index_label: str = "") -> str:
    """Render a DataFrame as HTML; apply green/red to a 'delta_pct' column."""
    if df.empty:
        return '<p style="color:#6b7280;font-size:13px;">(sin datos)</p>'
    has_delta_pct = "delta_pct" in df.columns
    ths = [f"<th>{index_label or df.index.name or ''}</th>"] + [
        f"<th>{c}</th>" for c in df.columns
    ]
    rows = []
    for idx, row in df.iterrows():
        tds = [f"<td>{_format_cell(idx)}</td>"]
        for c in df.columns:
            if c == "delta_pct" and has_delta_pct:
                tds.append(_delta_cell(row[c]))
            elif c == "delta":
                v = row[c]
                if pd.isna(v):
                    tds.append("<td>-</td>")
                else:
                    cls = "num-positive" if v >= 0 else "num-negative"
                    tds.append(f'<td class="{cls}">{_format_cell(v)}</td>')
            else:
                tds.append(f"<td>{_format_cell(row[c])}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return ("<div class=\"table-wrapper\"><table>"
            f"<thead><tr>{''.join(ths)}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _flags_html(flags: list[dict]) -> str:
    items = []
    for f in flags:
        lvl = f.get("level", "info")
        msg = f.get("msg", "")
        items.append(f'<li class="flag-{lvl}">{msg}</li>')
    return f'<ul class="flags">{"".join(items)}</ul>'


def _image_html(b64: str, alt: str) -> str:
    return (f'<div class="chart">'
            f'<img src="data:image/png;base64,{b64}" alt="{alt}">'
            f'</div>')


def generate_html(*,
                  y1: int, y2: int,
                  totals_mov: pd.DataFrame,
                  totals_lab: pd.DataFrame,
                  ytd_mov: pd.DataFrame,
                  ytd_lab: pd.DataFrame,
                  monthly_mov_pv: pd.DataFrame,
                  monthly_lab_pv: pd.DataFrame,
                  daily_mov: pd.DataFrame,
                  daily_lab: pd.DataFrame,
                  ratios_mov_raw: pd.DataFrame,
                  ratios_lab_raw: pd.DataFrame,
                  orphans: pd.DataFrame,
                  breakdown_unit: pd.DataFrame,
                  breakdown_facility: pd.DataFrame,
                  breakdown_lab: pd.DataFrame,
                  load_mov: pd.DataFrame,
                  load_lab: pd.DataFrame,
                  flags: list[dict],
                  output_path: Path,
                  ytd_cutoff_y1: str,
                  ytd_cutoff_y2: str) -> None:
    """Write the full HTML report to ``output_path``."""
    title = f"Completitud de datos - {y1} vs {y2}"

    # Charts
    chart_mov_monthly = chart_monthly_lines(
        monthly_mov_pv[[y1, y2]] if not monthly_mov_pv.empty else monthly_mov_pv,
        y1, y2, f"Movements por mes ({y1} vs {y2})")
    chart_lab_monthly = chart_monthly_lines(
        monthly_lab_pv[[y1, y2]] if not monthly_lab_pv.empty else monthly_lab_pv,
        y1, y2, f"Labs por mes ({y1} vs {y2})")
    chart_mov_heat = chart_daily_heatmap(
        daily_mov, y1, y2, "Movements - heatmap diario (rojo = 0 filas)")
    chart_lab_heat = chart_daily_heatmap(
        daily_lab, y1, y2, "Labs - heatmap diario (rojo = 0 filas)")
    chart_mov_ratio = chart_ratio_bars(
        ratios_mov_raw, y1, y2, "Movements / episodio por mes")
    chart_lab_ratio = chart_ratio_bars(
        ratios_lab_raw, y1, y2, "Labs / episodio por mes")
    chart_mov_load = chart_load_freshness(
        load_mov, y1, y2, "Movements - lag entre mes y max(load_date) (dias)")
    chart_lab_load = chart_load_freshness(
        load_lab, y1, y2, "Labs - lag entre mes y max(load_date) (dias)")

    # HTML assembly
    sections_html = []

    # 1. Summary totals
    sections_html.append(
        '<section><h2>1. Resumen ejecutivo: totales y YTD</h2>'
        '<h3 style="font-size:13px;color:#374151;margin-top:0">Movements (ano completo)</h3>'
        + _df_to_html_table(totals_mov, index_label="metrica")
        + f'<h3 style="font-size:13px;color:#374151">Movements (YTD al {ytd_cutoff_y2[5:]})</h3>'
        + _df_to_html_table(ytd_mov, index_label="metrica")
        + '<h3 style="font-size:13px;color:#374151">Labs (ano completo)</h3>'
        + _df_to_html_table(totals_lab, index_label="metrica")
        + f'<h3 style="font-size:13px;color:#374151">Labs (YTD al {ytd_cutoff_y2[5:]})</h3>'
        + _df_to_html_table(ytd_lab, index_label="metrica")
        + '</section>'
    )

    # 2. Flags
    sections_html.append(
        '<section><h2>2. Banderas heuristicas</h2>'
        + _flags_html(flags)
        + '</section>'
    )

    # 3. Monthly evolution
    sections_html.append(
        '<section><h2>3. Evolucion mensual</h2>'
        '<div class="chart-grid">'
        + _image_html(chart_mov_monthly, "movements mensual")
        + _image_html(chart_lab_monthly, "labs mensual")
        + '</div>'
        '<h3 style="font-size:13px;color:#374151">Movements mensuales</h3>'
        + _df_to_html_table(monthly_mov_pv, index_label="mes")
        + '<h3 style="font-size:13px;color:#374151">Labs mensuales</h3>'
        + _df_to_html_table(monthly_lab_pv, index_label="mes")
        + '</section>'
    )

    # 4. Daily heatmap
    sections_html.append(
        '<section><h2>4. Heatmap diario</h2>'
        + _image_html(chart_mov_heat, "heatmap movements")
        + _image_html(chart_lab_heat, "heatmap labs")
        + '<p style="font-size:12px;color:#6b7280;">Cuadros rojos marcan dias con 0 filas. '
          'Bloques rojos contiguos sugieren cortes de ETL.</p>'
        + '</section>'
    )

    # 5. Ratios
    sections_html.append(
        '<section><h2>5. Filas por episodio</h2>'
        '<p style="font-size:13px;color:#374151;">Si los episodios se mantienen pero caen '
        'las filas/episodio, las filas hijas se estan perdiendo en la carga.</p>'
        '<div class="chart-grid">'
        + _image_html(chart_mov_ratio, "ratio movements")
        + _image_html(chart_lab_ratio, "ratio labs")
        + '</div>'
        '</section>'
    )

    # 6. Load date freshness
    sections_html.append(
        '<section><h2>6. Frescura de load_date</h2>'
        '<p style="font-size:13px;color:#374151;">Dias entre el fin de mes del evento '
        'clinico y el max(load_date) observado. Valores cercanos a 0 (o negativos) '
        'indican carga casi en tiempo real; valores altos + incrementales por mes '
        'son normales; valores planos que no avanzan = ETL detenido.</p>'
        '<div class="chart-grid">'
        + _image_html(chart_mov_load, "lag movements")
        + _image_html(chart_lab_load, "lag labs")
        + '</div>'
        '</section>'
    )

    # 7. Orphan episodes
    sections_html.append(
        '<section><h2>7. Episodios sin movements</h2>'
        '<p style="font-size:13px;color:#374151;">HOSP/HOSP_IQ/HOSP_RN/EM/HAH '
        'deberian tener al menos un movement; % elevados en un ano apuntan a '
        'movements no cargados.</p>'
        + _df_to_html_table(orphans.set_index("episode_type") if not orphans.empty else orphans,
                            index_label="tipo episodio")
        + '</section>'
    )

    # 8. Breakdowns
    sections_html.append(
        '<section><h2>8. Desglose por origen (top 25 por volumen, ordenado por %delta)</h2>'
        '<h3 style="font-size:13px;color:#374151">Movements por unidad fisica (ou_loc_ref)</h3>'
        + _df_to_html_table(breakdown_unit.set_index("ou_loc_ref") if not breakdown_unit.empty else breakdown_unit,
                            index_label="ou_loc_ref")
        + '<h3 style="font-size:13px;color:#374151">Movements por facility</h3>'
        + _df_to_html_table(breakdown_facility.set_index("facility") if not breakdown_facility.empty else breakdown_facility,
                            index_label="facility")
        + '<h3 style="font-size:13px;color:#374151">Labs por parametro (lab_sap_ref)</h3>'
        + _df_to_html_table(breakdown_lab.set_index("lab_sap_ref") if not breakdown_lab.empty else breakdown_lab,
                            index_label="lab_sap_ref")
        + '</section>'
    )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer = f"""
<div class="report-footer">
    <h3>Notas metodologicas</h3>
    <ul>
        <li><strong>Fuentes:</strong> datascope_gestor_prod.movements, datascope_gestor_prod.labs, datascope_gestor_prod.episodes.</li>
        <li><strong>YTD:</strong> comparacion restringida a start_date/extrac_date &lt;= {ytd_cutoff_y1} vs &lt;= {ytd_cutoff_y2} para neutralizar cierre de ano.</li>
        <li><strong>Ratios filas/episodio:</strong> solo filas con episode_ref no nulo.</li>
        <li><strong>Heatmap diario:</strong> reindexado dia a dia; un dia con 0 filas puede ser fin de semana puntual o un hueco de ETL; los bloques sostenidos son los relevantes.</li>
        <li><strong>Episodios sin movements:</strong> join externo episodes -&gt; movements por episode_ref; incluye tipos HOSP, HOSP_IQ, HOSP_RN, EM, HAH.</li>
        <li><strong>Load lag:</strong> dias entre el ultimo dia del mes (start_date/extrac_date) y el max(load_date) registrado para filas de ese mes.</li>
        <li><strong>Umbrales heuristicos:</strong> caida mensual &gt;25% (warning), &gt;50% (alert); ratio filas/episodio &gt;15% (warning); unidad/param &gt;80% (alert) con al menos 100 filas en {y1}.</li>
    </ul>
    <p class="timestamp">Informe generado el {now_str}</p>
</div>
"""

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
    <p class="subtitle">Hospital Clinic de Barcelona - analisis de completitud ETL (movements &amp; labs)</p>
</div>
{''.join(sections_html)}
{footer}
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
