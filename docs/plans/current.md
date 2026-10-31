# Current work

Updated 31 October 2026 (WP58 planned; the last two packages of Phase 4 settled, §8.2.24).
Navigation only;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it: the author has run the testing sessions and ruled
what they found; both fixes are done, a readable command line and then a pore's shape set apart from
its mesh, with the Python interface rebuilt on a case and the session that runs it. Two packages are
left and they end the phase. The first is planned: the written guide brought level with the
program, every untrue statement in it corrected, a page on driving the program from Python and one
listing the notebooks. Then the close, which settles every finding, measures the report's numbers
again and names the release. Phase 5, a browser workbench, has its design study merged; nothing is
built until that release is out.

**Your call:** nothing waits on you. Two questions sit in the new plan for your awareness only,
each with a recommendation: whether the site should stop calling itself pre-alpha now, and how wide
the examples' prose revision should read.

## Position

One line per lane (§8.4.4).

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress**. WP35 to WP57 are delivered; WP57
  ([plan](wp57-idealised-pore-and-python-interface.md),
  [CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)) is merged at `8a3488c`.
  **`v0.5.0-alpha.23` is the author's to push**: `/np-ship wp 57` was refused on the tag ref (403,
  while branch pushes went through), as §8.4.1 allows; the commands are in that session's report.
  The sessions' findings are ruled (§8.2.21), and the phase's last two packages are planned
  (§8.2.24):
  **WP58**, documentation increment 4, tagged `v0.5.0-alpha.24`, then **WP59**, the close, tagged
  `v0.5.0` alone. [WP58's plan](wp58-documentation-increment-4.md) is in: prose and navigation
  only, no `src/` file and no number re-pinned, a currency sweep of six checks, a Python interface
  page and a notebooks page. `duplicates.py` passes on the merged `main`, both lanes in (§8.4.4).
  Next: `/np-implement wp 58`; the alpha.23 tag does not block it.
- **Phase 5** ([the workbench](phase-5-workbench.md)), `v0.6.0`, is **in progress** in the second
  lane: [WP5.01](wp5.01-workbench-design-study.md), the design study, is **merged**, untagged
  before `v0.5.0`; WP5.02, the spike, comes after it.

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
- **Phase 4 ends in WP58, the documentation increment, and WP59, the close; the notebooks are
  listed, not rendered; no migration page, the changelog carrying each break; the examples change in
  prose alone** (§8.2.24 Z1 to Z4).
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
| The last two packages | `wp58-documentation-increment-4.md`; §8.2.24; the Phase 4 plan's entries |
| The workbench | `phase-5-workbench.md`; §8.2.17; M3; F5 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
