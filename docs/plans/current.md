# Current work

Updated 24 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

You have ruled on every proposal of the ground-up review. The rulings are written into the specification and wait
for their check.

**What changes.** The physics is rebuilt from small registered terms in this phase, first after the axis fix, after
a design package with a throwaway prototype that you rule on. The phase is split in two: the library's foundations
become the next phase, and the workbench's rebuild, with the composer's tool, the one after. No later release is
renumbered. One session will carry a whole package through fresh helpers, tried on the axis fix. The next phase
adds a page that shows which test proves each term, an error bar for the mesh, unequal reservoirs, and one
recorded comparison with the paper at its close.

**Cost.** This phase: about 43 more sessions, 26 to 49 agent hours and 66 times you act, at today's rates. The next
phase: about 68 sessions and 108.

**What could go wrong.** The kernel is checked in full only at its last package, so a result an early package
moves may be found late; the nightly run would show it. Its size is the review's draft count, which the challenge
found low. Unequal reservoirs are physics outside the paper's model.

**Your call.** Nothing now: the write-up is checked first. *Recommendation:* push the tag for the review's package,
which is still missing.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.04 merged**;
  `v0.7.0-alpha.4` is the author's to push.
- **The ground-up review is ruled** ([§8.2.53](../../specification/history/53-the-ground-up-review-ruled.md), BC1 to
  BC24; REV-280 fixed). Phases 6 to 12: [the input note](sessions/phases-6-to-11.md).
- **Next:** `/np-plan project review`, on Fable 5.2. Then `/np-plan amend 6`: the orchestrator, WP6.05, the guard
  numbers, the kernel's design, the kernel, the installed packages, the close. Until it, the Phase 6 plan reads as
  before the rulings.

## Not to be re-decided

- **Process rules** are §8.4: two lanes at most (S15); a VER-62 miss is reverted or re-pinned by ruling (G10); an
  open item is a `REV-nn` row (H12); the reading limit is 8,000 words (AZ18); each plan proposes its two models
  (AZ20, AZ21).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); **from v1.0 the case file and the run record are
  converted** (BC20).
- **The front end is NiceGUI, tried on its hardest view before the rebuild** (AF4; BC13); **the workbench's layout
  is its design document's** (BC16).
- **The phases are kernel, library, workbench with the composer's tool, mutator, sketcher, analyte forces,
  validation** (BC1, BC6, BC7; BA1, BA5). **One comparison with the paper is recorded at Phase 7's close and gates
  nothing** (BC8).
- **The kernel comes first after the axis fix, after a design the author rules; its full check runs at its last
  package** (BC1 to BC4).
- **An orchestrator carries a package; the three commands stay** (BC10). **QR-11 is withdrawn** (BC11). **The
  continuation trial adopts its path on a full pass of marks registered first** (BC24).

## Somebody else's

- **The ruling on the kernel's design** (BC2); **the boundary conditions of unequal reservoirs** (BC21); **the
  paper's figure data**, by Phase 7's close (D6; BC8); **verdicts at each design round and on the kit's trial**
  (AJ8; BC13); **whether shapes replace the sketcher**, at Phase 10's round (BC14).
- E1's ensemble legs; Read the Docs; `$NANOPNP_REFERENCE_DATA` on the nightly runner; the 200 ms redraw's GPU run
  (REV-258); rulings on a cycle (H6) or drift (I4).
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents (BA6); the customised PDB2PQR (BA9); the PlyAB model
  files (OPN-03); a second pore's data, if any (BC19); QR-10's observer (AW2).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-6/phase-6-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; `docs/design/reviews/`; §8.2.17 onwards.
- **Code:** `docs/project/architecture-survey.md`; `docs/project/ground-up-review.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
