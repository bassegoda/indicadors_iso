-- =====================================================================
-- Diccionario PRESCRIPTIONS (familia ATC cardiovascular y respiratoria)
-- =====================================================================
-- Reconstruimos el diccionario de fármacos desde `prescriptions` con
-- DISTINCT sobre (atc_ref, atc_descr, drug_ref, drug_descr, unit, ruta).
-- Sin filtro semántico fino: nos bajamos las familias ATC que pueden
-- intervenir en SOFA-2 (vasoactivos, sedantes/relajantes para soporte
-- ventilatorio, diuréticos para contexto renal). El filtro fino lo hago
-- en local.
--
-- IMPORTANTE: para SOFA-2 al ingreso usaremos `administrations` y
-- `perfusions` (lo que REALMENTE se administra), no `prescriptions`.
-- Este diccionario sirve sólo de referencia / fuente de descripción de
-- los fármacos, ya que `administrations` y `perfusions` no traen ATC.
--
-- Familias ATC traídas:
--   * C01CA*, C01CE*, C01CX*  -> agonistas adrenérgicos, dopaminérgicos,
--                                inotrópicos no glicósidos
--   * H01BA*                  -> vasopresina y análogos
--   * N01AX*, N05CD*, N05CM*  -> sedantes / hipnóticos (propofol,
--                                midazolam, dexmedetomidina, ketamina)
--   * M03A*                   -> relajantes musculares (cisatracurio,
--                                rocuronio) — marcador de VMI
--   * C03*                    -> diuréticos (furosemida, ...)
--
-- Cómo usarlo:
--   1. Ejecuta en Metabase (Athena).
--   2. Descarga a `dictionaries/sofa2/dic_prescriptions.csv`.
-- =====================================================================
SELECT
    atc_ref,
    atc_descr,
    drug_ref,
    drug_descr,
    unit,
    adm_route_ref,
    route_descr,
    COUNT(*) AS n_prescripciones
FROM datascope_gestor_prod.prescriptions
WHERE start_drug_date >= timestamp '2018-01-01 00:00:00'
  AND (
       atc_ref LIKE 'C01CA%'
    OR atc_ref LIKE 'C01CE%'
    OR atc_ref LIKE 'C01CX%'
    OR atc_ref LIKE 'H01BA%'
    OR atc_ref LIKE 'N01AX%'
    OR atc_ref LIKE 'N05CD%'
    OR atc_ref LIKE 'N05CM%'
    OR atc_ref LIKE 'M03A%'
    OR atc_ref LIKE 'C03%'
  )
GROUP BY
    atc_ref, atc_descr,
    drug_ref, drug_descr,
    unit, adm_route_ref, route_descr
ORDER BY atc_ref, drug_descr;
