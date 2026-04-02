"""
CAM-ICU indicators (ICU delirium screening) — figures
Reads CSVs produced from SQL (same directory):
  - camicu_compliance.csv       <- camicu_compliance.sql
  - camicu_positivity.csv       <- camicu_positivity.sql
  - camicu_daily_coverage.csv                <- camicu_daily_coverage.sql
  - camicu_daily_coverage_excl_deep_rass.csv <- camicu_daily_coverage_excl_deep_rass.sql

Writes to ./plots/:
  - camicu_compliance_global_by_shift.png
  - camicu_positivity_stacked_by_icu.png
  - camicu_positivity_trend_by_year.png
  - camicu_daily_coverage_by_icu.png
  - camicu_daily_coverage_excl_deep_rass_by_icu.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_YEAR = 2025

UNIT_LABELS = {
    "E014": "ICU E014", "E015": "ICU E015", "E016": "ICU E016",
    "E037": "ICU E037", "E043": "ICU E043", "E057": "ICU E057",
    "E073": "ICU E073", "E103": "ICU E103",
}
SHIFT_LABELS = {
    "M": "Day (8am–3pm)",
    "A": "Evening (3pm–10pm)",
    "N": "Night (10pm–8am)",
}
SHIFT_ORDER = ["M", "A", "N"]
SHIFT_COLORS = {"M": "#0072B2", "A": "#E69F00", "N": "#4B0082"}

UNIT_COLORS = {
    "E014": "#E69F00", "E015": "#56B4E9", "E016": "#009E73",
    "E037": "#F0E442", "E043": "#0072B2", "E057": "#D55E00",
    "E073": "#CC79A7", "E103": "#999999",
}

OUT_COMPLIANCE_GLOBAL = "camicu_compliance_global_by_shift.png"
OUT_POS_STACKED = "camicu_positivity_stacked_by_icu.png"
OUT_POS_TREND = "camicu_positivity_trend_by_year.png"
OUT_DAILY_COVERAGE = "camicu_daily_coverage_by_icu.png"
OUT_DAILY_COVERAGE_EXCL_DEEP_RASS = "camicu_daily_coverage_excl_deep_rass_by_icu.png"


def _require_csv(name: str) -> Path:
    path = BASE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Run: python deliris/run_sql.py deliris/{name.replace('.csv', '.sql')}"
        )
    return path


def load_data():
    compliance = pd.read_csv(_require_csv("camicu_compliance.csv"))
    positivity = pd.read_csv(_require_csv("camicu_positivity.csv"))
    daily_coverage = pd.read_csv(_require_csv("camicu_daily_coverage.csv"))
    daily_excl_deep = pd.read_csv(
        _require_csv("camicu_daily_coverage_excl_deep_rass.csv")
    )
    compliance = compliance[compliance["yr"] <= MAX_YEAR].copy()
    positivity = positivity[positivity["yr"] <= MAX_YEAR].copy()
    daily_coverage = daily_coverage[daily_coverage["yr"] <= MAX_YEAR].copy()
    daily_excl_deep = daily_excl_deep[daily_excl_deep["yr"] <= MAX_YEAR].copy()
    compliance["shift"] = pd.Categorical(
        compliance["shift"], categories=SHIFT_ORDER, ordered=True
    )
    return compliance, positivity, daily_coverage, daily_excl_deep


def plot_compliance_global(compliance: pd.DataFrame) -> None:
    agg_global = (
        compliance.groupby("yr")
        .agg(elig=("eligible_shifts", "sum"), cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg_global["pct"] = 100.0 * agg_global["cam"] / agg_global["elig"]

    agg_shift = (
        compliance.groupby(["yr", "shift"], observed=True)
        .agg(elig=("eligible_shifts", "sum"), cam=("shifts_with_cam", "sum"))
        .reset_index()
    )
    agg_shift["pct"] = 100.0 * agg_shift["cam"] / agg_shift["elig"]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.plot(
        agg_global["yr"], agg_global["pct"],
        color="black", linewidth=2.5, marker="o", markersize=7,
        label="All units", zorder=5,
    )
    for _, row in agg_global.iterrows():
        ax.annotate(
            f"{row['pct']:.0f}%", (row["yr"], row["pct"]),
            textcoords="offset points", xytext=(0, 10),
            ha="center", fontsize=9, fontweight="bold",
        )

    for shift in SHIFT_ORDER:
        sub = agg_shift[agg_shift["shift"] == shift]
        ax.plot(
            sub["yr"], sub["pct"],
            color=SHIFT_COLORS[shift], linewidth=1.5, marker="s",
            markersize=5, linestyle="--", label=SHIFT_LABELS[shift], alpha=0.8,
        )

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("CAM-ICU compliance (%)", fontsize=12)
    ax.set_title(
        "Delirium screening when RASS is in range\n"
        "% of eligible shifts (RASS -3 to +4) with CAM-ICU recorded",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(compliance["yr"].unique()))
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = OUTPUT_DIR / OUT_COMPLIANCE_GLOBAL
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")


def plot_positivity_stacked_by_icu(positivity: pd.DataFrame) -> None:
    max_yr = positivity["yr"].max()
    recent = positivity[
        positivity["yr"].isin([max_yr - 2, max_yr - 1, max_yr])
    ].copy()

    agg = (
        recent.groupby("ou_loc_ref")
        .agg(
            total=("total_cam", "sum"),
            pos=("n_positive", "sum"),
            neg=("n_negative", "sum"),
            oth=("n_other", "sum"),
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

    ax.bar(x, agg["pct_pos"], width, label="Delirium present", color="#D55E00")
    ax.bar(
        x, agg["pct_neg"], width, bottom=agg["pct_pos"],
        label="Delirium absent", color="#009E73",
    )
    ax.bar(
        x, agg["pct_oth"], width,
        bottom=agg["pct_pos"] + agg["pct_neg"],
        label="Other / not assessable", color="#BBBBBB",
    )

    for i, row in agg.reset_index(drop=True).iterrows():
        ax.text(
            i, row["pct_pos"] / 2, f"{row['pct_pos']:.0f}%",
            ha="center", va="center", fontsize=11, fontweight="bold", color="white",
        )
        if row["pct_neg"] > 5:
            ax.text(
                i, row["pct_pos"] + row["pct_neg"] / 2, f"{row['pct_neg']:.0f}%",
                ha="center", va="center", fontsize=10, color="white",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Share (%)", fontsize=12)
    ax.set_title(
        "CAM-ICU result mix by ICU\n"
        f"Stacked distribution ({max_yr - 2}–{max_yr})",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 108)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = OUTPUT_DIR / OUT_POS_STACKED
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")


def plot_positivity_trend_by_year(positivity: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(positivity["ou_loc_ref"].unique()):
        sub = positivity[positivity["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"], sub["pct_positive"],
            color=UNIT_COLORS.get(unit, "#333"), linewidth=2,
            marker="o", markersize=5, label=UNIT_LABELS.get(unit, unit),
        )

    agg = (
        positivity.groupby("yr")
        .agg(total=("total_cam", "sum"), p=("n_positive", "sum"))
        .reset_index()
    )
    agg["pct"] = 100.0 * agg["p"] / agg["total"]
    ax.plot(
        agg["yr"], agg["pct"],
        color="black", linewidth=2.5, marker="D", markersize=7,
        label="All units", zorder=5,
    )

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("CAM-ICU positive (%)", fontsize=12)
    ax.set_title(
        "Share of CAM-ICU records positive for delirium\nby ICU and year",
        fontsize=13, fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(50, 105)
    ax.set_xticks(sorted(positivity["yr"].unique()))
    ax.legend(loc="lower left", fontsize=9, ncol=2, title="Unit", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = OUTPUT_DIR / OUT_POS_TREND
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")


def plot_daily_coverage_by_icu(daily: pd.DataFrame) -> None:
    """
    Share of completed ICU stays with >=1 CAM-ICU on every calendar day of the stay.
    Global curve uses weighted %: sum(n_stays_cam_all_days) / sum(n_stays) by year.
    """
    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(daily["ou_loc_ref"].unique()):
        sub = daily[daily["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"],
            sub["pct_stays_cam_all_days"],
            color=UNIT_COLORS.get(unit, "#333"),
            linewidth=2,
            marker="o",
            markersize=5,
            label=UNIT_LABELS.get(unit, unit),
        )

    agg = (
        daily.groupby("yr")
        .agg(
            n=("n_stays", "sum"),
            ok=("n_stays_cam_all_days", "sum"),
        )
        .reset_index()
    )
    agg["pct"] = np.where(agg["n"] > 0, 100.0 * agg["ok"] / agg["n"], np.nan)
    ax.plot(
        agg["yr"],
        agg["pct"],
        color="black",
        linewidth=2.5,
        marker="D",
        markersize=7,
        label="All units (weighted)",
        zorder=5,
    )

    for _, row in agg.iterrows():
        if pd.notna(row["pct"]):
            ax.annotate(
                f"{row['pct']:.0f}%",
                (row["yr"], row["pct"]),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=9,
                fontweight="bold",
            )

    ax.set_xlabel("Year (admission)", fontsize=12)
    ax.set_ylabel("Stays with daily CAM-ICU (%)", fontsize=12)
    ax.set_title(
        "Completed ICU stays: CAM-ICU recorded at least once on each calendar day\n"
        "of the stay (by unit and year)",
        fontsize=13,
        fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(daily["yr"].unique()))
    ax.legend(loc="upper left", fontsize=9, ncol=2, title="Unit", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = OUTPUT_DIR / OUT_DAILY_COVERAGE
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")


def plot_daily_coverage_excl_deep_rass_by_icu(daily_excl: pd.DataFrame) -> None:
    """
    Share of stays with >=1 CAM-ICU on every evaluable calendar day.
    Evaluable days exclude calendar days with any RASS -5 / -4 (same SQL).
    Weighted aggregate: sum(n_stays_cam_all_evaluable_days)
    / sum(n_stays_with_evaluable_day) by year.
    """
    fig, ax = plt.subplots(figsize=(11, 6))

    for unit in sorted(daily_excl["ou_loc_ref"].unique()):
        sub = daily_excl[daily_excl["ou_loc_ref"] == unit]
        ax.plot(
            sub["yr"],
            sub["pct_stays_cam_all_evaluable_days"],
            color=UNIT_COLORS.get(unit, "#333"),
            linewidth=2,
            marker="o",
            markersize=5,
            label=UNIT_LABELS.get(unit, unit),
        )

    agg = (
        daily_excl.groupby("yr")
        .agg(
            denom=("n_stays_with_evaluable_day", "sum"),
            ok=("n_stays_cam_all_evaluable_days", "sum"),
        )
        .reset_index()
    )
    agg["pct"] = np.where(agg["denom"] > 0, 100.0 * agg["ok"] / agg["denom"], np.nan)
    ax.plot(
        agg["yr"],
        agg["pct"],
        color="black",
        linewidth=2.5,
        marker="D",
        markersize=7,
        label="All units (weighted)",
        zorder=5,
    )

    for _, row in agg.iterrows():
        if pd.notna(row["pct"]):
            ax.annotate(
                f"{row['pct']:.0f}%",
                (row["yr"], row["pct"]),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=9,
                fontweight="bold",
            )

    ax.set_xlabel("Year (admission)", fontsize=12)
    ax.set_ylabel("Stays meeting daily CAM on evaluable days (%)", fontsize=12)
    ax.set_title(
        "Completed ICU stays: CAM-ICU every calendar day after excluding days\n"
        "with RASS -5 or -4 (not assessable). Denominator: stays with ≥1 evaluable day.",
        fontsize=13,
        fontweight="bold",
    )
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0))
    ax.set_ylim(0, 105)
    ax.set_xticks(sorted(daily_excl["yr"].unique()))
    ax.legend(loc="upper left", fontsize=9, ncol=2, title="Unit", title_fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    out = OUTPUT_DIR / OUT_DAILY_COVERAGE_EXCL_DEEP_RASS
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")


def main():
    print("Loading data...")
    compliance, positivity, daily_coverage, daily_excl_deep = load_data()
    print(f"  Compliance rows: {len(compliance)}")
    print(f"  Positivity rows: {len(positivity)}")
    print(f"  Daily coverage rows: {len(daily_coverage)}")
    print(f"  Daily coverage (excl. RASS -5/-4 days) rows: {len(daily_excl_deep)}")

    print("\nGenerating plots...")
    plot_compliance_global(compliance)
    plot_positivity_stacked_by_icu(positivity)
    plot_positivity_trend_by_year(positivity)
    plot_daily_coverage_by_icu(daily_coverage)
    plot_daily_coverage_excl_deep_rass_by_icu(daily_excl_deep)

    print(f"\nPlots directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
