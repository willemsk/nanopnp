# Software Specification — nanopnp

Open-source continuum simulation of biological nanopores (ePNP-NS)

| Field | Value |
|---|---|
| Package | `nanopnp` |
| Version | 0.5 |
| Date | 16 August 2026 |
| Author of record | Kherim Willems |
| Status | Draft for review |
| Structure | ISO/IEC/IEEE 29148 (requirements), IEEE 1016 (design), IEEE 1012 (verification and validation) |

---


## How to read this specification

This file is the entry point. The specification itself is the OKF bundle [`specification/`](specification/index.md),
one file per section; this file holds the title block, the reading rule and the maps.

- **Read the current files by default.** They state what holds today, in the present tense. Every
  requirement, design clause and numerical method is in them, and `SPECIFICATION.md` is normative
  through them.
- **Read [`specification/history/`](specification/history/index.md) on demand.** It holds the Phase 0
  exit criteria and the author's dated rulings (§8.2.1 to §8.2.16), verbatim, with the reasons. Read
  it when the reason behind a rule is wanted. Its index says where each ruling holds now.
- **The rules of the development process** that no clause of its own carries are §8.4
  ([`04-development-process.md`](specification/08-implementation-plan/04-development-process.md)).
- **Print a clause by its identifier** with `uv run .claude/scripts/clause.py VER-62 §7.6 J8`: it prints
  the definition, then every NOTE and ruling that names it, each labelled with its file and lines.
- A reference to `SPECIFICATION.md §x` names the section of that number, wherever it lives. The map below
  gives its file.

### Section to file

Paths are under `specification/`.

| Section | File |
|---|---|
| §1 Introduction | `01-introduction.md` |
| §2 Product overview (S1–S4 scenarios, P1–P3 personas) | `02-product-overview.md` |
| §3 Requirements (IF, FR, QR, CON; N1–N7 exclusions) | `03-requirements.md` |
| §4 Physics specification (PHY) | `04-physics.md` |
| §5 Software design: introduction | `05-software-design/index.md` |
| §5.1 Architectural overview | `05-software-design/01-architectural-overview.md` |
| §5.2 Pipeline stages | `05-software-design/02-pipeline-stages.md` |
| §5.3, §5.3.1 Data design, the case file | `05-software-design/03-1-case-file.md` |
| §5.3.2 Artefacts and interchange formats | `05-software-design/03-2-artefacts.md` |
| §5.3.3 Provenance manifest | `05-software-design/03-3-provenance-manifest.md` |
| §5.3.4 Sweep specification and dataset | `05-software-design/03-4-sweeps.md` |
| §5.4 Component design | `05-software-design/04-component-design.md` |
| §5.5 Extension points | `05-software-design/05-extension-points.md` |
| §5.6 Architecture decisions (ADR) | `05-software-design/06-architecture-decisions.md` |
| §6 Numerical methods (NUM) | `06-numerics.md` |
| §7 Verification and validation: introduction | `07-verification/index.md` |
| §7.1 Strategy and ordering | `07-verification/01-strategy.md` |
| §7.2 Tier 1 (VER) | `07-verification/02-tier-1.md` |
| §7.3 Tier 2 (VER) | `07-verification/03-tier-2.md` |
| §7.4 Tier 3 (VAL) | `07-verification/04-tier-3.md` |
| §7.5 Tier 4 (VAL) | `07-verification/05-tier-4.md` |
| §7.6 Continuous integration | `07-verification/06-continuous-integration.md` |
| §8 Implementation plan: introduction | `08-implementation-plan/index.md` |
| §8.1 Phases and gates | `08-implementation-plan/01-phases-and-gates.md` |
| §8.2 Rulings by date (a stub; the rulings are the history) | `08-implementation-plan/02-rulings.md`, `history/index.md` |
| §8.2.k, the dated rulings and the Phase 0 exit criteria | `history/` |
| §8.3 Effort estimate | `08-implementation-plan/03-effort-estimate.md` |
| §8.4 Development process | `08-implementation-plan/04-development-process.md` |
| §9 Risk register (RSK) | `09-risks.md` |
| §10 Open items (OPN) | `10-open-items.md` |
| §11 Companion knowledge base | `11-companion-knowledge-base.md` |
| §12 References | `12-references.md` |
| Appendix A Requirements traceability matrix | `a-traceability-matrix.md` |
| Appendix B Reference COMSOL model settings | `b-comsol-settings.md` |

### Identifier to file

| Identifier | Defined in |
|---|---|
| `FR-nn`, `QR-nn`, `CON-nn`, `IF-nn` | `03-requirements.md` |
| `PHY-nn` | `04-physics.md` |
| `NUM-nn` | `06-numerics.md` |
| `VER-nn` | `07-verification/02-tier-1.md`, `07-verification/03-tier-2.md` |
| `VAL-nn` | `07-verification/04-tier-3.md`, `07-verification/05-tier-4.md` |
| `ADR-nn` | `05-software-design/06-architecture-decisions.md` |
| `RSK-nn` | `09-risks.md` |
| `OPN-nn` | `10-open-items.md` |
| `S1`–`S4`, `P1`–`P3` | `02-product-overview.md` |
| `N1`–`N7` (exclusions) | `03-requirements.md` |
| A letter and a number (`A1`, `J8`, `R10`: a ruling) | `history/`, by its letter; `history/index.md` |
| A requirement's tracing to a test | `a-traceability-matrix.md` |
