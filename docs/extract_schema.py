# This script extracts the schema of the database and saves it to a text file
# dic_ tables are excluded

import sys
from pathlib import Path
import mysql.connector

# Añadir directorio raíz al path para importar connection
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from connection import get_connection

# Definir ruta de salida
script_dir = Path(__file__).parent
output_dir = script_dir / 'output'
output_dir.mkdir(exist_ok=True)
OUTPUT_TXT = output_dir / 'schema_documentation.txt'

try:
    # Usar connection.py para obtener la conexión (lee credenciales del .env)
    conn = get_connection()
    cursor = conn.cursor()
    
    # Obtener el nombre de la base de datos desde la conexión
    cursor.execute("SELECT DATABASE()")
    database_name = cursor.fetchone()[0]
    
    # Obtener vistas y columnas (excluyendo tablas que empiezan por 'dic_')
    query = """
    SELECT 
        t.TABLE_NAME,
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.COLUMN_TYPE,
        c.IS_NULLABLE
    FROM information_schema.COLUMNS c
    JOIN information_schema.TABLES t 
        ON c.TABLE_NAME = t.TABLE_NAME 
        AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
    WHERE t.TABLE_TYPE = 'VIEW' 
      AND t.TABLE_SCHEMA = %s
      AND t.TABLE_NAME NOT LIKE 'dic_%'
    ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION;
    """
    
    cursor.execute(query, (database_name,))
    results = cursor.fetchall()

    # Preparar encabezado
    txt_lines = [
        f"DATABASE DOCUMENTATION: {database_name}",
        "=" * 50,
        "Generated via Python Auto-Discovery",
        ""
    ]

    # Agrupar columnas por vista
    current_view = None
    for row in results:
        view_name, col_name, data_type, full_type, is_nullable = row
        
        # Nueva vista
        if view_name != current_view:
            if current_view is not None:
                txt_lines.append("\n")
            
            txt_lines.append(f"VIEW: {view_name}")
            txt_lines.append("-" * 50)
            txt_lines.append(f"{'Column Name':<30} | {'Type':<20} | {'Null?'}")
            txt_lines.append("-" * 65)
            current_view = view_name
        
        # Añadir columna
        null_str = "YES" if is_nullable == 'YES' else "NO"
        txt_lines.append(f"{col_name:<30} | {full_type:<20} | {null_str}")

    # Guardar archivo TXT
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write("\n".join(txt_lines))
    
    print(f"✅ Documentation saved to {OUTPUT_TXT}")

except mysql.connector.Error as err:
    print(f"❌ Database Error: {err}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()