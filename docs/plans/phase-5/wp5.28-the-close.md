# WP5.28 — The close of Phase 5: the registers settled, the end-of-phase report and v0.6.0

**Status: planned, not started.** Written 22 November 2026, grounded in the code at `f853d52` (WP5.27's merge, pull
request 200, tagged `v0.6.0-alpha.27`). Inherits §8.2.47 AW1 to AW11, §8.2.46 AV5 and AV6, §8.2.48
AX1 and AX2 (ruled at this plan) and the test scope (§8.2.13 N1, N3). Its last commit on `main` takes `v0.6.0` alone
(§8.4.1).

The [Phase 5 plan](phase-5-workbench.md)'s WP5.28 entry sets this scope; `SPECIFICATION.md` governs, and where it and
this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** Phase 5 ends and version 0.6.0 is named, the first whose only graphical interface is the browser
workbench. Nothing in the program changes. The phase's final report is measured again on this package's own copy: the
screens the tests load, the checks on three operating systems, a pick's redraw time without a graphics card, and a
fresh install's time and size. About fifty rulings marked as waiting on a delivered package are marked as
landed, and every open item names its owner in the next phase. The changelog gathers the phase's 22 packages and every
change that breaks an older project or script, with its remedy. The install page stops calling the workbench a desktop
shell.

**Cost.** About four sessions, three to six hours of agent work and eight times you act, the merge and the tag among
them, as this phase's text packages measured. A user pays nothing.

**What could go wrong.** The redraw without a graphics card is expected to miss its line (about 300 ms against
200 ms); it is reported, not fixed, since the graphics-card measure is the next phase's. A ruling could be marked
landed while part of it still waits, or a breaking change left out of the changelog; the review reads each changed
line and each package's entry.

**Your call.** Settled on 22 November 2026: the later tool phases are ordered at the next phase's scope round, and the
tree's four reopened points go to its design round. One is left: do you run the Copilot app's checks before you merge?
*Recommendation:* no; the close carries them on, and this release does not depend on them.

## Execution brief

Scope: the Phase 5 plan's WP5.28 entry and criteria 1 to 6 of its *Verification*; §8.4.6's close rule;
`.claude/skills/np-ship/phase.md`'s confirmations. Depends on WP5.27, merged at `f853d52` and tagged
`v0.6.0-alpha.27` there. It claims no new identifier and writes no test (N1, N3). **Implementing session:
Opus, high effort**; item 1 goes to a Sonnet sub-agent. The only API named is the GitHub Actions dispatch of
*Implementation details*, item 3; no library API is new.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The registers** | No `REV-nn` row is `open` (AX2, set in this plan's commit). REV-166 to REV-168, if still `accepted` at item 2, are carried: their ruling cells and `copilot-host.md` name Phase 6's scope round in place of Phase 5's close. Every `accepted` or `deferred` row names its owner, checked by item 2's script; a `declined`, `wontfix` or `post-1.0` row names its ruling. The register's header stays `open`; Phase 5 opened no findings log of its own | §8.4.6; §8.2.46 AV5, AV6; ruled by the author, §8.2.48 AX2 |
| **D2 The rulings a delivered package landed** | In `holds-now.yaml`, each `open:` that names only a delivered Phase 5 package is removed: the line keeps the clause it names, or reads `spent`. T3, AC3 and AW1 keep what still waits. A line that names Phase 6, v1.0 or the Copilot session stays. `decisions.py` rewrites the register | A delivered package can no longer land a ruling (WP60's D1); decided by the plan |
| **D3 The report's numbers** | Each number of the *End-of-phase report* comes from a command run on this package's tree, named beside it: the capability record's counts, the Qt search, VER-78's screens and states, the suite's size, a CI run dispatched on the branch for the three platforms and the self-test (VER-78's screens run in the gate and the pull request's Tier 1 leg, on Linux alone), the headless redraw and the fresh install. A redraw over 200 ms is reported with its split, not fixed | Criteria 1 to 3 and 6; `np-ship/phase.md` ("never copy them from an Outcome"); §8.2.47 AW1 (REV-258); decided by the plan |
| **D4 Each v0.6 requirement checked** | For FR-31 to FR-35, FR-37 to FR-39, IF-09, CON-09, CON-11 and QR-16, a script resolves every test file and test name of the requirement's Appendix A row in `tests/`, and item 3 names the record of each part "verified at review". FR-32 is checked less its tree (v0.7); QR-16 is reported met in part (AW8). A stale name is corrected in Appendix A; a requirement with no check is a `REV-nn` row for the author | Criterion 4; N3; §8.2.47 AW1, AW8; decided by the plan |
| **D5 The release text** | `CHANGELOG.md` gains `## [0.6.0] - <date>` below `[Unreleased]`, which stays empty: a summary, the 22 packages with their tags, *Breaks and their migration* gathering each break since `v0.5.0`, and this package's own changes. `CITATION.cff` names `0.6.0` and the date. README and `docs/overrides/main.html` say `v0.6.0` is released and v0.7 is next; the banner and `docs/getting-started.md` say the browser workbench where they say the desktop shell. §8.1's Phase 5 gate ends "Closed with v0.6.0". The phase plan reads **delivered**; `current.md` points at Phase 6 | The phase plan's WP5.28 entry; `CONTRIBUTING.md`, *Versions and releases*; `release.yml` checks `CITATION.cff`; decided by the plan |
| **D6 The hand-over** | The report lists what Phase 6's scope round receives: the six moved packages (AW1), each open item under its Phase 6 package (AV5), REV-272's five proposals, the tool phases' order (AX1) and the Copilot checks. `current.md` names `/np-plan project` as the next step | REV-272; ruled by the author, §8.2.48 AX1 |

### Grounding

Facts at `f853d52`, with this plan's commit applied.

**D1.**

- `docs/project/review-findings.md`: 276 rows; 207 `fixed`, 38 `accepted`, 17 `deferred`, 7 `declined`, 4 `wontfix`,
  3 `post-1.0`, none `open`. Its front matter reads `status: open`, and §8.4.6 keeps it so.
- REV-166 to REV-168 are `accepted`, ruling `§8.2.25 AA6; §8.2.46 AV6: the Copilot host's session`.
  `docs/plans/sessions/copilot-host.md`'s second paragraph says the author runs them before Phase 5's close and that
  WP5.28 carries any not run. `holds-now.yaml`'s AA6 and AV6 name the session and stay.
- Every `accepted` or `deferred` row's ruling names a Phase 6 package, a tool's phase (REV-67, REV-149, REV-238,
  REV-244), FR-43's package or the Copilot session, except REV-276, which the author ruled "at the radius set's next
  change".
- `docs/project/modularity-findings.md` and `docs/user-testing/findings.md` read `status: closed` since WP60. No file
  under `docs/design/reviews/` carries a `findings:` front matter.
- `validation/findings.py:parse_log` stores `status` as a string; no test reads a row's status.

**D2.**

- `specification/history/holds-now.yaml`: 71 lines hold `open:`. 49 name only delivered packages: S8 to S10, T2, T4,
  U2, U3, U5, U7, Z5, AD3 to AD5, AG6, AH1, AI1, AI9 to AI12, AJ1, AJ2, AJ5 to AJ10, AK3, AL22, AN1, AN3, AN5 to AN7,
  AO1, AQ1, AQ2, AR4, AR8, AS1, AS3, AT1 to AT4, AU1 to AU3. Three are mixed: T3 (the `prepare` command and `upto`
  landed in WP5.16 and WP5.19; FR-28's exports and the composer wait), AC3 (REV-170 is `fixed`) and AW1 (Phase 6's
  scope round waits). The other 19 name Phase 6, v1.0, the Copilot session or `/np-plan phase 6`, AX1 and AX2 among
  them.
- `.claude/scripts/decisions.py:_status_of_ruling` reads an entry that starts `open` as `open`, `spent` as `spent`,
  `superseded by` as `superseded`, an empty one as `unstated`, anything else as `in force`; `gate.sh` runs
  `decisions.py --check`.

**D3.**

- `docs/design/reviews/2026-11-21-qt-capabilities.md`: 41 rows; 31 `present`, 1 `present as ruled (AW7)`, 9
  `carried (REV-274, point n)`, none `missing`.
- `git grep -il "pyside6\|pyinstaller"` outside `docs`, `specification`, `knowledge` and `CHANGELOG.md` prints
  `.gitignore` (the Python template's comment) and `tests/tier1/test_gui_viewmodels.py` (the guard).
- `gui/web/screens.py:SCREENS` holds 32 screens and `gui/web/states.py:STATES` 4 states (`empty`, `charged-tube`,
  `uncharged`, `refused`); `tests/tier1/test_gui_screens.py` collects 149 tests, 128 of them the screen-by-state grid.
- `uv run pytest --collect-only -q`: 1,954 of 2,068 collected (114 deselected); `-m tier1` 1,758, `-m tier2` 220.
- `ci.yml` on `workflow_dispatch` without `full` takes mode `main`: the `platforms` job runs the per-push selection on
  ubuntu, macOS and Windows at Python 3.14, each leg with `nanopnp gui --selftest`; `tests/conftest.py`'s summary
  prints `number stability on` with each walk's drift (VER-62). The dispatch's `ref` is a branch or a tag, not a
  commit.
- The `platforms` legs install no Chromium and leave `NANOPNP_REQUIRE_BROWSER` unset, so
  `tests/tier1/test_gui_screens.py:_launch` skips there and `-rs` lists the skips. Only `gate.sh run` and the pull
  request's `tests (tier1)` job, both on Linux, require a browser (Appendix A's CON-13 row: "VER-78 on ubuntu").
- `.claude/scripts/gui/redraw.cjs <address> --json` times Meso's Charge map after a pick, 20 picks after 3 warm-up
  picks: the markers' paint and the whole repaint, median and p95, with the GPU string. WP5.19 measured 297 / 380 ms
  for the markers' paint on this container's software GL. WP5.02's `measure/` scripts left the tree with the spike.
- `render_shell.py:cached_project` builds the 2WCD project into `<r>/../cache/2wcd-<key>/project`, and
  `filled_cache` walks its study to its charge; `python -m nanopnp.gui.web.server --no-browser --project <folder>`
  prints `nanopnp-gui ready <address>`. `require('playwright')` resolves here.
- Measured at `f853d52`: `uv build --wheel`, then `uv pip install` of `<wheel>[structure,gui]` into a fresh
  `uv venv` took 2.7 s warm; the environment holds 763 MB; its `nanopnp gui --selftest` exits 0 in 5.2 s.

**D4.**

- `specification/a-traceability-matrix.md`: the twelve rows name 17 test files and 13 test names between them; every
  one resolves at `f853d52`. FR-31, FR-33, FR-37 to FR-39 and QR-16 also name parts "verified at review".
- `specification/03-requirements.md`: FR-32's Release reads `v0.6; the tree of results v0.7`; QR-16's NOTE lists the
  keyboard gaps (REV-236, REV-245, REV-266).

**D5.**

- `CHANGELOG.md`: `[Unreleased]` is empty; then `[0.6.0-alpha.27]`, `[0.6.0-alpha.21]` down to `[0.6.0-alpha.2]`
  (which holds WP5.01's entry), then `[0.5.0] - 2026-11-02`. The 21 sections hold 9,361 words in bullets headed
  **Added**, **Changed**, **Removed**, **Fixed** and **Amended**; only three lines say "migration". `[0.5.0]` is the
  model: summary, package list, breaks, the close's own sections.
- `CITATION.cff`: `version: 0.5.0`, `date-released: 2026-11-02`.
- `README.md`: "v0.6 (Phase 5, the graphical interface) is in progress" in *Status and roadmap*, and the roadmap
  row `| v0.6 | 5 | … | **in progress** |`. `docs/overrides/main.html` line 4: "Pre-alpha, v0.5.0 released, v0.6 in
  progress.", and line 5 lists "the desktop shell" as delivered. `docs/index.md`'s warning names v0.7's gate and
  needs no edit. `docs/getting-started.md`: "`gui`, for the desktop shell"; with the banner's, the stale mentions of
  the Qt shell in the user pages.
- §8.1's Phase 4 gate ends "Closed with v0.5.0"; Phase 5's has no such sentence.
- `tag.yml` takes `tag` and `sha` and checks the changelog section; `release.yml` refuses a release whose
  `CITATION.cff` names another version.

**D6.**

- The Phase 5 plan's *Moved to Phase 6* table lists the six packages with their items. REV-272's section lists five
  proposals "for Phase 6's scope round". `.claude/skills/np-plan/project.md`: `/np-plan project` plans again the
  phases after the phase in flight.

### Implementation details

**Item 1** (Sonnet). Edit only the 49 lines D2's grounding lists. On each, delete `open: <package>` and the separator
before it. Then:

- A parenthesis after the package that names a clause, a NOTE, a design-document row or a `REV-nn` row becomes part
  of the hold, joined with `; `. A parenthesis that only cites rulings (`(AD3)`, `(AG1; AJ10)`, `placed by AS1`) is
  dropped.
- A parenthesis that names both keeps its ruling: `AR8: 'FR-31; REV-259; placed by AS1'`.
- Text after the open part that is not a package (`then ADR-004`; `its sequence amended by …`) is kept.
- A line left with nothing reads `spent`.
- Single-quote a value that holds `: `, starts with a quote or a backtick, or holds a `#`; double an inner quote.

Examples: `S8: ADR-004`; `AI9: spent`; `Z5: REV-121`; `AN6: '§5.3.2''s NOTE'`;
`AT1: 'VER-60''s restated NOTE; the design document''s Outline row'`;
`AJ2` drops `(the Physics suite)`. Six lines the rules do not reach take these values, from each ruling's
record: `S9: '§8.4.4; CONTRIBUTING.md'`; `S10: VER-78`;
`T2: 'REV-28, REV-30, REV-32, REV-39, REV-52, REV-62; MOD-13'` (each `fixed`); `AS3: FR-31`;
`AN1: 'the design document''s WB-37; FR-25''s run record'`;
`AN5: '§5.3.2''s NOTE; the Analysis suite''s rebuild (FR-32)'`. AJ10's range ends at this package, which lands it:
`AJ10: '§8.1''s Phase 5 row; the Phase 5 plan; its sequence amended by AL25, AS1 and AW1, its numbers by AL26, AS4
and AW4'`. For each kept clause, confirm it exists: `uv run .claude/scripts/clause.py <ID>` for an
identifier, `grep` for a NOTE or a row. Report each line whose clause you could not find; do not guess. Checks:
`uv run python -c "import yaml,pathlib;yaml.safe_load(pathlib.Path('specification/history/holds-now.yaml').read_text())"`;
then `uv run .claude/scripts/decisions.py`.

Main then sets the three mixed lines:
`T3: 'REV-41, REV-45, REV-67; open: FR-28 (v0.7) and the composer''s phase'`; `AC3: 'REV-170; placed by AD4'`; AW1
ends `open: Phase 6''s scope round`. `grep -c "open:" specification/history/holds-now.yaml` then prints 22: the 19,
T3, AW1 and the header's comment. Main reads the diff of all 52 lines against each ruling's record.

**Item 2.** If REV-166 to REV-168 are still `accepted`: each ruling cell gains `; carried by WP5.28 to Phase 6's
scope round`; each section gains a line **Carried** with the date; `copilot-host.md`'s second paragraph says the
author runs them in Phase 6, placed by its scope round, and the Phase 5 plan's supply row says the close carried
them. If the author ran them, follow the session's own record. The owner script: for each row of
`review-findings.md` whose status is `accepted` or `deferred`, print it unless its ruling matches
`Phase 6|(composer|mutator|sketcher)'s phase|FR-43|Copilot|next change`. It prints nothing.

**Item 3.** In order:

1. Gate and push items 1 and 2. Dispatch CI: `mcp__github__actions_run_trigger`, `run_workflow`, `workflow_id:
   ci.yml`, `ref: <the branch's name>`, no inputs; confirm the run's head is the pushed commit. From each
   `platforms` leg's log (`mcp__github__get_job_logs`) read the passed and skipped counts, the `number stability on`
   section and the self-test's lines. The screens' tests skip on these legs: report VER-78 from `gate.sh run` and
   the pull request's `tests (tier1)` job, and say it ran on Linux alone.
2. The capability counts: `grep -o "| \(present\|carried\)[^|]*|" docs/design/reviews/2026-11-21-qt-capabilities.md
   | sort | uniq -c`. The Qt search: D3's `git grep`.
3. The suite: the three `--collect-only` commands of D3; the screens and states from
   `uv run python -c "from nanopnp.gui.web.screens import SCREENS; from nanopnp.gui.web.states import STATES;
   print(len(SCREENS), len(STATES))"`.
4. The redraw: `uv run python .claude/scripts/gui/render_shell.py --only 2wcd <scratchpad>/render` builds the cache;
   serve `<scratchpad>/cache/2wcd-<key>/project` with D3's server command; `node .claude/scripts/gui/redraw.cjs
   <address> --json`. Report the medians, the p95s, the split and the GPU string, beside WP5.19's.
5. The install: `uv build --wheel --out-dir <scratchpad>/dist`; `uv venv <scratchpad>/venv --python 3.14`; `time uv
   pip install --python <scratchpad>/venv/bin/python "<wheel>[structure,gui]"`, once with `--no-cache` (cold) and once
   into a second fresh environment (warm); `du -sh`; `time <scratchpad>/venv/bin/nanopnp gui --selftest`.
6. D4's script: for each of the twelve rows, every `` `tests/….py` `` exists and every `` `test_…` `` is defined
   under `tests/`. For each "verified at review" part, name its record: the package's Outcome or its file under
   `docs/design/reviews/`.
7. The gate's durations from `.git/nanopnp-gate.log`; the pull request's CI critical path.

Write the report under the Phase 5 plan's `## End-of-phase report`, as the Phase 4 plan's: an opening line that names
the tree and each run, one bullet a subject, then `### Verdicts` with criteria 1 to 6, each `met`, `met in part` (4,
for QR-16) or `not this phase's` (5, 6). Then `### Handed to Phase 6's scope round` per D6: for the open items, group
the register's `accepted` and `deferred` rows by the package their ruling names.

**Item 5.** `[0.6.0]` follows `[0.5.0]`'s layout. The packages: WP5.01 (no tag), WP5.02 to WP5.21 (`alpha.2` to
`alpha.21`), WP5.27 (`alpha.27`), and that WP5.22 to WP5.26 are retired numbers (AW4). A break is a **Changed** or
**Removed** bullet after which a `v0.5.0` case file, project, script, command or stored result stops working or reads
differently: one bullet each, what broke, the migration, `(alpha.N)`. The summary gives the report's counts and links
the Phase 5 plan.

**Item 6.** `current.md`: Phase 5 closed as `v0.6.0`; the next step `/np-ship phase 5`, then `/np-plan project`,
Phase 6's scope round. The phase plan's status: **delivered, <date>; closes at the merge and the `v0.6.0` tag**.

### Work items

- [ ] 1. `specification/history/holds-now.yaml`, `docs/project/decisions.md` (D2); done when the item's checks pass
  and main has read the diff. **Executor:** `general-purpose` on Sonnet, high effort; main for the three mixed lines
- [ ] 2. REV-166 to REV-168 in `docs/project/review-findings.md` and `review-items.md`,
  `docs/plans/sessions/copilot-host.md`, the Phase 5 plan's supply row (D1); done when the owner script prints
  nothing. **Executor:** main
- [ ] 3. The *End-of-phase report*, its verdicts and the hand-over in the Phase 5 plan; Appendix A if a name is stale
  (D3, D4, D6); done when every number names its command or run. **Executor:** main
- [ ] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `CHANGELOG.md`, `CITATION.cff` (D5); done when the strict documentation build passes. **Executor:** main
- [ ] 6. `README.md`, `docs/overrides/main.html` (its version and its desktop shell), `docs/getting-started.md`,
  §8.1's Phase 5 gate, the Phase 5 plan's status and WP5.28 entry, `docs/plans/current.md` (D5, D6); done when the
  strict documentation build and `links.py` pass. **Executor:** main

### Verification

No test is written (N1); the criteria are verified at review (N3).

| Check | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| The restated clauses | 1, 2 | VER-43, VER-44, VER-55, VER-60 | Their tests, unchanged, on three platforms | their clauses | `.claude/hooks/gate.sh run`; the dispatched run |
| The screens | 1 | VER-78 | Its tests, unchanged, in Chromium on Linux; the dispatched legs skip them | its clause | `.claude/hooks/gate.sh run`; the pull request's `tests (tier1)` job |
| The golden | 1, 2 | VER-62 | Each leg's `number stability on` summary | 10⁻⁸ same mesh; the walk's moved tolerance (§7.6 NOTE) | the dispatched run |
| The layering and the backend set | 1 | VER-61, VER-65 | Their tests; the yaml unchanged | exact | `.claude/hooks/gate.sh run` |
| The registers | — | — | No `open` row; the owner script and item 1's checks | exact | review |
| The requirements | — | — | D4's script names no missing file or test | exact | review |
| The documentation | — | VER-45 | The strict build; `links.py` | exact | `CLAUDE.md`'s docs command |

### Out of scope

| Deferred | Owner |
|---|---|
| The tag `v0.6.0` and the GitHub Release | `/np-ship phase 5`, after the merge |
| A redraw over 200 ms; the GPU measure | Phase 6's performance package (REV-258) |
| The six moved packages, the open items, the tool phases' order | Phase 6's scope round (AW1, AV5, AX1) |
| The Phase 5 plan's length; the records' size | Phase 6's cleanup (AW5; REV-271, REV-272) |
| OPN-04, OPN-08; QR-10's trial | The author; v1.0's release candidate (AW2) |

### Open questions

None blocks. The author ruled AX1 and AX2 at this plan. The In brief's *Your call* on the Copilot checks is answered
by what the registers show at item 2 (AV6).
