"""VER-63: every findings log under ``docs/`` is well formed (section 8.2.7 G4; WP35 D17).

Every real log must pass :func:`~nanopnp.validation.findings.check_log`, and the
check is shown to refuse each defect it claims to: a log built here, valid but for
one row, is refused naming that row, so the check cannot pass by accepting
anything. Once a log's header says ``closed``, a row that is not terminal is
refused, which is how Phase 4's close is asserted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.findings import (
    REPOSITORY,
    check_log,
    counts,
    logs,
    parse_log,
)

REPORT = """# Report

### MOD-01 — A finding

### MOD-02 — Another
"""

HEADER = """---
findings:
  prefix: MOD
  status: {status}
  areas: [stages, coupling]
---

# Log

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
"""

ANOTHER = "[x](report.md#mod-02-another)"
"""A finding cell linking to the second heading of :data:`REPORT`."""

GOOD = "| MOD-01 | stages | high | open | — | [A finding](report.md#mod-01-a-finding) |"
"""A valid open row, linking to a heading of :data:`REPORT`."""


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Return a repository holding a specification with section 8.2.7 G4, a plan and a report."""
    (tmp_path / "SPECIFICATION.md").write_text(
        "#### 8.2.7 Phase 4\n\n| # | Decision |\n|---|---|\n| G4 | Logs |\n\n### 8.3 Next\n\n"
        "| G9 | not in 8.2 |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "plans" / "wp36.md").write_text("# WP36\n", encoding="utf-8")
    (tmp_path / "docs" / "project").mkdir()
    (tmp_path / "docs" / "project" / "report.md").write_text(REPORT, encoding="utf-8")
    return tmp_path


def _log(repository: Path, *rows: str, status: str = "open", name: str = "x-findings.md") -> Path:
    path = repository / "docs" / "project" / name
    path.write_text(HEADER.format(status=status) + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_ver63_every_log_in_the_repository_passes() -> None:
    found = logs()
    assert REPOSITORY / "docs" / "project" / "modularity-findings.md" in found
    for path in found:
        assert check_log(path) == (), check_log(path)


def test_ver63_a_valid_log_passes_and_counts(repository: Path) -> None:
    fixed = f"| MOD-02 | coupling | low | fixed | [WP36](../plans/wp36.md) | {ANOTHER} |"
    path = _log(repository, GOOD, fixed)
    assert check_log(path, repository) == ()
    tally = counts(parse_log(path))
    assert tally.status == {"open": 1, "fixed": 1}
    assert tally.area == {"stages": 1, "coupling": 1}
    assert tally.severity == {"high": 1, "low": 1}


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("| MOD-02 | stages | high | open | — |", "has 5 columns, not 6"),
        ("| MOD-2 | stages | high | open | — | [x](report.md#mod-02-another) |", "is not MOD-nn"),
        ("| UT-02 | stages | high | open | — | [x](report.md#mod-02-another) |", "is not MOD-nn"),
        ("| MOD-01 | stages | high | open | — | [x](report.md#mod-02-another) |", "repeats the id"),
        ("| MOD-02 | gui | high | open | — | [x](report.md#mod-02-another) |", "area 'gui'"),
        (
            "| MOD-02 | stages | dire | open | — | [x](report.md#mod-02-another) |",
            "severity 'dire'",
        ),
        (
            "| MOD-02 | stages | high | wontfix | — | [x](report.md#mod-02-another) |",
            "status 'wontfix'",
        ),
        (
            "| MOD-02 | stages | high | open | §8.2.7 G4 | [x](report.md#mod-02-another) |",
            "is open, so its ruling must be '—'",
        ),
        (
            "| MOD-02 | stages | high | deferred | — | [x](report.md#mod-02-another) |",
            "must be a section 8.2 row",
        ),
        (
            "| MOD-02 | stages | high | deferred | §8.2.7 G5 | [x](report.md#mod-02-another) |",
            "names no row of SPECIFICATION.md section 8.2.7",
        ),
        (
            "| MOD-02 | stages | high | declined | §8.2.6 G4 | [x](report.md#mod-02-another) |",
            "names no row of SPECIFICATION.md section 8.2.6",
        ),
        (
            "| MOD-02 | stages | high | fixed | §8.2.7 G4 | [x](report.md#mod-02-another) |",
            "must link to a plan under docs/plans/",
        ),
        (
            f"| MOD-02 | stages | high | fixed | [x](../plans/wp99.md) | {ANOTHER} |",
            "must link to a plan under docs/plans/",
        ),
        (
            f"| MOD-02 | stages | high | accepted | [x](../plans/wp36.md) | {ANOTHER} |",
            "must be a section 8.2 row",
        ),
        ("| MOD-02 | stages | high | open | — | MOD-02 |", "must link to its section"),
        ("| MOD-02 | stages | high | open | — | [x](report.md#mod-03) |", "anchor #mod-03"),
        (
            "| MOD-02 | stages | high | open | — | [x](gone.md#mod-02) |",
            "'gone.md', which is not a file",
        ),
    ],
)
def test_ver63_a_bad_row_is_refused_naming_it(repository: Path, row: str, message: str) -> None:
    path = _log(repository, GOOD, row)
    errors = check_log(path, repository)
    assert errors, row
    assert any(message in error for error in errors), errors
    assert all(f"{path}:" in error for error in errors), errors
    assert any(":13: row" in error for error in errors), errors


def test_ver63_a_closed_log_refuses_a_non_terminal_row(repository: Path) -> None:
    accepted = "| MOD-02 | stages | high | accepted | §8.2.7 G4 | [x](report.md#mod-02-another) |"
    deferred = "| MOD-02 | stages | high | deferred | §8.2.7 G4 | [x](report.md#mod-02-another) |"
    path = _log(repository, GOOD, accepted, status="closed")
    errors = check_log(path, repository)
    assert any("row MOD-01 is 'open' under a closed log" in error for error in errors), errors
    assert any("row MOD-02 is 'accepted' under a closed log" in error for error in errors)
    path = _log(repository, deferred, status="closed")
    assert check_log(path, repository) == ()


def test_ver63_front_matter_and_file_name_go_together(repository: Path) -> None:
    named = repository / "docs" / "project" / "y-findings.md"
    named.write_text("# Findings, with no front matter\n", encoding="utf-8")
    assert "declares no findings front matter" in check_log(named, repository)[0]
    unnamed = _log(repository, GOOD, name="notes.md")
    assert "is not named *findings.md" in check_log(unnamed, repository)[0]
    assert unnamed in logs(repository)


def test_ver63_a_log_status_other_than_open_or_closed_is_refused(repository: Path) -> None:
    path = _log(repository, GOOD, status="done")
    assert any("neither open nor closed" in error for error in check_log(path, repository))


def test_ver63_a_fixed_ruling_may_link_a_section_of_its_plan(repository: Path) -> None:
    """A plan link with an anchor still names the plan; the anchor is not part of the file."""
    fixed = f"| MOD-02 | coupling | low | fixed | [WP36](../plans/wp36.md#outcome) | {ANOTHER} |"
    assert check_log(_log(repository, GOOD, fixed), repository) == ()


def test_ver63_a_finding_linking_a_heading_of_the_log_itself_is_checked(repository: Path) -> None:
    """``#anchor`` alone is a heading of the log: checked against it, never read as a directory."""
    own = "| MOD-02 | stages | high | open | — | [x](#log) |"
    assert check_log(_log(repository, GOOD, own), repository) == ()
    gone = "| MOD-02 | stages | high | open | — | [x](#nowhere) |"
    errors = check_log(_log(repository, GOOD, gone), repository)
    assert any("anchor #nowhere names no heading of x-findings.md" in e for e in errors), errors


def test_ver63_front_matter_that_is_not_yaml_is_refused_by_name(repository: Path) -> None:
    named = repository / "docs" / "project" / "z-findings.md"
    named.write_text("---\nfindings: [\n---\n\n# Log\n", encoding="utf-8")
    assert "declares no findings front matter" in check_log(named, repository)[0]
    assert named in logs(repository)
