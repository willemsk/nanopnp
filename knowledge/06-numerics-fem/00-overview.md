---
type: Overview
title: Numerics — FEM formulation, solvers, and quantities of interest (overview)
description: The finite-element formulation, solvers and quantities of interest, with the measurements
  behind each choice.
tags:
- numerics
- overview
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

# Numerics — FEM formulation, solvers, and quantities of interest

Reference for agents implementing or modifying the solver. `SPECIFICATION.md` §4 and §6 state the
equations and the numerics; these concepts hold what building them measured. Companions:
`knowledge/01-physics-epnpns/index.md` and `knowledge/08-validation-benchmarks/index.md` (the tests).
Open items: `10-unverified-to-measure.md`.

Read when:

- **02** you touch the axis or a quadrature order; **04** the stabilisation; **05** the Newton
  convergence test, the ladder or a warm start; **06** the linear solver.
- **07** you extract a current, a transport number or a force.
- **09**, the NGSolve traps, before you touch `physics/`, `numerics/` or `solve/`.
- **11 to 17** you change the test they name: each records why its test asserts what it does.

---

