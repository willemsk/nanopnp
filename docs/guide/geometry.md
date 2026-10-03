# From a structure to a mesh

Stages 2 to 6 turn the aligned structure of stage 1 into a gated mesh. Stage 2 smears the atoms
into a 3D density map. Stage 3 averages that map around the axis into an (r, z) map. Stage 4 draws
the pore's outline from it, stage 5 builds the membrane and reservoirs around the outline, and
stage 6 meshes the result. [Structures and trajectories](structures.md) covers stage 1, and
[example 06](../_generated/examples/06-pdb-to-mesh.md) runs every stage on a PDB entry.

```console
$ nanopnp run case.yaml --store store --run-dir run --upto mesh
```

`--upto mesh` stops before anything is solved. Each stage is cached in the store, so changing a
key re-runs only the stages downstream of it. `nanopnp stage <name> case.yaml` runs one stage, and
what it needs upstream, and prints its artefact.

This page says what each stage does and which key steers it. The formulas, thresholds and their
derivations are in the [specification](../_generated/model/specification.md): §5.2 lists the
stages, [§5.2.1](../_generated/model/specification.md#521-contour-conditioning-and-its-gate) the
contour's conditioning and gate, [§5.2.2](../_generated/model/specification.md#522-meshing) the
mesh sizes, and the NOTEs of
[§5.3.1](../_generated/model/specification.md#531-case-file) the case keys. Measurements on ClyA
are in the knowledge base, [ClyA geometry and
charge](../_generated/model/knowledge/04-clya-geometry-and-charge.md) §1.3 and §1.4.

## The case keys

A `structure:` case may carry a `geometry:` block. Every key has a default, and the defaults are
the settings of the published ClyA model.

```yaml
geometry:
  density: {grid_spacing_nm: 0.05, kernel: gaussian_vdw, sharpness: 0.93}   # stage 2
  contour: {isolevel: 0.25, smoothing: taubin, simplify_tol_nm: 0.02}        # stage 4
  membrane: {thickness_nm: 2.8, centre_z_nm: 0.0}                             # stage 5
  reservoir: {radius_nm: 250.0}                                               # stage 5
numerics:
  mesh: {backend: netgen, wall_h_nm: auto, size_scale: 1.0}                   # stage 6
```

No gate threshold is a case key. The thresholds are constants of the code, recorded in each
artefact's key, so two runs that passed the same gates can be told apart from two that did not.

## Stage 2: the density map

Each atom becomes a Gaussian whose width is its van der Waals radius times `sharpness`. The radius
comes from the CHARMM set that PDB2PQR ships, by residue and atom name, and an atom the set does not
name is refused, naming its chain, residue and atom. There is no fallback by element, because a
guessed radius makes a plausible wrong wall. The atoms of one frame are combined as a probability
that at least one is present, so the map runs from 0 in the solvent to 1 inside the protein. With
a trajectory, the frames' maps are averaged.

`grid_spacing_nm` sets the grid, between 0.025 and 0.05 nm (FR-04). Its nodes sit at whole
multiples of the spacing in the stage-1 frame, so the axis is a column of nodes. The map must be
finite and between 0 and 1, or the run stops naming the voxel.

## Stage 3: the average around the axis

Stage 3 has no keys of its own: the n it averages over is the point group's. It averages the map
over the n rotated copies of the assembly, then around the axis, into an (r, z) map. The
averaging is exact, so no bin is interpolated.

It also reports how far the structure is from its own symmetry, as two variances around the
axis: that of the n-fold average, and that of the map without it. Their difference is the part of
the structure that is not n-fold symmetric. Neither is gated, because no threshold is specified.
Read them from the summary:

```console
$ nanopnp stage symmetry case.yaml --store store --json
```

`maximum` gives each variance's largest value and where it is. `unresolved_radius_nm` is the
radius below which the grid is too coarse to resolve any n-fold variation, so the variances there
are recorded as unresolved rather than as zero.

## Stage 4: the contour

Stage 4 draws the pore wall as the contour of the (r, z) map at `isolevel`, 0.25 by default. It
then conditions the loop: a closing and an opening by a disc of radius twice the grid spacing remove
gaps and fins too thin to mesh, Taubin smoothing follows when `smoothing: taubin`, the loop is
simplified to within `simplify_tol_nm`, which must be below the grid spacing, and vertices closer
than the spacing are removed.

The loop is then gated on the criteria of
[§5.2.1](../_generated/model/specification.md#521-contour-conditioning-and-its-gate): it must be
simple, its vertices spaced and its features wide enough to mesh, and it must stay clear of the
axis. Its radius is also checked against the largest sphere that fits on the axis between the
atoms, frame by frame. The contour may cut into that sphere by no more than the grid spacing, and
may stand no more than 1.5 nm outside it. A failure stops the run, naming the criterion, its value, the threshold and where on
the loop it failed.

What stage 4 produces is a pore profile: a `nanopnp/profile/v1` document with `provenance.source:
pipeline`, in the stage-1 frame. It is the same kind of document as the reference fixture, and it
can be exported and supplied to another case (see [Supplying a profile](#supplying-a-profile)).

## Stage 5: the region

### Registering the membrane

The density map has no bilayer, so stage 5 adds one, defined analytically in (r, z).
`geometry.membrane.centre_z_nm` is the height of the bilayer's centre on the stage-1 frame's axial
coordinate, which is the structure file's own. Stage 5 subtracts it from every z, so the model
frame has the bilayer centred at z = 0.

Choosing it is part of preparing the structure, because it says where the protein sits in the
membrane. For ClyA, nanopnp's validation places the C-alpha centroid of residues 8 to 292 where the
molecular-dynamics structure of the published model has it (§7.4, the NOTE on VAL-05). Example 06
does the same while preparing the file, so its cases keep the default of 0. For your own pore,
take it from a membrane-embedded simulation, from the hydrophobic belt of the structure, or from a
database of membrane-protein orientations, and record where it came from.

`membrane.thickness_nm` is the bilayer's thickness, and `reservoir.radius_nm` the radius of the
half-disc of electrolyte around the pore. Stage 5 fits the membrane's inner edge to the outer
surface of the profile, assembles the electrolyte, protein and membrane domains, and names every
boundary. It gates the junction where the membrane meets the protein, so neither a gap nor an
overlap is left there.

`charge.exclusion_offset_nm`, off by default, adds an ion-exclusion shell here: the profile offset
outward by that distance, meshed as an `exclusion` material that ions cannot enter, with the wall on
its outer surface. It is one of the two FR-15 switches, and [From a structure to a
charge](charge.md#the-two-fr-15-switches) covers both.

## Stage 6: the mesh

Stage 6 meshes the region under the size table of
[§5.2.2](../_generated/model/specification.md#522-meshing), with netgen by default or Gmsh on
request (see [Meshes](meshes.md#choosing-the-mesher-of-a-generated-mesh)).

`numerics.mesh.wall_h_nm` sets the element size on the pore wall. `auto` takes it from the Debye
length of the case's electrolyte, capped at the published model's wall size, so two cases with
different concentrations can get different meshes. `size_scale` multiplies every size in the
table, the wall's included, which is how a mesh-convergence study is run as a sweep.

The mesh then passes the gates every mesh does ([Meshes](meshes.md#the-quality-gate)), plus one of
its own: the wall's segments must come out near the size asked for. A generated mesh is filed under
its recipe, the region and the sizes, and its content hash is recorded beside that key. The
manifest records the mesh a solve actually read.

## Supplying a profile

A case can skip stages 1 to 4 and start from a profile document:

```yaml
schema: nanopnp/case/v2
name: from-profile
inputs:
  profile: {path: contour.profile.yaml}
electrolyte: ...
```

There is no `structure:` section, because a stage whose output is supplied does not run, and
neither does anything upstream of it. Stage 5 applies `geometry.membrane.centre_z_nm` to the
supplied profile exactly as to stage 4's. The run records the file by its SHA-256 under the
manifest's `inputs.files`, and the region and mesh are filed under new keys, since their input
changed. The same profile meshes to the same mesh, which example 06 asserts.

## Editing the contour by hand

A contour may need a correction the pipeline cannot make: a loop around a flexible region that the
density does not resolve, or one stage 4 refuses. There are two routes, and both produce a profile
document that enters a run through `inputs.profile`.

**The Geometry tab of the desktop shell.** Drag, add and delete vertices on the contour, check the
edit against the §5.2.1 criteria, and save it. The shell writes the edited profile and a derived
case that uses it in place of the structure. It re-derives the profile's measurements and marks
it `provenance.source: hand-edit`. See [Desktop shell](desktop.md).

**A profile document edited as text.** Export stage 4's profile, edit its `vertices`, and supply
it through `inputs.profile`. The document's `provenance` block records measurements of its own
polygon: `vertex_count`, `min_vertex_spacing_nm`, `min_feature_size_nm` and `signed_area_nm2`.
The loader checks each against the vertices. A vertex moved without them being updated is refused,
and `nanopnp run` exits `3` with a message such as:

```text
provenance.signed_area_nm2 is <recorded> but these vertices give <measured>; the provenance block
does not describe this polygon
```

So re-derive all four after editing, and set `provenance.source` to `hand-edit`, as the shell does.
The loader does not check the label, so keeping it honest is up to you: a profile that says
`pipeline` claims stage 4 drew it. Either way, the edited profile is then gated like any supplied
profile, by stages 5 and 6. The Geometry tab re-derives the measurements for you, which is the
reason to prefer it.

## Exporting what the stages store

`nanopnp stage <name> case.yaml --export PATH` runs the stage, from the store where it can, and
writes its artefact in the format the suffix of `PATH` names. The path is an output location and
changes no key. A stage or suffix it does not write is refused before anything runs, and a failed
write leaves no file.

| Stage | Suffix | Writes |
|---|---|---|
| `structure` | `.pdb` | the aligned ensemble's first frame, with a `.dcd` of every frame beside it, in ångströms |
| `density` | `.dx`, `.ccp4`, `.mrc`, `.map` | the 3D map as OpenDX or CCP4/MRC, in ångströms, for a molecular viewer |
| `density` | `.npz` | the stored map, nanopnp's own format, in nm |
| `symmetry` | `.npz` | the stored (r, z) average and its two variances, in nm |
| `contour` | `.yaml` | the stored profile document, byte for byte |
| `mesh` | `.msh` | the stored Gmsh MSH 4.1 mesh, byte for byte |

The 3D files are in ångströms because that is the unit molecular viewers read, and the CCP4/MRC
format defines its cell in ångströms. A map exported this way sits on the structure exported beside
it. Inside nanopnp, and in its own `.npz` files, lengths stay in nm (the IF-05 NOTE on length
units, §3.1). The profile and the mesh are copied byte for byte, so the file you hold has the hash
the store records.
