-- =====================================================================
-- Diccionario PERFUSIONS (infusión continua — vasopresores, sedantes)
-- =====================================================================
-- `perfusions` sólo guarda `treatment_ref` + ritmo de infusión (mL/h)
-- + start/end. NO trae `drug_ref` ni `atc_ref` directamente. Para
-- saber QUÉ fármaco está en infusión hay que cruzar con `prescriptions`
-- (o `administrations`) por `treatment_ref`.
--
-- Esta query reconstruye un "diccionario" de los fármacos que han
-- estado alguna vez en perfusión continua: hace JOIN perfusions ↔
-- prescriptions por (patient_ref, episode_ref, treatment_ref) y
-- agrupa por (drug_ref, drug_descr, atc_ref, atc_descr).
--
-- Es la base para identificar vasopresores en infusión para el SOFA-2
-- cardiovascular (necesario para clasificar a dosis bajas vs altas
-- de noradrenalina, etc.).
--
-- Cómo usarlo:
--   1. Ejecuta en Metabase (Athena).
--   2. Descarga a `dictionaries/sofa2/dic_perfusions.csv`.
--
-- Notas:
--   * Filtramos por `start_date >= 2018`.
--   * `n_perfusiones` cuenta combinaciones distintas (drug_ref, ritmo).
--   * Si el JOIN se queda sin `prescription` (treatment_ref huérfano),
--     ese drug_ref aparecerá como NULL — útil para detectar gaps ETL.
-- =====================================================================
WITH perf_drugs AS (
    SELECT DISTINCT
        pe.patient_ref,
        pe.episode_ref,
        pe.treatment_ref
    FROM datascope_gestor_prod.perfusions pe
    WHERE pe.start_date >= timestamp '2018-01-01 00:00:00'
),
perf_with_drug AS (
    SELECT
        pd.treatment_ref,
        pr.drug_ref,
        pr.drug_descr,
        pr.atc_ref,
        pr.atc_descr,
        pr.unit                       AS prescribed_unit,
        pr.adm_route_ref,
        pr.route_descr
    FROM perf_drugs pd
    LEFT JOIN datascope_gestor_prod.prescriptions pr
        ON  pr.patient_ref   = pd.patient_ref
        AND pr.episode_ref   = pd.episode_ref
        AND pr.treatment_ref = pd.treatment_ref
)
SELECT
    drug_ref,
    drug_descr,
    atc_ref,
    atc_descr,
    prescribed_unit,
    adm_route_ref,
    route_descr,
    COUNT(*) AS n_perfusiones
FROM perf_with_drug
GROUP BY
    drug_ref, drug_descr,
    atc_ref, atc_descr,
    prescribed_unit, adm_route_ref, route_descr
ORDER BY n_perfusiones DESC, drug_descr;
