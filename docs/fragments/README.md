# DataNex Schema Fragments

Fragmentos del esquema de DataNex para live coding. Cada archivo cubre un tema específico.

## Fragmentos disponibles

| Archivo | Tema | Tablas principales |
|---------|------|-------------------|
| `00_instructions.md` | Instrucciones para LLM | - |
| `01_episodes_movements.md` | Episodios y movimientos | g_episodes, g_care_levels, g_movements |
| `02_demographics.md` | Demografía y defunción | g_demographics, g_exitus, g_adm_disch |
| `03_diagnoses.md` | Diagnósticos | g_diagnostics, g_diagnostic_related_groups, g_health_issues |
| `04_labs_clinical.md` | Laboratorio y registros clínicos | g_labs, g_rc |
| `05_microbiology.md` | Microbiología | g_micro, g_antibiograms |
| `06_medications.md` | Medicación | g_prescriptions, g_administrations, g_perfusions |
| `07_procedures.md` | Procedimientos y encuentros | g_procedures, g_encounters, g_provisions |
| `08_surgery.md` | Cirugía | g_surgery, g_surgery_team, g_surgery_timestamps, g_surgery_waiting_list |
| `09_forms_pathology.md` | Formularios y patología | g_dynamic_forms, g_special_records, g_pathology_*, g_tags |
| `10_dictionaries.md` | Diccionarios | dic_diagnostic, dic_lab, dic_ou_loc, dic_ou_med, dic_rc |

## Uso recomendado

1. **Siempre empezar con**: `00_instructions.md` (reglas y contexto básico)
2. **Añadir según necesidad**: El fragmento específico del tema a trabajar
3. **Opcional**: `10_dictionaries.md` si necesitas buscar códigos

## Ejemplo de combinación para live coding

**Análisis de laboratorio en UCI**:
- `00_instructions.md` + `01_episodes_movements.md` + `04_labs_clinical.md`

**Prescripciones de antibióticos**:
- `00_instructions.md` + `06_medications.md` + `05_microbiology.md`

**Cirugías y procedimientos**:
- `00_instructions.md` + `07_procedures.md` + `08_surgery.md`
