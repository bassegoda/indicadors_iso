WITH movement_data AS (
    SELECT 
        m.patient_ref,
        m.episode_ref,
        m.start_date,
        m.end_date,
        TIMESTAMPDIFF(hour, m.start_date, m.end_date) AS horesingres,
        LEAD(m.start_date) OVER (PARTITION BY m.episode_ref ORDER BY m.start_date) AS next_start_date
    FROM
        g_movements as m
    WHERE 
        ou_loc_ref IN ('E073', 'I073') 
        AND start_date BETWEEN '2023-01-01 00:00:00' AND '2023-12-31 23:59:59'
        AND m.start_date != m.end_date
        AND TIMESTAMPDIFF(hour, m.start_date, m.end_date) > 1
),
final_cohort AS (
SELECT *
FROM movement_data
WHERE next_start_date IS NULL
   OR end_date != next_start_date
ORDER BY episode_ref, start_date
)
SELECT * FROM final_cohort
