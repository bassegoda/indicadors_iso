"""SQL para autopsias / necropsias (no neonatales) ligadas a la cohorte
E073/I073.

Replica la cohorte canónica per-unit (idéntico `stay_id`/`ou_loc_ref` que
`demographics/per_unit/_sql.py`) y le hace un INNER JOIN con las
provisiones de tipo autopsia/necropsia ordenadas por `regexp_like` sobre
`prov_descr`.

Patrón regex (case-insensitive):
    INCLUYE: necr[oó]psia | autopsia
    EXCLUYE: fetal | neonatal

Atribución temporal: la autopsia se asigna a una estancia si comparte
`(patient_ref, episode_ref)` y `start_date >= admission_date`. Una misma
autopsia puede así quedar ligada a varias estancias del mismo episodio
(p. ej. tras un traslado E073→I073). El filtro definitivo a una sola
estancia (la del éxitus) se aplica en el cálculo de la métrica en
`demographics/_metrics.py`, donde se exige
`exitus_during_stay = 'Yes'`.
"""
from __future__ import annotations

# Regex que define una autopsia válida sobre `prov_descr`.
AUTOPSY_REGEX_INCLUDE = "(?i)necr[oó]psia|autopsia"
AUTOPSY_REGEX_EXCLUDE = "(?i)fetal|neonatal"


def render_sql(
    min_year: int,
    max_year: int,
    units: list[str] = ("E073", "I073"),
) -> str:
    units_sql = ", ".join(f"'{u}'" for u in units)

    return f"""
WITH all_related_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ({units_sql})
      AND start_date <= timestamp '{max_year}-12-31 23:59:59'
      AND COALESCE(end_date, current_timestamp) >= timestamp '{min_year}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, current_timestamp) > start_date
),
flagged_starts AS (
    SELECT
        *,
        CASE
            WHEN ABS(date_diff('minute',
                LAG(effective_end_date) OVER (
                    PARTITION BY patient_ref, episode_ref, ou_loc_ref ORDER BY start_date
                ),
                start_date
            )) <= 5
            THEN 0
            ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    SELECT
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY patient_ref, episode_ref, ou_loc_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        stay_id,
        MIN(start_date)         AS admission_date,
        MAX(effective_end_date) AS effective_discharge_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN {min_year} AND {max_year}
),
autopsy_provisions AS (
    SELECT
        patient_ref,
        episode_ref,
        start_date AS autopsy_date,
        prov_descr,
        prov_ref,
        ou_med_ref_order
    FROM datascope_gestor_prod.provisions
    WHERE start_date BETWEEN timestamp '{min_year}-01-01 00:00:00'
                          AND timestamp '{max_year + 2}-12-31 23:59:59'
      AND regexp_like(prov_descr, '{AUTOPSY_REGEX_INCLUDE}')
      AND NOT regexp_like(prov_descr, '{AUTOPSY_REGEX_EXCLUDE}')
)
SELECT
    c.patient_ref,
    c.episode_ref,
    c.ou_loc_ref,
    c.stay_id,
    MIN(ap.autopsy_date)        AS first_autopsy_date,
    COUNT(*)                    AS n_autopsy_provisions,
    COUNT(DISTINCT ap.prov_descr) AS n_distinct_autopsy_descr
FROM cohort c
INNER JOIN autopsy_provisions ap
    ON c.patient_ref = ap.patient_ref
   AND c.episode_ref = ap.episode_ref
   AND ap.autopsy_date >= c.admission_date
GROUP BY c.patient_ref, c.episode_ref, c.ou_loc_ref, c.stay_id
"""
