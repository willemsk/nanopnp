---
type: Overview
title: ClyA-AS — geometry, fixed charge, and validation targets (overview)
description: The ClyA-AS pipelines from structure to geometry, charge and mesh, and the numeric validation
  targets.
tags:
- clya
- overview
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

# ClyA-AS — geometry, fixed charge, and validation targets

**Status:** authoritative for the *reference case*. Transcribed from the thesis ch. 6 and ch. 6 SI
(`chapters/transport/transport.tex`, `chapters/transport_appendix/transport_appendix.tex`) =
Willems et al., *Nanoscale* **12**, 16775 (2020). MD setup details are cross-referenced by ch. 6
into ch. 4 (`chapters/electrostatics/electrostatics.tex`, `sec:elec:methods:molec`) and are
transcribed from there.

**Scope.** This file covers *only* the ClyA-specific pipeline and numbers. Governing equations,
correction functions, their parameters, and the errata belong to `knowledge/01-physics-epnpns/index.md` and are not
repeated. Citation keys below: **T** = `transport.tex`, **TA** = `transport_appendix.tex`,
**E** = `electrostatics.tex`; `Lnnn` = line number at time of transcription.

---

