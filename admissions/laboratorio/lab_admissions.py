"""
Laboratorio de pruebas para estrategias de identificación de ingresos en UCI.

Este script permite probar diferentes criterios para determinar qué constituye
un "ingreso real" en las unidades E073 e I073.

NOTA: Un mismo paciente puede tener múltiples ingresos (estancias) en el mismo año.
Cada estancia se cuenta como un ingreso independiente.

Estrategias disponibles:
- baseline: Sin filtros adicionales (solo unidad y fecha)
- place_ref: Requiere cama asignada (place_ref IS NOT NULL)
- place_prescriptions: Requiere cama asignada + prescripción de medicación durante la estancia
"""

import pandas as pd
import sys
from pathlib import Path

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query

# ==========================================
# CONFIGURACIÓN
# ==========================================
UNITS = ["E073", "I073"]
YEARS = [2023, 2024, 2025]


# ==========================================
# TEMPLATES SQL
# ==========================================

# Estrategia 1: BASELINE - Solo filtra por unidad y año (con solapamiento)
SQL_BASELINE = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
)
SELECT
    patient_ref,
    episode_ref,
    stay_id,
    SUBSTRING_INDEX(GROUP_CONCAT(ou_loc_ref ORDER BY start_date SEPARATOR ','), ',', 1) as ou_loc_ref,
    MIN(start_date) as true_start_date,
    MAX(end_date) as true_end_date,
    TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
FROM grouped_stays
GROUP BY patient_ref, episode_ref, stay_id;
"""

# Estrategia 2: PLACE_REF - Requiere cama asignada (con solapamiento)
SQL_PLACE_REF = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
)
SELECT
    patient_ref,
    episode_ref,
    stay_id,
    SUBSTRING_INDEX(GROUP_CONCAT(ou_loc_ref ORDER BY start_date SEPARATOR ','), ',', 1) as ou_loc_ref,
    MIN(start_date) as true_start_date,
    MAX(end_date) as true_end_date,
    TIMESTAMPDIFF(HOUR, MIN(start_date), MAX(end_date)) AS total_hours
FROM grouped_stays
GROUP BY patient_ref, episode_ref, stay_id;
"""

# Estrategia 3: PLACE_PRESCRIPTIONS - place_ref + prescripción de medicación (con solapamiento)
SQL_PLACE_PRESCRIPTIONS = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
    c.total_hours
FROM cohort c
INNER JOIN g_prescriptions p 
    ON c.patient_ref = p.patient_ref 
    AND c.episode_ref = p.episode_ref
    AND p.start_drug_date <= c.true_end_date
    AND (p.end_drug_date >= c.true_start_date OR p.end_drug_date IS NULL);
"""

STRATEGIES = {
    "baseline": SQL_BASELINE,
    "place_ref": SQL_PLACE_REF,
    "place_prescriptions": SQL_PLACE_PRESCRIPTIONS
}

# Query de diagnóstico: ingresos con cama PERO SIN prescripciones (con solapamiento)
SQL_NO_PRESCRIPTIONS = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
),
with_prescriptions AS (
    SELECT DISTINCT c.patient_ref, c.episode_ref, c.stay_id
    FROM cohort c
    INNER JOIN g_prescriptions p 
        ON c.patient_ref = p.patient_ref 
        AND c.episode_ref = p.episode_ref
        AND p.start_drug_date <= c.true_end_date
        AND (p.end_drug_date >= c.true_start_date OR p.end_drug_date IS NULL)
)
SELECT 
    c.patient_ref,
    c.episode_ref,
    c.stay_id,
    c.ou_loc_ref,
    c.true_start_date,
    c.true_end_date,
    c.total_hours
FROM cohort c
LEFT JOIN with_prescriptions wp 
    ON c.patient_ref = wp.patient_ref 
    AND c.episode_ref = wp.episode_ref 
    AND c.stay_id = wp.stay_id
WHERE wp.patient_ref IS NULL
ORDER BY c.ou_loc_ref, c.true_start_date;
"""

# Query de diagnóstico: estancias cortas (<24h) con cama Y prescripciones (con solapamiento)
SQL_SHORT_STAYS = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
),
with_prescriptions AS (
    SELECT DISTINCT
        c.patient_ref,
        c.episode_ref,
        c.stay_id,
        c.ou_loc_ref,
        c.true_start_date,
        c.true_end_date,
        c.total_hours
    FROM cohort c
    INNER JOIN g_prescriptions p 
        ON c.patient_ref = p.patient_ref 
        AND c.episode_ref = p.episode_ref
        AND p.start_drug_date <= c.true_end_date
        AND (p.end_drug_date >= c.true_start_date OR p.end_drug_date IS NULL)
    WHERE c.total_hours < {max_hours}
)
SELECT 
    wp.patient_ref,
    wp.episode_ref,
    wp.stay_id,
    wp.ou_loc_ref,
    wp.true_start_date,
    wp.true_end_date,
    wp.total_hours,
    CASE 
        WHEN e.exitus_date IS NOT NULL 
             AND e.exitus_date >= DATE(wp.true_start_date) 
             AND e.exitus_date <= DATE(wp.true_end_date)
        THEN 1
        ELSE 0
    END AS exitus_during_stay
FROM with_prescriptions wp
LEFT JOIN g_exitus e ON wp.patient_ref = e.patient_ref
ORDER BY wp.ou_loc_ref, wp.total_hours;
"""

# Query de diagnóstico: estancias que cruzan el cambio de año (solapamiento)
SQL_YEAR_OVERLAP = """
WITH raw_moves AS (
    SELECT 
        patient_ref,
        episode_ref,
        ou_loc_ref, 
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date <= '{year}-12-31 23:59:59'
      AND end_date >= '{year}-01-01 00:00:00'
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
SELECT
    patient_ref,
    episode_ref,
    stay_id,
    ou_loc_ref,
    true_start_date,
    true_end_date,
    total_hours,
    CASE 
        WHEN YEAR(true_start_date) < {year} THEN 'ingreso_año_anterior'
        WHEN YEAR(true_end_date) > {year} THEN 'alta_año_siguiente'
        ELSE 'dentro_del_año'
    END AS tipo_solapamiento
FROM cohort
ORDER BY tipo_solapamiento, ou_loc_ref, true_start_date;
"""


# ==========================================
# FUNCIONES
# ==========================================
def diagnose_year_overlap(year: int) -> pd.DataFrame:
    """Identifica estancias que cruzan el cambio de año."""
    units_formatted = ", ".join([f"'{u}'" for u in UNITS])
    query = SQL_YEAR_OVERLAP.format(units_formatted=units_formatted, year=year)
    return execute_query(query)


def diagnose_short_stays(year: int, max_hours: int = 24) -> pd.DataFrame:
    """Identifica estancias cortas (<max_hours) con cama y prescripciones."""
    units_formatted = ", ".join([f"'{u}'" for u in UNITS])
    query = SQL_SHORT_STAYS.format(units_formatted=units_formatted, year=year, max_hours=max_hours)
    return execute_query(query)


def diagnose_no_prescriptions(year: int) -> pd.DataFrame:
    """Identifica ingresos con cama asignada pero SIN prescripciones (casos sospechosos)."""
    units_formatted = ", ".join([f"'{u}'" for u in UNITS])
    query = SQL_NO_PRESCRIPTIONS.format(units_formatted=units_formatted, year=year)
    return execute_query(query)


def run_strategy(strategy_name: str, year: int) -> pd.DataFrame:
    """Ejecuta una estrategia específica y devuelve los datos brutos de cada estancia."""
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Estrategia '{strategy_name}' no reconocida. Opciones: {list(STRATEGIES.keys())}")
    
    sql_template = STRATEGIES[strategy_name]
    units_formatted = ", ".join([f"'{u}'" for u in UNITS])
    
    query = sql_template.format(
        units_formatted=units_formatted,
        year=year
    )
    
    return execute_query(query)


def calculate_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula estadísticas agregadas por unidad a partir de datos brutos."""
    if df.empty:
        return pd.DataFrame()
    
    stats = df.groupby('ou_loc_ref').agg(
        total_admissions=('patient_ref', 'count'),
        unique_patients=('patient_ref', 'nunique'),
        avg_hours=('total_hours', 'mean'),
        median_hours=('total_hours', 'median'),
        min_hours=('total_hours', 'min'),
        max_hours=('total_hours', 'max')
    ).reset_index()
    
    return stats


def compare_strategies(year: int):
    """Compara todas las estrategias para un año dado."""
    print(f"\n{'='*80}")
    print(f"  COMPARACIÓN DE ESTRATEGIAS - AÑO {year}")
    print(f"  Unidades: {', '.join(UNITS)}")
    print(f"{'='*80}")
    
    results = {}
    
    for strategy_name in STRATEGIES:
        print(f"\n>>> Ejecutando estrategia: {strategy_name.upper()}")
        df_raw = run_strategy(strategy_name, year)
        stats = calculate_stats(df_raw)
        results[strategy_name] = {'raw': df_raw, 'stats': stats}
        
        if stats.empty:
            print("    Sin resultados")
            continue
            
        for _, row in stats.iterrows():
            unit = row['ou_loc_ref']
            admissions = int(row['total_admissions'])
            patients = int(row['unique_patients'])
            avg_h = row['avg_hours']
            median_h = row['median_hours']
            print(f"    {unit}: {admissions:,} ingresos | {patients:,} pacientes únicos | Media: {avg_h:.1f}h | Mediana: {median_h:.1f}h")
    
    return results


def summary_table(years: list = YEARS):
    """Genera una tabla resumen comparando estrategias por año."""
    print(f"\n{'='*90}")
    print(f"  TABLA RESUMEN - INGRESOS ANUALES POR ESTRATEGIA")
    print(f"{'='*90}")
    
    all_data = []
    
    for year in years:
        print(f"\n--- Procesando año {year} ---")
        for strategy_name in STRATEGIES:
            df_raw = run_strategy(strategy_name, year)
            stats = calculate_stats(df_raw)
            
            for unit in UNITS:
                unit_data = stats[stats['ou_loc_ref'] == unit]
                if not unit_data.empty:
                    row = unit_data.iloc[0]
                    all_data.append({
                        'year': year,
                        'strategy': strategy_name,
                        'unit': unit,
                        'admissions': int(row['total_admissions']),
                        'patients': int(row['unique_patients']),
                        'avg_hours': round(row['avg_hours'], 1),
                        'median_hours': round(row['median_hours'], 1)
                    })
                else:
                    all_data.append({
                        'year': year,
                        'strategy': strategy_name,
                        'unit': unit,
                        'admissions': 0,
                        'patients': 0,
                        'avg_hours': 0,
                        'median_hours': 0
                    })
    
    summary_df = pd.DataFrame(all_data)
    
    # Mostrar tabla pivotada por año y estrategia
    print(f"\n{'='*90}")
    print("  RESULTADOS FINALES - INGRESOS")
    print(f"{'='*90}\n")
    
    for unit in UNITS:
        print(f"\n{'─'*60}")
        print(f"  UNIDAD: {unit}")
        print(f"{'─'*60}")
        unit_df = summary_df[summary_df['unit'] == unit]
        pivot = unit_df.pivot(index='strategy', columns='year', values='admissions')
        print(pivot.to_string())
    
    # Mostrar medianas
    print(f"\n{'='*90}")
    print("  RESULTADOS FINALES - MEDIANA DE ESTANCIA (horas)")
    print(f"{'='*90}\n")
    
    for unit in UNITS:
        print(f"\n{'─'*60}")
        print(f"  UNIDAD: {unit}")
        print(f"{'─'*60}")
        unit_df = summary_df[summary_df['unit'] == unit]
        pivot = unit_df.pivot(index='strategy', columns='year', values='median_hours')
        print(pivot.to_string())
    
    return summary_df


# ==========================================
# MAIN
# ==========================================
def main():
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     LABORATORIO DE ESTRATEGIAS DE IDENTIFICACIÓN DE INGRESOS  ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    print("\nOpciones:")
    print("  1. Comparar estrategias para un año específico")
    print("  2. Generar tabla resumen multi-año")
    print("  3. Ejecutar estrategia individual")
    print("  4. Diagnosticar ingresos SIN prescripciones (casos sospechosos)")
    print("  5. Analizar estancias cortas (<24h) con cama + prescripción")
    print("  6. Reporte de solapamiento (estancias que cruzan cambio de año)")
    
    option = input("\nSelecciona opción (1/2/3/4/5/6): ").strip()
    
    if option == "1":
        year = input("Año a analizar (ej: 2024): ").strip()
        compare_strategies(int(year))
        
    elif option == "2":
        years_input = input(f"Años a analizar (separados por coma) [{','.join(map(str, YEARS))}]: ").strip()
        years = [int(y.strip()) for y in years_input.split(',')] if years_input else YEARS
        summary_df = summary_table(years)
        
        # Guardar CSV
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "summary_strategies.csv"
        summary_df.to_csv(output_path, index=False)
        print(f"\n✓ Resumen guardado en: {output_path}")
        
    elif option == "3":
        print(f"\nEstrategias disponibles: {', '.join(STRATEGIES.keys())}")
        strategy = input("Estrategia: ").strip()
        year = input("Año: ").strip()
        
        df_raw = run_strategy(strategy, int(year))
        stats = calculate_stats(df_raw)
        
        print(f"\n{'─'*60}")
        print(f"  ESTADÍSTICAS AGREGADAS")
        print(f"{'─'*60}")
        print(stats.to_string(index=False))
        
        print(f"\n{'─'*60}")
        print(f"  DATOS BRUTOS ({len(df_raw)} estancias)")
        print(f"{'─'*60}")
        print(df_raw.head(20).to_string(index=False))
        if len(df_raw) > 20:
            print(f"  ... y {len(df_raw) - 20} estancias más")
    
    elif option == "4":
        year = input("Año a analizar (ej: 2024): ").strip()
        
        print(f"\n{'='*80}")
        print(f"  DIAGNÓSTICO: INGRESOS CON CAMA PERO SIN PRESCRIPCIONES - AÑO {year}")
        print(f"  (Casos sospechosos que requieren revisión)")
        print(f"{'='*80}")
        
        df_no_rx = diagnose_no_prescriptions(int(year))
        
        if df_no_rx.empty:
            print("\n✓ No hay casos sospechosos. Todos los ingresos con cama tienen prescripciones.")
        else:
            # Estadísticas por unidad
            print(f"\n>>> RESUMEN POR UNIDAD:")
            for unit in UNITS:
                unit_df = df_no_rx[df_no_rx['ou_loc_ref'] == unit]
                if not unit_df.empty:
                    n_cases = len(unit_df)
                    avg_hours = unit_df['total_hours'].mean()
                    median_hours = unit_df['total_hours'].median()
                    min_hours = unit_df['total_hours'].min()
                    max_hours = unit_df['total_hours'].max()
                    print(f"    {unit}: {n_cases} casos | Media: {avg_hours:.1f}h | Mediana: {median_hours:.1f}h | Rango: {min_hours}-{max_hours}h")
            
            # Detalle de casos
            print(f"\n>>> DETALLE DE CASOS ({len(df_no_rx)} total):")
            print(f"{'─'*100}")
            
            # Convertir fechas para mejor visualización
            df_display = df_no_rx.copy()
            df_display['true_start_date'] = pd.to_datetime(df_display['true_start_date']).dt.strftime('%Y-%m-%d %H:%M')
            df_display['true_end_date'] = pd.to_datetime(df_display['true_end_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            print(df_display.to_string(index=False))
            
            # Guardar CSV (sin datos identificativos)
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            df_no_rx_safe = df_no_rx.drop(columns=['patient_ref', 'episode_ref'], errors='ignore')
            output_path = output_dir / f"no_prescriptions_{year}.csv"
            df_no_rx_safe.to_csv(output_path, index=False)
            print(f"\n✓ Detalle guardado en: {output_path}")
    
    elif option == "5":
        year = input("Año a analizar (ej: 2024): ").strip()
        max_hours_input = input("Umbral máximo de horas (por defecto 24): ").strip()
        max_hours = int(max_hours_input) if max_hours_input else 24
        
        print(f"\n{'='*80}")
        print(f"  ANÁLISIS: ESTANCIAS CORTAS (<{max_hours}h) CON CAMA + PRESCRIPCIÓN - AÑO {year}")
        print(f"  (Estrategia place_prescriptions)")
        print(f"{'='*80}")
        
        df_short = diagnose_short_stays(int(year), max_hours)
        
        if df_short.empty:
            print(f"\n✓ No hay estancias de menos de {max_hours} horas.")
        else:
            # Estadísticas por unidad
            print(f"\n>>> RESUMEN POR UNIDAD:")
            for unit in UNITS:
                unit_df = df_short[df_short['ou_loc_ref'] == unit]
                if not unit_df.empty:
                    n_cases = len(unit_df)
                    avg_hours = unit_df['total_hours'].mean()
                    median_hours = unit_df['total_hours'].median()
                    min_hours = unit_df['total_hours'].min()
                    max_h = unit_df['total_hours'].max()
                    n_exitus = unit_df['exitus_during_stay'].sum()
                    pct_exitus = n_exitus / n_cases * 100
                    print(f"    {unit}: {n_cases} casos | Media: {avg_hours:.1f}h | Mediana: {median_hours:.1f}h | Rango: {min_hours}-{max_h}h | Exitus: {n_exitus} ({pct_exitus:.1f}%)")
            
            # Distribución por rangos de horas
            print(f"\n>>> DISTRIBUCIÓN POR RANGOS DE HORAS:")
            bins = [0, 1, 2, 4, 6, 12, 24]
            labels = ['0-1h', '1-2h', '2-4h', '4-6h', '6-12h', '12-24h']
            df_short['rango_horas'] = pd.cut(df_short['total_hours'], bins=bins, labels=labels, right=False)
            
            for unit in UNITS:
                unit_df = df_short[df_short['ou_loc_ref'] == unit]
                if not unit_df.empty:
                    print(f"\n    {unit}:")
                    dist = unit_df['rango_horas'].value_counts().sort_index()
                    for rango, count in dist.items():
                        pct = count / len(unit_df) * 100
                        print(f"      {rango}: {count} ({pct:.1f}%)")
            
            # Distribución de exitus por rangos de horas
            print(f"\n>>> EXITUS POR RANGOS DE HORAS:")
            for unit in UNITS:
                unit_df = df_short[df_short['ou_loc_ref'] == unit]
                if not unit_df.empty and unit_df['exitus_during_stay'].sum() > 0:
                    print(f"\n    {unit}:")
                    exitus_by_range = unit_df.groupby('rango_horas')['exitus_during_stay'].agg(['sum', 'count'])
                    for rango in labels:
                        if rango in exitus_by_range.index:
                            row = exitus_by_range.loc[rango]
                            if row['count'] > 0:
                                pct = row['sum'] / row['count'] * 100 if row['count'] > 0 else 0
                                print(f"      {rango}: {int(row['sum'])} exitus de {int(row['count'])} ({pct:.1f}%)")
            
            # Detalle de casos
            print(f"\n>>> DETALLE DE CASOS ({len(df_short)} total):")
            print(f"{'─'*100}")
            
            # Convertir fechas para mejor visualización
            df_display = df_short.drop(columns=['rango_horas']).copy()
            df_display['true_start_date'] = pd.to_datetime(df_display['true_start_date']).dt.strftime('%Y-%m-%d %H:%M')
            df_display['true_end_date'] = pd.to_datetime(df_display['true_end_date']).dt.strftime('%Y-%m-%d %H:%M')
            
            print(df_display.to_string(index=False))
            
            # Guardar CSV (sin datos identificativos)
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            df_short_safe = df_short.drop(columns=['rango_horas', 'patient_ref', 'episode_ref'], errors='ignore')
            output_path = output_dir / f"short_stays_{max_hours}h_{year}.csv"
            df_short_safe.to_csv(output_path, index=False)
            print(f"\n✓ Detalle guardado en: {output_path}")
    
    elif option == "6":
        year = input("Año a analizar (ej: 2024): ").strip()
        
        print(f"\n{'='*80}")
        print(f"  REPORTE DE SOLAPAMIENTO - AÑO {year}")
        print(f"  Estancias que cruzan el cambio de año")
        print(f"{'='*80}")
        
        df_overlap = diagnose_year_overlap(int(year))
        
        if df_overlap.empty:
            print("\n✓ No hay estancias en este período.")
        else:
            # Separar por tipo
            df_anterior = df_overlap[df_overlap['tipo_solapamiento'] == 'ingreso_año_anterior']
            df_siguiente = df_overlap[df_overlap['tipo_solapamiento'] == 'alta_año_siguiente']
            df_dentro = df_overlap[df_overlap['tipo_solapamiento'] == 'dentro_del_año']
            
            # Resumen general
            print(f"\n>>> RESUMEN GENERAL:")
            print(f"    Total estancias que solapan con {year}: {len(df_overlap)}")
            print(f"    - Ingresos del año anterior (alta en {year}): {len(df_anterior)}")
            print(f"    - Altas del año siguiente (ingreso en {year}): {len(df_siguiente)}")
            print(f"    - Completamente dentro de {year}: {len(df_dentro)}")
            
            # Detalle por unidad
            print(f"\n>>> DETALLE POR UNIDAD:")
            for unit in UNITS:
                unit_total = df_overlap[df_overlap['ou_loc_ref'] == unit]
                unit_anterior = df_anterior[df_anterior['ou_loc_ref'] == unit]
                unit_siguiente = df_siguiente[df_siguiente['ou_loc_ref'] == unit]
                
                print(f"\n    {unit}:")
                print(f"      Ingresos del año anterior: {len(unit_anterior)}")
                print(f"      Altas del año siguiente: {len(unit_siguiente)}")
                print(f"      Total con solapamiento: {len(unit_anterior) + len(unit_siguiente)} de {len(unit_total)} ({(len(unit_anterior) + len(unit_siguiente)) / len(unit_total) * 100 if len(unit_total) > 0 else 0:.1f}%)")
            
            # Mostrar casos de solapamiento
            df_solapamiento = df_overlap[df_overlap['tipo_solapamiento'] != 'dentro_del_año']
            
            if not df_solapamiento.empty:
                print(f"\n>>> DETALLE DE CASOS CON SOLAPAMIENTO ({len(df_solapamiento)} total):")
                print(f"{'─'*120}")
                
                df_display = df_solapamiento.copy()
                df_display['true_start_date'] = pd.to_datetime(df_display['true_start_date']).dt.strftime('%Y-%m-%d %H:%M')
                df_display['true_end_date'] = pd.to_datetime(df_display['true_end_date']).dt.strftime('%Y-%m-%d %H:%M')
                
                print(df_display.to_string(index=False))
                
                # Guardar CSV (sin datos identificativos)
                output_dir = Path(__file__).parent / "output"
                output_dir.mkdir(exist_ok=True)
                df_solapamiento_safe = df_solapamiento.drop(columns=['patient_ref', 'episode_ref'], errors='ignore')
                output_path = output_dir / f"year_overlap_{year}.csv"
                df_solapamiento_safe.to_csv(output_path, index=False)
                print(f"\n✓ Detalle guardado en: {output_path}")
            else:
                print(f"\n✓ No hay estancias que crucen el cambio de año.")
    
    else:
        print("Opción no válida")


if __name__ == "__main__":
    main()
