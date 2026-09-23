"""VER-32 (Tier 2) — ``nanopnp mesh reference`` writes a mesh the frozen cases ingest.

The Tier-1 half is in ``tests/tier1/test_cli.py``, on the idealised pore. The
reference geometry takes seconds to mesh rather than milliseconds, so it is here:
the file ingests through the VER-27 gate with the mapping the command printed, and
the hash it printed is the one the run's FR-25 manifest records. This is the test
that would have caught the frozen cases mapping a ``default`` group the reference
geometry does not carry.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from nanopnp.cli import main
from nanopnp.cli.errors import EXIT_OK
from nanopnp.io.run import run_case
from nanopnp.io.store import Store

REPOSITORY = Path(__file__).resolve().parents[2]
FROZEN = REPOSITORY / "examples" / "05-clya-reference" / "clya-0.5M-plus50mV.case.yaml"


def test_ver32_mesh_reference_ingests_with_its_printed_groups(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Printed groups are the frozen case's; printed hash is the manifest's."""
    monkeypatch.chdir(tmp_path)
    assert main(["mesh", "reference", "--out", "clya-reference.msh", "--json"]) == EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert printed["groups"] == {}
    assert printed["min_sicn"] > 0.3 and printed["min_gamma"] > 0.3

    case = shutil.copy(FROZEN, tmp_path / FROZEN.name)
    result = run_case(Path(case), store=Store(tmp_path / "store"), upto="mesh")
    assert result.manifest.geometry_and_mesh["content_hash"] == printed["content_hash"]
