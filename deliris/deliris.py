import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 1. Setup Project Root using Pathlib (Clean & Modern)
# Assuming this script is inside a folder one level deep (e.g., /scripts/myscript.py)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from connection import execute_query as eq

# ==========================================
# SQL TEMPLATES
# ==========================================
DELIRIUM_ASSESSMENTS_SQL = """
SELECT
    patient_ref,
    episode_ref,
    result_date,
    ou_loc_ref,
    result_txt
FROM g_rc
WHERE rc_sap_ref = 'DELIRIO_CAM-ICU'
  AND result_txt IN ('DELIRIO_CAM-ICU_1', 'DELIRIO_CAM-ICU_2', 'DELIRIO_CAM-ICU_3')
  AND ou_loc_ref IN ({units_formatted})
  AND result_date BETWEEN '{year}-01-01 00:00:00' AND '{year}-12-31 23:59:59';
"""

# Cohort + delirium analysis in E073/I073 (per stay)
COHORT_DELIRIUM_SQL = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date BETWEEN '{year}-01-01' AND '{year}-12-31 23:59:59'
      AND start_date != end_date
),
flagged_starts AS (
    SELECT 
        *,
        CASE 
            WHEN LAG(end_date) OVER (PARTITION BY episode_ref ORDER BY start_date) = start_date 
            THEN 0 
            ELSE 1 
        END AS is_new_stay
    FROM raw_moves
),
grouped_stays AS (
    SELECT 
        *,
        SUM(is_new_stay) OVER (PARTITION BY episode_ref ORDER BY start_date) as stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT 
        patient_ref,
        episode_ref,
        stay_id,
        MIN(ou_loc_ref) as ou_loc_ref, 
        MIN(start_date) as true_start_date,
        MAX(end_date) as true_end_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) >= 10
),
delirium_rc AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        result_date,
        result_txt
    FROM g_rc
    WHERE rc_sap_ref = 'DELIRIO_CAM-ICU'
      AND result_txt IN ('DELIRIO_CAM-ICU_1', 'DELIRIO_CAM-ICU_2', 'DELIRIO_CAM-ICU_3')
      AND result_date BETWEEN '{year}-01-01 00:00:00' AND '{year}-12-31 23:59:59'
),
cohort_rc AS (
    SELECT
        c.patient_ref,
        c.episode_ref,
        c.stay_id,
        c.ou_loc_ref,
        c.true_start_date,
        c.true_end_date,
        c.total_hours,
        r.result_date,
        r.result_txt
    FROM cohort c
    LEFT JOIN delirium_rc r
      ON r.patient_ref = c.patient_ref
     AND r.result_date BETWEEN c.true_start_date AND c.true_end_date
)
SELECT
    patient_ref,
    episode_ref,
    stay_id,
    ou_loc_ref,
    true_start_date,
    true_end_date,
    total_hours,
    COUNT(result_txt) AS total_assessments,
    SUM(CASE WHEN result_txt = 'DELIRIO_CAM-ICU_2' THEN 1 ELSE 0 END) AS present_count,
    MIN(result_date) AS first_assessment_date,
    MIN(CASE WHEN result_txt = 'DELIRIO_CAM-ICU_2' THEN result_date ELSE NULL END) AS first_present_date
FROM cohort_rc
GROUP BY patient_ref, episode_ref, stay_id, ou_loc_ref, true_start_date, true_end_date, total_hours
ORDER BY episode_ref, true_start_date;
"""


def _print_hepatica_delirium_analysis(df_stays: pd.DataFrame, year: int, units: list[str]) -> None:
    # Defensive conversions
    df_stays = df_stays.copy()
    for col in ["true_start_date", "true_end_date", "first_assessment_date", "first_present_date"]:
        if col in df_stays.columns:
            df_stays[col] = pd.to_datetime(df_stays[col], errors="coerce")

    df_stays["has_any_assessment"] = df_stays["total_assessments"].fillna(0).astype(int) > 0
    df_stays["has_delirium_present"] = df_stays["present_count"].fillna(0).astype(int) > 0

    # Time-to-event (hours) for those with dates
    df_stays["hours_to_first_assessment"] = (
        (df_stays["first_assessment_date"] - df_stays["true_start_date"]).dt.total_seconds() / 3600.0
    )
    df_stays["hours_to_first_present"] = (
        (df_stays["first_present_date"] - df_stays["true_start_date"]).dt.total_seconds() / 3600.0
    )

    n_stays = len(df_stays)
    n_patients = df_stays["patient_ref"].nunique() if "patient_ref" in df_stays.columns else None
    n_assessed = int(df_stays["has_any_assessment"].sum())
    n_present = int(df_stays["has_delirium_present"].sum())

    pct_assessed = (n_assessed / n_stays * 100.0) if n_stays else 0.0
    pct_present_all = (n_present / n_stays * 100.0) if n_stays else 0.0
    pct_present_among_assessed = (n_present / n_assessed * 100.0) if n_assessed else 0.0

    print("\n" + "=" * 72)
    print(f"DELIRIUM (CAM-ICU) EN COHORTE ADMITIDA A {', '.join(units)} - {year}")
    print("=" * 72)
    print(f"Estancias (>=10h): {n_stays}")
    if n_patients is not None:
        print(f"Pacientes únicos: {n_patients}")
    print(f"Estancias con >=1 evaluación: {n_assessed} ({pct_assessed:.1f}%)")
    print(f"Estancias con >=1 'Present': {n_present} ({pct_present_all:.1f}%)")
    print(f"'Present' entre evaluadas: {pct_present_among_assessed:.1f}%")

    if n_assessed:
        med_assess = df_stays.loc[df_stays["has_any_assessment"], "hours_to_first_assessment"].median()
        print(f"Mediana horas hasta 1ª evaluación: {med_assess:.1f} h")
    if n_present:
        med_present = df_stays.loc[df_stays["has_delirium_present"], "hours_to_first_present"].median()
        print(f"Mediana horas hasta 1er 'Present': {med_present:.1f} h")
    print("=" * 72)


def _parse_units(units_input: str) -> list[str]:
    units = [u.strip() for u in units_input.split(",") if u.strip()]
    # Remove duplicates, preserve order
    seen = set()
    out = []
    for u in units:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


def main() -> None:
    print("========================================")
    print("   DELIRIUM (CAM-ICU) ANALYSIS")
    print("========================================")

    year_input = input("Enter Year (e.g., 2025): ").strip()
    units_input = input("Enter Units separated by commas (e.g., E073, I073): ").strip()

    try:
        year = int(year_input)
    except ValueError:
        raise ValueError(f"Año inválido: {year_input!r}")

    unit_list = _parse_units(units_input)
    if not unit_list:
        raise ValueError("Debes indicar al menos una unidad (p.ej. E073).")

    sql_units_formatted = ", ".join([f"'{u}'" for u in unit_list])

    # 2. Load and Execute delirium assessments
    query = DELIRIUM_ASSESSMENTS_SQL.format(year=year, units_formatted=sql_units_formatted)
    df = eq(query)

# Check if data exists
    if df.empty:
        print("No data returned from the query.")
        return

# 3. Clean & Map Data (Do this globally first)
# Using a dictionary map is faster and cleaner than 3 separate .loc calls
    result_mapping = {
        'DELIRIO_CAM-ICU_1': 'Absent',
        'DELIRIO_CAM-ICU_2': 'Present',
        'DELIRIO_CAM-ICU_3': 'Other'
    }
    df['result_txt'] = df['result_txt'].replace(result_mapping)

# 4. Prepare Plot Data
# Sorting by count descending makes the chart easier to read
    icu_counts = df['ou_loc_ref'].value_counts().reset_index()
    icu_counts.columns = ['ICU', 'Count']
    icu_counts = icu_counts.sort_values('Count', ascending=False)

# 5. Plotting
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")

# Create the plot object (ax) to manipulate it later
    ax = sns.barplot(
        data=icu_counts,
        x="ICU",
        y="Count",
        hue="ICU",
        palette="viridis",
        legend=False,
        order=icu_counts['ICU'] # Ensure plot follows our sorted order
    )

# Title and Labels
    plt.title(f"Recompte d'avaluacions de delirium (CAM-ICU) {year}", fontsize=16, fontweight='bold', color='#333')
    plt.xlabel("Unitat (ICU)", fontsize=12)
    plt.ylabel("Nombre de registres", fontsize=12)

# Modern way to add labels (No need for manual loops/calculations)
    ax.bar_label(ax.containers[0], padding=3, fontsize=10)

    plt.tight_layout()

# Save plot
    units_str = "-".join(unit_list).replace(" ", "")
    output_path = project_root / "deliris" / f"icu_delirium_counts_{year}_{units_str}.png"
    plt.savefig(output_path, dpi=400)
    print(f"Plot saved to: {output_path}")

# 6. Specific Statistics for Hepàtica (E073, I073)
    print("\n" + "=" * 72)
    print(f"Recompte d'avaluacions de delirium (CAM-ICU) a {', '.join(unit_list)}")
    print("=" * 72)

    df_units = df[df['ou_loc_ref'].isin(unit_list)]
    delirium_counts = df_units['result_txt'].value_counts()
    print(delirium_counts)

    print("-" * 72)
    total_assessments = int(delirium_counts.sum())
    delirium_present = int(delirium_counts.get('Present', 0))
    proportion_delirium = (delirium_present / total_assessments * 100) if total_assessments > 0 else 0
    print(f"Total evaluaciones: {total_assessments}")
    print(f"Casos 'Present': {delirium_present}")
    print(f"Proporción 'Present': {proportion_delirium:.2f}%")
    print("=" * 72)

# 7. Cohort-based delirium analysis for admissions to E073/I073
    query_cohort = COHORT_DELIRIUM_SQL.format(year=year, units_formatted=sql_units_formatted)
    df_stays = eq(query_cohort)

    if df_stays.empty:
        print("\nNo se encontraron estancias (>=10h) para la cohorte con esas unidades.")
    else:
        _print_hepatica_delirium_analysis(df_stays, year, unit_list)


if __name__ == "__main__":
    main()