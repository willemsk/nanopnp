# Current work

Updated 19 November 2026 (WP5.21, the Analysis suite, planned). Navigation only; `SPECIFICATION.md` governs; an
unmerged branch is not shipped.

## In brief

The Analysis suite is planned. It opens a finished run: its field as a map, with a cut along the axis and probes, or
on its mesh in 3D; its current against voltage; its numbers. Comparison saves two runs, side by side on one scale or as
their difference. As you ruled, every plot moves to a borrowed chart library whose axes you set, any Matplotlib colour
map can be chosen, and Comparison's pair switches between maps and 3D. A run cleaned from the store is rebuilt on
request and checked against its record. About eight sessions, with the round.

**Your call.** Read the plan's review, then let it run. At the round: the tiles' layout and whether a run opens on the
map or in 3D. Recommendation: rule them on the drawn screens.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.20 merged
  (`v0.6.0-alpha.19`; WP5.20's `v0.6.0-alpha.20` to be pushed). **WP5.21**, [the Analysis suite](phase-5/wp5.21-the-analysis-suite.md),
  planned with the author's AU1 to AU3 (§8.2.45), its pull request open. **Next:** `/np-plan wp 5.21 review`, then
  `/np-implement wp 5.21`. Then WP5.22 performance, WP5.23 the route, WP5.24 the close. host: claude-code.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Phase 5 is a browser workbench, §8.2.17 S1 to
  S14; Qt stays gated until it** (M3). **Two lanes at most** (S15).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a
  VER-62 miss is reverted or re-pinned by ruling (G10, I4). **An open item is a `REV-nn` row** until resolved (H12).
- **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23). **The front end is NiceGUI; Mol*
  draws the molecule** (AF4). **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4).
- **One shell package per suite; variables keyed by resolved values** (§8.2.31). **A study overrides any model value**
  (AG12). **An output states its needs of a model** (AH1). **A user's theme sets its contrast** (AI1). **The store
  cleans the unused or all, never while a run holds it** (AN5, AN6).
- **Physics is a third model with its own suite; models declare exposed values; suites are prototyped on 2WCD first**
  (§8.2.34). **Layers read a model's declaration, never its name** (VER-56). **A callback is not an input** (VER-44).
  **A generated mesh is read only through `deployed_mesh`.** **Text follows the tested program** (AM1, AM2).
- **An edited outline keeps its charge; a continuum model builds alone** (§8.2.40). **A physics model is shown
  in a picked study** (§8.2.41). **Red blocks, blue informs; refusals are ASD-STE100** (WB-42). **A thread count is recorded, never keyed** (AR3).
- **Meso holds Density, Outline and Charge map; the 200 ms line is WP5.22's, after Analysis** (AR7, AR8; AS1 to
  AS3). **An edit marks the atoms it moves; the overlay is kept; a study's charge node opens the continuum model's**
  (AT1 to AT4). **The charge map opens on the 99th percentile; a free list of layers is its own package** (WB-49).
  **Every plot is uPlot's, its axes the user's; any Matplotlib map; Comparison's pair switches between maps and 3D**
  (AU1 to AU3).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run, in WP5.22 (REV-258); **where the free list of layers is placed** (REV-265); **verdicts on each suite's prototype** (AJ8).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **REV-156**'s speed-up is Phase 6's (Z6).

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
