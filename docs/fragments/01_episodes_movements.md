# DataNex - Episodes, Care Levels & Movements

## g_episodes

Contains all hospital episodes for each patient.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| episode_ref | INT (PK) | Identifies an episode |
| patient_ref | INT (FK) | Identifies a patient |
| episode_type_ref | VARCHAR(8) | **AM** (outpatient), **EM** (emergency), **DON** (Donor), **HOSP_IQ** (surgery), **HOSP_RN** (newborn), **HOSP** (other hospitalization), **EXT_SAMP** (external sample), **HAH** (hospital at home) |
| start_date | DATETIME | Start of episode |
| end_date | DATETIME | End of episode (in AM = last visit date) |
| load_date | DATETIME | Update date |

---

## g_care_levels

Care level = intensity of healthcare needs. Only EM, HAH and HOSP episodes have care levels.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| care_level_ref | INT (PK) | Groups consecutive care levels of same type |
| start_date | DATETIME | Start of care level |
| end_date | DATETIME | End of care level |
| load_date | DATETIME | Update date |
| care_level_type_ref | VARCHAR(16) | **WARD** (conventional), **ICU** (intensive), **EM** (emergency), **SPEC** (special), **HAH** (home), **SHORT** (short stay) |

---

## g_movements

Movements = changes in patient's location. Discharge and exitus are also movements.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| start_date | DATETIME | Start of movement |
| end_date | DATETIME | End of movement |
| place_ref | INT | Encrypted room/bed reference |
| ou_med_ref | VARCHAR(8) (FK) | Medical organizational unit |
| ou_med_descr | VARCHAR(32) | Medical unit description |
| ou_loc_ref | VARCHAR(8) (FK) | Physical hospitalization unit |
| ou_loc_descr | VARCHAR(32) | Physical unit description |
| care_level_type_ref | VARCHAR(8) | Care level type |
| facility | VARCHAR(32) | Facility description |
| care_level_ref | INT (FK) | Links to care level |

---

## Example: ICU stays with movements

```sql
WITH icu_stays AS (
    SELECT 
        cl.patient_ref,
        cl.episode_ref,
        cl.care_level_ref,
        cl.start_date AS icu_start,
        cl.end_date AS icu_end
    FROM g_care_levels cl
    WHERE cl.care_level_type_ref = 'ICU'
),
icu_movements AS (
    SELECT 
        m.patient_ref,
        m.care_level_ref,
        m.ou_loc_descr,
        m.start_date,
        m.end_date
    FROM g_movements m
)
SELECT 
    i.*,
    im.ou_loc_descr,
    im.start_date AS movement_start
FROM icu_stays i
JOIN icu_movements im 
    ON i.patient_ref = im.patient_ref 
    AND i.care_level_ref = im.care_level_ref
ORDER BY i.patient_ref, im.start_date;
```
