"""The ``nanopnp/case/v0.5`` case-file schema: its shape, its diagnostics, reading and writing."""

from __future__ import annotations

import difflib
import itertools
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias, get_args

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.core.paths import available_corrections
from nanopnp.io.artefact import CASE_SCHEMA

SCHEMA: str = CASE_SCHEMA


FieldType: TypeAlias = Any


FieldValue: TypeAlias = Any


CORRECTION_PROPERTIES: tuple[str, ...] = (
    "diffusivity",
    "mobility",
    "viscosity",
    "permittivity",
    "density",
)


STERIC_MODELS: frozenset[str] = frozenset({"none", "borukhov"})


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


class CaseValidationError(ValueError):
    """A case document failed validation; the message names every offending key by dotted path."""

    def __init__(self, message: str, errors: ValidationError | None = None) -> None:
        super().__init__(message)
        self.errors = errors


class UnsupportedCaseSection(NotImplementedError):  # noqa: N818 - a release gap, not a failure
    """The case asks for a section this release does not run; the message names its release."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SuppliedArtefact(_Strict):
    """One upstream stage output supplied from outside the pipeline, by path or hash."""

    path: Path | None = None
    artefact: str | None = None
    format: str | None = None
    groups: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _exactly_one_source(self) -> SuppliedArtefact:
        if (self.path is None) == (self.artefact is None):
            raise ValueError(
                "a supplied artefact names exactly one of path: (a file on disk) and artefact: "
                "(a content hash already in the store)"
            )
        return self


SUPPLIED_FIELDS: dict[str, str] = {
    "charge": "a fixed-charge field",
    "eps_r": "a dielectric field",
}


def stored_artefact_refused(key: str) -> UnsupportedCaseSection:
    """Return the refusal of a hash-named output under ``inputs.<key>``: mesh, charge or eps_r."""
    if key == "mesh":
        return UnsupportedCaseSection(
            "inputs.mesh: artefact: names a mesh by its store hash. FR-27's substitution reads "
            "a supplied mesh by path only; the store form is REV-62, deferred to v0.6 (section "
            "8.2.9 I3); supply inputs.mesh: path: instead"
        )
    return UnsupportedCaseSection(
        f"inputs.{key}: artefact: names {SUPPLIED_FIELDS[key]} by its store hash. FR-27's "
        "substitution reads a supplied field by path only, and no release of SPECIFICATION.md "
        f"schedules the store form; supply inputs.{key}: path: instead"
    )


class Inputs(_Strict):
    """Supplied upstream artefacts, by the stage whose output each replaces."""

    mesh: SuppliedArtefact | None = None
    charge: SuppliedArtefact | None = None
    eps_r: SuppliedArtefact | None = None
    profile: SuppliedArtefact | None = None
    pqr: SuppliedArtefact | None = None


class StructureSource(_Strict):
    """The structure file and the MDAnalysis selection naming the pore."""

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


class Symmetry(_Strict):
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
    """Stage 1: structure ingestion and alignment."""

    source: StructureSource
    ensemble: Ensemble = Field(default_factory=Ensemble)
    symmetry: Symmetry


class Density(_Strict):
    """Stage 2: Gaussian smearing to a grid."""

    grid_spacing_nm: float = 0.05
    kernel: Literal["gaussian_vdw"] = "gaussian_vdw"
    sharpness: float = 0.93


class Contour(_Strict):
    """Stage 4: contour extraction and conditioning."""

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


class Membrane(_Strict):
    """The bilayer, defined analytically; ``centre_z_nm`` is in the structure's frame."""

    thickness_nm: float = 2.8
    centre_z_nm: float = 0.0


class Reservoir(_Strict):
    """The reservoir half-disc."""

    radius_nm: float = 250.0


class Pore(_Strict):
    """An idealised pore declared in the case: its shape and lumen radius."""

    shape: Literal["cylinder"]
    radius_nm: float = Field(gt=0.0, allow_inf_nan=False)


class Analyte(_Strict):
    """An axisymmetric analyte body in the pore."""

    shape: Literal["sphere", "prolate_spheroid", "oblate_spheroid"]
    a_nm: float
    b_nm: float | None = None
    z_nm: float = 0.0
    charge_e: float = 0.0


class Geometry(_Strict):
    """Stages 2-5: density, contour, membrane, reservoir and analyte."""

    density: Density = Field(default_factory=Density)
    contour: Contour = Field(default_factory=Contour)
    membrane: Membrane = Field(default_factory=Membrane)
    reservoir: Reservoir = Field(default_factory=Reservoir)
    analyte: Analyte | None = None
    pore: Pore | None = None


class Smearing(_Strict):
    """Stage 7: the kernel width and export lattice."""

    sharpness: float = 0.5
    grid_spacing_nm: float = 0.005
    axis_cutoff_nm: float = 0.01


class Charge(_Strict):
    """Stage 7: charge assembly; the offsets are switches whose validated default is 0."""

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
    smearing: Smearing = Field(default_factory=Smearing)
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


class Species(_Strict):
    """One solved ionic species, by the name the parameter file gives it."""

    name: str
    z: int


class CorrectionChoice(_Strict):
    """One property's correction: a registered model and its concentration and wall parts."""

    model: str = "none"
    concentration: bool = True
    wall: bool = True


class Steric(_Strict):
    """The size-modified flux and the diameters it is built on."""

    model: Literal["none", "borukhov"] = "none"
    a_ion_nm: float | None = None
    a_water_nm: float | None = None


class Corrections(_Strict):
    """The nine independently switchable corrections."""

    diffusivity: CorrectionChoice = Field(default_factory=CorrectionChoice)
    mobility: CorrectionChoice = Field(default_factory=CorrectionChoice)
    viscosity: CorrectionChoice = Field(default_factory=CorrectionChoice)
    permittivity: CorrectionChoice = Field(default_factory=CorrectionChoice)
    density: CorrectionChoice = Field(default_factory=CorrectionChoice)
    steric: Steric = Field(default_factory=Steric)


class Electrolyte(_Strict):
    """Stage 8: the electrolyte, its reference parameter file and its corrections."""

    species: list[Species]
    concentration_M: float
    temperature_K: float = 298.15
    parameters: str = "willems2020_nacl"
    driver: Literal["average", "ionic_strength"] = "average"
    corrections: Corrections = Field(default_factory=Corrections)


class Wall(_Strict):
    """The conditions applied on the pore and membrane walls."""

    ion_flux: Literal["no_flux", "prescribed"] = "no_flux"
    slip: Literal["no_slip", "navier", "free"] = "no_slip"


class BoundaryConditions(_Strict):
    """The applied bias, the grounded electrode and the wall conditions."""

    bias_V: float
    ground: Literal["cis", "trans"] = "cis"
    walls: Wall = Field(default_factory=Wall)
    wall_charge_C_m2: float = Field(
        default=0.0,
        allow_inf_nan=False,
        description=(
            "The uniform surface charge density of an idealised pore's wall, in C/m^2; read "
            "only beside geometry.pore."
        ),
    )


class Physics(_Strict):
    """The named physics model and its switches."""

    model: str = "epnp-ns"
    flow: bool = True
    variable_density: bool = True
    inertia: bool = True
    dielectric_gradient_forces: bool = False
    solid_permittivities: dict[str, Annotated[float, Field(gt=0.0, allow_inf_nan=False)]] = Field(
        default_factory=dict
    )


class Elements(_Strict):
    """Element orders per field; an equal-order pair needs a stabilising flow mode."""

    phi: str = "P2"
    c: str = "P2"
    u: str = "P2"
    p: str = "P1"


class Mesh(_Strict):
    """Stage 6: the mesher and its size field."""

    backend: str = Field(
        default="netgen",
        description="The mesher backend, checked against the mesher registry (section 5.5).",
    )
    wall_h_nm: float | Literal["auto"] = "auto"
    wall_for_concentration_M: float | None = Field(
        default=None,
        gt=0.0,
        allow_inf_nan=False,
        description=(
            "The concentration, in mol/L, at whose Debye length `wall_h_nm: auto` is sized; "
            "none sizes it at the case's own."
        ),
    )
    maxh_nm: float | None = Field(
        default=None,
        gt=0.0,
        allow_inf_nan=False,
        description=(
            "The global element size of an idealised pore, in nm; none takes the global size "
            "of the size field. Read only beside geometry.pore."
        ),
    )
    size_scale: float = Field(default=1.0, gt=0.0, allow_inf_nan=False)
    boundary_layer: bool = False


class Nonlinear(_Strict):
    """The damped-Newton policy; the defaults are the reference settings."""

    strategy: Literal["newton", "hybrid"] = "newton"
    damping: Literal["residual", "backtracking"] = "residual"
    max_iter: int = Field(default=100, ge=1)
    rtol: float = Field(default=1.0e-6, gt=0.0, lt=1.0, allow_inf_nan=False)


class Linear(_Strict):
    """The direct linear solver."""

    solver: str = Field(
        default="umfpack",
        description="Direct linear solver, checked against the solver registry (section 5.5).",
    )


class WallDistance(_Strict):
    """The wall-distance field: its source boundaries, as a regular expression, and its cap."""

    sources: str = "wall"
    max_distance_nm: float = 3.0


class Numerics(_Strict):
    """Discretisation, meshing, continuation, stabilisation and the solvers."""

    elements: Elements = Field(default_factory=Elements)
    mesh: Mesh = Field(default_factory=Mesh)
    nonlinear: Nonlinear = Field(default_factory=Nonlinear)
    continuation: Literal["default_ladder", "none"] = "default_ladder"
    stabilisation: str = Field(
        default="none",
        description=(
            "Residual stabilisation mode, checked against the stabilisation registry (section 5.5)."
        ),
    )
    wall_distance: WallDistance = Field(default_factory=WallDistance)
    linear: Linear = Field(default_factory=Linear)


class CaseDocument(_Strict):
    """A validated case file (schema ``nanopnp/case/v0.5``)."""

    schema_id: str = Field(alias="schema")
    name: str
    inputs: Inputs = Field(default_factory=Inputs)
    structure: Structure | None = None
    geometry: Geometry | None = None
    charge: Charge | None = None
    electrolyte: Electrolyte
    boundary_conditions: BoundaryConditions
    physics: Physics = Field(default_factory=Physics)
    numerics: Numerics = Field(default_factory=Numerics)
    outputs: list[str] = Field(default_factory=lambda: ["current"])
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, title="Case")

    @model_validator(mode="after")
    def _check_installed(self) -> CaseDocument:
        problems: list[str] = []
        installed = available_corrections()
        for name in CORRECTION_PROPERTIES:
            choice: CorrectionChoice = getattr(self.electrolyte.corrections, name)
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
            defaults = Mesh()
            for key in Mesh.model_fields:
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


PQR_FORMAT = "pqr"


PROFILE_FORMAT = "profile1"


def _model_of(annotation: object) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for argument in get_args(annotation):
        found = _model_of(argument)
        if found is not None:
            return found
    return None


def _owner_of(loc: Sequence[str | int]) -> type[BaseModel]:
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
    return sorted(field.alias or name for name, field in model.model_fields.items())


def render_problems(source: str, error: ValidationError) -> str:
    """Render a pydantic error as one ``<dotted.path>: <what>`` line per problem."""
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


def read_case(path: str | Path) -> CaseDocument:
    """Read a case file, check its schema string first, and return the validated document.

    Raises
    ------
    CaseValidationError
        If the file is not a mapping, names another schema, or fails validation.
    """
    source = Path(path)
    return _validate(yaml.safe_load(source.read_text(encoding="utf-8")), str(source))


def read_case_text(
    text: str, *, source: str = "<string>", model: type[CaseDocument] = CaseDocument
) -> CaseDocument:
    """Validate a case document held in memory against the schema; see :func:`read_case`.

    Parameters
    ----------
    model
        The class to build: ``CaseDocument``, or a subclass that adds methods and no field.
    """
    return _validate(yaml.safe_load(text), source, model)


def _validate(raw: object, source: str, model: type[CaseDocument] = CaseDocument) -> CaseDocument:
    if not isinstance(raw, Mapping):
        raise CaseValidationError(
            f"{source}: a case file is a YAML mapping, found {type(raw).__name__}"
        )
    declared = raw.get("schema")
    if declared != SCHEMA:
        raise CaseValidationError(f"{source}: expected schema {SCHEMA!r}, found {declared!r}")
    try:
        return model.model_validate(dict(raw))
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from error


def dump_case(document: CaseDocument, path: str | Path) -> Path:
    """Write a validated case document back to YAML and return the path written."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps_case(document), encoding="utf-8")
    return target


def dumps_case(document: CaseDocument) -> str:
    """Return a validated case document as YAML text, under the aliases a case file writes."""
    return str(yaml.safe_dump(document.model_dump(by_alias=True, mode="json"), sort_keys=False))
