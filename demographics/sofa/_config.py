"""Códigos y constantes para el cálculo del SOFA al ingreso en UCI.

Score implementado: **SOFA original** (Vincent JL et al. Intensive Care
Med 1996;22:707-10). NO es el SOFA 2.0 (Moreno 2023).

Todos los códigos vienen identificados desde los CSVs en
`dictionaries/sofa/`. Si DataNex añade nuevos lab/rc/drug refs habrá
que regenerar los CSVs y revisar este fichero.
"""

# ---------------------------------------------------------------------------
# UCIs Hospital Clínic — mismas que `deliris/camicu_compliance.sql`
# ---------------------------------------------------------------------------
ICU_UNITS = ["E016", "E103", "E014", "E015", "E037", "E057", "E073", "E043"]

# ---------------------------------------------------------------------------
# Ventana temporal — SOFA al ingreso = peor valor en las primeras 24 h.
# ---------------------------------------------------------------------------
WINDOW_HOURS = 24

# ---------------------------------------------------------------------------
# Laboratorio (`labs.lab_sap_ref`)
# ---------------------------------------------------------------------------
LAB_PAO2 = ("LAB3072", "LABRPAPO2")  # pO2 sangre arterial
LAB_PLATELETS = ("LAB1301",)          # Plaquetas recuento
LAB_BILIRUBIN = ("LAB2407",)          # Bilirrubina adulto total
LAB_CREATININE = ("LABCREA", "LAB2467")  # Creatinina sangre

# ---------------------------------------------------------------------------
# Registros clínicos (`rc.rc_sap_ref`)
# ---------------------------------------------------------------------------
RC_FIO2 = ("FIO2", "VMI_FIO2", "VNI_FIO2", "AR_FIO2", "ACR_FIO2", "VMA_FIO2")
RC_VENT_MODE = ("VMI_MOD", "VNI_MOD", "VIA_AEREA_MOD")
RC_MAP = ("PA_M", "PANIC_M", "PANI_M")  # presión arterial media: invasiva > NIBP continua > NIBP

# ---------------------------------------------------------------------------
# Glasgow (`dynamic_forms.form_ref='GLASGOW'`)
# ---------------------------------------------------------------------------
GCS_FORM = "GLASGOW"
GCS_QUESTIONS = ("OBER_ULLS", "RES_MOTORA", "RES_VERBAL")
# Form alternativo: form 'UCI' question 'GLASG_P' = puntuación total ya sumada.
GCS_TOTAL_FORM = "UCI"
GCS_TOTAL_QUESTION = "GLASG_P"

# ---------------------------------------------------------------------------
# Peso del paciente — necesario para mcg/kg/min en versiones futuras.
# Fuente preferida: `rc.rc_sap_ref` IN ('PESO','PESO_SECO').
#   * PESO       = peso medido a pie de cama.
#   * PESO_SECO  = peso "seco" estimado (sin sobrecarga hídrica).
#                  Especialmente útil en cirróticos con ascitis (E073).
# Fallback: `dynamic_forms` form 'UCI', question 'PES'.
# ---------------------------------------------------------------------------
RC_WEIGHT = ("PESO", "PESO_SECO")
WEIGHT_FORM = "UCI"
WEIGHT_QUESTION = "PES"

# ---------------------------------------------------------------------------
# Vasopresores / inotrópicos.
#
# IMPORTANTE: muchas perfusiones llevan el ATC del DILUYENTE (B05BB91 /
# B05BA91), no del principio activo. Por eso identificamos por nombre del
# fármaco en `drug_descr`, no por `atc_ref`.
# ---------------------------------------------------------------------------
# Patrón regex (lower-case, Trino regexp_like) para identificar vasopresor /
# inotrópico en `prescriptions.drug_descr` o `administrations.drug_descr`.
VASOACTIVE_DRUG_REGEX = (
    r"noradr|norepin|adrenalin|epinef|dopami|dobutami|"
    r"fenilefr|vasopres|terlipres|milrinon|levosimen|isoprenal"
)

# Categorías para SOFA cardiovascular (v1: presencia binaria, sin dosis).
VASOACTIVE_CATEGORIES = {
    "norepi": r"noradr|norepin",
    "epi": r"adrenalin|epinef",
    "dopa": r"dopami",
    "dobu": r"dobutami",
    "vasop": r"vasopres|terlipres",
    "phenyl": r"fenilefr",
    "inotrope_other": r"milrinon|levosimen|isoprenal",
}

# Vías de administración consideradas como infusión / IV continua.
IV_ROUTE_DESCR_REGEX = r"perfusion|intravenosa"
