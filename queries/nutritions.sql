WITH movement_data AS (
    SELECT 
        m.patient_ref,
        m.episode_ref,
        m.start_date,
        m.end_date,
        TIMESTAMPDIFF(hour, m.start_date, m.end_date) AS horesingres,
        LEAD(m.start_date) OVER (PARTITION BY m.episode_ref ORDER BY m.start_date) AS next_start_date
    FROM
        g_mov_events AS m
    WHERE 
        ou_loc_ref IN ('E073', 'I073') 
        AND start_date BETWEEN '2023-01-01 00:00:00' AND '2023-12-31 23:59:59'
        AND m.start_date != m.end_date
        AND TIMESTAMPDIFF(hour, m.start_date, m.end_date) > 1
),
fc AS (
    SELECT *
    FROM movement_data
    WHERE next_start_date IS NULL
       OR end_date != next_start_date
),
fc_with_drugs AS (
    SELECT 
        fc.episode_ref, 
        fc.start_date, 
        pe.start_drug_date, 
        pe.drug_descr,
        ROW_NUMBER() OVER (PARTITION BY fc.episode_ref ORDER BY pe.start_drug_date ASC) AS rn
    FROM 
        fc
    INNER JOIN 
        g_prescription_events AS pe
    ON 
        fc.episode_ref = pe.episode_ref
    WHERE 
        pe.drug_descr IN ('NUTRICION ENTERAL', 'NUTRICIÓN PARENTERAL CENTRAL')
)
SELECT 
    episode_ref, 
    start_date, 
    start_drug_date, 
    drug_descr, 
    TIMESTAMPDIFF(hour, start_date, start_drug_date) AS hours_difference
FROM 
    fc_with_drugs
WHERE 
    rn = 1
    AND TIMESTAMPDIFF(hour, start_date, start_drug_date) > 0
ORDER BY 
    episode_ref, start_date;
