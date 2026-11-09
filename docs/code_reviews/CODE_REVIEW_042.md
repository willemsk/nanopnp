# Code review 042: WP5.10, the written knowledge's tools and rules

2026-11-09 · PR #171, branch `ccr-dbee00a1-kqe1yy`, head `aa81101` on base `94c432a` · scope: the PR's diff, read in
full for code (`.claude/scripts/decisions.py`, `index_records.py`, `links.py`, `docs/scripts/architecture.py` and
`generate.py`, `.claude/hooks/checkpoint.sh`, `gate.sh` and `session-start.sh`, `.claude/settings.json`, `justfile`,
`.github/workflows/ci.yml`, `tests/tier1/test_written_architecture.py`) and for the workflow prose it changes; the
moved plans and rewritten paths by sample · focus: correctness of the record scripts and the checkpoint hook,
removed behaviour, the gate's and CI's wiring, the conventions of `CLAUDE.md` and `.claude/rules/python.md` ·
status: completed.

Static review (`/np-ship wp 5.10`, `/code-review xhigh --fix --max-findings all 171`). No gate ran in the review; the
ship turn gates the fixes. Probed by running the scripts: the 311 ruling letters are unique and equal holds-now's
311 keys; the OPN rows' register status matches their Owner column; `just` passes a parameter's default as `$1`
under `set positional-arguments`; `tag.yml`'s and `release.yml`'s changelog greps include the closing bracket, so
`alpha.1` does not match `alpha.10`; `decisions.py --check` takes 0.26 s; the `src/` changes are `noqa` markers only.
After the fixes: ruff and format clean, the three VER-79 tests pass, `links.py` reports 1,432 links, 0 broken and
2 known, and the decisions page re-renders with 1,259 rows (WP5.03's five rows move from *plan in flight* to
*delivered plan*).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `links.py` | Masking code replaced newlines with spaces, so a broken link after a fenced block was reported on the wrong line | Fixed: the mask keeps newlines |
| 2 | Medium | `checkpoint.sh` | `save` printed `on` without jq, while hook mode needs jq and exits silently without it: the session would go on past a checkpoint with no Stop guard and no prompt across the compaction | Fixed: without jq the switch is off |
| 3 | Medium | `checkpoint.sh` | A saved checkpoint outlives the switch; its Stop hook blocks every later turn end on the branch, and nothing named the way out | Fixed: the Stop reason and the post-compaction line say to run `checkpoint.sh clear` when the switch is not 1; `CLAUDE.md` names `clear` |
| 4 | Medium | `decisions.py` `plans()` | Only `delivered` in a plan's head marked it done: WP5.03, `merged`, was listed in flight | Fixed: delivered, merged, implemented or closed |
| 5 | Medium | VER-79 holds-now test | Sets hid a ruling letter used twice in the history and a key repeated in `holds-now.yaml`, which YAML keeps silently | Fixed: both asserted unique |
| 6 | Medium | `np-plan/rulings.md` | The holds-now line `<id>: open: <package>` is invalid YAML unquoted; the next ruling round would break the commit gate with a traceback | Fixed: the rule says to single-quote a value holding `: `, with the file's own example |
| 7 | Low | `justfile` `gmsh-libs` | No `apt-get update` fallback, unlike the session hook: fails in a fresh container | Fixed: install, else update and install |
| 8 | Low | `CLAUDE.md` | The commit and push gate paragraphs omitted the decisions page check `gate.sh` now runs | Fixed |
| 9 | Low | `decisions.py` `open_items()` | An OPN row was closed when "closed" appeared anywhere in it | Fixed: read from its Owner column; the page is unchanged |
| 10 | Low | `decisions.py` `orientation()` | `next(glob(...))` took the rulings file in filesystem order | Fixed: `min(...)` |
| 11 | Low | `decisions.py` `plans()` | A delivered plan's rows carry its delivery date, not the date its decisions were taken | Not fixed: the page dates a plan by its head; the headers do not name the planning date in one form |
| 12 | Low | `session-start.sh` | Without `timeout` (stock macOS) the payload read is unbounded | Not fixed: Claude Code closes the hook's stdin; bash has no portable bounded read |
| 13 | Low | `checkpoint.sh` PreCompact | The prompt is not capped at the host's 10,000 characters | Not fixed: prompts run to about 3,000; a cut would drop the resume line |
| 14 | Low | `generate.py` | The docstring said six kinds of file and left out the architecture page | Fixed |
| 15 | Low | `justfile` `lint` | "As the gate runs them" overstated: the gate adds the lock and decisions checks | Fixed |
| 16 | Low | VER-79 decisions test | Re-implemented `decisions.py --check` | Fixed: calls `decisions.main(["--check"])` |
| 17 | Low | `decisions.py` `_escape` | The escaping expression was written twice | Fixed |
| 18 | Low | `index_records.py` | Read each index back to count its lines | Fixed |
