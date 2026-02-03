# CLAUDE.MD - AI Assistant Context

This file provides context for AI assistants (Claude, Copilot, etc.) working with this codebase.

---

## Project Overview

**ELE/DILI Analysis Pipeline** - A clinical research tool for analyzing Elevated Liver Enzymes (ELE) and Drug-Induced Liver Injury (DILI) in hospitalized patients at Hospital Clínic Barcelona.

### Key Objectives
- Automatically identify cases with elevated liver enzymes (ELE) using laboratory criteria
- Compare clinical outcomes between ELE and non-ELE patients
- Validate analytical findings against ICD-10 coded diagnoses (confirmed DILI = K71.x)
- Generate comprehensive reports with survival analysis

### Terminology: ELE vs DILI
- **ELE (Elevated Liver Enzymes)**: Cases detected by laboratory criteria, before diagnostic validation
- **DILI (Drug-Induced Liver Injury)**: Confirmed cases with ICD-10 code K71.x (toxic liver disease)

---

## Core Concepts

### ELE Classification Criteria

Episodes are classified based on **24-hour windows** of laboratory values from **24h before admission** through hospital discharge:

**ELE Criteria** (at least one must be met):
- **(A)** ALT ≥ 200 U/L
- **(B)** Alkaline phosphatase ≥ 232 U/L
- **(C)** ALT ≥ 120 U/L **AND** Total bilirubin > 2.4 mg/dL

**NO-ELE Criteria** (all must be met):
- All ALT < 100 U/L
- All alkaline phosphatase < 150 U/L
- All total bilirubin < 1.5 mg/dL (if measured)

**ELE Timing Classification:**
- **Community-acquired**: Criteria met in first 24h of admission (includes pre-admission labs)
- **Nosocomial**: Criteria met >24h after admission with normal baseline labs
- **Uncertain timing**: Criteria met >24h but no baseline labs available

### Important Notes
- **Temporal window**: Labs from 24h BEFORE admission through discharge (expanded in 2026-01)
- Values are evaluated within each 24h window (not necessarily same blood draw)
- Episodes not meeting ELE or NO-ELE criteria are classified as "indeterminate" and excluded
- The classification algorithm is in `src/dili/classification.py`

---

## Codebase Structure

```
dili/
├── src/dili/                    # Main Python package
│   ├── config.py                # Constants, thresholds, paths
│   ├── db.py                    # MySQL database connection
│   ├── etl.py                   # Data loading and transformation
│   ├── classification.py        # DILI/NO DILI classification logic
│   ├── analysis.py              # Outcomes calculation, survival analysis
│   ├── visualization.py         # Figure generation (Kaplan-Meier, etc.)
│   ├── diagnostics.py           # ICD-10 diagnosis classification
│   └── report.py                # HTML report generation
├── sql/                         # SQL queries for data extraction
│   ├── base_cohort.sql          # Patient cohort selection
│   ├── labs.sql                 # Laboratory determinations
│   └── diagnostics.sql          # ICD-10 coded diagnoses
├── data/                        # Raw data (not versioned)
├── output/                      # Results (not versioned)
├── run_pipeline.py              # Main entry point
├── pyproject.toml               # Package configuration
├── README.md                    # User documentation (Spanish)
└── CLAUDE.MD                    # This file
```

---

## Key Modules

### `config.py`
- Contains all thresholds and constants (ELE_*, NO_ELE_*)
- Defines file paths for data and output
- **Important**: When modifying thresholds, update both code and README.md
- **Note**: Uses ELE terminology for lab criteria, DILI reserved for K71.x codes

### `classification.py`
- **Core algorithm**: `get_ele_episodes()` (formerly classify_dili_episodes)
- Evaluates 24-hour windows of lab values internally
- Returns classification and timing for each episode
- **Critical**: Changes here require validation against known cases

### `etl.py`
- Handles data loading from CSV or database
- Pivots lab results into wide format
- **Important**: Duplicates are handled by taking first occurrence

### `analysis.py`
- Calculates outcomes: length of stay, mortality, ICU admission
- Performs survival analysis using lifelines
- Generates comparison statistics

### `visualization.py`
- Creates all figures for the report
- Kaplan-Meier curves, cohort flow diagrams, box plots
- **Style**: Uses consistent color scheme defined in config

### `diagnostics.py`
- Maps ICD-10 codes to clinical categories
- Creates validation groups combining ELE (labs) + diagnoses
- **Important**: ICD-10 mappings are in `DIAGNOSTIC_CATEGORIES` dict
- **Note**: DILI_CODES contains K71.x codes for confirmed DILI (exported as ELE_CODES for API compatibility)
- **Key functions**:
  - `enrich_diagnoses_with_categories()`: Classifies each diagnosis
  - `create_dili_diagnostic_groups()`: Classifies ELE episodes into 4 groups:
    - **confirmado**: ELE + K71.x code (confirmed DILI)
    - **alternativo**: ELE + plausible alternative diagnosis
    - **posible**: ELE without alternative diagnosis (possible unrecognized DILI)
    - **indeterminado**: ELE + nonspecific liver diagnoses
  - `assess_diagnosis_plausibility()`: Evaluates plausibility of alternative diagnoses

### `report.py`
- Generates comprehensive HTML report
- Combines results, figures, and statistical tables
- Output: `output/informe_dili.html`
- **Key functions for diagnostic groups** (optional section if data available):
  - `_create_diagnostic_groups_km()`: KM curves by diagnostic group
  - `_calculate_diagnostic_group_mortality()`: Mortality stats by group
  - `_generate_diagnostic_groups_section()`: HTML section with table and chart

---

## Data Flow

```
Database (MySQL)           CSV Files (data/)
      ↓                          ↓
      └─────────→ ETL (etl.py) ←┘
                       ↓
        Classification (classification.py)
                       ↓
          Analysis + Diagnostics (analysis.py, diagnostics.py)
                       ↓
        Visualization (visualization.py)
                       ↓
          Report Generation (report.py)
                       ↓
              Output Files (output/)
```

---

## Important Conventions

### Code Style
- Python 3.10+ (uses modern type hints)
- Line length: 100 characters
- Use ruff for linting (`ruff check src/`)
- Type hints preferred but not strictly required

### Naming Conventions
- **Functions**: snake_case (`classify_dili_episodes`)
- **Variables**: snake_case (`lab_values`, `dili_episodes`)
- **Constants**: UPPER_SNAKE_CASE (`DILI_THRESHOLDS`)
- **Classes**: PascalCase (minimal use in this project)

### DataFrame Conventions
- Episode ID: `episode_ref` (string)
- Patient ID: `patient_ref` (string)
- Date columns: datetime64[ns] type
- Lab values: float64 (NaN for missing)
- **Key columns**: Always preserve `episode_ref`, `ele_group`, `ele_timing`

### Testing
- Test files in `tests/` (not yet implemented)
- Use pytest: `pytest tests/`
- Coverage goal: >80% for core modules

---

## Common Operations

### Running the Pipeline

```bash
# Complete pipeline with existing CSV data
python run_pipeline.py

# Load fresh data from database
python run_pipeline.py --from-db

# Custom date range
python run_pipeline.py --from-db --start 2023-01-01 --end 2023-12-31

# Generate HTML report
python run_pipeline.py --report

# Include diagnostics extraction and classification
python run_pipeline.py --diagnostics

# Extract diagnostics only (from database, without running DILI pipeline)
python run_pipeline.py --diagnostics-only --from-db

# Run diagnostic group analysis (requires prior data)
python run_pipeline.py --diagnostics-analysis

# Only regenerate figures
python run_pipeline.py --figures-only

# Skip figure generation
python run_pipeline.py --no-figures
```

### Modifying Thresholds

1. Edit values in `src/dili/config.py`
2. Update documentation in `README.md` (Spanish)
3. Rerun classification: `python run_pipeline.py`
4. Validate results against known cases

### Adding New Lab Parameters

1. Update SQL query in `sql/labs.sql`
2. Add column handling in `etl.py`
3. Update thresholds in `config.py` if needed
4. Update classification logic in `classification.py`
5. Update README.md documentation

### Adding New Diagnostic Categories

1. Add ICD-10 codes to `DIAGNOSTIC_CATEGORIES` in `diagnostics.py`
2. Update plausibility logic in `assess_diagnosis_plausibility()` if needed
3. Update `create_dili_diagnostic_groups()` if classification logic changes
4. Update README.md documentation

### Running Diagnostic Analysis

```bash
# Step 1: Extract diagnostics from database
python run_pipeline.py --diagnostics-only --from-db

# Step 2: Run diagnostic group classification
python run_pipeline.py --diagnostics-analysis

# Output files:
#   - output/diagnostics_enriched.csv (all diagnoses with categories)
#   - output/ele_diagnostic_groups.csv (ELE episodes classified in 4 groups)
#   - output/ele_diagnostic_summary.txt (summary statistics)
```

---

## Database Connection

- Credentials stored in `~/OneDrive/MedInfo/.env`
- Format: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Connection handled by `db.py:get_connection()`
- **Never commit credentials** to version control

---

## Common Pitfalls

### Episode Independence
⚠️ **Current limitation**: Episodes from the same patient are treated as independent. This may violate statistical assumptions. See README.md section "Limitaciones metodológicas" for details.

### Missing Data
- Not all episodes have complete lab data
- Missing values are handled as NaN
- Classification requires minimum data: at least one ALT and one alkaline phosphatase

### Timing Windows
- 24-hour windows use hospital admission time as reference
- Windows may span calendar days
- Same blood draw can contribute to multiple windows if values are relevant

### Diagnosis Coding
- Only ~3% of analytical ELE cases have ICD-10 code K71.x (confirmed DILI)
- This is expected due to underreporting, not a bug
- Validation groups help identify diagnostic patterns

### Laboratory Temporal Window
- **As of 2026-01**: Labs extracted from 24h BEFORE admission through discharge
- This allows detection of community-acquired elevated enzymes present before hospitalization
- **Important**: JOIN by `patient_ref` + temporal window (NOT `episode_ref`)
  - Labs from ANY episode (ambulatory, emergency) within the window are included
  - Assigned to the hospitalization episode being analyzed
- SQL uses pre-filtering for optimization on the massive `g_labs` table

---

## Output Files

### Main Outputs

| File | Description | Format |
|------|-------------|--------|
| `output/informe_dili.html` | Comprehensive visual report | HTML |
| `output/comparison_ele_nosocomial.csv` | Episode-level data for stats | CSV |
| `output/pipeline_summary.txt` | Text summary of key statistics | TXT |
| `output/ele_episodes.csv` | List of ELE episodes with timing | CSV |

### Diagnostic Outputs (optional)

| File | Description |
|------|-------------|
| `output/diagnostics_enriched.csv` | All diagnoses with ICD-10 categories and `is_dili` flag |
| `output/diagnostics_summary_by_episode.csv` | Summary of diagnoses per episode |
| `output/ele_diagnostic_groups.csv` | ELE episodes classified into 4 diagnostic groups |
| `output/ele_diagnostic_summary.txt` | Summary statistics of diagnostic groups |

---

## When Making Changes

### Before Modifying Core Logic
1. Understand the clinical context (see README.md)
2. Check if there are existing test cases
3. Consider impact on statistical analysis
4. Document changes in commit messages

### After Making Changes
1. Run the full pipeline: `python run_pipeline.py --from-db`
2. Check output files for unexpected changes
3. Review HTML report for anomalies
4. Update documentation if needed

### For Bug Fixes
1. Document the bug in detail
2. Create a minimal reproduction case if possible
3. Fix the bug
4. Add test to prevent regression
5. Update README.md if it affects user-facing behavior

---

## Questions to Ask

When working on this codebase, consider:

- Does this change affect episode classification?
- Should thresholds be configurable or hard-coded?
- Does this impact statistical independence assumptions?
- Should this be documented in README.md?
- Are there clinical implications I should verify?

---

## Language Note

- **Code**: English (variables, functions, comments)
- **Documentation**: Spanish (README.md for end users)
- **This file**: English (for AI assistants)
- **Git commits**: English preferred

---

## Clinical Context

This is a **retrospective observational study** analyzing real patient data. Key considerations:

- Data quality varies (missing values, timing uncertainties)
- Clinical definitions may not perfectly match analytical criteria
- Results inform but do not replace clinical judgment
- Privacy: All data must be de-identified in outputs

---

## Getting Help

- **Clinical questions**: Consult with medical team
- **Technical questions**: Check README.md, DB_CONTEXT.md
- **Database schema**: See DB_CONTEXT.md
- **SQL queries**: All in `sql/` directory

---

## Version Information

- **Python**: >=3.10
- **Key dependencies**: pandas >=2.0, lifelines >=0.27, matplotlib >=3.7
- **Database**: MySQL 8.0+
- **Status**: Beta (v1.0.0)

---

*Last updated: 2026-02-01*
*Diagnostic groups analysis added: 2026-01-31*
