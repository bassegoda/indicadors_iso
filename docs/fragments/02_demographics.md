# DataNex - Demographics & Death

## g_demographics

Demographic information for each patient.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (PK) | Identifies a patient |
| birth_date | DATE | Date of birth |
| sex | INT | **-1** (not reported), **1** (male), **2** (female), **3** (other) |
| natio_ref | VARCHAR(8) (FK) | Nationality code |
| natio_descr | VARCHAR(512) | Country description (ISO:3) |
| health_area | VARCHAR | Health area |
| postcode | VARCHAR | Postal code |
| load_date | DATETIME | Update date |

---

## g_exitus

Date of death for each patient.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (PK) | Identifies a patient |
| exitus_date | DATE | Date of death |
| load_date | DATETIME | Update date |

---

## g_adm_disch

Reasons for admission and discharge per episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| mot_ref | INT (FK) | Reason code |
| mot_descr | VARCHAR(32) | Reason description |
| mot_type | VARCHAR(45) | **ST** (starting motive), **END** (ending motive) |
| load_date | DATETIME | Update date |

---

## Example: Patient demographics with episodes

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
