---
type: Specification
title: "1. Introduction"
description: "Specifies nanopnp, an open-source Python replacement for a COMSOL nanopore workflow, and maps the specification's sections."
---

## 1. Introduction

### 1.1 Purpose

This document specifies `nanopnp`, an open-source Python program replacing a COMSOL Multiphysics
workflow for continuum simulation of biological nanopores. It states the requirements (§3), the
normative physics model (§4), the software design (§5), the numerical methods (§6) and the
verification and validation plan (§7).

### 1.2 Scope

`nanopnp` accepts an atomistic structure (PDB or mmCIF, optionally with a molecular-dynamics
trajectory), an electrolyte specification and an applied bias, and returns ionic conductance,
transport numbers, current rectification, electro-osmotic flow rate, and axial force and PMF on an
embedded analyte. It solves the extended Poisson–Nernst–Planck / Navier–Stokes (**ePNP-NS**)
equations of Willems et al., *Nanoscale* **12**, 16775 (2020), at steady state, on a
2D-axisymmetric finite-element mesh generated automatically from the structure. Coverage runs from
density mapping, symmetry reduction, contour extraction, geometry and mesh construction and
fixed-charge assembly through solution, QoI extraction, sweeps and provenance. Exclusions are
in §3.5.

### 1.3 Definitions and acronyms

| Term | Definition |
|---|---|
| ePNP-NS | Extended Poisson–Nernst–Planck / Navier–Stokes model of Willems et al. (2020): PNP-NS with concentration- and wall-distance-dependent corrections to D, μ, η, ε and ϱ |
| PNP-NS | Classical Poisson–Nernst–Planck / Navier–Stokes; ePNP-NS at β = 0 with all f^c = f^w = 1 |
| PB | Poisson–Boltzmann, equilibrium; PB-linear is its Debye–Hückel linearisation |
| EDL / EOF | Electrical double layer / electro-osmotic flow |
| QoI | Quantity of interest: conductance G, transport number t₊, rectification ratio RR, EOF rate, analyte force |
| PMF | Potential of mean force, ΔU(z) = −∫F dz |
| MMS | Method of manufactured solutions |
| ClyA-AS | Cysteine-free ClyA variant modelled in the source work, built on PDB 2WCD |
| ESI | Electronic supplementary information of the Nanoscale paper |
| Case file | Declarative YAML document that is the unit of reproducibility (§5.3) |

### 1.4 References

References are collected in §12. The normative sources are the Nanoscale paper and its ESI, the
CC-BY-4.0 thesis (`github.com/willemsk/phdthesis-text`, chs. 5–6), and the COMSOL model report
of §1.6.

### 1.5 Document conventions

Requirements use RFC 2119 keywords: SHALL (mandatory), SHOULD (recommended), MAY (optional). Each
carries a unique identifier, numbered within its class and zero-padded to two digits.

| Prefix | Class | Location |
|---|---|---|
| `IF-nn` | External interface | §3.1 |
| `FR-nn` | Functional | §3.2 |
| `QR-nn` | Quality of service | §3.3 |
| `CON-nn` | Design or implementation constraint | §3.4 |
| `PHY-nn` | Physics/model | §4 |
| `NUM-nn` | Numerical method | §6 |
| `VER-nn` / `VAL-nn` | Verification / validation activity | §7 |
| `ADR-nn` | Architecture decision record | §5.6 |
| `RSK-nn` | Risk register entry | §9 |
| `OPN-nn` | Open item | §10 |

Units are SI and explicit: nm, mol/L (M), K, V or mV, pN. Spelling is British.

### 1.6 Provenance and verification status

Of 118 discrete claims in v0.1, ten were wrong and were corrected, including a factor-of-two error
in the Maxwell–Hall access-conductance benchmark, an inverted sign in the steric flux, and the
finding that the NGSolve pip wheel ships without MUMPS. Transcription of the ePNP-NS
parameterisation from the CC-BY-4.0 thesis LaTeX source surfaced five further errata, one of which
contradicted a correction supplied by the author from memory.

The overriding authority is the 162-page COMSOL model report `npgrid_clya_v8_NaCl_report.mph`
(COMSOL 5.4 build 388, dated 22 May 2020), read in full. Where it disagrees with the printed
sources or with author recollection, the model file governs. It settles the mesh, solver and
stabilisation questions, supplies full-precision fit coefficients, and reverses the earlier ruling
on the permittivity parameters. It also resolves the "0.62" discrepancy: the ESI writes the wall
coefficient as `0.62e1`, which is 6.2.

Claims that could not be verified are marked in place. Errata in the source material are in §4.6.

---
