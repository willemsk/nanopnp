---
type: Test Evidence
title: 'Tier-1 test evidence: analyte bodies (WP45 item 20)'
description: What the Tier-1 tests of analyte bodies establish, recorded at WP45 item
  20.
tags:
- analyte
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_analyte.py::TestAnalyteInBox::test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_analyte.py::TestAnalyteInBox::test_fr21_the_body_is_a_half_disc_of_the_right_size
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_analyte.py::TestPoreWithAnalyte::test_fr21_the_body_does_not_eat_the_pore_wall
  at: '2026-10-16T00:00:00Z'
---

## Tier-1 test evidence: analyte bodies (WP45 item 20)

- **[tested: tests/tier1/test_analyte.py::TestAnalyteInBox::test_fr21_the_body_is_a_half_disc_of_the_right_size]** The meridian area of a half-disc analyte is checked one-sidedly against `π a²/2`: a straight-edged mesh can only cut the corner off a curved body, so an area above the exact one would mean fluid is being picked up. Source: `tests/tier1/test_analyte.py` (`test_fr21_the_body_is_a_half_disc_of_the_right_size`).
- **[tested: tests/tier1/test_analyte.py::TestAnalyteInBox::test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc]** The meshed arc length of the body is checked one-sidedly against half a circle's circumference. Source: `test_analyte.py` (`test_fr21_the_analyte_boundary_is_the_bodys_meridian_arc`).
- **[tested: tests/tier1/test_analyte.py::TestPoreWithAnalyte::test_fr21_the_body_does_not_eat_the_pore_wall]** Ramanujan's ellipse-perimeter approximation is used only as a scale reference for the meshed arc length, at a 2 % tolerance. Source: `test_analyte.py` (`_analytic_ellipse_perimeter`).

