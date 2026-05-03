"""Cálculo del SOFA al ingreso a partir del DataFrame agregado por SQL.

Score implementado: **SOFA original** (Vincent JL et al. Intensive Care
Med 1996;22:707-10). Cortes y reglas de la tabla original. NO es el
SOFA 2.0 (Moreno 2023).

Cada función `score_*` devuelve un entero 0-4 según la tabla SOFA, o
`pd.NA` si los datos son insuficientes para evaluar el componente.

Política de componentes faltantes (decidida 2026-05-03):
    Si un componente no es evaluable (p.ej. no hay Glasgow porque el
    paciente no necesitó valoración neurológica), se marca como NA y
    suma 0 al `sofa_total`. NO se imputa ningún valor — incluyendo el
    caso del paciente intubado sin GCS: si la enfermería no hizo
    ventana neurológica para calcular el GCS es porque clínicamente no
    procedía, así que no es razonable asumir un GCS bajo. La cuenta de
    componentes realmente evaluados se preserva en
    `sofa_components_available` para que el lector pueda distinguir
    SOFA=5 con 6 componentes vs SOFA=5 con sólo 3 componentes.

Limitaciones conocidas (v1):
  * Cardiovascular: no parseamos dosis exacta de vasopresor (mcg/kg/min)
    porque la concentración vive en `drug_descr` libre. Asignamos:
        - 4 si noradrenalina o adrenalina activas (asumido > 0.1 mcg/kg/min).
        - 3 si dopamina o dobutamina activas, o vasopresina/fenilefrina.
        - 2 si MAP < 70 sin vasopresores.
        - 1 si MAP entre 70 y "borderline" (no aplica → se omite).
        - 0 si MAP >= 70 sin vasopresores.
    Pendiente v2: parsear concentración + cruzar con `infusion_rate` y
    `weight_kg` para clasificar 3 vs 4 por dosis real.
  * Renal: sin diuresis (no disponible en BBDD). Sólo creatinina.
  * Respiratorio: si no hay FiO2 registrada se asume FiO2 = 0.21 (aire
    ambiente). Si tampoco hay PaO2 → componente NA.
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Componentes individuales
# ---------------------------------------------------------------------------
def score_respiratory(pao2_mmhg, fio2_pct, on_vmi):
    """SOFA respiratorio basado en PaO2/FiO2.

    fio2_pct se asume en porcentaje (21-100). Si viene como fracción (0.21-1.0)
    se reescala. Si es NA → asumimos 21% (aire ambiente).
    """
    if pd.isna(pao2_mmhg):
        return pd.NA
    if pd.isna(fio2_pct):
        fio2_pct = 21.0
    elif fio2_pct <= 1.0:
        fio2_pct = fio2_pct * 100.0
    if fio2_pct <= 0:
        return pd.NA
    ratio = pao2_mmhg / (fio2_pct / 100.0)
    on_support = bool(on_vmi) if not pd.isna(on_vmi) else False
    if ratio < 100 and on_support:
        return 4
    if ratio < 200 and on_support:
        return 3
    if ratio < 300:
        return 2
    if ratio < 400:
        return 1
    return 0


def score_coagulation(platelets_k):
    """SOFA coagulación basado en plaquetas (10^9/L = mil/μL)."""
    if pd.isna(platelets_k):
        return pd.NA
    if platelets_k < 20:
        return 4
    if platelets_k < 50:
        return 3
    if platelets_k < 100:
        return 2
    if platelets_k < 150:
        return 1
    return 0


def score_liver(bilirubin_mgdl):
    """SOFA hepático basado en bilirrubina total (mg/dL)."""
    if pd.isna(bilirubin_mgdl):
        return pd.NA
    if bilirubin_mgdl >= 12.0:
        return 4
    if bilirubin_mgdl >= 6.0:
        return 3
    if bilirubin_mgdl >= 2.0:
        return 2
    if bilirubin_mgdl >= 1.2:
        return 1
    return 0


def score_cardiovascular(map_min, on_norepi, on_epi, on_dopa, on_dobu,
                         on_vasop, on_phenyl, on_inotrope_other):
    """SOFA cardiovascular — versión sin dosis exacta (v1).

    Ver docstring del módulo para limitaciones.
    """
    high_dose_pressor = bool(on_norepi) or bool(on_epi)
    low_dose_pressor = (bool(on_dopa) or bool(on_dobu) or bool(on_vasop)
                        or bool(on_phenyl) or bool(on_inotrope_other))
    if high_dose_pressor:
        return 4  # asumido — falta parseo de dosis para distinguir 3/4
    if low_dose_pressor:
        return 3
    if pd.isna(map_min):
        return pd.NA
    if map_min < 70:
        return 1
    return 0


def score_neuro(gcs):
    """SOFA neurológico basado en Glasgow."""
    if pd.isna(gcs):
        return pd.NA
    if gcs < 6:
        return 4
    if gcs < 10:
        return 3
    if gcs < 13:
        return 2
    if gcs < 15:
        return 1
    return 0


def score_renal(creatinine_mgdl):
    """SOFA renal basado SÓLO en creatinina (sin diuresis — no disponible)."""
    if pd.isna(creatinine_mgdl):
        return pd.NA
    if creatinine_mgdl >= 5.0:
        return 4
    if creatinine_mgdl >= 3.5:
        return 3
    if creatinine_mgdl >= 2.0:
        return 2
    if creatinine_mgdl >= 1.2:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Aplicación al DataFrame de cohorte
# ---------------------------------------------------------------------------
COMPONENT_COLS = [
    "sofa_resp", "sofa_coag", "sofa_liver",
    "sofa_cardio", "sofa_neuro", "sofa_renal",
]


def compute_sofa(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas `sofa_*` y `sofa_total` al DataFrame de entrada."""
    out = df.copy()
    out["sofa_resp"] = out.apply(
        lambda r: score_respiratory(r["pao2_min"], r["fio2_max"], r["on_vmi"]), axis=1)
    out["sofa_coag"]   = out["platelets_min"].apply(score_coagulation)
    out["sofa_liver"]  = out["bilirubin_max"].apply(score_liver)
    out["sofa_cardio"] = out.apply(
        lambda r: score_cardiovascular(
            r["map_min"], r["on_norepi"], r["on_epi"], r["on_dopa"],
            r["on_dobu"], r["on_vasop"], r["on_phenyl"], r["on_inotrope_other"]),
        axis=1)
    out["sofa_neuro"]  = out["gcs_min"].apply(score_neuro)
    out["sofa_renal"]  = out["creatinine_max"].apply(score_renal)

    # Total = suma de componentes disponibles (componentes NA cuentan 0
    # pero los marcamos para reporting).
    comps = out[COMPONENT_COLS]
    out["sofa_components_available"] = comps.notna().sum(axis=1)
    out["sofa_total"] = comps.fillna(0).sum(axis=1).astype(int)
    return out


# ---------------------------------------------------------------------------
# Resúmenes agregados por unidad / año
# ---------------------------------------------------------------------------
def summarize_by_unit_year(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve estadísticos del SOFA por (ou_loc_ref, year_admission)."""
    grp = df.groupby(["ou_loc_ref", "year_admission"], dropna=False)
    summary = grp.agg(
        n_stays=("sofa_total", "size"),
        n_full=("sofa_components_available", lambda s: int((s == 6).sum())),
        sofa_mean=("sofa_total", "mean"),
        sofa_median=("sofa_total", "median"),
        sofa_p25=("sofa_total", lambda s: s.quantile(0.25)),
        sofa_p75=("sofa_total", lambda s: s.quantile(0.75)),
        pct_exitus=("exitus_during_stay", lambda s: 100.0 * s.mean()),
    ).round(2)
    return summary.reset_index()
