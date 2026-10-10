# Phase 4 (Polish and user testing): a codebase whose seams are measured and whose surface has been used

**Status: in progress.** Written 5 October 2026, after Phase 3 closed as `v0.4.0`. Amended the
same day, after the author ruled every `MOD-nn` (§8.2.8). Amended again on 6 October 2026, after
the author ruled the review register (§8.2.9).
Delivered: WP35, the modularity exploration
([wp35-modularity-exploration.md](wp35-modularity-exploration.md)), tagged `v0.5.0-alpha.1`;
WP36, the stage protocol and the walk ([wp36-stage-protocol-and-walk.md](wp36-stage-protocol-and-walk.md)),
tagged `v0.5.0-alpha.2`; WP37, the cycle cuts, the exit codes and the backend guard
([wp37-cycle-cuts-exit-codes-backend-guard.md](wp37-cycle-cuts-exit-codes-backend-guard.md)),
tagged `v0.5.0-alpha.3`; WP38, the `io` split ([wp38-io-split.md](wp38-io-split.md)),
tagged `v0.5.0-alpha.4`; WP39, the backend registries ([wp39-backend-registries.md](wp39-backend-registries.md)),
to be tagged `v0.5.0-alpha.5`; WP40, the stale refusals ([wp40-stale-refusals.md](wp40-stale-refusals.md)),
to be tagged `v0.5.0-alpha.6`; WP41, the accuracy fixes ([wp41-accuracy-fixes.md](wp41-accuracy-fixes.md)),
to be tagged `v0.5.0-alpha.7`.
Planned: WP42, the verification checks; WP43, the small fixes; WP44, the OKF bundle; WP45,
its backfill; WP46, the user-testing protocol (§8.2.9 I1). Provisional, and planned by the second
`/phase-plan amend 4` once the author has run the sessions and ruled every `UT-nn`: the fixes, from
WP47, then the documentation increment and the close, which take their numbers then.
Estimate: 4–6 weeks (§8.2.9 I5). Release: **v0.5** (`v0.5.0`).

This is the delivery plan for Phase 4 of `SPECIFICATION.md` §8.1. The specification is normative.
Where this file and the specification disagree, the specification governs and this file is wrong.
Requirement identifiers here are pointers into the specification, never restatements of it. The
author's rulings behind this plan are §8.2.6 F3, F4 and F6, §8.2.7 G1 to G11, §8.2.8 H1 to H12 (on
the modularity report and the review register), and §8.2.9 I1 to I5 (on planning the register's
items). They are not re-argued here.

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

The rulings on the review register (§8.2.9), 6 October 2026, cover the 56 items left open by the
packages up to WP36. 37 are planned into Phase 4: 30 into three new packages
before the OKF bundle (WP41 to WP43), three each into WP38 and WP39, and one into the close; REV-03
and REV-05 were already WP38's and WP39's. 15 are deferred to Phase 5 or 6, two are post-1.0, and two
are declined (I1 to I3).

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
| The review register's items | Those accepted for Phase 4 land in three packages by kind, WP41 to WP43, after WP40 and before the OKF bundle. The OKF bundle, the backfill and the protocol become WP44 to WP46 (§8.2.9 I1, I2) | Numbers settle before the ledger re-establishes them and before the testers see them |
| The open `REV-nn` rows | Each one ruled: into a Phase 4 package, deferred to Phase 5 or 6, post-1.0, or declined (I3) | Every item of the register has an owner |
| An accuracy fix and the golden | WP41's plan argues a bound for each VER-62 QoI before the change. A drift within that bound is re-pinned in the same commit as the amended clause; a drift beyond it stops the package (I4) | G10's ruling is given in advance for a fix whose purpose is to move a number, and only within a bound registered beforehand |

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

### WP43 — The small fixes (REV-14 to REV-16, REV-18, REV-19, and eleven low items)

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

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP44**, after WP43. It is written against
> the test node ids that WP36 to WP43 leave. VER-68 stays its proposed identifier.

### OKF backfill — Provisional

It waits on the bundle package. Every listed claim gets its test: a Tier-1 or Tier-2 test that
re-establishes the claim, named inline. A library-behaviour concept gains `tested_with`. At the end
the list is empty and the check refuses any unbacked `[tested]` (G3). The new tests' cost is bound
by the §7.6 NOTE's levers. A claim whose test fails is a finding about the knowledge base, never a
reason to loosen the test.

> **Amended, 5 October 2026.** This is **WP42** (§8.2.8 H8). It claims no new identifier: each new
> test is named for the claim it backs, and VER-68's list reaching empty is the package's end.

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP45**. A claim about Newton's
> convergence test or the areal-charge quadrature is backed against WP41's tree, not the one before it.

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

> **Amended, 6 October 2026** (§8.2.9 I1). This is now **WP46**. VER-69 stays its proposed identifier.

### Fix packages — Provisional

They wait on the sessions and on the author's ruling of each `UT-nn`. A second `/phase-plan amend 4`
plans them. The rules of the refactor packages apply: VER-61, VER-62, `CHANGELOG.md` breaks, the
shell following, and schema moves under `nanopnp/case/v0.5` (G6).

> **Amended, 5 October 2026.** They also carry `MOD-11`, decided by the author's ruling of the
> sessions' findings (§8.2.8 H2). Their numbers are assigned by the second amendment, from WP44 (H8).

> **Amended, 6 October 2026** (§8.2.9 I1, I3). They are numbered from **WP47**. They carry no review
> item that §8.2.9 placed elsewhere. An item a later review adds goes to them only by a ruling
> recorded in the register.

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
| The review register's accepted items | At the second amendment, or before the OKF bundle | **Settled by the author, 6 October 2026** (§8.2.9 I1): WP41 to WP43, before WP44 |
| Their grouping | By kind, two packages, or one per area | **Settled by the author, 6 October 2026** (I2): accuracy, verification, small fixes |
| `REV-23` to `REV-65` | Phase 4, Phase 5, Phase 6, post-1.0 or declined, each | **Settled by the author, 6 October 2026** (I3) |
| An accuracy fix that moves VER-62 | Stop (G10), pre-rule, or diagnose only | **Settled by the author, 6 October 2026** (I4): pre-ruled within a bound WP41's plan argues |
| REV-06's frame, and whether REV-08 makes NUM-16's test per field | — | **Settled by WP41's plan, 7 October 2026**, from measurement: a supplied field is in the model frame, and a declared other frame is refused (WP41 D1, amended in the plan's commit); the test becomes per field, and the relative residual test no longer closes a rung (WP41 D4, amended in its item's commit, I4) |
| `with_section`, `register` in `PUBLIC` | Add or keep out | Carried from WP34 D9 as `MOD-11`. **Accepted, and decided after the sessions** (H2), by the author's ruling, in a fix package |
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
| WP43, small fixes | 1, 2 | Tests named by item; no new identifier |
| WP44, OKF bundle | 1 | VER-68 (proposed), the F6 check |
| WP45, OKF backfill | 1, 2 | Tests named by claim; no new identifier |
| WP46, protocol | 1 or 2 | VER-69 (proposed) |
| Every refactor | 1, 2 | VER-61, VER-62 and VER-63 kept green |
| Fixes, from WP47 | 1, 2 | Claimed at the second amendment |
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
10. *Added, 6 October 2026* (§8.2.9 I1 to I3). **Every `REV-nn` row placed in a Phase 4 package
    is `fixed`**, read from the register that VER-63 checks. The register stays `open`, because it is
    rolling (H12), so the close lists the rows whose ruling names WP38 to WP43 or the close.
    Prediction: all 39 (37 from I3 and I2, with REV-03 and REV-05). If one misses, it is deferred
    by an explicit ruling, never left `accepted` past the close.

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
