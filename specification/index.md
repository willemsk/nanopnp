---
okf_version: "0.2"
---

# nanopnp specification

The normative specification of `nanopnp`, one file per section. The sections hold what is true now; the
author's dated rulings, with their reasons, are the [history](history/index.md), read on demand. The
entry point, [SPECIFICATION.md](../SPECIFICATION.md), says how to read the bundle and maps each section
and identifier to its file. The rules of the development process that no clause of its own carries are
§8.4, in [08-implementation-plan](08-implementation-plan/index.md).

* [1. Introduction](01-introduction.md) - Specifies nanopnp, an open-source Python replacement for a COMSOL nanopore workflow, and maps the specification's sections.
* [2. Product overview](02-product-overview.md) - Places nanopnp beside COMSOL in the source work, and describes the reference implementation, product functions, users, environment and release scope.
* [3. Requirements](03-requirements.md) - Sets out the external interfaces, functional requirements, quality of service, design constraints and exclusions the product must meet.
* [4. Physics specification (normative)](04-physics.md) - States the normative ePNP-NS physics: domains and symbols, governing equations, empirical corrections, fixed charge, dielectric model and switches.
* [5.1 Architectural overview](05-software-design/01-architectural-overview.md) - Describes the linear pipeline of pure, cacheable stages, each emitting a typed, content-hashed artefact that can run and be inspected standalone.
* [5.2 Pipeline stages](05-software-design/02-pipeline-stages.md) - Tabulates each pipeline stage with its inputs, outputs, tools and validation gate.
* [5.3 Data design](05-software-design/03-1-case-file.md) - Specifies the case file as one declarative YAML document, the unit of reproducibility from which everything else is derived.
* [5.3.2 Artefacts and interchange formats](05-software-design/03-2-artefacts.md) - Lists the artefact each stage emits and its format, native or interchange.
* [5.3.3 Provenance manifest](05-software-design/03-3-provenance-manifest.md) - Specifies the provenance manifest emitted with every result, sufficient alone to reconstruct the run, and the run directory naming.
* [5.3.4 Sweep specification and dataset](05-software-design/03-4-sweeps.md) - Specifies sweeps, sets of runs described by their own declarative document that names a base case and the axes to vary.
* [5.4 Component design](05-software-design/04-component-design.md) - Specifies the physics/ design: weak forms written once against a thin internal interface, with one production NGSolve implementation.
* [5.5 Extension points](05-software-design/05-extension-points.md) - Specifies the two levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration.
* [5.6 Architecture decisions](05-software-design/06-architecture-decisions.md) - Records the architecture decisions, beginning with NGSolve as the single production backend behind the abstraction of §5.4.1.
* [6. Numerical methods specification](06-numerics.md) - Fixes the discretisation and solution algorithm for the §4 model as NUM-nn requirements, and records where the reference implementation differs.
* [7.1 Strategy and ordering](07-verification/01-strategy.md) - Sets out the verification strategy: the four test tiers, their runtimes, frequencies and roles in the phase gates.
* [7.2 Tier 1 unit and property tests](07-verification/02-tier-1.md) - Lists the Tier 1 unit and property tests (VER-01 onward), each with its acceptance criterion.
* [7.3 Tier 2 analytic benchmarks](07-verification/03-tier-2.md) - Specifies the Tier 2 analytic benchmarks, which verify the axisymmetric weak forms, axis treatment and coupling against closed-form solutions.
* [7.4 Tier 3 cross-implementation comparison](07-verification/04-tier-3.md) - Specifies the Tier 3 cross-implementation comparison against the paper's published current–voltage relationships and in-pore averages.
* [7.5 Tier 4 experimental reproduction](07-verification/05-tier-4.md) - Lists the Tier 4 experimental reproduction activities (VAL-07 onward), each with its acceptance criterion against experiment.
* [7.6 Continuous integration](07-verification/06-continuous-integration.md) - Maps each CI trigger, a pull request, a push to main, or the nightly run, to the tiers and platforms it runs.
* [8.1 Phases and gates](08-implementation-plan/01-phases-and-gates.md) - Lists each implementation phase with its deliverable, gate and estimate, from the Phase 0 spike onwards.
* [8.2 Rulings by date](08-implementation-plan/02-rulings.md) - Points to the Phase 0 exit criteria and the author's dated rulings, §8.2.1 to §8.2.16, now held in the history folder.
* [8.3 Effort estimate](08-implementation-plan/03-effort-estimate.md) - Estimates effort to the validated release: 6 to 9 part-time months without the desktop GUI, 9 to 14 with it.
* [9. Risk register](09-risks.md) - Lists the RSK-nn risk register, each risk with its severity, likelihood, mitigation and detection phase.
* [10. Open items](10-open-items.md) - Lists the open items, OPN-nn, each with its owner and the work it blocks until settled.
* [11. Companion knowledge base](11-companion-knowledge-base.md) - Describes the companion knowledge base shipped alongside the specification in the repository root, so that agents and people read verified sources.
* [12. References](12-references.md) - Lists the normative sources, numerical methods, software and standards cited by the specification.
* [Appendix A. Requirements traceability matrix](a-traceability-matrix.md) - Maps each requirement of §3 to the activity of §7 that demonstrates it, marking those with none yet specified.
* [Appendix B. Reference COMSOL model settings](b-comsol-settings.md) - Condenses the reference COMSOL model settings from the 162-page model report; the full detail is in the knowledge base.
* [History](history/index.md) - The Phase 0 exit criteria and the author's dated rulings, §8.2.1 to §8.2.16, and where each ruling holds now.
