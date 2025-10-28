# Cross-platform connection to be stored in each project root directory

import platform
import configparser
import time
import mysql.connector
import pandas as pd
import os

def get_config_path():
    """Sets the path to the config.init file which should be in the Documents folder
    inside a .sql_connection directory
    """
    if platform.system() == 'Windows':
        # Primer path hardcodejat de PC ANACONDA
        path1 = r"C:\Users\User\Documents\.sql_config\config.ini"
        # Segon path hardcodejat Clínic
        path2 = r"C:\Users\bassegoda\Documents\.sql_config\config.ini"
        # Determinar quina ruta existeix
        if os.path.exists(path1):
            return path1
        elif os.path.exists(path2):
            return path2
    else:  # Path hardcodejat per Mac
        return "/Users/octavi/Documents/.sql_config/config.ini"
    

def get_connection(db_name=None):
    """Returns a MySQL connection with credentials from config file"""
    config = configparser.ConfigParser()
    config.read(get_config_path())
    
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
        