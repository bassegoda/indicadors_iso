"""Configuración compartida para los pipelines de demographics.

`FAKE_BED_PLACE_REFS_E073`
    `place_ref` de la "cama falsa" de E073: una posición en `movements`
    que no es una cama real de paciente crítico, sino una cama auxiliar
    usada para realizar procedimientos. Se excluye del numerador y del
    denominador del cálculo de ocupación de camas.

    Para identificar el/los `place_ref` correspondientes, ejecutar
    `demographics/helper_identify_fake_bed.sql` en Metabase y revisar la
    salida: la cama falsa se distingue por una mediana de duración por
    movimiento muy baja (procedimiento dura horas, no días), muchos
    movimientos y pacientes variados.

    Si la lista está vacía, no se excluye nada y el cálculo equivale a
    contar todas las camas que aparecen en `movements`.
"""

from __future__ import annotations

# Identificada el 2026-04-30 mediante `helper_identify_fake_bed.sql`.
# Patrón frente al resto de place_ref de E073:
#   - mediana de 216 min (~3.6 h) por movimiento (vs ~5500 min en las
#     camas reales)
#   - total acumulado de sólo 1.149 h en todo el periodo cubierto por
#     el sistema (vs ~56.000 h en cualquiera de las camas reales)
#   - p90 de 901 min (~15 h), incompatible con estancia crítica
# → corresponde a la cama auxiliar de procedimientos.
FAKE_BED_PLACE_REFS_E073: list[int] = [42109160000]
