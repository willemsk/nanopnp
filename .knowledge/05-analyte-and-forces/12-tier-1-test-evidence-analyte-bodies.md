---
type: Test Evidence
title: 'Tier-1 test evidence: analyte bodies (WP45 item 20)'
---

## Tier-1 test evidence: analyte bodies (WP45 item 20)

- **[tested]** The meridian area of a half-disc analyte is checked one-sidedly against `π a²/2`: a straight-edged mesh can only cut the corner off a curved body, so an area above the exact one would mean fluid is being picked up. Source: `tests/tier1/test_analyte.py` (`test_fr21_the_body_is_a_half_disc_of_the_right_size`).
- **[tested]** The meshed arc length of the body is checked one-sidedly against half a circle's circumference. Source: `test_analyte.py` (`test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc`).
- **[tested]** Ramanujan's ellipse-perimeter approximation is used only as a scale reference for the meshed arc length, at a 2 % tolerance. Source: `test_analyte.py` (`_analytic_ellipse_perimeter`).

