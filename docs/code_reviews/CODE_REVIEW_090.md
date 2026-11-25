# Code review 090: WP6.09, the lean carry

2026-11-25 · PR #219, head `251cca8` on base `5946602` (`main`) · scope: the whole package, 34 files, +790 and −209,
read from `git diff 5946602...251cca8`; the checkout was at the PR's head and clean. Above all the four agent files,
`land.sh` and its recipe, the carry, plan and ship skills, `helper.md` and §8.4.4 and §8.4.5 against §8.2.56 BF1 to
BF9, §8.2.50 AZ20 and AZ21, §8.2.54 BD2 and the plan's D1 to D7. Read in place: `.claude/workflow/core.md` and
`finish.md`, `.claude/skills/steward/SKILL.md` (*Failure classes*), `np-implement/finish.md`, `decisions.py` and
`index_records.py` (what each writes), §8.4.1, `CONTRIBUTING.md`'s *Versions and releases*, knowledge 07/26 and
`.claude/rules/python.md` and `physics-numerics.md` · reviewer: `np-reviewer`, Opus 5.5 at high effort, the
package's one review (§8.2.56 BF4) · status: completed.

Static review: no `gate.sh`, no `pytest`, no benchmark. Probes: `land.sh`'s source filter under `pipefail` on
generated name lists of 10 to 50,000 lines; the `land` recipe's argument passing on a copy of the recipe under
`just` 1.59.0; `land.sh` with a wrong argument after the fix; `gh auth status` on the cloud host. No code under `src/`
or `tests/` changed, so the physics and numerics axis has no form, flux, gate or tolerance to read, and no test is
added or due (§8.2.13 N1, N3).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/scripts/land.sh:39`, step 1 | Axis 2, D7 and the core's step 1. `decisions.py` writes two pages, `docs/project/decisions.md` and `decisions-closed.md` (`CLOSED_PAGE`); step 1 adds and checks only the first. Whenever the closed page changes, it stays uncommitted and step 2 stops `land` at "a clean tree" | Fixed: the closed page joins the register paths |
| 2 | Low | `.claude/scripts/land.sh:58`, step 3 | Axis 2, D7: a check that can skip in silence. `git diff … \| grep -E … \| grep -vqE …` under `pipefail`: the last `grep -q` exits at its first match, the middle `grep` takes SIGPIPE, and the pipeline returns 141, so the documentation build is skipped. Measured: from about 10,000 changed names on; below a pipe's buffer it holds. CI's `docs` job would still catch the fault | Fixed: the names are collected first and tested for emptiness |
| 3 | Medium | `.claude/scripts/land.sh:27`; `justfile`, `land` | Axis 2, the core's step 7. The recipe's first parameter is the log, so `just land --lease <sha>` takes `--lease` for the log and hands `land.sh` the sha alone, which it ignored: a branch rewritten on `main` was then rebased on its old remote head instead of pushed with the lease. Nothing named the order | Fixed: `land.sh` refuses any argument but `--lease <sha>`; the recipe's comment and the core's step 7 name `uv run just land <log> --lease <sha>` |
| 4 | High | `.claude/agents/np-builder.md:6`, `np-planner.md:6` | Axis 2, BF6 and D6 against the skills each agent follows. The builder finds the package's PR among the open PRs (the core's *The package's PR and branch*), opens it and writes its **Measured** (`np-implement`, `workflow/finish.md`); the planner opens the plan's PR (`np-plan/wp.md`, step 4). Neither file lists a GitHub tool, and on the cloud host `gh` is not logged in (`GH_TOKEN` refused). Item 1's probe asked each agent for its tool list, not for a PR | Not fixed: the edit of an agent's tool list was refused to this review by the permission check. Recommendation: add `mcp__github__list_pull_requests`, `pull_request_read`, `create_pull_request` and `update_pull_request` to both lists (deferred, so the start context barely moves) |
| 5 | Medium | `.claude/skills/np-carry/SKILL.md:30`, §2 | Axis 2, BF2 and D2. The first plan helper commits `docs: WP<n> plan draft` in the plan's file; a branch that shows that draft matches no row of the stage table, since the plan exists and its `implementation plan` commit does not | Fixed: the first row takes "or only its draft" |
| 6 | Medium | `.claude/skills/np-carry/SKILL.md:79` and `:86`, §4 | Axis 2, BF2 and the plan's item 2 ("the answer starts a fresh helper … with 'Read `<note>`, then continue at Next'"). A checkpoint's `DONE` started the next builder with "Start at item k" alone, so the note's **Decided**, which no record holds, was lost; a `WAIT` named no prompt for a step that leaves no note | Fixed: the checkpoint's builder gets §3's prompt after a hand-back with its note; the `WAIT`'s shipper gets §3's first prompt and the event |
| 7 | Medium | `.claude/skills/np-ship/wp.md:21`, §0 step 3 | Axis 2, D2 and D4. A ship helper records the reviewed head, then commits `docs: WP<n> hand-off, ship` before it hands back `REVIEW` (`helper.md`). That commit lies after the reviewed head and is not among the commits the resume allows, so a fresh shipper woken by CI or the merge failed the check and ran the whole review again | Fixed: the resume allows a helper's hand-off commits |
| 8 | Medium | `.claude/skills/np-ship/wp.md:57` against `.claude/agents/np-shipper.md:13` | Axis 2, D4 ("the shipper writes no fix"). §4 still had the ship delete each test outside the test scope; the shipper's file says it changes no test. The reviewer's first axis already holds the test scope | Fixed: §4 gives the test scope to the reviewer, and its prompt asks it to drop each such test in its own commit |
| 9 | Medium | `.claude/skills/np-ship/wp.md:106`; `.claude/agents/np-shipper.md:13` | Axis 2, BF1. BF1's consequence escalates to Opus "a red CI that is not lint, format or a flaky runner", so lint and format stay with the ship; the diff sends only "a test or a numerical gate" to `np-builder` and has the ship fix no code. A `ruff` failure, and any class that is neither (`docs`, a stale lock, `mypy`), then has no owner. The ruling's option text and its consequence say different things | Not fixed: the fix chooses between the ruling's two wordings, and it edits an agent file. Recommendation: follow the consequence: the ship runs `ruff format` and `ruff check --fix` alone and reruns a flaky runner; every other failure goes to `np-builder` |
| 10 | Low | §8.4.4, `specification/08-implementation-plan/04-development-process.md:178`; `docs/plans/current.md:40` | Axis 2, BF1 supersedes AZ20 and AZ21. The auto-ship bullet still cited AZ21, and *Not to be re-decided* still said "each plan proposes its two models (AZ20, AZ21)" | Fixed: the bullet cites BF1; the line names the agents' models and the author's pick of the planning model (BF1, BF9) |
| 11 | Low | `.claude/workflow/finish.md:32`; `.claude/skills/np-implement/finish.md:69` | Axis 2, BF5. Both still said the ship puts each finding against the implementing session's decisions to the author; a finding the review leaves is now an open `REV` row | Fixed: both say so, citing BF5 |
| 12 | Medium | `CHANGELOG.md:28`; the plan's status line | Axis 2, §8.4.1: "From Phase 5, N is the package's number within its phase". WP6.09 takes `v0.7.0-alpha.7`, which is WP6.07's by that rule; `alpha.9` would instead put a lower version on `main` after it when WP6.07 merges, against "versions on `main` only increase". §8.2.54 BD1 numbers Phase 6's packages in the order they are built, which this package, built seventh, does not follow. No clause is amended | Not fixed: a ruling. Recommendation: the author rules that Phase 6's alpha numbers follow the merge order from here, and §8.4.1 and `CONTRIBUTING.md` say so in this PR; or WP6.09 is renumbered WP6.07 and the two later packages move up, as BD1 reads |
| 13 | Low | `.claude/scripts/index_records.py:102`; `helper.md`, *The hand-off note* | Axis 2, D2. The note lives in `docs/plans/phase-<p>/`, so the plans index lists each note as a plan with "no status line", and every hand-off and the ship's deletion rewrite the index (`land` commits it) | Not fixed: a change to a kept script beyond the plan's items. Recommendation: `index_records.py` skips `*-handoff.md` |

The pass fixed nine findings and left four. Findings 4 and 9 need an agent file changed; 12 needs a ruling.

## Checked and found true

- **The rulings and their clauses.** §8.2.56 holds BF1 to BF9 as the plan's decisions cite them; `holds-now.yaml`
  supersedes AZ20 and AZ21 by BF1 and BD2's resume by BF2, and BF5's review is amended by BF8. §8.4.4, §8.4.5,
  `CLAUDE.md` *Models*, the core's *Models and executors* and the changelog agree with each other on each role's model
  and effort. BF6's project-level plugin block was found to do nothing, removed, and recorded in §8.4.5, the plan's
  Outcome and `holds-now.yaml`.
- **The agents.** Each front matter names `model` and `effort`: planner Fable at high, builder and reviewer Opus at
  high, shipper Sonnet at medium, as D1 says; the knowledge note's probe table matches. Seven agents and nine scripts
  are on disk, as §8.4.5 counts them; the CI-log classifier is on Haiku.
- **The plan's self-check (BF3).** `review.md` keeps the `code-review` call for the other levels only; the eight
  checks match D3; `wp.md` runs it before the commit and hands back `DONE` with the manager's summary.
- **The planning model (BF9).** `/np-plan` asks first at every level, a carry helper skips it, `/np-carry` asks at the
  plan stage and passes `model: "opus"`, `effort: "xhigh"` on each planner call; the plan's status line names the
  model.
- **`land.sh` otherwise.** Steps 1 to 6 follow the core in order; the docs sources match step 3's list (`src/` read as
  a whole); the rebase is skipped with a lease; the push gate runs on the tree after the rebase; the lease form is
  `--force-with-lease=<branch>:<sha>`; each failure prints `land: failed at <step>` and the recipe appends `exit`.
- **The records.** REV-288 and REV-289 are set `fixed` with their sections; the decisions page and its closed page
  agree with the records (`decisions.py` rewrote nothing after this review's edits).

## Not assessed

- `just land` end to end after the fixes, the push gate and the strict documentation build, which the ship runs.
- Whether a fresh helper's note carries enough, and whether one review catches what three did: the plan measures both
  on WP6.07.
