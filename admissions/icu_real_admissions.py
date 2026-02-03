"""
IDENTIFICADOR DE INGRESOS REALES EN UNIDADES DE HOSPITALIZACIÓN

Criterios de ingreso real:
1. Cama asignada (place_ref IS NOT NULL)
2. Prescripción INICIADA durante la estancia

Genera un CSV con datos individuales por cada unidad.
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query
from origin import classify_origin


# ==========================================
# CONFIGURACIÓN
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ==========================================
# SQL
# ==========================================
SQL_REAL_ADMISSIONS = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref = '{unit}'
      AND YEAR(start_date) BETWEEN {min_year} AND {max_year}
      AND place_ref IS NOT NULL
      AND end_date > start_date
),
flagged_starts AS (
    SELECT 
        *,
        CASE 
            WHEN LAG(end_date) OVER (
                PARTITION BY episode_ref ORDER BY start_date
            ) = start_date 
            THEN 0 
            ELSE 1 
        END AS is_new_stay
    FROM raw_moves
),
grouped_stays AS (
    SELECT 
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_ref ORDER BY start_date
        ) as stay_id
    FROM flagged_starts
),
cohort AS (
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        '{unit}' as ou_loc_ref,
        MIN(start_date) as admission_date,
        MAX(end_date) as discharge_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS hours_stay,
        TIMESTAMPDIFF(DAY, MIN(start_date), MAX(end_date)) AS days_stay,
        COUNT(*) as num_movements
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
)
SELECT DISTINCT
    c.patient_ref,
    c.episode_ref,
    c.stay_id,
    c.ou_loc_ref,
    c.admission_date,
    c.discharge_date,
    c.hours_stay,
    c.days_stay,
    c.num_movements,
    YEAR(c.admission_date) as year_admission,
    TIMESTAMPDIFF(YEAR, d.birth_date, c.admission_date) as age_at_admission,
    CASE 
        WHEN d.sex = 1 THEN 'Hombre'
        WHEN d.sex = 2 THEN 'Mujer'
        WHEN d.sex = 3 THEN 'Otro'
        ELSE 'No reportado'
    END as sex,
    CASE 
        WHEN ex.exitus_date IS NOT NULL 
             AND ex.exitus_date BETWEEN c.admission_date AND c.discharge_date 
        THEN 'Sí'
        ELSE 'No'
    END as exitus_during_stay,
    ex.exitus_date,
    d.health_area,
    d.postcode
FROM cohort c
LEFT JOIN g_demographics d
    ON c.patient_ref = d.patient_ref
LEFT JOIN g_exitus ex 
    ON c.patient_ref = ex.patient_ref
INNER JOIN g_prescriptions p 
    ON c.patient_ref = p.patient_ref 
    AND c.episode_ref = p.episode_ref
    AND p.start_drug_date BETWEEN c.admission_date AND c.discharge_date
ORDER BY c.admission_date;
"""


# ==========================================
# FUNCIONES
# ==========================================
def get_years_from_user() -> list:
    """Solicita años a analizar."""
    print("\nAños a analizar (ej: 2024 o 2023-2025): ", end="")
    user_input = input().strip()
    
    if "-" in user_input:
        start, end = map(int, user_input.split("-"))
        return list(range(start, end + 1))
    elif "," in user_input:
        return [int(y.strip()) for y in user_input.split(",")]
    else:
        return [int(user_input)]


def get_units_from_user() -> list:
    """Solicita unidades a analizar."""
    print("Unidades a analizar (ej: E073 o E073,I073): ", end="")
    user_input = input().strip().upper()
    return [u.strip() for u in user_input.split(",")]


def process_unit(unit: str, years: list, timestamp: str):
    """Procesa una unidad: ejecuta query y guarda CSV."""
    min_year = min(years)
    max_year = max(years)
    
    query = SQL_REAL_ADMISSIONS.format(
        unit=unit,
        min_year=min_year,
        max_year=max_year
    )
    
    # Ejecutar query
    df = execute_query(query)
    
    if df.empty:
        print(f"\n[{unit}] No se encontraron datos")
        return
    
    # Validar datos
    initial = len(df)
    df = df[
        (df['discharge_date'] > df['admission_date']) &
        (df['hours_stay'] > 0) &
        (df['age_at_admission'] >= 0) &
        (df['age_at_admission'] <= 120)
    ]
    
    if len(df) < initial:
        print(f"[{unit}] Se eliminaron {initial - len(df)} registros incoherentes")

    # Clasificación de origen
    df["origin"] = classify_origin(df)

    # Guardar CSV
    year_str = f"{min_year}-{max_year}" if len(years) > 1 else str(min_year)
    filename = OUTPUT_DIR / f"ingresos_{unit}_{year_str}_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    # Resumen
    total = len(df)
    pacientes = df['patient_ref'].nunique()
    fallecidos = (df['exitus_during_stay'] == 'Sí').sum()
    mortalidad = (fallecidos / total * 100) if total > 0 else 0
    
    print(f"\n[{unit}] {total} estancias | {pacientes} pacientes | {fallecidos} fallecimientos ({mortalidad:.1f}%)")
    print(f"        Origen: {df['origin'].value_counts().to_dict()}")
    print(f"        Archivo: {filename.name}")


# ==========================================
# MAIN
# ==========================================
def main():
    print("\n" + "="*70)
    print("  IDENTIFICADOR DE INGRESOS REALES EN HOSPITALIZACIÓN")
    print("="*70)
    
    years = get_years_from_user()
    units = get_units_from_user()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\nProcesando {len(units)} unidad(es) para años {min(years)}-{max(years)}...")
    
    for unit in units:
        process_unit(unit, years, timestamp)
    
    print(f"\n✓ Archivos guardados en: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()