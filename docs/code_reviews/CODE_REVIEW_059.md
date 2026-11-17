# Code review 059: WP5.19's plan, the Study suite

2026-11-17 · PR #188, branch `ccr-24fd66d5-2we2o9`, head `e73b685` on base `51059ff` · scope: the plan commit,
`docs/plans/phase-5/wp5.19-the-study-suite.md` with its ruling round (§8.2.42 AR3 to AR5), the phase entry, `current.md`
and the decisions page. Each grounding claim was checked against the code at this head: `gui/web/screens.py`,
`pages.py`, `frame.py`, `builds.py`, `states.py`, `queue.py`, `settings.py`, `link.py`, `plane.py`; `gui/solver.py`,
`run_model.py`, `convergence.py`, `charge.py`, `render.py`; `api/project.py`, `api/sweep.py`, `api/reproduce.py`,
`api/session.py`; `sweep/plan.py`, `sweep/document.py`, `sweep/run.py`; `io/store.py`, `io/models.py`,
`io/case_paths.py`, `io/manifest.py`, `io/resolved.py`; `pipeline/run.py`, `pipeline/checks.py`; `solve/stage.py`,
`solve/continuation.py`; `geometry/region.py`, `geometry/profile.py`; `charge/fields.py`;
`docs/project/modularity-layering.yaml`; NiceGUI 3.18.0's `mermaid` element. Each decision was read against AR3 to
AR5, AP5 and the clauses its verification rows claim (VER-35, VER-36, VER-44, VER-59, VER-60, VER-78), and the plan
against `.claude/skills/np-plan/wp.md`'s sections and caps · level: high, with `--fix` · status: completed.

Static review of a plan: no test and no `gate.sh` ran; the review turn gates afterwards. The other grounding claims hold
at this head, among them `ui.mermaid`'s `on_node_click` since 3.3.0, a spawned solve child that loads neither NumPy
nor NGSolve before its walk, and `Artefact.hash` leaving the solve's summary out of every key (AR3).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | Item 2, `_pairs` | The pairing key, a member's dump without `bias_V` and `variables`, keeps its `name`, which `_member` sets per point: no two points pair and VER-36's row fails | Fixed: `name` left out too; keyed from the resolved members |
| 2 | High | Item 8, `StudyModel` | `BUILD_UPTO["study"]` lets `BuiltModel.build` and `Project.kept_artefacts` call `build_case("study", …)`, which reads the study as a model file under `BUILD_LAYER`; `kind` is typed `ModelKind` | Fixed: `BuiltModel.upto`, `build()` through `self.case()`, `kind` an `ItemKind`; `BUILD_UPTO` gains no row (grounding D1) |
| 3 | High | Item 7, the mesh layer | An element's mean over its area does not keep `∫ρ 2πr dA = q_mesh_e` to 10⁻¹², which VER-60's row asserts | Fixed: the r-weighted mean `∫ρ r dA / ∫ r dA` |
| 4 | Medium | Item 4, the shell's spacing | A repeated vertex records spacing 0; the shell divides by `h_c` and the `2 h_c` check refuses nothing | Fixed: refused at resolve, naming the file; VER-59's row asserts it |
| 5 | Medium | Item 8, the routes | With Study in `TOOL_SUITES`, `pages.ROUTES` reads `VIEWS["study"]`, which is absent; `Route.view`, `VIEWS`, `tool_view` and `tool_controls` do not take `pair` | Fixed: each named, `pair`'s controls `molecule` and `plane` (grounding D1) |
| 6 | Medium | Items 2 and 8 | Item 2 adds the static `gui -> sweep` edge; only item 8 edits the layering file, so item 2's commit fails VER-61 | Fixed: the row in item 2 |
| 7 | Medium | Item 1, the export | Results go to `results/<the report payload's key>`, but `run.json` holds store paths only | Fixed: the path relative to the report artefact's directory (grounding D9) |
| 8 | Medium | Item 8, the graph | `securityLevel: loose` is said to be needed by `on_node_click`; NiceGUI binds its own listener and emits the SVG id, and `loose` renders labels as HTML | Fixed: the default level; a click matched by the id containing `node-<section>` (grounding D3) |
| 9 | Medium | VER-35's row | No fresh store, which VER-35 requires: the store could serve every stage | Fixed: a fresh store, its misses asserted |
| 10 | Medium | D5, D8 | The deployed layer needs a run record, which the boot walk does not write; Runs would list every build's `upto-charge` record | Fixed: the newest `upto-charge` record, else *Build*; Runs lists records that reached `qoi` |
| 11 | Low | Item 2, `threads` | None where the variable is unset states no count, which AR3 asks each record to state | Fixed: FR-25's text says None is the libraries' default, not pinned |
| 12 | Low | Item 4, AR5 | "The smallest shift the gate refuses" is undefined if every shift passes | Fixed: the largest shift measured, which passes |
| 13 | Low | Item 3 | A Sonnet item wrote QR-08's normative NOTE (`wp.md`: normative text stays `main`) | Fixed: the NOTE is main's |
| 14 | Low | Grounding D6 | "No test builds a `ConvergenceModel`": `test_gui_solver_process.py` builds one through `RunModel` | Fixed: no test reads its bands |
| 15 | Low | Item 4 | The knowledge concept lacked its index entry and log line (`CLAUDE.md`, *Durable learnings*) | Fixed |
| 16 | Low | Item 2 | `plan.case(index)` re-validates every member the plan already resolved | Fixed with 1 |
| 17 | Low | D4 | A `models.*` axis value is a file beside the study's folder; the pane's form was unstated | Fixed: `../models/<kind>/<name>.yaml` |
| 18 | Low | Out of scope | REV-41's `prepare` and region export, and their owners, were unnamed | Fixed: FR-37; FR-28, v0.7 |
| 19 | Low | The caps | 1,653 words outside Grounding and Implementation details, over 1,650 | Fixed: 1,650 after the fixes; details 1,041 of 1,100; the plan 3,530 of 3,850 |

Not findings:

- AR3 keys nothing: the solve's summary lies outside `Artefact.hash`, so recording the count moves no VER-62 key.
- `pin_threads(count: int = 1)` stays a valid pool initializer, which passes no argument.
- Eleven decisions against wp.md's guideline of about six: each is a choice the package needs, as the plan's report said.
- Item 2's FR-25 test reads the variable the child set; VER-62's equal keys check that the count moves no result.

## Fixes

| File | Change |
|---|---|
| `docs/plans/phase-5/wp5.19-the-study-suite.md` | Findings 1 to 19 |
