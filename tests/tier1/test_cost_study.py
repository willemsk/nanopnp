"""WP49's cost-study harness: its timers, projection, record and refusals (REV-112)."""

from __future__ import annotations

import json
import time

import pytest

from nanopnp.validation import costs


def test_a_nested_call_of_one_category_counts_once() -> None:
    timer = costs.CategoryTimer()

    def inner() -> None:
        with timer.time("io"):
            time.sleep(0.05)

    with timer.time("io"):
        time.sleep(0.05)
        inner()
    assert timer.totals["io"] == pytest.approx(0.10, abs=0.04)
    assert timer.totals["io"] < 0.05 + 0.05 + 0.05


def test_a_nested_call_of_one_group_is_credited_to_the_outermost_category() -> None:
    timer = costs.CategoryTimer()
    with timer.time("write", group="io"), timer.time("read", group="io"):
        time.sleep(0.02)
    assert "read" not in timer.totals
    assert timer.totals["write"] >= 0.02


@pytest.mark.parametrize("names", [costs.A8_BUILD, costs.A16_IO, (costs.SOLVE_RUN,)])
def test_every_named_callable_resolves(names: tuple[str, ...]) -> None:
    for name in names:
        owner, attribute, found = costs.resolve(name)
        assert callable(found), name
        assert getattr(owner, attribute) is found


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
    json.dumps(record)


def test_a8_refuses_a_stage_total_off_by_more_than_two_percent() -> None:
    with pytest.raises(costs.CostStudyError, match="off the recorded"):
        costs.check_stage_total(103.0, 100.0)
    costs.check_stage_total(101.0, 100.0)
