# Current work

Updated 29 October 2026 (§8.2.20). Navigation only; `SPECIFICATION.md` governs; an
unmerged branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it: the revised notebooks are merged, and the
protocol for the author's testing sessions is delivered on its branch. Phase 5, a workbench in the browser, has its
design study merged; nothing is built until Phase 4's release.

**Your call:** should Phase 4's estimate grow to five to seven weeks? *Recommendation:* yes.

## Position

One line per lane (§8.4.4).

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 to §8.2.16). WP35 to WP54 are merged, tagged to `v0.5.0-alpha.19`;
  `v0.5.0-alpha.20`, WP54's, is the author's step. [WP55](wp55-user-testing-protocol.md), the
  protocol, is **delivered** on its branch, ready for `/np-ship wp 55`; then the author's sessions,
  the fixes from WP56, the documentation increment and the close.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress** in the second
  lane. [WP5.01](wp5.01-workbench-design-study.md), the design study, is **merged**, untagged
  before `v0.5.0`. WP5.02, the spike, after `v0.5.0`.

## Not to be re-decided

- **Reading the specification:** `SPECIFICATION.md` maps `specification/`; history on demand;
  `clause.py <ID>` for a clause; a ruling's table to a new history record, its rule to §8.4 (R2, R3).
- **The rules of process** (versions, the loop, the test scope, plans, agents and models, open
  items) are §8.4: one minor version per phase and `v0.5.0` alone at the close (§8.4.1); the commit
  hook, the push gate and Python 3.14 with a 3.11 floor (§8.4.2); tests only inside the scope
  (§8.4.3, §7.1); `/np-plan`, `/np-implement` and `/np-ship` with levels (§8.4.4). WP54's scope is
  §8.2.20 V1 to V17.
- **Figures:** Matplotlib in `plot/`, below `pipeline`, importing no backend; figures declared in
  the stage registry; marimo notebooks, nightly. → §8.2.14 P2 to P6; FR-30.
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **Phase 4's shape:** refactors before the protocol (G2); findings only from the author's sessions
  (G7); the VER-62 golden (G10). The `MOD-nn` rulings stand (§8.2.8).
- **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss is
  reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12; §8.4.6).
- **Layers read a model's declaration, never its name** (VER-56). **A refusal names its requirement
  and release** (VER-67). **Only `poisson` adds a quadrature order for `r`** (E4; NUM-07 NOTE).
  **A golden carries the stage-7 recipe** (E3; VAL-03).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's
  identifier, `nanopnp/case/v0.5` (G6), and is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`.** **Stage 1's frame is fixed.**

## What is still somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (§8.2.4 D6); E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **Phase 5's comments, design-round answers, framework ruling, colleague** (S8, S13, S21).
- **The install route of the sessions** (WP55's *Your call*). **The user-testing sessions, and
  the rulings on each `UT-nn`, `MOD-11`, any residual cycle (H6) and any WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file it maps; `specification/history/index.md` |
| The documents' record | `wp52-specification-and-plans-split.md`; `phase-4-record.md` for the phase plan's amendments |
| The workflow | `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5 |
| The notebooks revised | `wp54-notebooks-and-figures-revised.md`; §8.2.20; `wp51-plotting-and-notebooks.md`; FR-30, FR-37 |
| The protocol | `wp55-user-testing-protocol.md`; §8.2.6 F3, §8.2.7 G7, §8.2.8 H2, §8.2.13 N4; VER-46; `src/nanopnp/validation/examples.py` |
| The workbench | `phase-5-workbench.md`; §8.2.17; M3; F5 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
