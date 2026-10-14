---
type: Orientation
title: Files
---

## Files

| File | Read it when |
|---|---|
| **`01-physics-epnpns.md`** | **First for physics work.** The normative equations, corrections, parameters and errata; read the governing sections before implementing, testing or reviewing model behaviour. Workflow-only and mechanical tasks need not load it. |
| `02-electrokinetics-background.md` | Underlying theory: double layers, Poisson–Boltzmann, electro-osmosis, selectivity, rectification. |
| `03-nanopore-biology.md` | Domain grounding: the pores, ClyA, electrophysiology, glossary. |
| `04-clya-geometry-and-charge.md` | The structure → geometry → mesh and charge pipelines; numeric validation targets. |
| `05-analyte-and-forces.md` | Embedded analyte bodies and forces. A continuum reference exists: the PlyAB work (Angew. Chem. 2022), §10. |
| `06-numerics-fem.md` | Weak forms, solvers, continuation, QoI extraction. |
| `07-software-stack.md` | Library versions, licences, why a dependency was chosen or rejected. |
| `08-validation-benchmarks.md` | Writing tests or interpreting a validation failure. |
| `09-comsol-reference-settings.md` | The original COMSOL mesh, solver and stabilisation settings, from the 5.4 model report. Read it before assuming our discretisation matches theirs: **their stabilisation was ON** in transport and flow. |
| `../data/corrections/willems2020_nacl.yaml` | The fitted correction parameters, transcribed and verified. |

---

