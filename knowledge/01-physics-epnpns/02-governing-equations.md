---
type: Physics
title: 2. Governing equations
description: "The Poisson weak form, with pointers to PHY-03 to PHY-09 for the equations, domains and boundaries."
tags:
- physics
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 2. Governing equations

`SPECIFICATION.md` §4.2 states the equations, their signs and their boundary conditions (PHY-03 to
PHY-09). This concept keeps the headings that other concepts link to, each with a pointer, and the
Poisson weak form, which §4 does not state.

### 2.1 Poisson

PHY-03 (thesis eq. 5.1, `eq:poisson`): solved over the whole domain `Ω`, with piecewise
permittivity. `ε_r,p = 20` is the default protein permittivity, a calibration parameter reported as
fitted (PHY-20, ruling 5); `ε_r,m = 3.2`; the electrolyte's `ε_r,f(⟨c⟩)` is PHY-11's.

**Weak form** (SI §A.1), test function `ψ`, over `Ω = Ω_w + Ω_p + Ω_m`:

```
∫_Ω ∇ψ · D dΩ − ∫_Γ ψ (D·n) dΓ = ∫_Ω ψ ρ_pore dΩ + ∫_Ω ψ ρ_ion dΩ ,    D = ε_0 ε_r ∇φ
```

with `Γ_PE = Γ_w,c + Γ_w,t + Γ_m`. Dirichlet `φ = 0` on `Γ_w,c`, `φ = V_bias` on `Γ_w,t`, and zero
charge `n·D = 0` on `Γ_m`.

### 2.2 Size-modified Nernst–Planck

PHY-04 states the flux, PHY-05 the steric flux vector and its sign (`β_i` enters the bracket with
`+`, and the bracket is negated), and PHY-06 the packing assertion (thesis eqs. 5.4 and 5.5,
`eq:sm-nernst-planck`, `eq:epnp-ns_steric_flux_vector`). Solved on `Ω_w` only.

### 2.3 Navier–Stokes, variable density and viscosity

PHY-07 states the variable-density incompressible formulation of Axelsson et al. (2015), three
equations, not the constant-density Navier–Stokes most summaries assume; PHY-08 the body force
`ρ_ion E` and why it carries no dielectric-gradient term (thesis eqs. 5.9 to 5.13). Solved on `Ω_w`
only.

### 2.4 Domains and boundaries

`SPECIFICATION.md` §4.1.1 names the domains and boundaries, and its NOTE the reference geometry:
hemispherical reservoirs of 250 nm on each side and a DPhPC bilayer 2.8 nm thick. PHY-09 states the
boundary conditions (thesis App. B §B.1).

---
