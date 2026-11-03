# Current work

Updated 3 November 2026 (WP5.05 delivered). Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 4 is released, and the workbench's technology is chosen. The rest of Phase 5 is planned: library steps, one
package per part of the screen, the guided route, the old shell's removal and the guide. The first library step is
merged: the pore's shape is built from the protein as charged at the chosen pH. The second is merged too: a case can fix
a residue's protonation state, change its charge by a whole unit, or scale its atoms, recording what differs. The third
is delivered: a case names a molecular and a continuum model kept in files of their own, overrides any of their values and
reuses what they built. It waits for its review.

**Your call.** None open. The colleague who tries the workbench is
named by the close.

## Position

One line per lane (§8.4.4).

- Phases 1 to 4 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7), `v0.4.0` and `v0.5.0`.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress**: WP5.01 to WP5.04 are merged
  (`v0.6.0-alpha.4`). Library WP5.05 to WP5.07, shell WP5.08 to WP5.13, close WP5.14 (§8.2.31).
  **WP5.05** ([named models and study overrides](wp5.05-named-models-and-study-overrides.md))
  is delivered on its branch, not merged; next `/np-ship wp 5.05`. host: claude-code.

## Not to be re-decided

- **The rules of process** are §8.4: versions (§8.4.1), the loop (§8.4.2), the test scope (§8.4.3),
  the commands (§8.4.4).
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss
  is reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12; §8.4.6).
- **An idealised pore is geometry the case declares; stage 6 meshes it; a wall charge is a boundary
  condition** (§8.2.22 X1 to X4). **A `Case` is the case document built from public blocks; a
  `Session` runs it for every caller; one public object per job** (§8.2.23 Y1 to Y11).
- **Text output is a reading, `--json` the record** (W2). **A non-finite Newton trial residual aborts** (AC2).
- **The workbench keeps a desktop wrapper possible; the server's contract is ADR-004's NOTE** (§8.2.30 AF1).
  **The front end is NiceGUI; Mol* draws the molecule** (AF4).
- **One shell package per suite; variables may be expressions, units through `pint`, keyed by resolved values**
  (§8.2.31 AG1 to AG5). **Example 07 is re-pinned** (AG8). **A charge edit sits on the titratable group;
  a radius edit is a scale; a variant is never a deviation** (AG9 to AG11). **A study overrides any model value** (AG12).
- **Layers read a model's declaration, never its name** (VER-56). **A golden carries the stage-7 recipe** (E3).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's identifier, `nanopnp/case/v0.6` (G6).
- **A callback is not an input** (VER-44). **A generated mesh is read only through `deployed_mesh`.**
  **Stage 1's frame is fixed.**

## What is still somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs. **The Read the Docs project**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **The 200 ms redraw**, on the author's GPU, in WP5.11 (AF4; AG7).
- **Rulings on a residual cycle (H6) or WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.
- **REV-156**'s speed-up is Phase 6's (Z6); REV-121 is WP5.09's, REV-170 WP5.10's (AG1).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file it maps; `specification/history/index.md` |
| The phase's amendments | `phase-5-record.md` |
| The workflow | `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5 |
| WP5.05 | its plan; FR-39; WB-11 and WB-16 in the design document; §8.2.31 AG4, AG5, AG12, AG13; §8.2.18 T2; REV-62 |
| The workbench | `phase-5-workbench.md`; `docs/design/workbench.md`; `docs/design/spike/report.md`; §8.2.17, §8.2.28, §8.2.30, §8.2.31; M3; F5 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
