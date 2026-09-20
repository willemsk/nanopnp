"""The desktop shell (IF-09): a window over the view-models, and nothing more.

ADR-004's consequence, stated: "the interface is a thin shell over the stage
objects the CLI drives". This module assembles three panels and wires them to
each other; it decides nothing about a case, a run or a result, exactly as
:mod:`nanopnp.cli` decides nothing about them.

**Save, then run.** §5.3.1 makes the case file the unit of reproducibility, and
the FR-25 manifest names it. So "Run" commits the staged edits, writes the file,
and runs the file — never a document held only in memory, whose manifest would
name an input that does not exist.

**It prints for the same reason the command line does.** ``nanopnp-gui`` is a shell like
``nanopnp``, and a case file it cannot open is refused on standard error in the words
``nanopnp run`` would use, rather than opened into an empty form.

**This release's increment.** QR-11 asks each release for a usable graphical
surface over the functionality that exists at it. WP14's half is the
schema-generated editor, run control and the result panel; the live convergence
plot and the ``webgui`` field viewer are WP15's, and this window is laid out to
take them as further tabs rather than to be rearranged for them.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from PySide6 import QtWidgets

from nanopnp.cli.errors import classify
from nanopnp.gui.case_model import CaseEditor
from nanopnp.gui.run_model import RunControl
from nanopnp.gui.widgets import CaseEditorWidget, ResultWidget, RunControlWidget
from nanopnp.io.case import CaseValidationError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

__all__ = ["MainWindow", "main"]


class MainWindow(QtWidgets.QMainWindow):
    """The shell's window: the case, the run and the result.

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
        self._run = RunControlWidget(self._control)
        self._result = ResultWidget()

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._case, "Case")
        tabs.addTab(self._run, "Run")
        tabs.addTab(self._result, "Result")
        self.setCentralWidget(tabs)
        self.setWindowTitle(f"nanopnp — {editor.source or editor.document.name}")
        self.resize(1000, 800)

        self._run.startRequested.connect(self.start_run)
        self._run.settled.connect(self._show_result)

    def start_run(self) -> None:
        """Commit, save and run the case file.

        A refused commit stops here with the whole-document diagnostic on the
        case panel: a run of a case the schema does not accept would fail in the
        child with the same message, one process and several seconds later.

        Saving is :meth:`~nanopnp.gui.case_model.CaseEditor.ensure_saved` and
        not ``save``: a run that changed nothing must not rewrite a hand-written
        file and lose its comments.
        """
        editor = self._case.editor
        if editor.staged and not self._case.commit():
            self.statusBar().showMessage("the case was refused; see the Case tab")
            return
        try:
            path = editor.ensure_saved()
        except (ValueError, OSError) as error:
            # ``CaseValidationError`` is a ``ValueError`` and is caught with it.
            self.statusBar().showMessage(str(error))
            return
        self._control.start(path, store=self._store)
        # The previous run's numbers are not this run's, and the deviations
        # beside them are the configuration that produced *those* numbers
        # (FR-25). The panel is emptied before the new run rather than left
        # showing the old one until it settles.
        self._result.show_outcome(None)
        self._run.began()
        self.statusBar().showMessage(f"running {path}")

    def _show_result(self) -> None:
        """Read the run directory back into the result panel, if there is one."""
        try:
            self._result.show_outcome(self._control.model.outcome())
        except (FileNotFoundError, ValueError) as error:
            # A run directory that is not there, or a manifest this build cannot
            # read: the panel says so rather than showing the previous run.
            self.statusBar().showMessage(str(error))


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
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
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
