# paths.py at 86e647b
# Reading paths, in words and estimated tokens

Tokens are estimated as characters divided by four. A `§` item is the text `clause.py --no-history` prints.

## The always-loaded set

| Path | Items (words) | Words | Tokens |
|---|---|---|---|
| always loaded (CLAUDE.md, SPECIFICATION.md, current.md, core.md, the two rules files) | `CLAUDE.md` (2099), `SPECIFICATION.md` (1026), `docs/plans/current.md` (699), `.claude/workflow/core.md` (1501), `.claude/rules/physics-numerics.md` (384), `.claude/rules/python.md` (294) | 6003 | 10655 |

## Each skill's load (beside the always-loaded set)

| Path | Items (words) | Words | Tokens |
|---|---|---|---|
| /np-plan project | `.claude/skills/np-plan/SKILL.md` (191), `.claude/workflow/core.md` (1501), `.claude/skills/np-plan/project.md` (308), `.claude/skills/np-plan/rulings.md` (991), `.claude/skills/np-plan/review.md` (871) | 3862 | 5855 |
| /np-plan phase n | `.claude/skills/np-plan/SKILL.md` (191), `.claude/workflow/core.md` (1501), `.claude/skills/np-plan/phase.md` (962), `.claude/skills/np-plan/rulings.md` (991), `.claude/skills/np-plan/review.md` (871) | 4516 | 6823 |
| /np-plan amend n | `.claude/skills/np-plan/SKILL.md` (191), `.claude/workflow/core.md` (1501), `.claude/skills/np-plan/amend.md` (237), `.claude/skills/np-plan/rulings.md` (991), `.claude/skills/np-plan/review.md` (871) | 3791 | 5744 |
| /np-plan wp n | `.claude/skills/np-plan/SKILL.md` (191), `.claude/workflow/core.md` (1501), `.claude/skills/np-plan/wp.md` (1712), `.claude/skills/np-plan/review.md` (871) | 4275 | 6446 |
| /np-implement wp n | `.claude/skills/np-implement/SKILL.md` (103), `.claude/workflow/core.md` (1501), `.claude/skills/np-implement/wp.md` (953) | 2557 | 3866 |
| /np-ship wp n | `.claude/skills/np-ship/SKILL.md` (122), `.claude/workflow/core.md` (1501), `.claude/skills/np-ship/wp.md` (1641) | 3264 | 4943 |
| /np-ship phase n | `.claude/skills/np-ship/SKILL.md` (122), `.claude/workflow/core.md` (1501), `.claude/skills/np-ship/phase.md` (241), `.claude/skills/np-ship/wp.md` (1641) | 3505 | 5306 |
| /np-gui render | `.claude/skills/np-gui/SKILL.md` (132), `.claude/skills/np-gui/render.md` (506) | 638 | 1136 |
| /np-gui review | `.claude/skills/np-gui/SKILL.md` (132), `.claude/skills/np-gui/review.md` (117) | 249 | 413 |
| /np-gui publish | `.claude/skills/np-gui/SKILL.md` (132), `.claude/skills/np-gui/publish.md` (212) | 344 | 566 |
| /np-gui collect | `.claude/skills/np-gui/SKILL.md` (132), `.claude/skills/np-gui/collect.md` (150) | 282 | 456 |
| /np-gui grill | `.claude/skills/np-gui/SKILL.md` (132), `.claude/skills/np-gui/grill.md` (288) | 420 | 663 |
| steward (a PR event) | `.claude/skills/steward/SKILL.md` (1724) | 1724 | 2636 |
| a Copilot host, in addition | `.claude/workflow/hosts.md` (91), `.claude/workflow/hosts/copilot.md` (1229), `AGENTS.md` (32) | 1352 | 2126 |

## Each row of *Where to start, by task*

| Path | Items (words) | Words | Tokens |
|---|---|---|---|
| Implement or change a pipeline stage: §3.2, §5.2, §5.3.2 (then the PHY or NUM clauses it cites: varies) | `§3.2` (2234), `§5.2` (6192), `§5.3.2` (3759) | 12185 | 18350 |
| Change the case file: §5.3.1, §5.3.3, Appendix A | `§5.3.1` (2427), `§5.3.3` (1052), `specification/a-traceability-matrix.md` (2677) | 6156 | 9964 |
| Touch the physics or a correction: §4, knowledge/01-physics-epnpns/, then §6 | `specification/04-physics.md` (6916), `knowledge/01-physics-epnpns/` (4118), `specification/06-numerics.md` (7197) | 18231 | 27707 |
| Touch the numerics, solver or mesh: §6, §7.3 | `specification/06-numerics.md` (7197), `specification/07-verification/03-tier-2.md` (3021) | 10218 | 15125 |
| Write or judge a test: §7.1, Appendix A (then the VER or VAL row: varies) | `specification/07-verification/01-strategy.md` (513), `specification/a-traceability-matrix.md` (2677) | 3190 | 5285 |
| Plan or ship a work package: §8.1, §8.4, current.md | `specification/08-implementation-plan/01-phases-and-gates.md` (1395), `specification/08-implementation-plan/04-development-process.md` (2070), `docs/plans/current.md` (699) | 4164 | 6394 |

## The nominal walk to each of the author's five hard-to-reach things

| Path | Items (words) | Words | Tokens |
|---|---|---|---|
| a decision and its reason: which ruling set the plan word cap, and why (SPECIFICATION.md → §8.4 → history/index.md → records 15, 16, 33) | `SPECIFICATION.md` (1026), `specification/08-implementation-plan/04-development-process.md` (2070), `specification/history/index.md` (4025), `specification/history/15-the-work-package-plan-grounded-in-the-code-agreed.md` (338), `specification/history/16-phase-4-amended-the-specification-and-the-workflow.md` (1691), `specification/history/33-wp508s-plan-a-users-colour-themes.md` (2178) | 11328 | 17570 |
| the current state of the work: what is merged and what is next (current.md → the phase plan) | `docs/plans/current.md` (699), `docs/plans/phase-5/phase-5-workbench.md` (5287) | 5986 | 9406 |
| which rule governs an action: a push from a Copilot host (CLAUDE.md → §8.4 → hosts.md → copilot.md → record 25) | `CLAUDE.md` (2099), `specification/08-implementation-plan/04-development-process.md` (2070), `.claude/workflow/hosts.md` (91), `.claude/workflow/hosts/copilot.md` (1229), `specification/history/25-the-workflow-on-the-github-copilot-app.md` (934) | 6423 | 9956 |
| a measured number and its derivation: the Tier 2 tolerance on the current (SPECIFICATION.md → §7.3 → §6 → knowledge/08-…) | `SPECIFICATION.md` (1026), `specification/07-verification/03-tier-2.md` (3021), `specification/06-numerics.md` (7197), `knowledge/08-validation-benchmarks/` (3488) | 14732 | 24756 |
| the current code architecture: which subpackage owns the wall distance and what imports it (§5.1 → modularity.md → the layering file) | `specification/05-software-design/01-architectural-overview.md` (443), `docs/project/modularity.md` (3615), `docs/project/modularity-layering.yaml` (1849) | 5907 | 10217 |

