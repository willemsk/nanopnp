# The model

nanopnp's model is documented by its two normative records, rendered here **verbatim**:

- **[The specification](../_generated/model/specification.md)**, `SPECIFICATION.md`, is normative.
  Its requirements (`FR-`, `QR-`, `CON-`), physics (`PHY-`, §4), numerics (`NUM-`, §6) and
  verification (`VER-`, `VAL-`, §7) are what the code implements and the tests discharge.
- **[The knowledge base](../_generated/model/knowledge/00-index.md)**, `.knowledge/`, is the
  verified background: the physics and its errata, the numerics, the biology, the ClyA geometry and
  charge, the reference COMSOL settings, and the tooling. Each claim is marked **[tested]** or
  **[verified]** and cites its source.

This page restates no equation, and neither does the rest of this documentation. Summaries of this
model circulate that are wrong: the wall function's sign, the steric flux's sign and several
printed coefficients have all been copied incorrectly. `.knowledge/01` §8 and the specification's
§4.6 record five errata in the original sources, with the arithmetic. Where the printed sources and
the reference model report disagree, the model report governs. Read the equations in the records
themselves.

## Where each case-file switch is specified

Each switch below is a field of the case file. The [case-file
reference](../_generated/reference/case-file.md) gives its values and its validated default; this
table says where the specification defines what it does.

| Case-file path | Specified by |
|---|---|
| `physics.model` | PHY-21 (the named models), PHY-24 (Poisson–Boltzmann is its own model) |
| `electrolyte.corrections.<property>.model` | PHY-22 (each correction independently switchable), PHY-10–PHY-13 (the forms, the coefficients, the validity range) |
| `electrolyte.corrections.<property>.concentration`, `.wall` | PHY-10, PHY-11 (the two parts of each correction) |
| `electrolyte.corrections.steric.model` | PHY-04, PHY-05 (the size-modified flux and its sign), PHY-06 (the packing gate) |
| `electrolyte.driver` | PHY-01 (the correction driver is the mean ion concentration, not the ionic strength) |
| `electrolyte.parameters` | PHY-12, §11 (the coefficients and their provenance) |
| `physics.flow`, `physics.variable_density`, `physics.inertia` | PHY-07, PHY-08 (the flow and its body force), PHY-22 |
| `physics.dielectric_gradient_forces` | PHY-23 (an opt-in deviation, off in the validated model) |
| `physics.solid_permittivities` | PHY-03, PHY-20 (permittivity by domain) |
| `boundary_conditions.*` | PHY-09 (the boundary conditions), NUM-24 (the current's sign) |
| `inputs.charge`, `inputs.eps_r` | PHY-16–PHY-20 (fixed charge, the axis guard, conservation, the dielectric), and the §5.3.1 `inputs.charge` NOTE |
| `numerics.wall_distance.*` | PHY-02 (distance to the pore boundary only), NUM-31, NUM-34 |
| `numerics.elements.*` | NUM-01, NUM-03 (the element orders and the velocity–pressure pair) |
| `numerics.stabilisation` | NUM-11–NUM-15 (§6.4) |
| `numerics.nonlinear.*` | NUM-16, NUM-17 (damped Newton and its per-step gates), NUM-20 (fallbacks) |
| `numerics.continuation` | NUM-18 (the ladder, and its NOTE on what it refuses) |
| `numerics.linear.solver` | NUM-21 (sparse direct), CON-11 (the licence of the default solver) |
| `outputs` | NUM-23–NUM-29 (§6.7: the current's two routes, the derived quantities, the analyte force) |

## Verification

What the code is tested against, and how, is §7 of the specification. The worked
examples in this documentation are part of it (VER-46): each asserts a property of the model, never
a transcribed number.
