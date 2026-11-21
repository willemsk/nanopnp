"""The installation's self-test: each compiled payload exercised once, and the server's renderer."""

from __future__ import annotations

import http.cookiejar
import importlib.util
import math
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.errors import EXIT_OK
from nanopnp.core.paths import structure_file
from nanopnp.gui.render import RENDERER_DIRECTORY, RENDERER_URL, host_page

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable, Collection, Sequence

__all__ = [
    "FRAGMENT",
    "FRAGMENT_Q_NET_E",
    "PAYLOADS",
    "SERVER_MODULE",
    "SERVER_TIMEOUT_S",
    "PayloadError",
    "exercise_payloads",
    "main",
]

PAYLOADS: tuple[str, ...] = (
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

SERVER_MODULE = "nanopnp.gui.web.server"
"""The module the self-test starts as a child, to ask it for the shipped renderer."""

SERVER_TIMEOUT_S = 60.0
"""How long the server child has to print its ready line."""


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


# GLU 18 to LEU 26 of 2WCD chain A, as deposited; a shipped file, because PDB2PQR fetches a path
# that is not a file from rcsb.org.
FRAGMENT = "2wcd-a-18-26"

# Q_net per pH (knowledge/07-software-stack/03-charge-and-electrostatics.md): three acids and both
# termini, neutral at pH 2 and three
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
        gmsh.model.add("nanopnp-selftest")
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


def _exercise_mesh() -> str:
    import netgen
    import ngsolve
    from netgen.occ import unit_square
    from ngsolve.webgui import Draw

    mesh = ngsolve.Mesh(unit_square.GenerateMesh(maxh=0.3))
    if mesh.ne == 0:
        raise ValueError("meshed the unit square into no triangles")
    data = Draw(mesh, show=False).GetData()
    if not data:
        raise ValueError("the renderer's scene of the unit square holds no data")
    return (
        f"NGSolve {ngsolve.__version__} with Netgen {netgen.version.__version__}: meshed the "
        f"unit square into {mesh.ne} triangles and drew its scene"
    )


def _ready_address(child: subprocess.Popen[str]) -> str:
    # Imported here: the server's module loads its web framework, which no other payload needs.
    from nanopnp.gui.web.server import READY

    assert child.stdout is not None
    deadline = time.monotonic() + SERVER_TIMEOUT_S
    while time.monotonic() < deadline:
        line = child.stdout.readline()
        if not line:
            break
        found = READY.match(line.strip())
        if found is not None:
            return found.group(1)
    raise RuntimeError(
        f"{SERVER_MODULE} printed no ready line within {SERVER_TIMEOUT_S:.0f} s "
        f"(exit status {child.poll()})"
    )


def _exercise_renderer(expected: Path) -> str:
    command = [sys.executable, "-m", SERVER_MODULE, "--no-browser", "--state", "empty"]
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ) as child:
        try:
            try:
                address = _ready_address(child)
            except RuntimeError as error:
                raise PayloadError(SERVER_MODULE, error) from error
            root, _, token = address.partition("/?token=")
            # The first answer sets the launch cookie, which the renderer's request then carries.
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            with opener.open(f"{root}/api/health?token={token}", timeout=30) as answer:
                if answer.status != 200:
                    raise ValueError(f"the server's health answered {answer.status}")
            with opener.open(f"{root}{RENDERER_URL}", timeout=30) as answer:
                served = answer.read()
        finally:
            assert child.stdin is not None
            child.stdin.close()
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    if served != expected.read_bytes():
        raise ValueError(
            f"the server serves {RENDERER_URL} as {len(served)} bytes that are not the shipped "
            f"renderer {expected}"
        )
    if RENDERER_URL not in host_page("/scene", RENDERER_URL, "self-test"):
        raise ValueError(f"a field's page does not load the renderer from {RENDERER_URL}")
    return f"ngsolve.webgui: a server child served the shipped renderer, {len(served)} bytes"


def exercise_payloads(
    only: Collection[str] | None = None, *, renderer: Path | None = None
) -> dict[str, str]:
    """Exercise each payload once; return one line per payload.

    Parameters
    ----------
    only
        Payload names to exercise; all of them by default.
    renderer
        The file the served renderer must equal; the shipped one by default.
    """
    expected = renderer if renderer is not None else RENDERER_DIRECTORY / "webgui.js"
    report: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="nanopnp-selftest-") as scratch:
        structure = Path(scratch) / "three-atoms.pdb"
        structure.write_text(_THREE_ATOMS, encoding="utf-8")
        exercises: tuple[tuple[str, Callable[[], str]], ...] = (
            ("ngsolve", _exercise_mesh),
            ("ngsolve.webgui", lambda: _exercise_renderer(expected)),
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
            if payload == "gmsh" and importlib.util.find_spec("gmsh") is None:
                report[payload] = "gmsh: not installed, the optional mesher skipped"
                continue
            try:
                report[payload] = exercise()
            except PayloadError:
                raise
            except Exception as error:
                raise PayloadError(payload, error) from error
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Run the self-test, print a line a payload and return 0; a failed payload raises.

    Raises
    ------
    PayloadError
        If a payload did not import or did not work; the message names it.
    """
    del argv
    for line in exercise_payloads().values():
        print(f"exercised {line}")
    return EXIT_OK
