---
type: Glossary
title: Glossary of project terminology and shorthands
description: Comprehensive glossary of nanopnp specification prefixes, numerical continuation ladders, rungs, review findings, and software architecture concepts.
tags:
- orientation
- glossary
- specification
sources:
- id: spec
  resource: SPECIFICATION.md
  title: The normative specification
- id: code
  resource: src/nanopnp/pipeline/run.py
  title: The pipeline walk (selected_stages)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-20T00:00:00Z'
---

# Glossary of project terminology and shorthands

## Section 1. Core shorthands

* **ladder**. The numerical continuation ladder defined in NUM-18. It defines a sequential homotopy path of nine rungs. It advances from a simple linear electrostatic problem to the fully coupled nonlinear continuum system. Each rung warm-starts from the converged solution of the preceding rung. Rungs 4, 5, and 9 contain parameter ramps, so a complete ladder solve executes many discrete numerical steps. The sequence enables robust convergence across the entire operating envelope. Enabling physical corrections last isolates their individual impact on numerical stability.

* **rung**. A single discrete sub-problem solved within the NUM-18 continuation ladder. The ladder numbers its rungs 1 to 9; these are not the pipeline stage numbers of the walk (section 5), which are a separate sequence. Each rung solves an intermediate model to convergence using damped Newton iterations. It transfers its converged state vector to initialise the next rung. The nine standard rungs proceed in a fixed sequence. Rung 1 solves linear Poisson-Boltzmann. Rung 2 solves nonlinear Poisson-Boltzmann. Rung 3 solves equilibrium Poisson-Nernst-Planck at zero bias and zero fluid velocity. Rung 4 ramps surface charge and pore charge from zero to target values. Rung 5 ramps applied voltage bias from zero to target potential in small steps. Rung 6 enables Stokes or Navier-Stokes hydrodynamic flow coupling. Rung 7 activates concentration-dependent and wall-distance-dependent property corrections for diffusivity, mobility, fluid viscosity, solvent permittivity, and solution density. Rung 8 enables steric flux. Rung 9 sweeps electrolyte salt concentration across the operating range. Re-solving an already converged rung costs at most one Newton step: when the entry residual is already below its target the solve returns before its first step (NUM-16, VER-44). **[verified][^spec]**

* **REV**. Review register findings tracked in docs/project/review-findings.md and review-items.md. They log items left open during work package implementation or review. Each item records its identifier, area, severity, status, and authoritative ruling. An item remains open until resolved by an author ruling or a resolving commit.

## Section 2. Specification and identifier prefixes

* **FR-nn**. Functional requirements defined in SPECIFICATION section 3.2. They specify mandatory software capabilities. Examples include structure ingestion, contour conditioning, charge assembly, and sweep dispatch.

* **QR-nn**. Quality of service requirements defined in SPECIFICATION section 3.3. They specify performance targets, memory ceilings, numerical accuracy limits, and platform compatibility.

* **CON-nn**. Design and implementation constraints defined in SPECIFICATION section 3.4. They enforce architectural boundaries, licensing obligations, and dependency restrictions.

* **PHY-nn**. Physics and model requirements defined in SPECIFICATION section 4. They specify the governing partial differential equations, constitutive relations, boundary conditions, and empirical property corrections.

* **NUM-nn**. Numerical methods requirements defined in SPECIFICATION section 6. They govern finite-element function spaces, weak formulations, hoop-strain assembly, quadrature rules, damping, and Newton convergence criteria.

* **IF-nn**. External interface requirements defined in SPECIFICATION section 3.1. They define programmatic contracts for the Python API, command-line interface, case file schemas, mesh formats, and field export files.

* **VER-nn**. Verification requirements and test identifiers defined in SPECIFICATION section 7 and Appendix A. They follow IEEE 1012 verification standards. They prove that the software solves the governing continuum equations correctly. Verification answers whether the code implements the mathematics correctly. Verification activities are partitioned across Tier 1 unit tests and Tier 2 analytic benchmarks.

* **VAL-nn**. Validation activity requirements defined in SPECIFICATION section 7. They follow IEEE 1012 validation standards. They evaluate whether the mathematical model represents the physical nanopore system with high fidelity. Validation answers whether the code models the correct physical reality. Tier 3 tests compare simulated results against archived reference simulations. Tier 4 tests compare simulated results against published experimental data.

* **ADR-nn**. Architecture decision records defined in SPECIFICATION section 5.6. They record significant architectural choices, evaluated alternatives, and their technical consequences. Examples include ADR-001 for the finite-element backend and ADR-002 for mesher adapters.

* **RSK-nn**. Risk register entries defined in SPECIFICATION section 9. They track project risks, severities, likelihoods, mitigations, and detection phases.

* **MOD-nn**. Modularity review findings recorded in docs/project/modularity-findings.md and ruled in SPECIFICATION section 8.2.8. They record findings from the Phase 4 architectural modularity exploration regarding coupling, layering, and extension points.

* **CR-nn**. Numbered comments of a code review of a pull request (for example CR-1 to CR-17 of PR #43). Those left open are carried as REV-nn items.

* **OPN-nn**. Open items register defined in SPECIFICATION section 10. They document open scientific questions, parameter uncertainties, and deferred technical decisions.

* **UT-nn**. User-testing findings, logged in docs/user-testing/findings.md once the Phase 4 sessions run and ruled by the author (SPECIFICATION section 8.2.8, H2 and H9). They track issues identified during end-user evaluation protocols.

* **WP-nn**. Work packages. They are scoped development increments that execute the phased project roadmap. Each package carries a dedicated plan in docs/plans/.

* **D1/D2**. Numbered decisions. They designate the rows of a work package plan's Decisions table and the rulings labelled D in a phase section of SPECIFICATION section 8.2 (for example D2 in section 8.2.4).

* **H1-H12**. Modularity report rulings defined in SPECIFICATION section 8.2.8. They represent twelve author rulings on the modularity report, its sequence and its fixes; H12 rules how open items are kept. They belong to the broader set of author rulings documented in SPECIFICATION section 8.2.

## Section 3. Physics and electrokinetics terms

* **ePNP-NS**. Extended Poisson-Nernst-Planck and Navier-Stokes continuum model. It couples electrostatic potential, ionic concentrations, and fluid velocity. It applies local concentration-dependent and wall-distance-dependent corrections to ionic diffusivity, ionic mobility, fluid viscosity, solvent permittivity, and solution density.

* **PNP-NS**. Classical Poisson-Nernst-Planck and Navier-Stokes model. It assumes bulk transport properties and uniform fluid properties throughout the domain. All extended correction factors equal unity.

* **PB**. Poisson-Boltzmann equation. It is a nonlinear mean-field model for equilibrium electrostatics. It assumes zero ionic flux and zero fluid flow.

* **DH**. Debye-Hückel theory. It is the linearised form of the Poisson-Boltzmann equation. It is valid when electrical potential is small compared to thermal voltage.

* **EDL**. Electrical double layer. It is the screening layer of ions that forms in the electrolyte adjacent to a charged surface. It consists of an excess of counter-ions and a depletion of co-ions.

* **Debye length**. The characteristic screening distance of the electrical double layer. It is denoted by lambda_D. It scales inversely with the square root of ionic strength.

* **EOF**. Electro-osmotic flow. It is bulk fluid motion driven by an applied electric field acting on net space charge within the electrical double layer.

* **steric flux (PHY-05)**. The ion-crowding term beta_i added to the Nernst-Planck flux bracket. It is species-dependent, through the prefactor a_i^3 / a_0^3 (4.16 for the reference NaCl parameters), and sums the concentration gradients of all species. It is singular as the packing fraction Phi approaches 1, which NUM-17 asserts against at every Newton step. It is not the single-species Bikerman form. **[verified][^spec]**

* **concentration-dependent permittivity (PHY-11)**. The fall of the solvent relative permittivity with local salt concentration, in the Langevin form fitted by Gavish. It is a function of the concentration alone, not of the electric field, so it is not a field-driven (Booth) saturation. **[verified][^spec]**

* **access resistance / Maxwell-Hall**. The spreading electrical resistance of the bulk electrolyte at the entrance and exit apertures of a pore. It scales inversely with pore diameter and electrolyte conductivity.

* **access conductance trap**. A common literature error that substitutes pore radius for diameter in Hall access conductance. The correct two-sided access resistance is rho over 2a, which equals 1 over sigma times d. Substituting radius for diameter under-predicts total conductance by about 16 percent for a = 2 nm and L = 13 nm only; other geometries differ (VER-17 note). **[verified][^spec]**

* **wall distance field (d, PHY-02)**. The scalar distance from any fluid point to the nearest pore boundary. The membrane boundary is explicitly excluded from this distance calculation. The field is clamped at zero to prevent the empirical wall functions from producing negative values or unphysical anti-diffusion.

* **wall functions**. Empirical correction functions that damp ionic mobility and increase fluid viscosity near solid boundaries. They evaluate local property reductions as a function of distance to the nearest pore wall.

* **G**. Total ionic conductance of the nanopore. It is defined as electrical current divided by applied voltage bias.

* **t_i**. Transport number of ionic species i. It represents the fraction of total electrical current carried by that species.

* **RR**. Rectification ratio. It is the ratio of ionic conductance at a positive voltage bias to conductance at the opposite negative bias.

* **PMF**. Potential of mean force. It represents the free-energy landscape experienced by an analyte along the pore axis. It is obtained by integrating axial electromechanical and hydrodynamic forces.

* **biological nanopore terms**. For domain definitions concerning biological pores, lipid bilayers, and single-channel electrophysiology, see the dedicated glossary in knowledge/03-nanopore-biology/08-glossary.md.

## Section 4. Numerics and meshing

* **2D axisymmetric (r, z)**. Two-dimensional cylindrical coordinate reduction. It models the physical domain using the radial coordinate r and axial coordinate z. It exploits rotational symmetry around the central pore axis.

* **C_n symmetry**. Cyclic rotational symmetry group of order n. A structure with C_n symmetry is invariant under rotations of 360/n degrees about the symmetry axis.

* **azimuthal averaging**. Projection of three-dimensional spatial data onto the two-dimensional (r, z) half-plane. It integrates quantities over the azimuthal angle in harmonic space.

* **damped Newton**. Monolithic nonlinear solver algorithm. It computes update steps from the full coupled Jacobian matrix. It damps step lengths based on residual reduction.

* **Taylor-Hood element pair**. The stable P2-P1 finite-element space pair. Velocity lives in continuous quadratic vector space P2. Pressure lives in continuous linear scalar space P1. This pair satisfies the Ladyzhenskaya-Babuška-Brezzi inf-sup stability condition without requiring artificial pressure stabilisation.

* **equal-order elements**. A discretisation using identical polynomial spaces for velocity and pressure, such as P1-P1. This combination violates the inf-sup condition. It requires Pressure-Stabilizing Petrov-Galerkin stabilisation to suppress spurious pressure modes.

* **P1 / P2 function spaces**. Continuous Lagrange finite-element polynomial spaces. In nanopnp, electrostatic potential and ionic concentrations live in P2. Velocity lives in vector P2. Pressure lives in P1.

* **SUPG / PSPG stabilisation**. Petrov-Galerkin finite-element stabilisation methods. Streamline-Upwind Petrov-Galerkin stabilises advection-dominated transport. Pressure-Stabilizing Petrov-Galerkin stabilises equal-order velocity and pressure elements. The production solve runs without stabilisation (NUM-11); SUPG is an optional flag.

* **direct linear solvers (UMFPACK / SuperLU)**. Sparse direct matrix factorisation libraries. They compute exact LU decompositions of the linearised Newton system at each iteration. They avoid iterative convergence issues in coupled indefinite systems.

* **SICN vs gamma**. Finite-element mesh quality metrics. Signed Inverted Condition Number is signed. A zero or negative SICN flags inverted or degenerate triangles. The gamma metric measures element equilateral shape but is unsigned, so it cannot detect inverted elements.

* **cylindrical hoop strain (NUM-05)**. The geometric viscous stress term 2 eta u_r v_r / r^2 of the cylindrical strong form, which the r integration weight reduces to 2 eta u_r v_r / r in the axisymmetric weak form. **[verified][^spec]** Omitting this term silently corrupts the computed velocity and pressure fields near the central symmetry axis.

* **dual-route agreement (NUM-26, QR-04)**. The requirement that total current computed via cross-sectional indicator integration and via variational reaction flux agree within 0.001 relative tolerance. **[verified][^spec]** Disagreement indicates numerical error or inadequate mesh refinement.

* **natural axis conditions (NUM-06)**. Boundary conditions on the symmetry axis r = 0. Only radial velocity u_r = 0 is an essential Dirichlet constraint. The radial derivatives of potential, concentrations, and axial velocity vanish naturally under the axisymmetric radial integration weight r.

* **MMS**. Method of manufactured solutions. It is an exact numerical verification method. It injects analytic solutions into differential operators to measure asymptotic spatial convergence rates.

* **Netgen / Gmsh**. Unstructured triangular mesh generation backends. Netgen is the built-in default engine. Gmsh is an optional alternative engine.

* **NGSolve**. The underlying finite-element library. It handles weak-form assembly, automatic differentiation, and sparse linear algebra.

## Section 5. Software architecture and pipeline

* **the walk**. The canonical pipeline that executes simulation workflows over the thirteen registered stages, minus those a case does not need (protonation, charge and region are dropped when nothing reads them). Stage 9 (case) executes first to resolve inputs and settings for all downstream stages. The walk then proceeds through structure ingestion, density map generation, symmetry reduction, contour extraction, CAD boundary assembly, mesh generation, protonation, fixed charge assembly, materials resolution, nonlinear solution, quantity of interest extraction, and reporting. Stage 7 comprises two registered stages, protonation and charge. **[verified][^code]**

* **case file**. Declarative YAML configuration document. It defines physical parameters, numerical options, boundary conditions, and file inputs. It is the primary unit of scientific reproducibility.

* **artefact**. An immutable data product emitted by a pipeline stage. It is identified by its schema version and content hash.

* **result store / cache**. A content-addressed filesystem cache. It stores and retrieves stage artefacts based on recipe hashes to avoid redundant computation.

* **manifest**. Run provenance document specified by FR-25. It records environment metadata, input digests, execution timings, mesh hashes, and model deviations.

* **deviations (FR-25)**. An explicit list in the run manifest documenting every physics switch or parameter set away from its validated default.

* **refusal vs failure**. Exit codes are a contract (IF-02). A refusal is a clean, diagnostic abort: exit code 3 for a case rejected by validation or schema, exit code 4 for a numerical gate abort of the QR-12 family. Exit code 5 is nonlinear non-convergence, an expected result at the corners of a sweep envelope. A failure is exit code 1, an unexpected exception, the only class whose traceback is worth keeping. **[verified][^spec]**

* **test tiers 1-4**. The four-tier verification and validation hierarchy. Tier 1 executes unit and property tests in seconds on every push. Tier 2 executes analytic benchmarks in minutes on every push and nightly. Tier 3 executes cross-implementation comparisons against reference COMSOL simulations. Tier 4 executes experimental reproduction benchmarks to gate releases.

[^spec]: SPECIFICATION.md: NUM-05, NUM-16, NUM-17, NUM-18, NUM-26, PHY-05, PHY-11, VER-17 and its NOTE, VER-44, IF-02.
[^code]: `selected_stages()` in `src/nanopnp/pipeline/run.py`.
