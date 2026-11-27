# Code review 098: the chore that brings the /code-review hunt back before np-reviewer (§8.2.61 BK1 to BK3)

2026-11-27 · branch `ccr-a1bfde87-pka0hj`, head `451daaa` on base `a494a0c` · scope: one commit, 14 files, +105
and −28, read from `git diff a494a0c...451daaa`, against the chore's statement (no plan), §8.4.4, §8.4.5,
§8.2.56 BF4, BF8, BF11, §8.2.58 BH1, §8.2.61 BK1 to BK3 and `CLAUDE.md` · reviewer: `np-reviewer`, Opus 5.5 at high
effort · status: completed.

Static review of Markdown alone: the chore changes nothing under `src/` or `tests/`, so no hunt ran before this
review (BK3). Probes: `.claude/skills/np-ship/wp.md` at `5b1e7fb` for the call before WP6.07 and its note;
§8.2.56's preamble for the model of the forks; each agent's `tools:` for `Skill`; `.claude/settings.json` for a
permission line; `np-ship/SKILL.md`, `phase.md`, `np-shipper.md`, `np-plan/review.md` and `.claude/workflow/` for
every other path that starts a review; the tracked files that are code without a `.py` or `.sh` suffix. Line numbers
are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/skills/np-ship/wp.md:99-103`; `.claude/skills/np-carry/SKILL.md:92-97` | Axis 2, BK1 ("lists each in its one report with its outcome"). Under `/np-carry` the main session writes the hunt's findings into the reviewer's prompt and passes back only the reply, so the fresh `np-shipper` that checks the reply never sees the findings and cannot check "each of the hunt's included". Its retry of a reply that lacks the evidence hands back the template again, ending `<to be added>`, so the main session would run the hunt a second time on the same head, which no ruling asks and which is the repeated review BF4 cut. Confirmed | Fixed: the carry passes the findings with the reply; a second start of the reviewer takes the same prompt with the findings written in, so the hunt does not run again (`wp.md`, `np-carry`, `helper.md`, §8.4.4) |
| 2 | Low | `.claude/skills/np-carry/SKILL.md:92` | Axis 2, BK3. The carry ran the hunt wherever the prompt ended with the placeholder line, whatever the block's effort; a medium-effort review whose prompt a helper copied from §4's template would run it, which BK3 excludes. Doubt | Fixed: the hunt runs where the block asks no `effort: medium`, a review at medium runs none, and `helper.md` says a medium review's prompt has no such line |
| 3 | Low | `.claude/agents/np-reviewer.md:47-49` | Axis 2, BK1. Lines 16-18 give a hunt finding the outcome "refuted, with the reason", but the reply's outcomes stayed fixed or left, so a refuted lead had no place in the reply that §4's evidence rule reads. Confirmed | Fixed: the reply's outcomes add "refuted (with the reason)" for one of the hunt's |
| 4 | Low | `specification/08-implementation-plan/04-development-process.md:139` | Axis 2, BK1. "the reviewer judges each on its axes and fixes it as one of its own" reads as fixing every lead; BK1 fixes what the reviewer confirms. Confirmed | Fixed: it fixes, leaves or refutes each in its one report, and a second start takes the same findings |
| 5 | Low | `specification/08-implementation-plan/04-development-process.md:256` | Axis 1, prose. The inserted clause "and runs the hunt, a skill that starts its own agents" makes the next "it keeps the task list" read as the main session; the helper keeps it (§8.4.4). Confirmed | Fixed: "the helper keeps the task list" |
| 6 | Low | `.claude/skills/np-ship/SKILL.md:3`; `.claude/skills/np-carry/SKILL.md:10-11` | Axis 2, BK1. The ship's description and the carry's list of what its main session does omit the hunt, which the chore puts in `CLAUDE.md`. Confirmed | Fixed: both name it |
| 7 | Low | `.claude/skills/np-carry/SKILL.md:95`; `.claude/skills/np-ship/wp.md:102`; §8.4.4 line 140 | Axis 1, prose. Three edited lines ran to 130 to 170 characters against the files' wrap near 105. Confirmed | Fixed: rewrapped in the fixes of 1 and 4 |
| 8 | Low | BK3; `.claude/skills/np-chore/SKILL.md:36-38` | Axis 2. The chore implements BK3's letter, a `.py` or `.sh` file or a path under `src/` or `tests/`. Code without those suffixes escapes the hunt: `.githooks/pre-push` (a shell script), `.claude/scripts/gui/*.cjs`, `justfile`. A chore that changes only them gets `np-reviewer` alone. Widening the test moves the ruling. Doubt | Left to the author, who ruled it the same day as §8.2.61 BK4: `.githooks/`, `.cjs` files and `justfile` join the chore's hunt, beyond the recommendation, which left the justfile out. Fixed by the chore's session |

The pass fixed seven findings and left one.

## Checked and found true

- **One call, one syntax.** `wp.md` §4 and `np-chore` step 6 give the same `Skill(skill="code-review", args="high
  --max-findings all <head branch> -- Report only: …")`, `<branch>` in the chore being its head branch; `np-carry`
  points to `wp.md` §4. The order is level, flag, target, `--`, free text, as in `np-plan/review.md`'s call and the
  call at `5b1e7fb`; there is no `--fix` (BK2).
- **Only a session that can start agents runs it.** No agent's `tools:` lists `Skill`; `np-shipper` hands back
  `REVIEW`; the chore refuses under a carry or as a helper, reviewer or worker. The hunt runs in the standalone
  ship, in the carry's main session on a full `REVIEW`, and in a chore that changes code; a phase close reaches it
  through `wp.md`. The medium reviews of `wp.md` §4 item 1 and the chore's step 7 run none.
- **The carry's main session still edits nothing.** The hunt's free text forbids an edit, a commit or a written
  file, and filling the prompt's last line is a change to a prompt, as its replacement of the head sha already is.
  The carry's rule against starting an agent during a land or a `RUN` holds: the hunt follows the land.
- **Resuming after a review holds.** The hunt makes no commit, so `wp.md` §0 step 3's list of commits after the
  reviewed head is unchanged.
- **The records.** `holds-now.yaml` gives BK1 to BK3 their clauses and BF4 its amendment; the decisions page gains
  three rows and BF4's amended row; the history index has 8.2.61's line; the knowledge note's footnote quotes
  `wp.md:77` at `5b1e7fb` word for word and §8.2.56's preamble on the forks' model; `knowledge/log.md` has the entry.
- **No permission line is added.** `.claude/settings.json` is unchanged.

## Not assessed

- The skill's behaviour at run time: whether it writes nothing without `--fix` when its free text asks so, and
  which base it diffs a branch target against. Nothing was run here.
- `just land` and the pull request's CI, which the session that started the review runs.

## Addendum: the commit that rules finding 8 (§8.2.61 BK4)

2026-11-27 · head `bef82af` on base `fec3c9c` · scope: one commit, 7 files, +18 and −15, read from
`git diff fec3c9c...bef82af`, against BK3, BK4, §8.4.4 and the chore's step 6 · reviewer: `np-reviewer`, Opus 5.5
at high effort · status: completed.

Static review of Markdown and YAML alone. Probes: the tracked files outside `src/`, `tests/` and `.githooks/` that
are code without a `.py`, `.sh` or `.cjs` ending; every text that states the chore's hunt trigger; the decisions
page's rows for BK3 and BK4 against the convention of an earlier widened ruling (§8.2.53 BC3).

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 9 | Low | BK4; `.claude/skills/np-chore/SKILL.md:37-38`; `.claude/scripts/gui/digest.tpl.html` | Axis 2, BK4 ("code without those endings"). `digest.tpl.html` holds 107 lines of inline JavaScript that `digest.py` fills in and writes out; it is one of the GUI's scripts in all but its ending, and a chore that changes it alone gets `np-reviewer` alone. `.devcontainer/Dockerfile` is the only other code-like file left out, and it is on no run path of the package or the gate. The `.js` under `docs/design/` are generated mockups, not code any path runs. Widening the test again moves BK4. Doubt | Left to the author, who ruled it the same day as §8.2.61 BK5, the recommendation: everything under `.claude/scripts/` joins the chore's hunt, and the Dockerfile keeps `np-reviewer` alone. Fixed by the chore's session |

The pass fixed none and left one.

### Checked and found true

- **One statement of the trigger.** BK4, §8.4.4's bullet and step 6 give the same paths in the same order; no other
  text (`CLAUDE.md`, `np-reviewer.md`, `.claude/workflow/`, the ship and carry skills) states the chore's trigger, so
  none is left at BK3's letter. Step 6 cites BK1 to BK4 and §8.4.4 cites BK3 and BK4.
- **The records.** BK3 carries "*Its paths are widened by BK4.*" and its *Holds now* says so, as BC3 does for BI1;
  BK4 has its *Holds now*; the decisions page gains one row, its counts one ruling and one binding row; the
  history index and the record's description name the added paths. The garbled lead of BK3's and BK4's rows on the
  decisions page is how `decisions.py` renders every row that opens with an italic note (BC3, AZ13).
- **What a session could do with it.** The change adds no permission line and moves no path into or out of the
  always-reviewed list; it only makes the report-only hunt run on more chores, from the session that already runs
  it. A fix's own diff still gets the medium review without the hunt (BK3, unchanged by BK4). Finding 8's outcome
  states the author's choice and that it went beyond the recommendation.
- **Wrap.** The edited lines of §8.4.4 and step 6 run 77 to 98 characters.
