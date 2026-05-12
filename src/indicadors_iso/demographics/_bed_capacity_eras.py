"""Capacidad nominal de camas por época histórica de la UCI.

Define el denominador del % de ocupación. En lugar de derivarlo
empíricamente del nº de `place_ref` con actividad mensual (que respira
con el numerador y se distorsiona durante COVID y en transiciones
administrativas), fijamos una capacidad nominal por (unidad, época).

Épocas:
  - 2018-01-01 → 2020-02-29  →  I073 = 4 camas, E073 = 8 camas (stable)
  - 2020-03-01 → 2022-03-31  →  UCI agregada = 12 camas (covid)
  - 2022-04-01 → futuro      →  I073 = 4 camas, E073 = 10 camas (stable)

El final de la era COVID se mueve a 2022-03 (no 2022-02) porque los
datos mensuales muestran que en marzo 2022 E073 todavía tenía 14
`place_ref` activos (configuración COVID extendida) y I073 marzo
estaba siendo reactivada sólo parcialmente (30% util en 4 camas). La
transición operativa real ocurrió en abril 2022.

Durante la época `covid`, el etiquetado E073/I073 no es interpretable
porque las camas físicas se reasignaron administrativamente entre
unidades (la cama 1, normalmente I073, podía aparecer codificada como
E073, etc.) y los `place_ref` están pseudo-anonimizados, por lo que no
podemos mapear cama física ↔ place_ref a lo largo del tiempo. La
solución honesta es agregar el numerador de E073 + I073 en una unidad
sintética "UCI" frente a 12 camas nominales (la suma pre-COVID).
Durante la pandemia el % puede superar 100% (expansión real). Los
límites de las épocas pueden ajustarse cuando se valide con clínica.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

# Etiqueta de la unidad sintética usada en la época `covid`.
COMBINED_UNIT_LABEL = "UCI"

# Capacidad combinada I073 (4) + E073 (8) pre-marzo-2020. Se usa también
# como referencia para interpretar los % de la época `covid`: el nominal
# que ponemos durante COVID coincide con esta cifra para que el %
# refleje directamente la presión sobre la dotación pre-pandemia.
PRE_COVID_TOTAL_BEDS = 12


@dataclass(frozen=True)
class CapacityEra:
    start: date           # inclusive
    end: date             # inclusive
    unit: str             # "E073", "I073" o COMBINED_UNIT_LABEL
    nominal_beds: int
    regimen: str          # "stable" | "covid"


NOMINAL_CAPACITY_HISTORY: list[CapacityEra] = [
    CapacityEra(date(2018, 1, 1),  date(2020, 2, 29), "I073", 4, "stable"),
    CapacityEra(date(2018, 1, 1),  date(2020, 2, 29), "E073", 8, "stable"),
    CapacityEra(date(2020, 3, 1),  date(2022, 3, 31),
                COMBINED_UNIT_LABEL, PRE_COVID_TOTAL_BEDS, "covid"),
    CapacityEra(date(2022, 4, 1),  date(2099, 12, 31), "I073", 4, "stable"),
    CapacityEra(date(2022, 4, 1),  date(2099, 12, 31), "E073", 10, "stable"),
]


def lookup_capacity_for_month(
    year: int, month: int, raw_unit: str
) -> Optional[tuple[str, int, str]]:
    """Devuelve (effective_unit, nominal_beds, regimen) o None.

    - En `stable`: effective_unit == raw_unit, beds = nominal de la unidad.
    - En `covid`: raw_unit ∈ {"E073", "I073"} colapsa a "UCI" con 12 camas.
    - Devuelve None si la combinación no encaja en ninguna época.

    Las épocas están alineadas con inicios/finales de mes para que un
    mes calendario nunca se solape con dos regímenes distintos.
    """
    target = date(year, month, 1)
    for era in NOMINAL_CAPACITY_HISTORY:
        if not (era.start <= target <= era.end):
            continue
        if era.regimen == "covid":
            if raw_unit in {"E073", "I073"}:
                return COMBINED_UNIT_LABEL, era.nominal_beds, "covid"
            continue
        if era.unit == raw_unit:
            return era.unit, era.nominal_beds, "stable"
    return None


def hours_in_year(year: int) -> int:
    """Horas totales del año (8784 en bisiestos, 8760 en normales)."""
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    return 8784 if leap else 8760
