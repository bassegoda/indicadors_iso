"""
Análisis de nutrición enteral y parenteral
"""

import sys
from pathlib import Path
import pandas as pd

# Añadir el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from connection import execute_query

# Configurar carpeta de output
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Configuración de pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

def get_nutrition_query(start_date, end_date, unit_list):
    """Genera la query SQL para el análisis de nutrición"""
    # Generar la lista de unidades formateada para SQL
    units_formatted = ", ".join([f"'{u}'" for u in unit_list])
    
    query = f"""
    WITH movement_data AS (
        SELECT 
            m.patient_ref,
            m.episode_ref,
            m.start_date,
            m.end_date,
            TIMESTAMPDIFF(hour, m.start_date, m.end_date) AS horesingres,
            LEAD(m.start_date) OVER (PARTITION BY m.episode_ref ORDER BY m.start_date) AS next_start_date
        FROM
            g_movements AS m
        WHERE 
            m.ou_loc_ref IN ({units_formatted}) 
            AND m.start_date BETWEEN '{start_date} 00:00:00' AND '{end_date} 23:59:59'
            AND m.start_date != m.end_date
            AND TIMESTAMPDIFF(hour, m.start_date, m.end_date) > 1
    ),
    final_movements AS (
        SELECT 
            patient_ref,
            episode_ref,
            start_date,
            end_date
        FROM movement_data
        WHERE next_start_date IS NULL
           OR end_date != next_start_date
    ),
    nutrition_prescriptions AS (
        SELECT 
            pe.episode_ref,
            pe.start_drug_date,
            pe.drug_descr,
            ROW_NUMBER() OVER (PARTITION BY pe.episode_ref ORDER BY pe.start_drug_date ASC) AS rn
        FROM 
            g_prescriptions AS pe
        WHERE 
            pe.drug_descr IN ('NUTRICION ENTERAL', 'NUTRICIÓN PARENTERAL CENTRAL')
            AND pe.start_drug_date IS NOT NULL
    ),
    matched_nutrition AS (
        SELECT 
            fm.episode_ref,
            fm.start_date,
            np.start_drug_date,
            np.drug_descr,
            TIMESTAMPDIFF(hour, fm.start_date, np.start_drug_date) AS hours_difference
        FROM 
            final_movements fm
        INNER JOIN 
            nutrition_prescriptions np
        ON 
            fm.episode_ref = np.episode_ref
        WHERE 
            np.rn = 1
            AND np.start_drug_date >= fm.start_date
            AND (np.start_drug_date <= fm.end_date OR fm.end_date IS NULL)
    )
    SELECT 
        episode_ref,
        start_date,
        start_drug_date,
        drug_descr,
        hours_difference
    FROM 
        matched_nutrition
    WHERE 
        hours_difference >= 0
    ORDER BY 
        episode_ref, start_date;
    """
    return query


def analyze_nutrition(df, year, unit_list, start_date, end_date):
    """Analiza los datos de nutrición y muestra estadísticas"""
    if df.empty:
        print("No se encontraron datos para el período analizado.")
        return
    
    print(f"\n{'='*60}")
    print(f"ANÁLISIS DE NUTRICIÓN {year}")
    print(f"{'='*60}\n")
    print(f"Total de episodios con nutrición: {len(df)}\n")
    
    # Análisis por tipo de nutrición
    enterals = df[df['drug_descr'] == 'NUTRICION ENTERAL']
    parenterals = df[df['drug_descr'] == 'NUTRICIÓN PARENTERAL CENTRAL']
    
    enterals_count = len(enterals)
    parenterals_count = len(parenterals)
    nutri_totals = len(df)
    
    if nutri_totals > 0:
        perc_enterals = (enterals_count / nutri_totals) * 100
        perc_parenterals = (parenterals_count / nutri_totals) * 100
        
        print(f"Nutrición Enteral:")
        print(f"  - Cantidad: {enterals_count}")
        print(f"  - Porcentaje: {perc_enterals:.2f}%\n")
        
        print(f"Nutrición Parenteral Central:")
        print(f"  - Cantidad: {parenterals_count}")
        print(f"  - Porcentaje: {perc_parenterals:.2f}%\n")
        
        # Tiempos medios
        if enterals_count > 0:
            temps_enteral = enterals['hours_difference'].mean()
            print(f"Tiempo medio hasta inicio nutrición enteral: {temps_enteral:.0f} horas")
        
        if parenterals_count > 0:
            temps_parenteral = parenterals['hours_difference'].mean()
            print(f"Tiempo medio hasta inicio nutrición parenteral: {temps_parenteral:.0f} horas")
    
    print(f"\n{'='*60}\n")
    
    # Guardar resultados en CSV
    units_str = "-".join(unit_list).replace(" ", "")
    output_csv = OUTPUT_DIR / f"nutritions_analysis_{year}_{units_str}.csv"
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Resultados guardados en: {output_csv}")
    
    return df


def main():
    """Función principal"""
    print("========================================")
    print("   ANÁLISIS DE NUTRICIÓN")
    print("========================================")
    
    # Solicitar año
    year_input = input("Enter Year (e.g., 2024): ").strip()
    try:
        year = int(year_input)
    except ValueError:
        raise ValueError(f"Año inválido: {year_input!r}")
    
    # Solicitar unidades
    units_input = input(
        "Enter Units separated by commas (e.g., E073 or E073, I073): "
    ).strip()
    unit_list = [u.strip() for u in units_input.split(',') if u.strip()]
    
    if len(unit_list) < 1:
        raise ValueError("Debes indicar al menos una unidad (p.ej. E073).")
    
    # Generar fechas basadas en el año
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    print(f"\nEjecutando análisis de nutrición para {year}...")
    print(f"Unidades: {', '.join(unit_list)}")
    print(f"Período: {start_date} a {end_date}\n")
    
    # Generar y ejecutar query
    query = get_nutrition_query(start_date, end_date, unit_list)
    df = execute_query(query)
    
    # Mostrar información básica del dataframe
    print(f"\nInformación del dataset:")
    print(df.info())
    
    # Realizar análisis
    analyze_nutrition(df, year, unit_list, start_date, end_date)
    
    return df


if __name__ == "__main__":
    df = main()
