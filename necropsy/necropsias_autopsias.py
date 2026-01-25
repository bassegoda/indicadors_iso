"""
Análisis de provisions de necropsias y autopsias
Busca en el diccionario términos relacionados y consulta la base de datos
"""

import sys
from pathlib import Path
import pandas as pd

# Setup paths
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from connection import execute_query

# Configurar carpeta de output
OUTPUT_DIR = current_file.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Ruta al diccionario
DICT_PATH = project_root / "docs" / "dictionaries" / "dic_provisions.csv"

def load_provisions_dict():
    """Carga el diccionario de provisions"""
    try:
        df = pd.read_csv(DICT_PATH, encoding='utf-8')
        return df
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el diccionario en {DICT_PATH}")
        print("   Ejecuta primero: python docs/dictionaries/generate_provisions_dict.py")
        sys.exit(1)

def find_necropsia_autopsia_codes(df_dict):
    """Busca códigos relacionados con necropsias y autopsias en el diccionario"""
    
    # Términos a buscar (case-insensitive)
    search_terms = [
        'necrops',
        'autops',
        'autòps',
        'necòps',
        'post-mortem',
        'postmortem'
    ]
    
    # Filtrar el diccionario
    mask = df_dict['prov_descr'].str.lower().str.contains('|'.join(search_terms), case=False, na=False)
    matching_codes = df_dict[mask].copy()
    
    return matching_codes

def get_necropsias_by_year(year, prov_refs):
    """Obtiene todas las provisions de necropsias/autopsias de un año"""
    
    # Formatear lista de códigos para SQL
    prov_refs_formatted = ", ".join([f"'{ref}'" for ref in prov_refs])
    
    query = f"""
    SELECT 
        prov_ref,
        prov_descr,
        level_1_ref,
        level_1_descr,
        level_2_ref,
        level_2_descr,
        level_3_ref,
        level_3_descr,
        category,
        start_date,
        end_date,
        ou_med_ref_order,
        ou_med_ref_exec,
        start_date_plan,
        end_date_plan
    FROM g_provisions
    WHERE prov_ref IN ({prov_refs_formatted})
      AND YEAR(start_date) = {year}
    ORDER BY start_date;
    """
    
    return execute_query(query)

def main():
    print("=" * 80)
    print("  ANÁLISIS DE NECROPSIAS Y AUTOPSIAS")
    print("=" * 80)
    
    # 1. Cargar diccionario
    print("\n>>> Cargando diccionario de provisions...")
    df_dict = load_provisions_dict()
    print(f"✓ Diccionario cargado: {len(df_dict)} provisions")
    
    # 2. Buscar códigos relacionados
    print("\n>>> Buscando códigos de necropsias/autopsias en el diccionario...")
    matching_codes = find_necropsia_autopsia_codes(df_dict)
    
    if matching_codes.empty:
        print("❌ No se encontraron códigos relacionados con necropsias/autopsias")
        return
    
    print(f"✓ Encontrados {len(matching_codes)} códigos relacionados:")
    print("\n" + "-" * 80)
    for _, row in matching_codes.iterrows():
        print(f"  {row['prov_ref']:15} | {row['prov_descr']}")
    print("-" * 80)
    
    # 3. Solicitar año
    print("\n>>> Selección de año")
    year = input("Año a analizar (ej: 2024): ").strip()
    
    if not year.isdigit():
        print("❌ Error: Debe introducir un año válido")
        return
    
    year = int(year)
    
    # 4. Obtener provisions del año
    print(f"\n>>> Consultando provisions de necropsias/autopsias del año {year}...")
    prov_refs = matching_codes['prov_ref'].tolist()
    df_results = get_necropsias_by_year(year, prov_refs)
    
    if df_results.empty:
        print(f"✓ No se encontraron provisions de necropsias/autopsias en {year}")
        return
    
    print(f"✓ Encontradas {len(df_results)} provisions")
    
    # 5. Mostrar resumen
    print("\n" + "=" * 80)
    print(f"  RESUMEN - AÑO {year}")
    print("=" * 80)
    
    # Resumen por tipo
    print(f"\n>>> Por tipo de provisión:")
    summary = df_results.groupby('prov_ref').agg({
        'prov_descr': 'first',
        'start_date': 'count'
    }).rename(columns={'start_date': 'cantidad'}).sort_values('cantidad', ascending=False)
    
    for prov_ref, row in summary.iterrows():
        print(f"  {prov_ref:15} | {row['prov_descr']:50} | {int(row['cantidad'])} casos")
    
    # Resumen por mes
    print(f"\n>>> Por mes:")
    df_results['month'] = pd.to_datetime(df_results['start_date']).dt.month
    monthly = df_results.groupby('month').size()
    for month, count in monthly.items():
        month_name = pd.to_datetime(f"2024-{month:02d}-01").strftime('%B')
        print(f"  {month_name:15} | {count} casos")
    
    # 6. Mostrar detalle (primeras 20)
    print(f"\n>>> Detalle (primeras 20 de {len(df_results)}):")
    print("-" * 120)
    df_display = df_results.head(20).copy()
    df_display['start_date'] = pd.to_datetime(df_display['start_date']).dt.strftime('%Y-%m-%d %H:%M')
    df_display['end_date'] = pd.to_datetime(df_display['end_date']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Seleccionar columnas relevantes para mostrar
    display_cols = ['prov_ref', 'prov_descr', 'start_date', 'end_date', 'ou_med_ref_order', 'ou_med_ref_exec']
    display_cols = [col for col in display_cols if col in df_display.columns]
    print(df_display[display_cols].to_string(index=False))
    
    if len(df_results) > 20:
        print(f"\n  ... y {len(df_results) - 20} provisions más")
    
    # 7. Guardar resultados (sin datos identificativos)
    print(f"\n>>> Guardando resultados...")
    df_safe = df_results.drop(columns=['patient_ref', 'episode_ref'], errors='ignore')
    output_path = OUTPUT_DIR / f"necropsias_autopsias_{year}.csv"
    df_safe.to_csv(output_path, index=False, encoding='utf-8')
    print(f"✓ Resultados guardados en: {output_path}")
    print(f"  Total de registros: {len(df_safe)}")

if __name__ == "__main__":
    main()
