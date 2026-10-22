---
type: Specification
title: "11. Companion knowledge base"
description: "Describes the companion knowledge base shipped alongside the specification in the repository root, so that agents and people read verified sources."
---

## 11. Companion knowledge base

Shipped alongside this specification as `nanopnp-kb/` and held in the repository root from the
first commit, so that agents and people working on the codebase read from local, verified sources.

| Path | Content |
|---|---|
| `CLAUDE.md` | Agent instructions; points at the index; carries the maintenance rule |
| `knowledge/index.md` | The bundle's root index, declaring `okf_version` and listing the notes |
| `knowledge/00-orientation/index.md` | Traps, conventions, provenance, author rulings, open questions |
| `knowledge/log.md`, `knowledge/pending.yaml` | The dated log of the notes; the ledger of claims no test backs, which is empty |
| `knowledge/01-physics-epnpns/index.md` | Normative equations, corrections, parameters, errata |
| `knowledge/02-electrokinetics-background/index.md` | EDL, Poisson–Boltzmann, electro-osmosis, selectivity, rectification |
| `knowledge/03-nanopore-biology/index.md` | Biological nanopores, ClyA, electrophysiology, glossary |
| `knowledge/04-clya-geometry-and-charge/index.md` | The pipeline as executed, with numeric validation targets |
| `knowledge/05-analyte-and-forces/index.md` | Analyte representation, forces, trapping |
| `knowledge/06-numerics-fem/index.md` | Weak forms, solvers, continuation, QoI extraction |
| `knowledge/07-software-stack/index.md` | Libraries, versions, licences, tested behaviours |
| `knowledge/08-validation-benchmarks/index.md` | The four-tier benchmark ladder with formulas |
| `knowledge/09-comsol-reference-settings/index.md` | Reference mesh, solver and stabilisation settings |
| `data/corrections/willems2020_nacl.yaml` | Fitted correction parameters, transcribed and verified |
| `SPECIFICATION.md` | The specification's entry point: how to read it, and the map from section and identifier to file |
| `specification/index.md` | The specification bundle's root index, declaring `okf_version` and listing the sections |
| `specification/history/index.md` | The Phase 0 exit criteria and the dated rulings, read on demand, and where each ruling holds now |

The knowledge base is an Open Knowledge Format v0.2 bundle (§8.2.6 F6, §8.2.7 G12): a
directory per note, a concept per `##` section with a header (a `type` from a closed list, its
`sources`, and who generated and verified it), an `index.md` per directory and a `log.md` of dated
events. A claim verified by running code is marked `[tested: <test>]`, naming a surviving test
under `tests/`; a reading of a source is marked `[verified]`, with a footnote to a source of its
concept. No test checks the bundle's form; it is read at review (§8.2.13 N3). Anything unverified
says so. The maintenance rule, stated in
`CLAUDE.md`: when something durable is learned, it is written as a concept, with a line in the log.

---

