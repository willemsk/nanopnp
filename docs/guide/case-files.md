# Case files

A case file is YAML with `schema: nanopnp/case/v0.6` and a `name`. Every field is listed, with its
type, default, accepted values and validated default, in the generated [case-file
reference](../_generated/reference/case-file.md). This page explains how the document fits together.

## A minimal case

```yaml
schema: nanopnp/case/v0.6
name: my-pore

geometry:
  pore: {shape: cylinder, radius_nm: 2}
  membrane: {thickness_nm: 6}
  reservoir: {radius_nm: 10}

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
default, the value a case gets when it names nothing, is `none`; the validated run names
`willems2020_nacl` for each, as the [case-file reference](../_generated/reference/case-file.md)'s *Validated default* column shows. So a case that names no correction solves classical PNP-NS. Its manifest says so
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
| `structure`, `geometry` | The geometry pipeline: the structure file and its symmetry, the density map, the contour, the membrane and the reservoir, or `geometry.pore`, an idealised pore that stage 6 meshes. A `structure:` case walks every stage. See [Structures and trajectories](structures.md) and [From a structure to a mesh](geometry.md) |
| `charge` | Stage 7 on a structure: the pH, force field and titration of the protonation, a residue's pinned state (`edits`), the smearing of the deposit, and the two FR-15 switches, the ion-exclusion shell and the derived dielectric. See [From a structure to a charge](charge.md) |
| `models` | The molecular, continuum and physics model files a study is merged over. See the [case-file reference](../_generated/reference/case-file.md#models) |
| `variables` | Named values and expressions that a leaf of the case may name. See [§5.3.1's `variables:` NOTE](../_generated/model/specification/05-software-design/03-1-case-file.md) |

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

## A case's paths are read beside the case file

A relative path in a case is read beside the case file, not in the directory the command runs from.
That covers `inputs.*.path`, `structure.source.path`, `structure.ensemble.trajectory` and a
correction file named by path. A case reads the same files from any working directory, and so do
its edited copies, the members of a sweep over it and a reproduction of it.

`Case.load` keeps the directory of the file it read. An edit with `Case.with_` makes each relative
path absolute against that directory, a path the edit sets included, so a path the edit names is
read where every other path of that case is read. The manifest records the absolute paths. Only a
case that never had a file, one built by `Case.cylinder` or `Case.loads`, reads a relative path
against the working directory (§5.3.1).

## Correction parameter files

`electrolyte.parameters` names a correction parameter file: fitted coefficients, one file per
electrolyte, shipped with the package. Corrections are data, not code. See [correction data
files](../reference/corrections.md).
