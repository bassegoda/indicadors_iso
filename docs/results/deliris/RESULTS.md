# Deliris — resultados (CAM-ICU)

Documentación de los resultados obtenidos en el módulo `deliris/` a partir de los CSV (`camicu_compliance.csv`, `camicu_positivity.csv`, `camicu_daily_coverage.csv`, `camicu_daily_coverage_excl_deep_rass.csv`) y de las cinco figuras en `plots/`. Todos los agregados se calculan limitando a `yr ≤ 2025`, igual que `camicu_plots.py`.

---

## Fuente de los datos

Todos los datos presentados en este informe se han extraído de la **base de datos clínica DataNex** del Hospital Clínic de Barcelona, a través de la **API de Metabase** (`https://metabase.clinic.cat`). Las consultas se ejecutan sobre la instancia AWS/Athena (dialecto Trino/Presto) en el esquema `datascope_gestor_prod`. Las tablas implicadas son:

- `movements` — episodios y movimientos entre unidades, para definir la cohorte de estancia UCI (segmentos consecutivos unidos si el hueco entre ellos es ≤ 5 minutos).
- `rc` — registros clínicos: `SEDACION_RASS` para el RASS y `DELIRIO_CAM-ICU` para los resultados del CAM-ICU.

El detalle metodológico (definición de cohorte, codificación del RASS, ventanas temporales, criterios de inclusión por turno y por día calendario) está documentado en `deliris/README.md` y en cada archivo `.sql` del módulo. Los CSV de partida fueron generados con `deliris/run_sql.py` y las figuras con `deliris/camicu_plots.py`.

---

## Alcance del análisis

- **Unidades incluidas (8 UCIs):** `E014`, `E015`, `E016`, `E037`, `E043`, `E057`, `E073`, `E103`.
- **Años cubiertos:** 2018–2025 (algunas UCIs entran más tarde — p.ej. `E037` desde 2021, `E043` desde 2019).
- **Volumen global del periodo:**

  | Indicador | Denominador | N |
  |---|---|---|
  | Cumplimiento CAM-ICU por turno | turnos elegibles (RASS −3…+4) | **59 108** turnos (de los cuales 6 528 con CAM → 11,0 %) |
  | Positividad CAM-ICU | registros CAM-ICU | **223 066** registros |
  | Cobertura diaria | estancias UCI cerradas | **23 777** estancias |
  | Cobertura diaria (excl. RASS −5/−4) | estancias con ≥1 día evaluable | **22 777** estancias (1 000 estancias sin ningún día evaluable) |

> Nota: el CSV de positividad contiene una fila aislada `E073, yr=2026, total_cam=5` que se descarta (probable centinela de fechas). Las cifras de arriba ya están filtradas.

---

## Figura 1 — Cumplimiento CAM-ICU por turno (global)

**Archivo:** `plots/camicu_compliance_global_by_shift.png`
**Fuente:** `camicu_compliance.csv`
**Pregunta:** Entre los turnos de enfermería (M = mañana 8–15 h, A = tarde 15–22 h, N = noche 22–8 h) en los que ya **consta** un RASS en rango evaluable (−3 a +4), ¿qué proporción tiene también un CAM-ICU registrado en **el mismo turno**?

**Lo que muestra el gráfico:**
- Línea negra continua: media ponderada de las 8 UCIs por año.
- Tres líneas discontinuas (azul/naranja/morado): mismo cálculo desagregado por turno M/A/N.

**Resultados clave (todas las UCIs, 2018–2025):**

| Año | Turnos elegibles | Turnos con CAM | % cumplimiento |
|---|---:|---:|---:|
| 2018 | 4 500 | 581 | 12,9 % |
| 2019 | 4 826 | 485 | 10,0 % |
| 2020 | 8 627 | 996 | 11,5 % |
| 2021 | 14 479 | 1 658 | 11,5 % |
| 2022 | 7 911 | 1 024 | 12,9 % |
| 2023 | 5 840 | 598 | 10,2 % |
| 2024 | 7 038 | 682 | 9,7 % |
| 2025 | 5 887 | 504 | 8,6 % |

**Por turno (acumulado 2018–2025):** Mañana 9,7 % · Tarde 11,4 % · **Noche 12,1 %** (el turno mejor cumplido).

**Por UCI (acumulado 2018–2025):**

| UCI | Elegibles | Con CAM | % |
|---|---:|---:|---:|
| E103 | 7 482 | 1 758 | **23,5 %** |
| E016 | 5 060 | 676 | 13,4 % |
| E057 | 6 873 | 846 | 12,3 % |
| E015 | 5 623 | 665 | 11,8 % |
| E014 | 6 496 | 575 | 8,9 % |
| E043 | 16 883 | 1 451 | 8,6 % |
| E037 | 2 165 | 154 | 7,1 % |
| E073 | 8 526 | 403 | **4,7 %** |

**Lectura:** el cumplimiento global se mueve siempre por debajo del 13 % y muestra una **caída progresiva desde 2022** (13 %) hasta 2025 (≈ 9 %). El turno noche es el que más registra; mañana el que menos. La UCI con cumplimiento más alto es **E103** y la más baja **E073**.

---

## Figura 2 — Mezcla de resultados CAM-ICU por UCI (2023–2025)

**Archivo:** `plots/camicu_positivity_stacked_by_icu.png`
**Fuente:** `camicu_positivity.csv` (filtrado a los **3 últimos años**, 2023–2025).
**Pregunta:** Entre los registros CAM-ICU de los últimos 3 años, ¿qué proporción es delirio presente / ausente / no valorable?

**Codificación:** `DELIRIO_CAM-ICU_2` = positivo (delirio presente, naranja); `_1` = negativo (verde); `_3` = otros / no valorable (gris).

**Resultados (2023–2025, agregado por UCI):**

| UCI | Total CAM | % positivos | % negativos | % otros |
|---|---:|---:|---:|---:|
| E014 | 4 492 | 78,6 % | 12,7 % | 8,7 % |
| E015 | 6 696 | 87,8 % | 8,9 % | 3,4 % |
| E016 | 27 105 | 93,0 % | 5,9 % | 1,0 % |
| E037 | 5 128 | 85,0 % | 13,8 % | 1,2 % |
| E043 | 6 729 | 84,4 % | 15,1 % | 0,5 % |
| E057 | 2 291 | 87,3 % | 12,3 % | 0,5 % |
| E073 | 8 234 | 87,1 % | 12,7 % | 0,3 % |
| E103 | 35 542 | **94,5 %** | 5,1 % | 0,4 % |

**Lectura:** En todas las UCIs, la **mayoría** de los CAM-ICU registrados resultan positivos (rango 79–95 %). E103 y E016 son las más extremas (>93 %); E014 destaca por una proporción no despreciable de "otros / no valorable" (≈9 %). La proporción tan alta de positivos sugiere que el CAM-ICU se registra preferentemente cuando hay sospecha clínica, no como cribado universal.

---

## Figura 3 — Tendencia anual de positividad CAM-ICU por UCI

**Archivo:** `plots/camicu_positivity_trend_by_year.png`
**Fuente:** `camicu_positivity.csv`
**Pregunta:** ¿Cómo evoluciona el % de CAM-ICU positivos por UCI a lo largo del tiempo?

**Lo que muestra:** una línea por UCI (8 colores) más una línea negra global con marcadores en diamante. Eje Y entre 50 % y 105 %.

**Resultados globales (todas las UCIs):**

| Año | Registros CAM | % positivo |
|---|---:|---:|
| 2018 | 19 828 | 90,7 % |
| 2019 | 23 775 | 90,4 % |
| 2020 | 26 179 | 89,0 % |
| 2021 | 26 718 | 89,9 % |
| 2022 | 30 349 | 91,1 % |
| 2023 | 34 664 | 89,8 % |
| 2024 | 34 236 | 91,7 % |
| 2025 | 27 317 | 91,3 % |

**Acumulado del periodo:** 223 066 registros, 201 884 positivos → **90,5 %** positividad global.

**Lectura:** la positividad global se mantiene muy estable (89–92 %) durante 8 años. Las UCIs se mueven en bandas: **E103 y E016** con tendencia ascendente hacia ≈ 95–97 % en 2024–2025; **E014 y E073** las más bajas (74–88 %). Los puntos extremos (E043 = 100 % en 2019 con n = 322; E043 cae a 72,6 % en 2025; E073 = 20 % en 2026 con n = 5) son artefactos de denominadores pequeños y no reflejan cambios clínicos reales.

---

## Figura 4 — Cobertura diaria CAM-ICU en estancias UCI cerradas

**Archivo:** `plots/camicu_daily_coverage_by_icu.png`
**Fuente:** `camicu_daily_coverage.csv`
**Pregunta:** De las **estancias UCI cerradas** (alta real registrada), ¿qué porcentaje tiene **al menos un CAM-ICU cada día calendario** del ingreso?

**Lo que muestra:** una línea por UCI más línea negra con la media **ponderada** por estancias.

**Resultados globales (8 UCIs, 23 777 estancias cerradas 2018–2025):**

| Año | Estancias | Con CAM todos los días | Con CAM algún día | % todos | % algún |
|---|---:|---:|---:|---:|---:|
| 2018 | 2 732 | 227 | 989 | 8,3 % | 36,2 % |
| 2019 | 3 107 | 282 | 1 094 | 9,1 % | 35,2 % |
| 2020 | 3 004 | 334 | 1 377 | 11,1 % | 45,8 % |
| 2021 | 3 076 | 365 | 1 454 | 11,9 % | 47,3 % |
| 2022 | 3 140 | 485 | 1 506 | 15,4 % | 48,0 % |
| 2023 | 3 140 | 401 | 1 541 | 12,8 % | 49,1 % |
| 2024 | 3 036 | 419 | 1 501 | 13,8 % | 49,4 % |
| 2025 | 2 542 | 393 | 1 289 | 15,5 % | 50,7 % |

**Acumulado del periodo:** 23 777 estancias → 2 906 con CAM **todos** los días (12,2 %), 10 751 con CAM algún día (45,2 %).

**Por UCI (acumulado):**

| UCI | Estancias | % todos los días | % algún día |
|---|---:|---:|---:|
| E103 | 4 163 | **26,2 %** | **79,0 %** |
| E016 | 4 709 | 19,3 % | 44,7 % |
| E057 | 1 421 | 14,3 % | 53,3 % |
| E015 | 2 369 | 9,3 % | 50,5 % |
| E037 | 588 | 9,0 % | 44,2 % |
| E043 | 5 842 | 4,4 % | 21,3 % |
| E014 | 1 402 | 4,2 % | 45,6 % |
| E073 | 3 283 | **3,6 %** | 38,4 % |

**Lectura:** la cobertura "completa" diaria pasa del 8 % en 2018 al 15–16 % en 2024–2025 (mejora gradual). E103 sigue claramente por delante (≈ 28 % en 2025) y E016 sube hasta 37 % en 2025. E043, E057, E073, E037 quedan por debajo del 10 %. Más de la mitad de las estancias **no tienen ni un solo CAM-ICU** registrado en algún día (denominador "algún día" = 45 %).

---

## Figura 5 — Cobertura diaria excluyendo días con RASS −5/−4

**Archivo:** `plots/camicu_daily_coverage_excl_deep_rass_by_icu.png`
**Fuente:** `camicu_daily_coverage_excl_deep_rass.csv`
**Pregunta:** Igual que la figura 4 pero **descontando** los días en los que el paciente está en sedación profunda (RASS −5 o −4) — días en los que el CAM-ICU es no valorable. El denominador del % por UCI es **estancias con ≥1 día evaluable**.

**Resultados globales:**

- 23 777 estancias totales · **22 777** con ≥1 día evaluable · **1 000** estancias enteras no evaluables (4,2 %).
- 4 376 estancias cumplen CAM en **todos** sus días evaluables → **19,2 %** global del periodo.

| Año | Estancias evaluables | Cumplen | % |
|---|---:|---:|---:|
| 2018 | 2 599 | 442 | 17,0 % |
| 2019 | 2 967 | 488 | 16,4 % |
| 2020 | 2 853 | 546 | 19,1 % |
| 2021 | 2 906 | 570 | 19,6 % |
| 2022 | 3 050 | 625 | 20,5 % |
| 2023 | 3 060 | 539 | 17,6 % |
| 2024 | 2 908 | 620 | 21,3 % |
| 2025 | 2 434 | 546 | 22,4 % |

**Por UCI (acumulado):**

| UCI | Estancias eval. | Sin día eval. | Cumplen | % |
|---|---:|---:|---:|---:|
| E103 | 3 932 | 231 | 2 054 | **52,2 %** |
| E016 | 4 530 | 179 | 1 077 | 23,8 % |
| E057 | 1 352 | 69 | 265 | 19,6 % |
| E015 | 2 251 | 118 | 312 | 13,9 % |
| E037 | 572 | 16 | 75 | 13,1 % |
| E043 | 5 628 | 214 | 356 | 6,3 % |
| E014 | 1 344 | 58 | 80 | 6,0 % |
| E073 | 3 168 | 115 | 157 | **5,0 %** |

**Lectura:** al descontar los días no valorables, la cifra global sube del 12 % al **19 %** (y a 22 % en 2025). E103 mejora muchísimo (de 26 % a 52 %), confirmando que parte de su carga eran días de sedación profunda. E016 también escala hasta ~45 % en 2025. Las UCIs digestivas/respiratorias (E073, E014, E043) siguen por debajo del 10 % incluso con el ajuste — es un problema real de registro, no de pacientes inevaluables.

---

## Resumen ejecutivo

- **Cohorte total analizada:** 8 UCIs (E014, E015, E016, E037, E043, E057, E073, E103); 2018–2025; **23 777 estancias UCI cerradas**, **223 066 registros CAM-ICU** y **59 108 turnos elegibles** evaluados.
- **Cumplimiento por turno (RASS in range):** 11,0 % global del periodo, con tendencia descendente desde 2022. Turno noche el mejor (12,1 %), mañana el peor (9,7 %).
- **Positividad CAM-ICU:** 90,5 % de los CAM-ICU registrados son positivos, estable a lo largo de 8 años. Sugiere registro selectivo (por sospecha) más que cribado universal.
- **Cobertura diaria completa:** 12,2 % global (15 % en 2025) si se exigen todos los días calendario; sube a 19,2 % (22 % en 2025) si se descuentan días con RASS −5/−4.
- **Heterogeneidad entre UCIs muy marcada:** E103 lidera en cumplimiento, cobertura y positividad; E073 y E014 son las que más espacio de mejora tienen en registro.

---

## Limitaciones (recordatorio)

- Mide **lo que consta en DataNex**, no la práctica no registrada.
- El cumplimiento por turno **solo** considera turnos con RASS −3…+4; turnos sin RASS no entran en el denominador.
- La cobertura diaria base no condiciona al RASS — un paciente sedado profundo cuenta como "día sin CAM" en la figura 4 pero no en la figura 5.
- Estancias enteramente con RASS −5/−4 (1 000 en el periodo) no aportan numerador ni denominador en la figura 5.
