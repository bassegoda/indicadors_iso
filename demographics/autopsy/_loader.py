"""Loader y mergers para indicadores de autopsia/necropsia."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from demographics.autopsy._sql import render_sql

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTOPSY_JOIN_KEYS_PER_UNIT = ["patient_ref", "episode_ref", "ou_loc_ref", "stay_id"]
AUTOPSY_JOIN_KEYS_PREDOMINANT = ["patient_ref", "episode_ref"]

AUTOPSY_OUTPUT_COLS = [
    "first_autopsy_date",
    "received_autopsy",
]


def load_autopsy_cohort(
    min_year: int, max_year: int, units: list[str]
) -> pd.DataFrame:
    """Descarga año a año las autopsias/necropsias ligadas a estancias
    de la cohorte (per-unit grain).
    """
    print(
        f"[autopsy] descargando autopsias/necropsias año a año desde Metabase "
        f"({min_year}-{max_year}, {list(units)})…"
    )
    sys.path.insert(0, str(_REPO_ROOT))
    from connection import execute_query_yearly

    df = execute_query_yearly(
        lambda year: render_sql(year, year, units=units),
        min_year,
        max_year,
        label="autopsy",
    )

    if df.empty:
        print("[autopsy] sin filas — saltando.")
        return pd.DataFrame(
            columns=AUTOPSY_JOIN_KEYS_PER_UNIT + AUTOPSY_OUTPUT_COLS
        )

    df["first_autopsy_date"] = pd.to_datetime(
        df["first_autopsy_date"], errors="coerce", utc=True
    )
    df["received_autopsy"] = df["first_autopsy_date"].notna().astype("Int64")
    df["stay_id"] = pd.to_numeric(df["stay_id"], errors="coerce").astype("Int64")

    n_stays = int((df["received_autopsy"] == 1).sum())
    n_episodes = df["episode_ref"].nunique()
    print(
        f"[autopsy] {n_stays} estancias ligadas a ≥1 autopsia "
        f"({n_episodes} episodios distintos)."
    )

    keep = AUTOPSY_JOIN_KEYS_PER_UNIT + AUTOPSY_OUTPUT_COLS
    return df[keep].copy()


def aggregate_to_predominant(per_unit_df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa a `[patient_ref, episode_ref]` para predominant-unit.

    Una autopsia ligada a varias estancias del mismo episodio se cuenta
    una sola vez con la fecha más temprana.
    """
    if per_unit_df.empty:
        return pd.DataFrame(
            columns=AUTOPSY_JOIN_KEYS_PREDOMINANT
            + ["first_autopsy_date", "received_autopsy"]
        )

    agg = per_unit_df.groupby(AUTOPSY_JOIN_KEYS_PREDOMINANT, as_index=False).agg(
        first_autopsy_date=("first_autopsy_date", "min"),
    )
    agg["received_autopsy"] = agg["first_autopsy_date"].notna().astype("Int64")
    return agg


def merge_per_unit(
    cohort: pd.DataFrame, autopsy_df: pd.DataFrame
) -> pd.DataFrame:
    if autopsy_df.empty:
        cohort = cohort.copy()
        cohort["received_autopsy"] = 0
        return cohort

    for k in AUTOPSY_JOIN_KEYS_PER_UNIT:
        if k not in cohort.columns:
            print(f"[autopsy] cohort sin columna `{k}` — saltando merge.")
            return cohort

    cohort = cohort.copy()
    cohort["stay_id"] = pd.to_numeric(cohort["stay_id"], errors="coerce").astype("Int64")

    before = len(cohort)
    merged = cohort.merge(autopsy_df, on=AUTOPSY_JOIN_KEYS_PER_UNIT, how="left")
    merged["received_autopsy"] = (
        pd.to_numeric(merged["received_autopsy"], errors="coerce")
        .fillna(0)
        .astype("Int64")
    )
    n = int((merged["received_autopsy"] == 1).sum())
    print(
        f"[autopsy] mergeado per-unit: {n} estancias con autopsia "
        f"(de {before} totales)."
    )
    return merged


def merge_predominant(
    cohort: pd.DataFrame, autopsy_df: pd.DataFrame
) -> pd.DataFrame:
    """Left-join autopsia sobre cohorte predominant-unit por
    `[patient_ref, episode_ref]` y filtra a la ventana de la estancia.
    """
    if autopsy_df.empty:
        cohort = cohort.copy()
        cohort["received_autopsy"] = 0
        return cohort

    agg = aggregate_to_predominant(autopsy_df)

    cohort = cohort.copy()
    before = len(cohort)
    merged = cohort.merge(agg, on=AUTOPSY_JOIN_KEYS_PREDOMINANT, how="left")

    adm = pd.to_datetime(merged["admission_date"], errors="coerce", utc=True)
    autopsy_dt = pd.to_datetime(
        merged.get("first_autopsy_date"), errors="coerce", utc=True
    )

    # Solo cuenta como autopsia de ESTA estancia si su fecha es posterior
    # al ingreso de la estancia. Sin upper bound: la autopsia suele
    # registrarse días/semanas después del éxitus.
    in_window = autopsy_dt.notna() & (autopsy_dt >= adm)
    merged["first_autopsy_date"] = autopsy_dt.where(in_window)
    merged["received_autopsy"] = in_window.astype("Int64")

    n = int((merged["received_autopsy"] == 1).sum())
    print(
        f"[autopsy] mergeado predominant: {n} estancias con autopsia "
        f"(de {before} totales)."
    )
    return merged
