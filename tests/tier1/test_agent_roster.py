"""The agent roster and the plain summaries (WP43 D13, D15; §8.2.10 J8, J9).

Claude Code ignores a frontmatter key it does not know, so a misspelt ``model`` or
``tools`` silently gives an agent the session's model and every tool. These
tests read the files as data and fail on any key outside the documented set.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
AGENTS = REPOSITORY / ".claude/agents"
PLANNED = "planned: WP43 D13 (J8)"

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
}
"""The keys code.claude.com/docs/en/sub-agents documented on 12 October 2026."""

READ_ONLY = {"Read", "Grep", "Glob"}

ROSTER = {
    "gate-runner": ("sonnet", {"Bash", "Read"}),
    "spec-reader": ("sonnet", READ_ONLY),
    "surveyor": ("haiku", READ_ONLY),
    "ci-log-classifier": ("sonnet", READ_ONLY),
    "physics-reviewer": ("opus", READ_ONLY),
}
"""Each agent's model and its exact tool list (the WP43 plan, D13)."""


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
def test_the_roster_is_the_planned_five_with_their_models_and_tools() -> None:
    found = {path.stem: _frontmatter(path) for path in sorted(AGENTS.glob("*.md"))}
    assert set(found) == set(ROSTER)
    for name, (model, tools) in ROSTER.items():
        meta = found[name]
        assert meta["name"] == name
        assert meta["model"] == model, name
        assert _tools(meta["tools"]) == tools, name
        assert isinstance(meta["description"], str) and meta["description"].strip(), name


@pytest.mark.xfail(strict=True, reason=PLANNED)
def test_no_agent_file_carries_a_key_claude_code_would_ignore() -> None:
    paths = sorted(AGENTS.glob("*.md"))
    assert paths
    for path in paths:
        unknown = set(_frontmatter(path)) - KNOWN_KEYS
        assert not unknown, f"{path.name}: {sorted(unknown)}"


@pytest.mark.xfail(strict=True, reason="planned: WP43 D15 (J9)")
@pytest.mark.parametrize("skill", ["phase-plan", "wp-plan", "wp-implement"])
def test_the_planning_skills_require_an_in_brief_of_at_most_250_words(skill: str) -> None:
    text = (REPOSITORY / f".claude/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
    assert "## In brief" in text
    assert "250 words" in text
    assert "Your call" in text


def _plan_number(path: Path) -> int:
    match = re.match(r"wp(\d+)-", path.name)
    assert match
    return int(match.group(1))


def test_every_plan_from_wp43_opens_with_an_in_brief_of_at_most_250_words() -> None:
    """J9: the section comes before the Execution brief and is readable at a glance."""
    plans = [
        path
        for path in sorted((REPOSITORY / "docs/plans").glob("wp*-*.md"))
        if _plan_number(path) >= 43
    ]
    assert plans
    for path in plans:
        text = path.read_text(encoding="utf-8")
        brief = re.search(r"^## In brief\n(.*?)^## ", text, re.S | re.M)
        assert brief, f"{path.name} has no In brief before its next section"
        assert text.index("## In brief") < text.index("## Execution brief"), path.name
        assert len(brief.group(1).split()) <= 250, path.name
        assert "Your call" in brief.group(1), path.name
