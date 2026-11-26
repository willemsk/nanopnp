# Code review 097: WP6.09, the kernel's design (§8.4.4)

2026-11-26 · branch `ccr-d29ea716-fd3bw4`, PR #224, head `8e0151b` on base `45b9798` · scope: 11 commits, 17 files,
+542 and −67, read from `git diff 45b9798...8e0151b`, against [the plan](../plans/phase-6/wp6.09-the-kernels-design.md),
FR-40, FR-20, QR-13, QR-14, PHY-08, PHY-23, NUM-07, NUM-12, NUM-14, NUM-24 to NUM-26, CON-01, CON-04, VER-13, VER-17,
§5.4.1, §8.2.53 BC1 to BC5, §8.2.60 BJ1 to BJ3, MOD-10, REV-67, REV-298 and `CLAUDE.md` · reviewer: `np-reviewer`,
Opus 5.5 at high effort · status: completed.

Static review of Markdown alone: the package changes nothing under `src/` or `tests/`. Probes: the prototype read with
`git show 1b5f5e3:<path>` (`physics/kernel.py`, `physics/models.py`, `prototype/three_d.py`), never checked out;
`git diff --stat` of the prototype against its fork point and of `0867e2d..1b5f5e3`; today's
`physics/terms.py`, `physics/models.py` (declarations, `__post_init__`), `pipeline/checks.py:_check_physics_switches`,
`physics/stabilisation.py:advective_velocity`, `post/qoi.py`, `numerics/measures.py`, `mesh/adapter.py`; function
lengths by the syntax tree; `uv run just docs` after the fixes, which passed. Line numbers are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `docs/design/kernel.md:22-23`; `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` §8.7 | Axis 3. The page says the engine sets an integral's order "from the integrand", and §8.7, marked `[verified]` on the prototype, that "NGSolve sets an integral's order from its integrand, so the sum is what keeps each slot's rule". The verified fact (`02-axisymmetric-weak-forms.md`, NUM-07's NOTE on the `r` weight) is that NGSolve estimates the order from the trial and test functions, not from coefficients, which is why a split can move a rule; and the prototype never measured a split slot, so the `[verified]` mark covers a claim its source does not hold. Confirmed | Fixed: both say the order comes from the trial and test functions; §8.7 says the prototype did not measure a split |
| 2 | Medium | `docs/design/kernel.md:106-107, 112` | Axis 2. The switch table gives `variable_density` and `inertia` `requires: flow`, and the text says `requires` and `excludes` "replace the two refusals in `CoupledModel.__post_init__`". Both cannot hold: `epnp-ns` declares both values of every switch, `_check_physics_switches` refuses only PHY-23 without the flow, and a case with `physics.flow: false` and those two at their default `true` runs today; read as refusals, the two extra `requires` would refuse it. Their terms already need `flow` through their display switches (`terms.py`). The prototype wrote the same records and never read them. Confirmed | Fixed: the two cells are empty, and the page says why and that the prototype's records carry them unread |
| 3 | Medium | `docs/design/kernel.md:141`; `docs/project/review-items.md`, REV-300 | Axis 2. "No clause says whether the wind should read the decrement". NUM-12's NOTE writes the advective velocity the implementation assembles as `b_i = z_i μ_i ∇φ̃ + D_i β_i − Pe u`, without the decrement; what no clause says is whether that holds under PHY-23. The recommendation pointed at NUM-14's NOTE, not the clause that writes `b_i`. Confirmed | Fixed: the page and REV-300 cite NUM-12's NOTE, and the recommendation says so in it; REV-300 stays the round's |
| 4 | Medium | `docs/design/kernel.md`, *One expression and its three readers*; the packages table | Axis 3, a gate that stops seeing a fault. NUM-24's indicator current reads the flux through `species_flux`, the function today's weak form integrates (PHY-23's NOTE, FR-23); the prototype composed the flux from the drifts and left the indicator there, so its flux is written twice, and that is why the control was refused at NUM-26's route check. The page lists three readers, omits this one, and calls the route check "a guard of its own" against a dropped term; with one expression, as D4 asks, a dropped term leaves both routes and the route check no longer sees it. Doubt | Fixed: a paragraph names the fourth reader and what then guards a dropped term (the stored walks and package 1's Tier 1 check); the control's paragraph says "today"; package 1's scope adds the indicator reading the drifts in force, at the same price |
| 5 | Low | `docs/design/kernel.md:207-211` | Axis 2, §5.4.1. The page lists the table's names without `grad`, then says "These are the table's names" while a term writes `ngs.grad`. `grad` is in §5.4.1's table, so the seam the page proposes leaves one of the table's names in the terms. Confirmed | Fixed: `grad` is listed, and the page says it is the one name the terms keep as backend algebra |
| 6 | Low | `docs/design/kernel.md:220-221` | Axis 2, the plan's Outcomes. "Each run used the prototype's head", while mark (a) ran at `0867e2d`. The head `1b5f5e3` adds `prototype/three_d.py` alone (`git diff --stat 0867e2d 1b5f5e3`), so the result stands, but the sentence was wrong. Confirmed | Fixed: marks (b) to (e) on the head, mark (a) at `0867e2d`, and why that is the same code |
| 7 | Low | `docs/design/kernel.md:270, 282`; knowledge §8.7; the plan's item 4 Outcome | Axis 2. The refusal of a 3D mesh is cited to CON-04, which is the azimuthal variance that accompanies a reduced geometry; the 2D restriction is CON-01. Option A's "(CON-04 stands)" said nothing true. Confirmed | Fixed: CON-01 cited, with the message's CON-04 noted; option A says the adapters' refusal stands |
| 8 | Low | `src/nanopnp/mesh/adapter.py:386, 471`; `src/nanopnp/mesh/quality.py:200` | Axis 1, prose in code (§8.4.2). The three refusals of a 3D or mirrored mesh cite CON-04 for the half-plane; CON-01 is the clause. Predates the package. Confirmed | Left to the author: the plan changes no code (D8). *Recommendation:* a `REV` row, fixed by the next package or chore that edits `mesh/` |
| 9 | Low | `docs/plans/phase-6/phase-6-library-foundations.md:3` | Axis 2, the records. The Status lists WP6.09 among the delivered and still says "WP6.09 is planned". Confirmed | Fixed: the clause dropped; `index_records.py` leaves the truncated index line unchanged |

The pass fixed eight findings and left one.

## Checked and found true

- **The page's numbers are the Outcomes'.** 2.1 × 10⁻¹⁶ and 1.2 × 10⁻¹⁶ at `0867e2d`; 8.7 × 10⁻¹⁴ on example 01 and
  the twelve other drifts with their modes; 43 passed in 426 s; the gate's 474 s on `c0171d4`; the control's
  6.2718 and 6.3127 × 10⁻¹¹ A against 6.2876 × 10⁻¹¹ A, which give 6.5 × 10⁻³, 2.5 × 10⁻³ and 4.0 × 10⁻³; the 3D
  trial's counts and errors, and the eight `OCCGeometry(dim=2)` and other 2D sites, as `three_d.py` prints them.
- **The prototype's shape is the page's.** 1,405 lines in five files; a context of twenty fields; 11 functions of
  `kernel.py` import NGSolve; the slots, their domains, rules and closings as the table has them, 4 + 3·2 + 11 and a
  source each; the flux slot closes `−(Σ)·∇v_i`, a force slot `−f·v`, and the ionic force is `−S ρ ∇φ` (PHY-08);
  the decrement's drift is `in_drift=False`; the steric drop is read by `in_force` alone, so the indicator, which
  takes `species_flux`, keeps the steric flux the composed form lost.
- **Today's code is as the page states.** `advective_velocity` leaves out the decrement; `Measures.volume` builds
  rules for `SEGM`, `TRIG` and `QUAD` alone; `from_ngsolve` refuses a third coordinate and every quality gate reads
  through it; `physics/models.py` is 2,076 lines and `default_ladder` 293; `pnp` builds on the willems2020 set unless
  told classical, so "its corrections as the case sets them" holds.
- **The prices add up.** 12 sessions, 9 to 16 agent hours, 19 touches across the four packages, against §8.3's 20,
  12 to 24, 32; four packages is BC1's count.
- **The records.** `holds-now.yaml` sets BJ1 to BJ3 `spent` and BC2's `open:` names the round alone, with AZ1 and BC5
  following; the decisions pages move the plan's rows to closed; REV-300's row and section match in title and
  anchor; the knowledge section has its footnote, index line and log entry; `CHANGELOG.md` has
  `## [0.7.0-alpha.9]`; `mkdocs.yml` lists the page under the workbench's.
- **No test is added or removed, and nothing under `src/` or `tests/` changes**, so no test lies outside the scope.

## Not assessed

- The prototype's runs themselves, which were not repeated (no benchmark, walk or gate run here).
- `just land` and the pull request's CI, which the session that started the review runs.
