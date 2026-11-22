# Code review 071: PR 202, WP5.28, the close of Phase 5

2026-11-22 · branch `ccr-7f42d119-nlqnbh` at `288cbd3` on `main` · scope: the pull request's 19 files, read from
`gh pr diff 202`; the checkout was the pull request's head, so each file was read in place · level: xhigh, with
`--fix` · status: completed.

Static review of a text package: no `gate.sh`, benchmark or `--nightly` run. Read-only checks were run: the review
register's status counts and the hand-over table against each `accepted` and `deferred` row; the `open:` lines of
`holds-now.yaml`; the capability record's counts; the Qt search; `--collect-only` counts by marker; the screen
registry's length; `decisions.py --check`, `index_records.py`, `links.py` and VER-79's three tests; the `tier12`
action's step order; and `v0.5.0`'s sources against each break `[0.6.0]` lists and each `alpha` entry it gathers.
After the fixes, `decisions.py` was re-run, and `decisions.py --check`, `links.py` and VER-79's tests pass;
`holds-now.yaml` still holds 23 `open:` lines and `current.md` 687 words.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `CHANGELOG.md` `[0.6.0]`, its summary; the Phase 5 plan's report, *Number stability* | The release notes say the installed `nanopnp gui --selftest` checks each payload "on three platforms", and the report gives "each leg's" self-test. The self-test is the `tier12` action's step after the tests; the Windows leg failed a test and was cancelled, so the step never ran there, in run 837 or in any run since it was added on 21 November | Fixed: both name Linux and macOS, and the report says why Windows never reached the step |
| 2 | Important | `CHANGELOG.md` `[0.6.0]`, *Breaks and their migration* | `ModelDeclaration` is in `nanopnp.PUBLIC`, and `alpha.6` removed its `quantities` field. A model registered with `quantities=` under `v0.5.0` fails to construct under `v0.6.0`; the list names only internal paths for `alpha.6` | Fixed: a *Python interface* group gives the removal and its migration |
| 3 | Important | `CHANGELOG.md` `[0.6.0]`, *Breaks and their migration* | Two changes to what `v0.5.0` ran are missing. A structure case under `charge.forcefield: PEOEPB` or `SWANSON` is refused under the new default `protonated` (`alpha.3`). A supplied outline's ion-exclusion shell takes the outline's recorded spacing held within 0.025 to 0.05 nm, where `v0.5.0` took 0.05 nm, and `RegionStage._key` reads it, so a fine outline with the shell on builds a new region (`alpha.19`) | Fixed: one bullet each, under *The case file* and *The numbers and the stored results* |
| 4 | Important | `holds-now.yaml`, T4, AI9, AI10, AI12; `docs/project/decisions.md` | The four read `spent`, so the register lists them `spent`, but §5.5 cites T4 for the outputs and steric registries, and §5.3.5's NOTE cites AI9 to AI14 (the design document's *The project folder* cites AI9 and AI10). The plan's item 1 gave `AI9: spent` as an example | Fixed: T4 reads §5.5, AI9 and AI10 §5.3.5's NOTE and the design document's section, AI12 §5.3.5's NOTE; `decisions.py` re-run. Against the plan's example: for the author |
| 5 | Nit | `CHANGELOG.md` `[0.6.0]`, *Changed*; the Phase 5 plan's WP5.28 entry and *The registers* | "T3, AC3 and AW1 keep what waits", but AC3 now reads `REV-170; placed by AD4`, with nothing open; the report's own count lists only T3 and AW1. The changelog bullet also cites §8.2.48 AX2, the tree's reopened points, for the ruling index | Fixed: AC3 keeps its clause alone; AX2 is cited for no `open` row and AV5 for the owners |
| 6 | Nit | `CHANGELOG.md` `[0.6.0]`, its summary | "Each that waits names its owner in Phase 6". REV-276 waits for the radius set's next change, REV-67, REV-149, REV-238 and REV-244 for a tool's phase, and REV-183 for FR-43's package | Fixed: "names its owner" |
| 7 | Nit | `CHANGELOG.md` `[0.6.0]`, its summary | The Windows leg "failed one test and then met its 40-minute limit on every run since 10 November". A nightly leg's limit is 240 minutes, and only run 837's failure was seen | Fixed: the leg has not finished on any run since then; run 837 failed one test and met its 40-minute limit |
| 8 | Nit | `review-items.md`, REV-277 | "With `-q` and the job cancelled": the `tier12` action runs `pytest -rs -n auto --dist loadfile`, and `addopts` holds no `-q` | Fixed: "With the job cancelled" |
| 9 | Nit | The Phase 5 plan's report, *The suite* | "114 deselected as `nightly` or `slow`". 20 of them are Tier 3 tests, which `addopts`' tier filter leaves out; 94 are `nightly` or `slow` | Fixed: the two counts |
| 10 | Nit | `CHANGELOG.md` `[0.6.0]`, the `gui` extra | Matplotlib joined the `gui` extra in `alpha.21`, which the bullet's attribution leaves out | Fixed: `alpha.21` added |
| 11 | Nit | The Phase 5 plan's In brief | "Two packages remain", under a status line that reads delivered | Fixed: its last two packages are delivered |
| 12 | Nit | `current.md`'s In brief | "Phase 5 is closed as version 0.6.0", where the plans say it closes at the merge and the tag | Fixed: it closes at the merge and the tag; 687 words, In brief 145 |
| 13 | Nit | `current.md`, *Not to be re-decided* | The rewrite drops entries no ruling superseded, several binding Phase 6's packages: WB-53's "a true 3D view is the tree's", WB-42's "red blocks, blue informs", AW7's typed vertex, AI1's theme contrast, §8.2.40, §8.2.41, AT1 to AT4 and WB-49. `np-plan/phase.md` replaces the entries the rulings supersede; each still has its row in the decisions register | Skipped: the 700-word cap and which entries Phase 6's scope round needs are the author's |

Checked and found true: 277 rows, `fixed` 207, `accepted` 39, `deferred` 17, `declined` 7, `wontfix` 4, `post-1.0` 3,
none `open`; the hand-over table names each of the 56 `accepted` and `deferred` rows under its ruling's package; 23
`open:` lines (the 19, T3, AW1, AX3 and the header's comment); 52 changed entries, the 49 and T3, AC3 and AW1; 41
capability rows, 31 present, one as ruled, nine carried; the Qt search's two files; 32 screens, 149 tests in
`test_gui_screens.py`; 2,068 tests, 1,954 by default, Tier 1 1,758, Tier 2 220; the 23 packages and the retired
numbers; the `alpha.3` to `alpha.21` internal moves against `v0.5.0`'s sources; `nanopnp.PUBLIC` gains `Project`
alone; the README's anchor; `CITATION.cff` against `release.yml`'s check; the 8.2.48 title in the index and the
navigation; §8.1's Phase 5 gate.

Not checked: run 837's timings, drifts and the redraw and install measurements, which need the run's logs, a browser
or a build.
