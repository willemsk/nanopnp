"""A study in the workbench: its walk to the charge and its run records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml

from nanopnp.core.stages import walk_order
from nanopnp.gui.solver import RunRequest
from nanopnp.gui.web.builds import REFUSED, BuiltModel
from nanopnp.io.project import RUNS_FOLDER, STORE_FOLDER, ItemKind
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.case import Case
    from nanopnp.io.resolved import ResolvedCase

__all__ = ["STAGES", "StudyModel", "charge_record", "reached"]

_ORDER = walk_order()
STAGES: tuple[str, ...] = _ORDER[_ORDER.index("structure") : _ORDER.index("charge") + 1]
"""The stages a study's build walks, stages 1 to 7, in the order the walk runs them."""


def _record(directory: Path) -> dict[str, Any]:
    try:
        found = json.loads((directory / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def reached(directory: Path) -> tuple[str, ...]:
    """Return the stages a run record lists, in walk order."""
    stages = _record(directory).get("stages")
    if not isinstance(stages, list):
        return ()
    return tuple(str(entry.get("stage")) for entry in stages if isinstance(entry, dict))


def charge_record(directory: Path) -> str | None:
    """Return the hash of the charge a run record names, or None where it reached no charge."""
    artefacts = _record(directory).get("artefacts")
    charge = artefacts.get("charge") if isinstance(artefacts, dict) else None
    found = charge.get("hash") if isinstance(charge, dict) else None
    return str(found) if found else None


@dataclass
class StudyModel(BuiltModel):
    """One study of a project: its stages 1 to 7, its build to the charge and its run records.

    The build writes its run record into ``runs/<study>/``.
    """

    kind: ClassVar[ItemKind] = "study"
    stages: ClassVar[tuple[str, ...]] = STAGES
    upto: ClassVar[str] = "charge"
    paths: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:structure|charge|geometry|electrolyte|boundary_conditions|physics|numerics|"
        r"models|outputs|variables|inputs)(?:\.[A-Za-z0-9_]+)+"
    )

    def body(self) -> dict[str, Any]:
        """Return the study file's own values, or none where it does not load."""
        try:
            raw = yaml.safe_load(self.project.path("study", self.name).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _built_case(self) -> Case | str:
        try:
            return self.project.study(self.name)
        except REFUSED as error:
            return str(error).replace(f"{self.project.root}/", "")

    def request(self, case: Path, upto: str) -> RunRequest:
        """Return the walk of the study's own file to a stage, its run record written."""
        return RunRequest(
            case=str(self.project.path("study", self.name)),
            store=str(self.project.root / STORE_FOLDER),
            upto=upto,
            runs=str(self.project.root / RUNS_FOLDER),
        )

    def resolved(self) -> ResolvedCase | None:
        """Return the study resolved, or None where it does not resolve."""
        return self._once("resolved", self._resolved)

    def _resolved(self) -> ResolvedCase | None:
        case = self.case()
        if case is None:
            return None
        try:
            return resolve(case, base=case.source.base)
        except REFUSED:
            return None

    # -- the run records ------------------------------------------------------------------

    def records(self) -> tuple[Path, ...]:
        """Return the study's run directories, the newest first."""
        found = self.project.runs(self.name)
        return tuple(sorted(found, key=lambda d: (d / RUN_RECORD_FILENAME).stat().st_mtime)[::-1])

    def runs(self) -> tuple[Path, ...]:
        """Return the records of the runs that reached their quantities, the newest first."""
        return tuple(d for d in self.records() if "qoi" in reached(d))
