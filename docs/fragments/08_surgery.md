# DataNex - Surgery Tables

`surgery_ref` links these tables: **g_surgery** ↔ **g_surgery_team** ↔ **g_surgery_timestamps**

---

## g_surgery

General surgical procedure information.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| mov_ref | INT (FK) | Links to movement |
| ou_med_ref | VARCHAR (FK) | Medical unit |
| ou_loc_ref | VARCHAR (FK) | Physical unit |
| operating_room | VARCHAR | Assigned operating room |
| start_date | DATETIME | Surgery start |
| end_date | DATETIME | Surgery end |
| surgery_ref | INT (FK) | Surgery identifier |
| surgery_code | VARCHAR | Q code (e.g., Q01972) |
| surgery_code_descr | VARCHAR | Surgery description |

---

## g_surgery_team

Surgical team and tasks.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| surgery_ref | INT (FK) | Links to surgery |
| task_ref | VARCHAR | Task code |
| task_descr | VARCHAR | Task description |
| employee | INT | Employee who performed task |

---

## g_surgery_timestamps

Timestamps of surgical events.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| event_label | VARCHAR | Event code |
| event_descr | VARCHAR | Event description |
| event_timestamp | DATETIME | When event happened |
| surgery_ref | INT (FK) | Links to surgery |

---

## g_surgery_waiting_list

Waiting list for surgical procedures.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| surgeon_code | INT | Surgeon code |
| waiting_list | VARCHAR | Waiting list name |
| planned_date | DATETIME | Scheduled intervention date |
| proc_ref | VARCHAR (FK) | Procedure code |
| registration_date | DATETIME | Registration date |
| requesting_physician | INT | Requesting physician |
| priority | INT | Priority in waiting list |

---

## Example: Surgical procedures with team and timestamps

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
