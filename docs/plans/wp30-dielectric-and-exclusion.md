# WP30 — The dielectric field and the ion-exclusion shell (FR-15)

**Status: planned, not started.** Planned 2 October 2026, on `main` at `aa3a743`, with WP29 merged.
This is the fifth package of Phase 3. It inherits the following:

- from WP21: stage 5's model frame, junction and `RegionRecord`, and stage 6's sizing and gates;
- from WP23: the Gmsh region graph;
- from WP26: the `solid_fraction` declaration;
- from WP28: stage 7's `FieldsArtefact` and the rule that consumers read a field only from it;
- from §4.4: the VER-30 blend and its gates, which already treat `exclusion` as ion-free water;
- from WP29: VAL-06, closed.

This plan belongs to [Phase 3](phase-3-charge-pipeline.md). `SPECIFICATION.md` governs, and the
identifiers here are pointers into it. This plan's commit amends the specification in seven places:

- a §4.4 NOTE on the derived solid fraction;
- a §5.2.1 NOTE on the ion-exclusion shell;
- the stage-7 design note in §5.2;
- the §5.3.1 NOTEs on the protonation keys and on the v2 keys that change a number, which replace
  the "WP30" refusal with the conditions under which the keys are refused;
- the `interface` sentence of the vocabulary NOTE, to cover solid-to-solid seams;
- a new VER-59 row;
- one sentence in OPN-07.

## Execution brief

**Scope.** Two switches stop being refused. Both default to 0, the validated model.

- **`charge.exclusion_offset_nm`.** Stage 5 offsets the profile outward and assembles the shell as
  the material `exclusion`. Stage 6 meshes it, and `wall` moves to the shell's outer surface.
- **`charge.dielectric_transition_nm`.** Stage 7 derives `χ` from the same profile, and the VER-30
  blend consumes it.

The package discharges FR-15 and adds evidence for FR-09, FR-10, PHY-02 and PHY-20. It adds VER-59
and extends VER-30 (the `exclusion` registration rule) and VER-31 (a generated slab shell).

The brief runs past its target. Seven of the decisions change a number a run reports: D1–D4, D7,
D9 and D11.

**Read first.**

- The §4.4 NOTE on the derived solid fraction, and the PHY-20 blend NOTE before it.
- The §5.2.1 NOTE on the ion-exclusion shell, and the membrane-junction NOTE before it.
- The vocabulary NOTE in §5.3.1.
- VER-30, VER-31 and VER-59.
- *Design* §1–§4 below.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | What `χ` is | `χ = S(s/δ + ½)` with `S = 3x² − 2x³`. `s` is the signed distance to `W`, positive in the body, and `W` is the profile's water-facing part. The transition is C¹ and spans `\|s\| < δ/2` | §4.4 NOTE. The 1/2-level is the meshed interface, so δ → 0 gives the material split exactly. A remap of the stage-3 mean would not, and its width would vary with `\|∇ρ\|` (*Design* §1). This refines the phase plan's "from the stage-3 mean" |
| D2 | `W` | The profile's edges, split at the bilayer planes, whose outward side is not membrane (an outward probe at each piece's midpoint). It must equal the region's protein-to-water edges as `name_region` assigns them | The protein against the membrane stays sharp: there is no water there. Checking against `name_region` catches a frame or orientation slip |
| D3 | Analytic solids | `χ ≡ 1` on every solid material other than `protein`, for the derived field only. A supplied `χ` keeps its current meaning | The membrane is not drawn from the density. VER-30's supplied-field tests use the membrane as the solid and must not change |
| D4 | Representation | Nodal samples on a lattice of spacing `δ/20` over the body's bounding box widened by `δ` and clipped at `r = 0`. They are read through `coefficient(grid)`, the supplied path's `VoxelCoefficient`. The payload is `eps_r.npz` in stage 7's artefact. The distances are computed in numpy, band by band and segment by segment, with an even–odd scanline for the sign, so no Shapely is needed | The interpolation error is ≤ 0.75 (h/δ)² = 1.9 × 10⁻³ off the vertices. Bilinear interpolation keeps [0, 1], and the box edge is 0 by construction (*Design* §1). Stage 7 must keep running without the `structure` extra |
| D5 | Where `χ` is built | In stage 7's `charge` half, which also runs when δ > 0. `region` joins its declared inputs. The artefact's parameters gain `eps_r: {derived: …}` only when δ > 0. The solve reads `χ` whenever the artefact holds one, and `fields.eps_r` stays false | §5.2 stage-7 note. Setting `fields.eps_r` would break OPN-07's constraint, and the identity gap is recorded there |
| D6 | Gates on `χ` | The range gate runs on the samples. The registration gate runs on the per-material means, and the `exclusion` ceiling is 1/2 rather than 0.1. That ceiling applies to a supplied `χ` too | The shell lies wholly on the water side. A planar shell averages 3δ/(32a), which is 0.156 at δ = 0.2 and a = 0.12 nm (*Design* §1) |
| D7 | Shell construction | Dilate by `a` (round joins, `QUAD_SEGS` = 8), close by `2h_c`, fill holes and record them, apply step 6, gate the ring. Shell = `O − P − M`, electrolyte = `D − M − O`, and the membrane is unchanged. Shapely is imported inside the function. Without the `structure` extra the case is refused naming the extra and the key | §5.2.1 NOTE. The closing and the hole-filling reuse stage 4's constants and rationale. A filled pocket is fluid that no ion can reach, so it is recorded rather than refused. Hand-rolling a robust polygon offset is not worth the risk |
| D8 | Names | Shell to electrolyte is `wall`. Protein to shell and shell to membrane are `interface`, as protein to membrane already is. A protein edge facing the electrolyte beside a shell raises `RegionGateError` naming it | The vocabulary NOTE, as amended. Moving `wall` moves the no-slip surface, the no-flux surface and PHY-02's source with no code change in `mesh/distance.py` |
| D9 | Sizes | The `exclusion` domain is sized at the resolved `wall_h_nm`, in `domain_size` and in `GMSH_FIELD_RULES` | A 0.25 nm shell then has about five elements across it. The protein-to-shell dielectric jump keeps the resolution the old wall had |
| D10 | Record and keys | `RegionRecord` gains an optional `exclusion` block: the offset, the constants, the outer loop, the filled holes and the measured width range. The block is **omitted from the dump** when absent. The schema stays `nanopnp/region/v1`. `region_parameters` gains `exclusion` only when `a > 0`, and `KEY_CONSTANTS` is untouched | VER-59's first clause: at 0, every key and the record's bytes are unchanged. The rebuild reads the loop, so stage 6 needs no Shapely (*Design* §4) |
| D11 | Resolution limits | Refuse `0 < δ < h_c` and `0 < a ≤ 2h_c`, naming the key and `geometry.density.grid_spacing_nm` | The first would be finer than the grid that places the contour. The second would be narrower than §5.2.1's feature-size criterion |
| D12 | Case refusals | Either key is refused beside `inputs.mesh`, or with neither `structure:` nor `inputs.profile`. `δ` is refused beside `inputs.eps_r`. A model not declaring a solid fraction refuses `δ`. `_UNREAD_CHARGE_KEYS` is emptied but kept | The §5.3.1 NOTE on the v2 keys. It follows the knob-with-no-effect rule (`size_scale`) and the exclusive supply chains |
| D13 | Stage-5 refusals | An offset within `h_c` of the axis is refused, naming the z interval, the body's least radius, `a` and `h_c`. So is an offset vertex outside the reservoir, and any domain that is not one face | §5.2.1 NOTE. The first is VER-59's "closes the constriction" |
| D14 | FR-25 | No new code. Both keys are already in `SWITCH_PATHS`, and `exclusion_deviations` already fires on the mesh's materials. VER-59 asserts all three entries | `io/defaults.py`; `mesh/ingest.py` |
| D15 | Test values | `a` = 0.25 nm, which is `a_Na/2` from `willems2020_nacl` and VER-31's `λ_S`. `δ` = 0.15 nm, the middle of PHY-20's 1–2 Å | Each traces to a cited source, and neither is a fit |
| D16 | Goldens | Before the first code change, record on `main` the region, mesh, fields and stage-10 keys, and the region record's bytes, for VER-53's coarse synthetic region walked to stage 10 at a cheap `size_scale` | The invariance claim is only meaningful if the comparison is against keys recorded before the change |
| D17 | Stern through the pipeline | Use the cylindrical Gauss form on a stage-5 body through `inputs.profile`, solved with `pnp` at zero bias at 0.1 M. The slab of VER-31 is rebuilt from the generated shell | *Design* §3. A planar Stern problem cannot be posed through stage 5's axisymmetric region |

### Work items

0. Record the D16 goldens on `main` in `tests/tier2/test_exclusion_keys.py`, as frozen literals.
1. **The shell.** In `geometry/region.py`:
   - an `exclusion_shell(profile, offset_nm, h_c)` function, implementing D7, D11 and D13;
   - a fourth domain in `assemble_faces`;
   - the D8 rules in `name_region`;
   - the `exclusion` block on `RegionRecord`, and D10's parameters.

   Then update `region_graph` and `_chain` for four faces, and add D9 to `mesh/sizing.py` and
   `mesh/gmsh_backend.py`. Read first: the §5.2.1 NOTEs, and WP21's Design §1.
2. **The case.** In `io/case.py`: empty `_UNREAD_CHARGE_KEYS`; add D11 and D12; route `δ` through
   the model's declaration. In `io/run.py`, `selected_stages` adds `charge` when δ > 0.
3. **`χ`.** A derived solid-fraction class in `materials/fields.py`, implementing D1–D4 and sharing
   the gate code; the D6 rule in `check_materials`. Stage 7 (`charge/stage.py`) gets D5:
   `_prepare`, the "no work" refusal, the parameters, the payload and `region` as an input. The
   solve's and the post stage's field gates widen to "the artefact holds `χ`". Read first: the
   §4.4 NOTEs; `materials/fields.py`; and the WP28 plan's D9.
4. **The existing tests that change.**
   - `test_case_schema.py:250` (the WP30 refusal).
   - VER-52's naming expectations, which are unchanged at `a = 0`.
   - VER-31's slab, which gains the generated-shell variant.
5. **Records.**
   - `.knowledge/04` gains the 2WCD shell and `χ` measurements, marked [tested].
   - `.knowledge/06` gains whatever GEOS buffer behaviour is found.
   - Add Appendix A rows for VER-59, and update the FR-15 row.
   - `CHANGELOG.md` gets a section under `v0.4.0-alpha.5`.
   - Update the phase plan's WP30 Outcome and `current.md`.

### Verification

| Test file | Tier | Identifiers | Assertion and oracle | Tolerance and source |
|---|---|---|---|---|
| `tests/tier1/test_exclusion_shell.py` | 1 | VER-59 (shell), FR-09, QR-12 | On the parallelogram body: the distance band of every `wall` node; names and the one-face check; the membrane, chord and junction equal the shell-free region's; the constriction refusal names its z; a necked pocket is filled and recorded; the D11 and D12 refusals and the missing extra (monkeypatched); the record round-trips and rebuilds without Shapely; the key moves only when `a > 0`; the Gmsh graph reads four faces | `[a − max(h_c²/a, a/100), a + 10⁻⁶]`, *Design* §2 |
| `tests/tier1/test_derived_dielectric.py` | 1 | VER-59 (dielectric), VER-30 | Along the normals at the midpoints of the water-facing edges, `χ_h` against `S(s/δ + ½)` for `\|s\| ≤ δ`. `χ = 1` in the membrane and deep in the protein, the box edge is 0, `W` equals the adjacency, the range and registration gates pass, and an inverted derived `χ` and the refusals fail. The blend is checked at one point inside the protein and one in the fluid | 4 × 10⁻³, twice *Design* §1's 1.9 × 10⁻³ |
| `tests/tier2/test_exclusion_keys.py` | 2 | VER-59 (invariance) | With both keys at 0 the D16 keys and bytes are equal | Equality |
| `tests/tier2/test_stern_layer.py` | 2 | VER-31, VER-59 | The slab's shell from `exclusion_shell` equals the drawn `[0, λ_S] × [0, H]`, and `φ_0` is unchanged | 10⁻¹² nm, and the solver tolerance |
| `tests/tier2/test_exclusion_stern.py` | 2 | VER-59, FR-15 | On the cylindrical body: the mid-plane drop across the shell against Gauss's law, φ at `√(R(R − a))` against the mean of the ends, and the drop ≥ 10 % of the wall potential | 1 % (VER-31's own), 10⁻³ of the drop; *Design* §3 |
| `tests/tier2/test_exclusion_2wcd.py` | 2 | VER-59, FR-10 | 2WCD at `a` = 0.25: the lower distance band at every `wall` node, VER-10 and the wall-size gate, the closed share recorded. Adding `δ` = 0.15, the WP28 charged walk runs to stage 12 with every gate passing and the three deviations in the manifest | The *Design* §2 lower bound |
| same file, `-m slow` | — | — | `χ` derivation time and memory at `δ = h_c` on 2WCD, and the largest interpolation error near the vertices | Recorded |

```bash
uv run pytest tests/tier1/test_exclusion_shell.py tests/tier1/test_derived_dielectric.py -v
uv run pytest tests/tier2/test_exclusion_keys.py tests/tier2/test_exclusion_stern.py tests/tier2/test_exclusion_2wcd.py tests/tier2/test_stern_layer.py -v
```

### Out of scope

| Item | Owner |
|---|---|
| Showing the shell and `χ` in the GUI | WP31 |
| A `χ` export as a `field1` document. It would not re-read through `inputs.eps_r`, because of D3 | WP31, as the viewer's input |
| The guide to the switches | WP32 |
| A shell or a transition at the membrane or the analyte | Not specified. The analyte in a generated region is FR-21, v1.0 |
| The identity of a derived `χ` in a golden | OPN-07 |
| The coupled models' quadrature order | WP28 D13, open |
| VAL-06 with the switches on | Not required |
| A supplied `χ` on a generated ClyA mesh | Observed, not changed. It cannot cover a 250 nm membrane, because the box edge would be refused, and anything short of that fails the membrane's registration |

### Open questions

None blocks implementation. The author may overrule any of these three close calls:

- D7 fills enclosed pockets and records them, where it could refuse them.
- D9 meshes the shell at the wall size.
- D6 sets the shell's registration ceiling at 1/2.

## Design

### 1. The derived `χ` [verified]

**The function.** `S(x) = 3x² − 2x³` has `S(½) = ½`, `S′ = 6x(1 − x)` with its maximum of 1.5 at
½, and `S″ = 6 − 12x`, with `|S″| ≤ 6`. So `|∂²χ/∂s²| ≤ 6/δ²`.

**The interpolation bound.** The bilinear error on a cell of side `h` is at most
`(h²/8)(max|χ_rr| + max|χ_zz|)`. Off the vertices, `s` is affine and `χ_rr + χ_zz` is at most
`6/δ² (n_r² + n_z²) = 6/δ²`, so the error is at most `0.75 (h/δ)²`, which is 1.875 × 10⁻³ at
`h = δ/20`.

Near a vertex, the distance's Hessian adds `(h²/8)(1.5/δ)/ρ`. That is a further 1.9 × 10⁻³ at
`ρ = δ/4`. Where the medial axis crosses the band, at concave vertices on the water side, `χ` has a
kink, and there the error is of order `h · 3/δ / 4` ≈ 0.04. The test therefore asserts at edge
midpoints on a convex body, and records the error near vertices on 2WCD.

**Why not remap the density.** The conditioned profile differs from the 0.25 isolevel by the `2h`
closing and opening, Taubin smoothing and simplification. Each of these is up to a few hundredths
of a nm, and the closing fills grooves up to 0.2 nm wide (§5.2.1 NOTE). A remap `χ = F(ρ)` would
put protein elements in those grooves at `χ < ½` and fluid elements at `χ > ½`. Its δ → 0 limit
would therefore not be the mesh's split, and it would trip the registration gate. `|∇ρ|` varies
along the wall, so no single `F` gives one width.

**The masses.** `∫₀^{½} S dx = 1/8 − 1/32 = 3/32`. So the water side of a planar transition carries
`(3/32)δ` of `χ` per unit area. A shell of width `a ≥ δ/2` therefore averages `3δ/(32a)`: 0.0563
at δ = 0.15 and a = 0.25, and 0.156 at δ = 0.2 and a = 0.12. In general, `S < ½` on the water side,
so any shell averages below ½, and an inverted field averages above it.

The protein side loses `(3/32)δ` per unit length of `W`. On a ClyA body (26.5 nm², `W` about
45 nm long) at δ = 0.15 that is about 0.63 nm², a mean of 0.976, which clears the 0.9 floor.

**Cost.** At `δ = h_c` = 0.05 nm the spacing is 0.0025 nm. The 2WCD box, about 4.5 × 14.2 nm, then
holds about 1.0 × 10⁷ samples, 82 MB at float64. At δ = 0.15 nm it holds 1.1 × 10⁶. The distances
are evaluated only in the band `|s| < δ/2` plus two cells, and the sign by scanline.

### 2. The shell's width [verified]

GEOS places round-join vertices on the offset circle, and straight offset edges lie at exactly `a`.
At 8 segments per quarter circle, each chord of a radius-`a` arc subtends π/16. Its sagitta is
`a(1 − cos(π/32)) = 4.8 × 10⁻³ a`.

Step 6 merges edges shorter than `h_c`. A merged chord on an arc is therefore shorter than `2h_c`,
and its sagitta is `a − √(a² − h_c²) ≈ h_c²/(2a)`. The closing re-discretises at radius `2h_c`,
adding at most `2h_c(1 − cos(π/32)) = 4.8 × 10⁻⁴` nm at `h_c` = 0.05.

The bound `max(h_c²/a, a/100)` is twice the larger of the two sagittas, which covers the closing's
term. At `a` = 0.25 it is 0.01 nm against a sagitta of 0.0051.

Every chord lies on the body's side of the arc it replaces, so nothing departs outward except where
the closing filled a concave groove or a pocket was filled. Both are recorded. The closing is a
no-op on the convex `O` of a convex body, which is why the Tier 1 test can assert both sides of the
band on the parallelogram.

The shell is one face: `O − P` is a ring around the simple polygon `P`, and `M`, which meets `P`
along its outer surface between the planes and reaches the reservoir arc, cuts the ring exactly
once.

### 3. Stern through the pipeline [verified]

On the symmetry plane of a long cylindrical body, `∂φ/∂z = 0`. The charge-free shell
`R − a < r < R` then satisfies Gauss's law on a unit length:
`−ε₀ ε_r,f⁰ ∂φ/∂r · 2πr = λ_enc`, where `λ_enc = F Σ z_i ∫₀^{R−a} c_i(r, 0) 2πr dr`. Integrating,

```
φ(R − a) − φ(R) = λ_enc ln(R/(R − a)) / (2π ε₀ ε_r,f⁰)
```

The axial term the plane neglects decays as `exp(−L/(2λ_D))` in the lumen and as
`exp(−πL/(2T))` in a body of thickness `T`. With `L` = 20 nm, `λ_D` = 0.96 nm (0.1 M) and `T` =
2 nm, these are 3 × 10⁻⁵ and 1.5 × 10⁻⁷, both far below the 1 % tolerance.

At `R` = 3 nm and `a` = 0.25 nm, `ln(R/(R − a))` = 0.087011, so the effective width is
`R ln(R/(R − a))` = 0.26103 nm. A fixed charge equivalent to VER-31's `σ_s` = 0.0435 C m⁻² gives a
drop of 16.4 mV on a wall potential near 67 mV, about 24 %. That leaves the 10 % margin with room.

The body is the rectangle `r ∈ [3, 5]`, `z ∈ [−10, 10]`, in a 40 nm reservoir. Its fixed charge is
a supplied `volume_charge_density`: a band in the body at least three protein elements wide, so
that the consumer gates pass. The mobile charge is sampled on the mid-plane with Simpson's rule.

`pnp` with every correction `none` leaves `ε_r,f⁰` uniform in the fluid, so the shell and the lumen
share one permittivity. A shell that held ions would curve the profile, and the geometric-mean
check would catch it.

### 4. Keys at zero [verified, from the survey of `aa3a743`]

| Key | Invariant when `a` and `δ` are 0 |
|---|---|
| Stage 5 | `region_parameters` (`region.py:1041`) adds nothing, and `KEY_CONSTANTS` is untouched. The record dump omits the absent block, so `region.yaml`'s bytes are unchanged |
| Stage 6 | It keys on the region hash and the record's face and edge sets, all of which are unchanged |
| Stage 7 | `selected_stages` and `ResolvedFields.parameters` are unchanged when δ = 0. `region` is a declared input, but it enters the key only when δ > 0 |
| Stage 10 | `solve_provenance` gains no key, because D5 leaves `fields.eps_r` alone. Its inputs are the mesh and fields hashes above |

The VER-47 and VER-34 digests therefore do not move.
