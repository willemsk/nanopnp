# Current work

Updated 27 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** You ruled the kernel's design. Three packages rebuild the model's equations from small registered
pieces, the cleaner structure winning over an old number. Three more solve two benchmarks on a 3D mesh and price the
flow in 3D, and a last one lets an installed package add a term.

**Cost.** Spent on the round: one session. Left: about 24 sessions, 20 to 37 agent hours and 38 times you act, the 3D
pore's machine time not yet measured.

**What could go wrong.** A lost term could hide behind a re-pinned number; a package that moves one must show the old
value returns with its one change undone. The 3D pore's solve may not fit a machine; a miss comes to you.

**Your call.** Approve the amended plan after its review, by merging its pull request? *Recommendation:* approve; it
records your ten rulings and departs from none.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.09 merged**,
  tagged to `v0.7.0-alpha.9`. The prototype is `prototype/wp6.09-kernel` at `1b5f5e3`, on `origin`, never merged.
- **The kernel's design is ruled** (§8.2.62; [the design](../design/kernel.md); §5.4.4); the amended plan is not
  yet merged.
- **Planned by scope:** WP6.10 to WP6.12, the kernel; WP6.13 to WP6.15, the 3D benchmarks; WP6.16, the installed
  packages; the close.
- **Next:** `/np-plan amend 6 review` (Fable 5.2, high). Then the author merges the amendment's pull request, then
  `/np-carry wp 6.10`, the composition (Sonnet 5.5, medium; the author picks its plan's model).

## Not to be re-decided

- **Process rules** are §8.4: two lanes at most (S15); the reading limit is 8,000 words (AZ18); the author picks the
  planning model at each plan (BF1, BF9). **A gate asks three platforms at a phase's close; a pull request tests
  Linux** (AY4; AZ8). **No touches target** (BL10).
- **A session may restructure code while the push gate passes, its nightly walks not asked** (BA7, BA14). **The more
  modular structure comes before a held number** (BL1).
- **A VER-62 miss is reverted or re-pinned by ruling** (G10); **in WP6.10 to WP6.12 a stored number the kernel moves is
  re-pinned once explained** (VER-62; BL2). **The full check runs at WP6.12** (BC4; BL3).
- **No term names the backend or a dimension** (BL6). **The wind reads every drift** (BL5). **The log branch is a case
  key** (BL7). **An installed package registers through one registrar** (BL8).
- **3D is in benchmarks alone, before the installed packages** (BL4, BL9; N4).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4; BC20).
- **The front end is NiceGUI, tried on its hardest view before the rebuild** (AF4; BC13; BC16).
- **The phases are kernel, library, workbench with the composer's tool, mutator, sketcher, analyte forces,
  validation** (BC1, BC6, BC7; BA1, BA5). **One comparison with the paper at Phase 7's close gates nothing** (BC8).
- **The channel axis's two limits stay** (BE1). **Six guard numbers are held on Linux alone** (BI1, BI2).
- **An orchestrator carries a package; the three commands stay** (BC10; BD2).

## Somebody else's

- **A ruling if the 3D solve misses its marks** (WP6.14), **and on the flow in 3D after its trial** (WP6.15; BL4);
  **the boundary conditions of unequal reservoirs** (BC21); **the paper's figure data**, by Phase 7's close (D6; BC8);
  **verdicts at each design round and on the kit's trial** (AJ8; BC13); **whether shapes replace the sketcher**, at
  Phase 10's round (BC14).
- E1's ensemble legs; Read the Docs; `$NANOPNP_REFERENCE_DATA` on the nightly runner; the redraw's GPU run
  (REV-258); rulings on a cycle (H6) or drift (I4).
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents (BA6); the customised PDB2PQR (BA9); the PlyAB files
  (OPN-03); a second pore's data (BC19); QR-10's observer (AW2).

## On demand

- **Specification:** `SPECIFICATION.md`; `docs/project/decisions.md`. **Amendments:** `phase-6/phase-6-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`.
- **Workbench:** `docs/design/workbench.md`.
- **Code:** `docs/project/architecture-survey.md`; `docs/project/ground-up-review.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
