# Review register

What a work package's implementation or review left open, one numbered item each, `REV-nn`,
until it is resolved (§8.2.8 H12). `/wp-implement` and `/wp-ship` add an item in the commit that
leaves it open: a confirmed review finding not fixed, a deferral to a later package, or a question
put to the author. The commit that resolves one sets its row `fixed`. The status of each item is in
[the findings log](review-findings.md), which VER-63 checks; this page says what each one is.

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

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-15 — Example 05 quotes #SBATCH directives as shell words

*Area:* interface. *Severity:* low. *Found:* PR #34 (WP16), a confirmed review finding not fixed.

**Measured.** `examples/05-clya-reference/render_slurm.py` passes the job name and working directory
through `shlex.quote` into `#SBATCH` lines. sbatch does not read a directive as a shell would, so a
value that needs quoting does not reach it as written; the review of PR #34 confirmed the finding
and left it unfixed.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-16 — A salt sweep regenerates an identical mesh at each concentration

*Area:* performance. *Severity:* low. *Found:* PR #42 (WP21), left for the author.

**Measured.** The stage-6 recipe key carries λ_D, so below 1.474 M, where the wall size it drives no
longer changes, each concentration of a sweep re-meshes an identical mesh. Warm starts are
unaffected.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

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

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-19 — A zero-frame trajectory raises a bare IndexError

*Area:* interface. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `structure/read.py` raises a bare `IndexError` on a trajectory with no frames, rather
than a refusal naming the file (QR-12). Two Cα with the same `(resid, icode)` in one chain also
overwrite each other in `per_chain`.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-20 — The desktop shell has no multiprocessing.freeze_support

*Area:* process. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** No `multiprocessing.freeze_support()` exists in `src/`. It is needed when the frozen
shell spawns children on Windows.

**Resolves it.** Phase 5, which makes the shell the bundle's executable (QR-10).

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

**Resolves it.** WP43, the small fixes, which measures the duplication first and removes it if it is there (§8.2.9 I2).

### REV-25 — A post stage run without a solve writes scratch to the default store

*Area:* interface. *Severity:* low. *Found:* PR #24 (WP10).

**Measured.** A library caller invoking `QoIStage` or `ReportStage` with no upstream `solve` sends
its scratch to the process-default store root.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

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
walk (open question 1 of the [WP38 plan](../plans/wp38-io-split.md)).

### REV-28 — The viewer renders every finished run eagerly

*Area:* performance. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** Each finished run is rendered whether or not it is viewed.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

### REV-29 — The cylindrical-pore fixture is copied into four test modules

*Area:* verification. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** Four Tier-1 modules each define the same cylindrical-pore fixture.

**Resolved.** WP42 D13: consolidated `cylindrical_pore_case` fixture in `tests/conftest.py` across Tier-1 test modules.

### REV-30 — The viewer's scene is written twice

*Area:* performance. *Severity:* low. *Found:* PR #32 (WP15).

**Measured.** The scene file is written twice per render.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

### REV-31 — The bundle's size is not recorded

*Area:* documentation. *Severity:* low. *Found:* PR #37 (Phase 1 close).

**Measured.** No document records the Windows bundle's size.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

### REV-32 — Old store entries are neither migrated nor removed

*Area:* interface. *Severity:* low. *Found:* PR #38 (WP17).

**Measured.** Entries written under an earlier schema stay in the store, unread and unremoved.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

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

### REV-40 — DensityMap.read accepts a file written in nm

*Area:* interface. *Severity:* low. *Found:* PR #50 (WP25).

**Measured.** A density map written before the ångström convention of §8.2.2 B10 is read without
refusal, ten times off.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-41 — No prepare command, upto on reproduce, or region export

*Area:* interface. *Severity:* low. *Found:* PR #50 (WP25).

**Measured.** `nanopnp prepare`, `reproduce --upto` and a region export were left out of WP25 with
no later owner.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

### REV-42 — pnp carries inert flow keys

*Area:* interface. *Severity:* low. *Found:* PR #53 (WP26).

**Measured.** The `pnp` model accepts `variable_density` and `inertia` as given, though without flow
they do nothing.

**Resolved.** WP42 D5: `pnp` model restricts `variable_density` and `inertia` switch sets to `(False,)`; schema moves to `nanopnp/case/v0.5`.

### REV-43 — chain_characters duplicates the export's mapping

*Area:* process. *Severity:* low. *Found:* PR #55 (WP27).

**Measured.** `chain_characters` repeats the mapping inside `AlignedEnsemble.export`.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-44 — The Stern-layer test re-solves the drawn slab

*Area:* verification. *Severity:* low. *Found:* PR #60 (WP30).

**Measured.** `test_stern_layer.py`'s generated-slab clause re-solves the slab it already drew.

**Resolved.** WP42 D13: `drawn_slab` module-scoped fixture in `tests/tier2/test_stern_layer.py`.

### REV-45 — The derived χ field has no export

*Area:* interface. *Severity:* low. *Found:* PR #60 (WP30).

**Measured.** WP31 shows χ in the GUI; no command exports it.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

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

### REV-48 — The 2WCD walk test copies its constants

*Area:* verification. *Severity:* low. *Found:* PR #67 (WP33), review finding 13.

**Measured.** `test_exclusion_2wcd_walk.py` copies constants from `test_exclusion_2wcd.py`, which
can drift apart.

**Resolved.** WP42 D13: consolidated `exclusion_2wcd` fixture in `tests/conftest.py`.

### REV-49 — AXISYMMETRIC is replaced repeatedly

*Area:* process. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** The same `replace(AXISYMMETRIC, …)` is repeated at several call sites.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-50 — _inner_wall_nm re-implements innermost_crossings

*Area:* process. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** `_inner_wall_nm` repeats the logic of `innermost_crossings`.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-51 — A redundant reopen and resolve in WP34's walk

*Area:* performance. *Severity:* low. *Found:* PR #72 (WP34), a review finding not acted on.

**Measured.** A case is reopened and resolved where the resolved case is already at hand.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-52 — deviations and SolveReporting are off the stage protocol

*Area:* interface. *Severity:* low. *Found:* PR #79 (WP36).

**Measured.** The protocol declares `name`, `describe`, `key` and `run`; `deviations` and
`SolveReporting` stay conventions of some stages.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

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

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

### REV-56 — The geometry editor's simplicity check runs on the Qt thread

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `gui/widgets/geometry.py`'s O(n²) `_check_simple` re-runs on every `_show_row`, 0.63 s
at 600 vertices. *Seed from refusal* and a rebuild drop unsaved edits without confirmation.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

### REV-57 — frame_times decodes every frame

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `structure/read.py`'s `frame_times` decodes every frame only to read its time, and no
PBC or RMSD gate catches a chain split across the periodic box.

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

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

**Resolves it.** WP43, the small fixes (§8.2.9 I1, I2).

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

**Open.** For the author: whether stage 10's key gains an algorithm revision that a number-moving
change bumps (re-pinning `SOLVE_HASHES` and invalidating stored solves), or the library version
recorded in the manifest is ruled sufficient.

### REV-72 — A supplied field's rule order travels beside its source as a second argument

*Area:* coupling. *Severity:* low. *Found:* PR #89 (WP41), the `/wp-ship` review at `d704e84`.

**Measured.** WP41 D2 threads `fixed_charge_rule_order` beside `fixed_charge` through
`single_rung`, `default_ladder`, `CoupledModel` and `PoissonModel`. PHY-19's one-rule NOTE then
holds only where every caller passes both: a caller passing `fixed_charge=field.assemble(scales)`
alone silently returns to NGSolve's order-3 estimate. `test_charge_quadrature.py` checks the call
sites in `physics/models.py`, not their callers.

**Open.** For the author: whether the charge object carries its own source term (one argument,
the rule inside it), a change to the model interface outside WP41's scope.

### REV-73 — Cross-leaf inertness is not checked

*Area:* physics. *Severity:* low. *Found:* PR #85 (WP42).

**Measured.** VER-71 probes single leaves from each model's base, but does not probe leaves rendered inert by another leaf's value (such as `variable_density` beside a `none` density correction, `dielectric_gradient_forces` beside no permittivity concentration fit, or wall distance with every wall part off).

**Open.** Phase 5 (§8.2.9 I3).
