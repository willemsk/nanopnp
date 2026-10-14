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

**Resolved.** WP46 D6: `DensityMap.read` refuses an interchange file whose spacing lies outside FR-04's 0.025-0.05 nm, saying a map is written in ångströms; `GRID_SPACING_RANGE_NM` lives in `density/map.py` and `pipeline/case.py` imports it.

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

**Resolved.** WP46 D6: `chain_characters` lives in `structure/ensemble.py` and `AlignedEnsemble.export` uses it; too many long-keyed chains raise `EnsembleFormatError` (exit 4) rather than `PQRError`.

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

### REV-57 — frame_times decodes every frame

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `structure/read.py`'s `frame_times` decodes every frame only to read its time, and no
PBC or RMSD gate catches a chain split across the periodic box.

**Resolved.** WP46 D5: a DCD's frame times are computed from its header without decoding a frame; XTC, TRR and NetCDF decode, their times living in frame headers. A chain split across the periodic box is refused naming chain, pair, frame and distance; the deposited 2WCD's largest consecutive-Cα distance is 0.3856 nm (`.knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md#11-the-authors-md-archive-measured`).

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

*Area:* performance. *Severity:* medium. *Found:* [WP43](../plans/wp43-development-loop.md) item 2.

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

**Fixed.** By removal ([WP44](../plans/wp44-simplify-the-loop.md), §8.2.11 L2): the commit hook runs all of Tier 1, so no
process-starting test is selected or widened and no commit falls back. The recorder, selector and map are deleted.

### REV-81 — Most past commits would fall back to the development selection

*Area:* performance. *Severity:* low. *Found:* [WP43](../plans/wp43-development-loop.md) item 2.

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

**Fixed.** By removal ([WP44](../plans/wp44-simplify-the-loop.md), §8.2.11 L2): no selection exists to fall back from.

### REV-82 — The push gate takes over 9 minutes against its 5-minute budget

*Area:* performance. *Severity:* medium. *Found:* [WP43](../plans/wp43-development-loop.md) item 10.

**Measured.** `gate.sh run` on tree `4d9c306` (2,213 tests, the development selection under branch
coverage and the `extended` walks without it, 4 cores, a quiet machine) took 555 s against
§8.2.10 J7's 300 s, beyond the 450 s its 50 % margin allows. WP43 D9 predicted the miss at 6.5 to
8 minutes: example 07's walk alone takes 421 to 477 s and cannot be shortened by the four ways of
§7.6's runtime NOTE without breaking its headroom rule. A follow-up after a pass is bounded below by
the same walk whenever the change reaches a process-starting test (REV-80).

**Fixed.** The author's ruling (J7), taken on the recommendation: `push_gate_s` is 600 s, the measured floor with room for example 07's walk (§8.2.10 J7 amended; VER-73; `.github/budgets.yaml`). The gate still logs the time and never fails on it. Splitting the walk stays open as a way to a lower figure.

### REV-83 — The longest-first test order is inert under xdist file scheduling

*Area:* performance. *Severity:* low. *Found:* [WP43](../plans/wp43-development-loop.md) item 10.

**Measured.** WP43 D8 collects files longest first so that `--dist loadfile` would start example 07
first. pytest-xdist re-sorts the files by their number of tests unless `--no-loadscope-reorder` is
passed, so the order only breaks ties. On a quiet machine, `--extended` without coverage on 4
cores took 534 s and 512 s with the order, 477 s without it and 474 s with the order and
`--no-loadscope-reorder` (`.knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md#122-where-the-time-goes-on-314-and-coverages-sysmon-core`): within the spread of like runs, and every run
bounded by example 07's 421 to 477 s. The shards' bin-packing reads the same record and is
unaffected.

**Fixed.** The sort is dropped from `tests/conftest.py`: collection keeps pytest's own order (`--ff`, `--nf` and fixture grouping stand), and `tests/durations.json` serves the shards' packing alone (`.knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md#122-where-the-time-goes-on-314-and-coverages-sysmon-core`).

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

Open: WP48 reads each of the 47, and either backs it with a test or gives it a footnote to a source; the ceiling falls with each.
