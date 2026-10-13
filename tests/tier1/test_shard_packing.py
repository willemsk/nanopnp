"""VER-73 and §8.2.10 J4 — CI's test shards partition the selection, packed by duration (WP43 D10).

A pull request runs the development selection as two shards, ``--shard 1/2`` and
``--shard 2/2`` (``tests/conftest.py``). A shard that dropped a file would leave
it untested with every job green, so the oracle here is the partition: every
file lands in exactly one shard, whole. The packing is longest-first onto the
least-loaded shard, from ``tests/durations.json``, and a file it has no time for
takes the median, so a new file is neither first nor forgotten.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from tests.conftest import (
    DURATIONS,
    file_order,
    parse_shard,
    recorded_durations,
    shard_files,
)

REPOSITORY = Path(__file__).resolve().parents[2]


def test_ver73_j4_shards_partition_the_files_whole_whatever_the_durations() -> None:
    files = [f"tests/tier1/test_{name}.py" for name in "abcdefghij"]
    durations = {files[0]: 120.0, files[3]: 5.0, files[4]: 60.0, "tests/gone.py": 300.0}
    for count in (1, 2, 3, 7, 12):
        shards = shard_files(files, durations, count)
        assert len(shards) == count
        placed = [name for shard in shards for name in shard]
        assert sorted(placed) == sorted(files), count


def test_ver73_j4_the_longest_file_goes_first_to_the_least_loaded_shard() -> None:
    durations = {"a.py": 100.0, "b.py": 60.0, "c.py": 50.0, "d.py": 10.0}
    # a -> 1 (100); b -> 2 (60); c -> 2 (110); d -> 1 (110).
    assert shard_files(list(durations), durations, 2) == [["a.py", "d.py"], ["b.py", "c.py"]]
    # Equal loads go to the lower index.
    assert shard_files(["x.py", "y.py"], {"x.py": 1.0, "y.py": 1.0}, 2) == [["x.py"], ["y.py"]]


def test_ver73_j4_a_file_with_no_recorded_time_takes_the_median() -> None:
    durations = {"a.py": 100.0, "b.py": 10.0, "c.py": 30.0}
    assert file_order(["b.py", "z.py", "c.py", "a.py"], durations) == [
        "a.py",
        "c.py",
        "z.py",
        "b.py",
    ]
    assert file_order(["q.py", "p.py"], {}) == ["p.py", "q.py"]


@pytest.mark.parametrize("value", ["0/2", "3/2", "1/0", "x/2", "2", "1/2/3"])
def test_ver73_j4_a_shard_outside_one_to_n_is_refused(value: str) -> None:
    with pytest.raises(pytest.UsageError, match="--shard"):
        parse_shard(value)


def test_ver73_j4_the_committed_durations_are_read_and_name_test_files() -> None:
    durations = recorded_durations(DURATIONS)
    assert durations, "tests/durations.json records no file"
    for name, seconds in durations.items():
        assert name.startswith("tests/") and name.endswith(".py"), name
        assert seconds >= 0.0, name


def test_ver73_j4_an_unreadable_durations_file_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "durations.json"
    broken.write_text('{"schema": "nanopnp/durations/v1"}', encoding="utf-8")
    with pytest.raises(pytest.UsageError, match="durations"):
        recorded_durations(broken)
    assert recorded_durations(tmp_path / "absent.json") == {}


def test_ver73_the_no_cover_marker_the_conftest_applies_is_registered_without_pytest_cov() -> None:
    """``--strict-markers`` refuses a marker nobody registered, and only pytest-cov defines this.

    With pytest-cov off (``-p no:cov``) every ``--extended`` run would otherwise end in an
    internal error as the conftest marks the walks.
    """
    config = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(line.startswith("no_cover:") for line in markers)
