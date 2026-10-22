---
type: Specification
title: "5.4 Component design"
description: "Specifies the physics/ design: weak forms written once against a thin internal interface, with one production NGSolve implementation."
---

### 5.4 Component design

#### 5.4.1 Backend abstraction layer

`physics/` expresses the weak forms once against a thin internal interface, with one production
implementation on NGSolve (QR-13, CON-06). Its purpose is to make a future DOLFINx backend for 3D
and MPI bounded work.

| In scope | Out of scope |
|---|---|
| `FunctionSpace`, product spaces | A general symbolic layer or user-facing PDE language (§5.5) |
| `TrialFn`, `TestFn`, `grad` | Mesh generation, held by the mesh adapters |
| `dx_axi`, the axisymmetric measure | Continuation, warm start, linear-solver selection, held by `solve/` |
| `ds`, boundary measures | IO, provenance and caching, held by `core/` and `io/` |
| `Coefficient` | Any construct required by only one backend |

NOTE (QR-13, §8.2.8 H3): the interface above is not built for v1. With one backend it cannot be
tested for the property it exists for, and a wrapper written now would wrap NGSolve without showing
that it fits DOLFINx. QR-13 is met by the single statement of the weak forms, against NGSolve
directly, and the backend's reach is pinned instead: the subpackages that import `ngsolve` or
`netgen` are the `backend:` list of `docs/project/modularity-layering.yaml`, which VER-65 asserts
in both directions: eleven, the eleven `MOD-10` measured and `numerics/` (§8.2.8 H11), less `io/`,
whose field export is `post/export.py`. The table
is the shape a second backend takes when N4 is planned, and Phase 6 or a later plan decides it.

#### 5.4.2 Correction-model interface

A correction model is a class implementing `evaluate(c_avg, wall_distance) -> value` plus
`parameters` and `provenance`, registered by string name, with fit coefficients in versioned data
files such as `data/corrections/willems2020_nacl.yaml` (FR-16). The case file names models by
string. Disabling a correction selects the `none` model rather than taking a code branch (PHY-22).

#### 5.4.3 Physics-model interface

A `PhysicsModel` declares its field set, its weak-form contributions, its boundary-condition
vocabulary and its default solve strategy (FR-20). The geometry, mesh, charge, solver,
post-processing, sweep, provenance and interface layers are model-agnostic, so adding a model
changes none of them.

NOTE (what a model declares; WP26): a model is registered by name
together with a declaration that can be read without building it. The declaration states the
case-derived options its builder takes, which are the resolved `model_options`; the value set of each
`physics:` switch it honours; whether it carries solid materials, and which supplied coefficients it
accepts (the fixed charge, `χ`); whether it reads the PHY-02 distance field; the values of
`numerics.continuation` it admits; the quantities of interest it provides (§6.7); and whether it
solves ionic transport. Every built model reports its field set, boundary vocabulary, essential
boundaries, NUM-09 scale set and provenance. A layer outside `physics/` reads these, and SHALL NOT
branch on a model's name or on its class: case validation refuses what the declaration does not
admit, the mesh gate requires the boundaries the model declares, the solve passes the coefficients
it accepts, and QoI extraction reaches the transport members through the declaration. The NUM-18
ladder is the one place outside `physics/` that names models, because §6.5 defines it as a path
through named models; it is a strategy a model admits, not a branch on the model, and only the
models it ends at, `epnp-ns` and `pnp-ns`, may admit it.

NOTE (what a model does not read; WP42): the declaration also states the case leaves the model does
not read. A value other than the schema default at one of them SHALL be refused at resolution, in
one message naming every such key, its default and the models that read it, because it would be
recorded in the FR-25 manifest and never applied. A leaf the schema requires has no default to be
refused away from, and is recorded: `poisson`'s `electrolyte.concentration_M`. A switch value that
is an exact identity of a model's equations is not honoured, and is refused likewise: `pnp`
honours `variable_density` and `inertia` false only, as the electrostatic models do, and `pnp-ns`,
whose density and permittivity are constant, honours `variable_density` true only and
`dielectric_gradient_forces` false only. The load-time inf-sup check runs only for a model that
reads `numerics.elements.u`, so a model without flow is refused on its flow switch (VER-71).
