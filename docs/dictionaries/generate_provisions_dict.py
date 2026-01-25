"""
Script para generar el diccionario de provisions (dic_provisions.csv)
Extrae los valores únicos de prov_ref y prov_descr de la tabla g_provisions
"""

import sys
from pathlib import Path

# Setup paths
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.append(str(project_root))

from connection import execute_query

# Output path
output_path = current_file.parent / "dic_provisions.csv"

# Query para extraer valores únicos de prov_ref y prov_descr
query = """
SELECT DISTINCT
    prov_ref,
    prov_descr
FROM g_provisions
WHERE prov_ref IS NOT NULL
  AND prov_descr IS NOT NULL
ORDER BY prov_ref;
"""

print("Generando diccionario de provisions...")
print(f"Ejecutando query en g_provisions...")

df = execute_query(query)

if df.empty:
    print("⚠️  No se encontraron datos en g_provisions")
else:
    print(f"✓ Encontrados {len(df)} registros únicos")
    
    # Guardar CSV
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"✓ Diccionario guardado en: {output_path}")
    print(f"  Columnas: {', '.join(df.columns.tolist())}")
    print(f"  Total de provisions únicas: {len(df)}")
