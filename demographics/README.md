# Demographics — Reporting clínico/demográfico E073 e I073

Análisis demográfico y clínico de las estancias en las unidades **E073** e **I073** del Hospital Clínic. Genera tablas tipo "Table 1" en HTML + CSV con cifras anuales y total: demografía, estancia, cirrosis, reingresos 24/72 h, mortalidad global / cirrosis / no-AISBE / procedencia otro hospital.

## Estructura

```
demographics/
├── _loader.py                       # carga del snapshot + augmentación sintética 2025
├── _metrics.py                      # cálculos (compartido por ambas variantes)
├── _report.py                       # generación HTML/CSV (compartido)
├── _bed_capacity_sql.py             # SQL parametrizada de capacidad/uso por mes
├── _bed_occupancy.py                # agrega meses al año + cache CSV
├── _config.py                       # FAKE_BED_PLACE_REFS_E073 (cama falsa a excluir)
├── helper_identify_fake_bed.sql     # query auxiliar para identificar la cama falsa
├── README.md                        # este archivo
│
├── predominant_unit/                  ← Variante 1
│   ├── _sql.py                          plantilla SQL parametrizable
│   ├── cohort_query_2019-2025.sql       SQL standalone para Metabase
│   ├── cohort_2019-2025.csv             snapshot (gitignored, generar manualmente)
│   └── run.py                           punto de entrada
│
├── per_unit/                          ← Variante 2
│   ├── _sql.py
│   ├── cohort_query_2019-2025.sql
│   ├── cohort_2019-2025.csv             snapshot (gitignored)
│   └── run.py
│
└── output/
    ├── predominant_unit/                outputs HTML/CSV de la variante 1
    └── per_unit/                        outputs HTML/CSV de la variante 2
```

## Las dos variantes

| Aspecto | `predominant_unit/` | `per_unit/` |
|---|---|---|
| Agrupamiento | Movimientos consecutivos entre E073 e I073 dentro del mismo episodio se **agrupan en una sola estancia**. | Cada unidad genera estancias **independientes**. Un traslado E073→I073 cuenta como **dos estancias** distintas. |
| Asignación a unidad | A la unidad donde el paciente pasó **más tiempo** (con desempate por primera unidad). | A la unidad real del movimiento (por construcción cada estancia = 1 unidad). |
| `had_transfer` | `Yes` si la estancia visitó >1 unidad antes de agruparse. | Siempre `No` (las estancias agrupan una sola unidad). |
| Reingresos 24/72 h | Siguiente estancia del mismo paciente en E073/I073. | Siguiente estancia del mismo paciente en un **episodio distinto** (excluye traslados intra-episodio). |
| Output | **1** HTML/CSV combinado E073+I073. | **2** HTML/CSV, uno por unidad. |
| Filtro común (cama asignada, año, prescripción) | Idéntico. | Idéntico. |

Ambas comparten `_loader.py`, `_metrics.py` y `_report.py`. Las únicas diferencias están en la SQL (plantilla y standalone) y en el script orquestador.

---

## Cómo leer cada informe — guía para audiencia clínica

Los dos informes responden a preguntas distintas. Las cifras **no son intercambiables ni sumables** entre ellos. Esta sección explica qué pacientes se cuentan distinto y dónde puede engañar cada método.

### Idea en 3 frases

- **`predominant_unit`** — un episodio = un ingreso. Si el paciente pasó por E073 y por I073 en el mismo ingreso, el caso aparece **una sola vez**, asignado a la unidad donde estuvo más tiempo. Bueno para responder "¿cuánto trabajo tuvo el servicio E073+I073 en su conjunto?".
- **`per_unit`** — un episodio puede generar varios ingresos. Cada paso por una unidad es un ingreso independiente, aunque sea breve. Bueno para responder "¿cuánto trabajo tuvo MI unidad concreta?".
- Sumar "N estancias E073" + "N estancias I073" del informe per-unit **no** equivale al total combinado del informe predominant-unit: hay solapamiento (los pacientes trasladados entre unidades aparecen en los dos lados del per-unit).

### Tres casos clínicos que se cuentan distinto

> **Caso 1 — Paciente trasladado E073 → I073**
>
> El Sr. García ingresa en E073 desde Urgencias, está 2 días, se traslada a I073 donde permanece 6 días, y al octavo día recibe el alta a domicilio.
>
> | Informe | Cómo aparece |
> |---|---|
> | `predominant_unit` | **1 estancia** asignada a I073 (donde pasó más tiempo). Estancia (días) = 8. En el informe combinado E073+I073, este paciente aparece una vez. |
> | `per_unit` | **2 estancias**: una en el informe E073 (2 días) y otra en el informe I073 (6 días). El paciente se cuenta en los dos informes. |

> **Caso 2 — Paciente que fallece tras un traslado**
>
> La Sra. López ingresa en E073, está 5 días, se traslada a I073 donde fallece al día siguiente. Total: 6 días en planta.
>
> | Informe | Cómo aparece la **mortalidad en estancia** |
> |---|---|
> | `predominant_unit` | La estancia se asigna a E073 (más tiempo) y se marca como exitus en estancia. **El fallecimiento aparece en el informe combinado bajo "Mortalidad en estancia"** (sumada a las muertes de la cohorte). |
> | `per_unit` | El "ingreso E073" muestra `exitus_during_stay = No` (porque a efectos de movimientos la paciente "salió viva" de E073, transferida). El "ingreso I073" muestra `exitus_during_stay = Yes`. **La muerte solo se contabiliza en el informe de I073**. |
>
> ⚠ Implicación: si un patrón habitual es trasladar a pacientes graves de E073 a I073 antes del éxito, **el informe `per_unit` puede infraestimar la mortalidad de E073**. Mirad las dos tablas para tener la imagen completa.

> **Caso 3 — Contar pacientes únicos**
>
> En 2024 hubo (cifras inventadas) 600 pacientes que pasaron por E073 y/o I073. De ellos, 80 fueron trasladados entre las dos unidades durante el mismo ingreso.
>
> | Informe | "N pacientes" |
> |---|---|
> | `predominant_unit` (combinado) | **600** |
> | `per_unit` E073 | 540 (los que pasaron por E073, incluidos los trasladados) |
> | `per_unit` I073 | 140 (los que pasaron por I073, incluidos los trasladados) |
> | Suma per_unit E073 + I073 | **680** ← sobrecuenta en 80 (los pacientes trasladados aparecen en ambos lados) |
>
> ⚠ No sumes los "N pacientes" del informe E073 con los del informe I073: harías un doble conteo de los traslados.

### Limitaciones específicas de `predominant_unit`

- **Atribución sesgada por minoría de tiempo.** Un paciente que pasó el 51 % del ingreso en E073 y el 49 % en I073 aparece como "estancia E073" entera. La actividad de I073 con ese paciente queda invisible en el reporting.
- **Estancia (días) infla la cifra "real" de la unidad asignada.** El campo "Estancia, mediana [IQR]" suma TODO el tiempo del ingreso (incluyendo el tiempo en la otra unidad). Si interpretáis ese número como "días que el paciente pasó en E073", **estaréis sobreestimando**: una parte de esos días los pasó en I073.
- **Mortalidad ubicada en una unidad que tal vez no fue donde ocurrió.** El éxito puede haber pasado físicamente en I073, pero el informe lo contabiliza como muerte de E073 si fue la unidad predominante. Buena práctica: tratar la cifra como "mortalidad del episodio asistido por E073/I073" en lugar de "mortalidad ocurrida en E073".
- **No detecta patrones de traslado.** No se ve cuántos pacientes han ido E073→I073, ni la dirección. La columna `had_transfer` solo dice "Sí/No", sin dirección.
- **Pacientes con ingresos cortos en una unidad pueden desaparecer.** Si un paciente entra en E073 unas horas y se mueve a I073 para 10 días, su paso por E073 no se ve en ningún informe.

### Limitaciones específicas de `per_unit`

- **Doble conteo entre informes.** Como ya se indicó, los pacientes trasladados aparecen en los dos informes. Útil para cargas de trabajo de cada unidad, peligroso si se suman.
- **Estancias artificialmente cortas.** Un traslado a las 2 horas crea un "ingreso" en E073 de 2 horas. Esto **reduce la mediana de estancia** del informe de E073 (donde antes habría una estancia más larga al combinar ambas unidades) y puede dar la falsa impresión de "altas precoces". En realidad fue un traslado.
- **Mortalidad por estancia infraestima en la unidad de partida.** Como en el Caso 2, la unidad donde el paciente NO falleció (porque fue trasladado vivo) no contabiliza el éxito; aunque clínicamente su atención inicial fue parte del proceso. La mortalidad a 30 y 90 días, en cambio, no tiene este sesgo: se calculan desde la admisión y solo dependen de que el paciente muera dentro de la ventana, no de en qué unidad ocurra.
- **30-day / 90-day mortality contabilizada DOS veces** entre informes para los pacientes trasladados. Si la Sra. López fallece a los 12 días de su ingreso en E073 (5 días E073 + 1 día I073 + recuperación, recaída y muerte el día 12), tanto el "ingreso E073" como el "ingreso I073" cumplen mortalidad a 30 d. **Cada informe la cuenta como 1 muerte.** Si calculáis por separado y sumáis, contaréis dos muertes para una persona.
- **Reingresos a corto plazo conservadores.** El cálculo excluye los traslados intra-episodio (lo cual es correcto: no son reingresos). Pero también significa que **un paciente trasladado E073→I073 que vuelve a casa el mismo día y reingresa en E073 24 horas después** sí se cuenta como reingreso (episodio nuevo). Coherente con la definición clínica habitual.
- **Pacientes únicos por unidad ≠ unión.** El "N pacientes" del informe E073 + el del informe I073 no es la cohorte total. Para cifras agregadas del servicio entero, usad `predominant_unit`.

### Recomendaciones rápidas según la pregunta

| Si queréis responder… | Mirad… | Por qué |
|---|---|---|
| ¿Cuántos episodios reales atendió el servicio (E073+I073) este año? | `predominant_unit` | Sin doble conteo. Cada episodio = 1 estancia. |
| ¿Cuál fue la carga de trabajo de mi unidad concreta? | `per_unit` (la unidad que toque) | Refleja cada paso por la unidad, aunque sea breve. |
| ¿Cuál es la ocupación física real de E073 (camas ocupadas / camas disponibles)? | `per_unit` informe E073 | El numerador refleja sólo el tiempo en E073; el denominador, sólo las camas de E073. |
| ¿Cuál es la ocupación global del servicio E073+I073? | `predominant_unit` | Suma las horas de todos los ingresos (en cualquier unidad) frente al pool combinado de 12-14 camas. |
| ¿Cuál es la duración real de los pacientes que cuida mi unidad? | `per_unit` | La mediana refleja el tiempo en esa unidad. |
| ¿Cuál es la duración total del paso de los pacientes por nuestro servicio? | `predominant_unit` | La mediana refleja la duración del episodio entero. |
| ¿Cuál es la mortalidad intrahospitalaria de mi unidad? | **Ambos**, con cuidado. `per_unit` infraestima si trasladáis a pacientes terminales. `predominant_unit` la atribuye a la unidad de mayor permanencia, no a la unidad donde ocurrió el éxito. | Triangulad. Si las cifras son muy distintas, suele señalar un patrón de traslado pre-éxitus. |
| ¿Cuál es la mortalidad del paciente atendido (a 30/90 días)? | `predominant_unit` | Más interpretable: una muerte = una persona; sin riesgo de doble conteo. |
| ¿Cuántos pacientes proceden de otro hospital? | `predominant_unit` | A nivel de paciente único sin solapamientos. |
| Tasa de reingreso del servicio | `predominant_unit` | Tradicionalmente se reporta a nivel de episodio, no de unidad. |
| ¿Cuántos traslados internos se producen entre nuestras unidades? | `predominant_unit` (campo `had_transfer`) | Cada estancia indica si hubo o no traslado intra-servicio. |

### Sobre la fila "Ocupación de camas (%)"

> **Cambio de método (abril 2026):** la ocupación ya no se calcula contra una dotación fija de camas (8/10 en E073, 4 en I073). Antes daba > 100 % en 2021 porque la dotación variaba mes a mes durante COVID. Ahora se deriva **empíricamente** de `datascope_gestor_prod.movements`, mes a mes y agregada al año.

#### Cómo se calcula ahora

La fila se calcula completamente fuera de la cohorte clínica (no depende de `hours_stay`, ni del filtro de prescripciones, ni de la augmentación sintética 2025). El flujo está en `demographics/_bed_capacity_sql.py` + `demographics/_bed_occupancy.py` y se ejecuta una vez por run desde `predominant_unit/run.py` y `per_unit/run.py`.

Por cada `(unidad, año, mes)`:

- **Numerador (`bed_hours_used`)** = suma de los minutos solapados entre cada movimiento y los límites del mes, dividido por 60. Una estancia que cruza el 31-dic se reparte automáticamente entre los dos años.
- **Denominador (`bed_hours_available`)** = `n_camas_activas_ese_mes × horas_del_mes`, donde `n_camas_activas` es el `count distinct` de `place_ref` con al menos un minuto de presencia en la unidad ese mes.

`% anual = Σ_meses(bed_hours_used) / Σ_meses(bed_hours_available) × 100`

En el informe `predominant_unit` (combinado), las filas de E073 e I073 se suman por mes antes de agregar al año. En `per_unit`, sólo se usa la unidad concreta del informe.

#### Exclusión de la cama falsa de E073

E073 contiene una posición auxiliar (en la tabla `movements` se ve como un `place_ref` específico) que no es una cama de paciente crítico, sino un espacio para realizar procedimientos. Se distingue por su mediana de duración por movimiento (horas, no días) y un volumen alto de movimientos breves.

Para excluirla del numerador y del denominador:

1. Ejecutar `demographics/helper_identify_fake_bed.sql` en Metabase.
2. Identificar el(los) `place_ref` cuya mediana de duración sea muy baja con muchos movimientos.
3. Añadirlo(s) a `demographics/_config.py`:

```python
FAKE_BED_PLACE_REFS_E073: list[int] = [123456]  # rellenar con los place_ref reales
```

Si la lista está vacía, el cálculo simplemente no excluye nada (la cama falsa contribuirá tanto al numerador — sus horas — como al denominador — como una cama "activa" más, lo cual amortigua su efecto pero no lo anula del todo).

#### Cache

El resultado de la query se cachea en `demographics/output/_bed_capacity_<units>_<min>-<max>.csv` para no volver a consultar Athena en cada ejecución. Si cambia la lista `FAKE_BED_PLACE_REFS_E073` o se quiere refrescar, basta con borrar ese archivo o pasar `force_refresh=True` a `compute_bed_occupancy(...)`.

#### Limitaciones a tener en cuenta

- **Estancias todavía abiertas** se cuentan hasta `current_timestamp` (un movimiento sin `end_date` se considera ocupando cama hasta ahora). Esto es coherente con la realidad y afecta sobre todo al año en curso.
- **Ocupación física:** una estancia de 3 días suma 72 h al numerador aunque parte del tiempo el paciente físicamente no esté en la cama (pruebas, baño, etc.). Es la métrica estándar de "carga de cama".
- **Camas que no aparecen en `movements`:** si en un mes una cama existe pero no se usó nunca, no se cuenta como activa y no entra en el denominador. En la práctica, en una unidad con alta ocupación todas las camas operativas dejan rastro cada mes; en una unidad infrautilizada el método puede subestimar ligeramente el denominador.
- **2025 Nov-Dic:** la BBDD dejó de cargar movimientos a finales de 2025. La ocupación de 2025 refleja sólo los meses con datos reales en `movements`. La augmentación sintética del cohort (filas `SYN2025-…`) **no afecta** a la ocupación porque ésta se calcula desde `movements`, no desde el cohort.
- **Independencia de filtros clínicos:** numerador y denominador miran la unidad entera, no sólo las estancias con prescripción. Eso hace que la ocupación represente "% de horas-cama de la unidad realmente ocupadas" y no "% de horas-cama atribuibles a la cohorte filtrada".

### Y los datos sintéticos de 2025

Independientemente de la variante, las cifras de **noviembre y diciembre de 2025 no son reales**: la BBDD no había cargado esos datos cuando se generó este reporting. Se han añadido filas sintéticas (bootstrap-sampling de los meses reales de 2025) hasta alcanzar la media de los tres años previos. Detalles técnicos en la sección "Workaround temporal (2)" más abajo.

⚠ **Para una audiencia clínica:**
- Las **proporciones** de 2025 (% mortalidad, % cirrosis, % AISBE, etc.) son fiables porque las filas sintéticas replican las reales — no introducen pacientes con perfiles nuevos.
- Las **cifras absolutas** de 2025 son una *estimación* de cómo habría sido el año completo si los volúmenes se mantuvieran como en 2022-2024. **No son la actividad real registrada.**
- Cuando lleguen los datos reales habrá que regenerar el snapshot; el sistema dejará de inyectar sintéticos automáticamente.

---

## Ejecución

```bash
python demographics/predominant_unit/run.py
python demographics/per_unit/run.py
```

Cada uno pide rango de años (default `2019-2025`) y produce los archivos en `demographics/output/<variante>/`.

> **Nota:** el rango por defecto excluye 2018 — quedó fuera para homogeneizar la serie temporal. Si necesitas analizar 2018, pasa `2018-2025` al prompt y regenera el snapshot CSV con la SQL ajustada.

---

## Workaround temporal (1) — Snapshot CSV en lugar de query Python

> **Estado:** activo desde abril 2026.

### Por qué

`connection.execute_query()` (la conexión Python a Metabase) está **truncando los resultados a 2000 filas**, lo que rompe el análisis 2019–2025 de cualquiera de las dos variantes. Mientras se resuelve el problema con DataNex / Metabase, trabajamos contra un **snapshot CSV** generado manualmente desde la web de Metabase.

### Cómo regenerar un snapshot

Para cada variante (`predominant_unit/` y `per_unit/`):

1. Abrir Metabase (https://metabase.clinic.cat) → nuevo "Native query" sobre la base AWS Athena.
2. Pegar el contenido íntegro de `cohort_query_2019-2025.sql` de la subcarpeta correspondiente.
3. Ejecutar (debe devolver varios miles de filas).
4. Exportar el resultado como **CSV** ("Download full results" → CSV).
5. Renombrar y guardarlo en:
   - `demographics/predominant_unit/cohort_2019-2025.csv`
   - `demographics/per_unit/cohort_2019-2025.csv`

> El nombre `cohort_2019-2025.csv` es exacto: el loader lo busca por path absoluto. El CSV está cubierto por la regla global `*.csv` del `.gitignore`.

### Cómo lo usa el código

`_loader.load_cohort(snapshot_path, min_year, max_year, sql_template, synthetic_group_col)` resuelve la fuente de datos automáticamente:

- **Si existe** el snapshot → lo lee, filtra por `year_admission ∈ [min_year, max_year]` y, si el rango incluye 2025, aplica la augmentación (ver workaround 2).
- **Si NO existe** → ejecuta `sql_template.format(...)` contra Metabase via `connection.execute_query`. Esto solo funciona si el resultado cabe en <2000 filas.

### Cómo volver al modo query Python cuando se arregle

Borrar el(los) snapshot(s):

```bash
rm demographics/predominant_unit/cohort_2019-2025.csv
rm demographics/per_unit/cohort_2019-2025.csv
```

A partir del siguiente run, el loader ejecuta la query directamente. Sin tocar código.

---

## Workaround temporal (2) — Augmentación sintética 2025

> **Estado:** activo desde abril 2026, mientras la BBDD no termine de cargar Nov-Dic 2025.

### Por qué

La base de datos dejó de cargar a finales de octubre / principios de noviembre de 2025. El snapshot real cubre ~10 meses. Para que el reporting sea visualmente comparable con 2024 (año completo) y los porcentajes de 2025 no aparezcan distorsionados por un denominador chico, el loader **rellena** la cohorte 2025 mediante bootstrap-sampling.

### Política de target (cuántas filas añadir)

`_loader.compute_3y_mean_target(df, year_now=2025, n_years=3, group_col=...)` calcula el target como **la media de estancias por año en los 3 años previos**:

- `predominant_unit/` (todos los pacientes juntos): target global = media(2022, 2023, 2024).
  Ejemplo actual: (608 + 640 + 693) / 3 ≈ **647**. Con 562 estancias 2025 reales → +85 sintéticas.
- `per_unit/` (por unidad): un target distinto para E073 y otro para I073, cada uno = media de las estancias de ESA unidad en 2022-2024.

### Cómo se generan las filas sintéticas

`_loader.augment_synthetic_2025` aplica bootstrap-sampling sobre las estancias reales 2025:

1. Toma muestras con reemplazo (`df.sample(replace=True, random_state=42)`) hasta llenar el déficit.
2. Reescribe en cada fila sintética:
   - `patient_ref` y `episode_ref` → prefijos `"SYN2025-…"` (no colisionan con los reales).
   - `admission_date` → aleatoria en `SYNTHETIC_DATE_RANGE` (Nov-Dic 2025 por defecto).
   - `discharge_date` y `effective_discharge_date` → recalculadas preservando la `hours_stay` original.
   - `exitus_date` → desplazada por el mismo delta que la admisión (las cuentas de mortalidad 30/90 d se mantienen).
   - `still_admitted` → `"No"` (entran en el agregado).
   - `synthetic` → `True` (columna nueva, presente en el CSV de cohorte exportado).

Como cada fila sintética es **copia exacta** de una fila real (salvo IDs y fechas), todas las proporciones se preservan en expectativa: % cirrosis, AISBE, procedencia otro hospital, sexo, edad, mortalidad, LOS, etc.

### Configuración

En `demographics/_loader.py`:

```python
SYNTHETIC_DATE_RANGE = (datetime(2025, 11, 1), datetime(2025, 12, 31, 23, 59, 59))
SYNTHETIC_RANDOM_SEED = 42
SYNTHETIC_YEAR = 2025
SYNTHETIC_LOOKBACK_YEARS = 3
```

### Cómo desactivar la augmentación

Cuando la BBDD vuelva a cargar Nov-Dic 2025: regenerar el snapshot real. Si `n_real >= target`, el loader avisa y no añade nada (sin tocar código).

Si quieres desactivarlo de forma explícita: poner `SYNTHETIC_LOOKBACK_YEARS = 0` o eliminar la llamada a `augment_synthetic_2025` en `load_cohort`.

### Identificar las filas sintéticas en el CSV de cohorte exportado

Cualquiera de las dos variantes incluye la columna `synthetic` (True/False) en `output/<variante>/ward_stays_cohort_*.csv`:

```python
import pandas as pd
df = pd.read_csv("demographics/output/predominant_unit/ward_stays_cohort_2019-2025_E073-I073.csv")
print(df["synthetic"].value_counts())
print(df.loc[df["synthetic"], "year_admission"].value_counts())
```

---

## Columnas que produce la query (ambas variantes)

| Columna | Notas |
|---|---|
| `patient_ref`, `episode_ref`, `stay_id` | Identificadores. Las filas sintéticas usan `"SYN2025-…"`. |
| `ou_loc_ref` | Unidad asignada (única por estancia en `per_unit`). |
| `admission_date`, `discharge_date`, `effective_discharge_date` | Fechas del ingreso y alta. |
| `hours_stay`, `days_stay`, `minutes_stay` | Duración. |
| `still_admitted` | `Yes/No`; las filas con `Yes` se excluyen del agregado. |
| `num_movements`, `num_units_visited` | Constantes en `per_unit` (1 unidad por estancia). |
| `had_transfer` | `Yes/No` en `predominant_unit`; siempre `No` en `per_unit`. |
| `year_admission`, `age_at_admission`, `sex`, `nationality`, `natio_ref`, `health_area`, `postcode` | Demografía. |
| `exitus_during_stay`, `exitus_date` | Mortalidad intrahospitalaria + 30/90 d (`_metrics.py`). |
| `has_cirrhosis`, `readmission_24h`, `readmission_72h` | Indicadores clínicos. |
| `procedencia_codigo`, `procedencia` | `dynamic_forms` (UCI form, PROCE_MALA), última valoración por episodio. |
| `from_other_hospital` | `1` si `value_text IN ('20-Altre hospital-', '20-Otro hospital-')`. El formulario UCI migró del catalán al castellano hacia septiembre de 2022 (ver `dynamic_forms/queries/06_diag_proce_mala_e073_i073_yearly.sql`). |
| `synthetic` | Añadida por `_loader.py`; `True` en filas sintéticas, `False` en reales. |

## Notas

- El filtro `still_admitted == "No"` se aplica en `_metrics.compute_summary` para excluir estancias todavía abiertas del análisis agregado.
- Las fechas (`admission_date`, `exitus_date`) llegan como strings con offsets mixtos (CET/CEST). El parseo se hace con `pd.to_datetime(..., utc=True)` para que `.dt.total_seconds()` funcione en `_metrics._mortality`.
- Las unidades E073/I073 están **hardcodeadas** en ambos `_sql.py` y en las SQL exportadas. Para analizar otras unidades, hay que editar los cuatro archivos. El cálculo empírico de camas también las usa (vía `compute_bed_occupancy(units=...)` en los `run.py`).
- La fila **"Ocupación de camas (%)"** se deriva en `_metrics.compute_summary` a partir del DataFrame que produce `_bed_occupancy.compute_bed_occupancy()`, que a su vez consulta `datascope_gestor_prod.movements` directamente. No es una columna producida por la SQL del cohort. Por eso aparece en el HTML/CSV de resumen pero no en el CSV de cohorte. Ver sección "Sobre la fila Ocupación de camas" para los detalles del cálculo y la exclusión de la cama falsa de E073.
