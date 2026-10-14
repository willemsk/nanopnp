---
type: Test Evidence
title: 'Tier-2 test evidence: quadrature gates, the exclusion shell and the contour (WP45 item 25)'
description: What the Tier-2 tests of quadrature gates, the exclusion shell and the contour establish,
  recorded at WP45 item 25.
tags:
- clya
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier2/test_charge_conservation.py::test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_charge_conservation.py::test_ver29_the_per_plane_ramp_is_not_cosmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_contour_2wcd.py::test_ver51_2wcd_contour
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_exclusion_stern.py::test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law
  at: '2026-10-14T00:00:00Z'
---

## Tier-2 test evidence: quadrature gates, the exclusion shell and the contour (WP45 item 25)

- **[tested: pending]** On the structured under-resolving mesh family of QR-03's agreement gate the quadrature error is not monotone in `h`: 0.261 nm reads 7.4 × 10⁻⁵ and 0.240 nm reads 5.0 × 10⁻⁶, both below the 10⁻⁴ gate, while 0.222 nm exceeds it. That is aliasing of the 0.085 nm Gaussian by a Gauss rule, so the gate must be a measured order-agreement and not an element-size rule. At 0.222 nm the conservation legs still read 1.9 × 10⁻⁴ (five times inside QR-03's 10⁻³) while the order/order+3 agreement reads 3.7 × 10⁻⁴. Source: `tests/tier2/test_charge_conservation.py` (module docstring at `3782c43`, before WP45).
- **[tested: pending]** An unstructured netgen `maxh = 0.2 nm` mesh of the same geometry gave 2.3 × 10⁻⁴ on Linux, 7.8 × 10⁻⁵ on Windows and 2.2 × 10⁻⁵ on macOS, straddling the 10⁻⁴ gate from the mesher alone; the under-resolving fixture is therefore built with `MakeStructured2DMesh`, whose vertices are placed arithmetically. Source: `test_charge_conservation.py` (`coarse_mesh`).
- **[tested: tests/tier2/test_charge_conservation.py::test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one]** Charge placed 0.5 nm into the coarse lumen fails the quadrature gate at 1.3 × 10⁻⁴ against 10⁻⁴, while the conservation legs pass. Source: `test_charge_conservation.py` (`test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one`).
- **[tested: tests/tier2/test_charge_conservation.py::test_ver29_the_per_plane_ramp_is_not_cosmetic]** The per-plane check through the ring centres reads 7 × 10⁻⁶ of `Q_net` with the 0.2 nm ramp and 1.9 × 10⁻³ with a 0.002 nm near-step (nearly twice QR-03's budget), purely from quadrature across elements the plane straddles; the ramp removes the discontinuity, not the disagreement. Source: `test_charge_conservation.py` (`test_ver29_the_per_plane_ramp_is_not_cosmetic`).
- **[tested: tests/tier2/test_contour_2wcd.py::test_ver51_2wcd_contour]** The 2WCD constriction lies at `z = −1.40 nm` in the stage-1 frame (measured on the author's copy, WP20 plan), which is what the stage-4 contour of the vendored structure must bracket. Source: `tests/tier2/test_contour_2wcd.py` (`test_ver51_2wcd_contour`).
- **[tested: pending]** Gauss's law across a generated ion-exclusion shell `R − a < r < R` (charge-free, `φ` flat in `z`): `φ(R − a) − φ(R) = λ_enc ln(R/(R − a)) / (2π ε₀ ε_r,f0)`, with `λ_enc = F Σ z_i ∫₀^{R−a} c_i 2πr dr` read off the analysis plane; `φ` is logarithmic in `r` across the shell, so it takes the mean of its ends at `√(R(R − a))`. Source: `tests/tier2/test_exclusion_stern.py` (module docstring at `3782c43`, before WP45).
- **[tested: pending]** With the bilayer (`ε = 3.2` on the body's outer side) on the analysis plane, the drop misses Gauss's law by 6 %: the bilayer curves `φ` in `z` across the 2 nm body, so `d²φ/dz²` is not zero there although `dφ/dz` is. The body is therefore 30 nm long and the bilayer is moved 12 nm below its middle (`geometry.membrane.centre_z_nm`). Source: `test_exclusion_stern.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_exclusion_stern.py::test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law]** The shell drop of the Stern benchmark is 6.54 mV on a wall potential of −36.8 mV (17.8 %). Its Gauss-law error is 1.3 × 10⁻⁴ at the default sizes and 3.6 × 10⁻³ at `size_scale` 2, where the lumen's concentration is coarser and the enclosed charge moves. Source: `test_exclusion_stern.py` (`test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law`).

