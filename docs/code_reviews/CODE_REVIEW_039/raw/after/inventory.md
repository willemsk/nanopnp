# inventory.py at 86e647b
# Inventory of the files in scope

Tokens are estimated as characters divided by four. `indexed by` lists the index files (`index.md`, `README.md`, `SPECIFICATION.md`, `CLAUDE.md`, `AGENTS.md`, `current.md`) that link to the file; `inbound` counts every other Markdown file that links to it or names its path; `code` counts the `src/` and `tests/` files naming its path.

| Path | Words | Tokens | Kind | OKF type | Site nav | Indexed by | Inbound | Code |
|---|---|---|---|---|---|---|---|---|
| `.claude/agents/ci-log-classifier.md` | 134 | 203 | live |  | no | — | 3 | 0 |
| `.claude/agents/gui-reviewer.md` | 257 | 407 | live |  | no | — | 7 | 0 |
| `.claude/agents/physics-reviewer.md` | 118 | 193 | live |  | no | — | 4 | 0 |
| `.claude/hooks/format.sh` | 256 | 404 | live |  | no | — | 5 | 0 |
| `.claude/hooks/gate.sh` | 3840 | 6769 | live |  | no | — | 95 | 0 |
| `.claude/hooks/session-start.sh` | 1049 | 1917 | live |  | no | — | 13 | 0 |
| `.claude/rules/physics-numerics.md` | 384 | 684 | live |  | no | — | 22 | 0 |
| `.claude/rules/python.md` | 294 | 493 | live |  | no | — | 35 | 0 |
| `.claude/scripts/clause.py` | 1018 | 2249 | live |  | no | — | 43 | 0 |
| `.claude/scripts/duplicates.py` | 359 | 861 | live |  | no | — | 24 | 0 |
| `.claude/scripts/same_tree.py` | 566 | 1289 | live |  | no | — | 15 | 0 |
| `.claude/skills/np-gui/SKILL.md` | 132 | 229 | live |  | no | — | 3 | 0 |
| `.claude/skills/np-gui/collect.md` | 150 | 227 | live |  | no | — | 5 | 0 |
| `.claude/skills/np-gui/grill.md` | 288 | 434 | live |  | no | — | 9 | 0 |
| `.claude/skills/np-gui/publish.md` | 212 | 337 | live |  | no | — | 5 | 0 |
| `.claude/skills/np-gui/render.md` | 506 | 907 | live |  | no | — | 8 | 0 |
| `.claude/skills/np-gui/review.md` | 117 | 184 | live |  | no | — | 5 | 0 |
| `.claude/skills/np-implement/SKILL.md` | 103 | 176 | live |  | no | — | 3 | 0 |
| `.claude/skills/np-implement/wp.md` | 953 | 1399 | live |  | no | — | 9 | 0 |
| `.claude/skills/np-plan/SKILL.md` | 191 | 308 | live |  | no | — | 5 | 0 |
| `.claude/skills/np-plan/amend.md` | 237 | 361 | live |  | no | — | 10 | 0 |
| `.claude/skills/np-plan/phase.md` | 962 | 1440 | live |  | no | — | 7 | 0 |
| `.claude/skills/np-plan/project.md` | 308 | 472 | live |  | no | — | 8 | 0 |
| `.claude/skills/np-plan/review.md` | 871 | 1302 | live |  | no | — | 8 | 0 |
| `.claude/skills/np-plan/rulings.md` | 991 | 1482 | live |  | no | — | 28 | 0 |
| `.claude/skills/np-plan/wp.md` | 1712 | 2545 | live |  | no | — | 14 | 0 |
| `.claude/skills/np-ship/SKILL.md` | 122 | 193 | live |  | no | — | 3 | 0 |
| `.claude/skills/np-ship/phase.md` | 241 | 363 | live |  | no | — | 5 | 0 |
| `.claude/skills/np-ship/wp.md` | 1641 | 2459 | live |  | no | — | 13 | 0 |
| `.claude/skills/steward/SKILL.md` | 1724 | 2636 | live |  | no | — | 12 | 0 |
| `.claude/workflow/core.md` | 1501 | 2291 | live |  | no | — | 45 | 0 |
| `.claude/workflow/hosts.md` | 91 | 154 | live |  | no | — | 17 | 0 |
| `.claude/workflow/hosts/copilot.md` | 1229 | 1911 | live |  | no | — | 18 | 0 |
| `AGENTS.md` | 32 | 61 | live |  | no | — | 9 | 0 |
| `CHANGELOG.md` | 26615 | 45773 | record |  | generated | `README.md`, `SPECIFICATION.md` | 96 | 1 |
| `CLAUDE.md` | 2099 | 3374 | live |  | no | `AGENTS.md`, `README.md` | 107 | 2 |
| `CONTRIBUTING.md` | 1769 | 2812 | live |  | no | `README.md` | 38 | 0 |
| `README.md` | 1439 | 2788 | live |  | no | — | 53 | 3 |
| `SPECIFICATION.md` | 1026 | 2609 | live |  | generated | `README.md`, `specification/index.md` | 167 | 36 |
| `docs/code_reviews/CODE_REVIEW_001.md` | 4766 | 9190 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_002.md` | 7270 | 13652 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_003.md` | 5795 | 10291 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_004.md` | 1168 | 1958 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_005.md` | 1110 | 2105 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_006.md` | 2078 | 3439 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_007.md` | 511 | 1025 | record |  | excluded | `docs/code_reviews/index.md` | 4 | 0 |
| `docs/code_reviews/CODE_REVIEW_008.md` | 989 | 1858 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_009.md` | 1337 | 2265 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_010.md` | 3926 | 7355 | record |  | excluded | `docs/code_reviews/index.md` | 6 | 0 |
| `docs/code_reviews/CODE_REVIEW_011.md` | 738 | 1210 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_012.md` | 3702 | 6878 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_013.md` | 1330 | 2079 | record |  | excluded | `docs/code_reviews/index.md` | 8 | 0 |
| `docs/code_reviews/CODE_REVIEW_014.md` | 1737 | 2604 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_015.md` | 1916 | 2921 | record |  | excluded | `docs/code_reviews/index.md` | 4 | 0 |
| `docs/code_reviews/CODE_REVIEW_016.md` | 1861 | 2881 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_017.md` | 1785 | 2868 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_018.md` | 1717 | 2696 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_019.md` | 392 | 664 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_020.md` | 732 | 1167 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_021.md` | 1654 | 2714 | record |  | excluded | `docs/code_reviews/index.md` | 7 | 0 |
| `docs/code_reviews/CODE_REVIEW_022.md` | 381 | 676 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_023.md` | 208 | 421 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_024.md` | 1246 | 1959 | record |  | excluded | `docs/code_reviews/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 6 | 0 |
| `docs/code_reviews/CODE_REVIEW_024/execution-plan.md` | 3649 | 8239 | record |  | excluded | — | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_025.md` | 855 | 1528 | record |  | excluded | `docs/code_reviews/index.md` | 7 | 0 |
| `docs/code_reviews/CODE_REVIEW_026.md` | 468 | 797 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_027.md` | 407 | 751 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_028.md` | 336 | 530 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_029.md` | 882 | 1456 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/CODE_REVIEW_030.md` | 960 | 1548 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_031.md` | 592 | 979 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_032.md` | 369 | 586 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_033.md` | 746 | 1144 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_034.md` | 721 | 1201 | record |  | excluded | `docs/code_reviews/index.md` | 4 | 0 |
| `docs/code_reviews/CODE_REVIEW_035.md` | 550 | 883 | record |  | excluded | `docs/code_reviews/index.md` | 1 | 0 |
| `docs/code_reviews/CODE_REVIEW_036.md` | 6644 | 15167 | record |  | excluded | `docs/code_reviews/index.md` | 6 | 0 |
| `docs/code_reviews/CODE_REVIEW_037.md` | 813 | 1329 | record |  | excluded | `docs/code_reviews/index.md` | 2 | 0 |
| `docs/code_reviews/CODE_REVIEW_038.md` | 2775 | 4616 | record |  | excluded | `docs/code_reviews/index.md` | 5 | 0 |
| `docs/code_reviews/CODE_REVIEW_039.md` | 793 | 1467 | record |  | excluded | `docs/code_reviews/index.md` | 3 | 0 |
| `docs/code_reviews/index.md` | 1272 | 2721 | record |  | excluded | — | 0 | 0 |
| `docs/design/generators/README.md` | 196 | 299 | out |  | excluded | — | 1 | 0 |
| `docs/design/reviews/2026-10-25-choices.md` | 2132 | 2767 | record |  | excluded | `docs/design/reviews/index.md` | 5 | 0 |
| `docs/design/reviews/2026-10-25-concepts.md` | 940 | 1335 | record |  | excluded | `docs/design/reviews/index.md` | 4 | 0 |
| `docs/design/reviews/2026-10-25-qt-shell.md` | 1139 | 1631 | record |  | excluded | `docs/design/reviews/index.md` | 5 | 0 |
| `docs/design/reviews/2026-10-25-style.md` | 595 | 824 | record |  | excluded | `docs/design/reviews/index.md` | 4 | 0 |
| `docs/design/reviews/2026-10-26-mockups.md` | 1942 | 2575 | record |  | excluded | `docs/design/reviews/index.md` | 5 | 0 |
| `docs/design/reviews/2026-11-05-frame.md` | 1590 | 2244 | record |  | excluded | `docs/design/reviews/index.md` | 8 | 0 |
| `docs/design/reviews/index.md` | 290 | 528 | record |  | excluded | — | 3 | 0 |
| `docs/design/spike/report.md` | 1491 | 2108 | record |  | excluded | `docs/plans/phase-5/phase-5-record.md`, `docs/plans/phase-5/phase-5-workbench.md` | 12 | 0 |
| `docs/design/tokens.css` | 650 | 1228 | live |  | no | — | 19 | 0 |
| `docs/design/workbench.md` | 10825 | 15665 | live |  | nav | `docs/project/index.md` | 45 | 1 |
| `docs/examples/index.md` | 413 | 652 | live |  | nav | — | 8 | 0 |
| `docs/getting-started.md` | 517 | 893 | live |  | nav | `docs/index.md` | 14 | 0 |
| `docs/guide/case-files.md` | 757 | 1274 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 19 | 0 |
| `docs/guide/charge.md` | 1671 | 2650 | live |  | nav | `docs/guide/index.md` | 16 | 0 |
| `docs/guide/concepts.md` | 839 | 1284 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 13 | 0 |
| `docs/guide/desktop.md` | 1418 | 2080 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 13 | 0 |
| `docs/guide/fields.md` | 589 | 941 | live |  | nav | `docs/guide/index.md` | 7 | 0 |
| `docs/guide/geometry.md` | 1852 | 3000 | live |  | nav | `docs/guide/index.md` | 27 | 0 |
| `docs/guide/index.md` | 303 | 503 | live |  | nav | — | 4 | 0 |
| `docs/guide/meshes.md` | 1175 | 1852 | live |  | nav | `docs/guide/index.md` | 15 | 0 |
| `docs/guide/notebooks.md` | 290 | 560 | live |  | nav | `docs/guide/index.md` | 12 | 0 |
| `docs/guide/outputs.md` | 602 | 945 | live |  | nav | `docs/guide/index.md` | 8 | 0 |
| `docs/guide/provenance.md` | 599 | 964 | live |  | nav | `docs/guide/index.md` | 8 | 0 |
| `docs/guide/python.md` | 1216 | 2115 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 11 | 0 |
| `docs/guide/running.md` | 927 | 1390 | live |  | nav | `docs/guide/index.md` | 12 | 0 |
| `docs/guide/stabilisation.md` | 332 | 549 | live |  | nav | `docs/guide/index.md` | 19 | 0 |
| `docs/guide/structures.md` | 1360 | 2081 | live |  | nav | `docs/guide/index.md` | 13 | 0 |
| `docs/guide/sweeps.md` | 772 | 1198 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 16 | 0 |
| `docs/index.md` | 501 | 881 | live |  | nav | — | 16 | 0 |
| `docs/model/index.md` | 504 | 935 | live |  | nav | `docs/guide/index.md`, `docs/index.md` | 9 | 0 |
| `docs/plans/sessions/copilot-host.md` | 4819 | 8252 | record |  | excluded | `docs/plans/index.md` | 6 | 0 |
| `docs/plans/current.md` | 699 | 1204 | live |  | excluded | `SPECIFICATION.md`, `docs/plans/index.md` | 76 | 0 |
| `docs/plans/sessions/history-prose-review.md` | 2607 | 4353 | record |  | excluded | `docs/plans/index.md` | 8 | 0 |
| `docs/plans/index.md` | 1287 | 2613 | record |  | excluded | — | 0 | 0 |
| `docs/plans/sessions/kb-audit-brief.md` | 4954 | 8173 | record |  | excluded | `docs/plans/index.md` | 4 | 0 |
| `docs/plans/sessions/notebooks-review-for-wp54.md` | 3012 | 6111 | record |  | excluded | `docs/plans/index.md` | 7 | 0 |
| `docs/plans/sessions/okf-converter-rules.md` | 841 | 1351 | record |  | excluded | `docs/plans/index.md` | 4 | 0 |
| `docs/plans/sessions/okf-knowledge-bundle.md` | 1164 | 1878 | record |  | excluded | `docs/plans/index.md` | 8 | 0 |
| `docs/plans/phase-0/phase-0-consolidation.md` | 3652 | 6555 | record |  | excluded | `docs/plans/index.md` | 3 | 0 |
| `docs/plans/phase-0/phase-0-spike.md` | 5880 | 9001 | record |  | excluded | `docs/plans/index.md` | 4 | 0 |
| `docs/plans/phase-1/phase-1-solver-core.md` | 13636 | 22434 | record |  | excluded | `docs/plans/index.md` | 19 | 0 |
| `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 7293 | 11664 | record |  | excluded | `docs/plans/index.md` | 14 | 0 |
| `docs/plans/phase-3/phase-3-charge-pipeline.md` | 7550 | 11850 | record |  | excluded | `docs/plans/index.md` | 16 | 0 |
| `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 8112 | 12371 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-record.md` | 32 | 0 |
| `docs/plans/phase-4/phase-4-record.md` | 18859 | 29268 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 9 | 0 |
| `docs/plans/phase-5/phase-5-record.md` | 3800 | 5738 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 9 | 0 |
| `docs/plans/phase-5/phase-5-workbench.md` | 5287 | 8202 | live |  | excluded | `docs/plans/current.md`, `docs/plans/index.md`, `docs/plans/phase-5/phase-5-record.md` | 26 | 0 |
| `docs/plans/phase-1/wp10-cli-runs-field-output.md` | 7759 | 12262 | record |  | excluded | `docs/plans/index.md` | 2 | 0 |
| `docs/plans/phase-1/wp11-sweep-runner.md` | 11217 | 17199 | record |  | excluded | `docs/plans/index.md` | 3 | 0 |
| `docs/plans/phase-1/wp12-reference-stabilised-mode.md` | 9488 | 14720 | record |  | excluded | `docs/plans/index.md` | 5 | 0 |
| `docs/plans/phase-1/wp13-tier3-comsol-comparison.md` | 6126 | 10020 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-1/phase-1-solver-core.md` | 3 | 0 |
| `docs/plans/phase-1/wp14-gui-shell-packaging-probe.md` | 5983 | 10141 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-1/phase-1-solver-core.md` | 7 | 0 |
| `docs/plans/phase-1/wp15-live-convergence-and-viewer.md` | 5956 | 9282 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-1/phase-1-solver-core.md` | 5 | 0 |
| `docs/plans/phase-1/wp16-user-docs-and-examples.md` | 3172 | 5221 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-1/phase-1-solver-core.md` | 3 | 0 |
| `docs/plans/phase-2/wp17-case-schema-v2.md` | 3181 | 5169 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 6 | 0 |
| `docs/plans/phase-2/wp18-structure-ingestion.md` | 4897 | 7614 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 7 | 0 |
| `docs/plans/phase-2/wp19-density-and-reduction.md` | 5623 | 8627 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 4 | 0 |
| `docs/plans/phase-2/wp20-contour-extraction.md` | 5904 | 8879 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 5 | 0 |
| `docs/plans/phase-2/wp21-cad-assembly-and-meshing.md` | 4474 | 7264 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 7 | 0 |
| `docs/plans/phase-2/wp22-val05-reference-geometry.md` | 4556 | 7248 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 9 | 0 |
| `docs/plans/phase-2/wp23-gmsh-backend.md` | 4590 | 7134 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 4 | 0 |
| `docs/plans/phase-2/wp24-gui-geometry-pipeline.md` | 3943 | 6395 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 5 | 0 |
| `docs/plans/phase-2/wp25-geometry-docs-and-example.md` | 3303 | 5316 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-2/phase-2-geometry-pipeline.md` | 3 | 0 |
| `docs/plans/phase-3/wp26-physics-model-interface.md` | 2772 | 4622 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 3 | 0 |
| `docs/plans/phase-3/wp27-protonation.md` | 2958 | 4745 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 4 | 0 |
| `docs/plans/phase-3/wp28-charge-deposition.md` | 3785 | 5855 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 6 | 0 |
| `docs/plans/phase-3/wp29-val06-apbs.md` | 4416 | 6205 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 4 | 0 |
| `docs/plans/phase-3/wp30-dielectric-and-exclusion.md` | 4504 | 6464 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 5 | 0 |
| `docs/plans/phase-3/wp31-gui-charge-pipeline.md` | 4156 | 6483 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 5 | 0 |
| `docs/plans/phase-3/wp32-charge-docs-and-example.md` | 4334 | 7076 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 4 | 0 |
| `docs/plans/phase-3/wp33-test-durations.md` | 4160 | 6075 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 4 | 0 |
| `docs/plans/phase-3/wp34-phase-3-close.md` | 3425 | 5553 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-3/phase-3-charge-pipeline.md` | 5 | 0 |
| `docs/plans/phase-4/wp35-modularity-exploration.md` | 4536 | 7560 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 3 | 0 |
| `docs/plans/phase-4/wp36-stage-protocol-and-walk.md` | 2368 | 3866 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 4 | 0 |
| `docs/plans/phase-4/wp37-cycle-cuts-exit-codes-backend-guard.md` | 2631 | 4460 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 5 | 0 |
| `docs/plans/phase-4/wp38-io-split.md` | 3769 | 6591 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 6 | 0 |
| `docs/plans/phase-4/wp39-backend-registries.md` | 3055 | 5340 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 5 | 0 |
| `docs/plans/phase-4/wp40-stale-refusals.md` | 1988 | 3424 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 6 | 0 |
| `docs/plans/phase-4/wp41-accuracy-fixes.md` | 3904 | 6002 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 4 | 0 |
| `docs/plans/phase-4/wp42-verification-checks.md` | 4366 | 7882 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 5 | 0 |
| `docs/plans/phase-4/wp43-development-loop.md` | 10154 | 16020 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 7 | 0 |
| `docs/plans/phase-4/wp44-simplify-the-loop.md` | 1352 | 2207 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 7 | 0 |
| `docs/plans/phase-4/wp45-prose-strip.md` | 1724 | 2713 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 5 | 0 |
| `docs/plans/phase-4/wp46-small-fixes.md` | 1703 | 3015 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 6 | 0 |
| `docs/plans/phase-4/wp47-okf-bundle.md` | 1445 | 2431 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 5 | 0 |
| `docs/plans/phase-4/wp48-okf-backfill.md` | 3472 | 6757 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 4 | 0 |
| `docs/plans/phase-4/wp49-cost-study.md` | 1739 | 2809 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 4 | 0 |
| `docs/plans/phase-0/wp5-continuation-qoi-envelope.md` | 3153 | 4997 | record |  | excluded | `docs/plans/index.md` | 3 | 0 |
| `docs/plans/phase-5/wp5.01-workbench-design-study.md` | 6466 | 10916 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-record.md`, `docs/plans/phase-5/phase-5-workbench.md` | 7 | 0 |
| `docs/plans/phase-5/wp5.02-framework-spike.md` | 3002 | 5232 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-record.md`, `docs/plans/phase-5/phase-5-workbench.md` | 6 | 0 |
| `docs/plans/phase-5/wp5.03-protonation-before-the-density.md` | 2710 | 5058 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 6 | 0 |
| `docs/plans/phase-5/wp5.04-the-charge-mutators-library-step.md` | 2702 | 4856 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 4 | 0 |
| `docs/plans/phase-5/wp5.05-named-models-and-study-overrides.md` | 2690 | 5077 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 5 | 0 |
| `docs/plans/phase-5/wp5.06-outputs-and-steric-registries.md` | 2374 | 4881 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 5 | 0 |
| `docs/plans/phase-5/wp5.07-variables-and-the-rebuild-forecast.md` | 3213 | 5752 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 7 | 0 |
| `docs/plans/phase-5/wp5.08-the-frame-and-the-project-folder.md` | 3511 | 6498 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-5/phase-5-record.md`, `docs/plans/phase-5/phase-5-workbench.md` | 4 | 0 |
| `docs/plans/phase-5/wp5.09-the-physics-model.md` | 2336 | 4458 | record |  | excluded | `docs/plans/current.md`, `docs/plans/index.md`, `docs/plans/phase-5/phase-5-workbench.md` | 5 | 0 |
| `docs/plans/phase-4/wp50-test-scope.md` | 1599 | 2594 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 3 | 0 |
| `docs/plans/phase-4/wp51-plotting-and-notebooks.md` | 4083 | 6809 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 3 | 0 |
| `docs/plans/phase-4/wp52-specification-and-plans-split.md` | 3098 | 5312 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 7 | 0 |
| `docs/plans/phase-4/wp53-workflow-commands.md` | 4250 | 6879 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 5 | 0 |
| `docs/plans/phase-4/wp54-notebooks-and-figures-revised.md` | 3464 | 6330 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 7 | 0 |
| `docs/plans/phase-4/wp55-user-testing-protocol.md` | 2875 | 4910 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 8 | 0 |
| `docs/plans/phase-4/wp56-command-line-read-by-a-person.md` | 2619 | 4945 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 4 | 0 |
| `docs/plans/phase-4/wp57-idealised-pore-and-python-interface.md` | 7312 | 14997 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md`, `docs/plans/phase-4/phase-4-record.md` | 7 | 0 |
| `docs/plans/phase-4/wp58-documentation-increment-4.md` | 3853 | 6696 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 5 | 0 |
| `docs/plans/phase-4/wp59-architecture-review-fixes.md` | 2957 | 5715 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 8 | 0 |
| `docs/plans/phase-0/wp6-analyte-and-forces.md` | 3764 | 6083 | record |  | excluded | `docs/plans/index.md` | 2 | 0 |
| `docs/plans/phase-4/wp60-phase-4-close.md` | 2978 | 4913 | record |  | excluded | `docs/plans/index.md`, `docs/plans/phase-4/phase-4-polish-and-user-testing.md` | 4 | 0 |
| `docs/plans/phase-1/wp7-case-schema-artefacts-manifest.md` | 5308 | 8871 | record |  | excluded | `docs/plans/index.md` | 2 | 0 |
| `docs/plans/phase-1/wp8-mesh-ingestion-quality-reference.md` | 8541 | 13475 | record |  | excluded | `docs/plans/index.md` | 3 | 0 |
| `docs/plans/phase-1/wp9-external-fields.md` | 7324 | 11525 | record |  | excluded | `docs/plans/index.md` | 3 | 0 |
| `docs/project/citing.md` | 107 | 197 | live |  | nav | `docs/project/index.md` | 4 | 0 |
| `docs/project/contributing.md` | 555 | 917 | live |  | nav | `docs/project/index.md` | 8 | 0 |
| `docs/project/index.md` | 251 | 446 | live |  | nav | — | 3 | 0 |
| `docs/project/licence.md` | 139 | 268 | live |  | nav | `docs/project/index.md` | 3 | 0 |
| `docs/project/modularity-findings.md` | 597 | 1241 | live |  | nav | `SPECIFICATION.md`, `docs/plans/phase-4/phase-4-record.md`, `docs/project/index.md` | 24 | 0 |
| `docs/project/modularity.md` | 3615 | 6196 | live |  | nav | `docs/plans/phase-4/phase-4-record.md`, `docs/project/index.md` | 26 | 0 |
| `docs/project/physics-models.md` | 1426 | 2515 | live |  | nav | `docs/project/index.md` | 13 | 0 |
| `docs/project/review-findings.md` | 5271 | 12855 | live |  | nav | `SPECIFICATION.md`, `docs/project/index.md` | 38 | 0 |
| `docs/project/review-items.md` | 30721 | 51153 | live |  | nav | `docs/project/index.md` | 39 | 0 |
| `docs/reference/corrections.md` | 318 | 549 | live |  | nav | — | 17 | 0 |
| `docs/reference/index.md` | 145 | 282 | live |  | nav | — | 4 | 0 |
| `docs/superpowers/specs/2026-10-18-test-pruning-design.md` | 1650 | 2682 | record |  | excluded | — | 5 | 0 |
| `docs/superpowers/specs/2026-10-22-notebooks-per-stage-design.md` | 2079 | 3276 | record |  | excluded | — | 2 | 0 |
| `docs/sweeps/README.md` | 333 | 516 | out |  | nav | `docs/project/index.md` | 6 | 0 |
| `docs/user-testing/findings.md` | 4322 | 8666 | record |  | excluded | — | 58 | 0 |
| `docs/user-testing/protocol.md` | 598 | 918 | record |  | excluded | — | 12 | 0 |
| `docs/user-testing/sessions/01-command-line/README.md` | 297 | 439 | record |  | excluded | — | 2 | 0 |
| `docs/user-testing/sessions/02-physics/README.md` | 384 | 574 | record |  | excluded | — | 2 | 0 |
| `docs/user-testing/sessions/03-numerics/README.md` | 333 | 518 | record |  | excluded | — | 2 | 0 |
| `docs/user-testing/sessions/04-python-api/README.md` | 441 | 614 | record |  | excluded | — | 2 | 0 |
| `docs/user-testing/sessions/05-sweep/README.md` | 338 | 484 | record |  | excluded | — | 2 | 0 |
| `docs/validation/comsol-export-contract.md` | 1647 | 2724 | out |  | nav | `docs/plans/phase-1/phase-1-solver-core.md`, `docs/project/index.md` | 10 | 1 |
| `knowledge/00-orientation/00-overview.md` | 172 | 329 | live | Overview | generated | `knowledge/00-orientation/index.md` | 1 | 0 |
| `knowledge/00-orientation/01-files.md` | 228 | 475 | live | Orientation | generated | `knowledge/00-orientation/index.md` | 7 | 0 |
| `knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md` | 174 | 389 | live | Orientation | generated | `knowledge/00-orientation/index.md` | 8 | 0 |
| `knowledge/00-orientation/03-conventions-used-throughout.md` | 114 | 200 | live | Orientation | generated | `knowledge/00-orientation/index.md` | 5 | 0 |
| `knowledge/00-orientation/04-provenance-and-how-to-extend-this.md` | 197 | 387 | live | Orientation | generated | `knowledge/00-orientation/index.md` | 4 | 0 |
| `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md` | 450 | 817 | live | Author Ruling | generated | `knowledge/00-orientation/index.md` | 13 | 0 |
| `knowledge/00-orientation/06-still-open.md` | 104 | 208 | live | Open Item | generated | `knowledge/00-orientation/index.md` | 5 | 0 |
| `knowledge/00-orientation/07-glossary.md` | 2392 | 4382 | live | Glossary | generated | `knowledge/00-orientation/index.md` | 10 | 0 |
| `knowledge/00-orientation/index.md` | 177 | 333 | live |  | generated | `knowledge/index.md` | 4 | 0 |
| `knowledge/01-physics-epnpns/00-overview.md` | 154 | 296 | live | Overview | generated | `knowledge/01-physics-epnpns/index.md` | 4 | 0 |
| `knowledge/01-physics-epnpns/01-symbols.md` | 378 | 533 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 8 | 0 |
| `knowledge/01-physics-epnpns/02-governing-equations.md` | 612 | 956 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 11 | 0 |
| `knowledge/01-physics-epnpns/03-the-corrections.md` | 703 | 1023 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 13 | 2 |
| `knowledge/01-physics-epnpns/04-rationale-worth-preserving.md` | 249 | 415 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 6 | 0 |
| `knowledge/01-physics-epnpns/05-fixed-charge-from-structure.md` | 207 | 362 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 8 | 0 |
| `knowledge/01-physics-epnpns/06-reference-case.md` | 118 | 183 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 4 | 1 |
| `knowledge/01-physics-epnpns/07-implementation-notes-carried-forward.md` | 764 | 1612 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 9 | 1 |
| `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md` | 621 | 944 | live | Erratum | generated | `knowledge/01-physics-epnpns/index.md` | 18 | 0 |
| `knowledge/01-physics-epnpns/09-source-files.md` | 140 | 273 | live | Physics | generated | `knowledge/01-physics-epnpns/index.md` | 5 | 0 |
| `knowledge/01-physics-epnpns/index.md` | 172 | 347 | live |  | generated | `SPECIFICATION.md`, `knowledge/index.md` | 20 | 1 |
| `knowledge/02-electrokinetics-background/00-overview.md` | 126 | 299 | live | Overview | generated | `knowledge/02-electrokinetics-background/index.md` | 2 | 0 |
| `knowledge/02-electrokinetics-background/01-the-electrical-double-layer.md` | 384 | 739 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 3 | 0 |
| `knowledge/02-electrokinetics-background/02-poissonboltzmann-and-debyehuckel.md` | 296 | 575 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 3 | 0 |
| `knowledge/02-electrokinetics-background/03-pb-vs-pnp-equilibrium-vs-non-equilibrium.md` | 290 | 499 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 4 | 0 |
| `knowledge/02-electrokinetics-background/04-electro-osmosis.md` | 447 | 798 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 3 | 0 |
| `knowledge/02-electrokinetics-background/05-electrophoresis-and-the-force-on-a.md` | 287 | 480 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 2 | 0 |
| `knowledge/02-electrokinetics-background/06-selectivity-transport-number-reversal.md` | 196 | 351 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 3 | 0 |
| `knowledge/02-electrokinetics-background/07-ionic-current-rectification.md` | 160 | 283 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 7 | 0 |
| `knowledge/02-electrokinetics-background/08-access-resistance-and-conductance.md` | 261 | 437 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 2 | 0 |
| `knowledge/02-electrokinetics-background/09-quantities-the-software-must-compute.md` | 228 | 354 | live | Background | generated | `knowledge/02-electrokinetics-background/index.md` | 3 | 0 |
| `knowledge/02-electrokinetics-background/index.md` | 160 | 381 | live |  | generated | `knowledge/index.md` | 6 | 0 |
| `knowledge/03-nanopore-biology/00-overview.md` | 97 | 214 | live | Overview | generated | `knowledge/03-nanopore-biology/index.md` | 2 | 0 |
| `knowledge/03-nanopore-biology/01-biological-vs-solid-state-nanopores.md` | 328 | 580 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 2 | 0 |
| `knowledge/03-nanopore-biology/02-the-pores-that-appear-in-this-work.md` | 437 | 606 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 3 | 0 |
| `knowledge/03-nanopore-biology/03-clya-in-depth-the-reference-system.md` | 634 | 1041 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 3 | 0 |
| `knowledge/03-nanopore-biology/04-the-lipid-bilayer.md` | 229 | 427 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 2 | 0 |
| `knowledge/03-nanopore-biology/05-single-channel-electrophysiology.md` | 427 | 754 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 2 | 0 |
| `knowledge/03-nanopore-biology/06-what-nanopores-are-used-for.md` | 116 | 195 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 2 | 0 |
| `knowledge/03-nanopore-biology/07-why-accurate-modelling-matters-for-pore.md` | 181 | 341 | live | Domain | generated | `knowledge/03-nanopore-biology/index.md` | 4 | 0 |
| `knowledge/03-nanopore-biology/08-glossary.md` | 411 | 635 | live | Glossary | generated | `knowledge/03-nanopore-biology/index.md` | 6 | 0 |
| `knowledge/03-nanopore-biology/index.md` | 156 | 315 | live |  | generated | `knowledge/index.md` | 6 | 0 |
| `knowledge/04-clya-geometry-and-charge/00-overview.md` | 165 | 351 | live | Overview | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 1 | 0 |
| `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md` | 4473 | 7502 | live | Pipeline | generated | `docs/plans/phase-2/phase-2-geometry-pipeline.md`, `knowledge/04-clya-geometry-and-charge/index.md` | 26 | 3 |
| `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md` | 1329 | 2518 | live | Pipeline | generated | `docs/plans/phase-2/phase-2-geometry-pipeline.md`, `knowledge/04-clya-geometry-and-charge/index.md` | 9 | 2 |
| `knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md` | 1946 | 3195 | live | Pipeline | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 20 | 2 |
| `knowledge/04-clya-geometry-and-charge/04-mesh.md` | 338 | 625 | live | Pipeline | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 7 | 0 |
| `knowledge/04-clya-geometry-and-charge/05-solver-and-sweeps.md` | 202 | 360 | live | Pipeline | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 1 | 0 |
| `knowledge/04-clya-geometry-and-charge/06-validation-targets.md` | 1170 | 1484 | live | Pipeline | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 7 | 0 |
| `knowledge/04-clya-geometry-and-charge/07-stated-limitations-and-caveats.md` | 220 | 364 | live | Pipeline | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 1 | 0 |
| `knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md` | 983 | 1569 | live | Open Item | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 13 | 1 |
| `knowledge/04-clya-geometry-and-charge/09-tier-1-test-evidence-contours-and.md` | 694 | 1905 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 3 | 0 |
| `knowledge/04-clya-geometry-and-charge/10-tier-1-test-evidence-the-derived.md` | 104 | 243 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 5 | 0 |
| `knowledge/04-clya-geometry-and-charge/11-tier-1-test-evidence-the-val-05-harness.md` | 283 | 708 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 4 | 0 |
| `knowledge/04-clya-geometry-and-charge/12-tier-2-test-evidence-quadrature-gates.md` | 628 | 1507 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 5 | 0 |
| `knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md` | 290 | 597 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 8 | 1 |
| `knowledge/04-clya-geometry-and-charge/14-pdb2pqrs-residue-and-hydrogen-names-and-the-protonated-density.md` | 335 | 613 | live | Test Evidence | generated | `knowledge/04-clya-geometry-and-charge/index.md` | 7 | 0 |
| `knowledge/04-clya-geometry-and-charge/index.md` | 378 | 731 | live |  | generated | `knowledge/index.md` | 14 | 0 |
| `knowledge/05-analyte-and-forces/00-overview.md` | 123 | 281 | live | Overview | generated | `knowledge/05-analyte-and-forces/index.md` | 1 | 0 |
| `knowledge/05-analyte-and-forces/01-read-this-first-the-acs-nano-2019-work.md` | 267 | 448 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 2 | 0 |
| `knowledge/05-analyte-and-forces/02-analyte-geometry-apbs-bead-model.md` | 329 | 502 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 1 | 0 |
| `knowledge/05-analyte-and-forces/03-charge-representation-both-forms-and.md` | 346 | 557 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 1 | 0 |
| `knowledge/05-analyte-and-forces/04-dielectric-constant-and-boundary.md` | 201 | 334 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 1 | 1 |
| `knowledge/05-analyte-and-forces/05-force-computation-the-analytic-model.md` | 481 | 866 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 6 | 0 |
| `knowledge/05-analyte-and-forces/06-from-energy-landscape-to-rates-no.md` | 242 | 444 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 2 | 0 |
| `knowledge/05-analyte-and-forces/07-electro-osmosis-vs-electrophoresis.md` | 158 | 249 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 2 | 0 |
| `knowledge/05-analyte-and-forces/08-validation-targets.md` | 547 | 730 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 5 | 0 |
| `knowledge/05-analyte-and-forces/09-stated-limitations-and-off-axis.md` | 216 | 417 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 1 | 0 |
| `knowledge/05-analyte-and-forces/10-gaps-and-ambiguities.md` | 678 | 1314 | live | Open Item | generated | `knowledge/05-analyte-and-forces/index.md` | 4 | 0 |
| `knowledge/05-analyte-and-forces/11-correction-continuum-force-computation.md` | 1646 | 2593 | live | Domain | generated | `knowledge/05-analyte-and-forces/index.md` | 7 | 1 |
| `knowledge/05-analyte-and-forces/12-tier-1-test-evidence-analyte-bodies.md` | 155 | 452 | live | Test Evidence | generated | `knowledge/05-analyte-and-forces/index.md` | 4 | 0 |
| `knowledge/05-analyte-and-forces/13-tier-2-test-evidence-electro-osmosis.md` | 594 | 1496 | live | Test Evidence | generated | `knowledge/05-analyte-and-forces/index.md` | 6 | 0 |
| `knowledge/05-analyte-and-forces/index.md` | 292 | 587 | live |  | generated | `knowledge/index.md` | 4 | 0 |
| `knowledge/06-numerics-fem/00-overview.md` | 86 | 176 | live | Overview | generated | `knowledge/06-numerics-fem/index.md` | 3 | 0 |
| `knowledge/06-numerics-fem/01-discretisation.md` | 145 | 241 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 5 | 0 |
| `knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md` | 1082 | 1953 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 16 | 1 |
| `knowledge/06-numerics-fem/03-nondimensionalisation.md` | 195 | 269 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 6 | 0 |
| `knowledge/06-numerics-fem/04-stabilisation.md` | 3147 | 5534 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 17 | 1 |
| `knowledge/06-numerics-fem/05-nonlinear-solution.md` | 1893 | 3351 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 14 | 0 |
| `knowledge/06-numerics-fem/06-linear-solvers.md` | 619 | 1043 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 9 | 0 |
| `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md` | 3165 | 5661 | live | Numerics | generated | `knowledge/06-numerics-fem/index.md` | 18 | 2 |
| `knowledge/06-numerics-fem/08-mesh-resolution-and-adaptivity.md` | 1085 | 1890 | live | Numerics | generated | `docs/plans/phase-2/phase-2-geometry-pipeline.md`, `knowledge/06-numerics-fem/index.md` | 12 | 0 |
| `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` | 7875 | 16118 | live | Library Behaviour | generated | `knowledge/06-numerics-fem/index.md` | 26 | 4 |
| `knowledge/06-numerics-fem/10-unverified-to-measure.md` | 76 | 132 | live | Open Item | generated | `knowledge/06-numerics-fem/index.md` | 4 | 0 |
| `knowledge/06-numerics-fem/11-tier-1-test-evidence-norms-and-the.md` | 267 | 601 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 2 | 0 |
| `knowledge/06-numerics-fem/12-tier-1-test-evidence-the-langevin.md` | 111 | 251 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 6 | 0 |
| `knowledge/06-numerics-fem/13-tier-1-test-evidence-the-domain.md` | 225 | 629 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 3 | 0 |
| `knowledge/06-numerics-fem/14-tier-1-test-evidence-newtons.md` | 372 | 998 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 6 | 0 |
| `knowledge/06-numerics-fem/15-tier-1-test-evidence-scaling-the-wall.md` | 834 | 2168 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 5 | 0 |
| `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md` | 847 | 2054 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 5 | 1 |
| `knowledge/06-numerics-fem/17-tier-3-test-evidence-the-mesh-geometry.md` | 202 | 474 | live | Test Evidence | generated | `knowledge/06-numerics-fem/index.md` | 7 | 1 |
| `knowledge/06-numerics-fem/index.md` | 420 | 810 | live |  | generated | `knowledge/index.md` | 13 | 1 |
| `knowledge/07-software-stack/00-overview.md` | 78 | 146 | live | Overview | generated | `knowledge/07-software-stack/index.md` | 1 | 0 |
| `knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md` | 711 | 1370 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 12 | 0 |
| `knowledge/07-software-stack/02-structure-trajectory-and-density.md` | 3046 | 5412 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 15 | 2 |
| `knowledge/07-software-stack/03-charge-and-electrostatics.md` | 3491 | 5895 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 17 | 6 |
| `knowledge/07-software-stack/04-geometry-meshing-and-io.md` | 2807 | 5268 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 17 | 1 |
| `knowledge/07-software-stack/05-gui-and-packaging.md` | 4242 | 7872 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 27 | 0 |
| `knowledge/07-software-stack/06-licence-summary.md` | 183 | 379 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/07-local-assets.md` | 138 | 284 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md` | 759 | 1338 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 11 | 0 |
| `knowledge/07-software-stack/09-the-clis-import-budget-measured.md` | 304 | 674 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/10-canonical-is-the-on-disk-format-not.md` | 265 | 541 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 4 | 0 |
| `knowledge/07-software-stack/11-a-stages-workspace-falls-back-to-the.md` | 184 | 397 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md` | 1865 | 3117 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 18 | 0 |
| `knowledge/07-software-stack/13-documentation-tooling-mkdocs-material.md` | 507 | 940 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/14-a-windows-checkout-rewrites-the-bytes-a.md` | 213 | 415 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 5 | 0 |
| `knowledge/07-software-stack/15-an-npz-is-reproducible-bytes-only-if.md` | 362 | 710 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 7 | 0 |
| `knowledge/07-software-stack/16-ngsolves-bundled-stubs-cannot-type.md` | 149 | 284 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 3 | 0 |
| `knowledge/07-software-stack/17-tier-1-test-evidence-the-viewer-and-the.md` | 181 | 372 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 6 | 0 |
| `knowledge/07-software-stack/18-tier-1-test-evidence-the-mesh-seam-and.md` | 131 | 340 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 2 | 0 |
| `knowledge/07-software-stack/19-tier-1-test-evidence-stores-paths-occ.md` | 340 | 810 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 6 | 0 |
| `knowledge/07-software-stack/20-tier-1-test-evidence-import-costs.md` | 366 | 915 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 10 | 0 |
| `knowledge/07-software-stack/21-tier-2-test-evidence-budgets-timings.md` | 400 | 1003 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 5 | 0 |
| `knowledge/07-software-stack/22-tier-2-test-evidence-analytic.md` | 3227 | 7992 | live | Test Evidence | generated | `knowledge/07-software-stack/index.md` | 6 | 0 |
| `knowledge/07-software-stack/23-pinning-a-protonation-state-through-apply-pka-values.md` | 406 | 758 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 8 | 0 |
| `knowledge/07-software-stack/24-pint-with-a-fraction-registry-exact-units.md` | 334 | 615 | live | Library Behaviour | generated | `knowledge/07-software-stack/index.md` | 9 | 0 |
| `knowledge/07-software-stack/index.md` | 618 | 1176 | live |  | generated | `knowledge/index.md` | 11 | 4 |
| `knowledge/08-validation-benchmarks/00-overview.md` | 88 | 155 | live | Overview | generated | `knowledge/08-validation-benchmarks/index.md` | 4 | 0 |
| `knowledge/08-validation-benchmarks/01-tier-1-unit-and-property-tests-seconds.md` | 296 | 665 | live | Benchmark | generated | `knowledge/08-validation-benchmarks/index.md` | 3 | 0 |
| `knowledge/08-validation-benchmarks/02-tier-2-analytic-benchmarks-minutes.md` | 790 | 1492 | live | Benchmark | generated | `knowledge/08-validation-benchmarks/index.md` | 7 | 0 |
| `knowledge/08-validation-benchmarks/03-tier-3-comsol-differential-tests-hours.md` | 1248 | 2418 | live | Benchmark | generated | `knowledge/08-validation-benchmarks/index.md` | 8 | 0 |
| `knowledge/08-validation-benchmarks/04-tier-4-experimental-reproduction.md` | 269 | 503 | live | Benchmark | generated | `knowledge/08-validation-benchmarks/index.md` | 1 | 0 |
| `knowledge/08-validation-benchmarks/05-continuous-integration.md` | 82 | 136 | live | Benchmark | generated | `knowledge/08-validation-benchmarks/index.md` | 4 | 0 |
| `knowledge/08-validation-benchmarks/06-tier-1-test-evidence-apbs-maps-golden.md` | 198 | 522 | live | Test Evidence | generated | `knowledge/08-validation-benchmarks/index.md` | 3 | 0 |
| `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md` | 340 | 781 | live | Test Evidence | generated | `knowledge/08-validation-benchmarks/index.md` | 7 | 0 |
| `knowledge/08-validation-benchmarks/index.md` | 177 | 351 | live |  | generated | `knowledge/index.md` | 7 | 0 |
| `knowledge/09-comsol-reference-settings/00-overview.md` | 291 | 521 | live | Overview | generated | `knowledge/09-comsol-reference-settings/index.md` | 4 | 0 |
| `knowledge/09-comsol-reference-settings/01-document-map.md` | 193 | 273 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 2 | 0 |
| `knowledge/09-comsol-reference-settings/02-mesh-27.md` | 486 | 743 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 11 | 1 |
| `knowledge/09-comsol-reference-settings/03-solver-3-4.md` | 637 | 981 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 10 | 0 |
| `knowledge/09-comsol-reference-settings/04-physics-settings.md` | 1935 | 3491 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 9 | 2 |
| `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md` | 491 | 998 | live | Erratum | generated | `knowledge/09-comsol-reference-settings/index.md` | 10 | 0 |
| `knowledge/09-comsol-reference-settings/06-what-we-must-replicate-for-a-like-for.md` | 473 | 710 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 1 | 0 |
| `knowledge/09-comsol-reference-settings/07-differences-that-cannot-be-removed.md` | 319 | 515 | live | Reference Settings | generated | `knowledge/09-comsol-reference-settings/index.md` | 5 | 2 |
| `knowledge/09-comsol-reference-settings/index.md` | 138 | 271 | live |  | generated | `knowledge/index.md` | 9 | 1 |
| `knowledge/index.md` | 201 | 436 | live |  | generated | `README.md` | 24 | 0 |
| `knowledge/log.md` | 2084 | 4342 | live |  | generated | — | 38 | 0 |
| `specification/01-introduction.md` | 672 | 1093 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 5 | 0 |
| `specification/02-product-overview.md` | 1666 | 2574 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 12 | 0 |
| `specification/03-requirements.md` | 6568 | 10007 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 22 | 1 |
| `specification/04-physics.md` | 6916 | 10132 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 19 | 0 |
| `specification/05-software-design/01-architectural-overview.md` | 443 | 852 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 7 | 0 |
| `specification/05-software-design/02-pipeline-stages.md` | 6206 | 9207 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 17 | 0 |
| `specification/05-software-design/03-1-case-file.md` | 11319 | 17838 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 18 | 0 |
| `specification/05-software-design/03-2-artefacts.md` | 2531 | 3861 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 8 | 0 |
| `specification/05-software-design/03-3-provenance-manifest.md` | 485 | 770 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 7 | 0 |
| `specification/05-software-design/03-4-sweeps.md` | 1411 | 2075 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 7 | 0 |
| `specification/05-software-design/04-component-design.md` | 749 | 1217 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 8 | 0 |
| `specification/05-software-design/05-extension-points.md` | 1085 | 1735 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 6 | 0 |
| `specification/05-software-design/06-architecture-decisions.md` | 2273 | 3701 | live | Specification | generated | `SPECIFICATION.md`, `specification/05-software-design/index.md` | 10 | 0 |
| `specification/05-software-design/index.md` | 218 | 413 | live |  | generated | `SPECIFICATION.md`, `specification/index.md` | 2 | 0 |
| `specification/06-numerics.md` | 7197 | 10631 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 13 | 0 |
| `specification/07-verification/01-strategy.md` | 513 | 738 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 10 | 0 |
| `specification/07-verification/02-tier-1.md` | 12252 | 18464 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 13 | 0 |
| `specification/07-verification/03-tier-2.md` | 3021 | 4494 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 12 | 0 |
| `specification/07-verification/04-tier-3.md` | 3077 | 4683 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 8 | 0 |
| `specification/07-verification/05-tier-4.md` | 466 | 742 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 8 | 0 |
| `specification/07-verification/06-continuous-integration.md` | 910 | 1288 | live | Specification | generated | `SPECIFICATION.md`, `specification/07-verification/index.md` | 8 | 0 |
| `specification/07-verification/index.md` | 191 | 352 | live |  | generated | `SPECIFICATION.md`, `specification/index.md` | 4 | 0 |
| `specification/08-implementation-plan/01-phases-and-gates.md` | 1395 | 2080 | live | Specification | generated | `SPECIFICATION.md`, `specification/08-implementation-plan/index.md` | 9 | 0 |
| `specification/08-implementation-plan/02-rulings.md` | 68 | 103 | live | Specification | generated | `SPECIFICATION.md`, `specification/08-implementation-plan/index.md` | 6 | 0 |
| `specification/08-implementation-plan/03-effort-estimate.md` | 441 | 695 | live | Specification | generated | `SPECIFICATION.md`, `specification/08-implementation-plan/index.md` | 4 | 0 |
| `specification/08-implementation-plan/04-development-process.md` | 2070 | 3110 | live | Process | generated | `SPECIFICATION.md`, `specification/08-implementation-plan/index.md` | 17 | 0 |
| `specification/08-implementation-plan/index.md` | 111 | 181 | live |  | generated | `SPECIFICATION.md`, `specification/index.md` | 5 | 0 |
| `specification/09-risks.md` | 1255 | 1877 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 9 | 0 |
| `specification/10-open-items.md` | 1101 | 1820 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 12 | 0 |
| `specification/11-companion-knowledge-base.md` | 399 | 736 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 8 | 0 |
| `specification/12-references.md` | 516 | 1185 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 6 | 0 |
| `specification/a-traceability-matrix.md` | 2677 | 4547 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 13 | 0 |
| `specification/b-comsol-settings.md` | 411 | 635 | live | Specification | generated | `SPECIFICATION.md`, `specification/index.md` | 7 | 0 |
| `specification/history/00-phase-0-exit-criteria.md` | 190 | 295 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/01-amendments-to-phase-0-agreed-19-august-2026.md` | 549 | 849 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/02-phase-2-decisions-agreed-24-september-2026.md` | 811 | 1162 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/03-phase-1-exit-agreed-24-september-2026.md` | 346 | 523 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/04-phase-2-exit-and-phase-3-decisions-agreed-30-septe.md` | 918 | 1318 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/05-phase-3-exit-and-the-phase-4-release-agreed-3-octo.md` | 711 | 1037 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/06-phases-4-to-6-re-planned-agreed-4-october-2026.md` | 1149 | 1746 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/07-phase-4-decisions-agreed-5-october-2026.md` | 1454 | 2158 | record | Ruling Record | generated | `specification/history/index.md` | 5 | 0 |
| `specification/history/08-phase-4-rulings-on-the-modularity-report-agreed-5.md` | 1655 | 2531 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/09-phase-4-amended-the-review-register-planned-agreed.md` | 846 | 1231 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/10-phase-4-amended-the-development-loop-agreed-11-oct.md` | 1835 | 2680 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/11-phase-4-amended-the-development-loop-simplified-ag.md` | 1433 | 2072 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/12-phase-4-amended-the-architecture-review-checked-ag.md` | 784 | 1183 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/13-phase-4-amended-the-test-scope-agreed-18-october-2.md` | 806 | 1248 | record | Ruling Record | generated | `specification/history/index.md` | 4 | 0 |
| `specification/history/14-phase-4-amended-the-plotting-library-and-the-noteb.md` | 1508 | 2330 | record | Ruling Record | generated | `specification/history/index.md` | 4 | 0 |
| `specification/history/15-the-work-package-plan-grounded-in-the-code-agreed.md` | 338 | 485 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/16-phase-4-amended-the-specification-and-the-workflow.md` | 1691 | 2482 | record | Ruling Record | generated | `specification/history/index.md` | 5 | 0 |
| `specification/history/17-phase-5-decisions-ahead-of-phase-4s-exit-agreed.md` | 2813 | 4203 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/18-the-workbench-design-studys-rulings-agreed-27-oct.md` | 774 | 1136 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/19-the-workbench-design-studys-open-items-agreed-27.md` | 753 | 1108 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/20-wp54s-notebooks-and-figures-agreed-28-october-2.md` | 1796 | 2580 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/21-phase-4-amended-the-user-testing-findings-ruled.md` | 1143 | 1602 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/22-phase-4-amended-the-geometry-split-and-wp57-wide.md` | 1018 | 1483 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/23-phase-4-amended-the-python-interface-rebuilt-on-a.md` | 1130 | 1714 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/24-phase-4-amended-the-final-packages-and-the-close.md` | 938 | 1380 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/25-the-workflow-on-the-github-copilot-app.md` | 934 | 1407 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/26-copilot-hook-refusal.md` | 164 | 249 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/27-phase-4-amended-the-architecture-reviews-fixes.md` | 875 | 1311 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/28-phase-5-amended-the-library-packages.md` | 613 | 926 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/29-wp59-review-items.md` | 545 | 795 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/30-wp502s-plan-the-spike-and-the-desktop-wrapper.md` | 789 | 1155 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/31-phase-5-amended-the-shell-packages-and-the-sweep.md` | 1997 | 2968 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/32-wp506s-plan-what-an-output-needs-of-a-model.md` | 351 | 549 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/33-wp508s-plan-a-users-colour-themes.md` | 2178 | 3120 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/34-phase-5-amended-the-frame-the-physics-model-and-the-design-loop.md` | 1732 | 2602 | record | Ruling Record | generated | `specification/history/index.md` | 3 | 0 |
| `specification/history/35-wp509s-plan-the-physics-models-boundaries-and-exposed-values.md` | 587 | 908 | record | Ruling Record | generated | `specification/history/index.md` | 2 | 0 |
| `specification/history/index.md` | 4025 | 5764 | record |  | generated | `SPECIFICATION.md`, `specification/index.md` | 22 | 0 |
| `specification/index.md` | 401 | 768 | live |  | generated | `SPECIFICATION.md` | 13 | 0 |

## Totals by folder

| Folder | Files | Words | Tokens |
|---|---|---|---|
| `(root)` | 6 | 32980 | 57417 |
| `.claude/agents` | 3 | 509 | 803 |
| `.claude/hooks` | 3 | 5145 | 9090 |
| `.claude/rules` | 2 | 678 | 1177 |
| `.claude/scripts` | 3 | 1943 | 4399 |
| `.claude/skills` | 19 | 11461 | 17454 |
| `.claude/workflow` | 3 | 2821 | 4356 |
| `docs/code_reviews` | 41 | 71181 | 129818 |
| `docs/design` | 11 | 21790 | 31204 |
| `docs/examples` | 1 | 413 | 652 |
| `docs/getting-started.md` | 1 | 517 | 893 |
| `docs/guide` | 16 | 14702 | 23386 |
| `docs/index.md` | 1 | 501 | 881 |
| `docs/model` | 1 | 504 | 935 |
| `docs/plans` | 82 | 362522 | 595443 |
| `docs/project` | 9 | 42682 | 75788 |
| `docs/reference` | 2 | 463 | 831 |
| `docs/superpowers` | 2 | 3729 | 5958 |
| `docs/sweeps` | 1 | 333 | 516 |
| `docs/user-testing` | 7 | 6713 | 12213 |
| `docs/validation` | 1 | 1647 | 2724 |
| `knowledge/00-orientation` | 9 | 4008 | 7520 |
| `knowledge/01-physics-epnpns` | 11 | 4118 | 6944 |
| `knowledge/02-electrokinetics-background` | 11 | 2835 | 5196 |
| `knowledge/03-nanopore-biology` | 10 | 3016 | 5108 |
| `knowledge/04-clya-geometry-and-charge` | 16 | 13538 | 24272 |
| `knowledge/05-analyte-and-forces` | 15 | 6275 | 11270 |
| `knowledge/06-numerics-fem` | 19 | 22646 | 44353 |
| `knowledge/07-software-stack` | 26 | 25307 | 49023 |
| `knowledge/08-validation-benchmarks` | 9 | 3488 | 7023 |
| `knowledge/09-comsol-reference-settings` | 9 | 4963 | 8503 |
| `knowledge/index.md` | 1 | 201 | 436 |
| `knowledge/log.md` | 1 | 2084 | 4342 |
| `specification/01-introduction.md` | 1 | 672 | 1093 |
| `specification/02-product-overview.md` | 1 | 1666 | 2574 |
| `specification/03-requirements.md` | 1 | 6568 | 10007 |
| `specification/04-physics.md` | 1 | 6916 | 10132 |
| `specification/05-software-design` | 10 | 26720 | 41669 |
| `specification/06-numerics.md` | 1 | 7197 | 10631 |
| `specification/07-verification` | 7 | 20430 | 30761 |
| `specification/08-implementation-plan` | 5 | 4085 | 6169 |
| `specification/09-risks.md` | 1 | 1255 | 1877 |
| `specification/10-open-items.md` | 1 | 1101 | 1820 |
| `specification/11-companion-knowledge-base.md` | 1 | 399 | 736 |
| `specification/12-references.md` | 1 | 516 | 1185 |
| `specification/a-traceability-matrix.md` | 1 | 2677 | 4547 |
| `specification/b-comsol-settings.md` | 1 | 411 | 635 |
| `specification/history` | 37 | 42179 | 62290 |
| `specification/index.md` | 1 | 401 | 768 |
| **all** | 423 | 798906 | 1336822 |

## Files no other Markdown links to or names (2)

- `docs/code_reviews/index.md` (record)
- `docs/plans/index.md` (record)
