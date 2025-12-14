WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ('E073', 'I073')
      AND start_date BETWEEN '2024-01-01' AND '2024-12-31 23:59:59'
),
-- Identify where a new "stay" actually begins (previous end != current start)
flagged_starts AS (
    SELECT 
        *,
        CASE 
            WHEN LAG(end_date) OVER (PARTITION BY episode_ref ORDER BY start_date) = start_date 
            THEN 0 ELSE 1 
        END AS is_new_stay
    FROM raw_moves
),
-- Create a unique ID for each continuous stay
grouped_stays AS (
    SELECT 
        *,
        SUM(is_new_stay) OVER (PARTITION BY episode_ref ORDER BY start_date) as stay_id
    FROM flagged_starts
)
-- Aggregate to get the TRUE start and TRUE end
SELECT 
    patient_ref,
    episode_ref,
    MIN(start_date) as true_start_date,
    MAX(end_date) as true_end_date,
    TIMESTAMPDIFF(MINUTE, MIN(start_date), MAX(end_date)) / 60.0 as total_hours
FROM grouped_stays
GROUP BY patient_ref, episode_ref, stay_id
HAVING total_hours >= 10 -- Filter for > 10 hours here
ORDER BY episode_ref, true_start_date