"""Sondeos exploratorios sobre la cohorte rectal-MDR (Enterobacterales)
para diseñar las reglas de clasificación BLEE / Carbapenemasa.

Usa los CSVs ya descargados (micro/output/rectal_mdr_<unit>_2019-2025.csv).
Filtra a Enterobacterales del top-10 y lanza dos sondeos contra Metabase:

1. Sondeo `antibiograms`: lista todos los `antibiotic_descr` distintos y
   las sensitivity para los `antibiogram_ref` de la cohorte. Chunk por
   (año × unidad) para esquivar el cap de 2000.
2. Sondeo `micro.result_text`: filas de la cohorte que mencionen
   BLEE/ESBL/Carbapenemasa/KPC/OXA/NDM/VIM/IMP/productor/multiresistente.

Salidas en `micro/output/exploratory/`:
    antibiograms_full.csv       — todas las filas de antibiograma
    antibiotic_descr_freq.csv   — qué tests/antibióticos existen y cuántas filas
    confirmatory_flags.csv      — subset que parece test fenotípico/genotípico
    result_text_flags.csv       — anotaciones libres de fenotipo
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from connection import execute_query  # noqa: E402

OUT_DIR = _REPO_ROOT / "micro" / "output"
EXP_DIR = OUT_DIR / "exploratory"

# Enterobacterales del top-10 (post-merge K. pneumoniae complex, etc.)
ENTERO_RAW_TO_NORM = {
    "Escherichia coli": "Escherichia coli",
    "Klebsiella pneumoniae": "Klebsiella pneumoniae (complex)",
    "Klebsiella pneumoniae complex": "Klebsiella pneumoniae (complex)",
    "Enterobacter cloacae": "Enterobacter cloacae (complex)",
    "Enterobacter cloacae complex": "Enterobacter cloacae (complex)",
    "Citrobacter freundii": "Citrobacter freundii (complex)",
    "Citrobacter freundii complex": "Citrobacter freundii (complex)",
    "Klebsiella oxytoca": "Klebsiella oxytoca",
    "Klebsiella oxytoca/Raoultella ornithynol": "Klebsiella oxytoca/Raoultella",
    "Klebsiella aerogenes": "Klebsiella aerogenes",
    "Klebsiella variicola": "Klebsiella variicola",
    "Proteus mirabilis": "Proteus mirabilis",
    "Serratia marcescens": "Serratia marcescens",
    "Hafnia alvei": "Hafnia alvei",
    "Morganella morganii": "Morganella morganii",
    "Enterobacter sp": "Enterobacter sp",
}

CONFIRMATORY_PAT = re.compile(
    r"BLEE|ESBL|carbapenem|KPC|OXA[- ]?48|NDM|VIM|IMP|mCIM|eCIM|ampc|amp[- ]c",
    flags=re.IGNORECASE,
)


def load_cohort_isolates() -> pd.DataFrame:
    parts = []
    for unit in ("E073", "I073"):
        df = pd.read_csv(OUT_DIR / f"rectal_mdr_{unit}_2019-2025.csv")
        df["unit"] = unit
        parts.append(df)
    full = pd.concat(parts, ignore_index=True)
    full = full[full["micro_descr"].isin(ENTERO_RAW_TO_NORM.keys())].copy()
    full["micro_norm"] = full["micro_descr"].replace(ENTERO_RAW_TO_NORM)
    return full


def fetch_antibiograms_chunked(isolates: pd.DataFrame) -> pd.DataFrame:
    """Descarga antibiograma por (año × unidad) usando antibiogram_ref."""
    chunks = []
    for (year, unit), grp in isolates.groupby(["year_admission", "unit"]):
        refs = sorted({int(x) for x in grp["antibiogram_ref"].dropna().tolist()})
        if not refs:
            print(f"  [{unit} {year}] sin antibiogram_ref")
            continue
        # split por seguridad si la lista IN supera 1000 elementos
        for i in range(0, len(refs), 800):
            sub_refs = refs[i:i + 800]
            in_list = ",".join(str(r) for r in sub_refs)
            sql = f"""
            SELECT
                ab.patient_ref,
                ab.episode_ref,
                ab.antibiogram_ref,
                ab.micro_ref,
                ab.micro_descr,
                ab.antibiotic_ref,
                ab.antibiotic_descr,
                ab.result,
                ab.sensitivity,
                ab.extrac_date
            FROM datascope_gestor_prod.antibiograms ab
            WHERE ab.antibiogram_ref IN ({in_list})
            LIMIT 2000
            """
            df = execute_query(sql, verbose=False)
            chunks.append(df.assign(unit=unit, year_admission=year, chunk_size=len(df)))
            marker = "  ⚠ posible truncado" if len(df) >= 1900 else ""
            print(f"  [{unit} {year} part{i // 800}] {len(df)} filas{marker}")
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def fetch_result_text(isolates: pd.DataFrame) -> pd.DataFrame:
    """Para no replicar la cohorte en Athena, traemos result_text por
    (patient_ref, episode_ref, extrac_date) año a año."""
    chunks = []
    for (year, unit), grp in isolates.groupby(["year_admission", "unit"]):
        if grp.empty:
            continue
        # construimos predicado por (patient_ref, episode_ref) lista
        pairs = grp[["patient_ref", "episode_ref"]].drop_duplicates()
        if pairs.empty:
            continue
        # limit por seguridad
        pairs_chunks = [pairs.iloc[i:i + 400] for i in range(0, len(pairs), 400)]
        for j, pchunk in enumerate(pairs_chunks):
            tuples = ",".join(
                f"({int(p)},{int(e)})"
                for p, e in pchunk.itertuples(index=False, name=None)
            )
            sql = f"""
            SELECT
                m.patient_ref,
                m.episode_ref,
                m.extrac_date,
                m.method_descr,
                m.micro_descr,
                m.result_text
            FROM datascope_gestor_prod.micro m
            WHERE (m.patient_ref, m.episode_ref) IN ({tuples})
              AND m.method_descr LIKE '%Frotis rectal%multi%'
              AND m.positive = 'X'
            LIMIT 2000
            """
            df = execute_query(sql, verbose=False)
            chunks.append(df.assign(unit=unit, year_admission=year))
            marker = "  ⚠ posible truncado" if len(df) >= 1900 else ""
            print(f"  [result_text {unit} {year} part{j}] {len(df)} filas{marker}")
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


def main() -> None:
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    isolates = load_cohort_isolates()
    print(f"\n[cohort] aislados Enterobacterales: {len(isolates)} "
          f"(E073={int((isolates['unit']=='E073').sum())}, "
          f"I073={int((isolates['unit']=='I073').sum())})")

    # ----- Sondeo 1: antibiograms -----
    print("\n[sondeo 1] descargando antibiograms (chunk por unidad × año)…")
    abs_df = fetch_antibiograms_chunked(isolates)
    print(f"[sondeo 1] total filas: {len(abs_df)}")
    abs_df.to_csv(EXP_DIR / "antibiograms_full.csv", index=False)

    if not abs_df.empty:
        freq = (
            abs_df.groupby("antibiotic_descr")
            .agg(
                n_rows=("antibiotic_descr", "size"),
                n_isolates=("antibiogram_ref", "nunique"),
                pct_S=("sensitivity", lambda s: round((s == "S").mean() * 100, 1)),
                pct_R=("sensitivity", lambda s: round((s == "R").mean() * 100, 1)),
                pct_I=("sensitivity", lambda s: round((s == "I").mean() * 100, 1)),
            )
            .reset_index()
            .sort_values("n_rows", ascending=False)
        )
        freq.to_csv(EXP_DIR / "antibiotic_descr_freq.csv", index=False)

        confirm = abs_df[
            abs_df["antibiotic_descr"].fillna("").str.contains(CONFIRMATORY_PAT)
        ]
        confirm.to_csv(EXP_DIR / "confirmatory_flags.csv", index=False)
        confirm_freq = (
            confirm.groupby(["antibiotic_descr", "sensitivity"])
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
        )
        confirm_freq.to_csv(EXP_DIR / "confirmatory_flags_freq.csv", index=False)
    else:
        freq = pd.DataFrame()
        confirm = pd.DataFrame()
        confirm_freq = pd.DataFrame()

    # ----- Sondeo 2: result_text -----
    print("\n[sondeo 2] descargando result_text…")
    rt_df = fetch_result_text(isolates)
    print(f"[sondeo 2] total filas: {len(rt_df)}")
    if not rt_df.empty:
        rt_df["text_lc"] = rt_df["result_text"].fillna("").str.lower()
        rt_df["match"] = rt_df["text_lc"].str.contains(CONFIRMATORY_PAT)
        flagged = rt_df[rt_df["match"]].copy()
        flagged.to_csv(EXP_DIR / "result_text_flags.csv", index=False)
    else:
        flagged = pd.DataFrame()

    # Resumen consola
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"\nAntibiograms — total filas: {len(abs_df)} | aislados con AB: "
          f"{abs_df['antibiogram_ref'].nunique() if not abs_df.empty else 0}")
    if not freq.empty:
        print("\nTop 30 antibióticos por nº de filas:")
        print(freq.head(30).to_string(index=False))
        print(f"\nFilas confirmatorias (BLEE/ESBL/carbapenem/KPC/OXA/NDM/VIM/IMP/mCIM/eCIM/AmpC): "
              f"{len(confirm)}")
        if not confirm_freq.empty:
            print("\nDetalle de tests confirmatorios:")
            print(confirm_freq.to_string(index=False))

    print(f"\nresult_text — filas con anotación fenotípica: {len(flagged)}")
    if not flagged.empty:
        print("\n5 ejemplos de result_text marcado:")
        for _, row in flagged.head(5).iterrows():
            print(f"  - [{row['micro_descr']}] {str(row['result_text'])[:150]}")

    print(f"\nCSVs guardados en: {EXP_DIR.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
