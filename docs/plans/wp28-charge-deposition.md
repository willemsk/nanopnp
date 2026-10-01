# WP28 — Fixed-charge deposition on the deployed mesh and its gates (FR-13, FR-14)

**Status: planned, not started.** Planned 1 October 2026, on `main` at `09e1c4d` (WP27 merged and
tagged `v0.4.0-alpha.2`). The third package of Phase 3. It inherits WP27's `ProtonationTable` and
`protonated_2wcd`, WP26's model declarations (a charge is produced only for a model declaring
`fixed_charge`), the consumer path's `ConservationReport` and gates (VER-29, the §4.4 NOTEs), WP21's
`deployed_mesh`, stage 5's model frame (`geometry/region.py`, `to_model_frame`) and the frozen
schema v2 (§8.2.2 B3).

This plan belongs to [Phase 3](phase-3-charge-pipeline.md). `SPECIFICATION.md` governs; identifiers
here are pointers into it. The spec amendments this package needs are made in this plan's commit:
FR-13 (it still named the annular-volume construction that §8.2.4 D2 replaced), a PHY-16 NOTE on the
deposition as run, a §4.4 NOTE on the producer path's conservation report, the §5.3.1 NOTE on
`charge.smearing`, the §5.3.2 row for stage 7 and RSK-08's mitigation. The kernel's lattice
measurements they rest on are in `.knowledge/04` §3.3.

## Execution brief

**Scope.** Stage 7 becomes a producer: it sums PHY-16 step 5's closed-form kernel over the
`protonation` artefact's atoms and frames on the 0.005 nm export lattice, deposits the sum on the
deployed mesh as an element-wise polynomial by `r`-weighted L² projection, and gates it. A
`structure:` or `inputs.pqr` case then protonates and solves charged by default. Discharges FR-13,
FR-14 and QR-03's producer path; retires RSK-08; adds VER-01 and VER-02 in full, and VER-58. The
brief runs past its target because the consumers of a produced charge (D9) and two existing walks
(D14) change with it; deferring either leaves a `structure:` case solving uncharged.

**Read first.** PHY-16 to PHY-19 and the §4.4 NOTEs; §5.3.1 NOTE on `charge.smearing`;
`.knowledge/04` §3–§3.3; `.knowledge/06` §8.1.1.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Kernel | PHY-16 step 5 with `scipy.special.i0e`, `w_i = sharpness · R_i`; `q_i = 0` skipped; a square patch of half-width `6 w_i` (tail `1 − erf(6)² = 4.3 × 10⁻¹⁷`), renormalised on the lattice to `q_i / n_frames` | PHY-18; *Design* §1 |
| D2 | Export lattice | Areal `2πr ρ̄` (C m⁻²) as a `RadialGrid` at `grid_spacing_nm`, a node on `r = 0`, box = atoms ± `6 w_max` snapped outward. **Model frame**: `to_model_frame` with `centre_z_nm` on a generated mesh, no shift on a supplied one. One sparse product of the separable factors per frame. Spacing > `½ min w_i` refused naming the atom | PHY-16 step 6; stage 5's frame; *Design* §1 |
| D3 | Deposition space | Discontinuous `P_k`, **`k` = the potential's order** (2 by default), scaled monomials about each centroid; moments by the lattice trapezoid rule, each node in one element (lowest index on a shared edge) | Galerkin-exact source, *Design* §2 |
| D4 | Placement | Every element of every material, as the reference (`.knowledge/04` §3). Refused: node mass outside every element > 10⁻¹² of the largest, naming (r, z); under half of `Σ\|q_i\|` centred in solids, naming the share and the shift. Shares recorded | A mesh hole or a frame mismatch would otherwise move charge silently |
| D5 | Transfer | Payload: coefficients (`elements × basis`), `k`, element-geometry digest. `charge/` sets an NGSolve `L2(order=k)` GridFunction (NGSolve imported in the function) behind `ChargeField`'s interface (`volume_density_C_m3`, `assemble`). `MeshData` order = NGSolve's, asserted; another digest refused naming both | QR-13 |
| D6 | Report | Producer leg: export integral against `Q_net` (frame mean). Consumer leg: `Measures.integrate` of the deployed field at the solve's order. Quadrature and ring as today. Per plane the **source atoms** are the reference, in closed form, under `½ erfc((z − p)/s)`, `s = 0.5` nm, 12 planes over the atoms' z-extent; grid and mesh each gated at 10⁻³ against it. The re-read guard deficit is recorded | PHY-19, VER-02; *Design* §3 |
| D7 | Keys | `nanopnp/charge-grid/v1`, keyed on protonation, sharpness, spacing, truncation, frame shift and kernel id, not the mesh. The stage-7 `FieldsArtefact` gains inputs `protonation`, `charge_grid`; `fields.charge` records `source: deposited` and `k`; `gates` add planes and `s`. `charge` joins `STORE_STAGES`. Payload `charge.yaml` (`field1`, `q_net_e`, `axis_cutoff_nm: 0.01`), `charge.npz`, `deposit.npz` | §5.3.2; a `size_scale` sweep re-deposits, never re-sums |
| D8 | Walk | `protonation` and `charge` run when the case protonates and the model declares `fixed_charge`, else are recorded not run with the reason (WP27 D3 retired). `inputs.pqr` with a model lacking it is refused naming the model. `upto="mesh"` never protonates | WP26's live rule |
| D9 | Consumers | Solve, `restore` and the `ρ_fixed` export read a produced charge only from the stage-7 artefact handed down, through one loader in `charge/stage.py`; none handed down on a producer case is refused naming stage 7. Supplied path unchanged | The reads at `solve/stage.py`, `solve/state.py`, `post/stage.py` are `inputs.charge` |
| D10 | Case keys | `sharpness` → `SWITCH_PATHS` (0.5); `grid_spacing_nm` → `CONFIGURATION_PATHS`; `axis_cutoff_nm` away from default refused everywhere, naming PHY-18. Smearing keys beside `inputs.charge`, or with neither `structure:` nor `inputs.pqr`, refused naming both keys | §5.3.1 NOTE on `charge.smearing` (amended here) |
| D11 | Export, manifest | `stage charge --export X.yaml` writes the `field1` document and its `.npz`, re-read by `inputs.charge` to the same digest; `.dx`/`.mrc` the grid (IF-05). The *Charge* group: report, `Q_net`, shares, counts, timings | FR-25, IF-05 |
| D12 | Cancellation | Between frames, before the projection and before each gate | FR-27 |
| D13 | Source quadrature | `ρ_h v r` is degree `2k + 1`: exact in `poisson`, one order short in the coupled models. NUM-07's open question, recorded not decided; VER-58 solves with `poisson` | NUM-07 NOTE |
| D14 | Uncharged walks | VER-53's walk becomes exit criterion 4's charged walk, its store seeded with `protonated_2wcd`'s artefact. WP22 D9's comparison stays geometric: its generated leg gets the walked mesh via `inputs.mesh` | A charged leg against an uncharged fixture compares charge |

### Work items

1. `charge/kernel.py`: D1, D2. Read *Design* §1 first.
2. `charge/deposit.py`: D3–D5. Read *Design* §2 first.
3. `charge/fields.py`: D6. Read *Design* §3 first; `check_conservation` keeps its order.
4. `charge/stage.py`, `io/artefact.py`, `core/stages.py`: the producer stage (inputs gain
   `protonation`), D7, D9, D12.
5. `io/case.py`, `io/defaults.py` (D8, D10); `io/run.py`, `io/manifest.py` (D8, D11);
   `solve/stage.py`, `solve/state.py`, `post/stage.py` (D9); `cli/export.py` (D11).
6. Tests below; a `tests/conftest.py` helper seeding a store with `protonated_2wcd` (D14).
7. `SPECIFICATION.md`: VER-58's row; Appendix A (FR-13, FR-14, QR-03 → VER-58); RSK-08 retired.
   `CHANGELOG.md` under `v0.4.0-alpha.3`. No public name is added.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance |
|---|---|---|---|
| `tests/tier1/test_charge_kernel.py` | 1 | VER-58 | Integral `q` to 10⁻¹² at `r_i/w` ∈ {0, 0.3, 1, 3, 30, 600}; finite and even on the axis; 3D Cartesian deposition binned by `annular_weights` converges (≥ 3.5× per halving, three spacings, < 10⁻³ at the finest); separable = direct sum to 10⁻¹³; unrenormalised on-axis sum `−h²/(6w²)` to 10 %, renormalised exact; spacing gate |
| `tests/tier1/test_charge_deposit.py` | 1 | VER-01, VER-02, VER-58, QR-12 | Element moments against every monomial ≤ `k` equal the lattice's to 10⁻¹²; NGSolve field's equal the payload's; element order; every *Design* §5 row fails its gate and only it; D4 and digest gates name their quantity; first z-moment = source's − `centre_z_nm` to 10⁻⁹ |
| `test_case_*`, `test_run`, `test_manifest`, `test_cli`, `test_stages`, `test_charge_stage`, `test_protonation` | 1 | VER-24, VER-25, VER-29, VER-32 | D10 refusals name their keys; switches classified; D8; listing imports no NGSolve; export round-trips; WP27's pinned target-only and "WP28" tests updated, not deleted |
| `tests/tier2/test_charge_potential.py` | 2 | VER-58 | `poisson`, one atom, grounded sphere, *Design* §4. `w = 0.25` nm, `r_i` ∈ {0, 1.5} nm, near-atom mesh halved twice: `r`-weighted L² error over a 2 nm disc at rate ≥ 2.5 between the finest two (`P2` 3, `P0` 2). Recorded: on-axis error; an unresolved atom (`w = 0.0112` nm, 0.1 nm elements) at ≥ 1 nm beside `P0`'s |
| `tests/tier2/test_charge_2wcd.py` | 2 | VER-01, VER-02, VER-29, QR-03 | `protonated_2wcd` on its generated mesh: both legs and every plane ≤ 10⁻³; `Q_net` −60 e; ring ≤ 10⁻⁴; solid share ≥ 0.5, recorded; export re-read to the same digest; seconds and peak memory recorded |
| `tests/tier2/test_pipeline_2wcd.py` | 2 | VER-53, FR-25, FR-27 | Every `PIPELINE` stage to a charged solve; the manifest keys each and records `Q_net` and the report |
| `tests/tier3/test_charge_archive.py` | 3, recorded | VER-01, VER-02, VAL-15 | Archived PQRs 50–99 via `inputs.pqr` beside `structure:`, in VAL-05's frame (`Z_MD`): legs and worst plane; export against `rhoq_pore` (planar integrals, rms and maximum difference, per plane), split through the G4 construction rebuilt from the same PQRs; the export re-read via `inputs.charge` and its verdict; the charged frozen case (G, `t₊`) against the reference mesh and table |
| `-m slow` | — | — | Sum and deposit wall-clock and peak RSS, per 2WCD frame and for 50 frames |

`uv run pytest tests/tier1/test_charge_kernel.py tests/tier1/test_charge_deposit.py tests/tier2/test_charge_potential.py tests/tier2/test_charge_2wcd.py -v`,
then the full gate.

### Out of scope

`χ` and the exclusion shell (WP30); APBS and VAL-06 (WP29); the GUI's charge views (WP31); the
guide and example 07 (WP32); the coupled models' `r`-weight order (NUM-07 NOTE, open; D13); a
per-frame lattice cache and parallel frames (no owner; measured); the analyte's charge (FR-21,
v1.0).

### Open questions

None blocking. Close calls the author may overrule without disturbing the rest: D3's `k` (against
`P0`/`P1`); D6's smoothed weight at 0.5 nm on the producer path, while the consumer path keeps its
0.2 nm linear ramp (a spec amendment, made here); D10's refusal of `axis_cutoff_nm`; D4's threshold
of half the absolute charge; D14's uncharged geometry comparison.

## Design

### 1. The kernel on the lattice [verified, tested]

PHY-16 step 5 factorises: `ρ̄_i = q_i π^(−3/2) w⁻³ · Z_i(z) · R_i(r)`, with
`Z_i = exp(−(z − z_i)²/w²)` and `R_i = exp(−(r − r_i)²/w²) Ĩ₀(2 r r_i/w²)`. The exponent is safe:
`r² + r_i² − 2 r r_i cos θ`, averaged over `θ`, gives `I₀(2rr_i/w²) e^{−(r² + r_i²)/w²}`, which is
`Ĩ₀ · e^{−(r − r_i)²/w²}`, so no factor overflows at `2 r r_i/w² ~ 10⁶`.

The areal density on the lattice is therefore a sum of rank-one patches, `Z_i ⊗ (2πr R_i)`. Over a
frame it is one sparse product `A Bᵀ`, with `A` of shape (`n_z × atoms`) and `B` of shape
(`n_r × atoms`). The atom's lattice sum is also separable, `(Σ_z τ_z Z_i)(Σ_r τ_r 2πr R_i) h²`, so
renormalising costs a patch's side, not its area.

Measured on the trapezoid lattice at `h = 0.005` nm (`.knowledge/04` §3.3):

- Off the axis the sum is exact to 10⁻¹⁵, down to the CHARMM polar hydrogen's `w = 0.0112` nm,
  because the trapezoid rule on a Gaussian errs by `~2 exp(−π²w²/h²) = 10⁻²¹`.
- On the axis the integrand `2πr ρ̄` starts linearly, and the end correction is `−h²/(6w²)`:
  −1.67 × 10⁻³ at `w = 0.05` nm, −3.2 × 10⁻⁴ at `r_i = 0.05`, `w = 0.1`.

Per-atom renormalisation removes that error, and it is the construction VER-01's producer leg
guards. ClyA's innermost atoms sit at `r ≳ 1.6` nm, where it does not arise.

The spacing gate `h ≤ ½ min w_i` keeps the aliasing below `e^{−4π²} = 7 × 10⁻¹⁸`. The default
passes it at `w/h = 2.24`.

### 2. The projection is Galerkin-exact for the source [verified]

On element `K`, `ρ_h|K ∈ P_k` solves `∫_K ρ_h v r = Σ_{n∈K} m_n v(x_n)` for every `v ∈ P_k(K)`. Here
`m_n = τ_n h² a_n / (2π)` is the lattice's trapezoid mass, and `a_n` is the areal density at node
`n`. Since `ρ = a/(2πr)`, `ρ r = a/(2π)`, and nothing singular is sampled.

Every test function of the potential's `P_k` space restricts to `P_k(K)` on each element. So the
assembled source `∫ ρ_h v r` equals the lattice integral of the kernel against `v`, for every `v` of
the space, exactly, wherever the assembly integrates degree `2k + 1` (D13). The potential is the Galerkin solution for the true charge up to the
lattice's quadrature, and the projection adds no error of its own.

`P0` keeps only each element's monopole, which moves charge by up to half an element. That is 0.05 nm
in ClyA's 0.1 nm protein elements, and it shows as a dipole error and an `O(h²)` potential where
`P2` gives `O(h³)`, which VER-58 measures.

Three facts follow, each of which the implementation relies on.

- Taking `v = 1`, each element carries exactly its lattice charge. So `Q_mesh = Q_grid` up to the
  uncovered mass that D4 gates: the consumer leg is exact by construction, and is fed broken
  constructions in Tier 1.
- The basis is monomials in `((r − r_K)/d_K, (z − z_K)/d_K)` about the centroid, scaled by the
  diameter, so each Gram matrix is well conditioned. `G_K = ∫_K φ_a φ_b r` is exact under a
  triangle rule of degree `2k + 1` (Dunavant's 7-point rule at `k = 2`).
- The generated meshes are affine, since nothing calls `Curve`, so barycentric node location and
  the NGSolve geometry agree.

A node on a shared edge goes to the lowest element index, so every node is counted once.

### 3. The per-plane check on the producer path [verified]

Azimuthal averaging keeps the z-marginal, so atom `i`'s marginal is exactly Gaussian, `N(z_i, w_i²/2)`.
Under the weight `W_p(z) = ½ erfc((z − p)/s)`, its share below plane `p` is
`½ erfc((z_i − p)/√(s² + w_i²))`. That was checked against adaptive quadrature to round-off. The
source side is then `Σ q_i ½ erfc(...)/n_frames`, with no discretisation at all.

The error this check carries is the mesh side's: `∫ (ρ − ρ_h)(W − Π_k W) r` on the elements where
`W` is not a polynomial of degree `k`.

- The consumer path's 0.2 nm linear ramp has two kinks. A `P2` fit to a kink errs by `h/(16s)`,
  which is 0.031 on the 0.1 nm protein elements (`SizeTable.protein_nm`). Against `|Q_net| = 60 e`
  and 10⁻³, that leaves too little margin to call the gate discriminating rather than lucky.
- The erf weight is smooth. Its `|W'''| ≤ 2/(√π s³)`, so a `P2` fit errs by about
  `0.064 h³ |W'''| = 5.8 × 10⁻⁴` at `s = 0.5`, 50 times less, and falls as `h³`.

`s = 0.5` nm is still well below the nanometre scale at which a compensating Jacobian error
redistributes charge along ClyA's funnel. That is the failure PHY-19's per-slice check exists for
(*Design* §5, row 3).

These are estimates. Tier 2 records the worst plane on 2WCD. A failure there is first evaluated at
order + 3 and at `s = 1` nm: if it falls as `(h/s)³`, it belongs to the check and not to the
deposit, and is reported as such. The tolerance is not moved.

### 4. VER-58's closed form [verified]

A smeared atom at `(r_i, z_i)` sits in a uniform `ε` inside a grounded sphere of radius `R` (the
half-disc, its arc `cis` and `trans` at zero bias). Let `a = √(r_i² + z_i²)`. The Kelvin image of
each point of the ring is a charge `−qR/a` at `R²/a` along the same ray, so the images form a ring
at `(R² r_i/a², R² z_i/a²)`. Outside the Gaussian's support the smeared ring is the point ring.
The exact potential is therefore

```
φ(r, z) = (q/4πε) · ⟨ erf(d/w)/d ⟩_θ  −  (q R/a)/(4πε) · ⟨ 1/d' ⟩_θ
```

where `d` and `d'` are the distances to the ring point and to its image at azimuth `θ`, and
`⟨·⟩_θ` is the azimuthal mean (periodic trapezoid, spectrally accurate). On the axis every point
of each ring is equidistant, so

```
φ(0, z) = q erf(ρ/w)/(4πε ρ) − q R/(a · 4πε ρ')
```

The sphere's boundary values computed from this vanish to 10⁻¹⁷. At `r_i = z_i = 0` the image term
is the constant `−q/(4πεR)`. `erf((R − a)/w)` is 1 to round-off for `R = 10` nm.

### 5. Broken constructions and the gate each must fail

| Broken construction | Fails | Passes |
|---|---|---|
| Per-atom renormalisation dropped; an atom at `r_i = 0`, `w = 0.05` nm (−1.67 × 10⁻³) | VER-01 producer leg | consumer leg |
| The projection's Gram matrix without the `r` weight; an atom near the axis | VER-01 consumer leg | producer leg |
| `2πr` dropped from the areal density and renormalised globally to `Q_net`; unit charges at (1, −1) and (4, +1) nm. The cumulative at `z = 0` is 1.6 against 1.0 | VER-02, mesh and grid against source | VER-01, both legs |
| Patch truncated at `2 w` with no renormalisation (`1 − erf(2)² = 0.93 %` outside) | VER-01 producer leg | — |
| `centre_z_nm` not applied | the first-moment assertion; the solid-share gate at a 5 nm shift | conservation |
| Deposit at `P0` | the Galerkin moment test; VER-58's rate (Tier 2) | conservation |
| Payload on a permuted copy of its mesh | the digest gate | — |

### 6. Cost

A 2WCD frame holds about 54 k heavy atoms, with `w` 0.085–0.11 nm and patches of about 200² nodes,
and a similar number of hydrogens with smaller patches. That is about 3 × 10⁹ multiply-adds in one
sparse product, seconds to tens of seconds. The ensemble is 50 such frames.

The lattice for ClyA is about 1400 × 3400 nodes (34 MB). Node location rasterises each triangle
in the lattice box over its bounding box, about 10⁷ barycentric tests.

Targets are 60 s and 2 GB per frame, measured under `-m slow` and not gated. The sum is linear, so
a frame-parallel or per-frame-cached version changes no number.
