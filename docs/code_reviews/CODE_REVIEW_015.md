# Code review: PR 128, the Phase 5 plan and the author's rulings (§8.2.17)

24 October 2026 · `33a7971..d5134a7` (`claude/zen-cray-yc2751`) · scope: the pull request's diff ·
focus: correctness, convention · effort: xhigh, with `--fix` · status: completed

## Summary

The pull request plans Phase 5 as a browser workbench, records the rulings S1 to S15 as §8.2.17,
amends §8.1, §8.3, §8.4.1, §8.4.4 and RSK-15, and adds a two-lane rule to the workflow so that WP57,
a prose-only design study, can run beside Phase 4. It changes no code and no test. The claims the
plan makes about the code hold: only `gui/app.py`, `gui/probe.py` and the seven widget modules import
PySide6; `SolverProcess`, `EventCancel`, `Finished`, `Failed` and `Cancelled` are in `gui/solver.py`;
`mesh/primitives.py` has the three geometries; `physics/models.py` registers six models; VER-77 is one
above the highest identifier. `docs/scripts/generate.py` reproduces the new navigation entry exactly.

The defects are in the two-lane rule's reach. The level files that tag a package still tag every
package. For WP57, whose changelog entry waits under the next release, `/np-ship` §7 would read the
tag `v0.6.0` from that section and publish the release early (finding 1). Phase 4 still has unnumbered
packages that the Phase 4 plan numbers "from WP56", so the WP57 and WP58 numbers can collide, and the
renumbering rule does not cover package numbers (finding 2). The core's wording of that rule could
give two items one number (finding 3). `current.md`, rewritten here, still sent the next session to
ship WP53, which merged on 23 October (finding 4).

Eight findings are fixed in the working tree, uncommitted, one of them in part; six are left to
`/np-ship` and the author, because each would change a ruling or a package's scope. No test, gate,
or documentation build was run. `generate.py` was run once, and `mkdocs.yml` did not change.

| Severity | Count |
|---|---:|
| High | 2 |
| Medium | 6 |
| Low | 6 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `.claude/skills/np-ship/wp.md` §6, §7; `.claude/skills/np-implement/wp.md` *Finishing* | S15 and the core's *Two lanes*: a package merged before its previous phase's release takes no alpha tag, and its `CHANGELOG.md` entry waits under the next release. The level files were not changed. `np-implement` still requires a section "under `vX.Y.Z-alpha.N`" and reports "the tag". `np-ship` §7 takes the tag "from its `CHANGELOG.md` section". For WP57 that section is `[0.6.0]`, so §7 would tag WP57's merge `v0.6.0`, and `release.yml` would publish the v0.6.0 Release before Phase 5 is built. | Fixed: both files state the exception. §7 reports that no tag applies and stops. §6 and the `np-implement` report say "or that it gets none". |
| 2 | `docs/plans/phase-5-workbench.md` WP57, WP58; §8.2.17 S1, S14 | The Phase 4 plan leaves its fix packages ("numbered from WP56"), documentation increment 4 and the close unnumbered: they "take their numbers then", at the second `/np-plan amend 4`. Phase 4 therefore needs at least WP56 to WP58, and Phase 5 claims WP57 and WP58. S15's renumbering covers `REV-nn`, history records, code reviews and `VER-`/`VAL-`, but not package numbers. Plan file names, PR titles (the core finds a PR by `WP<n> —`), tags and `current.md` would all name two packages with one number. | Not fixed: the numbers are in S1 and S14. For the author: number Phase 4's remaining packages now, start Phase 5 above them, or add package numbers to S15's list. |
| 3 | `.claude/workflow/core.md` *Two lanes*, last bullet | The core said "renumber each new … that `main` already uses, to one above the highest there". §8.4.4 renumbers all of the branch's new items. Take a branch that adds REV-126 and REV-127 while `main` adds only REV-126. The core moves REV-126 alone, to 127, which is the branch's other new row: two rows get one number. The core also did not say that each reference to a renumbered item moves with it: the §8.2.N ranges in five files, the history index line, the `mkdocs.yml` entry, and the letter series. | Fixed: "renumber the branch's new … each kind in order from one above the highest on `main`, and every reference to them", as §8.4.4 says. |
| 4 | `docs/plans/current.md` *Position*, *In brief*; `specification/history/17-…md` opening | PR #124 (WP53) merged on 23 October, and `v0.5.0-alpha.19` is published on its last commit. This pull request rewrote these lines on 24 October and kept "WP53 … is **implemented** on its branch … Next: **`/np-ship wp 53`**", "WP35 to WP52 are merged; tags to `v0.5.0-alpha.18`", and "the working instructions await review". The ruling record said "WP53 was unshipped". Phase 4's remaining work also left out the documentation increment and the close, and "WP58 after it" was ambiguous next to S1. | Fixed: Phase 4 is one lane line (WP35 to WP53 merged and tagged to `v0.5.0-alpha.19`; `v0.5.0-alpha.16`, WP50's tag, is still unpublished and the author's step; next `/np-plan wp 54`), the In brief is current, WP58 comes "after `v0.5.0`", and the record says WP53 had merged. `current.md` is now 695 words, within its 700. |
| 5 | `docs/plans/phase-5-workbench.md` WP57; §8.4.4 (the second lane) | The second lane "changes no `src/`, `tests/`, case schema or public API" before `v0.5.0`. WP57 may merge before `v0.5.0`, yet it restates VER-43, VER-44, VER-55, VER-60, CON-09's PySide6 clause, ADR-004's packaging NOTE, RSK-13, P3 and QR-10 for the browser shell, and adds requirement identifiers. M3 rules that the shell's gating clauses keep gating the Qt shell until Phase 5 replaces it, so that v0.5 ships a gated surface. If WP57 lands first, `v0.5.0` carries a specification whose gating clauses describe a shell that does not exist, while its tests still check the Qt shell. | Not fixed: S2, S12 and M3 put the restatement in WP57's design-document commit. For the author: add the restated clauses as new v0.6 identifiers, hold the restatement until after `v0.5.0`, or add the normative clauses to the lane's exclusions. |
| 6 | `.claude/skills/np-plan/phase.md` lines 45, 84; `.claude/skills/np-plan/wp.md` line 58 | `phase.md` told the phase level to "replace the position with Phase n planned". The core's new rule is "Edit only your lane's line", and an overlapping phase plan like this one would erase Phase n−1's line. Both `np-plan` files also kept "green … before the next [package]" without the lane qualifier that §8.4.4 and `CLAUDE.md` now carry. S15 updated `np-implement` and `np-ship` but not `np-plan`. | Fixed: the phase level adds its line beside an open Phase n−1, and both files say "before the next … of its lane". |
| 7 | §8.4.4 (line 63), S15, the core's *Two lanes* | The renumbering list leaves out FR-, QR-, IF-, CON-, RSK-, ADR- and OPN- identifiers. WP57 writes exactly these ("Each settled requirement enters the specification as an identifier tagged v0.6"), and Phase 4's fix packages may add the same kinds. It also leaves out the ruling letter series: two lanes that each write §8.2.18 would also both take the letter T. | Not fixed: the list is S15's. For the author: widen it to every numbered identifier and the letter series. |
| 8 | `docs/plans/phase-5-workbench.md` *Open decisions*, row 3 | REV-73 (cross-leaf inertness, physics) is `fixed` by WP42, not an inherited Phase 5 row. `MOD-18` is missing, although §8.2.8 H10 says "Phase 5's plan inherits the finding". `MOD-11` is ruled by Phase 4's sessions and fixed in a Phase 4 fix package (H2; the history index reads "H2 - open: the user-testing sessions rule `MOD-11`"), so WP57 does not propose it. | Fixed: REV-73 and `MOD-11` are removed, `MOD-18` is added, and `MOD-13` is narrowed to its command-line part (the part MOD-13's recommendation deferred to Phase 5). |
| 9 | §8.4.1 (line 24); `CONTRIBUTING.md`; plan WP58 | "N counts the phase's work packages" (`CONTRIBUTING.md`). If WP57 merges untagged, WP58 is either `v0.6.0-alpha.2` (N counts packages) or `v0.6.0-alpha.1` (the first tag), and no text decides which. `np-plan/phase.md` asks each package for its tag, but WP58 has none. In a newest-first changelog, "the next release's section" is not defined: `[0.6.0]` placed above the later `[0.5.0-alpha.N]` and `[0.5.0]` sections breaks the order, and `[Unreleased]` is not named. | Not fixed: the numbering is a rule of versions for the author. Recommendation: N counts tags, WP58 is `-alpha.1`, and the entry waits under `## [Unreleased]`. |
| 10 | `.claude/skills/np-ship/wp.md` §1 (line 32) | The renumbering runs only when a later `/np-ship` merges `main` into a stale branch. If the author merges both lanes' PRs one after the other, nothing runs it. Two different history files, or two `VER-` rows in different files, give no textual conflict, and no test checks that identifiers are unique. The duplicate reaches `main` silently. | Not fixed: outside this diff. A uniqueness check of identifiers in CI, or "require branches to be up to date", would enforce the rule. |
| 11 | `docs/plans/phase-5-workbench.md`; `.claude/workflow/core.md`; `docs/plans/current.md` | Word caps: the phase plan has 1,612 words before its report, and `np-plan/phase.md` sets a target of 1,500 that review checks (§8.2.13 N3). `core.md` grew from 985 words (WP53 D2's cap, as REV-125 set it) to 1,104. The workflow files hold 7,659 words, against a cap of 7,518. `current.md` had 704 words, against the 700 of its *Handoff Rules*. | Fixed in part: `current.md` is 695. The plan and the core are not cut (the core is now 1,111, after finding 3). Choosing what to cut is the author's call, as it was for REV-125. |
| 12 | `docs/plans/phase-5-workbench.md` WP59 onward; RSK-15; §8.1 *Tool phases* | v0.6 includes the charge-level mutator (S4), and the plan's context says "the library has no residue mutation". RSK-15's restated mitigation says that no screen is built for a capability Tiers 1 and 2 do not verify. §8.1 makes every other tool library-first. The plan gives the mutator no library step and no Tier 1 or Tier 2 row: it is listed only among the shell packages. | Not fixed: placing the mutator is WP57's design work. Recommended for WP57's requirements: a library function over the PQR artefact, with its own Tier 1 test, before the tab. |
| 13 | `specification/history/index.md`, M3 | S8 says that M3's "the design document chooses its server library" is settled by WP58's spike, but the index still sent M3 only to current clauses. | Fixed: "M3 - ADR-004, CON-09, §8.1; its choice of the server library superseded by S8". |
| 14 | `docs/plans/phase-5-workbench.md` *End-of-phase report* | `np-plan/phase.md` requires "the list of numbers it must report, each with the test that logs it". The click-to-redraw time, the install time on a clean machine and VER-77's counts name no test or command that logs them. | Not fixed: WP58 defines the measures. For WP58's plan. |

## Verified and found clean

- The plan's "true of the codebase today" list against `src/nanopnp/gui/`, `mesh/primitives.py` and
  `physics/models.py`; the stage-7 PQR step (§5.2); VER-43, VER-44, VER-55 and VER-60 are the shell's
  gating clauses; VER-77 follows VER-76; IF-03, QR-10, QR-13 and P1 to P3 read as cited.
- The quotations of M3 and F5 in S1, S8 and S9; every "§8.2.1 to §8.2.N" range now ends at 17;
  `mkdocs.yml` matches `generate.py`'s output; the record's front matter matches records 15 and 16.
- The other inherited rows (REV-20 to REV-67 and REV-114) are each deferred to Phase 5 in
  `review-items.md`; H4 sends `MOD-09` to Phase 5.
- RSK-15's severity change matches S7, and its columns are in the order Severity, Likelihood.
