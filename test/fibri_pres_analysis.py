import pandas as pd
import numpy as np
from pathlib import Path

def analyze_fibrinogen_pres(csv_path):
    if not Path(csv_path).exists():
        print(f"Error: No s'ha trobat el fitxer {csv_path}")
        return

    # Carregar dades
    df = pd.read_csv(csv_path)
    
    if df.empty:
        print("El fitxer CSV està buit.")
        return

    print("=" * 60)
    print("ANÀLISI DE PRESCRIUCCIÓ DE FIBRINOGEN (2024)")
    print("=" * 60)

    # Identificació de casos segons laboratori
    df_lab = df[df['fib_level_g_l'].notnull()]
    df_blind = df[df['fib_level_g_l'].isnull()]

    # 1. Volumetria General
    total_pres = len(df)
    unique_patients = df['patient_ref'].nunique()
    total_grams = df['quantity'].sum()
    pres_lab = len(df_lab)
    pres_blind = len(df_blind)

    print(f"\n[1] MÈTRIQUES DE VOLUM DE PRESCRIUCCIÓ")
    print(f"  - Prescripcions totals: {total_pres}")
    print(f"  - Grams totals:          {total_grams:.2f} g")
    print(f"  - Traçabilitat al SAP:")
    print(f"    - Amb analítica prèvia:  {pres_lab} ({pres_lab/total_pres*100:.1f}%)")
    print(f"    - Sense analítica (CEC?): {pres_blind} ({pres_blind/total_pres*100:.1f}%)")
    print(f"  - Pacients únics:        {unique_patients}")
    print(f"  - Dosi mitjana:          {df['quantity'].mean():.2f} g")

    # 2. Perfil Clínic
    if not df_lab.empty:
        avg_fib = df_lab['fib_level_g_l'].mean()
        med_fib = df_lab['fib_level_g_l'].median()
        low_fib_20 = (df_lab['fib_level_g_l'] < 2.0).sum()
        low_fib_15 = (df_lab['fib_level_g_l'] < 1.5).sum()

        print(f"\n[2] PERFIL CLÍNIC AL MOMENT DE PRESCRIURE")
        print(f"  - Nivell mitjà:          {avg_fib:.2f} g/L")
        print(f"  - Nivell medià:          {med_fib:.2f} g/L")
        print(f"  - Casos amb Fib < 2.0:   {low_fib_20} ({low_fib_20/pres_lab*100:.1f}%)")
        print(f"  - Casos amb Fib < 1.5:   {low_fib_15} ({low_fib_15/pres_lab*100:.1f}%)")

    # 3. Eficiència del Prescriptor (Temps des de Resultat -> Prescripció)
    if not df_lab.empty:
        times = df_lab[df_lab['minutes_result_to_pres'] >= 0]['minutes_result_to_pres']
        avg_time = times.mean()
        med_time = times.median()

        print(f"\n[3] EFICIÈNCIA DEL PRESCRIPTOR (Resultat -> Prescripció)")
        print(f"  - Temps mitjà de resposta: {avg_time:.1f} minuts")
        print(f"  - Temps medià (p50):       {med_time:.1f} minuts")
        print(f"  - Resposta ràpida (<1h):   {(times <= 60).sum()} ({(times <= 60).sum()/pres_lab*100:.1f}%)")

    # 4. Diferències entre Admin i Pres (Comentari teòric per l'usuari)
    print(f"\n[4] OBSERVACIONS")
    print("  - Les prescripcions solen reflectir la intenció del metge.")
    print("  - Una menor quantitat de prescripcions respecte a administracions pot")
    print("    indicar recàrregues d'una mateixa pauta o ordres de planta.")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    csv_file = Path(__file__).parent / "fibri_pres.csv"
    analyze_fibrinogen_pres(csv_file)
