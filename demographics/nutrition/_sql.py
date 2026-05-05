"""SQL para indicadores de nutrición enteral / parenteral por estancia.

Replica la **cohorte canónica per-unit** de `demographics/per_unit/_sql.py`
(con `stay_id` particionado por `(patient_ref, episode_ref, ou_loc_ref)`
y tolerancia 5 min entre movimientos de la misma unidad) para que la
clave `[patient_ref, episode_ref, ou_loc_ref, stay_id]` sea idéntica al
DataFrame demográfico — así el merge en Python es directo.

Devuelve, por cada estancia:
    nutr_enteral_start          -> MIN start_drug_date enteral *iniciada
                                   dentro* de [admission_date,
                                   effective_discharge_date]
    nutr_parenteral_start       -> idem para parenteral
    hours_to_enteral            -> date_diff('hour', admission_date, *_start)
    hours_to_parenteral         -> idem
    received_enteral / _parenteral -> 0/1 flags

Para alimentar el pipeline `predominant_unit` (donde una estancia que
pasa por E073 e I073 colapsa en una sola fila asignada a la unidad
predominante), agregamos *también* a nivel `[patient_ref, episode_ref]`
en `aggregate_to_predominant()` desde Python — más simple que mantener
dos consultas SQL casi idénticas.
"""
from __future__ import annotations

from demographics.nutrition._config import (
    enteral_predicate,
    parenteral_predicate,
)


def render_sql(
    min_year: int,
    max_year: int,
    units: list[str] = ("E073", "I073"),
) -> str:
    units_sql = ", ".join(f"'{u}'" for u in units)
    enteral_pred = enteral_predicate("p.drug_descr")
    parenteral_pred = parenteral_predicate("p.drug_descr")

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
        MIN(start_date)        AS admission_date,
        MAX(effective_end_date) AS effective_discharge_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN {min_year} AND {max_year}
),
nutrition_prescriptions AS (
    SELECT
        p.patient_ref,
        p.episode_ref,
        p.start_drug_date,
        CASE WHEN {enteral_pred}    THEN 1 ELSE 0 END AS is_enteral,
        CASE WHEN {parenteral_pred} THEN 1 ELSE 0 END AS is_parenteral
    FROM datascope_gestor_prod.prescriptions p
    WHERE p.start_drug_date BETWEEN timestamp '{min_year}-01-01 00:00:00'
                                 AND timestamp '{max_year}-12-31 23:59:59'
      AND ({enteral_pred} OR {parenteral_pred})
),
matched AS (
    SELECT
        c.patient_ref,
        c.episode_ref,
        c.ou_loc_ref,
        c.stay_id,
        c.admission_date,
        np.start_drug_date,
        np.is_enteral,
        np.is_parenteral
    FROM cohort c
    INNER JOIN nutrition_prescriptions np
        ON c.patient_ref = np.patient_ref
       AND c.episode_ref = np.episode_ref
       AND np.start_drug_date >= c.admission_date
       AND np.start_drug_date <= c.effective_discharge_date
)
SELECT
    patient_ref,
    episode_ref,
    ou_loc_ref,
    stay_id,
    admission_date,
    MIN(CASE WHEN is_enteral    = 1 THEN start_drug_date END) AS nutr_enteral_start,
    MIN(CASE WHEN is_parenteral = 1 THEN start_drug_date END) AS nutr_parenteral_start
FROM matched
GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id, admission_date
"""
