# CLAUDE.MD - Project Context for AI Assistants

## Project Overview

**Indicadores ISO** is a clinical indicators analysis system for Hospital Clínic de Barcelona. It extracts and analyzes clinical indicators from a MySQL/MariaDB database (DataNex).

**Primary Language**: Spanish (Catalan context)
**Database**: MySQL/MariaDB (DataNex hospital database)
**Main Purpose**: Generate clinical reports and indicators from hospital data

## Project Structure

```
indicadors_iso/
├── connection.py           # Cross-platform database connection module
├── requirements.txt        # Python dependencies
├── .env                   # (Not in repo) Stored in OneDrive root
├── admissions/            # ICU admission identification strategies
│   ├── lab_admissions.py      # Version using g_* tables (patient_ref, episode_ref)
│   ├── lab_admissions_val.py  # Version using val_* tables (nhc, episode_sap)
│   └── output/               # Generated CSV reports (git-ignored)
├── demographics/          # Demographic cohort analysis
│   ├── demo.py
│   ├── threshold_sensitivity.py
│   └── output/
├── deliris/              # Delirium analysis (CAM-ICU)
│   ├── deliris.py
│   └── output/
├── micro/                # Microbiology and antibiograms
│   ├── get_tables.py
│   ├── micro.sql
│   ├── antibiogram.sql
│   └── output/
├── mortality/            # Monthly mortality analysis
│   ├── deaths_by_month.py
│   ├── deaths_by_month.sql
│   └── output/
├── nutritions/           # Enteral and parenteral nutrition analysis
│   ├── nutritions.py
│   └── output/
├── snisp/                # Incident analysis
│   ├── analysis_2025.py
│   └── output/
└── docs/                 # Database schema documentation
    ├── 00_full_context.md
    ├── dictionaries/     # Reference dictionaries (CSV files)
    └── fragments/        # Detailed documentation fragments
```

**IMPORTANT**: All analysis folders contain an `output/` subfolder for generated results. These folders are git-ignored and must never contain patient-identifying data.

## Database Connection

### Architecture
The `connection.py` module provides centralized database access with these features:
- **Cross-platform support**: Works on Windows and macOS
- **Auto-detection**: Finds OneDrive path automatically
- **Centralized credentials**: `.env` file stored in OneDrive root (syncs across devices)
- **Password rotation**: Easy updates when DB password changes (every 2-5 days)

### Environment Variables
Required in `.env` (stored at OneDrive root):
```env
DB_HOST=your_host
DB_USER=your_username
DB_PASSWORD=your_password
DB_DATABASE=your_database
DB_PORT=3306
```

### Usage Pattern
All scripts import connection like this:
```python
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from connection import execute_query
```

## Database Tables: g_* vs val_*

The database has two parallel table sets:

### g_* Tables (Pseudonymized)
- Use `patient_ref` (INT) as patient identifier
- Use `episode_ref` (INT) as episode identifier
- Examples: `g_movements`, `g_prescriptions`, `g_exitus`, `g_episodes`

### val_* Tables (Validated/Alternative)
- Use `nhc` as patient identifier
- Use `episode_sap` as episode identifier
- Examples: `val_movements`, `val_prescriptions`, `val_exitus`

**When to use which:**
- Most scripts use `g_*` tables (standard)
- Some validation/analysis scripts use `val_*` tables
- Always check which table set a script expects before modifying

## DataNex Database Schema

### Core Tables Hierarchy
```
Episodes (admissions, visits)
  └── Care Levels (ICU, WARD intensity)
      └── Movements (location changes)
```

### Key Tables
- **g_episodes**: Medical events (admissions, emergencies, outpatient visits)
- **g_care_levels**: Healthcare intensity levels
- **g_movements**: Patient location changes (includes discharge and exitus)
- **g_demographics**: Patient demographics
- **g_exitus**: Mortality data (patient_ref, exitus_date)
- **g_labs**: Laboratory results
- **g_diagnostics**: Clinical diagnoses
- **g_prescriptions**: Medication orders
- **g_administrations**: Medication administration records
- **g_micro**: Microbiology cultures and results
- **g_antibiograms**: Antibiotic sensitivity testing

### Key Relationships
- `patient_ref` / `nhc`: Primary patient identifier (links most tables)
- `episode_ref` / `episode_sap`: Links to hospital episodes
- `care_level_ref`: Groups consecutive care levels
- `treatment_ref`: Links prescriptions, administrations, perfusions
- `place_ref`: Room/bed assignment (NULL = no bed assigned)

### Important Fields
- **place_ref**: Encrypted reference for patient's room and bed. NULL means patient has no bed assigned.
- **exitus_date**: Date of death (DATE format, not DATETIME)
- **start_date / end_date**: In movements, if start_date = end_date, it's a discharge or exitus event

## Important Query Rules

1. **Use CTEs**: Prefer Common Table Expressions for optimization and readability
2. **Dictionary lookups**: Use `ref` fields for searches, not `descr` fields
3. **Diagnosis exception**: For diagnoses, search by `diag_descr` in `g_diagnostics` directly (don't link via `diag_ref`)
4. **Laboratory data**: Search using `lab_sap_ref` in `dic_lab` dictionary
5. **Date filtering with overlap**: For annual queries, use overlap filtering:
   ```sql
   WHERE start_date <= '{year}-12-31 23:59:59'
     AND end_date >= '{year}-01-01 00:00:00'
   ```
   This captures stays that cross year boundaries.
6. **Stay identification**: Use window functions (LAG, SUM OVER) to group consecutive movements into stays
7. **Optimization**: Apply optimizations without explaining them

## Admissions Module - ICU Admission Identification

### Overview
The `admissions/` module contains a laboratory for testing different strategies to identify "real" ICU admissions in units E073 and I073.

### Scripts

#### `lab_admissions.py` (g_* tables version)
- Uses `g_movements`, `g_prescriptions`, `g_exitus`
- Fields: `patient_ref`, `episode_ref`
- Units: E073, I073

#### `lab_admissions_val.py` (val_* tables version)
- Uses `val_movements`, `val_prescriptions`, `val_exitus`
- Fields: `nhc`, `episode_sap`
- Units: E073, I073

### Strategies

1. **baseline**: No additional filters (only unit and date)
2. **place_ref**: Requires bed assignment (`place_ref IS NOT NULL`)
3. **place_prescriptions**: Requires bed assignment + medication prescription during stay

### Features

- **Stay grouping**: Uses window functions to group consecutive movements into stays
- **Year overlap filtering**: Captures stays that cross year boundaries
- **Diagnostic tools**:
  - Option 4: Identify admissions with bed but NO prescriptions (suspicious cases)
  - Option 5: Analyze short stays (<24h) with bed + prescription
  - Option 6: Report on stays that cross year boundaries

### Output Files (in `admissions/output/`)
- `summary_strategies.csv` / `summary_strategies_val.csv`: Annual comparison by strategy
- `no_prescriptions_{year}.csv`: Cases with bed but no prescriptions
- `short_stays_{max_hours}h_{year}.csv`: Short stays analysis
- `year_overlap_{year}.csv`: Stays crossing year boundaries

**IMPORTANT**: All output CSVs have patient-identifying columns (`patient_ref`, `episode_ref`, `nhc`, `episode_sap`) removed before saving.

## Output Management & Security

### Output Folder Structure
- **Every analysis folder** must have an `output/` subfolder
- All generated files (CSV, PNG, etc.) go in `output/`
- `output/` folders are git-ignored (see `.gitignore`)

### Data Privacy Rules

**CRITICAL**: Never save patient-identifying data in output files.

**Identifying fields to remove:**
- `patient_ref` (g_* tables)
- `episode_ref` (g_* tables)
- `nhc` (val_* tables)
- `episode_sap` (val_* tables)

**Before saving any DataFrame to CSV:**
```python
# Remove identifying columns
df_safe = df.drop(columns=['patient_ref', 'episode_ref', 'nhc', 'episode_sap'], errors='ignore')
df_safe.to_csv(output_path, index=False)
```

**Allowed in outputs:**
- Aggregated statistics (counts, means, medians)
- Dates (without patient linkage)
- Unit codes (E073, I073)
- Clinical indicators (without patient linkage)
- Visualizations (charts, graphs)

## Development Workflow

### Running Scripts
Scripts are executed independently from their folders:
```bash
python admissions/lab_admissions.py
python demographics/demo.py
python deliris/deliris.py
python nutritions/nutritions.py
```

Scripts typically:
1. Request interactive parameters (year, units, etc.)
2. Execute SQL queries via `execute_query()`
3. Generate output files in `output/` subfolder
4. Remove identifying data before saving

### Output Format
- Results saved in respective `output/` folders
- Common formats: CSV, PNG (for charts), HTML reports
- All outputs are git-ignored

## Key Features

### 1. Cross-Platform Database Access
The `find_onedrive_path()` function detects OneDrive on:
- **Windows**: Via environment variables or user profile paths
- **macOS**: Via Library/CloudStorage or home directory

### 2. Password Rotation Support
When DB password changes:
1. Update only `DB_PASSWORD=` line in `.env`
2. OneDrive syncs to all devices automatically
3. No code changes needed

### 3. Module Analysis Types
- **admissions**: ICU admission identification strategies (E073, I073)
- **demographics**: Patient cohort demographics
- **deliris**: CAM-ICU delirium scoring
- **micro**: Antibiogram and microbiology data
- **mortality**: Death records by month
- **nutritions**: Nutritional support analysis
- **snisp**: Clinical incident tracking

## Documentation Reference

For detailed schema information, see:
- `docs/00_full_context.md`: Complete database schema reference
- `docs/fragments/`: Detailed documentation by topic
  - `00_instructions.md`: LLM query generation rules
  - `01_episodes_movements.md`: Episodes, care levels, movements
  - `02_demographics.md`: Patient demographics
  - `03_diagnoses.md`: Clinical diagnoses
  - `04_labs_clinical.md`: Laboratory and clinical records
  - `05_microbiology.md`: Microbiology data
  - `06_medications.md`: Prescriptions and administrations
  - `10_dictionaries.md`: Reference dictionaries
- `docs/dictionaries/`: CSV dictionary files (dic_lab.csv, dic_ou_loc.csv, etc.)

## Dependencies

Install with: `pip install -r requirements.txt`

Key dependencies:
- `mysql-connector-python`: Database connectivity
- `pandas`: Data manipulation and analysis
- `python-dotenv`: Environment variable management
- `matplotlib`: Chart generation (for some modules)
- Additional analysis libraries as needed

## Security Notes

- `.env` file is **NOT** in repository (stored in OneDrive)
- Credentials synced via OneDrive across authorized devices only
- Database password rotates frequently (every 2-5 days)
- **All output files must exclude patient-identifying data**
- `output/` folders are git-ignored to prevent accidental commits

## Git Repository

- **Current branch**: main
- **Remote**: GitHub repository
- **Ignored**: All `output/` folders, `.env`, `__pycache__/`, `.vscode/`

## Common Tasks

### Adding a New Indicator Analysis
1. Create new folder in project root
2. Add Python script using connection pattern
3. Create `output/` subfolder for results
4. Import `execute_query` from `connection.py`
5. **Always remove identifying columns before saving CSVs**

### Updating Database Credentials
1. Locate `.env` in OneDrive root
2. Update `DB_PASSWORD=new_password`
3. Save (OneDrive syncs automatically)

### Writing SQL Queries
1. Review schema docs in `docs/` folder
2. Use CTEs for complex queries
3. Reference dictionary tables for lookups
4. Use year overlap filtering for annual queries
5. Test with `execute_query()` function

### Creating Output Files
1. Create `output/` folder in your module directory
2. Remove identifying columns: `df.drop(columns=['patient_ref', 'episode_ref', 'nhc', 'episode_sap'], errors='ignore')`
3. Save to `output/` subfolder
4. Verify file is not tracked by git

## ICU Admission Analysis Workflow

### Understanding Stay Identification
- **Movements** are grouped into **stays** using window functions
- Consecutive movements with `end_date = next_start_date` are part of the same stay
- Each stay is assigned to the **first unit** where the patient entered
- A patient can have multiple stays in the same year (multiple admissions)

### Year Overlap Handling
- Use overlap filtering to capture stays crossing year boundaries
- Example: Patient admitted Dec 28, 2023, discharged Jan 5, 2024
  - Old method (start_date filter): Would miss this stay in 2024 analysis
  - New method (overlap filter): Captures it in 2024 analysis

### Strategy Selection
- **baseline**: Too permissive (includes movements without beds)
- **place_ref**: Good balance (requires bed assignment)
- **place_prescriptions**: Most restrictive (requires bed + medication)

## Contact & Support

For questions about:
- Database schema: See `docs/00_full_context.md`
- Query generation: See `docs/fragments/00_instructions.md`
- Connection issues: Check `.env` file in OneDrive root
- Admissions strategies: See `admissions/lab_admissions.py` docstrings
