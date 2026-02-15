"""
DRG Complexity Report — Direct Database Connection
====================================================
Connects to DataNex, identifies hospitalisation stays using the
predominant-unit assignment logic, joins DRG data, and generates
a multi-page PDF report demonstrating unit complexity.

Uses the same stay-merging methodology as extract_ward_stays.py:
  - Consecutive movements within 5min tolerance → single stay
  - Assigned to unit with most time (predominant unit)
  - Prescription filter to exclude phantom admissions
  - Bed assignment required (place_ref IS NOT NULL)

Usage:
    python drg_complexity_report.py
    (interactive prompts for units and years)

Output:
    output/drg_complexity_report_<units>_<years>_<timestamp>.pdf
    output/drg_complexity_report_<units>_<years>_<timestamp>.csv
"""

import sys
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec

# ── Connection setup (same as extract_ward_stays.py) ──────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

from connection import execute_query

OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# 1. SQL BUILDER
# ══════════════════════════════════════════════════════════════════════════

def build_drg_query(units: list) -> str:
    """
    Build SQL that identifies stays via predominant-unit logic
    and joins DRG data. Returns one row per stay with DRG fields.
    """
    units_list = "'" + "','".join(units) + "'"

    return f"""
WITH all_related_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_list})
      AND start_date <= '{{max_year}}-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '{{min_year}}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    SELECT
        *,
        CASE
            WHEN ABS(TIMESTAMPDIFF(MINUTE,
                LAG(effective_end_date) OVER (
                    PARTITION BY episode_ref ORDER BY start_date
                ),
                start_date
            )) <= 5
            THEN 0
            ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    SELECT
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
time_per_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) AS minutes_in_unit
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id, ou_loc_ref
),
predominant_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref AS assigned_unit,
        minutes_in_unit AS max_minutes
    FROM (
        SELECT
            t.patient_ref,
            t.episode_ref,
            t.stay_id,
            t.ou_loc_ref,
            t.minutes_in_unit,
            ROW_NUMBER() OVER (
                PARTITION BY t.patient_ref, t.episode_ref, t.stay_id
                ORDER BY t.minutes_in_unit DESC, MIN(g.start_date) ASC
            ) AS rn
        FROM time_per_unit t
        INNER JOIN grouped_stays g
            ON t.patient_ref = g.patient_ref
            AND t.episode_ref = g.episode_ref
            AND t.stay_id = g.stay_id
            AND t.ou_loc_ref = g.ou_loc_ref
        GROUP BY t.patient_ref, t.episode_ref, t.stay_id,
                 t.ou_loc_ref, t.minutes_in_unit
    ) ranked
    WHERE rn = 1
),
stays AS (
    SELECT
        g.patient_ref,
        g.episode_ref,
        g.stay_id,
        p.assigned_unit AS ou_loc_ref,
        MIN(g.start_date) AS admission_date,
        MAX(g.effective_end_date) AS effective_discharge_date,
        YEAR(MIN(g.start_date)) AS stay_year
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.patient_ref = p.patient_ref
        AND g.episode_ref = p.episode_ref
        AND g.stay_id = p.stay_id
    GROUP BY g.patient_ref, g.episode_ref, g.stay_id, p.assigned_unit
    HAVING YEAR(MIN(g.start_date)) BETWEEN {{min_year}} AND {{max_year}}
)
SELECT DISTINCT
    s.patient_ref,
    s.episode_ref,
    s.stay_id,
    s.ou_loc_ref,
    s.stay_year,
    s.admission_date,
    s.effective_discharge_date,
    drg.drg_ref,
    drg.mdc_ref,
    drg.weight,
    drg.severity_ref,
    drg.severity_descr,
    drg.mortality_risk_ref,
    drg.mortality_risk_descr
FROM stays s
INNER JOIN g_diagnostic_related_groups drg
    ON s.patient_ref = drg.patient_ref
    AND s.episode_ref = drg.episode_ref
INNER JOIN g_prescriptions p
    ON s.patient_ref = p.patient_ref
    AND s.episode_ref = p.episode_ref
    AND p.start_drug_date BETWEEN s.admission_date
        AND s.effective_discharge_date
ORDER BY s.stay_year, s.admission_date;
"""


# ══════════════════════════════════════════════════════════════════════════
# 2. DATA EXTRACTION
# ══════════════════════════════════════════════════════════════════════════

def get_years_from_user() -> list:
    """Prompt user for years to analyse."""
    print("\nYears to analyse (e.g. 2024 or 2018-2024): ", end="")
    user_input = input().strip()
    if "-" in user_input:
        start, end = map(int, user_input.split("-"))
        return list(range(start, end + 1))
    elif "," in user_input:
        return [int(y.strip()) for y in user_input.split(",")]
    else:
        return [int(user_input)]


def get_units_from_user() -> list:
    """Prompt user for units (minimum 2)."""
    while True:
        print("Units to analyse (e.g. E073,I073): ", end="")
        user_input = input().strip().upper()
        units = list(dict.fromkeys(u.strip() for u in user_input.split(",") if u.strip()))
        if len(units) < 2:
            print("  ❌ Minimum 2 units required for predominance analysis.\n")
            continue
        return units


def extract_data(units: list, years: list) -> pd.DataFrame:
    """Execute query and return cleaned DataFrame."""
    min_year, max_year = min(years), max(years)
    sql_template = build_drg_query(units)
    query = sql_template.format(min_year=min_year, max_year=max_year)

    print(f"\n  Querying DB for {', '.join(units)} | {min_year}–{max_year}...")
    df = execute_query(query)

    if df is None or df.empty:
        print("  ❌ No data returned.")
        sys.exit(1)

    # Clean
    df["stay_year"] = df["stay_year"].astype(int)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["severity_ref"] = pd.to_numeric(df["severity_ref"], errors="coerce")
    df["mortality_risk_ref"] = pd.to_numeric(df["mortality_risk_ref"], errors="coerce")
    for col in ("severity_descr", "mortality_risk_descr"):
        df[col] = df[col].astype(str).str.strip().str.title()

    # Deduplicate: one row per stay (the prescription JOIN can multiply rows)
    df = df.drop_duplicates(subset=["patient_ref", "episode_ref", "stay_id"])

    print(f"  ✓ {len(df):,} stays | {df['patient_ref'].nunique():,} patients | "
          f"years {df['stay_year'].min()}–{df['stay_year'].max()}")

    return df


# ══════════════════════════════════════════════════════════════════════════
# 3. REPORT CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════

SOI_ORDER = ["Minor", "Moderate", "Major", "Extreme"]
SOI_COLORS = {"Minor": "#4CAF50", "Moderate": "#FFC107", "Major": "#FF9800", "Extreme": "#F44336"}

ROM_ORDER = ["Minor", "Moderate", "Major", "Extreme"]
ROM_COLORS = {"Minor": "#66BB6A", "Moderate": "#42A5F5", "Major": "#AB47BC", "Extreme": "#EF5350"}

ACCENT = "#1565C0"
BG_LIGHT = "#F5F7FA"


# ══════════════════════════════════════════════════════════════════════════
# 4. REPORT HELPERS
# ══════════════════════════════════════════════════════════════════════════

def pct_table(df, descr_col, order, years):
    ct = df.groupby(["stay_year", descr_col]).size().unstack(fill_value=0)
    for cat in order:
        if cat not in ct.columns:
            ct[cat] = 0
    ct = ct[order].reindex(years, fill_value=0)
    pct = ct.div(ct.sum(axis=1).replace(0, 1), axis=0) * 100
    return ct, pct


def annotate_bars(ax, container, fmt="{:.0f}%", min_height=4):
    for bar in container:
        h = bar.get_height()
        if h >= min_height:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + h / 2,
                    fmt.format(h), ha="center", va="center",
                    fontsize=7, fontweight="bold", color="white")


def style_ax(ax, title, ylabel=""):
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10, loc="left")
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_facecolor(BG_LIGHT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)


# ══════════════════════════════════════════════════════════════════════════
# 5. REPORT PAGES
# ══════════════════════════════════════════════════════════════════════════

def page_title(pdf, df, units_str, years):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")

    total = len(df)
    patients = df["patient_ref"].nunique()
    avg_w = df["weight"].mean()
    pct_soi = df["severity_descr"].isin(["Major", "Extreme"]).mean() * 100
    pct_rom = df["mortality_risk_descr"].isin(["Major", "Extreme"]).mean() * 100

    fig.text(0.5, 0.82, "Informe de Complejidad Asistencial",
             ha="center", fontsize=26, fontweight="bold", color=ACCENT)
    fig.text(0.5, 0.75, f"Unidades {units_str}  ·  {min(years)} – {max(years)}",
             ha="center", fontsize=16, color="#555")

    kpis = [
        (f"{total:,}", "Estancias totales"),
        (f"{patients:,}", "Pacientes únicos"),
        (f"{avg_w:.3f}", "Peso DRG medio"),
        (f"{pct_soi:.1f}%", "Severidad ≥ Major"),
        (f"{pct_rom:.1f}%", "Mortalidad ≥ Major"),
    ]
    x_pos = np.linspace(0.1, 0.9, len(kpis))
    for x, (val, lab) in zip(x_pos, kpis):
        fig.text(x, 0.52, val, ha="center", fontsize=28, fontweight="bold", color=ACCENT)
        fig.text(x, 0.46, lab, ha="center", fontsize=10, color="#666")

    fig.text(0.5, 0.30,
             "Este informe demuestra la elevada complejidad de la casuística atendida,\n"
             "con datos objetivos de severidad, riesgo de mortalidad y consumo relativo\n"
             "de recursos (peso DRG). Estancias identificadas mediante lógica de unidad\n"
             "predominante con filtro de prescripción activa.",
             ha="center", fontsize=11, color="#444", linespacing=1.6)

    pdf.savefig(fig)
    plt.close(fig)


def page_volume_and_weight(pdf, df, years):
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 5.5))
    fig.patch.set_facecolor("white")
    fig.suptitle("Evolución del Volumen y Complejidad", fontsize=14, fontweight="bold", y=0.98)

    vol = df.groupby("stay_year").size().reindex(years, fill_value=0)
    ax = axes[0]
    bars = ax.bar(vol.index, vol.values, color=ACCENT, alpha=0.85, width=0.6)
    for bar, v in zip(bars, vol.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + vol.max() * 0.02,
                f"{v:,}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    style_ax(ax, "Nº de Estancias por Año", "Estancias")
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45)

    cmi = df.groupby("stay_year")["weight"].mean().reindex(years)
    ax = axes[1]
    ax.plot(cmi.index, cmi.values, marker="o", linewidth=2.5, color="#E65100", markersize=8)
    for x, y in zip(cmi.index, cmi.values):
        if pd.notna(y):
            ax.text(x, y + cmi.max() * 0.02, f"{y:.3f}",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
    style_ax(ax, "Índice de Case Mix (Peso DRG Medio)", "CMI")
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45)
    ax.set_ylim(bottom=0)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)


def page_stacked_metric(pdf, df, years, descr_col, order, colors, title, short_name):
    """Generic page for SOI or ROM: stacked bars + high-complexity line + summary."""
    fig = plt.figure(figsize=(11.69, 5.5))
    fig.patch.set_facecolor("white")
    gs = GridSpec(1, 5, figure=fig, width_ratios=[3, 0.3, 2, 0.3, 1.5])

    # Stacked bar
    ax1 = fig.add_subplot(gs[0])
    _, pct = pct_table(df, descr_col, order, years)
    bottom = np.zeros(len(years))
    for cat in order:
        vals = pct[cat].values
        cont = ax1.bar(years, vals, bottom=bottom, color=colors[cat],
                       label=cat, width=0.6, edgecolor="white", linewidth=0.5)
        annotate_bars(ax1, cont)
        bottom += vals
    style_ax(ax1, f"Distribución {short_name} (%)", "% Estancias")
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.set_xticks(years)
    ax1.set_xticklabels(years, rotation=45)
    ax1.legend(fontsize=7, loc="lower left")

    # High-complexity line
    ax2 = fig.add_subplot(gs[2])
    high = df.copy()
    high["is_high"] = high[descr_col].isin(["Major", "Extreme"])
    pct_h = high.groupby("stay_year")["is_high"].mean().reindex(years) * 100
    ax2.plot(pct_h.index, pct_h.values, marker="s", linewidth=2.5,
             color=colors["Extreme"], markersize=8)
    for x, y in zip(pct_h.index, pct_h.values):
        if pd.notna(y):
            ax2.text(x, y + 1.5, f"{y:.1f}%", ha="center", fontsize=8, fontweight="bold")
    style_ax(ax2, f"% {short_name} ≥ Major", "% Estancias")
    ax2.set_xticks(years)
    ax2.set_xticklabels(years, rotation=45)
    ax2.set_ylim(bottom=0)

    # Summary box
    ax3 = fig.add_subplot(gs[4])
    ax3.axis("off")
    latest = df[df["stay_year"] == df["stay_year"].max()]
    first = df[df["stay_year"] == df["stay_year"].min()]
    p_lat = latest[descr_col].isin(["Major", "Extreme"]).mean() * 100
    p_fir = first[descr_col].isin(["Major", "Extreme"]).mean() * 100
    delta = p_lat - p_fir
    summary = (
        f"Último año ({latest['stay_year'].iloc[0]}):\n"
        f"  {p_lat:.1f}% ≥ Major\n\n"
        f"Primer año ({first['stay_year'].iloc[0]}):\n"
        f"  {p_fir:.1f}% ≥ Major\n\n"
        f"Variación:\n"
        f"  {'+'if delta>0 else ''}{delta:.1f} pp"
    )
    ax3.text(0.05, 0.95, summary, transform=ax3.transAxes,
             fontsize=9, va="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor=BG_LIGHT, edgecolor="#ccc"))

    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)


def page_weight_distribution(pdf, df, years):
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 5.5))
    fig.patch.set_facecolor("white")
    fig.suptitle("Distribución del Peso DRG (Consumo de Recursos)",
                 fontsize=14, fontweight="bold", y=0.98)

    ax = axes[0]
    data_by_year = [df[df["stay_year"] == y]["weight"].dropna().values for y in years]
    bp = ax.boxplot(data_by_year, tick_labels=years, patch_artist=True,
                    medianprops=dict(color="white", linewidth=2),
                    flierprops=dict(marker=".", markersize=2, alpha=0.3))
    for patch in bp["boxes"]:
        patch.set_facecolor(ACCENT)
        patch.set_alpha(0.7)
    style_ax(ax, "Boxplot del Peso DRG por Año", "Peso DRG")
    ax.tick_params(axis="x", rotation=45)

    ax = axes[1]
    p50 = df.groupby("stay_year")["weight"].median().reindex(years)
    p75 = df.groupby("stay_year")["weight"].quantile(0.75).reindex(years)
    p90 = df.groupby("stay_year")["weight"].quantile(0.90).reindex(years)
    mean = df.groupby("stay_year")["weight"].mean().reindex(years)
    ax.fill_between(years, p50.values, p90.values, alpha=0.15, color=ACCENT)
    ax.plot(years, p90.values, marker="^", linewidth=1.5, color="#C62828", label="P90", markersize=6)
    ax.plot(years, p75.values, marker="s", linewidth=1.5, color="#E65100", label="P75", markersize=6)
    ax.plot(years, mean.values, marker="o", linewidth=2.5, color=ACCENT, label="Media", markersize=7)
    ax.plot(years, p50.values, marker="D", linewidth=1.5, color="#2E7D32", label="Mediana", markersize=6)
    style_ax(ax, "Evolución de Percentiles del Peso DRG", "Peso DRG")
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45)
    ax.legend(fontsize=8)
    ax.set_ylim(bottom=0)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)


def page_top_mdc(pdf, df, years):
    fig = plt.figure(figsize=(11.69, 5.5))
    fig.patch.set_facecolor("white")
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.3])

    ax1 = fig.add_subplot(gs[0])
    mdc_counts = df.groupby("mdc_ref").size().sort_values(ascending=True)
    top10 = mdc_counts.tail(10)
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(top10)))
    bars = ax1.barh(range(len(top10)), top10.values, color=colors, height=0.6)
    ax1.set_yticks(range(len(top10)))
    ax1.set_yticklabels([f"MDC {int(m)}" for m in top10.index], fontsize=8)
    for bar, v in zip(bars, top10.values):
        ax1.text(v + top10.max() * 0.02, bar.get_y() + bar.get_height() / 2,
                 f"{v:,}", va="center", fontsize=8, fontweight="bold")
    style_ax(ax1, "Top 10 MDCs (Categorías Diagnósticas)", "")
    ax1.set_xlabel("Nº Estancias", fontsize=9)

    ax2 = fig.add_subplot(gs[1])
    top10_mdcs = top10.index.tolist()[::-1]
    yearly = df[df["mdc_ref"].isin(top10_mdcs)].groupby(
        ["mdc_ref", "stay_year"]).size().unstack(fill_value=0)
    yearly = yearly.reindex(columns=years, fill_value=0).reindex(top10_mdcs)
    im = ax2.imshow(yearly.values, aspect="auto", cmap="YlOrRd")
    ax2.set_xticks(range(len(years)))
    ax2.set_xticklabels(years, fontsize=8, rotation=45)
    ax2.set_yticks(range(len(top10_mdcs)))
    ax2.set_yticklabels([f"MDC {int(m)}" for m in top10_mdcs], fontsize=8)
    for i in range(len(top10_mdcs)):
        for j in range(len(years)):
            val = yearly.values[i, j]
            if val > 0:
                c = "white" if val > yearly.values.max() * 0.6 else "black"
                ax2.text(j, i, f"{val}", ha="center", va="center",
                         fontsize=7, color=c, fontweight="bold")
    style_ax(ax2, "Evolución Anual por MDC (Top 10)", "")
    plt.colorbar(im, ax=ax2, shrink=0.7, label="Estancias")

    fig.suptitle("Categorías Diagnósticas Mayores (MDC)", fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)


def page_top_drg(pdf, df):
    top = df.groupby("drg_ref").agg(
        n=("drg_ref", "size"),
        avg_weight=("weight", "mean"),
        mdc=("mdc_ref", "first"),
        pct_high_soi=("severity_descr", lambda x: x.isin(["Major", "Extreme"]).mean() * 100),
    ).sort_values("n", ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(11.69, 5.5))
    fig.patch.set_facecolor("white")
    ax.axis("off")

    cols = ["DRG", "MDC", "Estancias", "Peso Medio", "% SOI ≥ Major"]
    data = []
    for drg, r in top.iterrows():
        data.append([f"{int(drg)}", f"{int(r['mdc'])}", f"{int(r['n']):,}",
                     f"{r['avg_weight']:.3f}", f"{r['pct_high_soi']:.1f}%"])

    table = ax.table(cellText=data, colLabels=cols, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    for j in range(len(cols)):
        table[0, j].set_facecolor(ACCENT)
        table[0, j].set_text_props(color="white", fontweight="bold")
    for i in range(1, len(data) + 1):
        bg = BG_LIGHT if i % 2 == 0 else "white"
        for j in range(len(cols)):
            table[i, j].set_facecolor(bg)

    fig.suptitle("Top 15 DRGs Más Frecuentes", fontsize=14, fontweight="bold", y=0.95)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    pdf.savefig(fig)
    plt.close(fig)


def page_summary_table(pdf, df, years):
    records = []
    for y in years:
        ydf = df[df["stay_year"] == y]
        if len(ydf) == 0:
            continue
        records.append({
            "Año": y,
            "Estancias": f"{len(ydf):,}",
            "Pacientes": f"{ydf['patient_ref'].nunique():,}",
            "CMI": f"{ydf['weight'].mean():.3f}",
            "P75": f"{ydf['weight'].quantile(0.75):.3f}",
            "P90": f"{ydf['weight'].quantile(0.90):.3f}",
            "% SOI≥Maj": f"{ydf['severity_descr'].isin(['Major','Extreme']).mean()*100:.1f}%",
            "% ROM≥Maj": f"{ydf['mortality_risk_descr'].isin(['Major','Extreme']).mean()*100:.1f}%",
            "DRGs": f"{ydf['drg_ref'].nunique()}",
            "MDCs": f"{ydf['mdc_ref'].nunique()}",
        })

    sdf = pd.DataFrame(records)
    fig, ax = plt.subplots(figsize=(11.69, 4.5))
    fig.patch.set_facecolor("white")
    ax.axis("off")

    cols = sdf.columns.tolist()
    data = sdf.values.tolist()
    table = ax.table(cellText=data, colLabels=cols, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    for j in range(len(cols)):
        table[0, j].set_facecolor(ACCENT)
        table[0, j].set_text_props(color="white", fontweight="bold")
    for i in range(1, len(data) + 1):
        bg = BG_LIGHT if i % 2 == 0 else "white"
        for j in range(len(cols)):
            table[i, j].set_facecolor(bg)

    fig.suptitle("Resumen de Indicadores por Año", fontsize=14, fontweight="bold", y=0.95)
    fig.text(0.5, 0.08,
             "CMI = Case Mix Index  |  SOI = Severity of Illness  |  "
             "ROM = Risk of Mortality  |  Pxx = Percentil xx",
             ha="center", fontsize=8, color="#888")
    fig.tight_layout(rect=[0, 0.1, 1, 0.92])
    pdf.savefig(fig)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 70)
    print("  DRG COMPLEXITY REPORT — PREDOMINANT UNIT ASSIGNMENT")
    print("=" * 70)

    years = get_years_from_user()
    units = get_units_from_user()
    units_str = " / ".join(units)

    # ── Extract ──
    df = extract_data(units, years)

    # ── Export CSV for traceability ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
    base_name = f"drg_complexity_{'-'.join(units)}_{year_str}_{timestamp}"

    csv_path = OUTPUT_DIR / f"{base_name}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ Data saved: {csv_path.name}")

    # ── Generate report ──
    pdf_path = OUTPUT_DIR / f"{base_name}.pdf"
    print(f"\n  Generating report: {pdf_path.name}")

    with PdfPages(pdf_path) as pdf:
        page_title(pdf, df, units_str, years)
        page_volume_and_weight(pdf, df, years)
        page_stacked_metric(pdf, df, years,
                            "severity_descr", SOI_ORDER, SOI_COLORS,
                            "Severidad de la Enfermedad (SOI)", "SOI")
        page_stacked_metric(pdf, df, years,
                            "mortality_risk_descr", ROM_ORDER, ROM_COLORS,
                            "Riesgo de Mortalidad (ROM)", "ROM")
        page_weight_distribution(pdf, df, years)
        page_top_mdc(pdf, df, years)
        page_top_drg(pdf, df)
        page_summary_table(pdf, df, years)

    print(f"  ✓ Report saved: {pdf_path.name} (8 pages)")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
        sys.exit(0)