---
type: Library Behaviour
title: 7. Local assets
description: The external sources the knowledge base cites, and where each lives.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  pyyaml: 6.0.3
  scikit-image: 0.26.0
  shapely: 2.1.2
---

## 7. Local assets

The external sources the knowledge base cites, and where each lives. None is in this repository.

| Source | Where | What |
|---|---|---|
| The thesis | `github.com/willemsk/phdthesis-text`, CC-BY-4.0, cloned beside the checkout when needed | LaTeX source of the full thesis, all parameter tables included; the notes cite commit `43d0f0f` |
| The paper | Willems et al., *Nanoscale* **12**, 16775–16795 (2020), `doi.org/10.1039/D0NR03114C` | The published model and results |
| The ESI and the COMSOL model report | The paper's electronic supplementary information, `rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf`, distributes the COMSOL 5.4 model report of 22 May 2020 (162 pages) | The model's parameters, mesh, solver and physics settings (`knowledge/09-comsol-reference-settings/`); the author holds the model file |
| The author's contour script | `create_polygon_contour` in the author's `pqr2grid` (MIT, 2019) | Read 26 September 2026: `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md#12-the-authors-contour-script-read` |
| COMSOL models | The author's licence | An optional field oracle while the licence lasts (RSK-14); no release waits on it |
