# WP36 — The stage protocol and the walk

**Status: delivered, 5 October 2026.** Written 5 October 2026, on `ccr-8378e74e-taeua5` at `e987c8d`,
after WP35 merged as `v0.5.0-alpha.1` and the author ruled every `MOD-nn` (§8.2.8). It inherits
everything the [current brief](current.md) lists as not to be re-decided. In particular it inherits
the stage registry of `core/stages.py` with VER-25's introspection rule, the walk of `io/run.py`,
VER-61's recorded layering and VER-62's golden, both of which it must keep green.

This is the second work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md), and it
discharges `MOD-01`, `MOD-02` and `MOD-12` (§8.2.8 H1, H8). `SPECIFICATION.md` governs, and the
identifiers below are pointers into it. **No spec amendment is made in this commit.** VER-64 is
claimed by `/wp-implement`, with its §7.2 row, its Appendix A entry under FR-27 and VER-25's added
clause, in the commit that implements it, as WP35 claimed VER-61 to VER-63.

## Execution brief

### Scope

Three findings, one PR:

- **`MOD-01`.** `key(inputs)` joins the `Stage` protocol. `MaterialsStage` and `CaseStage` define
  it, and the two `# type: ignore[attr-defined]` calls go (`validation/comsol.py:439`,
  `gui/assess.py:337`).
- **`MOD-02`.** The per-stage facts the walk holds move into the registry's `StageDescription`.
  `io/run.py` derives the walk order, the payload-free stages, the workspace and store stages, the
  structure stages and the progress weights from it. `selected_stages`' drop rules stay, as case
  logic.
- **`MOD-12`.** `test_public_api.py` asserts that `PUBLIC` equals its `TYPE_CHECKING` mirror.

**Break** (F4; `CHANGELOG.md`): `nanopnp.Stage` gains `key`, so a stage written outside the package
must define it. Additive: `registered_stages()` descriptions and `stage --list --json` gain five
fields. Internal (IF-01; listed for whoever imported them): `io.run`'s `PIPELINE`, `PAYLOAD_FREE`,
`STRUCTURE_STAGES`, `WORKSPACE_STAGES` and `STORE_STAGES` go, replaced by `core.stages.walk_order()`
and the description's facts, and `register()` refuses what D5 lists.

Pointers: FR-27, IF-01 (§3.1 NOTE), §5.2, §5.3.2, VER-25, VER-32, VER-45, VER-57, VER-61, VER-62,
and the [report](../project/modularity.md)'s three findings. No `OPN-` is open here.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | `key` on the protocol | `def key(self, inputs: StageInputs) -> Artefact`, with no progress or cancel. It returns `run`'s artefact without its payload; for a stage whose `key_is_artefact` is true (D3) it returns that artefact entire, summary included | §5.3.2: the key is taken before the stage runs. Keys are cheap by contract (`Store.get_or_compute`) |
| D2 | `key` for `case` and `materials` | Returns exactly what `run` returns. `run` becomes: check cancel, report 0, `self.key(inputs)`, report 1 | The walk stores a payload-free stage's key as its artefact (`_resolve_stage`), so a key without the summary would drop it from the store. One code path cannot drift |
| D3 | Where the facts live | Five required, keyword-only fields of `StageDescription`: `takes_workspace`, `takes_store`, `key_is_artefact` (bool), `weight` (float) and `needs_section` (`str \| None`). `summary()` carries all five | As the phase plan says. The walk reads `describe()`, never the private catalogue. Required, so a missing fact is a `TypeError`, not a silent default. `extra` stays on `StageEntry` (its docstring) |
| D4 | The walk's order | **Registration order.** `case` is registered first. `walk_order()` in `core/stages.py` returns the registered names in that order, read at call time. `registered_stages()` keeps sorting by number, so `stage --list` is unchanged | Today's `PIPELINE` is registration order with `case` in front, and VER-32 already asserts that every registered stage is walked. Read live, so import order never decides what is walked (*Design* §1) |
| D5 | What `register` now refuses | (a) an input that is neither `case_path` nor a stage registered before it, naming the input and the stage; (b) a `weight` that is not finite and positive, naming the value. Either refusal leaves the registry unchanged | (a) turns VER-32's dependency-order test into a refusal at the one place the order is made (QR-12: name the quantity). (b) A zero total weight divides by zero in `_walk`, and a negative one makes progress non-monotone (VER-25) |
| D6 | `STRUCTURE_STAGES` | Derived: the stages whose `needs_section` is `"structure"`. The drop rule becomes "drop each stage whose `needs_section` names a top-level `CaseDocument` field the case leaves `None`". VER-64 asserts that each declared value is an optional top-level field. `gui/geometry.py` derives `GEOMETRY_STAGES` from it | The phase plan leaves this to WP36. A new stage-1-to-4 sibling is then one registry entry. The other drop rules (`region`, `protonation`, `charge`) test case predicates, not section presence, and stay as written |
| D7 | `io.run`'s constants | Removed, not kept as derived aliases. Callers use `walk_order()` and `describe(name).<fact>`. The `_WEIGHTS` comments move beside each registry entry | A module constant snapshots the registry at import, so a stage registered later would be walked but absent from it: a second truth, which `MOD-02` exists to remove |
| D8 | `_probe` | Removed. The walk, `stored_upstream`, `validation/comsol.py` and `gui/assess.py` call `stage.key(inputs)` directly | With `key` universal there is nothing to probe |
| D9 | VER-64's source of truth | `validation.modularity.stage_conformance` gains `key_signature` and `STAGE_KEY = "(inputs)"`; `conforms` requires `key`. `stage_sets(module="io/run.py")` must return nothing | Read from the syntax tree, importing no stage (VER-25). The report stays dated at `97f2b3d` |
| D10 | `MOD-12`'s check | `validation.modularity.surface()` read live: `mirror_differs == ()`, and `set(public) == set(nanopnp.PUBLIC)` so the syntax tree and the runtime agree. Named for VER-45 | The report's recommendation. No new identifier (phase plan) |
| D11 | The findings log | `MOD-01`, `MOD-02` and `MOD-12` become `fixed`, their ruling linking this plan | VER-63: a `fixed` row's ruling links a plan |
| D12 | Release | `v0.5.0-alpha.2`, and a `CHANGELOG.md` section of that name | §2.7; G11 |

### Work items

In dependency order. Read *Design* §1 before item 1.

1. **`core/stages.py`**: add `key` to `Stage` (D1). Add the five fields to `StageDescription`
   and to `summary()` (D3). Move `case`'s `register` call first, and give every built-in entry its
   facts, the values in *Design* §2 (D4). Add `walk_order()`, and give `register` D5's refusals.
2. **`io/case.py` `CaseStage`, `materials/stage.py` `MaterialsStage`**: add `key` (D2).
3. **`io/run.py`**: remove the five constants, `_WEIGHTS` and `_probe` (D7, D8). Derive from
   `walk_order()` and `describe()` in `construct`, `selected_stages`, `_resolve_stage`,
   `stored_upstream` and `_walk`, including the complete-walk label (`walk_order()[-1]`).
4. **`validation/comsol.py`, `gui/assess.py`, `gui/geometry.py`**: drop both `type: ignore`s (D8),
   and derive `GEOMETRY_STAGES` (D6).
5. **`validation/modularity.py`**: `key_signature`, `STAGE_KEY` and the stricter `conforms` (D9).
6. **Tests**: VER-64 (below). Rewrite `test_run.py`'s three set tests against the facts. Move
   `PIPELINE` users (`test_solve_hook.py`, `test_pipeline_2wcd.py`, `test_exclusion_2wcd_walk.py`,
   `test_examples_07_pdb_to_charged_run.py`) to `walk_order()`. Add D10's check.
7. **Records**: §7.2's VER-64 row, VER-25's added clause, FR-27's Appendix A row; the findings log
   (D11); `CHANGELOG.md` (D12); the phase plan's WP36 Outcome and `current.md`. VER-61's YAML is
   edited in the same commit as any edge that moves. None is predicted: `gui` keeps importing
   `io.run` for `selected_stages`.

### Verification

| Test | Tier | Identifiers | Assertion and oracle |
|---|---|---|---|
| `tests/tier1/test_stage_conformance.py` (new) | 1 | VER-64 | Every registered stage `conforms`, by `stage_conformance`: `describe`, `key (inputs)` and `run (inputs, *, progress, cancel)`. Fed synthetic sources whose stage lacks `key`, or whose `key` takes `(inputs, cancel)`, it does not conform. `stage_sets("io/run.py") == ()` |
| same file | 1 | VER-64 | The facts against the code: `takes_workspace` and `takes_store` equal the constructor signatures (VER-32's and VER-57's old tests, moved); for each stage with `key_is_artefact` true, `key(inputs).meta()` equals `run(inputs).meta()` less `created_at`, with no payload, on `test_run.py`'s case; every `needs_section` names an optional top-level `CaseDocument` field |
| same file | 1 | VER-64 | `register` refuses an input not registered before it, a weight of `0`, `-1`, `nan` and `inf`, and a description missing a fact (`TypeError`), each leaving the registry unchanged. `walk_order()` equals the 13 names written out in today's `PIPELINE` order, so the walk cannot reorder unseen |
| `tests/tier1/test_public_api.py` | 1 | VER-45, `MOD-12` | D10 on the live tree. On synthetic sources with a name dropped from the mirror, `mirror_differs` names it |
| `tests/tier1/test_run.py`, `test_stages.py` | 1 | VER-32, VER-25, VER-57 | Unchanged claims, rewritten against `walk_order()` and the facts |
| The gated walks | 2 | VER-62 | **Zero drift.** The walk's order, keys and work are unchanged; any difference is a defect of this package |
| `tests/tier1/test_layering.py`, `test_findings_logs.py` | 1 | VER-61, VER-63 | Green; the log's three rows `fixed` |
| mypy strict | — | `MOD-01` | Clean with both `type: ignore`s removed |

Commands: the phase plan's *Verification* block (gate, `.claude/hooks/gate.sh run`, docs build).

> **Outcome — the `key == run` check reads the quickstart case.** Stages 8 and 9 need only a case
> that resolves, and `examples/01-quickstart` resolves without generating the mesh `test_run.py`'s
> case names. The moved `takes_workspace` and `takes_store` checks sit in the VER-64 file, and
> `test_run.py` keeps VER-32's dependency-order test, read against `walk_order()`. VER-25's
> fresh-process test also reads the facts, since its clause now names them.

### Out of scope

- `MOD-11`, `register` or `with_section` in `PUBLIC`: after the sessions (H2).
- `MOD-15`, `core/stages.py`'s `TYPE_CHECKING` import of `io.artefact`: WP38, with the `io` split.
  `key`'s annotation adds a use of that import and no new edge.
- The optional `deviations` member and the `SolveReporting` capability stay off the protocol: no
  finding asks for them.
- `selected_stages`' remaining literals and the GUI's `"region", "mesh"`: case logic and the shell's
  view choice. Phase 5 owns the second (F5).

### Open questions

None blocking. D4, D6 and D7 are the close calls; the author may overrule any of them before
`/wp-implement` starts.

## Design

### 1. Why the walk is registration order, and what that commits a registered stage to

Today `PIPELINE` is `case`, then the registry in registration order. Registration order already
places `protonation` after `mesh` (WP27 D2) and `materials` after `charge`. Moving `case`'s
`register` call first therefore leaves the walk exactly as it is: VER-62's zero-drift prediction
rests on this. `registered_stages()` sorts by `(number, registration)`. The only shared number is
7, where `protonation` still precedes `charge`. So the listing is unchanged too.

D5(a) makes registration order a dependency order by construction. Each stage's inputs are
`case_path` or names registered earlier: `case` takes `case_path`; every other stage takes `case`
and its upstream stages; `charge` takes `region`, registered at 5. A stage registered from outside
the package is appended. It is walked after `report`, and only if its inputs exist. VER-32 already
asserts that every registered stage is walked, so this is today's invariant made explicit, not a
new one. A test that registers a stage successfully must restore the registry (`monkeypatch` on a
copy of `_REGISTRY`), or that stage joins every later walk in the process.

### 2. The facts of the built-in stages

Read from today's `WORKSPACE_STAGES`, `STORE_STAGES`, `PAYLOAD_FREE`, `STRUCTURE_STAGES` and
`_WEIGHTS`, at `e987c8d`.

| Stage | `takes_workspace` | `takes_store` | `key_is_artefact` | `weight` | `needs_section` |
|---|---|---|---|---|---|
| case | no | no | yes | 0.01 | — |
| structure | yes | no | no | 0.05 | `structure` |
| density | yes | no | no | 0.2 | `structure` |
| symmetry | yes | no | no | 0.05 | `structure` |
| contour | yes | no | no | 0.03 | `structure` |
| region | yes | no | no | 0.01 | — |
| mesh | yes | no | no | 0.05 | — |
| protonation | yes | yes | no | 1.0 | — |
| charge | yes | yes | no | 0.2 | — |
| materials | no | no | yes | 0.01 | — |
| solve | yes | no | no | 0.75 | — |
| qoi | no | no | no | 0.08 | — |
| report | yes | no | no | 0.04 | — |

`key_is_artefact` is what the walk branches on today through `PAYLOAD_FREE`: such a stage's key is
stored as its artefact, and under `only` it is resolved rather than demanded from the store. It is
named for that, not for whether a file is written. `qoi`'s key avoids the solve and carries no
summary, so it is not its artefact, whatever the payload. VER-64's `key == run` check applies
exactly where the fact is true.
