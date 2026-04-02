-- CAM-ICU positivity rate: % of recorded CAM-ICU that are positive
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

-- CAM-ICU records classified
cam_results AS (
    SELECT 
        c.ou_loc_ref,
        YEAR(r.result_date) AS yr,
        r.result_txt,
        CASE
            WHEN r.result_txt = 'DELIRIO_CAM-ICU_2' THEN 'positive'
            WHEN r.result_txt = 'DELIRIO_CAM-ICU_1' THEN 'negative'
            WHEN r.result_txt = 'DELIRIO_CAM-ICU_3' THEN 'other'
            ELSE 'unknown'
        END AS cam_result
    FROM g_rc r
    INNER JOIN cohort c
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date BETWEEN c.admission_date AND c.effective_discharge_date
    WHERE r.rc_sap_ref = 'DELIRIO_CAM-ICU'
)

SELECT 
    ou_loc_ref,
    yr,
    COUNT(*) AS total_cam,
    SUM(CASE WHEN cam_result = 'positive' THEN 1 ELSE 0 END) AS n_positive,
    SUM(CASE WHEN cam_result = 'negative' THEN 1 ELSE 0 END) AS n_negative,
    SUM(CASE WHEN cam_result = 'other' THEN 1 ELSE 0 END) AS n_other,
    ROUND(100.0 * SUM(CASE WHEN cam_result = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_positive,
    ROUND(100.0 * SUM(CASE WHEN cam_result = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_negative
FROM cam_results
GROUP BY ou_loc_ref, yr
ORDER BY ou_loc_ref, yr;