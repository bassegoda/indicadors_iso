-- Ingresos (episodios) con procedencia de otro centro u otro hospital
-- Formulario UCI, campo PROCE_MALA (procedencia antes del ingreso hospitalario)
-- Un episodio por fila
-- Dialect: Athena (Trino/Presto)
SELECT DISTINCT
    e.patient_ref,
    e.episode_ref,
    e.episode_type_ref,
    e.start_date AS fecha_ingreso,
    e.end_date AS fecha_alta,
    df.value_text AS procedencia_codigo,
    df.value_descr AS procedencia,
    df.form_date AS fecha_valoracion,
    df.ou_loc_ref,
    df.ou_med_ref
FROM datascope_gestor_prod.episodes e
INNER JOIN datascope_gestor_prod.dynamic_forms df
    ON e.patient_ref = df.patient_ref
    AND e.episode_ref = df.episode_ref
WHERE df.form_ref = 'UCI'
  AND df.question_ref = 'PROCE_MALA'
  AND df.status = 'CO'
  AND (
      df.value_text LIKE '%Otro centro%'
      OR df.value_text LIKE '%otro centro%'
      OR df.value_text LIKE '%Otro hospital%'
      OR df.value_text LIKE '%otro hospital%'
      OR df.value_descr LIKE '%Otro centro%'
      OR df.value_descr LIKE '%Otro hospital%'
  )
ORDER BY e.start_date DESC;
