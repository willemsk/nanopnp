# Current work

Updated 25 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** The orchestrator is merged and carries its first package, the fix for the pore's axis, whose plan
is written. It found the fault larger than recorded, about one degree and not 0.6, and its cause elsewhere: a
space lost at a flat rim, not a broken tie. The fix cures every trial wall, and the real pore keeps its axis to the
last digit. You ruled that the two limits stay, that a case on a channel's axis runs again once, and the models.
Fresh helpers now review, build and ship it; the stored reference numbers for the optional switches follow.

**Cost.** This package: about 4 sessions, 2 to 4 agent hours and 6 times you act. The rest of the phase with it:
about 38 sessions, 23 to 43 agent hours and 58 times you act.

**What could go wrong.** The session you started may fill up from the reviews it runs; this package and the next
measure it; the three commands remain the way back.

**Your call.** Approve the axis plan after its review. *Recommendation:* approve; your three rulings are in it.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.05 merged**,
  tagged to `v0.7.0-alpha.4`; `v0.7.0-alpha.5` is not published yet.
- **Phase 6 is amended** ([§8.2.54](../../specification/history/54-phase-6-amended-the-packages-after-the-review-numbered.md),
  BD1): WP6.06 the axis fix, WP6.07 the guard numbers, WP6.08 the kernel's design; the rest is numbered at the round
  on the design. Phases 6 to 12: [the input note](sessions/phases-6-to-11.md).
- **WP6.06 is planned** ([the plan](phase-6/wp6.06-the-channel-axis-at-a-ragged-rim.md);
  [§8.2.55](../../specification/history/55-wp606s-plan-the-channel-axis-limits-stored-results-and-models.md), BE1 to
  BE3).
- **Next:** `/np-plan wp 6.06 review` on Fable 5.2; then `/np-implement wp 6.06` on Opus 5.5 and `/np-ship wp 6.06`
  on Fable 5.2; then `/np-carry wp 6.07`.

## Not to be re-decided

- **Process rules** are §8.4: two lanes at most (S15); a VER-62 miss is reverted or re-pinned by ruling (G10); the
  reading limit is 8,000 words (AZ18); each plan proposes its two models (AZ20, AZ21). **A gate asks three
  platforms at a phase's close; a pull request tests Linux** (AY4; AZ8).
- **A session may restructure code while the push gate passes, its nightly walks not asked** (BA7, BA14).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); **from v1.0 the case file and the run record are
  converted** (BC20).
- **The front end is NiceGUI, tried on its hardest view before the rebuild** (AF4; BC13); **the workbench's layout
  is its design document's** (BC16).
- **The phases are kernel, library, workbench with the composer's tool, mutator, sketcher, analyte forces,
  validation** (BC1, BC6, BC7; BA1, BA5). **One comparison with the paper is recorded at Phase 7's close and gates
  nothing** (BC8).
- **The kernel follows the axis fix and a design the author rules; its full check runs at its last package** (BC1
  to BC4).
- **The channel axis's two limits stay; a stored channel case runs again once** (BE1, BE2).
- **An orchestrator carries a package; the three commands stay** (BC10; BD2). **The continuation trial adopts its path
  on a full pass of marks registered first** (BC24).

## Somebody else's

- **The ruling on the kernel's design**, after WP6.08 (BC2); **the boundary conditions of unequal reservoirs** (BC21); **the paper's figure data**, by Phase 7's close (D6; BC8); **verdicts at each design round and on the kit's trial**
  (AJ8; BC13); **whether shapes replace the sketcher**, at Phase 10's round (BC14).
- E1's ensemble legs; Read the Docs; `$NANOPNP_REFERENCE_DATA` on the nightly runner; the 200 ms redraw's GPU run
  (REV-258); rulings on a cycle (H6) or drift (I4).
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents (BA6); the customised PDB2PQR (BA9); the PlyAB model
  files (OPN-03); a second pore's data, if any (BC19); QR-10's observer (AW2).

## On demand

- **Specification:** `SPECIFICATION.md`; `docs/project/decisions.md`. **Amendments:** `phase-6/phase-6-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`.
- **Workbench:** `docs/design/workbench.md`.
- **Code:** `docs/project/architecture-survey.md`; `docs/project/ground-up-review.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
