import sys
import os
from pathlib import Path

# Add root to path to import connection.py
# Assuming this script is in the 'test' directory, root is the parent.
root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

try:
    from connection import execute_query
except ImportError as e:
    print(f"Error: Could not import 'execute_query' from 'connection.py'.")
    print(f"Ensure connection.py is in {root_path}")
    print(f"Details: {e}")
    sys.exit(1)

def run_sql_file(file_path):
    """Reads a .sql file and executes the query using connection.py."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    print(f"--- Reading SQL file: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            query = f.read().strip()
            
        if not query:
            print("Error: The SQL file is empty.")
            return

        # Execute query
        df = execute_query(query)
        
        # Display results
        if df is not None and not df.empty:
            print("\n--- Query Results (First 5 rows) ---")
            print(df.head().to_string())
            print(f"\nTotal rows returned: {len(df)}")
        else:
            print("\nQuery executed successfully, but returned no results.")
        df.to_csv(file_path.with_suffix('.csv'), index=False)
        print(f"\nResults saved to: {file_path.with_suffix('.csv')}")
            
    except Exception as e:
        print(f"\nFailed to execute query:\n{e}")

if __name__ == "__main__":
    # If a filename is passed as argument, use it. Otherwise use query.sql in the same folder.
    if len(sys.argv) > 1:
        target_file = Path(sys.argv[1])
    else:
        print("No filename passed as argument. Please pass a filename as argument.")
        print("Usage: python run_sql.py <filename>")
        print("Available files:")
        print("  - camicu_compliance.sql")
        print("  - camicu_positivity.sql")
        print("  - camicu_daily_coverage.sql")
        print("  - camicu_plots.py")
        sys.exit(1)
    run_sql_file(target_file)
