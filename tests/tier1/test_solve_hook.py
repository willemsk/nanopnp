"""VER-44 — the structural solve hook: rungs and steps as numbers, and no moved hash.

Three claims, and the third is the one that would fail silently.

**The rungs arrive, all of them, in order, with their NUM-18 stage numbers.**
``_instrumented`` injects the damped-Newton callback only into a rung whose model
is a :class:`~nanopnp.physics.models.CoupledModel`, so the ladder's electrostatic
stages emit no Newton step at all. A hook that rode the Newton callback alone
would show them as a gap; one that rides ``on_rung`` shows them as rungs that ran
and kept no Newton record, which is what they are.

**A silent rung is silent for one of two reasons, and the hook says which.**
Measured on this file's ladder: of its twelve rungs, **two** take no callback
(``1-pb-linear`` and ``2-pb``, neither a coupled model) and **three** more are
coupled rungs that reported nothing because ``damped_newton`` found the
transferred state already below its target and returned before the first step
(``3-equilibrium-pnp``, ``7-corrections``, ``8-steric``). That second class is
the NUM-16 warm-start case, not a missing record, and a band annotated "not a
Newton solve" for it would be false.
So ``rung`` carries ``reporting``, taken from the same test that injects the
callback, and this file asserts that a rung which reported steps was reporting
and that a non-reporting rung reported none.

**The steps carry the residual and the undamped relative update as floats.** The
residual reaches a :class:`~nanopnp.core.stages.Progress` caller only inside a
``:.3e`` caption, and the update reaches it not at all. What is asserted here is
that the hook's numbers are the solver's own — the last step of each rung against
the ``newton`` record the stage wrote into its artefact — rather than a parse of a
display format.

**Watching a run must not move its artefact hash.** The hook is a callback, not
an input, and the driver rebinds the stage only after its key has been taken. So
the same case is run twice into one store, watched and unwatched, and what is
asserted is one hash and one *stored* solve: the second run is a cache hit, and a
cache hit emits no rung and no step at all (D4) — which is the state the shell
must name rather than draw as an empty plot.

The case is the cheapest one that walks the whole pipeline, as
``tests/tier1/test_run.py`` and ``tests/tier1/test_gui_solver_process.py`` use.
Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from nanopnp.core.stages import SolveReporting, create
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.newton import DEFAULT_SETTINGS

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0

CASE = """
schema: nanopnp/case/v1
name: hook-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder, stabilisation: none}}
outputs: [current]
"""


@dataclass
class Recorder:
    """A :class:`~nanopnp.core.stages.SolveHook` that keeps what it was told.

    Rungs and steps in one list, in arrival order, because the ordering *is* the
    claim: a step belongs to the rung most recently announced, and a reader that
    bands a series by rung is relying on nothing else.
    """

    events: list[tuple[str, tuple[object, ...]]] = field(default_factory=list)

    def rung(  # noqa: D102
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        self.events.append(("rung", (name, stage, index, total, reporting, tolerance)))

    def step(  # noqa: D102
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        self.events.append(("step", (iteration, residual, update, damping, trials, forced)))

    @property
    def rungs(self) -> list[tuple[object, ...]]:
        """Every rung call's arguments, in order."""
        return [payload for kind, payload in self.events if kind == "rung"]

    def banded(self) -> list[tuple[tuple[object, ...], list[tuple[object, ...]]]]:
        """Return each rung with the steps that arrived inside it."""
        bands: list[tuple[tuple[object, ...], list[tuple[object, ...]]]] = []
        for kind, payload in self.events:
            if kind == "rung":
                bands.append((payload, []))
            else:
                assert bands, "a Newton step arrived before any rung was announced"
                bands[-1][1].append(payload)
        return bands


@pytest.fixture(scope="module")
def case_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the case and the mesh it names, once for the module."""
    work = tmp_path_factory.mktemp("hook")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return path


def test_fr27_only_the_solve_stage_offers_the_reporting_capability() -> None:
    """``SolveReporting`` is satisfied by stage 10 and by none of the others.

    The point of delivering the hook by capability rather than by widening
    :class:`~nanopnp.core.stages.Stage`: eleven stages would have grown a
    keyword they can only ignore. Asserted in both directions, so a stage that
    grew a ``with_solve_hook`` by accident fails here.
    """
    from nanopnp.io.run import PIPELINE

    reporting = {name for name in PIPELINE if isinstance(create(name), SolveReporting)}
    assert reporting == {"solve"}


def test_ver44_the_hook_sees_every_rung_and_the_steps_inside_it(
    case_file: Path, tmp_path: Path
) -> None:
    """Every rung of the ladder is announced, and each step falls in its rung.

    The NUM-18 stage numbers are asserted non-decreasing rather than equal to a
    hard-coded list: a ramp expands into several rungs sharing one stage, and the
    ladder's shape is ``default_ladder``'s business, not this test's. What is
    this test's business is that a silent rung is *announced*, that it says why
    it will be silent, and that the numbers in a band are the solver's own.
    """
    hook = Recorder()
    result = run_case(case_file, store=Store(tmp_path / "store"), on_solve=hook)

    bands = hook.banded()
    assert bands, "the solve emitted no rung at all"
    assert [rung[2] for rung, _ in bands] == list(range(len(bands)))
    assert {rung[3] for rung, _ in bands} == {len(bands)}
    stages = [rung[1] for rung, _ in bands]
    assert stages == sorted(stages), stages
    # The NUM-16 tolerance travels with the rung so a reader can say which of the
    # two disjunctive tests the solver applied without importing the solver to
    # read a default it may not be using.
    assert {rung[5] for rung, _ in bands} == {DEFAULT_SETTINGS.relative_tolerance}

    # NUM-18's electrostatic rungs are announced, and silent by construction.
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

    # The solver's own record, not a second computation: the ladder's summary
    # carries the per-rung ``newton`` block, and the last step the hook saw in a
    # rung must be the residual and iteration count that block reports.
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
        # A reporting rung's step count is its iteration count, zero included:
        # a coupled rung that converged on entry records ``iterations: 0`` and
        # reports nothing, and the two agreeing is what makes an empty band
        # readable as "converged before the first step" rather than as a
        # dropped record.
        assert len(steps) == newton["iterations"], (name, len(steps), newton)
        if steps:
            assert steps[-1][1] == float(newton["residual"])


def test_ver44_watching_a_run_moves_no_hash_and_a_cached_solve_is_silent(
    case_file: Path, tmp_path: Path
) -> None:
    """The same case, watched and unwatched, is one artefact and one solve.

    §5.3.2's whole claim about the hook. The key is taken from the unbound stage
    and the driver rebinds only afterwards, so a run watched from the shell must
    land on the store entry the command line already made — asserted on the hash
    *and* on the store's own hit counter, because two equal hashes would also be
    produced by a second solve that happened to agree.

    The second half is D4: a solve served from the store never enters the
    ladder, so the hook is never called. An empty plot would read as a solve
    that converged instantly, which is why the shell has to be able to tell the
    two apart, and it can only do so if this is true.
    """
    store = Store(tmp_path / "store")
    cold = run_case(case_file, store=store)
    assert not next(record for record in cold.stages if record.name == "solve").cached

    hook = Recorder()
    warm = run_case(case_file, store=store, on_solve=hook)

    assert warm.artefacts["solve"].hash == cold.artefacts["solve"].hash
    assert next(record for record in warm.stages if record.name == "solve").cached
    assert hook.events == [], "a solve served from the store reported rungs it never climbed"

    # And the other order: the hook does not make the *first* run key differently
    # either. A fresh store, watched from cold, must reach the same hash.
    fresh = run_case(case_file, store=Store(tmp_path / "second"), on_solve=Recorder())
    assert fresh.artefacts["solve"].hash == cold.artefacts["solve"].hash


def test_ver44_the_hook_is_not_reachable_from_the_stage_key(
    case_file: Path, tmp_path: Path
) -> None:
    """A stage bound to a hook produces the same key as the stage without one.

    One level below the run: the rebinding is what the driver relies on, and it
    is sound only because :meth:`~nanopnp.solve.stage.SolveStage.key` cannot see
    the hook. Asserted on the stage itself so that a future key computed from
    the constructor's arguments fails here rather than by scattering a store.
    """
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.case import load_case

    document = load_case(case_file)
    inputs = StageInputs(case=document, upstream={}, options={})
    bare = create("solve", workspace=tmp_path / "bare")
    assert isinstance(bare, SolveReporting)
    watched = bare.with_solve_hook(Recorder())

    assert watched.key(inputs).hash == bare.key(inputs).hash  # type: ignore[attr-defined]
