"""§8.2.11 L3 — the pull request's two shards, Tier 1 and Tier 2, and the ``no_cover`` marker."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]


def _collect(marker: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            marker,
            "tests",
        ],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_l3_the_marker_shards_partition_the_selection_with_no_overlap() -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        selected = pool.submit(_collect, "(tier1 or tier2) and not slow")
        both = pool.submit(_collect, "tier1 and tier2")
    selection, overlap = selected.result(), both.result()
    assert selection.returncode == 0, selection.stdout[-2000:] + selection.stderr[-2000:]
    assert any("tests/tier1/" in line for line in selection.stdout.splitlines())
    assert any("tests/tier2/" in line for line in selection.stdout.splitlines())
    assert overlap.returncode == pytest.ExitCode.NO_TESTS_COLLECTED, overlap.stdout[-2000:]
    assert "::" not in overlap.stdout


def test_l3_the_ci_workflow_runs_the_two_tiers_as_its_shards() -> None:
    workflow = (REPOSITORY / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "shard: [tier1, tier2]" in workflow
    assert '-m "$SHARD and not slow"' in workflow
    assert "--shard" not in workflow


def test_ver72_the_no_cover_marker_the_conftest_applies_is_registered_without_pytest_cov() -> None:
    config = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(line.startswith("no_cover:") for line in markers)
