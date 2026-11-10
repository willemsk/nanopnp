"""The artefact store's run directories, its stale listing, its clean-up and its lock."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.api.session import Session
from nanopnp.io.artefact import Artefact
from nanopnp.io.store import META, READ_MARK, Store, StoreBusy
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk

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


def _age(store: Store, artefact: Artefact, seconds: float) -> None:
    mark = store.location(artefact.schema, artefact.hash) / READ_MARK
    mark.touch()
    os.utime(mark, (seconds, seconds))


def _hashes(store: Store) -> set[str]:
    return {path.parent.name for path in (store.root / "artefacts").glob(f"*/*/*/{META}")}


def test_fr27_a_cleaned_store_rebuilds_what_it_removed_and_never_reads_half_an_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store(tmp_path / "store")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    schema = "nanopnp/stage/x/v1"
    a, b, c = (_put(store, schema, scratch, tag) for tag in "abc")
    for age, artefact in zip((300.0, 100.0, 200.0), (a, b, c), strict=True):
        _age(store, artefact, age)

    # (1) The least recently read goes first.
    assert [e.hash for e in store.evict(keep=frozenset(), to_bytes=2 * _size(store.root) // 3)] == [
        b.hash
    ]
    # (2) A kept digest survives a clean to nothing.
    assert {e.hash for e in store.evict(keep=frozenset({a.hash}), to_bytes=0)} == {c.hash}
    assert store.get(a.schema, a.hash) is not None

    # (3) An evicted key misses, and its rebuild gives back its digest and payload bytes.
    assert store.get(b.schema, b.hash) is None
    assert not store.contains(b)
    remade = scratch / "b.bin"
    remade.write_bytes(b"x" * 1000)
    rebuilt = store.get_or_compute(
        b, lambda: Artefact(schema=schema, parameters={"tag": "b"}, payload={"data": remade})
    )
    assert rebuilt.hash == b.hash
    assert Path(rebuilt.payload["data"]).read_bytes() == b"x" * 1000

    # (4) An entry whose removal stopped half-way is a miss: it was renamed away first.
    monkeypatch.setattr(shutil, "rmtree", lambda *_args, **_kwargs: None)
    store.evict(keep=frozenset({a.hash}))
    monkeypatch.undo()
    assert store.get(b.schema, b.hash) is None
    assert not store.contains(b)
    left = [p for p in store.location(b.schema, b.hash).parent.iterdir() if p.name.startswith(".")]
    assert left and (left[0] / META).is_file()

    # (5) A young staging directory survives a clean-up and the put after it.
    staging = store.location(a.schema, a.hash).with_name(f".{'cd' * 32}.1.feed")
    staging.mkdir()
    (staging / META).write_text("{}", encoding="utf-8")
    store.evict(keep=frozenset())
    _put(store, schema, scratch, "d")
    assert staging.is_dir()
    # (7) A hidden directory is never an entry: it is neither counted nor evicted.
    assert store.usage().entries == len(_hashes(store) - {staging.name, left[0].name})
    assert all(not e.path.name.startswith(".") for e in store.evict(keep=frozenset()))
    assert staging.is_dir()


def test_fr27_a_project_clean_keeps_what_its_runs_and_its_window_hold(tmp_path: Path) -> None:
    project = Project.create(tmp_path / "p")
    study = project.import_case(Case.load(QUICKSTART))
    case = project.study(study)
    session = project.session()
    session.run(case, upto="mesh")
    variant = case.with_({"geometry.pore.radius_nm": 2.5})
    held = Session(session.store, write=False).run(variant, upto="mesh")
    holding = frozenset(artefact.hash for artefact in held.artefacts.values())
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    unused = _put(session.store, "nanopnp/stage/x/v1", scratch, "u")
    before = _hashes(session.store)
    assert holding - project.kept_artefacts(), "the window's walk is one no record names"

    # (6) The unused clean takes only what no run and no window holds, inputs kept.
    removed = project.clean_store(holding=holding)
    assert {entry.hash for entry in removed} == {unused.hash}
    assert _hashes(session.store) == before - {unused.hash}
    assert project.store_usage(holding).kept_entries == len(before) - 1
    assert {entry.hash for entry in project.clean_store(everything=True)} == before - {unused.hash}
    assert _hashes(session.store) == set()
    misses = session.store.misses
    session.run(case, upto="mesh")
    assert session.store.misses > misses
    assert project.kept_artefacts() <= _hashes(session.store)


def test_fr27_a_walk_in_another_program_stops_a_clean_up(tmp_path: Path) -> None:
    store = Store(tmp_path / "store")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    entry = _put(store, "nanopnp/stage/x/v1", scratch, "a")
    child = textwrap.dedent(
        f"""
        import sys
        from nanopnp.io.store import Store
        with Store({str(store.root)!r}).using():
            print("holding", flush=True)
            sys.stdin.readline()
        """
    )
    process = subprocess.Popen(
        [sys.executable, "-c", child], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "holding"
        # (8) A walk in another program makes a clean-up refuse, removing nothing.
        with pytest.raises(StoreBusy, match="nothing was removed"):
            store.evict(keep=frozenset())
        assert store.get(entry.schema, entry.hash) is not None
    finally:
        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=30)
    assert [e.hash for e in store.evict(keep=frozenset())] == [entry.hash]


def test_fr27_a_forecast_moves_no_read_mark(tmp_path: Path) -> None:
    store = Store(tmp_path / "store")
    case = Case.load(QUICKSTART)
    Session(store, write=False).run(case, upto="mesh")
    marks = [meta.with_name(READ_MARK) for meta in store.root.glob(f"artefacts/*/*/*/{META}")]
    assert marks
    for mark in marks:
        mark.touch()
        os.utime(mark, (100.0, 100.0))
    # (9) A forecast keys every stage against the store and records no read.
    keyed_walk(resolve(case, base=case.source.base), store=store, planned=set())
    assert {mark.stat().st_mtime for mark in marks} == {100.0}
