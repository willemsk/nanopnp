# WP40 — The stale refusals

**Status: planned, not started.** Written 7 October 2026 at `d067c5e`, after WP39 was delivered as
`v0.5.0-alpha.5`. It inherits everything the [current brief](current.md) lists as not to be
re-decided, and in particular:

- WP38's split: `io` is the base, `pipeline/checks.py` makes the case's refusals at resolution
  (WP38 D7), and the stage guards repeat them for a stage invoked directly;
- VER-47's exit-code contract (`core/errors.py`), which this package keeps;
- VER-61's recorded layering and VER-62's golden, neither of which this package moves;
- WP39's rule that a refusal names requirements only (WP39 *Out of scope*).

This is the sixth work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md). It fixes
`MOD-14` (§8.2.8 H1, H8) and claims VER-67. `SPECIFICATION.md` governs, and the identifiers below
are pointers into it. **This commit amends the specification**: the §5.3.1 NOTE on `inputs:` states
how a supplied artefact named by store hash is refused, and the NOTE on `numerics.nonlinear` states
that the NUM-20 fallbacks are refused and that no release schedules them (D5, D6). VER-67's row and
Appendix A's pointer are claimed by `/wp-implement` in the commit that implements them, as VER-66's
were.

## Execution brief

### Scope

`MOD-14` measured seven non-docstring strings naming a release. On `d067c5e`, after WP38 moved
`io/case.py`'s checks to `pipeline/checks.py`, `validation.modularity.version_literals` finds
the same seven:

| Site | Text today | Disposition |
|---|---|---|
| `charge/stage.py:306` | `inputs.<key>: artefact:` "which the charge pipeline of v0.4 fills" | D5 |
| `pipeline/checks.py:392` | the same, at resolution | D5 |
| `mesh/ingest.py:704` | `inputs.mesh: artefact:` "which the meshing pipeline of v0.3 fills" | D5 |
| `pipeline/checks.py:438` | `strategy` "is the NUM-20 fallback ladder, which is v0.2" | D6 |
| `pipeline/checks.py:444` | `damping` "is v0.2" | D6 |
| `io/defaults.py:120` | `CONFIGURATION_PATHS` reason "mesh generation is v0.3" | D7 |
| `pipeline/checks.py:731` | `geometry.analyte` "is FR-21, v0.7" | D7: conforms, kept |

Two empty tables, `_UNCONSUMED_INPUTS` and `_UNREAD_CHARGE_KEYS`, loop to refuse "not delivered in
this release" (D8).

**Breaks** (F4; `CHANGELOG.md`): the five refusal texts and the configuration reason change. A case
naming `inputs.mesh` by `artefact:` is refused at resolution, so `nanopnp validate case` exits 3 on
it where it exited 0 (D5). Exit codes do not change (VER-47). The schema identifier stays (D5).

Pointers: IF-02, FR-27, FR-10, FR-21, NUM-16, NUM-20, VER-24, VER-47, VER-61, VER-67 (proposed),
VER-72; §2.7 NOTE (Versioning); §5.3.1 NOTEs on `inputs:` and `numerics.nonlinear`; §8.2.8 H1, H8;
§8.2.9 I3; [`MOD-14`](../project/modularity.md#mod-14-refusals-name-releases-that-have-shipped);
[REV-62](../project/review-items.md#rev-62-a-mesh-named-by-store-key-is-refused). No `OPN-` is open
here.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | What names a release | `VERSION_LITERAL` widens to `(?<![\w/.-])v(\d+)\.(\d+)(?!\d)`: any `vX.Y`, with a pre-release naming its minor (`v0.2.0-alpha.3` names `v0.2`). A schema identifier (`nanopnp/case/v0.5`) is not a release name: the look-behind refuses a `/`. One row per release named | `v1.0` must be checkable before it is tagged. G6 moves the schema to `nanopnp/case/v0.5`, which must not fail at `v0.5.0` |
| D2 | "Already tagged", without the network | `tagged_releases(changelog_text) -> tuple[str, ...]` reads `CHANGELOG.md`'s `## [X.Y.0]` headings, sorted. It raises `ValueError` if there is none ("names no release") or if a major's minors have a gap, naming the missing release. Never git | §2.7: `CHANGELOG.md` records every tag. This clone has 0 local tags; origin has 45. An empty or gapped read would pass every string, so it is refused |
| D3 | What VER-67 checks | `stale_release_literals(tagged, root=None, sources=None)` returns `(path, line, release, text)` for each non-docstring string of `src/nanopnp` naming a tagged release. Every string, not only refusals. Docstrings and comments are not checked | A reason or label a user reads is as stale as a refusal (`io/defaults.py`). A docstring's "(v0.3)" records when a section arrived, which stays true |
| D4 | The refusal template | Names the key and value, then the requirement, then the release that schedules it ("deferred to v0.6", "FR-21, v0.7") or "which no release of SPECIFICATION.md schedules", then the remedy. Texts exact in *Design* §1 | `MOD-14`'s recommendation; IF-02 |
| D5 | The store form | `io.case.stored_artefact_refused(key) -> UnsupportedCaseSection` writes the one text per key. The two fields: no release schedules the store form. The mesh: REV-62, deferred to v0.6 (§8.2.9 I3). `require_runnable` refuses all three keys at resolution, and the stage guards (`mesh/ingest._source_path`, `charge/stage._field_path`) raise the same object's text. Spec amendment | Today `validate` passes a mesh `run` refuses. Not a narrowing under G6: no run ever accepted it. Three call sites, one text |
| D6 | NUM-20 | The strategy and damping texts of *Design* §1. Spec amendment to the NOTE on `numerics.nonlinear` | NUM-20 carries no release; the schema's `Literal` admits exactly `hybrid` and `backtracking`, so each text names its fallback |
| D7 | The rest of the seven | `CONFIGURATION_PATHS["numerics.mesh.backend"]` names FR-10 (*Design* §1). The `geometry.analyte` refusal stays verbatim; so does FR-11's "after v1.0" | Both conform to D4. VER-67 fails the FR-21 text at the `v0.7.0` tag unless FR-21 ships, which is the ratchet working |
| D8 | The empty tables | `_UNCONSUMED_INPUTS`, `_UNREAD_CHARGE_KEYS` and their loops go. The §5.3.1 rule stays in the specification. `test_ver47_every_new_input_is_read_by_the_stage_that_consumes_it` loses its assertion on the table | `MOD-14` rules the first. The second is the same dead refusal saying "this release"; a later key adds its own refusal and test |
| D9 | Docstrings with a false schedule | Rewritten beside their refusals: `_source_path`, `_field_path`, `_check_charge`'s Raises, and `ReportStage`'s "Figures are v0.4" (FR-28 is v0.7). Not checked by VER-67 (D3) | Coverage cannot see a stale docstring; the four are the ones touched or provably false |

### Work items

- [ ] 1. [Opus] — a pattern or a CHANGELOG read that misses a name passes every string. `validation/modularity.py`: `VERSION_LITERAL`, `tagged_releases`, `stale_release_literals` (D1–D3); `render_measurements` keeps its section, counting the widened pattern. Done when the three synthetic `test_ver67_*` tests pass.
- [ ] 2. [Opus] — a refusal's text and where it fires. `io/case.py` `stored_artefact_refused`; `pipeline/checks.py` `require_runnable` refusing the three keys; the stage guards; their docstrings (D5, D9). Done when `test_fr27_a_*_named_by_store_hash_*` and `test_ver47_validate_case_refuses_a_stored_mesh_with_exit_three` pass.
- [ ] 3. [Opus] — refusal texts and the removal of a refusal path. The NUM-20 texts (D6), the configuration reason (D7), the empty tables (D8) and `ReportStage`'s docstring (D9). Done when every test of `test_stale_refusals.py` passes, `test_ver67_no_string_in_the_package_names_a_tagged_release` included, with `test_case_schema.py` and `test_case_schema_v2.py`.
- [ ] 4. [any] Records: VER-67's row in §7 and IF-02's Appendix A pointer; `MOD-14` `fixed` in `modularity-findings.md`; `CHANGELOG.md` `0.5.0-alpha.6`, *Changed*, with the breaks; this plan's status and the brief. Done when VER-63, VER-72 and the strict docs build pass.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_stale_refusals.py` (new; planned in this commit) | 1 | VER-67, IF-02, FR-27, NUM-20, VER-24, VER-47 | (a) A synthetic changelog with `0.1.0`, `0.2.0`, `0.2.0-alpha.10`, `0.3.0-alpha.1` reads `("v0.1", "v0.2")`; one with only an alpha raises "no release"; `0.1.0` and `0.3.0` raise naming `v0.2`; the real file starts `v0.1`–`v0.4`, contiguous. (b) A synthetic package with tagged `v0.1`, `v0.2`: an f-string piece "is v0.2" at line 4 and `v0.2.0-alpha.3` at line 2 are found; a docstring naming `v0.2`, `nanopnp/case/v0.2`, `v0.20`, `v0.7` and `v1.0` are not; with `v0.7` and `v1.0` tagged, those two are. (c) The live tree finds none. (d) Each text of *Design* §1 equals the refusal exactly, through `resolve` and through each stage guard. (e) `nanopnp validate case` on a stored mesh exits `EXIT_CASE` with the text on stderr and no traceback. (f) The tables are gone and `pipeline/checks.py` holds no "not delivered in this release" |
| `tests/tier1/test_case_schema.py::test_fr27_the_num20_fallbacks_are_refused_by_name` | 1 | NUM-20 | Unchanged; still matches `NUM-20` |
| `tests/tier1/test_case_schema_v2.py` | 1 | VER-47 | D8's edit; `inputs.pqr` still read |
| `tests/tier1/test_cli.py`, `test_layering.py`, `test_source_conventions.py`, `test_plan_records.py` | 1 | VER-47, VER-61, VER-72 | Unchanged: no exit code, edge or private import moves (the three sites already import `io.case`) |

Command: `uv run pytest tests/tier1/test_stale_refusals.py -v`, then `.claude/hooks/gate.sh run`.
Tier 2 is not touched; VER-62 is not re-pinned.

### Out of scope

- Reading a mesh from the store: REV-62, Phase 5 (§8.2.9 I3). A store-form field: unscheduled.
- A check that a string pairing a requirement with a release agrees with §3's Release column. Not
  ruled; VER-67 checks only the tags.
- Refusals that name no release and no requirement (`walls`): not `MOD-14`'s; WP46's sessions.

### Open questions

None blocking. D5 (refusing the stored mesh at resolution) and D8 (removing
`_UNREAD_CHARGE_KEYS` as well) go slightly past `MOD-14`'s letter; each is a one-line revert
if the author rules otherwise.

## Design

### 1. The texts

`{key}`, `{what}` are `charge`, "a fixed-charge field" and `eps_r`, "a dielectric field".

| Site | Text |
|---|---|
| Field, store form | `inputs.{key}: artefact: names {what} by its store hash. FR-27's substitution reads a supplied field by path only, and no release of SPECIFICATION.md schedules the store form; supply inputs.{key}: path: instead` |
| Mesh, store form | `inputs.mesh: artefact: names a mesh by its store hash. FR-27's substitution reads a supplied mesh by path only; the store form is REV-62, deferred to v0.6 (section 8.2.9 I3); supply inputs.mesh: path: instead` |
| Strategy | `numerics.nonlinear.strategy 'hybrid' selects NUM-20's hybrid segregated fallback, which no release of SPECIFICATION.md schedules; every rung is solved by the monolithic damped Newton of NUM-16 (strategy: newton)` |
| Damping | `numerics.nonlinear.damping 'backtracking' selects NUM-20's damped Newton with l2 backtracking, which no release of SPECIFICATION.md schedules; the damping is NUM-16's, adapted on residual reduction (damping: residual), whose recovery rule the reference records` |
| Mesher reason | `the mesher is stage 6's choice (FR-10), recorded in the Geometry and mesh group of the manifest (section 5.3.3); it changes the discretisation, not the model` |

The value is written with `!r`. The NUM-20 names are the table's own rows: "Hybrid segregated" and
"Damped Newton with ℓ₂ backtracking", in ASCII for a console. "v0.6" is Phase 5's release (§2.7),
which I3 defers REV-62 to; VER-67 fails it at `v0.6.0` unless REV-62 is resolved first.

### 2. Why the stored mesh is not a narrowing

G6 moves the schema identifier when a document that ran is refused (I2, on REV-42). Here,
`resolve` accepts `inputs.mesh: {artefact: …}`, and stage 6 refuses it, `EXIT_CASE`, in
`_source_path`. No stage reads the store form (`grep 'SuppliedArtefact(' src` builds only `path:`
forms), so no case that ran is refused. The refusal moves earlier, to where `nanopnp validate case`
sees it, and keeps its class and exit code.
