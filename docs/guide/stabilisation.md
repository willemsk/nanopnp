# Stabilisation modes

`numerics.stabilisation` selects how the transport and flow operators are stabilised. It has three
values (the §5.3.1 `numerics.stabilisation` NOTE, §6.4):

| Value | What it is | When |
|---|---|---|
| `none` | plain Galerkin | **the default, and the production policy (NUM-11)** |
| `supg` | streamline-upwind Petrov–Galerkin on the transport operator | a coarse continuation mesh, never the final solve |
| `reference` | streamline and crosswind stabilisation on transport, plus the flow stabilisation, as in the reference COMSOL model (NUM-14) | like-for-like comparison against the published COMSOL currents |

## Why the default is `none`

Stabilisation adds terms to the equations. Those terms bias the current, the quantity the model
exists to predict, and destroy the Jacobian's symmetry. A mesh that resolves the double layer keeps
the cell Péclet number of electromigration small, and there plain Galerkin is accurate and
stabilisation buys nothing (§6.4.1). Every run records its largest cell Péclet number per species,
so you can see whether the mesh needed stabilisation.

## Why `reference` exists

The reference COMSOL model had streamline and crosswind stabilisation **on**, in transport and in
flow (`.knowledge/09`). Its currents therefore include the stabilisation's own contribution, and a
comparison against them is not like-for-like until ours does too. `reference` reproduces those
settings, and it is the only mode that permits the equal-order velocity–pressure pair the reference
used. The Tier-3 comparison runs it as one rung of an attribution ladder (§7.4), so a discrepancy can
be attributed to discretisation or to model.

## It is recorded with every number

The manifest's `stabilisation` group records the mode, its parameters and their provenance. Where a
mode is on, it also records the stabilisation's own contribution to each species' current, so a
stabilised number can be corrected, or at least read, for what the stabilisation added. Changing the
mode is a deviation from the validated model, and the manifest lists it. A sweep treats it as a
barrier: it never warm-starts across a change of mode.
