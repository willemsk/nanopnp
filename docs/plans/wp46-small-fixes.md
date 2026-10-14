# WP46 — The small fixes

**Status: planned, not started**, 14 October 2026. Inherits WP44's loop and WP45's prose rule
(§8.2.11 L4); the register's fifteen rows of §8.2.9 I2 (renumbered by §8.2.10 J1).

The Phase 4 plan owns the phase ([phase plan](phase-4-polish-and-user-testing.md), *WP46*).
`SPECIFICATION.md` governs; identifiers are pointers. The behaviour this package adds is written
into the specification in this plan's commit (D1 to D5), so no item amends a clause on its own.

## In brief

Fifteen small faults found by earlier reviews, each fixed where it lives, with its own test. None should move a computed result beyond round-off.

**What changes.** A salt sweep stops rebuilding the same mesh at every concentration below about
1.5 M. Two sweep members writing the same stored result at once can no longer leave a record that
disagrees with its file. Bad inputs that today crash or are read silently wrong are refused with a
message naming the file: an empty trajectory, a duplicated atom, a molecule wrapped across the
simulation box, a density map written in the wrong length unit. A stage run by hand without a
scratch folder says so instead of writing somewhere of its own choosing. Copied code gets one home.

**Cost.** About a dozen commits; one to two days of machine time, mostly the automatic checks.

**What could go wrong.** A new refusal could reject a real structure, such as one numbered across a
gap; the vendored pore and your ensemble are tested against it, and the message names the residues.
Stored mesh keys change once, so an existing store re-meshes once. Programs that ran a stage
without a scratch folder must now pass one; the change log says how.

**Your call.** Your three rulings of today are written in. Should the wrapped-molecule refusal use
a fixed 1 nm bound rather than the box size the file records? *Recommendation:* yes, since many
files record no box, and no bonded pair comes near 1 nm.

## Execution brief

Scope: the fifteen rows above; REV-47 stays with the close. Depends on WP45 as merged (`068a0d6`).
Clauses amended here: §5.3.1 NOTEs on `numerics.mesh` and `structure:`; the IF-05 NOTE on length
units; the §5.3.2 NOTE on workspace locality; VER-26, VER-29, VER-48, VER-49, VER-53 and VER-54.
Also the shipping skill's stop rule (item 11). No new identifier. Models (`CLAUDE.md`): Sonnet by default; D2's key and D5's gate on Opus, as the
phase plan rules; Haiku for item 9.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Radial grid `.npz` (REV-14) | `write_grid` adds `origin_nm` and `spacing_nm` beside `r_nm`, `z_nm`, `values`; `_read_npz` takes the grid from them when present, refusing a file whose axes disagree with them by more than `UNIFORM_TOL_NM`, and from the axes otherwise. `charge/stage.py`'s re-read goes, so the deposited grid is the summed one | VER-29 amended. The drift is in the last bits of the spacing, far inside VER-62's 1e-8 |
| D2 Stage-6 key (REV-16, Opus) | `WallSize` gains `key()`: `wall_h_nm`, `source`, `size_scale`; `sizing_parameters` uses it and the manifest's `sizing` block keeps `summary()` with λ_D. Every recorded stage-6 or downstream key golden (VER-54's netgen key among them) is re-recorded in the same commit, naming this decision | §5.3.1 NOTE on `numerics.mesh`, VER-53, VER-54 amended. λ_D moves the mesh only through `wall_h_nm`, already in the key |
| D3 `Store.put` (REV-18) | Write payloads and `meta.json` into a fresh sibling directory, then rename it onto `location()`. If a complete entry is already there, discard the staging directory and return `get()` of it (first writer wins); an entry without `meta.json`, left by an older put, is replaced. A payload already inside the target directory is copied, not moved | VER-26 amended. Per-file atomic writes leave a record and a payload from different writers when puts interleave |
| D4 Scratch (REV-25, REV-55) | One helper, `io/workspace.py` `scratch_directory(workspace, prefix)`: a fresh `mkdtemp` inside the given workspace, or `MissingWorkspaceError` naming the `workspace` argument. The eleven stage fallbacks and their `WORKSPACE_DIRNAME` copies go; `pipeline/run.py`'s store scratch, `cli/export.py`'s staging and the shell's probe stay. A break, listed in `CHANGELOG.md` with its migration | Author, 14 October 2026: the cleanest long-term contract. The workspace-locality NOTE amended |
| D5 Structure gates (REV-19, REV-57, Opus) | `load_universe` refuses zero frames naming the file; `select` refuses a second Cα at one `(chain, resid, icode)`. `frame_times` on DCD returns `time_offset + i·dt` without decoding; XTC, TRR and NetCDF decode, their times living in frame headers. The wrap gate runs on the loaded Cα positions: consecutive residue numbers without insertion codes in one chain over 1.0 nm apart in any selected frame are refused naming chain, pair, frame and distance. The largest such distance on the vendored 2WCD is measured and recorded in `.knowledge/04` **[tested]** | Author, 14 October 2026, for DCD only. §5.3.1 NOTE on `structure:`, VER-48 amended. A bonded pair is 0.38 nm; a wrapped one is a box length |
| D6 The rest | REV-40: `DensityMap._read_interchange` refuses a spacing outside `GRID_SPACING_RANGE_NM`, which moves from `pipeline/case.py` to `density/` (an edge down the order). REV-59: `attribute_to_construction` refuses a comparison with uncrossed planes with `GeometryComparisonError`, before binning. REV-15: `#SBATCH` values are written raw and a value holding whitespace, a quote, `#`, `%` or a control character is refused naming the key. REV-43: `chain_characters` moves to `structure/ensemble.py` and `AlignedEnsemble.export` uses it. REV-49: `Measures.at_order(order)` replaces every `replace(AXISYMMETRIC, element_order=…)`. REV-50: the tier-2 test uses `innermost_crossings`. REV-51: `ReopenedRun` carries its `ResolvedCase` and the CLI stops re-resolving. REV-24: count SI-expression builds per field per Newton iterate; remove the duplicate only if the count exceeds one, recording the count either way | Author, 14 October 2026, for REV-40. IF-05 NOTE and VER-49 amended. Each row is local and moves no number |

### Work items

Each item sets its `REV-nn` rows `fixed` in `docs/project/review-findings.md`, linking this plan,
and gives each `review-items.md` section a *Resolved* line.

- [x] 1. 6891891 `density/grid.py`, `charge/stage.py` (D1); done when the round-trip and legacy-read tests of *Verification* pass and VER-62 holds.
- [x] 2. 0cf9b46 `mesh/sizing.py`, `mesh/generate.py`, any re-recorded key golden (D2); done when the shared-key test passes and VER-62 holds.
- [x] 3. 84fe7e3 `io/store.py` (D3); done when the interleaving and two-process tests pass.
- [x] 4. 136f83c `io/workspace.py`, the eleven stage modules, their tests' `workspace=`, `CHANGELOG.md` (D4); done when the refusal test passes and VER-61 holds.
  > **Outcome — D4 writes into the workspace itself.** `scratch_directory(workspace, stage)` returns the workspace, created, rather than a fresh `mkdtemp` under it: the walk already gives each stage a fresh `<run scratch>/<stage>` directory, and a named workspace keeps `work/mesh/mesh.msh` where `test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads` and the examples read it. Ten stage modules held a fallback (the registry has ten workspace stages).

*Compaction checkpoint: after item 4; resume from this plan and `git log`.*

- [x] 5. 80da6ff `structure/read.py`, `structure/stage.py`, `.knowledge/04-clya-geometry-and-charge.md` (D5); done when the refusal and frame-time tests pass and the 2WCD walk passes.
- [x] 6. 58103bd `density/map.py`, `pipeline/case.py`, `modularity-layering.yaml` if the edge is new (D6, REV-40).
- [x] 7. 13d1cb3 `validation/geometry.py` (REV-59) and `examples/05-clya-reference/render_slurm.py` (REV-15).
- [ ] 8. `charge/pqr.py`, `structure/ensemble.py` (REV-43); `numerics/measures.py` and its callers (REV-49); `validation/runs.py`, `cli/__init__.py` (REV-51).
- [ ] 9. `tests/tier2/test_axis_weight_order.py` (REV-50).
- [ ] 10. REV-24: the count, recorded in this plan's Outcomes and the row's ruling; the cache only if needed.

- [ ] 11. `.claude/skills/wp-ship/SKILL.md` §6 and `.claude/skills/steward/SKILL.md` *Bounded wakes*: once CI is green and the PR mergeable, report once, unsubscribe and cancel the check-in, so a merge does not wake a cold session; `/wp-ship` resumes (author, 14 October 2026).

*Compaction checkpoint: after item 10; then the push gate and `/wp-implement`'s PR.*

### Verification

Tier 1 unless stated; command `uv run pytest --extended`, then `.claude/hooks/gate.sh run`.

| Test | Identifiers | Oracle and tolerance |
|---|---|---|
| `test_charge_fields.py::test_ver29_npz_round_trips_origin_and_spacing_bitwise` and `…_axes_only_npz_still_reads` | VER-29 | Equality of `origin_nm`, `spacing_nm` and `digest()` before and after; an axes-only file gives today's grid; disagreeing axes are refused |
| `test_mesh_generate.py::test_ver53_salt_below_ceiling_shares_stage6_key` | VER-53, VER-54 | Keys at 0.15 and 1.0 M equal; at 2 and 3 M different; manifest `sizing` still carries λ_D |
| `test_artefact_hashing.py::test_ver26_interleaved_puts_leave_one_consistent_entry` and `…_two_processes_race` | VER-26 | Writer B forced between each step of A, then two processes on a barrier; every recorded `sha256` matches its file; both returns equal `get()` |
| `test_stage_workspace.py:: (new) test_stage_without_workspace_refuses_scratch` | — | Each scratch-writing stage of the registry, run without a workspace, raises `MissingWorkspaceError` naming `workspace`; none writes under `store_root()` |
| `test_structure_stage.py::test_ver48_*` (zero frames, duplicate Cα, wrapped chain, DCD frame times) | VER-48 | Each refusal names what D5 says; DCD times equal decoded times exactly with zero frames decoded; 2WCD passes |
| `test_density.py::test_ver49_nm_written_map_is_refused` | VER-49 | A map exported with spacing divided by ten is refused saying nm; the existing exports still read |
| `test_val05_geometry.py::test_lax_comparison_is_refused_by_attribution` | — | `GeometryComparisonError`, not `MissingPlaneError` |
| `test_examples_plan.py::test_sbatch_values_are_raw_and_refused_when_unpassable` | — | A plain name appears unquoted; each forbidden character is refused naming its key |
| Tier 2 `test_axis_weight_order.py` | — | Unchanged result through `innermost_crossings` |
| VER-61, VER-62, VER-63 | — | Layering, golden at 1e-8, the register's rows |

### Out of scope

REV-47 (the close). Header-only times for XTC, TRR and NetCDF (not needed by any shipped case;
reopened only by a measured need). The shell's probe directory (Phase 5).

### Open questions

None blocking. The wrapped-chain bound (In brief, *Your call*) defaults to D5 unless ruled.
