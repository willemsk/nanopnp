---
type: Specification
title: "Appendix B. Reference COMSOL model settings"
description: "Condenses the reference COMSOL model settings from the 162-page model report; the full detail is in the knowledge base."
---

## Appendix B. Reference COMSOL model settings

Condensed from the 162-page model report. Full detail is in
`knowledge/09-comsol-reference-settings/index.md`.

| Aspect | Setting |
|---|---|
| Model file | `npgrid_clya_v8_NaCl_report.mph`, report dated 22 May 2020 |
| Software version | COMSOL Multiphysics 5.4, build 388 |
| Dimensionality | 2D axisymmetric, steady state |
| Mesh type | Free triangular throughout, no boundary layers |
| Mesh statistics | 120,917 triangles, 1,879 edge elements, 196 vertex elements; minimum element quality 0.6378, average 0.9765 |
| Global size ("Finer") | max 10 nm, min 0.001 nm, curvature factor 0.25, growth rate 1.05 |
| Pore boundary size | max 0.05 nm, min 0.001 nm, curvature factor 0.25, growth rate 1.05 |
| Pore domain size ("Extremely fine") | max 0.1 nm, min 0.004 nm, curvature factor 0.2 |
| Reservoir domain size | max 2.8 nm, min 0.04 nm, growth rate 1.04 |
| Reservoir outer boundary size | max 5 nm, min 0.025 nm, growth rate 1.25 |
| Symmetry axis inside pore | max 0.075 nm, min 0.04 nm |
| Linear solver | PARDISO, pivoting perturbation 1 × 10⁻¹³ |
| Nonlinear solver | Fully coupled; initial damping 0.2, minimum damping 0.01, recovery damping 0.2; maximum 100 iterations; relative tolerance 1 × 10⁻⁶ |
| Continuation | On `V_bias` |
| Stabilisation, Transport of Diluted Species | Streamline diffusion on; crosswind diffusion on, type "Do Carmo and Galeão", equation residual "Approximate residual"; isotropic diffusion off; convective term in conservative form |
| Stabilisation, Laminar Flow | Streamline and crosswind diffusion on, isotropic off |
| Discretisation | Potential quadratic, concentrations quadratic, velocity and pressure both linear (P1+P1, not Taylor–Hood) |
| Assembly integration orders | Crosswind terms order 6, streamline order 4, most other weak terms order 4, order 2 in the flow interface |
| Current extraction | Variational reaction flux at integration order 4: `F*(z_cpos*tds.ntflux_cpos + z_cneg*tds.ntflux_cneg)` over an electrode boundary |
| Permittivity parameters | `epsr_ms = 30.08`, `epsr_alpha = 11.5` (Gavish NaCl) |
| Sweep | Parameter switch over 5 physics cases × 35 bias values × 21 salt concentrations = 3,675 solves |
| Runtime | 41 h on 12 cores |
| Mesh convergence study | None present in the report (RSK-09) |
