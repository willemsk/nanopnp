---
type: Specification
title: "5.5 Extension points"
description: "Specifies the two levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration."
---

### 5.5 Extension points

Pluggability has two levels, matching the two kinds of change users make (QR-14). Below them, the
backends of the discretisation are registries as well (§8.2.8 H7): a mesher (`numerics.mesh.backend`,
`mesh/meshers.py`), a linear solver (`numerics.linear.solver`, `numerics/linear.py`) and a
stabilisation mode (`numerics.stabilisation`, `physics/stabilisation.py`) are each added by one
registration, and each key is a string checked against its registry when a case is loaded, as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and `sparsecholesky`
cannot be registered (NUM-21). Whether those registering functions are public is REV-67's, with the
composer phase (§8.2.18 T3). A pipeline stage is extended through one call on a `Session`, below;
`core.stages.register` and `StageDescription` are internal (§8.2.23 Y10). A physics model's
registry, unlike it, serves the whole process: a case names its model and is checked when it is
loaded, before any `Session` exists (§8.2.23 Y9).

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

| Level | Unit of extension | Requires | Obtained free |
|---|---|---|---|
| 1, correction models | A versioned data file naming a registered model and its coefficients | No code | Recording of the model version on every result; correction-by-correction switching as a configuration sweep |
| 2, physics models | One class against the §5.4.3 interface | One file | Meshing, geometry, charge assembly, continuation, QoI extraction, sweeps, provenance and the GUI |

Shipped physics models (PHY-21, FR-18, FR-19).

| Model | Fields | Notes |
|---|---|---|
| `epnp-ns` | φ, c_i, u, p | The validated default |
| `pnp-ns` | φ, c_i, u, p | The same model with corrections off; a configuration, not code |
| `pnp` | φ, c_i | No flow coupling |
| `pb` | φ | Nonlinear Poisson–Boltzmann, equilibrium; a separate model, not the PNP solver at zero bias (PHY-14, PHY-24) |
| `pb-linear` | φ | Debye–Hückel; an initialiser and the basis of the DWR error estimator |
| `poisson` | φ | Electrostatics only; the APBS cross-check target |

Since ePNP-NS reduces exactly to PNP-NS at β_i = 0 with all f^c = f^w = 1, the PNP-against-ePNP
comparison and the contribution of each individual correction are configuration sweeps, and are the
project's primary differential-testing instrument (§7.4).

Boundary of the framework (N1): a nanopore transport solver with swappable physics models, which
will not become a general symbolic PDE framework. Users do not write weak forms. A model may be
swapped or extended; an unrelated multiphysics problem may not be posed, and users wanting
arbitrary weak forms should use NGSolve or FEniCS directly. Deriving new correction
parameterisations from MD is a separate later tool (N6).
