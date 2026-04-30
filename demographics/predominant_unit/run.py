"""Reporting demográfico/clínico — variante `predominant_unit`.

Aplica la lógica de "unidad predominante": los movimientos consecutivos
entre E073 e I073 dentro de un mismo episodio se agrupan en UNA estancia
y se asignan a la unidad donde el paciente pasó más tiempo. Genera UN
único informe combinado para E073 + I073.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from demographics._bed_occupancy import compute_bed_occupancy
from demographics._config import FAKE_BED_PLACE_REFS_E073
from demographics._loader import load_cohort
from demographics._metrics import compute_summary
from demographics._report import generate_html, to_dataframe
from demographics.predominant_unit._sql import SQL_TEMPLATE

SCRIPT_DIR = Path(__file__).resolve().parent
SNAPSHOT_CSV = SCRIPT_DIR / "cohort_2019-2025.csv"
OUTPUT_DIR = _REPO_ROOT / "demographics" / "output" / "predominant_unit"


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

    print(f"Consultando cohorte (predominant_unit) {years_str}…")
    df = load_cohort(
        snapshot_path=SNAPSHOT_CSV,
        min_year=min_year,
        max_year=max_year,
        sql_template=SQL_TEMPLATE,
        synthetic_group_col=None,
    )

    n_total = len(df)
    n_open = int((df["still_admitted"] == "Yes").sum())
    n_patients = df["patient_ref"].nunique()

    print(f"  {n_total} estancias | {n_patients} pacientes únicos")
    if n_open:
        print(
            f"  {n_open} episodio(s) aún abiertos excluidos del análisis "
            f"({n_open / n_total * 100:.1f}%)"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cohort_path = OUTPUT_DIR / f"ward_stays_cohort_{years_str}_E073-I073.csv"
    df.to_csv(cohort_path, index=False, encoding="utf-8-sig")

    units_in_cohort = sorted(df["ou_loc_ref"].dropna().unique())
    print(
        f"Calculando ocupaci\u00f3n emp\u00edrica de camas {units_in_cohort} "
        f"{min_year}-{max_year}\u2026"
    )
    bed_occupancy = compute_bed_occupancy(
        units=units_in_cohort,
        min_year=min_year,
        max_year=max_year,
        fake_bed_place_refs=FAKE_BED_PLACE_REFS_E073,
    )

    sections, years = compute_summary(df, bed_occupancy=bed_occupancy)

    summary_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_E073-I073.csv"
    to_dataframe(sections, years).to_csv(summary_path, encoding="utf-8-sig")

    html_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_E073-I073.html"
    generate_html(
        sections,
        years,
        f"Demografía y resultados E073+I073 — unidad predominante ({years_str})",
        html_path,
        subtitle=(
            "Hospital Clínic de Barcelona — Unidades E073, I073 "
            "(predominant-unit, traslados intra-unidades agrupados)"
        ),
    )

    print(f"Listo. Archivos guardados en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
