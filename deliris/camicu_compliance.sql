-- camicu_compliance.sql -> camicu_compliance.csv (run_sql.py)
-- CAM-ICU compliance: % of eligible shifts (RASS -3 to +4) with CAM-ICU recorded
-- Handles both RASS formats: coded (pre-2022) and numeric (2022+)
-- All ICUs | Period: 2018-2025

WITH all_related_moves AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref,
        start_date, end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM g_movements
    WHERE ou_loc_ref IN ('E016','E103','E014','E015','E037','E057','E073','E043')
      AND start_date <= '2025-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '2018-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    SELECT *,
        CASE
            WHEN ABS(TIMESTAMPDIFF(MINUTE,
                LAG(effective_end_date) OVER (
                    PARTITION BY patient_ref, episode_ref, ou_loc_ref
                    ORDER BY start_date
                ),
                start_date
            )) <= 5
            THEN 0 ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    SELECT *,
        SUM(is_new_stay) OVER (
            PARTITION BY patient_ref, episode_ref, ou_loc_ref
            ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref, stay_id,
        MIN(start_date) AS admission_date,
        MAX(effective_end_date) AS effective_discharge_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING YEAR(MIN(start_date)) BETWEEN 2018 AND 2025
),

-- RASS: filter eligible values in both formats
rass_eligible AS (
    SELECT 
        c.patient_ref,
        c.ou_loc_ref,
        c.episode_ref,
        c.stay_id,
        r.result_date,
        CASE
            WHEN HOUR(r.result_date) >= 8  AND HOUR(r.result_date) < 15 THEN 'M'
            WHEN HOUR(r.result_date) >= 15 AND HOUR(r.result_date) < 22 THEN 'A'
            ELSE 'N'
        END AS shift,
        CASE
            WHEN HOUR(r.result_date) < 8 THEN DATE(r.result_date) - INTERVAL 1 DAY
            ELSE DATE(r.result_date)
        END AS shift_date
    FROM g_rc r
    INNER JOIN cohort c
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date BETWEEN c.admission_date AND c.effective_discharge_date
    WHERE r.rc_sap_ref = 'SEDACION_RASS'
      AND (
          -- Old format (pre-2022): SEDACION_RASS_3 to _10 = RASS -3 to +4
          r.result_txt IN ('SEDACION_RASS_3','SEDACION_RASS_4','SEDACION_RASS_5',
                           'SEDACION_RASS_6','SEDACION_RASS_7','SEDACION_RASS_8',
                           'SEDACION_RASS_9','SEDACION_RASS_10')
          OR
          -- New format (2022+): numeric string
          (r.result_txt REGEXP '^-?[0-9]+$' AND CAST(r.result_txt AS SIGNED) BETWEEN -3 AND 4)
      )
),

-- Eligible shifts: at least one eligible RASS per shift
eligible_shifts AS (
    SELECT 
        patient_ref, ou_loc_ref, episode_ref, stay_id,
        shift_date, shift,
        COUNT(*) AS n_rass
    FROM rass_eligible
    GROUP BY patient_ref, ou_loc_ref, episode_ref, stay_id, shift_date, shift
),

-- CAM-ICU records
cam_shifts AS (
    SELECT DISTINCT
        c.patient_ref,
        c.ou_loc_ref,
        CASE
            WHEN HOUR(r.result_date) >= 8  AND HOUR(r.result_date) < 15 THEN 'M'
            WHEN HOUR(r.result_date) >= 15 AND HOUR(r.result_date) < 22 THEN 'A'
            ELSE 'N'
        END AS shift,
        CASE
            WHEN HOUR(r.result_date) < 8 THEN DATE(r.result_date) - INTERVAL 1 DAY
            ELSE DATE(r.result_date)
        END AS shift_date
    FROM g_rc r
    INNER JOIN cohort c
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date BETWEEN c.admission_date AND c.effective_discharge_date
    WHERE r.rc_sap_ref = 'DELIRIO_CAM-ICU'
)

-- Compliance by unit, year, and shift
SELECT 
    e.ou_loc_ref,
    YEAR(e.shift_date) AS yr,
    e.shift,
    COUNT(*) AS eligible_shifts,
    SUM(CASE WHEN cs.patient_ref IS NOT NULL THEN 1 ELSE 0 END) AS shifts_with_cam,
    ROUND(100.0 * SUM(CASE WHEN cs.patient_ref IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_compliance
FROM eligible_shifts e
LEFT JOIN cam_shifts cs
    ON e.patient_ref = cs.patient_ref
    AND e.ou_loc_ref = cs.ou_loc_ref
    AND e.shift_date = cs.shift_date
    AND e.shift = cs.shift
GROUP BY e.ou_loc_ref, YEAR(e.shift_date), e.shift
ORDER BY e.ou_loc_ref, yr, FIELD(e.shift, 'M', 'A', 'N');