"""§8.2.11 L3 — the pull request's two shards, Tier 1 and Tier 2, and the ``no_cover`` marker."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def _collected(marker: str) -> set[str]:
    result = subprocess.run(
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
    return {line for line in result.stdout.splitlines() if "::" in line}


def test_l3_the_marker_shards_partition_the_selection_with_no_overlap() -> None:
    with ThreadPoolExecutor(max_workers=3) as pool:
        selections = [
            pool.submit(_collected, marker)
            for marker in (
                "tier1 and not slow",
                "tier2 and not slow",
                "(tier1 or tier2) and not slow",
            )
        ]
    first, second, both = (selection.result() for selection in selections)
    assert first and second
    assert not first & second
    assert first | second == both


def test_l3_the_ci_workflow_runs_the_two_tiers_as_its_shards() -> None:
    workflow = (REPOSITORY / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "shard: [tier1, tier2]" in workflow
    assert '-m "$SHARD and not slow"' in workflow
    assert "--shard" not in workflow


def test_ver72_the_no_cover_marker_the_conftest_applies_is_registered_without_pytest_cov() -> None:
    config = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(line.startswith("no_cover:") for line in markers)
