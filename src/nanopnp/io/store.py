"""The content-addressed artefact store (``SPECIFICATION.md`` section 5.3.2).

A stage whose input hashes and parameters are unchanged is not recomputed. That
sentence is the whole design: the cache key is
:attr:`nanopnp.io.artefact.Artefact.hash`, which is computable *before* the stage
runs, so :meth:`Store.get_or_compute` can decide without doing the work.

Layout::

    <root>/artefacts/<schema-slug>/<hash[:2]>/<hash>/meta.json
                                                    /<payload files>
    <root>/runs/<case-name>-<hash[:12]>/manifest.json

Writes go to a temporary file in the destination directory and are then moved
into place, which is atomic on POSIX and Windows alike. The store is
content-addressed, so a race writes identical bytes; a job array (WP11) hits this
on its first run.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.paths import store_root
from nanopnp.io.artefact import Artefact, timestamp

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.hashing import Canonicalisable

logger = logging.getLogger(__name__)

META = "meta.json"
"""Name of the record every stored artefact carries."""

FANOUT = 2
"""Leading hex characters of the hash used as a directory level."""


class StoreError(RuntimeError):
    """A stored artefact could not be read, or a write could not be completed."""


class Store:
    """A directory of content-addressed artefacts.

    Parameters
    ----------
    root
        Store root; defaults to :func:`nanopnp.core.paths.store_root`. Created on
        first write and never on construction, so that merely constructing a
        store — which ``nanopnp --env`` does — leaves no directories behind.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root).expanduser().resolve() if root is not None else store_root()
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

    def run_directory(self, name: str, digest: str) -> Path:
        """Return the directory a run's manifest, case and QoIs are written to."""
        from nanopnp.core.hashing import short

        return self._root / "runs" / f"{name}-{short(digest)}"

    def sweep_directory(self, name: str, digest: str) -> Path:
        """Return the directory one sweep's plan, member records and dataset live in.

        Beside ``runs/`` rather than inside it: a sweep is a set of runs and each
        of its members already has a run directory of its own, so nesting them
        would make a member's manifest reachable by two paths. The digest is the
        plan's, so re-planning the same document lands on the same directory and
        a plan with one value inserted lands on another (§5.3.4).
        """
        from nanopnp.core.hashing import short

        return self._root / "sweeps" / f"{name}-{short(digest)}"

    def contains(self, artefact: Artefact) -> bool:
        """Whether an artefact with this key is already stored."""
        return (self.location(artefact.schema, artefact.hash) / META).is_file()

    def put(self, artefact: Artefact) -> Artefact:
        """Write an artefact to the store and return it as stored.

        The returned artefact's payload paths point into the store, and it
        carries the recorded hash and payload digests, so a caller that keeps it
        can detect a later hand substitution without re-reading ``meta.json``.

        Raises
        ------
        StoreError
            If a payload file named by the artefact is missing.
        """
        directory = self.location(artefact.schema, artefact.hash)
        directory.mkdir(parents=True, exist_ok=True)

        stored_payload: dict[str, Path] = {}
        for name, source in sorted(artefact.payload.items()):
            if not Path(source).is_file():
                raise StoreError(
                    f"payload {name!r} of artefact {artefact.short_hash} is not a file: {source}"
                )
            target = directory / Path(source).name
            if Path(source).resolve() != target.resolve():
                _atomic_write_bytes(target, Path(source).read_bytes())
            stored_payload[name] = target

        record = Artefact(
            schema=artefact.schema,
            parameters=artefact.parameters,
            inputs=artefact.inputs,
            payload=stored_payload,
            summary=artefact.summary,
            created_at=artefact.created_at or timestamp(),
        )
        meta = record.meta()
        _atomic_write_bytes(
            directory / META, json.dumps(meta, indent=2, sort_keys=True).encode("utf-8")
        )
        logger.debug("stored %s %s", record.schema, record.short_hash)
        payload_digests = {
            name: str(entry["sha256"]) for name, entry in _payload_entries(meta).items()
        }
        return Artefact(
            schema=record.schema,
            parameters=record.parameters,
            inputs=record.inputs,
            payload=record.payload,
            summary=record.summary,
            created_at=record.created_at,
            recorded_hash=record.hash,
            recorded_payload=payload_digests,
        )

    def get(self, schema: str, digest: str) -> Artefact | None:
        """Return a stored artefact, or ``None`` if it is not in the store.

        The payload digests recorded in ``meta.json`` are carried onto the
        artefact but never trusted: :attr:`~nanopnp.io.artefact.Artefact.hand_substituted`
        recomputes them from the files on disk. A recorded hash that disagrees
        with the parameters is carried the same way rather than raising, because
        FR-27 permits an artefact to be edited by hand and section 5.3.2 requires
        that be *recorded*, not aborted.

        Raises
        ------
        StoreError
            If ``meta.json`` exists but is not readable as a record.
        """
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
        """Return the stored artefact for ``key``, computing it on a miss.

        Parameters
        ----------
        key
            An artefact carrying the schema, parameters and input hashes of the
            work about to be done, and no payload. It is the cache key, so it
            must be constructible without doing the work — which is exactly the
            property that keeps a stage a pure function of its inputs (FR-27).
        compute
            Called on a miss; must return an artefact with the same key.

        Raises
        ------
        StoreError
            If ``compute`` returns an artefact whose hash is not ``key``'s. That
            means the stage's declared parameters do not determine its output,
            which would make every later cache hit a wrong answer.
        """
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


def _payload_entries(meta: Mapping[str, Canonicalisable]) -> dict[str, dict[str, str]]:
    """Return the payload block of a record, checked for shape."""
    payload = meta.get("payload", {})
    if not isinstance(payload, dict):
        raise StoreError("a stored record's payload block is a JSON object")
    return {str(name): dict(entry) for name, entry in payload.items()}


def _atomic_write_bytes(target: Path, data: bytes) -> None:
    """Write bytes to ``target`` through a temporary file in the same directory.

    ``Path.replace`` is ``os.replace``, atomic on POSIX and Windows. The
    temporary carries the process id so two workers of a job array cannot collide
    on the temporary itself.
    """
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_bytes(data)
    temporary.replace(target)
