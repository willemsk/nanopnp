"""A continuum model in the workbench: the protein geometry, the region and the mesh it builds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from nanopnp.api.project import own_outline
from nanopnp.geometry.profile import PAYLOAD_NAME as PROFILE_PAYLOAD
from nanopnp.geometry.profile import PoreProfile, load_profile
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.web.builds import BuiltModel
from nanopnp.io.case import PROFILE_FORMAT
from nanopnp.io.models import ModelKind
from nanopnp.io.project import INPUTS_FOLDER

__all__ = ["STAGES", "ContinuumModel"]

STAGES: tuple[str, ...] = ("density", "symmetry", "contour", "region", "mesh")
"""The stages a continuum model is built of, in the order the walk runs them."""


# A hand edit of each model's outline, kept for the server's life until it is saved or dropped.
_EDITS: dict[tuple[Path, str], ProfileEditor] = {}


@dataclass
class ContinuumModel(BuiltModel):
    """One continuum model of a project: each stage's state, its build and what it built."""

    kind: ClassVar[ModelKind] = "continuum"
    stages: ClassVar[tuple[str, ...]] = STAGES
    paths: ClassVar[re.Pattern[str]] = re.compile(
        # A bare "geometry", as in "a geometry: section" or "element geometry", names no value.
        r"\b(?:geometry(?=\.[a-z_])|numerics\.mesh|inputs\.profile|inputs\.mesh|"
        r"charge\.exclusion_offset_nm)(?:\.[a-z_]+)*"
    )
    gate_paths: ClassVar[tuple[tuple[str, str], ...]] = (
        ("stage 4 contour gate", "geometry.contour.isolevel"),
    )

    def own_outline(self) -> str | None:
        """Return the value with which the model draws its own pore, or None where it has none."""
        return own_outline(self.body())

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

    def outline(self) -> PoreProfile | None:
        """Return the outline an edit starts from: stage 4's as built, else the supplied one."""
        held = self.artefacts()
        if "contour" in held:
            return load_profile(held["contour"].payload[PROFILE_PAYLOAD])
        path = self.profile()
        if path is None or not path.is_file():
            return None
        return load_profile(path)

    def editor(self) -> ProfileEditor | None:
        """Return the hand edit of the model's outline held now, or None."""
        return _EDITS.get((self.project.root, self.name))

    def start_edit(self) -> ProfileEditor:
        """Start a hand edit of the model's outline, or return the one held.

        Raises
        ------
        ValueError
            If the model has no outline to edit: none built, none supplied.
        """
        key = (self.project.root, self.name)
        if key not in _EDITS:
            outline = self.outline()
            if outline is None:
                raise ValueError(
                    f"continuum model {self.name!r} has no outline to edit: build its geometry, "
                    "or supply one as inputs.profile"
                )
            _EDITS[key] = ProfileEditor.from_profile(outline)
        return _EDITS[key]

    def hold_edit(self, editor: ProfileEditor) -> None:
        """Hold an edit started elsewhere, as from a seed of a refused loop."""
        _EDITS[(self.project.root, self.name)] = editor

    def drop_edit(self) -> None:
        """Forget the hand edit held, unsaved."""
        _EDITS.pop((self.project.root, self.name), None)

    def save_edit(self, name: str) -> Path:
        """Save the hand edit as a new continuum model that supplies it; return the model's file.

        The outline is written to the project's inputs, named by its digest; the new model is
        this one's values with the outline as ``inputs.profile`` and stages 2 to 4's values
        removed, so a study runs it with its molecular model's structure and charge.

        Raises
        ------
        ValueError
            If no edit is held, the loop would not load, or the new model is refused.
        """
        editor = self.editor()
        if editor is None:
            raise ValueError(f"continuum model {self.name!r} holds no edit to save")
        folder = self.project.root / INPUTS_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        held = {path.name for path in folder.iterdir()}
        written = editor.save(folder)
        value = {"path": self.project.input_path(self.kind, written), "format": PROFILE_FORMAT}
        try:
            location = self.project.derive_model(
                "continuum",
                self.name,
                name,
                {"inputs.profile": value, "geometry.density": None, "geometry.contour": None},
            )
        except Exception:
            # The outline is named by its digest, so a file the folder held before is another
            # model's and stays.
            if written.name not in held:
                written.unlink(missing_ok=True)
            raise
        self.drop_edit()
        return location
