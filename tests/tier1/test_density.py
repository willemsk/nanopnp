"""VER-49: stage 2, the density map: union, grid, radii, artefact and walk."""

from __future__ import annotations

import logging
import math
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
import yaml

from nanopnp import Case, Session
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
from nanopnp.io.artefact import CASE_SCHEMA, StageInputs
from nanopnp.io.case import CaseValidationError
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, loads_case, resolve
from nanopnp.pipeline.run import selected_stages

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)

# Coarsest spacing admitted: SPECIFICATION.md FR-04.
H = 0.05

# CHARMM C-alpha radius, 2.275 Å.
CA_WIDTH_NM = 0.93 * 0.2275


def _nodes(grid: DensityGrid) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return np.meshgrid(grid.axis_nm("z"), grid.axis_nm("y"), grid.axis_nm("x"), indexing="ij")


def _gaussian(grid: DensityGrid, centre: np.ndarray, width: float) -> np.ndarray:
    z, y, x = _nodes(grid)
    squared = (x - centre[0]) ** 2 + (y - centre[1]) ** 2 + (z - centre[2]) ** 2
    return np.exp(-squared / width**2)


def _kept(g: np.ndarray) -> np.ndarray:
    return np.where(g >= EPSILON, g, 0.0)


def _case(
    tmp_path: Path, pdb: Path, *, geometry: str = "", inputs: str = "", atoms: str = "as_loaded"
) -> Path:
    block = yaml.safe_load(geometry) if geometry else {"geometry": {}}
    block["geometry"].setdefault("density", {}).setdefault("atoms", atoms)
    geometry = yaml.safe_dump(block, default_flow_style=None)
    text = (
        f"schema: {CASE_SCHEMA}\n"
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


def test_ver49_closed_forms() -> None:
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


# QR-12
def test_ver49_union_is_bounded() -> None:
    rng = np.random.default_rng(49)
    positions = rng.uniform(-1.5, 1.5, (1, 500, 3))
    positions[0, :10] = [0.1, -0.2, 0.3]
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
    assert error.max() > 0.0


def test_ver49_slab_thickness_does_not_change_the_map(monkeypatch: pytest.MonkeyPatch) -> None:
    import nanopnp.density.union as union

    rng = np.random.default_rng(8)
    positions = rng.uniform(-0.9, 0.9, (2, 150, 3))
    widths = 0.93 * rng.choice([0.17, 0.185, 0.2, 0.2275, 0.132], 150)
    grid = canonical_grid(positions, widths, H)
    monkeypatch.setattr(union, "SLAB_CELLS", grid.n * grid.n)
    thin = deposit(positions, widths, grid, float64=True)
    monkeypatch.setattr(union, "SLAB_CELLS", grid.n * grid.n * grid.nz)
    whole = deposit(positions, widths, grid, float64=True)
    assert thin.max() > 0.5
    assert np.max(np.abs(thin - whole)) <= 1e-14


def test_ver49_frames_average_not_union() -> None:
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


@pytest.mark.parametrize(
    ("residue", "atom", "radius"),
    [
        ("ALA", "CA", 2.275),
        ("HID", "ND1", 1.85),
        ("HIS", "CA", 2.275),
        ("HIS", "HD1", 0.2245),
        ("ILE", "CD1", 2.06),
        ("ALA", "OXT", 1.70),
        ("GLU", "HT1", 0.2245),
        ("HSE", "HT1", 0.2245),
        ("PRO", "HN1", 0.2245),
        ("GLY", "HT2", 0.2245),
    ],
)
def test_ver49_radius_lookup(residue: str, atom: str, radius: float) -> None:
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


# VER-29, IF-05, FR-27
def test_ver49_map_round_trip_and_export(synthetic_c12: Path, tmp_path: Path) -> None:
    case = _case(tmp_path, synthetic_c12)
    store = Store(tmp_path / "store")
    result = Session(store, write=False).run(Case.load(case), upto="density")
    artefact = result.artefacts["density"]
    density = DensityMap.read(artefact.payload["density"])
    assert density.digest() == artefact.summary["payload_digest"]
    assert density.header["hydrogens"] == 0
    assert density.header["atoms"]["by_element"] == {"C": 288, "N": 96, "O": 96}
    assert density.header["radius_set"]["name"] == "pdb2pqr_charmm"
    again = DensityMap.read(density.write(tmp_path / "copy.npz"))
    assert again.digest() == density.digest()

    from gridData import Grid

    h = density.grid.spacing_nm
    x0, y0, z0 = density.grid.origin_nm
    for suffix, tolerance, header_A in (
        (".dx", 5e-7 + 2.0**-24, 5e-6),
        (".ccp4", 0.0, 5e-5),
        (".mrc", 0.0, 5e-5),
        (".map", 0.0, 5e-5),
    ):
        path = density.export(tmp_path / f"map{suffix}")
        header = Grid(str(path), file_format="DX" if suffix == ".dx" else "MRC")
        assert np.allclose(header.delta, 10.0 * h, rtol=0.0, atol=header_A)
        assert np.allclose(header.origin, 10.0 * np.asarray((x0, y0, z0)), rtol=0.0, atol=header_A)
        exported = DensityMap.read(path)
        assert exported.grid == density.grid
        assert np.max(np.abs(exported.values - density.values)) <= tolerance
    with pytest.raises(GridFormatError, match=r"\.npz, \.dx, \.ccp4"):
        density.export(tmp_path / "map.vtk")
    raw = np.transpose(density.values, (2, 1, 0))[:5, :5, :5]
    for origin in ((x0 - h / 2, y0 - h / 2, z0), (x0, y0, z0 + 0.013)):
        off = tmp_path / "off-lattice.dx"
        Grid(
            grid=raw, origin=tuple(10.0 * value for value in origin), delta=(10.0 * h,) * 3
        ).export(str(off), file_format="DX")
        with pytest.raises(GridFormatError, match=r"integer multiples of it"):
            DensityMap.read(off)

    script = (
        "from nanopnp.core.stages import create\n"
        "from nanopnp import Case, Session\n"
        "from nanopnp.io.store import Store\n"
        f"result = Session(Store({str(tmp_path / 'store')!r}), write=False).run("
        f"Case.load({str(case)!r}), upto='density')\n"
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
    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs

    def key(geometry: str) -> str:
        case = load_case(_case(tmp_path, synthetic_c12, geometry=geometry))
        structure = create("structure").key(StageInputs(resolved=resolve(case)))  # type: ignore[attr-defined]
        inputs = StageInputs(resolved=resolve(case), upstream={"structure": structure})
        return str(create("density").key(inputs).hash)  # type: ignore[attr-defined]

    base = key("")
    assert key("geometry: {density: {grid_spacing_nm: 0.05, sharpness: 0.93}}\n") == base
    assert key("geometry: {density: {grid_spacing_nm: 0.04}}\n") != base
    assert key("geometry: {density: {sharpness: 0.9}}\n") != base


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
    case = _case(tmp_path, synthetic_c12, geometry=f"geometry: {{density: {geometry}}}\n")
    with pytest.raises(CaseValidationError, match=message):
        resolve(load_case(case))


def test_ver49_resolution_and_walk_rules(synthetic_c12: Path, tmp_path: Path) -> None:
    from nanopnp.sweep.plan import plan_from_document

    case = _case(tmp_path, synthetic_c12, geometry="geometry: {membrane: {thickness_nm: 2.8}}\n")
    store = Store(tmp_path / "store")
    ran = Session(store, write=False).run(Case.load(case), upto="symmetry")
    assert [record.name for record in ran.stages] == ["case", "structure", "density", "symmetry"]
    group = ran.manifest.geometry_and_mesh
    assert {"structure", "density", "reduction"} <= set(group)
    assert group["density"]["radius_set"]["name"] == "pdb2pqr_charmm"  # type: ignore[index]
    assert group["reduction"]["n"] == 12  # type: ignore[index]

    assert selected_stages(resolve(load_case(case)), None) == (
        "case",
        "structure",
        "protonation",
        "density",
        "symmetry",
        "contour",
        "region",
        "mesh",
        "charge",
        "materials",
        "solve",
        "qoi",
        "report",
    )
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v0.5\n"
        "name: density-sweep\n"
        f"base: {case}\n"
        "axes:\n"
        "  - {name: bias, path: boundary_conditions.bias_V, values: [0.05, 0.1]}\n",
        encoding="utf-8",
    )
    assert len(plan_from_document(sweep).points) == 2

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
    with pytest.raises(CaseValidationError, match=r"neither inputs\.mesh nor inputs\.profile"):
        resolve(load_case(alone))


def test_ver49_a_bad_atom_aborts_stage_two_naming_it(synthetic_c12: Path, tmp_path: Path) -> None:
    lines = synthetic_c12.read_text(encoding="utf-8").splitlines()
    lines[44] = lines[44][:12] + "CG  " + lines[44][16:]
    pdb = tmp_path / "bad.pdb"
    pdb.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(DensityInputError, match=r"atom 'CG' of residue ALA 1 in chain 'B'"):
        Session(Store(tmp_path / "store")).run(Case.load(_case(tmp_path, pdb)), upto="density")


def test_ver49_radius_refusal_names_the_first_atom_in_file_order() -> None:
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


# IF-05
def test_ver49_nm_written_map_is_refused(tmp_path: Path) -> None:
    from gridData import Grid

    spacing_nm = 0.05
    raw = np.ones((5, 5, 5))
    for suffix, file_format in ((".dx", "DX"), (".ccp4", "MRC")):
        path = tmp_path / f"in-nm{suffix}"
        Grid(grid=raw, origin=(-0.1,) * 3, delta=(spacing_nm,) * 3).export(
            str(path), file_format=file_format
        )
        with pytest.raises(GridFormatError, match=r"written in angstroms.*nm reads ten times"):
            DensityMap.read(path)


FRAGMENT = (18, 26)


def _fragment_case(tmp_path: Path, atoms: str, charge: str = "ph: 8.0") -> object:
    text = (
        f"schema: {CASE_SCHEMA}\n"
        "name: fragment\n"
        f"structure:\n  source: {{path: {tmp_path / 'fragment.pdb'}}}\n"
        "  symmetry: {point_group: C1, axis: z}\n"
        f"geometry: {{density: {{atoms: {atoms}}}}}\n"
        f"charge: {{{charge}}}\n"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.15\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.05, ground: cis}\n"
        "physics: {model: epnp-ns, solid_permittivities: {protein: 20.0, membrane: 3.2}}\n"
    )
    return resolve(loads_case(text))


def _protonated_fragment(
    tmp_path: Path, fragment_2wcd: object, ph: float
) -> tuple[object, object, object]:
    pytest.importorskip("pdb2pqr", reason="the structure extra carries PDB2PQR")
    from nanopnp.charge.protonation import ProtonationStage
    from nanopnp.io.artefact import StructureArtefact
    from nanopnp.structure.protonated import ProtonationTable

    ensemble = fragment_2wcd(*FRAGMENT)  # type: ignore[operator]
    path = ensemble.write(tmp_path / "ensemble.npz")
    structure = StructureArtefact(
        parameters={"ensemble": ensemble.digest()}, payload={"ensemble": path}
    )
    resolved = _fragment_case(tmp_path, "protonated", charge=f"ph: {ph}")
    protonation = ProtonationStage(workspace=tmp_path / "workspace").run(
        StageInputs(resolved=resolved, upstream={"structure": structure})  # type: ignore[arg-type]
    )
    table = ProtonationTable.read(protonation.payload["protonation"])
    return structure, protonation, table


def _density_stage(
    tmp_path: Path,
    atoms: str,
    structure: object,
    protonation: object | None,
    charge: str = "ph: 8.0",
) -> tuple[Any, StageInputs]:
    from nanopnp.density.stage import DensityStage

    upstream = {"structure": structure}
    if protonation is not None:
        upstream["protonation"] = protonation
    resolved = _fragment_case(tmp_path, atoms, charge=charge)
    inputs = StageInputs(resolved=resolved, upstream=upstream)  # type: ignore[arg-type]
    stage = DensityStage(workspace=tmp_path / f"density-{atoms}")
    return stage, inputs


def test_ver49_a_changed_protonation_state_moves_the_density(
    tmp_path: Path, fragment_2wcd: object
) -> None:
    """A protonation state the density ignores would leave the contour and mesh stale."""
    runs = {}
    for ph in (2.0, 8.0):
        structure, protonation, _ = _protonated_fragment(tmp_path / f"ph{ph}", fragment_2wcd, ph)
        runs[ph] = (structure, protonation)
    maps = {}
    keys = {}
    for atoms in ("protonated", "as_loaded"):
        for ph, (structure, protonation) in runs.items():
            stage, inputs = _density_stage(
                tmp_path / f"{atoms}-{ph}", atoms, structure, protonation
            )
            keys[atoms, ph] = stage.key(inputs)
            artefact = stage.run(inputs)
            maps[atoms, ph] = DensityMap.read(artefact.payload["density"])
    assert keys["protonated", 2.0].hash != keys["protonated", 8.0].hash
    assert keys["protonated", 8.0].parameters["atoms"] == "protonated"
    assert maps["protonated", 2.0].grid == maps["protonated", 8.0].grid
    difference = np.abs(maps["protonated", 2.0].values - maps["protonated", 8.0].values)
    assert float(difference.max()) > 1e-3

    assert keys["as_loaded", 2.0].hash == keys["as_loaded", 8.0].hash
    assert "atoms" not in keys["as_loaded", 2.0].parameters
    assert set(keys["as_loaded", 2.0].inputs) == {"structure"}
    structure = runs[8.0][0]
    stage, inputs = _density_stage(tmp_path / "bare", "as_loaded", structure, None)
    assert stage.key(inputs).hash == keys["as_loaded", 8.0].hash
    assert np.array_equal(maps["as_loaded", 2.0].values, maps["as_loaded", 8.0].values)


def test_ver49_protonated_radii_are_pdb2pqr_charmm_radii(
    tmp_path: Path, fragment_2wcd: object
) -> None:
    """A radius looked up by the parent residue's name would give a state's new proton none."""
    from nanopnp.density.radii import resolve_protonated_radii

    for ph in (2.0, 8.0):
        _, _, table = _protonated_fragment(tmp_path / f"ph{ph}", fragment_2wcd, ph)
        radii = resolve_protonated_radii("pdb2pqr_charmm", table)  # type: ignore[arg-type]
        np.testing.assert_allclose(
            radii.radii_nm,
            table.radius_nm,  # type: ignore[attr-defined]
            rtol=0.0,
            atol=1e-12,
        )
        if ph == 2.0:
            names = list(zip(table.resid.tolist(), table.name.tolist(), strict=True))  # type: ignore[attr-defined]
            assert (18, "HE2") in names
            assert (21, "HD2") in names


def test_ver49_the_protonated_map_deposits_the_tables_atoms(
    tmp_path: Path, fragment_2wcd: object
) -> None:
    """A map built from stage 1's atoms beside the table's key would pass every key check."""
    from nanopnp.density.radii import resolve_protonated_radii

    structure, protonation, table = _protonated_fragment(tmp_path / "ph", fragment_2wcd, 2.0)
    stage, inputs = _density_stage(tmp_path / "run", "protonated", structure, protonation)
    artefact = stage.run(inputs)
    stored = DensityMap.read(artefact.payload["density"])
    spec = inputs.resolved.density  # type: ignore[attr-defined]
    radii = resolve_protonated_radii("pdb2pqr_charmm", table)  # type: ignore[arg-type]
    frames = [table.positions_nm[table.frame_slice(f)] for f in range(table.frames)]  # type: ignore[attr-defined]
    widths = [spec.sharpness * radii.radii_nm[table.frame_slice(f)] for f in range(table.frames)]  # type: ignore[attr-defined]
    grid = canonical_grid(frames, widths, spec.grid_spacing_nm)
    assert grid == stored.grid
    assert np.array_equal(deposit(frames, widths, grid), stored.values)


def test_fr38_a_radius_scale_moves_the_density_and_the_kernel_width(
    tmp_path: Path, fragment_2wcd: object
) -> None:
    """A radius edit the density ignores would change the table and leave the contour unchanged."""
    from nanopnp.structure.protonated import ProtonationTable

    edit = "ph: 8.0, edits: [{residue: 'LEU 24', radius_scale: 1.2}]"
    parent = _protonated_fragment(tmp_path / "parent", fragment_2wcd, 8.0)
    pinned = _fragment_case(tmp_path / "edited", "protonated", charge=edit)
    assert pinned.protonation.edits  # type: ignore[attr-defined]
    structure = parent[0]
    from nanopnp.charge.protonation import ProtonationStage

    edited = ProtonationStage(workspace=tmp_path / "edited-workspace").run(
        StageInputs(resolved=pinned, upstream={"structure": structure})  # type: ignore[arg-type]
    )
    variant = ProtonationTable.read(edited.payload["protonation"])
    table = parent[2]
    leu = (variant.resid == 24) & (variant.resname.astype(str) == "LEU")  # type: ignore[attr-defined]
    assert leu.any()
    expected = np.where(leu, 1.2, 1.0) * table.radius_nm  # type: ignore[attr-defined]
    np.testing.assert_allclose(variant.radius_nm, expected, rtol=0.0, atol=1e-12)  # type: ignore[attr-defined]

    maps, keys = {}, {}
    for atoms in ("protonated", "as_loaded"):
        for label, charge, protonation in (
            ("parent", "ph: 8.0", parent[1]),
            ("edited", edit, edited),
        ):
            stage, inputs = _density_stage(
                tmp_path / f"{atoms}-{label}", atoms, structure, protonation, charge
            )
            keys[atoms, label] = stage.key(inputs)
            maps[atoms, label] = DensityMap.read(stage.run(inputs).payload["density"])
    assert keys["protonated", "parent"].hash != keys["protonated", "edited"].hash
    # A wider kernel on LEU 24 widens the grid's margin, so the two maps are not the same shape.
    assert maps["protonated", "parent"].grid != maps["protonated", "edited"].grid
    assert (
        maps["protonated", "parent"].header["radius_range_nm"][1]
        < (maps["protonated", "edited"].header["radius_range_nm"][1])
    )

    # The deposit from the table's own edited radii is the third route to the stage's widths.
    spec = inputs.resolved.density  # type: ignore[attr-defined]
    frames = [variant.positions_nm[variant.frame_slice(f)] for f in range(variant.frames)]  # type: ignore[attr-defined]
    widths = [
        spec.sharpness * variant.radius_nm[variant.frame_slice(f)] for f in range(variant.frames)
    ]  # type: ignore[attr-defined]
    grid = canonical_grid(frames, widths, spec.grid_spacing_nm)
    stored = maps["protonated", "edited"]
    assert grid == stored.grid
    assert np.array_equal(deposit(frames, widths, grid), stored.values)
    assert stored.header["radius_range_nm"][1] == pytest.approx(
        float(variant.radius_nm.max()), abs=1e-12
    )  # type: ignore[attr-defined]

    assert keys["as_loaded", "parent"].hash == keys["as_loaded", "edited"].hash
    assert np.array_equal(maps["as_loaded", "parent"].values, maps["as_loaded", "edited"].values)


def test_ver49_ragged_frames_deposit_as_the_stacked_call() -> None:
    """The ragged route must keep the uniform route's arithmetic, or as-loaded maps would move."""
    rng = np.random.default_rng(3)
    positions = rng.uniform(-1.0, 1.0, (2, 40, 3))
    widths = rng.uniform(0.1, 0.2, 40)
    grid = canonical_grid(positions, widths, 0.05)
    stacked = deposit(positions, widths, grid)
    ragged = deposit(list(positions), [widths, widths], grid)
    assert np.array_equal(stacked, ragged)
    assert canonical_grid(list(positions), [widths, widths], 0.05) == grid


def test_ver49_a_disulfide_cysteine_takes_the_disu_radii() -> None:
    """A CYS holding 1SG, looked up by its parent name alone, would be refused under the default."""
    from nanopnp.density.radii import RadiusSet, resolve_protonated_radii
    from nanopnp.structure.protonated import ProtonationTable

    empty = np.zeros(0)
    table = ProtonationTable(
        frame_offsets=np.array([0, 3]),
        positions_nm=np.zeros((3, 3)),
        charge_e=np.zeros(3),
        radius_nm=np.zeros(3),
        name=np.array(["1CB", "1SG", "HB1"]),
        resname=np.array(["CYS"] * 3),
        chain=np.array(["A"] * 3),
        resid=np.array([5] * 3),
        icode=np.array([""] * 3),
        residue_chain=np.array(["A"]),
        residue_resid=np.array([5]),
        residue_icode=np.array([""]),
        residue_name=np.array(["CYS"]),
        residue_charge_e=np.zeros(1),
        tautomer=np.array([[""]]),
        expected_charge_e=np.zeros((1, 1)),
        unapplied=empty,
        group_residue=empty,
        group_type=empty,
        group_label=empty,
        group_pka=empty,
        header={},
    )
    radii = resolve_protonated_radii("pdb2pqr_charmm", table)
    cysteine = RadiusSet.load("pdb2pqr_charmm").radius_A("CYS", "HB1")
    np.testing.assert_allclose(radii.radii_nm, np.array([2.175, 1.975, cysteine]) * 0.1, atol=1e-12)
