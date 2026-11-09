---
type: Overview
title: ePNP-NS — the physics behind §4 (overview)
description: The status of the ePNP-NS concepts and how they relate to SPECIFICATION.md §4.
tags:
- physics
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

# ePNP-NS — the physics behind §4

**Status:** the backing of `SPECIFICATION.md` §4, which states the model normatively; where they
differ, §4 governs, and where the reference and the published text differ, the COMSOL model report
governs (`SPECIFICATION.md` §1.6). Transcribed from Willems K. et al., *Nanoscale* **12**,
16775–16795 (2020) and the CC-BY-4.0 thesis `willemsk/phdthesis-text`, ch. 5 + ch. 5 SI
(`epnpns.tex`, `epnpns_appendix.tex`).

§4 states the equations, the corrections and their coefficients. These concepts hold what §4 does
not: the Poisson weak form (`02-governing-equations.md`), the infinite-dilution sources and the
measured Einstein ratio (`03-the-corrections.md`), the rationale, the reference's charge
construction, the implementation notes, and the errata with their arithmetic
(`08-errata-in-the-source-with-the-arithmetic.md`, numbered as §4.6's rows).

Agents: do **not** re-derive the model from the paper abstract or from web summaries — several
widely-copied summaries of this model are wrong.

---
