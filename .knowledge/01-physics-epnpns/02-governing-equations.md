---
type: Physics
title: 2. Governing equations
description: The Poisson, size-modified Nernst-Planck and Navier-Stokes equations, with their domains
  and boundaries.
tags:
- physics
- physics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 2. Governing equations

### 2.1 Poisson

```
∇·(ε_0 ε_r ∇φ) = −(ρ_pore + ρ_ion) ,      ρ_ion = F Σ_i z_i c_i
```

`ε_r` is piecewise: `ε_r,p = 20` in the protein, `ε_r,m = 3.2` in the bilayer, and in the
electrolyte `ε_r,f(⟨c⟩) = ε_r,f⁰ · ε_r,f^c(⟨c⟩)` with `ε_r,f⁰ = 78.15`.

**Weak form** (SI §A.1), test function `ψ`, over `Ω = Ω_w + Ω_p + Ω_m`:

```
∫_Ω ∇ψ · D dΩ − ∫_Γ ψ (D·n) dΓ = ∫_Ω ψ ρ_pore dΩ + ∫_Ω ψ ρ_ion dΩ ,    D = ε_0 ε_r ∇φ
```

with `Γ_PE = Γ_w,c + Γ_w,t + Γ_m`. Dirichlet `φ = 0` on `Γ_w,c`, `φ = V_bias` on `Γ_w,t`, and zero
charge `n·D = 0` on `Γ_m`.

> Note the Poisson equation is solved over the **whole** domain including protein and membrane;
> the Nernst–Planck and Navier–Stokes equations are solved only on `Ω_w`.

### 2.2 Size-modified Nernst–Planck

```
∂c_i/∂t = −∇·J_i = 0        (steady state)

J_i = −[ D_i ∇c_i  +  z_i μ_i c_i ∇φ  +  D_i β_i c_i  −  u c_i ]
```

**Steric flux vector** (Borukhov/Kilic/Lu size-modified PNP):

```
            (a_i³ / a_0³) · Σ_j N_A a_j³ ∇c_j
    β_i  =  ─────────────────────────────────
              1 − Σ_j N_A a_j³ c_j
```

with `a_i = 0.5 nm` (all ions; max packing 13.3 M) and `a_0 = 0.311 nm` (water; max packing
55.2 M). There are no experimentally verified values for these; they are from Bazant 2009.

> **Sign discipline.** `β_i` enters `J_i` inside the bracket with a `+`, and the whole bracket is
> negated. Write it exactly as above and add a code comment: *this is the most likely place for a
> sign error in the entire model; a flipped sign drives ions into crowded regions, pushes the
> packing fraction to 1, and diverges.* The `a_i³/a_0³` prefactor makes the steric drive
> species-dependent, and the sum over `j` couples all species — do not collapse it to a
> self-interaction.

**Boundary conditions:** Dirichlet `c_i = c_bulk` on `Γ_w,c` and `Γ_w,t`; no-flux `n·J_i = 0` on
`Γ_p+m`.

### 2.3 Navier–Stokes, variable density and viscosity

The published model uses the **variable-density incompressible** formulation of Axelsson et al.
(2015) — a system of *three* equations, not the constant-density NS most summaries assume:

```
u·∇ϱ = 0                                             (density continuity)
(u·∇)(ϱu) + ∇·σ = f                                  (momentum)
∇·(ϱu) − u·∇ϱ = 0                                    (velocity continuity)

σ = p I − η [ ∇u + (∇u)ᵀ ]
```

**Body force:**

```
f = ρ_ion E = −ρ_ion ∇φ
```

> **There is no Korteweg–Helmholtz / dielectric-gradient term in the published model.** Although
> `ε_r` varies with `⟨c⟩`, the model does **not** include `−½|∇φ|²∇ε` in the momentum equation,
> nor the corresponding `−½|∇φ|² ∂ε/∂c_i` term in the Nernst–Planck excess chemical potential.
> Adding either is a **deviation from the validated model**. Implement both behind a single
> `dielectric_gradient_forces` flag, default **off**, and quantify their magnitude as a numerical
> experiment. Do not silently add them: the model's agreement with experiment was obtained
> without them, and adding one without the other is thermodynamically inconsistent.

**Boundary conditions:** no-slip `u = 0` on `Γ_p+m`; no normal stress `σ·n = 0` on `Γ_w,c` and
`Γ_w,t`.

### 2.4 Domains and boundaries

```
Ω   = Ω_w (electrolyte reservoir) + Ω_p (pore protein) + Ω_m (lipid bilayer)
Γ_w,c , Γ_w,t   exterior reservoir boundaries, cis and trans
Γ_m             exterior membrane boundary
Γ_p+m           interior interface: fluid | (pore + membrane)
```

Geometry: hemispherical reservoirs R = 250 nm each side; DPhPC bilayer thickness 2.8 nm.

---

