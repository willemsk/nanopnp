# WP9 — External material and charge fields

**Status: delivered, 6 September 2026.** Written 5 September 2026, the third package of Phase 1, after WP7
landed the case schema, the content-addressed artefact and the provenance manifest, and WP8 landed
mesh ingestion, the vocabulary gate, the element-quality gates and the ClyA reference geometry. It
inherits a solver that runs on an *uncharged* pore: `src/nanopnp/charge/` is a one-line docstring
with no code, `solve/stage.py:290-305` calls `default_ladder` with no charge argument at all and
says so in a comment, and `io/case.py:826-835` refuses outright any case that supplies
`inputs.charge` or `inputs.eps_r`. The seams those fields must reach — `CoupledModel.residual_form`'s
`fixed_charge=` keyword, `CoupledModel.permittivity`'s `MaterialCF`, the ladder's stage-4 charge
ramp, the manifest's `charge` group — all exist and are all wired to zero.

This is the implementation plan for WP9 of `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md`
remains normative: where this file and the specification disagree, the specification governs and this
file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

Phase 1's premise is that the solver runs on inputs it did not produce (§8.1). WP8 made that true of
the mesh. WP9 makes it true of the two fields the reference model itself supplied from outside: the
smeared fixed charge `rhoq_pore(r, z)`, which COMSOL loaded as a precomputed 2D interpolation
function on a 0.005 nm grid, and the dielectric assignment, which the reference took as piecewise
constants per domain (PHY-20) and which FR-15 generalises to a field built from the density map.
Until both are ingestible, the solver can reproduce no published number that depends on the pore's
charge, which is all of them.

Four facts about the tree shape the design; all four were established by reading or running code.

- **The case schema already anticipates this package and then refuses it.** `Inputs.charge` and
  `Inputs.eps_r` exist as `SuppliedArtefact` fields, `manifest.GROUPS` carries a `charge` group, and
  both are dead: `_require_runnable` raises `UnsupportedCaseSection` on either input, and the
  manifest group is a permanent `not_run(...)`. WP9 is the package that lifts the refusal, and the
  refusal's own wording — "recording an input the solver never reads would make the FR-25 manifest
  describe a run that never happened" — is the standard it has to meet.
- **Nothing in the codebase interpolates gridded data onto a mesh.** There is no
  `scipy.interpolate` call anywhere in `src/`, no use of `gridData`, and no helper that turns a
  NumPy array plus a coordinate grid into an NGSolve coefficient function. `mesh/distance.py` is the
  nearest precedent and it *solves* for its field rather than reading one.
- **The only charge the solver can carry today is a scalar.** `default_ladder` takes
  `fixed_charge_C_m3: float` and an optional `fixed_charge_domain`, builds
  `mesh.MaterialCF({domain: density}, default=0.0)`, and ramps it 0 → target over the stage-4
  sub-rungs of the NUM-18 ladder. The ramp is exactly the machinery a gridded field needs; the
  scalar is the only thing standing in for one.
- **The mesh vocabulary has no ion-exclusion name.** `MATERIAL_VOCABULARY` is
  `analyte, cis, electrolyte, membrane, protein, trans`, and `check_solid_permittivities` aborts on
  any non-fluid material without an entry in `physics.solid_permittivities`. An ion-exclusion shell
  is neither fluid nor a solid with a permittivity of its own, so it cannot be expressed at all.

The risk this package retires is **RSK-08** (charge non-conservation through smearing and the `1/r`
projection, rated Med/Med, scheduled Phase 3). It cannot retire it, because the producer is Phase 3;
what it retires is the half that belongs to the *consumer* — the assertion on the deployed mesh, and
the decomposition that says whether a failure came from the grid it was handed or from the mesh it
was deployed on. Quantified: the reference reports `-72.9 e` integrated over its own mesh against
`-72 e` atomistic, a **1.25 % discrepancy**, twelve times QR-03's budget, with no statement of which
half of the pipeline it belongs to. WP9 builds the instrument that would have said.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Field document | `inputs.charge.path` and `inputs.eps_r.path` name a **pydantic-validated YAML header**, `schema: nanopnp/field/v1`, carrying quantity, units, grid descriptor, axis cutoff, declared `Q_net`, provenance and the *data* file it refers to; `format: field1` | The WP8 `PoreProfile` pattern, and the only way a `.dx` file can carry metadata at all — OpenDX has nowhere to put a `Q_net` or a unit. One header shape for every data format keeps the gates in one place, and `extra="forbid"` names an unknown key (IF-03) |
| Quantity vocabulary | `areal_charge_density` (the reference's `rhoq_pore`, C m⁻²), `volume_charge_density` (C m⁻³) and `solid_fraction` (dimensionless). The `1/(2πr)` division and the axis guard apply to `areal_charge_density` **only** | Applying the projection factor twice, or not at all, is the single worst silent error available here and it is invisible in the global conservation check (§Design). A declared quantity makes it a validation failure rather than a factor of `2πr` |
| Absolute `ε_r` fields | **Refused**, with a diagnostic pointing at PHY-11/PHY-12. `inputs.eps_r` supplies a *solid fraction* `χ ∈ [0, 1]` and the solver blends `ε_r = χ ε_p + (1 − χ) ε_r,f(⟨c⟩)` | An absolute `ε_r` field is static; `ε_r,f` depends on the solved `⟨c⟩`. Accepting one would silently disable the permittivity correction while reporting ePNP-NS. §4.4's "the transition **to ε_w**" is a blend by construction |
| Native format | `.npz`, float64, on the default path. OpenDX and CCP4 read *and* written through GridDataFormats **behind the `structure` extra** | CON-10's argument, applied to a second optional dependency: GridDataFormats needs Python ≥ 3.11 and the project floor is 3.10 (`.knowledge/07` §versions), so a field must be readable without it. IF-05's formats are the interchange, not the working format |
| 2D grids in 3D formats | A `(r, z)` grid is written as a 3D grid whose **third axis is a singleton**; the reader requires `shape[2] == 1` and refuses anything else naming the shape | Measured: gridData 1.2.0 round-trips `(4, 3, 1)` through both DX and MRC with origin and delta intact, and a genuinely 2D array fails inside the DX writer with `TypeError: not enough arguments for format string` (§Findings). Refusing it ourselves is the difference between a diagnostic and a stack trace |
| "CCP4" | Written through gridData's `MRC` writer, to a `.ccp4` or `.mrc` name | Measured: `file_format="ccp4"` raises `ValueError: File format CCP4 not available`; the registry offers `DX, PKL, PICKLE, PYTHON, VDB, MRC`, and MRC *is* the CCP4-2000 map format. It stores float32, so a CCP4 round trip is not bit-exact and changes the artefact hash — recorded, not hidden |
| Interpolation | `ngsolve.VoxelCoefficient(start, end, values, linear=True)` — bilinear, evaluated at quadrature points in C++ | Matches the reference's own "2D linear interpolation function" exactly. `linear=False` (nearest) is not offered: it is not what the reference did and it would make the conservation budget a function of the mesh |
| Out-of-box values | The value array is **padded with a ring of zeros** and the box extended by one spacing each way | `VoxelCoefficient` continues by the *constant* edge value outside its box, not by zero (measured, §Findings). Over a 250 nm reservoir that turns a residual edge value into a charge sheet 1056 times the grid's own footprint (§Design). Padding makes the field zero outside *and* continuous, where an `IfPos` window would make it zero and discontinuous |
| Truncation gate | Abort unless `max\|value\|` on the grid's boundary ring is below `10⁻⁴ ×` the interior maximum, naming the ring value and its `(r, z)` | The padding hides truncation; the gate is what refuses to hide it. Budget derived in §Design; PHY-16 step 4's ≥ 4σ margin gives `exp(−16) = 1.1 × 10⁻⁷`, three decades of headroom, so a grid that fails this was cut short |
| Conservation, decomposed | Report **`Q_grid` vs `Q_net`** (the producer's) and **`Q_mesh` vs `Q_grid`** (the consumer's) separately; QR-03's 10⁻³ gates both. With no declared `Q_net`, the producer check records that it could not run and the consumer check **still gates** | A single number against `Q_net` attributes nothing, which is why the reference's 1.25 % is uninterpretable. Skipping the whole assertion because its reference is absent is how a conservation failure reaches a published number |
| Per-plane check | The cumulative charge below each of a ladder of `z` planes, evaluated with a **linear ramp of width δ = 0.2 nm** applied identically to the mesh-side and grid-side integrals | A step indicator is integrated by quadrature inside the elements it straddles, at ≈ 0.2 % of `Q_net` on the reference mesh (§Design) — five times the budget it is meant to police. A ramp makes both sides one Lipschitz functional evaluated two ways, and the tolerance stays at 10⁻³ |
| Quadrature adequacy | `Q_mesh` evaluated at the `Measures` order and again at `extra_order=3`; a difference above `10⁻⁴ \|Q_net\|` aborts, naming the mesh as under-resolving the field | The conservation check is, on the deployed mesh, a quadrature-resolution check (§Design). Without this the gate reports a number it cannot defend, and NUM-07's floor is about `1/r`, not about a Gaussian of width 0.085 nm on 0.05 nm elements |
| The `2π` | Restored **in `charge/fields.py`**, once, for `Q_mesh` | `Measures.integrate` applies the `r` weight and not the `2π`; the Phase-0 rule names `io/`, `sweep/` and `gui/` as the layers that must not re-apply it, and those consume a QoI rather than produce one. A doubled or missing `2π` fails the analytic test by a factor of 6.283, which is not a tolerance question |
| Ion exclusion | A **named material**, `exclusion`, that is a *solid* for both Nernst–Planck and the flow and takes the **fluid's** `ε_r` for Poisson. `physics.solid_permittivities` does **not** require an entry for it | Making it solid for the flow puts the no-slip surface at the outer Helmholtz plane, which is the conventional shear plane (`.knowledge/02` §EDL) rather than an approximation — and it means `CoupledModel.fluid` is untouched and `permittivity()`'s `default=fluid_permittivity` already does the right thing. The region becomes a configuration of existing machinery, as `analyte` is, not a third domain partition |
| Exclusion is a deviation | Recorded as one whenever the ingested mesh carries the material, through a new **stage-contributed** deviation channel | `.knowledge/02` records that ePNP-NS has **no explicit Stern layer**, so its presence is a departure from the validated model (FR-25, §5.3.3). It is set by the mesh, not by a case-file switch, so `deviations_group`'s diff cannot see it and must be told |
| Smoothed dielectric is a deviation | Same channel, whenever `inputs.eps_r` is supplied | PHY-20 gives the validated model sharp per-domain constants. No new case-file switch is added: a switch that could disagree with the presence of the input would be a second source of truth |
| Analytic fields | A **registry of named forms** (`uniform`, `gaussian_ring`, `slab`), each with typed parameters, following `materials/models.py`'s `register` / `registered_models` / `create` | FR-16's rule generalised: a field is data, named, with provenance. A free-text expression string evaluated at solve time is arbitrary code whose provenance is a string, and `materials/forms.py` already shows what the alternative looks like |
| Grid IO lives in `density/` | `density/grid.py` holds `RadialGrid` and its readers; `charge/fields.py` and `materials/fields.py` consume it | §5.1 assigns "grid IO" to `density/` and nothing else. Putting it in `charge/` would make the dielectric field import the charge module for a container. This fills one file of a Phase-2 slot; it does not start the density pipeline |
| Stage number | One stage, **7 `charge`**, over `("case", "mesh")`, emitting `nanopnp/fields/v1` with both fields and the conservation report | §5.2's stage 7 outputs `ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface` — one row, and FR-15's whole point is that the dielectric and the exclusion contour come from the same density field. It takes the mesh because PHY-19's gate is evaluated on the deployed mesh, which the §5.1 diagram does not show |

> **Outcome — every decision above stands, and a fourth data format joined them.** The delivered
> ClyA table arrived mid-package as COMSOL's own `%Grid`/`%Data` text export, so `density/grid.py`
> gained a **`comsolgrid`** reader: read-only, coordinates in metres, and refusing a non-uniform
> axis naming it, since `VoxelCoefficient` takes a box and a shape and would otherwise resample one
> in silence. It is read-only deliberately — it is an input to the reference model, not an output of
> ours, and offering a writer would invite a round trip that is not one.

## Design

### The `2πr` cancels, and that is why the global check is not enough

The reference's assembly (PHY-16 step 6, verbatim COMSOL) is

```
scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r, z) / (2*pi*r))     [C m^-3]
```

and the conservation assertion (step 7, PHY-19) integrates it over the deployed mesh with the
axisymmetric volume element `dV = 2πr dr dz`:

```
Q_mesh = ∫_Ω ρ · 2πr dr dz = ∫_{Ω, r ≥ r_guard} rhoq_pore(r, z) dr dz
```

**The `2πr` of the Jacobian and the `1/(2πr)` of the assembly cancel identically** [verified]. Three
consequences follow, and each is a design constraint.

1. **The global check is blind to the Jacobian.** Both factors are evaluated at the same quadrature
   point with the same `r`, so an error in how `r` enters cancels exactly. What survives is the
   interpolation of `rhoq_pore` onto the mesh, the mesh's coverage of the grid's support, and the
   axis guard. This is precisely the "compensating Jacobian error" PHY-19's rationale warns of, and
   it is why PHY-19 asks for a second, localised check rather than a tighter global one.
2. **A quantity declared `volume_charge_density` gets no cancellation**, because there is no
   `1/(2πr)` to cancel against — its check *does* exercise the Jacobian. Two quantities, two
   different tests, which is a further reason the quantity is declared rather than inferred.
3. **`Q_mesh` is a planar integral of the source table**, so the target it must reproduce is
   computable on the grid alone, exactly, before any mesh exists. That is `Q_grid`, and it is what
   separates the producer's error from the consumer's.

### The three deficits, and where the budget goes

QR-03 allows `|Q_mesh − Q_net| / |Q_net| < 10⁻³`. Split it:

```
Q_net   declared by the producer (Σ_i q_i over the PQR)
Q_grid  = ∫_box rhoq dr dz             — trapezium rule on the source grid
Q_mesh  = 2π ∫_Ω ρ̃ · r dr dz            — the deployed FE mesh, at the Measures order

producer error   (Q_grid − Q_net) / |Q_net|     smearing, projection, annular volumes
consumer error   (Q_mesh − Q_grid) / |Q_grid|   interpolation, quadrature, footprint, axis guard
```

**`Q_grid` is essentially exact.** The trapezium rule applied to a smooth function that decays to
zero at both ends of the integration range has *no* Euler–Maclaurin boundary terms, so its error is
beyond all orders in the spacing rather than `O(h²)` [verified]. On a 0.005 nm grid carrying
Gaussians of width `w = σR_i ≈ 0.5 × 0.17 = 0.085 nm`, `h/w = 0.059`, and the leading correction
`(h²/12)∫∇²f` vanishes identically because `∫∇²f = 0` for a decaying `f`. So `Q_grid` may be treated
as the producer's own number, and any disagreement with `Q_net` is the producer's.

The consumer's budget is then spent on four things, in decreasing order of size.

- **FE quadrature.** `rhoq_pore` is a bilinear interpolant of a 0.085 nm Gaussian; the reference mesh
  is 0.05 nm at the pore boundary, 0.1 nm in the pore domain and 2.8 nm in the reservoir. This is
  the term that can plausibly consume the whole budget, and the only one whose size cannot be
  predicted from the grid — hence the order/`order + 3` agreement gate.
- **Interpolation.** Second-order pointwise, but the leading term of the *integral* error cancels for
  the same Euler–Maclaurin reason, so this is not expected to be visible against the quadrature term.
- **Footprint.** Charge outside the mesh, which for a 250 nm half-disc against a ~6 × 15 nm grid is
  zero, and charge outside the *grid*, which the truncation gate bounds.
- **Axis guard.** `ΔQ_guard = ∫_{r < 0.01 nm} rhoq dr dz`. The innermost ClyA atoms sit at
  `r ≳ 1.6 nm`, so the guard strip sees `exp(−(1.6/0.085)²) = exp(−354)` of peak. It is
  computed and reported rather than assumed, because a *different* structure — or an analyte on the
  axis — makes it real.

> **Outcome — the ordering was right and the size was not.** Measured on the delivered table
> (`.knowledge/04` §3.1, §3.2): the producer leg is `4.7 × 10⁻¹²` (`Q_grid = −71.999999999663 e`
> against a declared `−72 e`), the ring ratio `8.5 × 10⁻²⁴`, the guard deficit `1.4 × 10⁻⁶⁸ e` —
> the last three exactly as predicted, with decades to spare. FE quadrature did not "plausibly
> consume the whole budget": on the WP8 reference mesh it consumed **ten times** it, at
> `+9.868 × 10⁻³`, and **it does not converge**. Refining `h` to 3,463,372 elements made it
> *worse* (`−1.062 × 10⁻²`, non-monotone in between); raising the order from 8 to 37 oscillated
> without settling. The table's radial structure alternates sign 49 times along its densest `z`,
> with extrema a median 0.035 nm apart — below element scale, so the quadrature is aliased rather
> than inaccurate. The tolerance was **not** slackened: the quadrature-agreement gate fires first,
> at `9.273 × 10⁻³` against its own `10⁻⁴`, and reports that the mesh under-resolves the supplied
> field. The remedy is the producer's (deposit onto the FE space and rescale) and is v0.9's stage 7.
> §4.4 of the specification gains a NOTE saying all of this normatively.

### Why the grid must be padded, not clamped

`ngsolve.VoxelCoefficient` "will be continued by a constant function outside of this box" — the
clamped edge value, not zero (measured, §Findings). Take the reference footprint: the mesh is a half
disc of radius 250 nm, area `πR²/2 = 98 175 nm²`; a charge grid covering `r ∈ [0, 6]`,
`z ∈ [−2.5, 13]` has area `93 nm²`. The extension amplifies the edge value over an area **1056
times** the grid's own. For the leaked charge to stay under QR-03's budget,

```
ε_ring / mean_interior  <  10⁻³ × 93 / 98 175  =  9.5 × 10⁻⁷
```

— a criterion no producer states and none should have to meet. Padding with a ring of zeros and
extending the box by one spacing makes the continuation exactly zero and keeps the coefficient
function continuous, which an `IfPos` window would not.

The gate then bounds what the padding threw away. With a ring maximum `M_ring ≤ 10⁻⁴ M_interior`
and an outward decay length of at most `w_max ≈ 0.1 nm`, the discarded charge is at most
`M_ring × perimeter × w_max = 10⁻⁴ M × 43 nm × 0.1 nm = 4.3 × 10⁻³ M nm²` against
`Q_grid ≈ M × A_eff` with `A_eff` of order 20 nm² — that is `2 × 10⁻⁵` of `Q_grid`, a fiftieth of
the budget. PHY-16 step 4's "extend ≥ 4σ_max beyond the protein" delivers `exp(−16) = 1.1 × 10⁻⁷`,
so a compliant grid clears the gate by three decades and a truncated one does not.

### The per-plane check needs a ramp, not a step

PHY-19 asks for a per-`z`-slice cumulative check because a globally satisfied check can hide
compensating local errors. The obvious implementation — `Integrate(ρ · r · IfPos(z_k − z, 1, 0))` —
integrates a discontinuous function, and NGSolve's quadrature does that inside every element the
plane crosses. Size it on the reference mesh: the protein spans ≈ 14 nm in `z`, elements at the
pore boundary are 0.05–0.1 nm, so a plane crosses a band holding ≈ 0.7 % of `Q_net`, and a Gauss
rule misplaces a substantial fraction of a straddled element's contribution. **≈ 0.2 % of `Q_net`**
is the resulting noise floor — five times the tolerance the check is supposed to enforce.

Replacing the step by a linear ramp of width `δ` centred on `z_k`,

```
W_k(z) = clamp( (z_k + δ/2 − z) / δ , 0, 1 )
```

makes both sides Lipschitz. The mesh side integrates `ρ̃ W_k` at the `Measures` order; the grid side
integrates `rhoq · W_k` by the trapezium rule on the 0.005 nm grid. Both evaluate *the same
functional*, so the comparison stays at QR-03's 10⁻³ and the smoothing cancels out of it entirely.
`δ = 0.2 nm` is two to four times the local element size on the reference mesh, which is the
condition for the quadrature error to be negligible while `δ` stays far below the 14 nm over which
the cumulative varies.

What the check localises is unchanged: a region where the mesh cannot carry the smeared charge shows
up as a deficit at the planes bracketing it, whether or not a surplus elsewhere cancels it globally.

### The dielectric blend

PHY-20 assigns `ε_r` per domain: 20 in the protein, 3.2 in the membrane, `78.15 · f^c(⟨c⟩)` in the
electrolyte. `CoupledModel.permittivity` implements exactly that, as
`mesh.MaterialCF(solids, default=fluid_permittivity)` with every value divided by `ε_r,f⁰ = 78.15`.
§4.4 additionally requires the dielectric contour to be built from the density field "with the
transition to `ε_w` smoothed over 1–2 Å".

A smoothed transition **to `ε_w`** cannot be a static `ε_r` field, because `ε_w` is
`ε_r,f⁰ · ε_r,f^c(⟨c⟩)` and `⟨c⟩` is solved for. The only formulation consistent with both PHY-20 and
PHY-11/PHY-12 is a blend on a solid fraction `χ`:

```
ε̃_r(r, z) = χ(r, z) · ε_p/ε_r,f⁰  +  (1 − χ(r, z)) · ε̃_r,f(⟨c⟩)
```

with `χ = 1` inside the protein, `0` in the fluid, and the 1–2 Å transition carried by `χ` alone.
Setting `χ` to the sharp material indicator recovers the piecewise `MaterialCF` exactly, which is
the Tier-1 assertion. `ε_p` continues to come from `physics.solid_permittivities`, so the mesh still
carries the material split and Nernst–Planck is still not solved inside the protein; the field
smooths the coefficient, not the domain.

Two gates, both cheap and both aimed at the failure that actually happens — a field written with `r`
and `z` transposed, or with the sense inverted:

- `0 ≤ χ ≤ 1` everywhere on the deployed mesh, aborting with the offending value and its `(r, z)`.
- The **mean of `χ` over each material**: above 0.9 on every solid, below 0.1 on every fluid
  material, aborting with both numbers. An inverted or grossly misregistered field fails this by
  construction; a 1–2 Å transition moves neither mean by more than a percent.

### Gouy–Chapman–Stern: the closed form the exclusion region is checked against

An ion-free layer of thickness `λ_S` against a charged plane wall, with `ε_r` unchanged across it,
carries no space charge, so `φ` is linear there and `E = σ_s/(ε₀ε_r)` is constant. At the outer
edge, Gouy–Chapman applies unchanged with the same `σ_s`. Hence

```
φ_0 = φ_d + σ_s λ_S / (ε₀ ε_r) ,     σ_s = √(8 ε₀ε_r R T c₀) · sinh(ζ̃_d/2)   (Grahame, VER-12)
```

Worked at the conditions VER-12 already uses — 0.1 M, `ζ̃_d = 2`, `T = 298.15 K`, `ε_r = 78.15`, and
`λ_S = a_Na/2 = 0.25 nm` from `willems2020_nacl`'s `steric_diameter_nm: 0.5` [verified]:

| quantity | value |
|---|---|
| `V_T = RT/F` | 25.6926 mV |
| `λ_D` | 0.95984 nm |
| `φ_d = 2 V_T` | 51.385 mV |
| `σ_s = √(8εRTc₀) sinh 1` | 0.0435363 C m⁻² |
| `Δφ_S = σ_s λ_S/ε` | 15.729 mV |
| **`φ_0`** | **67.114 mV** |

The Stern layer raises the wall potential by **30.6 %**. An exclusion region that is silently
ignored — because nothing restricts the ion space to it, or because the material fell through to the
fluid set — returns 51.4 mV, which no tolerance forgives. Setting `λ_S = 0` must reproduce VER-12
exactly, on the same mesh, which is the second half of the test.

Recorded as a caveat rather than hidden: the exclusion shell and the PHY-02 ion wall function
`f^w = 1 − exp(−6.2(d̄ + 0.01))` model overlapping physics — both suppress ion presence near the
wall — and with the shell present, `d` is measured from the shell's outer surface, since that is the
boundary named `wall` in the mesh. This is a further reason the region is off by default and
recorded as a deviation when it is not.

## Findings this plan established by running code

All on NGSolve 6.2.2606 and GridDataFormats 1.2.0, in this repository's environment. **[tested]**

1. **`VoxelCoefficient`'s value array is indexed `[axis-2, axis-1]`, not `[axis-1, axis-2]`.** For a
   2D grid over `(r, z)` the array must be `values[i_z, i_r]`. Passing the transpose raises nothing:
   a field built to be `10r + z` returned 1.0 at `(r=1, z=0)` where 10.0 was intended, and **agreed
   exactly** at the symmetric sample `(0.5, 0.5)` — so a test that samples on the diagonal passes on
   a transposed field.
2. **`VoxelCoefficient` continues by the clamped edge value outside its box**, in every direction,
   as its docstring says and as measured at `r` and `z` beyond the box. Not zero.
3. **gridData 1.2.0 round-trips a `(4, 3, 1)` grid** through OpenDX and MRC with `origin` and `delta`
   preserved, and **fails on a genuinely 2D array** with `TypeError: not enough arguments for format
   string` raised from inside the DX writer.
4. **gridData has no `CCP4` writer.** `file_format="ccp4"` raises
   `ValueError: File format CCP4 not available, choose one of dict_keys(['DX', 'PKL', 'PICKLE',
   'PYTHON', 'VDB', 'MRC'])`. `MRC` writes the CCP4-2000 map format and accepts a `.ccp4` filename;
   it stores float32.

5. **`extra_order=3` on a singular form is not a refinement.** `Measures.bonus_order(singular=True)`
   takes `max(extra, 3)` — NUM-07's floor for a form carrying `1/r` — so the quadrature-agreement
   gate as this plan specified it would have compared a value with itself and passed
   unconditionally. `extra=0` and `extra=3` both return `−71.289538 e`, bit-identical; `extra=6`
   returns `−71.957178 e`. The gate as built asks for enough extra orders to clear the floor.

Each of these goes into `.knowledge/` at implementation time — 1, 2 and 5 into `06-numerics-fem.md`
§8.1 beside the other silent NGSolve traps, 3 and 4 into `07-software-stack.md`.

> **Outcome — all five recorded, and §8.1 gained a section of its own.** Findings 1, 2 and 5 are
> traps 16, 17 and 18 in `06-numerics-fem.md` §8.1; 3 and 4 are in `07-software-stack.md` §2. The
> non-convergence above is `06` §8.1.1, because it is not a trap in an API but a property of the
> problem: a mesh integral of a sub-element-scale field converges in neither `h` nor order.

## Work items

| File | Delivers | Identifiers |
|---|---|---|
| `density/grid.py` | `RadialGrid` (origin, spacing, `values[i_z, i_r]` float64, units, `.extent`, `.planar_integral()`, `.cumulative(planes, ramp_nm)`, `.boundary_ring_maximum()`, `.padded()`); `read_grid(path, *, format=None)` and `write_grid(grid, path, *, format)` over `.npz` on the default path and OpenDX/MRC behind the `structure` extra, with the singleton-third-axis convention and our own diagnostic for a 2D array; `coefficient(grid)` building the padded `VoxelCoefficient` with the axis order asserted | IF-05, §5.1 |
| `charge/fields.py` | `FieldDocument` (`nanopnp/field/v1`, `extra="forbid"`), `QUANTITIES`, `load_field(path)`; `ChargeField.assemble(mesh, scales)` → the axis-guarded dimensionless `ρ̃`; `ConservationReport` and `conservation(field, mesh, measures)`; `check_conservation(...)` raising `ChargeFieldError(gate, quantity, location)`; the named analytic-form registry | QR-03, PHY-18, PHY-19, FR-14 (mesh half), FR-27 |
| `materials/fields.py` | `SolidFractionField`; `blend(chi, protein_permittivity, fluid_permittivity)`; the range gate and the per-material mean gate; the refusal of an absolute `ε_r` field naming PHY-11 | FR-15 (consumer half), PHY-20 |
| `charge/stage.py` | `FieldStage`, stage 7, over `("case", "mesh")`, emitting `FieldsArtefact`; `key(inputs)` beside `run(inputs)`; progress and cooperative cancellation between the two fields and the gates | FR-27, IF-01 |
| `io/artefact.py` (edit) | `FIELDS_SCHEMA = "nanopnp/fields/v1"` and `FieldsArtefact`, parameters carrying the grid descriptor and the value array's digest, the data file as payload | §5.3.2 |
| `io/case.py` (edit) | Lift the `inputs.charge` / `inputs.eps_r` refusal; `ResolvedCase` gains both; the `charge:` *section* stays refused, being the v0.9 producer | IF-03 |
| `io/manifest.py` (edit) | The `charge` group populated from the conservation report — source, hash, quantity, units, grid descriptor, `Q_net`, `Q_grid`, `Q_mesh`, the two relative errors, the guard deficit, the ring maximum, the worst plane and its `z`, the interpolation kernel, and whether the producer check ran; `deviations_group(document, *, contributed=())`; the group's stale `not_run` reason corrected from "stages 4 and 5, FR-08 to FR-11" to stage 7, FR-12 to FR-15 | FR-25, IF-08 |
| `mesh/ingest.py` (edit) | `exclusion` in `MATERIAL_VOCABULARY`, exempt from `check_solid_permittivities`; its presence contributed as a deviation | IF-06, PHY-03 |
| `physics/models.py` (edit) | `permittivity()` accepts a blended fluid branch; the unassigned-material warning exempts `exclusion` | PHY-20 |
| `solve/continuation.py` (edit) | `default_ladder(..., fixed_charge_field=None)` in SI C m⁻³, divided by `Scales.charge_density_C_m3` and multiplied by the stage-4 `fraction`, mutually exclusive with `fixed_charge_C_m3` | NUM-18 |
| `solve/stage.py` (edit) | The fields artefact taken from `upstream` or computed, threaded into the ladder, and entering the digest by its content hash | §5.3.2, FR-27 |
| `core/stages.py` (edit) | `register(StageDescription(name="charge", number=7, …), "nanopnp.charge.stage:FieldStage")` | FR-27, IF-01 |
| `mesh/primitives.py` (edit) | `SlabGeometry(..., exclusion_nm=0.0)` — an ion-free layer against the charged wall, for VER-31 | VER-31 |

> **Outcome — every row delivered, plus three the plan did not foresee.**
> `core/paths.py` gained `reference_data_root()` and `reference_file(name)` over
> `$NANOPNP_REFERENCE_DATA`, because the delivered table is 77 MB and no reduction of it is a fair
> reference — cropping at a `10⁻⁶` relative threshold still costs 28 MB, and subsampling by four
> moves the planar integral by 1.5 %, fifteen times QR-03's budget. `density/grid.py` gained the
> `comsolgrid` reader. `tests/tier3/test_reference_charge_map.py` is the Tier-3 file those two
> exist for, and it skips rather than fails where the archive is absent (§7.1 NOTE).
> `mesh/primitives.py`'s `SlabGeometry(..., exclusion_nm=…)` landed as planned.

`RadialGrid` is the seam behind every gridded field: the charge table, the solid fraction, and (in
Phase 2) the reduced density map all become one, and nothing downstream of `density/grid.py` knows
which format it arrived in. It is the field analogue of what `MeshData` did for the meshers.

## Specification changes in this commit

- **A. §5.3.1's `inputs:` example gains `charge:` and `eps_r:`, and a NOTE defines the field
  document.** `nanopnp/field/v1`: quantity from `{areal_charge_density, volume_charge_density,
  solid_fraction}`, units, grid descriptor, axis cutoff (default 0.01 nm, PHY-18), optional `Q_net`,
  provenance, and the data file. The NOTE states that the `1/(2πr)` projection and the axis guard
  apply to `areal_charge_density` only, that an absolute `ε_r` field is refused because it cannot
  carry PHY-11's concentration dependence, and that the interpolant is zero outside the grid box.
- **B. §5.3.1's mesh vocabulary gains `exclusion`,** with a NOTE: it is a solid for Nernst–Planck and
  the flow and takes the fluid's `ε_r` for Poisson, so `physics.solid_permittivities` requires no
  entry for it; the no-slip surface then sits at the outer Helmholtz plane, which is the
  conventional shear plane; ePNP-NS has no explicit Stern layer, so its presence is a deviation from
  the validated model and is recorded as one (FR-25).
- **C. §4.4 gains a NOTE on the dielectric blend**: `ε_r = χ ε_p + (1 − χ) ε_r,f(⟨c⟩)`, the
  arithmetic showing that the sharp `χ` reproduces PHY-20's piecewise assignment exactly, and the
  refusal of an absolute field.
- **D. §4.4 / PHY-19 gain a NOTE on the cancellation**: the `2πr` Jacobian and the `1/(2πr)`
  assembly cancel identically, so the global conservation check is blind to the Jacobian; the check
  is therefore decomposed into a producer part (`Q_grid` against `Q_net`) and a consumer part
  (`Q_mesh` against `Q_grid`), both gated at 10⁻³, and the per-plane cumulative uses a ramped
  indicator of stated width so that both sides evaluate one functional.
- **E. §5.2's stage-7 row records that on the consumer path the stage takes the deployed mesh as an
  input**, because PHY-19's gate is evaluated on it — which the §5.1 diagram does not show.
- **F. §7.2 gains VER-29, VER-30 and VER-31**, as below.
- **G. Appendix A**: IF-05 gains VER-29 (it reads "None yet" today), QR-03 gains VER-29 beside
  VER-01, FR-14 gains VER-29 for its mesh half, FR-15 gains VER-30 and VER-31 beside VAL-06. The
  coverage sentence under the table moves from 35 of 67 to 36.
- **H. §10 gains OPN-06**, the attribution of the reference's own 1.25 % conservation gap — open
  question 2 below, recorded where the other open items live so that WP13 does not have to
  rediscover it.

> **Outcome — A to H all landed in the plan commit; implementation added four more.** §7.1 gains a
> NOTE on why Tier-3 reference files are named by `$NANOPNP_REFERENCE_DATA` rather than vendored,
> with the crop and subsample figures that rule out a shipped fixture. §5.3.1's field-document NOTE
> gains the `comsolgrid` format and the uniform-axis requirement. §4.4 gains the NOTE on the
> consumer leg being a resolution question rather than a tolerance one, with the refinement and
> quadrature-order tables, and states normatively that the tolerance is **not** slackened for it.
> §7.4 gains **VAL-15**, and OPN-06 is rewritten as closed.

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_charge_fields.py` | 1 | VER-29, QR-03, IF-05, IF-03 | A `RadialGrid` round-trips through `.npz`, OpenDX and MRC with origin, spacing and values preserved (the last two skipped without the `structure` extra), and a 2D array is refused by us naming the shape; the interpolant reproduces the non-symmetric field `10r + z` at off-diagonal sample points, so a transposed array fails; the field is exactly zero one spacing outside the box; an unknown key in the field document is rejected naming the key; conservation against an analytic `Q_net` on a coarse mesh; the ring gate fires naming the ring value and its `(r, z)`; a field with no declared `Q_net` gates on `Q_mesh` against `Q_grid` and records the producer check as not run |
| `tests/tier1/test_dielectric_field.py` | 1 | VER-30, FR-15, PHY-20 | `χ` outside `[0, 1]` aborts naming the value and its location; an inverted `χ` aborts on the per-material means, reporting both; the sharp `χ` reproduces `MaterialCF` to round-off at every quadrature point; an absolute `ε_r` field is refused with PHY-11 named |
| `tests/tier2/test_charge_conservation.py` | 2 | VER-29, QR-03, PHY-19 | On the WP8 ClyA reference mesh, a synthetic field of Gaussian rings whose exact `Q_net = e Σ q_i` is known analytically conserves to better than **10⁻³** on both the producer and consumer legs; every ramped plane cumulative agrees to **10⁻³** of `\|Q_net\|`; the order / `order + 3` quadrature agreement is better than **10⁻⁴ \|Q_net\|`, and a deliberately coarsened mesh fails that gate rather than the conservation gate |
| `tests/tier2/test_stern_layer.py` | 2 | VER-31, FR-15 | Gouy–Chapman–Stern on the slab: `φ_0 = φ_d + σ_s λ_S/(ε₀ε_r)` to better than **1 %** at 0.1 M, `ζ̃_d = 2`, `λ_S = 0.25 nm` — a 30.6 % effect, so a shell that is silently fluid fails by 24 %; `λ_S = 0` reproduces VER-12 on the same mesh to solver tolerance |
| `tests/tier1/test_manifest.py` (edit) | 1 | FR-25, IF-08 | The `charge` group is populated rather than `not_run` when a field is supplied, and carries both conservation legs; a stage-contributed deviation appears under Deviations without a case-file switch existing for it |
| `tests/tier1/test_stages.py` (edit) | 1 | VER-25, FR-27 | Stage 7 describes itself without importing `nanopnp.charge.stage`, reports monotone progress, and leaves no artefact on cancellation |

New verification items for §7.2:

- **VER-29 — External field ingestion and charge conservation.** A `(r, z)` grid round-trips through
  the native and interchange formats with the singleton-axis convention, and a 2D array is refused
  naming its shape; the interpolant's axis order is asserted against a field that is not symmetric
  in its arguments; the field is zero outside the grid box; on the deployed finite-element mesh
  `|Q_mesh − Q_net|/|Q_net| < 10⁻³`, decomposed into a producer leg against `Q_grid` and a consumer
  leg, each gated separately, with the axis-guard deficit and the boundary-ring maximum reported;
  the ramped per-plane cumulative agrees to the same tolerance at every plane; a grid whose ring
  maximum exceeds `10⁻⁴` of its interior maximum aborts naming the value and its location; a field
  declaring no `Q_net` gates the consumer leg and records the producer leg as not run (QR-03,
  PHY-18, PHY-19, IF-05, FR-14 in part).
- **VER-30 — Dielectric blend.** The sharp solid fraction reproduces PHY-20's piecewise assignment
  to round-off; `χ` outside `[0, 1]` and an inverted `χ` both abort with the quantity and its
  location; an absolute `ε_r` field is refused with PHY-11 named (FR-15).
- **VER-31 — Gouy–Chapman–Stern.** With an ion-exclusion layer of thickness `λ_S` against the
  charged wall, the wall potential is `φ_d + σ_s λ_S/(ε₀ε_r)` to better than 1 %, and `λ_S = 0`
  reproduces VER-12 on the same mesh (FR-15).

> **Outcome — the tests landed as specified, with two identifiers moved.** **VER-31 sits in §7.3,
> not §7.2**: it is a closed-form analytic benchmark that extends VER-12, its test is Tier 2, and
> §7.2 is the Tier-1 section — VER-26 is the precedent for a Tier-2 item appearing there out of
> numeric order. And the Tier-3 file needed an identifier of its own: it compares the *reference
> model's own table* on our mesh, which is not VAL-06 (potential against APBS), so **VAL-15** was
> added to §7.4 and Appendix A's IF-05, QR-03 and FR-14 rows cite it.
>
> Green on the current tree: **551 passed, 1 skipped** in 104 s (Tiers 1 and 2; the skip is
> `test_mesh_quality.py`'s gmsh backend, which needs `libGLU.so.1` and predates this package). The
> four Tier-3 tests pass in 14.6 s with the archive present and skip without it.

> **Outcome — two of these tests were measurements of the platform, and the CI matrix said so.**
> Both landed green on Linux/3.12 and failed elsewhere, and both were the same mistake in different
> clothes: asserting on a number that is a property of the environment rather than of the code.
>
> **VER-29's coarsened-mesh gate was a measurement of netgen's mesher.** The order/order+3 agreement
> at `maxh = 0.2 nm` read 2.3e-4 on Linux, 7.8e-5 on Windows and 2.2e-5 on macOS — the same field,
> the same box, three different unstructured triangulations, straddling the 1e-4 gate three ways.
> Coarsening is not the repair: §8.1.1's non-monotonicity in `h` means it only re-rolls the dice.
> The mesh is now `MakeStructured2DMesh` at `(27, 70)` — 0.222 × 0.221 nm — where every vertex is
> placed arithmetically and the number is the same everywhere: legs 1.9e-4 at worst (five times
> inside QR-03), agreement 3.7e-4 (nearly four times over its gate). Recorded as
> `.knowledge/06` §8.1.2.
>
> **VER-29's CCP4 round trip was a measurement of the resolver.** GridDataFormats 1.2 requires
> Python ≥ 3.11, so on 3.10 the resolver takes 1.0.2, whose exporter registry has no `MRC` entry: it
> reads MRC and CCP4 and writes neither. The test's `needs_griddata` guard was the wrong predicate —
> 1.0.2 *imports* fine — so 3.10 got a third-party `ValueError` out of `Grid.export`. `write_grid`
> now checks the exporter registry and refuses in QR-12 terms (format, installed version, the
> release that gained the writer), `writable_formats()` exposes the capability for FR-27, and the
> test asserts the refusal on the branch where the writer is absent rather than skipping — so 3.10
> and 3.11+ each assert something. IF-05 gained the NOTE saying its write side is conditional and
> why QR-09's 3.10 floor is the larger promise. Recorded as `.knowledge/07`.

Gate before the package is done, as every package:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

## Out of scope

- **The producer.** PDB2PQR, protonation, per-atom smearing, azimuthal projection over annular
  volumes, and the density map they share with the geometry — FR-12, FR-13 and the producer halves
  of FR-14 and FR-15, all Phase 3 (v0.9). WP9 consumes a field somebody else made.
- **VER-01 and VER-02 proper.** VER-01 is the producer's conservation and VER-02 is the per-z-slice
  cumulative *against the PQR sorted by z*. WP9 delivers the consumer's counterpart of both —
  against `Q_grid` and against the source grid's own cumulative — which is what can be checked
  without a charge list. Both keep their Phase-3 owners.
- **3D density maps.** `RadialGrid` is two-dimensional. Reading a genuinely 3D map, and the
  azimuthal reduction that turns one into an `(r, z)` grid, are stage 3 and Phase 2.
- **The exclusion offset.** How far outward the exclusion contour sits from the dielectric contour is
  a producer parameter (FR-15, "independently configurable exclusion offset"). WP9 consumes a mesh
  that already carries the region; it does not construct one from a density field.
- **Surface charge from structure.** `residual_form`'s `surface_charge=` seam exists and stays as it
  is; a fixed surface density on a named boundary is not a field artefact.
- **Boundary layers.** Ruled out for this package on 5 September 2026 (phase plan, WP9): WP8 reached
  the published quality band by isotropic grading alone, so nothing here reopens FR-11.

## Open questions

> **Outcome — all three answered, 6 September 2026, by the author delivering the table.** It arrived
> during implementation as `prod5_clya_charge`, COMSOL's `%Grid`/`%Data` export of the published
> model's own `rhoq_pore`. The measurements are in `.knowledge/04` §3.1 and §3.2 and are not
> repeated here; the answers are below, in place.

1. **Is there a real `rhoq_pore` grid from the COMSOL model that could ship as a fixture?**
   **Yes to the grid, no to the fixture.** The delivered table is 1401 × 3401 at 0.005 nm — 77 MB
   of text — and nothing survives being made small enough to vendor: a `10⁻⁶`-threshold crop keeps
   `1.1 × 10⁻⁷` relative accuracy but still weighs 28 MB, and subsampling by four costs
   `1.5 × 10⁻²` on the planar integral, fifteen times the budget it would be used to check. It is
   therefore an **archived Tier-3 reference**, located by `$NANOPNP_REFERENCE_DATA`, with the tier
   skipping where it is absent (§7.1 NOTE). The Tier-2 conservation test keeps its synthetic field,
   which is the right thing regardless: its `Q_net` is exact by construction.

2. **Does the reference's `−72.9 e` against `−72 e` (1.25 %) belong to the producer or the
   consumer?** **The consumer's.** The delivered table's own planar integral is
   `−71.999999999663 e` — the *integer* −72, to `4.7 × 10⁻¹²` — so the producer leg is not where
   1.25 % went, and Ruling 8's "different constructs" reading does not hold on this axis. Our own
   consumer leg on a comparable mesh is `−0.99 %` by the same interpolate-and-integrate route: same
   size, same character, opposite sign, which is what aliasing does rather than what lost charge
   does. **OPN-06 is closed in the specification** on those numbers, and any Tier-3 comparison of
   pore charge (VAL-06, WP13) is now a comparison of two consumer legs, with ours gated ten times
   more strictly than the reference achieved.

3. **Units of the delivered table.** **`e/m²` — there is no `e` inside the file.** The integral
   being the integer −72 rather than `−72 × 1.6 × 10⁻¹⁹` settles it: the stored sum is in units of
   `e`, and the COMSOL assembly's `e_const` supplies the coulombs exactly once. `.knowledge/04`
   §3's transcription of eq. `eq:scdpore` with an `e` inside the sum is the published expression and
   not the file; implementing it literally and then applying `e_const` double-counts. **G5 and G10
   both close on this table** (§8 of that file).

One scope note rather than a question, recorded as written: the ion-exclusion material and its
Gouy–Chapman–Stern benchmark are the natural cut line if this package proves too large for one PR. They are independent
of the field-ingestion work — a different vocabulary name, a different test, no shared code beyond
the mesh — and everything Phase 1's completion criteria need is on the other side of that line.

> **Outcome — the cut line was not needed.** Both halves shipped in one package: field ingestion
> and the decomposed conservation gate, and the `exclusion` material with VER-31 behind it.
