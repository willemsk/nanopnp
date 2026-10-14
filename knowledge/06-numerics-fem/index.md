# Numerics — FEM formulation, solvers, and quantities of interest

* [Numerics — FEM formulation, solvers, and quantities of interest (overview)](00-overview.md) - The finite-element formulation, solvers and quantities of interest, with the measurements behind each choice.
* [1. Discretisation](01-discretisation.md) - The discretisation: elements, spaces and assembly.
* [2. Axisymmetric weak forms](02-axisymmetric-weak-forms.md) - The axisymmetric weak forms, the axis and the quadrature order that avoids NaN.
* [3. Nondimensionalisation](03-nondimensionalisation.md) - The nondimensionalisation and the scales that keep every field of order one.
* [4. Stabilisation](04-stabilisation.md) - Stabilisation: the mode as built and what each term does.
* [5. Nonlinear solution](05-nonlinear-solution.md) - The nonlinear solution: damped Newton, convergence tests and the continuation ladder.
* [6. Linear solvers](06-linear-solvers.md) - Linear solvers, with UMFPACK and SuperLU measured at production size.
* [7. Quantities of interest — and the flux trap](07-quantities-of-interest-and-the-flux-trap.md) - The quantities of interest, the flux trap and the routes that extract them.
* [8. Mesh resolution and adaptivity](08-mesh-resolution-and-adaptivity.md) - Mesh resolution and adaptivity, measured against the reference mesh.
* [8.1 NGSolve traps found by implementing this — all silent](09-ngsolve-traps-found-by-implementing.md) - NGSolve traps found by implementing the model, all of them silent.
* [9. Unverified / to measure](10-unverified-to-measure.md) - Items still unverified or to be measured.
* [Tier-1 test evidence: norms and the attribution identity (WP45 item 20)](11-tier-1-test-evidence-norms-and-the.md) - What the Tier-1 tests of norms and the attribution identity establish, recorded at WP45 item 20.
* [Tier-1 test evidence: the Langevin cutoff (WP45 item 21)](12-tier-1-test-evidence-the-langevin.md) - What the Tier-1 tests of the Langevin cutoff establish, recorded at WP45 item 21.
* [Tier-1 test evidence: the domain indicator and the quality measures (WP45 item 22)](13-tier-1-test-evidence-the-domain.md) - What the Tier-1 tests of the domain indicator and the quality measures establish, recorded at WP45 item 22.
* [Tier-1 test evidence: Newton's counterexamples, the band and the vector indicator (WP45 item 23)](14-tier-1-test-evidence-newtons.md) - What the Tier-1 tests of Newton's counterexamples, the band and the vector indicator establish, recorded at WP45 item 23.
* [Tier-1 test evidence: scaling, the wall-distance clamp and the warm-start rationale (WP45 item 24)](15-tier-1-test-evidence-scaling-the-wall.md) - What the Tier-1 tests of scaling, the wall-distance clamp and the warm-start rationale establish, recorded at WP45 item 24.
* [Tier-2 test evidence: ladder walks, block systems and extraction routes (WP45 item 25)](16-tier-2-test-evidence-ladder-walks-block.md) - What the Tier-2 tests of ladder walks, block systems and extraction routes establish, recorded at WP45 item 25.
* [Tier-3 test evidence: the mesh geometry digest (WP45 item 27)](17-tier-3-test-evidence-the-mesh-geometry.md) - What the Tier-3 tests of the mesh geometry digest establish, recorded at WP45 item 27.
