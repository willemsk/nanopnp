# WP29 — VAL-06: Poisson against APBS (the phase gate)

**Status: planned, not started.** Planned 1 October 2026, on `main` at `c6c0c0d` (WP28 merged). The
fourth package of Phase 3, and the one that carries its gate. It inherits WP26's `poisson` model
with solids, `fixed_charge` and `solid_fraction` (PHY-21 NOTE), WP27's protonation artefact and
PQR export, and WP28's export lattice, deposit and `seeded_protonated_2wcd`. It also inherits
`sample_at` (`io/fields.py`), `deployed_mesh`, stage 5's model frame and the frozen schema v2.

This plan belongs to [Phase 3](phase-3-charge-pipeline.md). `SPECIFICATION.md` governs, and the
identifiers here are pointers into it. The specification amendment this package needs is made in
this plan's commit: a §7.4 NOTE on VAL-06 stating the legs' construction, the boundary treatment,
the probe set, the metric and the tolerance with its argument. That is what the VAL-06 row means by
"stated … before the comparison is run". The APBS facts the decisions rest on are measured and
recorded in `.knowledge/07` §3 under *APBS 3.4.1 driven by maps*.

## Execution brief

**Scope.** This package adds a driver in `nanopnp.validation` that gives APBS our problem as maps,
runs it and samples the result. It also adds a closed-form benchmark of that driver and the gated
comparison on 2WCD. VAL-06 is discharged, the evidence for FR-12, FR-13 and FR-15 grows, and Phase 3
gets the third leg of its gate. No pipeline stage changes, and no case key is added. The brief runs
past its target because the comparison's construction is the correctness decision here: each of D2
to D8 changes the number VAL-06 reports.

**Read first.** VAL-06 and its new §7.4 NOTE; PHY-16 step 6 and its NOTEs; PHY-20's blend NOTE;
PHY-21's NOTE on the electrostatic models; `.knowledge/07` §3; *Design* §1–§4 below.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | The problem | `poisson` on the case's generated mesh and stage-7 deposit, `bias_V: 0`, `solid_permittivities {protein: 20, membrane: 3.2}`, fluid at `ε_r,f⁰`. APBS: `lpbe`, no `ion` line (zero ionic strength), `temp` = the case's. APBS's `kT/e` is our `φ̃ = φ/V_T`, compared without conversion | PHY-21 NOTE; `.knowledge/07` §3 |
| D2 | Box boundary | `bcfl map`: the APBS box's faces take **our** solution, sampled through `sample_at`. Both legs use it | *Design* §1: our far field cannot be posed in APBS, so the interior is compared |
| D3 | Grid | A cube with spacing `h = 0.1` nm, dime 193 and `nlev 4`. A nested 0.2 nm grid (dime 97) gives the self-refinement estimate. The axis is a node line. The z origin puts the membrane's faces midway between fine planes. The box must hold all lattice charge at least 1 nm inside every face, or the run is refused naming the face and the coordinate | *Design* §2. Measured cost: *Design* §5 |
| D4 | Charge map | The **stage-7 export lattice** (the sum the deposit projects) moved onto the nodes by hat weights: linear in z, and in the azimuth `M ≥ 16·2πr/h` equal-angle samples per ring spread bilinearly. In e Å⁻³. It conserves charge to round-off and keeps the first moments | *Design* §2. Point sampling aliases (VAL-15): hydrogens have `w` = 0.0112 nm |
| D5 | Dielectric maps | The permittivity the solve **assembled** (`relative_permittivity_field`, χ when present), sampled on a 0.01 nm (r, z) raster through the deployed mesh. Each map is staggered by `h/2` along its axis; each edge takes the **harmonic mean** of 8 sub-samples | *Design* §3: half point sampling's error on a dielectric sphere. The mesh, not the contour, is the FE solve's geometry |
| D6 | Probes and metric | Nodes of the 0.2 nm grid (also fine-grid nodes) in a fluid material, ≥ 0.3 nm from every solid (an (r, z) distance transform of the raster) and ≥ 0.4 nm inside the faces; the axis nodes are a named subset. APBS is read at nodes, ours through `sample_at`. Norms: `e_max = max\|φ_A − φ_F\| / max\|φ_F\|` and `e_rms = rms(φ_A − φ_F) / rms(φ_F)` over the probes, and `e_axis`, which is `e_max` over the axis subset | An FD solution lives at nodes; the distance keeps out the local staircase layer |
| D7 | Tolerance | **`e_max` ≤ 3 %, `e_rms` ≤ 1 %, `e_axis` ≤ 1.5 %.** Ruled by the author, 1 October 2026, on *Design* §4's argument. Written into VAL-06 and its §7.4 NOTE | §7.4 NOTE on VAL-06; *Design* §4 |
| D8 | Discretisation budget | Before the comparison, in the same test: `ê_A` = APBS 0.1 against 0.2 nm (a first-order bound), `ê_F` = ours `P3` against `P2`, and `ê_A + ê_F` ≤ ½ τ in each norm (measured 1.22, 0.18, 0.58 % against 1.5, 0.5, 0.75 %), or the test fails naming the budget. A 0.2 nm run with the charge zeroed must move the probes by ≥ 10 τ_rms, or fails naming that | A tolerance met inside an unmeasured error is luck. `P3` needs `elements {phi: P3, c: P3}` |
| D9 | Recorded leg | Same box, grid and face data; APBS's `chgm spl4` from the protonation artefact's PQR in the model frame, `srfm smol` (`srad 1.4`, `swin 0.3`, `pdie 20`, `sdie` `ε_r,f⁰`). Pass 1 writes APBS's diel maps; ε → 3.2 on edges our mesh calls membrane where APBS's value exceeds `(pdie + sdie)/2`; pass 2 solves. Per probe ring (24 angles, trilinear): the azimuthal mean against ours, and the spread. Not gated | VAL-06; CON-04. Without the membrane the leg would measure the slab |
| D10 | Closed form | A Gaussian ring (`r_b` 1 nm, `z_b` 0.5 nm, `w` 0.1 nm) in a dielectric sphere (`a` 2 nm, ε 20) in water, grounded at `R` 20 nm. The exact potential is the three-region series of *Design* §4. APBS at 0.1 nm, with the box faces from the series, and our `P2` are each within ½ τ of it in D6's norms. Every *Design* §6 broken construction exceeds ½ τ in at least one norm | The phase plan's synthetic ring: localises an error to the driver or a solver |
| D11 | Dependency | Group `apbs` = `apbs-binary==3.4.1.1; (sys_platform == 'linux' and platform_machine == 'x86_64') or sys_platform == 'darwin'`, in `default-groups` (CI's sync lines unchanged). Run through `apbs_binary.popen_apbs` (sets macOS's `DYLD_LIBRARY_PATH`), imported in the function; absent, refused naming the group | §8.2.4 D3; CON-07 (a group never reaches a wheel); the `py3-none` wheel serves 3.11–3.14 |
| D12 | Required or skipped | `NANOPNP_REQUIRE_APBS=1` per leg on CI's Linux and macOS legs, where a missing binary fails; Windows skips visibly (`-rs`), naming the absent wheel | The WP23 D11 rule: a skip is not evidence |
| D13 | Driver and IO | `validation/apbs.py`: typed inputs, a Pydantic `Val06Report` written as JSON. A vectorised OpenDX writer (`%.10e`, three per line); APBS's output read by GridDataFormats. The deck reads a one-atom, zero-charge PQR outside the box (APBS refuses a run without `mol`). A wall-clock limit kills APBS, naming the run | `.knowledge/07` §3. gridData's writer formats each of ~7 M values in Python |
| D14 | Tiers | Tier 2: D10 and the gated 2WCD leg. `-m slow`: the 2WCD recorded leg, and a 0.05 nm focused check of ê_A's order. Tier 3, recorded: the archived ensemble (PQRs 50–99 via `inputs.pqr`), both legs | *Design* §5 |

### Work items

1. `pyproject.toml`, `uv.lock` (`uv lock`), `.github/workflows/ci.yml`: D11 and D12.
2. `validation/apbs.py`: the box and grid (D3), the charge map (D4), the diel maps and raster (D5),
   the face data (D2), the deck, the run and the reader (D13), the probes and metric (D6) and the
   report. Read *Design* §1–§3 first.
3. `tests/tier1/test_apbs_maps.py`: map construction without APBS (*Verification*).
4. `tests/tier2/test_val06_ring.py` (D10), then `tests/tier2/test_val06_2wcd.py` (D1–D8; the
   recorded leg under `-m slow`), then `tests/tier3/test_val06_archive.py` (D14).
5. `SPECIFICATION.md`: the VAL-06 NOTE's measured outcome. `CHANGELOG.md` under `v0.4.0-alpha.4`.
   `.knowledge/07` §3 for anything learnt. No public name is added.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance |
|---|---|---|---|
| `tests/tier1/test_apbs_maps.py` | 1 | VAL-06 (driver) | The charge map's sum equals the lattice's to 10⁻¹². Its first z-moment equals the lattice's to 10⁻¹² e nm, and its (x, y) dipole is 0 to 10⁻¹². A layered (z-only) raster gives each z-edge the exact harmonic mean. Each staggered origin is offset `h/2`. The writer round-trips through gridData to 10⁻¹⁰. Box refusals name the face. Importing the module imports neither `apbs_binary` nor NGSolve |
| `tests/tier2/test_val06_ring.py` | 2 | VAL-06 | *Design* §4's series. APBS at 0.1 nm and `P2` are each within ½ τ of it in all three norms; the errors are recorded. D6's metric between the two solvers is within τ. Each *Design* §6 row exceeds ½ τ in the norm named there |
| `tests/tier2/test_val06_2wcd.py` | 2 | VAL-06, FR-13, FR-15 | `seeded_protonated_2wcd`, registered as `test_charge_2wcd.py` registers it and solved with `poisson` at `P2` and `P3`. D8's budget and charge-visibility check come first, then `e_max` ≤ 3 %, `e_rms` ≤ 1 % and `e_axis` ≤ 1.5 %. The report records the probe counts, ê_A, ê_F, the three norms, the seconds and the peak RSS |
| same, `-m slow` | — | VAL-06 | The recorded leg (D9). A focused 0.05 nm grid on the lumen confirms ê_A's order |
| `tests/tier3/test_val06_archive.py` | 3, recorded | VAL-06 | The ensemble's gated-construction leg and its recorded leg, per frame and averaged. Not yet run here |

`uv run pytest tests/tier1/test_apbs_maps.py tests/tier2/test_val06_ring.py tests/tier2/test_val06_2wcd.py -v -rs`,
then the full gate.

### Out of scope

A produced χ and the exclusion shell are WP30's; D5 consumes χ when present. The GUI's charge views
are WP31's, the guide WP32's. APBS at finite ionic strength is excluded (`.knowledge/07` §3). So
are VAL-16 and VAL-17 (v1.0), OPN-07 (no golden is compared here), and the coupled models' `r`
weight (NUM-07 NOTE, open).

### Open questions

None blocking. The tolerance (D7) was ruled by the author before this commit. The close calls below
can be overruled without disturbing the rest of the plan:

- **D2, the face data from our own solution.** The far field is then ours alone, and only the
  interior is compared.
- **D9, the membrane imposed on APBS's own maps.** Without it, the recorded leg measures the slab.
- **D14, the 2WCD recorded leg under `-m slow`, not every push.** It costs two 0.1 nm APBS runs.
- **D11, `apbs` in `default-groups`.** Every development environment on a covered platform then
  carries 33 MB.
- **D6, the probe distance of 0.3 nm.** At 0.5 nm the max norm tightens to 0.77 % but goes blind to
  the first 0.5 nm next to the wall.

## Design

### 1. The box boundary [verified]

Our domain is the half-disc of radius 250 nm, with `cis` and `trans` grounded on the arc and the
membrane slab (`z ∈ ±1.4` nm, ε 3.2) reaching the arc with a natural condition on its edge
(`geometry/region.py`, `solve/state.py`). APBS poses a box with one condition on all six faces.

- `zero` grounds the faces at a few nanometres from a −60 e protein. At zero ionic strength nothing
  screens, so the potential there is tens of `V_T`, not 0.
- `sdh` and `mdh` evaluate a Coulomb or multipole sum in the solvent permittivity. Through the
  slab's ε 3.2 that far field is wrong.
- `focus` only moves the problem to a coarser box that still has one of these boundaries.

Any of them makes the difference at the probes mostly a far-field one, which is not what VAL-06
measures. `bcfl map` takes the face values from a potential map [tested]. Our `P2` solution, sampled
at the face nodes, gives APBS the boundary data of the same problem. The interior is then decided by
the charge inside and the dielectric inside, which are the two things VAL-06 hands it. Whatever
error our solution carries at the faces is shared and cancels, and the inside is compared.

The box must not let the face data carry the comparison. D8 therefore requires the charge to move
the probes by at least 10 τ_rms, measured by a run with the charge map zeroed. *Design* §6 has the
zeroed map exceed τ on the ring.

### 2. The grid and the charge map [verified, tested]

On 2WCD in the model frame, the lattice's charge occupies `r ≤ 6.45` nm and `z ∈ [−2.24, 12.84]`
nm. A cube of 19.2 nm (dime 193 at 0.1 nm, 97 at 0.2 nm) leaves at least 3.1 nm in x and y and
2.1 nm in z, so the 1 nm margin of D3 holds with room. The ensemble is checked against the same
rule, and is refused rather than cut if it does not fit.

The x and y origins are `−9.6` nm, which puts the axis on a node line. The z origin is
`z₀ = 1.35 + k·0.1` nm, with the integer `k` closest to centring the charge. The membrane faces at
±1.4 nm then lie midway between fine planes and a quarter-cell off the coarse ones, so no edge
parallel to the slab lies on it.

Each lattice node `n` at `(r_n, z_n)` carries `Q_n = a_n h_l²/e`, where `a_n` is the areal density in
C m⁻² and `h_l` = 0.005 nm. This is the trapezoid mass the deposit projects (WP28 *Design* §2).

- **In z.** `Q_n` is split between the two neighbouring planes `j` and `j+1` in the ratio
  `1 − f` to `f`, with `f = (z_n − z_j)/h`.
- **In the azimuth.** Ring `r_n` is sampled at `M = max(64, ⌈16·2πr_n/h⌉)` angles
  `θ_m = (m + ½)2π/M`. Each sample carries `1/M` of the ring and is spread to its four (x, y)
  neighbours with bilinear weights.
- **In units.** The node sums are divided by `h³` in Å³.

Each step is a partition of unity, so the map's sum is the lattice's to round-off: the spike gave
−60.000000000000 e at both spacings, as APBS's own integral also reports. The z hats reproduce
linear functions, so the first z-moment is kept. The sample angles are symmetric, so the (x, y)
dipole vanishes.

The weights are the 7-point operator's own test functions. That operator is `Q1` finite elements
with a lumped rule, and a node's right-hand side is `∫ ρ φ_j`. Each solver thus receives the charge
through its own test space, exactly up to the lattice's quadrature, as the deposit does on our side.

Point sampling would instead read `ρ` at the nodes. A hydrogen's kernel (`w` = 0.0112 nm) would then
be seen by a node only by chance, which is VAL-15's aliasing again. With the sparse matrices the
build takes 3 s at 0.2 nm and 5 s at 0.1 nm.

### 3. The dielectric maps [tested]

The permittivity is the one `poisson` assembled: `relative_permittivity_field` with the case's
solids, χ when present, and the fluid at `ε_r,f⁰`. It is sampled through the deployed mesh at the
centres of a 0.01 nm (r, z) raster reaching `r = √2 · 9.6` nm, which covers the box's corners.
The raster has 2.6 M points and took 16 s. Each map node of axis `a` lies at a grid node plus
`h/2` along `a`. Its value is `8 / Σ_s 1/ε(x + u_s e_a)`, with `u_s = (s + ½)h/8 − h/2`. That is
the harmonic mean along the edge, which makes the flux across an interface normal to the edge exact.

On the dielectric sphere (`.knowledge/07` §3), the harmonic mean halves point sampling's fluid error
at 0.1 nm (0.14 % against 0.25 %) and converges faster. An arithmetic mean over the dual face, taken
first, made it worse, so D5 does not take one. The spike's per-plane loop took 38 s at 0.1 nm, and
the implementation vectorises it over slabs.

Using the mesh's materials, and not stage 5's contour, puts the same polygonal interface in both
solvers. The remaining geometric difference is APBS's staircase of it, which is what ê_A measures.

### 4. The tolerance, and the closed form [verified, tested]

**The tolerance.** If both solvers are consistent, `|φ_A − φ_F| ≤ e_A + e_F` at every probe,
where `e` is each solver's true error.

- **APBS's estimate.** `ê_A = |φ_A(h) − φ_A(2h)|` bounds `e_A(h)` when APBS converges at first
  order or better. The sphere shows first order at worst, from the staircase, and second order in
  rms.
- **Our estimate.** `ê_F = |φ_F(P3) − φ_F(P2)|` estimates `e_F(P2)`, because `P3` is far more
  accurate on the same polygonal geometry (VER-58 rates).

Measured on 2WCD as relative norms, over 555,535 probes and the 93 on the axis:

| Norm | ê_A | ê_F | Sum | ½ τ | τ |
|---|---|---|---|---|---|
| max | 0.98 % | 0.24 % | 1.22 % | 1.5 % | 3 % |
| rms | 0.17 % | 0.01 % | 0.18 % | 0.5 % | 1 % |
| axis | 0.57 % | 0.013 % | 0.58 % | 0.75 % | 1.5 % |

The tolerance is twice an upper bound on the expected disagreement. Whatever exceeds it is a
disagreement that neither solver's discretisation explains.

The max-norm budget is the thinnest, at 1.22 % against 1.5 %. That is why D8 re-measures the
budget on every run rather than trusting this table: if the implementation's details move it past
½ τ, the test fails naming the budget, and the remedy is a finer APBS grid (focusing on the lumen),
never a wider τ.

**The ring in a dielectric sphere, grounded.** A Gaussian ring of charge `q` lies at `(r_b, z_b)`,
`b = (r_b² + z_b²)^½`, `cos θ_b = z_b/b`. Region 1 is the sphere `ρ < a`, with permittivity `ε₁`.
Region 2 is the shell `a < ρ < R`, with `ε₂`, grounded at `R`. The coordinates `ρ` and `θ` are
spherical about the centre. With `k = q/(4π ε₀)` (in `kT/e` units, `k = q·l_B⁰`, where `l_B⁰` is
the vacuum Bjerrum length), `p_l = P_l(cos θ_b)` and `β_l = k p_l b^l/ε₁`:

```
φ₁ = (k/ε₁) G(x)  +  Σ_l A_l ρ^l P_l(cos θ)
φ₂ = Σ_l (B_l ρ^l + C_l ρ^−(l+1)) P_l(cos θ)
```

`G` is the ring-averaged Gaussian kernel `⟨erf(|x − y|/w)/|x − y|⟩`, taken over the ring's angle by
a periodic trapezoid rule, which converges spectrally. For `ρ > b` it equals
`Σ (b^l/ρ^(l+1)) p_l P_l(cos θ)` to `erfc` of the gap over `w`, which is about `10⁻³⁵` here, since
the gap is 0.88 nm against `w = 0.1`. The ring's own multipoles therefore drive the reaction field
exactly. Per `l`, `A_l`, `B_l` and `C_l` solve:

```
β_l a^−(l+1) + A_l a^l           =  B_l a^l + C_l a^−(l+1)                  (φ continuous)
ε₁[−(l+1) β_l a^−(l+2) + l A_l a^(l−1)] = ε₂[l B_l a^(l−1) − (l+1) C_l a^−(l+2)]   (D·n continuous)
B_l R^l + C_l R^−(l+1)           =  0                                           (grounded)
```

As `R → ∞` this gives `C_l = k p_l b^l (2l+1)/(ε₁ l + ε₂(l+1))`, which is Kirkwood's exterior
coefficient [verified]. The `l = 0` term checks the continuity of `φ` at `a` by hand. The series is
summed to `l = 80`. Inside, it converges as `(b/a)^l = 0.56^l`, which is below 10⁻¹⁵ well before
that.

On the sphere spike (infinite `R`, `h` = 0.1 nm), APBS's fluid error is 0.14 % max and 0.022 % rms,
which is a tenth of ½ τ. That margin is what lets the broken constructions of §6 show.

### 5. Cost [tested]

The 2WCD Tier-2 test was measured on the spike, in this container with 4 cores. Neither walk pays
protonation, because the store is seeded.

| Step | Wall-clock |
|---|---|
| The `P2` walk, stages 4–12 | 19 s |
| The `P3` walk | 22 s |
| The raster | 16 s |
| The maps | 5 s at 0.2 nm and 43 s at 0.1 nm in the spike's loops; target ≤ 15 s vectorised |
| APBS | 4 s at 0.2 nm, 4 s more with the charge zeroed, 44 s at 0.1 nm |

About 2½ minutes in all. Peak memory is APBS's 1.9 GB at 193³, in a child process.

The ring test runs APBS at 65³ about ten times, at about 1 s each, plus one `P2` solve. The
recorded leg (`-m slow`) adds two 0.1 nm APBS runs, about 1½ minutes.

The Tier-3 ensemble costs 50 frames × 2 runs × 44 s, about 75 minutes, plus the gated-construction
leg once on the frame-averaged charge.

### 6. Broken constructions and the norm each must exceed

On the ring at 0.1 nm, against the series, each row must exceed ½ τ in the norm named. "Predicted"
rows are confirmed by the implementation. A row that does not fail is an Outcome, and the row is
strengthened, never dropped.

| Construction | Exceeds | Status |
|---|---|---|
| Charge map in e per node (no `1/h³`) | all | Predicted: ×10³ |
| Areal density `2πrρ` written as if a volume density | all | Predicted: the Jacobian |
| Charge point-sampled at the nodes, with the ring at `w` = 0.0112 nm | all | Predicted: the ring falls between the nodes |
| Diel values at the nodes, declared at the staggered origin | max | Tested: 2.05 % against 1.5 %, and 0.53 % rms |
| APBS `temp` 310 K against the case's 298.15 K | all | Predicted: 3.8 % |
| Charge map left 0.5 nm off in z (a frame shift not applied) | all | Predicted |
| `bcfl zero` in place of the face map | max | Predicted |
| Charge map zeroed | all | Predicted |
