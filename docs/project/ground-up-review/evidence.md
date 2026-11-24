# The evidence

The program measured where it cost, for [the ground-up review](../ground-up-review.md). Each number stands under the
command that printed it, run on 24 November 2026 in the repository's root on the tree at `e938930`, whose `src/`,
`tests/` and `data/` are those of `v0.7.0-alpha.3`. No script is committed. The container has four CPUs and 15 GB; the
six survey agents of [today's alternatives](technologies.md) fetched pages while the two cases ran, so a run time
here is an upper bound. A figure that an earlier record measured is cited from it, not measured again.

## Size

`for d in src/nanopnp/*/; do find "$d" -name '*.py' | xargs cat | wc -l; done`, with the files counted by
`find "$d" -name '*.py' | wc -l`:

| Subpackage | Files | Lines | | Subpackage | Files | Lines |
|---|---|---|---|---|---|---|
| `gui` | 43 | 21,422 | | `cli` | 11 | 2,998 |
| `validation` | 18 | 8,560 | | `structure` | 8 | 2,736 |
| `io` | 13 | 5,910 | | `plot` | 4 | 2,520 |
| `charge` | 9 | 5,878 | | `solve` | 4 | 1,962 |
| `physics` | 12 | 4,278 | | `sweep` | 6 | 1,598 |
| `api` | 6 | 3,740 | | `density` | 6 | 1,568 |
| `mesh` | 12 | 3,426 | | `core` | 9 | 1,563 |
| `post` | 9 | 3,334 | | `materials` | 7 | 1,358 |
| `pipeline` | 5 | 3,199 | | `numerics` | 6 | 1,272 |
| `geometry` | 10 | 3,085 | | `symmetry` | 4 | 445 |

`find src/nanopnp -name '*.py' | xargs cat | wc -l` prints 80,973 lines in 204 files; the top level holds 121 of them.
The shells (`gui`, `cli`) hold 24,420 lines, 30 %; the checks of `validation` 8,560, 11 %; what solves the model
(`physics`, `numerics`, `solve`, `materials`) 8,870, 11 %.

`find src/nanopnp -name '*.py' | xargs wc -l | sort -rn`: 18 files hold more than 1,000 lines. The largest are
`gui/web/tools.py` 2,299, `physics/models.py` 2,076, `api/project.py` 1,884, `validation/modularity.py` 1,682,
`plot/data.py` 1,508, `charge/protonation.py` 1,456, `validation/apbs.py` 1,454 and `pipeline/run.py` 1,438.

`find src/nanopnp \( -name '*.js' -o -name '*.css' \) | xargs wc -lc`: 15,296 lines and 6.6 MB of JavaScript and CSS.
Of these, 11,802 lines and 6.5 MB are bundles shipped unmodified (Mol\*, 5.3 MB; NGSolve's `webgui`, 0.8 MB; KaTeX;
uPlot). The workbench's own front-end code is 1,700 lines of JavaScript in five files (`plane.js` 950, `chart.js` 363,
`bridge.js` 162, `frame.js` 146, `palette.js` 79) and 1,794 lines of CSS in two. The plan's grounding counted the
bundles as the program's own; it is corrected.

`find tests/tier<n> -name 'test_*.py' | wc -l` and `find tests/tier<n> -name '*.py' | xargs cat | wc -l`:

| Tier | Test files | Lines |
|---|---|---|
| 1 | 115 | 32,563 |
| 2 | 60 | 12,025 |
| 3 | 8 | 1,544 |
| 4 | 0 | 14 |

`find tests -name '*.py' | xargs cat | wc -l` prints 46,960 lines: 0.58 lines of test for each line of the package.

## What a package touched

The clone was shallow; `git fetch --unshallow origin` and `git fetch --tags origin` gave it the history, 1,391
commits on `main` since 19 August 2026. A package is the range between two tags in the order of `git rev-list --count
<tag>`. `v0.6.0-alpha.1` does not exist (WP5.01 merged before Phase 4's release and took no tag, §2.7), so the first
range runs from `v0.5.0`; `alpha.13` and `alpha.14` share a commit. For each range,
`git rev-list --count <prev>..<tag>`, `git diff --name-only <prev> <tag> -- src | wc -l`, the third path component of
those names sorted and counted, `git diff --shortstat <prev> <tag> -- src`, and `git diff --name-only <prev> <tag> --
tests | wc -l`:

| Tag | Commits | Files under `src/` | Subpackages | Lines added, removed | Test files |
|---|---|---|---|---|---|
| `v0.6.0-alpha.2` | 17 | 15 | 4 | 9,546, 4 | 3 |
| `v0.6.0-alpha.3` | 12 | 17 | 8 | 519, 260 | 66 |
| `v0.6.0-alpha.4` | 11 | 16 | 10 | 839, 37 | 4 |
| `v0.6.0-alpha.5` | 14 | 21 | 11 | 955, 122 | 5 |
| `v0.6.0-alpha.6` | 12 | 20 | 7 | 499, 197 | 8 |
| `v0.6.0-alpha.7` | 14 | 17 | 9 | 1,515, 61 | 4 |
| `v0.6.0-alpha.8` | 25 | 36 | 7 | 4,786, 1,726 | 5 |
| `v0.6.0-alpha.9` | 13 | 11 | 5 | 296, 79 | 5 |
| `v0.6.0-alpha.10` | 48 | 16 | 11 | 25, 25 | 1 |
| `v0.6.0-alpha.11` | 37 | 0 | 0 | 0, 0 | 0 |
| `v0.6.0-alpha.12` | 22 | 7 | 4 | 22, 20 | 1 |
| `v0.6.0-alpha.13` | 11 | 11 | 5 | 241, 258 | 3 |
| `v0.6.0-alpha.15` | 33 | 29 | 7 | 3,533, 974 | 8 |
| `v0.6.0-alpha.16` | 23 | 40 | 10 | 4,949, 377 | 9 |
| `v0.6.0-alpha.17` | 21 | 41 | 11 | 4,735, 978 | 45 |
| `v0.6.0-alpha.18` | 21 | 61 | 11 | 4,439, 692 | 18 |
| `v0.6.0-alpha.19` | 24 | 42 | 10 | 4,577, 862 | 10 |
| `v0.6.0-alpha.20` | 23 | 25 | 5 | 3,068, 1,050 | 4 |
| `v0.6.0-alpha.21` | 27 | 41 | 9 | 5,144, 654 | 6 |
| `v0.6.0-alpha.27` | 30 | 30 | 4 | 626, 4,203 | 7 |
| `v0.6.0` | 10 | 0 | 0 | 0, 0 | 0 |
| `v0.7.0-alpha.1` | 17 | 2 | 2 | 59, 5 | 6 |
| `v0.7.0-alpha.2` | 14 | 0 | 0 | 0, 0 | 1 |
| `v0.7.0-alpha.3` | 14 | 0 | 0 | 0, 0 | 0 |

Twenty of the 24 ranges changed `src/`. The count of subpackages in each, sorted: 2, 4, 4, 4, 5, 5, 5, 7, 7, 7, 8, 9,
9, 10, 10, 10, 11, 11, 11, 11. The median is between seven and eight of the 19 subpackages that changed at all.

The same names, one line for each package and subpackage, `sort -u`, then counted by subpackage. Of the 20 packages:

| Subpackage | Packages | | Subpackage | Packages | | Subpackage | Packages |
|---|---|---|---|---|---|---|---|
| `io` | 18 | | `core` | 7 | | `physics` | 5 |
| `pipeline` | 15 | | `solve` | 6 | | `sweep` | 4 |
| `gui` | 15 | | `plot` | 6 | | `geometry` | 4 |
| `cli` | 15 | | `density` | 6 | | `mesh` | 3 |
| `api` | 13 | | `structure` | 5 | | `numerics` | 2 |
| `validation` | 11 | | `post` | 5 | | `materials` | 2 |
| `charge` | 8 | | | | | `symmetry` | 0 |

And counted by file, the files most packages changed:

| File | Packages | Lines today |
|---|---|---|
| `pipeline/run.py` | 12 | 1,438 |
| `gui/web/pages.py` | 12 | |
| `io/case.py` | 11 | 869 |
| `gui/web/frame.py` | 10 | |
| `api/project.py` | 10 | 1,884 |
| `pipeline/checks.py` | 9 | 1,151 |
| `pipeline/case.py` | 9 | 482 |
| `gui/web/screens.py` | 9 | |
| `io/project.py` | 8 | |
| `io/models.py` | 8 | 1,063 |

Over Phases 5 and 6 so far, `git log --format=%s v0.5.0..v0.7.0-alpha.3`, counted by prefix: 473 commits, of them
`docs` 234, `feat` 101, `fix` 74, `chore` 32, `test` 20 and `refactor` 12. `git log --format=%h <range> -- <path> | wc
-l`: 176 commits touch `src/`, 134 `tests/`, 317 `docs/plans/` and 182 the specification. `git diff --shortstat v0.5.0
v0.7.0-alpha.3 -- <paths>`: `src/` gained 45,260 lines and lost 7,471; `tests/` gained 6,554 and lost 615; the plans,
the specification, the reviews, the knowledge base and `CHANGELOG.md` together gained 45,766 and lost 4,169.

## The open items

`grep '^| REV-' docs/project/review-findings.md docs/project/review-archive.md`, the area and the severity cut with
`awk -F'|'` and counted. The log holds 59 rows and the archive 220; the highest is REV-279.

| Area | Rows, both files | In the log today | High | Medium |
|---|---|---|---|---|
| interface | 102 | 28 | 1 | 10 |
| verification | 41 | 3 | 1 | 15 |
| process | 31 | 5 | 0 | 8 |
| performance | 23 | 6 | 0 | 3 |
| numerics | 22 | 6 | 1 | 8 |
| documentation | 16 | 3 | 0 | 0 |
| coupling | 16 | 0 | 0 | 2 |
| physics | 15 | 5 | 1 | 6 |
| provenance | 7 | 2 | 0 | 2 |
| tooling | 4 | 0 | 0 | 0 |
| efficiency | 2 | 1 | 0 | 0 |

By severity, both files: 4 high, 54 medium, 221 low. By status: the log holds 35 `accepted`, 17 `deferred`, 3
`post-1.0`, 3 `declined` and 1 `fixed`; the archive 209 `fixed`, 7 `declined` and 4 `wontfix`. Interface items are 37 %
of all rows and 47 % of those still in the log.

## Two runs, timed

Each case ran once with bash's `time`, one thread, a new store and a new run directory:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 UV_NO_SYNC=1
NANOPNP_STORE=<new> bash -c 'time uv run nanopnp run <case> --threads 1 --run-dir <new> --json'
```

The stage times are the `stages` of the JSON the command prints; the rest is `solver.run` and `stabilisation` of the
run's `manifest.json`. Both ran on NGSolve 6.2.2606 with UMFPACK under Python 3.14.6.

| | `examples/01-quickstart/quickstart.case.yaml` | `examples/02-charged-pore/epnpns.case.yaml` |
|---|---|---|
| Wall time (`real`) | 9.46 s | 9.71 s |
| Stages: region, mesh, charge, solve, quantities | 0.23, 0.71, –, 7.40, 0.12 s | 0.11, 0.17, 0.09, 8.67, 0.12 s |
| Mesh | 392 elements, 215 vertices | 392 elements, 215 vertices |
| Stabilisation mode, requested and recorded | `none` | `none` |
| Largest cell Péclet number | 0.074 | 0.334 |
| Rungs of the ladder | 15 | 19 |
| Newton iterations | 64 | 110 |
| Smallest damping used | 0.200 | 0.080 |
| Switches away from the validated default | 0 | 0 |

The same manifests, the rungs summed by their model:

| Model of the rung | Quickstart: rungs, iterations, seconds | Charged pore: rungs, iterations, seconds | Seconds an iteration |
|---|---|---|---|
| `pnp` | 6, 30, 0.45 | 10, 70, 1.06 | 0.015 |
| `pnp-ns` | 1, 4, 0.13 | 1, 5, 0.17 | 0.033 |
| `epnp-ns` | 6, 30, 6.55 | 6, 35, 7.19 | 0.218 and 0.205 |

On one mesh of 392 elements, a Newton iteration of the full model with its corrections takes six times one of the same
five fields without them, and 85 to 92 % of each solve is spent in the six rungs that carry the corrections. Each run
reaches its answer through 15 or 19 rungs; the rung that is the answer is one of them.

## The records beside the code

`find <path> -name '*.md' | xargs cat | wc -w`, with the files counted by `find <path> -name '*.md' | wc -l`:

| Record | Files | Words |
|---|---|---|
| The specification, less its history (`specification/` outside `history/`, with `SPECIFICATION.md`) | 36 | 88,566 |
| The rulings' history (`specification/history/`) | 54 | 72,141 |
| The plans (`docs/plans/`) | 104 | 453,720 |
| The code reviews (`docs/code_reviews/`) | 115 | 413,493 |
| The knowledge base (`knowledge/`) | 140 | 94,600 |
| `CHANGELOG.md` | 1 | 34,502 |
| The agents' instructions (`.claude/**/*.md`, with `CLAUDE.md`) | 30 | 18,850 |

The same count over the code: `src/nanopnp/**/*.py` holds 314,652 words in its 80,973 lines and `tests/**/*.py`
162,041 in 46,960. The seven records hold 1,175,872 words: 2.5 words of record for each word of package and tests.
The workflow's scripts and hooks (`.claude/**/*.py` and `*.sh`) are another 4,393 lines.

## The measured rates

`specification/08-implementation-plan/03-effort-estimate.md` (§8.3), read on the same day:

- a text or clean-up package takes about 5 sessions, 3 to 6 agent hours and 8 of the author's touches;
- a shell package about 6 sessions, 6 to 12 agent hours and 10 touches;
- a package takes at least four sessions: its plan, the plan's review, its implementation and its shipping;
- Phase 5's library steps WP5.03 to WP5.06 took 1 to 3 hours each from first commit to last, and WP5.07, WP5.08 and
  WP5.10, which add a mechanism, a screen or the rules, 7 to 11;
- the estimate to v0.13 from 23 November 2026, less Phases 8 to 10, which are not estimated: 194 sessions, 171 to 341
  agent hours and 317 touches.

## Cited, not measured again

- **Stage times at `db952e3`** (`docs/project/cost-study.json`, `walks`). The quickstart walk took 12.4 s, 12.1 s of it
  the solve. The walk of the pore `2wcd` took 394 s, 275 s of it the solve; reading and writing the store took 0.7 % of
  it.
- **The push gate** took 539 s on `13f72c3` on four CPUs, against 243 s at Phase 4's close; the 149 browser tests of
  the screens take 468 s of it (Phase 5's end-of-phase report, *The development loop*).
- **The install** with the `structure` and `gui` extras took 5.3 s cold into an environment of 763 MB; the wheel is
  3.1 MB (the same report, *The fresh install*).
- **The redraw** of a pick on the charge map, without a graphics card: 314.6 ms median and 513.8 ms at the 95th
  percentile against the 200 ms line, 188 ms of the median the server's handling; the whole repaint with Mol\*
  1,285.6 ms (the same report, *The redraw, headless*).
- **Continuous integration.** The critical path of run 837 was 10 min 58 s on Linux and macOS; the Windows leg has not
  finished since 10 November 2026 (REV-277; the same report).
- **The suite.** 2,068 tests: 1,758 in Tier 1, 220 in Tier 2 (the same report, *The suite*).
- **A slow solve.** A cylinder of 16,444 elements takes 761 s on four cores (REV-156, whose title gives the mesh as
  16,562 elements); UMFPACK repeats its symbolic analysis in every Newton step (REV-60).
