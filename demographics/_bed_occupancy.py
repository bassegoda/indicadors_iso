"""Cálculo empírico de ocupación de camas por (unidad, año).

Sustituye la antigua constante `beds_per_unit()` por una capacidad real
derivada de `movements`:
    - bed_hours_available_year = Σ_meses (n_place_refs_activos_en_mes × horas_del_mes)
    - bed_hours_used_year       = Σ_meses (Σ minutos solapados / 60)
    - pct_year                  = bed_hours_used / bed_hours_available × 100

La cama falsa de E073 (auxiliar de procedimientos) se excluye de ambos.

El resultado se cachea en `demographics/output/_bed_capacity_<units>_<min>-<max>.csv`
para no volver a consultar Athena en cada ejecución del informe. Si el
cache existe, se reutiliza salvo que se pase `force_refresh=True`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from demographics._bed_capacity_sql import query_bed_capacity

_CACHE_DIR = Path(__file__).resolve().parent / "output"


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
                f"[bed_occupancy] Consultando capacidad emp\u00edrica "
                f"{units_list} {min_year}-{max_year}\u2026"
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
                    "[bed_occupancy] La query devolvi\u00f3 0 filas; "
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


def compute_bed_occupancy(
    units: Iterable[str],
    min_year: int,
    max_year: int,
    fake_bed_place_refs: Optional[Iterable[int]] = None,
    force_refresh: bool = False,
    verbose: bool = True,
) -> pd.DataFrame:
    """Tabla anual por (unit, year) con ocupación agregada.

    Columnas devueltas:
        unit, year, bed_hours_used, bed_hours_available, pct,
        n_months_with_data, max_n_active_place_refs

    El % se calcula como `Σ used / Σ available × 100`. Si para una
    (unit, year) no hay filas en `movements`, no aparece en la tabla.
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

    grouped = (
        monthly.groupby(["unit", "year"], as_index=False)
        .agg(
            bed_hours_used=("bed_hours_used", "sum"),
            bed_hours_available=("bed_hours_available", "sum"),
            n_months_with_data=("month", "nunique"),
            max_n_active_place_refs=("n_active_place_refs", "max"),
        )
    )
    grouped["pct"] = grouped.apply(
        lambda r: (r["bed_hours_used"] / r["bed_hours_available"] * 100)
        if r["bed_hours_available"] > 0 else float("nan"),
        axis=1,
    )
    grouped["year"] = grouped["year"].astype(int)
    return grouped
