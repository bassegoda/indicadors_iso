"""
Import Treatment Dictionaries from Database
===========================================
Generates useful dictionaries from treatment-related tables (g_prescriptions,
g_administrations, g_perfusions) by extracting unique values with their descriptions.

This script creates consolidated dictionaries for:
1. Drugs (drug_ref, drug_descr, atc_ref, atc_descr)
2. ATC codes (atc_ref, atc_descr)
3. Administration routes (route_ref, route_descr)
4. Pharmaceutical forms (phform_ref, phform_descr)
5. Frequencies (freq_ref)
6. Dose units (quantity_unit)
"""

from pathlib import Path
import sys
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from connection import execute_query


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
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def create_drug_dictionary():
    """
    Create comprehensive drug dictionary with ATC codes.
    Combines data from g_prescriptions and g_administrations.
    """
    print("\n" + "="*80)
    print("CREATING DRUG DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            drug_ref,
            drug_descr,
            atc_ref,
            atc_descr
        FROM (
            SELECT drug_ref, drug_descr, atc_ref, atc_descr
            FROM g_prescriptions
            WHERE drug_ref IS NOT NULL
            
            UNION
            
            SELECT drug_ref, drug_descr, atc_ref, atc_descr
            FROM g_administrations
            WHERE drug_ref IS NOT NULL
        ) AS combined_drugs
        ORDER BY drug_descr, drug_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique drugs")
    
    # Fix encoding
    for col in ['drug_descr', 'atc_descr']:
        if col in df.columns:
            df[col] = df[col].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "drug_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def create_atc_dictionary():
    """
    Create ATC code dictionary (Anatomical Therapeutic Chemical Classification).
    """
    print("\n" + "="*80)
    print("CREATING ATC DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            atc_ref,
            atc_descr
        FROM (
            SELECT atc_ref, atc_descr
            FROM g_prescriptions
            WHERE atc_ref IS NOT NULL AND atc_descr IS NOT NULL
            
            UNION
            
            SELECT atc_ref, atc_descr
            FROM g_administrations
            WHERE atc_ref IS NOT NULL AND atc_descr IS NOT NULL
        ) AS combined_atc
        ORDER BY atc_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique ATC codes")
    
    # Fix encoding
    df['atc_descr'] = df['atc_descr'].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "atc_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def create_route_dictionary():
    """
    Create administration route dictionary.
    """
    print("\n" + "="*80)
    print("CREATING ADMINISTRATION ROUTE DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            route_ref,
            route_descr
        FROM (
            SELECT adm_route_ref AS route_ref, route_descr
            FROM g_prescriptions
            WHERE adm_route_ref IS NOT NULL AND route_descr IS NOT NULL
            
            UNION
            
            SELECT route_ref, route_descr
            FROM g_administrations
            WHERE route_ref IS NOT NULL AND route_descr IS NOT NULL
        ) AS combined_routes
        ORDER BY route_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique routes")
    
    # Fix encoding
    df['route_descr'] = df['route_descr'].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "route_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def create_phform_dictionary():
    """
    Create pharmaceutical form dictionary.
    """
    print("\n" + "="*80)
    print("CREATING PHARMACEUTICAL FORM DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            phform_ref,
            phform_descr
        FROM g_prescriptions
        WHERE phform_ref IS NOT NULL AND phform_descr IS NOT NULL
        ORDER BY phform_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique pharmaceutical forms")
    
    # Fix encoding
    df['phform_descr'] = df['phform_descr'].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "phform_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def create_frequency_dictionary():
    """
    Create frequency dictionary.
    """
    print("\n" + "="*80)
    print("CREATING FREQUENCY DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            freq_ref
        FROM g_prescriptions
        WHERE freq_ref IS NOT NULL
        ORDER BY freq_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique frequencies")
    
    # Fix encoding
    df['freq_ref'] = df['freq_ref'].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "frequency_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def create_unit_dictionary():
    """
    Create dose unit dictionary.
    """
    print("\n" + "="*80)
    print("CREATING DOSE UNIT DICTIONARY")
    print("="*80)
    
    query = """
        SELECT DISTINCT
            unit AS unit_ref
        FROM (
            SELECT unit
            FROM g_prescriptions
            WHERE unit IS NOT NULL
            
            UNION
            
            SELECT quantity_unit AS unit
            FROM g_administrations
            WHERE quantity_unit IS NOT NULL
        ) AS combined_units
        ORDER BY unit_ref
    """
    
    print(">>> Executing query...")
    df = execute_query(query)
    
    if df is None or df.empty:
        print("❌ Error: No data retrieved")
        return None
    
    print(f"✓ Retrieved {len(df):,} unique dose units")
    
    # Fix encoding
    df['unit_ref'] = df['unit_ref'].apply(fix_encoding)
    
    output_path = Path(__file__).parent / "unit_dictionary.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"✓ Saved to: {output_path.name}")
    
    return df


def show_samples(df, title, max_rows=10):
    """Display sample entries from a dictionary."""
    if df is None or df.empty:
        return
    
    print(f"\n{'─'*80}")
    print(f"{title} - Sample entries (first {min(max_rows, len(df))} rows):")
    print(f"{'─'*80}")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 60)
    print(df.head(max_rows).to_string(index=False))


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("TREATMENT DICTIONARIES GENERATOR")
    print("="*80)
    print("\nThis script will generate the following dictionaries:")
    print("  1. Drug dictionary (drug_ref, drug_descr, atc_ref, atc_descr)")
    print("  2. ATC dictionary (ATC classification codes)")
    print("  3. Administration route dictionary")
    print("  4. Pharmaceutical form dictionary")
    print("  5. Frequency dictionary")
    print("  6. Dose unit dictionary")
    print("\n⚠️  Note: These queries may take several minutes as they scan large tables.")
    
    # Ask for confirmation
    response = input("\nContinue? (y/n): ").strip().lower()
    if response not in ['y', 'yes', 's', 'si', 'sí']:
        print("\n❌ Operation cancelled by user.")
        return
    
    results = {}
    
    # Generate all dictionaries
    results['drug'] = create_drug_dictionary()
    results['atc'] = create_atc_dictionary()
    results['route'] = create_route_dictionary()
    results['phform'] = create_phform_dictionary()
    results['frequency'] = create_frequency_dictionary()
    results['unit'] = create_unit_dictionary()
    
    # Show samples
    print("\n" + "="*80)
    print("SAMPLE ENTRIES FROM GENERATED DICTIONARIES")
    print("="*80)
    
    if results['drug'] is not None:
        show_samples(results['drug'], "DRUG DICTIONARY", 5)
    
    if results['atc'] is not None:
        show_samples(results['atc'], "ATC DICTIONARY", 5)
    
    if results['route'] is not None:
        show_samples(results['route'], "ADMINISTRATION ROUTE", 5)
    
    if results['phform'] is not None:
        show_samples(results['phform'], "PHARMACEUTICAL FORM", 5)
    
    if results['frequency'] is not None:
        show_samples(results['frequency'], "FREQUENCY", 10)
    
    if results['unit'] is not None:
        show_samples(results['unit'], "DOSE UNIT", 10)
    
    # Summary
    print("\n" + "="*80)
    print("GENERATION SUMMARY")
    print("="*80)
    
    success = sum(1 for df in results.values() if df is not None)
    print(f"✓ Successfully created: {success}/6 dictionaries")
    
    for name, df in results.items():
        if df is not None:
            print(f"  • {name}_dictionary.csv: {len(df):,} entries")
    
    print("\n" + "="*80)
    print("PROCESS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user (Ctrl+C)")
        sys.exit(0)
