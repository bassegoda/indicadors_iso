-- Valoración de críticos (UCI): campo procedencia/origen con valor "Otro centro"
-- Incluye join con episodios para contexto
-- Dialect: Athena (Trino/Presto)
SELECT
    df.patient_ref,
    df.episode_ref,
    df.form_date,
    df.question_descr,
    df.section_descr,
    df.value_text,
    df.value_descr,
    df.ou_med_ref,
    e.episode_type_ref,
    e.start_date AS episode_start,
    e.end_date AS episode_end
FROM datascope_gestor_prod.dynamic_forms df
JOIN datascope_gestor_prod.episodes e
    ON df.patient_ref = e.patient_ref
    AND df.episode_ref = e.episode_ref
WHERE df.form_ref = 'UCI'
  AND df.status = 'CO'
  AND (
      df.question_descr LIKE '%procedencia%'
      OR df.question_descr LIKE '%origen%'
      OR df.question_descr LIKE '%antes%'
      OR df.section_descr LIKE '%procedencia%'
  )
  AND (
      df.value_text LIKE '%Otro centro%'
      OR df.value_text LIKE '%otro centro%'
      OR df.value_text LIKE '%Otro hospital%'
      OR df.value_descr LIKE '%Otro centro%'
      OR df.value_descr LIKE '%Otro hospital%'
  )
ORDER BY df.form_date DESC;
