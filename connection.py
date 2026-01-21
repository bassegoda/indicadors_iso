# Cross-platform connection to be stored in each project root directory

import platform
import configparser
import time
import mysql.connector
import pandas as pd
import os

def get_config_path():
    """Sets the path to the config.init file which should be in the Documents folder
    inside a .sql_config directory
    """
    home_dir = os.path.expanduser('~')
    config_path = os.path.join(home_dir, 'Documents', '.sql_config', 'config.ini')
    
    if os.path.exists(config_path):
        return config_path
    else:
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración en: {config_path}\n"
            f"Por favor, crea el archivo con las credenciales de la base de datos."
        )
    

def get_connection(db_name=None):
    """Returns a MySQL connection with credentials from config file"""
    config_path = get_config_path()
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Verificar que el archivo tiene las claves necesarias
    if 'DEFAULT' not in config:
        raise KeyError(f"El archivo de configuración {config_path} no tiene una sección [DEFAULT]")
    
    required_keys = ['host', 'user', 'password', 'database']
    missing_keys = [key for key in required_keys if key not in config['DEFAULT']]
    if missing_keys:
        raise KeyError(f"El archivo de configuración {config_path} no tiene las siguientes claves: {', '.join(missing_keys)}")
    
    # Create MySQL connection
    conn = mysql.connector.connect(
        host=config['DEFAULT']['host'],
        user=config['DEFAULT']['user'],
        password=config['DEFAULT']['password'],
        database=db_name or config['DEFAULT']['database'],
        port=3306
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
        