# Current work

Updated 13 November 2026 (WP5.18 planned and reviewed). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 4 is released, and Phase 5 is merged through the Continuum suite. The Physics suite is planned to your two
rulings: each tool shows the physics model inside a study you pick, and picking another set of equations sets its
switches, with a note and Undo. Two suites, the route and the close follow, about 40 sessions.

**Your call.** Approve the Physics suite's reviewed plan? Recommendation: yes; its two choices are yours as
ruled.

## Position

- Phases 1 to 4 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`.
- **Phase 5** ([the workbench](phase-5/phase-5-workbench.md)), `v0.6.0`, **in progress**: WP5.01 to WP5.17 merged
  (`v0.6.0-alpha.17`).
  **WP5.18** [planned](phase-5/wp5.18-the-physics-suite.md) and reviewed (CODE_REVIEW_057) on
  `claude/trusting-bell-hhyxbe` (§8.2.41; REV-249). Next, `/np-implement wp 5.18`. host: claude-code.

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
  **A user's theme sets its contrast** (§8.2.33 AI1). **Threads per solve alone
  may move a result; the store cleans the unused or all, never while a run holds it** (§8.2.38 AN1, AN5, AN6).
- **Physics is a third model with its own suite; models declare exposed values; Quasar's components build the
  frame; suites are prototyped on 2WCD first; `impeccable` serves `np-gui`** (§8.2.34 AJ1 to AJ10).
- **Layers read a model's declaration, never its name** (VER-56). **A golden carries the stage-7 recipe** (E3).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4), a move taking `nanopnp/case/v0.6` (G6).
- **A callback is not an input** (VER-44). **A generated mesh is read only through `deployed_mesh`.**
- **Plans are archived by phase** (§8.2.36 AL5, AL22 to AL26). **Text follows the tested program; its gaps, REV-223 to 225, are Phase 6's** (§8.2.37 AM1, AM2).
- **A pore's axis is found; a variant follows its parent** (§8.2.39). **An edited outline keeps its charge; a
  continuum model builds alone; mesh parts are typed** (§8.2.40). **A physics model is shown in a picked study; a
  change of model sets its switches** (§8.2.41).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw** on the author's GPU, WP5.19 (AF4; AG7; AJ10); **verdicts on each suite's prototype** (AJ8).
- **Rulings on a cycle (H6) or drift (I4)**; **Tier 3's PQRs**.
- **REV-156**'s speed-up is Phase 6's (Z6); the compute settings WP5.19's and a cleaned run's rebuild WP5.20's (AN4,
  AN5).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-5-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; §8.2.17, §8.2.30,
  §8.2.31, §8.2.34; `docs/design/reviews/`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
