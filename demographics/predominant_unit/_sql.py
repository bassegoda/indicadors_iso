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
    WHERE ou_loc_ref IN ('E073','I073')
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
time_per_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref,
        SUM(date_diff('minute', start_date, effective_end_date)) AS minutes_in_unit,
        MIN(start_date) AS first_start_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id, ou_loc_ref
),
predominant_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref AS assigned_unit,
        minutes_in_unit AS max_minutes
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY patient_ref, episode_ref, stay_id
                ORDER BY minutes_in_unit DESC, first_start_date ASC
            ) AS rn
        FROM time_per_unit
    ) ranked
    WHERE rn = 1
),
cohort AS (
    SELECT
        g.patient_ref,
        g.episode_ref,
        g.stay_id,
        p.assigned_unit AS ou_loc_ref,
        MIN(g.start_date) AS admission_date,
        MAX(g.end_date) AS discharge_date,
        MAX(g.effective_end_date) AS effective_discharge_date,
        date_diff('hour', MIN(g.start_date), MAX(g.effective_end_date)) AS hours_stay,
        date_diff('day', MIN(g.start_date), MAX(g.effective_end_date)) AS days_stay,
        date_diff('minute', MIN(g.start_date), MAX(g.effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(g.end_date) IS NULL THEN 'Yes' ELSE 'No' END AS still_admitted,
        COUNT(*) AS num_movements,
        COUNT(DISTINCT g.ou_loc_ref) AS num_units_visited
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.patient_ref = p.patient_ref
        AND g.episode_ref = p.episode_ref
        AND g.stay_id = p.stay_id
    GROUP BY g.patient_ref, g.episode_ref, g.stay_id, p.assigned_unit
    HAVING year(MIN(g.start_date)) BETWEEN {min_year} AND {max_year}
),
prescription_filtered AS (
    SELECT DISTINCT
        c.*
    FROM cohort c
    INNER JOIN datascope_gestor_prod.prescriptions p
        ON c.patient_ref = p.patient_ref
        AND c.episode_ref = p.episode_ref
        AND p.start_drug_date BETWEEN c.admission_date
            AND c.effective_discharge_date
),
cohort_with_next AS (
    SELECT
        c.*,
        LEAD(admission_date) OVER (
            PARTITION BY patient_ref ORDER BY admission_date
        ) AS next_admission_date
    FROM prescription_filtered c
),
cirrhosis_dx AS (
    SELECT DISTINCT patient_ref
    FROM datascope_gestor_prod.diagnostics
    WHERE
        -- ICD-10 cirrhosis-related codes
        code LIKE 'K70.3%' OR
        code LIKE 'K71.7%' OR
        code LIKE 'K74.3%' OR
        code LIKE 'K74.4%' OR
        code LIKE 'K74.5%' OR
        code LIKE 'K74.6%' OR
        -- ICD-9 cirrhosis-related codes
        code LIKE '571.2%' OR
        code LIKE '571.5%' OR
        code LIKE '571.6%' OR
        code LIKE '571.8%' OR
        code LIKE '571.9%'
),
-- Episodios con trasplante hepático realizado durante el episodio.
-- Usados después para excluir a estos pacientes de la cohorte de
-- "cirrosis": ingresan electivamente para trasplante y su mortalidad
-- depende del proceso del trasplante, no de la cirrosis subyacente.
liver_transplant_episodes AS (
    SELECT DISTINCT patient_ref, episode_ref
    FROM datascope_gestor_prod.procedures
    WHERE
        -- ICD-10-PCS: 0FY0... (trasplante de hígado, allog./sing./xeno.)
        code LIKE '0FY0%' OR
        -- ICD-9-CM Vol 3: 50.5x (con o sin punto)
        code LIKE '50.5%' OR
        code LIKE '505%'
),
-- Procedencia del paciente antes del ingreso (formulario UCI, PROCE_MALA)
-- Se queda con la última valoración por episodio (la más reciente en form_date)
procedencia_episodio AS (
    SELECT patient_ref, episode_ref, value_text, value_descr
    FROM (
        SELECT
            patient_ref,
            episode_ref,
            value_text,
            value_descr,
            ROW_NUMBER() OVER (
                PARTITION BY patient_ref, episode_ref
                ORDER BY form_date DESC
            ) AS rn
        FROM datascope_gestor_prod.dynamic_forms
        WHERE form_ref = 'UCI'
          AND question_ref = 'PROCE_MALA'
          AND status = 'CO'
    ) x
    WHERE rn = 1
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
        WHEN dx.patient_ref IS NOT NULL THEN 1 ELSE 0
    END AS has_cirrhosis,
    CASE
        WHEN lt.patient_ref IS NOT NULL THEN 1 ELSE 0
    END AS liver_transplant_during_episode,
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
    END AS readmission_72h,
    proc.value_text AS procedencia_codigo,
    proc.value_descr AS procedencia,
    CASE
        -- El formulario UCI cambió del catalán al castellano hacia
        -- septiembre de 2022. Aceptamos ambas variantes para que la
        -- serie 2019-2025 sea homogénea.
        WHEN proc.value_text IN (
            '20-Altre hospital-',
            '20-Otro hospital-'
        ) THEN 1 ELSE 0
    END AS from_other_hospital
FROM cohort_with_next cw
LEFT JOIN datascope_gestor_prod.demographics d
    ON cw.patient_ref = d.patient_ref
LEFT JOIN cirrhosis_dx dx
    ON cw.patient_ref = dx.patient_ref
LEFT JOIN liver_transplant_episodes lt
    ON cw.patient_ref = lt.patient_ref
    AND cw.episode_ref = lt.episode_ref
LEFT JOIN datascope_gestor_prod.exitus ex
    ON cw.patient_ref = ex.patient_ref
LEFT JOIN procedencia_episodio proc
    ON cw.patient_ref = proc.patient_ref
    AND cw.episode_ref = proc.episode_ref
ORDER BY cw.admission_date;
"""
