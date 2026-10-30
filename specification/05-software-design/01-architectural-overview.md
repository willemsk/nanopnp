---
type: Specification
title: "5.1 Architectural overview"
description: "Describes the linear pipeline of pure, cacheable stages, each emitting a typed, content-hashed artefact that can run and be inspected standalone."
---

### 5.1 Architectural overview

The product is a linear pipeline of pure, cacheable stages. A stage takes typed inputs and emits a
typed, serialisable artefact carrying a content hash; every stage runs standalone, and every
artefact may be inspected, exported, edited and substituted by hand (FR-27). The Python API, the
CLI and the desktop shell drive the same stage objects (IF-01, IF-02, IF-09).

```
 PDB/mmCIF ──┐
 trajectory ─┼─►[1 structure]─►[2 density]─┬─►[3 symmetry]─►[4 contour]─►[5 CAD]─►[6 mesh]─┐
 pH, force field ┘                         │                                               │
                                           └─►[7 charge]────────────────────────────────────┤
 electrolyte, corrections ────────────────────►[8 materials]────────────────────────────────┼─►[9 case]
 bias, BCs, analyte ───────────────────────────────────────────────────────────────────────►┘     │
                                                                                                  ▼
                                                    [12 report / export]◄──[11 QoI]◄──[10 solve]
```

| Module | Responsibility |
|---|---|
| `core/` | Units, constants, validation, provenance, caching, logging |
| `structure/` | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection |
| `density/` | Gaussian smearing to grid, ensemble averaging, grid IO |
| `symmetry/` | Cₙ averaging, azimuthal reduction to (r, z), variance diagnostics |
| `geometry/` | Contour extraction, polyline conditioning, CAD assembly, analyte bodies |
| `mesh/` | Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates |
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
| `gui/` | Desktop application |
| `validation/` | Benchmarks, MMS, COMSOL comparison harness, regression fixtures |
