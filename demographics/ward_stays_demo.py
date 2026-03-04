import sys
from pathlib import Path

import pandas as pd

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query
from demographics._sql import SQL_TEMPLATE
from demographics._metrics import ABS_CLINIC, _classify_aisbe, compute_summary
from demographics._report import generate_html, to_dataframe


def parse_year_input(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return 2018, 2024
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    year_val = int(text)
    return year_val, year_val


def _print_aisbe_stats(df: pd.DataFrame) -> None:
    if "health_area" not in df.columns:
        return

    patient_health_all = (
        df[["patient_ref", "health_area", "postcode"]]
        .drop_duplicates(subset=["patient_ref"])
        .set_index("patient_ref")
    )
    n_patients_all = len(patient_health_all)

    ha_all = patient_health_all["health_area"].astype(str).str.strip()
    missing_health = ha_all.eq("") | ha_all.eq("nan")
    n_missing_health = int(missing_health.sum())
    pct_missing_health = n_missing_health / n_patients_all * 100 if n_patients_all > 0 else 0.0
    print(
        f"Pacientes \u00fanicos: {n_patients_all} | "
        f"health_area missing/vac\u00eda en {n_missing_health} "
        f"({pct_missing_health:.1f}%)"
    )

    print("\nDistribuci\u00f3n de health_area (top 20):")
    ha_counts = ha_all[~missing_health].value_counts().head(20)
    for area, count in ha_counts.items():
        pct = count / n_patients_all * 100 if n_patients_all > 0 else 0.0
        print(f"  {area}: {count} pacientes ({pct:.1f}%)")

    is_aisbe_all = _classify_aisbe(patient_health_all)
    n_aisbe_total = int(is_aisbe_all.sum())
    pct_aisbe_total = n_aisbe_total / n_patients_all * 100 if n_patients_all > 0 else 0.0

    is_abs_all = patient_health_all["health_area"].astype(str).str.strip().isin(ABS_CLINIC)
    n_aisbe_ha = int(is_abs_all.sum())
    n_aisbe_cp = n_aisbe_total - n_aisbe_ha

    print(
        "\nClasificaci\u00f3n AISBE (toda la cohorte, a nivel paciente):\n"
        f"  AISBE por health_area (ABS cl\u00ednicas): {n_aisbe_ha}\n"
        f"  AISBE a\u00f1adido por c\u00f3digo postal: {n_aisbe_cp}\n"
        f"  Total AISBE: {n_aisbe_total} "
        f"({pct_aisbe_total:.1f}% de los pacientes \u00fanicos)"
    )


def main():
    print("========================================")
    print("   WARD STAYS DEMOGRAPHIC TABLE (E073+I073)")
    print("========================================")

    year_input = input(
        "Enter year range (e.g., 2018-2024, default 2018-2024): "
    )
    min_year, max_year = parse_year_input(year_input)
    print(f"Using years from {min_year} to {max_year}")

    query = SQL_TEMPLATE.format(min_year=min_year, max_year=max_year)
    df = execute_query(query)
    print(f"Datos de cohorte obtenidos: {len(df)} estancias")

    _print_aisbe_stats(df)

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    # Save full cohort
    cohort_filename = output_dir / f"ward_stays_cohort_{years_str}_E073-I073.csv"
    df.to_csv(cohort_filename, index=False, encoding="utf-8-sig")
    print(f"Cohorte completa guardada en: {cohort_filename}")

    # Compute metrics once; derive both CSV and HTML outputs
    sections, years = compute_summary(df)

    summary_df = to_dataframe(sections, years)
    summary_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.csv"
    summary_df.to_csv(summary_filename, encoding="utf-8-sig")
    print(f"Tabla resumen (CSV) guardada en: {summary_filename}")

    html_filename = output_dir / f"ward_stays_summary_{years_str}_E073-I073.html"
    title_text = f"Demograf\u00eda y resultados de estancias en E073+I073 ({years_str})"
    generate_html(sections, years, title_text, html_filename)
    print(f"Tabla resumen (HTML) guardada en: {html_filename}")


if __name__ == "__main__":
    main()
