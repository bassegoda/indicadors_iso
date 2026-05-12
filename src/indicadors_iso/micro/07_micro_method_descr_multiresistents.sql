-- Textos descriptivos extraidos de la query original (method_descr)
-- Dialect: Athena (Trino/Presto)
WITH method_descr_filtres AS (
    SELECT method_descr
    FROM (
        VALUES
            ('Frotis rectal. DetecciÃ³ BGNs multiresistents'),
            ('Frotis rectal. DetecciÃ³ de bacteris multiresistens (BGNs/Ent'),
            ('Frotis rectal. DetecciÃ³ de bacteris multiresistents'),
            ('Frotis rectal. DetecciÃ³n BGNs multiresitentes'),
            ('Frotis rectal. DetecciÃ³n BGNs multirresistentes'),
            ('Mostra ambiental. DetecciÃ³ de microorganismes multiresistent')
    ) AS t(method_descr)
)
SELECT
    m.patient_ref,
    m.episode_ref,
    m.extrac_date,
    m.res_date,
    m.ou_med_ref,
    m.mue_ref,
    m.mue_descr,
    m.method_descr,
    m.positive,
    m.antibiogram_ref,
    m.micro_ref,
    m.micro_descr,
    m.num_micro,
    m.result_text,
    m.load_date,
    m.care_level_ref
FROM datascope_gestor_prod.micro AS m
INNER JOIN method_descr_filtres f
    ON m.method_descr = f.method_descr
LIMIT 1048575;
