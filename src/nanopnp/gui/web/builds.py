"""A model built alone in the workbench: what the store holds of it, and the walk that builds it."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

from nanopnp.api.project import BUILD_UPTO, Problem, Project
from nanopnp.core.stages import describe
from nanopnp.gui.solver import Cancelled, Failed, Finished, RunRequest, SolverProcess, Stage
from nanopnp.gui.web.queue import Entry, Queue
from nanopnp.io.project import ITEM_SUITES, STORE_FOLDER
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk, selected_stages

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.case import Case
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.models import ModelKind

__all__ = ["BuiltModel", "StageState", "ToolModel", "cancel_builds", "refusals"]

StageState = Literal["empty", "building", "built", "refused"]

REFUSED = (ValueError, KeyError, OSError)
"""What a model's file or its case raises where it forms no case to build."""


@dataclass
class _Build:
    process: SolverProcess
    entry: Entry
    folder: Path
    upto: str
    stage: str


@dataclass
class _Held:
    build: _Build | None = None
    refusal: tuple[str, str] | None = None
    """The stage the last build was refused at, and what it said."""


# Each model's build and refusal outlive a window: keyed by project, kind and name.
_MODELS: dict[tuple[Path, str, str], _Held] = {}
_KINDS: dict[str, type[BuiltModel]] = {}


class ToolModel(Protocol):
    """What a suite's tools ask of the model they build: its stages' states and its build."""

    kind: ModelKind
    name: str
    project: Project

    def states(self) -> dict[str, StageState]:
        """Return each of the model's stages the walk runs, and its state."""

    def build(self, upto: str) -> None:
        """Start the walk that builds the model up to a stage, unless one is running."""

    def cancel(self) -> None:
        """Ask a running build to stop at its next check."""

    def refusal(self) -> tuple[str, str] | None:
        """Return the stage the last build was refused at and its message, or None."""

    def problem(self) -> str | None:
        """Return why the model's file forms no case, or None where it does."""

    def running_stage(self) -> str | None:
        """Return the stage a running build is at, or None where none runs."""

    def dismiss(self) -> None:
        """Forget the last build's refusal, as a value's change does."""

    def refused_path(self, message: str) -> str | None:
        """Return the case path a refusal names, or None where it names none."""


def refusals(project: Project) -> tuple[Problem, ...]:
    """Return the last build's refusal of each model of a project, as its problems."""
    found = []
    for (root, kind, name), held in _MODELS.items():
        if root != project.root or held.refusal is None:
            continue
        model = _KINDS[kind](project, name)
        path = model.refused_path(held.refusal[1])
        found.append(Problem(f"{kind}/{name}", path, held.refusal[1], ITEM_SUITES[model.kind]))
    return tuple(found)


def cancel_builds() -> None:
    """Cancel every build a window started, as the server does when it stops."""
    for held in _MODELS.values():
        if held.build is not None and held.build.process.running:
            held.build.process.cancel()


@dataclass
class BuiltModel:
    """A model its suite builds alone: each stage's state, its build and what it built.

    Parameters
    ----------
    queue
        The window's queue, which a build is entered in.
    """

    project: Project
    name: str
    queue: Queue = field(default_factory=Queue)

    kind: ClassVar[ModelKind]
    stages: ClassVar[tuple[str, ...]]
    """The model's own stages, in the order the walk runs them."""
    paths: ClassVar[re.Pattern[str]]
    """The case paths of the model's own values, as a refusal names them."""
    gate_paths: ClassVar[tuple[tuple[str, str], ...]] = ()
    """The words a gate's refusal says, and the value each belongs to, where it names no path."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        _KINDS[cls.kind] = cls

    @property
    def _held(self) -> _Held:
        return _MODELS.setdefault((self.project.root, self.kind, self.name), _Held())

    def case(self) -> Case | None:
        """Return the case that builds the model alone, or None where its file forms none."""
        try:
            return self.project.build_case(self.kind, self.name)
        except REFUSED:
            return None

    def problem(self) -> str | None:
        """Return why the model's file forms no case, or None where it does."""
        try:
            self.project.build_case(self.kind, self.name)
        except REFUSED as error:
            return str(error).replace(f"{self.project.root}/", "")
        return None

    def refused_path(self, message: str) -> str | None:
        """Return the case path a refusal names, or None where it names none."""
        found = self.paths.search(message)
        if found is not None:
            return found.group(0)
        # A gate words its rule and not its path; each belongs to one value.
        for words, path in self.gate_paths:
            if words in message:
                return path
        return None

    def walked(self) -> tuple[str, ...]:
        """Return the model's own stages its build walks: a supplied input drops some."""
        case = self.case()
        if case is None:
            return self.stages
        try:
            wanted = selected_stages(resolve(case, base=case.source.base), BUILD_UPTO[self.kind])
        except REFUSED:
            return self.stages
        return tuple(stage for stage in self.stages if stage in wanted)

    def artefacts(self) -> dict[str, Artefact]:
        """Return the model's own stages the store holds for the model as it is now."""
        case = self.case()
        if case is None:
            return {}
        store = self.project.session().store
        try:
            resolved = resolve(case, base=case.source.base)
            identities = keyed_walk(resolved, store=store, planned=set())
            wanted = selected_stages(resolved, BUILD_UPTO[self.kind])
        except REFUSED:
            return {}
        found: dict[str, Artefact] = {}
        for stage in self.stages:
            if stage not in wanted or stage not in identities or identities[stage].built:
                continue
            stored = store.get(describe(stage).artefact_schema, identities[stage].hash)
            if stored is not None:
                found[stage] = stored
        return found

    def poll(self) -> None:
        """Read what a running build has said: its stage, its end, and a refusal."""
        held = self._held
        build = held.build
        if build is None:
            return
        # Read before the drain: a child that ended by then has posted its last word, which the
        # drain reads, where one ending after the drain would be taken for one that said nothing.
        ended = not build.process.running
        for event in build.process.drain():
            if isinstance(event, Stage):
                build.stage = event.name
            elif isinstance(event, Finished):
                self.queue.set(build.entry, "done")
                held.build = None
            elif isinstance(event, Failed):
                held.refusal = (build.stage, event.message.replace(f"{self.project.root}/", ""))
                self.queue.set(build.entry, "failed")
                held.build = None
            elif isinstance(event, Cancelled):
                self.queue.set(build.entry, "failed")
                self.queue.log.append(f"cancelled {build.entry.label}")
                held.build = None
        if held.build is None or ended:
            if held.build is not None:
                # The child ended without a last word, as a killed one does.
                held.refusal = (build.stage, "the build stopped before it finished")
                self.queue.set(build.entry, "failed")
                held.build = None
            shutil.rmtree(build.folder, ignore_errors=True)

    @property
    def building(self) -> bool:
        """Whether a build of the model is running."""
        self.poll()
        return self._held.build is not None

    def running_stage(self) -> str | None:
        """Return the stage a running build is at, or None where none runs."""
        self.poll()
        build = self._held.build
        return None if build is None else build.stage

    def dismiss(self) -> None:
        """Forget the last build's refusal, as a value's change does."""
        self._held.refusal = None

    def refusal(self) -> tuple[str, str] | None:
        """Return the stage the last build was refused at and its message, or None."""
        self.poll()
        return self._held.refusal

    def states(self) -> dict[str, StageState]:
        """Return each stage the build walks: built from the store, else building, refused or empty.

        A stage after a refused one is empty: it was not reached.
        """
        self.poll()
        held = self._held
        stored = self.artefacts()
        walked = self.walked()
        found: dict[str, StageState] = {}
        for index, stage in enumerate(self.stages):
            if stage not in walked:
                continue
            if stage in stored:
                found[stage] = "built"
            elif held.build is not None and index <= self.stages.index(held.build.upto):
                found[stage] = "building"
            elif held.refusal is not None and stage == held.refusal[0]:
                found[stage] = "refused"
            else:
                found[stage] = "empty"
        return found

    def build(self, upto: str) -> None:
        """Start the walk that builds the model up to a stage, unless one is running.

        The walk runs in a child process, writes no run directory, and reads the case from a
        temporary folder that is removed when it ends.
        """
        held = self._held
        self.poll()
        if held.build is not None:
            return
        case = self.project.build_case(self.kind, self.name)
        folder = Path(tempfile.mkdtemp(prefix="nanopnp-build-"))
        written = folder / f"{self.name}.case.yaml"
        written.write_text(case.dumps(), encoding="utf-8")
        process = SolverProcess(
            RunRequest(
                case=str(written),
                store=str(self.project.root / STORE_FOLDER),
                upto=upto,
                write=False,
            )
        )
        entry = self.queue.add(f"{self.name} to {upto}", "running", suite=self.kind)
        held.refusal = None
        held.build = _Build(process, entry, folder, upto, self.stages[0])
        process.start()

    def cancel(self) -> None:
        """Ask a running build to stop at its next check."""
        build = self._held.build
        if build is not None:
            build.process.cancel()
