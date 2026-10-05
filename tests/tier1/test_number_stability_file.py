"""VER-62: the number-stability golden file is well formed and every walk in it is asserted.

The golden itself is asserted inside the seven gated walks (``tests/tier2``), which
run only under ``--extended``. This file checks, at Tier 1, what would let one of
those assertions pass while checking nothing: a walk in the golden that no test
asserts, a walk asserted twice, a value of zero (whose relative drift is
undefined), or a key that lacks a walk another key has (WP35 D13).
"""

from __future__ import annotations

import ast
import json
import math
import re
from collections import Counter
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
GOLDEN = TESTS / "tier2" / "data" / "number_stability.json"
SCHEMA = "nanopnp/golden/stability/v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
KEY = re.compile(r"^[a-z0-9]+-[A-Za-z0-9_]+(-py3\.\d+)?$")


def _golden() -> dict[str, object]:
    golden: dict[str, object] = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return golden


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


def test_ver62_golden_schema_is_valid() -> None:
    golden = _golden()
    assert golden["schema"] == SCHEMA
    assert golden["tolerance"] == 1e-8
    keys = golden["keys"]
    assert isinstance(keys, dict) and keys
    for key, walks in keys.items():
        assert KEY.match(key), key
        assert isinstance(walks, dict) and walks, key
        for walk, entry in walks.items():
            assert set(entry) == {"mesh_hash", "values"}, (key, walk)
            assert SHA256.match(entry["mesh_hash"]), (key, walk)
            assert entry["values"], (key, walk)
            for quantity, value in entry["values"].items():
                assert math.isfinite(float.fromhex(value)), (key, walk, quantity)


def test_ver62_every_golden_walk_is_asserted_by_exactly_one_test() -> None:
    asserted = _asserted_walks()
    assert all(count == 1 for count in asserted.values()), asserted
    keys = _golden()["keys"]
    assert isinstance(keys, dict)
    for key, walks in keys.items():
        assert set(walks) == set(asserted), (key, sorted(set(walks) ^ set(asserted)))


def test_ver62_no_golden_value_is_zero() -> None:
    keys = _golden()["keys"]
    assert isinstance(keys, dict)
    zeros = [
        (key, walk, quantity)
        for key, walks in keys.items()
        for walk, entry in walks.items()
        for quantity, value in entry["values"].items()
        if float.fromhex(value) == 0.0
    ]
    assert not zeros


def test_ver62_every_key_has_every_walk_with_the_same_quantities() -> None:
    keys = _golden()["keys"]
    assert isinstance(keys, dict)
    shapes = {
        key: {walk: sorted(entry["values"]) for walk, entry in walks.items()}
        for key, walks in keys.items()
    }
    first = next(iter(shapes.values()))
    for key, shape in shapes.items():
        assert shape == first, key
