# DataNex - Labs & Clinical Records

## g_labs

Laboratory tests for each episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| extrac_date | DATETIME | Sample extraction date |
| result_date | DATETIME | Result date |
| load_date | DATETIME | Update date |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| care_level_ref | INT (FK) | Care level (may be absent) |
| lab_sap_ref | VARCHAR(16) (FK) | SAP lab parameter reference |
| lab_descr | VARCHAR(32) | Lab parameter description |
| result_num | FLOAT | Numerical result |
| result_txt | VARCHAR(128) | Text result |
| units | VARCHAR(32) | Units |
| lab_group_ref | INT | Grouped lab parameters |

---

## g_rc

Clinical records (vital signs, measurements).

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| result_date | DATETIME | Measurement date |
| meas_type_ref | VARCHAR(1) | **0** (manual), **1** (machine, not validated), **2** (machine, validated) |
| ou_loc_ref | VARCHAR(8) (FK) | Physical unit (if manual) |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit (if manual) |
| rc_sap_ref | VARCHAR(16) | SAP clinical record reference |
| rc_descr | VARCHAR(32) | Clinical record description |
| result_num | FLOAT | Numerical result |
| result_txt | VARCHAR(128) | Text result |
| units | VARCHAR(8) | Units |
| care_level_ref | INT (FK) | Care level |

---

## dic_lab (Dictionary)

| lab_sap_ref | lab_descr |
|-------------|-----------|
| LAB110 | Urea |
| LAB1100 | Tiempo de protombina segundos |
| LAB1102 | Fibrinogeno |
| LAB1111 | Grup ABO |
| LAB1173 | INR |
| LAB1300 | Leucocitos recuento |
| LAB1301 | Plaquetas recuento |

---

## dic_rc (Dictionary)

| rc_sap_ref | rc_descr |
|------------|----------|
| FC | Frecuencia cardíaca |
| TAS | Tensión arterial sistólica |
| TAD | Tensión arterial diastólica |
| TEMP | Temperatura |
| APACHE_II | Valoración gravedad enfermo crítico |

---

## Example: Lab results in date range

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
