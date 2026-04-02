-- RASS coverage: % of theoretical patient-shifts with at least one RASS recorded
-- Excludes still-admitted patients to avoid inflated theoretical shifts
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
        MAX(end_date) AS discharge_date,
        MAX(effective_end_date) AS effective_discharge_date,
        CASE WHEN MAX(end_date) IS NULL THEN 1 ELSE 0 END AS still_admitted,
        -- Theoretical shifts: shift-days × 3
        (DATEDIFF(
            CASE WHEN HOUR(MAX(effective_end_date)) < 8
                 THEN DATE(MAX(effective_end_date)) - INTERVAL 1 DAY
                 ELSE DATE(MAX(effective_end_date)) END,
            CASE WHEN HOUR(MIN(start_date)) < 8
                 THEN DATE(MIN(start_date)) - INTERVAL 1 DAY
                 ELSE DATE(MIN(start_date)) END
        ) + 1) * 3 AS theoretical_shifts
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING YEAR(MIN(start_date)) BETWEEN 2018 AND 2025
      AND MAX(end_date) IS NOT NULL  -- Exclude still-admitted
),

-- Count distinct shifts with ANY RASS recorded per stay
rass_coverage AS (
    SELECT 
        c.patient_ref, c.episode_ref, c.ou_loc_ref, c.stay_id,
        COUNT(DISTINCT CONCAT(
            CASE WHEN HOUR(r.result_date) < 8 
                 THEN DATE(r.result_date) - INTERVAL 1 DAY
                 ELSE DATE(r.result_date) END,
            '-',
            CASE
                WHEN HOUR(r.result_date) >= 8  AND HOUR(r.result_date) < 15 THEN 'M'
                WHEN HOUR(r.result_date) >= 15 AND HOUR(r.result_date) < 22 THEN 'A'
                ELSE 'N'
            END
        )) AS shifts_with_rass
    FROM cohort c
    LEFT JOIN g_rc r
        ON c.patient_ref = r.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date BETWEEN c.admission_date AND c.effective_discharge_date
        AND r.rc_sap_ref = 'SEDACION_RASS'
    GROUP BY c.patient_ref, c.episode_ref, c.ou_loc_ref, c.stay_id
)

-- Aggregate by unit and year
SELECT 
    c.ou_loc_ref,
    YEAR(c.admission_date) AS yr,
    COUNT(*) AS n_stays,
    SUM(c.theoretical_shifts) AS total_theoretical,
    SUM(rc.shifts_with_rass) AS total_with_rass,
    ROUND(100.0 * SUM(rc.shifts_with_rass) / SUM(c.theoretical_shifts), 1) AS pct_rass_coverage,
    ROUND(AVG(100.0 * rc.shifts_with_rass / c.theoretical_shifts), 1) AS avg_coverage_per_stay,
    SUM(CASE WHEN rc.shifts_with_rass = 0 THEN 1 ELSE 0 END) AS stays_without_any_rass,
    ROUND(100.0 * SUM(CASE WHEN rc.shifts_with_rass = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_stays_no_rass
FROM cohort c
INNER JOIN rass_coverage rc
    ON c.patient_ref = rc.patient_ref
    AND c.episode_ref = rc.episode_ref
    AND c.ou_loc_ref = rc.ou_loc_ref
    AND c.stay_id = rc.stay_id
GROUP BY c.ou_loc_ref, YEAR(c.admission_date)
ORDER BY c.ou_loc_ref, yr;