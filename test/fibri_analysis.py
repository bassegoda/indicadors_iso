import pandas as pd
import numpy as np
from pathlib import Path

def analyze_fibrinogen(csv_path):
    if not Path(csv_path).exists():
        print(f"Error: No s'ha trobat el fitxer {csv_path}")
        return

    # Carregar dades
    df = pd.read_csv(csv_path)
    
    if df.empty:
        print("El fitxer CSV està buit.")
        return

    print("=" * 60)
    print("ANÀLISI D'ÚS DE FIBRINOGEN (2024)")
    print("=" * 60)

    # Identificar casos seguits per lab vs seguits per tromboelastograma/clínica
    # Els casos sense fib_level_g_l són aquells que no tenien analítica prèvia al SAP
    df_lab = df[df['fib_level_g_l'].notnull()]
    df_blind = df[df['fib_level_g_l'].isnull()]

    # 1. Volumetria General
    total_admins = len(df)
    unique_patients = df['patient_ref'].nunique()
    total_grams = df['quantity'].sum()
    admins_lab = len(df_lab)
    admins_blind = len(df_blind)

    print(f"\n[1] MÈTRIQUES DE VOLUM I TRAÇABILITAT")
    print(f"  - Administracions totals: {total_admins}")
    print(f"  - Grams totals:          {total_grams:.2f} g")
    print(f"  - Traçabilitat al SAP:")
    print(f"    - Amb analítica prèvia:  {admins_lab} ({admins_lab/total_admins*100:.1f}%)")
    print(f"    - Sense analítica (Tromboelastograma?): {admins_blind} ({admins_blind/total_admins*100:.1f}%)")
    print(f"  - Pacients únics:        {unique_patients}")
    print(f"  - Dosi mitjana:          {df['quantity'].mean():.2f} g")

    # 2. Perfil Clínic (Només per als que tenen lab)
    if not df_lab.empty:
        avg_fib = df_lab['fib_level_g_l'].mean()
        med_fib = df_lab['fib_level_g_l'].median()
        low_fib_20 = (df_lab['fib_level_g_l'] < 2.0).sum()
        low_fib_15 = (df_lab['fib_level_g_l'] < 1.5).sum()
        very_low_fib_10 = (df_lab['fib_level_g_l'] < 1.0).sum()

        print(f"\n[2] PERFIL CLÍNIC (Només casos amb analítica al SAP)")
        print(f"  - Nivell mitjà:          {avg_fib:.2f} g/L")
        print(f"  - Nivell medià:          {med_fib:.2f} g/L")
        print(f"  - Casos amb Fib < 2.0:   {low_fib_20} ({low_fib_20/admins_lab*100:.1f}%)")
        print(f"  - Casos amb Fib < 1.5:   {low_fib_15} ({low_fib_15/admins_lab*100:.1f}%)")
        print(f"  - Casos amb Fib < 1.0:   {very_low_fib_10} ({very_low_fib_10/admins_lab*100:.1f}%)")

    # 3. Eficiència Temporal (Només per als que tenen lab)
    if not df_lab.empty:
        times = df_lab[df_lab['minutes_result_to_admin'] >= 0]['minutes_result_to_admin']
        avg_time = times.mean()
        med_time = times.median()

        print(f"\n[3] EFICIÈNCIA (Temps des de Resultat -> Administració)")
        print(f"  - Temps medià (p50):       {med_time:.1f} minuts")
        print(f"  - Resposta ràpida (<1h):   {(times <= 60).sum()} ({(times <= 60).sum()/admins_lab*100:.1f}%)")

    # 4. Comparativa de dosis
    dose_avg_lab = df_lab['quantity'].mean()
    dose_avg_blind = df_blind['quantity'].mean() if not df_blind.empty else 0
    print(f"\n[4] COMPARACIÓ DE DOSIS")
    print(f"  - Dosi mitjana amb analítica SAP:  {dose_avg_lab:.2f} g")
    print(f"  - Dosi mitjana sense analítica:    {dose_avg_blind:.2f} g")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    csv_file = Path(__file__).parent / "fibri.csv"
    analyze_fibrinogen(csv_file)
