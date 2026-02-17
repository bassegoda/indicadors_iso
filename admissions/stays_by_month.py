"""
ESTANCIAS POR MES DE INICIO

Analiza la cantidad de estancias por mes de inicio de la estancia.
Usa la misma lógica que hosp_ward_longest_stay_no_prescription.py:
- Sin filtro de prescripciones
- Asignación por unidad predominante (longest stay principle)

Parámetros:
- Año: año a analizar
- Unidad: unidad de hospitalización (ej: E073, I073)

Output:
- CSV con conteo de estancias por mes
- Gráfico de barras (PNG)
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

# Add root directory to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query


# ==========================================
# CONFIGURATION
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ==========================================
# SQL BUILDER
# ==========================================
def build_hours_per_unit_cases(units: list) -> str:
    """Build CASE statements for hours per unit."""
    cases = []
    for unit in units:
        cases.append(f"""
        SUM(CASE WHEN g.ou_loc_ref = '{unit}' 
            THEN TIMESTAMPDIFF(MINUTE, g.start_date, COALESCE(g.end_date, NOW())) 
            ELSE 0 END) as minutes_{unit}""")
    return ",".join(cases)


def build_sql_query(units: list) -> str:
    """Build complete SQL query with dynamic units."""
    units_list = "'" + "','".join(units) + "'"
    hours_cases = build_hours_per_unit_cases(units)
    
    # Build column list for final SELECT
    hours_columns = ",\n    ".join([f"c.minutes_{unit}" for unit in units])
    
    return f"""
WITH all_related_moves AS (
    -- Get movements from all specified units
    -- end_date can be NULL (patient still admitted); use NOW() as proxy
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date,
        COALESCE(end_date, NOW()) AS effective_end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_list})
      AND start_date <= '{{year}}-12-31 23:59:59'
      AND COALESCE(end_date, NOW()) >= '{{year}}-01-01 00:00:00'
      AND place_ref IS NOT NULL
      AND COALESCE(end_date, NOW()) > start_date
),
flagged_starts AS (
    -- Mark where new stays begin (across all units)
    -- Tolerance: movements within 5 minutes are considered consecutive
    SELECT 
        *,
        CASE 
            WHEN ABS(TIMESTAMPDIFF(MINUTE, 
                LAG(effective_end_date) OVER (
                    PARTITION BY episode_ref ORDER BY start_date
                ), 
                start_date
            )) <= 5
            THEN 0 
            ELSE 1 
        END AS is_new_stay
    FROM all_related_moves
),
grouped_stays AS (
    -- Number each stay within the episode
    SELECT 
        *,
        SUM(is_new_stay) OVER (
            PARTITION BY episode_ref ORDER BY start_date
        ) as stay_id
    FROM flagged_starts
),
time_per_unit AS (
    -- Calculate MINUTES spent in each unit per stay (minutes avoids truncation)
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref,
        SUM(TIMESTAMPDIFF(MINUTE, start_date, effective_end_date)) as minutes_in_unit
    FROM grouped_stays
    GROUP BY patient_ref, episode_ref, stay_id, ou_loc_ref
),
predominant_unit AS (
    -- Identify unit with most time per stay
    -- ROW_NUMBER with first-visited tiebreaker to avoid duplicates on ties
    SELECT
        patient_ref,
        episode_ref,
        stay_id,
        ou_loc_ref as assigned_unit,
        minutes_in_unit as max_minutes
    FROM (
        SELECT
            t.patient_ref,
            t.episode_ref,
            t.stay_id,
            t.ou_loc_ref,
            t.minutes_in_unit,
            ROW_NUMBER() OVER (
                PARTITION BY t.patient_ref, t.episode_ref, t.stay_id
                ORDER BY t.minutes_in_unit DESC, MIN(g.start_date) ASC
            ) as rn
        FROM time_per_unit t
        INNER JOIN grouped_stays g
            ON t.patient_ref = g.patient_ref
            AND t.episode_ref = g.episode_ref
            AND t.stay_id = g.stay_id
            AND t.ou_loc_ref = g.ou_loc_ref
        GROUP BY t.patient_ref, t.episode_ref, t.stay_id, 
                 t.ou_loc_ref, t.minutes_in_unit
    ) ranked
    WHERE rn = 1
),
cohort AS (
    -- Merge movements into complete stays
    SELECT
        g.patient_ref,
        g.episode_ref,
        g.stay_id,
        p.assigned_unit as ou_loc_ref,
        MIN(g.start_date) as admission_date,
        MAX(g.end_date) as discharge_date,
        MAX(g.effective_end_date) as effective_discharge_date,
        TIMESTAMPDIFF(HOUR, MIN(g.start_date), MAX(g.effective_end_date)) AS hours_stay,
        TIMESTAMPDIFF(DAY, MIN(g.start_date), MAX(g.effective_end_date)) AS days_stay,
        TIMESTAMPDIFF(MINUTE, MIN(g.start_date), MAX(g.effective_end_date)) AS minutes_stay,
        CASE WHEN MAX(g.end_date) IS NULL THEN 'Yes' ELSE 'No' END as still_admitted,
        COUNT(*) as num_movements,
        COUNT(DISTINCT g.ou_loc_ref) as num_units_visited,{hours_cases}
    FROM grouped_stays g
    INNER JOIN predominant_unit p
        ON g.patient_ref = p.patient_ref
        AND g.episode_ref = p.episode_ref
        AND g.stay_id = p.stay_id
    GROUP BY g.patient_ref, g.episode_ref, g.stay_id, p.assigned_unit
    HAVING YEAR(MIN(g.start_date)) = {{year}}
       AND p.assigned_unit = '{{unit}}'  -- Only stays assigned to requested unit
)
SELECT DISTINCT
    c.patient_ref,
    c.episode_ref,
    c.stay_id,
    c.ou_loc_ref,
    c.admission_date,
    c.discharge_date,
    c.effective_discharge_date,
    c.hours_stay,
    c.days_stay,
    c.minutes_stay,
    c.still_admitted,
    c.num_movements,
    c.num_units_visited,
    {hours_columns},
    CASE 
        WHEN c.num_units_visited > 1 THEN 'Yes' 
        ELSE 'No' 
    END as had_transfer,
    YEAR(c.admission_date) as year_admission,
    TIMESTAMPDIFF(YEAR, d.birth_date, c.admission_date) as age_at_admission,
    CASE
        WHEN d.sex = 1 THEN 'Male'
        WHEN d.sex = 2 THEN 'Female'
        WHEN d.sex = 3 THEN 'Other'
        ELSE 'Not reported'
    END as sex,
    CASE
        WHEN ex.exitus_date IS NOT NULL
             AND ex.exitus_date BETWEEN c.admission_date 
                 AND c.effective_discharge_date
        THEN 'Yes'
        ELSE 'No'
    END as exitus_during_stay,
    ex.exitus_date
FROM cohort c
LEFT JOIN g_demographics d 
    ON c.patient_ref = d.patient_ref
LEFT JOIN g_exitus ex 
    ON c.patient_ref = ex.patient_ref
ORDER BY c.admission_date;
"""


# ==========================================
# FUNCTIONS
# ==========================================
def get_year_from_user() -> int:
    """Prompt user for year to analyse."""
    while True:
        print("\nAño a analizar (ej: 2024): ", end="")
        user_input = input().strip()
        
        try:
            year = int(user_input)
            if year < 2000 or year > 2100:
                print("❌ Error: Año debe estar entre 2000 y 2100.")
                continue
            return year
        except ValueError:
            print("❌ Error: Debe ingresar un año válido (ej: 2024).")
            continue


def get_unit_from_user() -> str:
    """Prompt user for unit to analyse."""
    while True:
        print("Unidad a analizar (ej: E073, I073): ", end="")
        user_input = input().strip().upper()
        
        if not user_input:
            print("❌ Error: Debe especificar una unidad.")
            continue
        
        return user_input


def create_month_label(date_series: pd.Series) -> pd.Series:
    """
    Create month label (e.g., "2024-01", "2024-02").
    """
    dates = pd.to_datetime(date_series)
    return dates.dt.strftime('%Y-%m')


def create_monthly_summary(df: pd.DataFrame, year: int, unit: str) -> pd.DataFrame:
    """
    Create monthly summary of stays.
    Returns DataFrame with columns: month_start, month_label, count
    """
    if df.empty:
        return pd.DataFrame(columns=['month_start', 'month_label', 'count'])
    
    # Create month label (e.g., "2024-01", "2024-02")
    df['month_label'] = create_month_label(df['admission_date'])
    
    # Group by month_label and count
    monthly_counts = df.groupby('month_label').size().reset_index(name='count')
    monthly_counts = monthly_counts.sort_values('month_label')
    
    # Ensure all months of the year are included (fill with 0)
    all_months = pd.date_range(
        start=f'{year}-01-01',
        end=f'{year}-12-01',
        freq='MS'  # Month Start
    )
    
    # Create complete monthly series
    all_months_df = pd.DataFrame({
        'month_start': all_months
    })
    all_months_df['month_label'] = create_month_label(all_months_df['month_start'])
    
    # Merge with actual counts using month_label as key
    monthly_summary = all_months_df.merge(
        monthly_counts,
        on='month_label',
        how='left'
    )
    monthly_summary['count'] = monthly_summary['count'].fillna(0).astype(int)
    
    # Convert month_start to date for CSV output
    monthly_summary['month_start'] = pd.to_datetime(monthly_summary['month_start']).dt.date
    
    # Sort by month_start
    monthly_summary = monthly_summary.sort_values('month_start').reset_index(drop=True)
    
    return monthly_summary


def create_bar_chart(monthly_summary: pd.DataFrame, year: int, unit: str, output_path: Path):
    """
    Create bar chart of stays per month.
    """
    if monthly_summary.empty:
        print("⚠️  No hay datos para generar el gráfico.")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")
    
    # Create bars
    bars = ax.bar(
        range(len(monthly_summary)),
        monthly_summary['count'],
        color='#2E86AB',
        alpha=0.85,
        width=0.7,
        edgecolor='white',
        linewidth=0.5
    )
    
    # Add value labels on top of bars
    max_count = monthly_summary['count'].max()
    for i, (bar, count) in enumerate(zip(bars, monthly_summary['count'])):
        if count > 0:
            offset = max_count * 0.01 if max_count > 0 else 1
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                count + offset,
                f'{count}',
                ha='center',
                va='bottom',
                fontsize=9,
                fontweight='bold'
            )
    
    # Set labels and title
    ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
    ax.set_ylabel('Número de Estancias', fontsize=11, fontweight='bold')
    ax.set_title(
        f'Estancias por Mes de Inicio - {unit} ({year})',
        fontsize=13,
        fontweight='bold',
        pad=20
    )
    
    # Set x-axis ticks (show all months)
    tick_positions = range(len(monthly_summary))
    # Format month labels: "2024-01" -> "Ene 2024"
    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    tick_labels = []
    for label in monthly_summary['month_label']:
        month_num = int(label.split('-')[1])
        tick_labels.append(f"{month_names[month_num-1]} {year}")
    
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10)
    
    # Set y-axis to start at 0
    max_count = monthly_summary['count'].max()
    if max_count > 0:
        ax.set_ylim(bottom=0, top=max_count * 1.15)
    else:
        ax.set_ylim(bottom=0, top=1)
    
    # Add grid for better readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Add summary statistics as text
    total_stays = monthly_summary['count'].sum()
    avg_per_month = monthly_summary['count'].mean()
    max_month = monthly_summary.loc[monthly_summary['count'].idxmax()]
    
    # Format month name for display
    month_num = int(max_month['month_label'].split('-')[1])
    month_name = month_names[month_num-1]
    
    stats_text = (
        f'Total: {total_stays} estancias | '
        f'Promedio/mes: {avg_per_month:.1f} | '
        f'Máximo: {max_month["count"]} ({month_name})'
    )
    ax.text(
        0.5,
        -0.12,
        stats_text,
        transform=ax.transAxes,
        ha='center',
        fontsize=9,
        style='italic'
    )
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"        → Gráfico guardado: {output_path.name}")


def process_unit(year: int, unit: str):
    """Process a single unit and generate weekly analysis."""
    # Build units list (for predominance analysis, we need at least the unit itself)
    # If only one unit, we still use the same logic but it will only have that unit
    units = [unit]
    
    # Build SQL query
    sql_template = build_sql_query(units)
    query = sql_template.format(year=year, unit=unit)
    
    # Execute query
    print(f"\nEjecutando consulta para {unit} ({year})...")
    df = execute_query(query)
    
    if df.empty:
        print(f"❌ No se encontraron datos para {unit} en {year}")
        return
    
    print(f"✓ {len(df)} estancias encontradas")
    
    # Convert admission_date to datetime if needed
    df['admission_date'] = pd.to_datetime(df['admission_date'])
    
    # Diagnostic: Check date range
    min_date = df['admission_date'].min()
    max_date = df['admission_date'].max()
    print(f"   Rango de fechas: {min_date.strftime('%Y-%m-%d')} a {max_date.strftime('%Y-%m-%d')}")
    
    # Diagnostic: Check distribution by month
    df['month'] = df['admission_date'].dt.to_period('M')
    monthly_dist = df.groupby('month').size()
    print(f"   Distribución por mes:")
    for month, count in monthly_dist.items():
        print(f"      {month}: {count} estancias")
    
    # Create monthly summary
    monthly_summary = create_monthly_summary(df, year, unit)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV
    csv_filename = OUTPUT_DIR / f"estancias_mensuales_{unit}_{year}_{timestamp}.csv"
    monthly_summary.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"        → CSV guardado: {csv_filename.name}")
    
    # Create bar chart
    chart_filename = OUTPUT_DIR / f"estancias_mensuales_{unit}_{year}_{timestamp}.png"
    create_bar_chart(monthly_summary, year, unit, chart_filename)
    
    # Print summary
    total_stays = monthly_summary['count'].sum()
    avg_per_month = monthly_summary['count'].mean()
    max_month = monthly_summary.loc[monthly_summary['count'].idxmax()]
    min_month = monthly_summary.loc[monthly_summary['count'].idxmin()]
    
    # Format month names for display
    month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    max_month_num = int(max_month['month_label'].split('-')[1])
    min_month_num = int(min_month['month_label'].split('-')[1])
    
    print(f"\n📊 Resumen:")
    print(f"   Total estancias: {total_stays}")
    print(f"   Promedio por mes: {avg_per_month:.1f}")
    print(f"   Mes con más estancias: {month_names[max_month_num-1]} ({max_month['count']} estancias)")
    print(f"   Mes con menos estancias: {month_names[min_month_num-1]} ({min_month['count']} estancias)")
    print(f"   Meses con estancias: {(monthly_summary['count'] > 0).sum()}/{len(monthly_summary)}")


# ==========================================
# MAIN
# ==========================================
def main():
    print("\n" + "="*70)
    print("  ESTANCIAS POR MES DE INICIO")
    print("="*70)
    print("  Análisis mensual de estancias hospitalarias")
    print("  Sin filtro de prescripciones")
    print("="*70)
    
    year = get_year_from_user()
    unit = get_unit_from_user()
    
    process_unit(year, unit)
    
    print(f"\n✓ Archivos guardados en: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
