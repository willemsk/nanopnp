# Modularity report

This report measures nanopnp's architecture against its own claims and logs what it finds as
numbered findings, `MOD-nn`. It changes no code: the author rules each finding before anything
moves (§8.2.7 G1), through `/phase-plan amend 4`. The findings and their status are logged in
[the findings log](modularity-findings.md), and the live measurements are on
[the measurements page](../_generated/project/modularity-measurements.md).

## What is measured, and how

Every number below comes from `nanopnp.validation.modularity`, which reads the source by its
syntax tree and imports nothing it measures. Each finding names the function that measures it and
quotes the numbers **at `97f2b3d`**, the tree Phase 3 closed on with this phase's plan added. The
measurements page shows the same functions run on the tree the site was built from, so a finding
stays true as dated after a refactor has changed the live numbers.

The claims measured are:

- **FR-27**: every stage independently invocable, cancellable, progress-reporting and
  introspectable, emitting a hashed artefact.
- **FR-16, QR-14 and ADR-005**: a new correction is a data file; a new physics model is one class.
- **FR-20 and §5.4.3**: the layers outside `physics/` are model-agnostic.
- **QR-13 and §5.4.1**: the weak forms are written once against a thin backend interface.
- **ADR-002**: the mesher is an adapter, and Gmsh is optional.
- **IF-01**: the public surface is `nanopnp.PUBLIC`.

### The import relation

The nodes are the 16 subpackages, plus `nanopnp` for `__init__.py`. An import of one `nanopnp`
module by another is one of four kinds:

| Kind | Where |
|---|---|
| `top` | At module scope, outside `if TYPE_CHECKING:` |
| `deferred` | Inside a function |
| `typing` | Inside `if TYPE_CHECKING:` |
| `string` | A string constant naming a module, as the stage registry, `PUBLIC` and the exit-code table do |

The **static** relation is the union of the first three. A deferral or an annotation still
couples two layers, so moving an import into a function changes its kind and never the static
relation. The **string** relation is the fourth kind. `docs/project/modularity-layering.yaml`
records both, one row per subpackage edge, and VER-61 asserts that the live relations equal it
in both directions. A commit that adds or removes an edge edits that file. At `97f2b3d` there
are 806 import edges between modules: 460 `top`, 112 `deferred`, 132 `typing` and 102
`string`. They make 101 static and 27 string subpackage edges.

Strongly connected components are computed by Tarjan's algorithm (`components`). Each lists its
internal edges with the number of import statements carrying each, lightest first
(`component_edges`). Those are candidate cuts. A minimum cut is NP-hard, so the report names
candidates and never claims an optimum.

| Relation | Components |
|---|---|
| `top` | One of 10: `charge`, `density`, `geometry`, `io`, `materials`, `mesh`, `physics`, `solve`, `structure`, `symmetry` |
| runtime (`top` and `deferred`) | That one, and `cli`, `sweep`, `validation` |
| static | The ten and `core`; and `cli`, `nanopnp`, `sweep`, `validation` |
| static and string | The eleven and `post`; and `cli`, `gui`, `nanopnp`, `sweep`, `validation` |

The module graph of `top` imports has no cycle: Python resolves the subpackage cycle only because
no two modules import each other at load time. VER-61 asserts that this stays so.

### The order the findings read the layers in

A layering needs an order. This report reads the subpackages lowest first as the pipeline of
§5.2 runs, with `io`, the shells and the facade last: `core`, `structure`, `density`,
`symmetry`, `geometry`, `mesh`, `charge`, `materials`, `physics`, `solve`, `post`, `io`, `sweep`,
`validation`, `cli`, `gui`, `nanopnp`. An edge pointing up that order is annotated in the YAML with
the finding that explains it. The order is the report's reading, not a requirement. The author
may rule a different one, and the annotations move with it.

## Findings

Severity is **high** for a SHALL the code does not meet, **medium** for a property held only by
convention or an extension needing an edit outside its home, and **low** for size or tidiness.
*User-visible* is no, or names what a fix breaks: the API, the CLI or the schema (§8.2.6 F4,
§8.2.7 G6).

### MOD-01 — Two stages have no key, and the protocol declares none

*Area:* stages. *Severity:* high.

**Measured** (`stage_conformance`, at `97f2b3d`). Eleven of the 13 registered stage classes
define `key()`. `MaterialsStage` and `CaseStage` do not. The `Stage` protocol declares `name`,
`describe` and `run`, and not `key`. Every `run` takes `(inputs, *, progress, cancel)`, so the
protocol's own members are met. The two callers that need a key for a stage named at run time,
`validation/comsol.py:439` and `gui/assess.py:337`, reach it under
`# type: ignore[attr-defined]`.

**Consequence.** FR-27's "introspectable" is met for the description and not for the cache key. A
caller cannot ask a stage for the key of its artefact without knowing which stage it holds. The
walk compensates with `PAYLOAD_FREE` (MOD-02), and the type checker cannot see the two calls that
rely on the convention.

**Recommendation.** Fix in Phase 4. Add `key()` to the protocol. The two payload-free stages
return the hash `run` would, and the two `type: ignore` comments go.

**User-visible.** API: `nanopnp.Stage` gains a member, so a stage written outside the package must
define it.

### MOD-02 — The walk holds what the stages should declare

*Area:* stages. *Severity:* medium.

**Measured** (`stage_sets`, `function_literals`, `extension_points`, at `97f2b3d`). `io/run.py`
writes six module-level collections of stage names: `PIPELINE` (13), `PAYLOAD_FREE` (2),
`STRUCTURE_STAGES` (4), `WORKSPACE_STAGES` (10), `STORE_STAGES` (2) and `_WEIGHTS` (13). Its
`selected_stages` writes six more stage-name literals for its drop rules. Stage names are spelled
as strings in 43 modules outside `core/stages.py`, 69 times in `io/run.py` alone.

**Consequence.** The registry describes each stage's inputs and outputs, but the walk does not
read them. It decides order, workspace, store access, caching and progress weight from its own
lists. Adding a stage means editing the registry, the class and up to seven places in
`io/run.py`, and a Tier-1 test catches only two of them (`WORKSPACE_STAGES` and `STORE_STAGES`
against the constructors).

**Recommendation.** Fix in Phase 4. Move the per-stage facts into the registry entry: whether a
stage takes a workspace or the store, whether it has a payload, and its progress weight. Derive
`PIPELINE` from registration order, as `registered_stages` already sorts. The drop rules of
`selected_stages` are case logic and stay.

**User-visible.** No. `registered_stages()` descriptions may gain fields, which is additive.

### MOD-03 — Ten subpackages form one import cycle

*Area:* coupling. *Severity:* medium.

**Measured** (`components`, `component_edges` on the `top` relation, at `97f2b3d`). One strongly
connected component of 10 subpackages: `charge`, `density`, `geometry`, `io`, `materials`, `mesh`,
`physics`, `solve`, `structure`, `symmetry`. Twelve of its edges are carried by one import
statement each:

| Edge | The one import |
|---|---|
| `charge → mesh` | `charge/stage.py:119` |
| `charge → physics` | `charge/stage.py:120` |
| `geometry → density` | `geometry/contour.py:68` |
| `io → charge` | `io/case.py:53` |
| `io → materials` | `io/case.py:64` |
| `io → mesh` | `io/fields.py:62` |
| `materials → charge` | `materials/fields.py:35` |
| `materials → density` | `materials/fields.py:43` |
| `materials → mesh` | `materials/fields.py:44` |
| `mesh → materials` | `mesh/sizing.py:38` |
| `mesh → solve` | `mesh/distance.py:45` |
| `physics → mesh` | `physics/models.py:51` |

`mesh/distance.py` also imports `physics` (line 44), the Poisson solve behind the wall distance.

**Consequence.** §5.1's one subpackage per module is a naming convention and not a layering. No
member of the cycle can be imported, tested in isolation or replaced without loading the other
nine. A future backend (QR-13) or a second mesher (ADR-002) has no layer boundary to stop at.

**Recommendation.** Fix in Phase 4: the cheap cuts first. Each removes a row from the YAML, and
the cycle is re-measured after each. The wall-distance solve in `mesh/distance.py` belongs with
`physics` or `solve`. `materials/fields.py` takes a field type from `charge`. `io`'s three cuts
are MOD-04's. A cut that needs more than moving a definition is reported back rather than forced.

**User-visible.** No.

### MOD-04 — io is both the base layer and the assembler

*Area:* coupling. *Severity:* medium.

**Measured** (`subpackage_relation`, at `97f2b3d`). Fifteen subpackages import `io`. The ten
pipeline subpackages import `io.artefact` 23 times, `io.case` 23 times (9 of them under
`TYPE_CHECKING`) and `io.defaults`, `io.fields` and `io.store` 7 times. In the other direction,
`io` imports `charge`, `materials`, `mesh`, `physics` and `solve`, mostly from `io/case.py`
(3,160 lines), which resolves a case by asking each registry what it admits.

**Consequence.** The artefact types and the case schema, which every stage needs, live in the
same subpackage as the assembler that dispatches to every stage. That makes `io` the hub of
MOD-03's cycle. A stage cannot read its own resolved case without, transitively, importing the
physics registry that resolution consults.

**Recommendation.** Fix in Phase 4. Split `io` into a base, holding the artefacts, the store and
the resolved-case types and imported downward only, and an assembler, holding resolution, the walk
and reproduction, which imports the stages. `io/case.py` divides along the same line (MOD-13).

**User-visible.** No. `PUBLIC` names keep their meaning, and internal module paths are not API
(IF-01).

### MOD-05 — The exit-code table lives in the shell and the library imports it

*Area:* coupling. *Severity:* low.

**Measured** (`subpackage_relation`, at `97f2b3d`). Five modules outside `cli` import
`cli/errors.py`: `sweep/run.py:42`, `validation/examples.py:43`, `gui/app.py:46`,
`gui/run_model.py:43` and `gui/solver.py:57`. Its exit-code table names
`nanopnp.gui.probe:PayloadError` as a string (`cli/errors.py:253`). On the runtime relation `cli`,
`sweep` and `validation` form a cycle, and on the static relation `nanopnp` joins it.

**Consequence.** IF-02's classification of an error into an exit class is library knowledge,
since the sweep runner records a member's class. It sits in a shell, so the library depends on its
own command line.

**Recommendation.** Fix in Phase 4. Move the classification and the exit codes to `core`. `cli`
re-exports them for its own use.

**User-visible.** No. The exit codes do not change (VER-47).

### MOD-06 — The mesher is a branch, not a registry

*Area:* extension. *Severity:* medium.

**Measured** (`extension_points`, at `97f2b3d`). The schema admits `numerics.mesh.backend` as
`Literal["netgen", "gmsh"]` (`io/case.py`), and `mesh/generate.py` branches on
`backend == "gmsh"` at line 323. The two names are spelled as strings in 4 modules outside the
schema, 14 times in `mesh/adapter.py` and 8 in `mesh/generate.py`.

**Consequence.** ADR-002 makes the mesher an adapter. A third mesher needs edits to the schema, to
the generator's branch and to the adapter's format table. That is three modules in two
subpackages, against the one class QR-14 asks of a physics model.

**Recommendation.** Defer to Phase 6. One alternative mesher exists and none is planned. Recording
the shape now lets the 3D work (N4) decide whether a registry is worth its indirection.

**User-visible.** No.

### MOD-07 — The linear solver is a branch, and the schema reads its list

*Area:* extension. *Severity:* medium.

**Measured** (`extension_points`, at `97f2b3d`). `solve/linear.py` defines `AVAILABLE_SOLVERS`
(`superlu`, `umfpack`) and branches on `solver == "superlu"` at line 152. `io/case.py` imports the
set to validate `numerics.linear.solver`. The names are spelled in 2 modules outside
`solve/linear.py`.

**Consequence.** A new direct or iterative solver (PARDISO, MUMPS, or an iterative solver for 3D)
edits the branch and the set. The schema's import is one of the edges MOD-04 cuts.

**Recommendation.** Defer to Phase 6, with MOD-06, for the same reason.

**User-visible.** No.

### MOD-08 — Five registries in four shapes

*Area:* extension. *Severity:* low.

**Measured** (`extension_points`, at `97f2b3d`).

| Registry | Home | Members | Registration |
|---|---|---|---|
| Stages | `core/stages.py` | 13 | `register(description, "module:Class", extra=)`, imported on `create` |
| Corrections | `materials/models.py` | 1 file (`willems2020_nacl`) | A YAML file under `data/corrections/`, or `register(name, builder)` |
| Physics models | `physics/models.py` | 6 | `register_model(name, builder, declaration)` |
| Stabilisation | `physics/stabilisation.py` | 2 | `register(name, builder)` |
| Charge forms | `charge/fields.py` | 3 | `register_form(name, builder)` |

`none` is not counted, because every switch takes it.

**Consequence.** Each registry refuses a duplicate and lists its members in its own words. The
shapes differ where they need to: stages are lazy so that introspection imports nothing, and
corrections are files (FR-16). They also differ where nothing requires it, which a contributor
learns five times.

**Recommendation.** Post-1.0. The differences are deliberate where they matter, and unifying the
rest moves code without changing what can be extended.

**User-visible.** No.

### MOD-09 — Outputs and steric models are closed enumerations in the assembler

*Area:* extension. *Severity:* low.

**Measured** (`extension_points`, at `97f2b3d`). `io/case.py` defines `OUTPUTS` (6 members) and
`STERIC_MODELS` (`borukhov`, besides `none`). The outputs are spelled in 15 modules outside
`io/case.py`, 11 times in `physics/models.py` and 8 in `post/stage.py`. The correction forms of
`materials/forms.py` (6) are spelled nowhere else: a parameter file names them, and that is the
FR-16 shape working.

**Consequence.** A new quantity of interest edits the schema's enumeration, the post-processing
stage and, through the declaration, the physics model. A second steric model edits the schema and
the forms. Neither is reachable from a plugin.

**Recommendation.** Defer to Phase 5. The GUI phase (F5) decides how outputs are offered to a
user, and the enumeration's shape should follow that.

**User-visible.** No.

### MOD-10 — The backend interface of section 5.4.1 does not exist

*Area:* extension. *Severity:* high.

**Measured** (`backend_imports`, at `97f2b3d`). 33 modules in 11 subpackages import NGSolve or
Netgen: `physics` 9, `mesh` 4, `post` 4, `solve` 4, and `charge`, `geometry`, `gui`,
`materials` and `validation` 2 each, with `density` and `io` 1 each. None of the names §5.4.1
puts in scope (`FunctionSpace`, `TrialFn`, `TestFn`, `dx_axi`, `Coefficient`) is defined.
`physics/measures.py` defines the axisymmetric measure as `Measures`, which is the one piece that
exists.

**Consequence.** QR-13 SHALL express the weak forms once against the internal interface. They are
expressed once, but against NGSolve directly. The single statement holds and the abstraction does
not. §5.4.1's purpose, to bound the work of a DOLFINx backend for 3D and MPI, is not met. The
backend reaches eleven subpackages, not one.

**Recommendation.** Amend the specification, and defer the interface to Phase 6. An interface
with one implementation cannot be tested for the property it exists for. Writing one now would
wrap NGSolve without proving the wrapper fits DOLFINx. The amendment states QR-13 as met by the
single statement, and §5.4.1 as the shape a second backend takes when N4 is planned. It also
confines new `ngsolve` imports to the subpackages that already have them, which VER-61's
machinery can pin.

**User-visible.** No.

### MOD-11 — with_section and register are outside PUBLIC

*Area:* surface. *Severity:* low.

**Measured** (`surface`, at `97f2b3d`). `PUBLIC` has 26 names. `io.case.with_section` and
`core.stages.register` are not among them. WP34 D9 left both out and carried the question to this
report.

**Consequence.** A user adding a stage, or editing a case document section by section, imports an
internal module that may change before v1.0 without a `CHANGELOG.md` break entry.

**Recommendation.** Fix in Phase 4: add both, or rule them internal and say so in the API page.
The user-testing sessions (G7) would show which, so the ruling may wait for them.

**User-visible.** API: added names are additive.

### MOD-12 — PUBLIC is mirrored by hand for the type checker

*Area:* surface. *Severity:* low.

**Measured** (`surface`, at `97f2b3d`). `nanopnp/__init__.py` lists the 26 names twice: as the
`PUBLIC` table, resolved lazily, and as `TYPE_CHECKING` imports. The two agree today.

**Consequence.** A name added to one and not the other is either untyped for users or eagerly
importable. Nothing but review holds the two together.

**Recommendation.** Fix in Phase 4 with a Tier-1 assertion that the two lists are equal. This
module already measures both.

**User-visible.** No.

### MOD-13 — Three modules and two functions are past review size

*Area:* surface. *Severity:* low.

**Measured** (`sizes`, at `97f2b3d`). `io/case.py` has 3,160 lines, `physics/models.py` 2,660
and `cli/__init__.py` 1,266. `cli/__init__.py` holds `build_parser` (217 lines), and
`solve/continuation.py` holds `default_ladder` (433 lines). The next longest function is
`solve/newton.py` `damped_newton`, at 202.

**Consequence.** A change to the case schema, a physics model or the command line is reviewed
against a file no reviewer reads whole.

**Recommendation.** Fix in Phase 4 for `io/case.py`, as part of MOD-04's split. Defer the rest to
Phase 5: `cli/__init__.py` with the GUI's shell work, and `physics/models.py` and
`default_ladder` with whatever MOD-10's amendment decides.

**User-visible.** No.

### MOD-14 — Refusals name releases that have shipped

*Area:* surface. *Severity:* medium.

**Measured** (`version_literals`, at `97f2b3d`). Seven non-docstring strings name a release:
`charge/stage.py:306`, `io/case.py:2353`, `2399`, `2405` and `2714`, `io/defaults.py:119` and
`mesh/ingest.py:700`. Among them, `numerics.nonlinear.strategy` is refused as "the NUM-20
fallback ladder, which is v0.2", and `inputs.charge: artefact:` as filled by "the charge pipeline
of v0.4". Both releases have shipped. `_require_runnable` also loops over `_UNCONSUMED_INPUTS`,
which is empty, to raise "not delivered in this release".

**Consequence.** A user reads that a feature belongs to a release they are running. The texts are
user-visible (IF-02), and a refusal that misstates the schedule teaches the user to distrust the
rest.

**Recommendation.** Fix in Phase 4. Each refusal names the requirement and says that no release
schedules it, or names the release that does. The empty loop goes. A Tier-1 check over
`version_literals` keeps stale release names out.

**User-visible.** CLI: refusal texts change. Exit codes do not.

### MOD-15 — core reaches upward, once by an annotation and into ten subpackages by the registry

*Area:* coupling. *Severity:* low.

**Measured** (`subpackage_relation`, at `97f2b3d`). `core/stages.py:44` imports from `io` under
`TYPE_CHECKING`, which puts `core` in the static cycle. The stage registry's targets are strings
naming modules in ten subpackages.

**Consequence.** The string edges are the registry working as designed: introspection imports
nothing (VER-25). The annotation import is the only thing that makes the base layer depend on the
assembler.

**Recommendation.** Fix in Phase 4, with MOD-04. The annotated type moves to the base half of
`io`, or to `core`. The string edges stay, recorded in the YAML.

**User-visible.** No.

### MOD-16 — The stabilisation registry is closed by a Literal in the schema

*Area:* extension. *Severity:* medium.

**Measured** (`extension_points`, at `97f2b3d`). `physics/stabilisation.py` registers `supg` and
`reference` by `register(name, builder)`, and `CaseDocument` checks the case against
`registered_stabilisations()`. The schema field is also
`stabilisation: Literal["none", "supg", "reference"]` (`io/case.py:662`), so a mode registered
at run time is refused by validation before the registry is consulted. `physics.model`, by
contrast, is a string checked against its registry.

**Consequence.** The registry offers an extension point that the schema closes. Registering a
mode is not enough, and `io/case.py` must also be edited.

**Recommendation.** Fix in Phase 4. Make the field a string, validated by the registry check
that already exists, as `physics.model` is.

**User-visible.** Schema: the JSON schema of `numerics.stabilisation` loses its enumeration.
Every document that validated still validates.

### MOD-17 — The validated correction set is a default in eight signatures

*Area:* extension. *Severity:* low.

**Measured** (`extension_points`, at `97f2b3d`). `willems2020_nacl` is the default value of a
parameter in five functions of `physics/models.py` and one each of `solve/continuation.py`,
`materials/electrolyte.py` and `io/case.py`. `io/defaults.py` names it six times, as the validated
default every deviation is measured against (FR-25).

**Consequence.** The validated default is stated in one place (`io/defaults.py`) and repeated in
eight. A second electrolyte is still a data file (FR-16 holds), but changing which set is the
default means nine edits.

**Recommendation.** Post-1.0. Nothing plans a second default. The defaults would read from
`io/defaults.py` once it sits in the base layer (MOD-04).

**User-visible.** No.

## Seed findings merged or added

WP35's plan listed 14 measured candidates (Design §4). All 14 are here, as MOD-01 to MOD-14 in
the plan's order. The measurement added three:

- **MOD-15**: `core`'s single upward annotation import.
- **MOD-16**: the stabilisation `Literal`.
- **MOD-17**: the repeated default correction set.

None was dropped or merged.
