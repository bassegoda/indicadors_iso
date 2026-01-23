import pandas as pd
from tableone import TableOne
import sys
from pathlib import Path

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query

# ==========================================
# 1. SQL TEMPLATE
# ==========================================
SQL_TEMPLATE = """
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
),
flagged_starts AS (
    SELECT 
        *,
        CASE 
            WHEN LAG(end_date) OVER (
                PARTITION BY episode_ref ORDER BY start_date
            ) = start_date 
            THEN 0 
            ELSE 1 
        END AS is_new_stay
    FROM raw_moves
),
grouped_stays AS (
    SELECT 
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_ref ORDER BY start_date
        ) as stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        SUBSTRING_INDEX(GROUP_CONCAT(ou_loc_ref ORDER BY start_date SEPARATOR ','), ',', 1) as ou_loc_ref,
        MIN(start_date) as true_start_date,
        MAX(end_date) as true_end_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) >= 10
),
cohort_with_next AS (
    SELECT 
        *,
        LEAD(true_start_date) OVER (
            PARTITION BY patient_ref ORDER BY true_start_date
        ) as next_admission_date
    FROM cohort
),
cirrhosis_dx AS (
    SELECT DISTINCT patient_ref
    FROM g_diagnostics
    WHERE code LIKE 'K70.3%' OR code LIKE 'K71.7%' OR code LIKE 'K74.3%'  
       OR code LIKE 'K74.4%' OR code LIKE 'K74.5%' OR code LIKE 'K74.6%' 
)
SELECT 
    c.patient_ref,
    c.episode_ref,
    c.ou_loc_ref,
    c.true_start_date,
    c.true_end_date,
    c.total_hours,
    d.sex,
    d.natio_descr AS nationality,
    TIMESTAMPDIFF(YEAR, d.birth_date, c.true_start_date) AS age_at_start,
    d.postcode,
    d.health_area,
    CASE 
        WHEN dx.patient_ref IS NOT NULL THEN 1 ELSE 0 
    END AS has_cirrhosis,
    CASE 
        WHEN e.exitus_date BETWEEN c.true_start_date AND c.true_end_date 
        THEN 1 ELSE 0 
    END AS exitus_in_icu,
    CASE 
        WHEN c.next_admission_date IS NOT NULL 
             AND TIMESTAMPDIFF(
                 HOUR, c.true_end_date, c.next_admission_date
             ) <= 24 
        THEN 1 ELSE 0 
    END AS readmission_at_24h,
    CASE 
        WHEN c.next_admission_date IS NOT NULL 
             AND TIMESTAMPDIFF(
                 HOUR, c.true_end_date, c.next_admission_date
             ) <= 72 
        THEN 1 ELSE 0 
    END AS readmission_at_72h
FROM cohort_with_next c
LEFT JOIN g_demographics d ON c.patient_ref = d.patient_ref
LEFT JOIN cirrhosis_dx dx ON c.patient_ref = dx.patient_ref
LEFT JOIN g_exitus e ON c.patient_ref = e.patient_ref
ORDER BY c.episode_ref, c.true_start_date;
"""


# ==========================================
# 2. ANALYSIS LOGIC
# ==========================================
def _add_semester_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["true_start_date"] = pd.to_datetime(df["true_start_date"], errors="coerce")
    df["semester"] = df["true_start_date"].dt.month.map(lambda m: "H1" if m <= 6 else "H2")
    return df


def generate_table(df, year, unit_list, split_semesters: bool = False):
    """Genera una taula descriptiva a partir de les dades de cohort."""
    df['unit'] = 'Unit ' + df['ou_loc_ref'].astype(str)
    if split_semesters:
        df = _add_semester_columns(df)
        df["unit_group"] = df["unit"] + " - " + df["semester"]
        groupby_col = "unit_group"
    else:
        groupby_col = "unit"

    df['los_days'] = df['total_hours'] / 24.0
    df['sex'] = df['sex'].map({1: 'Male', 2: 'Female'})

    binary_vars = [
        'has_cirrhosis',
        'exitus_in_icu',
        'readmission_at_24h',
        'readmission_at_72h'
    ]
    for var in binary_vars:
        df[var] = df[var].map({0: 'No', 1: 'Yes'})

    # Nationality Logic (TOP 6)
    top_6_nat = df['nationality'].value_counts().nlargest(6).index
    df['nationality'] = df['nationality'].where(
        df['nationality'].isin(top_6_nat),
        'Other'
    )
    df['nationality'] = pd.Categorical(
        df['nationality'],
        categories=df['nationality'].value_counts().index,
        ordered=True
    )

    columns = [
        'age_at_start',
        'sex',
        'nationality',
        'los_days',
        'has_cirrhosis',
        'exitus_in_icu',
        'readmission_at_24h',
        'readmission_at_72h'
    ]
    categorical = [
        'sex',
        'nationality',
        'has_cirrhosis',
        'exitus_in_icu',
        'readmission_at_24h',
        'readmission_at_72h'
    ]
    nonnormal = ['los_days']
    labels = {
        'age_at_start': 'Age (years)',
        'sex': 'Sex',
        'nationality': 'Nationality',
        'los_days': 'Length of Stay (days)',
        'has_cirrhosis': 'History of Cirrhosis',
        'exitus_in_icu': 'Mortality in ICU',
        'readmission_at_24h': 'Readmission (24h)',
        'readmission_at_72h': 'Readmission (72h)'
    }

    table_two = TableOne(
        df,
        columns=columns,
        categorical=categorical,
        groupby=groupby_col,
        nonnormal=nonnormal,
        rename=labels,
        pval=False,
        missing=False
    )

    # Crear carpeta output si no existe
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    units_str = "-".join(unit_list).replace(" ", "")
    suffix = "_semesters" if split_semesters else ""
    output_filename = output_dir / f"cohort_table_{year}_{units_str}{suffix}.html"

    title_text = f"Analysis of {', '.join(unit_list)} in {year}"
    if split_semesters:
        title_text += " (H1 vs H2)"
    full_html = (
        f"<html><head><style>"
        f"body{{font-family:Arial;margin:40px;}}"
        f"h2{{color:#2c3e50;}}"
        f"table{{border-collapse:collapse;width:100%;}}"
        f"th,td{{border:1px solid #ddd;padding:12px;}}"
        f"th{{background-color:#f8f9fa;}}"
        f"</style></head><body>"
        f"<h2>{title_text}</h2>"
        f"{table_two.to_html()}"
        f"</body></html>"
    )

    with open(output_filename, "w", encoding='utf-8') as f:
        f.write(full_html)

    print(f"Tabla guardada en: {output_filename}")


# ==========================================
# 3. MAIN FLOW
# ==========================================
def main():
    """Flux principal d'execució."""
    print("========================================")
    print("   ICU COHORT ANALYSIS GENERATOR")
    print("========================================")

    year_input = input("Enter Year (e.g., 2024): ").strip()
    units_input = input(
        "Enter Units separated by commas (e.g., E073, I073): "
    ).strip()
    split_semesters_input = input("Split analysis by semesters (H1/H2)? [y/N]: ").strip().lower()
    split_semesters = split_semesters_input in ("y", "yes", "s", "si")

    unit_list = [u.strip() for u in units_input.split(',')]
    sql_units_formatted = ", ".join([f"'{u}'" for u in unit_list])
    
    query = SQL_TEMPLATE.format(
        year=year_input,
        units_formatted=sql_units_formatted
    )
    
    df = execute_query(query)
    
    print(f"Datos obtenidos: {len(df)} registros")
    
    generate_table(df, year_input, unit_list, split_semesters=split_semesters)


if __name__ == "__main__":
    main()