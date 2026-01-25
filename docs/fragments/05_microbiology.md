# DataNex - Microbiology & Antibiograms

## g_micro

Microbiology results for each episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| extrac_date | DATETIME | Sample extraction date |
| res_date | DATETIME | Result date |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| mue_ref | VARCHAR | Sample type/origin code |
| mue_descr | VARCHAR | Sample type description |
| method_descr | VARCHAR | Method used to process sample |
| positive | VARCHAR | **'X'** = microorganism detected |
| antibiogram_ref | INT (FK) | Links to antibiogram |
| micro_ref | VARCHAR | Microorganism code |
| micro_descr | VARCHAR | Microorganism scientific name |
| num_micro | INT | Microbe count (starts at 1) |
| result_text | VARCHAR(128) | Text result |
| care_level_ref | INT (FK) | Care level |

---

## g_antibiograms

Antibiogram results for each episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| extrac_date | DATETIME | Sample extraction date |
| result_date | DATETIME | Result date |
| sample_ref | VARCHAR | Sample type/origin code |
| sample_descr | VARCHAR | Sample description |
| antibiogram_ref | INT | Antibiogram identifier |
| micro_ref | VARCHAR | Microorganism code |
| micro_descr | VARCHAR | Microorganism name |
| antibiotic_ref | VARCHAR | Antibiotic code |
| antibiotic_descr | VARCHAR | Antibiotic name |
| result | VARCHAR | MIC (minimum inhibitory concentration) |
| sensitivity | VARCHAR | **S** (sensitive), **R** (resistant) |
| care_level_ref | INT (FK) | Care level |

---

## Example: Positive cultures with antibiograms

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
