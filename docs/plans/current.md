# Current work

Updated 26 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** The kernel's design is built and waits for its review. Its page proposes rebuilding the core of
the physics from small registered pieces. The throwaway prototype matched today's equations to round-off and every
stored run, and passed the tests of every push. A short trial priced a 3D check at one package.

**Cost.** Left: the review and the ship. The page prices the kernel at four packages, about 12 sessions, 9 to 16
agent hours and 19 times you act; the round sets it.

**What could go wrong.** The prototype holds the numbers, which shows that the design can hold them, not that the
kernel will. One question it found, the stabilisation's wind, is yours at the round.

**Your call.** Nothing until the review; then the seven choices at the page's end. *Recommendation:* ship the
package, then rule the design as the page recommends.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.08 merged**,
  tagged to `v0.7.0-alpha.8`.
- **WP6.09, the kernel's design, is built** ([the plan](phase-6/wp6.09-the-kernels-design.md);
  [the design](../design/kernel.md)): the prototype is `prototype/wp6.09-kernel` at `1b5f5e3`, on `origin`, never
  merged. Its pull request waits for `/np-ship wp 6.09`.
- **After it, the round on the design** (`/np-plan amend 6`) rules the design, the kernel's packages and the 3D
  benchmark, and numbers what follows (BC2, BC5; BD1; [the input note](sessions/phases-6-to-11.md)).
- **Next:** `/np-ship wp 6.09` (Sonnet 5.5, medium), within `/np-carry wp 6.09`.

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
