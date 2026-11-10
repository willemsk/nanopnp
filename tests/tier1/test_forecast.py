"""FR-39 — the sweep forecast names the stages a run rebuilds, and runs none of them."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.api.sweep import plan_sweep, run_plan, run_point
from nanopnp.core.stages import create
from nanopnp.io.case import CaseDocument
from nanopnp.io.resolved import ResolvedCase
from nanopnp.pipeline import case as pipeline_case
from nanopnp.pipeline.run import open_run
from nanopnp.sweep.document import loads_sweep
from nanopnp.sweep.forecast import Forecast, forecast
from nanopnp.sweep.plan import PLAN_FILENAME, SweepPlan, build_plan, read_plan, write_plan

SWEEP = """\
schema: nanopnp/sweep/v0.5
name: forecast
base: base.case.yaml
axes:
  - {name: radius, path: geometry.pore.radius_nm, values: [2, 2.5]}
  - {name: bias, path: boundary_conditions.bias_V, values: [0.0, 0.05]}
"""


def _case() -> Case:
    return Case.cylinder(
        concentration_M=0.1, bias_V=0.0, maxh_nm=4.0, wall_h_nm=1.0, outputs=("current",)
    ).with_(
        **{
            "physics.model": "pnp",
            "physics.flow": False,
            "physics.variable_density": False,
            "physics.inertia": False,
            "physics.dielectric_gradient_forces": False,
            "numerics.continuation": "none",
            "electrolyte.corrections": {
                name: {"model": "none"}
                for name in ("diffusivity", "mobility", "viscosity", "permittivity", "density")
            }
            | {"steric": {"model": "none"}},
        }
    )


def _plan(directory: Path) -> SweepPlan:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "base.case.yaml").write_text(_case().dumps(), encoding="utf-8")
    source = directory / "forecast.sweep.yaml"
    source.write_text(SWEEP, encoding="utf-8")
    return build_plan(loads_sweep(SWEEP), source=source, check_meshes=False)


def _moved(found: Forecast, axis: str) -> set[str]:
    return set(found.axes[axis])


@pytest.fixture
def counted(monkeypatch: pytest.MonkeyPatch) -> Iterator[Counter[str]]:
    resolved: Counter[str] = Counter()
    original = pipeline_case.resolve

    def counting(document: CaseDocument, **kwargs: Path | None) -> ResolvedCase:
        resolved[document.name] += 1
        return original(document, **kwargs)

    for module in ("nanopnp.sweep.plan", "nanopnp.pipeline.run", "nanopnp.api.sweep"):
        monkeypatch.setattr(f"{module}.resolve", counting)
    yield resolved


def test_fr39_a_planned_sweep_resolves_each_member_once(
    tmp_path: Path, counted: Counter[str]
) -> None:
    # A plan that resolves its members again for the forecast, the run and each parent pays
    # four times for what it settled once.
    session = Session(tmp_path / "store", write=False)
    planned = plan_sweep(_case(), session=session, axis="bias_V", values=[0.0, 0.05, 0.1])
    names = [point.name for point in planned.plan.points]
    assert counted == Counter(names)

    counted.clear()
    planned.forecast()
    result = planned.run()
    assert counted == Counter(names)
    assert all(row["status"] == "ok" for row in result.rows)
    counted.clear()
    planned.forecast()
    assert not counted

    files = _plan(tmp_path / "files")
    counted.clear()
    forecast(files, store=session.store)
    directory = tmp_path / "filed"
    write_plan(files, directory)
    members = run_plan(files, directory, session=session)
    assert not counted
    assert [member.status for member in members] == ["ok"] * len(files.points)

    read = read_plan(planned.directory / PLAN_FILENAME)
    point = read.point(2)
    assert point.parent is not None
    member = run_point(read, 2, session=session, directory=planned.directory)
    assert member.status == "ok"
    assert counted == Counter([point.name, read.point(point.parent).name])
    assert all(read.held_member(index) is None for index in range(len(read.points)))


def test_fr39_the_forecast_equals_the_stages_the_walk_rebuilds(tmp_path: Path) -> None:
    # A forecast that disagrees with the walk misleads the author about what a sweep costs.
    plan = _plan(tmp_path / "files")
    session = Session(tmp_path / "store", write=False)
    before = forecast(plan, store=session.store)
    assert _moved(before, "radius") == {"case", "region", "mesh", "solve", "qoi", "report"}
    assert _moved(before, "bias") == {"case", "solve", "qoi", "report"}
    assert before.builds["mesh"] == 2 and before.builds["region"] == 2
    assert before.builds["solve"] == 4
    assert "radius" in before.warnings()[0] and "2 region and 2 mesh" in before.warnings()[0]
    assert not any("'bias'" in line for line in before.warnings())

    directory = tmp_path / "sweep"
    write_plan(plan, directory)
    results = run_plan(plan, directory, session=session)
    assert [member.status for member in results] == ["ok"] * 4
    for member in results:
        assert member.directory is not None
        walked = tuple(
            record.name for record in open_run(member.directory).stages if not record.cached
        )
        assert before.points[member.index] == walked

    after = forecast(plan, store=session.store)
    assert sum(after.builds.values()) == 0
    assert all(not stages for stages in after.points)


def test_fr39_the_forecast_never_runs_a_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A forecast that built a mesh would cost what it exists to warn about.
    plan = _plan(tmp_path / "files")
    store = Session(tmp_path / "store", write=False).store

    def refuse(self: object, *args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a forecast ran a stage")

    for name in ("case", "region", "mesh", "materials", "solve", "qoi", "report"):
        monkeypatch.setattr(
            type(create(name, store=store) if name == "mesh" else create(name)), "run", refuse
        )
    before = sorted(store.root.rglob("*"))
    found = forecast(plan, store=store)
    assert found.builds["mesh"] == 2
    assert sorted(store.root.rglob("*")) == before
