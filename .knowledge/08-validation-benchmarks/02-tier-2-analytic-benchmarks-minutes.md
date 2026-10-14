---
type: Benchmark
title: Tier 2 — Analytic benchmarks (minutes)
---

## Tier 2 — Analytic benchmarks (minutes)

### 2.1 Gouy–Chapman, 1:1 electrolyte
```
φ̃(x) = 4 artanh( tanh(ζ̃/4) · e^{−x/λ_D} )          φ̃ = φF/RT
σ_s   = √(8 ε R T c₀) · sinh(ζ̃/2)                    (Grahame)
```
Mutually consistent to 6 digits by numerical differentiation. **[verified]**
Tests: Poisson + Boltzmann equilibrium.

### 2.1.1 Gouy–Chapman–Stern through stage 5: Gauss's law across a cylindrical shell **[tested]** {#211-gouychapmanstern-through-stage-5-gausss-law-across-a-cylindrical-shell}

A planar Stern layer (VER-31) cannot be posed through stage 5, whose region is axisymmetric, so
VER-59 poses it on a long tube, `r ∈ [3, 5]` nm, with stage 5's shell of `a` = 0.25 nm on its lumen
side. On a plane where `φ` is flat in `z`, the charge-free shell carries the flux of the mobile
charge it encloses:

```
φ(R − a) − φ(R) = λ_enc ln(R/(R − a)) / (2π ε₀ ε_r,f⁰),   λ_enc = F Σ z_i ∫₀^{R−a} c_i 2πr dr
```

and `φ` takes the mean of its ends at `√(R(R − a))`. The trap: `∂φ/∂z = 0` by symmetry is not
enough, because Gauss's law in the shell needs `∂²φ/∂z² = 0` too. **With the bilayer on the analysis
plane the drop missed the closed form by 6 %**: the membrane (`ε` = 3.2) against the body's outer
side curves `φ` in `z` across the 2 nm body. With the bilayer moved 12 nm away
(`geometry.membrane.centre_z_nm` = −12 on a 30 nm tube) the drop is 6.5365 mV against 6.5357 mV,
1.3e-4 relative, at 0.1 M, `pnp`, zero bias, the default sizes (49,629 triangles, 44 s to stage 10),
and the geometric-mean point is the mean of the ends to 2e-6 of the drop. At `size_scale` 2 the
agreement is 3.6e-3: what moves is `λ_enc`, the lumen's concentration integral, not the drop. The
shell is 17.8 % of the wall potential (−36.8 mV), so a shell holding ions cannot pass.
`tests/tier2/test_exclusion_stern.py`.

### 2.2 Debye–Hückel in a cylinder
```
φ(r) = ζ · I₀(r/λ_D) / I₀(a/λ_D)
```
Satisfies `∇²φ = φ/λ_D²` in cylindrical coordinates to 6 digits. **[verified]**
**The cleanest single test of the axisymmetric Poisson weak form and the axis BC** — it exercises
the `r`-weighted measure and the natural condition at `r = 0` with an exact answer.

### 2.3 Electro-osmosis in a cylindrical capillary
Rice & Whitehead, *J. Phys. Chem.* **69**, 4017 (1965) — thick and thin EDL. Burgreen & Nakache
(1964) for slits. Tests coupled Poisson + Stokes.

### 2.4 Helmholtz–Smoluchowski limit
```
u_slip = −ε ζ E_t / η          as λ_D/a → 0
```
Tests the asymptotic correctness of the coupled solve.

### 2.5 1D steady PNP with limiting current
Bazant, Chu & Bayly, *SIAM J. Appl. Math.* **65**, 1463 (2005). Tests the full PNP system.

### 2.6 Maxwell–Hall access conductance
```
G = σ · [ L/(πa²) + 1/(2a) ]⁻¹        (radius form)
  ≡ σ · [ 4L/(πd²) + 1/d ]⁻¹          (diameter form)
```
Uncharged pore at 1 M; **reproduce to < 2 %**.

> **Factor-of-two trap.** Hall's result is `R_access = ρ/(4a)` *per side*, so both sides give
> `ρ/(2a)`. The frequently-copied `G = σ[L/(πa²) + 1/a]⁻¹` substitutes radius for diameter in the
> access term and is wrong by 2× there — for a ClyA-like `a = 2 nm`, `L = 13 nm` it under-predicts
> `G` by ~16 %. Using it as the target would make a *correct* solver fail the gate, and invite
> "fixing" the solver to hit a wrong number.

### 2.7 Method of manufactured solutions
On the **full coupled axisymmetric system** with `r`-weighted forms. **The only way to verify the
`u_r/r²` hoop term and the axis treatment.** Expect O(h³) in L² for P2.

### 2.8 Analyte force benchmarks
The thesis's trapping work used equilibrium APBS on a bead model with a 1D analytic rate model,
with no stress-tensor integrals and no force profile (see `05-analyte-and-forces.md` §0–§9). The
only published force profile is Angew. Chem. 2022 (`05` §10), which gives main-text targets
(`05` §10.6) but no code or field data. Verify against analytics first, then those targets:

- Stokes drag on a sphere: `F = 6πηaU` (and the axisymmetric-tube correction for confinement).
- Maxwell stress on a dielectric sphere in a uniform field — closed form available.
- Electrophoretic mobility limits: Hückel (`λ_D ≫ a`) `μ_e = 2εζ/3η`; Smoluchowski
  (`λ_D ≪ a`) `μ_e = εζ/η`.
- Domain-form vs surface-form force must agree (`06-numerics-fem.md` §7).

---

