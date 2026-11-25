# A helper of `/np-carry`

`/np-carry` started you for one step (§8.4.4). Follow the level's files, but for these:

| Where a level's file says | A helper |
|---|---|
| ask the author | hands back `ASK` |
| give an item or a read to an agent | hands back `WORKER` |
| start `np-reviewer` | hands back `REVIEW` |
| wait for CI, schedule a check-in | hands back `WAIT` |
| run `usage.py` or `checkpoint.sh`, subscribe to a PR or unsubscribe, cancel a check-in, use a task tool it lacks | skips it |
| print a prompt, pause, report, end the turn | hands back `DONE` |

Make your first change with an edit tool, not a shell command (§8.2.50 AZ17).

**Every hand-back ends you.** No helper is resumed: the answer starts a fresh helper of your agent,
which reads your hand-off note and goes on (§8.2.56 BF2). Write the note so that it needs nothing
else of this session.

## The hand-off note

Before each hand-back, write `docs/plans/phase-<p>/wp<n>-handoff.md`, overwriting the last one, and
commit it as `docs: WP<n> hand-off, <step>` with the step's work; then gate and push as the core
says. The ship's `WAIT` and `DONE` write none: a push would start CI again, and `np-ship/wp.md` §0
resumes from the PR. The ship deletes the note in its commit after the review. At most 600 words, in
these sections:

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
<body>
```

- `ASK`: the round's brief, then a fenced JSON array of at most three questions in
  `AskUserQuestion`'s shape, as `.claude/workflow/author.md` writes them.
- `WORKER`: `agent: <type>`, `model: <name>` (none for a project agent, whose file sets it), then the
  worker's whole prompt.
- `REVIEW`: `agent: np-reviewer`, `effort: medium` for the review of a finding the author pulled in
  (§8.2.56 BF8), then the reviewer's whole prompt.
- `WAIT`: `pr: <number>` and the steward's check-in delay.
- `DONE`: the PR, the head's sha and what no record holds, in 200 words; the manager's summary and
  the ship's report whole.
- `BLOCKED`: the reason, whether the tree is clean and pushed, and the command that continues.
