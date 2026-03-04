# Dynamic Forms - Queries

Script para ejecutar consultas SQL contra la base de datos DataNex relacionadas con formularios dinámicos (`g_dynamic_forms`).

## Estructura

```
dynamic_forms/
├── run_queries.py      # Script principal
├── queries/            # Archivos .sql
│   ├── 01_explorar_uci.sql
│   ├── 02_uci_otro_centro.sql
│   ├── 03_uci_procedencia_otro_centro.sql
│   ├── 04_procedencias_e073_2024.sql
│   └── 05_ingresos_otro_centro.sql   # Ingresos desde otros centros
├── output/             # Resultados CSV (por defecto)
└── README.md
```

## Uso

```bash
# Desde la raíz del proyecto
cd indicadors_iso
python dynamic_forms/run_queries.py --list

# Ejecutar una query (guarda CSV en output/ por defecto)
python dynamic_forms/run_queries.py --query ingresos_otro_centro
python dynamic_forms/run_queries.py --query 04_procedencias_e073_2024

# Ejecutar todas las queries
python dynamic_forms/run_queries.py --all

# Ejecutar sin guardar CSV
python dynamic_forms/run_queries.py --query explorar_uci --no-save
```

## Requisitos

- Credenciales en `.env` (DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE)
- `connection.py` en la raíz del proyecto
- Dependencias: `pandas`, `mysql-connector-python`, `python-dotenv`

## Añadir nuevas queries

Crea un archivo `.sql` en `queries/` y ejecútalo con `--query <nombre_sin_ext>` o `--all`.
