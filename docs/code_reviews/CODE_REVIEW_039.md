# Code review 039: the written knowledge audit

2026-11-08 · branch `ccr-ffafd419-mwhw6f` from `main` at `a5039af` · scope: the specification bundle, `knowledge/`, the docs tree, `.claude/`, the root entry points; records for reachability only · focus: accuracy, clarity, efficiency, redundancy, organisation · status: in progress

Brief: `docs/plans/kb-audit-brief.md`. The brief names the report 037; 037 and 038 were taken when this session started, so this report is 039 throughout. Every count below was measured on `a5039af` unless it names another commit.

## Status

| Step | Done when | State |
|---|---|---|
| 0 set up | branch, directories and commit recorded here | done |
| 1 baseline | inventory, path costs, every check's output under `raw/` | done: `raw/inventory.md`, `raw/paths.md`, `raw/links.md`, `raw/probes.md` (+ `probes-live-problems.md`), `raw/markers.md`, `raw/clause-check.log`, `raw/clause-check-appendix-a.log`, `raw/duplicates.log`, `raw/build-strict.log` |
| 2 mechanical sweep | every hit a finding or a dismissal | pending: inputs are the step 1 outputs; nothing classified yet |
| 3 reading sweep | every live file a verdict, every record a reachability verdict | returns saved: `raw/reader-{spa,spb,spc,spd,kph,kge,knu,kst,doc,cld}.md` (all ten readers); the orchestrator's own cross-cutting read and the re-run of a sample of each return are pending |
| 4 task walks | each walk a transcript under `raw/` | done: `raw/walks-01-06.md`, `walks-07-12.md`, `walks-13-16.md` |
| 5 decisions register | `decisions.py` runs clean, output attached, proposal written | script written and run (`decisions.md`, `decisions.json` beside this file); proposal pending |
| 6 architecture | survey table, `architecture.py` output, proposal | survey run (`raw/survey/`, `survey.sh`); architecture-document findings are in SPC, DOC and CLD; `architecture.py` and the proposal pending |
| 7 cross-cutting | map, sediment list, proposals with verified scripts | pending |
| 8 safe fixes | gate `exit 0`, pushed, PR open | pending; nothing committed yet (the working tree holds the scripts, this report and `raw/`) |
| 9 report | every finding in one state | pending |

### How to pick this up in a new session (interim)

The state is this file, `raw/` and the scripts under `.claude/scripts/audit/`. Nothing is committed. The
sub-agent returns carry their own finding prefixes (SPA, SPB, SPC, SPD for the specification; KPH, KGE,
KNU, KST for `knowledge/`; DOC for the docs tree; CLD for `.claude/` and the root files); the report
renumbers them `AUD-nn` in order of discovery. Re-run any baseline with `uv run .claude/scripts/audit/<name>.py`
(`links.py --anchors`, `inventory.py`, `probes.py`, `markers.py`, `paths.py`, `decisions.py`) and the
survey with `.claude/scripts/audit/survey.sh`. The thesis clone and the scratch measurements live only
in the session's scratchpad; `raw/` holds what the report needs. Next: step 2 (classify every hit in
`raw/probes-live-problems.md`, `raw/markers.md`, `raw/links.md`, `raw/inventory.md`'s unreached list
and the two `clause-check` logs), then the re-run sample of step 3, then steps 5 to 9.

Scratch directories (session-local, not committed): thesis clone `scratchpad/thesis` (`github.com/willemsk/phdthesis-text`, shallow clone at session start), sub-agent returns `scratchpad/returns` (copied into `CODE_REVIEW_039/raw/`), measurements `scratchpad/measure`.
