# Cross-platform MySQL connection. Place in project root with .env or use OneDrive/CWD fallback.

import os
import time
import mysql.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH_CACHE = None

def _find_onedrive_path():
    """Find OneDrive path on Windows or macOS."""
    home = Path.home()
    if os.name == 'nt':
        for env_var in ('OneDrive', 'OneDriveCommercial'):
            p = os.getenv(env_var)
            if p and (path := Path(p)).exists():
                return path
        for name in ('OneDrive',):
            if (path := home / name).exists():
                return path
        if userprofile := os.getenv('USERPROFILE'):
            if (path := Path(userprofile) / 'OneDrive').exists():
                return path
    else:
        cloud = home / 'Library' / 'CloudStorage'
        if cloud.exists():
            for item in cloud.iterdir():
                if 'OneDrive' in item.name:
                    return item
        if (path := home / 'OneDrive').exists():
            return path
    return None

def get_env_path():
    """Find .env: project root → OneDrive → CWD."""
    global _ENV_PATH_CACHE
    if _ENV_PATH_CACHE is not None:
        return _ENV_PATH_CACHE

    candidates = [
        Path(__file__).resolve().parent / '.env',
        Path.cwd() / '.env',
    ]
    onedrive = _find_onedrive_path()
    if onedrive:
        candidates.insert(1, onedrive / '.env')

    for env_path in candidates:
        if env_path.exists() and env_path.is_file():
            _ENV_PATH_CACHE = env_path
            return env_path

    raise FileNotFoundError(
        ".env not found. Searched: project root, OneDrive, CWD.\n"
        "Create .env with: DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE, DB_PORT"
    )

def get_connection(db_name=None):
    """Return MySQL connection with credentials from .env."""
    load_dotenv(get_env_path())
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_DATABASE', db_name)
    port = int(os.getenv('DB_PORT', '3306'))

    missing = [k for k, v in [('DB_HOST', host), ('DB_USER', user),
              ('DB_PASSWORD', password), ('DB_DATABASE', database)] if not v]
    if missing:
        raise ValueError(f"Missing in .env: {', '.join(missing)}")

    return mysql.connector.connect(
        host=host, user=user, password=password, database=database, port=port,
        charset='utf8mb4', use_unicode=True
    )

def execute_query(query, verbose=True):
    """Execute SELECT and return pandas DataFrame."""
    if verbose:
        print("Executing query...")
    start = time.time()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if verbose:
            print(f"Query executed successfully in {time.time() - start:.2f} seconds")
        return df
    except Exception as e:
        if verbose:
            print(f"Error executing query: {e}")
        raise
    finally:
        cur.close()
        conn.close()
