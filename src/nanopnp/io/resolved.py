"""The resolved case: the objects a run is made of, as every stage reads them.

:func:`nanopnp.pipeline.case.resolve` builds a :class:`ResolvedCase` once from a
validated document, and the walk hands it to every stage as
:attr:`nanopnp.io.artefact.StageInputs.resolved` (WP38 D4). The types live in
the base so that a stage reads a resolved case without importing the registries
that built it: the electrolyte, the Newton settings and the model declaration
are annotations here, never imports at run time (``MOD-04``).
"""

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
"""Provenance keys that cannot change a converged field, so cannot key a solve.

``schema`` is here because a document and its upgrade describe one run: were it
in the key, the next schema move would re-solve every stored case (section 5.3.2
NOTE). It left the key at the move to ``nanopnp/case/v2``, which is the one move
that re-keys a solve.

Named by exclusion rather than by an allow-list: a key added to
:attr:`ResolvedCase.provenance` and forgotten here enters the solve's cache key,
which costs a re-solve, while one forgotten from an allow-list would be dropped
from the key and serve a stale solution for a changed case (section 5.3.2).
"""


@dataclass(frozen=True)
class ResolvedStructure:
    """The ``structure:`` block, with the refusals resolution can make before a file is read.

    Parameters
    ----------
    spec
        The validated block.
    n
        The order of ``symmetry.point_group``.
    chains
        The identifiers ``source.chains`` lists, or ``None`` for ``all``.
    """

    spec: Structure
    n: int
    chains: tuple[str, ...] | None


@dataclass(frozen=True)
class ResolvedProtonation:
    """What the ``protonation`` stage is configured with (PHY-16 step 3, WP27 D13).

    The ``charge:`` block's three protonation keys, at their defaults when the
    case has no ``charge:`` block.
    """

    ph: float = 7.5
    forcefield: str = "CHARMM"
    titration: str = "propka"


@dataclass(frozen=True)
class ResolvedCase:
    """A case document turned into the objects a run is made of.

    Everything here is derived from the document and from the installed data
    files; nothing is read from the environment. Two documents that resolve to
    equal :attr:`provenance` describe the same run, which is the half of FR-26
    that a content hash cannot express (a field nothing records could differ).
    """

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
    """What :attr:`model` admits: its switches, coefficients, solids, strategies and
    quantities (section 5.4.3 NOTE). Filled by ``resolve`` from the model registry,
    so a stage below ``physics`` reads it without importing the registry (WP38 D5)."""
    essential_boundaries: Mapping[str, str]
    """The built model's essential boundaries under the default vocabulary, field by
    region pattern: what stage 6's gate checks a mesh against (WP38 D5)."""
    structure: ResolvedStructure | None = None
    density: DensitySpec | None = None
    """``geometry.density`` on a case carrying ``structure:``, at its defaults when the
    case has no ``geometry:`` block; ``None`` on any other case."""
    contour: ContourSpec | None = None
    """``geometry.contour`` on a case carrying ``structure:``, likewise (WP20 D3)."""
    profile: SuppliedArtefact | None = None
    """``inputs.profile``, which stage 5 reads in place of stage 4's contour (WP21)."""
    membrane: MembraneSpec | None = None
    """``geometry.membrane`` on a case that generates its mesh, at its defaults when the
    case has no ``geometry:`` block; ``None`` on a case supplying ``inputs.mesh``."""
    reservoir: ReservoirSpec | None = None
    """``geometry.reservoir``, likewise."""
    pqr: SuppliedArtefact | None = None
    """``inputs.pqr``, which the ``protonation`` stage reads in place of running PDB2PQR (WP27)."""
    protonation: ResolvedProtonation = dataclass_field(default_factory=ResolvedProtonation)
    """``charge.ph``, ``charge.forcefield`` and ``charge.titration`` (WP27 D13)."""
    smearing: SmearingSpec = dataclass_field(default_factory=SmearingSpec)
    """``charge.smearing``, at its defaults without ``charge:`` (WP28 D10)."""
    exclusion_offset_nm: float = 0.0
    """``charge.exclusion_offset_nm``, ``a``: stage 5's ion-exclusion shell when non-zero (WP30)."""
    dielectric_transition_nm: float = 0.0
    """``charge.dielectric_transition_nm``, ``delta``: stage 7's derived ``chi`` when non-zero."""

    @property
    def contour_spacing_nm(self) -> float:
        """``h_c``: the density grid spacing, the contour's size target (section 5.2.1 NOTE).

        ``geometry.density.grid_spacing_nm`` on a case carrying ``structure:``; its
        default on any other, where :func:`_check_profile` refuses it set away
        from that default.
        """
        return contour_spacing_nm(self.document)

    @property
    def derives_eps_r(self) -> bool:
        """Whether stage 7 derives ``chi`` from the stage-4 profile (section 4.4 NOTE, WP30 D5)."""
        return self.dielectric_transition_nm > 0.0

    @property
    def protonates(self) -> bool:
        """Whether the ``protonation`` stage has something to read (WP27 D3).

        A ``structure:`` section to protonate or an ``inputs.pqr`` to read, and no
        ``inputs.charge``, which would replace what stage 7 makes of either.
        """
        return (self.structure is not None or self.pqr is not None) and self.charge is None

    @property
    def deposits_charge(self) -> bool:
        """Whether stage 7 deposits a charge from the protonation artefact (WP28 D8).

        The case protonates and its model declares ``fixed_charge``: read from the
        declaration, never from the model's name (section 5.4.3 NOTE). Both halves
        of stage 7 then run, and the solve reads the charge from stage 7's
        artefact (D9).
        """
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
        """Return the part of :attr:`provenance` that can change a converged field.

        Section 5.3.2 keys an artefact on "the parameters that produced it", and
        two of the keys in :attr:`provenance` produce nothing: the case's
        ``name`` and its ``outputs``. Neither reaches the mesh, the operator or
        the boundary data, so two cases differing only in them have the same
        solution and must share its cache entry — otherwise adding ``fields`` to
        ``outputs:`` in order to write a picture re-solves a case that has
        already converged, which on the reference pore is minutes of work thrown
        away for a question about post-processing.

        They stay in :attr:`provenance` itself, which is the FR-25 manifest's
        record of what was *asked for* rather than of what was computed: a
        manifest that did not say which quantities the run reported would not
        reconstruct the run (section 5.3.3).
        """
        return {
            key: value
            for key, value in self.provenance.items()
            if key not in SOLVE_IRRELEVANT_PROVENANCE
        }

    @property
    def provenance(self) -> dict[str, Any]:
        """Return what the FR-25 manifest must record about the resolved case.

        The stabilisation mode is here because section 6.4 and section 7.4 make it
        load-bearing: a number recorded without it is not comparable to the
        reference COMSOL run, which was stabilised.
        """
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
            },
            "linear_solver": self.linear_solver,
            "stabilisation": self.stabilisation,
            "continuation": self.continuation,
            "wall_distance": {
                "sources": self.wall_distance_sources,
                "max_distance_nm": self.wall_distance_max_nm,
            },
            # The two supplied fields are named here and hashed elsewhere: the
            # stage-7 artefact carries their contents into the solve's key
            # (section 5.3.2), so recording the *path* here would key two runs
            # differently for a file that merely moved.
            "fields": {
                "charge": self.charge is not None,
                "eps_r": self.eps_r is not None,
            },
            "outputs": list(self.outputs),
        }


def parse_chains(chains: str) -> tuple[str, ...] | None:
    """Return the identifiers ``structure.source.chains`` lists, or ``None`` for ``all``.

    The key is ``all`` or a comma-separated list of chain identifiers (section
    5.3.1 NOTE on ``structure:``). Whitespace around an identifier is dropped.
    """
    if chains.strip() == "all":
        return None
    return tuple(part.strip() for part in chains.split(","))


def contour_spacing_nm(document: CaseDocument) -> float:
    """Return ``h_c``, the density grid spacing the contour is placed on (section 5.2.1 NOTE).

    ``geometry.density`` counts only beside ``structure:``: on any other case
    stages 2 to 4 do not run, and :func:`_check_profile` refuses it set.
    """
    density = (
        document.geometry.density
        if document.geometry is not None and document.structure is not None
        else DensitySpec()
    )
    return density.grid_spacing_nm
