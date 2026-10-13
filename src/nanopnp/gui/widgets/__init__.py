"""The Qt half of the shell: widgets over the view-models, and no logic of its own."""

from __future__ import annotations

from nanopnp.gui.widgets.case_editor import CaseEditorWidget
from nanopnp.gui.widgets.charge import ChargeWidget
from nanopnp.gui.widgets.convergence import ConvergenceWidget
from nanopnp.gui.widgets.geometry import GeometryWidget
from nanopnp.gui.widgets.result import ResultWidget
from nanopnp.gui.widgets.run_control import RunControlWidget
from nanopnp.gui.widgets.viewer import ViewerWidget

__all__ = [
    "CaseEditorWidget",
    "ChargeWidget",
    "ConvergenceWidget",
    "GeometryWidget",
    "ResultWidget",
    "RunControlWidget",
    "ViewerWidget",
]
