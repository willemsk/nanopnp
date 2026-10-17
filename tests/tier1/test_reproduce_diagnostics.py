"""VER-35, QR-12: the reproduction check names a moved input by its path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.pipeline.reproduce import (
    InputMovedError,
    check_inputs,
)

# On Windows the path separator supplies the backslash ``repr`` would double; on
# POSIX a backslash in the file name does, and is a legal name there.
AWKWARD_NAME = "mesh.vol" if os.name == "nt" else "back\\slash.vol"


def _manifest(path: Path, *, sha256: str) -> dict[str, Canonicalisable]:
    return {"inputs": {"files": {"mesh": {"path": str(path), "sha256": sha256}}}}


def test_ver35_a_moved_input_is_named_by_its_path_not_its_repr(tmp_path: Path) -> None:
    mesh = tmp_path / AWKWARD_NAME
    mesh.write_bytes(b"original\n")
    manifest = _manifest(mesh, sha256=file_hash(mesh))
    mesh.write_bytes(b"edited\n")

    with pytest.raises(InputMovedError) as moved:
        check_inputs(manifest, where=tmp_path)

    assert str(mesh) in str(moved.value)
    assert repr(str(mesh)) not in str(moved.value)
    assert "sha256" in str(moved.value)


def test_ver35_an_absent_input_is_named_by_its_path_not_its_repr(tmp_path: Path) -> None:
    mesh = tmp_path / AWKWARD_NAME
    mesh.write_bytes(b"original\n")
    manifest = _manifest(mesh, sha256=file_hash(mesh))
    mesh.unlink()

    with pytest.raises(InputMovedError) as moved:
        check_inputs(manifest, where=tmp_path)

    assert str(mesh) in str(moved.value)
    assert "is gone" in str(moved.value)


def _load_root_conftest() -> object:
    import sys

    return sys.modules["tests.conftest"]


def test_charged_tube_fixture_defaults_and_gaussian_peak_shift(tmp_path: Path) -> None:
    root_conftest = _load_root_conftest()
    case = root_conftest.write_charged_tube(tmp_path / "tube")  # type: ignore[attr-defined]
    assert "size_scale: 5.0" in case.read_text(encoding="utf-8")
    width_nm = 0.5 * (root_conftest.CHARGED_TUBE_RADIUS_A * 0.1)  # type: ignore[attr-defined]
    assert width_nm == pytest.approx(0.075)
    radii_nm = [
        (x**2 + y**2) ** 0.5 * 0.1
        for _, x, y, _, _ in root_conftest.CHARGED_TUBE_ATOMS  # type: ignore[attr-defined]
    ]
    assert min(radii_nm) == pytest.approx(3.25)
    assert max(width_nm**2 / (2.0 * r_nm) for r_nm in radii_nm) < 0.001


def test_conftest_seed_and_stability_invariants(tmp_path: Path) -> None:
    import inspect

    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs
    from nanopnp.pipeline.case import loads_case, resolve

    root_conftest = _load_root_conftest()
    assert "mesh.pickle" in inspect.getsource(root_conftest.clya_reference_mesh)  # type: ignore[attr-defined]
    assert "route_agreement" not in root_conftest.STABILITY_QUANTITIES  # type: ignore[attr-defined]
    extracted = root_conftest.stability_values(  # type: ignore[attr-defined]
        {
            "current_A": 1.0e-9,
            "currents_A": {"Na+": 6.0e-10, "Cl-": 4.0e-10},
            "conductance_S": 1.0e-8,
            "transport_number": 0.6,
            "eof_m3_s": 1.0e-20,
            "route_agreement": {"relative_difference": 1.0e-6},
        }
    )
    assert "route_agreement" not in extracted
    pdb = tmp_path / "stub.pdb"
    pdb.write_text("END\n", encoding="utf-8")
    base_text = root_conftest.SEED_CASE.format(pdb=pdb)  # type: ignore[attr-defined]
    base_resolved = resolve(loads_case(base_text))
    moved_electrolyte = resolve(
        loads_case(base_text.replace("concentration_M: 0.15", "concentration_M: 1.0"))
    )
    moved_symmetry = resolve(loads_case(base_text.replace("point_group: C12", "point_group: C8")))

    def _stage3_hash(resolved: object) -> str:
        s1 = create("structure").key(StageInputs(resolved=resolved))  # type: ignore[arg-type]
        s2 = create("density").key(StageInputs(resolved=resolved, upstream={"structure": s1}))  # type: ignore[arg-type]
        s3 = create("symmetry").key(StageInputs(resolved=resolved, upstream={"density": s2}))  # type: ignore[arg-type]
        return s3.hash

    assert _stage3_hash(base_resolved) == _stage3_hash(moved_electrolyte)
    assert _stage3_hash(base_resolved) != _stage3_hash(moved_symmetry)


def test_comsol_archive_layout_matches_export_contract() -> None:
    from nanopnp.validation.comsol import ARCHIVE_NAME

    root = Path(__file__).resolve().parents[2]
    tier3_text = (root / "tests/tier3/test_comsol_comparison.py").read_text(encoding="utf-8")
    assert 'ARCHIVE_SUBDIR = "comsol"' in tier3_text
    assert ARCHIVE_NAME == "golden.npz"
    contract = (root / "docs/validation/comsol-export-contract.md").read_text(encoding="utf-8")
    assert "golden.npz" in contract
