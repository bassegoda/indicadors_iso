-- =====================================================================
-- Helper: ranking de place_ref en E073 para identificar la "cama falsa"
-- =====================================================================
-- Pegar tal cual en Metabase (Native query, AWS Athena/Trino).
-- También se puede ejecutar desde Python con:
--     execute_query(open(...).read())
--
-- Objetivo: listar TODOS los place_ref que han aparecido en `movements`
-- con `ou_loc_ref = 'E073'` para que detectemos cuál es la cama auxiliar
-- de procedimientos (no de paciente crítico).
--
-- Patrón típico de la cama falsa:
--   - Muchos `n_movements` (rotación alta)
--   - `median_minutes_per_movement` MUY baja (procedimiento dura horas)
--   - Pacientes muy variados (`n_patients` alto en relación a movimientos)
--   - Presencia constante en todo el periodo (min_year temprano, max_year reciente)
-- En contraste, las camas reales tienen menor rotación y estancias en
-- días (mediana ~24-72 h).
--
-- Pasar el/los `place_ref` resultantes a `demographics/_config.py` →
-- `FAKE_BED_PLACE_REFS_E073`.
-- =====================================================================

WITH e073_moves AS (
    SELECT
        place_ref,
        patient_ref,
        episode_ref,
        start_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date,
        date_diff('minute', start_date, COALESCE(end_date, current_timestamp))
            AS duration_minutes
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref = 'E073'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, current_timestamp) > start_date
),
per_place AS (
    SELECT
        place_ref,
        COUNT(*) AS n_movements,
        COUNT(DISTINCT episode_ref) AS n_episodes,
        COUNT(DISTINCT patient_ref) AS n_patients,
        ROUND(SUM(duration_minutes) / 60.0, 1) AS total_hours,
        ROUND(approx_percentile(duration_minutes, 0.5), 1)
            AS median_minutes_per_movement,
        ROUND(approx_percentile(duration_minutes, 0.9), 1)
            AS p90_minutes_per_movement,
        year(MIN(start_date)) AS min_year,
        year(MAX(start_date)) AS max_year
    FROM e073_moves
    GROUP BY place_ref
)
SELECT
    place_ref,
    n_movements,
    n_episodes,
    n_patients,
    total_hours,
    median_minutes_per_movement,
    p90_minutes_per_movement,
    min_year,
    max_year
FROM per_place
ORDER BY n_movements DESC;
