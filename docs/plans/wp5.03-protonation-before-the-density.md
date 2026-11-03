# WP5.03 — Protonation before the density

**Status: planned, not started.** Planned 3 November 2026, on `v0.6.0-alpha.2`. It inherits §8.2.19 U2,
§8.2.28 AD3, §8.2.31 AG8 and REV-135.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** The pore's shape is built from the protein as it is charged at the chosen pH, its
hydrogens included. Changing a residue's protonation, or later its charge, then moves the pore's wall
and mesh as well as its charge. Building from the atoms as loaded, as the published reference did,
stays available as a switch, recorded in every result it affects. The reference cases set it, so their
numbers do not move. Case files take a new version label, and older files are refused with a message
saying what to change.

**Cost.** About a week. Building a geometry now runs the protonation step first: about a minute per
frame of the ClyA dodecamer, the same minute a charged run already spends.

**What could go wrong.** A crystal structure without hydrogens gains about 50,000 of them, so worked
example 07's pore narrows and its current falls. As you ruled, its recorded numbers are taken again.
A rise in its current instead would stop the package for investigation. An atom whose size the
CHARMM table does not give is refused by name. The other two force fields name their hydrogens
differently, so with either of them the new default is refused. The message points to CHARMM or to
the switch.

**Your call.** None open. You ruled on example 07 at this plan (AG8).

## Execution brief

**Scope.** Stage 7's `protonation` walks before stage 2, which smears its atoms by default
(`geometry.density.atoms`). The case schema moves to `nanopnp/case/v0.6`. The VER-62 walks are
handled as AG8 rules. The clauses U2 names are amended. **Depends on:** `v0.6.0-alpha.2`.
**Requirements:** PHY-16, FR-04, FR-25, IF-03, IF-05; VER-46, VER-49, VER-57, VER-61, VER-62,
VER-76; REV-135. **Implementing session:** Sonnet, high effort; D3's lookup and D5's re-pin stay
`main`. Tag `v0.6.0-alpha.3`.

**Clauses amended when it lands:** PHY-16 (step 3 placed before stage 2; the U2 NOTE written into the
text); FR-04 and its Appendix A row; §5.2's stage-2 and stage-7 rows and the stage-7 design note;
§5.3.1's NOTEs on `inputs:` (the two chains), on `geometry.density` (the key, D3's lookup, D2's
refusal) and on the schema identifier; §5.3.1's IF-03 identifier wherever it is cited.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Walk | `protonation` keeps number 7 and is registered after `structure`, before `density`. Stage 2 takes it as an optional input. It walks when a deposition reads it, when `ResolvedCase.density_protonated` holds (`density` not None and `atoms == "protonated"`), or when it is named as the target. Beside `inputs.charge` it runs for the density alone | U2; manifests cite stage numbers. Registration order is the walk's order (`core/stages.py:register`) |
| D2 Switch | `geometry.density.atoms: protonated \| as_loaded`, default `protonated`, a switch path in `io/defaults.py`. The schema identifier moves to `nanopnp/case/v0.6`. A `v0.5` document is refused, the message naming the migration: set the identifier, and add `atoms: as_loaded` to keep v0.5's density. `protonated` beside a produced protonation under `charge.forcefield` other than `CHARMM` is refused at resolution, naming both keys | §5.3.1: adding a key moves the schema (G6). SWANSON's hydrogen names are not in the CHARMM set (Grounding) |
| D3 Atoms and radii | Under `protonated`, stage 2 deposits each frame's own atoms from the protonation table, at its positions. Each atom's `R_i` comes from the CHARMM set: first from its residue's state patch (the table's `tautomer` for HIS; `ASPP` for an ASP holding `HD2`; `GLUP` for a GLU holding `HE2`), by that patch's own entry. Otherwise it comes from `RadiusSet.radius_A` on the residue's parent name, or the existing refusal applies. `ProtonationTable` and `PARENT_RESIDUE`/`parent_residue` move to `structure/protonated.py`, re-exported where they are now | §5.3.1: CHARMM set, no fallback by element. density sits below charge, and upward edges only shrink (VER-61). It reproduces PDB2PQR's own CHARMM radius on every atom (Grounding) |
| D4 Keys | Under `as_loaded`, stage 2's key is byte-identical to today's: parameters without `atoms`, inputs `structure` alone. Under `protonated` it adds the parameter `"atoms": "protonated"` and the input `"protonation"`. The header records `atoms` and the table's payload digest. Artefact schemas are unchanged | No as-loaded cache entry or golden moves |
| D5 Goldens | AG8: examples 06 and 07 take the default, and example 07's VER-62 walk is re-pinned in the reference environment. `2wcd-charged`, `2wcd-shell`, Tier 3, VAL-05/06 and every test whose oracle was set on as-loaded atoms set `as_loaded` | The author, 3 November 2026. The re-pin is predicted: the conductance falls. A rise is investigated before re-pinning |

### Grounding

**D1.**
- `core/stages.py:_register_builtins` registers `protonation` after `mesh`, with inputs
  `(case, structure)`. `register` refuses an input registered later. `charge`'s inputs already name
  `protonation`.
- `pipeline/run.py:selected_stages` drops `protonation` unless `resolved.deposits_charge`, or unless
  `upto == "protonation"` and the case protonates. The closure for `upto` adds each stage's declared
  inputs.
- A structure case beside `inputs.profile` is refused at resolution, so stage 2 runs exactly when
  `resolved.density` is not None.
- `charge/protonation.py:_resolved` refuses unless `resolved.protonates`, which is false beside
  `inputs.charge`. `examples/07-pdb-to-charged-run/resupplied.case.yaml` is structure plus
  `inputs.charge` and shares 07's mesh.
- `pipeline/run.py:_protonation_reason` and `_short_of_stage_7` word the not-run reasons. The probe
  of the walk order, today: `case, structure, density, symmetry, contour, region, mesh, protonation,
  charge, …`.
- `tests/tier1/test_run.py` iterates `walk_order()`. `test_figures.py`, `test_solve_hook.py` and
  `test_stage_conformance.py` read it too.

**D2.**
- `io/case.py:Density` has `grid_spacing_nm`, `kernel` and `sharpness`.
- `pipeline/case.py:_resolve_density` returns `Density()` for any structure case and refuses bad
  values, so D2's refusal goes there.
- `io/defaults.py:SWITCH_PATHS` lists the switches. `_block_absent` skips a path whose block is
  absent, and `_VALIDATED_DEFAULTS` must read each path. `CONFIGURATION_PATHS` holds the
  non-switch literals.
- `validation/case_leaves.py` lists `geometry.density.*` leaves.
- `tests/tier1/test_case_json_schema.py` checks the generated schema's leaves against the fields.
- `nanopnp/case/v0.5` occurs in 3 `src` files (`io/artefact.py:CASE_SCHEMA`, `io/case.py` twice,
  `core/stages.py`'s stage-9 schema), and in 49 test files, examples, `docs/`, `README.md`,
  `CLAUDE.md` and specification text.
- `io/resolved.py:SOLVE_IRRELEVANT_PROVENANCE` holds `schema`, so no solve key moves.
  `tests/tier2/test_exclusion_keys.py`'s pinned keys (a profile and PQR case) do not move.
- PDB2PQR 3.8 under `--ff=SWANSON` on `data/structures/2wcd-a-18-26.pdb` writes AMBER hydrogen
  names (`H`, `HB3`, `H1`). Fourteen are unresolved, and every heavy radius differs from CHARMM's.
  `PEOEPB` failed on the fragment.

**D3.**
- `density/stage.py:DensityStage.run` reads `AlignedEnsemble` and calls `density/radii.py:resolve_radii`,
  `union.py:check_positions`, `canonical_grid` and `deposit`.
- `deposit` takes `(frames, atoms, 3)` with one width per atom, and builds one stencil set
  (`_stencils`) for every frame.
- A protonation table is ragged: `frame_offsets` slice the concatenated atoms. Frames can differ in
  atoms, for example a HIS tautomer.
- `charge/protonation.py:ProtonationTable` (arrays plus `read`, `write` and `digest`) imports
  `PQRFrame` only for `pqr_frames`, whose callers are `export_pqr` and
  `tests/tier1/test_protonation.py`. Its digest string comes from `io/artefact.py:PROTONATION_SCHEMA`.
- `charge/protonation.py` imports `density/radii.py`. Layer order: core, io, structure, density, …,
  charge.
- `charge/pqr.py:_frame` writes one name per residue: the variant where PDB2PQR labelled one
  (`ASPP`), else the parent.
- At pH 2 the fragment's ASP 21 and ASP 25 read `ASPP`. Its N-terminal GLU 18 is protonated but
  written `GLU`, holding `HE2` with `OE2` at 1.77 Å.
- Today's lookup (`protonation.py:_table_radius`) leaves `GLU HE2` unresolved and gives `OE2` 1.70 Å.
- `GLUP` and `ASPP` are side-chain patches in `data/radii/pdb2pqr_charmm.yaml` (OE2 and OD2 at
  1.77 Å, the acid H at 0.2245 Å). At pH 7.5 every atom resolves and agrees with the PQR.
- The table has exactly the ensemble's frames: `_produced` loops `ensemble.frames`, and `_supplied`
  refuses a different count. Positions are rounded to 0.001 Å.

**D4.**
- `density/stage.py:density_parameters` dumps the whole `Density` block, so `atoms` must be
  excluded from it. The key's inputs are `{"structure": …}`.
- `validation/comsol.py:case_identity` reads no geometry key, so identities do not move.

**D5.**
- `tests/tier2/data/number_stability.json` walks: `2wcd-charged`, `2wcd-shell` (from
  `test_pipeline_2wcd.py` and `test_exclusion_2wcd*.py`), `example-07` (one mesh at X86_V3, one at
  X86_V4), and four idealised-pore walks with no structure.
- `validation/stability.py:fold` refuses a fold whose derived tolerance exceeds 10⁻³, and `--replace`
  re-pins a known mesh only.
- This container is `linux-x86_64/X86_V4`. `gate.sh` caps NumPy with
  `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`.
- `tests/data/structures/2wcd.pdb.gz` has 53,688 atoms and no hydrogen
  (`test_density_2wcd.py` asserts `hydrogens == 0`).
- `test_examples_07_*.py` asserts 07's manifest lists no deviation.
- `test_examples_06_*.py:test_ver46_06_the_exported_map_overlays_the_aligned_structure` bounds the
  map by the structure's atoms.
- Structure cases reaching stage 2 in tests:
  - `tests/conftest.py`;
  - in Tier 1: `test_contour`, `test_density`, `test_reduction`, `test_region`, `test_run`, `test_cli`,
    `test_gui_assess` and `test_gui_probe`;
  - in Tier 2: `test_charge_2wcd`, `test_contour_2wcd`, `test_density_2wcd`, `test_exclusion_2wcd`,
    `test_exclusion_2wcd_walk`, `test_gui_geometry_2wcd`, `test_pipeline_2wcd`, `test_val05_2wcd` and
    `test_val06_2wcd`;
  - in Tier 3: `conftest.py` and `test_structure_ensemble.py`.
- The synthetic C12 ring protonates in about 1 s; PDB2PQR doubles it to 996 atoms. The web fixture
  states use a profile and a PQR, with no structure.

### Implementation details

**Item 1.**
- `structure/protonated.py` holds `ProtonationTable` (without `pqr_frames`), `PAYLOAD_NAME`,
  `PARENT_RESIDUE` and `parent_residue`.
- `read` refuses a missing array with a `ValueError` subclass defined there. `PQRError` subclasses it,
  so existing `pytest.raises(PQRError)` still pass.
- `charge/protonation.py` gains `pqr_frames(table)`. `charge/pqr.py` and `charge/protonation.py`
  import the moved names back.

**Item 2.**
- The refusal text: `schema 'nanopnp/case/v0.5' is retired: declare 'nanopnp/case/v0.6'; a case
  with structure: that keeps v0.5's geometry adds geometry.density.atoms: as_loaded`.

**Item 3.**
- The command, from the repository root:
  ```bash
  git grep -l "nanopnp/case/v0.5" -- . ':!specification/history' ':!CHANGELOG.md' ':!docs/plans' ':!docs/code_reviews' ':!docs/_generated' ':!knowledge/log.md' | xargs sed -i 's#nanopnp/case/v0\.5#nanopnp/case/v0.6#g'
  ```
- Restore the retired-identifier tests in `tests/tier1/test_case.py` to the old literal where they
  assert a refusal of `v0.5`.
- Then run `uv run pytest -m tier1 -x -q`.

**Item 5.**
- `density/radii.py:resolve_protonated_radii(name, table) -> ResolvedRadii`:
  - per frame, collect each residue's atom names;
  - take its state patch: HIS `table.tautomer[f, r]`, ASP with `HD2` → `ASPP`, GLU with `HE2` →
    `GLUP`, else none;
  - for each atom, use `radius_set.residues[patch][atom]` when present, else
    `radius_set.radius_A(parent, atom)`;
  - raise `DensityInputError` as `resolve_radii` does, naming frame, chain, residue and atom;
  - return the radii flattened in table order.
- `union.py`: `check_positions`, `canonical_grid` and `deposit` accept a sequence of per-frame
  `(atoms_f, 3)` arrays with a matching sequence of widths. A single widths array keeps one stencil
  set, so the as-loaded arithmetic is unchanged.

**Item 9, the re-pin.**
- Delete `walks["example-07"]` from the golden.
- Run:
  ```bash
  NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" uv run pytest tests/tier2/test_examples_07_pdb_to_charged_run.py -k ver62
  ```
- Save the record it prints, then run
  `uv run tests/tier2/data/merge_number_stability.py --entry <record>`.
- Record the old and new values and element counts in the PR.

### Work items

- [ ] 1. `structure/protonated.py`; `charge/protonation.py` and `charge/pqr.py` re-export; `pqr_frames(table)`; `docs/project/modularity-layering.yaml` if an edge appears (D3). Done when `uv run pytest -m tier1 -k "protonation or layering or charge"` passes. **Executor:** `general-purpose` on Sonnet.
- [ ] 2. `io/case.py:Density.atoms`; `io/artefact.py:CASE_SCHEMA` and `core/stages.py` at `v0.6` with the refusal; `io/resolved.py:density_protonated`; `pipeline/case.py:_resolve_density`'s force-field refusal; `io/defaults.py` switch and validated default; `validation/case_leaves.py` (D2). Done when `test_case*.py` and `test_defaults*.py` pass. **Executor:** main.
- [ ] 3. The identifier sweep of *Implementation details*. Done when Tier 1 collects and `test_case.py` passes. **Executor:** `general-purpose` on Haiku.
- [ ] 4. `core/stages.py` registration order and stage 2's optional input; `pipeline/run.py:selected_stages`, `_protonation_reason`; `charge/protonation.py:_resolved` (D1). Done when the walk-order tests of *Verification* pass. **Executor:** main.
- [ ] 5. `density/radii.py:resolve_protonated_radii`; `density/union.py` ragged frames; `density/stage.py` key, run and header (D3, D4). Done when the VER-49 rows pass. **Executor:** main.
- [ ] 6. Compaction checkpoint. **Executor:** main.
- [ ] 7. `geometry.density.atoms: as_loaded` on each Tier 1 to 3 case of D5's list whose oracle was set on as-loaded atoms; a case that only checks the walk's mechanics keeps the default. Done when `uv run pytest -m tier1` passes. **Executor:** main.
- [ ] 8. The nightly files of D5's list, under `--nightly`, with the 2WCD walks at `as_loaded`, and VER-62 unmoved for them. Done when they pass. **Executor:** main.
- [ ] 9. Examples 06 and 07 under the default: their READMEs; the example-06 overlay test's atom set; example 07's re-pin (D5). Done when `test_examples_06_*` and `test_examples_07_*` pass under `--nightly`. **Executor:** main.
- [ ] 10. The clauses of the Execution brief; `CHANGELOG.md`; `cli/reference.py`'s `geometry` prose; a `knowledge/04-clya-geometry-and-charge/` note on PDB2PQR's residue and hydrogen names, `[tested]` by item 5's test; REV-135 `fixed`. Done when the code and review say so, and the strict documentation build passes. **Executor:** main.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_density.py::test_ver49_a_changed_protonation_state_moves_the_density` | 1 | VER-49, PHY-16 (U2) | Fragment 18–26 protonated at pH 2 and 8. Under `protonated`, the keys differ and the maps differ by more than 10⁻³ in some voxel. Under `as_loaded`, the two keys are equal, equal to the key built with no protonation upstream, carry no `atoms` parameter, and the maps are byte-equal | `uv run pytest tests/tier1/test_density.py` |
| `tests/tier1/test_density.py::test_ver49_protonated_radii_are_pdb2pqr_charmm_radii` | 1 | VER-49, VER-57 | At pH 2 and 8, every atom's stage-2 radius equals the table's `radius_nm` to 10⁻¹² nm. The table's radius is PDB2PQR's own CHARMM radius. This includes GLU 18 `HE2` and `OE2`, and ASP 21 `HD2` | same |
| `tests/tier1/test_density.py::test_ver49_the_protonated_map_deposits_the_tables_atoms` | 1 | VER-49 | The stage-2 map equals `deposit` of the table's per-frame positions and widths, by `np.array_equal`. A two-frame uniform ensemble deposited as ragged frames equals the stacked call | same |
| `tests/tier1/test_run.py::test_protonation_walks_before_the_density_it_feeds` | 1 | U2 (core mechanism) | Under the default, `selected_stages` puts `protonation` before `density`, including for `upto="mesh"`, an uncharged model and `inputs.charge`. Under `as_loaded` with an uncharged model it is absent | `uv run pytest tests/tier1/test_run.py` |
| `tests/tier2/test_protonation_2wcd.py::test_ver57_every_heavy_radius_is_the_charmm_tables`, extended | 2, nightly | VER-57 | On the protonated dodecamer, `resolve_protonated_radii` equals `radius_nm` on every atom | `uv run pytest tests/tier2/test_protonation_2wcd.py` |
| `tests/tier2/test_examples_07_pdb_to_charged_run.py::test_ver62_07_…` | 2, nightly | VER-62 (AG8) | Re-pinned once in the reference environment; 10⁻⁸ thereafter. Predicted: the conductance below the old pin | item 9's command |
| The VER-62 walks `2wcd-charged`, `2wcd-shell` and examples 01 to 03 | 2 | VER-62 | Unmoved at 10⁻⁸ | `uv run pytest --nightly tests/tier2/test_pipeline_2wcd.py tests/tier2/test_exclusion_2wcd_walk.py` |

### Out of scope

- The charge mutator, which reuses D1 and D3: WP5.04.
- Folding example 07's mesh for environments other than X86_V3, when their nightly prints it (VER-62's
  procedure).
- A protonated density under SWANSON or PEOEPB names. It is refused by D2 until a radius set with
  their names exists. No package owns it, and REV-180 records it.

### Open questions

None. The author ruled AG8 at this plan.
