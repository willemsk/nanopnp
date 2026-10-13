"""VER-72 (g) — plans stay small, and the agent files, clause script and rules are in order.

§8.2.11 L6 to L8. A work-package plan from WP44 on holds at most 1,500 words, at most six
``Decisions`` rows, no ``## Design`` heading and an In brief of at most 250 words.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
AGENTS = REPOSITORY / ".claude/agents"
SCRIPTS = REPOSITORY / ".claude/scripts"
RULES = REPOSITORY / ".claude/rules"
PLANS = REPOSITORY / "docs/plans"

MAX_PLAN_WORDS = 1500
MAX_DECISIONS = 6
MAX_BRIEF_WORDS = 250

KNOWN_KEYS = {
    "name",
    "description",
    "tools",
    "disallowedTools",
    "model",
    "effort",
    "permissionMode",
    "isolation",
    "skills",
    "hooks",
    "memory",
    "background",
    "maxTurns",
    "mcpServers",
    "color",
    "initialPrompt",
    "omitClaudeMd",
    "experimental",
}
"""The keys code.claude.com/docs/en/sub-agents documented on 12 October 2026."""

IDENTIFIER = re.compile(r"`|§|\b[A-Z]{2,4}-\d+\b|\b[A-Z]{1,2}\d+\b")
"""What an In brief keeps out: code, section signs and identifiers."""


def _frontmatter(path: Path) -> dict[str, object]:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"{path.name} has no frontmatter"
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict)
    return loaded


def _tools(value: object) -> set[str]:
    if isinstance(value, str):
        return {part.strip() for part in value.split(",") if part.strip()}
    assert isinstance(value, list)
    return {str(part) for part in value}


def _number(path: Path, prefix: str) -> int:
    match = re.match(rf"{prefix}-?(\d+)-", path.name)
    assert match
    return int(match.group(1))


def _brief_problems(text: str) -> list[str]:
    brief = re.search(r"^## In brief\n(.*?)^## ", text, re.S | re.M)
    if not brief:
        return ["no In brief before the next section"]
    body = brief.group(1)
    problems = []
    if len(body.split()) > MAX_BRIEF_WORDS:
        problems.append(f"In brief of {len(body.split())} words, over {MAX_BRIEF_WORDS}")
    if "Your call" not in body:
        problems.append("In brief without a Your call")
    found = IDENTIFIER.findall(body)
    if found:
        problems.append(f"In brief names {sorted(set(found))}")
    return problems


def plan_problems(text: str) -> list[str]:
    """Return the caps of §8.2.11 L7 that a work-package plan breaks."""
    problems = _brief_problems(text)
    if len(text.split()) > MAX_PLAN_WORDS:
        problems.append(f"{len(text.split())} words, over {MAX_PLAN_WORDS}")
    if re.search(r"^#{2,3} Design\b", text, re.M):
        problems.append("a Design heading")
    section = re.search(r"^### Decisions\n(.*?)(?=^#{1,3} )", text, re.S | re.M)
    if section:
        rows = [line for line in section.group(1).splitlines() if line.startswith("|")]
        decisions = len(rows) - 2
        if decisions > MAX_DECISIONS:
            problems.append(f"{decisions} decisions, over {MAX_DECISIONS}")
    return problems


def _toy_plan(words: int = 0, decisions: int = 6, design: bool = False, brief: int = 20) -> str:
    rows = "".join(f"| D{n} | choice | why |\n" for n in range(decisions))
    return (
        f"# WP99\n\n## In brief\n\n{' '.join(['word'] * brief)}\n\n**Your call.** None.\n\n"
        "## Execution brief\n\n### Decisions\n\n| Decision | Choice | Why |\n|---|---|---|\n"
        f"{rows}\n### Work items\n\n- [ ] 1. Change it.\n\n{' '.join(['text'] * words)}\n"
        + ("\n## Design\n\nmore\n" if design else "")
    )


def test_ver72_g_a_plan_within_the_caps_passes() -> None:
    assert plan_problems(_toy_plan(words=1000)) == []


@pytest.mark.parametrize(
    ("plan", "message"),
    [
        (_toy_plan(words=1501), "over 1500"),
        (_toy_plan(decisions=7), "7 decisions"),
        (_toy_plan(design=True), "Design heading"),
        (_toy_plan(brief=251), "In brief of"),
    ],
    ids=["words", "decisions", "design", "brief"],
)
def test_ver72_g_a_plan_over_a_cap_is_found(plan: str, message: str) -> None:
    assert any(message in problem for problem in plan_problems(plan)), plan_problems(plan)


def test_ver72_g_every_plan_from_wp44_keeps_the_caps() -> None:
    plans = [path for path in sorted(PLANS.glob("wp*-*.md")) if _number(path, "wp") >= 44]
    assert plans
    for path in plans:
        assert plan_problems(path.read_text(encoding="utf-8")) == [], path.name


def test_ver72_g_every_plan_from_wp43_opens_with_a_plain_in_brief() -> None:
    plans = [path for path in sorted(PLANS.glob("wp*-*.md")) if _number(path, "wp") >= 43]
    assert plans
    for path in plans:
        text = path.read_text(encoding="utf-8")
        assert _brief_problems(text) == [], path.name
        assert text.index("## In brief") < text.index("## Execution brief"), path.name


def test_ver72_g_current_and_the_phase_plans_keep_the_in_brief_check() -> None:
    phases = [path for path in sorted(PLANS.glob("phase-*-*.md")) if _number(path, "phase") >= 4]
    assert phases
    for path in [PLANS / "current.md", *phases]:
        assert _brief_problems(path.read_text(encoding="utf-8")) == [], path.name


@pytest.mark.parametrize("skill", ["phase-plan", "wp-plan", "wp-implement"])
def test_ver72_g_the_planning_skills_require_an_in_brief_of_at_most_250_words(skill: str) -> None:
    text = (REPOSITORY / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
    assert "## In brief" in text
    assert "250 words" in text
    assert "Your call" in text


def test_the_agent_files_carry_only_keys_claude_code_reads() -> None:
    paths = sorted(AGENTS.glob("*.md"))
    assert {path.stem for path in paths} == {"ci-log-classifier", "physics-reviewer"}
    for path in paths:
        meta = _frontmatter(path)
        assert not set(meta) - KNOWN_KEYS, path.name
        assert isinstance(meta["description"], str) and meta["description"].strip(), path.name
        assert _tools(meta["tools"]) == {"Read", "Grep", "Glob"}, path.name


def _clause(*identifiers: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "clause.py"), *identifiers],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_clause_prints_an_identifiers_row_and_every_ruling_that_names_it() -> None:
    result = _clause("VER-62")
    assert result.returncode == 0, result.stderr
    assert "| **VER-62** | Number stability |" in result.stdout
    assert "| G10 |" in result.stdout, result.stdout[:2000]


def test_clause_refuses_an_identifier_with_no_definition() -> None:
    result = _clause("VER-9999")
    assert result.returncode != 0
    assert "VER-9999" in result.stderr


PHYSICS_PATHS = {
    *(
        f"src/nanopnp/{module}/**"
        for module in (
            "physics",
            "numerics",
            "solve",
            "post",
            "materials",
            "charge",
            "mesh",
            "validation",
        )
    ),
    "data/corrections/**",
    "tests/tier2/**",
    "tests/tier3/**",
}
"""Where the physics and numerics rules load: every module whose code they govern."""


def test_the_physics_rules_load_wherever_the_rules_govern_the_code() -> None:
    meta = _frontmatter(RULES / "physics-numerics.md")
    assert set(meta) == {"paths"}, "paths is the only key Claude Code reads from a rule"
    assert set(_tools(meta["paths"])) >= PHYSICS_PATHS
    for skill in ("phase-plan", "wp-plan", "wp-ship"):
        text = (REPOSITORY / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
        assert ".claude/rules/physics-numerics.md" in text, skill
