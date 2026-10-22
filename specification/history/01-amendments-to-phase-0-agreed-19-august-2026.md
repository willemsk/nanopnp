---
type: Ruling Record
title: "8.2.1 Amendments to Phase 0, agreed 19 August 2026"
description: "Records the amendments to Phase 0 agreed on 19 August 2026, with the consequence of each."
---

#### 8.2.1 Amendments to Phase 0, agreed 19 August 2026

| # | Amendment | Consequence |
|---|---|---|
| A1 | Criterion 1 stands in full, including VER-19 to VER-22. Those four benchmarks require an embedded body, so Phase 0 SHALL implement a rigid analyte body of revolution and the domain-form force integral of NUM-28 to the extent the benchmarks exercise them | Brings part of FR-21 and FR-22 forward from v1.0 into the spike, and verifies RSK-04 — a near-cancellation of two approximately 10 pN terms — against analytic results at the earliest point at which it can be verified at all. The case-file surface for analytes remains v1.0 work |
| A2 | Criterion 4, the PySide6 and `webgui` Windows bundle, is deferred out of Phase 0 and is recorded as deliberately unmet | RSK-13 (desktop packaging defeated by a binary dependency) stays open and undetected for longer than ADR-004 intends. The GUI track of §8.1 resumes at Phase 1 |
| A3 | The Phase 0 COMSOL comparison is deferred in full to Phase 1, together with the Tier 3 harness, the export contract and reference-set generation (VAL-03) | Phase 0 verifies against analytic solutions only. This tightens rather than weakens the gate, criterion 1 being the criterion that localises an error to a single term; §8.2 already excluded the comparison from the gate |
| A4 | **Added 20 September 2026.** Criterion 4 is discharged in Phase 1, and how: a gated `windows-latest` continuous-integration job SHALL build the bundle on every push from a probe application that imports PySide6, `QtWebEngineWidgets`, NGSolve, Netgen and `ngsolve.webgui` in one process, and SHALL launch the built bundle headlessly. The criterion is closed by the author's observation that the uploaded bundle double-clicks, recorded with the build that produced it | Turns RSK-13 from a risk detected once into one detected on every push, which is what amendment A2 cost. A probe that omitted Qt WebEngine would retire RSK-13 without exercising the payload most likely to defeat packaging, so the import set is named here rather than left to the builder. "Double-clickable" remains a human observation: a process exit code on a headless runner does not establish it, and the criterion says desktop |

Phase 0 is therefore met by criteria 1 to 3 as written, with criterion 4 explicitly outstanding
until amendment A4's build and observation have both happened.

NOTE — **Criterion 4 closed, 24 September 2026.** The author double-clicked the bundle uploaded as
`nanopnp-probe-windows` by the gated `bundle` job of CI run
[36045057612](https://github.com/willemsk/nanopnp/actions/runs/36045057612), built from commit
`52fd531` (reported version `0.5.0a11.dev4+g52fd531b4`, which is `0.2.0a11.dev4+g52fd531b4` under the renumbering of §8.2.4 D1), on a Windows desktop. The executable opened
a window drawing a basic mesh with its controls. The author called it "still a bit janky", which is
a usability remark on the probe and not a packaging failure: the criterion asks that the bundle
build and open, and it did. Amendment A4's build and observation have both happened, so criterion 4
is met and RSK-13 is retired as a risk. The `bundle` job keeps detecting it on every push.
