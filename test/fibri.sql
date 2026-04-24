-- Pre-administration fibrinogen levels: last lab before each fibrinogen infusion
-- Lab: LAB1102 (Fibrinogeno, g/L) | Drug: ATC B02BB01 (Fibrinogeno humano)
-- Period: 2024, inpatient/EM episodes only
-- Dialect: Athena (Trino/Presto)

WITH fib_admin AS (
    -- All fibrinogen administrations
    SELECT
        a.patient_ref,
        a.episode_ref,
        a.treatment_ref,
        a.administration_date,
        a.quantity,
        a.quantity_unit,
        a.drug_descr,
        a.given
    FROM administrations a
    INNER JOIN episodes e ON a.episode_ref = e.episode_ref
    WHERE a.atc_ref = 'B02BB01'
      AND a.administration_date >= timestamp '2024-01-01 00:00:00'
      AND a.administration_date < timestamp '2025-01-01 00:00:00'
      AND e.episode_type_ref IN ('EM', 'HOSP')
),
fib_labs AS (
    -- All fibrinogen lab results
    SELECT
        patient_ref,
        episode_ref,
        extrac_date,
        result_date,
        result_num,
        units
    FROM labs
    WHERE lab_sap_ref = 'LAB1102'
      AND result_num IS NOT NULL
      AND result_date >= timestamp '2024-01-01 00:00:00'
      AND result_date < timestamp '2025-01-01 00:00:00'
),
last_lab_before_admin AS (
    -- For each administration, find the closest lab RESULT available before administration
    SELECT
        fa.patient_ref,
        fa.episode_ref,
        fa.treatment_ref,
        fa.administration_date,
        fa.quantity,
        fa.quantity_unit,
        fa.drug_descr,
        fa.given,
        fl.extrac_date AS lab_date,
        fl.result_date AS result_date,
        fl.result_num AS fib_level_g_l,
        fl.units AS lab_units,
        ROW_NUMBER() OVER (
            PARTITION BY fa.patient_ref, fa.episode_ref, fa.administration_date
            ORDER BY fl.result_date DESC
        ) AS rn
    FROM fib_admin fa
    LEFT JOIN fib_labs fl
        ON fa.patient_ref = fl.patient_ref
        AND fa.episode_ref = fl.episode_ref
        AND fl.result_date < fa.administration_date
)
SELECT
    patient_ref,
    episode_ref,
    treatment_ref,
    administration_date,
    quantity,
    quantity_unit,
    drug_descr,
    given,
    lab_date,
    result_date,
    fib_level_g_l,
    lab_units,
    date_diff('minute', result_date, administration_date) AS minutes_result_to_admin,
    ROUND(date_diff('minute', result_date, administration_date) / 60.0, 1) AS hours_result_to_admin,
    year(administration_date) AS yr
FROM last_lab_before_admin
WHERE rn = 1 AND given IS NULL
ORDER BY administration_date;
