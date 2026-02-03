# Indicadores ISO

Proyecto para obtener indicadores clínicos a partir de una base de datos MySQL del Hospital Clínic de Barcelona.

## Estructura del Proyecto

Cada subcarpeta contiene análisis específicos de diferentes indicadores:

- **demographics/**: Análisis demográfico de cohortes de pacientes
- **deliris/**: Análisis de delirium (CAM-ICU)
- **micro/**: Datos de microbiología y antibiogramas
- **mortality/**: Análisis de mortalidad por mes
- **nutritions/**: Análisis de nutrición enteral y parenteral
- **snisp/**: Análisis de incidentes
- **admissions/**: Identificación de ingresos reales en unidades de hospitalización (ver sección detallada más abajo)

Cada análisis genera sus resultados en una subcarpeta `output/` dentro de su respectiva carpeta.

---

## Admissions — Identificación de ingresos reales

El script `admissions/hosp_ward_stays.py` extrae los ingresos reales en una unidad física determinada (ej. E073). Un ingreso se considera **real** únicamente si cumple los tres criterios siguientes:

### Criterios de ingreso real

| # | Criterio | Rationale |
|---|----------|-----------|
| 1 | **Cama asignada**: `place_ref IS NOT NULL` en `g_movements` | Sin cama no hay estancia física; los movimientos sin `place_ref` son traslados administrativos o de paso |
| 2 | **Fecha de ingreso dentro del año solicitado**: `YEAR(admission_date)` debe estar en el rango de años | Se aplica sobre la fecha de ingreso de la **estancia agrupada** (no sobre los movimientos individuales), para evitar corromper el agrupamiento en estancias que cruzan el cambio de año |
| 3 | **Prescripción iniciada durante la estancia**: al menos una prescripción con `start_drug_date >= admission_date AND start_drug_date <= discharge_date` | Acredita que el paciente fue tratado efectivamente en la unidad. Las prescripções que ya estaban activas antes de la llegada no se consideran |

### Lógica de agrupamiento de movimientos en estancias

`g_movements` registra cada cambio de ubicación. Para obtener una estancia continua se agrupan los movimientos consecutivos cuyo `end_date` coincide exactamente con el `start_date` del siguiente (patrón LAG-window):

```
raw_moves  →  flagged_starts  →  grouped_stays  →  cohort
  (filtro         (detecta           (asigna         (GROUP BY:
  unidad +        nuevo stay         stay_id         admission_date,
  fecha broad +   con LAG)           con SUM)        discharge_date,
  place_ref)                                         duración)
```

El filtro de fecha en `raw_moves` es **amplio** (el movimiento toca el rango de años) para que el agrupamiento funcione correctamente si una estancia cruza un cambio de año. El filtro por año real se aplica **después** del agrupamiento, con `HAVING YEAR(MIN(start_date)) BETWEEN min_year AND max_year`.

### Alcance de las prescripciones (episode_ref)

El episodio de urgencias (EM) tiene un `episode_ref` distinto al de la hospitalización (HOSP). El join de prescripciones se hace sobre `episode_ref`, por lo que las prescripciones del paso por urgencias **no** se incluyen automáticamente. Se validó contra E073/2024 que esto no genera falsos negativos: los 17 ingresos excluidos por no tener prescripción iniciada durante la estancia no tenían episodio EM previo, y los 96 ingresos que sí tienen prescripciones activas del EM ya están incluidos por sus propias prescripciones del episodio HOSP.

### Ejecución

```bash
python admissions/hosp_ward_stays.py
```

El script solicita interactivamente:
- **Año(s)**: un solo año (`2024`), un rango (`2023-2025`) o una lista (`2023,2024`)
- **Unidad(es)**: una o varias separadas por coma (`E073` o `E073,I073`)

Genera un CSV por unidad en `admissions/output/` con el nombre `admissions_{unidad}_{años}_{timestamp}.csv`.

### Columnas de salida

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

## Conexión a la Base de Datos

La conexión a la base de datos se gestiona mediante el módulo `connection.py` ubicado en la raíz del proyecto.

### Configuración

Las credenciales se almacenan en un archivo `.env` ubicado en la **raíz de OneDrive**. El sistema detecta automáticamente la ruta de OneDrive tanto en Windows como en macOS.

### Archivo `.env`

Crea un archivo `.env` en la raíz de OneDrive con el siguiente formato:

```env
DB_HOST=tu_host
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_DATABASE=tu_base_de_datos
DB_PORT=3306
```

**Importante**: Cuando cambie la contraseña (cada 2-5 días), actualiza únicamente la línea `DB_PASSWORD=` en este archivo. El archivo se sincronizará automáticamente con OneDrive en todos tus ordenadores.

### Uso en los Scripts

Todos los scripts importan la conexión de la misma forma:

```python
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from connection import execute_query
```

## Requisitos

Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

Cada script se ejecuta de forma independiente desde su carpeta:

```bash
python demographics/demo.py
python deliris/deliris.py
python nutritions/nutritions.py
```

Los scripts solicitan interactivamente los parámetros necesarios (año, unidades, etc.) y generan los resultados en la carpeta `output/` correspondiente.
