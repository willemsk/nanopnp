"""Physical constants in SI units, and the derived thermal voltage.

Values are CODATA 2018 as used throughout ``.knowledge/01-physics-epnpns.md``.
Every quantity here is SI: metres, kelvin, coulombs, volts. Nanometres, molar
concentrations and millivolts appear only at the interface layer, where the
unit is part of the name (``radius_nm``, ``bias_V``).
"""

from __future__ import annotations

from typing import Final

ELEMENTARY_CHARGE: Final = 1.602176634e-19
"""Elementary charge e, in C (exact, SI definition)."""

BOLTZMANN: Final = 1.380649e-23
"""Boltzmann constant k_B, in J/K (exact, SI definition)."""

AVOGADRO: Final = 6.02214076e23
"""Avogadro constant N_A, in 1/mol (exact, SI definition)."""

FARADAY: Final = ELEMENTARY_CHARGE * AVOGADRO
"""Faraday constant F = e N_A, in C/mol."""

GAS_CONSTANT: Final = BOLTZMANN * AVOGADRO
"""Molar gas constant R = k_B N_A, in J/(mol K)."""

VACUUM_PERMITTIVITY: Final = 8.8541878128e-12
"""Electric constant eps_0, in F/m."""

REFERENCE_TEMPERATURE_K: Final = 298.15
"""Reference temperature of the source work, in K (experiments at 25 +/- 1 degC)."""


def thermal_voltage(temperature_K: float = REFERENCE_TEMPERATURE_K) -> float:
    """Return the thermal voltage V_T = k_B T / e, in volts.

    At the reference temperature this is 25.693 mV, the value the published
    infinite-dilution mobilities were derived with (VER-04). Note that the
    Nernst-Einstein relation ``mu_i = D_i / V_T`` holds only at infinite
    dilution: D and mu carry different concentration corrections, so
    ``D_i / mu_i`` drifts to 1.2-1.7 x kT/e between 0.15 M and 3 M (VER-05,
    PHY-14).

    Parameters
    ----------
    temperature_K
        Absolute temperature, in K.

    Returns
    -------
    float
        Thermal voltage, in V.
    """
    return BOLTZMANN * temperature_K / ELEMENTARY_CHARGE
