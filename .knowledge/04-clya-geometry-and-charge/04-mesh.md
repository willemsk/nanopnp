---
type: Pipeline
title: 4. Mesh
---

## 4. Mesh

**Nothing is stated.** No element count, element type, element order, refinement rule, boundary-layer
strategy, or mesh-convergence study appears anywhere in ch. 6, ch. 6 SI, ch. 5 or ch. 5 SI. The only
mesh reference is "integration ... over the final mesh" (T L425).

**Measured on the delivered vertex table [tested].** 185 vertices, traced **clockwise** (signed area
−26.4939 nm²), `r ∈ [1.65, 5.66]` nm, `z ∈ [−1.85, 12.25]` nm, sha256
`d0c2008140dc43d4cf7465d2c345f927a7b77110936f5d941976fc2122b0b386`. Minimum vertex spacing
**0.0361 nm**, on one edge; 10 of its 185 edges are shorter than the 0.05 nm reference wall size,
and 45 are shorter than 0.1 nm. Minimum local feature size **0.0806 nm**. Both minima are *below*
the conditioning thresholds the FR-08 contour pipeline enforces, and the reference mesh was
nevertheless built from this polygon at a 0.05 nm wall size and reached minimum element quality
0.6378 — which is why a *supplied* fixture is gated on validity, simplicity and loop topology but
not on spacing or feature size.

Measuring the local feature size needs a neighbourhood of **two edges either side**, not one: a
vertex is always within an edge length of the edge beyond its immediate neighbour, so excluding only
the two incident edges collapses the measure onto the shortest edge and reports 0.0361 nm — sampling
density — rather than 0.0806 nm, which is a feature.

The membrane's drawn inner corners, `(2.0, −1.4)` and `(3.5, +1.4)`, lie **0.275 and 0.540 nm inside
the pore body** on this table. The plane cuts on the pore's own outer surface are at **r = 2.7524 nm**
on `z = −1.4` and **r = 4.88 nm** on `z = +1.4`; the table already carries a vertex exactly at
`(4.88, +1.4)`. A junction gate written against the drawn corners asserts numbers the geometry never
produces.

