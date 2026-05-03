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
python demographics/predominant_unit/run.py   # 1 informe combinado (E073+I073, unidad predominante)
python demographics/per_unit/run.py           # 2 informes (E073 e I073 por separado, sin agrupar traslados)
python drg/drg_complexity_report.py           # outputs PDF + CSV
python dynamic_forms/run_queries.py --list
python dynamic_forms/run_queries.py --query <name>
python dynamic_forms/run_queries.py --all
python data_quality/completeness_2024_vs_2025.py  # prompts for (y1,y2) + YTD cutoff; ETL completeness report
```

There are no tests, linters, or build tools configured.

## Architecture

**`connection.py`** (root) — shared database layer via Metabase API. Use `execute_query(query, verbose=True)` for a single SQL string returning a DataFrame, or `execute_query_yearly(render_sql, min_year, max_year, label="…")` to dodge Metabase's silent 2000-row truncation by chunking year-by-year (`render_sql` is a `int -> str` callable). Both handle `.env` discovery across Windows/macOS OneDrive paths automatically and authenticate against Metabase.

**Module pattern** (demographics is the canonical example):
- `_sql.py` — SQL template (typically a large CTE chain)
- `_metrics.py` — statistical calculations on the resulting DataFrame
- `_report.py` — CSV and HTML/PDF output
- `<main_script>.py` — orchestrates the pipeline, handles interactive prompts

**`demographics/`** has two co-existing pipelines as subfolders sharing `_loader.py`/`_metrics.py`/`_report.py`:
  - `predominant_unit/` — current logic. Movements between E073/I073 in the same episode are merged and assigned to the unit with the most time. One combined report.
  - `per_unit/` — new logic. A transfer between units splits the stay into two separate rows. Generates one HTML/CSV per unit. Readmission excludes intra-episode transfers.

  Both pipelines share `_loader.py`, which (a) downloads the cohort year-by-year via `execute_query_yearly` to dodge Metabase's silent 2000-row cap, and (b) augments missing 2025 data via bootstrap-sampling, with the target = mean stays of the previous 3 years (per-unit when applicable). See `demographics/README.md` for details.

**`demographics/sofa/`** — SOFA original (Vincent 1996) at ICU admission. Athena query aggregates the 6 components in the first 24 h (one row per stay, per-unit), Python computes the score. Sources by component documented in `demographics/sofa/README.md`. Fetched year-by-year via `execute_query_yearly`. Consumed only as a library by `demographics/per_unit/run.py`, which merges the score into the cohort and adds SOFA rows (global, cirrosis, otro hospital) to the report for both E073 (UCI) and I073 (semi-intensive digestive). The `predominant_unit` pipeline does **not** use SOFA (the predominant-unit aggregation is incompatible with the per-stay 24h window).

Simpler modules: **deliris** — see `deliris/README.md` for CAM-ICU SQL/CSV/plots and cohort definitions; **nutritions** — enteral/parenteral nutrition analysis.

**`data_quality/`** — ETL completeness cross-year comparison over `movements` and `labs`. Same `_sql.py` / `_metrics.py` / `_report.py` split as demographics, but `_report.py` also embeds matplotlib charts (line, heatmap, bars) as base64 PNGs into a standalone HTML file.

**Output** goes to `<module>/output/` directories, which are gitignored.

## SQL Conventions

The database runs on **AWS Athena (Trino/Presto SQL dialect)** — not MySQL. Tables must be schema-qualified with `datascope_gestor_prod.` (e.g. `datascope_gestor_prod.movements`). Tables no longer carry the `g_` prefix (e.g. `g_episodes` → `episodes`). Dictionary tables keep `dic_` prefix. SQL queries use extensive CTEs and window functions (`LAG`, `LEAD`, `ROW_NUMBER`). The predominant-unit logic (assign a stay to the unit where the patient spent the most time) is a recurring pattern shared across demographics and drg modules.

**`DB_CONTEXT_AWS.md`** (root) is the authoritative database schema reference for the AWS/Athena instance. Read it before writing new SQL — it documents all relevant tables (without the `g_` prefix), ETL rules, ICD mappings, and the Athena (Trino/Presto) SQL dialect to use instead of MySQL. For code lookups (ICD, DRG, provisions, etc.), query the database directly via `execute_query` instead of using local dictionaries.

## Interactive Prompts

Most scripts prompt for:
- Year range: accepts `2024`, `2023-2025`, or `2023,2024`
- Unit codes: single (e.g. `E073`) or comma-separated (e.g. `E073,I073`)

Defaults are shown in brackets and accepted with Enter.
