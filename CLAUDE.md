# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clinical quality indicators system for Hospital Clínic de Barcelona. Extracts, analyzes, and exports clinical indicators from a Metabase API (connected to DataNex on AVS) as CSV and PDF reports. Each module handles one indicator independently.

## Setup

Requires Python ≥ 3.10 and a `.env` file in the OneDrive root (auto-detected cross-platform):

```
METABASE_URL=https://metabase.clinic.cat
METABASE_EMAIL=...
METABASE_PASSWORD=...
METABASE_DATABASE_NAME=...
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
python data_quality/completeness_2024_vs_2025.py  # prompts for (y1,y2) + YTD cutoff; ETL completeness report
```

There are no tests, linters, or build tools configured.

## Architecture

**`connection.py`** (root) — shared database layer via Metabase API. Use `execute_query(query, verbose=True)` which returns a pandas DataFrame. Handles `.env` discovery across Windows/macOS OneDrive paths automatically. Authenticates against Metabase, resolves the database by name, and executes native SQL queries.

**Module pattern** (demographics is the canonical example):
- `_sql.py` — SQL template (typically a large CTE chain)
- `_metrics.py` — statistical calculations on the resulting DataFrame
- `_report.py` — CSV and HTML/PDF output
- `<main_script>.py` — orchestrates the pipeline, handles interactive prompts

Simpler modules: **deliris** — see `deliris/README.md` for CAM-ICU SQL/CSV/plots and cohort definitions; others (necropsy, sepsis3, snisp, nutritions) often collapse into a single script.

**`data_quality/`** — ETL completeness cross-year comparison over `movements` and `labs`. Same `_sql.py` / `_metrics.py` / `_report.py` split as demographics, but `_report.py` also embeds matplotlib charts (line, heatmap, bars) as base64 PNGs into a standalone HTML file.

**Output** goes to `<module>/output/` directories, which are gitignored.

## SQL Conventions

The database runs on **AWS Athena (Trino/Presto SQL dialect)** — not MySQL. Tables must be schema-qualified with `datascope_gestor_prod.` (e.g. `datascope_gestor_prod.movements`). Tables no longer carry the `g_` prefix (e.g. `g_episodes` → `episodes`). Dictionary tables keep `dic_` prefix. SQL queries use extensive CTEs and window functions (`LAG`, `LEAD`, `ROW_NUMBER`). The predominant-unit logic (assign a stay to the unit where the patient spent the most time) is a recurring pattern shared across demographics, admissions, and drg modules.

**`DB_CONTEXT_AWS.md`** (root) is the authoritative database schema reference for the AWS/Athena instance. Read it before writing new SQL — it documents all relevant tables (without the `g_` prefix), ETL rules, ICD mappings, and the Athena (Trino/Presto) SQL dialect to use instead of MySQL. For code lookups (ICD, DRG, provisions, etc.), query the database directly via `execute_query` instead of using local dictionaries.

## Interactive Prompts

Most scripts prompt for:
- Year range: accepts `2024`, `2023-2025`, or `2023,2024`
- Unit codes: single (e.g. `E073`) or comma-separated (e.g. `E073,I073`)

Defaults are shown in brackets and accepted with Enter.
