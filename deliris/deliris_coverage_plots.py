"""
Delirium Monitoring in ICU — Comprehensive Visualization
==========================================================
Reads three CSVs and generates publication-ready plots telling the full story:
  1. RASS coverage (is sedation being assessed?)
  2. CAM-ICU compliance (when RASS is eligible, is delirium screened?)
  3. CAM-ICU positivity (what proportion of screenings are positive?)

Input files (same directory as script):
  - deliris_rass_coverage.csv
  - deliris_compliance.csv
  - deliris_positivity.csv

Output: PNG plots saved to ./plots/
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# -- Config --
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_YEAR = 2025  # Exclude partial years beyond this

# Friendly labels
UNIT_LABELS = {
    "E014": "UCI E014", "E015": "UCI E015", "E016": "UCI E016",
    "E037": "UCI E037", "E043": "UCI E043", "E057": "UCI E057",
    "E073": "UCI E073", "E103": "UCI E103",
}
SHIFT_LABELS = {"M": "Mañana (8-15h)", "A": "Tarde (15-22h)", "N": "Noche (22-8h)"}
SHIFT_ORDER = ["M", "A", "N"]
SHIFT_COLORS = {"M": "#0072B2", "A": "#E69F00", "N": "#4B0082"}

# Colorblind-friendly palette
UNIT_COLORS = {
    "E014": "#E69F00", "E015": "#56B4E9", "E016": "#009E73",
    "E037": "#F0E442", "E043": "#0072B2", "E057": "#D55E00",
    "E073": "#CC79A7", "E103": "#999999",
}


def load_all():
    """Load, validate and clean the three input CSVs."""
    coverage = pd.read_csv(BASE_DIR / "deliris_rass_coverage.csv")
    compliance = pd.read_csv(BASE_DIR / "deliris_compliance.csv")
    positivity = pd.read_csv(BASE_DIR / "deliris_positivity.csv")

    # Filter year range
    coverage = coverage[coverage["yr"] <= MAX_YEAR].copy()
    compliance = compliance[compliance["yr"] <= MAX_YEAR].copy()
    positivity = positivity[positivity["yr"] <= MAX_YEAR].copy()

    compliance["shift"] = pd.Categorical(
        compliance["shift"], categories=SHIFT_ORDER, ordered=True
    )
    return coverage, compliance, positivity


# =========================================================================
# PLOT 1: RASS coverage — global evolution
# =========================================================================
def plot_rass_coverage_global(cov):
    """Overall RASS coverage trend across all ICUs."""
    agg = (
        cov.groupby("yr")
        .agg(theo=("total_theoretical", "sum"), rass=("total_with_rass", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["rass"] / agg["theo"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(agg["yr"], agg["pct"], color="#0072B2", linewidth=2.5, marker="o", markersize=8)

    for _, row in agg.iterrows():
        ax.annotate(
            f"{row['pct']:.0f}%", (row["yr"], row["pct"]),
            textcoords="offset points", xytext=(0, 12),
            ha="center", fontsize=10, fontweight="bold",
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cobertura RASS (%)", fontsize=12)
    ax.set_title(
        "¿Se evalúa la sedación (RASS) en las UCIs?\n"
        "% de turnos teóricos con al menos un RASS registrado",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(agg["yr"])
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_rass_cobertura_global.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 01_rass_cobertura_global.png")


# =========================================================================
# PLOT 2: RASS coverage — by UCI
# =========================================================================
def plot_rass_coverage_by_unit(cov):
    """RASS coverage trend per ICU."""
    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(cov["ou_loc_ref"].unique()):
        sub = cov[cov["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"], sub["pct_rass_coverage"],
            color=UNIT_COLORS.get(unit, "#333"), linewidth=2,
            marker="o", markersize=5, label=UNIT_LABELS.get(unit, unit),
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cobertura RASS (%)", fontsize=12)
    ax.set_title(
        "Cobertura de la evaluación de sedación (RASS)\npor unidad de cuidados intensivos",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(cov["yr"].unique()))
    ax.legend(loc="upper left", fontsize=9, ncol=2, title="Unidad", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_rass_cobertura_por_uci.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 02_rass_cobertura_por_uci.png")


# =========================================================================
# PLOT 3: CAM-ICU compliance — global by shift
# =========================================================================
def plot_compliance_global(comp):
    """Overall CAM-ICU compliance trend, broken down by nursing shift."""
    agg_global = (
        comp.groupby("yr")
        .agg(elig=("eligible_shifts", "sum"), cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg_global["pct"] = 100.0 * agg_global["cam"] / agg_global["elig"]

    agg_shift = (
        comp.groupby(["yr", "shift"], observed=True)
        .agg(elig=("eligible_shifts", "sum"), cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg_shift["pct"] = 100.0 * agg_shift["cam"] / agg_shift["elig"]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Global line
    ax.plot(
        agg_global["yr"], agg_global["pct"],
        color="black", linewidth=2.5, marker="o", markersize=7,
        label="Global", zorder=5,
    )
    for _, row in agg_global.iterrows():
        ax.annotate(
            f"{row['pct']:.0f}%", (row["yr"], row["pct"]),
            textcoords="offset points", xytext=(0, 10),
            ha="center", fontsize=9, fontweight="bold",
        )

    # Shift lines
    for shift in SHIFT_ORDER:
        sub = agg_shift[agg_shift["shift"] == shift]
        ax.plot(
            sub["yr"], sub["pct"],
            color=SHIFT_COLORS[shift], linewidth=1.5, marker="s",
            markersize=5, linestyle="--", label=SHIFT_LABELS[shift], alpha=0.8,
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cumplimiento CAM-ICU (%)", fontsize=12)
    ax.set_title(
        "¿Se evalúa el delirio cuando corresponde?\n"
        "% de turnos con RASS elegible (-3 a +4) que tienen CAM-ICU registrado",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(comp["yr"].unique()))
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_camicu_compliance_global.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 03_camicu_compliance_global.png")


# =========================================================================
# PLOT 4: CAM-ICU compliance — by UCI
# =========================================================================
def plot_compliance_by_unit(comp):
    """CAM-ICU compliance trend per ICU (all shifts aggregated)."""
    agg = (
        comp.groupby(["yr", "ou_loc_ref"], observed=True)
        .agg(elig=("eligible_shifts", "sum"), cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["cam"] / agg["elig"]

    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(agg["ou_loc_ref"].unique()):
        sub = agg[agg["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"], sub["pct"],
            color=UNIT_COLORS.get(unit, "#333"), linewidth=2,
            marker="o", markersize=5, label=UNIT_LABELS.get(unit, unit),
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cumplimiento CAM-ICU (%)", fontsize=12)
    ax.set_title(
        "Cumplimiento del registro de delirio (CAM-ICU)\npor unidad de cuidados intensivos",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(agg["yr"].unique()))
    ax.legend(loc="upper left", fontsize=9, ncol=2, title="Unidad", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "04_camicu_compliance_por_uci.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 04_camicu_compliance_por_uci.png")


# =========================================================================
# PLOT 5: CAM-ICU positivity — stacked bar by UCI (recent years)
# =========================================================================
def plot_positivity_by_unit(pos):
    """Stacked bar: positive vs negative CAM-ICU per unit (last 3 years)."""
    max_yr = pos["yr"].max()
    recent = pos[pos["yr"].isin([max_yr - 2, max_yr - 1, max_yr])].copy()

    agg = (
        recent.groupby("ou_loc_ref")
        .agg(
            total=("total_cam", "sum"), pos=("n_positive", "sum"),
            neg=("n_negative", "sum"), oth=("n_other", "sum"),
        )
        .reset_index()
    )
    agg["pct_pos"] = 100.0 * agg["pos"] / agg["total"]
    agg["pct_neg"] = 100.0 * agg["neg"] / agg["total"]
    agg["pct_oth"] = 100.0 * agg["oth"] / agg["total"]
    agg = agg.sort_values("ou_loc_ref")

    labels = [UNIT_LABELS.get(u, u) for u in agg["ou_loc_ref"]]
    x = np.arange(len(labels))
    width = 0.6

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.bar(x, agg["pct_pos"], width, label="Delirio presente", color="#D55E00")
    ax.bar(x, agg["pct_neg"], width, bottom=agg["pct_pos"],
           label="Delirio ausente", color="#009E73")
    ax.bar(x, agg["pct_oth"], width, bottom=agg["pct_pos"] + agg["pct_neg"],
           label="Otros / no valorable", color="#BBBBBB")

    # Annotate positive %
    for i, row in agg.reset_index(drop=True).iterrows():
        ax.text(
            i, row["pct_pos"] / 2, f"{row['pct_pos']:.0f}%",
            ha="center", va="center", fontsize=11, fontweight="bold", color="white",
        )
        # Annotate negative % if visible
        if row["pct_neg"] > 5:
            ax.text(
                i, row["pct_pos"] + row["pct_neg"] / 2, f"{row['pct_neg']:.0f}%",
                ha="center", va="center", fontsize=10, color="white",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Proporción (%)", fontsize=12)
    ax.set_title(
        f"¿Qué se registra cuando se hace el CAM-ICU?\n"
        f"Distribución de resultados por UCI ({max_yr - 2}–{max_yr})",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 108)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "05_camicu_positividad_por_uci.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 05_camicu_positividad_por_uci.png")


# =========================================================================
# PLOT 6: CAM-ICU positivity — temporal evolution
# =========================================================================
def plot_positivity_evolution(pos):
    """Positivity rate evolution per UCI over time."""
    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(pos["ou_loc_ref"].unique()):
        sub = pos[pos["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"], sub["pct_positive"],
            color=UNIT_COLORS.get(unit, "#333"), linewidth=2,
            marker="o", markersize=5, label=UNIT_LABELS.get(unit, unit),
        )

    # Global aggregate
    agg = (
        pos.groupby("yr")
        .agg(total=("total_cam", "sum"), p=("n_positive", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["p"] / agg["total"]
    ax.plot(
        agg["yr"], agg["pct"],
        color="black", linewidth=2.5, marker="D", markersize=7,
        label="Global", zorder=5,
    )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("CAM-ICU positivo (%)", fontsize=12)
    ax.set_title(
        "Proporción de registros CAM-ICU positivos (delirio presente)\npor UCI y año",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(50, 105)
    ax.set_xticks(sorted(pos["yr"].unique()))
    ax.legend(loc="lower left", fontsize=9, ncol=2, title="Unidad", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "06_camicu_positividad_evolucion.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: 06_camicu_positividad_evolucion.png")


# =========================================================================
# MAIN
# =========================================================================
def main():
    print("Loading data...")
    coverage, compliance, positivity = load_all()
    print(f"  Coverage:   {len(coverage)} rows")
    print(f"  Compliance: {len(compliance)} rows")
    print(f"  Positivity: {len(positivity)} rows")

    print("\nGenerating plots...")
    plot_rass_coverage_global(coverage)
    plot_rass_coverage_by_unit(coverage)
    plot_compliance_global(compliance)
    plot_compliance_by_unit(compliance)
    plot_positivity_by_unit(positivity)
    plot_positivity_evolution(positivity)

    print(f"\nAll plots saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()