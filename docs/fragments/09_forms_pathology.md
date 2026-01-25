# DataNex - Dynamic Forms, Special Records & Pathology

## g_dynamic_forms

Structured clinical data collection forms.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| ou_loc_ref | VARCHAR(8) (FK) | Physical unit |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| status | VARCHAR(3) | **CO** (completed), **EC** (in process) |
| form_ref | VARCHAR(8) | Form identifier |
| form_descr | VARCHAR | Form description |
| tab_ref | VARCHAR(10) | Tab identifier |
| tab_descr | VARCHAR | Tab description |
| section_ref | VARCHAR(10) | Section identifier |
| section_descr | VARCHAR | Section description |
| type_ref | VARCHAR(8) | Question identifier |
| type_descr | VARCHAR | Question description |
| class_ref | VARCHAR(3) | **CC** (clinical course), **EF** (physical exam), **ES** (scales), **RG** (reports), **RE** (special records), **VA** (assessments), **TS** (social work) |
| value_num | FLOAT | Numeric value |
| value_text | VARCHAR(255) | Text value |
| value_date | DATETIME | Date value |
| form_date | DATETIME | Form save date |

**Hierarchy**: Form → Tab → Section → Type (question)

---

## g_special_records

Nursing records (specific type of dynamic form).

Same structure as g_dynamic_forms but `class_ref` = **RE** only.

---

## g_pathology_sample

Pathology samples per case.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| case_ref | VARCHAR (FK) | Case reference |
| case_date | DATETIME | Case date |
| sample_ref | VARCHAR (FK) | Sample reference |
| sample_descr | VARCHAR | Sample description |
| validated_by | INT | Validator |

---

## g_pathology_diagnostic

Pathology diagnoses per case.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| case_ref | VARCHAR (FK) | Case reference |
| case_date | DATETIME | Case date |
| sample_ref | VARCHAR (FK) | Sample reference |
| diag_type | VARCHAR | Diagnosis type |
| diag_code | INT | Diagnosis code |
| diag_date | DATETIME | Diagnosis date |
| diag_descr | VARCHAR | Diagnosis description |
| validated_by | INT | Validator |

**Chain**: `case_ref` and `sample_ref` link pathology tables.

---

## g_tags

Labels to identify patient groups.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| tag_ref | INT (FK) | Tag reference |
| tag_group | VARCHAR | Tag group |
| tag_subgroup | VARCHAR | Tag subgroup |
| tag_descr | VARCHAR | Tag description |
| inactive_atr | INT | **0** (active), **1** (inactive) |
| start_date | DATETIME | Start date |
| end_date | DATETIME | End date |
