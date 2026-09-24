"""Freeze the ``nanopnp/case/v1`` corpus and what the v1 loader made of it (VER-47).

Run once, on the unmodified v1 code, before the schema moved to v2::

    uv run tests/tier1/data/case_v1/record.py

It copies every case file the project shipped at ``v0.5.0`` into ``corpus/``,
byte for byte, and writes two records beside it:

- ``fields.txt``, the dotted paths :func:`nanopnp.io.case.case_fields` walked
  under v1, one per line;
- ``golden.json``, per corpus file, the solve provenance the v1 resolver built,
  decoded, together with the three keys computed from it and the stage-8
  materials key.

Recording from the code that performs the upgrade would test the upgrade
against itself (WP17 D7). This script therefore refuses to run once the
package's case schema is no longer v1: after the move there is nothing left
for it to record honestly, and the files it wrote are the oracle.
"""

from __future__ import annotations

import json
import shutil
from importlib.metadata import version
from pathlib import Path

from nanopnp.core.hashing import content_hash
from nanopnp.io.artefact import CASE_SCHEMA, SOLUTION_SCHEMA, StageInputs
from nanopnp.io.case import case_fields, load_case, resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.validation.comsol import case_identity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

SOURCES: tuple[str, ...] = (
    "examples/01-quickstart/quickstart.case.yaml",
    "examples/02-charged-pore/classical.case.yaml",
    "examples/02-charged-pore/epnpns.case.yaml",
    "examples/03-iv-sweep/charged.case.yaml",
    "examples/03-iv-sweep/uncharged.case.yaml",
    "examples/04-python-api/tour.case.yaml",
    "examples/05-clya-reference/clya-0.5M-plus50mV.case.yaml",
    "docs/validation/cases/clya-0.05M-minus200mV.case.yaml",
    "docs/validation/cases/clya-0.05M-plus200mV.case.yaml",
    "docs/validation/cases/clya-0.5M-plus50mV.case.yaml",
    "docs/validation/cases/clya-3M-minus200mV.case.yaml",
    "docs/validation/cases/clya-3M-plus200mV.case.yaml",
    "docs/sweeps/phase1-reference.case.yaml",
)
"""Every case file shipped at ``v0.5.0``: seven examples, five validation cases, one sweep base."""


def main() -> None:
    """Copy the corpus and write ``fields.txt`` and ``golden.json``."""
    if CASE_SCHEMA != "nanopnp/case/v1":
        raise SystemExit(
            f"the package's case schema is {CASE_SCHEMA!r}; this record is made by the v1 code "
            "only, and re-running it now would test the upgrade against itself (WP17 D7)"
        )
    corpus = HERE / "corpus"
    golden: dict[str, object] = {}
    for relative in SOURCES:
        target = corpus / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        resolved = resolve(load_case(target))
        materials = MaterialsStage().run(StageInputs(case=resolved.document))
        golden[relative] = {
            "restore_digest": content_hash(SOLUTION_SCHEMA, resolved.solve_provenance),
            "materials_key": materials.hash,
            "case_identity": case_identity(resolved),
            "solve_provenance": resolved.solve_provenance,
        }
    record = {
        "recorded_by": f"nanopnp {version('nanopnp')}",
        "schema": CASE_SCHEMA,
        "cases": golden,
    }
    (HERE / "golden.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    paths = [reference.path for reference in case_fields()]
    (HERE / "fields.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
