-- =============================================================================
-- SEPSIS-3 QUERY - DataNex (MariaDB compatible) - CORREGIDA
-- =============================================================================

WITH 
target_units AS (
    SELECT 'E073' AS ou_loc_ref UNION ALL
    SELECT 'I073' UNION ALL
    SELECT 'E043' UNION ALL
    SELECT 'I043' UNION ALL
    SELECT 'E015' UNION ALL
    SELECT 'E014' UNION ALL
    SELECT 'I014' UNION ALL
    SELECT 'I015'
),

first_admission AS (
    SELECT 
        m.patient_ref,
        m.episode_ref,
        m.ou_loc_ref,
        m.start_date AS admission_date,
        DATE_ADD(m.start_date, INTERVAL 24 HOUR) AS window_24h_end,
        DATE_ADD(m.start_date, INTERVAL 48 HOUR) AS window_48h_end,
        DATE_SUB(m.start_date, INTERVAL 48 HOUR) AS window_48h_start,
        ROW_NUMBER() OVER (PARTITION BY m.episode_ref ORDER BY m.start_date) AS rn
    FROM g_movements m
    INNER JOIN target_units tu ON m.ou_loc_ref = tu.ou_loc_ref
    INNER JOIN g_episodes e ON m.episode_ref = e.episode_ref
    WHERE e.episode_type_ref IN ('HOSP', 'HOSP_IQ', 'HOSP_RN')
      AND m.start_date >= '2024-01-01'
      AND m.start_date < '2025-01-01'
),

admissions AS (
    SELECT * FROM first_admission WHERE rn = 1
),

-- =============================================================================
-- 2. SOSPECHA DE INFECCIÓN - CORREGIDA (un solo registro por episodio)
-- =============================================================================

cultures AS (
    SELECT DISTINCT
        mi.patient_ref,
        mi.episode_ref,
        mi.extrac_date AS culture_date
    FROM g_micro mi
    INNER JOIN admissions a ON mi.episode_ref = a.episode_ref
    WHERE mi.extrac_date BETWEEN a.window_48h_start AND a.window_48h_end
),

antibiotics AS (
    SELECT DISTINCT
        ad.patient_ref,
        ad.episode_ref,
        ad.administration_date AS antibiotic_date
    FROM g_administrations ad
    INNER JOIN admissions a ON ad.episode_ref = a.episode_ref
    WHERE ad.atc_ref LIKE 'J01%'
      AND ad.administration_date BETWEEN a.window_48h_start AND a.window_48h_end
),

-- Todas las combinaciones válidas cultivo + antibiótico
infection_combinations AS (
    SELECT 
        c.patient_ref,
        c.episode_ref,
        c.culture_date,
        ab.antibiotic_date,
        LEAST(c.culture_date, ab.antibiotic_date) AS infection_onset
    FROM cultures c
    INNER JOIN antibiotics ab 
        ON c.episode_ref = ab.episode_ref
        AND ABS(TIMESTAMPDIFF(HOUR, c.culture_date, ab.antibiotic_date)) <= 48
),

-- DEDUPLICAR: quedarse con el PRIMER infection_onset por episodio
suspected_infection AS (
    SELECT 
        patient_ref,
        episode_ref,
        culture_date,
        antibiotic_date,
        infection_onset,
        ROW_NUMBER() OVER (PARTITION BY episode_ref ORDER BY infection_onset) AS rn
    FROM infection_combinations
),

suspected_infection_first AS (
    SELECT 
        patient_ref,
        episode_ref,
        culture_date,
        antibiotic_date,
        infection_onset
    FROM suspected_infection
    WHERE rn = 1
),

-- =============================================================================
-- 3. COMPONENTES SOFA - LABORATORIO (primeras 24h)
-- =============================================================================

pao2_values AS (
    SELECT 
        l.patient_ref,
        l.episode_ref,
        l.result_num AS pao2,
        l.extrac_date,
        ROW_NUMBER() OVER (PARTITION BY l.episode_ref ORDER BY l.extrac_date) AS rn
    FROM g_labs l
    INNER JOIN admissions a ON l.episode_ref = a.episode_ref
    WHERE l.lab_sap_ref IN ('LAB3072', 'LABRPAPO2')
      AND l.result_num IS NOT NULL
      AND l.extrac_date BETWEEN a.admission_date AND a.window_24h_end
),

platelets_lab AS (
    SELECT 
        l.patient_ref,
        l.episode_ref,
        l.result_num AS platelets,
        l.extrac_date,
        ROW_NUMBER() OVER (PARTITION BY l.episode_ref ORDER BY l.extrac_date) AS rn
    FROM g_labs l
    INNER JOIN admissions a ON l.episode_ref = a.episode_ref
    WHERE l.lab_sap_ref = 'LAB1301'
      AND l.result_num IS NOT NULL
      AND l.extrac_date BETWEEN a.admission_date AND a.window_24h_end
),

bilirubin_values AS (
    SELECT 
        l.patient_ref,
        l.episode_ref,
        l.result_num AS bilirubin,
        l.extrac_date,
        ROW_NUMBER() OVER (PARTITION BY l.episode_ref ORDER BY 
            CASE l.lab_sap_ref 
                WHEN 'LAB2407' THEN 1
                ELSE 2 
            END, 
            l.extrac_date) AS rn
    FROM g_labs l
    INNER JOIN admissions a ON l.episode_ref = a.episode_ref
    WHERE l.lab_sap_ref IN ('LAB2407','LABBILSV','LABBILSA','LABBILSC',
                            'LABBILSVN1','LABBILSVN2','LABBILSVN3',
                            'LABBILSAN1','LABBILSAN2','LABBILSAN3')
      AND l.result_num IS NOT NULL
      AND l.extrac_date BETWEEN a.admission_date AND a.window_24h_end
),

creatinine_values AS (
    SELECT 
        l.patient_ref,
        l.episode_ref,
        l.result_num AS creatinine,
        l.extrac_date,
        ROW_NUMBER() OVER (PARTITION BY l.episode_ref ORDER BY 
            CASE l.lab_sap_ref 
                WHEN 'LAB2467' THEN 1
                WHEN 'LABCREA' THEN 2
                ELSE 3 
            END, 
            l.extrac_date) AS rn
    FROM g_labs l
    INNER JOIN admissions a ON l.episode_ref = a.episode_ref
    WHERE l.lab_sap_ref IN ('LAB2467','LABCREA','LABCREAV','LABCREAAR')
      AND l.result_num IS NOT NULL
      AND l.extrac_date BETWEEN a.admission_date AND a.window_24h_end
),

-- =============================================================================
-- 4. COMPONENTES SOFA - REGISTROS CLÍNICOS (primeras 24h)
-- =============================================================================

fio2_values AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num AS fio2,
        r.result_date,
        ROW_NUMBER() OVER (PARTITION BY r.episode_ref ORDER BY r.result_date) AS rn
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref IN ('FIO2','VMI_FIO2','VNI_FIO2','VMA_FIO2')
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

pam_direct AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num AS pam,
        r.result_date,
        r.rc_sap_ref,
        ROW_NUMBER() OVER (PARTITION BY r.episode_ref ORDER BY r.result_date) AS rn
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref IN ('PA_M','PANI_M','PANIC_M')
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

pa_systolic AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num AS pas,
        r.result_date
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref IN ('PA_S','PANI_S','PANIC_S')
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

pa_diastolic AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num AS pad,
        r.result_date
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref IN ('PA_D','PANI_D','PANIC_D')
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

pam_calculated AS (
    SELECT 
        s.patient_ref,
        s.episode_ref,
        (s.pas + 2 * d.pad) / 3 AS pam,
        s.result_date,
        ROW_NUMBER() OVER (PARTITION BY s.episode_ref ORDER BY s.result_date) AS rn
    FROM pa_systolic s
    INNER JOIN pa_diastolic d 
        ON s.episode_ref = d.episode_ref
        AND s.result_date = d.result_date
),

pam_values AS (
    SELECT episode_ref, pam FROM pam_direct WHERE rn = 1
    UNION ALL
    SELECT episode_ref, pam FROM pam_calculated 
    WHERE rn = 1 
      AND episode_ref NOT IN (SELECT episode_ref FROM pam_direct WHERE rn = 1)
),

glasgow_values AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num AS gcs,
        r.result_date,
        ROW_NUMBER() OVER (PARTITION BY r.episode_ref ORDER BY r.result_date) AS rn
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref IN ('COMA_GCS','ESTADO_CONCIENC')
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

platelets_rc AS (
    SELECT 
        r.patient_ref,
        r.episode_ref,
        r.result_num * 1000 AS platelets,
        r.result_date,
        ROW_NUMBER() OVER (PARTITION BY r.episode_ref ORDER BY r.result_date) AS rn
    FROM g_rc r
    INNER JOIN admissions a ON r.patient_ref = a.patient_ref
    WHERE r.rc_sap_ref = 'PLAQUETAS'
      AND r.result_num IS NOT NULL
      AND r.result_date BETWEEN a.admission_date AND a.window_24h_end
),

-- =============================================================================
-- 5. VASOPRESORES (primeras 24h)
-- =============================================================================
vasopressors AS (
    SELECT DISTINCT
        ad.patient_ref,
        ad.episode_ref,
        1 AS on_vasopressors
    FROM g_administrations ad
    INNER JOIN admissions a ON ad.episode_ref = a.episode_ref
    WHERE ad.atc_ref IN ('C01CA03','C01CA24','C01CA04','C01CA07')
      AND ad.administration_date BETWEEN a.admission_date AND a.window_24h_end
),

-- =============================================================================
-- 6. CONSOLIDAR COMPONENTES SOFA
-- =============================================================================
sofa_components AS (
    SELECT 
        a.patient_ref,
        a.episode_ref,
        a.admission_date,
        a.ou_loc_ref,
        pao2.pao2,
        fio2.fio2,
        CASE WHEN fio2.fio2 > 0 THEN pao2.pao2 / (fio2.fio2 / 100.0) ELSE NULL END AS pf_ratio,
        COALESCE(pl.platelets, prc.platelets) AS platelets,
        bil.bilirubin,
        cr.creatinine,
        pam.pam,
        gcs.gcs,
        COALESCE(vp.on_vasopressors, 0) AS on_vasopressors
    FROM admissions a
    LEFT JOIN pao2_values pao2 ON a.episode_ref = pao2.episode_ref AND pao2.rn = 1
    LEFT JOIN fio2_values fio2 ON a.episode_ref = fio2.episode_ref AND fio2.rn = 1
    LEFT JOIN platelets_lab pl ON a.episode_ref = pl.episode_ref AND pl.rn = 1
    LEFT JOIN platelets_rc prc ON a.episode_ref = prc.episode_ref AND prc.rn = 1
    LEFT JOIN bilirubin_values bil ON a.episode_ref = bil.episode_ref AND bil.rn = 1
    LEFT JOIN creatinine_values cr ON a.episode_ref = cr.episode_ref AND cr.rn = 1
    LEFT JOIN pam_values pam ON a.episode_ref = pam.episode_ref
    LEFT JOIN glasgow_values gcs ON a.episode_ref = gcs.episode_ref AND gcs.rn = 1
    LEFT JOIN vasopressors vp ON a.episode_ref = vp.episode_ref
),

-- =============================================================================
-- 7. CALCULAR SOFA SCORE
-- =============================================================================
sofa_scores AS (
    SELECT 
        sc.*,
        CASE 
            WHEN pf_ratio IS NULL THEN NULL
            WHEN pf_ratio < 100 THEN 4
            WHEN pf_ratio < 200 THEN 3
            WHEN pf_ratio < 300 THEN 2
            WHEN pf_ratio < 400 THEN 1
            ELSE 0
        END AS sofa_resp,
        CASE 
            WHEN platelets IS NULL THEN NULL
            WHEN platelets < 20 THEN 4
            WHEN platelets < 50 THEN 3
            WHEN platelets < 100 THEN 2
            WHEN platelets < 150 THEN 1
            ELSE 0
        END AS sofa_coag,
        CASE 
            WHEN bilirubin IS NULL THEN NULL
            WHEN bilirubin >= 12 THEN 4
            WHEN bilirubin >= 6 THEN 3
            WHEN bilirubin >= 2 THEN 2
            WHEN bilirubin >= 1.2 THEN 1
            ELSE 0
        END AS sofa_hepatic,
        CASE 
            WHEN pam IS NULL AND on_vasopressors = 0 THEN NULL
            WHEN on_vasopressors = 1 THEN 3
            WHEN pam < 70 THEN 1
            ELSE 0
        END AS sofa_cardio,
        CASE 
            WHEN gcs IS NULL THEN NULL
            WHEN gcs < 6 THEN 4
            WHEN gcs < 10 THEN 3
            WHEN gcs < 13 THEN 2
            WHEN gcs < 15 THEN 1
            ELSE 0
        END AS sofa_neuro,
        CASE 
            WHEN creatinine IS NULL THEN NULL
            WHEN creatinine >= 5 THEN 4
            WHEN creatinine >= 3.5 THEN 3
            WHEN creatinine >= 2 THEN 2
            WHEN creatinine >= 1.2 THEN 1
            ELSE 0
        END AS sofa_renal
    FROM sofa_components sc
),

sofa_total AS (
    SELECT 
        ss.*,
        COALESCE(sofa_resp, 0) + 
        COALESCE(sofa_coag, 0) + 
        COALESCE(sofa_hepatic, 0) + 
        COALESCE(sofa_cardio, 0) + 
        COALESCE(sofa_neuro, 0) + 
        COALESCE(sofa_renal, 0) AS sofa_score,
        (CASE WHEN sofa_resp IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sofa_coag IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sofa_hepatic IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sofa_cardio IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sofa_neuro IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sofa_renal IS NOT NULL THEN 1 ELSE 0 END) AS components_available
    FROM sofa_scores ss
)

-- =============================================================================
-- 8. RESULTADO FINAL: PACIENTES CON SEPSIS-3 (UN REGISTRO POR EPISODIO)
-- =============================================================================
SELECT 
    st.patient_ref,
    st.episode_ref,
    st.admission_date,
    st.ou_loc_ref,
    si.infection_onset,
    si.culture_date,
    si.antibiotic_date,
    st.pf_ratio,
    st.platelets,
    st.bilirubin,
    st.pam,
    st.on_vasopressors,
    st.gcs,
    st.creatinine,
    st.sofa_resp,
    st.sofa_coag,
    st.sofa_hepatic,
    st.sofa_cardio,
    st.sofa_neuro,
    st.sofa_renal,
    st.sofa_score,
    st.components_available,
    1 AS sepsis_flag
FROM sofa_total st
INNER JOIN suspected_infection_first si ON st.episode_ref = si.episode_ref
WHERE st.sofa_score >= 2
ORDER BY st.admission_date, st.patient_ref;