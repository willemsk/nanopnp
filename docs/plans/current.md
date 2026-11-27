# Current work

Updated 27 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

**What changes.** The first of three packages that rebuild the model's equations is built, reviewed and merges
once CI is green: the same equations, assembled from small registered pieces, none naming the finite-element
library or two dimensions. A user notices nothing at the defaults; with the dielectric forces and a stabilisation
both on, the stabilisation now reads the dielectric drift too, as you ruled.

**Cost.** Left: your merge. The rest of the phase about 21 sessions, 17 to 30 agent hours and 33 times you act, the
3D pore's machine time not measured.

**What could go wrong.** Nothing moved beyond round-off: the thirteen stored runs hold to 2.9 × 10⁻¹². That opt-in
combination assembles about fifty times more slowly (REV-302).

**Your call.** Merge the pull request. *Recommendation:* merge; it tags `v0.7.0-alpha.10`.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md)), `v0.7`: **WP6.01 to WP6.10 merged**,
  tagged to `v0.7.0-alpha.10`.
- **The kernel's design is ruled** (§8.2.62; [the design](../design/kernel.md); §5.4.4).
- **WP6.10, the composition, is merged and tagged `v0.7.0-alpha.10`** ([the plan](phase-6/wp6.10-the-composition.md);
  VER-81; PR #227). **By scope:** WP6.11 and WP6.12, the kernel; WP6.13 to WP6.15, the 3D benchmarks; WP6.16, the
  installed packages; the close.
- **Next:** `/np-plan wp 6.11`, the switch records, the log branch's key and `post/forces.py` reading the densities.

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
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); **from v1.0 the case file and the run record are
  converted** (BC20).
- **The front end is NiceGUI, tried on its hardest view before the rebuild** (AF4; BC13); **the workbench's layout
  is its design document's** (BC16).
- **The phases are kernel, library, workbench with the composer's tool, mutator, sketcher, analyte forces,
  validation** (BC1, BC6, BC7; BA1, BA5). **One comparison with the paper at Phase 7's close gates nothing** (BC8).
- **The channel axis's two limits stay** (BE1). **Six guard numbers are held on Linux alone** (BI1, BI2).
- **An orchestrator carries a package; the three commands stay** (BC10; BD2). **The continuation trial adopts its
  path on a full pass of marks registered first** (BC24).

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
