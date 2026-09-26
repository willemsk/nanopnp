"""The stage protocol, and the registry that introspects stages without importing them.

FR-27 requires every pipeline stage of section 5.2 to be independently
invocable, cancellable and introspectable, and section 5.3.2 makes each one a
pure function of its inputs by keying its artefact on their hashes. Three
consequences are all this module holds.

**Introspection must not import the stage.** ``nanopnp stage --list`` and the
desktop shell's stage browser exist to say what a stage takes and produces; if
answering that imported ``nanopnp.solve.stage`` it would import NGSolve, which
costs about 370 ms in every CLI, GUI and sweep-worker process. So the registry
holds each stage's :class:`StageDescription` *beside* a ``"module:attribute"``
target string, and :func:`create` is the only function that resolves it.

**Cancellation is cooperative.** A :class:`CancelToken` is checked between rungs
and inside the damped-Newton callback, and :class:`Cancelled` unwinds the solve.
Interrupting a UMFPACK factorisation would need a subprocess and a signal; the
desktop shell has one above this layer (ADR-004).

**Progress is a fraction, not a log line.** ``progress(fraction, message)`` is
monotone in [0, 1] and ends at 1, so a caller can drive a bar without parsing
anything. What a caller has to *act* on travels beside it as data:
:class:`StageHook` carries the stage transition, :class:`SolveHook` the
continuation rung and the Newton step. Both exist because the alternative is a
caller parsing a caption, which makes a display format into an interface.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, runtime_checkable

StageOption: TypeAlias = Any
"""A keyword argument passed through to a stage's constructor."""

if TYPE_CHECKING:  # pragma: no cover - imported for annotations only
    # ``io`` depends on ``core`` and never the other way round at run time. The
    # protocol below still has to name the artefact it returns, and
    # ``from __future__ import annotations`` keeps that name a string, so the
    # dependency stays where it belongs: in the type checker.
    from nanopnp.io.artefact import Artefact, StageInputs


class Cancelled(RuntimeError):  # noqa: N818 - see the docstring: this is not a failure
    """A stage was cancelled through its :class:`CancelToken` and did not finish.

    Distinct from an error: nothing is wrong, the caller asked to stop. A
    cancelled stage writes no artefact, so the store never holds a partial
    result (section 5.3.2).
    """


class Progress(Protocol):
    """Called by a running stage with its completion fraction and a message."""

    def __call__(self, fraction: float, message: str) -> None:
        """Report ``fraction`` in [0, 1], monotonically, ending at 1."""


class StageHook(Protocol):
    """Called before each stage of a pipeline walk, with the stage's position.

    The structural counterpart of the ``"stage <name>"`` line
    :func:`~nanopnp.io.run.run_document` reports through :class:`Progress`. Both
    exist because they answer different questions and only one of them can be
    answered honestly by a string: a progress bar wants a fraction and a caption,
    and a caller that has to *act* on the stage — the desktop shell's run panel,
    which shows which stage is running and how many are left — wants the name
    and the position as data.

    Recovering them by parsing the caption would make a display format into an
    interface: the first person to widen it would move the panel without
    touching it. The solve stage's ``on_rung`` callback is the same idea one
    level down.
    """

    def __call__(self, name: str, index: int, total: int) -> None:
        """Report that stage ``index`` of ``total`` (0-based) is about to run."""


class SolveHook(Protocol):
    """Called by the solve with each continuation rung and each Newton step.

    :class:`StageHook` one level down, and for the same reason it exists: the
    residual reaches a :class:`Progress` caller only inside a ``:.3e`` string,
    and a convergence plot's whole subject is six or more orders of that number.
    Recovering it from the caption would make a display format into an
    interface.

    Two methods rather than two hooks, so that threading it through the pipeline
    is one object; and :meth:`rung` always precedes the steps it scopes, which is
    what lets a reader band a series by rung rather than by a running iteration
    count. A rung may report no step at all, and :meth:`rung` says in advance
    whether one is even possible, because the two reasons for the silence are
    different facts and neither is visible from the silence itself.

    Plain scalars only. This module is on the command line's import path, and
    naming :class:`~nanopnp.solve.newton.NewtonStep` here would import NGSolve
    for a type the CLI never constructs.
    """

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        """Report that rung ``index`` of ``total`` (0-based) is about to be solved.

        Parameters
        ----------
        name
            The rung's name, as the ladder and the run record give it.
        stage
            The NUM-18 stage number this rung belongs to; a ramp expands into
            several rungs sharing one.
        index, total
            The rung's position in the ladder, 0-based.
        reporting
            Whether this rung's solve was given a Newton callback at all. NUM-18's
            electrostatic stages are not coupled models and take none, so they
            report no step by construction; a rung that *is* reporting and still
            reports no step converged on entry, before its first step, which is
            the NUM-16 warm-start case and not a missing record. A reader told
            only the silence cannot tell the two apart.
        tolerance
            The relative tolerance this rung is solved to. Both halves of NUM-16's
            disjunctive criterion are measured against it, so a reader holding the
            steps and this number can say what the solver tested rather than
            assuming a default — and can say it without importing the solver to
            read one.
        """

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        """Report one accepted Newton step of the rung most recently announced.

        The fields of :class:`~nanopnp.solve.newton.NewtonStep`, as numbers:
        ``residual`` after the step, ``update`` the relative update on the
        *undamped* direction, and ``forced`` whether NUM-16 accepted the step at
        minimum damping without reducing the residual.
        """


@runtime_checkable
class SolveReporting(Protocol):
    """A stage that can be asked to report its Newton progress (:class:`SolveHook`).

    A capability rather than a parameter on :class:`Stage`. ``progress`` and
    ``cancel`` are on the stage protocol because they are universal; a Newton
    hook is meaningful to exactly one of the twelve stages, and putting it on
    the protocol would add a keyword to eleven signatures that can only ever
    ignore it.

    The hook is **not an input**. A caller rebinds the stage *after* its artefact
    key has been taken, so a run watched from the desktop shell lands on the same
    store entry as the same run from the command line (section 5.3.2).
    """

    def with_solve_hook(self, hook: SolveHook) -> Stage:
        """Return a copy of this stage that reports through ``hook``."""


@runtime_checkable
class CancelToken(Protocol):
    """Asked by a running stage whether the caller has asked it to stop."""

    def cancelled(self) -> bool:
        """Return whether the stage should raise :class:`Cancelled`."""


class CancelFlag:
    """A :class:`CancelToken` a caller sets from another thread.

    The whole implementation: the desktop shell (ADR-004) and the sweep runner
    need something to pass, and a test needs something that turns true at a
    chosen point.
    """

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the running stage to stop at its next check."""
        self._cancelled = True

    def cancelled(self) -> bool:  # noqa: D102 - documented on the protocol
        return self._cancelled


def check_cancelled(cancel: CancelToken | None, where: str) -> None:
    """Raise :class:`Cancelled` if ``cancel`` has been set.

    Parameters
    ----------
    cancel
        The token, or ``None`` when the caller passed none.
    where
        What was about to run, named in the exception so a cancelled run says
        how far it got.

    Raises
    ------
    Cancelled
        If the token reports cancellation.
    """
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
    name
        Registry key, e.g. ``"solve"``.
    number
        Stage number in the section 5.2 pipeline table.
    title
        The stage's name in that table.
    inputs
        Names of the inputs it consumes, as they appear in
        :class:`~nanopnp.io.artefact.StageInputs`.
    outputs
        What the artefact carries, for a caller deciding whether to run it.
    artefact_schema
        Schema identifier of the artefact it emits.
    """

    name: str
    number: int
    title: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    artefact_schema: str

    def summary(self) -> dict[str, Any]:
        """Return this description as plain data, for the CLI and the GUI."""
        return {
            "name": self.name,
            "number": self.number,
            "title": self.title,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "artefact_schema": self.artefact_schema,
        }


class Stage(Protocol):
    """One pipeline stage of section 5.2: typed inputs to a hashed artefact (FR-27)."""

    name: str

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> Artefact:
        """Run the stage and return its artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true before the stage finishes.
        """


@dataclass(frozen=True)
class StageEntry:
    """One registry row: a description, and where the implementation lives."""

    description: StageDescription
    target: str
    """``"module:attribute"``, imported by :func:`create` and by nothing else."""
    extra: str | None = None
    """The optional-dependency extra the implementation needs, or ``None``.

    On the entry and not on :class:`StageDescription`, so the description a
    caller introspects (VER-25) is unchanged by where a stage's dependencies
    come from.
    """


class MissingExtraError(ImportError):
    """A registered stage's implementation needs an extra that is not installed.

    Raised by :func:`create` naming the extra, the module that failed and the
    install command, rather than letting a bare ``ModuleNotFoundError`` for
    ``gemmi`` surface from three imports down. The case is not wrong and no gate
    fired; the installation is, so IF-02 classifies it with the case refusals: a
    retry fails identically until the extra is installed.
    """


_REGISTRY: dict[str, StageEntry] = {}


def register(description: StageDescription, target: str, *, extra: str | None = None) -> None:
    """Register a stage under its name.

    Parameters
    ----------
    description
        Everything introspection needs, held here so that answering a question
        about a stage never imports it.
    target
        ``"module:attribute"`` naming the class implementing the stage.
    extra
        The ``pyproject.toml`` optional-dependency extra the implementation
        imports, named by :func:`create` when it is missing.

    Raises
    ------
    ValueError
        If the name is already registered, or if ``target`` is not of the form
        ``module:attribute``. A silently replaced stage would make two runs with
        the same manifest execute different code.
    """
    if description.name in _REGISTRY:
        raise ValueError(
            f"stage {description.name!r} is already registered as "
            f"{_REGISTRY[description.name].target!r}; replacing it would let two runs share a "
            "manifest and execute different code"
        )
    if target.count(":") != 1:
        raise ValueError(f"stage target {target!r} must be of the form 'module:attribute'")
    _REGISTRY[description.name] = StageEntry(description=description, target=target, extra=extra)


def registered_stages() -> tuple[StageDescription, ...]:
    """Return every registered stage's description, ordered by pipeline number."""
    return tuple(
        sorted(
            (entry.description for entry in _REGISTRY.values()), key=lambda d: (d.number, d.name)
        )
    )


def describe(name: str) -> StageDescription:
    """Return one stage's description without importing its module.

    Raises
    ------
    KeyError
        If no stage is registered under that name; the message lists the ones
        that are.
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        known = ", ".join(sorted(_REGISTRY)) or "none"
        raise KeyError(f"no stage {name!r}; registered stages are {known}")
    return entry.description


def create(name: str, **kwargs: StageOption) -> Stage:
    """Import a stage's module and construct it.

    The only function here that imports anything. Everything else — listing
    stages, describing one, deciding whether to run it — is answered from the
    registry, which is what keeps ``import nanopnp.cli`` free of NGSolve.

    Parameters
    ----------
    name
        Registered stage name.
    **kwargs
        Passed to the stage's constructor.

    Raises
    ------
    KeyError
        If no stage is registered under that name.
    MissingExtraError
        If the stage declares an extra and importing its module fails on a
        module outside this package, naming the extra, the missing module and
        the install command.
    """
    describe(name)  # raises the diagnostic naming the registered stages
    entry = _REGISTRY[name]
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
    """Register the stages this release implements.

    The descriptions live here rather than beside each stage class precisely
    because they must be readable without importing it; each stage's
    ``describe()`` returns its registry entry, and a Tier-1 test asserts the two
    cannot drift apart.
    """
    register(
        StageDescription(
            name="structure",
            number=1,
            title="Structure ingestion and alignment",
            inputs=("case",),
            outputs=("aligned ensemble", "Cn axis on z at r = 0", "symmetry-gate record"),
            artefact_schema="nanopnp/structure/v1",
        ),
        "nanopnp.structure.stage:StructureStage",
        extra="structure",
    )
    register(
        StageDescription(
            name="density",
            number=2,
            title="Density map",
            inputs=("case", "structure"),
            outputs=("ensemble-mean union density on a canonical 3D grid", "radius-set record"),
            artefact_schema="nanopnp/density/v1",
        ),
        "nanopnp.density.stage:DensityStage",
    )
    register(
        StageDescription(
            name="symmetry",
            number=3,
            title="Symmetry reduction to (r, z)",
            inputs=("case", "density"),
            outputs=("(r, z) mean", "Cn-averaged and raw azimuthal variance"),
            artefact_schema="nanopnp/reduced/v1",
        ),
        "nanopnp.symmetry.stage:SymmetryStage",
    )
    register(
        StageDescription(
            name="contour",
            number=4,
            title="Contour extraction and conditioning",
            inputs=("case", "structure", "symmetry"),
            outputs=(
                "conditioned closed polyline, a nanopnp/profile/v1 document",
                "conditioning and gate record",
                "probe-radius profile",
            ),
            artefact_schema="nanopnp/profile/v1",
        ),
        "nanopnp.geometry.contour:ContourStage",
        extra="structure",
    )
    register(
        StageDescription(
            name="region",
            number=5,
            title="CAD assembly",
            inputs=("case", "contour"),
            outputs=(
                "tagged (r, z) region, a nanopnp/region/v1 record",
                "membrane inner edge and junction-gate record",
            ),
            artefact_schema="nanopnp/region/v1",
        ),
        "nanopnp.geometry.region:RegionStage",
    )
    register(
        StageDescription(
            name="mesh",
            number=6,
            title="Mesh",
            inputs=("case", "region"),
            outputs=("tagged mesh", "element-quality report", "size-field record"),
            artefact_schema="nanopnp/mesh/v1",
        ),
        "nanopnp.mesh.ingest:MeshStage",
    )
    register(
        StageDescription(
            name="charge",
            number=7,
            title="Charge assembly",
            inputs=("case", "mesh"),
            outputs=(
                "fixed-charge field",
                "dielectric solid fraction",
                "charge-conservation report",
            ),
            artefact_schema="nanopnp/fields/v1",
        ),
        "nanopnp.charge.stage:FieldStage",
    )
    register(
        StageDescription(
            name="materials",
            number=8,
            title="Materials",
            inputs=("case",),
            outputs=("electrolyte", "correction models", "resolved coefficient set"),
            artefact_schema="nanopnp/materials/v1",
        ),
        "nanopnp.materials.stage:MaterialsStage",
    )
    register(
        StageDescription(
            name="case",
            number=9,
            title="Case assembly",
            inputs=("case_path",),
            outputs=("resolved case document",),
            artefact_schema="nanopnp/case/v2",
        ),
        "nanopnp.io.case:CaseStage",
    )
    register(
        StageDescription(
            name="solve",
            number=10,
            title="Solve",
            inputs=("case", "materials", "mesh"),
            outputs=("converged fields", "iteration history"),
            artefact_schema="nanopnp/solution/v2",
        ),
        "nanopnp.solve.stage:SolveStage",
    )
    register(
        StageDescription(
            name="qoi",
            number=11,
            title="Quantities of interest",
            inputs=("case", "solve"),
            outputs=("scalar quantities of interest", "route-agreement record"),
            artefact_schema="nanopnp/qoi/v1",
        ),
        "nanopnp.post.stage:QoIStage",
    )
    register(
        StageDescription(
            name="report",
            number=12,
            title="Report",
            inputs=("case", "qoi", "solve"),
            outputs=("field export", "run record"),
            artefact_schema="nanopnp/report/v1",
        ),
        "nanopnp.post.stage:ReportStage",
    )


_register_builtins()


def _catalogue() -> Mapping[str, StageEntry]:
    """Return the registry itself, for tests that need the target strings."""
    return _REGISTRY
