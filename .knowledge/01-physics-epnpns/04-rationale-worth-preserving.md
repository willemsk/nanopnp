---
type: Physics
title: 4. Rationale worth preserving
---

## 4. Rationale worth preserving

**Why the wall offset is 0.01 nm and not Simakov's 0.22 nm.** With `P₂ = 0.22` the function is
negative over the first ~0.2 nm, giving a dead zone of near-zero diffusivity. Pederson et al.
patched this by clamping to an arbitrary positive floor, but that makes any pore narrower than
~0.5 nm carry essentially no current — contradicted experimentally (Rigo 2019). Willems et al.
instead assign the full offset to the heavy atom, i.e. assume the ion-inaccessible volume is
*already* excluded by the geometry. Resulting values: `f^w(0) = 0.06`, `f^w(0.75 nm) = 0.99`.

**Why the viscosity wall function was fitted inverted.** Pronk's MD viscosity data were offset by
each protein's hydrodynamic radius so that `d = 0` means "at the wall" independent of protein
size, then normalised and inverted (`η_0/η^w`) so the fit ranged over [0,1]. Resulting values:
`η_0/η^w(0) = 0.37` (i.e. ~2.6× bulk viscosity at the wall), `η_0/η^w(1.45 nm) = 0.99`.

**Why bulk fits are used inside the double layer.** Acknowledged as the model's main
approximation: there is no non-bulk experimental data and no tractable analytical model. Justified
*a posteriori* by agreement with experiment except at the lowest salt (< 0.05 M), where double
layers overlap and selectivity dominates.

---

