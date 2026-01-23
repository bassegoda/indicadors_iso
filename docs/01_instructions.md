# DataNex Database - LLM Instructions

**Purpose**: SQL query generation from natural language for Hospital Clinic database (MySQL MariaDB)

## Process

1. Confirm you understand the DataNex schema
2. Request the natural language question
3. Use 'descr' fields in dictionaries to find corresponding 'ref' codes
4. Generate optimized SQL query using CTEs when appropriate
5. Present the final query ready for copy-paste

## Rules

- Always explain how the query works before showing it
- Search using 'ref' fields, not 'descr'
- **Exception for diagnoses**: Do NOT use `diag_ref` to link `dic_diagnostic` with `g_diagnostics`. The `diag_ref` fields in these tables are independent systems. Search directly by `diag_descr` in `g_diagnostics` table.
- Use Common Table Expressions (CTEs) for optimization
- Do not explain optimizations, just do them
- For laboratory data, search in dic_lab dictionary using `lab_sap_ref`

## Database Overview

DataNex consists of several tables. The central tables are **g_episodes**, **g_care_levels** and **g_movements**:

- **Episodes**: Medical events experienced by a patient (admission, emergency assessment, outpatient visits, etc.)
- **Care levels**: Intensity of healthcare needs (ICU, WARD, etc.)
- **Movements**: Changes in patient's location

Hierarchy: **episodes → care_levels → movements**

## Key Relationships

- `patient_ref`: Links most tables (primary patient identifier)
- `episode_ref`: Links to hospital episodes
- `care_level_ref`: Groups consecutive care levels (ICU, WARD, etc.)
- `treatment_ref`: Links g_prescriptions, g_administrations, g_perfusions

## Documentation Files

- `02_core_tables.md`: Episodes, care levels, movements, demographics, death records
- `03_clinical_tables.md`: Labs, diagnostics, prescriptions, microbiology, procedures, surgery
- `04_dictionaries.md`: Reference dictionaries (diagnoses, labs, locations, clinical records)
- `05_query_examples.md`: SQL query examples with CTEs
