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
* [5. Software design description](05-software-design/index.md) - Opens the software design and lists its subsections, one file each.
* [6. Numerical methods specification](06-numerics.md) - Fixes the discretisation and solution algorithm for the §4 model as NUM-nn requirements, and records where the reference implementation differs.
* [7. Verification and validation plan](07-verification/index.md) - Distinguishes verification (VER-nn) from validation (VAL-nn) activities and lists the plan's subsections.
* [8. Implementation plan](08-implementation-plan/index.md) - Opens the implementation plan and lists its subsections, one file each.
* [9. Risk register](09-risks.md) - Lists the RSK-nn risk register, each risk with its severity, likelihood, mitigation and detection phase.
* [10. Open items](10-open-items.md) - Lists the open items, OPN-nn, each with its owner and the work it blocks until settled.
* [11. Companion knowledge base](11-companion-knowledge-base.md) - Describes the companion knowledge base shipped alongside the specification in the repository root, so that agents and people read verified sources.
* [12. References](12-references.md) - Lists the normative sources, numerical methods, software and standards cited by the specification.
* [Appendix A. Requirements traceability matrix](a-traceability-matrix.md) - Maps each requirement of §3 to the activity of §7 that demonstrates it, marking those with none yet specified.
* [Appendix B. Reference COMSOL model settings](b-comsol-settings.md) - Condenses the reference COMSOL model settings from the 162-page model report; the full detail is in the knowledge base.
* [History](history/index.md) - The Phase 0 exit criteria and the author's dated rulings, §8.2.1 to §8.2.20, and where each ruling holds now.
