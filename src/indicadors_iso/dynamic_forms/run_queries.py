#!/usr/bin/env python3
"""
Ejecutar queries SQL contra la base de datos DataNex desde la carpeta dynamic_forms.

Las queries se almacenan como archivos .sql en dynamic_forms/queries/.
Los resultados se pueden guardar en dynamic_forms/output/.

Uso:
  python run_queries.py --list             # Lista queries disponibles
  python run_queries.py --query ingresos_otro_centro   # Ejecuta y guarda CSV
  python run_queries.py --all              # Ejecuta todas y guarda CSV
  python run_queries.py --query X --no-save  # Ejecuta sin guardar CSV
"""

import argparse
import sys
from pathlib import Path

# Añadir raíz del proyecto para importar connection
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Rutas
DYNAMIC_FORMS_DIR = Path(__file__).resolve().parent
QUERIES_DIR = DYNAMIC_FORMS_DIR / "queries"
OUTPUT_DIR = DYNAMIC_FORMS_DIR / "output"


def get_available_queries():
    """Devuelve lista de archivos .sql en queries/ ordenados por nombre."""
    if not QUERIES_DIR.exists():
        return []
    return sorted(QUERIES_DIR.glob("*.sql"))


def get_query_name(sql_path: Path) -> str:
    """Nombre de la query sin extensión (para --query y nombres de archivo)."""
    return sql_path.stem


def run_query(sql_path: Path, verbose: bool = True):
    """Ejecuta una query SQL y devuelve el DataFrame."""
    from connection import execute_query

    sql = sql_path.read_text(encoding="utf-8")
    return execute_query(sql, verbose=verbose)


def main():
    parser = argparse.ArgumentParser(
        description="Ejecutar queries de dynamic forms contra la base de datos"
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        help="Nombre de la query a ejecutar (sin .sql). Ej: explorar_uci",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Ejecutar todas las queries disponibles",
    )
    parser.add_argument(
        "--save",
        "-s",
        action="store_true",
        default=True,
        help="Guardar resultados en output/ como CSV (por defecto: sí)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="No guardar CSV, solo mostrar por consola",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Listar queries disponibles y salir",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Menos salida por consola",
    )
    args = parser.parse_args()
    save_csv = args.save and not args.no_save

    # Crear directorio de queries si no existe
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    queries = get_available_queries()
    if not queries:
        print(f"No se encontraron archivos .sql en {QUERIES_DIR}")
        print("Crea archivos .sql en esa carpeta para ejecutarlos.")
        return 1

    if args.list:
        print("Queries disponibles:")
        for q in queries:
            print(f"  - {get_query_name(q)}")
        return 0

    # Determinar qué queries ejecutar
    if args.all:
        to_run = queries
    elif args.query:
        name = args.query.strip().lower()
        # Coincidencia exacta primero, luego por contenido
        matches = [q for q in queries if get_query_name(q).lower() == name]
        if not matches:
            matches = [q for q in queries if name in get_query_name(q).lower()]
        if not matches:
            print(f"Query '{args.query}' no encontrada.")
            print("Disponibles:", ", ".join(get_query_name(q) for q in queries))
            return 1
        to_run = matches
    else:
        print("Usa --query <nombre> para ejecutar una query o --all para todas.")
        print("Usa --list para ver las disponibles.")
        return 0

    verbose = not args.quiet
    for sql_path in to_run:
        name = get_query_name(sql_path)
        if verbose:
            print(f"\n{'='*60}")
            print(f"Query: {name}")
            print("=" * 60)

        try:
            df = run_query(sql_path, verbose=verbose)
            if verbose:
                print(f"Filas: {len(df)}")

            if save_csv:
                out_path = OUTPUT_DIR / f"{name}.csv"
                df.to_csv(out_path, index=False, encoding="utf-8-sig")
                if verbose:
                    print(f"Guardado: {out_path} ({len(df)} filas)")
        except Exception as e:
            print(f"Error en {name}: {e}")
            if not args.all:
                raise
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
