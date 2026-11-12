"""A continuum model in the workbench: the protein geometry, the region and the mesh it builds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from nanopnp.gui.web.builds import REFUSED, BuiltModel
from nanopnp.io.models import ModelKind, read_model_file

__all__ = ["OWN_OUTLINE", "STAGES", "ContinuumModel"]

STAGES: tuple[str, ...] = ("density", "symmetry", "contour", "region", "mesh")
"""The stages a continuum model is built of, in the order the walk runs them."""

OWN_OUTLINE: tuple[str, ...] = ("geometry.pore", "inputs.profile", "inputs.mesh")
"""The values with which a continuum model draws its own pore, and reads no molecular model."""


def _holds(body: Any, path: str) -> bool:  # noqa: ANN401 - a parsed YAML body
    cursor = body
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return False
        cursor = cursor[part]
    return cursor is not None


@dataclass
class ContinuumModel(BuiltModel):
    """One continuum model of a project: each stage's state, its build and what it built."""

    kind: ClassVar[ModelKind] = "continuum"
    stages: ClassVar[tuple[str, ...]] = STAGES
    paths: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:geometry|numerics\.mesh|inputs\.profile|inputs\.mesh|charge\.exclusion_offset_nm)"
        r"(?:\.[a-z_]+)*"
    )

    def body(self) -> dict[str, Any]:
        """Return the model file's own values, or none where it does not load."""
        try:
            location = self.project.path(self.kind, self.name)
            return dict(read_model_file(self.kind, location, rebase=False).body)
        except REFUSED:
            return {}

    def own_outline(self) -> str | None:
        """Return the value with which the model draws its own pore, or None where it has none."""
        body = self.body()
        return next((path for path in OWN_OUTLINE if _holds(body, path)), None)

    def molecular(self) -> str | None:
        """Return the molecular model the model is built over, or None where it reads none."""
        if self.own_outline() is not None:
            return None
        return self.project.molecular_for(self.name)

    def pair(self, molecular: str | None) -> None:
        """Build the model over a molecular model from now on; None returns to the default one.

        Raises
        ------
        ProjectError
            If the project holds no such molecular model.
        """
        self.project.set_built_with(self.name, molecular)

    def profile(self) -> Path | None:
        """Return the outline file the model supplies as ``inputs.profile``, or None."""
        case = self.case()
        if case is None or case.inputs.profile is None or case.inputs.profile.path is None:
            return None
        return Path(case.inputs.profile.path)
