WITH base_data AS (
    -- Afegim duracio dels moviments i una columna amb la next_start_date: data del següent moviment dins del mateix episodi
    WITH cte_with_durations AS (
        SELECT 
            m.*,
            TIMESTAMPDIFF(hour, m.start_date, m.end_date) AS horesingres,
            LEAD(m.start_date) OVER (PARTITION BY m.episode_ref ORDER BY m.start_date) AS next_start_date
        FROM 
            g_mov_events AS m
        WHERE 
            (m.ou_loc_ref = 'I073' OR m.ou_loc_ref = 'E073') 
            AND m.start_date != m.end_date 
            AND TIMESTAMPDIFF(hour, m.start_date, m.end_date) > 6
    ),
    cte_longest_stay AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY episode_ref ORDER BY horesingres DESC) AS rn_max_duration
        FROM 
            cte_with_durations
    ),
    cte_filtered_movements AS (
        SELECT 
            *
        FROM 
            cte_with_durations
        WHERE 
            end_date != next_start_date OR next_start_date IS NULL
    )
    SELECT 
        DISTINCT a.*
    FROM 
        cte_filtered_movements AS a
    LEFT JOIN 
        cte_longest_stay AS b
    ON 
        a.episode_ref = b.episode_ref AND b.rn_max_duration = 1
    WHERE 
        b.rn_max_duration = 1 OR a.end_date != a.next_start_date
),
deliriums AS ( 
	SELECT episode_ref, descr
    FROM g_rc_events
    WHERE descr = 'Grado de delirio según escala CAM-ICU'
)
-- Join with other tables here
SELECT 
	bd.*,
    d.*
FROM
	base_data as bd
LEFT JOIN
	deliriums as d
ON 
	bd.episode_ref = d.episode_ref  

;