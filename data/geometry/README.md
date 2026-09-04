# Geometry fixtures

## `clya_as_radial_geometry.csv`

The ClyA-AS pore boundary in the `(r, z)` half-plane: `r,z` pairs in **nanometres**, one vertex per
line, in the order they trace the closed loop. The closing edge from the last vertex back to the
first is implied and is not repeated.

| Property | Value |
|---|---|
| Vertices | 185, no duplicates |
| Extent | `r ∈ [1.65, 5.66]` nm, `z ∈ [−1.85, 12.25]` nm |
| Topology | simple closed loop, no self-intersection |
| Orientation | clockwise in `(r, z)`; signed area −26.4939 nm² |
| Minimum vertex spacing | 0.0361 nm; 10 of the 185 edges are below 0.05 nm |
| Minimum local feature size | 0.0806 nm |
| sha256 | `d0c2008140dc43d4cf7465d2c345f927a7b77110936f5d941976fc2122b0b386` |

Supplied by the author of the reference model (Willems et al., *Nanoscale* **12**, 16775–16795,
2020) as the radial geometry behind `npgrid_clya_v8_NaCl_report.mph`. The extent matches the
published `z ∈ [−1.85, 12.25]`, `r ≈ 1.65–5.66` of `SPECIFICATION.md` §2.2 to the digit. The model
report records **190** vertices for the pore polygon against the 185 delivered here; the difference
is recorded rather than reconciled (§5.2.1 NOTE, OPN-05) and does not change the geometry this table
describes.

The file is kept **verbatim as delivered**, line endings included, so that the hash above identifies
the delivered artefact and not a reformatting of it. Nothing reads it at run time: `mesh/profile.py`
converts it once into the validated fixture the code loads (WP8).
