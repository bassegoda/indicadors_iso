# Cross-platform connection to be stored in each project root directory

import os
import time
import mysql.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

def find_onedrive_path():
    """
    Encuentra la ruta de OneDrive en Windows o Mac.
    Busca en múltiples ubicaciones comunes.
    """
    home_dir = Path.home()
    system = os.name
    
    # Windows
    if system == 'nt':
        # Opción 1: Variable de entorno OneDrive
        onedrive_env = os.getenv('OneDrive') or os.getenv('OneDriveCommercial')
        if onedrive_env:
            onedrive_path = Path(onedrive_env)
            if onedrive_path.exists():
                return onedrive_path
        
        # Opción 2: Buscar en el perfil del usuario
        possible_paths = [
            home_dir / 'OneDrive',
            home_dir / 'OneDrive - Hospital Clínic de Barcelona',
            Path(os.getenv('USERPROFILE', '')) / 'OneDrive',
            Path(os.getenv('USERPROFILE', '')) / 'OneDrive - Hospital Clínic de Barcelona',
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
    
    # macOS
    else:
        # Opción 1: CloudStorage (OneDrive moderno en macOS)
        cloud_storage = home_dir / 'Library' / 'CloudStorage'
        if cloud_storage.exists():
            for item in cloud_storage.iterdir():
                if 'OneDrive' in item.name:
                    return item
        
        # Opción 2: OneDrive directo en home
        possible_paths = [
            home_dir / 'OneDrive',
            home_dir / 'OneDrive - Hospital Clínic de Barcelona',
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
    
    return None

def get_env_path():
    """
    Busca el archivo .env en la raíz de OneDrive.
    """
    onedrive_path = find_onedrive_path()
    
    if not onedrive_path:
        raise FileNotFoundError(
            "No se pudo encontrar la carpeta de OneDrive.\n"
            "Por favor, asegúrate de que OneDrive esté instalado y configurado.\n"
            "O crea el archivo .env manualmente en la raíz de OneDrive."
        )
    
    env_path = onedrive_path / '.env'
    
    if not env_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo .env en: {env_path}\n"
            f"Por favor, crea el archivo .env en la raíz de OneDrive con las siguientes variables:\n"
            f"DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE, DB_PORT"
        )
    
    return env_path

def get_connection(db_name=None):
    """Returns a MySQL connection with credentials from .env file"""
    env_path = get_env_path()
    load_dotenv(env_path)
    
    # Obtener valores del .env
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_DATABASE', db_name)
    port = int(os.getenv('DB_PORT', '3306'))
    
    # Validar que existen los valores requeridos
    required = {
        'DB_HOST': host,
        'DB_USER': user,
        'DB_PASSWORD': password,
        'DB_DATABASE': database
    }
    missing = [k for k, v in required.items() if not v]
    
    if missing:
        raise ValueError(
            f"Faltan las siguientes variables en {env_path}:\n"
            f"{', '.join(missing)}\n"
            f"Por favor, añade estas variables al archivo .env"
        )
    
    # Create MySQL connection
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port
    )
    
    return conn


def execute_query(query):
    """Executes a SELECT query and returns a pandas dataframe"""
    print("Executing query...")
    start_time = time.time()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        df = pd.DataFrame(results) if results else pd.DataFrame()
            
        execution_time = time.time() - start_time
        print(f"Query executada correctament en {execution_time:.2f} segons")
        return df
    except Exception as e:
        print(f"Error executing query: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        