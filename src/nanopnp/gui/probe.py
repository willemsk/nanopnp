"""The packaging probe: the binary payloads of RSK-13, in one process.

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
likely to defeat packaging (ADR-004's packaging NOTE, §8.2.1 A4) — and, since
WP24, the geometry pipeline's compiled readers, contour extraction, polygon
checks and the optional Gmsh backend, and since WP31 PDB2PQR and PROPKA, each
exercised once. :data:`PAYLOADS`
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
generated and loaded into the view as a file, that the **renderer shipped with
the package** reached the page with no network (WP15 OQ-1), and that the CON-11
licence notice travelled with the bundle. A renderer missing from the bundle
fails the selftest: it is a payload the viewer cannot draw without, and a bundle
that drops it is RSK-13's failure exactly. It does not establish that the scene
*rendered* — a headless runner has no GPU for WebGL — so whether the scene
initialised is reported and not gated. Rendering is a human observation, which is
why criterion 4 still ends at the author's double-click.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import sys
import traceback
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.paths import PACKAGE_ROOT, structure_file

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
"""The binary payloads the bundle must carry, named by §8.2.1 amendment A4.

Five are the geometry pipeline's compiled readers and meshers (WP24 D16, D17):
stage 1's two structure readers, stage 4's contour extraction and polygon
checks, and the optional Gmsh backend (§8.2.2 B8). Each is **exercised** by
:func:`exercise_payloads`, not only imported: RSK-13's failure is an extension
that imports and then cannot load the library it wraps.

The last two are stage 7's protonation (WP31 D14). They are pure Python, so what
can defeat the bundle is not a shared library but a data tree found through
``Path(__file__).parent``: PDB2PQR's force-field files and PROPKA's parameter
file. The exercise protonates a shipped fragment at two pH values, which only
works if both trees travelled.

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


class PayloadError(RuntimeError):
    """A payload imported but did not work, or did not import; the message names it."""

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
"""A three-atom PDB: the smallest structure both stage-1 readers accept."""


FRAGMENT = "2wcd-a-18-26"
"""The structure the protonation exercise reads, through :func:`~nanopnp.core.paths.structure_file`.

``GLU 18`` to ``LEU 26`` of 2WCD chain A, heavy atoms as deposited, written by
the stage's own :func:`~nanopnp.charge.protonation.frame_pdb`. A shipped file,
because PDB2PQR fetches a path that is not a file from rcsb.org.
"""

FRAGMENT_Q_NET_E: dict[float, float] = {2.0: 0.0, 8.0: -3.0}
"""``Q_net`` of :data:`FRAGMENT` at each pH, in e (`.knowledge/07` section 3, WP27).

Three acids and both termini: everything is neutral at pH 2, and the three
carboxylates are charged at pH 8 (PDB2PQR never applies a terminal pKa). Two
values rather than one, because only PROPKA moves them: without a titration
method the two pH values give equal charges.
"""

Q_NET_INTEGER_E = 1e-6
"""How far each ``Q_net`` may be from its integer, the stage's own gate (WP27 D9)."""


def _exercise_mdanalysis(structure: Path) -> str:
    """Read the three-atom structure with MDAnalysis."""
    import MDAnalysis

    atoms = MDAnalysis.Universe(str(structure)).atoms.n_atoms
    if atoms != 3:
        raise ValueError(f"read {atoms} atoms from a three-atom structure")
    return f"MDAnalysis {MDAnalysis.__version__}: read 3 atoms"


def _exercise_gemmi(structure: Path) -> str:
    """Read the three-atom structure with gemmi."""
    import gemmi

    atoms = gemmi.read_structure(str(structure))[0].count_atom_sites()
    if atoms != 3:
        raise ValueError(f"read {atoms} atoms from a three-atom structure")
    return f"gemmi {metadata.version('gemmi')}: read 3 atoms"


def _exercise_skimage() -> str:
    """Extract the contours of a 3 x 3 cross with scikit-image."""
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
    """Check a triangle with Shapely, which calls into GEOS."""
    import shapely
    import shapely.geometry

    if not shapely.geometry.Polygon([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]).is_valid:
        raise ValueError("GEOS reports the unit right triangle invalid")
    return f"Shapely {shapely.__version__} (GEOS {shapely.geos_version_string}): is_valid"


def _exercise_gmsh() -> str:
    """Mesh the unit square with Gmsh, and finalise it whatever happens."""
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
    """Return whether ``error`` was raised through the package that holds ``module_file``.

    PDB2PQR calls PROPKA and PROPKA never calls back, so a traceback that enters
    PROPKA's directory was raised inside PROPKA, or below it in the standard
    library on its behalf. That is how a missing ``propka.cfg``, which surfaces
    as an exception out of PDB2PQR's run, is still named PROPKA.
    """
    if module_file is None:
        return False
    package = Path(module_file).resolve().parent
    return any(
        Path(frame.filename).resolve().is_relative_to(package)
        for frame in traceback.extract_tb(error.__traceback__)
    )


def _exercise_protonation(scratch: Path) -> str:
    """Protonate :data:`FRAGMENT` at each pH of :data:`FRAGMENT_Q_NET_E`, as stage 7 does.

    Through :func:`~nanopnp.charge.protonation.run_pdb2pqr`, the stage's own
    driver, so the arguments, the logging and the Python 3.14 PROPKA fallback are
    the ones a run uses. Settings are ``Charge()``'s defaults with only ``ph``
    set: the probe writes no force field or titration method of its own (D14).

    Raises
    ------
    PayloadError
        Naming PROPKA when it does not import, when the failure was raised inside
        PROPKA's own code, as a missing ``propka.cfg`` is, or when the two pH
        values give equal charges:
        PDB2PQR ran, and nothing titrated. Any other failure is raised as it
        came, and the caller names PDB2PQR.
    """
    import pdb2pqr

    try:
        import propka
    except ImportError as error:
        # Named by the import system rather than by a literal here (D16): a
        # missing PROPKA is PROPKA's failure, not PDB2PQR's.
        raise PayloadError(error.name or pdb2pqr.__name__, error) from error

    from nanopnp.charge.pqr import read_pqr
    from nanopnp.charge.protonation import run_pdb2pqr
    from nanopnp.io.case import Charge, ResolvedProtonation

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
    """Exercise each geometry and protonation payload once, and report what each did.

    WP24 D17 for the geometry payloads, WP31 D14 for PDB2PQR and PROPKA.

    Parameters
    ----------
    only
        The exercises to run, by the payload each is keyed on; all of them by
        default. PDB2PQR's exercise covers PROPKA too. A test selects one where
        another payload's library is absent from the machine (Gmsh needs
        ``libGLU``).

    Returns
    -------
    dict of str to str
        Payload to a one-line account of what it did.

    Raises
    ------
    PayloadError
        Naming the first payload that failed to import or to work. An extension
        that imports and then cannot load its library is RSK-13's failure, so
        importing alone would prove nothing.
    """
    import tempfile

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


def scene_document() -> Path:
    """Write the host document for a trivial scene and return its path.

    A unit-square mesh, coarse enough to be instant: the scene is here to make
    ``ngsolve.webgui`` and the compiled meshers part of what the bundle has to
    carry, not to show anything about a nanopore. The document is the viewer's
    own (:func:`nanopnp.gui.render.host_document`), loading the shipped renderer,
    and it is written to a file because a ``setHtml`` page has no ``file:``
    origin to load that renderer from — the same reason the viewer loads a file
    (WP15 D9).
    """
    import json
    import tempfile

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
    """Construct the window offscreen, wait for its document load, and report.

    Returns
    -------
    int
        ``0`` once the window has been built and, if the document loaded, its
        renderer was there; ``1`` if the document loaded **without** the
        renderer. Every payload imported and every object constructed before this
        is reached, and those are what RSK-13 is about; the renderer is a payload
        too, now that it ships with the package, and the readiness probe is the
        only thing that can see it (``loadFinished`` is reached without it). A
        document load that does not complete, and a scene that does not
        initialise, are reported on standard error rather than failed, because Qt
        WebEngine's rasteriser on a headless runner is not this project's
        dependency; §8.2.1 A4's criterion is closed by the author's double-click
        either way.
    """
    import json

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
        # The geometry and protonation payloads first, each exercised once: a
        # bundle that cannot read a structure, mesh a square or protonate a
        # fragment fails naming the payload, before Qt.
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
