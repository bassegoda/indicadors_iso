import sys
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 1. Setup Project Root using Pathlib (Clean & Modern)
# Assuming this script is inside a folder one level deep (e.g., /scripts/myscript.py)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

from connection import execute_query as eq

# 2. Load and Execute SQL
sql_file_path = project_root / "deliris" / "deliris.sql"

try:
    with open(sql_file_path, "r", encoding="utf-8") as file:
        query = file.read()
    df = eq(query)
except FileNotFoundError:
    print(f"Error: Could not find SQL file at {sql_file_path}")
    sys.exit(1)

# Check if data exists
if df.empty:
    print("No data returned from the query.")
    sys.exit()

# 3. Clean & Map Data (Do this globally first)
# Using a dictionary map is faster and cleaner than 3 separate .loc calls
result_mapping = {
    'DELIRIO_CAM-ICU_1': 'Absent',
    'DELIRIO_CAM-ICU_2': 'Present',
    'DELIRIO_CAM-ICU_3': 'Other'
}
df['result_txt'] = df['result_txt'].replace(result_mapping)

# 4. Prepare Plot Data
# Sorting by count descending makes the chart easier to read
icu_counts = df['ou_loc_ref'].value_counts().reset_index()
icu_counts.columns = ['ICU', 'Count']
icu_counts = icu_counts.sort_values('Count', ascending=False)

# 5. Plotting
plt.figure(figsize=(10, 6))
sns.set_theme(style="whitegrid")

# Create the plot object (ax) to manipulate it later
ax = sns.barplot(
    data=icu_counts,
    x="ICU",
    y="Count",
    hue="ICU",
    palette="viridis",
    legend=False,
    order=icu_counts['ICU'] # Ensure plot follows our sorted order
)

# Title and Labels
plt.title("Recompte d'avaluacions de delirium (1r Quatrimestre 2025)", fontsize=16, fontweight='bold', color='#333')
plt.xlabel("Unitat (ICU)", fontsize=12)
plt.ylabel("Nombre de registres", fontsize=12)

# Modern way to add labels (No need for manual loops/calculations)
ax.bar_label(ax.containers[0], padding=3, fontsize=10)

plt.tight_layout()

# Save plot
output_path = project_root / "deliris" / "icu_delirium_counts_2025.png"
plt.savefig(output_path, dpi=400)
print(f"Plot saved to: {output_path}")

# 6. Specific Statistics for Hepàtica (E073, I073)
print("\n" + "=" * 52)
print("Recompte d'avaluacions de delirium a E073 i I073")
print("=" * 52)

hepatica_units = ['E073', 'I073']
# Filter
df_hepatica = df[df['ou_loc_ref'].isin(hepatica_units)]
delirium_counts = df_hepatica['result_txt'].value_counts()

print(delirium_counts)

print("-" * 52)

# Calculate Proportion
total_assessments = delirium_counts.sum()
delirium_present = delirium_counts.get('Present', 0)

# Used logic: if total > 0 calculate, else 0
proportion_delirium = (delirium_present / total_assessments * 100) if total_assessments > 0 else 0

print(f"Total Avaluacions: {total_assessments}")
print(f"Casos Positius (Present): {delirium_present}")
print(f"Proporció de delirium present: {proportion_delirium:.2f}%")
print("=" * 52)