# Current work

Updated 18 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: WP7–WP12. Current: **WP13, planned and not started** —
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).
- WP13 scope: the Tier-3 harness, the export contract, the probe grid, the archived
  goldens and the attribution ladder (VAL-01 … VAL-04, RSK-14, RSK-09). Tier 3 stays
  recorded, not gated; VAL-01 and VAL-02 do not become gates in this package.
- Closed by the author, 18 September 2026: **VAL-03 export scope** — five frozen cases
  (0.05 M and 3 M × ±200 mV, plus 0.5 M / +50 mV), the §7.5.1 analyte case excluded,
  VAL-04 on the published mesh plus one uniform refinement at the centre case.
  `SPECIFICATION.md` §7.4 carries the ruling.
- Amended with that plan: the phase plan's attribution ladder is **four rungs**, not
  three, on WP12's measured 0.98 convergence rate for `reference` on a Taylor–Hood
  pair. Do not design against the three-rung row.
- Later: WP14 GUI and packaging probe; Windows verification still needs the author's
  machine or a Windows CI runner. See the phase plan's Open decisions.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| WP13 decisions, work items and verification | `wp13-tier3-comsol-comparison.md` Execution brief; its §Design 1–3 for the ladder algebra, the norms and the golden contract |
| What Tier 3 accepts and what it archives | Specification §7.4 including its two NOTEs, and the §7.1 NOTE on `$NANOPNP_REFERENCE_DATA` |
| What must be matched for like-for-like | `.knowledge/09-comsol-reference-settings.md` §C.2, §C.10, §E, §F |
| Stabilisation findings inherited by WP13 | Phase plan: the final Inherited by WP13 paragraphs in WP12; `wp12-reference-stabilised-mode.md` Outcomes in Design sections 3 and 4 |
| Reference geometry and field inputs | Phase plan: WP8 and WP9; follow their evidence links only for the input under investigation |
| Running cases and sweeps | Phase plan: WP10 and WP11; `docs/sweeps/README.md` for the reference sweep, which the WP13 ladder reuses |
| Reference settings and equations | `.knowledge/00-index.md`, then relevant sections of 01, 06 and 09; specification remains normative |

The WP12 inherited findings supersede its original prediction that the flow terms
are asymptotically inert on Taylor-Hood. Do not use that historical decision row as
the current conclusion. Read the linked Outcomes before designing attribution.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Link the active WP plan once it exists. Keep measurements and derivations in their
owning records, and preserve existing historical sections there. Load those
sections only when a decision, implementation or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
