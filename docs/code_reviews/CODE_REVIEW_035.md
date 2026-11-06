# Code review 035: WP5.09's plan, the physics model (§8.2.35)

Reviewed head `6c9e2ec4ecec21c99875cd08ce8d73da63bfd3d7` against `main` (`4de067b`), branch `ccr-55e66f77-s0t613`.
Status: completed. Static review of a plan commit at `medium`, with `--fix`. The plan's claims were checked against
`src/nanopnp/io/models.py` (`OWNERS`, `_read_model_file`, `ModelFile`), `io/case.py` (`Models`, `Numerics`, `Charge`,
`Mesh`), `io/case_paths.py:schema_default`, `io/variables.py:field_unit`, `mesh/sizing.py` (`WallSize.key`,
`resolve_wall_size`), `sweep/forecast.py`, `api/sweep.py:Sweep.forecast`, `io/project.py`, `api/project.py`,
`gui/web/frame.py`, `gui/web/states.py`, `validation/case_leaves.py` and the tests the plan rewrites. Its decisions were
checked against §8.2.34 and §8.2.35 and the amended §5.3.1 NOTE, and the plan against `.claude/skills/np-plan/wp.md`.
No test and no `gate.sh` ran; the review turn gates afterwards. Nine findings, all fixed in the plan. No ruling moved.
The plan holds 2,184 words, 1,357 of them outside the grounding and the details, and the details 423.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | *Work items* 1 to 4 | Items 1 to 3 named tests that item 4 rewrote. The commit hook runs Tier 1, and after item 1 `split_case` and tier 2's `_study` would still write `electrolyte` into a continuum model, which the ownership check then refuses, so item 1 could not commit. | Fixed: the split fixtures move into item 1's commit; items 2 and 3 write their own rows; item 4 holds row 5 alone. |
| 2 | `tests/tier1/test_project.py` (FR-34) | The changed-list test writes a continuum model holding `electrolyte`, `boundary_conditions` and `physics`, and expects `physics.flow` to be the continuum model's. The plan did not name it, so it would fail unplanned. | Fixed: item 1's tests split the fixture into continuum and physics files; row 7 covers it. |
| 3 | *Verification* row 7 | It said a second import reuses three files. The quick-start has no molecular key, and `split_case` writes no empty model, so the split writes two. | Fixed: every file the split wrote, the continuum and physics models. |
| 4 | *Verification* row 5 | The quick-start sets `wall_h_nm: 0.35`, so a split continuum model shares one mesh at every salt; the row also left open how the test builds the sweep. | Fixed: item 4's details set `auto`, write four physics files and read `plan_sweep(...).forecast().builds["mesh"]` against an empty store. |
| 5 | *Implementation details*, item 2 | `exposed_values` read `body.get("exposes")`, but D3 strips `exposes` from the body with `schema` and `name`. | Fixed: it takes the file's whole mapping, before the strip. |
| 6 | *Out of scope* | The amended NOTE says a range guides the suites and the sweep; no package owned the sweep's use. | Fixed: WP5.14, with the Study suite's list. |
| 7 | *Implementation details*, item 2 | `schema_bounds` reads `Gt` and `Ge` alike, so an open bound reads as a closed one, and the plan left the checks' treatment open. | Fixed: an open bound is given as its limit, and a range is checked as closed, since it only guides. |
| 8 | *Implementation details*, item 3 | `ItemKind`, `ITEM_KINDS` and `LIBRARY_FIELDS` were in D4 but not in the item; `Library.names` raises without the last. | Fixed: named in item 3. |
| 9 | *Work items* 6 | Item 1 changes `Models.physics`'s description and `cli/reference.py`, which the generated reference reads; the item ran only `gate.sh`. | Fixed: item 6 runs the strict documentation build too. |
