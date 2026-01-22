# DataNex SQL Query Examples

Use Common Table Expressions (CTEs) for optimization. Always search using 'ref' fields from dictionaries.

---

## Example 1: Patients with specific diagnosis

```sql
WITH diagnosis_search AS (
    SELECT DISTINCT patient_ref, episode_ref, diag_descr
    FROM g_diagnostics
    WHERE diag_descr LIKE '%diabetes%'
)
SELECT * FROM diagnosis_search;
```

---

## Example 2: Laboratory results in date range

```sql
WITH lab_results AS (
    SELECT 
        patient_ref,
        episode_ref,
        lab_sap_ref,
        lab_descr,
        result_num,
        units,
        extrac_date
    FROM g_labs
    WHERE extrac_date BETWEEN '2024-01-01' AND '2024-12-31'
        AND lab_sap_ref = 'LAB110'  -- Urea
)
SELECT * FROM lab_results
ORDER BY patient_ref, extrac_date;
```

---

## Example 3: Patient demographics with episodes

```sql
WITH patient_episodes AS (
    SELECT DISTINCT 
        e.patient_ref, 
        e.episode_ref,
        e.episode_type_ref,
        e.start_date,
        e.end_date
    FROM g_episodes e
),
patient_info AS (
    SELECT 
        d.patient_ref,
        d.birth_date,
        d.sex,
        d.natio_descr
    FROM g_demographics d
)
SELECT 
    pe.*,
    pi.birth_date,
    pi.sex,
    pi.natio_descr
FROM patient_episodes pe
JOIN patient_info pi ON pe.patient_ref = pi.patient_ref;
```

---

## Example 4: Drug administrations with prescriptions (Antibiotics)

```sql
WITH prescriptions AS (
    SELECT 
        patient_ref,
        episode_ref,
        treatment_ref,
        drug_ref,
        drug_descr,
        atc_ref,
        dose,
        unit
    FROM g_prescriptions
    WHERE atc_ref LIKE 'J01%'  -- Antibacterials
),
administrations AS (
    SELECT 
        patient_ref,
        episode_ref,
        treatment_ref,
        administration_date,
        quantity,
        quantity_unit
    FROM g_administrations
)
SELECT 
    p.*,
    a.administration_date,
    a.quantity
FROM prescriptions p
JOIN administrations a 
    ON p.patient_ref = a.patient_ref 
    AND p.treatment_ref = a.treatment_ref;
```

---

## Example 5: Microbiology with antibiograms

```sql
WITH micro_positive AS (
    SELECT 
        patient_ref,
        episode_ref,
        extrac_date,
        micro_ref,
        micro_descr,
        antibiogram_ref
    FROM g_micro
    WHERE positive = 'X'
),
antibiogram_results AS (
    SELECT 
        patient_ref,
        antibiogram_ref,
        antibiotic_descr,
        sensitivity
    FROM g_antibiograms
)
SELECT 
    mp.*,
    ar.antibiotic_descr,
    ar.sensitivity
FROM micro_positive mp
JOIN antibiogram_results ar 
    ON mp.patient_ref = ar.patient_ref 
    AND mp.antibiogram_ref = ar.antibiogram_ref;
```

---

## Example 6: Patients in ICU with specific lab values

```sql
WITH icu_patients AS (
    SELECT DISTINCT 
        patient_ref,
        episode_ref,
        care_level_ref
    FROM g_care_levels
    WHERE care_level_type_ref = 'UCI'
),
creatinine_labs AS (
    SELECT 
        patient_ref,
        episode_ref,
        result_num,
        extrac_date
    FROM g_labs
    WHERE lab_sap_ref = 'LAB1200'  -- Creatinina
        AND result_num > 2.0
)
SELECT 
    ip.patient_ref,
    ip.episode_ref,
    cl.result_num AS creatinine,
    cl.extrac_date
FROM icu_patients ip
JOIN creatinine_labs cl 
    ON ip.patient_ref = cl.patient_ref 
    AND ip.episode_ref = cl.episode_ref;
```

---

## Example 7: Surgical procedures with timestamps

```sql
WITH surgeries AS (
    SELECT 
        patient_ref,
        episode_ref,
        surgery_ref,
        surgery_code,
        surgery_code_descr,
        start_date,
        end_date
    FROM g_surgery
    WHERE start_date >= '2024-01-01'
),
surgery_events AS (
    SELECT 
        surgery_ref,
        event_label,
        event_descr,
        event_timestamp
    FROM g_surgery_timestamps
)
SELECT 
    s.*,
    se.event_descr,
    se.event_timestamp
FROM surgeries s
LEFT JOIN surgery_events se ON s.surgery_ref = se.surgery_ref
ORDER BY s.patient_ref, s.start_date, se.event_timestamp;
```

---

## Example 8: Mortality analysis by diagnosis

```sql
WITH patient_deaths AS (
    SELECT 
        patient_ref,
        exitus_date
    FROM g_exitus
),
patient_diagnoses AS (
    SELECT DISTINCT
        patient_ref,
        diag_descr
    FROM g_diagnostics
    WHERE class = 'P'  -- Primary diagnosis
)
SELECT 
    pd.diag_descr,
    COUNT(DISTINCT pd.patient_ref) AS total_patients,
    COUNT(DISTINCT ex.patient_ref) AS deceased_patients
FROM patient_diagnoses pd
LEFT JOIN patient_deaths ex ON pd.patient_ref = ex.patient_ref
GROUP BY pd.diag_descr
ORDER BY deceased_patients DESC;
```

---

## Example 9: Clinical records (vital signs) for episode

```sql
WITH vital_signs AS (
    SELECT 
        patient_ref,
        episode_ref,
        result_date,
        rc_sap_ref,
        rc_descr,
        result_num,
        units
    FROM g_rc
    WHERE rc_sap_ref IN ('FC', 'TAS', 'TAD', 'FR', 'TEMP', 'SAT_O2')
        AND episode_ref = 123456  -- Replace with actual episode
)
SELECT * FROM vital_signs
ORDER BY result_date;
```

---

## Example 10: Patient movement history

```sql
WITH movements AS (
    SELECT 
        patient_ref,
        episode_ref,
        start_date,
        end_date,
        ou_med_descr,
        ou_loc_descr,
        care_level_type_ref
    FROM g_movements
    WHERE patient_ref = 12345  -- Replace with actual patient
)
SELECT * FROM movements
ORDER BY start_date;
```
