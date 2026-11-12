"""A molecular model in the workbench: the prepared structure and its protonation, built alone."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from nanopnp.gui.web.builds import REFUSED, BuiltModel
from nanopnp.io.case import Membrane
from nanopnp.io.models import ModelKind

__all__ = ["STAGES", "MolecularModel"]

STAGES: tuple[str, ...] = ("structure", "protonation")
"""The stages a molecular model is built of, in the order the walk runs them."""


@dataclass
class MolecularModel(BuiltModel):
    """One molecular model of a project: each stage's state, its build and what it built."""

    kind: ClassVar[ModelKind] = "molecular"
    stages: ClassVar[tuple[str, ...]] = STAGES
    paths: ClassVar[re.Pattern[str]] = re.compile(r"\b(?:structure|charge)(?:\.[a-z_]+)+")
    gate_paths: ClassVar[tuple[tuple[str, str], ...]] = (
        ("axis: z", "structure.symmetry.axis"),
        ("displacement gate", "structure.symmetry.axis"),
        ("channel", "structure.symmetry.axis"),
        ("expects", "structure.symmetry.point_group"),
    )

    def membrane(self) -> tuple[Membrane, str | None]:
        """Return the membrane of the first study that names this model, and that study.

        The membrane is the continuum model's, in the prepared structure's frame; where no study
        names this model, it is the schema's default and the study is None.
        """
        mine = self.project.path("molecular", self.name).resolve()
        for study in self.project.items("study"):
            try:
                case = self.project.study(study)
            except REFUSED:
                continue
            record = case.models_record
            if record is None or case.geometry is None:
                continue
            if any(f.kind == "molecular" and f.path.resolve() == mine for f in record.files):
                return case.geometry.membrane, study
        return Membrane(), None

    def pqr(self) -> Path | None:
        """Return the PQR file the model reads its atoms and charges from, or None."""
        case = self.case()
        if case is None or case.inputs.pqr is None or case.inputs.pqr.path is None:
            return None
        return Path(case.inputs.pqr.path)

    def has_structure(self) -> bool:
        """Say whether the model names a structure, which stage 1 reads; a PQR model names none."""
        case = self.case()
        return case is not None and case.structure is not None
