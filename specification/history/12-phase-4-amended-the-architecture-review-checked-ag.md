---
type: Ruling Record
title: "8.2.12 Phase 4 amended: the architecture review checked, agreed 18 October 2026"
description: "Records the rulings on an external architecture review's eighteen proposed packages, agreed 18 October 2026, each claim checked against the code."
---

#### 8.2.12 Phase 4 amended: the architecture review checked, agreed 18 October 2026

Rulings by the author, taken through `/phase-plan amend 4` after WP48 was delivered. The input is an
externally generated architecture review proposing eighteen work packages (A1 to A18) for a later
phase. Each claim was checked against the code at `645289e`. Eleven describe what the code already
does or what a ruling already placed: A2 (each atom's kernel touches a patch of 6 `w_i` and point
location is bucketed, `charge/kernel.py`, `charge/deposit.py`), A3 (exact cell–annulus overlap weights,
the closed-form azimuthal kernel of §5.3.1 step 5 and the conservation gate), A9 (direct solves, NUM-21;
the solver registry of VER-66 takes a Krylov solver as one class), A10 (the NUM-02 log branch and
the increment gates that cut the damping), A11 (the distance field is a heat-method solve and a
smoothing pass with no `min`; corrections are closed forms built as symbolic coefficients), A12
(MOD-08, MOD-09; §8.2.8 H4, H5), A13 (`post/indicator.py` is NUM-24's ψ, not an error indicator;
adaptivity is FR-29, NUM-32, post-1.0), A14 (NUM-25's variational reaction flux), A15 (the spawned
pool with pinned threads and the warm-start forest, `sweep/`), A16's atomicity (staging and rename in
`io/store.py`) and A18 (`requires-python` is already `>=3.11,<3.15`). Four are open and unmeasured:
A1 (the aligned ensemble holds every frame, float32, in memory; the density deposit already streams
by frame), A8 (each continuation rung rebuilds its symbolic forms on a reused space), A16's
in-memory hand-off (each stage reads its inputs back through the store) and A17 (the case schema is
Pydantic v2 with `extra="forbid"`, and no JSON Schema is exported). A4 to A7 propose a browser shell
in place of PySide6. Package numbers from M4 on supersede L1's.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| M1 | **The review's already-met claims are declined with their evidence**: A2, A3, A9 to A15, A16's atomicity and A18. A12 stays under MOD-08 and MOD-09, A13 under FR-29 and NUM-32, A9 under NUM-21 | No package; one register row records the verdicts (REV-115) | None |
| M2 | **One measure-first package, WP49, the cost study.** It measures A1, A8 and A16 on the quick-start pore and the prepared 2WCD on a 4-core container, against thresholds registered in the Phase 4 plan before any measurement, and fixes in the same package only a cost over its threshold. It exports the case schema as JSON Schema, generated from the case document's model, its leaves equal to `case_fields`' in both directions (proposed VER-76). A fix changes no number: VER-62 holds at 10⁻⁸ on a recorded mesh, and a miss is reverted (G10). A fix too large for the package is carried as a `REV-nn` row and ruled into a fix package | Every claimed cost becomes a measured one, and nothing is optimised on a guess. REV-112 and REV-113 are WP49's | Appendix A gains VER-76, in WP49 |
| M3 | **Phase 5 builds a browser shell in place of the Qt desktop shell.** A local server in `gui/` over the existing view-models, and a browser front end; PySide6, the Qt widgets, the PyInstaller bundle and the packaging probe leave in Phase 5, once the browser shell meets the shell's gating clauses as Phase 5's design document restates them. The view-models stay pure Python and hold no physics (VER-60). CON-09's renderer clause stands: `webgui.js` is loaded unmodified as a separate file, or the front end draws without it. Phase 4 does no GUI work; the Qt shell keeps QR-11 at v0.5 | ADR-004's rejection of a local web application is withdrawn. F5's design document designs the browser shell and chooses its server library. The shell's gating clauses keep gating the Qt shell until Phase 5 replaces them, so v0.5 ships a gated surface. RSK-13 is re-scoped by the design document. REV-114 is deferred to Phase 5 | ADR-004 and CON-09 (a NOTE each) and §8.1's Phase 5 rows, in this commit; VER-43, VER-44, VER-55, VER-60, ADR-004's packaging NOTE, CON-09's PySide6 clause and RSK-13, in Phase 5's design-document commit |
| M4 | **WP49 comes before the protocol.** The protocol becomes WP50 and the fix packages are numbered from WP51. Tag `v0.5.0-alpha.15` | Testers judge the tree v0.5 ships (G2). The sessions start about a week later | The Phase 4 plan, in this commit |
| M5 | **The phase estimate stands** at 4–6 weeks | The study is absorbed, as WP43 was (J12) | None |
