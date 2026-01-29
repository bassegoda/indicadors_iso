"""
Import All Dictionary Tables from Database
==========================================
Interactive script to download dictionary tables from DataNex database,
fix encoding issues, and save them as local CSV files.

Available dictionaries:
- dic_diagnostic: Diagnosis codes
- dic_lab: Laboratory parameters
- dic_ou_loc: Physical hospitalization units
- dic_ou_med: Medical organizational units
- dic_rc: Clinical records
- dic_rc_text: Clinical records text values
"""

from pathlib import Path
import sys
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from connection import execute_query


# Dictionary definitions: table_name -> (output_filename, columns)
DICTIONARIES = {
    'dic_diagnostic': {
        'filename': 'diagnostic_dictionary.csv',
        'query': 'SELECT diag_ref, catalog, code, diag_descr FROM dic_diagnostic ORDER BY diag_ref',
        'text_columns': ['diag_descr']
    },
    'dic_lab': {
        'filename': 'lab_dictionary.csv',
        'query': 'SELECT lab_sap_ref, lab_descr, units, lab_ref FROM dic_lab ORDER BY lab_sap_ref',
        'text_columns': ['lab_descr', 'units']
    },
    'dic_ou_loc': {
        'filename': 'ou_loc_dictionary.csv',
        'query': 'SELECT ou_loc_ref, ou_loc_descr, care_level_type_ref, facility_ref, facility_descr FROM dic_ou_loc ORDER BY ou_loc_ref',
        'text_columns': ['ou_loc_descr', 'facility_descr']
    },
    'dic_ou_med': {
        'filename': 'ou_med_dictionary.csv',
        'query': 'SELECT ou_med_ref, ou_med_descr FROM dic_ou_med ORDER BY ou_med_ref',
        'text_columns': ['ou_med_descr']
    },
    'dic_rc': {
        'filename': 'rc_dictionary.csv',
        'query': 'SELECT rc_sap_ref, rc_descr, units, rc_ref FROM dic_rc ORDER BY rc_sap_ref',
        'text_columns': ['rc_descr', 'units']
    },
    'dic_rc_text': {
        'filename': 'rc_text_dictionary.csv',
        'query': 'SELECT rc_sap_ref, result_txt, descr FROM dic_rc_text ORDER BY rc_sap_ref, result_txt',
        'text_columns': ['result_txt', 'descr']
    }
}


def fix_encoding(text):
    """
    Fix double-encoded UTF-8 text.
    
    Args:
        text: String that may be incorrectly encoded
        
    Returns:
        Corrected string
    """
    if pd.isna(text):
        return text
    
    try:
        # Try to fix double encoding (latin-1 -> utf-8)
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # If it fails, return original text
        return text


def import_dictionary(table_name, config):
    """
    Import a single dictionary table from database.
    
    Args:
        table_name: Name of the dictionary table
        config: Dictionary configuration with query and text columns
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"IMPORTING: {table_name}")
    print(f"{'='*80}")
    
    # Execute query
    print(f">>> Executing query...")
    df = execute_query(config['query'])
    
    if df is None or df.empty:
        print(f"❌ Error: No data retrieved from {table_name}")
        return False
    
    print(f"✓ Retrieved {len(df):,} records")
    
    # Fix encoding issues in text columns
    print(f">>> Fixing encoding issues...")
    encoding_fixed = False
    
    for col in config['text_columns']:
        if col in df.columns:
            # Check if encoding needs fixing (sample first non-null value)
            sample_idx = df[col].first_valid_index()
            if sample_idx is not None:
                original_sample = df[col].loc[sample_idx]
                df[col] = df[col].apply(fix_encoding)
                fixed_sample = df[col].loc[sample_idx]
                
                if original_sample != fixed_sample:
                    encoding_fixed = True
                    print(f"  • Column '{col}': encoding fixed")
                    print(f"    Before: {original_sample}")
                    print(f"    After:  {fixed_sample}")
    
    if not encoding_fixed:
        print("  • No encoding issues detected")
    
    # Save to CSV with UTF-8 encoding
    output_path = Path(__file__).parent / config['filename']
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"\n✓ Dictionary saved to: {output_path.name}")
    print(f"✓ Total records: {len(df):,}")
    
    # Show sample entries (first 5 rows)
    print(f"\n{'─'*80}")
    print("Sample entries (first 5 rows):")
    print(f"{'─'*80}")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)
    print(df.head(5).to_string(index=False))
    
    return True


def show_menu():
    """Display interactive menu."""
    print("\n" + "="*80)
    print("DATANEX DICTIONARY IMPORTER")
    print("="*80)
    print("\nAvailable dictionaries:")
    print()
    
    for i, (table_name, config) in enumerate(DICTIONARIES.items(), 1):
        print(f"  {i}. {table_name:20} → {config['filename']}")
    
    print(f"\n  {len(DICTIONARIES)+1}. ALL DICTIONARIES")
    print(f"  0. Exit")
    print()


def get_user_choice():
    """Get and validate user choice."""
    while True:
        try:
            choice = input("Select option (0-7): ").strip()
            choice_num = int(choice)
            
            if 0 <= choice_num <= len(DICTIONARIES) + 1:
                return choice_num
            else:
                print(f"❌ Invalid option. Please enter a number between 0 and {len(DICTIONARIES)+1}")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def confirm_action(message):
    """Ask for user confirmation."""
    while True:
        response = input(f"\n{message} (y/n): ").strip().lower()
        if response in ['y', 'yes', 's', 'si', 'sí']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("❌ Please answer 'y' (yes) or 'n' (no)")


def main():
    """Main execution function."""
    show_menu()
    choice = get_user_choice()
    
    if choice == 0:
        print("\n👋 Exiting without changes.")
        return
    
    # Determine which dictionaries to import
    if choice == len(DICTIONARIES) + 1:
        # Import all dictionaries
        if not confirm_action("⚠️  This will download ALL dictionary tables. Continue?"):
            print("\n❌ Operation cancelled by user.")
            return
        
        dictionaries_to_import = list(DICTIONARIES.items())
    else:
        # Import single dictionary
        table_name = list(DICTIONARIES.keys())[choice - 1]
        config = DICTIONARIES[table_name]
        
        if not confirm_action(f"Download {table_name} → {config['filename']}?"):
            print("\n❌ Operation cancelled by user.")
            return
        
        dictionaries_to_import = [(table_name, config)]
    
    # Import selected dictionaries
    print("\n" + "="*80)
    print("STARTING IMPORT PROCESS")
    print("="*80)
    
    success_count = 0
    fail_count = 0
    
    for table_name, config in dictionaries_to_import:
        try:
            if import_dictionary(table_name, config):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"\n❌ Error importing {table_name}: {e}")
            fail_count += 1
    
    # Summary
    print("\n" + "="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"✓ Successfully imported: {success_count} dictionaries")
    if fail_count > 0:
        print(f"❌ Failed imports: {fail_count} dictionaries")
    print("\n" + "="*80)
    print("PROCESS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user (Ctrl+C)")
        sys.exit(0)
