# Validation and verification — the benchmark ladder

Four tiers, cheapest first. Tiers 1–2 run on every commit; Tier 3 nightly; Tier 4 gates releases.
Formulas below are stated in full so an agent can implement a test without leaving this file. Each
was checked numerically where marked **[verified]**.

---

## Tier 1 — Unit and property tests (seconds)

- Charge conservation through Gaussian smearing and azimuthal projection, evaluated **on the
  deployed FE mesh**, not the source grid: `|∫ρ_fixed·2πr dr dz − Q_net|/|Q_net| < 10⁻³`. Also
  check per-z-slice cumulative charge against the PQR sorted by z — this catches Jacobian errors
  that cancel globally.
- Every correction model reproduces its published check values (see `01-physics-epnpns.md` §8):
  `f^w_D(0) = 0.0601`, `f^w_D(0.75) = 0.9910`, `η₀/η^w(0) = 0.3790`, `η₀/η^w(1.45) = 0.9876`,
  `η(5.3 M) = 1.752 × 10⁻³ Pa s`, `ϱ(5.3 M) = 1194 kg m⁻³`, `D_Na(5.3 M) = 8.13 × 10⁻¹⁰`,
  `D_Cl(5.3 M) = 1.071 × 10⁻⁹`. **[verified]**
- Nernst–Einstein consistency of the infinite-dilution values: `μ_i⁰ = D_i⁰/V_T` to 4 significant
  figures. **[verified]**
- **Einstein-relation drift test.** `D_i/μ_i` is *not* `kT/e` at finite concentration — the ratio
  drifts to 1.2–1.7 × `kT/e` between 0.15 and 3 M because D and μ were fitted independently. Assert
  the drift matches expectation rather than asserting the Einstein relation. This is also why
  Poisson–Boltzmann is a *separate model*, not the PNP solver at zero bias.
- Wall-distance field is C¹ after mollification.
- Integration order ≥ 3 asserted on every form containing `1/r`; a unit test integrating a known
  `1/r`-weighted quantity on an axis-touching mesh (order 2 returns NaN — see
  `06-numerics-fem.md` §2.2). **[verified]**
- Packing fraction `Σ_j N_A a_j³ c_j < 1` enforced.
- Case-file schema round-trips; mesh quality gates fire on known-bad input.

---

## Tier 2 — Analytic benchmarks (minutes)

### 2.1 Gouy–Chapman, 1:1 electrolyte
```
φ̃(x) = 4 artanh( tanh(ζ̃/4) · e^{−x/λ_D} )          φ̃ = φF/RT
σ_s   = √(8 ε R T c₀) · sinh(ζ̃/2)                    (Grahame)
```
Mutually consistent to 6 digits by numerical differentiation. **[verified]**
Tests: Poisson + Boltzmann equilibrium.

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

### 2.8 Analyte force benchmarks (new — no prior results exist)
Because the thesis's trapping work used equilibrium APBS on a bead model with a 1D analytic rate
model — no stress-tensor integrals, no force profile (see `05-analyte-and-forces.md`) — the force
feature has **no reference implementation to regress against**. Verify against analytics instead:

- Stokes drag on a sphere: `F = 6πηaU` (and the axisymmetric-tube correction for confinement).
- Maxwell stress on a dielectric sphere in a uniform field — closed form available.
- Electrophoretic mobility limits: Hückel (`λ_D ≫ a`) `μ_e = 2εζ/3η`; Smoluchowski
  (`λ_D ≪ a`) `μ_e = εζ/η`.
- Domain-form vs surface-form force must agree (`06-numerics-fem.md` §7).

---

## Tier 3 — COMSOL differential tests (hours, nightly)

The oracle tier, available because the author retains a COMSOL licence.

For a frozen set of cases spanning the envelope, compare field-by-field against exported COMSOL
solutions — `φ`, `c_i`, `u`, `p` sampled on a common probe grid — plus every scalar QoI.

**Acceptance: < 1 % relative L² on fields, < 0.5 % on integrated QoIs.**

Golden files stored as compressed arrays with the generating COMSOL model archived alongside.

> **Treat the oracle as a depreciating asset.** Generate and archive the full reference set
> *early*, in the solver-core phase, so the project stays verifiable if licence access ever lapses.

**Differential-test design.** Because the corrections are independently switchable, the most
informative comparisons are *ablations*: classical PNP-NS, then each correction family enabled
alone, then all. A discrepancy that appears only when one correction is on localises the bug
immediately. This is the strongest argument for making PNP-vs-ePNP a first-class configuration
rather than a code branch.

### Measured: the attribution ladder on the VER-11 benchmark pore **[tested]**

Four configurations of one model against a self-golden generated by the last of them, on the
708-element VER-11 pore (2 nm radius, 13 nm membrane, 0.5 M, +50 mV, −0.05 C/m², validated ePNP-NS
with the flow on). `E_k` is the *r*-weighted relative L² on a 157-point probe grid;
`Δ_resid = E₃` is zero by construction because rung 3 generated the golden. Four full ladder
solves take **75 s** on this mesh.

| field | `Δ_total` (`none`, P2/P1) | `Δ_transport` (→ `supg`) | `Δ_flow` (→ `reference`) | `Δ_pair` (→ P1/P1) |
|---|---|---|---|---|
| `potential` | 4.01e-2 | −3.55e-2 | −3.40e-3 | −1.23e-3 |
| `c_Na+` | 2.35e-3 | −1.38e-3 | −9.20e-4 | −4.25e-5 |
| `c_Cl-` | 7.27e-4 | +1.27e-4 | −8.12e-4 | −4.21e-5 |
| `pressure` | 1.89e-1 | +3.97e-2 | −1.98e-1 | −3.09e-2 |
| `velocity_r` | 8.53e-1 | +2.71e-3 | −7.69e-1 | −8.71e-2 |
| `velocity_z` | 5.77e-2 | −8.53e-3 | −2.08e-2 | −2.84e-2 |

Two things this says, and neither is visible in a three-rung ladder.

**The transport stabilisation dominates the potential and the flow GLS dominates the velocity.**
`Δ_transport` carries 88 % of the potential's distance and 0.3 % of `velocity_r`'s; `Δ_flow`
carries 90 % of `velocity_r`'s. Collapsing the two into one `Δ_stab`, as a three-rung ladder does,
would report a single number that is 88 % transport for one field and 90 % flow operator for
another — and attribute neither.

**`Δ_pair` is not negligible for the flow.** The element pair alone moves `velocity_r` by 8.7 % and
the pressure by 3.1 %, against 0.004 % for `c_Na+`. A comparison against a P1/P1 reference that ran
at Taylor-Hood would carry that as an unexplained residual.

These are machinery measurements on a coarse benchmark, not statements about the reference
implementation: the golden is one of our own solutions and the report says `golden_source: self`.

### The transposed table is silent, and non-square patches are the cheap gate **[verified]**

A COMSOL `%Data` block is one row per `z` sample and one value per `r` sample, which is
`RadialGrid`'s own `[i_z, i_r]` layout. The reader checks that every row has the same width, which
catches a ragged file and **not** a cleanly transposed square one: the shape check passes and the
field is wrong everywhere except on the diagonal `r = z`, where it is exactly right. Requiring
`n_r ≠ n_z` on every probe patch turns that case into a shape error at ingest and costs nothing —
no physically motivated patch needs equal sample counts.

### The *r*-weighted norm cannot see the axis **[tested]**

On the checked-in ClyA probe grid, a unit perturbation confined to the `axis_line` patch — 1 610 of
6 205 points, all within 0.045 nm of the symmetry axis — gives `rel_l2 = 0.51` and
`rel_L2_r = 4.0e-4`. Three orders. The weight is `w_p · r_p`, and `r_p` is 0.005 nm there against
60 nm at the far edge of the reservoir patch. The axis is where the `1/r` forms of §6.2 and the
NUM-06 natural condition are fragile, so a Tier-3 comparison reporting the weighted norm alone
would be least sensitive exactly where the implementation is most likely to be wrong. The same
perturbation moved to the reservoir patch gives `rel_L2_r > 0.1`, which is what shows the contrast
is the axis and not the patch's point count.

### The telescoping identity catches a slip, not a stale golden **[verified]**

`Δ_total + Δ_transport + Δ_flow + Δ_pair = E₀ + (E₁−E₀) + (E₂−E₁) + (E₃−E₂) = E₃ = Δ_resid` holds
for **any** four numbers. It is worth asserting — it fails if the deltas are formed or assigned
wrongly — but it cannot detect a rung compared against a re-exported golden or an edited probe
grid, which telescope exactly as cleanly. Those need the hashes compared directly, and the retained
point count per field compared between rungs. The WP13 plan's decision row claimed the identity did
that job; it does not.

### A `%Grid` table round-trips `float64` exactly at `%.17g` **[tested]**

Seventeen significant decimal digits round-trip an IEEE-754 double by definition, so a solution
written to a `%Grid` table and read back through `density.grid.read_grid` reproduces its array
**bitwise**, `NaN` included (`f"{nan:.17g}"` is `"nan"`, which `np.fromstring` parses back). A
self-golden round trip therefore asserts exactly `0`, not a tolerance — any difference at all is a
defect in the transport format rather than a rounding budget being spent.

---

## Tier 4 — Experimental reproduction (release gate)

Reproduce the published ClyA results:

- Conductance vs salt over the experimental range **0.05–3 M** (simulated 0.005–5 M).
- I–V and rectification `α(V_b)` over **±200 mV** — not ±150 mV, which drops the highest-|V|
  quarter of the envelope, precisely where rectification is largest and Newton convergence hardest.
- Cation transport number `t_Na⁺`.

**Acceptance: agreement no worse than the paper's own agreement with experiment.**

**Also reproduce the failure.** Classical PNP-NS must reproduce the paper's reported
*over-estimation* of current. Reproducing the failure of the uncorrected model is as diagnostic as
reproducing the success of the corrected one — it proves the corrections are actually active and
doing what they should.

Detailed numeric targets — transport numbers, peak radial potentials, pore-averaged ion ratios,
energy barriers, EOF velocities, pressure hotspots, and the correction-ablation percentages — are
tabulated in `04-clya-geometry-and-charge.md` §6.

> **Caveat on all Tier-4 targets.** The published results carry no discretisation error bar: the
> thesis reports no element counts, no mesh convergence study, no solver tolerances. Small
> disagreements may be *their* discretisation error rather than ours. Where a target is a
> pore-average, check which averaging convention it uses — the thesis's pore averages appear to
> omit the `2πr` Jacobian while being described as volume averages.

---

## Continuous integration

| Tier | When | Gate |
|---|---|---|
| 1, 2 | every push | must pass |
| 3 | nightly + pre-release | must pass |
| 4 | pre-release | must pass |

Every run emits a provenance manifest: input hashes, library versions, mesh hash, solver settings,
correction parameter file version, and which corrections were enabled.
