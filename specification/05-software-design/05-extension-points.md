---
type: Specification
title: "5.5 Extension points"
description: "Specifies the two levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration."
---

### 5.5 Extension points

Pluggability has two levels, matching the two kinds of change users make (QR-14). Below them, the
backends of the discretisation are registries as well (§8.2.8 H7): a mesher (`numerics.mesh.backend`,
`mesh/meshers.py`), a linear solver (`numerics.linear.solver`, `numerics/linear.py`) and a
stabilisation mode (`numerics.stabilisation`, `physics/stabilisation.py`) are each added by one
registration, and each key is a string checked against its registry when a case is loaded, as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and `sparsecholesky`
cannot be registered (NUM-21). Whether the registering functions are public waits for `MOD-11`'s
ruling (§8.2.8 H2).

| Level | Unit of extension | Requires | Obtained free |
|---|---|---|---|
| 1, correction models | A versioned data file naming a registered model and its coefficients | No code | Recording of the model version on every result; correction-by-correction switching as a configuration sweep |
| 2, physics models | One class against the §5.4.3 interface | One file | Meshing, geometry, charge assembly, continuation, QoI extraction, sweeps, provenance and the GUI |

Shipped physics models (PHY-21, FR-18, FR-19).

| Model | Fields | Notes |
|---|---|---|
| `epnp-ns` | φ, c_i, u, p | The validated default |
| `pnp-ns` | φ, c_i, u, p | The same model with corrections off; a configuration, not code |
| `pnp` | φ, c_i | No flow coupling |
| `pb` | φ | Nonlinear Poisson–Boltzmann, equilibrium; a separate model, not the PNP solver at zero bias (PHY-14, PHY-24) |
| `pb-linear` | φ | Debye–Hückel; an initialiser and the basis of the DWR error estimator |
| `poisson` | φ | Electrostatics only; the APBS cross-check target |

Since ePNP-NS reduces exactly to PNP-NS at β_i = 0 with all f^c = f^w = 1, the PNP-against-ePNP
comparison and the contribution of each individual correction are configuration sweeps, and are the
project's primary differential-testing instrument (§7.4).

Boundary of the framework (N1): a nanopore transport solver with swappable physics models, which
will not become a general symbolic PDE framework. Users do not write weak forms. A model may be
swapped or extended; an unrelated multiphysics problem may not be posed, and users wanting
arbitrary weak forms should use NGSolve or FEniCS directly. Deriving new correction
parameterisations from MD is a separate later tool (N6).
