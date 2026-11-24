# Current work

Updated 24 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** Four packages have their numbers, in the order they are built. The first builds a new way to carry
a package: one session that you start hands each step to a fresh helper and comes to you only for rulings, the
plan's approval and the merge. It is tried on the next two: the fix for the pore's axis, and stored reference numbers
for the model's optional switches. The fourth designs how the physics is rebuilt from small registered terms, with a
prototype. You rule that design before any package of the rebuild is planned.

**Cost.** About 43 sessions, 26 to 49 agent hours and 66 times you act. Your ruling round on the
design adds about 2 sessions and 3.

**What could go wrong.** The helpers may be unable to run the commit checks or to ask you a question; the first
package tests that first and falls back to separate sessions. The prototype may miss the stored numbers, which comes
to you before the rebuild is planned. The rebuild is checked in full only at its last package; the nightly run would
show a moved result sooner.

**Your call.** Do you approve the amendment, by merging its pull request? *Recommendation:* approve; it departs from
none of your rulings.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.04 merged**
  and tagged, to `v0.7.0-alpha.4`.
- **Phase 6 is amended** ([§8.2.54](../../specification/history/54-phase-6-amended-the-packages-after-the-review-numbered.md),
  BD1): WP6.05 the orchestrator, WP6.06 the axis fix, WP6.07 the guard numbers, WP6.08 the kernel's design; the
  rest is numbered at the round on the design. Phases 6 to 12: [the input note](sessions/phases-6-to-11.md).
- **Next:** `/np-plan amend 6 review`, on Fable 5.2; then `/np-plan wp 6.05`.

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
- **An orchestrator carries a package; the three commands stay** (BC10). **The continuation trial adopts its path
  on a full pass of marks registered first** (BC24).

## Somebody else's

- **What the reading limit counts under the orchestrator**, at WP6.05's plan; **the ruling on the kernel's design**,
  after WP6.08 (BC2); **the boundary conditions of unequal reservoirs** (BC21); **the paper's figure data**, by Phase 7's close (D6; BC8); **verdicts at each design round and on the kit's trial**
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
