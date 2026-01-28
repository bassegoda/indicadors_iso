"""
IDENTIFICADOR DE INGRESOS REALES EN UCI - ESTRATEGIA: CAMA + PRESCRIPCIÓN

Script para identificar ingresos reales en unidades de cuidados intensivos
basándose en la presencia de:
1. Cama asignada (place_ref IS NOT NULL)
2. Prescripción de medicación durante la estancia

Utiliza tablas g_* (patient_ref, episode_ref) con movimientos sin cambios
de cama instantáneos (end_date > start_date).

Salida: CSV con todas las estancias identificadas + CSV resumen por unidad
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query


# ==========================================
# CONFIGURACIÓN DE SALIDA
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ==========================================
# TEMPLATES SQL
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
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{max_year}-12-31 23:59:59'
      AND end_date >= '{min_year}-01-01 00:00:00'
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
        SUBSTRING_INDEX(GROUP_CONCAT(ou_loc_ref ORDER BY start_date SEPARATOR ','), ',', 1) as ou_loc_ref,
        MIN(start_date) as true_start_date,
        MAX(end_date) as true_end_date,
        TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id
)
SELECT DISTINCT
    c.patient_ref,
    c.episode_ref,
    c.stay_id,
    c.ou_loc_ref,
    c.true_start_date,
    c.true_end_date,
    c.total_hours,
    YEAR(c.true_start_date) as year_admission,
    TIMESTAMPDIFF(DAY, c.true_start_date, c.true_end_date) as days_stay
FROM cohort c
INNER JOIN g_prescriptions p 
    ON c.patient_ref = p.patient_ref 
    AND c.episode_ref = p.episode_ref
    AND p.start_drug_date <= c.true_end_date
    AND (p.end_drug_date >= c.true_start_date OR p.end_drug_date IS NULL)
ORDER BY c.ou_loc_ref, c.true_start_date;
"""


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def get_years_from_user() -> list:
    """Solicita al usuario los años a analizar."""
    print("\n" + "="*80)
    print("  SELECCIÓN DE AÑOS")
    print("="*80)
    print("\nEjemplos de entrada:")
    print("  - Un año:    2024")
    print("  - Rango:     2023-2025")
    print("  - Múltiples: 2023,2024,2025")
    
    while True:
        try:
            user_input = input("\nAños a analizar: ").strip()
            
            years = []
            
            # Caso 1: Rango (ej: 2023-2025)
            if "-" in user_input:
                parts = user_input.split("-")
                if len(parts) == 2:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    years = list(range(start, end + 1))
            
            # Caso 2: Múltiples separadas por coma
            elif "," in user_input:
                years = [int(y.strip()) for y in user_input.split(",")]
            
            # Caso 3: Un año único
            else:
                years = [int(user_input.strip())]
            
            # Validar
            if not years:
                print("❌ No se ingresaron años válidos. Intenta de nuevo.")
                continue
            
            years = sorted(list(set(years)))  # Eliminar duplicados y ordenar
            print(f"\n✓ Años seleccionados: {years}")
            return years
            
        except ValueError:
            print("❌ Entrada inválida. Por favor, ingresa años como números (ej: 2024 o 2023-2025).")


def get_units_from_user() -> list:
    """Solicita al usuario las unidades a analizar."""
    print("\n" + "="*80)
    print("  SELECCIÓN DE UNIDADES")
    print("="*80)
    print("\nUnidades comunes ICU:")
    print("  - E073: Unidad de Cuidados Intensivos (principal)")
    print("  - I073: Unidad Intermedia")
    print("\nPuedes ingresar otras unidades si lo necesitas.")
    print("\nEjemplos de entrada:")
    print("  - Una unidad:     E073")
    print("  - Múltiples:      E073,I073")
    print("  - Personalizado:  E073,I073,X999")
    
    while True:
        try:
            user_input = input("\nUnidades a analizar (separadas por coma): ").strip().upper()
            
            if not user_input:
                print("❌ No ingresaste unidades. Por favor, intenta de nuevo.")
                continue
            
            units = [u.strip() for u in user_input.split(",") if u.strip()]
            
            if not units:
                print("❌ No se ingresaron unidades válidas. Intenta de nuevo.")
                continue
            
            print(f"\n✓ Unidades seleccionadas: {units}")
            return units
            
        except Exception as e:
            print(f"❌ Error: {e}. Por favor, intenta de nuevo.")


def format_units_for_sql(units: list) -> str:
    """Formatea las unidades para la cláusula IN del SQL."""
    return ", ".join([f"'{u}'" for u in units])


def get_real_admissions(years: list, units: list) -> pd.DataFrame:
    """Ejecuta la query para obtener ingresos reales."""
    print("\n⏳ Ejecutando análisis...")
    
    min_year = min(years)
    max_year = max(years)
    units_formatted = format_units_for_sql(units)
    
    query = SQL_REAL_ADMISSIONS.format(
        units_formatted=units_formatted,
        min_year=min_year,
        max_year=max_year
    )
    
    try:
        df = execute_query(query)
        print(f"✓ Query ejecutada correctamente. Se encontraron {len(df)} estancias.")
        return df
    except Exception as e:
        print(f"❌ Error ejecutando la query: {e}")
        return pd.DataFrame()


def calculate_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula estadísticas resumidas por unidad y año."""
    if df.empty:
        return pd.DataFrame()
    
    summary = df.groupby(['year_admission', 'ou_loc_ref']).agg(
        total_admissions=('patient_ref', 'count'),
        unique_patients=('patient_ref', 'nunique'),
        unique_episodes=('episode_ref', 'nunique'),
        avg_hours=('total_hours', 'mean'),
        median_hours=('total_hours', 'median'),
        min_hours=('total_hours', 'min'),
        max_hours=('total_hours', 'max'),
        avg_days=('days_stay', 'mean'),
        median_days=('days_stay', 'median')
    ).reset_index()
    
    return summary.sort_values(['year_admission', 'ou_loc_ref'])


def save_results(df_raw: pd.DataFrame, df_summary: pd.DataFrame, years: list, units: list):
    """Guarda los resultados en archivos CSV."""
    if df_raw.empty:
        print("\n⚠️  No hay datos para guardar.")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
    units_str = "_".join(units)
    
    # Archivo detallado
    file_detail = OUTPUT_DIR / f"icu_admissions_{year_str}_{units_str}_{timestamp}.csv"
    df_raw.to_csv(file_detail, index=False, encoding='utf-8-sig')
    print(f"\n✓ Archivo detallado guardado: {file_detail.name}")
    
    # Archivo resumen
    file_summary = OUTPUT_DIR / f"icu_admissions_summary_{year_str}_{units_str}_{timestamp}.csv"
    df_summary.to_csv(file_summary, index=False, encoding='utf-8-sig')
    print(f"✓ Archivo resumen guardado: {file_summary.name}")


def display_summary(df_raw: pd.DataFrame, df_summary: pd.DataFrame):
    """Muestra un resumen en consola."""
    print("\n" + "="*80)
    print("  RESUMEN DE RESULTADOS")
    print("="*80)
    
    if df_raw.empty:
        print("\n⚠️  No se encontraron estancias con los criterios especificados.")
        return
    
    print(f"\n📊 Total de estancias identificadas: {len(df_raw)}")
    print(f"👥 Pacientes únicos: {df_raw['patient_ref'].nunique()}")
    
    print("\n" + "-"*80)
    print("ESTADÍSTICAS POR AÑO Y UNIDAD:")
    print("-"*80)
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    print(df_summary.to_string(index=False))
    
    print("\n" + "-"*80)
    print("DISTRIBUCIÓN DE DURACIÓN:")
    print("-"*80)
    print(f"  Estancias < 24h:  {len(df_raw[df_raw['total_hours'] < 24])} ({len(df_raw[df_raw['total_hours'] < 24])/len(df_raw)*100:.1f}%)")
    print(f"  Estancias 24-72h: {len(df_raw[(df_raw['total_hours'] >= 24) & (df_raw['total_hours'] < 72)])} ({len(df_raw[(df_raw['total_hours'] >= 24) & (df_raw['total_hours'] < 72)])/len(df_raw)*100:.1f}%)")
    print(f"  Estancias > 72h:  {len(df_raw[df_raw['total_hours'] >= 72])} ({len(df_raw[df_raw['total_hours'] >= 72])/len(df_raw)*100:.1f}%)")


# ==========================================
# MAIN
# ==========================================

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║   IDENTIFICADOR DE INGRESOS REALES EN UCI                    ║")
    print("║   Estrategia: Cama Asignada + Prescripción de Medicación      ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    # Obtener entrada del usuario
    years = get_years_from_user()
    units = get_units_from_user()
    
    # Ejecutar análisis
    df_raw = get_real_admissions(years, units)
    
    if df_raw.empty:
        print("\n❌ No se encontraron datos. Verifica los años y unidades ingresadas.")
        return
    
    # Calcular estadísticas
    df_summary = calculate_summary_stats(df_raw)
    
    # Mostrar resultados
    display_summary(df_raw, df_summary)
    
    # Guardar resultados
    save_results(df_raw, df_summary, years, units)
    
    print("\n✓ Análisis completado.\n")


if __name__ == "__main__":
    main()
