# From a structure to a charge

Stage 7 gives the pore its fixed charge. It runs in two halves. **Protonation** assigns each atom
of the structure a partial charge and a radius, with PDB2PQR and PROPKA. **Deposition** smears
those charges into a fixed-charge density on the mesh, and gates it. Both halves run after stage 6,
because the charge is deposited on the mesh the solve uses. [From a structure to a
mesh](geometry.md) covers stages 2 to 6, and [example 07](../_generated/examples/07-pdb-to-charged-run.md)
runs every stage on a PDB entry, through to a charged solve.

```console
$ nanopnp run case.yaml --store store --run-dir run --upto charge
```

`--upto charge` stops before the solve. Each half is cached in the store like every other stage,
so changing the pH re-runs the protonation and the deposition, and nothing upstream of them.

This page says what each step does and which key steers it. The formulas, the tolerances and their
derivations are in the [specification](../_generated/model/specification.md):
[§4.4](../_generated/model/specification.md#44-fixed-charge-and-dielectric-model) has the charge
pipeline (PHY-16 to PHY-20) and its NOTEs, and the NOTEs of
[§5.3.1](../_generated/model/specification.md#531-case-file) the case keys. A field supplied as a
file, rather than produced from a structure, is [Charge and permittivity fields](fields.md).

## The case keys

A case carrying `structure:` may carry a `charge:` block. Every key has a default, and the defaults
are the settings of the published ClyA model, so a case without the block runs exactly as one with
it written out.

```yaml
charge:
  ph: 7.5                         # protonation: the pH PROPKA assigns states at
  forcefield: CHARMM              # protonation: PDB2PQR's force field
  titration: propka               # protonation: propka, or none
  smearing:                       # deposition
    sharpness: 0.5                #   kernel width w = sharpness x atomic radius
    grid_spacing_nm: 0.005        #   the export lattice
  exclusion_offset_nm: 0.0        # the ion-exclusion shell, built at stage 5; 0 is off
  dielectric_transition_nm: 0.0   # the derived dielectric, built at stage 7; 0 is off
```

`ph` is a condition of the experiment, as the concentration is. `grid_spacing_nm` is a
discretisation choice. Every other key is a switch: a value away from its default is listed in the
manifest as a deviation from the validated model (FR-25). A key that would change nothing is
refused rather than ignored, naming the key that makes it inert. `ph` beside `titration: none` is
one example, and `smearing` beside a supplied `inputs.charge` is another. The [case-file
reference](../_generated/reference/case-file.md) lists every key with its option set.

## Protonation

PDB2PQR runs once for each frame of the aligned structure, at `charge.ph`, under
`charge.forcefield`, with PROPKA choosing the protonation state of each titratable residue
(PHY-16 step 3). Each frame's hydrogens and waters are removed first. A residue the source file
names by a protonation variant, such as `HSE` or `GLH`, is renamed to its parent, so the states
are PROPKA's at this pH and not the file's. Chains are kept.

`titration: none` runs PDB2PQR without PROPKA: every residue keeps the force field's standard state.
`CHARMM`, `PEOEPB` and `SWANSON` are the force fields offered. The others PDB2PQR ships give charged
atoms a zero radius, which the kernel cannot smear, so they are not offered.

The artefact records, for each frame:

- **`Q_net`**, the sum of the frame's charges. The run's `Q_net` is the mean over frames.
- **Unapplied states.** Under CHARMM, PDB2PQR cannot represent some states PROPKA prefers, such as
  a neutral terminus or a deprotonated cysteine, and keeps the standard one. Each is recorded by
  residue, with PROPKA's pKa, and is not an error: these are the validated model's states.
- **Per-chain differences.** The chains of a homo-oligomer are protonated independently and are
  not symmetrised. A residue whose charge differs between chains of the same sequence is recorded.

`nanopnp stage protonation case.yaml --json` prints that record. `--export protein.pqr` writes the
charges and radii as a PQR file, one `MODEL` per frame.

### Supplying a PQR

A PQR made elsewhere, or exported by a previous run, enters through `inputs.pqr`:

```yaml
inputs:
  pqr: {path: protein.pqr, format: pqr}
```

PDB2PQR and PROPKA then do not run. The protonation stage still runs, reading the file, and
records `source: inputs.pqr` and the file's hash. Leave out the protonation keys beside it,
because the file replaces the step they configure. Keep `structure:`, because stages 1 to 6 still
build the geometry from it. Each frame of the PQR is registered to stage 1's frame by
superposing its C-alpha atoms on the structure's, and its heavy atoms must then sit on the
structure's: a PQR of another structure, or with another number of frames, is refused naming the
frame. Every atom needs a positive radius. The deposit depends only on the atoms' positions, charges and radii, so
an exported PQR fed back in deposits the same charge.

## Deposition

Each atom becomes a 3D Gaussian of width `sharpness` times its radius, carrying its charge. Its
mean around the pore axis has a closed form, so the axisymmetric charge density is computed
exactly, without building a 3D grid (PHY-16 steps 4 and 5, PHY-17). Atoms of zero charge are left
out.

The atoms are summed on the **export lattice**, an (r, z) grid at `grid_spacing_nm`. Each atom's
lattice sum is scaled to its charge, so the lattice carries `Q_net` exactly. The lattice is then
**deposited** onto the mesh: each triangle receives a polynomial of the potential's element order,
by a weighted projection whose integrals are taken on the lattice. Each element keeps exactly the
charge of the lattice nodes it holds. The charge is deposited on every material (PHY-16 step 6).

**The charge is deposited, not interpolated.** A structure's charge changes sign every few
hundredths of a nanometre, which is finer than a mesh element. Sampling it at the solve's
quadrature points aliases: the integral moves with the quadrature order and does not converge as
the mesh is refined (the §4.4 NOTE on the consumer leg). The deposit integrates every atom over the
elements, so it does not alias, and the solve assembles exactly the charge the lattice carries.

Before depositing, stage 7 checks that at least half of the absolute charge has its atoms inside
the mesh's solid materials, and that no lattice charge falls outside the mesh. A structure in
another frame than its mesh fails here, naming the share or the location.

## The conservation report

Stage 7 then checks that the charge on the mesh is the charge of the structure (PHY-19, QR-03). The
report is in the artefact and in the manifest's `charge` group:

```console
$ nanopnp stage charge case.yaml --store store --json
$ nanopnp inspect run
```

| Entry | Compares |
|---|---|
| `producer` | the lattice's integral against `Q_net` |
| `consumer` | the deployed field's integral, at the solve's quadrature order, against the lattice's |
| `quadrature_agreement` | the deployed field's integral at that order against a higher one |
| `per_plane` | the charge below each of a set of planes across the protein, on the lattice and on the mesh, against the atoms themselves |
| `boundary_ring` | what the lattice carries at its edge |
| `axis_guard_deficit_e` | what the axis guard would remove if the lattice were read back as a supplied field |

Each entry records its value beside its tolerance. The two legs are exact by construction, so
they guard the construction: a lost atom, a lost frame or a missing `2πr` fails one of them and
names the side it belongs to. The per-plane check is the discriminating one. Its reference is the
atoms, in closed form, rather than the lattice, so an error that moves charge along the axis
without changing the total still fails it. The worst plane of each side is recorded with its z.

A check that fails stops the run with exit code `4`, naming the check, its value, its tolerance and
where.

### Exporting the charge

```console
$ nanopnp stage charge case.yaml --store store --export charge.field.yaml
```

This writes the lattice as a `nanopnp/field/v1` areal charge density, with its data in
`charge.field.npz` beside it, declaring `Q_net`. `.dx`, `.mrc` and `.ccp4` write it for other
tools. The export is for those tools, and for a mesh fine enough to resolve it. Supplied back
through `inputs.charge` on the mesh it came from, it is refused by the quadrature-agreement check,
for the aliasing reason above. Within nanopnp, deposit from the PQR instead.

## The two FR-15 switches

The published model has a sharp material interface: the protein has its permittivity, the
electrolyte its own, and ions reach the protein's surface. Two switches change that. Both are off
by default, both are built from the stage-4 profile, and each is listed as a deviation when set.

- **`exclusion_offset_nm`**, the ion-exclusion shell. Stage 5 offsets the pore profile outward by
  this distance and meshes the band between them as an `exclusion` material, which ions cannot
  enter (the §5.2.1 NOTE on the ion-exclusion shell). The wall, its no-slip and no-flux conditions,
  and the wall distance move to the shell's outer surface. See [From a structure to a
  mesh](geometry.md#stage-5-the-region).
- **`dielectric_transition_nm`**, the derived dielectric. Stage 7 derives a solid fraction `χ` that
  steps smoothly from 1 in the protein to 0 in the water over this width, centred on the profile
  (the §4.4 NOTE on the derived solid fraction). The permittivity blends the protein's with the
  fluid's by `χ`, as a supplied `inputs.eps_r` does. The membrane stays sharp.

Each is refused where it would change nothing, such as beside a supplied mesh, and below the
resolution of the density grid it is built from.

## Which models take a charge

A physics model takes a fixed charge when its declaration lists `fixed_charge`, and a solid
fraction when it lists `solid_fraction` (the §5.4.3 NOTE). Stage 7 reads the declaration, not the
model's name. Of the shipped models, `epnp-ns`, `pnp-ns`, `pnp` and `poisson` take both, and `pb`
and `pb-linear` take neither. A structure case under a model that takes no charge does not
protonate. `inputs.pqr` beside such a model is refused, naming the models that accept it.
[Physics models](../project/physics-models.md) says how a model declares what it takes.
