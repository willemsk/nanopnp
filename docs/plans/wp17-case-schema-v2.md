# WP17 — Case schema v2 and the 3.11 floor

**Status: planned, not started.** Written 24 September 2026. This is the first package of Phase 2.
It inherits the `case_fields()` schema walk and switch classification (WP7, WP14), the stage-10
solve-key and restore-digest contract (WP10, WP15), and the Tier-3 case identity (WP13). **It is not
implemented until ruling B1 is met.** The Phase 1 end-of-phase report has merged as `v0.5.0`, and the
author's double-click observation of amendment A4 was recorded on 24 September 2026 (the NOTE to
§8.2.1), so B1 is met. Its tag is `v0.9.0-alpha.1`.

This package belongs to [Phase 2, geometry pipeline](phase-2-geometry-pipeline.md) §WP17.
`SPECIFICATION.md` governs, and every identifier below points into it. Where this plan and the
specification disagree, the plan is wrong. **Spec amendments made in this plan's commit:** IF-03
names v2 and the lossless v1 read; the §5.3.1 example moves to v2, and two NOTEs are added, one on
the v2 key set and the upgrade, one on the three v2 keys that change a number; the `inputs:` NOTE
gains `profile`, `pqr` and the one-chain rule; the §5.3.2 solve-key NOTE excludes `schema:`; the
§5.2 stage-9 row and the §5.3.2 artefact row name v2; the §5.3.4 and VER-43 wording is no longer
tied to v1; **VER-47** is added; and Appendix A maps IF-03, FR-26 and QR-09 to it. The IF-05 NOTE
and VER-29 change with the code, as B4 requires (work item 5).

## Execution brief

### Scope

This package makes the breaking change of Phase 2 before anything else is built on the schema (B3,
B4). It does three things:

1. Move the case schema to `nanopnp/case/v2`, with the key set fixed by the §5.3.1 v2 NOTE, and read
   a v1 document losslessly.
2. Raise the Python floor to 3.11 and the `structure` extra's floors to the §2.6 versions, and
   retire the conditional CCP4 writer.
3. Verify both under **VER-47**.

It discharges IF-03 and FR-26 as amended and QR-09 as amended. It also touches FR-25 (two new
switches) and FR-27 (two new substitution points). No stage is added. Every new `inputs:` key and
every block of Phases 2 and 3 is still refused as an unsupported section, and each later package
lifts its own refusal.

**The brief exceeds its 1,200-word target, at about 1,900 words.** Its fifteen decisions fix a key
set that no later package can change without another schema move. They are kept together rather
than split, because the key set, the upgrade and the key survival are one change and are verified
by one oracle.

### Pointers

- §5.3.1: the example, the v2 NOTEs, and the `inputs:` and solid-permittivity NOTEs.
- §5.3.2: the NOTE on what keys a solve.
- §3.1: IF-03 and the IF-05 NOTE.
- §2.5, §2.6, QR-09 and §8.2.2 B3–B4.
- VER-09, VER-24, VER-29, VER-34, VER-43, VER-45 and VER-47.
- Code: `io/case.py` (models, `load_case`, `loads_case`, `_require_runnable`,
  `SOLVE_IRRELEVANT_PROVENANCE`); `io/artefact.py` (`CASE_SCHEMA`); `io/defaults.py`;
  `density/grid.py` (the writer gap); `validation/comsol.py` (`case_identity`);
  `solve/state.py:577` (the restore digest).

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | The v2 key set | Seven keys are added: `inputs.profile`, `inputs.pqr`, `structure.source.selection` (default `protein`), `geometry.membrane.centre_z_nm` (0), `charge.exclusion_offset_nm` (0), `charge.dielectric_transition_nm` (0) and `numerics.mesh.size_scale` (1). One key is renamed: `structure.source.pdb` becomes `path`. Two keys are removed: `charge.eps_protein` and `geometry.membrane.eps_r`. Nothing else changes | §5.3.1 v2 NOTE. The rule used: a key goes in if the spec or a Phase 2 ruling already names it as configurable, or if a Phase 2 or 3 package cannot run without it. A later need is met by widening an existing key's value set where possible, which does not move the schema (§5.3.1 compatibility rule). [Design §1](#1-the-v2-key-set-and-where-each-key-comes-from) |
| D2 | Permittivities | `physics.solid_permittivities` becomes the only place they are set. The Python defaults 20 and 3.2 go | **Author ruling, 24 September 2026.** A calibration parameter set in two places has two sources of truth, and `CLAUDE.md` forbids hard-coding `ε_protein` in Python. Every shipped case already writes `protein: 20.0` |
| D3 | Contour tuning parameters and gate thresholds | Neither becomes a case key. Taubin, spacing and spline parameters are constants cited in WP20. A gate threshold is never a case key | **Author ruling, 24 September 2026.** A gate that a case can loosen is not a gate. If WP20 does need a knob, that is a v3 move, and that risk is accepted |
| D4 | Upgrade mechanism | `upgrade_v1(raw) -> raw` in `io/case.py` is a pure mapping transform that runs before `CaseDocument.model_validate`. `load_case` and `loads_case` dispatch on the declared schema, and `dumps_case` always writes v2. No v1 pydantic model is kept. `V2_ADDED`, `V2_RENAMED` and `V2_MOVED` are module constants | A second model would be a second schema to maintain. The frozen v1 field tree is the contract, and it is held as test data (D7) |
| D5 | Upgrade refusals | Four cases are refused, each as a `CaseValidationError` naming the keys: a v1 document carrying a v2 key; a moved permittivity that disagrees with the map, naming both values; a v2 document using a removed or renamed key, naming its replacement through `render_problems`; and an undeclared schema, naming both accepted schemas | §5.3.1 v2 NOTE: a document is valid against the schema it declares or not at all. An `eps_protein` silently ignored in v2 would be a calibration parameter dropped without a word |
| D6 | Which artefact keys survive the move | Kept: the stage-10 solve key, the VER-34 restore digest, the Tier-3 `case_identity`, and the stage-6, 7 and 8 keys. Moved: the stage-9, 11 and 12 keys. Mechanism: `schema` joins `SOLVE_IRRELEVANT_PROVENANCE`. Old store entries are left in place and nothing is migrated | §5.3.2 amended. The expensive artefact is the solve, and a key that told a v1 document from its upgrade would re-solve every stored case. Stage 9 hashes the full validated dump, which has new keys whether or not they are defaulted, so its key cannot survive without a canonicalisation that would also hide real changes to defaults. [Design §2](#2-why-exactly-these-keys-survive) |
| D7 | Oracle for "the same run" | A frozen corpus of every v1 case file shipped at `v0.5.0`: 7 example case files, 5 validation cases and the sweep base case, 13 in total. Their v1 field tree and a golden record are **generated by the unmodified v1 code and committed first**: per file, the restore digest, the materials key, `case_identity` and the decoded `solve_provenance` | VER-47. Recording from the same code that does the upgrade would test the upgrade against itself. `resolve()` reads no file, so this runs in Tier 1 |
| D8 | Stage granularity of `inputs:` | Two chains: structure → density → profile → mesh, and structure → PQR → charge field. Supplying an artefact beside one downstream of it on the same chain is refused, naming both. `profile` and `pqr` are refused as unsupported, naming WP21 and Phase 3 respectively | §5.3.1 `inputs:` NOTE. An unread upstream artefact would be hashed into the manifest as an input |
| D9 | The new switches | `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` join `SWITCH_PATHS` with validated default `0.0` and are validated `≥ 0`. `deviations()` reads a path under an absent optional block as its validated default. `VALIDATED_DEFAULT_CASE` gains a `charge:` block at its defaults, so that `test_ver24_every_switch_path_reads_off_the_validated_default` holds | §5.3.1 NOTE on the v2 keys that change a number. Floats are not switch-typed by the walk, so they are classified by hand, and the reverse-direction VER-24 test covers them |
| D10 | `size_scale` with a supplied mesh | A value other than 1 beside `inputs.mesh` is a `CaseValidationError`. The key is a configuration choice, not a deviation | Same NOTE: a knob with no effect is refused, as with the other inapplicable settings |
| D11 | `structure.source.selection` | An MDAnalysis selection string with default `protein`. It is configuration, not a switch | The bilayer is absent from the density map (§5.2, notes on stages 3 and 5), and the ensemble archive may include lipids and waters (Phase 2 plan, open decisions) |
| D12 | Interpreter floor | `requires-python = ">=3.11,<3.15"`, classifiers 3.11–3.14, ruff `target-version = "py311"`, and the resulting `UP` fixes. mypy stays at 3.12. The CI matrix becomes `["3.11", "3.13", "3.14"]` plus the desktop legs | B4, QR-09, §2.5. VER-47 asserts the four declarations agree |
| D13 | `structure` extra floors | `MDAnalysis>=2.10`, `GridDataFormats>=1.2` and `pdb2pqr>=3.7`, then `uv lock` | §2.6 names these versions. The comment tying the floors to 3.10 goes |
| D14 | The CCP4 writer | Delete `MRC_WRITER_MIN_VERSION` and the version-gap wording of `_no_writer`. `writable_formats()` stays as the queryable surface. VER-29 asserts the CCP4 round trip unconditionally | B4. A refusal branch that no supported interpreter can reach is untested code |
| D15 | Upgrade command | None. Reading is lossless, and every run writes the upgraded document to its run directory. The manifest embeds the file as it was read (the `case_hash` is the upgrade's) | This keeps IF-02 unchanged. See out of scope |

> **Outcome — D6 was wrong about the three solve keys; they moved once.** The v1
> `solve_provenance` *contained* `"schema": "nanopnp/case/v1"`, so adding `schema` to
> `SOLVE_IRRELEVANT_PROVENANCE` changes the stage-10 key, the restore digest and `case_identity`
> of every v1 case (clya-0.5M-plus50mV: `7e9ca188…` → `e266057d…`). Design §2's "removing
> `schema` therefore leaves all three hashes unchanged" is the error. The author ruled on
> 24 September 2026 to let them move once rather than freeze a v1 string into every v2 solve
> record. The materials key survives. VER-47 now holds the upgraded record equal to the recorded
> v1 record less `schema`, entry by entry, and checks that the recorded digests hash the recorded
> record; §5.3.1, the §5.3.2 NOTE and VER-47 are amended, and the export contract's `case_hash`
> is updated.

### Work items

1. **Freeze the oracle, on unchanged code, as its own commit** (D7). Put the corpus in
   `tests/tier1/data/case_v1/`, together with `fields.txt` (the `case_fields()` paths) and
   `golden.json`, both written by `record.py` in that directory (`uv run tests/tier1/data/case_v1/record.py`).
   Add `test_ver47_the_v1_corpus_resolves_to_its_recorded_solve` in
   `tests/tier1/test_case_schema_v2.py`, which passes on v1. Commit it as
   `test: freeze the v1 case corpus and its solve keys`.
2. **Schema** (D1, D2, D4–D6, D8, D10, D11). Change `CASE_SCHEMA` to v2 and add `CASE_SCHEMA_V1`.
   In the models, add the seven keys, rename `pdb`, and remove the two permittivities. Add
   `upgrade_v1` and dispatch on the declared schema. Extend the `render_problems` suggestion with the
   v2 replacements. Add `schema` to `SOLVE_IRRELEVANT_PROVENANCE`. Add the `_require_runnable`
   refusals and the chain rule. Remove the hard-coded v1 strings in `core/stages.py:433`,
   `cli/__init__.py:986` and `cli/reference.py:116`, deriving them from `SCHEMA` instead.
3. **Classification** (D9): update `io/defaults.py` and the absent-block rule in `deviations()`.
4. **Rewrite every shipped case to v2**: `examples/*/`, `docs/validation/cases/`, `docs/sweeps/`,
   the inline YAML in the tests (except the tests that exercise the upgrade), `docs/guide/`, the
   README, `CLAUDE.md` §Provenance, and the docstrings that name v1. `docs/guide/case-files.md` gains
   a short section on reading v1 files.
5. **Floor** (D12–D14): `pyproject.toml`, `uv lock`, `.github/workflows/ci.yml`, `density/grid.py`
   and `test_charge_fields.py`. In the spec, replace the IF-05 NOTE with a one-line retirement note
   and drop VER-29's "or where the installed GridDataFormats has no CCP4 writer" clause.
6. **VER-47 tests** (see Verification). Add the `CHANGELOG.md` section `v0.9.0-alpha.1`. Update the
   Outcomes in this plan, and `current.md`.

### Verification

| Test | Tier | Identifier | Oracle | Tolerance |
|---|---|---|---|---|
| `test_case_schema_v2.py::test_ver47_the_v1_corpus_resolves_to_its_recorded_solve` | 1 | VER-47, FR-26 | Each corpus file, upgraded, reproduces the `golden.json` restore digest, materials key and `case_identity`. A mismatch prints the `solve_provenance` diff | exact (hash equality) |
| `…::test_ver47_a_v1_file_and_its_v2_rewrite_are_one_case` | 1 | VER-47, FR-26 | Per corpus file, `dumps_case(load(v1))` reloads to equal `CaseArtefact` and `ResolvedCase.provenance` | exact |
| `…::test_ver47_the_v1_tree_maps_onto_v2_in_both_directions` | 1 | VER-47 | `fields.txt` minus renamed and moved, plus added and renamed targets, equals `case_fields()` of v2. Checked both ways | set equality |
| `…::test_ver47_refusals` (parametrised) | 1 | VER-47, IF-03, QR-12 | Each D5, D8 and D10 input raises with every named key present in the message | — |
| `…::test_ver47_the_new_switches_are_deviations` | 1 | VER-47, FR-25 | A non-zero `exclusion_offset_nm` is listed and an absent `charge:` block lists nothing | — |
| `…::test_ver47_the_declared_python_range_agrees` | 1 | VER-47, QR-09 | `requires-python`, the classifiers, the ruff target and the `ci.yml` matrix are parsed, and each equals §2.5's 3.11–3.14 | — |
| existing VER-09, VER-24, VER-43 and VER-45 suites | 1 | VER-09, VER-24, VER-43, VER-45 | They pick up the v2 paths through `case_fields()` without edits beyond the schema string | — |
| `test_charge_fields.py::test_ver29_a_grid_round_trips_through_opendx_and_ccp4` | 1 | VER-29, IF-05 | The CCP4 round trip holds unconditionally | as today |
| the docs build | CI | VER-45 | The generated case reference lists the seven keys and not the two removed ones | strict |

Commands: `uv run pytest tests/tier1/test_case_schema_v2.py -v`, then the full gate
(`.claude/hooks/gate.sh run`). Also run `uv run pytest -m "tier2 and not slow"` to completion.

### Out of scope

- The stages that consume the new keys belong to WP18–WP21 (Phase 2) and to Phase 3.
- The analyte's surface-or-volume charge option of FR-21 belongs to v1.0. If it needs a key, that
  is a v3 move.
- `inputs.density` and a supplied stage-3 map are left out. FR-27's substitution of those artefacts
  is already met by editing their store payload (VER-23).
- A `nanopnp case upgrade` command is left out (D15). It would add IF-02 surface for something every
  run already does.
- FR-20's physics-model interface (Phase 3) takes no case keys. A model that needs parameters reads
  them from a data file, as the corrections do.

### Open questions

None that block WP17. The contour-parameter question (D3) and the permittivity question (D2) were
put to the author and ruled on before this plan was committed.

## Design

### 1. The v2 key set, and where each key comes from

| Key | Change | Default | Source | Consumed by |
|---|---|---|---|---|
| `inputs.profile` | added | — | B3; §8.1 GUI increment 2 | WP20, WP21, WP24 |
| `inputs.pqr` | added | — | Phase 2 plan §WP17 ("a supplied PQR"); FR-12 | Phase 3 |
| `structure.source.path` | renamed from `pdb` | — | IF-04 (mmCIF) | WP18 |
| `structure.source.selection` | added | `protein` | §5.2 stage notes 3 and 5 | WP18, WP19 |
| `geometry.membrane.centre_z_nm` | added | `0.0` | B3; phase Design decisions (model frame); G9 | WP21, WP22 |
| `geometry.membrane.eps_r` | removed, moved to `physics.solid_permittivities.membrane` | — | D2 | — |
| `charge.eps_protein` | removed, moved to `physics.solid_permittivities.protein` | — | D2; PHY-20 | — |
| `charge.exclusion_offset_nm` | added | `0.0` | FR-15; PHY-20 ("SHALL be surfaced") | Phase 3 |
| `charge.dielectric_transition_nm` | added | `0.0` | PHY-20 and its blend NOTE | Phase 3 |
| `numerics.mesh.size_scale` | added | `1.0` | FR-24 × RSK-09, §6.8 | WP21 |

Why the key set can stay this small: `smoothing: Literal[...]`, `kernel`, `titration`, `axis` and
`backend` can all take new values without a schema move. A Phase 2 or 3 method choice that can be
expressed as a new value (for example a deposition method, or `centre_z_nm: lipids`) therefore needs
no key now.

Every added key defaults to the validated configuration. Every renamed or removed key sits in a
block that `_require_runnable` refuses under v1, apart from `physics.solid_permittivities`, which
is unchanged. So no v1 document that could run gets a different configuration. The only change in
behaviour is for a v1 `charge:` or `geometry:` block that relied on the implicit 20 or 3.2, and v1
never resolved such a block. The upgrade moves written values only.

### 2. Why exactly these keys survive

The stage-10 key is `content_hash(SOLUTION_SCHEMA, solve_provenance, (mesh, materials, fields))`
(`solve/stage.py:235`). The restore digest is `content_hash(SOLUTION_SCHEMA, solve_provenance)`
(`solve/state.py:577`). `case_identity` hashes `solve_provenance` without its discretisation keys
(`validation/comsol.py:255`). `solve_provenance` is `provenance` minus
`SOLVE_IRRELEVANT_PROVENANCE`, and `provenance` holds `"schema": document.schema_id`. The other
provenance entries are built field by field from resolved objects, not dumped, so they do not see
the new keys. Removing `schema` therefore leaves all three hashes of a runnable v1 case unchanged.
Work item 1 records those hashes before the change and VER-47 checks them after it.
*(Historical, and wrong: see the D6 Outcome above. `provenance` holds `schema`, so removing it
moves all three.)*

The mesh, materials and fields keys never see the case schema. `CaseArtefact` (stage 9) hashes
`document.model_dump()` under `CASE_SCHEMA`, so the dump gains `inputs.profile: null` and the
other new keys, and the key moves. Stage 11 keys on the case hash (`post/stage.py:381`) and moves
with it, and the stage-12 key follows. Stages 9, 11 and 12 recompute in seconds.

### 3. The upgrade, step by step

1. Read `schema`. If it is v2, validate directly. If it is v1, continue. Anything else is refused,
   naming both accepted schemas.
2. Refuse any path in `V2_ADDED` that is present.
3. Move `structure.source.pdb` to `path`.
4. For each of the (`charge.eps_protein`, `protein`) and (`geometry.membrane.eps_r`, `membrane`)
   pairs, if the key was written: when `physics.solid_permittivities[name]` already exists and
   differs, refuse; otherwise set it. Then delete the source key.
5. Set `schema` to v2 and validate.

The transform never adds a default, so the validated result is exactly what pydantic makes of the
written keys.
