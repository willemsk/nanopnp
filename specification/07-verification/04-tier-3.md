---
type: Specification
title: "7.4 Tier 3 cross-implementation comparison"
description: "Specifies the Tier 3 cross-implementation comparison against the paper's published current–voltage relationships and in-pore averages."
---

### 7.4 Tier 3 cross-implementation comparison

This implementation is compared with the reference on what the paper publishes: the current–voltage
relationships and the in-pore averages of its ePNP-NS results (VAL-16, VAL-17), which gate v0.7, the Phase 6 release (§8.2.5 E2, §8.2.6 F1).
The reference numbers are the paper's tables, shipped as test data, and the data behind its
figures, which the author supplies under `NANOPNP_REFERENCE_DATA` (§8.2.4 D6). The second route, VAL-01 to VAL-04, a field-by-field comparison against exported COMSOL
solutions, runs wherever exports exist, but no release waits on it.

On the field route, frozen cases spanning the envelope are compared field by field against exported
COMSOL reference solutions (`φ`, `c_i`, `u`, `p`) on a common probe grid, together with all scalar
QoIs. Golden files are stored as compressed arrays with the generating model archived alongside.

Tight agreement is not expected at first: the reference uses a different discretisation (linear
velocity and pressure) on a mesh from a different generator, with streamline and crosswind
stabilisation active in both interfaces. Acceptance targets of better than 1 % relative L² error on
fields and 0.5 % on integrated quantities therefore apply only once the matching stabilised mode of
§6.4 exists and the meshes have been convergence-matched. Until both preconditions hold,
differences are recorded and attributed rather than gated on.

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-01** | Field comparison on the common probe grid | **Not required** (§8.2.4 D6); runs where exports exist. < 1 % relative L² error per field, once the preconditions above hold |
| **VAL-02** | Integrated-quantity comparison (`G`, `t₊`, `RR`, EOF rate) against the exports | **Not required** (§8.2.4 D6); VAL-16 compares the same quantities with the published results. < 0.5 % relative error, once the preconditions above hold |
| **VAL-03** | Reference-solution generation and archival, in Phase 1 | **Not required** (§8.2.4 D6), and not generated in Phase 1 (§8.2.3 C1); the harness ingests and refuses as below whenever a set arrives. Full reference set for the frozen cases archived with the generating model, independent of continued licence access, and **declaring** per field its source expression and its unit, and for the current its evaluation boundary and which electrode it references; a golden leaving any of those unstated is refused rather than interpreted. A golden's case identity names a fixed charge that stage 7 deposits by its stage-7 recipe: the stage-1 key's parameters, the protonation key's parameters without its gate tolerances, which move a verdict and never a charge, any input file's digest, and the kernel's parameters. It names a `χ` that stage 7 derives by its derivation parameters and the stage-1 key's parameters, and a non-zero `charge.exclusion_offset_nm` by the offset, because the ion-exclusion shell is a physics switch rather than a refinement of the geometry. Keys enter by their parameters, never their hashes, so an artefact schema string does not move an identity. A finished run's identity is read from the stage-1 and protonation artefacts the run recorded, never from the files its case names (§8.2.5 E3; OPN-07, closed) |
| **VAL-04** | Reference discretisation-error probe | **Not required** (§8.2.4 D6). The reference case re-solved at two refinement levels while licence access lasts, bounding the reference's own discretisation error |
| **VAL-05** | Geometry pipeline against the published boundary | Auto-generated contour compared against the delivered reference pore polygon (§5.2.1): radius profile and constriction radius within a stated tolerance. Measured on two inputs (§8.2.2 B2): the public 2WCD entry, gated at Tier 2 to a looser tolerance, and the author's ClyA-AS ensemble, archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3; the Phase 2 gate requires the ensemble leg. Each leg's metric, registration and tolerance are stated, with their argument, in the NOTE on VAL-05 below (WP22) |
| **VAL-06** | Poisson-only comparison against APBS | Potential from the assembled fixed-charge and dielectric fields agrees with an APBS solve on the same structure within a stated tolerance. Two legs (§8.2.4 D3). The **gated** leg gives APBS, at zero ionic strength, our assembled charge and solid fraction as 3D maps, so that only the two solvers differ. The **recorded** leg runs APBS from the PQR with its own charge assignment and molecular surface, which measures the azimuthal averaging of CON-04. APBS runs from the test-only `apbs-binary` package on every CI leg its wheels cover, so VAL-06 is gated at Tier 2 on 2WCD and skips visibly where no wheel exists; the ensemble is recorded at Tier 3. The tolerance is stated, with its argument, by the work package that implements it, before the comparison is run: ≤ 3 % max, ≤ 1 % rms and ≤ 1.5 % on the axis, within a refinement budget of half of each (WP29 plan; NOTE on VAL-06 below) |
| **VAL-15** | The reference model's own `rhoq_pore` table, on our mesh | The delivered table reads with the grid its header declares, its planar integral is the declared `Q_net` to better than 10⁻⁹, and its boundary ring is negligible against its interior, so the producer leg of §4.4 is exact and the reference's 1.25 % is the consumer's (OPN-06); the consumer leg on the reference mesh is recorded with the mesh it came from, and the quadrature-agreement gate refuses it, per cent-level, rather than reporting a conserved number it cannot defend |
| **VAL-16** | Current–voltage relationships against the published results | The ionic current, conductance `G`, rectification ratio, cation transport number and electro-osmotic flow rate agree with the paper's published ePNP-NS results within a stated tolerance, at the published concentrations and biases. Two legs, as for VAL-06. The **gated** leg solves on the reference inputs, the §5.2.1 geometry and the delivered `rhoq_pore` table, so that only the solver differs. The **recorded** leg solves on the geometry and charge that stages 1–7 generate from the author's ensemble. Gates v0.7, the Phase 6 release (§8.2.4 D6; §8.2.5 E2; §8.2.6 F1). The tolerance is stated, with its argument, by the work package that implements it, before the comparison is run |
| **VAL-17** | In-pore averages against the published results | The pore-averaged ion concentrations, the peak radially averaged equilibrium potential, and the mobile charge in the pore with its wall and bulk split agree with the paper's published values within a stated tolerance. The same two legs, reference sources and tolerance rule as VAL-16. Gates v0.7, the Phase 6 release (§8.2.4 D6; §8.2.5 E2; §8.2.6 F1) |

NOTE (the comparison surface, and why VAL-01 reports two norms; WP13): the probe grid is **this
project's**, a content-hashed document of named tensor-product patches that the reference is
interpolated onto, so the comparison does not depend on the reference's mesh and a re-export cannot
silently move the sample points; the grid's hash is declared in every golden and a mismatch is
refused. A probe point is retained for a field only where the point *and* its four `±0.05 nm`
neighbours lie inside that field's domain — the reference model's own maximum element size on the
pore wall — because a solver returns zero outside a field's domain rather than refusing, and a
concentration norm taken over the membrane is dominated by fabricated zeros and reads as agreement.
Where the two implementations then still disagree about where a field exists, the comparison SHALL
abort naming the worst point and its distance rather than intersecting the two sets.

The VAL-01 quantity is the **`r`-weighted** axisymmetric relative L² error, which is the norm the
axisymmetric weak forms of §6.2 are posed in. It SHALL be reported together with the unweighted
relative L² and with the located maximum, because the `r` weight vanishes on the axis — the weight
is three orders smaller on a near-axis sample than at the pore wall — and the axis is exactly where
the `1/r` forms of §6.2 and the NUM-06 natural condition are fragile. A comparison reporting the
weighted norm alone would be least sensitive precisely where this implementation is most likely to
be wrong. The pressure SHALL be compared **gauge-free**, its `r`-weighted mean removed from both
fields and the removed constants reported: `p` enters the momentum equation only through `∇p`, the
reference's gauge is not in the model report, and a gauge offset compared raw presents as a
discrepancy of order one that is not a discrepancy at all.

NOTE (VAL-16 and VAL-17; §8.2.4 D6): the gated leg solves on the
reference inputs in the validated configuration, so a difference there belongs to the solver or to
the reference's own discretisation (RSK-09). The recorded leg solves the same cases on the geometry
and charge generated from the ensemble. Its difference from the gated leg is what the pipeline adds,
and it gates nothing. Every published number compared SHALL be declared with its unit and sign
convention. A current SHALL also declare the boundary it was evaluated on (`knowledge/04-clya-geometry-and-charge/06-validation-targets.md#66-auxiliary-formulas-needed-to-compute-the-targets`),
and an average its weight. The published pore averages may omit the `2πr` Jacobian
(`knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md` G6), so the declaration settles G6 and the comparison does not guess it. A
reference value missing its declaration is refused, as VAL-03 refuses a golden. The tolerances are
not QR-02's 1 % and 0.5 %. The published values carry no discretisation error bar, were solved with
streamline and crosswind stabilisation on, and are quoted to two or three significant figures. The
work package states each tolerance with that argument before the comparison is run. The published
correction-ablation percentages (`knowledge/04-clya-geometry-and-charge/06-validation-targets.md#65-correction-ablation-targets-t-sectransportcomparison_corrections`) are recorded beside the verdict. A
discrepancy that appears under one correction family alone localises to it, which recovers part of
what a field comparison would have localised.

NOTE: the reference model carries no mesh convergence study, so part of any residual difference may
originate in the reference (RSK-09). The project's own discretisation error is quantified first
(§7.3), and the residual is then attributed.

NOTE (the frozen cases, closing VAL-03's scope; author ruling): the reference set
is **five cases** on the §5.2.1 reference geometry, in the validated ePNP-NS configuration — the
four envelope corners 0.05 M and 3 M × ±200 mV, and the centre point 0.5 M / +50 mV. The corners
span the experimental range of VAL-07 and supply VAL-02 a matched opposite-bias pair at each salt,
so `RR` is comparable and not only `I`; the centre point separates a discrepancy linear in bias from
one quadratic in it. The §7.5.1 analyte case is **not** in the set. VAL-04's refinement pair is the
published mesh and one uniform refinement of it, on the centre case alone: RSK-09 needs a bound on
the reference's own discretisation error, not a field of them, and a comparison whose residual falls
below that bound SHALL be reported as *reference-limited* rather than as agreement. The bound and the
residual SHALL be taken over the same probe points: the margin band beside every fluid/solid
interface, which the comparison against the rungs drops, is dropped from `Δ_ref` too, although the
two exports carry values there. Kept, it would put the near-wall disagreement of the two
refinements into a bound on errors that never saw it, and the verdict would read
*reference-limited* too readily.

NOTE (VAL-05's metric, registration and tolerances; WP22; author
ruling of the same date): both legs compare polygons in the model frame. Ours is the stage-5
region's profile. The reference is the delivered 185-vertex table of §5.2.1. The comparison runs
on the 282 mid-planes `z_k = −1.85 + (k + ½)·0.05` nm, where the lumen radius is each polygon's
innermost crossing. The generated polygon SHALL cross every plane except within 0.1 nm of the
reference's tips. The rule binds the gated comparison; the recorded isolevel sweep compares each
level on the planes both polygons cross and records the rest, since a high level shortens the body
at both tips (WP22 Outcomes). With `Δ = r_ours − r_ref` and `r = r_ref`, three quantities are gated:

- `ε_G = 2 Σ (Δ/r) r⁻² / Σ r⁻²`, the first-order relative conductance change of a bulk series
  resistor, which is the phase plan's `G ∝ r²` made a number;
- the rms of `Δ`;
- `Δr_c`, the difference of the two minimum lumen radii over `z ∈ [−1.85, 1.6]` nm, each
  located on its own polygon.

| Leg | Tier | `\|ε_G\|` | `\|Δr_c\|` | rms `Δ` | Axial registration |
|---|---|---|---|---|---|
| ClyA-AS ensemble, DCD frames 48–97 (the Phase 2 gate) | 3 | ≤ 5 % | ≤ 0.1 nm | ≤ 0.1 nm | `centre_z_nm = 0` in the MD frame (G9) |
| Vendored 2WCD, chains A–L | 2 | ≤ 10 % | ≤ 0.1 nm | ≤ 0.2 nm | Cα centroid of residues 8–292 at `Z_MD = 5.655` nm, the MD structure's over DCD frames 48–97, which the Tier-3 leg pins to 0.01 nm (the centroid with residue 7 included is 5.63 nm and is not the reference; §8.2.4 D7) |

The argument for the tolerances follows. ±1 % on G (`knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md` G3) was a floor set while the
vertex list was unavailable. The author has since confirmed that the table was made with
`pqr2grid`'s radial binning at a 15 nm half-extent, an index-to-radius erratum worth about −8 % of
ε_G, and then by a hand edit that moved vertices by about the same amount the other way. Neither
step belongs to the method the pipeline implements, so ±1 % is unreachable by construction. The
tolerance is instead the method's own definitional uncertainty. The 25 % isolevel is unjustified
in the source (G2), and ±0.1 of isolevel moves ε_G by about ±5 %. The radius bounds are 2h, below
which stage 4 erases features by design. The 2WCD leg is looser because 2WCD lacks residues 1–7,
its hydrogens and the MD relaxation (§8.2.2 B2). No offset is fitted, and the isolevel is not
varied to pass. The isolevel sensitivity, the attribution to the erratum and the hand edit, one
frozen case's conductance on both meshes, the mesh figures and the FR-06 variance are recorded
beside the verdict (WP22 plan, D2–D11 and Design §1–§4).

NOTE (VAL-06's construction, metric and tolerance; WP29 plan; author
ruling of the same date): the problem is `poisson` on the case's deployed mesh with its stage-7
deposit, both electrodes grounded, and the fluid at the ion-free `ε_r,f⁰` (PHY-21 NOTE). APBS solves
the same problem at zero ionic strength (`lpbe`, no ions) at the case temperature, on a cubic grid
of 0.1 nm that holds all of the charge at least 1 nm inside each face. The box faces take our own
solution (`bcfl map`). Our domain's grounded outer arc and the membrane's natural edge cannot be
posed in APBS. A multipole boundary would assume a homogeneous far field, which the membrane slab
breaks. With the face data imposed, the leg compares the two interior solves, which is what it is
for.

On the **gated** leg, APBS's charge map is the stage-7 export lattice moved onto the grid nodes by
hat weights, conserving its charge and first moments. Its three staggered dielectric maps are the
permittivity the solve assembled, sampled on the deployed mesh and harmonically averaged along each
grid edge. The **recorded** leg keeps the box, grid and face data. It takes APBS's `spl4` charge
from the PQR and its `smol` surface, with the mesh's membrane imposed wherever APBS's map is on the
solvent side.

The probes are the nodes of the nested 0.2 nm grid that lie in a fluid material, at least 0.3 nm
from every solid and at least 0.4 nm inside the faces. APBS is read at its nodes. With
`Δ = φ_APBS − φ_ours` over the probes, three quantities are gated:

| Quantity | Tolerance |
|---|---|
| `e_max = max\|Δ\| / max\|φ_ours\|` | ≤ 3 % |
| `e_rms = rms Δ / rms φ_ours` | ≤ 1 % |
| `e_axis`, `e_max` over the probes on `r = 0` | ≤ 1.5 % |

Before the comparison, each solver's own error SHALL be estimated by refinement in the same run:
APBS by its 0.1 nm against its 0.2 nm solution, and ours by `P2` against `P3`. The difference is
taken as the error, a first-order bound. The sum of the two estimates SHALL lie within half of
each tolerance, or the run fails naming the budget, not the agreement.

The argument follows (WP29 plan, *Design* §4). Measured on 2WCD without forming `Δ`, the two
estimates sum to 1.22 %, 0.18 % and 0.58 % of the three norms. APBS's share is 0.98 %, 0.17 % and
0.57 %: its staircase of the protein surface, largest in the constriction. Halving the tolerance
for the two known errors leaves the other half for a disagreement, and a broken construction of
either input exceeds it (*Design* §6). The max norm is the looser of the three, because the
staircase layer meets the probes at 0.3 nm, which is three grid cells. The rms and axial norms are
the sharp ones. The tolerance is not re-argued after the comparison runs (§8.2.4 D7's reasoning).
On the analytic ring of the same plan, each solver is gated against the exact series at half of
each tolerance.

Measured (WP29, `tests/tier2/test_val06_2wcd.py`): on the protonated 2WCD at the
default sizes (44,985 elements), over 569,541 probes and the 93 on the axis, the budget is 1.20 %,
0.18 % and 0.59 % (APBS 0.95 %, 0.17 % and 0.58 %; ours 0.25 %, 0.010 % and 0.013 %). Zeroing the
charge moves the probes by 45 % rms, where 10 `τ_rms` is required, so the charge and not the faces
carries the comparison. The agreement is **0.41 %, 0.10 % and 0.23 %**, seven, ten and six times
inside the tolerance. A focused 0.05 nm grid on the lumen measures APBS's order at 1.6 in both max
and rms, so its 0.1-against-0.2 nm difference is the bound the budget assumes. On the ring
(`tests/tier2/test_val06_ring.py`) APBS and our `P2` are within 0.13 % and 0.010 % of the series in
the max norm, and each of the eight broken constructions exceeds half the tolerance. The recorded
leg's ring means differ from ours by 15.7 %, 6.7 % and 13.6 %, and the spread around a ring reaches
46 % of `max|φ|` (4.1 % rms). That is the azimuthal averaging of CON-04 together with APBS's own
charge and surface models, recorded and not gated.
