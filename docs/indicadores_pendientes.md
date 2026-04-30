# Indicadores pendientes de UCI (DataNex)

Este documento recoge los indicadores de calidad todavia no implementados en el repositorio, con un formato comun para facilitar su diseno, priorizacion y validacion.

## Estados de trabajo

- `Pendiente`: no iniciado
- `En diseno`: definicion clinica y tecnica en preparacion
- `En SQL`: query en desarrollo
- `Validacion`: contrastando resultados con equipo clinico
- `En produccion`: indicador operativo y revisado

## Prioridad inicial

Escala sugerida:

- `Alta`: impacto clinico/seguridad y factibilidad alta
- `Media`: impacto relevante o dependencia de definiciones
- `Baja`: impacto menor o dependencias externas importantes

## Backlog de indicadores

### 1) Gravedad al ingreso y mortalidad ajustada por gravedad

- **Nombre corto**: Gravedad + mortalidad ajustada
- **Objetivo**: incorporar una escala de gravedad (SOFA, SAPS o APACHE) al ingreso para estimar mortalidad ajustada por riesgo.
- **Definicion clinica (pendiente de cerrar)**:
  - definir escala principal (SOFA/SAPS/APACHE) y ventana temporal de captura al ingreso.
  - definir mortalidad objetivo (intra-UCI, hospitalaria, 30 dias).
- **Fuente DataNex**: pendiente de mapear tablas/campos de constantes, analiticas y variables fisiologicas.
- **Numerador/denominador**:
  - numerador: muertes observadas en cohorte.
  - denominador: muertes esperadas segun modelo de riesgo.
- **Salida esperada**: O/E (observada/esperada), mortalidad ajustada y tendencia temporal.
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 2) Cateteres retirados por sospecha de infeccion

- **Nombre corto**: Retirada de cateter por sospecha
- **Objetivo**: monitorizar retiradas no programadas de cateter motivadas por sospecha infecciosa.
- **Definicion clinica (pendiente de cerrar)**: criterio de "sospecha" (motivo de retirada, sospecha documentada, solicitud de cultivo de punta, etc.).
- **Fuente DataNex**: pendiente de mapear procedimientos/dispositivos y motivo de retirada.
- **Numerador/denominador**:
  - numerador: cateteres retirados por sospecha.
  - denominador: total de cateteres retirados o total de dias-cateter (a validar).
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 3) Infeccion de cateter

- **Nombre corto**: Bacteriemia/infeccion relacionada con cateter
- **Objetivo**: estimar incidencia de infeccion asociada a cateter.
- **Definicion clinica (pendiente de cerrar)**: criterios CDC/ENVIN o protocolo local (microbiologia + clinica + exclusiones).
- **Fuente DataNex**: pendiente de mapear microbiologia, hemocultivos, dispositivos y episodios.
- **Numerador/denominador**:
  - numerador: episodios de infeccion relacionada con cateter.
  - denominador: 1000 dias-cateter.
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 4) ITU por sonda urinaria

- **Nombre corto**: ITU-SU
- **Objetivo**: medir infeccion del tracto urinario asociada a sonda.
- **Definicion clinica (pendiente de cerrar)**: criterio diagnostico de ITU asociada a sonda (micro + clinica + tiempo de exposicion).
- **Fuente DataNex**: pendiente de mapear sondaje urinario, urocultivos y diagnosticos.
- **Numerador/denominador**:
  - numerador: episodios ITU-SU.
  - denominador: 1000 dias-sonda.
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 5) Infecciones por MDRO

- **Nombre corto**: Infeccion por microorganismo multirresistente
- **Objetivo**: vigilar infecciones por MDRO durante estancia UCI.
- **Definicion clinica (pendiente de cerrar)**: listado de MDRO valido (segun protocolo local) y criterio de infeccion (no colonizacion).
- **Fuente DataNex**: pendiente de mapear microbiologia y antibiogramas.
- **Numerador/denominador**:
  - numerador: episodios de infeccion por MDRO.
  - denominador: 1000 estancias o 1000 dias-UCI (a definir).
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 6) Colonizaciones por MDRO

- **Nombre corto**: Colonizacion por MDRO
- **Objetivo**: medir adquisicion/prevalencia de colonizacion por MDRO.
- **Definicion clinica (pendiente de cerrar)**: cribado de ingreso vs adquisicion intrahospitalaria, localizacion anatomica y reglas temporales.
- **Fuente DataNex**: pendiente de mapear cultivos de vigilancia y fechas de ingreso.
- **Numerador/denominador**:
  - numerador: pacientes con colonizacion por MDRO.
  - denominador: pacientes ingresados o 1000 pacientes-dia (a definir).
- **Estado**: `Pendiente`
- **Prioridad**: `Media`
- **Responsable**: `Por asignar`

### 7) Evaluacion de dolor y delirium

- **Nombre corto**: Dolor + delirium
- **Objetivo**: monitorizar adherencia a evaluacion sistematica de dolor y delirium.
- **Definicion clinica (pendiente de cerrar)**:
  - dolor: escala validada (NRS/BPS/CPOT), frecuencia minima por turno.
  - delirium: CAM-ICU o equivalente y frecuencia minima.
- **Fuente DataNex**: pendiente de mapear formularios dinamicos/enfermeria.
- **Numerador/denominador**:
  - numerador: pacientes-dias con evaluacion completa segun protocolo.
  - denominador: total de pacientes-dias elegibles.
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 8) Nutricion enteral y parenteral

- **Nombre corto**: Soporte nutricional (EN/PN)
- **Objetivo**: evaluar inicio, cobertura y adecuacion de soporte nutricional.
- **Definicion clinica (pendiente de cerrar)**: criterios de indicacion, tiempos de inicio y objetivos calórico-proteicos.
- **Fuente DataNex**: pendiente de mapear modulo `nutritions`, prescripcion y administracion.
- **Numerador/denominador**:
  - numerador: pacientes que cumplen objetivo nutricional en ventana definida.
  - denominador: pacientes elegibles para soporte nutricional.
- **Estado**: `Pendiente`
- **Prioridad**: `Media`
- **Responsable**: `Por asignar`

### 9) Autoextubaciones

- **Nombre corto**: Autoextubacion
- **Objetivo**: cuantificar eventos de retirada no planificada de tubo endotraqueal.
- **Definicion clinica (pendiente de cerrar)**: evento de autoextubacion y exclusiones (extubacion programada/fallo tecnico).
- **Fuente DataNex**: pendiente de mapear ventilacion, procedimientos y eventos de incidente.
- **Numerador/denominador**:
  - numerador: numero de autoextubaciones.
  - denominador: 1000 dias de ventilacion mecanica.
- **Estado**: `Pendiente`
- **Prioridad**: `Alta`
- **Responsable**: `Por asignar`

### 10) Necropsias

- **Nombre corto**: Tasa de necropsias
- **Objetivo**: medir proporcion de fallecimientos con necropsia realizada.
- **Definicion clinica (pendiente de cerrar)**: necropsia clinica completa/parcial y criterios de inclusion.
- **Fuente DataNex**: pendiente de mapear modulo `necropsy` y estado de fallecimiento.
- **Numerador/denominador**:
  - numerador: fallecimientos con necropsia.
  - denominador: total de fallecimientos en UCI.
- **Estado**: `Pendiente`
- **Prioridad**: `Media`
- **Responsable**: `Por asignar`

## Siguiente paso recomendado

Para avanzar rapido, cerrar primero estos 3 bloques:

1. Definicion clinica exacta por indicador (1 hoja por indicador, validada con el equipo).
2. Mapeo de campos DataNex (tabla/campo/filtro/fecha-evento).
3. Criterio temporal comun (por ingreso, por estancia, por paciente-dia, por 1000 dispositivo-dia).
