# Software Specification — nanopnp

Open-source continuum simulation of biological nanopores (ePNP-NS)

| Field | Value |
|---|---|
| Package | `nanopnp` |
| Version | None of its own: the specification is versioned with the code, by the release tags of §2.7. The text a release was built against is this tree at its tag, and [`CHANGELOG.md`](CHANGELOG.md) lists every tag with what changed |
| History | The author's dated rulings, with their reasons, are [`specification/history/`](specification/history/index.md); every edit is in `git log -- SPECIFICATION.md specification/` |
| Author of record | Kherim Willems |
| Structure | ISO/IEC/IEEE 29148 (requirements), IEEE 1016 (design), IEEE 1012 (verification and validation) |

---


## How to read this specification

This file is the entry point. The specification itself is the OKF bundle [`specification/`](specification/index.md),
one file per section; this file holds the title block, the reading rule and the maps.

- **Read the current files by default.** They state what holds today, in the present tense. Every
  requirement, design clause and numerical method is in them, and `SPECIFICATION.md` is normative
  through them.
- **Read [`specification/history/`](specification/history/index.md) on demand.** It holds the Phase 0
  exit criteria and the author's dated rulings (§8.2.1 to §8.2.21), verbatim, with the reasons. Read
  it when the reason behind a rule is wanted. Its index says where each ruling holds now.
- **The rules of the development process** that no clause of its own carries are §8.4
  ([`specification/08-implementation-plan/04-development-process.md`](specification/08-implementation-plan/04-development-process.md)).
- **Print a clause by its identifier** with `uv run .claude/scripts/clause.py VER-62 §7.6 J8`: it prints
  the definition, then every NOTE and ruling that names it, each labelled with its file and lines.
- A reference to `SPECIFICATION.md §x` names the section of that number, wherever it lives. The map below
  gives its file.

### Authority and conventions

- **Keywords.** SHALL is mandatory, SHOULD recommended, MAY optional (RFC 2119), and every
  requirement carries a unique identifier (§1.5). A withdrawn `VER-` row stays, and its identifier is
  not reused (§7.2).
- **Precedence.** This specification governs the plans in `docs/plans/`, the documentation and the
  code. For the physics, §4 is backed by the normative concepts of
  [`knowledge/01-physics-epnpns/`](knowledge/01-physics-epnpns/index.md); where sources disagree, the
  COMSOL model report governs (§1.6), and the errata in the sources are §4.6.
- **A NOTE** that names a clause belongs with it; `clause.py` prints it after the clause.
- **Units** are SI and explicit, and spelling is British (§1.5).

### Where to start, by task

| Task | Read |
|---|---|
| Implement or change a pipeline stage | §3.2 (its FR), §5.2, §5.3.2, then the PHY or NUM clauses it cites |
| Change the case file | §5.3.1, §5.3.3, Appendix A |
| Touch the physics or a correction | §4 and [`knowledge/01-physics-epnpns/`](knowledge/01-physics-epnpns/index.md), then §6 |
| Touch the numerics, solver or mesh | §6, §7.3 |
| Write or judge a test | §7.1 (tiers and the test scope), the VER or VAL row, Appendix A |
| Plan or ship a work package | §8.1, §8.4, then [`docs/plans/current.md`](docs/plans/current.md) |

### Changing the specification

- A change of specified behaviour edits the clause in its current file, in the same commit as the code.
- An author's ruling is recorded verbatim as a new file in `specification/history/`, listed in
  [`specification/history/index.md`](specification/history/index.md) with where it holds now; the site's navigation is
  generated from the index pages. A ruling that sets a standing rule of process with no clause of its
  own is also restated in §8.4.
- A new file in the bundle opens with the front matter `type`, `title` and `description`, and is listed
  in its directory's `index.md`.

### Section to file

| Section | File |
|---|---|
| §1 Introduction (purpose, scope, definitions, conventions, provenance) | [`specification/01-introduction.md`](specification/01-introduction.md) |
| §2 Product overview (S1–S4 scenarios, P1–P3 personas, release scope) | [`specification/02-product-overview.md`](specification/02-product-overview.md) |
| §3 Requirements (IF, FR, QR, CON; N1–N7 exclusions) | [`specification/03-requirements.md`](specification/03-requirements.md) |
| §4 Physics specification (PHY) | [`specification/04-physics.md`](specification/04-physics.md) |
| §5 Software design: introduction | [`specification/05-software-design/index.md`](specification/05-software-design/index.md) |
| §5.1 Architectural overview | [`specification/05-software-design/01-architectural-overview.md`](specification/05-software-design/01-architectural-overview.md) |
| §5.2 Pipeline stages | [`specification/05-software-design/02-pipeline-stages.md`](specification/05-software-design/02-pipeline-stages.md) |
| §5.3, §5.3.1 Data design, the case file | [`specification/05-software-design/03-1-case-file.md`](specification/05-software-design/03-1-case-file.md) |
| §5.3.2 Artefacts and interchange formats | [`specification/05-software-design/03-2-artefacts.md`](specification/05-software-design/03-2-artefacts.md) |
| §5.3.3 Provenance manifest | [`specification/05-software-design/03-3-provenance-manifest.md`](specification/05-software-design/03-3-provenance-manifest.md) |
| §5.3.4 Sweep specification and dataset | [`specification/05-software-design/03-4-sweeps.md`](specification/05-software-design/03-4-sweeps.md) |
| §5.4 Component design | [`specification/05-software-design/04-component-design.md`](specification/05-software-design/04-component-design.md) |
| §5.5 Extension points | [`specification/05-software-design/05-extension-points.md`](specification/05-software-design/05-extension-points.md) |
| §5.6 Architecture decisions (ADR) | [`specification/05-software-design/06-architecture-decisions.md`](specification/05-software-design/06-architecture-decisions.md) |
| §6 Numerical methods (NUM) | [`specification/06-numerics.md`](specification/06-numerics.md) |
| §7 Verification and validation: introduction | [`specification/07-verification/index.md`](specification/07-verification/index.md) |
| §7.1 Strategy and ordering, the test scope | [`specification/07-verification/01-strategy.md`](specification/07-verification/01-strategy.md) |
| §7.2 Tier 1 (VER) | [`specification/07-verification/02-tier-1.md`](specification/07-verification/02-tier-1.md) |
| §7.3 Tier 2 (VER) | [`specification/07-verification/03-tier-2.md`](specification/07-verification/03-tier-2.md) |
| §7.4 Tier 3 (VAL) | [`specification/07-verification/04-tier-3.md`](specification/07-verification/04-tier-3.md) |
| §7.5 Tier 4 (VAL) | [`specification/07-verification/05-tier-4.md`](specification/07-verification/05-tier-4.md) |
| §7.6 Continuous integration | [`specification/07-verification/06-continuous-integration.md`](specification/07-verification/06-continuous-integration.md) |
| §8 Implementation plan: introduction | [`specification/08-implementation-plan/index.md`](specification/08-implementation-plan/index.md) |
| §8.1 Phases and gates | [`specification/08-implementation-plan/01-phases-and-gates.md`](specification/08-implementation-plan/01-phases-and-gates.md) |
| §8.2 Rulings by date (a stub pointing to the history) | [`specification/08-implementation-plan/02-rulings.md`](specification/08-implementation-plan/02-rulings.md) |
| §8.2 Phase 0 exit criteria and §8.2.1 to §8.2.21, the dated rulings | [`specification/history/index.md`](specification/history/index.md) |
| §8.3 Effort estimate | [`specification/08-implementation-plan/03-effort-estimate.md`](specification/08-implementation-plan/03-effort-estimate.md) |
| §8.4 Development process | [`specification/08-implementation-plan/04-development-process.md`](specification/08-implementation-plan/04-development-process.md) |
| §9 Risk register (RSK) | [`specification/09-risks.md`](specification/09-risks.md) |
| §10 Open items (OPN) | [`specification/10-open-items.md`](specification/10-open-items.md) |
| §11 Companion knowledge base | [`specification/11-companion-knowledge-base.md`](specification/11-companion-knowledge-base.md) |
| §12 References | [`specification/12-references.md`](specification/12-references.md) |
| Appendix A Requirements traceability matrix | [`specification/a-traceability-matrix.md`](specification/a-traceability-matrix.md) |
| Appendix B Reference COMSOL model settings | [`specification/b-comsol-settings.md`](specification/b-comsol-settings.md) |

### Identifier to file

| Identifier | Defined in |
|---|---|
| `FR-nn`, `QR-nn`, `CON-nn`, `IF-nn` | [`specification/03-requirements.md`](specification/03-requirements.md) |
| `PHY-nn` | [`specification/04-physics.md`](specification/04-physics.md) |
| `NUM-nn` | [`specification/06-numerics.md`](specification/06-numerics.md) |
| `VER-nn` | [`specification/07-verification/02-tier-1.md`](specification/07-verification/02-tier-1.md), [`specification/07-verification/03-tier-2.md`](specification/07-verification/03-tier-2.md) |
| `VAL-nn` | [`specification/07-verification/04-tier-3.md`](specification/07-verification/04-tier-3.md), [`specification/07-verification/05-tier-4.md`](specification/07-verification/05-tier-4.md) |
| `ADR-nn` | [`specification/05-software-design/06-architecture-decisions.md`](specification/05-software-design/06-architecture-decisions.md) |
| `RSK-nn` | [`specification/09-risks.md`](specification/09-risks.md) |
| `OPN-nn` | [`specification/10-open-items.md`](specification/10-open-items.md) |
| `S1`–`S4`, `P1`–`P3` | [`specification/02-product-overview.md`](specification/02-product-overview.md) |
| `N1`–`N7` (exclusions) | [`specification/03-requirements.md`](specification/03-requirements.md) |
| A letter and a number (`A1`, `J8`, `R10`: a ruling) | [`specification/history/index.md`](specification/history/index.md) |
| A requirement's tracing to a test | [`specification/a-traceability-matrix.md`](specification/a-traceability-matrix.md) |

Identifiers outside the specification: `REV-nn`, the open review items, are in
[`docs/project/review-findings.md`](docs/project/review-findings.md); `MOD-nn`, the modularity findings, in
[`docs/project/modularity-findings.md`](docs/project/modularity-findings.md).
