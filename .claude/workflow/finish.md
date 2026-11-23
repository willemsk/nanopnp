# Finishing a level

The core's last section sends a session here before it opens or updates a pull request or writes a
level's report (`core.md`; §8.4.4).

## The author's page

*The In brief*, the section a plan and a pull request start with, and *Putting a choice to the author*
are in `author.md` beside this file (§8.2.33 AI7). Read it at a step that writes an In brief or puts
a choice to the author.

## The PR contract

Open or reuse the branch's PR against `main` without asking. Reuse one only after you verify its
repository, its exact head and its base `main`. Keep human edits and review evidence. If you cannot
create the PR, report the blocker and the pushed branch.

Titles: `feat: WP<n> — <what it delivers>`, or `fix:` for a package that fixes findings. A plan
level's PR takes its commit's subject.

The body starts with `## In brief` (`author.md`). It then fills in `.github/pull_request_template.md`, and ticks the
Verification checklist only for what ran. Give numbers, not adjectives: rates with their meshes, route
agreement, timings, each with its stabilisation mode. Never omit "Specification changes"; "None." is
an answer. Link derivations and tables; do not copy them. End with this session's attribution footer.
On a reused PR, bring the body to the tree's current state. If the review changes an author's
decision, update the In brief.

## Report and stop

Each level ends with the report its file names, then stops. `/np-implement` pauses after its report
for a compaction; `/np-ship` then runs in that session or a fresh one, and a finding against a decision
the implementing session took goes to the author (§8.2.33 AI4). A level of `/np-plan` pauses after its report for a compaction,
and `/np-plan <level> [n] review` then reviews the plan and summarises it for approval
(`np-plan/review.md`).

Each report, and each pause for a compaction, ends with the line that
`uv run .claude/scripts/usage.py --label <level>` prints: the session's cost since the level's command,
in §8.3's units, with its tokens by model. The PR's **Measured** section gains the line (§8.4.5;
§8.2.37 AM11).
