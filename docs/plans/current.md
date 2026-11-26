# Current work

Updated 26 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** The design package of the kernel is planned. It writes how the core of the physics is rebuilt
from small registered pieces, and tries that in a throwaway prototype of the whole coupled model, checked against
today's equations, all thirteen stored reference runs and the tests of every push. A trial prices a 3D check.

**Cost.** About 3 sessions, 4 to 7 agent hours and 8 times you act, one to push the prototype's branch. The rest of
the phase after it: about 28 sessions, 16 to 30 agent hours and 43 times you act.

**What could go wrong.** The prototype may miss the stored numbers: a miss on the first example comes to you before
any kernel package is planned. Its branch is never merged, so its code survives only while that branch does.

**Your call.** Approve the plan of the design package, after its review? *Recommendation:* approve; it changes no
code a user runs and no rule.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.08 merged**,
  tagged to `v0.7.0-alpha.8`.
- **WP6.09, the kernel's design, is planned** ([the plan](phase-6/wp6.09-the-kernels-design.md);
  [§8.2.60](../../specification/history/60-wp609s-plan-the-kernels-design.md)): a design page, and a prototype of
  the whole coupled model on `prototype/wp6.09-kernel`, never merged, with thirteen walks reported on it.
- **After it, the rest is numbered at the round on that design** (BD1;
  [the input note](sessions/phases-6-to-11.md)).
- **Next:** `/np-plan wp 6.09 review` (Fable 5.2, high); then, approved, `/np-carry wp 6.09` (Sonnet 5.5, medium)
  or `/np-implement wp 6.09` (Opus 5.5, high).

## Not to be re-decided

- **Process rules** are §8.4: two lanes at most (S15); a VER-62 miss is reverted or re-pinned by ruling (G10); the
  reading limit is 8,000 words (AZ18); each role's model and effort are its agent's, and the author picks the
  planning model at each plan (BF1, BF9). **A gate asks three platforms at a phase's close; a pull request tests
  Linux** (AY4; AZ8).
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
- **The channel axis's two limits stay** (BE1). **Six settings get guard numbers, held on Linux alone** (BI1, BI2).
- **The prototype covers the whole model, on its own branch** (BJ1, BJ3).
- **An orchestrator carries a package; the three commands stay** (BC10; BD2). **The continuation trial adopts its path
  on a full pass of marks registered first** (BC24).

## Somebody else's

- **The ruling on the kernel's design**, after WP6.09 (BC2); **the boundary conditions of unequal reservoirs** (BC21); **the paper's figure data**, by Phase 7's close (D6; BC8); **verdicts at each design round and on the kit's trial**
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
