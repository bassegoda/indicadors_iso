"""SOFA-2 al ingreso en UCI — pipeline completo.

Ejecuta una sola query SQL contra DataNex (Athena vía Metabase) que
agrega los 6 componentes SOFA en las primeras 24 h por estancia
(per-unit, sin agrupar traslados). Calcula puntuación en Python.

Salidas en `sofa2/output/`:
  * `sofa2_cohort_<periodo>.csv`   — 1 fila por estancia con valores y SOFA
  * `sofa2_summary_<periodo>.csv`  — resumen por unidad/año
  * `sofa2_summary_<periodo>.html` — informe estilo demographics
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from connection import execute_query
from sofa2._config import ICU_UNITS, WINDOW_HOURS
from sofa2._metrics import compute_sofa, summarize_by_unit_year
from sofa2._report import write_cohort_csv, write_html_report, write_summary_csv
from sofa2._sql import render_sql

OUTPUT_DIR = _REPO_ROOT / "sofa2" / "output"
SNAPSHOT_DIR = _REPO_ROOT / "sofa2" / "snapshots"


def load_snapshot_or_query(years_str: str, units: list[str],
                           min_year: int, max_year: int) -> pd.DataFrame:
    """Si existe un snapshot CSV exportado de Metabase, úsalo; si no,
    lanza la query vía Python (limitada a 2000 filas por Metabase API).

    Convención del nombre: `sofa2_snapshot_<periodo>.csv` en
    `sofa2/snapshots/`. Da igual qué unidades contenga: filtramos en
    Python por las pedidas y por el rango de año.
    """
    snapshot = SNAPSHOT_DIR / f"sofa2_snapshot_{years_str}.csv"
    if snapshot.exists():
        print(f"  [snapshot] usando {snapshot.relative_to(_REPO_ROOT)}")
        df = pd.read_csv(snapshot)
        df = df[df["ou_loc_ref"].isin(units)
                & df["year_admission"].between(min_year, max_year)]
        return df.reset_index(drop=True)

    print(f"  [api] lanzando query vía Metabase API (límite 2000 filas)")
    sql = render_sql(min_year, max_year, units, window_hours=WINDOW_HOURS)
    return execute_query(sql, verbose=True)


def parse_year_input(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return 2024, 2024
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    if "," in text:
        parts = [int(p) for p in text.split(",")]
        return min(parts), max(parts)
    y = int(text)
    return y, y


def parse_units_input(text: str, default: list[str]) -> list[str]:
    text = text.strip()
    if not text:
        return default
    return [u.strip().upper() for u in text.split(",") if u.strip()]


def main():
    year_input = input("Periodo (p.ej. 2023-2024) [2024]: ").strip()
    min_year, max_year = parse_year_input(year_input)
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    units_input = input(
        f"Unidades UCI (coma) [{','.join(ICU_UNITS)}]: "
    ).strip()
    units = parse_units_input(units_input, ICU_UNITS)

    print(f"\nConsultando SOFA-2 {years_str} en {units}...")
    df = load_snapshot_or_query(years_str, units, min_year, max_year)

    if df.empty:
        print("Sin filas. Aborto.")
        return

    if len(df) >= 2000 and not (SNAPSHOT_DIR / f"sofa2_snapshot_{years_str}.csv").exists():
        print(f"  ⚠️  {len(df)} filas — posible truncamiento de Metabase API.")
        print(f"      Si esperas más, lanza el SQL desde Metabase web y guarda")
        print(f"      el CSV completo en {SNAPSHOT_DIR}/sofa2_snapshot_{years_str}.csv")

    print(f"  {len(df)} estancias recuperadas.")
    print("Calculando SOFA...")
    df = compute_sofa(df)

    full = (df["sofa_components_available"] == 6).sum()
    partial = (df["sofa_components_available"].between(1, 5)).sum()
    empty = (df["sofa_components_available"] == 0).sum()
    print(f"  {full} con 6 componentes | {partial} parciales | {empty} sin datos")
    print(f"  SOFA total: media {df['sofa_total'].mean():.2f}, "
          f"mediana {df['sofa_total'].median():.0f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort_path = OUTPUT_DIR / f"sofa2_cohort_{years_str}.csv"
    summary_path = OUTPUT_DIR / f"sofa2_summary_{years_str}.csv"
    html_path = OUTPUT_DIR / f"sofa2_summary_{years_str}.html"

    summary = summarize_by_unit_year(df)
    write_cohort_csv(df, cohort_path)
    write_summary_csv(summary, summary_path)
    write_html_report(
        df, summary,
        f"SOFA-2 al ingreso en UCI ({years_str})",
        html_path,
    )

    print(f"\nListo. Archivos en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
