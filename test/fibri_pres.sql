-- Pre-prescription fibrinogen levels: last lab available before each fibrinogen prescription
-- Lab: LAB1102 (Fibrinogeno, g/L) | Drug: ATC B02BB01 (Fibrinogeno humano)
-- Period: 2024, inpatient/EM episodes only

WITH fib_pres AS (
    -- All fibrinogen prescriptions
    SELECT 
        p.patient_ref,
        p.episode_ref,
        p.treatment_ref,
        p.start_drug_date AS prescription_date,
        p.dose AS quantity,
        p.unit AS quantity_unit,
        p.drug_descr,
        p.prn
    FROM g_prescriptions p
    INNER JOIN g_episodes e ON p.episode_ref = e.episode_ref
    WHERE p.atc_ref = 'B02BB01'
      AND p.start_drug_date >= '2024-01-01'
      AND p.start_drug_date < '2025-01-01'
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
    FROM g_labs
    WHERE lab_sap_ref = 'LAB1102'
      AND result_num IS NOT NULL
      AND result_date >= '2024-01-01'
      AND result_date < '2025-01-01'
),
last_lab_before_pres AS (
    -- For each prescription, find the closest lab RESULT available before it
    SELECT 
        fp.patient_ref,
        fp.episode_ref,
        fp.treatment_ref,
        fp.prescription_date,
        fp.quantity,
        fp.quantity_unit,
        fp.drug_descr,
        fp.prn,
        fl.extrac_date AS lab_date,
        fl.result_date AS result_date,
        fl.result_num AS fib_level_g_l,
        fl.units AS lab_units,
        ROW_NUMBER() OVER (
            PARTITION BY fp.patient_ref, fp.episode_ref, fp.prescription_date
            ORDER BY fl.result_date DESC
        ) AS rn
    FROM fib_pres fp
    LEFT JOIN fib_labs fl
        ON fp.patient_ref = fl.patient_ref
        AND fp.episode_ref = fl.episode_ref
        AND fl.result_date < fp.prescription_date
)
SELECT 
    patient_ref,
    episode_ref,
    treatment_ref,
    prescription_date,
    quantity,
    quantity_unit,
    drug_descr,
    prn,
    lab_date,
    result_date,
    fib_level_g_l,
    lab_units,
    TIMESTAMPDIFF(MINUTE, result_date, prescription_date) AS minutes_result_to_pres,
    ROUND(TIMESTAMPDIFF(MINUTE, result_date, prescription_date) / 60.0, 1) AS hours_result_to_pres,
    YEAR(prescription_date) AS yr
FROM last_lab_before_pres
WHERE rn = 1
ORDER BY prescription_date;
