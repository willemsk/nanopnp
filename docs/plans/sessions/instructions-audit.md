# The instructions audit: `CLAUDE.md` and `.claude/`

**Status: report, written 22 November 2026 at WP6.02 item 3 (§8.2.49 AY8); its proposed changes are WP6.03's, and this package applies no hunk.**

The `claude-api` skill's `prompt-audit` (its `shared/prompt-audit.md`, steps 0 to 6), run over the project's agent
instructions. A finding names its file and line at commit `2120ab9`, quotes the text, names the guide's pattern, says
why it no longer fits, and gives a confidence and an action. The proposed diff closes the report, one hunk per
finding.

## Scope and target models

- **Scope.** `CLAUDE.md`, `AGENTS.md` and the 29 tracked Markdown files under `.claude/`: the core, `author.md`,
  `hosts.md` and `hosts/copilot.md`; the five skills (`np-plan`, `np-implement`, `np-ship`, `np-gui`, `steward`) with
  their level files; the three agents; the two rules. 20,561 words in all. Not read, as the guide says: the settings
  files `.claude/settings*.json`. Not in scope: the scripts and hooks, which are code (their own descriptions were read
  only where an instruction names them).
- **Target models**, from AY7 and the agent files: Fable 5.2 for `CLAUDE.md`, the rules, the core, `author.md`, the
  `np-plan`, `np-ship`, `np-gui` and `steward` skills; Opus 5.5 for `np-implement`; Opus for `physics-reviewer` and
  `gui-reviewer`, which pin it; Haiku for `ci-log-classifier`, which pins it. The project calls no model API: Group 4
  is not applicable, except its roster check.
- **Provenance.** `git log -S` dates each conflicting line; the dated rulings of `specification/history/` give the
  reason behind each rule.

## Summary

The surface is in good repair. It has no pressure language (no capitalised `MUST`, `NEVER`, `CRITICAL` or
`IMPORTANT`), no thinking or planning incantation, no update suppressor, and no stale path, script, flag or heading:
a check of every named path, recipe, flag, environment variable and cross-reference in the 31 files found none. Its
prohibitions carry their reasons (Tier 2 evidence, licences, the test scope), so the keep list holds them.

The findings that matter are three:

1. **The model of the cleanup packages.** `CLAUDE.md`'s *Models* paragraph says `/np-implement` runs on Opus 5.5.
   AY7 runs the cleanup packages whole on Fable 5.2. Nothing in the instructions says so, and WP6.02's own
   implementing session started on Opus 5.5.
2. **A ship in the implementing session runs on the implementer's model.** Four places let `/np-ship` run in the
   session that implemented, and `NANOPNP_AUTO_SHIP` chains into it. AY7 runs `/np-ship` on Fable 5.2 and
   `/np-implement` on Opus 5.5.
3. **Who owns the code.** The instructions say nothing on ownership and hold several scope rules, while the Phase 6
   plan records repeated code where a restructure is wanted. On Fable 5.2 this is the guide's own conflict; the
   author decides which way it goes.

Counts: Group 1, two findings (both flags); Group 2, six; Group 3, none (the agents' descriptions state their
contracts); Group 4, not applicable but for the roster, which is clean.

## Findings

| # | Location | Evidence | Pattern | Why it no longer fits | Confidence | Action |
|---|---|---|---|---|---|---|
| F1 | `CLAUDE.md:168-169`; `.claude/skills/np-plan/wp.md:28` | "`/np-implement` runs on Opus 5.5 at high effort, set explicitly"; "The plan is written on Fable 5.2 for an implementer on Opus 5.5" | Group 2, files that contradict each other | AY7, of the same commit `fb652bf` as the `CLAUDE.md` line, runs "the cleanup package whole" on Fable 5.2, and the Phase 6 plan says "Both cleanup packages run on Fable 5.2". The instruction files carry only the general rule, so a session reads Opus 5.5 for WP6.02 and WP6.03 | High | `rewrite` both (hunks 1, 2) |
| F2 | `CLAUDE.md:157`; `.claude/workflow/core.md:140`; `.claude/skills/np-ship/wp.md:4`; `.claude/skills/np-implement/wp.md:123-124` | "`/np-ship` then runs in that session or a fresh one"; "run the `np-ship` skill with `wp <n>` in this turn" | Group 2, files that contradict each other | AY7 puts `/np-ship` on Fable 5.2 and `/np-implement` on Opus 5.5. A ship in the implementing session, and the automatic chain above all, runs on Opus 5.5 unless the author switches the model. Both texts are recent (AI4, AY7), so history does not order them | Medium | `flag`: the author decides whether a ship may run on the implementer's model, or whether the same-session route and `NANOPNP_AUTO_SHIP` go |
| F3 | `CLAUDE.md` (no ownership line); `.claude/skills/steward/SKILL.md:149-153`; `.claude/skills/np-ship/wp.md:109-110`; `CLAUDE.md:142` | "Fix what the failure needs… A change that widens the package… goes to the user first"; "Give the user each finding that is architectural or that would make the package wider"; "One work package per PR" | Group 1g, who owns the code (Fable 5.2 targets) | The Phase 6 plan records repeated code where a restructure is wanted: `run.json` "parse[d] raw" at 13 sites, numbers computed in the shell at 12 sites, and `post/forces.py` assembling "again the terms of `physics/flow.py`". The prompts say nothing on ownership and hold scope rules, the guide's third row | Medium | `flag` the scope rules and the notes: whether the structure should improve is the author's call, at the rescoping round, before WP6.04's restructure |
| F4 | `.claude/skills/np-ship/wp.md:76-78` | "Observed 2026-11: inside an `Agent` the skill returned no findings." | Group 2, history narratives | The rule ("call the skill directly, never inside an `Agent`") binds; the dated observation is its archaeology | Medium | `rewrite` (hunk 3) |
| F5 | `.claude/skills/np-plan/phase.md:75` | "Target 1,500 words, without the report." | Group 2, volatile specifics | The Phase 6 plan holds 1,877 words; Phase 5's held 8,206 at its largest (REV-271). The number is ruled at WP6.02 item 5 (AY8; AW5) | High | `rewrite`, taken by WP6.02 item 5, not WP6.03 |
| F6 | `CLAUDE.md:171-178`; `specification/08-implementation-plan/04-development-process.md` §8.4.5 | "seven scripts in `.claude/scripts/`" | Group 2, volatile specifics | The count holds for the top level, but `.claude/scripts/gui/` (five files, which `np-gui` runs) and `.claude/scripts/audit/` (ten files, which no instruction names) are unlisted. WP6.02 item 7 adds an eighth kept script | Medium | `rewrite` at item 7 for the eighth; `flag` `audit/` for the outdated list (D7) |
| F7 | `CLAUDE.md:192-196`; `.claude/workflow/core.md:61-71`; `.claude/workflow/hosts.md`; `.claude/workflow/hosts/copilot.md`; `.claude/skills/np-plan/review.md:164` | "The workflow also runs on the GitHub Copilot app"; *Host coordination* | Group 1d, text that outlived its use | AY5 retires the Copilot host at WP6.03. `hosts.md` also keeps `.agents/` for Antigravity, which "has not been verified live" | High | `remove`, WP6.03's (AY5); not in the diff below |
| F8 | `.claude/rules/python.md:9` | `".github/scripts/**/*.py"` | Group 2, volatile specifics | The path glob matches no tracked file: `.github/scripts/` holds `prose-only.sh` alone. A glob for files to come is harmless | Low | `flag` |
| F9 | `.claude/workflow/core.md:118-122` (*Models and executors*); `.claude/skills/np-plan/phase.md:31`; `.claude/skills/np-plan/wp.md:21` | "A survey goes to Sonnet"; "Give a survey (the core, *Models and executors*)" | Group 1d, delegation lines (Fable 5.2: limit unneeded subagents) | The guide asks to review lines that invite delegation first. Here they carry a reason (a Sonnet read costs a quarter of a Fable read) and no over-delegation is recorded | Low | `flag`; the baseline (item 2) shows the sub-agents' share |
| F10 | `.claude/workflow/author.md:13`; `.claude/skills/np-plan/wp.md:96-106`; `.claude/skills/np-plan/review.md:188` | "About 250 words, up to 10% over (275)"; the caps; "About 1,000 words" | Group 1f, numeric output ceilings | These cap records that later sessions read, and the cleanup's measure exists to hold them (AY8, AZ9): a stated, measured reason, not a clamp against an older model's verbosity | Low | none: kept, listed so the next audit need not ask again |

No finding was made against `np-gui`'s level files, the steward's failure classes, the physics rule, the three agents,
or `author.md`'s choice protocol: each states context or a reasoned constraint that only the author holds.

## Proposed diff

One hunk per finding at high or medium confidence with a `rewrite` or `remove` action outside another item's scope.
WP6.03 takes them; F5 and F6's eighth script are this package's own items 5 and 7; F7 is WP6.03's removal of the
host.

Hunk 1 (F1):

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ *Models*
-`/np-implement` runs on Opus 5.5 at high effort, set explicitly. A scoped item goes to a Sonnet 5.5
+`/np-implement` runs on Opus 5.5 at high effort, set explicitly; the two cleanup packages, WP6.02 and
+WP6.03, run whole on Fable 5.2 (§8.2.49 AY7). A scoped item goes to a Sonnet 5.5
```

Hunk 2 (F1):

```diff
--- a/.claude/skills/np-plan/wp.md
+++ b/.claude/skills/np-plan/wp.md
@@ ## Grounding the plan
-The plan is written on Fable 5.2 for an implementer on Opus 5.5 who has not seen this session. An item marked for a
+The plan is written on Fable 5.2 for an implementer on the model `CLAUDE.md`'s *Models* names, who has not seen this session. An item marked for a
```

Hunk 3 (F4):

```diff
--- a/.claude/skills/np-ship/wp.md
+++ b/.claude/skills/np-ship/wp.md
@@ ## 4. Review pass
-Observed 2026-11: inside an `Agent` the skill returned no findings. Called directly, it starts its
-own review agent. Keep the review without gaps.
+Inside an `Agent` the skill returns no findings; called directly, it starts its own review agent.
```

F2 and F3 take no hunk until the author rules. Once WP6.03 has merged, hunk 1's exception has no package left to
cover and goes with the next edit of *Models*.
