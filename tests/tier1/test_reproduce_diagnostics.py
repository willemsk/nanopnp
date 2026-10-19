"""Stage-key invariants of the shared test fixtures."""

from __future__ import annotations

from pathlib import Path


def _load_root_conftest() -> object:
    import sys

    return sys.modules["tests.conftest"]


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
