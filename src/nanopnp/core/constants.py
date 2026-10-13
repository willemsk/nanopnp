"""Physical constants in SI units, and the derived thermal voltage."""

from __future__ import annotations

from typing import Final

ELEMENTARY_CHARGE: Final = 1.602176634e-19

BOLTZMANN: Final = 1.380649e-23

AVOGADRO: Final = 6.02214076e23

FARADAY: Final = ELEMENTARY_CHARGE * AVOGADRO

GAS_CONSTANT: Final = BOLTZMANN * AVOGADRO

VACUUM_PERMITTIVITY: Final = 8.8541878128e-12

REFERENCE_TEMPERATURE_K: Final = 298.15


def thermal_voltage(temperature_K: float = REFERENCE_TEMPERATURE_K) -> float:
    """Return the thermal voltage k_B T / e, in volts."""
    return BOLTZMANN * temperature_K / ELEMENTARY_CHARGE
