"""
Comprueba si la API de Metabase sigue truncando resultados a 2000 filas.

Uso:
    pytest tests/test_metabase_row_cap.py            # ejecución como test
    python tests/test_metabase_row_cap.py            # ejecución directa con argparse
    python tests/test_metabase_row_cap.py --year 2024 --probe-limit 5000
"""

from __future__ import annotations

import argparse
import sys

from indicadors_iso.connection import METABASE_SILENT_ROW_CAP, execute_query


def build_count_query(year: int) -> str:
    return f"""
    SELECT COUNT(*) AS total_rows
    FROM datascope_gestor_prod.movements
    WHERE year(start_date) = {year}
    """


def build_probe_query(year: int, probe_limit: int) -> str:
    return f"""
    SELECT
        patient_ref,
        episode_ref,
        start_date,
        end_date,
        ou_loc_ref
    FROM datascope_gestor_prod.movements
    WHERE year(start_date) = {year}
    ORDER BY start_date
    LIMIT {probe_limit}
    """


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evalua si Metabase sigue aplicando un truncado silencioso "
            f"de {METABASE_SILENT_ROW_CAP} filas."
        )
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Año a evaluar sobre la tabla movements (por defecto: 2024).",
    )
    parser.add_argument(
        "--probe-limit",
        type=int,
        default=5000,
        help=(
            "Filas solicitadas en la query de prueba. Debe ser > 2000 "
            "(por defecto: 5000)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.probe_limit <= METABASE_SILENT_ROW_CAP:
        print(
            "ERROR: --probe-limit debe ser mayor que "
            f"{METABASE_SILENT_ROW_CAP}."
        )
        return 2

    print("1) Calculando total real de filas...")
    count_df = execute_query(build_count_query(args.year), verbose=False)
    total_rows = int(count_df.iloc[0]["total_rows"]) if not count_df.empty else 0
    print(f"   Total real (COUNT(*)): {total_rows}")

    print("2) Ejecutando query de prueba con LIMIT alto...")
    probe_df = execute_query(build_probe_query(args.year, args.probe_limit), verbose=False)
    returned_rows = len(probe_df)
    print(f"   Filas devueltas por API: {returned_rows}")
    print(f"   Límite solicitado en query: {args.probe_limit}")
    print(f"   Cap esperado históricamente: {METABASE_SILENT_ROW_CAP}")

    print("\nDiagnóstico:")
    if total_rows <= METABASE_SILENT_ROW_CAP:
        print(
            "- El conjunto del año probado no supera 2000 filas; "
            "no permite confirmar truncado."
        )
        print("- Prueba con otro año/filtro que tenga más volumen.")
        return 0

    if returned_rows == METABASE_SILENT_ROW_CAP and total_rows > METABASE_SILENT_ROW_CAP:
        print("- PROBABLE TRUNCADO: la API devuelve exactamente 2000 filas.")
        print("- Conclusión: el límite silencioso sigue activo.")
        return 1

    if returned_rows > METABASE_SILENT_ROW_CAP:
        print("- SIN TRUNCADO A 2000: se han recibido más de 2000 filas.")
        print("- Conclusión: el tope histórico parece no aplicarse en esta prueba.")
        return 0

    print("- Resultado no concluyente.")
    print("- Ajusta el filtro o aumenta --probe-limit para repetir la validación.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
