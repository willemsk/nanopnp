# WP55 — The user-testing protocol

**Status: delivered, 2026-10-29.** Re-planned 29 October 2026 on WP54 as merged, grounded in the code
at `aac6739` (§8.2.15 Q1); first written 19 October 2026. Inherits WP50's test scope (§8.2.13 N1 to
N6), WP54's notebooks and figures (§8.2.20) and the protocol's rulings (§8.2.6 F3, §8.2.7 G7, §8.2.8
H2).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The program is tidied; now its author uses it as a nanopore modeller would, before anyone else
relies on it. This package writes what those sessions follow.

**What changes.** Pages beside the project's documents: how to install the program and run a
session, an empty log for findings, and five tasks a modeller would set: the command line, from a
case file to a reproduced current; the model's corrections and the salt; mesh refinement and a
refused mesh; the Python interface in a notebook, with a step of one's own added; and a sweep over
voltage and salt. Each states the goal and what the physics says should happen, never a number.
Every command runs each night, so the tasks cannot go stale before the sessions.

**Cost.** One to two days of work. The checks before each push do not grow; the nightly run grows
by about four minutes.

**What could go wrong.** A task could hint at a weakness the tester should meet unprompted; each
states the goal, never the trap. A task could quietly run nothing; the nightly check fails it. An
expected behaviour could be wrong; each was checked on the current code, and a physics review reads
them again.

**Your call.**
- Should the sessions run on the program installed as the getting-started page says, from the
  repository at the release tag into a fresh environment, rather than from the development
  checkout? *Recommendation:* yes; installing is part of what a user meets.

## Execution brief

Scope: the Phase 4 plan's WP55 section; G7 as superseded by N4 (the scripts run nightly); F3 (the
author runs the sessions); H2 (one task touches `with_section` and `core.stages.register`, for
`MOD-11`). Depends on WP54, merged. Claims VER-69, reserved by §8.2.9 I2, on VER-46's runner. Tag
`v0.5.0-alpha.21`. Implementing session: Sonnet, high effort. No `src/` change. A `physics-reviewer`
pass reads the five sessions' expected outcomes (item 7).

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Form and home | `docs/user-testing/protocol.md`, `docs/user-testing/findings.md`, and one self-contained directory per session, `docs/user-testing/sessions/NN-<slug>/`: a `README.md` and the case, field and Python files it uses, with no `../` path. Commands sit in `<!-- example: run -->` or `<!-- example: refused -->` console blocks, run by `src/nanopnp/validation/examples.py` unchanged; Python lives in files beside, run as `$ python <file>.py`. `sessions/.gitignore` lists what a session writes; `mkdocs.yml`'s `exclude_docs` gains `user-testing/`; ruff gives `sessions/*/notebook.py` the notebooks' ignores | G7: verbatim, as an example's (VER-46). One runner, no second extractor |
| D2 The sessions | Five, 20 to 40 minutes each, on cylinder meshes; no PDB entry, no PROPKA. **01** command line: a shipped uncharged case meshed, validated, run, inspected, reproduced. **02** physics: example 02's mid-plane ring, ePNP-NS and classical at 0.1 M, ePNP-NS at 1 M. **03** numerics: wall sizes 0.35, 0.25 and 0.175 nm, the stabilisation mode and the rungs read back, a 1.0 nm wall refused (exit 4). **04** Python API, a marimo notebook: `Case.cylinder`, `run_document` with progress and a cancel, the result's display and fields, a mesh substituted and walked `upto="materials"`, `with_section`, and a stage registered from a module beside it, both imported from their internal modules (H2). **05** sweep: the cis-ring pore over ±50 and ±100 mV × 0.1 and 1 M, planned, run on two workers, collected, inspected | F3's four areas, with the sweep as the modeller's routine use. Every step was run on this code (Grounding) |
| D3 What a session states | The task as a modeller sets it; the starting point; the steps; the outcome expected, as a property of the model (*Implementation details*), never a number; one variation the tester makes unscripted; a closing prompt naming the log. No session names a known weakness or a `MOD-nn` or `REV-nn` row. The protocol: install per the *Your call*, with the `notebook` extra; copy a session's directory out of the tagged checkout; time-box; log as you go | VER-46: no number in the documentation is a result unless a test asserts it. F3: a hint would spoil the finding |
| D4 The findings log | `findings.md`: front matter as `docs/project/modularity-findings.md`'s (`prefix: UT`, `status: open`, areas `install`, `cli`, `api`, `physics`, `numerics`, `docs`); a table `ID \| Area \| Severity \| Status \| Ruling \| Finding`, no rows; a legend: `high` a wrong or unusable result, `medium` a task needing knowledge the documentation does not give, `low` friction; status `open` until the second `/np-plan amend 4` rules it | G4's shape; its check is withdrawn, and the close reads the log at review (N3) |
| D5 VER-69's test | `tests/tier2/test_user_testing_sessions.py`, `nightly`, one case per directory of the glob `docs/user-testing/sessions/*/`. Per session: `copy_example`, then `run_tagged` for `run` then `refused`; assert at least one tagged command, and that every `$ nanopnp` or `$ python` line of a `console` block sits in a tagged block (a `$ marimo edit` line stays untagged, as in `notebooks/`). Exit status is the oracle; no number is asserted. VER-69's row and Appendix A's note come with the test | N4. The silent failure: a protocol gone stale, or a mis-tagged block that runs nothing. The expected properties are the tester's to judge |
| D6 The dry run and a defect | The implementer's run of D5's test is G7's dry run and records no `UT-nn`. Once, by hand, a session copy with one command broken must fail; the result goes in the Outcome, not a test (N1). A failure that is the script's is fixed in the script; one that is the program's is a `REV-nn` row (H12), fixed in its own commit when it touches one module, else put to the author before the package ends. A session is never rewritten to step around it | G7; N1; H12 |

### Grounding

**D1**
- `validation/examples.py:TAGGED_BLOCK` matches `<!-- example: <tag> -->` directly followed by a
  ```` ```console ```` fence. `tagged_commands` keeps `$ ` lines only and raises
  `ExampleCommandError` on a program outside `PROGRAMS = ("nanopnp", "python")`.
- `EXPECTED_EXIT`: `run` and `plan` exit 0, `refused` exits `EXIT_GATE`, 4 (`core/errors.py`).
- `copy_example(example, root, *, repository)` copies to `root/examples/<name>`, skipping the
  patterns of `example.parent/.gitignore` and `__pycache__`; a `../` word would mirror its directory.
- `run_tagged(directory, tag)` runs in `directory`, `python` as `sys.executable`, `nanopnp` from the
  interpreter's scripts directory, and raises on the first unexpected exit with stdout and stderr.
- `mkdocs.yml:exclude_docs` has no `user-testing/` entry. `pyproject.toml`'s ruff lints all of `docs/`
  except `docs/design/generators`; `"notebooks/*" = ["D100", "ANN001", "ANN202", "B018"]`. mypy
  reads `src` only.
- `.github/scripts/prose-only.sh` treats a `docs/**.md` change as prose: the push gate runs ruff
  alone. No change: the sessions' test is `nightly` and the push gate runs none.

**D2**
- `nanopnp mesh cylinder` takes `--pore-radius-nm` (2), `--membrane-thickness-nm` (6),
  `--reservoir-radius-nm` (10), `--maxh-nm` (4), `--wall-h-nm` (0.35), `--out`; it meshes in about
  1 s and prints the `inputs.mesh.groups` block, `{default: interface}`.
- 01: `examples/01-quickstart/quickstart.case.yaml` on the default mesh runs in 14 s, one thread,
  exit 0. `nanopnp validate case <file>` checks a case without solving.
- 02: `examples/02-charged-pore/ring.field.yaml` is a Gaussian ring, `q_net_e: -6.0`, at r 2.6 nm,
  z 0. Measured, default mesh: t₊ 0.542 for ePNP-NS at 0.1 M (20 s), 0.556 classical (5 s), 0.392
  ePNP-NS at 1.0 M (16 s); the uncharged pore's is 0.385.
- 03: walls 0.35, 0.25, 0.175 nm give currents 6.6228, 6.6473 and 6.6617 × 10⁻¹¹ A in 14, 18 and
  28 s: the finer pair differs by 1.4 × 10⁻¹³ A, the coarser by 2.5 × 10⁻¹³ A. `--wall-h-nm 1.0`
  meshes (exit 0); `nanopnp run` on it exits 4 in 1.5 s, naming NUM-34's wall-distance gate and
  `numerics.mesh.wall_h_nm`.
- 04: `Case.cylinder(..., store=, write=, outputs=)` (`pipeline/handle.py`) meshes into
  `<store>/meshes/`. `Case.run` takes no `progress` or `cancel`; `run_document(case.document,
  case_text=dumps_case(case.document), store=, progress=, cancel=CancelFlag())` does, and raises
  `Cancelled` (both public). `case.with_(**{"inputs.mesh.path": ...}).run(upto="materials")` walks
  `case` and `materials` only, the materials hash unchanged. `with_section` is
  `io/case_paths.py:with_section`, and takes only `"charge"`; that document, walked, serves mesh,
  materials and solve from the store and recomputes case, qoi and report. `RunResult.fields`,
  `current_nA`, `figure(stage)` and its display exist.
- 04: `core/stages.py:register(StageDescription(...), "module:Class")` appends a stage, walked after
  `report`; `create` imports the module, and marimo sets `sys.path[0]` to the notebook's directory
  under `edit` and `python` (its documentation). A prototype `selectivity.py` with `inputs=("case",
  "qoi")`, `needs_section=None`, building `nanopnp.io.artefact.Artefact` from
  `StageInputs.require("qoi")`, walked in full; its artefact is in `result.artefacts`. Registering a
  name twice raises `ValueError`.
- 05: two axes, bias origin 2 and salt origin 0, plan 8 points in 4 waves; `sweep run --workers 2`
  took 35 s; the root is cold, every other point `warm_start.status: warm`. Rectification 0.91 and
  0.84 at 0.1 M, 0.994 and 0.989 at 1 M; `nanopnp inspect <dir>/dataset.json` prints them.

**D4**
- `docs/project/modularity-findings.md`'s front matter is `findings: {prefix, status, areas}`; its
  legend cites VER-63, withdrawn, which `findings.md` does not copy.

**D5**
- `tests/tier2/conftest.py` marks the directory `tier2`; `pytestmark = pytest.mark.nightly` as in
  `test_notebooks.py`; naming the file runs it without `--nightly`.
- VER-69's row goes between VER-68 and VER-70 in `specification/07-verification/02-tier-1.md`, where
  VER-46 sits though it runs in Tier 2. Appendix A has no row per `VER-`; its closing note names
  VER-61 and VER-62 as verifying Phase 4's gate rather than a §3 requirement, and VER-69 joins them.

### Implementation details

**Item 1.** `findings.md`: the front matter of D4, a title, one paragraph (the log of the sessions
of `protocol.md`; a row per finding; ruled at the second amendment), the legend, the empty table
header. `sessions/.gitignore`: `store/`, `*.msh`, `run-*/`, `iv-*/`, `__pycache__/`,
`__marimo__/`. `mkdocs.yml`: `user-testing/` after `plans/`. `pyproject.toml`:
`"docs/user-testing/sessions/*/notebook.py" = ["D100", "ANN001", "ANN202", "B018"]` beside
`notebooks/*`.

**Item 2.** `protocol.md`: *Setup* (a fresh virtual environment; `pip install "nanopnp[notebook] @
git+https://github.com/willemsk/nanopnp@<tag>"`; `nanopnp --env`; `git clone --branch <tag>` for
the session files; copy one session directory to a working directory, run there without `uv run`);
*Order* (01 to 05, one sitting each, 40 minutes); *Recording* (a row per surprise, as it happens,
area and severity by the legend, the command and its output pasted into the row's section); *Dry
runs* (G7: an agent may run a session to debug it and records nothing).

**Item 3.** The test, one function, parametrised by `pytest.mark.parametrize` over
`sorted(SESSIONS.glob("*/README.md"))`, ids the directory name: `copy_example(session,
tmp_path, repository=REPOSITORY)`; collect the commands of `run` and `refused` with
`tagged_commands` and assert they are not empty; collect every `$ nanopnp`/`$ python` line inside
any ```` ```console ```` fence of the README and assert it is among them; then `run_tagged(copy,
"run")` and `run_tagged(copy, "refused")`; log each session's seconds.

**Sessions.** Each README: *The task*, *You start with*, *Steps* (the tagged block, then what each
command does), *What to expect*, *Then try*, *Record*. Files and expectations:

- **01-command-line**: `pore.case.yaml` (the quickstart case, renamed). Block `run`: `mesh cylinder
  --out pore.msh`, `validate case pore.case.yaml`, `run pore.case.yaml --store store --run-dir
  run-pore`, `inspect run-pore`, `reproduce run-pore`. Expect: the two current routes agree, no
  deviation is listed, `reproduce` agrees. Then try: reverse the bias; expect the current to reverse
  at the same magnitude, the pore being uncharged and mirror-symmetric.
- **02-physics**: `ring.field.yaml`, `epnpns.case.yaml`, `classical.case.yaml` (example 02's),
  `epnpns-1M.case.yaml`. Block `run`: mesh, three runs, `inspect` of the classical run. Expect: t₊
  above ½ at 0.1 M under both models; each `none` correction listed as a deviation in the classical
  run, none in the ePNP-NS runs; at 1 M t₊ falls towards the uncharged pore's, the charge screened.
  Then try: a positive ring.
- **03-numerics**: the quickstart case as `wall-035.case.yaml`, `wall-025.case.yaml` and
  `wall-0175.case.yaml`, each naming its `wall-*.msh`, and `coarse.case.yaml` naming `wall-100.msh`,
  each with its own `name:`. Block `run`: four meshes (`--wall-h-nm` 0.35, 0.25, 0.175, 1.0), three runs,
  `inspect` of the finest. Block `refused`: `run coarse.case.yaml ...`. Expect: the current changes
  less between the finer pair than the coarser; the manifest records the stabilisation mode and
  each rung; the refusal names its gate, the quantity, where, and the setting to change.
- **04-python-api**: `notebook.py` (marimo, store `store/` beside it), `selectivity.py` (the
  prototype of *Grounding*, typed, with docstrings). Block `run`: `python notebook.py`; an untagged
  block, `marimo edit notebook.py`. Expect: a cancel stores no solve; the substituted mesh moves the
  mesh key and not the materials key; the added `charge:` section moves no solve key; the new stage
  appears after `report` with its verdict. Then try: make the stage read the solve.
- **05-sweep**: `charged.case.yaml`, `cis-ring.field.yaml` (example 03's), `grid.sweep.yaml` (D2's
  axes). Block `run`: mesh, `sweep plan ... --directory iv-grid`, `sweep run iv-grid/plan.json
  --store store --workers 2 --csv`, `sweep collect`, `inspect iv-grid/dataset.json`. Expect: every
  point after the first starts warm; rectification departs from unity at 0.1 M, more at 100 mV than
  at 50 mV, and returns towards unity at 1 M. Then try: an uncharged control.

### Work items

- [x] 1. ba542be `docs/user-testing/findings.md`, `docs/user-testing/sessions/.gitignore`, `mkdocs.yml`,
  `pyproject.toml` (D1, D4); done when the code and review say so, and `uv run ruff check .` and the
  strict documentation build pass. **Executor:** `general-purpose` on Haiku.
- [x] 2. 9388f9c `docs/user-testing/protocol.md` (D3); done when the code and review say so. **Executor:**
  main.
- [x] 3. 8cac812 `tests/tier2/test_user_testing_sessions.py`, `docs/user-testing/sessions/01-command-line/`,
  VER-69's row and Appendix A's note (D2, D5); done when `uv run pytest
  tests/tier2/test_user_testing_sessions.py` passes. **Executor:** main.
- [x] 4. 3f2a6b0 `sessions/02-physics/`, `sessions/03-numerics/` (D2, D3); done when the same command
  passes. **Executor:** main.
- [x] 5. Compaction checkpoint. **Executor:** main.
- [x] 6. 7608f53 `sessions/04-python-api/`, `sessions/05-sweep/` (D2, D3, H2); done when the same command
  passes. **Executor:** main.
- [x] 7. 7bb72a7 D6's broken-command check; a `physics-reviewer` pass on the five *What to expect*
  sections; each session's nightly seconds on four cores in the Outcome; `CHANGELOG.md`
  `[Unreleased]`; `current.md` and the Phase 4 plan's WP55 section delivered; done when
  `.claude/hooks/gate.sh run` passes and the test passes. **Executor:** main.

> **Outcome — the sessions run as written.** `uv run pytest tests/tier2/test_user_testing_sessions.py`
> passes for all five on four cores, in 199 s in all (3.3 minutes, inside the "about four" of the
> *In brief*): 01 command line 30.8 s, 02 physics 42.6 s, 03 numerics 64.5 s, 04 Python API 19.7 s,
> 05 sweep 39.4 s. Session 04 differs from the plan in two small ways, both found by running it:
> `case.run(upto="materials")` walks `case` and `materials` alone, so the notebook walks to `mesh` and to
> `materials` separately, as example 04's tour does; and the stage is registered behind
> `"selectivity" not in walk_order()`, because a marimo cell reruns and a second registration raises.
>
> **Outcome — the broken-command check (D6).** Once, by hand: a copy of session 01 with
> `validate case pore.case.yaml` changed to `validate case pore-missing.case.yaml` was run with
> `run_tagged(session, "run")` and raised `ExampleCommandError`, the command exiting 3 where a `run`
> command must exit 0. It is not a test (N1).

> **Outcome — the physics review (item 7).** A `physics-reviewer` pass over the five *What to expect* sections
> found and this package fixed: session 04's stage called a pore "cation-selective" at t₊ above ½, though bulk
> NaCl is already at about 0.4, so it now names the ion that carries more than half of the current and the README
> expects only that its transport number is the result's; session 02 compared the cation share with ½
> instead of with the bulk electrolyte's, and its flip-the-ring variation named no comparison; session 01 expects the mirror
> symmetry to the accuracy of the mesh. The review confirmed session 05's claim that the departure from unity is
> larger at 100 mV than at 50 mV, and found no session naming a known weakness. It also found that the knowledge
> base said rectification needs a geometric asymmetry, which the cis ring in a symmetric cylinder contradicts;
> the sentence is corrected (`knowledge/log.md`). The program's own defect it found, NUM-34's refusal naming a
> setting a supplied mesh ignores, is REV-154, open, and session 03 is not rewritten around it (D6).

### Verification

| Test | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `test_session_commands_still_run_as_written[<session>]`, one per session directory; VER-69 in the commit body, not the name (`CLAUDE.md`) | 2, `nightly` | VER-69 | Per session: at least one tagged command; no untagged `$ nanopnp` or `$ python` line; each `run` command exits 0 and each `refused` command 4 | Exit codes, IF-02 | `uv run pytest tests/tier2/test_user_testing_sessions.py` |

D6's broken-command check is a one-off, recorded in the Outcome. No test asserts a session's
expected properties (D3, D5).

### Out of scope

- The sessions and every `UT-nn` row: the author's (F3, G7).
- The `MOD-11` choice: a fix package, after the sessions (H2).
- The fix packages from WP56, the documentation increment and the close: the second `/np-plan amend 4`.
- The sessions on the documentation site: documentation increment 4, if the author rules so.

### Open questions

None blocking. The *Your call* defaults to its recommendation; a contrary ruling changes only the
protocol's *Setup*. The author ruled on 20 October 2026 that the tasks stay off the documentation
site until the documentation increment (D1).
