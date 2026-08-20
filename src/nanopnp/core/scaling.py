"""Nondimensionalisation of the coupled system (NUM-09, NUM-10).

The five fields of ePNP-NS span twenty-odd orders of magnitude in SI: a
potential of 1e-1 V, a concentration of 1e3 mol/m^3, a velocity of 1e-3 m/s, a
pressure of 1e2 Pa and a diffusivity of 1e-9 m^2/s. Assembled together into one
Jacobian, that spread is the whole difficulty of the linear solve — not the
sparsity pattern, not the size. Scaling is therefore not a tidiness measure
here; it is what makes the direct factorisation give a trustworthy answer.

NUM-09 fixes the scales: length by the pore radius ``a``, potential by the
thermal voltage ``V_T = RT/F``, concentration by the bulk value ``c_0``,
diffusivity by ``D_0``, and then

    u_0 = eps V_T^2 / (eta a)        p_0 = eps V_T^2 / a^2

which are the velocity and pressure at which the electrical body force balances
viscosity. Two dimensionless groups fall out and both are physics, not
bookkeeping:

    lambda~ = lambda_D / a           the screening ratio, 0.088 to 0.679
    Pe      = eps V_T^2 / (eta D_0)  0.386 at 298.15 K and eta = 0.890 mPa s

``Pe < 1`` is the statement that ion transport through the pore is not
convection-dominated; it is why the Nernst-Planck equation is solvable without
stabilisation on a mesh that resolves the double layer (NUM-11), and it is worth
recomputing rather than trusting, because the frequently quoted ``Pe = 0.34``
belongs to ``eta = 1.00 mPa s``, that is to 20 degC and not 25 degC. Mixing the
two temperatures across material properties is a silent per-cent-level error.

Lengths are in **nm** in the mesh and in every interface here, matching
``mesh.primitives``; the conversion to metres happens inside this module and
nowhere else.
"""

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
"""Nanometres per metre; lengths cross this boundary here and nowhere else."""

MOL_PER_M3_PER_MOL_PER_L: Final = 1e3
"""mol/m^3 per mol/L."""

REFERENCE_DIFFUSIVITY_M2_S: Final = 1.334e-9
"""``D_0``, in m^2/s (NUM-09). The infinite-dilution mean for NaCl."""

REFERENCE_VISCOSITY_PA_S: Final = 0.890e-3
"""Water viscosity at 298.15 K, in Pa s (NUM-09 note on the Peclet number)."""

REFERENCE_PERMITTIVITY: Final = 78.15
"""Relative permittivity of water at 298.15 K (``.knowledge/01-physics-epnpns.md``)."""


@dataclass(frozen=True)
class Scales:
    """The NUM-09 scale set, derived from a geometry and an electrolyte.

    Attributes are the *defining* inputs; every scale is a property computed
    from them, so no two members can disagree.

    Parameters
    ----------
    length_nm
        Reference length ``a``, the pore radius. Around 2 nm for ClyA.
    concentration_M
        Bulk concentration ``c_0``, in mol/L.
    temperature_K
        Absolute temperature. Every material property must be quoted at this
        same temperature; see the module docstring.
    diffusivity_m2_s
        Reference diffusivity ``D_0``.
    viscosity_Pa_s
        Reference dynamic viscosity ``eta``.
    relative_permittivity
        Reference relative permittivity of the electrolyte.
    """

    length_nm: float
    concentration_M: float
    temperature_K: float = REFERENCE_TEMPERATURE_K
    diffusivity_m2_s: float = REFERENCE_DIFFUSIVITY_M2_S
    viscosity_Pa_s: float = REFERENCE_VISCOSITY_PA_S
    relative_permittivity: float = REFERENCE_PERMITTIVITY

    def __post_init__(self) -> None:
        """Reject a scale set that would divide by zero downstream."""
        for name in (
            "length_nm",
            "concentration_M",
            "temperature_K",
            "diffusivity_m2_s",
            "viscosity_Pa_s",
            "relative_permittivity",
        ):
            value = getattr(self, name)
            if value <= 0.0:
                raise ValueError(f"scale {name} must be positive, got {value}")

    # -- primitive scales ------------------------------------------------

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
        """Potential scale ``V_T = RT/F``, in V. 25.693 mV at 298.15 K."""
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
    def flux_mol_m2_s(self) -> float:
        """Ion-flux scale ``D_0 c_0 / a``, in mol/(m^2 s)."""
        return self.diffusivity_m2_s * self.concentration_mol_m3 / self.length_m

    @property
    def current_A(self) -> float:
        """Current scale ``F D_0 c_0 a``, in A.

        The flux scale times an area ``a^2`` times Faraday's constant: the
        current a diffusive flux at the reference gradient carries through a
        pore-sized aperture.
        """
        return FARADAY * self.diffusivity_m2_s * self.concentration_mol_m3 * self.length_m

    # -- dimensionless groups --------------------------------------------

    @property
    def debye_length_nm(self) -> float:
        """``lambda_D`` for a symmetric monovalent electrolyte, in nm.

        ``lambda_D^2 = eps RT / (2 F^2 c_0)``. 1.357 nm at 0.05 M, 0.304 nm at
        1 M, 0.175 nm at 3 M (NUM-09).
        """
        squared = (
            self.permittivity
            * GAS_CONSTANT
            * self.temperature_K
            / (2.0 * FARADAY**2 * self.concentration_mol_m3)
        )
        return math.sqrt(squared) * NM_PER_M

    @property
    def debye_ratio(self) -> float:
        """``lambda~ = lambda_D / a``. 0.088 to 0.679 over 0.05-3 M at a = 2 nm."""
        return self.debye_length_nm / self.length_nm

    @property
    def peclet(self) -> float:
        """``Pe = eps V_T^2 / (eta D_0)``, the electroviscous Peclet number.

        0.386 at 298.15 K with ``eta = 0.890 mPa s``. Equivalently
        ``u_0 a / D_0``: the ratio of the electro-osmotic to the diffusive
        transport rate.
        """
        return (
            self.permittivity * self.potential_V**2 / (self.viscosity_Pa_s * self.diffusivity_m2_s)
        )

    # -- conversions ------------------------------------------------------

    def nondimensionalise(self, quantity: str, value: float) -> float:
        """Return ``value``, given in the SI unit of ``quantity``, divided by its scale.

        Parameters
        ----------
        quantity
            One of ``length``, ``potential``, ``concentration``, ``velocity``,
            ``pressure``, ``diffusivity``, ``flux``, ``current``.
        value
            The quantity in SI units (m, V, mol/m^3, m/s, Pa, m^2/s,
            mol/(m^2 s), A).

        Returns
        -------
        float
            The dimensionless value.

        Raises
        ------
        KeyError
            If ``quantity`` is not a scaled field.
        """
        return value / self._scale(quantity)

    def redimensionalise(self, quantity: str, value: float) -> float:
        """Return a dimensionless ``value`` multiplied by its SI scale.

        The inverse of :meth:`nondimensionalise`; this is the boundary at which
        ``post/`` hands numbers back in SI.
        """
        return value * self._scale(quantity)

    def _scale(self, quantity: str) -> float:
        """Return the SI scale of a named quantity."""
        scales = {
            "length": self.length_m,
            "potential": self.potential_V,
            "concentration": self.concentration_mol_m3,
            "velocity": self.velocity_m_s,
            "pressure": self.pressure_Pa,
            "diffusivity": self.diffusivity_m2_s,
            "flux": self.flux_mol_m2_s,
            "current": self.current_A,
        }
        if quantity not in scales:
            raise KeyError(
                f"{quantity!r} is not a scaled quantity; expected one of {sorted(scales)}"
            )
        return scales[quantity]

    def bias_to_dimensionless(self, bias_V: float) -> float:
        """Return an applied bias in volts as a multiple of ``V_T``.

        +/-200 mV, the envelope of FR-17, is +/-7.784 at 298.15 K.
        """
        return bias_V / self.potential_V

    def summary(self) -> dict[str, float]:
        """Return every scale and group, for the provenance manifest (FR-25)."""
        return {
            "length_nm": self.length_nm,
            "concentration_M": self.concentration_M,
            "temperature_K": self.temperature_K,
            "potential_V": self.potential_V,
            "velocity_m_s": self.velocity_m_s,
            "pressure_Pa": self.pressure_Pa,
            "diffusivity_m2_s": self.diffusivity_m2_s,
            "current_A": self.current_A,
            "debye_length_nm": self.debye_length_nm,
            "debye_ratio": self.debye_ratio,
            "peclet": self.peclet,
        }
