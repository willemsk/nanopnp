"""Run the stale-reference probes of the audit brief's Appendix C over the files in scope.

Reads the files ``scope.py`` names and, for the probes that check existence, the tree: the
history records' §8.2 numbers, the plans' ``| Dn |`` rows, ``git tag``, ``tests/``, the code-review
reports, the ``REV-``, ``MOD-`` and ``OPN-`` registers and the requirement rows of the current
specification. Writes one Markdown report to standard output: a section per probe, each hit as
``file:line`` with the line's text and, where the probe checks existence, a verdict. Live files
first, then the records, which are in scope for reachability only, so a hit in a record is
context and not a finding.

Run it as ``uv run .claude/scripts/audit/probes.py``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT, live_files, record_files, relative

Verdict = Callable[[re.Match[str]], str]

TEXT_PROBES: dict[str, str] = {
    "nanopnp-kb": r"nanopnp-kb",
    "pending.yaml": r"pending\.yaml",
    "schema v0.0 to v0.5": r"nanopnp/case/v0\.[0-5]\b",
    "load_case, run_case, resolve(": r"\bload_case\b|\brun_case\b|\bresolve\(",
    "old command names": r"/phase-plan|/wp-plan|/wp-implement|/wp-ship",
    "PyQt": r"PyQt",
    "coverage tooling": r"\bcoverage\b|diff-cover|pytest-cov",
    "--extended, no_cover, test_plan_shape": r"--extended|no_cover|test_plan_shape",
}


def _history_numbers() -> set[int]:
    numbers: set[int] = set()
    for path in (ROOT / "specification" / "history").glob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^#+\s+8\.2\.(\d+)\s", line)
            if match:
                numbers.add(int(match.group(1)))
    return numbers


def _plan_decisions() -> dict[str, set[str]]:
    """Return, per package number, the ``Dn`` rows of its plan's tables."""
    found: dict[str, set[str]] = {}
    for path in (ROOT / "docs" / "plans").glob("wp*.md"):
        match = re.match(r"^wp(\d+(?:\.\d+)?)-", path.name)
        if not match:
            continue
        rows = set(
            re.findall(r"^\|\s*\*?\*?(D\d+)\*?\*?\s*\|", path.read_text(encoding="utf-8"), re.M)
        )
        found[match.group(1)] = rows
    return found


def _tags() -> set[str]:
    out = subprocess.run(["git", "tag"], cwd=ROOT, capture_output=True, text=True, check=False)
    return set(out.stdout.split())


def _register(path: Path, prefix: str) -> dict[str, str]:
    """Return each ``PREFIX-nn`` row's text of a register table."""
    rows: dict[str, str] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(rf"^\|\s*\*?\*?({prefix}-\d+)\*?\*?\s*\|(.*)$", line)
        if match:
            rows[match.group(1)] = match.group(2).strip()
    return rows


def _requirements() -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in (ROOT / "specification").rglob("*.md"):
        if "history" in path.relative_to(ROOT).parts:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\|\s*\*\*([A-Z]+-\d+)\*\*\s*\|(.*)$", line)
            if match:
                rows[match.group(1)] = match.group(2)
            match = re.match(r"^\*\*([A-Z]+-\d+)\.\*\*(.*)$", line)
            if match:
                rows[match.group(1)] = match.group(2)
    return rows


def _status_cell(row: str) -> str:
    cells = [c.strip() for c in row.split("|")]
    return " | ".join(c for c in cells[:4] if c)


def _existence_probes() -> dict[str, tuple[str, Verdict]]:
    history = _history_numbers()
    decisions = _plan_decisions()
    tags = _tags()
    reports = {p.stem for p in (ROOT / "docs" / "code_reviews").glob("CODE_REVIEW_*.md")}
    rev = _register(ROOT / "docs/project/review-findings.md", "REV")
    mod = _register(ROOT / "docs/project/modularity-findings.md", "MOD")
    opn = _register(ROOT / "specification/10-open-items.md", "OPN")
    requirements = _requirements()

    def ruling(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return (
            "exists"
            if n in history
            else f"NO RECORD §8.2.{n} (history runs to §8.2.{max(history)})"
        )

    def decision(m: re.Match[str]) -> str:
        package, d = m.group(1), m.group(2)
        if package not in decisions:
            return f"NO PLAN wp{package}"
        return "exists" if d in decisions[package] else f"NO ROW {d} in wp{package}'s plan"

    def version(m: re.Match[str]) -> str:
        v = m.group(0)
        if v in tags:
            return "tag"
        return "not a tag" + (" (a prefix of tags)" if any(t.startswith(v) for t in tags) else "")

    def test_file(m: re.Match[str]) -> str:
        return "exists" if (ROOT / m.group(0)).exists() else "NO FILE"

    def report(m: re.Match[str]) -> str:
        return "exists" if m.group(0) in reports else "NO REPORT"

    def register_row(m: re.Match[str]) -> str:
        key = m.group(0)
        table = {"REV": rev, "MOD": mod, "OPN": opn}[key.split("-")[0]]
        if key not in table:
            return "NO ROW"
        return "row: " + _status_cell(table[key])[:80]

    def requirement(m: re.Match[str]) -> str:
        key = m.group(0)
        if key not in requirements:
            return "NO DEFINITION"
        text = requirements[key]
        return "withdrawn" if re.search(r"withdrawn", text, re.I) else "defined"

    return {
        "§8.2.20 to §8.2.39 cited (does the record exist?)": (r"§8\.2\.(2\d|3\d)\b", ruling),
        "WPn Dm cited (does the plan's decision exist?)": (
            r"\bWP(\d+(?:\.\d+)?) (D\d+)\b",
            decision,
        ),
        "version named (is it a tag?)": (r"\bv0\.\d\.\d+(?:-alpha\.\d+)?\b", version),
        "test file named (does it exist?)": (r"tests/tier[0-9]/[a-z_0-9]+\.py", test_file),
        "code review named (does the report exist?)": (r"CODE_REVIEW_0\d+", report),
        "REV, MOD, OPN row named (does the row exist; its status)": (
            r"\b(?:REV|MOD|OPN)-\d+\b",
            register_row,
        ),
        "VER, VAL identifier named (defined; withdrawn?)": (r"\b(?:VER|VAL)-\d+\b", requirement),
    }


def _hits(paths: Iterable[Path], pattern: re.Pattern[str], verdict: Verdict | None) -> list[str]:
    out: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                where = f"{relative(path)}:{number}"
                snippet = line.strip()
                if len(snippet) > 140:
                    start = max(0, match.start() - 60)
                    snippet = "…" + line[start : start + 140].strip() + "…"
                tail = f" — **{verdict(match)}**" if verdict else ""
                escaped = snippet.replace("|", "\\|")
                out.append(f"- `{where}`{tail}: {escaped}")
                if verdict is None:
                    break
    return out


def main() -> int:
    """Print the probe report."""
    live = live_files()
    records = record_files()
    print("# Appendix C probes over the files in scope")
    print()
    print(
        f"Live files: {len(live)}. Records: {len(records)}. "
        "A hit in a record is context, not a finding."
    )
    probes: list[tuple[str, re.Pattern[str], Verdict | None]] = [
        (name, re.compile(p), None) for name, p in TEXT_PROBES.items()
    ]
    probes += [(name, re.compile(p), v) for name, (p, v) in _existence_probes().items()]
    for name, pattern, verdict in probes:
        for label, paths in (("live", live), ("records", records)):
            hits = _hits(paths, pattern, verdict)
            if verdict is not None:
                hits = (
                    [
                        h
                        for h in hits
                        if "**exists**" not in h
                        and "**defined**" not in h
                        and "**tag**" not in h
                        and "**row: " not in h
                    ]
                    if label == "records"
                    else hits
                )
            print()
            print(f"## {name} — {label} ({len(hits)})")
            print()
            print("\n".join(hits) if hits else "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
