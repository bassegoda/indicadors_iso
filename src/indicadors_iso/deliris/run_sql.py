"""Run a deliris .sql file against Metabase and save the CSV.

Usage:
    python deliris/run_sql.py <name|path>

`<name>` may be the bare query stem (e.g. ``camicu_compliance``) — in which
case the bundled ``deliris/sql/<name>.sql`` is used — or an explicit path
to a .sql file. The legacy paths (``deliris/camicu_compliance.sql``)
also resolve transparently by basename.
"""

import sys
from pathlib import Path

from indicadors_iso._paths import module_output_dir
from indicadors_iso.connection import execute_query

SQL_DIR = Path(__file__).resolve().parent / "sql"
OUTPUT_DIR = module_output_dir("deliris")


def _resolve_sql(arg: str) -> Path:
    """Resolve `arg` to a real .sql file inside the package."""
    p = Path(arg)
    if p.exists():
        return p

    stem = p.stem if p.suffix == ".sql" else p.name
    candidate = SQL_DIR / f"{stem}.sql"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Query not found: '{arg}'. "
        f"Available: {', '.join(sorted(q.stem for q in SQL_DIR.glob('*.sql')))}"
    )


def run_sql_file(file_path: Path) -> None:
    """Read a .sql file, execute it, print a head and write the CSV."""
    print(f"--- Reading SQL file: {file_path} ---")
    query = file_path.read_text(encoding="utf-8").strip()

    if not query:
        print("Error: The SQL file is empty.")
        return

    df = execute_query(query)

    if df is not None and not df.empty:
        print("\n--- Query Results (First 5 rows) ---")
        print(df.head().to_string())
        print(f"\nTotal rows returned: {len(df)}")
    else:
        print("\nQuery executed successfully, but returned no results.")

    out_path = OUTPUT_DIR / f"{file_path.stem}.csv"
    df.to_csv(out_path, index=False)
    print(f"\nResults saved to: {out_path}")


def main() -> int:
    if len(sys.argv) <= 1:
        print("Usage: python deliris/run_sql.py <name|path>")
        print("Available queries:")
        for q in sorted(SQL_DIR.glob("*.sql")):
            print(f"  - {q.stem}")
        return 1

    try:
        target = _resolve_sql(sys.argv[1])
    except FileNotFoundError as e:
        print(e)
        return 1

    run_sql_file(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
