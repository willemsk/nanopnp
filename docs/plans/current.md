# Current work

Updated 10 November 2026 (WP5.12 delivered). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 4 is released. Phase 5's library steps, the physics model, the frame and two packages on the written
knowledge are merged. The third, correcting the knowledge base and the guide, is delivered and waits for
its review. Then the tidy-ups and the screens: about 70 sessions and 60 to 120 agent hours remain.

**Your call.** Review the third package's PR with `/np-ship wp 5.12`; adopt two measuring tools or not (the
trial recommends neither).

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0` (D7), `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.11 merged
  (tags `.10` and `.11` unpushed). Next WP5.13 and WP5.14 the clean-ups, then the frame,
  the suites, the route and the close, WP5.15 to WP5.22 (§8.2.36).
  **WP5.12** [delivered](phase-5/wp5.12-the-knowledge-base-and-the-guide.md): 163 audit findings fixed, the six
  source findings answered (REV-227), REV-226 fixed. Next `/np-ship wp 5.12`. host: claude-code.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a VER-62 miss
  is reverted or re-pinned by ruling (G10, I4).
- **An open item is a `REV-nn` row** until resolved (H12).
- **An idealised pore is geometry the case declares; a wall charge is a boundary condition** (§8.2.22 X1 to X4).
  **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23 Y1 to Y11).
- **Text output is a reading, `--json` the record** (W2). **A non-finite Newton trial residual aborts** (AC2).
- **A desktop wrapper stays possible** (§8.2.30 AF1). **The front end is NiceGUI; Mol* draws the molecule** (AF4).
- **One shell package per suite; variables may be expressions, units through `pint`, keyed by resolved values**
  (§8.2.31 AG1 to AG5). **Example 07 is re-pinned** (AG8). **A charge edit sits on the titratable group;
  a radius edit is a scale; a variant is never a deviation** (AG9 to AG11). **A study overrides any model value** (AG12).
  **An output states its needs of a model; a model provides every output whose needs it meets** (§8.2.32 AH1).
  **Settings select and modify colour themes; a user's theme sets its contrast** (§8.2.33 AI1).
- **Physics is a third model with its own suite; models declare exposed values; Quasar's components build the
  frame; suites are prototyped on 2WCD first; `impeccable` serves `np-gui`** (§8.2.34 AJ1 to AJ10).
- **Layers read a model's declaration, never its name** (VER-56). **A golden carries the stage-7 recipe** (E3).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's identifier, `nanopnp/case/v0.6` (G6).
- **A callback is not an input** (VER-44). **A generated mesh is read only through `deployed_mesh`.**
- **Written knowledge, then clean-ups, then the frame; packages renumbered; plans archived by phase** (§8.2.36 AL5,
  AL22 to AL26). **Text follows the tested program; its gaps, REV-223 to 225, are Phase 6's** (§8.2.37 AM1, AM2).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw** on the author's GPU, WP5.19 (AF4; AG7; AJ10).
- **Rulings on a residual cycle (H6) or drift (I4)**; **Tier 3's archived PQRs**.
- **REV-156**'s speed-up is Phase 6's (Z6); REV-121 and REV-218 WP5.16's, REV-170 WP5.17's (AG1; AJ10; AL22).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-5-record.md`.
- **The follow-ups:** CODE_REVIEW_039 with `findings.md`; CODE_REVIEW_036's designs and corrections; §8.2.36.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; `docs/design/spike/report.md`; §8.2.17, §8.2.28, §8.2.30,
  §8.2.31, §8.2.34; `docs/design/reviews/2026-11-05-frame.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
