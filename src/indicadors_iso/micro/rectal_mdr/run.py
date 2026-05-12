"""Aislamientos positivos en frotis rectal de multirresistentes —
restringidos a las estancias E073 / I073 definidas en
demographics/per_unit (sin agrupar traslados, prescripción durante la
estancia, place_ref asignado).

Genera UN CSV por unidad. Descarga año a año vía
`connection.execute_query_yearly` para esquivar el tope silencioso de
2000 filas de Metabase.

Salida:
    micro/output/rectal_mdr_E073_<min>-<max>.csv
    micro/output/rectal_mdr_I073_<min>-<max>.csv
"""
from __future__ import annotations

import pandas as pd

from indicadors_iso._paths import REPO_ROOT, module_output_dir
from indicadors_iso.connection import execute_query_yearly
from indicadors_iso.micro.rectal_mdr._sql import SQL_TEMPLATE

OUTPUT_DIR = module_output_dir("micro", "rectal_mdr")
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


def load_isolates(min_year: int, max_year: int) -> pd.DataFrame:
    print(
        f"[loader] descargando aislamientos rectal-MDR año a año "
        f"({min_year}-{max_year})…"
    )
    df = execute_query_yearly(
        lambda year: SQL_TEMPLATE.format(min_year=year, max_year=year),
        min_year,
        max_year,
        label="rectal_mdr",
    )
    return df


def main() -> None:
    raw = input("Rango de años [2019-2025]: ")
    min_year, max_year = parse_year_input(raw)

    df = load_isolates(min_year, max_year)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if df.empty:
        print("[run] sin filas; no se generan CSV.")
        return

    print(f"[run] total filas descargadas: {len(df)}")
    for unit in UNITS:
        sub = df[df["ou_loc_ref"] == unit].copy()
        out_path = OUTPUT_DIR / f"rectal_mdr_{unit}_{min_year}-{max_year}.csv"
        sub.to_csv(out_path, index=False)
        print(f"  [{unit}] {len(sub)} filas -> {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
