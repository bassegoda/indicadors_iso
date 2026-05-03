-- =====================================================================
-- Diccionario ADMINISTRATIONS (lo que REALMENTE se administra)
-- =====================================================================
-- `administrations` no trae ATC propio, pero sí `drug_ref`, `drug_descr`,
-- `route_ref` y `quantity_unit`. Para SOFA al ingreso (primeras 24 h)
-- esta tabla es la fuente correcta para fármacos en bolo / pauta fija
-- (más fiel que `prescriptions`).
--
-- Para vasopresores en infusión continua, mejor cruzar con `perfusions`
-- (ver 05_dic_perfusions.sql). Aquí nos bajamos el catálogo de fármacos
-- realmente administrados, sin filtro semántico, y luego en local
-- identifico los relevantes para SOFA.
--
-- Cómo usarlo:
--   1. Ejecuta en Metabase (Athena).
--   2. Descarga a `dictionaries/sofa/dic_administrations.csv`.
--
-- Notas:
--   * Filtramos `given IS NULL` para coger sólo administraciones
--     realizadas (la 'X' en `given` significa NO administrado).
--   * `n_administraciones` ayuda a priorizar.
--   * Limitamos a 2018+ para descartar fármacos retirados.
-- =====================================================================
SELECT
    drug_ref,
    drug_descr,
    atc_ref,
    atc_descr,
    route_ref,
    route_descr,
    quantity_unit,
    COUNT(*) AS n_administraciones
FROM datascope_gestor_prod.administrations
WHERE administration_date >= date '2018-01-01'
  AND given IS NULL                  -- sólo administraciones realizadas
  AND drug_ref IS NOT NULL
GROUP BY
    drug_ref, drug_descr,
    atc_ref, atc_descr,
    route_ref, route_descr,
    quantity_unit
ORDER BY n_administraciones DESC, drug_descr;
