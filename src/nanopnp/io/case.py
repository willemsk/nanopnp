"""The ``nanopnp/case/v2`` case-file schema, and its resolution to runnable objects.

One declarative YAML document is the unit of reproducibility (IF-03,
``SPECIFICATION.md`` section 5.3.1); everything else is derived. This module owns
its shape, its diagnostics and the step that turns it into the objects the solver
takes.

Three things it deliberately does, each with a failure it exists to prevent.

**The ``schema:`` string is checked before structural validation.** A file
written to a future schema then fails naming the schema it claims, rather than
with a wall of field errors against a shape it never declared. This copies
:func:`nanopnp.materials.corrections.load_corrections` exactly, ordering
included.

**A ``nanopnp/case/v1`` document is read as its upgrade.** :func:`upgrade_v1`
maps the v1 mapping onto v2 before validation (section 5.3.1 v2 NOTE), so
there is one model to maintain rather than one per schema; the frozen v1 field
tree it is held to lives in the tests (VER-47).

**Every model forbids unknown keys, and the diagnostic names the key.** IF-03
requires that; pydantic's own message does not carry it (the key is in ``loc``,
not in ``msg``), so :class:`CaseValidationError` renders one line per error as
``<dotted.path>: <what>`` and offers a suggestion from the owning model's fields.
A typo in ``corrections`` would otherwise disable a correction silently, which is
the failure PHY-21's differential testing exists to catch.

**The round trip is asserted on the content hash, never on the text** (FR-26,
VER-09). A case written by hand omits defaults, orders keys freely and carries
comments, none of which survive a round trip and none of which change the run.
:func:`resolve` produces the objects, and :attr:`ResolvedCase.provenance` the
record; equality of either is a statement about the *run*, which is what FR-26
means by "semantically identical".
"""

from __future__ import annotations

import copy
import difflib
import itertools
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any, Literal, TypeAlias, get_args, get_origin

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator
from pydantic.fields import FieldInfo

from nanopnp.charge.fields import FIELD_FORMAT
from nanopnp.core.paths import available_corrections
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import CASE_SCHEMA, CASE_SCHEMA_V1, CaseArtefact, StageInputs
from nanopnp.materials.electrolyte import (
    CorrectionChoice,
    CorrectionSwitches,
    Electrolyte,
)
from nanopnp.physics.models import (
    LADDER_STRATEGY,
    SWITCHES,
    PhysicsModel,
    create,
    declaration,
    inf_sup_problem,
    registered_models,
    registered_stabilisations,
)
from nanopnp.solve.linear import AVAILABLE_SOLVERS
from nanopnp.solve.newton import DEFAULT_SETTINGS, NewtonSettings

SCHEMA: str = CASE_SCHEMA
"""Schema identifier every case file must declare.

Defined in :mod:`nanopnp.io.artefact` beside the artefact that carries it, so
that the string a case file declares and the string the store addresses it by
cannot drift apart.
"""

V2_ADDED: tuple[str, ...] = (
    "inputs.profile",
    "inputs.pqr",
    "structure.source.selection",
    "geometry.membrane.centre_z_nm",
    "charge.exclusion_offset_nm",
    "charge.dielectric_transition_nm",
    "numerics.mesh.size_scale",
)
"""Paths ``nanopnp/case/v2`` added to v1; a v1 document carrying one is refused (section 5.3.1)."""

V2_RENAMED: dict[str, str] = {"structure.source.pdb": "structure.source.path"}
"""v1 path to the v2 path that replaced it. IF-04 reads mmCIF as well as PDB."""

V2_MOVED: dict[str, str] = {
    "charge.eps_protein": "physics.solid_permittivities.protein",
    "geometry.membrane.eps_r": "physics.solid_permittivities.membrane",
}
"""v1 path to the v2 entry its value moves to. ``physics.solid_permittivities`` is
the one place a solid's permittivity is set (PHY-20; author ruling, 24 September 2026)."""

FieldType: TypeAlias = Any
"""The type the case schema declares at one dotted path.

A ``type``, a ``Literal[...]``, a union or a parameterised container -- whatever
pydantic put on the field. The alias names what the value *is* where the checker
can only say ``Any`` (the house convention of :mod:`nanopnp.core.typing`)."""

FieldValue: TypeAlias = Any
"""A value one case-file field can hold: a bool, a number, a string, a path, or
a block of them. Constrained by the schema per field; a walk over dotted paths
sees the union."""

CORRECTION_PROPERTIES: tuple[str, ...] = (
    "diffusivity",
    "mobility",
    "viscosity",
    "permittivity",
    "density",
)
"""The five properties carrying a concentration-and-wall correction (PHY-22).

Named once because two things index the case by them: :meth:`CaseDocument._check_registries`,
which refuses a model that is not installed, and :func:`registry_options`, which
tells an editor what to offer. A list that offered a sixth property the check
never validated would be an editor offering a correction the solver ignores.
"""

STERIC_MODELS: frozenset[str] = frozenset({"none", "borukhov"})
"""Steric models: the Borukhov size-modified flux, or off (PHY-22)."""

OUTPUTS: frozenset[str] = frozenset(
    {
        "current",
        "transport_numbers",
        "rectification",
        "eof_rate",
        "analyte_force",
        "fields",
    }
)
"""Selectable outputs, per the section 5.3.1 example."""


class CaseValidationError(ValueError):
    """A case document failed validation; the message names every offending key.

    Wraps pydantic's :class:`~pydantic.ValidationError` rather than replacing it:
    the underlying error is kept on :attr:`errors` so a caller can inspect it,
    and the rendering is what IF-03 requires — the dotted path to the key, what
    is wrong with it, and, for an unknown key, the nearest field name of the
    block that rejected it.
    """

    def __init__(self, message: str, errors: ValidationError | None = None) -> None:
        super().__init__(message)
        self.errors = errors


class UnsupportedCaseSection(NotImplementedError):  # noqa: N818 - a release gap, not a failure
    """The case asks for a pipeline stage this release does not implement.

    Raised by :func:`resolve` naming the section and the release that owns it,
    so that a Phase-2 case run against the solver core says which release will
    run it rather than failing somewhere inside the solver.
    """


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


# -- inputs: hand-substituted upstream artefacts (FR-27, section 5.3.1) --------


class SuppliedArtefact(_Strict):
    """One upstream stage output supplied from outside the pipeline.

    FR-27 grants that any artefact may be substituted by hand; this is that
    substitution applied at stage granularity. A stage whose output is supplied
    does not run, and neither does anything upstream of it — which is how the
    solver core runs a real case before the meshing and charge pipelines exist
    (section 8.1).

    Exactly one of ``path`` and ``artefact`` is given: a file on disk, or the
    hash of an artefact already in the store. The store form is what keeps a
    sweep from re-hashing the same mesh at every operating point.
    """

    path: Path | None = None
    artefact: str | None = None
    format: str | None = None
    groups: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _exactly_one_source(self) -> SuppliedArtefact:
        """Reject a supplied artefact that names neither or both of its sources."""
        if (self.path is None) == (self.artefact is None):
            raise ValueError(
                "a supplied artefact names exactly one of path: (a file on disk) and artefact: "
                "(a content hash already in the store)"
            )
        return self


class Inputs(_Strict):
    """Supplied upstream artefacts, by the stage whose output each replaces."""

    mesh: SuppliedArtefact | None = None
    charge: SuppliedArtefact | None = None
    eps_r: SuppliedArtefact | None = None
    profile: SuppliedArtefact | None = None
    pqr: SuppliedArtefact | None = None


# -- structure, geometry and charge: phases 2 and 3 ---------------------------


class StructureSource(_Strict):
    """The structure file and which of it to use.

    ``selection`` is an MDAnalysis selection string. The bilayer is absent from
    the density map (section 5.2, stages 3 and 5), and an ensemble archive may
    carry lipids and waters, so what counts as the pore is said here rather than
    assumed.
    """

    path: Path = Field(
        description=(
            "A PDB or mmCIF file, optionally gzipped (.pdb, .ent, .cif, .mmcif). MDAnalysis reads "
            "PDB and gemmi reads mmCIF. The file's +z SHALL point from the trans side to the cis "
            "side, and every selected atom SHALL carry its element in the file"
        )
    )
    variant: str | None = Field(
        default=None,
        description=(
            "A label for the prepared structure (OPN-04). It is recorded in the manifest through "
            "the case and keys no stage: relabelling does not re-run anything"
        ),
    )
    chains: str = Field(
        default="all",
        description=(
            "`all`, or a comma-separated list of chain identifiers. A chain is its chain "
            "identifier, or its segment identifier where the chain column is blank. The selected "
            "chains SHALL number the point group's n (FR-03)"
        ),
    )
    selection: str = Field(
        default="protein",
        description="An MDAnalysis selection applied to the file; alternate locations are refused",
    )


class Frames(_Strict):
    """Which trajectory frames enter the ensemble average."""

    last_ns: float | None = Field(
        default=None,
        description=(
            "Keep the frames within this many ns of the last, by the times the file records; "
            "refused beyond the recorded span plus one frame interval"
        ),
    )
    count: int | None = Field(
        default=None,
        description=(
            "Keep this many frames at the uniform stride floor(N/count), ending on the last "
            "frame of the window of N"
        ),
    )


class Ensemble(_Strict):
    """The trajectory and its frame selection."""

    trajectory: Path | None = Field(
        default=None,
        description=(
            "A DCD, XTC, TRR or NetCDF trajectory whose frames are the ensemble; without one, "
            "the models of the source file are. Every frame is superposed on the C-alpha of the "
            "earliest selected frame (FR-01)"
        ),
    )
    frames: Frames = Field(default_factory=Frames)


class SymmetrySpec(_Strict):
    """The expected point group and how the axis is found."""

    point_group: str = Field(description="C<n> with n >= 1, e.g. C12 for ClyA (FR-03)")
    axis: Literal["auto", "z"] = Field(
        default="auto",
        description=(
            "`auto`: the Cn axis by chain-permutation superposition, gated on the chains' "
            "spacing, the rotation angle and a 10 degree limit from the file's z (FR-02). `z`: "
            "the file's z axis through its origin, refused where n >= 2 and it strays more than "
            "0.01 nm from the detected axis over the C-alpha extent"
        ),
    )


class Structure(_Strict):
    """Stage 1: structure ingestion and alignment (v0.3).

    The normative contract is the section 5.3.1 NOTE on ``structure:``.
    """

    source: StructureSource
    ensemble: Ensemble = Field(default_factory=Ensemble)
    symmetry: SymmetrySpec


class DensitySpec(_Strict):
    """Stage 2: Gaussian smearing to a grid."""

    grid_spacing_nm: float = 0.05
    kernel: Literal["gaussian_vdw"] = "gaussian_vdw"
    sharpness: float = 0.93


class ContourSpec(_Strict):
    """Stage 4: contour extraction and conditioning.

    The normative contract is the section 5.3.1 NOTE on ``geometry.contour``. No
    other contour parameter and no gate threshold is a case key: they are the
    constants of section 5.2.1, and they key the stage-4 artefact (WP17 D3).
    """

    isolevel: float = Field(
        default=0.25,
        description=(
            "The density isolevel whose contour is the pore wall, finite and in (0, 1). The "
            "source work used 0.25 without a sensitivity study (section 5.3.1 NOTE on "
            "geometry.contour)"
        ),
    )
    smoothing: Literal["taubin", "none"] = Field(
        default="taubin",
        description=(
            "`taubin`: resample at arc length h/2, then ten Taubin passes of lambda 0.5 and mu "
            "-0.53, which keep the enclosed area where Laplacian smoothing shrinks it. `none` "
            "skips both (section 5.2.1)"
        ),
    )
    simplify_tol_nm: float = Field(
        default=0.02,
        description=(
            "The Douglas-Peucker tolerance, finite, positive and below the density grid "
            "spacing h: a larger one discards resolved geometry and breaks the margin of the "
            "closing of radius 2h that the feature-size gate relies on (section 5.2.1 NOTE)"
        ),
    )


class MembraneSpec(_Strict):
    """The bilayer, defined analytically rather than from the density map.

    ``centre_z_nm`` is the bilayer's centre along the axis, in the structure's
    frame. Its permittivity is ``physics.solid_permittivities.membrane``, the one
    place it is set (PHY-20).
    """

    thickness_nm: float = 2.8
    centre_z_nm: float = 0.0


class ReservoirSpec(_Strict):
    """The reservoir half-disc."""

    radius_nm: float = 250.0


class AnalyteSpec(_Strict):
    """An axisymmetric analyte body in the pore (PHY-11, WP6)."""

    shape: Literal["sphere", "prolate_spheroid", "oblate_spheroid"]
    a_nm: float
    b_nm: float | None = None
    z_nm: float = 0.0
    charge_e: float = 0.0


class Geometry(_Strict):
    """Stages 2-5: density, contour, membrane, reservoir and analyte."""

    density: DensitySpec = Field(default_factory=DensitySpec)
    contour: ContourSpec = Field(default_factory=ContourSpec)
    membrane: MembraneSpec = Field(default_factory=MembraneSpec)
    reservoir: ReservoirSpec = Field(default_factory=ReservoirSpec)
    analyte: AnalyteSpec | None = None


class SmearingSpec(_Strict):
    """Stage 7: the kernel width and the export lattice of the deposition (PHY-16 steps 4-6).

    ``sharpness`` is the ``0.5`` of ``w_i = 0.5 R_i``, a switch; ``grid_spacing_nm``
    the export lattice's spacing, a discretisation choice; ``axis_cutoff_nm`` is
    refused away from its default on every path, naming PHY-18 (section 5.3.1 NOTE
    on ``charge.smearing``).
    """

    sharpness: float = 0.5
    grid_spacing_nm: float = 0.005
    axis_cutoff_nm: float = 0.01


class Charge(_Strict):
    """Stage 7: charge assembly (v0.4).

    ``exclusion_offset_nm`` is FR-15's fitted exclusion offset and
    ``dielectric_transition_nm`` the width of PHY-20's transition to ``eps_w``.
    Both are switches whose validated default is ``0``: the validated model has no
    exclusion shell and a sharp material permittivity (section 5.3.1 NOTE). The
    protein's permittivity is ``physics.solid_permittivities.protein`` (PHY-20).
    """

    ph: float = Field(
        default=7.5,
        ge=0.0,
        le=14.0,
        allow_inf_nan=False,
        description=(
            "The pH PROPKA assigns protonation states at, in [0, 14] (PHY-16 step 3). A condition "
            "of the experiment, not a deviation; refused away from its default beside "
            "titration: none, where it reaches no calculation"
        ),
    )
    forcefield: Literal["CHARMM", "PEOEPB", "SWANSON"] = Field(
        default="CHARMM",
        description=(
            "The PDB2PQR force field, passed as both --ff and --ffout. AMBER, PARSE and TYL06 give "
            "charged atoms a zero radius and are refused (section 5.3.1 NOTE on the protonation "
            "keys)"
        ),
    )
    titration: Literal["propka", "none"] = Field(
        default="propka",
        description=(
            "propka: PROPKA's states at charge.ph. none: every residue keeps the force field's "
            "standard state"
        ),
    )
    smearing: SmearingSpec = Field(default_factory=SmearingSpec)
    exclusion_offset_nm: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    dielectric_transition_nm: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)


# -- electrolyte --------------------------------------------------------------


class SpeciesSpec(_Strict):
    """One solved ionic species, by the name the parameter file gives it."""

    name: str
    z: int


class CorrectionChoiceSpec(_Strict):
    """One property's correction: a registered model, and its two parts (PHY-22).

    ``model: none`` disables the correction by selecting the registered ``none``
    model, never by taking a code branch. The concentration and wall parts switch
    independently, which is what makes an ablation study a configuration sweep.
    """

    model: str = "none"
    concentration: bool = True
    wall: bool = True

    def to_choice(self) -> CorrectionChoice:
        """Return the materials-layer choice this names."""
        return CorrectionChoice(model=self.model, concentration=self.concentration, wall=self.wall)


class StericSpec(_Strict):
    """The size-modified flux ``beta_i`` and the diameters it is built on (PHY-22).

    ``a_ion_nm`` and ``a_water_nm`` are optional, and when given are **checked
    against the parameter file** rather than used: the diameters belong to the
    fitted parameter set, and a case file that could override them silently
    would be a second source of truth for a physical constant (FR-16).
    """

    model: Literal["none", "borukhov"] = "none"
    a_ion_nm: float | None = None
    a_water_nm: float | None = None


class CorrectionsSpec(_Strict):
    """The nine independently switchable corrections of PHY-22."""

    diffusivity: CorrectionChoiceSpec = Field(default_factory=CorrectionChoiceSpec)
    mobility: CorrectionChoiceSpec = Field(default_factory=CorrectionChoiceSpec)
    viscosity: CorrectionChoiceSpec = Field(default_factory=CorrectionChoiceSpec)
    permittivity: CorrectionChoiceSpec = Field(default_factory=CorrectionChoiceSpec)
    density: CorrectionChoiceSpec = Field(default_factory=CorrectionChoiceSpec)
    steric: StericSpec = Field(default_factory=StericSpec)


class ElectrolyteSpec(_Strict):
    """Stage 8: the electrolyte, its reference parameter file and its corrections.

    ``parameters`` names the file the *reference* properties come from —
    ``D_i^0``, ``eta^0``, ``rho^0``, ``eps_r,f^0`` and the steric diameters —
    and is separate from the per-property correction models because a classical
    PNP-NS run turns every correction off and still needs those reference values
    (PHY-21).
    """

    species: list[SpeciesSpec]
    concentration_M: float
    temperature_K: float = 298.15
    parameters: str = "willems2020_nacl"
    driver: Literal["average", "ionic_strength"] = "average"
    corrections: CorrectionsSpec = Field(default_factory=CorrectionsSpec)


# -- boundary conditions, physics and numerics --------------------------------


class WallSpec(_Strict):
    """The conditions applied on the pore and membrane walls.

    The values name the condition **applied**, not its absence: under the
    ``r``-weighted forms of section 6.2 the natural condition is the free one, so
    a value reading as "none applied" would silently remove no-slip while
    appearing to be the validated default.
    """

    ion_flux: Literal["no_flux", "prescribed"] = "no_flux"
    slip: Literal["no_slip", "navier", "free"] = "no_slip"


class BoundaryConditions(_Strict):
    """The applied bias, the grounded electrode and the wall conditions."""

    bias_V: float
    ground: Literal["cis", "trans"] = "cis"
    walls: WallSpec = Field(default_factory=WallSpec)


class PhysicsSpec(_Strict):
    """The named physics model of PHY-21 and the switches it carries.

    ``solid_permittivities`` is the one member that is not a switch: it is the
    relative permittivity of each non-fluid domain of the mesh, keyed by the
    material name the boundary vocabulary gives it (section 5.3.1). Poisson is
    solved over the solids too, so a domain with no entry silently takes the
    electrolyte's ``eps_r`` — about 24 times too large in a bilayer — which is
    why :func:`nanopnp.mesh.ingest.check_solid_permittivities` aborts on one.
    PHY-20 gives 3.2 for the membrane and 20 for the protein and the analyte;
    they are not defaulted here because the mesh decides which solids exist.
    """

    model: str = "epnp-ns"
    flow: bool = True
    variable_density: bool = True
    inertia: bool = True
    dielectric_gradient_forces: bool = False
    solid_permittivities: dict[str, float] = Field(default_factory=dict)


class ElementsSpec(_Strict):
    """Element orders per field; the Taylor-Hood pair of NUM-03.

    ``u`` is independent of ``phi`` and ``c``. The reference model of section 6.4
    runs ``phi`` and ``c`` at P2 with ``u`` and ``p`` at P1, which is neither the
    Taylor-Hood pair nor one order throughout, and is legal only because the flow
    stabilisation supplies the missing inf-sup stability — :func:`resolve` refuses
    an equal-order pair in a mode that does not.
    """

    phi: str = "P2"
    c: str = "P2"
    u: str = "P2"
    p: str = "P1"


class MeshSpec(_Strict):
    """Stage 6: the mesher and its size field (v0.3).

    ``size_scale`` multiplies every element-size target of section 5.2.2 and
    NUM-30, the resolved ``wall_h_nm`` included, so that a mesh-convergence study
    (RSK-09, section 6.8) is a sweep over this field (FR-24) rather than a code
    edit. A discretisation choice recorded with the mesh, not a deviation.
    """

    backend: Literal["netgen", "gmsh"] = "netgen"
    wall_h_nm: float | Literal["auto"] = "auto"
    size_scale: float = Field(default=1.0, gt=0.0, allow_inf_nan=False)
    boundary_layer: bool = False


class NonlinearSpec(_Strict):
    """The damped-Newton policy; the defaults are the NUM-16 reference settings."""

    strategy: Literal["newton", "hybrid"] = "newton"
    damping: Literal["residual", "backtracking"] = "residual"
    max_iter: int = 100
    rtol: float = 1.0e-6


class LinearSpec(_Strict):
    """The direct linear solver of section 6.6."""

    solver: Literal["umfpack", "superlu"] = "umfpack"


class WallDistanceSpec(_Strict):
    """The PHY-02 distance field: which boundaries it measures from, and its cap.

    ``sources`` is a boundary-name regular expression. The validated default is
    the pore wall alone: PHY-02 excludes the membrane from the source set
    deliberately, so widening this is a deviation from the validated model and is
    recorded as one.
    """

    sources: str = "wall"
    max_distance_nm: float = 3.0


class NumericsSpec(_Strict):
    """Discretisation, meshing, continuation, stabilisation and the solvers."""

    elements: ElementsSpec = Field(default_factory=ElementsSpec)
    mesh: MeshSpec = Field(default_factory=MeshSpec)
    nonlinear: NonlinearSpec = Field(default_factory=NonlinearSpec)
    continuation: Literal["default_ladder", "none"] = "default_ladder"
    stabilisation: Literal["none", "supg", "reference"] = "none"
    wall_distance: WallDistanceSpec = Field(default_factory=WallDistanceSpec)
    linear: LinearSpec = Field(default_factory=LinearSpec)


class CaseDocument(_Strict):
    """A validated case file (schema ``nanopnp/case/v2``).

    ``schema`` is carried under an alias so the reserved name does not shadow
    ``BaseModel``, exactly as :class:`nanopnp.materials.corrections.CorrectionDocument`
    does.
    """

    schema_id: str = Field(alias="schema")
    name: str
    inputs: Inputs = Field(default_factory=Inputs)
    structure: Structure | None = None
    geometry: Geometry | None = None
    charge: Charge | None = None
    electrolyte: ElectrolyteSpec
    boundary_conditions: BoundaryConditions
    physics: PhysicsSpec = Field(default_factory=PhysicsSpec)
    numerics: NumericsSpec = Field(default_factory=NumericsSpec)
    outputs: list[str] = Field(default_factory=lambda: ["current"])

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _check_registries(self) -> CaseDocument:
        """Check every name that must resolve to something installed.

        Raises
        ------
        ValueError
            Naming the value and the installed alternatives. Doing this here
            rather than at solve time is what stops a misspelt correction model
            from disabling a correction silently: ``models.create`` would raise,
            but only after the ladder had already been built.
        """
        problems: list[str] = []
        if self.physics.model not in registered_models():
            problems.append(
                f"physics.model {self.physics.model!r} is not registered; the models are "
                f"{', '.join(registered_models())}"
            )
        if self.numerics.stabilisation not in registered_stabilisations():
            problems.append(
                f"numerics.stabilisation {self.numerics.stabilisation!r} is not a registered "
                f"mode; the available modes are {', '.join(registered_stabilisations())}. "
                "Recording a mode the solver does not apply would make the FR-25 manifest "
                "describe a run that never happened"
            )
        if self.numerics.linear.solver not in AVAILABLE_SOLVERS:
            problems.append(
                f"numerics.linear.solver {self.numerics.linear.solver!r} is not available; the "
                f"solvers are {', '.join(sorted(AVAILABLE_SOLVERS))}"
            )
        installed = available_corrections()
        for name in CORRECTION_PROPERTIES:
            choice: CorrectionChoiceSpec = getattr(self.electrolyte.corrections, name)
            if choice.model != "none" and choice.model not in installed:
                problems.append(
                    f"electrolyte.corrections.{name}.model {choice.model!r} is not installed; the "
                    f"correction files are {', '.join(installed) or 'none'}"
                )
        if self.electrolyte.parameters not in installed:
            problems.append(
                f"electrolyte.parameters {self.electrolyte.parameters!r} is not installed; the "
                f"correction files are {', '.join(installed) or 'none'}"
            )
        unknown = sorted(set(self.outputs) - OUTPUTS)
        if unknown:
            problems.append(
                f"outputs {', '.join(unknown)} are not selectable; the outputs are "
                f"{', '.join(sorted(OUTPUTS))}"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @model_validator(mode="after")
    def _check_supplied(self) -> CaseDocument:
        """Refuse a supplied artefact beside one it makes unread, and an idle knob.

        Section 5.3.1: a stage whose output is supplied does not run, and neither
        does anything upstream of it, so an upstream artefact supplied beside a
        downstream one would be hashed into the FR-25 manifest as an input to a
        run that never read it. Every ``numerics.mesh`` key configures the
        mesher, and beside a supplied mesh there is no mesher (section 5.3.1 NOTE
        on ``numerics.mesh``, WP21 D14).

        Raises
        ------
        ValueError
            Naming both artefacts, or each mesh key and the supplied mesh.
        """
        problems: list[str] = []
        for chain in SUPPLY_CHAINS:
            given = [name for name in chain if getattr(self.inputs, name) is not None]
            for upstream, downstream in itertools.pairwise(given):
                problems.append(
                    f"inputs.{upstream} and inputs.{downstream} are both supplied, but "
                    f"{downstream} is downstream of {upstream} on one chain "
                    f"({' -> '.join(chain)}), so inputs.{upstream} would be recorded as an input "
                    "to a run that never read it; supply one of them"
                )
        if self.inputs.mesh is not None:
            defaults = MeshSpec()
            for key in MeshSpec.model_fields:
                value = getattr(self.numerics.mesh, key)
                if value == getattr(defaults, key):
                    continue
                problems.append(
                    f"numerics.mesh.{key} is {value!r} beside inputs.mesh; it configures the "
                    "mesher, and a supplied mesh is not meshed, so it would have no effect; "
                    f"remove it or remove inputs.mesh"
                )
        if problems:
            raise ValueError("; ".join(problems))
        return self


SUPPLY_CHAINS: tuple[tuple[str, ...], ...] = (("profile", "mesh"), ("pqr", "charge"))
"""The ``inputs:`` keys on each chain of section 5.3.1, upstream first.

The chains are structure -> density -> profile -> mesh and structure -> PQR ->
charge field; these are the members ``inputs:`` can carry. ``eps_r`` comes from
the density on a branch of its own (FR-15) and is on neither.
"""


# -- what a value may be: the schema's own type, and the live registries -------


def registry_options(path: str) -> tuple[str, ...] | None:
    """Return the values an installed registry admits at a dotted path.

    The same registries :meth:`CaseDocument._check_registries` asks, indexed by
    the path its diagnostic names, so that a generated editor offers exactly the
    values a document would be accepted with. It lives here rather than in
    ``gui/`` for that reason: a second list of stabilisation modes would be a
    GUI offering a mode the solver does not apply, which is a manifest
    describing a run that never happened (§5.3.3).

    Parameters
    ----------
    path
        A dotted case-file path.

    Returns
    -------
    tuple of str or None
        The admissible values, or ``None`` where no registry governs the path —
        which is not the same as "anything": the schema's declared type still
        does, through :func:`options_at`.
    """
    if path == "physics.model":
        return registered_models()
    if path == "numerics.stabilisation":
        return registered_stabilisations()
    if path == "numerics.linear.solver":
        return tuple(sorted(AVAILABLE_SOLVERS))
    if path == "electrolyte.parameters":
        return available_corrections()
    if path in _CORRECTION_MODEL_PATHS:
        # ``none`` disables a correction by selecting the registered ``none``
        # model rather than by taking a code branch (PHY-22), so it is offered
        # beside the installed parameter files and is not one of them.
        return ("none", *available_corrections())
    if path == "outputs":
        return tuple(sorted(OUTPUTS))
    return None


_CORRECTION_MODEL_PATHS: frozenset[str] = frozenset(
    f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES
)
"""The five correction-model paths, built from :data:`CORRECTION_PROPERTIES`."""


def options_at(path: str) -> tuple[str, ...] | None:
    """Return every value a case document would be accepted with at a path.

    The **intersection** of what the schema's declared type accepts and what the
    installed registries admit, because :class:`CaseDocument` requires both: a
    ``Literal`` member no registry has is refused by ``_check_registries``, and a
    registered name outside the ``Literal`` is refused by the type. Offering
    either alone would offer a value that cannot be saved.

    Parameters
    ----------
    path
        A dotted case-file path.

    Returns
    -------
    tuple of str or None
        The admissible values in the schema's own order where it declares them,
        or ``None`` for a field whose values are not enumerable — a number, a
        free string, a path.

    Raises
    ------
    UnknownCasePathError
        If the path is not one the schema declares.
    """
    reference = field_at(path)
    literal = _literal_options(reference.annotation)
    registered = registry_options(path)
    if literal is None:
        return registered
    if registered is None:
        return literal
    admitted = set(registered)
    return tuple(value for value in literal if value in admitted)


def _literal_options(annotation: FieldType) -> tuple[str, ...] | None:
    """Return the members of a ``Literal``, looking through a union and a list.

    ``list[str]`` and ``float | Literal["auto"]`` both reach here: the first
    carries no ``Literal`` and enumerates nothing, and the second enumerates only
    ``auto``, which is exactly what an editor should offer beside a free numeric
    entry.
    """
    for candidate in (annotation, *get_args(annotation)):
        if get_origin(candidate) is Literal:
            return tuple(str(value) for value in get_args(candidate))
    return None


# -- diagnostics --------------------------------------------------------------


def _model_of(annotation: object) -> type[BaseModel] | None:
    """Return the model class an annotation carries, if it carries exactly one.

    Walks ``X | None`` and ``list[X]`` alike, so that the owner of a key inside
    ``electrolyte.species[0]`` is found as readily as one inside ``numerics``.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for argument in get_args(annotation):
        found = _model_of(argument)
        if found is not None:
            return found
    return None


def _owner_of(loc: Sequence[str | int]) -> type[BaseModel]:
    """Return the model whose fields the last element of ``loc`` was checked against."""
    owner: type[BaseModel] = CaseDocument
    for key in loc[:-1]:
        if isinstance(key, int):
            continue
        field = owner.model_fields.get(key)
        if field is None:
            break
        nested = _model_of(field.annotation)
        if nested is None:
            break
        owner = nested
    return owner


def _keys_of(model: type[BaseModel]) -> list[str]:
    """Return the names a block accepts, under the aliases a case file writes."""
    return sorted(field.alias or name for name, field in model.model_fields.items())


def render_problems(source: str, error: ValidationError) -> str:
    """Render a pydantic error as one ``<dotted.path>: <what>`` line per problem.

    Public because the sweep document of §5.3.4 is an IF-03 configuration file
    too, and its diagnostics must be the ones a case file gets rather than
    pydantic's own — a second rendering would be a second thing to keep right.

    IF-03 requires the offending key be named. pydantic reports ``extra_forbidden``
    with the key in ``loc`` and a message that does not carry it, so the key is
    read out of ``loc`` and, for an unknown one, the nearest accepted name of the
    block that rejected it is offered.
    """
    problems = error.errors()
    lines = [f"{source}: {len(problems)} problem(s) in the case document"]
    for problem in problems:
        loc = problem["loc"]
        dotted = ".".join(str(part) for part in loc) if loc else "<document>"
        if problem["type"] == "extra_forbidden":
            replaced = _v2_replacement(loc)
            if replaced is not None:
                lines.append(f"  {dotted}: unknown key; {replaced}")
                continue
            accepted = _keys_of(_owner_of(loc))
            close = difflib.get_close_matches(str(loc[-1]), accepted, n=1)
            hint = (
                f"did you mean {close[0]!r}?"
                if close
                else f"this block accepts {', '.join(accepted)}"
            )
            lines.append(f"  {dotted}: unknown key; {hint}")
        else:
            lines.append(f"  {dotted}: {problem['msg']}")
    return "\n".join(lines)


def _v2_replacement(loc: Sequence[str | int]) -> str | None:
    """Return what replaced a v1 key that a v2 document still uses, if it is one.

    A v2 document writing ``charge.eps_protein`` would otherwise be told the
    nearest field name of ``charge:``, which is no help: the key was moved to
    another block, and a calibration parameter a reader believed was set would
    be dropped with a spelling hint (section 5.3.1 v2 NOTE).
    """
    path = ".".join(str(part) for part in loc if not isinstance(part, int))
    if path in V2_RENAMED:
        return f"{CASE_SCHEMA} renamed it to {V2_RENAMED[path]}"
    if path in V2_MOVED:
        return (
            f"{CASE_SCHEMA} removed it; the value is set as {V2_MOVED[path]}, the one place a "
            "solid's permittivity is set (PHY-20)"
        )
    return None


# -- dotted paths: reading, checking and substituting -------------------------


class UnknownCasePathError(KeyError):
    """A dotted path does not name a field of the case schema (IF-03, FR-24).

    Raised by :func:`field_at` before anything is read or written, so that a
    misspelt sweep axis is refused at plan time by the component that is wrong
    rather than a day later by a member that solved something else. A
    :class:`KeyError` still, so a caller written against the mapping-like
    reading of a path keeps working, but a *named* one: the CLI classifies it as
    the case error it is (IF-02).
    """

    def __str__(self) -> str:
        """Return the message as written, without :class:`KeyError`'s quoting."""
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class FieldReference:
    """One field of the case schema, found by its dotted path.

    Parameters
    ----------
    path
        The dotted path, as it was given.
    annotation
        The type the schema declares at that path. For an entry of a mapping- or
        sequence-valued field it is the *element* type, which is what a value
        written there has to satisfy.
    container
        ``"model"`` for a declared field of a block, ``"mapping"`` for an entry
        of a ``dict``-valued one, ``"sequence"`` for an element of a list. The
        distinction matters to substitution: a mapping entry may be created, a
        model field may not, and a sequence index must already exist.
    """

    path: str
    annotation: FieldType
    container: Literal["model", "mapping", "sequence"] = "model"

    def validate(self, value: FieldValue) -> FieldValue:
        """Return ``value`` as the schema's declared type accepts it.

        Raises
        ------
        CaseValidationError
            If the declared type refuses it, naming the path, the value and
            what was expected. Re-validating the whole document would catch this
            too, but only per point and only after a plan has committed to
            thousands of them (FR-24).
        """
        try:
            return TypeAdapter(self.annotation).validate_python(value)
        except ValidationError as error:
            reasons = "; ".join(problem["msg"] for problem in error.errors())
            raise CaseValidationError(
                f"{self.path}: {value!r} is not a value this field accepts "
                f"({_annotation_name(self.annotation)}): {reasons}"
            ) from None


def _annotation_name(annotation: FieldType) -> str:
    """Return a readable name for a declared type, for a diagnostic."""
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def _entry_annotation(
    annotation: FieldType,
) -> tuple[FieldType, Literal["mapping", "sequence"]] | None:
    """Return the element type of a mapping- or sequence-valued annotation.

    ``dict[str, float]`` gives ``(float, "mapping")`` and ``list[str]`` gives
    ``(str, "sequence")``; anything else gives ``None``. Walking through the
    container is what lets a sweep vary ``physics.solid_permittivities.membrane``
    or one entry of ``electrolyte.species`` without a second path syntax.
    """
    for candidate in (annotation, *get_args(annotation)):
        origin = get_origin(candidate)
        arguments = get_args(candidate)
        if origin in (dict, Mapping) and len(arguments) == 2:
            return arguments[1], "mapping"
        if origin in (list, Sequence) and len(arguments) == 1:
            return arguments[0], "sequence"
    return None


def field_at(path: str) -> FieldReference:
    """Return the schema's declaration of the field a dotted path names.

    The inverse of :func:`nanopnp.io.defaults.value_at`'s walk, taken over the
    *schema* rather than over a document, so that a path can be checked before
    any case is substituted into (FR-24, §5.3.4). Two loud failures rather than
    one: this names a component that does not exist, and
    :meth:`FieldReference.validate` names a value the field would not accept.

    Parameters
    ----------
    path
        Dotted path under the aliases a case file writes, e.g.
        ``"boundary_conditions.bias_V"`` or
        ``"electrolyte.corrections.diffusivity.wall"``.

    Returns
    -------
    FieldReference
        The declared type and how it is reached.

    Raises
    ------
    UnknownCasePathError
        If any component is not a field of the block it is read from, naming the
        prefix that does exist, the component that does not, and what that block
        accepts (QR-12).
    """
    components = [part for part in path.split(".") if part]
    if not components:
        raise UnknownCasePathError("a case-file path cannot be empty")

    owner: type[BaseModel] | None = CaseDocument
    annotation: FieldType = CaseDocument
    container: Literal["model", "mapping", "sequence"] = "model"
    walked: list[str] = []

    for component in components:
        # The container is tried first, because a ``list[SpeciesSpec]`` carries
        # a model *and* is indexed: ``electrolyte.species.0.name`` steps through
        # the list before it reaches the block, and asking the block first would
        # report ``0`` as an unknown field of ``SpeciesSpec``.
        entry = _entry_annotation(annotation)
        if entry is not None and entry[1] == "sequence" and not _is_index(component):
            # A list is reached only by index. Without this the container branch
            # below would swallow ``electrolyte.species.name`` as though ``name``
            # were an index, hand back the *element* type, and leave the path to
            # fail much later inside a substitution (FR-24, QR-12).
            prefix = ".".join(walked) or "<document>"
            raise UnknownCasePathError(
                f"{path!r} is not a field of the case schema: {prefix} is a list, and "
                f"{component!r} is not an index into it"
            )
        if entry is not None:
            annotation, container = entry
        elif owner is not None:
            field = _field_named(owner, component)
            if field is None:
                accepted = ", ".join(_keys_of(owner))
                prefix = ".".join(walked) or "<document>"
                close = difflib.get_close_matches(component, _keys_of(owner), n=1)
                hint = f"did you mean {close[0]!r}? " if close else ""
                raise UnknownCasePathError(
                    f"{path!r} is not a field of the case schema: {prefix} has no "
                    f"{component!r}. {hint}It accepts {accepted}"
                )
            annotation = field.annotation
            container = "model"
        else:
            prefix = ".".join(walked)
            raise UnknownCasePathError(
                f"{path!r} is not a field of the case schema: {prefix} is a "
                f"{_annotation_name(annotation)}, which has no {component!r} inside it"
            )
        walked.append(component)
        owner = _model_of(annotation)

    return FieldReference(path=path, annotation=annotation, container=container)


SEQUENCE_INDEX = "0"
"""The index :func:`case_fields` stands on inside a sequence of blocks.

The walk is over the *schema*, which fixes no length, so a representative index
is the only way to name a field of ``electrolyte.species`` at all. ``0`` is the
one every non-empty document has.
"""


def case_fields() -> tuple[FieldReference, ...]:
    """Return every editable field of ``nanopnp/case/v2``, in declaration order.

    The enumeration a generated editor is built from (IF-09), and the one the
    FR-25 switch classification is checked against. It is deliberately not
    :meth:`~pydantic.BaseModel.model_json_schema`: three things the callers need
    do not survive that projection — the container kinds :class:`FieldReference`
    carries, the ``schema:`` alias, and the fact that ``_check_registries`` asks
    the *installed* registries rather than the document. Walking
    ``model_fields`` gives all three, and gives the dotted paths every other
    component of this package already indexes the case by as a by-product.

    A field is *editable* when it carries a value rather than a block: a leaf,
    a ``list[str]`` or a ``dict[str, float]``, but never ``numerics`` itself.
    Blocks are walked through, including through ``X | None`` and through a
    sequence of blocks — where :data:`SEQUENCE_INDEX` stands for the index, so
    that the path resolves through :func:`field_at` like any other.

    Returns
    -------
    tuple of FieldReference
        Each equal to ``field_at`` of its own path, which
        ``tests/tier1/test_case_fields.py`` asserts element by element: two
        walks over one schema drift, and the one that drifts silently is the one
        no test reads.

    Raises
    ------
    NotImplementedError
        If the schema grows a mapping whose *values* are blocks. ``nanopnp/case/v2``
        has none, and there is no representative key to stand on the way
        :data:`SEQUENCE_INDEX` stands on an index — so the walk says so rather
        than omitting the block's fields, which would make them silently
        uneditable and silently unclassified.
    """
    return tuple(_walk_fields(CaseDocument, ""))


def _walk_fields(owner: type[BaseModel], prefix: str) -> list[FieldReference]:
    """Return the editable fields of ``owner``, depth first, prefixed by ``prefix``."""
    found: list[FieldReference] = []
    for name, field in owner.model_fields.items():
        path = f"{prefix}{field.alias or name}"
        annotation = field.annotation
        entry = _entry_annotation(annotation)
        if entry is not None:
            element, kind = entry
            nested = _model_of(element)
            if nested is None:
                # list[str], dict[str, float]: the container is itself the value
                # a reader writes, and its entries are reached under it.
                found.append(FieldReference(path=path, annotation=annotation))
                continue
            if kind == "mapping":
                raise NotImplementedError(
                    f"{path!r} is a mapping of {nested.__name__} blocks; case_fields() has no "
                    "representative key to walk one under, so a mapping of blocks needs a "
                    "decision here rather than silently missing fields"
                )
            found.extend(_walk_fields(nested, f"{path}.{SEQUENCE_INDEX}."))
            continue
        nested = _model_of(annotation)
        if nested is not None:
            found.extend(_walk_fields(nested, f"{path}."))
            continue
        found.append(FieldReference(path=path, annotation=annotation))
    return found


def schema_default(path: str) -> tuple[bool, FieldValue]:
    """Return whether the schema defaults a field, and the default it declares.

    The generated case-file reference prints this beside each path of
    :func:`case_fields` (VER-45), so that the documented default is the one a
    document omitting the field is validated with, rather than a transcription.

    Parameters
    ----------
    path
        A dotted path as :func:`case_fields` names it; a sequence index stands
        for any element.

    Returns
    -------
    tuple
        ``(False, None)`` for a required field; otherwise ``(True, default)``,
        with a ``default_factory`` called for its value.

    Raises
    ------
    UnknownCasePathError
        If the path does not name a declared field of a block.
    """
    field_at(path)  # the named diagnostic for a path that is wrong
    owner: type[BaseModel] | None = CaseDocument
    info: FieldInfo | None = None
    for component in path.split("."):
        if _is_index(component):
            continue
        if owner is None:
            raise UnknownCasePathError(f"{path!r} does not end at a declared field of a block")
        info = _field_named(owner, component)
        if info is None:
            raise UnknownCasePathError(f"{path!r} does not end at a declared field of a block")
        owner = _model_of(info.annotation)
    if info is None or info.is_required():
        return False, None
    return True, info.get_default(call_default_factory=True)


def _is_index(component: str) -> bool:
    """Return whether a path component reads as a list index."""
    return component.removeprefix("-").isdigit()


def _field_named(owner: type[BaseModel], component: str) -> FieldInfo | None:
    """Return the field a block declares under ``component``, by alias or by name.

    By alias first, because a case file writes ``schema:`` for a field this
    module has to call ``schema_id``.
    """
    for name, field in owner.model_fields.items():
        if (field.alias or name) == component:
            return field
    return None


def field_description(path: str) -> str | None:
    """Return the description a field of the schema declares, or ``None``.

    The generated case-file reference prints it under its section (VER-45), so a
    normative contract written on a field — the section 5.3.1 NOTE on
    ``structure:`` — reaches the documentation without a hand-written copy.
    """
    owner: type[BaseModel] = CaseDocument
    parts = path.split(".")
    for index, part in enumerate(parts):
        if _is_index(part):
            continue
        field = _field_named(owner, part)
        if field is None:
            return None
        if index == len(parts) - 1:
            return field.description
        entry = _entry_annotation(field.annotation)
        nested = _model_of(entry[0] if entry is not None else field.annotation)
        if nested is None:
            return None
        owner = nested
    return None


def value_at(document: CaseDocument, path: str) -> FieldValue:
    """Return the value a dotted path names in a case document.

    Checked against the schema by :func:`field_at` first, so that an unknown
    component is named the same way whether it was asked of the schema or of a
    document. A path that silently resolved to ``None`` would report a switch as
    never deviating, which is the failure :mod:`nanopnp.io.defaults` exists to
    prevent.

    Raises
    ------
    UnknownCasePathError
        If the path is not one the schema declares, or if a block on the way to
        it is absent from *this* document.
    """
    field_at(path)
    value: FieldValue = document
    walked: list[str] = []
    for component in path.split("."):
        walked.append(component)
        if value is None:
            raise UnknownCasePathError(
                f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} is absent from it"
            )
        if isinstance(value, Mapping):
            if component not in value:
                raise UnknownCasePathError(
                    f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} "
                    f"has no entry {component!r}"
                )
            value = value[component]
        elif isinstance(value, list):
            value = _sequence_entry(value, component, path, walked)
        else:
            value = getattr(value, _attribute_named(type(value), component))
    return value


def _attribute_named(owner: type, component: str) -> str:
    """Return the attribute a block's alias names, e.g. ``schema`` to ``schema_id``."""
    fields: Mapping[str, FieldInfo] = getattr(owner, "model_fields", {})
    for name, field in fields.items():
        if (field.alias or name) == component:
            return name
    return component


def _sequence_entry(
    values: list[FieldValue], component: str, path: str, walked: list[str]
) -> FieldValue:
    """Return one element of a list-valued field, by index."""
    try:
        index = int(component)
        return values[index]
    except (ValueError, IndexError):
        raise UnknownCasePathError(
            f"{path!r} cannot be read from this case: {'.'.join(walked[:-1])} holds "
            f"{len(values)} entries, and {component!r} is not an index into them"
        ) from None


def substitute(document: CaseDocument, assignments: Mapping[str, FieldValue]) -> CaseDocument:
    """Return ``document`` with each dotted path set to its assigned value.

    Dump by alias, set into the plain dict, re-validate the **whole document**
    (§5.3.4). Re-validation is what makes a substitution that produces an
    inadmissible case fail with the diagnostic a hand-written case would get, for
    free: a typo hits ``extra="forbid"`` and :func:`render_problems`'s "did you mean"
    message, and a cross-field rule such as the NUM-18 ladder refusal in
    :func:`resolve` still runs. ``model_copy(update=...)`` would accept the typo,
    and rebuilding the object field by field would make a configuration that
    names itself stop being itself.

    Parameters
    ----------
    document
        The base case.
    assignments
        Dotted case-file path to the value to set there. An empty mapping
        returns an equal document, which is the all-origins point of a sweep
        with no axes.

    Returns
    -------
    CaseDocument
        Freshly validated. Never the same object as ``document``.

    Raises
    ------
    UnknownCasePathError
        If a path is not one the schema declares, or if the block it is inside
        is absent from this document.
    CaseValidationError
        If a value is not one the declared type accepts, or if the substituted
        document is not a valid case.
    """
    payload = document.model_dump(by_alias=True, mode="json")
    for path, value in assignments.items():
        reference = field_at(path)
        # Validated against the declared type first, so that the diagnostic
        # names the path rather than pydantic's own location inside a document
        # the caller never wrote. Dumped back to JSON because the payload being
        # written into is a plain dict: a validated ``Path`` set into it would
        # come back out of ``model_dump`` as an object YAML cannot write.
        reference.validate(value)
        _set_at(payload, path, value)
    try:
        return CaseDocument.model_validate(payload)
    except ValidationError as error:
        listed = ", ".join(sorted(assignments)) or "nothing"
        raise CaseValidationError(
            render_problems(f"<{document.name} with {listed} substituted>", error), error
        ) from None


def with_profile(document: CaseDocument, path: str | Path) -> CaseDocument:
    """Return ``document`` rewritten to take its pore profile from ``path`` (WP24 D6).

    How a hand-edited contour enters a run: as a supplied profile, through
    ``inputs.profile``, which stage 5 reads exactly as it reads stage 4's
    (section 5.3.1 NOTE on ``geometry.contour``). Four things change and nothing
    else does:

    - ``structure:`` is removed, because a stage whose output is supplied does
      not run and neither does anything upstream of it;
    - ``geometry.density`` and ``geometry.contour`` are reset to their defaults,
      because stages 2 to 4 read them and do not run;
    - ``inputs.profile`` is set to ``{path, format: profile1}``;
    - the whole document is re-validated.

    :func:`substitute` cannot do this, because it sets values inside blocks the
    document already has and ``inputs.profile`` is absent from a structure case.
    The result is accepted by :func:`resolve`'s ``inputs.profile`` refusals by
    construction, and a command-line user writing it by hand gets the same file.

    Parameters
    ----------
    document
        The case whose profile is replaced: a structure case, or one already
        supplying a profile.
    path
        The profile document. Written verbatim, so a caller wanting the derived
        case to run from any working directory passes an absolute path (WP24 D7);
        case paths resolve against the process's working directory.

    Returns
    -------
    CaseDocument
        Freshly validated.

    Raises
    ------
    CaseValidationError
        If the rewritten document is not a valid case: for instance one that
        also supplies ``inputs.mesh``, which is downstream of the profile.
    """
    payload = document.model_dump(by_alias=True, mode="json")
    payload.pop("structure", None)
    geometry = payload.get("geometry")
    if isinstance(geometry, dict):
        geometry["density"] = DensitySpec().model_dump(mode="json")
        geometry["contour"] = ContourSpec().model_dump(mode="json")
    inputs = payload.setdefault("inputs", {})
    inputs["profile"] = {"path": str(path), "format": PROFILE_FORMAT}
    try:
        return CaseDocument.model_validate(payload)
    except ValidationError as error:
        raise CaseValidationError(
            render_problems(f"<{document.name} with inputs.profile {path}>", error), error
        ) from None


def _set_at(payload: dict[str, FieldValue], path: str, value: FieldValue) -> None:
    """Set ``value`` into a dumped case document at a dotted path.

    Raises
    ------
    UnknownCasePathError
        If a block on the way is absent from this document. The path is known to
        the *schema* by the time this runs -- ``structure.source.path`` is a real
        field -- and a case that declares no ``structure:`` still has nowhere to
        put it, which is a fact about the document and not about the path.
    """
    components = path.split(".")
    cursor: FieldValue = payload
    for depth, component in enumerate(components[:-1]):
        prefix = ".".join(components[: depth + 1])
        if isinstance(cursor, list):
            cursor = _sequence_entry(cursor, component, path, components[: depth + 1])
            continue
        if not isinstance(cursor, dict) or cursor.get(component) is None:
            raise UnknownCasePathError(
                f"{path!r} cannot be set on this case: {prefix} is absent from it, so there "
                "is no block to substitute into; give the base case that section first"
            )
        cursor = cursor[component]
    last = components[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = value
    else:
        cursor[last] = value


# -- reading and writing ------------------------------------------------------


def load_case(path: str | Path) -> CaseDocument:
    """Read and validate a case file.

    The ``schema:`` string is checked first, so a file written to a future schema
    fails naming the schema it claims rather than with a wall of field errors
    against a shape it never declared. A ``nanopnp/case/v1`` file is read as its
    v2 upgrade (:func:`upgrade_v1`).

    Parameters
    ----------
    path
        The YAML case file.

    Returns
    -------
    CaseDocument
        The validated document.

    Raises
    ------
    CaseValidationError
        If the file is not a mapping, declares neither accepted schema, cannot
        be upgraded, or fails validation; the message names every offending key
        by dotted path.
    """
    source = Path(path)
    return _validate(yaml.safe_load(source.read_text(encoding="utf-8")), str(source))


def loads_case(text: str, *, source: str = "<string>") -> CaseDocument:
    """Validate a case document held in memory; see :func:`load_case`."""
    return _validate(yaml.safe_load(text), source)


def _validate(raw: object, source: str) -> CaseDocument:
    """Dispatch on the declared schema, upgrade a v1 mapping, and validate."""
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: a case file is a YAML mapping, found {type(raw).__name__}"
        )
    declared = raw.get("schema")
    if declared == CASE_SCHEMA_V1:
        raw = upgrade_v1(raw, source=source)
    elif declared != SCHEMA:
        raise CaseValidationError(
            f"{source}: expected schema {SCHEMA!r}, or {CASE_SCHEMA_V1!r} (read as its upgrade), "
            f"found {declared!r}"
        )
    try:
        return CaseDocument.model_validate(dict(raw))
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from error


def upgrade_v1(raw: Mapping[str, FieldValue], *, source: str = "<string>") -> dict[str, FieldValue]:
    """Return a ``nanopnp/case/v1`` mapping rewritten as ``nanopnp/case/v2``.

    A pure transform over the parsed YAML, run before validation, so that one
    model serves both schemas (section 5.3.1 v2 NOTE). It moves only what was
    written and adds no default: :data:`V2_RENAMED` keys are renamed, and a
    written :data:`V2_MOVED` permittivity moves into
    ``physics.solid_permittivities``. Validation of the result is the caller's.

    Parameters
    ----------
    raw
        The parsed v1 document. It is not modified.
    source
        Names the document in a diagnostic.

    Returns
    -------
    dict
        The v2 mapping, declaring ``nanopnp/case/v2``.

    Raises
    ------
    CaseValidationError
        If the v1 document carries a key v1 did not have (a document is valid
        against the schema it declares or not at all), or if a moved permittivity
        disagrees with one ``physics.solid_permittivities`` already holds, naming
        both keys and both values.
    """
    document: dict[str, FieldValue] = copy.deepcopy(dict(raw))
    foreign = [
        path
        for path in (*V2_ADDED, *V2_RENAMED.values())
        if _raw_lookup(document, path) is not _ABSENT
    ]
    if foreign:
        raise CaseValidationError(
            f"{source}: declares {CASE_SCHEMA_V1!r} but carries {', '.join(foreign)}, which "
            f"only {CASE_SCHEMA!r} has; declare {CASE_SCHEMA!r}, since a document is valid "
            "against the schema it declares or not at all"
        )
    for old, new in V2_RENAMED.items():
        value = _raw_pop(document, old)
        if value is not _ABSENT:
            _raw_put(document, new, value, source)
    problems: list[str] = []
    for old, new in V2_MOVED.items():
        value = _raw_pop(document, old)
        if value is _ABSENT:
            continue
        held = _raw_lookup(document, new)
        if held is not _ABSENT and held != value:
            problems.append(
                f"{old} is {value!r} but {new} is {held!r}; {CASE_SCHEMA!r} sets a solid's "
                "permittivity in one place, and the two disagree"
            )
            continue
        _raw_put(document, new, value, source)
    if problems:
        raise CaseValidationError(
            f"{source}: cannot upgrade to {CASE_SCHEMA!r}: " + "; ".join(problems)
        )
    document["schema"] = CASE_SCHEMA
    return document


class _Absent:
    """The marker for a key a raw mapping does not carry, where ``None`` is a value."""


_ABSENT = _Absent()


def _raw_lookup(document: Mapping[str, FieldValue], path: str) -> FieldValue:
    """Return the value at a dotted path of a raw mapping, or :data:`_ABSENT`."""
    cursor: FieldValue = document
    for component in path.split("."):
        if not isinstance(cursor, Mapping) or component not in cursor:
            return _ABSENT
        cursor = cursor[component]
    return cursor


def _raw_pop(document: dict[str, FieldValue], path: str) -> FieldValue:
    """Remove and return the value at a dotted path of a raw mapping, or :data:`_ABSENT`."""
    *head, last = path.split(".")
    parent = _raw_lookup(document, ".".join(head)) if head else document
    if not isinstance(parent, dict) or last not in parent:
        return _ABSENT
    return parent.pop(last)


def _raw_put(document: dict[str, FieldValue], path: str, value: FieldValue, source: str) -> None:
    """Set a value at a dotted path of a raw mapping, creating absent blocks.

    Only a block the document does not carry is created. One written as
    ``null`` is present, and v1 refused it, so it is not turned into a block
    that would make the upgrade accept a document v1 did not.

    Raises
    ------
    CaseValidationError
        If a block on the way is present and is not a mapping, so the value has
        nowhere to go; dropping it would lose a written parameter.
    """
    *head, last = path.split(".")
    cursor = document
    for depth, component in enumerate(head):
        if component not in cursor:
            cursor[component] = {}
        nested = cursor[component]
        if not isinstance(nested, dict):
            prefix = ".".join(head[: depth + 1])
            raise CaseValidationError(
                f"{source}: cannot upgrade to {CASE_SCHEMA!r}: {path} is where the value goes, "
                f"and {prefix} is a {type(nested).__name__}, not a block"
            )
        cursor = nested
    cursor[last] = value


def dump_case(document: CaseDocument, path: str | Path) -> Path:
    """Write a validated case document back to YAML.

    The text is not the round-trip invariant — comments, key order and ``1``
    against ``1.0`` are all lost here, and none of them changes the run. FR-26 and
    VER-09 are asserted on the content hash of the validated document and on
    :attr:`ResolvedCase.provenance` instead (section 5.3.1 NOTE).

    Returns
    -------
    Path
        The file written.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps_case(document), encoding="utf-8")
    return target


def dumps_case(document: CaseDocument) -> str:
    """Return a validated case document as the YAML text a case file holds.

    The half of :func:`dump_case` that does not touch the filesystem, because a
    case assembled in memory still has to reach the FR-25 manifest as text: the
    manifest embeds the case beside its hash and writes it back out as the run
    directory's ``case.yaml``, which is what QR-08's reproduction re-runs from
    (§5.3.3). A sweep member is exactly such a case (§5.3.4).

    Returns
    -------
    str
        YAML under the aliases a case file writes, in declaration order.
    """
    return str(yaml.safe_dump(document.model_dump(by_alias=True, mode="json"), sort_keys=False))


# -- resolution ---------------------------------------------------------------

_ORDERS: dict[str, int] = {"P1": 1, "P2": 2, "P3": 3}
"""Element labels of section 5.3.1 against their polynomial order."""

PQR_FORMAT = "pqr"
"""``inputs.pqr.format``: a PQR of one frame or one ``MODEL`` per frame (section 5.3.1 NOTE)."""

_UNREAD_CHARGE_KEYS: dict[str, str] = {}
"""``charge:`` keys a later package's stage reads, with that stage.

Each is refused set away from its default, naming the stage, until the package
that delivers the stage removes its entry (section 5.3.1 NOTE on the protonation
keys). ``charge:`` itself left the table of unrun sections in WP27, when the
``protonation`` stage made ``ph``, ``forcefield`` and ``titration`` runnable, and
``smearing`` left it in WP28, when stage 7's deposition came to read it. Empty
since WP30, whose stages 5 and 7 read ``exclusion_offset_nm`` and
``dielectric_transition_nm``; kept, because the rule outlives the last key that
needed it.
"""

PROFILE_KEYS: tuple[str, ...] = ("exclusion_offset_nm", "dielectric_transition_nm")
"""The ``charge:`` keys built from the stage-4 profile (WP30 D12)."""

SMEARING_KEYS: tuple[str, ...] = ("sharpness", "grid_spacing_nm")
"""The ``charge.smearing`` keys stage 7's deposition reads (PHY-16 steps 4-6, WP28 D10)."""

PROTONATION_KEYS: tuple[str, ...] = ("ph", "forcefield", "titration")
"""The ``charge:`` keys the ``protonation`` stage reads (PHY-16 step 3, WP27 D13)."""

PROFILE_FORMAT = "profile1"
"""``inputs.profile.format``: a ``nanopnp/profile/v1`` document (section 5.3.1 NOTE)."""

GRID_SPACING_RANGE_NM: tuple[float, float] = (0.025, 0.05)
"""FR-04's density grid spacing, 0.25-0.5 Å (section 5.3.1 NOTE on ``geometry.density``)."""

_POINT_GROUP = re.compile(r"C([1-9][0-9]*)")
"""``symmetry.point_group``: a cyclic group ``C<n>``, n >= 1 (section 5.3.1 NOTE)."""

_UNCONSUMED_INPUTS: dict[str, str] = {}
"""``inputs:`` keys ``nanopnp/case/v2`` accepts ahead of the stage that reads them.

Each is refused naming that stage until the stage is delivered, and the package
that delivers it removes its entry (section 5.3.1 NOTE on ``inputs:``). Empty
since WP27, whose ``protonation`` stage reads ``inputs.pqr``; kept, because the
rule outlives the last key that needed it.
"""


def _order(label: str, field: str) -> int:
    """Return the polynomial order a ``P<n>`` element label names."""
    try:
        return _ORDERS[label]
    except KeyError:
        raise CaseValidationError(
            f"numerics.elements.{field} {label!r} is not an element label; "
            f"the labels are {', '.join(sorted(_ORDERS))}"
        ) from None


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
        return (self.density if self.density is not None else DensitySpec()).grid_spacing_nm

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
        return self.protonates and "fixed_charge" in declaration(self.model).coefficients

    @property
    def name(self) -> str:
        """The case name, which names the run directory in the store."""
        return self.document.name

    def physics_model(self) -> PhysicsModel:
        """Build the named model at this case's operating point (WP26 D6).

        Every consumer that needs the built model -- the single rung, the mesh
        gate, a restore -- builds it here, so none of them can pass the builder a
        different set of keywords.
        """
        return build_model(self.model, self.electrolyte, self.concentration_M, self.model_options)

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


def _switches(document: CaseDocument) -> CorrectionSwitches:
    """Return the PHY-22 switch set the document's ``corrections`` block names."""
    corrections = document.electrolyte.corrections
    return CorrectionSwitches(
        diffusivity=corrections.diffusivity.to_choice(),
        mobility=corrections.mobility.to_choice(),
        viscosity=corrections.viscosity.to_choice(),
        permittivity=corrections.permittivity.to_choice(),
        density=corrections.density.to_choice(),
        steric=corrections.steric.model != "none",
    )


def parse_chains(chains: str) -> tuple[str, ...] | None:
    """Return the identifiers ``structure.source.chains`` lists, or ``None`` for ``all``.

    The key is ``all`` or a comma-separated list of chain identifiers (section
    5.3.1 NOTE on ``structure:``). Whitespace around an identifier is dropped.
    """
    if chains.strip() == "all":
        return None
    return tuple(part.strip() for part in chains.split(","))


def _resolve_structure(document: CaseDocument) -> ResolvedStructure | None:
    """Make the ``structure:`` refusals that need no file (section 5.3.1 NOTE, WP18 D4).

    Each is a refusal here rather than a narrowing of the schema: a narrowed value
    set would move the schema (the section 5.3.1 compatibility rule), and a
    document valid against ``nanopnp/case/v2`` stays valid.

    Raises
    ------
    CaseValidationError
        Naming the key: a point group that is not ``C<n>``, ``axis: auto`` on
        ``C1``, a chain list that is empty, repeats an identifier or does not
        number ``n``, and a non-positive ``last_ns`` or ``count``.
    """
    spec = document.structure
    if spec is None:
        return None
    group = spec.symmetry.point_group.strip()
    match = _POINT_GROUP.fullmatch(group)
    if match is None:
        raise CaseValidationError(
            f"structure.symmetry.point_group {group!r} is not a cyclic point group; the accepted "
            "form is C<n> with n >= 1, such as C12 for ClyA, C7 for alpha-hemolysin or C8 for "
            "MspA (section 5.3.1 NOTE on structure:)"
        )
    n = int(match.group(1))
    if n == 1 and spec.symmetry.axis == "auto":
        raise CaseValidationError(
            "structure.symmetry.axis is auto and the point group is C1, which has no chain "
            "permutation to superpose (FR-02); set structure.symmetry.axis: z, which takes the "
            "file's z axis through its origin, unchecked"
        )
    chains = parse_chains(spec.source.chains)
    if chains is not None:
        if any(not chain for chain in chains):
            raise CaseValidationError(
                f"structure.source.chains {spec.source.chains!r} has an empty entry; it is `all` "
                "or a comma-separated list of chain identifiers"
            )
        repeated = sorted({chain for chain in chains if chains.count(chain) > 1})
        if repeated:
            raise CaseValidationError(
                f"structure.source.chains lists {', '.join(repeated)} more than once"
            )
        if len(chains) != n:
            raise CaseValidationError(
                f"structure.source.chains lists {len(chains)} chains ({', '.join(chains)}), and "
                f"structure.symmetry.point_group {group} has {n} (FR-03)"
            )
    frames = spec.ensemble.frames
    if frames.last_ns is not None and not frames.last_ns > 0.0:
        raise CaseValidationError(
            f"structure.ensemble.frames.last_ns is {frames.last_ns}; it is a positive time in ns"
        )
    if frames.count is not None and frames.count < 1:
        raise CaseValidationError(
            f"structure.ensemble.frames.count is {frames.count}; it is at least 1"
        )
    return ResolvedStructure(spec=spec, n=n, chains=chains)


def _resolve_density(document: CaseDocument) -> DensitySpec | None:
    """Make the ``geometry.density`` refusals (section 5.3.1 NOTE, WP19 D2).

    Value checks, not a narrowing of the schema, for the reason
    :func:`_resolve_structure` gives.

    Returns
    -------
    DensitySpec or None
        The block, or its defaults where the case has no ``geometry:``; ``None``
        on a case without ``structure:``, which runs no stage that reads it.

    Raises
    ------
    CaseValidationError
        Naming the key and its value: a grid spacing outside FR-04's
        0.025-0.05 nm, or a sharpness that is not positive.
    """
    if document.structure is None:
        return None
    spec = document.geometry.density if document.geometry is not None else DensitySpec()
    low, high = GRID_SPACING_RANGE_NM
    if not low <= spec.grid_spacing_nm <= high:
        raise CaseValidationError(
            f"geometry.density.grid_spacing_nm is {spec.grid_spacing_nm} nm; FR-04 requires "
            f"{low}-{high} nm (0.25-0.5 A), because the trans constriction's contour moves with "
            "resolution (section 5.3.1 NOTE on geometry.density)"
        )
    if not 0.0 < spec.sharpness < math.inf:
        raise CaseValidationError(
            f"geometry.density.sharpness is {spec.sharpness}; it scales each atom's radius to "
            "its Gaussian width, so it is a positive number (section 5.3.1 NOTE on "
            "geometry.density)"
        )
    return spec


def _resolve_contour(document: CaseDocument, density: DensitySpec | None) -> ContourSpec | None:
    """Make the ``geometry.contour`` refusals (section 5.3.1 NOTE, WP20 D3).

    Value checks, not a narrowing of the schema, for the reason
    :func:`_resolve_structure` gives.

    Returns
    -------
    ContourSpec or None
        The block, or its defaults where the case has no ``geometry:``; ``None``
        on a case without ``structure:``.

    Raises
    ------
    CaseValidationError
        Naming the key and its value: an isolevel that is not finite or not in
        (0, 1), or a tolerance that is not finite or not in (0, h), which also
        names h.
    """
    if document.structure is None or density is None:
        return None
    spec = document.geometry.contour if document.geometry is not None else ContourSpec()
    if not (math.isfinite(spec.isolevel) and 0.0 < spec.isolevel < 1.0):
        raise CaseValidationError(
            f"geometry.contour.isolevel is {spec.isolevel}; it is a level of a density in "
            "[0, 1], so it lies in (0, 1) (section 5.3.1 NOTE on geometry.contour)"
        )
    h = density.grid_spacing_nm
    if not (math.isfinite(spec.simplify_tol_nm) and 0.0 < spec.simplify_tol_nm < h):
        raise CaseValidationError(
            f"geometry.contour.simplify_tol_nm is {spec.simplify_tol_nm} nm; it must be positive "
            f"and below the density grid spacing h = {h} nm, because a larger tolerance "
            "discards resolved geometry and breaks the feature-size margin of the closing of "
            "radius 2h (section 5.3.1 NOTE on geometry.contour, section 5.2.1)"
        )
    return spec


def _check_species(document: CaseDocument, electrolyte: Electrolyte) -> None:
    """Check the case's species, steric diameters and temperature against the parameter file.

    The diameters are *checked*, never applied: they are fitted parameters of the
    correction file (FR-16), and a case file that could override them silently
    would be a second source of truth for a physical constant. So is the
    temperature: every reference property, every scale and ``V_T`` come from the
    file, and the fits are temperature-specific, so a case at another temperature
    would be solved at the file's while its manifest recorded the case's.
    """
    problems: list[str] = []
    temperature_K = document.electrolyte.temperature_K
    if temperature_K != electrolyte.temperature_K:
        problems.append(
            f"electrolyte.temperature_K is {temperature_K} K, but "
            f"{document.electrolyte.parameters!r} is fitted at {electrolyte.temperature_K} K and "
            "the solve takes every material property and V_T from the file; set temperature_K: "
            f"{electrolyte.temperature_K} or supply a parameter file fitted at the temperature "
            "you want"
        )
    for index, species in enumerate(document.electrolyte.species):
        valence = electrolyte.ion(species.name).valence
        if valence != species.z:
            problems.append(
                f"electrolyte.species[{index}].z is {species.z:+d} for {species.name!r}, but "
                f"{document.electrolyte.parameters!r} gives {valence:+d}"
            )
    steric = document.electrolyte.corrections.steric
    if steric.a_ion_nm is not None:
        for index, ion in enumerate(electrolyte.species):
            given_m = steric.a_ion_nm * 1e-9
            if abs(ion.steric_diameter - given_m) > 1e-15:
                problems.append(
                    f"electrolyte.corrections.steric.a_ion_nm is {steric.a_ion_nm} nm, but "
                    f"{document.electrolyte.parameters!r} gives "
                    f"{ion.steric_diameter * 1e9} nm for {ion.name!r} "
                    f"(species[{index}]); the diameters are fitted parameters of the correction "
                    "file and the case file cannot override them (FR-16)"
                )
    if steric.a_water_nm is not None:
        given_m = steric.a_water_nm * 1e-9
        if abs(electrolyte.water_steric_diameter - given_m) > 1e-15:
            problems.append(
                f"electrolyte.corrections.steric.a_water_nm is {steric.a_water_nm} nm, but "
                f"{document.electrolyte.parameters!r} gives "
                f"{electrolyte.water_steric_diameter * 1e9} nm"
            )
    if problems:
        raise CaseValidationError("; ".join(problems))


def _require_runnable(document: CaseDocument) -> SuppliedArtefact | None:
    """Reject every section this release does not run, and return the supplied mesh.

    Returns
    -------
    SuppliedArtefact or None
        ``inputs.mesh``. A case carrying ``structure:`` or supplying
        ``inputs.profile`` may omit it, and stages 5 and 6 build the mesh. Any
        other case without one describes no run at all.
    """
    _check_charge(document)
    for supplied, consumer in _UNCONSUMED_INPUTS.items():
        if getattr(document.inputs, supplied) is not None:
            raise UnsupportedCaseSection(
                f"case {document.name!r} supplies inputs.{supplied}; {consumer} is not delivered "
                "in this release, so nothing would read it (section 5.3.1 NOTE on inputs:)"
            )
    for supplied, what in (
        ("charge", "a fixed-charge field"),
        ("eps_r", "a dielectric field"),
    ):
        field: SuppliedArtefact | None = getattr(document.inputs, supplied)
        if field is None:
            continue
        if field.path is None:
            raise UnsupportedCaseSection(
                f"inputs.{supplied}: artefact: names {what} in the store, which the charge "
                f"pipeline of v0.4 fills; supply inputs.{supplied}: path: instead"
            )
        if field.groups:
            raise CaseValidationError(
                f"inputs.{supplied}.groups is the mesh's vocabulary mapping (IF-06) and means "
                f"nothing for {what}; a field is named by its header document, which carries the "
                "quantity and the units (section 5.3.1 NOTE)"
            )
        if field.format not in (None, FIELD_FORMAT):
            raise CaseValidationError(
                f"inputs.{supplied}.format is {field.format!r}; a supplied field is named by a "
                f"header document, so the format is {FIELD_FORMAT!r} and the *data* format is read "
                "from the document's data.format key (section 5.3.1 NOTE)"
            )
    if document.structure is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a structure: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run, and neither does anything upstream of "
            "it, so the structure would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on inputs:); remove one of them"
        )
    if document.geometry is not None and document.inputs.mesh is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a geometry: section and supplies inputs.mesh. A "
            "stage whose output is supplied does not run, and neither does anything upstream of "
            "it, so the geometry would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on geometry.density); remove one of them"
        )
    _check_profile(document)
    if (
        document.inputs.mesh is None
        and document.structure is None
        and document.inputs.profile is None
    ):
        raise CaseValidationError(
            f"case {document.name!r} names no geometry: it supplies neither inputs.mesh nor "
            "inputs.profile and carries no structure: section, so there is nothing to mesh and "
            "no mesh to solve on (section 5.3.1 NOTE on inputs:)"
        )
    if document.inputs.mesh is None:
        _check_generation(document)
    mesh = document.inputs.mesh
    nonlinear = document.numerics.nonlinear
    if nonlinear.strategy != "newton":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.strategy {nonlinear.strategy!r} is the NUM-20 fallback ladder, "
            "which is v0.2; this release solves every rung with the monolithic damped Newton of "
            "NUM-16"
        )
    if nonlinear.damping != "residual":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.damping {nonlinear.damping!r} is v0.2; this release uses the "
            "residual-monotonicity damping of NUM-16, whose recovery rule the reference records"
        )
    walls = document.boundary_conditions.walls
    if walls.slip != "no_slip" or walls.ion_flux != "no_flux":
        # Nothing downstream reads the wall values: the forms pose no-slip and
        # no-flux unconditionally, so any other value would be recorded in the
        # manifest without being applied (section 5.3.1 NOTE on walls).
        raise UnsupportedCaseSection(
            f"boundary_conditions.walls asks for slip: {walls.slip} and ion_flux: "
            f"{walls.ion_flux}; this release applies slip: no_slip and ion_flux: no_flux only, "
            "and no release of SPECIFICATION.md section 3 schedules the others yet"
        )
    # Read from the model's declaration, never from its name (section 5.4.3
    # NOTE): the switch check first, because a case the model cannot pose is a
    # more precise diagnostic than one about how to continue it.
    _check_physics_switches(document)
    _check_strategy(document)
    if document.numerics.continuation == LADDER_STRATEGY:
        _check_ladder_can_honour(document.physics)
    _check_outputs(document)
    return mesh


def _resolve_protonation(document: CaseDocument) -> ResolvedProtonation:
    """Return the ``protonation`` stage's settings, at their defaults without ``charge:``."""
    charge = document.charge if document.charge is not None else Charge()
    return ResolvedProtonation(
        ph=charge.ph, forcefield=charge.forcefield, titration=charge.titration
    )


def _check_charge(document: CaseDocument) -> None:
    """Make the ``charge:`` and ``inputs.pqr`` refusals (section 5.3.1 NOTEs, WP27 D13).

    Raises
    ------
    UnsupportedCaseSection
        Naming the stage, for a ``charge:`` key a later package's stage reads
        (:data:`_UNREAD_CHARGE_KEYS`, empty since WP30).
    CaseValidationError
        Naming the keys: the refusals of :func:`_check_profile_keys`;
        ``artefact:``, ``groups`` or a format other than ``pqr`` on
        ``inputs.pqr``; the ``charge.smearing`` refusals of
        :func:`_check_smearing`; ``charge.ph`` away from its default beside
        ``titration: none``; and a protonation key away from its default where
        the ``protonation`` stage does not run, which is beside ``inputs.pqr``,
        beside ``inputs.charge``, and in a case with neither ``structure:`` nor
        ``inputs.pqr``.
    """
    pqr = document.inputs.pqr
    if pqr is not None:
        if pqr.path is None:
            raise CaseValidationError(
                "inputs.pqr: artefact: names a protonation artefact in the store; the stage's "
                "own artefact is reached through a structure: section, and a supplied PQR is "
                "named by inputs.pqr: path: (section 5.3.1 NOTE on inputs:)"
            )
        if pqr.groups:
            raise CaseValidationError(
                "inputs.pqr.groups is the mesh's vocabulary mapping (IF-06) and means nothing "
                "for a PQR file (section 5.3.1 NOTE on inputs:)"
            )
        if pqr.format not in (None, PQR_FORMAT):
            raise CaseValidationError(
                f"inputs.pqr.format is {pqr.format!r}; a supplied PQR file of one frame or one "
                f"MODEL per frame has format {PQR_FORMAT!r} (section 5.3.1 NOTE on inputs:)"
            )
    charge = document.charge
    if charge is None:
        return
    defaults = Charge()
    for key, stage in _UNREAD_CHARGE_KEYS.items():
        if getattr(charge, key) != getattr(defaults, key):
            raise UnsupportedCaseSection(
                f"charge.{key} is set away from its default; {stage} reads it and is not "
                "delivered in this release, so it would change nothing (section 5.3.1 NOTE on "
                "the protonation keys)"
            )
    _check_profile_keys(document, charge)
    _check_smearing(document, charge.smearing, defaults.smearing)
    if charge.titration == "none" and charge.ph != defaults.ph:
        raise CaseValidationError(
            f"charge.ph is {charge.ph} beside charge.titration: none, which runs PDB2PQR "
            "without a titration method, so the pH reaches no calculation; remove charge.ph or "
            "set charge.titration: propka (section 5.3.1 NOTE on the protonation keys)"
        )
    changed = [
        f"charge.{key}"
        for key in PROTONATION_KEYS
        if getattr(charge, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    where = (
        "beside inputs.pqr, which supplies the charges and radii PDB2PQR would compute"
        if pqr is not None
        else "beside inputs.charge, which supplies the field stage 7 would make of them"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr, so there is nothing "
        "to protonate"
        if document.structure is None
        else None
    )
    if where is not None:
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where}; the "
            "protonation stage they configure does not run, so they would change nothing "
            "(section 5.3.1 NOTE on the protonation keys)"
        )


def _check_profile_keys(document: CaseDocument, charge: Charge) -> None:
    """Make the refusals of the two keys built from the stage-4 profile (WP30 D11, D12).

    Raises
    ------
    CaseValidationError
        Naming both keys: either set away from ``0`` beside ``inputs.mesh``, or in
        a case with neither ``structure:`` nor ``inputs.profile``, where there is
        no profile to build it from (a knob with no effect); a non-zero
        ``dielectric_transition_nm`` beside ``inputs.eps_r``, which supplies the
        same quantity; ``0 < dielectric_transition_nm < h_c`` and
        ``0 < exclusion_offset_nm <= 2 h_c``, with ``h_c`` the density grid
        spacing (section 4.4 NOTE on the derived solid fraction; section 5.2.1
        NOTE on the ion-exclusion shell).
    """
    changed = [f"charge.{key}" for key in PROFILE_KEYS if getattr(charge, key) != 0.0]
    if not changed:
        return
    named = f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set away from 0"
    if document.inputs.mesh is not None:
        raise CaseValidationError(
            f"{named} beside inputs.mesh; both are built from the stage-4 profile, and a "
            "supplied mesh has none, so they would change nothing (section 5.3.1 NOTE on the "
            "v2 keys that change a number)"
        )
    if document.structure is None and document.inputs.profile is None:
        raise CaseValidationError(
            f"{named} in a case with neither a structure: section nor inputs.profile; both are "
            "built from the stage-4 profile, and there is none (section 5.3.1 NOTE on the v2 keys "
            "that change a number)"
        )
    if charge.dielectric_transition_nm > 0.0 and document.inputs.eps_r is not None:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {charge.dielectric_transition_nm} nm beside "
            "inputs.eps_r; both supply the solid fraction chi, so the case names one quantity "
            "twice; remove one of them (section 5.3.1 NOTE on the v2 keys that change a number)"
        )
    density = (
        document.geometry.density
        if document.geometry is not None and document.structure is not None
        else DensitySpec()
    )
    h_c = density.grid_spacing_nm
    delta = charge.dielectric_transition_nm
    if 0.0 < delta < h_c:
        raise CaseValidationError(
            f"charge.dielectric_transition_nm is {delta} nm, below "
            f"geometry.density.grid_spacing_nm = {h_c} nm: the transition would be finer than "
            "the grid the contour it is built on is placed on (section 4.4 NOTE on the derived "
            "solid fraction)"
        )
    offset = charge.exclusion_offset_nm
    if 0.0 < offset <= 2.0 * h_c:
        raise CaseValidationError(
            f"charge.exclusion_offset_nm is {offset} nm, at most twice "
            f"geometry.density.grid_spacing_nm = {h_c} nm: the shell is a face of width a, and "
            f"section 5.2.1's feature-size criterion admits nothing narrower than 2 h_c = "
            f"{2.0 * h_c:g} nm (section 5.2.1 NOTE on the ion-exclusion shell)"
        )


def _check_smearing(document: CaseDocument, smearing: SmearingSpec, defaults: SmearingSpec) -> None:
    """Make the ``charge.smearing`` refusals (section 5.3.1 NOTE on ``charge.smearing``, WP28 D10).

    Raises
    ------
    CaseValidationError
        Naming the key: ``axis_cutoff_nm`` away from its default, on every path
        (PHY-18); a ``sharpness`` or ``grid_spacing_nm`` that is not finite and
        positive; and either set away from its default beside ``inputs.charge``,
        or in a case with neither ``structure:`` nor ``inputs.pqr``, where the
        deposition they configure does not run, naming both keys.
    """
    if smearing.axis_cutoff_nm != defaults.axis_cutoff_nm:
        raise CaseValidationError(
            f"charge.smearing.axis_cutoff_nm is {smearing.axis_cutoff_nm}; it is refused away "
            f"from its default {defaults.axis_cutoff_nm} on every path (PHY-18). The deposited "
            "kernel is regular on the axis and takes no guard, and a supplied field declares its "
            "own axis_cutoff_nm in its header document, so the key would change nothing "
            "(section 5.3.1 NOTE on charge.smearing)"
        )
    for key in SMEARING_KEYS:
        value = getattr(smearing, key)
        if not 0.0 < value < math.inf:
            raise CaseValidationError(
                f"charge.smearing.{key} is {value}; it must be finite and positive (PHY-16 "
                "steps 4-6)"
            )
    changed = [
        f"charge.smearing.{key}"
        for key in SMEARING_KEYS
        if getattr(smearing, key) != getattr(defaults, key)
    ]
    if not changed:
        return
    where = (
        "beside inputs.charge, which supplies the field stage 7 would otherwise deposit"
        if document.inputs.charge is not None
        else "in a case with neither a structure: section nor inputs.pqr, so there is nothing "
        "to deposit"
        if document.structure is None and document.inputs.pqr is None
        else None
    )
    if where is not None:
        other = "inputs.charge" if document.inputs.charge is not None else "structure:"
        raise CaseValidationError(
            f"{', '.join(changed)} {'is' if len(changed) == 1 else 'are'} set {where} "
            f"({other}); the deposition stage 7 would configure with "
            f"{'it' if len(changed) == 1 else 'them'} does not run, so "
            f"{'it' if len(changed) == 1 else 'they'} would change nothing (section 5.3.1 NOTE "
            "on charge.smearing)"
        )


def _check_profile(document: CaseDocument) -> None:
    """Make the ``inputs.profile`` refusals (section 5.3.1 NOTE on ``inputs:``, WP21 D14).

    Raises
    ------
    CaseValidationError
        Naming the key: ``artefact:``, ``groups`` or a format other than
        ``profile1`` on ``inputs.profile``; ``structure:`` beside it; and
        ``geometry.density`` or ``geometry.contour`` set away from their defaults
        beside it, which stages 2 to 4 would read and which do not run.
    """
    profile = document.inputs.profile
    if profile is None:
        return
    if profile.path is None:
        raise CaseValidationError(
            "inputs.profile: artefact: names a profile in the store; stage 4's artefact is "
            "reached through a structure: section, and a supplied profile is named by "
            "inputs.profile: path: (section 5.3.1 NOTE on inputs:)"
        )
    if profile.groups:
        raise CaseValidationError(
            "inputs.profile.groups is the mesh's vocabulary mapping (IF-06) and means nothing "
            "for a profile, whose one boundary stage 5 names itself (section 5.3.1 NOTE on "
            "inputs:)"
        )
    if profile.format not in (None, PROFILE_FORMAT):
        raise CaseValidationError(
            f"inputs.profile.format is {profile.format!r}; a supplied profile is a "
            f"nanopnp/profile/v1 document, format {PROFILE_FORMAT!r} (section 5.3.1 NOTE on "
            "inputs:)"
        )
    if document.structure is not None:
        raise CaseValidationError(
            f"case {document.name!r} carries a structure: section and supplies inputs.profile. "
            "A stage whose output is supplied does not run, and neither does anything upstream "
            "of it, so the structure would be recorded as an input to a run that never read it "
            "(section 5.3.1 NOTE on inputs:); remove one of them"
        )
    geometry = document.geometry
    if geometry is None:
        return
    for key, default in (("density", DensitySpec()), ("contour", ContourSpec())):
        if getattr(geometry, key) != default:
            raise CaseValidationError(
                f"geometry.{key} is set beside inputs.profile. Stages 2 to 4 read it and a "
                "supplied profile means they do not run, so it would change nothing; remove it "
                "(section 5.3.1 NOTE on inputs:)"
            )


def _check_generation(document: CaseDocument) -> None:
    """Make the refusals of a case whose mesh stages 5 and 6 build (WP21 D14).

    Raises
    ------
    UnsupportedCaseSection
        Naming the key and its value: ``boundary_layer: true`` (FR-11,
        post-1.0) and ``geometry.analyte`` (FR-21, v1.0). ``backend: gmsh`` is
        not refused here: it resolves on any install, and stage 6 refuses it
        naming the extra when ``gmsh`` does not import (WP23 D9).
    CaseValidationError
        Naming the key and its value: a membrane thickness, a reservoir radius
        or an explicit ``wall_h_nm`` that is not finite and positive.
    """
    mesh = document.numerics.mesh
    if mesh.boundary_layer:
        raise UnsupportedCaseSection(
            "numerics.mesh.boundary_layer is true; boundary-layer meshing is FR-11, after v1.0. "
            "The reference mesh used none, only isotropic grading to the wall (section 5.2.2)"
        )
    geometry = document.geometry
    if geometry is not None and geometry.analyte is not None:
        raise UnsupportedCaseSection(
            f"geometry.analyte is a {geometry.analyte.shape}; an analyte in a generated region "
            "is FR-21, v1.0. The benchmark geometries embed one (PHY-11)"
        )
    membrane = geometry.membrane if geometry is not None else MembraneSpec()
    reservoir = geometry.reservoir if geometry is not None else ReservoirSpec()
    for key, value in (
        ("geometry.membrane.thickness_nm", membrane.thickness_nm),
        ("geometry.reservoir.radius_nm", reservoir.radius_nm),
    ):
        if not (math.isfinite(value) and value > 0.0):
            raise CaseValidationError(
                f"{key} is {value}; it is a length, finite and positive (section 5.3.1 NOTE on "
                "numerics.mesh)"
            )
    if not math.isfinite(membrane.centre_z_nm):
        raise CaseValidationError(
            f"geometry.membrane.centre_z_nm is {membrane.centre_z_nm}; it is a finite position "
            "along the axis in the structure's frame"
        )
    if mesh.wall_h_nm != "auto" and not (math.isfinite(mesh.wall_h_nm) and mesh.wall_h_nm > 0.0):
        raise CaseValidationError(
            f"numerics.mesh.wall_h_nm is {mesh.wall_h_nm}; it is `auto` or an element size in "
            "nm, finite and positive (section 5.3.1 NOTE on numerics.mesh)"
        )


_LADDER_PHYSICS: dict[str, bool] = {
    "flow": True,
    "variable_density": True,
    "inertia": True,
    "dielectric_gradient_forces": False,
}
"""The physics configuration the NUM-18 ladder arrives at, whatever the case says.

``nanopnp.solve.continuation.default_ladder`` builds its rungs itself and reads
none of these four from the case: its ``_coupled`` helper passes ``flow``
explicitly -- off for the early electrostatic and equilibrium-PNP rungs, on from
the stage-6 rung upwards, which is the ladder's own path rather than a switch --
and leaves ``variable_density``, ``inertia`` and ``dielectric_gradient_forces``
at the :class:`~nanopnp.physics.models.CoupledModel` defaults recorded above.
Only ``numerics.continuation: none`` threads the case's four through to the
model builder (:func:`_model_options`). The values here are therefore what the
*top* rung carries, which is the rung the result and its manifest come from."""


def _check_ladder_can_honour(physics: PhysicsSpec) -> None:
    """Refuse a physics switch the NUM-18 ladder cannot honour.

    NUM-18 fixes the path: flow is enabled at stage 6 and the corrections at
    stage 7, so "flow off" is not a rung of the ladder but a different run, and
    the opt-in dielectric-gradient forces of PHY-23 are not on the ladder at
    all. ``default_ladder`` accordingly reads none of the four from the case, so
    a case that set one of them and still selected the ladder would converge
    with the FR-25 manifest recording a deviation the solve never carried --
    exactly the silent drop :func:`_check_physics_switches` exists to prevent,
    one rung later and for a different reason.

    A model whose own switches cannot match the ladder -- ``pnp``, which honours
    ``flow: false`` only -- never reaches this check: it does not admit the ladder
    as a strategy, and :func:`_check_strategy` has already said so.
    """
    mismatched = [
        name for name, fixed in _LADDER_PHYSICS.items() if getattr(physics, name) != fixed
    ]
    if not mismatched:
        return
    named = ", ".join(f"physics.{name}" for name in mismatched)
    raise CaseValidationError(
        f"{named} would be silently ignored by the NUM-18 ladder, which fixes the path rather "
        "than reading these from the case (flow on from stage 6, variable_density and inertia "
        "on, dielectric_gradient_forces off); set numerics.continuation: none to run a single "
        "rung with the switches as given, or set them to match the ladder"
    )


def _admitting(predicate: Callable[[str], bool]) -> str:
    """Return the registered models a predicate on their declaration admits, as prose."""
    names = [name for name in registered_models() if predicate(name)]
    return ", ".join(names) or "no registered model"


def _honouring(switch: str, value: bool) -> str:
    """Return the registered models honouring one switch value, as prose."""
    return _admitting(lambda other: value in declaration(other).switches[switch])


def _accepting(coefficient: str) -> str:
    """Return the registered models accepting one supplied coefficient, as prose."""
    return _admitting(lambda other: coefficient in declaration(other).coefficients)


def _check_physics_switches(document: CaseDocument) -> None:
    """Refuse a case whose physics the named model cannot honour (PHY-21, section 5.4.3).

    Read from the model's declaration, never from its name. A switch the solver
    silently drops is worse than one it refuses: the FR-25 manifest would record
    ``flow: true`` beside a solution that has no velocity field in it, and a
    reader would have no way to tell. The same holds for ``physics.
    solid_permittivities`` beside a model that carries no solids, and for the two
    supplied fields of stage 7 beside a model that does not accept them -- the
    same failure arriving as an input: stage 7 would gate the field, the manifest
    would record it, and the solve would never read it.

    Raises
    ------
    CaseValidationError
        Naming the model, the key and the values or models that are admitted.
    """
    physics = document.physics
    model = physics.model
    declared = declaration(model)
    for name in SWITCHES:
        value = getattr(physics, name)
        honoured = declared.switches[name]
        if value not in honoured:
            admitted = " or ".join(str(choice).lower() for choice in honoured)
            raise CaseValidationError(
                f"physics.model {model!r} honours physics.{name}: {admitted} only (PHY-21), so "
                f"physics.{name} must be {admitted}; {str(value).lower()} would be recorded in "
                f"the manifest and never applied. Models honouring {str(value).lower()}: "
                f"{_honouring(name, value)}"
            )
    transition = (document.charge or Charge()).dielectric_transition_nm
    if transition > 0.0 and "solid_fraction" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no material permittivity field, so "
            f"charge.dielectric_transition_nm = {transition} nm would derive a chi stage 7 gates "
            "and the solve ignores, as it refuses inputs.eps_r (PHY-24, section 5.4.3). Models "
            f"accepting it: {_accepting('solid_fraction')}"
        )
    if physics.solid_permittivities and not declared.solids:
        raise CaseValidationError(
            f"physics.model {model!r} carries no solid materials, so "
            "physics.solid_permittivities would be recorded and never applied; it is posed on a "
            "mesh with no solid domain (PHY-21 NOTE). Models carrying solids: "
            f"{_admitting(lambda other: declaration(other).solids)}"
        )
    if document.inputs.mesh is None and not declared.solids:
        # Every region stages 5 and 6 build carries a membrane and a protein, so
        # the stage-6 gate would refuse this case -- after meshing it.
        raise CaseValidationError(
            f"physics.model {model!r} carries no solid materials, so it is posed on a mesh with "
            "no solid domain (PHY-21 NOTE), and every mesh stages 5 and 6 generate carries a "
            "membrane and a protein; supply inputs.mesh with no solid domain. Models carrying "
            f"solids: {_admitting(lambda other: declaration(other).solids)}"
        )
    if document.inputs.pqr is not None and "fixed_charge" not in declared.coefficients:
        raise CaseValidationError(
            f"physics.model {model!r} takes no fixed-charge source, so inputs.pqr would be "
            "protonated into a charge stage 7 never deposits and the solve never reads (WP28 D8). "
            f"Models accepting it: {_accepting('fixed_charge')}"
        )
    for supplied, coefficient, what in (
        ("charge", "fixed_charge", "a fixed-charge source"),
        ("eps_r", "solid_fraction", "a material permittivity field"),
    ):
        if getattr(document.inputs, supplied) is not None and coefficient not in (
            declared.coefficients
        ):
            raise CaseValidationError(
                f"physics.model {model!r} takes no {what}, so inputs.{supplied} would be gated by "
                "stage 7 and recorded in the manifest while the solve ignored it (PHY-24). "
                f"Models accepting it: {_accepting(coefficient)}"
            )


def _check_strategy(document: CaseDocument) -> None:
    """Refuse a ``numerics.continuation`` the named model does not admit (section 6.5).

    Raises
    ------
    CaseValidationError
        Naming the model, the value, the values it admits and the models that
        admit the value asked for.
    """
    model = document.physics.model
    value = document.numerics.continuation
    admitted = declaration(model).strategies
    if value in admitted:
        return
    raise CaseValidationError(
        f"physics.model {model!r} admits numerics.continuation {', '.join(admitted)} only, not "
        f"{value!r}: the NUM-18 ladder is a path through named models, and every rung from "
        "stage 6 carries the flow coupling and transport this model may not have. Write "
        f"numerics.continuation: {' or '.join(admitted)}, or choose a model admitting {value!r}: "
        f"{_admitting(lambda other: value in declaration(other).strategies)}"
    )


def _check_outputs(document: CaseDocument) -> None:
    """Refuse an ``outputs:`` quantity the named model does not declare (section 5.3.1 NOTE).

    ``fields`` is the IF-07 export and not a quantity, and every model admits it.

    Raises
    ------
    CaseValidationError
        Naming the model, the words and the quantities it declares.
    """
    model = document.physics.model
    declared = declaration(model).quantities
    undeclared = [word for word in document.outputs if word != "fields" and word not in declared]
    if not undeclared:
        return
    advice = (
        f"remove {', '.join(undeclared)} from outputs"
        if declared
        else "write outputs: [] or outputs: [fields]"
    )
    raise CaseValidationError(
        f"outputs asks for {', '.join(undeclared)}, which physics.model {model!r} does not "
        f"provide; it declares {', '.join(declared) or 'no quantity of interest'} (section 6.7), "
        f"so {advice}. fields, the IF-07 export, is admitted for every model"
    )


def _model_options(
    document: CaseDocument, *, order: int, velocity_order: int, pressure_order: int
) -> dict[str, Any]:
    """Return the keyword arguments the named model's builder takes (PHY-21, WP26 D5).

    The case offers one candidate set and the model's declaration selects from it
    (section 5.4.3 NOTE): ``pnp`` fixes ``flow=False`` in its builder and does not
    declare it, and ``pb`` declares ``order`` alone. The candidate order is the one
    the keys have always been written in, so every model's resolved options, and
    with them its stage-10 key, are what they were before the declaration existed.
    :func:`_check_physics_switches` has already refused any case where the omission
    would hide a switch the user set.
    """
    physics = document.physics
    candidates: dict[str, Any] = {
        "solid_permittivities": dict(physics.solid_permittivities),
        "variable_density": physics.variable_density,
        "inertia": physics.inertia,
        "dielectric_gradient_forces": physics.dielectric_gradient_forces,
        "order": order,
        "velocity_order": velocity_order,
        "pressure_order": pressure_order,
        "stabilisation": document.numerics.stabilisation,
        "flow": physics.flow,
    }
    declared = declaration(physics.model).options
    return {key: value for key, value in candidates.items() if key in declared}


def build_model(
    model: str, electrolyte: Electrolyte, concentration_M: float, options: Mapping[str, Any]
) -> PhysicsModel:
    """Build the named model at the case's operating point (WP26 D6, D10).

    The one call site: every builder receives the electrolyte and the
    concentration beside the declared options. Building imports no
    finite-element backend, so :func:`resolve` does it once to surface a builder's
    own refusal while the case is being resolved.

    Raises
    ------
    CaseValidationError
        If the builder refuses the configuration, naming ``physics.model`` and
        carrying the builder's reason.
    """
    try:
        return create(model, electrolyte=electrolyte, concentration_M=concentration_M, **options)
    except (TypeError, ValueError) as error:
        raise CaseValidationError(
            f"physics.model {model!r} cannot be built for this case: {error}"
        ) from error


def _check_operating_point(document: CaseDocument) -> None:
    """Refuse a concentration, bias or distance cap no solve could use.

    Written so that NaN fails every test: ``nan <= 0`` is False, and a sweep
    plan resolves every point precisely so that an inadmissible one fails at
    plan time rather than after a ladder of non-converging Newton.
    """
    concentration = document.electrolyte.concentration_M
    if not (math.isfinite(concentration) and concentration > 0.0):
        raise CaseValidationError(
            f"electrolyte.concentration_M is {concentration!r}; it must be finite and positive"
        )
    bias = document.boundary_conditions.bias_V
    if not math.isfinite(bias):
        raise CaseValidationError(f"boundary_conditions.bias_V is {bias!r}; it must be finite")
    cap = document.numerics.wall_distance.max_distance_nm
    if not (math.isfinite(cap) and cap > 0.0):
        raise CaseValidationError(
            f"numerics.wall_distance.max_distance_nm is {cap!r}; the PHY-02 saturation distance "
            "must be finite and positive, or the wall functions are evaluated at a capped d"
        )


def resolve(document: CaseDocument) -> ResolvedCase:
    """Turn a validated case document into the objects the solver takes.

    Parameters
    ----------
    document
        A validated case document.

    Returns
    -------
    ResolvedCase
        The electrolyte, the model options, the Newton settings and the mesh the
        run is made of.

    Raises
    ------
    UnsupportedCaseSection
        If the case asks for a pipeline stage a later release owns; the message
        names the section and the release.
    CaseValidationError
        If the document is internally inconsistent — a species the parameter file
        does not carry, a steric diameter or a temperature disagreeing with it, an element label
        that is not one.
    """
    mesh = _require_runnable(document)
    structure = _resolve_structure(document)
    density = _resolve_density(document)
    contour = _resolve_contour(document, density)
    geometry = document.geometry if document.geometry is not None else Geometry()

    electrolyte = Electrolyte.from_parameter_file(
        document.electrolyte.parameters,
        switches=_switches(document),
        species=[species.name for species in document.electrolyte.species],
        driver=document.electrolyte.driver,
    )
    _check_species(document, electrolyte)
    _check_operating_point(document)

    elements = document.numerics.elements
    order = _order(elements.phi, "phi")
    concentration_order = _order(elements.c, "c")
    if concentration_order != order:
        raise CaseValidationError(
            f"numerics.elements.c is {elements.c!r} and numerics.elements.phi is "
            f"{elements.phi!r}; this release carries one order for phi and c_i, which the "
            "NUM-02 log branch and the PHY-05 steric term both assume"
        )
    # ``u`` is no longer folded into that equality. The reference mode of section
    # 6.4 runs phi and c at P2 with u and p at P1, so the velocity order is a
    # third order rather than a restatement of the first.
    velocity_order = _order(elements.u, "u")
    pressure_order = _order(elements.p, "p")
    if document.physics.flow:
        problem = inf_sup_problem(
            velocity_order=velocity_order,
            pressure_order=pressure_order,
            stabilisation=document.numerics.stabilisation,
        )
        if problem is not None:
            raise CaseValidationError(
                f"numerics.elements.u is {elements.u!r} and numerics.elements.p is "
                f"{elements.p!r}: {problem}"
            )

    physics = document.physics
    nonlinear = document.numerics.nonlinear
    options = _model_options(
        document, order=order, velocity_order=velocity_order, pressure_order=pressure_order
    )
    resolved = ResolvedCase(
        document=document,
        electrolyte=electrolyte,
        concentration_M=document.electrolyte.concentration_M,
        temperature_K=document.electrolyte.temperature_K,
        bias_V=document.boundary_conditions.bias_V,
        ground=document.boundary_conditions.ground,
        model=physics.model,
        model_options=options,
        newton=NewtonSettings(
            initial_damping=DEFAULT_SETTINGS.initial_damping,
            minimum_damping=DEFAULT_SETTINGS.minimum_damping,
            recovery_damping=DEFAULT_SETTINGS.recovery_damping,
            growth_factor=DEFAULT_SETTINGS.growth_factor,
            max_iterations=nonlinear.max_iter,
            relative_tolerance=nonlinear.rtol,
            absolute_tolerance=DEFAULT_SETTINGS.absolute_tolerance,
            reference_norm=DEFAULT_SETTINGS.reference_norm,
        ),
        linear_solver=document.numerics.linear.solver,
        stabilisation=document.numerics.stabilisation,
        continuation=document.numerics.continuation,
        wall_distance_sources=document.numerics.wall_distance.sources,
        wall_distance_max_nm=document.numerics.wall_distance.max_distance_nm,
        mesh=mesh,
        charge=document.inputs.charge,
        eps_r=document.inputs.eps_r,
        outputs=tuple(document.outputs),
        structure=structure,
        density=density,
        contour=contour,
        profile=document.inputs.profile,
        membrane=geometry.membrane if mesh is None else None,
        reservoir=geometry.reservoir if mesh is None else None,
        pqr=document.inputs.pqr,
        protonation=_resolve_protonation(document),
        smearing=(document.charge if document.charge is not None else Charge()).smearing,
        exclusion_offset_nm=(document.charge or Charge()).exclusion_offset_nm,
        dielectric_transition_nm=(document.charge or Charge()).dielectric_transition_nm,
    )
    # Built once and discarded, through the one call every consumer uses: a
    # builder's own refusal -- ``pb`` beside a salt that is not symmetric
    # monovalent -- is a case error, and is reported now rather than when stage
    # 10 builds the model again (WP26 D10).
    resolved.physics_model()
    return resolved


# -- the stage ----------------------------------------------------------------


class CaseStage:
    """Stage 9 of section 5.2: the resolved case document.

    Resolving is the work: validation has already happened at the file boundary,
    and what this stage adds is the check that the document describes a run *this
    release can perform*, before a mesh is read or a form assembled.
    """

    name = "case"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> CaseArtefact:
        """Resolve the case and emit the stage-9 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` is already set; resolution is too short to interrupt
            usefully, so the token is checked once on entry.
        """
        check_cancelled(cancel, "case")
        report(progress, 0.0, f"resolving case {inputs.case.name!r}")
        resolved = resolve(inputs.case)
        report(progress, 1.0, f"case {inputs.case.name!r} resolved")
        return CaseArtefact(inputs.case, summary=resolved.provenance)
