import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query
from demographics._sql import SQL_TEMPLATE
from demographics._metrics import compute_summary
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


def main():
    year_input = input("Periodo (p.ej. 2018-2024) [2018-2024]: ").strip()
    min_year, max_year = parse_year_input(year_input)
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    print(f"Consultando cohorte {years_str}...")
    df = execute_query(SQL_TEMPLATE.format(min_year=min_year, max_year=max_year))

    n_total = len(df)
    n_open = int((df["still_admitted"] == "Yes").sum())
    n_closed = n_total - n_open
    n_patients = df["patient_ref"].nunique()

    print(f"  {n_total} estancias | {n_patients} pacientes únicos")
    if n_open:
        print(f"  {n_open} episodio(s) aún abiertos excluidos del análisis ({n_open/n_total*100:.1f}%)")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    cohort_path = output_dir / f"ward_stays_cohort_{years_str}_E073-I073.csv"
    df.to_csv(cohort_path, index=False, encoding="utf-8-sig")

    sections, years = compute_summary(df)

    summary_path = output_dir / f"ward_stays_summary_{years_str}_E073-I073.csv"
    to_dataframe(sections, years).to_csv(summary_path, encoding="utf-8-sig")

    html_path = output_dir / f"ward_stays_summary_{years_str}_E073-I073.html"
    generate_html(sections, years, f"Demografía y resultados E073+I073 ({years_str})", html_path)

    print(f"Listo. Archivos guardados en {output_dir}/")


if __name__ == "__main__":
    main()
