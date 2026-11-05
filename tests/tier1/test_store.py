"""The artefact store's run directories and its listing of entries an older release wrote."""

from __future__ import annotations

from pathlib import Path

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.io.artefact import Artefact
from nanopnp.io.store import Store

ROOT = Path(__file__).resolve().parents[2]

QUICKSTART = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"

DIGEST = "ab" * 32


def _put(store: Store, schema: str, directory: Path, tag: str) -> Artefact:
    payload = directory / f"{tag}.bin"
    payload.write_bytes(b"x" * 1000)
    return store.put(Artefact(schema=schema, parameters={"tag": tag}, payload={"data": payload}))


def _size(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def test_rev32_the_store_lists_and_removes_only_entries_of_an_older_schema(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "store")
    case = Case.load(QUICKSTART)
    Session(store, write=False).run(case, upto="mesh")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    old_case = _put(store, "nanopnp/case/v0.5", scratch, "a")
    old_fields = _put(store, "nanopnp/fields/v0.4", scratch, "b")
    # A newer release's entry, and a stage of one's own, are not this release's to remove.
    newer = _put(store, "nanopnp/fields/v0.7", scratch, "c")
    own = _put(store, "nanopnp/stage/x/v1", scratch, "d")

    stale = store.stale()
    assert {(entry.schema, entry.hash) for entry in stale} == {
        (old_case.schema, old_case.hash),
        (old_fields.schema, old_fields.hash),
    }
    for entry in stale:
        assert entry.size_bytes == _size(entry.path) >= 1000

    assert store.remove(stale) == 2
    assert store.stale() == ()
    assert store.get(newer.schema, newer.hash) is not None
    assert store.get(own.schema, own.hash) is not None
    assert store.get(old_case.schema, old_case.hash) is None

    misses = store.misses
    Session(store, write=False).run(case, upto="mesh")
    assert store.misses == misses


def test_ver62_a_store_given_no_runs_root_writes_run_directories_where_it_did(
    tmp_path: Path,
) -> None:
    short = DIGEST[:12]
    store = Store(tmp_path / "s")
    assert store.run_directory("a", DIGEST) == store.root / "runs" / f"a-{short}"
    assert store.run_directory("a", DIGEST, upto="mesh") == (
        store.root / "runs" / f"a-upto-mesh-{short}"
    )
    placed = Store(tmp_path / "s", runs=tmp_path / "runs", sweeps=tmp_path / "sweeps")
    assert placed.run_directory("a", DIGEST) == tmp_path / "runs" / "a" / short
    assert placed.run_directory("a", DIGEST, upto="mesh") == (
        tmp_path / "runs" / "a" / f"upto-mesh-{short}"
    )
    assert placed.sweep_directory("w", DIGEST) == tmp_path / "sweeps" / f"w-{short}"
