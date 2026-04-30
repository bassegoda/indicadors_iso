SQL_TEMPLATE = """
-- =====================================================================
-- Demographics — variante PER-UNIT
-- =====================================================================
-- Cohorte de estancias en E073/I073 SIN agrupamiento entre unidades:
--   * Si un paciente se traslada de E073 a I073 dentro del mismo
--     episodio, **cuentan como dos estancias distintas**.
--   * Cada estancia agrupa solo los movimientos consecutivos dentro de
--     LA MISMA unidad (tolerancia 5 min entre movimientos).
--
-- Mantiene los criterios de:
--   - Cama asignada (place_ref IS NOT NULL).
--   - Año de ingreso en el rango.
--   - Al menos una prescripción durante la estancia.
--
-- Reingresos: definidos como la siguiente admisión del mismo paciente
-- en un EPISODIO DISTINTO (ignora transferencias intra-episodio).
-- =====================================================================
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
    -- Particionamos por (patient, episode, ou_loc_ref) para que un
    -- cambio de unidad inicie automáticamente una nueva estancia.
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
        MIN(start_date) AS admission_date,
        MAX(end_date) AS discharge_date,
        MAX(effective_end_date) AS effective_discharge_date,
        date_diff('hour',  MIN(start_date), MAX(effective_end_date)) AS hours_stay,
        date_diff('day',   MIN(start_date), MAX(effective_end_date)) AS days_stay,
        date_diff('minute',MIN(start_date), MAX(effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(end_date) IS NULL THEN 'Yes' ELSE 'No' END AS still_admitted,
        COUNT(*) AS num_movements,
        1       AS num_units_visited
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN {min_year} AND {max_year}
),
prescription_filtered AS (
    SELECT DISTINCT c.*
    FROM cohort c
    INNER JOIN datascope_gestor_prod.prescriptions p
        ON c.patient_ref = p.patient_ref
        AND c.episode_ref = p.episode_ref
        AND p.start_drug_date BETWEEN c.admission_date
            AND c.effective_discharge_date
),
-- Reingreso: siguiente admisión del paciente en un EPISODIO distinto.
-- Calculamos LEAD a nivel de episodio (no de estancia) para no contar
-- los traslados intra-episodio como reingresos.
episode_starts AS (
    SELECT
        patient_ref,
        episode_ref,
        MIN(admission_date) AS episode_start
    FROM prescription_filtered
    GROUP BY patient_ref, episode_ref
),
episode_lead AS (
    SELECT
        patient_ref,
        episode_ref,
        episode_start,
        LEAD(episode_start) OVER (
            PARTITION BY patient_ref ORDER BY episode_start
        ) AS next_episode_start
    FROM episode_starts
),
cohort_with_next AS (
    SELECT
        c.*,
        e.next_episode_start AS next_admission_date
    FROM prescription_filtered c
    LEFT JOIN episode_lead e
        ON c.patient_ref = e.patient_ref
        AND c.episode_ref = e.episode_ref
),
cirrhosis_dx AS (
    SELECT DISTINCT patient_ref
    FROM datascope_gestor_prod.diagnostics
    WHERE
        code LIKE 'K70.3%' OR
        code LIKE 'K71.7%' OR
        code LIKE 'K74.3%' OR
        code LIKE 'K74.4%' OR
        code LIKE 'K74.5%' OR
        code LIKE 'K74.6%' OR
        code LIKE '571.2%' OR
        code LIKE '571.5%' OR
        code LIKE '571.6%' OR
        code LIKE '571.8%' OR
        code LIKE '571.9%'
),
-- Episodios con trasplante hepático realizado durante el episodio.
-- Estos pacientes se sacan de la cohorte de "cirrosis" en _metrics.py.
liver_transplant_episodes AS (
    SELECT DISTINCT patient_ref, episode_ref
    FROM datascope_gestor_prod.procedures
    WHERE
        code LIKE '0FY0%' OR
        code LIKE '50.5%' OR
        code LIKE '505%'
),
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
    'No' AS had_transfer,
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
    CASE WHEN dx.patient_ref IS NOT NULL THEN 1 ELSE 0 END AS has_cirrhosis,
    CASE WHEN lt.patient_ref IS NOT NULL THEN 1 ELSE 0 END AS liver_transplant_during_episode,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND date_diff('hour', cw.effective_discharge_date, cw.next_admission_date) <= 24
        THEN 1 ELSE 0
    END AS readmission_24h,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND date_diff('hour', cw.effective_discharge_date, cw.next_admission_date) <= 72
        THEN 1 ELSE 0
    END AS readmission_72h,
    proc.value_text AS procedencia_codigo,
    proc.value_descr AS procedencia,
    CASE
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
ORDER BY cw.ou_loc_ref, cw.admission_date;
"""
