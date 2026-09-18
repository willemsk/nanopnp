# Current work

Updated 18 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: WP7-WP12. Next: WP13; no WP13 implementation plan exists yet.
- WP13 scope: Tier 3 harness, export contract, archived goldens and attribution
  (VAL-01 to VAL-04, RSK-14, RSK-09). Read the phase plan's
  [WP13 section](phase-1-solver-core.md#wp13--tier-3-harness-and-the-comsol-comparison).
- Author decision needed: VAL-03 export scope, before WP13 starts. The harness
  depends on the author's exports and WP8 reference geometry. A self-generated
  golden tests machinery only, not agreement with COMSOL.
- Later: WP14 GUI and packaging probe; Windows verification still needs the
  author's machine or a Windows CI runner. See the phase plan's Open decisions.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| WP13 comparison design and acceptance | Phase plan: Design / The Tier-3 attribution ladder, WP13, Verification; specification section 7.4 and its cited requirements |
| Reference geometry and field inputs | Phase plan: WP8 and WP9; follow their evidence links only for the input under investigation |
| Running cases and sweeps | Phase plan: WP10 and WP11; `docs/sweeps/README.md` for the reference sweep |
| Stabilisation findings inherited by WP13 | Phase plan: final Inherited by WP13 paragraphs in WP12; `wp12-reference-stabilised-mode.md` Outcomes in Design sections 3 and 4 |
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