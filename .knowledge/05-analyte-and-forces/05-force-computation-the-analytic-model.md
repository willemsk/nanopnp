---
type: Domain
title: 4. Force computation — the analytic model actually used
description: The analytic force model the source work actually uses.
tags:
- analyte
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 4. Force computation — the analytic model actually used

`trapping_appendix.tex §sec:trapping_appendix:single_barrier_system`. Both external forces are
assumed **constant along the pore** (linear potential drop over L = 14 nm), i.e. spatially uniform
1-D scalars, not fields:

```
F_ep  = e · N_net · V_b / L            (eq:forceep,     N_net = N_body + N_tag)
F_eo  = e · N_eo  · V_b / L            (eq:osmoticforce)
E_ep(x) = −F_ep·x + b_ep ,  E_osm(x) = −F_osm·x + b_osm
ΔE^cis = −F·Δx_cis ,  ΔE^trans = +F·Δx_trans
```

`N_eo` = **equivalent osmotic charge number** — "*the number of charges that must be added to DHFR
to create an equal electrophoretic force*"; asserted to be "*an invariant related solely to the size
and shape of the molecule*". That is the entire force model: **no Maxwell stress, no
dielectric-gradient term, no pressure/viscous decomposition, no surface integral.**

The *general* framework the author endorses (background ch. 2, `nanopores.tex`; adopted by the spec):

```
F_ele = ∮_Γ (T_E · n) dΓ ,   T_E = ε E E − ½ ε (E·E) I        (eq:nanopores_electric_force)
F_hyd = ∮_Γ (T_H · n) dΓ ,   T_H = p I − η[∇u + (∇u)ᵀ]        (eq:nanopores_hydrodynamic_force)
```

magnetic terms of T_E set to zero. The full-tensor form captures **both EP and dielectrophoretic**
contributions (F_DEP = (p·∇)E) with no shape assumption; Stokes' law F_d = −6πηaU is only a
first-order stand-in valid outside the pore. `conclusion.tex` (l. 180) makes it a finding: the
5–30 atm pressure hotspots mean the pressure term is non-negligible, "*confirming the importance of
using the full hydrodynamic stress tensor to calculate the force, rather than just the Stokes'
drag*". T_H is the **same** tensor as in the momentum equation (`.knowledge/01-physics-epnpns/02-governing-equations.md#23-navierstokes-variable-density-and-viscosity`), so η
is the corrected position-dependent viscosity — the integrand inherits the wall correction.

**Sign, resolved [tested: pending].** `T_H = p I − η[∇u + (∇u)ᵀ]` as printed above is the *negative* of the
Cauchy stress the momentum equation is written in, which is `T_H = −p I + 2 η sym ∇u` with
`∇·T_H + f = Re ϱ(u·∇)u` — a positive pressure pushing outward. NUM-28 and
`post/forces.hydrodynamic_stress` use the momentum-equation convention, because the domain form is
derived from that divergence and mixing the two flips the force. The two conventions give the same
physics and opposite numbers, so the rule is: whichever is chosen, the tensor in the force integral
and the tensor in the residual must be the same one. `T_M = ε(E ⊗ E − ½|E|²I)` has no such ambiguity
— `E` appears twice, so the sign of `E` cannot leak into it.

