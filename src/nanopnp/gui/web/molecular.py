"""A molecular model in the workbench: what the store holds of it, and the walk that builds it."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from nanopnp.api.case import Case
from nanopnp.api.project import BUILD_UPTO, Problem, Project
from nanopnp.core.stages import describe
from nanopnp.gui.solver import Cancelled, Failed, Finished, RunRequest, SolverProcess, Stage
from nanopnp.gui.web.queue import Entry, Queue
from nanopnp.io.artefact import Artefact
from nanopnp.io.project import STORE_FOLDER
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk, selected_stages

__all__ = ["STAGES", "MolecularModel", "StageState", "cancel_builds"]

StageState = Literal["empty", "building", "built", "refused"]

STAGES: tuple[str, ...] = ("structure", "protonation")
"""The stages a molecular model is built of, in the order the walk runs them."""

_REFUSED = (ValueError, KeyError, OSError)


@dataclass
class _Build:
    process: SolverProcess
    entry: Entry
    folder: Path
    upto: str
    stage: str = STAGES[0]


@dataclass
class _Held:
    build: _Build | None = None
    refusal: tuple[str, str] | None = None
    """The stage the last build was refused at, and what it said."""


_MODELS: dict[tuple[Path, str], _Held] = {}
_CASE_PATH = re.compile(r"\b(?:structure|charge)(?:\.[a-z_]+)+")
_GATE_PATHS = (
    ("axis: z", "structure.symmetry.axis"),
    ("displacement gate", "structure.symmetry.axis"),
    ("channel", "structure.symmetry.axis"),
    ("expects", "structure.symmetry.point_group"),
)


def refused_path(message: str) -> str | None:
    """Return the case path a refusal names, or None where it names none."""
    found = _CASE_PATH.search(message)
    if found is not None:
        return found.group(0)
    # A gate of stage 1 words its rule and not its path; each belongs to one value.
    for words, path in _GATE_PATHS:
        if words in message:
            return path
    return None


def refusals(project: Project) -> tuple[Problem, ...]:
    """Return the last build's refusal of each molecular model of a project, as its problems."""
    return tuple(
        Problem(f"molecular/{name}", refused_path(held.refusal[1]), held.refusal[1], "molecular")
        for (root, name), held in _MODELS.items()
        if root == project.root and held.refusal is not None
    )


def cancel_builds() -> None:
    """Cancel every build a window started, as the server does when it stops."""
    for held in _MODELS.values():
        if held.build is not None and held.build.process.running:
            held.build.process.cancel()


@dataclass
class MolecularModel:
    """One molecular model of a project: each stage's state, its build and what it built.

    Parameters
    ----------
    queue
        The window's queue, which a build is entered in.
    """

    project: Project
    name: str
    queue: Queue = field(default_factory=Queue)

    @property
    def _held(self) -> _Held:
        return _MODELS.setdefault((self.project.root, self.name), _Held())

    def case(self) -> Case | None:
        """Return the case that builds the model alone, or None where its file forms none."""
        try:
            return self.project.build_case("molecular", self.name)
        except _REFUSED:
            return None

    def problem(self) -> str | None:
        """Return why the model's file forms no case, or None where it does."""
        try:
            self.project.build_case("molecular", self.name)
        except _REFUSED as error:
            return str(error).replace(f"{self.project.root}/", "")
        return None

    def has_structure(self) -> bool:
        """Say whether the model names a structure, which stage 1 reads; a PQR model names none."""
        case = self.case()
        return case is not None and case.structure is not None

    def artefacts(self) -> dict[str, Artefact]:
        """Return the stages of ``STAGES`` the store holds for the model as it is now."""
        case = self.case()
        if case is None:
            return {}
        store = self.project.session().store
        try:
            resolved = resolve(case, base=case.source.base)
            identities = keyed_walk(resolved, store=store, planned=set())
            wanted = selected_stages(resolved, BUILD_UPTO["molecular"])
        except _REFUSED:
            return {}
        found: dict[str, Artefact] = {}
        for stage in STAGES:
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
        if held.build is None or not build.process.running:
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
        """Return each stage's state: built from the store, else building, refused or empty.

        A stage after a refused one is empty: it was not reached.
        """
        self.poll()
        held = self._held
        stored = self.artefacts()
        found: dict[str, StageState] = {}
        for index, stage in enumerate(STAGES):
            if stage in stored:
                found[stage] = "built"
            elif held.build is not None and index <= STAGES.index(held.build.upto):
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
        case = self.project.build_case("molecular", self.name)
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
        entry = self.queue.add(f"{self.name} to {upto}", "running")
        held.refusal = None
        held.build = _Build(process, entry, folder, upto)
        process.start()

    def cancel(self) -> None:
        """Ask a running build to stop at its next check."""
        build = self._held.build
        if build is not None:
            build.process.cancel()
