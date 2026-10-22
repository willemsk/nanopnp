# Phase 4 plan: the record

The text of [the Phase 4 plan](phase-4-polish-and-user-testing.md) as it stood at `a201d92`, before WP52 restated it to its current scope (§8.2.16 R4), copied verbatim with every `Amended` blockquote. Read it on demand; the plan states what holds now. A later amendment appends a dated section below.

---

# Phase 4 (Polish and user testing): a codebase whose seams are measured and whose surface has been used

**Status: in progress.** Written 5 October 2026, after Phase 3 closed as `v0.4.0`. Amended the
same day, after the author ruled every `MOD-nn` (§8.2.8). Amended again on 6 October 2026, after
the author ruled the review register (§8.2.9), and on 11 October 2026, when the author inserted the
development loop (§8.2.10), on 13 October 2026, when the author simplified it (§8.2.11), and on
18 October 2026, after the author ruled an external architecture review (§8.2.12), and again that
day, when the author ruled the test scope (§8.2.13), and on 22 October 2026, when the author inserted
the plotting library and the notebooks (§8.2.14), and again that day, when the author inserted the
documents, the workflow and the notebooks' revision (§8.2.16).
Delivered: WP35, the modularity exploration
([wp35-modularity-exploration.md](wp35-modularity-exploration.md)), tagged `v0.5.0-alpha.1`;
WP36, the stage protocol and the walk ([wp36-stage-protocol-and-walk.md](wp36-stage-protocol-and-walk.md)),
tagged `v0.5.0-alpha.2`; WP37, the cycle cuts, the exit codes and the backend guard
([wp37-cycle-cuts-exit-codes-backend-guard.md](wp37-cycle-cuts-exit-codes-backend-guard.md)),
tagged `v0.5.0-alpha.3`; WP38, the `io` split ([wp38-io-split.md](wp38-io-split.md)),
tagged `v0.5.0-alpha.4`; WP39, the backend registries ([wp39-backend-registries.md](wp39-backend-registries.md)),
to be tagged `v0.5.0-alpha.5`; WP40, the stale refusals ([wp40-stale-refusals.md](wp40-stale-refusals.md)),
to be tagged `v0.5.0-alpha.6`; WP41, the accuracy fixes ([wp41-accuracy-fixes.md](wp41-accuracy-fixes.md)),
to be tagged `v0.5.0-alpha.7`; WP42, the verification checks
([wp42-verification-checks.md](wp42-verification-checks.md)), to be tagged `v0.5.0-alpha.8`;
WP43, the development loop ([wp43-development-loop.md](wp43-development-loop.md)), to be tagged
`v0.5.0-alpha.9`; WP44, simplify the loop ([wp44-simplify-the-loop.md](wp44-simplify-the-loop.md)), to be
tagged `v0.5.0-alpha.10`; WP45, the prose strip ([wp45-prose-strip.md](wp45-prose-strip.md)), to be tagged
`v0.5.0-alpha.11`; WP46, the small fixes ([wp46-small-fixes.md](wp46-small-fixes.md)), to be tagged
`v0.5.0-alpha.12`; WP47, the OKF bundle ([plan](wp47-okf-bundle.md)), to be tagged
`v0.5.0-alpha.13`; WP48, the OKF backfill ([plan](wp48-okf-backfill.md)), to be tagged
`v0.5.0-alpha.14`; WP49, the cost study ([plan](wp49-cost-study.md)), to be tagged
`v0.5.0-alpha.15`; WP50, the test scope ([plan](wp50-test-scope.md)), to be tagged
`v0.5.0-alpha.16`.
WP51, the plotting library and the notebooks ([plan](wp51-plotting-and-notebooks.md)), to be tagged
`v0.5.0-alpha.17`.
Planned (§8.2.16 R1), each awaiting its plan: WP52, the documents; WP53, the workflow; WP54, the
notebooks and figures revised.
Planned: WP55, the user-testing protocol ([plan](wp55-user-testing-protocol.md); §8.2.9 I1,
renumbered by §8.2.12 M4, §8.2.13 N6, §8.2.14 P1 and §8.2.16 R1).
Provisional, and planned by the second `/phase-plan amend 4` once the author has run the sessions
and ruled every `UT-nn`: the fixes, from WP56, then the documentation increment and the close,
which take their numbers then.
Estimate: 4–6 weeks (§8.2.9 I5). Release: **v0.5** (`v0.5.0`).

## In brief

Phase 4 tidies the program before others rely on it. The rebuilt structure, the simpler loop, the
trimmed code and tests, the reorganised notes, the cost study, and a picture of every step of the
pipeline with notebooks to try it are done. On 22 October the author asked for two more things
before the testing sessions.

**What changes.** Three packages now come before the protocol. The first splits the specification
into what holds today, read by default, and its history, read only when needed, and does the same
for this plan. The second rebuilds the working instructions as three commands, plan, implement and
ship, each taking a level; hands batches of independent edits to fresh helpers; and keeps the
instructions a session loads up to date. The third revises the notebooks and figures from the
author's notes.

**Cost.** About a week and a half. Nothing a user runs changes in the first two.

**What could go wrong.** Moving 78,000 words could drop or alter a requirement; a script checks that
every line lands somewhere, and every identifier still finds the same text. A rewritten instruction
could lose a rule; the first package planned with the new commands would show it. The notebooks'
revision has an open scope, so its plan names any new dependency before it enters.

**Your call.** Should the phase estimate grow from four to six weeks to five to seven?
*Recommendation:* yes; the sessions matter more than the date.

## Context

This is the delivery plan for Phase 4 of `SPECIFICATION.md` §8.1. The specification is normative.
Where this file and the specification disagree, the specification governs and this file is wrong.
Requirement identifiers here are pointers into the specification, never restatements of it. The
author's rulings behind this plan are §8.2.6 F3, F4 and F6, §8.2.7 G1 to G11, §8.2.8 H1 to H12 (on
the modularity report and the review register), §8.2.9 I1 to I5 (on planning the register's items), §8.2.10 J1 to J9 (on the development loop), and
§8.2.12 M1 to M5 (on the architecture review), §8.2.13 N1 to N7 (on the test scope) and §8.2.14 P1
to P7 (on the plotting library and the notebooks).
They are not re-argued here.

Phases 0 to 3 built the pipeline, from a structure to a charged current. Phase 4 asks two questions
before the GUI phase builds on that pipeline and the validation phase measures it. The first is
whether the architecture is as modular as FR-27, FR-20 and QR-14 claim. The second is whether a
person who did not write the code can use the physics, the numerics, the Python API and the
command line. The phase answers the first with a measured report and the refactors the author
accepts from it, and the second with scripted sessions that the author runs and a findings log.
Between them, the companion knowledge base becomes an OKF bundle in which every tested claim names
its test (F6).

The gate (§8.1, as amended by §8.2.7) has five parts:

- the modularity report is merged, with every finding ruled;
- the user-testing findings log is closed;
- both logs pass the G4 check with their headers set to `closed`;
- the number-stability golden holds (10⁻⁸ on a recorded mesh; G10, VER-62);
- Tiers 1 and 2 pass.

*Amended, 11 October 2026* (§8.2.10 J7), *replaced, 13 October 2026* (§8.2.11 L2 to L8): a sixth part,
the development loop is simple and the prose small, with the loop's timings reported and a miss ruled.

No requirement in Appendix A is tagged v0.5, so the evidence is the report, the two logs, the golden
and the suites.

Seven things are true of the codebase today, at `a774b20`, and they shape every package below.

- **The stage protocol does not cover the key.** `core/stages.py` defines `Stage`, with `name`,
  `describe()` and `run(inputs, *, progress, cancel)`. Thirteen stages are registered through
  `register()` and built lazily by `create()`. `key()` is not on the Protocol:
  - `MaterialsStage` and `CaseStage` have no `key()`;
  - `validation/comsol.py` calls `key()` under `# type: ignore[attr-defined]`;
  - `io/run.py` hard-codes `WORKSPACE_STAGES`, `STORE_STAGES` and `STRUCTURE_STAGES`, and its
    `selected_stages()` decides which stages a case skips.
- **Modules are layered, subpackages are not.** The top-level import graph between modules is
  acyclic. Between subpackages, ten of them form one strongly connected set, from `structure` to
  `io`. Some examples:
  - `mesh/distance.py` imports `physics.measures` and `solve.linear`;
  - `materials/fields.py` imports `charge.fields`;
  - `io/case.py` imports `charge`, `materials`, `physics` and `solve`, so `io` is both the base
    layer and the assembler;
  - `cli/errors.py`, the exit-code table, is imported by `sweep`, `validation` and `gui`.

  No layering test exists.
- **The extension points are uneven.** Two of them are registries:
  - corrections: `materials/models.py`, with a YAML file per model;
  - physics models: `physics/models.py` `register_model`. Nothing outside `physics/` names a
    model, so VER-56 holds.

  The mesher and the linear solver are branches:
  - `mesh/generate.py` `mesh_region` tests `if backend == "gmsh"`, behind a schema `Literal`;
  - `solve/linear.py` tests `if solver == "superlu"`, against `AVAILABLE_SOLVERS`.
- **The public surface is 26 names**, in `nanopnp.PUBLIC`, pinned by `tests/tier1/test_public_api.py`.
  `with_section` was held out for this phase's API pass (WP34 D9). `core.stages.register` is
  public in practice but is not in `PUBLIC`. No hand-written page of the user guide covers the
  API; example 04 and the generated reference do.
- **The command line is one module.** `cli/__init__.py` is 1,266 lines, and its `build_parser`
  alone is 216 lines. It has eight subcommands. `test_cli.py` pins the exit-code table in
  `cli/errors.py` in both directions. Some refusal texts in `io/case.py`'s `_require_runnable`
  are stale:
  - an unconsumed input is "not delivered in this release";
  - a stored charge artefact is one "the charge pipeline of v0.4 fills";
  - two `numerics.nonlinear` values are refused as "v0.2".
- **The knowledge base is ten flat files**: 5,682 lines, 88 `##` sections, 193 `[tested]` and 53
  `[verified]` markers, cited about 470 times outside itself. `docs/scripts/generate.py` globs
  `knowledge/*.md` without recursing.
- **The suite collects 1,764 tests by default and 1,861 in all.** Collection takes 12 s. The
  `extended` walks already compute the numbers a stability golden needs.

This phase retires no risk. RSK-15 and RSK-16 stay continuous. The report raised no new risk, and
its rulings (§8.2.8) enter none.

The rulings on the report, 5 October 2026: 13 findings accepted for Phase 4 (`MOD-01` to `MOD-07`,
`MOD-11` to `MOD-16`), `MOD-09` deferred to Phase 5, `MOD-10` deferred to Phase 6 with QR-13
restated, and `MOD-08` and `MOD-17` post-1.0. `MOD-06` and `MOD-07` are fixed now, against the
report's recommendation to defer them (H7). `MOD-11` alone waits for the sessions (H2).

The rulings on the review register (§8.2.9), 6 October 2026, cover the 56 items left open by the
packages up to WP36. 37 are planned into Phase 4: 30 into three new packages
before the OKF bundle (WP41 to WP43), three each into WP38 and WP39, and one into the close; REV-03
and REV-05 were already WP38's and WP39's. 15 are deferred to Phase 5 or 6, two are post-1.0, and two
are declined (I1 to I3).

The rulings on the development loop (§8.2.10), 11 October 2026, insert WP43 before the small fixes.
Five things were measured that day, at `d630f85`, on a 4-core container:

- **The commit hook's pytest stage took 199 s**, over 2,077 tests. Ruff, the lock check and a warm
  mypy took about 3 s together (mypy took 37 s cold), and collection took 3.7 s.
- **The push gate's pytest stage took 395 s, and 527 s with branch coverage**, over 2,135 tests. The
  58 `extended` walks account for about half of it. The longest setups are session-scoped 2WCD seeds,
  each paid by the worker that asks first, so under `--dist loadfile` one file carries it: example
  07's setup took 314 s.
- **CI's critical path took about 10.5 minutes.** `check` and five `test-matrix` legs each run the
  full suite, pytest is 90–95 % of every job, and no job sets a timeout. There is no
  `.test_durations` file and no test-impact tool.
- **There is no `.claude/agents/`.** The model for each delegated task lives only in the prose of
  `.claude/model-policy.md`. The five skills total about 9,300 words. `SPECIFICATION.md` is about
  70,000 words.
- **`import nanopnp` took 0.1 s.** Lazy imports would not shorten the gate (J6).

Deliberately excluded:

- any GUI work beyond following the API and the schema (QR-11; §8.1, GUI increment 4). Screens,
  the result browser and figure export are Phase 5's (F5);
- Tier 3 and Tier 4, the archive-dependent legs and NUM-07's decision, which are Phase 6's (E1, E4,
  F1);
- OPN-08 (stable v1.0), which stays the author's;
- structure preparation, and OPN-04;
- any new physics. A finding that asks for physics is deferred, with a ruling, to Phase 6 or to
  post-1.0;
- Python 3.15 and its lazy imports, which wait on OPN-09 (§8.2.10 J6);
- the browser shell that replaces the Qt shell, which is Phase 5's (§8.2.12 M3), and every claim of
  the 18 October architecture review that the code already meets (M1, REV-115);
- the export of figures from a run by the command line and the report stage, FR-28's at v0.7 in
  Phase 6; the GUI's own plots, which Phase 5 replaces (M3; §8.2.14 P3); and the notebooks on the
  documentation site, which wait on documentation increment 4 (P5).

The rulings on the architecture review (§8.2.12), 18 October 2026, rest on four facts measured at
`645289e`:

- **The aligned ensemble is held whole.** `structure/ensemble.py` `AlignedEnsemble.positions_nm` is
  one float32 array of frames × atoms × 3, while `density/union.py` `deposit` already streams by frame
  and by z slab.
- **Every rung rebuilds its forms.** `physics/models.py` `CoupledModel.solve` builds a new
  `BilinearForm` per rung, on the space the warm start hands it.
- **Every stage reads its inputs back from the store.** `pipeline/run.py` goes through
  `Store.get_or_compute`, whose writes are already staged and renamed (`io/store.py`).
- **The case schema is Pydantic v2 and strict, and has no JSON Schema export.** `io/case.py` sets
  `extra="forbid"`; nothing calls `model_json_schema`.

The rulings on the plotting library and the notebooks (§8.2.14), 22 October 2026, rest on five facts
at `7f32b20`:

- **The library draws nothing.** No module of `src/nanopnp/` outside `gui/` imports a plotting
  library. Examples 03 (`plot_iv.py`) and 04 (`tour.py`) draw with Matplotlib, the `examples`
  extra's only package, and `tests/tier1/test_source_conventions.py` `DEFERRABLE` already admits it.
- **The GUI's drawing data sits above everything.** `gui/geometry.py` `ImageModel`,
  `reduced_image` and `density_section`, `gui/charge.py` `charge_image` and `gui/convergence.py`
  `ConvergenceModel` import no Qt, but `gui` is last in `validation/modularity.py` `LAYER_ORDER`.
  The plots are `QPainter` widgets, and the fields go through `webgui` (`gui/render.py` `render`).
- **Fields come out as arrays.** `post/export.py` `p2_nodes` and `sample_at` give a field's
  values at points, and `RunResult.artefacts` (`pipeline/run.py`) maps each stage to its artefact.
- **The registry already names things lazily.** `core/stages.py` `_register_builtins` registers each
  stage by a dotted path and an optional `extra=`, both resolved at `create()`.
- **No artefact displays itself.** No type defines a `_repr_*_` method, and no notebook tool is in
  `uv.lock` (REV-123). The examples runner, `validation/examples.py`, runs `nanopnp` and `python`
  commands only.

## Design decisions

Each package's `/wp-plan` decides the rest in its own decisions table: WP35 decides the report's
contents and the guard's form, and the first OKF package decides open questions 3 to 7 (G9).

| Decision | Choice | Why |
|---|---|---|
| What opens the phase | A report with numbered findings, `MOD-nn`, produced by a committed script, and a Tier-1 guard that pins the layering the report records. No refactor in that PR (§8.2.7 G1) | F3's gate rules on findings before code moves. A measurement that cannot be rerun is an adjective |
| When refactors land | Every refactor the author accepts lands before the user-testing protocol (G2) | Testers then judge the surface v0.5 ships |
| The OKF work | Two packages joined by a shrinking list of unbacked claims (G3). Executable `[verified]` claims get tests. The rest stay `[verified]` with a required source footnote under `process:arithmetic` (G8) | One mechanical PR, then one PR of tests needing physics review. The gate never holds a half-built ledger |
| Findings | One Markdown log per study under `docs/`. Each row gives the id, area, severity, status and the ruling pointer. A Tier-1 check refuses a malformed row at any time, and a non-terminal row once the header says `closed` (G4) | The gate's "each finding ruled" becomes a test |
| The protocol | Its scripts run verbatim in the push gate, as an example's do. Findings come from the author's sessions only, and an agent dry run records none (G7) | The protocol cannot go stale before the sessions, and the tester did not write the code |
| The case schema | It moves as needed. A move takes the release's identifier, starting with `nanopnp/case/v0.5`. It may change between alpha packages and is fixed at the tag. Earlier identifiers are read as their upgrade (G6; the §5.3.1 NOTE) | The author's ruling: the schema keeps step with the package until v1.0 fixes it |
| Number stability | A golden recorded in WP35 on `v0.4.0`'s tree and asserted by every later package, at 10⁻⁸ relative on a recorded mesh (G10; VER-62) | A polish phase must not move a result inside a benchmark's tolerance unnoticed |
| The public API | It may break (F4). Each break is decided in `test_public_api.py` and listed in `CHANGELOG.md` with its migration. The shell follows it in the same PR (QR-11) | IF-01's promise starts at v1.0 |
| Close and tags | `v0.5.0` alone on the close package's last commit. The session pushes each tag if its access allows, and otherwise prints the commands (G11) | As E5 did for Phase 3 |
| The findings | Each `MOD-nn` as §8.2.8 H1 to H5 rule it. `MOD-11`'s choice follows the sessions (H2) | The report's recommendations, except H7 |
| The coupling target | The subpackage `top` relation acyclic, in the report's layer order. On a miss, the residual cycle is reported with its cut and ruled; no cut is forced (H6) | Pre-registered, so the gate does not take whatever the refactors leave |
| QR-13 | Met by the single statement of the weak forms. The backend's subpackages are a recorded set that only shrinks without a ruling (H3; VER-65) | An interface with one implementation cannot be tested for the property it exists for |
| Backend keys | The mesher, linear solver and stabilisation become registries, and their schema keys strings checked against them. Each is a widening, so the identifier stays (H7; the §5.3.1 NOTE) | QR-14's one-class extension, for the three branches the report measured |
| Refactor order | Stage protocol, cuts, `io` split, registries, refusals (H8) | The interface later packages read goes first, and the split precedes the schema edits |
| The review register's items | Those accepted for Phase 4 land in three packages by kind, WP41 to WP43, after WP40 and before the OKF bundle. The OKF bundle, the backfill and the protocol become WP46 to WP48 (§8.2.9 I1, I2) | Numbers settle before the ledger re-establishes them and before the testers see them |
| The open `REV-nn` rows | Each one ruled: into a Phase 4 package, deferred to Phase 5 or 6, post-1.0, or declined (I3) | Every item of the register has an owner |
| An accuracy fix and the golden | WP41's plan argues a bound for each VER-62 QoI before the change. A drift within that bound is re-pinned in the same commit as the amended clause; a drift beyond it stops the package (I4) | G10's ruling is given in advance for a fix whose purpose is to move a number, and only within a bound registered beforehand |
| The architecture review | Already-met claims declined with their evidence; one measure-first package with registered thresholds and a JSON Schema export; the browser shell to Phase 5 (§8.2.12 M1 to M3) | A cost is fixed when it is measured, not when it is suspected |
| Where the cost study goes | WP49, before the protocol, which becomes WP50 (M4) | Testers see the tree v0.5 ships (G2) |
| The test scope | Tests only for physics, numerics, core mechanisms and the licence and architecture guards; no coverage gate; walks nightly but for examples 01 and 02; a reviewer step deletes off-category tests; WP50, before the protocol (§8.2.13 N1 to N6) | Development speed is spent on tests that can catch a wrong answer |
| The plotting library and the notebooks | WP51, before the protocol, which becomes WP52. Matplotlib in a new `plot/` below `pipeline`, importing no backend; each stage's figure declared in the stage registry, so every artefact displays itself; marimo notebooks run nightly; FR-30, tested by a smoke test and an import guard (§8.2.14 P1 to P7) | The author confirms each stage by eye before the sessions, and neither the display nor a later stage can break the layering |
| The documents and the workflow | WP52 to WP54, before the protocol, which becomes WP55. The specification an OKF bundle read current by default, its history on demand, the rulings in force restated in a process section; plans current, their amendments in a record; `/plan`, `/implement` and `/ship` with levels; workers for independent batches; the primary checkout fast-forwarded; the notebooks revised from the author's notes, scope open (§8.2.16 R1 to R10) | A session reads what holds today, and the author tests notebooks revised from their own review |
| The development loop | WP43, before the small fixes. The commit hook runs the fast checks and the affected tests. The push gate runs once, in the background. CI runs ubuntu on Python 3.14 on a pull request, and macOS and Windows after a merge. Python 3.14 is the default. The agent roster is defined, and plans open with a plain-language summary. Every change is held to pre-registered budgets (§8.2.10 J1 to J9) | Every later package is built on it. The budgets keep it from drifting back |

## Conventions established by earlier phases

Inherited, and not re-decided by any package below.

- **The case document is the unit of reproducibility.** No stage reads YAML, and an unknown key is
  refused, naming it (IF-03). A move of the schema now follows G6.
- **Every switch is classified** in `SWITCH_PATHS` or `CONFIGURATION_PATHS`, in both directions
  (VER-24). Disabling a correction selects `none`; it takes no code branch.
- **Artefact keys are canonical hashes over validated payloads** (§5.3.2). The environment is
  recorded beside a key, never inside it, and no payload records wall-clock time (VER-23).
- **A stage is introspectable without importing its implementation** (VER-25). A missing extra is
  a named `MissingExtraError` at `create()`. `import nanopnp.cli` stays solver-free, and the
  `CLAUDE.md` deferred-import rule governs every refactor.
- **Layers read a model's declaration, never its name or class** (VER-56; the §5.4.3 NOTE).
- **A generated mesh is read only through `deployed_mesh`**, and a charge is deposited on the mesh
  the solve uses (WP21 D12; WP28).
- **Supply chains are exclusive** (the §5.3.1 NOTE on `inputs:`).
- **A documented command runs verbatim in the gate** (VER-46). A number in the documentation is a
  result only if a test asserts it. Generated references are built, never committed.
- **The desktop shell holds no physics** and reads every number from a stage's artefact (VER-60).
  A new payload is declared in `PAYLOADS` and exercised by `--selftest`.
- **A gated test gets cheaper only by the §7.6 NOTE's four levers** (WP33). The protocol's scripts
  and the golden attach to work the gate already does wherever they can.
- **Every plan, and every package's pull request, opens with `## In brief`** (§8.2.10 J9).
- **2WCD is prepared through `prepared_2wcd`** in tests. The VAL-05 ensemble test fails on the
  archive by design (D7).

## Work packages

Each package gets its own `/wp-plan <n>` before implementation, and is green on Tiers 1 and 2
before the next starts. Identifiers from VER-61 on are **proposed**, and a package claims its own
when it implements them. Tags are `v0.5.0-alpha.N`.

### WP35 — The modularity exploration: report, findings log, guard and golden

WP35 measures the architecture against its own claims and reports what it finds. It does not
change it. It covers:

- **the stage boundaries and FR-27**: the Protocol, the uneven `key()`, and the walk's hard-coded
  stage sets;
- **the coupling between subpackages**: the import matrix and the strongly connected set, and
  whether `io` should split into a base layer and an assembler;
- **the extension points**: corrections, physics models, the mesher and the linear solver, judged
  against FR-16, FR-20, QR-14 and ADR-002, together with QR-13's single statement of the weak
  forms;
- **the public surface and the command line, as structure**: `with_section`, `register`, the size
  of `cli/__init__.py`, and the stale refusals.

The report is `docs/project/modularity.md`, rendered by the documentation site. Its findings log is
`docs/project/modularity-findings.md`, `MOD-nn`, header `open`. Each finding states:

- what was measured, and the script line that measures it;
- the consequence;
- a recommendation: fix in Phase 4, defer to Phase 5 or 6, or post-1.0;
- whether the fix is visible to users. A user-visible fix breaks the API, the CLI or the schema
  (F4, G6).

The measurements come from a script under `validation/` or `docs/scripts/`, chosen by WP35's plan,
which the report's numbers cite.

Proposed identifiers:

- **VER-61, the layering guard.** A Tier-1 AST walk over `src/nanopnp/` asserts the subpackage
  import relation that the report records as accepted, in both directions. A new edge fails it,
  and so does a removed edge left unrecorded. It needs no new dependency (G1). Oracle: the
  report's matrix; fed a synthetic violating import, the guard must fail.
- **VER-62, the number-stability golden.** WP35 records QoIs that the gated walks already compute
  on `v0.4.0`'s tree. Among them are the 2WCD charged walk's Na⁺ and Cl⁻ currents. Example 05's
  solve is `slow`, recorded and not gated, so it cannot feed the golden; WP35 D11 lists the gated
  walks that do. WP35 argues the 10⁻⁸ relative tolerance from a rerun on every CI platform, and the
  predicted spread is below 10⁻¹⁰. The assertions attach to existing tests, by the §7.6 lever of
  shared work (G10).
- **VER-63, the findings-log check.** It is a Tier-1 parse of every findings log under `docs/`
  (G4). It refuses:
  - a malformed row;
  - a duplicate id;
  - a ruling pointer that resolves to no §8.2 row and no plan;
  - once the header is `closed`, a status that is not terminal.

  Oracle: it must fail on constructed bad logs.

No Tier 3 leg. Ends with the author ruling every `MOD-nn`, through `/phase-plan amend 4`.

> **Delivered, 5 October 2026** ([plan](wp35-modularity-exploration.md), to be tagged
> `v0.5.0-alpha.1`). The [report](../project/modularity.md) logs 17 findings in
> [modularity-findings.md](../project/modularity-findings.md), header `open`: 2 high (MOD-01, the
> missing `key()`; MOD-10, no §5.4.1 interface), 7 medium and 8 low, measured at `97f2b3d` by
> `validation/modularity.py`. VER-61 pins the 101 static and 27 string subpackage edges in
> `docs/project/modularity-layering.yaml`; VER-63 checks every findings log; VER-62's golden holds
> seven walks, recorded on a tree D15 shows computes as `v0.4.0`, with zero drift on a Linux rerun.
> Every later package keeps all three green, edits the YAML with any edge it moves, and re-pins the
> golden only by a G10 ruling. Next: the author rules each `MOD-nn` through `/phase-plan amend 4`.

### Refactor packages — Provisional

They wait on the rulings of `MOD-nn`. `/phase-plan amend 4` turns each accepted finding, or a
group of them, into a package with a number and identifiers. User-visible changes are batched where
the rulings allow, so that one schema identifier, `nanopnp/case/v0.5`, and one list of breaks
carry them. Each package:

- keeps VER-61 green, updating the accepted relation in the same commit as the code;
- keeps VER-62 green (10⁻⁸ on a recorded mesh);
- lists each break and its migration in `CHANGELOG.md`;
- carries the shell along (QR-11, VER-43, VER-60).

> **Amended, 5 October 2026.** The author ruled every `MOD-nn` (§8.2.8). The accepted findings are
> WP36 to WP40, below, in the order H8 rules. The rules above apply to each. No refactor moves the
> schema identifier: H7's three keys widen their value sets (the §5.3.1 NOTE). `MOD-11` is not
> among them. It waits for the sessions and lands with the fixes (H2).

### WP36 — The stage protocol and the walk (MOD-01, MOD-02, MOD-12; FR-27)

Plan: [wp36-stage-protocol-and-walk.md](wp36-stage-protocol-and-walk.md).

`key()` joins the `Stage` protocol in `core/stages.py`. `MaterialsStage` and `CaseStage` define it,
returning the hash `run` would, and the two `# type: ignore[attr-defined]` calls go
(`validation/comsol.py`, `gui/assess.py`). The facts the walk now keeps in its own lists move into
the registry entry: whether a stage takes a workspace, takes the store, or has a payload, and its
progress weight. `io/run.py` derives `PIPELINE`, `PAYLOAD_FREE`, `WORKSPACE_STAGES`,
`STORE_STAGES` and `_WEIGHTS` from the registry. `selected_stages`' drop rules are case logic and
stay, and the plan decides where `STRUCTURE_STAGES` sits. `test_public_api.py` gains the `MOD-12`
assertion that `PUBLIC` equals its `TYPE_CHECKING` mirror.

Break: `nanopnp.Stage` gains `key`, so a stage written outside the package must define it
(`CHANGELOG.md`, F4). `registered_stages()` descriptions gain fields, which is additive.

**VER-64, stage conformance** (proposed). A Tier-1 check that every registered stage class defines
`name`, `describe`, `key` and `run` with the protocol's signature, read through
`validation.modularity.stage_conformance`, and that every stage collection the walk uses is derived
from the registry. Oracle: a synthetic stage without `key` is refused, and so is a registry entry
missing a fact. VER-62 must show zero drift: the walk's order does not change.

> **Delivered, 5 October 2026** ([plan](wp36-stage-protocol-and-walk.md), to be tagged
> `v0.5.0-alpha.2`). `MOD-01`, `MOD-02` and `MOD-12` are `fixed`. `Stage.key(inputs)` is on the
> protocol, and `StageDescription` carries six required facts: `takes_workspace`, `takes_store`,
> `key_is_artefact`, `weight`, `needs_section` and `optional_inputs` (D13, from the review).
> A stage whose case drops a required input is not walked. The walk is registration order, read live by
> `core.stages.walk_order()`, with `case` registered first. `register` refuses an input not
> registered before the stage and a weight that is not finite and positive. `io/run.py` keeps no
> stage set (VER-64), and `STRUCTURE_STAGES` became `needs_section`. VER-62's golden holds, and
> VER-61's relation is unchanged. Inherited constraints:
> - a new stage declares its facts and defines `key`;
> - a test that registers a stage restores the registry.

### WP37 — The cycle cuts outside `io`, the exit codes, and the backend guard (MOD-03, MOD-05, MOD-10; QR-13)

Plan: [wp37-cycle-cuts-exit-codes-backend-guard.md](wp37-cycle-cuts-exit-codes-backend-guard.md).

The single-import cuts of `MOD-03`'s table that do not start in `io`: `charge → mesh`,
`charge → physics`, `geometry → density`, `materials → charge`, `materials → density`,
`materials → mesh`, `mesh → materials`, `mesh → solve` and `physics → mesh`. With them, the
wall-distance solve leaves `mesh/distance.py`, taking `mesh → physics` with it. Its new home must
not make the corrections in `materials/` import upward. The plan decides it, and if no move does,
that edge is reported back (H6). The exit classification and codes of `cli/errors.py` move to
`core` (`MOD-05`), which is their one home (§8.2.8 H12). VER-47's codes and `test_cli.py`'s table do not change.
Each removed edge leaves `modularity-layering.yaml` in the same commit.

**VER-65, the backend guard** (proposed; H3). A Tier-1 check that the set of subpackages importing
`ngsolve` or `netgen`, in any of the four kinds, equals a set recorded beside the layering. A
subpackage that gains the import fails, naming its module and line. A recorded one that loses it
fails until the record shrinks. Oracle: an `import ngsolve` substituted into `structure/` is
refused. QR-13's Appendix A row names it.

> **Amended, 6 October 2026** (§8.2.8 H11; [plan](wp37-cycle-cuts-exit-codes-backend-guard.md)).
> Measured at `a346419`, the nine edges above and WP38's split leave a `top` cycle of five, through
> `geometry ↔ mesh` and `physics ↔ solve`. The author ruled that WP37 cuts the `top` edges that
> point up the order, outside `io`: `charge → physics`, `charge → materials`, `geometry → mesh`,
> `mesh → materials`, `mesh → physics` and `mesh → solve`. `charge → mesh`, `geometry → density` and
> `physics → mesh` point down and stay. The solver kernel (`gates`, `linear`, `newton`) and the
> axisymmetric measure move to a new subpackage, `numerics/`, after `mesh` in the order. The
> wall-distance solve goes to `physics`. VER-65's set starts at twelve, and VER-61 gains a recorded
> list of upward `top` edges, which WP38 and WP39 shrink.

> **Delivered, 6 October 2026** ([plan](wp37-cycle-cuts-exit-codes-backend-guard.md), to be tagged
> `v0.5.0-alpha.3`). `MOD-05` is `fixed`; `MOD-03` stays `accepted` for WP38. `numerics/` holds
> `gates`, `linear`, `newton` and `measures`; the wall distance is `physics/distance.py`, the profile
> `geometry/profile.py`, the χ field `charge/dielectric.py`, the exit table `core/errors.py`.
> Measured on the tree, the only upward `top` edges are the nine into `io` and `cli → nanopnp`, and
> without `io`'s edges the `top` relation is acyclic. VER-65 pins twelve backend subpackages and
> VER-61 the `upward:` list. VER-62's golden holds. Inherited constraints:
> - `upward:` only shrinks, and `backend:` grows only by the author's ruling;
> - a cut removes a dependency; a deferred import is not a cut (D12);
> - WP39's linear-solver registry lands in `numerics/linear.py`.

### WP38 — The `io` split (MOD-04, MOD-13 for `io/case.py`, MOD-15, and `io`'s cuts of MOD-03)

Plan: [wp38-io-split.md](wp38-io-split.md).

`io` splits into a base, holding the artefact types, the store, the defaults and the resolved-case
types, imported downward only, and an assembler, holding resolution, the walk and reproduction,
which imports the stages. `io/case.py`, at 3,160 lines, divides along the same line. `core/stages.py`'s
`TYPE_CHECKING` import goes to the base or to `core` (`MOD-15`). `io`'s three edges, `io → charge`,
`io → materials` and `io → mesh`, are cut. A registry check that the schema makes today, such as
`physics.model` against `physics/models.py`, moves to the assembler. The plan decides whether the
base is a new subpackage, which amends §5.1 and `CLAUDE.md`'s structure list in the same PR, or a
module of `core`. `PUBLIC` names keep their meaning, and internal paths are not API (IF-01).

No new identifier: VER-61 records the new relation, and VER-62 must show zero drift.

> **Amended, 6 October 2026** (§8.2.8 H12; §8.2.9 I3). WP38 also resolves four review items:
> - REV-03: the solution-field names get one home, in the base;
> - REV-27: `nanopnp validate` runs the checks the assembler makes, the inf-sup check among them;
> - REV-54: the `MOD-12` assertion compares the module each mirrored name comes from, as well as
>   the name, so a module the split moves cannot leave the mirror pointing at the old one;
> - REV-63: the walk visits only the input closure of the requested stage, so `protonation` no
>   longer walks through meshing. VER-64's derivation from the registry is kept.

> **Delivered, 6 October 2026** ([plan](wp38-io-split.md), tagged `v0.5.0-alpha.4`).
> `io` is the base, importing only `core` at run time: the schema, the case paths, the resolved
> types and the field vocabulary. `pipeline/` is the assembler: loading, resolution and its checks,
> the walk and reproduction. The IF-07 export is `post/export.py`. A stage is handed
> `StageInputs.resolved` and only the artefacts it declares, and a walk runs its target's input
> closure. `MOD-03`, `MOD-04`, `MOD-13` (its `io/case.py` part) and `MOD-15` are `fixed`, as are
> REV-03, REV-27 (with `nanopnp validate case`, by the author's ruling), REV-54 and REV-63. VER-61's
> only upward `top` edge is `cli → nanopnp`, VER-65 pins eleven backend subpackages, and VER-62's
> golden and every artefact key hold. Inherited constraints:
> - WP39's registries replace the three registry checks in `pipeline/checks.py`;
> - a stage reading an upstream artefact declares it, and `undeclared_reads` refuses one that does
>   not (VER-64);
> - `stored_upstream` keys the closure of the stage it feeds, never a walk to `materials`.

### WP39 — The backend registries (MOD-06, MOD-07, MOD-16; ADR-002, QR-14)

Plan: [wp39-backend-registries.md](wp39-backend-registries.md).

The mesher, the linear solver and the stabilisation mode become registries, each in the shape of
the nearest existing one (H5). The linear solver's registry lives in `numerics/linear.py` (H11). `numerics.mesh.backend`, `numerics.linear.solver` and
`numerics.stabilisation` become strings, checked by the assembler against the registry as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and a missing extra is
still `MissingExtraError` at use. The schema's import of `numerics.linear` goes. That is the last of
the edges H6's target needs, so **this package measures the target**: if the `top` relation is
acyclic, VER-61 gains the assertion; if not, the residual cycle goes to the author with the cut it
would need. The generated case-file reference loses three enumerations, which `CHANGELOG.md`
records, and the shell's selectors read the registries (QR-11, VER-43).

**VER-66, extension by registration** (proposed). A test registers a stub mesher, linear solver
and stabilisation mode. A case naming each validates, and is dispatched to the stub, with no file
outside the test edited. An unregistered name is refused naming the registered ones (IF-03).
VER-24's classification is unchanged.

> **Amended, 6 October 2026** (§8.2.8 H12; §8.2.9 I3). WP39 also resolves four review items:
> - REV-05: where the facade's version and `PUBLIC` sit (WP37 D11);
> - REV-36: the Gmsh session no longer stops a logger it borrowed;
> - REV-37: a wheel that imports but fails to initialise is refused at use, naming the extra, as a
>   missing one is;
> - REV-38: the cleanup's `gmsh.model.remove()` cannot mask the error it follows.

> **Delivered, 6 October 2026** ([plan](wp39-backend-registries.md), to be tagged `v0.5.0-alpha.5`).
> The mesher (`mesh/meshers.py`), linear solver (`numerics/linear.py`) and stabilisation mode
> (`physics/stabilisation.py`) are registries in uniform shape; `MeshSpec.backend`,
> `LinearSpec.solver` and `NumericsSpec.stabilisation` are `str` validated in `pipeline/checks.py`.
> VER-66 verifies dynamic registration of stubs and refusal of unknown names. VER-61 asserts
> subpackage acyclicity on the `top` relation via Tarjan's algorithm (H6). `core/public.py` holds
> `__version__` and `PUBLIC`, emptying `upward:` and `deferred_upward:` in `modularity-layering.yaml`.
> `gmsh_backend._session` respects borrowed loggers, translates init failures to
> `MissingExtraError`, and runs non-masking sequential cleanup. `MOD-06`, `MOD-07`, `MOD-16`,
> REV-05, REV-36, REV-37 and REV-38 are `fixed`. VER-62's golden and all stage keys hold with zero
> drift. Inherited constraints:
> - The six registration functions are internal; public exposure is deferred to Phase 5 (`MOD-11`, REV-67);
> - `upward:` and `deferred_upward:` remain empty;
> - The `top` subpackage relation remains acyclic.

### WP40 — The stale refusals (MOD-14; IF-02)

Plan: [wp40-stale-refusals.md](wp40-stale-refusals.md).

The seven release-naming strings `MOD-14` lists are rewritten. Each refusal names its requirement,
and either the release that schedules it or that none does. The empty `_UNCONSUMED_INPUTS` loop
goes. Break: CLI refusal texts change. Exit codes do not (VER-47).

**VER-67, no stale release in a refusal** (proposed). A Tier-1 check over
`validation.modularity.version_literals` refuses a non-docstring string naming a release that is
already tagged. The plan fixes how "already tagged" is read without the network. Oracle: a synthetic
refusal naming `v0.2` is refused.

> **Delivered, 7 October 2026** ([plan](wp40-stale-refusals.md), to be tagged `v0.5.0-alpha.6`).
> VER-67 reads the tagged releases from `CHANGELOG.md`'s milestone headings, never git, refusing
> an empty or gapped read, and fails on any non-docstring string of `src/nanopnp` naming one
> (`validation/modularity.py`). The store form of `inputs.mesh`, `inputs.charge` and
> `inputs.eps_r` is refused at resolution and by the stage guards in one text per key
> (`io.case.stored_artefact_refused`); the mesh's names REV-62, deferred to v0.6, so
> `nanopnp validate case` now exits 3 on it. The NUM-20 refusals and the mesher's configuration
> reason name their requirements. `_UNCONSUMED_INPUTS` and `_UNREAD_CHARGE_KEYS` are gone.
> `MOD-14` is `fixed`; REV-62 stays open. No stage key moves (VER-62). Inherited constraints:
> - a string naming a release fails VER-67 once `CHANGELOG.md` records that release: REV-62's
>   text at `v0.6.0`, FR-21's at `v0.7.0`, unless each ships first;
> - a refusal names its requirement, and the release that schedules it or that none does.

### WP41 — The accuracy fixes (REV-06 to REV-09, REV-17, REV-26)

Plan: [wp41-accuracy-fixes.md](wp41-accuracy-fixes.md).

*Added, 6 October 2026* (§8.2.9 I1, I2). These are the register's physics and numerics items.
Each one is a property that a number depends on and that, today, is held only by convention.
Planned and implemented on Opus (`.claude/model-policy.md`).

- **REV-06.** The specification states the frame of a supplied `inputs.charge` or `inputs.eps_r`
  field beside a `structure:` case whose `centre_z_nm ≠ 0`. The code then applies the field in
  that frame, or refuses the combination, naming it (QR-12). This amends the §5.3.1 NOTE on
  `inputs:`.
- **REV-07.** The conservation gate and the Poisson source integrate an areal fixed charge by one
  rule (`charge/fields.py`). The plan shows which rule is right from the quadrature's own error
  on the synthetic alternating field. The gate then measures the charge the solve actually sees.
- **REV-08.** Newton's update test (`numerics/newton.py`) is measured per block on the gated
  walks. If the flow blocks pass with a looser relative convergence than the ion blocks, the test
  becomes per field, and NUM-16 is amended in the same commit. If they do not, NUM-16 gains a NOTE
  recording the measurement, and nothing moves.
- **REV-09.** A clamp of the ionic-strength driver is logged whenever it is applied
  (`materials/electrolyte.py`), as the per-species clamps already are. This is checked on a
  constructed multivalent parameter file, because no shipped file is multivalent.
- **REV-17.** A warm start compares the stabilisation provenance's settings and not its `note`
  prose (`solve/state.py`). A changed setting still refuses the warm start (VER-37).
- **REV-26.** `stabilisation_parameters` refuses, or names the mode, for a model that is not
  coupled (`solve/continuation.py`), and no longer returns an empty mapping.

**The golden.** Before changing any code, the plan argues a bound for each VER-62 QoI that REV-07 or
REV-08 can move. A drift within that bound is recorded, the clause is amended, and the golden is
re-pinned in one commit. A drift beyond the bound stops the package for the author (I4). No
other item may move the golden.

No new identifier: each fix's test is named for the requirement it holds (QR-03, NUM-16, PHY-13,
VER-37).

> **Delivered, 8 October 2026** ([plan](wp41-accuracy-fixes.md), to be tagged `v0.5.0-alpha.7`).
> Fixed-charge assembly shares an explicit order-8 quadrature rule with the conservation gate
> (`charge/fields.py`, `numerics/measures.py`, `physics/models.py`), matching to 4 × 10⁻¹⁶ (D2).
> Newton converges on a per-field relative-update criterion with an absolute residual floor
> (`numerics/newton.py`, D4). Supplied field model frame is declared and checked against mesh
> generation (`charge/fields.py`, `charge/stage.py`, D1). The ionic-strength correction driver clamp
> is logged and counted (`materials/electrolyte.py`, D7). Stabilisation provenance is moved to operator
> keys in warm start gating (`solve/state.py`, D8). Electrostatic models name stabilisation `none` and
> `LadderResult` refuses missing or non-mapping entries (`physics/models.py`, `solve/continuation.py`, D9).
> REV-06, REV-07, REV-08, REV-09, REV-17, and REV-26 are `fixed`. The number-stability golden is
> re-pinned within D3's and D5's bounds (I4). Inherited constraints:
> - Order-8 quadrature rule is shared between source assembly and gate legs;
> - Newton converges per field with floor ratio 10⁻⁶ beside absolute floor 10⁻¹²;
> - Every model's provenance names its stabilisation mode, parameters, and provenance.


### WP42 — The verification checks (REV-11 to REV-13, REV-23, REV-29, REV-34, REV-42, REV-44, REV-48)

*Added, 6 October 2026* (§8.2.9 I1, I2). Two checks that turn conventions into tests, and the test
hygiene that the register found.

**VER-70, no gate passes a NaN** (proposed; REV-11). A Tier-1 AST walk over the modules that
hold gates (`numerics/gates.py`, the charge and mesh quality gates, and the plan names the rest).
It refuses a comparison that a NaN would pass: `if value > tol: fail` with no finiteness test on
the same value. Oracle: a synthetic gate written that way is refused, naming its line, and the
same gate guarded by `math.isfinite` passes.

**VER-71, no inert case leaf** (proposed; REV-12). For every leaf of `CaseDocument`, a test shows
one of two things: a perturbation of the leaf changes the assembled forms or a stage key, or the
leaf is listed as provenance-only. The list is classified both ways, as VER-24's is. Oracle: a
leaf added to the schema and consumed nowhere fails. **REV-42** is the instance it finds: under
`pnp`, `variable_density` and `inertia` are refused, naming the model. That is a narrowing, so
the schema takes `nanopnp/case/v0.5`, and `CHANGELOG.md` gives the migration (G6).

With them:

- REV-13: example 06's key test covers stage 7;
- REV-23: the corrections test bounds each ion by its own range;
- REV-29, REV-34 and REV-48: the copied fixtures and constants each get one home;
- REV-44: the Stern-layer test stops re-solving the slab it drew.

These last are moves, not new assertions. The §7.6 NOTE's levers bound their cost.

> **Completed, 10 October 2026:** [wp42-verification-checks.md](wp42-verification-checks.md). Delivered as
> `0.5.0-alpha.8`. By the author's ruling VER-71 refuses every value a model never applies, not REV-42's two keys alone,
> and REV-66 is resolved with it.

### WP43 — The development loop (§8.2.10 J1 to J9; VER-73, VER-74 proposed)

*Added, 11 October 2026* (§8.2.10 J1). It makes the commit hook, the push gate and CI cheap
enough that later packages are not paced by them, and it moves delegation onto defined agents. It
covers:

- **the commit hook** (J2): the fast checks, then a test-impact selection. Its tool (for example
  pytest-testmon, or a map derived from coverage) is chosen by the plan from a measurement, and it
  enters the lock. A change it cannot map falls back to the development selection;
- **the push gate** (J3): it runs once per push, in the background, and reports only its failures. A
  follow-up fix re-runs the affected tests, with changed-line coverage over them. The suite is made
  cheaper by §7.6's four levers, and each changed test names the lever it uses:
  - the 2WCD seeds and the meshes shared across workers through the store;
  - workers balanced by recorded durations, in place of `--dist loadfile`'s long poles;
  - cheaper coverage collection;
- **CI** (J4):
  - the pull-request leg and the post-merge platform legs;
  - sharding by recorded durations;
  - timeouts on every job, trimmed installs and a cached apt step;
  - skipping the ubuntu leg on `main` when the merged tree equals the head that passed;
  - the nightly runs on 3.11 to 3.13;
  - the release matrix;
  - the names of the required checks;
- **Python 3.14** (J5): uv's pin, after VER-62 holds at round-off on 3.14;
- **the roster and the skills** (J8): `.claude/agents/`, with the model policy amended for Haiku.
  The skills and agent files are made leaner, path-scoped rules are introduced, and a usage script
  reports a session's tokens, compactions, gate minutes and agent spawns;
- **the plain summaries** (J9): `## In brief` in `/phase-plan`, `/wp-plan` and `/wp-implement`,
  and in the pull-request body they write;
- **the clauses J2 to J9 amend**: §7.6's table and NOTEs, with its new budget NOTE; `CLAUDE.md`'s
  *Setup* and *Commands*; and `knowledge/07-software-stack/index.md`'s gate timings.

Proposed **VER-73**, the loop's budgets: CI's duration report holds each selection within its
recorded budget plus the argued margin. Its oracle is a budget recorded below the measured
duration, which must fail. Proposed **VER-74**, the soundness of the test-impact selection:

- a change planted in a `src/nanopnp` function selects every test that executes it;
- a change to a file the tool cannot map selects the development selection.

Both are Tier 1.

Its budgets are measured on its own tree (J7):

- the commit hook within 60 s on a one-module change;
- the push gate within 5 minutes on 4 cores;
- the pull-request critical path within 6 minutes.

The token figure, at least 30 % fewer tokens read before code, is measured on WP46's
`/wp-implement` against WP42's, and reported in WP46's Outcomes. Until WP43's new hook is committed,
its own commits still run the old gate.

Its `/wp-plan` decides the impact tool, the shard count, VER-73's margin, the roster's files and the
order of the switch. Most items are `[any]`. Three are `[Opus]`: VER-62 on 3.14, any coarsening
under the third lever, and the soundness argument of the selection. Tagged `v0.5.0-alpha.9`.

> **Amended, 12 October 2026** (§8.2.10 J10 to J12), at its `/wp-plan`: [wp43-development-loop.md](wp43-development-loop.md).
> The `extended` walks leave the pull-request leg and run on `main`, nightly and before a release,
> because example 07 alone takes 5 to 8 minutes. Changed-line coverage is measured over the
> development selection. The token figure is the fixed reading set, 9,849 words for WP42. The push
> gate's 5 minutes is a predicted miss (6.5 to 8 minutes), reported at the close.

> **Superseded in part, 13 October 2026** (§8.2.11 L2, L3, L6, L8). The test-impact selection, the follow-up run, the
> budget enforcer and the agent framework are removed by WP44.

> **Completed, 12 October 2026:** [wp43-development-loop.md](wp43-development-loop.md), to be
> tagged `v0.5.0-alpha.9`. A commit runs the tests a recorded impact map selects (VER-74), the push
> gate runs once in the background and follows up on its selection, and a pull request runs one
> ubuntu leg in two shards; Python 3.14 is the working version, VER-62 holding on it. Of J7's
> budgets the pull request's critical path (225 s) and the reading set are met; the commit hook
> (136 to 234 s) and the push gate (555 s) are missed, REV-80 to REV-82 for the author's ruling,
> and the longest-first order is inert (REV-83).

### WP44 — Simplify the loop (§8.2.11 L2, L3, L6, L7, L8)

> **Delivered, 13 October 2026** ([plan](wp44-simplify-the-loop.md)). The commit hook runs the lock
> check, ruff, format, mypy and all of Tier 1 (187 to 220 s on 4 cores, against 90 s predicted); the push
> gate runs the suite with `--extended`, once, without coverage (509 s), and the push guard stays;
> pull-request shards are Tier 1 and Tier 2. The impact map, budget enforcer, duration record, agent
> guard, roster test, `model-policy.md` and two agents are deleted; VER-73 and VER-74 are withdrawn;
> VER-72 (g) caps plans at 1,500 words and six decisions. L4's rule is written down (D101 to D107,
> D417 off); the tree is WP45's. Live: `gate.sh` is 561 lines, not 300 (the push guard's recognition is
> 273); a pull request's critical path was 194 s on its first CI run. REV-80 and REV-81 are fixed.

*Added, 13 October 2026.* The simplest gate that still checks for regressions and expected
behaviour, and plans a session can afford. Tag `v0.5.0-alpha.10`. It does:

- **commit hook** (L2): lock check, ruff, format, mypy and all of Tier 1; delete `tests/impact.py`,
  the map, `test_impact_selection.py` and VER-74;
- **push gate** (L3): lint, types and the whole suite with `--extended`, no coverage, in the
  background, with the push guard (open decision below); delete the follow-up, `durations.json`
  ordering, `ci_budget.py`, `budgets.yaml`, the file ceiling and VER-73; `gate.sh` falls to about
  300 lines; CI keeps its pull-request leg in two shards by the simplest split, and diff-cover
  enforces changed-line coverage there;
- **agents** (L6): delete the guard hook, the roster test, `reading_set.py`, `usage.py` and
  `model-policy.md`; the rule is Haiku for easy items, Sonnet by default, Opus after Sonnet fails;
  the `[Opus]` marks go; `test_agent_roster.py`'s In brief check moves to a small plan-shape test;
- **plans** (L7): the skills cap a WP plan at 1,500 words and six decisions, drop per-item Design
  sections and plan-time planned tests, and mark compaction checkpoints; a test checks the cap on
  plans from WP44 on;
- **clauses** (L2, L3): §7.6's table and NOTEs, Appendix A, `CLAUDE.md`, `CONTRIBUTING.md` and
  `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md`, in step.

REV-80 and REV-81 close by removal. Its numbers are reported against these predictions, none
enforced: commit hook about 90 s on 4 cores; push gate 8 to 9 minutes; pull-request critical path
under 6 minutes. A miss is reported with its cause and the author rules (L8). Items are `[any]`.

### WP45 — The prose strip (§8.2.11 L4, L5; VER-75)

> **Delivered, 14 October 2026** ([plan](wp45-prose-strip.md)). Docstrings and comments are 10.6 % of
> `src/nanopnp` (from 33.0 %; predicted at most 10 %) and 2.1 % of `tests/` (from 18.8 %; at most 3 %).
> `same_tree.py` proved every commit changes no instruction. Every public function, class and method
> keeps a condensed docstring (L4 as amended after item 19); tests keep none. VER-75 (a) and (b) are
> `test_prose_share.py`, ceilings 11.62 % and 3.14 %. 33 fresh workers, one redo, no escalation (L9).
> Facts found nowhere else moved to `knowledge/`. The review's REV-93 to REV-97 are fixed, REV-91 deferred and REV-92 declined (§8.2.11 L10).

*Added, 13 October 2026.* Tag `v0.5.0-alpha.11`. The rule itself (`python.md`, `pyproject.toml`'s docstring
rules, `CONTRIBUTING.md`) is WP44's. The tree, one commit per subpackage, by per-module agent
passes (Haiku for `tests/`, Sonnet for `src/`, Opus only on a failure), each followed by the
syntax-tree check with docstrings removed; each subpackage goes to a fresh worker sub-agent while the main
session keeps only the plan and the log (§8.2.11 L9, a trial whose session cost is compared with WP44's); a subpackage whose check differs is reverted and
redone. Checkpoints: after each subpackage. The reference pages are rebuilt strict. Proposed
**VER-75**: the docstring and comment share of `src/` stays at or below its measured value plus
1 point; the oracle is a docstring added to a private function. Prediction: `src/` at most 10 %,
`tests/` at most 3 %, from 32 % and 18 %. A miss reports the shares by subpackage and the author
rules whether to pass again or re-argue the figure by amendment. VER-62 and every test are
unchanged. Items are `[any]`.

### WP46 — The small fixes (REV-14 to REV-16, REV-18, REV-19, and eleven low items)

> **Delivered, 14 October 2026** ([plan](wp46-small-fixes.md)). Fifteen `REV-nn` rows are `fixed`, each
> with its test (VER-26, VER-29, VER-48, VER-49, VER-53, VER-54, VER-25 for the workspace). The stage-6 key
> leaves λ_D out (`WallSize.key()`), so a salt sweep below 1.5 M meshes once; netgen's key golden is
> re-recorded. `Store.put` publishes one complete entry by rename. A stage without a workspace raises
> `MissingWorkspaceError` (a break, listed in `CHANGELOG.md`); the plan writes into the workspace itself
> rather than a fresh directory under it. Stage 1 refuses an empty trajectory, a repeated Cα and a chain
> split across the box (1.0 nm; the deposited 2WCD's largest consecutive pair is 0.3856 nm). REV-24
> measured no duplicate. The new `pipeline → density` edge is in `modularity-layering.yaml`.
> Live constraint: `chain_characters` raises `EnsembleFormatError` (exit 4).

> **Amended, 11 October 2026** (§8.2.10 J1). This was WP43, and is now **WP46**, after the
> development loop. Its scope is unchanged.

*Added, 6 October 2026* (§8.2.9 I1, I2). Local fixes, each with its own test, and none moving a
number:

- **REV-14**: `density/grid.py`'s `.npz` carries the origin and spacing, and `charge/stage.py`'s
  workaround goes;
- **REV-15**: example 05 writes `#SBATCH` values as sbatch reads them, and refuses a value it
  cannot pass;
- **REV-16**: below the concentration at which λ_D stops changing the wall size, the stage-6 key
  no longer carries λ_D, so a salt sweep meshes once. The key changes, and VER-62 compares
  numbers, not keys;
- **REV-18**: `Store.put` (`io/store.py`) is made atomic, write to a temporary file and rename,
  and a test races two writers;
- **REV-19**: a zero-frame trajectory is refused, naming the file, and duplicated Cα keys in one
  chain are refused rather than overwritten;
- **REV-24**: the SI-expression build is measured, and its duplication removed if it is there;
- **REV-25 and REV-55**: a post stage or a stage with no workspace writes its scratch to a
  workspace it is given, never to the process-default store or `mkdtemp`;
- **REV-40**: a density map with no unit marker, or one written in nm, is refused (§8.2.2 B10);
- **REV-43, REV-49, REV-50 and REV-51**: each duplicate gets one home, and the redundant reopen
  goes;
- **REV-57**: `frame_times` reads the times without decoding the coordinates, and a chain split
  across the periodic box is refused (QR-12);
- **REV-59**: `attribute_to_construction` refuses a lax comparison, saying that, and does not
  raise `MissingPlaneError`.

The plan may give the purely mechanical items to Sonnet. REV-16's key and REV-57's gate stay on
Opus. No new identifier.

> **Planned, 14 October 2026** ([plan](wp46-small-fixes.md)). The author ruled three choices: a
> stage given no workspace refuses to write scratch (a break, in `CHANGELOG.md`); only DCD frame
> times are read without decoding; a map written in nm is refused by the stage-2 spacing range,
> with no unit marker. The behaviour is written into the §5.3.1 NOTEs on `numerics.mesh` and
> `structure:`, the IF-05 and workspace-locality NOTEs, and VER-26, VER-29, VER-48, VER-49, VER-53
> and VER-54, in the plan's commit.

### WP47 — The OKF bundle and its checks (§8.2.7 G12; VER-68)

> **Delivered, 14 October 2026** ([plan](wp47-okf-bundle.md)). `knowledge/` is a bundle of 121 concepts
> in ten directories: a header on each (a closed list of 15 types, sources, `generated`, `verified`),
> an `index.md` per directory, `log.md` and `pending.yaml`. VER-68 is `test_okf_bundle.py` over
> `validation/okf.py`: each refusal on a constructed bundle, the real tree, every tracked address,
> and the heading ids against the docs build. 69 claims name a test; 361 are pending, the ceiling
> (314 `[tested: pending]`, 47 `[verified]` without a source). Live constraints: a durable fact is a
> concept with a log line; a Markdown file that cites `knowledge/` runs the tests (`prose-only.sh`);
> a heading carrying a marker has an explicit id. REV-103 is open for WP48.


It waits on the refactors (G5). F6 and the input note's K1 to K11 bind this package. It covers:

- the bundle: one concept per `##`, in a directory per file;
- every `knowledge/0N §x` citation, history included, rewritten to a bundle path;
- the six checks of the input note as one Tier-1 test, which carries G3's committed list of
  unbacked claims. Executable `[verified]` claims join that list (G8).

Its `/wp-plan` puts open questions 3 to 7 to the author (G9). `generate.py` has to recurse.

> **Amended, 5 October 2026.** This is **WP41** (§8.2.8 H8), after WP40. The F6 check is proposed
> as **VER-68**, with the six refusals of the input note, *What the package SHALL check*. Its
> oracle is a constructed bundle that breaks each rule in turn. The bundle is written against the
> test node ids WP36 to WP40 leave, which is G5's reason for the order. Open questions 3 to 7
> stay with this package's `/wp-plan` (G9).

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP46**, after WP43. It is written against
> the test node ids that WP36 to WP43 leave. VER-68 stays its proposed identifier.

> **Amended, 11 October 2026** (§8.2.10 J1). This is now **WP47**, written against the test node
> ids that WP36 to WP46 leave.

> **Planned, 14 October 2026** ([plan](wp47-okf-bundle.md)). The author ruled the note's questions 3 to 7
> (§8.2.7 G12); VER-68 is in Appendix A.

### WP48 — The OKF backfill (§8.2.7 G3, G8; REV-103)

> **Delivered, 17 October 2026** ([plan](wp48-okf-backfill.md)). Backfilled all 361 open claims across
> the bundle, audited all 56 verified markers, populated and verified `tested_with` on all 17 library
> behaviour concepts, and added assertions in existing suites and new Tier-1 suites (`test_knowledge_arithmetic.py`,
> `test_library_behaviour.py`, `test_ngsolve_traps.py`). `pending.yaml` is empty (`{}`), `CEILING` is 0,
> `[tested: pending]` is refused unconditionally in `okf.py`, `VER-68` is amended, and `REV-103` is closed.

It waits on the bundle package. Every listed claim gets its test: a Tier-1 or Tier-2 test that
re-establishes the claim, named inline. A library-behaviour concept gains `tested_with`. At the end
the list is empty and the check refuses any unbacked `[tested]` (G3). The new tests' cost is bound
by the §7.6 NOTE's levers. A claim whose test fails is a finding about the knowledge base, never a
reason to loosen the test.

> **Amended, 5 October 2026.** This is **WP42** (§8.2.8 H8). It claims no new identifier: each new
> test is named for the claim it backs, and VER-68's list reaching empty is the package's end.

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP47**. A claim about Newton's
> convergence test or the areal-charge quadrature is backed against WP41's tree, not the one before it.

> **Amended, 11 October 2026** (§8.2.10 J1). This is now **WP48**.

> **Planned, 15 October 2026** ([plan](wp48-okf-backfill.md)). Backfills all 361 open claims:
> 100 pending test-evidence markers audited, all 56 verified markers classified (including nine
> sourced markers outside the ledger), and all 17 library-behaviour concepts given checked
> `tested_with` metadata. Historical measurements are separated from current properties; the
> opening inventory establishes test cost. The package ends with the full evidence audit complete,
> `pending.yaml` empty and `CEILING = 0` (G3, G8; REV-103).

### WP49 — The cost study (§8.2.12 M2; REV-112, REV-113; VER-76)

> **Delivered, 18 October 2026** ([plan](wp49-cost-study.md), to be tagged `v0.5.0-alpha.15`). Measured
> A1, A8 and A16 with a committed script (`validation/costs.py`; `docs/project/cost-study.json`): stage 1
> projects to 1.14 GB at 1,000 frames (limit 4 GB), form building is at most 0.33 % of stage 10 (limit
> 5 %), store IO at most 0.51 % of a cold walk (limit 10 %); the fixed harness gives at most 0.54 % and
> 0.69 %, and the close re-runs it (REV-116). None is over, so nothing is fixed and
> VER-62 is untouched. VER-76 exports the case schema as JSON Schema, published as
> `reference/case.schema.json`. REV-112 and REV-113 are `fixed`. Main's macOS and Windows CI failure
> (no ngsolve stub file in those wheels) is fixed in the same package.

Added on 18 October 2026 (§8.2.12 M2, M4). It waits on WP48's merge, and the protocol waits on it.
It measures three costs an external review suspected, on a 4-core container, on the quick-start pore
and on the prepared 2WCD, with a committed script whose numbers the plan's Outcome and the
end-of-phase report quote. It fixes a cost only if it crosses its threshold, which is registered
here, before any measurement:

| Cost | Measured as | Fixed if | Prediction | The fix |
|---|---|---|---|---|
| A1, the ensemble in memory | Stage 1's peak resident memory on 2WCD's ensemble, projected linearly to 1,000 frames | Over 4 GB | About 1 GB: the array is about 0.7 GB at 1,000 frames of 55,000 atoms | Align and write frame by frame, so peak memory holds a frame, not the ensemble; the artefact's bytes and key unchanged |
| A8, forms rebuilt per rung | Share of stage 10's wall time spent building symbolic forms, not assembling them, over both NUM-18 ladders | Over 5 % | Under 1 % | Build the forms once per mesh, with the rung's scales as parameters |
| A16, stages read back from the store | Share of a cold walk's wall time spent serialising and reading artefacts between stages | Over 10 % | Under 5 % | Hand a stage's in-memory result to the next, the store still written and every key unchanged |

It also exports the case schema as a JSON Schema, generated from the case document's own model and
published by the documentation build. Proposed **VER-76**: the export's leaves equal those
`case_fields` walks, in both directions, so a field added to one and not the other fails; its oracle
is a substituted schema with one extra leaf, which must fail.

A fix changes no number: VER-62 holds at 10⁻⁸ on a recorded mesh, and a miss is reverted (G10).
A fix that does not fit one pull request is carried as a `REV-nn` row and ruled into a fix package.
The package claims VER-76 and sets REV-112 and REV-113 `fixed`. Tag `v0.5.0-alpha.15`.

### WP50 — The test scope (§8.2.13 N1 to N5)

> **Delivered, 19 October 2026** ([plan](wp50-test-scope.md), to be tagged `v0.5.0-alpha.16`). N1's
> rule is written once in `CLAUDE.md` and `.claude/rules/python.md`, and the skills, `CONTRIBUTING.md`,
> the pull-request template and `tests/README.md` follow it; `/wp-ship` deletes off-scope tests before
> `/code-review` (N5). The coverage job and `diff-cover` are gone (N2). `nightly` replaces `extended`;
> every push runs example 01 and example 02's ePNP-NS leg with their VER-62 goldens, and a failed
> nightly run opens an issue (N4). VER-63, VER-67, VER-68 and VER-75 are withdrawn, VER-72 keeps its
> import guard, and §7.1 to §7.3, §7.6, §8.1 and Appendix A follow (N3). 378 Tier 1 tests and
> `pending.yaml` are deleted; 31 knowledge markers are retargeted. The per-push run takes 201 s
> (1,505 tests). VER-61, VER-62 and VER-65 hold. REV-117 carries the tooling left without tests.

Added on 18 October 2026 (§8.2.13 N6). It waits on WP49's merge, and the protocol waits on it. The
design is `docs/superpowers/specs/2026-10-18-test-pruning-design.md`. It:

- writes N1's rule once in `CLAUDE.md` and `.claude/rules/python.md`, and replaces every instruction
  to write a test per item, per identifier or per changed line in the skills, `CONTRIBUTING.md`, the
  pull-request template and `tests/README.md`;
- removes the coverage job and `diff-cover` (N2);
- replaces `extended` with `nightly`, sets the per-push selection of N4, keeps examples 01 (under 60 s)
  and 02's ePNP-NS pore on every push, and makes a failed nightly run open an issue;
- deletes the tests outside N1, area by area, keeping a smoke test per entry point;
- withdraws N3's identifiers, amends §7.1 to §7.3, §7.6, §8.1 and Appendix A, and retargets the
  knowledge base's markers;
- adds N5's reviewer step to `/wp-ship`.

No tolerance is loosened, and no kept test is weakened. VER-62 holds at 10⁻⁸ on a recorded mesh on the
tests that remain. It claims no new identifier. Tag `v0.5.0-alpha.16`.

### WP51 — The plotting library and the notebooks (FR-30; §8.2.14 P1 to P6; REV-123)

*Added, 22 October 2026* (§8.2.14 P1). It waits on WP50's merge, and the protocol waits on it. The
author asked for a figure of every part of the pipeline, to confirm by eye what each stage
produces, and for notebooks in which to test the API interactively. It delivers:

- **`plot/`**, a new subpackage after `post` and before `pipeline` (P3). Its data layer turns each
  artefact into arrays in SI units and the model frame. Its drawing layer, Matplotlib behind a
  `plot` extra and imported inside the functions that draw (P2), makes:
  - stage 1: the aligned atoms in (r, z);
  - stages 2 and 3: the density's section and the reduced map with its azimuthal variance (CON-04);
  - stage 4: the conditioned contour over that map;
  - stages 5 and 6: the regions and their boundaries, and the mesh with its size field and quality;
  - stage 7: the protonation states, the deposited charge and the dielectric field;
  - stage 8: the corrections against their declared driver (⟨c⟩ by default) and the wall distance;
  - stage 10: the fields, the Newton history and the continuation rungs;
  - stage 11: the quantities;
  - a sweep's collected curves.

  Fields are read through `post/export.py`'s sampling, so `plot/` imports no backend.
- **The display** (P6). `core.stages.register` takes an optional `figure=` dotted path, as it takes
  `extra=`, and every builtin stage declares one or sits on a recorded figure-free list. Every
  artefact and `RunResult` answer the `_repr_*_` display protocol: the figure with the extra
  installed, otherwise a text summary of schema, key and payload.
- **`notebooks/`**: marimo notebooks, plain `.py` files, one each for geometry, charge, solve and
  fields, and sweep (P5). Each walks the public API with figures and widgets. A `notebook` extra
  adds marimo, and the examples runner runs each as `python <notebook>.py` every night.
- **The clauses**: §5.1's table, `CLAUDE.md`'s structure list, `modularity-layering.yaml` and
  `LAYER_ORDER` gain `plot`, with no upward edge; `CHANGELOG.md` lists `register`'s new keyword and
  the extras.

Tests, by N1 (P4):

- a smoke test that draws every declared figure on examples 01 and 02 per push, and on examples 06
  and 07 nightly, and refuses a stage neither declaring a figure nor on the figure-free list;
- the data layer's unit and frame conversions, and a field sampled on a grid against `sample_at`;
- an architecture guard that `import nanopnp` and a walk load neither Matplotlib nor marimo;
- the notebooks, run nightly with their exit status as the oracle.

No figure is compared with a baseline image. VER-61 is re-recorded, and VER-62 and VER-65 do not
move. Its `/wp-plan` decides the public names (`nanopnp.plot`, and whether a name joins `PUBLIC`,
F4), the figure-free list, how a sweep's results reach `plot/` from below `sweep`, and the notebooks'
widgets. REV-123 becomes `fixed`. Tag `v0.5.0-alpha.17`.

> **Delivered, 22 October 2026** ([plan](wp51-plotting-and-notebooks.md), to be tagged
> `v0.5.0-alpha.17`). `nanopnp.plot`, behind the `plot` extra, draws a figure of every stage's artefact
> and of a sweep, from the stored artefacts alone; the stage registry declares each figure (`case` and
> `report` are figure-free), and `Artefact` and `RunResult` display themselves in a notebook. The solve
> now stores its Newton history, and the IF-07 export and the figures share one restore and sampling path.
> Four marimo notebooks (geometry, charge, solve, sweep) run headless every night. `plot` follows `post`
> in the layer order with no upward edge, and VER-61, VER-62 and VER-65 hold. The gate gains about 13 s.
> REV-123 is fixed. The author must look at every figure and notebook before the merge.
>
> *Planned, 22 October 2026.* Its decisions: no name joins
> `PUBLIC`; `case` and `report` are figure-free; a sweep is drawn from its `io` artefact's rows; each
> notebook has at most two widgets. Stage 8's line read "against ionic strength"; the driver is
> the one the electrolyte declares, ⟨c⟩ = (1/n)Σcᵢ by default and the ionic strength only where the
> corrections file says so (`Electrolyte.driver`), so the line now says so.

### WP52 — The documents: the specification and the plans split (§8.2.16 R2 to R4, R9, R10)

*Added, 22 October 2026* (§8.2.16 R1). It waits on WP51's merge. The author asked that a session read
the current specification by default and its history only on demand. It delivers:

- **`specification/`**, an OKF bundle beside `knowledge/`: one file per numbered section, §5 and §7 by
  subsection, an `index.md` per directory. `specification/history/` takes the dated §8.2.x tables and
  the superseded and withdrawn rows and NOTEs; each leaves a one-line pointer in the current text (R2).
- **The development-process section**: the rulings in force that have no clause of their own,
  restated once, each pointing to its ruling (R3).
- **`SPECIFICATION.md` as the entry point** and map from section and identifier to file;
  `clause.py`, `docs/scripts/generate.py` and `mkdocs.yml` reading the directory; anchored links in
  `docs/`, `knowledge/` and `.claude/` repointed; §11 and `CLAUDE.md` updated (R2, R9).
- **This plan restructured** to its current scope, its amendments moved to a record (R4).

No file under `src/` or `tests/` changes, so the gate is prose-only. No identifier is claimed and no
test is kept (N1). R10's two conditions are checked in the pull request, the line check by a one-off
script whose output goes into the Outcome. Its `/wp-plan` decides the file boundaries, the bundle's
`type` vocabulary, where this plan's amendment record lives and how the restated rows are listed.
Tag `v0.5.0-alpha.18`.

> **Amended, 22 October 2026** (§8.2.16 R11). At its plan the author added two workflow changes, which
> WP52 carries: the planning skills open the PR, and a plan may add up to 1,000 words of implementation
> details for a smaller model, names each item's executor and makes each compaction checkpoint a work
> item that ends the turn with a `/compact` prompt. The plan is
> [wp52-specification-and-plans-split.md](wp52-specification-and-plans-split.md).

### WP53 — The workflow: three skills with levels, workers, and a current checkout (§8.2.16 R5 to R7)

*Added, 22 October 2026* (§8.2.16 R1). It waits on WP52, whose layout its skills read. It delivers:

- **`/plan`, `/implement` and `/ship`**, each a short router over a shared core file and one file per
  level (`project`, `phase`, `amend` and `wp` for `/plan`; `wp` and `phase` for `/ship`), replacing
  `phase-plan`, `wp-plan`, `wp-implement` and `wp-ship`. R3's and R4's rules for rulings and plan
  amendments go into the planning levels (R5).
- **The worker pattern** in the implementing level, and the planning level's mark for the items that
  go to workers (R6).
- **The session-start hook's fast-forward** of a clean primary `main`, and its warning otherwise (R7).
- **The pointers**: `CLAUDE.md`'s *Implementation workflow* and *Commands*, `current.md`'s handoff
  rules, and every mention of the old names.

`steward` and the two agent files stay. No test is kept (N1). WP54 is the first package planned,
implemented and shipped with the new skills, and its sessions are the check. Its `/wp-plan` decides
the core file's contents, whether the old names stay as aliases, and the hook's behaviour on a
detached or diverged checkout. Tag `v0.5.0-alpha.19`.

### WP54 — The notebooks and figures revised (§8.2.16 R8)

*Added, 22 October 2026* (§8.2.16 R1). It waits on WP53, and on the author's document of comments
and notes on WP51's notebooks and figures, which its `/plan wp 54` reads. Its scope is what that
document asks (R8), new dependencies and changes below `plot/` included, each a decision of its plan.
WP51's rules carry unless that plan rules otherwise and amends FR-30 in the same commit: `plot/`
imports no backend; `import nanopnp` and a walk load no drawing or notebook library; every notebook
runs headless nightly; every stage declares a figure or is figure-free. A change to `PUBLIC` is decided
in `test_public_api.py` (F4) and listed in `CHANGELOG.md`. VER-61, VER-62 and VER-65 stay green. Its
plan claims its identifiers. Tag `v0.5.0-alpha.20`.

### User-testing protocol — Provisional

> **Planned, 19 October 2026** ([plan](wp55-user-testing-protocol.md)): five sessions, VER-69 on
> VER-46's runner, nightly.

> **Amended, 22 October 2026** (§8.2.14 P1, P5). This is now **WP52**, and it waits on WP51. Session
> 04, the Python API, is a marimo notebook in its own directory, using WP51's figures and display;
> the tester installs the `notebook` extra. Tag `v0.5.0-alpha.18`.

> **Amended, 22 October 2026** (§8.2.16 R1). This is now **WP55**, and it waits on WP54, whose
> notebooks session 04 is re-read against. Tag `v0.5.0-alpha.21`.

It waits on the OKF backfill. It writes:

- `docs/user-testing/protocol.md`, the protocol;
- scripted sessions over the physics, the numerics, the Python API and the command line. Each
  session is a task that a nanopore modeller would set, with the outcome expected and where to
  record surprise;
- the findings log, `docs/user-testing/findings.md`, `UT-nn`, header `open`.

Every script's commands and code run verbatim in the push gate (G7), by a test modelled on VER-46.
An agent dry run debugs the scripts and records nothing. The package ends when the author has the
protocol. **The sessions themselves are the author's**, and their findings are logged as they run.

> **Amended, 5 October 2026.** This is **WP43** (§8.2.8 H8). The execution test is proposed as
> **VER-69**: every command and code block of the session scripts runs verbatim in the push gate,
> on VER-46's pattern, under the §7.6 NOTE's levers. Its oracle is a script with a broken command,
> which must fail. The protocol includes a task touching `with_section` and stage registration, so
> that the sessions inform `MOD-11` (H2).

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP48**. VER-69 stays its proposed identifier.

> **Amended, 11 October 2026** (§8.2.10 J1). This is now **WP49**.

> **Amended, 18 October 2026** (§8.2.12 M4). This is now **WP50**, and it waits on WP49, the cost
> study, as well as the OKF backfill. Tag `v0.5.0-alpha.16`.

> **Amended, 18 October 2026** (§8.2.13 N4, N6). This is now **WP51**, and it waits on WP50. Its
> scripts run nightly, not in the push gate, and VER-69 is proposed on that footing. Tag
> `v0.5.0-alpha.17`.

### Fix packages — Provisional

They wait on the sessions and on the author's ruling of each `UT-nn`. A second `/phase-plan amend 4`
plans them. The rules of the refactor packages apply: VER-61, VER-62, `CHANGELOG.md` breaks, the
shell following, and schema moves under `nanopnp/case/v0.5` (G6).

> **Amended, 5 October 2026.** They also carry `MOD-11`, decided by the author's ruling of the
> sessions' findings (§8.2.8 H2). Their numbers are assigned by the second amendment, from WP46 (H8).

> **Amended, 6 October 2026** (§8.2.9 I1, I3). They are numbered from **WP49**. They carry no review
> item that §8.2.9 placed elsewhere. An item a later review adds goes to them only by a ruling
> recorded in the register.

> **Amended, 11 October 2026** (§8.2.10 J1). They are numbered from **WP50**.

> **Amended, 18 October 2026** (§8.2.12 M4). They are numbered from **WP51**. They also take any
> cost WP49 measures over its threshold and cannot fix within its own pull request, by ruling.

> **Amended, 18 October 2026** (§8.2.13 N6). They are numbered from **WP52**, and their tests follow N1.

> **Amended, 22 October 2026** (§8.2.14 P1). They are numbered from **WP53**.

> **Amended, 22 October 2026** (§8.2.16 R1). They are numbered from **WP56**.

### Documentation increment 4 — Provisional

It waits on the fixes. It delivers §8.1's documentation increment for Phase 4:

- the modularity report in the site;
- the user guide, the API reference and the CLI reference revised against both logs, including a
  hand-written Python API page if the sessions show it is needed;
- every break of the phase listed with its migration (F4).

VER-45 and VER-46 gate it.

### The close package — Phase 4 closed, and the end-of-phase report

It comes last, and the first amendment gives it its number. It:

- resolves or carries each row of `## Open decisions`;
- confirms that every `MOD-nn` and `UT-nn` row is terminal, and sets both logs' headers to
  `closed`, so that VER-63 asserts closure from then on;
- re-runs the end-of-phase report's numbers on its own tree, never copying them from an Outcome;
- writes the report below, the `[0.5.0]` section of `CHANGELOG.md` and `CITATION.cff`'s version
  and date;
- updates `current.md` to point at Phase 5 (F5).

Its last commit on `main` is tagged `v0.5.0` alone (G11).

> **Amended, 5 October 2026.** The second amendment, not the first, gives this package and the
> documentation increment their numbers, after the fix packages (§8.2.8 H8).

> **Amended, 6 October 2026** (§8.2.9 I3). The close also resolves REV-47: it reports the push
> gate's serial and parallel durations on its own tree against WP33 D15's targets: at least 180 s
> of serial time saved, and no file over 90 s. It then states, in the end-of-phase report, whether
> each target is met, re-argued or retired. It also confirms that every `REV-nn` row whose ruling
> places it in a Phase 4 package is `fixed` (criterion 10).

> **Amended, 18 October 2026** (§8.2.13 N3). VER-63 is withdrawn: the close reads both logs and the
> register itself and records their closure in the report. REV-47's targets are retired by N4.

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| Opening study | Report, guard, no refactor | **Settled by the author, 5 October 2026** (§8.2.7 G1) |
| Refactor timing | All accepted refactors before the protocol | **Settled by the author, 5 October 2026** (G2) |
| OKF split, `[verified]` | Two packages with a ratchet; tests where executable | **Settled by the author, 5 October 2026** (G3, G8) |
| Findings record | In-repo logs, checked, with a closable header | **Settled by the author, 5 October 2026** (G4) |
| Sequence | As in *Work packages* | **Settled by the author, 5 October 2026** (G5) |
| Schema moves | As needed; the identifier names the release | **Settled by the author, 5 October 2026** (G6; the §5.3.1 NOTE) |
| Protocol | Executed by the gate; findings from the author's sessions only | **Settled by the author, 5 October 2026** (G7) |
| Number stability | Golden at 10⁻⁸ relative on a recorded mesh; on an unseen mesh, 10 × the measured spread between recorded meshes, capped at 10⁻³ | **Settled by the author, 5 October 2026** (G10); the mesh-moved tolerance **ruled by the author, 5 October 2026**, after CI's first run showed NumPy's SIMD dispatch moving a PDB-derived mesh (VER-62; WP35 D13 as amended). WP35 argues the figure from measurement, and a re-argued figure is a spec amendment |
| Close and tags | `v0.5.0` alone; the session tags if it can | **Settled by the author, 5 October 2026** (G11) |
| OKF open questions 3–7 | Preamble, root index, `type` vocabulary, `log.md`, docs site | **Open**, owned by the OKF bundle package's `/wp-plan` (G9) |
| Each `MOD-nn` | Fix in Phase 4, defer, or post-1.0 | **Settled by the author, 5 October 2026** (§8.2.8 H1 to H5, H7) |
| The coupling target | Acyclic `top` relation, or whatever the cuts leave | **Settled by the author, 5 October 2026** (H6). Measured by WP39 |
| QR-13 and `MOD-10` | Build §5.4.1, or restate QR-13 and confine the backend | **Settled by the author, 5 October 2026** (H3) |
| Refactor sequence | Stages first, or the `io` split first | **Settled by the author, 5 October 2026** (H8) |
| The base half of `io` | A new subpackage, or a module of `core` | **Settled by WP38's plan, 6 October 2026**: `io` is the base, directly above `core`, and the assembler is a new subpackage, `pipeline/`, in `io`'s old place in the order (WP38 D1) |
| The wall-distance solve's home | `physics`, `solve`, or reported back | **Settled by WP37's plan, 6 October 2026**: `physics/distance.py`, once the kernel is in `numerics/` (H11) |
| WP37's edge list, and `physics ↔ solve` | The named nine, or the edges pointing up the order; how the 2-cycle is cut | **Settled by the author, 6 October 2026** (H11) |
| Each `UT-nn` | Fix or defer | **Author**, through the second amendment |
| Phase estimate | §8.1's "Set by the phase plan" | **Settled by the author, 5 October 2026**: 3–5 weeks (H9; §8.1, §8.3). **Re-settled, 6 October 2026**: 4–6 weeks (§8.2.9 I5) |
| The review register's accepted items | At the second amendment, or before the OKF bundle | **Settled by the author, 6 October 2026** (§8.2.9 I1): WP41 to WP43, before WP46 |
| The development loop | Insert a package before the small fixes, and its scope | **Settled by the author, 11 October 2026** (§8.2.10 J1 to J5, J7 to J9) |
| Python 3.15 and lazy imports | Bump, add, or revisit | **Settled by the author, 11 October 2026** (J6): revisited under OPN-09 |
| The impact tool, the shard count, VER-73's margin, the roster's files | — | **Settled by WP43's plan, 12 October 2026** ([wp43-development-loop.md](wp43-development-loop.md) D2, D10, D11, D13), from measurement |
| The phase estimate after J1 | 4–6 weeks (I5), or a week more for WP43 | **Settled by the author, 12 October 2026** (§8.2.10 J12): 4–6 weeks, WP43 absorbed |
| The walks on a pull request; J7's token figure | — | **Settled by the author, 12 October 2026**, at WP43's `/wp-plan` (§8.2.10 J10, J11): the `extended` walks run after a merge; the figure is the fixed reading set |
| The remediation of WP43 | Two packages first; commit hook = Tier 1; push gate without coverage; the prose rule; agents retired; models; plan caps; no dollar gate | **Settled by the author, 13 October 2026** (§8.2.11 L1 to L8) |
| The agents after WP44 | Keep the physics reviewer and the log classifier, or more | **Settled by the author, 13 October 2026** (§8.2.11 L9): those two, the classifier on Haiku; WP45 trials a fresh worker per item |
| The push guard (refuse `git push` until the gate passed) | Keep, or drop with the rest of WP43's machinery | **Settled by the author, 13 October 2026**: keep, simplified; WP44's plan reports its size |
| Running fewer tests on commit, after WP44's measured 187–220 s | Keep all of Tier 1, or select | **Settled by the author, 13 October 2026**: keep all of Tier 1 (L2 stands); the time is reported, not enforced (L8) |
| The phase estimate after L1 | 4–6 weeks stands, or more | **Author, open.** Default: stands |
| Their grouping | By kind, two packages, or one per area | **Settled by the author, 6 October 2026** (I2): accuracy, verification, small fixes |
| `REV-23` to `REV-65` | Phase 4, Phase 5, Phase 6, post-1.0 or declined, each | **Settled by the author, 6 October 2026** (I3) |
| An accuracy fix that moves VER-62 | Stop (G10), pre-rule, or diagnose only | **Settled by the author, 6 October 2026** (I4): pre-ruled within a bound WP41's plan argues |
| REV-06's frame, and whether REV-08 makes NUM-16's test per field | — | **Settled by WP41's plan, 7 October 2026**, from measurement: a supplied field is in the model frame, and a declared other frame is refused (WP41 D1, amended in the plan's commit); the test becomes per field, and the relative residual test no longer closes a rung (WP41 D4, amended in its item's commit, I4) |
| `with_section`, `register` in `PUBLIC` | Add or keep out | Carried from WP34 D9 as `MOD-11`. **Accepted, and decided after the sessions** (H2), by the author's ruling, in a fix package |
| The architecture review of 18 October 2026 | Which claims to act on, the browser shell, where the study goes, the estimate | **Settled by the author, 18 October 2026** (§8.2.12 M1 to M5) |
| The Qt shell until the browser shell matches it | Keep it gated through v0.5 and until Phase 5 replaces it, or drop it earlier | **Settled by the author, 18 October 2026** (M3): kept. The In brief of 18 October invited a re-ruling |
| The test scope, its place and the estimate | What is tested, the coverage gate, the split, prevention, WP50 before the protocol | **Settled by the author, 18 October 2026** (§8.2.13 N1 to N7) |
| The plotting library and the notebooks | Their place in the sequence, the notebook form, the drawing library, the subpackage's place, the requirement and its tests, the display, the estimate | **Settled by the author, 22 October 2026** (§8.2.14 P1 to P7). P6 follows the author's instruction to build the most long-term viable design |
| WP51's public names | `nanopnp.plot` as a namespace, and whether any name joins `PUBLIC` | **Open**, owned by WP51's `/wp-plan`; a change to `PUBLIC` is decided in `test_public_api.py` (F4) |
| The notebooks on the documentation site | In documentation increment 4, or later | **Author, open**, at the second amendment. Default: on the site, after the sessions show which help |
| The documents and the workflow | The packages, the specification's home, current and history, the plans, the skills, the workers, the checkout, `knowledge/`'s scope, WP52's checks | **Settled by the author, 22 October 2026** (§8.2.16 R1 to R7, R9, R10) |
| WP54's scope | Bounded to `plot/` and `notebooks/`, or open | **Settled by the author, 22 October 2026** (R8): open, decided at its plan from the author's notes |
| WP52's file boundaries, `type` vocabulary and amendment record; WP53's aliases and the hook on a diverged checkout | — | **Open**, owned by WP52's and WP53's plans |
| The phase estimate after R1 | 4–6 weeks stands (P7), or 5–7 | **Author, open.** Recommendation: 5–7 weeks |
| WP49's thresholds | 4 GB, 5 %, 10 % | **Registered by this amendment**, 18 October 2026. A re-argued threshold is a plan amendment before the measurement, never after |
| NUM-07 order; the archive-dependent legs | — | **Phase 6** (E1, E4, F1). Not this phase's |
| OPN-04, OPN-08 | — | **Author, open.** Not on this phase's path |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| A ruling on every `MOD-nn` | The first amendment | **Given, 5 October 2026** (§8.2.8) |
| A ruling on every `REV-nn` left open | This amendment | **Given, 6 October 2026** (§8.2.9). A row a later review adds is ruled when it is added (H12) |
| A ruling on any residual cycle H6's target leaves, and on any subpackage VER-65's set would gain | WP37 to WP39, as they report it | The package stops at the edge and carries it. VER-61 and VER-65 stay red until the ruling is recorded |
| The `MOD-11` choice | The fix packages | `MOD-11` stays `accepted`, and VER-63 refuses the close |
| The scripted sessions, run by the author, with findings logged | The second amendment, then the fix packages | The phase waits. No agent session substitutes (G7) |
| A ruling on every `UT-nn` | The fix packages and the close | As for `MOD-nn` |
| A ruling on a WP41 drift beyond its argued bound | WP41, if it happens | The package stops at the fix and carries it, and VER-62 stays red until the ruling (I4) |
| Open questions 3–7 of the OKF note | The OKF bundle package's plan | That plan carries them as open and blocks on them |
| A ruling if VER-62 moves on Python 3.14 | WP43 | The interpreter stays 3.12 until it is ruled (J5, G10) |
| A ruling on each of J7's budgets that WP43 misses | WP43's shipping | The miss is carried as a `REV-nn` row |
| The required status checks renamed in the repository's branch protection, if it has any | WP43's merge | The pull request cannot merge, or merges with stale checks required |
| The tag `v0.5.0-alpha.9` and CI result as the required check | Now | WP44's pull request waits on the old checks |
| A read of WP45's pull request, and of any module the author picks | WP45's merge | The pull request waits |
| A ruling on any WP49 cost over its threshold that one pull request cannot fix | WP49's shipping | The cost is carried as a `REV-nn` row, and the protocol does not wait on it |
| A look at every stage's figure and every notebook, on a case of the author's choosing | WP51's merge | The pull request waits; a figure the author finds misleading is a `REV-nn` row, fixed before the merge |
| The document of comments and notes on the notebooks and figures | WP54's plan | WP54 waits; the author may drop it by ruling and the protocol goes ahead |
| The merge of every PR | Every package | — |
| The tags, if the session cannot push them | After each merge (`v0.5.0-alpha.N`) and at the close (`v0.5.0`) | The session prints the `git tag -a` and `git push` commands (G11) |

## Verification

Every package leaves the full gate green before the next starts:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
.claude/hooks/gate.sh run          # the push gate, with --extended
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP35 | 1, 2 | VER-61, VER-62, VER-63 (proposed) |
| WP36 | 1, 2 | VER-64 (proposed); `MOD-12`'s assertion in `test_public_api.py` |
| WP37 | 1, 2 | VER-65 (proposed); VER-47 unchanged |
| WP38 | 1, 2 | VER-61 re-recorded |
| WP39 | 1, 2 | VER-66; VER-61 gains H6's acyclicity; QR-14, IF-03, QR-11 |
| WP40 | 1 | VER-67 (proposed) |
| WP41, accuracy | 1, 2 | Tests named for QR-03, NUM-16, PHY-13, VER-37; VER-62 re-pinned only under I4 |
| WP42, verification | 1, 2 | VER-70, VER-71 (proposed) |
| WP43, development loop | 1 | VER-73, VER-74 (proposed); VER-62 on Python 3.14; both withdrawn by WP44 |
| WP44, simplify the loop | 1 | Plan-shape test; VER-73 and VER-74 withdrawn; VER-62 unchanged |
| WP45, prose strip | 1, 2 | VER-75; syntax-tree equality; VER-45 |
| WP46, small fixes | 1, 2 | Tests named by item; no new identifier |
| WP47, OKF bundle | 1 | VER-68, the F6 check |
| WP48, OKF backfill | 1, 2 | Tests named by claim; no new identifier |
| WP49, cost study | 1, 2 | VER-76 (proposed); VER-62 unchanged |
| WP50, test scope | 1, 2 | None new; N3's identifiers withdrawn; VER-61, VER-62, VER-65 kept green |
| WP51, plotting and notebooks | 1, 2, nightly | FR-30's smoke test, the data layer's conversions, the import guard and the notebooks' nightly run; VER-61 re-recorded; VER-62 and VER-65 unchanged |
| WP52, documents | 1, 2 | None new; R10's line and identifier checks in the pull request; VER-45 |
| WP53, workflow | 1, 2 | None new |
| WP54, notebooks revised | 1, 2, nightly | Claimed by its plan; FR-30's tests kept; VER-61, VER-62, VER-65 unchanged |
| WP55, protocol | nightly | VER-69 (proposed) |
| Every refactor | 1, 2 | VER-61, VER-62 and VER-63 kept green |
| Fixes, from WP56 | 1, 2 | Claimed at the second amendment |
| Documentation | 1, 2 | VER-45, VER-46 |
| Close | 1, 2 | VER-63 against closed logs |

> **Amended, 18 October 2026** (§8.2.13 N2 to N4). From WP50 the push gate runs N4's per-push
> selection and no `--extended`; the rest runs nightly. Criterion 1 reads "Tiers 1 and 2 pass, per
> push and nightly". Where criteria 2, 4, 5, 10 and 11 cite VER-63, VER-68, VER-75, the plan-shape test
> or G3's list, the close verifies the same condition at review and records it in the report.

**The phase is complete when:**

1. **Tiers 1 and 2 pass**, `--extended`, including every earlier phase's gate. If one misses, the
   cause is investigated and fixed. There is no waiver: these are the project's own analytic tests.
2. **The modularity report is merged and every `MOD-nn` is terminal**, asserted by VER-63 on the
   closed log. Prediction: 10 to 25 findings, most of them deferred. If one misses, a finding not
   ruled by the close is deferred by an explicit ruling. Leaving it open is not an option.
   *Amended, 5 October 2026:* 17 findings, of which 13 are accepted and must be `fixed` by the
   close (§8.2.8).
3. **VER-61 passes** on the layering the rulings accepted. If it misses, the edge is removed, or it
   is ruled accepted and recorded in the same commit. *Amended, 5 October 2026* (H6): from WP39 it
   also asserts that the subpackage `top` relation is acyclic. Prediction: met by WP39, with no
   `top` component left of the ten members `MOD-03` measured. The static relation, which counts
   deferred and annotation imports, is reported and not targeted. If it misses, the residual cycle
   is ruled accepted or deferred with its cut named. It is never forced.
4. **The knowledge base is an OKF bundle and the F6 check passes, with G3's list empty.** If it
   misses, a claim no test can re-establish is downgraded or removed by ruling, with the concept
   amended. The check is never relaxed.
5. **The user-testing log is closed**: every `UT-nn` is terminal under VER-63, and every protocol
   script runs in the gate (G7). If it misses, the response is the same as for criterion 2.
6. **VER-62 holds** on every CI platform, against the golden recorded on `v0.4.0`: at 10⁻⁸ relative
   on a recorded mesh, and within the walk's measured mesh-moved tolerance (at most 10⁻³) on an
   unseen one, an unseen mesh failing in the reference environment.
   Prediction: zero drift beyond round-off. If it misses, the change is investigated, then
   reverted, or ruled a deliberate fix that amends its clause and re-pins the golden (G10).
7. **The shell follows** (QR-11): VER-43, VER-44, VER-55 and VER-60 pass, and the bundle
   self-tests. If it misses, the fix lands in the package that broke it.
8. **Documentation increment 4 is merged**, VER-45 and VER-46 pass, and every break of the phase is
   in `CHANGELOG.md` with its migration.
9. *Added, 5 October 2026* (H3). **VER-65 passes**: no subpackage imports NGSolve or Netgen beyond
   the recorded set. If it misses, the import is removed, or the author rules the set wider in the
   same commit.
10. *Added, 6 October 2026* (§8.2.9 I1 to I3). **Every `REV-nn` row placed in a Phase 4 package
    is `fixed`**, read from the register that VER-63 checks. The register stays `open`, because it is
    rolling (H12), so the close lists the rows whose ruling names WP38 to WP43 or the close.
    Prediction: all 39 (37 from I3 and I2, with REV-03 and REV-05). If one misses, it is deferred
    by an explicit ruling, never left `accepted` past the close.
    *Amended, 11 October 2026* (§8.2.10 J1): the small fixes are now WP46, so the rows read are
    those naming WP38 to WP46.
11. *Added, 11 October 2026* (§8.2.10 J7); **replaced, 13 October 2026** (§8.2.11 L2 to L8). **The
    loop is simple and the prose small.** On the close's tree: the commit hook runs only lint,
    types and Tier 1; the impact recorder, budget enforcer and agent framework are gone; a plan from
    WP44 on is within its word cap, checked by the plan-shape test; and VER-75 holds, with `src/`
    prose at most 10 % and `tests/` at most 3 %. Reported, not gated: the commit hook (prediction
    about 90 s), the push gate (8 to 9 minutes) and the pull-request critical path (under 6
    minutes). If a gated item misses, it is fixed; if a reported number misses, the cause is
    reported and the author rules. No tolerance is loosened and no oracle weakened.
12. *Added, 18 October 2026* (§8.2.12 M2). **Each cost the architecture review suspected is measured**
    against its threshold registered under WP49, and each one over it is fixed or ruled into a fix
    package; VER-76 passes. Prediction: all three under their thresholds, so no fix lands. If a
    measurement misses its prediction, the number is reported and the fix follows the threshold, not
    the prediction; a threshold is never moved after its measurement.
13. *Added, 22 October 2026* (§8.2.14 P3 to P6). **FR-30 holds.** Every registered stage declares a
    figure or is on the recorded figure-free list, checked both ways. The smoke test draws every
    declared figure on examples 01 and 02 per push, and on 06 and 07 nightly. `import nanopnp` and a
    walk load neither Matplotlib nor marimo. Every notebook runs headless nightly. VER-61 records
    `plot` with no upward edge, VER-65's set stays at eleven, and VER-62 shows zero drift.
    Prediction: all met in WP51, with `case` and `report` the only figure-free stages. If one
    misses, it is fixed in WP51. A backend import is removed, VER-65's set growing only by the
    author's ruling, and a VER-62 move is reverted (G10). A figure the author finds misleading is
    fixed before the merge.
14. *Added, 22 October 2026* (§8.2.16 R2 to R7, R10). **The specification and the plans read current
    by default, and the skills have levels.** `SPECIFICATION.md` is the entry point over
    `specification/`, with the history in `specification/history/`. R10's line check and identifier
    check pass in WP52, their output in its Outcome, and VER-45 passes. This plan states its current
    scope, with its amendments in a record. The skills are `/plan`, `/implement`, `/ship` and
    `steward`. Prediction, reported and not gated (§8.2.11 L8): the current text of the
    specification is 60,000 to 68,000 words, and this plan's current scope under 6,000. A lost line or
    an unresolved identifier is fixed before WP52 merges, with no waiver. A missed prediction is
    reported.

## End-of-phase report

Empty until the close package fills it. It reports:

- **The modularity report:** the number of `MOD-nn` findings by area, and how many were fixed,
  deferred or sent post-1.0, with the deferrals' destinations. Source: VER-63 on the closed log.
- **The layering:** the subpackage import matrix before (`v0.4.0`) and after, the size of the
  strongly connected set, whether H6's target was met and, if not, the ruled residual. Source:
  WP35's script and VER-61.
- **The backend's reach:** the subpackages importing NGSolve or Netgen, eleven at `97f2b3d`, and
  at the close. Source: VER-65.
- **Number stability:** the largest relative drift of each golden QoI on each platform, with the
  golden's commit. Source: VER-62.
- **The ledger:** the count of `[tested: …]` claims, their distinct tests, the `[verified]` claims
  that remain under `process:arithmetic`, and the concepts carrying `tested_with`. Source: the F6
  check.
- **The review register:** the `REV-nn` rows by status at the close, those fixed in Phase 4 by
  package, and those deferred by destination. Source: VER-63 on the register.
- **User testing:** the number of sessions and `UT-nn` findings by area and severity, and how many
  were fixed or deferred. Source: VER-63.
- **Breaks:** the schema identifier at the release, the `PUBLIC` names added and removed, and the
  CLI changes, each with its migration. Sources: `test_public_api.py`, VER-47 and `CHANGELOG.md`.
- **The suite:** test counts by tier and the push gate's serial and parallel durations, against the
  1,764 collected by default at `v0.4.0`. Source: the gate run on the close package's tree.
- **The cost study:** WP49's three measurements against their thresholds and predictions, and what
  was fixed. Source: WP49's script, re-run on the close's tree.
- **Plotting and notebooks:** the stages with a figure and those on the figure-free list, the
  notebooks, and their nightly runtime on four cores. Sources: FR-30's smoke test and the nightly
  run.
- **The development loop:** the wall times of the commit hook, the push gate and CI's pull-request
  critical path, against 11 October 2026's 199 s, 527 s and about 10.5 minutes. Sources: the gate log
  (`<git dir>/nanopnp-gate.log`) and CI's job timings.

---

## Amended 22 October 2026 (§8.2.16 R12)

At WP53's plan the author renamed the commands, because `/plan` is a built-in Claude Code command. The
plan settled the aliases and the hook's open cases. WP53's entry read, before this amendment:

> **WP53 — The workflow: three skills with levels, workers, and a current checkout (§8.2.16 R5 to R7)**
>
> It waits on WP52, whose layout its skills read.
>
> - **`/plan`, `/implement` and `/ship`**, each a short router over a shared core file and one file per
>   level (`project`, `phase`, `amend` and `wp` for `/plan`; `wp` and `phase` for `/ship`), replacing
>   `phase-plan`, `wp-plan`, `wp-implement` and `wp-ship`. R3's and R4's rules for rulings and plan
>   amendments go into the planning levels, and a ruling's table is written to a new `history/` file
>   and its rule to §8.4 (R5).
> - **The worker pattern** in the implementing level, and the planning level's mark for the items that
>   go to workers (R6).
> - **The session-start hook's fast-forward** of a clean primary `main`, and its warning otherwise (R7).
> - **The pointers**: `CLAUDE.md`'s *Implementation workflow* and *Commands*, `current.md`'s handoff
>   rules, §8.4.4 and every mention of the old names.
>
> `steward` and the two agent files stay. No test is kept (N1). WP54 is the first package planned,
> implemented and shipped with the new skills, and its sessions are the check. Its plan decides the
> core file's contents, whether the old names stay as aliases and the hook's behaviour on a detached or
> diverged checkout. Tag `v0.5.0-alpha.19`.

The *Open decisions* row on WP53's aliases and the hook read **Open**, owned by WP53's plan.
