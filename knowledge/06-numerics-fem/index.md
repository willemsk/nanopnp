# Numerics — FEM formulation, solvers, and quantities of interest

* [Numerics — FEM formulation, solvers, and quantities of interest (overview)](00-overview.md) - The finite-element formulation, solvers and quantities of interest, with the measurements behind each choice.
* [1. Discretisation](01-discretisation.md) - The discretisation: elements, spaces and assembly.
* [2. Axisymmetric weak forms](02-axisymmetric-weak-forms.md) - The axisymmetric weak forms, the axis and the quadrature order that avoids NaN.
* [3. Nondimensionalisation](03-nondimensionalisation.md) - Points to NUM-09's scales and NUM-10's row scaling, and why no field-wise row scaling is applied.
* [4. Stabilisation](04-stabilisation.md) - Stabilisation: the mode as built and what each term does.
* [5. Nonlinear solution](05-nonlinear-solution.md) - The nonlinear solution: damped Newton, convergence tests and the continuation ladder.
* [6. Linear solvers](06-linear-solvers.md) - UMFPACK and SuperLU measured at production size, which NUM-21's NOTE cites; NUM-21 and NUM-22 state the solver choices.
* [7. Quantities of interest — and the flux trap](07-quantities-of-interest-and-the-flux-trap.md) - The quantities of interest, the flux trap and the routes that extract them.
* [8. Mesh resolution and adaptivity](08-mesh-resolution-and-adaptivity.md) - Mesh resolution and adaptivity, measured against the reference mesh.
* [NGSolve traps and measured numerics facts](09-ngsolve-traps-found-by-implementing.md) - The NGSolve traps found by implementing the model, all silent, then measured facts: the reaction flux, convergence and solver facts, sweep warm starts and parallel scaling, the zero-bias route check, the gate sampler and the gate constants.
* [9. Unverified / to measure](10-unverified-to-measure.md) - Items still unverified or to be measured.
* [Tier-1 test evidence: norms and the attribution identity](11-tier-1-test-evidence-norms-and-the.md) - The relative L² norms on known fields, the axis defect the r-weighted norm hides, the pressure gauge, and why the attribution identity cannot see a stale golden.
* [Tier-1 test evidence: the Langevin cutoff](12-tier-1-test-evidence-the-langevin.md) - A pointer to the Langevin series cutoff, recorded with the physics.
* [Tier-1 test evidence: the domain indicator and the quality measures](13-tier-1-test-evidence-the-domain.md) - Why the current indicator is built on the fluid, its leak past the band, the smoothstep's slope, and why gamma is blind to an inverted element and SICN is not.
* [Tier-1 test evidence: Newton's counterexamples, the band and the vector indicator](14-tier-1-test-evidence-newtons.md) - Newton's two counterexamples, the current's independence of where the indicator band sits, the vector indicator of NUM-25, and the permittivity sensitivity with its correction off.
* [Tier-1 test evidence: scaling, the wall-distance clamp and the warm-start rationale](15-tier-1-test-evidence-scaling-the-wall.md) - The Péclet number and force scale, the wall forms' clamp and gate, the restore of a stored distance field, the zero-wind stabilisation, and the reference sweep's pairing.
* [Tier-2 test evidence: ladder walks, block systems and extraction routes](16-tier-2-test-evidence-ladder-walks-block.md) - The access-conductance benchmark, the wall-pinned trivial state, the block system's constraints, the force tolerance and reference record, the envelope walk, and the route agreement under stabilisation.
* [Test-suite fixtures: the pickled reference mesh, the stability golden, the seed case](17-tier-3-test-evidence-the-mesh-geometry.md) - Why the reference mesh is pickled, why the stability golden takes no difference of two routes, and what the seeded stages 1 to 3 key on.
