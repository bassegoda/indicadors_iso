# Admissions — Identificación de ingresos reales

El script `hosp_ward_stays.py` extrae los ingresos reales en una unidad física determinada (ej. E073). Un ingreso se considera **real** únicamente si cumple los tres criterios siguientes:

## Criterios de ingreso real

| # | Criterio | Rationale |
|---|----------|-----------|
| 1 | **Cama asignada**: `place_ref IS NOT NULL` en `g_movements` | Sin cama no hay estancia física; los movimientos sin `place_ref` son traslados administrativos o de paso |
| 2 | **Fecha de ingreso dentro del año solicitado**: `YEAR(admission_date)` debe estar en el rango de años | Se aplica sobre la fecha de ingreso de la **estancia agrupada** (no sobre los movimientos individuales), para evitar corromper el agrupamiento en estancias que cruzan el cambio de año |
| 3 | **Prescripción iniciada durante la estancia**: al menos una prescripción con `start_drug_date >= admission_date AND start_drug_date <= discharge_date` | Acredita que el paciente fue tratado efectivamente en la unidad. Las prescripções que ya estaban activas antes de la llegada no se consideran |

## Lógica de agrupamiento de movimientos en estancias

`g_movements` registra cada cambio de ubicación. Para obtener una estancia continua se agrupan los movimientos consecutivos cuyo `end_date` coincide exactamente con el `start_date` del siguiente (patrón LAG-window):

```
raw_moves  →  flagged_starts  →  grouped_stays  →  cohort
  (filtro         (detecta           (asigna         (GROUP BY:
  unidad +        nuevo stay         stay_id         admission_date,
  fecha broad +   con LAG)           con SUM)        discharge_date,
  place_ref)                                         duración)
```

El filtro de fecha en `raw_moves` es **amplio** (el movimiento toca el rango de años) para que el agrupamiento funcione correctamente si una estancia cruza un cambio de año. El filtro por año real se aplica **después** del agrupamiento, con `HAVING YEAR(MIN(start_date)) BETWEEN min_year AND max_year`.

## Alcance de las prescripciones (episode_ref)

El episodio de urgencias (EM) tiene un `episode_ref` distinto al de la hospitalización (HOSP). El join de prescripciones se hace sobre `episode_ref`, por lo que las prescripciones del paso por urgencias **no** se incluyen automáticamente. Se validó contra E073/2024 que esto no genera falsos negativos: los 17 ingresos excluidos por no tener prescripción iniciada durante la estancia no tenían episodio EM previo, y los 96 ingresos que sí tienen prescripciones activas del EM ya están incluidos por sus propias prescripciones del episodio HOSP.

## Ejecución

```bash
python admissions/hosp_ward_stays.py
```

El script solicita interactivamente:
- **Año(s)**: un solo año (`2024`), un rango (`2023-2025`) o una lista (`2023,2024`)
- **Unidad(es)**: una o varias separadas por coma (`E073` o `E073,I073`)

Genera un CSV por unidad en `admissions/output/` con el nombre `admissions_{unidad}_{años}_{timestamp}.csv`.

## Script por unidad predominante (`hosp_ward_longest_stay.py`)

Cuando se analizan **varias unidades relacionadas** (p. ej. E073 e I073), el script `hosp_ward_longest_stay.py` agrupa movimientos consecutivos entre esas unidades en una sola estancia y asigna cada estancia a la **unidad donde el paciente pasó más tiempo** (principio de estancia predominante). Así se evita contar dos veces a un paciente que pasa de E073 a I073.

**Ejecución:**

```bash
python admissions/hosp_ward_longest_stay.py
```

Solicita año(s) y **al menos dos unidades** (p. ej. `E073,I073`). Los criterios de ingreso real (cama, año, prescripción) son los mismos que en `hosp_ward_stays.py`.

**Salida en terminal:** Para cada unidad se imprime el número de estancias, pacientes, fallecimientos, traslados y **cuántas estancias se excluyen por no tener ninguna prescripción** durante la estancia (línea `Excluded (no prescription): N stays`). Los CSV se guardan en `admissions/output/` con nombres del tipo `admissions_{unidad}_from_{unidades}_{años}_{timestamp}.csv`.

## Carpeta `admissions/validation/`

Carpeta para archivos de validación local (p. ej. listados de estancias con/sin prescripción). **No está versionada**: se eliminó del repositorio y está en `.gitignore`. Puedes usarla en tu máquina sin que se suba a git.

## Columnas de salida

| Columna | Descripción |
|---------|-------------|
| `patient_ref` | ID seudonimizado del paciente |
| `episode_ref` | ID del episodio hospitalario |
| `stay_id` | Identificador de estancia dentro del episodio |
| `ou_loc_ref` | Unidad física |
| `admission_date` | Fecha/hora de ingreso en la unidad |
| `discharge_date` | Fecha/hora de alta de la unidad |
| `hours_stay` | Duración en horas |
| `days_stay` | Duración en días |
| `minutes_stay` | Duración en minutos |
| `num_movements` | Número de movimientos agrupados en la estancia |
| `year_admission` | Año del ingreso |
| `age_at_admission` | Edad en años en la fecha de ingreso |
| `sex` | Sexo (`Male` / `Female` / `Other` / `Not reported`) |
| `exitus_during_stay` | Si el paciente fallecimiento durante la estancia (`Yes` / `No`) |
| `exitus_date` | Fecha de fallecimiento (NULL si no ha fallecido) |
| `procedencia` | Procedencia antes del ingreso (formulario UCI PROCE_MALA), si existe |
| `procedencia_otro_centro` | `Sí` si procedencia es otro centro/hospital, `No` si otra, `Sin datos` si no hay formulario |
