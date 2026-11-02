# WP60 — Phase 4 closed: the open items resolved, and the end-of-phase report

**Status: delivered, 2 November 2026.** Written 2 November 2026, grounded in the code at `a800a45` (WP59 merged, tagged
`v0.5.0-alpha.25`; CI run 41446908606 green). Inherits §8.2.24 Z1 and Z3, §8.2.27 AC1 and AC6, §8.2.29 AE5 (ruled at
this plan) and the test scope (§8.2.13 N1, N3). Its last commit on `main` takes `v0.5.0` alone (§8.4.1).

The [Phase 4 plan](phase-4-polish-and-user-testing.md)'s WP60 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

This package ends Phase 4 and names the release that the browser workbench builds on.

**What changes.** Every finding of the phase is read and marked settled. The record of what the program costs to run
is measured again with a corrected tool, because the old record came from a tool that undercounted. Every number of
the phase's final report is measured again on this package's own copy of the program, never copied from earlier
notes. The instructions that the coding sessions read are rewritten in plainer, shorter sentences, each rule stated
once, with no rule lost. The changelog gathers every change of the phase that breaks an old case file or script,
with what to do about it. The front page and citation file name the release.

**Cost.** Three to four days, mostly waiting on measurements: about fifteen minutes for the cost record, ten
for the checks on three operating systems, and the usual checks before each push. No result moves.

**What could go wrong.** A rewritten instruction could drop a rule; a script compares every number, identifier,
command and path before and after; the review reads the rest. A cost could come out over its limit; it is
reported to you, not fixed here, since the rule is to measure before fixing.

**Your call.** Should the plain-language pass also cover the review-steward instructions and the Copilot tool map?
*Recommendation:* no; your ruling named the project instructions and the three commands, and those two files are
reference tables.

## Execution brief

Scope: the Phase 4 plan's WP60 entry; criteria 1 to 14 of its *Verification*; REV-47 and REV-116; AC6. Depends on
WP59, merged at `a800a45`. It claims no new identifier and writes no test (N1, N3); VER-61, VER-62 and VER-65 stay
green on the three platforms. **Implementing session: Sonnet, high effort.** The prose pass stays in the main
session; the history index goes to a Haiku sub-agent. One library API is named, the GitHub Actions dispatch of
*Implementation details* item 6; no library API is new.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The registers close** | Both findings logs take `status: closed`. REV-116 and REV-47 are set `fixed` (items 2, 6); no `REV-nn` row is `open`, the register's header stays `open`. In `specification/history/index.md`, each ruling line whose `open:` names a delivered Phase 4 package (WP54 to WP60, WP57's plan) keeps its clause, or reads `spent` if it names none; H2 reads `spent`. The *Open decisions* rows still open are carried: OPN-04 and OPN-08 to the author, NUM-07 to Phase 6; no residual cycle, drift or cost over threshold was reported (H6, I4, M2) | Criteria 2, 5, 10; H12; §8.2.9 I3 for REV-47. A delivered package can no longer land a ruling, so an `open:` naming one is stale (Z3) |
| **D2 The cost record re-run** | `validation/costs.py`'s quick-start leg walks the shipped quick-start case, meshed by stage 6, instead of calling the removed `nanopnp mesh cylinder`. `python -m nanopnp.validation.costs all` runs on a committed, clean tree (`dirty: false`) and replaces `docs/project/cost-study.json`. A share over its threshold is reported as a `REV-nn` row for the author, never fixed here and never re-thresholded | REV-116 (ruled 18 October 2026); M2; WP49's thresholds 4 GB, 5 %, 10 % |
| **D3 The report's numbers** | Each number of *End-of-phase report* comes from a command run on WP60's tree, named beside it: the prose share and the markers from the scripts of item 6; the layering from `render_measurements` and VER-61's test; the platforms from a CI run dispatched on the branch head; the suite from `pytest --collect-only`; the loop's timings from the gate log and the PR's CI run. The before-matrix is WP35's, read from `docs/project/modularity.md`. The source's prose share is accepted as measured (AE5) | Criteria 4, 11; Z1; N3 ("Phase 4's criteria that read a withdrawn check are verified by the close at review") |
| **D4 The workflow prose** | `CLAUDE.md`, `.claude/workflow/core.md` and every file of `np-plan`, `np-implement`, `np-ship` and `np-gui` are rewritten in short, active, present-tense sentences (Simplified Technical English). A rule repeated across them is stated in its owner, and the others point to it: `CLAUDE.md` owns setup, commands, the gate procedure, testing, provenance, prose, git and the prohibitions; `core.md` owns what every level shares; a level file owns its level. No rule changes meaning, no cap or number is lost, and every heading another file cites keeps its name. §8.4 changes only where it cites a file for a rule that moved. `steward/SKILL.md` and `hosts/copilot.md` are out | AC6; §8.4.4 |
| **D5 The release text** | `CHANGELOG.md` gains `## [0.5.0] - <date>` above `[0.5.0-alpha.25]` and below `[Unreleased]`, which keeps WP5.01's entry (§8.4.1): a summary, the 26 packages with their tags, *Breaks and their migration* gathering each break of alpha.1 to alpha.25, and WP60's own Added, Changed and Fixed. `CITATION.cff` names `0.5.0` and the date. README, `docs/index.md` and `docs/overrides/main.html` say `v0.5.0` is released and v0.6 is in progress. The phase plan reads **closed**; `current.md` points at Phase 5 | Criterion 8; Z3; F5; `release.yml` checks `CITATION.cff`'s version |

### Grounding

Facts at `a800a45`.

**D1.**

- `docs/project/modularity-findings.md`: front matter `status: open`; 18 rows, all terminal: 13 `fixed`, MOD-08 and
  MOD-17 `post-1.0`, MOD-09 and MOD-10 `deferred`, MOD-18 `wontfix`.
- `docs/user-testing/findings.md`: `status: open`; 12 rows, 11 `fixed`, UT-09 `deferred` (REV-156).
- `docs/project/review-findings.md`: 173 rows; 127 `fixed`, 20 `deferred`, 12 `accepted`, 7 `declined`, 4 `wontfix`,
  2 `post-1.0`, 1 `open` (REV-116). Of the accepted, REV-135 to REV-139, REV-141 and REV-143 are Phase 5's (§8.2.19),
  REV-166 to REV-168 the Copilot probes (AA6), REV-170 the Geometry tool's (AD4); REV-47's section names "Phase 4's
  close package", which reports the gate's durations and "re-argues or retires WP33's targets" (180 s gated, 90 s per
  file). Neither target is in the specification: §7.6's NOTE on the loop's timings replaced them.
- `validation/findings.py:parse_log` stores `status` as a string and checks only the three keys; `test_layering.py`
  reads rows, not the status. `closed` parses unchanged.
- `specification/history/index.md`, *Where each ruling holds now*: 45 lines carry `open:` naming WP54 to WP60 or
  WP57's plan (V1 to V12, W1 to W8, X1 to X8, Y1 to Y11, Z1 to Z4, AC1, AC2, AC5, AC6, AE1 to AE3), and H2 names "the
  user-testing sessions rule `MOD-11`", fixed by Y5. Lines naming Phase 5, Phase 6 or a Copilot session stay.

**D2.**

- `validation/costs.py:_quickstart_case` runs `[_nanopnp(), "mesh", "cylinder", "--out", "pore.msh"]` and substitutes
  `inputs.mesh.path`. Since WP57 `nanopnp mesh` takes a geometry file or `reference`, and
  `examples/01-quickstart/quickstart.case.yaml` declares `geometry.pore` and `numerics.mesh` and names no file: the
  leg fails, and a supplied mesh beside `numerics.mesh` is refused. `_nanopnp` has no other caller.
- `_charged_case` prepares 2WCD with `examples/06-pdb-to-mesh/prepare.py` from `tests/data/structures/2wcd.pdb.gz` and
  substitutes `structure.source.path` in example 07's case, its only path. Every name of `A8_BUILD`, `A16_WRITES` and
  `A16_READS` still resolves through `costs.resolve`.
- `_walk` runs `Session(store, write=False).run(Case.load(case))`, the store in the scratch directory, so nothing is
  written beside a case. `environment_record` records `commit` and `dirty`.
- The record at `4deb53e`: A1 1.14 GB projected at 1,000 frames; A8 0.33 % (quick-start) and 0.017 % (2WCD); A16 0.10 % and 0.51 %;
  2WCD stage 10 213 s, wall 298 s; four CPUs, threads unset. No test imports `validation.costs`.

**D3.**

- No prose-share function survives in `src/`; WP45 D4 defines the share as docstring lines plus non-directive comment
  lines over physical lines. Measured by item 6's script at `a800a45`: `src/nanopnp` 11.88 %, `tests/` 2.75 %; `api/`
  20.3 % is the highest subpackage. AE5 accepts the source's share as measured.
- `knowledge/`: 442 `[tested: …]` spans; three are the format's `<test>` placeholder and one the log's `…`; the other
  438 name 315 distinct tests, every one present. 120 `[verified]` markers.
- `validation/modularity.py:render_measurements()` returns the import matrices, components and backend set as
  Markdown (182 lines); `tests/tier1/test_layering.py` and `test_backend_guard.py` are VER-61 and VER-65.
- `tests/conftest.py:pytest_terminal_summary` prints `number stability on <environment>` and each walk's largest
  relative drift; each CI leg's log carries it. `ci.yml` on `workflow_dispatch` without `full` runs the `platforms`
  job (ubuntu, macOS, Windows; Python 3.14; the per-push selection).
- `uv run pytest --collect-only -q`: 1,652 of 1,764 collected (112 deselected); `-m tier1` 1,460, `-m tier2` 216.
  `gate.sh` appends seconds per run to `.git/nanopnp-gate.log`. `tests/tier2/test_notebooks.py` is `nightly` and runs
  when named.

**D4.**

- Words: `CLAUDE.md` 1,835; `core.md` 1,077; `np-plan` 3,995; `np-implement` 983; `np-ship` 1,760; `np-gui` 1,201.
- Repeated rules: the plan caps in `CLAUDE.md` and `np-plan/wp.md` (twice); models in `CLAUDE.md`, `core.md` and
  `np-plan/wp.md`; the gate procedure in `CLAUDE.md`, `core.md` and `np-ship/wp.md`; "plans before WP53" in
  `CLAUDE.md` and `core.md`; open items in `CLAUDE.md`, `core.md` and five level files; the drop commit in
  `CLAUDE.md` and `np-ship/wp.md`.
- Cited headings: in `CLAUDE.md`, *Setup*, *Commands*, *Testing*, *Implementation workflow*, *Models*, *Open items*,
  *Prose in code*, *Durable learnings*, *Do NOT*, *Provenance* (by `.claude/`, `.github/`, `CONTRIBUTING.md`,
  `knowledge/` and the hooks); in `core.md`, *The package's PR and branch*, *Two lanes*, *Models and executors*,
  *Records*, *Gate and push*.
- §8.4.4 cites `CLAUDE.md` for the fresh-session rule and §8.4.6 for the review reports' numbering.

**D5.**

- `CHANGELOG.md`: `[Unreleased]` (WP5.01, the Copilot host), then `[0.5.0-alpha.25]` to `[0.5.0-alpha.1]`, alpha.N
  being WP(34+N). 19 lines mark a break or a migration, plus alpha.23's *Each break, with its migration* list and
  alpha.8's *Migrating a case file to nanopnp/case/v0.5*. `[0.4.0]` is the model: summary, package list, then the
  close's own sections.
- `CITATION.cff`: `version: 0.4.0`, `date-released: 2026-10-04`.
- "not yet tagged" or "in progress": `README.md` lines 57 and 67, `docs/index.md`'s warning, `docs/overrides/main.html`
  line 4.

### Implementation details

**Item 1.** `_quickstart_case(repository, directory)` returns `dump_case(read_case(repository / QUICKSTART_CASE),
directory / "quickstart.case.yaml")`; delete `_nanopnp`, which has no other caller. Check:
`uv run python -m nanopnp.validation.costs walks --out <scratchpad>/walks.json` exits 0.

**Item 2.** `git status --porcelain` empty, `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` unset, then
`uv run python -m nanopnp.validation.costs all`; confirm `"dirty": false` in every environment block, commit the JSON.
REV-116's row `fixed`, ruling `[WP60](../plans/wp60-phase-4-close.md)`; its section ends **Fixed in WP60:** with the
three shares, their thresholds and the commit.

**Item 3.** Each log's front matter `status: closed`, and one sentence after its first paragraph: "Closed on <date> by
WP60: every row is terminal." In the history index, for each line of D1's grounding: remove `; open: <package>`; a
line left with no clause, or reading only `open: …`, becomes `<id> - spent`; H2 becomes `H2 - spent`; W4 becomes
`W4 - spent; its \`Case.run\` clause superseded by Y4`. Leave Z1 and AC6 for item 7. Check:
`grep -nE "open: (WP5[4-9]|WP57's plan)" specification/history/index.md` prints nothing.

**Item 4.** Before editing, write the old files to `<scratchpad>/prose-before/`. After, run:

```bash
uv run python <scratchpad>/tokens.py <scratchpad>/prose-before CLAUDE.md .claude/workflow/core.md .claude/skills/np-plan .claude/skills/np-implement .claude/skills/np-ship .claude/skills/np-gui
```

where `tokens.py` collects from each side the set of identifiers (`§\d[\d.]*`, `[A-Z]{2,4}-\d+`, ruling ids
`[A-Z]{1,2}\d+`), numbers (`\d[\d,.]*`), backticked spans and `*heading*` citations, and prints old minus new. Each
printed token is restored or named in the commit body as a removed duplicate with its owner. Then
`grep -rn -F "*<heading>*"` for each cited heading of D4. Record word counts before and after in the plan's Outcome.

**Item 6.** Prose share: `ast` string-expression statements (every line they span) ∪ full-line comments that
`tokenize` yields, minus directives (`#!`, a coding line, `noqa`, `type:`, `pragma`, `fmt:`), over physical lines,
for `src/nanopnp` and `tests`. Markers: every `[tested: X]` in `knowledge/`, split on `;` and `,`, each `path::name`
present as a file with that function or class. Platforms: `mcp__github__actions_run_trigger` `run_workflow`,
`workflow_id: ci.yml`, `ref: <head>`, no inputs; read each `platforms` job's log (`mcp__github__get_job_logs`) for
its `number stability on` section and VER-61's and VER-65's results. Notebooks: `uv run pytest
tests/tier2/test_notebooks.py -n 4 --durations=0`. The PR's critical path: first job start to last job end of its
latest CI run. The commit hook: the gate log's line for item 6's commit. REV-47 `fixed`: WP33's targets retired,
superseded by §7.6's NOTE on the loop's timings, with the three measured timings.

**Item 7.** `[0.5.0]` per D5; each break one bullet: what broke, the migration, and `(alpha.N)`. Z1 and AC6 read
`spent` in the index.

### Work items

- [x] 1. db952e3 `src/nanopnp/validation/costs.py`: the quick-start leg on the shipped case (D2); done when the `walks` leg
  exits 0 and the code and review say so. **Executor:** main
- [x] 2. d9f34f2 `docs/project/cost-study.json`, REV-116 in `docs/project/review-findings.md` and `review-items.md` (D2); done
  when the record shows `dirty: false` on every leg and each verdict is stated. **Executor:** main
- [x] 3. 021251c Both findings logs' headers; `specification/history/index.md`'s stale `open:` markers (D1); done when the
  item's `grep` prints nothing and the strict documentation build passes. **Executor:** `general-purpose` on Haiku
- [x] 4. fd4562b `CLAUDE.md`, `.claude/workflow/core.md`, `.claude/skills/np-{plan,implement,ship,gui}/*.md`, §8.4 where a
  citation moves (D4); done when the token script prints nothing unexplained and every cited heading resolves.
  **Executor:** main
- [x] 5. Compaction checkpoint. **Executor:** main
- [x] 6. b40be15 The *End-of-phase report* and each criterion's verdict in the Phase 4 plan, REV-47 (D3); done when every
  number names its command and run. **Executor:** main
- [x] 7. 9ed2fdc `CHANGELOG.md`, `CITATION.cff`, `README.md`, `docs/index.md`, `docs/overrides/main.html`, the Phase 4 plan's
  status and WP60 entry, `current.md`, Z1 and AC6 in the index (D5); done when the strict documentation build passes.
  **Executor:** main

> **Outcome — items 1 to 4.** The quick-start leg walks the shipped case; `walks` exits 0. The re-run on the clean
> commit `db952e3` (four CPUs, threads unset, `dirty: false`) gives A1 1.15 GB of 4 GB, A8 0.69 % (quick-start) and
> 0.03 % (2WCD) of 5 %, and A16 0.84 % and 0.70 % of 10 %: no share is over (REV-116 `fixed`). The prose pass
> (`fd4562b`): the token script prints nothing that is not a removed duplicate or a pattern artefact, and every cited
> heading resolves. The files total 11,016 words (10,849 before): the sentences are shorter (mean 14.3 to 11.6
> words; those over 25 words 56 to 18), but the pass moved rules to their owner rather than cutting words.
> The gate-procedure steps live in `CLAUDE.md` alone, the plan caps in `np-plan/wp.md` alone.

> **Outcome — items 6 and 7.** The report in the Phase 4 plan is measured on this tree: prose share 11.89 % of
> `src/nanopnp` (6,573 of 55,299 lines) and 2.75 % of `tests/` (1,127 of 41,020); 442 `[tested: …]` spans, 438 naming
> 315 tests, all present; VER-61 with no `top` component; VER-65 at eleven (38 modules); VER-62's drift at most
> 1.5 × 10⁻¹³ on Linux, macOS and Windows (dispatched `ci.yml`, run 611 on `72b0689`: 1,652, 1,652 and 1,642 passed);
> notebooks 6 of 6 in 445 s on four workers; the commit hook 95 to 117 s, the push gate 243 s, the pull request's
> critical path 4 min 46 s. Two things the plan did not foresee: the commit of a findings log runs the full hook
> (101 s), not ruff alone, and `current.md` was already 1,021 words against its 700 target (972 now); neither is
> changed. Criterion 11's two timing targets and criterion 14's two word counts are reported misses for the author
> (specification 74,298 words, phase plan 6,869). `[0.5.0]` lists 48 breaks (bullets), each with its migration. The platforms run
> is on `72b0689`; the commits after it change Markdown, `CITATION.cff` and this plan only, so the tree under test is
> unchanged.

### Verification

No test is written (N1); the criteria that read a withdrawn check are verified at review (N3).

| Check | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| The layering | 1 | VER-61 | `test_layering.py`, the yaml unchanged | exact | `.claude/hooks/gate.sh run`; the dispatched run |
| The backend set | 1 | VER-65 | `test_backend_guard.py` at eleven | exact | as above |
| The golden on three platforms | 1, 2 | VER-62 | each leg's `number stability on` summary | 10⁻⁸ same mesh; the walk's moved tolerance (§7.6 NOTE) | the dispatched run |
| The suite | 1, 2 | — | the per-push selection passes | — | `.claude/hooks/gate.sh run` |
| The registers | — | — | every row terminal; no `open` REV row; item 3's grep empty | exact | review |
| The prose pass | — | — | item 4's token script | exact | review |
| The documentation | — | VER-45 | strict build | exact | `CLAUDE.md`'s docs command |

### Out of scope

| Deferred | Owner |
|---|---|
| The tag `v0.5.0` and the GitHub Release | `/np-ship phase 4`, after the merge |
| `steward/SKILL.md`, `hosts/copilot.md` | Not ruled into AC6 |
| A cost over its threshold, a drift or a residual cycle, if one appears | The author (M2, I4, H6) |
| REV-121, REV-156, REV-170, REV-171 | Phase 5 and Phase 6 (Z5, Z6, AC3, AC4) |
| OPN-04, OPN-08 | The author |

### Open questions

None blocks. The source's prose share was ruled at this plan (AE5). The In brief's *Your call*, the prose pass's
reach, is decided in review if the author does not answer first.
