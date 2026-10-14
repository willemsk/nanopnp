"""Nondimensionalisation of the coupled system."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from nanopnp.core.constants import (
    FARADAY,
    GAS_CONSTANT,
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
    thermal_voltage,
)

NM_PER_M: Final = 1e9

MOL_PER_M3_PER_MOL_PER_L: Final = 1e3

# D_0 (D_Na0, Mills 1989) and water's viscosity at 298.15 K: SPECIFICATION.md section 6.3.
REFERENCE_DIFFUSIVITY_M2_S: Final = 1.334e-9

REFERENCE_VISCOSITY_PA_S: Final = 0.890e-3

# eps_r,f0 after Gavish 2016 (knowledge/01-physics-epnpns/03-the-corrections.md); the P0 of the
# permittivity correction in willems2020_nacl.yaml, and physics.pb's alias.
REFERENCE_PERMITTIVITY: Final = 78.15


def debye_length_nm(
    concentration_M: float,
    *,
    relative_permittivity: float = REFERENCE_PERMITTIVITY,
    temperature_K: float = REFERENCE_TEMPERATURE_K,
    valence: int = 1,
) -> float:
    """Return the Debye length in nm of a symmetric z:z electrolyte; ValueError for c <= 0."""
    if not concentration_M > 0.0:  # NaN fails too
        raise ValueError(f"concentration must be positive, got {concentration_M} M")
    permittivity = VACUUM_PERMITTIVITY * relative_permittivity
    concentration_mol_m3 = concentration_M * MOL_PER_M3_PER_MOL_PER_L
    squared = (
        permittivity
        * GAS_CONSTANT
        * temperature_K
        / (2.0 * FARADAY**2 * valence**2 * concentration_mol_m3)
    )
    return math.sqrt(squared) * NM_PER_M


@dataclass(frozen=True)
class Scales:
    """The scale set of a geometry and an electrolyte; each scale is a computed property."""

    length_nm: float
    concentration_M: float
    temperature_K: float = REFERENCE_TEMPERATURE_K
    diffusivity_m2_s: float = REFERENCE_DIFFUSIVITY_M2_S
    viscosity_Pa_s: float = REFERENCE_VISCOSITY_PA_S
    relative_permittivity: float = REFERENCE_PERMITTIVITY

    def __post_init__(self) -> None:
        for name in (
            "length_nm",
            "concentration_M",
            "temperature_K",
            "diffusivity_m2_s",
            "viscosity_Pa_s",
            "relative_permittivity",
        ):
            value = getattr(self, name)
            if not value > 0.0:  # NaN fails too
                raise ValueError(f"scale {name} must be positive, got {value}")

    @property
    def length_m(self) -> float:
        """Reference length ``a``, in m."""
        return self.length_nm / NM_PER_M

    @property
    def permittivity(self) -> float:
        """Absolute permittivity ``eps = eps_r eps_0``, in F/m."""
        return self.relative_permittivity * VACUUM_PERMITTIVITY

    @property
    def potential_V(self) -> float:
        """Potential scale ``V_T = RT/F``, in V."""
        return thermal_voltage(self.temperature_K)

    @property
    def concentration_mol_m3(self) -> float:
        """Concentration scale ``c_0``, in mol/m^3."""
        return self.concentration_M * MOL_PER_M3_PER_MOL_PER_L

    @property
    def velocity_m_s(self) -> float:
        """Velocity scale ``u_0 = eps V_T^2 / (eta a)``, in m/s."""
        return self.permittivity * self.potential_V**2 / (self.viscosity_Pa_s * self.length_m)

    @property
    def pressure_Pa(self) -> float:
        """Pressure scale ``p_0 = eps V_T^2 / a^2``, in Pa."""
        return self.permittivity * self.potential_V**2 / self.length_m**2

    @property
    def force_N(self) -> float:
        """Force scale ``p_0 a^2 = eps V_T^2``, in N; independent of the reference length."""
        return self.permittivity * self.potential_V**2

    @property
    def flux_mol_m2_s(self) -> float:
        """Ion-flux scale ``D_0 c_0 / a``, in mol/(m^2 s)."""
        return self.diffusivity_m2_s * self.concentration_mol_m3 / self.length_m

    @property
    def current_A(self) -> float:
        """Current scale ``F D_0 c_0 a``, in A."""
        return FARADAY * self.diffusivity_m2_s * self.concentration_mol_m3 * self.length_m

    @property
    def volumetric_flow_m3_s(self) -> float:
        """Volumetric-flow scale ``u_0 a^2``, in m^3/s."""
        return self.velocity_m_s * self.length_m**2

    @property
    def charge_density_C_m3(self) -> float:
        """Space-charge scale ``eps V_T / a^2``, in C/m^3."""
        return self.permittivity * self.potential_V / self.length_m**2

    @property
    def surface_charge_C_m2(self) -> float:
        """Surface-charge scale ``eps V_T / a``, in C/m^2."""
        return self.permittivity * self.potential_V / self.length_m

    @property
    def debye_length_nm(self) -> float:
        """Debye length of a symmetric monovalent electrolyte, in nm."""
        return debye_length_nm(
            self.concentration_M,
            relative_permittivity=self.relative_permittivity,
            temperature_K=self.temperature_K,
        )

    @property
    def debye_ratio(self) -> float:
        """Ratio of the Debye length to the reference length, dimensionless."""
        return self.debye_length_nm / self.length_nm

    @property
    def peclet(self) -> float:
        """Electroviscous Peclet number Pe = eps V_T^2 / (eta D_0)."""
        return (
            self.permittivity * self.potential_V**2 / (self.viscosity_Pa_s * self.diffusivity_m2_s)
        )

    def nondimensionalise(self, quantity: str, value: float) -> float:
        """Return ``value``, in SI units of ``quantity``, divided by that quantity's scale.

        Parameters
        ----------
        quantity
            A scaled field name, e.g. ``length`` or ``potential``; KeyError if unknown.
        """
        return value / self._scale(quantity)

    def redimensionalise(self, quantity: str, value: float) -> float:
        """Return a dimensionless value times its SI scale; inverts nondimensionalise."""
        return value * self._scale(quantity)

    def _scale(self, quantity: str) -> float:
        scales = {
            "length": self.length_m,
            "potential": self.potential_V,
            "concentration": self.concentration_mol_m3,
            "velocity": self.velocity_m_s,
            "pressure": self.pressure_Pa,
            "force": self.force_N,
            "diffusivity": self.diffusivity_m2_s,
            "flux": self.flux_mol_m2_s,
            "current": self.current_A,
            "volumetric_flow": self.volumetric_flow_m3_s,
            "charge_density": self.charge_density_C_m3,
            "surface_charge": self.surface_charge_C_m2,
        }
        if quantity not in scales:
            raise KeyError(
                f"{quantity!r} is not a scaled quantity; expected one of {sorted(scales)}"
            )
        return scales[quantity]

    def bias_to_dimensionless(self, bias_V: float) -> float:
        """Return an applied bias in volts as a multiple of ``V_T``."""
        return bias_V / self.potential_V

    def summary(self) -> dict[str, float]:
        """Return every defining input, scale and group, for the manifest."""
        return {
            "length_nm": self.length_nm,
            "concentration_M": self.concentration_M,
            "temperature_K": self.temperature_K,
            "viscosity_Pa_s": self.viscosity_Pa_s,
            "relative_permittivity": self.relative_permittivity,
            "potential_V": self.potential_V,
            "velocity_m_s": self.velocity_m_s,
            "pressure_Pa": self.pressure_Pa,
            "force_N": self.force_N,
            "diffusivity_m2_s": self.diffusivity_m2_s,
            "flux_mol_m2_s": self.flux_mol_m2_s,
            "current_A": self.current_A,
            "volumetric_flow_m3_s": self.volumetric_flow_m3_s,
            "charge_density_C_m3": self.charge_density_C_m3,
            "surface_charge_C_m2": self.surface_charge_C_m2,
            "debye_length_nm": self.debye_length_nm,
            "debye_ratio": self.debye_ratio,
            "peclet": self.peclet,
        }
