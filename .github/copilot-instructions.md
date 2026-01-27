# Copilot Instructions for Indicadores ISO

## Project Overview

Clinical indicators analysis system for Hospital Clínic de Barcelona. Extracts and analyzes indicators from DataNex (MySQL hospital database). All scripts are **standalone Python files** that query the database, process data, and generate reports in local `output/` folders.

**Primary Language**: Spanish (with Catalan context)  
**Database**: MySQL/MariaDB (DataNex)  
**Key Constraint**: Database passwords rotate every 2-5 days

## Critical Architecture Patterns

### Database Connection
All scripts use **centralized connection module** at project root:

```python
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from connection import execute_query
```

- **Never** use `mysql.connector` directly in analysis scripts
- Connection credentials live in `.env` at **OneDrive root** (auto-detected cross-platform)
- Use `execute_query(sql_string)` which returns pandas DataFrame
- All required env vars: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE`, `DB_PORT`

### DataNex Schema: g_* vs val_* Tables

The database has **two parallel table sets**:
- **g_* tables**: Use `patient_ref` (INT) and `episode_ref` (INT) — **ALWAYS USE BY DEFAULT**
- **val_* tables**: Use `nhc` and `episode_sap` — **only when explicitly requested by user**

**Always use g_* tables** unless user specifically asks for val_* tables.

### Core Table Hierarchy
DataNex follows: **episodes → care_levels → movements**

- `g_episodes`: Medical events (admission, emergency, outpatient)
- `g_care_levels`: Healthcare intensity within episode (ICU, WARD, etc.)
- `g_movements`: Patient location changes (transfers, discharge, death)

Only **EM**, **HAH**, and **HOSP** episode types have care_levels and movements.

## SQL Query Patterns

### ICU Stay Identification (Standard Pattern)
Most scripts identify ICU stays using this **window function approach**:

```sql
WITH raw_moves AS (
    SELECT patient_ref, episode_ref, ou_loc_ref, start_date, end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})  -- Prompt user for units (e.g., 'E073', 'I073')
      AND start_date BETWEEN '{year}-01-01' AND '{year}-12-31 23:59:59'
      AND place_ref IS NOT NULL  -- Has assigned bed
),
flagged_starts AS (
    SELECT *,
        CASE WHEN LAG(end_date) OVER (PARTITION BY episode_ref ORDER BY start_date) = start_date
        THEN 0 ELSE 1 END AS is_new_stay
    FROM raw_moves
),
grouped_stays AS (
    SELECT *, SUM(is_new_stay) OVER (PARTITION BY episode_ref ORDER BY start_date) as stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT patient_ref, episode_ref, stay_id,
        MIN(start_date) as true_start_date,
        MAX(end_date) as true_end_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
    HAVING TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) >= 10  -- Adjustable threshold
)
```

**Key technique**: LAG window function detects consecutive movements, `stay_id` groups them into stays.
**User inputs**: Always prompt for unit codes (ou_loc_ref) and adjust duration threshold per analysis needs.

### Diagnosis/Procedure Code Searches
- Use `code` field with ICD-9/ICD-10 patterns: `code LIKE 'K70.3%'`
- For other ref fields, search by `*_ref` not `*_descr` when possible
- **Exception**: Diagnoses and procedures always use `code` field with general ICD knowledge

## Project Structure Conventions

```
indicadors_iso/
├── connection.py          # NEVER modify without checking all scripts
├── requirements.txt       # pandas, mysql-connector-python, matplotlib, python-dotenv
├── admissions/            # ICU admission strategies
│   ├── lab_admissions.py      # Uses g_* tables
│   ├── lab_admissions_val.py  # Uses val_* tables
│   └── output/               # Git-ignored, NEVER commit patient data
├── demographics/          # Cohort demographic analysis
├── deliris/              # Delirium (CAM-ICU) analysis
├── micro/                # Microbiology and antibiograms
├── mortality/            # Monthly death analysis
├── nutritions/           # Enteral/parenteral nutrition
├── snisp/                # Incident analysis
└── docs/
    ├── 00_full_context.md     # Complete DataNex schema for SQL generation
    ├── dictionaries/          # Reference CSV dictionaries extracted from DB
    └── fragments/            # Modular schema documentation
```

### Output Folder Rules
- Every analysis folder has `output/` subfolder
- **All output folders are git-ignored**
- Never include patient-identifying data in outputs committed to repo
- Typical outputs: CSV reports, HTML tables, matplotlib charts

## Script Execution Pattern

All scripts are **interactive and standalone**:
1. User runs `python demographics/demo.py` from project root
2. Script **prompts for parameters**: year, organizational units (ou_loc_ref), duration thresholds, etc.
3. Script executes SQL via `execute_query()`
4. Results saved to `./output/` in script's folder
5. Execution time logged: "Query executada correctament en X.XX segons"

**No CLI frameworks** — use `input()` to ask user for analysis parameters. Never hardcode units or thresholds.

## Development Workflows

### Testing Database Connection
```python
from connection import execute_query
df = execute_query("SELECT COUNT(*) as total FROM g_episodes")
print(df)
```

### Generating Data Dictionaries
See [docs/dictionaries/generate_provisions_dict.py](docs/dictionaries/generate_provisions_dict.py) for pattern:
- Extract `DISTINCT ref, descr` from table
- Save as CSV in `docs/dictionaries/`
- Used for reference when writing queries

### When Password Changes
User only updates `DB_PASSWORD` in OneDrive `.env` — no code changes needed.

## Dependencies

**Required packages** (see [requirements.txt](requirements.txt)):
- `pandas` — data manipulation
- `mysql-connector-python` — database connection
- `matplotlib`, `seaborn` — visualization
- `python-dotenv` — environment variable management
- `tableone` — demographic table generation (used in demographics/)

## Common Pitfalls

1. **Don't import mysql.connector in analysis scripts** — use `connection.execute_query()`
2. **Always use g_* tables by default** — only use val_* when user explicitly requests them
3. **Prompt for units** — ask user which ou_loc_ref to analyze (common: E073, I073 for ICU)
4. **Duration thresholds are flexible** — 10 hours is common but adjust per analysis needs
5. **Date ranges** — always specify datetime fully: `'YYYY-MM-DD HH:MM:SS'`
6. **Window functions** — LAG/LEAD partition by `episode_ref`, order by `start_date`

## Documentation Reference

- [docs/00_full_context.md](docs/00_full_context.md): Complete schema reference for SQL generation
- [docs/fragments/](docs/fragments/): Modular schema documentation by topic
- [CLAUDE.MD](CLAUDE.MD): Extended project context (contains more detailed table explanations)
