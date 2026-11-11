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
- The two limits are twice these: `axis: z` is admitted within 0.015 nm of the channel's axis, and a centre more than
  0.03 nm from the line refuses the axis. Both rest on this one pore, which is nearly C12 (the ring's permutation RMSD
  is 0.026 nm).
- Under an exact Cₙ the method returns the axis to rounding, from a start 8° or 35° off it.
  **[tested: tests/tier1/test_structure_axis.py::test_ver48_the_channel_axis_recovers_a_known_axis]**
- A candidate centre is a point where a plane cuts a Voronoi edge. The Voronoi vertices alone do not serve: along a
  lumen 3 nm in radius they lie 0.5 to 1.5 nm apart on the axis, so 12 of 2WCD's 28 slabs held none and took a void of
  the wall. **[verified][^wp516]**
- Atoms on one sphere, as the n images of an atom are, triangulate into tetrahedra some of which are flat; a flat one
  takes its neighbour's centre, or the on-axis Voronoi edges are cut. **[verified][^wp516]**
- Two weaknesses, both at a ragged rim or lumen. Where no atom lines the axis's side of a plane, its widest spaces are
  n equal ones off the axis; a line a little off the axis breaks their tie and can hold the iteration at a line about
  0.01 rad off. And one such centre, 0.26 nm aside on the test wall, exceeds the straightness limit. A pore less regular
  than 2WCD may therefore be refused (REV-239). **[verified][^wp516]**

[^wp516]: `docs/plans/phase-5/wp5.16-the-molecular-suite.md`, the Outcome under D2 (measured at item 2 on `tests/data/structures/2wcd.pdb.gz` and on synthetic walls).
