---
type: Library Behaviour
title: "24. pint with a Fraction registry converts exactly, and formats nothing (WP5.07)"
description: Why the case's units go through pint with Fraction magnitudes, what that registry converts exactly, which version the Python 3.11 floor allows, and the calls that raise.
tags:
- software
- library-behaviour
- units
sources:
- id: pint-repo
  resource: https://github.com/hgrecco/pint
  title: pint, upstream repository (BSD-3-Clause; `pip install pint`)
- id: wp5.07-plan
  resource: docs/plans/wp5.07-variables-and-the-rebuild-forecast.md
  title: WP5.07 plan, Grounding for D2
generated:
  by: claude-code/0.6.0-alpha.7
  at: '2026-11-04T00:00:00Z'
tested_with:
  pint: 0.25.3
verified:
- by: process:tests/tier1/test_variables.py::test_fr39_a_conversion_of_the_same_dimension_is_exact
  at: '2026-11-04T00:00:00Z'
---

## 24. pint with a `Fraction` registry converts exactly, and formats nothing (WP5.07)

The case's variables and units (FR-39; §8.2.31 AG3) go through one
`pint.UnitRegistry(non_int_type=Fraction)`.

**Version.** The project supports Python 3.11 to 3.14 (QR-09; §8.2.2 B4). pint 0.26 requires 3.12, so the
dependency is `pint>=0.25.3,<0.26`. 0.25.3 is BSD-3-Clause, pure Python, and needs `flexcache`, `flexparser`,
`platformdirs` and `typing-extensions`; it needs no NumPy. Import takes about 0.26 s cumulative and a registry
about 0.2 s, built at first use.

**Why `Fraction`.** A float registry gives 20 Å → 1.9999999999999998 nm, a different key from the decimal
`2.0`. With `Fraction` magnitudes entered as `Fraction(repr(value))`, each of these `==` the decimal:
20 Å → 2.0 nm, 3.5 Å → 0.35, 0.3 Å → 0.03, 50 mV → 0.05 V, 100 mM → 0.1 M, 25 degC → 298.15 K.

**What raises.**

- `str()` or `format()` of a unit or dimensionality that carries a power raises `ValueError` (`Fraction` has no
  `n` format). So does the text of a `DimensionalityError`. A message names the unit texts the case wrote.
- An unknown unit raises `pint.UndefinedUnitError`.
- pint reads `a` as a year and `M` as molar, so a variable called `a` is fine only because variable names never
  reach the unit parser.
