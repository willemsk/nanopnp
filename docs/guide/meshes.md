# Meshes

A mesh is either an input or built by the pipeline. You supply one through `inputs.mesh`, or write
the ClyA reference geometry with `nanopnp mesh reference`. A case with a `geometry.pore`, a
`structure:` section or an `inputs.profile` builds its own, through stages 5 and 6 (FR-10): see
[From a structure to a mesh](geometry.md).

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
ion-exclusion shell `exclusion`, which is ion-free water (`ε_r,f⁰`) by design: ions do not exist
there, so the salt correction does not apply. A mesh carrying an `exclusion` domain is recorded as a
deviation from the validated model, which has no Stern layer.

## The quality gate

Every mesh, supplied or generated, is gated on element quality before anything is solved (VER-10):
no inverted element, and both quality measures, SICN and gamma, above the specified floor. A
failure exits with code `4`. It names the measure, its value, and the element's centroid, so you
know where to refine. The wall-distance gate (NUM-34) runs later, once the model knows whether its
wall corrections are on. It refuses a mesh too coarse at the wall to resolve the corrections.

## An idealised pore

A case declares a straight lumen through a membrane, with a quarter-disc reservoir on each side, as
`geometry.pore`, and stage 6 meshes it under `numerics.mesh`:

```yaml
geometry:
  pore: {shape: cylinder, radius_nm: 2}
  membrane: {thickness_nm: 6}
  reservoir: {radius_nm: 10}
numerics:
  mesh: {maxh_nm: 4, wall_h_nm: 0.35}
```

`maxh_nm` is the global element size and `wall_h_nm` the size at the wall, or `auto` to size it by
the Debye length. Both are read only beside `geometry.pore`; a supplied mesh refuses them. The lumen
is the domain `electrolyte`, the reservoirs are `cis` and `trans`, and the two pore mouths are the
boundary `interface`. The defaults are quick to solve, but not converged.

`nanopnp geometry cylinder --out pore.geometry.yaml` writes the same pore as a geometry file and
prints the `geometry:` block that declares it.

## Generating a mesh file

```console
$ nanopnp mesh pore.geometry.yaml --out pore.msh
$ nanopnp mesh reference --out clya-reference.msh
```

- **`mesh <geometry file>`** meshes the pore of a geometry file at `--maxh-nm` and `--wall-h-nm`.
- **`mesh reference`** builds the ClyA reference geometry at the published mesh preset (§5.2.2). It
  takes no geometric flag. Its groups are already in the vocabulary.

Both commands gate the mesh by the same route a run ingests it by. They print the mesh's content
hash, which the run's manifest will record, and the `inputs.mesh` block to paste into a case. A mesh
the gate refuses leaves no file behind. These generators produce input files, so their flags do not
change what a run solves: the run records the mesh by its content hash, like any supplied mesh (the
IF-02 generators NOTE).

## Choosing the mesher of a generated mesh

A case that builds its own mesh, from `inputs.profile` or a `structure:` section, meshes it with
netgen by default. `numerics.mesh.backend: gmsh` meshes it with Gmsh instead:

```yaml
numerics:
  mesh: {backend: gmsh}
```

Gmsh is optional and GPL-2+, so it is an extra and never on the default path (CON-10). Install it
with `pip install "nanopnp[gmsh] @ git+https://github.com/willemsk/nanopnp"`, or `uv sync
--all-extras` in a checkout. `uv` manages Python wheels but cannot install operating system packages.
On Linux, the Gmsh wheel dynamically links native OpenGL and X11 libraries:

- **Arch Linux:** `sudo pacman -S glu libxft libxinerama libxcursor`
- **Debian / Ubuntu:** `sudo apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1`

Without the extra, or on Linux without these native libraries, the case still validates, and the
run stops at the meshing stage with exit code `3`, naming the extra and the import error
(`libGLU.so.1` or a related X11 library when the wheel installed but could not load). The stages
before meshing are cached, so after installing the extra and the system packages a re-run pays for
the mesh only.

Both meshers mesh the same region, assembled once, and under the same size table (§5.2.2). Gmsh
also gets size fields that state what netgen does without being asked: grading away from each
domain's boundary, refining near short edges, and holding the membrane to its own thickness. Both
meshes then pass the same gates, including the wall-size gate. On the ClyA reference profile, Gmsh
makes about 10 % more triangles than netgen, in about half the time. The two meshes give
conductances 1.2e-4 apart, less than refining either mesh moves it. The backend is recorded with the
mesh and keys it. Changing it gives a different mesh in the store, and in a sweep it stops warm
starts across that axis. Boundary layers (`boundary_layer: true`) are refused on either backend
(FR-11).

## A mesh is identified by its content

A mesh's hash is taken over its canonical vertices, connectivity and group tags, never over the
file's bytes or its path. A mesh rewritten with a different header, or copied under another name,
is the same mesh and hits the store. A mesh whose `wall` gained one edge is a different mesh.
