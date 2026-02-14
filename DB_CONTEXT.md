# DataNex Database Schema - LLM Context

**Purpose**: Comprehensive reference for SQL query generation from natural language.

**Privacy**: All example rows in this document use synthetic data only (placeholder IDs 90xxxxx/80xxxxx, year 2099, generic descriptions). No real identifiers or dates are included.

## Instructions for LLM

You are a SQL query assistant specialized in DataNex (Hospital Clinic database). 
Your task: Create SQL queries from natural language questions. If I ask you for the SQL just give that with the following rules. 

### Process:
1. Confirm you understand the DataNex schema very briefly.
2. Request the natural language question
3. Generate optimized SQL query using CTEs when appropriate
4. Present the final query ready for copy-paste

### Rules:

#### General Query Rules:
- Always explain how the query works before showing the code
- Use Common Table Expressions (CTEs) for optimization
- Optimize operations on large tables (`g_labs` and `g_rc`) by filtering early in CTEs
- Do not explain optimizations in your response, just implement them
- Use always MariaDB dialect.

#### Using Local Dictionaries:
- A complete dictionary repository is available at `dictionaries/` with 54 CSV files covering all coded fields
- **Before writing a SQL query**, grep the relevant dictionary to find the correct `_ref` codes:
  - `dic_lab.csv` → lab_sap_ref codes (e.g., grep "creatinina" to find LAB120)
  - `dic_ou_med.csv` → ou_med_ref codes (e.g., grep "cardiologia" to find CAR)
  - `dic_ou_loc.csv` → ou_loc_ref codes for physical units
  - `dic_diagnostic.csv` → ICD-9/ICD-10 codes and descriptions
  - `dic_rc.csv` → clinical record parameter codes (e.g., grep "temperatura" to find TEMP)
  - `drug_dictionary.csv` → drug_ref and atc_ref codes
  - `atc_dictionary.csv` → ATC pharmaceutical classification
  - `microorganism_dictionary.csv` → micro_ref codes
  - `antibiotic_dictionary.csv` → antibiotic_ref codes
  - `surgery_code_dictionary.csv` → surgery Q-codes
  - `snomed_health_issues_dictionary.csv` → SNOMED-CT codes
  - `enum_*.csv` → inline code meanings (episode types, care levels, sex, POA, etc.)
- Full index: `dictionaries/dictionaries_manifest.csv` and `dictionaries/dictionaries_README.md`
- This avoids unnecessary exploratory queries to the database and ensures correct reference codes

#### Searching by Reference Fields:
- **Default behavior**: Search using `_ref` fields (e.g., `lab_sap_ref`, `ou_med_ref`)
- Retrieve `_ref` values from the local `dictionaries/` CSV files first, or from `dic_` tables when needed
- If you think a first query exploring the necessary `_ref` codes could be helpful, ask the user to execute it and paste the result so that you can retrieve the needed codes

#### Searching Diagnoses (g_diagnostics table):
1. **Primary method**: Search by `code` field using ICD-9 or ICD-10 codes
   - Use your knowledge of ICD codes or search online for the appropriate codes
   - Always use `LIKE '%code%'` pattern matching (e.g., `code LIKE '%50.5%'` for liver transplant)
   
2. **Alternative method**: Search by `diag_descr` field using text patterns
   - Use only when you don't know the specific ICD code
   - Always use `LIKE '%text%'` pattern matching (e.g., `diag_descr LIKE '%diabetes%'`)

3. **NEVER use**: 
   - The `catalog` field (unless explicitly requested by the user)
   - The `diag_ref` field to join with `dic_diagnostic` (they are independent systems)
   - The `care_level' related fields because they are under development in the database. 

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

**Example (5 rows)**

| episode_ref | patient_ref | episode_type_ref | start_date | end_date | load_date |
| --- | --- | --- | --- | --- | --- |
| 800001 | 900001 | AM | 2099-01-03 12:33:59 | 2099-01-03 12:33:59 | 2099-12-31 12:00:00 |
| 800002 | 900002 | AM | 2099-01-04 12:37:22 | 2099-01-04 09:00:00 | 2099-12-31 12:00:00 |
| 800003 | 900003 | AM | 2099-01-05 12:36:51 | 2099-01-05 12:36:51 | 2099-12-31 12:00:00 |
| 800004 | 900004 | AM | 2099-01-06 12:39:13 | 2099-01-06 12:39:13 | 2099-12-31 12:00:00 |
| 800005 | 900005 | AM | 2099-01-07 12:40:48 | 2099-01-07 19:30:00 | 2099-12-31 12:00:00 |


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

**Example (5 rows)**

| patient_ref | episode_ref | care_level_ref | start_date | end_date | load_date | care_level_type_ref |
| --- | --- | --- | --- | --- | --- | --- |
| 900001 | 900002 | 16 | 2099-01-03 18:33:07 | 2099-01-03 11:12:57 | 2099-01-03 18:22:13 | EM |
| 900003 | 900004 | 17 | 2099-01-04 07:30:00 | 2099-01-04 11:02:48 | 2099-01-04 22:04:44 | WARD |
| 900005 | 900006 | 18 | 2099-01-05 16:00:00 | 2099-01-05 15:40:00 | 2099-01-05 11:18:20 | WARD |
| 900007 | 900008 | 19 | 2099-01-06 08:15:00 | 2099-01-06 14:27:31 | 2099-01-06 11:18:56 | SHORT |
| 900009 | 900010 | 20 | 2099-01-07 23:00:00 | 2099-01-07 11:38:33 | 2099-01-07 11:19:08 | EM |


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

**Example (5 rows)**

| patient_ref | episode_ref | start_date | end_date | place_ref | ou_med_ref | ou_med_descr | ou_loc_ref | ou_loc_descr | care_level_type_ref | facility | load_date | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900011 | 900012 | 2099-01-03 12:20:16 | 2099-01-03 13:52:46 | 900013 | HDM | Example unit
 | UNIT_X | Example unit | HAH | Example facility | 2099-01-04 08:55:14 | 546 |
| 900011 | 900012 | 2099-01-05 13:52:46 | 2099-01-05 14:07:24 | 900014 | HDM | Example unit
 | UNIT_X | Example unit | HAH | Example facility | 2099-01-06 08:55:14 | 546 |
| 900015 | 100006 | 2099-01-07 13:49:11 | 2099-01-07 14:04:38 | 900017 | HDM | Example unit
 | UNIT_X | Example unit | HAH | Example facility | 2099-01-08 08:55:14 | 900018 |
| 900019 | 100010 | 2099-01-09 18:18:54 | 2099-01-09 14:36:45 | 900021 | HDM | Example unit
 | UNIT_X | Example unit | HAH | Example facility | 2099-01-10 08:55:14 | 900022 |
| 900019 | 100010 | 2099-01-11 14:36:45 | 2099-01-11 14:36:45 | 900021 | HDM | Example unit
 | UNIT_X | Example unit | HAH | Example facility | 2099-01-12 11:17:41 | 900022 |


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

**Example (5 rows)**

| patient_ref | birth_date | sex | natio_ref | natio_descr | health_area | postcode | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 900023 | 2090-01-01 | 1 | XX | Example country | AREA_A | 00000 | 2099-12-31 12:00:00 |
| 900025 | 2090-01-02 | 1 | XX | Example country | AREA_A | 00000 | 2099-12-31 12:00:00 |
| 900027 | 2090-01-03 | 1 | XX | Example country | AREA_A | 00000 | 2099-12-31 12:00:00 |
| 900029 | 2090-01-04 | 2 | XX | Example country | AREA_A | 00000 | 2099-12-31 12:00:00 |
| 900031 | 2090-01-05 | 2 | XX | Example country | AREA_A | 00000 | 2099-12-31 12:00:00 |


---

### g_exitus

Contains the date of death for each patient.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | PK | Pseudonymized number that identifies a patient |
| exitus_date | DATE | | Date of death |
| load_date | DATETIME | | Date and time of update |

**Example (5 rows)**

| patient_ref | exitus_date | load_date |
| --- | --- | --- |
| 900001 | 2099-01-03 | 2099-12-31 12:00:00 |
| 900002 | 2099-01-04 | 2099-12-31 12:00:00 |
| 900003 | 2099-01-05 | 2099-12-31 12:00:00 |
| 900004 | 2099-01-06 | 2099-12-31 12:00:00 |
| 900005 | 2099-01-07 | 2099-12-31 12:00:00 |


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

**Example (5 rows)**

| patient_ref | episode_ref | mot_ref | mot_descr | mot_type | load_date |
| --- | --- | --- | --- | --- | --- |
| 900033 | 900034 | 900035 | Example motive | START | 2099-01-03 06:03:39 |
| 900036 | 900037 | 900035 | Example motive | START | 2099-01-04 23:31:25 |
| 900038 | 900039 | 900035 | Example motive | START | 2099-01-05 13:38:39 |
| 900040 | 900041 | 900035 | Example motive | START | 2099-01-06 23:50:44 |
| 900042 | 900043 | 900035 | Example motive | START | 2099-01-07 21:05:23 |


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

**Example (5 rows)**

| patient_ref | episode_ref | diag_date | diag_ref | catalog | code | diag_descr | class | poa | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900044 | 100005 | 2099-01-03 11:48:31 | 1 | 12 | M15.4 | (osteo)artrosis erosiva | A | - | 2099-01-03 09:50:42 |
| 900046 | 100007 | 2099-01-04 08:39:17 | 1 | 12 | M15.4 | (osteo)artrosis erosiva | A | - | 2099-01-04 13:07:18 |
| 900048 | 100009 | 2099-01-05 17:45:34 | 1 | 12 | M15.4 | (osteo)artrosis erosiva | A | - | 2099-01-05 09:50:42 |
| 900050 | 100001 | 2099-01-06 09:52:19 | 1 | 12 | M15.4 | (osteo)artrosis erosiva | A | - | 2099-01-06 08:36:37 |
| 900052 | 100003 | 2099-01-07 19:30:48 | 1 | 12 | M15.4 | (osteo)artrosis erosiva | A | - | 2099-01-07 08:36:37 |


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

**Example (5 rows)**

| patient_ref | episode_ref | weight | drg_ref | severity_ref | severity_descr | mortality_risk_ref | mortality_risk_descr | mdc_ref | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 343 | 181 | 0.3292 | 560 | 2 | Moderate | 1 | Minor | 14 | 2099-01-03 11:48:19 |
| 473 | 220 | 0.5545 | 750 | 1 | Minor | 1 | Minor | 19 | 2099-01-04 11:48:19 |
| 604 | 286 | 0.4554 | 751 | 2 | Moderate | 1 | Minor | 19 | 2099-01-05 11:48:19 |
| 740 | 350 | 0.3292 | 560 | 2 | Moderate | 1 | Minor | 14 | 2099-01-06 11:48:19 |
| 771 | 365 | 0.4932 | 540 | 1 | Minor | 1 | Minor | 14 | 2099-01-07 11:48:19 |


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

**Example (5 rows)**

| patient_ref | episode_ref | snomed_ref | snomed_descr | ou_med_ref | start_date | end_date | end_motive | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900054 | 900055.0 | 100006 |  | UCOT | 2099-01-03 00:00:00 |  | 03 | 2099-01-03 15:32:56 |
| 900057 | 900058.0 | 100006 |  | UCOT | 2099-01-04 00:00:00 |  | 03 | 2099-01-04 15:30:09 |
| 900059 | 900060.0 | 100006 |  | UCOT | 2099-01-05 00:00:00 |  | 03 | 2099-01-05 15:30:42 |
| 900061 |  | 900062 |  | CAR | 2099-01-06 00:00:00 |  | 03 | 2099-01-06 15:25:04 |
| 900063 |  | 900064 |  | URM | 2099-01-07 00:00:00 |  | 03 | 2099-01-07 15:26:12 |


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

**Example (5 rows)**

| patient_ref | episode_ref | extrac_date | result_date | load_date | ou_med_ref | care_level_ref | lab_sap_ref | lab_descr | result_num | result_txt | units | lab_group_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6835 | 5416 | 2099-01-03 11:09:30 | 2099-01-03 17:33:55 | 2099-01-03 13:05:02 | GAS |  | LAB0SDHF | Example lab parameter|  | (Example result) | N.D. | 900065 |
| 6835 | 5416 | 2099-01-04 11:09:30 | 2099-01-04 09:11:03 | 2099-01-04 13:05:02 | GAS |  | LAB0SDHF | Example lab parameter|  | (Example result) | N.D. | 900065 |
| 900066 | 100007 | 2099-01-05 07:40:22 | 2099-01-05 18:45:20 | 2099-01-05 20:19:46 | END |  | LAB0SDHF | Example lab parameter|  | (Example result) | N.D. | 900065 |
| 900068 | 100009 | 2099-01-06 16:18:10 | 2099-01-06 13:29:53 | 2099-01-06 09:14:46 | END |  | LAB0SDHF | Example lab parameter|  | (Example result) | N.D. | 900065 |
| 900070 | 900071 | 2099-01-07 09:58:40 | 2099-01-07 11:14:20 | 2099-01-07 12:52:26 | END |  | LAB0SDHF | Example lab parameter|  | Example result | N.D. | 900065 |


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

**Example (5 rows)**

| patient_ref | episode_ref | result_date | meas_type_ref | load_date | ou_loc_ref | ou_med_ref | rc_sap_ref | rc_descr | result_num | result_txt | units | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900072 |  | 2099-01-03 09:00:00 | 0 | 2099-01-03 19:26:32 | GEL2 | OBS | ABDOMEN_DIST | DistensiÃ³n abdominal |  | EXAMPLE_CODE | DescripciÃ³n |  |
| 900073 |  | 2099-01-04 09:00:00 | 0 | 2099-01-04 19:26:32 | GEL2 | OBS | ABDOMEN_DIST | DistensiÃ³n abdominal |  | EXAMPLE_CODE | DescripciÃ³n |  |
| 900074 |  | 2099-01-05 11:00:00 | 0 | 2099-01-05 20:06:22 | SP00 | OBS | ABDOMEN_DIST | DistensiÃ³n abdominal |  | EXAMPLE_CODE | DescripciÃ³n |  |
| 900075 |  | 2099-01-06 10:00:00 | 0 | 2099-01-06 20:56:43 | GEL2 | OBS | ABDOMEN_DIST | DistensiÃ³n abdominal |  | EXAMPLE_CODE | DescripciÃ³n |  |
| 900076 |  | 2099-01-07 10:00:00 | 0 | 2099-01-07 20:06:22 | GEL2 | OBS | ABDOMEN_DIST | DistensiÃ³n abdominal |  | EXAMPLE_CODE | DescripciÃ³n |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | extrac_date | res_date | ou_med_ref | mue_ref | mue_descr | method_descr | positive | antibiogram_ref | micro_ref | micro_descr | num_micro | result_text | load_date | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900077 | 900078 | 2099-01-03 13:41:00 | 2099-01-03 08:58:47 | HEP | MICMAEX | Aspirats, Exudats, Biópsies, Drenatges | Biopsia |  |  |  |  |  |  Negative,  | 2099-01-03 12:18:29 |  |
| 900079 | 900080 | 2099-01-04 15:05:00 | 2099-01-04 09:33:13 | URM | MICMAEX | Aspirats, Exudats, Biópsies, Drenatges | AbscÃ©s/pus/exudat | X | 900081 | MICSAUR | Staphylococcus aureus | 1.0 |  SaÃ¯llen abundants colÃ²nies de: Staphylococcus aureus | 2099-01-04 12:23:31 |  |
| 900082 | 900083 | 2099-01-05 19:27:00 | 2099-01-05 15:20:25 | MDI | MICMAEX | Aspirats, Exudats, Biópsies, Drenatges | AbscÃ©s/pus/exudat |  |  |  |  |  |  Sample not received,  | 2099-01-05 12:23:31 |  |
| 900084 | 900085 | 2099-01-06 11:38:00 | 2099-01-06 09:10:03 | GER | MICMAEX | Aspirats, Exudats, Biópsies, Drenatges | AbscÃ©s/pus/exudat | X | 900086 | MICECOL | Escherichia coli | 1.0 |  SaÃ¯llen abundants colÃ²nies de: Escherichia coli | 2099-01-06 12:33:43 |  |
| 900087 | 900088 | 2099-01-07 12:51:00 | 2099-01-07 19:21:39 | ERM | MICMAEX | Aspirats, Exudats, Biópsies, Drenatges | AbscÃ©s/pus/exudat | X | 900089 | MICECNE | Estafilococ coagulasa Negative | 1.0 |  SaÃ¯llen abundants colÃ²nies de: Estafilococ coagulasa Negative | 2099-01-07 12:33:43 |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | extrac_date | result_date | sample_ref | sample_descr | antibiogram_ref | micro_ref | micro_descr | antibiotic_ref | antibiotic_descr | result | sensitivity | load_date | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900090 | 900091 | 2099-01-03 14:30:00 | 2099-01-03 09:17:35 | MICMPFA | Teixit epitelial, dermis | 900092 | MICSAUR | Staphylococcus aureus | MICFUS | Acid Fusidic | <=0,5 | S | 2099-01-03 12:33:43 |  |
| 900093 | 900094 | 2099-01-04 20:09:00 | 2099-01-04 10:00:35 | MICMPFA | Teixit epitelial, dermis | 900095 | MICSAUR | Staphylococcus aureus | MICFUS | Acid Fusidic | 1 | S | 2099-01-04 12:48:05 |  |
| 900096 | 900097 | 2099-01-05 20:18:00 | 2099-01-05 09:09:10 | MICMPFA | Teixit epitelial, dermis | 900098 | MICSAUR | Staphylococcus aureus | MICFUS | Acid Fusidic | <=0,5 | S | 2099-01-05 13:02:19 |  |
| 900099 | 900100 | 2099-01-06 05:14:00 | 2099-01-06 17:01:49 | MICMPFA | Teixit epitelial, dermis | 900001 | MICSAUR | Staphylococcus aureus | MICFUS | Acid Fusidic | 1 | S | 2099-01-06 13:07:05 |  |
| 900002 | 900003 | 2099-01-07 17:23:00 | 2099-01-07 16:32:45 | MICMMOS | Material osteoarticular | 900004 | MICSAUR | Staphylococcus aureus | MICFUS | Acid Fusidic | 1 | S | 2099-01-07 13:16:17 |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | treatment_ref | prn | freq_ref | phform_ref | phform_descr | prescr_env_ref | adm_route_ref | route_descr | atc_ref | atc_descr | ou_loc_ref | ou_med_ref | start_drug_date | end_drug_date | load_date | drug_ref | drug_descr | enum | dose | unit | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4923 | 100005 | 100006 |  | DE-0-0 | 110 | CAPSULA | 4 | 100 | ORAL | A02BC01 | Omeprazol | G093 | HEP | 2099-01-03 15:28:22 | 2099-01-03 15:29:25 | 2099-01-03 13:51:50 | DRUGREF001 | OMEPRAZOL | 0 | 1.0 | UND |  |
| 4923 | 100005 | 100007 |  | DE-0-0 | 110 | CAPSULA | 4 | 100 | ORAL | A02BC01 | Omeprazol | G093 | HEP | 2099-01-04 15:29:20 | 2099-01-04 19:26:10 | 2099-01-04 14:26:27 | DRUGREF001 | OMEPRAZOL | 0 | 1.0 | UND |  |
| 900008 | 100009 | 100010 |  | C/12H | 110 | CAPSULA | 4 | 100 | ORAL | A02BC01 | Omeprazol | U071 | HEM | 2099-01-05 13:48:41 | 2099-01-05 19:16:46 | 2099-01-05 14:55:54 | DRUGREF001 | OMEPRAZOL | 0 | 1.0 | UND |  |
| 900011 | 100002 | 100003 |  | C/24H | 110 | CAPSULA | 4 | 100 | ORAL | A02BC01 | Omeprazol | G093 | HEP | 2099-01-06 10:12:29 | 2099-01-06 10:12:48 | 2099-01-06 13:51:50 | DRUGREF001 | OMEPRAZOL | 0 | 1.0 | UND |  |
| 900011 | 100002 | 100004 |  | C/24H | 110 | CAPSULA | 4 | 100 | ORAL | A02BC01 | Omeprazol | G093 | HEP | 2099-01-07 10:12:43 | 2099-01-07 19:28:14 | 2099-01-07 14:26:27 | DRUGREF001 | OMEPRAZOL | 0 | 1.0 | UND |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | treatment_ref | administration_date | route_ref | route_descr | prn | given | not_given_reason_ref | drug_ref | drug_descr | atc_ref | atc_descr | enum | quantity | quantity_planing | quantity_unit | load_date | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900015 | 100006 | 900017 | 2099-01-03 13:46:00 | 350 | PERFUSION INTRAVENOSA |  |  | 0 | DRUGREF001 | DOPAMINA [x8] 2000 MG + SF / 250 ML | B05BB91 | Sodio cloruro, solucion parenteral | 0 | 250.0 |  | ML | 2099-01-03 12:34:41 |  |
| 900015 | 100006 | 900017 | 2099-01-04 00:00:00 | 350 | PERFUSION INTRAVENOSA |  |  | 0 | DRUGREF001 | DOPAMINA [x8] 2000 MG + SF / 250 ML | B05BB91 | Sodio cloruro, solucion parenteral | 0 | 250.0 |  | ML | 2099-01-04 12:34:41 |  |
| 900018 | 100009 | 900020 | 2099-01-05 15:48:48 | 100 | ORAL |  | X | 7 | DRUGREF001 | CITALOPRAM, 30 MG COMP | N06AB04 | Citalopram | 0 | 1.0 |  | UND | 2099-01-05 13:06:02 |  |
| 900018 | 100009 | 900020 | 2099-01-06 16:09:33 | 100 | ORAL |  | X | 7 | DRUGREF001 | CITALOPRAM, 30 MG COMP | N06AB04 | Citalopram | 0 | 1.0 |  | UND | 2099-01-06 13:06:02 |  |
| 900018 | 100009 | 900020 | 2099-01-07 16:39:56 | 100 | ORAL |  | X | 7 | DRUGREF001 | CITALOPRAM, 30 MG COMP | N06AB04 | Citalopram | 0 | 1.0 |  | UND | 2099-01-07 13:06:02 |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | treatment_ref | infusion_rate | rate_change_counter | start_date | end_date | load_date | care_level_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900021 | 100002 | 100003 | 41.67 | 1 | 2099-01-03 00:17:00 | 2099-01-03 09:00:00 | 2099-01-03 09:50:12 |  |
| 900021 | 100002 | 100003 | 41.67 | 2 | 2099-01-04 09:00:00 | 2099-01-04 19:55:00 | 2099-01-04 09:50:12 |  |
| 900021 | 100002 | 100003 | 41.67 | 3 | 2099-01-05 19:55:00 | 2099-01-05 21:00:00 | 2099-01-05 09:50:12 |  |
| 900021 | 100002 | 100004 | 62.5 | 1 | 2099-01-06 00:17:00 | 2099-01-06 01:00:00 | 2099-01-06 09:50:12 |  |
| 900021 | 100002 | 100004 | 62.5 | 2 | 2099-01-07 01:00:00 | 2099-01-07 09:00:00 | 2099-01-07 09:50:12 |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | date | load_date | ou_med_ref | ou_loc_ref | encounter_type | agen_ref | act_type_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900001 | 800001 | 2099-01-03 12:33:59 | 2099-12-31 12:00:00 | ONC | ONCAC | HD | UAC | FIMP |
| 900001 | 800002 | 2099-01-04 08:45:02 | 2099-12-31 12:00:00 | NRC | NRCCE | PP |  |  |
| 900001 | 800002 | 2099-01-05 09:45:00 | 2099-12-31 12:00:00 | NRC | NRCCE | IC |  |  |
| 900001 | 800002 | 2099-01-06 21:17:00 | 2099-12-31 12:00:00 | RADIO | SCA | PR | TCP1 | CNRL |
| 900001 | 800002 | 2099-01-07 10:15:00 | 2099-12-31 12:00:00 | NRC | NRCCE | VS |  |  |


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

**Example (5 rows)**

| patient_ref | episode_ref | ou_loc_ref | ou_med_ref | catalog | code | descr | text | place_ref | place_descr | class | start_date | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900061 | 800061 |  |  | 10 | 10E0XZZ | Example procedure description
 |  | 6 | Example place
 | P | 2099-01-05 03:25:00 | 2099-12-31 12:00:00 |
| 900061 | 800061 |  |  | 10 | 3E0P7VZ | Example procedure |  |  |  | S | 2099-01-06 14:41:00 | 2099-12-31 12:00:00 |
| 900061 | 800061 |  |  | 10 | 3E0R3BZ | Example procedure
 |  |  |  | S | 2099-01-08 02:04:00 | 2099-12-31 12:00:00 |
| 900062 | 800062 |  |  | 10 | GZ50ZZZ | Example procedure
 |  | 5 | Example place
 | P | 2099-01-11 08:46:00 | 2099-12-31 12:00:00 |
| 900063 | 800063 |  |  | 10 | GZ50ZZZ | Example procedure
 |  | 5 | Example place
 | P | 2099-01-14 19:19:00 | 2099-12-31 12:00:00 |


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

**Example (5 rows)**

| patient_ref | episode_ref | ou_med_ref_order | prov_ref | prov_descr | level_1_ref | level_1_descr | level_2_ref | level_2_descr | level_3_ref | level_3_descr | category | start_date | end_date | accession_number | ou_med_ref_exec | start_date_plan | end_date_plan |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900001 | 800001 | ONC | 102FNP | Example provision | VIS | visita | 171 | visita sucesiva | 176 | visita enfermeria | 2 | 2099-01-03 12:33:59 | 2099-01-03 12:33:59 | ACC001 | ONCAC | NaT | NaT |
| 900001 | 800002 | ONC | 103 | Example provision | VIS | visita | 160 | primera visita | 159 | visita medica | 2 | 2099-01-04 09:45:00 | 2099-01-04 09:45:00 | ACC002 | NRCCE | 2099-01-04 09:45:00 | 2099-01-04 09:45:00 |
| 900001 | 800002 | NRC | 9618A | Example provision | DIM | diagnostico imagen | 039 | escaner | 154 | tomografia computarizada | 6 | 2099-01-05 21:17:00 | 2099-01-05 21:17:00 | ACC003 | SCA | 2099-01-05 21:17:00 | 2099-01-05 21:17:00 |
| 900001 | 800002 | NRC | VALSNC_M | Example provision | VIS | visita | 171 | visita sucesiva | 159 | visita medica | 2 | 2099-01-06 08:45:02 | 2099-01-06 08:45:02 | ACC004 | NRCCE | NaT | NaT |
| 900001 | 800002 | NRC | 102 | Example provision | VIS | visita | 171 | visita sucesiva | 159 | visita medica | 2 | 2099-01-07 10:15:00 | 2099-01-07 10:15:00 | ACC005 | NRCCE | 2099-01-07 10:15:00 | 2099-01-07 10:15:00 |


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

**Example (5 rows)**

| patient_ref | episode_ref | ou_loc_ref | ou_med_ref | status | class_ref | class_descr | form_ref | form_descr | form_date | tab_ref | tab_descr | section_ref | section_descr | question_ref | question_descr | value_num | value_text | value_date | value_descr | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900031 | 900032 | E037 | NMO | CO | AL | Alertas | TIPUS_IRA | Example form
 | 2099-01-04 14:41:47 | TIPUS_IRA | Example form
 | P_TIPUS_IR | preguntes Example form| TIPUS_1 | causa ingres |  | 13-IngrÃ©s per altra causa amb IRA- |  | IngrÃ©s per altra causa amb IRA | 2099-01-05 06:01:30 |
| 900033 | 900034 | G094 | CGD | CO | AL | Alertas | CAMP_LET | Example form
 | 2099-01-07 08:51:54 | CAMP_LET | aet
 | PREG_LET | preguntas aet | LET_TXT | let_txt |  | --X |  |  | 2099-01-08 10:07:42 |
| 900033 | 900034 | G094 | CGD | CO | AL | Alertas | CAMP_LET | Example form
 | 2099-01-10 08:51:54 | CAMP_LET | aet
 | PREG_LET | preguntas aet | LET_PRINC | let_princ |  | --X |  |  | 2099-01-11 10:07:42 |
| 900033 | 900034 | G094 | CGD | CO | AL | Alertas | CAMP_LET | Example form
 | 2099-01-13 08:51:54 | CAMP_LET | aet
 | PREG_LET | preguntas aet | LET_1 | intubacion |  | -No- |  | No | 2099-01-14 10:04:56 |
| 900033 | 900034 | G094 | CGD | CO | AL | Alertas | CAMP_LET | Example form
 | 2099-01-16 08:51:54 | CAMP_LET | aet
 | PREG_LET | preguntas aet | LET_2 | vmni |  | -No- |  | No | 2099-01-17 10:04:56 |


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

**Example (5 rows)**

| patient_ref | episode_ref | ou_loc_ref | ou_med_ref | status | class_ref | class_descr | form_ref | form_descr | tab_ref | tab_descr | section_ref | section_descr | question_ref | question_descr | start_date | end_date | value_num | value_text | value_descr | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900035 | 900036 | G065 | ONC | EC | RE | Formularios de Example form | REGISTRES | Example form
 | ESP_FERID | Example section
 | NAFRES | Example section | NUM_FER_N | identificador herida | 2099-01-05 14:45:38 | 2099-01-05 13:13:45 |  | 010 |  1 | 2099-01-05 10:07:34 |
| 900035 | 900036 | G065 | ONC | EC | RE | Formularios de Example form | REGISTRES | Example form
 | ESP_FERID | Example section
 | NAFRES | Example section | DATA_INSER | fecha de inicio | 2099-01-08 14:45:38 | 2099-01-08 13:13:45 |  |  | 06/04/2024 | 2099-01-08 10:15:45 |
| 900035 | 900036 | G065 | ONC | EC | RE | Formularios de Example form | REGISTRES | Example form
 | ESP_FERID | Example section
 | NAFRES | Example section | DATA_VAL | fecha de valoracion | 2099-01-11 14:45:38 | 2099-01-11 13:13:45 |  |  | 10/04/2024 | 2099-01-11 10:15:45 |
| 900035 | 900036 | G065 | ONC | EC | RE | Formularios de Example form | REGISTRES | Example form
 | ESP_FERID | Example section
 | NAFRES | Example section | LOC_GEN | localizacion general | 2099-01-14 14:45:38 | 2099-01-14 13:13:45 |  | 70 | Example location| 2099-01-14 10:07:34 |
| 900035 | 900036 | G065 | ONC | EC | RE | Formularios de Example form | REGISTRES | Example form
 | ESP_FERID | Example section
 | NAFRES | Example section | LOC_ESP_ZS | localizacion Example location| 2099-01-17 14:45:38 | 2099-01-17 13:13:45 |  | 440 | Example location | 2099-01-17 10:07:34 |


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

**Example (5 rows)**

| patient_ref | episode_ref | tag_ref | tag_group | tag_subgroup | tag_descr | inactive_atr | start_date | end_date | load_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900037 | 900038 | 1 | UGO | Example tag | Example tag | 0 | 2099-01-03 12:59:27 |  | 2099-01-03 14:01:08 |
| 900039 | 900040 | 1 | UGO | Example tag | Example tag | 0 | 2099-01-04 04:49:19 |  | 2099-01-04 11:05:43 |
| 900041 | 900042 | 1 | UGO | Example tag | Example tag | 0 | 2099-01-05 13:40:46 |  | 2099-01-05 10:09:05 |
| 900043 | 900044 | 1 | UGO | Example tag | Example tag | 0 | 2099-01-06 16:49:58 |  | 2099-01-06 11:17:20 |
| 900045 | 900046 | 1 | UGO | Example tag | Example tag | 0 | 2099-01-07 16:50:26 |  | 2099-01-07 10:09:05 |


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

**Example (5 rows)**

| patient_ref | episode_ref | mov_ref | ou_med_ref | ou_loc_ref | operating_room | start_date | end_date | surgery_ref | surgery_code | surgery_code_descr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900047 | 100008 | 0 |  |  |  | NaT |  | 900049 | Q00726 | Example procedure|
| 900047 | 100008 | 0 |  |  |  | NaT |  | 900049 | Q00726 | Example procedure|
| 900047 | 100008 | 0 |  |  |  | NaT |  | 900049 | Q00726 | Example procedure|
| 900050 | 100001 | 4 |  |  |  | NaT |  | 900052 | Q01314 | Example procedure|
| 900053 | 100004 | 3 | CIR | BQUIR | QUI2 | 2099-01-07 12:28:00 |  | 900055 | Q00641 | Example procedure|


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

**Example (5 rows)**

| patient_ref | episode_ref | surgery_ref | task_ref | task_descr | employee |
| --- | --- | --- | --- | --- | --- |
| 900064 | 800064 | 700064 | CI | Example role | 900065 |
| 900064 | 800064 | 700064 | EC | Example role | 900066 |
| 900064 | 800064 | 700064 | CI | Example role | 900067 |
| 900064 | 800064 | 700064 | TCDI | Example role | 900068 |
| 900069 | 800069 | 700069 | CI | Example role | 900070 |


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

**Example (5 rows)**

| patient_ref | episode_ref | event_label | event_descr | event_timestamp | surgery_ref |
| --- | --- | --- | --- | --- | --- |
| 900064 | 800064 | ENTRADAQ | Example event | 2099-01-03 13:10:00 | 700064 |
| 900064 | 800064 | SUTURA | Example event | 2099-01-04 13:50:00 | 700064 |
| 900069 | 800069 | ENTRADAQ | Example event | 2099-01-05 10:07:00 | 700069 |
| 900069 | 800069 | SORTIDAQ | Example event | 2099-01-06 10:25:00 | 700069 |
| 900069 | 800069 | SUTURA | Example event | 2099-01-07 10:20:00 | 700069 |


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

**Example (5 rows)**

| patient_ref | episode_ref | surgeon_code | waiting_list | planned_date | proc_ref | registration_date | requesting_physician | priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900063 | 100004 | 900065 | Q041 | 2099-01-03 08:00:00 |  | 2099-01-03 00:00:00 | 900066 | 9 |
| 900067 | 100008 | 900065 | Q041 | 2099-01-04 08:00:00 |  | 2099-01-04 00:00:00 | 900069 | 9 |
| 900070 | 100001 | 900072 | Q041 | 2099-01-05 08:00:00 |  | 2099-01-05 00:00:00 | 900073 | 9 |
| 900074 | 100005 | 900076 | Q051 | 2099-01-06 09:00:00 |  | 2099-01-06 00:00:00 | 900077 | 9 |
| 900078 | 100009 | 900072 | Q041 | 2099-01-07 15:00:00 |  | 2099-01-07 00:00:00 | 900073 | 9 |


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

**Example (5 rows)**

| patient_ref | episode_ref | case_ref | case_date | sample_ref | sample_descr | validated_by |
| --- | --- | --- | --- | --- | --- | --- |
| 900080 | 100001 | Z17-900082 | 2099-01-03 09:01:51 | Z17-900082-COMPL1 |  | 900083 |
| 900084 | 100005 | C17-900086 | 2099-01-04 15:47:18 | C17-900086-COMPL1 |  | 900083 |
| 900084 | 100005 | C17-900086 | 2099-01-05 15:47:18 | C17-900086-COMPL2 |  | 900087 |
| 900080 | 100001 | B17-900088 | 2099-01-06 11:48:36 | B17-900088-A |  | 900089 |
| 900080 | 100001 | B17-900088 | 2099-01-07 11:48:36 | B17-900088-COMPL1 |  | 900083 |


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

**Example (5 rows)**

| patient_ref | episode_ref | case_ref | case_date | sample_ref | diag_type | diag_code | diag_date | diag_descr | validated_by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 900080 | 100001 | Z17-900082 | 2099-01-03 09:01:51 | Z17-900082-B | L | 900090 | 2099-01-03 11:40:59 | Example term | 900091 |
| 900080 | 100001 | Z17-900082 | 2099-01-04 09:01:51 | Z17-900082-B | M | 900092 | 2099-01-04 11:40:59 | congestiÃ³n | 900091 |
| 900084 | 100005 | C17-900086 | 2099-01-05 15:47:18 | C17-900086-B | L | 900090 | 2099-01-05 16:16:09 | Example term | 7996 |
| 900084 | 100005 | C17-900086 | 2099-01-06 15:47:18 | C17-900086-B | M | 900092 | 2099-01-06 16:16:09 | congestiÃ³n | 7996 |
| 900080 | 100001 | B17-900088 | 2099-01-07 11:48:36 | B17-900088-A | L | 900090 | 2099-01-07 12:09:28 | Example term | 900093 |


---

## Dictionary Tables

> 💡 **All dictionary tables below are available as local CSV files in `dictionaries/`**. When designing SQL queries, grep the local CSVs first to find the correct reference codes instead of running exploratory queries against the database. See `dictionaries/dictionaries_README.md` for a full index of 54 available dictionaries (dic_* tables, data table extracts, and inline enumerations).

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

**Example (5 rows)**

| diag_ref | catalog | code | diag_descr |
| --- | --- | --- | --- |
| 900094 | 12 | M15.4 | (osteo)artrosis erosiva |
| 900095 | 1 | 715.09 | (osteo)artrosis primaria generalizada |
| 900096 | 12 | M15.0 | (osteo)artrosis primaria generalizada |
| 900097 | 12 | Z3A.11 | 11 semanas de gestación |
| 900098 | 12 | Z3A.22 | 22 semanas de gestación |


---

### dic_lab

Laboratory parameters dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| lab_sap_ref | VARCHAR(16) | PK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | Laboratory parameter description |
| units | VARCHAR(32) | | Units |
| lab_ref | INT | | Laboratory reference |

**Example (5 rows)**

| lab_sap_ref | lab_descr | units | lab_ref |
| --- | --- | --- | --- |
| LAB0SDHF | Example lab parameter| N.D. | 1 |
| LAB110 | Urea | mg/dL | 2 |
| LAB1100 | Tiempo de protombina segundos | seg | 3 |
| LAB1101 | Tiempo de tromboplastina parcial | seg | 4 |
| LAB1102 | Fibrinogeno | g/L | 5 |


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

**Example (5 rows)**

| ou_loc_ref | ou_loc_descr | care_level_type_ref | facility_ref | facility_descr |
| --- | --- | --- | --- | --- |
| HAH | Example unit | HAH | 900099 | Example facility |
| HAH3 | Example unit| HAH | 900099 | Example facility |
| HAH4 | Example unit| HAH | 900099 | Example facility |
| HAH5 | Example unit| HAH | 900099 | Example facility |
| UNIT_X | Example unit | HAH | 900099 | Example facility |


---

### dic_ou_med

Medical organizational units dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_med_ref | VARCHAR(8) | PK | Medical organizational unit reference |
| ou_med_descr | VARCHAR(32) | | Description |

**Example (5 rows)**

| ou_med_ref | ou_med_descr |
| --- | --- |
| HP2 | Example unit
 |
| HP3 | Example unit
 |
| HP4 | Example unit
 |
| DLC | Example service
 |
| ALE | Example service
 |


---

### dic_rc

Clinical records dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | PK | SAP clinical record reference |
| rc_descr | VARCHAR(256) | | Clinical record description |
| units | VARCHAR(32) | | Units |
| rc_ref | INT | | Clinical record reference |

**Example (5 rows)**

| rc_sap_ref | rc_descr | units | rc_ref |
| --- | --- | --- | --- |
| ABDOMEN_DIST | DistensiÃ³n abdominal | DescripciÃ³n | 900100 |
| ABDO_NEO | Abdomen | DescripciÃ³n | 900001 |
| ACR_DIS | Modelo de dispositivo | DescripciÃ³n | 900002 |
| ACR_FIO2 | FiO2 mezclador | % | 900003 |
| ACR_MOD | Modalidad de terapia de oxigenaciÃ³n extracorpÃ³rea | DescripciÃ³n | 900004 |


---

### dic_rc_text

Clinical records text values dictionary.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| result_txt | VARCHAR(36) | | Text result value |
| descr | VARCHAR(191) | | Description of the text value |

**Example (5 rows)**

| rc_sap_ref | result_txt | descr |
| --- | --- | --- |
| EDEMA_Example location | 0 | 0 |
| FC_CVP | 1 | 1 |
| DOLOR_PIPP_NEO | 10 | 10 |
| FC_CVP | 2 | 2 |
| FC_CVP | 3 | 3 |


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