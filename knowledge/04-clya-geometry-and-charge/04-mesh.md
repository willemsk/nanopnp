---
type: Pipeline
title: 4. Mesh
description: "The thesis states no mesh; the delivered polygon's spacing and feature size; the drawn membrane corners."
tags:
- clya
- pipeline
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_mesh_profile.py::test_the_delivered_table_has_the_published_properties
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_mesh_profile.py::test_the_local_feature_size_skips_the_vertexs_own_neighbourhood
  at: '2026-10-16T00:00:00Z'
---

## 4. Mesh

**Nothing is stated.** No element count, element type, element order, refinement rule, boundary-layer
strategy, or mesh-convergence study appears anywhere in ch. 6, ch. 6 SI, ch. 5 or ch. 5 SI **[verified][^thesis]**. The only
mesh reference besides the quality of the hand-edited contour (T L395-396) is "integration ... over the final mesh" (T L425-426) **[verified][^thesis]**.

**The delivered vertex table.** Its measurements (185 vertices, clockwise, extent, sha256, minimum
spacing 0.0361 nm, minimum local feature size 0.0806 nm) are in
`data/geometry/README.md` **[tested: tests/tier1/test_mesh_profile.py::test_the_delivered_table_has_the_published_properties]**,
and the gate that applies to a supplied fixture is the `SPECIFICATION.md` §5.2.1 NOTE on the
conditioning gate and a supplied fixture. Both minima lie below the thresholds the FR-08 contour
pipeline enforces, and the reference mesh was nevertheless built from this polygon at a 0.05 nm
wall size. The COMSOL model report's mesh is in
`knowledge/09-comsol-reference-settings/02-mesh-27.md`.

Measuring the local feature size needs a neighbourhood of **two edges either side**, not one: a
vertex is always within an edge length of the edge beyond its immediate neighbour, so excluding only
the two incident edges collapses the measure onto the shortest edge and reports 0.0361 nm — sampling
density — rather than 0.0806 nm, which is a feature **[tested: tests/tier1/test_mesh_profile.py::test_the_local_feature_size_skips_the_vertexs_own_neighbourhood]**.

The membrane's drawn inner corners, `(2.0, −1.4)` and `(3.5, +1.4)`, lie **0.275 and 0.540 nm inside
the pore body** on this table. The plane cuts on the pore's own outer surface are at **r = 2.7524 nm**
on `z = −1.4` and **r = 4.88 nm** on `z = +1.4`; the table already carries a vertex exactly at
`(4.88, +1.4)`. A junction gate written against the drawn corners asserts numbers the geometry never
produces.

---

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. T = `chapters/transport/transport.tex`, TA = `chapters/transport_appendix/transport_appendix.tex`, E = `chapters/electrostatics/electrostatics.tex`; `Lnnn` is the line in that commit.
