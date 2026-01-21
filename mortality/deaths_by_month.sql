SELECT
    YEAR(exitus_date) AS year,
    MONTH(exitus_date) AS month,
    COUNT(*) AS deaths
FROM g_exitus
WHERE exitus_date IS NOT NULL
    {date_filter}
GROUP BY YEAR(exitus_date), MONTH(exitus_date)
ORDER BY year, month;
