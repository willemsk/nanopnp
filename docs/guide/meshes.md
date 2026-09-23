# Meshes

In v0.5 the mesh is an input. You supply it through `inputs.mesh`, or generate an idealised pore or
the ClyA reference geometry with `nanopnp mesh`. Building a mesh from a protein structure is the
v0.9 geometry pipeline (FR-10).

## Coordinates and formats

A mesh is a 2D triangulation of the `(r, z)` half-plane, in nanometres, with the symmetry axis at
`r = 0`: the azimuthal cross-section of the axisymmetric problem (CON-04). Two formats are read,
chosen by `inputs.mesh.format` or, if that is absent, by the file suffix:

- **Gmsh MSH** (`msh41`, `msh`, `gmsh`; suffix `.msh`), the archival format (IF-06);
- **Netgen** (`vol`, `netgen`; suffix `.vol`).

Physical groups name the domains and the boundaries. A 3D mesh, or one with a vertex at negative
radius, is refused.

## The group vocabulary

The solver selects domains and boundaries by name, from a fixed vocabulary (§5.3.1):

| Kind | Names |
|---|---|
| Domains | `electrolyte`, `cis`, `trans` (all fluid); `membrane`, `protein`, `analyte`, `exclusion` (solid) |
| Boundaries | `axis`, `wall`, `membrane`, `membrane_outer`, `cis`, `trans`, `analyte`, `interface` |

`inputs.mesh.groups` maps the file's own group names onto that vocabulary, as `{name in the file:
vocabulary name}`. Many-to-one is fine: a CAD export often splits one wall into several curves. The
mapping has three rules, each enforced with a diagnostic naming the group:

- **Every group must be claimed.** A boundary nothing selects on silently receives the natural
  boundary condition (NUM-06), so a group that is neither in the vocabulary nor mapped onto it is
  refused. An interior seam that separates fluid from fluid maps to `interface`, which nothing
  selects on.
- **A name must land in the right namespace.** Mapping a boundary group onto a domain name is
  refused.
- **A mapping written backwards is caught.** The key is what the file says, and the value is what
  the solver selects on.

The `wall` boundary is special: it is the source of the distance field the wall corrections are
measured from (PHY-02). The membrane is deliberately left out of that source set, so calling a
membrane face `wall` changes the physics.

Every solid domain needs a relative permittivity in `physics.solid_permittivities`, except the
ion-exclusion shell `exclusion`, which takes the fluid's permittivity by design. A mesh carrying an
`exclusion` domain is recorded as a deviation from the validated model, which has no Stern layer.

## The quality gate

Every mesh, supplied or generated, is gated on element quality before anything is solved (VER-10):
no inverted element, and both quality measures, SICN and gamma, above the specified floor. A
failure exits with code `4`. It names the measure, its value, and the element's centroid, so you
know where to refine. The wall-distance gate (NUM-34) runs later, once the model knows whether its
wall corrections are on. It refuses a mesh too coarse at the wall to resolve the corrections.

## Generating a mesh

```console
$ nanopnp mesh cylinder --out pore.msh
$ nanopnp mesh reference --out clya-reference.msh
```

- **`mesh cylinder`** builds an idealised pore: a straight lumen through a membrane, with a
  quarter-disc reservoir on each side. `--pore-radius-nm`, `--membrane-thickness-nm`,
  `--reservoir-radius-nm`, `--maxh-nm` and `--wall-h-nm` shape it. The defaults give the smallest
  mesh the wall-distance gate accepts with the wall corrections on. That is quick to solve, but not
  converged. The lumen is the domain `electrolyte`, the reservoirs are `cis` and `trans`, and the
  two pore mouths are left at Netgen's `default` name, which the printed mapping sends to
  `interface`.
- **`mesh reference`** builds the ClyA reference geometry at the published mesh preset (§5.2.2). It
  takes no geometric flag. Its groups are already in the vocabulary.

Both commands gate the mesh by the same route a run ingests it by. They print the mesh's content
hash, which the run's manifest will record, and the `inputs.mesh` block to paste into a case. A mesh
the gate refuses leaves no file behind. These generators produce input files, so their flags do not
change what a run solves: the run records the mesh by its content hash, like any supplied mesh (the
IF-02 generators NOTE).

## A mesh is identified by its content

A mesh's hash is taken over its canonical vertices, connectivity and group tags, never over the
file's bytes or its path. A mesh rewritten with a different header, or copied under another name,
is the same mesh and hits the store. A mesh whose `wall` gained one edge is a different mesh.
