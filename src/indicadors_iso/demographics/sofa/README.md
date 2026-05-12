# SOFA al ingreso en UCI

Pipeline para calcular la puntuación **SOFA original (Vincent et al.,
*Intensive Care Med* 1996;22:707-10)** al ingreso para cada estancia en
una UCI del Hospital Clínic, a partir de DataNex (AWS / Athena) vía
Metabase.

> ⚠️ **No es el "SOFA 2.0" propuesto por Moreno et al. en 2023.** Esta
> implementación usa los cortes y componentes del SOFA clásico. La
> versión actualizada (que añadiría SpO2/FiO2, lactato y AKI-stage
> KDIGO) queda pendiente como posible v2.

> **SOFA al ingreso** = peor valor de cada componente en las **primeras
> 24 h** desde la fecha de admisión a UCI. Rango por componente: 0-4
> puntos. Total: 0-24.

---

## Estructura del módulo

```
demographics/sofa/
├── _config.py     Códigos de lab/rc, regex de fármacos, lista de UCIs, ventana 24 h
├── _sql.py        Query Athena única que devuelve 1 fila por estancia con los 6 componentes agregados
└── _metrics.py    Funciones score_* (0-4 por componente) + compute_sofa()
```

Este módulo se consume como **dependencia de
`demographics/per_unit/run.py`**: ahí se descarga la cohorte SOFA año a
año vía Metabase, se calcula el score por estancia y se mergea en la
cohorte demográfica para enriquecer el reporting (mediana SOFA global,
subgrupo cirrosis y subgrupo procedencia "otro hospital"). No existe
un orquestador SOFA standalone — se usa siempre vía el pipeline
per_unit.

---

## Cómo se calcula cada componente

Para todos los componentes se usa la **ventana 24 h** desde
`movements.start_date` (entrada a UCI). La cohorte de estancias se
construye con la lógica `per_unit` de `demographics/per_unit/` (sin
agrupar traslados entre unidades).

### 1. Respiratorio — PaO2 / FiO2

| Variable | Fuente | Detalle |
|---|---|---|
| **PaO2** | `labs.result_num` | `lab_sap_ref IN ('LAB3072','LABRPAPO2')` (pO2 sangre arterial). Tomamos `MIN` en la ventana. |
| **FiO2** | `rc.result_num` | `rc_sap_ref IN ('FIO2','VMI_FIO2','VNI_FIO2','AR_FIO2','ACR_FIO2','VMA_FIO2')` — cubre respiración espontánea, VMI, VMNI, mezclador y anestesia. Tomamos `MAX` (peor escenario). |
| **VMI activa** | `rc.rc_sap_ref` | Si aparece cualquier registro con `rc_sap_ref IN ('VMI_FIO2','VMI_MOD')` → `on_vmi=1`. |

Puntuación (`score_respiratory` en `_metrics.py`):
- Si no hay PaO2 → componente **NA**.
- Si no hay FiO2 → asumimos 21% (aire ambiente).
- Ratio = PaO2 / (FiO2/100). Puntuación según tabla SOFA estándar (0=≥400, 1=<400, 2=<300, 3=<200 con VMI, 4=<100 con VMI).

### 2. Coagulación — Plaquetas

| Variable | Fuente | Detalle |
|---|---|---|
| **Plaquetas (10⁹/L)** | `labs.result_num` | `lab_sap_ref = 'LAB1301'` ("Plaquetas recuento"). Tomamos `MIN`. |

Puntuación: 0 ≥150, 1 <150, 2 <100, 3 <50, 4 <20.

### 3. Hígado — Bilirrubina total

| Variable | Fuente | Detalle |
|---|---|---|
| **Bilirrubina (mg/dL)** | `labs.result_num` | `lab_sap_ref = 'LAB2407'` ("Bilirrubina adulto total"). Tomamos `MAX`. |

Puntuación: 0 <1.2, 1 ≥1.2, 2 ≥2.0, 3 ≥6.0, 4 ≥12.0.

### 4. Cardiovascular — PAM y vasopresores

| Variable | Fuente | Detalle |
|---|---|---|
| **PAM (mmHg)** | `rc.result_num` | `rc_sap_ref IN ('PA_M','PANIC_M','PANI_M')` — PA invasiva, no invasiva continua, no invasiva. Tomamos `MIN`. |
| **Vasopresor activo** | `perfusions` ↔ `prescriptions` (por `treatment_ref`) **+** `administrations` | Filtro por nombre de fármaco (regex sobre `drug_descr`): `noradr\|norepin\|adrenalin\|epinef\|dopami\|dobutami\|fenilefr\|vasopres\|terlipres\|milrinon\|levosimen\|isoprenal`. Categorización por sub-regex (`on_norepi`, `on_epi`, `on_dopa`, `on_dobu`, `on_vasop`, `on_phenyl`, `on_inotrope_other`). |

> ⚠️ **Hallazgo importante para los joins**:
> - Se identifican vasopresores por **nombre del fármaco**, NO por ATC. Las
>   perfusiones diluidas (BIC, "[x4] 40 MG + SG5%") llevan el `atc_ref`
>   del **diluyente** (`B05BB91` salino, `B05BA91` glucosado), no del
>   principio activo. Filtrar por ATC perdería el grueso.
> - `perfusions` se joinea con la cohorte solo por `patient_ref` + solape
>   temporal de la perfusión. **No** se usa `episode_ref`. Verificado:
>   joinear por `episode_ref` perdía el 100% de las rows porque las
>   perfusiones / prescripciones para el mismo paciente viven en un
>   episode_ref distinto al del movement de UCI.
> - `perfusions` ↔ `prescriptions` se joinea solo por `(patient_ref,
>   treatment_ref)` (sin `episode_ref`).
> - `administrations` se joinea solo por `patient_ref` + ventana sobre
>   `administration_date`. No se filtra por `given` (el ETL guarda string
>   vacío en lugar de NULL para administraciones realizadas).

Puntuación (`score_cardiovascular` — versión sin dosis exacta):
- 4 si **noradrenalina o adrenalina** activas (asumido > 0.1 mcg/kg/min).
- 3 si dopamina, dobutamina, vasopresina, fenilefrina o inotrópico otro.
- 1 si MAP < 70 sin vasopresores.
- 0 si MAP ≥ 70 sin vasopresores.
- NA si no hay MAP y no hay vasopresores.

### 5. SNC — Glasgow Coma Scale

| Variable | Fuente | Detalle |
|---|---|---|
| **GCS total** | `rc.result_num` | `rc_sap_ref = 'COMA_GCS'`. Resultado numérico ya integrado (3-15). Tomamos `MIN`. |

> ⚠️ **No se usa** `dynamic_forms.GLASGOW.OBER_ULLS/RES_MOTORA/RES_VERBAL`
> aunque existe en el catálogo: en producción los valores van como
> string en `value_text` (`"010-De manera espontánea-"`), no en
> `value_num`. La puntuación total `rc.COMA_GCS` ya incluye la suma de
> las 3 subescalas con el mismo timestamp y es más limpia.

Puntuación: 0 = 15, 1 = 13-14, 2 = 10-12, 3 = 6-9, 4 < 6.

### 6. Renal — Creatinina (sin diuresis)

| Variable | Fuente | Detalle |
|---|---|---|
| **Creatinina (mg/dL)** | `labs.result_num` | `lab_sap_ref IN ('LABCREA','LAB2467')`. Tomamos `MAX`. |

> ⚠️ **El ritmo de diuresis NO está disponible en DataNex**. La diuresis
> horaria/24h vive en sistemas que no se cargan en el almacén de datos.
> Por eso el componente renal usa **únicamente creatinina**. Esto puede
> infraestimar la afectación renal real en oligúricos sin elevación de
> creatinina aguda.

Puntuación: 0 <1.2, 1 ≥1.2, 2 ≥2.0, 3 ≥3.5, 4 ≥5.0.

---

## Política de componentes faltantes

Si un componente no es evaluable (no hay GCS, no hay PaO2, etc.) se
marca como **NA** y suma **0** al `sofa_total`.

**No se imputa ningún valor** — incluyendo el caso del paciente
intubado sin GCS: si la enfermería no hizo ventana neurológica para
calcular el GCS es porque clínicamente no procedía, así que asumir un
valor sería superponer una decisión nuestra a una decisión clínica que
ya se tomó.

Para que el lector pueda distinguir un SOFA=5 con cobertura completa
(6/6 componentes) de un SOFA=5 con cobertura parcial (3/6), se preserva
la columna **`sofa_components_available`** (0-6) en el CSV.

---

## Variables auxiliares

Además de los 6 componentes, el CSV de cohorte incluye:

| Columna | Origen | Uso |
|---|---|---|
| `weight_kg` | `rc.result_num` con `rc_sap_ref IN ('PESO','PESO_SECO')`, primer registro válido en ventana 24h (rango 30-250 kg). Fallback: `dynamic_forms` form `UCI` question `PES`. | Reservado para v2 (cálculo dosis vasopresor en mcg/kg/min). `PESO_SECO` es especialmente útil en cirróticos con ascitis. |
| `sofa_form_*` (resp/coag/liver/cardio/neuro/renal) | `dynamic_forms` form `SOFA` questions `SOFA_*` | Validación cruzada contra puntuación SOFA precalculada por la enfermería. **Cobertura observada en 2024: 0% en TODAS las UCIs** — el form existe pero no se rellena en producción. |
| `exitus_during_stay` | `exitus.exitus_date` entre admission y discharge | Para curvas de mortalidad por SOFA. |
| `age_at_admission`, `sex` | `demographics` | Demografía. |
| `admission_date`, `effective_discharge_date`, `window_end` | Cohorte | Trazabilidad de la ventana. |

---

## Unidades incluidas

Definidas en `_config.ICU_UNITS`:

```
E016, E103, E014, E015, E037, E057, E073, E043, I073
```

Las `E0xx` son UCIs propiamente dichas (lista alineada con
`deliris/camicu_compliance.sql`). `I073` es la unidad semi-intensiva
digestiva: opera con monitorización completa (labs frecuentes,
constantes, vasopresores) por lo que el SOFA al ingreso es clínicamente
informativo y se reporta también ahí.

---

## Cómo se usa

El SOFA se calcula automáticamente al lanzar
`python demographics/per_unit/run.py`. La query se ejecuta **año a año**
vía Metabase API (`connection.execute_query_yearly`): cada anualidad
para E073/I073 es ≤ ~500 filas, muy por debajo del tope silencioso de
2000 filas de Metabase. El loader avisa por consola si algún año se
aproxima al tope para que decidas trocear más fino (mes / unidad).

---

## Outputs

El SOFA mergeado se vuelca al CSV de cohorte de per_unit
(`demographics/output/per_unit/ward_stays_cohort_<periodo>_E073.csv`,
columnas `sofa_total`, `sofa_components_available`, `sofa_resp`, …) y
al reporte HTML (`ward_stays_summary_<periodo>_E073.html`) como filas
nuevas en la sección *Clínica*: SOFA global, cobertura 6/6, subgrupo
cirrosis y subgrupo otro hospital.

---

## Validación clínica (2024, 8 UCIs, 3036 estancias)

Curva mortalidad/SOFA monótona — el score discrimina bien:

| Banda SOFA | n | Mortalidad |
|---|---|---|
| 0-4 | 1480 | 3.9% |
| 5-9 | 1220 | 10.7% |
| 10-14 | 317 | 24.0% |
| 15-19 | 17 | 47.1% |
| 20+ | 2 | 100% |

Mediana global SOFA = 5 (IQR 3-7), coherente con literatura UCI.

Cobertura de componentes:
- 34% de las estancias con 6/6 componentes evaluables.
- 42% con 5/6 (faltante más frecuente: GCS).
- 0.4% con 0 componentes.

Perfiles por unidad coherentes con su especialidad: E103 sale como
postquirúrgica (84% VMI con 1.6% mortalidad — ingresos electivos
intubados rutina), E073 como la más grave en términos de SOFA al
ingreso (mediana 7), etc.

---

## Limitaciones conocidas (v1)

1. **Cardiovascular sin dosis exacta de vasopresor**: presencia binaria.
   Para distinguir 3 ↔ 4 por dosis (mcg/kg/min) habría que parsear la
   concentración del fármaco desde `drug_descr` libre (texto tipo
   `"NORADRENALINA [x4] 40 MG + SG5% / 250 ML"`) y combinar con
   `perfusions.infusion_rate` (mL/h) y `weight_kg`.
2. **Renal sin diuresis**: dato no disponible en DataNex.
3. **Respiratorio asume FiO2 = 21% si no hay registro**: razonable si el
   paciente está en respiración espontánea, puede infraestimar si lleva
   gafas / ventimask sin que se registre la FiO2.
4. **Form SOFA precalculado no usable como gold-standard**: existe en
   el catálogo pero la cobertura en producción es 0%.

---

## Diccionarios de referencia

Los códigos `lab_sap_ref` / `rc_sap_ref` / fármacos provienen de:

- `dictionaries/sofa/dic_labs.csv`
- `dictionaries/sofa/dic_rc.csv`
- `dictionaries/sofa/dic_dynamic_forms.csv`
- `dictionaries/sofa/dic_administrations.csv`
- `dictionaries/sofa/dic_perfusions.csv`
- `dictionaries/sofa/dic_prescriptions.csv`

Generados por los SQL `dictionaries/sofa/0X_*.sql` (ejecutados en
Metabase y descargados como CSV completo).
