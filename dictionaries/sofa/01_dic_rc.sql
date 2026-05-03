-- =====================================================================
-- Diccionario RC completo (para luego filtrar SOFA en local)
-- =====================================================================
-- Las tablas `dic_*` ya no existen en datascope_gestor_prod, así que
-- reconstruimos el diccionario desde la propia tabla `rc` con DISTINCT
-- sobre (rc_sap_ref, rc_descr, units). Sin filtro semántico: nos
-- bajamos TODO el diccionario y la búsqueda de los códigos SOFA la
-- hacemos en local sobre el CSV.
--
-- Cómo usarlo:
--   1. Ejecuta la query en Metabase (Athena).
--   2. Si pasa de 2000 filas, descarga el CSV completo desde la UI
--      ("..." -> Download full results) a:
--        dictionaries/sofa/dic_rc_full.csv
--   3. Avísame cuando esté el CSV y hago el grep en local para extraer
--      los códigos de FiO2, PEEP, modo VM, TAS/TAD/TAM, FC, diuresis,
--      Glasgow (si está aquí), etc.
--
-- Notas:
--   * Filtramos por `result_date >= 2018` para descartar códigos
--     descontinuados. Si quieres TODO el histórico, quita el WHERE.
--   * `n_apariciones` ayuda a priorizar (lo más usado primero).
-- =====================================================================
SELECT
    rc_sap_ref,
    rc_descr,
    units,
    COUNT(*) AS n_apariciones
FROM datascope_gestor_prod.rc
WHERE result_date >= timestamp '2018-01-01 00:00:00'
  AND rc_sap_ref IS NOT NULL
GROUP BY rc_sap_ref, rc_descr, units
ORDER BY rc_sap_ref, rc_descr, units;
