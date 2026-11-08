# Step 2: hits dismissed, with the reason

Every hit of step 1 that is not a finding. The findings the hits produced are ORC-01 to ORC-15 in `own-findings.md`. Counts are at a5039af; the two probe scripts were corrected and re-run on the same files at b602e60 (`markers.md`, `probes.md`, `probes-live-problems.md`).

| Hit (file, probe) | Reason |
|---|---|
| `probes.md`, §8.2.39 cited, 1 record hit | The hit is the probe's own heading in the audit's output file. |
| `probes.md`, WP46 D1 to D6 and WP59 D5 "NO ROW" (16 live hits) | False positives: `probes.py` required the first cell to be `Dn` alone, and those plans write `D1 Radial grid …` and `**D1 The case owns its source**`. The rows exist (`wp46-small-fixes.md:46-51`, `wp59-architecture-review-fixes.md:42-47`). Regex corrected; the re-run reports none. |
| `probes.md`, version named "not a tag" (70 live hits) | The hosted clone is shallow and holds five tags. `git ls-remote --tags origin` lists `v0.1.0` to `v0.5.0` with their alphas and `v0.6.0-alpha.2` to `.9`. `v0.6.0-alpha.1` is not a tag by rule (WP5.01 merged before `v0.5.0`, §8.4.1); `v0.6.0-alpha.15` to `.16`, `v0.6.0` and `v0.7.0` are planned; `v0.2.0` in `CONTRIBUTING.md:177` is the procedure's example; zensical `v0.0.11` is another project's tag. |
| `probes.md`, test file named: `docs/project/review-items.md:958-984` | The *Measured* and *Fixed* paragraphs of the closed items REV-87, REV-88 and REV-90 record the state at the time; the register's rows are records (brief, *Scope*). |
| `probes.md`, test file named: `knowledge/log.md:65` | A dated log line. |
| `probes.md`, VER/VAL withdrawn: `.claude/rules/python.md:30`, `knowledge/07-software-stack/20-…:33`, `24-…:35`, `specification/10-open-items.md:19` | VER-72's guard part (a) is in force; only its conventions (b) to (h) are withdrawn, and each hit cites the guard or VER-72's import list. |
| `probes.md`, VER/VAL "NO DEFINITION": `.claude/scripts/clause.py:8` (`VER-6`) | The docstring's example of a non-match. |
| `probes.md`, VER/VAL withdrawn: `docs/project/review-findings.md:34,93,114,117,119`; `review-items.md:118-1147` (REV-10, 69, 74, 85, 87, 88, 90, 92, 93, 95, 96, 109 sections) | Closed items naming the identifier as it stood when found; records. |
| `probes.md`, VER/VAL withdrawn: `specification/07-verification/02-tier-1.md:56-68`, `a-traceability-matrix.md:102-103`, `knowledge/log.md:52` | The withdrawn rows themselves, the matrix sentence that lists them, and a log line. |
| `probes.md`, `pending.yaml`: `docs/project/review-items.md:1091,1093`, `knowledge/log.md:38` | REV-103's closed record and the log line that records the deletion. |
| `probes.md`, `nanopnp/case/v0.5`: `specification/05-software-design/03-1-case-file.md:110,759,767` | Each names the identifier as retired (SPC-21 counts the second as a duplicate sentence). |
| `probes.md`, `load_case`, `run_case`, `resolve(`: `.claude/scripts/clause.py:26`, `duplicates.py:20` | `Path.resolve()`. |
| `probes.md`, `load_case`, `resolve(`: `docs/plans/phase-5-workbench.md:169`, `specification/05-software-design/03-1-case-file.md:278,282,776`, `docs/project/review-items.md:2552` | `pipeline.case.load_case` and `pipeline.case.resolve` exist (`src/nanopnp/pipeline/case.py:56,265`); not public, but the sentences do not say they are. |
| `probes.md`, `run_case`, `resolve`: `docs/project/review-items.md:289,293,1048,1974`, `knowledge/log.md:24` | Closed items' *Measured* text and a log line that records the renaming (WP57). |
| `probes.md`, old command names (16 live hits) | `core.md:4-5` states that plans before WP53 use them; the REV titles and *Found* lines name the review that found an item, as it was called; `knowledge/07-software-stack/15-…:45,47` cite "the WP32 `/wp-ship` review" as a dated source. |
| `probes.md`, PyQt (11 live hits) | Every hit forbids PyQt or asserts its absence. |
| `probes.md`, coverage tooling (28 live hits) | Each hit says no coverage is measured (CLAUDE.md, CONTRIBUTING.md, §7.6, the steward, VER-72), is a closed item or a dated measurement (REV-74, REV-109, `knowledge/07/12:114-163`, which ends "nothing in the suite measures coverage now"), or means platform coverage (`knowledge/07/05`). |
| `probes.md`, `--extended`, `no_cover`, `test_plan_shape`: `knowledge/07/12:103,135,146,160-163`, `07/19:32`, `knowledge/log.md:39,65`, `docs/project/review-items.md:852,909,958` | `07/12:103` and `:162-163` state the renaming and the removal; `07/19:32` says the test was deleted; the rest are dated records. (`07/08:85` is ORC-09.) |
| `markers.md`, four `[tested:]` markers "no function" (`knowledge/05/12:23-25`, `06/09:613`) | `markers.py` did not read `Class::method` node ids; the methods exist (`tests/tier1/test_analyte.py:85,96,135`, `test_forces.py:47`). Script corrected; the re-run reports none. |
| `markers.md`, `knowledge/log.md:38` unparseable `[tested: …]` | The log line describes the marker form. |
| `markers.md`, `[verified]` without footnote: `knowledge/00-orientation/03:19`, `04:32`, `08-validation-benchmarks/00:17`, `knowledge/log.md:38,53` | The convention's own text and two log lines. (The other fifteen are ORC-07.) |
| `markers.md`, `[verified]` sources by kind (70 plan or review, 17 COMSOL report, 9 specification, 6 ESI, 5 code or test, 1 thesis) | A profile of the evidence, reported in §2; the one thesis-footnoted claim is KGE-10. |
| `links.md`, broken paths: `docs/code_reviews/CODE_REVIEW_013.md:31`, `docs/plans/wp52-specification-and-plans-split.md:175` | Records stay byte for byte; both are reported here for reachability. |
| `links.md`, anchors `README.md:63-67` → `CHANGELOG.md#010---2026-09-02` and the like | GitHub's anchor for `## [0.1.0] - 2026-09-02`; `links.py` applies Python-Markdown's slug, and README is read on GitHub, not on the site. |
| `links.md`, anchors `docs/plans/wp13-…:17`, `wp14-…:19` | Records. |
| `inventory.md`, unreached `.claude/agents/physics-reviewer.md` | Claude Code discovers an agent by its directory; CLAUDE.md names it by name. |
| `inventory.md`, unreached `docs/code_reviews/CODE_REVIEW_039.md` | This report. |
| `clause-check-appendix-a.log` | 83 identifiers, 0 misses: nothing to classify. |
| `duplicates.log` | Exit 0: no shared number; its first-cell gap is ORC-01. |
| `build-strict.log` | Exit 0; its forty `INFO` lines on links to excluded plans are ORC-14. |
| Every log's `UV_NATIVE_TLS` deprecation warning | The container's `uv` environment, not the repository. |
