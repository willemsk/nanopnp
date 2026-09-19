# Current work

Updated 18 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: WP7–WP13. Next: **WP14, the GUI increment and packaging probe** — not
  planned yet. See the phase plan's `### WP14` section and its Open decisions.
- WP13 delivered the Tier-3 harness: the probe grid, the export contract, the golden
  archive and its refusals, the comparison norms, the four-rung attribution ladder and
  the nightly job (VAL-01 … VAL-04, RSK-14 retired, RSK-09 bounded). Details:
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).
- **Tier 3 is recorded, not gated, and stays that way.** §7.4's targets are conditional
  on both of its preconditions; WP12 delivered the stabilised mode, and
  convergence-matching the meshes is not scheduled. WP13 *measures* whether it holds,
  through `Δ_ref`, and reports a comparison as *reference-limited* when our residual
  falls below the reference's own discretisation error.

## What WP13 leaves for somebody else

- **The COMSOL exports do not exist yet.** They are the author's, against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md):
  five frozen cases × six fields × five patches, plus one uniform refinement of the
  centre case for VAL-04. Until they land, the harness runs against a self-golden and
  every report it produces carries `golden_source: self` — which tests the machinery and
  says nothing about the reference. `tests/tier3/test_comsol_comparison.py` skips the
  archive comparison, visibly, rather than failing.
- **Two declarations only the author can make**, and the loader refuses a golden without
  them: which boundary `tds.ntflux_i` was evaluated on, and which electrode the exported
  current references. Both are NOT IN REPORT (`.knowledge/09` §F).
- **`$NANOPNP_REFERENCE_DATA` on the nightly runner** is still open. If it cannot be
  mounted there, Tier 3 is a local and on-demand tier and the job records a visible skip;
  nothing else changes.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| What the Tier-3 harness is and how to drive it | `wp13-tier3-comsol-comparison.md` Delivered and Outcomes; `docs/validation/comsol-export-contract.md`; `nanopnp validate --help` |
| Why the ladder has four rungs, and what each delta may be called | `src/nanopnp/validation/attribution.py` module docstring; `.knowledge/08-validation-benchmarks.md`, "Measured: the attribution ladder on the VER-11 benchmark pore" |
| Why VAL-01 reports two norms | Specification §7.4's comparison-surface NOTE; `.knowledge/08-validation-benchmarks.md`, "The *r*-weighted norm cannot see the axis" |
| What Tier 3 accepts and what it archives | Specification §7.4 including its three NOTEs, and the §7.1 NOTE on `$NANOPNP_REFERENCE_DATA` |
| What must be matched for like-for-like | `.knowledge/09-comsol-reference-settings.md` §C.2, §C.10, §E, §F |
| Sweeps whose axis a warm start cannot cross | `sweep/plan.py`'s `WARM_START_BARRIERS`; `.knowledge/06-numerics-fem.md` §8.4.1 |
| Stabilisation findings inherited from WP12 | Phase plan: the Inherited by WP13 paragraphs in WP12; `wp12-reference-stabilised-mode.md` Outcomes in Design sections 3 and 4 |
| Reference geometry, field inputs, runs and sweeps | Phase plan: WP8, WP9, WP10, WP11; `docs/sweeps/README.md` |
| Reference settings and equations | `.knowledge/00-index.md`, then relevant sections of 01, 06, 08 and 09; specification remains normative |

Two claims in the WP13 plan's decision table are corrected by its own Outcomes and must
not be read as current: the telescoping identity does **not** catch a rung compared
against a stale golden (the hash and point-count gates do), and the export is one table
per field **per patch**, not per field. Read the Outcomes before designing against either.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Link the active WP plan once it exists. Keep measurements and derivations in their
owning records, and preserve existing historical sections there. Load those
sections only when a decision, implementation or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
