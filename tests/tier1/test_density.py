"""VER-49: stage 2, the density map — the union, its grid, its radii, its artefact and the walk.

The closed-form tests come first because they localise an error to one term: one
atom must deposit ``g`` itself, two must deposit ``g1 + g2 - g1 g2``, and two
frames must average rather than unite. The truncation is then held to its own
per-voxel bound against a brute-force evaluation with nothing truncated, which is
the one oracle that does not share the implementation's stencil (WP19 plan,
Verification; Design §1).
"""

from __future__ import annotations

import logging
import math
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import radii_file
from nanopnp.density.grid import GridFormatError
from nanopnp.density.map import DensityMap
from nanopnp.density.radii import DensityInputError, RadiusSet, resolve_radii
from nanopnp.density.union import (
    EPSILON,
    DensityGateError,
    DensityGrid,
    canonical_grid,
    check_positions,
    cutoff_nm,
    deposit,
    gate_density,
)
from nanopnp.io.case import CaseValidationError, UnsupportedCaseSection, load_case, resolve
from nanopnp.io.run import run_case
from nanopnp.io.store import Store

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)

H = 0.05
"""The coarsest spacing FR-04 admits, and the one every test here uses."""

CA_WIDTH_NM = 0.93 * 0.2275
"""sigma R for a CHARMM C-alpha, 2.275 A: the widest heavy-atom kernel."""


def _nodes(grid: DensityGrid) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the node coordinates as ``[z, y, x]`` arrays."""
    return np.meshgrid(grid.axis_nm("z"), grid.axis_nm("y"), grid.axis_nm("x"), indexing="ij")


def _gaussian(grid: DensityGrid, centre: np.ndarray, width: float) -> np.ndarray:
    """Return ``exp(-|x - a|^2/w^2)`` at every node, evaluated directly."""
    z, y, x = _nodes(grid)
    squared = (x - centre[0]) ** 2 + (y - centre[1]) ** 2 + (z - centre[2]) ** 2
    return np.exp(-squared / width**2)


def _kept(g: np.ndarray) -> np.ndarray:
    """Return ``g`` where it is kept and 0 where the stencil drops it."""
    return np.where(g >= EPSILON, g, 0.0)


def _case(tmp_path: Path, pdb: Path, *, geometry: str = "", inputs: str = "") -> Path:
    """Write a case carrying ``structure:`` for ``pdb``, and return its path."""
    text = (
        "schema: nanopnp/case/v2\n"
        "name: density\n"
        f"{inputs}"
        "structure:\n"
        f"  source: {{path: {pdb}}}\n"
        "  symmetry: {point_group: C12}\n"
        f"{geometry}"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.1\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}\n"
    )
    path = tmp_path / "density.case.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# -- the union, in closed form ------------------------------------------------


def test_ver49_closed_forms() -> None:
    """One atom deposits ``g``; two atoms 0.2 nm apart deposit ``g1 + g2 - g1 g2`` (FR-04).

    To 1e-15 in the float64 accumulation, and to float32 round-off (6e-8) in the
    stored map. The atoms sit off the nodes, so the separable stencil, the
    fractional offsets and the log-sum all enter.
    """
    one = np.array([[[0.013, -0.021, 0.37]]])
    widths = np.array([CA_WIDTH_NM])
    grid = canonical_grid(one, widths, H)
    expected = _kept(_gaussian(grid, one[0, 0], CA_WIDTH_NM))
    assert np.max(np.abs(deposit(one, widths, grid, float64=True) - expected)) <= 1e-15
    assert np.max(np.abs(deposit(one, widths, grid) - expected)) <= 6e-8

    two = np.array([[[0.013, -0.021, 0.37], [0.213, -0.021, 0.37]]])
    widths = np.array([CA_WIDTH_NM, 0.93 * 0.17])
    grid = canonical_grid(two, widths, H)
    g1 = _kept(_gaussian(grid, two[0, 0], widths[0]))
    g2 = _kept(_gaussian(grid, two[0, 1], widths[1]))
    expected = g1 + g2 - g1 * g2
    measured = deposit(two, widths, grid, float64=True)
    logger.info("two atoms: max error %.3g", float(np.max(np.abs(measured - expected))))
    assert np.max(np.abs(measured - expected)) <= 1e-15
    assert np.max(np.abs(deposit(two, widths, grid) - expected)) <= 6e-8


def test_ver49_union_is_bounded() -> None:
    """500 random atoms, ten of them coincident on a node: finite and within [0, 1] (QR-12).

    At a node under ten coincident atoms each term is ``log1p(-1) = -inf`` before
    the floor, so this is the case the floor exists for. The gate fires on an
    injected NaN naming the voxel, and a non-finite coordinate is refused naming
    the frame and the atom.
    """
    rng = np.random.default_rng(49)
    positions = rng.uniform(-1.5, 1.5, (1, 500, 3))
    positions[0, :10] = [0.1, -0.2, 0.3]  # on a node: g = 1 exactly there
    widths = 0.93 * rng.choice([0.17, 0.185, 0.2, 0.2275, 0.132, 0.02245], 500)
    grid = canonical_grid(positions, widths, H)
    values = deposit(positions, widths, grid, float64=True)
    assert np.all(np.isfinite(values))
    assert values.min() >= 0.0
    assert values.max() <= 1.0
    k, j, i = (
        int(np.argmin(np.abs(axis - value)))
        for axis, value in zip(
            (grid.axis_nm("z"), grid.axis_nm("y"), grid.axis_nm("x")), (0.3, -0.2, 0.1), strict=True
        )
    )
    assert values[k, j, i] == 1.0

    injected = values.copy()
    injected[3, 4, 5] = np.nan
    with pytest.raises(DensityGateError, match=r"voxel \[z=3, y=4, x=5\]"):
        gate_density(injected, grid)
    injected[3, 4, 5] = 1.0 + 1e-6
    with pytest.raises(DensityGateError, match=r"density gate: the map is 1\.000001"):
        gate_density(injected, grid)
    positions[0, 17, 1] = np.inf
    with pytest.raises(DensityInputError, match=r"frame 0 .* atom 17"):
        check_positions(positions)


def test_ver49_truncation_bound() -> None:
    """At each voxel, ``|delta rho| <= sum of g/(1 - g)`` over the dropped terms, nothing truncated.

    The oracle evaluates every atom at every node with nothing dropped, so it
    shares no stencil, no separable factorisation and no slab with the
    implementation. The maximum is logged; Design §1 predicts about 1e-5 at the
    protein's heavy-atom density.
    """
    rng = np.random.default_rng(7)
    positions = rng.uniform(-0.9, 0.9, (1, 200, 3))
    widths = 0.93 * rng.choice([0.17, 0.185, 0.2, 0.2275], 200)
    grid = canonical_grid(positions, widths, H)
    values = deposit(positions, widths, grid, float64=True)
    total = np.zeros(grid.shape)
    bound = np.zeros(grid.shape)
    for centre, width in zip(positions[0], widths, strict=True):
        g = _gaussian(grid, centre, width)
        total += np.log1p(-np.minimum(g, 1.0 - 2.0**-53))
        dropped = g < EPSILON
        bound[dropped] += g[dropped] / (1.0 - g[dropped])
    exact = -np.expm1(total)
    error = np.abs(values - exact)
    logger.info(
        "truncation: max |delta rho| %.3g, max bound %.3g (predicted about 1e-5)",
        float(error.max()),
        float(bound.max()),
    )
    assert np.all(error <= bound + 1e-15)
    assert error.max() > 0.0  # the bound is not met by computing nothing


def test_ver49_frames_average_not_union() -> None:
    """One atom in two frames 0.3 nm apart averages to ``(g_a + g_b)/2``, not their union.

    At the midpoint the two differ by ``g_a g_b / 2``, about 0.18 here, so a union
    across frames cannot pass (FR-04, WP19 D4).
    """
    positions = np.array([[[0.0, 0.0, 0.40]], [[0.0, 0.0, 0.10]]])
    widths = np.array([CA_WIDTH_NM])
    grid = canonical_grid(positions, widths, H)
    ga = _kept(_gaussian(grid, positions[0, 0], CA_WIDTH_NM))
    gb = _kept(_gaussian(grid, positions[1, 0], CA_WIDTH_NM))
    values = deposit(positions, widths, grid)
    assert np.max(np.abs(values - (ga + gb) / 2.0)) <= 1e-7
    union = ga + gb - ga * gb
    k = int(np.argmin(np.abs(grid.axis_nm("z") - 0.25)))
    centre = grid.half_width
    assert union[k, centre, centre] - values[k, centre, centre] > 1e-2


def test_ver49_grid_is_canonical() -> None:
    """Nodes are multiples of h, the axis is a node column, and the box holds every kept term.

    Permuting the frames changes neither the grid nor the map beyond summation
    order. Moving every atom by exactly one spacing in z moves the map by exactly
    one plane: the lattice is fixed by the frame, not by the atoms.
    """
    rng = np.random.default_rng(11)
    positions = rng.uniform(-1.0, 1.0, (3, 60, 3)) + np.array([0.3, -0.2, 4.0])
    widths = 0.93 * rng.choice([0.17, 0.2, 0.2275], 60)
    grid = canonical_grid(positions, widths, H)
    for axis in ("x", "y", "z"):
        nodes = grid.axis_nm(axis) / H
        assert np.max(np.abs(nodes - np.rint(nodes))) <= 1e-12
    assert grid.axis_nm("x")[grid.half_width] == 0.0
    assert grid.axis_nm("y")[grid.half_width] == 0.0
    reach = cutoff_nm(widths)
    low = np.array(grid.origin_nm)
    high = low + (np.array(grid.shape[::-1]) - 1) * H
    for frame in positions:
        assert np.all(frame - reach[:, None] >= low + H)
        assert np.all(frame + reach[:, None] <= high - H)
    assert np.all(np.hypot(frame[:, 0], frame[:, 1]) + reach <= (grid.half_width - 1) * H)

    values = deposit(positions, widths, grid, float64=True)
    permuted = positions[[2, 0, 1]]
    assert canonical_grid(permuted, widths, H) == grid
    assert np.max(np.abs(deposit(permuted, widths, grid, float64=True) - values)) <= 1e-15

    shifted = positions + np.array([0.0, 0.0, H])
    moved = canonical_grid(shifted, widths, H)
    assert (moved.half_width, moved.z_first, moved.nz) == (
        grid.half_width,
        grid.z_first + 1,
        grid.nz,
    )
    assert np.max(np.abs(deposit(shifted, widths, moved, float64=True) - values)) <= 1e-12


# -- the radius set -----------------------------------------------------------


@pytest.mark.parametrize(
    ("residue", "atom", "radius"),
    [
        ("ALA", "CA", 2.275),  # (1) the residue itself
        ("HID", "ND1", 1.85),  # (1) PDB2PQR's histidine name, read as HSD
        ("HIS", "CA", 2.275),  # (2) HIS, where HSD, HSE and HSP agree
        ("HIS", "HD1", 0.2245),  # (2) HSD and HSP name it and agree; HSE lacks it
        ("ILE", "CD1", 2.06),  # (3) the atom alias for CHARMM's CD
        ("ALA", "OXT", 1.70),  # (3) OXT as OT2, then (4) the CTER patch
        ("GLU", "HT1", 0.2245),  # (4) the NTER patch
        ("HSE", "HT1", 0.2245),  # (4) the NTER patch on a CHARMM histidine
        ("PRO", "HN1", 0.2245),  # (4) proline's own N-terminal patch
        ("GLY", "HT2", 0.2245),  # (4) glycine's own N-terminal patch
    ],
)
def test_ver49_radius_lookup(residue: str, atom: str, radius: float) -> None:
    """Each lookup route of WP19 D3 resolves to the CHARMM radius, in Å."""
    assert RadiusSet.load("pdb2pqr_charmm").radius_A(residue, atom) == radius


@pytest.mark.parametrize(
    ("residue", "atom", "message"),
    [
        ("XYZ", "CA", r"has no residue XYZ"),
        ("ALA", "CG", r"names no radius for ALA CG"),
        ("HIS", "HD2", r"HIS HD2 is ambiguous .* HSD 1\.468 Å, HSE 1\.468 Å, HSP 0\.9 Å"),
        ("DUM", "DUM", r"has radius 0\.0 Å"),
    ],
)
def test_ver49_radius_refusals(residue: str, atom: str, message: str) -> None:
    """An atom the set does not resolve is refused naming chain, residue number, residue and atom.

    There is no fallback by element (section 5.3.1 NOTE on ``geometry.density``).
    An unknown residue is refused before the terminal patches are consulted,
    which would otherwise place its C-alpha from ``NTER``.
    """
    with pytest.raises(DensityInputError, match=message) as raised:
        resolve_radii(
            "pdb2pqr_charmm",
            resname=np.array(["ALA", residue]),
            atom=np.array(["CA", atom]),
            chain=np.array(["A", "K"]),
            resid=np.array([1, 27]),
            icode=np.array(["", "B"]),
        )
    assert f"atom {atom!r} of residue {residue} 27B in chain 'K'" in str(raised.value)


def test_ver49_radius_table_matches_charmm_dat() -> None:
    """The shipped table equals PDB2PQR's ``CHARMM.DAT``, entry for entry, both ways.

    Skips without the ``structure`` extra, which carries pdb2pqr.
    """
    pdb2pqr = pytest.importorskip("pdb2pqr")
    source = Path(pdb2pqr.__file__).parent / "dat" / "CHARMM.DAT"
    table = RadiusSet.load("pdb2pqr_charmm")
    listed: set[tuple[str, str]] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        residue, atom, _, radius, *_ = line.split("\t")
        assert table.residues[residue][atom] == float(radius), (residue, atom)
        listed.add((residue, atom))
    shipped = {(residue, atom) for residue, atoms in table.residues.items() for atom in atoms}
    assert shipped == listed
    raw = yaml.safe_load(radii_file("pdb2pqr_charmm").read_text(encoding="utf-8"))
    if pdb2pqr.__version__ == raw["source"]["version"]:
        from nanopnp.core.hashing import file_hash

        assert file_hash(source) == raw["source"]["sha256"]


# -- the artefact -------------------------------------------------------------


def test_ver49_map_round_trip_and_export(synthetic_c12: Path, tmp_path: Path) -> None:
    """The map round-trips through ``.npz``, OpenDX and CCP4; the key is stable; an edit is seen.

    Origin, spacing and shape come back exactly, because the grid is rebuilt from
    integer node indices. OpenDX writes float32 values to six decimals, so they
    return within 5e-7 plus float32's spacing at 1 when parsed back, 6e-8; CCP4
    stores float32, so they return exactly (VER-29's statement of each format's
    precision; IF-05, FR-27).
    """
    case = _case(tmp_path, synthetic_c12)
    store = Store(tmp_path / "store")
    result = run_case(case, store=store, upto="density", write=False)
    artefact = result.artefacts["density"]
    density = DensityMap.read(artefact.payload["density"])
    assert density.digest() == artefact.summary["payload_digest"]
    assert density.header["hydrogens"] == 0
    assert density.header["atoms"]["by_element"] == {"C": 288, "N": 96, "O": 96}
    assert density.header["radius_set"]["name"] == "pdb2pqr_charmm"
    again = DensityMap.read(density.write(tmp_path / "copy.npz"))
    assert again.digest() == density.digest()

    for suffix, tolerance in ((".dx", 5e-7 + 2.0**-24), (".ccp4", 0.0), (".mrc", 0.0)):
        exported = DensityMap.read(density.export(tmp_path / f"map{suffix}"))
        assert exported.grid == density.grid
        assert np.max(np.abs(exported.values - density.values)) <= tolerance
    with pytest.raises(GridFormatError, match=r"\.npz, \.dx, \.ccp4"):
        density.export(tmp_path / "map.vtk")
    # An origin off the lattice, by half a spacing in x and y or 0.013 nm in z, is
    # refused rather than rounded onto it, which would move every value.
    from gridData import Grid

    h = density.grid.spacing_nm
    x0, y0, z0 = density.grid.origin_nm
    raw = np.transpose(density.values, (2, 1, 0))
    for origin in ((x0 - h / 2, y0 - h / 2, z0), (x0, y0, z0 + 0.013)):
        off = tmp_path / "off-lattice.dx"
        Grid(grid=raw, origin=origin, delta=(h,) * 3).export(str(off), file_format="DX")
        with pytest.raises(GridFormatError, match=r"integer multiples of it"):
            DensityMap.read(off)

    script = (
        "from nanopnp.core.stages import create\n"
        "from nanopnp.io.run import run_case\n"
        "from nanopnp.io.store import Store\n"
        f"result = run_case({str(case)!r}, store=Store({str(tmp_path / 'store')!r}), "
        "upto='density', write=False)\n"
        "print(result.artefacts['density'].hash, result.stages[-1].cached)\n"
    )
    other = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert other.stdout.split() == [artefact.hash, "True"]

    stored = store.get(artefact.schema, artefact.hash)
    assert stored is not None
    assert not stored.hand_substituted
    DensityMap(
        values=density.values * np.float32(0.5), grid=density.grid, header=density.header
    ).write(stored.payload["density"])
    assert store.get(artefact.schema, artefact.hash).hand_substituted  # type: ignore[union-attr]


def test_ver49_the_key_moves_with_every_input(synthetic_c12: Path, tmp_path: Path) -> None:
    """The stage-2 key moves with the spacing and the sharpness, and not with the case name."""
    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs

    def key(geometry: str) -> str:
        case = load_case(_case(tmp_path, synthetic_c12, geometry=geometry))
        structure = create("structure").key(StageInputs(case=case))  # type: ignore[attr-defined]
        inputs = StageInputs(case=case, upstream={"structure": structure})
        return str(create("density").key(inputs).hash)  # type: ignore[attr-defined]

    base = key("")
    assert key("geometry: {density: {grid_spacing_nm: 0.05, sharpness: 0.93}}\n") == base
    assert key("geometry: {density: {grid_spacing_nm: 0.04}}\n") != base
    assert key("geometry: {density: {sharpness: 0.9}}\n") != base


# -- case resolution and the walk ----------------------------------------------


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        ("{grid_spacing_nm: 0.02}", r"grid_spacing_nm is 0\.02 nm; FR-04 requires 0\.025-0\.05"),
        ("{grid_spacing_nm: 0.06}", r"grid_spacing_nm is 0\.06 nm; FR-04 requires 0\.025-0\.05"),
        ("{sharpness: 0.0}", r"sharpness is 0\.0; it scales each atom's radius"),
        ("{sharpness: -0.93}", r"sharpness is -0\.93"),
        ("{sharpness: .inf}", r"sharpness is inf; .* a positive number"),
    ],
)
def test_ver49_resolution_refusals(
    synthetic_c12: Path, tmp_path: Path, geometry: str, message: str
) -> None:
    """A spacing outside FR-04's range, or a non-positive sharpness, is refused naming the key."""
    case = _case(tmp_path, synthetic_c12, geometry=f"geometry: {{density: {geometry}}}\n")
    with pytest.raises(CaseValidationError, match=message):
        resolve(load_case(case))


def test_ver49_resolution_and_walk_rules(synthetic_c12: Path, tmp_path: Path) -> None:
    """A ``structure:`` case walks to stage 3; a full walk and a sweep are refused naming stage 5.

    Stage 4 until WP20 delivered it (WP20 D1).

    ``geometry:`` beside ``inputs.mesh`` is refused naming both, by the upstream
    rule; ``geometry:`` with neither ``structure:`` nor a mesh describes no run
    (WP19 D1, D2; section 5.3.1 NOTE on ``geometry.density``).
    """
    from nanopnp.sweep.plan import SweepPlanError, plan_from_document

    case = _case(tmp_path, synthetic_c12, geometry="geometry: {membrane: {thickness_nm: 2.8}}\n")
    store = Store(tmp_path / "store")
    ran = run_case(case, store=store, upto="symmetry", write=False)
    assert [record.name for record in ran.stages] == ["case", "structure", "density", "symmetry"]
    group = ran.manifest.geometry_and_mesh
    assert {"structure", "density", "reduction"} <= set(group)
    assert group["density"]["radius_set"]["name"] == "pdb2pqr_charmm"  # type: ignore[index]
    assert group["reduction"]["n"] == 12  # type: ignore[index]

    with pytest.raises(UnsupportedCaseSection, match=r"Stage 5, CAD assembly .* WP21"):
        run_case(case, store=store, write=False)
    with pytest.raises(UnsupportedCaseSection, match=r"stage 'mesh' extends past stage 4"):
        run_case(case, store=store, upto="mesh", write=False)
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v1\n"
        "name: density-sweep\n"
        f"base: {case}\n"
        "axes:\n"
        "  - {name: bias, path: boundary_conditions.bias_V, values: [0.05, 0.1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(SweepPlanError, match=r"Stage 5, CAD assembly"):
        plan_from_document(sweep)

    mesh = "inputs:\n  mesh: {path: pore.msh, format: msh41}\n"
    text = case.read_text(encoding="utf-8")
    beside = tmp_path / "beside.case.yaml"
    beside.write_text(
        text.replace("structure:\n", mesh + "structure:\n", 1).replace(
            text[text.index("structure:\n") : text.index("geometry:")], "", 1
        )
    )
    with pytest.raises(CaseValidationError, match=r"geometry: section and supplies inputs\.mesh"):
        resolve(load_case(beside))
    alone = tmp_path / "alone.case.yaml"
    alone.write_text(text.replace(text[text.index("structure:\n") : text.index("geometry:")], ""))
    with pytest.raises(UnsupportedCaseSection, match=r"supplies no inputs\.mesh"):
        resolve(load_case(alone))


def test_ver49_a_bad_atom_aborts_stage_two_naming_it(synthetic_c12: Path, tmp_path: Path) -> None:
    """An atom the radius set does not place aborts the run naming it, before any deposition."""
    lines = synthetic_c12.read_text(encoding="utf-8").splitlines()
    lines[44] = lines[44][:12] + "CG  " + lines[44][16:]  # chain B, residue 1
    pdb = tmp_path / "bad.pdb"
    pdb.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(DensityInputError, match=r"atom 'CG' of residue ALA 1 in chain 'B'"):
        run_case(_case(tmp_path, pdb), store=Store(tmp_path / "store"), upto="density")


def test_ver49_radius_refusal_names_the_first_atom_in_file_order() -> None:
    """Of two atoms the set does not place, the refusal names the one earlier in the file.

    ``TRP QQ`` comes first in the file and ``ALA QZ`` first in sorted order, which
    is the order the distinct pairs are looked up in.
    """
    columns = {
        "resname": np.array(["ALA", "TRP", "ALA"]),
        "atom": np.array(["CA", "QQ", "QZ"]),
        "chain": np.array(["A", "A", "B"]),
        "resid": np.array([1, 2, 3]),
        "icode": np.array(["", "", ""]),
    }
    with pytest.raises(DensityInputError, match=r"atom 'QQ' of residue TRP 2 in chain 'A'"):
        resolve_radii("pdb2pqr_charmm", **columns)


def test_ver49_2wcd_resolves_every_atom(prepared_2wcd: Prepared2WCD) -> None:
    """Every heavy atom of the vendored 2WCD resolves: ILE CD1 and HIS are its two aliases.

    Design §4: 216 ``ILE CD1`` and 120 ``HIS`` atoms are where 2WCD's names and
    ``CHARMM.DAT``'s differ, and nothing else is.
    """
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents

    group = mda.Universe(str(prepared_2wcd.path)).atoms
    radii = resolve_radii(
        "pdb2pqr_charmm",
        resname=group.resnames,
        atom=group.names,
        chain=group.chainIDs,
        resid=group.resids,
        icode=group.icodes,
    )
    assert radii.radii_nm.size == 26844
    assert int(np.sum((group.resnames == "ILE") & (group.names == "CD1"))) == 216
    assert int(np.sum(group.resnames == "HIS")) == 120
    assert math.isclose(float(radii.radii_nm.max()), 0.2275)
    assert math.isclose(float(radii.radii_nm.min()), 0.170)
