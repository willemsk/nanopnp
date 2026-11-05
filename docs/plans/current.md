# Current work

Updated 5 November 2026 (WP5.08 delivered). Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 4 is released, and the workbench's technology is chosen. Phase 5's library steps are merged: the pore follows the
protein's charge state; a residue's charge or size can change; a case names and reuses its models; and a case defines
named values with units, and a sweep warns of what each will rebuild. The window now has its frame and its document: a
project is a plain folder that exports as readable files, and the window has menus, a command palette, shortcuts you can
change, the changed and problems lists, and your own colour themes. The suites' tools follow.

**Your call.** Your verdicts on the frame (`docs/design/reviews/2026-11-05-frame.md`) leave four questions for a
design round before WP5.09's plan: the settings' layout and contents (REV-212); whether the suites that build models
should stand apart from those that use them (REV-213); the changed list's density and the project name's place
(REV-214); and the charge screen (REV-215). The colleague who tries the workbench is named by the close.

## Position

- Phases 1 to 4 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7), `v0.4.0` and `v0.5.0`.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress**: WP5.01 to WP5.07 are merged
  (`v0.6.0-alpha.7`). Shell WP5.08 to WP5.13, close WP5.14 (§8.2.31). **WP5.08** ([the frame and the project folder](wp5.08-the-frame-and-the-project-folder.md)) is
  delivered, its PR open; next `/np-ship wp 5.08`, then WP5.09. host: claude-code.

## Not to be re-decided

- **The rules of process** are §8.4. **Cost fixes follow measurement** (§8.2.12 M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss
  is reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12; §8.4.6).
- **An idealised pore is geometry the case declares; a wall charge is a boundary condition** (§8.2.22 X1 to X4).
  **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23 Y1 to Y11).
- **Text output is a reading, `--json` the record** (W2). **A non-finite Newton trial residual aborts** (AC2).
- **A desktop wrapper stays possible** (§8.2.30 AF1). **The front end is NiceGUI; Mol* draws the molecule** (AF4).
- **One shell package per suite; variables may be expressions, units through `pint`, keyed by resolved values**
  (§8.2.31 AG1 to AG5). **Example 07 is re-pinned** (AG8). **A charge edit sits on the titratable group;
  a radius edit is a scale; a variant is never a deviation** (AG9 to AG11). **A study overrides any model value** (AG12).
  **An output states what it needs of a model; a model provides every output whose need it meets** (§8.2.32 AH1).
  **The settings select and modify colour themes; a user's theme sets its own contrast** (§8.2.33 AI1).
- **Layers read a model's declaration, never its name** (VER-56). **A golden carries the stage-7 recipe** (E3).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's identifier, `nanopnp/case/v0.6` (G6).
- **A callback is not an input** (VER-44). **A generated mesh is read only through `deployed_mesh`.**

## What is still somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **The 200 ms redraw**, on the author's GPU, in WP5.11 (AF4; AG7).
- **Rulings on a residual cycle (H6) or drift (I4)**; **the archived PQRs** for Tier 3.
- **REV-156**'s speed-up is Phase 6's (Z6); REV-121 is WP5.09's, REV-170 WP5.10's (AG1).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file it maps; `specification/history/index.md` |
| The phase's amendments | `phase-5-record.md` |
| The workflow | `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5 |
| WP5.08 | its plan; FR-31, FR-32, FR-34, FR-35, QR-16; §5.3.2, §5.5; VER-64, VER-78; REV-32, REV-52; MOD-13; §8.2.33 AI1 |
| The workbench | `docs/design/workbench.md`; `docs/design/spike/report.md`; §8.2.17, §8.2.28, §8.2.30, §8.2.31 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
