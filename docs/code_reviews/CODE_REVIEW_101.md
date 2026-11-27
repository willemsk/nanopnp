# Code review 101: the chore that keeps a carry off the push gate's tests and idle wakes

2026-11-27 · branch `ccr-a5409d84-cca31n`, head `5eb0fbe` on base `2c2b7b2` · scope: 4 files, +18 and −6, read
from `git diff 2c2b7b2...5eb0fbe`, against the chore's statement (no plan), §8.4.4, §8.2.56 BF11, §8.2.13 N3,
`.claude/workflow/core.md` *Gate and push*, `np-ship/wp.md`, `np-implement/wp.md`, the steward skill, the agents'
files, `gate.sh`, `land.sh` and the `justfile` · reviewer: `np-reviewer`, Opus 5.5 at high effort, with no hunt
findings · status: completed.

Static review of four workflow edits, prose only. Probes: what `gate.sh run` selects (`uv run pytest -q -n auto
--dist loadfile`, the `addopts` selection; records alone on a prose-only range; nothing on a stamped tree); where
the slow and nightly tests live (`tests/tier2/`); what a `RUN` command writes to its log (`helper.md`: its output
only, no `exit` line); Bash's limit for a background command (7,200,000 ms); whether CI posts pull-request
comments (it opens issues only). No test run: the change is Markdown and `.claude/` alone. Line numbers are the
reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/workflow/helper.md:33-34` | Axis 1, internal consistency. "Never hand back a `RUN` of a Tier 1 or 2 selection" forbids the table's own `RUN` row (line 12): the nightly VER-62 walks and every `slow` test are Tier 2 tests under `tests/tier2/`, and `pytest --nightly` is a Tier 1–2 selection. A helper that obeys the sentence runs a walk in the foreground or never runs it. Confirmed | Fixed: the ban is on a marker selection such as `-m tier2`, or the carried tests; a `RUN` names its tests by file or node id |
| 2 | Medium | `.claude/skills/np-carry/SKILL.md:105-106` | Axis 1, the statement's purpose. The refusal reaches a selection "the land's push gate already ran on that head"; WP6.10's `pytest -m tier2` is not one, as it adds the 23 `slow` tests the gate leaves out, so a literal main session serves it and loses the 71 minutes again. Doubt | Fixed: it refuses a command that reruns the push gate's tests, as a marker selection or the carried tests do |
| 3 | Medium | `.claude/skills/np-carry/SKILL.md:107-108`; `helper.md` `RUN` | Axis 1, a gate that can hang. "Decide on the log's `exit` line" relies on a line no `RUN` command writes: `helper.md` asks for the output in a log, and only `just land` and `just gate` append `exit`. The core's wait, `until grep -q '^exit '`, then never ends; and a command stopped at the 2-hour limit writes none either, with no rule for what follows. Confirmed | Fixed: the main session starts `<command>; echo "exit $?" >> <log>`, and a command the limit stops goes to the next helper with its log as stopped at 2 hours |
| 4 | Low | `.claude/workflow/helper.md:31-32` | Axis 1. The paragraph reads a done-criterion of "the carried tests or Tier 2", but the chore's new plans write "the land's push gate", which it did not cover; and "run the test files the item touches" had no bound, against the 4 minutes of BF11. Confirmed | Fixed: it names the land's push gate, and the run keeps within the 4 minutes |
| 5 | Low | `.claude/skills/np-plan/review.md:54-55` | Axis 1, §8.2.13 N3. Self-check 4 now asks every done-criterion to name test files or "the land's push gate", so an item outside the test scope, whose criterion is "the code and review say so" (`wp.md`'s row), fails it, or gets a criterion it should not have. Confirmed | Fixed: the self-check keeps that form |
| 6 | Low | `.claude/skills/np-implement/wp.md:51` | Axis 1. "An item is done when the tests of its done-criterion pass" gave no reading of "the land's push gate" to a session run directly or to a worker, which lands nothing and could run `gate.sh run` per item. Doubt | Fixed: such an item is done when the test files it touches pass, and the land runs the rest |

The pass fixed all six findings in `6290d05`. The hunt reported none, so none is refuted.

## Checked and found true

- **The specification.** §8.4.4 and §8.2.56 BF11 say that a helper waits on nothing over about four minutes and
  hands back a longer command, which the main session runs. Answering a `RUN` that reruns the push gate's tests
  with the land's log serves the command's result without running it twice; the `WAIT` filter, the timeout and the
  done-criterion's form are each below what a clause states. The chore's judgement holds: no clause moves and no
  specification text is due. No clause states a done-criterion's form.
- **The timeout.** 7,200,000 ms is Bash's maximum for a background command, and its default of 1,800,000 ms is
  the 30 minutes that stopped WP6.10's run. A `slow` test of 3,974 s fits; a command over 2 hours is stopped, which
  finding 3 now handles.
- **The `WAIT` filter skips no needed wake.** CI posts no pull-request comment (`ci.yml` and `release.yml` open
  issues only), so a bot's comment carries no CI result; a bot's review still counts as a review; the check-in
  stays scheduled when an event is ignored, so a closed pull request or a conflict still reaches a shipper. It
  agrees with the steward's *Bounded wakes* and with `np-ship/wp.md` §4's "CI results and review comments".
- **The push gate's selection.** `gate.sh run` runs `uv run pytest -q -rsfE -n auto --dist loadfile`, the
  `addopts` selection `(tier1 or tier2) and not slow` without `nightly`, as the new paragraph says; §8.4.4 places
  VER-62's per-push walks in it, so "the nightly VER-62 walks" in the `RUN` row is right.
- **Agreement with the rest.** The core's *Gate and push* (the land in the background, the foreground wait on
  `exit`), `np-ship/wp.md`, the steward skill and the four agents' files say nothing the edits contradict. No
  permission line is added.

## Not assessed

- Whether `subscription.created` is the event's exact name; the statement takes it from WP6.10's session.
- A comment a helper posts through the GitHub tools carries the author's login and so reads as a person's comment;
  the steward's rule that a session's own edit is no new work covers it at the shipper, and the filter makes it no
  worse than before.
