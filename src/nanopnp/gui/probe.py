"""The packaging probe: the four binary payloads of RSK-13, in one process.

RSK-13 is "desktop packaging defeated by a binary dependency", and §8.2
criterion 4 asks for "a trivial PySide6 and NGSolve ``webgui`` application" that
"builds into a working double-clickable bundle on Windows". Amendment A4 says how
that is discharged: a gated ``windows-latest`` job builds this module into a
one-dir PyInstaller bundle on every push and launches it headlessly, and the
author's double-click closes the criterion.

**The probe is a detector, not a demonstration.** It carries every payload the
real shell will — Qt's widgets *and* Qt WebEngine, the compiled NGSolve and
Netgen extensions, and the ``ngsolve.webgui`` scene generator — because a probe
omitting WebEngine would retire RSK-13 without exercising the dependency most
likely to defeat packaging (ADR-004's packaging NOTE, §8.2.1 A4). :data:`PAYLOADS`
names that set, and ``tests/tier1/test_gui_probe.py`` reads this module's own
import statements to assert the two cannot drift apart.

**Every import is deferred.** ``PySide6.QtWidgets`` does not import at all on a
machine without the GL libraries (`.knowledge/07-software-stack.md` §5), and
``ngsolve`` costs ~370 ms; so nothing here is imported at module scope, and the
Tier-1 test that reads :data:`PAYLOADS` runs on the push gate where neither can
be imported.

**It is a program entry point, so it prints.** ``nanopnp.cli`` states the rule — diagnostics to
standard error, the command's own result to standard output, and no :func:`print` outside a shell's
own output. ``nanopnp-probe`` is such a shell: the ``--selftest`` report *is* its result, and it is
what the continuous-integration job's log shows.

**What ``--selftest`` establishes, and what it does not.** It establishes that
every payload imported, that a ``QApplication``, a ``QMainWindow`` and a
``QWebEngineView`` constructed, that a real ``ngsolve.webgui`` scene was
generated and handed to the view, and that the CON-11 licence notice travelled
with the bundle. It does not establish that the scene *rendered*: the HTML
webgui emits loads its renderer from a CDN, so a headless runner without network
finishes the document load with nothing drawn. Rendering is a human observation,
which is why criterion 4 still ends at the author's double-click.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.paths import PACKAGE_ROOT

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

    from PySide6.QtWidgets import QApplication, QMainWindow

logger = logging.getLogger(__name__)

__all__ = [
    "LICENCE_NOTICE_FILENAME",
    "PAYLOADS",
    "SELFTEST_TIMEOUT_MS",
    "build_window",
    "licence_notice",
    "main",
    "payload_versions",
    "scene_html",
]

PAYLOADS: tuple[str, ...] = (
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "ngsolve",
    "netgen",
    "ngsolve.webgui",
)
"""The binary payloads the bundle must carry, named by §8.2.1 amendment A4.

Not a list this module keeps beside its code: ``tests/tier1/test_gui_probe.py``
parses the import statements below and asserts the set they name is exactly this
one, so a payload dropped from the probe fails Tier 1 rather than quietly
narrowing what the bundle proves.
"""

LICENCE_NOTICE_FILENAME = "LICENSES-BUNDLE.md"
"""The CON-11 notice, collected into the bundle beside the executable."""

SELFTEST_TIMEOUT_MS = 60_000
"""How long ``--selftest`` waits for the web view's document load.

Generous because a cold Qt WebEngine start on a CI runner is slow, and the wait
is not what the test is about: every payload has already been imported and
constructed by the time it begins.
"""


def licence_notice() -> Path:
    """Return the path of the bundle's licence notice.

    Searched where PyInstaller puts a collected data file first, then beside the
    installed package, then in the repository, so that the probe reads the same
    notice whether it was launched from the bundle, from a wheel or from a
    checkout. ``nanopnp-probe`` is a declared console script, so the wheel
    location is not optional: without it the entry point would raise for every
    installation that is not a source tree.

    Returns
    -------
    Path
        The notice.

    Raises
    ------
    FileNotFoundError
        If it is in neither place, naming both. A bundle without it would be
        distributed in breach of CON-11, which is a packaging defect the probe
        is the right thing to detect — so ``--selftest`` fails on it rather than
        showing a window with an empty licence pane.
    """
    candidates = [
        # PyInstaller's extraction root, set on the frozen executable only.
        Path(getattr(sys, "_MEIPASS", sys.prefix)) / LICENCE_NOTICE_FILENAME,
        # Force-included into the wheel beside the package (pyproject.toml).
        PACKAGE_ROOT / LICENCE_NOTICE_FILENAME,
        PACKAGE_ROOT.parents[1] / "packaging" / LICENCE_NOTICE_FILENAME,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f"the bundle licence notice {LICENCE_NOTICE_FILENAME!r} is not installed; searched "
        f"{searched}. CON-11 requires the bundle to state the GPL-2+ obligations its default "
        "linear solver creates, so a bundle without it must not be distributed"
    )


def payload_versions() -> dict[str, str]:
    """Return the resolved version of every payload, importing each of them.

    Returns
    -------
    dict of str to str
        Library name to version string, in the order a reader wants them.
    """
    import netgen
    import ngsolve
    from PySide6 import QtCore

    return {
        "nanopnp": _nanopnp_version(),
        "Python": sys.version.split()[0],
        "PySide6": _pyside_version(),
        "Qt": QtCore.qVersion(),
        "NGSolve": str(ngsolve.__version__),
        "Netgen": str(netgen.version.__version__),
    }


def _nanopnp_version() -> str:
    """Return this package's version without importing a stage module."""
    from nanopnp import __version__

    return str(__version__)


def _pyside_version() -> str:
    """Return the PySide6 version string."""
    import PySide6

    return str(PySide6.__version__)


def scene_html() -> str:
    """Return the ``ngsolve.webgui`` HTML document for a trivial scene.

    A unit-square mesh, coarse enough to be instant: the scene is here to make
    ``ngsolve.webgui`` and the compiled meshers part of what the bundle has to
    carry, not to show anything about a nanopore.
    """
    import ngsolve
    from netgen.occ import unit_square
    from ngsolve.webgui import Draw

    mesh = ngsolve.Mesh(unit_square.GenerateMesh(maxh=0.3))
    scene = Draw(mesh, show=False)
    html: str = scene.GenerateHTML()
    return html


def build_window() -> QMainWindow:
    """Return the probe's window: the scene, the versions and the licence notice.

    Returns
    -------
    QMainWindow
        Not shown; the caller decides. ``loadFinished`` on the web view is the
        signal ``--selftest`` waits for, reached through
        ``window.findChild(QWebEngineView)``.

    Raises
    ------
    FileNotFoundError
        If the licence notice did not travel with the bundle; see
        :func:`licence_notice`.
    """
    from PySide6 import QtWidgets
    from PySide6.QtWebEngineWidgets import QWebEngineView

    notice = licence_notice().read_text(encoding="utf-8")
    versions = payload_versions()

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("nanopnp packaging probe")

    view = QWebEngineView()
    view.setHtml(scene_html())

    summary = QtWidgets.QPlainTextEdit()
    summary.setReadOnly(True)
    summary.setPlainText(
        "\n".join(f"{name}: {value}" for name, value in versions.items()) + "\n\n" + notice
    )

    splitter = QtWidgets.QSplitter()
    splitter.addWidget(view)
    splitter.addWidget(summary)
    splitter.setSizes([700, 500])
    window.setCentralWidget(splitter)
    window.resize(1200, 800)
    return window


def _selftest(application: QApplication, window: QMainWindow) -> int:
    """Construct the window offscreen, wait for its document load, and report.

    Returns
    -------
    int
        ``0`` always, once the window has been built: every payload imported and
        every object constructed before this is reached, and those are what
        RSK-13 is about. A document load that does not complete is reported on
        standard error rather than failed, because Qt WebEngine's rasteriser on
        a headless runner is not this project's dependency; §8.2.1 A4's
        criterion is closed by the author's double-click either way.
    """
    from PySide6 import QtCore
    from PySide6.QtWebEngineWidgets import QWebEngineView

    view = window.findChild(QWebEngineView)
    if view is None:  # pragma: no cover - build_window always adds one
        raise RuntimeError("the probe window carries no QWebEngineView")

    loaded: list[bool] = []

    def finished(ok: bool) -> None:
        loaded.append(bool(ok))
        application.quit()

    view.loadFinished.connect(finished)
    QtCore.QTimer.singleShot(SELFTEST_TIMEOUT_MS, application.quit)
    window.show()
    application.exec()

    for name, value in payload_versions().items():
        print(f"{name}: {value}")
    print(f"licence notice: {licence_notice()}")
    if loaded and loaded[0]:
        print("web view: document loaded")
    else:
        print(
            "web view: the document load did not complete within "
            f"{SELFTEST_TIMEOUT_MS / 1000:.0f} s; every payload still imported and constructed",
            file=sys.stderr,
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the probe.

    Parameters
    ----------
    argv
        Command-line arguments, defaulting to ``sys.argv[1:]``.

    Returns
    -------
    int
        ``0`` on success. A missing payload raises out of here, and the frozen
        executable's traceback is the diagnostic — which is exactly what RSK-13
        wants the CI job to print.
    """
    parser = argparse.ArgumentParser(
        prog="nanopnp-probe",
        description=(
            "The RSK-13 packaging probe: PySide6, Qt WebEngine, NGSolve, Netgen and "
            "ngsolve.webgui in one process (SPECIFICATION.md section 8.2 criterion 4)."
        ),
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="construct the window offscreen, wait for its document load, and exit",
    )
    arguments = parser.parse_args(argv)

    if arguments.selftest:
        # Set before QApplication, and only for the selftest: a user who
        # double-clicks the bundle wants the platform's own plugin.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # Qt WebEngine on a headless runner has no GPU to talk to; without this
        # its Chromium child aborts before the document load begins.
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

    from PySide6 import QtWidgets

    existing = QtWidgets.QApplication.instance()
    application = (
        existing
        if isinstance(existing, QtWidgets.QApplication)
        else QtWidgets.QApplication([sys.argv[0]])
    )
    window = build_window()
    if arguments.selftest:
        return _selftest(application, window)
    window.show()
    return int(application.exec())


if __name__ == "__main__":  # pragma: no cover - the frozen entry point
    raise SystemExit(main())
