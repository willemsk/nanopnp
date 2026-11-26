# Code review 095: WP6.08, the guard numbers (VER-80; §8.2.59 BI1, BI2)

2026-11-26 · branch `claude/zealous-planck-aio2ty`, PR #221, head `17e3111` on base `f571e72` · scope: 12 commits,
26 files, +793 and −63, read from `git diff f571e72...17e3111`, against
[the plan](../plans/phase-6/wp6.08-the-guard-numbers.md), VER-80, VER-62, §7.6's NOTEs, §8.2.53 BC3 and BC4, §8.2.59
BI1 and BI2, PHY-23, NUM-02, NUM-11, NUM-14 and NUM-18's NOTE, `CLAUDE.md`, `.claude/rules/python.md` and
`.claude/rules/physics-numerics.md`. Read in place: `tests/conftest.py`'s `NumberStability`,
`validation/stability.py`'s `compare` and `environment`, `solve/state.py`'s `ladder`, `post/qoi.py`'s stabilisation
current, `physics/models.py`'s descriptor switches, `ci.yml`'s environment and the `tier12` action · reviewer:
`np-reviewer`, Opus 5.5 at high effort · status: completed.

Static review: no `gate.sh run`, no `--nightly`, no walk. Probes: `tests/tier1/test_number_stability_file.py` and
`tests/tier1/test_stability_golden.py` (15 passed), ruff on the guard file, the guard file's collection (six tests),
each guard walk's shift recomputed from `number_stability.json`, `decisions.py` and `index_records.py` after the
fixes. No code under `src/` changed. The six guard tests are in the test scope (§8.2.13 N1: a numerical regression
reference over physics paths), each named for what it holds; none is dropped.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `specification/07-verification/03-tier-2.md:34` | Axis 2, VER-80. The row says only that "a setting the NUM-18 ladder refuses runs as a single rung", which leaves `guard-log`'s path unstated: the ladder does not refuse the log branch, it drops it (`solve/state.py:ladder` builds `default_ladder` without `model_options["log_variables"]`), and the test runs it as a single rung. A kernel rebuild reading the clause could put `guard-log` on the ladder and solve the primitive model. Confirmed | Fixed: the row says the log branch runs as a single rung because the ladder's rungs would drop it, and that the two stabilisation modes run on the ladder |
| 2 | Low | `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md:39-50`, `:89` | Axis 1, the provenance rule ("keep the header's `verified` list equal to the tests the claims name"). The header gained six tests, the claims named four: the reference and SUPG tests stood in `verified` behind no claim, though the third claim states their shifts | Fixed: that claim carries the two tests' tags |
| 3 | Low | `docs/plans/phase-6/wp6.07-the-lean-carry.md:3`; `phase-6-library-foundations.md:97-104` | Axis 1, `np-implement/finish.md` *Keeping the record straight*. The PR marks WP6.07 delivered in the Phase 6 plan and `current.md` (tagged `v0.7.0-alpha.7`), but WP6.07's own status line still read "built and reviewed, awaiting its merge", so `docs/plans/index.md` and `decisions.py` kept it in flight; it had no delivered summary, and its phase entry was not the one-line `Live:` form of WP6.05's and WP6.06's | Fixed: status `delivered, 26 November 2026`, a **Delivered.** paragraph, the phase entry in the `Live:` form; `decisions.py` moves WP6.07's rows to the closed page |
| 4 | Low | `specification/07-verification/06-continuous-integration.md:42-46` | Axis 1. The edit to the per-push NOTE left a line of 119 characters among neighbours wrapped at about 100 | Fixed: rewrapped to the next sentence, no word changed |

The pass fixed four findings and left none.

## Checked and found true

- **The descriptor assertion is what makes a guard walk mean its setting.** `_check_model` reads `switches` and
  `stabilisation` from the stored state's descriptor, which `CoupledModel.provenance` writes from the model that
  solved (`physics/models.py:747-763`); the five switches it reads are the five the row names. A walk that solved the
  default model would fail it before its numbers.
- **The numbers cannot pass on a partial set.** `stability.compare` fails where the walk's quantity names differ from
  the golden's, so the stabilised walks fail if a species' stabilisation current goes missing, and the others if one
  appears. The stabilisation current is a single integral (`post/qoi.py:stabilisation_currents`), not a difference of
  two routes, so VER-62's bar on a held difference does not apply; at about 0.5 % of the current its round-off is far
  inside 10⁻⁸.
- **The shifts.** Recomputed from the stored values against `example-02-epnpns` on `546c34f4…`: dielectric 1.10e-3
  (current) and 2.73e-3 (EOF), log 6.54e-6 and 7.54e-6, reference 6.66e-3 and 1.66e-2, SUPG 6.93e-3 and 8.90e-3,
  constant density 3.65e-8 and 2.81e-8, no inertia 3.41e-12 and 4.75e-9, as the knowledge table rounds them. Every
  walk but `guard-no-inertia` would fail at 10⁻⁸ if its setting were ignored in the forms; `guard-no-inertia` would not,
  which the plan's *What could go wrong*, the knowledge claim and `current.md` state and the author approved.
- **The skip.** The autouse fixture skips before the walk outside `linux-x86_64/X86_V3`; `ci.yml` sets the SIMD cap
  for every job, so the Linux nightly leg is the reference environment and the macOS and Windows legs skip, naming the
  environment under `-rs` (BI2). The fold added six walks and moved no other line of `number_stability.json`.
- **The clauses.** VER-80's row, §7.3's opening list, §7.6's NOTE, Appendix A's paragraph, BC3's pointer and its
  `holds-now` entry, BI1 and BI2 and their entries agree with the plan and the test; VER-80 is the highest `VER-`
  identifier and `duplicates.py`'s skip of `*-handoff.md` matches `index_records.py`'s.

## Not assessed

- The six guard walks and VER-62's seven, which are `nightly`; item 2's run of the tree at `8cce00f` is the evidence.
- `just land` on this branch and its CI, which the session that started the review runs.
