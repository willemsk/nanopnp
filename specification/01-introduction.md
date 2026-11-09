---
type: Specification
title: "1. Introduction"
description: "States nanopnp's purpose and scope, its definitions, references and identifier conventions, and the provenance of its sources."
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

Workbench terms (suite, project, molecular, continuum and physics model, study, variant, exposed value)
are defined in the Glossary of [`docs/design/workbench.md`](../docs/design/workbench.md); a deviation is
a switch away from the validated default (§5.3.3).

### 1.4 References

References are collected in §12. The normative sources are the Nanoscale paper and its ESI, the
CC-BY-4.0 thesis (`github.com/willemsk/phdthesis-text`, chs. 5–6), and the COMSOL model report
of §1.6.

### 1.5 Document conventions

Requirements use RFC 2119 keywords: SHALL (mandatory), SHOULD (recommended), MAY (optional). Each
carries a unique identifier, numbered within its class and zero-padded to two digits. Identifiers carry
a class prefix (IF, FR, QR, CON, PHY, NUM, VER, VAL, ADR, RSK, OPN); `SPECIFICATION.md`'s *Identifier to
file* maps each to its file.

Units are SI and explicit: nm, mol/L (M), K, V or mV, pN. Spelling is British.

### 1.6 Provenance and verification status

The sources were checked claim by claim; their errata are §4.6, and the author's rulings on
disagreements are
[`knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`](../knowledge/00-orientation/05-author-rulings-2026-08-these-override.md).

The overriding authority is the 162-page COMSOL model report `npgrid_clya_v8_NaCl_report.mph`
(COMSOL 5.4 build 388, dated 22 May 2020), read in full. Where it disagrees with the printed
sources or with author recollection, the model file governs. It settles the mesh, solver and
stabilisation questions, supplies full-precision fit coefficients and the permittivity parameters,
and writes the wall coefficient as `0.62e1`, i.e. 6.2.

---
