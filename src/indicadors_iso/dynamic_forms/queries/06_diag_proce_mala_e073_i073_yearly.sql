-- ====================================================================
-- DIAGNÓSTICO: catálogo de valores PROCE_MALA en E073/I073, por año
-- ====================================================================
-- Objetivo: comprobar si el catálogo de opciones del campo PROCE_MALA
-- (formulario UCI, procedencia del paciente antes del ingreso) ha
-- cambiado a lo largo de 2018-2025. Permite detectar:
--   - Cambios en el código (`value_text`), p.ej. "20-Altre hospital-"
--     vs "20-Otro hospital-" vs "21-…"
--   - Cambios en la descripción (`value_descr`)
--   - Opciones que aparecen/desaparecen entre años
--
-- Cohorte: episodios con al menos un movimiento en E073 o I073 con cama
-- asignada en el periodo 2018-2025 (sin filtro de prescripción, para
-- ver el catálogo completo de respuestas, aunque el episodio no entre
-- en la cohorte final del informe).
--
-- Dialect: Athena (Trino/Presto)
-- ====================================================================

WITH e073_i073_episodes AS (
    SELECT DISTINCT patient_ref, episode_ref
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ('E073','I073')
      AND start_date >= timestamp '2018-01-01 00:00:00'
      AND start_date <  timestamp '2026-01-01 00:00:00'
      AND place_ref IS NOT NULL
),
proce_mala AS (
    SELECT
        df.patient_ref,
        df.episode_ref,
        df.form_date,
        year(df.form_date) AS year_form,
        df.value_text,
        df.value_descr
    FROM datascope_gestor_prod.dynamic_forms df
    INNER JOIN e073_i073_episodes ep
        ON df.patient_ref = ep.patient_ref
        AND df.episode_ref = ep.episode_ref
    WHERE df.form_ref = 'UCI'
      AND df.question_ref = 'PROCE_MALA'
      AND df.status = 'CO'
)

-- ---------- Vista pivotada (una fila por opción del catálogo) ----------
-- Muestra el conteo de respuestas por (value_text, value_descr) y año.
-- Si una opción cambió de código entre 2023 y 2024, lo verás como dos
-- filas distintas: la antigua con cuentas en y2018-y2023 y 0 en y2024+,
-- y la nueva al revés.
SELECT
    value_text,
    value_descr,
    SUM(CASE WHEN year_form = 2018 THEN 1 ELSE 0 END) AS y2018,
    SUM(CASE WHEN year_form = 2019 THEN 1 ELSE 0 END) AS y2019,
    SUM(CASE WHEN year_form = 2020 THEN 1 ELSE 0 END) AS y2020,
    SUM(CASE WHEN year_form = 2021 THEN 1 ELSE 0 END) AS y2021,
    SUM(CASE WHEN year_form = 2022 THEN 1 ELSE 0 END) AS y2022,
    SUM(CASE WHEN year_form = 2023 THEN 1 ELSE 0 END) AS y2023,
    SUM(CASE WHEN year_form = 2024 THEN 1 ELSE 0 END) AS y2024,
    SUM(CASE WHEN year_form = 2025 THEN 1 ELSE 0 END) AS y2025,
    COUNT(*)        AS total,
    MIN(form_date)  AS first_seen,
    MAX(form_date)  AS last_seen
FROM proce_mala
GROUP BY value_text, value_descr
ORDER BY total DESC;
