# Current work

Updated 18 November 2026 (Phase 5 amended: the meso suite and the performance package placed). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 5 is merged through the Study suite. The plan now places the two packages you asked for at the Study round.
The new suite between Molecular and Continuum comes next: it shows how the molecule becomes the pore's shape and
charge, each picture beside the molecule, and takes the outline and charge tools from where they stand. The Analysis
suite follows, then the performance package, timed on your machine with a graphics card, then the guided route and
the close. The later packages moved up a number, and every mention of them was renumbered, the records included.

**Your call.** At the review: is the plan's entry for the new suite what you meant by a bridge between the scales?
Recommendation: yes; it holds the three tools ruled at the Study round and adds no kind of model.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.19 merged
  (`v0.6.0-alpha.19`). The fifth amendment (§8.2.43 AS1 to AS4) is on `claude/serene-pascal-dmnl60`: the meso suite
  is WP5.20, the performance package WP5.22; Analysis, the route and the close are WP5.21, WP5.23 and WP5.24.
  **Next:** `/np-plan amend 5 review`, then, once merged, `/np-plan wp 5.20`.
  host: claude-code.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Phase 5 is a browser workbench, §8.2.17 S1 to
  S14; Qt stays gated until it** (M3). **Two lanes at most** (S15).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a
  VER-62 miss is reverted or re-pinned by ruling (G10, I4). **An open item is a `REV-nn` row** until resolved (H12).
- **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23). **The front end is NiceGUI; Mol*
  draws the molecule** (AF4). **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4).
- **One shell package per suite; variables keyed by resolved values** (§8.2.31). **A study overrides any model value**
  (AG12). **The store cleans the unused or all, never while a run holds it** (AN5, AN6).
- **Physics is a third model with its own suite; models declare exposed values; suites are prototyped on 2WCD first**
  (§8.2.34). **Layers read a model's declaration, never its name** (VER-56). **A callback is not an input** (VER-44).
- **An edited outline keeps its charge; a continuum model builds alone** (§8.2.40). **Red blocks, blue informs;
  refusals are ASD-STE100** (WB-42). **A thread count is recorded, never keyed** (AR3).
- **The meso suite is next, WP5.20, holding Density, Outline and Charge map and named at its round; the 200 ms line is
  the performance package's, WP5.22, after Analysis** (AR7, AR8; §8.2.43 AS1 to AS3).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run, in WP5.22 (REV-258); **the meso suite's name**, at WP5.20's round (AS3); **verdicts on each suite's prototype** (AJ8).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **REV-156**'s speed-up is Phase 6's (Z6); a cleaned run's rebuild WP5.21's (AN5).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-5-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; §8.2.17, §8.2.30,
  §8.2.31, §8.2.34, §8.2.42, §8.2.43; `docs/design/reviews/`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
