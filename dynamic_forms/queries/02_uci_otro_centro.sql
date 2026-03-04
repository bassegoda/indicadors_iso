-- Formularios de valoración de críticos (UCI) donde el paciente
-- indica "Otro centro" como procedencia
SELECT
    patient_ref,
    episode_ref,
    form_ref,
    form_descr,
    form_date,
    tab_ref,
    tab_descr,
    section_ref,
    section_descr,
    question_ref,
    question_descr,
    value_text,
    value_num,
    value_date,
    value_descr,
    ou_med_ref,
    ou_loc_ref
FROM g_dynamic_forms
WHERE form_ref = 'UCI'
  AND status = 'CO'
  AND (
      value_text LIKE '%Otro centro%'
      OR value_text LIKE '%otro centro%'
      OR value_text LIKE '%Otro hospital%'
      OR value_descr LIKE '%Otro centro%'
      OR value_descr LIKE '%Otro hospital%'
  )
ORDER BY form_date DESC;
