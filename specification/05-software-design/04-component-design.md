---
type: Specification
title: "5.4 Component design"
description: "Specifies the component interfaces: the weak forms stated once as terms that name no backend, the correction-model interface, the physics-model interface and the kernel of registered terms."
---

### 5.4 Component design

#### 5.4.1 Backend abstraction layer

`physics/` states the weak forms once (QR-13), as the terms of the kernel (§5.4.4), and a term names no
backend: it takes its operators and its geometry from the kernel's context (§8.2.62 BL6). NGSolve, the
single production backend (CON-06), stands behind the context, the slot and the measure. The backend's
reach is confined to the subpackages that `docs/project/modularity-layering.yaml` lists under `backend:`,
and within `physics/` no module that holds a term imports it; VER-65 checks both.

| The interface | Held by |
|---|---|
| `FunctionSpace`, product spaces | The model's field set, which the kernel's context is built on |
| `TrialFn`, `TestFn` | The context: the trial, test and lagged functions |
| `grad`, the products, the elementary functions, the element size | The context's operators |
| The coordinates, the dimension, the axial direction, the identity | The context's geometry |
| `dx_axi`, the axisymmetric measure; `ds`, boundary measures | `Measures`, and the slot's domain and rule |
| `Coefficient` | The coefficients of each side (§5.4.2) |

Out of scope: a general symbolic layer or user-facing PDE language (§5.5); mesh generation, held by the
mesh adapters; continuation, warm start and linear-solver selection, held by `solve/`; IO, provenance and
caching, held by `core/` and `io/`; any construct required by only one backend.

NOTE (QR-13; §8.2.8 H3; §8.2.50 AZ1; §8.2.62 BL6): the kernel's packages of Phase 6, WP6.10 to WP6.12,
build this layer, and VER-65 takes the rule on a term's module with the first. Until the first merges,
`physics/models.py` `CoupledModel` assembles the coupled forms directly against NGSolve, and the
single-field models theirs until the last, their reach pinned by VER-65 alone. The layer's geometry is
tested under a second measure by Phase 6's benchmarks in 3D
(CON-01's NOTE). That the layer fits a second backend, DOLFINx for 3D and MPI, is not shown: with one
backend it cannot be tested for that, and it is the shape such a backend would take when N4 is planned.
A stage outside `physics/` on VER-65's list still reaches NGSolve directly.

#### 5.4.2 Correction-model interface

A correction model is a class implementing `evaluate(c_avg, wall_distance) -> value` plus
`parameters` and `provenance`, registered by string name, with fit coefficients in versioned data
files such as `data/corrections/willems2020_nacl.yaml` (FR-16). The case file names models by
string. Disabling a correction selects the `none` model rather than taking a code branch (PHY-22).

#### 5.4.3 Physics-model interface

A `PhysicsModel` declares its field set, its weak-form contributions, its boundary-condition
vocabulary and its default solve strategy (FR-20). From the kernel (§5.4.4) its weak-form contributions
are a registered list of terms, and a variant of a model is a difference of lists or of switch values,
never a subclass (FR-40; §8.2.62 BL1). The geometry, mesh, charge, solver,
post-processing, sweep, provenance and interface layers are model-agnostic, so adding a model
changes none of them.

NOTE (what a model declares; WP26): a model is registered by name
together with a declaration that can be read without building it. The declaration states the
case-derived options its builder takes, which are the resolved `model_options`; the value set of each
`physics:` switch it honours; whether it carries solid materials, and which supplied coefficients it
accepts (the fixed charge, `χ`); whether it reads the PHY-02 distance field; the values of
`numerics.continuation` it admits; whether it solves ionic transport; and its terms, each the PHY or
NUM clause it is written from, its equation in that clause's symbols as the model assembles it, the
`physics:` switches it is assembled under, each a switch the model honours true, and the correction
leaf, one the model reads, whose `none` model leaves it out, so a reader shows the equations a case
solves without building the model (WP5.18). It lists no quantities of
interest: a registered output states what it needs of a declaration, ionic transport or the flow
switch's `true`, and a model provides every output whose need its declaration meets (§6.7; §8.2.32 AH1). Every built model reports its field set, boundary vocabulary, essential
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

#### 5.4.4 The kernel of registered terms

The kernel composes a physics model from five kinds of record, each of which a reader lists without
building a model (FR-40; §8.2.53 BC1, BC2; §8.2.62 BL1):

| Piece | What it is | Rule |
|---|---|---|
| Term | One part of the equations, written from one PHY or NUM clause: its display record (§5.4.3's NOTE) and the contributions it adds | A flux term states its drift once and a force term its force density once. The weak form, the stabilisation (§6.4), the indicator current (NUM-24) and the forces (NUM-28) read that one statement, and no term keeps its drift or its density from a reader (§8.2.62 BL5) |
| Slot | One integral of one equation: the field whose test function it takes, its domain, its quadrature rule, and how the summed contributions close into the integrand | The kernel sums a slot's contributions and integrates once. A term never owns an integral and never chooses its test function. Each slot states its rule, at order 3 or more where the form carries `1/r` (VER-07) |
| Coefficient | A corrected property, built once for an assembly from its registered correction model (§5.4.2; PHY-22) | Every term that reads the property reads the same object. Switching a correction to `none` changes the coefficient, never a term |
| Switch | A record: its name, its case path, its validated default, the terms it brings in force, and what it requires and excludes | PHY-23's switch brings both of its terms in force or neither (PHY-08). Every list of switches and every list of deviations (FR-25) is derived from the records |
| Model | A list of terms with a field set, a boundary vocabulary and a strategy (§5.4.3) | `pnp-ns` is `epnp-ns` with the classical correction set, and `pnp` is `epnp-ns` without the flow's terms. A model's declared terms are those it assembles |

A term assumes no dimension and no backend (§5.4.1). The more modular and maintainable structure is
preferred to holding a stored number, and a number that the kernel moves is handled as VER-62 says
(§8.2.62 BL1, BL2).

The kernel's own tests (FR-40) are of Tier 1: a slot with two contributions assembles as one integral,
where their sum integrated term by term under a moved rule does not; a term left out changes its own slots
alone; the stabilisation's wind is the sum of the drifts in force; PHY-23's switch brings both terms or
neither; a model registered as a list of terms runs from a case file, its declared terms those assembled. Of
Tier 2 it has the analytic benchmarks, unchanged. Each takes its clause in §7 with the package that writes it.

NOTE (§8.2.62 BL1, BL3): WP6.10 to WP6.12 build the kernel, and until the last merges `CoupledModel`
assembles the coupled models in one class. [The kernel's design](../../docs/design/kernel.md) holds the
slots, the switch records, the names the workbench reads and what the prototype showed.
