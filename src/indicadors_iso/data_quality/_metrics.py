"""Metrics and heuristic flags for the 2024 vs 2025 data-completeness report.

The raw DataFrames produced by ``_sql.py`` queries are transformed here into:

- pivoted year-by-year tables with absolute and percent deltas,
- daily series reindexed to contain every calendar day (gaps become 0),
- ratio series (rows / episode) per month,
- load_date lag (days between last day of the event month and max(load_date)),
- a flat list of heuristic flags (strings) summarising suspicious patterns.

No plotting happens here; see ``_report.py``.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

MONTH_NAMES_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def _parse_naive_dt(series: pd.Series) -> pd.Series:
    """Parse Metabase ISO-8601 timestamps ignoring the trailing timezone offset.

    Metabase returns strings such as ``2024-06-15T08:30:00+02:00`` mixing CET
    and CEST offsets, which breaks ``pd.to_datetime`` (it falls back to object
    dtype). We strip the offset so every value becomes a naive local timestamp
    — safe because we only need calendar dates and month-level lags.
    """
    if series.empty:
        return pd.to_datetime(series, errors="coerce")
    stripped = series.astype(str).str[:19]
    return pd.to_datetime(stripped, errors="coerce")


def _parse_naive_date(series: pd.Series) -> pd.Series:
    """Same as :func:`_parse_naive_dt` but returns ``datetime.date`` objects."""
    return _parse_naive_dt(series).dt.date

# Drop thresholds used to raise heuristic flags.
MONTHLY_DROP_WARNING = 0.25   # month with >25% fewer rows in y2 vs y1
MONTHLY_DROP_ALERT = 0.50     # month with >50% fewer rows
RATIO_DROP_WARNING = 0.15     # rows/episode ratio drop >15%
ORPHAN_WARNING = 0.01         # >1% orphan episodes
UNIT_DROP_ALERT = 0.80        # unit with >80% fewer rows
DAILY_ZERO_ALERT_DAYS = 3     # 3+ consecutive zero-row days
LOAD_LAG_WARNING_DAYS = 45    # max(load_date) more than 45d after month-end is fine
                              # but gaps >LOAD_LAG_WARNING_DAYS between adjacent
                              # months of the same year raise a flag.


# -----------------------------------------------------------------------------
# Totals / YTD
# -----------------------------------------------------------------------------

def totals_table(df: pd.DataFrame, y1: int, y2: int) -> pd.DataFrame:
    """Transpose a totals dataframe so rows are metrics and cols are years+delta."""
    if df.empty:
        return pd.DataFrame()
    df = df.set_index("yr")
    cols = [y1, y2]
    existing = [c for c in cols if c in df.index]
    out = df.loc[existing].T
    out.columns = [str(c) for c in out.columns]
    if str(y1) in out.columns and str(y2) in out.columns:
        v1 = pd.to_numeric(out[str(y1)], errors="coerce")
        v2 = pd.to_numeric(out[str(y2)], errors="coerce")
        out["delta"] = v2 - v1
        with np.errstate(divide="ignore", invalid="ignore"):
            out["delta_pct"] = np.where(v1 > 0, (v2 - v1) / v1 * 100.0, np.nan)
    return out


# -----------------------------------------------------------------------------
# Monthly pivots
# -----------------------------------------------------------------------------

def monthly_pivot(df: pd.DataFrame, y1: int, y2: int,
                  value_col: str = "n_rows") -> pd.DataFrame:
    """Pivot a (yr, mth) dataframe into a 12-row table indexed by month."""
    full_index = pd.Index(range(1, 13), name="mth")
    if df.empty:
        pivot = pd.DataFrame(index=full_index, columns=[y1, y2], dtype=float)
    else:
        pivot = (df.pivot(index="mth", columns="yr", values=value_col)
                   .reindex(full_index))
        for y in (y1, y2):
            if y not in pivot.columns:
                pivot[y] = np.nan
        pivot = pivot[[y1, y2]]
    pivot.index = [MONTH_NAMES_ES[m - 1] for m in pivot.index]
    pivot.index.name = "mes"
    v1 = pivot[y1]
    v2 = pivot[y2]
    pivot["delta"] = v2 - v1
    with np.errstate(divide="ignore", invalid="ignore"):
        pivot["delta_pct"] = np.where(v1 > 0, (v2 - v1) / v1 * 100.0, np.nan)
    return pivot


# -----------------------------------------------------------------------------
# Daily series
# -----------------------------------------------------------------------------

def daily_series(df: pd.DataFrame, y1: int, y2: int) -> pd.DataFrame:
    """Return a (day, n_rows) series with every day from y1-01-01 to y2-12-31.

    Missing days are filled with 0.
    """
    if df.empty:
        return pd.DataFrame(columns=["day", "n_rows", "yr"])
    df = df.copy()
    df["day"] = _parse_naive_date(df["day"])
    df = df.dropna(subset=["day"])
    df["n_rows"] = pd.to_numeric(df["n_rows"], errors="coerce").fillna(0).astype(int)
    df = df.groupby("day", as_index=True)["n_rows"].sum()
    idx = pd.date_range(
        start=date(min(y1, y2), 1, 1),
        end=date(max(y1, y2), 12, 31),
        freq="D",
    ).date
    df = df.reindex(idx, fill_value=0).to_frame()
    df.index.name = "day"
    df = df.reset_index()
    df["yr"] = df["day"].apply(lambda d: d.year)
    df["day_of_year"] = df["day"].apply(lambda d: d.timetuple().tm_yday)
    return df


def zero_day_streaks(daily: pd.DataFrame, year: int) -> list[tuple[date, date, int]]:
    """Return consecutive zero-row streaks (start, end, length) for ``year``."""
    if daily.empty:
        return []
    sub = daily[daily["yr"] == year].sort_values("day").reset_index(drop=True)
    streaks: list[tuple[date, date, int]] = []
    current_start: date | None = None
    current_end: date | None = None
    for _, row in sub.iterrows():
        if row["n_rows"] == 0:
            if current_start is None:
                current_start = row["day"]
            current_end = row["day"]
        else:
            if current_start is not None and current_end is not None:
                length = (current_end - current_start).days + 1
                streaks.append((current_start, current_end, length))
                current_start = None
                current_end = None
    if current_start is not None and current_end is not None:
        length = (current_end - current_start).days + 1
        streaks.append((current_start, current_end, length))
    return streaks


# -----------------------------------------------------------------------------
# Orphan episodes
# -----------------------------------------------------------------------------

def orphan_summary(df: pd.DataFrame, y1: int, y2: int) -> pd.DataFrame:
    """Pivot orphan-episodes dataframe into (episode_type, y1, y2, pct_y1, pct_y2)."""
    if df.empty:
        return pd.DataFrame()
    pv_total = df.pivot(index="episode_type", columns="yr",
                        values="n_episodes").fillna(0)
    pv_orphan = df.pivot(index="episode_type", columns="yr",
                         values="n_orphans").fillna(0)

    for y in (y1, y2):
        if y not in pv_total.columns:
            pv_total[y] = 0
        if y not in pv_orphan.columns:
            pv_orphan[y] = 0

    out = pd.DataFrame(index=pv_total.index)
    out[f"episodes_{y1}"] = pv_total[y1].astype(int)
    out[f"episodes_{y2}"] = pv_total[y2].astype(int)
    out[f"orphans_{y1}"] = pv_orphan[y1].astype(int)
    out[f"orphans_{y2}"] = pv_orphan[y2].astype(int)
    with np.errstate(divide="ignore", invalid="ignore"):
        out[f"pct_orphans_{y1}"] = np.where(
            pv_total[y1] > 0, pv_orphan[y1] / pv_total[y1] * 100.0, np.nan,
        )
        out[f"pct_orphans_{y2}"] = np.where(
            pv_total[y2] > 0, pv_orphan[y2] / pv_total[y2] * 100.0, np.nan,
        )
    return out.reset_index()


# -----------------------------------------------------------------------------
# Load date freshness
# -----------------------------------------------------------------------------

def load_lag(df: pd.DataFrame, y1: int, y2: int) -> pd.DataFrame:
    """Compute days between end of (yr, mth) and max(load_date).

    Negative lag means the data was loaded before the month ended (very rare;
    probably clock skew). Very large lag (>> typical) means the ETL ran stale.
    """
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["max_load_date"] = _parse_naive_dt(df["max_load_date"])
    df["min_load_date"] = _parse_naive_dt(df["min_load_date"])
    df["yr"] = pd.to_numeric(df["yr"], errors="coerce").astype("Int64")
    df["mth"] = pd.to_numeric(df["mth"], errors="coerce").astype("Int64")

    def _month_end(yr: int, mth: int) -> date:
        if mth == 12:
            return date(yr, 12, 31)
        return date(yr, mth + 1, 1) - timedelta(days=1)

    def _safe_month_end(row) -> "date | float":
        if pd.isna(row["yr"]) or pd.isna(row["mth"]):
            return np.nan
        return _month_end(int(row["yr"]), int(row["mth"]))

    df["month_end"] = df.apply(_safe_month_end, axis=1)

    def _lag(row) -> float:
        mload = row["max_load_date"]
        mend = row["month_end"]
        if pd.isna(mload) or not isinstance(mend, date):
            return np.nan
        return (mload.date() - mend).days

    df["lag_days"] = df.apply(_lag, axis=1)
    return df[["yr", "mth", "month_end", "max_load_date", "lag_days", "n_rows"]]


# -----------------------------------------------------------------------------
# Breakdowns (by ou_loc_ref, facility, lab_sap_ref)
# -----------------------------------------------------------------------------

def breakdown_pivot(df: pd.DataFrame, y1: int, y2: int,
                    key_col: str, label_col: str | None = None,
                    top_n: int = 25) -> pd.DataFrame:
    """Pivot a breakdown dataframe and keep the top-N entries by y1+y2 volume.

    ``key_col`` is the grouping column (e.g. ``ou_loc_ref``).
    ``label_col`` (optional) is a descriptive column (e.g. ``ou_loc_descr``);
    if given, the most frequent non-null description is kept.
    """
    if df.empty:
        return pd.DataFrame()
    label_map = None
    if label_col and label_col in df.columns:
        label_map = (df.dropna(subset=[label_col])
                       .groupby(key_col)[label_col]
                       .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else ""))
    pv = (df.pivot_table(index=key_col, columns="yr", values="n_rows",
                         aggfunc="sum", fill_value=0))
    for y in (y1, y2):
        if y not in pv.columns:
            pv[y] = 0
    pv = pv[[y1, y2]].astype(int)
    pv.columns = [f"n_{y1}", f"n_{y2}"]

    pv["delta"] = pv[f"n_{y2}"] - pv[f"n_{y1}"]
    with np.errstate(divide="ignore", invalid="ignore"):
        pv["delta_pct"] = np.where(
            pv[f"n_{y1}"] > 0,
            (pv[f"n_{y2}"] - pv[f"n_{y1}"]) / pv[f"n_{y1}"] * 100.0,
            np.nan,
        )
    pv["total"] = pv[f"n_{y1}"] + pv[f"n_{y2}"]
    pv = pv.sort_values("total", ascending=False).head(top_n)
    if label_map is not None:
        pv.insert(0, "desc", pv.index.map(label_map).fillna(""))
    pv = pv.sort_values("delta_pct", ascending=True)
    pv = pv.drop(columns=["total"])
    return pv.reset_index()


# -----------------------------------------------------------------------------
# Heuristic flags
# -----------------------------------------------------------------------------

def compute_flags(*,
                  y1: int,
                  y2: int,
                  totals_mov: pd.DataFrame,
                  totals_lab: pd.DataFrame,
                  ytd_mov: pd.DataFrame,
                  ytd_lab: pd.DataFrame,
                  monthly_mov: pd.DataFrame,
                  monthly_lab: pd.DataFrame,
                  daily_mov: pd.DataFrame,
                  daily_lab: pd.DataFrame,
                  ratios_mov: pd.DataFrame,
                  ratios_lab: pd.DataFrame,
                  orphans: pd.DataFrame,
                  breakdown_unit: pd.DataFrame,
                  breakdown_facility: pd.DataFrame,
                  breakdown_lab: pd.DataFrame,
                  load_mov: pd.DataFrame,
                  load_lab: pd.DataFrame) -> list[dict]:
    """Generate a list of heuristic flags. Each flag is a dict with:
        level: "info" | "warning" | "alert"
        msg:   short human-readable Spanish message
    """
    flags: list[dict] = []

    def _level_for_pct_drop(drop: float) -> str | None:
        if drop >= MONTHLY_DROP_ALERT:
            return "alert"
        if drop >= MONTHLY_DROP_WARNING:
            return "warning"
        return None

    # Global totals
    def _global_drop(df: pd.DataFrame, label: str) -> None:
        if df.empty or "delta_pct" not in df.columns:
            return
        if "n_rows" not in df.index:
            return
        pct = df.loc["n_rows", "delta_pct"]
        if pd.isna(pct):
            return
        if pct < -MONTHLY_DROP_ALERT * 100:
            flags.append({"level": "alert",
                          "msg": f"{label}: caida global de filas {pct:+.1f}% en {y2} vs {y1}."})
        elif pct < -MONTHLY_DROP_WARNING * 100:
            flags.append({"level": "warning",
                          "msg": f"{label}: caida global de filas {pct:+.1f}% en {y2} vs {y1}."})
        elif pct < -10:
            flags.append({"level": "info",
                          "msg": f"{label}: ligera caida global {pct:+.1f}% en {y2} vs {y1}."})

    _global_drop(totals_mov, "movements (ano completo)")
    _global_drop(totals_lab, "labs (ano completo)")
    _global_drop(ytd_mov, "movements (YTD)")
    _global_drop(ytd_lab, "labs (YTD)")

    # Monthly drops
    def _monthly_drops(df: pd.DataFrame, label: str) -> None:
        if df.empty or "delta_pct" not in df.columns:
            return
        for mes, row in df.iterrows():
            pct = row["delta_pct"]
            if pd.isna(pct):
                continue
            drop = -pct / 100.0
            lvl = _level_for_pct_drop(drop)
            if lvl:
                flags.append({"level": lvl,
                              "msg": f"{label}: {mes} cae {pct:+.1f}% "
                                     f"({int(row[y1])} -> {int(row[y2])})."})

    _monthly_drops(monthly_mov, "movements mensuales")
    _monthly_drops(monthly_lab, "labs mensuales")

    # Ratios (rows/episode)
    def _ratio_drops(df: pd.DataFrame, label: str) -> None:
        if df.empty:
            return
        pv = df.pivot(index="mth", columns="yr", values="rows_per_episode")
        for y in (y1, y2):
            if y not in pv.columns:
                return
        dropped_months = []
        for m, row in pv.iterrows():
            r1 = row.get(y1)
            r2 = row.get(y2)
            if pd.isna(r1) or pd.isna(r2) or r1 <= 0:
                continue
            drop = (r1 - r2) / r1
            if drop >= RATIO_DROP_WARNING:
                dropped_months.append((m, r1, r2, drop))
        if dropped_months:
            n = len(dropped_months)
            lvl = "alert" if n >= 6 else "warning"
            meses = ", ".join(MONTH_NAMES_ES[m - 1] for m, *_ in dropped_months)
            flags.append({"level": lvl,
                          "msg": f"{label}: filas/episodio cae >15% en {n} mes(es) "
                                 f"({meses}) -> sugiere falta de filas hijas."})

    _ratio_drops(ratios_mov, "movements")
    _ratio_drops(ratios_lab, "labs")

    # Orphans
    if not orphans.empty:
        for _, row in orphans.iterrows():
            pct = row.get(f"pct_orphans_{y2}")
            if pd.isna(pct):
                continue
            if pct / 100.0 > ORPHAN_WARNING:
                lvl = "alert" if pct > 5 else "warning"
                flags.append({
                    "level": lvl,
                    "msg": f"episodios {row['episode_type']} en {y2} sin movements: "
                           f"{int(row[f'orphans_{y2}'])} / {int(row[f'episodes_{y2}'])} "
                           f"({pct:.1f}%).",
                })

    # Daily zero streaks
    def _zero_streaks(daily: pd.DataFrame, label: str) -> None:
        if daily.empty:
            return
        for y in (y1, y2):
            streaks = zero_day_streaks(daily, y)
            long_streaks = [s for s in streaks if s[2] >= DAILY_ZERO_ALERT_DAYS]
            if long_streaks:
                lvl = "alert" if y == y2 else "warning"
                worst = max(long_streaks, key=lambda t: t[2])
                flags.append({
                    "level": lvl,
                    "msg": f"{label} {y}: {len(long_streaks)} racha(s) de "
                           f">={DAILY_ZERO_ALERT_DAYS} dias sin filas; peor: "
                           f"{worst[0]} a {worst[1]} ({worst[2]} dias).",
                })

    _zero_streaks(daily_mov, "movements diarios")
    _zero_streaks(daily_lab, "labs diarios")

    # Unit / facility / lab parameter drops
    def _unit_drops(df: pd.DataFrame, key_col: str, label: str) -> None:
        if df.empty or "delta_pct" not in df.columns:
            return
        col_y1 = f"n_{y1}"
        severe = df[(df[col_y1] >= 100) & (df["delta_pct"] <= -UNIT_DROP_ALERT * 100)]
        if not severe.empty:
            top = severe.head(5)
            for _, row in top.iterrows():
                flags.append({
                    "level": "alert",
                    "msg": f"{label} '{row[key_col]}' con caida "
                           f"{row['delta_pct']:+.0f}% "
                           f"({int(row[col_y1])} -> {int(row[f'n_{y2}'])}).",
                })

    _unit_drops(breakdown_unit, "ou_loc_ref", "unidad fisica")
    _unit_drops(breakdown_facility, "facility", "facility")
    _unit_drops(breakdown_lab, "lab_sap_ref", "parametro lab")

    # Load date freshness anomalies per year
    def _load_freshness(df: pd.DataFrame, label: str) -> None:
        if df.empty:
            return
        for y in (y1, y2):
            sub = df[df["yr"] == y]
            if sub.empty:
                continue
            latest = sub["max_load_date"].max()
            if pd.isna(latest):
                continue
            today = pd.Timestamp.today().normalize()
            age_days = (today - latest).days
            if age_days > 60:
                lvl = "alert" if age_days > 120 else "warning"
                flags.append({
                    "level": lvl,
                    "msg": f"{label} {y}: ultima load_date = "
                           f"{latest.date()} ({age_days} dias atras) -> "
                           f"posible ETL detenido.",
                })

    _load_freshness(load_mov, "movements")
    _load_freshness(load_lab, "labs")

    if not flags:
        flags.append({"level": "info",
                      "msg": "No se detectan anomalias claras en las heuristicas configuradas."})
    return flags
