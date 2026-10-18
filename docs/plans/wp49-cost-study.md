# WP49 — The cost study

PR: [#107](https://github.com/willemsk/nanopnp/pull/107), branch claude/wp-implement-49-oejjuz

**Status: delivered, 18 October 2026.** Inherits WP48 as shipped (the OKF backfill,
PR #104), the Phase 4 amendment of 18 October 2026 (§8.2.12 M1 to M5) and the thresholds that
amendment registered.

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase; its WP49 threshold table is
this package's contract, re-argued only by a phase amendment before measuring. `SPECIFICATION.md`
governs; identifiers are pointers.

## In brief

An outside review guessed that three parts of the program waste memory or time; nobody has
measured them. This package measures all three on two standard cases and fixes a part only if it
crosses a limit written down before measuring. It also publishes the case-file format in a
standard machine-readable form.

**What changes.** Three numbers settle the question, saved with the script that produced them. The
format description goes into the documentation, and a check fails if it and the program's own list
of settings disagree.

**Cost.** About a day of machine time. Six to eight commits.

**What could go wrong.** A fix could change a computed result. The existing record of results
catches a change in the eighth digit, and such a fix is undone. A measurement could flatter the
program, so the timers count generously. A fix too big for one package is registered for a later ruling.

**Your call.** Should the format description also come with the program, through a command, as
well as in the documentation? *Recommendation:* documentation only for now; the browser page can
ask the program directly when it is built.

## Execution brief

Scope: measure A1, A8 and A16 against the registered thresholds (4 GB, 5 %, 10 %), fix only a cost
over its threshold, and export the case schema as JSON Schema with proposed **VER-76**. It sets
REV-112 and REV-113 `fixed` (§8.2.12 M2). Depends on WP48 merged. Constraints: VER-62 at 10⁻⁸, a miss
reverted (G10); a new import edge edits `docs/project/modularity-layering.yaml` (VER-61); stages
stay independently invocable (FR-27). Models: Sonnet by default, Haiku for items 7 and 8.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Harness | `src/nanopnp/validation/costs.py`, run as `uv run python -m nanopnp.validation.costs <a1\|a8\|a16\|all>`. Timing wraps callables named in the module; no production code changes. A nested call of one category counts once. Output: `docs/project/cost-study.json`, with CPU count, thread variables, versions and commit | Phase plan: a committed script the close re-runs; `validation/`'s edges to `pipeline`, `io`, `solve` exist |
| D2 A1, ensemble memory | The prepared 2WCD as a synthetic DCD of 16, 32 and 64 rigidly jittered frames (alignment does real work). Stage 1 alone in a fresh subprocess per count; peak is `ru_maxrss`. The least-squares line at 1,000 frames is compared with 4 GB. Stage 2's peak is recorded, not gated | Registered on stage 1. The float64 read plus float32 copy (`structure/read.py`, `structure/stage.py`) put the 1 GB prediction in doubt |
| D3 A8, forms per rung | "Both ladders": the one each walk climbs, quick-start and 2WCD. Build time: `BilinearForm(space)` construction, each model's `residual_form`, `create`/`with_switches` and the ladder's CFs; never assembly, linearisation, factorisation or solves. Share = build over stage 10's wall time, against 5 % per ladder. A stage-10 total more than 2 % off `StageRecord`'s seconds invalidates the run | Build defined generously, so the share cannot under-report |
| D4 A16, store traffic | A cold walk (empty store, fresh process) of each case. IO: `io/store.py` (`get`, `put`, `get_or_compute` minus `compute`), each payload type's write and read (listed in D1's module), `np.savez`/`np.load`, mesh read and write. Share = IO over walk wall time, against 10 %, split into writes and reads | The registered measure; the fix removes only reads |
| D5 A fix, if any | One item per cost over its threshold, the phase plan's fix. A1: frame-by-frame align and write, payload digest and key byte-identical. A8: forms once per mesh, rung scales as `ngs.Parameter`. A16: in-memory hand-off, store still written. Each passes VER-62 at 10⁻⁸ and re-runs its leg under threshold; one too large for the PR becomes a `REV-nn` row | §8.2.12 M2; G10 |
| D6 VER-76, JSON Schema | `case_json_schema()` in `io/case_paths.py` returns `CaseDocument.model_json_schema(by_alias=True, mode="validation")`. `schema_leaves(schema)` mirrors `case_fields`: resolve `$ref`; descend `properties`; in `anyOf`, the first object branch (as `_model_of`); array of objects → `.0.`; `additionalProperties` of objects refused (mapping of blocks); else a leaf. VER-76: set equality both ways. The docs build writes `reference/case.schema.json`, linked from the case-file page; not in the CLI | §8.2.12 M2; REV-113 |

### Work items

- [x] 3bc1e16 1. `src/nanopnp/validation/costs.py` holds the harness skeleton (D1): the category timers with their nesting guard, the record writer and the linear projection, with no measurement yet. `tests/tier1/test_cost_study.py` is its tests. Done when the D1 rows of *Verification* pass.
- [x] 3bc1e16 2. The A1 leg (D2): a synthetic-trajectory writer and the subprocess runs. Done when `costs a1` writes its block and the A1 Tier-1 rows pass.
- [x] 1db058a 3. The A8 leg (D3). Done when `costs a8` writes both ladders' shares and the 2 % consistency check holds.
- [x] 1db058a 4. The A16 leg (D4). Run `costs all` and commit `docs/project/cost-study.json`. The *Outcome* quotes each cost, its threshold, its prediction and its verdict.

  > **Outcome — all three costs are under their thresholds** (`docs/project/cost-study.json`, four-core
  > container, stabilisation unchanged). **A1:** stage 1 peaks at 158, 172 and 207 MB for 16, 32 and 64
  > frames and projects to 1.14 GB at 1,000 frames against 4 GB (prediction about 1 GB; not over). Stage 2
  > projects to 0.81 GB, recorded. **A8:** building symbolic forms is 0.02 % of stage 10 on the 2WCD
  > (0.036 s of 213 s) and 0.33 % on the quick-start pore, against 5 % (prediction under 1 %; met). **A16:**
  > store IO is 0.51 % of the cold 2WCD walk (writes 0.50 %, reads 0.01 %) and 0.10 % of the quick-start
  > walk, against 10 % (prediction under 5 %; met). The stage totals agree with `StageRecord` within 2 %.

*Compaction checkpoint: after item 4; resume from this plan, `docs/project/cost-study.json` and `git log`.*

- [x] none 5. Fixes (D5): one commit for each cost over its threshold, in the file the phase plan names. If no cost is over, this item's *Outcome* says so and nothing changes. Done when VER-62 passes at 10⁻⁸ and the harness leg, re-run, is under its threshold, or a `REV-nn` row records the carried cost.

  > **Outcome — nothing is fixed.** No cost is over its threshold (item 4), so no code path of the
  > program changes, VER-62 is untouched and no `REV-nn` row carries a cost (M2).
- [x] fb4801f 6. VER-76 (D6): `case_json_schema` and `schema_leaves` in `src/nanopnp/io/case_paths.py`; `tests/tier1/test_case_json_schema.py`; a VER-76 row in Appendix A of `SPECIFICATION.md`. Done when the VER-76 rows pass.
- [x] 4deb53e 7. `docs/scripts/generate.py` writes `reference/case.schema.json`, and a link to it goes into the generated case-file reference. Add a `CHANGELOG.md` *Added* line. Done when the documentation build passes `--strict` and the file parses as JSON.
- [x] 74d6066 8. Close: set REV-112 and REV-113 `fixed` in `docs/project/review-findings.md` and `review-items.md`, with the measured numbers. Mark this plan *delivered*, update the phase plan's *Delivered* line and replace `docs/plans/current.md`. Done when `test_plan_shape.py` and `test_plan_records.py` pass.
- [x] cc58ca1 9. Added at the author's request: main's CI failed on macOS and Windows, whose ngsolve
  wheels ship no `__init__.pyi`; the stub check runs only where it ships (VER-72).

### Verification

| Test | Tier | Identifier | Oracle and tolerance |
|---|---|---|---|
| `test_cost_study.py::test_a_nested_call_of_one_category_counts_once` | 1 | REV-112 | Two nested sleeping callables: the category total is the outer call's time and is less than the sum |
| `::test_every_named_callable_resolves` | 1 | REV-112 | Each dotted name in each of A8's and A16's lists imports to a callable, so a renamed function fails |
| `::test_the_projection_is_the_least_squares_line` | 1 | REV-112 | Three exact points on a known line project to its value at 1,000 frames, within 10⁻⁹ |
| `::test_the_record_carries_the_environment` | 1 | REV-112 | The JSON keys for CPU count, thread variables, versions and commit are present and non-empty |
| `::test_a8_refuses_a_stage_total_off_by_more_than_two_percent` | 1 | REV-112 | A fabricated record that is 3 % off is refused, and one that is 1 % off is accepted |
| `test_case_json_schema.py::test_ver76_schema_leaves_equal_case_fields` | 1 | VER-76 | Set equality of `schema_leaves(case_json_schema())` with the paths of `case_fields()` |
| `::test_ver76_an_extra_schema_leaf_fails` | 1 | VER-76 | A schema with one property added: the extra path is found |
| `::test_ver76_a_missing_schema_leaf_fails` | 1 | VER-76 | A schema with one property removed: the missing path is found |
| `::test_ver76_an_extra_case_field_fails` | 1 | VER-76 | A substituted `case_fields` with an extra leaf fails |
| `::test_ver76_a_mapping_of_blocks_is_refused` | 1 | VER-76 | `additionalProperties` holding an object with properties raises `NotImplementedError` |
| `::test_ver76_lists_unions_and_maps_walk_as_case_fields_does` | 1 | VER-76 | `species.0.*`, `structure.*` reached through `anyOf`, and `groups` and `solid_permittivities` as leaves |
| `::test_ver76_every_literal_leaf_carries_its_choices` | 1 | VER-76 | The schema survives `json.dumps`, and each `Literal` leaf of `case_fields` has an `enum` or a `const` equal to its arguments. No new dependency |
| VER-62 tier-2 walks | 2 | VER-62 | Unchanged; a D5 fix must keep 10⁻⁸ on a recorded mesh |
| VER-61, VER-45 | 1, 2 | — | Kept green; the documentation build is `--strict` |

The measurements are verdicts recorded, not gates (M2). Commands:
`uv run python -m nanopnp.validation.costs all`; the two Tier-1 files; `.claude/hooks/gate.sh run`.

### Out of scope

- A cost under its threshold is not optimised (M2); a missed prediction is reported only.
- Stage 2's memory: recorded (D2), not gated; over 4 GB projected, a `REV-nn` row for WP51 on.
- Using the schema from a browser editor: Phase 5 (M3, REV-114).
- Shipping the schema through the CLI or the wheel: declined here (*Your call*).

### Open questions

None blocking. The *Your call* above has a default, and work goes ahead on it unless the author
rules otherwise.
