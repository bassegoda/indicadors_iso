import pandas as pd
from pathlib import Path
from datetime import datetime
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
                    PARTITION BY patient_ref, episode_ref ORDER BY start_date
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
            PARTITION BY patient_ref, episode_ref ORDER BY start_date
        ) AS stay_id
    FROM flagged_starts
),
time_per_unit AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) AS minutes_in_unit,
        MIN(start_date) AS first_start_date
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
            *,
            ROW_NUMBER() OVER (
                PARTITION BY patient_ref, episode_ref, stay_id
                ORDER BY minutes_in_unit DESC, first_start_date ASC
            ) AS rn
        FROM time_per_unit
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
# 2. CONSTANTES AISBE
# ==========================================

ABS_CLINIC = [
    "2A", "2B", "2C", "2D", "2E",
    "3A", "3B", "3C", "3D", "3E",
    "3G", "3H", "3I",
    "4A", "4B", "4C",
    "5A", "5B", "5C", "5D",
]
CP_CLINIC = [
    "08004", "08011", "08014", "08015", "08017", "08021",
    "08022", "08028", "08029", "08034", "08036", "08038",
]


# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================

def _format_median_iqr(series: pd.Series) -> str:
    series = series.dropna()
    if series.empty:
        return ""
    q1 = series.quantile(0.25)
    q2 = series.median()
    q3 = series.quantile(0.75)
    return f"{q2:.1f} [{q1:.1f}-{q3:.1f}]"


def _fmt_n_pct(count: int, total: int) -> str:
    if total == 0:
        return ""
    pct = count / total * 100
    return f"{count} ({pct:.1f}%)"


def _classify_aisbe(patient_df: pd.DataFrame) -> pd.Series:
    """Classify patients as AISBE based on health_area and postcode.

    Args:
        patient_df: DataFrame indexed by patient_ref with health_area and postcode columns.

    Returns:
        Boolean Series indexed by patient_ref.
    """
    ha = patient_df["health_area"].astype(str).str.strip()
    pc = patient_df["postcode"].astype(str).str.strip().str[:5]
    is_abs = ha.isin(ABS_CLINIC)
    is_cp = (~is_abs) & pc.isin(CP_CLINIC)
    return is_abs | is_cp


def _compute_mortality(sub: pd.DataFrame) -> dict:
    """Compute in-stay, 30-day and 90-day mortality from admission date.

    Returns dict with keys: deaths_stay, deaths_30, deaths_90,
    n (denominator), and formatted strings.
    """
    n = len(sub)
    if n == 0:
        return {
            "deaths_stay": 0, "deaths_30": 0, "deaths_90": 0, "n": 0,
            "stay_fmt": "", "d30_fmt": "", "d90_fmt": "",
        }

    deaths_stay = int((sub["exitus_during_stay"] == "Yes").sum())

    # 30/90-day mortality from admission date (standard clinical convention)
    admission_dt = pd.to_datetime(sub["admission_date"], errors="coerce")
    exitus_dt = pd.to_datetime(sub["exitus_date"], errors="coerce")
    valid = exitus_dt.notna() & admission_dt.notna()
    delta = (exitus_dt - admission_dt).dt.total_seconds() / 86400

    deaths_30 = int((valid & (delta >= 0) & (delta <= 30)).sum())
    deaths_90 = int((valid & (delta >= 0) & (delta <= 90)).sum())

    return {
        "deaths_stay": deaths_stay,
        "deaths_30": deaths_30,
        "deaths_90": deaths_90,
        "n": n,
        "stay_fmt": _fmt_n_pct(deaths_stay, n),
        "d30_fmt": _fmt_n_pct(deaths_30, n),
        "d90_fmt": _fmt_n_pct(deaths_90, n),
    }


# ==========================================
# 4. RESUMEN POR AÑO (CSV - flat)
# ==========================================

def build_yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build flat yearly summary for CSV export."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "days_stay" not in df.columns and "hours_stay" in df.columns:
        df["days_stay"] = df["hours_stay"] / 24.0
    df["year_admission"] = df["year_admission"].astype(int)

    summary_rows: dict[str, dict[int, str]] = {
        "N estancias": {},
        "N pacientes": {},
        "Edad, mediana [IQR]": {},
        "Sexo masculino (n, %)": {},
        "Sexo femenino (n, %)": {},
        "Nacionalidad española (n, %)": {},
        "Otras nacionalidades (n, %)": {},
        "Pacientes AISBE (n, %)": {},
        "Estancia (días), mediana [IQR]": {},
        "Cirrosis (n, %)": {},
        "Reingreso 24h (n, %)": {},
        "Reingreso 72h (n, %)": {},
        "Mortalidad global - en estancia (n, %)": {},
        "Mortalidad global - 30 días (n, %)": {},
        "Mortalidad global - 90 días (n, %)": {},
        "Mortalidad cirrosis - en estancia (n, %)": {},
        "Mortalidad cirrosis - 30 días (n, %)": {},
        "Mortalidad cirrosis - 90 días (n, %)": {},
        "Mortalidad no AISBE - en estancia (n, %)": {},
        "Mortalidad no AISBE - 30 días (n, %)": {},
        "Mortalidad no AISBE - 90 días (n, %)": {},
    }

    years = sorted(df["year_admission"].dropna().unique())

    for year in years:
        sub = df[df["year_admission"] == year]
        n = len(sub)
        summary_rows["N estancias"][year] = str(n)

        if n == 0:
            for key in summary_rows:
                summary_rows[key].setdefault(year, "")
            continue

        # Unique patients for patient-level metrics
        patients = sub.drop_duplicates(subset=["patient_ref"])
        n_pat = len(patients)
        summary_rows["N pacientes"][year] = str(n_pat)

        # Age (stay-level, as age varies by admission date)
        summary_rows["Edad, mediana [IQR]"][year] = _format_median_iqr(
            pd.to_numeric(sub["age_at_admission"], errors="coerce")
        )

        # Sex (patient-level)
        sex_counts = patients["sex"].value_counts(dropna=False)
        male = int(sex_counts.get("Male", 0))
        female = int(sex_counts.get("Female", 0))
        summary_rows["Sexo masculino (n, %)"][year] = _fmt_n_pct(male, n_pat)
        summary_rows["Sexo femenino (n, %)"][year] = _fmt_n_pct(female, n_pat)

        # Nationality (patient-level)
        natio = patients["natio_ref"].fillna("").astype(str)
        n_spain = int((natio == "ES").sum())
        n_other = n_pat - n_spain
        summary_rows["Nacionalidad española (n, %)"][year] = _fmt_n_pct(n_spain, n_pat)
        summary_rows["Otras nacionalidades (n, %)"][year] = _fmt_n_pct(n_other, n_pat)

        # AISBE (patient-level)
        patient_health = patients[["patient_ref", "health_area", "postcode"]].set_index(
            "patient_ref"
        )
        is_aisbe = _classify_aisbe(patient_health)
        n_aisbe = int(is_aisbe.sum())
        summary_rows["Pacientes AISBE (n, %)"][year] = _fmt_n_pct(n_aisbe, n_pat)

        # Length of stay (stay-level)
        summary_rows["Estancia (días), mediana [IQR]"][year] = _format_median_iqr(
            pd.to_numeric(sub["days_stay"], errors="coerce")
        )

        # Cirrhosis (stay-level prevalence)
        cirr = pd.to_numeric(sub["has_cirrhosis"], errors="coerce").fillna(0)
        has_cirr = int((cirr == 1).sum())
        summary_rows["Cirrosis (n, %)"][year] = _fmt_n_pct(has_cirr, n)

        # Readmissions (stay-level)
        for col, key in [
            ("readmission_24h", "Reingreso 24h (n, %)"),
            ("readmission_72h", "Reingreso 72h (n, %)"),
        ]:
            vals = pd.to_numeric(sub[col], errors="coerce").fillna(0)
            count = int((vals == 1).sum())
            summary_rows[key][year] = _fmt_n_pct(count, n)

        # Global mortality (from admission date)
        mort = _compute_mortality(sub)
        summary_rows["Mortalidad global - en estancia (n, %)"][year] = mort["stay_fmt"]
        summary_rows["Mortalidad global - 30 días (n, %)"][year] = mort["d30_fmt"]
        summary_rows["Mortalidad global - 90 días (n, %)"][year] = mort["d90_fmt"]

        # Cirrhosis mortality
        sub_cirr = sub[cirr == 1]
        mort_cirr = _compute_mortality(sub_cirr)
        summary_rows["Mortalidad cirrosis - en estancia (n, %)"][year] = mort_cirr["stay_fmt"]
        summary_rows["Mortalidad cirrosis - 30 días (n, %)"][year] = mort_cirr["d30_fmt"]
        summary_rows["Mortalidad cirrosis - 90 días (n, %)"][year] = mort_cirr["d90_fmt"]

        # Non-AISBE mortality
        patient_is_aisbe = sub["patient_ref"].map(is_aisbe).fillna(False)
        sub_no_aisbe = sub[~patient_is_aisbe.values]
        mort_no = _compute_mortality(sub_no_aisbe)
        summary_rows["Mortalidad no AISBE - en estancia (n, %)"][year] = mort_no["stay_fmt"]
        summary_rows["Mortalidad no AISBE - 30 días (n, %)"][year] = mort_no["d30_fmt"]
        summary_rows["Mortalidad no AISBE - 90 días (n, %)"][year] = mort_no["d90_fmt"]

    index = list(summary_rows.keys())
    data = {year: [summary_rows[row].get(year, "") for row in index] for year in years}

    summary_df = pd.DataFrame(data, index=index)
    summary_df.index.name = "Variable"
    return summary_df


# ==========================================
# 5. RESUMEN ESTRUCTURADO (para HTML)
# ==========================================

def build_yearly_summary_structured(df: pd.DataFrame) -> tuple[list[dict], list[int]]:
    """Build structured yearly summary for HTML report.

    Returns:
        (sections, years) where sections is a list of section dicts and
        years is the sorted list of year values.
    """
    if df.empty:
        return [], []

    df = df.copy()
    if "days_stay" not in df.columns and "hours_stay" in df.columns:
        df["days_stay"] = df["hours_stay"] / 24.0
    df["year_admission"] = df["year_admission"].astype(int)

    years = sorted(df["year_admission"].dropna().unique())

    # Accumulators per section; each row is {label, values:{year:str}, total:str, style:str}
    demo_rows = []
    clinical_rows = []
    mort_global_rows = []
    mort_cirr_rows = []
    mort_noaisbe_rows = []

    # -- Initialize row templates --
    def _new_row(label, style=""):
        return {"label": label, "values": {}, "total": "", "style": style}

    r_n_stays = _new_row("N estancias", "bold")
    r_n_patients = _new_row("N pacientes", "bold")
    r_age = _new_row("Edad, mediana [IQR]")
    r_male = _new_row("Sexo masculino", "indent")
    r_female = _new_row("Sexo femenino", "indent")
    r_spain = _new_row("Nacionalidad espa\u00f1ola", "indent")
    r_other_nat = _new_row("Otras nacionalidades", "indent")
    r_aisbe = _new_row("Pacientes AISBE")
    r_los = _new_row("Estancia (d\u00edas), mediana [IQR]")
    r_cirr = _new_row("Cirrosis")
    r_readm24 = _new_row("Reingreso 24h")
    r_readm72 = _new_row("Reingreso 72h")
    r_mg_stay = _new_row("En estancia")
    r_mg_30 = _new_row("A 30 d\u00edas")
    r_mg_90 = _new_row("A 90 d\u00edas")
    r_mc_stay = _new_row("En estancia")
    r_mc_30 = _new_row("A 30 d\u00edas")
    r_mc_90 = _new_row("A 90 d\u00edas")
    r_mn_stay = _new_row("En estancia")
    r_mn_30 = _new_row("A 30 d\u00edas")
    r_mn_90 = _new_row("A 90 d\u00edas")

    # Accumulators for totals
    total_stays = 0
    all_patients = set()
    all_ages = []
    total_male = 0
    total_female = 0
    total_spain = 0
    total_other_nat = 0
    total_aisbe = 0
    total_n_pat = 0
    all_los = []
    total_cirr = 0
    total_readm24 = 0
    total_readm72 = 0
    # Mortality totals
    t_mg = {"stay": 0, "d30": 0, "d90": 0, "n": 0}
    t_mc = {"stay": 0, "d30": 0, "d90": 0, "n": 0}
    t_mn = {"stay": 0, "d30": 0, "d90": 0, "n": 0}

    for year in years:
        sub = df[df["year_admission"] == year]
        n = len(sub)
        total_stays += n
        r_n_stays["values"][year] = str(n)

        if n == 0:
            for r in [r_n_patients, r_age, r_male, r_female, r_spain, r_other_nat,
                      r_aisbe, r_los, r_cirr, r_readm24, r_readm72,
                      r_mg_stay, r_mg_30, r_mg_90,
                      r_mc_stay, r_mc_30, r_mc_90,
                      r_mn_stay, r_mn_30, r_mn_90]:
                r["values"][year] = ""
            continue

        # Unique patients
        patients = sub.drop_duplicates(subset=["patient_ref"])
        n_pat = len(patients)
        all_patients.update(patients["patient_ref"].tolist())
        total_n_pat += n_pat
        r_n_patients["values"][year] = str(n_pat)

        # Age
        ages = pd.to_numeric(sub["age_at_admission"], errors="coerce").dropna()
        all_ages.extend(ages.tolist())
        r_age["values"][year] = _format_median_iqr(ages)

        # Sex (patient-level)
        sex_counts = patients["sex"].value_counts(dropna=False)
        male = int(sex_counts.get("Male", 0))
        female = int(sex_counts.get("Female", 0))
        total_male += male
        total_female += female
        r_male["values"][year] = _fmt_n_pct(male, n_pat)
        r_female["values"][year] = _fmt_n_pct(female, n_pat)

        # Nationality (patient-level)
        natio = patients["natio_ref"].fillna("").astype(str)
        n_spain = int((natio == "ES").sum())
        n_other = n_pat - n_spain
        total_spain += n_spain
        total_other_nat += n_other
        r_spain["values"][year] = _fmt_n_pct(n_spain, n_pat)
        r_other_nat["values"][year] = _fmt_n_pct(n_other, n_pat)

        # AISBE
        patient_health = patients[["patient_ref", "health_area", "postcode"]].set_index(
            "patient_ref"
        )
        is_aisbe = _classify_aisbe(patient_health)
        n_aisbe = int(is_aisbe.sum())
        total_aisbe += n_aisbe
        r_aisbe["values"][year] = _fmt_n_pct(n_aisbe, n_pat)

        # Length of stay
        los = pd.to_numeric(sub["days_stay"], errors="coerce").dropna()
        all_los.extend(los.tolist())
        r_los["values"][year] = _format_median_iqr(los)

        # Cirrhosis
        cirr = pd.to_numeric(sub["has_cirrhosis"], errors="coerce").fillna(0)
        has_cirr = int((cirr == 1).sum())
        total_cirr += has_cirr
        r_cirr["values"][year] = _fmt_n_pct(has_cirr, n)

        # Readmissions
        for col, row_ref, total_ref_name in [
            ("readmission_24h", r_readm24, "total_readm24"),
            ("readmission_72h", r_readm72, "total_readm72"),
        ]:
            vals = pd.to_numeric(sub[col], errors="coerce").fillna(0)
            count = int((vals == 1).sum())
            row_ref["values"][year] = _fmt_n_pct(count, n)
            if total_ref_name == "total_readm24":
                total_readm24 += count
            else:
                total_readm72 += count

        # Global mortality
        mort = _compute_mortality(sub)
        r_mg_stay["values"][year] = mort["stay_fmt"]
        r_mg_30["values"][year] = mort["d30_fmt"]
        r_mg_90["values"][year] = mort["d90_fmt"]
        t_mg["stay"] += mort["deaths_stay"]
        t_mg["d30"] += mort["deaths_30"]
        t_mg["d90"] += mort["deaths_90"]
        t_mg["n"] += mort["n"]

        # Cirrhosis mortality
        sub_cirr = sub[cirr == 1]
        mort_c = _compute_mortality(sub_cirr)
        r_mc_stay["values"][year] = mort_c["stay_fmt"]
        r_mc_30["values"][year] = mort_c["d30_fmt"]
        r_mc_90["values"][year] = mort_c["d90_fmt"]
        t_mc["stay"] += mort_c["deaths_stay"]
        t_mc["d30"] += mort_c["deaths_30"]
        t_mc["d90"] += mort_c["deaths_90"]
        t_mc["n"] += mort_c["n"]

        # Non-AISBE mortality
        patient_is_aisbe = sub["patient_ref"].map(is_aisbe).fillna(False)
        sub_no_aisbe = sub[~patient_is_aisbe.values]
        mort_n = _compute_mortality(sub_no_aisbe)
        r_mn_stay["values"][year] = mort_n["stay_fmt"]
        r_mn_30["values"][year] = mort_n["d30_fmt"]
        r_mn_90["values"][year] = mort_n["d90_fmt"]
        t_mn["stay"] += mort_n["deaths_stay"]
        t_mn["d30"] += mort_n["deaths_30"]
        t_mn["d90"] += mort_n["deaths_90"]
        t_mn["n"] += mort_n["n"]

    # -- Compute totals --
    r_n_stays["total"] = str(total_stays)
    r_n_patients["total"] = str(len(all_patients))
    r_age["total"] = _format_median_iqr(pd.Series(all_ages)) if all_ages else ""
    r_male["total"] = _fmt_n_pct(total_male, total_n_pat)
    r_female["total"] = _fmt_n_pct(total_female, total_n_pat)
    r_spain["total"] = _fmt_n_pct(total_spain, total_n_pat)
    r_other_nat["total"] = _fmt_n_pct(total_other_nat, total_n_pat)
    r_aisbe["total"] = _fmt_n_pct(total_aisbe, total_n_pat)
    r_los["total"] = _format_median_iqr(pd.Series(all_los)) if all_los else ""
    r_cirr["total"] = _fmt_n_pct(total_cirr, total_stays)
    r_readm24["total"] = _fmt_n_pct(total_readm24, total_stays)
    r_readm72["total"] = _fmt_n_pct(total_readm72, total_stays)

    r_mg_stay["total"] = _fmt_n_pct(t_mg["stay"], t_mg["n"])
    r_mg_30["total"] = _fmt_n_pct(t_mg["d30"], t_mg["n"])
    r_mg_90["total"] = _fmt_n_pct(t_mg["d90"], t_mg["n"])
    r_mc_stay["total"] = _fmt_n_pct(t_mc["stay"], t_mc["n"])
    r_mc_30["total"] = _fmt_n_pct(t_mc["d30"], t_mc["n"])
    r_mc_90["total"] = _fmt_n_pct(t_mc["d90"], t_mc["n"])
    r_mn_stay["total"] = _fmt_n_pct(t_mn["stay"], t_mn["n"])
    r_mn_30["total"] = _fmt_n_pct(t_mn["d30"], t_mn["n"])
    r_mn_90["total"] = _fmt_n_pct(t_mn["d90"], t_mn["n"])

    # -- Assemble sections --
    sections = [
        {
            "section": "Demograf\u00eda",
            "css": "demo",
            "rows": [r_n_stays, r_n_patients, r_age, r_male, r_female,
                     r_spain, r_other_nat, r_aisbe],
        },
        {
            "section": "Cl\u00ednica",
            "css": "clinical",
            "rows": [r_los, r_cirr, r_readm24, r_readm72],
        },
        {
            "section": "Mortalidad global",
            "css": "mortality",
            "rows": [r_mg_stay, r_mg_30, r_mg_90],
        },
        {
            "section": "Mortalidad en cirrosis",
            "css": "mortality-cirr",
            "rows": [r_mc_stay, r_mc_30, r_mc_90],
        },
        {
            "section": "Mortalidad en no AISBE",
            "css": "mortality-noaisbe",
            "rows": [r_mn_stay, r_mn_30, r_mn_90],
        },
    ]

    return sections, years


# ==========================================
# 6. HTML REPORT GENERATION
# ==========================================

_CSS = """
:root {
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    --color-text: #1f2937;
    --color-text-muted: #6b7280;
    --color-border: #e5e7eb;
    --color-border-thick: #d1d5db;
    --color-bg: #ffffff;
    --color-bg-header: #f8fafc;
    --color-bg-total: #f8fafc;
    --section-demo: #eef2f7;
    --section-demo-text: #1e3a5f;
    --section-demo-accent: #3b82f6;
    --section-clinical: #eef2f7;
    --section-clinical-text: #1e3a5f;
    --section-clinical-accent: #3b82f6;
    --section-mortality: #fef2f2;
    --section-mortality-text: #991b1b;
    --section-mortality-accent: #ef4444;
    --section-mortality-cirr: #faf5ff;
    --section-mortality-cirr-text: #581c87;
    --section-mortality-cirr-accent: #a855f7;
    --section-mortality-noaisbe: #f3f4f6;
    --section-mortality-noaisbe-text: #374151;
    --section-mortality-noaisbe-accent: #6b7280;
}

* { box-sizing: border-box; }

body {
    font-family: var(--font-sans);
    color: var(--color-text);
    margin: 0;
    padding: 40px;
    background: #f9fafb;
    line-height: 1.5;
}

.container {
    max-width: 1300px;
    margin: 0 auto;
    background: var(--color-bg);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    overflow: hidden;
}

/* Header */
.report-header {
    padding: 32px 40px 24px;
    border-bottom: 1px solid var(--color-border);
}
.report-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--color-text);
    margin: 0 0 6px;
}
.report-header .subtitle {
    font-size: 14px;
    color: var(--color-text-muted);
    margin: 0;
}

/* Table wrapper for horizontal scroll */
.table-wrapper {
    overflow-x: auto;
    padding: 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
    min-width: 800px;
}

thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--color-bg-header);
    padding: 12px 16px;
    text-align: center;
    font-weight: 600;
    font-size: 13px;
    color: var(--color-text);
    border-bottom: 2px solid var(--color-border-thick);
    white-space: nowrap;
}
thead th:first-child {
    text-align: left;
    min-width: 220px;
    position: sticky;
    left: 0;
    z-index: 3;
    background: var(--color-bg-header);
}
thead th.col-total {
    border-left: 2px solid var(--color-border-thick);
    background: var(--color-bg-total);
    font-weight: 700;
}

/* Section header rows */
tr.section-header td {
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--color-border);
    border-top: 1px solid var(--color-border);
}
tr.section-header td:first-child {
    border-left: 4px solid transparent;
}

tr.section-demo td { background: var(--section-demo); color: var(--section-demo-text); }
tr.section-demo td:first-child { border-left-color: var(--section-demo-accent); }
tr.section-clinical td { background: var(--section-clinical); color: var(--section-clinical-text); }
tr.section-clinical td:first-child { border-left-color: var(--section-clinical-accent); }
tr.section-mortality td { background: var(--section-mortality); color: var(--section-mortality-text); }
tr.section-mortality td:first-child { border-left-color: var(--section-mortality-accent); }
tr.section-mortality-cirr td { background: var(--section-mortality-cirr); color: var(--section-mortality-cirr-text); }
tr.section-mortality-cirr td:first-child { border-left-color: var(--section-mortality-cirr-accent); }
tr.section-mortality-noaisbe td { background: var(--section-mortality-noaisbe); color: var(--section-mortality-noaisbe-text); }
tr.section-mortality-noaisbe td:first-child { border-left-color: var(--section-mortality-noaisbe-accent); }

/* Data rows */
tbody td {
    padding: 9px 16px;
    text-align: center;
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
tbody td:first-child {
    text-align: left;
    color: var(--color-text);
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--color-bg);
}
tbody td.col-total {
    border-left: 2px solid var(--color-border-thick);
    background: var(--color-bg-total);
    font-weight: 600;
}
tbody tr:hover td {
    background-color: #f1f5f9;
}
tbody tr:hover td:first-child {
    background-color: #f1f5f9;
}
tbody tr:hover td.col-total {
    background-color: #eef2f6;
}

/* Row styles */
tr.row-bold td:first-child { font-weight: 700; }
tr.row-bold td { font-weight: 600; }
tr.row-indent td:first-child { padding-left: 36px; color: var(--color-text-muted); }

/* Footer */
.report-footer {
    padding: 24px 40px;
    border-top: 1px solid var(--color-border);
    background: #fafbfc;
}
.report-footer h3 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin: 0 0 10px;
    font-weight: 600;
}
.report-footer ul {
    margin: 0;
    padding: 0 0 0 18px;
    font-size: 12px;
    color: var(--color-text-muted);
    line-height: 1.7;
}
.report-footer .timestamp {
    margin-top: 14px;
    font-size: 11px;
    color: #9ca3af;
}

/* Print */
@media print {
    body { background: #fff; padding: 0; margin: 0; }
    .container { box-shadow: none; border-radius: 0; }
    .report-header { padding: 20px; }
    table { font-size: 10px; min-width: 0; }
    thead th, tbody td { padding: 5px 8px; }
    thead th:first-child, tbody td:first-child { position: static; }
    thead { display: table-header-group; }
    .report-footer { padding: 16px 20px; }
    @page { size: landscape; margin: 1cm; }
}

@media (max-width: 768px) {
    body { padding: 16px; }
    .report-header { padding: 20px; }
    .report-header h1 { font-size: 18px; }
    table { font-size: 11px; }
    thead th, tbody td { padding: 6px 10px; }
}
"""


def generate_html_report(
    sections: list[dict],
    years: list[int],
    title: str,
    output_path: Path,
) -> None:
    """Generate a professional HTML report from structured summary data."""

    n_cols = len(years) + 2  # Variable + years + Total

    # Header row
    year_ths = "".join(f'<th>{y}</th>' for y in years)
    thead = (
        f'<thead><tr>'
        f'<th>Variable</th>'
        f'{year_ths}'
        f'<th class="col-total">Total</th>'
        f'</tr></thead>'
    )

    # Body
    body_rows = []
    for sec in sections:
        # Section header
        body_rows.append(
            f'<tr class="section-header section-{sec["css"]}">'
            f'<td colspan="{n_cols}">{sec["section"]}</td>'
            f'</tr>'
        )
        for row in sec["rows"]:
            style = row.get("style", "")
            row_class = f'row-{style}' if style else ''
            cells = [f'<td>{row["label"]}</td>']
            for y in years:
                cells.append(f'<td>{row["values"].get(y, "")}</td>')
            cells.append(f'<td class="col-total">{row.get("total", "")}</td>')
            body_rows.append(
                f'<tr class="{row_class}">' + "".join(cells) + '</tr>'
            )

    tbody = '<tbody>' + "\n".join(body_rows) + '</tbody>'

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">

<div class="report-header">
    <h1>{title}</h1>
    <p class="subtitle">Hospital Cl\u00ednic de Barcelona &mdash; Unidades E073, I073</p>
</div>

<div class="table-wrapper">
<table>
{thead}
{tbody}
</table>
</div>

<div class="report-footer">
    <h3>Notas metodol\u00f3gicas</h3>
    <ul>
        <li><strong>Unidades analizadas:</strong> E073, I073 (movimientos con place_ref v\u00e1lido).</li>
        <li><strong>Estancia:</strong> movimientos consecutivos agrupados con tolerancia de 5 min; unidad predominante por tiempo.</li>
        <li><strong>Filtro de prescripci\u00f3n:</strong> solo estancias con al menos una prescripci\u00f3n activa durante la estancia.</li>
        <li><strong>Sexo y nacionalidad:</strong> calculados a nivel de paciente \u00fanico (no de estancia).</li>
        <li><strong>AISBE:</strong> pacientes con \u00e1rea b\u00e1sica de salud del \u00e1rea de influencia del hospital o c\u00f3digo postal correspondiente.</li>
        <li><strong>Mortalidad a 30/90 d\u00edas:</strong> acumulada desde la fecha de ingreso (incluye muertes intrahospitalarias).</li>
        <li><strong>Cirrosis:</strong> diagn\u00f3stico ICD-9/ICD-10 en cualquier episodio del paciente (condici\u00f3n cr\u00f3nica).</li>
        <li><strong>Reingresos:</strong> siguiente ingreso en E073/I073 dentro del plazo indicado tras el alta.</li>
        <li><strong>Total:</strong> pacientes \u00fanicos se cuentan una vez; porcentajes se calculan sobre la suma de los denominadores anuales.</li>
    </ul>
    <p class="timestamp">Informe generado el {now_str}</p>
</div>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ==========================================
# 7. MAIN
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
        patient_health_all = (
            df[["patient_ref", "health_area", "postcode"]]
            .drop_duplicates(subset=["patient_ref"])
            .set_index("patient_ref")
        )
        n_patients_all = len(patient_health_all)

        ha_all = patient_health_all["health_area"].astype(str).str.strip()

        # Missing en health_area
        missing_health = ha_all.eq("") | ha_all.eq("nan")
        n_missing_health = int(missing_health.sum())
        pct_missing_health = (
            n_missing_health / n_patients_all * 100 if n_patients_all > 0 else 0.0
        )
        print(
            f"Pacientes \u00fanicos: {n_patients_all} | "
            f"health_area missing/vac\u00eda en {n_missing_health} "
            f"({pct_missing_health:.1f}%)"
        )

        # Distribución de áreas básicas de salud (no missing)
        print("\nDistribuci\u00f3n de health_area (top 20):")
        ha_counts = ha_all[~missing_health].value_counts().head(20)
        for area, count in ha_counts.items():
            pct = count / n_patients_all * 100 if n_patients_all > 0 else 0.0
            print(f"  {area}: {count} pacientes ({pct:.1f}%)")

        # AISBE classification
        is_aisbe_all = _classify_aisbe(patient_health_all)
        n_aisbe_total = int(is_aisbe_all.sum())
        pct_aisbe_total = (
            n_aisbe_total / n_patients_all * 100 if n_patients_all > 0 else 0.0
        )

        is_abs_all = patient_health_all["health_area"].astype(str).str.strip().isin(ABS_CLINIC)
        n_aisbe_ha = int(is_abs_all.sum())
        n_aisbe_cp = n_aisbe_total - n_aisbe_ha

        print(
            "\nClasificaci\u00f3n AISBE (toda la cohorte, a nivel paciente):\n"
            f"  AISBE por health_area (ABS cl\u00ednicas): {n_aisbe_ha}\n"
            f"  AISBE a\u00f1adido por c\u00f3digo postal: {n_aisbe_cp}\n"
            f"  Total AISBE: {n_aisbe_total} "
            f"({pct_aisbe_total:.1f}% de los pacientes \u00fanicos)"
        )

    # Crear carpeta output si no existe
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Guardar cohorte completa
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)
    cohort_filename = output_dir / f"ward_stays_cohort_{years_str}_E073-I073.csv"
    df.to_csv(cohort_filename, index=False, encoding="utf-8-sig")
    print(f"Cohorte completa guardada en: {cohort_filename}")

    # CSV summary (flat)
    summary_df = build_yearly_summary(df)
    summary_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.csv"
    summary_df.to_csv(summary_filename, encoding="utf-8-sig")
    print(f"Tabla resumen (CSV) guardada en: {summary_filename}")

    # HTML summary (structured)
    sections, section_years = build_yearly_summary_structured(df)
    html_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.html"
    title_text = f"Demograf\u00eda y resultados de estancias en E073+I073 ({years_str})"
    generate_html_report(sections, section_years, title_text, html_filename)
    print(f"Tabla resumen (HTML) guardada en: {html_filename}")


if __name__ == "__main__":
    main()
