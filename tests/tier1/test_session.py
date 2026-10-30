"""A Session runs a case into its store; a hook is not an input, and `only` never computes."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.stages import CancelFlag
from nanopnp.pipeline.run import MissingUpstreamError

QUICKSTART = (
    Path(__file__).resolve().parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
)


@pytest.fixture
def case() -> Case:
    return Case.load(QUICKSTART)


def test_ver44_session_run_passes_on_its_hooks_and_moves_no_key(case: Case, tmp_path: Path) -> None:
    plain = Session(tmp_path / "plain", write=False).run(case, upto="mesh")
    seen: dict[str, list[object]] = {"stage": [], "artefact": [], "progress": []}
    hooked = Session(tmp_path / "hooked", write=False).run(
        case,
        upto="mesh",
        progress=lambda fraction, message: seen["progress"].append((fraction, message)),
        cancel=CancelFlag(),
        on_stage=lambda name, index, total: seen["stage"].append((name, index, total)),
        on_artefact=lambda name, schema, key, cached: seen["artefact"].append((name, key)),
    )
    assert [stage[0] for stage in seen["stage"]] == [record.name for record in hooked.stages]
    assert seen["progress"]
    assert {name: key for name, key in seen["artefact"]} == {
        name: artefact.hash for name, artefact in plain.artefacts.items()
    }
    assert {name: artefact.hash for name, artefact in hooked.artefacts.items()} == {
        name: artefact.hash for name, artefact in plain.artefacts.items()
    }
    assert sorted(path.name for path in (tmp_path / "hooked").rglob("*.json")) == sorted(
        path.name for path in (tmp_path / "plain").rglob("*.json")
    )


def test_fr27_only_refuses_an_upstream_the_store_does_not_hold(case: Case, tmp_path: Path) -> None:
    session = Session(tmp_path / "store", write=False)
    with pytest.raises(MissingUpstreamError, match="'region'"):
        session.run(case, upto="solve", only=True)
    session.run(case, upto="mesh")
    again = session.run(case, upto="mesh", only=True)
    assert all(record.cached for record in again.stages)
