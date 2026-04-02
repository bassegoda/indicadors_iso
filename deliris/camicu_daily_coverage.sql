-- camicu_daily_coverage.sql -> camicu_daily_coverage.csv (run_sql.py)
-- Share of completed ICU stays with at least one CAM-ICU on every calendar day of the stay.
-- Cohort: same ICU list as other camicu_* queries; only stays where every movement row has a
-- real closed end_date (no open segments, no far-future placeholders).
-- Calendar days: inclusive from DATE(admission) through DATE(discharge).
-- CAM days: DISTINCT DATE(result_date) for rc_sap_ref = 'DELIRIO_CAM-ICU' within [admission, discharge].

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
        DATEDIFF(DATE(MAX(end_date)), DATE(MIN(start_date))) + 1 AS n_icu_calendar_days
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING YEAR(MIN(start_date)) BETWEEN 2018 AND 2025
      AND COUNT(*) = COUNT(
            CASE WHEN end_date IS NOT NULL AND end_date <= NOW() THEN 1 END
          )
      AND DATEDIFF(DATE(MAX(end_date)), DATE(MIN(start_date))) + 1 > 0
),

per_stay AS (
    SELECT
        c.ou_loc_ref,
        YEAR(c.admission_date) AS yr,
        c.patient_ref,
        c.episode_ref,
        c.stay_id,
        c.n_icu_calendar_days,
        COUNT(DISTINCT DATE(r.result_date)) AS days_with_cam
    FROM cohort c
    LEFT JOIN g_rc r
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date >= c.admission_date
        AND r.result_date <= c.discharge_date
        AND r.rc_sap_ref = 'DELIRIO_CAM-ICU'
    GROUP BY
        c.ou_loc_ref, YEAR(c.admission_date),
        c.patient_ref, c.episode_ref, c.stay_id, c.n_icu_calendar_days
)

SELECT
    ou_loc_ref,
    yr,
    COUNT(*) AS n_stays,
    SUM(CASE WHEN days_with_cam >= n_icu_calendar_days THEN 1 ELSE 0 END) AS n_stays_cam_all_days,
    SUM(CASE WHEN days_with_cam >= 1 THEN 1 ELSE 0 END) AS n_stays_cam_any_day,
    ROUND(
        100.0 * SUM(CASE WHEN days_with_cam >= n_icu_calendar_days THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS pct_stays_cam_all_days,
    ROUND(
        100.0 * SUM(CASE WHEN days_with_cam >= 1 THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS pct_stays_cam_any_day,
    ROUND(AVG(100.0 * days_with_cam / n_icu_calendar_days), 1) AS avg_pct_calendar_days_with_cam
FROM per_stay
GROUP BY ou_loc_ref, yr
ORDER BY ou_loc_ref, yr;
