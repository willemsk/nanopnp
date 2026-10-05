"""Fold recorded VER-62 walks into the number-stability golden (WP35 D14).

A walk run with ``NANOPNP_RECORD_STABILITY=<dir>`` writes ``<dir>/<walk>.json``.
This script folds every such file in ``<dir>`` into ``number_stability.json``
under the key each file was recorded on, which must be the running machine's::

    NANOPNP_RECORD_STABILITY=rec uv run pytest --extended <the seven walks>
    uv run tests/tier2/data/merge_number_stability.py rec

A key from another platform comes from the entry a failing CI leg prints, which
is already in the golden's shape: pass that file with ``--entry`` instead. An
existing entry is replaced only with ``--replace``, which a G10 re-pin uses in the
commit that rules the change (section 8.2.7 G10).
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent / "number_stability.json"
SCHEMA = "nanopnp/golden/stability/v1"

logger = logging.getLogger("merge_number_stability")


def _key() -> str:
    return f"{sys.platform}-{platform.machine()}"


def _load() -> dict[str, object]:
    if GOLDEN.exists():
        golden: dict[str, object] = json.loads(GOLDEN.read_text(encoding="utf-8"))
        return golden
    return {"schema": SCHEMA, "tolerance": 1e-8, "keys": {}}


def main(argv: list[str] | None = None) -> int:
    """Fold recorded walks, or a printed CI entry, into the golden."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", nargs="?", type=Path, help="the recording directory")
    parser.add_argument("--entry", type=Path, help="a JSON entry a CI leg printed")
    parser.add_argument("--replace", action="store_true", help="replace an existing walk")
    arguments = parser.parse_args(argv)
    golden = _load()
    keys = golden["keys"]
    assert isinstance(keys, dict)
    incoming: dict[str, dict[str, object]] = {}
    if arguments.entry is not None:
        incoming = json.loads(arguments.entry.read_text(encoding="utf-8"))
    if arguments.directory is not None:
        for path in sorted(arguments.directory.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("schema") != SCHEMA or record["key"] != _key():
                raise SystemExit(f"{path}: recorded on {record.get('key')!r}, not {_key()!r}")
            incoming.setdefault(record["key"], {})[record["walk"]] = {
                "mesh_hash": record["mesh_hash"],
                "values": record["values"],
            }
    for key, walks in incoming.items():
        existing = keys.setdefault(key, {})
        for walk, entry in walks.items():
            if walk in existing and existing[walk] != entry and not arguments.replace:
                raise SystemExit(f"{key} {walk}: already in the golden; pass --replace to re-pin")
            existing[walk] = entry
            logger.info("%s %s: %d values", key, walk, len(entry["values"]))  # type: ignore[index]
    golden["keys"] = {key: dict(sorted(keys[key].items())) for key in sorted(keys)}
    GOLDEN.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
