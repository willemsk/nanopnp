# Case files

A case file is YAML with `schema: nanopnp/case/v1` and a `name`. Every field is listed, with its
type, default, accepted values and validated default, in the generated [case-file
reference](../_generated/reference/case-file.md). This page explains how the document fits together.

## A minimal case

```yaml
schema: nanopnp/case/v1
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
| `inputs` | Stage outputs supplied from outside: `mesh`, and optionally `charge` and `eps_r`, each by `path` and `format` (the §5.3.1 `inputs:` NOTE) |
| `electrolyte` | Species and valences, concentration, temperature, the correction parameter file, and each correction's model and parts |
| `boundary_conditions` | The bias, which electrode is grounded, and the wall conditions |
| `physics` | The model (`epnp-ns`, `pnp-ns`, `pnp`, `pb`, `pb-linear`, `poisson`), the flow switches, and the solid permittivities |
| `numerics` | Element orders, the nonlinear and linear solvers, the continuation ladder, stabilisation, the wall-distance field |
| `outputs` | Which quantities to report: `current`, `transport_numbers`, `eof_rate`, `rectification`, `analyte_force`, `fields` |
| `structure`, `geometry`, `charge` | The v0.9 geometry and charge pipeline. Accepted by the schema, refused by this release, naming the section |

## Validation

A case is validated before anything is solved. An unknown key is refused with a diagnostic naming
the key and suggesting the nearest accepted one (IF-03). A value of the wrong type is refused naming
its dotted path. So is a correction model no installed parameter file provides, or an output this
run cannot produce, such as `rectification` at one operating point. Every refusal exits with code
`3`.

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
