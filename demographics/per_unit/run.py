"""Reporting demográfico/clínico — variante `per_unit`.

NO agrupa traslados entre unidades: si un paciente pasa de E073 a I073
durante el mismo episodio, contará como dos estancias distintas (una en
cada unidad). Genera **un informe por cada unidad** (E073 e I073).

La augmentación sintética 2025 se calcula y aplica POR unidad: cada
unidad recibe su propio target = media de estancias 2022-2024 EN ESA
unidad.

Para las unidades incluidas en `demographics.sofa._config.ICU_UNITS`
(en este pipeline E073 e I073), se calcula el SOFA al ingreso y se
mergea en la cohorte para enriquecer el reporting (mediana global,
subgrupo cirrosis y subgrupo procedencia "otro hospital").
"""

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from demographics._bed_occupancy import compute_bed_occupancy_nominal
from demographics._config import FAKE_BED_PLACE_REFS_E073
from demographics._loader import (
    SYNTHETIC_LOOKBACK_YEARS,
    SYNTHETIC_YEAR,
    augment_synthetic_2025,
    compute_3y_mean_target,
    load_cohort,
)
from demographics._metrics import compute_summary
from demographics._report import generate_html, to_dataframe
from demographics.autopsy._loader import (
    load_autopsy_cohort,
    merge_per_unit as merge_autopsy_per_unit,
)
from demographics.nutrition._loader import (
    load_nutrition_cohort,
    merge_per_unit as merge_nutrition_per_unit,
)
from demographics.per_unit._sql import SQL_TEMPLATE
from demographics.sofa._config import ICU_UNITS, WINDOW_HOURS
from demographics.sofa._metrics import compute_sofa
from demographics.sofa._sql import render_sql as render_sofa_sql

OUTPUT_DIR = _REPO_ROOT / "demographics" / "output" / "per_unit"

UNITS = ["E073", "I073"]

# Claves de merge entre la cohorte demographic per_unit y la cohorte SOFA.
# Ambas usan la misma lógica per-unit (`PARTITION BY patient_ref,
# episode_ref, ou_loc_ref` con tolerancia 5 min en `start_date`), por lo
# que `stay_id` queda alineado.
SOFA_JOIN_KEYS = ["patient_ref", "episode_ref", "ou_loc_ref", "stay_id"]

# Columnas SOFA-derivadas que queremos exponer en la cohorte enriquecida.
# El resto (componentes individuales, valores crudos) se queda en el CSV
# de cohorte SOFA original; aquí solo subimos lo que el reporting agrega.
SOFA_OUTPUT_COLS = [
    "sofa_total",
    "sofa_components_available",
    "sofa_resp",
    "sofa_coag",
    "sofa_liver",
    "sofa_cardio",
    "sofa_neuro",
    "sofa_renal",
]


def parse_year_input(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        return 2019, 2025
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    year_val = int(text)
    return year_val, year_val


def load_sofa_cohort(
    min_year: int, max_year: int, units: list[str]
) -> pd.DataFrame:
    """Descarga la cohorte SOFA año a año para las `units` que sean UCI.

    Devuelve un DataFrame vacío si ninguna unidad pedida está en
    `ICU_UNITS` (p.ej. una unidad de hospitalización convencional).
    """
    icu_subset = [u for u in units if u in ICU_UNITS]
    if not icu_subset:
        print(
            "[sofa] ninguna de las unidades pedidas es UCI "
            f"({units}); no se calcula SOFA."
        )
        return pd.DataFrame(columns=SOFA_JOIN_KEYS)

    print(
        f"[sofa] descargando SOFA año a año desde Metabase "
        f"({min_year}-{max_year}, {icu_subset})…"
    )
    from connection import execute_query_yearly

    df = execute_query_yearly(
        lambda year: render_sofa_sql(
            year, year, icu_subset, window_hours=WINDOW_HOURS
        ),
        min_year,
        max_year,
        label="sofa",
    )

    if df.empty:
        print("[sofa] sin filas — saltando cálculo SOFA.")
        return pd.DataFrame(columns=SOFA_JOIN_KEYS)

    df = compute_sofa(df)
    n_full = int((df["sofa_components_available"] == 6).sum())
    n_partial = int(df["sofa_components_available"].between(1, 5).sum())
    n_empty = int((df["sofa_components_available"] == 0).sum())
    print(
        f"[sofa] {len(df)} estancias UCI con SOFA: "
        f"{n_full} con 6 comp. | {n_partial} parciales | {n_empty} sin datos. "
        f"Mediana SOFA={df['sofa_total'].median():.0f}."
    )

    keep = SOFA_JOIN_KEYS + [c for c in SOFA_OUTPUT_COLS if c in df.columns]
    return df[keep].copy()


def merge_sofa(cohort: pd.DataFrame, sofa_df: pd.DataFrame) -> pd.DataFrame:
    """Left-join `sofa_df` sobre `cohort` por `SOFA_JOIN_KEYS`.

    Requiere que `cohort` esté SIN augmentación sintética (los IDs
    sintéticos `SYN2025-…` no existen en la cohorte SOFA).
    """
    if sofa_df.empty:
        return cohort

    for key in SOFA_JOIN_KEYS:
        if key not in cohort.columns:
            print(
                f"[sofa] cohort sin columna `{key}` — no se puede "
                "mergear SOFA. Saltando."
            )
            return cohort

    # `stay_id` puede venir como float en el CSV (NaN handling). Normalizamos
    # a Int64 nullable en ambos lados antes del merge.
    for key in ("stay_id",):
        for d in (cohort, sofa_df):
            if key in d.columns:
                d[key] = pd.to_numeric(d[key], errors="coerce").astype("Int64")

    before = len(cohort)
    merged = cohort.merge(sofa_df, on=SOFA_JOIN_KEYS, how="left")
    matched = int(merged["sofa_total"].notna().sum())
    in_icu = int(merged["ou_loc_ref"].isin(ICU_UNITS).sum())
    print(
        f"[sofa] mergeado: {matched}/{in_icu} estancias en UCI con SOFA "
        f"asignado (de {before} totales en cohorte)."
    )
    return merged


def main():
    year_input = input("Periodo (p.ej. 2019-2025) [2019-2025]: ").strip()
    min_year, max_year = parse_year_input(year_input)
    years_str = f"{min_year}-{max_year}" if min_year != max_year else str(min_year)

    print(f"Consultando cohorte (per_unit) {years_str}…")
    df = load_cohort(
        min_year=min_year,
        max_year=max_year,
        sql_template=SQL_TEMPLATE,
        synthetic_group_col="ou_loc_ref",
        skip_synthetic=True,
    )

    print(f"Consultando SOFA al ingreso (UCI) {years_str}…")
    sofa_df = load_sofa_cohort(min_year, max_year, UNITS)
    df = merge_sofa(df, sofa_df)

    print(f"Consultando nutrición enteral / parenteral {years_str}…")
    nutrition_df = load_nutrition_cohort(min_year, max_year, UNITS)
    df = merge_nutrition_per_unit(df, nutrition_df)

    print(f"Consultando autopsias / necropsias {years_str}…")
    autopsy_df = load_autopsy_cohort(min_year, max_year, UNITS)
    df = merge_autopsy_per_unit(df, autopsy_df)

    # Augmentación sintética 2025 — se hace AHORA, después de los merges
    # de SOFA y nutrición, para que las filas sintéticas hereden valores
    # SOFA y flags/tiempos de nutrición del template (`_make_synthetic_rows`
    # clona toda la fila incluyendo `sofa_*`, `received_*`, `hours_to_*`
    # y solo sobrescribe IDs y fechas).
    if min_year <= SYNTHETIC_YEAR <= max_year:
        target = compute_3y_mean_target(
            df,
            year_now=SYNTHETIC_YEAR,
            n_years=SYNTHETIC_LOOKBACK_YEARS,
            group_col="ou_loc_ref",
        )
        df = augment_synthetic_2025(df, target=target, group_col="ou_loc_ref")

    n_total = len(df)
    n_open = int((df["still_admitted"] == "Yes").sum())
    n_patients = df["patient_ref"].nunique()

    print(f"  {n_total} estancias totales | {n_patients} pacientes únicos")
    if n_open:
        print(
            f"  {n_open} episodio(s) aún abiertos excluidos del análisis "
            f"({n_open / n_total * 100:.1f}%)"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    available_units = sorted(df["ou_loc_ref"].dropna().unique())
    print(f"  Unidades en cohorte: {available_units}")

    print(
        f"Calculando ocupación nominal de camas {available_units} "
        f"{min_year}-{max_year}…"
    )
    bed_occupancy = compute_bed_occupancy_nominal(
        units=available_units,
        min_year=min_year,
        max_year=max_year,
        fake_bed_place_refs=FAKE_BED_PLACE_REFS_E073,
    )

    for unit in UNITS:
        sub = df[df["ou_loc_ref"] == unit].copy()
        n_unit = len(sub)
        n_unit_pat = sub["patient_ref"].nunique()
        print(f"\n--- {unit} ---  {n_unit} estancias | {n_unit_pat} pacientes únicos")

        if sub.empty:
            print(f"  (sin filas para {unit}, saltando informe)")
            continue

        cohort_path = OUTPUT_DIR / f"ward_stays_cohort_{years_str}_{unit}.csv"
        sub.to_csv(cohort_path, index=False, encoding="utf-8-sig")

        sections, years = compute_summary(sub, bed_occupancy=bed_occupancy)

        summary_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_{unit}.csv"
        to_dataframe(sections, years).to_csv(summary_path, encoding="utf-8-sig")

        html_path = OUTPUT_DIR / f"ward_stays_summary_{years_str}_{unit}.html"
        generate_html(
            sections,
            years,
            f"Demografía y resultados {unit} — per unit ({years_str})",
            html_path,
            subtitle=(
                f"Hospital Clínic de Barcelona — Unidad {unit} (per-unit, "
                "estancias separadas por unidad)"
            ),
            stay_note=(
                "movimientos consecutivos agrupados con tolerancia de 5 min "
                "dentro de la misma unidad; si un paciente se traslada de "
                "E073 a I073 (o viceversa) dentro del mismo episodio, "
                "cuenta como dos estancias distintas."
            ),
        )

    print(f"\nListo. Archivos guardados en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
