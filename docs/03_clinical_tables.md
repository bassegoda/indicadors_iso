# DataNex Clinical Tables

## g_diagnostics

Contains information about the diagnoses for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| diag_date | DATETIME | | Diagnostic code registration date |
| diag_ref | INT | FK | DataNex own diagnosis reference number |
| catalog | INT | | Catalog: 1=CIE9 MC, 2=MDC, 3=CIE9 Emergencies, 5=SNOMED, 8=SNOMEDCT, 12=CIE10 MC, 13=CIE10 Outpatients |
| code | VARCHAR(45) | | ICD-9 or ICD-10 code for each diagnosis |
| diag_descr | VARCHAR(256) | | Description of the diagnosis (nullable) |
| class | VARCHAR(2) | | **P** (primary validated), **S** (secondary validated), **H** (not validated), **E** (emergency), **A** (outpatient) |
| poa | VARCHAR(2) | | Present on Admission: **Y** (yes), **N** (no), **U** (unknown), **W** (undetermined), **E** (exempt), **-** (unreported) |
| load_date | DATETIME | | Date of update |

---

## g_diagnostic_related_groups

Contains Diagnosis-Related-Groups (DRG) for billing and resource allocation.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| weight | DOUBLE | | DRG cost weight (nullable) |
| drg_ref | INT | FK | DRG reference |
| severity_ref | VARCHAR(2) | FK | SOI (Severity of Illness) reference (nullable) |
| severity_descr | VARCHAR(128) | | SOI description (nullable) |
| mortality_risk_ref | VARCHAR(2) | FK | ROM (Risk of Mortality) reference (nullable) |
| mortality_risk_descr | VARCHAR(45) | | ROM description (nullable) |
| mdc_ref | VARCHAR(191) | FK | MDC (Major Diagnostic Categories) reference |
| load_date | DATETIME | | Date of update |

---

## g_health_issues

Contains SNOMED-CT codified health problems recorded by doctors.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode (nullable) |
| snomed_ref | BIGINT | | SNOMED code for a health problem |
| snomed_descr | VARCHAR(255) | | Description of the SNOMED code |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference (nullable) |
| start_date | DATETIME | | Start date of the health problem |
| end_date | DATETIME | | End date of the health problem (nullable) |
| end_motive | VARCHAR(2) | | Reason for the change (nullable) |
| load_date | DATETIME | | Date of update |

---

## g_labs

Contains the laboratory tests for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| result_date | DATETIME | | Date and time the result was obtained |
| load_date | DATETIME | | Date of update |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| care_level_ref | INT | FK | Care level identifier (nullable) |
| lab_sap_ref | VARCHAR(16) | FK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | lab_sap_ref description |
| result_num | DOUBLE | | Numerical result (nullable) |
| result_txt | VARCHAR(100) | | Text result (nullable) |
| units | VARCHAR(32) | | Units (nullable) |
| lab_group_ref | VARCHAR(16) | FK | Reference for grouped laboratory parameters (nullable) |

---

## g_rc

Contains the clinical records for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode (nullable) |
| result_date | DATETIME | | Date and time of the measurement |
| meas_type_ref | VARCHAR(2) | | 0 (manual), 1 (machine, not validated), 2 (machine, validated) |
| load_date | DATETIME | | Date of update |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| rc_descr | VARCHAR(256) | | Description of the clinical record |
| result_num | DOUBLE | | Numerical result (nullable) |
| result_txt | VARCHAR(36) | | Text result (nullable) |
| units | VARCHAR(32) | | Units (nullable) |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_micro

Contains the microbiology results for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| res_date | DATETIME | | Date and time the result was obtained |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| mue_ref | VARCHAR(10) | | Code for sample type or origin |
| mue_descr | VARCHAR(60) | | Description of sample type |
| method_descr | VARCHAR(128) | | Method used to process the sample (nullable) |
| positive | CHAR(2) | | 'X' = microorganism detected |
| antibiogram_ref | CHAR(36) | FK | Antibiogram identifier (nullable) |
| micro_ref | VARCHAR(10) | | Microorganism code (nullable) |
| micro_descr | VARCHAR(60) | | Scientific name of microorganism (nullable) |
| num_micro | INT | | Sequential number for identified microbes (nullable) |
| result_text | TEXT | | Text result (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_antibiograms

Contains the antibiograms for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| result_date | DATETIME | | Date and time the result was obtained |
| sample_ref | VARCHAR(10) | | Code for sample type |
| sample_descr | VARCHAR(60) | | Description of sample |
| antibiogram_ref | CHAR(36) | | Unique antibiogram identifier |
| micro_ref | VARCHAR(10) | | Microorganism code |
| micro_descr | VARCHAR(60) | | Scientific name of microorganism |
| antibiotic_ref | CHAR(10) | | Antibiotic code |
| antibiotic_descr | VARCHAR(60) | | Full name of antibiotic |
| result | CHAR(60) | | MIC result (nullable) |
| sensitivity | CHAR(2) | | **S** (sensitive) or **R** (resistant) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_prescriptions

Contains prescribed medical products. Links to g_administrations and g_perfusions via `treatment_ref`.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| prn | VARCHAR(16) | | "X" = administered only if needed (nullable) |
| freq_ref | VARCHAR(16) | FK | Administration frequency code (nullable) |
| phform_ref | INT | FK | Pharmaceutical form identifier (nullable) |
| phform_descr | VARCHAR(256) | | Pharmaceutical form description (nullable) |
| prescr_env_ref | INT | FK | Healthcare setting where prescription was generated |
| adm_route_ref | INT | FK | Administration route reference (nullable) |
| route_descr | VARCHAR(256) | | Route description (nullable) |
| atc_ref | VARCHAR(16) | | ATC code (nullable) |
| atc_descr | VARCHAR(256) | | ATC description (nullable) |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| start_drug_date | DATETIME | | Start date of prescription |
| end_drug_date | DATETIME | | End date of prescription |
| load_date | DATETIME | | Date of update |
| drug_ref | VARCHAR(56) | FK | Medical product identifier |
| drug_descr | VARCHAR(512) | | Drug description |
| enum | VARCHAR(16) | | Role of drug in prescription (nullable) |
| dose | FLOAT | | Prescribed dose (nullable) |
| unit | VARCHAR(8) | | Dose unit (nullable) |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_administrations

Contains administered pharmaceuticals. Links to g_prescriptions via `treatment_ref`.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| administration_date | DATETIME | | Date of administration |
| route_ref | INT | FK | Administration route reference (nullable) |
| route_descr | VARCHAR(256) | | Route description (nullable) |
| prn | VARCHAR(1) | | "X" = administered only if needed (nullable) |
| given | VARCHAR(1) | | "X" = drug has NOT been administered (nullable) |
| not_given_reason_ref | INT | | Reason for non-administration (nullable) |
| drug_ref | VARCHAR(56) | FK | Medical product identifier |
| drug_descr | VARCHAR(512) | | Drug description |
| atc_ref | VARCHAR(16) | | ATC code (nullable) |
| atc_descr | VARCHAR(256) | | ATC description (nullable) |
| enum | INT | | Role of drug in prescription (nullable) |
| quantity | FLOAT | | Dose actually administered (nullable) |
| quantity_planing | FLOAT | | Planned dose (nullable) |
| quantity_unit | VARCHAR(10) | | Dose unit (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_perfusions

Contains drug perfusion data. Links to g_prescriptions via `treatment_ref`.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| infusion_rate | FLOAT | | Rate in ml/h |
| rate_change_counter | INT | | Counter: starts at 1, increments with each rate change |
| start_date | DATETIME | | Start date of perfusion |
| end_date | DATETIME | | End date of perfusion (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Care level identifier (nullable) |

---

## g_procedures

Contains all procedures per episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(16) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| catalog | VARCHAR(2) | | 1 = ICD9; 12 = ICD10 (nullable) |
| code | VARCHAR(10) | | Procedure code |
| descr | VARCHAR(255) | | Procedure description (nullable) |
| text | VARCHAR(255) | | Details about the procedure (nullable) |
| place_ref | VARCHAR(2) | FK | Location reference (nullable) |
| place_descr | VARCHAR(255) | | Location: **1** (Surgical block), **2** (Diagnostic cabinet), **3** (Minor surgery), **4** (Interventional radiology), **5** (Non-intervention room), **6** (Obstetric block), **EX** (External) (nullable) |
| class | ENUM('P','S') | | P (primary), S (secondary) (nullable) |
| start_date | DATETIME | | Start date (nullable) |
| load_date | DATETIME | | Date of update |

---

## g_surgery

Contains general information about surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| mov_ref | INT | FK | Reference joining surgery with its movement |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| operating_room | VARCHAR(10) | | Assigned operating room (nullable) |
| start_date | DATETIME | | Surgery start time (nullable) |
| end_date | DATETIME | | Surgery end time (nullable) |
| surgery_ref | INT | FK | Surgery identifier; links to other Surgery tables |
| surgery_code | VARCHAR(10) | | Local Q code (e.g., Q01972) |
| surgery_code_descr | VARCHAR(255) | | Surgery description |

---

## g_surgery_team

Contains surgical tasks performed during procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| surgery_ref | INT | FK | Surgery identifier |
| task_ref | VARCHAR(4) | | Surgical task code |
| task_descr | VARCHAR(60) | | Task description (nullable) |
| employee | VARCHAR(10) | | Employee who performed the task (nullable) |

---

## g_surgery_timestamps

Stores timestamps of surgical events.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| event_label | VARCHAR(10) | | Surgical event code |
| event_descr | VARCHAR(60) | | Event description (nullable) |
| event_timestamp | DATETIME | | When the event happened |
| surgery_ref | INT | FK | Surgery identifier |

---

## g_surgery_waiting_list

Contains waiting list information for surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| surgeon_code | INT | | Surgeon code |
| waiting_list | VARCHAR(50) | | Waiting list name |
| planned_date | DATETIME | | Scheduled surgery date (nullable) |
| proc_ref | VARCHAR(8) | FK | Procedure code (nullable) |
| registration_date | DATETIME | | Date registered on waiting list (nullable) |
| requesting_physician | INT | | Requesting physician (nullable) |
| priority | INT | | Priority in waiting list (nullable) |

---

## g_pathology_sample

Contains Pathology samples for each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR(20) | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR(20) | FK | Sample reference |
| sample_descr | VARCHAR(45) | | Sample description (nullable) |
| validated_by | INT | | Employee who validated (nullable) |

---

## g_pathology_diagnostic

Contains Pathology diagnoses for each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR(20) | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR(20) | FK | Sample reference |
| diag_type | VARCHAR(2) | | Type of diagnosis |
| diag_code | VARCHAR(20) | | Diagnosis code |
| diag_date | DATETIME | | Diagnosis date |
| diag_descr | VARCHAR(50) | | Diagnosis description |
| validated_by | INT | | Employee who validated (nullable) |

---

## g_dynamic_forms

Dynamic forms collect clinical data in a structured manner.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| status | VARCHAR(3) | | **CO** (completed), **EC** (in process) |
| class_ref | VARCHAR(16) | | Assessment class reference |
| class_descr | VARCHAR(132) | | Class: **CC** (clinical course), **EF** (physical exam), **ES** (scales), **RG** (reports), **RE** (special records), **VA** (assessment), **TS** (social work) |
| form_ref | VARCHAR(16) | | Form identifier |
| form_descr | VARCHAR(150) | | Form description |
| form_date | DATETIME | | Date form was saved |
| tab_ref | VARCHAR(16) | | Tab (group) identifier |
| tab_descr | VARCHAR(132) | | Tab description |
| section_ref | VARCHAR(16) | | Section identifier |
| section_descr | VARCHAR(300) | | Section description |
| question_ref | VARCHAR(16) | | Question identifier |
| question_descr | VARCHAR(300) | | Question description |
| value_num | DOUBLE | | Numeric value (nullable) |
| value_text | CHAR(255) | | Text value (nullable) |
| value_date | DATETIME(3) | | Datetime value (nullable) |
| value_descr | CHAR(128) | | Value description |
| load_date | DATETIME | | Date of update |

---

## g_special_records

Nursing records - a specific type of dynamic form completed by nurses.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| status | VARCHAR(3) | | **CO** (completed), **EC** (in process) |
| class_ref | VARCHAR(16) | | Assessment class reference |
| class_descr | VARCHAR(132) | | Class: **RE** (special records) |
| form_ref | VARCHAR(16) | | Form identifier |
| form_descr | VARCHAR(150) | | Form description |
| tab_ref | VARCHAR(16) | | Tab identifier |
| tab_descr | VARCHAR(132) | | Tab description |
| section_ref | VARCHAR(16) | | Section identifier |
| section_descr | VARCHAR(300) | | Section description |
| question_ref | VARCHAR(16) | | Question identifier |
| question_descr | VARCHAR(300) | | Question description |
| start_date | DATETIME(3) | | Start date (nullable) |
| end_date | DATETIME(3) | | End date (nullable) |
| value_num | DOUBLE | | Numeric value (nullable) |
| value_text | CHAR(255) | | Text value (nullable) |
| value_descr | CHAR(128) | | Value description |
| load_date | DATETIME | | Date of update |
