"""A physics model in the workbench: the study it is shown in, and the case it runs there."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml

from nanopnp.gui.web.builds import REFUSED, BuiltModel, StageState
from nanopnp.io.case_paths import schema_default
from nanopnp.io.models import ModelKind, leaves, owner_of
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.case import Case
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.resolved import ResolvedCase

__all__ = ["PhysicsModel"]


@dataclass
class PhysicsModel(BuiltModel):
    """One physics model of a project, shown inside a study: it builds nothing alone.

    Parameters
    ----------
    shown_in
        The study the window shows the model in, or None for the one ``within`` picks.
    """

    shown_in: str | None = None

    kind: ClassVar[ModelKind] = "physics"
    stages: ClassVar[tuple[str, ...]] = ()
    paths: ClassVar[re.Pattern[str]] = re.compile(
        # A bare "physics", as in "physics model", names no value.
        r"\b(?:(?:physics|electrolyte|boundary_conditions)(?=\.[a-z_])|"
        r"numerics\.(?:elements|stabilisation|wall_distance))(?:\.[A-Za-z0-9_]+)*"
    )

    def within(self) -> str | None:
        """Return the study the model is shown in, or None where the project holds no study.

        It is ``shown_in`` while that names a study; else the first study that names this
        model; else the project's first study.
        """
        return self._once("within", self._within)

    def _within(self) -> str | None:
        studies = self.project.items("study")
        if self.shown_in in studies:
            return self.shown_in
        target = self.project.path(self.kind, self.name).resolve()
        for study in studies:
            location = self.project.path("study", study)
            named = _read(location).get("models")
            physics = named.get("physics") if isinstance(named, dict) else None
            if isinstance(physics, str) and (location.parent / physics).resolve() == target:
                return study
        return studies[0] if studies else None

    def _built_case(self) -> Case | str:
        study = self.within()
        root = f"{self.project.root}/"
        try:
            case = self.project.physics_case(self.name, study)
            # A study refuses a model its own values cannot run with once it resolves, and its
            # stages' checks, such as a mesh's solids against the permittivities, once it keys.
            resolved = resolve(case, base=case.source.base)
            keyed_walk(resolved, store=self.project.session().store, planned=set())
        except REFUSED as error:
            # The case's own label, such as "<study S with physics model P>", names what the
            # prefix says.
            said = re.sub(r"^<[^<>]*>:\s*", "", str(error).replace(root, ""))
            return said if study is None else f"In study {study}: {said}"
        return case

    def resolved(self) -> ResolvedCase | None:
        """Return the shown case resolved, or None where the study refuses the model."""
        return self._once("resolved", self._resolved)

    def _resolved(self) -> ResolvedCase | None:
        case = self.case()
        if case is None:
            return None
        try:
            return resolve(case, base=case.source.base)
        except REFUSED:
            return None

    def refused_path(self, message: str) -> str | None:
        """Return the case path a refusal names: a value the model's choice refuses, else any."""
        found = [match.group(0) for match in self.paths.finditer(message)]
        # A refusal of the model's switch names the model and the switch: the switch is the
        # field to change, as Undo or another model is the other way out.
        return next((path for path in found if path != "physics.model"), None) or (
            found[0] if found else None
        )

    def study_values(self) -> dict[str, Any]:
        """Return the shown study's own values of the model's keys, which the shown case leaves out.

        Each is keyed by its dotted leaf path, as the study's file writes it.
        """
        return dict(self._once("study_values", self._study_values))

    def _study_values(self) -> dict[str, Any]:
        study = self.within()
        if study is None:
            return {}
        body = _read(self.project.path("study", study))
        return {path: value for path, value in leaves(body) if owner_of(path) == self.kind}

    def shown(self, path: str) -> Any:  # noqa: ANN401 - whatever the field holds
        """Return the value the model gives a path: its own, else the schema's default, or None."""
        cursor: Any = self._once("body", self.body)
        for part in path.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                cursor = None
                break
            cursor = cursor[part]
        if cursor is not None:
            return cursor
        try:
            has_default, default = schema_default(path)
        except KeyError:
            return None
        return default if has_default else None

    def walked(self) -> tuple[str, ...]:
        """Return no stage: a physics model is built by the studies that name it."""
        return ()

    def artefacts(self) -> dict[str, Artefact]:
        """Return nothing: no stage is the physics model's alone."""
        return {}

    def states(self) -> dict[str, StageState]:
        """Return no stage's state: the suite builds nothing."""
        return {}


def _read(location: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(location.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return raw if isinstance(raw, dict) else {}
