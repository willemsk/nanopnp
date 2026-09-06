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
anything.
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


_REGISTRY: dict[str, StageEntry] = {}


def register(description: StageDescription, target: str) -> None:
    """Register a stage under its name.

    Parameters
    ----------
    description
        Everything introspection needs, held here so that answering a question
        about a stage never imports it.
    target
        ``"module:attribute"`` naming the class implementing the stage.

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
    _REGISTRY[description.name] = StageEntry(description=description, target=target)


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
    """
    describe(name)  # raises the diagnostic naming the registered stages
    entry = _REGISTRY[name]
    module_name, _, attribute = entry.target.partition(":")
    module = importlib.import_module(module_name)
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
            name="mesh",
            number=6,
            title="Mesh",
            inputs=("case",),
            outputs=("tagged mesh", "element-quality report"),
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
            artefact_schema="nanopnp/case/v1",
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
            artefact_schema="nanopnp/solution/v1",
        ),
        "nanopnp.solve.stage:SolveStage",
    )


_register_builtins()


def _catalogue() -> Mapping[str, StageEntry]:
    """Return the registry itself, for tests that need the target strings."""
    return _REGISTRY
