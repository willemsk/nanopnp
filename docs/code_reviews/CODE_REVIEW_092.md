# Code review 092: /np-chore, a change outside a work package

2026-11-26 · branch `chore/np-chore`, head `2764a50` on base `368ca66` (`origin/main`) · scope: the chore's one
commit, 10 files, +91 and −4, read from `git diff origin/main...2764a50`, with the chore's statement in place of a
plan. Against §8.4.4, §8.4.5, §8.2.57 BG1 to BG5 and §8.2.56 BF8 and BF11. Read in place: `.claude/workflow/core.md`
(*Gate and push*, *Two lanes*), `helper.md`, `finish.md`, `np-carry/SKILL.md`, `np-ship/wp.md` §0 and §1,
`land.sh`, the `land` and `check-records` recipes, `prose-only.sh`, `duplicates.py`, `ci.yml`'s triggers and its
`changes`, `docs` and `CI result` jobs, the agents' tool lists and `.claude/settings.json` · reviewer: `np-reviewer`,
Opus 5.5 at high effort · status: completed.

Static review: no `gate.sh run`, no benchmark. Probes: `duplicates.py`, `decisions.py --check` and `links.py` on
the head and after the fixes, all passing; `ci.yml` parsed as YAML; `pytest -m records`, 3 passed. No code under
`src/` or `tests/` changed, so the physics and numerics axis has nothing to read, and no test is due (§8.2.13 N1).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/skills/np-chore/SKILL.md:18` | Axis 2, BG3. Step 3 reuses the harness-bound branch, reset to `origin/main`, judging only the local branch. `land.sh` step 4 rebases on `origin/<branch>` wherever it exists and is not an ancestor of `HEAD`, so a bound branch whose remote copy holds commits, an earlier chore's or package's, brings them into the pushed chore after `np-reviewer` read `origin/main...<head>`: the PR then carries commits no review saw | Fixed in `a868818`: the bound branch is reused only where `origin/<it>` is absent or holds no commit past `origin/main`; a new `chore/<slug>` takes a slug no branch on `origin` has |
| 2 | Medium | `.claude/skills/np-chore/SKILL.md:27` | Axis 2, BG3. The ruling always reviews "the hooks, the agents, the skills or the workflows", because `prose-only.sh` passes `.claude/` as prose. The skill lists `.github/workflows/`, which is never Markdown, and leaves out `.claude/workflow/` (`core.md`, `helper.md`, `author.md`, `finish.md`), which is: a chore that edits only the core would skip the review | Fixed in `a868818`: the skill lists `.claude/workflow/`, and §8.4.4 names the workflows of `.claude/` and `.github/` |
| 3 | Low | `.claude/skills/np-chore/SKILL.md:42`; §8.4.4; §8.2.57 BG4's consequence | Axis 2, BG4. "An open package rebases on `main` at its next land (core, step 7)": `land.sh` runs the core's steps 1 to 6 and rebases only on `origin/<branch>`, never on `main`. A package is brought up to `main` at its ship, `np-ship/wp.md` §1. The prior review's "`just land` does not rebase on `main`" stood unanswered in the text | Fixed in `a868818`: "at its ship (`np-ship/wp.md` §1), as `just land` never rebases on `main`" in the skill, §8.4.4 and BG4's consequence column. The decision, a chore is not a lane, is unchanged; the author may reword the record's column |
| 4 | Low | `.claude/skills/np-chore/SKILL.md:16` | Axis 2, BG2 against `np-carry` §4. "A helper that finds a chore hands back `DONE` with it under **Open**": `np-carry` reads a plan helper's `DONE` as the plan's end and asks for approval, and an implement helper's as the next item. No helper reads this file either: the helpers' tool lists hold no `Skill` tool | Fixed in `a868818`: a helper, the reviewer or a worker names the chore in its hand-back or reply and makes it nowhere |
| 5 | Low | `.claude/skills/np-chore/SKILL.md:14` | Axis 2, BG2. The refusals, "commits past `origin/main`" among them, came before step 3's `git fetch origin main`, so they read a stale `origin/main` | Fixed in `a868818`: the fetch opens step 2 |
| 6 | Low | `.github/workflows/ci.yml:186` | Axis 1. The `docs` job's comment lists its checks and omitted the new one | Fixed in `a868818` |
| 7 | Low | `specification/history/index.md:70` | Axis 1. The entry's description began in lower case, unlike every other | Fixed in `a868818` |
| 8 | Medium | `.claude/skills/np-chore/SKILL.md:14` | Axis 2, BG2, a doubt. "Where no carry is running" is checked only in this checkout. The hand-off-note refusal can never fire on a tree that passes the other two: a note lives on a package branch (commits past `origin/main`) or uncommitted (a dirty tree), and the ship deletes it before the merge, so `main` holds none. A carry in another worktree, clone or cloud session goes unseen | Left to the author. Recommendation: say in the skill and §8.4.4 that the refusals see this checkout alone and the author's start of the session is the check, and drop the dead hand-off-note refusal; or add `git worktree list` showing a package branch as a refusal |
| 9 | Medium | `.github/workflows/ci.yml:204` | Axis 2, BG5, a doubt. On a pull request the step checks the merge with the base as it was when the run started. GitHub reruns nothing when `main` moves, so a green `CI result` goes stale, and a number shared after a later merge is caught only by the push-to-`main` run, on `main` | Left to the author. Recommendation: require branches to be up to date before merging, in the branch protection, or rerun CI on a chore or package PR before merging it when `main` moved |
| 10 | Medium | `.claude/skills/np-chore/SKILL.md:35`, steps 7 to 9 | Axis 2, BG3, a doubt. The one review reads the head before the land. A fix of a failed land, of a red CI or of what the author asks for on the PR is committed after it, can be code or workflow, and is reviewed by no one; the skill says nothing of a red CI on the chore's PR | Left to the author. Recommendation: a commit after the review that is not Markdown alone gets a review of its own diff by `np-reviewer` at medium effort, as BF8 does for a package; a red CI follows the ship's rule (format and lint by the session, every other failure to Opus) |
| 11 | Medium | `.claude/skills/np-chore/SKILL.md:10` | Axis 2, §8.4.5 against BG1 and BG2, a doubt. "The author starts the session for it on Sonnet 5.5 at medium effort", while BG2 lets any session run it and BG1 sets no limit on content: a chore may change physics in `src/` built on Sonnet at medium, where §8.4.5 has Opus 5.5 at high build and the core keeps physics decisions in an Opus session. No ruling names a chore's model | Left to the author. Recommendation: a chore that touches `src/` or `tests/` is built on Opus 5.5 at high, written into §8.4.5 and the skill; Sonnet at medium for the rest |
| 12 | Low | `.claude/skills/np-chore/SKILL.md:3` | Axis 2, BG1, a doubt. The description lets the model start the skill itself "when the author asks for a small change that no package owns", so a request in passing can open a branch, a review, a land and a PR the author did not ask for by name. No ruling says whether the model may | Left to the author. Recommendation: `disable-model-invocation: true` in the front matter, or "Use on /np-chore" alone |

The pass fixed seven findings and left five, all doubts.

## Checked and found true

- **The CI step runs where BG5 says.** `ci.yml` triggers on `pull_request`, on a push to `main`, on a dispatch and on
  a call; the `docs` job runs in every mode but `nightly`, and `CI result`, the required check, needs it. On a pull
  request `actions/checkout` with an empty `inputs.ref` takes the merge ref, so the step sees the PR's numbers beside
  the base's. `duplicates.py` reads the working tree alone and imports the standard library alone, so the job's
  `fetch-depth: 0` is more than it needs and `uv run --no-sync` runs it after the `docs` group's sync.
- **BF11 stands.** A chore's session runs a command itself, so it is the main session that §8.4.4's land bullet and
  the core's *Gate and push* let land; the helpers, the reviewer and the workers cannot start the skill, having no
  `Skill` tool, and the carry's main session refuses it.
- **The records agree.** After the fixes the skill, §8.4.4's bullet, BG1 to BG5, their `holds-now.yaml` entries,
  `CLAUDE.md`'s line and the reviewer's description say the same; `decisions.md` matches the records and
  `mkdocs.yml` carries the record. The chore adds no permission line: `.claude/settings.json` is unchanged.
- **The reviewer's prompt and the open items.** Step 6's prompt matches `np-reviewer`'s inputs, the statement standing
  for the plan; a finding left to the author becomes a `REV` row owned by the current phase before the land, as
  §8.4.6 asks.

## Not assessed

- `just land` end to end on this branch, the push gate and the strict documentation build, which the chore's session
  runs.
- The chore's CI on its pull request.
