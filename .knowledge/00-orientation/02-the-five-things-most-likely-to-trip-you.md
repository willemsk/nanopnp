---
type: Orientation
title: The five things most likely to trip you up
---

## The five things most likely to trip you up

Stated in `.claude/rules/physics-numerics.md`; derived here.

1. **The wall function is `1 − exp(−6.2(d + 0.01))`**: plus, and 6.2 nm⁻¹ (ESI `0.62e1`). → `01-physics-epnpns.md` §8.
2. **The steric flux sign:** `β_i` enters the bracket with `+`, and the bracket is negated. → `01` §2.2.
3. **No dielectric-gradient body force** in the published model (`f = ρ_ion E` only); adding one is a
   deviation. → `01` §2.3.
4. **Einstein holds only at infinite dilution:** `D_i/μ_i` drifts to 1.2–1.7 × `kT/e` between 0.15
   and 3 M, so Poisson–Boltzmann is a distinct model, not PNP at V = 0. → `02-electrokinetics-background.md`.
5. **`1/r` terms return NaN at integration order 2.** → `06-numerics-fem.md` §2.2.

---

