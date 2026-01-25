# DataNex - Procedures & Encounters

## g_procedures

All procedures per episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| ou_loc_ref | VARCHAR(8) (FK) | Physical unit |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| catalog | VARCHAR(10) | **1** (ICD9), **12** (ICD10) |
| code | VARCHAR(10) | Procedure code |
| descr | VARCHAR(255) | Procedure description |
| text | VARCHAR(255) | Procedure details |
| place | VARCHAR(2) | Location: **1** (surgical block), **2** (diagnostic cabinet), **3** (minor surgery), **4** (interventional radiology), **5** (non-intervention room), **6** (obstetric block), **EX** (external) |
| class | VARCHAR(2) | **P** (primary), **S** (secondary) |
| start_date | DATETIME | Procedure start |
| end_date | DATETIME | Procedure end |

---

## g_encounters

Punctual medical interactions (visit, test, etc.).

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| date | DATETIME | Encounter date |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| ou_loc_ref | VARCHAR(8) (FK) | Physical unit |
| encounter_type | VARCHAR(8) (FK) | Encounter type (see below) |
| agen_ref | VARCHAR (FK) | Encounter identifier |
| act_type_ref | VARCHAR(8) (FK) | Activity type |

**Encounter types:**

| Code | Description |
|------|-------------|
| PV | Primera vista |
| VS | Vista sucesiva |
| IC | Interconsulta |
| IQ | Interv. quir. |
| PR | Prueba |
| TR | Tratamiento |
| UR | Urgencias |
| HD | Hospital de día |
| CA | Cirugía mayor A |
| CM | Cirugía menor A |
| PA | Preanestesia |

---

## g_provisions

Healthcare benefits (prestaciones).

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| ou_med_ref_order | VARCHAR(8) (FK) | Requesting unit |
| prov_ref | VARCHAR(32) | Provision code |
| prov_descr | VARCHAR(255) | Provision description |
| level_1_ref | VARCHAR(16) | Level 1 code |
| level_1_descr | VARCHAR(45) | Level 1 description |
| level_2_ref | VARCHAR(3) | Level 2 code |
| level_2_descr | VARCHAR(55) | Level 2 description |
| level_3_ref | VARCHAR(3) | Level 3 code |
| level_3_descr | VARCHAR(50) | Level 3 description |
| category | INT | **2** (generic), **6** (imaging) |
| start_date | DATETIME | Start date |
| end_date | DATETIME | End date |
| accession_number | VARCHAR(10) (PK) | Unique ID (links to XNAT) |
| ou_med_ref_exec | VARCHAR(8) (FK) | Executing unit |
