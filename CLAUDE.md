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

The project is an installable package (`src/`-layout). Install in editable mode once:

```bash
pip install -e .          # or `pip install -e .[dev]` for pytest + ruff
```

After install, `from indicadors_iso.connection import execute_query` works from anywhere — no `sys.path` hacks.

## Running Scripts

The original entry-point paths are preserved as thin shims; each forwards to its real implementation under `src/indicadors_iso/`:

```bash
python demographics/predominant_unit/run.py   # 1 informe combinado (E073+I073, unidad predominante)
python demographics/per_unit/run.py           # 2 informes (E073 e I073 por separado, sin agrupar traslados)
python drg/drg_complexity_report.py           # outputs PDF + CSV
python dynamic_forms/run_queries.py --list
python dynamic_forms/run_queries.py --query <name>
python dynamic_forms/run_queries.py --all
python data_quality/completeness_2024_vs_2025.py  # prompts for (y1,y2) + YTD cutoff; ETL completeness report
python deliris/run_sql.py <query>             # CAM-ICU compliance / positivity / coverage (resolves against deliris/sql/)
python deliris/camicu_plots.py                # CAM-ICU plots from previously generated CSVs
python nutritions/nutritions.py               # nutrición enteral/parenteral
python micro/rectal_mdr/run.py                # aislamientos rectal-MDR por unidad (E073, I073)
```

Outputs from every module land under the centralized `output/<module>/…` (gitignored). Tests: `pytest` (or `python tests/test_metabase_row_cap.py` for the DB-touching cap check).

## Architecture

**Package layout.** All Python code lives under `src/indicadors_iso/`. The directories `data_quality/`, `demographics/`, `deliris/`, `drg/`, `dynamic_forms/`, `micro/`, `nutritions/` at the repo root contain **only 5-line shim scripts** that forward to the package — never put real logic there. Real implementations are at `src/indicadors_iso/<module>/`. `dictionaries/`, `docs/`, `tests/`, and `output/` stay outside the package.

**`indicadors_iso.connection`** — shared database layer via Metabase API. Use `execute_query(query, verbose=True)` for a single SQL string returning a DataFrame, or `execute_query_yearly(render_sql, min_year, max_year, label="…")` to dodge Metabase's silent 2000-row truncation by chunking year-by-year (`render_sql` is a `int -> str` callable). Both handle `.env` discovery across Windows/macOS OneDrive paths automatically and authenticate against Metabase.

**`indicadors_iso._paths`** — single source of truth for repo paths: `REPO_ROOT`, `OUTPUT_DIR` (=`<repo>/output/`), `DICTIONARIES_DIR`, and `module_output_dir("module", "submodule")` which creates and returns `output/module/submodule/`. Modules use this helper instead of `Path(__file__).parent / "output"`.

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

**`demographics/autopsy/`** and **`demographics/nutrition/`** — library-only sibling submodules consumed by both `demographics/per_unit/run.py` and `demographics/predominant_unit/run.py`. Each exposes `load_*_cohort(min_year, max_year, units)` (year-by-year via `execute_query_yearly`) plus `merge_per_unit` / `merge_predominant` helpers. Per-unit grain joins on `[patient_ref, episode_ref, ou_loc_ref, stay_id]`; predominant-unit grain joins on `[patient_ref, episode_ref]` with episode-level aggregation (e.g. `received_enteral` = OR across stays, `nutr_enteral_start` = MIN). For nutrition, `hours_to_enteral` must be recomputed against the admission_date of the *predominant-unit* row after the merge, since it can predate the per-unit admission_date when the nutrition started after a transfer.

Simpler modules:
- **`deliris/`** — CAM-ICU compliance / positivity / daily coverage. Each indicator is a standalone `.sql` file run via `run_sql.py`; plots from the resulting CSVs via `camicu_plots.py`. See `deliris/README.md`.
- **`nutritions/`** — enteral/parenteral nutrition analysis (single-script `nutritions.py`).
- **`micro/rectal_mdr/`** — rectal MDR isolates restricted to E073/I073 stays (per-unit grain, with `place_ref`). Year-by-year download, one CSV per unit.

**`data_quality/`** — ETL completeness cross-year comparison over `movements` and `labs`. Same `_sql.py` / `_metrics.py` / `_report.py` split as demographics, but `_report.py` also embeds matplotlib charts (line, heatmap, bars) as base64 PNGs into a standalone HTML file.

**`dictionaries/datanex/`** (root) — local CSV/SQL catalogs of DataNex reference tables (`dic_lab`, `dic_rc`, `dic_prescriptions`, `dic_administrations`, `dic_perfusions`, `dic_dynamic_forms`). Use these to grep for `*_ref` codes locally instead of running exploratory queries; rerun the numbered SQLs (`00_*.sql`, `01_*.sql`, …) to refresh. The folder used to be named `dictionaries/sofa/` but holds generic DataNex catalogs — kept here for SOFA + adjacent indicator work.

**Output** goes to the centralized `output/<module>/` (e.g. `output/demographics/per_unit/`), which is gitignored. Use `module_output_dir(...)` from `indicadors_iso._paths` rather than hardcoding paths.

## SQL Conventions

The database runs on **AWS Athena (Trino/Presto SQL dialect)** — not MySQL. Tables must be schema-qualified with `datascope_gestor_prod.` (e.g. `datascope_gestor_prod.movements`). Tables no longer carry the `g_` prefix (e.g. `g_episodes` → `episodes`). Dictionary tables keep `dic_` prefix. SQL queries use extensive CTEs and window functions (`LAG`, `LEAD`, `ROW_NUMBER`). The predominant-unit logic (assign a stay to the unit where the patient spent the most time) is a recurring pattern shared across demographics and drg modules.

**`docs/DB_CONTEXT_AWS.md`** is the authoritative database schema reference for the AWS/Athena instance. Read it before writing new SQL — it documents all relevant tables (without the `g_` prefix), ETL rules, ICD mappings, and the Athena (Trino/Presto) SQL dialect to use instead of MySQL. For code lookups (ICD, DRG, provisions, etc.), query the database directly via `execute_query` instead of using local dictionaries.

## Interactive Prompts

Most scripts prompt for:
- Year range: accepts `2024`, `2023-2025`, or `2023,2024`
- Unit codes: single (e.g. `E073`) or comma-separated (e.g. `E073,I073`)

Defaults are shown in brackets and accepted with Enter.
