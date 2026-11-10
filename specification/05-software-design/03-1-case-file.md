---
type: Specification
title: "5.3.1 Case file"
description: "The case file: an annotated example, the schema identifier and compatibility rule, and one NOTE per key block."
---

### 5.3 Data design

#### 5.3.1 Case file

One declarative YAML document is the unit of reproducibility (IF-03). Everything else is derived.

```yaml
schema: nanopnp/case/v0.6
name: clya-wt-1M-100mV

# models:                           # optional; a study, WP5.05 (the NOTE on `models:`)
#   molecular: clya-wt.molecular.yaml     # nanopnp/molecular-model/v0.6
#   continuum: clya-pore.continuum.yaml   # nanopnp/continuum-model/v0.6

# variables:                        # optional; named values, WP5.07 (the NOTE on `variables:`)
#   a: {value: 20, unit: angstrom}
#   L: {expression: "3 * a", unit: nanometer}

# inputs:                           # optional; supplied artefacts, §5.3.2
#   profile: {path: clya_profile.yaml, format: profile1}   # stage 4, nanopnp/profile/v0.5
#   pqr:     {path: clya.pqr, format: pqr}                 # stage 7's PDB2PQR step

structure:
  source: {path: 2WCD.pdb, variant: ClyA-AS, chains: all, selection: protein}
  ensemble: {trajectory: eq.xtc, frames: {last_ns: 5, count: 50}}
  symmetry: {point_group: C12, axis: auto}

geometry:
  density:  {grid_spacing_nm: 0.05, kernel: gaussian_vdw, sharpness: 0.93}   # 0.5 Å, as the paper
  contour:  {isolevel: 0.25, smoothing: taubin, simplify_tol_nm: 0.02}
  membrane: {thickness_nm: 2.8, centre_z_nm: 0.0}   # centre in the structure's frame, along the axis
  reservoir: {radius_nm: 250}

charge:
  ph: 7.5
  forcefield: CHARMM
  titration: propka
  smearing: {sharpness: 0.5, grid_spacing_nm: 0.005, axis_cutoff_nm: 0.01}
  exclusion_offset_nm: 0.0           # FR-15, PHY-20; 0 is the validated model, no exclusion shell
  dielectric_transition_nm: 0.0      # PHY-20 NOTE; 0 is the sharp indicator of the validated model

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  temperature_K: 298.15
  parameters: willems2020_nacl      # reference D_i^0, eta^0, rho^0, eps_r,f^0, a_i, a_0
  driver: average                   # PHY-01; `ionic_strength` is a deviation
  corrections:                      # the pluggable registry, §5.5
    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}
    mobility:     {model: willems2020_nacl, wall: true, concentration: true}
    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}
    permittivity: {model: willems2020_nacl}
    density:      {model: willems2020_nacl}
    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}

boundary_conditions:
  bias_V: 0.100
  ground: cis
  walls: {ion_flux: no_flux, slip: no_slip}

physics:                            # the named model of PHY-21
  model: epnp-ns
  flow: true
  variable_density: true
  inertia: true                      # PHY-22; the reference model retained it
  dielectric_gradient_forces: false  # PHY-23; off in the validated model
  solid_permittivities: {protein: 20.0, membrane: 3.2}   # PHY-20; the only place they are set

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  mesh: {backend: netgen, wall_h_nm: auto, size_scale: 1.0, boundary_layer: false}
  # wall_for_concentration_M: 3.0   # optional: size `auto` at this salt's Debye length (§8.2.14 P10)
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}   # NUM-16
  continuation: default_ladder
  stabilisation: none                # NUM-11; `supg` is its flag, `reference` matches §6.4
  wall_distance: {sources: wall, max_distance_nm: 3.0}                         # PHY-02
  linear: {solver: umfpack}          # see §6.6; MUMPS requires a source build

outputs: [current, transport_numbers, rectification, eof_rate, fields]
```

A case that takes a supplied mesh names it, with the fields that mesh carries, under `inputs:`, and
carries no `structure:` or `geometry:` (the NOTE on `inputs:`):

```yaml
schema: nanopnp/case/v0.6
name: clya-mesh-1M-100mV

inputs:                             # supplied artefacts, §5.3.2
  mesh: {path: clya.msh, format: msh41,
         groups: {lumen: electrolyte, upper: cis, lower: trans,
                  clya: protein, bilayer: membrane,
                  pore_wall: wall, outer_rim: membrane_outer,
                  symmetry_axis: axis}}
  charge: {path: clya_charge.yaml, format: field1}
  eps_r:  {path: clya_solid_fraction.yaml, format: field1}

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  temperature_K: 298.15
  parameters: willems2020_nacl      # reference D_i^0, eta^0, rho^0, eps_r,f^0, a_i, a_0
  driver: average                   # PHY-01; `ionic_strength` is a deviation
  corrections:                      # the pluggable registry, §5.5
    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}
    mobility:     {model: willems2020_nacl, wall: true, concentration: true}
    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}
    permittivity: {model: willems2020_nacl}
    density:      {model: willems2020_nacl}
    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}

boundary_conditions:
  bias_V: 0.100
  ground: cis
  walls: {ion_flux: no_flux, slip: no_slip}

physics:                            # the named model of PHY-21
  model: epnp-ns
  flow: true
  variable_density: true
  inertia: true                      # PHY-22; the reference model retained it
  dielectric_gradient_forces: false  # PHY-23; off in the validated model
  solid_permittivities: {protein: 20.0, membrane: 3.2}   # PHY-20; the only place they are set

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}   # NUM-16
  continuation: default_ladder
  stabilisation: none                # NUM-11; `supg` is its flag, `reference` matches §6.4
  wall_distance: {sources: wall, max_distance_nm: 3.0}                         # PHY-02
  linear: {solver: umfpack}          # see §6.6; MUMPS requires a source build

outputs: [current, transport_numbers, rectification, eof_rate, fields]
```

NOTE (the case schema: its identifier and the compatibility rule; §8.2.7 G6): every case document
must declare schema `nanopnp/case/v0.6` exactly, and any other schema identifier is refused naming
the expected schema and the declared identifier before any structural validation. The earlier
pre-release identifiers `nanopnp/case/v1`, `nanopnp/case/v2` and `nanopnp/case/v0.5` are retired.
The refusal of `v0.5` names the migration: declare `nanopnp/case/v0.6`, and a case with `structure:`
that keeps v0.5's density adds `geometry.density.atoms: as_loaded`, since v0.6's default moves the
density (the NOTE on `geometry.density`). **Widening the accepted
value set of an existing key is compatible and SHALL NOT move the schema version, because every
document that validated before still validates; adding, removing, renaming or narrowing a key SHALL
move it.** What a run actually read is in its FR-25 manifest, so no artefact of an earlier revision becomes
ambiguous under a widening. The identifier that a move takes names the release that ships it: the
first move inside v0.6 makes the schema `nanopnp/case/v0.6`, and the stable schema of v1.0 is
`nanopnp/case/v1.0`, which is distinct from the retired `nanopnp/case/v1`. A release whose
packages move nothing keeps the identifier it inherited. Between that release's work packages, the
schema under its identifier may change again without a new identifier, because a pre-release makes
no compatibility promise. The manifest of every run records the package version (FR-25), and that
version settles which revision the run read. The identifier is fixed when `vX.Y.0` is
tagged.

NOTE (the added keys that change a number): `charge.exclusion_offset_nm`
and `charge.dielectric_transition_nm` are the fitted exclusion offset of FR-15 and the width of
PHY-20's transition to `ε_w`. Both SHALL be non-negative, and both are switches whose validated
default is `0`: the validated model has no exclusion shell and a sharp material permittivity (PHY-20
NOTEs). A non-zero value is therefore a deviation that the FR-25 manifest records. When the
`charge:` block is absent, each reads as its validated default. Both are built from the stage-4
profile (§5.2.1 NOTE on the ion-exclusion shell; §4.4 NOTE on the derived solid fraction), so
either set away from `0` beside `inputs.mesh`, or in a case carrying neither `structure:` nor
`inputs.profile`, is a knob with no effect and SHALL be refused naming both keys. A non-zero
`dielectric_transition_nm` beside `inputs.eps_r` supplies one quantity twice and SHALL be refused
naming both. Each is refused below its resolution limit as its NOTE says, and a model that declares
no solid fraction refuses the transition as it refuses `inputs.eps_r` (§5.4.3) (WP30). `numerics.mesh.size_scale`, default
`1`, SHALL multiply every element-size target of §5.2.2 and NUM-30, the resolved `wall_h_nm`
included. It exists so that a mesh-convergence study (RSK-09, §6.8) is a sweep over a case-file
field (FR-24) rather than a code edit. It is a discretisation choice recorded with the mesh, not a
deviation. With a supplied `inputs.mesh` a value other than `1` would be a knob with no effect, so
it SHALL be refused.

NOTE (`charge.ph`, `charge.forcefield`, `charge.titration`; the `protonation` stage, PHY-16 step 3,
FR-12; WP27): `ph` is a number in [0, 14], the range PDB2PQR accepts.
`titration` is `propka` or `none`; `none` runs PDB2PQR without a titration method, so every
residue keeps the force field's standard state and the pH reaches no calculation. A `ph` set away
from its default beside `titration: none` is therefore a knob with no effect and SHALL be refused
naming both keys, as `numerics.mesh.size_scale` is beside `inputs.mesh`. `forcefield` is one of
`CHARMM`, `PEOEPB` and `SWANSON`, and is passed to PDB2PQR as both `--ff` and `--ffout`. PDB2PQR 3.7
also ships `AMBER`, `PARSE` and `TYL06`, but each gives charged atoms a zero radius (53, 93 and 2269
of them on one chain of 2WCD, measured), and PHY-16 step 4's kernel width
`w_i = 0.5 R_i` is then zero, so they are refused naming the atom count rather than admitted to
fail at deposition; the stage refuses a charged atom with a radius that is not positive from any
source, `inputs.pqr` included, naming the frame and the atom. `titration` and `forcefield` are switches whose validated defaults
are `propka` and `CHARMM` (PHY-16 step 3); any other value is a deviation that the FR-25 manifest
records. `ph` is a condition of the experiment, as `concentration_M` is, and not a deviation. The
case's `structure.source.variant` is recorded beside `Q_net`, which it is the provenance of
(OPN-04). `charge.exclusion_offset_nm` is read by stage 5 and `charge.dielectric_transition_nm`
by stage 7 (WP30; see the NOTE on the added keys that change a number,
which says when each is refused). `charge.smearing` is read
by stage 7's deposition (WP28; see the NOTE on `charge.smearing`).

NOTE (`charge.smearing`, PHY-16 steps 4–6, PHY-18; WP28): `sharpness`
is the `0.5` of PHY-16 step 4's `w_i = 0.5 R_i`. It is a switch whose validated default is `0.5`,
and any other value is a deviation that the FR-25 manifest records. `grid_spacing_nm` is the
spacing of the export lattice, on which the kernel is summed and the deposit's integrals are taken.
It is a discretisation choice recorded with the artefact, as `numerics.mesh.size_scale` is, and not
a deviation. A spacing above half the smallest kernel width of a charged atom SHALL be refused naming
that atom (PHY-16 NOTE on the deposition). `axis_cutoff_nm` set away from its default SHALL be
refused naming PHY-18 on every path. The deposited kernel is regular on the axis and takes no
guard, and a supplied field declares its own guard in its header (§5.3.1 NOTE on `inputs.charge`),
so the key would change nothing. The exported field declares the default `0.01 nm` for a later
re-read. As with the protonation keys, `charge.smearing` set away from its defaults beside
`inputs.charge`, or in a case carrying neither `structure:` nor `inputs.pqr`, configures a step
that does not run and SHALL be refused naming both keys.

NOTE (`charge.edits`, FR-38, PHY-16 step 3; WP5.04; §8.2.31 AG9 to AG11): `charge.edits` is a list, empty by
default. Each entry names a `residue` as the parent name, the number and an optional insertion code
(`ASP 21`, `HIS 292A`), and holds exactly one of three edits, which apply on every chain and every frame:
`state` (`charged` or `neutral`) pins a titratable residue's protonation state; `charge_change_e` (a
non-zero integer) changes its net charge by that amount; `radius_scale` (finite, above 0) multiplies every
atom radius of the residue, hydrogens included. A residue holds one edit of each kind, compared by name,
number and insertion code (`ASP 021` is `ASP 21`), and `state` beside `charge_change_e` on one residue SHALL
be refused. A `residue` named by a protonation-variant name (`HSD`, `ASH`) SHALL be refused naming its parent. `state` SHALL be refused on a residue other than ASP, GLU
and HIS, beside `titration: none`, under a force field other than `CHARMM` (which holds no `LYS⁰`, `ARG⁰`,
`CYS⁻` or `TYR⁻`) and beside `inputs.pqr`. `charge_change_e` SHALL be refused on a residue with no
titratable group. Every edit SHALL be refused beside `inputs.charge`, and any edit in a case with neither
`structure:` nor `inputs.pqr`, naming both keys, because no step would apply it. A residue that a
frame does not hold, or that has another parent name, SHALL be refused naming the frame and the chain.
The change of `charge_change_e` is spread evenly over the atoms of the residue's titratable group that the
frame holds, the charge-centre atoms of PROPKA 3.5.1 (`data/charge/titratable_groups.yaml`, held equal to
PROPKA's configuration by a Tier 1 test), so `Q_net` stays an integer; a terminal residue's charge
includes its terminus, which is why the edit is a change and not a target. A fractional state is FR-43's.
The edits ride on stage 7's `protonation` step (§5.2 NOTE on `charge.edits`) and enter its key, sorted
by residue and kind; without edits no key of the pipeline differs from a case that never had the field.
The radius scales also set stage 2's radii under `geometry.density.atoms: protonated`, so they move the
density, the contour and the mesh, and stage 4's probe-radius profile scales the same atoms by the same
factors, its key carrying the radius edits where there are some; under `as_loaded` they move the charge's
kernel width alone and the density key is the parent's. Stage 2 keys on the protonation key with its charge
edits dropped: a charge edit moves no atom, name or radius, so a charge variant shares its parent's
density, contour and mesh. The edited table is a variant of its parent: the stage keeps the unedited
table beside it and records `variant_of` in its summary, the parent's key, the edits, each residue whose
atoms, charges, radii or positions differ (per chain, both charges per frame, atoms added and removed,
the largest radius change and displacement) and `Q_net` of the parent and the variant per frame. None of
it is a deviation (FR-25): `charge.edits` is configuration, so the manifest's list of switches away
from the validated default does not change, and `charge.protonation.variant_of` carries the record.

NOTE (`inputs:`, FR-27): the optional top-level `inputs:` block is hand substitution (FR-27) applied
at stage granularity. Each key names a stage output supplied from outside — a mesh, a charge field,
a dielectric field — by path and format. A stage whose output is supplied does not run, and neither
does anything upstream of it; the substituted file is hashed by content and enters the FR-25
manifest as an input like any other. This is what makes the solver core testable without the
meshing pipeline (§8.1).
`inputs.profile` supplies stage 4's conditioned polyline as a `nanopnp/profile/v0.5` document
(`format: profile1`), which is how a hand-edited contour enters a run (§8.1, GUI increment 2), and
`inputs.pqr` supplies the per-atom charges and radii of stage 7's PDB2PQR step (`format: pqr`). The
two chains are structure → density → profile → mesh and structure → PQR → charge field, and the
dielectric field comes from the density (FR-15). Under `geometry.density.atoms: protonated`, the
default, the chains share their first link: stage 7's protonation, or the supplied PQR, feeds the density
as well as the charge field, so the density reads the supplied PQR's atoms, and beside `inputs.charge` the
protonation runs for the density alone (WP5.03). Supplying an artefact together with one downstream
of it on the same chain SHALL be refused, naming both. The upstream one would be hashed into the
manifest as an input to a run that never read it, and the same holds of every key: each key of
`inputs:` SHALL be read by the stage that consumes it, so that no file is hashed into the manifest
as an input to a run that never read it (FR-25, VER-47).
A supplied artefact is read by `path`. `inputs.mesh` alone also takes `artefact:`, the 64-character
store hash of a stage-6 mesh artefact (REV-62; WP5.05). The mesh stage takes the store and its key is
the stored artefact itself, so a mesh a run generated keeps its hash when a later case names it by
that hash, and every stage downstream keys as it does for the generated mesh. A hash the store does
not hold SHALL be refused, naming the hash and the store's root, and so SHALL `format` or `groups`
beside `artefact:`, since the stored artefact has declared its groups already. A stored mesh passed
its gates when it was made, so the sweep plan does not gate it again. `structure:` or `geometry:`
beside `inputs.mesh`, a stored mesh included, stays refused (REV-186: a stored mesh's frame against
a structure is unknown). `artefact:` on `inputs.charge` or `inputs.eps_r` SHALL be refused as an
unsupported section when the case is resolved, naming the key: no release schedules the store form of
the two fields (WP40).

NOTE (`inputs.profile`): `inputs.profile` is consumed by stage 5. It is named by `path`
with `format: profile1`, and `artefact:` or `groups` beside it is refused. The profile is
hashed by the canonical digest of its validated payload. `structure:` beside it is refused naming
both, by the upstream rule, and so are `geometry.density` and `geometry.contour` where either is
set away from its default; `geometry.membrane` and `geometry.reservoir` are read. A section set to
its defaults is not refused, because a case dumped from its resolved document writes every section
out, and FR-26 requires that dump to load back.

NOTE (`inputs.pqr`): `inputs.pqr` is consumed by the `protonation` stage, the first half of stage 7
(§8.2.4 D4). It is named by `path` with `format: pqr`, and `artefact:` or `groups` beside it is
refused. The file is a PQR of one frame, or one `MODEL` per frame; every frame SHALL hold the same
residues, and every atom a charge and a radius. Unlike `inputs.profile`, `inputs.pqr` stands beside
`structure:`, because stage 1 still runs for the geometry chain: there the PQR SHALL hold exactly the ensemble's frames, in order, each registered to
its stage-1 frame (§5.2's NOTE on reading a supplied PQR). Without
`structure:` the coordinates are taken to be in stage 1's frame already, which is the frame the
stage exports. Beside `inputs.pqr`,
`charge.ph`, `charge.forcefield` and `charge.titration` configure a step that does not run, so any
of them set away from its default SHALL be refused naming both keys, as `geometry.density` is beside
`inputs.profile`. The same holds beside `inputs.charge` under `geometry.density.atoms: as_loaded`,
where the supplied field replaces what stage 7 would make of a protonation and nothing else reads
it; under the default the protonation runs for the density and these keys configure it. It holds
also in a case carrying neither `structure:` nor `inputs.pqr`, which has nothing to protonate.

NOTE (`models:`, FR-39, FR-32, IF-03; WP5.05, WP5.09; §8.2.31 AG12, AG13; §8.2.34 AJ2, AJ3, AJ5; §8.2.35 AK1 to
AK3): the optional top-level `models:` block, `{molecular: <path>, continuum: <path>, physics: <path>}` with at least
one of the three, names a case's **molecular model**, **continuum model** and **physics model**, each a YAML file of
its own schema, `nanopnp/molecular-model/v0.6`, `nanopnp/continuum-model/v0.6` or `nanopnp/physics-model/v0.6`. A case
that names a model is a **study**. A model file holds `schema`, `name`, an optional `exposes:` list and only the keys
its kind owns; it names no model; a file with another `schema`, no `name`, a `models:` key or a key of another kind
SHALL be refused, naming the file, the key and the kind that owns it. Ownership is one table, and the longest dotted
prefix decides; every path with no row is the study's. The molecular model owns `structure`, `charge.ph`,
`charge.forcefield`, `charge.titration`, `charge.edits` and `inputs.pqr`. The continuum model owns `geometry`,
`charge.exclusion_offset_nm`, `numerics.mesh`, `inputs.mesh` and `inputs.profile`. The physics model owns `physics`
(the registered model, its switches and the solid permittivities), `electrolyte`, `boundary_conditions`,
`numerics.elements`, `numerics.stabilisation` and `numerics.wall_distance`, the PHY-02 field the wall corrections
read, so the bias and the walls are the physics model's defaults, which a study overrides for a sweep or a ramp
(WB-16). The study owns the rest: `schema`, `name`, `outputs`, `models`, `charge.smearing`,
`charge.dielectric_transition_nm`, `inputs.charge`, `inputs.eps_r` and the Newton, continuation and linear-solver
settings (`numerics.nonlinear`, `numerics.continuation`, `numerics.linear`). `numerics.mesh.wall_h_nm: auto` reads the
resolved case's electrolyte, so a continuum model's wall size follows the salt of the physics model its study pairs it
with, as a case written inline does; `numerics.mesh.wall_for_concentration_M`, a continuum key, pins it.

A model's **exposed values** are the few its study lists first and sweeps directly (WB-35). Each kind has a default
list: `concentration` (`electrolyte.concentration_M`) and `bias` (`boundary_conditions.bias_V`) on a physics model,
`pH` (`charge.ph`) on a molecular model, `size_scale` (`numerics.mesh.size_scale`) on a continuum model. A model
file's `exposes:`, a list of `{name, path, range}` with `range: [low, high]` optional, replaces its kind's list. An
entry's unit is its field's (the `variables:` NOTE's suffixes), its range the declared one, else the field's schema
bounds, and its default the model's own value at the path, else the schema's default. An entry SHALL be refused,
naming the file and the entry, when its name repeats or does not match `[A-Za-z][A-Za-z0-9_]*`, when its path is not
a numeric field of the case or is owned by another kind, when its range is not two finite numbers in increasing
order, or when the model's own value lies outside it. A range guides the suites and the sweep and refuses no study's
override. `exposes:` keys nothing: it is left out of the merge, so no artefact or stage key reads it.
A relative path in a model file is read beside that file, and one in `models:` beside the case.

The case resolves by merging the study over the molecular model, then the continuum model, then the physics model: a
mapping merges key by key, and a list or a free mapping replaces whole. The result validates once as
a case. The models and the study's own keys, taken without the study's values in a named model's
keys (the *view*), SHALL validate alone as well, or the model is refused naming its file: a model
that cannot stand alone cannot be reused. A refusal names the case path and, in brackets, the file
its value came from.

A value the study sets in a named model's keys that differs from the model's is an **override**. An
override is a leaf, the deepest path at which both sides are blocks; a value equal to the model's is
none. The resolved case recomputes its overrides on every substitution, so they survive an edit and a
sweep, and `Case.overrides` maps each path to the model's value and the study's. A substitution of
`models.molecular`, `models.continuum` or `models.physics` swaps a model the study names; one that names a model the
study does not name, or drops one, SHALL be refused, since the study's document holds a value, its
default included, for every key of a model it does not name, and each would override the new model.
A substitution that gives `models:` to a case naming no model SHALL be refused likewise, saying to
write `models:` in the case file. A substitution that drops whole (sets to null) a block a named model and
the study share, such as `charge` beside a molecular model, SHALL be refused naming the keys the model
sets, since the study form writes overrides leaf by leaf and could not write the drop (REV-187). A study overrides
any value of the models it names; the Study suite lists each model's exposed values first (WB-16, WB-35). `models` is left out of every dump, hash and equality of the case, `Case` and the document
`pipeline.case.load_case` returns alike (REV-190), so a study equals
and keys as the case it resolves to, written inline: the artefact keys, the stage keys and the
cache are those of that case, and a stage a model built is reused by every study that names the
model. Every case reader resolves `models:`: `read_case` and
`read_case_text`, and `Case.load` and `pipeline.case.load_case` through them. The run writes the
one complete case it resolved to as `case.yaml`, with no `models:`, which the command line runs as
it is (FR-25); `Case.dumps(study=True)` writes the study as written, with `models:` absolute and every
override, and a sweep over a study writes that form as its base file (§5.3.4). A project holds a study's models and the study as files of one folder (§5.3.5).

NOTE (`variables:`, FR-39, FR-25, IF-03; WP5.07; §8.2.31 AG2 to AG5): the optional top-level
`variables:` block maps a name to `{value: <number>, unit: <text>}` or `{expression: <text>, unit:
<text>}`, exactly one of the first two, the unit defaulting to `dimensionless`. A name matches
`[A-Za-z][A-Za-z0-9_]*` and is neither `auto` nor a function of the list below. A string at a numeric
leaf of the case is an **expression** of the variables, unless the field takes the string as a
literal (`numerics.mesh.wall_h_nm: auto`). An expression is parsed from Python's syntax tree
(`ast.parse`) and walked against a whitelist: numbers, variable names, `+ - * /`, `**`, parentheses,
a unary sign and the functions `sqrt`, `exp`, `log`, `abs`, `min` and `max` with positional arguments.
No code runs; an expression of more than 256 characters, any other construct, an unknown name, a
cycle among the variables, a division by zero and a non-finite result SHALL be refused, naming the
expression and the variables that cause it. `exp` and `log` take a dimensionless argument, and `min`
and `max` arguments of one dimension. A number is read as its decimal text and arithmetic is exact in
fractions (a conversion of 20 Å gives 2.0 nm, not 1.9999999999999998), except a power, which is
taken in floating point and whose exponent is dimensionless.

Units go through one `pint` registry (a runtime dependency, BSD-3-Clause, pure Python, CON-07). A
field takes its unit from the suffix of its name: `_nm` nanometre, `_ns` nanosecond, `_V` volt, `_M`
molar, `_K` kelvin, `_e` elementary charge, `_C_m2` coulomb per square metre; every other numeric
field is dimensionless. A value or expression of the same dimension as the field SHALL be converted
to the field's unit (50 mV at `bias_V` is 0.05; 25 °C at `temperature_K` is 298.15), and one of
another dimension SHALL be refused at the field, naming the field, the expression and both units. A
field of integer type takes only an integral value. A numeric field the case schema gains has a
suffix of the table or is listed dimensionless in `io/variables.py`, and a test fails otherwise.

The case resolves its own `variables:` and expressions to numbers before it merges any model, so
every stage and every identity reads numbers only: `L: 2*a` with `a` = 2 nm keys as `L: 4`, the same
`CaseArtefact` hash and the same stage keys, and a case without `variables:` keys as it did before.
The variables as written are held beside the document, outside its dump, equality and every hash,
as `models` is. The run's `case.yaml` and `Case.dumps()` write the case as written, with `variables:`
first after `name` and each expression at its field, which every case reader resolves again; the manifest records the variables beside their numbers (§5.3.3). A
study owns `variables:`, and a model file that holds it, or an expression at one of its leaves, SHALL
be refused, naming the file and the key, since a model serves many studies. A substitution at
`variables.<name>` sets the number, in the variable's declared unit, or replaces the definition; a
substitution of a number at a field that was an expression drops the expression. The case is read
again as written with each substitution, so every field the variable reaches moves. A substitution
at `variables.<name>` of an unknown name SHALL be refused, naming it.

NOTE (a relative path in a case, FR-25, QR-08; §8.2.23 Y3): every file a case names by a relative
path (`inputs.*.path`, `structure.source.path`, `structure.ensemble.trajectory` and a correction file
read by path, below) is taken against the directory of the case file the run read, so a case reads
the same files from any working directory. A case held in memory SHALL carry the directory of the
file it came from, where it came from one, and take its relative paths against that: an edited
copy, a member of a sweep over it and a reproduction of it read the files the case file read, and
only a case that never had a file — one a factory or a caller's text built — reads against the
working directory. A case read in Python keeps that directory, and an edit makes each relative path
absolute against it, the caller's own edits included and *after* them, so a path the edit names is
read where every other path of that case is read. The FR-25
manifest records each input file, the case file included, by its absolute path and content hash;
the case hash covers the paths as written, so moving a case and its files together moves no key. A
reproduction takes a relative path against the directory the original case was read from (QR-08).
A supplied `inputs.charge` or `inputs.eps_r` is in the model frame, beside a moved structure as
anywhere else (the NOTE on `inputs.charge`, `inputs.eps_r`; WP41).

NOTE (`structure:`, stage 1, FR-01 to FR-03, IF-04): `source.path` names a PDB or mmCIF file,
optionally gzipped. MDAnalysis reads PDB and gemmi reads mmCIF. `source.selection` is an MDAnalysis
selection applied to the file, and one MDAnalysis cannot parse SHALL be refused naming the key. The
selected atoms are those of the selection in the chains `source.chains` lists. `source.chains` is
`all` or a comma-separated list of chain identifiers, such as `A,B,C`, which SHALL number `n`.
`symmetry.point_group` is `C<n>` with `n ≥ 1`, and any other group SHALL be refused naming the
accepted form. The ensemble is the frames of `ensemble.trajectory` when one is given, and otherwise
the models of the source file. `frames.last_ns` keeps the frames within that many nanoseconds of the
last one, by the times the file records. `frames.count` keeps `count` frames at the uniform stride
`⌊N/count⌋`, ending on the last frame of the window of `N` frames. `symmetry.axis: auto` detects the
Cₙ axis (FR-02), and `symmetry.axis: z` takes the file's z axis through its origin. The structure
file SHALL point +z from the *trans* side to the *cis* side, and `geometry.membrane.centre_z_nm` is
read in the file's axial coordinate. Stage 1's behaviour, thresholds and refusals: §5.2's NOTE on
stage 1. Stage 1 alone runs through the stage command (IF-02). A case carrying `structure:` and
`inputs.mesh` SHALL be refused naming both: a stage whose output is supplied does not run, and
neither does anything upstream of it (the `inputs:` NOTE), so the structure would be recorded as an
input to a run that never read it.

NOTE (`geometry.density`, stages 2 and 3, FR-04 to FR-06, CON-04, IF-05; WP19): the `geometry:` block is read on a case carrying `structure:`. Beside `inputs.mesh`
it SHALL be refused naming both, by the upstream rule of the `inputs:` NOTE. `grid_spacing_nm`
SHALL lie in [0.025, 0.05] nm (FR-04) and `sharpness` SHALL be finite and positive, and each is refused naming
its value rather than narrowed in the schema.

`atoms` (`protonated` or `as_loaded`; WP5.03, PHY-16, §8.2.19 U2) says which atoms stage 2 smears. `protonated`, the
validated default, deposits each frame's own atoms from stage 7's protonation table, hydrogens included, at the
positions PDB2PQR wrote. Each atom's `R_i` comes from the CHARMM radius set: first from its residue's state patch
(the table's tautomer for a histidine; `ASPP` for an aspartate holding `HD2`; `GLUP` for a glutamate holding `HE2`; `DISU` for the `1CB`, `1SG`, `2SG` and `2CB` of a disulfide-bonded cysteine),
by that patch's own entry, and otherwise from the residue's parent name. An atom without a radius is refused naming
its frame, chain, residue and atom, as under `as_loaded`, with no fallback by element. `as_loaded` deposits the atoms as stage 1 read
them, which is the reference's density; it is a switch away from the validated default, so the manifest lists it (FR-25).
`protonated` beside a produced protonation under a `charge.forcefield` other than `CHARMM` SHALL be refused at
resolution naming both keys, since another force field writes hydrogen names that the CHARMM set does not hold.
`atoms` takes part in stage 2's key only when it is `protonated`: under `as_loaded`, `atoms` does
not enter stage 2's key. `kernel: gaussian_vdw` takes each atom's width as `σ R_i`, with σ the
`sharpness` and R_i from the CHARMM radius set. The kernel, the radius set and the union are in
§5.2's NOTE on stage 2, and stage 3's binning and Cₙ average in its NOTE on stage 3.

NOTE (`geometry.pore`, an idealised pore, IF-02, FR-09, FR-10; §8.2.22 X1): a case without
`structure:`, `inputs.profile` or `inputs.mesh` MAY declare an idealised pore,
`geometry.pore: {shape: cylinder, radius_nm}`, the membrane's thickness and the reservoir's radius
read from `geometry.membrane` and `geometry.reservoir`. Stage 5 builds the region from it: the lumen
surface `r = R`, `|z| < h/2` with `h` the membrane's thickness, is named `wall`, PHY-02's distance source set and the surface PHY-09's
`σ_s` is set on, and the membrane's cis and trans faces are excluded from it, as the bilayer's are in
the reference model. Each reservoir is the quarter disc of radius `geometry.reservoir.radius_nm`
centred on its mouth, the lumen is the domain `electrolyte` and the reservoirs are `cis` and
`trans`, and the two mouths are `interface`. Stage 6 meshes it under `numerics.mesh` and its gates,
with the size field of the §5.2.2 NOTE on an idealised pore; stages 1 to 4 and the charge stages do not run unless `inputs.charge`
supplies a field. `geometry.pore` beside `structure:`, `inputs.profile` or `inputs.mesh` SHALL be
refused naming both, and `radius_nm` not below `geometry.reservoir.radius_nm` SHALL be refused
naming both values. The solid around the lumen is the `membrane` domain, so a case declaring
`geometry.pore` SHALL set `physics.solid_permittivities.membrane` and is refused naming the key
otherwise, rather than taking ion-free water as an unlisted solid does; `geometry.membrane.thickness_nm`
defaults to the bilayer's 2.8 nm, so a solid-state pore sets it. Beside `geometry.pore`, keys that
only a structure's stages read are refused naming each: `geometry.membrane.centre_z_nm` away from 0,
which is a position in a structure's frame, and `geometry.density` or `geometry.contour` away from
their defaults; so is `numerics.mesh.backend` other than `netgen`, since the Gmsh backend's size
field is posed on a structure's region (WP57). `boundary_conditions.wall_charge_C_m2`
(PHY-09) and `numerics.mesh.maxh_nm` are read only beside `geometry.pore`, and each is refused
elsewhere naming the key.

NOTE (`geometry.contour`, stage 4, FR-07, FR-08; WP20): `isolevel`
SHALL be finite and lie in (0, 1). `simplify_tol_nm` SHALL be finite, positive and below the
density grid spacing h, because a larger tolerance discards resolved geometry and breaks the margin
of the §5.2.1 NOTE on the contour's size target. Each is refused naming its value, and the second
names h as well. `smoothing` is `taubin` or `none`. No other contour parameter and no gate
threshold is a case key: they are the constants of §5.2.1, and they key the stage-4 artefact.
Stage 4 emits a `nanopnp/profile/v0.5` document with `provenance.source: pipeline`, and its `sha256`
is the digest of the stage-3 payload it was drawn from. The loop runs clockwise from its lowest
vertex and stays in the stage-1 frame, so stage 5 applies `geometry.membrane.centre_z_nm` to it
exactly as to a supplied profile. The document read back through `inputs.profile` is a supplied
profile (the §5.2.1 NOTE on a supplied fixture). The conditioning and gate records belong to the
stage-4 artefact, not to the document, so a hand edit cannot carry a stale one.
A hand edit written by the desktop shell (§8.1, GUI increment 2) is a `nanopnp/profile/v0.5`
document with `provenance.source: hand-edit`, which is never a reference source. Its `sha256` is the
canonical digest of the profile it was edited from, or, where it was started from a loop stage 4's
gate refused (§8.2.2 B9), the digest of the stage-3 payload that loop was drawn from, as stage 4
records it. Its measurements are re-derived from its own vertices. It enters a run only through
`inputs.profile`, and is gated as a supplied profile (WP24 D5).

NOTE (`inputs.charge`, `inputs.eps_r`, IF-05, IF-03): a supplied field is named by a
pydantic-validated header document, `schema: nanopnp/field/v0.5`, which carries the `quantity`, its
units, the grid descriptor (origin, spacing, shape), the axis cutoff of PHY-18 (default 0.01 nm),
the declared `Q_net` where the producer knows one, the provenance of the file, and the data file it
refers to. `format: field1` names that document; the *data* format is read from it, `.npz` on the
default path, OpenDX or CCP4 through GridDataFormats, which SHALL remain optional, and
`comsolgrid` — the reference model's own `%Grid`/`%Data` interpolation table, in metres, **read
only**, since it is an input to the reference rather than an output of ours and writing it would
invite a round trip that is not one. A grid axis SHALL be uniform to round-off or the file SHALL
be refused naming the axis: the interpolant of PHY-19 takes a box and a shape, so a non-uniform
axis would otherwise be resampled onto a uniform one in silence. A header
document SHALL reject an unknown key naming the key, as every other schema in §5.3 does. `quantity`
is one of `areal_charge_density` (the reference's `rhoq_pore`, C m⁻²), `volume_charge_density`
(C m⁻³) or `solid_fraction` (dimensionless), and the `1/(2πr)` projection and the axis guard of
PHY-16 step 6 SHALL be applied to `areal_charge_density` **only** — applying them twice, or not at
all, is invisible in the conservation check of PHY-19, for the reason given there. The interpolant
SHALL be zero outside the grid box rather than continued by its edge value, and a grid whose
boundary values are not negligible against its interior SHALL be refused rather than truncated
silently. An `inputs.eps_r` field SHALL supply a solid fraction, not an absolute `ε_r`: see §4.4.
A supplied field is in the **model frame**, the frame of the mesh the solve runs on, and SHALL be
applied at that mesh's coordinates without a shift. For a case that generates its mesh, that frame
is stage 1's moved by stage 5's `z ← z − geometry.membrane.centre_z_nm`, the frame stage 7 deposits
and exports in; beside a supplied mesh it is that mesh's own. The header MAY declare the frame it
was written in as `model_frame_centre_z_nm`, the `centre_z_nm` of the case it belongs to, and stage
7's export SHALL declare it. Beside a case that generates its mesh, a declared value other than the
case's `geometry.membrane.centre_z_nm` SHALL be refused, naming both values and the offset every
feature would be applied at (QR-12). Beside a generated mesh named by its store hash
(`inputs.mesh.artefact`), the declared value SHALL be checked against the membrane centre of the
region that mesh was generated from, read from the store, and refused alike; a store that lacks
that region SHALL refuse the declaration, since it cannot be checked (REV-191). A header that declares none is read in the model frame, as
before the key existed, so no document that ran is refused (WP41 D1, REV-06).
An analytic form that carries a charge (`gaussian_ring`'s `charge_e`) need not equal `q_net_e`, the
field's integral over `r ≥ 0`, planar for an areal density and `2πr`-weighted for a volume density: an
areal ring on the axis integrates to half its charge. A charge and a `q_net_e` of opposite sign, or one
of them zero and the other not, are refused when the document is read, before its grid is built; a
disagreement in size is the producer leg's of PHY-19, whose refusal names `q_net_e` and the form's
charge parameter.

NOTE (`inputs.mesh.groups`, IF-06, QR-12): the mapping reads **file group name → vocabulary name**.
The key is the physical-group name the mesh file carries; the value is the name the solver selects
on. Several file groups MAY map to one vocabulary name — a CAD export routinely splits one physical
wall into several curves — and the reverse is not expressible, which is why the direction is this
way round. The vocabulary is fixed and carries no aliases: materials `electrolyte`, `cis`, `trans`,
`protein`, `membrane`, `analyte`, `exclusion`; boundaries `axis`, `wall`, `membrane`,
`membrane_outer`, `cis`, `trans`, `analyte`, `interface`. `protein` is the pore's dielectric body (§2.2), a solid domain
Poisson is solved on and Nernst–Planck and the flow are not; `pore` is deliberately **not** a name,
because it reads as both that body and the lumen fluid, and a mesh that uses it SHALL disambiguate
through the mapping. `interface` is the interior fluid-to-fluid seam a fragmented region carries —
the pore-mouth interfaces the reservoir-to-lumen split leaves behind — and, in a region stage 5
generates, every solid-to-solid seam: the protein against the membrane and, with an exclusion
shell, the shell against the protein and the membrane (WP30). **Nothing
selects on it**;
it is in the vocabulary because every group must be claimed by some name, and calling an interior
seam `wall` would put it in the PHY-02 distance source set and impose no-slip across the middle of
the electrolyte. `exclusion` is the ion-exclusion region of FR-15 — the shell between the dielectric
contour and the exclusion contour, offset outward by the hydrated-ion radius. It is a solid for
Nernst–Planck and for the flow, so the no-slip surface sits at the outer edge of the shell, which is
the conventional hydrodynamic shear plane; it is **water** for Poisson, so
`physics.solid_permittivities` SHALL NOT require an entry for it and SHALL NOT abort on its absence.
Ions do not exist in it, so `⟨c⟩` has no meaning there (author ruling 13, §4.4 NOTE) and the water
is ion-free: the shell SHALL take `ε_r,f⁰` exactly, never `ε_r,f(⟨c⟩)` evaluated where the
concentrations are undefined. The resulting step at the shear plane is the salt correction of the
fluid side, which the shell by construction does not carry.
ePNP-NS carries no explicit Stern layer, so a mesh presenting this material is a deviation from the
validated model and SHALL be recorded as one in the run provenance (FR-25), even though no case-file
switch selects it. Ingestion SHALL abort when any group in the file is left unclaimed by the mapping,
or when any name the resolved run selects on — the boundary-condition names,
`numerics.wall_distance.sources` and the fluid material set — is supplied by no group, and the
diagnostic SHALL name both lists (QR-12). A mapping whose keys are all vocabulary names while its
values are not is almost certainly written backwards, and the diagnostic SHALL say so rather than
reporting every group unclaimed.

NOTE (a group that claims itself, IF-06): a group whose own name is already a vocabulary name needs
no entry in the mapping, and is claimed by that fact. Which names the run selects on is derived from
the resolved case — the model's boundary vocabulary, both electrodes, the species, the fluid material
set and `numerics.wall_distance.sources` — and never from a constant list. A selection pattern that is not a flat `a|b|c` alternation of literal names SHALL be refused rather
than parsed heuristically, since a requirement derived from a mis-parsed pattern is a gate that can
only pass.

NOTE (a solid without a permittivity, PHY-03, QR-12): `physics.solid_permittivities` is a map from
material name to relative permittivity, defaulting to empty; PHY-20 gives ε_r = 3.2 for the membrane
and 20 for the protein and the analyte, and it is not defaulted because the mesh decides which
solids exist. It is the one member of `physics:` that is not a switch, and `pb` and `pb-linear`
carry no solids, so a non-empty map beside one of them SHALL be refused as §5.3.1's other
inapplicable switches are; each value SHALL be finite and positive, and each key SHALL name a solid
material of the vocabulary, because a key naming a fluid domain (`electrolyte`, `cis`, `trans`) would
replace ε_r,f(⟨c⟩) in the electrolyte and a name outside the vocabulary would be recorded and never
applied, so case resolution refuses both naming the key (a vocabulary solid the mesh lacks is allowed);
`poisson` carries them as the coupled models do. On an **ingested** mesh, a material that is
neither in the fluid set nor named in `physics.solid_permittivities` SHALL abort the run, naming the
material; for a model that carries no solids the abort SHALL say that the model cannot be posed on
a mesh with a solid domain, rather than ask for an entry the case would then refuse. Poisson is
solved over the whole domain, so the alternative is the electrolyte's ε_r about
24 times too large in a solid — a plausible wrong answer with no solver diagnostic. Meshes built in
process by the benchmark geometries take a warning instead, since an ingested mesh's material names
were not written by this codebase. A mesh stage 6 generates from a profile is gated as an ingested
one is: its `protein` is a structure's body, not a benchmark's, and the same wrong answer follows
from a missing entry. Rationale: boundary conditions are selected by name and the natural condition under the
`r`-weighted forms is the *free* one (§6.2, NUM-06), so an unmapped wall becomes an open boundary,
the solve converges, and the current is wrong with no residual, no gate and no diagnostic.

NOTE (`geometry.membrane`, `geometry.reservoir`, `numerics.mesh`; stages 5 and 6, FR-09, FR-10,
NUM-30; WP21): `membrane.thickness_nm`, `reservoir.radius_nm` and an
explicit `wall_h_nm` SHALL each be finite and positive, and each is refused naming its value.
Stage 5 applies `membrane.centre_z_nm` as `z ← z − centre_z_nm` and gates the junction as the
§5.2.1 NOTE on the membrane junction on any profile says. `wall_h_nm: auto` resolves to
`size_scale × min(0.05 nm, λ_D/5)`. λ_D is §6.3's `√(ε₀ ε_r,f⁰ RT / (2F² I))`, with `ε_r,f⁰`
from `electrolyte.parameters`, the case's temperature and the ionic strength I of the bulk species.
The 0.05 nm ceiling is §5.2.2's pore-boundary maximum, which the validated reference applied at
every concentration. It governs below 1.474 M, and above that NUM-30's target is finer and governs.
`ε_r,f⁰` is used rather than the concentration-corrected permittivity, so the mesh does not move
when the permittivity correction is switched. An explicit value is used as written, times
`size_scale`. `wall_for_concentration_M`, default none, takes λ_D at that concentration instead of
the case's own for `auto`, so every salt at or above it shares one mesh (§8.2.14 P10). It SHALL be
positive and finite, and is refused beside an explicit `wall_h_nm`, which it would not move. The
manifest records the run's own λ_D and NUM-30 ratio beside the design concentration and the λ_D it
sized the wall at. A resolved wall size coarser than λ_D/5 is logged and recorded in the manifest, not
refused: it is a discretisation choice, and a mesh-convergence study needs coarse meshes. §5.2.2's
other sizes are each multiplied by `size_scale`. After meshing, the mean length of the `wall`
boundary segments SHALL NOT exceed 1.15 × the resolved wall size, and the longest SHALL NOT exceed
2.0 ×, or the run aborts naming the statistic, the segment and its midpoint (QR-12). Netgen treats
the size as a target, and 1.045–1.078 and 1.25–1.62 are the measured means and maxima (WP21 plan,
Design §3). `backend: gmsh` meshes the stage-5 region with the optional backend of ADR-002, under
the §5.2.2 NOTE on its size field, and passes the same three gates. It needs the `gmsh` extra.
Without it, stage 6 refuses the run, naming the extra and the import error, whether that error is a
missing module, a native library the wheel could not load, or a library that loads and then fails
to initialise (CON-10; REV-37). The resolved case is not refused: `backend` is checked only against
the registered meshers, `netgen` and `gmsh` as shipped (§5.5). A generated mesh's key records the backend and that backend's own settings, and the Gmsh
version is recorded beside the key (WP23 D8, D9). The key's wall entry is the resolved wall size,
its source and `size_scale`, never λ_D: λ_D moves the mesh only through the wall size, so below
the 1.4741 M at which the ceiling binds a salt sweep meshes once. λ_D stays in the manifest's
sizing record beside the key (REV-16; WP46).
`maxh_nm`, default none, is the global element size of an idealised pore, finite and positive
and refused naming its value otherwise; none takes §5.2.2's global 10 nm. It is multiplied by
`size_scale` as the wall size is, and it enters the stage-6 key (the §5.2.2 NOTE on an idealised
pore).
`boundary_layer: true` is refused naming FR-11. `geometry.analyte` on a generated mesh is refused naming FR-21.
Beside `inputs.mesh`, any `numerics.mesh` key away from its default is refused naming it, because
nothing meshes and the key would change nothing.

NOTE (`electrolyte.parameters`, `electrolyte.driver`): `parameters` names the correction file the
*reference* properties are read from — `D_i^0`, `η^0`, `ϱ^0`, `ε_r,f^0` and the steric diameters
`a_i`, `a_0` — and is separate from the per-property correction models because a classical PNP-NS
run turns every correction to `none` and still needs those values. Steric diameters given under
`corrections.steric` SHALL be checked against that file and SHALL NOT override it: they are fitted
parameters of the correction set (FR-16), and a case file that could override them silently would
be a second source of truth for a physical constant. `driver` selects the argument the
concentration corrections are evaluated at: `average`, `⟨c⟩ = (1/n)Σc_i` (PHY-01), or
`ionic_strength`, which is a deviation from the validated model and is recorded as one.
`electrolyte.temperature_K` is checked against that file the same way and SHALL be refused naming
both values when it differs: every reference property, every scale and `V_T` are taken from the
file, whose fits are temperature-specific, so a case at another temperature would be solved at the
file's while its manifest recorded the case's (code review CR-1).

NOTE (a correction file outside the package, FR-16, FR-25; §8.2.22 X6, REV-122): `electrolyte.parameters`
and each `electrolyte.corrections.*.model` MAY name a file by a path, relative to the case file or
absolute, as well as by the name of an installed file. A file read by path is not pinned by the
package's version, so its content hash SHALL enter the stage-8 key and the FR-25 manifest, and the
file SHALL be listed as a deviation from the validated default; an edit of the file then misses the
cache rather than serving a stale result. Its **path** SHALL NOT enter a key: a key carries the
file's name alone, so one calculation run beside two copies of the same file keys one artefact and
two checkouts of one piece of work share a cache, while an edit of either file still moves the key
through the content hash. A case naming two correction files of one file name by different paths
SHALL be refused, naming the file name, rather than keyed as though it named one (QR-12). A name
ending in `.yaml` is a path; any other is an installed file's name. A relative path is taken
against the directory of the case file the run read, as the NOTE on a relative path above has it;
the manifest records the file among the run's inputs by its absolute path and hash, and SHALL
refuse rather than record a null hash for a file it cannot find, and a reproduction takes a
relative path against the directory the original case was read from, so that it reads the file the
run read (QR-08).

NOTE (`numerics.nonlinear`): the values shown are the NUM-16 reference settings — the monolithic
damped Newton of the reference model, 100 iterations, relative tolerance 10⁻⁶ on the per-field
relative update of the undamped direction, or the residual at its absolute floor (NUM-16's NOTE). `strategy: hybrid` and `damping: backtracking` select
the NUM-20 fallbacks, which no release schedules, so a case selecting either SHALL be refused as an
unsupported section naming NUM-20 and its fallback (WP40).

NOTE (`numerics.elements`, NUM-03): `phi` and `c_i` carry one element order; `u` is independent of
them and `p` is independent of both, so the reference implementation's own discretisation —
quadratic `phi` and `c_i` with linear `u` and `p` — is expressible. An order for `u` at or below
the order of `p` SHALL be refused unless `numerics.stabilisation` selects a mode supplying the flow
stabilisation of §6.4.2, and the refusal SHALL name both the inf-sup condition and the mode that
would permit the pair. The refusal is made when the case is loaded, so `nanopnp validate case`
and the desktop shell's commit make it with the same text as a run. All three orders are recorded
in the run provenance record (NUM-03).

NOTE (`numerics.stabilisation`): the value set is
the registered modes, shipped as `none | supg | reference`; a mode registered at run time widens it
(§5.5; §8.2.8 H7). `none` is the validated default and the production policy of NUM-11;
`supg` is NUM-11's flag, the streamline term alone; `reference` is the mode of NUM-14, streamline
and crosswind on the transport operator together with the flow stabilisation of §6.4.2, and is the
only shipped value permitting an equal-order velocity–pressure pair; a registered mode permits
one by declaring it (`permits_equal_order`).

NOTE (`numerics.wall_distance`): `sources` is the boundary-name pattern the PHY-02 distance field
`d` is measured from, and its validated default is the pore wall alone. PHY-02 excludes the
membrane from the source set deliberately, so widening `sources` is a deviation from the validated
model and SHALL be recorded in the run provenance (FR-25). `max_distance_nm` is the saturation
distance beyond which the wall functions are 1 to within round-off. A value other than the
validated 3.0 nm SHALL be recorded as a deviation for the same reason: below about 1 nm the ion
wall function no longer reaches 1 inside the cap, which changes the model. A value that is not
finite and positive SHALL be refused by `resolve()`, naming the key (codebase review CR-4).

NOTE (`walls`): the wall values name the condition applied, not its absence. `ion_flux` takes
`no_flux | prescribed` and `slip` takes `no_slip | navier | free`. Under the `r`-weighted forms of
§6.2 the natural condition is the free one, so a value reading as "none applied" would silently
remove no-slip while appearing to be the validated default. The forms pose `no_flux` and `no_slip`
only, so every other value SHALL be refused by name until the condition is implemented, and the
refusal lifted in the same commit that implements it: a condition recorded in the manifest but not
applied would be a plausible wrong answer (code review CR-2).

NOTE (`outputs:`): the list selects what the run produces, and each word is refused rather than
silently ignored where it cannot be met. `current`, `transport_numbers` and `eof_rate` select scalar
quantities of interest (§6.7). Each word names a registered output, and each output states what it
needs of a model's declaration (§5.4.3; §8.2.32 AH1). A word the named model does not provide SHALL
be refused when the case is resolved, naming the model and the outputs it provides, rather than when
stage 11 reaches it (WP26); the electrostatic models provide `fields` alone, so a case naming one of
them writes `outputs: []` or `outputs: [fields]`. `fields` gates the IF-07 field export, which is off unless asked for:
the export is of order ten megabytes per solve and an envelope sweep of thousands of points would
otherwise write tens of gigabytes nobody requested. `analyte_force` requires the mesh to carry an
`analyte` material, and a case asking for it on a mesh without one SHALL abort naming the missing
material (QR-12). `rectification` is a two-point quantity, `I(+V)/I(−V)`; a case asking for it at a
single operating point SHALL be refused naming it as such, because the second bias can only come
from a sweep (FR-24) and inventing one would report a ratio the run did not measure. A sweep
(§5.3.4) SHALL therefore strip `rectification` from each member's `outputs:` and produce it in
collection, from pairs of members whose case-file assignments are equal except at
`boundary_conditions.bias_V` and whose two biases are exactly opposite. Exactly, not approximately:
a tolerance on the pairing would report the ratio of two unrelated operating points as a
rectification. A sweep asking for `rectification` whose axes produce no such pair SHALL be refused
when the plan is built, naming the axis, rather than collecting a column of absent values (QR-12).
