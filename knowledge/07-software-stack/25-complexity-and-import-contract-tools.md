---
type: Library Behaviour
title: "25. xenon and import-linter beside ruff's C901 and VER-61 (WP5.10)"
description: What xenon and import-linter report on nanopnp, what each adds over ruff's complexity rules and the layering test, and why neither is adopted.
tags:
- software
- library-behaviour
- code-quality
- architecture
sources:
- id: wp5.10-plan
  resource: docs/plans/phase-5/wp5.10-the-written-knowledges-tools-and-rules.md
  title: WP5.10 plan, D6 and D8
- id: survey
  resource: .claude/scripts/audit/survey.sh
  title: The survey script of code review 039, which runs both tools from ephemeral environments
- id: modularity
  resource: docs/project/modularity.md
  title: The modularity report, its edge kinds and its layer order
generated:
  by: claude-code/0.6.0-alpha.9
  at: '2026-11-09T00:00:00Z'
tested_with:
  xenon: 0.9.3
  radon: 6.0.1
  import-linter: 2.16
  grimp: 3.19
verified:
- by: process:uvx xenon and uv run --with import-linter at 3427617a
  at: '2026-11-09T00:00:00Z'
---

## 25. xenon and import-linter beside ruff's C901 and VER-61 (WP5.10)

The tree measures function size with ruff's `C901` (McCabe, `max-complexity = 15`) and `PLR0913`
(`max-args = 8`), and guards its layering with VER-61 (`tests/tier1/test_layering.py`), which asserts
that the live import relation equals `docs/project/modularity-layering.yaml` in both directions
(§8.2.36 AL7, AL27). Both tools below were run on commit `3427617a` from ephemeral environments, so
neither touched `uv.lock`. [verified][^run]

### import-linter: a subset of VER-61

One `layers` contract lists `LAYER_ORDER` of `nanopnp.validation.modularity` highest first, `gui` down
to `core`, without the root package.

| Configuration | Imports read | Result | Time |
|---|---|---|---|
| As is | 922 | Broken: 8 imports in 5 layer pairs | 12.6 s, the tool's download included |
| `exclude_type_checking_imports = True` | 795 | Kept | 0.3 s |

The eight are all inside `if TYPE_CHECKING:`: `core.stages` to `io.artefact` and `io.defaults`;
`geometry.analyte` to `mesh.primitives`; `io.artefact`, `io.manifest` and `io.resolved` to
`materials.electrolyte`; `io.resolved` to `numerics.newton` and to `physics.models`. Each pair is
already a row of `modularity-layering.yaml` with its finding (for example `core` to `io`, MOD-15;
`geometry` to `mesh`, MOD-03; WP5.17 removed that import and its row). [verified][^run]

- **It adds:** the file and line of each offending import, and a contract that can name independent
  siblings (`a | b`).
- **It lacks:** the four edge kinds of the modularity report (it sees `typing` imports or nothing, and
  never the `string` relation); the accepted edges with their findings, which it could hold only as an
  `ignore_imports` list repeating the YAML; and the reverse direction, so an edge that disappears goes
  unnoticed. With `typing` imports excluded, a kept contract says what VER-61's two upward ratchets
  already say: no `top` or `deferred` import points up the order.

### xenon: another measure, not a stricter one

xenon asserts thresholds on radon's cyclomatic complexity. Run as the survey runs it
(`--max-absolute C --max-modules B --max-average A`), it fails on 20 blocks of rank D or E (21 or
more) and on the module `cli/__init__.py` (rank C). With `--max-absolute C` alone it fails on the same
20 blocks. [verified][^run]

radon and ruff's McCabe count differently. radon adds one for each boolean operator and each
comprehension condition, and scores a nested function apart from its parent. So:

- 7 of the 20 already carry `# noqa: C901`: `structure/read.py` `select` (38), `pipeline/run.py`
  `selected_stages` (37), `solve/continuation.py` `default_ladder` (29), `pipeline/checks.py`
  `require_runnable` (27), `cli/running.py` `_inspect` and `_plot` (27 each), `numerics/newton.py`
  `damped_newton` (25).
- 13 pass ruff at 15, among them `charge/protonation.py` `_assemble` (radon 39, McCabe 12) and
  `validation/modularity.py` `surface` (radon 21, McCabe 5).
- 2 of ruff's suppressions pass xenon: `gui/web/pages.py` `install` (radon 3, its closures scored
  apart) and `io/variables.py` `_admit` (radon 20, rank C).

xenon suppresses only by path (`--exclude`, `--ignore`), never one block, so adopting it means a
second threshold that disagrees with the first on 15 of 22 functions, and whole files excluded.

### Recommendation

Adopt neither. The adoption is the author's (the Phase 5 plan's open decision 14). import-linter repeats
VER-61 with less: no edge kinds, no accepted edges, one direction. xenon measures what ruff's `C901`
already bounds, by a rule that weights boolean operators, and cannot suppress one block. If the author
wants a second bound, ruff's `PLR0912` (branches) and `PLR0915` (statements) add one with no new
dependency and the same `noqa` as `C901`.

[^run]: `uv run --with import-linter lint-imports --config <ini> --no-cache` with the two
    configurations above, `uvx xenon src/nanopnp --max-absolute C --max-modules B --max-average A`,
    `uvx xenon src/nanopnp --max-absolute C`, and `uvx radon cc -s -n D src/nanopnp` for the scores;
    ruff's McCabe scores by `ruff check --select C901` at `max-complexity = 1`. Run 9 November 2026.
