# DataNex Dictionaries

**Usage**: Use 'descr' to find corresponding 'ref' code for searches. Always search using 'ref' fields, not 'descr'.

---

## Dictionary Tables Schema

### dic_diagnostic

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| diag_ref | INT | PK | Diagnosis reference number |
| catalog | INT | | Catalog code |
| code | VARCHAR(45) | | ICD code |
| diag_descr | VARCHAR(256) | | Diagnosis description (nullable) |

### dic_lab

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| lab_sap_ref | VARCHAR(16) | PK | SAP laboratory parameter reference |
| lab_descr | VARCHAR(256) | | Laboratory parameter description |
| units | VARCHAR(32) | | Units (nullable) |
| lab_ref | INT | | Laboratory reference |

### dic_ou_loc

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_loc_ref | VARCHAR(16) | PK | Physical hospitalization unit reference |
| ou_loc_descr | VARCHAR(256) | | Description (nullable) |
| care_level_type_ref | VARCHAR(16) | | Care level type reference |
| facility_ref | INT | | Facility reference |
| facility_descr | VARCHAR(32) | | Facility description |

### dic_ou_med

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| ou_med_ref | VARCHAR(8) | PK | Medical organizational unit reference |
| ou_med_descr | VARCHAR(32) | | Description |

### dic_rc

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | PK | SAP clinical record reference |
| rc_descr | VARCHAR(256) | | Clinical record description |
| units | VARCHAR(32) | | Units (nullable) |
| rc_ref | INT | | Clinical record reference |

### dic_rc_text

| Attribute | Data type | Key | Definition |
|-----------|-----------|-----|------------|
| rc_sap_ref | VARCHAR(16) | | SAP clinical record reference |
| result_txt | VARCHAR(36) | | Text result value |
| descr | VARCHAR(191) | | Description of the text value |

---

## Dictionary Data (ref:descr format)

### dic_diagnostic (35181 total entries, showing samples)

```
6000001:(osteo)artrosis erosiva
6000002:(osteo)artrosis primaria generalizada
6000003:(osteo)artrosis primaria generalizada
6000004:11 semanas de gestación
6000005:22 semanas de gestación
6000006:23 semanas de gestación
6000007:24 semanas completas de gestacion, recien nacido
6000008:25 26 semanas completas de gestacion, recien nacido
6000009:27 28 semanas completas de gestacion, recien nacido
6000010:29 30 semanas completas de gestacion, recien nacido
6000011:30 semanas de gestación
6000012:31 32 semanas completas de gestacion, recien nacido
6000013:31 semanas de gestación
6000014:32 semanas de gestación
6000015:33 34 semanas completas de gestacion, recien nacido
6000016:33 semanas de gestación
6000017:34 semanas de gestación
6000018:35 36 semanas completas de gestacion, recien nacido
6000019:37 o mas semanas completas de gestacion, recien nacido
6000020:37 semanas de gestación
6000021:38 semanas de gestación
6000022:39 semanas de gestación
6000023:40 semanas de gestación
6000024:41 semanas de gestación
6000025:Abdomen agudo
6000026:Abertura artificial, no especificada
6000027:Abortadora habitual
6000028:Abortadora habitual
6000029:Aborto espontaneo con alteracion metabolica incompleto
6000030:Aborto espontaneo con complicacion neom completo
```
... (35131 more entries in database)

---

### dic_lab (5098 total entries, showing samples)

```
LAB0SDHF:Gen SDH-mutació concreta (cas
LAB110:Urea
LAB1100:Tiempo de protombina segundos
LAB1101:Tiempo de tromboplastina parcial
LAB1102:Fibrinogeno
LAB1103:Temps de trombina
LAB1104:Temps de reptilase
LAB1105:PDF
LAB1106:Plaquetes citrat. Recompte
LAB1107:Antitrombina III
LAB1108:Anticoagulante tipo Lupus
LAB1109:Ac IgG anticardiolipina
LAB1110:Ac IgM anticardiolipina
LAB1111:Grup ABO
LAB1112:Rh (D)
LAB1118:Tiempo de protombina %
LAB1173:INR
LAB11ANDRO:11ß-OH-androsterona
LAB11ETIOO:11ß-OH-etiocolanolona
LAB11OXOO:11-oxo-etiocolanolona
LAB11THAO:Tetrahidro-11-dehidrocorticost
LAB1215:Urea,orina
LAB1225:Urat,orina recent
LAB1255:Magnesi,orina
LAB1300:Leucocitos recuento
LAB1301:Plaquetas recuento
LAB1302:VPM Volumen Plaquetario Medio
LAB1303:PDW Platelet Distribut Width
LAB1304:Plaquetòcrit
LAB1305:Hematias recuento
```
... (5048 more entries in database)

---

### dic_ou_loc (986 total entries, showing samples)

```
HAH:HAH SALA HOSP. DOMICILIARIA
HAH3:HAH3 HOSPITALIZACIÓN DOMICILIARIA 3
HAH4:HAH4 HOSPITALIZACIÓN DOMICILIARIA 4
HAH5:HAH5 HOSPITALIZACIÓN DOMICILIARIA 5
HDOP:HAH PERSONAL HCB
HDOP2:HAH 2 PERSONAL HCB
HDOP3:HAH 3 PERSONAL HCB
HDOP4:HAH 4 PERSONAL HCB
HDOP5:HAH 5 PERSONAL HCB
HDSM:HDSM HOSPITALIZACIÓN DOMICILIARIA PSIQUIATRÍA
HDSMJ:HDSMJ HOSPITALIZACIÓN DOMICILIARIA PSIQUIATRÍA INFANTOJUVENIL
ELE1:SE NEONAT.MAT.UCI  ELE1
ELE2:SE NEONAT.MAT.UCI  ELE2
GEL2:GEL2 SALA G OBSTETRICIA MATERNITAT
GEL3:GEL3 SALA G OBSTETRICIA MATERNITAT
GLE1:GLE1 SALA NEONATOLOGÍA  MATERNITAT
GLE2:GLE2 SALA NEONATOLOGÍA MATERNITAT
GLL2:S. G OBST. MATER.  GLL2
GPO3:GPO3 GESTANTES COVID
ILE1:ILE1 SALA CUIDADOS INTERMEDIOS MATERNITAT
ILE2:SALA INTERMITJOS MATER ILE2
INPO:INPO SALA CUIDADOS INTENSIVOS OBSTETRICIA MATERNITAT
NEL2:NEL2 SALA G NIDOS OBSTETRICIA MATERNITAT
NEL3:NEL3 SALA G NIDOS OBSTETRICIA MATERNITAT
NNPO:NNPO SALA CUIDADOS INTENSIVOS NIDOS OBSTETRICIA MATERNITAT
CPT3:CPT3 SALA C PLATÓ PL.3
EHP40:EHP40 SALA E UGA - PLATÓ
EPT0:EPT0 CUIDADOS INTENSIVOS PLATÓ PL.0
GPT1:GPT1 SALA G PLATÓ PL.1
GPT2:GPT2 SALA G PLATÓ PL.2
```
... (936 more entries in database)

---

### dic_ou_med (287 total entries, showing samples)

```
HP2:2ª planta Plató
HP3:3ª planta Plató
HP4:4ª planta Plató
DLC:ACTIVITAT PERSONAL DE LA CASA
ALE:AL.LERGOLOGIA
B-ANE:ANESTESIOLOGIA BCL
BANE:ANESTESIOLOGIA BCL
ANE:ANESTESIOLOGIA I REANIMACIO
H-PAT:ÁREA OP.HISTOPATOL.I PAT.CEL.
CORE:ÁREA OPERATIVA CORE
QUIR:ÁREA QUIRÚRGICA
E5915:ASSIR LES CORTS
ASM:AVALUACIO I SUPORT METODOLOGIC
HMT:BANC DE SANG
BCL:BARNACLÍNIC
B-BCL:BARNACLÍNIC GENERAL
BCLI:BARNACLÍNIC GENERAL
H-HOS:BCL HOSP. HCP
B-HOS:BCL HOSPITALIZACIÓN B047
LCE:BIOQ.GEN.MOL
BLQ:BLOQUEIG BO
CORBM:BM - GENERAL
CAR:CARDIOLOGIA
H-CAR:CARDIOLOGIA
B-CAR:CARDIOLOGIA BCL
BCAR:CARDIOLOGIA BCL
M-CAR:CARDIOLOGIA MATER REPLICA
CDBGR:CDB GENERAL
M-CIG:CIR. GRAL MATER REPLICA
B-HBP:CIR. HEP. I BILIO-PANCR. BCL
```
... (237 more entries in database)

---

### dic_rc (897 total entries, showing samples)

```
ABDOMEN_DIST:Distensión abdominal
ABDO_NEO:Abdomen
ACR_DIS:Modelo de dispositivo
ACR_FIO2:FiO2 mezclador
ACR_MOD:Modalidad de terapia de oxigenación extracorpórea
ACR_O2Q:Flujo de oxígeno
ACR_OXIGENADOR:Tipo de módulo oxigenador
ACR_PART:Presión arterial postmembrana del módulo oxigenador
ACR_PVEN:Presión venosa premembra del módulo oxigenador
ACR_QS:Flujo de sangre
ACR_RPM:Revoluciones de la bomba centrífuga de sangre
ACR_SVO2:Saturación de oxígeno venosa antes del oxigenador (premembrana)
ACR_TEMP_ART:Temperatura arterial (postmembrana del oxigenador)
ACR_TEMP_VEN:Temperatura venosa (premembrana al oxigenador)
ACTIV_NEO:Actividad
AC_DIS:Dispositivo utilizado para la asistencia circulatoria
AC_MOD:Modalidad de asistencia circulatoria
AC_QS_DER:Flujo de sangre corazón derecho
AC_QS_IZQ:Flujo de sangre corazón izquierdo
AC_RPM_DER:Revoluciones bomba centrífuga corazón derecho
AC_RPM_IZQ:Revoluciones bomba centrífuga corazón izquierdo
ALDRETE:Escala de Aldrete modificada
ALT_NEU_NEO:Alteraciones neurológicas
ANTI_XA:Actividad anti factor X activado
APACHE_II:Valoración de gravedad del enfermo crítico
APTEM:Tromboelastometria con corrección de la fibrinolisis con aprotinina
AR_DIS:Dispositivo para realizar asistencia respiratoria extracorporea
AR_FIO2:FiO2 del mezclador
AR_MOD:Modalidad de terapia de oxigenación extracorpórea
AR_O2Q:Flujo de oxígeno
```
... (847 more entries in database)

---

### dic_rc_text (1634 total entries, showing samples)

```
EDEMA_SACRO:0
FC_CVP:1
DOLOR_PIPP_NEO:10
FC_CVP:2
FC_CVP:3
FC_CVP:4
TCSR_REP_Q:5
TCSR_REP_Q:6
DOLOR_PIPP_NEO:7
DOLOR_PIPP_NEO:8
DOLOR_PIPP_NEO:9
EDEMA_SACRO:No Valorable
ABDOMEN_DIST:Normal
ABDOMEN_DIST:Normal-Distendido
ABDOMEN_DIST:Distendido
ABDO_NEO:Ausente
ABDO_NEO:Leve
ABDO_NEO:Moderada
ABDO_NEO:Grave
ABDO_NEO:Otro (especificar)
ACR_DIS:Levitronix CentriMag
ACR_DIS:Otro (especificar)
ACR_FIO2:Derecha
ACR_FIO2:Izquierda
ACR_FIO2:Biventricular
ACR_FIO2:Otro (especificar)
ACR_QS:CardioHelp
ACR_QS:Otro (especificar)
ACR_QS:Rotaflow
ACR_QS:Levitronix CentriMag
```
... (1584 more entries in database)
