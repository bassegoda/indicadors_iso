SQL_TEMPLATE = """
-- =====================================================================
-- Aislamientos positivos en frotis rectal de multirresistentes
-- restringidos a estancias E073 / I073 (lógica per_unit).
-- =====================================================================
-- Replica EXACTAMENTE la definición de estancia de
-- demographics/per_unit/_sql.py (sin agrupar traslados, tolerancia
-- 5 min, place_ref IS NOT NULL, prescripción durante la estancia).
--
-- Sobre esa cohorte se cruzan los registros de
-- datascope_gestor_prod.micro filtrando:
--   - positive = 'X'  (microorganismo aislado)
--   - method_descr corresponde a frotis rectal de multirresistentes
--     (variantes ortográficas/encoding cubiertas con LIKE)
--   - extrac_date dentro de la ventana [admission_date, effective_discharge_date]
--
-- Salida: una fila por aislamiento positivo. La clasificación final de
-- qué microorganismos son "MDR" se hace a posteriori por el clínico.
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
        MAX(effective_end_date) AS effective_discharge_date
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
rectal_mdr_micro AS (
    -- Frotis rectal de detección de bacterias multirresistentes.
    -- Cubrimos todas las variantes ortográficas y de encoding observadas
    -- en method_descr con un LIKE robusto. Excluimos explícitamente la
    -- muestra ambiental.
    SELECT
        patient_ref,
        episode_ref,
        extrac_date,
        res_date,
        ou_med_ref,
        mue_ref,
        mue_descr,
        method_descr,
        positive,
        antibiogram_ref,
        micro_ref,
        micro_descr,
        num_micro,
        result_text,
        load_date,
        care_level_ref
    FROM datascope_gestor_prod.micro
    WHERE positive = 'X'
      AND (
            method_descr LIKE '%Frotis rectal%multiresist%'
         OR method_descr LIKE '%Frotis rectal%multirresist%'
         OR method_descr LIKE '%Frotis rectal%multiresit%'
      )
      AND method_descr NOT LIKE '%ambiental%'
)
SELECT
    c.patient_ref,
    c.episode_ref,
    c.ou_loc_ref,
    c.stay_id,
    c.admission_date,
    c.effective_discharge_date,
    year(c.admission_date) AS year_admission,
    m.extrac_date,
    m.res_date,
    m.ou_med_ref           AS micro_ou_med_ref,
    m.mue_ref,
    m.mue_descr,
    m.method_descr,
    m.positive,
    m.antibiogram_ref,
    m.micro_ref,
    m.micro_descr,
    m.num_micro,
    m.result_text,
    m.load_date            AS micro_load_date,
    m.care_level_ref       AS micro_care_level_ref
FROM prescription_filtered c
INNER JOIN rectal_mdr_micro m
    ON c.patient_ref = m.patient_ref
   AND c.episode_ref = m.episode_ref
   AND m.extrac_date BETWEEN c.admission_date
       AND c.effective_discharge_date
ORDER BY c.ou_loc_ref, c.admission_date, m.extrac_date, m.num_micro;
"""
