WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ('E073', 'I073')
      AND start_date BETWEEN '2025-01-01' AND '2025-12-31 23:59:59'
),
flagged_starts AS (
    SELECT 
        *,
        -- Flag as new stay if the previous end_date does not match current start_date
        CASE 
            WHEN LAG(end_date) OVER (PARTITION BY episode_ref ORDER BY start_date) = start_date 
            THEN 0 
            ELSE 1 
        END AS is_new_stay
    FROM raw_moves
),
grouped_stays AS (
    SELECT 
        *,
        -- Create a unique ID for the contiguous stay
        SUM(is_new_stay) OVER (PARTITION BY episode_ref ORDER BY start_date) as stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT 
        patient_ref,
        episode_ref,
        stay_id,
        -- Determine the Unit for this stay (MIN picks the first alphabetical if mixed, usually consistent)
        MIN(ou_loc_ref) as ou_loc_ref, 
        MIN(start_date) as true_start_date,
        MAX(end_date) as true_end_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) >= 10
),
-- Look ahead to find the next admission for the same patient to calc readmission
cohort_with_next AS (
    SELECT 
        *,
        -- Get the start date of the NEXT stay for this patient
        LEAD(true_start_date) OVER (PARTITION BY patient_ref ORDER BY true_start_date) as next_admission_date
    FROM cohort
),
-- Pre-calculate Cirrhosis prevalence
cirrhosis_dx AS (
    SELECT DISTINCT patient_ref
    FROM g_diagnostics
    WHERE code LIKE 'K70.3%'  
       OR code LIKE 'K71.7%'  
       OR code LIKE 'K74.3%'  
       OR code LIKE 'K74.4%'  
       OR code LIKE 'K74.5%'  
       OR code LIKE 'K74.6%' 
)
SELECT 
    c.patient_ref,
    c.episode_ref,
    c.ou_loc_ref,        
    c.true_start_date,
    c.true_end_date,
    c.total_hours,
    -- Demographics
    d.sex,
    d.natio_descr AS nationality,
    TIMESTAMPDIFF(YEAR, d.birth_date, c.true_start_date) AS age_at_start,
    d.postcode,
    d.health_area,
    -- Cirrhosis Flag
    CASE 
        WHEN dx.patient_ref IS NOT NULL THEN 1 
        ELSE 0 
    END AS has_cirrhosis,
    -- Exitus Flag
    CASE 
        WHEN e.exitus_date BETWEEN c.true_start_date AND c.true_end_date THEN 1 
        ELSE 0 
    END AS exitus_in_icu,
    -- Readmission Flags
    CASE 
        WHEN c.next_admission_date IS NOT NULL 
             AND TIMESTAMPDIFF(HOUR, c.true_end_date, c.next_admission_date) <= 24 
        THEN 1 
        ELSE 0 
    END AS readmission_at_24h,
    CASE 
        WHEN c.next_admission_date IS NOT NULL 
             AND TIMESTAMPDIFF(HOUR, c.true_end_date, c.next_admission_date) <= 72 
        THEN 1 
        ELSE 0 
    END AS readmission_at_72h
FROM cohort_with_next c
LEFT JOIN g_demographics d 
    ON c.patient_ref = d.patient_ref
LEFT JOIN cirrhosis_dx dx
    ON c.patient_ref = dx.patient_ref
LEFT JOIN g_exitus e
    ON c.patient_ref = e.patient_ref
ORDER BY c.episode_ref, c.true_start_date;