# Dictionary Repository

Generated: 2026-02-06 20:30:24
Total dictionaries: 54

## From Dictionary Tables (dic_*)

| File | Description | Source | Rows |
|------|-------------|--------|------|
| dic_diagnostic.csv | ICD-9/ICD-10 diagnosis codes | dic_diagnostic | 35,181 |
| dic_lab.csv | Laboratory parameters (lab_sap_ref -> description, units) | dic_lab | 5,098 |
| dic_ou_loc.csv | Physical hospitalization units | dic_ou_loc | 986 |
| dic_ou_med.csv | Medical organizational units | dic_ou_med | 287 |
| dic_rc.csv | Clinical record parameters (rc_sap_ref -> description, units) | dic_rc | 897 |
| dic_rc_text.csv | Clinical record text value mappings | dic_rc_text | 1,634 |

## From Data Tables (SELECT DISTINCT)

| File | Description | Source | Rows |
|------|-------------|--------|------|
| adm_disch_motive_dictionary.csv | Admission and discharge reason codes | g_adm_disch | 20 |
| antibiogram_sample_type_dictionary.csv | Antibiogram sample type codes | g_antibiograms | 20 |
| antibiotic_dictionary.csv | Antibiotic codes used in sensitivity testing | g_antibiograms | 101 |
| atc_dictionary.csv | ATC pharmaceutical classification codes | g_prescriptions, g_administrations | 1,977 |
| drg_dictionary.csv | Diagnosis-Related Group codes with MDC | g_diagnostic_related_groups | 1,351 |
| drug_dictionary.csv | Drugs with ATC codes (from prescriptions + administrations) | g_prescriptions, g_administrations | 32,628 |
| dynamic_form_dictionary.csv | Dynamic form types (clinical + nursing) | g_dynamic_forms, g_special_records | 327 |
| encounter_type_dictionary.csv | Encounter type codes (from actual data) | g_encounters | 41 |
| frequency_dictionary.csv | Dosing frequency codes | g_prescriptions | 313 |
| health_area_dictionary.csv | Health area codes | g_demographics | 309 |
| health_issue_end_motive_dictionary.csv | Health issue end motive codes | g_health_issues | 5 |
| mdc_dictionary.csv | Major Diagnostic Categories | g_diagnostic_related_groups | 27 |
| micro_method_dictionary.csv | Microbiology sample processing methods | g_micro | 1,327 |
| micro_sample_type_dictionary.csv | Microbiology sample type/origin codes | g_micro | 21 |
| microorganism_dictionary.csv | Microorganism codes and scientific names | g_micro, g_antibiograms | 930 |
| mortality_rom_dictionary.csv | Risk of Mortality (ROM) levels | g_diagnostic_related_groups | 6 |
| nationality_dictionary.csv | Nationality codes (ISO country codes) | g_demographics | 217 |
| operating_room_dictionary.csv | Operating room identifiers | g_surgery | 67 |
| pathology_diag_type_dictionary.csv | Pathology diagnosis type codes | g_pathology_diagnostic | 2 |
| phform_dictionary.csv | Pharmaceutical forms | g_prescriptions | 91 |
| prescr_env_dictionary.csv | Prescription environment (healthcare setting) codes | g_prescriptions | 12 |
| provision_dictionary.csv | Healthcare provision codes | g_provisions | 16,524 |
| provision_levels_dictionary.csv | Provision hierarchical classification (level 1/2/3) | g_provisions | 377 |
| route_dictionary.csv | Drug administration routes | g_prescriptions, g_administrations | 69 |
| severity_soi_dictionary.csv | Severity of Illness (SOI) levels | g_diagnostic_related_groups | 5 |
| snomed_health_issues_dictionary.csv | SNOMED-CT health problem codes used in the hospital | g_health_issues | 11,713 |
| surgery_code_dictionary.csv | Surgery Q-codes (local procedure codes) | g_surgery | 2,516 |
| surgery_event_dictionary.csv | Surgical event timestamp types | g_surgery_timestamps | 37 |
| surgery_task_dictionary.csv | Surgical team task types (surgeon, nurse, etc.) | g_surgery_team | 20 |
| surgery_waiting_list_dictionary.csv | Surgery waiting list names | g_surgery_waiting_list | 13 |
| tag_dictionary.csv | Clinical tags for patient grouping | g_tags | 261 |
| unit_dictionary.csv | Dose units | g_prescriptions, g_administrations | 27 |

## Inline Enumerations (hard-coded from DB_CONTEXT.md)

| File | Description | Source | Rows |
|------|-------------|--------|------|
| enum_care_level_type.csv | Care level type codes (g_care_levels.care_level_type_ref) | g_care_levels | 7 |
| enum_diag_catalog.csv | Diagnosis catalog codes (g_diagnostics.catalog) | g_diagnostics | 12 |
| enum_diag_class.csv | Diagnosis class codes (g_diagnostics.class) | g_diagnostics | 5 |
| enum_dynamic_form_class.csv | Dynamic form assessment class (g_dynamic_forms.class_ref) | g_dynamic_forms | 7 |
| enum_dynamic_form_status.csv | Dynamic form status (g_dynamic_forms.status) | g_dynamic_forms | 2 |
| enum_encounter_type_descr.csv | Encounter type codes with descriptions (g_encounters.encounter_type) | g_encounters | 33 |
| enum_episode_type.csv | Episode type codes (g_episodes.episode_type_ref) | g_episodes | 8 |
| enum_meas_type.csv | Measurement type (g_rc.meas_type_ref) | g_rc | 3 |
| enum_mot_type.csv | Admission/discharge motive type (g_adm_disch.mot_type) | g_adm_disch | 2 |
| enum_poa.csv | Present on Admission indicator (g_diagnostics.poa) | g_diagnostics | 6 |
| enum_procedure_catalog.csv | Procedure catalog codes (g_procedures.catalog) | g_procedures | 2 |
| enum_procedure_class.csv | Procedure class (g_procedures.class) | g_procedures | 2 |
| enum_procedure_place.csv | Procedure location codes (g_procedures.place) | g_procedures | 7 |
| enum_provision_category.csv | Provision category (g_provisions.category) | g_provisions | 2 |
| enum_sensitivity.csv | Antibiotic sensitivity result (g_antibiograms.sensitivity) | g_antibiograms | 2 |
| enum_sex.csv | Sex codes (g_demographics.sex) | g_demographics | 4 |
