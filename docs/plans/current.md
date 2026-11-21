# Current work

Updated 21 November 2026 (verdicts collected; Phase 5 to close early). Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

The verdicts keep the results tree, its plot types and its chart library, and ask for every run reachable, views
that split and tab like a code editor, settings in their own pane, and the boards' finer style everywhere. Two code
surveys found a sound solving core, but a results side and a workbench spine that would make those features one-off
code. You ruled that the restructure opens the next phase, after a scope round and a cleanup of the records and
instructions, and that this phase closes soon.

**Your call.** Approve the amendment moving the remaining packages. *Recommendation:* keep the desktop shell's
removal, a short guide and the close; move the rest, so nothing is built twice.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.21 merged
  (`v0.6.0-alpha.19`; alpha.20 and .21 to be pushed). WP5.22's round ruled WB-54 to WB-63
  ([record](../design/reviews/2026-11-21-tree.md)); its verdicts reopen three (REV-273). The author ruled that the
  restructure ([survey](../project/architecture-survey.md)) opens Phase 6 and Phase 5 closes early (REV-272). **Next:** `/np-plan amend 5` (REV-272's moves; REV-271). host: claude-code.

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
  in a picked study** (§8.2.41). **Red blocks, blue informs; refusals are ASD-STE100** (WB-42).
- **Meso holds Density, Outline and Charge map** (AR8; AS1 to AS3). **An edit marks the atoms it moves; the overlay is kept; a study's charge node opens the continuum model's**
  (AT1 to AT4). **The charge map opens on the 99th percentile** (WB-49).
  **A plot's axes are the user's; any Matplotlib map; a true 3D view is the tree's**
  (AU1 to AU3; WB-53). **Analysis is COMSOL's tree; Plotly draws every chart and map** (WB-54 to WB-63). **Phase 6 opens with its scope, a cleanup, then the foundations** (REV-272). **The words follow
  five rules** (WB-52). **Every open item names a package** (§8.2.46).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8); **the Copilot host's checks**, before the close (REV-166 to REV-168; AV6).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **Phase 6's provisional packages** (AV5), REV-156's speed-up first (Z6).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-5-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; `docs/design/reviews/`; §8.2.17 onwards.
- **Code:** `docs/project/architecture-survey.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
