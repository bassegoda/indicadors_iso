# DataNex - Dictionary Tables

Use dictionaries to find 'ref' codes from descriptions.

---

## dic_diagnostic

> ⚠️ **Important**: `diag_ref` does NOT link to `g_diagnostics.diag_ref`. Search directly by `diag_descr` in `g_diagnostics`.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| diag_ref | INT (PK) | Internal diagnosis ID |
| catalog | INT | Catalog code |
| code | VARCHAR(45) | ICD code |
| diag_descr | VARCHAR(256) | Diagnosis description |

---

## dic_lab

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| lab_sap_ref | VARCHAR(16) (PK) | SAP lab reference |
| lab_descr | VARCHAR(256) | Lab parameter description |
| units | VARCHAR(32) | Units |
| lab_ref | INT | Lab reference |

**Sample entries:**
- LAB110: Urea
- LAB1102: Fibrinogeno
- LAB1173: INR
- LAB1300: Leucocitos recuento
- LAB1301: Plaquetas recuento

---

## dic_ou_loc

Physical hospitalization units.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| ou_loc_ref | VARCHAR(16) (PK) | Physical unit reference |
| ou_loc_descr | VARCHAR(256) | Description |
| care_level_type_ref | VARCHAR(16) | Care level type |
| facility_ref | INT | Facility reference |
| facility_descr | VARCHAR(32) | Facility description |

**Sample entries:**
- ICU: CUIDADOS INTENSIVOS
- WARD: HOSPITALIZACIÓN CONVENCIONAL
- HAH: SALA HOSP. DOMICILIARIA

---

## dic_ou_med

Medical organizational units.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| ou_med_ref | VARCHAR(8) (PK) | Medical unit reference |
| ou_med_descr | VARCHAR(32) | Description |

**Sample entries:**
- ANE: ANESTESIOLOGIA I REANIMACIO
- CAR: CARDIOLOGIA
- NEU: NEUROLOGIA
- HMT: BANC DE SANG

---

## dic_rc

Clinical records dictionary.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| rc_sap_ref | VARCHAR(16) (PK) | SAP clinical record reference |
| rc_descr | VARCHAR(256) | Description |
| units | VARCHAR(32) | Units |
| rc_ref | INT | Clinical record reference |

**Sample entries:**
- FC: Frecuencia cardíaca
- TAS: Tensión arterial sistólica
- TAD: Tensión arterial diastólica
- TEMP: Temperatura
- APACHE_II: Valoración gravedad enfermo crítico

---

## dic_rc_text

Text values for clinical records.

| Attribute | Data type | Definition |
|-----------|-----------|------------|
| rc_sap_ref | VARCHAR(16) | SAP clinical record reference |
| result_txt | VARCHAR(36) | Text result value |
| descr | VARCHAR(191) | Description |
