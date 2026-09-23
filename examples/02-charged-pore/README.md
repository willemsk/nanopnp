# 02 · A charged pore, and classical PNP-NS against ePNP-NS

**For:** the collaborating computational scientist (P2) modelling a pore that selects between
ions.
**Runtime:** under a minute. **Needs:** nanopnp installed (the getting-started page of the documentation).
**Exercises:** IF-05, FR-14, FR-23, FR-25, PHY-19, PHY-21, PHY-22.

Biological pores carry fixed charge, and it is what makes them select one ion over another. This
example supplies a fixed charge to the pore of [example 01](../01-quickstart/README.md) and solves
the same case twice: once with the validated ePNP-NS model, and once as classical PNP-NS, with every
correction switched off.

Run every command from this directory; in a development checkout, put `uv run` in front of each.

## The fixed charge

`ring.field.yaml` is a field header (`schema: nanopnp/field/v1`). It declares what the field is
(an areal charge density in the `(r, z)` half-plane), its net charge `q_net_e`, and where its values
come from. Here they come from a registered analytic form: a Gaussian ring, the reference model's own
smearing kernel, sitting in the membrane just behind the pore wall. A real pore's charge map arrives
the same way, with `data:` naming a grid file in place of `form:`.

The case names the header under `inputs.charge` with `format: field1`. Stage 7 interpolates the
field onto the mesh, then checks that the charge it deployed is the charge that was declared
(PHY-19). If it is not, the run aborts and says by how much, and where. See the fields page of the
user guide for the three quantities a field may carry, and why an absolute permittivity field is
refused.

## The commands

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out pore.msh
$ nanopnp run epnpns.case.yaml --store store --run-dir run-epnpns
$ nanopnp run classical.case.yaml --store store --run-dir run-classical
$ nanopnp inspect run-classical
```

Both runs share the mesh and the charge artefacts in `store/`. Each stage's key is the hash of its
inputs, so the second run computes only what its corrections change.

`classical.case.yaml` differs from `epnpns.case.yaml` only in `electrolyte.corrections`: each
correction selects its registered `none` model. Classical PNP-NS is a *configuration* of the same
solver, not a separate code path (PHY-21, PHY-22). `nanopnp inspect run-classical` shows the
consequence. The manifest's `deviations` block lists every switch that differs from the validated
model, with the value this run used and the validated default beside it (FR-25). The ePNP-NS run's
list is empty.

## What the test asserts

`tests/tier2/test_examples_02_charged_pore.py` runs the commands above, verbatim, from a copy of
this directory, and checks properties of the model rather than numbers:

- **counter-ion selectivity**: in both runs, the cation transport number `t+` is above ½. A negative
  fixed charge enriches cations in the pore, so they carry most of the current. A sign error
  anywhere between the field header and the Poisson source would push `t+` below the uncharged
  pore's value, and this check would fail;
- the classical run's manifest lists each of the six correction switches under its deviations, and
  the ePNP-NS run's lists none;
- the two current-extraction routes of FR-23 agree to the tolerance the solver gates on.

No number from these runs is quoted here. The magnitude of `t+` depends on the mesh, the charge and
the salt, and it is not a validated prediction.

## Next

[03](../03-iv-sweep/README.md) sweeps the bias and shows a pore charged on one side rectifying.
