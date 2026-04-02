"""
CAM-ICU Compliance Visualization
=================================
Reads deliris_rass.csv (output from compliance SQL query) and generates
publication-ready plots for non-technical clinical audiences.

Input columns: ou_loc_ref, yr, shift, eligible_shifts, shifts_with_cam, pct_compliance
Output: PNG plots saved to /root/deliris/plots/
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# -- Config --
INPUT_FILE = Path(__file__).parent / "deliris_rass.csv"
OUTPUT_DIR = Path(__file__).parent / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)

# Friendly unit names for labels
UNIT_LABELS = {
    "E014": "UCI E014",
    "E015": "UCI E015",
    "E016": "UCI E016",
    "E037": "UCI E037",
    "E043": "UCI E043",
    "E057": "UCI E057",
    "E073": "UCI E073",
    "E103": "UCI E103",
}

# Shift display names
SHIFT_LABELS = {"M": "Mañana (8-15h)", "A": "Tarde (15-22h)", "N": "Noche (22-8h)"}
SHIFT_ORDER = ["M", "A", "N"]

# Color palette (colorblind-friendly)
UNIT_COLORS = {
    "E014": "#E69F00",
    "E015": "#56B4E9",
    "E016": "#009E73",
    "E037": "#F0E442",
    "E043": "#0072B2",
    "E057": "#D55E00",
    "E073": "#CC79A7",
    "E103": "#999999",
}

SHIFT_COLORS = {"M": "#0072B2", "A": "#E69F00", "N": "#4B0082"}


def load_data(filepath):
    """Load and validate compliance CSV."""
    df = pd.read_csv(filepath)
    expected = {"ou_loc_ref", "yr", "shift", "eligible_shifts", "shifts_with_cam", "pct_compliance"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["shift"] = pd.Categorical(df["shift"], categories=SHIFT_ORDER, ordered=True)
    df["unit_label"] = df["ou_loc_ref"].map(UNIT_LABELS).fillna(df["ou_loc_ref"])
    return df


def plot_overall_evolution(df):
    """
    Plot 1: Overall compliance trend across all ICUs combined.
    Shows the global picture year by year, broken down by nursing shift.
    """
    # Aggregate across all units
    agg = (
        df.groupby(["yr", "shift"], observed=True)
        .agg(eligible=("eligible_shifts", "sum"), with_cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["with_cam"] / agg["eligible"]

    # Also compute global (all shifts)
    agg_global = (
        df.groupby("yr")
        .agg(eligible=("eligible_shifts", "sum"), with_cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg_global["pct"] = 100.0 * agg_global["with_cam"] / agg_global["eligible"]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Global line (thick)
    ax.plot(
        agg_global["yr"], agg_global["pct"],
        color="black", linewidth=2.5, marker="o", markersize=7,
        label="Global", zorder=5,
    )

    # Per-shift lines (thinner, dashed)
    for shift in SHIFT_ORDER:
        subset = agg[agg["shift"] == shift]
        ax.plot(
            subset["yr"], subset["pct"],
            color=SHIFT_COLORS[shift], linewidth=1.5, marker="s", markersize=5,
            linestyle="--", label=SHIFT_LABELS[shift], alpha=0.8,
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cumplimiento CAM-ICU (%)", fontsize=12)
    ax.set_title(
        "Evolución del registro de delirio (CAM-ICU)\nen todas las UCIs. RASS -3 a +4.",
        fontsize=14, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(agg_global["yr"])
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    # Annotate global values
    for _, row in agg_global.iterrows():
        ax.annotate(
            f"{row['pct']:.0f}%",
            (row["yr"], row["pct"]),
            textcoords="offset points", xytext=(0, 10),
            ha="center", fontsize=9, fontweight="bold",
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_evolucion_global.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: 01_evolucion_global.png")


def plot_evolution_by_unit(df):
    """
    Plot 2: Compliance trend per ICU unit.
    One line per unit, aggregating all shifts.
    """
    # Aggregate across shifts per unit-year
    agg = (
        df.groupby(["yr", "ou_loc_ref"], observed=True)
        .agg(eligible=("eligible_shifts", "sum"), with_cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["with_cam"] / agg["eligible"]
    agg["unit_label"] = agg["ou_loc_ref"].map(UNIT_LABELS).fillna(agg["ou_loc_ref"])

    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(agg["ou_loc_ref"].unique()):
        subset = agg[agg["ou_loc_ref"] == unit]
        color = UNIT_COLORS.get(unit, "#333333")
        ax.plot(
            subset["yr"], subset["pct"],
            color=color, linewidth=2, marker="o", markersize=6,
            label=UNIT_LABELS.get(unit, unit),
        )

    ax.set_xlabel("Año", fontsize=12)
    ax.set_ylabel("Cumplimiento CAM-ICU (%)", fontsize=12)
    ax.set_title(
        "Evolución del registro de delirio (CAM-ICU)\npor unidad de cuidados intensivos. RASS -3 a +4.",
        fontsize=14, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(agg["yr"].unique()))
    ax.legend(
        loc="upper left", fontsize=9, framealpha=0.9,
        ncol=2, title="Unidad", title_fontsize=10,
    )
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_evolucion_por_uci.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: 02_evolucion_por_uci.png")


def plot_shift_heatmap(df):
    """
    Plot 3: Heatmap of compliance by unit and shift (latest 2 full years).
    Gives a snapshot of current performance patterns.
    """
    # Use the two most recent complete years
    max_year = df["yr"].max()
    recent = df[df["yr"].isin([max_year - 1, max_year])].copy()

    # Aggregate the two years together for a stable picture
    agg = (
        recent.groupby(["ou_loc_ref", "shift"], observed=True)
        .agg(eligible=("eligible_shifts", "sum"), with_cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["with_cam"] / agg["eligible"]

    # Pivot for heatmap
    pivot = agg.pivot(index="ou_loc_ref", columns="shift", values="pct")
    pivot = pivot.reindex(columns=SHIFT_ORDER)
    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(8, 6))

    # Color matrix
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)

    # Labels
    ax.set_xticks(range(len(SHIFT_ORDER)))
    ax.set_xticklabels([SHIFT_LABELS[s] for s in SHIFT_ORDER], fontsize=11)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(
        [UNIT_LABELS.get(u, u) for u in pivot.index], fontsize=11,
    )

    # Annotate each cell with percentage
    for i in range(len(pivot.index)):
        for j in range(len(SHIFT_ORDER)):
            val = pivot.values[i, j]
            if np.isnan(val):
                text = "—"
                color = "gray"
            else:
                text = f"{val:.0f}%"
                color = "white" if val < 40 or val > 80 else "black"
            ax.text(j, i, text, ha="center", va="center", fontsize=13, fontweight="bold", color=color)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label("Cumplimiento (%)", fontsize=11)
    cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))

    ax.set_title(
        f"Cumplimiento CAM-ICU por UCI y turno\n({max_year - 1}–{max_year}). RASS -3 a +4.",
        fontsize=14, fontweight="bold",
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_heatmap_uci_turno.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: 03_heatmap_uci_turno.png")


def main():
    print(f"Reading: {INPUT_FILE}")
    df = load_data(INPUT_FILE)
    print(f"  {len(df)} rows | Units: {sorted(df['ou_loc_ref'].unique())} | Years: {sorted(df['yr'].unique())}")

    print("\nGenerating plots...")
    plot_overall_evolution(df)
    plot_evolution_by_unit(df)
    plot_shift_heatmap(df)
    print(f"\nAll plots saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()