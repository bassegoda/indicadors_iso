"""Carga la cohorte de nutrición y la prepara para mergear con la
cohorte demográfica.

`load_nutrition_cohort` descarga año a año vía `execute_query_yearly`
(igual que el loader de `sofa`) y devuelve un DataFrame con flags y
horas-a-inicio por estancia (per-unit).

`aggregate_to_predominant` colapsa esa misma tabla a nivel
`[patient_ref, episode_ref]` para alimentar el pipeline predominant-unit
(donde un episodio que recorre E073→I073 es UNA sola fila). El criterio
es:
    - `received_enteral` = OR a nivel episodio
    - `nutr_enteral_start` = MIN entre las estancias del episodio
    - `hours_to_enteral` se recalcula contra la admission_date de la
      cohorte demographic predominant-unit *después* del merge — porque
      la admission_date de la fila predominant-unit puede ser anterior a
      la admission_date de la fila per-unit donde se inició la nutrición
      (p. ej. ingreso por E073 con nutrición iniciada tras pasar a I073).
"""
from __future__ import annotations

import pandas as pd

from indicadors_iso.connection import execute_query_yearly
from indicadors_iso.demographics.nutrition._sql import render_sql

NUTRITION_JOIN_KEYS_PER_UNIT = ["patient_ref", "episode_ref", "ou_loc_ref", "stay_id"]
NUTRITION_JOIN_KEYS_PREDOMINANT = ["patient_ref", "episode_ref"]

# Columnas derivadas que añadimos a la cohorte tras el merge.
NUTRITION_OUTPUT_COLS = [
    "nutr_enteral_start",
    "nutr_parenteral_start",
    "received_enteral",
    "received_parenteral",
    "hours_to_enteral",
    "hours_to_parenteral",
]


def load_nutrition_cohort(
    min_year: int, max_year: int, units: list[str]
) -> pd.DataFrame:
    """Descarga datos de nutrición año a año (per-unit grain)."""
    print(
        f"[nutrition] descargando nutrición año a año desde Metabase "
        f"({min_year}-{max_year}, {list(units)})…"
    )

    df = execute_query_yearly(
        lambda year: render_sql(year, year, units=units),
        min_year,
        max_year,
        label="nutrition",
    )

    if df.empty:
        print("[nutrition] sin filas — saltando.")
        return pd.DataFrame(columns=NUTRITION_JOIN_KEYS_PER_UNIT + NUTRITION_OUTPUT_COLS)

    for col in ("admission_date", "nutr_enteral_start", "nutr_parenteral_start"):
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    df["received_enteral"] = df["nutr_enteral_start"].notna().astype("Int64")
    df["received_parenteral"] = df["nutr_parenteral_start"].notna().astype("Int64")
    df["hours_to_enteral"] = (
        (df["nutr_enteral_start"] - df["admission_date"]).dt.total_seconds() / 3600
    )
    df["hours_to_parenteral"] = (
        (df["nutr_parenteral_start"] - df["admission_date"]).dt.total_seconds() / 3600
    )

    n_ent = int((df["received_enteral"] == 1).sum())
    n_par = int((df["received_parenteral"] == 1).sum())
    print(
        f"[nutrition] {len(df)} estancias con ≥1 prescripción de nutrición: "
        f"{n_ent} enteral | {n_par} parenteral."
    )

    df["stay_id"] = pd.to_numeric(df["stay_id"], errors="coerce").astype("Int64")
    keep = NUTRITION_JOIN_KEYS_PER_UNIT + NUTRITION_OUTPUT_COLS
    return df[keep].copy()


def aggregate_to_predominant(per_unit_df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa a nivel `[patient_ref, episode_ref]`.

    Usado por el pipeline predominant-unit. El primer inicio enteral del
    episodio = `MIN` sobre las estancias del episodio. `hours_to_*` se
    deja como NaN: el pipeline lo recalcula tras el merge usando la
    `admission_date` de la cohorte predominant-unit (que puede diferir
    de la de la fila per-unit donde se inició la nutrición).
    """
    if per_unit_df.empty:
        return pd.DataFrame(
            columns=NUTRITION_JOIN_KEYS_PREDOMINANT
            + ["nutr_enteral_start", "nutr_parenteral_start",
               "received_enteral", "received_parenteral"]
        )

    agg = per_unit_df.groupby(NUTRITION_JOIN_KEYS_PREDOMINANT, as_index=False).agg(
        nutr_enteral_start=("nutr_enteral_start", "min"),
        nutr_parenteral_start=("nutr_parenteral_start", "min"),
    )
    agg["received_enteral"] = agg["nutr_enteral_start"].notna().astype("Int64")
    agg["received_parenteral"] = agg["nutr_parenteral_start"].notna().astype("Int64")
    return agg


def merge_per_unit(
    cohort: pd.DataFrame, nutrition_df: pd.DataFrame
) -> pd.DataFrame:
    """Left-join nutrición sobre cohorte per-unit por las 4 claves."""
    if nutrition_df.empty:
        return cohort

    for k in NUTRITION_JOIN_KEYS_PER_UNIT:
        if k not in cohort.columns:
            print(f"[nutrition] cohort sin columna `{k}` — saltando merge.")
            return cohort

    cohort = cohort.copy()
    cohort["stay_id"] = pd.to_numeric(cohort["stay_id"], errors="coerce").astype("Int64")

    before = len(cohort)
    merged = cohort.merge(
        nutrition_df, on=NUTRITION_JOIN_KEYS_PER_UNIT, how="left"
    )
    n_ent = int((merged["received_enteral"] == 1).sum())
    n_par = int((merged["received_parenteral"] == 1).sum())
    print(
        f"[nutrition] mergeado per-unit: {n_ent} estancias con enteral, "
        f"{n_par} con parenteral (de {before} totales)."
    )
    return merged


def merge_predominant(
    cohort: pd.DataFrame, nutrition_df: pd.DataFrame
) -> pd.DataFrame:
    """Left-join nutrición sobre cohorte predominant-unit por
    `[patient_ref, episode_ref]` y recalcula `hours_to_*` usando la
    `admission_date` de la cohorte (no la del subloader)."""
    if nutrition_df.empty:
        return cohort

    agg = aggregate_to_predominant(nutrition_df)

    cohort = cohort.copy()
    before = len(cohort)
    merged = cohort.merge(agg, on=NUTRITION_JOIN_KEYS_PREDOMINANT, how="left")

    adm = pd.to_datetime(merged["admission_date"], errors="coerce", utc=True)
    ent = pd.to_datetime(merged.get("nutr_enteral_start"), errors="coerce", utc=True)
    par = pd.to_datetime(merged.get("nutr_parenteral_start"), errors="coerce", utc=True)

    # Solo cuenta como nutrición de ESTA estancia si el inicio cae dentro
    # de la ventana [admission_date, effective_discharge_date]. La
    # cohorte predominant-unit puede haber descartado movimientos
    # asignados a otras estancias del mismo episodio (p.ej. una
    # readmisión posterior); filtrar evita atribuirles falsamente la
    # nutrición que se inició en otra estancia del mismo episodio.
    eff = pd.to_datetime(merged["effective_discharge_date"], errors="coerce", utc=True)
    in_window_ent = ent.notna() & (ent >= adm) & (ent <= eff)
    in_window_par = par.notna() & (par >= adm) & (par <= eff)

    merged["nutr_enteral_start"] = ent.where(in_window_ent)
    merged["nutr_parenteral_start"] = par.where(in_window_par)
    merged["received_enteral"] = in_window_ent.astype("Int64")
    merged["received_parenteral"] = in_window_par.astype("Int64")
    merged["hours_to_enteral"] = (
        (merged["nutr_enteral_start"] - adm).dt.total_seconds() / 3600
    )
    merged["hours_to_parenteral"] = (
        (merged["nutr_parenteral_start"] - adm).dt.total_seconds() / 3600
    )

    n_ent = int((merged["received_enteral"] == 1).sum())
    n_par = int((merged["received_parenteral"] == 1).sum())
    print(
        f"[nutrition] mergeado predominant: {n_ent} estancias con enteral, "
        f"{n_par} con parenteral (de {before} totales)."
    )
    return merged
