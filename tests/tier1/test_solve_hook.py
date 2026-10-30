"""VER-44: the structural solve hook, its rungs and steps, and the store key it leaves alone."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nanopnp.core.stages import SolveReporting, create, walk_order
from nanopnp.io.store import Store
from nanopnp.numerics.newton import DEFAULT_SETTINGS
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import run_case


@dataclass
class Recorder:
    events: list[tuple[str, tuple[object, ...]]] = field(default_factory=list)

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        self.events.append(("rung", (name, stage, index, total, reporting, tolerance)))

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        self.events.append(("step", (iteration, residual, update, damping, trials, forced)))

    def rung_solved(self, name: str, seconds: float, iterations: int) -> None:
        self.events.append(("solved", (name, seconds, iterations)))

    @property
    def rungs(self) -> list[tuple[object, ...]]:
        return [payload for kind, payload in self.events if kind == "rung"]

    def banded(self) -> list[tuple[tuple[object, ...], list[tuple[object, ...]]]]:
        bands: list[tuple[tuple[object, ...], list[tuple[object, ...]]]] = []
        for kind, payload in self.events:
            if kind == "rung":
                bands.append((payload, []))
            elif kind == "step":
                assert bands, "a Newton step arrived before any rung was announced"
                bands[-1][1].append(payload)
        return bands


def test_fr27_only_the_solve_stage_offers_the_reporting_capability() -> None:
    reporting = {name for name in walk_order() if isinstance(create(name), SolveReporting)}
    assert reporting == {"solve"}


def test_ver44_the_hook_sees_every_rung_and_the_steps_inside_it(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    hook = Recorder()
    result = run_case(cylindrical_pore_case, store=Store(tmp_path / "store"), on_solve=hook)

    bands = hook.banded()
    assert bands, "the solve emitted no rung at all"
    assert [rung[2] for rung, _ in bands] == list(range(len(bands)))
    assert {rung[3] for rung, _ in bands} == {len(bands)}
    stages = [rung[1] for rung, _ in bands]
    assert stages == sorted(stages), stages
    # The rung carries its NUM-16 tolerance, so the tests the solver applied are readable here.
    assert {rung[5] for rung, _ in bands} == {DEFAULT_SETTINGS.relative_tolerance}

    assert any(not rung[4] for rung, _ in bands), "every rung claimed to report Newton steps"
    assert any(steps for _, steps in bands), "no rung emitted any Newton step"
    for rung, steps in bands:
        if not rung[4]:
            assert not steps, f"rung {rung[0]!r} took no callback yet reported {len(steps)} steps"

    for _, steps in bands:
        assert [step[0] for step in steps] == list(range(1, len(steps) + 1))
        for _, residual, update, damping, trials, forced in steps:
            assert isinstance(residual, float) and residual >= 0.0
            assert isinstance(update, float) and update >= 0.0
            assert 0.0 < damping <= 1.0
            assert isinstance(trials, int) and trials >= 1
            assert isinstance(forced, bool)

    # The solver's own per-rung record: the last step a rung saw is the residual and iteration
    # count its newton block reports.
    ladder = result.artefacts["solve"].summary["rungs"]
    assert isinstance(ladder, list)
    recorded = {
        str(entry["rung"]): entry["newton"]
        for entry in ladder
        if isinstance(entry, dict) and isinstance(entry.get("newton"), dict)
    }
    banded = {str(rung[0]): (rung[4], steps) for rung, steps in bands}
    assert set(banded) >= set(recorded), (sorted(banded), sorted(recorded))
    for name, (reporting, steps) in banded.items():
        newton = recorded.get(name)
        if not reporting or newton is None:
            continue
        # Zero steps is a rung that converged on entry: the band reads empty, not dropped.
        assert len(steps) == newton["iterations"], (name, len(steps), newton)
        if steps:
            assert steps[-1][1] == float(newton["residual"])


def test_ver44_the_end_of_rung_call_carries_the_manifests_seconds(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    hook = Recorder()
    result = run_case(cylindrical_pore_case, store=Store(tmp_path / "store"), on_solve=hook)
    solved = [payload for kind, payload in hook.events if kind == "solved"]
    ladder = result.artefacts["solve"].summary["rungs"]
    assert isinstance(ladder, list)
    assert [name for name, _, _ in solved] == [entry["rung"] for entry in ladder]
    assert [seconds for _, seconds, _ in solved] == [entry["seconds"] for entry in ladder]
    assert [iterations for _, _, iterations in solved] == [
        0 if entry["newton"] is None else entry["newton"]["iterations"] for entry in ladder
    ]
    # Each rung is announced, then solved, before the next is announced.
    order = [kind for kind, _ in hook.events if kind in {"rung", "solved"}]
    assert order == ["rung", "solved"] * len(ladder)


def test_ver44_watching_a_run_moves_no_hash_and_a_cached_solve_is_silent(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    cold = run_case(cylindrical_pore_case, store=store)
    assert not next(record for record in cold.stages if record.name == "solve").cached

    hook = Recorder()
    warm = run_case(cylindrical_pore_case, store=store, on_solve=hook)

    assert warm.artefacts["solve"].hash == cold.artefacts["solve"].hash
    assert next(record for record in warm.stages if record.name == "solve").cached
    assert hook.events == [], "a solve served from the store reported rungs it never climbed"

    fresh = run_case(cylindrical_pore_case, store=Store(tmp_path / "second"), on_solve=Recorder())
    assert fresh.artefacts["solve"].hash == cold.artefacts["solve"].hash


def test_ver44_the_hook_is_not_reachable_from_the_stage_key(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    from nanopnp.io.artefact import StageInputs
    from nanopnp.pipeline.case import load_case

    document = load_case(cylindrical_pore_case)
    inputs = StageInputs(resolved=resolve(document), upstream={}, options={})
    bare = create("solve", workspace=tmp_path / "bare")
    assert isinstance(bare, SolveReporting)
    watched = bare.with_solve_hook(Recorder())

    assert watched.key(inputs).hash == bare.key(inputs).hash  # type: ignore[attr-defined]
