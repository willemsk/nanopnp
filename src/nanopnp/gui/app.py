"""The desktop shell (IF-09): a window over the view-models, and nothing more.

ADR-004's consequence, stated: "the interface is a thin shell over the stage
objects the CLI drives". This module assembles six panels and wires them to
each other; it decides nothing about a case, a run, a result or a picture,
exactly as :mod:`nanopnp.cli` decides nothing about them.

**Save, then run.** §5.3.1 makes the case file the unit of reproducibility, and
the FR-25 manifest names it. So "Run" commits the staged edits, writes the file,
and runs the file — never a document held only in memory, whose manifest would
name an input that does not exist. "Build geometry" on the Geometry tab does the
same, and walks the saved file through stage 6 (WP24 D3).

**It prints for the same reason the command line does.** ``nanopnp-gui`` is a shell like
``nanopnp``, and a case file it cannot open is refused on standard error in the words
``nanopnp run`` would use, rather than opened into an empty form.

**This release's increment.** QR-11 asks each release for a usable graphical
surface over the functionality that exists at it: the schema-generated editor,
run control, the result panel, the live convergence plot and the ``webgui``
field viewer, five tabs over one run; and since WP24, Phase 2's increment, the
Geometry tab, which builds stages 1 to 6 and edits the contour by hand.

**The plot and the viewer are fed from the same two places the rest is.** The
convergence panel draws the :class:`~nanopnp.gui.convergence.ConvergenceModel`
that :class:`~nanopnp.gui.run_model.RunModel` builds from the run's own event
stream, and the viewer renders the run *directory* — the same directory the
result panel reads (§5.3.3). Neither is handed anything this window computed.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from PySide6 import QtCore, QtGui, QtWidgets

from nanopnp.cli.errors import classify
from nanopnp.gui.case_model import CaseEditor
from nanopnp.gui.run_model import RunControl
from nanopnp.gui.widgets import (
    CaseEditorWidget,
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
"""How often the convergence panel redraws while a run is in flight.

Slower than the run panel's 100 ms drain: that drain is what moves the model, and
a repaint of a few hundred line segments is worth doing four times a second
rather than ten."""


class MainWindow(QtWidgets.QMainWindow):
    """The shell's window: the case, its geometry, the run, its convergence, the result, the fields.

    Parameters
    ----------
    editor
        The case open for editing.
    store
        The artefact store's root, or ``None`` for the process default.
    """

    def __init__(self, editor: CaseEditor, *, store: Path | None = None) -> None:
        super().__init__()
        self._store = store
        self._control = RunControl()
        self._case = CaseEditorWidget(editor)
        self._geometry = GeometryWidget(editor, store=store)
        self._run = RunControlWidget(self._control)
        self._convergence = ConvergenceWidget(self._control.model.convergence)
        self._result = ResultWidget()
        self._viewer = ViewerWidget()

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._case, "Case")
        # After Case (WP24 D15): the geometry is built from the case and
        # before the run, which reads it back from the store.
        tabs.addTab(self._geometry, "Geometry")
        tabs.addTab(self._run, "Run")
        tabs.addTab(self._convergence, "Convergence")
        tabs.addTab(self._result, "Result")
        tabs.addTab(self._viewer, "Fields")
        self.setCentralWidget(tabs)
        self.setWindowTitle(f"nanopnp — {editor.source or editor.document.name}")
        self.resize(1000, 800)

        self._run.startRequested.connect(self.start_run)
        self._geometry.buildRequested.connect(self.build_geometry)
        self._geometry.structureLoaded.connect(self._show_structure)
        self._run.settled.connect(self._show_result)
        self._refresh = QtCore.QTimer(self)
        self._refresh.setInterval(PLOT_INTERVAL_MS)
        self._refresh.timeout.connect(self._convergence.refresh)
        self._refresh.start()

    def start_run(self) -> None:
        """Commit, save and run the case file.

        A refused commit stops here with the whole-document diagnostic on the
        case panel: a run of a case the schema does not accept would fail in the
        child with the same message, one process and several seconds later.

        Saving is :meth:`~nanopnp.gui.case_model.CaseEditor.ensure_saved` and
        not ``save``: a run that changed nothing must not rewrite a hand-written
        file and lose its comments.
        """
        path = self._saved_case()
        if path is None:
            return
        self._control.start(path, store=self._store)
        # The previous run's numbers are not this run's, and the deviations
        # beside them are the configuration that produced *those* numbers
        # (FR-25). The panels are emptied before the new run rather than left
        # showing the old one until it settles — the picture as much as the
        # numbers, and the plot is repointed because ``start`` builds a fresh
        # model rather than resetting the old one.
        self._result.show_outcome(None)
        self._viewer.show_run(None)
        self._convergence.set_model(self._control.model.convergence)
        self._run.began()
        self.statusBar().showMessage(f"running {path}")

    def _saved_case(self) -> Path | None:
        """Commit and save the case, or show why not and return ``None``.

        What a run and a geometry build both start from: the child reads the
        file, so an unsaved edit would be an edit the build never saw.
        """
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
        """Commit, save and build the case through stage 6 on the Geometry tab (WP24 D3)."""
        path = self._saved_case()
        if path is None:
            return
        if self._geometry.build(path):
            self.statusBar().showMessage(f"building the geometry of {path}")
        else:
            self.statusBar().showMessage("the geometry was not built; see the Geometry tab")

    def _show_structure(self, path: str) -> None:
        """Show a structure the Geometry tab staged in the Case tab's field.

        ``setText`` emits no ``editingFinished``, so the value is shown and not
        staged a second time.
        """
        field = self._case.widget_at("structure.source.path")
        if isinstance(field, QtWidgets.QLineEdit):
            field.setText(path)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Stop the Geometry tab's build and children with the window."""
        self._geometry.shutdown()
        super().closeEvent(event)

    def _show_result(self) -> None:
        """Read the run directory back into the result panel and the viewer.

        The viewer is pointed at the run *directory* and not at a solution: the
        render child restores the state through the stage-10 gate for itself, in
        a process of its own, so this window never holds a ``GridFunction`` and
        a run from an earlier session opens by the same path.
        """
        self._convergence.refresh()
        try:
            outcome = self._control.model.outcome()
        except (FileNotFoundError, ValueError) as error:
            # A run directory that is not there, or a manifest this build cannot
            # read: the panel says so rather than showing the previous run.
            self.statusBar().showMessage(str(error))
            return
        self._result.show_outcome(outcome)
        # Only a finished run has a converged state to draw. A cancelled run
        # wrote no artefact (§5.3.2) and a failed one has nothing to restore.
        self._viewer.show_run(None if outcome is None else outcome.directory)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the desktop shell.

    Parameters
    ----------
    argv
        Command-line arguments, defaulting to ``sys.argv[1:]``.

    Returns
    -------
    int
        The Qt event loop's exit status, or the §3.1 exit class
        :func:`~nanopnp.cli.errors.classify` gives when the case file named on
        the command line cannot be opened — refused here, in the words and with
        the code the command line uses, rather than opened into an empty form.
        A file that is not there and a file that is not YAML are refusals as
        much as one the schema rejects; ``classify`` gives each the code
        ``nanopnp run`` gives it for the same file, rather than a diagnostic
        for one of them and a traceback for the other two.
    """
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
        # The window now holds a ``QWebEngineView`` (the Fields panel), and Qt
        # WebEngine on a headless runner has no GPU to talk to; without this its
        # Chromium child aborts. The same pair ``nanopnp.gui.probe`` sets, for
        # the same reason and in the same place.
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
