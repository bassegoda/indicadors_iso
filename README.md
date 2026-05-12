# Indicadores ISO

> Clinical quality indicators from Hospital Clínic de Barcelona via Metabase API (DataNex on AWS Athena). Each module extracts, analyses, and exports a specific indicator as CSV / HTML / PDF.

## Inicio Rápido

```bash
# 1. Clona el repositorio
git clone https://github.com/bassegoda/indicadors_iso.git
cd indicadors_iso

# 2. Crea el archivo .env en la raíz de OneDrive (ver sección "Conexión a la Base de Datos")

# 3. Crea un venv e instala el paquete en modo editable (requiere Python ≥ 3.10)
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows
pip install -e .              # o `pip install -e .[dev]` para incluir pytest + ruff

# 4. Ejecuta cualquier script
python demographics/predominant_unit/run.py
```

`pip install -e .` instala el paquete `indicadors_iso` apuntando a `src/indicadors_iso/`. Los scripts en `demographics/`, `deliris/`, etc. son *shims* finos que importan el código real del paquete instalado.

## Estructura del Proyecto

```
indicadors_iso/
├── src/indicadors_iso/      # Paquete Python instalable
│   ├── connection.py        # API de Metabase
│   ├── _paths.py            # REPO_ROOT, OUTPUT_DIR, module_output_dir(...)
│   ├── data_quality/        # ETL completeness cross-year
│   ├── demographics/        # Cohorte E073+I073 (per_unit, predominant_unit, SOFA, autopsy, nutrition)
│   ├── deliris/             # CAM-ICU compliance / positivity / coverage
│   ├── drg/                 # Complejidad asistencial (DRG, SOI, ROM, CMI)
│   ├── dynamic_forms/       # Queries SQL exploratorias sobre formularios dinámicos
│   ├── micro/rectal_mdr/    # Aislamientos rectal-MDR por unidad
│   └── nutritions/          # Nutrición enteral / parenteral
├── data_quality/  demographics/  deliris/  drg/  dynamic_forms/  micro/  nutritions/
│                            # Shims que mantienen `python <módulo>/<script>.py` funcionando
├── dictionaries/datanex/    # Catálogos DataNex (CSV + SQL de regeneración)
├── docs/                    # DB_CONTEXT_AWS.md y notas de indicadores pendientes
├── tests/                   # Suite pytest
├── output/                  # Carpeta centralizada (gitignored) — todos los outputs
├── pyproject.toml           # Configuración del paquete + ruff
├── requirements.txt         # Versiones pinneadas
├── requirements-dev.txt     # pytest + ruff
└── CLAUDE.md                # Instrucciones para Claude Code
```

Cada análisis genera sus resultados en `output/<módulo>/…` (en lugar del antiguo `<módulo>/output/`).

| Carpeta | Descripción |
|---------|-------------|
| **data_quality/** | Comparación de completitud `movements` y `labs` entre dos años: totales, YTD, serie mensual y diaria (heatmap), filas/episodio, episodios huérfanos, frescura de `load_date`. Salidas: CSVs + reporte HTML con gráficas. |
| **demographics/** | Tabla demográfica y de resultados de estancias en E073+I073 (`predominant_unit/run.py` y `per_unit/run.py`). Estructura modular: `_sql.py` (consulta SQL), `_metrics.py` (cálculo de métricas), `_report.py` (generación HTML/CSV). El submódulo `demographics/sofa/` aporta el cálculo de SOFA al ingreso (Vincent 1996) y se mergea en el reporte de `per_unit` (E073). [Ver SOFA →](src/indicadors_iso/demographics/sofa/README.md) |
| **deliris/** | Indicadores CAM-ICU / delirio en UCI. [Documentación →](src/indicadors_iso/deliris/README.md) |
| **drg/** | Informe de complejidad asistencial basado en DRGs: PDF multipágina con indicadores de severidad (SOI), riesgo de mortalidad (ROM) y peso DRG (Case Mix Index). |
| **dynamic_forms/** | Consultas SQL sobre formularios dinámicos. Ejecución con `run_queries.py`; queries en `src/indicadors_iso/dynamic_forms/queries/`. [Ver README →](src/indicadors_iso/dynamic_forms/README.md) |
| **nutritions/** | Análisis de nutrición enteral y parenteral. |
| **micro/rectal_mdr/** | Aislamientos rectal-MDR (E073, I073), per-unit. |
| **dictionaries/datanex/** | Catálogos de DataNex descargados como CSV (lab, rc, dynamic_forms, prescriptions, administrations, perfusions). Sirven para hacer grep local de los `_ref` necesarios sin lanzar queries exploratorias; cada `0X_*.sql` regenera su CSV. |

---

## Conexión a la Base de Datos

La conexión se gestiona en `src/indicadors_iso/connection.py` y se importa con `from indicadors_iso.connection import execute_query`. Usa la API de Metabase contra DataNex (AWS Athena).

### Configuración

Las credenciales se almacenan en un archivo `.env` ubicado en la **raíz de OneDrive**. El sistema detecta automáticamente la ruta de OneDrive tanto en Windows como en macOS.

> [!IMPORTANT]
> El archivo `.env` está excluido del repositorio vía `.gitignore`. Nunca subas credenciales al repositorio.

### Archivo `.env`

Crea un archivo `.env` en la raíz de OneDrive con el siguiente formato:

```env
METABASE_URL=https://metabase.clinic.cat
METABASE_EMAIL=tu_email
METABASE_PASSWORD=tu_contraseña
METABASE_DATABASE_NAME=nombre_base_de_datos
```

**Importante**: Cuando cambie la contraseña, actualiza únicamente la línea `METABASE_PASSWORD=` en este archivo. El archivo se sincronizará automáticamente con OneDrive en todos tus ordenadores.

### Uso en los Scripts

Tras `pip install -e .`, los imports son directos:

```python
from indicadors_iso.connection import execute_query, execute_query_yearly
from indicadors_iso._paths import OUTPUT_DIR, module_output_dir
```

## Requisitos

- **Python ≥ 3.10** (desarrollado con Python 3.12)
- Instala el paquete y dependencias con `pip install -e .` (añade `[dev]` para pytest + ruff).

## Ejecución

Todos los scripts originales siguen funcionando desde la raíz del repo:

```bash
python demographics/predominant_unit/run.py
python demographics/per_unit/run.py
python data_quality/completeness_2024_vs_2025.py
python deliris/run_sql.py camicu_compliance
python deliris/run_sql.py camicu_positivity
python deliris/run_sql.py camicu_daily_coverage
python deliris/run_sql.py camicu_daily_coverage_excl_deep_rass
python deliris/camicu_plots.py
python nutritions/nutritions.py
python drg/drg_complexity_report.py
python dynamic_forms/run_queries.py --list
python micro/rectal_mdr/run.py
```

Los scripts solicitan interactivamente los parámetros necesarios (año, unidades, etc.) y generan los resultados en `output/<módulo>/`.

## Tests

```bash
pytest                                        # ejecuta la suite (no requiere DB)
python tests/test_metabase_row_cap.py         # comprueba el cap silencioso de 2000 filas (requiere DB)
```
