"""
HOSPITALISATION WARD STAYS - PREDOMINANT UNIT ASSIGNMENT (val_ schema)

Same logic as hosp_ward_longest_stay.py but for database with:
- Tables: val_movements, val_demographics, val_exitus, val_prescriptions (g_ → val_)
- episode_ref → episode_sap, patient_ref → nhc

Admission criteria (all three must be met):
1. Bed assigned (place_ref IS NOT NULL)
2. Admission date falls within the requested year(s)
3. At least one prescription initiated during the stay

Stay-merging logic:
    Consecutive movements across related units are merged into a single
    hospitalisation stay. A tolerance of 5 minutes is used to detect
    consecutive movements (accounts for minor timestamp mismatches).
    The stay is assigned to the unit where the patient spent the MOST
    TIME (longest stay principle), with first-visited tiebreaker.

    Example: E073(2d)→I073(8d) = ONE stay assigned to I073
    Prevents double-counting when patients transfer between units.

Prescription filter validation (E073/2024):
    96.4% of stays have prescriptions. Excluded 3.6% are ultra-short
    (mean 6.2h) non-clinical cases: pre-transplant evaluations, phantom
    admissions, brief transfers.

Output: One CSV per unit (only stays assigned to that unit)
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
# SQL BUILDER
# ==========================================
def build_hours_per_unit_cases(units: list) -> str:
    """Build CASE statements for hours per unit."""
    cases = []
    for unit in units:
        cases.append(f"""
        SUM(CASE WHEN g.ou_loc_ref = '{unit}'
            THEN TIMESTAMPDIFF(MINUTE, g.start_date, COALESCE(g.end_date, NOW()))
            ELSE 0 END) as minutes_{unit}""")
    return ",".join(cases)


def build_sql_query(units: list) -> str:
    """Build complete SQL query with dynamic units."""
    units_list = "'" + "','".join(units) + "'"
    hours_cases = build_hours_per_unit_cases(units)

    # Build column list for final SELECT
    hours_columns = ",\n    ".join([f"c.minutes_{unit}" for unit in units])

    return f"""
WITH all_related_moves AS (
    -- Get movements from all specified units
    -- end_date can be NULL (patient still admitted); use NOW() as proxy
    SELECT
        nhc,
        episode_sap,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM val_movements
    WHERE ou_loc_ref IN ({units_list})
      AND start_date <= '{{max_year}}-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '{{min_year}}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    -- Mark where new stays begin (across all units)
    -- Tolerance: movements within 5 minutes are considered consecutive
    SELECT
        *,
        CASE
            WHEN ABS(TIMESTAMPDIFF(MINUTE,
                LAG(effective_end_date) OVER (
                    PARTITION BY episode_sap ORDER BY start_date
                ),
                start_date
            )) <= 5
            THEN 0
            ELSE 1
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    -- Number each stay within the episode
    SELECT
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_sap ORDER BY start_date
        ) as stay_id
    FROM flagged_starts
),
time_per_unit AS (
    -- Calculate MINUTES spent in each unit per stay (minutes avoids truncation)
    SELECT
        nhc,
        episode_sap,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) as minutes_in_unit
    FROM grouped_stays
    GROUP BY nhc, episode_sap, stay_id, ou_loc_ref
),
predominant_unit AS (
    -- Identify unit with most time per stay
    -- ROW_NUMBER with first-visited tiebreaker to avoid duplicates on ties
    SELECT
        nhc,
        episode_sap,
        stay_id,
        ou_loc_ref as assigned_unit,
        minutes_in_unit as max_minutes
    FROM (
        SELECT
            t.nhc,
            t.episode_sap,
            t.stay_id,
            t.ou_loc_ref,
            t.minutes_in_unit,
            ROW_NUMBER() OVER (
                PARTITION BY t.nhc, t.episode_sap, t.stay_id
                ORDER BY t.minutes_in_unit DESC, MIN(g.start_date) ASC
            ) as rn
        FROM time_per_unit t
        INNER JOIN grouped_stays g
            ON t.nhc = g.nhc
            AND t.episode_sap = g.episode_sap
            AND t.stay_id = g.stay_id
            AND t.ou_loc_ref = g.ou_loc_ref
        GROUP BY t.nhc, t.episode_sap, t.stay_id,
                 t.ou_loc_ref, t.minutes_in_unit
    ) ranked
    WHERE rn = 1
),
cohort AS (
    -- Merge movements into complete stays
    SELECT
        g.nhc,
        g.episode_sap,
        g.stay_id,
        p.assigned_unit as ou_loc_ref,
        MIN(g.start_date) as admission_date,
        MAX(g.end_date) as discharge_date,
        MAX(g.effective_end_date) as effective_discharge_date,
        TIMESTAMPDIFF(HOUR, MIN(g.start_date), MAX(g.effective_end_date)) AS hours_stay,
        TIMESTAMPDIFF(DAY, MIN(g.start_date), MAX(g.effective_end_date)) AS days_stay,
        TIMESTAMPDIFF(MINUTE, MIN(g.start_date), MAX(g.effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(g.end_date) IS NULL THEN 'Yes' ELSE 'No' END as still_admitted,
        COUNT(*) as num_movements,
        COUNT(DISTINCT g.ou_loc_ref) as num_units_visited,{hours_cases}
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.nhc = p.nhc
        AND g.episode_sap = p.episode_sap
        AND g.stay_id = p.stay_id
    GROUP BY g.nhc, g.episode_sap, g.stay_id, p.assigned_unit
    HAVING YEAR(MIN(g.start_date)) BETWEEN {{min_year}} AND {{max_year}}
       AND p.assigned_unit = '{{unit}}'  -- Only stays assigned to requested unit
)
SELECT DISTINCT
    c.nhc,
    c.episode_sap,
    c.stay_id,
    c.ou_loc_ref,
    c.admission_date,
    c.discharge_date,
    c.effective_discharge_date,
    c.hours_stay,
    c.days_stay,
    c.minutes_stay,
    c.still_admitted,
    c.num_movements,
    c.num_units_visited,
    {hours_columns},
    CASE
        WHEN c.num_units_visited > 1 THEN 'Yes'
        ELSE 'No'
    END as had_transfer,
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
             AND ex.exitus_date BETWEEN c.admission_date
                 AND c.effective_discharge_date
        THEN 'Yes'
        ELSE 'No'
    END as exitus_during_stay,
    ex.exitus_date
FROM cohort c
LEFT JOIN val_demographics d
    ON c.nhc = d.nhc
LEFT JOIN val_exitus ex
    ON c.nhc = ex.nhc
INNER JOIN val_prescriptions p
    ON c.nhc = p.nhc
    AND c.episode_sap = p.episode_sap
    AND p.start_drug_date BETWEEN c.admission_date
        AND c.effective_discharge_date
ORDER BY c.admission_date;
"""


def build_sql_count_query(units: list) -> str:
    """Build SQL that counts total stays per unit (no prescription filter)."""
    units_list = "'" + "','".join(units) + "'"
    hours_cases = build_hours_per_unit_cases(units)
    return f"""
WITH all_related_moves AS (
    SELECT
        nhc,
        episode_sap,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM val_movements
    WHERE ou_loc_ref IN ({units_list})
      AND start_date <= '{{max_year}}-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '{{min_year}}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    SELECT
        *,
        CASE
            WHEN ABS(TIMESTAMPDIFF(MINUTE,
                LAG(effective_end_date) OVER (
                    PARTITION BY episode_sap ORDER BY start_date
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
            PARTITION BY episode_sap ORDER BY start_date
        ) as stay_id
    FROM flagged_starts
),
time_per_unit AS (
    SELECT
        nhc,
        episode_sap,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) as minutes_in_unit
    FROM grouped_stays
    GROUP BY nhc, episode_sap, stay_id, ou_loc_ref
),
predominant_unit AS (
    SELECT
        nhc,
        episode_sap,
        stay_id,
        ou_loc_ref as assigned_unit,
        minutes_in_unit as max_minutes
    FROM (
        SELECT
            t.nhc,
            t.episode_sap,
            t.stay_id,
            t.ou_loc_ref,
            t.minutes_in_unit,
            ROW_NUMBER() OVER (
                PARTITION BY t.nhc, t.episode_sap, t.stay_id
                ORDER BY t.minutes_in_unit DESC, MIN(g.start_date) ASC
            ) as rn
        FROM time_per_unit t
        INNER JOIN grouped_stays g
            ON t.nhc = g.nhc
            AND t.episode_sap = g.episode_sap
            AND t.stay_id = g.stay_id
            AND t.ou_loc_ref = g.ou_loc_ref
        GROUP BY t.nhc, t.episode_sap, t.stay_id,
                 t.ou_loc_ref, t.minutes_in_unit
    ) ranked
    WHERE rn = 1
),
cohort AS (
    SELECT
        g.nhc,
        g.episode_sap,
        g.stay_id,
        p.assigned_unit as ou_loc_ref
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.nhc = p.nhc
        AND g.episode_sap = p.episode_sap
        AND g.stay_id = p.stay_id
    GROUP BY g.nhc, g.episode_sap, g.stay_id, p.assigned_unit
    HAVING YEAR(MIN(g.start_date)) BETWEEN {{min_year}} AND {{max_year}}
       AND p.assigned_unit = '{{unit}}'
)
SELECT COUNT(*) as total_stays FROM cohort c;
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
    """Prompt user for units to analyse (minimum 2 required)."""
    while True:
        print("Units to analyse (e.g. E073,I073 - minimum 2 units): ", end="")
        user_input = input().strip().upper()
        units = [u.strip() for u in user_input.split(",") if u.strip()]

        if len(units) < 2:
            print("❌ Error: You must specify at least 2 units for predominance analysis.")
            print("   Example: E073,I073 or E073,I073,E074\n")
            continue

        # Remove duplicates while preserving order
        seen = set()
        unique_units = []
        for u in units:
            if u not in seen:
                seen.add(u)
                unique_units.append(u)

        if len(unique_units) < len(units):
            print(f"ℹ️  Removed duplicate units. Using: {','.join(unique_units)}\n")

        return unique_units


def process_unit(
    unit: str,
    all_units: list,
    years: list,
    timestamp: str,
    sql_template: str,
    count_sql_template: str,
):
    """Run query for a unit and save CSV."""
    min_year = min(years)
    max_year = max(years)

    query = sql_template.format(
        unit=unit,
        min_year=min_year,
        max_year=max_year
    )

    df = execute_query(query)
    total_included = len(df)

    # Total stays (before prescription filter) to report exclusions
    count_query = count_sql_template.format(
        unit=unit,
        min_year=min_year,
        max_year=max_year
    )
    count_df = execute_query(count_query)
    total_stays = int(count_df["total_stays"].iloc[0]) if not count_df.empty else 0
    excluded_no_prescription = total_stays - total_included

    if df.empty:
        print(f"[{unit}] No data found")
        print(f"        Excluded (no prescription): {excluded_no_prescription} stays")
        return

    # Save CSV
    year_str = f"{min_year}-{max_year}" if len(years) > 1 else str(min_year)
    units_str = "-".join(all_units)
    filename = OUTPUT_DIR / f"admissions_{unit}_from_{units_str}_{year_str}_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    # Summary
    total = total_included
    patients = df['nhc'].nunique()
    deaths = (df['exitus_during_stay'] == 'Yes').sum()
    mortality = (deaths / total * 100) if total > 0 else 0
    transfers = (df['had_transfer'] == 'Yes').sum()
    transfer_pct = (transfers / total * 100) if total > 0 else 0
    still_in = (df['still_admitted'] == 'Yes').sum() if 'still_admitted' in df.columns else 0

    print(f"[{unit}] {total} stays | {patients} patients | {deaths} deaths ({mortality:.1f}%)")
    print(f"        Transfers: {transfers} ({transfer_pct:.1f}%) | Still admitted: {still_in}")
    print(f"        Excluded (no prescription): {excluded_no_prescription} stays")
    print(f"        → {filename.name}")


# ==========================================
# MAIN
# ==========================================
def main():
    print("\n" + "="*70)
    print("  HOSPITALISATION WARD STAYS - PREDOMINANT UNIT (val_ schema)")
    print("="*70)
    print("  Each stay assigned to unit with most hours (prevents duplicates)")
    print("="*70)

    years = get_years_from_user()
    units = get_units_from_user()

    # Build SQL template with dynamic units
    print(f"\nBuilding query for units: {', '.join(units)}...")
    sql_template = build_sql_query(units)
    count_sql_template = build_sql_count_query(units)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Processing {len(units)} unit(s) for years {min(years)}-{max(years)}...\n")

    for unit in units:
        process_unit(unit, units, years, timestamp, sql_template, count_sql_template)

    print(f"\n✓ Output saved to: {OUTPUT_DIR}")
    print(f"✓ No duplicate stays across {', '.join(units)}\n")


if __name__ == "__main__":
    main()
