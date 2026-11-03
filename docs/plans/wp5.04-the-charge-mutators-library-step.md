# WP5.04 — The charge mutator's library step

**Status: planned, not started.** Planned 3 November 2026, on `v0.6.0-alpha.3`. It inherits §8.2.17 S4, §8.2.19 U6,
§8.2.28 AD3 and §8.2.31 AG9 to AG11, ruled at this plan.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** A case can now change one residue of the pore, on every copy of it in the ring. It
can fix a residue's protonation state, whatever the pH would give. It can add or remove a whole charge
on the residue's acid or base group, or make its atoms larger or smaller. The changed pore is a variant
of the original. Each run keeps the original beside it and records exactly which residues differ and
how. Because the pore's shape is built from the same atoms, a changed state or size moves the wall
too. A case without changes gives the same numbers, to the last digit, as before.

**Cost.** About a week. Changing a charge or a size costs a few seconds once the original has been
built. Fixing a state runs the protonation again, about a minute per frame of the ClyA ring, once per
variant.

**What could go wrong.** The state is fixed by stepping into the protonation program's procedure.
A later version of that program could silently ignore the request, so every run checks that the state
it asked for is the one it got, and stops otherwise. Changing one residue's state could shift a
neighbour's hydrogens; the record lists every residue that moved, not only the one asked for.

**Your call.** None open. You ruled the three questions at this plan: where a charge goes, how a size
changes, and how a variant is recorded.

## Execution brief

**Scope.** `charge.edits`, applied at stage 7's `protonation` step; the variant with its parent and
difference; stage 2 reading a radius edit. **Depends on:** `v0.6.0-alpha.3`. **Requirements:** FR-38, PHY-16 step 3, FR-12, FR-25, IF-03; VER-49, VER-57,
VER-62, VER-71, VER-24. **Implementing session:** Sonnet, high effort; D2, D3 and D5 stay `main`.
Tag `v0.6.0-alpha.4`.

**Amended when it lands:** §5.2's stage-7 row and note; a §5.3.1 NOTE on `charge.edits`; §5.3.3's
charge group; PHY-16 step 3's NOTE. FR-38 and the Charge edit row are amended in this commit (AG9 to AG11).

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Case | `charge.edits`, a list, default empty. Each entry: `residue` (`"ASP 21"`, `"HIS 292A"`: parent name, number, optional insertion code) and exactly one of `state` (`charged` or `neutral`), `charge_change_e` (a non-zero integer) and `radius_scale` (finite, above 0). An edit applies on every chain and frame. One entry per kind per residue; `state` beside `charge_change_e` on one residue is refused. `state` is refused off ASP, GLU and HIS, beside `titration: none`, under a force field other than CHARMM and beside `inputs.pqr`. `charge_change_e` is refused on a residue with no group (AG9). Every edit is refused beside `inputs.charge`. The schema stays `nanopnp/case/v0.6` | G6. CHARMM holds no LYS⁰, ARG⁰, CYS⁻ or TYR⁻. A change, not a target: a terminal residue's charge includes its terminus |
| D2 Pin | During PDB2PQR's call, `Biomolecule.apply_pka_values` is wrapped. The wrapper drops each pinned residue's `pka_key(parent, resid, chain, icode)`, on every chain, calls the original, then applies `ASH`, `GLH` or `HIP` for `neutral` ASP, `neutral` GLU and `charged` HIS. The standard state takes no patch. Each frame's key gains `pins` only when pins exist. After assembly, a gate refuses a frame whose pinned residue does not hold its state: `HD2` for neutral ASP, `HE2` for neutral GLU, tautomer `HSP` for charged HIS, the converse for the standard state. It names frame, chain and residue. A pinned residue is never `unapplied` | PROPKA's pKa table stays whole, and both states can be pinned; renaming cannot pin the standard one |
| D3 Charge and radius | Applied to the assembled table, after the pins and the radius comparison. `charge_change_e` is spread evenly over the residue's group atoms present in that frame. The groups are PROPKA's charge-centre atoms, in `data/charge/titratable_groups.yaml`. `radius_scale` multiplies `radius_nm` of every atom of the residue. `residue_charge_e` is recomputed; the edits go to `header["edits"]` | AG9, AG10. `Q_net` stays an integer; a fractional charge is FR-43's (REV-183) |
| D4 Stage 2 | Under `protonated`, stage 2 multiplies `resolve_protonated_radii`'s radii by `structure/protonated.py:radius_scales(table)`, which also sets D3's radii | Stage 2 reads radii by name, never `radius_nm`. Under `as_loaded` the density does not move (U2) |
| D5 Variant | With edits, the payload adds `parent`, the unedited table, beside `protonation`. The summary adds `variant_of`: `parent` (the unedited key's hash), `edits`, `residues` (each residue whose atoms, charges or radii differ, per chain: both charges per frame, atoms added and removed, the largest radius change) and `q_net_e` (`parent` and `variant` per frame). `charge.edits.0.state` is in `CONFIGURATION_PATHS`, with AG11's reason. No edit is a deviation | AG11. The manifest's charge group carries the protonation summary already |
| D6 Keys | Without edits, every key (protonation, each frame, stages 2 and 7) is byte-identical to today's. With edits, `protonation_parameters` adds `edits`, sorted by `(resid, icode, kind)`. A frame key adds `pins` only for `state` edits, so charge and radius variants reuse the parent's stored frames | VER-62 at zero drift; a variant costs its edits only |

### Grounding

**D1.**
- `io/case.py:Charge` holds `ph`, `forcefield`, `titration`, `smearing` and the two offsets.
  `pipeline/case.py:_resolve_protonation` builds `io/resolved.py:ResolvedProtonation(ph, forcefield, titration)`.
- `pipeline/checks.py:_check_charge` refuses `PROTONATION_KEYS` with a `where` clause. Under that rule a
  charge or radius edit beside `inputs.pqr` would be refused, so the edits get their own `_check_edits`.
- `io/case_paths.py:case_fields` names list leaves `electrolyte.species.0.name`.
  `tests/tier1/test_manifest.py::test_ver24_every_switch_typed_field_of_the_schema_is_classified`
  requires `charge.edits.0.state` in `SWITCH_PATHS` or `CONFIGURATION_PATHS`, and
  `validation/case_leaves.py:LEAVES` must classify each new leaf (VER-71).
- `charge/pqr.py` reads PDB2PQR 3.8's terminal-patch atoms under their residue's name (GLU 18 holds
  `HT1`–`HT3`, LEU 26 `OT1`/`OT2`), so `residue_charge_e` of a terminal residue includes its terminus.

**D2.**
- In PDB2PQR 3.8.0, `main.non_trivial` calls `biomolecule.apply_pka_values(forcefield_.name, args.ph,
  {pka_key(res_name, res_num, chain_id, ins_code): pKa})` only under `--titration-state-method=propka`.
  `apply_pka_values` pops each key and applies `ASH`, `GLH` or `HIP` by pH against pKa. With the key
  absent, the residue keeps the standard state.
- On fragment 18–26 at pH 7.5, holding ASP 21's key out and applying `ASH` gives the same atom lines
  as renaming the input residue `ASH`. Every other atom is identical to the unpinned PQR. PROPKA's pKa
  rows are unchanged, while renaming drops ASP 21's row. At pH 2, holding the key out gives a charged
  ASP 21 (−1) where PROPKA protonates it. An input residue named `ASP` is titrated, so renaming cannot
  pin the charged state.
- On chain A 288–292, `HIP` at pH 7.5 gives HIS 292 `HD1` and `HE2`. Held out at pH 4, it is neutral
  with `HD1`. HIS 292 also carries a `C-` row with the same number, so the key names the residue, not
  the number.
- Under CHARMM, `apply_pka_values` warns and keeps the standard state for CYS⁻, LYS⁰, TYR⁻ and ARG⁰
  (`knowledge/07-software-stack/03-charge-and-electrostatics.md`).
- `charge/protonation.py:ProtonationStage._produced` keys each frame on
  `protonation_parameters(settings)`. `run_pdb2pqr` calls PDB2PQR in-process inside `_quiet_libraries`.
  `restore_propka_annotations` patches a library attribute in-process.
- `_assemble` sets `unapplied` where `|residue_charge − expected| > 0.5`.

**D3.**
- PROPKA 3.5.1's `propka.cfg` anchors the groups: `protein_group_mapping` ASP-CG COO, GLU-CD COO,
  HIS-CG HIS, CYS-SG CYS, TYR-OH TYR, LYS-NZ LYS, ARG-CZ ARG. `group.py`'s `setup_atoms` takes the
  anchor's bonded oxygens for COO, the ring nitrogens and their hydrogens for HIS, and the nitrogens
  bonded to CZ and their hydrogens for ARG. For CYS, TYR and LYS it takes the anchor alone.
- `data/radii/pdb2pqr_charmm.yaml` holds the CHARMM atom names the table carries. `core/paths.py:radii_file`
  is the pattern for a data loader, and `pyproject.toml` force-includes `data/` in the wheel.
- `charge/kernel.py:source_atoms` takes the width as `sharpness × radius_nm` and the weight as
  `charge_e / frames`, over the atoms whose charge is not 0. `sum_kernel` renormalises each atom to its
  charge, so the lattice is linear in the atoms' charges.
- `charge/kernel.py:check_spacing` refuses a lattice spacing above half the narrowest kernel width.
  It is the gate for a small `radius_scale` (REV-182).

**D4.**
- `density/stage.py:DensityStage.run`, under `protonated`, calls
  `resolve_protonated_radii(KERNEL_RADII[spec.kernel], table)`. The radii come by name from the CHARMM
  set; `table.radius_nm` is never read. `ResolvedRadii.radii_nm` is in table order.
- Under `protonated`, stage 2's key inputs include the protonation artefact's hash, so an edit moves the
  density key with no change to the key code.

**D5.**
- `ProtonationStage.run`'s summary already has `variant`: `structure.source.variant`, the OPN-04 label.
  So the new key is `variant_of`.
- `io/manifest.py:_charge_group` writes the protonation summary as `charge.protonation`. The manifest's
  eight groups do not change.
- `io/defaults.py:deviations` reads `SWITCH_PATHS` only.
- Stage 2, stage 7's `charge` and `export_pqr` read `payload["protonation"]` alone, so a `parent` entry
  disturbs none of them.

**D6.**
- None of the VER-62 walks in `tests/tier2/data/number_stability.json` carries `charge:` edits.

### Implementation details

**Item 1.**
- `io/case.py:ChargeEdit(_Strict)`:
  - `residue: str`, matching `^[A-Z]{3} -?\d{1,4}[A-Z]?$`;
  - `state: Literal["charged", "neutral"] | None`;
  - `charge_change_e: int | None`;
  - `radius_scale: float | None`, with `allow_inf_nan=False`;
  - a `model_validator` refusing zero or several of the three.
- `Charge.edits: list[ChargeEdit] = Field(default_factory=list, …)`.
- `io/resolved.py:ResolvedEdit(parent, resid, icode, kind, value)`, with `kind` one of `state`,
  `charge`, `radius`. `ResolvedProtonation.edits: tuple[ResolvedEdit, ...] = ()`, sorted by
  `(resid, icode, kind)`.
- `pipeline/checks.py:_check_edits` holds D1's refusals. Each names `charge.edits[<i>]` and the
  clashing key, and cites "section 5.3.1 NOTE on charge.edits".

**Item 2.**
- Write `data/charge/titratable_groups.yaml`:
  ```yaml
  schema: nanopnp/titratable-groups/v0.5
  source: {package: propka, version: 3.5.1, files: [propka/propka.cfg, propka/group.py]}
  anchors: {ASP: CG, GLU: CD, HIS: CG, CYS: SG, TYR: OH, LYS: NZ, ARG: CZ}
  groups:
    ASP: [OD1, OD2]
    GLU: [OE1, OE2]
    HIS: [ND1, NE2, HD1, HE2]
    CYS: [SG]
    TYR: [OH]
    LYS: [NZ]
    ARG: [NE, NH1, NH2, HE, HH11, HH12, HH21, HH22]
  ```
  Put a comment header with the source, as `pdb2pqr_charmm.yaml` has.
- Add `core/paths.py:charge_data_file(name)`, by `radii_file`'s pattern.
- Add `charge/edits.py:TitratableGroups.load()`, a pydantic model.
- Add the test of *Verification*'s row 6.

**Item 3.**
- `charge/protonation.py:_pinned(pins)` is a context manager that swaps
  `pdb2pqr.biomolecule.Biomolecule.apply_pka_values` and restores it in `finally`. The patches are
  `{("ASP", "neutral"): "ASH", ("GLU", "neutral"): "GLH", ("HIS", "charged"): "HIP"}`.
- The wrapper walks `self.residues`. For each `aa.Amino` whose `name`, `res_seq` and `ins_code` match a pin, it pops
  `pdb2pqr.biomolecule.pka_key(residue.name, residue.res_seq, residue.chain_id, residue.ins_code)`, using the chain
  letter PDB2PQR sees. After the original call it applies the patch with `self.apply_patch(patch, residue)`.
- `run_pdb2pqr` takes `pins` and enters `_pinned` inside `_quiet_libraries`.
- `_frame_parameters(settings)` is `protonation_parameters` without `edits`, plus `pins` when any.
- `_assemble` takes the pinned residue indices, for `unapplied` and for the gate.

**Item 4.**
- `structure/protonated.py:radius_scales(table) -> np.ndarray` reads `header["edits"]` entries of kind
  `radius`. It returns 1.0 per atom, except on the matching `resid` and `icode`, on every chain.
- `charge/edits.py:apply_edits(table, edits, groups) -> ProtonationTable`:
  - refuse a residue missing from a chain, or of another parent, naming frame and chain;
  - refuse a charge edit whose group atoms are absent;
  - return the table with the new `header["edits"]`, `charge_e`, `radius_nm` and `residue_charge_e`.
- `charge/edits.py:difference(parent, variant) -> dict` builds D5's `residues` and `q_net_e`.
- In `ProtonationStage.run`, with edits:
  - build the parent table, without pins;
  - build the pinned frames when there are `state` edits;
  - apply the edits;
  - write both tables;
  - add `variant_of`.
- The parent's key hash is `ProtonationArtefact(parameters=protonation_parameters(settings without edits), inputs=key.inputs).hash`.

### Work items

- [ ] 1. `io/case.py:ChargeEdit`, `Charge.edits`; `io/resolved.py:ResolvedEdit`; `pipeline/case.py:_resolve_protonation`; `pipeline/checks.py:_check_edits`; `io/defaults.py:CONFIGURATION_PATHS`; `validation/case_leaves.py` (D1, D5). Done when `uv run pytest -m tier1 -k "case or manifest or defaults"` passes. **Executor:** main.
- [ ] 2. `data/charge/titratable_groups.yaml`, `core/paths.py:charge_data_file`, `charge/edits.py:TitratableGroups`, and *Verification*'s row 6 (D3). Done when that row passes. **Executor:** `general-purpose` on Haiku.
- [ ] 3. `charge/protonation.py`: `_pinned`, `run_pdb2pqr(pins)`, `_frame_parameters`, the pin gate, `unapplied` (D2, D6). Done when rows 1 and 5 pass. **Executor:** main.
- [ ] 4. `structure/protonated.py:radius_scales`; `charge/edits.py:apply_edits`, `difference`; `ProtonationStage.run`'s parent, payload and `variant_of` (D3, D5, D6). Done when rows 2, 4 and 5 pass. **Executor:** main.
- [ ] 5. Compaction checkpoint. **Executor:** main.
- [ ] 6. `density/stage.py`: the radius scales under `protonated` (D4). Done when row 3 passes. **Executor:** main.
- [ ] 7. The clauses of the Execution brief; `CHANGELOG.md`; `cli/reference.py`'s `charge` prose; a `knowledge/07-software-stack/` note on pinning a state through `apply_pka_values`, `[tested]` by row 1; FR-38's Appendix A row. Done when the code and review say so, and the strict documentation build passes. **Executor:** main.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_protonation.py::test_fr38_a_pinned_state_holds_and_changes_that_residue_alone` | 1 | FR-38, PHY-16 | Fragment 18–26 of chains A and B as one ensemble: pH 7.5, ASP 21 `neutral`; pH 2, ASP 21 `charged`. On each chain ASP 21 holds the state, its charge off the parent's by exactly +1 (−1). Every other atom's name, position, charge and radius, and `group_pka`, equal the parent's. `Q_net` moves by twice that. `variant_of.residues` is ASP 21 on A and B | `uv run pytest tests/tier1/test_protonation.py -k fr38` |
| `tests/tier1/test_protonation.py::test_fr38_a_charge_change_moves_the_projected_charge_by_that_residue_alone` | 1 | FR-38, PHY-16 step 4 | The same ensemble, ASP 25 `charge_change_e: +1`. Charges differ only on ASP 25's group atoms, by +1/n each, +1 per chain to 10⁻¹². The variant's `sum_kernel` lattice minus the parent's equals `sum_kernel` of the difference atoms alone, on one grid, to 10⁻¹² of its largest value | same |
| `tests/tier1/test_density.py::test_fr38_a_radius_scale_moves_the_density_and_the_kernel_width` | 1 | FR-38, VER-49 | LEU 24 `radius_scale: 1.2`. Under `protonated`, stage 2's radii are the parent's × 1.2 on LEU 24 and equal elsewhere, to 10⁻¹² nm; key and map differ. `radius_nm` moves on the same atoms by the same factor. Under `as_loaded`, stage 2's key and map equal the parent's | `uv run pytest tests/tier1/test_density.py -k fr38` |
| `tests/tier1/test_protonation.py::test_fr38_without_edits_every_key_is_unchanged` | 1 | VER-62 (D6) | With `edits: []` and with no `charge:` block, the protonation, frame-0 and stage-2 keys equal today's, holding neither `edits` nor `pins`. A radius-only variant reuses the parent's stored frames (`cached_frames` = frames) | `uv run pytest tests/tier1/test_protonation.py -k fr38` |
| `tests/tier1/test_protonation.py::test_fr38_a_pin_that_takes_no_effect_is_refused` | 1 | FR-38 (the pin gate) | `_pinned` replaced by a no-op: the stage raises `ProtonationError` naming frame 0, chain A and ASP 21 | same |
| `tests/tier1/test_library_behaviour.py::test_fr38_the_titratable_groups_are_propkas` | 1 | FR-38 | The data file's `anchors` equal `propka.cfg`'s `protein_group_mapping` for the seven residues. Each group atom is a name of `pdb2pqr_charmm.yaml`'s entry for its residue or its state patch. `Biomolecule.apply_pka_values`, `biomolecule.pka_key` and the patches `ASH`, `GLH` and `HIP` exist | `uv run pytest tests/tier1/test_library_behaviour.py -k fr38` |
| The VER-62 walks | 2 | VER-62 | Unmoved at 10⁻⁸, with no re-pin | `.claude/hooks/gate.sh run` |

### Out of scope

- The Charge edit tool, and the changed count reading `variant_of`: WP5.09 (AG1; AG11).
- Fractional protonation, and the author's customised PDB2PQR route to it: FR-43, a later phase
  (REV-183).
- A histidine's tautomer pin, and a pin beside `titration: none` or under SWANSON and PEOEPB: refused by D1.
- Named molecular models: WP5.05.

### Open questions

None. The author ruled AG9 to AG11 at this plan.
