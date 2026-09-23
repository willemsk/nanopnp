"""Capture the desktop shell's panels for the user guide (WP16 D14).

Run by hand when the shell changes, not in CI, and commit the PNGs it writes::

    QT_QPA_PLATFORM=offscreen uv run docs/scripts/capture_gui.py

It copies example 01 into a scratch directory, writes its mesh, opens the case in the
shell's own window offscreen, runs it, and grabs three panels into ``docs/guide/img/``:
the case editor, the run control once the run has settled, and the convergence plot.
The WebEngine field viewer is described in the guide's text rather than captured, since
an offscreen WebEngine draws nothing to grab. No test looks at the pixels: the panels'
behaviour is Tier 1's (``tests/tier1/test_gui_widgets.py``), and these are pictures of
it.

On a Linux machine without ``libEGL.so.1``, PySide6 does not import. See
``.knowledge/07-software-stack.md`` section 5 for the local shim.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger("capture_gui")

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "guide" / "img"
EXAMPLE = ROOT / "examples" / "01-quickstart"
TIMEOUT_S = 600.0
"""How long the run may take before the capture gives up."""


def main() -> int:
    """Capture the three panels; return a process exit status."""
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

    from PySide6 import QtCore, QtWidgets

    from nanopnp.cli import main as cli
    from nanopnp.gui.app import MainWindow
    from nanopnp.gui.case_model import CaseEditor

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch) / EXAMPLE.name
        # Inputs only: a store left in the example by a manual run would serve
        # the solve from cache, and the plot would have no ladder to draw.
        shutil.copytree(EXAMPLE, work, ignore=shutil.ignore_patterns("store", "run*", "*.msh"))
        os.chdir(work)  # the case's mesh path resolves against the working directory
        if cli(["mesh", "cylinder", "--out", "pore.msh"]) != 0:
            return 1

        application = QtWidgets.QApplication([sys.argv[0]])
        window = MainWindow(CaseEditor.open(work / "quickstart.case.yaml"), store=work / "store")
        window.resize(1000, 760)
        window.show()
        tabs = window.centralWidget()
        assert isinstance(tabs, QtWidgets.QTabWidget)

        def grab(index: int, name: str) -> None:
            tabs.setCurrentIndex(index)
            application.processEvents()
            window.grab().save(str(OUTPUT / name))
            logger.info("wrote %s", OUTPUT / name)

        grab(0, "editor.png")

        settled: list[bool] = []
        window._run.settled.connect(lambda: settled.append(True))
        window.start_run()
        deadline = time.monotonic() + TIMEOUT_S
        loop = QtCore.QEventLoop()
        while not settled and time.monotonic() < deadline:
            QtCore.QTimer.singleShot(200, loop.quit)
            loop.exec()
        if not settled:
            logger.error("the run did not settle within %.0f s", TIMEOUT_S)
            return 1
        window._convergence.refresh()
        grab(1, "run.png")
        grab(2, "convergence.png")
        window.close()
        os.chdir(ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
