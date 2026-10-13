"""The packaging probe: the binary payloads of RSK-13, in one process."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import tempfile
import traceback
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.paths import PACKAGE_ROOT, structure_file
from nanopnp.core.public import __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable, Collection, Sequence

    from PySide6.QtWidgets import QApplication, QMainWindow

logger = logging.getLogger(__name__)

__all__ = [
    "FRAGMENT",
    "FRAGMENT_Q_NET_E",
    "LICENCE_NOTICE_FILENAME",
    "PAYLOADS",
    "SELFTEST_TIMEOUT_MS",
    "PayloadError",
    "build_window",
    "exercise_payloads",
    "licence_notice",
    "main",
    "payload_versions",
    "scene_document",
]

PAYLOADS: tuple[str, ...] = (
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineWidgets",
    "ngsolve",
    "netgen",
    "ngsolve.webgui",
    "MDAnalysis",
    "gemmi",
    "skimage.measure",
    "shapely.geometry",
    "gmsh",
    "pdb2pqr",
    "propka",
)

LICENCE_NOTICE_FILENAME = "LICENSES-BUNDLE.md"

SELFTEST_TIMEOUT_MS = 60_000


def licence_notice() -> Path:
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


class PayloadError(RuntimeError):
    def __init__(self, payload: str, cause: BaseException) -> None:
        self.payload = payload
        super().__init__(f"payload {payload!r} failed: {type(cause).__name__}: {cause}")


_THREE_ATOMS = (
    "".join(
        f"ATOM  {serial:5d}  {name:<3s} ALA A   1    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00"
        f"           {name[0]}\n"
        for serial, (name, x, y, z) in enumerate(
            (("N", 0.0, 0.0, 0.0), ("CA", 1.458, 0.0, 0.0), ("C", 2.009, 1.42, 0.0)), start=1
        )
    )
    + "END\n"
)


# GLU 18 to LEU 26 of 2WCD chain A, as deposited; a shipped file, because PDB2PQR fetches a path
# that is not a file from rcsb.org.
FRAGMENT = "2wcd-a-18-26"

# Q_net per pH (.knowledge/07 section 3): three acids and both termini, neutral at pH 2 and three
# carboxylates charged at pH 8; only PROPKA moves them, so equal charges mean nothing titrated.
FRAGMENT_Q_NET_E: dict[float, float] = {2.0: 0.0, 8.0: -3.0}

Q_NET_INTEGER_E = 1e-6


def _exercise_mdanalysis(structure: Path) -> str:
    import MDAnalysis

    atoms = MDAnalysis.Universe(str(structure)).atoms.n_atoms
    if atoms != 3:
        raise ValueError(f"read {atoms} atoms from a three-atom structure")
    return f"MDAnalysis {MDAnalysis.__version__}: read 3 atoms"


def _exercise_gemmi(structure: Path) -> str:
    import gemmi

    atoms = gemmi.read_structure(str(structure))[0].count_atom_sites()
    if atoms != 3:
        raise ValueError(f"read {atoms} atoms from a three-atom structure")
    return f"gemmi {metadata.version('gemmi')}: read 3 atoms"


def _exercise_skimage() -> str:
    import skimage.measure
    import skimage.morphology

    # The cross ``disk(1)``, as floats: made by the payload itself, because
    # importing NumPy here would be a payload the probe does not declare. Its
    # arms reach the edges, so the level cuts it into four open arcs.
    cross = skimage.morphology.disk(1).astype(float)  # type: ignore[no-untyped-call]
    contours = skimage.measure.find_contours(cross, 0.5)  # type: ignore[no-untyped-call]
    if not contours:
        raise ValueError("found no contour of a 3 x 3 cross at half its height")
    return (
        f"scikit-image {metadata.version('scikit-image')}: find_contours on a 3 x 3 array, "
        f"{len(contours)} arcs"
    )


def _exercise_shapely() -> str:
    import shapely
    import shapely.geometry

    if not shapely.geometry.Polygon([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]).is_valid:
        raise ValueError("GEOS reports the unit right triangle invalid")
    return f"Shapely {shapely.__version__} (GEOS {shapely.geos_version_string}): is_valid"


def _exercise_gmsh() -> str:
    import gmsh

    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("nanopnp-probe")
        gmsh.model.occ.addRectangle(0.0, 0.0, 0.0, 1.0, 1.0)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.5)
        gmsh.model.mesh.generate(2)
        _, tags, _ = gmsh.model.mesh.getElements(2)
        triangles = sum(len(block) for block in tags)
    finally:
        gmsh.finalize()
    if triangles == 0:
        raise ValueError("meshed the unit square into no triangles")
    return f"Gmsh {gmsh.__version__}: meshed the unit square into {triangles} triangles"


def _passes_through(error: BaseException, module_file: str | None) -> bool:
    if module_file is None:
        return False
    package = Path(module_file).resolve().parent
    return any(
        Path(frame.filename).resolve().is_relative_to(package)
        for frame in traceback.extract_tb(error.__traceback__)
    )


def _exercise_protonation(scratch: Path) -> str:
    import pdb2pqr

    try:
        import propka
    except ImportError as error:
        # Named by the import system: a missing PROPKA is PROPKA's failure, not PDB2PQR's.
        raise PayloadError(error.name or pdb2pqr.__name__, error) from error

    from nanopnp.charge.pqr import read_pqr
    from nanopnp.charge.protonation import run_pdb2pqr
    from nanopnp.io.case import Charge
    from nanopnp.io.resolved import ResolvedProtonation

    source = structure_file(FRAGMENT)
    found: dict[float, float] = {}
    for ph in FRAGMENT_Q_NET_E:
        charge = Charge(ph=ph)
        settings = ResolvedProtonation(
            ph=charge.ph, forcefield=charge.forcefield, titration=charge.titration
        )
        pqr = scratch / f"{FRAGMENT}-ph{ph:g}.pqr"
        try:
            report = run_pdb2pqr(source, pqr, settings)
        except Exception as error:
            if _passes_through(error, propka.__file__):
                raise PayloadError(propka.__name__, error) from error
            raise
        if report["missing"]:
            raise ValueError(f"could not parameterise {report['missing']} at pH {ph:g}")
        frames = read_pqr(pqr)
        if not frames or frames[0].atoms == 0:
            raise ValueError(f"wrote no charged atoms at pH {ph:g}")
        found[ph] = math.fsum(frames[0].charge_e.tolist())
    if len(set(found.values())) == 1:
        raise PayloadError(
            propka.__name__,
            ValueError(
                f"Q_net is {next(iter(found.values())):+.6f} e at every pH of "
                f"{sorted(found)}, so no titration state was computed"
            ),
        )
    for ph, expected in FRAGMENT_Q_NET_E.items():
        if abs(found[ph] - expected) > Q_NET_INTEGER_E:
            raise ValueError(
                f"Q_net of {FRAGMENT} at pH {ph:g} is {found[ph]:+.6f} e, not {expected:+.0f} e"
            )
    charges = ", ".join(f"{round(found[ph]):+d} e at pH {ph:g}" for ph in FRAGMENT_Q_NET_E)
    return (
        f"PDB2PQR {metadata.version(pdb2pqr.__name__)} with PROPKA "
        f"{metadata.version(propka.__name__)}: protonated {FRAGMENT}, {charges}"
    )


def exercise_payloads(only: Collection[str] | None = None) -> dict[str, str]:
    report: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="nanopnp-probe-") as scratch:
        structure = Path(scratch) / "three-atoms.pdb"
        structure.write_text(_THREE_ATOMS, encoding="utf-8")
        exercises: tuple[tuple[str, Callable[[], str]], ...] = (
            ("MDAnalysis", lambda: _exercise_mdanalysis(structure)),
            ("gemmi", lambda: _exercise_gemmi(structure)),
            ("skimage.measure", _exercise_skimage),
            ("shapely.geometry", _exercise_shapely),
            ("gmsh", _exercise_gmsh),
            ("pdb2pqr", lambda: _exercise_protonation(Path(scratch))),
        )
        for payload, exercise in exercises:
            if only is not None and payload not in only:
                continue
            try:
                report[payload] = exercise()
            except PayloadError:
                raise
            except Exception as error:
                raise PayloadError(payload, error) from error
    return report


def payload_versions() -> dict[str, str]:
    import netgen
    import ngsolve
    from PySide6 import QtCore

    return {
        "nanopnp": __version__,
        "Python": sys.version.split()[0],
        "PySide6": _pyside_version(),
        "Qt": QtCore.qVersion(),
        "NGSolve": str(ngsolve.__version__),
        "Netgen": str(netgen.version.__version__),
    }


def _pyside_version() -> str:
    import PySide6

    return str(PySide6.__version__)


def scene_document() -> Path:
    import ngsolve
    from netgen.occ import unit_square
    from ngsolve.webgui import Draw

    from nanopnp.gui.render import host_document, renderer_source

    mesh = ngsolve.Mesh(unit_square.GenerateMesh(maxh=0.3))
    scene = Draw(mesh, show=False)
    # Owner-only and unpredictable: never a name another local user can pre-create.
    directory = Path(tempfile.mkdtemp(prefix="nanopnp-probe-"))
    document = directory / "scene.html"
    document.write_text(
        host_document(
            json.dumps(scene.GetData()), renderer=renderer_source(), title="nanopnp probe"
        ),
        encoding="utf-8",
    )
    return document


def build_window() -> QMainWindow:
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtWebEngineWidgets import QWebEngineView

    notice = licence_notice().read_text(encoding="utf-8")
    versions = payload_versions()

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("nanopnp packaging probe")

    view = QWebEngineView()
    view.load(QtCore.QUrl.fromLocalFile(str(scene_document())))

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
    from PySide6 import QtCore
    from PySide6.QtWebEngineWidgets import QWebEngineView

    from nanopnp.gui.render import readiness_script, renderer_source

    view = window.findChild(QWebEngineView)
    if view is None:  # pragma: no cover - build_window always adds one
        raise RuntimeError("the probe window carries no QWebEngineView")

    loaded: list[bool] = []
    answers: list[object] = []

    def answered(answer: object) -> None:
        answers.append(answer)
        application.quit()

    def finished(ok: bool) -> None:
        loaded.append(bool(ok))
        if ok:
            view.page().runJavaScript(readiness_script(), answered)
        else:
            application.quit()

    view.loadFinished.connect(finished)
    QtCore.QTimer.singleShot(SELFTEST_TIMEOUT_MS, application.quit)
    window.show()
    application.exec()

    for name, value in payload_versions().items():
        print(f"{name}: {value}")
    print(f"licence notice: {licence_notice()}")
    print(f"renderer: {renderer_source()}")
    if not (loaded and loaded[0]):
        print(
            "web view: the document load did not complete within "
            f"{SELFTEST_TIMEOUT_MS / 1000:.0f} s; every payload still imported and constructed",
            file=sys.stderr,
        )
        return 0
    print("web view: document loaded")
    report = json.loads(answers[0]) if answers and isinstance(answers[0], str) else {}
    if not report.get("renderer_loaded"):
        print(
            f"web view: the document loaded but the renderer shipped at {renderer_source()} "
            "did not reach it, so this bundle cannot draw a field",
            file=sys.stderr,
        )
        return 1
    print("web view: renderer loaded")
    if report.get("ready"):
        print("web view: scene initialised")
    else:
        print(
            f"web view: the scene did not initialise ({report.get('error') or 'no reason given'}); "
            "a headless runner has no GPU for WebGL, so this is reported and not gated",
            file=sys.stderr,
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nanopnp-probe",
        description=(
            "The RSK-13 packaging probe: PySide6, Qt WebEngine, NGSolve, Netgen, "
            "ngsolve.webgui, the geometry pipeline's compiled payloads and stage 7's protonation "
            "in one process "
            "(SPECIFICATION.md section 8.2 criterion 4)."
        ),
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="construct the window offscreen, wait for its document load, and exit",
    )
    arguments = parser.parse_args(argv)

    if arguments.selftest:
        # The geometry and protonation payloads first: a bundle that cannot use one fails naming it,
        # before Qt.
        try:
            exercised = exercise_payloads()
        except PayloadError as error:
            print(f"nanopnp-probe: {error}", file=sys.stderr)
            return 1
        for line in exercised.values():
            print(f"exercised {line}")
        # Set before QApplication, and only for the selftest: a user who
        # double-clicks the bundle wants the platform's own plugin.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # Qt WebEngine on a headless runner has no GPU; without this its Chromium child aborts
        # before the load.
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
