"""The content-addressed artefact store (SPECIFICATION.md section 5.3.2)."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import secrets
import shutil
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.paths import store_root
from nanopnp.core.stages import registered_stages
from nanopnp.io.artefact import CHARGE_GRID_SCHEMA, PROTONATION_FRAME_SCHEMA, Artefact, timestamp

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.hashing import Canonicalisable

logger = logging.getLogger(__name__)

META = "meta.json"

FANOUT = 2

STALE_STAGING_SECONDS = 24 * 3600
"""Age after which a hidden staging directory is a killed put's, not a slow copy."""


_SCHEMA_PATTERN = re.compile(r"^(?P<family>nanopnp/[a-z-]+/)v(?P<version>\d+(?:\.\d+)*)$")

AUXILIARY_SCHEMAS = (PROTONATION_FRAME_SCHEMA, CHARGE_GRID_SCHEMA)
"""Schemas that stages store besides the ones they register."""


class StoreError(RuntimeError):
    """A stored artefact could not be read, or a write could not be completed."""


@dataclass(frozen=True)
class StaleEntry:
    """One stored artefact written under an older version of a schema this release writes."""

    schema: str
    hash: str
    path: Path
    size_bytes: int


class Store:
    """A directory of content-addressed artefacts; the root is created on first write.

    ``runs`` and ``sweeps`` place run and sweep directories outside the root, so that a project
    keeps them beside its store; by default both stay under the root.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        runs: str | Path | None = None,
        sweeps: str | Path | None = None,
    ) -> None:
        self._root = Path(root).expanduser().resolve() if root is not None else store_root()
        self._runs = Path(runs).expanduser().resolve() if runs is not None else None
        self._sweeps = Path(sweeps).expanduser().resolve() if sweeps is not None else None
        self.hits = 0
        self.misses = 0

    @property
    def root(self) -> Path:
        """The store root."""
        return self._root

    def location(self, schema: str, digest: str) -> Path:
        """Return the directory one artefact occupies, whether or not it exists."""
        slug = schema.replace("/", "-")
        return self._root / "artefacts" / slug / digest[:FANOUT] / digest

    def run_directory(self, name: str, digest: str, *, upto: str | None = None) -> Path:
        """Return the directory a run's manifest, case and QoIs are written to.

        ``upto`` names the last stage of a walk that stopped before the end.
        """
        from nanopnp.core.hashing import short

        if self._runs is not None:
            leaf = f"upto-{upto}-{short(digest)}" if upto is not None else short(digest)
            return self._runs / name / leaf
        label = f"{name}-upto-{upto}" if upto is not None else name
        return self._root / "runs" / f"{label}-{short(digest)}"

    def sweep_directory(self, name: str, digest: str) -> Path:
        """Return the directory one sweep's plan, member records and dataset live in."""
        from nanopnp.core.hashing import short

        base = self._sweeps if self._sweeps is not None else self._root / "sweeps"
        return base / f"{name}-{short(digest)}"

    def contains(self, artefact: Artefact) -> bool:
        """Whether an artefact with this key is already stored."""
        return (self.location(artefact.schema, artefact.hash) / META).is_file()

    def put(self, artefact: Artefact) -> Artefact:
        """Store an artefact; return the entry held, the first writer's if the key was taken.

        Raises StoreError if a payload is missing or the entry cannot be published.
        """
        directory = self.location(artefact.schema, artefact.hash)
        for name, source in artefact.payload.items():
            if not Path(source).is_file():
                raise StoreError(
                    f"payload {name!r} of artefact {artefact.short_hash} is not a file: {source}"
                )
        held = self.get(artefact.schema, artefact.hash)
        if held is not None:
            return held
        directory.parent.mkdir(parents=True, exist_ok=True)
        _sweep_staging(directory.parent)
        # One writer's payloads and record arrive together or not at all: two puts of one key
        # never interleave their files into a record that disagrees with its payloads.
        staging = directory.with_name(f".{directory.name}.{os.getpid()}.{secrets.token_hex(4)}")
        staging.mkdir()
        try:
            stored_payload: dict[str, Path] = {}
            for name, source in sorted(artefact.payload.items()):
                shutil.copyfile(source, staging / Path(source).name)
                stored_payload[name] = staging / Path(source).name
            record = Artefact(
                schema=artefact.schema,
                parameters=artefact.parameters,
                inputs=artefact.inputs,
                payload=stored_payload,
                summary=artefact.summary,
                created_at=artefact.created_at or timestamp(),
            )
            (staging / META).write_bytes(
                json.dumps(record.meta(), indent=2, sort_keys=True).encode("utf-8")
            )
            _publish(staging, directory)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        stored = self.get(artefact.schema, artefact.hash)
        if stored is None:
            raise StoreError(f"artefact {artefact.short_hash} is not in the store after its put")
        logger.debug("stored %s %s", stored.schema, stored.short_hash)
        return stored

    def get(self, schema: str, digest: str) -> Artefact | None:
        """Return a stored artefact, or None if absent; StoreError if its record is unreadable."""
        directory = self.location(schema, digest)
        meta_path = directory / META
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise StoreError(f"{meta_path}: not readable as JSON: {error}") from error
        if not isinstance(meta, dict):
            raise StoreError(f"{meta_path}: a stored record is a JSON object")
        try:
            entries = _payload_entries(meta)
            artefact = Artefact(
                schema=str(meta["schema"]),
                parameters=meta["parameters"],
                inputs=meta.get("inputs", {}),
                payload={name: directory / str(entry["file"]) for name, entry in entries.items()},
                summary=meta.get("summary", {}),
                created_at=meta.get("created_at"),
                recorded_hash=str(meta["hash"]),
                recorded_payload={name: str(entry["sha256"]) for name, entry in entries.items()},
            )
        except (KeyError, TypeError) as error:
            raise StoreError(f"{meta_path}: incomplete artefact record: {error}") from error
        if artefact.recorded_hash != artefact.hash:
            logger.warning(
                "artefact %s records hash %s but its parameters hash to %s; "
                "reading it as a hand substitution (FR-27)",
                meta_path,
                artefact.recorded_hash,
                artefact.hash,
            )
        return artefact

    def get_or_compute(self, key: Artefact, compute: Callable[[], Artefact]) -> Artefact:
        """Return the stored artefact for ``key``, computing it on a miss."""
        found = self.get(key.schema, key.hash)
        if found is not None:
            self.hits += 1
            logger.debug("cache hit %s %s", key.schema, key.short_hash)
            return found
        self.misses += 1
        produced = compute()
        if produced.hash != key.hash:
            raise StoreError(
                f"stage produced artefact {produced.short_hash} under key {key.short_hash}: the "
                "parameters the stage declared do not determine the artefact it made, so a later "
                "cache hit would return a different run's answer"
            )
        return self.put(produced)

    def stale(self) -> tuple[StaleEntry, ...]:
        """List the entries of an older version of a schema this release writes.

        A newer version's entry, and any entry of a schema this release does not write, is kept:
        a store may be shared with a newer release.
        """
        current = _current_schemas()
        found: list[StaleEntry] = []
        for meta_path in sorted((self._root / "artefacts").glob("*/*/*/" + META)):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                schema = str(meta["schema"])
                digest = str(meta["hash"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if not _is_older(schema, current):
                continue
            directory = meta_path.parent
            size = sum(file.stat().st_size for file in directory.rglob("*") if file.is_file())
            found.append(StaleEntry(schema, digest, directory, size))
        return tuple(found)

    def remove(self, entries: Iterable[StaleEntry]) -> int:
        """Delete the given entries, and return how many were removed."""
        removed = 0
        root = (self._root / "artefacts").resolve()
        for entry in entries:
            directory = entry.path.resolve()
            if root not in directory.parents:
                raise StoreError(f"{directory} is not an entry of the store at {self._root}")
            if directory.is_dir():
                shutil.rmtree(directory)
                removed += 1
                with contextlib.suppress(OSError):  # the fan-out directory still holds others
                    directory.parent.rmdir()
        return removed


def _current_schemas() -> tuple[str, ...]:
    return tuple(d.artefact_schema for d in registered_stages()) + AUXILIARY_SCHEMAS


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _is_older(schema: str, current: Iterable[str]) -> bool:
    # Compared as numbers: v0.10 is newer than v0.9.
    mine = _SCHEMA_PATTERN.match(schema)
    if mine is None:
        return False
    for other in current:
        theirs = _SCHEMA_PATTERN.match(other)
        if (
            theirs is not None
            and theirs["family"] == mine["family"]
            and _version(mine["version"]) < _version(theirs["version"])
        ):
            return True
    return False


def _sweep_staging(parent: Path) -> None:
    # A put killed before its rename (a time limit, SIGKILL) leaves its staging directory behind.
    cutoff = time.time() - STALE_STAGING_SECONDS
    for entry in parent.glob(".*"):
        try:
            stale = entry.is_dir() and entry.stat().st_mtime < cutoff
        except OSError:  # pragma: no cover - the entry vanished between the glob and the stat
            continue
        if stale:
            shutil.rmtree(entry, ignore_errors=True)


def _publish(staging: Path, directory: Path) -> None:
    # A rename onto a non-empty directory fails: the first complete entry stays, and a
    # directory without a record (an older put's) is cleared and replaced.
    refused: OSError | None = None
    for _ in range(3):
        try:
            staging.rename(directory)
        except OSError as error:
            if (directory / META).is_file():
                return
            refused = error
            shutil.rmtree(directory, ignore_errors=True)
        else:
            return
    raise StoreError(f"could not publish the artefact at {directory}: {refused}") from refused


def _payload_entries(meta: Mapping[str, Canonicalisable]) -> dict[str, dict[str, str]]:
    payload = meta.get("payload", {})
    if not isinstance(payload, dict):
        raise StoreError("a stored record's payload block is a JSON object")
    return {str(name): dict(entry) for name, entry in payload.items()}


def atomic_write_bytes(target: Path, data: bytes) -> None:
    """Write bytes to ``target`` atomically, through a same-directory temporary file."""
    # The temporary name carries the pid and a token: job-array workers on a shared filesystem
    # run on different hosts, where pids repeat.
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
