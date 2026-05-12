"""Cálculo de ocupación de camas por (unidad efectiva, año).

`compute_bed_occupancy_nominal()` — única versión activa. Denominador
fijado por la tabla de épocas en `demographics/_bed_capacity_eras.py`.
Durante la época `covid` los movimientos en E073 e I073 se agregan en
la unidad sintética "UCI" (12 camas nominales), sorteando el
reetiquetado COVID-19.

El SQL mensual está en `_bed_capacity_sql.py`; los resultados mensuales
se cachean en CSV bajo `demographics/output/`. La cama falsa de E073
(auxiliar de procedimientos) se excluye en el SQL — ver `_config.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from indicadors_iso._paths import module_output_dir
from indicadors_iso.demographics._bed_capacity_eras import (
    COMBINED_UNIT_LABEL,
    lookup_capacity_for_month,
)
from indicadors_iso.demographics._bed_capacity_sql import query_bed_capacity

_CACHE_DIR = module_output_dir("demographics", "_bed_capacity_cache")


def _cache_path(units: Iterable[str], min_year: int, max_year: int) -> Path:
    units_tag = "-".join(sorted(units))
    return _CACHE_DIR / f"_bed_capacity_{units_tag}_{min_year}-{max_year}.csv"


def load_or_query_monthly(
    units: Iterable[str],
    min_year: int,
    max_year: int,
    fake_bed_place_refs: Optional[Iterable[int]] = None,
    force_refresh: bool = False,
    verbose: bool = True,
) -> pd.DataFrame:
    """Devuelve la tabla mensual (unit, year, month, ...) usando cache CSV."""
    units_list = list(units)
    cache = _cache_path(units_list, min_year, max_year)

    if cache.exists() and not force_refresh:
        if verbose:
            print(f"[bed_occupancy] Usando cache: {cache.name}")
        df = pd.read_csv(cache)
    else:
        if verbose:
            print(
                f"[bed_occupancy] Consultando capacidad empírica "
                f"{units_list} {min_year}-{max_year}…"
            )
        df = query_bed_capacity(
            units=units_list,
            min_year=min_year,
            max_year=max_year,
            fake_bed_place_refs=fake_bed_place_refs,
            verbose=verbose,
        )
        if df.empty:
            if verbose:
                print(
                    "[bed_occupancy] La query devolvió 0 filas; "
                    "no se cachea nada."
                )
            return df
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False, encoding="utf-8")
        if verbose:
            print(f"[bed_occupancy] Cache escrito en {cache.name}")

    numeric_cols = [
        "year",
        "month",
        "hours_in_month",
        "bed_hours_used",
        "n_active_place_refs",
        "bed_hours_available",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _default_incomplete_months() -> set[tuple[int, int]]:
    """Meses que se excluyen del cálculo por falta de carga al DW.

    Se derivan del rango sintético de la cohorte (`_loader.SYNTHETIC_
    DATE_RANGE`) para que numerador y denominador del bed_capacity
    coincidan con el periodo que el loader tuvo que rellenar mediante
    bootstrap. Excluir estos meses (no aparecen en numerador ni en
    denominador) preserva el ratio anual sobre los meses con datos
    completos: equivale a anualizar la ocupación observada en lo que
    sí está cargado.
    """
    from demographics._loader import SYNTHETIC_DATE_RANGE
    start, end = SYNTHETIC_DATE_RANGE
    months: set[tuple[int, int]] = set()
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.add((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def compute_bed_occupancy_nominal(
    units: Iterable[str],
    min_year: int,
    max_year: int,
    fake_bed_place_refs: Optional[Iterable[int]] = None,
    force_refresh: bool = False,
    verbose: bool = True,
    exclude_months: Optional[Iterable[tuple[int, int]]] = None,
) -> pd.DataFrame:
    """Ocupación anual con denominador NOMINAL por época.

    Columnas devueltas:
        effective_unit       "E073" | "I073" | "UCI" (covid)
        year
        regimen              "stable" | "covid"
        nominal_beds         capacidad nominal de la época
        n_months_in_era      meses del año bajo esa (effective_unit, regimen)
        bed_hours_used
        bed_hours_available  = nominal_beds × Σ hours_in_month_in_era
        pct                  used / available × 100
        max_active_place_refs    diagnóstico (cuántas camas físicas hubo
                                 codificadas a la vez algún mes)
        n_months_excluded    meses incompletos (datos no cargados al DW)
                             que se descartaron del cálculo del año.

    En épocas `stable` cada raw_unit aparece por separado. En `covid`
    los movimientos en E073 e I073 se agregan en effective_unit="UCI"
    con 12 camas nominales: durante 2020-2021 y principios de 2022 el
    etiquetado por unidad no es fiable, así que reportamos UCI completa.

    `exclude_months` permite descartar meses con carga incompleta del
    data warehouse (Nov-Dic 2025 mientras los datos no han aterrizado).
    Si es None se autodetecta a partir de `_loader.SYNTHETIC_DATE_RANGE`,
    coincidiendo con el periodo que el loader rellena por bootstrap en
    la cohorte. Pasar `exclude_months=[]` desactiva la exclusión.
    """
    monthly = load_or_query_monthly(
        units=units,
        min_year=min_year,
        max_year=max_year,
        fake_bed_place_refs=fake_bed_place_refs,
        force_refresh=force_refresh,
        verbose=verbose,
    )
    if monthly.empty:
        return monthly

    monthly = monthly.copy()

    if exclude_months is None:
        exclude_set = _default_incomplete_months()
    else:
        exclude_set = {(int(y), int(m)) for y, m in exclude_months}

    excluded_per_year: dict[int, int] = {}
    if exclude_set:
        ym_pairs = list(zip(monthly["year"].astype(int), monthly["month"].astype(int)))
        excl_mask = pd.Series(
            [(y, m) in exclude_set for y, m in ym_pairs], index=monthly.index
        )
        excluded_rows = monthly[excl_mask]
        # Cuántos meses calendario distintos descartamos por año (1 evento
        # cuenta una vez aunque aparezca en E073 e I073).
        for y, sub in excluded_rows.groupby(excluded_rows["year"].astype(int)):
            excluded_per_year[int(y)] = int(
                sub["month"].astype(int).nunique()
            )
        monthly = monthly[~excl_mask].copy()
        if verbose and excluded_per_year:
            summary = ", ".join(
                f"{y}: {n}m" for y, n in sorted(excluded_per_year.items())
            )
            print(
                f"[bed_occupancy] Excluidos meses incompletos del DW "
                f"(numerador y denominador): {summary}"
            )
        if monthly.empty:
            return monthly

    mapped = monthly.apply(
        lambda r: lookup_capacity_for_month(
            int(r["year"]), int(r["month"]), str(r["unit"])
        ),
        axis=1,
    )
    monthly["effective_unit"] = mapped.map(lambda x: x[0] if x else None)
    monthly["nominal_beds"] = mapped.map(lambda x: x[1] if x else None)
    monthly["regimen"] = mapped.map(lambda x: x[2] if x else None)
    monthly = monthly.dropna(subset=["effective_unit"])
    if monthly.empty:
        return monthly
    monthly["nominal_beds"] = monthly["nominal_beds"].astype(int)

    # Sumamos numerador por (effective_unit, year, month). En covid esto
    # colapsa E073 + I073 → UCI (los movimientos de ambas raw_units en el
    # mismo mes se suman). En stable cada effective_unit ya es la propia
    # raw_unit, así que el sum es no-op (1 fila → 1 fila).
    per_month = (
        monthly.groupby(
            ["effective_unit", "year", "month"], as_index=False
        ).agg(
            bed_hours_used=("bed_hours_used", "sum"),
            hours_in_month=("hours_in_month", "first"),
            nominal_beds=("nominal_beds", "first"),
            regimen=("regimen", "first"),
            n_active_place_refs=("n_active_place_refs", "sum"),
        )
    )
    per_month["bed_hours_available"] = (
        per_month["nominal_beds"] * per_month["hours_in_month"]
    )

    yearly = (
        per_month.groupby(["effective_unit", "year"], as_index=False).agg(
            bed_hours_used=("bed_hours_used", "sum"),
            bed_hours_available=("bed_hours_available", "sum"),
            n_months_in_era=("month", "nunique"),
            nominal_beds=("nominal_beds", "first"),
            regimen=("regimen", "first"),
            max_active_place_refs=("n_active_place_refs", "max"),
        )
    )
    yearly["pct"] = yearly.apply(
        lambda r: (r["bed_hours_used"] / r["bed_hours_available"] * 100)
        if r["bed_hours_available"] > 0 else float("nan"),
        axis=1,
    )
    yearly["year"] = yearly["year"].astype(int)
    yearly["n_months_excluded"] = (
        yearly["year"].map(excluded_per_year).fillna(0).astype(int)
    )

    if verbose:
        _print_capacity_diagnostics(yearly)

    return yearly


def _print_capacity_diagnostics(yearly: pd.DataFrame) -> None:
    """Avisa de meses con `n_active_place_refs` muy distinto del nominal.

    Útil para detectar derivas: una cama auxiliar nueva no excluida, una
    migración administrativa en curso, o una época con boundaries
    desalineadas. Sólo imprime; no modifica nada.
    """
    if yearly.empty:
        return
    flagged = yearly[
        (yearly["max_active_place_refs"].notna())
        & (
            (yearly["max_active_place_refs"] > yearly["nominal_beds"] * 1.2)
            | (yearly["max_active_place_refs"] < yearly["nominal_beds"] * 0.5)
        )
    ]
    if flagged.empty:
        return
    print(
        "[bed_occupancy] Aviso: años con desviación entre "
        "max_active_place_refs y nominal_beds (revisar configuración):"
    )
    for _, row in flagged.iterrows():
        print(
            f"  - {row['effective_unit']} {int(row['year'])} "
            f"({row['regimen']}): nominal={int(row['nominal_beds'])}, "
            f"max_active={int(row['max_active_place_refs'])}"
        )
