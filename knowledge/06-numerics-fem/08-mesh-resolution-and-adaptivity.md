---
type: Numerics
title: 8. Mesh resolution and adaptivity
description: Mesh resolution and adaptivity, measured against the reference mesh.
tags:
- numerics
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_mesh_quality.py::test_ver10_gmsh_agrees_on_the_magnitude_of_both_measures
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reference_geometry.py::test_ver10_the_reference_mesh_is_in_the_published_quality_band
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_region_reference.py::test_ver10_the_generated_mesh_matches_the_drawn_one_and_meets_the_band
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_region_reference.py::test_ver53_the_wall_gate_passes_at_both_measured_sizes
  at: '2026-10-16T00:00:00Z'
---

## 8. Mesh resolution and adaptivity

- First wall layer `h₁ ≈ λ_D/5` — 0.035 nm at 3 M. Geometric ratio 1.15–1.2 over ~15 layers,
  growing to 5–10 nm in the far reservoir. Expect 5 × 10⁴ – 2 × 10⁵ cells.
- **Compute the wall-distance field once per mesh and mollify it to C¹** (eikonal or
  screened-Poisson). `D`, `μ`, `η` all depend on `d`, so a kinked `d` propagates into the Jacobian.
- Goal-oriented (DWR) adaptivity on the current QoI: Becker & Rannacher, *Acta Numerica* **10**, 1
  (2001). Mitscha-Baude's economy — build the estimator from the **linear PB surrogate** rather
  than the full coupled adjoint — is heuristic but empirically retains the optimal O(h²) rate in
  the QoI at a fraction of the cost. Ship as an optional loop, not a v1 default.
- **The published results carry no discretisation error bar.** The *thesis* states only "COMSOL
  Multiphysics v5.4" and mentions "the final mesh" in passing: no element counts, no types, no
  refinement strategy, no tolerances, no convergence study. **[verified][^esi]** by grep over
  `thesis/chapters/`. Our mesh convergence study is therefore new work, and small disagreements
  with published numbers may be *their* discretisation error rather than ours.
  **Correction to the above, added later:** the paper's *ESI* is a 143-page COMSOL-generated model
  report that **does** contain a Mesh section (§2.7), Solver Configurations for both studies
  (§3.2, §4.3) and a "Mesh quality" results section (§5.4). Those numbers exist; they have not yet
  been extracted (`WebFetch` truncates the PDF at ~p. 66 of 143). Still no convergence study.
  → `knowledge/09-comsol-reference-settings/index.md`.

### Measured: the reference region meshes to a third of COMSOL's element count **[tested: tests/tier2/test_reference_geometry.py::test_ver10_the_reference_mesh_is_in_the_published_quality_band]** **[tested: tests/tier2/test_region_reference.py::test_ver10_the_generated_mesh_matches_the_drawn_one_and_meets_the_band]** {#measured-the-reference-region-meshes-to-a-third-of-comsols-element-count}

The ClyA region of §5.2.1 — the delivered 185-vertex profile, the membrane quadrilateral with its
slanted inner edge, a 250 nm reservoir half-disc, glued — meshed by netgen at the §5.2.2 size fields
(global 10 nm, pore boundary 0.05 nm, pore domain 0.1 nm, reservoir domain 2.8 nm, reservoir arc
5 nm, axis-in-pore 0.075 nm), `grading = 0.2`, `optsteps2d = 5`:

| | netgen, here | COMSOL, §5.2.2 |
|---|---|---|
| triangles | 44,316 | 120,917 |
| minimum element quality | 0.6559 (SICN), 0.6157 (gamma) | 0.6378 |
| mean element quality | 0.9870 (SICN) | 0.9765 |
| time | 6.5 s | — |

A third of the elements in the same quality band. The counts are *not* comparable as a convergence
statement — the two meshers' size fields are not the same knobs, and COMSOL's single "element
quality" is not stated to be SICN — but the quality band is, and it is met without boundary layers,
by isotropic grading alone, which is what §5.2.2 says the reference model did.

### Measured: the wall-size field reaches the wall, and a gate can tell **[tested: tests/tier2/test_region_reference.py::test_ver53_the_wall_gate_passes_at_both_measured_sizes]** {#measured-the-wall-size-field-reaches-the-wall-and-a-gate-can-tell}

Netgen treats a size as a target, not a bound. Stage 6 (WP21) measures the `wall` segment lengths
over the resolved target, at the §5.2.2 sizes otherwise; netgen 6.2.2606, Linux, 26 September 2026:

| Region | Target (nm) | Segments | Mean | p95 | Max | Triangles | Min SICN, gamma |
|---|---|---|---|---|---|---|---|
| Fixture | 0.05 | 569 | 1.045 | 1.200 | 1.600 | 44,316 | 0.6559, 0.6157 |
| Fixture | 0.03505 (3 M) | 792 | 1.071 | 1.194 | 1.614 | 48,986 | 0.7489, 0.6870 |
| Fixture | 0.02715 (5 M) | 1003 | 1.092 | 1.218 | 1.519 | 54,256 | 0.6414, 0.5671 |
| 2WCD, stage 4 | 0.05 | 582 | 1.062 | 1.233 | 1.485 | 44,688 | 0.7111, 0.6196 |
| 2WCD, stage 4 | 0.03505 (3 M) | 826 | 1.067 | 1.180 | 1.250 | 49,878 | 0.7335, 0.6470 |
| Fixture, **no wall field** | 0.05 | 301 | 1.976 | 2.691 | 3.200 | 38,908 | — |

The gate's bounds, mean ≤ 1.15 × and max ≤ 2.0 ×, sit above every row with the field and below
the row without it. Withheld, the protein domain's 0.1 nm field and the polygon's own edges govern,
and the mean doubles. The fixture meshes to the same 44,316 triangles through the derived chord as
through the drawn one. Stages 5 and 6 take 0.4–0.7 s and 6.9–9.8 s. **The minimum quality moves
with the target by more than the band's width** (0.6414 at 5 M against 0.7489 at 3 M), so a quality
check value belongs to one target, not to the geometry.

**The quality gate is cheap enough to run unconditionally**: ≈1.1 s on a 121k-element mesh, a
fraction of the time to build one. The measured margin on the geometries this project generates is
wide (minimum SICN 0.647 against a 0.3 floor), so gating only *imported* meshes would leave the ones
we build ourselves unwatched for no saving.

**`mesh/quality.py`'s SICN and gamma agree with `gmsh.model.mesh.getElementQualities(..., "minSICN")`
and `"gamma"` to every digit gmsh prints [tested: tests/tier1/test_mesh_quality.py::test_ver10_gmsh_agrees_on_the_magnitude_of_both_measures]**, which calibrates the 0.3 threshold against the
implementation that set it. gmsh returns `+1` for a clockwise triangle (a 2-D element in a discrete
entity has no intrinsic orientation there), so only the magnitude is comparable; the sign is ours.

**The gate's first run found a degenerate mesh, and the answer was not to weaken it.** VER-16's
Gouy-Chapman slab is 2000 nm × 0.5 nm meshed at 50 nm: a chain of 100:1 triangles at minimum SICN
0.019. That anisotropy is not a defect — the transverse extent is an artefact of solving a
one-dimensional problem on a two-dimensional mesh, and the stretched direction is the one the
solution is constant in, so those elements carry zero interpolation error rather than merely bounded
error. A gate that measures isotropy has nothing to say about such a mesh; the exemption belongs at
that call site, with its reasoning, not in the floor.

---

[^esi]: Electronic supplementary information of the paper.
