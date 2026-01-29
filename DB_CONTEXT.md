# DataNex Database Schema - LLM Context

**Purpose**: Comprehensive reference for SQL query generation from natural language

## Instructions for LLM

You are a SQL query assistant specialized in DataNex (Hospital Clinic database). Use MySQL MariaDB dialect.
Your task: Create SQL queries from natural language questions or generate full Python analytical pipelines to do the task described. If I ask you for the SQL just give that with the following rules. 

### Process:
1. Confirm you understand the DataNex schema
2. Request the natural language question
3. Generate optimized SQL query using CTEs when appropriate
4. Present the final query ready for copy-paste

### Rules:

#### General Query Rules:
- Always explain how the query works before showing the code
- Use Common Table Expressions (CTEs) for optimization
- Optimize operations on large tables (`g_labs` and `g_rc`) by filtering early in CTEs
- Do not explain optimizations in your response, just implement them

#### Searching by Reference Fields:
- **Default behavior**: Search using `_ref` fields (e.g., `lab_sap_ref`, `ou_med_ref`)
- Retrieve `_ref` values from corresponding `dic_` tables when needed

#### Searching Diagnoses (g_diagnostics table):
1. **Primary method**: Search by `code` field using ICD-9 or ICD-10 codes
   - Use your knowledge of ICD codes or search online for the appropriate codes
   - Always use `LIKE '%code%'` pattern matching (e.g., `code LIKE '%50.5%'` for liver transplant)
   
2. **Alternative method**: Search by `diag_descr` field using text patterns
   - Use when you don't know the specific ICD code
   - Always use `LIKE '%text%'` pattern matching (e.g., `diag_descr LIKE '%diabetes%'`)

3. **NEVER use**: 
   - The `catalog` field (unless explicitly requested by the user)
   - The `diag_ref` field to join with `dic_diagnostic` (they are independent systems)

#### Searching Procedures (g_procedures table):
1. **Primary method**: Search by `code` field using ICD-9 or ICD-10 procedure codes
   - Use your knowledge of procedure codes or search online for the appropriate codes
   - Always use `LIKE '%code%'` pattern matching (e.g., `code LIKE '50.5%'` for liver transplant procedures)
   
2. **Alternative method**: Search by `descr` field using text patterns
   - Use when you don't know the specific procedure code
   - Always use `LIKE '%text%'` pattern matching (e.g., `descr LIKE '%transplant%'`)

3. **NEVER use**: The `catalog` field (unless explicitly requested by the user)

#### Handling Duplicate Codes:
- Be aware that the same diagnosis or procedure may appear multiple times in an episode
- ICD-9 and ICD-10 codes for the same condition can coexist in the same episode
- When counting:
  - Use COUNT(*) for total occurrences
  - Use COUNT(DISTINCT episode_ref) for unique episodes
  - Use COUNT(DISTINCT patient_ref) for unique patients
- When unsure about duplicate handling, ask the user for clarification

#### Joining tables 
- When joining events (labs, drugs) to episodes, ALWAYS filter by episode_ref. Do NOT rely solely on dates unless episode_ref is not present in the table (like in g_rc) or is null.

## Database Overview

DataNex is a database made up of several tables. Keeping information in different tables allows us to reduce storage space and group that information by topic.

The central tables in DataNex are **g_episodes**, **g_care_levels** and **g_movements**:

- **Episodes**: Medical events experienced by a patient (an admission planned or from the emergency department, an assessment in the emergency department, a set of visits for a medical specialty in outpatients, etc.). Stored in `g_episodes`.
- **Care levels**: Intensity of healthcare needs that a patient requires. Inside an episode, a care level groups different movements that share the same intensity of healthcare needs. Stored in `g_care_levels`.
- **Movements**: Changes in the patient's location (e.g., transfer from room A to room B). Patient discharge and exitus are also considered movements. Stored in `g_movements`.

These three central tables follow a hierarchy: **episodes → care_levels → movements**

### Episode Types
Only EM (emergency), HAH (hospital at home) and all HOSP (HOSP, HOSP_RN and HOSP_IQ) episode types have care levels and movements.

### Care Level Identification
For the same patient, each new care level is uniquely identified by a number. If in the same admission the patient goes from level WARD to level ICU and then to level WARD, they would have three different numeric identifiers, one for each new level.

---

## Database Views (All Tables)

---

### g_episodes

Contains all hospital episodes for each patient. An episode represents a medical event: an admission, an emergency assessment, outpatient visits, etc.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| episode_ref | INT | PK | Pseudonymized number that identifies an episode |
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_type_ref | VARCHAR(8) | FK | Episode typology: **AM** (outpatient episode), **EM** (emergency episode), **DON** (Donor), **HOSP_IQ** (hospitalization episode for surgery), **HOSP_RN** (hospitalization episode for healthy newborn), **HOSP** (hospitalization episode different from HOSP_IQ and HOSP_RN), **EXT_SAMP** (external sample), **HAH** (hospital at home or home hospitalization) |
| start_date | DATETIME | | Start date and time of the episode |
| end_date | DATETIME | | End date and time of the episode. In AM episodes (outpatient episodes), the end_date does not signify the end of the episode but rather the date of the patient's last visit |
| load_date | DATETIME | | Date of update |

---

### g_care_levels

Contains the care levels for each episode. Care level refers to the intensity of healthcare needs that a patient requires. Only EM, HAH and all HOSP (HOSP, HOSP_RN and HOSP_IQ) episode types have care levels.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| care_level_ref | INT | PK | Unique identifier that groups consecutive care levels (ICU, WARD, etc.) if they belong to the same level |
| start_date | DATETIME | | Start date and time of the admission |
| end_date | DATETIME | | End date and time of the admission |
| load_date | DATETIME | | Date of update |
| care_level_type_ref | VARCHAR(16) | FK | Care level type: **WARD** (conventional hospitalization), **ICU** (intensive care unit), **EM** (emergency episode), **SPEC** (special episode), **HAH** (hospital at home or home hospitalization), **PEND. CLAS** (pending classification), **SHORT** (short stay) |

---

### g_movements

Contains the movements for each care level. Movements are changes in the patient's location. Patient discharge and exitus are also considered movements. All movements have a `care_level_ref`. Only EM, HAH and all HOSP (HOSP, HOSP_RN and HOSP_IQ) episode types have movements.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| start_date | DATETIME | | Date and time of the start of the movement |
| end_date | DATETIME | | Date and time of the end of the movement |
| place_ref | INT | | Encrypted reference for the patient's room and bed |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| ou_med_descr | VARCHAR(32) | | Description of the medical organizational unit reference |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference |
| ou_loc_descr | VARCHAR(32) | | Description of the physical hospitalization unit reference |
| care_level_type_ref | VARCHAR(8) | FK | Care level (ICU, HAH, etc.) |
| facility | VARCHAR(32) | | Description of the facility reference |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (intensive care unit, conventional hospitalization, etc.) if they are consecutive and belong to the same level |

---

### g_demographics

Contains demographic information for each patient.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | PK | Pseudonymized number that identifies a patient |
| birth_date | DATE | | Date of birth |
| sex | INT | | Sex: **-1** (not reported in SAP), **1** (male), **2** (female), **3** (other) |
| natio_ref | VARCHAR(8) | FK | Reference code for nationality |
| natio_descr | VARCHAR(512) | | Description of the country code according to ISO:3 |
| health_area | VARCHAR | | Health area |
| postcode | VARCHAR | | Postal code |
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
| mot_type | VARCHAR(45) | | Indicates if it is the starting motive (**ST**) or the ending motive (**END**) of the episode |
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
| catalog | INT | | Catalog to which the 'code' belongs: **1** (CIE9 MC, until 2017), **2** (MDC), **3** (CIE9 Emergencies), **4** (ACR), **5** (SNOMED), **7** (MDC-AP), **8** (SNOMEDCT), **9** (Subset ANP SNOMED CT), **10** (Subset ANP SNOMED ID), **11** (CIE9 in Outpatients), **12** (CIE10 MC), **13** (CIE10 Outpatients) |
| code | VARCHAR(8) | | ICD-9 or ICD-10 code for each diagnosis |
| diag_descr | VARCHAR(32) | | Description of the diagnosis |
| class | VARCHAR(2) | | Diagnosis class: **P** (primary diagnosis validated by documentalist), **S** (secondary diagnosis validated by documentalist), **H** (diagnosis not validated by documentalist), **E** (emergency diagnosis), **A** (outpatient diagnosis). A hospitalization episode has only one P diagnosis and zero or more S or H diagnoses |
| poa | VARCHAR(2) | | Present on Admission indicator: **Y** (present at admission - comorbidity), **N** (not present at admission - complication), **U** (unknown - insufficient documentation), **W** (clinically undetermined), **E** (exempt), **-** (unreported - documentalist has not registered the diagnostic code) |
| load_date | DATETIME | | Date of update |

> ⚠️ **Link with dic_diagnostic**: Do NOT use `diag_ref` to link with the dictionary. Search directly by `diag_descr` in this table when looking for specific diagnostics.

---

### g_diagnostic_related_groups

Contains the Diagnosis-Related-Groups (DRG). DRG is a concept used to categorize hospital cases into groups according to diagnosis, procedures, age, comorbidities and other factors. These DRG are used mainly for administrative purposes, billing and resource allocation. DRG are further classified in Major Diagnostic Categories (MDC).

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| weight | FLOAT | | DRG cost weight - relative resource consumption for that group compared to others |
| drg_ref | INT | FK | DRG (Diagnosis-Related Group) reference |
| severity_ref | VARCHAR(2) | FK | SOI (Severity of Illness) reference - metric to evaluate how sick a patient is |
| severity_descr | VARCHAR(128) | | Description of the SOI reference |
| mortality_risk_ref | VARCHAR(2) | FK | ROM (Risk of Mortality) reference - metric to evaluate likelihood of patient dying |
| mortality_risk_descr | VARCHAR(128) | | Description of the ROM reference |
| mdc_ref | INT | FK | MDC (Major Diagnostic Categories) reference - broad categories used to group DRG based on similar clinical conditions or body systems |
| load_date | DATETIME | | Date of update |

---

### g_health_issues

Contains information about all health problems related to a patient. Health problems are SNOMED-CT (Systematized Nomenclature of Medicine Clinical Terms) codified health problems that a patient may present. SNOMED is a comprehensive multilingual clinical terminology used worldwide in healthcare. Those health problems are codified by the doctors taking care of the patients, thus expanding and enriching the codification possibilities.

Health problems have a start date, indicating when they were first recorded by the clinician, and may also have an end date, marking when the clinician determined the health problem was no longer active.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| snomed_ref | INT | | SNOMED code for a health problem |
| snomed_descr | VARCHAR(255) | | Description of the SNOMED code |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| start_date | DATE | | Start date of the health problem |
| end_date | DATE | | End date of the health problem (not mandatory) |
| end_motive | INT | | Reason for the change (not mandatory) |
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
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit |
| care_level_ref | INT | FK | Unique identifier that groups care levels (ICU, WARD, etc.) if they are consecutive and belong to the same level; the care_level_ref is absent if the lab test is requested after the end of the episode in EM, HOSP and HAH episodes |
| lab_sap_ref | VARCHAR(16) | FK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(32) | | lab_sap_ref description |
| result_num | FLOAT | | Numerical result of the laboratory test |
| result_txt | VARCHAR(128) | | Text result from the DataNex laboratory reference |
| units | VARCHAR(32) | | Units |
| lab_group_ref | INT | | Reference for grouped laboratory parameters |

---

### g_rc

Contains the clinical records for each episode. Currently, the fields `episode_ref` and `care_level_ref` may be empty in some records but they will be filled soon.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| result_date | DATETIME | | Date and time of the measurement |
| meas_type_ref | VARCHAR(1) | | Measurement type: **0** (manual input), **1** (from machine, result not validated), **2** (from machine, result validated) |
| load_date | DATETIME | | Date of update |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit; filled if the clinical registry is manually collected, empty if automatically collected |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit; filled if the clinical registry is manually collected, empty if automatically collected |
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| rc_descr | VARCHAR(32) | | Description of the SAP clinical record reference |
| result_num | FLOAT | | Numerical result of the clinical record |
| result_txt | VARCHAR(128) | | Text result from the DataNex clinical record reference |
| units | VARCHAR(8) | | Units |
| care_level_ref | INT | FK | Unique identifier that groups care levels (intensive care unit, conventional hospitalization, etc.) if they are consecutive and belong to the same level |

> 📖 **Dictionary for result_txt**: Check the [rc_result_txt dictionary](https://dsc-clinic.gitlab.io/datascope/rc_result_txt_dic.html)

---

### g_micro

Contains the microbiology results for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| res_date | DATETIME | | Date and time the result was obtained |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit |
| mue_ref | VARCHAR | | Code that identifies the type or origin of the sample |
| mue_descr | VARCHAR | | Description of the type or origin of the sample; provides a general classification of the sample |
| method_descr | VARCHAR | | Detailed description of the sample itself or the method used to process the sample; includes specific procedures and tests performed |
| positive | VARCHAR | | 'X' means that a microorganism has been detected in the sample |
| antibiogram_ref | INT | FK | Unique identifier for the antibiogram |
| micro_ref | VARCHAR | | Code that identifies the microorganism |
| micro_descr | VARCHAR | | Scientific name of the microorganism |
| num_micro | INT | | Number that starts at 1 for the first identified microbe and increments by 1 for each newly identified microbe in the sample |
| result_text | VARCHAR(128) | | Text result from the microbiology sample |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (intensive care unit, conventional hospitalization, etc.) if they are consecutive and belong to the same level |

---

### g_antibiograms

Contains the antibiograms for each episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| extrac_date | DATETIME | | Date and time the sample was extracted |
| result_date | DATETIME | | Date and time the result was obtained |
| sample_ref | VARCHAR | | Code that identifies the type or origin of the sample |
| sample_descr | VARCHAR | | Description of the type or origin of the sample; provides a general classification of the sample |
| antibiogram_ref | INT | | Unique identifier for the antibiogram |
| micro_ref | VARCHAR | | Code that identifies the microorganism |
| micro_descr | VARCHAR | | Scientific name of the microorganism |
| antibiotic_ref | VARCHAR | | Code of the antibiotic used in the sensitivity testing |
| antibiotic_descr | VARCHAR | | Full name of the antibiotic |
| result | VARCHAR | | Result of the antibiotic sensitivity test; represents the minimum inhibitory concentration (MIC) required to inhibit the growth of the bacteria |
| sensitivity | VARCHAR | | Sensitivity (**S**) or resistance (**R**) of the bacteria to the antibiotic tested |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (intensive care unit, conventional hospitalization, etc.) if they are consecutive and belong to the same level |

---

### g_prescriptions

Contains the prescribed medical products (pharmaceuticals and medical devices) for each episode. A treatment prescription (identified by `treatment_ref`) may be composed by one or more medical products, so this table will show as many rows as prescribed medical products per treatment prescription.

The `treatment_ref` field serves as a foreign key that links the `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| prn | VARCHAR | | Null value or "X"; the "X" indicates that this drug is administered only if needed |
| freq_ref | VARCHAR | FK | Administration frequency code |
| phform_ref | INT | FK | Pharmaceutical form identifier |
| phform_descr | VARCHAR | | Description of phform_ref |
| prescr_env_ref | INT | FK | Healthcare setting where the prescription was generated (see complementary descriptions) |
| adm_route_ref | INT | FK | Administration route reference |
| route_descr | VARCHAR | | Description of adm_route_ref |
| atc_ref | VARCHAR | | ATC code |
| atc_descr | VARCHAR | | Description of the ATC code |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit |
| start_drug_date | DATETIME | | Start date of prescription validity |
| end_drug_date | DATETIME | | End date of prescription validity |
| load_date | DATETIME | | Date of update |
| drug_ref | VARCHAR | FK | Medical product identifier |
| drug_descr | VARCHAR | | Description of the drug_ref field |
| enum | INT | | Role of the drug in the prescription (see complementary descriptions where `enum` equals `drug_type_ref`) |
| dose | INT | | Prescribed dose |
| unit | VARCHAR | FK | Dose unit (see complementary descriptions) |
| care_level_ref | INT | FK | Unique identifier that groups care levels (ICU, WARD, etc.) if they are consecutive and belong to the same level |

> 📖 **Complementary descriptions**: See [Prescriptions complementary descriptions](https://gitlab.com/dsc-clinic/datascope/-/wikis/Prescriptions#complementary-descriptions) for details on `prescr_env_ref`, `enum`/`drug_type_ref`, and `unit`.

---

### g_administrations

Contains the administered pharmaceuticals (drugs) for each episode. The `treatment_ref` field serves as a foreign key that links the `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription |
| administration_date | DATE | | Date of administration |
| route_ref | INT | FK | Administration route reference |
| route_descr | VARCHAR | | Description of route_ref |
| prn | VARCHAR | | Null value or "X"; the "X" indicates that this drug is administered only if needed |
| given | VARCHAR | | Null value or "X"; the "X" indicates that this drug has not been administered |
| not_given_reason_ref | INT | | Number that indicates the reason for non-administration |
| drug_ref | VARCHAR | FK | Medical product identifier |
| drug_descr | VARCHAR | | Description of the drug_ref field |
| atc_ref | VARCHAR | | ATC code |
| atc_descr | VARCHAR | | Description of the ATC code |
| enum | INT | | Role of the drug in the prescription (see complementary descriptions where `enum` equals `drug_type_ref`) |
| quantity | INT | | Dose actually administered to the patient |
| quantity_planing | INT | | Planned dose |
| quantity_unit | VARCHAR | FK | Dose unit (see complementary descriptions) |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (ICU, WARD, etc.) if they are consecutive and belong to the same level |

> 📖 **Complementary descriptions**: See [Prescriptions complementary descriptions](https://gitlab.com/dsc-clinic/datascope/-/wikis/Prescriptions#complementary-descriptions) for details on `enum`/`drug_type_ref` and `quantity_unit`.

---

### g_perfusions

Contains data about the administered drug perfusions for each episode. The `treatment_ref` field serves as a foreign key that links the `g_prescriptions`, `g_administrations` and `g_perfusions` tables.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| treatment_ref | INT | | Code that identifies a treatment prescription. Points to the `treatment_ref` in the `g_administrations` and `g_prescriptions` tables |
| infusion_rate | INT | | Rate in ml/h |
| rate_change_counter | INT | | Perfusion rate change counter: starts at 1 (first rate) and increments by one unit with each change (each new rate) |
| start_date | DATETIME | | Start date of the perfusion |
| end_date | DATETIME | | End date of the perfusion |
| load_date | DATETIME | | Date of update |
| care_level_ref | INT | FK | Unique identifier that groups care levels (ICU, WARD, etc.) if they are consecutive and belong to the same level |

---

### g_encounters

An encounter refers to a punctual event in which detailed information is recorded about a medical interaction or procedure involving a patient (for instance a chest radiograph, an outpatient visit, etc.).

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| date | DATETIME | | Date of the encounter event |
| load_date | DATETIME | | Update date |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference; points to the ou_med_dic table |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference; points to the ou_loc_dic table |
| encounter_type | VARCHAR(8) | FK | Encounter type (see dictionary below) |
| agen_ref | VARCHAR | FK | Code that identifies the encounter |
| act_type_ref | VARCHAR(8) | FK | Activity type |

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
| VS | Vista sucesiva |
| VU | Vista URPA / Vista urgencias |

> ⚠️ **Note**: The dictionaries for `agen_ref` and `act_type_ref` fields will be available in future updates.

---

### g_procedures

Contains all procedures per episode.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit |
| catalog | VARCHAR(10) | | Catalog: **1** (ICD9), **12** (ICD10) |
| code | VARCHAR(10) | | Procedure code |
| descr | VARCHAR(255) | | Procedure description |
| text | VARCHAR(255) | | Details about the procedure |
| place | VARCHAR(2) | | Location of the procedure: **1** (Bloque quirúrgico), **2** (Gabinete diagnóstico y terapéutico), **3** (Cirugía menor), **4** (Radiología intervencionista o medicina nuclear), **5** (Sala de no intervención), **6** (Bloque obstétrico), **EX** (Procedimiento externo) |
| class | VARCHAR(2) | | Procedure class: **P** (primary procedure), **S** (secondary procedure) |
| start_date | DATETIME | | Start date of the procedure |
| load_date | DATETIME | | Date and time of update |

---

### g_provisions

Provisions are healthcare benefits. They are usually categorized into three levels: each level 1 class contains its own level 2 classes, and each level 2 class contains its own level 3 classes. However, this structure is not mandatory, so some provisions may not have any levels at all. In any case, each provision always has a code (`prov_ref`) that identifies it.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_med_ref_order | VARCHAR(8) | FK | Medical organizational unit that requests the provision; points to the dic_ou_med table |
| prov_ref | VARCHAR(32) | | Code that identifies the healthcare provision |
| prov_descr | VARCHAR(255) | | Description of the provision code |
| level_1_ref | VARCHAR(16) | | Level 1 code; may end with '_inferido', indicating this level was not recorded in SAP but has been inferred from the context in SAP tables |
| level_1_descr | VARCHAR(45) | | Level 1 code description |
| level_2_ref | VARCHAR(3) | | Level 2 code |
| level_2_descr | VARCHAR(55) | | Level 2 code description |
| level_3_ref | VARCHAR(3) | | Level 3 code |
| level_3_descr | VARCHAR(50) | | Level 3 code description |
| category | INT | | Class of the provision: **2** (generic provisions), **6** (imaging diagnostic provisions) |
| start_date | DATETIME | | Start date of the provision |
| end_date | DATETIME | | End date of the provision |
| accession_number | VARCHAR(10) | PK | Unique identifier for each patient provision. For example, if a patient undergoes two ECGs on the same day, this will result in two separate provisions, each with its own accession number. This field links to the XNAT data repository |
| ou_med_ref_exec | VARCHAR(8) | FK | Medical organizational unit that executes the provision; points to the dic_ou_med table |
| start_date_plan | DATETIME | | Scheduled start date of the provision |
| end_date_plan | DATETIME | | Scheduled end date of the provision |

---

### g_dynamic_forms

Dynamic forms collect clinical data in a structured manner. All of this data is recorded in the `g_dynamic_forms` table, where each dynamic form and its characteristics appear as many times as the form was saved in SAP. This is reflected in the `form_date` variable, which stores the date or dates when the form was saved.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| status | VARCHAR(3) | | Record status: **CO** (completed), **EC** (in process) |
| form_ref | VARCHAR(8) | | Form name identifier |
| form_descr | VARCHAR | | Form description |
| tab_ref | VARCHAR(10) | | Form tab (group) identifier |
| tab_descr | VARCHAR | | Tab description |
| section_ref | VARCHAR(10) | | Form section (parameter) identifier |
| section_descr | VARCHAR | | Section description |
| type_ref | VARCHAR(8) | | Form question (characteristic) identifier |
| type_descr | VARCHAR | | Characteristic description |
| class_ref | VARCHAR(3) | | Assessment class: **CC** (structured clinical course forms), **EF** (physical examination forms), **ES** (scale forms), **RG** (record or report forms), **RE** (special record forms), **VA** (assessment forms), **TS** (social work forms) |
| class_descr | VARCHAR | | Class description |
| value_num | FLOAT | | Numeric value inserted |
| value_text | VARCHAR(255) | | Text value inserted |
| value_date | DATETIME | | Datetime value inserted |
| form_date | DATETIME | | Date when the form was saved |
| load_date | DATETIME | | Date of update |

**Dynamic forms structure:**

The components of dynamic forms follow this hierarchy:
- **Form** (form_ref, form_descr): The main container
- **Tab** (tab_ref, tab_descr): Groups within a form
- **Section** (section_ref, section_descr): Parameters within a tab
- **Type** (type_ref, type_descr): Questions/characteristics within a section

---

### g_special_records

Special records (also known as nursing records) are a specific type of dynamic form completed by nurses to collect clinical data in a structured manner. All of this data is recorded in the `g_special_records` table, where each special record appears as many times as it was saved in SAP.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_loc_ref | VARCHAR(8) | FK | Physical hospitalization unit reference |
| ou_med_ref | VARCHAR(8) | FK | Medical organizational unit reference |
| status | VARCHAR(3) | | Record status: **CO** (completed), **EC** (in process) |
| form_ref | VARCHAR(8) | | Form name identifier |
| form_descr | VARCHAR | | Form description |
| tab_ref | VARCHAR(10) | | Form tab (group) identifier |
| tab_descr | VARCHAR | | Tab description |
| section_ref | VARCHAR(10) | | Form section (parameter) identifier |
| section_descr | VARCHAR | | Section description |
| type_ref | VARCHAR(8) | | Form question (characteristic) identifier |
| type_descr | VARCHAR | | Characteristic description |
| class_ref | VARCHAR(3) | | Assessment class: **RE** (special record forms) |
| class_descr | VARCHAR | | Class description |
| value_num | FLOAT | | Numeric value inserted |
| value_text | VARCHAR(255) | | Text value inserted |
| value_date | DATETIME | | Datetime value inserted |
| form_date | DATETIME | | Date when the form was saved |
| load_date | DATETIME | | Date of update |

---

### g_tags

Tags are labels that some clinicians use to identify groups of patients. The exact meaning of each tag and its maintenance depends on the tag administrator.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| tag_ref | INT | FK | Reference identifying the tag |
| tag_group | VARCHAR | | Tag group |
| tag_subgroup | VARCHAR | | Tag subgroup |
| tag_descr | VARCHAR | | Description of the tag reference |
| inactive_atr | INT | | Inactivity: **0** (off), **1** (on) |
| start_date | DATETIME | | Start date and time of the tag |
| end_date | DATETIME | | End date and time of the tag |
| load_date | DATETIME | | Update date and time |

---

### g_surgery

Contains general information about the surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| mov_ref | INT | FK | Reference that joins the surgery with its movement |
| ou_med_ref | VARCHAR | FK | Medical organizational unit reference |
| ou_loc_ref | VARCHAR | FK | Physical hospitalization unit reference |
| operating_room | VARCHAR | | Assigned operating room |
| start_date | DATETIME | | When the surgery starts |
| end_date | DATETIME | | When the surgery ends |
| surgery_ref | INT | FK | Number that identifies a surgery; links to other Surgery tables |
| surgery_code | VARCHAR | | Standard code for the surgery. Local code named Q codes (e.g., Q01972 for "injeccio intravitria") |
| surgery_code_descr | VARCHAR | | Surgery code description |

---

### g_surgery_team

Contains information about surgical tasks performed during surgical procedures.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| surgery_ref | INT | FK | Number that identifies a surgery; links to other Surgery tables |
| task_ref | VARCHAR | | Code that identifies the surgical task |
| task_descr | VARCHAR | | Description of the surgical task |
| employee | INT | | Employee who performed the task |

---

### g_surgery_timestamps

Stores the timestamps of surgical events for each surgical procedure.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| event_label | VARCHAR | | Surgical event code |
| event_descr | VARCHAR | | Description of the surgical event |
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
| waiting_list | VARCHAR | | Name of the waiting list |
| planned_date | DATETIME | | Scheduled date and time of the surgical intervention |
| proc_ref | VARCHAR | FK | Procedure code |
| registration_date | DATETIME | | Date and time when the patient was registered on the waiting list |
| requesting_physician | INT | | Physician who requested the surgery |
| priority | INT | | Priority assigned to the patient in the waiting list |

---

### g_pathology_sample

Contains all Pathology samples and their descriptions for each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR | FK | Sample reference (a case holds one or more samples) |
| sample_descr | VARCHAR | | Sample description |
| validated_by | INT | | Employee who validated the sample |

---

### g_pathology_diagnostic

Contains all Pathology diagnoses associated with each case.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| case_ref | VARCHAR | FK | Case reference |
| case_date | DATETIME | | Date of the case |
| sample_ref | VARCHAR | FK | Sample reference (a case holds one or more samples) |
| diag_type | VARCHAR | | Type of diagnosis |
| diag_code | INT | | Diagnosis code |
| diag_date | DATETIME | | Diagnosis date |
| diag_descr | VARCHAR | | Diagnosis description |
| validated_by | INT | | Employee who validated the sample |

---

## Dictionary Tables

---

### dic_diagnostic

Diagnosis dictionary for searching diagnoses by reference code.

> ⚠️ **IMPORTANT**: The `diag_ref` field in this table does NOT match the `diag_ref` in `g_diagnostics`. They are independent identification systems. Additionally, this dictionary does not cover all catalogs used in clinical practice. To search for diagnoses, search directly by `diag_descr` in `g_diagnostics`.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| diag_ref | INT | PK | Diagnosis reference number (internal ID, not linked to g_diagnostics.diag_ref) |
| catalog | INT | | Catalog code |
| code | VARCHAR(45) | | ICD code (use with catalog to link to g_diagnostics) |
| diag_descr | VARCHAR(256) | | Diagnosis description |

---

### dic_lab

Laboratory parameters dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| lab_sap_ref | VARCHAR(16) | PK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | Laboratory parameter description |
| units | VARCHAR(32) | | Units |
| lab_ref | INT | | Laboratory reference |

---

### dic_ou_loc

Physical hospitalization units dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_loc_ref | VARCHAR(16) | PK | Physical hospitalization unit reference |
| ou_loc_descr | VARCHAR(256) | | Description |
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
| units | VARCHAR(32) | | Units |
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

### Primary Identifiers
- `patient_ref`: Links most tables (primary patient identifier)
- `episode_ref`: Links to hospital episodes

### Hierarchical Relationships
- Tables follow hierarchy: **episodes → care_levels → movements**
- `care_level_ref`: Groups consecutive care levels (ICU, WARD, etc.) if they belong to the same level

### Treatment Chain
- `treatment_ref`: Links `g_prescriptions`, `g_administrations`, and `g_perfusions`

### Surgery Chain
- `surgery_ref`: Links `g_surgery`, `g_surgery_team`, and `g_surgery_timestamps`

### Pathology Chain
- `case_ref` and `sample_ref`: Link `g_pathology_sample` and `g_pathology_diagnostic`

### Microbiology Chain
- `antibiogram_ref`: Links `g_micro` and `g_antibiograms`

---

## Dictionaries (ref:descr format)

**Usage**: Use 'descr' to find corresponding 'ref' code for searches.

### dic_diagnostic (sample entries)

```
6000001:(osteo)artrosis erosiva
6000002:(osteo)artrosis primaria generalizada
6000025:Abdomen agudo
6000026:Abertura artificial, no especificada
6000027:Abortadora habitual
...
```

### dic_lab (sample entries)

```
LAB110:Urea
LAB1100:Tiempo de protombina segundos
LAB1101:Tiempo de tromboplastina parcial
LAB1102:Fibrinogeno
LAB1111:Grup ABO
LAB1112:Rh (D)
LAB1173:INR
LAB1300:Leucocitos recuento
LAB1301:Plaquetas recuento
...
```

### dic_ou_loc (sample entries)

```
HAH:HAH SALA HOSP. DOMICILIARIA
ICU:CUIDADOS INTENSIVOS
WARD:HOSPITALIZACIÓN CONVENCIONAL
ELE1:SE NEONAT.MAT.UCI ELE1
EPT0:EPT0 CUIDADOS INTENSIVOS PLATÓ PL.0
...
```

### dic_ou_med (sample entries)

```
ANE:ANESTESIOLOGIA I REANIMACIO
CAR:CARDIOLOGIA
HMT:BANC DE SANG
BCL:BARNACLÍNIC
NEU:NEUROLOGIA
...
```

### dic_rc (sample entries)

```
ABDOMEN_DIST:Distensión abdominal
APACHE_II:Valoración de gravedad del enfermo crítico
FC:Frecuencia cardíaca
TAS:Tensión arterial sistólica
TAD:Tensión arterial diastólica
TEMP:Temperatura
...
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
    WHERE atc_ref LIKE '%J01%'  -- Antibacterials
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

### Example 6: Multiple transplant types by year with pivot (ADVANCED)
```sql
-- Cuenta pacientes únicos trasplantados por tipo y año, con años como columnas
SELECT 
  tipo_trasplante,
  SUM(CASE WHEN año = 2015 THEN total_trasplantes ELSE 0 END) AS '2015',
  SUM(CASE WHEN año = 2016 THEN total_trasplantes ELSE 0 END) AS '2016',
  SUM(CASE WHEN año = 2017 THEN total_trasplantes ELSE 0 END) AS '2017',
  SUM(CASE WHEN año = 2018 THEN total_trasplantes ELSE 0 END) AS '2018',
  SUM(CASE WHEN año = 2019 THEN total_trasplantes ELSE 0 END) AS '2019',
  SUM(CASE WHEN año = 2020 THEN total_trasplantes ELSE 0 END) AS '2020',
  SUM(CASE WHEN año = 2021 THEN total_trasplantes ELSE 0 END) AS '2021',
  SUM(CASE WHEN año = 2022 THEN total_trasplantes ELSE 0 END) AS '2022',
  SUM(CASE WHEN año = 2023 THEN total_trasplantes ELSE 0 END) AS '2023',
  SUM(CASE WHEN año = 2024 THEN total_trasplantes ELSE 0 END) AS '2024'
FROM (
  SELECT 
    'Trasplante cardíaco' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND (code LIKE '37.51%' OR code LIKE '02YA%')
  GROUP BY YEAR(start_date)
  
  UNION ALL
  
  SELECT 
    'Trasplante de córnea' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND code LIKE '11.6%'
  GROUP BY YEAR(start_date)
  
  UNION ALL
  
  SELECT 
    'Trasplante de médula ósea/células madre' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND code LIKE '41.0%'
  GROUP BY YEAR(start_date)
  
  UNION ALL
  
  SELECT 
    'Trasplante de páncreas' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND (code LIKE '52.8%' OR code LIKE '0FYG%')
  GROUP BY YEAR(start_date)
  
  UNION ALL
  
  SELECT 
    'Trasplante hepático' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND (code LIKE '50.5%' OR code LIKE '0FY0%')
  GROUP BY YEAR(start_date)
  
  UNION ALL
  
  SELECT 
    'Trasplante renal' AS tipo_trasplante,
    YEAR(start_date) AS año,
    COUNT(DISTINCT patient_ref) AS total_trasplantes
  FROM g_procedures
  WHERE start_date >= '2015-01-01' 
    AND start_date < '2025-01-01'
    AND (code LIKE '55.6%' OR code LIKE '0TY0%' OR code LIKE '0TY1%')
  GROUP BY YEAR(start_date)
) AS datos
GROUP BY tipo_trasplante
ORDER BY tipo_trasplante;
```

### Example 7: Surgical procedures with team and timestamps
```sql
WITH surgeries AS (
    SELECT 
        s.patient_ref,
        s.episode_ref,
        s.surgery_ref,
        s.surgery_code,
        s.surgery_code_descr,
        s.start_date,
        s.end_date,
        s.operating_room
    FROM g_surgery s
),
surgery_teams AS (
    SELECT 
        st.surgery_ref,
        st.task_descr,
        st.employee
    FROM g_surgery_team st
),
surgery_events AS (
    SELECT 
        sts.surgery_ref,
        sts.event_descr,
        sts.event_timestamp
    FROM g_surgery_timestamps sts
)
SELECT 
    su.*,
    st.task_descr,
    se.event_descr,
    se.event_timestamp
FROM surgeries su
LEFT JOIN surgery_teams st ON su.surgery_ref = st.surgery_ref
LEFT JOIN surgery_events se ON su.surgery_ref = se.surgery_ref
ORDER BY su.patient_ref, su.start_date, se.event_timestamp;
```