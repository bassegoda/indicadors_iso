# DataNex - Diagnoses & Health Issues

## g_diagnostics

Diagnoses for each episode.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| diag_date | DATETIME | Diagnostic registration date |
| diag_ref | INT (FK) | DataNex diagnosis reference |
| catalog | INT | **1** (CIE9 MC), **3** (CIE9 ER), **5** (SNOMED), **8** (SNOMEDCT), **11** (CIE9 Outpatient), **12** (CIE10 MC), **13** (CIE10 Outpatient) |
| code | VARCHAR(8) | ICD-9 or ICD-10 code |
| diag_descr | VARCHAR(32) | Diagnosis description |
| class | VARCHAR(2) | **P** (primary), **S** (secondary), **H** (not validated), **E** (emergency), **A** (outpatient) |
| poa | VARCHAR(2) | **Y** (present on admission), **N** (not present), **U** (unknown), **W** (undetermined), **E** (exempt), **-** (unreported) |

> ⚠️ **Important**: Do NOT use `diag_ref` to link with dictionary. Search directly by `diag_descr` or use `code` field with ICD knowledge.

---

## g_diagnostic_related_groups

DRG for billing and resource allocation.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| weight | FLOAT | DRG cost weight |
| drg_ref | INT (FK) | DRG reference |
| severity_ref | VARCHAR(2) | SOI (Severity of Illness) |
| severity_descr | VARCHAR(128) | SOI description |
| mortality_risk_ref | VARCHAR(2) | ROM (Risk of Mortality) |
| mortality_risk_descr | VARCHAR(128) | ROM description |
| mdc_ref | INT (FK) | MDC (Major Diagnostic Categories) |

---

## g_health_issues

SNOMED-CT codified health problems.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| patient_ref | INT (FK) | Identifies a patient |
| episode_ref | INT (FK) | Identifies an episode |
| snomed_ref | INT | SNOMED code |
| snomed_descr | VARCHAR(255) | SNOMED description |
| ou_med_ref | VARCHAR(8) (FK) | Medical unit |
| start_date | DATE | Start date |
| end_date | DATE | End date (optional) |
| end_motive | INT | Reason for change (optional) |

---

## Example: Patients with specific diagnosis

```sql
WITH diagnosis_search AS (
    SELECT DISTINCT patient_ref, episode_ref, diag_descr
    FROM g_diagnostics
    WHERE diag_descr LIKE '%diabetes%'
)
SELECT * FROM diagnosis_search;
```
