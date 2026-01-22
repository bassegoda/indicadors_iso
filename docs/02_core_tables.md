# DataNex Core Tables

## g_episodes

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

## g_care_levels

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

## g_movements

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

## g_demographics

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

## g_exitus

Contains the date of death for each patient.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | PK | Pseudonymized number that identifies a patient |
| exitus_date | DATE | | Date of death |
| load_date | DATETIME | | Date and time of update |

---

## g_adm_disch

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

## g_tags

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

## g_encounters

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
| HD | Hospital de día |
| IC | Interconsulta |
| IQ | Interv. quir. |
| LT | Llamada telef. |
| PA | Preanestesia |
| PR | Prueba |
| PV | Primera vista |
| TR | Tratamiento |
| UR | Urgencias |
| VD | Vis. domicilio |
| VS | Vista sucesiva |

---

## g_provisions

Provisions are healthcare benefits categorized into three levels.

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| patient_ref | INT | FK | Pseudonymized number that identifies a patient |
| episode_ref | INT | FK | Pseudonymized number that identifies an episode |
| ou_med_ref_order | VARCHAR(8) | FK | Medical organizational unit that requests the provision (nullable) |
| prov_ref | VARCHAR(32) | | Code that identifies the healthcare provision |
| prov_descr | VARCHAR(255) | | Description of the provision code |
| level_1_ref | VARCHAR(16) | | Level 1 code (nullable) |
| level_1_descr | VARCHAR(45) | | Level 1 code description (nullable) |
| level_2_ref | VARCHAR(3) | | Level 2 code (nullable) |
| level_2_descr | VARCHAR(55) | | Level 2 code description (nullable) |
| level_3_ref | VARCHAR(3) | | Level 3 code (nullable) |
| level_3_descr | VARCHAR(50) | | Level 3 code description (nullable) |
| category | INT | | Class: **2** (generic provisions), **6** (imaging diagnostic provisions) (nullable) |
| start_date | DATETIME | | Start date of the provision |
| end_date | DATETIME | | End date of the provision (nullable) |
| accession_number | VARCHAR(10) | PK | Unique identifier; links to XNAT data repository |
| ou_med_ref_exec | VARCHAR(8) | FK | Medical organizational unit that executes the provision (nullable) |
| start_date_plan | DATETIME | | Scheduled start date (nullable) |
| end_date_plan | DATETIME | | Scheduled end date (nullable) |
