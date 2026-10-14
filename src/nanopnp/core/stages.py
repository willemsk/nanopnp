"""The stage protocol, and the registry that introspects stages without importing them."""

from __future__ import annotations

import importlib
import math
from collections.abc import Mapping
from dataclasses import KW_ONLY, dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, runtime_checkable

__all__ = [
    "ArtefactHook",
    "CancelFlag",
    "CancelToken",
    "Cancelled",
    "MissingExtraError",
    "Progress",
    "SolveHook",
    "SolveReporting",
    "Stage",
    "StageDescription",
    "StageEntry",
    "StageHook",
    "StageIdentifier",
    "StageName",
    "StageNameLiteral",
    "StageOption",
    "check_cancelled",
    "create",
    "describe",
    "register",
    "registered_stages",
    "report",
    "walk_order",
]


class StageName(StrEnum):
    """Canonical identifiers of all built-in pipeline stages."""

    CASE = "case"
    STRUCTURE = "structure"
    DENSITY = "density"
    SYMMETRY = "symmetry"
    CONTOUR = "contour"
    REGION = "region"
    MESH = "mesh"
    PROTONATION = "protonation"
    CHARGE = "charge"
    MATERIALS = "materials"
    SOLVE = "solve"
    QOI = "qoi"
    REPORT = "report"


StageNameLiteral: TypeAlias = Literal[
    "case",
    "structure",
    "density",
    "symmetry",
    "contour",
    "region",
    "mesh",
    "protonation",
    "charge",
    "materials",
    "solve",
    "qoi",
    "report",
]
StageIdentifier: TypeAlias = StageName | StageNameLiteral

StageOption: TypeAlias = Any

if TYPE_CHECKING:  # pragma: no cover - imported for annotations only
    # ``io`` depends on ``core``, never the reverse at run time
    from nanopnp.io.artefact import Artefact, StageInputs


class Cancelled(RuntimeError):  # noqa: N818 - see the docstring: this is not a failure
    """A stage was cancelled through its cancel token and did not finish; not a failure."""


class Progress(Protocol):
    """Called by a running stage with its completion fraction and a message."""

    def __call__(self, fraction: float, message: str) -> None:
        """Report ``fraction`` in [0, 1], monotonically, ending at 1."""


class StageHook(Protocol):
    """Called before each stage of a pipeline walk, with the stage's position."""

    def __call__(self, name: str, index: int, total: int) -> None:
        """Report that stage ``index`` of ``total`` (0-based) is about to run."""


class SolveHook(Protocol):
    """Called by the solve with each continuation rung and each Newton step."""

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        """Report that rung ``index`` of ``total`` (0-based) is about to be solved."""

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        """Report one accepted Newton step of the rung most recently announced."""


class ArtefactHook(Protocol):
    """Called after each stage of a pipeline walk, once its artefact is in the store."""

    def __call__(self, name: str, schema: str, hash: str, cached: bool) -> None:
        """Report that stage ``name`` produced artefact ``(schema, hash)``."""


@runtime_checkable
class SolveReporting(Protocol):
    """A stage that accepts a progress hook, which is not part of its artefact key."""

    def with_solve_hook(self, hook: SolveHook) -> Stage:
        """Return a copy of this stage that reports through ``hook``."""


@runtime_checkable
class CancelToken(Protocol):
    """Asked by a running stage whether the caller has asked it to stop."""

    def cancelled(self) -> bool:
        """Return whether the stage should raise ``Cancelled``."""


class CancelFlag:
    """A cancel token a caller sets from another thread."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the running stage to stop at its next check."""
        self._cancelled = True

    def cancelled(self) -> bool:
        """Return whether the stage should raise ``Cancelled``."""
        return self._cancelled


def check_cancelled(cancel: CancelToken | None, where: str) -> None:
    """Raise Cancelled if ``cancel`` has been set; ``where`` names the step about to run."""
    if cancel is not None and cancel.cancelled():
        raise Cancelled(f"cancelled before {where}")


def report(progress: Progress | None, fraction: float, message: str) -> None:
    """Call ``progress`` if there is one, clamping the fraction into [0, 1]."""
    if progress is not None:
        progress(min(1.0, max(0.0, fraction)), message)


@dataclass(frozen=True)
class StageDescription:
    """What a stage takes, produces and is called, without importing it.

    Parameters
    ----------
    needs_section
        The case section the stage reads, or None.
    weight
        The stage's share of a walk's progress; finite and positive.
    """

    name: str
    number: int
    title: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    artefact_schema: str
    _: KW_ONLY
    takes_workspace: bool
    takes_store: bool
    key_is_artefact: bool
    weight: float
    needs_section: str | None
    optional_inputs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name))

    def summary(self) -> dict[str, Any]:
        """Return this description as plain data, for the CLI and the GUI."""
        return {
            "name": self.name,
            "number": self.number,
            "title": self.title,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "artefact_schema": self.artefact_schema,
            "takes_workspace": self.takes_workspace,
            "takes_store": self.takes_store,
            "key_is_artefact": self.key_is_artefact,
            "weight": self.weight,
            "needs_section": self.needs_section,
            "optional_inputs": list(self.optional_inputs),
        }


class Stage(Protocol):
    """One pipeline stage: typed inputs to a hashed artefact."""

    name: str

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""

    def key(self, inputs: StageInputs) -> Artefact:
        """Return the artefact ``run`` will produce, without its payload."""

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> Artefact:
        """Run the stage and return its artefact."""


@dataclass(frozen=True)
class StageEntry:
    """One registry row: a description, and where the implementation lives."""

    description: StageDescription
    target: str
    extra: str | None = None


class MissingExtraError(ImportError):
    """Raised when a registered stage needs an optional extra that is not installed."""


_REGISTRY: dict[str, StageEntry] = {}


def register(description: StageDescription, target: str, *, extra: str | None = None) -> None:
    """Register a stage under its name; ValueError for a duplicate or malformed entry."""
    if description.name in _REGISTRY:
        raise ValueError(
            f"stage {description.name!r} is already registered as "
            f"{_REGISTRY[description.name].target!r}; replacing it would let two runs share a "
            "manifest and execute different code"
        )
    if target.count(":") != 1:
        raise ValueError(f"stage target {target!r} must be of the form 'module:attribute'")
    for name in description.inputs:
        if name != "case_path" and name not in _REGISTRY:
            raise ValueError(
                f"stage {description.name!r} takes input {name!r}, which is neither 'case_path' "
                "nor a stage registered before it; the walk runs stages in registration order, "
                "so register its inputs first"
            )
    stray = [name for name in description.optional_inputs if name not in description.inputs]
    if stray:
        raise ValueError(
            f"stage {description.name!r} declares optional input {stray[0]!r}, which is not one "
            f"of its inputs {description.inputs}"
        )
    if not (math.isfinite(description.weight) and description.weight > 0):
        raise ValueError(
            f"stage {description.name!r} has progress weight {description.weight!r}; a weight "
            "must be finite and positive"
        )
    _REGISTRY[description.name] = StageEntry(description=description, target=target, extra=extra)


def walk_order() -> tuple[str, ...]:
    """Return every registered stage name in registration order, which is a dependency order."""
    return tuple(_REGISTRY)


def registered_stages() -> tuple[StageDescription, ...]:
    """Return every registered stage's description, by pipeline number and then registration."""
    order = {name: index for index, name in enumerate(_REGISTRY)}
    return tuple(
        sorted(
            (entry.description for entry in _REGISTRY.values()),
            key=lambda d: (d.number, order[d.name]),
        )
    )


def describe(name: StageIdentifier | str) -> StageDescription:
    """Return one stage's description without importing its module; KeyError if unregistered."""
    entry = _REGISTRY.get(str(name))
    if entry is None:
        known = ", ".join(sorted(_REGISTRY)) or "none"
        raise KeyError(f"no stage {name!r}; registered stages are {known}")
    return entry.description


def create(name: StageIdentifier | str, **kwargs: StageOption) -> Stage:
    """Import a stage's module and construct it with ``kwargs``; KeyError if unregistered."""
    describe(name)
    entry = _REGISTRY[str(name)]
    module_name, _, attribute = entry.target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        missing = error.name or ""
        if entry.extra is None or missing == "nanopnp" or missing.startswith("nanopnp."):
            raise
        raise MissingExtraError(
            f"stage {name!r} needs the {entry.extra!r} extra: importing {module_name} failed "
            f"because {missing!r} is not installed. Install the extras with "
            "`uv sync --all-extras`",
            name=missing,
        ) from error
    factory = getattr(module, attribute)
    stage: Stage = factory(**kwargs)
    return stage


def _register_builtins() -> None:
    # Registration order is the walk's order; stage 9 comes first, every stage consumes its case.
    register(
        StageDescription(
            name=StageName.CASE,
            number=9,
            title="Case assembly",
            inputs=("case_path",),
            outputs=("resolved case document",),
            artefact_schema="nanopnp/case/v0.5",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=True,
            # Weights are shares of a walk's progress; the solve is the run, and equal weights
            # would hold a progress bar near its end for the whole ladder.
            weight=0.01,
            needs_section=None,
            optional_inputs=(),
        ),
        "nanopnp.pipeline.case:CaseStage",
    )
    register(
        StageDescription(
            name=StageName.STRUCTURE,
            number=1,
            title="Structure ingestion and alignment",
            inputs=("case",),
            outputs=("aligned ensemble", "Cn axis on z at r = 0", "symmetry-gate record"),
            artefact_schema="nanopnp/structure/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.05,
            needs_section="structure",
            optional_inputs=(),
        ),
        "nanopnp.structure.stage:StructureStage",
        extra="structure",
    )
    register(
        StageDescription(
            name=StageName.DENSITY,
            number=2,
            title="Density map",
            inputs=("case", "structure"),
            outputs=("ensemble-mean union density on a canonical 3D grid", "radius-set record"),
            artefact_schema="nanopnp/density/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            # Stage 2 deposits every frame's atoms: seconds for a crystal, minutes for an ensemble.
            weight=0.2,
            needs_section="structure",
            optional_inputs=(),
        ),
        "nanopnp.density.stage:DensityStage",
    )
    register(
        StageDescription(
            name=StageName.SYMMETRY,
            number=3,
            title="Symmetry reduction to (r, z)",
            inputs=("case", "density"),
            outputs=("(r, z) mean", "Cn-averaged and raw azimuthal variance"),
            artefact_schema="nanopnp/reduced/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.05,
            needs_section="structure",
            optional_inputs=(),
        ),
        "nanopnp.symmetry.stage:SymmetryStage",
    )
    register(
        StageDescription(
            name=StageName.CONTOUR,
            number=4,
            title="Contour extraction and conditioning",
            inputs=("case", "structure", "symmetry"),
            outputs=(
                "conditioned closed polyline, a nanopnp/profile/v0.5 document",
                "conditioning and gate record",
                "probe-radius profile",
            ),
            artefact_schema="nanopnp/profile/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.03,
            needs_section="structure",
            optional_inputs=(),
        ),
        "nanopnp.geometry.contour:ContourStage",
        extra="structure",
    )
    register(
        StageDescription(
            name=StageName.REGION,
            number=5,
            title="CAD assembly",
            inputs=("case", "contour"),
            outputs=(
                "tagged (r, z) region, a nanopnp/region/v0.5 record",
                "membrane inner edge and junction-gate record",
            ),
            artefact_schema="nanopnp/region/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.01,
            needs_section=None,
            optional_inputs=("contour",),
        ),
        "nanopnp.geometry.region:RegionStage",
    )
    register(
        StageDescription(
            name=StageName.MESH,
            number=6,
            title="Mesh",
            inputs=("case", "region"),
            outputs=("tagged mesh", "element-quality report", "size-field record"),
            artefact_schema="nanopnp/mesh/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            # Generating a mesh takes 6-8 s on the reference profile.
            weight=0.05,
            needs_section=None,
            optional_inputs=("region",),
        ),
        "nanopnp.mesh.ingest:MeshStage",
    )
    register(
        StageDescription(
            name=StageName.PROTONATION,
            number=7,
            title="Protonation",
            inputs=("case", "structure"),
            outputs=(
                "per-frame atom table with charges and radii",
                "Q_net per frame",
                "titratable residue states",
            ),
            artefact_schema="nanopnp/protonation/v0.5",
            takes_workspace=True,
            # Each frame is stored under its own key, so a changed frame selection re-protonates
            # only the added frames.
            takes_store=True,
            key_is_artefact=False,
            # About a minute per frame of a ClyA dodecamer, PROPKA included.
            weight=1.0,
            needs_section=None,
            optional_inputs=("structure",),
        ),
        # No extra: inputs.pqr runs without PDB2PQR, imported only when the stage protonates.
        "nanopnp.charge.protonation:ProtonationStage",
    )
    register(
        StageDescription(
            name=StageName.CHARGE,
            number=7,
            title="Charge assembly",
            inputs=("case", "mesh", "protonation", "region"),
            outputs=(
                "fixed-charge field, deposited on the mesh or supplied",
                "export lattice, a nanopnp/field/v0.5 document",
                "dielectric solid fraction",
                "charge-conservation report",
            ),
            artefact_schema="nanopnp/fields/v0.5",
            takes_workspace=True,
            # The export lattice is keyed without the mesh, so a mesh-convergence sweep
            # re-deposits without re-summing.
            takes_store=True,
            key_is_artefact=False,
            weight=0.2,
            needs_section=None,
            optional_inputs=("protonation", "region"),
        ),
        "nanopnp.charge.stage:FieldStage",
    )
    register(
        StageDescription(
            name=StageName.MATERIALS,
            number=8,
            title="Materials",
            inputs=("case",),
            outputs=("electrolyte", "correction models", "resolved coefficient set"),
            artefact_schema="nanopnp/materials/v0.5",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=True,
            weight=0.01,
            needs_section=None,
            optional_inputs=(),
        ),
        "nanopnp.materials.stage:MaterialsStage",
    )
    register(
        StageDescription(
            name=StageName.SOLVE,
            number=10,
            title="Solve",
            inputs=("case", "charge", "materials", "mesh"),
            outputs=("converged fields", "iteration history"),
            artefact_schema="nanopnp/solution/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.75,
            needs_section=None,
            optional_inputs=("charge",),
        ),
        "nanopnp.solve.stage:SolveStage",
    )
    register(
        StageDescription(
            name=StageName.QOI,
            number=11,
            title="Quantities of interest",
            inputs=("case", "charge", "mesh", "solve"),
            outputs=("scalar quantities of interest", "route-agreement record"),
            artefact_schema="nanopnp/qoi/v0.5",
            takes_workspace=False,
            takes_store=False,
            key_is_artefact=False,
            weight=0.08,
            needs_section=None,
            optional_inputs=("charge",),
        ),
        "nanopnp.post.stage:QoIStage",
    )
    register(
        StageDescription(
            name=StageName.REPORT,
            number=12,
            title="Report",
            inputs=("case", "charge", "mesh", "qoi", "solve"),
            outputs=("field export", "run record"),
            artefact_schema="nanopnp/report/v0.5",
            takes_workspace=True,
            takes_store=False,
            key_is_artefact=False,
            weight=0.04,
            needs_section=None,
            optional_inputs=("charge",),
        ),
        "nanopnp.post.stage:ReportStage",
    )


_register_builtins()


def _catalogue() -> Mapping[str, StageEntry]:
    return _REGISTRY
