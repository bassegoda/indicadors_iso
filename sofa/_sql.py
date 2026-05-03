"""SQL único que construye la cohorte UCI + agregados SOFA al ingreso.

Devuelve **una fila por estancia** (per-unit, sin agrupar traslados),
con los peores valores de cada componente SOFA en las primeras 24 h.
La puntuación final se calcula en `_metrics.py` (Python) para no
incrustar lógica clínica en SQL.

Parámetros de plantilla:
    {min_year}, {max_year}      -> rango de admisión
    {window_hours}              -> ventana de medición (24 por defecto)
    {icu_units_csv}             -> lista entrecomillada de UCIs, p.ej.
                                   "'E016','E103',..."
"""

SQL_TEMPLATE = r"""
-- =====================================================================
-- SOFA al ingreso — cohorte UCI + agregados por componente (24 h)
-- Dialect: Athena (Trino/Presto)
-- =====================================================================

-- 1. Cohorte de estancias UCI (per-unit, lógica de demographics/per_unit).
WITH all_related_moves AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref,
        start_date, end_date,
        COALESCE(end_date, current_timestamp) AS effective_end_date
    FROM datascope_gestor_prod.movements
    WHERE ou_loc_ref IN ({icu_units_csv})
      AND start_date <= timestamp '{max_year}-12-31 23:59:59'
      AND COALESCE(end_date, current_timestamp) >= timestamp '{min_year}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, current_timestamp) > start_date
),
flagged_starts AS (
    SELECT *,
        CASE
            WHEN ABS(date_diff('minute',
                LAG(effective_end_date) OVER (
                    PARTITION BY patient_ref, episode_ref, ou_loc_ref ORDER BY start_date
                ),
                start_date
            )) <= 5 THEN 0 ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    SELECT *,
        SUM(is_new_stay) OVER (
            PARTITION BY patient_ref, episode_ref, ou_loc_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref, stay_id,
        MIN(start_date) AS admission_date,
        MAX(effective_end_date) AS effective_discharge_date
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
    HAVING year(MIN(start_date)) BETWEEN {min_year} AND {max_year}
),
cohort_window AS (
    SELECT
        c.*,
        date_add('hour', {window_hours}, c.admission_date) AS window_end
    FROM cohort c
),

-- 2. LABS dentro de las primeras 24 h.
labs_in_window AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        l.lab_sap_ref, l.result_num
    FROM cohort_window cw
    JOIN datascope_gestor_prod.labs l
        ON l.patient_ref = cw.patient_ref
       AND l.episode_ref = cw.episode_ref
       AND l.extrac_date >= cw.admission_date
       AND l.extrac_date <  cw.window_end
    WHERE l.result_num IS NOT NULL
      AND l.lab_sap_ref IN (
          'LAB3072','LABRPAPO2',           -- PaO2
          'LAB1301',                       -- Plaquetas
          'LAB2407',                       -- Bilirrubina total
          'LABCREA','LAB2467'              -- Creatinina
      )
),

-- 2b. Glasgow desde rc.COMA_GCS (resulta ser la fuente más completa).
--     `rc.episode_ref` está NULL → join SOLO por patient_ref + ventana.
gcs_from_rc AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        MIN(r.result_num) AS gcs_min
    FROM cohort_window cw
    JOIN datascope_gestor_prod.rc r
        ON r.patient_ref = cw.patient_ref
       AND r.result_date >= cw.admission_date
       AND r.result_date <  cw.window_end
    WHERE r.rc_sap_ref = 'COMA_GCS'
      AND r.result_num IS NOT NULL
      AND r.result_num BETWEEN 3 AND 15
    GROUP BY cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id
),
labs_agg AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref, stay_id,
        MIN(CASE WHEN lab_sap_ref IN ('LAB3072','LABRPAPO2') THEN result_num END) AS pao2_min,
        MIN(CASE WHEN lab_sap_ref = 'LAB1301'                THEN result_num END) AS platelets_min,
        MAX(CASE WHEN lab_sap_ref = 'LAB2407'                THEN result_num END) AS bilirubin_max,
        MAX(CASE WHEN lab_sap_ref IN ('LABCREA','LAB2467')   THEN result_num END) AS creatinine_max
    FROM labs_in_window
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
),

-- 3. RC dentro de las primeras 24 h (rc.episode_ref es NULL → join por
--    patient_ref + ventana temporal sobre result_date).
rc_in_window AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        r.rc_sap_ref, r.result_num, r.result_txt
    FROM cohort_window cw
    JOIN datascope_gestor_prod.rc r
        ON r.patient_ref = cw.patient_ref
       AND r.result_date >= cw.admission_date
       AND r.result_date <  cw.window_end
    WHERE r.rc_sap_ref IN (
        'FIO2','VMI_FIO2','VNI_FIO2','AR_FIO2','ACR_FIO2','VMA_FIO2',
        'VMI_MOD','VNI_MOD','VIA_AEREA_MOD',
        'PA_M','PANIC_M','PANI_M'
    )
),
rc_agg AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref, stay_id,
        -- FiO2 máxima registrada (peor escenario respiratorio)
        MAX(CASE WHEN rc_sap_ref IN (
                'FIO2','VMI_FIO2','VNI_FIO2','AR_FIO2','ACR_FIO2','VMA_FIO2'
            ) THEN result_num END) AS fio2_max,
        -- PAM mínima en la ventana
        MIN(CASE WHEN rc_sap_ref IN ('PA_M','PANIC_M','PANI_M')
                 THEN result_num END) AS map_min,
        -- Soporte ventilatorio: VMI / VNI (cualquier valor registrado)
        MAX(CASE WHEN rc_sap_ref IN ('VMI_FIO2','VMI_MOD') THEN 1 ELSE 0 END) AS on_vmi,
        MAX(CASE WHEN rc_sap_ref IN ('VNI_FIO2','VNI_MOD') THEN 1 ELSE 0 END) AS on_vni
    FROM rc_in_window
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
),

-- 4. Glasgow → ahora se resuelve en `gcs_from_rc` (rc.COMA_GCS).
--    Las subescalas en dynamic_forms vienen como string en value_text
--    (no en value_num), así que no las usamos.

-- 5. Vasopresores activos en la ventana — vía administrations + perfusions.
--
--    Joins MUY relajados (verificado el 2026-05-03 que los joins por
--    `episode_ref` perdían el 100% de las rows, probablemente porque las
--    perfusiones / prescripciones pueden vivir en un episode_ref distinto
--    al del movement de UCI):
--      - administrations: SOLO por patient_ref + ventana temporal sobre
--        administration_date. Sin filtro `given` (siempre viene vacío),
--        sin filtro de ruta (la regex sobre drug_descr ya es suficiente).
--      - perfusions: SOLO por patient_ref + solape temporal de la
--        perfusión con la ventana de la estancia. Para resolver el
--        drug_descr (perfusions no lo trae) se joinea con prescriptions
--        SOLO por (patient_ref, treatment_ref), sin episode_ref.
--
--    Filtramos por regex sobre drug_descr (NO por ATC — los preparados
--    diluidos llevan el ATC del diluyente, no del principio activo).
admin_vasoactive AS (
    SELECT DISTINCT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        a.drug_descr
    FROM cohort_window cw
    JOIN datascope_gestor_prod.administrations a
        ON a.patient_ref = cw.patient_ref
       AND a.administration_date >= cast(cw.admission_date as date)
       AND a.administration_date <= cast(cw.window_end as date)
    WHERE regexp_like(lower(coalesce(a.drug_descr,'')),
          'noradr|norepin|adrenalin|epinef|dopami|dobutami|fenilefr|vasopres|terlipres|milrinon|levosimen|isoprenal')
),
perf_vasoactive AS (
    SELECT DISTINCT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        pr.drug_descr
    FROM cohort_window cw
    JOIN datascope_gestor_prod.perfusions p
        ON p.patient_ref = cw.patient_ref
       AND p.start_date <  cw.window_end
       AND COALESCE(p.end_date, current_timestamp) > cw.admission_date
    JOIN datascope_gestor_prod.prescriptions pr
        ON pr.patient_ref   = p.patient_ref
       AND pr.treatment_ref = p.treatment_ref
    WHERE regexp_like(lower(coalesce(pr.drug_descr,'')),
          'noradr|norepin|adrenalin|epinef|dopami|dobutami|fenilefr|vasopres|terlipres|milrinon|levosimen|isoprenal')
),
vasoactive_union AS (
    SELECT * FROM admin_vasoactive
    UNION ALL
    SELECT * FROM perf_vasoactive
),
vasoactive_agg AS (
    SELECT
        patient_ref, episode_ref, ou_loc_ref, stay_id,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'noradr|norepin')   THEN 1 ELSE 0 END) AS on_norepi,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'adrenalin|epinef') THEN 1 ELSE 0 END) AS on_epi,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'dopami')           THEN 1 ELSE 0 END) AS on_dopa,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'dobutami')         THEN 1 ELSE 0 END) AS on_dobu,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'vasopres|terlipres') THEN 1 ELSE 0 END) AS on_vasop,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'fenilefr')         THEN 1 ELSE 0 END) AS on_phenyl,
        MAX(CASE WHEN regexp_like(lower(drug_descr), 'milrinon|levosimen|isoprenal') THEN 1 ELSE 0 END) AS on_inotrope_other
    FROM vasoactive_union
    GROUP BY patient_ref, episode_ref, ou_loc_ref, stay_id
),

-- 6. Peso del paciente. Preferimos `rc.PESO` / `rc.PESO_SECO` (registro
--    a pie de cama, alta cobertura). Fallback a `dynamic_forms.UCI.PES`
--    para los pocos casos sin registro en rc.
--    rc.episode_ref es NULL → join SOLO por patient_ref + ventana.
weight_from_rc AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        r.result_num AS weight_kg,
        ROW_NUMBER() OVER (
            PARTITION BY cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id
            ORDER BY r.result_date ASC
        ) AS rn
    FROM cohort_window cw
    JOIN datascope_gestor_prod.rc r
        ON r.patient_ref = cw.patient_ref
       AND r.result_date >= cw.admission_date
       AND r.result_date <  cw.window_end
    WHERE r.rc_sap_ref IN ('PESO','PESO_SECO')
      AND r.result_num IS NOT NULL
      AND r.result_num BETWEEN 30 AND 250
),
weight_from_form AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        df.value_num AS weight_kg,
        ROW_NUMBER() OVER (
            PARTITION BY cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id
            ORDER BY df.form_date ASC
        ) AS rn
    FROM cohort_window cw
    JOIN datascope_gestor_prod.dynamic_forms df
        ON df.patient_ref = cw.patient_ref
       AND df.episode_ref = cw.episode_ref
       AND df.form_date >= cw.admission_date
       AND df.form_date <  cw.window_end
    WHERE df.form_ref = 'UCI'
      AND df.question_ref = 'PES'
      AND df.status = 'CO'
      AND df.value_num IS NOT NULL
      AND df.value_num BETWEEN 30 AND 250
),
weight_agg AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        COALESCE(wr.weight_kg, wf.weight_kg) AS weight_kg
    FROM cohort_window cw
    LEFT JOIN weight_from_rc   wr ON wr.patient_ref = cw.patient_ref AND wr.episode_ref = cw.episode_ref AND wr.ou_loc_ref = cw.ou_loc_ref AND wr.stay_id = cw.stay_id AND wr.rn = 1
    LEFT JOIN weight_from_form wf ON wf.patient_ref = cw.patient_ref AND wf.episode_ref = cw.episode_ref AND wf.ou_loc_ref = cw.ou_loc_ref AND wf.stay_id = cw.stay_id AND wf.rn = 1
),

-- 7. SOFA precalculado en `dynamic_forms` (gold standard parcial).
sofa_form_agg AS (
    SELECT
        cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id,
        MAX(CASE WHEN df.question_ref = 'SOFA_RESPI' THEN df.value_num END) AS sofa_form_resp,
        MAX(CASE WHEN df.question_ref = 'SOFA_COAGU' THEN df.value_num END) AS sofa_form_coag,
        MAX(CASE WHEN df.question_ref = 'SOFA_LIVER' THEN df.value_num END) AS sofa_form_liver,
        MAX(CASE WHEN df.question_ref = 'SOFA_CARDI' THEN df.value_num END) AS sofa_form_cardio,
        MAX(CASE WHEN df.question_ref = 'SOFA_GLASG' THEN df.value_num END) AS sofa_form_neuro,
        MAX(CASE WHEN df.question_ref = 'SOFA_RENAL' THEN df.value_num END) AS sofa_form_renal
    FROM cohort_window cw
    JOIN datascope_gestor_prod.dynamic_forms df
        ON df.patient_ref = cw.patient_ref
       AND df.episode_ref = cw.episode_ref
       AND df.form_date >= cw.admission_date
       AND df.form_date <  cw.window_end
    WHERE df.form_ref = 'SOFA'
      AND df.status = 'CO'
    GROUP BY cw.patient_ref, cw.episode_ref, cw.ou_loc_ref, cw.stay_id
),

-- 8. Demografía + exitus para enriquecer.
demo AS (
    SELECT
        d.patient_ref,
        d.birth_date,
        d.sex,
        d.natio_descr AS nationality
    FROM datascope_gestor_prod.demographics d
)

SELECT
    cw.patient_ref,
    cw.episode_ref,
    cw.ou_loc_ref,
    cw.stay_id,
    cw.admission_date,
    cw.effective_discharge_date,
    cw.window_end,
    year(cw.admission_date)                                 AS year_admission,
    date_diff('year', d.birth_date, cw.admission_date)      AS age_at_admission,
    CASE WHEN d.sex = 1 THEN 'Male' WHEN d.sex = 2 THEN 'Female' ELSE 'Other' END AS sex,
    -- Labs
    la.pao2_min,
    la.platelets_min,
    la.bilirubin_max,
    la.creatinine_max,
    -- RC
    ra.fio2_max,
    ra.map_min,
    ra.on_vmi,
    ra.on_vni,
    -- Glasgow desde rc.COMA_GCS
    gr.gcs_min,
    -- Vasoactivos
    COALESCE(va.on_norepi, 0)         AS on_norepi,
    COALESCE(va.on_epi, 0)            AS on_epi,
    COALESCE(va.on_dopa, 0)           AS on_dopa,
    COALESCE(va.on_dobu, 0)           AS on_dobu,
    COALESCE(va.on_vasop, 0)          AS on_vasop,
    COALESCE(va.on_phenyl, 0)         AS on_phenyl,
    COALESCE(va.on_inotrope_other, 0) AS on_inotrope_other,
    -- Peso
    wa.weight_kg,
    -- SOFA precalculado en form (validación cruzada)
    sf.sofa_form_resp,
    sf.sofa_form_coag,
    sf.sofa_form_liver,
    sf.sofa_form_cardio,
    sf.sofa_form_neuro,
    sf.sofa_form_renal,
    -- Exitus durante la estancia
    CASE
        WHEN ex.exitus_date BETWEEN cw.admission_date AND cw.effective_discharge_date
        THEN 1 ELSE 0
    END AS exitus_during_stay
FROM cohort_window cw
LEFT JOIN demo d                 ON d.patient_ref = cw.patient_ref
LEFT JOIN labs_agg la            ON la.patient_ref = cw.patient_ref AND la.episode_ref = cw.episode_ref AND la.ou_loc_ref = cw.ou_loc_ref AND la.stay_id = cw.stay_id
LEFT JOIN rc_agg ra              ON ra.patient_ref = cw.patient_ref AND ra.episode_ref = cw.episode_ref AND ra.ou_loc_ref = cw.ou_loc_ref AND ra.stay_id = cw.stay_id
LEFT JOIN gcs_from_rc gr         ON gr.patient_ref = cw.patient_ref AND gr.episode_ref = cw.episode_ref AND gr.ou_loc_ref = cw.ou_loc_ref AND gr.stay_id = cw.stay_id
LEFT JOIN vasoactive_agg va      ON va.patient_ref = cw.patient_ref AND va.episode_ref = cw.episode_ref AND va.ou_loc_ref = cw.ou_loc_ref AND va.stay_id = cw.stay_id
LEFT JOIN weight_agg wa          ON wa.patient_ref = cw.patient_ref AND wa.episode_ref = cw.episode_ref AND wa.ou_loc_ref = cw.ou_loc_ref AND wa.stay_id = cw.stay_id
LEFT JOIN sofa_form_agg sf       ON sf.patient_ref = cw.patient_ref AND sf.episode_ref = cw.episode_ref AND sf.ou_loc_ref = cw.ou_loc_ref AND sf.stay_id = cw.stay_id
LEFT JOIN datascope_gestor_prod.exitus ex ON ex.patient_ref = cw.patient_ref
ORDER BY cw.ou_loc_ref, cw.admission_date;
"""


def render_sql(min_year: int, max_year: int, icu_units, window_hours: int = 24) -> str:
    units_csv = ",".join(f"'{u}'" for u in icu_units)
    return SQL_TEMPLATE.format(
        min_year=min_year,
        max_year=max_year,
        window_hours=window_hours,
        icu_units_csv=units_csv,
    )
