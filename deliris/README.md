# Deliris — vigilancia de delirio en UCI (CAM-ICU)

Módulo para extraer indicadores de **registro de RASS** y **CAM-ICU** en las unidades de cuidados intensivos definidas en las consultas, y generar tablas CSV y figuras a partir de DataNex via Metabase API (`g_movements`, `g_rc`).

La documentación de esquema y tablas relevantes está en `DB_CONTEXT.md` / `DB_CONTEXT_dicts.md` en la raíz del repositorio.

---

## Requisitos

- Python ≥ 3.10, dependencias del proyecto (`requirements.txt`).
- Archivo `.env` con credenciales de Metabase (véase README principal).
- La query `camicu_daily_coverage_excl_deep_rass.sql` usa `WITH RECURSIVE` para expandir días calendario.

---

## Ejecución rápida

Desde la raíz del repositorio:

```bash
# Generar CSV (cada .sql escribe el .csv homónimo en esta carpeta)
python deliris/run_sql.py deliris/camicu_compliance.sql
python deliris/run_sql.py deliris/camicu_positivity.sql
python deliris/run_sql.py deliris/camicu_daily_coverage.sql
python deliris/run_sql.py deliris/camicu_daily_coverage_excl_deep_rass.sql

# Figuras (requiere que existan todos los CSV anteriores)
python deliris/camicu_plots.py
```

`run_sql.py` sin argumentos ejecuta por defecto `camicu_compliance.sql`.

Los CSV suelen estar en `.gitignore` (`*.csv`); hay que regenerarlos en cada entorno.

---

## UCIs incluidas

`E016`, `E103`, `E014`, `E015`, `E037`, `E057`, `E073`, `E043` — mismo filtro en todas las queries del módulo.

---

## Cohorte de estancia UCI (definición común)

Las consultas alinean **movimientos** (`g_movements`) por paciente, episodio y unidad:

- Se **unen** segmentos consecutivos si el hueco entre fin del anterior e inicio del siguiente es **≤ 5 minutos** (misma estancia).
- Para **`camicu_daily_coverage*.sql`**: solo estancias **cerradas** en todas las filas del grupo: `end_date` no nulo y `end_date <= NOW()` en **todos** los segmentos (evita altas abiertas y fechas “centinela” que inflan días).

El campo **`yr`** en cada CSV sigue la definición de esa query (p. ej. año del **turno** elegible en cumplimiento, año del **ingreso** en cobertura diaria, año del **resultado CAM** en positividad). Revisar el `GROUP BY` del SQL si hace falta cotejar con gestión.

---

## Codificación del RASS en `g_rc`

- **`rc_sap_ref = 'SEDACION_RASS'`**
- **Formato antiguo (codificado):** `SEDACION_RASS_3` … `SEDACION_RASS_10` corresponden a RASS **-3 a +4** (como en `camicu_compliance.sql`). `SEDACION_RASS_1` y `_2` se interpretan como **-5** y **-4**.
- **Formato numérico (aprox. desde 2022):** `result_txt` que cumple entero vía `REGEXP` y `CAST(... AS SIGNED)`.

Las queries que excluyen sedación profunda usan **ambos** formatos para detectar **-5 / -4**.

---

## Archivos SQL y CSV

| SQL | CSV | Resumen |
|-----|-----|--------|
| `camicu_compliance.sql` | `camicu_compliance.csv` | Cumplimiento CAM-ICU **por turno** entre turnos con al menos un RASS **elegible** (–3 a +4) en ese mismo turno. Cohorte con `effective_discharge_date` (incluye tramos abiertos vía `COALESCE(end_date, NOW())`). |
| `camicu_positivity.sql` | `camicu_positivity.csv` | Distribución de resultados del CAM-ICU (`DELIRIO_CAM-ICU_1/2/3`) por UCI y año. |
| `camicu_daily_coverage.sql` | `camicu_daily_coverage.csv` | % de estancias **cerradas** con ≥1 CAM-ICU en **cada día calendario** del ingreso (de `DATE(ingreso)` a `DATE(alta)` inclusive). |
| `camicu_daily_coverage_excl_deep_rass.sql` | `camicu_daily_coverage_excl_deep_rass.csv` | Igual idea que la anterior, pero un día **no exige** CAM si ese día consta algún RASS **-5 o -4** (no evaluable). El % principal (`pct_stays_cam_all_evaluable_days`) usa como denominador estancias con **≥1 día evaluable**. Requiere MySQL recursivo para generar la rejilla de días. |

---

## Detalle por consulta (flujo lógico)

### `camicu_compliance.sql`

**Objetivo:** medir, entre los **turnos de enfermería** (mañana / tarde / noche) en los que el RASS ya figura en rango **–3 a +4**, qué parte tiene también un **CAM-ICU** en **ese mismo turno**.

**Pseudoflujo**

1. `all_related_moves` — Filas de `g_movements` en UCIs objetivo, con ventana temporal global y `place_ref` no nulo.
2. `flagged_starts` — Marca nuevo inicio de estancia si el salto respecto al fin efectivo del segmento anterior es **> 5 minutos** (`effective_end_date` = `COALESCE(end_date, NOW())`).
3. `grouped_stays` — Acumula `stay_id` por paciente, episodio y unidad.
4. `cohort` — Una fila por estancia: `admission_date` = primer `start_date`, **`effective_discharge_date` = `MAX(effective_end_date)`** (permite episodios con último tramo aún abierto). Filtro `YEAR(ingreso) ∈ [2018, 2025]`.
5. `rass_eligible` — Hechos `g_rc` con `SEDACION_RASS` en la ventana `[ingreso, alta_efectiva]` y valor **–3…+4** (códigos `_3`…`_10` o entero numérico en texto).
6. `eligible_shifts` — Una fila por `(estancia, shift_date, shift)` con al menos un RASS elegible. `shift_date` / `shift` se derivan de `HOUR(result_date)` (turno noche: mediciones antes de las 8:00 se asocian al **día civil anterior** como en el SQL).
7. `cam_shifts` — Pares distintos `(shift_date, shift)` con `DELIRIO_CAM-ICU` en la misma ventana.
8. **SELECT final** — `LEFT JOIN` de turnos elegibles a turnos CAM por clave de estancia + fecha de turno + franja. Agregación por **`ou_loc_ref`**, **`YEAR(shift_date)`** y **`shift`**.  
   - Columnas clave: `eligible_shifts`, `shifts_with_cam`, `pct_compliance`.

**`yr` en el CSV:** año del **`shift_date`**, no necesariamente el año de ingreso.

**Límite metodológico:** No entran en el denominador turnos **sin** RASS o con RASS fuera de –3…+4 en esa franja.

---

### `camicu_positivity.sql`

**Objetivo:** entre **todos** los registros CAM-ICU dentro de las estancias de la cohorte, describir la proporción de **positivos / negativos / otros** por UCI y año.

**Pseudoflujo**

1. Cadenas `all_related_moves` → `flagged_starts` → `grouped_stays` → `cohort` **iguales en espíritu** a cumplimiento: ventana **`[admission_date, effective_discharge_date]`**.
2. `cam_results` — Registros `DELIRIO_CAM-ICU` en esa ventana; clasificación:
   - `DELIRIO_CAM-ICU_2` → positivo (delirio presente),
   - `DELIRIO_CAM-ICU_1` → negativo,
   - `DELIRIO_CAM-ICU_3` → otros / no valorable,
   - cualquier otro `result_txt` → `unknown` (en el agregado no se separa en columnas dedicadas más allá de lo que haga el `CASE`).
3. **SELECT final** — `GROUP BY ou_loc_ref`, **`YEAR(result_date)`**.  
   - Columnas: `total_cam`, `n_positive`, `n_negative`, `n_other`, `pct_positive`, `pct_negative`.

**`yr` en el CSV:** año de **`result_date`** del CAM, no del ingreso.

---

### `camicu_daily_coverage.sql`

**Objetivo:** entre estancias **cerradas** (ver cohorte abajo), proporción de estancias con **≥1 CAM-ICU cada día calendario** que dura la estancia.

**Pseudoflujo**

1. `all_related_moves` … `grouped_stays` — Igual construcción de estancia.
2. `cohort` — `admission_date`, **`discharge_date = MAX(end_date)`** (solo fechas reales). Filtros:
   - `YEAR(ingreso) ∈ [2018, 2025]`,
   - **todos** los segmentos con `end_date IS NOT NULL` y `end_date <= NOW()` (estancia cerrada de verdad),
   - `n_icu_calendar_days = DATEDIFF(DATE(alta), DATE(ingreso)) + 1`.
3. `per_stay` — `LEFT JOIN` a `g_rc` CAM en `[ingreso, alta]`; **`days_with_cam = COUNT(DISTINCT DATE(result_date))`**.
4. **SELECT final** — Por `ou_loc_ref` y **`YEAR(admission_date)`**:
   - Cumple “cobertura total” si `days_with_cam >= n_icu_calendar_days`.
   - `pct_stays_cam_all_days` = % sobre **todas** las estancias del grupo.
   - También informa “algún día con CAM” y la media de % de días con CAM (`avg_pct_calendar_days_with_cam`).

**`yr` en el CSV:** año del **ingreso** (`admission_date`).

---

### `camicu_daily_coverage_excl_deep_rass.sql`

**Objetivo:** como la anterior, pero un **día calendario no obliga** a tener CAM si ese día hay al menos un RASS **–5 o –4** (ambos formatos de registro). Solo se exige CAM en días **evaluables**.

**Pseudoflujo**

1. `WITH RECURSIVE nums` — Enteros **0…800** (suficiente para cubrir `DATEDIFF` de estancia; estancias &gt; 801 días quedarían truncadas si las hubiera).
2. Misma cadena `all_related_moves` … `cohort` que `camicu_daily_coverage.sql` (cerrada, `MAX(end_date)`).
3. `stay_calendar_days` — Producto de cada estancia con `nums`: una fila por **día civil** desde `DATE(ingreso)` hasta `DATE(alta)` inclusive (`DATE_ADD(..., INTERVAL n DAY)` con `n <= DATEDIFF`).
4. `rass_deep_sedation_day` — Pares distintos `(estancia, cal_day)` donde existe RASS –5/–4 ese día (`DATE(result_date) = cal_day`).
5. `cam_days` — Pares distintos `(estancia, cal_day)` con al menos un CAM ese día.
6. `per_stay` — Para cada estancia:
   - `n_evaluable_days` = filas de calendario **sin** fila en `rass_deep_sedation_day` ese día,
   - `n_evaluable_days_with_cam` = entre evaluables, días con fila en `cam_days`.
   - Criterio de éxito: `n_evaluable_days >= 1` y `n_evaluable_days_with_cam >= n_evaluable_days`.
7. **SELECT final** — `GROUP BY ou_loc_ref`, **`YEAR(admission_date)`**:
   - `pct_stays_cam_all_evaluable_days` = entre estancias con **≥1 día evaluable** (denominador `n_stays_with_evaluable_day`),
   - `n_stays_no_evaluable_day` = estancias solo con días –5/–4 (o sin días “libres” según regla).

**`yr` en el CSV:** año del **ingreso**.

**MySQL:** si algún entorno limitara la recursión, revisar `cte_max_recursion_depth` (ha de ser ≥ 801 para la tabla de enteros).

---

## Scripts

| Archivo | Función |
|---------|--------|
| `run_sql.py` | Lee un `.sql`, ejecuta vía `connection.execute_query`, guarda `mismo_nombre.csv`. |
| `camicu_plots.py` | Carga los CSV necesarios y escribe figuras en `plots/`. Falla con mensaje claro si falta algún CSV. |

---

## Figuras (`plots/`)

| PNG | Fuente CSV | Pregunta que responde |
|-----|------------|------------------------|
| `camicu_compliance_global_by_shift.png` | `camicu_compliance.csv` | Entre turnos donde **hay** RASS elegible (–3 a +4), ¿en qué % también hay CAM-ICU **en ese mismo turno**? Línea negra global; discontinuas por turno (mañana/tarde/noche). |
| `camicu_positivity_stacked_by_icu.png` | `camicu_positivity.csv` | Mezcla de resultados CAM-ICU por UCI en los **tres últimos años** de los datos (apilado). |
| `camicu_positivity_trend_by_year.png` | `camicu_positivity.csv` | Evolución del % de registros CAM-ICU **positivos** por UCI y año (+ global). |
| `camicu_daily_coverage_by_icu.png` | `camicu_daily_coverage.csv` | % de estancias cerradas con CAM-ICU **al menos una vez cada día calendario** de la estancia. La línea negra agrupa todas las UCIs con media **ponderada** por número de estancias. |
| `camicu_daily_coverage_excl_deep_rass_by_icu.png` | `camicu_daily_coverage_excl_deep_rass.csv` | Igual que la anterior pero ignorando días con RASS –5/–4. Denominador del % por UCI: estancias con ≥1 día evaluable; la línea negra usa \(\sum\) cumplen / \(\sum\) con día evaluable. |

Textos de ejes y títulos en las figuras están en **inglés** (convención del código del módulo).

---

## Interpretación clínica (límites)

- Los indicadores miden **lo que consta en la base de datos**, no la práctica no registrada.
- El **cumplimiento por turno** no incluye pacientes sin RASS en ese turno; la **cobertura diaria** no condiciona al RASS excepto en la variante `excl_deep_rass`.
- Las estancias con **solo** días –5/–4 pueden quedar con **cero días evaluables**; aparecen en `n_stays_no_evaluable_day` en el CSV correspondiente.

---

## Cierre del análisis

Este README resume el alcance del módulo **deliris** tal como queda cerrado: cuatro consultas de extracción, cuatro CSV, `run_sql.py`, `camicu_plots.py` y cinco figuras estándar. Incluye la tabla resumen, la interpretación de las figuras y el **detalle por consulta** (pseudoflujo y definición de `yr`). Cualquier ampliación (p. ej. nuevas UCIs, umbrales RASS, estancias muy largas &gt; 800 días en la query recursiva, u otra fuente) debe actualizar las queries y este documento en consecuencia.
