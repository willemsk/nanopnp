# Current work

Updated 22 October 2026 (§8.2.16). Navigation only; `SPECIFICATION.md` governs; an
unmerged branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it. The specification and this phase's plan are now
split into what holds today, read by default, and their history, read only when needed. The working
instructions rebuilt as three commands with levels are planned. Then come the notebooks and figures
revised from the author's notes, and the testing sessions.

**Your call:** should the phase estimate grow to five to seven weeks? *Recommendation:* yes.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 to §8.2.16). WP35 to WP52 are merged; tags to `v0.5.0-alpha.18` are the
  author's step.
- [WP53](wp53-workflow-commands.md), the workflow, is **planned**; its tag is `v0.5.0-alpha.19`.
  Next: **`/wp-implement`**, then `/wp-ship`: the old commands, until WP53 merges. Then WP54, the
  notebooks revised, the first package run with `/np-plan`, `/np-implement` and `/np-ship`; then [WP55](wp55-user-testing-protocol.md), the protocol, **planned**; then the
  author's sessions, and fixes from WP56.

## Not to be re-decided

- **Reading the specification:** `SPECIFICATION.md` is the entry point over `specification/`; the
  current files by default, `specification/history/` on demand, `clause.py <ID>` for a clause. → R2, R3.
  Until WP53 merges, an amendment writes its ruling table to a new `specification/history/` file,
  listed in `history/index.md`, and its standing rules to §8.4, whatever the old skills say.
- **The rules of process** (versions, the loop, the test scope, plans, agents and models, open
  items) are §8.4: one minor version per phase and `v0.5.0` alone at the close (§8.4.1); the commit
  hook, the push gate and Python 3.14 with a 3.11 floor (§8.4.2); tests only inside the scope
  (§8.4.3, §7.1). `/np-plan`, `/np-implement`, `/np-ship` with levels and no aliases are WP53's,
  and WP54's scope is open (§8.2.16 R5, R12, R8, all open).
- **Figures:** Matplotlib in `plot/`, below `pipeline`, importing no backend; figures declared in
  the stage registry; marimo notebooks, nightly. → §8.2.14 P2 to P6; FR-30.
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5
  builds a browser shell; the Qt shell stays gated until then** (M3).
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
- **The notes on the notebooks and figures, for WP54's plan.** **The user-testing sessions, and
  the rulings on each `UT-nn`, `MOD-11`, any residual cycle (H6) and any WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file its map names; `specification/history/index.md` for where each ruling holds now |
| The documents' record | `wp52-specification-and-plans-split.md`; `phase-4-record.md` for the phase plan's amendments |
| The workflow | `wp53-workflow-commands.md`; §8.2.16 R5 to R7, R12; §8.4.4, §8.4.5 |
| The notebooks revised | The Phase 4 plan's WP54; `wp51-plotting-and-notebooks.md`; §8.2.14; FR-30 |
| The protocol | `wp55-user-testing-protocol.md`; §8.2.7 G7, §8.2.8 H2, §8.2.13 N4; VER-46 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
