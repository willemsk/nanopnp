---
type: Library Behaviour
title: 4. Geometry, meshing and I/O
description: The geometry, meshing and I/O libraries.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_field_export.py::test_if07_a_discontinuous_quantity_is_written_cell_centred
  at: '2026-10-16T00:00:00Z'
---

## 4. Geometry, meshing and I/O

| Tool | Version | Licence | Verdict |
|---|---|---|---|
| **Netgen OCC** (`netgen.occ`) | 6.2.2606 | LGPL-2.1 | **Default.** Same OpenCASCADE kernel, in-process, no extra binary, no GPL exposure |
| **Gmsh** (Python API) | 4.15.2 | **GPLv2+** | Optional backend. Best-in-class: `BoundaryLayer` (works in 2D), `Distance`/`Threshold`, `Min`/`Restrict` field algebra, `Fan` points, quads-in-BL |
| **scikit-image** | 0.26.0 | BSD-3 | `measure.find_contours` (sub-pixel marching squares), `marching_cubes` |
| **Shapely** | 2.1.2 | BSD-3 | `LinearRing`, `is_valid`, `is_simple`, `make_valid`, `simplify`, `buffer` |
| **meshio** | 5.3.5 | MIT | Reliable but last release 2024-01 — treat as stable-frozen |
| CadQuery / build123d | — | Apache-2.0 | 3D-solid-centric; overkill for a 2D (r,z) region |
| pythonocc-core | — | LGPLv3 | Raw OCCT; only for BRep edge cases |

**Avoid:** MeshPy — actively maintained (2026.1) but wraps **Triangle**, whose licence states
distribution as part of a commercial system is *"permissible ONLY BY DIRECT ARRANGEMENT WITH THE
AUTHOR"*, and **TetGen 1.5** (AGPLv3). Also avoid **pygmsh** (last release 2022-01) and
**pygalmesh** (2022-09), both stale — call the `gmsh` API directly instead.

**Shapely offsetting:** `parallel_offset` is *not* removed and emits *no* DeprecationWarning in
2.1.2 **[tested: pending]**, but its docstring marks it legacy in favour of `offset_curve` (different
sign/`quad_segs` convention). For a closed contour, `buffer(-d)` is more robust than either.

**`find_contours` orientation in (r, z) [tested: pending].** On a `[z, r]` array with
`positive_orientation="high"`, a point `(row, col)` maps to `(r, z) = (col·Δr, row·Δz)`, which
swaps the axes, so the winding flips from the one the docstring describes. A loop around values
above the level has a **negative** shoelace area in (r, z), clockwise, and a loop around a void
inside it is counter-clockwise. Stage 4 tells bodies from holes that way (`nanopnp.geometry.contour`,
WP20 D4). A contour that reaches the array's edge comes back open, with its first and last points
distinct, and `fully_connected="high"` joins diagonal neighbours above the level. Measured with
scikit-image 0.26.0 on 26 September 2026.

**Shapely closing and opening [tested: pending].** `region.buffer(δ, quad_segs=8, join_style="round")
.buffer(−δ, …)` is a closing and the reverse order an opening; both keep a straight wall straight,
fill a slot narrower than 2δ completely, and remove a fin thinner than 2δ with no bump at its root.
A 90° corner moves by `δ²(1 − π/4)` in area, concave corners gaining and convex ones losing. The
output ring is densely sampled on its arcs, with edges of about `δπ/16`, which is why stage 4
resamples before it measures a feature size. Measured with Shapely 2.1.2 (VER-51).

**Keep MSH 4.1 as the archival interchange format** — physical groups survive round-trips there
and get mangled in some VTU paths.

**Netgen's own `.vol` round-trips boundary and material names [tested: pending].** `mesh.ngmesh.Save(path)`
followed by `ngsolve.Mesh(path)` returns `GetMaterials()` and `GetBoundaries()` unchanged, so a
mesh written by one process and solved by another keeps the vocabulary the essential conditions and
the `definedon` restrictions are written against. Measured on a `CylindricalPoreGeometry` at
`maxh = 4 nm`: materials `['electrolyte', 'membrane', 'cis', 'trans']` and boundaries `['axis',
'cis', 'default', 'membrane', 'membrane_outer', 'trans', 'wall']` on both sides of the write. This
is what makes an externally supplied mesh usable at all — a format that dropped the names would
apply every essential condition to nothing and converge to the wrong problem in silence, so a
release that reads a mesh from a case file must restrict itself to formats that carry them.

**Netgen's own reader is an MSH 2.2 parser and cannot read the archival format [tested: pending].**
`netgen.read_gmsh.ReadGmsh` handed a 4.1 file dies inside `int()` on the entity-block header, so the
reader for the format IF-06 mandates cannot be the one netgen ships. `meshio` is therefore not
optional bookkeeping — it is the only route in. CON-10 keeps `gmsh` itself off the default path for
an unrelated reason (GPLv2+), and the two constraints agree.

**meshio 5.3.5's MSH 4.1 writer gets entity bookkeeping wrong in two ways, both silent [tested: pending].**

- *One cell block is one entity.* `_write_elements` takes the **first** `gmsh:geometrical` tag of a
  block and writes the whole block under it. Four boundary groups packed into a single `line` block
  come back with all four physical tags equal to the first — three no-flux walls silently becoming
  one. Cure: emit one cell block per (group, element type).
- *An entity that owns no node is never written.* `_write_entities` builds `$Entities` from
  `np.unique(point_data["gmsh:dim_tags"])` alone, so an entity a cell block references but no node
  claims is omitted, and reading the file back raises `KeyError` — after the write reported success.
  Cure: assign each node its lowest-dimensional entity, then repair any group left with none.

**Netgen's mesh tables mix 1-based and 0-based indices [tested: pending].** Through `ngsolve.Mesh.ngmesh`,
`el.vertices[i].nr`, `Element2D.index` (into `GetMaterial`) and `Element1D.index` (into
`GetBCName(index - 1)`) are 1-based, and `FaceDescriptor.SetBCName` is 0-based. Mixing the two shifts every
boundary name by one (`wall` becomes the axis) and nothing raises. Names survive an OCC boolean and a
glue, so naming an embedded body's edges before the chain of position-based names leaves them alone.
When every boundary node is shared by two groups (a closed loop of named edges), a greedy choice of one
node per entity can fail; choose the representatives by bipartite matching with augmenting paths, then
give each leftover node its lowest-dimensional entity, as gmsh does. Source: `mesh/adapter.py`
(`from_ngsolve`, `to_ngsolve`, `_node_entities`), `mesh/primitives.py` (`name_edges`).

**`meshio.Mesh.field_data` is keyed by name, so it cannot carry the same name in two dimensions
[tested: pending].** The §5.3.1 vocabulary uses `cis`, `trans`, `membrane` and `analyte` as both a domain name
and a boundary name, which is exactly the collision. Read `$PhysicalNames` off the file and key it
`(dimension, tag)` instead.

**A round trip through MSH 4.1 permutes both nodes and cells [tested: pending]**, because meshio's reader
returns nodes grouped by entity and cell blocks in entity order. A content hash taken over the arrays
in file order would therefore make a mesh differ from itself. Hash a canonical form: vertices sorted
by `(r, z)`, connectivity renumbered into that order, elements sorted by group name — invariant under
everything the round trip does, and changing the moment an edge moves group.

**`meshio.read` on a `.msh` file prints an empty line to standard output unless told the format
[tested: pending].** meshio 5.3.5 maps the `.msh` suffix to both `ansys` and `gmsh`, tries `ansys` first, and
`print`s that reader's `ReadError` — whose text is empty — before falling through to `gmsh`. Found by
WP16 (23 September 2026) when a CLI test asserted that a refused `nanopnp mesh` wrote nothing to
stdout; every `nanopnp run` on an MSH case had been writing the same stray line, which a caller
parsing the IF-02 result stream would read. Pass `file_format="gmsh"`.

**netgen.occ facts, all measured on 6.2.2606 [tested: pending]:**

- **A clockwise wire gives OCC a face of negative area, and a negative face subtracts as an
  addition.** With the delivered ClyA table's own orientation (signed area −26.4939 nm²),
  `disc - quad` returns the disc split in two rather than the disc with a hole, and `quad * disc`
  returns nothing at all. Fix the orientation once, where the face is built.
- **`Glue` is conformal and `Compound` is not.** `occ.Glue([a, b])` meshes with one node chain per
  seam; `occ.Compound([a, b])` meshes with two coincident chains. On two unit rectangles sharing
  the edge `x = 1`, meshed at `maxh = 0.5`: glue gives 13 points, 13 of them distinct, 3 on the seam;
  compound gives 16 points, still 13 distinct, 6 on the seam. Two chains agree to the last digit on
  coordinates, so only a mesh-level check catches it, and what it costs is a potential free to jump
  across the seam with nothing raising.
- **`edge.center` is the centre of mass, and for an arc it lies off the curve.** A
  classify-by-centre chain works for straight edges and silently misplaces every curved one. Use
  `edge.parameter_interval` with `edge.Value(t)` to get a point that is actually on the edge.
- **`edge.faces` is empty.** Traversal is downward only, so an edge cannot be named by which faces
  adjoin it; classify by geometry instead.
  **The other direction works** **[tested: pending]** (WP21, netgen 6.2.2606): a shape hashes and compares
  equal to the same topological entity reached another way, so `set(face.edges)` per named face
  after a `Glue` gives each edge's adjacency by membership. A seam shared by two faces is in both
  sets, and `set(shape.edges)` removes the per-face duplicates (383 listed edges become 195 on the
  ClyA region). Stage 5 names every edge this way: `protein` with `membrane` is `interface`,
  `protein` with `electrolyte` is `wall`, `membrane` with `electrolyte` is `membrane`. Geometry is
  left to the two tests adjacency cannot make, `r = 0` and the reservoir arc.
- **`Circle(...).Face()` is one closed edge with a seam at parameter zero**, and the seam survives
  a boolean clip as an ordinary vertex. A half-disc of radius 250 clipped to `r ≥ 0` carries a vertex
  at `(250, 0)` that splits whatever arc segment spans it.
- **A boolean on shapes returns a compound.** `.mass` and `.name` on the result raise
  `NgException: Cannot query properties of compound shapes`; read them off `list(shape.faces)[0]`.
- **The mesh netgen generates is not bit-reproducible across platforms.**
  `CylindricalPoreGeometry(2.0, 13.0, 50.0)` at `maxh = 2.0 nm`, `wall_h = 0.05 nm` meshes to
  **8141 triangles on Linux and macOS and 8147 on Windows** — same version, same options, a drift
  of 0.07 %. The advancing front takes its decisions on floating-point comparisons, and the
  compiler decides those. So an element count, or a minimum element quality read to four decimals,
  is a property of the *build* and not of the geometry: assert a band on either, and keep exact
  check values for figures computed in closed form on hand-built elements. The three smaller
  phase-0 geometries (192, 811 and 124 elements) do agree exactly across all three platforms,
  which is what makes this easy to miss until a mesh is large enough to have a choice to make.

**Gmsh facts, measured on 4.15.2 with netgen 6.2.2606, Linux (WSL2), 29 September 2026 [tested: pending]**
(WP23; the implementation is `mesh/gmsh_backend.py`, the evidence the WP23 plan's Design and
Outcomes):

- **`gmsh.initialize()` from Python turns the terminal on.** `General.Terminal` reads 1 straight
  after it, so meshing writes Gmsh's progress to standard output, which IF-02 reserves. Set it to 0
  before anything else, and collect the messages with `gmsh.logger` instead. Pass
  `readConfigFiles=False` too, or a user's `~/.gmsh-options` changes a mesh under an unchanged key.
  Pass `interruptible=False`, because the default installs a SIGINT handler, which only the main
  thread may do.
- **A stage-5 region goes into the built-in `geo` kernel from netgen's own coordinates.** Reading
  `set(shape.vertices)`, `set(shape.edges)` and each face's `set(face.edges)` off the glued shape
  gives the graph: 193 vertices and 195 edges on the ClyA fixture. Its face areas, in closed form
  (Green's theorem, `½(a × b)` per segment and `½R²Δθ` per arc), agree with OCC's `face.mass` to
  1e-15 on the electrolyte and 1e-12 on the membrane. No BREP passes between netgen-occt and Gmsh's
  own OpenCASCADE. Every region vertex survives as a mesh node, the 185 profile vertices included.
- **The only curved edges are the reservoir arcs, and each spans less than π,** which
  `geo.addCircleArc` requires. OCC's seam at `(R, 0)` is what splits the membrane's outer arc in two.
  A straight edge is told from an arc by its parameter midpoint lying on its chord, to 1e-9.
- **A clockwise curve loop meshes every triangle of its surface inverted.** On the coarse
  parallelogram region, the protein's loop handed to Gmsh reversed gave 14 triangles, all 14
  inverted. Orient each loop counter-clockwise by its signed area before `addCurveLoop`, as the
  pore face is oriented for OCC above.
- **Given only §5.2.2's size table, Gmsh does not match netgen's quality.** Netgen limits the
  element size near short edges and close edges by itself, and grades outwards from a face's
  `maxh`. A Gmsh `Constant` field does neither. On the fixture, with the table as `Distance` and
  `Threshold` sources and `Constant` domains, the minimum gamma is 0.3143 against VER-10's 0.3.
  With the domain boundaries also as graded sources it fails at `size_scale` 2 (0.2084, beside a
  0.0412 nm profile edge) and at 4 (0.2348, where the 2.8 nm membrane strip meets the arc). The
  field the backend uses fixes that: sources `h + 0.2 d` on every sized boundary and domain
  boundary, on each vertex whose shortest curve is shorter than its curves' smallest target, and on
  the membrane at its unscaled thickness. Its minimum gamma is 0.5840, 0.5241, 0.5655 and 0.5072
  at `size_scale` 1, 2, 4 and 8. `Mesh.MeshSizeExtendFromBoundary` 1 is the tempting shortcut. It
  doubles the element count, to 95,103 at `size_scale` 1, and still gives only 0.3876 at 4.
- **Frontal-Delaunay (`Mesh.Algorithm` 6) is the algorithm, and one thread makes the mesh
  reproducible.** With the table-only field, algorithm 5 gives 10 % more triangles at a mean gamma
  of 0.95 against 0.99, and MeshAdapt (1) is slower and worse (WP23 plan, Design §3). `Mesh.Smoothing`
  5 is its optimisation pass, as `optsteps2d` is netgen's. With `General.NumThreads` and
  `Mesh.MaxNumThreads2D` at 1, two fresh processes give one content hash.
- **Gmsh's wall runs at or under its target, and netgen's over it.** With the backend's field on the
  fixture, the mean `wall` segment is 0.909, 0.931 and 0.945 of the target at 0.05, 0.03505 and
  0.02715 nm, and the longest is 1.029–1.055 of it. Netgen's mean is 1.045–1.078. The mesh has
  48,941 triangles in 3.3–4.2 s, against netgen's 44,316 in 6.4–7.0 s.
- **`Distance`'s sampling option is `Sampling`** (formerly `NumPointsPerCurve`). A source curve
  needs about `⌈L/h⌉` samples, so a reservoir arc hundreds of nm long, sized at 5 nm, needs 80 or
  more, where the default is 20.
- **The wheel can install and still fail to import.** On a bare Linux container `import gmsh`
  raises `OSError: libGLU.so.1`, not `ImportError`. A dispatch that turns a missing extra into a
  refusal has to catch both, as `tests/conftest.py`'s `import_gmsh` does for the tests.
- **On `ubuntu-latest`, four packages make it import [tested: pending].** GitHub's image lacks
  `libGLU.so.1`. After `apt-get install --no-install-recommends libglu1-mesa libxft2 libxinerama1
  libxcursor1`, Gmsh 4.15 imports and meshes on Python 3.11 to 3.14 (WP23 PR, run 36574260470,
  29 September 2026).
- **Session cleanup and borrowed sessions [tested: pending].** `gmsh_backend._session` records each undo step (`gmsh.model.remove()`, restoring options, `gmsh.finalize()`) only once the change it reverses has been made, and runs every recorded step in reverse order, so a session it opened is finalised even when an intermediate step or the setup itself fails, and a borrowed session's own model is never removed in place of one that was never added. When an exception is active during cleanup, secondary failures are logged at WARNING and attached to the exception via `add_note()`, preventing the original error from being masked (REV-38). A borrowed session (`gmsh.isInitialized()` true on entry) leaves the caller's logger untouched (no `start` or `stop`), preserving caller messages (REV-36). If `gmsh.initialize()` fails, a `GmshInitialisationError` is raised, translated to `MissingExtraError` naming `gmsh` (REV-37).
- **The IF-07 export samples a fluid-restricted field through a whole-domain carrier [tested: pending].**
  Point evaluation of a space built with `definedon=fluid` returns zero at an interface node whose
  point search lands in a membrane element. On the coarse four-material pore that is 16 of the 208
  fluid nodes, with a maximum error of 13.0 against a linear test function. Interpolating into a
  whole-domain space of the same order first and evaluating that is exact to 5.5e-14, because a P2
  node's value depends only on the entities carrying it, each a fluid entity (`post/export.py`
  `sample_at`).
- **meshio 5.3.5 reads an XDMF `Information` element only in its own `field_data` encoding
  [tested: pending].** Children carry `key` and `dim` attributes with integer text; anything else raises
  `ParseError`. The IF-07 scale set is therefore written as HDF5 root attributes (`post/export.py`).
- **Discontinuous export fields are cell-centred [tested: tests/tier1/test_field_export.py::test_if07_a_discontinuous_quantity_is_written_cell_centred].** `material_id` and `eps_r` jump across
  a material interface, so a node value there is one side chosen arbitrarily and a viewer draws a
  ramp across every boundary element; a barycentre lies strictly inside its element, so the point
  search is unambiguous.

---

