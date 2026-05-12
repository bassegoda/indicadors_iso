"""Reporting demográfico/clínico — variante `predominant_unit`.

Aplica la lógica de "unidad predominante": los movimientos consecutivos
entre E073 e I073 dentro de un mismo episodio se agrupan en UNA estancia
y se asignan a la unidad donde el paciente pasó más tiempo. Genera UN
único informe combinado para E073 + I073.
"""

from indicadors_iso._paths import module_output_dir
from indicadors_iso.demographics._bed_occupancy import compute_bed_occupancy_nominal
from indicadors_iso.demographics._config import FAKE_BED_PLACE_REFS_E073
from indicadors_iso.demographics._loader import (
    SYNTHETIC_LOOKBACK_YEARS,
    SYNTHETIC_YEAR,
    augment_synthetic_2025,
    compute_3y_mean_target,
    load_cohort,
)
from indicadors_iso.demographics._metrics import compute_summary
from indicadors_iso.demographics._report import generate_html, to_dataframe
from indicadors_iso.demographics.autopsy._loader import (
    load_autopsy_cohort,
    merge_predominant as merge_autopsy_predominant,
)
from indicadors_iso.demographics.nutrition._loader import (
    load_nutrition_cohort,
    merge_predominant as merge_nutrition_predominant,
)
from indicadors_iso.demographics.predominant_unit._sql import SQL_TEMPLATE

UNITS = ["E073", "I073"]

OUTPUT_DIR = module_output_dir("demographics", "predominant_unit")


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
        min_year=min_year,
        max_year=max_year,
        sql_template=SQL_TEMPLATE,
        synthetic_group_col=None,
        skip_synthetic=True,
    )

    print(f"Consultando nutrición enteral / parenteral {years_str}…")
    nutrition_df = load_nutrition_cohort(min_year, max_year, UNITS)
    df = merge_nutrition_predominant(df, nutrition_df)

    print(f"Consultando autopsias / necropsias {years_str}…")
    autopsy_df = load_autopsy_cohort(min_year, max_year, UNITS)
    df = merge_autopsy_predominant(df, autopsy_df)

    # Augmentación sintética 2025: se aplica AHORA, después del merge de
    # nutrición, para que las filas sintéticas hereden los flags
    # `received_*` y los `hours_to_*` del template (igual patrón que en
    # `per_unit/run.py` con SOFA + nutrición).
    if min_year <= SYNTHETIC_YEAR <= max_year:
        target = compute_3y_mean_target(
            df,
            year_now=SYNTHETIC_YEAR,
            n_years=SYNTHETIC_LOOKBACK_YEARS,
            group_col=None,
        )
        df = augment_synthetic_2025(df, target=target, group_col=None)

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
        f"Calculando ocupaci\u00f3n nominal de camas {units_in_cohort} "
        f"{min_year}-{max_year}\u2026"
    )
    bed_occupancy = compute_bed_occupancy_nominal(
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
