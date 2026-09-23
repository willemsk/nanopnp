"""The ``nanopnp/case/v1`` case-file schema, and its resolution to runnable objects.

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

import difflib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from nanopnp.io.artefact import CASE_SCHEMA, CaseArtefact, StageInputs
from nanopnp.materials.electrolyte import (
    CorrectionChoice,
    CorrectionSwitches,
    Electrolyte,
)
from nanopnp.physics.models import (
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

COUPLED_MODELS: frozenset[str] = frozenset({"epnp-ns", "pnp-ns", "pnp"})
"""Physics models the continuation ladder of NUM-18 drives (PHY-21).

``pb``, ``pb-linear`` and ``poisson`` are single-solve electrostatic models with
no ladder and no transport; they are registered and selectable, and the solve
stage refuses them by name rather than building a ladder that means nothing.
"""

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


# -- structure, geometry and charge: phases 2 and 3 ---------------------------


class StructureSource(_Strict):
    """The structure file and which of it to use."""

    pdb: Path
    variant: str | None = None
    chains: str = "all"


class Frames(_Strict):
    """Which trajectory frames enter the ensemble average."""

    last_ns: float | None = None
    count: int | None = None


class Ensemble(_Strict):
    """The trajectory and its frame selection."""

    trajectory: Path | None = None
    frames: Frames = Field(default_factory=Frames)


class SymmetrySpec(_Strict):
    """The expected point group and how the axis is found."""

    point_group: str
    axis: Literal["auto", "z"] = "auto"


class Structure(_Strict):
    """Stage 1: structure ingestion and alignment (v0.9)."""

    source: StructureSource
    ensemble: Ensemble = Field(default_factory=Ensemble)
    symmetry: SymmetrySpec


class DensitySpec(_Strict):
    """Stage 2: Gaussian smearing to a grid."""

    grid_spacing_nm: float = 0.05
    kernel: Literal["gaussian_vdw"] = "gaussian_vdw"
    sharpness: float = 0.93


class ContourSpec(_Strict):
    """Stage 4: contour extraction and conditioning."""

    isolevel: float = 0.25
    smoothing: Literal["taubin", "none"] = "taubin"
    simplify_tol_nm: float = 0.02


class MembraneSpec(_Strict):
    """The bilayer, defined analytically rather than from the density map."""

    thickness_nm: float = 2.8
    eps_r: float = 3.2


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
    """Stage 7: quintic B-spline deposition of the partial charges (PHY-16)."""

    sharpness: float = 0.5
    grid_spacing_nm: float = 0.005
    axis_cutoff_nm: float = 0.01


class Charge(_Strict):
    """Stage 7: charge assembly (v0.9)."""

    ph: float = 7.5
    forcefield: str = "CHARMM"
    titration: Literal["propka", "none"] = "propka"
    smearing: SmearingSpec = Field(default_factory=SmearingSpec)
    eps_protein: float = 20.0


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
    """Stage 6: the mesher and its size field (v0.9)."""

    backend: Literal["netgen", "gmsh"] = "netgen"
    wall_h_nm: float | Literal["auto"] = "auto"
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
    """A validated case file (schema ``nanopnp/case/v1``).

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
    """Return every editable field of ``nanopnp/case/v1``, in declaration order.

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
        If the schema grows a mapping whose *values* are blocks. ``nanopnp/case/v1``
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


def _set_at(payload: dict[str, FieldValue], path: str, value: FieldValue) -> None:
    """Set ``value`` into a dumped case document at a dotted path.

    Raises
    ------
    UnknownCasePathError
        If a block on the way is absent from this document. The path is known to
        the *schema* by the time this runs -- ``structure.source.pdb`` is a real
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
    against a shape it never declared.

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
        If the file is not a mapping, declares another schema, or fails
        validation; the message names every offending key by dotted path.
    """
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: a case file is a YAML mapping, found {type(raw).__name__}"
        )
    declared = raw.get("schema")
    if declared != SCHEMA:
        raise CaseValidationError(f"{source}: expected schema {SCHEMA!r}, found {declared!r}")
    try:
        return CaseDocument.model_validate(dict(raw))
    except ValidationError as error:
        raise CaseValidationError(render_problems(str(source), error), error) from error


def loads_case(text: str, *, source: str = "<string>") -> CaseDocument:
    """Validate a case document held in memory; see :func:`load_case`."""
    raw = yaml.safe_load(text)
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: a case file is a YAML mapping, found {type(raw).__name__}"
        )
    declared = raw.get("schema")
    if declared != SCHEMA:
        raise CaseValidationError(f"{source}: expected schema {SCHEMA!r}, found {declared!r}")
    try:
        return CaseDocument.model_validate(dict(raw))
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from error


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

_PIPELINE_SECTIONS: dict[str, str] = {
    "structure": "structure and trajectory ingestion (FR-01 to FR-03)",
    "geometry": "the density, contour and CAD pipeline (FR-04 to FR-10)",
    "charge": "the PDB2PQR charge and dielectric pipeline (FR-12 to FR-15)",
}
"""Case-file sections whose stages land in v0.9, with what each one drives."""


def _order(label: str, field: str) -> int:
    """Return the polynomial order a ``P<n>`` element label names."""
    try:
        return _ORDERS[label]
    except KeyError:
        raise CaseValidationError(
            f"numerics.elements.{field} {label!r} is not an element label; "
            f"the labels are {', '.join(sorted(_ORDERS))}"
        ) from None


SOLVE_IRRELEVANT_PROVENANCE = frozenset({"name", "outputs"})
"""Provenance keys that cannot change a converged field, so cannot key a solve.

Named by exclusion rather than by an allow-list: a key added to
:attr:`ResolvedCase.provenance` and forgotten here enters the solve's cache key,
which costs a re-solve, while one forgotten from an allow-list would be dropped
from the key and serve a stale solution for a changed case (section 5.3.2).
"""


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
    mesh: SuppliedArtefact
    charge: SuppliedArtefact | None
    eps_r: SuppliedArtefact | None
    outputs: tuple[str, ...]

    @property
    def name(self) -> str:
        """The case name, which names the run directory in the store."""
        return self.document.name

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


def _check_species(document: CaseDocument, electrolyte: Electrolyte) -> None:
    """Check the case's species and steric diameters against the parameter file.

    The diameters are *checked*, never applied: they are fitted parameters of the
    correction file (FR-16), and a case file that could override them silently
    would be a second source of truth for a physical constant.
    """
    problems: list[str] = []
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


def _require_runnable(document: CaseDocument) -> SuppliedArtefact:
    """Reject every section this release does not run, and return the supplied mesh.

    Returns
    -------
    SuppliedArtefact
        ``inputs.mesh``, which every Phase-1 run has by construction: the meshing
        pipeline is v0.9, so a case without one describes no run at all.
    """
    for section, what in _PIPELINE_SECTIONS.items():
        if getattr(document, section) is not None:
            raise UnsupportedCaseSection(
                f"case {document.name!r} carries a {section}: section; {what} is v0.9 "
                f"(SPECIFICATION.md section 3). This release runs on artefacts supplied through "
                "inputs:, which is FR-27's hand substitution at stage granularity"
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
                f"pipeline of v0.9 fills; supply inputs.{supplied}: path: instead"
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
    if document.inputs.mesh is None:
        raise UnsupportedCaseSection(
            f"case {document.name!r} supplies no inputs.mesh; the meshing pipeline is v0.9 "
            "(SPECIFICATION.md section 3, FR-10), so this release needs an externally supplied "
            "mesh (section 5.3.1 NOTE on inputs:)"
        )
    mesh = document.inputs.mesh
    nonlinear = document.numerics.nonlinear
    if nonlinear.strategy != "newton":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.strategy {nonlinear.strategy!r} is the NUM-20 fallback ladder, "
            "which is v0.5; this release solves every rung with the monolithic damped Newton of "
            "NUM-16"
        )
    if nonlinear.damping != "residual":
        raise UnsupportedCaseSection(
            f"numerics.nonlinear.damping {nonlinear.damping!r} is v0.5; this release uses the "
            "residual-monotonicity damping of NUM-16, whose recovery rule the reference records"
        )
    model = document.physics.model
    if model not in COUPLED_MODELS and document.numerics.continuation != "none":
        raise CaseValidationError(
            f"physics.model {model!r} has no transport to continue, so the NUM-18 ladder does not "
            f"apply to it; set numerics.continuation: none, or choose one of "
            f"{', '.join(sorted(COUPLED_MODELS))}"
        )
    _check_physics_switches(document)
    if model in COUPLED_MODELS and document.numerics.continuation != "none":
        _check_ladder_can_honour(document.physics)
    return mesh


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

    ``pnp`` gets its own message because it cannot take the advice the others
    get: :func:`_check_physics_switches` already requires ``physics.flow: false``
    for it, so "set them to match the ladder" is impossible by construction.
    """
    mismatched = [
        name for name, fixed in _LADDER_PHYSICS.items() if getattr(physics, name) != fixed
    ]
    if not mismatched:
        return
    if physics.model == "pnp":
        raise CaseValidationError(
            "physics.model 'pnp' cannot be run on the NUM-18 ladder: every rung from stage 6 "
            "carries the flow coupling, so the ladder would solve 'pnp-ns' while the manifest "
            "recorded 'pnp'; set numerics.continuation: none to solve the single cold rung, or "
            "choose 'pnp-ns' if the flow coupling was intended"
        )
    named = ", ".join(f"physics.{name}" for name in mismatched)
    raise CaseValidationError(
        f"{named} would be silently ignored by the NUM-18 ladder, which fixes the path rather "
        "than reading these from the case (flow on from stage 6, variable_density and inertia "
        "on, dielectric_gradient_forces off); set numerics.continuation: none to run a single "
        "rung with the switches as given, or set them to match the ladder"
    )


def _check_physics_switches(document: CaseDocument) -> None:
    """Refuse a case whose physics switches the named model cannot honour (PHY-21).

    A switch the solver silently drops is worse than one it refuses: the FR-25
    manifest would record ``flow: true`` beside a solution that has no velocity
    field in it, and a reader would have no way to tell. Each check here names
    something the chosen model fixes for itself — a switch, or one of the two
    supplied fields of stage 7, which are the same failure arriving as an input.
    """
    physics = document.physics
    model = physics.model
    if model == "pnp" and physics.flow:
        raise CaseValidationError(
            "physics.model 'pnp' is Poisson-Nernst-Planck with no flow coupling (PHY-21), so "
            "physics.flow must be false; 'pnp-ns' is the same transport model with flow"
        )
    if model in COUPLED_MODELS:
        return
    inapplicable = [
        name
        for name in (
            "flow",
            "variable_density",
            "inertia",
            "dielectric_gradient_forces",
            "solid_permittivities",
        )
        if getattr(physics, name)
    ]
    if inapplicable:
        named = ", ".join(f"physics.{name}" for name in inapplicable)
        raise CaseValidationError(
            f"physics.model {model!r} solves electrostatics alone (PHY-24): it carries no "
            f"momentum and no transport, so {named} would be recorded in the manifest and never "
            f"applied; set them false, or choose one of {', '.join(sorted(COUPLED_MODELS))}"
        )
    # The same rule for the two supplied fields, which are inputs rather than
    # switches: the electrostatic family of PHY-21 takes neither a material
    # permittivity nor a fixed-charge source, so stage 7 would gate the field,
    # the FR-25 manifest would record it, and the solve would never read it.
    supplied = [f"inputs.{name}" for name in ("charge", "eps_r") if getattr(document.inputs, name)]
    if supplied:
        raise CaseValidationError(
            f"physics.model {model!r} solves electrostatics alone (PHY-24): it takes no "
            f"fixed-charge source and no material permittivity, so {', '.join(supplied)} would "
            "be gated by stage 7 and recorded in the manifest while the solve ignored it; "
            f"choose one of {', '.join(sorted(COUPLED_MODELS))}"
        )


def _model_options(
    document: CaseDocument, *, order: int, velocity_order: int, pressure_order: int
) -> dict[str, Any]:
    """Return the keyword arguments the named model's builder takes (PHY-21).

    The builders are not uniform, and deliberately so:
    ``nanopnp.physics.models`` gives the electrostatic family only ``order``, and
    the ``pnp`` builder fixes ``flow=False`` itself. Passing every switch to every
    builder would raise a ``TypeError`` for a duplicate keyword on ``pnp`` and be
    rejected as unknown by ``pb``; :func:`_check_physics_switches` has already
    refused any case where the omission would hide a switch the user set.
    """
    physics = document.physics
    if physics.model not in COUPLED_MODELS:
        return {"order": order}
    options: dict[str, Any] = {
        "solid_permittivities": dict(physics.solid_permittivities),
        "variable_density": physics.variable_density,
        "inertia": physics.inertia,
        "dielectric_gradient_forces": physics.dielectric_gradient_forces,
        "order": order,
        "velocity_order": velocity_order,
        "pressure_order": pressure_order,
        "stabilisation": document.numerics.stabilisation,
    }
    if physics.model != "pnp":
        options["flow"] = physics.flow
    return options


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
        does not carry, a steric diameter disagreeing with it, an element label
        that is not one.
    """
    mesh = _require_runnable(document)

    electrolyte = Electrolyte.from_parameter_file(
        document.electrolyte.parameters,
        switches=_switches(document),
        species=[species.name for species in document.electrolyte.species],
        driver=document.electrolyte.driver,
    )
    _check_species(document, electrolyte)

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
    return ResolvedCase(
        document=document,
        electrolyte=electrolyte,
        concentration_M=document.electrolyte.concentration_M,
        temperature_K=document.electrolyte.temperature_K,
        bias_V=document.boundary_conditions.bias_V,
        ground=document.boundary_conditions.ground,
        model=physics.model,
        model_options=_model_options(
            document,
            order=order,
            velocity_order=velocity_order,
            pressure_order=pressure_order,
        ),
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
    )


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
