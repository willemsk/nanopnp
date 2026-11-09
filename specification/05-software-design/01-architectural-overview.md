---
type: Specification
title: "5.1 Architectural overview"
description: "The linear pipeline of cacheable stages and the module table: which subpackage owns what."
---

### 5.1 Architectural overview

The product is a linear pipeline of pure, cacheable stages. A stage takes typed inputs and emits a
typed, serialisable artefact carrying a content hash; every stage runs standalone, and every
artefact may be inspected, exported, edited and substituted by hand (FR-27). The Python API, the
CLI and the workbench drive the same stage objects (IF-01, IF-02, IF-09).

```
 case file ──►[9 case]──► feeds every stage below

 [1 structure]──┬──►[7 protonation]──┬──────────────────────────────────────┐
                │                    ▼                                      │
                ├───────────────►[2 density]──►[3 symmetry]──┐              │
                │                                            ▼              │
                └──────────────────────────────────────►[4 contour]         │
                                                             │              │
                                                             ▼              │
                                                         [5 region]──┐      │
                                                             │       │      │
                                                             ▼       ▼      ▼
                                                          [6 mesh]─►[7 charge]
                                                             │          │
                                                             └────┬─────┘
                                                                  │ mesh, charge
                                     [8 materials]──►[10 solve]◄──┤
                                                       │   │      │
                                                       │   ▼      │
                                                       │ [11 qoi]◄┤
                                                       │    │     │
                                                       ▼    ▼     │
                                                     [12 report]◄─┘
```

Each arrow is an input the stage registry declares (`core/stages.py`); the mesh and the charge
each feed stages 10, 11 and 12. Stage 9 reads the case file and resolves it, and every other stage
reads its resolved case. The two stages numbered 7 are told apart by name (§5.2's design note on
stage 7).

| Module | Responsibility |
|---|---|
| `core/` | Units and scaling, constants, content hashing, errors and exit classes, paths, the public-name list, the stage registry (`core/stages.py`) |
| `structure/` | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection |
| `density/` | Gaussian smearing to grid, ensemble averaging, grid IO |
| `symmetry/` | Cₙ averaging, azimuthal reduction to (r, z), variance diagnostics |
| `geometry/` | Contour extraction, polyline conditioning, CAD assembly, analyte bodies |
| `mesh/` | Mesher adapters (netgen, gmsh), size fields, quality gates; boundary layers are FR-11, after v1.0 |
| `numerics/` | Linear-solver adapters, damped Newton, the state and increment gates, the axisymmetric measure (§8.2.8 H11) |
| `charge/` | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric |
| `materials/` | Electrolyte models and the pluggable correction registry |
| `physics/` | Weak forms: Poisson, Nernst–Planck, Navier–Stokes; the wall-distance field |
| `solve/` | Continuation ladder, warm start, the solve stage |
| `post/` | QoI extraction: current, transport number, EOF, rectification, forces |
| `plot/` | Figures of every stage's artefact and of a sweep, drawn from the stored results alone with Matplotlib (the `plot` extra); imports no backend (§8.2.14 P3) |
| `sweep/` | Sweep documents, planning and result collection; the members run through the `Session` (`api/`) |
| `io/` | Case-file schema, artefact and resolved-case types, the solution-field vocabulary, result store, provenance manifests: the base every stage imports, importing only `core` at run time (`MOD-04`; WP38) |
| `pipeline/` | Case resolution and the checks against the registries, the pipeline walk: the assembler, which imports the stages (`MOD-04`; WP38) |
| `api/` | The Python interface: the `Case`, the `Session` that runs, sweeps and reopens it, and reproduction; the command line, the shell and the sweep runner run through it, above `sweep/` (IF-01; §8.2.23 Y4) |
| `cli/` | Command-line entry points |
| `gui/` | The browser workbench (NiceGUI, `gui/web/`), and the PySide6 shell until WP5.21 |
| `validation/` | Benchmarks, MMS, COMSOL comparison harness, regression fixtures |
| `case.py` (top level) | The public case module: `Case` and its blocks, re-exported from `api/` and `io/` |

The accepted import relation between these subpackages, its layer order and the subpackages that
reach the backend are recorded in `docs/project/modularity-layering.yaml` (VER-61, VER-65); read it
before adding an import across subpackages.

NOTE (the module table; §8.2.36 AL6): the site's *Architecture* page is generated from the tree at
each build. VER-79 holds this table's module rows equal to the subpackages; the responsibilities
are written here.
