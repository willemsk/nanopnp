# Current work

Updated 22 November 2026. Navigation;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 5 is closed as version 0.6.0, its graphical interface the browser workbench alone. The close measured the final
report again on its own copy: the tests pass on Linux and macOS, the screens load in every state, and a fresh install
takes about five seconds. The Windows test run has failed since 10 November; you ruled to release and carry it to the
next phase. The release notes gather the phase's packages and every change that breaks an older project or script,
with its remedy. The Copilot app's checks were not run and are carried. The moved packages and every open item wait
for the next phase's scope round.

**Your call.** Merge the close and tag the release. *Next:* the ship step for the phase, then the project's planning
round, which plans Phase 6 and the tool phases again.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **closing early** (§8.2.47; REV-272):
  WP5.01 to WP5.21 and WP5.27 merged (`v0.6.0-alpha.21`, `v0.6.0-alpha.27`).
  [WP5.28](phase-5/wp5.28-the-close.md), the close, is **delivered** on branch `ccr-7f42d119-nlqnbh`; its
  [end-of-phase report](phase-5/phase-5-workbench.md#end-of-phase-report) is written. **Phase 5 closes as `v0.6.0`**
  at the merge and the tag. The Windows leg is carried (§8.2.48 AX3; REV-277).
  **Next:** `/np-ship phase 5`, then `/np-plan project`, Phase 6's scope round. host: claude-code.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Two lanes at most** (S15). **Phase 5 is a
  browser workbench; Qt is removed** (S1 to S14; S17).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a
  VER-62 miss is reverted or re-pinned by ruling (G10, I4). **An open item is a `REV-nn` row** until resolved (H12).
- **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23). **The front end is NiceGUI; Mol*
  draws the molecule** (AF4). **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4).
- **Variables are keyed by resolved values; a study overrides any model value** (§8.2.31; AG12). **An output states
  its needs of a model** (AH1). **The store cleans the unused or all, never while a run holds it** (AN5, AN6).
- **Physics is a third model with its own suite; models declare exposed values** (§8.2.34). **Layers read a model's
  declaration, never its name** (VER-56). **A callback is not an input** (VER-44). **Text follows the tested
  program** (AM1, AM2). **Refusals are ASD-STE100** (WB-42).
- **Meso holds Density, Outline and Charge map** (AR8; AS1 to AS3). **A plot's axes are the user's** (AU1 to AU3).
  **Analysis is COMSOL's tree; Plotly draws every chart and map** (WB-54 to WB-63). **The words follow five rules**
  (WB-52). **Every open item names a package** (§8.2.46).
- **Phase 6 opens with its scope, a cleanup, then the foundations** (REV-272). **QR-10's trial waits for v1.0's
  release candidate; WP5.22 to WP5.26 are retired; QR-16's keyboard gaps ship noted; five Qt details are carried**
  (§8.2.47; REV-274). **The tool phases are ordered at Phase 6's scope round; v0.6.0 ships with the Windows leg
  carried** (§8.2.48 AX1, AX3).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8); **the Copilot host's checks**, carried to Phase 6's scope round (REV-166 to REV-168; AV6).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **Phase 6's provisional packages** (AV5; AW1), Z6's speed-up first revisited (REV-272); **the Windows leg** (REV-277; AX3);
  **QR-10's observer** (AW2).

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
