---
type: Specification
title: "5.5 Extension points"
description: "Specifies the three levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration."
---

### 5.5 Extension points

Pluggability has three levels, matching the kinds of change users make (QR-14; ADR-005). Below them, the
backends of the discretisation are registries as well (§8.2.8 H7): a mesher (`numerics.mesh.backend`,
`mesh/meshers.py`), a linear solver (`numerics.linear.solver`, `numerics/linear.py`) and a
stabilisation mode (`numerics.stabilisation`, `physics/stabilisation.py`) are each added by one
registration, and each key is a string checked against its registry when a case is loaded, as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and `sparsecholesky`
cannot be registered (NUM-21). An installed package registers through one registrar, below; the
registering functions stay internal (REV-67; §8.2.62 BL8). The outputs a case may select (`outputs:`, `post/outputs.py`) and the steric models
(`electrolyte.corrections.steric.model`, `physics/steric.py`) are registries of the same kind, each added by one
registration and checked against its registry when a case is loaded (MOD-09; §8.2.18 T4); an output states what it needs of a
model's declaration, and a model provides every output whose need it meets (§5.4.3; §8.2.32 AH1). A pipeline stage is extended through one call on a `Session`, below;
`core.stages.register` and `StageDescription` are internal (§8.2.23 Y10). A physics model's
registry, unlike it, serves the whole process: a case names its model and is checked when it is
loaded, before any `Session` exists (§8.2.23 Y9).

NOTE (the steric model; PHY-05; PHY-22): a steric model is a form `(variables, coefficients, species) -> β̃_i`
registered by name. `borukhov` is PHY-05 and the validated default; `none` sets `β_i = 0` and is the off value, offered beside
the registry as a correction's `none` is, and it cannot be registered. Any other registered name is a deviation from the
validated model (FR-25): it is listed among the model's deviations, and its name enters the solve key as
`electrolyte.steric_model`, so a second form never shares a key with `borukhov`. The keys of `borukhov` and of `none` are
those of a release that had no registry, and the case schema's identifier is unchanged.

NOTE (FR-27, a stage of one's own; QR-14; §8.2.23 Y10, UT-10): a stage of one's own is a Python
function registered on a `Session` by `session.register_stage(function, *, name=None)`, its name
the function's own unless given. Each parameter of the function names a stage the Session walks
before it, `case` included, and receives that stage's artefact; the function returns a summary, a mapping the
canonical encoding of §5.3.2 accepts. The call builds and registers the stage: the Session walks it after
every built-in stage and every stage registered on it before, takes no workspace and no store, is checked for cancellation
before the function runs, and emits an artefact of schema `nanopnp/stage/<name>/v1` whose summary
is what the function returned. Its key is the hashes of the artefacts it reads and a digest of the
function's code object (its bytecode, constants and names, nested code included), so an edited
function misses the cache rather than serving its old result, and registering a function again
on that Session under its name replaces the earlier one; another Session never sees it. What the function reads besides its parameters, a global,
a closure or a file, is not keyed. A name that is a built-in stage's, or not of the form
`[a-z][a-z0-9_-]*`, a parameter naming no registered stage, a keyword-only or variadic parameter,
and a return value that is not such a mapping are each refused naming it.

NOTE (the rebuild forecast, FR-39, FR-27, VER-64; WP5.07; §8.2.31 AG5): a stage MAY provide
`forecast_parameters(inputs) -> Mapping`, the protocol `core.stages.Forecastable`, for the sweep's forecast
(§5.3.4). A stage's key that reads an upstream payload the forecast has not built raises
`core.stages.NotBuilt`. The stage is then identified by a hash of its name and its
`forecast_parameters`, which SHALL include the hash of each upstream artefact the key reads and
nothing of the case the key does not read (the mesh returns its region's hash and its sizing, so a
bias does not move it). A stage without `forecast_parameters` is identified by the case's hash and its
declared inputs' identities, so any change of the case moves it. The forecast never calls `run`.
The method is optional, adds nothing to the key, and a stage of one's own needs none.

NOTE (optional members, FR-27, VER-64; WP5.08; §8.2.18 T2): the optional members of a stage are the
runtime-checkable protocols of `core.stages`, and the walk tests each by `isinstance`, never by
`hasattr`: `ContributesDeviations` (`deviations(inputs)`, which a stage defines to add to the run's
deviations list), `SolveReporting` (`with_solve_hook(hook)`) and `Forecastable` (`forecast_parameters(inputs)`).
A member a stage defines SHALL have its protocol's signature, which VER-64 reads from the syntax tree,
so a stage whose `deviations` takes no `inputs` is found by the test and not skipped by the walk.

| Level | Unit of extension | Requires | Obtained free |
|---|---|---|---|
| 1, correction models | A versioned data file naming a registered model and its coefficients | No code | Recording of the model version on every result; correction-by-correction switching as a configuration sweep |
| 2, terms | One registered term of the kernel (§5.4.4), within electrolyte transport (N1) | One function, which names no backend (§5.4.1) | Every reader of the term: the weak form, the stabilisation, the indicator current, the forces, the displayed equations and the manifest |
| 3, physics models | A registered list of terms with a field set, a boundary vocabulary and a strategy (§5.4.3); one class until WP6.12 | One file | Meshing, geometry, charge assembly, continuation, QoI extraction, sweeps, provenance and the GUI |

NOTE (an installed package; FR-40; §8.2.53 BC5; §8.2.62 BL8): an installed package declares its terms,
corrections, shapes or solvers through one entry point in the group `nanopnp.extensions`, which resolves to
a function that receives one registrar and registers through it. The library reads the group at the first
use of any registry, once a process, so the command line, the workbench and the Python interface find the
same set. An extension that fails to import or to register SHALL be refused, naming its package and
version, and never skipped: a run that silently lacks a term is a plausible wrong answer. Each registration
is recorded with its package and version, and a run's manifest names every extension whose registration
the run used (FR-25). A term states the analytic case that verifies it, a `VER-` identifier or a
manufactured solution; one that states none is marked unverified in the manifest and beside the displayed
equations. WP6.16 builds this; until it merges nothing reads the group.

Shipped physics models (PHY-21, FR-18, FR-19).

| Model | Fields | Notes |
|---|---|---|
| `epnp-ns` | φ, c_i, u, p | The validated default |
| `pnp-ns` | φ, c_i, u, p | The same model with corrections off; a configuration, not code |
| `pnp` | φ, c_i | No flow coupling |
| `pb` | φ | Nonlinear Poisson–Boltzmann, equilibrium; a separate model, not the PNP solver at zero bias (PHY-14, PHY-24) |
| `pb-linear` | φ | Debye–Hückel; an initialiser |
| `poisson` | φ | Electrostatics only; the APBS cross-check target |

Since ePNP-NS reduces exactly to PNP-NS at β_i = 0 with all f^c = f^w = 1, the PNP-against-ePNP
comparison and the contribution of each individual correction are configuration sweeps, and are the
project's primary differential-testing instrument (§7.4).

Boundary of the framework (N1): a nanopore transport solver with swappable physics models, which
will not become a general symbolic PDE framework. A developer writes terms within electrolyte
transport, and a model may be swapped, extended or composed of them (FR-40; §8.2.53 BC5); an
unrelated multiphysics problem may not be posed, and users wanting
arbitrary weak forms should use NGSolve or FEniCS directly. Deriving new correction
parameterisations from MD is a separate later tool (N6).
