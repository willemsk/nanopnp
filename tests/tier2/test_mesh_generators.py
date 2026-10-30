"""VER-32 (Tier 2): ``nanopnp mesh reference`` writes a mesh the frozen cases ingest."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from nanopnp import Case, Session
from nanopnp.cli import main
from nanopnp.core.errors import EXIT_OK
from nanopnp.io.store import Store

REPOSITORY = Path(__file__).resolve().parents[2]
FROZEN = REPOSITORY / "examples" / "05-clya-reference" / "clya-0.5M-plus50mV.case.yaml"


def test_ver32_mesh_reference_ingests_with_its_printed_groups(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["mesh", "reference", "--out", "clya-reference.msh", "--json"]) == EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert printed["groups"] == {}
    assert printed["min_sicn"] > 0.3 and printed["min_gamma"] > 0.3

    case = shutil.copy(FROZEN, tmp_path / FROZEN.name)
    result = Session(Store(tmp_path / "store")).run(Case.load(Path(case)), upto="mesh")
    assert result.manifest.geometry_and_mesh["content_hash"] == printed["content_hash"]
