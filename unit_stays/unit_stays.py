import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query
from unit_stays._sql import SQL_TEMPLATE


def parse_year_input(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return 2018, 2024
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    year_val = int(text)
    return year_val, year_val


def parse_units_input(text: str) -> tuple[str, str]:
    """Parse comma-separated unit codes. Returns (sql_in_list, display_str)."""
    codes = [u.strip() for u in text.strip().split(",") if u.strip()]
    sql_list = ", ".join(f"'{c}'" for c in codes)
    display = "-".join(codes)
    return sql_list, display


def main():
    units_input = input("Unidad(es) a analizar (p.ej. E073 o E073,I073): ").strip()
    if not units_input:
        print("Se requiere al menos una unidad.")
        sys.exit(1)
    units_sql, units_display = parse_units_input(units_input)

    year_input = input("Periodo (p.ej. 2022-2024) [2018-2024]: ").strip()
    min_year, max_year = parse_year_input(year_input)
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    print(f"\nConsultando estancias en {units_display} ({years_str})...")
    df = execute_query(SQL_TEMPLATE.format(units=units_sql, min_year=min_year, max_year=max_year))

    n_total = len(df)
    n_patients = df["patient_ref"].nunique()
    n_open = int((df["still_admitted"] == "Yes").sum())

    print(f"  {n_total} estancias | {n_patients} pacientes únicos")
    if n_open:
        print(f"  {n_open} episodio(s) aún abiertos excluidos del CSV ({n_open / n_total * 100:.1f}%)")

    df_closed = df[df["still_admitted"] == "No"].copy()

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / f"{units_display}_stays_{years_str}.csv"
    df_closed.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"Listo. CSV guardado en {csv_path}")


if __name__ == "__main__":
    main()
