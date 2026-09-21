"""The Qt half of the shell: widgets over the view-models, and no logic of its own.

Everything here imports PySide6, and nothing here decides anything. What a field
admits, whether a value is acceptable, what a run is doing and what it produced
are all answered by :mod:`nanopnp.gui.case_model`, :mod:`nanopnp.gui.solver` and
:mod:`nanopnp.gui.run_model`, which import no Qt at all. That split is not
tidiness: ``PySide6.QtWidgets`` does not import on the Linux push gate
(`.knowledge/07-software-stack.md` §5), so a rule implemented in this package
would be a rule tested on two of the seven matrix jobs.

It is also the rule the command line states for itself (``nanopnp.cli``): the
shells hold no physics, and the interface is thin over the stage objects
(§5.1, IF-09).
"""

from __future__ import annotations

from nanopnp.gui.widgets.case_editor import CaseEditorWidget
from nanopnp.gui.widgets.convergence import ConvergenceWidget
from nanopnp.gui.widgets.result import ResultWidget
from nanopnp.gui.widgets.run_control import RunControlWidget
from nanopnp.gui.widgets.viewer import ViewerWidget

__all__ = [
    "CaseEditorWidget",
    "ConvergenceWidget",
    "ResultWidget",
    "RunControlWidget",
    "ViewerWidget",
]
