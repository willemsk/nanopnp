"""The agent roster, its context and the plain summaries (WP43 D13 to D15; §8.2.10 J8, J9, J11).

Claude Code ignores a frontmatter key it does not know, so a misspelt ``model`` or
``tools`` silently gives an agent the session's model and every tool. These
tests read the files as data and fail on any key outside the documented set.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
AGENTS = REPOSITORY / ".claude/agents"
SCRIPTS = REPOSITORY / ".claude/scripts"
RULES = REPOSITORY / ".claude/rules"
GUARD = REPOSITORY / ".claude/hooks/agent-guard.sh"
PLANNED = "planned: WP43 D13 (J8)"
PLANNED_CONTEXT = "planned: WP43 D14 (J8, J11)"

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

READ_ONLY = {"Read", "Grep", "Glob"}

ROSTER = {
    "gate-runner": ("sonnet", {"Bash", "Read"}, "low", True),
    "surveyor": ("haiku", READ_ONLY, "low", True),
    "ci-log-classifier": ("sonnet", READ_ONLY, None, True),
    "physics-reviewer": ("opus", READ_ONLY, "high", False),
}
"""Each agent's model, exact tools, effort and whether it skips ``CLAUDE.md`` (WP43 D13)."""


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path.name} has no frontmatter"
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict)
    return loaded


def _tools(value: object) -> set[str]:
    if isinstance(value, str):
        return {part.strip() for part in value.split(",") if part.strip()}
    assert isinstance(value, list)
    return {str(part) for part in value}


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_the_roster_is_the_planned_four_with_their_models_tools_and_effort() -> None:
    found = {path.stem: _frontmatter(path) for path in sorted(AGENTS.glob("*.md"))}
    assert set(found) == set(ROSTER)
    for name, (model, tools, effort, omits_claude_md) in ROSTER.items():
        meta = found[name]
        assert meta["name"] == name
        assert meta["model"] == model, name
        assert _tools(meta["tools"]) == tools, name
        assert meta.get("effort") == effort, name
        assert meta.get("omitClaudeMd", False) is omits_claude_md, name
        assert isinstance(meta["description"], str) and meta["description"].strip(), name


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_no_agent_file_carries_a_key_claude_code_would_ignore() -> None:
    paths = sorted(AGENTS.glob("*.md"))
    assert paths
    for path in paths:
        unknown = set(_frontmatter(path)) - KNOWN_KEYS
        assert not unknown, f"{path.name}: {sorted(unknown)}"


def _clause(*identifiers: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "clause.py"), *identifiers],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_clause_prints_an_identifiers_row_and_every_ruling_that_names_it() -> None:
    """D13: the script, not an agent, returns a clause verbatim with its rulings."""
    result = _clause("VER-62")
    assert result.returncode == 0, result.stderr
    assert "| **VER-62** | Number stability |" in result.stdout
    # G10 names VER-62; a ruling that names the identifier is printed with the row.
    assert "| G10 |" in result.stdout, result.stdout[:2000]


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_clause_refuses_an_identifier_with_no_definition() -> None:
    result = _clause("VER-9999")
    assert result.returncode != 0
    assert "VER-9999" in result.stderr


def _guard(tool_input: dict[str, object], tool_name: str = "Agent") -> str:
    bash = shutil.which("bash")
    assert bash is not None
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input, "cwd": str(REPOSITORY)})
    result = subprocess.run(
        [bash, str(GUARD)], input=payload, capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _denied(stdout: str) -> bool:
    if not stdout.strip():
        return False
    decision = json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
    return bool(decision == "deny")


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None or shutil.which("jq") is None,
    reason="the agent guard is a bash hook that reads its payload with jq",
)
@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_the_agent_guard_holds_each_spawn_to_the_roster_and_the_policy() -> None:
    """D13: a call's ``model`` overrides the file's, so the hook keeps the two equal."""
    refused = _guard({"subagent_type": "surveyor", "model": "opus", "prompt": "x"})
    assert _denied(refused) and "surveyor" in refused and "model-policy" in refused
    unnamed = _guard({"subagent_type": "general-purpose", "prompt": "x"})
    assert _denied(unnamed) and "model-policy" in unnamed
    assert not _denied(_guard({"subagent_type": "surveyor", "prompt": "x"}))
    assert not _denied(_guard({"subagent_type": "surveyor", "model": "haiku", "prompt": "x"}))
    assert not _denied(_guard({"subagent_type": "Explore", "model": "sonnet", "prompt": "x"}))
    assert not _denied(_guard({"subagent_type": "fork", "prompt": "x"}))
    assert not _denied(_guard({"command": "ls"}, tool_name="Bash"))


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_the_guard_is_registered_on_agent_calls() -> None:
    settings = json.loads((REPOSITORY / ".claude/settings.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entry in settings["hooks"]["PreToolUse"]
        if "Agent" in entry["matcher"].split("|")
        for hook in entry["hooks"]
    ]
    assert any("agent-guard.sh" in command for command in commands)


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
"""Where the physics and numerics rules load (D14): every module whose code they govern."""


@pytest.mark.xfail(strict=True, reason=PLANNED_CONTEXT)
def test_the_physics_rules_load_wherever_the_rules_govern_the_code() -> None:
    meta = _frontmatter(RULES / "physics-numerics.md")
    assert set(meta) == {"paths"}, "paths is the only key Claude Code reads from a rule"
    assert set(_tools(meta["paths"])) >= PHYSICS_PATHS
    for skill in ("phase-plan", "wp-plan", "wp-ship"):
        text = (REPOSITORY / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
        assert ".claude/rules/physics-numerics.md" in text, skill


def _reading_set() -> ModuleType:
    spec = importlib.util.spec_from_file_location("reading_set", SCRIPTS / "reading_set.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _toy_plan(brief_words: int) -> str:
    return (
        "# WP99\n\n## In brief\n\nShort.\n\n## Execution brief\n\n"
        + " ".join(["word"] * brief_words)
        + "\n\n### Work items\n\n- [ ] 1. [Opus] Change `src/nanopnp/physics/poisson.py`.\n"
        + "\n## Design\n"
    )


@pytest.mark.xfail(strict=True, reason=PLANNED_CONTEXT)
def test_the_reading_set_counts_the_rule_files_a_package_loads(tmp_path: Path) -> None:
    """J11, amended: text moved into a rule the package loads is not a cut."""
    rules = tmp_path / ".claude/rules"
    rules.mkdir(parents=True)
    (rules / "physics-numerics.md").write_text(
        '---\npaths:\n  - "src/nanopnp/physics/**"\n---\none two three\n', encoding="utf-8"
    )
    (rules / "gui.md").write_text(
        '---\npaths:\n  - "src/nanopnp/gui/**"\n---\nfour five\n', encoding="utf-8"
    )
    triggered = _reading_set().triggered_rules(_toy_plan(10), rules)
    assert [path.name for path in triggered] == ["physics-numerics.md"]


@pytest.mark.xfail(strict=True, reason=PLANNED_CONTEXT)
def test_the_reading_set_refuses_a_brief_over_1200_words(tmp_path: Path) -> None:
    plan = tmp_path / "wp99-toy.md"
    plan.write_text(_toy_plan(1201), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "reading_set.py"), str(plan)],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "1,200" in result.stdout + result.stderr


@pytest.mark.xfail(strict=True, reason="planned: WP43 D15 (J9)")
@pytest.mark.parametrize("skill", ["phase-plan", "wp-plan", "wp-implement"])
def test_the_planning_skills_require_an_in_brief_of_at_most_250_words(skill: str) -> None:
    text = (REPOSITORY / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
    assert "## In brief" in text
    assert "250 words" in text
    assert "Your call" in text


IDENTIFIER = re.compile(r"`|§|\b[A-Z]{2,4}-\d+\b|\b[A-Z]{1,2}\d+\b")
"""What J9 keeps out of an In brief: code, section signs and identifiers (VER-62, D13, WP43)."""


def _plan_number(path: Path, prefix: str) -> int:
    match = re.match(rf"{prefix}-?(\d+)-", path.name)
    assert match
    return int(match.group(1))


def _check_in_brief(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    brief = re.search(r"^## In brief\n(.*?)^## ", text, re.S | re.M)
    assert brief, f"{path.name} has no In brief before its next section"
    body = brief.group(1)
    assert len(body.split()) <= 250, f"{path.name}: {len(body.split())} words"
    assert "Your call" in body, path.name
    found = IDENTIFIER.findall(body)
    assert not found, f"{path.name}: {sorted(set(found))}"


def test_every_plan_from_wp43_opens_with_an_in_brief_of_at_most_250_words() -> None:
    """J9: the section comes before the Execution brief and is readable at a glance."""
    plans = [
        path
        for path in sorted((REPOSITORY / "docs/plans").glob("wp*-*.md"))
        if _plan_number(path, "wp") >= 43
    ]
    assert plans
    for path in plans:
        _check_in_brief(path)
        text = path.read_text(encoding="utf-8")
        assert text.index("## In brief") < text.index("## Execution brief"), path.name


def test_current_md_opens_with_an_in_brief_of_at_most_250_words() -> None:
    _check_in_brief(REPOSITORY / "docs/plans/current.md")


@pytest.mark.xfail(strict=True, reason="planned: WP43 D15 (J9)")
def test_every_phase_plan_from_phase_4_opens_with_an_in_brief_of_at_most_250_words() -> None:
    plans = [
        path
        for path in sorted((REPOSITORY / "docs/plans").glob("phase-*-*.md"))
        if _plan_number(path, "phase") >= 4
    ]
    assert plans
    for path in plans:
        _check_in_brief(path)
