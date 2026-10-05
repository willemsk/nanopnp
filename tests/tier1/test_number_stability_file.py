"""VER-62: the number-stability golden file is well formed and every walk in it is asserted.

The golden itself is asserted inside the seven gated walks (``tests/tier2``), which
run only under ``--extended``. This file checks, at Tier 1, what would let one of
those assertions pass while checking nothing: a walk in the golden that no test
asserts, a walk asserted twice, a value of zero (whose relative drift is
undefined), meshes of one walk holding different quantities, or a mesh-moved
tolerance that is not the one its recorded meshes argue, or exceeds the ceiling
(WP35 D13, as amended).
"""

from __future__ import annotations

import ast
import math
import re
from collections import Counter
from pathlib import Path

from nanopnp.validation import stability
from nanopnp.validation.stability import StabilityGolden

TESTS = Path(__file__).resolve().parents[1]
GOLDEN = TESTS / "tier2" / "data" / "number_stability.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ENVIRONMENT = re.compile(r"^[a-z0-9]+-[A-Za-z0-9_]+/[A-Za-z0-9_]+$")


def _golden() -> StabilityGolden:
    return StabilityGolden.read(GOLDEN)


def _asserted_walks() -> Counter[str]:
    """Count each ``number_stability("<walk>", ...)`` call in ``tests/tier2``."""
    found: Counter[str] = Counter()
    for path in sorted((TESTS / "tier2").glob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "number_stability"
            ):
                first = node.args[0] if node.args else None
                assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
                    f"{path.name}:{node.lineno}: number_stability's walk must be a literal"
                )
                found[first.value] += 1
    return found


def test_ver62_golden_holds_the_module_constants() -> None:
    """The file's tolerances are the module's, so neither can move without the other."""
    golden = _golden()
    assert golden.same_mesh_tolerance == stability.SAME_MESH_TOLERANCE == 1e-8
    assert golden.safety_factor == stability.SAFETY_FACTOR
    assert golden.ceiling == stability.CEILING
    assert golden.reference_environment == stability.REFERENCE_ENVIRONMENT
    assert golden.walks


def test_ver62_every_mesh_is_well_formed() -> None:
    for walk, record in _golden().walks.items():
        assert record.reference_mesh in record.meshes, walk
        for mesh_hash, entry in record.meshes.items():
            assert SHA256.match(mesh_hash), (walk, mesh_hash)
            assert entry.values, (walk, mesh_hash)
            assert entry.seen_on, (walk, mesh_hash)
            assert all(ENVIRONMENT.match(where) for where in entry.seen_on), entry.seen_on
            for quantity, value in entry.floats().items():
                assert math.isfinite(value), (walk, quantity)


def test_ver62_every_walk_has_a_reference_mesh_from_the_reference_environment() -> None:
    """An unseen mesh is held against the mesh CI's pinned leg deploys."""
    golden = _golden()
    for walk, record in golden.walks.items():
        seen = record.meshes[record.reference_mesh].seen_on
        assert golden.reference_environment in seen, (walk, seen)


def test_ver62_every_golden_walk_is_asserted_by_exactly_one_test() -> None:
    asserted = _asserted_walks()
    assert all(count == 1 for count in asserted.values()), asserted
    walks = set(_golden().walks)
    assert walks == set(asserted), sorted(walks ^ set(asserted))


def test_ver62_no_golden_value_is_zero() -> None:
    zeros = [
        (walk, mesh_hash, quantity)
        for walk, record in _golden().walks.items()
        for mesh_hash, entry in record.meshes.items()
        for quantity, value in entry.floats().items()
        if value == 0.0
    ]
    assert not zeros


def test_ver62_every_mesh_of_a_walk_holds_the_same_quantities() -> None:
    for walk, record in _golden().walks.items():
        shapes = {mesh_hash: sorted(entry.values) for mesh_hash, entry in record.meshes.items()}
        assert len({tuple(shape) for shape in shapes.values()}) == 1, (walk, shapes)


def test_ver62_mesh_moved_tolerance_is_derived_and_under_the_ceiling() -> None:
    """Nobody chooses a mesh-moved tolerance: it is the safety factor on the measured spread."""
    golden = _golden()
    for walk, record in golden.walks.items():
        assert record.moved_tolerance == stability.moved_tolerance(record, golden), walk
        if record.moved_tolerance is not None:
            assert golden.same_mesh_tolerance <= record.moved_tolerance <= golden.ceiling, walk
