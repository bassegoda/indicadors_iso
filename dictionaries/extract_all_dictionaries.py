"""
Extract All Dictionaries from DataNex Database
================================================
Unified script to extract all dictionary/lookup tables from the DataNex hospital
database into CSV files for AI-assisted coding (grep-friendly repository).

Three categories:
  - from_dic_tables: Official dic_* dictionary tables
  - from_data_tables: DISTINCT value pairs from g_* data tables
  - inline_enums: Hard-coded enumerations from DB_CONTEXT.md

Usage:
  python extract_all_dictionaries.py --all                        # Extract everything
  python extract_all_dictionaries.py --category from_dic_tables   # Just dic_* tables
  python extract_all_dictionaries.py --category inline_enums      # No DB needed
  python extract_all_dictionaries.py --dict nationality drug      # Specific IDs
  python extract_all_dictionaries.py --list                       # List available
  python extract_all_dictionaries.py --dry-run                    # Show what would run
  python extract_all_dictionaries.py --skip-slow                  # Skip large queries

Replaces: import_all_dictionaries.py, import_treatment_dictionaries.py
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add project root to path for connection module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

OUTPUT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Dictionary Registry
# ---------------------------------------------------------------------------

DICTIONARY_REGISTRY = {
    # ===================================================================
    # A. FROM DIC_* TABLES (6)
    # ===================================================================
    "from_dic_tables": {
        "dic_diagnostic": {
            "description": "ICD-9/ICD-10 diagnosis codes",
            "filename": "dic_diagnostic.csv",
            "query": "SELECT diag_ref, catalog, code, diag_descr FROM dic_diagnostic ORDER BY diag_ref",
            "text_columns": ["diag_descr"],
            "source_table": "dic_diagnostic",
        },
        "dic_lab": {
            "description": "Laboratory parameters (lab_sap_ref -> description, units)",
            "filename": "dic_lab.csv",
            "query": "SELECT lab_sap_ref, lab_descr, units, lab_ref FROM dic_lab ORDER BY lab_sap_ref",
            "text_columns": ["lab_descr", "units"],
            "source_table": "dic_lab",
        },
        "dic_ou_loc": {
            "description": "Physical hospitalization units",
            "filename": "dic_ou_loc.csv",
            "query": (
                "SELECT ou_loc_ref, ou_loc_descr, care_level_type_ref, "
                "facility_ref, facility_descr "
                "FROM dic_ou_loc ORDER BY ou_loc_ref"
            ),
            "text_columns": ["ou_loc_descr", "facility_descr"],
            "source_table": "dic_ou_loc",
        },
        "dic_ou_med": {
            "description": "Medical organizational units",
            "filename": "dic_ou_med.csv",
            "query": "SELECT ou_med_ref, ou_med_descr FROM dic_ou_med ORDER BY ou_med_ref",
            "text_columns": ["ou_med_descr"],
            "source_table": "dic_ou_med",
        },
        "dic_rc": {
            "description": "Clinical record parameters (rc_sap_ref -> description, units)",
            "filename": "dic_rc.csv",
            "query": "SELECT rc_sap_ref, rc_descr, units, rc_ref FROM dic_rc ORDER BY rc_sap_ref",
            "text_columns": ["rc_descr", "units"],
            "source_table": "dic_rc",
        },
        "dic_rc_text": {
            "description": "Clinical record text value mappings",
            "filename": "dic_rc_text.csv",
            "query": "SELECT rc_sap_ref, result_txt, descr FROM dic_rc_text ORDER BY rc_sap_ref, result_txt",
            "text_columns": ["result_txt", "descr"],
            "source_table": "dic_rc_text",
        },
    },

    # ===================================================================
    # B. FROM DATA TABLES via SELECT DISTINCT (~29)
    # ===================================================================
    "from_data_tables": {
        # --- Treatment-related (existing) ---
        "drug": {
            "description": "Drugs with ATC codes (from prescriptions + administrations)",
            "filename": "drug_dictionary.csv",
            "query": (
                "SELECT DISTINCT drug_ref, drug_descr, atc_ref, atc_descr FROM ("
                "  SELECT drug_ref, drug_descr, atc_ref, atc_descr FROM g_prescriptions WHERE drug_ref IS NOT NULL"
                "  UNION"
                "  SELECT drug_ref, drug_descr, atc_ref, atc_descr FROM g_administrations WHERE drug_ref IS NOT NULL"
                ") AS combined ORDER BY drug_descr, drug_ref"
            ),
            "text_columns": ["drug_descr", "atc_descr"],
            "source_table": "g_prescriptions, g_administrations",
            "slow": True,
        },
        "atc": {
            "description": "ATC pharmaceutical classification codes",
            "filename": "atc_dictionary.csv",
            "query": (
                "SELECT DISTINCT atc_ref, atc_descr FROM ("
                "  SELECT atc_ref, atc_descr FROM g_prescriptions WHERE atc_ref IS NOT NULL AND atc_descr IS NOT NULL"
                "  UNION"
                "  SELECT atc_ref, atc_descr FROM g_administrations WHERE atc_ref IS NOT NULL AND atc_descr IS NOT NULL"
                ") AS combined ORDER BY atc_ref"
            ),
            "text_columns": ["atc_descr"],
            "source_table": "g_prescriptions, g_administrations",
            "slow": True,
        },
        "route": {
            "description": "Drug administration routes",
            "filename": "route_dictionary.csv",
            "query": (
                "SELECT DISTINCT route_ref, route_descr FROM ("
                "  SELECT adm_route_ref AS route_ref, route_descr FROM g_prescriptions"
                "    WHERE adm_route_ref IS NOT NULL AND route_descr IS NOT NULL"
                "  UNION"
                "  SELECT route_ref, route_descr FROM g_administrations"
                "    WHERE route_ref IS NOT NULL AND route_descr IS NOT NULL"
                ") AS combined ORDER BY route_ref"
            ),
            "text_columns": ["route_descr"],
            "source_table": "g_prescriptions, g_administrations",
            "slow": True,
        },
        "phform": {
            "description": "Pharmaceutical forms",
            "filename": "phform_dictionary.csv",
            "query": (
                "SELECT DISTINCT phform_ref, phform_descr "
                "FROM g_prescriptions "
                "WHERE phform_ref IS NOT NULL AND phform_descr IS NOT NULL "
                "ORDER BY phform_ref"
            ),
            "text_columns": ["phform_descr"],
            "source_table": "g_prescriptions",
            "slow": True,
        },
        "frequency": {
            "description": "Dosing frequency codes",
            "filename": "frequency_dictionary.csv",
            "query": (
                "SELECT DISTINCT freq_ref "
                "FROM g_prescriptions "
                "WHERE freq_ref IS NOT NULL "
                "ORDER BY freq_ref"
            ),
            "text_columns": ["freq_ref"],
            "source_table": "g_prescriptions",
            "slow": True,
        },
        "unit": {
            "description": "Dose units",
            "filename": "unit_dictionary.csv",
            "query": (
                "SELECT DISTINCT unit_ref FROM ("
                "  SELECT unit AS unit_ref FROM g_prescriptions WHERE unit IS NOT NULL"
                "  UNION"
                "  SELECT quantity_unit AS unit_ref FROM g_administrations WHERE quantity_unit IS NOT NULL"
                ") AS combined ORDER BY unit_ref"
            ),
            "text_columns": ["unit_ref"],
            "source_table": "g_prescriptions, g_administrations",
            "slow": True,
        },

        # --- Demographics ---
        "nationality": {
            "description": "Nationality codes (ISO country codes)",
            "filename": "nationality_dictionary.csv",
            "query": (
                "SELECT DISTINCT natio_ref, natio_descr "
                "FROM g_demographics "
                "WHERE natio_ref IS NOT NULL "
                "ORDER BY natio_ref"
            ),
            "text_columns": ["natio_descr"],
            "source_table": "g_demographics",
        },
        "health_area": {
            "description": "Health area codes",
            "filename": "health_area_dictionary.csv",
            "query": (
                "SELECT DISTINCT health_area "
                "FROM g_demographics "
                "WHERE health_area IS NOT NULL "
                "ORDER BY health_area"
            ),
            "text_columns": ["health_area"],
            "source_table": "g_demographics",
        },

        # --- Admission / Discharge ---
        "adm_disch_motive": {
            "description": "Admission and discharge reason codes",
            "filename": "adm_disch_motive_dictionary.csv",
            "query": (
                "SELECT DISTINCT mot_ref, mot_descr, mot_type "
                "FROM g_adm_disch "
                "WHERE mot_ref IS NOT NULL "
                "ORDER BY mot_type, mot_ref"
            ),
            "text_columns": ["mot_descr"],
            "source_table": "g_adm_disch",
        },

        # --- DRG / Severity / Mortality ---
        "drg": {
            "description": "Diagnosis-Related Group codes with MDC",
            "filename": "drg_dictionary.csv",
            "query": (
                "SELECT DISTINCT drg_ref, mdc_ref "
                "FROM g_diagnostic_related_groups "
                "WHERE drg_ref IS NOT NULL "
                "ORDER BY drg_ref"
            ),
            "text_columns": [],
            "source_table": "g_diagnostic_related_groups",
        },
        "severity_soi": {
            "description": "Severity of Illness (SOI) levels",
            "filename": "severity_soi_dictionary.csv",
            "query": (
                "SELECT DISTINCT severity_ref, severity_descr "
                "FROM g_diagnostic_related_groups "
                "WHERE severity_ref IS NOT NULL "
                "ORDER BY severity_ref"
            ),
            "text_columns": ["severity_descr"],
            "source_table": "g_diagnostic_related_groups",
        },
        "mortality_rom": {
            "description": "Risk of Mortality (ROM) levels",
            "filename": "mortality_rom_dictionary.csv",
            "query": (
                "SELECT DISTINCT mortality_risk_ref, mortality_risk_descr "
                "FROM g_diagnostic_related_groups "
                "WHERE mortality_risk_ref IS NOT NULL "
                "ORDER BY mortality_risk_ref"
            ),
            "text_columns": ["mortality_risk_descr"],
            "source_table": "g_diagnostic_related_groups",
        },
        "mdc": {
            "description": "Major Diagnostic Categories",
            "filename": "mdc_dictionary.csv",
            "query": (
                "SELECT DISTINCT mdc_ref "
                "FROM g_diagnostic_related_groups "
                "WHERE mdc_ref IS NOT NULL "
                "ORDER BY mdc_ref"
            ),
            "text_columns": [],
            "source_table": "g_diagnostic_related_groups",
        },

        # --- Health Issues (SNOMED) ---
        "snomed_health_issues": {
            "description": "SNOMED-CT health problem codes used in the hospital",
            "filename": "snomed_health_issues_dictionary.csv",
            "query": (
                "SELECT DISTINCT snomed_ref, snomed_descr "
                "FROM g_health_issues "
                "WHERE snomed_ref IS NOT NULL "
                "ORDER BY snomed_ref"
            ),
            "text_columns": ["snomed_descr"],
            "source_table": "g_health_issues",
            "slow": True,
        },
        "health_issue_end_motive": {
            "description": "Health issue end motive codes",
            "filename": "health_issue_end_motive_dictionary.csv",
            "query": (
                "SELECT DISTINCT end_motive "
                "FROM g_health_issues "
                "WHERE end_motive IS NOT NULL "
                "ORDER BY end_motive"
            ),
            "text_columns": [],
            "source_table": "g_health_issues",
        },

        # --- Microbiology ---
        "micro_sample_type": {
            "description": "Microbiology sample type/origin codes",
            "filename": "micro_sample_type_dictionary.csv",
            "query": (
                "SELECT DISTINCT mue_ref, mue_descr "
                "FROM g_micro "
                "WHERE mue_ref IS NOT NULL "
                "ORDER BY mue_ref"
            ),
            "text_columns": ["mue_descr"],
            "source_table": "g_micro",
        },
        "micro_method": {
            "description": "Microbiology sample processing methods",
            "filename": "micro_method_dictionary.csv",
            "query": (
                "SELECT DISTINCT method_descr "
                "FROM g_micro "
                "WHERE method_descr IS NOT NULL "
                "ORDER BY method_descr"
            ),
            "text_columns": ["method_descr"],
            "source_table": "g_micro",
        },
        "microorganism": {
            "description": "Microorganism codes and scientific names",
            "filename": "microorganism_dictionary.csv",
            "query": (
                "SELECT DISTINCT micro_ref, micro_descr FROM ("
                "  SELECT micro_ref, micro_descr FROM g_micro WHERE micro_ref IS NOT NULL"
                "  UNION"
                "  SELECT micro_ref, micro_descr FROM g_antibiograms WHERE micro_ref IS NOT NULL"
                ") AS combined ORDER BY micro_ref"
            ),
            "text_columns": ["micro_descr"],
            "source_table": "g_micro, g_antibiograms",
        },

        # --- Antibiograms ---
        "antibiogram_sample_type": {
            "description": "Antibiogram sample type codes",
            "filename": "antibiogram_sample_type_dictionary.csv",
            "query": (
                "SELECT DISTINCT sample_ref, sample_descr "
                "FROM g_antibiograms "
                "WHERE sample_ref IS NOT NULL "
                "ORDER BY sample_ref"
            ),
            "text_columns": ["sample_descr"],
            "source_table": "g_antibiograms",
        },
        "antibiotic": {
            "description": "Antibiotic codes used in sensitivity testing",
            "filename": "antibiotic_dictionary.csv",
            "query": (
                "SELECT DISTINCT antibiotic_ref, antibiotic_descr "
                "FROM g_antibiograms "
                "WHERE antibiotic_ref IS NOT NULL "
                "ORDER BY antibiotic_ref"
            ),
            "text_columns": ["antibiotic_descr"],
            "source_table": "g_antibiograms",
        },

        # --- Provisions ---
        "provision": {
            "description": "Healthcare provision codes",
            "filename": "provision_dictionary.csv",
            "query": (
                "SELECT DISTINCT prov_ref, prov_descr "
                "FROM g_provisions "
                "WHERE prov_ref IS NOT NULL "
                "ORDER BY prov_ref"
            ),
            "text_columns": ["prov_descr"],
            "source_table": "g_provisions",
            "slow": True,
        },
        "provision_levels": {
            "description": "Provision hierarchical classification (level 1/2/3)",
            "filename": "provision_levels_dictionary.csv",
            "query": (
                "SELECT DISTINCT "
                "  level_1_ref, level_1_descr, "
                "  level_2_ref, level_2_descr, "
                "  level_3_ref, level_3_descr "
                "FROM g_provisions "
                "WHERE level_1_ref IS NOT NULL "
                "ORDER BY level_1_ref, level_2_ref, level_3_ref"
            ),
            "text_columns": ["level_1_descr", "level_2_descr", "level_3_descr"],
            "source_table": "g_provisions",
            "slow": True,
        },

        # --- Dynamic Forms ---
        "dynamic_form": {
            "description": "Dynamic form types (clinical + nursing)",
            "filename": "dynamic_form_dictionary.csv",
            "query": (
                "SELECT DISTINCT form_ref, form_descr, class_ref, class_descr FROM ("
                "  SELECT form_ref, form_descr, class_ref, class_descr FROM g_dynamic_forms WHERE form_ref IS NOT NULL"
                "  UNION"
                "  SELECT form_ref, form_descr, class_ref, class_descr FROM g_special_records WHERE form_ref IS NOT NULL"
                ") AS combined ORDER BY class_ref, form_ref"
            ),
            "text_columns": ["form_descr", "class_descr"],
            "source_table": "g_dynamic_forms, g_special_records",
            "slow": True,
        },
        "dynamic_form_structure": {
            "description": "Dynamic form full hierarchy (form > tab > section > question)",
            "filename": "dynamic_form_structure_dictionary.csv",
            "query": (
                "SELECT DISTINCT "
                "  form_ref, form_descr, "
                "  tab_ref, tab_descr, "
                "  section_ref, section_descr, "
                "  type_ref, type_descr "
                "FROM ("
                "  SELECT form_ref, form_descr, tab_ref, tab_descr, "
                "         section_ref, section_descr, type_ref, type_descr "
                "  FROM g_dynamic_forms WHERE form_ref IS NOT NULL"
                "  UNION"
                "  SELECT form_ref, form_descr, tab_ref, tab_descr, "
                "         section_ref, section_descr, type_ref, type_descr "
                "  FROM g_special_records WHERE form_ref IS NOT NULL"
                ") AS combined ORDER BY form_ref, tab_ref, section_ref, type_ref"
            ),
            "text_columns": ["form_descr", "tab_descr", "section_descr", "type_descr"],
            "source_table": "g_dynamic_forms, g_special_records",
            "slow": True,
        },

        # --- Tags ---
        "tag": {
            "description": "Clinical tags for patient grouping",
            "filename": "tag_dictionary.csv",
            "query": (
                "SELECT DISTINCT tag_ref, tag_group, tag_subgroup, tag_descr "
                "FROM g_tags "
                "WHERE tag_ref IS NOT NULL "
                "ORDER BY tag_group, tag_subgroup, tag_ref"
            ),
            "text_columns": ["tag_descr"],
            "source_table": "g_tags",
        },

        # --- Surgery ---
        "surgery_code": {
            "description": "Surgery Q-codes (local procedure codes)",
            "filename": "surgery_code_dictionary.csv",
            "query": (
                "SELECT DISTINCT surgery_code, surgery_code_descr "
                "FROM g_surgery "
                "WHERE surgery_code IS NOT NULL "
                "ORDER BY surgery_code"
            ),
            "text_columns": ["surgery_code_descr"],
            "source_table": "g_surgery",
        },
        "surgery_task": {
            "description": "Surgical team task types (surgeon, nurse, etc.)",
            "filename": "surgery_task_dictionary.csv",
            "query": (
                "SELECT DISTINCT task_ref, task_descr "
                "FROM g_surgery_team "
                "WHERE task_ref IS NOT NULL "
                "ORDER BY task_ref"
            ),
            "text_columns": ["task_descr"],
            "source_table": "g_surgery_team",
        },
        "surgery_event": {
            "description": "Surgical event timestamp types",
            "filename": "surgery_event_dictionary.csv",
            "query": (
                "SELECT DISTINCT event_label, event_descr "
                "FROM g_surgery_timestamps "
                "WHERE event_label IS NOT NULL "
                "ORDER BY event_label"
            ),
            "text_columns": ["event_descr"],
            "source_table": "g_surgery_timestamps",
        },
        "operating_room": {
            "description": "Operating room identifiers",
            "filename": "operating_room_dictionary.csv",
            "query": (
                "SELECT DISTINCT operating_room "
                "FROM g_surgery "
                "WHERE operating_room IS NOT NULL "
                "ORDER BY operating_room"
            ),
            "text_columns": [],
            "source_table": "g_surgery",
        },
        "surgery_waiting_list": {
            "description": "Surgery waiting list names",
            "filename": "surgery_waiting_list_dictionary.csv",
            "query": (
                "SELECT DISTINCT waiting_list "
                "FROM g_surgery_waiting_list "
                "WHERE waiting_list IS NOT NULL "
                "ORDER BY waiting_list"
            ),
            "text_columns": [],
            "source_table": "g_surgery_waiting_list",
        },

        # --- Encounters ---
        "encounter_type": {
            "description": "Encounter type codes (from actual data)",
            "filename": "encounter_type_dictionary.csv",
            "query": (
                "SELECT DISTINCT encounter_type "
                "FROM g_encounters "
                "WHERE encounter_type IS NOT NULL "
                "ORDER BY encounter_type"
            ),
            "text_columns": [],
            "source_table": "g_encounters",
        },

        # --- Prescriptions extra ---
        "prescr_env": {
            "description": "Prescription environment (healthcare setting) codes",
            "filename": "prescr_env_dictionary.csv",
            "query": (
                "SELECT DISTINCT prescr_env_ref "
                "FROM g_prescriptions "
                "WHERE prescr_env_ref IS NOT NULL "
                "ORDER BY prescr_env_ref"
            ),
            "text_columns": [],
            "source_table": "g_prescriptions",
            "slow": True,
        },

        # --- Pathology ---
        "pathology_diag_type": {
            "description": "Pathology diagnosis type codes",
            "filename": "pathology_diag_type_dictionary.csv",
            "query": (
                "SELECT DISTINCT diag_type "
                "FROM g_pathology_diagnostic "
                "WHERE diag_type IS NOT NULL "
                "ORDER BY diag_type"
            ),
            "text_columns": [],
            "source_table": "g_pathology_diagnostic",
        },
    },

    # ===================================================================
    # C. INLINE ENUMS (hard-coded from DB_CONTEXT.md, no DB needed)
    # ===================================================================
    "inline_enums": {
        "episode_type": {
            "description": "Episode type codes (g_episodes.episode_type_ref)",
            "filename": "enum_episode_type.csv",
            "source_table": "g_episodes",
            "data": [
                {"code": "AM", "description": "Outpatient episode (ambulatorio)"},
                {"code": "EM", "description": "Emergency episode"},
                {"code": "DON", "description": "Donor"},
                {"code": "HOSP_IQ", "description": "Hospitalization for surgery"},
                {"code": "HOSP_RN", "description": "Hospitalization for healthy newborn"},
                {"code": "HOSP", "description": "Hospitalization (other)"},
                {"code": "EXT_SAMP", "description": "External sample"},
                {"code": "HAH", "description": "Hospital at home (home hospitalization)"},
            ],
        },
        "care_level_type": {
            "description": "Care level type codes (g_care_levels.care_level_type_ref)",
            "filename": "enum_care_level_type.csv",
            "source_table": "g_care_levels",
            "data": [
                {"code": "WARD", "description": "Conventional hospitalization"},
                {"code": "ICU", "description": "Intensive care unit"},
                {"code": "EM", "description": "Emergency"},
                {"code": "SPEC", "description": "Special"},
                {"code": "HAH", "description": "Hospital at home"},
                {"code": "PEND. CLAS", "description": "Pending classification"},
                {"code": "SHORT", "description": "Short stay"},
            ],
        },
        "sex": {
            "description": "Sex codes (g_demographics.sex)",
            "filename": "enum_sex.csv",
            "source_table": "g_demographics",
            "data": [
                {"code": "-1", "description": "Not reported in SAP"},
                {"code": "1", "description": "Male"},
                {"code": "2", "description": "Female"},
                {"code": "3", "description": "Other"},
            ],
        },
        "diag_catalog": {
            "description": "Diagnosis catalog codes (g_diagnostics.catalog)",
            "filename": "enum_diag_catalog.csv",
            "source_table": "g_diagnostics",
            "data": [
                {"code": "1", "description": "CIE9 MC (until 2017)"},
                {"code": "2", "description": "MDC"},
                {"code": "3", "description": "CIE9 Emergencies"},
                {"code": "4", "description": "ACR"},
                {"code": "5", "description": "SNOMED"},
                {"code": "7", "description": "MDC-AP"},
                {"code": "8", "description": "SNOMEDCT"},
                {"code": "9", "description": "Subset ANP SNOMED CT"},
                {"code": "10", "description": "Subset ANP SNOMED ID"},
                {"code": "11", "description": "CIE9 in Outpatients"},
                {"code": "12", "description": "CIE10 MC"},
                {"code": "13", "description": "CIE10 Outpatients"},
            ],
        },
        "diag_class": {
            "description": "Diagnosis class codes (g_diagnostics.class)",
            "filename": "enum_diag_class.csv",
            "source_table": "g_diagnostics",
            "data": [
                {"code": "P", "description": "Primary diagnosis (validated by documentalist)"},
                {"code": "S", "description": "Secondary diagnosis (validated by documentalist)"},
                {"code": "H", "description": "Diagnosis not validated by documentalist"},
                {"code": "E", "description": "Emergency diagnosis"},
                {"code": "A", "description": "Outpatient diagnosis"},
            ],
        },
        "poa": {
            "description": "Present on Admission indicator (g_diagnostics.poa)",
            "filename": "enum_poa.csv",
            "source_table": "g_diagnostics",
            "data": [
                {"code": "Y", "description": "Present at admission (comorbidity)"},
                {"code": "N", "description": "Not present at admission (complication)"},
                {"code": "U", "description": "Unknown (insufficient documentation)"},
                {"code": "W", "description": "Clinically undetermined"},
                {"code": "E", "description": "Exempt"},
                {"code": "-", "description": "Unreported (not registered by documentalist)"},
            ],
        },
        "mot_type": {
            "description": "Admission/discharge motive type (g_adm_disch.mot_type)",
            "filename": "enum_mot_type.csv",
            "source_table": "g_adm_disch",
            "data": [
                {"code": "START", "description": "Starting motive (reason for admission)"},
                {"code": "END", "description": "Ending motive (reason for discharge)"},
            ],
        },
        "meas_type": {
            "description": "Measurement type (g_rc.meas_type_ref)",
            "filename": "enum_meas_type.csv",
            "source_table": "g_rc",
            "data": [
                {"code": "0", "description": "Manual input"},
                {"code": "1", "description": "From machine, result not validated"},
                {"code": "2", "description": "From machine, result validated"},
            ],
        },
        "sensitivity": {
            "description": "Antibiotic sensitivity result (g_antibiograms.sensitivity)",
            "filename": "enum_sensitivity.csv",
            "source_table": "g_antibiograms",
            "data": [
                {"code": "S", "description": "Sensitive"},
                {"code": "R", "description": "Resistant"},
            ],
        },
        "procedure_place": {
            "description": "Procedure location codes (g_procedures.place)",
            "filename": "enum_procedure_place.csv",
            "source_table": "g_procedures",
            "data": [
                {"code": "1", "description": "Bloque quirurgico (surgical block)"},
                {"code": "2", "description": "Gabinete diagnostico y terapeutico"},
                {"code": "3", "description": "Cirugia menor (minor surgery)"},
                {"code": "4", "description": "Radiologia intervencionista o medicina nuclear"},
                {"code": "5", "description": "Sala de no intervencion"},
                {"code": "6", "description": "Bloque obstetrico (obstetric block)"},
                {"code": "EX", "description": "Procedimiento externo (external procedure)"},
            ],
        },
        "procedure_catalog": {
            "description": "Procedure catalog codes (g_procedures.catalog)",
            "filename": "enum_procedure_catalog.csv",
            "source_table": "g_procedures",
            "data": [
                {"code": "1", "description": "ICD-9"},
                {"code": "12", "description": "ICD-10"},
            ],
        },
        "procedure_class": {
            "description": "Procedure class (g_procedures.class)",
            "filename": "enum_procedure_class.csv",
            "source_table": "g_procedures",
            "data": [
                {"code": "P", "description": "Primary procedure"},
                {"code": "S", "description": "Secondary procedure"},
            ],
        },
        "dynamic_form_status": {
            "description": "Dynamic form status (g_dynamic_forms.status)",
            "filename": "enum_dynamic_form_status.csv",
            "source_table": "g_dynamic_forms",
            "data": [
                {"code": "CO", "description": "Completed"},
                {"code": "EC", "description": "In process (en curso)"},
            ],
        },
        "dynamic_form_class": {
            "description": "Dynamic form assessment class (g_dynamic_forms.class_ref)",
            "filename": "enum_dynamic_form_class.csv",
            "source_table": "g_dynamic_forms",
            "data": [
                {"code": "CC", "description": "Structured clinical course forms (curso clinico)"},
                {"code": "EF", "description": "Physical examination forms (examen fisico)"},
                {"code": "ES", "description": "Scale forms (escalas)"},
                {"code": "RG", "description": "Record or report forms (registro)"},
                {"code": "RE", "description": "Special record forms (registros especiales)"},
                {"code": "VA", "description": "Assessment forms (valoracion)"},
                {"code": "TS", "description": "Social work forms (trabajo social)"},
            ],
        },
        "provision_category": {
            "description": "Provision category (g_provisions.category)",
            "filename": "enum_provision_category.csv",
            "source_table": "g_provisions",
            "data": [
                {"code": "2", "description": "Generic provisions"},
                {"code": "6", "description": "Imaging diagnostic provisions"},
            ],
        },
        "encounter_type_descr": {
            "description": "Encounter type codes with descriptions (g_encounters.encounter_type)",
            "filename": "enum_encounter_type_descr.csv",
            "source_table": "g_encounters",
            "data": [
                {"code": "2O", "description": "2a opinion"},
                {"code": "AD", "description": "Hosp. dia domic."},
                {"code": "BO", "description": "Blog. obstetrico"},
                {"code": "CA", "description": "Cirugia mayor A"},
                {"code": "CM", "description": "Cirugia menor A"},
                {"code": "CU", "description": "Cura"},
                {"code": "DH", "description": "Derivacion hosp"},
                {"code": "DI", "description": "Der. otros serv."},
                {"code": "DU", "description": "Derivacion urg."},
                {"code": "EI", "description": "Entrega ICML"},
                {"code": "HD", "description": "Hospital de dia"},
                {"code": "IC", "description": "Interconsulta"},
                {"code": "IH", "description": "Servicio final"},
                {"code": "IQ", "description": "Interv. quir."},
                {"code": "LT", "description": "Llamada telef."},
                {"code": "MA", "description": "Copia mater."},
                {"code": "MO", "description": "Morgue"},
                {"code": "NE", "description": "Necropsia"},
                {"code": "PA", "description": "Preanestesia"},
                {"code": "PD", "description": "Posible donante"},
                {"code": "PF", "description": "Pompas funebres"},
                {"code": "PP", "description": "Previa prueba"},
                {"code": "PR", "description": "Prueba"},
                {"code": "PV", "description": "Primera vista"},
                {"code": "RE", "description": "Recetas"},
                {"code": "SM", "description": "Sec. multicentro"},
                {"code": "TR", "description": "Tratamiento"},
                {"code": "UD", "description": "Urg. hosp. dia"},
                {"code": "UR", "description": "Urgencias"},
                {"code": "VD", "description": "Vis. domicilio"},
                {"code": "VE", "description": "V. Enf. Hospital"},
                {"code": "VS", "description": "Vista sucesiva"},
                {"code": "VU", "description": "Vista URPA / Vista urgencias"},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def fix_encoding(text):
    """Fix double-encoded UTF-8 text (latin-1 -> utf-8)."""
    if pd.isna(text):
        return text
    try:
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def extract_db_dictionary(dict_id, config):
    """
    Extract a dictionary from the database via SQL query.

    Returns:
        tuple: (DataFrame or None, success: bool)
    """
    from connection import execute_query

    print(f"  >>> Executing query on {config.get('source_table', '?')}...")
    start = time.time()

    try:
        df = execute_query(config["query"])
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, False

    if df is None or df.empty:
        print(f"  WARNING: No data retrieved for {dict_id}")
        return pd.DataFrame(), False

    elapsed = time.time() - start
    print(f"  Retrieved {len(df):,} rows in {elapsed:.1f}s")

    # Fix encoding on text columns
    for col in config.get("text_columns", []):
        if col in df.columns:
            df[col] = df[col].apply(fix_encoding)

    # Save CSV
    output_path = OUTPUT_DIR / config["filename"]
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"  Saved: {config['filename']} ({len(df):,} rows)")

    return df, True


def generate_inline_enum(dict_id, config):
    """
    Generate a CSV from hard-coded inline enum data.

    Returns:
        tuple: (DataFrame or None, success: bool)
    """
    df = pd.DataFrame(config["data"])

    output_path = OUTPUT_DIR / config["filename"]
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"  Saved: {config['filename']} ({len(df)} rows)")

    return df, True


def generate_manifest(results):
    """
    Generate dictionaries_manifest.csv and dictionaries_README.md from extraction results.

    Args:
        results: dict of {dict_id: {category, filename, description, source_table, row_count, success}}
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- CSV manifest ---
    manifest_path = OUTPUT_DIR / "dictionaries_manifest.csv"
    rows = []
    for dict_id, info in sorted(results.items(), key=lambda x: (x[1]["category"], x[0])):
        if not info["success"]:
            continue
        rows.append({
            "dict_id": dict_id,
            "category": info["category"],
            "filename": info["filename"],
            "description": info["description"],
            "source_table": info["source_table"],
            "row_count": info["row_count"],
            "extraction_date": now,
        })

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "dict_id", "category", "filename", "description",
            "source_table", "row_count", "extraction_date",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nManifest saved: {manifest_path.name} ({len(rows)} entries)")

    # --- Markdown README ---
    readme_path = OUTPUT_DIR / "dictionaries_README.md"
    lines = [
        f"# Dictionary Repository",
        f"",
        f"Generated: {now}",
        f"Total dictionaries: {len(rows)}",
        f"",
    ]

    categories = {
        "from_dic_tables": "From Dictionary Tables (dic_*)",
        "from_data_tables": "From Data Tables (SELECT DISTINCT)",
        "inline_enums": "Inline Enumerations (hard-coded from DB_CONTEXT.md)",
    }

    for cat_key, cat_title in categories.items():
        cat_rows = [r for r in rows if r["category"] == cat_key]
        if not cat_rows:
            continue

        lines.append(f"## {cat_title}")
        lines.append("")
        lines.append("| File | Description | Source | Rows |")
        lines.append("|------|-------------|--------|------|")
        for r in cat_rows:
            lines.append(
                f"| {r['filename']} | {r['description']} "
                f"| {r['source_table']} | {r['row_count']:,} |"
            )
        lines.append("")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"README saved: {readme_path.name}")


def list_dictionaries():
    """Print all available dictionaries grouped by category."""
    categories = {
        "from_dic_tables": "FROM DIC_* TABLES",
        "from_data_tables": "FROM DATA TABLES (SELECT DISTINCT)",
        "inline_enums": "INLINE ENUMERATIONS (no DB needed)",
    }

    total = 0
    for cat_key, cat_title in categories.items():
        dicts = DICTIONARY_REGISTRY[cat_key]
        print(f"\n{'='*70}")
        print(f"  {cat_title} ({len(dicts)} dictionaries)")
        print(f"{'='*70}")
        for dict_id, config in dicts.items():
            slow_tag = " [SLOW]" if config.get("slow") else ""
            print(f"  {dict_id:35s} -> {config['filename']}{slow_tag}")
            print(f"  {'':35s}    {config['description']}")
        total += len(dicts)

    print(f"\n{'='*70}")
    print(f"  TOTAL: {total} dictionaries")
    print(f"{'='*70}")


def find_dict_entry(dict_id):
    """Find a dictionary entry by ID across all categories. Returns (category, config) or (None, None)."""
    for category, dicts in DICTIONARY_REGISTRY.items():
        if dict_id in dicts:
            return category, dicts[dict_id]
    return None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract all DataNex dictionaries into CSV files for AI-assisted coding.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python extract_all_dictionaries.py --all\n"
            "  python extract_all_dictionaries.py --category inline_enums\n"
            "  python extract_all_dictionaries.py --dict nationality drug atc\n"
            "  python extract_all_dictionaries.py --list\n"
            "  python extract_all_dictionaries.py --all --skip-slow\n"
        ),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Extract all dictionaries")
    group.add_argument(
        "--category",
        choices=["from_dic_tables", "from_data_tables", "inline_enums"],
        help="Extract all dictionaries in a category",
    )
    group.add_argument("--dict", nargs="+", metavar="ID", help="Extract specific dictionaries by ID")
    group.add_argument("--list", action="store_true", help="List all available dictionaries")

    parser.add_argument("--dry-run", action="store_true", help="Show what would be extracted without running")
    parser.add_argument("--skip-slow", action="store_true", help="Skip dictionaries marked as slow")

    return parser.parse_args()


def main():
    args = parse_args()

    # --- List mode ---
    if args.list:
        list_dictionaries()
        return

    # --- Determine which dictionaries to extract ---
    to_extract = []  # list of (dict_id, category, config)

    if args.all:
        for category, dicts in DICTIONARY_REGISTRY.items():
            for dict_id, config in dicts.items():
                to_extract.append((dict_id, category, config))

    elif args.category:
        category = args.category
        for dict_id, config in DICTIONARY_REGISTRY[category].items():
            to_extract.append((dict_id, category, config))

    elif args.dict:
        for dict_id in args.dict:
            category, config = find_dict_entry(dict_id)
            if config is None:
                print(f"ERROR: Unknown dictionary ID '{dict_id}'. Use --list to see available IDs.")
                sys.exit(1)
            to_extract.append((dict_id, category, config))

    # --- Filter slow if requested ---
    if args.skip_slow:
        before = len(to_extract)
        to_extract = [(d, c, cfg) for d, c, cfg in to_extract if not cfg.get("slow")]
        skipped = before - len(to_extract)
        if skipped:
            print(f"Skipping {skipped} slow dictionaries (use --all without --skip-slow to include them)")

    # --- Dry-run mode ---
    if args.dry_run:
        print(f"\nDRY RUN - Would extract {len(to_extract)} dictionaries:\n")
        for dict_id, category, config in to_extract:
            slow_tag = " [SLOW]" if config.get("slow") else ""
            print(f"  [{category}] {dict_id} -> {config['filename']}{slow_tag}")
        return

    # --- Extract ---
    print(f"\n{'='*70}")
    print(f"DATANEX DICTIONARY EXTRACTION")
    print(f"{'='*70}")
    print(f"Extracting {len(to_extract)} dictionaries to: {OUTPUT_DIR}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    success_count = 0
    fail_count = 0

    for i, (dict_id, category, config) in enumerate(to_extract, 1):
        slow_tag = " [SLOW]" if config.get("slow") else ""
        print(f"\n[{i}/{len(to_extract)}] {dict_id}{slow_tag}")

        if category == "inline_enums":
            df, success = generate_inline_enum(dict_id, config)
        else:
            df, success = extract_db_dictionary(dict_id, config)

        row_count = len(df) if df is not None else 0
        results[dict_id] = {
            "category": category,
            "filename": config["filename"],
            "description": config["description"],
            "source_table": config.get("source_table", ""),
            "row_count": row_count,
            "success": success,
        }

        if success:
            success_count += 1
        else:
            fail_count += 1

    # --- Generate manifest ---
    print(f"\n{'='*70}")
    print("GENERATING MANIFEST")
    print(f"{'='*70}")
    generate_manifest(results)

    # --- Summary ---
    print(f"\n{'='*70}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*70}")
    print(f"  Successful: {success_count}")
    if fail_count:
        print(f"  Failed:     {fail_count}")
        for dict_id, info in results.items():
            if not info["success"]:
                print(f"    - {dict_id}: {info['filename']}")
    print(f"  Total:      {success_count + fail_count}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user (Ctrl+C)")
        sys.exit(0)
