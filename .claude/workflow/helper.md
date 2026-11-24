# A helper of `/np-carry`

`/np-carry` started you for one step (§8.4.4). Follow the level's files, but for these:

| Where a level's file says | A helper |
|---|---|
| ask the author | hands back `ASK` |
| give an item or a read to an agent | hands back `WORKER` |
| call the `code-review` skill | hands back `REVIEW` |
| wait for CI, schedule a check-in | hands back `WAIT` |
| run `usage.py` or `checkpoint.sh`, subscribe to a PR or unsubscribe, cancel a check-in, use a task tool it lacks | skips it |
| print a prompt, pause, report, end the turn | hands back `DONE` |

Make your first change with an edit tool, not a shell command (§8.2.50 AZ17). A resume brings the
answer: go on.

A hand-back is your last message:

```text
HANDBACK <kind>
step: <plan | plan-review | implement | ship>
next: <item k, or the step that follows>
<body>
```

- `ASK`: the round's brief, then a fenced JSON array of at most three questions in
  `AskUserQuestion`'s shape, as `.claude/workflow/author.md` writes them.
- `WORKER`: `agent: <type>`, `model: <name>`, then the worker's whole prompt.
- `REVIEW`: `args: <the skill's arguments>`.
- `WAIT`: `pr: <number>` and the steward's check-in delay.
- `DONE`: the PR, the head's sha and what no record holds, in 200 words; the manager's summary and
  the ship's report whole.
- `BLOCKED`: the reason, whether the tree is clean and pushed, and the command that continues.
