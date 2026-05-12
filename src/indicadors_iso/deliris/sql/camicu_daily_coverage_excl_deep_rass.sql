-- camicu_daily_coverage_excl_deep_rass.sql -> camicu_daily_coverage_excl_deep_rass.csv (run_sql.py)
-- Share of completed ICU stays with >=1 CAM-ICU on every *evaluable* calendar day.
-- Evaluable day = ICU calendar day with NO RASS of -5 or -4 recorded that same calendar day
--   (old coded: SEDACION_RASS_1 = -5, SEDACION_RASS_2 = -4; numeric: result_txt -5 / -4).
-- Days with only deep sedation RASS are excluded from the CAM requirement (cannot assess CAM-ICU).
-- Denominator for pct_stays_cam_all_evaluable_days: stays with at least one evaluable day.
-- Cohort: same ICUs and closed-stay rules as camicu_daily_coverage.sql
-- Dialect: Athena (Trino/Presto) — uses UNNEST(sequence(...)) instead of WITH RECURSIVE

WITH nums AS (
    SELECT n FROM UNNEST(sequence(0, 800)) AS t(n)
),
all_related_moves AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref,
        start_date, end_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ('E016','E103','E014','E015','E037','E057','E073','E043')
      AND start_date <= timestamp '2025-12-31 23:59:59'
      AND COALESCE(end_date, current_timestamp) >= timestamp '2018-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, current_timestamp) > start_date
),
flagged_starts AS (
    SELECT *,
        CASE
            WHEN ABS(date_diff('minute',
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
        MAX(end_date) AS discharge_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN 2018 AND 2025
      AND COUNT(*) = COUNT(
            CASE WHEN end_date IS NOT NULL AND end_date <= current_timestamp THEN 1 END
          )
      AND date_diff('day', cast(MIN(start_date) as date), cast(MAX(end_date) as date)) + 1 > 0
),

stay_calendar_days AS (
    SELECT
        c.ou_loc_ref,
        year(c.admission_date) AS yr,
        c.patient_ref,
        c.episode_ref,
        c.stay_id,
        date_add('day', n.n, cast(c.admission_date as date)) AS cal_day
    FROM cohort c
    INNER JOIN nums n
        ON n.n <= date_diff('day', cast(c.admission_date as date), cast(c.discharge_date as date))
),

rass_deep_sedation_day AS (
    SELECT DISTINCT
        c.patient_ref,
        c.episode_ref,
        c.ou_loc_ref,
        c.stay_id,
        cast(r.result_date as date) AS cal_day
    FROM cohort c
    INNER JOIN datascope_gestor_prod.rc r
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date >= c.admission_date
        AND r.result_date <= c.discharge_date
        AND r.rc_sap_ref = 'SEDACION_RASS'
        AND (
            r.result_txt IN ('SEDACION_RASS_1', 'SEDACION_RASS_2')
            OR (
                regexp_like(r.result_txt, '^-?[0-9]+$')
                AND cast(r.result_txt as bigint) IN (-5, -4)
            )
        )
),
cam_days AS (
    SELECT DISTINCT
        c.patient_ref,
        c.episode_ref,
        c.ou_loc_ref,
        c.stay_id,
        cast(r.result_date as date) AS cal_day
    FROM cohort c
    INNER JOIN datascope_gestor_prod.rc r
        ON r.patient_ref = c.patient_ref
        AND r.ou_loc_ref = c.ou_loc_ref
        AND r.result_date >= c.admission_date
        AND r.result_date <= c.discharge_date
        AND r.rc_sap_ref = 'DELIRIO_CAM-ICU'
),

per_stay AS (
    SELECT
        scd.ou_loc_ref,
        scd.yr,
        scd.patient_ref,
        scd.episode_ref,
        scd.stay_id,
        SUM(CASE WHEN r.patient_ref IS NULL THEN 1 ELSE 0 END) AS n_evaluable_days,
        SUM(
            CASE
                WHEN r.patient_ref IS NULL AND cm.patient_ref IS NOT NULL THEN 1
                ELSE 0
            END
        ) AS n_evaluable_days_with_cam
    FROM stay_calendar_days scd
    LEFT JOIN rass_deep_sedation_day r
        ON scd.patient_ref = r.patient_ref
        AND scd.episode_ref = r.episode_ref
        AND scd.ou_loc_ref = r.ou_loc_ref
        AND scd.stay_id = r.stay_id
        AND scd.cal_day = r.cal_day
    LEFT JOIN cam_days cm
        ON scd.patient_ref = cm.patient_ref
        AND scd.episode_ref = cm.episode_ref
        AND scd.ou_loc_ref = cm.ou_loc_ref
        AND scd.stay_id = cm.stay_id
        AND scd.cal_day = cm.cal_day
    GROUP BY
        scd.ou_loc_ref,
        scd.yr,
        scd.patient_ref,
        scd.episode_ref,
        scd.stay_id
)

SELECT
    ou_loc_ref,
    yr,
    COUNT(*) AS n_stays,
    SUM(CASE WHEN n_evaluable_days >= 1 THEN 1 ELSE 0 END) AS n_stays_with_evaluable_day,
    SUM(
        CASE
            WHEN n_evaluable_days >= 1
                 AND n_evaluable_days_with_cam >= n_evaluable_days
            THEN 1
            ELSE 0
        END
    ) AS n_stays_cam_all_evaluable_days,
    SUM(CASE WHEN n_evaluable_days = 0 THEN 1 ELSE 0 END) AS n_stays_no_evaluable_day,
    ROUND(
        100.0 * SUM(
            CASE
                WHEN n_evaluable_days >= 1
                     AND n_evaluable_days_with_cam >= n_evaluable_days
                THEN 1
                ELSE 0
            END
        ) / NULLIF(SUM(CASE WHEN n_evaluable_days >= 1 THEN 1 ELSE 0 END), 0),
        1
    ) AS pct_stays_cam_all_evaluable_days,
    ROUND(
        AVG(
            CASE
                WHEN n_evaluable_days >= 1
                THEN 100.0 * n_evaluable_days_with_cam / n_evaluable_days
            END
        ),
        1
    ) AS avg_pct_evaluable_days_with_cam
FROM per_stay
GROUP BY ou_loc_ref, yr
ORDER BY ou_loc_ref, yr;
