-- Procedencias de pacientes en E073 durante 2024
-- Formulario UCI, campo PROCE_MALA (procedencia antes del ingreso hospitalario)
-- Dialect: Athena (Trino/Presto)
WITH episodios_e073 AS (
    SELECT DISTINCT patient_ref, episode_ref
    FROM movements
    WHERE ou_loc_ref = 'E073'
      AND start_date >= timestamp '2024-01-01 00:00:00'
      AND start_date < timestamp '2025-01-01 00:00:00'
)
SELECT
    df.patient_ref,
    df.episode_ref,
    df.form_date,
    df.value_text AS procedencia_codigo,
    df.value_descr AS procedencia,
    df.ou_loc_ref,
    df.ou_med_ref,
    e.start_date AS episode_start,
    e.end_date AS episode_end
FROM dynamic_forms df
INNER JOIN episodios_e073 m
    ON df.patient_ref = m.patient_ref
    AND df.episode_ref = m.episode_ref
JOIN episodes e
    ON df.patient_ref = e.patient_ref
    AND df.episode_ref = e.episode_ref
WHERE df.form_ref = 'UCI'
  AND df.question_ref = 'PROCE_MALA'
  AND df.status = 'CO'
  AND df.form_date >= timestamp '2024-01-01 00:00:00'
  AND df.form_date < timestamp '2025-01-01 00:00:00'
ORDER BY df.form_date;
