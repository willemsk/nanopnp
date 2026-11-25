---
type: Test Evidence
title: "The channel's axis of 2WCD against its ring axis"
description: What the channel-axis method measures on chains A–L of 2WCD, the two limits that rest on it, and where the method is known to be weak.
tags:
- clya
- structure
- test-evidence
sources:
- id: wp5.16-plan
  resource: docs/plans/phase-5/wp5.16-the-molecular-suite.md
  title: WP5.16 plan, D2 and its Outcome
- id: wp6.06-plan
  resource: docs/plans/phase-6/wp6.06-the-channel-axis-at-a-ragged-rim.md
  title: WP6.06 plan, the Grounding of D1 to D7 and item 1's Outcome
generated:
  by: claude-code/0.6.0-alpha.15
---

# The channel's axis of 2WCD against its ring axis

Stage 1 finds a pore's axis two ways: from the ring of chains (FR-02) and, under C1 or on request, from the channel's
empty space (`structure/cavity.py`; §5.2's NOTE on stage 1 states the method). 2WCD's dodecamer has both, so it measures
one against the other.

- On the prepared copy of chains A–L (tilted 4°, 26,844 heavy atoms) the channel's axis lies **0.0073 nm** from the
  ring's axis over the Cα axial extent, tilted 0.042° from it and 0.0095 nm aside at the foot. Each of the 28 planes
  holds a centre, the farthest **0.0148 nm** from the fitted line, and the line is fixed after 3 iterations.
  **[tested: tests/tier1/test_structure_stage.py::test_ver48_2wcd_channel_axis_agrees_with_its_ring_axis]**
- The two limits are twice these: `axis: z` is admitted within 0.015 nm of the channel's axis, which refuses it beyond,
  and a centre more than 0.03 nm from the line is warned of and does not refuse the axis (the author's ruling on
  REV-239, 11 November 2026). Both rest on this one pore, which is nearly C12 (the ring's permutation RMSD is
  0.026 nm).
- Under an exact Cₙ the method returns the axis to rounding, from a start 8° or 35° off it.
  **[tested: tests/tier1/test_structure_axis.py::test_ver48_the_channel_axis_recovers_a_known_axis]**
- A candidate centre is a point where a plane cuts a Voronoi edge. The Voronoi vertices alone do not serve: along a
  lumen 3 nm in radius they lie 0.5 to 1.5 nm apart on the axis, so 12 of 2WCD's 28 slabs held none and took a void of
  the wall. **[verified][^wp516]**
- Atoms on one sphere, as the n images of an atom are, triangulate into tetrahedra some of which are flat; a flat one
  takes its neighbour's centre, or the on-axis Voronoi edges are cut. **[verified][^wp516]**
- Before v0.7.0-alpha.6, which line the iteration held at a ragged rim was decided by rounding. The 8-fold test wall
  tilted 12° about x read 12.000° on Linux and 11.38° on Windows; on Linux a relative change of 1e-14 in the atoms'
  positions gave 11.381°, 11.446° or 11.780° for 3 of 8 draws. Without the rim the wall read 12.0000° in 19 of 19
  draws (REV-279). **[verified][^wp601]**
- The cause was not the tie between the rim's n equal spaces, as REV-279 first read it, but the diagram. Where the
  atoms of a rim lie exactly in one plane, many tetrahedra there are flat or have a centre that is not empty, and fix
  no centre; the code dropped the Voronoi edge of each face between such a tetrahedron and one that fixes a centre.
  The 8-fold wall tilted 12° has 50 such tetrahedra of 27,644; a draw at 1e-14 has 2,146 of 29,741, 1,161 of them
  wholly in the top rim plane. Its last plane then held no candidate within 0.36 nm of the axis, where without the
  draw it holds one on the axis at 2.018 nm clearance, and the first cut, 12° off, took one of eight spaces 0.364 nm
  aside. On walls tilted 12°, four draws at each of 1e-14, 1e-12 and 1e-10, the C7 and C8 walls locked in 17 of 24,
  the worst 0.84°; one further C8 draw read 1.05°. The C12 wall locked in none. **[verified][^wp606]**
- An edge now runs on past the hull and past a tetrahedron that fixes no centre, and a candidate is kept only where
  its clearance is its nearest atom's distance to a relative 1e-6, since such a ray can pass its edge's true end. None
  of the 24 draws locks, the worst 5.4e-11 rad, and none of 225 draws at 1e-14 over C7, C8 and C12 at 8°, 12° and
  35°, the worst 5.7e-14 rad. Two narrower rules fail: rays past flat tetrahedra alone still lock 14 of 18 draws at
  1e-12, and a tie weighted over 0.02 nm without the rays locks 11 of 21 C7 draws. On 2WCD the rule adds 182 rays and
  moves no bit of its axis, its centroid or its 28 centres.
  **[tested: tests/tier1/test_structure_axis.py::test_ver48_the_channel_axis_is_not_locked_by_rounding]**
  **[verified][^wp606]**
- Qhull refuses some draws for precision (`QH6417`, 2 of 360 trial walls, C7 at 8° and C8 at 35°). The atoms are then
  triangulated again with `QJ Qbb Qc Q12`, which gives the same simplices on every run, and both walls recover their
  axis to 1.7e-14 rad. `Qz` beside `QJ` leaves a simplex that indexes the point at infinity, so it is left out.
  **[tested: tests/tier1/test_structure_axis.py::test_ver48_a_refused_triangulation_is_joggled]**
  **[verified][^wp606]**
- A lumen with atoms on its axis is a weakness that remains. A wall with atoms 0.1 nm to 0.3 nm from its axis over its
  top 1 nm reads 7° to 8° off in 54 of 54 runs, before and after the fix, with a straightness of 0.46 nm to 0.54 nm,
  so the straightness warning fires (§8.2.39 AO4). A pore less regular than 2WCD may likewise be warned of for its
  straightness and refused by the `axis: z` budget (REV-239). **[verified][^wp606]**

[^wp516]: `docs/plans/phase-5/wp5.16-the-molecular-suite.md`, the Outcome under D2 (measured at item 2 on `tests/data/structures/2wcd.pdb.gz` and on synthetic walls).
[^wp601]: `docs/plans/phase-6/wp6.01-the-windows-leg.md`, item 1's Outcome and D9 (run 851's Windows leg; the perturbed walls measured at item 2).
[^wp606]: `docs/plans/phase-6/wp6.06-the-channel-axis-at-a-ragged-rim.md`, the Grounding of D1, D3, D4 and D7 (measured at `7ebfd4f` on SciPy 1.18.0 and NumPy 2.5.2, Linux) and item 1's Outcome.
