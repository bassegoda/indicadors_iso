"""Cargador de cohorte para demographics.

Workaround temporal (1) — Snapshot CSV:
    La conexión Metabase API desde Python está limitando los resultados
    a 2000 filas. Como salida temporal, los pipelines (`predominant_unit`
    y `per_unit`) cargan un snapshot CSV generado manualmente desde la
    web de Metabase usando su `cohort_query_2019-2025.sql`. Si el CSV no
    existe se hace fallback a `connection.execute_query` con la plantilla
    SQL pasada por el script.

Workaround temporal (2) — Augmentación sintética 2025:
    La BBDD dejó de cargar a finales de 2025, por lo que falta Nov-Dic.
    Para mantener un reporting visualmente comparable con 2024 (año
    completo), se rellena 2025 mediante bootstrap-sampling sobre las
    estancias 2025 reales. El **objetivo de filas** es la **media de los
    tres años previos** (2022-2024 cuando se reporta 2025). Si el
    cohort tiene varias unidades y se pasa `synthetic_group_col`,
    el target se calcula y aplica por grupo (p.ej. una media propia para
    E073 y otra para I073).

    Las filas sintéticas:
      - Llevan `patient_ref` / `episode_ref` con prefijo "SYN2025-…"
        para no colisionar con los reales.
      - Mantienen idénticas todas las variables clínicas (edad, sexo,
        AISBE, cirrosis, procedencia, etc.) → proporciones preservadas.
      - Reubican `admission_date` aleatoria en `SYNTHETIC_DATE_RANGE`
        (Nov-Dic 2025 por defecto).
      - Desplazan `exitus_date` por el mismo delta que la admisión, así
        las cuentas de mortalidad 30/90 d siguen coherentes.
      - Marcan `still_admitted = "No"` y `synthetic = True`.

    Cuando lleguen los datos reales: regenerar el snapshot. Si el
    `n_real >= target`, el loader avisa y no inyecta nada.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Augmentación sintética 2025 — TEMPORAL
# ---------------------------------------------------------------------------
SYNTHETIC_DATE_RANGE = (
    datetime(2025, 11, 1),
    datetime(2025, 12, 31, 23, 59, 59),
)
SYNTHETIC_RANDOM_SEED = 42
SYNTHETIC_YEAR = 2025
SYNTHETIC_LOOKBACK_YEARS = 3  # promedio sobre los 3 años previos


# ---------------------------------------------------------------------------
# Loader principal
# ---------------------------------------------------------------------------
def load_cohort(
    snapshot_path: Path,
    min_year: int,
    max_year: int,
    sql_template: Optional[str] = None,
    synthetic_group_col: Optional[str] = None,
) -> pd.DataFrame:
    """Carga la cohorte desde el snapshot CSV (o cae al fallback SQL).

    Tras filtrar por años, si el rango incluye 2025 aplica la
    augmentación sintética con target = media de las estancias en
    `SYNTHETIC_LOOKBACK_YEARS` años previos.

    Args:
        snapshot_path: ruta al CSV exportado de Metabase.
        min_year, max_year: rango de filtrado por `year_admission`.
        sql_template: plantilla SQL con `{min_year}`/`{max_year}` para el
            fallback cuando el snapshot no existe.
        synthetic_group_col: si se pasa (p.ej. "ou_loc_ref"), el target y
            el bootstrap se calculan por grupo. Si es None, se aplican de
            forma global a toda la cohorte 2025.
    """
    if snapshot_path.exists():
        print(f"[loader] Usando snapshot local: {snapshot_path.name}")
        df_full = pd.read_csv(snapshot_path)

        if "year_admission" not in df_full.columns:
            raise ValueError(
                f"El snapshot {snapshot_path.name} no contiene 'year_admission'. "
                "Regenerar con la SQL correspondiente."
            )

        year_col = pd.to_numeric(df_full["year_admission"], errors="coerce")
        mask = (year_col >= min_year) & (year_col <= max_year)
        df = df_full.loc[mask].copy()
        print(
            f"[loader] {len(df)} filas tras filtrar por años "
            f"{min_year}-{max_year} (de {len(df_full)} totales)."
        )

        if min_year <= SYNTHETIC_YEAR <= max_year:
            target = compute_3y_mean_target(
                df_full,
                year_now=SYNTHETIC_YEAR,
                n_years=SYNTHETIC_LOOKBACK_YEARS,
                group_col=synthetic_group_col,
            )
            df = augment_synthetic_2025(
                df, target=target, group_col=synthetic_group_col
            )
        return df

    if sql_template is None:
        raise FileNotFoundError(
            f"Snapshot {snapshot_path} no existe y no se pasó `sql_template` para hacer fallback."
        )

    print(
        f"[loader] Snapshot {snapshot_path.name} no encontrado: "
        "ejecutando query contra Metabase…"
    )
    sys.path.insert(0, str(_REPO_ROOT))
    from connection import execute_query

    return execute_query(sql_template.format(min_year=min_year, max_year=max_year))


# ---------------------------------------------------------------------------
# Cálculo de target sintético
# ---------------------------------------------------------------------------
def compute_3y_mean_target(
    df: pd.DataFrame,
    year_now: int = SYNTHETIC_YEAR,
    n_years: int = SYNTHETIC_LOOKBACK_YEARS,
    group_col: Optional[str] = None,
) -> Union[int, dict]:
    """Devuelve el número objetivo de estancias para `year_now`.

    Calcula la media de filas/año en la ventana [year_now-n_years,
    year_now-1]. Si `group_col` está definido, devuelve un dict
    {valor_grupo: target_int}.
    """
    years_to_avg = list(range(year_now - n_years, year_now))
    year_col = pd.to_numeric(df["year_admission"], errors="coerce")
    src = df.loc[year_col.isin(years_to_avg)]

    if group_col is not None and group_col in df.columns:
        targets: dict[str, int] = {}
        for value, group in src.groupby(group_col):
            counts = group.groupby("year_admission").size()
            present = counts.reindex(years_to_avg, fill_value=0)
            targets[str(value)] = int(round(present.mean())) if len(present) else 0
        return targets

    counts = src.groupby("year_admission").size()
    present = counts.reindex(years_to_avg, fill_value=0)
    return int(round(present.mean())) if len(present) else 0


# ---------------------------------------------------------------------------
# Augmentación sintética
# ---------------------------------------------------------------------------
def augment_synthetic_2025(
    df: pd.DataFrame,
    target: Union[int, dict],
    group_col: Optional[str] = None,
    seed: int = SYNTHETIC_RANDOM_SEED,
) -> pd.DataFrame:
    """Bootstrap-sampling de estancias 2025 para rellenar Nov-Dic.

    No modifica el CSV en disco. Las filas sintéticas son copias de filas
    reales 2025 con IDs y fechas reescritas; preservan todas las
    variables clínicas. Si `target` es dict y `group_col` está definido,
    aplica el target por grupo (p.ej. 'E073' y 'I073' por separado).
    """
    if "year_admission" not in df.columns:
        return df

    year_col = pd.to_numeric(df["year_admission"], errors="coerce")
    mask_2025 = year_col == SYNTHETIC_YEAR

    if "synthetic" not in df.columns:
        df = df.copy()
        df["synthetic"] = False

    if not mask_2025.any():
        if isinstance(target, dict):
            total = sum(target.values())
        else:
            total = int(target or 0)
        if total > 0:
            print(
                "[loader] 2025 vacío en el snapshot; no hay filas plantilla "
                "para hacer bootstrap. Se omite la augmentación."
            )
        return df

    src_full_2025 = df.loc[mask_2025].reset_index(drop=True)

    chunks: list[pd.DataFrame] = [df]
    total_added = 0
    summary_parts: list[str] = []

    if isinstance(target, dict):
        if group_col is None or group_col not in df.columns:
            raise ValueError(
                "augment_synthetic_2025: target es dict pero `group_col` no está definido."
            )
        for grp_value, grp_target in target.items():
            grp_src = src_full_2025[src_full_2025[group_col].astype(str) == str(grp_value)]
            n_real = len(grp_src)
            n_needed = max(int(grp_target) - n_real, 0)
            summary_parts.append(f"{grp_value}: {n_real}→{n_real + n_needed}")
            if n_needed == 0 or n_real == 0:
                continue
            chunks.append(_make_synthetic_rows(grp_src, n_needed, seed + hash(str(grp_value)) % 10000))
            total_added += n_needed
    else:
        n_real = len(src_full_2025)
        n_needed = max(int(target or 0) - n_real, 0)
        summary_parts.append(f"global: {n_real}→{n_real + n_needed}")
        if n_needed > 0:
            chunks.append(_make_synthetic_rows(src_full_2025, n_needed, seed))
            total_added = n_needed

    if total_added == 0:
        print(
            f"[loader] 2025 ya cumple el target ({'; '.join(summary_parts)}); "
            "sin augmentación."
        )
        return df

    out = pd.concat(chunks, ignore_index=True)
    print(
        f"[loader] AUGMENTACION SINTETICA 2025: +{total_added} filas "
        f"({'; '.join(summary_parts)})."
    )
    print(
        "[loader]   ! datos sinteticos para Nov-Dic 2025 - "
        "regenerar el snapshot con datos reales cuando esten disponibles."
    )
    return out


def _make_synthetic_rows(
    template_df: pd.DataFrame, n_needed: int, seed: int
) -> pd.DataFrame:
    """Bootstrap-sampling sobre `template_df` produciendo `n_needed` filas."""
    synth = template_df.sample(
        n=n_needed, replace=True, random_state=seed
    ).reset_index(drop=True)

    rng = random.Random(seed)
    start, end = SYNTHETIC_DATE_RANGE
    span_seconds = int((end - start).total_seconds())

    new_admissions = [
        start + timedelta(seconds=rng.randint(0, span_seconds))
        for _ in range(n_needed)
    ]

    hours_stay = (
        pd.to_numeric(synth["hours_stay"], errors="coerce")
        .fillna(0)
        .astype(int)
        .tolist()
    )
    new_discharges = [
        adm + timedelta(hours=h) for adm, h in zip(new_admissions, hours_stay)
    ]

    src_admission_dt = pd.to_datetime(synth["admission_date"], errors="coerce", utc=True)
    src_exitus_dt = pd.to_datetime(synth["exitus_date"], errors="coerce", utc=True)
    delta_exitus = src_exitus_dt - src_admission_dt

    new_exitus_strs: list[Optional[str]] = []
    for adm, d in zip(new_admissions, delta_exitus):
        if pd.isna(d):
            new_exitus_strs.append(None)
        else:
            new_exitus_strs.append((adm + d.to_pytimedelta()).strftime("%Y-%m-%d"))

    synth["patient_ref"] = [f"SYN2025-{i:05d}" for i in range(n_needed)]
    synth["episode_ref"] = [f"SYN2025E-{i:05d}" for i in range(n_needed)]
    synth["stay_id"] = 1
    synth["admission_date"] = [adm.strftime("%Y-%m-%dT%H:%M:%S") for adm in new_admissions]
    synth["discharge_date"] = [d.strftime("%Y-%m-%dT%H:%M:%S") for d in new_discharges]
    synth["effective_discharge_date"] = [
        d.strftime("%Y-%m-%dT%H:%M:%S+01:00") for d in new_discharges
    ]
    synth["still_admitted"] = "No"
    synth["year_admission"] = SYNTHETIC_YEAR
    synth["exitus_date"] = new_exitus_strs
    synth["synthetic"] = True
    return synth
