-- Explorar la estructura del formulario UCI (valoración de críticos)
-- para identificar el campo de procedencia / origen del paciente
-- Dialect: Athena (Trino/Presto)
SELECT DISTINCT
    form_ref,
    form_descr,
    tab_ref,
    tab_descr,
    section_ref,
    section_descr,
    question_ref,
    question_descr,
    value_text,
    value_num,
    value_date,
    value_descr
FROM datascope_gestor_prod.dynamic_forms
WHERE form_ref = 'UCI'
  AND status = 'CO'
ORDER BY tab_ref, section_ref, question_ref
LIMIT 500;
