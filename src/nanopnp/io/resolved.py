"""The resolved case: the objects a run is made of, as every stage reads them."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any, Literal

from nanopnp.io.case import (
    CaseDocument,
    ContourSpec,
    DensitySpec,
    MembraneSpec,
    ReservoirSpec,
    SmearingSpec,
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
    spec: Structure
    n: int
    chains: tuple[str, ...] | None


@dataclass(frozen=True)
class ResolvedProtonation:
    ph: float = 7.5
    forcefield: str = "CHARMM"
    titration: str = "propka"


@dataclass(frozen=True)
class ResolvedCase:
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
    density: DensitySpec | None = None
    contour: ContourSpec | None = None
    profile: SuppliedArtefact | None = None
    membrane: MembraneSpec | None = None
    reservoir: ReservoirSpec | None = None
    pqr: SuppliedArtefact | None = None
    protonation: ResolvedProtonation = dataclass_field(default_factory=ResolvedProtonation)
    smearing: SmearingSpec = dataclass_field(default_factory=SmearingSpec)
    exclusion_offset_nm: float = 0.0
    dielectric_transition_nm: float = 0.0

    @property
    def contour_spacing_nm(self) -> float:
        return contour_spacing_nm(self.document)

    @property
    def derives_eps_r(self) -> bool:
        return self.dielectric_transition_nm > 0.0

    @property
    def protonates(self) -> bool:
        return (self.structure is not None or self.pqr is not None) and self.charge is None

    @property
    def deposits_charge(self) -> bool:
        return self.protonates and "fixed_charge" in self.declaration.coefficients

    @property
    def name(self) -> str:
        return self.document.name

    @property
    def generates_mesh(self) -> bool:
        return self.mesh is None

    @property
    def solve_provenance(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.provenance.items()
            if key not in SOLVE_IRRELEVANT_PROVENANCE
        }

    @property
    def provenance(self) -> dict[str, Any]:
        return {
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


def parse_chains(chains: str) -> tuple[str, ...] | None:
    if chains.strip() == "all":
        return None
    return tuple(part.strip() for part in chains.split(","))


def contour_spacing_nm(document: CaseDocument) -> float:
    density = (
        document.geometry.density
        if document.geometry is not None and document.structure is not None
        else DensitySpec()
    )
    return density.grid_spacing_nm
