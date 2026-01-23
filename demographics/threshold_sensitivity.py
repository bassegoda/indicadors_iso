import pandas as pd
import sys
from pathlib import Path

# Añadir directorio raíz al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from connection import execute_query

# ==========================================
# SQL TEMPLATE - EXTRAE TODOS LOS DATOS SIN FILTRO DE THRESHOLD
# ==========================================
SQL_TEMPLATE = """
WITH raw_moves AS (
    SELECT
        patient_ref,
        episode_ref,
        ou_loc_ref,
        start_date,
        end_date
    FROM g_movements
    WHERE ou_loc_ref IN ({units_formatted})
      AND start_date BETWEEN '{year}-01-01' AND '{year}-12-31 23:59:59'
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
    total_hours / 24 as days
FROM cohort
ORDER BY total_hours;
"""

# ==========================================
# ANALYSIS LOGIC
# ==========================================
def analyze_threshold_sensitivity(year, unit_list, thresholds, max_days_filter=None):
    """Analiza la sensibilidad del umbral temporal en horas."""

    sql_units_formatted = ", ".join([f"'{u}'" for u in unit_list])

    print("\n" + "=" * 80)
    print(f"  THRESHOLD SENSITIVITY ANALYSIS - Year: {year}, Units: {', '.join(unit_list)}")
    print("=" * 80 + "\n")

    # Ejecutar query UNA SOLA VEZ para obtener todos los datos
    print("Fetching data from database (this may take a moment)...")
    query = SQL_TEMPLATE.format(
        year=year,
        units_formatted=sql_units_formatted
    )

    df_all = execute_query(query)

    if df_all.empty:
        print("No data found for the specified year and units.")
        return pd.DataFrame()

    # Convertir a float para evitar problemas con Decimal
    df_all['total_hours'] = df_all['total_hours'].astype(float)
    df_all['days'] = df_all['days'].astype(float)

    print(f"Total records fetched: {len(df_all)}")

    # Mostrar información sobre outliers
    print(f"\nData quality check:")
    print(f"  Min days: {df_all['days'].min():.1f}")
    print(f"  Max days: {df_all['days'].max():.1f}")
    print(f"  Mean days: {df_all['days'].mean():.1f}")
    print(f"  Median days: {df_all['days'].median():.1f}")

    # Identificar outliers extremos (>365 días = 1 año)
    extreme_outliers = df_all[df_all['days'] > 365]
    if len(extreme_outliers) > 0:
        print(f"  ⚠️  WARNING: {len(extreme_outliers)} records with >365 days detected!")
        print(f"      These extreme values may skew the mean significantly.")
        print(f"      Max outlier: {extreme_outliers['days'].max():.1f} days")

    # Aplicar filtro de días máximos si se especifica
    if max_days_filter is not None:
        df_filtered_count = len(df_all[df_all['days'] > max_days_filter])
        df_all = df_all[df_all['days'] <= max_days_filter].copy()
        print(f"\n  Filtering: Excluding {df_filtered_count} records with >{max_days_filter} days")
        print(f"  Records after filter: {len(df_all)}")

    print(f"\nAnalyzing {len(thresholds)} different thresholds...\n")

    # Analizar cada umbral en Python (mucho más rápido)
    results = []
    for threshold in thresholds:
        print(f"Processing threshold: {threshold} hours...", end=" ")

        # Filtrar datos según el umbral
        df_filtered = df_all[df_all['total_hours'] >= threshold].copy()

        if not df_filtered.empty and len(df_filtered) > 0:
            days = df_filtered['days']

            result = {
                'threshold_hours': threshold,
                'total_admissions': len(df_filtered),
                'unique_patients': df_filtered['patient_ref'].nunique(),
                'unique_episodes': df_filtered['episode_ref'].nunique(),
                'mean_days': round(days.mean(), 1),
                'sd_days': round(days.std(), 1),
                'median_days': round(days.median(), 1),
                'q1_days': round(days.quantile(0.25), 1),
                'q3_days': round(days.quantile(0.75), 1)
            }
            print(f"✓ {result['total_admissions']} admissions")
        else:
            result = {
                'threshold_hours': threshold,
                'total_admissions': 0,
                'unique_patients': 0,
                'unique_episodes': 0,
                'mean_days': None,
                'sd_days': None,
                'median_days': None,
                'q1_days': None,
                'q3_days': None
            }
            print("✓ 0 admissions")

        results.append(result)

    # Crear DataFrame de resultados
    results_df = pd.DataFrame(results)

    # Calcular diferencias respecto al umbral anterior
    results_df['admissions_diff'] = results_df['total_admissions'].diff()
    results_df['admissions_diff_pct'] = (
        results_df['total_admissions'].pct_change() * 100
    ).round(2)

    return results_df


def save_results(results_df, year, unit_list):
    """Guarda los resultados en CSV y genera un reporte HTML."""

    # Crear carpeta output si no existe
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    units_str = "-".join(unit_list).replace(" ", "")

    # Guardar CSV
    csv_filename = output_dir / f"threshold_sensitivity_{year}_{units_str}.csv"
    results_df.to_csv(csv_filename, index=False, encoding='utf-8')
    print(f"\n✓ CSV guardado en: {csv_filename}")

    # Generar HTML
    html_filename = output_dir / f"threshold_sensitivity_{year}_{units_str}.html"

    # Formatear el DataFrame para mejor visualización
    display_df = results_df.copy()
    display_df['threshold_hours'] = display_df['threshold_hours'].astype(int)
    display_df['total_admissions'] = display_df['total_admissions'].astype(int)
    display_df['unique_patients'] = display_df['unique_patients'].astype(int)
    display_df['unique_episodes'] = display_df['unique_episodes'].astype(int)

    # Crear columnas combinadas para mejor presentación
    display_df['Mean (SD)'] = display_df.apply(
        lambda row: f"{row['mean_days']:.1f} ({row['sd_days']:.1f})"
        if pd.notna(row['mean_days']) and pd.notna(row['sd_days']) else "N/A",
        axis=1
    )

    display_df['Median [IQR]'] = display_df.apply(
        lambda row: f"{row['median_days']:.1f} [{row['q1_days']:.1f}-{row['q3_days']:.1f}]"
        if pd.notna(row['median_days']) and pd.notna(row['q1_days']) and pd.notna(row['q3_days']) else "N/A",
        axis=1
    )

    # Formatear diferencias
    display_df['admissions_diff'] = display_df['admissions_diff'].apply(
        lambda x: f"{int(x)}" if pd.notna(x) else "-"
    )
    display_df['admissions_diff_pct'] = display_df['admissions_diff_pct'].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
    )

    # Seleccionar solo las columnas que queremos mostrar
    display_df = display_df[[
        'threshold_hours',
        'total_admissions',
        'unique_patients',
        'unique_episodes',
        'Mean (SD)',
        'Median [IQR]',
        'admissions_diff',
        'admissions_diff_pct'
    ]]

    # Renombrar columnas para el HTML
    display_df.columns = [
        'Threshold (hours)',
        'Total Admissions',
        'Unique Patients',
        'Unique Episodes',
        'Mean Days (SD)',
        'Median Days [IQR]',
        'Diff vs Previous',
        'Diff % vs Previous'
    ]

    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 30px;
            }}
            .info {{
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: right;
            }}
            th {{
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            tr:hover {{
                background-color: #e8f4f8;
            }}
            td:first-child, th:first-child {{
                text-align: center;
                font-weight: bold;
            }}
            .summary {{
                background-color: #d5f4e6;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .summary h3 {{
                color: #27ae60;
                margin-top: 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Threshold Sensitivity Analysis</h1>

            <div class="info">
                <p><strong>Year:</strong> {year}</p>
                <p><strong>Units:</strong> {', '.join(unit_list)}</p>
                <p><strong>Analysis Date:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <h2>Results by Threshold</h2>
            {display_df.to_html(index=False, escape=False)}

            <div class="summary">
                <h3>Summary</h3>
                <p>• <strong>Minimum threshold tested:</strong> {int(results_df['threshold_hours'].min())} hours</p>
                <p>• <strong>Maximum threshold tested:</strong> {int(results_df['threshold_hours'].max())} hours</p>
                <p>• <strong>Total admissions range:</strong> {int(results_df['total_admissions'].min())} - {int(results_df['total_admissions'].max())}</p>
                <p>• <strong>Maximum difference between thresholds:</strong> {int(results_df['admissions_diff'].abs().max())} admissions</p>
            </div>
        </div>
    </body>
    </html>
    """

    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ HTML report guardado en: {html_filename}")


def print_summary(results_df):
    """Imprime un resumen en consola."""

    print("\n" + "=" * 100)
    print("  SUMMARY")
    print("=" * 100)

    for _, row in results_df.iterrows():
        threshold = int(row['threshold_hours'])
        admissions = int(row['total_admissions'])
        diff = row['admissions_diff']
        diff_pct = row['admissions_diff_pct']

        mean = row['mean_days']
        sd = row['sd_days']
        median = row['median_days']
        q1 = row['q1_days']
        q3 = row['q3_days']

        print(f"\nThreshold: {threshold:2d}h → {admissions:4d} admissions", end="")

        if pd.notna(diff):
            diff_int = int(diff)
            sign = "+" if diff_int >= 0 else ""
            print(f"  [{sign}{diff_int:3d}, {sign}{diff_pct:.2f}%]", end="")

        if pd.notna(mean) and pd.notna(median):
            print(f"\n    Mean: {mean:.1f}±{sd:.1f} days  |  Median: {median:.1f} [{q1:.1f}-{q3:.1f}] days", end="")

        print()

    print("\n" + "=" * 100 + "\n")


# ==========================================
# MAIN FLOW
# ==========================================
def main():
    """Flux principal d'execució."""
    print("=" * 80)
    print("   THRESHOLD SENSITIVITY ANALYSIS FOR ICU ADMISSIONS")
    print("=" * 80)

    year_input = input("\nEnter Year (e.g., 2024): ").strip()
    units_input = input("Enter Units separated by commas (e.g., E073, I073): ").strip()

    # Preguntar por umbrales personalizados o usar los predefinidos
    use_custom = input("\nUse custom thresholds? [y/N]: ").strip().lower()

    if use_custom in ("y", "yes", "s", "si"):
        thresholds_input = input("Enter thresholds in hours separated by commas (e.g., 3,5,8,10,15,20): ").strip()
        thresholds = [int(t.strip()) for t in thresholds_input.split(',')]
        thresholds.sort()
    else:
        thresholds = [5, 10, 15, 20]

    # Preguntar por filtro de outliers
    filter_outliers = input("\nFilter extreme outliers? [y/N]: ").strip().lower()
    max_days_filter = None
    if filter_outliers in ("y", "yes", "s", "si"):
        max_days_input = input("Maximum days to include (e.g., 365): ").strip()
        max_days_filter = float(max_days_input) if max_days_input else 365

    unit_list = [u.strip() for u in units_input.split(',')]

    print(f"\nAnalyzing thresholds: {thresholds} hours")
    print(f"Units: {', '.join(unit_list)}")
    print(f"Year: {year_input}")
    if max_days_filter:
        print(f"Max days filter: {max_days_filter}")
    print()

    # Ejecutar análisis
    results_df = analyze_threshold_sensitivity(year_input, unit_list, thresholds, max_days_filter)

    # Mostrar resumen
    print_summary(results_df)

    # Guardar resultados
    save_results(results_df, year_input, unit_list)

    print("\n✓ Analysis completed successfully!\n")


if __name__ == "__main__":
    main()
