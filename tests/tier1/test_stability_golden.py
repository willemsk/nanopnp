"""VER-62: the number-stability comparison asks the right question of each mesh.

On a recorded mesh the golden holds round-off; on an unseen mesh it holds the
walk's measured mesh-moved tolerance, except in the reference environment, where
an unseen mesh fails. These run the comparison on synthetic goldens, so a
regression in the classification shows at Tier 1 rather than as a CI leg that
passes while checking nothing (WP35 D13, as amended; section 8.2.7 G10).
"""

from __future__ import annotations

import pytest

from nanopnp.validation.stability import (
    CEILING,
    REFERENCE_ENVIRONMENT,
    SAFETY_FACTOR,
    SAME_MESH_TOLERANCE,
    FoldError,
    StabilityGolden,
    compare,
    fold,
)

MESH_A = "a" * 64
MESH_B = "b" * 64
MESH_C = "c" * 64
ELSEWHERE = "darwin-arm64/ASIMDHP"


def _record(mesh: str, current: float, where: str, walk: str = "walk") -> dict[str, object]:
    return {
        "schema": "nanopnp/golden/stability/v2",
        "walk": walk,
        "mesh_hash": mesh,
        "environment": where,
        "values": {"current_A": current.hex(), "q_mesh_e": (-60.0).hex()},
    }


def _golden(*records: dict[str, object]) -> StabilityGolden:
    golden = StabilityGolden.empty()
    for record in records:
        golden = fold(golden, record)
    return golden


def _values(current: float) -> dict[str, float]:
    return {"current_A": current, "q_mesh_e": -60.0}


def test_ver62_a_recorded_mesh_holds_round_off() -> None:
    golden = _golden(_record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT))
    same = compare(golden, "walk", MESH_A, _values(1.0e-10 * (1 + 1e-9)), REFERENCE_ENVIRONMENT)
    assert same.mode == "same-mesh" and same.failure is None
    assert same.tolerance == SAME_MESH_TOLERANCE
    moved = compare(golden, "walk", MESH_A, _values(1.0e-10 * (1 + 1e-7)), ELSEWHERE)
    assert moved.mode == "same-mesh" and moved.failure is not None
    assert "a change moved a number" in moved.failure


def test_ver62_one_recorded_mesh_argues_no_mesh_moved_tolerance() -> None:
    golden = _golden(_record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT))
    assert golden.walks["walk"].moved_tolerance is None
    verdict = compare(golden, "walk", MESH_B, _values(1.0e-10), ELSEWHERE)
    assert verdict.mode == "missing" and verdict.failure is not None
    assert '"environment": "darwin-arm64/ASIMDHP"' in verdict.failure


def test_ver62_mesh_moved_tolerance_is_the_safety_factor_on_the_spread() -> None:
    golden = _golden(
        _record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT),
        _record(MESH_B, 1.0e-10 * (1 + 2e-5), ELSEWHERE),
    )
    walk = golden.walks["walk"]
    assert walk.reference_mesh == MESH_A
    assert walk.moved_tolerance == pytest.approx(SAFETY_FACTOR * 2e-5, rel=1e-6)
    inside = compare(golden, "walk", MESH_C, _values(1.0e-10 * (1 - 1e-4)), "win32-AMD64/X86_V3")
    assert inside.mode == "mesh-moved" and inside.failure is None
    outside = compare(golden, "walk", MESH_C, _values(1.0e-10 * (1 + 5e-4)), "win32-AMD64/X86_V3")
    assert outside.failure is not None and "unseen mesh" in outside.failure


def test_ver62_the_reference_environment_refuses_an_unseen_mesh() -> None:
    """There a mesh move is a code change, so it never falls back to the mesh-moved band."""
    golden = _golden(
        _record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT),
        _record(MESH_B, 1.0e-10 * (1 + 2e-5), ELSEWHERE),
    )
    verdict = compare(golden, "walk", MESH_C, _values(1.0e-10), REFERENCE_ENVIRONMENT)
    assert verdict.mode == "missing" and verdict.failure is not None
    assert "reference environment" in verdict.failure


def test_ver62_a_fold_from_the_reference_environment_becomes_the_reference_mesh() -> None:
    golden = _golden(
        _record(MESH_B, 1.0e-10, ELSEWHERE),
        _record(MESH_A, 1.0e-10 * (1 + 1e-6), REFERENCE_ENVIRONMENT),
    )
    assert golden.walks["walk"].reference_mesh == MESH_A


def test_ver62_fold_refuses_a_tolerance_above_the_ceiling() -> None:
    golden = _golden(_record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT))
    drift = 2 * CEILING / SAFETY_FACTOR
    with pytest.raises(FoldError, match="above the ceiling"):
        fold(golden, _record(MESH_B, 1.0e-10 * (1 + drift), ELSEWHERE))


def test_ver62_fold_refuses_to_overwrite_or_to_hold_zero() -> None:
    golden = _golden(_record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT))
    with pytest.raises(FoldError, match="--replace"):
        fold(golden, _record(MESH_A, 2.0e-10, REFERENCE_ENVIRONMENT))
    repinned = fold(golden, _record(MESH_A, 2.0e-10, REFERENCE_ENVIRONMENT), replace=True)
    assert repinned.walks["walk"].meshes[MESH_A].floats()["current_A"] == 2.0e-10
    with pytest.raises(FoldError, match="zero"):
        fold(golden, _record(MESH_B, 0.0, ELSEWHERE))


def test_ver62_a_known_mesh_gains_the_environment_that_deployed_it() -> None:
    """Round-off between environments on one mesh folds in; the first values stay."""
    golden = _golden(
        _record(MESH_A, 1.0e-10, REFERENCE_ENVIRONMENT),
        _record(MESH_A, 1.0e-10 * (1 + 1e-13), ELSEWHERE),
    )
    entry = golden.walks["walk"].meshes[MESH_A]
    assert entry.seen_on == sorted([REFERENCE_ENVIRONMENT, ELSEWHERE])
    assert entry.floats()["current_A"] == 1.0e-10
    assert golden.walks["walk"].moved_tolerance is None
