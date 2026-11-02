# Current work

Updated 2 November 2026 (WP60, the close, delivered; Phase 4 closes at its merge and the `v0.5.0` tag).
Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 4 tidied the program before others rely on it, and its last package is now written. Every
finding of the structure review and of the user-testing sessions is settled, every number of the
phase report was measured again on the final tree, and the instructions for the coding sessions
are plainer. The release is named: the author merges the pull request, and the closing step tags
it. Phase 5, the browser workbench, has its design study merged. Its next package is the spike
that picks the front-end framework; nothing of the workbench is built before the release.

**Settled:** the author ruled the plain-language pass also covers the steward's instructions and the Copilot
map, and accepted the two slow checks and the two documents over their word targets.

## Position

One line per lane (§8.4.4).

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **delivered**: WP35 to WP60, WP60 at its PR ([plan](wp60-phase-4-close.md); report in the phase plan).
  REV-170 is Phase 5's, REV-171 Phase 6's. The phase closes when the author merges; `v0.5.0` alone goes on the
  last commit. Next: `/np-ship phase 4`. host: claude-code.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress** in the second
  lane: [WP5.01](wp5.01-workbench-design-study.md), the design study, is **merged**, untagged before `v0.5.0`. After
  the release, `/np-plan wp 5.02` plans the spike. The
  first amendment (§8.2.28) orders, after WP5.02's spike, four library packages: WP5.03 protonation before the
  density, WP5.04 the mutator's library step, WP5.05 named models, WP5.06 the outputs registries. The shell
  packages wait for a second `/np-plan amend 5` after the framework ruling.

## Not to be re-decided

- **Reading the specification:** `SPECIFICATION.md` maps `specification/`; history on demand;
  `clause.py <ID>` for a clause; a ruling's table to a new history record, its rule to §8.4 (R2, R3).
- **The rules of process** (versions, the loop, the test scope, plans, agents and models, open
  items) are §8.4: one minor version per phase and `v0.5.0` alone at the close (§8.4.1); the commit
  hook, the push gate and Python 3.14 with a 3.11 floor (§8.4.2); tests only inside the scope
  (§8.4.3, §7.1); `/np-plan`, `/np-implement` and `/np-ship` with levels (§8.4.4).
- **Figures:** Matplotlib in `plot/`, below `pipeline`, importing no backend; figures declared in
  the stage registry; marimo notebooks, nightly. → §8.2.14 P2 to P6; FR-30.
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5 is a
  browser workbench, §8.2.17 S1 to S14; Qt stays gated until it** (M3). **Two lanes at most** (S15); **packages `WP5.01` on** (S16).
- **Phase 4's shape:** the `MOD-nn` rulings stand (§8.2.8); findings only from the author's sessions
  (G7). **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss
  is reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12; §8.4.6).
- **An idealised pore is geometry the case declares; stage 6 meshes it; a wall charge is a boundary
  condition** (§8.2.22 X1 to X4). **A `Case` is the case document built from public blocks; a
  `Session` runs it for every caller; one public object per job** (§8.2.23 Y1 to Y11).
- **Text output is a reading, `--json` the record; a remedy names what the run reads** (§8.2.21 W2, W5).
- **Phase 4 ends in WP58, the documentation increment, WP59, the review's fixes, and WP60, the close; the
  notebooks are listed, not rendered; no migration page, the changelog carrying each break; the examples change
  in prose alone** (§8.2.24 Z1 to Z4; §8.2.27 AC1). **A non-finite Newton trial residual aborts** (AC2). **The
  region interface waits for the shell, the review's costs for Phase 6's measurement** (AC3, AC4).
- **Layers read a model's declaration, never its name** (VER-56). **A refusal names its requirement
  and release.** **Only `poisson` adds a quadrature order for `r`** (E4; NUM-07 NOTE). **A golden
  carries the stage-7 recipe** (E3; VAL-03).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's
  identifier, `nanopnp/case/v0.5` (G6), and is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`.** **Stage 1's frame is fixed.**

## What is still somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (§8.2.4 D6); E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **Phase 5's comments, design-round answers, framework ruling, colleague** (S8, S13, S21).
- **The rulings on any residual cycle (H6) and any WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.
- **REV-121**, stage 1's axis for a single-chain or mixed-chain pore, is Phase 5's, with structure
  preparation; **REV-156**'s speed-up is Phase 6's, the assembly first (§8.2.24 Z5, Z6).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The specification | `SPECIFICATION.md`, then the file it maps; `specification/history/index.md` |
| The documents' record | `wp52-specification-and-plans-split.md`; `phase-4-record.md` for the phase plan's amendments |
| The workflow | `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5 |
| The notebooks and the protocol | `wp54-notebooks-and-figures-revised.md`, `wp55-user-testing-protocol.md`; §8.2.20; FR-30, FR-37 |
| The fixes | `wp56-command-line-read-by-a-person.md`, `wp57-idealised-pore-and-python-interface.md`; `docs/user-testing/findings.md`; §8.2.21, §8.2.22 |
| The close | `wp60-phase-4-close.md`; the Phase 4 plan's end-of-phase report; §8.2.27 AC6; §8.2.29 AE5 |
| The workbench | `phase-5-workbench.md`; §8.2.17, §8.2.28; M3; F5 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
