"""SQL templates for the 2024 vs 2025 data-completeness comparison.

Each template is parameterised by ``{y1}`` (reference year, typically 2024) and
``{y2}`` (year under scrutiny, typically 2025). Two extra placeholders,
``{ytd_cutoff_y1}`` and ``{ytd_cutoff_y2}``, are ISO dates used for
year-to-date (YTD) comparisons.

All queries target Athena/Trino (``datascope_gestor_prod.*``).
"""

# Block 1 - Totals (full year + YTD) for movements and labs
SQL_TOTALS_MOVEMENTS = """
SELECT
    year(start_date) AS yr,
    COUNT(*)                          AS n_rows,
    COUNT(DISTINCT patient_ref)       AS n_patients,
    COUNT(DISTINCT episode_ref)       AS n_episodes,
    COUNT(DISTINCT care_level_ref)    AS n_care_levels,
    MIN(start_date)                   AS first_start_date,
    MAX(start_date)                   AS last_start_date,
    MIN(load_date)                    AS first_load_date,
    MAX(load_date)                    AS last_load_date
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
GROUP BY year(start_date)
ORDER BY yr
"""

SQL_TOTALS_LABS = """
SELECT
    year(extrac_date) AS yr,
    COUNT(*)                          AS n_rows,
    COUNT(DISTINCT patient_ref)       AS n_patients,
    COUNT(DISTINCT episode_ref)       AS n_episodes,
    COUNT(DISTINCT lab_sap_ref)       AS n_lab_params,
    MIN(extrac_date)                  AS first_extrac_date,
    MAX(extrac_date)                  AS last_extrac_date,
    MIN(load_date)                    AS first_load_date,
    MAX(load_date)                    AS last_load_date
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
GROUP BY year(extrac_date)
ORDER BY yr
"""

# YTD totals. Filtered by the same month/day cut-off (today's month-day of the
# year under scrutiny) to get an apples-to-apples comparison insensitive to
# end-of-year backlogs.
SQL_YTD_MOVEMENTS = """
SELECT
    year(start_date) AS yr,
    COUNT(*)                        AS n_rows,
    COUNT(DISTINCT patient_ref)     AS n_patients,
    COUNT(DISTINCT episode_ref)     AS n_episodes,
    COUNT(DISTINCT care_level_ref)  AS n_care_levels
FROM datascope_gestor_prod.movements
WHERE (year(start_date) = {y1} AND start_date <= timestamp '{ytd_cutoff_y1} 23:59:59')
   OR (year(start_date) = {y2} AND start_date <= timestamp '{ytd_cutoff_y2} 23:59:59')
GROUP BY year(start_date)
ORDER BY yr
"""

SQL_YTD_LABS = """
SELECT
    year(extrac_date) AS yr,
    COUNT(*)                      AS n_rows,
    COUNT(DISTINCT patient_ref)   AS n_patients,
    COUNT(DISTINCT episode_ref)   AS n_episodes,
    COUNT(DISTINCT lab_sap_ref)   AS n_lab_params
FROM datascope_gestor_prod.labs
WHERE (year(extrac_date) = {y1} AND extrac_date <= timestamp '{ytd_cutoff_y1} 23:59:59')
   OR (year(extrac_date) = {y2} AND extrac_date <= timestamp '{ytd_cutoff_y2} 23:59:59')
GROUP BY year(extrac_date)
ORDER BY yr
"""

# Block 2 - Monthly series
SQL_MONTHLY_MOVEMENTS = """
SELECT
    year(start_date)  AS yr,
    month(start_date) AS mth,
    COUNT(*)                       AS n_rows,
    COUNT(DISTINCT patient_ref)    AS n_patients,
    COUNT(DISTINCT episode_ref)    AS n_episodes
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
GROUP BY year(start_date), month(start_date)
ORDER BY yr, mth
"""

SQL_MONTHLY_LABS = """
SELECT
    year(extrac_date)  AS yr,
    month(extrac_date) AS mth,
    COUNT(*)                       AS n_rows,
    COUNT(DISTINCT patient_ref)    AS n_patients,
    COUNT(DISTINCT episode_ref)    AS n_episodes
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
GROUP BY year(extrac_date), month(extrac_date)
ORDER BY yr, mth
"""

# Block 3 - Daily series (heatmap input)
SQL_DAILY_MOVEMENTS = """
SELECT
    CAST(date_trunc('day', start_date) AS DATE) AS day,
    COUNT(*) AS n_rows
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
GROUP BY CAST(date_trunc('day', start_date) AS DATE)
ORDER BY day
"""

SQL_DAILY_LABS = """
SELECT
    CAST(date_trunc('day', extrac_date) AS DATE) AS day,
    COUNT(*) AS n_rows
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
GROUP BY CAST(date_trunc('day', extrac_date) AS DATE)
ORDER BY day
"""

# Block 4 - Rows-per-episode ratio (movements and labs)
#
# We compute the ratio at the month level: COUNT(*) / COUNT(DISTINCT episode_ref).
# A stable ratio across years -> missing whole episodes (activity drop).
# A ratio drop -> episodes exist but rows are missing (incomplete ETL of children).
SQL_RATIOS_MOVEMENTS = """
SELECT
    year(start_date)               AS yr,
    month(start_date)              AS mth,
    COUNT(*)                       AS n_rows,
    COUNT(DISTINCT episode_ref)    AS n_episodes,
    CAST(COUNT(*) AS DOUBLE) / NULLIF(COUNT(DISTINCT episode_ref), 0) AS rows_per_episode
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
  AND episode_ref IS NOT NULL
GROUP BY year(start_date), month(start_date)
ORDER BY yr, mth
"""

SQL_RATIOS_LABS = """
SELECT
    year(extrac_date)              AS yr,
    month(extrac_date)             AS mth,
    COUNT(*)                       AS n_rows,
    COUNT(DISTINCT episode_ref)    AS n_episodes,
    CAST(COUNT(*) AS DOUBLE) / NULLIF(COUNT(DISTINCT episode_ref), 0) AS rows_per_episode
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
  AND episode_ref IS NOT NULL
GROUP BY year(extrac_date), month(extrac_date)
ORDER BY yr, mth
"""

# Block 5 - Orphan episodes: HOSP/HOSP_IQ/HOSP_RN/EM/HAH episodes with no movements.
SQL_ORPHAN_EPISODES = """
WITH target_episodes AS (
    SELECT episode_ref, patient_ref, episode_type_ref, start_date
    FROM datascope_gestor_prod.episodes
    WHERE episode_type_ref IN ('HOSP', 'HOSP_IQ', 'HOSP_RN', 'EM', 'HAH')
      AND year(start_date) IN ({y1}, {y2})
),
episodes_with_moves AS (
    SELECT DISTINCT episode_ref
    FROM datascope_gestor_prod.movements
    WHERE episode_ref IS NOT NULL
)
SELECT
    year(te.start_date)     AS yr,
    te.episode_type_ref     AS episode_type,
    COUNT(*)                AS n_episodes,
    SUM(CASE WHEN ewm.episode_ref IS NULL THEN 1 ELSE 0 END) AS n_orphans
FROM target_episodes te
LEFT JOIN episodes_with_moves ewm
    ON te.episode_ref = ewm.episode_ref
GROUP BY year(te.start_date), te.episode_type_ref
ORDER BY yr, episode_type
"""

# Block 6 - load_date freshness: for each (yr, mth) of start_date/extrac_date,
# what's the max load_date?  Big gap between the clinical event month and
# max(load_date) => stale / halted ETL for that window.
SQL_LOAD_FRESHNESS_MOVEMENTS = """
SELECT
    year(start_date)  AS yr,
    month(start_date) AS mth,
    MIN(load_date)    AS min_load_date,
    MAX(load_date)    AS max_load_date,
    COUNT(*)          AS n_rows
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
  AND load_date IS NOT NULL
GROUP BY year(start_date), month(start_date)
ORDER BY yr, mth
"""

SQL_LOAD_FRESHNESS_LABS = """
SELECT
    year(extrac_date)  AS yr,
    month(extrac_date) AS mth,
    MIN(load_date)     AS min_load_date,
    MAX(load_date)     AS max_load_date,
    COUNT(*)           AS n_rows
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
  AND load_date IS NOT NULL
GROUP BY year(extrac_date), month(extrac_date)
ORDER BY yr, mth
"""

# Block 7 - Breakdown by unit / facility / lab parameter. Pivoted in Python.
SQL_BREAKDOWN_OU_LOC = """
SELECT
    COALESCE(ou_loc_ref, '(null)')     AS ou_loc_ref,
    MAX(ou_loc_descr)                   AS ou_loc_descr,
    year(start_date)                    AS yr,
    COUNT(*)                            AS n_rows
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
GROUP BY COALESCE(ou_loc_ref, '(null)'), year(start_date)
ORDER BY ou_loc_ref, yr
"""

SQL_BREAKDOWN_FACILITY = """
SELECT
    COALESCE(facility, '(null)')  AS facility,
    year(start_date)              AS yr,
    COUNT(*)                      AS n_rows
FROM datascope_gestor_prod.movements
WHERE year(start_date) IN ({y1}, {y2})
GROUP BY COALESCE(facility, '(null)'), year(start_date)
ORDER BY facility, yr
"""

SQL_BREAKDOWN_LAB_PARAM = """
SELECT
    COALESCE(lab_sap_ref, '(null)') AS lab_sap_ref,
    MAX(lab_descr)                   AS lab_descr,
    year(extrac_date)                AS yr,
    COUNT(*)                         AS n_rows
FROM datascope_gestor_prod.labs
WHERE year(extrac_date) IN ({y1}, {y2})
GROUP BY COALESCE(lab_sap_ref, '(null)'), year(extrac_date)
ORDER BY lab_sap_ref, yr
"""


def format_query(template: str, y1: int, y2: int,
                 ytd_cutoff_y1: str = "", ytd_cutoff_y2: str = "") -> str:
    """Fill year (and YTD) placeholders in a SQL template."""
    return template.format(
        y1=y1,
        y2=y2,
        ytd_cutoff_y1=ytd_cutoff_y1,
        ytd_cutoff_y2=ytd_cutoff_y2,
    )
