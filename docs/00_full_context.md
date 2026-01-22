# DataNex Database Schema - LLM Context

**Purpose**: Comprehensive reference for SQL query generation from natural language

## Instructions for LLM

You are a SQL query generator specialized in DataNex (Hospital Clinic database). Use MySQL MariaDB dialect.
Your task: Create SQL queries from natural language questions.

### Process:
1. Confirm you understand the DataNex schema
2. Request the natural language question
3. Use 'descr' fields in DICTIONARIES section to find corresponding 'ref' codes
4. Generate optimized SQL query using CTEs when appropriate
5. Present the final query ready for copy-paste

### Rules:
- Always explain how the query works before showing it
- Search using 'ref' fields, not 'descr'
- Use Common Table Expressions (CTEs) for optimization
- Do not explain optimizations, just do them
- For laboratory data, search in dic_lab dictionary
- For diagnoses, search in dic_diagnostic dictionary

---

## Database Overview

DataNex is a database made up of several tables. The central tables are **g_episodes**, **g_care_levels** and **g_movements**:

- **Episodes**: Medical events experienced by a patient (admission, emergency assessment, outpatient visits, etc.)
- **Care levels**: Intensity of healthcare needs (ICU, WARD, etc.)
- **Movements**: Changes in patient's location

These three central tables follow a hierarchy: **episodes → care_levels → movements**

---

## Database Views (All Tables)

Total views: 34

---

### g_episodes

Contains all hospital episodes for each patient. An episode represents a medical event: an admission, an emergency assessment, outpatient visits, etc.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| episode_ref | INT | PK | Pseudonymized number that identifies an episode |
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_type_ref | VARCHAR(8) | FK | Episode type reference |
| start_date | DATETIME | | Start date of the episode |
| end_date | DATETIME | | End date of the episode |
| load_date | DATETIME | | Date of update |

---

### g_care_levels

Contains the care levels for each episode. Care level refers to the intensity of healthcare needs that a patient requires.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| care_level_ref | INT | PK | Unique identifier that groups care levels (ICU, WARD, etc.) if they are consecutive and belong to the same level |
| start_date | DATETIME | | Start date of the care level |
| end_date | DATETIME | | End date of the care level |
| load_date | DATETIME | | Date of update |
| care_level_type_ref | VARCHAR(16) | FK | Care level type reference |

---

### g_movements

Contains the movements for each care level. Movements are changes in the patient's location.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| start_date | DATETIME | | Start date of the movement |
| end_date | DATETIME | | End date of the movement |
| place_ref | BIGINT | FK | Place reference (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| ou_med_descr | VARCHAR(32) | | Description of the medical organizational unit |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference |
| ou_loc_descr | VARCHAR(256) | | Description of the physical hospitalization unit (nullable) |
| care_level_type_ref | VARCHAR(16) | FK | Care level type reference |
| facility | VARCHAR(32) | | Facility name |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_demographics

Contains demographic information for each patient.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | PK | Pseudonymized number that identifies a patient |
| birth_date | DATE | | Date of birth |
| sex | INT | | Sex: -1 (not reported in SAP), 1 (male), 2 (female), 3 (other) |
| natio_ref | VARCHAR(8) | FK | Reference code for nationality |
| natio_descr | VARCHAR(256) | | Description of the country code according to ISO:3 |
| health_area | VARCHAR(9) | | Health area (nullable) |
| postcode | VARCHAR(10) | | Postal code (nullable) |
| load_date | DATETIME | | Date of update |

---

### g_exitus

Contains the date of death for each patient.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | PK | Pseudonymized number that identifies a patient |
| exitus_date | DATE | | Date of death |
| load_date | DATETIME | | Date and time of update |

---

### g_adm_disch

Contains the reasons for admission and discharge per episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| mot_ref | INT | FK | Reason for admission or discharge (numeric) |
| mot_descr | VARCHAR(32) | | Description of the mot_ref |
| mot_type | VARCHAR(45) | | Indicates if it is the starting motive (ST) or the ending motive (END) of the episode |
| load_date | DATETIME | | Update date |

---

### g_diagnostics

Contains information about the diagnoses for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| diag_date | DATETIME | | Diagnostic code registration date |
| diag_ref | INT | FK | DataNex own diagnosis reference number |
| catalog | INT | | Catalog to which the 'code' belongs: 1=CIE9 MC (until 2017), 2=MDC, 3=CIE9 Emergencies, 4=ACR, 5=SNOMED, 7=MDC-AP, 8=SNOMEDCT, 9=Subset ANP SNOMED CT, 10=Subset ANP SNOMED ID, 11=CIE9 in Outpatients, 12=CIE10 MC, 13=CIE10 Outpatients |
| code | VARCHAR(45) | | ICD-9 or ICD-10 code for each diagnosis |
| diag_descr | VARCHAR(256) | | Description of the diagnosis (nullable) |
| class | VARCHAR(2) | | **P** (primary diagnosis validated), **S** (secondary diagnosis validated), **H** (diagnosis not validated), **E** (emergency diagnosis), **A** (outpatient diagnosis). A hospitalization episode has only one P diagnosis and zero or more S or H diagnoses |
| poa | VARCHAR(2) | | Present on Admission indicator: **Y** (present at admission), **N** (not present at admission), **U** (unknown), **W** (clinically undetermined), **E** (exempt), **-** (unreported) |
| load_date | DATETIME | | Date of update |

---

### g_diagnostic_related_groups

Contains the Diagnosis-Related-Groups (DRG). DRG categorizes hospital cases into groups according to diagnosis, procedures, age, comorbidities and other factors. Used mainly for administrative purposes, billing and resource allocation.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| weight | DOUBLE | | DRG cost weight - relative resource consumption for that group compared to others (nullable) |
| drg_ref | INT | FK | DRG (Diagnosis-Related Group) reference |
| severity_ref | VARCHAR(2) | FK | SOI (Severity of Illness) reference - metric to evaluate how sick a patient is (nullable) |
| severity_descr | VARCHAR(128) | | Description of the SOI reference (nullable) |
| mortality_risk_ref | VARCHAR(2) | FK | ROM (Risk of Mortality) reference - metric to evaluate likelihood of patient dying (nullable) |
| mortality_risk_descr | VARCHAR(45) | | Description of the ROM reference (nullable) |
| mdc_ref | VARCHAR(191) | FK | MDC (Major Diagnostic Categories) reference - broad categories used to group DRG based on similar clinical conditions or body systems |
| load_date | DATETIME | | Date of update |

---

### g_health_issues

Contains information about all health problems related to a patient. Health problems are SNOMED-CT codified and recorded by doctors.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode (nullable) |
| snomed_ref | BIGINT | | SNOMED code for a health problem |
| snomed_descr | VARCHAR(255) | | Description of the SNOMED code |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference (nullable) |
| start_date | DATETIME | | Start date of the health problem |
| end_date | DATETIME | | End date of the health problem (nullable, not mandatory) |
| end_motive | VARCHAR(2) | | Reason for the change (nullable, not mandatory) |
| load_date | DATETIME | | Date of update |

---

### g_labs

Contains the laboratory tests for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| result_date | DATETIME | | Date and time the result was obtained |
| load_date | DATETIME | | Date of update |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| care_level_ref | INT | FK | Unique identifier that groups care levels; absent if lab test is requested after the end of the episode in EM, HOSP and HAH episodes (nullable) |
| lab_sap_ref | VARCHAR(16) | FK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | lab_sap_ref description |
| result_num | DOUBLE | | Numerical result of the laboratory test (nullable) |
| result_txt | VARCHAR(100) | | Text result from the DataNex laboratory reference (nullable) |
| units | VARCHAR(32) | | Units (nullable) |
| lab_group_ref | VARCHAR(16) | FK | Reference for grouped laboratory parameters (nullable) |

---

### g_rc

Contains the clinical records for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode (nullable) |
| result_date | DATETIME | | Date and time of the measurement |
| meas_type_ref | VARCHAR(2) | | 0 (manual input), 1 (from machine, result not validated), 2 (from machine, result validated) |
| load_date | DATETIME | | Date of update |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit; filled if manually collected, empty if automatically collected (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit; filled if manually collected, empty if automatically collected (nullable) |
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| rc_descr | VARCHAR(256) | | Description of the SAP clinical record reference |
| result_num | DOUBLE | | Numerical result of the clinical record (nullable) |
| result_txt | VARCHAR(36) | | Text result from the DataNex clinical record reference (nullable) |
| units | VARCHAR(32) | | Units (nullable) |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_micro

Contains the microbiology results for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| res_date | DATETIME | | Date and time the result was obtained |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| mue_ref | VARCHAR(10) | | Code that identifies the type or origin of the sample |
| mue_descr | VARCHAR(60) | | Description of the type or origin of the sample; provides a general classification |
| method_descr | VARCHAR(128) | | Detailed description of the sample itself or the method used to process the sample; includes specific procedures and tests performed (nullable) |
| positive | CHAR(2) | | 'X' means that a microorganism has been detected in the sample |
| antibiogram_ref | CHAR(36) | FK | Unique identifier for the antibiogram (nullable) |
| micro_ref | VARCHAR(10) | | Code that identifies the microorganism (nullable) |
| micro_descr | VARCHAR(60) | | Scientific name of the microorganism (nullable) |
| num_micro | INT | | Number that starts at 1 for the first identified microbe and increments by 1 for each newly identified microbe in the sample (nullable) |
| result_text | TEXT | | Text result from the microbiology sample (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_antibiograms

Contains the antibiograms for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| result_date | DATETIME | | Date and time the result was obtained |
| sample_ref | VARCHAR(10) | | Code that identifies the type or origin of the sample |
| sample_descr | VARCHAR(60) | | Description of the type or origin of the sample; provides a general classification |
| antibiogram_ref | CHAR(36) | | Unique identifier for the antibiogram |
| micro_ref | VARCHAR(10) | | Code that identifies the microorganism |
| micro_descr | VARCHAR(60) | | Scientific name of the microorganism |
| antibiotic_ref | CHAR(10) | | Code of the antibiotic used in the sensitivity testing |
| antibiotic_descr | VARCHAR(60) | | Full name of the antibiotic |
| result | CHAR(60) | | Result of the antibiotic sensitivity test; represents the minimum inhibitory concentration (MIC) required to inhibit the growth of the bacteria (nullable) |
| sensitivity | CHAR(2) | | Sensitivity (S) or resistance (R) of the bacteria to the antibiotic tested |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_prescriptions

Contains the prescribed medical products (pharmaceuticals and medical devices) for each episode. A treatment prescription (identified by `treatment_ref`) may be composed by one or more medical products. The `treatment_ref` field links `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| prn | VARCHAR(16) | | Null value or "X"; the "X" indicates that this drug is administered only if needed (nullable) |
| freq_ref | VARCHAR(16) | FK | Administration frequency code (nullable) |
| phform_ref | INT | FK | Pharmaceutical form identifier (nullable) |
| phform_descr | VARCHAR(256) | | Description of phform_ref (nullable) |
| prescr_env_ref | INT | FK | Healthcare setting where the prescription was generated |
| adm_route_ref | INT | FK | Administration route reference (nullable) |
| route_descr | VARCHAR(256) | | Description of adm_route_ref (nullable) |
| atc_ref | VARCHAR(16) | | ATC code (nullable) |
| atc_descr | VARCHAR(256) | | Description of the ATC code (nullable) |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| start_drug_date | DATETIME | | Start date of prescription validity |
| end_drug_date | DATETIME | | End date of prescription validity |
| load_date | DATETIME | | Date of update |
| drug_ref | VARCHAR(56) | FK | Medical product identifier |
| drug_descr | VARCHAR(512) | | Description of the drug_ref field |
| enum | VARCHAR(16) | | Role of the drug in the prescription (nullable) |
| dose | FLOAT | | Prescribed dose (nullable) |
| unit | VARCHAR(8) | | Dose unit (nullable) |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_administrations

Contains the administered pharmaceuticals (drugs) for each episode. The `treatment_ref` field links `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| administration_date | DATETIME | | Date of administration |
| route_ref | INT | FK | Administration route reference (nullable) |
| route_descr | VARCHAR(256) | | Description of route_ref (nullable) |
| prn | VARCHAR(1) | | Null value or "X"; the "X" indicates that this drug is administered only if needed (nullable) |
| given | VARCHAR(1) | | Null value or "X"; the "X" indicates that this drug has not been administered (nullable) |
| not_given_reason_ref | INT | | Number that indicates the reason for non-administration (nullable) |
| drug_ref | VARCHAR(56) | FK | Medical product identifier |
| drug_descr | VARCHAR(512) | | Description of the drug_ref field |
| atc_ref | VARCHAR(16) | | ATC code (nullable) |
| atc_descr | VARCHAR(256) | | Description of the ATC code (nullable) |
| enum | INT | | Role of the drug in the prescription (nullable) |
| quantity | FLOAT | | Dose actually administered to the patient (nullable) |
| quantity_planing | FLOAT | | Planned dose (nullable) |
| quantity_unit | VARCHAR(10) | | Dose unit (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_perfusions

Contains data about the administered drug perfusions for each episode. The `treatment_ref` field links `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription; points to `treatment_ref` in `g_administrations` and `g_prescriptions` tables |
| infusion_rate | FLOAT | | Rate in ml/h |
| rate_change_counter | INT | | Perfusion rate change counter: starts at 1 (first rate) and increments by one unit with each change |
| start_date | DATETIME | | Start date of the perfusion |
| end_date | DATETIME | | End date of the perfusion (nullable) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (nullable) |

---

### g_encounters

An encounter refers to a punctual event in which detailed information is recorded about a medical interaction or procedure involving a patient (e.g., a chest radiograph, an outpatient visit, etc.).

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| date | DATETIME | | Date of the encounter event |
| load_date | DATETIME | | Update date |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference |
| encounter_type | VARCHAR(4) | FK | Encounter type (nullable) |
| agen_ref | VARCHAR(8) | FK | Code that identifies the encounter (nullable) |
| act_type_ref | VARCHAR(8) | FK | Activity type (nullable) |

**Encounter type dictionary:**

| Code | Description |
|------|-------------|
| 2O | 2ª opinión |
| AD | Hosp. día domic. |
| BO | Blog. obstétrico |
| CA | Cirugía mayor A |
| CM | Cirugía menor A |
| CU | Cura |
| DH | Derivación hosp |
| DI | Der. otros serv. |
| DU | Derivación urg. |
| EI | Entrega ICML |
| HD | Hospital de día |
| IC | Interconsulta |
| IH | Servicio final |
| IQ | Interv. quir. |
| LT | Llamada telef. |
| MA | Copia mater. |
| MO | Morgue |
| NE | Necropsia |
| PA | Preanestesia |
| PD | Posible donante |
| PF | Pompas fúnebres |
| PP | Previa prueba |
| PR | Prueba |
| PV | Primera vista |
| RE | Recetas |
| SM | Sec. multicentro |
| TR | Tratamiento |
| UD | Urg. hosp. día |
| UR | Urgencias |
| VD | Vis. domicilio |
| VE | V. Enf. Hospital |
| VU | Vista URPA |
| VS | Vista sucesiva |

---

### g_procedures

Contains all procedures per episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(16) | FK | Physical hospitalization unit (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit (nullable) |
| catalog | VARCHAR(2) | | 1 is ICD9; 12 is ICD10 (nullable) |
| code | VARCHAR(10) | | Procedure code |
| descr | VARCHAR(255) | | Procedure description (nullable) |
| text | VARCHAR(255) | | Details about the procedure (nullable) |
| place_ref | VARCHAR(2) | FK | Location of the procedure (nullable) |
| place_descr | VARCHAR(255) | | Description of place: **1** (Bloque quirúrgico), **2** (Gabinete diagnóstico y terapéutico), **3** (Cirugía menor), **4** (Radiología intervencionista o medicina nuclear), **5** (Sala de no intervención), **6** (Bloque obstétrico), **EX** (Procedimiento externo) (nullable) |
| class | ENUM('P','S') | | P (primary procedure), S (secondary procedure) (nullable) |
| start_date | DATETIME | | Start date of the procedure (nullable) |
| load_date | DATETIME | | Date and time of update |

---

### g_provisions

Provisions are healthcare benefits. They are usually categorized into three levels: each level 1 class contains its own level 2 classes, and each level 2 class contains its own level 3 classes. However, this structure is not mandatory.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_med_ref_order | VARCHAR(8) | FK | Medical organizational unit that requests the provision (nullable) |
| prov_ref | VARCHAR(32) | | Code that identifies the healthcare provision |
| prov_descr | VARCHAR(255) | | Description of the provision code |
| level_1_ref | VARCHAR(16) | | Level 1 code; may end with '_inferido' indicating inferred from context (nullable) |
| level_1_descr | VARCHAR(45) | | Level 1 code description (nullable) |
| level_2_ref | VARCHAR(3) | | Level 2 code (nullable) |
| level_2_descr | VARCHAR(55) | | Level 2 code description (nullable) |
| level_3_ref | VARCHAR(3) | | Level 3 code (nullable) |
| level_3_descr | VARCHAR(50) | | Level 3 code description (nullable) |
| category | INT | | Class of the provision: **2** (generic provisions), **6** (imaging diagnostic provisions) (nullable) |
| start_date | DATETIME | | Start date of the provision |
| end_date | DATETIME | | End date of the provision (nullable) |
| accession_number | VARCHAR(10) | PK | Unique identifier for each patient provision; links to XNAT data repository |
| ou_med_ref_exec | VARCHAR(8) | FK | Medical organizational unit that executes the provision (nullable) |
| start_date_plan | DATETIME | | Scheduled start date of the provision (nullable) |
| end_date_plan | DATETIME | | Scheduled end date of the provision (nullable) |

---

### g_dynamic_forms

Dynamic forms collect clinical data in a structured manner. Each dynamic form appears as many times as the form was saved in SAP.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference (nullable) |
| status | VARCHAR(3) | | Record status: **CO** (completed), **EC** (in process) |
| class_ref | VARCHAR(16) | | Assessment class reference |
| class_descr | VARCHAR(132) | | Class description: **CC** (structured clinical course forms), **EF** (physical examination forms), **ES** (scale forms), **RG** (record or report forms), **RE** (special record forms), **VA** (assessment forms), **TS** (social work forms) |
| form_ref | VARCHAR(16) | | Form name identifier |
| form_descr | VARCHAR(150) | | Form description |
| form_date | DATETIME | | Date when the form was saved |
| tab_ref | VARCHAR(16) | | Form tab (group) identifier |
| tab_descr | VARCHAR(132) | | Tab description |
| section_ref | VARCHAR(16) | | Form section (parameter) identifier |
| section_descr | VARCHAR(300) | | Section description |
| question_ref | VARCHAR(16) | | Form question (characteristic) identifier |
| question_descr | VARCHAR(300) | | Characteristic description |
| value_num | DOUBLE | | Numeric value inserted (nullable) |
| value_text | CHAR(255) | | Text value inserted (nullable) |
| value_date | DATETIME(3) | | Datetime value inserted (nullable) |
| value_descr | CHAR(128) | | Value description |
| load_date | DATETIME | | Date of update |

---

### g_special_records

Special records (nursing records) are a specific type of dynamic form completed by nurses.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference (nullable) |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference (nullable) |
| status | VARCHAR(3) | | Record status: **CO** (completed), **EC** (in process) |
| class_ref | VARCHAR(16) | | Assessment class reference |
| class_descr | VARCHAR(132) | | Class description: **RE** (special record forms) |
| form_ref | VARCHAR(16) | | Form name identifier |
| form_descr | VARCHAR(150) | | Form description |
| tab_ref | VARCHAR(16) | | Form tab (group) identifier |
| tab_descr | VARCHAR(132) | | Tab description |
| section_ref | VARCHAR(16) | | Form section (parameter) identifier |
| section_descr | VARCHAR(300) | | Section description |
| question_ref | VARCHAR(16) | | Form question (characteristic) identifier |
| question_descr | VARCHAR(300) | | Characteristic description |
| start_date | DATETIME(3) | | Start date (nullable) |
| end_date | DATETIME(3) | | End date (nullable) |
| value_num | DOUBLE | | Numeric value inserted (nullable) |
| value_text | CHAR(255) | | Text value inserted (nullable) |
| value_descr | CHAR(128) | | Value description |
| load_date | DATETIME | | Date of update |

---

### g_tags

Tags are labels used to identify groups of patients.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| tag_ref | INT | FK | Reference identifying the tag |
| tag_group | VARCHAR(16) | | Tag group |
| tag_subgroup | VARCHAR(8) | | Tag subgroup |
| tag_descr | VARCHAR(256) | | Description of the tag reference |
| inactive_atr | TINYINT(1) | | Inactivity off (0) or on (1) |
| start_date | DATETIME | | Start date and time of the tag |
| end_date | DATETIME | | End date and time of the tag (nullable) |
| load_date | DATETIME | | Update date and time |

---

### g_surgery

Contains general information about surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| mov_ref | INT | FK | Reference that joins the surgery with its movement |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference (nullable) |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference (nullable) |
| operating_room | VARCHAR(10) | | Assigned operating room (nullable) |
| start_date | DATETIME | | When the surgery starts (nullable) |
| end_date | DATETIME | | When the surgery ends (nullable) |
| surgery_ref | INT | FK | Number that identifies a surgery; links to other Surgery tables |
| surgery_code | VARCHAR(10) | | Standard code for the surgery. Local code named Q codes (e.g., Q01972) |
| surgery_code_descr | VARCHAR(255) | | Surgery code description |

---

### g_surgery_team

Contains information about surgical tasks performed during surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| surgery_ref | INT | FK | Number that identifies a surgery; links to other Surgery tables |
| task_ref | VARCHAR(4) | | Code that identifies the surgical task |
| task_descr | VARCHAR(60) | | Description of the surgical task (nullable) |
| employee | VARCHAR(10) | | Employee who performed the task (nullable) |

---

### g_surgery_timestamps

Stores the timestamps of surgical events for each surgical procedure.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| event_label | VARCHAR(10) | | Surgical event code |
| event_descr | VARCHAR(60) | | Description of the surgical event (nullable) |
| event_timestamp | DATETIME | | Timestamp indicating when the surgical event happened |
| surgery_ref | INT | FK | Number that identifies a surgery; links to other Surgery tables |

---

### g_surgery_waiting_list

Contains the waiting list information for requested surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| surgeon_code | INT | | Code identifying the surgeon |
| waiting_list | VARCHAR(50) | | Name of the waiting list |
| planned_date | DATETIME | | Scheduled date and time of the surgical intervention (nullable) |
| proc_ref | VARCHAR(8) | FK | Procedure code (nullable) |
| registration_date | DATETIME | | Date and time when the patient was registered on the waiting list (nullable) |
| requesting_physician | INT | | Physician who requested the surgery (nullable) |
| priority | INT | | Priority assigned to the patient in the waiting list (nullable) |

---

### g_pathology_sample

Contains all Pathology samples and their descriptions for each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR(20) | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR(20) | FK | Sample reference (a case holds one or more samples) |
| sample_descr | VARCHAR(45) | | Sample description (nullable) |
| validated_by | INT | | Employee who validated the sample (nullable) |

---

### g_pathology_diagnostic

Contains all Pathology diagnoses associated with each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR(20) | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR(20) | FK | Sample reference (a case holds one or more samples) |
| diag_type | VARCHAR(2) | | Type of diagnosis |
| diag_code | VARCHAR(20) | | Diagnosis code |
| diag_date | DATETIME | | Diagnosis date |
| diag_descr | VARCHAR(50) | | Diagnosis description |
| validated_by | INT | | Employee who validated the sample (nullable) |

---

## Dictionary Tables

### dic_diagnostic

Diagnosis dictionary for searching diagnoses by reference code.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| diag_ref | INT | PK | Diagnosis reference number |
| catalog | INT | | Catalog code |
| code | VARCHAR(45) | | ICD code |
| diag_descr | VARCHAR(256) | | Diagnosis description (nullable) |

---

### dic_lab

Laboratory parameters dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| lab_sap_ref | VARCHAR(16) | PK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | Laboratory parameter description |
| units | VARCHAR(32) | | Units (nullable) |
| lab_ref | INT | | Laboratory reference |

---

### dic_ou_loc

Physical hospitalization units dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_loc_ref | VARCHAR(16) | PK | Physical hospitalization unit reference |
| ou_loc_descr | VARCHAR(256) | | Description (nullable) |
| care_level_type_ref | VARCHAR(16) | | Care level type reference |
| facility_ref | INT | | Facility reference |
| facility_descr | VARCHAR(32) | | Facility description |

---

### dic_ou_med

Medical organizational units dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_med_ref | VARCHAR(8) | PK | Medical organizational unit reference |
| ou_med_descr | VARCHAR(32) | | Description |

---

### dic_rc

Clinical records dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | PK | SAP clinical record reference |
| rc_descr | VARCHAR(256) | | Clinical record description |
| units | VARCHAR(32) | | Units (nullable) |
| rc_ref | INT | | Clinical record reference |

---

### dic_rc_text

Clinical records text values dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| result_txt | VARCHAR(36) | | Text result value |
| descr | VARCHAR(191) | | Description of the text value |

---

## Key Relationships

- `patient_ref`: Links most tables (primary patient identifier)
- `episode_ref`: Links to hospital episodes
- `care_level_ref`: Groups consecutive care levels (ICU, WARD, etc.)
- `treatment_ref`: Links g_prescriptions, g_administrations, g_perfusions
- Tables follow hierarchy: **episodes → care_levels → movements**

---

## Dictionaries (ref:descr format)

**Usage**: Use 'descr' to find corresponding 'ref' code for searches.

### dic_diagnostic (35181 total entries, showing 50 samples)

```
6000001:(osteo)artrosis erosiva
6000002:(osteo)artrosis primaria generalizada
6000003:(osteo)artrosis primaria generalizada
6000004:11 semanas de gestación
6000005:22 semanas de gestación
6000006:23 semanas de gestación
6000007:24 semanas completas de gestacion, recien nacido
6000008:25 26 semanas completas de gestacion, recien nacido
6000009:27 28 semanas completas de gestacion, recien nacido
6000010:29 30 semanas completas de gestacion, recien nacido
6000011:30 semanas de gestación
6000012:31 32 semanas completas de gestacion, recien nacido
6000013:31 semanas de gestación
6000014:32 semanas de gestación
6000015:33 34 semanas completas de gestacion, recien nacido
6000016:33 semanas de gestación
6000017:34 semanas de gestación
6000018:35 36 semanas completas de gestacion, recien nacido
6000019:37 o mas semanas completas de gestacion, recien nacido
6000020:37 semanas de gestación
6000021:38 semanas de gestación
6000022:39 semanas de gestación
6000023:40 semanas de gestación
6000024:41 semanas de gestación
6000025:Abdomen agudo
6000026:Abertura artificial, no especificada
6000027:Abortadora habitual
6000028:Abortadora habitual
6000029:Aborto espontaneo con alteracion metabolica incompleto
6000030:Aborto espontaneo con complicacion neom completo
... (35131 more entries)
```

### dic_lab (5098 total entries, showing 50 samples)

```
LAB0SDHF:Gen SDH-mutació concreta (cas
LAB110:Urea
LAB1100:Tiempo de protombina segundos
LAB1101:Tiempo de tromboplastina parcial
LAB1102:Fibrinogeno
LAB1103:Temps de trombina
LAB1104:Temps de reptilase
LAB1105:PDF
LAB1106:Plaquetes citrat. Recompte
LAB1107:Antitrombina III
LAB1108:Anticoagulante tipo Lupus
LAB1109:Ac IgG anticardiolipina
LAB1110:Ac IgM anticardiolipina
LAB1111:Grup ABO
LAB1112:Rh (D)
LAB1118:Tiempo de protombina %
LAB1173:INR
LAB11ANDRO:11ß-OH-androsterona
LAB11ETIOO:11ß-OH-etiocolanolona
LAB11OXOO:11-oxo-etiocolanolona
LAB11THAO:Tetrahidro-11-dehidrocorticost
LAB1215:Urea,orina
LAB1225:Urat,orina recent
LAB1255:Magnesi,orina
LAB1300:Leucocitos recuento
LAB1301:Plaquetas recuento
LAB1302:VPM Volumen Plaquetario Medio
LAB1303:PDW Platelet Distribut Width
LAB1304:Plaquetòcrit
LAB1305:Hematias recuento
... (5048 more entries)
```

### dic_ou_loc (986 total entries, showing 50 samples)

```
HAH:HAH SALA HOSP. DOMICILIARIA
HAH3:HAH3 HOSPITALIZACIÓN DOMICILIARIA 3
HAH4:HAH4 HOSPITALIZACIÓN DOMICILIARIA 4
HAH5:HAH5 HOSPITALIZACIÓN DOMICILIARIA 5
HDOP:HAH PERSONAL HCB
HDOP2:HAH 2 PERSONAL HCB
HDOP3:HAH 3 PERSONAL HCB
HDOP4:HAH 4 PERSONAL HCB
HDOP5:HAH 5 PERSONAL HCB
HDSM:HDSM HOSPITALIZACIÓN DOMICILIARIA PSIQUIATRÍA
HDSMJ:HDSMJ HOSPITALIZACIÓN DOMICILIARIA PSIQUIATRÍA INFANTOJUVENIL
ELE1:SE NEONAT.MAT.UCI  ELE1
ELE2:SE NEONAT.MAT.UCI  ELE2
GEL2:GEL2 SALA G OBSTETRICIA MATERNITAT
GEL3:GEL3 SALA G OBSTETRICIA MATERNITAT
GLE1:GLE1 SALA NEONATOLOGÍA  MATERNITAT
GLE2:GLE2 SALA NEONATOLOGÍA MATERNITAT
GLL2:S. G OBST. MATER.  GLL2
GPO3:GPO3 GESTANTES COVID
ILE1:ILE1 SALA CUIDADOS INTERMEDIOS MATERNITAT
ILE2:SALA INTERMITJOS MATER ILE2
INPO:INPO SALA CUIDADOS INTENSIVOS OBSTETRICIA MATERNITAT
NEL2:NEL2 SALA G NIDOS OBSTETRICIA MATERNITAT
NEL3:NEL3 SALA G NIDOS OBSTETRICIA MATERNITAT
NNPO:NNPO SALA CUIDADOS INTENSIVOS NIDOS OBSTETRICIA MATERNITAT
CPT3:CPT3 SALA C PLATÓ PL.3
EHP40:EHP40 SALA E UGA - PLATÓ
EPT0:EPT0 CUIDADOS INTENSIVOS PLATÓ PL.0
GPT1:GPT1 SALA G PLATÓ PL.1
GPT2:GPT2 SALA G PLATÓ PL.2
... (936 more entries)
```

### dic_ou_med (287 total entries, showing 50 samples)

```
HP2:2ª planta Plató
HP3:3ª planta Plató
HP4:4ª planta Plató
DLC:ACTIVITAT PERSONAL DE LA CASA
ALE:AL.LERGOLOGIA
B-ANE:ANESTESIOLOGIA BCL
BANE:ANESTESIOLOGIA BCL
ANE:ANESTESIOLOGIA I REANIMACIO
H-PAT:ÁREA OP.HISTOPATOL.I PAT.CEL.
CORE:ÁREA OPERATIVA CORE
QUIR:ÁREA QUIRÚRGICA
E5915:ASSIR LES CORTS
ASM:AVALUACIO I SUPORT METODOLOGIC
HMT:BANC DE SANG
BCL:BARNACLÍNIC
B-BCL:BARNACLÍNIC GENERAL
BCLI:BARNACLÍNIC GENERAL
H-HOS:BCL HOSP. HCP
B-HOS:BCL HOSPITALIZACIÓN B047
LCE:BIOQ.GEN.MOL
BLQ:BLOQUEIG BO
CORBM:BM - GENERAL
CAR:CARDIOLOGIA
H-CAR:CARDIOLOGIA
B-CAR:CARDIOLOGIA BCL
BCAR:CARDIOLOGIA BCL
M-CAR:CARDIOLOGIA MATER REPLICA
CDBGR:CDB GENERAL
M-CIG:CIR. GRAL MATER REPLICA
B-HBP:CIR. HEP. I BILIO-PANCR. BCL
... (237 more entries)
```

### dic_rc (897 total entries, showing 50 samples)

```
ABDOMEN_DIST:Distensión abdominal
ABDO_NEO:Abdomen
ACR_DIS:Modelo de dispositivo
ACR_FIO2:FiO2 mezclador
ACR_MOD:Modalidad de terapia de oxigenación extracorpórea
ACR_O2Q:Flujo de oxígeno
ACR_OXIGENADOR:Tipo de módulo oxigenador
ACR_PART:Presión arterial postmembrana del módulo oxigenador
ACR_PVEN:Presión venosa premembra del módulo oxigenador
ACR_QS:Flujo de sangre
ACR_RPM:Revoluciones de la bomba centrífuga de sangre
ACR_SVO2:Saturación de oxígeno venosa antes del oxigenador (premembrana)
ACR_TEMP_ART:Temperatura arterial (postmembrana del oxigenador)
ACR_TEMP_VEN:Temperatura venosa (premembrana al oxigenador)
ACTIV_NEO:Actividad
AC_DIS:Dispositivo utilizado para la asistencia circulatoria
AC_MOD:Modalidad de asistencia circulatoria
AC_QS_DER:Flujo de sangre corazón derecho
AC_QS_IZQ:Flujo de sangre corazón izquierdo
AC_RPM_DER:Revoluciones bomba centrífuga corazón derecho
AC_RPM_IZQ:Revoluciones bomba centrífuga corazón izquierdo
ALDRETE:Escala de Aldrete modificada
ALT_NEU_NEO:Alteraciones neurológicas
ANTI_XA:Actividad anti factor X activado
APACHE_II:Valoración de gravedad del enfermo crítico
APTEM:Tromboelastometria con corrección de la fibrinolisis con aprotinina
AR_DIS:Dispositivo para realizar asistencia respiratoria extracorporea
AR_FIO2:FiO2 del mezclador
AR_MOD:Modalidad de terapia de oxigenación extracorpórea
AR_O2Q:Flujo de oxígeno
... (847 more entries)
```

### dic_rc_text (1634 total entries, showing 50 samples)

```
EDEMA_SACRO:0
FC_CVP:1
DOLOR_PIPP_NEO:10
FC_CVP:2
FC_CVP:3
FC_CVP:4
TCSR_REP_Q:5
TCSR_REP_Q:6
DOLOR_PIPP_NEO:7
DOLOR_PIPP_NEO:8
DOLOR_PIPP_NEO:9
EDEMA_SACRO:No Valorable
ABDOMEN_DIST:Normal
ABDOMEN_DIST:Normal-Distendido
ABDOMEN_DIST:Distendido
ABDO_NEO:Ausente
ABDO_NEO:Leve
ABDO_NEO:Moderada
ABDO_NEO:Grave
ABDO_NEO:Otro (especificar)
ACR_DIS:Levitronix CentriMag
ACR_DIS:Otro (especificar)
ACR_FIO2:Derecha
ACR_FIO2:Izquierda
ACR_FIO2:Biventricular
ACR_FIO2:Otro (especificar)
ACR_QS:CardioHelp
ACR_QS:Otro (especificar)
ACR_QS:Rotaflow
ACR_QS:Levitronix CentriMag
... (1584 more entries)
```

---

## Query Examples

### Example 1: Patients with specific diagnosis

```sql
WITH diagnosis_search AS (
    SELECT DISTINCT patient_ref, episode_ref, diag_descr
    FROM g_diagnostics
    WHERE diag_descr LIKE '%diabetes%'
)
SELECT * FROM diagnosis_search;
```

### Example 2: Laboratory results in date range

```sql
WITH lab_results AS (
    SELECT 
        patient_ref,
        episode_ref,
        lab_sap_ref,
        lab_descr,
        result_num,
        units,
        extrac_date
    FROM g_labs
    WHERE extrac_date BETWEEN '2024-01-01' AND '2024-12-31'
        AND lab_sap_ref = 'LAB110'  -- Urea
)
SELECT * FROM lab_results
ORDER BY patient_ref, extrac_date;
```

### Example 3: Patient demographics with episodes

```sql
WITH patient_episodes AS (
    SELECT DISTINCT 
        e.patient_ref, 
        e.episode_ref,
        e.episode_type_ref,
        e.start_date,
        e.end_date
    FROM g_episodes e
),
patient_info AS (
    SELECT 
        d.patient_ref,
        d.birth_date,
        d.sex,
        d.natio_descr
    FROM g_demographics d
)
SELECT 
    pe.*,
    pi.birth_date,
    pi.sex,
    pi.natio_descr
FROM patient_episodes pe
JOIN patient_info pi ON pe.patient_ref = pi.patient_ref;
```

### Example 4: Drug administrations with prescriptions

```sql
WITH prescriptions AS (
    SELECT 
        patient_ref,
        episode_ref,
        treatment_ref,
        drug_ref,
        drug_descr,
        atc_ref,
        dose,
        unit
    FROM g_prescriptions
    WHERE atc_ref LIKE 'J01%'  -- Antibacterials
),
administrations AS (
    SELECT 
        patient_ref,
        episode_ref,
        treatment_ref,
        administration_date,
        quantity,
        quantity_unit
    FROM g_administrations
)
SELECT 
    p.*,
    a.administration_date,
    a.quantity
FROM prescriptions p
JOIN administrations a 
    ON p.patient_ref = a.patient_ref 
    AND p.treatment_ref = a.treatment_ref;
```

### Example 5: Microbiology with antibiograms

```sql
WITH micro_positive AS (
    SELECT 
        patient_ref,
        episode_ref,
        extrac_date,
        micro_ref,
        micro_descr,
        antibiogram_ref
    FROM g_micro
    WHERE positive = 'X'
),
antibiogram_results AS (
    SELECT 
        patient_ref,
        antibiogram_ref,
        antibiotic_descr,
        sensitivity
    FROM g_antibiograms
)
SELECT 
    mp.*,
    ar.antibiotic_descr,
    ar.sensitivity
FROM micro_positive mp
JOIN antibiogram_results ar 
    ON mp.patient_ref = ar.patient_ref 
    AND mp.antibiogram_ref = ar.antibiogram_ref;
```
