"""VER-47 — case schema v2, the v1 upgrade, and the supported interpreter range.

The oracle is a frozen corpus: every case file the project shipped under
``nanopnp/case/v1``, copied into ``tests/tier1/data/case_v1/corpus/`` together
with what the unmodified v1 code made of each of them (``golden.json``) and the
v1 field tree (``fields.txt``). All three were written by ``record.py`` in that
directory *before* the schema moved, so the upgrade is held to a record it did
not produce (WP17 D7). A record written by the code under test would agree with
it for the same wrong reason.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

import pytest

from nanopnp.core.hashing import content_hash
from nanopnp.io.artefact import SOLUTION_SCHEMA, StageInputs
from nanopnp.io.case import load_case, resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.validation.comsol import case_identity

DATA = Path(__file__).parent / "data" / "case_v1"
GOLDEN: dict[str, Any] = json.loads((DATA / "golden.json").read_text(encoding="utf-8"))
CORPUS: tuple[str, ...] = tuple(sorted(GOLDEN["cases"]))


def _decoded(record: dict[str, Any]) -> dict[str, Any]:
    """Return a provenance record as ``golden.json`` holds it, tuples as lists."""
    decoded: dict[str, Any] = json.loads(json.dumps(record, sort_keys=True))
    return decoded


def _diff(recorded: dict[str, Any], resolved: dict[str, Any]) -> str:
    """Return a unified diff of two provenance records, for a failure message."""
    before = json.dumps(recorded, indent=2, sort_keys=True).splitlines()
    after = json.dumps(resolved, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(before, after, "recorded (v1)", "resolved", lineterm=""))


def test_ver47_the_corpus_is_every_case_file_shipped_at_v0_5_0() -> None:
    """Thirteen files: seven examples, five validation cases, the sweep base case."""
    assert len(CORPUS) == 13
    on_disk = sorted(
        path.relative_to(DATA / "corpus").as_posix()
        for path in (DATA / "corpus").rglob("*.case.yaml")
    )
    assert on_disk == list(CORPUS)


@pytest.mark.parametrize("relative", CORPUS)
def test_ver47_the_v1_corpus_resolves_to_its_recorded_solve(relative: str) -> None:
    """Each corpus file resolves to the solve, materials and identity v1 recorded."""
    recorded = GOLDEN["cases"][relative]
    resolved = resolve(load_case(DATA / "corpus" / relative))

    provenance = _decoded(resolved.solve_provenance)
    assert provenance == recorded["solve_provenance"], _diff(
        recorded["solve_provenance"], provenance
    )
    assert content_hash(SOLUTION_SCHEMA, resolved.solve_provenance) == recorded["restore_digest"]
    assert case_identity(resolved) == recorded["case_identity"]

    materials = MaterialsStage().run(StageInputs(case=resolved.document))
    assert materials.hash == recorded["materials_key"]
