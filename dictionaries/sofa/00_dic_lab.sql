-- =====================================================================
-- Diccionario LAB completo (para luego filtrar SOFA-2 en local)
-- =====================================================================
-- Las tablas `dic_*` ya no existen en datascope_gestor_prod, así que
-- reconstruimos el diccionario desde la propia tabla `labs` con DISTINCT
-- sobre (lab_sap_ref, lab_descr, units). Sin filtro semántico: nos
-- bajamos TODO el diccionario y la búsqueda de los códigos SOFA-2 la
-- hacemos en local sobre el CSV.
--
-- Cómo usarlo:
--   1. Ejecuta la query en Metabase (Athena).
--   2. Si pasa de 2000 filas, descarga el CSV completo desde la UI
--      ("..." -> Download full results) a:
--        dictionaries/sofa2/dic_lab_full.csv
--   3. Avísame cuando esté el CSV y hago el grep en local para extraer
--      los códigos de PaO2, PaCO2, plaquetas, bilirrubina, creatinina,
--      lactato, etc.
--
-- Notas:
--   * Filtramos por `extrac_date >= 2018` para descartar códigos
--     descontinuados. Si quieres TODO el histórico, quita el WHERE.
--   * `n_apariciones` ayuda a priorizar (lo más usado primero).
-- =====================================================================
SELECT
    lab_sap_ref,
    lab_descr,
    units,
    COUNT(*) AS n_apariciones
FROM datascope_gestor_prod.labs
WHERE extrac_date >= timestamp '2018-01-01 00:00:00'
  AND lab_sap_ref IS NOT NULL
GROUP BY lab_sap_ref, lab_descr, units
ORDER BY lab_sap_ref, lab_descr, units;
