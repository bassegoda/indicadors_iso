"""
IDENTIFICADOR DE INGRESOS REALES EN UNIDADES DE HOSPITALIZACIÓN

Script flexible para identificar ingresos reales en cualquier unidad de hospitalización.
Criterios de ingreso real:
1. Cama asignada (place_ref IS NOT NULL)
2. Prescripción de medicación durante la estancia

Genera por cada unidad:
- CSV detallado con todos los ingresos
- CSV resumen con estadísticas agregadas
- Gráfico de evolución temporal
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Configurar backend de matplotlib ANTES de importar pyplot (fix para Windows/Tcl)
import matplotlib
matplotlib.use('Agg')  # Backend sin interfaz gráfica
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

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
    WHERE ou_loc_ref = '{unit}'
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
    e.episode_type_ref,
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
    ex.exitus_date
FROM cohort c
INNER JOIN g_episodes e 
    ON c.episode_ref = e.episode_ref
LEFT JOIN g_demographics d 
    ON c.patient_ref = d.patient_ref
LEFT JOIN g_exitus ex 
    ON c.patient_ref = ex.patient_ref
INNER JOIN g_prescriptions p 
    ON c.patient_ref = p.patient_ref 
    AND c.episode_ref = p.episode_ref
    AND p.start_drug_date <= c.discharge_date
    AND (p.end_drug_date >= c.admission_date OR p.end_drug_date IS NULL)
ORDER BY c.admission_date;
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
            
            if "-" in user_input:
                parts = user_input.split("-")
                if len(parts) == 2:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    years = list(range(start, end + 1))
            elif "," in user_input:
                years = [int(y.strip()) for y in user_input.split(",")]
            else:
                years = [int(user_input.strip())]
            
            if not years:
                print("❌ No se ingresaron años válidos. Intenta de nuevo.")
                continue
            
            years = sorted(list(set(years)))
            print(f"\n✓ Años seleccionados: {years}")
            return years
            
        except ValueError:
            print("❌ Entrada inválida. Por favor, ingresa años como números (ej: 2024 o 2023-2025).")


def get_units_from_user() -> list:
    """Solicita al usuario las unidades a analizar."""
    print("\n" + "="*80)
    print("  SELECCIÓN DE UNIDADES")
    print("="*80)
    print("\nPuedes ingresar códigos de unidades de hospitalización.")
    print("\nEjemplos comunes:")
    print("  - E073: UCI principal")
    print("  - I073: Unidad Intermedia")
    print("  - Otras unidades según necesites")
    print("\nEjemplos de entrada:")
    print("  - Una unidad:     E073")
    print("  - Múltiples:      E073,I073")
    
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
            print(f"   Se generará análisis SEPARADO para cada unidad.")
            return units
            
        except Exception as e:
            print(f"❌ Error: {e}. Por favor, intenta de nuevo.")


def validate_raw_data(df: pd.DataFrame, unit: str) -> pd.DataFrame:
    """Valida y limpia datos potencialmente erróneos."""
    initial_count = len(df)
    
    # Eliminar estancias con fechas incoherentes
    df = df[df['discharge_date'] > df['admission_date']]
    
    # Eliminar estancias de 0 horas
    df = df[df['hours_stay'] > 0]
    
    # Eliminar edades imposibles
    df = df[(df['age_at_admission'] >= 0) & (df['age_at_admission'] <= 120)]
    
    removed = initial_count - len(df)
    if removed > 0:
        print(f"   ⚠️  [{unit}] Se eliminaron {removed} estancias con datos incoherentes.")
    
    return df


def get_real_admissions_for_unit(years: list, unit: str) -> pd.DataFrame:
    """Ejecuta la query para obtener ingresos reales de UNA unidad."""
    min_year = min(years)
    max_year = max(years)
    
    query = SQL_REAL_ADMISSIONS.format(
        unit=unit,
        min_year=min_year,
        max_year=max_year
    )
    
    try:
        df = execute_query(query)
        return df
    except Exception as e:
        print(f"   ❌ [{unit}] Error ejecutando query: {e}")
        return pd.DataFrame()


def calculate_summary_stats(df: pd.DataFrame, unit: str) -> pd.DataFrame:
    """Calcula estadísticas resumidas por año para una unidad."""
    if df.empty:
        return pd.DataFrame()
    
    summary = df.groupby('year_admission').agg(
        total_admissions=('patient_ref', 'count'),
        unique_patients=('patient_ref', 'nunique'),
        unique_episodes=('episode_ref', 'nunique'),
        avg_age=('age_at_admission', 'mean'),
        median_age=('age_at_admission', 'median'),
        pct_male=('sex', lambda x: (x == 'Hombre').sum() / len(x) * 100),
        pct_female=('sex', lambda x: (x == 'Mujer').sum() / len(x) * 100),
        total_deaths=('exitus_during_stay', lambda x: (x == 'Sí').sum()),
        mortality_rate=('exitus_during_stay', lambda x: (x == 'Sí').sum() / len(x) * 100),
        avg_hours=('hours_stay', 'mean'),
        median_hours=('hours_stay', 'median'),
        min_hours=('hours_stay', 'min'),
        max_hours=('hours_stay', 'max'),
        avg_days=('days_stay', 'mean'),
        median_days=('days_stay', 'median'),
        stays_under_24h=('hours_stay', lambda x: (x < 24).sum()),
        stays_24_72h=('hours_stay', lambda x: ((x >= 24) & (x < 72)).sum()),
        stays_over_72h=('hours_stay', lambda x: (x >= 72).sum())
    ).reset_index()
    
    # Añadir columna de unidad
    summary.insert(0, 'unit', unit)
    
    # Redondear decimales
    summary = summary.round(2)
    
    return summary.sort_values('year_admission')


def save_results_for_unit(df_raw: pd.DataFrame, df_summary: pd.DataFrame, 
                           years: list, unit: str, timestamp: str):
    """Guarda los resultados CSV para una unidad específica."""
    if df_raw.empty:
        print(f"   ⚠️  [{unit}] No hay datos para guardar.")
        return
    
    year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
    
    # Archivo detallado
    file_detail = OUTPUT_DIR / f"ingresos_{unit}_{year_str}_{timestamp}.csv"
    df_raw.to_csv(file_detail, index=False, encoding='utf-8-sig')
    print(f"   ✓ [{unit}] CSV detallado: {file_detail.name}")
    
    # Archivo resumen
    file_summary = OUTPUT_DIR / f"resumen_{unit}_{year_str}_{timestamp}.csv"
    df_summary.to_csv(file_summary, index=False, encoding='utf-8-sig')
    print(f"   ✓ [{unit}] CSV resumen: {file_summary.name}")


def plot_admissions_for_unit(df_summary: pd.DataFrame, df_raw: pd.DataFrame, 
                              years: list, unit: str, timestamp: str):
    """Genera gráficos para una unidad específica."""
    try:
        year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0])
        
        # Crear figura con 3 subplots
        fig = plt.figure(figsize=(15, 10))
        gs = GridSpec(2, 2, figure=fig)
        
        # 1. Evolución de admisiones por año (arriba izquierda)
        ax1 = fig.add_subplot(gs[0, 0])
        df_summary.plot(x='year_admission', y='total_admissions', 
                        kind='bar', ax=ax1, color='steelblue', legend=False)
        ax1.set_title(f'Total de Ingresos por Año - {unit}', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Año')
        ax1.set_ylabel('Número de Ingresos')
        ax1.grid(axis='y', alpha=0.3)
        
        # Añadir valores sobre las barras
        for container in ax1.containers:
            ax1.bar_label(container, fmt='%d')
        
        # 2. Mortalidad por año (arriba derecha)
        ax2 = fig.add_subplot(gs[0, 1])
        ax2_twin = ax2.twinx()
        
        df_summary.plot(x='year_admission', y='total_deaths', 
                        kind='bar', ax=ax2, color='coral', label='Fallecimientos', alpha=0.7)
        df_summary.plot(x='year_admission', y='mortality_rate', 
                        kind='line', ax=ax2_twin, color='darkred', 
                        marker='o', linewidth=2, label='Tasa mortalidad (%)')
        
        ax2.set_title(f'Mortalidad por Año - {unit}', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Año')
        ax2.set_ylabel('Número de Fallecimientos')
        ax2_twin.set_ylabel('Tasa de Mortalidad (%)')
        ax2.legend(loc='upper left')
        ax2_twin.legend(loc='upper right')
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. Distribución de duración de estancias (abajo izquierda)
        ax3 = fig.add_subplot(gs[1, 0])
        
        # Preparar datos para stacked bar
        duration_data = df_summary[['year_admission', 'stays_under_24h', 
                                     'stays_24_72h', 'stays_over_72h']].set_index('year_admission')
        
        duration_data.plot(kind='bar', stacked=True, ax=ax3, 
                          color=['lightgreen', 'gold', 'tomato'])
        ax3.set_title(f'Duración de Estancias por Año - {unit}', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Año')
        ax3.set_ylabel('Número de Estancias')
        ax3.legend(['< 24h', '24-72h', '> 72h'], loc='upper left')
        ax3.grid(axis='y', alpha=0.3)
        
        # 4. Distribución edad al ingreso (abajo derecha)
        ax4 = fig.add_subplot(gs[1, 1])
        df_raw['age_at_admission'].plot(kind='hist', bins=20, ax=ax4, 
                                        color='mediumpurple', edgecolor='black', alpha=0.7)
        ax4.axvline(df_raw['age_at_admission'].median(), color='red', 
                   linestyle='--', linewidth=2, label=f'Mediana: {df_raw["age_at_admission"].median():.0f} años')
        ax4.set_title(f'Distribución de Edad al Ingreso - {unit}', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Edad (años)')
        ax4.set_ylabel('Frecuencia')
        ax4.legend()
        ax4.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfico
        plot_file = OUTPUT_DIR / f"graficos_{unit}_{year_str}_{timestamp}.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"   ✓ [{unit}] Gráficos: {plot_file.name}")
        
    except Exception as e:
        print(f"   ⚠️  [{unit}] Error generando gráficos: {e}")


def display_summary_for_unit(df_raw: pd.DataFrame, df_summary: pd.DataFrame, unit: str):
    """Muestra resumen en consola para una unidad."""
    print("\n" + "="*80)
    print(f"  RESULTADOS PARA UNIDAD: {unit}")
    print("="*80)
    
    if df_raw.empty:
        print(f"\n⚠️  No se encontraron estancias para {unit}.")
        return
    
    print(f"\n📊 Total de estancias: {len(df_raw)}")
    print(f"👥 Pacientes únicos: {df_raw['patient_ref'].nunique()}")
    print(f"📅 Episodios únicos: {df_raw['episode_ref'].nunique()}")
    print(f"💀 Fallecimientos: {(df_raw['exitus_during_stay'] == 'Sí').sum()} ({(df_raw['exitus_during_stay'] == 'Sí').sum() / len(df_raw) * 100:.1f}%)")
    
    print("\n" + "-"*80)
    print("RESUMEN POR AÑO:")
    print("-"*80)
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 20)
    
    # Mostrar columnas más relevantes
    summary_display = df_summary[['year_admission', 'total_admissions', 
                                   'unique_patients', 'total_deaths', 
                                   'mortality_rate', 'avg_age', 'median_hours', 'median_days']]
    
    print(summary_display.to_string(index=False))


def process_unit(unit: str, years: list, timestamp: str):
    """Procesa una unidad completa: query, validación, CSV, resumen y gráfico."""
    print(f"\n{'='*80}")
    print(f"  PROCESANDO UNIDAD: {unit}")
    print(f"{'='*80}")
    
    # 1. Obtener datos
    print(f"\n⏳ [{unit}] Ejecutando query...")
    df_raw = get_real_admissions_for_unit(years, unit)
    
    if df_raw.empty:
        print(f"   ❌ [{unit}] No se encontraron datos.")
        return
    
    print(f"   ✓ [{unit}] Query completada. {len(df_raw)} estancias encontradas.")
    
    # 2. Validar datos
    df_raw = validate_raw_data(df_raw, unit)
    
    if df_raw.empty:
        print(f"   ❌ [{unit}] No hay datos válidos después de la validación.")
        return
    
    # 3. Calcular resumen
    df_summary = calculate_summary_stats(df_raw, unit)
    
    # 4. Mostrar resultados en consola
    display_summary_for_unit(df_raw, df_summary, unit)
    
    # 5. Guardar CSV
    print(f"\n💾 [{unit}] Guardando archivos...")
    save_results_for_unit(df_raw, df_summary, years, unit, timestamp)
    
    # 6. Generar gráficos
    print(f"\n📊 [{unit}] Generando gráficos...")
    plot_admissions_for_unit(df_summary, df_raw, years, unit, timestamp)
    
    print(f"\n✓ [{unit}] Análisis completado.\n")


# ==========================================
# MAIN
# ==========================================

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║   IDENTIFICADOR DE INGRESOS REALES EN HOSPITALIZACIÓN         ║")
    print("║   Criterios: Cama Asignada + Prescripción de Medicación       ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    # Obtener entrada del usuario
    years = get_years_from_user()
    units = get_units_from_user()
    
    # Timestamp único para todos los archivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*80}")
    print(f"  INICIO DEL ANÁLISIS")
    print(f"{'='*80}")
    print(f"\n🗓️  Años: {min(years)}-{max(years)}")
    print(f"🏥 Unidades: {len(units)}")
    print(f"📁 Carpeta de salida: {OUTPUT_DIR}")
    
    # Procesar cada unidad por separado
    for unit in units:
        process_unit(unit, years, timestamp)
    
    # Resumen final
    print("\n" + "="*80)
    print("  ANÁLISIS COMPLETADO")
    print("="*80)
    print(f"\n✓ Se procesaron {len(units)} unidad(es)")
    print(f"✓ Archivos guardados en: {OUTPUT_DIR}")
    print("\nPor cada unidad se generaron:")
    print("  - CSV detallado con todos los ingresos")
    print("  - CSV resumen con estadísticas por año")
    print("  - Gráficos de evolución y distribuciones")
    print()


if __name__ == "__main__":
    main()