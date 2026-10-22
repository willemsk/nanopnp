---
type: Ruling Record
title: "8.2.3 Phase 1 exit, agreed 24 September 2026"
description: "Records the agreed Phase 1 exit gate of §8.1 and the end-of-phase report that measures the phase against it, dated 24 September 2026."
---

#### 8.2.3 Phase 1 exit, agreed 24 September 2026

The Phase 1 gate of §8.1 is "Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed".
The end-of-phase report (`docs/plans/phase-1-solver-core.md`) measures the phase against it.

| # | Amendment | Consequence |
|---|---|---|
| C1 | The gate's last clause is met by Tier 3 being **enabled and its attribution machinery verified**: the four-rung ladder against a self-golden, with `golden_source: self` on every report. The attribution of differences **against COMSOL** is recorded as outstanding until the author's reference exports exist (VAL-03, `docs/validation/comsol-export-contract.md`). When they land, it is reported as an addendum to the Phase 1 report, and it gates nothing retroactively. v0.2.0 is released on this basis | Phase 1 closes without the one comparison that needs data the project does not yet hold. The consequence is the same as A2's: a risk stays open longer than planned, here RSK-09 (a Tier-3 discrepancy originating in the reference) and the attribution of any residual. Nothing in Phase 2 touches a weak form, so the addendum can land at any point without re-opening a Phase 2 result. **Superseded 30 September 2026** (§8.2.4 D6): the exports are no longer required, so no addendum is owed, and the comparison against the published results gates v1.0 instead |
| C2 | The §8.3 reference sweep (3,675 points on 12 cores) is planned and checked in, but not run. QR-06's scaling is measured on 4 cores (VER-39, recorded and never gated) | QR-06 remains a SHOULD, measured only at the scale the development machine allows. The day-scale run is the author's to make, on HPC hardware |

Phase 0 criterion 4 is not changed by this section. It was closed by the author's double-click,
recorded in the NOTE to §8.2.1 on the same day, which met the last condition of §8.2.2 B1.

