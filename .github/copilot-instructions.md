# Copilot Instructions: Indicadores ISO

## Project Overview

**indicadores_iso** is a hospital analytics system that extracts clinical indicators from a MySQL database (Hospital Clínic de Barcelona DataNex). Each subdirectory analyzes specific clinical metrics: demographics, delirium (CAM-ICU), microbiology, mortality, admissions, etc.

### Key Architectural Pattern

- **Modular analysis structure**: Each indicator lives in its own folder with output isolation
- **Centralized database connection**: All scripts use the shared `connection.py` module
- **SQL-first approach**: Complex queries are written as templates with parameterization
- **Interactive workflows**: Scripts request parameters at runtime (year, units, etc.)

## Critical Setup Requirements

### Database Connection Flow

1. Credentials stored in **OneDrive root** (`.env` file)
   - Path detection is cross-platform (Windows & macOS)
   - See `connection.py` for `find_onedrive_path()` and `get_env_path()`
2. All scripts import: `from connection import execute_query`
3. `.env` variables: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE`, `DB_PORT`

**Import Pattern** (all scripts follow this):
```python
from pathlib import Path
import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
from connection import execute_query
```

## Database Schema Knowledge

**CRITICAL**: Read `DB_CONTEXT.md` before writing any SQL queries.

### Key Tables & Relationships
- **g_episodes**: Admission/event records (FK: patient_ref, episode_ref)
- **g_care_levels**: Intensity levels within episodes (ICU, WARD, HAH, etc.)
- **g_movements**: Location changes within care levels (includes discharge/exitus)
- **g_demographics**, **g_exitus**, **g_labs**, **g_rc**, **g_diagnostics**: Supporting clinical data

### Query Patterns to Know

**Cohort Definition Pattern** (used in `demographics/demo.py`, `deliris/deliris.py`):
- Starts with `g_movements` filtered by `ou_loc_ref` (unit) and date range
- Uses window functions to detect "new stays" (consecutive movement grouping)
- Groups by `stay_id` to aggregate multi-location stays
- Applies minimum duration filters (e.g., >= 10 hours)

**Template Variables**:
- `{units_formatted}`: SQL IN clause (e.g., `'E073', 'I073'`)
- `{year}`: Year integer for date filtering
- Units: E073 (one ICU), I073 (another ICU), other departments

### Data Privacy

- Remove `patient_ref`, `episode_ref` before exporting results (see `micro/get_tables.py`)
- Outputs should contain no patient identifiers

## Common Development Patterns

### File Organization
```
script_name/
  ├── script_name.py (main logic with embedded or template SQL)
  ├── validation.py (optional testing variant)
  └── output/ (generated CSVs/HTMLs)
```

### SQL Query Organization
- Templates stored as multiline strings with placeholders
- Parameters formatted before execution
- Large complex queries use CTEs (common table expressions) for clarity

### Data Processing Workflow
1. Execute query → pandas DataFrame
2. Apply calculations/transformations in pandas
3. Generate outputs: CSV, HTML tables (TableOne), plots (matplotlib/seaborn)
4. Save to `output/` subfolder with timestamp naming

**Example Output Pattern**: `icu_admissions_2022-2024_E073_I073_20260128_170717.csv`

## Project-Specific Conventions

### Naming Conventions
- `ou_loc_ref`: Physical hospitalization unit (E073, I073, etc.)
- `ou_med_ref`: Medical organizational unit
- `stay_id`: Grouping key for consecutive movements in same episode
- `care_level_ref`: Uniquely identifies a care intensity level

### Common Parameters
- **YEARS**: `[2023, 2024, 2025]` (typical analysis window)
- **UNITS**: `["E073", "I073"]` (ICU units in most analyses)
- **MIN_DURATION**: 10 hours (minimum admission length for cohort inclusion)

### Visualization Patterns
- Use `matplotlib` + `seaborn` for figures
- Export as PNG/PDF
- `TableOne` for demographic tables (HTML output)

## SQL Debugging Tips

1. Test queries incrementally—start with raw movements, then add CTEs
2. Use `TIMESTAMPDIFF(HOUR, ...)` to verify duration calculations
3. Check `place_ref IS NOT NULL` to identify "real" admissions (bed assignment)
4. Verify temporal overlaps don't create duplicate stays using window functions
5. Always filter by specific `ou_loc_ref` values—don't query all units blindly

## Before Writing Code

- ✅ Read the relevant section in `DB_CONTEXT.md`
- ✅ Check existing scripts in the same domain for patterns (e.g., review `demographics/demo.py` before writing delirium analysis)
- ✅ Test SQL templates locally using interactive execution (not in production)
- ✅ Verify cohort definitions match hospital standards (discuss with analysts)
