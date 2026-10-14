---
type: Domain
title: 9. Gaps and ambiguities
---

## 9. Gaps and ambiguities

1. **Stress-tensor forces on an analyte are absent from the trapping chapters.** The tensor
   expressions come from background ch. 2 and were never evaluated for an analyte *in the thesis*.
   **See §10:** they are evaluated, for PlyAB + haemoglobin, in Angew. Chem.
   2022; §10.6 gives regression targets. Analytic tests (isolated sphere: Maxwell integral → qE;
   Stokes sphere → 6πηaU) remain the right first check.

   **Done, and they were the right first check [tested]** (WP6, `tests/tier2/`). On a P2 sphere of
   radius 1 nm in a box of radius 10 nm, `a = 1 nm` mesh units, the numbers are:

   | Check | Measured | Reference |
   |---|---|---|
   | Stokes drag, three meshes (VER-19) | 0.430870, 0.430522, 0.430500 pN | `6πηaU` = 0.430491 pN |
   | its relative error | 8.80 × 10⁻⁴ → 7.11 × 10⁻⁵ → 1.98 × 10⁻⁵ | rates 3.63 and 1.85 per halving |
   | Maxwell integral on an uncharged dielectric sphere (VER-20) | −8.6 × 10⁻⁸ pN (domain), +7.0 × 10⁻⁵ pN (surface) | 0 |
   | `F = qE₀` anchor, −4 e at 5.1 MV/m (VER-20) | −8.21704 pN (domain), −8.18903 pN (surface) | −8.23281 pN, i.e. 0.19 % and 0.53 % |
   | Henry mobility at κa = 0.50 / 2.08 / 16.47 (VER-21) | `μ̃_e/ζ̃` = 0.661, 0.704, 0.872 | `2f(κa)/3` = 0.676, 0.711, 0.885 |

   Two findings worth carrying forward. **The far field decides whether VER-19 measures anything**:
   a uniform stream at `R = 10a` gives 1.285 × the drag, the `1 + (9/4)(a/b)` wall correction of a
   sphere in a concentric container, so the exact Stokes field has to be imposed instead. And **the
   zero test cannot stand alone**: a net force of zero on a polarised sphere is invariant under a
   uniform scale factor, so the `qE₀` anchor is what pins the magnitude of the Maxwell route, which
   has no reaction-route oracle because `φ` is not constrained on the body's surface.
2. **"Surface charge density vs smeared volumetric charge" resolves to one pipeline, not two
   models** (§2). If the author meant a genuine σ_s on an analyte boundary in other work, it is not
   in the thesis — ask.
3. **ε_protein = 10 (trapping) vs 20 (ePNP-NS)**, same citation. Unresolved.
4. **Body bead charge printed as both −1.43 e and −1.7143 e** (§2a). Resolve as N_body/7.
5. **`eq:threshold_voltage_complex` has a typo:** it prints `log(Δx_trans / Δx_trans)` ≡ 0;
   re-deriving dk/dV_b = 0 gives `log(Δx_trans / Δx_cis)`. Check with the fitted parameters
   (kT/e = 25.69 mV): corrected → 87.7 mV (N_tag +4), 61.1 mV (+9) vs published 87.3 / 60.4; the
   zero term gives 85.1 / 59.6. **The corrected form reproduces the published table.**
6. **Sign convention is sloppy:** V_b is negative throughout, yet V_thresh is tabulated positive
   (the leading minus makes it a magnitude). Pick one convention and assert it in tests.
7. **`f(t) = k·e^{−kT}`** (`trapping_appendix.tex §single_bound_state`) is a typo for `k·e^{−kt}`;
   the correct exponent appears two lines later.
8. **Δx_cis is ill-defined by the author's own admission** (voltage-dependent barrier location) — a
   fit parameter, not a geometric constant. A v1 PMF that locates the *cis* barrier should report
   against both 2.7 nm and 5.21 nm.
9. **Caption/text conflict:** `trapping_translocation_voltage` says the threshold voltage
   "increases" ≈5.21 mV per tag charge; the text says "decrease of ≈5 mV". Both describe |V_thresh|
   falling 87.3 → 60.4 mV; the caption means the signed value.
10. **N_eo "depends solely on size and shape"** — untested, and exactly what a v1 F(z) sweep can
    falsify: check whether F_hyd/V_b is constant across salt and bias at fixed geometry. Hypothesis,
    not result.

---

