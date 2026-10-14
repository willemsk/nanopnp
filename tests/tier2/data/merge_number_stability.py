"""Fold recorded VER-62 walks into the number-stability golden (WP35 D14)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from nanopnp.validation.stability import FoldError, StabilityGolden, fold

GOLDEN = Path(__file__).resolve().parent / "number_stability.json"

logger = logging.getLogger("merge_number_stability")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", nargs="?", type=Path, help="the recording directory")
    parser.add_argument(
        "--entry", type=Path, action="append", default=[], help="a record a CI leg printed"
    )
    parser.add_argument("--replace", action="store_true", help="re-pin a known mesh's values")
    arguments = parser.parse_args(argv)
    golden = StabilityGolden.read(GOLDEN) if GOLDEN.exists() else StabilityGolden.empty()
    paths = list(arguments.entry)
    if arguments.directory is not None:
        paths += sorted(arguments.directory.glob("*.json"))
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        try:
            golden = fold(golden, record, replace=arguments.replace)
        except FoldError as error:
            raise SystemExit(f"{path}: {error}") from error
        walk = golden.walks[record["walk"]]
        logger.info(
            "%s on %s: mesh %s, %d meshes, mesh-moved tolerance %s",
            record["walk"],
            record["environment"],
            record["mesh_hash"][:12],
            len(walk.meshes),
            "none" if walk.moved_tolerance is None else f"{walk.moved_tolerance:.3e}",
        )
    golden.write(GOLDEN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
