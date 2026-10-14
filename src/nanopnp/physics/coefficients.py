"""Material coefficients of the coupled system, in the NUM-09 variables."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from nanopnp.core.constants import FARADAY
from nanopnp.core.scaling import NM_PER_M, Scales
from nanopnp.core.typing import Expression, Numeric
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.materials.forms import NGSOLVE_OPS, MathOps
from nanopnp.numerics.gates import excluded_volume_m3_per_mol

__all__ = [
    "MESH_LENGTH_UNIT_NM",
    "SATURATED_WALL_DISTANCE_NM",
    "NondimensionalCoefficients",
    "mesh_unit_scales",
    "species_concentrations_SI",
]

MESH_LENGTH_UNIT_NM = 1.0

# f^w_D is within 1 % of 1 beyond 0.75 nm (knowledge/01-physics-epnpns/index.md).
# 0.0 would be the wall value.
SATURATED_WALL_DISTANCE_NM = 3.0


def mesh_unit_scales(electrolyte: Electrolyte, concentration_M: float) -> Scales:
    """Return the scale set for a mesh built in nanometres."""
    return Scales(
        length_nm=MESH_LENGTH_UNIT_NM,
        concentration_M=concentration_M,
        temperature_K=electrolyte.temperature_K,
        viscosity_Pa_s=electrolyte.viscosity_0,
        relative_permittivity=electrolyte.permittivity_0,
    )


@dataclass(frozen=True)
class NondimensionalCoefficients:
    """Every material coefficient of the coupled system, made dimensionless.

    Parameters
    ----------
    wall_distance_nm
        The distance field in nm; the saturated distance when no wall correction is active.
    """

    electrolyte: Electrolyte
    scales: Scales
    concentrations: Mapping[str, Expression]
    wall_distance_nm: Expression
    ops: MathOps = NGSOLVE_OPS
    _driver_M: Expression = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.scales.length_nm != MESH_LENGTH_UNIT_NM:
            raise ValueError(
                f"the reference length is {self.scales.length_nm} nm but the mesh is built in "
                f"{MESH_LENGTH_UNIT_NM} nm units; every gradient in the weak forms would be wrong "
                "by that ratio with no diagnostic. Build the scales with mesh_unit_scales()"
            )
        missing = [
            ion.name for ion in self.electrolyte.species if ion.name not in self.concentrations
        ]
        if missing:
            raise ValueError(
                f"no concentration expression for {', '.join(missing)}; the electrolyte solves for "
                f"{', '.join(ion.name for ion in self.electrolyte.species)}"
            )
        # Built once: the driver enters every corrected property, and rebuilding
        # the expression per property would multiply the size of the symbolic
        # tree NGSolve differentiates for the Jacobian.
        object.__setattr__(self, "_driver_M", self._build_driver())

    def _build_driver(self) -> Expression:
        scale = self.scales.concentration_mol_m3
        ordered = [self.concentrations[ion.name] * scale for ion in self.electrolyte.species]
        return self.electrolyte.average_concentration(ordered, self.ops)

    @property
    def driver_M(self) -> Expression:
        """The correction driver ``<c>``, in mol/L."""
        return self._driver_M

    def diffusivity(self, species: str) -> Expression:
        """Return ``D~_i = D_i(<c>, d) / D_0``."""
        value = self.electrolyte.diffusivity(
            species, self.driver_M, self.wall_distance_nm, self.ops
        )
        return value / self.scales.diffusivity_m2_s

    def mobility(self, species: str) -> Expression:
        """Return ``mu~_i = mu_i(<c>, d) V_T / D_0``."""
        value = self.electrolyte.mobility(species, self.driver_M, self.wall_distance_nm, self.ops)
        return value * self.scales.potential_V / self.scales.diffusivity_m2_s

    def viscosity(self) -> Expression:
        """Return ``eta~ = eta(<c>, d) / eta_0``."""
        value = self.electrolyte.viscosity(self.driver_M, self.wall_distance_nm, self.ops)
        return value / self.scales.viscosity_Pa_s

    def mass_density(self) -> Expression:
        """Return ``rho~ = rho(<c>) / rho_0``; density carries no wall correction."""
        value = self.electrolyte.mass_density(self.driver_M, self.wall_distance_nm, self.ops)
        return value / self.electrolyte.mass_density_0

    def relative_permittivity(self) -> Expression:
        """Return ``eps~_r = eps_r,f(<c>) / eps_r,f^0`` in the electrolyte."""
        value = self.electrolyte.relative_permittivity(
            self.driver_M, self.wall_distance_nm, self.ops
        )
        return value / self.scales.relative_permittivity

    def ionic_charge_density(self) -> Expression:
        """Return the dimensionless mobile charge ``sum_i z_i c~_i``."""
        terms = [
            float(ion.valence) * self.concentrations[ion.name] for ion in self.electrolyte.species
        ]
        total = terms[0]
        for term in terms[1:]:
            total = total + term
        return total

    @property
    def screening(self) -> float:
        """Return the Poisson and body-force coefficient ``S = F c_0 L_0^2 / (eps V_T)``."""
        return (
            FARADAY
            * self.scales.concentration_mol_m3
            * self.scales.length_m**2
            / (self.scales.permittivity * self.scales.potential_V)
        )

    @property
    def peclet(self) -> float:
        """Return the electroviscous Peclet number ``Pe = eps V_T^2 / (eta D_0)``."""
        return self.scales.peclet

    @property
    def reynolds(self) -> float:
        """Return the Reynolds number ``Re = rho_0 u_0 L_0 / eta_0``."""
        return (
            self.electrolyte.mass_density_0
            * self.scales.velocity_m_s
            * self.scales.length_m
            / self.scales.viscosity_Pa_s
        )

    @property
    def packing_coefficients(self) -> Mapping[str, float]:
        """Return ``nu_j = N_A a_j^3 c_0``, the packing weight per species."""
        return {
            ion.name: excluded_volume_m3_per_mol(ion.steric_diameter * NM_PER_M)
            * self.scales.concentration_mol_m3
            for ion in self.electrolyte.species
        }

    def steric_volume_ratio(self, species: str) -> float:
        """Return ``a_i^3 / a_0^3``, the species-dependent steric prefactor."""
        ion = self.electrolyte.ion(species)
        return (ion.steric_diameter / self.electrolyte.water_steric_diameter) ** 3

    def permittivity_sensitivity(self, species: str) -> Expression:
        """Return ``d eps~_r / d c~_i``, a deviation-only term."""
        import ngsolve as ngs

        permittivity = self.relative_permittivity()
        if not isinstance(permittivity, ngs.CoefficientFunction):
            return ngs.CoefficientFunction(0.0)
        return permittivity.Diff(self.concentrations[species])

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Return what the manifest must record about the coefficients."""
        return {
            "scales": self.scales.summary(),
            "screening": self.screening,
            "peclet": self.peclet,
            "reynolds": self.reynolds,
            "materials": dict(self.electrolyte.provenance),
        }


def species_concentrations_SI(
    scales: Scales, concentrations: Mapping[str, Expression]
) -> Mapping[str, Numeric]:
    """Return the species concentrations in mol/m^3, for the state gates."""
    scale = scales.concentration_mol_m3
    return {name: value * scale for name, value in concentrations.items()}
