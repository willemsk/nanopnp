"""The desktop shell (IF-09): a window over the view-models, and nothing more."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from PySide6 import QtCore, QtGui, QtWidgets

from nanopnp.core.errors import classify
from nanopnp.gui.case_model import CaseEditor
from nanopnp.gui.charge import BUILD_UPTO as CHARGE_UPTO
from nanopnp.gui.charge import build_offer
from nanopnp.gui.run_model import RunControl
from nanopnp.gui.widgets import (
    CaseEditorWidget,
    ChargeWidget,
    ConvergenceWidget,
    GeometryWidget,
    ResultWidget,
    RunControlWidget,
    ViewerWidget,
)
from nanopnp.io.case import CaseValidationError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

__all__ = ["MainWindow", "main"]

PLOT_INTERVAL_MS = 250


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, editor: CaseEditor, *, store: Path | None = None) -> None:
        super().__init__()
        self._store = store
        self._control = RunControl()
        self._case = CaseEditorWidget(editor)
        self._geometry = GeometryWidget(editor, store=store)
        # The Geometry tab's control: one walk, one cancel token, both tabs.
        self._charge = ChargeWidget(editor, self._geometry.control)
        self._run = RunControlWidget(self._control)
        self._convergence = ConvergenceWidget(self._control.model.convergence)
        self._result = ResultWidget()
        self._viewer = ViewerWidget()

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._case, "Case")
        # After Case: the geometry is built from the case, before the run reads it back from the
        # store.
        tabs.addTab(self._geometry, "Geometry")
        # After Geometry: stage 7 reads the region and the mesh.
        tabs.addTab(self._charge, "Charge")
        tabs.addTab(self._run, "Run")
        tabs.addTab(self._convergence, "Convergence")
        tabs.addTab(self._result, "Result")
        tabs.addTab(self._viewer, "Fields")
        self.setCentralWidget(tabs)
        self.setWindowTitle(f"nanopnp — {editor.source or editor.document.name}")
        self.resize(1000, 800)

        self._run.startRequested.connect(self.start_run)
        self._geometry.buildRequested.connect(self.build_geometry)
        self._charge.buildRequested.connect(self.build_charge)
        self._geometry.structureLoaded.connect(self._show_structure)
        self._run.settled.connect(self._show_result)
        self._refresh = QtCore.QTimer(self)
        self._refresh.setInterval(PLOT_INTERVAL_MS)
        self._refresh.timeout.connect(self._convergence.refresh)
        self._refresh.start()

    def start_run(self) -> None:
        path = self._saved_case()
        if path is None:
            return
        self._control.start(path, store=self._store)
        # Empty the panels before the new run, not when it settles: the old numbers, deviations
        # (FR-25) and picture are not this run's. The plot is repointed because start builds a fresh
        # model.
        self._result.show_outcome(None)
        self._viewer.show_run(None)
        self._convergence.set_model(self._control.model.convergence)
        self._run.began()
        self.statusBar().showMessage(f"running {path}")

    def _saved_case(self) -> Path | None:
        editor = self._case.editor
        if editor.staged and not self._case.commit():
            self.statusBar().showMessage("the case was refused; see the Case tab")
            return None
        try:
            return editor.ensure_saved()
        except (ValueError, OSError) as error:
            # ``CaseValidationError`` is a ``ValueError`` and is caught with it.
            self.statusBar().showMessage(str(error))
            return None

    def build_geometry(self) -> None:
        path = self._saved_case()
        if path is None:
            return
        if self._geometry.build(path):
            self.statusBar().showMessage(f"building the geometry of {path}")
        else:
            self.statusBar().showMessage("the geometry was not built; see the Geometry tab")

    def build_charge(self) -> None:
        path = self._saved_case()
        if path is None:
            return
        # Asked of the committed document before the walk starts: the commit may have staged away
        # stage 7's work, and a walk for a tab that declines to follow it would run unwatched.
        offer = build_offer(self._case.editor.document)
        if not offer.offered:
            self.statusBar().showMessage(f"the charge was not built: {offer.reason}")
            return
        if self._geometry.build(path, upto=CHARGE_UPTO) and self._charge.follow(path):
            self.statusBar().showMessage(f"building the charge of {path}")
        else:
            self.statusBar().showMessage("the charge was not built; see the Charge tab")

    def _show_structure(self, path: str) -> None:
        field = self._case.widget_at("structure.source.path")
        if isinstance(field, QtWidgets.QLineEdit):
            field.setText(path)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._charge.shutdown()
        self._geometry.shutdown()
        super().closeEvent(event)

    def _show_result(self) -> None:
        self._convergence.refresh()
        try:
            outcome = self._control.model.outcome()
        except (FileNotFoundError, ValueError) as error:
            # A missing run directory or an unreadable manifest: say so rather than show the
            # previous run.
            self.statusBar().showMessage(str(error))
            return
        self._result.show_outcome(outcome)
        # Only a finished run has a converged state to draw. A cancelled run
        # wrote no artefact (§5.3.2) and a failed one has nothing to restore.
        self._viewer.show_run(None if outcome is None else outcome.directory)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the desktop shell."""
    parser = argparse.ArgumentParser(
        prog="nanopnp-gui",
        description="The nanopnp desktop shell: edit a case, run it, read the result (IF-09).",
    )
    parser.add_argument("case", type=Path, help="the case file to open")
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="artefact store root; the process default when omitted",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="build the window offscreen and exit, without entering the event loop",
    )
    arguments = parser.parse_args(argv)

    try:
        editor = CaseEditor.open(arguments.case)
    except (CaseValidationError, OSError, yaml.YAMLError) as error:
        print(f"nanopnp-gui: {error}", file=sys.stderr)
        return classify(error)

    if arguments.selftest:
        # Set before QApplication, and only for the selftest: a user who runs
        # the shell wants the platform's own plugin and its own GPU.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # Qt WebEngine on a headless runner has no GPU, and its Chromium child aborts without this;
        # nanopnp.gui.probe sets the same pair.
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")
    existing = QtWidgets.QApplication.instance()
    application = (
        existing
        if isinstance(existing, QtWidgets.QApplication)
        else QtWidgets.QApplication([sys.argv[0]])
    )
    window = MainWindow(editor, store=arguments.store)
    if arguments.selftest:
        window.show()
        return 0
    window.show()
    return int(application.exec())


if __name__ == "__main__":  # pragma: no cover - the script entry point
    raise SystemExit(main())
