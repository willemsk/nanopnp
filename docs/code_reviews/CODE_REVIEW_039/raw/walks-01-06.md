# Task walks 1 to 6: the six rows of SPECIFICATION.md's *Where to start, by task*

Walker: a Sonnet 5.5 sub-agent at medium effort, holding only each walk's path. Return saved verbatim.

AUDIT REPORT. Six walks at commit a5039af, nothing changed. Words are `wc -w`. Tokens are `wc -c` / 4.

How I read: I used Bash `cat`/`sed` and the Read tool. A clause printout counts as one file, and its words are the printout's. In walks 2 to 6 the text of `SPECIFICATION.md` was not re-read. I counted it again with `wc` and used the text already in my context. The same holds for Appendix A in walk 5. In walk 4, `06-numerics.md` lines 110-137 (the NOTE on the `r` weight) were not re-read in that walk. I had seen them earlier, in the walk 1 PHY clause printout.

======== WALK 1: change stage 7 (charge deposition) to report progress ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§3.2 (its FR), §5.2, §5.3.2, then the PHY or NUM clauses it cites"; the section-to-file map |
| 2 | specification/03-requirements.md | 6562 | §3.2 via the map | FR-13, FR-14, FR-15, FR-27 (progress-reporting, cancellable, typed content-hashed artefact), FR-38, QR-03, QR-12, QR-13; the IF-01 NOTE with `session.run(..., progress=, cancel=, on_stage=, on_solve=, on_artefact=)` |
| 3 | specification/05-software-design/02-pipeline-stages.md | 6150 | §5.2 via the map | Two rows numbered 7. The `charge` row has its inputs, outputs, kernel and gate: conservation to 10⁻³ of Q_net on the deployed mesh plus a per-z-slice check. The design note says stage 7 is two registered stages so stages 8-12 do not renumber |
| 4 | specification/05-software-design/03-2-artefacts.md | 2521 | §5.3.2 via the map | Stage 7 `charge` artefact is `nanopnp/fields/v0.5` with lattice `nanopnp/charge-grid/v0.5`, with their keys. A changed summary contract is a changed schema version. Also the workspace-locality, canonical-hash and warm-start NOTEs |
| 5 | clause.py --no-history PHY-16 PHY-17 PHY-18 PHY-19 (04-physics.md plus the NOTEs it attaches) | 5900 | Named in the stage-7 row, FR-13 and FR-14 | PHY-16 steps 4-7, PHY-17, PHY-18, PHY-19, the deposition-as-run NOTE and the producer-path conservation NOTE |

(2) Stalls
- "Implement or change a pipeline stage | §3.2 (its FR), …" does not say which FR belongs to a stage. I scanned the whole FR table: FR-12 to FR-15, FR-27 and FR-38 all touch stage 7.
- The task's "stage 7, the charge deposition stage" is ambiguous. §5.2 has two rows numbered 7, `protonation` and `charge`. Only the design note "Stage 7 is two registered stages, `protonation` and then `charge`…" resolves it.
- No file on the path says how a stage reports progress. FR-27 only says "progress-reporting", and the IF-01 NOTE lists the `session.run` keywords. §5.4 and §5.5 are not pointed to from here.
- Term "consumer path" and "producer leg" first appear in the §5.2 row and are defined only inside the PHY-19 NOTEs.
- The clause.py printout appended NOTEs from three other files, so it reads as one mixed file. One NOTE is cut mid-sentence ("the Jacobian and the `1/(2πr)` … cancel identically, so").
- Pointers to §8.2.4 D2, WP27 and WP28 (history) were not followed.
- Four of the five files are long reads for a progress-callback change.

(3) Answer: partly answered.
- What stage 7 `charge` must do and emit:
  - FR-13: assemble the axisymmetric fixed charge.
  - FR-14: assert charge conservation on the deployed mesh.
  - FR-15: build the dielectric field and ion-exclusion surface.
  - PHY-16 steps 4-7 and PHY-17.
  - PHY-18: renormalise each atom to q_i e.
  - PHY-19: conservation evaluated on the deployed mesh, plus the per-z-slice check against the source atoms.
  - QR-03: 10⁻³ tolerance.
  - QR-12: gate failures name the gate, quantity and location.
  - FR-27: the stage must be progress-reporting, cancellable, and emit a typed, serialisable, content-hashed artefact.
- What must not change:
  - the PHY-16 normative settings, and the 10⁻³ tolerance (the PHY-19 NOTE says it SHALL NOT be slackened);
  - the artefact schemas `nanopnp/fields/v0.5` and `nanopnp/charge-grid/v0.5` and their key contents. Progress must not enter the hash, and a summary-contract change would move the schema version;
  - the shared stage number 7;
  - QR-13 (weak forms written once).
- Not found on the path: the actual callback signature and where it is declared.

(4) Totals: 5 files, 22,150 words, 140,782 bytes, about 35,200 tokens.

======== WALK 2: add case key `numerics.mesh.axis_refinement` ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§5.3.1, §5.3.3, Appendix A" |
| 2 | specification/05-software-design/03-1-case-file.md | 11273 | §5.3.1 via the map | YAML skeleton with `schema: nanopnp/case/v0.6`. Schema-history NOTE. Compatibility rule inside the NOTE titled "`numerics.stabilisation`, and the compatibility rule for the case schema". `numerics.mesh` NOTE, `models:` ownership table, `variables:` unit-suffix rule, size_scale and other "knob with no effect" refusal precedents |
| 3 | specification/05-software-design/03-3-provenance-manifest.md | 483 | §5.3.3 via the map | Manifest field groups; "Deviations: every switch set away from the validated default" |
| 4 | specification/a-traceability-matrix.md | 2675 | Appendix A via the map | IF-03 row: VER-09, VER-36, VER-47, VER-71, VER-57, `tests/tier1/test_case_schema.py`; FR-25 row; FR-26 row |
| 5 | clause.py --no-history VER-71 | 555 | Named in the Appendix A FR-25 row | "No case leaf is accepted and never applied": every leaf of the case schema is classified once, and a leaf added to the schema and classified nowhere fails |

(2) Stalls
- The compatibility rule is in a NOTE whose title is about `numerics.stabilisation`. I found it only by reading the whole 11k-word file.
- Whether the identifier must move depends on whether v0.6.0 is tagged, and no file on the path says. The NOTE says "The identifier is fixed when `vX.Y.0` is tagged" and "Between that release's work packages, the schema under its identifier may change again without a new identifier". `docs/plans/current.md` would settle it, but this row does not point there.
- Appendix A lists tests, not which clauses govern a new key. VER-71 and VER-76 (named in the matrix coverage note) had to be inferred. I did not open VER-76.
- Terms `case_fields` and `io/variables.py` (a test fails on an unclassified leaf) are not resolved by any file on the path.
- Pointers to §8.2.2 B3, §8.2.7 G6, WP numbers and REV rows (history) were not followed.

(3) Answer
- Clauses governing a new key:
  - IF-03: one YAML case file, unknown keys rejected with a diagnostic naming the key.
  - FR-26: round trip.
  - FR-25: the manifest records every switch set away from the validated default.
  - QR-12: refusals name the gate and the key.
  - VER-71: no leaf accepted and never applied. The key must be classified, and refused when it has no effect, for example beside `inputs.mesh`.
  - VER-09 and VER-47.
  - Applicable §5.3.1 NOTEs: `numerics.mesh`, which refuses any `numerics.mesh` key away from its default beside `inputs.mesh` and already carries `size_scale`; the `models:` ownership table, where `numerics.mesh` belongs to the continuum model; the `variables:` unit-suffix rule.
- Compatibility rule: widening the accepted value set of an existing key is compatible and does not move the schema version. "Adding, removing, renaming or narrowing a key SHALL move it." In v0.6 every document must declare `nanopnp/case/v0.6` exactly. Any other identifier is refused, naming the expected and the declared identifier, before structural validation. A document written before the key therefore needs no migration if the key defaults to the validated configuration, as the NOTE says of earlier added keys. A document declaring another identifier, such as v0.5, is refused.
- The schema identifier is the first line of the YAML skeleton in §5.3.1, `schema: nanopnp/case/v0.6`. It is repeated in IF-03, the stage 9 row of §5.2, the §5.3.2 table and VER-47. By the rule, the first move inside v0.6 makes the identifier v0.6, and the identifier is fixed at the `v0.6.0` tag. Pre-release, the schema may change under it without a new identifier. If v0.6.0 is already tagged, the add must move the identifier. That fact is not on this path.

(4) Totals: 5 files, 16,003 words, 106,986 bytes, about 26,750 tokens.

======== WALK 3: wall correction to the ion diffusivity ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§4 and knowledge/01-physics-epnpns/, then §6" |
| 2 | knowledge/01-physics-epnpns/index.md | 170 | Link in the row | List of concept files |
| 3 | specification/04-physics.md | 6761 | §4 via the map | PHY-10, PHY-11, PHY-12 table, PHY-14, §4.6 errata rows 1 and 2 |
| 4 | data/corrections/willems2020_nacl.yaml | 1162 | Backtick path in PHY-12 | `ion_wall_function` block (P1 6.2, P2 0.01, "PLUS") |
| 5 | knowledge/01-physics-epnpns/03-the-corrections.md | 680 | Link in the knowledge index | Same form; "both are verified in §8" |

(2) Stalls
- After listing the two data/knowledge directories with `ls`, I used that listing only to look at the file names. That is a search-like step, not a pointer. The yaml and the concept file were then opened by pointers from PHY-12 and the knowledge index.
- "then §6" is a pointer with no condition. The question was answered from §4, so §6 was not opened.
- 03-the-corrections.md says "both are verified in §8", which is ambiguous with SPECIFICATION §8. It means knowledge file 08-errata. §4.6 gives the same check.
- In PHY-11, P₂ = 0.01 is given in nm while d̄ is dimensionless. A reader must infer that d̄ is d in nm.

(3) Answer
- Form: D_i(⟨c⟩, d) = D_i⁰ · f^c(c̄) · f^w(d̄), with c̄ = ⟨c⟩/1 M and d̄ = d/(1 nm).
- Wall correction: **f^w(d̄) = 1 − exp(−P₁ (d̄ + P₂))**.
  - The offset sign is PLUS. The viscosity wall function uses minus, `1 + exp(−P₁(d̄ − P₂))`.
  - The thesis eq. 5.11 minus sign is an erratum (§4.6 row 1).
  - Coefficients: P₁ = 6.2 nm⁻¹ and P₂ = 0.01 nm. The "0.62e1" notation is 6.2, not 62 or 0.62 (§4.6 row 2).
  - The same coefficients and function apply to μ_i.
  - Self-consistency check: f^w(0) = 0.06 and f^w(0.75 nm) = 0.99.
- File holding the fitted parameters: `data/corrections/willems2020_nacl.yaml`, block `ion_wall_function` (`form: exponential_saturation_plus`, P1: 6.2, P2: 0.01, `applies_to: [diffusivity, mobility]`).
- The concentration part, for completeness: f^c(c̄) = (1 + P₁c̄^½ + P₂c̄ + P₃c̄^{3/2} + P₄c̄²)⁻¹. For Na⁺: D⁰ = 1.334e-9, P = 0.202, −0.3048, 0.219, −0.03124. For Cl⁻: D⁰ = 2.032e-9, P = 0.149, −0.04933, 0.03392, 0.01431.

(4) Totals: 5 files, 9,790 words, 66,506 bytes, about 16,630 tokens.

======== WALK 4: damped Newton convergence and the Tier 2 solver benchmark ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§6, §7.3" |
| 2 | specification/06-numerics.md | 7065 | §6 via the map | NUM-16 and its NOTEs, NUM-17, NUM-18 ladder, NUM-26 |
| 3 | specification/07-verification/03-tier-2.md | 2990 | §7.3 via the map | VER-12 to VER-22, VER-26, VER-31, VER-35, VER-39, VER-42, VER-62, VER-77 |

(2) Stalls
- §5.3.1's `numerics.nonlinear` NOTE says the settings are "tested on the residual and on the relative update alike". The NUM-16 NOTE says the residual relative to its entry value is rejected and convergence is a per-field relative-update test. I resolved this in favour of NUM-16, the section the row points to. The case-file wording looks stale. I did not read that NOTE in this walk.
- No Tier 2 row names the Newton convergence criterion directly. The solver benchmarks are inferred. I did not open §7.2 (Tier 1), where a criterion test might sit.
- Dated markers (WP41 D4, REV-08, §8.2.27 AC2) refer to history and were not followed.

(3) Answer
- NUM-16: monolithic damped Newton on the fully coupled system with a direct linear solve.
  - Damping adapts on residual reduction and is bounded below.
  - If the minimally damped step still fails to reduce the residual, that step is accepted rather than the solve aborted. A non-finite trial residual is not accepted: it raises a divergence.
- Convergence test (NUM-16 NOTE): a relative-update test on the undamped Newton direction, field by field. For every field f, ‖δu_f‖ ≤ rtol · max(‖u_f‖, 10⁻⁶ · max(‖u‖, 1)). Alternatively, the residual at its absolute floor of 10⁻¹². A step that failed to reduce the residual never counts as convergence.
- Tolerances:
  - rtol = 1×10⁻⁶ (finite, in (0, 1));
  - max_iter = 100 (at least 1);
  - initial damping 0.2;
  - minimum damping 1×10⁻²;
  - recovery damping 0.2;
  - fully coupled, no segregation groups.
- NUM-17, asserted every Newton step: min c_i > 0; Φ < 1; ‖δφ‖∞ ≤ V_T. A violation aborts naming the field and location.
- Tier 2 benchmarks that exercise the solver:
  - VER-18: method of manufactured solutions on the full coupled axisymmetric system, with O(h³) in L² for P2. It is the only check of the u_r/r² term and the axis treatment.
  - VER-16: 1D steady PNP with the limiting-current plateau.
  - VER-17: Maxwell-Hall access conductance within 2 %.
  - VER-12 to VER-15: Gouy-Chapman, Debye-Hückel, Rice-Whitehead, Helmholtz-Smoluchowski.
  - VER-62: number stability, 10⁻⁸ relative, on seven gated walks.
  - VER-35: end-to-end reproduction from the manifest within the 1×10⁻⁶ nonlinear tolerance.
  - No Tier 2 row tests the update-based criterion on its own.

(4) Totals: 3 files, 11,072 words, 72,170 bytes, about 18,040 tokens.

======== WALK 5: test that the CLI refuses an unknown case-file key ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§7.1 (tiers and the test scope), the VER or VAL row, Appendix A" |
| 2 | specification/07-verification/01-strategy.md | 511 | §7.1 via the map | The test-scope NOTE |
| 3 | specification/a-traceability-matrix.md | 2675 | Appendix A via the map | IF-03 row: VER-09, VER-47, `tests/tier1/test_case_schema.py`, "verified at review (§8.2.13 N3)" |
| 4 | clause.py --no-history VER-09 VER-47 | 568 | Named in the IF-03 row | VER-09: "an unknown key is rejected with a diagnostic naming the key"; VER-47 |

(2) Stalls
- The row says "the VER or VAL row" without saying which. I picked the IF-03 row of Appendix A.
- No file on the path states how a test is named. The §7.1 NOTE points to §8.2.13 N1 and N3, which are history. Neither §7.1 nor Appendix A mentions §8.4.3, which holds that rule. That is a dead end.
- "Where it goes" is not stated in §7.1. The only locator is the existing `tests/tier1/test_case_schema.py` in Appendix A.
- The IF-03 Appendix A cell is one long cell. Which items are tested and which are "verified at review" has to be read from its end.

(3) Answer: No, not as a CLI-level test.
- The §7.1 test-scope NOTE says "A refusal is tested only where it is a numerical or physical gate. Each entry point keeps a thin smoke test." An unknown-key refusal is a schema refusal, not a numerical or physical gate.
- The CLI is an entry point, so it gets only a thin smoke test. A row outside the scope "stays normative and is verified at review", and no test is added.
- Appendix A already lists the CLI behaviour ("that `nanopnp validate case` … give them in a run's text … are verified at review (§8.2.13 N3)").
- The schema-level behaviour is already VER-09, in Tier 1, which is where the existing case-schema tests sit (`tests/tier1/test_case_schema.py`). No new test is needed.
- Naming rule: not found on this path.

(4) Totals: 4 files, 4,771 words, 35,304 bytes, about 8,830 tokens.

======== WALK 6: next work package, planning command, plan contents and length ========

(1) Files

| # | File | Words | Pointer | Gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Row "§8.1, §8.4, then docs/plans/current.md" |
| 2 | specification/08-implementation-plan/01-phases-and-gates.md | 1395 | §8.1 via the map | Phase 5 table: library packages WP5.03-5.07 and WP5.09, shell WP5.08 and WP5.15-5.22 |
| 3 | specification/08-implementation-plan/04-development-process.md | 2069 | §8.4 via the map | §8.4.4 plan rules and `/np-plan` levels |
| 4 | docs/plans/current.md | 699 | Link in the row | Position: WP5.09 delivered 8 Nov 2026, "Next `/np-ship wp 5.09`"; WP5.15 is the frame; CODE_REVIEW_036's six refactors land after WP5.09 through `/np-plan amend 5` |

(2) Stalls
- "Which package is next" is ambiguous in `current.md`. "Next `/np-ship wp 5.09`" is the next step. The next package to plan is WP5.15, and an amendment (`/np-plan amend 5`) is queued before or beside it. The order is not stated.
- §8.4.4 gives the plan caps but no path to the file that holds the full plan template. `.claude/skills/np-plan/wp.md` and `review.md` appear only in the project notes, not on this path. `review.md` is named in the §8.4.4 text. I did not open it.
- Two statements of the In brief length differ: §8.4.4 says "about 250 words, up to 10% over", while `current.md`'s Handoff Rules say "at most 250 (no backticks or identifiers)". They concern different documents.
- The links to `phase-5-workbench.md`, `phase-5-record.md` and `wp5.09-the-physics-model.md` were not followed.

(3) Answer
- Next work package: WP5.09 (the physics model) is delivered and awaits `/np-ship wp 5.09`. After it, WP5.15 (the frame) is next in Phase 5. CODE_REVIEW_036's six refactors (REV-217 to REV-221 and REV-170) are planned through `/np-plan amend 5` after WP5.09, ahead of or alongside WP5.15.
- Planning command: `/np-plan wp 5.15` (§8.4.4: `/np-plan <project | phase n | amend n | wp n> [review]`; a work package is named `WP<phase>.<nn>`; the plan file is `docs/plans/wp5.15-<slug>.md`). `/np-plan wp 5.15 review` reviews it afterwards.
- A plan must contain:
  - `## In brief`, about 250 words and at most 10% over, readable without code or identifiers: what changes and why, what it costs, what could go wrong and how it would be noticed, then *Your call* with each decision that waits for the author and a recommendation.
  - `### Grounding`: by symbol, what the code does today, the call path, what it reads and writes, every variant of its input, the registry and layering rows it adds, and how each test gets the object it checks.
  - `### Implementation details`: 1,000 words, giving a smaller model the exact steps.
  - Each work item names its executor, either the main session or a sub-agent by type and model. The plan names the implementing session's model and effort.
  - One commit per work item, ticked `[x] <short sha>`.
  - Compaction checkpoints as work items.
  - Only in-scope tests, listed but not committed.
  - No `## Design` heading.
- Length cap: 3,500 words outside its Outcome annotations, of which 1,500 are outside Grounding and Implementation details. Each count may run up to 10% over; beyond that the plan is trimmed or split. About six decisions is a guideline, not a cap. WP57 and WP5.08 are exempt or have their own allowance.

(4) Totals: 4 files, 5,180 words, 36,165 bytes, about 9,040 tokens.

======== GRAND TOTALS ========
26 files opened across the six walks, 68,966 words, 457,913 bytes, about 114,500 tokens (`SPECIFICATION.md` counted once per walk).
