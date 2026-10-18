"""WP49's cost-study harness: its timers, projection, record and refusals (REV-112)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from nanopnp.io.case import read_case
from nanopnp.io.case_paths import value_at
from nanopnp.validation import costs

REPOSITORY = Path(__file__).resolve().parents[2]


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_a_nested_call_of_one_category_counts_once() -> None:
    clock = _Clock()
    timer = costs.CategoryTimer(clock)
    with timer.time("io"):
        clock.now += 1.0
        with timer.time("io"):
            clock.now += 2.0
    assert timer.totals == {"io": 3.0}


def test_a_nested_call_of_one_group_is_credited_to_the_outermost_category() -> None:
    clock = _Clock()
    timer = costs.CategoryTimer(clock)
    with timer.time("write", group="io"), timer.time("read", group="io"):
        clock.now += 0.5
    assert timer.totals == {"write": 0.5}


@pytest.mark.parametrize("names", [costs.A8_BUILD, costs.A16_IO, (costs.SOLVE_RUN,)])
def test_every_named_callable_resolves(names: tuple[str, ...]) -> None:
    for name in names:
        owner, attribute, found = costs.resolve(name)
        assert callable(found), name
        assert getattr(owner, attribute) == found


def test_a_renamed_callable_is_refused() -> None:
    with pytest.raises(costs.CostStudyError, match="nowhere_to_be_found"):
        costs.resolve("nanopnp.io.store.Store.nowhere_to_be_found")


def test_instrument_times_the_named_callable_and_restores_it() -> None:
    from nanopnp.io.store import Store

    original = Store.contains
    timer = costs.CategoryTimer()
    with costs.instrument(timer, {"probe": ["nanopnp.io.store.Store.contains"]}):
        assert Store.contains is not original
    assert Store.contains is original


def _probe(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    owner = ModuleType("nanopnp._cost_probe_owner")
    user = ModuleType("nanopnp._cost_probe_user")

    def read() -> int:
        return 7

    class Form:
        def __init__(self) -> None:
            self.terms = 0

        def __iadd__(self, other: int) -> Form:
            self.terms += other
            return self

        @staticmethod
        def build() -> int:
            return 3

        @classmethod
        def make(cls) -> str:
            return cls.__name__

    class Derived(Form):
        pass

    owner.read = read  # type: ignore[attr-defined]
    owner.Form = Form  # type: ignore[attr-defined]
    owner.Derived = Derived  # type: ignore[attr-defined]
    user.read = read  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, owner.__name__, owner)
    monkeypatch.setitem(sys.modules, user.__name__, user)
    return owner, user


def test_an_imported_function_is_timed_and_every_import_is_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, user = _probe(monkeypatch)
    original = owner.read
    timer = costs.CategoryTimer()
    late = ModuleType("nanopnp._cost_probe_late")
    with costs.instrument(timer, {"io": ["nanopnp._cost_probe_owner.read"]}):
        assert user.read is owner.read
        assert owner.read is not original
        assert user.read() == 7
        late.read = owner.read  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, late.__name__, late)
    assert "io" in timer.totals
    assert owner.read is original
    assert user.read is original
    assert late.read is original  # type: ignore[attr-defined]


def test_a_class_and_its_method_named_together_patch_the_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, _ = _probe(monkeypatch)
    form_class = owner.Form
    iadd = vars(form_class)["__iadd__"]
    timer = costs.CategoryTimer()
    names = ["nanopnp._cost_probe_owner.Form", "nanopnp._cost_probe_owner.Form.__iadd__"]
    with costs.instrument(timer, {"build": names}):
        form = owner.Form()
        timer.totals.clear()
        form += 2
        assert form.terms == 2
        assert "build" in timer.totals
    assert owner.Form is form_class
    assert vars(form_class)["__iadd__"] is iadd


def test_static_class_and_inherited_methods_survive_instrumentation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, _ = _probe(monkeypatch)
    form_class, derived = owner.Form, owner.Derived
    held = dict(vars(form_class))
    names = [
        "nanopnp._cost_probe_owner.Form.build",
        "nanopnp._cost_probe_owner.Form.make",
        "nanopnp._cost_probe_owner.Derived.make",
    ]
    timer = costs.CategoryTimer()
    with costs.instrument(timer, {"build": names}):
        assert form_class().build() == 3
        assert derived.make() == "Derived"
        assert form_class.make() == "Form"
    assert timer.totals["build"] >= 0.0
    assert vars(form_class)["build"] is held["build"]
    assert vars(form_class)["make"] is held["make"]
    assert "make" not in vars(derived)
    assert derived.make() == "Derived"


def test_the_projection_is_the_least_squares_line() -> None:
    points = [(16.0, 3.0 + 0.5 * 16), (32.0, 3.0 + 0.5 * 32), (64.0, 3.0 + 0.5 * 64)]
    assert costs.project(points, 1000.0) == pytest.approx(3.0 + 0.5 * 1000.0, abs=1e-9)


def test_the_record_carries_the_environment() -> None:
    record = costs.environment_record()
    assert record["cpu_count"]
    threads = record["threads"]
    assert isinstance(threads, dict)
    assert set(threads) == set(costs.THREAD_VARIABLES)
    versions = record["versions"]
    assert isinstance(versions, dict)
    assert versions["python"] and versions["nanopnp"]
    assert record["commit"]
    assert "dirty" in record
    json.dumps(record)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_the_record_says_whether_the_tree_differs_from_its_commit(tmp_path: Path) -> None:
    def git(*arguments: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(tmp_path), *arguments],
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    (tmp_path / "tracked.txt").write_text("a\n", encoding="utf-8")
    git("add", "tracked.txt")
    git("commit", "-q", "-m", "one")
    assert costs.environment_record(tmp_path)["dirty"] is False
    (tmp_path / "tracked.txt").write_text("b\n", encoding="utf-8")
    assert costs.environment_record(tmp_path)["dirty"] is True


def test_a8_refuses_a_stage_total_off_by_more_than_two_percent() -> None:
    with pytest.raises(costs.CostStudyError, match="off the recorded"):
        costs.check_stage_total(103.0, 100.0)
    costs.check_stage_total(101.0, 100.0)


def test_a_walk_entry_carries_each_legs_share_and_denominator() -> None:
    totals = {"solve-stage": 100.0, "build": 1.0, "io-write": 3.0, "io-read": 1.0}
    entry = costs.walk_entry(totals, 200.0, 100.0, ["a8", "a16"])
    assert entry["a8"] == {
        "build_s": 1.0,
        "stage10_s": 100.0,
        "share": 0.01,
        "threshold": costs.A8_THRESHOLD,
        "over": False,
    }
    a16 = entry["a16"]
    assert isinstance(a16, dict)
    assert a16["wall_s"] == 200.0
    assert a16["share"] == pytest.approx(0.02)
    assert a16["over"] is False
    assert set(costs.walk_entry(totals, 200.0, 100.0, ["a16"])) == {"a16"}
    over = costs.walk_entry({**totals, "build": 6.0}, 200.0, 100.0, ["a8"])["a8"]
    assert isinstance(over, dict)
    assert over["over"] is True


def test_a_walk_whose_stage_10_was_not_timed_is_refused() -> None:
    with pytest.raises(costs.CostStudyError, match="untimed"):
        costs.walk_entry({"build": 1.0}, 200.0, 100.0, ["a8"])
    with pytest.raises(costs.CostStudyError, match="off the recorded"):
        costs.walk_entry({"solve-stage": 90.0}, 200.0, 100.0, ["a8"])


def test_a_timed_call_outside_its_enclosing_call_is_not_counted() -> None:
    timer = costs.CategoryTimer()
    calls: list[int] = []

    def probe() -> int:
        calls.append(1)
        return 7

    wrapped = costs._timed(timer, "build", probe, None, "solve")
    assert wrapped() == 7
    assert "build" not in timer.totals
    with timer.time("solve"):
        assert timer.active("solve")
        wrapped()
    assert "build" in timer.totals
    assert not timer.active("solve")
    assert len(calls) == 2


def test_a_name_that_is_not_callable_or_not_importable_is_refused() -> None:
    with pytest.raises(costs.CostStudyError, match="not callable"):
        costs.resolve("nanopnp.validation.costs.THREAD_VARIABLES")
    with pytest.raises(costs.CostStudyError, match="nothing that can be imported"):
        costs.resolve("no_such_package_here.thing")


def test_the_record_survives_a_missing_package_and_a_missing_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def absent(name: str) -> str:
        raise costs.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(costs.metadata, "version", absent)
    record = costs.environment_record(tmp_path)
    versions = record["versions"]
    assert isinstance(versions, dict)
    assert versions["numpy"] == "not installed"

    def no_git(*args: object, **kwargs: object) -> object:
        raise OSError("no git")

    monkeypatch.setattr(costs.subprocess, "run", no_git)
    record = costs.environment_record(tmp_path)
    assert record["commit"] == "unknown"
    assert record["dirty"] is None


def test_peak_memory_is_a_positive_number_of_megabytes() -> None:
    if costs.resource is None:
        with pytest.raises(costs.CostStudyError, match="resource module"):
            costs._peak_rss_mb()
    else:
        assert costs._peak_rss_mb() > 0.0


def test_a_failed_child_is_refused_and_a_good_child_is_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Done:
        def __init__(self, code: int, out: str) -> None:
            self.returncode = code
            self.stdout = out
            self.stderr = "boom"

    monkeypatch.setattr(costs.subprocess, "run", lambda *a, **k: Done(1, ""))
    with pytest.raises(costs.CostStudyError, match="boom"):
        costs._run_child(["_a1"])
    monkeypatch.setattr(costs.subprocess, "run", lambda *a, **k: Done(0, 'noise\n{"a": 1}\n'))
    assert costs._run_child(["_a1"]) == {"a": 1}
    monkeypatch.setattr(
        costs.subprocess, "run", lambda *a, **k: Done(0, '{"a": 2}\n{not json\n[3]\nbye\n')
    )
    assert costs._run_child(["_a1"]) == {"a": 2}
    monkeypatch.setattr(costs.subprocess, "run", lambda *a, **k: Done(0, ""))
    with pytest.raises(costs.CostStudyError, match="no result"):
        costs._run_child(["_a1"])


def test_the_a1_case_is_the_charged_example_with_an_ensemble(tmp_path: Path) -> None:
    pdb, dcd = tmp_path / "p.pdb", tmp_path / "t.dcd"
    case = costs._a1_case(REPOSITORY, pdb, dcd, tmp_path / "a1.case.yaml")
    document = read_case(case)
    example = read_case(REPOSITORY / costs.CHARGED_CASE)
    assert value_at(document, "structure.source.path") == pdb
    assert value_at(document, "structure.ensemble.trajectory") == dcd
    assert document.charge is None
    assert value_at(document, "physics.solid_permittivities") == value_at(
        example, "physics.solid_permittivities"
    )


def test_the_mesher_command_is_found_beside_the_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert Path(costs._nanopnp()).parent == Path(sys.executable).parent
    monkeypatch.setattr(costs.sys, "executable", str(tmp_path / "python"))
    with pytest.raises(costs.CostStudyError, match="no nanopnp command"):
        costs._nanopnp()


def test_a_child_leg_prints_its_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[object] = []

    def a1(case: Path, store: Path, upto: str) -> dict[str, object]:
        seen.append((case, store, upto))
        return {"peak_mb": 1.5}

    def walk(case: Path, store: Path, legs: list[str]) -> dict[str, object]:
        seen.append((case, store, legs))
        return {"wall_s": 2.0}

    monkeypatch.setattr(costs, "_a1_child", a1)
    monkeypatch.setattr(costs, "_walk", walk)
    assert costs.main(["_a1", "c", "s", "structure"]) == 0
    assert json.loads(capsys.readouterr().out) == {"peak_mb": 1.5}
    assert costs.main(["_walk", "c", "s", "a8", "a16"]) == 0
    assert json.loads(capsys.readouterr().out) == {"wall_s": 2.0}
    assert seen == [(Path("c"), Path("s"), "structure"), (Path("c"), Path("s"), ["a8", "a16"])]


def test_each_leg_keeps_the_environment_it_was_measured_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runs = iter(range(1, 10))
    monkeypatch.setattr(costs, "environment_record", lambda repository: {"run": next(runs)})
    monkeypatch.setattr(costs, "measure_a1", lambda repository: {"over": False})

    def walks(repository: Path, legs: list[str]) -> dict[str, dict[str, object]]:
        return {"quickstart": {leg: {"share": 0.01} for leg in legs}}

    monkeypatch.setattr(costs, "measure_walks", walks)
    out = tmp_path / "record.json"
    arguments = ["--repository", str(tmp_path), "--out", str(out)]
    for leg in ("a1", "a8", "a16"):
        assert costs.main([leg, *arguments]) == 0
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["environment"] == {"a1": {"run": 1}, "a8": {"run": 2}, "a16": {"run": 3}}
    assert set(record["walks"]["quickstart"]) == {"a8", "a16"}
    assert costs.main(["all", *arguments]) == 0
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["environment"] == {leg: {"run": 4} for leg in ("a1", "a8", "a16")}
