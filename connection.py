# connection.py - Versión simplificada centrada en OneDrive
import os
import time
import mysql.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH_CACHE = None

def get_env_path():
    """Busca el archivo .env exclusivamente en OneDrive (Windows/macOS)."""
    global _ENV_PATH_CACHE
    if _ENV_PATH_CACHE is not None:
        return _ENV_PATH_CACHE

    home = Path.home()
    
    # Intento 1: Variables de entorno de Windows (OneDrive / OneDriveCommercial)
    if os.name == 'nt':
        for env_var in ('OneDrive', 'OneDriveCommercial'):
            p = os.getenv(env_var)
            if p:
                path = Path(p) / '.env'
                if path.exists():
                    _ENV_PATH_CACHE = path
                    return path
    
    # Intento 2: Ruta estándar de macOS (CloudStorage)
    else:
        cloud = home / 'Library' / 'CloudStorage'
        if cloud.exists():
            for s_path in cloud.iterdir():
                if 'OneDrive' in s_path.name:
                    path = s_path / '.env'
                    if path.exists():
                        _ENV_PATH_CACHE = path
                        return path

    # Intento 3: Ruta genérica ~/OneDrive/.env (Ambos)
    path = home / 'OneDrive' / '.env'
    if path.exists():
        _ENV_PATH_CACHE = path
        return path

    raise FileNotFoundError("¡Error! No se encontró el archivo .env en tu OneDrive. Verifica que esté sincronizado.")

def get_connection(db_name=None):
    """Carga credenciales desde el .env de OneDrive y conecta a MySQL."""
    load_dotenv(get_env_path())
    
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_DATABASE', db_name)
    port = int(os.getenv('DB_PORT', '3306'))

    if not all([host, user, password]):
        raise ValueError("Faltan credenciales en el archivo .env de OneDrive.")

    return mysql.connector.connect(
        host=host, user=user, password=password, database=database, port=port,
        charset='utf8mb4', use_unicode=True
    )

def execute_query(query, verbose=True):
    """Ejecuta una consulta SELECT y devuelve un DataFrame de pandas."""
    if verbose:
        print("Ejecutando query...")
    start = time.time()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if verbose:
            print(f"Éxito en {time.time() - start:.2f}s")
        return df
    except Exception as e:
        if verbose:
            print(f"Error al ejecutar query: {e}")
        raise
    finally:
        cur.close()
        conn.close()

