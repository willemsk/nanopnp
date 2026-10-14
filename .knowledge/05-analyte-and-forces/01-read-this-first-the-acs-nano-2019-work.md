---
type: Domain
title: 0. Read this first — the ACS Nano 2019 work contains no continuum analyte
---

## 0. Read this first — the ACS Nano 2019 work contains no continuum analyte

**There is no ePNP-NS simulation of an analyte anywhere in the thesis.** The trapping chapters
solve (a) equilibrium Poisson–Boltzmann in **APBS** for a coarse-grained bead analyte, and (b) a
**1-D analytic double-barrier rate model** fitted to experimental dwell times. No Maxwell-stress
integral, no hydrodynamic-stress integral, no ALE/moving mesh, no analyte surface in a
Navier–Stokes domain, no computed force profile F(z). The single force number quoted (9 pN) comes
from a **fitted charge parameter**, not a stress integral.

> **Scope: the thesis and ACS Nano 2019 only — read §10 for the force calculation.** A continuum
> force computation does exist in this body of work: Willems published it for PlyAB + haemoglobin in
> **Angew. Chem. Int. Ed. 2022, 61, e202206227**, after the thesis. See **§10**. The "future work"
> sentence below describes the thesis's own position.

Coupled ePNP-NS with an embedded particle is **future work** (`conclusion.tex
§sec:con:perspectives`: "*low-hanging fruits: … (2) computing the net force exerted on
translocating analyte molecules … the full electrophoretic and hydrodynamic force landscape*").
Spec G5 is therefore a **new capability**; its only anchors are (i) the APBS energy landscape,
(ii) the fitted N_eo ≈ +15.5 e, (iii) the pore-only ePNP-NS fields of ch. 6.

---

