"""
HOSPITALISATION WARD STAYS

Admission criteria (all three must be met):
1. Bed assigned (place_ref IS NOT NULL)
2. Admission date (MIN start_date after merging) falls within the requested year(s)
3. At least one prescription initiated on or after admission
   (start_drug_date >= admission_date AND start_drug_date <= discharge_date)

Stay-merging logic:
    Consecutive movements in g_movements whose end_date equals the next
    start_date are merged into a single stay.  The date filter on raw
    movements uses a broad overlap (movement touches the year range) so
    that merging is never corrupted by movements that cross a year
    boundary.  The year filter is then applied on the MERGED admission_date.

Prescription scope:
    Joined on episode_ref (ED episodes have a different episode_ref from
    the HOSP episode, so ED prescriptions are not included).  Validated
    against E073/2024: no false negatives from the ED->ICU pathway.

Outputs one CSV per unit.
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add root directory to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query


# ==========================================
# CONFIGURATION
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ==========================================
# SQL
# ==========================================
SQL_WARD_STAYS = """
WITH raw_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref = '{unit}'
      AND start_date <= '{max_year}-12-31 23:59:59'
      AND end_date   >= '{min_year}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND end_date > start_date
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
        '{unit}' as ou_loc_ref,
        MIN(start_date) as admission_date,
        MAX(end_date) as discharge_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS hours_stay,
        TIMESTAMPDIFF(DAY, MIN(start_date), MAX(end_date)) AS days_stay,
        TIMESTAMPDIFF(MINUTE, MIN(start_date), MAX(end_date)) AS minutes_stay,
        COUNT(*) as num_movements
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING YEAR(MIN(start_date)) BETWEEN {min_year} AND {max_year}
)
SELECT DISTINCT
    c.patient_ref,
    c.episode_ref,
    c.stay_id,
    c.ou_loc_ref,
    c.admission_date,
    c.discharge_date,
    c.hours_stay,
    c.days_stay,
    c.minutes_stay,
    c.num_movements,
    YEAR(c.admission_date) as year_admission,
    TIMESTAMPDIFF(YEAR, d.birth_date, c.admission_date) as age_at_admission,
    CASE
        WHEN d.sex = 1 THEN 'Male'
        WHEN d.sex = 2 THEN 'Female'
        WHEN d.sex = 3 THEN 'Other'
        ELSE 'Not reported'
    END as sex,
    CASE
        WHEN ex.exitus_date IS NOT NULL
             AND ex.exitus_date BETWEEN c.admission_date AND c.discharge_date
        THEN 'Yes'
        ELSE 'No'
    END as exitus_during_stay,
    ex.exitus_date
FROM cohort c
LEFT JOIN g_demographics d 
    ON c.patient_ref = d.patient_ref
LEFT JOIN g_exitus ex 
    ON c.patient_ref = ex.patient_ref
INNER JOIN g_prescriptions p 
    ON c.patient_ref = p.patient_ref 
    AND c.episode_ref = p.episode_ref
    AND p.start_drug_date BETWEEN c.admission_date AND c.discharge_date
ORDER BY c.admission_date;
"""


# ==========================================
# FUNCTIONS
# ==========================================
def get_years_from_user() -> list:
    """Prompt user for years to analyse."""
    print("\nYears to analyse (e.g. 2024 or 2023-2025): ", end="")
    user_input = input().strip()
    
    if "-" in user_input:
        start, end = map(int, user_input.split("-"))
        return list(range(start, end + 1))
    elif "," in user_input:
        return [int(y.strip()) for y in user_input.split(",")]
    else:
        return [int(user_input)]


def get_units_from_user() -> list:
    """Prompt user for units to analyse."""
    print("Units to analyse (e.g. E073 or E073,I073): ", end="")
    user_input = input().strip().upper()
    return [u.strip() for u in user_input.split(",")]


def process_unit(unit: str, years: list, timestamp: str):
    """Run query for a unit and save CSV."""
    min_year = min(years)
    max_year = max(years)

    query = SQL_WARD_STAYS.format(
        unit=unit,
        min_year=min_year,
        max_year=max_year
    )

    df = execute_query(query)

    if df.empty:
        print(f"[{unit}] No data found")
        return

    # Save CSV
    year_str = f"{min_year}-{max_year}" if len(years) > 1 else str(min_year)
    filename = OUTPUT_DIR / f"admissions_{unit}_{year_str}_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Summary
    total = len(df)
    patients = df['patient_ref'].nunique()
    deaths = (df['exitus_during_stay'] == 'Yes').sum()
    mortality = (deaths / total * 100) if total > 0 else 0

    print(f"[{unit}] {total} stays | {patients} patients | {deaths} deaths ({mortality:.1f}%) | {filename.name}")


# ==========================================
# MAIN
# ==========================================
def main():
    print("\n" + "="*70)
    print("  HOSPITALISATION WARD STAYS")
    print("="*70)

    years = get_years_from_user()
    units = get_units_from_user()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\nProcessing {len(units)} unit(s) for years {min(years)}-{max(years)}...\n")

    for unit in units:
        process_unit(unit, years, timestamp)

    print(f"\n✓ Output saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()