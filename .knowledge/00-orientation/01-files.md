---
type: Orientation
title: Files
---

## Files

| File | Read it when |
|---|---|
| **`.knowledge/01-physics-epnpns/index.md`** | **First for physics work.** The normative equations, corrections, parameters and errata; read the governing sections before implementing, testing or reviewing model behaviour. Workflow-only and mechanical tasks need not load it. |
| `.knowledge/02-electrokinetics-background/index.md` | Underlying theory: double layers, Poisson–Boltzmann, electro-osmosis, selectivity, rectification. |
| `.knowledge/03-nanopore-biology/index.md` | Domain grounding: the pores, ClyA, electrophysiology, glossary. |
| `.knowledge/04-clya-geometry-and-charge/index.md` | The structure → geometry → mesh and charge pipelines; numeric validation targets. |
| `.knowledge/05-analyte-and-forces/index.md` | Embedded analyte bodies and forces. A continuum reference exists: the PlyAB work (Angew. Chem. 2022), §10. |
| `.knowledge/06-numerics-fem/index.md` | Weak forms, solvers, continuation, QoI extraction. |
| `.knowledge/07-software-stack/index.md` | Library versions, licences, why a dependency was chosen or rejected. |
| `.knowledge/08-validation-benchmarks/index.md` | Writing tests or interpreting a validation failure. |
| `.knowledge/09-comsol-reference-settings/index.md` | The original COMSOL mesh, solver and stabilisation settings, from the 5.4 model report. Read it before assuming our discretisation matches theirs: **their stabilisation was ON** in transport and flow. |
| `../data/corrections/willems2020_nacl.yaml` | The fitted correction parameters, transcribed and verified. |

---

