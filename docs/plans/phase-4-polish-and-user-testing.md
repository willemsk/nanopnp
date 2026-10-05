# Phase 4 (Polish and user testing): a codebase whose seams are measured and whose surface has been used

**Status: in progress.** Written 5 October 2026, after Phase 3 closed as `v0.4.0`; amended the
same day, after the author ruled every `MOD-nn` (§8.2.8).
Delivered: WP35, the modularity exploration
([wp35-modularity-exploration.md](wp35-modularity-exploration.md)), tagged `v0.5.0-alpha.1`.
Planned: WP36, the stage protocol and the walk; WP37, the cycle cuts, the exit codes and the
backend guard; WP38, the `io` split; WP39, the backend registries; WP40, the stale refusals; WP41,
the OKF bundle; WP42, its backfill; WP43, the user-testing protocol. Provisional, and planned by the
second `/phase-plan amend 4` once the author has run the sessions and ruled every `UT-nn`: the
fixes, the documentation increment and the close, which take their numbers then (§8.2.8 H8).
Estimate: 3–5 weeks (H9). Release: **v0.5** (`v0.5.0`).

This is the delivery plan for Phase 4 of `SPECIFICATION.md` §8.1. The specification is normative.
Where this file and the specification disagree, the specification governs and this file is wrong.
Requirement identifiers here are pointers into the specification, never restatements of it. The
author's rulings behind this plan are §8.2.6 F3, F4 and F6, §8.2.7 G1 to G11, and, on the
modularity report, §8.2.8 H1 to H9. They are not re-argued here.

## Context

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
  `.knowledge/*.md` without recursing.
- **The suite collects 1,764 tests by default and 1,861 in all.** Collection takes 12 s. The
  `extended` walks already compute the numbers a stability golden needs.

This phase retires no risk. RSK-15 and RSK-16 stay continuous. The report raised no new risk, and
its rulings (§8.2.8) enter none.

The rulings on the report, 5 October 2026: 13 findings accepted for Phase 4 (`MOD-01` to `MOD-07`,
`MOD-11` to `MOD-16`), `MOD-09` deferred to Phase 5, `MOD-10` deferred to Phase 6 with QR-13
restated, and `MOD-08` and `MOD-17` post-1.0. `MOD-06` and `MOD-07` are fixed now, against the
report's recommendation to defer them (H7). `MOD-11` alone waits for the sessions (H2).

Deliberately excluded:

- any GUI work beyond following the API and the schema (QR-11; §8.1, GUI increment 4). Screens,
  the result browser and figure export are Phase 5's (F5);
- Tier 3 and Tier 4, the archive-dependent legs and NUM-07's decision, which are Phase 6's (E1, E4,
  F1);
- OPN-08 (stable v1.0), which stays the author's;
- structure preparation, and OPN-04;
- any new physics. A finding that asks for physics is deferred, with a ruling, to Phase 6 or to
  post-1.0.

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

### WP37 — The cycle cuts outside `io`, the exit codes, and the backend guard (MOD-03, MOD-05, MOD-10; QR-13)

The single-import cuts of `MOD-03`'s table that do not start in `io`: `charge → mesh`,
`charge → physics`, `geometry → density`, `materials → charge`, `materials → density`,
`materials → mesh`, `mesh → materials`, `mesh → solve` and `physics → mesh`. With them, the
wall-distance solve leaves `mesh/distance.py`, taking `mesh → physics` with it. Its new home must
not make the corrections in `materials/` import upward. The plan decides it, and if no move does,
that edge is reported back (H6). The exit classification and codes of `cli/errors.py` move to
`core`, and `cli` re-exports them (`MOD-05`). VER-47's codes and `test_cli.py`'s table do not change.
Each removed edge leaves `modularity-layering.yaml` in the same commit.

**VER-65, the backend guard** (proposed; H3). A Tier-1 check that the set of subpackages importing
`ngsolve` or `netgen`, in any of the four kinds, equals a set recorded beside the layering. A
subpackage that gains the import fails, naming its module and line. A recorded one that loses it
fails until the record shrinks. Oracle: an `import ngsolve` substituted into `structure/` is
refused. QR-13's Appendix A row names it.

### WP38 — The `io` split (MOD-04, MOD-13 for `io/case.py`, MOD-15, and `io`'s cuts of MOD-03)

`io` splits into a base, holding the artefact types, the store, the defaults and the resolved-case
types, imported downward only, and an assembler, holding resolution, the walk and reproduction,
which imports the stages. `io/case.py`, at 3,160 lines, divides along the same line. `core/stages.py`'s
`TYPE_CHECKING` import goes to the base or to `core` (`MOD-15`). `io`'s three edges, `io → charge`,
`io → materials` and `io → mesh`, are cut. A registry check that the schema makes today, such as
`physics.model` against `physics/models.py`, moves to the assembler. The plan decides whether the
base is a new subpackage, which amends §5.1 and `CLAUDE.md`'s structure list in the same PR, or a
module of `core`. `PUBLIC` names keep their meaning, and internal paths are not API (IF-01).

No new identifier: VER-61 records the new relation, and VER-62 must show zero drift.

### WP39 — The backend registries (MOD-06, MOD-07, MOD-16; ADR-002, QR-14)

The mesher, the linear solver and the stabilisation mode become registries, each in the shape of
the nearest existing one (H5). `numerics.mesh.backend`, `numerics.linear.solver` and
`numerics.stabilisation` become strings, checked by the assembler against the registry as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and a missing extra is
still `MissingExtraError` at use. The schema's import of `solve.linear` goes. That is the last of
the edges H6's target needs, so **this package measures the target**: if the `top` relation is
acyclic, VER-61 gains the assertion; if not, the residual cycle goes to the author with the cut it
would need. The generated case-file reference loses three enumerations, which `CHANGELOG.md`
records, and the shell's selectors read the registries (QR-11, VER-43).

**VER-66, extension by registration** (proposed). A test registers a stub mesher, linear solver
and stabilisation mode. A case naming each validates, and is dispatched to the stub, with no file
outside the test edited. An unregistered name is refused naming the registered ones (IF-03).
VER-24's classification is unchanged.

### WP40 — The stale refusals (MOD-14; IF-02)

The seven release-naming strings `MOD-14` lists are rewritten. Each refusal names its requirement,
and either the release that schedules it or that none does. The empty `_UNCONSUMED_INPUTS` loop
goes. Break: CLI refusal texts change. Exit codes do not (VER-47).

**VER-67, no stale release in a refusal** (proposed). A Tier-1 check over
`validation.modularity.version_literals` refuses a non-docstring string naming a release that is
already tagged. The plan fixes how "already tagged" is read without the network. Oracle: a synthetic
refusal naming `v0.2` is refused.

### OKF bundle and checks — Provisional

It waits on the refactors (G5). F6 and the input note's K1 to K11 bind this package. It covers:

- the bundle: one concept per `##`, in a directory per file;
- every `.knowledge/0N §x` citation, history included, rewritten to a bundle path;
- the six checks of the input note as one Tier-1 test, which carries G3's committed list of
  unbacked claims. Executable `[verified]` claims join that list (G8).

Its `/wp-plan` puts open questions 3 to 7 to the author (G9). `generate.py` has to recurse.

> **Amended, 5 October 2026.** This is **WP41** (§8.2.8 H8), after WP40. The F6 check is proposed
> as **VER-68**, with the six refusals of the input note, *What the package SHALL check*. Its
> oracle is a constructed bundle that breaks each rule in turn. The bundle is written against the
> test node ids WP36 to WP40 leave, which is G5's reason for the order. Open questions 3 to 7
> stay with this package's `/wp-plan` (G9).

### OKF backfill — Provisional

It waits on the bundle package. Every listed claim gets its test: a Tier-1 or Tier-2 test that
re-establishes the claim, named inline. A library-behaviour concept gains `tested_with`. At the end
the list is empty and the check refuses any unbacked `[tested]` (G3). The new tests' cost is bound
by the §7.6 NOTE's levers. A claim whose test fails is a finding about the knowledge base, never a
reason to loosen the test.

> **Amended, 5 October 2026.** This is **WP42** (§8.2.8 H8). It claims no new identifier: each new
> test is named for the claim it backs, and VER-68's list reaching empty is the package's end.

### User-testing protocol — Provisional

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

### Fix packages — Provisional

They wait on the sessions and on the author's ruling of each `UT-nn`. A second `/phase-plan amend 4`
plans them. The rules of the refactor packages apply: VER-61, VER-62, `CHANGELOG.md` breaks, the
shell following, and schema moves under `nanopnp/case/v0.5` (G6).

> **Amended, 5 October 2026.** They also carry `MOD-11`, decided by the author's ruling of the
> sessions' findings (§8.2.8 H2). Their numbers are assigned by the second amendment, from WP44 (H8).

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
| The base half of `io` | A new subpackage, or a module of `core` | **Open**, owned by WP38's `/wp-plan` |
| The wall-distance solve's home | `physics`, `solve`, or reported back | **Open**, owned by WP37's `/wp-plan` (H6) |
| Each `UT-nn` | Fix or defer | **Author**, through the second amendment |
| Phase estimate | §8.1's "Set by the phase plan" | **Settled by the author, 5 October 2026**: 3–5 weeks (H9; §8.1, §8.3) |
| `with_section`, `register` in `PUBLIC` | Add or keep out | Carried from WP34 D9 as `MOD-11`. **Accepted, and decided after the sessions** (H2), by the author's ruling, in a fix package |
| NUM-07 order; the archive-dependent legs | — | **Phase 6** (E1, E4, F1). Not this phase's |
| OPN-04, OPN-08 | — | **Author, open.** Not on this phase's path |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| A ruling on every `MOD-nn` | The first amendment | **Given, 5 October 2026** (§8.2.8) |
| A ruling on any residual cycle H6's target leaves, and on any subpackage VER-65's set would gain | WP37 to WP39, as they report it | The package stops at the edge and carries it. VER-61 and VER-65 stay red until the ruling is recorded |
| The `MOD-11` choice | The fix packages | `MOD-11` stays `accepted`, and VER-63 refuses the close |
| The scripted sessions, run by the author, with findings logged | The second amendment, then the fix packages | The phase waits. No agent session substitutes (G7) |
| A ruling on every `UT-nn` | The fix packages and the close | As for `MOD-nn` |
| Open questions 3–7 of the OKF note | The OKF bundle package's plan | That plan carries them as open and blocks on them |
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
| WP39 | 1, 2 | VER-66 (proposed); VER-61 gains H6's acyclicity, or the residual is ruled |
| WP40 | 1 | VER-67 (proposed) |
| WP41, OKF bundle | 1 | VER-68 (proposed), the F6 check |
| WP42, OKF backfill | 1, 2 | Tests named by claim; no new identifier |
| WP43, protocol | 1 or 2 | VER-69 (proposed) |
| Every refactor | 1, 2 | VER-61, VER-62 and VER-63 kept green |
| Fixes | 1, 2 | Claimed at the second amendment |
| Documentation | 1, 2 | VER-45, VER-46 |
| Close | 1, 2 | VER-63 against closed logs |

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
- **User testing:** the number of sessions and `UT-nn` findings by area and severity, and how many
  were fixed or deferred. Source: VER-63.
- **Breaks:** the schema identifier at the release, the `PUBLIC` names added and removed, and the
  CLI changes, each with its migration. Sources: `test_public_api.py`, VER-47 and `CHANGELOG.md`.
- **The suite:** test counts by tier and the push gate's serial and parallel durations, against the
  1,764 collected by default at `v0.4.0`. Source: the gate run on the close package's tree.
