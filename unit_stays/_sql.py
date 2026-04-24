SQL_TEMPLATE = """
WITH all_related_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ({units})
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
                    PARTITION BY patient_ref, episode_ref ORDER BY start_date
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
            PARTITION BY patient_ref, episode_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        MIN(ou_loc_ref) AS ou_loc_ref,
        MIN(start_date) AS admission_date,
        MAX(end_date) AS discharge_date,
        MAX(effective_end_date) AS effective_discharge_date,
        date_diff('hour', MIN(start_date), MAX(effective_end_date)) AS hours_stay,
        date_diff('day', MIN(start_date), MAX(effective_end_date)) AS days_stay,
        date_diff('minute', MIN(start_date), MAX(effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(end_date) IS NULL THEN 'Yes' ELSE 'No' END AS still_admitted,
        COUNT(*) AS num_movements,
        COUNT(DISTINCT ou_loc_ref) AS num_units_visited
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN {min_year} AND {max_year}
),
cohort_with_next AS (
    SELECT
        c.*,
        LEAD(admission_date) OVER (
            PARTITION BY patient_ref ORDER BY admission_date
        ) AS next_admission_date
    FROM cohort c
),
prescriptions_new AS (
    SELECT DISTINCT
        p.patient_ref,
        p.episode_ref
    FROM datascope_gestor_prod.prescriptions p
    INNER JOIN cohort c
        ON p.patient_ref = c.patient_ref
        AND p.episode_ref = c.episode_ref
        AND p.start_drug_date BETWEEN c.admission_date AND c.effective_discharge_date
)
SELECT DISTINCT
    cw.patient_ref,
    cw.episode_ref,
    cw.stay_id,
    cw.ou_loc_ref,
    cw.admission_date,
    cw.discharge_date,
    cw.effective_discharge_date,
    cw.hours_stay,
    cw.days_stay,
    cw.minutes_stay,
    cw.still_admitted,
    cw.num_movements,
    cw.num_units_visited,
    CASE
        WHEN cw.num_units_visited > 1 THEN 'Yes'
        ELSE 'No'
    END AS had_transfer,
    year(cw.admission_date) AS year_admission,
    date_diff('year', d.birth_date, cw.admission_date) AS age_at_admission,
    d.natio_ref,
    CASE
        WHEN d.sex = 1 THEN 'Male'
        WHEN d.sex = 2 THEN 'Female'
        WHEN d.sex = 3 THEN 'Other'
        ELSE 'Not reported'
    END AS sex,
    d.natio_descr AS nationality,
    d.health_area,
    d.postcode,
    CASE
        WHEN ex.exitus_date IS NOT NULL
             AND ex.exitus_date BETWEEN cw.admission_date
                 AND cw.effective_discharge_date
        THEN 'Yes'
        ELSE 'No'
    END AS exitus_during_stay,
    ex.exitus_date,
    CASE
        WHEN prx.patient_ref IS NOT NULL THEN 1 ELSE 0
    END AS has_new_prescription,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND date_diff(
                 'hour', cw.effective_discharge_date, cw.next_admission_date
             ) <= 24
        THEN 1 ELSE 0
    END AS readmission_24h,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND date_diff(
                 'hour', cw.effective_discharge_date, cw.next_admission_date
             ) <= 72
        THEN 1 ELSE 0
    END AS readmission_72h
FROM cohort_with_next cw
LEFT JOIN datascope_gestor_prod.demographics d
    ON cw.patient_ref = d.patient_ref
LEFT JOIN datascope_gestor_prod.exitus ex
    ON cw.patient_ref = ex.patient_ref
LEFT JOIN prescriptions_new prx
    ON cw.patient_ref = prx.patient_ref
    AND cw.episode_ref = prx.episode_ref
ORDER BY cw.admission_date;
"""
