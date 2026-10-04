# 07 · From a PDB entry to a charged run

**For:** anyone bringing their own pore structure: the method developer (P1) or the collaborating
computational scientist (P2) who has a PDB entry and wants a charged solve from it.
**Runtime:** about five minutes on one core. **Needs:** nanopnp with the `structure` extra, as the
getting-started page of the documentation installs it.
**Exercises:** IF-02, IF-05, FR-12 to FR-15, FR-23, FR-25, FR-27, QR-12.

The cytolysin A pore (ClyA), PDB entry 2WCD, taken from the deposited file to a solve of the
validated ePNP-NS model with the pore's own fixed charge. [Example 06](../06-pdb-to-mesh/README.md)
built the mesh. This example goes on through stage 7, which protonates the structure with PDB2PQR
and PROPKA and deposits its charge on the mesh, and then solves. Along the way you export the
charges and the charge density, feed the charges back in, turn on the two FR-15 switches, and
watch a gate refuse a shortcut.

Run every command from this directory. Paths in the case files resolve against the working
directory, not against the case file. In a development checkout, put `uv run` in front of each
command.

## Walk the pipeline to a charged solve

<!-- example: run -->
```console
$ python ../06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb
$ nanopnp run 2wcd.case.yaml --store store --run-dir run
$ nanopnp inspect run
$ nanopnp stage protonation 2wcd.case.yaml --store store --export 2wcd.pqr
$ nanopnp stage charge 2wcd.case.yaml --store store --export charge.field.yaml
$ nanopnp run from-pqr.case.yaml --store store --run-dir run-pqr --upto charge
$ nanopnp run switches.case.yaml --store store --run-dir run-switches --upto charge
$ nanopnp inspect run-switches
```

1. **`python ../06-pdb-to-mesh/prepare.py`** prepares the entry exactly as example 06 does, with
   example 06's own script: chains A to L, protein only, the pore axis on z with the *cis* cap up,
   and the bilayer centre at z = 0. That example's README says why each step is needed.
2. **`nanopnp run 2wcd.case.yaml`** walks every stage. Stages 1 to 6 build the mesh, as in example
   06. Stage 7 then runs in two halves. **Protonation** runs PDB2PQR on the structure, with PROPKA
   choosing each titratable residue's state at pH 7.5, under the CHARMM force field. Each atom gets
   a partial charge and a radius. **The charge** smears each atom into a Gaussian, takes its exact
   average around the axis, and deposits the result on the mesh, element by element. Stage 7
   checks that the charge on the mesh is the charge of the atoms, and stops the run if it is not.
   Stages 8 to 12 solve the validated ePNP-NS model at +50 mV in 0.15 M NaCl and report the
   current and the transport numbers.
3. **`inspect run`** reads the manifest back. Its `charge` group holds the protonation record and
   the conservation report, and its `deviations` group is empty: the run is the validated model.
4. **`stage protonation … --export 2wcd.pqr`** writes stage 7's charges and radii as a PQR file,
   from the store. Its charge column sums to the run's `Q_net`, a whole number of elementary
   charges.
5. **`stage charge … --export charge.field.yaml`** writes the charge density stage 7 deposited
   from, as a `nanopnp/field/v1` areal charge density with `charge.field.npz` beside it. The header
   declares `Q_net`.
6. **`run from-pqr.case.yaml`** supplies the PQR back through `inputs.pqr`. PDB2PQR and PROPKA do
   not run: the protonation stage reads the file instead and records its hash. The atoms are the
   same, so the deposit is the same, byte for byte, filed under a different key because it came
   from a different input. It stops at stage 7, which is where the two runs could differ.
7. **`run switches.case.yaml`** turns on both FR-15 switches, which the published model leaves
   off. `exclusion_offset_nm` makes stage 5 build an ion-exclusion shell 0.25 nm thick around the
   protein, which ions cannot enter. `dielectric_transition_nm` makes stage 7 derive a
   permittivity that steps from the protein's to water's over 0.15 nm, instead of jumping at the
   protein's surface. The region and the mesh change, and stage 7 deposits and checks the charge on
   the new mesh.
8. **`inspect run-switches`** lists both switches under `deviations`, with the shell they
   contribute. Any number from that run was not produced by the validated model, and its manifest
   says so.

`2wcd.case.yaml` writes its `charge:` block out at its defaults, so that you can see the keys you
would edit. `from-pqr.case.yaml` has no `charge:` block, because the PQR replaces the step those
keys configure. The four case files share one electrolyte and one mesh size, so every run meshes
the same pore.

**The mesh is coarse, for runtime.** `numerics.mesh.size_scale: 4` makes every element four times
larger than the default sizes. That is a discretisation choice, not a deviation, and it is recorded
with the mesh. At the default sizes the solve takes tens of minutes. The transport number from this
mesh is a property check, not a prediction: the double layer at the pore wall is under-resolved.
The published values come from the reference geometry at converged resolution, which nanopnp
compares against at v0.7.

## Supplying the exported density back is refused

<!-- example: refused -->
```console
$ nanopnp run resupplied.case.yaml --store store --run-dir run-resupplied --upto charge
```

`resupplied.case.yaml` supplies `charge.field.yaml` back through `inputs.charge`, as a field made by
another tool would be. Stage 7 refuses it with exit `4`, at its quadrature-agreement check, before
the conservation legs. A supplied field is sampled at the solve's quadrature points. This density
changes sign every few hundredths of a nanometre, much finer than the mesh's elements, so sampled
that way its integral depends on the quadrature order rather than on the charge. That is aliasing,
and it is exactly what depositing the charge from the atoms avoids. The export is for other tools,
and for a mesh fine enough to resolve it. Within nanopnp, supply the PQR.

## What the test asserts

`tests/tier2/test_examples_07_pdb_to_charged_run.py` runs both blocks above, verbatim, from a copy
of this directory, the `run` block first. It checks properties rather than transcribed numbers
(SPECIFICATION.md VER-46):

- the prepared entry walks every stage to a charged solve, and the manifest lists no deviation;
- the manifest's `Q_net` is the whole number that the exported PQR's charge column sums to, read
  by the test without nanopnp;
- the conservation report is in the manifest, and each leg and each worst plane is below its
  recorded tolerance;
- the negatively charged pore is cation-selective: the transport number of Na⁺ is above one half,
  and the two current-extraction routes agree;
- the PQR supplied back gives the same atom table and a byte-identical deposit;
- the switches are listed as exactly two deviations, and mesh an `exclusion` material;
- the exported density declares the manifest's `Q_net`;
- the density supplied back is refused at the quadrature-agreement check.

## Next

- *From a structure to a charge*, in the documentation's user guide, covers every key these cases
  use, the conservation report, and which physics models take a charge.
- [06](../06-pdb-to-mesh/README.md) exports the structure, the density map and the pore profile,
  and feeds the profile back in.
