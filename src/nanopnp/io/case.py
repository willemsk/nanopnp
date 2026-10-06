"""The ``nanopnp/case/v2`` case-file schema: its shape, its diagnostics, reading and writing.

One declarative YAML document is the unit of reproducibility (IF-03,
``SPECIFICATION.md`` section 5.3.1); everything else is derived. This module owns
its shape and its diagnostics. It is the base of the case: it imports ``core``
and ``io`` alone at run time, so every stage can read the schema's types without
reaching the registries above it. The checks that ask an installed registry, and
the step that turns a document into the objects the solver takes, are
:mod:`nanopnp.pipeline.checks` and :mod:`nanopnp.pipeline.case`.

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
:func:`nanopnp.pipeline.case.resolve` produces the objects, and
:attr:`nanopnp.io.resolved.ResolvedCase.provenance` the record; equality of
either is a statement about the *run*, which is what FR-26 means by
"semantically identical".
"""

from __future__ import annotations

import copy
import difflib
import itertools
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, TypeAlias, get_args

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.core.paths import available_corrections
from nanopnp.io.artefact import CASE_SCHEMA, CASE_SCHEMA_V1

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
the one place a solid's permittivity is set (PHY-20; author ruling)."""


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

Named once because two things index the case by them: :meth:`CaseDocument._check_installed`,
which refuses a model that is not installed, and
:func:`nanopnp.pipeline.checks.registry_options`, which
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

    Raised by :func:`nanopnp.pipeline.case.resolve` naming the section and the release that owns it,
    so that a Phase-2 case run against the solver core says which release will
    run it rather than failing somewhere inside the solver.
    """


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


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
    exclusion_offset_nm: float = Field(
        default=0.0,
        ge=0.0,
        allow_inf_nan=False,
        description=(
            "The ion-exclusion shell's width a, in nm: stage 5 offsets the profile by a and "
            "meshes the shell as material exclusion, with wall on its outer surface. 0, the "
            "validated default, builds none; refused at or below twice the density grid spacing, "
            "and beside inputs.mesh (section 5.2.1 NOTE on the ion-exclusion shell)"
        ),
    )
    dielectric_transition_nm: float = Field(
        default=0.0,
        ge=0.0,
        allow_inf_nan=False,
        description=(
            "The width delta, in nm, of the protein's dielectric transition to water: stage 7 "
            "derives chi from the profile as a C1 step of width delta. 0, the validated default, "
            "keeps PHY-20's sharp split; refused below the density grid spacing, beside "
            "inputs.eps_r and beside inputs.mesh (section 4.4 NOTE on the derived solid fraction)"
        ),
    )


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
    stabilisation supplies the missing inf-sup stability —
    :func:`nanopnp.pipeline.checks.check_document` refuses
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

    backend: str = Field(
        default="netgen",
        description="The mesher backend, checked against the mesher registry (section 5.5).",
    )
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

    solver: str = Field(
        default="umfpack",
        description="Direct linear solver, checked against the solver registry (section 5.5).",
    )


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
    stabilisation: str = Field(
        default="none",
        description=(
            "Residual stabilisation mode, checked against the stabilisation registry (section 5.5)."
        ),
    )
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
    def _check_installed(self) -> CaseDocument:
        """Check every correction file and output the document names.

        The four names an installed *registry* governs -- ``physics.model``,
        ``numerics.mesh.backend``, ``numerics.stabilisation`` and
        ``numerics.linear.solver`` -- are checked
        by :func:`nanopnp.pipeline.checks.check_document`, above the registries,
        so that this schema imports nothing above ``core`` (WP38 D7).

        Raises
        ------
        ValueError
            Naming the value and the installed alternatives. Doing this at
            validation rather than at solve time is what stops a misspelt
            correction model from disabling a correction silently.
        """
        problems: list[str] = []
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


PQR_FORMAT = "pqr"
"""``inputs.pqr.format``: a PQR of one frame or one ``MODEL`` per frame (section 5.3.1 NOTE)."""


PROFILE_FORMAT = "profile1"
"""``inputs.profile.format``: a ``nanopnp/profile/v1`` document (section 5.3.1 NOTE)."""


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


def read_case(path: str | Path) -> CaseDocument:
    """Read a case file and validate it against the schema.

    The structural read: the registry checks are
    :func:`nanopnp.pipeline.case.load_case`'s, which is this followed by
    :func:`nanopnp.pipeline.checks.check_document` and is what every caller
    outside the base uses (WP38 D7).

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


def read_case_text(text: str, *, source: str = "<string>") -> CaseDocument:
    """Validate a case document held in memory against the schema; see :func:`read_case`."""
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
