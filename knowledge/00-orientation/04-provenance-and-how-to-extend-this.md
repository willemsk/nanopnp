---
type: Orientation
title: Provenance and how to extend this
description: The primary sources and how a durable finding is added to the knowledge base.
tags:
- orientation
- orientation
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## Provenance and how to extend this

Primary sources: the thesis LaTeX (CC-BY-4.0, `github.com/willemsk/phdthesis-text`), the paper
(DOI `10.1039/D0NR03114C`), its bioRxiv preprint (`10.1101/2020.01.08.897819`), the ESI
(`rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf`) and the reference structure PDB **2WCD**
(ClyA dodecamer), variant **ClyA-AS**.

**When you learn something durable, write it here as a concept:** a discrepancy between sources, a
library behaviour found by testing, a numerical result that took effort to establish. Put it in the
directory of its note, list it in that directory's `index.md`, and add a dated line to `knowledge/log.md`.
Mark each claim `[tested: <test>]` or `[verified]` with a footnote to its source, and keep the header's
`verified` list equal to the tests the claims name. **Do not record** status, task lists or scope
opinions; those belong in the specification.

---

