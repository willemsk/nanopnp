# Current work

Updated 24 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** The next package is planned: a new way to carry a package. One session that you start hands the
plan, the building and the shipping to fresh helpers, and comes to you only for rulings, the plan's approval and the
merge. A helper cannot ask you a question or start its own helper, so your session does both for it. It is tried
on the two packages after it: the fix for the pore's axis, and stored reference numbers for the model's optional
switches. Then a design package says how the physics is rebuilt from small registered terms, and you rule that
design before the rebuild.

**Cost.** This package: about 5 sessions, 3 to 6 agent hours and 8 times you act; the phase after it, about 38, 23
to 43 and 58.

**What could go wrong.** The session you start may fill up from the reviews it runs; the next two packages measure
it, and the three commands remain. The prototype may miss the stored numbers, which comes to you first. The rebuild
is checked in full only at its last package; the nightly run would show a moved result sooner.

**Your call.** Do you approve the plan of the orchestrator's package, after its review? *Recommendation:* approve;
it follows your six rulings of today.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.04 merged**
  and tagged, to `v0.7.0-alpha.4`.
- **Phase 6 is amended** ([§8.2.54](../../specification/history/54-phase-6-amended-the-packages-after-the-review-numbered.md),
  BD1): then WP6.06 the axis fix, WP6.07 the guard numbers, WP6.08 the kernel's design; the rest is numbered at the
  round on the design. Phases 6 to 12: [the input note](sessions/phases-6-to-11.md).
- **WP6.05 is planned** ([the plan](phase-6/wp6.05-the-orchestrator.md); BD2 to BD6).
- **Next:** `/np-implement wp 6.05`, on Opus 5.5, once the author approves the reviewed plan.

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
