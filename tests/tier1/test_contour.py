"""VER-51: stage 4, contour extraction, conditioning and its gate (FR-07, FR-08).

Every oracle is independent of the route it checks:

- a square pyramid is linear along every grid edge, so marching squares must
  place its level set exactly, and a Gaussian's circle bounds the interpolation
  error in closed form (WP20 plan, Design §6);
- a regular n-gon is an eigenvector of the umbrella operator, so Taubin and
  Laplacian smoothing scale its area by closed forms that differ by 5 % (Design §3);
- the morphology is checked on shapes whose gaps and fins sit either side of 4h;
- the probe profile of a ring of atoms is a distance to a circle.

The walk and the artefact run on a small C12 tube: 12 chains of 27 alanines on
three rings and nine layers, 0.3 nm apart. Its inner wall is flat, every atom of
the inner ring touching the probe sphere, which is the worst case for the radius
band's lower bound (Design §5).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from nanopnp.core.stages import create
from nanopnp.geometry import contour
from nanopnp.geometry.contour import (
    PAYLOAD_NAME,
    ContourGateError,
    assemble_region,
    canonical,
    close_and_open,
    enforce_spacing,
    exterior,
    extract_loops,
    gate,
    resample,
    simplify,
    taubin,
)
from nanopnp.geometry.probe import probe_radius_profile
from nanopnp.io.artefact import Artefact, StageInputs
from nanopnp.io.case import CaseValidationError, UnsupportedCaseSection, load_case, resolve
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.profile import (
    PIPELINE_SOURCE,
    load_profile,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)

H = 0.05


# -- extraction ------------------------------------------------------------------


def _axes(
    r_nodes: int = 121, z_nodes: int = 241, z_first_nm: float = -2.0
) -> tuple[np.ndarray, np.ndarray]:
    """Return non-square grid axes with a non-zero z origin, so a transposition shows."""
    return np.arange(r_nodes) * H, z_first_nm + np.arange(z_nodes) * H


def test_ver51_pyramid_contour_is_exact() -> None:
    """A square pyramid's level set is found to round-off, at the square the axes place it.

    ``f = 1 - max(|r - 3|, |z - 5|)/a``, centred on the node (3, 5) nm, with
    ``a(1 - l) = (k + 1/2) h``. Its kinks lie on nodes, so f is linear along every
    grid edge and marching squares interpolates it exactly. The level set is the
    square of half-side ``(k + 1/2) h``, whose corners sit at cell centres; each
    corner cell cuts off a triangle of legs h/2, so the loop's area is the square's
    less ``h^2/2``. A transposed axis, a half-bin shift or the author's ``w/h``
    scale each misplaces a vertex by at least h/2.
    """
    r_nm, z_nm = _axes()
    level, k = 0.25, 10
    half = (k + 0.5) * H
    a = half / (1.0 - level)
    r, z = np.meshgrid(r_nm, z_nm)
    field = 1.0 - np.maximum(np.abs(r - 3.0), np.abs(z - 5.0)) / a

    loops = extract_loops(field, r_nm, z_nm, level)
    assert len(loops) == 1
    loop = loops[0]
    on_square = np.maximum(np.abs(loop[:, 0] - 3.0), np.abs(loop[:, 1] - 5.0))
    assert np.max(np.abs(on_square - half)) <= 1e-12
    assert abs(abs(signed_area(loop)) - ((2 * half) ** 2 - H**2 / 2)) <= 1e-12
    assert signed_area(loop) < 0.0, "a loop around high values runs clockwise in (r, z)"


def test_ver51_gaussian_section_subpixel() -> None:
    """A Gaussian's 0.25 level is a circle of radius ``s sqrt(ln 4)``, found to 1e-3 nm.

    On a grid line through the centre, linear interpolation of f misplaces the
    crossing by at most ``h^2 |f''| / (8 |f'|)``, 4.7e-4 nm here (Design §6).
    """
    r_nm, z_nm = _axes()
    s = 1.0
    r, z = np.meshgrid(r_nm, z_nm)
    field = np.exp(-((r - 3.0) ** 2 + (z - 5.0) ** 2) / s**2)
    loops = extract_loops(field, r_nm, z_nm, 0.25)
    assert len(loops) == 1
    distance = np.hypot(loops[0][:, 0] - 3.0, loops[0][:, 1] - 5.0) - s * math.sqrt(math.log(4))
    assert np.max(np.abs(distance)) <= 1e-3


# -- smoothing -------------------------------------------------------------------


def _ngon(n: int, radius: float, centre: tuple[float, float] = (3.0, 5.0)) -> np.ndarray:
    """Return a regular n-gon, clockwise."""
    angles = -2.0 * np.pi * np.arange(n) / n
    return np.column_stack(
        (centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles))
    )


def test_ver51_taubin_keeps_area_laplace_shrinks() -> None:
    """Taubin scales a regular 64-gon's area by ``f(k1)^2N``; the Laplacian by ``(1 - lam k1)^2N``.

    The n-gon is an eigenvector of the circulant umbrella operator with
    ``k1 = 1 - cos(2 pi/64)``; one pass multiplies it by
    ``f = (1 - lam k1)(1 - mu k1)`` about its centroid, which the constant mode
    keeps. The Laplacian is the same N = 10 passes with mu = 0. Both closed forms
    hold to 1e-12, and the two differ by 5 %, so the test discriminates.
    """
    polygon = _ngon(64, 1.0)
    area = abs(signed_area(polygon))
    k1 = 1.0 - math.cos(2.0 * math.pi / 64)
    passes = contour.TAUBIN_PASSES
    lam, mu = contour.TAUBIN_LAMBDA, contour.TAUBIN_MU
    expected_taubin = ((1 - lam * k1) * (1 - mu * k1)) ** (2 * passes)
    expected_laplace = (1 - lam * k1) ** (2 * passes)
    assert expected_taubin == pytest.approx(1.002770, abs=5e-7)
    assert expected_laplace == pytest.approx(0.952933, abs=5e-7)

    taubin_ratio = abs(signed_area(taubin(polygon))) / area
    laplace_ratio = abs(signed_area(taubin(polygon, mu=0.0))) / area
    assert taubin_ratio == pytest.approx(expected_taubin, rel=1e-12)
    assert laplace_ratio == pytest.approx(expected_laplace, rel=1e-12)


def test_ver51_resample_is_uniform() -> None:
    """Resampling places points at one arc length, within 1 % of the target, on the loop."""
    loop = np.array([[2.0, 0.0], [2.0, 2.0], [3.0, 2.0], [3.0, 0.0]])
    points = resample(loop, H / 2)
    assert len(points) == round(6.0 / (H / 2))
    spacing = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    assert np.ptp(spacing) <= 1e-12
    assert spacing[0] == pytest.approx(H / 2, rel=0.01)


# -- the morphology ---------------------------------------------------------------


CORNER = (1.0 - math.pi / 4.0) * (2 * H) ** 2
"""A 90-degree corner's area change under a closing or opening of radius 2h."""


def test_ver51_closing_fills_subresolution_slot() -> None:
    """Closing and opening by 2h fill a 0.1 nm slot, remove a 0.1 nm fin and keep a 0.3 nm slot.

    The body is 1 x 2 nm. The area after is the body less the wide slot, to the
    corner-rounding bound: each of its eight 90-degree corners moves by at most
    ``delta^2 (1 - pi/4)``, and the fin's two roots likewise. After the rest of the
    conditioning the feature size exceeds 2h.
    """
    body = box(2.0, 0.0, 3.0, 2.0)
    narrow = box(2.5, 0.5, 3.0, 0.6)
    wide = box(2.5, 1.2, 3.0, 1.5)
    fin = box(1.5, 1.0, 2.0, 1.1)
    region = body.difference(narrow).difference(wide).union(fin)

    closed, record = close_and_open(region, contour.CLOSING_SPACINGS * H)
    assert closed.contains(Point(2.75, 0.55)), "the 0.1 nm slot is filled"
    assert not closed.contains(Point(2.75, 1.35)), "the 0.3 nm slot is kept"
    assert not closed.intersects(Point(1.75, 1.05)), "the 0.1 nm fin is removed"
    expected = body.area - wide.area
    assert abs(closed.area - expected) <= 10 * CORNER
    assert record["holes_filled"] == {"count": 0, "area_nm2": 0.0, "centroids_nm": []}

    points = resample(exterior(closed), H / 2)
    points = simplify(taubin(points), 0.02)
    points, _ = enforce_spacing(points, H)
    assert min_feature_size(points) > 2 * H


def test_ver51_topology() -> None:
    """A void is filled and recorded; an island is refused naming it; a closed lumen names its z.

    The void is 0.5 x 0.5 nm; its four corners are concave for the region, so the
    closing fills ``delta^2 (1 - pi/4)`` at each before the hole is recorded.
    """
    body = box(2.0, 0.0, 3.0, 2.0)
    void = box(2.25, 0.75, 2.75, 1.25)
    filled, record = close_and_open(body.difference(void), contour.CLOSING_SPACINGS * H)
    holes = record["holes_filled"]
    assert holes["count"] == 1  # type: ignore[index]
    assert holes["area_nm2"] == pytest.approx(void.area - 4 * CORNER, abs=1e-3)  # type: ignore[index]
    assert holes["centroids_nm"] == [pytest.approx([2.5, 1.0])]  # type: ignore[index]
    assert filled.area == pytest.approx(body.area - 4 * CORNER, abs=1e-3)

    island = box(4.0, 0.5, 4.5, 1.0)
    with pytest.raises(ContourGateError, match=r"loop topology: 2 components remain") as caught:
        close_and_open(body.union(island), contour.CLOSING_SPACINGS * H)
    assert "centroid (r, z) = (4.2500, 0.7500) nm" in str(caught.value)
    assert "area 0.2" in str(caught.value)

    r_nm, z_nm = _axes()
    r, z = np.meshgrid(r_nm, z_nm)
    field = ((r >= 2.0) & (r <= 3.0) & (z >= 1.0) & (z <= 4.0)).astype(float)
    field[(z >= 2.0) & (z <= 2.5) & (r <= 2.0)] = 1.0
    with pytest.raises(ContourGateError, match=r"open at the axis") as caught:
        extract_loops(field, r_nm, z_nm, 0.25)
    assert "closed on the axis over z = 2.000 to 2.500 nm" in str(caught.value)

    field[:, -1] = 1.0
    field[(z >= 2.0) & (z <= 2.5)] = 0.0
    with pytest.raises(ContourGateError, match=r"open at the outer radial edge"):
        extract_loops(field, r_nm, z_nm, 0.25)

    loops = extract_loops(_hollow(), *_axes(15, 15), 0.25)
    region = assemble_region(loops)
    assert len(loops) == 2
    assert isinstance(region, Polygon)
    assert len(region.interiors) == 1, "a counter-clockwise loop is a hole, not a body"


def _hollow() -> np.ndarray:
    """Return a 15 x 15 map holding a square annulus: one outer loop and one hole."""
    field = np.zeros((15, 15))
    field[3:12, 3:12] = 1.0
    field[6:9, 6:9] = 0.0
    return field


# -- the gate --------------------------------------------------------------------


def _rectangle(spacing: float = 0.1) -> np.ndarray:
    """Return the loop of r in [2, 3], z in [0, 2], vertices ``spacing`` apart, canonical."""
    bottom = [(2.0 + i * spacing, 0.0) for i in range(round(1.0 / spacing))]
    right = [(3.0, i * spacing) for i in range(round(2.0 / spacing))]
    top = [(3.0 - i * spacing, 2.0) for i in range(round(1.0 / spacing))]
    left = [(2.0, 2.0 - i * spacing) for i in range(round(2.0 / spacing))]
    return canonical(np.asarray(bottom + right + top + left))


def _planes() -> np.ndarray:
    """Return the mid-planes of a 0.05 nm z lattice over the rectangle."""
    return (np.arange(40) + 0.5) * H


def _gate(loop: np.ndarray, probe_nm: float = 1.9) -> dict[str, object]:
    planes = _planes()
    return gate(loop, spacing_nm=H, planes_nm=planes, probe_nm=np.full(planes.size, probe_nm))


def test_ver51_gate_criteria_fire() -> None:
    """Each §5.2.1 criterion fires on a loop built to fail it, naming value, threshold, (r, z)."""
    record = _gate(_rectangle())
    assert record["vertex_spacing"]["value_nm"] == pytest.approx(0.1)  # type: ignore[index]
    assert record["band"]["low"]["value_nm"] == pytest.approx(0.1)  # type: ignore[index]
    assert record["constriction"]["r_nm"] == pytest.approx(2.0)  # type: ignore[index]

    short = _rectangle()
    # Clockwise, the bottom edge runs towards smaller r: put a vertex 0.03 nm before (2.3, 0).
    before = int(np.flatnonzero(np.isclose(short[:, 0], 2.3) & (short[:, 1] == 0.0))[0])
    short = np.insert(short, before, [2.33, 0.0], axis=0)
    with pytest.raises(ContourGateError) as caught:
        _gate(short)
    assert caught.value.criterion == "minimum vertex spacing"
    assert "0.03 nm long" in caught.value.measured
    assert "h_c = 0.05 nm" in caught.value.threshold
    assert "(2.3150, 0.0000)" in caught.value.where

    slot = _rectangle()
    # A slot 0.08 nm wide and 0.4 nm deep in the outer wall at z = 1, which runs down.
    wall = int(np.flatnonzero((slot[:, 0] == 3.0) & np.isclose(slot[:, 1], 1.0))[0])
    notch = [(3.0, 1.04), (2.6, 1.04), (2.6, 0.96), (3.0, 0.96)]
    slot = np.vstack((slot[:wall], notch, slot[wall + 1 :]))
    with pytest.raises(ContourGateError) as caught:
        _gate(slot)
    assert caught.value.criterion == "minimum local feature size"
    assert "0.08 nm" in caught.value.measured
    assert "> 2 h_c = 0.1 nm" in caught.value.threshold
    assert caught.value.where in (
        "at (r, z) = (3.0000, 1.0400) nm",
        "at (r, z) = (3.0000, 0.9600) nm",
    )

    touching = _rectangle() - np.array([1.98, 0.0])
    with pytest.raises(ContourGateError) as caught:
        _gate(touching, probe_nm=-0.05)
    assert caught.value.criterion == "loop topology"
    assert "within 0.02 nm of the axis" in caught.value.measured
    assert "(0.0200, " in caught.value.where

    with pytest.raises(ContourGateError) as caught:
        _gate(_rectangle(), probe_nm=2.1)
    assert caught.value.criterion == "radius profile"
    assert "0.1 nm inside the probe radius 2.1000 nm" in caught.value.measured
    assert "r_c - R_p >= -h_c = -0.05 nm" in caught.value.threshold
    assert "(2.0000, 0.0250)" in caught.value.where

    with pytest.raises(ContourGateError) as caught:
        _gate(_rectangle(), probe_nm=0.0)
    assert caught.value.criterion == "radius profile"
    assert "2 nm outside the probe radius 0.0000 nm" in caught.value.measured
    assert "r_c - R_p <= 1.5 nm" in caught.value.threshold

    bowtie = np.array([[2.0, 0.0], [3.0, 1.0], [3.0, 0.0], [2.0, 1.0]])
    with pytest.raises(ContourGateError) as caught:
        _gate(bowtie)
    assert caught.value.criterion == "validity and simplicity"
    assert "(2.5000, 0.5000)" in caught.value.where

    with pytest.raises(ContourGateError) as caught:
        _gate(np.array([[2.0, 0.0], [3.0, 1.0]]))
    assert caught.value.criterion == "validity and simplicity"
    assert "fewer than three vertices" in caught.value.measured


def test_ver51_spacing_and_canonical_form() -> None:
    """The spacing step drops the endpoint that moves the area least; the loop starts lowest-z."""
    loop = np.array([[2.0, 0.0], [2.0, 1.0], [2.02, 1.0], [3.0, 1.0], [3.0, 0.0]])
    spaced, removed = enforce_spacing(loop, H)
    assert removed == 1
    assert [2.02, 1.0] not in spaced.tolist(), "the collinear endpoint costs no area"
    assert min_vertex_spacing(spaced) >= H

    shuffled = np.roll(_rectangle()[::-1], 7, axis=0)
    ordered = canonical(shuffled)
    assert signed_area(ordered) < 0.0
    assert ordered[0].tolist() == [2.0, 0.0]


# -- the probe profile -----------------------------------------------------------


def test_ver51_probe_ring_closed_form() -> None:
    """A ring of 12 atoms gives ``sqrt(rho0^2 + (z - z0)^2) - R_a``; two frames give the mean."""
    rho0, z0, radius, shift = 2.4, 1.0, 0.17, 0.3
    angles = 2.0 * np.pi * np.arange(12) / 12
    ring = np.column_stack((rho0 * np.cos(angles), rho0 * np.sin(angles), np.full(12, z0)))
    frames = np.stack((ring, ring + np.array([0.0, 0.0, shift])))
    z = np.linspace(-1.0, 3.0, 17)

    def exact(centre: float) -> np.ndarray:
        return np.sqrt(rho0**2 + (z - centre) ** 2) - radius

    radii = np.full(12, radius)
    assert np.max(np.abs(probe_radius_profile(frames[:1], radii, z) - exact(z0))) <= 1e-12
    mean = 0.5 * (exact(z0) + exact(z0 + shift))
    assert np.max(np.abs(probe_radius_profile(frames, radii, z) - mean)) <= 1e-12
    with pytest.raises(ValueError, match="11 radii for 12 atoms"):
        probe_radius_profile(frames, radii[:11], z)


# -- the stage, on a synthetic tube ----------------------------------------------


_TUBE_NAMES = ("N", "CA", "C", "O", "CB")


def _tube_pdb(path: Path) -> Path:
    """Write the C12 tube: per chain five atoms a ring on three rings over nine layers."""
    lines = []
    serial = 0
    for chain in range(12):
        points = [
            (rho, 2.0 * math.pi * (5 * chain + k) / 60, 0.3 * layer)
            for layer in range(9)
            for rho in (2.7, 3.0, 3.3)
            for k in range(5)
        ]
        for index, (rho, angle, z) in enumerate(points):
            serial += 1
            name = _TUBE_NAMES[index % 5]
            x, y = 10 * rho * math.cos(angle), 10 * rho * math.sin(angle)
            lines.append(
                f"ATOM  {serial:5d} {name:<4s} ALA {'ABCDEFGHIJKL'[chain]}{1 + index // 5:4d}    "
                f"{x:8.3f}{y:8.3f}{10 * z:8.3f}  1.00  0.00           {name[0]}"
            )
    path.write_text("\n".join([*lines, "END"]) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def tube(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the tube's PDB."""
    return _tube_pdb(tmp_path_factory.mktemp("tube") / "tube.pdb")


def _case(directory: Path, pdb: Path, *, geometry: str = "", name: str = "tube") -> Path:
    path = directory / f"{name}.case.yaml"
    path.write_text(
        "schema: nanopnp/case/v2\n"
        f"name: {name}\n"
        "structure:\n"
        f"  source: {{path: {pdb}}}\n"
        "  symmetry: {point_group: C12}\n"
        f"{geometry}"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.1\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="module")
def tube_store(tmp_path_factory: pytest.TempPathFactory) -> Store:
    """One store for the module: stages 1 to 3 run once."""
    return Store(tmp_path_factory.mktemp("tube-store"))


_KEY_SCRIPT = """
import sys
from nanopnp.core.stages import create
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import load_case
case = load_case(sys.argv[1])
structure = create("structure").key(StageInputs(case=case))
density = create("density").key(StageInputs(case=case, upstream={"structure": structure}))
symmetry = create("symmetry").key(StageInputs(case=case, upstream={"density": density}))
inputs = StageInputs(case=case, upstream={"structure": structure, "symmetry": symmetry})
print(create("contour").key(inputs).hash)
"""


def _key_artefact(case_path: Path) -> Artefact:
    """Return the stage-4 key artefact for a case, computed from keys alone."""
    case = load_case(case_path)
    structure = create("structure").key(StageInputs(case=case))  # type: ignore[attr-defined]
    density = create("density").key(  # type: ignore[attr-defined]
        StageInputs(case=case, upstream={"structure": structure})
    )
    symmetry = create("symmetry").key(  # type: ignore[attr-defined]
        StageInputs(case=case, upstream={"density": density})
    )
    inputs = StageInputs(case=case, upstream={"structure": structure, "symmetry": symmetry})
    key: Artefact = create("contour").key(inputs)  # type: ignore[attr-defined]
    return key


def _key(case_path: Path) -> str:
    """Return the stage-4 key's hash for a case."""
    return _key_artefact(case_path).hash


def test_ver51_artefact_and_key(
    tube: Path, tube_store: Store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The payload is a profile document; the key is stable across processes and moves with D13.

    The payload loads through ``load_profile`` as a pipeline profile whose sha256
    is stage 3's payload digest, and ``write_profile`` round-trips it bit for bit.
    A hand edit of the stored file is recorded as one (FR-27, VER-23).
    """
    case = _case(tmp_path, tube)
    result = run_case(case, store=tube_store, upto="contour", write=False)
    artefact = result.artefacts["contour"]
    assert artefact.hash == _key(case)
    profile = load_profile(artefact.payload[PAYLOAD_NAME])
    assert profile.provenance.source == PIPELINE_SOURCE
    assert not profile.is_reference
    assert profile.name == f"contour-{artefact.hash[:12]}"
    assert profile.provenance.sha256 == result.artefacts["symmetry"].summary["payload_digest"]
    assert profile.is_clockwise
    loop = profile.as_array()
    assert loop[0, 1] == loop[:, 1].min()
    assert artefact.summary["vertex_count"] == len(loop)
    again = load_profile(write_profile(profile, tmp_path / "copy.yaml"))
    assert again == profile

    completed = subprocess.run(
        [sys.executable, "-c", _KEY_SCRIPT, str(case)], capture_output=True, text=True, check=True
    )
    assert completed.stdout.strip() == artefact.hash

    base = _key(case)
    for geometry in (
        "geometry: {contour: {isolevel: 0.3}}\n",
        "geometry: {contour: {smoothing: none}}\n",
        "geometry: {contour: {simplify_tol_nm: 0.03}}\n",
        "geometry: {density: {grid_spacing_nm: 0.04}}\n",
    ):
        assert _key(_case(tmp_path, tube, geometry=geometry, name="moved")) != base, geometry
    assert _key(_case(tmp_path, tube, name="renamed")) == base
    parameters = artefact.parameters
    for name, value in contour.KEY_CONSTANTS.items():
        assert parameters[name] == value
    assert parameters["radius_set"]["name"] == "pdb2pqr_charmm"  # type: ignore[index]
    # The entries are the constants the pipeline reads, not literals beside them.
    closing, taubin_key = parameters["closing"], parameters["taubin"]
    assert closing["radius"] == f"{contour.CLOSING_SPACINGS:g}h" == "2h"  # type: ignore[index]
    assert closing["quad_segs"] == contour.QUAD_SEGS  # type: ignore[index]
    assert taubin_key["resample"] == f"h/{1 / contour.RESAMPLE_SPACINGS:g}" == "h/2"  # type: ignore[index]
    assert taubin_key["lambda"] == contour.TAUBIN_LAMBDA  # type: ignore[index]
    assert taubin_key["mu"] == contour.TAUBIN_MU  # type: ignore[index]
    assert taubin_key["passes"] == contour.TAUBIN_PASSES  # type: ignore[index]
    assert parameters["band"]["high_nm"] == contour.BAND_HIGH_NM  # type: ignore[index]
    assert parameters["feature"]["factor"] == contour.FEATURE_FACTOR  # type: ignore[index]
    for name in contour.KEY_CONSTANTS:
        changed = {**contour.KEY_CONSTANTS, name: "changed"}
        monkeypatch.setattr(contour, "KEY_CONSTANTS", changed)
        assert _key(case) != base, name
    monkeypatch.undo()

    stored = tube_store.get(artefact.schema, artefact.hash)
    assert stored is not None
    assert not stored.hand_substituted
    path = stored.payload[PAYLOAD_NAME]
    path.write_text(path.read_text(encoding="utf-8").replace("name: contour-", "name: edited-"))
    assert tube_store.get(artefact.schema, artefact.hash).hand_substituted  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("contour_block", "message"),
    [
        ("{isolevel: 0.0}", r"isolevel is 0\.0; .* lies in \(0, 1\)"),
        ("{isolevel: 1.0}", r"isolevel is 1\.0; .* lies in \(0, 1\)"),
        ("{isolevel: .nan}", r"isolevel is nan"),
        (
            "{simplify_tol_nm: 0.0}",
            r"simplify_tol_nm is 0\.0 nm; .* below the density grid "
            r"spacing h = 0\.05 nm",
        ),
        ("{simplify_tol_nm: 0.05}", r"simplify_tol_nm is 0\.05 nm; .* h = 0\.05 nm"),
        ("{simplify_tol_nm: .inf}", r"simplify_tol_nm is inf nm"),
    ],
)
def test_ver51_case_value_refusals(
    tube: Path, tmp_path: Path, contour_block: str, message: str
) -> None:
    """An isolevel outside (0, 1) or a tolerance outside (0, h) is refused naming it (D3)."""
    case = _case(tmp_path, tube, geometry=f"geometry: {{contour: {contour_block}}}\n")
    with pytest.raises(CaseValidationError, match=message):
        resolve(load_case(case))


def test_ver51_case_values_and_walk(tube: Path, tube_store: Store, tmp_path: Path) -> None:
    """A ``structure:`` case walks to stage 4; a full walk, a mesh walk and a sweep name stage 5.

    The tolerance is checked against the case's own grid spacing, so 0.035 nm is
    refused at h = 0.03 nm and admitted at the default h. The manifest's Geometry
    group records the contour (D15).
    """
    from nanopnp.sweep.plan import SweepPlanError, plan_from_document

    case = _case(tmp_path, tube)
    ran = run_case(case, store=tube_store, upto="contour", write=False)
    assert [record.name for record in ran.stages] == [
        "case",
        "structure",
        "density",
        "symmetry",
        "contour",
    ]
    group = ran.manifest.geometry_and_mesh
    recorded = group["contour"]
    for key in (
        "isolevel",
        "smoothing",
        "simplify_tol_nm",
        "h_c_nm",
        "vertex_count",
        "min_vertex_spacing_nm",
        "min_feature_size_nm",
        "holes_filled",
        "band",
        "constriction",
    ):
        assert key in recorded, key  # type: ignore[operator]
    assert recorded["band"]["low"]["value_nm"] >= -H  # type: ignore[index]

    with pytest.raises(UnsupportedCaseSection, match=r"Stage 5, CAD assembly .* WP21"):
        run_case(case, store=tube_store, write=False)
    with pytest.raises(UnsupportedCaseSection, match=r"stage 'mesh' extends past stage 4"):
        run_case(case, store=tube_store, upto="mesh", write=False)
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v1\n"
        "name: contour-sweep\n"
        f"base: {case}\n"
        "axes:\n"
        "  - {name: bias, path: boundary_conditions.bias_V, values: [0.05, 0.1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(SweepPlanError, match=r"Stage 5, CAD assembly"):
        plan_from_document(sweep)

    fine = "geometry: {density: {grid_spacing_nm: 0.03}, contour: {simplify_tol_nm: 0.035}}\n"
    with pytest.raises(CaseValidationError, match=r"h = 0\.03 nm"):
        resolve(load_case(_case(tmp_path, tube, geometry=fine, name="fine")))
    coarse = "geometry: {contour: {simplify_tol_nm: 0.035}}\n"
    assert resolve(load_case(_case(tmp_path, tube, geometry=coarse, name="coarse"))).contour


def test_ver51_gate_failure_aborts_the_walk(tube: Path, tube_store: Store, tmp_path: Path) -> None:
    """An isolevel with no closed contour aborts stage 4 naming the criterion; nothing is stored."""
    case = _case(tmp_path, tube, geometry="geometry: {contour: {isolevel: 0.999}}\n", name="high")
    with pytest.raises(ContourGateError, match=r"loop topology: the map has no closed contour"):
        run_case(case, store=tube_store, upto="contour", write=False)
    assert not tube_store.contains(_key_artefact(case))
