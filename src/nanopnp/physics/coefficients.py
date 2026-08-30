"""Material coefficients of the coupled system, in the NUM-09 variables.

The weak forms of ``physics/`` never touch an SI material property. They ask
this module for a dimensionless coefficient, and it converts once:

    D~_i = D_i / D_0        mu~_i = mu_i V_T / D_0      eta~ = eta / eta_0
    rho~ = rho / rho_0      eps~_r = eps_r / eps_r^0

Three dimensionless groups fall out of the same conversion and are constants of
the case rather than fields:

    S  = F c_0 L_0^2 / (eps V_T)   the Poisson source and body-force coefficient
    Pe = eps V_T^2 / (eta D_0)     the convective coefficient of Nernst-Planck
    Re = rho_0 u_0 L_0 / eta_0     the coefficient of the inertia term

``S`` is the ``1/(2 lambda^2)`` that ``physics/pb.py`` already carries — for a
symmetric monovalent salt the two are the same number — but it is computed here
from its definition so that an asymmetric electrolyte is right too.

**The reference length is the mesh unit.** ``mesh/primitives.py`` builds its
geometries in nanometres and the corrections are fitted in nanometres, so a
:class:`~nanopnp.core.scaling.Scales` handed to these forms must carry
``length_nm = 1.0``; :func:`mesh_unit_scales` builds one, and the constructor
refuses anything else. Solving on a mesh in nm while scaling lengths by a 2 nm
pore radius would leave every gradient wrong by that factor with no diagnostic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from nanopnp.core.constants import FARADAY
from nanopnp.core.scaling import NM_PER_M, Scales
from nanopnp.core.typing import Expression, Numeric
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.materials.forms import NGSOLVE_OPS, MathOps
from nanopnp.solve.gates import excluded_volume_m3_per_mol

__all__ = [
    "MESH_LENGTH_UNIT_NM",
    "SATURATED_WALL_DISTANCE_NM",
    "NondimensionalCoefficients",
    "mesh_unit_scales",
    "species_concentrations_SI",
]

MESH_LENGTH_UNIT_NM = 1.0
"""The reference length ``L_0``, in nm: the unit the mesh is built in."""

SATURATED_WALL_DISTANCE_NM = 3.0
"""A wall distance at which every wall correction has saturated to 1.

``f^w_D`` is within 1 % of 1 beyond 0.75 nm, so passing this as the distance
field is the bulk limit. It exists so that a run with no wall correction active
can say so at the call site rather than pass an unlabelled ``0.0`` — which is
the *wall* value, ``f^w_D(0) = 0.0601``, and would silently suppress ion
motility everywhere.
"""


def mesh_unit_scales(electrolyte: Electrolyte, concentration_M: float) -> Scales:
    """Return the NUM-09 scale set for a mesh built in nanometres.

    The reference length is one mesh unit, and the viscosity, permittivity and
    temperature are taken from the electrolyte so that the scale set and the
    correction models cannot quote different reference values for the same
    property.

    Parameters
    ----------
    electrolyte
        Electrolyte whose reference properties define the scales.
    concentration_M
        Bulk concentration ``c_0``, in mol/L.
    """
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
    electrolyte
        Reference properties and the correction model in force per property.
    scales
        NUM-09 scale set; its ``length_nm`` must be the mesh unit.
    concentrations
        The dimensionless ``c~_i``, keyed by species name. These are the trial
        functions or grid functions of the solve, so ``ngsolve.grad`` applies to
        them.
    wall_distance_nm
        The PHY-02 distance field, in nm. Pass
        :data:`SATURATED_WALL_DISTANCE_NM` when no wall correction is active.
    ops
        Operation namespace the correction forms are evaluated with. NGSolve by
        default, because these coefficients are built for assembly; NumPy makes
        the same object usable as a diagnostic.
    """

    electrolyte: Electrolyte
    scales: Scales
    concentrations: Mapping[str, Expression]
    wall_distance_nm: Expression
    ops: MathOps = NGSOLVE_OPS
    _driver_M: Expression = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Reject a scale set or a species set that would be silently wrong.

        Raises
        ------
        ValueError
            If the reference length is not the mesh unit, or if a solved species
            has no concentration expression.
        """
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

    # -- the correction driver -------------------------------------------

    def _build_driver(self) -> Expression:
        """Return ``<c>`` in mol/L from the dimensionless concentrations."""
        scale = self.scales.concentration_mol_m3
        ordered = [self.concentrations[ion.name] * scale for ion in self.electrolyte.species]
        return self.electrolyte.average_concentration(ordered, self.ops)

    @property
    def driver_M(self) -> Expression:
        """The correction driver ``<c>``, in mol/L (PHY-01, PHY-10)."""
        return self._driver_M

    # -- dimensionless fields ---------------------------------------------

    def diffusivity(self, species: str) -> Expression:
        """Return ``D~_i = D_i(<c>, d) / D_0``."""
        value = self.electrolyte.diffusivity(
            species, self.driver_M, self.wall_distance_nm, self.ops
        )
        return value / self.scales.diffusivity_m2_s

    def mobility(self, species: str) -> Expression:
        """Return ``mu~_i = mu_i(<c>, d) V_T / D_0``.

        At infinite dilution ``mu_i^0 = D_i^0 / V_T`` (PHY-14), so ``mu~_i``
        reduces to ``D_i^0/D_0`` there. It does *not* stay equal to ``D~_i`` at
        finite concentration: the two carry different fitted corrections and the
        ratio drifts to 1.2-1.8 kT/e over the envelope (VER-05).
        """
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
        """Return the dimensionless mobile charge ``sum_i z_i c~_i``.

        The Poisson source is ``S`` times this, and the PHY-08 body force is
        ``-S`` times this times ``grad(phi~)``; the two share the coefficient
        because they are the same charge.
        """
        terms = [
            float(ion.valence) * self.concentrations[ion.name] for ion in self.electrolyte.species
        ]
        total = terms[0]
        for term in terms[1:]:
            total = total + term
        return total

    # -- dimensionless groups ---------------------------------------------

    @property
    def screening(self) -> float:
        """``S = F c_0 L_0^2 / (eps V_T)``, the Poisson and body-force coefficient.

        Equal to ``1/(2 lambda_D^2)`` with ``lambda_D`` in mesh units for a
        symmetric monovalent salt, which is the form ``physics/pb.py`` carries.
        Computed from the definition so that an asymmetric electrolyte, where
        the two differ, is right as well.
        """
        length_m = MESH_LENGTH_UNIT_NM / NM_PER_M
        return (
            FARADAY
            * self.scales.concentration_mol_m3
            * length_m**2
            / (self.scales.permittivity * self.scales.potential_V)
        )

    @property
    def peclet(self) -> float:
        """``Pe = eps V_T^2 / (eta D_0)``, 0.386 at 298.15 K. Length-independent."""
        return self.scales.peclet

    @property
    def reynolds(self) -> float:
        """``Re = rho_0 u_0 L_0 / eta_0``, about 6e-4. Length-independent.

        ``u_0 = eps V_T^2/(eta L_0)`` cancels the ``L_0``, leaving
        ``rho_0 eps V_T^2 / eta_0^2``: inertia is negligible here whatever the
        pore radius, which is why PHY-22 can leave it on without cost.
        """
        return (
            self.electrolyte.mass_density_0
            * self.scales.velocity_m_s
            * self.scales.length_m
            / self.scales.viscosity_Pa_s
        )

    @property
    def packing_coefficients(self) -> Mapping[str, float]:
        """``nu_j = N_A a_j^3 c_0``, the dimensionless packing weight per species.

        ``Phi = sum_j nu_j c~_j`` is then the packing fraction the NUM-17 gate
        watches, and the same coefficients drive the steric flux of PHY-05.
        """
        return {
            ion.name: excluded_volume_m3_per_mol(ion.steric_diameter * NM_PER_M)
            * self.scales.concentration_mol_m3
            for ion in self.electrolyte.species
        }

    def steric_volume_ratio(self, species: str) -> float:
        """Return ``a_i^3 / a_0^3``, the species-dependent steric prefactor.

        4.16 for the reference NaCl parameters (``a_i = 0.5 nm``,
        ``a_0 = 0.311 nm``). PHY-05 records that this is not a normalisation
        that may be dropped.
        """
        ion = self.electrolyte.ion(species)
        return (ion.steric_diameter / self.electrolyte.water_steric_diameter) ** 3

    def permittivity_sensitivity(self, species: str) -> Expression:
        """Return ``d eps~_r / d c~_i``, for the PHY-23 dielectric-decrement terms.

        Obtained by symbolic differentiation of the permittivity expression with
        respect to the concentration it was built from, so it stays consistent
        with whichever correction model is in force — including ``none``, where
        it is identically zero.

        Only used when ``dielectric_gradient_forces`` is enabled, which is a
        deviation from the validated model (PHY-08, PHY-23).
        """
        return self.relative_permittivity().Diff(self.concentrations[species])

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Return what the manifest must record about the coefficients (FR-25)."""
        return {
            "scales": self.scales.summary(),
            "screening": self.screening,
            "peclet": self.peclet,
            "reynolds": self.reynolds,
            "materials": dict(self.electrolyte.provenance),
        }


def species_concentrations_SI(
    coefficients: NondimensionalCoefficients,
) -> Mapping[str, Numeric]:
    """Return the species concentrations in mol/m^3, for the NUM-17 gates.

    ``PackingFractionGate`` sums ``N_A a_j^3 c_j`` with ``c_j`` in mol/m^3, so
    the gate is fed SI concentrations while the solve carries dimensionless
    ones. Converting here keeps the factor in one place.
    """
    scale = coefficients.scales.concentration_mol_m3
    return {name: value * scale for name, value in coefficients.concentrations.items()}
