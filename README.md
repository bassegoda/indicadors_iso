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

Cada análisis genera sus resultados en una subcarpeta `output/` dentro de su respectiva carpeta.

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
