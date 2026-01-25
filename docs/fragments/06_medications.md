# DataNex - Medications (Prescriptions, Administrations, Perfusions)

`treatment_ref` links these three tables: **g_prescriptions** ↔ **g_administrations** ↔ **g_perfusions**

---

## g_prescriptions

Prescribed medical products (pharmaceuticals and devices).

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| treatment_ref | INT | Treatment prescription identifier |
| prn | VARCHAR | **X** = administered only if needed |
| freq_ref | VARCHAR (FK) | Administration frequency |
| phform_ref | INT (FK) | Pharmaceutical form |
| phform_descr | VARCHAR | Pharmaceutical form description |
| prescr_env_ref | INT (FK) | Healthcare setting |
| adm_route_ref | INT (FK) | Administration route |
| route_descr | VARCHAR | Route description |
| atc_ref | VARCHAR | ATC code |
| atc_descr | VARCHAR | ATC description |
| ou_loc_ref | VARCHAR(8) (FK) | Physical unit |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| start_drug_date | DATETIME | Prescription start |
| end_drug_date | DATETIME | Prescription end |
| drug_ref | VARCHAR (FK) | Medical product ID |
| drug_descr | VARCHAR | Drug description |
| dose | INT | Prescribed dose |
| unit | VARCHAR (FK) | Dose unit |
| care_level_ref | INT (FK) | Care level |

---

## g_administrations

Administered pharmaceuticals.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| treatment_ref | INT | Links to prescription |
| administration_date | DATE | Administration date |
| route_ref | INT (FK) | Administration route |
| route_descr | VARCHAR | Route description |
| prn | VARCHAR | **X** = if needed |
| given | VARCHAR | **X** = NOT administered |
| not_given_reason_ref | INT | Reason for non-administration |
| drug_ref | VARCHAR (FK) | Medical product ID |
| drug_descr | VARCHAR | Drug description |
| atc_ref | VARCHAR | ATC code |
| atc_descr | VARCHAR | ATC description |
| quantity | INT | Dose actually administered |
| quantity_planing | INT | Planned dose |
| quantity_unit | VARCHAR (FK) | Dose unit |
| care_level_ref | INT (FK) | Care level |

---

## g_perfusions

Drug perfusions (continuous infusions).

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| treatment_ref | INT | Links to prescription/administration |
| infusion_rate | INT | Rate in ml/h |
| rate_change_counter | INT | Change counter (starts at 1) |
| start_date | DATETIME | Perfusion start |
| end_date | DATETIME | Perfusion end |
| care_level_ref | INT (FK) | Care level |

---

## Example: Antibiotics prescribed and administered

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
