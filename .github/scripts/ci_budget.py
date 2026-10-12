"""VER-73: hold a pull request's CI run to the budgets of ``.github/budgets.yaml``.

Two checks, each failing past its budget by more than the recorded margin
(SPECIFICATION.md section 7.6 budget NOTE; WP43 D11):

- ``critical-path``: the run's critical path, from the first job's start to the
  last measured job's completion, read from the GitHub API, against
  ``pull_request_critical_path_s``;
- ``files``: each test file's duration in the shards' junit reports against
  ``file_ceiling_s``, because the commit hook's wall time is bounded below by the
  longest file it selects.

Both write their figures to ``$GITHUB_STEP_SUMMARY`` where it is set, so every
run publishes its durations (section 8.2.10 J7)::

    uv run python .github/scripts/ci_budget.py critical-path --repo O/R --run ID --attempt N
        --running coverage --exclude "CI result"
    uv run python .github/scripts/ci_budget.py files junit-1.xml junit-2.xml
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
BUDGETS = REPOSITORY / ".github" / "budgets.yaml"


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def unfinished(jobs: Iterable[Mapping[str, Any]]) -> list[str]:
    """Return the names of the jobs that have not completed."""
    return [
        str(job["name"])
        for job in jobs
        if job.get("status") != "completed" or not job.get("completed_at")
    ]


def critical_path_s(jobs: Sequence[Mapping[str, Any]]) -> float:
    """Return the seconds from the first job's start to the last job's completion.

    Raises
    ------
    ValueError
        If a job has not completed, naming it: an unfinished job would shorten the
        path and pass a run that has not ended.
    """
    waiting = unfinished(jobs)
    if waiting:
        raise ValueError(f"unfinished job(s): {', '.join(waiting)}")
    if not jobs:
        raise ValueError("no jobs to measure")
    first = min(_instant(str(job["started_at"])) for job in jobs)
    last = max(_instant(str(job["completed_at"])) for job in jobs)
    return (last - first).total_seconds()


def _judge(measured: float, budget_s: float, margin: float, what: str) -> tuple[bool, str]:
    limit = budget_s * (1.0 + margin)
    figures = (
        f"{what} {measured:.0f} s against a budget of {budget_s:.0f} s "
        f"with a {margin * 100:.0f} % margin (limit {limit:.0f} s)"
    )
    if measured > limit:
        return False, f"{figures}: over budget beyond the margin"
    if measured > budget_s:
        return True, f"{figures}: over budget, inside the margin"
    return True, f"{figures}: within budget"


def check(jobs: Sequence[Mapping[str, Any]], budget_s: float, margin: float) -> tuple[bool, str]:
    """Judge a run's critical path against ``budget_s`` with ``margin``.

    Returns ``(passed, message)``. The message names the measured value, the
    budget and the margin as a percentage; a pass inside the margin says "over
    budget", and an unfinished job fails, named.
    """
    try:
        measured = critical_path_s(jobs)
    except ValueError as error:
        return False, f"critical path not measured: {error}"
    return _judge(measured, budget_s, margin, "critical path")


def check_files(
    durations: Mapping[str, float], ceiling_s: float, margin: float
) -> tuple[bool, str]:
    """Judge every file's duration against ``ceiling_s`` with ``margin``.

    Returns ``(passed, message)``; a failure names each file beyond the margin, and
    no other.
    """
    limit = ceiling_s * (1.0 + margin)
    over = {name: seconds for name, seconds in durations.items() if seconds > limit}
    rule = (
        f"a ceiling of {ceiling_s:.0f} s with a {margin * 100:.0f} % margin (limit {limit:.0f} s)"
    )
    if over:
        named = "; ".join(f"{name} {seconds:.0f} s" for name, seconds in sorted(over.items()))
        return False, f"test files over {rule}: {named}"
    if not durations:
        return True, f"no test file measured against {rule}"
    longest = max(durations, key=lambda name: durations[name])
    return True, f"every test file within {rule}; longest {longest} {durations[longest]:.0f} s"


def junit_durations(reports: Iterable[Path], root: Path = REPOSITORY) -> dict[str, float]:
    """Return each test file's seconds, summed over its test cases in junit ``reports``.

    pytest's junit ``time`` covers setup, call and teardown, so a module fixture is
    counted, in the first test that asks for it. The file is the longest prefix of
    the dotted ``classname`` that names a file under ``root``.
    """
    totals: dict[str, float] = {}
    for report in reports:
        for case in ElementTree.parse(report).iter("testcase"):
            parts = case.get("classname", "").split(".")
            for end in range(len(parts), 0, -1):
                candidate = "/".join(parts[:end]) + ".py"
                if (root / candidate).is_file():
                    totals[candidate] = totals.get(candidate, 0.0) + float(case.get("time", 0))
                    break
    return totals


def run_jobs(repo: str, run: str, attempt: str) -> list[dict[str, Any]]:
    """Return one attempt's jobs of a workflow run, as the GitHub API lists them."""
    endpoint = f"repos/{repo}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100"
    listed = subprocess.run(
        ["gh", "api", "--paginate", endpoint, "--jq", ".jobs[]"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [json.loads(line) for line in listed.splitlines() if line.strip()]


def _summary(lines: Iterable[str]) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with Path(target).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n\n")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ci_budget.py", description=__doc__.splitlines()[0])
    parser.add_argument("--budgets", type=Path, default=BUDGETS)
    commands = parser.add_subparsers(dest="command", required=True)
    path = commands.add_parser("critical-path", help="judge a run's critical path")
    path.add_argument("--repo", required=True)
    path.add_argument("--run", required=True)
    path.add_argument("--attempt", default="1")
    path.add_argument(
        "--running",
        default=None,
        help="the job making the check: still in progress, it is measured as ending now",
    )
    path.add_argument("--exclude", action="append", default=[], help="a job that is not measured")
    files = commands.add_parser("files", help="judge each test file against its ceiling")
    files.add_argument("reports", type=Path, nargs="+")
    arguments = parser.parse_args(argv)
    budgets = yaml.safe_load(arguments.budgets.read_text(encoding="utf-8"))
    margin = float(budgets["margin"])

    if arguments.command == "files":
        durations = junit_durations(arguments.reports)
        passed, message = check_files(durations, float(budgets["file_ceiling_s"]), margin)
        longest = sorted(durations.items(), key=lambda pair: -pair[1])[:15]
        _summary(
            [
                "### Test files, longest first (junit, setup + call + teardown)",
                "",
                "| File | Seconds |",
                "|---|---|",
                *(f"| `{name}` | {seconds:.1f} |" for name, seconds in longest),
                "",
                message,
            ]
        )
        print(message)
        return 0 if passed else 1

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    jobs = []
    for job in run_jobs(arguments.repo, arguments.run, arguments.attempt):
        if job["name"] in arguments.exclude or job.get("conclusion") == "skipped":
            continue
        if job["name"] == arguments.running:
            job = {**job, "status": "completed", "completed_at": now}
        jobs.append(job)
    passed, message = check(jobs, float(budgets["pull_request_critical_path_s"]), margin)
    rows = [
        f"| {job['name']} | {job.get('started_at')} | {job.get('completed_at')} |" for job in jobs
    ]
    _summary(
        [
            "### Critical path (VER-73)",
            "",
            "| Job | Started | Completed |",
            "|---|---|---|",
            *rows,
            "",
            message,
        ]
    )
    print(message)
    if arguments.attempt != "1":
        # A re-run attempt carries the first attempt's finished jobs with their
        # original times, so its span measures the wait for a re-run, not the run.
        print(f"attempt {arguments.attempt}: the critical path is reported, not judged")
        return 0
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(_main())
