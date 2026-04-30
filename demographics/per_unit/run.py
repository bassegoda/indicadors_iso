"""Reporting demográfico/clínico — variante `per_unit`.

NO agrupa traslados entre unidades: si un paciente pasa de E073 a I073
durante el mismo episodio, contará como dos estancias distintas (una en
cada unidad). Genera **un informe por cada unidad** (E073 e I073).

La augmentación sintética 2025 se calcula y aplica POR unidad: cada
unidad recibe su propio target = media de estancias 2022-2024 EN ESA
unidad.
"""

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from demographics._bed_occupancy import compute_bed_occupancy
from demographics._config import FAKE_BED_PLACE_REFS_E073
from demographics._loader import load_cohort
from demographics._metrics import compute_summary
from demographics._report import generate_html, to_dataframe
from demographics.per_unit._sql import SQL_TEMPLATE

SCRIPT_DIR = Path(__file__).resolve().parent
SNAPSHOT_CSV = SCRIPT_DIR / "cohort_2019-2025.csv"
OUTPUT_DIR = _REPO_ROOT / "demographics" / "output" / "per_unit"

UNITS = ["E073", "I073"]


def parse_year_input(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return 2019, 2025
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    year_val = int(text)
    return year_val, year_val


def main():
    year_input = input("Periodo (p.ej. 2019-2025) [2019-2025]: ").strip()
    min_year, max_year = parse_year_input(year_input)
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    print(f"Consultando cohorte (per_unit) {years_str}…")
    df = load_cohort(
        snapshot_path=SNAPSHOT_CSV,
        min_year=min_year,
        max_year=max_year,
        sql_template=SQL_TEMPLATE,
        synthetic_group_col="ou_loc_ref",
    )

    n_total = len(df)
    n_open = int((df["still_admitted"] == "Yes").sum())
    n_patients = df["patient_ref"].nunique()

    print(f"  {n_total} estancias totales | {n_patients} pacientes únicos")
    if n_open:
        print(
            f"  {n_open} episodio(s) aún abiertos excluidos del análisis "
            f"({n_open / n_total * 100:.1f}%)"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    available_units = sorted(df["ou_loc_ref"].dropna().unique())
    print(f"  Unidades en cohorte: {available_units}")

    print(
        f"Calculando ocupaci\u00f3n emp\u00edrica de camas {available_units} "
        f"{min_year}-{max_year}\u2026"
    )
    bed_occupancy = compute_bed_occupancy(
        units=available_units,
        min_year=min_year,
        max_year=max_year,
        fake_bed_place_refs=FAKE_BED_PLACE_REFS_E073,
    )

    for unit in UNITS:
        sub = df[df["ou_loc_ref"] == unit].copy()
        n_unit = len(sub)
        n_unit_pat = sub["patient_ref"].nunique()
        print(f"\n--- {unit} ---  {n_unit} estancias | {n_unit_pat} pacientes únicos")

        if sub.empty:
            print(f"  (sin filas para {unit}, saltando informe)")
            continue

        cohort_path = OUTPUT_DIR / f"ward_stays_cohort_{years_str}_{unit}.csv"
        sub.to_csv(cohort_path, index=False, encoding="utf-8-sig")

        sections, years = compute_summary(sub, bed_occupancy=bed_occupancy)

        summary_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_{unit}.csv"
        to_dataframe(sections, years).to_csv(summary_path, encoding="utf-8-sig")

        html_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_{unit}.html"
        generate_html(
            sections,
            years,
            f"Demografía y resultados {unit} — per unit ({years_str})",
            html_path,
            subtitle=(
                f"Hospital Clínic de Barcelona — Unidad {unit} (per-unit, "
                "estancias separadas por unidad)"
            ),
        )

    print(f"\nListo. Archivos guardados en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
