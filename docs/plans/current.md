# Current work

Updated 10 November 2026 (WP5.15 delivered). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 4 is released. Phase 5's library steps, the first frame, the written knowledge and both tidy-ups are merged.
The frame's rebuild is delivered for review: Quasar's components, five suites, the settings page and two store
clean-up buttons. Then the five suites, the guided route and the close: about 60 sessions and 55 to 110 agent hours remain.

**Your call.** Run `/np-ship wp 5.15`. Adopt two measuring tools or not (the trial recommends neither).

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0` (D7), `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.14 merged
  (`v0.6.0-alpha.14`). Then the shell, WP5.15 to WP5.22 (§8.2.36).
  **WP5.15** [delivered](phase-5/wp5.15-the-frame-on-quasars-components.md) on `ccr-4b90fcd6-fjrv03`, its PR
  open; tag `v0.6.0-alpha.15` once merged. Next, `/np-ship wp 5.15`. host: claude-code.

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
  **Settings select and modify colour themes; a user's theme sets its contrast** (§8.2.33 AI1). **Threads per solve alone
  may move a result; the store cleans the unused or all, never while a run holds it** (§8.2.38 AN1, AN5, AN6).
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
- **REV-156**'s speed-up is Phase 6's (Z6); REV-121 and REV-218 WP5.16's, REV-170 WP5.17's (AG1; AJ10; AL22); the
  compute settings WP5.19's and a cleaned run's rebuild WP5.20's (AN4, AN5).

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
