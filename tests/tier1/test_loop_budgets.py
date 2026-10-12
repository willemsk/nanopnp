"""VER-73 — the development loop's budgets are recorded and CI holds them (WP43 D11; §8.2.10 J7).

``.github/budgets.yaml`` records the budgets J7 pre-registered and the margin WP43
argues. ``.github/scripts/ci_budget.py`` reads a workflow run's jobs, as the
GitHub API lists them, and fails a pull-request run whose critical path exceeds
its budget by more than the margin. The oracle is J7's: a budget recorded below
the measured duration must fail.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
PLANNED = "planned: WP43 D11 (VER-73)"


def _checker() -> ModuleType:
    path = REPOSITORY / ".github/scripts/ci_budget.py"
    spec = importlib.util.spec_from_file_location("ci_budget", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _job(name: str, started: str, completed: str | None) -> dict[str, object]:
    return {
        "name": name,
        "status": "completed" if completed else "in_progress",
        "started_at": f"2026-10-12T10:{started}Z",
        "completed_at": f"2026-10-12T10:{completed}Z" if completed else None,
    }


# Lint 10:00:05-10:01:05; the two shards end at 10:04:30 and 10:05:00; coverage at
# 10:06:00. The critical path runs from the first start to the last completion: 355 s.
JOBS = [
    _job("lint", "00:05", "01:05"),
    _job("tests (shard 1/2)", "00:06", "04:30"),
    _job("tests (shard 2/2)", "00:07", "05:00"),
    _job("coverage", "05:10", "06:00"),
]


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_the_budgets_are_j7s_and_the_ceiling_and_margin_the_plans() -> None:
    budgets = yaml.safe_load((REPOSITORY / ".github/budgets.yaml").read_text(encoding="utf-8"))
    assert budgets == {
        "commit_hook_s": 60,
        "push_gate_s": 300,
        "pull_request_critical_path_s": 360,
        "file_ceiling_s": 90,
        "margin": 0.5,
    }


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_the_critical_path_spans_the_first_start_to_the_last_completion() -> None:
    assert _checker().critical_path_s(JOBS) == pytest.approx(355.0)


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_a_budget_below_the_measured_duration_beyond_the_margin_fails() -> None:
    """355 s against 200 s with a 50 % margin (300 s) fails, naming all three figures."""
    passed, message = _checker().check(JOBS, budget_s=200.0, margin=0.5)
    assert not passed
    assert "355" in message
    assert "200" in message
    assert "50 %" in message


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_a_run_over_budget_but_within_the_margin_passes_and_says_so() -> None:
    """355 s against 300 s with a 50 % margin (450 s) passes, reporting the overrun."""
    passed, message = _checker().check(JOBS, budget_s=300.0, margin=0.5)
    assert passed
    assert "over budget" in message


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_an_unfinished_job_fails_rather_than_shortening_the_path() -> None:
    jobs = [*JOBS[:-1], _job("coverage", "05:10", None)]
    passed, message = _checker().check(jobs, budget_s=360.0, margin=0.5)
    assert not passed
    assert "coverage" in message


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_ver73_a_file_over_its_ceiling_beyond_the_margin_fails_naming_it() -> None:
    """The hook's wall time is bounded below by its longest file, so each file has a ceiling."""
    durations = {"tests/tier1/test_fast.py": 3.0, "tests/tier2/test_long.py": 136.0}
    passed, message = _checker().check_files(durations, ceiling_s=90.0, margin=0.5)
    assert not passed
    assert "tests/tier2/test_long.py" in message
    assert "test_fast" not in message
    passed, _ = _checker().check_files(durations, ceiling_s=100.0, margin=0.5)
    assert passed
