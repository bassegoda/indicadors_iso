# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clinical quality indicators system for Hospital Clínic de Barcelona. Extracts, analyzes, and exports clinical indicators from a MySQL database (DataNex) as CSV and PDF reports. Each module handles one indicator independently.

## Setup

Requires Python ≥ 3.10 and a `.env` file in the OneDrive root (auto-detected cross-platform):

```
DB_HOST=...
DB_USER=...
DB_PASSWORD=...
DB_DATABASE=...
DB_PORT=3306
```

```bash
pip install -r requirements.txt
```

## Running Scripts

Each module is run directly — no build step:

```bash
python demographics/ward_stays_demo.py        # prompts for year range, outputs CSV + HTML
python demographics/cirrhosis_comparison.py
python admissions/hosp_ward_longest_stay.py   # prompts for years and units
python drg/drg_complexity_report.py           # outputs PDF + CSV
python dynamic_forms/run_queries.py --list
python dynamic_forms/run_queries.py --query <name>
python dynamic_forms/run_queries.py --all
python dictionaries/extract_all_dictionaries.py --all
python dictionaries/extract_all_dictionaries.py --list
```

There are no tests, linters, or build tools configured.

## Architecture

**`connection.py`** (root) — shared database layer. Use `execute_query(sql, params)` which returns a pandas DataFrame. Handles `.env` discovery across Windows/macOS OneDrive paths automatically.

**Module pattern** (demographics is the canonical example):
- `_sql.py` — SQL template (typically a large CTE chain)
- `_metrics.py` — statistical calculations on the resulting DataFrame
- `_report.py` — CSV and HTML/PDF output
- `<main_script>.py` — orchestrates the pipeline, handles interactive prompts

Simpler modules (deliris, necropsy, sepsis3, snisp, nutritions) collapse everything into a single script.

**Output** goes to `<module>/output/` directories, which are gitignored.

## SQL Conventions

SQL queries use extensive CTEs and window functions (`LAG`, `LEAD`, `ROW_NUMBER`). The predominant-unit logic (assign a stay to the unit where the patient spent the most time) is a recurring pattern shared across demographics, admissions, and drg modules.

**`DB_CONTEXT.md`** (root, 86KB) is the authoritative database schema reference. Read it before writing new SQL — it documents all relevant tables, ETL rules, ICD mappings, and how to use the local dictionaries.

**`dictionaries/`** contains 54 CSV files extracted from the database (ICD codes, lab parameters, drugs, DRG codes, SNOMED-CT, enumerations). Use these to look up codes offline before querying the live DB.

## Interactive Prompts

Most scripts prompt for:
- Year range: accepts `2024`, `2023-2025`, or `2023,2024`
- Unit codes: single (e.g. `E073`) or comma-separated (e.g. `E073,I073`)

Defaults are shown in brackets and accepted with Enter.
