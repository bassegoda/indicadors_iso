import pandas as pd
from tableone import TableOne
import sys
import os
from pathlib import Path


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
        MIN(ou_loc_ref) as ou_loc_ref, 
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
def generate_table(csv_path, year, unit_list):
    """Genera una taula descriptiva a partir de les dades de cohort."""
    print(f"\n--- Processing Data for {year} ---")
    df = pd.read_csv(csv_path)

    # Safety Check
    if 'ou_loc_ref' not in df.columns:
        print("ERROR: CSV missing 'ou_loc_ref'. "
              "Please check your SQL export.")
        return

    # Dynamic Pre-processing
    df['unit'] = 'Unit ' + df['ou_loc_ref'].astype(str)
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

    # Variables
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

    # Generate Table
    table_two = TableOne(
        df,
        columns=columns,
        categorical=categorical,
        groupby='unit',
        nonnormal=nonnormal,
        rename=labels,
        pval=False,
        missing=False
    )

    # Export
    units_str = "-".join(unit_list).replace(" ", "")
    output_filename = f"cohort_table_{year}_{units_str}.html"

    # Create valid HTML with Title
    title_text = f"Analysis of {', '.join(unit_list)} in {year}"
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

    print(f"Success! Table saved to: {output_filename}")


# ==========================================
# 3. MAIN INTERACTIVE FLOW
# ==========================================
def main():
    """Flux principal d'execució interactiva."""
    print("========================================")
    print("   ICU COHORT ANALYSIS GENERATOR")
    print("========================================")

    # 1. Ask for User Input
    year_input = input("Enter Year (e.g., 2024): ").strip()
    units_input = input(
        "Enter Units separated by commas (e.g., E073, I073): "
    ).strip()

    # Clean up units list
    unit_list = [u.strip() for u in units_input.split(',')]
    sql_units_formatted = ", ".join([f"'{u}'" for u in unit_list])

    # 2. Modify and Save SQL Query
    query_content = SQL_TEMPLATE.format(
        year=year_input,
        units_formatted=sql_units_formatted
    )

    query_filename = "generated_query.sql"
    with open(query_filename, "w") as f:
        f.write(query_content)

    csv_filename = f"data_{year_input}.csv"

    print("\n----------------------------------------")
    print(f"1. A new SQL query has been saved to: '{query_filename}'")
    print(f"2. Please run this query in your database manager.")
    print(f"3. Export the result as a CSV file named: '{csv_filename}'")
    print(f"   (Make sure it is in the same folder as this script)")
    print("----------------------------------------")

    # 3. Wait for User Confirmation
    while True:
        confirm = input(
            f"\nHave you saved '{csv_filename}'? (yes/no): "
        ).lower()
        if confirm in ['y', 'yes']:
            if os.path.exists(csv_filename):
                break
            else:
                print(
                    f"ERROR: Could not find file '{csv_filename}'. "
                    f"Please check the name and location."
                )
        elif confirm in ['n', 'no']:
            print("Exiting. Please run the script again when you "
                  "have the data.")
            sys.exit()

    # 4. Run Analysis
    generate_table(csv_filename, year_input, unit_list)


if __name__ == "__main__":
    main()