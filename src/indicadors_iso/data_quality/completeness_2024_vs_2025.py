"""Main script: compare completeness of movements and labs between two years.

Usage::

    python data_quality/completeness_2024_vs_2025.py

Prompts for the two years and a YTD cut-off, queries Metabase (9 blocks),
computes deltas + heuristic flags, and writes CSVs and a standalone HTML
report to ``data_quality/output/``.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from indicadors_iso._paths import module_output_dir
from indicadors_iso.connection import execute_query
from indicadors_iso.data_quality import _metrics, _sql
from indicadors_iso.data_quality._report import generate_html


def _parse_years(text: str, default: tuple[int, int]) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return default
    if "," in text:
        a, b = text.split(",", 1)
        return int(a.strip()), int(b.strip())
    if "-" in text:
        a, b = text.split("-", 1)
        return int(a.strip()), int(b.strip())
    y = int(text)
    return y, y + 1


def _prompt(msg: str, default: str) -> str:
    try:
        resp = input(f"{msg} [{default}]: ").strip()
    except EOFError:
        resp = ""
    return resp or default


def _run(template: str, label: str, **fmt_kwargs) -> pd.DataFrame:
    print(f"  -> {label}...", flush=True)
    query = _sql.format_query(template, **fmt_kwargs)
    return execute_query(query, verbose=False)


def main() -> None:
    today = date.today()
    default_y1 = today.year - 2
    default_y2 = today.year - 1

    year_input = _prompt(
        "Anos a comparar (p.ej. 2024,2025)",
        f"{default_y1},{default_y2}",
    )
    y1, y2 = _parse_years(year_input, (default_y1, default_y2))
    if y1 == y2:
        print("Los dos anos no pueden ser iguales.")
        return

    cutoff_input = _prompt(
        "Cutoff YTD (mes-dia) para comparacion justa",
        today.strftime("%m-%d"),
    )
    try:
        mm, dd = cutoff_input.split("-")
        ytd_cutoff_y1 = f"{y1}-{int(mm):02d}-{int(dd):02d}"
        ytd_cutoff_y2 = f"{y2}-{int(mm):02d}-{int(dd):02d}"
    except ValueError:
        print(f"Formato invalido para YTD ({cutoff_input!r}); se usa {today.strftime('%m-%d')}.")
        ytd_cutoff_y1 = f"{y1}-{today.month:02d}-{today.day:02d}"
        ytd_cutoff_y2 = f"{y2}-{today.month:02d}-{today.day:02d}"

    print(f"\nComparando {y1} vs {y2} (YTD cutoff {ytd_cutoff_y1} / {ytd_cutoff_y2})...\n")

    fmt_base = dict(
        y1=y1, y2=y2,
        ytd_cutoff_y1=ytd_cutoff_y1,
        ytd_cutoff_y2=ytd_cutoff_y2,
    )

    raw_totals_mov = _run(_sql.SQL_TOTALS_MOVEMENTS, "totals movements", **fmt_base)
    raw_totals_lab = _run(_sql.SQL_TOTALS_LABS, "totals labs", **fmt_base)
    raw_ytd_mov = _run(_sql.SQL_YTD_MOVEMENTS, "YTD movements", **fmt_base)
    raw_ytd_lab = _run(_sql.SQL_YTD_LABS, "YTD labs", **fmt_base)
    raw_monthly_mov = _run(_sql.SQL_MONTHLY_MOVEMENTS, "monthly movements", **fmt_base)
    raw_monthly_lab = _run(_sql.SQL_MONTHLY_LABS, "monthly labs", **fmt_base)
    raw_daily_mov = _run(_sql.SQL_DAILY_MOVEMENTS, "daily movements", **fmt_base)
    raw_daily_lab = _run(_sql.SQL_DAILY_LABS, "daily labs", **fmt_base)
    raw_ratios_mov = _run(_sql.SQL_RATIOS_MOVEMENTS, "ratios movements", **fmt_base)
    raw_ratios_lab = _run(_sql.SQL_RATIOS_LABS, "ratios labs", **fmt_base)
    raw_orphans = _run(_sql.SQL_ORPHAN_EPISODES, "orphan episodes", **fmt_base)
    raw_load_mov = _run(_sql.SQL_LOAD_FRESHNESS_MOVEMENTS, "load freshness movements", **fmt_base)
    raw_load_lab = _run(_sql.SQL_LOAD_FRESHNESS_LABS, "load freshness labs", **fmt_base)
    raw_breakdown_unit = _run(_sql.SQL_BREAKDOWN_OU_LOC, "breakdown by ou_loc_ref", **fmt_base)
    raw_breakdown_facility = _run(_sql.SQL_BREAKDOWN_FACILITY, "breakdown by facility", **fmt_base)
    raw_breakdown_lab = _run(_sql.SQL_BREAKDOWN_LAB_PARAM, "breakdown by lab_sap_ref", **fmt_base)

    # Numeric coercion where needed
    for df in (raw_totals_mov, raw_totals_lab, raw_ytd_mov, raw_ytd_lab,
               raw_monthly_mov, raw_monthly_lab, raw_ratios_mov, raw_ratios_lab,
               raw_orphans, raw_load_mov, raw_load_lab,
               raw_breakdown_unit, raw_breakdown_facility, raw_breakdown_lab):
        for col in df.select_dtypes(include="object").columns:
            if col in ("yr", "mth", "n_rows", "n_patients", "n_episodes",
                       "n_care_levels", "n_lab_params", "n_orphans",
                       "rows_per_episode"):
                df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Transforms ---
    totals_mov = _metrics.totals_table(raw_totals_mov, y1, y2)
    totals_lab = _metrics.totals_table(raw_totals_lab, y1, y2)
    ytd_mov = _metrics.totals_table(raw_ytd_mov, y1, y2)
    ytd_lab = _metrics.totals_table(raw_ytd_lab, y1, y2)

    monthly_mov_pv = _metrics.monthly_pivot(raw_monthly_mov, y1, y2, "n_rows")
    monthly_lab_pv = _metrics.monthly_pivot(raw_monthly_lab, y1, y2, "n_rows")

    daily_mov = _metrics.daily_series(raw_daily_mov, y1, y2)
    daily_lab = _metrics.daily_series(raw_daily_lab, y1, y2)

    orphans = _metrics.orphan_summary(raw_orphans, y1, y2)

    load_mov = _metrics.load_lag(raw_load_mov, y1, y2)
    load_lab = _metrics.load_lag(raw_load_lab, y1, y2)

    breakdown_unit = _metrics.breakdown_pivot(
        raw_breakdown_unit, y1, y2, "ou_loc_ref", "ou_loc_descr", top_n=25)
    breakdown_facility = _metrics.breakdown_pivot(
        raw_breakdown_facility, y1, y2, "facility", None, top_n=25)
    breakdown_lab = _metrics.breakdown_pivot(
        raw_breakdown_lab, y1, y2, "lab_sap_ref", "lab_descr", top_n=30)

    flags = _metrics.compute_flags(
        y1=y1, y2=y2,
        totals_mov=totals_mov,
        totals_lab=totals_lab,
        ytd_mov=ytd_mov,
        ytd_lab=ytd_lab,
        monthly_mov=monthly_mov_pv,
        monthly_lab=monthly_lab_pv,
        daily_mov=daily_mov,
        daily_lab=daily_lab,
        ratios_mov=raw_ratios_mov,
        ratios_lab=raw_ratios_lab,
        orphans=orphans,
        breakdown_unit=breakdown_unit,
        breakdown_facility=breakdown_facility,
        breakdown_lab=breakdown_lab,
        load_mov=load_mov,
        load_lab=load_lab,
    )

    # --- Output ---
    output_dir = module_output_dir("data_quality")
    tag = f"{y1}_vs_{y2}"

    def _csv(df: pd.DataFrame, name: str) -> None:
        if df is None or df.empty:
            return
        df.to_csv(output_dir / f"completeness_{tag}_{name}.csv",
                  index=True, encoding="utf-8-sig")

    _csv(totals_mov, "totals_mov")
    _csv(totals_lab, "totals_lab")
    _csv(ytd_mov, "ytd_mov")
    _csv(ytd_lab, "ytd_lab")
    _csv(monthly_mov_pv, "monthly_mov")
    _csv(monthly_lab_pv, "monthly_lab")
    _csv(daily_mov, "daily_mov")
    _csv(daily_lab, "daily_lab")
    _csv(orphans, "orphans")
    _csv(load_mov, "load_freshness_mov")
    _csv(load_lab, "load_freshness_lab")
    _csv(breakdown_unit, "breakdown_ou_loc_ref")
    _csv(breakdown_facility, "breakdown_facility")
    _csv(breakdown_lab, "breakdown_lab_sap_ref")
    _csv(raw_ratios_mov, "ratios_mov_raw")
    _csv(raw_ratios_lab, "ratios_lab_raw")

    html_path = output_dir / f"completeness_{tag}.html"
    generate_html(
        y1=y1, y2=y2,
        totals_mov=totals_mov,
        totals_lab=totals_lab,
        ytd_mov=ytd_mov,
        ytd_lab=ytd_lab,
        monthly_mov_pv=monthly_mov_pv,
        monthly_lab_pv=monthly_lab_pv,
        daily_mov=daily_mov,
        daily_lab=daily_lab,
        ratios_mov_raw=raw_ratios_mov,
        ratios_lab_raw=raw_ratios_lab,
        orphans=orphans,
        breakdown_unit=breakdown_unit,
        breakdown_facility=breakdown_facility,
        breakdown_lab=breakdown_lab,
        load_mov=load_mov,
        load_lab=load_lab,
        flags=flags,
        output_path=html_path,
        ytd_cutoff_y1=ytd_cutoff_y1,
        ytd_cutoff_y2=ytd_cutoff_y2,
    )

    print("\nFlags detectados:")
    for f in flags:
        print(f"  [{f['level'].upper():7}] {f['msg']}")
    print(f"\nListo. Archivos guardados en {output_dir}/")
    print(f"  HTML: {html_path}")


if __name__ == "__main__":
    main()
