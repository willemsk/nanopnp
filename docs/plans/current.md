# Current work

Updated 2 November 2026 (Phase 4 closed as `v0.5.0`; WP5.02 planned). Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 4 is released. Phase 5 builds the browser workbench, and its next step is planned: one hard
screen, a residue picked on the molecule lighting up its charge on the pore map and back, is built
two ways, all in Python and as a web application, and both are measured, including whether each
runs inside a desktop window, so a desktop app stays possible later. The author then picks the
technology, and the chosen one gets its groundwork.

**Settled:** the author ruled the two candidates, that the desktop option is kept open and checked,
and that both trial builds leave the code once the choice is made.

**Your call.** Which technology the workbench uses, once the report's numbers are in.
*Recommendation:* the Python-first one if it is fast enough and wraps in a desktop window.

## Position

One line per lane (§8.4.4).

- Phases 1 to 4 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7), `v0.4.0` and `v0.5.0`.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress**:
  [WP5.01](wp5.01-workbench-design-study.md), the design study, is merged.
  [WP5.02](wp5.02-framework-spike.md), the framework spike, is **planned** (§8.2.30 AF1 to AF3); next
  `/np-implement wp 5.02`, tag `v0.6.0-alpha.2`. After it, WP5.03 to WP5.06, the library packages
  (§8.2.28), and a second `/np-plan amend 5` for the shell packages. host: claude-code.

## Not to be re-decided

- **Reading the specification:** `SPECIFICATION.md` maps it; `clause.py <ID>` prints a clause (R2, R3).
- **The rules of process** are §8.4: versions (§8.4.1), the loop (§8.4.2), the test scope (§8.4.3),
  the commands (§8.4.4).
- **Figures:** Matplotlib in `plot/`, importing no backend; marimo notebooks, nightly (§8.2.14 P2 to P6).
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **The `MOD-nn` rulings stand** (§8.2.8). **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss
  is reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12; §8.4.6).
- **An idealised pore is geometry the case declares; stage 6 meshes it; a wall charge is a boundary
  condition** (§8.2.22 X1 to X4). **A `Case` is the case document built from public blocks; a
  `Session` runs it for every caller; one public object per job** (§8.2.23 Y1 to Y11).
- **Text output is a reading, `--json` the record** (§8.2.21 W2). **A non-finite Newton trial residual aborts** (AC2).
- **The workbench keeps a desktop wrapper possible; the server's contract is ADR-004's NOTE** (§8.2.30 AF1).
- **Layers read a model's declaration, never its name** (VER-56). **Only `poisson` adds a quadrature
  order for `r`** (E4). **A golden carries the stage-7 recipe** (E3).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's
  identifier, `nanopnp/case/v0.5` (G6), and is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`.** **Stage 1's frame is fixed.**

## What is still somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (§8.2.4 D6); E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **Phase 5's framework ruling, at WP5.02's item 5, and its colleague** (S8, S13).
- **The rulings on any residual cycle (H6) and any WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.
- **REV-156**'s speed-up is Phase 6's (Z6); REV-121 and REV-170 are placed in the Phase 5 plan.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file it maps; `specification/history/index.md` |
| The phase's amendments | `phase-5-record.md` |
| The workflow | `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5 |
| The workbench | `phase-5-workbench.md`; `wp5.02-framework-spike.md`; `docs/design/workbench.md`; §8.2.17, §8.2.28, §8.2.30; M3; F5 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
