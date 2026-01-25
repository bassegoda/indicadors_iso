import sys
from pathlib import Path

# 1. Setup Project Root using Pathlib (Clean & Modern)
# Assuming this script is inside a folder one level deep (e.g., /scripts/myscript.py)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from connection import execute_query as eq

# 2. Paths
micro_file_path = project_root / "micro" / "micro.sql"
antibiogram_file_path = project_root / "micro" / "antibiogram.sql"
output_dir = current_file.parent / "output"
output_dir.mkdir(exist_ok=True)

# 3. micro export
try:
    with open(micro_file_path, "r", encoding="utf-8") as file:
        query = file.read()
    df = eq(query)
    print(f"Length of micro data: {len(df)}")
    # Eliminar datos identificativos antes de guardar
    df_safe = df.drop(columns=['patient_ref', 'episode_ref'], errors='ignore')
    df_safe.to_csv(output_dir / "micro_data.csv", index=False)
except FileNotFoundError:
    print(f"Error: Could not find micro sql file at {micro_file_path}")
    sys.exit(1)

# 4. antibiogram export
try:
    with open(antibiogram_file_path, "r", encoding="utf-8") as file:
        query = file.read()
    df = eq(query)
    print(f"Length of antibiogram data: {len(df)}")
    # Eliminar datos identificativos antes de guardar
    df_safe = df.drop(columns=['patient_ref', 'episode_ref'], errors='ignore')
    df_safe.to_csv(output_dir / "antibiogram_data.csv", index=False)
except FileNotFoundError:
    print(f"Error: Could not find antibiogram sql file at {antibiogram_file_path}")
    sys.exit(1)