"""Apply the tier-2 marker to every test in this directory."""

from collections.abc import Callable
from pathlib import Path

import pytest

from nanopnp import Case, Session
from nanopnp.core.stages import figure_target
from nanopnp.io.store import Store
from nanopnp.pipeline.run import RunResult

_TIER_DIR = Path(__file__).parent


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        # A session hook sees every collected item; the path check keeps the tiers apart.
        if Path(item.path).is_relative_to(_TIER_DIR):
            item.add_marker(pytest.mark.tier2)


@pytest.fixture
def cached_run(monkeypatch: pytest.MonkeyPatch) -> Callable[..., RunResult]:
    """Return a callable that re-walks an example's case against the store its README filled."""

    def walk(example: Path, case: str, upto: str | None = None) -> RunResult:
        monkeypatch.chdir(example)
        return Session(Store(example / "store"), write=False).run(Case.load(case), upto=upto)

    return walk


@pytest.fixture
def check_figures() -> Callable[[RunResult], None]:
    """Return the check that every declared figure of a cached run draws and displays."""

    def check(result: RunResult) -> None:
        assert all(record.cached for record in result.stages), result.record()["stages"]
        for record in result.stages:
            artefact = result.artefacts[record.name]
            declared = figure_target(artefact.schema) is not None
            figure = result.figure(record.name)
            assert (figure is not None) == declared, record.name
            if figure is not None:
                assert figure.axes, record.name
            html = artefact._repr_mimebundle_()["text/html"]
            assert ("data:image/png;base64," in html) == declared, record.name
        assert "data:image/png;base64," in result._repr_mimebundle_()["text/html"]

    return check
