# ePNP-NS — normative physics reference

**Status:** authoritative. Transcribed from Willems K. et al., *Nanoscale* **12**, 16775–16795
(2020) and the CC-BY-4.0 thesis `willemsk/phdthesis-text`, ch. 5 + ch. 5 SI (`epnpns.tex`,
`epnpns_appendix.tex`). Every numeric claim below has been checked numerically against the
self-consistency values stated in the thesis. Where the thesis is internally inconsistent, the
resolution and its arithmetic are given in **§8 Errata**.

Agents: this file is the single source of truth for the equations. Do **not** re-derive from the
paper abstract or from web summaries — several widely-copied summaries of this model are wrong.

---

## 1. Symbols

| Symbol | Meaning | Units |
|---|---|---|
| `φ` | electric potential | V |
| `c_i` | concentration of ion *i* | mol m⁻³ |
| `u` | fluid velocity | m s⁻¹ |
| `p` | pressure | Pa |
| `J_i` | total molar flux of ion *i* | mol m⁻² s⁻¹ |
| `ρ_pore` | fixed (protein) space charge density | C m⁻³ |
| `ρ_ion` | mobile ionic charge density = `F Σ_i z_i c_i` | C m⁻³ |
| `⟨c⟩` | **average ion concentration** = `(1/n) Σ_i^n c_i` | mol L⁻¹ |
| `d` | distance to the **nearest pore boundary** | nm |
| `ε_0` | vacuum permittivity 8.85419 × 10⁻¹² | F m⁻¹ |
| `F` | Faraday constant 96485.33 | C mol⁻¹ |
| `N_A` | Avogadro 6.022 × 10²³ | mol⁻¹ |
| `a_i`, `a_0` | steric cubic diameters, ion / water | m |

> **⟨c⟩ is the average ion concentration, not the ionic strength.** The thesis defines
> `⟨c⟩ = (1/n) Σ_i c_i` in eq. 5.3 while the prose elsewhere says "local ionic strength". For a
> symmetric 1:1 salt the two coincide, so the distinction never surfaced in the published work —
> but it must be decided explicitly before any multivalent species is added. Implement `⟨c⟩` as
> the arithmetic mean per eq. 5.3, and make the choice a named, documented option.

> **`d` excludes the membrane.** The wall-distance field is the distance to the pore boundary
> only. The bilayer is deliberately not a source of wall distance, because electrolyte properties
> near the membrane do not affect the pore's figures of merit. In COMSOL this was implemented with
> a general extrusion operator and was **not smoothed** (author, 2026-08). See §7 for why we
> nevertheless recommend mollifying it in the new implementation.

---

## 2. Governing equations

### 2.1 Poisson

```
∇·(ε_0 ε_r ∇φ) = −(ρ_pore + ρ_ion) ,      ρ_ion = F Σ_i z_i c_i
```

`ε_r` is piecewise: `ε_r,p = 20` in the protein, `ε_r,m = 3.2` in the bilayer, and in the
electrolyte `ε_r,f(⟨c⟩) = ε_r,f⁰ · ε_r,f^c(⟨c⟩)` with `ε_r,f⁰ = 78.15`.

**Weak form** (SI §A.1), test function `ψ`, over `Ω = Ω_w + Ω_p + Ω_m`:

```
∫_Ω ∇ψ · D dΩ − ∫_Γ ψ (D·n) dΓ = ∫_Ω ψ ρ_pore dΩ + ∫_Ω ψ ρ_ion dΩ ,    D = ε_0 ε_r ∇φ
```

with `Γ_PE = Γ_w,c + Γ_w,t + Γ_m`. Dirichlet `φ = 0` on `Γ_w,c`, `φ = V_bias` on `Γ_w,t`, and zero
charge `n·D = 0` on `Γ_m`.

> Note the Poisson equation is solved over the **whole** domain including protein and membrane;
> the Nernst–Planck and Navier–Stokes equations are solved only on `Ω_w`.

### 2.2 Size-modified Nernst–Planck

```
∂c_i/∂t = −∇·J_i = 0        (steady state)

J_i = −[ D_i ∇c_i  +  z_i μ_i c_i ∇φ  +  D_i β_i c_i  −  u c_i ]
```

**Steric flux vector** (Borukhov/Kilic/Lu size-modified PNP):

```
            (a_i³ / a_0³) · Σ_j N_A a_j³ ∇c_j
    β_i  =  ─────────────────────────────────
              1 − Σ_j N_A a_j³ c_j
```

with `a_i = 0.5 nm` (all ions; max packing 13.3 M) and `a_0 = 0.311 nm` (water; max packing
55.2 M). There are no experimentally verified values for these; they are from Bazant 2009.

> **Sign discipline.** `β_i` enters `J_i` inside the bracket with a `+`, and the whole bracket is
> negated. Write it exactly as above and add a code comment: *this is the most likely place for a
> sign error in the entire model; a flipped sign drives ions into crowded regions, pushes the
> packing fraction to 1, and diverges.* The `a_i³/a_0³` prefactor makes the steric drive
> species-dependent, and the sum over `j` couples all species — do not collapse it to a
> self-interaction.

**Boundary conditions:** Dirichlet `c_i = c_bulk` on `Γ_w,c` and `Γ_w,t`; no-flux `n·J_i = 0` on
`Γ_p+m`.

### 2.3 Navier–Stokes, variable density and viscosity

The published model uses the **variable-density incompressible** formulation of Axelsson et al.
(2015) — a system of *three* equations, not the constant-density NS most summaries assume:

```
u·∇ϱ = 0                                             (density continuity)
(u·∇)(ϱu) + ∇·σ = f                                  (momentum)
∇·(ϱu) − u·∇ϱ = 0                                    (velocity continuity)

σ = p I − η [ ∇u + (∇u)ᵀ ]
```

**Body force:**

```
f = ρ_ion E = −ρ_ion ∇φ
```

> **There is no Korteweg–Helmholtz / dielectric-gradient term in the published model.** Although
> `ε_r` varies with `⟨c⟩`, the model does **not** include `−½|∇φ|²∇ε` in the momentum equation,
> nor the corresponding `−½|∇φ|² ∂ε/∂c_i` term in the Nernst–Planck excess chemical potential.
> Adding either is a **deviation from the validated model**. Implement both behind a single
> `dielectric_gradient_forces` flag, default **off**, and quantify their magnitude as a numerical
> experiment. Do not silently add them: the model's agreement with experiment was obtained
> without them, and adding one without the other is thermodynamically inconsistent.

**Boundary conditions:** no-slip `u = 0` on `Γ_p+m`; no normal stress `σ·n = 0` on `Γ_w,c` and
`Γ_w,t`.

### 2.4 Domains and boundaries

```
Ω   = Ω_w (electrolyte reservoir) + Ω_p (pore protein) + Ω_m (lipid bilayer)
Γ_w,c , Γ_w,t   exterior reservoir boundaries, cis and trans
Γ_m             exterior membrane boundary
Γ_p+m           interior interface: fluid | (pore + membrane)
```

Geometry: hemispherical reservoirs R = 250 nm each side; DPhPC bilayer thickness 2.8 nm.

---

## 3. The corrections

Each property is `X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄)`, with `c̄ = ⟨c⟩/(1 M)` and `d̄ = d/(1 nm)`
dimensionless. Numeric parameters live in `data/corrections/willems2020_nacl.yaml`.

| Property | `f^c` | `f^w` |
|---|---|---|
| `D_i` | `(1 + P₁c̄^½ + P₂c̄ + P₃c̄^{3/2} + P₄c̄²)⁻¹` | `1 − exp(−P₁(d̄ + P₂))` |
| `μ_i` | same form, own coefficients | `1 − exp(−P₁(d̄ + P₂))` |
| `η` | `1 + P₁c̄^½ + P₂c̄ + P₃c̄² + P₄c̄^{7/2}` | `1 + exp(−P₁(d̄ − P₂))` |
| `ϱ` | `1 + P₁c̄ + P₂c̄²` | — |
| `ε_r,f` | `1 − (1 − P₁/P₀) · L(3P₂c̄/(P₀−P₁))`, `L(x) = coth x − 1/x` | — |

**Note the two wall functions have opposite offset signs** — `(d̄ + P₂)` for D and μ,
`(d̄ − P₂)` for η. This is not a typo in this file; both are verified in §8.

**Infinite-dilution values (298.15 K):**

| | value | source |
|---|---|---|
| `D_Na⁰` | 1.334 × 10⁻⁹ m² s⁻¹ | Mills 1989 |
| `D_Cl⁰` | 2.032 × 10⁻⁹ m² s⁻¹ | Mills 1989 |
| `μ_Na⁰` | 5.192 × 10⁻⁸ m² V⁻¹ s⁻¹ | Bianchi 1989 |
| `μ_Cl⁰` | 7.909 × 10⁻⁸ m² V⁻¹ s⁻¹ | Bianchi 1989 |
| `η⁰` | 8.904 × 10⁻⁴ Pa s | Hai-Lang 1996 |
| `ϱ⁰` | 997 kg m⁻³ | Hai-Lang 1996 |
| `ε_r,f⁰` | 78.15 | Gavish 2016 |
| `ε_r,p` | 20 | Li/Li/Zhang/Alexov 2013 |
| `ε_r,m` | 3.2 | Gramse 2013 |
| `t_Na⁰` | 0.3963 | Bianchi 1989 |

**Validity and capping.** Fits cover 0–5.3 M NaCl. Above 5.3 M every property is **clamped** to
its 5.3 M value. Diffusivities between 4 and 5.3 M are extrapolated (no experimental data beyond
4 M). Implement clamping explicitly and log when it activates — a silently clamped run at high
salt is a plausible source of confusion.

**Deliberate omission.** Simakov and Pederson additionally reduce ion motility by the ratio of
ion radius to pore radius. Willems et al. **chose not to include this**, on the grounds that
extrapolating it to ions whose hydrodynamic radius is comparable to a solvent molecule is
questionable. Do not add it silently; if ever added, it must be an opt-in experimental model.

### 3.0 The Einstein ratio, measured

`D_i/μ_i` in units of `kT/e`, evaluated from the shipped coefficients far from any wall
(`f^w = 1`), computed with the implementation in `nanopnp.materials`. **[tested]**

| `⟨c⟩` | 0.15 M | 1 M | 3 M | 5.3 M |
|---|---|---|---|---|
| Na⁺ | 1.208 | 1.468 | 1.665 | 1.818 |
| Cl⁻ | 1.132 | 1.221 | 1.279 | 1.300 |

The frequently quoted "1.2–1.7 × kT/e between 0.15 and 3 M" describes **Na⁺**; Cl⁻ drifts far
less, reaching only 1.28 at 3 M. Both rise monotonically with concentration, because `D` is fitted
to self-diffusion data and `μ` to conductivity data and the two fits differ. A regression test
should assert monotonicity plus per-ion bounds rather than a single shared range.

### 3.1 ePNP-NS → PNP-NS

The classical equations are recovered exactly by setting

```
β_i = 0  and  ε_r,f^c = D_i^c = μ_i^c = η^c = ϱ^c = 1  and  D_i^w = μ_i^w = η^w = 1
```

This is why the correction registry should treat "off" as just another named model: the
PNP-vs-ePNP comparison, and the contribution of each individual correction, then becomes a
configuration sweep rather than a code branch.

### 3.2 Auxiliary: the transport-number fit

`t_Na^c(c̄)` shares the inverse-polynomial form. It is **not needed at solve time** — it was used
to split measured molar conductivity `Λ(c)` into per-ion mobilities via
`μ_i(c) = Λ(c) t_i(c) / (z_i F)`, with `t_Cl = 1 − t_Na`. Keep it in the data file: it is exactly
what someone re-parameterising a different salt will need.

---

## 4. Rationale worth preserving

**Why the wall offset is 0.01 nm and not Simakov's 0.22 nm.** With `P₂ = 0.22` the function is
negative over the first ~0.2 nm, giving a dead zone of near-zero diffusivity. Pederson et al.
patched this by clamping to an arbitrary positive floor, but that makes any pore narrower than
~0.5 nm carry essentially no current — contradicted experimentally (Rigo 2019). Willems et al.
instead assign the full offset to the heavy atom, i.e. assume the ion-inaccessible volume is
*already* excluded by the geometry. Resulting values: `f^w(0) = 0.06`, `f^w(0.75 nm) = 0.99`.

**Why the viscosity wall function was fitted inverted.** Pronk's MD viscosity data were offset by
each protein's hydrodynamic radius so that `d = 0` means "at the wall" independent of protein
size, then normalised and inverted (`η_0/η^w`) so the fit ranged over [0,1]. Resulting values:
`η_0/η^w(0) = 0.37` (i.e. ~2.6× bulk viscosity at the wall), `η_0/η^w(1.45 nm) = 0.99`.

**Why bulk fits are used inside the double layer.** Acknowledged as the model's main
approximation: there is no non-bulk experimental data and no tractable analytical model. Justified
*a posteriori* by agreement with experiment except at the lowest salt (< 0.05 M), where double
layers overlap and selectivity dominates.

---

## 5. Fixed charge from structure

From the paper/ESI (see also `knowledge/04-*.md`):

- CHARMM36 partial charges and radii, protonation at **pH 7.5** via PROPKA + PDB2PQR.
- Per-atom Gaussian smearing with **σ_i = 0.5 · R_i** (sharpness factor 0.5 × atomic radius).
- Ensemble of **50 aligned MD frames** from the final 5 ns of a 30 ns run (VMD RMSD alignment).
- Azimuthal contribution `δ_i / (2π r_i)`; gridded at **0.005 nm**; loaded as a linear
  interpolation function `rhoq_pore(r,z)`.
- Axis guard, verbatim COMSOL:
  `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*pi*r))` [C m⁻³].

The density map used for the **geometry** is a separate object: 0.5 Å grid, per-atom Gaussian
using each atom's VdW radius with width factor **σ = 0.93**, radially averaged, pore surface taken
as the **25 % contour**. Do not confuse the two sharpness factors (0.93 for the geometry density,
0.5 for the charge smearing).

---

## 6. Reference case

| | |
|---|---|
| Structure | PDB **2WCD** (Mueller et al., *Nature* **459**, 726, 2009), dodecameric ClyA, C₁₂ |
| Variant | **ClyA-AS** (directed-evolution variant), not wild type |
| Electrolyte | NaCl, 0.05–3 M experimental, 0.005–5 M simulated |
| Bias | −200 … +200 mV |
| Temperature | 298.15 K (25 ± 1 °C experimentally) |
| Solver used | COMSOL Multiphysics 5.4, PARDISO direct + damped Newton |
| Validated QoIs | conductance G, cation transport number t_Na⁺, rectification α(V_b) |

---

## 7. Implementation notes carried forward

- **Mollify the wall-distance field.** The original used an unsmoothed COMSOL general-extrusion
  distance. Because `D`, `μ` and `η` all depend on `d`, a kinked `d` propagates straight into the
  Jacobian. Compute `d` once per mesh (eikonal or screened-Poisson) and smooth it to C¹. This is a
  deviation from the original *implementation* but not from the *model*, and should improve Newton
  behaviour rather than change the answer. Verify against COMSOL either way.
- **Direct solver + damped Newton is known to work.** The author reports efficient convergence in
  COMSOL using PARDISO with a Newton method and a **lower-bounded variable damping factor**. This
  is direct empirical evidence for this exact system and outweighs the general literature warning
  (Mitscha-Baude et al. 2017) that monolithic Newton struggles at high surface charge. Make damped
  monolithic Newton the primary strategy; keep segregated/Gummel as fallback.
- **Clamping and packing.** Assert `Σ_j N_A a_j³ c_j < 1` every Newton step; a packing fraction
  reaching 1 makes `β_i` singular. Fail loudly with the offending location.
- **A saturated distance field silently disables half the correction set.** Every correction is a
  product of a concentration factor and a wall factor in `d`, so passing a constant `d` large enough
  that `f^w = 1` — the honest way to say "no wall correction is active" at a call site — leaves the
  run exercising the concentration half alone while looking, from the switches, fully corrected. A
  configuration claiming "every correction active" must be handed a real `d`, from the **pore wall
  only**; the membrane is deliberately not a source (PHY-02). The failure is silent because the
  answer is a perfectly reasonable one for a different model.
- **An electrolyte's correction switches are a *record*; the resolved models are the behaviour.**
  Resolve the switches to correction models once, at construction, and every property accessor reads
  the resolved model — the switches are never consulted again. Swapping the switches alone therefore
  produces an object that reports one configuration in its provenance and evaluates another, and the
  run that follows calls itself PNP-NS, converges, and is ePNP-NS. That makes the PHY-21 ablation
  compare a configuration against itself. Rebuild the resolved models whenever the switches change,
  and refuse a pair that disagrees. **[tested]**
- **Two errors can cancel and hide both.** The 1D limiting-current benchmark passed for a while at
  the wrong film length *because* of the bug above: a 100 nm film is space-charge-limited and reads
  14 % high against the electroneutral closed form, while the silently-active corrections broke the
  Einstein relation (`mu/mu0` = 0.63 against `D/D0` = 0.92 at 1 M) and pulled the current down by
  about as much. Fixing either alone turns a passing benchmark red. **[tested]**
- **The screening length that matters at a depleted electrode is not the bulk one.** `lambda_D` goes
  as `c^(-1/2)`, so at 1e-3 of bulk it is thirty-two times larger — 9.6 nm at 1 M. A benchmark that
  justifies its geometry with the bulk value can be an order of magnitude out. The signature of a
  space-charge-limited film is that the plateau current stops depending on the electrode
  concentration at all. **[tested]**
- **`d` is a discrete field, so it must travel with the solution, not be recomputed.** Two calls to
  the same distance solver return grid functions that differ at round-off, and a residual reassembled
  against the second is a *different operator* from the one that was solved. Any post-processing that
  rebuilds the flux — the ψ-indicator current does — or any warm start that re-solves a converged
  state must read `d` back off the solution. **[tested]**

---

## 8. Errata in the source, with the arithmetic

All four were found by reproducing the thesis's own stated check values. Numbers below are
computed, not asserted.

**E1 — The D/μ wall function sign.** Thesis eq. 5.11 prints `1 − exp(−P₁(d − P₂))`; Table 5.1
prints `1 − exp(−P₁(d + P₂))`. With `P₁ = 6.2`, `P₂ = 0.01`:

| form | `f(0)` | `f(0.75)` | matches stated 0.06 / 0.99? |
|---|---|---|---|
| **`(d + P₂)`** | **+0.0601** | **+0.9910** | **yes** |
| `(d − P₂)` | −0.0640 | +0.9898 | no — negative at the wall |

**The `+` form (Table 5.1) is correct.** The equation in the running text has a sign typo.

**E2 — `P₁ = 6.2 nm⁻¹`, not 62 and not 0.62.**

| `P₁` | `f(0)` | `f(0.75)` |
|---|---|---|
| 62 | 0.4621 | 1.0000 |
| **6.2** | **0.0601** | **0.9910** |
| 0.62 | 0.0062 | 0.3757 |

Only 6.2 reproduces the thesis's stated 0.06 and 0.99. Using 0.62 would suppress ion motility
throughout a narrow pore (only 38 % of bulk at 0.75 nm from the wall) and would badly
under-predict conductance. Table 5.2 lists 6.2, sourced from Simakov 2010.

**E3 — Mobility exponent.** Table 5.1 lists `μ_Na⁰ = 5.192 × 10⁻⁴ m² s⁻¹ V⁻¹`; Table 5.2's note
(b) gives the scaling as `10⁻⁸`. Nernst–Einstein settles it: with `V_T = RT/F = 25.693 mV`,
`μ = D/V_T` gives 5.1922 × 10⁻⁸ (Na⁺) and 7.9089 × 10⁻⁸ (Cl⁻) — matching Table 5.2 to four
figures. **`10⁻⁸` is correct.**

**E4 — Viscosity cap.** The text states `η(c > 5.3 M) = 1.75 × 10⁻⁴ Pa s`. Evaluating the fit at
5.3 M gives **1.752 × 10⁻³ Pa s**. The printed value is also unphysical — it is *below* pure
water's 8.904 × 10⁻⁴, whereas salt raises viscosity. The other caps check out exactly:
`ϱ(5.3 M) = 1194 kg m⁻³` (stated 1.19 × 10³), `D_Na = 8.13 × 10⁻¹⁰` (stated 0.81 × 10⁻⁹),
`D_Cl = 1.071 × 10⁻⁹` (stated 1.07 × 10⁻⁹).

**E5 — Which permittivity parameters were actually used (open question).** The text says the
authors "opted to make use of the parameters given by Gavish for NaCl at 298.15 K
(`P₁ = 30.08`, `P₂ = 11.5`)" rather than their own fit to Buchner 1999
(`P₁ = 29.50 ± 1.32`, `P₂ = 11.74 ± 0.21`). But the stated cap `ε_r(5.3 M) = 42.12` is reproduced
by the **own fit**, not by Gavish's:

| parameters | `ε_r(5.3 M)` |
|---|---|
| Gavish (30.08, 11.5) | 42.67 |
| **own fit (29.50, 11.74)** | **42.13** ← matches stated 42.12 |

So either the cap was computed before switching parameter sets, or the simulations used the own
fit. **Ask the author.** The difference is ~1 % in `ε_r` at saturation and negligible below ~1 M,
so it is unlikely to matter for the validated results — but it must be pinned down before the
regression suite treats either as "the" reference.

---

## 9. Source files

Cloned locally at `thesis/` from `github.com/willemsk/phdthesis-text` (CC-BY-4.0):

| File | Contents |
|---|---|
| `chapters/epnpns/epnpns.tex` | ch. 5 — the framework, all equations, Tables 5.1 and 5.2 |
| `chapters/epnpns_appendix/epnpns_appendix.tex` | ch. 5 SI — weak forms, domains, BCs |
| `chapters/transport/transport.tex` | ch. 6 — application to ClyA, geometry and charge pipeline |
| `chapters/trapping/trapping.tex` | analyte trapping, force computation |
| `chapters/electrostatics/electrostatics.tex` | background electrostatics/electrokinetics |
| `chapters/nanopores/nanopores.tex` | background on biological nanopores |
| `allpapers.bib`, `mypapers.bib` | full bibliography |
