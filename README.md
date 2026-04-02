# Indicadores ISO

> Clinical quality indicators from Hospital Clínic de Barcelona's MySQL database (DataNex). Each module extracts, analyses, and exports a specific indicator as CSV/PDF.

Proyecto para obtener indicadores clínicos a partir de una base de datos MySQL del Hospital Clínic de Barcelona.

## Inicio Rápido

```bash
# 1. Clona el repositorio
git clone https://github.com/bassegoda/indicadors_iso.git
cd indicadors_iso

# 2. Crea el archivo .env en la raíz de OneDrive (ver sección "Conexión a la Base de Datos")

# 3. Instala las dependencias (requiere Python ≥ 3.10)
pip install -r requirements.txt

# 4. Ejecuta cualquier script
python demographics/ward_stays_demo.py
```

## Estructura del Proyecto

Cada subcarpeta contiene análisis específicos de diferentes indicadores:

| Carpeta | Descripción |
|---------|-------------|
| **admissions/** | Identificación de ingresos reales en unidades de hospitalización. Incluye `hosp_ward_longest_stay.py` (por unidad predominante). [Ver documentación detallada →](admissions/README.md) |
| **demographics/** | Tabla demográfica y de resultados de estancias en E073+I073 (`ward_stays_demo.py`). Estructura modular: `_sql.py` (consulta SQL), `_metrics.py` (cálculo de métricas), `_report.py` (generación HTML/CSV). Salidas: cohorte completa + tabla resumen en CSV y HTML en `demographics/output/` |
| **deliris/** | Indicadores CAM-ICU / delirio en UCI. [Documentación →](deliris/README.md) |
| **drg/** | Informe de complejidad asistencial basado en DRGs (Diagnosis-Related Groups): genera un PDF multipágina con indicadores de severidad (SOI), riesgo de mortalidad (ROM) y peso DRG (Case Mix Index) |
| **dynamic_forms/** | Consultas SQL sobre formularios dinámicos (`g_dynamic_forms`). Ejecución con `run_queries.py`; consultas en `queries/`, salida CSV en `dynamic_forms/output/`. [Ver README →](dynamic_forms/README.md) |
| **necropsy/** | Análisis de provisions de necropsias y autopsias — busca códigos relacionados en el diccionario y consulta la base de datos |
| **nutritions/** | Análisis de nutrición enteral y parenteral |
| **sepsis3/** | Query SQL para identificación de pacientes con sepsis según criterios Sepsis-3 (SOFA score ≥ 2 + sospecha de infección) |
| **snisp/** | Análisis de incidentes (`analysis_2025.py`) |
| **dictionaries/** | 54 diccionarios CSV extraídos de la base de datos (códigos de diagnóstico, laboratorio, fármacos, unidades, etc.). Incluye `extract_all_dictionaries.py` para regenerarlos y su propio [README](dictionaries/dictionaries_README.md) con la descripción de cada archivo |

Cada análisis genera sus resultados en una subcarpeta `output/` dentro de su respectiva carpeta.

---

## Conexión a la Base de Datos

La conexión a la base de datos se gestiona mediante el módulo `connection.py` ubicado en la raíz del proyecto.

### Configuración

Las credenciales se almacenan en un archivo `.env` ubicado en la **raíz de OneDrive**. El sistema detecta automáticamente la ruta de OneDrive tanto en Windows como en macOS.

> [!IMPORTANT]
> El archivo `.env` está excluido del repositorio vía `.gitignore`. Nunca subas credenciales al repositorio.

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

- **Python ≥ 3.10** (desarrollado con Python 3.13)

Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

Cada script se ejecuta de forma independiente desde la raíz del proyecto:

```bash
python demographics/ward_stays_demo.py
python admissions/hosp_ward_longest_stay.py
python deliris/run_sql.py deliris/camicu_compliance.sql
python deliris/run_sql.py deliris/camicu_positivity.sql
python deliris/run_sql.py deliris/camicu_daily_coverage.sql
python deliris/run_sql.py deliris/camicu_daily_coverage_excl_deep_rass.sql
python deliris/camicu_plots.py
python nutritions/nutritions.py
python drg/drg_complexity_report.py
python necropsy/necropsias_autopsias.py
python dynamic_forms/run_queries.py --list
```

Los scripts solicitan interactivamente los parámetros necesarios (año, unidades, etc.) y generan los resultados en la carpeta `output/` correspondiente.
