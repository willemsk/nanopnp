---
type: Specification
title: "5.2 Pipeline stages"
description: "Tabulates each pipeline stage with its inputs, outputs, tools and validation gate."
---

### 5.2 Pipeline stages

| # | Stage | Inputs | Outputs | Tools | Validation gate |
|---|---|---|---|---|---|
| 1 | Structure ingestion and alignment | PDB/mmCIF, optional trajectory, expected point group | Aligned ensemble; Cₙ axis on z at r = 0 | MDAnalysis 2.10+ (LGPLv3) for PDB and every trajectory format; gemmi 0.7+ (MPL-2.0) for mmCIF, which MDAnalysis 2.10 does not read; the Kabsch rotation for superposition, cross-checked against MDAnalysis `rotation_matrix`; MDTraj as alternative reader; PDBFixer or Modeller for missing loops | Oligomeric state matches (ClyA 12, αHL 7, MspA 8); abort on missing chains (FR-03) |
| 2 | Density map | Aligned ensemble, grid spacing, kernel | 3D density map | Vectorised numpy Gaussian deposition over a spherical stencil truncated at 10⁻⁶, per-atom width σR_i from the CHARMM radius set of the §5.3.1 NOTE on `geometry.density`, sharpness 0.93; `gridData` IO. MDAnalysis `DensityAnalysis` is histogram-only and is not used (WP19) | Grid spacing 0.25–0.5 Å (FR-04); every atom has a radius; the map is finite and within [0, 1] |
| 3 | Symmetry reduction to (r, z) | 3D map, n | (r, z) map; residual azimuthal variance, Cₙ-averaged and raw | numpy and `scipy.sparse`; exact cell–annulus overlap weights; the Cₙ average in the angular harmonic basis (WP19) | Variance emitted with the geometry (FR-06, CON-04); annular weights summing to the exact annulus areas. The radius profile against the probe-radius profile is stage 4's gate (§5.2.1, §8.2.2 B5) |
| 4 | Contour extraction and conditioning | Stage 3's (r, z) mean; the aligned ensemble and its radius set, for the probe-radius profile; isolevel, smoothing and simplification tolerance | Closed conditioned polyline, a `nanopnp/profile/v1` document | scikit-image, Shapely (both BSD-3) and numpy, per §5.2.1 (WP20) | §5.2.1 (FR-08) |
| 5 | CAD assembly | Stage 4's polyline or a supplied `inputs.profile`, membrane specification with its `centre_z_nm` shift, reservoir radius, optional analyte | Fragmented (r, z) region, domains and boundaries tagged, as a declarative region record | `netgen.occ` (LGPL-2.1, OpenCASCADE, in-process). The optional Gmsh backend meshes this region at stage 6 and assembles none of its own (WP23 D1) | All bodies fragmented and imprinted, interfaces conformal, no gap or overlap at the membrane-to-pore junction, each domain one face, the membrane's inner edge strictly inside the body (FR-09, WP21; §5.2.1 NOTE on the membrane junction on any profile) |
| 6 | Meshing | Fragmented region, size fields | Graded triangular mesh | Netgen (LGPL-2.1) default, Gmsh (GPLv2+) optional, behind the mesh adapter | §5.2.2 (FR-10, QR-12): the VER-10 and VER-27 gates, as on an ingested mesh, and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` (WP21) |
| 7 | Protonation (`protonation`) | Stage 1's aligned ensemble, pH, force field, titration method; or a supplied `inputs.pqr` | Per-frame atom table in stage 1's frame (identity, coordinates, charge, radius), `Q_net` and every titratable residue's state per frame | PDB2PQR 3.7+ (BSD-3) driving PROPKA 3 (LGPL-2.1), one call per frame with the flags of PHY-16 step 3 (WP27) | Every atom carries a charge and a radius, and every charged atom a positive radius; `Q_net` an integer to 10⁻⁶ e on every frame; a supplied frame registered to its stage-1 frame to 0.01 Å (§5.3.1 NOTE on `inputs:`) |
| 7 | Charge assembly (`charge`) | The protonation artefact, **and the deployed mesh** (its gate is evaluated there, PHY-19); on the consumer path, a supplied field document instead | ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface | The closed-form azimuthal kernel deposited on the deployed mesh (PHY-16, §8.2.4 D2); APBS 3.4.1 (BSD-3) cross-check through the test-only `apbs-binary` package; settings per PHY-16 | Charge conservation to 10⁻³ of Q_net on the deployed FE mesh, plus the per-z-slice cumulative check (FR-14, QR-03, PHY-19) |
| 8 | Materials | Electrolyte specification, correction model names, coefficient files | D_i, μ_i, η, ϱ, ε_r as fields in ⟨c⟩ and d | Correction registry, `data/corrections/willems2020_nacl.yaml` | Conformance values of §4.3 reproduced; clamps above 5.3 M logged with location and property (PHY-13) |
| 9 | Case assembly | Mesh, charge and dielectric fields, materials, boundary conditions, bias, analyte, numerics | Resolved case document, assembled discrete problem | `io/` schema validator, `physics/` model registry | Schema 'nanopnp/case/v0.5' validates, unknown keys rejected with a diagnostic naming the key (IF-03); round trip semantically identical (FR-26) |
| 10 | Solve | Assembled problem, continuation ladder, optional warm start | Converged fields, iteration history | NGSolve 6.2.2606+ (LGPL-2.1), damped Newton; UMFPACK (GPL-2+) or scipy SuperLU (BSD) (CON-08) | No negative concentration at any nonlinear iterate; ladder completed to the target rung (FR-17); §6.5, §6.6 govern |
| 11 | QoI extraction | Converged fields | I, t₊, RR, EOF rate, F^em(z), F^hd(z), ΔU(z) | Domain/indicator form and variational reaction flux, both implemented | The two routes agree within the stated tolerance, checked in CI (FR-23, QR-04); §6.7 governs |
| 12 | Reporting and export | Results, artefact hashes, environment | Figures, XDMF/HDF5 fields, dataset, case file, manifest | `io/`, `sweep/` result store | Manifest complete and sufficient to reconstruct the run (FR-25, QR-08) |

Design notes, recorded where an implementer would otherwise choose wrongly.

| Stage | Note |
|---|---|
| 1 | The Cₙ axis comes from chain-permutation superposition: superpose chain A onto chain B, take the rotation's eigenvector of eigenvalue 1 (FR-02). Principal axes are unusable because they drift between frames. Over the 98 frames of the ClyA-AS ensemble, the largest-variance axis of the Cα set moved by up to 1.54° (rms 0.66°), while the chain-permutation axis moved by at most 0.010°. The cause is not degeneracy: the axial eigenvalue is well separated (1432 Å² against 801 and 881 Å² on the first frame). It is the chains' asymmetric fluctuation, which the permutation fit averages out by construction (measured; WP18 plan, Design §4). Stage 1 is specified in full in the §5.3.1 NOTE on `structure:`. |
| 2 | Histogram plus uniform `gaussian_filter` is rejected: van der Waals-weighted smearing preserves the exclusion surface, uniform post-smoothing rounds the constriction. The grid is not coarsened, the *trans* constriction being about 3.3 nm across with a contour position that moves measurably with resolution. |
| 3 | The n rotated copies are averaged before azimuthal averaging. Binning is area-weighted over exact annular volumes (about 6 cells per annulus of width h at r = h, about 630 at r = 5 nm, per slice at h = 0.05 nm). The overlap weights are exact, so no bin is interpolated (WP19 plan, Design §2–§3). The earlier "innermost 2–3 bins interpolated" compensated for centre-assigned binning, and against exact weights every interpolant tried was worse somewhere. The rotated copies are averaged in the angular harmonic basis, where the average keeps the harmonics m ≡ 0 (mod n): it is exact and costs one deposition. Depositing n rotated copies costs n, and rotating the voxel map by interpolation smooths it, lowering the peak Cₙ variance of a C12 ring by 3–6 %. The binned mean is subtracted at each cell's own radius before any variance is taken, or the radial gradient across a bin reads as azimuthal variance. A 1° axis error adds about 0.2 nm of apparent radius to a 3.3 nm constriction. |
| 3, 5 | The bilayer is absent from the density map. It is defined analytically in (r, z) over the hydrophobic belt and fragmented against the pore contour. |
| 5 | Reference geometry: reservoir half-disc R = 250 nm, membrane thickness 2.8 nm, `z_cis` = 12.25 nm, `z_trans` = −1.85 nm. The membrane is a quadrilateral, not a rectangle: vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm, inner edge slanted to meet the pore's outer surface. Code assuming a rectangle leaves a wedge of gap or overlap at the junction. CadQuery and build123d are 3D-solid-centric and unused; pythonocc serves BRep edge cases only. |
| 7 | Stage 7 is two registered stages, `protonation` and then `charge`, sharing the number so that stages 8 to 12, which this specification, the CLI's output and every recorded manifest cite by number, do not move (WP27). The registry lists stages by number and then in registration order. A run walks `protonation` after `mesh` and immediately before `charge`, so a walk truncated at the mesh, as the desktop shell's geometry build is, never protonates; protonating an ensemble costs about a minute per frame of a ClyA dodecamer (WP27 plan, *Design* §1). Both halves run when the case has something to protonate (`structure:` or `inputs.pqr`, and no `inputs.charge`) and its model declares a fixed charge (§5.4.3), and are otherwise recorded as not run with the reason. A consumer of a deposited charge reads it from stage 7's artefact and from nowhere else (WP28). With a non-zero `charge.dielectric_transition_nm` the `charge` half also runs, reading stage 5's record, to derive `χ` (§4.4 NOTE on the derived solid fraction), whether or not it deposits a charge; the solve reads that `χ` from stage 7's artefact likewise (WP30). |

#### 5.2.1 Contour conditioning and its gate

Pipeline (WP20):

1. `find_contours` (sub-pixel marching squares, diagonal neighbours above the level joined) runs
   on stage 3's mean at the isolevel, default 0.25. Each point is placed by the grid's own axes,
   so bin j sits at its centre `r_j = j·h`.
2. The closed contours are assembled into the region above the isolevel. A contour left open at the
   grid's edge is refused.
3. The region is closed, then opened, by a disc of radius 2h, with h the density grid spacing.
   Every hole left is filled and recorded, and exactly one component is admitted.
4. The loop is resampled at uniform arc length h/2 and smoothed by Taubin λ|μ, which preserves the
   area where Laplacian and Chaikin smoothing shrink it.
5. Shapely `simplify` (Douglas–Peucker, topology preserved) runs at `simplify_tol_nm`, default
   0.02 nm, which must be below h.
6. Vertices are removed until no edge is shorter than `h_c`.
7. An optional periodic B-spline fit is not implemented.

The constants are recorded in the WP20 plan, D4–D9. They key the stage-4 artefact and are not case
keys.

| Gate criterion | Threshold |
|---|---|
| `LinearRing.is_valid`, `is_simple` | both true |
| Minimum vertex spacing | ≥ `h_c` |
| Minimum local feature size, measured two edges either side of each vertex | > 2 `h_c` |
| Loop topology | one component after the closing and opening, with no contour open at the grid's edge, holes filled and recorded, and the loop clear of the axis by `h_c` |
| Radius profile | `−h_c ≤ r_c(z) − R_p(z) ≤ 1.5 nm` on every mid-plane between z nodes that crosses the loop. `r_c` is the loop's innermost crossing, and `R_p` the frame-mean radius of the largest sphere centred on the axis that clears every atom's radius in the aligned structure. HOLE is an optional cross-check (§8.2.2 B5) |

Rationale (feature size): near-tangential self-approaches at the constriction generate slivers the
mesher cannot repair.

NOTE (the contour's size target, WP20): `h_c`, the "target element
size" of the criteria above, is the density grid spacing h, 0.05 nm by default. It is not the
stage-6 wall size. NUM-30's `λ_D/5` is 0.27 nm at 0.05 M: read as the target, it would make the
contour depend on the electrolyte concentration, and at 0.05 M erase the lumen's corrugation.
Step 3's radius is set by the margin the feature-size criterion needs. Simplification moves each
wall by up to its tolerance, so the gap left by a closing of radius δ stays above `2h_c` only if
`δ > h + simplify_tol_nm`, and 2h meets that for every admitted tolerance. The gaps and fins it
removes, under 0.2 nm at the default grid, admit no water molecule and are thinner than one heavy
atom. Step 3 automates the "manual removal of overlapping and superfluous vertices" that the source
work records. On the ClyA-AS ensemble, a closing of radius h leaves a groove that fails the
criterion at 0.058 nm, and 2h passes it at 0.229 nm (WP20 plan, Design §2 and §4).

NOTE (the radius band, WP20): the lower bound is geometric. Inside
the axis-centred sphere every atom is at least its own radius away, so the 25 % contour of the
azimuthal mean can enter that sphere by at most a fraction of an atom's width. The upper bound is a
gross-error check on the lumen's corrugation. `r_c − R_p` measures between +0.061 and +0.908 nm
on 2WCD (chains A–L), and between +0.173 and +0.869 nm on the ClyA-AS ensemble. The band does not
detect a radial scale error of a few per cent; VAL-05 does (WP20 plan, Design §5).

The reference pore boundary is published in the COMSOL model report as a closed 190-vertex polygon
(r ≈ 1.65–5.66 nm, z from −1.85 to 12.25 nm). The author's delivered tabulation of that boundary
SHALL be shipped as the regression fixture (§7.2), so solver work proceeds on the reference polygon
without the contour pipeline. The table is held in
the repository as `data/geometry/clya_as_radial_geometry.csv`, supplied by the reference model's
author: 185 `r,z` pairs in nm tracing a simple closed loop, r ∈ [1.65, 5.66], z ∈ [−1.85, 12.25],
enclosing 26.4939 nm².

NOTE (the membrane junction): the membrane's slanted inner edge, (2, −1.4) → (3.5, +1.4), lies
strictly **inside** the pore body along its whole length. At z = −1.4 the pore spans
r ∈ [1.725, 2.7524] and the edge enters at 2.0 — 0.275 nm clear of the lumen wall and 0.752 nm clear
of the outer surface; at z = +1.4 the pore spans r ∈ [2.96, 4.88] and the edge leaves at 3.5, with
0.540 and 1.380 nm of clearance. The assembled membrane is therefore the quadrilateral **minus** the
pore body, and it meets the pore on the pore's own outer surface, not on the drawn edge. The slant is
necessary rather than cosmetic: the lumen wall passes through (2.0, 0) exactly and has opened to
r = 2.96 by z = +1.4, so a vertical inner edge at r = 2 would place membrane material inside the
electrolyte for every z > 0. The cap's underside is re-entrant, so the membrane also fills a cleft
beneath it and its boundary is not monotone in z; it remains one connected domain, which is what
makes the reported domain count come out at three — pore body, membrane, and a single electrolyte,
the lumen joining the two reservoirs.

NOTE (the membrane junction on any profile, stage 5, FR-09; WP21): the
profile is first moved into the model frame, `z ← z − geometry.membrane.centre_z_nm`. On each plane
`z = ±t/2` the **lumen-adjacent body interval** `[r₁, r₂]` is bounded by the profile's two
smallest crossings of that plane, an edge crossing it when `lower ≤ z < upper`. Where an edge of
the profile lies exactly on the plane, `r₂` runs on to that edge's far end, because the body's
section continues along it and the membrane meets the body there (CODE_REVIEW_003 CR-4; without it a valid step flush with a bilayer plane was refused by the
junction criterion below). The inner edge of the membrane quadrilateral is the chord from
the lower plane's interval to the upper plane's that has the largest minimum distance to the
profile. It is searched on the 63 × 63 interior points `r₁ + (r₂ − r₁)k/64` of the two intervals.
Any chord with its ends in those intervals that lies inside the body yields the same region: a
fluid pocket between two such chords would be enclosed by them, by the body and by the plane
segments between their ends, which are body too, while the complement of a simple polygon is
connected. The widest-margin chord is taken because it is the choice furthest from failure. The
chord between the intervals' mid-points is **not** admissible in general. On the delivered fixture
it runs from (2.2387, −1.4) to (3.92, +1.4) and crosses the cleft under the cap between
(3.070, −0.016) and (3.235, 0.260), which splits the electrolyte in two. On the fixture the
widest-margin chord is (1.982, 3.470) nm, with a clearance of 0.236 nm (WP21: the plan's prototype printed 3.464, a grid point the search does not visit). A plane
that crosses the profile more than twice always splits a domain, and the one-face criterion below
refuses it. The gap between the first two body intervals on the plane is a segment of fluid
bounded by body at both ends. The body arms on either side of it join above the plane or below
it, because the profile is one simple polygon. If they join above, the fluid over the gap is
enclosed by body and the gap, and is a second electrolyte face. If they join below, the pocket
under the gap is enclosed alike: bilayer where it lies in the slab, a second membrane face, and
electrolyte where it reaches past the other plane (WP21 Outcomes, [verified]). Stage 5 SHALL abort,
naming the criterion, the measured value, the threshold and the (r, z), on any of these:

- a plane crossing the profile fewer than twice, with the profile's model-frame z extent and
  `centre_z_nm` named;
- a best chord closer than 0.01 nm to the profile, so that the membrane is not representable as a
  quadrilateral with a slanted inner edge;
- a domain assembled as other than one face, with each face's centroid and area named;
- a profile vertex not strictly inside the reservoir disc;
- a membrane whose innermost radius on either plane differs from that plane's `r₂` by more than
  the fragmentation tolerance.

The last criterion is VER-28's junction measure, made generic. The shipped reference geometry keeps
its drawn corners (2.0, 3.5), and its mesh is unchanged. The fixture assembled with either chord
meshes to one connectivity, with vertices within 4.2 × 10⁻⁹ nm (WP21 plan, Design §1).

NOTE (the ion-exclusion shell, stage 5, FR-15, PHY-20; WP30): a non-zero
`charge.exclusion_offset_nm`, `a`, makes stage 5 build the exclusion contour from the model-frame
profile `P`, with `h_c` as in the NOTE on the contour's size target:

1. `O` is the dilation of `P` by `a`, with round joins at 8 segments per quarter circle (WP20 D5).
2. `O` is closed by a disc of radius `2h_c`, as in step 3 of §5.2.1 and for the same reason.
3. Every hole of `O` is filled and recorded with its centroid and area. A hole is fluid enclosed by
   the shell, which no ion can reach.
4. `O`'s ring is resampled at uniform arc length `L/⌊L/(1.05 h_c)⌋`, and step 6 of §5.2.1 runs on
   it (WP30 Outcomes; see below).
5. §5.2.1's validity, simplicity and spacing criteria are applied to that ring, together with its
   clearance of `h_c` from the axis.

The shell is `O − P − M` and the electrolyte is `D − M − O`, where `M` is the membrane quadrilateral
and `D` is the reservoir disc. The membrane, its chord and its junction are unchanged. The shell
SHALL be one face. It runs from the membrane's upper face round the cap, down the lumen, and round
the *trans* end to the membrane's lower face. Its outer surface, against the electrolyte, is `wall`.
The no-slip surface, the no-flux surface and the PHY-02 distance source therefore move there, with
no change to `numerics.wall_distance.sources`. The shell's seams with the protein and with the
membrane are `interface`. The outer surface lies at most `max(h_c²/a, a/100)` inside the exact
offset (0.01 nm at `a` = 0.25 nm), and stage 5 gates that on every edge of the ring. Away from the
closing and the filled holes it never lies more than 10⁻⁶ nm outside the exact offset (WP30 plan,
*Design* §2). The `exclusion` domain is meshed at the wall size. On netgen, each `wall` edge of the
shell, of length `L`, is cut into `n = ⌈L/(1.1 h_wall)⌉` equal segments by a size of `L/n` where
`n > 1`, and keeps `h_wall` where `n = 1`; Gmsh needs no such rule (WP30 review; see below).

The resampling of step 4 is what makes the bound hold, and its argument is this. A ring at least
`2πa > 4πh_c` long is cut into at least 11 arcs, so each chord `s` is below `1.15 h_c` and above
`h_c`, and step 6 removes nothing. A chord then lies at most `a(1 − cos(π/32)) + s²/(8a)` inside
the offset, the round join's own sagitta plus the chord's. That is at most 0.62 of the bound for
every `a` [verified], and measured 0.16–0.53 of it on four bodies and nine offsets from 0.11 to
2 nm [tested]. WP30 Outcomes. Without the resampling, the bound was
first argued as twice the sagitta of the longest chord, on the premise that step 6 leaves no
round-join chord longer than `2h_c`. That premise is false. At 8 segments a quarter circle's
chords are `aπ/16`, 0.049 nm at `a` = 0.25 nm, and step 6 merges runs of them into chords near
`3h_c`. The surface then reached 0.0106 nm inside the offset on a rectangle at `a` = 0.25 nm, which
the gate refused [tested]. The resampling length is held near `h_c` because netgen meshes an edge of
1.5 times its size target as one segment, which the wall-size gate refuses at the default wall
target of 0.05 nm [tested].

The same rounding is why stage 6 divides the shell's `wall` edges (WP30
review). Netgen must keep a node at each end of every ring edge, and given only `h_wall` it cuts an
edge into about `⌊L/h_wall + 0.4⌋` segments [tested]. With ring edges of 1.05–1.15 `h_c`, every wall
target a little under `L`, or under `L/2`, therefore left segments up to 1.6 times it. On 2WCD at
`a` = 0.25 nm the gate refused 0.045, 0.04, 0.035 and 0.0225 nm, which `auto` reaches between about
1.5 and 1.9 M and at 3 M, while 0.05, 0.03 and 0.0272 nm passed [tested]. A shell-free profile is
not affected: after step 6 its edges are long (2WCD's median is 0.22 nm), and it passed at every
one of those targets. `⌈L/(1.1 h_wall)⌉` fixes the count whatever netgen's rounding, so the
segments average at most 1.1 times the target, under the gate's 1.15. An edge needing one segment
keeps `h_wall`, so the mesh is unchanged wherever no edge needed dividing, as at the 0.05 nm default
on 2WCD. Gmsh already cuts each edge into `⌈L/h_wall⌉` segments, and passed at every target [tested].
Two alternatives were measured and set aside. The shell's outer surface as one spline through the
ring passed every target too, but bulges past `a + 10⁻⁶` nm between its vertices, and the `geo`
kernel of the Gmsh backend cannot reproduce OCC's curve. An exact OCC offset of the body cannot be
built through netgen's interface whenever the dilation encloses a pocket, which step 3 requires.

Stage 5 SHALL abort, naming the criterion, the value, the threshold and the (r, z), on any of these:

- an offset that comes within `h_c` of the axis and so closes the constriction, naming the z
  interval and the body's least radius over it;
- an offset vertex that is not strictly inside the reservoir disc;
- an edge of the outer surface closer to the body than `a − max(h_c²/a, a/100)`, naming its
  midpoint;
- a domain assembled as other than one face.

`0 < a ≤ 2h_c` SHALL be refused naming both keys. The shell is a face of width `a`, and §5.2.1's
feature-size criterion admits nothing narrower than `2h_c`. The construction reads Shapely, which
is in the `structure` extra. Without the extra, the case SHALL be refused naming the extra and the
key. The record carries the offset loop, so stage 6 rebuilds the region without Shapely. With
`a = 0` none of this NOTE runs, and the record, its key and the mesh are those of §5.2.1.

NOTE (vertex counts): the model report's geometry section records **190 vertices for the pore
polygon** and **3 domains, 198 boundaries and 196 vertices for the assembled region**. Earlier
revisions of this document attached the geometry-wide 196 to the pore boundary, and identified the
extra six as the membrane quadrilateral's own corners; both are corrected here against the delivered
table. Assembling as above, the region adds to the 190-vertex polygon: the two points where the
planes z = ±1.4 cut the pore's outer surface, each splitting a polygon edge (+2 vertices, +2 edges);
the membrane's two outer corners on the reservoir arc at r = √(250² − 1.4²) = 249.99608 nm (+2, +2);
and the arc's two endpoints on the axis at (0, ±250) (+2, +2). Closing the region takes six further
edges — the axis, the `cis` and `trans` arc segments, the `membrane_outer` arc between the corners,
and the membrane's two faces at z = ±1.4. That is 190 + 6 = **196 vertices** and
190 + 2 + 6 = **198 boundaries**, both as reported; Euler closes it, 196 − 198 + 4 = 2 over the three
domains and the unbounded face; and 196 is also the mesh's 196 vertex elements (§5.2.2), one per
geometry vertex.

The delivered table carries 185 vertices, five short of the report's 190, and — unlike the report's
polygon, which the count above requires to be cut at both planes — it already has a vertex exactly on
the cis plane at (4.88, +1.4), so under the same construction it assembles to 190 vertices and 192
boundaries (190 − 192 + 4 = 2 likewise). The difference is recorded, not reconciled: it changes
neither the geometry the table describes nor anything computed from it.

DECISION (the author): **the delivered 185-vertex table is the geometry of
record.** It is what the fixture ships, what `mesh/reference.py` assembles, and what VAL-05 and any
Tier-3 comparison cite. The model report's 190 stays recorded above as the count of the polygon
COMSOL held after its own import conditioning; no further reconciliation is sought, and the five
vertices are not chased. This settles which of two tabulations of one curve to use and touches
nothing the model report governs (`CLAUDE.md` §1.6) — not an equation, a correction or a fitted
parameter. OPN-05 is closed.

NOTE (what `nanopnp.mesh.reference` assembles): 193 vertices and 195 edges, three more of each than
the count above, and both deviations are deliberate. Two come from breaking the side on `r = 0` into
three collinear segments at the pore's axial extent: OCC keeps collinear segments as separate edges,
the pore polygon never touches the axis, and this is therefore the only way §5.2.2's 0.075 nm
"symmetry axis inside pore" can be applied as a size field at all. The third is the seam OCC places
at parameter zero on a closed circle, at (250, 0), which survives the clip to `r ≥ 0` and halves
`membrane_outer` into two arcs meeting there — a closed circle has a seam somewhere, and this one
costs one vertex element on the reservoir rim. The named edges are then 186 around the pore
(151 `wall`, 35 `interface`), 3 `axis`, 2 `membrane`, 2 `membrane_outer`, and one each of `cis` and
`trans`. VER-28 asserts these counts.

NOTE (the conditioning gate and a supplied fixture): the gate above applies to contours the FR-08
pipeline *produces*. The delivered reference polygon does not meet two of its criteria at the
reference wall size of 0.05 nm — minimum vertex spacing 0.0361 nm, with 10 of its 185 edges shorter
than that wall size, and minimum local feature size 0.0806 nm against a 0.1 nm threshold — and yet
it is what the reference mesh of §5.2.2 was built from, at that wall size, reaching minimum element
quality 0.6378. A supplied profile fixture is therefore NOT gated on those two criteria. It is gated
on validity, simplicity and loop topology, and its measured spacing and feature size are recorded in
its provenance block, so that a mesh size chosen against it can be checked rather than assumed.

#### 5.2.2 Meshing

The mesh resolves a Debye length of 0.18–1.4 nm against a 250 nm reservoir, a scale span of 10³,
without degenerate elements at the pore, membrane and reservoir triple junctions or at r = 0.
Near-wall target h₁ ≈ λ_D/5 (about 0.04 nm at 3 M), grading to 5–10 nm in the far reservoir,
expected size 5 × 10⁴ to 2 × 10⁵ cells.

Isotropic graded refinement is the default strategy (FR-10). The reference model reached the
published results with free triangular meshing, no boundary layers anywhere in the sequence, and
isotropic grading to 0.05 nm at the pore wall.

| Region | Max element | Min element | Curvature factor | Growth rate |
|---|---|---|---|---|
| Global ("Finer" preset) | 10 nm | 0.001 nm | 0.25 | 1.05 |
| Pore boundary | 0.05 nm | 0.001 nm | 0.25 | 1.05 |
| Pore domain ("Extremely fine") | 0.1 nm | 0.004 nm | 0.2 | — |
| Reservoir domain | 2.8 nm | 0.04 nm | — | 1.04 |
| Reservoir outer boundary | 5 nm | 0.025 nm | — | 1.25 |
| Symmetry axis inside pore | 0.075 nm | 0.04 nm | — | — |

That mesh has 120,917 triangles, 1,879 edge elements and 196 vertex elements, minimum element
quality 0.6378, average 0.9765, which set the target. Quality gate, enforced in code: minimum
SICN/gamma > 0.3, the mesher's own optimisation pass (netgen's `optsteps2d` 5, Gmsh's
`Mesh.Smoothing` 5; WP23 D5), worst element and its location
reported, run aborted on failure (QR-12).

NOTE (SICN and gamma): these are two distinct measures and both SHALL be gated. For a straight-sided
triangle, SICN is the signed inverse condition number of the Jacobian taken relative to the unit
equilateral element and gamma is the normalised inradius-to-circumradius ratio `2 r_in / R_circ`;
both equal 1 on the equilateral element and both are scale-invariant. They are not interchangeable:
on the isoceles family over a unit base, `SICN = 0.3` occurs at `gamma = 0.1298` and `gamma = 0.3` at
`SICN = 0.4687`, a factor of 1.6208 in element height (0.215508/0.132966), so a single
"SICN/gamma > 0.3" reading admits
two different meshes. Gamma is unsigned — an inverted equilateral element scores `gamma = 1` and
`SICN = −1` — so gamma alone cannot detect inversion, and `SICN ≤ 0` SHALL be reported as its own
failure ("inverted element") rather than folded into the quality gate. Under the axisymmetric
`r`-weighted forms an inverted element contributes negative volume and nothing else raises.

Anisotropic boundary layers are an optional element-count optimisation (FR-11, post-1.0), not a
dependency of the default path.

| Route | Mechanism and status |
|---|---|
| Geometric, in project code | Offset the conditioned contour inward by a geometric progression (Shapely `buffer(-d)` or `offset_curve`), mesh the strips as structured quads, let the unstructured mesher fill the interior; growth ratio 1.15–1.2 over about 15 layers. Preferred, deterministic. The legacy `parallel_offset` still works in Shapely 2.1.2 but is retained only for backwards compatibility and uses different sign and segment conventions |
| Mesher-native, Netgen | `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`, binding C++ `GenerateBoundaryLayer2`. Best-effort: an unresolved August 2024 NGSolve forum report has it failing to fill a zone adjacent to the new advancing front. The 3D `Mesh.BoundaryLayer` now unconditionally raises "Call syntax has changed! Pass a list of BoundaryLayerParameters to the GenerateMesh call instead" |
| Mesher-native, Gmsh | `BoundaryLayer`, `Distance`/`Threshold`, `Min`/`Restrict` size-field algebra, `Fan` points, quads-in-BL. Best-in-class, available only on the optional GPLv2+ backend |

Excluded components (CON-12): MeshPy, maintained at 2026.1 but wrapping Triangle, whose licence
permits distribution as part of a commercial system "ONLY BY DIRECT ARRANGEMENT WITH THE AUTHOR";
TetGen 1.5 (AGPLv3); pygmsh (2022-01) and pygalmesh (2022-09), both stale. The `gmsh` API is called
directly.

NOTE (the Gmsh backend's size field; FR-10, CON-10; WP23): the Gmsh
backend meshes the region stage 5 assembled, never one of its own. It applies the table above
through the classification netgen's sizes use. Gmsh has nothing like netgen's built-in restriction
of the element size by edge length and by the proximity of close edges. It does not grade outwards
from a domain's size either. Given the table alone it clears the quality gate on the reference
fixture at a minimum gamma of 0.3143 and fails it at `size_scale` 2 and 4 (WP23 plan, Design §2).
The backend therefore states those restrictions as size fields. Each is graded outwards as
`h + 0.2 d`, 0.2 being the constant netgen is given as its grading:

- every sized boundary (`wall`, the reservoir arc, the axis inside the pore) is a source at its
  size;
- the boundary of every sized domain is a source at the domain's size, the domain being held to
  that size inside;
- each vertex whose shortest incident curve is shorter than the smallest target of its incident
  curves is a source at that curve's length;
- the membrane is a sized domain at its own thickness, not multiplied by `size_scale`, because it is
  a feature of the geometry and not an entry of the table.

None of these touches a netgen mesh, which already meets them. On the fixture, the WP22 frozen case
gives conductances 1.25e-4 apart on the two backends' meshes at `size_scale` 2. Refining netgen to
`size_scale` 1 moves its own value by 2.0e-4 (WP23 plan, Design §4).

NOTE (an idealised pore's size field; FR-10, VER-62; §8.2.22 X1, X4; WP57): the table above sizes
a structure's region, whose protein and lumen it was set on. An idealised pore (§5.3.1, `geometry.pore`)
has neither, and stage 6 meshes it with netgen alone under two sizes: `numerics.mesh.maxh_nm`
(§5.2.2's global 10 nm where it is none) as the global maximum and the resolved wall size on `wall`,
each times `size_scale`, at netgen's grading 0.2 and three optimisation passes (`optsteps2d` 3),
with no other size and no other pass. That is the recipe of the earlier cylinder generator: on the
examples' pore (`radius_nm` 2, `thickness_nm` 6, `radius_nm` 10 for the reservoir, `maxh_nm` 4,
`wall_h_nm` 0.35) it gives the 392-element mesh VER-62's walks were recorded on, bit for bit, while
five passes keep the 392 elements and move every vertex (WP57 plan, Grounding). The quality gate
and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` apply as on any generated mesh; that
mesh's wall segments measure 1.071 × the target on average and 1.139 × at most. `nanopnp mesh` meshes
a geometry file by the same recipe (IF-02's generators NOTE), its `--maxh-nm` and `--wall-h-nm`
in the place of the two keys.

#### 5.2.3 Embedded analyte

| Approach | Verdict |
|---|---|
| Body-fitted remeshing per axial position: for each z_a, rebuild the (r, z) geometry with the analyte subtracted and remesh | Specified. In 2D a remesh takes seconds and the positions are embarrassingly parallel |
| ALE or moving mesh | Rejected: needed only for transient trajectories, and with analyte diameter comparable to pore diameter, distortion at the constriction forces a remesh regardless |
| Fictitious domain, immersed boundary or level set | Rejected: a diffuse interface cannot carry a sharp dielectric jump, zero ion flux and no-slip without degrading Debye-layer accuracy |

The analyte is a hard dielectric body with no ion flux, no-slip and a dielectric jump, as at the
pore wall (FR-21). Both charge models ship as named options, a surface charge density and a smeared
volumetric charge, sharing the smearing machinery of §4.4.
