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
├── demographics/          # Demographic cohort analysis
├── deliris/              # Delirium analysis (CAM-ICU)
├── micro/                # Microbiology and antibiograms
├── mortality/            # Monthly mortality analysis
├── nutritions/           # Enteral and parenteral nutrition analysis
├── snisp/                # Incident analysis
└── docs/                 # Database schema documentation
    ├── 00_full_context.md
    ├── 01_instructions.md
    ├── 02_core_tables.md
    ├── 03_clinical_tables.md
    ├── 04_dictionaries.md
    └── 05_query_examples.md
```

Each analysis folder contains:
- Python scripts for specific indicators
- `output/` subfolder for generated results

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
- **g_movements**: Patient location changes
- **g_patient_ident**: Patient demographics
- **g_death_records**: Mortality data
- **g_labs**: Laboratory results
- **g_diagnostics**: Clinical diagnoses
- **g_prescriptions**: Medication orders
- **g_administrations**: Medication administration records
- **g_microbiology**: Microbiology cultures and results

### Key Relationships
- `patient_ref`: Primary patient identifier (links most tables)
- `episode_ref`: Links to hospital episodes
- `care_level_ref`: Groups consecutive care levels
- `treatment_ref`: Links prescriptions, administrations, perfusions

## Important Query Rules

1. **Use CTEs**: Prefer Common Table Expressions for optimization
2. **Dictionary lookups**: Use `ref` fields for searches, not `descr` fields
3. **Diagnosis exception**: For diagnoses, search by `diag_descr` in `g_diagnostics` directly (don't link via `diag_ref`)
4. **Laboratory data**: Search using `lab_sap_ref` in `dic_lab` dictionary
5. **Optimization**: Apply optimizations without explaining them

## Development Workflow

### Running Scripts
Scripts are executed independently from their folders:
```bash
python demographics/demo.py
python deliris/deliris.py
python nutritions/nutritions.py
```

Scripts typically:
1. Request interactive parameters (year, units, etc.)
2. Execute SQL queries via `execute_query()`
3. Generate output files in `output/` subfolder

### Output Format
- Results saved in respective `output/` folders
- Common formats: CSV, Excel, reports

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
- **demographics**: Patient cohort demographics
- **deliris**: CAM-ICU delirium scoring
- **micro**: Antibiogram and microbiology data
- **mortality**: Death records by month
- **nutritions**: Nutritional support analysis
- **snisp**: Clinical incident tracking

## Documentation Reference

For detailed schema information, see:
- `docs/01_instructions.md`: LLM query generation rules
- `docs/02_core_tables.md`: Episodes, care levels, movements
- `docs/03_clinical_tables.md`: Labs, diagnostics, prescriptions, microbiology
- `docs/04_dictionaries.md`: Reference dictionaries
- `docs/05_query_examples.md`: SQL query examples with CTEs

## Dependencies

Install with: `pip install -r requirements.txt`

Key dependencies:
- `mysql-connector-python`: Database connectivity
- `pandas`: Data manipulation
- `python-dotenv`: Environment variable management
- Additional analysis libraries as needed

## Security Notes

- `.env` file is **NOT** in repository (stored in OneDrive)
- Credentials synced via OneDrive across authorized devices only
- Database password rotates frequently (every 2-5 days)

## Git Repository

- **Current branch**: main
- **Remote**: GitHub repository
- **Status**: Clean working directory (as of conversation start)

## Common Tasks

### Adding a New Indicator Analysis
1. Create new folder in project root
2. Add Python script using connection pattern
3. Create `output/` subfolder for results
4. Import `execute_query` from `connection.py`

### Updating Database Credentials
1. Locate `.env` in OneDrive root
2. Update `DB_PASSWORD=new_password`
3. Save (OneDrive syncs automatically)

### Writing SQL Queries
1. Review schema docs in `docs/` folder
2. Use CTEs for complex queries
3. Reference dictionary tables for lookups
4. Test with `execute_query()` function

## Contact & Support

For questions about:
- Database schema: See `docs/` folder
- Query generation: See `docs/01_instructions.md`
- Connection issues: Check `.env` file in OneDrive root
