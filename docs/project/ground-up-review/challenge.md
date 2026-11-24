# Ground-up review: the challenge

The reports of the two challengers and of the physics reviewer on the draft, kept unedited, and the answer to each
objection. An appendix of [the ground-up review](../ground-up-review.md).

## How the challenge was run

The draft was the report as item 12 of `wp6.04` committed it, at `d5ebeb0`. Three agents read it on 24 November
2026, each with [the walk](walk.md) and [the evidence](evidence.md), and each could check any fact in the
repository. None edited a file.

- **The first challenger**, a `general-purpose` agent on Sonnet 5.5 at high effort, was told to argue that each
  change, drop and add (GU-01 to GU-19) costs more than it gains.
- **The second challenger**, the same kind of agent, was told to argue that each keep is habit: GU-20 to GU-25, then
  the weakest keep rows of the walk.
- **The physics reviewer**, the project's `physics-reviewer` agent on Opus 5.5, read each proposal on a numerical
  method: GU-01, GU-08, GU-14, GU-15 and GU-22, and the design's statements of the method.

Each was told to be honest where a row survived, and to name its evidence. The three reports follow as they came
back; only the indentation of the hand-back is removed. A GU number in them is the draft's, and the report keeps
those numbers. Where a report cites a figure of the draft that the answers changed, the draft's figure stands in
the report below and the new one in [the report](../ground-up-review.md).

## The answers

The main session checked each objection's evidence at its source before it answered. *Changed* means that the row
of the report, and of the walk where it has one, was changed. *Shown* means that the objection is not met and
stands on its row for the author.

### To the first challenger: each change costs more than it gains

| GU | Objection, in short | Answer |
|---|---|---|
| GU-01 | The workbench reads the model through about eight names, and the weak forms already sit in sibling modules, so the gain is overstated | Changed. Checked, and they are nine: `gui/` imports `SWITCHES`, `Term`, `case_model`, `declaration`, `role_conditions`, `CONDITIONS`, `Symbol`, `symbols_in` and `written`; `CoupledModel` is lines 589 to 1346. The kernel stays in Phase 8 as AZ1 rules. Phase 6 states the target, fixes those names and stores numbers for the switches off their default |
| GU-01 | The cost is borrowed from the shell rate, is not netted against Phase 6's planned steps, and Phase 8 has no estimate | Changed with the row above: the cost for now is text and half a small package |
| GU-03, GU-04 | Two switches already remove two of the three pauses; AZ20 and AZ21 are not cited; "three touches" is unmeasured | Changed. The switches are tried first for two packages at no cost; a package follows only if the usage reports show that it pays; the target is set from that usage; each plan still proposes both models (AZ20, AZ21) |
| GU-09 | This is BA3 again a day later; the three designs are not independent; the author's reason is inferred | Changed in part. The card and the guard's section now say that the designs share one pack and one interview, and that the ruling records no reason. The proposal stands, and the card says that it is a keep if the author's ruling stands |
| GU-09 | A gap found early may be unreadable; the frozen cases could run with no package | Changed. The comparison is the frozen case of example 05 and its sweep, run at Phase 6's close and reported there, with no package. The card names the stabilisation and the missing error bar as its risk. Example 05 holds one case file, not five |
| GU-15 | "Checked" is weaker than stated; Newton holds no factor of the converged state | Changed. The card says that the transposed solve was checked on a scalar matrix alone, and that the adjoint costs a new assembly and factorisation |
| GU-14 | A third measure means forms that are generic in dimension; far more than one test | Changed, with the physics reviewer's finding: the test is a benchmark on a coarse 3D mesh, and its cost is left to Phase 8's round |
| GU-08 | The three-mesh sweep runs today; the new part is a wrapper; the finer mesh costs twenty times the run | Changed. The card names `numerics.mesh.size_scale`, is one small package, and does the estimate first where the answer is exact; the protein pore is Phase 12's study |
| GU-06 | §7.3 is published; `Term` already names its clause, so the ledger needs no kernel; tagging and recording errors are unpriced | Changed. The card states what §7.3 holds, keys the page on `Term.clause`, depends on nothing, and leaves the recording of errors to its plan's price |
| GU-13 | "Most pushes in a minute" is unmeasured: `gui` and its feeders changed in 13 to 18 of 20 packages | Changed. The gain reads "not measured" |
| GU-05 | A package can register by import today; entry points would fix nine names before the kernel | Changed. The proposal moves to Phase 8, where REV-67 already waits |
| GU-10 | The gain is thin; Zarr and Panel are no dependencies; each push's CI runs 3.14 alone | Changed. The floor moves when a dependency forces it |
| GU-11 | A supplied profile exists; the 50 sessions are BA1's guess; BA1 was ruled against the recommendation with no new reason here | Changed in part and shown. The card states the supplied profile and that the guess is unmeasured; the objection that the three designs are the one new reason stands on the card |
| GU-12 | Deleting four spent sections needs no change of IF-09 or FR-31 | Changed in part and shown. The deletion moves to GU-07, now; the objection to loosening IF-09 and FR-31 stands on the card |
| GU-17, GU-18 | No second pore with data is named; migrations are upkeep after version 1; AZ5 ruled that old runs are refused | Shown on both rows; GU-17's cost reads "not known" and GU-18's "then upkeep" |
| The load | Phase 6 can carry about three of the seven | Changed. The proposals for now are about three packages |

### To the second challenger: each keep is habit

| Row | Objection, in short | Answer |
|---|---|---|
| GU-22, GU-23 | "Keep until a trial" names no place; the trial is cheap; C is unsure of primitive unknowns; BA13's row says five questions | Changed. The trial's place is Phase 6's speed-up package and it compares the log branch too; GU-23 says that C is unsure; BA13's row says seven. The trial is not run here: `wp6.04` tries no design (BA13), and `continuation: none` removes the ladder and does not reorder it |
| GU-21, ADR-004 | Measuring the kit after the first rebuilt suite is the order of a sunk cost; the spike tested neither a design's ceiling nor QR-16 | Changed. Phase 7's design study builds the hardest view in the kit and audits it before the rebuild; it is the seventh trial |
| §7.6, §8.4.4 (2) | "Nothing measured argues against" Linux alone is wrong: a red Windows leg cost a package | Changed in part and shown. The walk's reason is corrected: the keep rests on AZ8, ruled on 22 November with that cost known. The objection stands on GU-25 |
| GU-25, the records | "Read on demand" counts reading alone; writing is measured | Shown on GU-25 with the measured figures. The keep rests on the author's "same process form" |
| GU-25, §2.7 v0.13 | The row's reason argues a change: each design validates before its workbench | Shown on GU-25 and on GU-09, which now says that it is the least of what each design does |
| GU-24 | "Built" is the sunk-cost reason, and the sizes were not stated | Shown, with the sizes: `io/variables.py` 678 lines and `sweep/forecast.py` 120, `physics/stabilisation.py` 716 |
| GU-12, GU-13 | The delay is unexplained | Changed in part. The four sections go now. GU-13 gives its reason: the gate can skip the browser tests only once CI runs them, and Phase 7 rebuilds them. The first challenger argues the other way on the same row |
| GU-20 | The direct solve is prompted, yet counted; the evidence for no stabilisation is two small cases | Changed. GU-20 no longer names the direct solve, and the design argues from NUM-11 and NUM-12's check on each run in place of the two cases' Péclet number |
| §8.4.4 (15), FR-30, §5.3.1, FR-33, IF-06 | Reasons that argue a change but carry a keep | Shown, as a list under group 11 |
| The headline | "207 of 259 kept" overstates agreement | Changed. In brief gives the split: a designer for and none against, no designer, at least one against |
| The pattern | The keeps lean towards the program as it is | Shown: In brief and *What stays open* say so |

### To the physics reviewer

| GU | Finding, in short | Answer |
|---|---|---|
| GU-01 | A flux integrated term by term moves its quadrature, so the guard of 10⁻⁸ cannot hold | Changed. The design's kernel integrates each flux once |
| GU-01 | The terms are not independent: shared coefficients, PHY-08's pair, PHY-05's sum | Changed. A correction is a shared coefficient and a rule binds terms; the card names this as Phase 8's design work |
| GU-01 | VER-62 guards the default path alone; VER-22 and VER-42 are missing from the list | Changed. Numbers are stored for the switches off their default before any redraw, and the list names VER-12 to VER-22, VER-31, VER-42 and VER-77 |
| GU-01 | A flipped damping decision would move the numbers | Noted here; the stored numbers would show it |
| GU-01, §7.3 | A term is no operator on its own; a manufactured field never reaches the clamps | Changed. A manufactured solution for each term over a verified base operator, at Phase 8, and the card states its limit |
| GU-08 | Coarser meshes fall where the gates refuse the run | Changed. The ladder goes finer, at seven to twenty times the run |
| GU-08 | Netgen's meshes are not nested; the wall layer must scale | Changed. The ratio comes from the element counts. `numerics.mesh.size_scale` multiplies the wall layer's size too (§5.3.1); the growth ratio is the package's to check |
| GU-08 | Three meshes cannot show the asymptotic range; the bar covers the mesh error alone | Changed. Four meshes or a safety factor; the bar is the mesh error on the given contour |
| GU-08 | Newton's stopping floor | Changed. The card names it |
| GU-08 | VER-12 and VER-13 check a potential | Changed. VER-16, VER-14, VER-17 and VER-18 argue the estimate |
| GU-08 | The VER-62 claim holds only if the reported value stays the case mesh's | Changed. The card says so |
| GU-15 | Newton keeps no factors | Changed, in the card and in the walk's rows add-3 and NUM-33 |
| GU-15 | NUM-33 governs an error estimator; it cannot move | Changed. NUM-33 is a keep, and the adjoint no longer replaces the ladder |
| GU-15 | The Jacobian is exact in the default mode alone; row scaling; scaled units | Changed for the first; the others are left to the package |
| GU-15 | The list ranks charge changes, not mutations | Changed |
| GU-15 | VER-13 is unfit | Changed. Grahame's relation (VER-12, VER-77), an identity between adjoint and tangent, and finite differences above Newton's floor |
| GU-14 | A 3D assembly never touches the axisymmetric terms | Changed. One benchmark on a coarse 3D mesh against its axisymmetric solve |
| GU-22 | Switching on at the target is the largest jump; the packing limit; the re-pin; the rungs are not removed | Changed. The third trial states all four |
| The design | The Péclet figure and the evidence for primitive unknowns come from two small cases; "exact Jacobian" holds in mode `none` | Changed for the first; GU-15's risk states the second |

## The first challenger's report

### The objections

| GU | Objection | Evidence | What would meet it |
|---|---|---|---|
| 01 | The gain is overstated. The shell touches about eight physics names (`declaration`, `Term`, `SWITCHES`, `case_model`, `role_conditions`, `CONDITIONS`, `symbols_in`, `written`), so Phase 7's Physics suite can be built on that narrow interface without the redraw. The weak forms already sit in sibling modules (`nernst_planck.py`, `flow.py`, `steric.py`, `pb.py`, `poisson.py`). `CoupledModel` is lines 589–1346, about 760 lines. The rest of the 2,076 is protocols, the registry and two other models. "One class in 2,076 lines" overstates the knot. | `gui/web/physics_tools.py:33-34`, `plane.py:28`, `screens.py:10`, `study_tools.py:51-52`; `physics/models.py` class lines; Phase 6 plan, provisional table | Freeze those names as the interface in the already-planned "switches as data" package. Phase 8 then redraws behind them, as AZ1 ruled. |
| 01 | The cost is borrowed and not netted. "Large package" is the shell rate (6 sessions), and Phase 8 has no estimate (BA1), so "moved from Phase 8" has no baseline. Phase 6 already plans "switches as data", "one registry shape" and "forces share the weak form's terms", so the card counts that work twice. A no-re-pin redraw (VER-62 at 10⁻⁸) and the equations package (which re-pins) edit the same file in series. A miss in one is confused with a miss in the other. The card also does not price the rewrite of FR-20, QR-14 ("only one class") and VER-56. | Evidence "measured rates": mechanism packages took 7–11 h. Plan: "Provisional" table. `specification/history/50-…` AZ1 ("redrawn once"; the author took the recommendation, 22 Nov). | A cost taken from the mechanism rate and netted against the two planned packages. A named reason why AZ1's reason ("the same lines redrawn once") no longer holds, beyond the three designs. |
| 03/04 | The author's own switches already remove two of the three pauses: `NANOPNP_AUTO_CHECKPOINT=1` and `NANOPNP_AUTO_SHIP=1`. What is left (chain the plan review, flip defaults) is a few file edits. The card prices it at 5 sessions and 8 touches, a cost as large as the saving per package. The card does not cite AZ20 and AZ21 (23 Nov), where the author asked that the plan propose both models and that they go to him. "Three touches a package" is unmeasured: brief, plan approval and merge already make three before any finding or ruling. | `04-development-process.md:150-154`; `history/50-…` AZ20, AZ21; §8.3 touch definition | Set the two switches for a package or two and read the usage reports. Set the target from that. Answer AZ21 explicitly. |
| 09 | This is BA3 again, one day later, against the author's choice. BA3's recommended option was the same: one recorded package, after the open terms, on the paper's tables. The only new evidence is three blind designs. They are not independent: same pack, same interview, two on Fable 5.2 and one on Opus 5.5. The author "accepted RSK-15 in full". The card says the author's reason was "exact digits". BA3's text gives no reason, and the interview says only "extensible over exact". | `history/51-…` BA3; `09-risks.md` RSK-15; `method.md:251` | State the author's reason from his own words, or say it is inferred. |
| 09 | A gap found early may be unreadable. VAL-16's text requires a stated tolerance, declared units, signs and G6, and the project's own discretisation error first (RSK-09). The published values were solved with stabilisation on; today's run uses none. Without GU-08 first, an early discrepancy cannot be attributed. The card does not list that dependency. | `07-verification/04-tier-3.md:60-76`; evidence "Two runs" (stabilisation `none`) | Run the five frozen cases that exist (`examples/05-clya-reference`, tens of minutes each). Put the numbers beside the paper in the end-of-phase report, with no package. |
| 15 | "The engine solves the transposed system with the same factors (checked)" is weaker than stated. The survey's own engine run reports `a.mat.T.Inverse(...)` failing ("InverseMatrix not available"). The 1e-14 agreement is on a scalar convection-diffusion matrix and a Stokes-type matrix, "not a coupled PNP-NS matrix". Newton holds the factor of its last iterate, not J(u*). UMFPACK repeats its symbolic step each iteration. | `technologies.md:99`, `:217`; evidence "Cited": REV-60 | A trial on a converged coupled system, with the transposed solve from the held factor, before NUM-33 is amended. |
| 14 | The cost is understated. The measures are two 2D symmetries, `("r","z")` or `("x","y")`. The forms carry a hoop term `u_r v_r / r²` and a two-component velocity. A "third, Cartesian 3D measure" therefore means dimension-generic forms. That collides with "forms written once" (QR-13) and is far more than "one test". | `numerics/measures.py` (`coordinate_names`); `physics/flow.py:56-67` | A sketch of one form under 3D, with its price. |
| 08 | The three-mesh sweep runs today: a mesh-scale key exists "so that a mesh-convergence study is a sweep" (RSK-09 mitigation, VAL-04 refinement pair). The new part is a Richardson wrapper. The card admits the order may not be clean on a corner-laden contour, which is where the estimate is wanted. The finer mesh costs 20 times the run: 2WCD at 394 s becomes about 2 hours a point. | `03-1-case-file.md:174`; `09-risks.md` RSK-09; NUM-33 NOTE | Do it as Phase 12's study, or first on VER-12/13/18 alone, where the true error is known. |
| 06 | "No page shows which term each case proves" is partly wrong. §7.3 is published and gives each benchmark its closed form and criterion. `Term` objects already carry their PHY or NUM clause, so ledger rows need no GU-01. The stated dependency is false and the ledger could go first. The card leaves out the cost of tagging about 60 Tier 2 files (12,025 lines). Tests assert thresholds and do not record errors, so measured error needs a harness. Every new term and test must be tagged afterwards. | `07-verification/03-tier-2.md`; `physics/terms.py` `Term.clause`; evidence "Size" | Key the ledger on today's `Term.clause`. Price the tagging. |
| 13 | The "most pushes in a minute" gain is not measured. `gui` changed in 15 of 20 packages, and its feeders `io` 18, `pipeline` 15, `api` 13. A path rule that protects the shell must include those, so most pushes still run the 468 s. | evidence "What a package touched" | Measure the share of pushes a safe rule would skip. |
| 05 | The registration functions are already plain module-level functions (`register_model`, `register_mesher`, `register_solver`, `register_form`, `register_output`, `register_steric_model`). A package can register by import today. Entry points add discovery only. They would freeze nine registry names before the kernel (GU-01) and Phase 8's round exist, and no second group has asked. | `src/` `register_*` defs; REV-67 (deferred to Phase 8) | Document register-by-import now. Add entry points when a user needs them. |
| 10 | The gain is thin. Zarr and Panel are not dependencies. Only SciPy (the lock already forks at 3.12, `uv.lock:967-968`) and the Pint pin (`pyproject.toml:41`) are affected. Per-push CI runs 3.14 only. 3.11 sits in the release, full and nightly legs. A cluster on 3.11 would need uv to download Python, against "any ordinary computer". Waiting costs nothing. | `ci.yml:298,326,356`; `pyproject.toml:9,35-41` | Do it at 3.11's end of life, or when a dependency forces it. |
| 11 | The supplied profile already exists (`inputs.profile`), so a cone or hourglass is a profile file today. The "about 50 sessions" being saved is BA1's own guess ("no measurement"). BA1 offered the composer alone and the others after version 1, and the author chose all three against the recommendation. The card names no new reason. | `io/case.py:99`; `history/51-…` BA1 | A measured price for the sketcher, or the author's reconsideration. |
| 12 | The "3,000 fewer words" comes from deleting four spent design sections. That needs no change to IF-09 or FR-31. Loosening a layout the author ruled on concept boards gains nothing extra. | walk "Organisation" row (kept for that reason) | Delete the spent sections and leave the requirements alone. |
| 17/18 | GU-17: "one small package" assumes a second pore's structure, ensemble and published ePNP-NS data. Only ClyA has them. GU-18: migration functions are upkeep for every schema change after version 1. The card prices only the first package. AZ5 and F4 ruled that old runs are refused. | `history/50-…` AZ5; FR-37 row | A named second dataset. A per-change upkeep figure. |

### Survives

- GU-02: the drop of QR-11 is one line, and VER-43, VER-44, VER-55 and VER-60 are traced under IF-09 (`a-traceability-matrix.md:23`). VER-78 keeps the shell loading.
- GU-07: the four text fixes. I found no cost, and CON-08 is the only one that needs a licence-note check.
- GU-16 and GU-19: deferred and costless now.
- GU-03's core idea, once the existing switches are tried first.
- GU-14's N1 wording and GU-12's text change are harmless. Only their gains and costs are in doubt.

### The load

Phase 6 today is about 66 sessions, 105 touches and 54–107 agent hours (review, ruling round, axis fix, ten packages). The seven proposals add 38 sessions, 62 touches and 30–60 hours, about 55–60 % more. The chain is serial, because the second lane may hold only a design study (§8.4.4 (10)). Cut first: GU-09 (to a table in the phase report), GU-08 (to Phase 12), GU-10 and GU-05 (later). Narrow GU-01 to freezing the shell's interface. Keep GU-02, GU-07 and a switch-first GU-03. GU-06 can go early without the kernel.

Phase 6 can carry about three of the seven.

## The second challenger's report

### Objections

| Row | Objection | Evidence | What would meet it |
|---|---|---|---|
| GU-22 (NUM-18), GU-23 (NUM-02) | "Keep until a trial" has no reason for the delay. The trial is a case-file edit on a case that runs in about 9.5 s. All three designers chose adaptive steps. The review prices the ladder itself: 85 to 92 % of each solve sits in the six correction rungs, and four of the six are the salt ramp. If the rungs cost about the same (my arithmetic), the ramp is up to roughly 60 % of a solve, a larger speed gain than any GU-01 to GU-19 states. NUM-02's "two of three" omits that C names primitive variables as its second-least-sure choice. | `numerics.continuation: none \| default_ladder` is in `io/case.py:609`. A `log_variables` switch exists (`physics/models.py:611`). Evidence.md has 9.46 s and 9.71 s runs, damping down to 0.08 and 110 iterations. Design C §6 item 2. BA13's row rejects "throwaway trials", and its reason says five questions were held back (the report says six). The trial is "owned by the round", with no phase named. | Run both timed cases with `continuation: none` and with the log flag, then at 0.005 M, 5 M and ±200 mV, before the round rules. Failing that, name the package and the phase. |
| GU-21, ADR-004, BA2, §2.6 NiceGUI | The review chooses to measure the kit after building the first suite on it, which is sunk-cost order. It writes that "a start-over would measure a whole suite before it chose". BA2's own best alternative is "a trial of the kit before the rebuild starts", and its reason ("the one cheap moment to settle the kit") argues for it. The spike never tested the criterion the author gave, a design ceiling. It never tested QR-16 either, and the survey found no WCAG audit of NiceGUI. | Spike report measures 1 to 6: lines, redraw, URL states, keyboard, install, licence. The workbench is 21,422 lines. `gui/` changed in 15 of 20 packages. Interface items are 47 % of the open log. REV-277: the Windows leg went red when `test_gui_screens.py` arrived, and three of its four faults were workbench-side. | Before Phase 7 starts, build the hardest view in the kit and run an accessibility audit on it. |
| §7.6, §8.4.4 (2) (the CI platforms) | The walk says "nothing measured argues against" a pull request testing on Linux alone. The evidence section itself cites a measurement against it. The Windows leg was red on `main` from 3 Nov to 22 Nov, and it took a whole package to fix. Windows costs 13 min 32 s once fixed. All three designers test on three systems per change. | REV-277 (archive), where "since 10 November" was corrected to run 621, 3 Nov. WP6.01: plan of 3,095 words, a package takes at least 4 sessions and about 8 touches. The author's AZ8 ruling is 22 Nov. The walk's own rule (D4) says a ruling's reason is evidence, not authority. | Price a red leg at one package against 13.5 min of CI per push. Or state that the keep rests on AZ8 alone. |
| GU-25 (records), §8.4.4 (12), (18), (20), §8.4.6 (1) and (5) | "Read on demand, so no session pays" counts only reading. Writing is the cost, and evidence.md measures it. Since v0.5.0, 317 of 473 commits touch `docs/plans/` against 176 touching `src/`, and 234 carry the `docs:` prefix. Docs, spec, reviews and knowledge gained 45,766 lines against `src/` 45,260. The review counts words read per session as a cost for the workbench document (GU-12, 3,000 words) but not for §5.3.1 (10,164 words) or §5.2 (8,742). The register's reason ("279 rows gave the evidence its count") is use to this review, not a start-over's choice. | Evidence.md sections "What a package touched" and "The records". 221 of 279 REV rows are low severity. Plans written after the cap, WP6.02 to 6.04, run 3,885 to 4,779 words against the 3,500 cap. The cap excludes Outcome annotations, so only a count that excludes them settles it, and it is one command. | Count words per plan net of annotations now. Put writing time per package beside reading time. |
| GU-25 / §2.7 v0.13 (validation last) | The row's reason argues a change. All three designers validate on ClyA before the workbench (A step 3 vs 4, B phase 2 vs 3, C step 5 vs 7). GU-09 proposes only a recorded, ungated comparison "on the paper's tables alone". The verdict "keep" rests on BA3 (23 Nov), whose reason the walk says bands already meet. | Design A §5, B §5, C §5; walk BA3 and §2.7 v0.13 rows. | Say that GU-09 is the minimum, and what a full pre-workbench validation would cost. |
| GU-24 (FR-39, NUM-14, two readers) | "Built, so nothing to gain by deleting" is the sunk-cost reason, and the report concedes it ("kept because they are built and no cost was measured"). The costs were countable in a minute and are not stated. Two readers: gemmi's output is hand-converted into an MDAnalysis universe, and MDAnalysis brings matplotlib and scipy. NUM-14 is kept for a Phase 12 like-for-like run that GU-09's bands-only comparison removes. | `variables.py` 678 lines, `forecast.py` 120, their tests 476. `physics/stabilisation.py` 716, its tests about 1,500. `structure/read.py:133-212`. technologies.md:389. | State these sizes in the card. |
| GU-12, GU-13 ("change later") | The delay is unexplained. The four spent workbench sections (about 3,000 words) are a deletion that costs nothing, yet wait for "Phase 7's round". The browser tests take 468 of the gate's 539 s on every push through Phase 6. The gate already skips on prose-only changes, so selection by path is the same mechanism. | `.claude/hooks/gate.sh:587-595`. Walk rows "Today's shell", "Tabs or areas", "Restated clauses", "Inherited rows". | Do both in Phase 6, or give a cost for doing so. |
| GU-20 (direct solve, no stabilisation) | The report's table lists the sparse direct solve as named by the pack ("proves nothing"), yet GU-20 counts it as chosen. Trial 1 says its cost at 10⁶ unknowns is unknown. If the factorisation (183 s of 761 s at 16,444 elements) scaled as N^1.5, an eightfold mesh would take about 4,100 s. That is my extrapolation, not a measurement. The "no stabilisation" evidence is two cases at 0.1 M, +50 mV and 392 elements, a quarter of the voltage envelope. | Report "What the guard showed"; walk REV-156; knowledge `04-stabilisation.md` §4.3.1 (Pe_K 4.7 and Na⁺ = −72.9 at 0.5 M, 313 elements). | Split the direct solve out of GU-20, and time one large mesh. |
| §8.4.4 (15), FR-30 (b), §5.3.1, FR-33, IF-06 | Reasons that argue a change but carry a keep. (15): "the author did not ask for it" is authority, while the author's complaint is touches, and A and B batch rulings with defaults. FR-30 (b): "moving it saves words, and that waits." §5.3.1: the prose repeats the schema, and all three generate it. FR-33: C drops it as design detail by the same logic that moves FR-31. IF-06: "no cost measured". | Walk rows for each. | Move them to "change later" with a phase, or give a cost. |
| Headline "207 of 259 kept" | It overstates agreement. Of 207 keeps, 91 (44 %) have a designer's yes and no dissent. 64 have no designer remark. 52 go against at least one designer. 18 are BA/BB ruling rows. 59 of the 64 read "none better found", and 11 read "no cost found". | Walk, counted. | Report the 91 separately. |

### Survives

- NGSolve, Netgen, P2 with Taylor–Hood: three of three unprompted, backed by the survey and CON-07.
- Coupled Newton with an exact Jacobian, and the two current routes: unprompted in all three.
- Gmsh optional: `mesh/` changed in only 3 of 20 packages, a measured cost.
- NUM-14: the knowledge base measures the band where it matters. The keep survives, though not on the reason given.
- FR-39 survives on its size of about 1 % of `src/`, not on "built".
- FR-04, FR-05 and FR-07: each rests on a stated downstream user.
- CON-09 licence: B itself says it is not worth reopening.
- REV-258's 315 ms is mostly program code (167 ms of repeated keying), so it is no case against NiceGUI.

### The pattern

The keeps lean towards the program as it is. Hard evidence (REV-277, REV-156, the ladder's cost) is cited, but where it argues change the verdict softens to "later" or "until a trial", and the trials are allowed by neither BA13 nor a date. Reasons often cite what exists ("built", "gave the evidence its count", "the author ruled"). Process and record rows are kept where no designer spoke. Today's costs of writing the records and of the workbench are measured in evidence.md but never set against the keeps.

## The physics reviewer's report

Two of the report's claims are wrong. First, Newton keeps no factorisation after it finishes, so the adjoint is not a back-substitution on factors it "already holds". Second, NUM-33 cannot move: it governs an error estimator, not sensitivities. Two tests are also unfit as written: GU-14's 3D assembly test, and VER-13 as the check for GU-15. Paths are under `/home/user/nanopnp/`. I edited nothing.

| GU | Finding | Severity | Source |
|---|---|---|---|
| 01 | **Confirmed:** today each species' whole flux is one integrand under one `dx`, so NGSolve sets one integration order for it. The coupled models run at the default order, which is one order short for the `r` weight. If each term holds "its weak form" as its own integral, the quadrature error moves, not just the round-off, and the 10⁻⁸ guard cannot hold. The composition has to add terms inside the flux or stress expression and integrate once, or else pin each term's rule to today's. | the card must say it | `src/nanopnp/physics/nernst_planck.py:192-220`; `numerics/measures.py:134`; NUM-07 NOTE |
| 01 | **Confirmed:** the terms do not add up independently. `D` multiplies the diffusion, steric and dielectric-decrement parts, and `ε` enters both Poisson and the Korteweg–Helmholtz force. PHY-08 requires the Korteweg–Helmholtz force and the decrement term together ("one without the other is thermodynamically inconsistent"), and PHY-05 forbids collapsing the steric sum. A correction is a coefficient shared by several terms, not a term with its own switch, so the registry needs coefficient providers and rules that bind terms together. | the card must say it | `nernst_planck.py:192-205`; PHY-05, PHY-08 |
| 01 | **Confirmed:** the guard is too narrow. Every example case runs `stabilisation: none`, so VER-62 protects only the default path at 10⁻⁸. The list leaves out VER-22 (body force, NUM-28 consistency terms) and VER-42 (the stabilisation, which is built from the same transport state). The PHY-23 terms, the NUM-14 mode and the NUM-02 log branch keep only Tier 2's looser checks. Add goldens for the non-default switches before the redraw. | the card must say it | `examples/*/*.case.yaml`; `models.py:1031-1063` |
| 01 | **Doubt:** a pure reordering of the sums should stay at round-off. But a flipped accept/reject decision in the damping would change the Newton path and move the numbers. | note | `numerics/newton.py:279` |
| 01 | §7.3's "one manufactured solution for each registered term": the hoop term, a coefficient correction or the steric term is not a well-posed problem on its own, so it must be composed with a verified base operator. Smooth manufactured fields never reach the clamps (PHY-13, the `d̄` clamp) or the gates. A source derived from the term's own text catches coding errors, not a wrong equation. Computed coefficients (the Varadhan distance `d`, the deposited charge) have to be replaced by analytic ones, which bypasses the code that produces them. | the card must say it | NUM-05; PHY-02; PHY-13 |
| 08 | Meshes coarser than the case's mesh fall where NUM-34 refuses the run, or where Newton converges and both routes still disagree by 40 %. They also fall where `Pe_h > 1` trips the positivity gate. | the card must say it | `knowledge/06-numerics-fem/07-…flux-trap.md` §7.1.1; VER-42 |
| 08 | Netgen meshes are not nested, and NUM-30 sets the wall layer's first size `h₁` by rule. Scaling `maxh` alone leaves the wall layer, where the error lives, unrefined. `h₁` and the growth ratio must scale too, with the refinement ratio taken from the element counts. | the card must say it | NUM-30 |
| 08 | The order the indicator current should converge at is unconfirmed. Re-entrant mouth corners and corners on the dielectric interface limit it. Three meshes give an order with no check that they are in the asymptotic range: use four meshes, or a safety factor. The error bar covers the mesh error on the given polygonal geometry only; the contour, the isolevel, the smearing and the model are outside it. | the card must say it | `knowledge/06-numerics-fem/10-unverified-to-measure.md:15` |
| 08 | **Confirmed:** Newton stops on the undamped update while the state took only the damped step, so it can stop up to (1−damping)·10⁻⁶ from the discrete solution. NUM-26 measures a 4×10⁻⁶ remainder set by Newton. The differences between meshes must stand well above this floor. | the card must say it | `newton.py:322-327`; NUM-26 |
| 08 | VER-12 and VER-13 check a potential, not a current, flow rate or transport number. VER-12 is 1D with no corners, VER-13 is linear, and both accept "to solver tolerance". Better fits: VER-16 (exact current), VER-14 (flow), VER-17 (corners, absolute current), VER-19 and VER-20 (curved boundaries, exact force). | the card must say it | §7.3 |
| 08 | The VER-62 claim holds only if the reported value stays the case mesh's value rather than the extrapolated one. | note | VER-62 |
| 15 | **Confirmed:** Newton keeps no factors. Each step builds `matrix.Inverse(...)` and drops it, and the SuperLU factorisation is local to one call. An adjoint needs a fresh assembly and factorisation at the converged state. The card's "about the cost of one more solve step" is right; the walk's "one back-substitution" is wrong. | the card must say it | `numerics/linear.py:56,192` |
| 15 | **Confirmed:** NUM-33 governs the dual-weighted-residual error estimator. An adjoint solved in the same finite-element space gives that estimator zero, so it needs a richer space and cannot reuse the primal factors. The card answers NUM-33's rationale only for sensitivities. NUM-33 should leave the Moves column, and so should "the adjoint later replaces the ladder". | blocks the proposal (the NUM-33 move) | NUM-32, NUM-33 |
| 15 | The Jacobian is exact in mode `none`. In the stabilised mode the parameters are lagged, so the adjoint would be inexact. The SuperLU path scales rows explicitly (`D·A`), so a transposed solve must return `D·z`. The reaction route needs the coupling rows between Dirichlet and free unknowns. Sensitivities come out in NUM-09's scaled units. | the card must say it | `models.py:970-987`; `linear.py:185-189` |
| 15 | Steps 4 to 6 of PHY-16 are linear in each `q_i` for fixed atoms, radii and frames, and a charge change moves neither the dielectric nor the geometry. Atoms of zero charge are not deposited, so their kernels have to be built. Protonation (step 3) is discrete, and a mutation changes atoms, radii and the contour of the protonated density. ±1 e is a finite change in a nonlinear problem, so the list ranks charge changes, not mutations. | the card must say it | PHY-16 |
| 15 | VER-13 is unfit. It is linear, so its Jacobian is the operator and nothing about the nonlinear Jacobian is tested. Its parameter is a Dirichlet value, whose adjoint path (the boundary rows) differs from a volume source. Better: Grahame's dζ/dσ_s (VER-12, VER-77), which is exact and nonlinear; an adjoint-against-tangent identity check; and finite-difference steps well above the Newton floor. | the card must say it | VER-13, VER-77 |
| 14 | **Confirmed:** under any measure that is not axisymmetric, the forms take the Cartesian branch and the hoop and `u_r/r` terms drop out. A 3D assembly therefore never touches NUM-04 to NUM-06. The (r, z) fixed-charge kernel has no 3D meaning. A fixed rule order builds rules for segments, triangles and quads only, so in 3D the charge's order-8 rule silently falls back: it assembles, with the wrong quadrature. Instead, solve VER-13 or VER-17 on a coarse 3D mesh and compare with the 2D solve. That also cross-checks NUM-04 to NUM-06. | blocks the proposal (the test) | `physics/flow.py:43,62`; `measures.py:128-133` |
| 22 | By PHY-12's coefficients (my arithmetic), `ε_r,f` is 77.6 at 0.05 M and 51 at 3 M, and the concentration factor on `μ_Na` is 0.86 and 0.47. Switching on at the target is the largest jump. It still keeps NUM-18's rationale of turning the corrections on last. | the card must say it | PHY-11, PHY-12 |
| 22 | **Doubt, not measured:** the packing fraction Φ = Σc_j / 13.3 M, which is 0.45 in a 3 M bulk. A classical state has no steric limit, so a counter-ion enrichment above about 4.4× near charged walls or deposited charges gives Φ ≥ 1. The entry gate then refuses the steric rung. Today the steric term enters at 0.05 M. | the card must say it | PHY-05, PHY-06; `newton.py:205` |
| 22 | A different path ends at a different iterate inside the Newton floor, so the VER-62 numbers move past 10⁻⁸. Neither the card nor the trial names the re-pin. | the card must say it | VER-62; `newton.py:322` |
| 22 | The four salt rungs become classical rungs; they are not removed. The 6–13× cost per step was measured on 392 elements. Sweep members started from a neighbour already skip the ladder. | note | evidence.md:164-181; NUM-18 NOTE |
| — | The Péclet figure of 0.33 and the evidence for primitive unknowns come from two 392-element cylinders, not from the FR-17 envelope or a mesh that meets NUM-30. Argue from §6.4.1 and NUM-11 instead. | note | evidence.md:164-166 |
| — | "Exact Jacobian" is true in mode `none` only. | note | `models.py:970-977` |

**Checked and sound**

- NUM-23 to NUM-26 are stated correctly: two current routes, and never the cross-section flux.
- VER-62's text does say "an error estimate is never held".
- The fixed charge is linear at fixed atoms, and a charge change moves neither the dielectric nor the geometry.
- Six correction rungs, four of them the salt ramp, matches `default_ladder`.
- P2 / Taylor–Hood, primitive unknowns and no stabilisation are today's code.
- Damping does not affect the converged Jacobian.
- At an active clamp the derivative is one-sided, as GU-15's risk says.

**Not checked**

- Whether NGSolve's UMFPACK inverse supports a transposed solve.
- Which switches walks 03, 07 and the 2WCD walks set beyond stabilisation and steric.
- Φ at 3 M on ClyA.
- NGSolve's order estimates per integrand, measured.
