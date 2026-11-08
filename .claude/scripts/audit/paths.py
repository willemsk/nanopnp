"""Measure the reading paths of nanopnp's documents in words and estimated tokens.

Reads the files each path names and, for a clause named by section number, the text that
``.claude/scripts/clause.py --no-history`` prints for it. Writes one Markdown report to standard
output: a table per group of paths (the always-loaded set, each skill's load, each row of
``SPECIFICATION.md``'s *Where to start, by task*, and the nominal walk to each of the five things
the audit brief says the author finds hard to reach), each row naming its items with their words
and tokens and the path's total. The paths are written into this file, with the file that defines
each; a path that varies by task (the clauses a stage cites, the VER row a test checks) is measured
on its fixed part and says so.

Run it as ``uv run .claude/scripts/audit/paths.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT, tokens, words

CLAUSE = ROOT / ".claude" / "scripts" / "clause.py"

Item = str
Group = dict[str, list[Item]]

ALWAYS: Group = {
    "always loaded (CLAUDE.md, SPECIFICATION.md, current.md, core.md, the two rules files)": [
        "CLAUDE.md",
        "SPECIFICATION.md",
        "docs/plans/current.md",
        ".claude/workflow/core.md",
        ".claude/rules/physics-numerics.md",
        ".claude/rules/python.md",
    ],
}

# Each skill's load, from its SKILL.md router.
SKILLS: Group = {
    "/np-plan project": [
        ".claude/skills/np-plan/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-plan/project.md",
        ".claude/skills/np-plan/rulings.md",
        ".claude/skills/np-plan/review.md",
    ],
    "/np-plan phase n": [
        ".claude/skills/np-plan/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-plan/phase.md",
        ".claude/skills/np-plan/rulings.md",
        ".claude/skills/np-plan/review.md",
    ],
    "/np-plan amend n": [
        ".claude/skills/np-plan/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-plan/amend.md",
        ".claude/skills/np-plan/rulings.md",
        ".claude/skills/np-plan/review.md",
    ],
    "/np-plan wp n": [
        ".claude/skills/np-plan/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-plan/wp.md",
        ".claude/skills/np-plan/review.md",
    ],
    "/np-implement wp n": [
        ".claude/skills/np-implement/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-implement/wp.md",
    ],
    "/np-ship wp n": [
        ".claude/skills/np-ship/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-ship/wp.md",
    ],
    "/np-ship phase n": [
        ".claude/skills/np-ship/SKILL.md",
        ".claude/workflow/core.md",
        ".claude/skills/np-ship/phase.md",
        ".claude/skills/np-ship/wp.md",
    ],
    "/np-gui render": [".claude/skills/np-gui/SKILL.md", ".claude/skills/np-gui/render.md"],
    "/np-gui review": [".claude/skills/np-gui/SKILL.md", ".claude/skills/np-gui/review.md"],
    "/np-gui publish": [".claude/skills/np-gui/SKILL.md", ".claude/skills/np-gui/publish.md"],
    "/np-gui collect": [".claude/skills/np-gui/SKILL.md", ".claude/skills/np-gui/collect.md"],
    "/np-gui grill": [".claude/skills/np-gui/SKILL.md", ".claude/skills/np-gui/grill.md"],
    "steward (a PR event)": [".claude/skills/steward/SKILL.md"],
    "a Copilot host, in addition": [
        ".claude/workflow/hosts.md",
        ".claude/workflow/hosts/copilot.md",
        "AGENTS.md",
    ],
}

# The rows of SPECIFICATION.md, *Where to start, by task*. A `§` item is measured by clause.py.
WHERE_TO_START: Group = {
    "Implement or change a pipeline stage: §3.2, §5.2, §5.3.2 "
    "(then the PHY or NUM clauses it cites: varies)": [
        "§3.2",
        "§5.2",
        "§5.3.2",
    ],
    "Change the case file: §5.3.1, §5.3.3, Appendix A": [
        "§5.3.1",
        "§5.3.3",
        "specification/a-traceability-matrix.md",
    ],
    "Touch the physics or a correction: §4, knowledge/01-physics-epnpns/, then §6": [
        "specification/04-physics.md",
        "knowledge/01-physics-epnpns/",
        "specification/06-numerics.md",
    ],
    "Touch the numerics, solver or mesh: §6, §7.3": [
        "specification/06-numerics.md",
        "specification/07-verification/03-tier-2.md",
    ],
    "Write or judge a test: §7.1, Appendix A (then the VER or VAL row: varies)": [
        "specification/07-verification/01-strategy.md",
        "specification/a-traceability-matrix.md",
    ],
    "Plan or ship a work package: §8.1, §8.4, current.md": [
        "specification/08-implementation-plan/01-phases-and-gates.md",
        "specification/08-implementation-plan/04-development-process.md",
        "docs/plans/current.md",
    ],
}

# The nominal walk to each of the author's five hard-to-reach things, as the pointers of the
# current text lead today. Step 4's task walks measure what a fresh reader does.
FIVE: Group = {
    "a decision and its reason: which ruling set the plan word cap, and why "
    "(SPECIFICATION.md → §8.4 → history/index.md → records 15, 16, 33)": [
        "SPECIFICATION.md",
        "specification/08-implementation-plan/04-development-process.md",
        "specification/history/index.md",
        "specification/history/15-the-work-package-plan-grounded-in-the-code-agreed.md",
        "specification/history/16-phase-4-amended-the-specification-and-the-workflow.md",
        "specification/history/33-wp508s-plan-a-users-colour-themes.md",
    ],
    "the current state of the work: what is merged and what is next "
    "(current.md → the phase plan)": [
        "docs/plans/current.md",
        "docs/plans/phase-5-workbench.md",
    ],
    "which rule governs an action: a push from a Copilot host "
    "(CLAUDE.md → §8.4 → hosts.md → copilot.md → record 25)": [
        "CLAUDE.md",
        "specification/08-implementation-plan/04-development-process.md",
        ".claude/workflow/hosts.md",
        ".claude/workflow/hosts/copilot.md",
        "specification/history/25-the-workflow-on-the-github-copilot-app.md",
    ],
    "a measured number and its derivation: the Tier 2 tolerance on the current "
    "(SPECIFICATION.md → §7.3 → §6 → knowledge/08-…)": [
        "SPECIFICATION.md",
        "specification/07-verification/03-tier-2.md",
        "specification/06-numerics.md",
        "knowledge/08-validation-benchmarks/",
    ],
    "the current code architecture: which subpackage owns the wall distance and what imports "
    "it (§5.1 → modularity.md → the layering file)": [
        "specification/05-software-design/01-architectural-overview.md",
        "docs/project/modularity.md",
        "docs/project/modularity-layering.yaml",
    ],
}


def _text(item: Item) -> str:
    if item.startswith("§"):
        out = subprocess.run(
            [sys.executable, str(CLAUSE), "--no-history", item],
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout
    path = ROOT / item
    if path.is_dir():
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(path.rglob("*.md")))
    return path.read_text(encoding="utf-8")


def _table(title: str, group: Group) -> None:
    print(f"## {title}")
    print()
    print("| Path | Items (words) | Words | Tokens |")
    print("|---|---|---|---|")
    for name, items in group.items():
        texts = [(item, _text(item)) for item in items]
        cells = ", ".join(f"`{item}` ({words(t)})" for item, t in texts)
        w = sum(words(t) for _, t in texts)
        t = sum(tokens(t) for _, t in texts)
        print(f"| {name} | {cells} | {w} | {t} |")
    print()


def main() -> int:
    """Print the reading-path measurements."""
    print("# Reading paths, in words and estimated tokens")
    print()
    print(
        "Tokens are estimated as characters divided by four. A `§` item is the text "
        "`clause.py --no-history` prints."
    )
    print()
    _table("The always-loaded set", ALWAYS)
    _table("Each skill's load (beside the always-loaded set)", SKILLS)
    _table("Each row of *Where to start, by task*", WHERE_TO_START)
    _table("The nominal walk to each of the author's five hard-to-reach things", FIVE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
