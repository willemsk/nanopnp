"""The resolved case: the objects a run is made of, as every stage reads them."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from nanopnp.io.case import (
    CaseDocument,
    Contour,
    Density,
    Membrane,
    Pore,
    Reservoir,
    Smearing,
    Structure,
    SuppliedArtefact,
)

if TYPE_CHECKING:
    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.numerics.newton import NewtonSettings
    from nanopnp.physics.models import ModelDeclaration


SOLVE_IRRELEVANT_PROVENANCE = frozenset({"name", "outputs", "schema"})

SOLVE_ALGORITHM_REVISION = 1


@dataclass(frozen=True)
class ResolvedStructure:
    """The ``structure:`` block, with the refusals resolution can make before a file is read."""

    spec: Structure
    n: int
    chains: tuple[str, ...] | None


@dataclass(frozen=True)
class ResolvedProtonation:
    """What the protonation stage is configured with; defaults if there is no charge block."""

    ph: float = 7.5
    forcefield: str = "CHARMM"
    titration: str = "propka"


@dataclass(frozen=True)
class ResolvedCase:
    """A case document turned into the objects a run is made of."""

    document: CaseDocument
    electrolyte: Electrolyte
    concentration_M: float
    temperature_K: float
    bias_V: float
    ground: Literal["cis", "trans"]
    model: str
    model_options: Mapping[str, Any]
    newton: NewtonSettings
    linear_solver: str
    stabilisation: str
    continuation: str
    wall_distance_sources: str
    wall_distance_max_nm: float
    mesh: SuppliedArtefact | None
    charge: SuppliedArtefact | None
    eps_r: SuppliedArtefact | None
    outputs: tuple[str, ...]
    declaration: ModelDeclaration
    essential_boundaries: Mapping[str, str]
    structure: ResolvedStructure | None = None
    density: Density | None = None
    contour: Contour | None = None
    profile: SuppliedArtefact | None = None
    membrane: Membrane | None = None
    reservoir: Reservoir | None = None
    pqr: SuppliedArtefact | None = None
    protonation: ResolvedProtonation = dataclass_field(default_factory=ResolvedProtonation)
    smearing: Smearing = dataclass_field(default_factory=Smearing)
    exclusion_offset_nm: float = 0.0
    dielectric_transition_nm: float = 0.0
    pore: Pore | None = None
    wall_charge_C_m2: float = 0.0
    correction_files: Mapping[str, Path] = dataclass_field(default_factory=dict)

    @property
    def contour_spacing_nm(self) -> float:
        """``h_c``: the density grid spacing, the contour's size target."""
        return contour_spacing_nm(self.document)

    @property
    def derives_eps_r(self) -> bool:
        """Whether stage 7 derives ``chi`` from the stage-4 profile."""
        return self.dielectric_transition_nm > 0.0

    @property
    def protonates(self) -> bool:
        """Whether the protonation stage has a structure or PQR input and no charge input."""
        return (self.structure is not None or self.pqr is not None) and self.charge is None

    @property
    def deposits_charge(self) -> bool:
        """Whether stage 7 deposits a charge from the protonation artefact."""
        return self.protonates and "fixed_charge" in self.declaration.coefficients

    @property
    def name(self) -> str:
        """The case name, which names the run directory in the store."""
        return self.document.name

    @property
    def generates_mesh(self) -> bool:
        """Whether stages 5 and 6 build this case's mesh: it supplies no ``inputs.mesh``."""
        return self.mesh is None

    @property
    def solve_provenance(self) -> dict[str, Any]:
        """Return the part of ``provenance`` that can change a converged field."""
        return {
            key: value
            for key, value in self.provenance.items()
            if key not in SOLVE_IRRELEVANT_PROVENANCE
        }

    @property
    def provenance(self) -> dict[str, Any]:
        """Return what the manifest must record about the resolved case."""
        recorded: dict[str, Any] = {
            "name": self.document.name,
            "schema": self.document.schema_id,
            "model": self.model,
            "model_options": dict(sorted(self.model_options.items())),
            "concentration_M": self.concentration_M,
            "temperature_K": self.temperature_K,
            "bias_V": self.bias_V,
            "ground": self.ground,
            "walls": self.document.boundary_conditions.walls.model_dump(),
            "electrolyte": dict(self.electrolyte.provenance),
            "newton": {
                "initial_damping": self.newton.initial_damping,
                "minimum_damping": self.newton.minimum_damping,
                "recovery_damping": self.newton.recovery_damping,
                "growth_factor": self.newton.growth_factor,
                "max_iterations": self.newton.max_iterations,
                "relative_tolerance": self.newton.relative_tolerance,
                "absolute_tolerance": self.newton.absolute_tolerance,
                "reference_norm": self.newton.reference_norm,
                "field_floor_ratio": self.newton.field_floor_ratio,
            },
            "algorithm_revision": SOLVE_ALGORITHM_REVISION,
            "linear_solver": self.linear_solver,
            "stabilisation": self.stabilisation,
            "continuation": self.continuation,
            "wall_distance": {
                "sources": self.wall_distance_sources,
                "max_distance_nm": self.wall_distance_max_nm,
            },
            # Named here, hashed in stage 7's artefact: a path in the key splits runs on a move.
            "fields": {
                "charge": self.charge is not None,
                "eps_r": self.eps_r is not None,
            },
            "outputs": list(self.outputs),
        }
        if self.wall_charge_C_m2 != 0.0:
            # Only a charged wall is named, so no solve key of a case without one moves.
            recorded["wall_charge_C_m2"] = self.wall_charge_C_m2
        return recorded


def parse_chains(chains: str) -> tuple[str, ...] | None:
    """Return the chain identifiers ``source.chains`` lists, or None for ``all``."""
    if chains.strip() == "all":
        return None
    return tuple(part.strip() for part in chains.split(","))


def contour_spacing_nm(document: CaseDocument) -> float:
    """Return ``h_c``, the density grid spacing the contour is placed on."""
    density = (
        document.geometry.density
        if document.geometry is not None and document.structure is not None
        else Density()
    )
    return density.grid_spacing_nm
