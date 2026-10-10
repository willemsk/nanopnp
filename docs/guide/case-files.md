# Case files

A case file is YAML with `schema: nanopnp/case/v0.5` and a `name`. Every field is listed, with its
type, default, accepted values and validated default, in the generated [case-file
reference](../_generated/reference/case-file.md). This page explains how the document fits together.

## A minimal case

```yaml
schema: nanopnp/case/v0.5
name: my-pore

inputs:
  mesh: {path: pore.msh, format: msh41, groups: {default: interface}}

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 0.1

boundary_conditions:
  bias_V: 0.05

physics:
  solid_permittivities: {membrane: 3.2}

outputs: [current, transport_numbers]
```

That is a complete case, but it does **not** solve the validated model. Each correction's schema
default is `none`, so a case that names no correction solves classical PNP-NS. Its manifest says so
by listing every correction as a deviation. To solve ePNP-NS, name the corrections, as [example
01](../_generated/examples/01-quickstart.md) does.

## The sections

| Section | Holds |
|---|---|
| `inputs` | Stage outputs supplied from outside, each by `path` and `format` (the §5.3.1 `inputs:` NOTE): a `mesh`, or a pore `profile` that stages 5 and 6 assemble and mesh, and optionally `charge` and `eps_r`, or a `pqr` of the structure's charges and radii, which replaces PDB2PQR and PROPKA (see [From a structure to a charge](charge.md#supplying-a-pqr)) |
| `electrolyte` | Species and valences, concentration, temperature, the correction parameter file, and each correction's model and parts |
| `boundary_conditions` | The bias, which electrode is grounded, and the wall conditions |
| `physics` | The model (`epnp-ns`, `pnp-ns`, `pnp`, `pb`, `pb-linear`, `poisson`), the flow switches, and the solid permittivities, which are set here and nowhere else |
| `numerics` | Element orders, the nonlinear and linear solvers, the continuation ladder, stabilisation, the wall-distance field, and the sizes of a generated mesh (`numerics.mesh`) |
| `outputs` | Which quantities to report: `current`, `transport_numbers`, `eof_rate`, `rectification`, `analyte_force`, `fields` |
| `structure`, `geometry` | The geometry pipeline: the structure file and its symmetry, the density map, the contour, the membrane and the reservoir. A `structure:` case walks every stage. See [Structures and trajectories](structures.md) and [From a structure to a mesh](geometry.md) |
| `charge` | Stage 7 on a structure: the pH, force field and titration of the protonation, the smearing of the deposit, and the two FR-15 switches, the ion-exclusion shell and the derived dielectric. See [From a structure to a charge](charge.md) |

## Validation

A case is validated before anything is solved. An unknown key is refused with a diagnostic naming
the key and suggesting the nearest accepted one (IF-03). A value of the wrong type is refused naming
its dotted path. So is a correction model no installed parameter file provides, or an output this
run cannot produce, such as `rectification` at one operating point. So is a physics model, a
stabilisation mode or a linear solver this install does not register, and a velocity-pressure
element pair that is not inf-sup stable in the case's stabilisation mode. Every refusal exits with
code `3`.

`nanopnp validate case case.yaml` makes every check a run makes before it meshes anything, the
parameter file's included, and prints the stages the case walks. It reads no file the case supplies
and solves nothing.

## Dotted paths

Every field has a dotted path: `electrolyte.concentration_M`, `boundary_conditions.bias_V`,
`electrolyte.corrections.diffusivity.wall`. A list element is reached by index:
`electrolyte.species.0.name`. Sweeps vary a case by these paths. The desktop editor is generated
from the same walk over the schema, so the reference, the editor and a sweep can never disagree about
what a field is called.

## Paths in a case resolve against the working directory

`inputs.mesh.path` and the other input paths are resolved against the **working directory of the
process**, not the directory of the case file. The sweep runner never changes directory, so a
member cannot silently read a different mesh from the one the plan was built against. Run a case
from the directory its paths are written relative to, as every worked example does.

## Correction parameter files

`electrolyte.parameters` names a correction parameter file: fitted coefficients, one file per
electrolyte, shipped with the package. Corrections are data, not code. See [correction data
files](../reference/corrections.md).
