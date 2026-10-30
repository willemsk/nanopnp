"""VER-23 — the content hash, and what it must and must not depend on (FR-27, section 5.3.2)."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from nanopnp import Case, Session
from nanopnp.core.hashing import (
    CanonicalisationError,
    canonical,
    content_hash,
    decode_floats,
    file_hash,
    short,
)
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.io.store import STALE_STAGING_SECONDS, Store, StoreError

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
    reordered = dict(reversed(list(FIXTURE.items())))
    assert content_hash("demo/v1", reordered) == content_hash("demo/v1", FIXTURE)
    assert canonical({"c": 1}) == canonical({"c": 1})
    assert canonical({"bias": 1}) != canonical({"bias": 1.0})
    assert canonical({"bias": -0.0}) == canonical({"bias": 0.0})
    assert canonical({"bias": 1e-9}) == canonical({"bias": 0.000000001})


# QR-08
def test_ver23_decode_floats_restores_the_numbers_a_canonical_file_holds() -> None:
    document = {
        "quantities": {"current_A": 3.6170916294619195e-11, "routes_checked": True},
        "band_nm": [0.6, 1.5],
        "sign": -0.0,
        "count": 7,
        "mode": "none",
        "missing": None,
    }
    restored = decode_floats(json.loads(canonical(document)))

    assert restored == {**document, "sign": 0.0}
    quantities = restored["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["current_A"] == 3.6170916294619195e-11
    assert quantities["routes_checked"] is True
    assert restored["count"] == 7 and not isinstance(restored["count"], float)

    # A digested array cannot be undone and is left as it stands, and a mapping
    # that carries the name beside another key is a document, not a wrapper.
    passthrough = {"__f__": "0x1.0p+0", "units": "A"}
    assert decode_floats(passthrough) == passthrough
    assert decode_floats({"__f__": 1.0}) == {"__f__": 1.0}


def test_ver23_an_unhashable_type_is_rejected_naming_its_path() -> None:
    with pytest.raises(CanonicalisationError, match=r"\$\.corrections\.models"):
        canonical({"corrections": {"models": {"a", "b"}}})
    with pytest.raises(CanonicalisationError, match=r"\$\.mesh"):
        canonical({"mesh": Path("clya.msh")})


def test_ver23_a_changed_input_hash_changes_the_output_hash() -> None:
    one = content_hash("demo/v1", FIXTURE, {"mesh": "a" * 64})
    two = content_hash("demo/v1", FIXTURE, {"mesh": "b" * 64})
    assert one != two
    assert content_hash("demo/v1", FIXTURE, {}) == content_hash("demo/v1", FIXTURE)


def test_ver23_file_hash_is_content_not_path(tmp_path: Path) -> None:
    here = tmp_path / "here.msh"
    there = tmp_path / "elsewhere" / "there.msh"
    there.parent.mkdir()
    here.write_bytes(b"$MeshFormat\n4.1 0 8\n")
    there.write_bytes(here.read_bytes())
    assert file_hash(here) == file_hash(there)
    there.write_bytes(b"$MeshFormat\n4.1 0 8\n$EndMeshFormat\n")
    assert file_hash(here) != file_hash(there)


def test_ver23_short_prefix_is_the_display_form_only() -> None:
    digest = content_hash("demo/v1", FIXTURE)
    assert short(digest) == digest[:12]
    assert len(digest) == 64


def test_ver23_store_round_trips_an_artefact(tmp_path: Path) -> None:
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


# FR-27
def test_ver23_an_edited_payload_loads_as_hand_substituted(tmp_path: Path) -> None:
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
    store = Store(tmp_path)
    key = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    wrong = Artefact(schema=SOLUTION_SCHEMA, parameters={**FIXTURE, "bias_V": 0.2})
    with pytest.raises(StoreError, match="do not determine"):
        store.get_or_compute(key, lambda: wrong)


def test_ver23_store_writes_are_atomic(tmp_path: Path) -> None:
    store = Store(tmp_path)
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    store.put(artefact)
    directory = store.location(SOLUTION_SCHEMA, artefact.hash)
    assert sorted(path.name for path in directory.iterdir()) == ["meta.json"]
    record = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    assert record["hash"] == artefact.hash
    assert "created_at" in record


def test_ver23_a_charged_walk_writes_the_same_bytes_into_two_stores(
    charged_tube, tmp_path: Path
) -> None:
    import numpy as np

    from nanopnp.charge.stage import DEPOSIT_FILE

    case = charged_tube.write(tmp_path / "case")
    roots = []
    for name in ("first", "second"):
        store = Store(tmp_path / name)
        Session(store, write=False).run(Case.load(case), upto="charge")
        roots.append(store.root / "artefacts")

    def files(root: Path) -> dict[str, Path]:
        # POSIX names, so the schema is the first component on Windows too.
        return {
            path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file()
        }

    first, second = files(roots[0]), files(roots[1])
    assert set(first) == set(second)
    schemas = {name.split("/")[0] for name in first}
    assert {
        "nanopnp-protonation-v0.5",
        "nanopnp-charge-grid-v0.5",
        "nanopnp-fields-v0.5",
    } <= schemas
    for name, path in first.items():
        if path.name == "meta.json":
            left = json.loads(path.read_text(encoding="utf-8"))
            right = json.loads(second[name].read_text(encoding="utf-8"))
            left.pop("created_at", None)
            right.pop("created_at", None)
            assert left == right, name
        else:
            assert path.read_bytes() == second[name].read_bytes(), name

    (deposit,) = [path for name, path in first.items() if path.name == DEPOSIT_FILE]
    with np.load(deposit, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    assert "seconds" not in arrays
    restored = tmp_path / "restored.npz"
    with restored.open("wb") as handle:
        np.savez(handle, **arrays, seconds=np.asarray(0.25))
    assert restored.read_bytes() != deposit.read_bytes()
    assert file_hash(restored) != file_hash(deposit)


def _put_with_payload(store: Store, directory: Path, content: bytes) -> Artefact:
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "fields.bin"
    source.write_bytes(content)
    return store.put(
        Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE, payload={"fields": source})
    )


def _assert_one_consistent_entry(store: Store, *returned: Artefact) -> None:
    stored = store.get(SOLUTION_SCHEMA, returned[0].hash)
    assert stored is not None
    directory = store.location(SOLUTION_SCHEMA, stored.hash)
    record = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    for name, entry in record["payload"].items():
        assert file_hash(directory / entry["file"]) == entry["sha256"], name
    assert sorted(path.name for path in directory.iterdir()) == ["fields.bin", "meta.json"]
    assert not stored.hand_substituted
    for artefact in returned:
        assert artefact.payload == stored.payload
        assert artefact.recorded_payload == stored.recorded_payload
        assert artefact.created_at == stored.created_at


@pytest.mark.parametrize("step", ["before_copy", "before_publish"])
def test_ver26_interleaved_puts_leave_one_consistent_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: str
) -> None:
    import nanopnp.io.store as store_module

    store = Store(tmp_path / "store")
    other: list[Artefact] = []
    running = False

    def writer_b() -> None:
        nonlocal running
        if not running:
            running = True
            other.append(_put_with_payload(store, tmp_path / "b", b"writer B"))

    real_copy = store_module.shutil.copyfile
    real_publish = store_module._publish

    def copy(source: Path, target: Path) -> Path:
        if step == "before_copy":
            writer_b()
        return real_copy(source, target)  # type: ignore[return-value]

    def publish(staging: Path, directory: Path) -> None:
        if step == "before_publish":
            writer_b()
        real_publish(staging, directory)

    monkeypatch.setattr(store_module.shutil, "copyfile", copy)
    monkeypatch.setattr(store_module, "_publish", publish)
    first = _put_with_payload(store, tmp_path / "a", b"writer A, a different payload")
    monkeypatch.undo()

    assert len(other) == 1
    _assert_one_consistent_entry(store, first, other[0])
    assert (store.location(SOLUTION_SCHEMA, first.hash) / "fields.bin").read_bytes() == b"writer B"


def test_ver26_a_put_of_a_stored_key_copies_nothing_and_returns_the_first_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import nanopnp.io.store as store_module

    store = Store(tmp_path / "store")
    first = _put_with_payload(store, tmp_path / "a", b"first writer")

    def refuse(source: Path, target: Path) -> None:
        raise AssertionError("a payload was copied for a key that is already stored")

    monkeypatch.setattr(store_module.shutil, "copyfile", refuse)
    second = _put_with_payload(store, tmp_path / "b", b"a later writer")

    assert second.payload["fields"].read_bytes() == b"first writer"
    assert second.hash == first.hash


def test_ver26_a_put_removes_staging_a_killed_put_left_and_keeps_a_recent_one(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "store")
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    parent = store.location(SOLUTION_SCHEMA, artefact.hash).parent
    stale = parent / ".abcd.1.deadbeef"
    recent = parent / ".abcd.2.cafef00d"
    for staging in (stale, recent):
        staging.mkdir(parents=True)
        (staging / "fields.bin").write_bytes(b"half a copy")
    old = time.time() - STALE_STAGING_SECONDS - 60
    os.utime(stale, (old, old))

    _put_with_payload(store, tmp_path / "src", b"complete")

    assert not stale.exists()
    assert recent.is_dir()


def test_ver26_an_entry_left_without_a_record_is_replaced(tmp_path: Path) -> None:
    store = Store(tmp_path / "store")
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    directory = store.location(SOLUTION_SCHEMA, artefact.hash)
    directory.mkdir(parents=True)
    (directory / "fields.bin").write_bytes(b"left by an older put")

    stored = _put_with_payload(store, tmp_path / "src", b"complete")

    _assert_one_consistent_entry(store, stored)
    assert (directory / "fields.bin").read_bytes() == b"complete"


def test_ver26_a_payload_already_inside_the_entry_is_copied_not_moved(tmp_path: Path) -> None:
    store = Store(tmp_path / "store")
    artefact = Artefact(schema=SOLUTION_SCHEMA, parameters=FIXTURE)
    directory = store.location(SOLUTION_SCHEMA, artefact.hash)
    stored = _put_with_payload(store, directory, b"written in place")

    _assert_one_consistent_entry(store, stored)
    assert (directory / "fields.bin").read_bytes() == b"written in place"


RACING_WRITER = """
import sys, time
from pathlib import Path
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact
from nanopnp.io.store import Store

root, name, go = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
(root / name).mkdir()
source = root / name / "fields.bin"
source.write_bytes(name.encode() * 200_000)
artefact = Artefact(schema=SOLUTION_SCHEMA, parameters={"k": 1}, payload={"fields": source})
(root / f"{name}.ready").touch()
while not go.exists():
    time.sleep(0.001)
stored = Store(root / "store").put(artefact)
print(stored.payload["fields"].read_bytes()[:1].decode(), stored.created_at)
"""


def test_ver26_two_processes_race(tmp_path: Path) -> None:
    go = tmp_path / "go"
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", RACING_WRITER, str(tmp_path), name, str(go)],
            stdout=subprocess.PIPE,
            text=True,
        )
        for name in ("a", "b")
    ]
    try:
        # Released only once both have imported and built their artefact, or it is no barrier.
        deadline = time.monotonic() + 120
        while not all((tmp_path / f"{name}.ready").exists() for name in ("a", "b")):
            assert time.monotonic() < deadline, "a writer never reached the barrier"
            time.sleep(0.01)
        go.touch()
        outputs = [process.communicate(timeout=120)[0].strip() for process in processes]
    finally:
        for process in processes:
            process.kill()
    assert [process.returncode for process in processes] == [0, 0]

    store = Store(tmp_path / "store")
    stored = store.get(SOLUTION_SCHEMA, Artefact(schema=SOLUTION_SCHEMA, parameters={"k": 1}).hash)
    assert stored is not None
    directory = store.location(SOLUTION_SCHEMA, stored.hash)
    record = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
    assert file_hash(directory / "fields.bin") == record["payload"]["fields"]["sha256"]
    winner = (directory / "fields.bin").read_bytes()[:1].decode()
    assert outputs == [f"{winner} {stored.created_at}"] * 2


def test_ver26_a_put_whose_entry_cannot_be_read_back_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Store, "get", lambda self, schema, digest: None)
    with pytest.raises(StoreError, match="is not in the store after its put"):
        _put_with_payload(Store(tmp_path / "store"), tmp_path / "src", b"x")


def test_ver26_a_put_that_cannot_publish_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: Path, target: Path) -> Path:
        raise PermissionError("read-only")

    monkeypatch.setattr(Path, "rename", refuse)
    with pytest.raises(StoreError, match="could not publish"):
        _put_with_payload(Store(tmp_path / "store"), tmp_path / "src", b"x")
