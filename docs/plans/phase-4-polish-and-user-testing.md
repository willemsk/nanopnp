# Phase 4 (Polish and user testing): a codebase whose seams are measured and whose surface has been used

**Status: in progress.** Written 5 October 2026, after Phase 3 closed as `v0.4.0`, and restated to its
current scope on 22 October 2026 (§8.2.16 R4). The text of every amendment since 5 October, and the
plan as it stood before this restatement, are in [phase-4-record.md](phase-4-record.md), read on
demand. Delivered: WP35 to WP52, below. Planned: WP53, the workflow; WP54, the notebooks and figures
revised; WP55, the user-testing protocol ([plan](wp55-user-testing-protocol.md)). Provisional, and
planned by the second `/phase-plan amend 4` once the author has run the sessions and ruled every
`UT-nn`: the fixes from WP56, the documentation increment and the close, which take their numbers
then. Estimate: 4–6 weeks (§8.2.9 I5). Release: **v0.5** (`v0.5.0`).

## In brief

Phase 4 tidies the program before others rely on it. The rebuilt structure, the simpler loop, the
trimmed code and tests, the reorganised notes, the cost study, a picture of every step of the
pipeline with notebooks to try it, and the split specification are done.

**What changes.** Two packages and a revision come before the testing sessions. The first rebuilds
the working instructions as three commands, plan, implement and ship, each taking a level; hands
batches of independent edits to fresh helpers; and keeps the instructions a session loads up to
date. The second revises the notebooks and figures from the author's notes. The third writes the
protocol the author's sessions follow.

**Cost.** About a week. Nothing a user runs changes in the first.

**What could go wrong.** A rewritten instruction could lose a rule; the first package planned with
the new commands would show it. The notebooks' revision has an open scope, so its plan names any new
dependency before it enters.

**Your call.** Should the phase estimate grow from four to six weeks to five to seven?
*Recommendation:* yes; the sessions matter more than the date.

## Context

This is the delivery plan for Phase 4 of `SPECIFICATION.md` §8.1. The specification is normative.
Where this file and the specification disagree, the specification governs and this file is wrong.
Requirement identifiers here are pointers into the specification, never restatements of it. The
author's rulings behind this plan are §8.2.6 F3, F4 and F6, §8.2.7 G1 to G11, §8.2.8 H1 to H12,
§8.2.9 I1 to I5, §8.2.10 J1 to J12, §8.2.11 L1 to L10, §8.2.12 M1 to M5, §8.2.13 N1 to N7, §8.2.14 P1
to P10, §8.2.15 Q1 and §8.2.16 R1 to R11. They are not re-argued here; where a ruling sets a standing
rule, it is in §8.4.

Phases 0 to 3 built the pipeline, from a structure to a charged current. Phase 4 asks two questions
before the GUI phase builds on it and the validation phase measures it. Is the architecture as
modular as FR-27, FR-20 and QR-14 claim? Can a person who did not write the code use the physics,
the numerics, the Python API and the command line? The phase answers the first with a measured
report and the refactors the author accepts from it, and the second with scripted sessions that the
author runs and a findings log. Between them, the companion knowledge base became an OKF bundle in
which every tested claim names its test, the specification became one, and every stage gained a
figure.

**The gate** (§8.1 as amended by §8.2.7) has five parts:

- the modularity report is merged, with every finding ruled;
- the user-testing findings log is closed;
- both logs are read at review as closed (§8.2.13 N3);
- the number-stability golden holds (10⁻⁸ on a recorded mesh; G10, VER-62);
- Tiers 1 and 2 pass.

A sixth part, the development loop is simple and the prose small, is criterion 11. No requirement in
Appendix A is tagged v0.5, so the evidence is the report, the two logs, the golden and the suites.

**Deliberately excluded:**

- any GUI work beyond following the API and the schema (QR-11). Screens, the result browser and
  figure export are Phase 5's (F5), and so is the browser shell that replaces the Qt shell (M3);
- Tier 3 and Tier 4, the archive-dependent legs and NUM-07's decision, which are Phase 6's (E1, E4,
  F1);
- OPN-08 (stable v1.0), structure preparation and OPN-04, which stay the author's;
- any new physics. A finding that asks for physics is deferred, with a ruling, to Phase 6 or to
  post-1.0;
- Python 3.15 and its lazy imports (J6; OPN-09), and every claim of the 18 October architecture
  review that the code already meets (M1);
- the export of figures by the command line and the report stage, FR-28's at v0.7 in Phase 6.

The phase retires no risk. RSK-15 and RSK-16 stay continuous.

## Design decisions

Each package's `/wp-plan` decides the rest in its own decisions table.

| Decision | Choice | Why |
|---|---|---|
| What opens the phase | A report with numbered findings, `MOD-nn`, from a committed script, and a Tier-1 guard pinning the layering it records. No refactor in that PR (G1) | A measurement that cannot be rerun is an adjective |
| When refactors land | Every refactor the author accepts lands before the protocol (G2) | Testers judge the surface v0.5 ships |
| Findings | One Markdown log per study under `docs/`, one row per finding with its ruling pointer, read at review as terminal at the close (G4, N3). Open items of a package are `REV-nn` rows (H12; §8.4.6) | The gate's "each finding ruled" is read, not assumed |
| The protocol | Its scripts run nightly, as an example's do (VER-46). Findings come from the author's sessions only, and an agent dry run records none (G7, N4; §8.4.6) | The tester did not write the code |
| The case schema | It moves as needed; a move takes the release's identifier, `nanopnp/case/v0.5`, and earlier identifiers read as their upgrade (G6; the §5.3.1 NOTE) | The schema keeps step with the package until v1.0 |
| Number stability | A golden recorded on `v0.4.0`'s tree and asserted by every later package at 10⁻⁸ relative on a recorded mesh. On an unseen mesh the tolerance is ten times the measured spread between recorded meshes, capped at 10⁻³, and an unseen mesh fails in the reference environment (G10, VER-62) | A polish phase must not move a result inside a benchmark's tolerance unnoticed |
| An accuracy fix and the golden | A fix that moves a VER-62 QoI within a bound argued before the change re-pins the golden in the same commit as the amended clause; a drift beyond the bound stops the package for the author's ruling (I4) | G10's ruling, given in advance |
| The public API | It may break (F4). Each break is decided in `test_public_api.py` and listed in `CHANGELOG.md` with its migration; the shell follows in the same PR (QR-11) | IF-01's promise starts at v1.0 |
| Close and tags | `v0.5.0` alone on the close package's last commit; the session pushes each tag if it can, otherwise prints the commands (G11; §8.4.1) | As E5 did for Phase 3 |
| The findings | Each `MOD-nn` as §8.2.8 H1 to H5 and H7 rule it. `MOD-11`, whether `with_section` and `core.stages.register` join `PUBLIC`, follows the sessions (H2) | The report's recommendations, except H7 |
| The coupling target | The subpackage `top` relation acyclic in the report's layer order, which gained `numerics`, then `plot` and `pipeline` (H6, H11, P3) | Pre-registered, so the gate does not take whatever the refactors leave |
| QR-13 | Met by the single statement of the weak forms; the backend's subpackages are a recorded set that only shrinks without a ruling (H3; VER-65) | An interface with one implementation cannot be tested for the property it exists for |
| Backend keys | The mesher, linear solver and stabilisation are registries, their schema keys strings checked against them (H7) | QR-14's one-class extension |
| The review register | Accepted items landed in packages by kind (WP41, WP42, WP46); the rest are ruled into Phase 5, 6, post-1.0 or declined (I1 to I3) | Every item has an owner |
| The architecture review | Already-met claims declined with their evidence; one measure-first package with registered thresholds; the browser shell to Phase 5; the Qt shell stays gated until then (M1 to M3) | A cost is fixed when it is measured |
| The test scope | Tests only for physics, numerics, core mechanisms and the licence and architecture guards; no coverage gate; the push gate runs the per-push selection and the rest runs nightly (N1 to N5; §8.4.3) | Development speed is not spent on tests that cannot catch a wrong answer |
| The development loop | The commit hook runs the lock check, lint, format, types and Tier 1; the push gate runs once, in the background; CI runs ubuntu on Python 3.14 on a pull request and the platforms after a merge; Python 3.14 is the default and 3.11 the floor (J4 to J6, L2, L3; §7.6, §8.4.2) | Every later package is built on it |
| Plans | Small, grounded in the code, with an executor per item and checkpoints that end the turn; amendments go to a record (L7, Q1, R4, R11; §8.4.4) | A smaller model can execute them |
| Plotting and notebooks | Matplotlib in `plot/` between `post` and `pipeline`, importing no backend; each stage declares its figure in the registry, so every artefact displays itself; marimo notebooks run nightly; `Case` joins `PUBLIC` (P2 to P6, P8; FR-30) | The author confirms each stage by eye before the sessions |
| The documents | `specification/` is an OKF bundle read current by default, its history on demand; rules in force without a clause are §8.4; `knowledge/` is not redistributed (R2, R3, R9) | A session reads what holds today |
| The workflow | `/plan`, `/implement` and `/ship` with levels; workers for independent batches; the primary checkout fast-forwarded (R5 to R7) | Fewer files to read, a current checkout |

## Conventions established by earlier phases

Inherited, and not re-decided by any package below.

- **The case document is the unit of reproducibility.** No stage reads YAML, and an unknown key is
  refused, naming it (IF-03).
- **Every switch is classified** in `SWITCH_PATHS` or `CONFIGURATION_PATHS`, in both directions
  (VER-24). Disabling a correction selects `none`; it takes no code branch.
- **Artefact keys are canonical hashes over validated payloads** (§5.3.2). The environment is
  recorded beside a key, never inside it, and no payload records wall-clock time (VER-23).
- **A stage is introspectable without importing its implementation** (VER-25). A missing extra is a
  named `MissingExtraError` at `create()`. `import nanopnp.cli` stays solver-free.
- **Layers read a model's declaration, never its name or class** (VER-56; the §5.4.3 NOTE).
- **A generated mesh is read only through `deployed_mesh`**, and a charge is deposited on the mesh
  the solve uses.
- **Supply chains are exclusive** (the §5.3.1 NOTE on `inputs:`).
- **A documented command runs verbatim in the gate** (VER-46). A number in the documentation is a
  result only if a test asserts it. Generated references are built, never committed.
- **The desktop shell holds no physics** and reads every number from a stage's artefact (VER-60).
- **A gated test gets cheaper only by the §7.6 NOTE's four levers.**
- **Every plan, and every package's pull request, opens with `## In brief`** (§8.4.4).
- **2WCD is prepared through `prepared_2wcd`** in tests.

## Work packages

Each package gets its own plan before implementation and is green on Tiers 1 and 2 before the next
starts. Tags are `v0.5.0-alpha.N`.

### WP35 to WP51, delivered

| Package | What it delivered | Plan | Tag |
|---|---|---|---|
| WP35 | The modularity exploration: report, findings log, layering guard (VER-61), number-stability golden (VER-62) | [plan](wp35-modularity-exploration.md) | `v0.5.0-alpha.1` |
| WP36 | The stage protocol and the walk: `key()` on the protocol, per-stage facts in the registry (`MOD-01`, `MOD-02`, `MOD-12`) | [plan](wp36-stage-protocol-and-walk.md) | `v0.5.0-alpha.2` |
| WP37 | The cycle cuts outside `io`, the exit codes in `core`, the backend guard (`MOD-03`, `MOD-05`; VER-65) | [plan](wp37-cycle-cuts-exit-codes-backend-guard.md) | `v0.5.0-alpha.3` |
| WP38 | The `io` split into a base layer and the `pipeline` assembler (`MOD-04`, `MOD-13`, `MOD-15`) | [plan](wp38-io-split.md) | `v0.5.0-alpha.4` |
| WP39 | The backend registries for the mesher, solver and stabilisation (`MOD-06`, `MOD-07`, `MOD-16`; VER-66) | [plan](wp39-backend-registries.md) | `v0.5.0-alpha.5` |
| WP40 | The stale refusals (`MOD-14`) | [plan](wp40-stale-refusals.md) | `v0.5.0-alpha.6` |
| WP41 | The accuracy fixes (REV-06 to REV-09, REV-17, REV-26) | [plan](wp41-accuracy-fixes.md) | `v0.5.0-alpha.7` |
| WP42 | The verification checks (REV-11 to REV-13 and others) | [plan](wp42-verification-checks.md) | `v0.5.0-alpha.8` |
| WP43 | The development loop, since simplified by WP44 | [plan](wp43-development-loop.md) | `v0.5.0-alpha.9` |
| WP44 | Simplify the loop: commit hook, push gate, CI, models, plan caps (L2, L3, L6, L7) | [plan](wp44-simplify-the-loop.md) | `v0.5.0-alpha.10` |
| WP45 | The prose strip: one rule for in-code prose (L4) | [plan](wp45-prose-strip.md) | `v0.5.0-alpha.11` |
| WP46 | The small fixes (REV-14 to REV-16, REV-18, REV-19 and eleven low items) | [plan](wp46-small-fixes.md) | `v0.5.0-alpha.12` |
| WP47 | The OKF bundle and its checks for `knowledge/` | [plan](wp47-okf-bundle.md) | `v0.5.0-alpha.13` |
| WP48 | The OKF backfill: tested claims name their tests | [plan](wp48-okf-backfill.md) | `v0.5.0-alpha.14` |
| WP49 | The cost study against registered thresholds, and the case schema as JSON Schema (VER-76) | [plan](wp49-cost-study.md) | `v0.5.0-alpha.15` |
| WP50 | The test scope (N1 to N5) | [plan](wp50-test-scope.md) | `v0.5.0-alpha.16` |
| WP51 | The plotting library and the notebooks (FR-30; P1 to P10) | [plan](wp51-plotting-and-notebooks.md) | `v0.5.0-alpha.17` |

The constraints these leave live are the conventions above, VER-61, VER-62 and VER-65 kept green,
and the standing rules of §8.4.

### WP52 — The documents: the specification and the plans split (§8.2.16 R2 to R4, R9, R10)

Delivered ([plan](wp52-specification-and-plans-split.md); tag `v0.5.0-alpha.18`). `specification/` is
an OKF bundle beside `knowledge/`: one file per numbered section, §5, §7 and §8 split by
subsection, an `index.md` per directory, and `history/` holding the Phase 0 criteria and §8.2.1 to
§8.2.16 verbatim, each ruling's home now listed in its index. `SPECIFICATION.md` is the entry point
and map. §8.4 restates the rulings in force that no clause carries, in 1,000 words. `clause.py`
prints every definition with its file and line range; the site, `mkdocs.yml` and the guide's anchors
read the bundle. This plan is its current scope, its amendments in
[phase-4-record.md](phase-4-record.md). No identifier is claimed and no test kept (N1); R10's two
checks, their output in the plan's Outcome, found no lost line and no changed definition.

### WP53 — The workflow: three skills with levels, workers, and a current checkout (§8.2.16 R5 to R7)

It waits on WP52, whose layout its skills read.

- **`/plan`, `/implement` and `/ship`**, each a short router over a shared core file and one file per
  level (`project`, `phase`, `amend` and `wp` for `/plan`; `wp` and `phase` for `/ship`), replacing
  `phase-plan`, `wp-plan`, `wp-implement` and `wp-ship`. R3's and R4's rules for rulings and plan
  amendments go into the planning levels, and a ruling's table is written to a new `history/` file
  and its rule to §8.4 (R5).
- **The worker pattern** in the implementing level, and the planning level's mark for the items that
  go to workers (R6).
- **The session-start hook's fast-forward** of a clean primary `main`, and its warning otherwise (R7).
- **The pointers**: `CLAUDE.md`'s *Implementation workflow* and *Commands*, `current.md`'s handoff
  rules, §8.4.4 and every mention of the old names.

`steward` and the two agent files stay. No test is kept (N1). WP54 is the first package planned,
implemented and shipped with the new skills, and its sessions are the check. Its plan decides the
core file's contents, whether the old names stay as aliases and the hook's behaviour on a detached or
diverged checkout. Tag `v0.5.0-alpha.19`.

### WP54 — The notebooks and figures revised (§8.2.16 R8)

It waits on WP53, and on the author's document of comments and notes on WP51's notebooks and
figures. Its scope is what that document asks (R8), new dependencies and changes below `plot/`
included, each a decision of its plan. WP51's rules carry unless that plan rules otherwise and amends
FR-30 in the same commit: `plot/` imports no backend; `import nanopnp` and a walk load no drawing or
notebook library; every notebook runs headless nightly; every stage declares a figure or is
figure-free. A change to `PUBLIC` is decided in `test_public_api.py` (F4) and listed in
`CHANGELOG.md`. VER-61, VER-62 and VER-65 stay green. Its plan claims its identifiers. Tag
`v0.5.0-alpha.20`.

### WP55 — The user-testing protocol (provisional detail)

[Plan](wp55-user-testing-protocol.md). It waits on WP54, whose notebooks session 04 is re-read
against. It writes:

- `docs/user-testing/protocol.md`, the protocol;
- scripted sessions over the physics, the numerics, the Python API and the command line. Each
  session is a task that a nanopore modeller would set, with the outcome expected and where to
  record surprise. Session 04, the Python API, is a marimo notebook in its own directory, using
  WP51's figures and display; the tester installs the `notebook` extra. One task touches
  `with_section` and stage registration, so the sessions inform `MOD-11`;
- the findings log, `docs/user-testing/findings.md`, `UT-nn`, header `open`.

Every script's commands and code run verbatim, by a test modelled on VER-46 (proposed VER-69), and
nightly (G7, N4). An agent dry run debugs the scripts and records nothing. The package ends when the
author has the protocol. **The sessions themselves are the author's**, and their findings are logged
as they run. Tag `v0.5.0-alpha.21`.

### Fix packages (provisional)

They wait on the sessions and on the author's ruling of each `UT-nn`; a second `/phase-plan amend 4`
plans them, numbered from WP56. They carry `MOD-11`, decided by the author's ruling of the sessions'
findings (H2), and any cost WP49 measured over its threshold that one pull request could not fix.
The rules of the refactor packages apply: VER-61, VER-62, `CHANGELOG.md` breaks, the shell following,
schema moves under `nanopnp/case/v0.5` (G6), and their tests follow N1.

### Documentation increment 4 (provisional)

It waits on the fixes and delivers §8.1's documentation increment for Phase 4: the modularity report
in the site; the user guide, the API reference and the CLI reference revised against both logs,
including a hand-written Python API page if the sessions show it is needed; every break of the phase
listed with its migration (F4). VER-45 and VER-46 gate it.

### The close package (provisional)

It comes last. It:

- resolves or carries each row of *Open decisions*;
- confirms that every `MOD-nn` and `UT-nn` row is terminal and sets both logs' headers to `closed`,
  recording their closure, and the register's, in the report (N3);
- confirms that every `REV-nn` row whose ruling places it in a Phase 4 package is `fixed`;
- re-runs the end-of-phase report's numbers on its own tree, never copying them from an Outcome;
- writes the report below, the `[0.5.0]` section of `CHANGELOG.md` and `CITATION.cff`'s version and
  date;
- updates `current.md` to point at Phase 5 (F5).

Its last commit on `main` is tagged `v0.5.0` alone (G11).

## Open decisions

| Decision | Owner and status |
|---|---|
| The phase estimate after R1: 4–6 weeks stands (P7), or 5–7 | **Author, open.** Recommendation: 5–7 weeks |
| The notebooks on the documentation site: in documentation increment 4, or later | **Author, open**, at the second amendment. Default: on the site, after the sessions show which help |
| WP53's aliases for the old command names, and the hook on a diverged checkout | **Open**, owned by WP53's plan |
| WP54's scope | **Settled** (R8): open, decided at its plan from the author's notes |
| Each `UT-nn`: fix or defer | **Author**, through the second amendment |
| `MOD-11` | **Accepted, and decided after the sessions** (H2), by the author's ruling, in a fix package |
| OPN-04, OPN-08 | **Author, open.** Not on this phase's path |
| NUM-07 order; the archive-dependent legs | **Phase 6** (E1, E4, F1) |
| Residual cycles, drift beyond a bound, a cost over its threshold | **Author**, only if a package reports one (H6, I4, M2) |
| WP49's thresholds | **Registered** 18 October 2026: 4 GB, 5 %, 10 %. A re-argued threshold is a plan amendment before the measurement, never after |

Everything else the phase decided is in *Design decisions*, with its ruling.

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| The document of comments and notes on the notebooks and figures | WP54's plan | WP54 waits; the author may drop it by ruling and the protocol goes ahead |
| The scripted sessions, run by the author, with findings logged | The second amendment, then the fix packages | The phase waits. No agent session substitutes (G7) |
| A ruling on every `UT-nn`, and on `MOD-11` | The fix packages and the close | `MOD-11` stays `accepted` and the close does not read as closed |
| A ruling on a residual cycle, a drift beyond a bound or a cost over its threshold | The package that reports it | The package stops at the edge and carries it as a `REV-nn` row |
| The merge of every PR | Every package | — |
| The tags, if the session cannot push them | After each merge (`v0.5.0-alpha.N`) and at the close (`v0.5.0`) | The session prints the `git tag -a` and `git push` commands (G11) |

## Verification

Every package leaves the full gate green before the next starts:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
.claude/hooks/gate.sh run          # the push gate
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP35 to WP51 | 1, 2, nightly | As their plans record; VER-61, VER-62 and VER-65 kept green |
| WP52, documents | none kept | R10's line and identifier checks in the pull request; VER-45 |
| WP53, workflow | none kept | None new |
| WP54, notebooks revised | 1, 2, nightly | Claimed by its plan; FR-30's tests kept |
| WP55, protocol | nightly | VER-69 (proposed) |
| Every refactor | 1, 2 | VER-61, VER-62 and VER-65 kept green |
| Fixes, from WP56 | 1, 2 | Claimed at the second amendment |
| Documentation | 1, 2 | VER-45, VER-46 |
| Close | 1, 2 | Both logs and the register read as closed |

**The phase is complete when:**

1. **Tiers 1 and 2 pass, per push and nightly**, including every earlier phase's gate. If one
   misses, the cause is investigated and fixed. There is no waiver: these are the project's own
   analytic tests.
2. **The modularity report is merged and every `MOD-nn` is terminal**, read from the closed log.
   Seventeen findings, of which 13 are accepted and must be `fixed` by the close (§8.2.8). A finding
   not ruled by the close is deferred by an explicit ruling; leaving it open is not an option.
3. **VER-61 passes** on the layering the rulings accepted, and the subpackage `top` relation is
   acyclic (H6). If it misses, the residual cycle is ruled accepted or deferred with its cut named.
   It is never forced.
4. **The knowledge base is an OKF bundle** in which every `[tested: …]` claim names a test in scope,
   checked at review (N3). A claim no test can re-establish is downgraded or removed by ruling.
5. **The user-testing log is closed**: every `UT-nn` is terminal, read at review, and every protocol
   script runs nightly (G7, N4).
6. **VER-62 holds** on every CI platform, against the golden recorded on `v0.4.0`: at 10⁻⁸ relative
   on a recorded mesh, and within the walk's measured mesh-moved tolerance (at most 10⁻³) on an
   unseen one. If it misses, the change is investigated, then reverted, or ruled a deliberate fix
   that amends its clause and re-pins the golden (G10, I4).
7. **The shell follows** (QR-11): VER-43, VER-44, VER-55 and VER-60 pass, and the bundle self-tests.
   If it misses, the fix lands in the package that broke it.
8. **Documentation increment 4 is merged**, VER-45 and VER-46 pass, and every break of the phase is
   in `CHANGELOG.md` with its migration.
9. **VER-65 passes**: no subpackage imports NGSolve or Netgen beyond the recorded set. If it misses,
   the import is removed, or the author rules the set wider in the same commit.
10. **Every `REV-nn` row placed in a Phase 4 package (WP38 to WP46 or the close) is `fixed`**, read
    from the register. The register stays rolling (H12). Prediction: all 39. One that is not is
    deferred by an explicit ruling, never left `accepted` past the close.
11. **The loop is simple and the prose small.** The commit hook runs only the lock check, lint,
    format, types and Tier 1; the impact recorder, budget enforcer and agent framework are gone; a
    plan from WP44 on is within its word caps; the prose of `src/` is at most 10 % and of `tests/` at
    most 3 %, with the accepted exception of L10. Reported, not gated: the commit hook (prediction
    about 90 s), the push gate (under 4 minutes) and the pull-request critical path (under 6
    minutes). If a gated item misses, it is fixed; if a reported number misses, the cause is
    reported and the author rules. No tolerance is loosened and no oracle weakened.
12. **Each cost the architecture review suspected is measured** against its registered threshold,
    and each one over it is fixed or ruled into a fix package. A threshold is never moved after its
    measurement (M2).
13. **FR-30 holds.** Every registered stage declares a figure or is on the recorded figure-free
    list, checked both ways. The smoke test draws every declared figure on examples 01 and 02 per
    push, and on 06 and 07 nightly. `import nanopnp` and a walk load neither Matplotlib nor marimo.
    Every notebook runs headless nightly. VER-61 records `plot` with no upward edge, VER-65's set
    stays at eleven, and VER-62 shows zero drift. A figure the author finds misleading is fixed
    before the merge.
14. **The specification and the plans read current by default, and the skills have levels.**
    `SPECIFICATION.md` is the entry point over `specification/`, with the history in
    `specification/history/`. R10's line check and identifier check pass in WP52, their output in
    its Outcome, and VER-45 passes. This plan states its current scope, its amendments in a record.
    The skills are `/plan`, `/implement`, `/ship` and `steward`. Prediction, reported and not gated
    (§8.2.11 L8): the current text of the specification is 60,000 to 68,000 words, and this plan under
    6,000. A lost line or an unresolved identifier is fixed before WP52 merges, with no waiver.

## End-of-phase report

Empty until the close package fills it. It reports:

- **The modularity report:** the `MOD-nn` findings by area, and how many were fixed, deferred or sent
  post-1.0, with the deferrals' destinations.
- **The layering:** the subpackage import matrix before (`v0.4.0`) and after, the size of the
  strongly connected set, whether H6's target was met and, if not, the ruled residual. Source:
  WP35's script and VER-61.
- **The backend's reach:** the subpackages importing NGSolve or Netgen, eleven at `97f2b3d`, and at
  the close. Source: VER-65.
- **Number stability:** the largest relative drift of each golden QoI on each platform, with the
  golden's commit. Source: VER-62.
- **The knowledge base:** the `[tested: …]` claims, their distinct tests, and the `[verified]` claims
  that remain.
- **The review register:** the `REV-nn` rows by status at the close, those fixed in Phase 4 by
  package, and those deferred by destination.
- **User testing:** the sessions and `UT-nn` findings by area and severity, and how many were fixed
  or deferred.
- **Breaks:** the schema identifier at the release, the `PUBLIC` names added and removed, and the
  CLI changes, each with its migration. Sources: `test_public_api.py`, VER-47 and `CHANGELOG.md`.
- **The suite:** test counts by tier and the push gate's duration, against the 1,764 collected by
  default at `v0.4.0`. Source: the gate run on the close package's tree.
- **The cost study:** WP49's three measurements against their thresholds and predictions, and what
  was fixed. Source: WP49's script, re-run on the close's tree.
- **Plotting and notebooks:** the stages with a figure and those on the figure-free list, the
  notebooks, and their nightly runtime on four cores.
- **The development loop:** the wall times of the commit hook, the push gate and CI's pull-request
  critical path, against 11 October 2026's 199 s, 527 s and about 10.5 minutes. Sources: the gate log
  (`<git dir>/nanopnp-gate.log`) and CI's job timings.
- **The documents:** the word counts of the current specification, its history and §8.4, and of this
  plan.
