# Current work

Updated 20 November 2026 (the sixth Phase 5 amendment: every open item placed). Navigation only; `SPECIFICATION.md` governs; an
unmerged branch is not shipped.

## In brief

Every point the reviews left open now has a package. Seven remain: results as an editable tree;
display layers in every molecule view; speed on a graphics card; plain messages that lead to their field; a
polish pass over every suite; the guided route, with new models and the old shell removed; the
close. Later points name a later phase's package.

**Your call.** Approve the amended plan after its review, then the tree of results at its design round.
*Recommendation:* settle it on drawn screens.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.21 merged
  (`v0.6.0-alpha.19`; alpha.20 and .21 to be pushed). The sixth amendment (§8.2.46) placed
  every open item: WP5.22 the tree of results, WP5.23 the layers, WP5.24 performance,
  WP5.25 the refusals, WP5.26 the polish pass, WP5.27 the route, WP5.28 the close.
  **Next:** `/np-plan amend 5 review`; then `/np-gui grill` on the tree of results (REV-268) and `/np-plan wp 5.22`. host: claude-code.

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
- **Meso holds Density, Outline and Charge map; the 200 ms line is WP5.24's** (AR7, AR8; AS1 to
  AS3). **An edit marks the atoms it moves; the overlay is kept; a study's charge node opens the continuum model's**
  (AT1 to AT4). **The charge map opens on the 99th percentile; a free list of layers is WP5.23, in every Mol* view** (WB-49; AV3).
  **A plot's axes are the user's; any Matplotlib map; a true 3D view is the tree's**
  (AU1 to AU3; WB-53). **Analysis becomes a tree of results, its chart library chosen again** (WB-51). **The words follow
  five rules** (WB-52). **Every open item names a package** (§8.2.46).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run, in WP5.24 (REV-258); **verdicts at each design round** (AJ8); **the Copilot host's checks**, before the close (REV-166 to REV-168; AV6).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **Phase 6's provisional packages** (AV5), REV-156's speed-up first (Z6).

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
