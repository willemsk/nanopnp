"""Grab every tab and sub-view of the Qt shell offscreen, on example 07, for a design review.

    uv run python .claude/scripts/gui/capture_qt.py <out-dir>

Drives ``MainWindow`` through four states (``opened``, ``refused``, ``built``, ``run``) and writes
``<state>-<tab>[-<view>].png`` for each grab. An offscreen ``QWebEngineView`` draws nothing, so the
script also writes ``webgui-manifest.json``, one entry per ``viewer/*.html`` the render children
wrote, for ``shoot.cjs``, and ``qt-index.json``, one entry per grab naming the HTML shot that stands
for an empty web view. The scratch copy of the example stays in ``<out>/work``: the manifest points
into it. Needs the ``structure`` extra and the system libraries of
``knowledge/07-software-stack/05-gui-and-packaging.md``; about ten minutes. Removed with the Qt
shell.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# Before PySide6 is imported anywhere: the platform plugin and WebEngine's Chromium read these once.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

from PySide6 import QtCore, QtWidgets
from PySide6.QtWebEngineWidgets import QWebEngineView

from nanopnp.gui.app import MainWindow
from nanopnp.gui.case_model import CaseEditor
from nanopnp.validation.examples import copy_example

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("capture_qt")

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples" / "07-pdb-to-charged-run"
STRUCTURE = ROOT / "tests" / "data" / "structures" / "2wcd.pdb.gz"
CASE = "2wcd.case.yaml"
WINDOW_SIZE = (1280, 860)
WALK_TIMEOUT_S = 900.0
VIEW_TIMEOUT_S = 300.0
GRACE_S = 1.5
"""Pumped after a view reports idle, so a loaded web view and a repaint land before the grab."""
REFUSED_FIELD = ("numerics.mesh.size_scale", "-2")
"""``charge.ph``, the case's one bounded field, is a spin box clamped to its range; a negative mesh
scale reaches the commit as text and the schema refuses it there."""
HTML_VIEWPORT = (1000, 700)


@dataclass
class Grab:
    file: str
    state: str
    tab: str
    view: str
    webengine_empty: bool = False
    document: str = ""
    stands_for: str = ""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _html_id(document: Path) -> str:
    return f"html-{_slug(document.parent.parent.name)[:24]}-{_slug(document.stem)}"


class Capture:
    def __init__(self, window: MainWindow, application: QtWidgets.QApplication, out: Path) -> None:
        self.window = window
        self.application = application
        self.out = out
        self.grabs: list[Grab] = []
        self.missed: list[str] = []
        tabs = window.centralWidget()
        assert isinstance(tabs, QtWidgets.QTabWidget)
        self.tabs = tabs

    def pump(self, done: Callable[[], bool], timeout_s: float, what: str) -> bool:
        deadline = time.monotonic() + timeout_s
        loop = QtCore.QEventLoop()
        while not done():
            if time.monotonic() > deadline:
                logger.error("%s did not happen within %.0f s", what, timeout_s)
                return False
            QtCore.QTimer.singleShot(200, loop.quit)
            loop.exec()
        return True

    def settle(self) -> None:
        self.application.processEvents()
        end = time.monotonic() + GRACE_S
        self.pump(lambda: time.monotonic() > end, GRACE_S + 1.0, "the grace period")

    def idle(self) -> bool:
        geometry = self.window._geometry
        charge = self.window._charge
        viewer = self.window._viewer
        return (
            geometry._render is None
            and geometry._assess is None
            and not geometry._loading
            and charge._render is None
            and not charge._loading
            and viewer.model.state not in ("rendering", "loading")
        )

    def wait_idle(self, what: str) -> None:
        if not self.pump(self.idle, VIEW_TIMEOUT_S, what):
            self.missed.append(what)
        self.settle()

    def select_tab(self, title: str) -> None:
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == title:
                self.tabs.setCurrentIndex(index)
                return
        raise KeyError(title)

    def grab(self, state: str, tab: str, view: str = "", web: QWebEngineView | None = None) -> None:
        self.application.processEvents()
        name = "-".join(part for part in (state, _slug(tab), _slug(view)) if part)
        path = self.out / f"{name}.png"
        self.window.grab().save(str(path))
        record = Grab(file=path.name, state=state, tab=tab, view=view)
        # Offscreen, WebEngine has no WebGL: the shell swaps the view for its "did not draw"
        # diagnostic, so the document the view loaded names the HTML shot that stands for it.
        if web is not None and (document := web.url().toLocalFile()):
            record.webengine_empty = True
            record.document = document
            record.stands_for = _html_id(Path(document))
        self.grabs.append(record)
        logger.info("grabbed %s", path.name)

    def tabs_titles(self) -> list[str]:
        return [self.tabs.tabText(index) for index in range(self.tabs.count())]

    def opened(self) -> None:
        for title in self.tabs_titles():
            self.select_tab(title)
            self.settle()
            self.grab("opened", title)

    def refused(self) -> None:
        case = self.window._case
        path, text = REFUSED_FIELD
        field = case.widget_at(path)
        assert isinstance(field, QtWidgets.QLineEdit)
        original = field.text()
        self.select_tab("Case")
        field.setText(text)
        field.editingFinished.emit()
        case.commit()
        area = case.findChild(QtWidgets.QScrollArea)
        if area is not None:
            area.ensureWidgetVisible(field)
        self.settle()
        self.grab("refused", "Case", path)
        if case.editor.problems() is None:
            self.missed.append(f"refused: {path} = {text} was committed, not refused")
        case.editor.discard()
        field.setText(original)
        case.commit()

    def built(self) -> None:
        geometry = self.window._geometry
        charge = self.window._charge
        self.select_tab("Charge")
        self.window.build_charge()
        # Both tabs clear their settled flag as a build starts; a refused build leaves them set, and
        # the rows would be grabbed unbuilt.
        if geometry._settled or charge._settled:
            message = self.window.statusBar().currentMessage()
            self.missed.append(f"built: the charge build did not start: {message}")
            return
        if not self.pump(
            lambda: geometry._settled and charge._settled, WALK_TIMEOUT_S, "the charge build"
        ):
            self.missed.append("built: the charge build did not settle")
            return
        self.wait_idle("built: the views after the build")

        self.select_tab("Geometry")
        for index, row in enumerate(geometry.rows):
            geometry._list.setCurrentRow(index)
            self.wait_idle(f"built: the geometry row {row.name}")
            self.grab(
                "built", "Geometry", row.name, web=geometry._web if row.name == "mesh" else None
            )

        self.select_tab("Charge")
        panes = charge.panes
        for index in range(panes.count()):
            pane = panes.tabText(index)
            if not panes.isTabEnabled(index):
                self.missed.append(f"built: the Charge pane {pane} is disabled")
                continue
            panes.setCurrentIndex(index)
            self.wait_idle(f"built: the Charge pane {pane}")
            self.grab(
                "built", "Charge", pane, web=charge._web if pane == "Deployed field" else None
            )

    def run(self) -> None:
        settled: list[bool] = []
        self.window._run.settled.connect(lambda: settled.append(True))
        self.select_tab("Run")
        self.window.start_run()
        if not self.pump(lambda: bool(settled), WALK_TIMEOUT_S, "the run"):
            self.missed.append("run: the run did not settle")
            return
        self.wait_idle("run: the field render")
        for title in ("Run", "Convergence", "Result", "Fields"):
            self.select_tab(title)
            self.settle()
            self.grab("run", title, web=self.window._viewer._view if title == "Fields" else None)

    def write_indices(self, work: Path) -> None:
        manifest = []
        for document in sorted(work.rglob("viewer/*.html")):
            manifest.append(
                {
                    "id": _html_id(document),
                    "url": document.as_uri(),
                    "viewport": list(HTML_VIEWPORT),
                    "scheme": "light",
                    "wait_ms": 2000,
                }
            )
        (self.out / "webgui-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        shot = {entry["id"] for entry in manifest}
        for record in self.grabs:
            if record.stands_for and record.stands_for not in shot:
                self.missed.append(f"{record.file}: no HTML document {record.stands_for}")
        index = {
            "grabs": [asdict(record) for record in self.grabs],
            "missed": self.missed,
        }
        (self.out / "qt-index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )


def _prepare(out: Path) -> Path:
    work_root = out / "work"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    work = copy_example(EXAMPLE, work_root, repository=ROOT)
    prepare = work.parent / "06-pdb-to-mesh" / "prepare.py"
    structure = work_root / STRUCTURE.relative_to(ROOT)
    subprocess.run(
        [sys.executable, str(prepare), str(structure), "2wcd-prepared.pdb"], cwd=work, check=True
    )
    return work


def main(argv: list[str]) -> int:
    """Grab the shell's views into the directory named by ``argv[0]``; return an exit status."""
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    if len(argv) != 1:
        logger.error("usage: capture_qt.py <out-dir>")
        return 64
    out = Path(argv[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = _prepare(out)
    origin = Path.cwd()
    # The case's relative paths resolve against the working directory.
    os.chdir(work)
    try:
        application = QtWidgets.QApplication([sys.argv[0]])
        window = MainWindow(CaseEditor.open(work / CASE), store=work / "store")
        window.resize(*WINDOW_SIZE)
        window.show()
        capture = Capture(window, application, out)
        capture.opened()
        capture.refused()
        capture.built()
        capture.run()
        capture.write_indices(work)
        window.close()
        application.processEvents()
    finally:
        os.chdir(origin)
    for missed in capture.missed:
        logger.warning("not reached: %s", missed)
    logger.info("%d grabs, %d not reached", len(capture.grabs), len(capture.missed))
    return 0 if not capture.missed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
