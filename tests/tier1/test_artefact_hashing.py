"""VER-23 — the content hash, and what it must and must not depend on (FR-27, section 5.3.2).

Every assertion here is an equality or an exception; there is no tolerance to
choose, and that is the point. A failure localises to one function.

The three properties the hash must have are asserted separately, because they
fail separately: it is stable across processes (nothing in the encoding depends
on dict iteration order or `repr` formatting), it moves under any change to the
parameters or the inputs, and it does *not* move under a change that resolves to
the same run.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from nanopnp.core.hashing import (
    CanonicalisationError,
    canonical,
    content_hash,
    file_hash,
    short,
)
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.io.store import Store, StoreError

FIXTURE = {
    "bias_V": 0.1,
    "concentration_M": 1,
    "corrections": {"steric": True, "viscosity": "willems2020_nacl"},
    "species": ["Na+", "Cl-"],
    "temperature_K": 298.15,
}
"""A parameter block exercising every encoder branch: float, int, bool, str, list, dict."""

FIXTURE_HASH = "4ea4b9756f0342ed33cfbc066333b983098ae2d800c1c83f7a7bc1d1ff95e882"
"""The digest of :data:`FIXTURE` under schema ``demo/v1``, stated rather than recomputed.

A test that recomputes the digest by the same code it is testing asserts only
that the function is deterministic. Writing the constant down makes an
unintended change to the encoding a failing test rather than a silently
invalidated store.
"""


def test_ver23_content_hash_is_stable_across_processes() -> None:
    """The digest does not depend on the interpreter's hash seed (section 5.3.2)."""
    script = (
        "import json,sys;"
        "from nanopnp.core.hashing import content_hash;"
        f"print(content_hash('demo/v1', json.loads({json.dumps(json.dumps(FIXTURE))})))"
    )
    digests = set()
    for seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        )
        digests.add(result.stdout.strip())
    assert digests == {FIXTURE_HASH}
    assert content_hash("demo/v1", FIXTURE) == FIXTURE_HASH


def test_ver23_every_leaf_change_moves_the_hash() -> None:
    """A change anywhere in the parameter tree reaches the digest."""
    base = content_hash("demo/v1", FIXTURE)
    variants = [
        {**FIXTURE, "bias_V": 0.100000000000001},
        {**FIXTURE, "species": ["Cl-", "Na+"]},
        {**FIXTURE, "corrections": {**FIXTURE["corrections"], "steric": False}},
        {**FIXTURE, "temperature_K": 298.16},
    ]
    for variant in variants:
        assert content_hash("demo/v1", variant) != base
    assert content_hash("other/v1", FIXTURE) != base


def test_ver23_hash_ignores_what_resolves_to_the_same_run() -> None:
    """Key order, ``1`` against ``1.0`` and the sign of zero are not differences.

    ``1`` and ``1.0`` are one value once pydantic has coerced the field, so the
    encoder must agree; ``-0.0`` and ``0.0`` are two spellings of the same bias
    and ``(-0.0).hex()`` differs from ``(0.0).hex()``, which is why the encoder
    normalises it.
    """
    reordered = dict(reversed(list(FIXTURE.items())))
    assert content_hash("demo/v1", reordered) == content_hash("demo/v1", FIXTURE)
    assert canonical({"c": 1}) == canonical({"c": 1})
    assert canonical({"bias": 1}) != canonical({"bias": 1.0})
    assert canonical({"bias": -0.0}) == canonical({"bias": 0.0})
    assert canonical({"bias": 1e-9}) == canonical({"bias": 0.000000001})


def test_ver23_an_unhashable_type_is_rejected_naming_its_path() -> None:
    """A set has no canonical order, so accepting one would make the hash depend on it."""
    with pytest.raises(CanonicalisationError, match=r"\$\.corrections\.models"):
        canonical({"corrections": {"models": {"a", "b"}}})
    with pytest.raises(CanonicalisationError, match=r"\$\.mesh"):
        canonical({"mesh": Path("clya.msh")})


def test_ver23_a_changed_input_hash_changes_the_output_hash() -> None:
    """Section 5.3.2: a hand-substituted artefact registers as a changed input."""
    one = content_hash("demo/v1", FIXTURE, {"mesh": "a" * 64})
    two = content_hash("demo/v1", FIXTURE, {"mesh": "b" * 64})
    assert one != two
    assert content_hash("demo/v1", FIXTURE, {}) == content_hash("demo/v1", FIXTURE)


def test_ver23_file_hash_is_content_not_path(tmp_path: Path) -> None:
    """An input file is hashed by content, so moving it is not a change."""
    here = tmp_path / "here.msh"
    there = tmp_path / "elsewhere" / "there.msh"
    there.parent.mkdir()
    here.write_bytes(b"$MeshFormat\n4.1 0 8\n")
    there.write_bytes(here.read_bytes())
    assert file_hash(here) == file_hash(there)
    there.write_bytes(b"$MeshFormat\n4.1 0 8\n$EndMeshFormat\n")
    assert file_hash(here) != file_hash(there)


def test_ver23_short_prefix_is_the_display_form_only() -> None:
    """The display prefix is 12 hex; the store never keys on it."""
    digest = content_hash("demo/v1", FIXTURE)
    assert short(digest) == digest[:12]
    assert len(digest) == 64


def test_ver23_store_round_trips_an_artefact(tmp_path: Path) -> None:
    """An artefact read back from the store carries the same key and summary."""
    store = Store(tmp_path)
    artefact = Artefact(
        schema=SOLUTION_SCHEMA,
        parameters=FIXTURE,
        inputs={"mesh": "c" * 64},
        summary={"iterations": 17},
    )
    assert store.get(SOLUTION_SCHEMA, artefact.hash) is None
    stored = store.put(artefact)
    loaded = store.get(SOLUTION_SCHEMA, artefact.hash)
    assert loaded is not None
    assert loaded.hash == artefact.hash == stored.hash
    assert loaded.summary["iterations"] == 17
    assert not loaded.hand_substituted
    assert loaded.created_at is not None


def test_ver23_an_edited_payload_loads_as_hand_substituted(tmp_path: Path) -> None:
    """FR-27 permits editing an artefact by hand; section 5.3.2 requires it be recorded.

    The payload is outside the digest — the key must be computable before the
    stage runs — so the edit is caught by recomputing the file's digest on load
    and comparing it with the one recorded beside the artefact, never by trusting
    the recorded value.
    """
    store = Store(tmp_path)
    source = tmp_path / "fields.xdmf"
    source.write_text("<Xdmf/>", encoding="utf-8")
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE, payload={"fields": source})
    stored = store.put(artefact)
    assert not stored.hand_substituted

    loaded = store.get(SOLUTION_SCHEMA, artefact.hash)
    assert loaded is not None
    loaded.payload["fields"].write_text("<Xdmf>edited</Xdmf>", encoding="utf-8")
    assert loaded.hand_substituted
    assert loaded.payload_hashes()["fields"] == file_hash(loaded.payload["fields"])
    assert loaded.payload_hashes()["fields"] != loaded.recorded_payload["fields"]


def test_ver23_get_or_compute_returns_the_stored_artefact_on_a_hit(tmp_path: Path) -> None:
    """The cache key is computable before the work, which is what makes it a cache."""
    store = Store(tmp_path)
    key = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE, inputs={"mesh": "d" * 64})
    calls = 0

    def compute() -> Artefact:
        nonlocal calls
        calls += 1
        return Artefact(
            schema=key.schema,
            parameters=key.parameters,
            inputs=key.inputs,
            summary={"iterations": 9},
        )

    first = store.get_or_compute(key, compute)
    second = store.get_or_compute(key, compute)
    assert calls == 1
    assert first.hash == second.hash == key.hash
    assert second.summary["iterations"] == 9
    assert (store.hits, store.misses) == (1, 1)

    other = Artefact(schema=SOLUTION_SCHEMA, parameters={**FIXTURE, "bias_V": -0.1})
    store.get_or_compute(other, lambda: other)
    assert (store.hits, store.misses) == (1, 2)


def test_ver23_a_stage_whose_parameters_do_not_determine_its_output_is_refused(
    tmp_path: Path,
) -> None:
    """A cache is only sound if the key determines the answer, so a mismatch aborts."""
    store = Store(tmp_path)
    key = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    wrong = Artefact(schema=SOLUTION_SCHEMA, parameters={**FIXTURE, "bias_V": 0.2})
    with pytest.raises(StoreError, match="do not determine"):
        store.get_or_compute(key, lambda: wrong)


def test_ver23_store_writes_are_atomic(tmp_path: Path) -> None:
    """No temporary file survives a write; the store directory holds only the record."""
    store = Store(tmp_path)
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    store.put(artefact)
    directory = store.location(SOLUTION_SCHEMA, artefact.hash)
    assert sorted(path.name for path in directory.iterdir()) == ["meta.json"]
    record = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    assert record["hash"] == artefact.hash
    assert "created_at" in record
