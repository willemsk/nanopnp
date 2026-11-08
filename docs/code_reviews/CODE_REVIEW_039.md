# Code review 039: the written knowledge audit

2026-11-08 · branch `ccr-ffafd419-mwhw6f` from `main` at `a5039af` · scope: the specification bundle, `knowledge/`, the docs tree, `.claude/`, the root entry points; records for reachability only · focus: accuracy, clarity, efficiency, redundancy, organisation · status: in progress (steps 0 to 4 done; 5 to 9 pending)

Brief: `docs/plans/kb-audit-brief.md`. The brief names the report 037; 037 and 038 were taken when this session started, so this report is 039 throughout. Every count below was measured on `a5039af` unless it names another commit.

## Status

| Step | Done when | State |
|---|---|---|
| 0 set up | branch, directories and commit recorded here | done |
| 1 baseline | inventory, path costs, every check's output under `raw/` | done: `raw/inventory.md`, `raw/paths.md`, `raw/links.md`, `raw/probes.md` (+ `probes-live-problems.md`), `raw/markers.md`, `raw/clause-check.log`, `raw/clause-check-appendix-a.log`, `raw/duplicates.log`, `raw/build-strict.log` |
| 2 mechanical sweep | every hit a finding or a dismissal | done: `raw/own-findings.md` (ORC-01 to ORC-15, WLK-01 to WLK-15), `raw/own-dismissals.md`; the two probe scripts corrected (`markers.py` reads `Class::method` ids, `probes.py` reads annotated `Dn` cells) and re-run at b602e60 |
| 3 reading sweep | every live file a verdict, every record a reachability verdict | done: the ten returns under `raw/reader-*.md`; the orchestrator's own read of §8.4, `knowledge/index.md`, `00-orientation/`, `log.md`, `history/index.md`, `current.md` is in `own-findings.md`; about forty reader verdicts re-checked against the tree (the `fix:` rows of `raw/dispositions.tsv` were each verified) |
| 4 task walks | each walk a transcript under `raw/` | done: `raw/walks-01-06.md`, `walks-07-12.md`, `walks-13-16.md`; their stalls are WLK-01 to WLK-15 |
| 5 decisions register | `decisions.py` runs clean, output attached, proposal written | script written and run (`decisions.md`, `decisions.json` beside this file); proposal pending |
| 6 architecture | survey table, `architecture.py` output, proposal | survey run (`raw/survey/`, `survey.sh`); architecture-document findings are in SPC, DOC and CLD; `architecture.py` and the proposal pending |
| 7 cross-cutting | map, sediment list, proposals with verified scripts | pending |
| 8 safe fixes | gate `exit 0`, pushed, PR open | pending; the verified edit list is `raw/step8-fixes.md` |
| 9 report | every finding in one state | pending; `register.py` (to write) merges `raw/reader-*.md`, `raw/own-findings.md` and `raw/dispositions.tsv` into the `AUD-nn` table |

### How to pick this up in a new session (interim)

The state is this file, `raw/` and the scripts under `.claude/scripts/audit/`, all committed and pushed on
`ccr-ffafd419-mwhw6f`. Finding prefixes: SPA, SPB, SPC, SPD (specification readers), KPH, KGE, KNU, KST
(`knowledge/` readers), DOC (docs tree), CLD (`.claude/` and the root files), ORC (the orchestrator's own),
WLK (the task walks). The report numbers them `AUD-nn` in the order ORC, SPA, SPB, SPC, SPD, KGE, KNU, DOC,
CLD, KST, KPH, WLK; `raw/dispositions.tsv` gives each reader finding its state (`fix:<category>`, `your call`,
`dismissed <reason>`), unlisted ids being `your call`. Re-run any baseline with `uv run .claude/scripts/audit/<name>.py`
(`links.py --anchors`, `inventory.py`, `probes.py`, `markers.py`, `paths.py`, `decisions.py`) and the survey with
`.claude/scripts/audit/survey.sh`. The thesis clone lives only in the session's scratchpad (`scratchpad/thesis`,
a shallow clone of `github.com/willemsk/phdthesis-text`; re-clone it into an empty scratch directory if a
thesis check is needed).

Next, in order:

1. Write `.claude/scripts/audit/register.py`: read the `| XXX-nn |` rows of `raw/reader-*.md` and `raw/own-findings.md`
   (split cells on unescaped `|`), apply `raw/dispositions.tsv` (`extra_where` appends to *Where*; a `fix:` row
   becomes `fixed <sha>` from `raw/commits.tsv`), number `AUD-nn` in the order above, and write
   `CODE_REVIEW_039/findings.md`: the source-to-AUD map, the findings by axis (accuracy, clarity, efficiency,
   redundancy, organisation) ranked high, medium, low, and the dismissed table (reader rows plus
   `raw/own-dismissals.md`).
2. Step 8: apply `raw/step8-fixes.md`, one commit per category, then the checks it lists.
3. Step 5: the register proposal (home, shape, what counts, relation to the history index's *Where each ruling
   holds now*, the one maintenance rule); note the 474 `D` rows the plans' tables hold against 624 `WPn Dm`
   citations.
4. Step 6: read `raw/survey/*.txt` and `pypi.json`, build the survey table (recommend at most two, adopt none);
   write read-only `architecture.py` (per subpackage: modules and first docstring lines, public names, lines,
   stages implemented, measured import edges in and out; the diff of §5.1's table against the tree) and run it
   to `CODE_REVIEW_039/architecture.md`.
5. Step 7: the redundancy map (the reader rows on the redundancy axis, each with its home), the sediment list,
   and the structural proposals with a `migrate_<name>.py` each, run on a scratch branch and verified
   (`links.py`, `clause.py`, `duplicates.py`, the strict build), the branch then deleted: an index for
   `docs/plans/`, an index for `docs/code_reviews/`, an index for `docs/design/reviews/`, and the folder moves.
6. Gate, push, open the PR (`docs: audit of the written knowledge (CODE_REVIEW_039)`); then step 9, the report in
   the house shape, with `findings.md` and `architecture.md` as attachments.

Scratch directories (session-local, not committed): thesis clone `scratchpad/thesis` (`github.com/willemsk/phdthesis-text`, shallow clone at session start), sub-agent returns `scratchpad/returns` (copied into `CODE_REVIEW_039/raw/`), measurements `scratchpad/measure`.
