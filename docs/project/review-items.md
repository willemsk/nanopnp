# Review register

What a work package's implementation or review left open, one numbered item each, `REV-nn`,
until it is resolved (§8.2.8 H12). `/np-implement` and `/np-ship` add an item in the commit that
leaves it open: a confirmed review finding not fixed, a deferral to a later package, or a question
put to the author. The commit that resolves one sets its row `fixed`. The status of each item is in
[the findings log](review-findings.md), read at review (§8.2.13 N3); this page says what each one is.

Each item gives where it was found, what was measured, and what resolves it. Unlike the
[modularity findings](modularity-findings.md), the register is never closed: it is not one of the
two logs Phase 4's gate closes.

## Items

### REV-01 — TOL_NM's home loaded pydantic and yaml

*Area:* performance. *Severity:* low. *Found:* WP37's shipping review (PR #80).

**Measured.** WP37 D6 moved `TOL_NM` into `geometry/profile.py`, which imports pydantic and yaml
at module scope. A bare `import nanopnp.mesh.primitives` rose from 71 ms on `a346419` to 179 ms,
and `nanopnp.geometry.analyte` to 151 ms (`python -X importtime`, warm cache). The CLI and GUI
entry points were unaffected, because they load pydantic anyway.

**Resolved.** `TOL_NM` lives in `geometry/tolerance.py`, which imports nothing: 62 ms and 54 ms.

### REV-02 — cli/errors.py was a re-export nothing imported

*Area:* coupling. *Severity:* low. *Found:* WP37's shipping review (PR #80).

**Measured.** WP37 D9 kept `cli/errors.py` as a re-export of `core/errors.py`, and no module of
`src/` or `tests/` imported it, against D10's "no shim at an old path".

**Resolved.** The module is removed; `core/errors.py` is the exit table's one home (IF-01: an
internal path is not API). `CHANGELOG.md` lists the removal.

### REV-03 — The solution-field names lived in two layers

*Area:* coupling. *Severity:* low. *Found:* WP37's shipping review (PR #80).

**Measured.** After WP37 D8, `POTENTIAL`, `VELOCITY` and `VELOCITY_AXIS` are defined in
`mesh/primitives.py` and `PRESSURE` and `PRESSURE_MEAN` in `physics/models.py`.
`io/fields.py`, `post/qoi.py`, `validation/compare.py` and `validation/mms.py` import field names
from both, and a new field has two possible homes.

**Resolved.** WP38 D9: the five names live in `io/vocabulary.py`, in the base layer, and
`mesh/primitives.py` and `physics/models.py` import them from there.

### REV-04 — VER-61's ratchet did not see an import moved into a function

*Area:* verification. *Severity:* medium. *Found:* WP37's shipping review (PR #80).

**Measured.** The `upward:` list covered only `top` imports. An upward edge already in the static
relation as a `TYPE_CHECKING` import (`geometry → mesh`) could come back as an import inside a
function, and neither the static relation nor `upward:` would change: WP37 D12, "a deferred import
is not a cut", was held by review alone. One such edge existed, `gui → nanopnp`.

**Resolved.** A `deferred_upward:` list records it, VER-61 asserts it both ways, and a
function-scope import of `nanopnp.mesh.primitives` in `geometry/analyte.py` fails naming the edge,
the module and the line.

### REV-05 — The shells read the nanopnp facade

*Area:* coupling. *Severity:* low. *Found:* WP37's shipping review (PR #80).

**Measured.** `cli → nanopnp` (`from nanopnp import __version__` and `PUBLIC`) is the one `top`
edge pointing up the order outside `io`, and `gui → nanopnp` (`gui/probe.py`, inside a function)
the one deferred one. Neither closes a cycle. Its `upward:` row carried no finding, against the
layering file's own header.

**Resolved.** WP39 D9: a new `core/public.py` holds `__version__` and `PUBLIC`. The facade imports both, and `cli/__init__.py`, `cli/reference.py` and `gui/probe.py` import from `nanopnp.core.public`. The `upward:` and `deferred_upward:` lists in `modularity-layering.yaml` are now empty.

### REV-06 — A supplied charge or permittivity field has no stated frame beside a moved structure

*Area:* physics. *Severity:* medium. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** A supplied `inputs.charge` or `inputs.eps_r` field beside a `structure:` case with
`centre_z_nm ≠ 0` is accepted, and the specification says the deposited lattice and atoms are in the
model frame but not which frame a supplied field is in. A field in the structure's frame would be
applied offset by `centre_z_nm`.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-07 — The conservation gate and the Poisson source integrate an areal charge differently

*Area:* numerics. *Severity:* medium. *Found:* CODE_REVIEW_002 (PR #44), *Leads not settled*.

**Measured.** The gate integrates the assembled fixed charge with `singular=True` for an areal field
(`charge/fields.py`, `assembled_total_C`), while the Poisson source assembles without it. On a
synthetic alternating field the two differed by 1e-5 to 1e-3 relative. Whether that exceeds QR-03 on
the aliased ClyA table needs that table.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-08 — Newton's update test takes one norm over every field

*Area:* numerics. *Severity:* medium. *Found:* CODE_REVIEW_002 (PR #44), *Leads not settled*.

**Measured.** `numerics/newton.py` tests `‖δu‖ / max(‖u‖, reference_norm)` with one ℓ2 norm over all
fields. With `a = 1 nm`, ũ ~ 1e-3, so the velocity and pressure blocks may be only about 1e-3
relatively converged when the test passes. The code matches NUM-16 as written, so this is a question
of the specification, for EOF and hydrodynamic-force accuracy.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-09 — A driver clamp under the ionic-strength driver is never logged

*Area:* physics. *Severity:* medium. *Found:* This register's sweep of PR #13 (Phase 0
consolidation), verified at `5559c7e`.

**Measured.** `report_clamp_activations` (`materials/electrolyte.py`) logs per-species clamps on the
premise that the driver it returns never exceeds the validity limit. Under the opt-in
`ionic_strength` driver, `I = ½ Σ zᵢ² cᵢ`: for CaCl₂ at 2 M Ca²⁺ and 4 M Cl⁻ no species exceeds 5.3
M, but `I = 6 M`. The correction model clamps the driver (`materials/models.py`, PHY-13 holds), and
no clamp is logged, against §5.1's stage-8 test target. No shipped parameter file is multivalent.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-10 — The prose rule let a ruling or a report heading change without VER-63

*Area:* verification. *Severity:* medium. *Found:* PR #77 (WP35), *Deliberately not done*.

**Measured.** `.github/scripts/prose-only.sh` counted `SPECIFICATION.md` and the report pages as
prose, so a commit deleting a §8.2 row a ruling cites, or renaming a finding's heading, ran ruff
alone in the commit hook.

**Resolved.** The script treats `SPECIFICATION.md`, `docs/project/modularity.md` and
`docs/project/review-items.md` as read by tests, and `test_workflow_hooks.py` asserts each.

### REV-11 — No check catches a NaN-permissive gate comparison

*Area:* verification. *Severity:* medium. *Found:* PR #43 (CR-1 to CR-17), a proposed test not
taken.

**Measured.** A gate written `if value > tol: fail` passes a NaN. The instances found were fixed one
by one, and nothing stops a new one: the review's proposed lint over gate modules was not written.

**Resolved.** WP42 D1, D2: VER-70 AST lint over gate modules; 38 comparisons rewritten to negated forms; six exempted with recorded reasons.

### REV-12 — No test shows every case leaf changes the forms or is provenance-only

*Area:* verification. *Severity:* medium. *Found:* PR #43 (CR-1 to CR-17), a proposed test not
taken.

**Measured.** VER-24 classifies the switches both ways, but no test walks every `CaseDocument` leaf
to show it either changes the assembled forms or is listed as provenance-only, so an inert key can
enter the schema unnoticed.

**Resolved.** WP42 D3–D8: VER-71 classifies 105 case leaves across 7 kinds in `src/nanopnp/validation/case_leaves.py`; `ModelDeclaration.unread` declares and refuses unread leaves; residual probes verify active leaves.

### REV-13 — Example 06's key test cannot see a stage-7 key change

*Area:* verification. *Severity:* medium. *Found:* PR #72 (WP34), review findings not acted on.

**Measured.** The check that every key of example 06 is unchanged does not cover stage 7, so a
change to the charge stage's key would pass it.

**Resolved.** WP42 D11: stage-7 keys of Example 06 pinned in `test_validation_identity.py` before and after `case_identity`.

### REV-14 — A radial grid's .npz does not round-trip its spacing exactly

*Area:* numerics. *Severity:* low. *Found:* PR #57 (WP28).

**Measured.** The `.npz` carries the axes, not the origin and spacing, and reads back with the z
spacing off in its last bits. `charge/stage.py` works around it by depositing the grid as re-read;
the root fix belongs in `density/grid.py`.

**Resolved.** WP46 D1: the `.npz` carries `origin_nm` and `spacing_nm` and reads them back bit for bit, and `charge/stage.py` deposits the grid it summed.

### REV-15 — Example 05 quotes #SBATCH directives as shell words

*Area:* interface. *Severity:* low. *Found:* PR #34 (WP16), a confirmed review finding not fixed.

**Measured.** `examples/05-clya-reference/render_slurm.py` passes the job name and working directory
through `shlex.quote` into `#SBATCH` lines. sbatch does not read a directive as a shell would, so a
value that needs quoting does not reach it as written; the review of PR #34 confirmed the finding
and left it unfixed.

**Resolved.** WP46 D6: `render_slurm.py` writes the #SBATCH values raw and refuses one holding whitespace, a quote, `#`, `%` or a control character, naming the key.

### REV-16 — A salt sweep regenerates an identical mesh at each concentration

*Area:* performance. *Severity:* low. *Found:* PR #42 (WP21), left for the author.

**Measured.** The stage-6 recipe key carries λ_D, so below 1.474 M, where the wall size it drives no
longer changes, each concentration of a sweep re-meshes an identical mesh. Warm starts are
unaffected.

**Resolved.** WP46 D2: `WallSize.key()` leaves λ_D out of the stage-6 key, so a salt sweep below the 0.05 nm ceiling shares one mesh; the manifest's `sizing` block keeps λ_D. Netgen's key golden is re-recorded.

### REV-17 — A warm start is gated on free prose in the stabilisation provenance

*Area:* numerics. *Severity:* low. *Found:* PR #28 (WP12), a VER-37 semantics question for the
author.

**Measured.** `solve/state.py` compares the whole `model.stabilisation_provenance` subtree,
including its `note` prose (`physics/stabilisation.py`), so a reworded note refuses a valid warm
start. It fails closed.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-18 — Concurrent sweep members may write the same store key

*Area:* interface. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** Job-array members generate and `put` the same stage 1–6 keys at the same time. Whether
that is safe depends on how atomic `Store.put` is, which has not been measured.

**Resolved.** WP46 D3: `Store.put` stages payloads and record in a sibling directory and renames it onto the entry; the first complete entry stays and both writers return `get()` of it.

### REV-19 — A zero-frame trajectory raises a bare IndexError

*Area:* interface. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `structure/read.py` raises a bare `IndexError` on a trajectory with no frames, rather
than a refusal naming the file (QR-12). Two Cα with the same `(resid, icode)` in one chain also
overwrite each other in `per_chain`.

**Resolved.** WP46 D5: a trajectory holding no frame is refused naming the file, and a second Cα at one chain, residue and insertion code is refused naming both.

### REV-20 — The desktop shell has no multiprocessing.freeze_support

*Area:* process. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** No `multiprocessing.freeze_support()` exists in `src/`. It is needed when the frozen
shell spawns children on Windows.

**Resolves it.** Phase 5, which makes the shell the bundle's executable (QR-10).

**Ruled** `wontfix` (§8.2.18 T1): no frozen executable remains once the bundle leaves (§8.2.17 S12).

### REV-21 — numerics/linear.py imports scipy inside its functions

*Area:* process. *Severity:* low. *Found:* PR #4 (WP3), a convention decision for the author.

**Measured.** `numerics/linear.py` imports `scipy.sparse` and `scipy.sparse.linalg` inside
functions, which `CLAUDE.md`'s import rule did not exempt. `import scipy.sparse` costs about 260 ms.

**Declined.** `CLAUDE.md` exempts `scipy` beside `numpy`, for the same reason.

### REV-22 — write_dx formats with %

*Area:* process. *Severity:* low. *Found:* PR #58 (WP29), the author's call.

**Measured.** `validation/apbs.py`'s `write_dx` formats the map body with one `%` over the whole
array, against `CLAUDE.md`'s f-string rule, because one pass is what keeps the write fast.

**Declined.** `CLAUDE.md` allows one `%` over a whole numeric array, naming this case.

### REV-23 — The corrections test bounds both ions by one range

*Area:* verification. *Severity:* low. *Found:* PR #2 (WP1).

**Measured.** `tests/tier1/test_corrections.py` asserts the monotonic rise of the ratio with ranges
that fit both ions, not per-ion bounds.

**Resolved.** WP42 D12: per-ion Einstein ratios (Na⁺ and Cl⁻) pinned within 1e-3 in `test_corrections.py`.

### REV-24 — Sampler construction may still be duplicated

*Area:* process. *Severity:* low. *Found:* PR #13 (Phase 0 consolidation); not re-measured.

**Measured.** The per-point sampler rebuild was fixed by `FieldSampler.shared`; whether the
SI-expression building is still duplicated was not checked.

**Resolved.** WP46 item 10: measured on the cylindrical-pore case (`tests/conftest.py` `CYLINDRICAL_PORE_CASE`, epnp-ns, Na+/Cl-, 0.1 M, stabilisation as the case sets it): a run of ten solves of the continuation ladder builds the SI concentration expressions ten times, once per solve and once for both gates, against 36 Newton iterates and 46 positivity checks. The count per field per iterate is zero, below one, so nothing is removed; `tests/tier1/test_gate_builds.py` holds it.

### REV-25 — A post stage run without a solve writes scratch to the default store

*Area:* interface. *Severity:* low. *Found:* PR #24 (WP10).

**Measured.** A library caller invoking `QoIStage` or `ReportStage` with no upstream `solve` sends
its scratch to the process-default store root.

**Resolved.** WP46 D4: `io/workspace.py` `scratch_directory` refuses a stage constructed without `workspace`, naming the argument; the stage writes into the workspace it was given.

### REV-26 — stabilisation_parameters returns an empty mapping off the coupled model

*Area:* interface. *Severity:* low. *Found:* PR #28 (WP12).

**Measured.** `LadderResult.stabilisation_parameters` returns `{}` for a model that is not a
`CoupledModel`, rather than refusing or naming the mode.

**Resolves it.** WP41, the accuracy fixes (§8.2.9 I1, I2).

### REV-27 — The inf-sup check ran at resolve, not at validation

*Area:* interface. *Severity:* low. *Found:* PR #28 (WP12).

**Measured.** The inf-sup check runs in `io.case.resolve()`, so `nanopnp validate` does not report
it.

**Resolved.** WP38 D8: `pipeline.checks.check_document` makes the registry checks and the inf-sup
check, and `load_case`, `resolve` and the desktop shell's commit all run it, with a run's refusal
text. The author ruled that "`nanopnp validate`" means a new subcommand, `nanopnp validate case
<file>`, beside the Tier-3 comparison harness: it loads and resolves the case, makes every check a
run makes before it meshes, and prints the model, the stabilisation and the stages a run would
walk (open question 1 of the [WP38 plan](../plans/phase-4/wp38-io-split.md)).

### REV-28 — The viewer renders every finished run eagerly

*Area:* performance. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** Each finished run is rendered whether or not it is viewed.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the workbench's Analysis package, which draws a field when a tile opens it.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.20, the Analysis suite.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.20, the Analysis suite.

### REV-29 — The cylindrical-pore fixture is copied into four test modules

*Area:* verification. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** Four Tier-1 modules each define the same cylindrical-pore fixture.

**Resolved.** WP42 D13: consolidated `cylindrical_pore_case` fixture in `tests/conftest.py` across Tier-1 test modules.

### REV-30 — The viewer's scene is written twice

*Area:* performance. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** The scene file is written twice per render.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the workbench's Analysis package, which writes each scene once and serves it.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.20, the Analysis suite.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.20, the Analysis suite.

### REV-31 — The bundle's size is not recorded

*Area:* documentation. *Severity:* low. *Found:* PR #37 (Phase 1 close).

**Measured.** No document records the Windows bundle's size.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** `wontfix` (§8.2.18 T1): the browser shell ships no bundle; the install's size is the package's.

### REV-32 — Old store entries are neither migrated nor removed

*Area:* interface. *Severity:* low. *Found:* PR #38 (WP17).

**Measured.** Entries written under an earlier schema stay in the store, unread and unremoved.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the project-folder package: the library lists entries of an older schema and removes them on request.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.08, the frame and the project folder, in its library step.

**Fixed** in WP5.08: `Store.stale` lists each entry of an older version of a schema a stage writes now, never a newer one, and `Store.remove` deletes them; `nanopnp store prune [--remove]` prints the count and size. The workbench offers it in a later package.

### REV-33 — writable_formats assumes the extra's floor

*Area:* interface. *Severity:* low. *Found:* PR #38 (WP17), a review finding not applied.

**Measured.** `density/grid.py`'s `writable_formats()` reports `mrc` writable wherever
GridDataFormats imports, which holds only at the extra's floor, 1.2, and above.

**Declined.** The extra's floor is GridDataFormats 1.2, at which `mrc` is writable, so the report holds wherever the extra is installed (§8.2.9 I3).

### REV-34 — Two reference tests duplicate the frozen case

*Area:* verification. *Severity:* low. *Found:* PR #46 (WP22).

**Measured.** `FROZEN_CASE`, `as_yaml` and the D10 figures are copied between the Tier-2 and Tier-3
VAL-05 files.

**Resolved.** WP42 D13: `VAL05_FROZEN_CASE` template, `as_yaml`, `reference_triangles` and `d10_figures` fixtures in `tests/conftest.py`.

### REV-35 — _second_crossings loops in Python

*Area:* performance. *Severity:* low. *Found:* PR #46 (WP22).

**Measured.** The second-crossing search iterates in Python where it could be vectorised.

**Post-1.0.** A saving no gate needs (§8.2.9 I3).

### REV-36 — The gmsh session stops a caller's logger

*Area:* interface. *Severity:* low. *Found:* PR #47 (WP23), a review finding not fixed.

**Measured.** `_session` calls `gmsh.logger.stop()` in a session it borrowed. No caller in the
repository holds a logger.

**Resolved.** WP39 D11: a borrowed session leaves the caller's logger untouched; `start()` and `stop()` are only called for sessions owned by nanopnp.

### REV-37 — A broken gmsh wheel is not a refusal

*Area:* interface. *Severity:* low. *Found:* PR #47 (WP23), a review finding not fixed.

**Measured.** A gmsh wheel that imports but fails to initialise surfaces as an exception, not as
`MissingExtraError` naming the extra.

**Resolved.** WP39 D11: `gmsh.initialize()` failure raises `GmshInitialisationError`, which `meshers.py` translates to `MissingExtraError` naming `gmsh` and the underlying error.

### REV-38 — gmsh.model.remove() can mask the error it follows

*Area:* interface. *Severity:* low. *Found:* PR #47 (WP23), a review finding not fixed.

**Measured.** The cleanup's `gmsh.model.remove()` can raise over the error that triggered it.

**Resolved.** WP39 D11: `_session` runs each cleanup step in sequence; if an exception is active, cleanup failures are logged at WARNING and added via `add_note`, never masking the original exception.

### REV-39 — A case supplying inputs.profile gets no contour editor

*Area:* interface. *Severity:* low. *Found:* PR #48 (WP24).

**Measured.** The Geometry tab offers its contour editor only for a profile the pipeline extracts.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the workbench's Continuum package: the Contour tool opens on any profile, extracted or supplied.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.17, the Continuum suite.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.17, the Continuum suite.

### REV-40 — DensityMap.read accepts a file written in nm

*Area:* interface. *Severity:* low. *Found:* PR #50 (WP25).

**Measured.** A density map written before the ångström convention of §8.2.2 B10 is read without
refusal, ten times off.

**Resolved.** WP46 D6: `DensityMap.read` refuses an interchange file whose spacing lies outside FR-04's 0.025-0.05 nm, saying a map is written in ångströms; `GRID_SPACING_RANGE_NM` lives in `density/map.py` and `pipeline/case.py` imports it.

### REV-41 — No prepare command, upto on reproduce, or region export

*Area:* interface. *Severity:* low. *Found:* PR #50 (WP25).

**Measured.** `nanopnp prepare`, `reproduce --upto` and a region export were left out of WP25 with
no later owner.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T3): `prepare` comes with structure preparation (FR-37); `upto` on reproduce with the workbench's Study package; the region export with FR-28, v0.7.

**Ruled in part** (§8.2.22 X1): the region's interchange document comes forward to WP57, as the geometry file of `nanopnp geometry cylinder`; `prepare` and `upto` stay as T3 placed them.

**Placed** (§8.2.31 AG1, 3 November 2026): `prepare` in WP5.16, which surfaces structure preparation; `upto` on reproduce in WP5.19, the Study suite.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): `prepare` in WP5.16, the Molecular suite; `upto` on reproduce in WP5.19, the Study suite.

### REV-42 — pnp carries inert flow keys

*Area:* interface. *Severity:* low. *Found:* PR #53 (WP26).

**Measured.** The `pnp` model accepts `variable_density` and `inertia` as given, though without flow
they do nothing.

**Resolved.** WP42 D5: `pnp` model restricts `variable_density` and `inertia` switch sets to `(False,)`; schema moves to `nanopnp/case/v0.6`.

### REV-43 — chain_characters duplicates the export's mapping

*Area:* process. *Severity:* low. *Found:* PR #55 (WP27).

**Measured.** `chain_characters` repeats the mapping inside `AlignedEnsemble.export`.

**Resolved.** WP46 D6: `chain_characters` lives in `structure/ensemble.py` and `AlignedEnsemble.export` uses it; too many long-keyed chains raise `EnsembleFormatError` (exit 4) rather than `PQRError`.

### REV-44 — The Stern-layer test re-solves the drawn slab

*Area:* verification. *Severity:* low. *Found:* PR #60 (WP30).

**Measured.** `test_stern_layer.py`'s generated-slab clause re-solves the slab it already drew.

**Resolved.** WP42 D13: `drawn_slab` module-scoped fixture in `tests/tier2/test_stern_layer.py`.

### REV-45 — The derived χ field has no export

*Area:* interface. *Severity:* low. *Found:* PR #60 (WP30).

**Measured.** WP31 shows χ in the GUI; no command exports it.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T3): with FR-28, v0.7.

### REV-46 — Example 07 is not run at default sizes or on the ensemble

*Area:* verification. *Severity:* low. *Found:* PR #65 (WP32).

**Measured.** Example 07 runs at reduced mesh sizes on one frame, not at the default sizes or on the
50-frame ensemble.

**Deferred.** Phase 6, with the ensemble legs (§8.2.5 E1; §8.2.9 I3).

### REV-47 — The test-duration targets are missed

*Area:* process. *Severity:* low. *Found:* PR #67 (WP33).

**Measured.** The 180 s gated target and the 90 s per-file bound were missed, recorded only in the
PR and the plan's Outcomes.

**Resolves it.** Phase 4's close package, which reports the gate's durations on its own tree and re-argues or retires WP33's targets (§8.2.9 I3).

**Fixed in WP60** (2 November 2026): WP33's targets, 180 s gated and 90 s per file, are retired. §7.6's NOTE on
the loop's timings replaced them when the loop was simplified (WP44), and neither target is in the specification.
The close reports the durations on its own tree instead, in the Phase 4 plan's end-of-phase report: the commit hook
95 to 117 s on a commit that changes Python or a findings log (1 s for prose alone), the push gate 243 s (`gate.sh run`, four
CPUs, `72b0689`), and the pull request's CI critical path 4 min 46 s.

### REV-48 — The 2WCD walk test copies its constants

*Area:* verification. *Severity:* low. *Found:* PR #67 (WP33), review finding 13.

**Measured.** `test_exclusion_2wcd_walk.py` copies constants from `test_exclusion_2wcd.py`, which
can drift apart.

**Resolved.** WP42 D13: consolidated `exclusion_2wcd` fixture in `tests/conftest.py`.

### REV-49 — AXISYMMETRIC is replaced repeatedly

*Area:* process. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** The same `replace(AXISYMMETRIC, …)` is repeated at several call sites.

**Resolved.** WP46 D6: `Measures.at_order(order)` replaces the six `replace(AXISYMMETRIC, element_order=…)` call sites.

### REV-50 — _inner_wall_nm re-implements innermost_crossings

*Area:* process. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** `_inner_wall_nm` repeats the logic of `innermost_crossings`.

**Resolved.** WP46 item 9: `tests/tier2/test_axis_weight_order.py` samples the wall through `innermost_crossings`, the top plane taken 1e-9 nm inside the half-open rule; the old loop and the helper agree to 4.4e-16 nm at the 2,840 other samples.

### REV-51 — A redundant reopen and resolve in WP34's walk

*Area:* performance. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** A case is reopened and resolved where the resolved case is already at hand.

**Resolved.** WP46 D6: `ReopenedRun` carries its `ResolvedCase`, and the CLI's identity reads it instead of resolving the case again.

### REV-52 — deviations and SolveReporting are off the stage protocol

*Area:* interface. *Severity:* low. *Found:* PR #79 (WP36).

**Measured.** The protocol declares `name`, `describe`, `key` and `run`; `deviations` and
`SolveReporting` stay conventions of some stages.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the first shell package, library first: `deviations` and `SolveReporting` join the stage protocol as optional members.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.08, the frame, library step first.

**Fixed** in WP5.08: `ContributesDeviations` joins `SolveReporting` and `Forecastable` as a runtime-checkable optional member of `core.stages`, the walk tests each by `isinstance`, and VER-64 checks each member's signature.

### REV-53 — Some walk rules stay as case logic

*Area:* interface. *Severity:* low. *Found:* PR #79 (WP36).

**Measured.** Not every walk rule is a declared stage fact; some remain conditions in the case.

**Declined.** WP36 ruled the drop rules of `selected_stages` case logic (§8.2.9 I3). REV-63, the cost of the walk, is WP38's.

### REV-54 — The MOD-12 check compared names, not modules

*Area:* verification. *Severity:* low. *Found:* PR #79 (WP36).

**Measured.** The check of `PUBLIC`'s type-checker mirror compares names only, not the module each
mirrored import comes from.

**Resolved.** WP38 D12: `validation.modularity.Surface` reads the module each mirrored import
comes from, and the check refuses a name mirrored from a module other than `PUBLIC`'s, naming the
name and both modules (VER-45).

### REV-55 — Per-stage mkdtemp fallbacks

*Area:* interface. *Severity:* low. *Found:* PR #43 (CR-1 to CR-17), left as they were.

**Measured.** Some stages fall back to `mkdtemp` for scratch rather than the store's workspace.

**Resolved.** WP46 D4: the ten per-stage fallbacks and their `WORKSPACE_DIRNAME` copies are removed; `pipeline/run.py`'s store scratch, `cli/export.py`'s staging and the shell's probe stay.

### REV-56 — The geometry editor's simplicity check runs on the Qt thread

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `gui/widgets/geometry.py`'s O(n²) `_check_simple` re-runs on every `_show_row`, 0.63 s
at 600 vertices. *Seed from refusal* and a rebuild drop unsaved edits without confirmation.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** `wontfix` for the Qt code (§8.2.18 T1). The workbench's Contour tool checks its edits off the interface's thread and asks before discarding one.

### REV-57 — frame_times decodes every frame

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `structure/read.py`'s `frame_times` decodes every frame only to read its time, and no
PBC or RMSD gate catches a chain split across the periodic box.

**Resolved.** WP46 D5: a DCD's frame times are computed from its header without decoding a frame; XTC, TRR and NetCDF decode, their times living in frame headers. A chain split across the periodic box is refused naming chain, pair, frame and distance; the deposited 2WCD's largest consecutive-Cα distance is 0.3856 nm (`knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md#11-the-authors-md-archive-measured`).

### REV-58 — The azimuthal reduction projects cells it then drops

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `symmetry/reduce.py` multiplies and projects all cells for every harmonic though only
bins with `K_j ≥ k` are kept, up to about 2× work. Correct.

**Post-1.0.** A saving no gate needs (§8.2.9 I3).

### REV-59 — attribute_to_construction raises the wrong error on a lax comparison

*Area:* interface. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `validation/geometry.py`'s `attribute_to_construction`, given a `strict=False`
comparison, raises `MissingPlaneError` rather than saying the comparisons do not match. In-repo
callers pass strict comparisons.

**Resolved.** WP46 D6: `attribute_to_construction` raises `GeometryComparisonError` for a comparison leaving a plane outside the tip band uncrossed, before binning.

### REV-60 — UMFPACK repeats its symbolic analysis every Newton step

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_002 (PR #44), *Leads not settled*.

**Measured.** `numerics/linear.py` redoes the symbolic factorisation on every Newton iteration; the
saving from reusing it is unmeasured.

**Deferred.** Phase 6, measured with the envelope's throughput (§8.2.9 I3).

### REV-61 — No B-spline fit or HOLE cross-check of the contour

*Area:* interface. *Severity:* low. *Found:* PR #41 (WP20); verified open at `5559c7e`.

**Measured.** The optional B-spline fit of the extracted contour and the HOLE cross-check (B5) were
left out of WP20, and nothing in `src/` or the specification owns them.

**Deferred.** Phase 6, the HOLE cross-check (§8.2.2 B5) with VAL-05; the B-spline fit with it (§8.2.9 I3).

### REV-62 — A mesh named by store key is refused

*Area:* interface. *Severity:* low. *Found:* PR #57 (WP28); verified open at `5559c7e`.

**Measured.** `inputs.mesh: {artefact: …}` is refused (`mesh/ingest.py`), so a mesh can be supplied
only as a file.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T2): owned by the named-model capability (REV-136), which references a continuum model's mesh.

**Fixed** (WP5.05, `e56d8a6`): `inputs.mesh.artefact` takes the 64-character store hash of a stage-6 mesh artefact.
The mesh stage takes the store, and its key is the stored artefact unchanged, so a stored mesh keeps its hash; a
hash the store does not hold is refused naming the hash and the store's root, and `format` or `groups` beside it
are refused. `artefact:` on `inputs.charge` and `inputs.eps_r` stays refused (§5.3.1 NOTE on `inputs:`). Tier 1:
`test_a_mesh_named_by_store_key_is_the_stored_artefact`.

### REV-63 — The protonation stage walked through meshing

*Area:* performance. *Severity:* low. *Found:* PR #55 (WP27); verified open at `5559c7e`.

**Measured.** Protonation declares `case` and `structure` as its inputs, yet
`selected_stages(resolved, 'protonation')` on example 07 walks density, symmetry, contour, region
and mesh first, because the walk runs in registration order (WP36).

**Resolved.** WP38 D11: a walk to a stage runs its transitive input closure, so example 07's walk
to `protonation` is `case`, `structure`, `protonation`. Each stage is handed only the inputs it
declares, and `validation.modularity.undeclared_reads` finds a read the declaration misses (VER-64).

### REV-64 — A sweep's plan-time NUM-34 gate skips generated meshes

*Area:* verification. *Severity:* low. *Found:* PR #42 (WP21); verified open at `5559c7e`.

**Measured.** `sweep/plan.py` skips a generated mesh, which does not exist until the member's stage
6, so a NUM-34 violation on one surfaces at the member's solve rather than in seconds at plan time.

**Deferred.** Phase 6, with the envelope sweeps (§8.2.9 I3). The violation is loud, at the member's solve.

### REV-65 — The Windows bundle exposes no mesh command

*Area:* interface. *Severity:* low. *Found:* PR #34 (WP16), open question 2; verified open at
`5559c7e`.

**Measured.** The bundle carries no `nanopnp mesh`; WP16 left it a GUI item unless the author ruled
otherwise.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** `wontfix` (§8.2.18 T1): no bundle; the command line installs with the package everywhere.

### REV-66 — A model without flow is refused on its element pair before its flow switch

*Area:* interface. *Severity:* low. *Found:* PR #82 (WP38), the `/wp-ship` review; reproduced at
`0b406b2`.

**Measured.** WP38 D8 moves the inf-sup check from `resolve` to `pipeline.checks.check_document`,
which runs at load, ahead of `require_runnable`'s switch checks. A case with `physics.model: pb`,
`physics.flow` left at its default `true`, `numerics.elements.u: P1` and
`numerics.stabilisation: none` is now refused naming the inf-sup velocity–pressure pair of a model
that solves no velocity or pressure. Before WP38 it was refused naming `pb honours physics.flow:
false only (PHY-21)`, the real mistake, which now surfaces only once the element pair is changed.
The document is refused either way; only the first diagnostic misleads (QR-12).

**Resolved.** WP42 D8: `check_document` gates the inf-sup check on `numerics.elements.u` not in the model's `unread` set and `physics.flow` true.

### REV-67 — Public registration functions for backend registries (MOD-11)

*Area:* interface. *Severity:* low. *Found:* WP39 (PR #84); verified open at `WP39`.

**Measured.** WP39 added six internal registration functions across `mesh/meshers.py` and
`numerics/linear.py` (`register_mesher`, `registered_meshers`, `create_mesher`, `register_solver`,
`registered_solvers`, `create_solver`), matching `physics/stabilisation.py`. None are exposed in
`PUBLIC` (D12).

**Deferred.** Phase 5, evaluated with `MOD-11` and the extension point public surface ruling (§8.2.8 H2).

**Ruled** (§8.2.18 T3): with the composer phase and MOD-11.

### REV-68 — The spec still promises a refusal that D8 removed

*Area:* verification. *Severity:* low. *Found:* PR #86 (WP40), the `/wp-ship` review at `bccf29f`.

**Measured.** SPECIFICATION.md's §5.3.1 NOTE on `inputs:` and the VER-47 row say a key no stage
reads yet "is refused as unsupported naming the stage that would consume it". D8 removed
`_UNCONSUMED_INPUTS` and `_UNREAD_CHARGE_KEYS` and the VER-47 assertion, so no code or test
enforces the sentence. A key added to `Inputs` later is accepted and hashed into the manifest
although nothing reads it (FR-25).

**Fixed.** The author ruled both (6 October 2026): the §5.3.1 NOTE and the VER-47 row now say every
`inputs:` key is read by the stage that consumes it, and `test_ver47_every_inputs_key_is_hashed_and_read_by_a_stage`
fails on a key the resolved case does not carry, `input_files` does not hash or no stage reads.

### REV-69 — VER-67 defers its refusal texts to a plan

*Area:* verification. *Severity:* low. *Found:* PR #86 (WP40), the `/wp-ship` review at `bccf29f`.

**Measured.** The VER-67 row points to "WP40 Design §1" for the exact refusal texts. `docs/plans/`
is planning, not requirements, and the texts are repeated in code, tests, the plan and the
changelog, so archiving the plan leaves the row undefined.

**Fixed.** The author ruled the rule goes in the row: VER-67 states that a refusal names its
requirement and the release that schedules it or that none does, and no longer cites the plan.

### REV-70 — WP40 D5 and D8 go beyond MOD-14's letter

*Area:* interface. *Severity:* low. *Found:* PR #86 (WP40), the `/wp-ship` review at `bccf29f`.

**Measured.** D5 refuses `artefact:` on `inputs.mesh`, `charge` and `eps_r` at resolution, so
`nanopnp validate case` exits 3 where it exited 0. D8 removes `_UNREAD_CHARGE_KEYS` too. A check
that a string pairing a requirement with a release matches §3's Release column is not built.

**Fixed.** The author ruled D5 and D8 stand, and that the Release-column check is built in this
package: VER-67 gains `requirement_releases` and `release_pairing_mismatches`.

### REV-71 — Stage 10's cache key does not move when the solver's algorithm does

*Area:* verification. *Severity:* medium. *Found:* PR #89 (WP41), the `/wp-ship` review at `d704e84`.

**Measured.** Stage 10's key is the resolved case's solve provenance, the mesh digest and the
materials and field artefacts' hashes (`SolveStage.key`). WP41 changes NUM-16's stopping test and a
supplied field's source rule, and both move converged numbers (D3, D5), but neither enters the
key: the `newton` record lists no `field_floor_ratio` and no criterion, `ResolvedFields.parameters()`
carries no rule order, and `SOLVE_HASHES` does not move. A store written before WP41 therefore
serves its old solution as a hit after the upgrade, and the manifest cannot tell it from a WP41
one (FR-25, §5.3.2). The property is not WP41's alone: any change that moves a number without
moving a case key has it.

**Fixed.** The author ruled stage 10's key gains an algorithm revision (WP42, "Add to key + revision const"). `SOLVE_ALGORITHM_REVISION` (`io/resolved.py`) enters the solve provenance and the manifest and is bumped by any change that moves a converged number; the `newton` record gains `field_floor_ratio`; a supplied charge field's artefact parameters gain `quadrature_order`. The five `SOLVE_HASHES` are re-pinned, and `test_model_interface.py` and `test_manifest.py` hold the three keys. Stored solves from before this commit miss, which is the point. SPECIFICATION §5.3.2 states the route.

### REV-72 — A supplied field's rule order travels beside its source as a second argument

*Area:* coupling. *Severity:* low. *Found:* PR #89 (WP41), the `/wp-ship` review at `d704e84`.

**Measured.** WP41 D2 threads `fixed_charge_rule_order` beside `fixed_charge` through
`single_rung`, `default_ladder`, `CoupledModel` and `PoissonModel`. PHY-19's one-rule NOTE then
holds only where every caller passes both: a caller passing `fixed_charge=field.assemble(scales)`
alone silently returns to NGSolve's order-3 estimate. `test_charge_quadrature.py` checks the call
sites in `physics/models.py`, not their callers.

**Fixed.** The author left the choice to the maintainers (WP42), and the charge object now carries its rule. `FixedCharge` (`numerics/measures.py`) is a density and a required `rule_order` (`None` being NGSolve's estimate, written out at the call site); `ChargeField` and `DepositedCharge` return it from `fixed_charge_C_m3()` and `assemble(scales)`, `default_ladder(fixed_charge_field=)` ramps it with `scaled()`, and the models' `fixed_charge_rule_order` argument is gone. A bare density is refused with a `TypeError` by both models that take one, since `Expression` is `Any` and the type checker cannot. The tier-2 benchmarks that pass an analytic or deposited density say `None` themselves. The first ruled fix (raise on a missing order) would have refused deposited charges and those benchmarks, whose estimate is deliberate.

### REV-73 — Cross-leaf inertness is not checked

*Area:* physics. *Severity:* low. *Found:* PR #85 (WP42).

**Measured.** VER-71 probes single leaves from each model's base, but does not probe leaves rendered inert by another leaf's value (such as `variable_density` beside a `none` density correction, `dielectric_gradient_forces` beside no permittivity concentration fit, or wall distance with every wall part off).

**Fixed.** The author ruled both are refused (WP42, "Refuse both in checks.py"). `_check_switch_partners` (`pipeline/checks.py`) refuses `physics.variable_density: false` where the density correction applies no fit that varies the density, and `physics.dielectric_gradient_forces: true` where the permittivity correction applies no concentration fit, naming the leaf and its partner; SPECIFICATION PHY-22's NOTE states both. The wall-distance pair was already refused by PHY-22 (every wall part off) and is tested with the other two in `test_case_leaves.py`. The "Phase 5 (§8.2.9 I3)" cite in the earlier text was wrong (that row covers REV-23 to REV-65).

### REV-74 — An untested raise in the force extension carries a coverage pragma

*Area:* verification. *Severity:* low. *Found:* PR #91 (WP42 review pass).

**Measured.** forces.py `_mean_square` (line 350) refuses a missing boundary under `# pragma: no cover - missing boundary in mesh`; no test reaches it, so the gate that names the boundary is outside the 100 % diff-cover claim (VER-72 f).

**Fixed.** The author ruled the test is written (WP42): `test_num28_check_extension_names_a_boundary_the_mesh_does_not_have` reaches the raise through `check_extension`, and the pragma is gone.

### REV-75 — The two defaults modules duplicate the specs' defaults

*Area:* coupling. *Severity:* low. *Found:* PR #91 (WP42 review pass).

**Measured.** `mesh/defaults.py` and `numerics/defaults.py` hold 18 constants, 16 read only by `test_defaults.py`: a third copy beside the pydantic specs and `io/defaults._VALIDATED_DEFAULTS`, kept in step by a parity test alone.

**Fixed.** The author ruled the test-only constants go (WP42, "Delete test-only constants"): `mesh/defaults.py` keeps the five the CLI and `CylindricalPoreGeometry` read and `numerics/defaults.py` the two `NewtonSettings` reads; `test_defaults.py` now holds the case schema's defaults equal to `_VALIDATED_DEFAULTS` directly. The plan's D16 row and Outcome no longer state the drifted values.

### REV-76 — `ModelDeclaration.unread` paths are not validated against the schema

*Area:* verification. *Severity:* medium. *Found:* PR #91 (WP42 review pass).

**Measured.** Neither `_check_unread` nor `register_model` checks that each path in `unread` exists, or has a default; a typo in a model's set makes its refusal never fire, with no error. `_check_unread` also walks all 105 `case_fields` per call rather than the model's own set (VER-71).

**Fixed.** The author ruled the subset test (WP42): `test_ver71_every_unread_path_is_a_schema_leaf` holds every model's `unread` inside the walked leaves, and `test_ver71_the_shipped_models_are_the_ones_the_leaf_tests_cover` holds the registry to `MODELS`. No registration-time check, because `physics` may not import `io` (§5.4.1). A leaf with no schema default (poisson's `electrolyte.concentration_M`) is a leaf and is not refused, as VER-71 already allows. `_check_unread` still walks all 105 leaves per call.

### REV-77 — Pinning every artefact schema at v0.5 removes the cache-bust a payload change needs

*Area:* process. *Severity:* medium. *Found:* PR #91 (WP42 review pass).

**Measured.** §5.3.2 relied on the schema version to bust a cache when a payload contract changed. With every identifier at `v0.5` until v1.0, a later payload change is a cache hit on an old store the loader cannot open; the docstrings in `io/artefact.py` still explain `v2` that way (D9, D14b).

**Fixed.** The author ruled the docstrings and the specification follow G6 (WP42, "Docs + spec to match G6"): the three `io/artefact.py` docstrings no longer promise a version bump and SPECIFICATION §5.3.2 names the route that replaces it (stage 10's `algorithm_revision`, REV-71). A payload-version counter for the other stages is not built; a change to one of their payloads is the author's ruling on a store invalidation until then.

### REV-78 — The threads flag re-lists the thread variables and writes the environment for good

*Area:* interface. *Severity:* low. *Found:* PR #91 (WP42 review pass).

**Measured.** `cli/__init__.py` names the three variables that `sweep/run.py` defines as `THREAD_VARIABLES`, sets them permanently, works only before NumPy or NGSolve is imported, and `nanopnp -vv run c.yaml -v` collapses verbosity to 1.

**Fixed.** The author ruled both fixes (WP42): the `--threads` branch imports `THREAD_VARIABLES` from `sweep/run.py` inside the branch (a top-level import would load the sweep on every invocation), and the subcommand's `-v` has its own destination, summed with the top-level count, so `-vv env -v` is three levels (`test_cr4_verbosity_given_before_and_after_the_subcommand_adds_up`). The item's remedy was already in place (the subparser defaulted to SUPPRESS); the collapse was the shared `dest`. The environment is still written for the life of the process, which is the CLI's own.

### REV-79 — The exclusion shell raises a bare ValueError for a NaN ring coordinate

*Area:* numerics. *Severity:* low. *Found:* PR #91 (WP42 review pass).

**Measured.** `geometry/region.py` rewrote its gate to `if not lowest >= h_c_nm`; with NaN `lowest`, `near` is empty and `near[:, 1].min()` raises `zero-size array to reduction operation minimum`, not a `RegionGateError` naming the gate, quantity and location (QR-12).

**Fixed.** Fixed by a finiteness check at the top of `exclusion_shell` (WP42) rather than a guard on the empty ring: the inner path is not reachable from a profile, because a NaN vertex is stopped earlier, by GEOS (`Points of LinearRing do not form a closed linestring`) or by the edge-distance gate. The check raises `RegionGateError` naming the vertex, for all of them (`test_ver59_a_non_finite_profile_coordinate_is_refused_naming_its_vertex`).

### REV-80 — A source change selects every process-starting test file, so the commit hook misses its 60 s budget

*Area:* performance. *Severity:* medium. *Found:* [WP43](../plans/phase-4/wp43-development-loop.md) item 2.

**Measured.** On 4 cores, Python 3.14.6, with a map recorded on the commit's parent, a planted body
change through the hook took 115 s in `rectification_ratio` (866 tests in 40 files; 8 tests call it)
and 155 s in `total_current` (1,012 tests), against §8.2.10 J7's 60 s and WP43 D5's predicted 30 to
50 s. D4 selects every test that starts a process on any change under the source root, and selection
is by whole file: 151 tests in 30 files, which alone take 64.7 s of wall time. 25 of the 30 files
start a Python child that imports the package; the rest start `git`, `bash` or `apbs`. The cost is
the whole-file widening of a few process-starting tests into slow files (`test_backend_registries.py`,
`test_val06_ring.py`'s setup, `test_sweep_plan.py`, `test_examples_plan.py`).

The same rule sets the push gate's follow-up floor: with `--extended`, the process starters include
the example walks, example 07 (477 s) among them, so a one-line docstring change in `post/qoi.py`
followed up in 685 s (955 tests in 50 files) against 966 s for the full run (WP43 item 3, both under
a parallel agent's load).

At the close (WP43 item 10, tree `4d9c306`, quiet machine, map of the same tree), a one-line
body change took 136 s in `post/qoi.py` (1,016 tests), 207 s in `physics/poisson.py` (1,260 tests)
and 234 s in `io/case.py`, which fell back (REV-81). All three miss the budget beyond its 90 s
margin.

**Open.** Either route keeps the selection sound: trace the Python children (the recorder carried
into the child through its environment), so a child is a set of functions rather than "anything";
or move each process-starting test that does not need its file's module fixtures into a file of its
own. A third, re-setting the budget, is the author's (J7).

**Fixed.** By removal ([WP44](../plans/phase-4/wp44-simplify-the-loop.md), §8.2.11 L2): the commit hook runs all of Tier 1, so no
process-starting test is selected or widened and no commit falls back. The recorder, selector and map are deleted.

### REV-81 — Most past commits would fall back to the development selection

*Area:* performance. *Severity:* low. *Found:* [WP43](../plans/phase-4/wp43-development-loop.md) item 2.

**Measured.** Of the 15 latest non-merge commits touching `src/` whose parent this clone holds
(`a93f5e3` to `d630f85`), D4's rules fall back on 12: another module-level change in 10, a changed
data, case or fixture file in 5, an added module in 2, an import change in 4, and never an import
change alone. These commits are whole review rounds, larger than a commit made while implementing.

At WP43's close a body change in `io/case.py` fell back on two counts: the file is read outside a
test, and `SuppliedArtefact._exactly_one_source` runs at import or outside a test (a case built
while collecting). A change to the case schema, the most edited module, therefore always runs the
development selection: 234 s on 4 cores.

**Open.** A finer rule for module-level code (a changed constant selects its readers, as a changed
function body does) would need its own soundness argument beside WP43 Design §1. Re-measure on the
commits of WP46 before deciding whether it is worth one.

**Fixed.** By removal ([WP44](../plans/phase-4/wp44-simplify-the-loop.md), §8.2.11 L2): no selection exists to fall back from.

### REV-82 — The push gate takes over 9 minutes against its 5-minute budget

*Area:* performance. *Severity:* medium. *Found:* [WP43](../plans/phase-4/wp43-development-loop.md) item 10.

**Measured.** `gate.sh run` on tree `4d9c306` (2,213 tests, the development selection under branch
coverage and the `extended` walks without it, 4 cores, a quiet machine) took 555 s against
§8.2.10 J7's 300 s, beyond the 450 s its 50 % margin allows. WP43 D9 predicted the miss at 6.5 to
8 minutes: example 07's walk alone takes 421 to 477 s and cannot be shortened by the four ways of
§7.6's runtime NOTE without breaking its headroom rule. A follow-up after a pass is bounded below by
the same walk whenever the change reaches a process-starting test (REV-80).

**Fixed.** The author's ruling (J7), taken on the recommendation: `push_gate_s` is 600 s, the measured floor with room for example 07's walk (§8.2.10 J7 amended; VER-73; `.github/budgets.yaml`). The gate still logs the time and never fails on it. Splitting the walk stays open as a way to a lower figure.

### REV-83 — The longest-first test order is inert under xdist file scheduling

*Area:* performance. *Severity:* low. *Found:* [WP43](../plans/phase-4/wp43-development-loop.md) item 10.

**Measured.** WP43 D8 collects files longest first so that `--dist loadfile` would start example 07
first. pytest-xdist re-sorts the files by their number of tests unless `--no-loadscope-reorder` is
passed, so the order only breaks ties. On a quiet machine, `--extended` without coverage on 4
cores took 534 s and 512 s with the order, 477 s without it and 474 s with the order and
`--no-loadscope-reorder` (`knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md#122-where-the-time-goes-on-314-and-coverages-sysmon-core`): within the spread of like runs, and every run
bounded by example 07's 421 to 477 s. The shards' bin-packing reads the same record and is
unaffected.

**Fixed.** The sort is dropped from `tests/conftest.py`: collection keeps pytest's own order (`--ff`, `--nf` and fixture grouping stand), and `tests/durations.json` serves the shards' packing alone (`knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md#122-where-the-time-goes-on-314-and-coverages-sysmon-core`).

**Also found in review.** The same sort in `tests/conftest.py` runs `trylast` over every item, so it
overrides the order that `pytest --ff` and `--nf` produce and undoes pytest's own fixture-grouping
reorder, for no measured gain. Dropping the order settles both.

### REV-84 — A Markdown file that a WP43 test reads is classed as prose, so its test does not run on a change to it

*Area:* verification. *Severity:* medium. *Found:* WP43 review (`/code-review xhigh`).

`.github/scripts/prose-only.sh` calls every Markdown file prose except the paths it lists. The
tests of WP43 read `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md` and
`docs/plans/*.md` (`test_agent_roster.py`: an agent's model and tools, a rule's `paths`, an
`## In brief` over 250 words). A pull request that changes only one of them is classed prose-only:
CI's `changes` job skips the test steps and reports green, and the commit gate runs ruff alone, so
a roster or In brief test never runs on it.

**Fixed.** The author's ruling, taken on the recommendation: `.claude/agents/`, `.claude/skills/`, `.claude/rules/` and `docs/plans/` are not prose in `.github/scripts/prose-only.sh`, so a change to only those runs the tests that read them, by the impact selection in the commit hook and by the shards in CI (`test_prose_only_reads_a_findings_log_as_not_prose`). A `/wp-plan` commit now pays that selection, or the development selection when no map is usable.

### REV-85 — tests/impact.py uses os.path against the coding conventions

*Area:* process. *Severity:* low. *Found:* WP43 review (`/code-review xhigh`).

`.claude/rules/python.md` says `pathlib.Path`, never `os.path`, and covers `tests/**/*.py`.
`tests/impact.py` uses `os.path.realpath`, `join`, `split` and `basename` at about ten sites, some
of them in the recorder's per-event callbacks, where a `Path` object per call would cost.

**Fixed.** `Path` replaces every `os.path` call in `tests/impact.py`. The per-event callbacks already look a path up in the `relpaths` and `identities` caches, so a `Path` is built on a miss only.

### REV-86 — ci.yml repeats the steps of the platforms job in the full-matrix job

*Area:* process. *Severity:* low. *Found:* WP43 review (`/code-review xhigh`).

The `platforms` and `full-matrix` jobs share about 45 lines of near-identical steps, and
`full-matrix` sets `WALKS_ONLY: "false"` and keeps the `walks=(...)` branch that can therefore never
run there. A later change to one job's steps is easily missed in the other.

**Fixed.** The shared steps are the composite action `.github/actions/tier12`, which `platforms` and `full-matrix` both use; the dead `WALKS_ONLY` branch no longer exists in the full matrix (its `walks-only` input defaults to false).

### REV-87 — The plan word cap counts the Outcome that /wp-implement appends

*Area:* process. *Severity:* low. *Found:* WP44 review (`/code-review xhigh`).

`tests/tier1/test_plan_shape.py` counts every word of the plan file against VER-72 (g)'s 1,500-word cap, including the PR line, the commit-sha ticks and the Outcome that `/wp-implement` appends at delivery. WP44's own plan fell from 1,476 to 1,346 words only by deleting its verification table and open questions.

**Fixed.** The author's ruling, taken on the recommendation: the cap counts the planning part only. `plan_problems` leaves out every `> **Outcome` block, an indented per-item annotation included (the blocks `test_plan_records.py` reads), and counts everything else, so a delivery note cannot fail Tier 1 and an early Outcome hides no later item (`test_ver72_g_the_outcome_appended_at_delivery_is_not_counted`, `test_ver72_g_every_outcome_annotation_is_left_out_and_nothing_else`). VER-72 (g), the `wp-plan` skill and §8.2.11 L7 (amended by the author on 13 October 2026) say "outside its Outcome annotations".

### REV-88 — No check remains that the public API carries its docstrings

*Area:* verification. *Severity:* medium. *Found:* WP44 review (`/code-review xhigh`).

D101 to D107 are off (§8.2.11 L4), so no automated check says a symbol of `nanopnp.PUBLIC` or a new package `__init__.py` has its docstring, which the rule requires. With them on, D101, D103 and D104 report nothing today and only D102 reports (51 protocol methods).

**Fixed.** The author's ruling, taken on the recommendation: a Tier 1 test. VER-72 (h) (`tests/tier1/test_public_docstrings.py`) requires a docstring on every module of `src/nanopnp` and on every function or class named in `nanopnp.PUBLIC`, and is shown to name a bare module and a bare public name. The ruff rules D101 to D107 stay off for WP45.

### REV-89 — The shard partition test ignores collection errors and recollects the tree on every commit

*Area:* verification. *Severity:* low. *Found:* WP44 review (`/code-review xhigh`).

`tests/tier1/test_pull_request_shards.py` collects the whole `tests/` tree three times in subprocesses on every commit-hook run (about 8 s wall) and ignores each return code, so a collection error shrinks the compared sets and the test still passes; `tier1 | tier2 == (tier1 or tier2)` is close to a tautology of marker algebra.

**Fixed.** The author's ruling, taken on the recommendation: `test_l3_the_marker_shards_partition_the_selection_with_no_overlap` now collects twice, in parallel, instead of three times: the selection must collect with return code 0 and hold both tiers, and `tier1 and tier2` must collect nothing (exit code 5). A collection error fails the test instead of shrinking the sets.

### REV-90 — VER-72 (d) and the planned-xfail logic guard a marker the workflow no longer writes

*Area:* documentation. *Severity:* low. *Found:* WP44 review (`/code-review xhigh`).

VER-72 (d) and the planned-xfail handling in `tests/tier1/test_plan_records.py` still guard `planned: WP<n>` markers, while §8.2.11 L7 and the rewritten skills retire planned tests. Removing a VER clause is a specification ruling.

**Fixed.** The author's ruling, taken on the recommendation: VER-72 (d) is withdrawn (the letter is not reused) and the planned-marker check, its helpers and its tests are deleted from `tests/tier1/test_plan_records.py`, which keeps (e).

### REV-91 — About 400 tests name their requirement only in a comment

*Area:* documentation. *Severity:* low. *Found:* WP45.

The strip removed test docstrings. Where a test's requirement identifier lived only there, a one-line comment above the test keeps it; the test name still does not carry it (CLAUDE.md asks tests named for their requirement).

**Deferred** (§8.2.11 L10): renamed in a later package.

### REV-92 — src prose share is 10.6 %, above the 10 % prediction

*Area:* documentation. *Severity:* low. *Found:* WP45.

The prediction (at most 10 %) assumed docstrings on `PUBLIC` names only. L4 now keeps a condensed docstring on every public method, so `src/nanopnp` closes at 10.6 % (by subpackage in the plan's Outcome). VER-75 (b) holds the ceiling at 12.48 %, set after review counted attribute docstrings (11.48 %).

**Declined** (§8.2.11 L10): the author accepts the share; no further condensing.

### REV-93 — VER-75 (a) says leading underscore; dunder methods count as public

*Area:* documentation. *Severity:* low. *Found:* WP45.

`test_prose_share.py` treats `__call__` and other dunder methods of a public class as public, so the hook Protocols keep their one-line docstrings. VER-75 (a) and L4 say "leading underscore".

**Fixed** in WP45 (§8.2.11 L10): L4, VER-75 (a), `python.md` and `CLAUDE.md` say a dunder method counts as public.

### REV-94 — 47 public functions and methods carry no docstring, and nothing checks them

*Area:* documentation. *Severity:* low. *Found:* WP45 review (`docs/code_reviews/CODE_REVIEW_006.md`, finding 4).

L4 as amended asks for a condensed docstring on every public function, class and method, but ruff's D101–D107 stay off (L4's consequence column) and VER-72 (h) checks only the `nanopnp.PUBLIC` names. Ruff D101, D102, D103 and D106 find 47 public names without one, among them `CancelFlag.cancelled`, the `NumpyOps` and `NGSolveOps` methods and 17 methods of `physics/stabilisation.py`. They were missing on `main` before WP45 too (51 there); the strip removed none.

**Fixed** in WP45 (§8.2.11 L10): the 47 docstrings are written, and D101 to D103 and D106 hold in `src/nanopnp`.

### REV-95 — VER-75 (a) states a check on derivations and history that no test makes

*Area:* verification. *Severity:* low. *Found:* WP45 review (finding 5).

VER-75 opens "Read from the source", and (a) includes "no docstring holds a derivation or a history". `test_prose_share.py` cannot check that, so the identifier claims more than its test discharges.

**Fixed** in WP45 (§8.2.11 L10): the clause left VER-75; L4 keeps it, for review.

### REV-96 — About 157 prose lines in src and tests still carry identifiers or plan history

*Area:* documentation. *Severity:* low. *Found:* WP45 review (finding 11).

About 93 docstrings and 64 comments in `src/nanopnp` cite `FR-` or `NUM-` identifiers or plan history such as "WP23 D3", and 156 test-module docstrings start with an identifier. L4 and `CLAUDE.md` keep identifiers to test names and commit messages, but `python.md` asks for the source of every constant, which is often a specification identifier.

**Fixed** in WP45 (§8.2.11 L10): plan history left the prose of `src/` and the test comments; test-module identifiers go with REV-91.

### REV-97 — A directive comment is defined twice, differently

*Area:* verification. *Severity:* low. *Found:* WP45 review (finding 14).

`.claude/scripts/same_tree.py` treats a shebang and a coding line as directives and matches its prefixes anywhere in a comment; `test_prose_share.py` and VER-75 (b) list six prefixes at the comment's start. A shebang therefore counts as code for L5 and as prose for VER-75 (b).

**Fixed** in WP45 (§8.2.11 L10): `test_prose_share.py` uses `same_tree.is_directive`, and VER-75 (b) names the shebang and coding line.

### REV-98 — The scratch directory is the workspace itself, where the specification says fresh per run

*Area:* interface. *Severity:* medium. *Found:* WP46 review (finding 6).

`scratch_directory` returns the workspace, created. The workspace-locality NOTE in §5.3.2 says the scratch directory is fresh per run, and plan D4 ruled a fresh `mkdtemp` inside the workspace. Two runs of one `ProtonationStage(workspace=w)` overwrite `w/protonation.npz` and `w/frame-N/*`, so the first run's payload, when no store is attached, disagrees with its recorded digest.

**Fixed** in WP46 (author, 14 October 2026): the scratch directory is the workspace itself. A stage refuses a workspace that already holds files, naming them and the `overwrite_workspace` switch; `overwrite_workspace=True` on the stage, or on `run_case`, replaces them. The workspace-locality NOTE and plan D4 say so.


### REV-99 — A put killed before the rename leaves a hidden staging directory nothing reclaims

*Area:* coupling. *Severity:* low. *Found:* WP46 review (finding 12).

A `put` killed between `staging.mkdir` and the rename (a SLURM time limit, SIGKILL) leaves a hidden `.<digest>.<pid>.<token>` directory with a full copy of the payload, in `artefacts/<slug>/<fanout>/`. Nothing enumerates or removes it.

**Fixed** in WP46: `put` removes hidden staging directories older than a day from the fan-out directory it writes into.


### REV-100 — A put copies and hashes a payload before learning the key is already stored

*Area:* performance. *Severity:* low. *Found:* WP46 review (finding 13).

`put` stages and hashes every payload before it finds a complete entry under the key, then discards the copy. A worker that lost the race pays the full cost of a large solution payload.

**Fixed** in WP46: `put` returns the stored entry before it copies or hashes anything.


### REV-101 — A pre-WP46 charge-grid npz in a store is served under an unchanged key

*Area:* numerics. *Severity:* low. *Found:* WP46 review (finding 14).

The charge-grid key did not move when REV-14 added `origin_nm` and `spacing_nm` to the `.npz`. A legacy axes-only entry is still a cache hit, whose grid differs from a fresh run's in the last bits.

**Fixed** in WP46: the charge-grid key names `lattice_record`, so an axes-only entry misses and the grid is deposited again once.


### REV-102 — frame_times reads a private MDAnalysis attribute

*Area:* coupling. *Severity:* low. *Found:* WP46 review (finding 15).

`frame_times` reads `trajectory._file.header` and copies the expression of `DCDReader._frame_to_ts`, to avoid decoding frames. A release that renames `_file` or changes how `ts.time` is derived makes the DCD branch raise `AttributeError` or disagree with `step.time`.

**Fixed** in WP46: the header read falls back to decoding the frames when the reader no longer has the attribute; the test compares both with `step.time`.


### REV-103 — A verified-only claim outside the test-evidence concepts is not yet classed as executable arithmetic or a source reading

*Area:* verification. *Severity:* low. *Found:* WP47 item 6.

G8 sends a `[verified]` claim whose arithmetic can be executed to a test and keeps a source reading as `[verified]` with a footnote. WP47 applies that split only where a concept's type is Test Evidence, whose `[verified]` claims became tested or pending claims. In the other concepts 56 `[verified]` claims stay as written: 9 cite a source by footnote and 47 name none, so `pending.yaml` counts them as `verified_unsourced`.

**Fixed** in WP48: all 56 `[verified]` markers across the bundle were audited. Executable calculations were backed by tests (including 15 deterministic checks in `tests/tier1/test_knowledge_arithmetic.py`), source readings and historical observations were backed with source footnotes and cited records, and `verified_unsourced` in `pending.yaml` was reduced to zero.


### REV-104 — A correction file keeps a dead citation to the removed flat knowledge file

*Area:* verification. *Severity:* low. *Found:* WP47 review.

The shipped `willems2020_nacl.yaml` still cites the physics note by the name it had before it became a directory in a comment. Its bytes are part of the pinned v0.5 solve key (VER-59), so the citation check skips it and a comment edit would move the key.

**Fixed** in WP47: the comment names the errata concept, the pinned solve key in `tests/tier2/test_exclusion_keys.py` is re-pinned to the new bytes, and the citation check no longer skips the file.


### REV-105 — SPECIFICATION G12 (7) says the navigation is generated from the index files; the build has one static entry

*Area:* documentation. *Severity:* low. *Found:* WP47 review.

The ruling reads that the documentation navigation comes from the `index.md` files. `mkdocs.yml` has one `Knowledge base` entry and lists the rest under `not_in_nav`.

**Fixed** in WP47: `docs/scripts/generate.py` writes the knowledge navigation into `mkdocs.yml` between two marker comments, read from the `index.md` files; a Tier 1 test fails when the block is stale, so the ruling and the build agree.


### REV-106 — The heading-slug function differs from the table-of-contents slugger for emphasis, entities and images

*Area:* verification. *Severity:* low. *Found:* WP47 review.

`okf.headings` strips the markup it knows; `_emphasis_`, HTML entities and images are read differently from the documentation build, so a citation to such a heading could pass the check and miss. No heading of the bundle has these today (the docs-anchor test compares all 241).

**Fixed** in WP47: the slug function reads emphasis with underscores, entities and images as the documentation build does, and a test compares seven such headings with the build.


### REV-107 — About 40 log entries are fragments

*Area:* documentation. *Severity:* low. *Found:* WP47 review.

Entries of `knowledge/log.md` made by cutting the old notes' dated lines read as fragments such as `Source: WP26 implementation session`. Two glaring ones were repaired in the WP47 review.

**Fixed** in WP47: the fourteen entries cut mid-sentence now state what the concept records, taken from its description and the source it named; the measurements stay in the concepts.


### REV-108 - WP48 omitted sourced arithmetic from its audit

*Area:* verification. *Severity:* medium. *Found:* WP48 plan review ([report](../code_reviews/CODE_REVIEW_007.md)).

The original D2 audited only the 47 unsourced verified markers. Nine others already have footnotes, and at least three contain executable arithmetic; the pending ledger cannot detect that G8 work.

**Fixed in the WP48 plan:** D2 and item 4 audit all 56 verified markers and require tests for sourced calculations too. This closes the planning omission, not the implementation; REV-103 remains open.


### REV-109 - WP48 omitted version metadata coverage and refusal checks

*Area:* verification. *Severity:* medium. *Found:* WP48 plan review ([report](../code_reviews/CODE_REVIEW_007.md)).

The original D3 and item 5 omitted the numerics Library Behaviour concept, and their completion test accepts absent, non-mapping or empty metadata. All 17 concepts currently lack the key and that test passes.

**Fixed in the WP48 plan:** D3 selects by type across the bundle, and item 5 requires presence enforcement, negative fixtures and the matching VER-68 amendment. Implementing those checks remains WP48 work.


### REV-110 - WP48 lacked an evidence route for historical numerical experiments

*Area:* verification. *Severity:* medium. *Found:* WP48 plan review ([report](../code_reviews/CODE_REVIEW_007.md)).

The pending claims include numerical sweeps no current fixture runs and aliasing errors on millions of elements. Extra assertions or toy tests cannot establish those measurements at the original promised zero additional solver cost.

**Fixed in the WP48 plan:** D1 inventories evidence and cost; D5 separates immutable historical records from current properties requiring tests. Unsupported measurements stay unresolved. The unconditional runtime promise and guessed intermediate ceilings are removed; implementation must establish the resulting evidence.


### REV-111 - The no-MPI-symbols claim is backed only by the lock file

*Area:* verification. *Severity:* low. *Found:* WP48 `/wp-ship` review.

`knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md` says no shipped `.so` of the NGSolve wheels carries MPI symbols and there is no `mpi4py`. Its marker cites `test_ngsolve_wheel_table_and_config_flags`, which shows only that `mpi4py` is not a locked package, so the symbol half of the claim has no test. Scanning the shipped binaries for MPI symbols depends on how NGSolve loads MPI, which is unsettled.

**Open:** the author rules whether to add a binary scan, or to narrow the claim to the lock file and the configuration flags.

**Ruled** (§8.2.22 X7): the claim is narrowed to what is tested, `mpi4py` not locked and the configuration flags showing no MPI; no binary is scanned. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): The claim in `knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md` is narrowed to the lock file and the build configuration, with the test that shows the flags; no binary is scanned.


### REV-112 — Three suspected costs were never measured

*Area:* performance. *Severity:* low. *Found:* the external architecture review of 18 October 2026,
claims A1, A8 and A16, checked at `645289e` (§8.2.12).

**Measured.** Not yet. The aligned ensemble holds every frame in one float32 array
(`structure/ensemble.py`); each continuation rung rebuilds its symbolic forms (`physics/models.py`);
each stage reads its inputs back through the store (`pipeline/run.py`). None has been timed or sized.

**Fixed in the WP49 plan:** measured on the quick-start pore and the prepared 2WCD
(`docs/project/cost-study.json`). Stage 1 projects to 1.14 GB at 1,000 frames (limit 4 GB); building
forms is 0.02 % to 0.33 % of stage 10 (limit 5 %); store IO is 0.10 % to 0.51 % of a cold walk (limit
10 %). None is over its threshold, so nothing is changed (M2). The A8 and A16 figures under-count;
the fixed harness gives at most 0.54 % and 0.69 %, and the record is replaced at the close (REV-116).

### REV-113 — The case schema has no JSON Schema export

*Area:* interface. *Severity:* low. *Found:* the same review, claim A17.

The case document is Pydantic v2 with `extra="forbid"` (`io/case.py`), but nothing exports it as a
JSON Schema that a browser editor or another tool could read.

**Fixed in the WP49 plan:** `case_json_schema()` exports the schema, the documentation build publishes
it as `reference/case.schema.json`, and VER-76 checks its leaves against `case_fields` in both
directions.

### REV-114 — The shell moves from Qt to a browser

*Area:* interface. *Severity:* medium. *Found:* the same review, claims A4 to A7.

The review proposed removing PySide6, the Qt widgets and the PyInstaller bundle for a local server and
a browser front end. Its plan modified `webgui.js`, which CON-09 forbids, and ADR-004 had rejected the
alternative. The author ruled the browser shell for Phase 5 (M3); ADR-004 and CON-09 carry a NOTE.

**Resolves it:** Phase 5's design document restates the shell's gating clauses for the browser shell,
which then replaces the Qt shell.

**Fixed** (§8.2.18 T5) by WP5.01: the gating clauses are restated as `NOTE (the browser shell, v0.6)` beside each, and the package that removes Qt makes them the text.

### REV-115 — The architecture review's already-met claims

*Area:* process. *Severity:* low. *Found:* the same review.

Eleven claims describe what the code already does or what a ruling already placed: A2 (patch-limited
kernels and bucketed point location), A3 (exact annulus weights, closed-form azimuthal kernel,
conservation gate), A9 (NUM-21; the solver registry), A10 (NUM-02's log branch, damping cut by the
increment gates), A11 (heat-method distance with a smoothing pass; closed-form corrections), A12
(MOD-08, MOD-09), A13 (`post/indicator.py` is NUM-24's ψ; adaptivity is FR-29, post-1.0), A14
(NUM-25), A15 (the spawned pool and the warm-start forest), A16's atomicity (`io/store.py` stages and
renames) and A18 (`requires-python` is already `>=3.11,<3.15`). The evidence for each is in §8.2.12's
preamble.

**Declined** (M1): no change.

### REV-116 — The cost record predates the harness fixes

*Area:* verification. *Severity:* low. *Found:* WP49 `/wp-ship` review
(`docs/code_reviews/CODE_REVIEW_009.md`, R2 to R7).

`docs/project/cost-study.json` was written by the harness as it stood before the review. That harness
missed calls made through a `from … import` copy (the ladder in `solve/stage.py`, the mesh read and
write in `mesh/ingest.py`), timed only the opening of a lazy `.npz`, left the payload types' own
reads and writes off the list, and ran both walks in one process. Its A8 and A16 shares therefore
under-count, and its environment block names `4deb53e` on a dirty tree. The fixed harness, run once on
a loaded container and an uncommitted tree, gave A8 at 0.03 % and 0.54 % (limit 5 %) and A16 at 0.69 %
and 0.64 % (limit 10 %): every verdict holds. A1's method is unchanged and its 1.14 GB stands.

**Open.** The author ruled on 18 October 2026 against a re-run in WP49, since no verdict can change.
The row stays open until the Phase 4 close re-runs `python -m nanopnp.validation.costs all` on a clean
tree, replaces the record and sets it `fixed`.

**Fixed in WP60:** the quick-start leg walked the removed `nanopnp mesh cylinder`, so the leg now walks
the shipped case (`validation/costs.py`). `python -m nanopnp.validation.costs all` ran on the clean
commit `db952e3`, four CPUs, threads unset (`"dirty": false` in every environment block), and replaced
the record. A1 projects 1.15 GB of stage 1 at 1,000 frames (limit 4 GB). A8 is 0.69 % on the quick-start
walk and 0.03 % on 2WCD (limit 5 %). A16 is 0.84 % and 0.70 % (limit 10 %). No share is over its
threshold, so no cost fix follows (§8.2.12 M2).

### REV-117: Tooling left without tests by the test scope

WP50 deleted the tests of the OKF checker (`validation/okf.py`), the findings-log reader, the plan
shape, the same-tree and push-guard scripts and similar repository tooling (§8.2.13 N3). The tools
stay in `src/` and `.claude/`, as WP50's scope kept them, and nothing now exercises their checks.

Two parts are still called by a gate, so neither module can be deleted whole. `docs/scripts/generate.py`,
which CI's `docs` job runs on every push, imports `navigation` and `splice_navigation` from
`validation/okf.py`, and `tests/tier1/test_library_behaviour.py` takes `REPOSITORY` from it.
`tests/tier1/test_layering.py` (VER-61, a kept guard) imports `REPOSITORY` and `parse_log` from
`validation/findings.py`.

**Fixed** (author's ruling, WP50 review). The checks of the OKF bundle and of the findings-log format
are deleted; `validation/okf.py` keeps the navigation helpers and `REPOSITORY`, and
`validation/findings.py` keeps `parse_log` and its types.

### REV-118: Gate and mechanism tests the pruning removed

WP50's review found deletions that arguably fall inside §8.2.13 N1 (doubt keeps the test) and
restored two groups (the number-stability file tests, the solution-state integrity tests). Three
remain deleted:

- the VER-71 classification-completeness tests of `test_case_leaves.py`: a new solve leaf that is
  accepted and ignored is caught only if it is added to `SOLVE_PROBES` by hand;
- the field-input gates of `test_charge_fields.py` (non-finite header value, units against quantity,
  solid fraction as fixed charge, absolute permittivity, non-uniform axis, grid descriptor), which
  stop a wrong quantity reaching the charge or dielectric;
- the manifest tests that every manifest carries the eight §5.3.3 groups, each absent group with a reason.

**Fixed** (author's ruling, WP50 review). All three groups are restored in `test_case_leaves.py`,
`test_charge_fields.py` and `test_manifest.py`, and `test_case_json_schema.py` (VER-76) is restored whole.

### REV-119: The analyte benchmark meshes skip the quality gate

`AnalyteInBoxGeometry.generate` and `PoreWithAnalyte.generate` (`geometry/analyte.py`) return the
netgen mesh without the element-quality gate (minimum SICN and gamma above 0.3) that every primitive
in `mesh/primitives.py` applies. Their only callers are the Tier 2 force benchmarks, which compare
with analytic values, so a degraded mesh fails there and not at a gate that names the element.

**Declined** (author's ruling, CODE_REVIEW_010 CR-8). A gate inside `geometry/` is a new upward
`geometry → mesh` edge, which VER-61 refuses, and moving both classes into `mesh/` costs more than a
low finding is worth.

### REV-120: The force-traction normal needs one material on the left along the whole surface

`MeshData.oriented_edges` directs every boundary edge with the adjacent triangle of the first material
by name on its left (CODE_REVIEW_010 CR-5), and `post/forces.py` fixes only the overall sign of the
traction normal, by n·(x − c). Along a surface whose neighbouring material changes, the first material
by name is not always the same side: an analyte that straddles the electrolyte/`cis` interface has the
analyte on the left where it meets `cis` but, were the body named after `electrolyte`, not where it
meets `electrolyte`. The normal then points out of the body on one part and into it on the other, and
part of the traction is negated with no warning. The built-in analyte geometry refuses a body that
crosses a pore mouth (`geometry/analyte.py`), and a body named `analyte` sorts before `cis`,
`electrolyte` and `trans`, so the built-in path is safe; a supplied `inputs.mesh` with a body of
another name that touches two fluid domains is not stopped.

*Recommendation:* refuse, in the force stage, a force surface whose two sides are not one pair of
materials all along it, rather than orient it by name. Not done here: it widens a review-fix package
into the force stage.

**Ruled** (§8.2.22 X6): accepted as recommended. NUM-29's NOTE on the force surface states the refusal. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): `post/forces.py:check_force_surface` names the pair of materials on the two sides of the force surface and refuses a surface of several, exit 4; `extract` calls it with the ingested mesh, and the QoI stage passes it.

### REV-121: Stage 1 checks no axis for a monomeric or hetero-oligomeric pore

`symmetry.axis: auto` finds the axis by cyclic chain permutation, so it needs n ≥ 2 chains that agree
in residue name wherever they share a residue number, each with at least half the C-alpha of the most
complete chain (`structure/read.py`; VER-48 refuses `auto` on C1). A hetero-oligomeric pore is
therefore refused, and a monomeric (C1) pore runs only under `symmetry.axis: z`, which takes the
file's z axis through its origin unchecked (§5.3.1). Found by CODE_REVIEW_012 AR-09.

**Deferred** (§8.2.24 Z5, 31 October 2026) to the Phase 5 package that surfaces structure
preparation, FR-37's v0.6 half, which must present a trustworthy axis for such an assembly before it
can prepare one; `/np-plan amend 5` places it. The fix is an axis estimate from the channel cavity,
gated like the permutation axis, for C1 and hetero-oligomeric assemblies, and it needs the changes to
§5.3.1 and VER-48 in the same package. FR-37's v0.5 library half, `orient_pore`, is not affected:
the gap is stage 1's `symmetry.axis` path. Confirmed as a gap by the author on 20 October 2026
(CODE_REVIEW_012 disposition).

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.16, the Molecular suite, library step first, with §5.3.1 and VER-48.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.16, the Molecular suite.

### REV-122: A case cannot load a correction file from outside the installed package

`electrolyte.parameters` and every `electrolyte.corrections.*.model` must name a file in
`CORRECTIONS_DIR`, inside the installed package (`core/paths.py`); any other name is refused as not
installed (`io/case.py`). `materials.models.register` adds a coded correction from Python, but no
route reads a parameter file from elsewhere. FR-16's "a new electrolyte or surface is a data file
rather than a code change" therefore holds only for a repository checkout: an installed user writes
into site-packages. Found by CODE_REVIEW_012 AR-15.

**Open** (author's ruling, CODE_REVIEW_012 disposition, 20 October 2026): confirmed.
*Recommendation:* admit a case-relative or absolute path. The case file is the unit of
reproducibility and a file outside the wheel is not pinned by its version, so the file's content
hash enters the stage-8 key and the FR-25 manifest, and the manifest lists it as a deviation from the
validated default; otherwise a cached result survives an edit of the file.

**Ruled** (§8.2.22 X6): accepted as recommended. §5.3.1's NOTE on a correction file outside the package states it. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): A correction file named by an absolute or case-relative path is read, its content hash enters the stage-8 key and the manifest, and it is listed as a deviation.

### REV-123: The library has no plotting helpers or notebook display

`src/nanopnp/` imports no plotting library outside `gui/`, whose plots are PySide6 widgets
(`ConvergencePlot`, `GeometryCanvas`) and whose `gui/render.py` writes Three.js files to disk. No
artefact or result type defines `_repr_html_` or `_repr_svg_`. A notebook user reads the arrays
(`PoreProfile.as_array()`, `MeshData.vertices`, `sample_at()`) and writes the figures by hand. No
requirement asks for either. Found by CODE_REVIEW_012 AR-16 and AR-17, merged here.

**Open** (author's ruling, CODE_REVIEW_012 disposition, 20 October 2026): confirmed as a feature gap.
*Recommendation:* an optional `plot` extra with Matplotlib helpers for the profile, mesh and fields,
and rich display on `RunResult`, `PoreProfile` and `MeshData`, kept off the default import path. It
needs a requirement first.

**Accepted** for WP51 (author's ruling, §8.2.14 P1 to P6, 22 October 2026). FR-30 states the
requirement. Matplotlib draws in a new `plot/` subpackage below `pipeline`. A stage declares its
figure in the stage registry, and every artefact and `RunResult` displays itself in a notebook.

**Fixed** (WP51, 22 October 2026). `nanopnp.plot` draws a figure of every stage's artefact and of a sweep, the stage registry declares each figure, `Artefact` and `RunResult` display themselves in a notebook, and four marimo notebooks run nightly (FR-30; `CHANGELOG.md`, `0.5.0-alpha.17`).

### REV-124: The specification's site navigation is listed by hand

`mkdocs.yml` lists the specification bundle's 52 pages by hand (WP52 plan D5), while the knowledge
base's navigation is generated from its index pages. `nav.omitted_files` is `warn` under `--strict`,
so every new `specification/` file, one per amendment until WP53 rewrites the skills, fails VER-45's
build until it is listed. Generating it would generalise `okf.navigation` in `src/`, which WP52 left
untouched. Found by CODE_REVIEW_013.

**Fixed** in WP52 (author's request, 22 October 2026): `nanopnp.validation.okf.navigation` takes the
bundle's title and its opening and closing entries, and `docs/scripts/generate.py` writes the
specification's navigation between its own markers in `mkdocs.yml`, read from `specification/index.md`
and the directory indexes. The root index lists the top-level files and the directory indexes only.

### REV-125: The workflow files exceed the plan's word caps

WP53's plan D2 caps one invocation at 2,200 words and the new files at 7,000 in all, and the core at 900. The delivered files hold 7,409 words in all, a core of 974, and invocations of 2,282 to 2,995 for `/np-plan` and 2,318 and 2,548 for `/np-ship` (`wc -w`, the plan's item 11 Outcome). No rule was cut to meet a count, and only the plan's Outcome and the pull request body recorded the overshoot. Found by CODE_REVIEW_014.

**Fixed** in WP53 (author's direction, 23 October 2026): D2 and its Verification row now state the caps as delivered, measured after the `PR:` line was dropped and CODE_REVIEW_014's fixes were merged. The core is 985 words, one invocation 3,006 at most (`np-plan phase`), and the new files 7,518 in all. The router cap of 150 holds, as the largest router is 137. The cut the review named, from `np-plan/phase.md` and `np-plan/rulings.md`, is not made.

### REV-126: Package numbers can collide between the two lanes

Phase 4's remaining packages are numbered from WP56 when the second `/np-plan amend 4` runs (its fix packages, documentation increment 4 and the close), while Phase 5's plan already claims WP57 and WP58 (§8.2.17 S1, S14). S15's renumbering covers `REV-nn` rows, history records, code reviews and `VER-`/`VAL-` identifiers, not package numbers, so plan files, PR titles, tags and `current.md` could name two packages with one number. Found by CODE_REVIEW_015, finding 2.

**Open** for the author: number Phase 4's remaining packages now, start Phase 5 above them, or add package numbers to S15's list.

**Fixed** (author's ruling, 24 October 2026, §8.2.17 S16): from Phase 5 a package is `WP<phase>.<nn>`, numbered from 01 within its phase, and Phase 4 keeps its flat numbers to its close, so the lanes cannot claim one number. WP57 and WP58 are WP5.01 and WP5.02 (§8.4.4).

### REV-127: WP57 may restate the Qt shell's gating clauses before v0.5.0

WP57 may merge before `v0.5.0` (S1) and restates VER-43, VER-44, VER-55, VER-60, CON-09's PySide6 clause, ADR-004's packaging NOTE, RSK-13, P3 and QR-10 for the browser shell. The lane excludes `src/`, `tests/`, the case schema and the public API, not normative clauses, and M3 keeps those clauses gating the Qt shell that `v0.5.0` ships. Found by CODE_REVIEW_015, finding 5.

**Open** for the author: add each restatement beside its clause, tagged v0.6, until Qt leaves, or hold WP57's restatements until after `v0.5.0`.

**Fixed** (author's ruling, 24 October 2026, §8.2.17 S17): a clause the design study restates before the current release is added beside the clause, tagged v0.6, and replaces it only at `v0.6.0`, so `v0.5.0` ships the clauses gating its Qt shell (§8.4.4; the Phase 5 plan's WP5.01).

### REV-128: The renumbering list leaves out other identifier kinds and the ruling letters

S15 and §8.4.4 renumber `REV-nn` rows, history records, code reviews and `VER-`/`VAL-` identifiers, but not `FR-`, `QR-`, `IF-`, `CON-`, `RSK-`, `ADR-` or `OPN-` identifiers, nor the §8.2 record number and its ruling letter series, all of which a lane can add. Found by CODE_REVIEW_015, finding 7.

**Open** for the author: widen the list to every numbered register and the ruling series.

**Fixed** (author's direction, 24 October 2026, §8.2.17 S18): the pull request that merges second renumbers every new item of every numbered register, the requirement identifiers of every prefix and the history records with their §8.2 number and ruling letters included, with every reference (§8.4.4; `.claude/workflow/core.md`).

### REV-129: WP58's tag and the place of a held changelog entry are undefined

If WP57 merges untagged before `v0.5.0`, nothing says whether WP58 is `v0.6.0-alpha.1` or `-alpha.2`: `CONTRIBUTING.md` counts the phase's packages. "The next release's section" is undefined in a changelog ordered newest first, where a `[0.6.0]` section above later `[0.5.0-alpha.N]` sections breaks the order. Found by CODE_REVIEW_015, finding 9.

**Open** for the author: rule WP58's tag and where a held entry sits.

**Fixed** (author's ruling, 24 October 2026, §8.2.17 S19): N is the package's number within its phase, so WP5.02 takes `v0.6.0-alpha.2` whether or not WP5.01 took a tag, and an untagged package's entry goes under `## [Unreleased]`, moved by the next tagged package of its phase (§8.4.1; §2.7's Versioning NOTE; `CONTRIBUTING.md`).

### REV-130: Nothing checks that identifiers stay unique after both lanes merge

Renumbering happens only when a later `/np-ship` merges `main` into a stale branch. Two lanes' PRs merged one after the other can each add the same `VER-` number or history record in different files, with no textual conflict and no test of uniqueness. Found by CODE_REVIEW_015, finding 10.

**Open** for the author: add a Tier 1 or CI uniqueness check over the registers, or accept the manual rule.

**Fixed** (author's ruling, 24 October 2026, §8.2.17 S20): `/np-ship` runs `.claude/scripts/duplicates.py` after merging `main`, and the author merges a second-lane pull request only after `/np-ship` has run on it against the current `main`. No test, as §8.2.13 N3 withdrew the repository self-checks (§8.4.4; `np-ship/wp.md` §1 and §6).

### REV-131: The charge-level mutator has no library step or tier row

v0.6 ships the charge-level mutator (S3 to S5), but the Phase 5 plan gives it no library function and no Tier 1 or Tier 2 row, and the library has no residue mutation, against the library-first rule §8.1 sets for the other tools and RSK-15's mitigation. Found by CODE_REVIEW_015, finding 12.

**Open**: WP57's design document places the mutator; `/np-plan amend 5` plans its library step and tests.

**Fixed** in the Phase 5 plan (24 October 2026): the shell packages land the mutator library first, a `charge/` function that sets a residue's charge state with a Tier 1 test that the projected charge changes by that residue's alone, before its shell control; the Verification table lists the test.

### REV-132: The Phase 5 end-of-phase report names no source for its numbers

The report lists click-to-redraw time, clean-machine install time and VER-77's counts with no test or command that logs them, which the phase-plan template requires and the close must re-run. Found by CODE_REVIEW_015, finding 14.

**Open**: WP58 defines the measures and the commands that log them.

**Fixed** in the Phase 5 plan (24 October 2026): VER-77's test logs its screen and state counts, and WP5.02 names the commands that log the click-to-redraw and clean-environment install times, which the close re-runs.

### REV-133: The Phase 5 plan and the core exceed their word caps

The Phase 5 plan holds 1,671 words against `np-plan`'s 1,500 target, checked at review (§8.2.13 N3); the core holds 1,111 against the 985 delivered under REV-125, and the workflow files exceed their 7,518 in all. `current.md` was cut to 695. Found by CODE_REVIEW_015, finding 11.

**Open** for the author: cut the plan and the core, or restate the caps.

**Fixed** (24 October 2026): the Phase 5 plan holds 1,500 words without its report, and the core 985. The workflow files hold 7,666 words in all against WP53's delivered 7,518: the difference is the rules S15 to S20 add to the level files, kept rather than cut, as REV-125 did.

### REV-134: The Qt shell's Result tab prints the stored float wrapper, not the number

`gui/run_model.py` reads the run record's `quantities` as stored, so the Result tab shows each float as the canonical wrapper, `{'__f__': '0x1.ac1ece4e515e9p-35'}` for `current_A`, where the command line and `pipeline/reproduce.py` undo it with `core/hashing.py:decode_floats`. A user of the v0.5 shell cannot read the current, conductance or transport number. Found by WP5.01's critique of today's shell (`/np-gui review`, finding C45, on example 07).

**Open** for the author: fix it in the Phase 4 lane before `v0.5.0` (one call to `decode_floats` and a number format with units), or carry it until the browser shell replaces the Qt one. WP5.01 changes no `src/` (§8.2.17 S1).

**Ruled** `deferred` (§8.2.19 U1): carried until Qt leaves. `v0.5.0` ships the wrapper on the Result tab, and the user-testing sessions read the numbers from the command line or the run record; the package that removes Qt closes the row, the browser shell reading the numbers through `plot/data.py`.

**Placed** (§8.2.31 AG1, 3 November 2026): WP5.21, which removes Qt.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.21, which removes Qt.

### REV-135: The density does not see the protonation chosen at the charge stage

The density stage smears the atoms of the structure as loaded at stage 1 (`density/stage.py`, its record counting the
hydrogens present), while protonation is chosen later, at stage 7's PDB2PQR and PROPKA step, and is not fed back. A
protonation state, or a charge-level mutation (§8.2.17 S4), therefore changes the charge but not the density, contour
or mesh. The author, marking today's shell (WP5.01, `docs/design/reviews/2026-10-25-qt-shell.md`, `opened-charge`):
"changes in protonation state may impact density, and thus geometry".

**Open** for the author, as a physics question for the knowledge base: whether the density should be built from the
protonated structure, and so whether protonation moves before the geometry stages in the pipeline, not only in the
workbench. The workbench design places protonation in the molecular area, before the geometry builder, either way.
WP5.01 changes no `src/` (§8.2.17 S1).

**Ruled** (§8.2.19 U2): protonation moves before the geometry stages, and the density smeared from the protonated frames is the validated default; the hydrogens as loaded become a switch, set by the reference-reproduction cases. WP5.03 lands it (§8.2.28 AD3), before the charge mutator, with a Tier 1 test that a changed protonation state moves the density (the NOTE beside PHY-16 step 3).

**Fixed** in WP5.03: `protonation` walks before `density`, stage 2 smears the protonated atoms by default (`geometry.density.atoms`), and a Tier 1 test shows that a changed protonation state moves the map (`test_ver49_a_changed_protonation_state_moves_the_density`).

### REV-136: The organisation round's rulings need library capabilities v0.5 lacks

The design round of WP5.01 (`docs/design/workbench.md`, *Decision log*) rules a workbench whose suites rest on
capabilities the library does not have at v0.5: structure preparation (WB-14: the axis estimated, the chains chosen,
the flip and the membrane's place set by the user); named molecular and continuum models that a case references and
resolves into one complete case file (WB-11, a case-schema change); studies that override the continuum model's
physics defaults (WB-16); and a saved comparison of two runs with a difference field (WB-04). RSK-15 lets no screen
be built for a capability Tiers 1 and 2 do not verify, and §8.2.17 S7 puts each new capability in the library
first. The concept-board review found the comparison and the queue drawn with no verifying artefact (finding B14).
The choice-panel review adds probes and cuts on a field, selecting mesh elements by a quality measure, an arrangement
of result tiles, and the deployed charge linked back to its residues (WB-06), each drawn with no verifying artefact
(`docs/design/reviews/2026-10-25-choices.md`, finding F). The author's picks add size fields over
sub-regions drawn by hand, to refine the mesh locally beyond the size table's parts (the ME1 note); the mockups draw
them with the later-phase banner.

**Open** for the author; proposed owner `/np-plan amend 5`, which sets Phase 5's packages after WP5.02: each capability becomes a library
package with its tests before the shell surfaces it, or the author moves it to a later phase. WP5.01 changes no
`src/` (§8.2.17 S1); its item 15 writes the requirements.

**Ruled** (§8.2.19 U3): owned by `/np-plan amend 5`, as proposed; the author rules the cut line between v0.6 and later phases there.

**Progress** (§8.2.20 V1): structure preparation's library half lands in WP54 as `nanopnp.structure.orient_pore`
(FR-37), which estimates the axis, keeps the chains named, points +z at the end the user names and places a
registration centroid; the workbench surfaces it in Phase 5 (WB-14). The item stays accepted for the other
capabilities.

**Cut line ruled** (§8.2.31 AG1, AG6, 3 November 2026): v0.6 holds every capability FR-31 to FR-39 name, placed in WP5.05 to WP5.08 and WP5.16 to WP5.20, and the comparison's difference of two runs' fields over the overlap of their fluid domains, library step first in WP5.20. Hand-drawn refinement regions, the Python console, the ribbon, FR-43 and FR-28 stay later. The item stays accepted until WP5.20 lands.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): the shell's packages are WP5.08 and WP5.15 to WP5.22, the difference field in WP5.20, the Analysis suite.

### REV-137: No renderer is chosen for the molecule in 3D or for the explorer's controls

CON-09 lets the field viewer's renderer, npm `webgui`, ship only unmodified and as a separate file. The organisation
round places a 3D molecule view in the Molecular suite (WB-05, WB-14) and asks the results explorer for zoom, a
colour scale per quantity, the mesh on or off and a framed opening view (the author's verdicts on today's shell);
`webgui` draws meshes and fields, not a molecular cartoon, and whether its own interface offers each control is not
checked. Found by the concept-board review (finding B15).

**Open** for the author; proposed owner WP5.02, whose spike chooses the front end (§8.2.17 S8): it names the renderer for each view, checks
the explorer's controls against `webgui`'s interface, and puts any second renderer's licence to the author under
CON-09.

**Ruled** (§8.2.19 U5): owned by WP5.02, as proposed.

**Fixed** (§8.2.19 U5, 2 November 2026, in WP5.02): the renderer table in `docs/design/workbench.md` (*The
renderers*): Mol* for the molecule, as its unmodified standalone bundle; `webgui` for meshes and fields; a canvas
drawn from `plot/data.py` for maps and plots. The table checks the explorer's four controls against the shipped
`webgui.js`: zoom and the mesh on or off are served, a colour scale for each quantity in part (one colour map per
scene), and a framed opening view not at all. The front end is NiceGUI over FastAPI (ADR-004's NOTE). No second
renderer needs a licence ruling under CON-09.

### REV-138: The render check measures text contrast but not the contrast of controls and graphics

`.claude/scripts/gui/shoot.cjs` checks each visible text element against WCAG 2.2 1.4.3 and each native control's size
against 2.5.8, and reports nothing else: an input's border, a focus ring, a selection fill or a colour bar's low end
is never measured against 1.4.11's 3:1. The style tile's review found input borders near 1.3:1 and viridis's dark end
near 1.1:1 on a dark panel, while `index.json` reported no failure (finding T1). WB-24 holds the workbench to
non-text contrast as well.

**Open** for the author; proposed owner WP5.02, which extends `/np-gui render` with the shell target: measure the
border, outline and fill of every control, and the ends of every colour bar, against the surface behind them.
Until then a review states non-text contrast as not measured. `tokens.css` holds its own pairs at 3:1 by
calculation.

**Ruled** (§8.2.19 U5): owned by WP5.02, as proposed.

**Fixed** (§8.2.19 U5, 2 November 2026, in WP5.02): `.claude/scripts/gui/shoot.cjs` has a `nontext` check: it measures
the border, outline and fill of each control, and the ends of each colour bar, against the surface behind them at WCAG
2.2 1.4.11's 3:1, beside the text and target-size checks. `/np-gui render shell` and `mockups` run it. The design
study's pages fail it in places (REV-176).

### REV-139: The sweep needs a design round: any value, user-defined variables, rebuilds detected

The author, marking the mockups' sweep (WP5.01, `docs/design/reviews/2026-10-26-mockups.md`, `st-sweep`): "I like
having the ability to sweep over everything. We should also be able to sweep over user-defined variables, and the need
for remeshing should be detected (and mentioned as a warning perhaps?). This screen needs some brainstorming still."
Round 2 of mockup A draws a first take: a list of parameters over any value, each naming what it rebuilds, a named
variable that several fields share, and a warning with the count of builds when a parameter changes the geometry.
FR-24's sweep already ranges over any case-file field; the library does not sweep over named models (WB-11), a case
has no variables, and nothing says which stages a value invalidates before the walk reaches them.

**Open** for the author: a design round on the sweep (`/np-gui grill`), then its library capabilities, as REV-136's
are, in a package after WP5.02. Variables in a case are a case-schema change for a package after `v0.5.0` (§8.2.17 S1).
The stages a value invalidates follow from the content hashes that key each stage's artefact (FR-27).

**Ruled** (§8.2.19 U4): the design round runs in `/np-plan amend 5`, as a `/np-gui grill` after WP5.02 has chosen the stack; its library capabilities join REV-136's packages.

**Design round held** (§8.2.31 AG2 to AG5, 3 November 2026), over mockup A's round-2 `st-sweep`: a variable is a value with its unit or an expression of others, parsed without running code; units are checked through `pint`; stages and identity are keyed by the resolved values, the variables recorded as written; and a forecast of the stages each swept value rebuilds is shown as a warning. WP5.07 lands the library step (FR-39); WP5.19 the Sweep tool.

**Fixed** (WP5.07, [the plan](../plans/phase-5/wp5.07-variables-and-the-rebuild-forecast.md)): the library step. A case defines `variables:` with units and expressions, keyed by the numbers they resolve to; a sweep axis ranges over `variables.<name>`; and `forecast` says before a sweep runs which stages each axis rebuilds and how many builds come before the solves (FR-39; §5.3.1 NOTE on `variables:`, §5.3.4). The Sweep tool that shows the warning beside the parameter is WP5.19's (FR-39's Appendix A row).

### REV-140: Two of the author's marks on the mockups ask what is not yet said

Two of the author's marks on mockup A (WP5.01, `docs/design/reviews/2026-10-26-mockups.md`) could not be acted on:

- `g-geometry`, the protein geometry tool, is marked `change` with no note.
- `m-protonation` asks for "partial protonation" among the protonation's settings. The protonation stage assigns each
  titratable group one state from PROPKA at the pH (PHY-16 step 3; FR-12); a partial, or fractional, state is not
  specified. Round 2 draws it with the later-phase banner.

**Fixed** (§8.2.18 T6, T7): the `g-geometry` mark was a slip, and the screen stands as `fine`. Partial protonation is a fractional charge at the pH, each titratable group carrying its charge averaged over its states from its pKa: FR-43, a later capability whose physics its library package writes, shown in v0.6 with the later-phase banner.

### REV-141: CON-08 and CON-11 name a bundle and a desktop path the browser shell removes

CON-11 makes "the redistributable bundle" default to UMFPACK under GPL-2+ obligations stated in its licence notice,
and CON-08 has "the desktop path" use UMFPACK or SuperLU. The browser shell ships no bundle (§8.2.17 S12): the
workbench is the package with its `gui` extra, installed from wheels, and WP5.01's restatements of the packaging
NOTE and RSK-13 say so. Neither constraint was in the set WP5.01 restates (IF-09, P3, QR-10, VER-43, VER-44, VER-55,
VER-60, CON-09, ADR-004's packaging NOTE, RSK-13), so once Qt leaves no text says which linear solver an installed
workbench defaults to, where UMFPACK comes from on a wheel install, or where its GPL-2+ notice is shown. Found while
writing the restatements (WP5.01 item 15). VER-60's restatement keeps the probe sentence's last
clause, "the licence notice has a row for each payload", which names the bundle's CON-11 notice.

**Open** for the author; proposed owner WP5.02, whose spike records the front end and the packaging in ADR-004
(§8.2.17 S8): restate CON-08 and CON-11 for an installed workbench, beside the other restated clauses.

**Ruled** (§8.2.19 U5): owned by WP5.02, as proposed.

**Fixed** (§8.2.19 U5, 2 November 2026, in WP5.02): the NOTEs on CON-08 and CON-11 in
`specification/03-requirements.md` restate both for an installed workbench: it uses UMFPACK, as NGSolve's wheel
provides it, or scipy SuperLU; the core stays BSD-3 and depends on no UMFPACK of its own; the workbench defaults to
NGSolve's UMFPACK, SuperLU selectable; and `nanopnp --env` states the GPL-2+ obligation. `nanopnp --env` does not
state it yet, so the NOTE says it SHALL.

### REV-142: FR-38 drops the charge and radius edits of the charge-level mutator

§8.2.17 S4 rules a charge-level mutation in which "a residue's protonation, charge or radius is edited at stage 7's
PQR step". FR-38, as WP5.01 wrote it, and the design document's Charge edit tool offered only the protonation state,
and no ruling recorded the cut. Found by `/np-ship`'s review of WP5.01 (`docs/code_reviews/CODE_REVIEW_016.md`).

**Fixed** (§8.2.19 U6): FR-38 and the Charge edit row restore the charge and radius edits, as S4 rules.

### REV-143: The light theme's control edge is under 3:1 on a selected row

`docs/design/tokens.css` gives `--control-edge` (`#868c99`) 3.4:1 on `--panel` and 3.2:1 on `--bg`, but an input in
a selected row sits on `--sel` (`#ece7ff`), where the edge is 2.80:1, under WCAG 2.2 1.4.11's 3:1 for a control's
boundary. The dark theme's edge is 3.0:1 on its `--sel`. `/np-gui render` measures text contrast only (REV-138), so
the rendered rounds did not see it. Found by `/np-ship`'s review of WP5.01 (`docs/code_reviews/CODE_REVIEW_016.md`).

**Ruled** (§8.2.19 U7): owned by WP5.02, with REV-138's non-text measure: the token is darkened (`#7c8290` gives
3.2:1 on `--sel`) and the pages rendered again there.

**Fixed** (§8.2.19 U7, 2 November 2026, in WP5.02): the token `--control-edge` is `#7c8290` in
`docs/design/tokens.css` (3.2:1 on `--sel`), and the pages are rendered again. The study's mockups show no finding at
the control edge; REV-176 records the rest.

### REV-144: Case.cylinder takes a charge field, not a uniform wall surface charge

The author's notes for WP54 (`docs/plans/sessions/notebooks-review-for-wp54.md`, Area A) give `Case.cylinder` a
`surface_charge_C_m2` argument. The case schema has no surface charge: a fixed charge reaches a case only as a field
under `inputs.charge` (`nanopnp/field/v0.5`, whose forms are `uniform`, `gaussian_ring` and `slab`), or deposited
from a structure. §8.2.20 V3 keeps the schema unchanged, so `Case.cylinder` takes a field file (`charge=`) instead,
and the cylinder notebooks use the Gaussian rings of examples 02 and 03. Found while WP54 was planned.

**Ruled** (§8.2.20 V3): deferred to the package that next changes the case schema, which decides whether a uniform
wall charge is a boundary condition or a field form.

**Ruled** (§8.2.22 X3): a boundary condition, `boundary_conditions.wall_charge_C_m2` beside `geometry.pore`, a surface term of the one weak form (PHY-09's NOTE), checked by VER-77; `Case.cylinder` takes it. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): `Case.cylinder` takes `wall_charge_C_m2`, a uniform surface charge on the lumen wall as a boundary condition (VER-77).

### REV-145: No case builders by section before Phase 5

The author's notes for WP54 name builders by section, `with_density` and `with_numerics`, beside the leaf edits of
`Case.with_`. §8.2.20 V3 defers them: WP54 adds the typed factories and keeps `with_` for edits. They bear on
`MOD-11`'s `with_section` (§8.2.8 H2), which the user-testing sessions inform.

**Ruled** (§8.2.20 V3): deferred to Phase 5, with `MOD-11`.

**Ruled** (§8.2.21 W7, after the user-testing sessions, UT-10): answered in WP57, which gives `Case` section edits
and a mapping form for a path that names more than one field. V3's deferral is spent.

**Ruled** (§8.2.23 Y1, Y2, superseding W7): a `Case` is built from the public typed blocks of `nanopnp.case`, and
`with_` takes a whole block, as a typed block or a mapping, creating an absent one. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): A case is built from the typed blocks of `nanopnp.case` and edited by copy through `Case.with_`; no builder by section is added.

### REV-146: The cylinder's default wall size is coarser than NUM-30's first layer

`nanopnp mesh cylinder` sizes the pore wall at 0.35 nm by default, and examples 02 and 03 solve on that
mesh. `Case.cylinder` (WP54) takes the same default, so a notebook's cylinder inherits it. NUM-30 asks for a
first wall layer of `λ_D/5`: 0.19 nm at 0.1 M, 0.06 nm at 1 M. Nothing flags it: the coarse-wall warning
covers a generated stage-6 mesh, and the deviation list compares switches, not sizes. WP54's mesh figure
marks `λ_D/5` beside the wall, so the gap shows.

**Question for the author:** should `Case.cylinder` size the wall from the case's Debye length, at the cost
of its parity with examples 02 and 03 and their VER-62 golden?

**Ruled** (§8.2.20 V9): both. The fixed 0.35 nm stays the default, keeping the examples' mesh and golden, and
`Case.cylinder(wall_h_nm="debye")` sizes the wall at `λ_D/5` of the case's salt; notebook 05 offers both
([WP54 plan](../plans/phase-4/wp54-notebooks-and-figures-revised.md)).

### REV-147: The lumen window is fixed, not read from the region

`plot.data.LUMEN_NM` is r ≤ 5 nm, |z| ≤ 10 nm about z = 0. The mesh figure's close-up and the u_z panel's
streamlines use it for every pore (WP54, D3 and D5), so a pore whose lumen reaches past either bound, or is
not centred on z = 0, is cut off. The window could be read from the stage-5 region record: the pore's axial
extent and its largest lumen radius. Found by the physics review of WP54 items 6 and 7; the notebooks offer
a window selector meanwhile.

**Ruled** (§8.2.20 V16): fixed. The window is read from the mesh's `wall` boundary, 2.5 lumen radii out and two
radii past its ends, the lumen radius being the wall's point nearest the axis in each 1 nm slice (the second review
found that a protein's outer face in the reservoir had widened it to 14 by 24 nm on 2WCD); the fixed window is the
fallback for a mesh with no such boundary.

### REV-148: A concentration panel's bulk is the case's salt for every species

`plot_field(..., relative_to_M=)` draws `log₁₀(c / c_bulk)` with one `c_bulk`, the case's concentration
in mol/m³ for every species. That matches the solver as it stands (every species' Dirichlet value is the
case's concentration; `core/scaling.py`), so it is right for the validated 1:1 model. A salt that is not
1:1, or a bulk that differs between cis and trans, would read 0 in a reservoir it does not fill and hide
it. Found by the physics review of WP54 items 6 and 7.

**Ruled** (§8.2.20 V16): fixed. A concentration is drawn against `SolutionFields.bulk_mol_m3`, the value the
solve imposed on cis and trans for that species, read from the model's scales.

### REV-149: Notebook 01 prepares a structure but does not change its residues

Notebook 01's preparation form chooses the chains, the cis end, the residue range and the centroid
height, and hands them to `orient_pore`. It cannot change a residue (a point mutation, a removed loop),
which the author would like a later stage to offer. Deferred by §8.2.20 V13, at WP54's third checkpoint.

### REV-150: `wall_h_nm="debye"` is not capped at NUM-30's 0.05 nm ceiling

`Case.cylinder(wall_h_nm="debye")` (§8.2.20 V9) sizes the wall at `λ_D/5` of the case's salt at `ε_r,f0`, with
no ceiling: 0.19 nm at 0.1 M. The NOTE on NUM-30 resolves a generated mesh's first layer as
`min(0.05 nm, λ_D/5)`, because a layer coarser than the ion wall function's decay length, 1/6.2 = 0.161 nm,
under-resolves it. The option is opt-in and the wall size is a case value, but notebook 05 describes it as
NUM-30's wall, and at 0.1 M it is coarser than that NOTE allows. The solve it gives (G = 1.21 nS against
1.20 nS for 0.35 nm) hides the difference. Found by the `physics-reviewer` pass of `/np-ship wp 54`. The
test `test_cylinder_debye_wall_is_stage_6s_lambda_d_over_5` compares with the mesh figure's `λ_D/5` marker,
which is uncapped, not with stage 6's wall.

**Ruled** (§8.2.20 V14): `"debye"` applies the same `min(0.05 nm, λ_D/5)`, by the helper stage 6 uses
(`mesh.sizing.debye_wall_nm`). Fixed.

### REV-151: `orient_pore` centres laterally on the registration residues, not on the pore axis

`orient_pore` fits the axis through the mean of the selected C-α atoms but rotates and translates about the
centroid of the registration residues. For a full ring these coincide. If a chain lacks some of the
registration residues, the structure shifts sideways and the pore axis lies parallel to z but off r = 0, so
`symmetry.axis: z` can refuse it. Stage 1 refits the axis, so the solve is probably unaffected. Fixing it
changes the prepared 2WCD bytes and the goldens of examples 06 and 07, so it needs the author's ruling.
Found by the `/np-ship wp 54` review and the `physics-reviewer` pass.

**Ruled** (§8.2.20 V15): deferred to its own package. Meanwhile `orient_pore` logs a warning where the
registration centroid is more than 0.1 nm off the estimated axis, and its docstring states the assumption.

### REV-152: WP54 review items: cache key, restores, duplicated helpers, edge cases

Found by the `/np-ship wp 54` review ([CODE_REVIEW_017](../code_reviews/CODE_REVIEW_017.md)) and the
`physics-reviewer` pass.

**Ruled** (§8.2.20 V17): all fixed in WP54, as below.

- **Cylinder mesh cache key.** `Case.cylinder` names its cached mesh by its geometry numbers alone, so a mesher
  fix or a tighter quality gate silently reuses the old file in `meshes/`. The key needs a mesher identity that
  is cheap to read.
- **Second restore.** `run.figure("solve")` and `run.fields` each restore the solved state, and `data.sampled`
  rebuilds the whole-mesh triangulation on each call, against V4's "no second restore". It needs a cache keyed by
  the artefact hash or a change to `draw`'s signature.
- **Duplicated Debye length.** `Case._debye_wall_nm` re-derives what `mesh.sizing` computes; both assume a 1:1 salt
  (REV-148), so a fix to one does not reach the other. The mesh is needed before the document exists.
- **Duplicated notebook cells.** The preparation block sits in notebooks 01, 02 and 06 and the field-view cells in
  03, 05 and 06; D6 forbids importing a shared module. A library helper is a design choice. The prepared file's
  key ignores the source entry and `orient_pore`'s version, and a call that dies mid-write leaves a truncated
  `prepared.pdb` that the existence check accepts.
- **Failed sweep points.** `plot.data.cis_referenced_bias_V` infers the ground side from successful points at
  non-zero bias; if there is none, a failed point is marked at the assigned bias, with the wrong sign under
  `ground: trans`.
- **Forces in the quantities table.** `QOI_UNITS` has no `_N` entry, so analyte forces show in N with no unit
  column.
- **The sweep directory digest.** `sweep()` names its directory by its own digest, not `plan.hash`, so
  `nanopnp sweep plan` on the `sweep.yaml` it wrote names another directory.
- **Cutline midside test.** The two cutline tests evaluate at nodes or on a linear field, so a swapped midside
  column would pass; asserting positive sub-triangle areas would close it.

Fixed as follows: the key carries `mesh.cylinder.mesher_identity`; `post.export.solution_fields` keeps the last two
restores by artefact hash and `plot.data.field_triangulation` the last four triangulations; `Case.cylinder` takes
its Debye length from `mesh.sizing`; the notebooks share `structure.prepared_pore`, `plot.data.field_menu` and
`default_potential_range_mV`, and the marimo cells that draw them stay per notebook (D6); a failed sweep point
whose side of the ground is unknown is left off; `QOI_UNITS` gains `_N` in pN; `sweep()` names its directory by
`plan.hash`; the cutline test checks the four sub-triangles' areas.

### REV-153: Latent gaps the second WP54 review left: the bulk's source, the Debye length twice, two hand-kept lists

Found by the second `/np-ship wp 54` review ([CODE_REVIEW_018](../code_reviews/CODE_REVIEW_018.md)) of `96181c2` and
`86d5b46`. None changes a number today; each is a coupling a later change could break silently.

- **The bulk is a constant.** `SolutionFields.bulk_mol_m3` is the concentration scale times
  `post.export.DIRICHLET_BULK = 1.0`, the default of `CoupledModel.solve`'s `concentration_values`. The pipeline
  passes no `concentration_values` (a solve-only keyword, not recorded), so every species' bulk is that value and
  the field panels read it right; a pipeline path that imposes another bulk would need the solve to record it.
- **The Debye length twice.** `Case._debye_wall_nm` reads the permittivity and temperature from the parameter file
  as `mesh.sizing.case_debye_length_nm` reads them from the resolved case; the cap and the ionic strength are
  shared (`debye_wall_nm`, `ionic_strength_of_M`). The factory needs the wall before a document exists, and
  `test_cylinder_debye_wall_is_num30s_first_layer_with_its_ceiling` pins the two equal at three concentrations.
- **Two hand-kept source lists.** `mesh.cylinder.mesher_identity` and `structure.prepared_pore`'s digest name the
  files that decide their output. The mesher's list now holds `geometry/tolerance.py`; the digest holds
  `orient.py` alone and not `structure/read.py`, so a change to the reader leaves a prepared file in use.
  Widening the digest renames every prepared file.
- **The triangulation cache.** `plot.data.field_triangulation` keeps four triangulations by array identity, in a
  module list; list operations are atomic under the GIL, so a shell with worker threads cannot corrupt it, but the
  arrays stay alive for the process. The restore cache in `post.export` takes a lock.

Recommendation: leave all four. Each is a few lines against a failure no current caller reaches; the Debye length
is covered by a test.

**Ruled** (§8.2.22 X6): the four couplings are fixed in WP57, against the recommendation to leave them.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): The bulk is one constant, `physics.models.DIRICHLET_BULK`, shared with `post/export.py`; the Debye length is read once (the `"debye"` wall is gone); `prepared_pore`'s digest reads `structure/read.py` as well as `orient.py`, and the mesher's list goes with `mesh/cylinder.py`; the triangulation cache holds weak references.

### REV-154: NUM-34's refusal names a setting that a supplied mesh ignores

Found while running user-testing session 03 (WP55, [plan](../plans/phase-4/wp55-user-testing-protocol.md)) as a dry run; it
is the program's, so the session is not rewritten around it (§8.2.7 G7, D6).

`nanopnp run` of a case that reads a mesh file with a 1.0 nm wall exits 4 on the wall-distance gate, and the message
ends "refine the mesh at the wall (`numerics.mesh.wall_h_nm`)". That case field sizes a mesh the program generates
(stage 6); a case that supplies `inputs.mesh.path` never reads it, so a user who edits the setting changes nothing,
and the mesh is refined where it was made (`nanopnp mesh cylinder --wall-h-nm`, or the mesher the file came from).
The gate is in `numerics/gates.py`, which does not know where the mesh came from.

Recommendation: let the pipeline's caller add the supplied-mesh sentence, or have the gate name both routes. Neither
is in this package (no `src/` change); the author rules.

**Ruled** (§8.2.21 W5): accepted, for WP56. The pipeline hands the gate its remedy from where the mesh came from,
and QR-12's NOTE on the remedy states the rule for every gate.

**Fixed** (WP56, [plan](../plans/phase-4/wp56-command-line-read-by-a-person.md)): `solve/state.py:wall_distance_remedy` gives
the gate `numerics.mesh.wall_h_nm` for a generated mesh, and the supplied file with `nanopnp mesh cylinder
--wall-h-nm` otherwise (`test_num34_refusal_names_a_setting_the_run_reads`).

### REV-155: WP55 review items the author rules on: the rectification claim's source, session 04's variation, a duplicated parser

Left by the review of WP55 ([CODE_REVIEW_019](../code_reviews/CODE_REVIEW_019.md)); each needs the author or a
`src/` change that WP55 rules out.

- **The rectification sentence has no marker.** `knowledge/02-electrokinetics-background/07-ionic-current-rectification.md`
  now says rectification needs an axial asymmetry of the geometry or of the fixed charge. Its only support is
  session 05's dry run (0.91 at 50 mV, [plan Outcome](../plans/phase-4/wp55-user-testing-protocol.md)); no test in scope
  asserts it, so it carries neither `[tested]` nor `[verified]` with a source. It needs a literature source from the
  author, or a Tier 2 case that is in the test scope.
- **Session 04's "Then try" variation.** Editing `selectivity.py` alone to read `solve` fails: the notebook registers
  the stage with `inputs=('case','qoi')`, and the `not in walk_order()` guard keeps the registration and the cached
  module until the kernel restarts. This may be the friction the session exists to expose; if the author rules it
  unintended, the README names the registration cell.
- **The tagged-block grammar lives twice.** `tests/tier2/test_user_testing_sessions.py` parses console fences beside
  `validation/examples.py`; the example READMEs get no untagged-command check. A helper next to `tagged_commands`
  serves both and is a `src/` change.

Recommendation: leave the variation until the sessions; source or test the sentence in the documentation increment;
move the helper with the next change to `validation/examples.py`.

**Ruled in part** (§8.2.21 W7): session 04's variation goes to WP57, whose stage of one's own is registered by a
public call; the other two items stay open.

**Ruled** (§8.2.22 X6, X8): the rectification sentence is softened to session 05's observation, with no general claim; the tagged-block parser becomes one helper for the example and session checks. WP57.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): `validation/examples.py:untagged_commands` serves the session and the example tests; the rectification sentence no longer asserts that a fixed-charge asymmetry alone rectifies; session 04's variation re-registers an edited function under the same name.

### REV-156: A 16 562-element cylinder takes minutes to solve (UT-09)

Found in user-testing session 03 (UT-09). `nanopnp mesh cylinder --maxh-nm 0.175` gives 16 562 elements, and the
run of its case had not finished after five minutes. WP49's table gives 4.4 s for one serial UMFPACK factorisation
at 1.43 × 10⁵ DOF (§6.6), and the NUM-18 ladder of that case takes 15 rungs and some 35 to 50 Newton steps, each
factorising again (REV-60), so the time is about what the measured parts predict: a cost, not a defect.

**Ruled** (§8.2.21 W8): deferred to Phase 6, with REV-60 (§8.2.9 I3), its fix to follow measurement against the
registered thresholds (§8.2.12 M2). WP56 measures the time of each rung and the factorisation's share on that mesh
and writes them here; its progress report shows each rung as it is solved.

**Measured** (WP56, [plan](../plans/phase-4/wp56-command-line-read-by-a-person.md), item 9's Outcome): the mesh of
`--maxh-nm 0.175` has 16 444 elements and 8 404 vertices; session 03's case (validated ePNP-NS, stabilisation
`none`) takes 761 s on a 4-core container, 754 s in the solve, 60 Newton steps over 15 rungs. The five bias rungs
take 8 to 10 s each and `6-flow` 23 s; the six `epnp-ns` rungs take 88 to 120 s each, at the same five steps. Of
the 761 s, Jacobian assembly (`AssembleLinearization`) is 473 s (62 %), `UmfpackSolver.solve` 184 s (24 %) and the
residual 74 s (10 %). The premise above, that the factorisation is the cost, does not hold on this mesh: REV-60's
symbolic reuse would save at most a quarter. Assembly runs on one thread (no `src/` file enters NGSolve's
`TaskManager`), and the corrected model's coefficients are what make each step 13 times dearer.

**Answered** (§8.2.24 Z6, 31 October 2026): the Phase 6 fix builds the equations first. The assembly is the larger
share and is this project's own weak forms and quadrature, so a threaded assembly and the cost of the correction
coefficients per step can be measured and cut against §8.2.12 M2's thresholds without touching the linear solver.
REV-60's factorisation reuse follows it. `/np-plan phase 6` reads this row.


### REV-157: WP56 review items left open: the last rung's time, two readers of a run directory, the manifest read twice

Left by the review of WP56 ([CODE_REVIEW_020](../code_reviews/CODE_REVIEW_020.md)). Each item needs a change that WP56
did not plan.

- **The last rung's time on stderr includes the solve's work after the ladder.** `cli/__init__.py`'s `_Progress`
  closes a rung only when the next rung or stage starts. The top rung's printed seconds therefore include the Péclet
  measurement and the write of the state to the store, and they disagree with the manifest's rung `seconds`, which
  REV-156's measurement reads. A fix is an end-of-rung call on `core.stages.SolveHook`, which `gui/solver.py`'s
  `QueueSolve` also implements.
- **Two readers of a run directory remain.** `validation/runs.py` reads `run.json` with its own `_record` and
  resolves the store in `reopen`, beside `pipeline.run.read_run` and `open_run`. Moving `reopen` onto `read_run`
  would also bring it the manifest-hash and case-text checks.
- **`inspect` of a run reads the manifest twice**, once raw and once through `read_run`, and `Manifest.hash` is
  recomputed on every `document()` call. The cost is small, kilobytes per call.
- **`solve/state.py:wall_distance_remedy` keeps a `None` branch that cannot be reached.** `generates_mesh` is
  `resolved.mesh is None`, so the else branch always has a supplied mesh.

Recommendation: add the end-of-rung hook with WP57's `Case.run` hooks (§8.2.21 W4); move `reopen` onto `read_run`
with the next change to `validation/runs.py`; take the last two items with whatever next touches those lines.

**Ruled** (§8.2.22 X6): all four items go to WP57; the end-of-rung call goes with `Case.run`'s hooks.

**Fixed** (WP57, [plan](../plans/phase-4/wp57-idealised-pore-and-python-interface.md)): `SolveHook.rung_solved` gives a rung's seconds, which the progress line prints; `validation/runs.py:reopen` reads through `read_run`; `inspect` reads the manifest once and `Manifest.hash` is cached; `wall_distance_remedy` has no unreachable branch.


### REV-158: A correction file named by path puts its absolute path in the stage-8 and stage-10 keys

Raised by the review of WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`pipeline/case.py` absolutises `electrolyte.parameters` before it reaches the electrolyte's
provenance, so the absolute path lands in `MaterialsArtefact.parameters["electrolyte"]` and in
`ResolvedCase.solve_provenance["electrolyte"]`. A case copied to `/a` and `/b` with a byte-identical
correction file beside each keys its materials and solve artefacts differently: two artefacts exist
for one calculation, nothing is shared between two checkouts of the same work, and artefact identity
stops being a function of content — although the file's `sha256` is already in the manifest's
`inputs`, which is what FR-25 needs to reconstruct the run.

The same is true of the other paths a case names, so this is not special to corrections; the
difference is that corrections were readable by name before this package and the name keyed the
artefact.

Recommendation: key the artefact by the correction file's content hash and keep the path in the
manifest's `inputs` alone, where it already is. That is a change to the artefact-key contract, not a
local edit, so it is the author's to rule.

**Question for the author:** should a file a case names key an artefact by its content rather than by
its path, so the same calculation in two folders shares one artefact? This is the other half of the
"read every file beside the case file" decision the package's In brief puts to you.

**Ruled by the author (31 October 2026): yes, by content.** `Electrolyte.identity` is
:attr:`provenance` with every file named by its file name alone (`core/paths.correction_identity`),
and it is what the stage-8 key and `ResolvedCase.solve_provenance` carry; `provenance`, which the
manifest's Materials group records, keeps the path. The `corrections:<name>` input hashes are keyed
by identity too, and a case naming two correction files of one file name by different paths is
refused rather than keyed as though it named one. §5.3.1's NOTE on a correction file outside the
package carries the rule; `tests/tier1/test_corrections.py` keys one case beside two copies of its
files and gets one artefact. Resolved with REV-159 and REV-161.

### REV-159: Three in-memory routes read a relative path against the working directory, not beside the case

Raised by the review of WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

A case read from a file now resolves its relative input paths beside that file (§5.3.1's NOTE,
§8.2.23 D12). Three routes do not, so one string means two different files depending on how the case
reaches the walk:

- **A sweep member.** `api/sweep.py:313` walks with `base=None`, although `plan.base_path.parent` is
  at hand. `nanopnp run examples/03-iv-sweep/charged.case.yaml` from the repository root finds
  `cis-ring.field.yaml`; `nanopnp sweep run` on the plan built from the same case does not.
- **An edited case.** `api/case.py:145` applies the caller's edits after the absolutisation, so
  `Case.load(...).with_(**{"inputs.charge.path": "ring.field.yaml"})` leaves the edited path relative
  while every other path of the same case is absolute, and the copy keeps no base to read it against.
- **A factory-built case.** `Case.cylinder` and `Case.from_structure` absolutise `charge` and
  `source` but leave a path-named `parameters` as given, so a factory case is half portable and
  `plan_sweep` refuses it outright for naming a relative correction path.

`CHANGELOG.md` states the sweep behaviour deliberately ("a case held in memory (a sweep member, a
window document) reads against the working directory"), so the first item is documented intent and
changing it is a decision, not a fix. The second and third read as oversights of the same change.

Recommendation: give a sweep member `plan.base_path.parent`; absolutise after the caller's edits, not
before; and treat `parameters` as `charge` and `source` are treated. All three make one rule of what
is now three.

**Question for the author:** should a case held in memory carry the base of the file it came from, so
that a sweep member, an edited copy and a factory case all read a relative path the way the case file
does?

**Ruled by the author (31 October 2026): yes, it carries the base.** `Case.with_` applies the
caller's edits first and rebases afterwards, and the copy keeps `_base`, so a path an edit names is
read beside the case like every other. A sweep member walks with `plan.base_path.parent`, and so do
the parent-artefact lookup that decides whether it starts warm and `build_plan`'s own resolve of
every point — without those two the member would have read one base and been keyed against another,
and no member would have started warm. `Case.cylinder` and `Case.from_structure` resolve a
path-named `parameters` as they already resolved `charge` and `source`. Only a case that never had a
file still reads against the working directory. §5.3.1's NOTE on a relative path carries the rule
and `CHANGELOG.md`'s statement of the old behaviour is corrected.

### REV-160: StageInputs.options is unreachable, so three QoI settings and their deviation are dead

Raised by the review of WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`run_document`'s `options` parameter and `_Walk.options` were deleted with `run_case`, but
`StageInputs.options` and its three readers in `post/stage.py` were kept. `QoIStage._prepare` still
reads `inputs.options.get("check_routes", True)`, `_shell(data, inputs.options)` and
`_band(data, inputs.options)`, and `QoIStage.deviations` reports the `check_routes` deviation from the
same mapping. `_Walk.inputs` now builds `StageInputs(resolved=..., upstream=...)` only, so `options`
is permanently `{}`: the force-route skip, the custom indicator band and the custom extension shell
cannot be set from the command line, the `Session` or the sweep runner, and the `ContributedDeviation`
they feed can never be recorded.

Nothing gives a wrong answer — the defaults are the validated ones — but a capability and a
manifest deviation are silently gone, and dead configuration in a QoI stage is the kind of thing a
later reader will wire up by guessing.

Recommendation: decide which it is. Either the three settings are configurable, in which case the
plumbing is restored and a case key or a `Session.run` argument reaches them; or they are not, in
which case `StageInputs.options`, the three readers and the deviation go, and §5.3.2's deviation list
loses `check_routes`.

**Question for the author:** should `check_routes`, the indicator band and the extension shell stay
configurable, or be fixed at their validated defaults and the dead plumbing removed?

**Ruled by the author (31 October 2026): the dead plumbing goes, but not the field.** On
inspection the premise was only half right. `StageInputs.options` is unreachable from the walk, as
above, but it is not unused: three Tier 1 tests set it by constructing `StageInputs` directly, which
is what FR-27's independently-invocable stage is for, and one of them is physics evidence —
`test_fr23_the_current_does_not_depend_on_where_the_band_sits` (VER-11) moves `indicator_band_nm` to
three half-widths and bounds the shift in the current. Deleting the field would have deleted that
benchmark's only lever, so the field stays, documented as a setting a direct caller reads and the
walk never sets.

What went is what claimed a capability no caller had: the `check_routes` option, `_Prepared`'s field
for it, the five sites that threaded it, and `QoIStage.deviations`. The NUM-26 cross-check is now
always run, which is what every walk has always done; `QoIArtefact` still records `check_routes` in
its key, as the constant it now is, so the key of every artefact extracted with the check on is the
one it has always had. The specification needed no edit: neither §5.3.2 nor §5.3.3 ever named these
three as configurable, and the stage-contributed deviation channel itself stays, used by stages 6
and 7. `tests/tier1/test_qoi_stage.py`'s deviation test is replaced by one asserting the check runs;
the manifest's contributed-deviation channel keeps its cover in `tests/tier1/test_manifest.py`.

### REV-161: The manifest records a null hash for a correction file it cannot find

Raised by the review of WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`io/manifest.py:153` resolves each correction file with `correction_source(each)` and no base, and
records `None` when the lookup raises. An `Electrolyte` built from a relative path by any route that
does not go through `resolve`, which absolutises, therefore reaches `materials_group` with a bare
name: if the file is not in the working directory the `FileNotFoundError` is swallowed and the
manifest records `parameter_file_hashes[name] = None`; if a *different* file of that name is there,
the manifest records that file's hash. Either way the manifest cannot reconstruct the run, which is
what FR-25 requires of it, and nothing refuses.

Not reachable from a case file today, because `resolve` absolutises first. It is reachable from the
public `Electrolyte`, and it is the manifest — the one record whose job is to be trustworthy.

Recommendation: pass the base through to `materials_group`, and refuse rather than record a null
hash: a manifest that cannot name the file it read is not a manifest. Take it with REV-158, which
decides what the key is made of.

**Resolved (31 October 2026), with REV-158.** `materials_group` refuses, naming the file and what to
do about it, rather than recording `None` or another file's hash — the same answer stage 8 has always
given for the same file, so the manifest and the stage now agree. No base is threaded: every route a
walk takes resolves the path before the electrolyte is built, and the one route that does not — the
public `Electrolyte` given a bare relative name — is refused by stage 8 before a manifest is
assembled at all. §5.3.1's NOTE on a correction file outside the package carries the refusal.

### REV-162: The wall surface charge's sign is written at four sites; Grahame's sigma and the sigma scale twice each

Raised by the `physics-reviewer` pass on WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

PHY-09's NOTE has the surface term added once. Its measure and `r` weight are shared through one
helper, and the boundary guard is now shared too, but its **sign** is written at four sites:
`physics/models.py:891` (coupled), `:1344` (PB), `:1512` (`poisson`), and `physics/pb.py:149`, where
it is a `sign` parameter that is `+1.0` in the linear branch and `-1.0` in the nonlinear one. Two of
the four are covered by a test — the coupled model by VER-77 (b), `pb` by VER-77 (a) and VER-31 —
and `PoissonModel`'s by none. A flipped sign at the uncovered site diverges or gives the mirror
answer with no other symptom.

Two oracles are also written twice and agree: Grahame's σ at `tests/tier2/test_stern_layer.py:37`
and `tests/tier2/test_wall_surface_charge.py:28`; and the surface-charge scale at
`core/scaling.py:131` (`ε V_T / a`) and `physics/pb.py:41` (`dimensionless_surface_charge`, the same
number by another route, read only by `test_stern_layer.py`). This package moved the `pb` term onto
the shared measure helper and left the second scale in place.

Recommendation: put the signed term behind one helper, so the sign is written once and every model
inherits it; drop `dimensionless_surface_charge` in favour of `Scales`; and let the two tests share
one Grahame expression. None of it moves a number. Take it with whatever next touches the surface
term.

**Resolved (31 October 2026).** `physics/poisson.surface_charge_term` takes `side`, `"load"` or
`"residual"`, and is the only place the sign is written: Poisson's boundary term stands on the
right-hand side, so it enters a linear form as written and a residual negated. The coupled, `pb` and
`poisson` models and both branches of `solve_pb_recorded` go through it, so `PoissonModel`'s sign,
which no test covered, is now the same expression VER-77 (b) and VER-31 exercise.
`dimensionless_surface_charge` is gone; `test_stern_layer.py` divides by
`Scales.surface_charge_C_m2`, which is the number it computed by the other route, and the two tests
share one Grahame expression, the `grahame_sigma_C_m2` fixture of `tests/tier2/conftest.py`. No
number moved: the Gauss balance, Grahame's zeta on the slab and the five Stern-layer assertions all
hold unchanged.

### REV-163: check_force_surface refuses a legitimate body straddling the lumen and reservoir seam

Raised by the `physics-reviewer` pass on WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`post/forces.py:check_force_surface` implements NUM-29's NOTE as written: it refuses a force surface
that does not lie between one pair of materials, because the traction normal is oriented by one pair
and part of the force would otherwise be negated. On a mesh this codebase builds it cannot
false-positive — `geometry/analyte.py:239` already refuses a body crossing a pore mouth. On a
**supplied** mesh it refuses an on-axis body straddling the lumen and reservoir seam, which is
physically legitimate: `electrolyte`, `cis` and `trans` are three names for one fluid, as the
codebase's own `ELECTROLYTE_DOMAINS` says, and `_oriented_normal` orients by a centroid star-shape
test that needs no single material pair. The gate is stricter than the failure it names.

Recommendation: compare the fluid domains by `ELECTROLYTE_DOMAINS` rather than by name, so a surface
meeting two names of one fluid passes and a surface meeting a fluid and a solid still refuses. That
changes what NUM-29's NOTE refuses, so it is an amendment, not a fix.

**Resolved (31 October 2026) as an amendment.** `check_force_surface` maps every name matching
`ELECTROLYTE_DOMAINS` to one material before it counts the pairs, after the side beyond the domain
has been settled — the order matters, or a fluid on both sides would read as an outer boundary. A
body straddling the lumen and a reservoir now passes and reports `("analyte", "electrolyte")`; a
surface meeting a fluid and a solid still refuses. NUM-29's NOTE carries the amendment in the same
commit, and `tests/tier1/test_forces.py`'s gate test now asserts both halves: the straddling body
passes, a body meeting `membrane` is refused.

### REV-164: default_ladder accepts a zeta-Dirichlet wall and a sigma_s wall together with no diagnostic

Raised by the `physics-reviewer` pass on WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`solve/continuation.py:605` puts `wall` into the Dirichlet set for the two PB rungs when
`wall_potential_V != 0`, while `:671` ramps `surface_charge_C_m2` on the same boundary from stage 4.
Nothing refuses both: a ladder given both would solve a ζ-Dirichlet wall and a σ_s wall in one
continuation, two wall models for one wall, with no diagnostic. Unreachable from a case file —
`io/case.py` has no `wall_potential_V` key and `solve/state.py` never passes one — so it is reachable
only by calling `default_ladder` directly.

Correct and checked, beside it: the PB rungs carry no surface charge, so a charged case warm-starts
from the uncharged PB field and stage 4 ramps the charge in, the same treatment the fixed charge
gets.

Recommendation: refuse the two together in `default_ladder`, naming both settings. A numerical gate,
so it takes a test when it is done.

**Resolved (31 October 2026).** `default_ladder` refuses `wall_potential_V` and
`surface_charge_C_m2` together, naming both values and the boundary, beside the refusal of the two
fixed charges that is its precedent. `tests/tier1/test_continuation.py` asserts the refusal and that
either setting alone still builds a ladder.

### REV-165: The Gauss-balance test's own quadrature error is not bounded against the physics bound it resolves

Raised by the `physics-reviewer` pass on WP57 ([CODE_REVIEW_021](../code_reviews/CODE_REVIEW_021.md)).

`tests/tier2/test_wall_surface_charge.py`'s Gauss-balance test asserts `rel=1e-3`, which is VER-77's
and QR-03's number, not a guessed one, and its geometry satisfies the clause's conditions — radius
5 λ, thickness 10 R, planes 10 λ from the mouths, a coaxial leakage estimate of 2.2 × 10⁻⁵ against
the clause's 1 × 10⁻⁴. What is unbounded is the test's **own** quadrature: a 48-node Gauss–Legendre
rule in `r` over a C⁰ piecewise-quadratic field with about 25 elements across the radius, and
Simpson over 17 planes. Neither error is estimated nor compared with the 2.2 × 10⁻⁵ physics bound
the assertion is meant to resolve, so the margin between "the balance holds" and "the quadrature
landed inside 1e-3" is unknown. The assertion is also not keyed to a mesh hash, while
`tests/tier2/data/number_stability.json` shows this walk class deploying different meshes per
platform.

The test does pin the physics it was written for: a flipped sign or a factor of two fails it by a
wide margin. The gap is in knowing how much headroom it has.

Recommendation: measure the two quadrature errors once by refining each rule and record the numbers
in the test's comment, as the other Tier 2 benchmarks do. No tolerance changes.

**Resolved (31 October 2026); no tolerance changed.** Both rules were refined against the other
held fine. The 48-node Gauss-Legendre rule in `r` is worth 8 x 10⁻⁷ relative against 192 nodes and
is settled by 48. Simpson over 17 planes is worth 1.4 x 10⁻⁵ against 129 planes and is the larger of
the two; because the integrand is sampled from a C⁰ piecewise-quadratic field its error does not
fall monotonically with the plane count (1.4 x 10⁻⁵ at 17, 1.2 x 10⁻⁵ at 33, 1 x 10⁻⁷ at 65) but
with where the planes land in the elements. With both rules fine the balance closes to 6 x 10⁻⁶,
the physics leakage this geometry leaves, inside the 1 x 10⁻⁴ of VER-77's conditions. The `rel=1e-3`
assertion therefore resolves a 2 x 10⁻⁵ total discrepancy with a factor of 48 in hand, which is the
headroom that was unknown; the numbers are in the test's comment. The assertion is still not keyed
to a mesh hash, and that margin is why it need not be: a platform deploying another mesh of this
class moves the balance far inside it.

### REV-166: The Copilot hook probes are incomplete

Raised by the implementation of [the Copilot host plan](../plans/sessions/copilot-host.md), built before its
Phase 0 probes ran (§8.2.25 AA6).

**Verified** (app 1.1.34, WSL host, disposable clones, 31 October 2026):

- Both hook sources load at startup and fire pre and post on shell, patch and MCP read calls. Hooks
  added mid-session do not fire.
- Shell: `bash` with `toolName`/`toolArgs`, or `Bash` with an object `tool_input`. Patch:
  `apply_patch`, or `Edit` with a raw patch string, which `format.sh` parses.
- An exit-0 structured denial blocks and shows its reason; exit 2 blocks with a generic reason.
  Claude Code 2.1.314 blocks the same denial with its reason (§8.2.26 AB1), so the inherited
  `COPILOT_CLI` control is resolved: no variable selects the protocol.
- A 40 s denial completes under a 60 s timeout.
- A linked worktree's push is gated on its own stamp, not the primary's.

**Open:** the `write_bash` payload and matcher; the GitHub MCP write-tool names against the deny
matcher; the full 1800 s timeout; `session-start.sh`'s JSON.

**Rule:** run the gate by hand on Copilot until this closes (`.claude/workflow/hosts/copilot.md`,
*Safety hooks*). The stop rule applies if a refusal or timeout is not honoured.

**Procedure:** a disposable clone opened as its own WSL repository, probes installed before startup;
record only tool names, argument types and sentinels.

### REV-167: Six Copilot app behaviours the substitutes assume are unchecked

Raised with REV-166 (§8.2.25 AA6). `.claude/workflow/hosts/copilot.md` gives a substitute for each Claude
Code construct the workflow names; six of them rest on app behaviour no session has checked:

- whether the app's Commit and Push buttons pass `--no-verify`, which would skip `.githooks/pre-push`;
- whether `$ARGUMENTS` is substituted in a skill (`hosts/copilot.md` says what to do when it is not);
- whether `/compact` can be called by hand at a compaction checkpoint;
- whether a coding session has the session-automation tool, the later upgrade of the CI rule (AA3);
- whether `CLAUDE.md`, loaded twice through `AGENTS.md`, can be turned off for Copilot alone;
- how `model:`, `effort:` and `omitClaudeMd` in `.claude/agents/` are treated; `hosts/copilot.md` passes
  `model` and `reasoning_effort` at each call so that the tier holds either way (AA7, AA8).

Recommendation: check each in the same session as REV-166 and write the answer into `hosts/copilot.md`.
Only the first can let an ungated tree through; the rest change how a substitute is worded.

### REV-168: The Copilot host has not been verified live

Raised with REV-166 (§8.2.25 AA6). The plan's *Verification* has a live part in the Copilot app (a
refused ruff violation that runs the gate once, a passing commit, a commit typed into a running
shell refused, the GitHub MCP file tools refused, an unstamped push refused from the agent and from
the Push button, a gated push let through, `format.sh` after an edit, the session-start text), a
regression in Claude Code (a failing commit refused with its reason, an unstamped push refused, the
session-start text and `format.sh`), the sub-agents called through `task`, and a dry run of
`/np-plan wp` and `/np-implement`. None of it has run.

Recommendation: run it after REV-166, on a WSL host, and ship the Copilot host's pull request from
Claude Code with `/np-ship`, as the plan says, which also covers the Claude Code regression.

### REV-169: The Phase-1 reference sweep's base case writes its mesh path against the working directory

Found by WP58 while it revised example 05's README ([plan](../plans/phase-4/wp58-documentation-increment-4.md), item 8).
`docs/sweeps/phase1-reference.case.yaml` names `inputs.mesh.path: docs/sweeps/clya-reference.msh`, and its header
comment says the path resolves against the process working directory and not against the file, so it is written from
the repository root. A relative path is read beside the case file (§5.3.1, the NOTE on a relative path), and
`sweep plan` resolves each member with `beside=base_path.parent` (`src/nanopnp/sweep/plan.py`). By that reading a run of
the sweep looks for `docs/sweeps/docs/sweeps/clya-reference.msh`. The mesh is not checked in, so no gate reads the path and
this was read from the code, not run.

The five `docs/validation/cases/clya-*.case.yaml` files carry the same path and the same header comment, and the comment in
`docs/scripts/capture_gui.py` (line 56) states the same stale rule; they belong to the same fix. `docs/sweeps/README.md` said
the same and now points here.

WP58 changes no case file (D1: a case hash and VER-62's golden stand), and example 05's README no longer asserts either rule.
The fix is an edit of the case file's path to `clya-reference.msh` and of its comment, in a later package that may re-pin a
hash; a tier 1 test that plans the sweep from another directory would be in the test scope only if it guards a mechanism.

**Accepted** (§8.2.27 AC5, 1 November 2026): WP59, the review-fix package before the close, edits the six case files'
path and comment and the comment in `docs/scripts/capture_gui.py`, so the close stays free of case edits.

**Fixed** (WP59, item 6, 1 November 2026): the phase-1 reference case names `clya-reference.msh` and the five
`docs/validation/cases/clya-*.case.yaml` files name `../../sweeps/clya-reference.msh`, each header reading "A relative
`inputs.mesh.path` is read beside this file (section 5.3.1)"; `docs/scripts/capture_gui.py`'s comment is corrected. The
five frozen case identities are unchanged (`0128dd1854ff`, `4db46a9d821b`, `1b48e22b656c`, `0e263b472108`,
`1e26bf4a0c11`).

### REV-170: Five callers pick the stage-5 region's kind

`geometry/region.py` `read_region` returns `RegionRecord | IdealisedRegionRecord`, and five callers outside the Qt
shell branch on the kind: `mesh/generate.py` twice, `mesh/ingest.py`, `plot/data.py` and `cli/__init__.py`. The cylinder
is described twice, by `geometry/pore.py` `CylinderPore` and `mesh/primitives.py` `CylindricalPoreGeometry`, and
`CylinderPore.name_edges` sets an edge's mesh size (`maxh`) inside `geometry/`. Found by the architecture review of
[CODE_REVIEW_024](../code_reviews/CODE_REVIEW_024.md), candidate 1 (verdicts 12 and 13); its claim that the idealised
drawing omits the reservoirs does not hold (verdict 11).

**Accepted** (§8.2.27 AC3, 1 November 2026) for Phase 5's shell packages; `/np-plan amend 5` places it. The fix is one
stage-5 region interface with an adapter per kind, the cylinder's two classes merged into `CylinderPore`, and the wall
sizing moved into `mesh/`. It waits for the browser geometry suite and for the pore-shape sketcher's third kind of
region, which shape the interface better than two kinds do; `plot/data.region_drawing` already gives the shell one
drawing. VER-62's recorded mesh hash must not move, or the move is ruled and re-pinned (G10, I4).

**Placed** (§8.2.28 AD4, 1 November 2026): in the shell package that builds the Continuum suite's Geometry tool, library
step first; the second `/np-plan amend 5` names the package.

**Named** (§8.2.31 AG1, 3 November 2026): WP5.17, the Continuum suite.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): WP5.17, the Continuum suite.

**Design** (§8.2.36 AL22, 8 November 2026): WP5.17's library step takes CODE_REVIEW_036's candidate 3 with its corrections C3.1 and C3.2, which also remove MOD-03's edge from `modularity-layering.yaml`.

### REV-171: The architecture review's unmeasured costs

The architecture review of [CODE_REVIEW_024](../code_reviews/CODE_REVIEW_024.md) names costs and checks that no one has
measured (verdicts 14 to 18): `physics/models.py` builds a second, unassembled PB `BilinearForm` after the solve, from
the same weak-form functions; `NondimensionalCoefficients` builds its symbolic expressions per species for the QoI, and
four `post/` and `physics/` modules repeat a boundary's existence check; the sweep planner loads the correction files
once per point; `geometry/contour.py` `enforce_spacing` is `O(n²)`; `density/union.py` scales the frame coordinates
inside its slab loop; `symmetry/reduce.py` multiplies one harmonic at a time; and `charge/deposit.py` `locate` allocates
a dense bucket grid. Internal arguments (`cell_nm`, `n`, a contour's axes, a zero-length loop) are not checked, though
each comes from a validated field or a caller in the same subpackage. Measured: `Case.with_` costs 1.0 ms per edit and a
`resolve` 1.5 ms. The review's proposal to keep each sweep point's solve key at plan time does not hold: a generated
mesh's key depends on the parent's stage-6 artefact, which exists only after the parent runs (`api/sweep.py`).

**Deferred** (§8.2.27 AC4, 1 November 2026) to Phase 6's speed-up, after the assembly (§8.2.24 Z6): each item is
measured against a registered threshold before it is fixed (§8.2.12 M2), and an argument check is added only where it
guards a public entry.

**Amended** (§8.2.28 AD5, 1 November 2026): the QoI seam, one extraction interface and one boundary-existence check shared
by `physics/distance.py`, `post/indicator.py`, `post/reaction_flux.py` and `post/forces.py`, moves to WP5.06 with
MOD-09's outputs registry. The cost items, the coefficient expressions among them, stay here.

**Done** (WP5.06): the seam part. `numerics/measures.py` holds `has_boundary` and `require_boundary`, which the wall
distance, the indicator, the reaction flux and the force extension call; stage 11 builds one `Extraction` and calls each
selected output. The cost items remain deferred to Phase 6.

### REV-172: A non-finite trial residual at minimum damping is reported before the state gates name its location

`numerics/newton.py` raises `NewtonDivergenceError` on a non-finite trial residual at minimum damping (NUM-16's NOTE;
WP59 D5) before the NUM-17 state gates see the trial state. Before WP59 such a step was forced and a positivity or
packing-fraction violation in it raised `GateViolationError`, naming the field and the location (QR-12, exit code
`EXIT_GATE`); now it raises the divergence, with residual, iteration and damping but no location (`EXIT_CONVERGENCE`).
It matters where log variables overflow `exp` to infinity, a state the packing gate would also refuse. A related case:
a non-finite Newton direction from the linear solve is reported as a non-finite trial residual after the damping cuts,
which points at the residual rather than at the solve. The NOTE asks only for residual, iteration and damping, so the
code meets the text; no recorded solve reaches either path. The options are to run `check_all(state_gates)` on the
trial state before raising, and to check the direction is finite after the linear solve.

Found by the physics review of [CODE_REVIEW_025](../code_reviews/CODE_REVIEW_025.md), 2 November 2026.

**Fixed** (§8.2.29 AE1, AE2, 2 November 2026, in WP59): at minimum damping the state gates are checked on the
non-finite trial before the divergence is raised, and a non-finite direction raises a divergence naming the linear
solve; NUM-16's NOTE says so, and two Tier 1 tests check it.

### REV-173: Plotting a run reads its record twice through the session

`nanopnp plot <run>` calls `Session.read`, then `Session.open`, which reads and checks `run.json`, `manifest.json` and
`case.yaml` again through `open_run`. Because `Session.open` always passes the session's own store, the command line
repeats `open_run`'s rule for choosing the store a record names, so the rule lives in two places. `Session.read` uses
nothing of the session, so `inspect` and `plot` build a throwaway `Session(write=False)` for it; and `Session.check`
reads `case.source.base`, which dumps an edited case to YAML to obtain a directory. Each costs milliseconds; none
changes a result. Removing the double read needs a store argument on `Session.open`, a change to the public interface
that WP59's D3 and IF-01's NOTE fixed.

Found as [CODE_REVIEW_025](../code_reviews/CODE_REVIEW_025.md) findings 3, 7 and 11, 2 November 2026.

**Fixed** (§8.2.29 AE3, 2 November 2026, in WP59): a session given no store opens a run from the store its record
names, so `plot` reads the run once and the store rule lives in `open_run` alone; `Session.read` is a static method.
The dump in `Session.check` is accepted. IF-01's NOTE says so.

### REV-174: The command line names the workbench's server by string

`nanopnp gui` starts the workbench's server, a module of `gui`. `gui` sits above `cli` in the layer order, so an
import would be an upward edge. The command passes the module's name, `nanopnp.gui.web.server`, to
`importlib.import_module` after it checks that the `gui` extra's packages import, and the edge is recorded as a
`string` edge in `modularity-layering.yaml`, as the stage registry's and the exit-code table's are.

Found at WP5.02's item 7, 2 November 2026.

**Fixed** (§8.2.30 AF1, 2 November 2026, in WP5.02): the edge is recorded and named for this finding. The command
imports nothing from `gui` at module scope, so a library install without the extra runs every other command.

### REV-175: pdb2pqr 3.8 is not read, and 3.7.1 pins docutils against the gui extra

The `structure` extra asks for `pdb2pqr>=3.7`. Resolved afresh, `uv add` took 3.8.0, which writes terminal residues
under two names (`GLU`, `NTER`); the PQR reader refuses them, and eighteen Tier 1 tests of VER-57 and VER-60 fail.
The lock holds 3.7.1, the version the tests were written against. 3.7.1 pins `docutils==0.17.1`, and NiceGUI, which
the `gui` extra now carries (§8.2.30 AF4), needs `docutils>=0.19`. `[tool.uv] override-dependencies` lets the lock
hold both; neither package imports the other's use of docutils. A `pip` install of both extras at once cannot take
the override, so it resolves to an older NiceGUI or fails.

Open: the author rules whether the `structure` extra is capped below 3.8 or the reader learns 3.8's terminal names,
and whether `pip install nanopnp[structure,gui]` is supported before 1.0.

**Fixed** (author's ruling, 3 November 2026, in WP5.02): the reader learns 3.8's names. 3.8.0 writes the terminal
patch atoms under `NTER` and `CTER` where 3.7.1 wrote `TER`; `PATCH_RESIDUES` holds all three, and
`test_ver57_pdb2pqr_38_terminal_patches_name_no_residue` reads them. PDB2PQR 3.8.0 does not require `docutils`, so
the `structure` extra asks for `pdb2pqr>=3.8`, the uv override is removed, and a pip-style resolve of
`.[structure,gui]` succeeds. `CHARMM.DAT` is byte-identical in 3.7.1 and 3.8.0, so the transcribed radii hold.

Found at WP5.02's item 7, 2 November 2026.

### REV-176: The design mockups fail the non-text contrast measure

`/np-gui render` measures non-text contrast from WP5.02 (REV-138). Rendered again, the design study's pages
(`docs/design/{concepts,style,choices,mockups}`, 382 shots) show no text, target or page error, and 376 non-text
findings in 54 shots: the colour-bar swatch fills of the diverging map on white (`#f4a582`, `#92c5de`), the
accent focus ring on the near-black 3D canvas (`--focus` on `--canvas-3d`), and the style sheet's `--line` edges.
None of them is the control edge of REV-143, which the new token (`#7c8290`) settles. The pages are WP5.01's
evidence and are not shipped. The shipped screens, rendered by `/np-gui render shell`, report none.

Open: the author rules whether the study's pages are corrected, or left as dated evidence, and the focus ring on
the 3D canvas (a ring of `--focus` that reads at 3:1 on `--canvas-3d`) is decided when the first screen that
draws a focusable control over it is built.

**Fixed** (author's ruling, 3 November 2026, in WP5.02): the study's pages stay as dated evidence of WP5.01 and are
not corrected; the measure applies to the shipped screens, which report none. The focus ring on the 3D canvas is
decided when the first screen that draws a focusable control over it is built.

Found at WP5.02's item 9, 2 November 2026.

### REV-177: The workbench's link failures end the server at startup

`boot_case` shows a refusal (exit 3 or 4) as the `refused` state. `Link.__init__` raises `ValueError` or `KeyError`
for a run with no charge lattice or no protonation artefact (a case with no `pqr` input), and that ends the server
(and the `--dev` reload loop) instead of showing a state.

Open: the author rules whether a case without charge shows as a state of its own, or as a refusal naming the missing
stage. The fix is small once ruled.

**Fixed** (author's ruling, 3 November 2026, in WP5.02): a charge with no structure behind it is a state of its own,
not a refusal and not a fault. A case with no `pqr` at all is refused by the pipeline (exit 3) and already shows as
`refused`; the case that failed was the one that walks to stage 7 with a derived dielectric or a supplied charge
field, which has no protonation artefact or no stored lattice. `Link.from_run` returns None there, `Workbench`
carries a `notice` beside `refusal`, and the Charge screen shows it. The state `uncharged` (the tube with
`dielectric_transition_nm` and no `pqr`) joins `STATES`, so VER-78 loads every screen in it. An artefact that is
present and unreadable still ends the server.
Found by the WP5.02 review (CODE_REVIEW_027, finding 3), 3 November 2026.

### REV-178: The selected-fill measure does not read the strip's pressed item

`shoot.cjs`'s non-text check of a selected fill reads `[aria-selected=true]`; the workbench marks its selected
strip item `aria-pressed=true`. A shot taken with a residue selected leaves that item's fill and edge unmeasured
against 3:1. Widening the selector changes what `/np-gui render` gates on (`--sel` on `--panel` is about 1.2:1).

Open: the author rules whether the selected strip item must reach 3:1 (the token changes) or the measure stays as it is.

**Fixed** (author's ruling, 3 November 2026, in WP5.02): the measure reads the marker, not the fill. WCAG 1.4.11
asks for the state indicator, and the selected strip item carries a 2px `--accent` edge (6.7:1 on `--panel`) and weight
600, as `tokens.css` says a selection always does. `shoot.cjs` now takes every `aria-selected`, `aria-pressed` and
`aria-current` item and passes it when its edge or its fill reaches 3:1; an item with neither is a finding
(`selected, no marker`). No colour changes. Checked on a page of three selected buttons: edge and fill passes, a
fill of 1.2:1 alone and weight alone are flagged. An earlier recommendation here, to darken `--sel`, was withdrawn.
Found by the WP5.02 review (CODE_REVIEW_027, finding 9), 3 November 2026.

### REV-179: `nanopnp gui` has no smoke test and takes no common flags

CLAUDE.md asks each entry point for a thin smoke test. VER-78 launches `python -m nanopnp.gui.web.server`, so
`_gui`'s forwarding of arguments is untested, and the subparser is not built with `_common`, so
`nanopnp gui --traceback` is refused after the subcommand.

Open: the author rules whether the server accepts `--json` and `--traceback`, and the smoke test follows that shape.

**Fixed** (author's ruling, 3 November 2026, in WP5.02): the server has one entry, `serve(case, state, port,
no_browser, dev, as_json)`. `nanopnp gui` is built with the common flags and calls it; `python -m
nanopnp.gui.web.server` (the desktop wrapper's entry, ADR-004) is a shim that parses and calls it. `--json` writes the
ready line as `{"ready": <url>}`; the plain line stays the default, so the wrapper contract does not move. VER-78's
state walk now launches through the command, which is the entry point's smoke test, and one test reads the JSON line.
Found by the WP5.02 review (CODE_REVIEW_027, finding 14), 3 November 2026.

### REV-180: The protonated density is refused under the SWANSON and PEOEPB force fields

Stage 2 takes each atom's radius from the CHARMM set of the §5.3.1 NOTE on `geometry.density`, by residue and atom
name. Under `charge.forcefield: SWANSON` PDB2PQR 3.8 writes AMBER hydrogen names (`H`, `HB3`, `H1`) that the set does
not hold, and on 2WCD residues 18 to 26 fourteen hydrogens resolve to no radius. `PEOEPB` failed on the same fragment.
WP5.03 therefore refuses `geometry.density.atoms: protonated` beside a produced protonation under either force field,
naming both keys, and the case sets `as_loaded` or `CHARMM`.

**Deferred**, owner unassigned: a protonated density under these force fields needs a radius set, or atom aliases,
that holds their names, chosen as an author ruling as the CHARMM set was. Found at WP5.03's plan, 3 November 2026.

### REV-181: Stage 2's header counts frame 0's atoms and reads an element from the first letter of a name

Under `geometry.density.atoms: protonated` the frames of the protonation table differ in atoms where a tautomer or an
acid state differs, yet `atoms.total`, `atoms.by_element` and `hydrogens` in stage 2's header count frame 0 only. The
element of an atom is its name's first letter after any leading digits, which gives `F` for `FE` and `C` for `CL`; the
table has no element column. The density is unaffected; the record understates the ensemble and misnames an ion.

**Open**, found at WP5.03's review: the author rules whether the table carries an element column (a change to the
artefact's schema) or the header lists every frame's counts.

### REV-182: A polar hydrogen's kernel is narrower than the density grid's spacing

The CHARMM radius of a polar hydrogen is 0.2245 Å, so its width at sharpness 0.93 is 0.0209 nm against the default grid
spacing of 0.05 nm. The nearest-node deposit of such an atom is aliased: its term at its nearest node runs from near 0
to 1 with where it sits in the cell. The atom lies about 0.1 nm from its N or O, whose own term there is already about
0.71, so the 0.25 isolevel is not expected to move; WP5.03 did not measure it. The sharpness and the isolevel were set
on a density without these hydrogens.

**Open**, found at WP5.03's review: the author rules whether the polar hydrogens are measured against a finer grid
before the protonated default is used outside the reference cases.

### REV-183: Fractional protonation through a customised PDB2PQR

WP5.04's charge edit changes a residue's net charge by an integer, on its titratable group (§8.2.31 AG9). A partially
(de)protonated state, a group carrying its charge averaged over its states at the pH, is FR-43's, a later phase
(§8.2.18 T6). The author, at WP5.04's plan: "If this is about partial (de)protonated states, I solved this in the past
using a custom version of PDB2PQR. This is something we can look into later, so write it down as such."

**Deferred** to FR-43's library package: it starts from the author's customised PDB2PQR, which the author supplies
then, and writes the physics into §4 first (T6). Found at WP5.04's plan, 3 November 2026.


### REV-184: Stage 4's probe-radius gate ignores a `charge.edits` radius scale

Under `geometry.density.atoms: protonated` a `radius_scale` widens or narrows the residue's kernels in stage 2, so
the contour moves (§5.3.1 NOTE on `charge.edits`). Stage 4's gate measures the lumen against the probe-radius
profile, which `geometry/contour.py:gate_inputs` builds from the aligned ensemble and the unscaled radius set; its key
does not read the protonation artefact. A scale above 1 on a lumen-lining residue pulls the contour inward against
an unmoved probe, so `r_c - R_p >= -h_c` can refuse a legitimate variant; a scale below 1 moves it outward towards
the upper band. Either way the gate compares the variant's wall with the parent's atoms.

**Fixed** (author's ruling, 3 November 2026, in WP5.04): under `protonated` the probe profile scales stage 1's
atoms by the case's radius edits, matched on the parent name, number and insertion code as stage 2 matches
them (`structure/protonated.py:residue_radius_scales`), so the gate compares the variant's wall with the
variant's atoms. Stage 4's key carries the radius edits only where there are some, so no key moves without
them; under `as_loaded` stage 2 does not scale and neither does the probe. Tier 1:
`test_fr38_a_radius_edit_scales_the_stage_4_probe_as_it_scales_the_density`.

### REV-185: A charge-only edit moves stage 2's key and rebuilds the mesh

Under `protonated`, stage 2 keys on the whole protonation artefact's hash. A `charge_change_e` edit changes no
position, name or radius stage 2 reads, yet it moves the protonation key and with it stages 2 to 6, so each charge
variant re-deposits the density and remeshes to the same map. WP5.03's review accepted that the whole-artefact key
can miss a cache and never hit a wrong one; with `charge.edits` the miss is the cost of every charge variant on a
full walk, against the plan's "a few seconds once the original has been built".

**Fixed** (author's ruling, 3 November 2026, in WP5.04): stage 2 keys on the protonation key with its charge edits
dropped (`density/stage.py:atoms_key`), which is the protonation artefact's own hash when there is no charge
edit, so the unedited keys do not move. A charge variant then shares its parent's stages 2 to 6; a state or
radius edit still moves them. Stage 2's summary records that key as `atom_source.atoms_key` in place of the
table's digest, which a shared density would misreport. Tier 1:
`test_fr38_a_charge_edit_keeps_the_parents_density_key_and_a_radius_edit_moves_it`.

### REV-186: A stored mesh beside a `structure:` section is refused

`inputs.mesh.artefact` (REV-62) names a stage-6 mesh in the store, and `structure:` or `geometry:` beside any
`inputs.mesh` is refused naming both, by the upstream rule of the §5.3.1 NOTE on `inputs:`. The stored mesh's frame
against a structure is unknown: nothing the case carries says where the structure sits in the frame the mesh was
made in, so a `structure:` beside it could be applied at the wrong offset without a gate to see it. The refusal is
safe, but a study cannot pair a molecular model that holds `structure` with a continuum model whose mesh is named
by hash.

Open: the author rules whether a stored mesh's frame is recorded and checked against the structure's, so that the
pair is refused only on a mismatch, or whether the refusal stays.

### REV-187: A study that drops a mixed block writes a study form it cannot read

`Case.with_({"charge": None})` on a study whose molecular model holds `charge.ph` gives a valid case with no
`charge:` section, and `io/models.py:_compare` records each model-owned leaf of the block as an override to `None`
(`charge.ph`, `charge.forcefield`, `charge.titration`, `charge.edits`, `charge.exclusion_offset_nm`).
`Case.dumps(study=True)` then writes `charge: {ph: null, ...}`, which the merge lays over the model's block and the
schema refuses, so the study form does not read back and a sweep over the study (§5.3.4, which writes that form as
its base) cannot be planned. A mixed block is split below its own name (§5.3.1 NOTE on `models:`), so dropping it
whole has no single override to write. Found by code review 030.

Open: the author rules whether a study may drop a block that a named model and the study share, and if so how its
study form writes it, or whether the substitution is refused.

Ruled by the author: refused. `ModelRecord.check_dropped`, called from `io/case_paths.py:substitute`, refuses
setting to `None` a block the study owns that holds a key a named model sets, naming those keys and the two
remedies (set them in the model file, or substitute the block's keys one by one). §5.3.1's NOTE on `models:` says
so. Verified at review (§8.2.13 N3).

### REV-188: The COMSOL comparison keys a stored mesh without a store

`validation/comsol.py:_upstream` builds each stage with `create(name)` when no recorded artefacts are given. Since
WP5.05 the mesh stage takes the store, and a case naming `inputs.mesh.artefact` has no key without it, so the
comparison raises `ValueError` ("built without a store") for such a case. `pipeline/run.py:stored_upstream` passes
the store as the walk does; `_upstream` has none to pass. Found by code review 030.

Open: no frozen COMSOL case names a stored mesh, so nothing fails today. Either the comparison takes a store, or it
refuses a stored mesh naming the key.

Ruled by the author: refused. `validation/comsol.py:_upstream`, keying a case without recorded artefacts,
refuses one naming `inputs.mesh.artefact`, naming the hash, and points at comparing a finished run of it or
supplying `inputs.mesh.path`. §5.2's stage table says so. Verified at review (§8.2.13 N3).

### REV-189: A relative model path reads beside the study in `with_`, and against the working directory in `plan_sweep`

`ModelRecord.carried` reads a relative `models.molecular` or `models.continuum` beside the study file, so
`Case.with_(models={"continuum": "b.yaml"})` reads `b.yaml` next to the study. `api/sweep.py:plan_sweep` resolves the
same relative axis values against the working directory before it writes the plan. A script run from another
directory sweeps other files than the edit it mirrors names, or is refused as "not a file". A sweep file's axis
values read beside its base case (§5.3.4), which is a third rule. Found by code review 030.

Open: the author rules which directory a relative model path in the Python sweep reads against.

Fixed: beside the study. `api/sweep.py:plan_sweep` reads a relative `models.*` axis value against the study's
`ModelRecord.base`, as `Case.with_` does, and writes it absolute into the plan. §5.3.4 says so. Verified at review
(§8.2.13 N3).

### REV-190: `CaseDocument` equality counts `models` and the model record

§5.3.1's NOTE on `models:` leaves `models` out of every dump, hash and equality of a case. `Case` compares dumps, so
a study equals its inline twin. `CaseDocument`, which `pipeline.case.load_case` returns, keeps pydantic's equality:
it compares the `models` field and the private record, whose `ModelRecord` compares by identity. Two loads of one
study compare unequal, and so do a study and its twin. Nothing in `src/` compares two documents today. Found by code
review 030.

Open: whether `CaseDocument` takes `Case`'s equality (and a hash to match it), or the NOTE narrows to `Case`.

Ruled by the author: `CaseDocument` takes `Case`'s equality. `__eq__` and `__hash__` move from `api/case.py` to
`io/case.py:CaseDocument` and compare and hash the dump, which leaves out `models` and the record; `Case` inherits
them. §5.3.1's NOTE on `models:` names both. Verified at review (§8.2.13 N3).

### REV-191: A stored generated mesh skips the field-frame check

`charge/stage.py` checks a supplied field's `model_frame_centre_z_nm` against the mesh's frame only when
`resolved.generates_mesh` and a membrane is set. A case that names a generated mesh by its store hash
(`inputs.mesh.artefact`) has no `geometry:`, so the check never runs and the frame shift is taken as 0, although the
stored region records the generator's shift (`geometry/region.py`). A case B that names case A's mesh (centre
`c ≠ 0`) and supplies `inputs.charge` declaring `c'` places the charge `c − c'` nm off along z, where case A refuses
the same field. The quick-start, whose centre is 0, does not reach it. Found by the WP5.05 physics review.

Open: the author rules whether the check reads the stored region's frame for a stored generated mesh, or a supplied
field beside a stored mesh is refused, as a structure beside one is (REV-186).

Ruled by the author: the stored region's frame is read. `charge/stage.py:check_stored_frame`, called from the
stage-7 key and run, reads the region the stored mesh was generated from (its `region` input) from the store and
refuses a supplied field whose `model_frame_centre_z_nm` differs from that region's membrane centre, as a
generated mesh does; a store without that region refuses the declaration, which it cannot check. A field that
declares no frame is read as before. §5.3.1's NOTE on `inputs.charge`, `inputs.eps_r` says so. Tier 1:
`test_fr27_a_field_beside_a_stored_generated_mesh_is_checked_against_its_region`.

### REV-192: A run on a stored mesh records the generating case's Debye sizing

`pipeline/run.py:_mesh_record` lays the run's own Debye record over the mesh summary's sizing only when the case
generates its mesh. A run on a stored mesh keeps the generating case's Debye length and ratio in its manifest's
geometry-and-mesh group, without saying so. The mesh hash still reconstructs the run, so nothing is lost, but a
reader can take that λ_D for this run's (§5.3.3). Found by the WP5.05 physics review.

Open: whether the record keeps the mesh's sizing and adds this run's Debye length beside it, marked, or overlays it
as a generated mesh does.

Fixed: kept and marked. `pipeline/run.py:_mesh_record` keeps a stored generated mesh's sizing as it was made and
adds this run's own Debye lengths beside it as `run_debye` (`mesh/sizing.py:run_debye_record`: the
uncorrected and the corrected `λ_D`). §5.3.3's Geometry-and-mesh row says so. Verified at review (§8.2.13 N3).

### REV-193: An output that needs nothing and extracts is skipped for a model with no transport

`post/stage.py:QoIStage.run` returns before any `extract` runs when the model declares no transport. An output
registered with `needs=∅` and an `extract` is offered by `outputs.provided` for every model, accepted by `_check_outputs`,
and then missing from the summary of `pb`, `pb-linear` and `poisson`, with no refusal. The six shipped outputs cannot
reach this: `fields` has no `extract`. Found by the WP5.06 review.

Fixed: ruled by the author. `register_output` refuses an output with an `extract` that does not need `transport`, naming
the reason, so no model offers an output that stage 11 would then leave out. Verified at review (§8.2.13 N3).

### REV-194: A registered steric form or output enters the key by name only

The solve key carries a non-validated steric model's name (`electrolyte.steric_model`), and the stage-11 key an output's
name and its parameters. Re-registering a name with a changed body returns the earlier cached artefact. §5.5's NOTE asks for the
name only, and `borukhov` is versioned with the package. A user's own stage is keyed on a digest of its code object
(§5.5). Found by the WP5.06 review.

Fixed: ruled by the author. The name alone keys a registered form and extractor, as §5.5's NOTE says; `borukhov` and the
shipped outputs are versioned with the package. A changed body is a new name. No digest, no amendment. No code change.

### REV-195: The manufactured source builds the Borukhov flux whatever steric model is named

`validation/mms.py` switches on `model.steric`, a bool, and always manufactures the Borukhov source. A second registered
form would fail the convergence test loudly but would not say why. Found by the WP5.06 review.

Fixed: ruled by the author. `ManufacturedSolution` refuses a steric model other than `borukhov`, naming the model, so a
second form fails with its reason; the package that ships one adds its manufactured form (§8.2.28 AD5).

### REV-196: The case JSON Schema no longer lists the steric models and the outputs

`Steric.model` and `outputs` are strings in the case model, checked by `check_document` against the registries, so
`case_json_schema()` and the published `case.schema.json` carry no enum for them. The `io` layer cannot import the
registries (VER-61). Found by the WP5.06 review.

Fixed: ruled by the author. `docs/scripts/generate.py` writes the registered steric models and outputs as enums into the
published `case.schema.json`; `io` stays registry-free (VER-61).

### REV-197: Rectification does not pair a bias set through a variable

The sweep plan pairs the two points of a rectification ratio by `boundary_conditions.bias_V` in their assignments
(`sweep/plan.py:_pairs`, §5.3.1 NOTE on `outputs:`). An axis over a variable that sets the bias (`bias_V: v` with an axis
on `variables.v`) assigns no `bias_V`, so the plan finds no matched pair and refuses a sweep that asks for
`rectification`. Found by WP5.07 (FR-39).

**Accepted**: WP5.19, which builds the Sweep tool (§8.2.34 AJ10), pairs points by each point's resolved bias (`plan.case(index).boundary_conditions.bias_V`) instead of its assignments.

### REV-198: A sweep plan is not tied to the variables as written

The plan reads barriers, warm-start parents and variable-axis reach from the variables as written, but `SweepPlan.base_case()` accepts a base case whose resolved numbers hash the same. A formula changed to a literal of equal value passes the check, and the plan's barriers are then stale. Found by the WP5.07 review (FR-39). The remedy is a plan identity that covers the variable record.

**Fixed** in WP5.07: the plan records the variables and expressions as written, carries them in its digest, and `SweepPlan.base_case()` refuses a base case whose variables moved, naming both.


### REV-199: The sweep forecast resolves every point again

`forecast()` re-reads the base case, substitutes and resolves each point, which `build_plan` already did; `run_plan` repeats it through `_announce`. The cost grows with the points and with a stored mesh ingested at each point. Found by the WP5.07 review. The remedy is for the plan to carry its resolved members.

**Fixed** in WP5.07: the plan resolves each member once (`SweepPlan.resolved_members`, seeded by `build_plan`), and the forecast reads them. A plan read from disk resolves them on first use.


### REV-200: A second type repeats the variable resolution

`VariableRecord` and `Resolution` hold the same four fields, and `VariableRecord.of` only copies one into the other. They must stay in step by hand. Found by the WP5.07 review. The remedy is one type, which spans `io/variables.py`, `io/models.py` and their callers.

**Fixed** in WP5.07: `VariableRecord` extends `Resolution` and takes its fields from it, so the four fields are declared once. The record stays in `io/models.py` because its operations need the case's document types, which `io/variables.py` cannot import.


### REV-201: `sweep plan --json` drops the reason a forecast could not be made, and the case JSON Schema does not describe variables

When the forecast fails, the text output gives the reason and the JSON gives `forecast: null` alone. `case_json_schema` lists neither `variables:` nor a string at a numeric field, which the workbench forms will need. Found by the WP5.07 review. Both change a public shape, so the author rules.

**Fixed** in WP5.07: `sweep plan --json` carries `forecast_unavailable` with the reason, and `case_json_schema` declares `variables:` and admits a string at each numeric field (VER-76 (c)).


### REV-202: The problems list leads to a suite, not to the field, and the suites' tools are not built

A row of the problems list opens the suite that owns the item, and the suite lists its tools as text ("in a later package"), so no field is reachable and the job "see a refusal, fix the value, go on" cannot be finished (WB-12). Found by the WP5.08 `/np-gui review` (F4, F5). The frame is this package's scope; the tools are WP5.16 to WP5.19's.

**Deferred** to WP5.16 to WP5.20 (§8.2.34 AJ10): each suite's package makes its tools real, and the problem row then opens the tool at the field. The tool lists become disabled list items or controls as the tools land.

### REV-203: The frame's accessibility and layout limits

The WP5.08 `/np-gui review` found, in the frame as built: the bottom panel opens about 180 px high and clips the changed list and the problems list with no row count (F3); the frame has no landmarks, no heading and no `aria-live` region for the changed count, the problem count and the queue line (F15); the splitter has no keyboard resize beside the fold buttons (doubt 5); the activity bar has names and no icons (F14); the shortcuts `Alt+Shift+digit`, `Ctrl+K` and `Ctrl+,` may be claimed by a browser or an operating system (doubt 6); and the 3D view's background is read once when the viewer starts, so a change in the settings reaches an open viewer after a reload (doubt 4).

**Deferred** to WP5.15, which rebuilds the frame on Quasar's components (§8.2.34 AJ1): the panel's height and row counts, the landmarks, heading and live regions, the splitter's keys, the icons and the reserved chords. The keyboard pass over every canvas action stays with the guided route, WP5.21 (QR-16).

**Fixed** by WP5.15 (5d0f934, 7b052a8 and item 14): the bottom panel opens 220 px high, scrolls, and is resized by its separator; the changed count stands in the title bar and the problem count in the status line, each a live region; the frame has named `nav` regions, a skip link and real headings; each separator moves by the arrow keys, Home and End; the activity bar shows an icon over each suite's name; no default chord is one a browser keeps (`commands.BROWSER_KEPT`), F1 opens the palette beside Ctrl+K, and every chord can be rebound. The 3D view's background follows a change in the settings at once (`nano.background`), and a keyboard focus ring in the accent marks Quasar's items, buttons and tree rows. The keyboard pass over the canvases stays with WP5.21 (QR-16).

### REV-204: The settings and the changed list lack some guards and units

The WP5.08 review found: the settings dialog has no sticky footer and the colours sit in a collapsed section (F9); a shortcut has no per-row clear control (F7); Reset, Reset layout and Quit act at once with no confirmation or undo, and Quit does not warn of a running build (F12); the changed list shows a value with no unit beside it and a default of `None` (F12); an item that fails to load adds nothing to the changed count and says nothing (doubt 1); and a path set in a case counts as changed whether or not it differs from the validated default (doubt 2). A user's theme has no contrast display by the author's ruling (§8.2.33 AI1), so that part of F8 is answered and not open.

**Deferred** to WP5.15, whose settings page follows one declared list (§8.2.34 AJ9) and whose changed table shows each unit (AJ7).

**Fixed** by WP5.15 (1c2416e, 230af47, 7b052a8): the settings are a page with no footer to lose, its colours a section of the theme's setting; each shortcut has its own clear; Reset, *Reset layout* and *Quit* ask first while the `confirm` setting is on, and *Quit* names the running entries; the changed table shows each value in the user's figures with the file's unit, and an empty default reads "not set"; an item that does not load, or that the problems list refuses, is a "not counted" row that leads to *Problems*, outside the count. A value counts as changed only where it is away from its default (`io/defaults.py:changes`).

### REV-205: The Study page shows fixture names, and the charge screen lacks a colour bar and axes

The Study page prints `State: <fixture name>` and stage chips with no verdict word (F16), and the charge screen's map has no axes, no unit and no diverging colour bar, and its strip lists one residue while two charges are drawn (F17). Found by the WP5.08 review. The charge screen is WP5.02's spike screen, placed in the frame.

**Deferred** to WP5.19, which builds the Charge on the mesh tool (WB-26; VER-60) after its prototype round on 2WCD (§8.2.34 AJ8, AJ10).

### REV-206: An exported project can lose a result file of the same name, and keeps the run record's old paths

The WP5.08 code review found four limits of `Project.export`. Two result files of one run that share a name, from different folders, are copied to `results/<name>` and the second replaces the first. The copied `run.json` still lists the result paths of the project it was copied from, so the copy's record points back at the original. An input file kept in a sub-folder of `inputs/` is copied flat while the item that names it is not rewritten, and an input in `inputs/` that no item names can share a name with a linked input and replace it. A failure part-way leaves a half-written destination that the next export refuses as not empty.

**Deferred** to WP5.19, the package that writes run records into a project (§8.2.34 AJ10).

### REV-207: The frame writes the layout on every drag step, rereads the theme files, and keeps its dialogs

The WP5.08 code review found: a splitter's change event writes the project file at every step of a drag; `theme.shipped()` parses `tokens.css` and `user_themes()` every theme file at each call, several times to build one page and once per colour keystroke; the New, Open, Import, Export and Glossary dialogs are created at each use and never deleted, so a long session accumulates them; an empty folder field in those dialogs reads as the server's working folder; and the palette's filter is written twice, in `fill_palette` and `first_match`.

**Deferred** to WP5.15, which rebuilds the frame (§8.2.34 AJ1, AJ10).

**Fixed** by WP5.15 (5d0f934, 7b052a8, 0aa6398): a separator saves the layout on release only; `theme.shipped` is cached and `user_themes` is cached on its folder's newest change; the dialogs are built once per page; an empty folder field is refused; the palette's filter is one function in `palette.js`.

### REV-208: The palette finds commands by title only, has no active row, and lists commands that cannot run

The second WP5.08 screen review found: the palette matches a typed word against a command's title only, so "theme", "density", "spacing", "dark" and "shortcut" find nothing and "Settings…" is the only route to them; no row is highlighted and the arrow keys do not move through the list; and "Import case…" and "Export project…" are listed with no project open, where they only refuse.

**Deferred** to WP5.15, with REV-211 (§8.2.34 AJ1, AJ10). It gives each command keywords, adds the setting commands, the highlighted row and the arrow keys, and disables a command with the reason.

**Fixed** by WP5.15 (d74b9b3, 0aa6398): each command has keywords and each setting a command; the palette's first runnable match is active and the arrow keys move it; a command that needs a project is listed disabled with its reason.

### REV-209: The charge screen in the frame shows a link where none exists, and its map ignores the dark theme

The charge screen is WP5.02's spike screen, placed in the frame. With no case or no structure charge it still shows "Linked" with an Unlink button beside two empty canvases and no caption; it says "case", a retired term; the Study page offers its link in the empty state; the map's background is light grey on the dark theme, against WB-26. The review doubted two things it could not check from the pictures: the Mol* toolbar icons may read below 3:1 (the harness measures no viewer control), and the 3D spheres and the map's dots may colour the same charges oppositely.

**Deferred** to WP5.19, which builds the Charge on the mesh tool (WB-26; VER-60) with the colour bar of REV-205, its design settled in its prototype round (§8.2.34 AJ8, AJ10).

### REV-210: The frame lacks icons, headings and some states in the render set

The second WP5.08 screen review found: the activity bar has text only where the design document says an icon with its name; suite and dialog titles are labels, not headings; the changed diamond is read aloud by a screen reader; the settings' colour inputs carry raw token names with no swatch; the Glossary holds 5 of the document's 22 terms and About is a toast that disappears; and the New, Open, Import and Export dialogs are a free text path with no browse list. The render set shows none of: those dialogs, the File, View and Help menus, a folded rail, the Queue and Log tabs, the Colours section, a user theme, compact density, tight spacing, the 3D background settings, a key being captured, or a typed palette query.

**Deferred** to WP5.15, which rebuilds the frame (§8.2.34 AJ1, AJ10): the icons, headings, render states and the dialogs with a recent-projects list. The review also doubted that opening a project runs its first study; that holds for the `--state` fixtures only, and `nanopnp gui <project>` walks nothing, so it is answered.

**Fixed** by WP5.15 (5d0f934, 7b052a8, 93add84): each suite has its icon; suite and dialog titles are headings; the diamond is hidden from a screen reader beside its word; the colours show swatches under plain names; the glossary holds the design document's 26 terms and About is a dialog; the project dialogs list recent projects. `render_shell.py` renders a 2WCD project, the four project dialogs, the three menus, a folded rail, the Queue and Log tabs, the Colours section, a user theme, compact density and tight spacing, the 3D background setting, a key being captured, a typed palette query, Glossary and About.

### REV-211: The palette opens as a full command list, not a bare input that suggests as you type

The author, marking the frame's palette (`docs/design/reviews/2026-11-05-frame.md`): "This should far more sleek and subtle, not just a list of commands. Default should be just a box to type in, and suggestions should pop up once you start typing." The palette opens as an input over every command with its chord.

**Deferred** to WP5.15, with REV-208 (§8.2.34 AJ1, AJ10). The palette opens as one input and lists no commands until a word is typed. The matches then appear under it, found by title and keyword, one row active and moved by the arrow keys. A command that cannot run is listed disabled with its reason.

**Fixed** by WP5.15 (0aa6398): the palette is one input, empty until a word is typed, its matches under it by title and keyword, the first runnable one active.

### REV-212: The settings need a searchable section list beside the panel, and which settings exist is undecided

The author, marking the frame's settings: "The settings window should have a navigation menu on the left, with search, and a settings panel on the right. Much like how this is done in Claude Code and other IDE editors. Further, we should discuss and brainstorm on which settings we should include, and how they are stored and applied." The settings are one dialog of stacked sections: theme, density, spacing, the 3D background, the colours and the shortcuts (§8.2.33 AI1; REV-204).

**Deferred** to WP5.15, ruled by the author on 5 November 2026 (§8.2.34 AJ9; WB-37): the settings are one declared list, each setting with its section, its scope (the user's, or the project's over the user's), its default, its description and search words and when it applies; the page, its search, the palette's setting commands and both files follow. The sections are appearance and accessibility, keyboard and editing guards, runs and storage, and units and numbers; which settings beyond them exist, compute and network among them, is put to the author at WP5.15's plan after a survey of comparable tools.

**Fixed** by WP5.15 (97bf4e2, 1c2416e): the settings are one declared list (`gui/web/settings.py:SETTINGS`), and `/settings` has search and the section list beside the panel, *User* or *Project*, *Modified only*, and each value's mark and reset. The compute settings are WP5.19's (§8.2.38 AN1, AN4).

### REV-213: The suites may need to separate those that build models from those that use them

The author, marking the Molecular suite and then the Continuum, Study and Analysis suites with "See Molecular suite comments": "I wonder if we need to make a further distinction in the suites between those that build components (molecular, continuum, physics), those that use components (study, analysis?). I think we need to discuss this further to figure out what I mean." The frame has four suites side by side in the activity bar (WB-02, WB-29). The models are built in Molecular and Continuum (WB-11), and the physics defaults sit in the continuum model (WB-16).

**Deferred**, ruled by the author on 5 November 2026 (§8.2.34 AJ2 to AJ5; WB-34, WB-35): physics becomes a third reusable model, and five suites show as those that build models (Molecular, Continuum, Physics) and those that use them (Study, Analysis). The physics model is WP5.09's library step, the grouped suites WP5.15's, and the Physics suite WP5.18's.

**Fixed** by WP5.15 (d74b9b3, 5d0f934): the activity bar shows Molecular, Continuum and Physics under *Build* and Study and Analysis under *Use*; Physics stays empty until WP5.18.

### REV-214: The changed list is loosely spaced, and the project name reads as a menu

The author, marking the changed list: "Spacing seems very generous. How is this kind of change tracking typically done in programs like `nanopnp`?" Each changed value is a row of about 48 px: the path, the value, its default and *Reset*. Then, on the refused state: "Not sure the "refused" marker in the top bar is the best location, looks like a menu item." The word is the fixture project's name (`--state refused` opens a project named `refused`), not a refusal marker. The name sits in the menu row, after *Help*, in the menus' weight, so it reads as a menu.

**Deferred** to WP5.15, ruled by the author on 5 November 2026 (§8.2.34 AJ7; WB-36): the mark at the field with its reset, a *Modified only* filter on each pane and the settings, and one dense table grouped by model and study with value, default, unit and reset. The project's name heads the project rail and names the browser tab.

**Fixed** by WP5.15 (230af47, 7b052a8): the changed values are one dense table grouped by item, with mark, field, value, default, unit and reset; the project's name heads the rail's tree and names the browser tab, and is gone from the menu row. The mark at each field and each pane's *Modified only* filter are the suites' (WP5.16 to WP5.19).

### REV-215: The charge screen needs its design and its function settled together

The author, marking the charge screen: "Looks very poorly integrated. Maybe because we are still in early development phase for the GUI. Also hard to judge without an example molecule.", then: "Looks very rudimentary still. I think we need to discuss a bit on how the design and functionality can go hand in hand." The screen is WP5.02's spike, placed in the frame (REV-205, REV-209). The render set's states are a charged and an uncharged tube, with no protein.

**Deferred** to WP5.19, ruled by the author on 5 November 2026 (§8.2.34 AJ8; WB-38): the Study package opens with its tools prototyped over 2WCD's artefacts and rendered through their states, and the charge screen's design is settled with its function in that round, with REV-205's colour bar and axes and REV-209's link and dark map.

### REV-216: The Phase 5 plan exceeds its word target again

The Phase 5 plan holds about 5,100 words without its report, against `np-plan`'s 1,500 target for a phase plan, checked at review (§8.2.13 N3). REV-133 brought it to 1,500 on 24 October 2026; the amendments since grew it to about 4,200 and §8.2.34 to 5,100, each rewriting its package entries to their current scope as R4 asks. The delivered entries WP5.01 to WP5.08 hold about 1,770 words, so moving them to `phase-5-record.md` would still leave about 3,400. Found by CODE_REVIEW_034, finding 9.

**Open** for the author: cut the plan to the target (delivered entries to one line each, the rest condensed), or restate the target for a phase amended in flight.

**Grown** (CODE_REVIEW_040, 8 November 2026): the fourth amendment (§8.2.36) brings the plan to about 6,500 words, of which about 2,500 are the delivered entries WP5.01 to WP5.09. WP5.11 moves delivered narratives out of the live plan (AL18; AUD-244), which takes the first half of the cut; the choice between the rest of the cut and a restated target stays the author's.

**Fixed** in WP5.11 (§8.2.36 AL18; AUD-244): WP5.01 to WP5.10 keep their title, merged line and live constraints, and their narratives move verbatim to `phase-5-record.md`; the dated status chain and the settled open decisions move with them. The plan holds 4,243 words by `wc -w`, from 6,548; the rest is the live scope of the eleven packages still to run.


### REV-217: Case reading, substitution and input-path discovery are split across five modules

Reading a case is split between `io/case.py:read_case`, which refuses `models:` and `variables:`, and `io/models.py:read`, which resolves them. `Case.with_` substitutes twice, once for the edits and once for the relative paths `_rebased_paths` finds. Input-file discovery is written four times: `io/case_paths.py:input_paths` with `correction_paths`, `io/models.py:_rebased`, `io/project.py:item_inputs`, and the merges in `api/case.py` and `api/sweep.py`. Found by CODE_REVIEW_036, candidate 1, with its corrections C1.1 to C1.5.

**Settled** with the author in [CODE_REVIEW_036](../code_reviews/CODE_REVIEW_036.md) on 7 November 2026, to land after WP5.09 (the physics model); its corrections bind the package that lands it, which *Placed* names.

**Placed** (§8.2.36 AL22, 8 November 2026): WP5.13, case and model files, with CODE_REVIEW_036's candidate 1; the case reader then resolves `models:` and `variables:` (AL23).

**Fixed** in WP5.13 (§8.2.36 AL22, AL23): `io/models.py:read_case` and `read_case_text` are the one reader pair and resolve `models:` and `variables:`; `io/case_paths.py` holds the one input-path seam (`input_paths`, `rewrite_inputs`, `rebase_inputs`); `substitute(document, assignments, *, base)` rebases in each branch, so `Case.with_` substitutes once.

### REV-218: Effective atom radii and atom-to-residue indexing are split across four subpackages

`density/radii.py:resolve_protonated_radii` returns CHARMM radii without the table's radius edits, so `density/stage.py` must multiply by `radius_scales(table)` itself. Atom-to-residue indexing is written twice, in `charge/edits.py:_owner` and in `resolve_protonated_radii`, and the two differ on an atom with no residue row. Found by CODE_REVIEW_036, candidate 4, with its corrections C4.1 and C4.2.

**Settled** with the author in [CODE_REVIEW_036](../code_reviews/CODE_REVIEW_036.md) on 7 November 2026, to land after WP5.09 (the physics model); its corrections bind the package that lands it, which *Placed* names.

**Placed** (§8.2.36 AL22, 8 November 2026): WP5.16, the Molecular suite's library step, with CODE_REVIEW_036's candidate 4.

### REV-219: A model file's validated body is discarded and parsed again by the project

`io/models.py:_read_model_file` validates and rebases a model file's body and then drops it from `ModelFile`. `api/project.py` reads the YAML again (`_body`), strips `schema` and `name` by hand for `mapping_changes`, and repeats `io/models.py:_put` and the layer split (`Project._split`). Found by CODE_REVIEW_036, candidate 5; its sketches are re-read against the code as WP5.09 leaves it (C5.1).

**Settled** with the author in [CODE_REVIEW_036](../code_reviews/CODE_REVIEW_036.md) on 7 November 2026, to land after WP5.09 (the physics model); its corrections bind the package that lands it, which *Placed* names.

**Placed** (§8.2.36 AL22, 8 November 2026): WP5.13, case and model files, with CODE_REVIEW_036's candidate 5.

**Fixed** in WP5.13 (§8.2.36 AL22): `ModelFile.body` carries the checked body that `read_model_file` reads once, rebased unless `rebase=False`; `io/models.py:split_case_layers` serves `Project._split`; `mapping_changes` skips the header and `models:`, so `api/project.py` strips nothing by hand.

### REV-220: The upstream lookup and the forecast re-implement the walk's stage keying

`pipeline/run.py:stored_upstream` and `pipeline/forecast.py:keyed_walk` each look up the stage description, build the stage, filter `offered()` and query the store on their own, beside `_Walk.describe`, `_Walk.inputs` and `_Walk.construct`, which serve the run. `stored_upstream` ignores a session's own stages. Keying must not use `_Walk.construct`, which makes scratch workspaces. Found by CODE_REVIEW_036, candidate 6, with its correction C6.1.

**Settled** with the author in [CODE_REVIEW_036](../code_reviews/CODE_REVIEW_036.md) on 7 November 2026, to land after WP5.09 (the physics model); its corrections bind the package that lands it, which *Placed* names.

**Placed** (§8.2.36 AL22, 8 November 2026): WP5.14, sweep planning and the walk's keying, with CODE_REVIEW_036's candidate 6.

**Fixed** in WP5.14 (§8.2.36 AL22): `pipeline/run.py` holds the one keying walk. `_Walk.keyed` builds a stage to compute its key without a workspace and `_Walk.stored` reads the store, and `stored_upstream`, `keyed_walk` and the run's substitution all use them; `stored_upstream` takes a session's own stages and an already resolved case, and `pipeline/forecast.py` is gone.

### REV-221: Planning a sweep from a case drops the members it resolved

`sweep/plan.py:build_plan` keeps the members it resolved as `plan.__dict__["resolved_members"]`, and `api/sweep.py:plan_sweep` moves the plan out of its staging directory with `replace(staged, base_path=...)`, which builds a fresh `SweepPlan` without them. `plan_sweep(...).forecast()` therefore resolves every member again, which REV-199 set out to stop. The staged members were resolved beside the deleted staging directory, so the fix keys held members on their directory rather than carrying them. Found by CODE_REVIEW_036, candidate 2, with its corrections C2.1 to C2.3.

**Settled** with the author in [CODE_REVIEW_036](../code_reviews/CODE_REVIEW_036.md) on 7 November 2026, to land after WP5.09 (the physics model); its corrections bind the package that lands it, which *Placed* names.

**Placed** (§8.2.36 AL22, 8 November 2026): WP5.14, sweep planning and the walk's keying, with CODE_REVIEW_036's candidate 2.

**Fixed** in WP5.14 (§8.2.36 AL22): a `SweepPlan` holds its resolved members keyed on the directory they were resolved beside, and a plan moved elsewhere resolves them again there (C2.2). `plan_sweep` plans in memory with `build_plan(..., base=case)`, so its plan keeps them, and `run_point` and the parent lookup take a member from `held_member` where the plan holds it; §5.3.4 says so.

### REV-222: The agentic instructions cite identifiers without their words and state two procedures in several places

CODE_REVIEW_038 audited `CLAUDE.md`, the skills, the workflow files and the hooks. Four of its findings were left for a later commit. C2: the skills cite a ruling or clause identifier about 90 times as the only cross-reference, each costing a `clause.py` call to read, against `core.md`'s own rule that an identifier only follows its words. C3: the gate-and-push procedure is stated in `CLAUDE.md`, `core.md`, `steward/SKILL.md` and `hosts/copilot.md`, and the two-lane rule in five places; none contradicts another today, and the risk is drift. E5: `core.md`'s *Putting a choice to the author* and *The In brief* are read by `/np-implement` and `/np-ship`, which do not use them, about 450 words each. E6: `AGENTS.md` imports `CLAUDE.md` with `@`, so a Copilot session loads it twice.

**Open.** Each is a wording change to agent text, with no specified behaviour behind it; take them in the next package that edits the file concerned, keeping each procedure stated in full in one place and pointed to from the others.

**Fixed** in WP5.11 (§8.2.37 AM9): C2, an identifier the skills cite alone gains its words; C3, the push gate's mechanics stay in `CLAUDE.md`'s *Commands* and `hosts/copilot.md`, the core keeps the order and points there, and the two-lane rule is §8.4.4's, with the core keeping a session's conduct; E5, *The In brief* and *Putting a choice to the author* move to `.claude/workflow/author.md`, read at the steps that write one or put one; E6, `AGENTS.md` points to `CLAUDE.md` and imports nothing.


### REV-223: PHY-07's density continuity is not assembled

PHY-07 states three flow equations: density continuity `u·∇ϱ = 0`, momentum `(u·∇)(ϱu) + ∇·σ = f`, and
velocity continuity. The reference supplies the first as the hand-added weak term
`(u*d(spf.rho, r) + w*d(spf.rho, z))*test(p)`. The coupled flow residual of `physics/models.py`
assembles the viscous and pressure terms, `continuity_term` with `mass_density` (velocity continuity)
and `inertia_term`, `Re ∫ ϱ̃ (ũ·∇)ũ·v r`, but no term carries `u·∇ϱ`. The assembled `ϱ (u·∇)u` is
PHY-07's `(u·∇)(ϱu)` only where `u·∇ϱ = 0`. Found by CODE_REVIEW_039 (AUD-56). NUM-04 states the forms
the program assembles, with a NOTE naming this item.

**Accepted** (§8.2.37 AM2, 9 November 2026): owned by Phase 6. Measure the term's effect on the
quantities VAL-16 and VAL-17 compare, on the reference case at the envelope's corners, and add it if
it moves one of them.

### REV-224: NUM-28's fluid consistency term omits the pore charge's force

NUM-28's consistency terms take `∇·T_M = ρ_ion E − ½|E|²∇ε` in the fluid. PHY-16 deposits `ρ_pore` on
every material, the fluid included, so in the fluid `∇·T_M` also carries `ρ_pore E`, and the domain
route loses `∫ ρ_pore E·w` wherever the shell of `w` overlaps a protein atom's Gaussian tail. Found by
CODE_REVIEW_039 (AUD-69). NUM-28 carries a NOTE naming this item.

**Accepted** (§8.2.37 AM2, 9 November 2026): owned by Phase 6. Measure `∫ ρ_pore E·w` against
`F^em` on an analyte case with a deposited charge, and either add the term or state that the support
of `w` excludes the deposit.

### REV-225: Three numerics tolerances have no written derivation

Three §6 tolerances give no derivation and no pointer: the absolute residual floor 10⁻¹² of NUM-16,
the increment cap `‖δφ‖_∞ ≤ V_T` of NUM-16 and NUM-17, and NUM-08's "deviation from the analytic value",
which names no tolerance. NUM-26 and NUM-34, by contrast, argue their numbers. Found by
CODE_REVIEW_039 (AUD-52). §6 carries a NOTE naming this item.

**Accepted** (§8.2.37 AM2, 9 November 2026): owned by Phase 6. Measure the residual of a converged solve
in NUM-09's scaling, the largest accepted `‖δφ‖_∞` across the gated walks, and the error NUM-08's test
sees, and write each number's derivation beside its clause.

### REV-226: Refusal messages in src/ cite the §5.3.1 NOTEs whose stage rules moved to §5.2

WP5.11 moved stage 1's refusals and thresholds and stage 2's radius set and union from §5.3.1's NOTEs
on `structure:` and `geometry.density` to §5.2's NOTEs on stages 1 and 2 (§8.2.36 AL11; AUD-113).
Refusal messages and comments in `structure/axis.py`, `structure/read.py`, `io/defaults.py`,
`density/union.py` and `density/radii.py` still cite the §5.3.1 NOTE, which now points on to §5.2: a
user refused by the 10° axis rule takes one extra hop to the rule. WP5.11 changes nothing under
`src/`. Found by CODE_REVIEW_044.

**Accepted** (the author, 9 November 2026, at WP5.11's review): owned by WP5.12. The fix rewrites the
citations in those messages and comments to §5.2's NOTEs, a prose-only change `same_tree.py` confirms
(§8.2.11 L5).

**Fixed** by WP5.12 item 11 (3227166): the messages and comments in those five files cite "section 5.2 NOTE on stage 1" or "on stage 2". `same_tree.py` cannot confirm a change inside a string literal, so `git diff -U0` showed that only the citations changed. The frame-specific refusal of a patched radius in `density/radii.py` keeps §5.3.1, which still states that rule.

### REV-227: The source checklist: six findings that rest on the ESI or the COMSOL report

CODE_REVIEW_039's readers could not check six findings: each rests on the paper's ESI or the COMSOL
model report, which the hosted session cannot read (§8.2.36 AL20; §8.2.37 AM16). The pages are those
of `knowledge/09-comsol-reference-settings/01-document-map.md`. The author checked all six in one round
at WP5.12's item 13 (§8.2.37 AM18), and the Verdict column records each answer.

| Finding | The claim | What the audit found | Source to look up | Verdict |
|---|---|---|---|---|
| AUD-136 (SPD-13) | Appendix B prints the reservoir domain's max 2.8 and min 0.04 nm, the outer boundary's min 0.025 nm and growth 1.25, the axis's min 0.04 nm and the pore domain's min 0.004 nm and curvature 0.2 as settings | `09/02` A.2 prints them "(Off)", inactive overrides; WP5.11 marked them "(inactive)" | Report §2.7 Mesh, pp. 122–131: the size nodes' override checkboxes | Confirmed, 10 November 2026: the marking stays |
| AUD-225 (KNU-32) | `06/08` says the ESI's mesh and solver numbers "have not yet been extracted", and sources a thesis grep to the ESI | `knowledge/09` holds the numbers; the footnote names the wrong source | The thesis (grepped: `epnpns.tex`:234, `transport.tex`:396, 426); report §2.7, §3.2, §4.3, §5.4 | Confirmed, 10 November 2026: the paragraph states both sources, no convergence study published |
| AUD-286 (KST-06) | Appendix B says the current is extracted "over an electrode boundary" | `09/04` C.10 says the evaluation boundary is not in the report | Report §5.1 Derived Values, pp. 143–145; §2.4 | Confirmed with a correction, 10 November 2026: the report does not print it; the paper's main text names the cis reservoir boundary, which also carries the ground. Appendix B, `09/04` C.10 and `09/07` say so |
| AUD-327 (KST-47) | Every `[verified]` claim of `knowledge/09` cites "COMSOL model report (5.4)" with no section or page; `09/00` says "read in full from the project store" | The page map exists in `09/01` and the footnotes do not use it; no path is named | Report, against `09/01`'s page map | Confirmed, 10 November 2026: each footnote names its sections and pages; the PDF is published with the article's ESI |
| AUD-343 (KPH-16) | Ruling 1 says "the running-text value and the 0.62 correction are wrong" | The thesis's running text gives 6.2 nm⁻¹ (`epnpns.tex`:842); which source's text is wrong is unclear | The paper's SI and the COMSOL report | Answered, 10 November 2026: the SI, the report and the thesis all give 6.2 nm⁻¹; ruling 1 now says so, and that the 62 and 0.62 readings are wrong |
| AUD-346 (KPH-19) | `01/02` cites the weak forms as "SI §A.1" | The thesis has them in App. B §B.1; the ESI's number was not checked | The paper's SI | Corrected, 10 November 2026: the SI numbers the section 1.4; `01/02` cites "ESI §1.4; thesis App. B §B.1" |

**The git rows.** AUD-226 (KNU-33) and AUD-326 (KST-46) were dismissed because the hosted clone was
shallow. In a full clone, each of the twelve hashes they name (3872426, 0ea0789, 6c0a249, 7597814,
0f8b57b, 5abcf42, fb4f9ae, 3782c43, c27c35c, 1a2e383, 0ff2d619, 1761f15c) resolves, and so does each
`<hash>:<path>` source in `knowledge/` (`git cat-file -e`, 10 November 2026).

**Fixed** by WP5.12 item 13: each row has its verdict and its edit.

### REV-228: The site's links from the project registers to the plans and reviews lead nowhere

The site excludes `docs/plans/` and `docs/code_reviews/` (`mkdocs.yml`'s `exclude_docs`), so about 150
links of `docs/project/` (the review and modularity registers, the modularity page) lead nowhere on the
built site, while they resolve in the repository. `docs/scripts/generate.py` repoints such links to
GitHub only in the pages it copies. Found by CODE_REVIEW_039 (AUD-14); WP5.12 makes no edit for it.

**Accepted** (the author, 9 November 2026, §8.2.37 AM15): owned by WP5.21, which rewrites the guide and
changes the site. The link check keeps checking the relative links meanwhile.

### REV-229: Three checks the knowledge base proposed without a requirement

Three ideas sat in the knowledge base as proposals, which `knowledge/00-orientation/04` keeps out of a
concept: a print at solve time of `D_i/μ_i` against `V_T` (was `knowledge/02-electrokinetics-background/03`,
AUD-357); an axial sweep of the force `F(z)` that would resolve the several minima the measured current
levels imply (was `knowledge/05-analyte-and-forces/09`, AUD-192); and a test that `N_eo` depends only on
the analyte's size and shape (was `knowledge/05-analyte-and-forces/10` item 10, AUD-192). WP5.12 removed
them from the concepts (items 5 and 7), and this item keeps them.

**Post-1.0** (the author, 9 November 2026, §8.2.37 AM14): visible to the planning of v1.0; no requirement
asks for any of them now.

### REV-230: The correction file's comments cite the wrong equation, count and cause

`data/corrections/willems2020_nacl.yaml`'s header says "Thesis eq. 5.11 prints a minus sign"; the wall
function is eq. 5.23 (AUD-341), which WP5.12 corrected in §4.6 and `knowledge/01`. The header announces
"Four transcription traps" where §4.6 counts six errata. The wall function's `rationale` (lines 146-147)
blames the near-wall dead zone on Simakov's negative form, where Pederson's floor causes it. Lines 33-34
say the ESI writes `P₁` as "0.62e1"; the author found that the paper's SI prints 6.2 nm⁻¹ (REV-227), so
the notation is at most the COMSOL report's.

**Open**, decided by the WP5.12 plan (D3): the file's bytes are a key of stage 8's cache (VER-62), so a
comment edit changes every cached result's key. The fix lands with the next package that changes that
file for another reason; none is named yet.

### REV-231: axis.py's comment sends the stage-1 margins to an index

`src/nanopnp/structure/axis.py`:15-16 reads "Thresholds: SPECIFICATION.md §5.2 NOTE on stage 1; margins:
knowledge/07-software-stack/index.md". That index only lists the concepts; §5.2's NOTE on stage 1 puts the
margins of the four stage-1 thresholds in the WP18 plan, Design §2 to §4. Found at WP5.12's item 11, whose
D6 allowed only REV-226's citations, AUD-216 and AUD-351 under `src/`.

**Open**: a one-line comment fix, for the next package that edits `structure/axis.py`.

### REV-232: Three statements the physics reviewer doubted at WP5.12

The physics reviewer read WP5.12's changes to `knowledge/` and §4.6 and doubted three statements that
WP5.12 did not change:

- §6's derivation of the wall resolution (`specification/06-numerics.md`:165) states `h̃ = λ̃_D/5`,
  citing NUM-30, whose first layer is `min(0.05 nm, λ_D/5)`. The bound NUM-30 sets still meets the
  derivation; the two wordings differ.
- VER-03's row asks for "four significant figures", where its tests assert a relative tolerance of 10⁻³.
  The row predates WP5.12.
- `knowledge/06-numerics-fem/02`'s 3.4e-2 `V_T` source error and its "The planar forms and a uniform-permittivity problem with no source are exact at the default" have no
  source in the WP26 record.

**Open**: each wants a reading against its source, by the next package that touches §6, VER-03 or
`knowledge/06`.


### REV-233: Importing a case leaves a model without a value the study writes as an expression

`Project._split` splits a case through `io/models.py:split_case_layers(raw, pinned=frozenset(case.expressions))`,
which sends a leaf to the study only when its path equals a pinned path, and then gives the leaf's model nothing.
§5.3.5 says the study resolves to the case it was split from; two cases do not import:

- An expression at a model-owned field the schema requires, such as `boundary_conditions.bias_V: v`: the physics
  model lacks `bias_V`, so the models with the study's own keys do not form a case and `_verify` refuses the import.
- An expression inside a list entry, such as `electrolyte.species.0.z` or `charge.edits.0.radius_scale`: `leaves`
  yields the list whole, the exact match misses, and the model receives the expression, which `read_model_file`
  refuses.

`study_layer` pins a leaf by prefix and keeps the model's number, so the study form of a study has neither fault.
Probed at WP5.13's head and at `main` (`ae01061`) alike; WP5.13 moved the split verbatim. Found by CODE_REVIEW_048.

**Fixed** in WP5.13, as the author ruled on 10 November 2026: `split_case_layers` pins a leaf by prefix, as
`study_layer` does, and gives the owning model the resolved number from the case it is passed as `resolved`; the
study keeps the expression. §5.3.5 says so; `tests/tier1/test_project.py:test_fr32_a_case_with_an_expression_at_a_models_value_imports_as_the_same_case`.

### REV-234: The frame shows a tool's 3D view to the left of its settings

The WP5.15 `/np-gui review` (F8): the frame's view region comes before the sub-page in the main row, so on the charge
screen the molecule is on the left and the tool's heading and settings on the right, in a fixed 560 × 420 box with
empty space below it. WB-05 and WB-07 dock a tool's settings on the left of its live view.
At WP5.15's collect the author asked for the residues below the 3D view, so that the view and the
tool's grid stay side by side (`docs/design/reviews/2026-11-11-frame.md`).

**Open.** The first suite with a view, WP5.16, settles the view region's place and size in its prototype round on 2WCD
(§8.2.34 AJ8); the charge screen itself is WP5.19's (REV-209, REV-215).

### REV-235: Design questions the frame's review leaves for the suites' prototype rounds

The WP5.15 `/np-gui review` and `impeccable`'s critique (§8.2.34 AJ6) raised, beyond what WP5.15 fixed:

- the problems list: one line per refusal that repeats the item and the file, opening the item rather than its field;
  no ✕ on a refused item in the rail or before "failed" in the status line (F10);
- the changed table: its header "Default or model's", groups headed by `kind/name`, field names
  that do not look like links (F11); the unit written twice was fixed at WP5.15's collect, which
  dropped the *File unit* column;
- the settings page: no marker of the section in view, the default not shown beside a changed value, the reset placed
  after a long control, the theme's colours in a collapsed section, the swatches below the field's baseline (F12;
  critique 9);
- the project dialogs: a free path with no hint, no browse list, *Create* enabled on an empty field (refused on
  accept), the same recent list in all four, no choice between copying and linking an import's inputs (FR-32), no
  option to export the store (F13; doubt 4); the author's note at the collect asks for a Browse
  button;
- the menus show few chords and not F1 (F14); the Glossary has no search and no scroll cue (F16); the log has no times,
  the queue's states no colour, and "to charge" is the pipeline's word (F17);
- the title bar's count and palette button do not look like controls; the status line repeats the bottom panel's
  tabs; the rail's items have no kind glyph or changed mark; the bottom panel has no grip or fold button (critique 7,
  8, 10, 11).

**Open**, a question for the author: each is put at the prototype round of the suite that first needs it, from WP5.16
(§8.2.34 AJ8), with the screens in front of the author.

### REV-236: Chords the operating system may claim, a command that cannot be unbound, and the glossary written twice

The WP5.15 review's doubts: on macOS, Option+Shift+digit types a character into a focused field, and a browser may
open its own help on F1 (the suite chords are the author's, §8.2.38 AN7); the per-key ✕ on the settings page resets a
chord to its default, and no control unbinds a command, though `commands.bindings` accepts an empty chord; the
glossary's 26 terms are written in `gui/web/glossary.py` and in the design document, and nothing checks that they agree.

**Open.** The keyboard pass over the workbench, WP5.21 (QR-16), takes the chords and the unbinding; the glossary's
single source is put to the author with it.

### REV-237: The author's notes on the frame's digest for the suites' prototype rounds

The author's `change` verdicts at WP5.15's collect (`docs/design/reviews/2026-11-11-frame.md`) that ask
for a redesign rather than a fix:

- the changed table takes much of the screen: something more condensed, or another approach; and a
  value that takes you to the screen where it is set (a row opens its suite at `?field=`, whose tools
  are still text);
- the settings as a floating window rather than a page, with less room per setting (the page is
  REV-212's ruling, which this reopens);
- the folded rail shows something more meaningful than the open item's initial, or nothing: a
  brainstorm;
- the palette, in the right direction now, designed more subtly;
- the Glossary folded into a proper help page (with REV-236's single source).

**Open**, a question for the author: each is put at the prototype round of the suite that first needs
it, from WP5.16 (§8.2.34 AJ8), with the screens in front of the author; the settings window and the
folded rail at WP5.16's, the first.
