import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from connection import execute_query

SQL_PATH = Path(__file__).resolve().parent / "deaths_by_month.sql"
OUTPUT_CSV = Path(__file__).resolve().parent / "deaths_by_month.csv"


def build_date_filter(start_date: str, end_date: str) -> str:
    if start_date and end_date:
        return (
            "AND exitus_date BETWEEN "
            f"'{start_date} 00:00:00' AND '{end_date} 23:59:59'"
        )
    if start_date:
        return f"AND exitus_date >= '{start_date} 00:00:00'"
    if end_date:
        return f"AND exitus_date <= '{end_date} 23:59:59'"
    return ""


def load_sql(date_filter: str) -> str:
    with open(SQL_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    return sql.format(date_filter=date_filter)


def main():
    print("Deaths by month and year")
    start_date = input("Start date (YYYY-MM-DD, optional): ").strip()
    end_date = input("End date   (YYYY-MM-DD, optional): ").strip()

    date_filter = build_date_filter(start_date, end_date)
    query = load_sql(date_filter)

    df = execute_query(query)

    if df.empty:
        print("No deaths found for the given range.")
        return

    df["month"] = df["month"].astype(int)
    df["year"] = df["year"].astype(int)
    df = df.sort_values(["year", "month"])

    df["month_label"] = df["month"].apply(lambda m: f"{m:02d}")
    pivot = df.pivot_table(
        index="year",
        columns="month_label",
        values="deaths",
        fill_value=0
    )

    print("\nDeaths by month/year:")
    print(df)

    print("\nPivot table (year x month):")
    print(pivot)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved detailed counts to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
