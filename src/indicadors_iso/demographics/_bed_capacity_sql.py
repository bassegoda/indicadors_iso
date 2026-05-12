"""SQL parametrizada para calcular ocupación empírica de camas.

Devuelve, por cada (unit, year, month) en el rango pedido:
  - bed_hours_used: suma de los minutos solapados entre cada movement y
    los límites del mes, dividido por 60. Excluye `place_ref` listados en
    `fake_bed_place_refs` (cama falsa de E073 — auxiliar de procedimientos).
  - n_active_place_refs: count distinct de `place_ref` con al menos un
    minuto de presencia en ese mes (igualmente excluyendo la fake).
  - bed_hours_available = n_active_place_refs * hours_in_month.

El resultado es pequeño (≈ unidades × años × 12 meses) por lo que no se
necesita snapshot CSV. Se llama desde `_bed_occupancy.py`.
"""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd


_SQL_TEMPLATE = """
WITH monthly_calendar AS (
    SELECT
        year(month_start) AS year,
        month(month_start) AS month,
        month_start,
        date_add('month', 1, month_start) AS month_end,
        date_diff('hour', month_start, date_add('month', 1, month_start))
            AS hours_in_month
    FROM (
        SELECT date_add('month', m, timestamp '{min_year}-01-01 00:00:00')
            AS month_start
        FROM UNNEST(sequence(0, {n_months} - 1)) AS t(m)
    ) months
),
clean_moves AS (
    SELECT
        ou_loc_ref,
        place_ref,
        start_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ({units_in})
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, current_timestamp) > start_date
      AND start_date < timestamp '{exclusive_max} 00:00:00'
      AND COALESCE(end_date, current_timestamp) >= timestamp '{min_year}-01-01 00:00:00'
      {fake_bed_filter}
),
move_month_overlap AS (
    SELECT
        m.ou_loc_ref,
        m.place_ref,
        c.year,
        c.month,
        c.hours_in_month,
        GREATEST(
            0,
            date_diff(
                'minute',
                GREATEST(m.start_date, c.month_start),
                LEAST(m.effective_end_date, c.month_end)
            )
        ) AS overlap_minutes
    FROM clean_moves m
    JOIN monthly_calendar c
        ON m.start_date < c.month_end
       AND m.effective_end_date > c.month_start
)
SELECT
    ou_loc_ref AS unit,
    year,
    month,
    hours_in_month,
    SUM(overlap_minutes) / 60.0 AS bed_hours_used,
    COUNT(DISTINCT CASE WHEN overlap_minutes > 0 THEN place_ref END)
        AS n_active_place_refs,
    COUNT(DISTINCT CASE WHEN overlap_minutes > 0 THEN place_ref END)
        * hours_in_month AS bed_hours_available
FROM move_month_overlap
GROUP BY ou_loc_ref, year, month, hours_in_month
ORDER BY ou_loc_ref, year, month
""".strip()


def build_sql(
    units: Iterable[str],
    min_year: int,
    max_year: int,
    fake_bed_place_refs: Optional[Iterable[int]] = None,
) -> str:
    """Construye la SQL Athena/Trino para el rango y unidades pedidos.

    Args:
        units: lista de `ou_loc_ref` a incluir (p.ej. ["E073", "I073"]).
        min_year, max_year: ambos inclusivos. El calendario mensual cubre
            del 1-ene-`min_year` al 1-ene-(max_year+1).
        fake_bed_place_refs: place_refs a excluir tanto del numerador
            como del denominador. Si es vacío/None no excluye nada.
    """
    units_list = list(units)
    if not units_list:
        raise ValueError("`units` no puede estar vacío.")
    if max_year < min_year:
        raise ValueError("max_year < min_year")

    units_in = ",".join(f"'{u}'" for u in units_list)
    n_months = (max_year - min_year + 1) * 12
    exclusive_max = f"{max_year + 1}-01-01"

    fake_ids = list(fake_bed_place_refs or [])
    if fake_ids:
        ids_in = ",".join(str(int(p)) for p in fake_ids)
        fake_bed_filter = f"AND place_ref NOT IN ({ids_in})"
    else:
        fake_bed_filter = ""

    return _SQL_TEMPLATE.format(
        min_year=min_year,
        n_months=n_months,
        exclusive_max=exclusive_max,
        units_in=units_in,
        fake_bed_filter=fake_bed_filter,
    )


def query_bed_capacity(
    units: Iterable[str],
    min_year: int,
    max_year: int,
    fake_bed_place_refs: Optional[Iterable[int]] = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Ejecuta la query de capacidad y devuelve un DataFrame mensual.

    Columnas: unit, year, month, hours_in_month, bed_hours_used,
    n_active_place_refs, bed_hours_available.
    """
    from indicadors_iso.connection import execute_query

    sql = build_sql(units, min_year, max_year, fake_bed_place_refs)
    df = execute_query(sql, verbose=verbose)

    if df.empty:
        return df

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
