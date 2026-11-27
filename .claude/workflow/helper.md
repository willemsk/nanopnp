# A helper of `/np-carry`

`/np-carry` started you for one step (§8.4.4). Follow the level's files, but for these:

| Where a level's file says | A helper |
|---|---|
| ask the author | hands back `ASK` |
| give an item or a read to an agent | hands back `WORKER` |
| run `/code-review`, start `np-reviewer` | hands back `REVIEW`, the main session running the hunt |
| wait for CI, schedule a check-in | hands back `WAIT` |
| gate and push, run `just land` | commits, and hands back with `land: yes` |
| run a command that takes over about 4 minutes and that the push gate does not run: the nightly VER-62 walks, a benchmark, a sweep, `pytest --nightly`, a `slow` test the plan names | hands back `RUN` |
| run `usage.py` or `checkpoint.sh`, subscribe to a PR or unsubscribe, cancel a check-in, use a task tool it lacks | skips it |
| print a prompt, pause, report, end the turn | hands back `DONE` |

Make your first change with an edit tool, not a shell command (§8.2.50 AZ17).

**Every hand-back ends you.** No helper is resumed: the answer starts a fresh helper of your agent,
which reads your hand-off note and goes on (§8.2.56 BF2). Write the note so that it needs nothing
else of this session.

**You never wait on the push gate** (§8.2.56 BF11). A helper runs on the 5-minute prompt cache and
the main session on the 1-hour one, and the push gate takes about 8 minutes: a helper that waits on
it comes back to an expired cache and writes its whole context again. So wait in the foreground on
nothing longer than about 4 minutes. Commit under the commit hook, which stays, and hand back: the
main session lands your commits before it serves the hand-back. Where a level's file opens or
updates the PR after a push, do it before the hand-back if `origin/<head>` exists, as the land
brings the PR to your commits; if it does not, the next helper does it.

**The land is the Tier 1–2 check.** The push gate runs `uv run pytest`, the default selection of
Tiers 1 and 2, on every land. Where an item's done-criterion names the land's push gate, the carried
tests or Tier 2, run in the foreground only the test files the item touches, within the 4 minutes
above, commit, and hand back with `land: yes`: the land runs the rest. Never hand back a `RUN` of a
marker selection such as `-m tier2`, or of the carried tests, nor one with `--slow` or `--nightly`,
which add tests that run for hours. A `RUN` names its tests by file or node id.

## The hand-off note

Before each hand-back, write `docs/plans/phase-<p>/wp<n>-handoff.md`, overwriting the last one, and
commit it as `docs: WP<n> hand-off, <step>` with the step's work; the main session lands it. The
ship's `WAIT` and `DONE` write none: a push would start CI again, and `np-ship/wp.md` §0 resumes from
the PR. The ship deletes the note in its commit after the review. At most 600 words, in these
sections:

- **Step**: plan, implement or ship, and where in it.
- **Done**: the commits of this step, by short sha and subject.
- **Measured**: numbers only, each with what it measures.
- **Decided**: what this step settled that no plan or record holds yet, the author's answers
  included.
- **Open**: the questions handed back, verbatim.
- **Next**: the exact first action of the helper that follows, with its file and its command.

The plan, the ticks and the records hold what they hold; the note does not repeat them.

## The hand-back

A hand-back is your last message:

```text
HANDBACK <kind>
step: <plan | implement | ship>
note: <the note's path, or none>
land: <yes | no | lease <sha>>
<body>
```

`land:` is `yes` where you committed since the branch's last push, `lease <sha>` where you rewrote
the branch on `main` (the core's *Gate and push*, step 7, with the sha last pushed), and `no`
otherwise. The main session runs `just land` on any but `no` before it serves the hand-back, and the
prompt of the helper after it ends with the land's last line, `land: pushed <sha>`: the branch is
pushed at that sha, its `HEAD`.

- `ASK`: the round's brief, then a fenced JSON array of at most three questions in
  `AskUserQuestion`'s shape, as `.claude/workflow/author.md` writes them.
- `WORKER`: `agent: <type>`, `model: <name>` (none for a project agent, whose file sets it), then the
  worker's whole prompt.
- `REVIEW`: `agent: np-reviewer`, `effort: medium` for the review of a finding the author pulled in
  (§8.2.56 BF8) or of a small finding fixed after the review (§8.2.58 BH1), then the reviewer's whole
  prompt. A full review's prompt ends `The hunt's findings: <to be added>`: the main session runs the
  `/code-review` hunt, fills it in and passes the findings back with the reply (§8.2.61 BK1). A
  second start of the same review writes them in, so that the hunt does not run again; a review at
  medium effort has no such line.
- `WAIT`: `pr: <number>` and the steward's check-in delay.
- `RUN`: the command, with its output sent to a log under `<git dir>`; it writes no tracked file.
  The main session runs it in the background, waits, and gives the next helper the log's path.
- `DONE`: the PR, the head's sha and what no record holds, in 200 words; the manager's summary and
  the ship's report whole.
- `BLOCKED`: the reason, whether the tree is clean, and the command that continues.
