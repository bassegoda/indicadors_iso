import pandas as pd
from pathlib import Path
import sys

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query


# ==========================================
# 1. SQL TEMPLATE
# ==========================================

SQL_TEMPLATE = """
WITH all_related_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM g_movements
    WHERE ou_loc_ref IN ('E073','I073')
      AND start_date <= '{max_year}-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '{min_year}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    SELECT
        *,
        CASE
            WHEN ABS(TIMESTAMPDIFF(MINUTE,
                LAG(effective_end_date) OVER (
                    PARTITION BY episode_ref ORDER BY start_date
                ),
                start_date
            )) <= 5
            THEN 0
            ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    SELECT
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
time_per_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) AS minutes_in_unit
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id, ou_loc_ref
),
predominant_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref AS assigned_unit,
        minutes_in_unit AS max_minutes
    FROM (
        SELECT
            t.patient_ref,
            t.episode_ref,
            t.stay_id,
            t.ou_loc_ref,
            t.minutes_in_unit,
            ROW_NUMBER() OVER (
                PARTITION BY t.patient_ref, t.episode_ref, t.stay_id
                ORDER BY t.minutes_in_unit DESC, MIN(g.start_date) ASC
            ) AS rn
        FROM time_per_unit t
        INNER JOIN grouped_stays g
            ON t.patient_ref = g.patient_ref
            AND t.episode_ref = g.episode_ref
            AND t.stay_id = g.stay_id
            AND t.ou_loc_ref = g.ou_loc_ref
        GROUP BY t.patient_ref, t.episode_ref, t.stay_id,
                 t.ou_loc_ref, t.minutes_in_unit
    ) ranked
    WHERE rn = 1
),
cohort AS (
    SELECT
        g.patient_ref,
        g.episode_ref,
        g.stay_id,
        p.assigned_unit AS ou_loc_ref,
        MIN(g.start_date) AS admission_date,
        MAX(g.end_date) AS discharge_date,
        MAX(g.effective_end_date) AS effective_discharge_date,
        TIMESTAMPDIFF(HOUR, MIN(g.start_date), MAX(g.effective_end_date)) AS hours_stay,
        TIMESTAMPDIFF(DAY, MIN(g.start_date), MAX(g.effective_end_date)) AS days_stay,
        TIMESTAMPDIFF(MINUTE, MIN(g.start_date), MAX(g.effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(g.end_date) IS NULL THEN 'Yes' ELSE 'No' END AS still_admitted,
        COUNT(*) AS num_movements,
        COUNT(DISTINCT g.ou_loc_ref) AS num_units_visited
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.patient_ref = p.patient_ref
        AND g.episode_ref = p.episode_ref
        AND g.stay_id = p.stay_id
    GROUP BY g.patient_ref, g.episode_ref, g.stay_id, p.assigned_unit
    HAVING YEAR(MIN(g.start_date)) BETWEEN {min_year} AND {max_year}
),
prescription_filtered AS (
    SELECT DISTINCT
        c.*
    FROM cohort c
    INNER JOIN g_prescriptions p
        ON c.patient_ref = p.patient_ref
        AND c.episode_ref = p.episode_ref
        AND p.start_drug_date BETWEEN c.admission_date
            AND c.effective_discharge_date
),
cohort_with_next AS (
    SELECT
        c.*,
        LEAD(admission_date) OVER (
            PARTITION BY patient_ref ORDER BY admission_date
        ) AS next_admission_date
    FROM prescription_filtered c
),
cirrhosis_dx AS (
    SELECT DISTINCT patient_ref
    FROM g_diagnostics
    WHERE
        -- ICD-10 cirrhosis-related codes
        code LIKE 'K70.3%' OR
        code LIKE 'K71.7%' OR
        code LIKE 'K74.3%' OR
        code LIKE 'K74.4%' OR
        code LIKE 'K74.5%' OR
        code LIKE 'K74.6%' OR
        -- ICD-9 cirrhosis-related codes
        code LIKE '571.2%' OR
        code LIKE '571.5%' OR
        code LIKE '571.6%' OR
        code LIKE '571.8%' OR
        code LIKE '571.9%'
)
SELECT DISTINCT
    cw.patient_ref,
    cw.episode_ref,
    cw.stay_id,
    cw.ou_loc_ref,
    cw.admission_date,
    cw.discharge_date,
    cw.effective_discharge_date,
    cw.hours_stay,
    cw.days_stay,
    cw.minutes_stay,
    cw.still_admitted,
    cw.num_movements,
    cw.num_units_visited,
    CASE
        WHEN cw.num_units_visited > 1 THEN 'Yes'
        ELSE 'No'
    END AS had_transfer,
    YEAR(cw.admission_date) AS year_admission,
    TIMESTAMPDIFF(YEAR, d.birth_date, cw.admission_date) AS age_at_admission,
    d.natio_ref,
    CASE
        WHEN d.sex = 1 THEN 'Male'
        WHEN d.sex = 2 THEN 'Female'
        WHEN d.sex = 3 THEN 'Other'
        ELSE 'Not reported'
    END AS sex,
    d.natio_descr AS nationality,
    d.health_area,
    d.postcode,
    CASE
        WHEN ex.exitus_date IS NOT NULL
             AND ex.exitus_date BETWEEN cw.admission_date
                 AND cw.effective_discharge_date
        THEN 'Yes'
        ELSE 'No'
    END AS exitus_during_stay,
    ex.exitus_date,
    CASE
        WHEN dx.patient_ref IS NOT NULL THEN 1 ELSE 0
    END AS has_cirrhosis,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND TIMESTAMPDIFF(
                 HOUR, cw.effective_discharge_date, cw.next_admission_date
             ) <= 24
        THEN 1 ELSE 0
    END AS readmission_24h,
    CASE
        WHEN cw.next_admission_date IS NOT NULL
             AND TIMESTAMPDIFF(
                 HOUR, cw.effective_discharge_date, cw.next_admission_date
             ) <= 72
        THEN 1 ELSE 0
    END AS readmission_72h
FROM cohort_with_next cw
LEFT JOIN g_demographics d
    ON cw.patient_ref = d.patient_ref
LEFT JOIN cirrhosis_dx dx
    ON cw.patient_ref = dx.patient_ref
LEFT JOIN g_exitus ex
    ON cw.patient_ref = ex.patient_ref
ORDER BY cw.admission_date;
"""


# ==========================================
# 2. RESUMEN POR AÑO
# ==========================================

def _format_median_iqr(series: pd.Series) -> str:
    series = series.dropna()
    if series.empty:
        return ""
    q1 = series.quantile(0.25)
    q2 = series.median()
    q3 = series.quantile(0.75)
    return f"{q2:.1f} [{q1:.1f}-{q3:.1f}]"


def build_yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Normalizar columnas clave
    if "days_stay" not in df.columns and "hours_stay" in df.columns:
        df["days_stay"] = df["hours_stay"] / 24.0

    df["year_admission"] = df["year_admission"].astype(int)

    # El orden de las claves define el orden visual de las filas
    summary_rows: dict[str, dict[int, str]] = {
        "N estancias": {},
        "Edad, mediana [IQR]": {},
        "Sexo": {},
        "Nacionalidad": {},
        "Pacientes AISBE (n, %)": {},
        "Estancia (días), mediana [IQR]": {},
        "Cirrosis (n, %)": {},
        "Reingreso 24h (n, %)": {},
        "Reingreso 72h (n, %)": {},
        "Mortalidad global (estancia, 30d, 90d) (n, %)": {},
        "Mortalidad en cirrosis (estancia, 30d, 90d) (n, %)": {},
        "Mortalidad en no AISBE (estancia, 30d, 90d) (n, %)": {},
    }

    years = sorted(df["year_admission"].dropna().unique())

    for year in years:
        sub = df[df["year_admission"] == year]
        n = len(sub)

        # N estancias
        summary_rows["N estancias"][year] = str(n)

        if n == 0:
            for key in summary_rows:
                summary_rows[key].setdefault(year, "")
            continue

        # Edad
        summary_rows["Edad, mediana [IQR]"][year] = _format_median_iqr(
            pd.to_numeric(sub["age_at_admission"], errors="coerce")
        )

        # Sexo (una sola fila con M/F)
        sex_counts = sub["sex"].value_counts(dropna=False)
        male_count = int(sex_counts.get("Male", 0))
        female_count = int(sex_counts.get("Female", 0))
        male_pct = (male_count / n * 100) if n > 0 else 0.0
        female_pct = (female_count / n * 100) if n > 0 else 0.0
        summary_rows["Sexo"][year] = (
            f"Masculino: {male_count} ({male_pct:.1f}%), "
            f"Femenino: {female_count} ({female_pct:.1f}%)"
        )

        # Nacionalidad: España vs Otras (ES en natio_ref), en una sola fila
        is_spain = sub.get("natio_ref", "").fillna("") == "ES"
        n_spain = int(is_spain.sum())
        n_other = n - n_spain
        pct_spain = (n_spain / n * 100) if n > 0 else 0.0
        pct_other = (n_other / n * 100) if n > 0 else 0.0
        summary_rows["Nacionalidad"][year] = (
            f"España: {n_spain} ({pct_spain:.1f}%), "
            f"Otras: {n_other} ({pct_other:.1f}%)"
        )

        # Pacientes de ABS clínicas (basado en paciente, no en estancias)
        abs_clinic = [
            "2A", "2B", "2C", "2D", "2E",
            "3A", "3B", "3C", "3D", "3E",
            "3G", "3H", "3I",
            "4A", "4B", "4C",
            "5A", "5B", "5C", "5D",
        ]
        cp_clinic = [
            "08004", "08011", "08014", "08015", "08017", "08021",
            "08022", "08028", "08029", "08034", "08036", "08038",
        ]

        # Un registro por paciente con su health_area y postcode (primera aparición)
        patient_health = (
            sub[["patient_ref", "health_area", "postcode"]]
            .drop_duplicates(subset=["patient_ref"])
            .set_index("patient_ref")
        )
        n_patients_year = len(patient_health)
        if n_patients_year > 0:
            ha = patient_health["health_area"].astype(str).str.strip()
            pc = (
                patient_health["postcode"]
                .astype(str)
                .str.strip()
                .str[:5]
            )

            # Regla AISBE:
            # 1) Si health_area está en abs_clinic -> AISBE
            # 2) Si no, pero postcode está en cp_clinic -> AISBE
            is_abs = ha.isin(abs_clinic)
            is_cp = (~is_abs) & pc.isin(cp_clinic)
            is_aisbe = is_abs | is_cp

            n_abs = int(is_aisbe.sum())
            pct_abs = n_abs / n_patients_year * 100
            summary_rows["Pacientes AISBE (n, %)"][year] = (
                f"{n_abs} ({pct_abs:.1f}%)"
            )
        else:
            summary_rows["Pacientes AISBE (n, %)"][year] = ""

        # Estancia (días)
        summary_rows["Estancia (días), mediana [IQR]"][year] = _format_median_iqr(
            pd.to_numeric(sub["days_stay"], errors="coerce")
        )

        # Mortalidad durante la estancia (toda la cohorte)
        deaths = int((sub["exitus_during_stay"] == "Yes").sum())
        deaths_pct = (deaths / n * 100) if n > 0 else 0.0

        # Mortalidad a 30 y 90 días post-alta (toda la cohorte)
        exitus_date = pd.to_datetime(sub["exitus_date"], errors="coerce")
        discharge_date = pd.to_datetime(sub["effective_discharge_date"], errors="coerce")
        valid_dates = exitus_date.notna() & discharge_date.notna()
        delta_days = (exitus_date - discharge_date).dt.total_seconds() / 86400

        # Mortalidad acumulada a 30/90 días desde el inicio de la estancia
        # (incluye muertes intrahospitalarias y post-alta)
        death_30 = valid_dates & (delta_days <= 30)
        death_90 = valid_dates & (delta_days <= 90)

        deaths_30 = int(death_30.sum())
        deaths_90 = int(death_90.sum())
        deaths_30_pct = (deaths_30 / n * 100) if n > 0 else 0.0
        deaths_90_pct = (deaths_90 / n * 100) if n > 0 else 0.0

        summary_rows["Mortalidad global (estancia, 30d, 90d) (n, %)"][year] = (
            f"En estancia: {deaths} ({deaths_pct:.1f}%), "
            f"30 días: {deaths_30} ({deaths_30_pct:.1f}%), "
            f"90 días: {deaths_90} ({deaths_90_pct:.1f}%)"
        )

        # Reingresos
        for col, row_key in [
            ("readmission_24h", "Reingreso 24h (n, %)"),
            ("readmission_72h", "Reingreso 72h (n, %)"),
        ]:
            vals = pd.to_numeric(sub[col], errors="coerce").fillna(0)
            count = int((vals == 1).sum())
            pct = (count / n * 100) if n > 0 else 0.0
            summary_rows[row_key][year] = f"{count} ({pct:.1f}%)"

        # Cirrosis (prevalencia)
        cirr = pd.to_numeric(sub["has_cirrhosis"], errors="coerce").fillna(0)
        has_cirr = int((cirr == 1).sum())
        cirr_pct = (has_cirr / n * 100) if n > 0 else 0.0
        summary_rows["Cirrosis (n, %)"][year] = f"{has_cirr} ({cirr_pct:.1f}%)"

        # Subgrupo con cirrosis: mortalidad en estancia, 30 y 90 días
        sub_cirr = sub[cirr == 1]
        n_cirr = len(sub_cirr)
        if n_cirr > 0:
            # En estancia
            deaths_cirr_stay = int((sub_cirr["exitus_during_stay"] == "Yes").sum())
            deaths_cirr_stay_pct = (deaths_cirr_stay / n_cirr * 100) if n_cirr > 0 else 0.0

            # 30 y 90 días post-alta
            exitus_cirr = pd.to_datetime(sub_cirr["exitus_date"], errors="coerce")
            discharge_cirr = pd.to_datetime(
                sub_cirr["effective_discharge_date"], errors="coerce"
            )
            valid_cirr = exitus_cirr.notna() & discharge_cirr.notna()
            delta_cirr = (exitus_cirr - discharge_cirr).dt.total_seconds() / 86400

            # Mortalidad acumulada 30/90 días en cirróticos
            death_cirr_30 = valid_cirr & (delta_cirr <= 30)
            death_cirr_90 = valid_cirr & (delta_cirr <= 90)

            deaths_cirr_30 = int(death_cirr_30.sum())
            deaths_cirr_90 = int(death_cirr_90.sum())
            deaths_cirr_30_pct = (
                deaths_cirr_30 / n_cirr * 100
            ) if n_cirr > 0 else 0.0
            deaths_cirr_90_pct = (
                deaths_cirr_90 / n_cirr * 100
            ) if n_cirr > 0 else 0.0

            summary_rows["Mortalidad en cirrosis (estancia, 30d, 90d) (n, %)"][year] = (
                f"En estancia: {deaths_cirr_stay} ({deaths_cirr_stay_pct:.1f}%), "
                f"30 días: {deaths_cirr_30} ({deaths_cirr_30_pct:.1f}%), "
                f"90 días: {deaths_cirr_90} ({deaths_cirr_90_pct:.1f}%)"
            )
        else:
            summary_rows["Mortalidad en cirrosis (estancia, 30d, 90d) (n, %)"][year] = ""

        # Subgrupo NO AISBE: mortalidad en estancia, 30 y 90 días
        # Reutilizamos is_aisbe definido arriba
        if n_patients_year > 0:
            # Marcamos AISBE a nivel estancia (por paciente_ref)
            # Para simplificar, consideramos estancia NO AISBE si su paciente no es AISBE
            patient_is_aisbe = is_aisbe.reindex(sub["patient_ref"]).fillna(False).to_numpy()
            sub_no_aisbe = sub[~patient_is_aisbe]
            n_no_aisbe = len(sub_no_aisbe)
        else:
            sub_no_aisbe = sub.iloc[0:0]
            n_no_aisbe = 0

        if n_no_aisbe > 0:
            # En estancia
            deaths_no_stay = int((sub_no_aisbe["exitus_during_stay"] == "Yes").sum())
            deaths_no_stay_pct = (
                deaths_no_stay / n_no_aisbe * 100 if n_no_aisbe > 0 else 0.0
            )

            # 30 y 90 días (mortalidad acumulada desde la estancia)
            exitus_no = pd.to_datetime(sub_no_aisbe["exitus_date"], errors="coerce")
            discharge_no = pd.to_datetime(
                sub_no_aisbe["effective_discharge_date"], errors="coerce"
            )
            valid_no = exitus_no.notna() & discharge_no.notna()
            delta_no = (exitus_no - discharge_no).dt.total_seconds() / 86400

            death_no_30 = valid_no & (delta_no <= 30)
            death_no_90 = valid_no & (delta_no <= 90)

            deaths_no_30 = int(death_no_30.sum())
            deaths_no_90 = int(death_no_90.sum())
            deaths_no_30_pct = (
                deaths_no_30 / n_no_aisbe * 100 if n_no_aisbe > 0 else 0.0
            )
            deaths_no_90_pct = (
                deaths_no_90 / n_no_aisbe * 100 if n_no_aisbe > 0 else 0.0
            )

            summary_rows["Mortalidad en no AISBE (estancia, 30d, 90d) (n, %)"][year] = (
                f"En estancia: {deaths_no_stay} ({deaths_no_stay_pct:.1f}%), "
                f"30 días: {deaths_no_30} ({deaths_no_30_pct:.1f}%), "
                f"90 días: {deaths_no_90} ({deaths_no_90_pct:.1f}%)"
            )
        else:
            summary_rows["Mortalidad en no AISBE (estancia, 30d, 90d) (n, %)"][year] = ""

    index = list(summary_rows.keys())
    data = {year: [summary_rows[row].get(year, "") for row in index] for year in years}

    summary_df = pd.DataFrame(data, index=index)
    summary_df.index.name = "Variable"

    return summary_df


# ==========================================
# 3. MAIN
# ==========================================

def main():
    print("========================================")
    print("   WARD STAYS DEMOGRAPHIC TABLE (E073+I073)")
    print("========================================")

    year_input = input(
        "Enter year range (e.g., 2018-2024, default 2018-2024): "
    ).strip()

    if not year_input:
        min_year, max_year = 2018, 2024
    elif "-" in year_input:
        start, end = year_input.split("-", 1)
        min_year, max_year = int(start), int(end)
    else:
        year_val = int(year_input)
        min_year = max_year = year_val

    print(f"Using years from {min_year} to {max_year}")

    query = SQL_TEMPLATE.format(min_year=min_year, max_year=max_year)
    df = execute_query(query)

    print(f"Datos de cohorte obtenidos: {len(df)} estancias")

    # Análisis rápido de health_area y AISBE a nivel paciente (toda la cohorte)
    if "health_area" in df.columns:
        abs_clinic = [
            "2A", "2B", "2C", "2D", "2E",
            "3A", "3B", "3C", "3D", "3E",
            "3G", "3H", "3I",
            "4A", "4B", "4C",
            "5A", "5B", "5C", "5D",
        ]
        cp_clinic = [
            "08004", "08011", "08014", "08015", "08017", "08021",
            "08022", "08028", "08029", "08034", "08036", "08038",
        ]

        patient_health_all = (
            df[["patient_ref", "health_area", "postcode"]]
            .drop_duplicates(subset=["patient_ref"])
            .set_index("patient_ref")
        )
        n_patients_all = len(patient_health_all)

        ha_all = patient_health_all["health_area"].astype(str).str.strip()
        pc_all = (
            patient_health_all["postcode"]
            .astype(str)
            .str.strip()
            .str[:5]
        )

        # Missing en health_area
        missing_health = ha_all.eq("") | ha_all.eq("nan")
        n_missing_health = int(missing_health.sum())
        pct_missing_health = (
            n_missing_health / n_patients_all * 100 if n_patients_all > 0 else 0.0
        )
        print(
            f"Pacientes únicos: {n_patients_all} | "
            f"health_area missing/vacía en {n_missing_health} "
            f"({pct_missing_health:.1f}%)"
        )

        # Distribución de áreas básicas de salud (no missing)
        print("\nDistribución de health_area (top 20):")
        ha_counts = ha_all[~missing_health].value_counts().head(20)
        for area, count in ha_counts.items():
            pct = count / n_patients_all * 100 if n_patients_all > 0 else 0.0
            print(f"  {area}: {count} pacientes ({pct:.1f}%)")

        # AISBE por health_area y por código postal
        is_abs_all = ha_all.isin(abs_clinic)
        is_cp_all = (~is_abs_all) & pc_all.isin(cp_clinic)
        is_aisbe_all = is_abs_all | is_cp_all

        n_aisbe_total = int(is_aisbe_all.sum())
        pct_aisbe_total = (
            n_aisbe_total / n_patients_all * 100 if n_patients_all > 0 else 0.0
        )

        n_aisbe_ha = int(is_abs_all.sum())
        n_aisbe_cp = int(is_cp_all.sum())

        print(
            "\nClasificación AISBE (toda la cohorte, a nivel paciente):\n"
            f"  AISBE por health_area (ABS clínicas): {n_aisbe_ha}\n"
            f"  AISBE añadido por código postal: {n_aisbe_cp}\n"
            f"  Total AISBE: {n_aisbe_total} "
            f"({pct_aisbe_total:.1f}% de los pacientes únicos)"
        )

    # Crear carpeta output si no existe
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Guardar cohorte completa por si se necesita para análisis adicionales
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)
    cohort_filename = output_dir / f"ward_stays_cohort_{years_str}_E073-I073.csv"
    df.to_csv(cohort_filename, index=False, encoding="utf-8-sig")
    print(f"Cohorte completa guardada en: {cohort_filename}")

    # Construir tabla resumen
    summary_df = build_yearly_summary(df)

    summary_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.csv"
    summary_df.to_csv(summary_filename, encoding="utf-8-sig")
    print(f"Tabla resumen (CSV) guardada en: {summary_filename}")

    # Exportar a HTML con formato más profesional
    html_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.html"

    title_text = f"Demografía y resultados de estancias en E073+I073 ({years_str})"

    # Construir tabla HTML manualmente para poder estilizar secciones
    columns = list(summary_df.columns)
    header_cells = "".join(f"<th>{col}</th>" for col in ["Variable"] + columns)

    body_rows = []
    for idx, row in summary_df.iterrows():
        # Estilos suaves por secciones
        if idx in {
            "N estancias",
            "Edad, mediana [IQR]",
            "Sexo",
            "Nacionalidad",
            "Pacientes AISBE (n, %)",
            "Estancia (días), mediana [IQR]",
        }:
            row_style = "background-color:#fafafa;font-weight:500;"
        elif idx in {
            "Cirrosis (n, %)",
            "Reingreso 24h (n, %)",
            "Reingreso 72h (n, %)",
        }:
            row_style = "background-color:#ffffff;"
        elif idx.startswith("Mortalidad global"):
            row_style = "background-color:#f3f4f6;font-weight:600;"
        elif idx.startswith("Mortalidad en cirrosis"):
            row_style = "background-color:#f9f5ff;"
        elif idx.startswith("Mortalidad en no AISBE"):
            row_style = "background-color:#f5f5f5;"
        else:
            row_style = ""

        cells = [f"<td style='text-align:left;'>{idx}</td>"]
        for col in columns:
            val = row[col]
            cells.append(f"<td>{val}</td>")
        body_rows.append(f"<tr style='{row_style}'>" + "".join(cells) + "</tr>")

    table_html = (
        "<table>"
        "<thead><tr>"
        f"{header_cells}"
        "</tr></thead>"
        "<tbody>"
        + "".join(body_rows) +
        "</tbody></table>"
    )

    full_html = (
        "<html><head><meta charset='utf-8'/>"
        "<style>"
        "body{font-family:Arial,Helvetica,sans-serif;margin:40px;}"
        "h2{color:#1f2933;margin-bottom:24px;}"
        "table{border-collapse:collapse;width:100%;font-size:14px;}"
        "th,td{border:1px solid #e1e4e8;padding:8px;text-align:center;}"
        "th{background-color:#f8f9fa;font-weight:600;}"
        "tbody tr:hover{background-color:#f1f5f9;}"
        "</style></head><body>"
        f"<h2>{title_text}</h2>"
        f"{table_html}"
        "</body></html>"
    )

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Tabla resumen (HTML) guardada en: {html_filename}")


if __name__ == "__main__":
    main()

