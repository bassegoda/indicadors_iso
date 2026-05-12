"""Configuración de patrones LIKE para identificar nutrición enteral y
parenteral en `prescriptions.drug_descr`.

El ATC es **inservible** para esta cohorte:
- Las filas reales de `NUTRICIÓN PARENTERAL CENTRAL` y `NUTRICION ENTERAL`
  tienen `atc_ref = NULL`.
- En perfusiones, el `atc_ref` suele ser el del DILUYENTE (sodio cloruro
  parenteral), no el del principio activo — caería gran cantidad de
  antibióticos, sedantes, electrolitos, etc., como falsos positivos
  "parenterales".

Por eso filtramos exclusivamente por `UPPER(drug_descr) LIKE`. Patrones
fijados tras `_explore_nutrition_descr.py` sobre 2019-2025, E073/I073:

    Enteral incluido:
        NUTRICION ENTERAL (NASOGASTRICA / GASTROSTOMIA / YEYUNOSTOMIA)
        NUTRICOM HEPA, 500 ML FRASCO       (V06, fórmula hepática enteral)
    Excluido (aunque pesque al LIKE genérico):
        AGUA ENTERAL              -> agua libre por sonda, no nutrición
        ORDENES NUTRICION         -> label genérico, no producto
        HIERRO ... PARENTERALES   -> mineral, no nutrición

    Parenteral incluido:
        NUTRICIÓN PARENTERAL CENTRAL
        NUTRICIÓN PARENTERAL PERIFERICA   (con tilde)
        NUTRICION PARENTERAL PERIFERICA   (sin tilde — variante reciente)
"""

ENTERAL_PATTERNS: tuple[str, ...] = (
    "%NUTRICION ENTERAL%",
    "%NUTRICOM%",
)

PARENTERAL_PATTERNS: tuple[str, ...] = (
    "%NUTRICION PARENTERAL%",
    "%NUTRICIÓN PARENTERAL%",
)


def _to_sql_or(column: str, patterns: tuple[str, ...]) -> str:
    """Devuelve `(UPPER(col) LIKE 'p1' OR UPPER(col) LIKE 'p2' ...)` listo
    para incrustar en una cláusula WHERE de Athena/Trino."""
    parts = [f"UPPER({column}) LIKE '{p}'" for p in patterns]
    return "(" + " OR ".join(parts) + ")"


def enteral_predicate(column: str = "drug_descr") -> str:
    return _to_sql_or(column, ENTERAL_PATTERNS)


def parenteral_predicate(column: str = "drug_descr") -> str:
    return _to_sql_or(column, PARENTERAL_PATTERNS)
