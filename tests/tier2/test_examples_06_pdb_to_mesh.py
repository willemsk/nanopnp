"""VER-46 — example 06, from a PDB entry to a mesh, executed verbatim (FR-01 to FR-10, IF-05).

The README's two blocks run from a copy of ``examples/06-pdb-to-mesh``. The
``refused`` block must exit 4, the gate class: the deposited 2WCD is refused by
stage 1's orientation gate. The ``run`` block prepares the entry with a script
that imports nothing from nanopnp, walks stages 1 to 6, exports what the stages
stored, and meshes the exported profile again as a supplied input (WP25 D3, D8).

Each oracle fails loudly on a frame, unit or substitution error rather than
comparing a number to itself:

- (a) the refusal names the orientation gate with an angle above its limit;
- (b) the walk records exactly the case and stages 1 to 6, and the structure file;
- (c) the aligned export passes stage 1 under ``symmetry.axis: z``;
- (d) ``density.mrc``, read in ångströms as a viewer reads it, boxes every heavy
  atom of ``aligned.pdb``, and reads at least the single-frame bound at each atom's
  nearest node (the WP25 plan, Design §2). A map in nm puts every atom outside a
  box a tenth its size, and one with its axes transposed puts the nearest node of
  most atoms in the lumen or the solvent;
- (e) the exported profile is the stored document, byte for byte, and loads as a
  pipeline profile;
- (f) the profile run moves the region and mesh keys, keeps the mesh content hash,
  and records no stage 1 to 4 artefact.

Nothing is solved, so no stabilisation mode applies. Durations are logged.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path

import numpy as np
import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.geometry.profile import PIPELINE_SOURCE, load_profile
from nanopnp.pipeline.case import load_case
from nanopnp.structure.axis import ORIENTATION_LIMIT_DEG
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

pytestmark = pytest.mark.extended

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]

PDB_ROUNDING_NM = 5e-5
"""Half the PDB coordinate column's 0.001 Å: how far a written atom may lie from the true one."""

STAGES = {"case", "structure", "density", "symmetry", "contour", "region", "mesh"}
"""The artefacts a walk to stage 6 records: the case and stages 1 to 6."""


def _read(path: Path) -> dict[str, object]:
    """Return a record written through ``canonical``, its floats decoded."""
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


def _command(results: list[CommandResult], *words: str) -> CommandResult:
    """Return the one result whose argv begins with ``words``."""
    (found,) = [result for result in results if result.argv[: len(words)] == words]
    return found


@pytest.fixture(scope="module")
def ran(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, list[CommandResult], list[CommandResult]]:
    """Copy the example; run the ``refused`` block, then the ``run`` block."""
    example = copy_example(
        REPOSITORY / "examples" / "06-pdb-to-mesh",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    started = time.perf_counter()
    refused = run_tagged(example, "refused")
    middle = time.perf_counter()
    walked = run_tagged(example, "run")
    logger.info(
        "example 06: refused block %.1f s, run block %.1f s",
        middle - started,
        time.perf_counter() - middle,
    )
    return example, refused, walked


def test_ver46_06_the_deposited_entry_is_refused_by_the_orientation_gate(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(a) Exit 4, naming the gate, an angle above the limit, and the limit (QR-12, FR-02)."""
    _, refused, _ = ran
    (result,) = refused
    assert result.returncode == 4
    assert result.stdout == ""
    found = re.search(
        r"orientation gate: the detected axis is ([\d.]+) degrees from the file's z against a "
        r"limit of ([\d.]+)",
        result.stderr,
    )
    assert found is not None, result.stderr
    angle, limit = float(found.group(1)), float(found.group(2))
    assert limit == ORIENTATION_LIMIT_DEG
    assert angle > limit
    assert "Traceback" not in result.stderr


def test_ver46_06_the_prepared_entry_walks_stages_1_to_6(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(b) Every command exits 0; the manifest keys exactly the case and stages 1 to 6 (FR-27)."""
    example, _, walked = ran
    assert [result.argv[:2] for result in walked] == [
        ("python", "prepare.py"),
        ("nanopnp", "run"),
        ("nanopnp", "stage"),
        ("nanopnp", "stage"),
        ("nanopnp", "stage"),
        ("nanopnp", "stage"),
        ("nanopnp", "stage"),
        ("nanopnp", "run"),
        ("nanopnp", "inspect"),
    ]
    inputs = _read(example / "run" / "manifest.json")["inputs"]
    assert isinstance(inputs, dict)
    assert set(inputs["artefacts"]) == STAGES
    assert Path(inputs["files"]["structure"]["path"]) == Path("2wcd-prepared.pdb")
    assert not any(inputs["artefacts"][name]["hand_substituted"] for name in STAGES)


def test_ver46_06_the_aligned_export_passes_stage_1_under_axis_z(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(c) The PDB stage 1 exported is in its own frame: the file's z is the pore axis (FR-02)."""
    example, _, walked = ran
    assert load_case(example / "aligned.case.yaml").structure.symmetry.axis == "z"  # type: ignore[union-attr]
    result = _command(walked, "nanopnp", "stage", "structure", "aligned.case.yaml")
    assert result.returncode == 0
    exported = _command(walked, "nanopnp", "stage", "structure", "2wcd.case.yaml")
    assert "export   aligned.pdb" in exported.stdout
    assert "export   aligned.dcd" in exported.stdout


def test_ver46_06_the_exported_map_overlays_the_aligned_structure(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(d) Read in Å, the map boxes every heavy atom and reads at least the bound at its node.

    One frame, so the map at a grid node a distance ``d`` from an atom is at least
    that atom's ``exp(-d²/(sigma R)²)``. The node nearest the written atom lies within
    ``√3h/2`` of it, and the written atom within ``√3`` times the PDB's rounding of
    the true one. ``R`` is the smallest shipped radius of any heavy atom in the
    structure, so the bound holds for every atom (the WP25 plan, Design §2; IF-05, §8.2.2 B10).
    """
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    from gridData import Grid

    from nanopnp.density.radii import ANGSTROM_TO_NM, KERNEL_RADII, RadiusSet
    from nanopnp.pipeline.case import resolve

    example, _, _ = ran
    density = resolve(load_case(example / "2wcd.case.yaml")).density
    assert density is not None
    radii = RadiusSet.load(KERNEL_RADII[density.kernel])

    grid = Grid(str(example / "density.mrc"))
    values = np.asarray(grid.grid)
    origin_A = np.asarray(grid.origin, dtype=np.float64)
    delta_A = np.asarray(grid.delta, dtype=np.float64).reshape(-1)[:3]
    h_nm = float(delta_A[0]) * ANGSTROM_TO_NM
    assert h_nm == pytest.approx(density.grid_spacing_nm, rel=1e-6)

    universe = mda.Universe(str(example / "aligned.pdb"))
    heavy = universe.select_atoms("not element H")
    assert len(heavy) > 0
    # Over the heavy atoms present, through the set's own lookup: a residue table
    # names hydrogens that do not start with H (NAD's NH2T), so filtering it by
    # name would take a hydrogen's radius and make the bound vacuous.
    pairs = set(zip(heavy.resnames.tolist(), heavy.names.tolist(), strict=True))
    smallest_nm = ANGSTROM_TO_NM * min(radii.radius_A(resname, atom) for resname, atom in pairs)
    positions_A = heavy.positions.astype(np.float64)
    top_A = origin_A + (np.asarray(values.shape) - 1) * delta_A
    assert np.all(positions_A >= origin_A) and np.all(positions_A <= top_A), (
        "an atom lies outside the map's box: a unit or axis-order error"
    )

    nodes = np.rint((positions_A - origin_A) / delta_A).astype(int)
    at_atoms = values[nodes[:, 0], nodes[:, 1], nodes[:, 2]]
    reach_nm = math.sqrt(3.0) * (h_nm / 2.0 + PDB_ROUNDING_NM)
    bound = math.exp(-((reach_nm / (density.sharpness * smallest_nm)) ** 2))
    logger.info(
        "example 06 overlay: %d heavy atoms, h = %.3f nm, R_min = %.4f nm, bound %.4f, "
        "lowest value at a nearest node %.4f",
        len(heavy),
        h_nm,
        smallest_nm,
        bound,
        float(at_atoms.min()),
    )
    # Design §2's 0.928 at h = 0.05 nm: a bound near zero would pass any map.
    assert bound > 0.9
    assert float(at_atoms.min()) >= bound


def test_ver46_06_the_exported_profile_is_the_stored_document(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(e) Byte for byte the store's ``profile/v1`` document, and a pipeline profile (FR-09)."""
    example, _, walked = ran
    result = _command(walked, "nanopnp", "stage", "contour")
    (stored,) = [
        line.split(maxsplit=2)[2]
        for line in result.stdout.splitlines()
        if line.startswith("payload")
    ]
    exported = example / "contour.profile.yaml"
    assert exported.read_bytes() == Path(stored).read_bytes()
    assert load_profile(exported).provenance.source == PIPELINE_SOURCE


def test_ver46_06_the_profile_meshes_to_the_same_mesh_under_another_key(
    ran: tuple[Path, list[CommandResult], list[CommandResult]],
) -> None:
    """(f) A supplied profile skips stages 1 to 4; the mesh is the same, its key is not."""
    example, _, walked = ran
    structure = _read(example / "run" / "manifest.json")
    profile = _read(example / "run-profile" / "manifest.json")
    left, right = structure["inputs"], profile["inputs"]
    assert isinstance(left, dict) and isinstance(right, dict)
    assert set(right["artefacts"]) == {"case", "region", "mesh"}
    assert Path(right["files"]["profile"]["path"]) == Path("contour.profile.yaml")
    for name in ("region", "mesh"):
        assert right["artefacts"][name]["hash"] != left["artefacts"][name]["hash"], name
    meshes = structure["geometry_and_mesh"], profile["geometry_and_mesh"]
    assert meshes[0]["content_hash"] == meshes[1]["content_hash"]  # type: ignore[index]
    assert "run-profile" in _command(walked, "nanopnp", "inspect").stdout
