# Review register

What a work package's implementation or review left open, one numbered item each, `REV-nn`,
until it is resolved (§8.2.8 H12). `/np-implement` and `/np-ship` add an item in the commit that
leaves it open: a confirmed review finding not fixed, a deferral to a later package, or a question
put to the author. The commit that resolves one sets its row `fixed`. The status of each item is in
[the findings log](review-findings.md), read at review (§8.2.13 N3); this page says what each one is.

A phase's close moves each closed item to [the archive](review-archive.md) (§8.2.50 AZ12).

Each item gives where it was found, what was measured, and what resolves it. Unlike the
[modularity findings](modularity-findings.md), the register is never closed: it is not one of the
two logs Phase 4's gate closes.

## Items

### REV-35 — _second_crossings loops in Python

*Area:* performance. *Severity:* low. *Found:* PR #46 (WP22).

**Measured.** The second-crossing search iterates in Python where it could be vectorised.

**Post-1.0.** A saving no gate needs (§8.2.9 I3).

### REV-41 — No prepare command, upto on reproduce, or region export

*Area:* interface. *Severity:* low. *Found:* PR #50 (WP25).

**Measured.** `nanopnp prepare`, `reproduce --upto` and a region export were left out of WP25 with
no later owner.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T3): `prepare` comes with structure preparation (FR-37); `upto` on reproduce with the workbench's Study package; the region export with FR-28, v0.7.

**Ruled in part** (§8.2.22 X1): the region's interchange document comes forward to WP57, as the geometry file of `nanopnp geometry cylinder`; `prepare` and `upto` stay as T3 placed them.

**Placed** (§8.2.31 AG1, 3 November 2026): `prepare` in WP5.16, which surfaces structure preparation; `upto` on reproduce in WP5.19, the Study suite.

**Fixed in part** at WP5.16: `nanopnp prepare` (item 3) and the workbench's Prepare tool (item 11). `upto` on reproduce stays deferred to WP5.19.

**Re-placed** (§8.2.34 AJ10, 5 November 2026): `prepare` in WP5.16, the Molecular suite; `upto` on reproduce in WP5.19, the Study suite.

**Fixed in part** at WP5.16's item 3: `nanopnp prepare` wraps `orient_pore` and writes the preparation record; `upto` on reproduce and the region export stay as placed.

**Fixed in part** at WP5.19's item 3: `reproduce(directory, upto=…)` and `nanopnp reproduce --upto` reproduce a run
stopped early to its last stage, each reached stage's key compared exactly
(`tests/tier2/test_reproducibility.py::test_ver35_a_run_stopped_at_its_charge_reproduces_to_that_stage`). The region
export stays with FR-28, v0.7.

**Placed** (§8.2.46 AV5, 20 November 2026): the region export, the part left, goes to Phase 6's provisional package *the exports*, with FR-28.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the exports.

**Placed** (§8.2.50 AZ4, 22 November 2026): its region export is that of Phase 6's tolerances and exports package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's tolerances and exports package.

### REV-45 — The derived χ field has no export

*Area:* interface. *Severity:* low. *Found:* PR #60 (WP30).

**Measured.** WP31 shows χ in the GUI; no command exports it.

**Deferred.** Phase 5, with the shell, the bundle and `MOD-13`'s CLI split (§8.2.9 I3).

**Ruled** (§8.2.18 T3): with FR-28, v0.7.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the exports*, with FR-28.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the exports.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's tolerances and exports package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's tolerances and exports package.

### REV-46 — Example 07 is not run at default sizes or on the ensemble

*Area:* verification. *Severity:* low. *Found:* PR #65 (WP32).

**Measured.** Example 07 runs at reduced mesh sizes on one frame, not at the default sizes or on the
50-frame ensemble.

**Deferred.** Phase 6, with the ensemble legs (§8.2.5 E1; §8.2.9 I3).

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the validation runs*, with the ensemble legs.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 11, the validation runs.

**Placed** (§8.2.51 BA5, 23 November 2026): Phase 12, the validation runs.

### REV-58 — The azimuthal reduction projects cells it then drops

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_003 (PR #49), *Leads not investigated*.

**Measured.** `symmetry/reduce.py` multiplies and projects all cells for every harmonic though only
bins with `K_j ≥ k` are kept, up to about 2× work. Correct.

**Post-1.0.** A saving no gate needs (§8.2.9 I3).

### REV-60 — UMFPACK repeats its symbolic analysis every Newton step

*Area:* performance. *Severity:* low. *Found:* CODE_REVIEW_002 (PR #44), *Leads not settled*.

**Measured.** `numerics/linear.py` redoes the symbolic factorisation on every Newton iteration; the
saving from reusing it is unmeasured.

**Deferred.** Phase 6, measured with the envelope's throughput (§8.2.9 I3).

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the speed-up*, after the assembly (REV-156).

**Placed** (§8.2.49 AY3, 22 November 2026): Phase 6, the speed-up, its last package before the close.

**Placed** (§8.2.50 AZ6, 22 November 2026): Phase 6's speed-up, with no fixed target. Its plan registers each threshold before it measures, on the code as the restructure leaves it; a cost over its threshold is fixed or carried.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's speed-up, its thresholds registered in its plan.

### REV-61 — No B-spline fit or HOLE cross-check of the contour

*Area:* interface. *Severity:* low. *Found:* PR #41 (WP20); verified open at `5559c7e`.

**Measured.** The optional B-spline fit of the extracted contour and the HOLE cross-check (B5) were
left out of WP20, and nothing in `src/` or the specification owns them.

**Deferred.** Phase 6, the HOLE cross-check (§8.2.2 B5) with VAL-05; the B-spline fit with it (§8.2.9 I3).

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the validation runs*, with VAL-05.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 11, the validation runs.

**Placed** (§8.2.51 BA5, 23 November 2026): Phase 12, the validation runs.

### REV-64 — A sweep's plan-time NUM-34 gate skips generated meshes

*Area:* verification. *Severity:* low. *Found:* PR #42 (WP21); verified open at `5559c7e`.

**Measured.** `sweep/plan.py` skips a generated mesh, which does not exist until the member's stage
6, so a NUM-34 violation on one surfaces at the member's solve rather than in seconds at plan time.

**Deferred.** Phase 6, with the envelope sweeps (§8.2.9 I3). The violation is loud, at the member's solve.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the validation runs*, with the envelope sweeps.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 11, the validation runs.

**Placed** (§8.2.51 BA5, 23 November 2026): Phase 12, the validation runs.

### REV-67 — Public registration functions for backend registries (MOD-11)

*Area:* interface. *Severity:* low. *Found:* WP39 (PR #84); verified open at `WP39`.

**Measured.** WP39 added six internal registration functions across `mesh/meshers.py` and
`numerics/linear.py` (`register_mesher`, `registered_meshers`, `create_mesher`, `register_solver`,
`registered_solvers`, `create_solver`), matching `physics/stabilisation.py`. None are exposed in
`PUBLIC` (D12).

**Deferred.** Phase 5, evaluated with `MOD-11` and the extension point public surface ruling (§8.2.8 H2).

**Ruled** (§8.2.18 T3): with the composer phase and MOD-11.

**Placed** (§8.2.46 AV5, 20 November 2026): the composer's phase, with MOD-11.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 8, the composer.

**Placed** (§8.2.53 BC5, 24 November 2026): Phase 6's installed packages, after the kernel: an installed package declares its terms, corrections, shapes or solvers, and that package settles which registering names are public.

**Proposed** (WP6.09, 26 November 2026; [the kernel's design](../design/kernel.md), *Installed packages*): one public
registrar handed to each entry point of the group `nanopnp.extensions`, the registries behind it private. The
installed packages' package settles it.

### REV-91 — About 400 tests name their requirement only in a comment

*Area:* documentation. *Severity:* low. *Found:* WP45.

The strip removed test docstrings. Where a test's requirement identifier lived only there, a one-line comment above the test keeps it; the test name still does not carry it (CLAUDE.md asks tests named for their requirement).

**Deferred** (§8.2.11 L10): renamed in a later package.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *V&V in CI*, which renames each test in scope for its requirement.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 11, V&V in CI.

**Placed** (§8.2.51 BA5, 23 November 2026): Phase 12, V&V in CI.

### REV-149: Notebook 01 prepares a structure but does not change its residues

Notebook 01's preparation form chooses the chains, the cis end, the residue range and the centroid
height, and hands them to `orient_pore`. It cannot change a residue (a point mutation, a removed loop),
which the author would like a later stage to offer. Deferred by §8.2.20 V13, at WP54's third checkpoint.

**Placed** (§8.2.46 AV5, 20 November 2026): the structural mutator's phase, which changes a residue in 3D (§8.2.17 S4).

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 9, the structural mutator.

### REV-151: `orient_pore` centres laterally on the registration residues, not on the pore axis

`orient_pore` fits the axis through the mean of the selected C-α atoms but rotates and translates about the
centroid of the registration residues. For a full ring these coincide. If a chain lacks some of the
registration residues, the structure shifts sideways and the pore axis lies parallel to z but off r = 0, so
`symmetry.axis: z` can refuse it. Stage 1 refits the axis, so the solve is probably unaffected. Fixing it
changes the prepared 2WCD bytes and the goldens of examples 06 and 07, so it needs the author's ruling.
Found by the `/np-ship wp 54` review and the `physics-reviewer` pass.

**Ruled** (§8.2.20 V15): deferred to its own package. Meanwhile `orient_pore` logs a warning where the
registration centroid is more than 0.1 nm off the estimated axis, and its docstring states the assumption.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the structure pipeline's loose ends*, which re-pins the prepared 2WCD and the goldens of examples 06 and 07 by ruling at its plan.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 9, the structure pipeline.

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

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the speed-up*, the assembly first (Z6).

**Placed** (§8.2.49 AY3, 22 November 2026): Phase 6, the speed-up, its last package before the close.

**Placed** (§8.2.50 AZ6, 22 November 2026): Phase 6's speed-up, with no fixed target. Its plan registers each threshold before it measures, on the code as the restructure leaves it; a cost over its threshold is fixed or carried.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's speed-up, its thresholds registered in its plan.

### REV-166: The Copilot hook probes are incomplete

Raised by the implementation of the Copilot host plan (`docs/plans/sessions/copilot-host.md` at the git tag `copilot-host`), built before its
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

**Placed** (§8.2.46 AV6, 20 November 2026): owned by the Copilot host's session plan (at the git tag `copilot-host`), run by the author on a WSL host before the close; the close carries it to Phase 6 if not run.

**Carried** (WP5.28, 22 November 2026): not run before Phase 5's close; carried to Phase 6, placed by its scope round (§8.2.48 AX1).

**Ruled** (§8.2.49 AY5, 22 November 2026): the author retires the Copilot host: "Retire, but add a tag in the
commit so we can find it back." Phase 6's cleanup removes the host's files and rules, a git tag marks the last
commit that holds them, and this row closes as `declined` in that commit. Nothing is run on Copilot until then.

**Placed** (§8.2.50 AZ4, 22 November 2026): WP6.03, the instructions and the Copilot host's retirement.

**Declined** (§8.2.49 AY5, 23 November 2026): WP6.03 removed the host's files, hooks and rules, so nothing is left to check. The git tag `copilot-host` marks the last commit that holds them.

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

**Placed** (§8.2.46 AV6, 20 November 2026): with REV-166, in the Copilot host's session plan (at the git tag `copilot-host`).

**Carried** (WP5.28, 22 November 2026): not run before Phase 5's close; carried to Phase 6, placed by its scope round (§8.2.48 AX1).

**Ruled** (§8.2.49 AY5, 22 November 2026): the author retires the Copilot host: "Retire, but add a tag in the
commit so we can find it back." Phase 6's cleanup removes the host's files and rules, a git tag marks the last
commit that holds them, and this row closes as `declined` in that commit. Nothing is run on Copilot until then.

**Placed** (§8.2.50 AZ4, 22 November 2026): WP6.03, the instructions and the Copilot host's retirement.

**Declined** (§8.2.49 AY5, 23 November 2026): WP6.03 removed the host's files, hooks and rules, so nothing is left to check. The git tag `copilot-host` marks the last commit that holds them.

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

**Placed** (§8.2.46 AV6, 20 November 2026): with REV-166, in the Copilot host's session plan (at the git tag `copilot-host`).

**Carried** (WP5.28, 22 November 2026): not run before Phase 5's close; carried to Phase 6, placed by its scope round (§8.2.48 AX1).

**Ruled** (§8.2.49 AY5, 22 November 2026): the author retires the Copilot host: "Retire, but add a tag in the
commit so we can find it back." Phase 6's cleanup removes the host's files and rules, a git tag marks the last
commit that holds them, and this row closes as `declined` in that commit. Nothing is run on Copilot until then.

**Placed** (§8.2.50 AZ4, 22 November 2026): WP6.03, the instructions and the Copilot host's retirement.

**Declined** (§8.2.49 AY5, 23 November 2026): WP6.03 removed the host's files, hooks and rules, so nothing is left to check. The git tag `copilot-host` marks the last commit that holds them.

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

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the speed-up*.

**Placed** (§8.2.49 AY3, 22 November 2026): Phase 6, the speed-up, its last package before the close.

**Placed** (§8.2.50 AZ6, 22 November 2026): Phase 6's speed-up, with no fixed target. Its plan registers each threshold before it measures, on the code as the restructure leaves it; a cost over its threshold is fixed or carried.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's speed-up, its thresholds registered in its plan.

### REV-180: The protonated density is refused under the SWANSON and PEOEPB force fields

Stage 2 takes each atom's radius from the CHARMM set of the §5.3.1 NOTE on `geometry.density`, by residue and atom
name. Under `charge.forcefield: SWANSON` PDB2PQR 3.8 writes AMBER hydrogen names (`H`, `HB3`, `H1`) that the set does
not hold, and on 2WCD residues 18 to 26 fourteen hydrogens resolve to no radius. `PEOEPB` failed on the same fragment.
WP5.03 therefore refuses `geometry.density.atoms: protonated` beside a produced protonation under either force field,
naming both keys, and the case sets `as_loaded` or `CHARMM`.

**Deferred**, owner unassigned: a protonated density under these force fields needs a radius set, or atom aliases,
that holds their names, chosen as an author ruling as the CHARMM set was. Found at WP5.03's plan, 3 November 2026.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the structure pipeline's loose ends*; the radius set or the aliases are put to the author at its plan.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 9, the structure pipeline.

### REV-181: Stage 2's header counts frame 0's atoms and reads an element from the first letter of a name

Under `geometry.density.atoms: protonated` the frames of the protonation table differ in atoms where a tautomer or an
acid state differs, yet `atoms.total`, `atoms.by_element` and `hydrogens` in stage 2's header count frame 0 only. The
element of an atom is its name's first letter after any leading digits, which gives `F` for `FE` and `C` for `CL`; the
table has no element column. The density is unaffected; the record understates the ensemble and misnames an ion.

**Open**, found at WP5.03's review: the author rules whether the table carries an element column (a change to the
artefact's schema) or the header lists every frame's counts.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the structure pipeline's loose ends*; the element column or every frame's counts is put to the author at its plan.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 9, the structure pipeline.

### REV-182: A polar hydrogen's kernel is narrower than the density grid's spacing

The CHARMM radius of a polar hydrogen is 0.2245 Å, so its width at sharpness 0.93 is 0.0209 nm against the default grid
spacing of 0.05 nm. The nearest-node deposit of such an atom is aliased: its term at its nearest node runs from near 0
to 1 with where it sits in the cell. The atom lies about 0.1 nm from its N or O, whose own term there is already about
0.71, so the 0.25 isolevel is not expected to move; WP5.03 did not measure it. The sharpness and the isolevel were set
on a density without these hydrogens.

**Open**, found at WP5.03's review: the author rules whether the polar hydrogens are measured against a finer grid
before the protonated default is used outside the reference cases.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the tolerances argued*, which measures the polar hydrogens against a finer grid before the protonated default is used outside the reference cases.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the tolerances argued.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's tolerances and exports package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's tolerances and exports package.

### REV-183: Fractional protonation through a customised PDB2PQR

WP5.04's charge edit changes a residue's net charge by an integer, on its titratable group (§8.2.31 AG9). A partially
(de)protonated state, a group carrying its charge averaged over its states at the pH, is FR-43's, a later phase
(§8.2.18 T6). The author, at WP5.04's plan: "If this is about partial (de)protonated states, I solved this in the past
using a custom version of PDB2PQR. This is something we can look into later, so write it down as such."

**Deferred** to FR-43's library package: it starts from the author's customised PDB2PQR, which the author supplies
then, and writes the physics into §4 first (T6). Found at WP5.04's plan, 3 November 2026.

**Placed** (§8.2.46 AV5, 20 November 2026): FR-43's library package, in a later phase.

**Placed** (§8.2.51 BA9, 23 November 2026): Phase 9, the mutator's phase, as a library package tagged v0.10. The author supplies the customised PDB2PQR by `/np-plan phase 9`; if it has not arrived, that round moves the package to after version 1.

### REV-186: A stored mesh beside a `structure:` section is refused

`inputs.mesh.artefact` (REV-62) names a stage-6 mesh in the store, and `structure:` or `geometry:` beside any
`inputs.mesh` is refused naming both, by the upstream rule of the §5.3.1 NOTE on `inputs:`. The stored mesh's frame
against a structure is unknown: nothing the case carries says where the structure sits in the frame the mesh was
made in, so a `structure:` beside it could be applied at the wrong offset without a gate to see it. The refusal is
safe, but a study cannot pair a molecular model that holds `structure` with a continuum model whose mesh is named
by hash.

Open: the author rules whether a stored mesh's frame is recorded and checked against the structure's, so that the
pair is refused only on a mismatch, or whether the refusal stays.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the structure pipeline's loose ends*; whether a stored mesh records its frame is put to the author at its plan.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 9, the structure pipeline.

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

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the model's open terms*.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the model's open terms.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's equations package, the model's open terms. The bound that stops its re-pin is put to the author at its plan, before any measurement.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's equations package, the model's open terms.

### REV-224: NUM-28's fluid consistency term omits the pore charge's force

NUM-28's consistency terms take `∇·T_M = ρ_ion E − ½|E|²∇ε` in the fluid. PHY-16 deposits `ρ_pore` on
every material, the fluid included, so in the fluid `∇·T_M` also carries `ρ_pore E`, and the domain
route loses `∫ ρ_pore E·w` wherever the shell of `w` overlaps a protein atom's Gaussian tail. Found by
CODE_REVIEW_039 (AUD-69). NUM-28 carries a NOTE naming this item.

**Accepted** (§8.2.37 AM2, 9 November 2026): owned by Phase 6. Measure `∫ ρ_pore E·w` against
`F^em` on an analyte case with a deposited charge, and either add the term or state that the support
of `w` excludes the deposit.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the model's open terms*.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the model's open terms.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's equations package, the model's open terms, with the step that shares the force terms with the weak form.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's equations package, the model's open terms.

### REV-225: Three numerics tolerances have no written derivation

Three §6 tolerances give no derivation and no pointer: the absolute residual floor 10⁻¹² of NUM-16,
the increment cap `‖δφ‖_∞ ≤ V_T` of NUM-16 and NUM-17, and NUM-08's "deviation from the analytic value",
which names no tolerance. NUM-26 and NUM-34, by contrast, argue their numbers. Found by
CODE_REVIEW_039 (AUD-52). §6 carries a NOTE naming this item.

**Accepted** (§8.2.37 AM2, 9 November 2026): owned by Phase 6. Measure the residual of a converged solve
in NUM-09's scaling, the largest accepted `‖δφ‖_∞` across the gated walks, and the error NUM-08's test
sees, and write each number's derivation beside its clause.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the tolerances argued*.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the tolerances argued.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's tolerances and exports package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's tolerances and exports package.

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

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the model's open terms*, whose re-pin of VER-62 takes the comment edit with it.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the model's open terms.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's equations package, the model's open terms, whose re-pin of VER-62 its comment edit rides.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's equations package, the model's open terms.

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

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the tolerances argued*, which touches §6, VER-03 and `knowledge/06`.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the tolerances argued.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's tolerances and exports package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's tolerances and exports package.

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
(§8.2.34 AJ8), with the screens in front of the author. WP5.16's round needed two, and its finishing item builds them
(`docs/design/reviews/2026-11-11-molecular.md`): a refusal opens its field and is listed among the problems, and
*Open structure…* lists the project's input files. At WP5.16's second collect
(`docs/design/reviews/2026-11-12-molecular.md`) the author ruled the Browse button "Both": *Open structure…* takes a
file from the system's own picker, copied into the project's inputs, and the workbench's own browser, which returns a
path, comes with the project dialogs. The project dialogs, the settings' rows, the menus, the Glossary, the log and
the frame's chrome wait for the round of a suite that needs them.
At WP5.17's collect (`docs/design/reviews/2026-11-12-continuum.md`) none was put: the Continuum screens open none
of them, and they wait for the Physics suite's round (WP5.18).
At WP5.18's collect (`docs/design/reviews/2026-11-16-physics.md`) the dark Electrolyte pick put the frame's chrome
(the title bar's count and palette button, the status line beside the panel's tabs, the rail's items), and the author
kept it as built, so those points are closed. The project dialogs, the settings' rows, the menus, the Glossary and the
log wait for the Study suite's round (WP5.19).

**Placed** (§8.2.46 AV2, 20 November 2026): the project dialogs, the settings' rows, the menus, the Glossary and the log are put at WP5.26's round, the polish pass.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then, and its round.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-236: Chords the operating system may claim, a command that cannot be unbound, and the glossary written twice

The WP5.15 review's doubts: on macOS, Option+Shift+digit types a character into a focused field, and a browser may
open its own help on F1 (the suite chords are the author's, §8.2.38 AN7); the per-key ✕ on the settings page resets a
chord to its default, and no control unbinds a command, though `commands.bindings` accepts an empty chord; the
glossary's 26 terms are written in `gui/web/glossary.py` and in the design document, and nothing checks that they agree.

**Open.** The keyboard pass over the workbench, WP5.26 (QR-16), takes the chords and the unbinding; the glossary's
single source is put to the author with it.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass, with its keyboard pass.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then, with its keyboard pass.
v0.6 ships with the gap, noted beside QR-16 (AW8).

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

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
it, from WP5.16 (§8.2.34 AJ8), with the screens in front of the author.

At WP5.16's collect (`docs/design/reviews/2026-11-11-molecular.md`) the author ruled two, which WP5.16 builds: the
settings are "Window over the tool. When working, I don't want to navigate away from the tool to change a setting",
and the folded bar shows the suites' icons with their state. On the changed table: "Let's also try a shorter list
version. The current table still takes up a lot of real-estate." Each Molecular tool's pane now marks its changed
values and filters to them; a list of one line per value is set beside the table at the next suite's round. The
palette's look and the help page stay open.

At WP5.16's second collect (`docs/design/reviews/2026-11-12-molecular.md`) the author marked the settings window
"Looking better. This will still need polishing to improve layout and spacing tightness. I would suggest having a
look at the settings pane of Claude Code as an example." WP5.16 sets each setting's control on the right of its title
and description, as asked; the pass over the window's spacing, with Claude Code's pane as the model, waits for
WP5.26's pass over the frame.

At WP5.17's collect (`docs/design/reviews/2026-11-12-continuum.md`): a changed Continuum value opens its tool at its
field (`?field=`), built in WP5.17's item 12 with the list of one line per changed value beside the table, which
its final render shows; the palette's look and the help page stay open.

**Placed** (§8.2.46 AV2, 20 November 2026): the settings window's spacing, the palette's look and the help page, at WP5.26's round.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then, and its round.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-238: The Prepare tool's axis and membrane are not dragged by handles

The design document's Prepare row drew the pore's axis and the membrane slab in the 3D view, dragged by their handles
(WB-14). Mol* ships unmodified and offers no handle that a pointer drags (CON-09), so WP5.16 draws both from the values
typed in the tool's pane and stepped by the arrow keys.

**Deferred** (§8.2.39 AO2, 11 November 2026): dragging by handles, with its keyboard equivalent already in place, goes
to WP5.26's pass over the canvases or a later tool package. Found at WP5.16's plan.

**Placed** (§8.2.46 AV5, 20 November 2026): dragging the axis and the membrane in Mol* goes to the structural mutator's phase, which edits the structure in the 3D view; Mol* ships unmodified until then (CON-09). Handles on the (r, z) canvas are WP5.26's.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 9, the structural mutator.

### REV-240: The author's notes on the Molecular digest that ask for a discussion

The author's notes at WP5.16's collect (`docs/design/reviews/2026-11-11-molecular.md`) that the package does not
settle:

- an ensemble's third view: beside one frame and the frames together, "a "B-factor" heatmap structure that represents
  the variation"; in the author's words it "needs a bit more discussion and research". What is drawn (a per-residue
  root-mean-square fluctuation over the aligned frames is the usual choice) and where it is computed, since `gui/`
  holds no analysis;
- colour maps beyond the two directions of the charge scale: "perhaps we can built-in support for custom colormaps"
  (WB-20's user-chosen maps). WP5.16 adds the setting for the direction only;
- the charge screen's views, at WP5.16's second collect (`docs/design/reviews/2026-11-12-molecular.md`): "perhaps
  we can think of creating an "overlay" view between the 3D structure, full 3D charge map, and the 2D-axisymmetric
  one (reduced, but then resolved again to make it pseudo-3D). To be thought about and discussed later." The (r, z)
  map turned about the axis is a picture of the reduced charge, so it shows what the reduction keeps and drops;
- one rule for the safeguards of actions that lose work: "it is good to think about such safeguards in general for
  the program (kind of like the danger zone in GitHub)". A build's *Cancel* stops at once, since each finished stage
  is already stored; deleting a model, a study or the store's entries is where a second step belongs.

**Open**, a question for the author: the variation view at the round of the suite that draws ensembles' results
(WP5.19's charge screen or Analysis); the charge screen's overlay with WP5.19's charge screen; the maps with the
plots' settings in Analysis; the safeguards before the first tool that deletes, with the project tree's actions.

*Carried at WP5.19's item 13* ([the record](../design/reviews/2026-11-18-study.md)). The charge screen moves to a bridge suite between Molecular and Continuum
(§8.2.42 AR8), so the overlay of the 3D structure, the 3D charge and the (r, z) map turned about the axis goes to that
suite's round (REV-259). The variation view and the maps go to WP5.21, which draws ensembles' results and plots. WP5.19
adds no tool that deletes, so the safeguards wait for the first one.

*Placed 19 November 2026* (§8.2.44 AT2, AT4): the overlay is drafted for WP5.20's round, the meso suite's, and built
there if kept: the deposit's charge in 3D and its mean about the axis, smoothed to 0.4 nm on a 0.2 nm grid, each as
isosurfaces over the structure.

*The overlay settled in WP5.20* ([the record](../design/reviews/2026-11-19-meso.md)): the author kept both volumes at their level, so the charge
screen's overlay is built. The variation view, the maps and the safeguards stay as carried above.

*The colour maps settled in WP5.21* (AU2): each field map and each comparison offers every Matplotlib colour map by name, and its reverse; a comparison records its map. The variation view and the safeguards stay as carried above.

**Placed** (§8.2.46 AV2, AV3, 20 November 2026): the variation view is WP5.23's, a colour a layer takes, computed in the library; the safeguards are WP5.27's, a second step before an action that deletes.

**Moved** (§8.2.47 AW1, 21 November 2026): the variation view goes with Phase 6's layers, WP5.23 until then; the safeguards with its guided route and new models, the first part of WP5.27 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the structure's layers, and the guided route and new models.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the structure's layers, and the guided route and new models.

### REV-241: What the final review of the Molecular tools left open

The GUI review and `impeccable`'s critique of the finished tools (WP5.16 item 12, render `shell-r2` at `def8265`; no
blocking finding) raised, beyond what the item fixed:

- ***Open structure…* opens no PQR** (Q09): a model's PQR is set in its file.
- **The charge screen**: with its pane on the left, the (r, z) map stands below the residue chips, and the map has no
  colour bar, axes or unit, so the switched colour direction cannot be read from it (WB-20, WB-26). WP5.19's screen
  (REV-209, REV-215).
- **The project tree does not mark the model a tool edits** where the project has no open item; the tree's empty
  groups show as bare rows.
- **The settings window covers the view** whose colours and background it changes.
- **A cancelled build is recorded as failed** in the queue's line.
- **The folded bar's state is a dot**, with the state in the button's name and tooltip, and names no project.
- **A dialog's backdrop does not dim the 3D canvas**; the tools' terms do not link to the glossary.

WP5.16's second collect (`docs/design/reviews/2026-11-12-molecular.md`) settled five of the points first listed: the
view that follows the typed values is REV-243, ruled for before Phase 5 closes; View draws a PQR model's atoms;
*Open structure…* gains the system's file picker; the author kept the warnings grouped by message, the paging of 15
rows and the empty 3D view; and a suite's icon opens its last tool, so the Molecular suite's page of five links is
gone.

**Open.** The PQR point goes with REV-242's new-model action: at WP5.17's plan the author ruled that an edited outline runs with its structure's charge, over the option that added a PQR opened in Prepare (§8.2.40 AP1). The charge screen's is WP5.19's; the rest wait for WP5.26's pass
over the frame.

**Placed** (§8.2.46 AV2, 20 November 2026): the PQR point is WP5.27's, with the new-model action; the frame's points are WP5.26's.

**Moved** (§8.2.47 AW1, 21 November 2026): the PQR point goes with Phase 6's guided route and new models, the first part of WP5.27 until then; the frame's points with its polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass, and the guided route and new models.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass, and the guided route and new models.

### REV-242: What the code review of the Molecular suite left open

[CODE_REVIEW_054](../code_reviews/CODE_REVIEW_054.md) on WP5.16 fixed 21 of its 28 findings, and `/np-ship` one
more (finding 16: Prepare reads the straightness as a warning, not a gate). These stay:

- **A molecular model without a `structure:` block cannot gain one** (finding 5). `Project.set_value` checks each
  value as a whole case: `structure.source.path` needs `structure.symmetry`, and the point group needs
  `structure.source`. Only `Project.new_model` makes such a model now; the workbench creates none, since its models
  come from an imported case. The way out is the author's: set several values in one write, or give the first
  structure a point group.
- **An imported full copy keeps its `variant_of.model`** (finding 15), naming a file of the project it came from,
  which in the new project is missing or another model; `changes()` then compares the copy with that model. Keep
  the name, drop it, or import the parent with the copy.
- **The Molecular tools re-key the walk on every refresh** (findings 17, 18). `MolecularModel.artefacts()` resolves
  the model and hashes its structure and trajectory files on each call, several times a refresh and once a second
  while a build runs; a scene request repeats about five keyed walks. Not measured; a cache needs the store's state
  in its key.
- **A refusal finds its field by its words** (finding 25): `molecular.refused_path` and `_GATE_PATHS` map a gate's
  message to a case path, so a message that names the channel goes to the axis. The root fix is a gate error that
  carries its case path, across every stage's errors.

**Open.** The first two the author ruled at WP5.16's `/np-ship` on 12 November 2026: "With the new-model action",
settled by the later suite that adds it, where the first structure is written as one block and an import decides
what becomes of `variant_of`. The third is measured with WP5.17's tools, which call the same reads, and cached if it shows (§8.2.12 M2).
The fourth waits for a pass over the stages' errors.

WP5.17's item 12 measured the third on 2WCD: a tool page's visit keyed the walk 3 to 12 times, 0.12 s to 0.32 s in
all, above the 0.25 s the plan set, so a pane's build, its refresh and each drawing request now key it once
(`BuiltModel.keyed_once`), 0.07 s to 0.13 s; a build's word read meanwhile drops what was read. The third is settled;
the other three stay open as ruled above.

**Placed** (§8.2.46 AV1, AV2, 20 November 2026): the first two points are WP5.27's new-model action, each put to the author at its plan; the fourth, a refusal that carries its case path, is WP5.25's.

**Moved** (§8.2.47 AW1, 21 November 2026): the first two points go with Phase 6's guided route and new models, the first part of WP5.27 until then; the fourth with its refusals package, WP5.25 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 6, the library's refusals; Phase 7, the guided route and new models.

**Placed** (§8.2.50 AZ3, 22 November 2026): the fourth point, a gate error that carries its case path, is that of Phase 6's error base.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's error base, for its fourth point; Phase 8, the guided route and new models.

### REV-243: Prepare's view does not follow the typed orientation

The axis and the membrane drawn in Prepare's view are those of the built, aligned structure: a typed tilt, azimuth,
flip or centre shows only after *Save prepared structure* (against §8.2.39 AO2; first raised in REV-241). Drawing
them as typed needs the source file's frame in the view, with the typed axis through its centroid and the leaflets
across it. The author, at WP5.16's second collect (`docs/design/reviews/2026-11-12-molecular.md`): "Instant feedback
would indeed be a nice feature, let's mark it as a QoL to be included before the end of the phase."

**Open**: built before Phase 5 closes, at the latest with WP5.26's pass over the frame.

**Placed** (§8.2.46 AV3, 20 November 2026): WP5.23, with the layers in every Mol* view.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's layers, WP5.23 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the structure's layers.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the structure's layers.

### REV-244: The author's notes on the Continuum digest that ask for a discussion

The author's notes at WP5.17's collect (`docs/design/reviews/2026-11-12-continuum.md`) that the package does not
settle:

- **A suite between Molecular and Continuum.** "Now that I see the division, perhaps the charge map and contour
  building need to go to their own suite that sits in between molecular and continuum. I would like to add this as a
  follow-up for more in-depth discussion." WP5.17 merges Contour into *Pore geometry*, which such a suite would take
  whole. The radius against z and the vertex list, which the design document's Contour row drew and the drafts did
  not, wait for the same discussion.
- **Region's CAD tooling.** "It should include some limited CAD tooling as well (ideally we import this from an
  existing package)." Drawing the (r, z) domain by hand is the sketcher (FR-42), a phase after Phase 5; which package
  it imports is put to the author with that phase's plan. WP5.17 draws each domain and selects it, and its values are
  typed (WB-41).
- **Subdivisions for meshing.** Preferring the tree of the mesh's parts: "I like this because it is also extensible.
  We may need a way as well to create subdivisions in boundaries and domains for meshing purposes as well." These are
  the refinement regions that the design document's Mesh builder lists as later (FR-11); in the tree each would be a
  child of the part it divides.

**Open**, a question for the author: the suite at a design round before the Study suite's prototype (WP5.19), whose
charge screen is the other half of it; the CAD tooling with the sketcher's phase; the subdivisions with the
refinement regions.

*Placed 18 November 2026* (§8.2.42 AR8; §8.2.43 AS1): the suite is WP5.20, the meso suite, and its round takes the
radius against z and the vertex list (REV-259).

*The suite settled in WP5.20* ([the record](../design/reviews/2026-11-19-meso.md)): Meso holds Density, Outline and Charge map. The author kept
Outline without the radius against z and the vertex list; the editor's keyboard path, which a vertex list would have
given, is REV-266's. The CAD tooling and the subdivisions stay as carried above.

**Placed** (§8.2.46 AV5, 20 November 2026): the CAD tooling and the subdivisions for meshing go to the sketcher's phase, with the refinement regions.

**Placed** (§8.2.49 AY2, 22 November 2026): Phase 10, the sketcher.

### REV-245: What the Continuum suite's final review left open

WP5.17's final render (244 shots, no page error and no contrast, non-text or target finding) was reviewed by the
`gui-reviewer` (6 major, 17 minor, none blocking) and by `impeccable`'s critique (24/40). Item 13 fixed the gate's
verdict and stage 4's under each tool's *Build*, the parts' sizes read from the built mesh, "default" for the table
with a glossary entry, the tool rows blocked while a file forms no case, the refused shot, the view's note while
building, *Seed* waiting for the map, the editor scrolled into view, the picked bar edged as the mesh is, 12 px
canvas text, the labels' words in the interface's face, the keys' swatches as their fills, *Mesh* as the tool's
name, and the design document's renderer and glossary rows. These stay:

- **The canvas's labels and keys.** Region's values on the drawing sit at the view's right edge, not at what they
  measure (the thickness across the membrane, the centre at its z, the reservoir's arc off view), and nothing shows
  that a label takes a typed value; a key lists lines out of view (the reservoir's boundary, the lumen radius) and
  covers the drawing's top; the equal scale centres the drawing, so up to 2 nm left of the axis is shown. With the
  handles dragged in the view and its keyboard pass, WP5.26 (QR-16).
- **The pane's layout.** In edit mode the stage 2 to 4 fields stay above the editor, its *Save* and *Discard* below;
  *Expose* is a row under each field and *Modified only* sits under *Build*; each tool carries a "Later:" banner.
  The critique asks for the inputs folded under the result, *Expose* as a toggle beside the field's reset, and the
  banners moved to Help.
- **Colour.** Pore geometry's outline is drawn in the accent, which WB-20 keeps for a selection; Region fills a
  domain at 55% and Mesh at full strength, so one material has two colours, and the names come in three orders.
  The critique proposes the outline in the plot's ink with a halo, and the materials as light and dark tokens drawn
  alike. A building stage's ● takes the warning colour a stale stage takes.
- **Words.** The changes list leads with the case path, not the field's label, and words an unset default two
  ways; the compact list does not show that it scrolls. The part card repeats the part's name as its field's label,
  and a domain's "size used" is its largest element. SICN, gamma, isolevel and the smoothing names link to no
  glossary entry (WB-25).
- **Progress.** A build says its stage, not how far it is or for how long (WB-23's "rung x of N").
- **Computed in the shell.** Region's domains are cut from the region's outlines with `shapely` in `gui/web/plane.py`,
  not read from the region artefact's faces; they agree with the meshed materials on 2WCD and the charged tube.

**Open**, a question for the author: the layout, the colours and the words at the next suite's round (WP5.18), with
the screens in front of the author; the canvas's labels and keys with WP5.26; the domains read from the artefact
when the region artefact records its faces' outlines.
At WP5.18's collect (`docs/design/reviews/2026-11-16-physics.md`) the author kept the colours ("Colors are fine") and
ruled the status colours (WB-42), which give a building stage's ● the info colour; the "Later" banners stay; *Expose*
leaves the Physics tools, its place elsewhere being REV-252; the words come under ASD-STE100, the Physics suite's in
WP5.18 and the rest under REV-254; the scroll cue and the glossary links wait for WP5.26.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass: the canvas's labels and keys, the pane's layout, the words, the progress, and Region's domains read from the region artefact's faces, library step first.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-249: A correction a physics model does not set reads none, and is not marked

Found at WP5.18's plan. A correction's schema default is `none` (`io/case.py:CorrectionChoice`), while the changed
mark compares a value with the validated `willems2020_nacl` and `borukhov` (`io/defaults.py:_default_of`). A physics
model that sets no correction therefore resolves to classical transport with every correction off, which the run's
manifest records as deviations, while the workbench's changed list (`mapping_changes`) lists only the values the file
sets, and the planned Electrolyte tool would show `none` with no mark. Every model of today's projects comes from an imported case,
which writes its corrections; a model `Project.new_model` makes writes none.

**Open**, a question for the author with the new-model action (REV-242): a new physics model written with the
validated corrections, or the mark read from the case the model resolves to.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.27, with the new-model action; the choice is put to the author at its plan.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's guided route and new models, the first part of WP5.27 until then; the choice is put to the author at its plan.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the guided route and new models.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the guided route and new models.

### REV-254: The stages' diagnostics and the other suites' words in ASD-STE100

At WP5.18's collect the author asked for simple sentences in ASD-STE100 and chose to rewrite the library's refusal
texts in the package. Item 9 rewrites the refusals of `pipeline/`, `io/` and `api/project.py`, and item 10 the Physics
suite's own words. Left: the gates' diagnostics and the stages' own errors in `mesh/`, `geometry/`, `charge/`,
`density/`, `structure/`, `numerics/`, `solve/`, `post/` and `sweep/` (about 550 raise sites); the CLI's messages; and
the Molecular and Continuum suites' own words, among them REV-245's: the changes list's lead, the two wordings of an
unset default, the part card's repeated name.

WP5.18's final review added the frame's own words: the Problems list and the Study suite's page give a refusal's whole
text, the Study page twice, with its case path written twice and no *Go to*, where a tool's card leads with the
refusal's words less its file and path; and the Study page still says "refused" where WB-40 says *blocked*.

[CODE_REVIEW_058](../code_reviews/CODE_REVIEW_058.md) found the cause under the words: a refusal is a sentence, and
three places read its place back out of it. The cards strip leading `X: ` prefixes (`gui/web/tools.py:_plain`), the
problems list takes the first dotted name that is a field (`api/project.py:_error_path`), and the Physics pane scans
the message for a field's path (`gui/web/physics_tools.py:problem_path`). A refusal that carried its case path and
its file as fields would end all three, with the pass over the diagnostics.

**Open**: WP5.26's pass over the workbench's words and keyboard, or a package of its own if the diagnostics need one.
The Study page's, WP5.19's.

*The Study page's part, fixed at WP5.19's item 14.* The Study suite's page gave way to its five tools at item 9. Each
tool's card leads with the refusal's plain words, less its file and path, with *Go to* its field, and says *blocked*.
The pane's status line says which value to correct. The rest stays with WP5.26.

**Placed** (§8.2.46 AV1, 20 November 2026): the stages' diagnostics and the command line's messages are WP5.25, a package of its own, each refusal carrying its case path and file as fields; the suites' own words go to WP5.26's sweep. The nine modules above hold about 440 raise sites; `physics/`, `materials/`, `symmetry/`, `core/` and the rest of `api/` hold about 110 more refusals, among them a correction's, and WP5.25 takes them too (CODE_REVIEW_066).

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's refusals package, WP5.25 until then, after the library's errors share a base; the suites' own words go with its polish pass.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 6, the library's refusals; the suites' words Phase 7's polish pass.

**Placed** (§8.2.50 AZ3, 22 November 2026): two steps. Phase 6's error base gives every library error one base that carries its case path and its file as fields, and moves the three readers of a refusal's sentence onto them. Its refusals package rewords the stages' diagnostics and the command line's messages after the restructure. The suites' own words stay Phase 7's polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's error base and its refusals reworded; the suites' words Phase 8's polish pass.

### REV-255: What the Physics suite's final review left open

WP5.18's final render (306 shots; no contrast, non-text or target finding; two shots failed under load and drew clean
on a second render) was reviewed by the `gui-reviewer` (22 findings: 9 major, 13 minor, none blocking) and by
`impeccable`'s critique (27/40, 13 findings). Item 12 fixed:

- the corrections table's heads over their boxes, and each model's and the parameter set's whole name;
- a condition's mathematics unbroken, and a unit never split;
- the definitions under an equation drawn at the equation's size;
- the flux's corrected coefficients written with their arguments, D_i(⟨c⟩, d) and μ_i(⟨c⟩, d), as ε_r
  and η are;
- the clamp's upper end named c_max, the parameter set's, not written as 5.3 M;
- a note on a density held constant left out;
- a refusal's card leading with the library's own words, less the file and path it starts with;
- a field a preview flags in the warning colour and ●, a blocking one with ✕;
- every switch a model needs set named in one line;
- the change note in the info colour;
- "uses this model" for "runs with this model";
- *Show mesh*'s reason when the study cannot run, and one key entry per colour with the region's outlines kept when
  the mesh is shown;
- a study's own value written under its field;
- the tool row whose value blocks a study marked ✕, or ● for a preview;
- the empty state's words, and disabled toggles drawn grey;
- a two-line hint that grows its row, and a *Go to* button on one line;
- KaTeX in the design document's renderer table, and its look-and-feel line.

`/np-ship` fixed two more, found while choosing round 2's picks: the flux's corrected bracket takes the parts that join
it on a line of their own, so `pnp`'s steric part no longer runs past the view's edge; and the empty Conditions' roles
box says no model is open.

These stay:

- **The (r, z) view in Conditions.** Its key covers the drawing's top right. It opens on the pore, where the
  reservoir's, cis and trans boundaries the key lists are out of view. An empty view's note sits at its foot, beside
  a *Fit* that acts on nothing. With REV-245's canvas labels and keys, WP5.26.
- **A study its physics model refuses draws no region.** The Conditions view resolves the shown case. A study that
  cannot run with its physics model, such as `pnp` with the flow on, forms no case, so neither its region nor its
  roles show, though the store holds the region. The region could come from the continuum model built alone, whose
  stage 5 keys as the study's. WP5.26, with the view.
- **The equations written for the corrections chosen.** Equations writes a model's terms with its switches. A
  property whose correction is none is written as X(⟨c⟩, d) under the note that it keeps X = X⁰, not
  as X⁰. With all five none, `epnp-ns` is not written as `pnp-ns`'s PHY-21 block. With the variable density on and
  the density's correction none, ϱ is constant as assembled, yet written ϱ(⟨c⟩) with the two notes that then say
  nothing; and the variable density's note says the inertia uses it with the inertia off (the physics review of item
  12). Under `electrolyte.driver: ionic_strength` the corrections read I = ½ Σ z_i² c_i, yet the equations and the
  clamp's note write ⟨c⟩ (the physics review at `/np-ship`); the one parameter set shipped, a 1:1 salt, refuses that
  driver (PHY-22's NOTE), so no case reaches it yet. A change to `physics/terms.py`'s composition, with a physics
  review: the next package that changes it.
- **The pane's layout.** The study's card stands above *Shown in*, which causes it. After a change of model, its note
  stands between the card and the *Model* row. The status line repeats the *Shown in* select. The symbols table is
  below the fold. Exposed values' *Name* head stands over the field's label, not its name, and its view is a two-row
  table. A solid's row and its field each carry the changed mark. The corrections' selects show no arrow, so the name
  fits. A number's unit sits below the value's baseline. At WP5.19's round, which reuses the pane.
- **Words.** The pane writes "C/m²" where the symbols table writes "C m⁻²". The plots' ⟨c⟩ draws as "(c)" in the
  interface's face, so "average concentration ⟨c⟩ (M)" reads as two brackets. The momentum and continuity notes ("equals
  PHY-07's … only where …") are the register the author called pedantic; they state what the model assembles.

[CODE_REVIEW_058](../code_reviews/CODE_REVIEW_058.md) left two more, for the view's package:

- **The shown case, resolved once.** A build of Conditions forms and resolves the shown case three or four times
  outside the model's cache (the pane's sections, the mesh's check, the solids, the view's request) and keys the walk
  each time; a supplied mesh is read from its file at each refresh, though the drawing caches it. One resolved case
  and one walk to the mesh, held per refresh, would serve all of them.
- **A plot's units in its keys.** The plot frame sends a graph's extent and points as `extent_nm` and `points_nm`,
  though they hold concentrations in M, distances and factors. The (r, z) frame's keys name nm; a plot's should name
  its axes' units, or none.

**Open**, a question for the author: the layout and the words at WP5.19's round; the view and the region with WP5.26.

*Ruled* by the author on 18 November 2026, at WP5.19's item 13 ([the record](../design/reviews/2026-11-18-study.md)): "Fix them in item 14". WP5.19's item 14
fixes *The pane's layout* and *Words* above. The view and the region stay with WP5.26, and CODE_REVIEW_058's two with
the view's package.

*The layout and the words, fixed at WP5.19's item 15.*
- *Shown in* stands above the study's card, and a change of model's note under the *Model* row.
- The status line says whether the study uses the model, without the study's name again.
- A link at the head of Equations reaches the symbols' table.
- Exposed values labels each box in itself: Name, From, To.
- A solid's rows carry the marks, not the field.
- The corrections' selects show their arrow.
- A unit sits on its value's line.
- The pane writes C m⁻², as the table does.
- The plots name the average concentration in words, and their marks write c.
- The momentum and continuity notes are one plain sentence each.

**Placed** (§8.2.46 AV2, AV5, 20 November 2026): the view, the region and CODE_REVIEW_058's two are WP5.26's; the equations written for the corrections chosen go to Phase 6's provisional package *the model's open terms*, which changes `physics/terms.py` with a physics review.

**Moved** (§8.2.47 AW1, 21 November 2026): the view, the region and CODE_REVIEW_058's two go with Phase 6's polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, AY6, 22 November 2026): Phase 7, the polish pass; the equations Phase 6's model's open terms.

**Placed** (§8.2.50 AZ4, 22 November 2026): its equations are those of Phase 6's equations package, the model's open terms.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass; the equations Phase 7's equations package, the model's open terms (§8.2.50 AZ4).

### REV-257: The blend's nearest-solid jump carries no dielectric force

Found by the physics review of REV-250's fix at WP5.18's ship. Under a solid fraction, PHY-20's blend goes to the
`ε_p` of the nearest solid, an element-wise field (`materials/fields.py:nearest_solid_permittivity`). Where the
nearest solid changes inside the band where `χ > 0`, between the protein and the membrane, the blend jumps by
`χ Δε_p` across an element edge. PHY-23's volume terms differentiate `ε_p` as constant, so that jump's interface force
is not assembled. The domain route's Maxwell stress keeps it implicitly, so NUM-28's split is not exact where the
extension's support crosses such an edge. The size depends on how far `χ` reaches past the protein–membrane junction,
which has not been measured on ClyA or 2WCD.

**Open**: measure the jump's force on a smoothed 2WCD case with the switch on, then assemble it as an edge term or
blend `ε_p` smoothly. With the next package that changes PHY-23's terms.

**Placed** (§8.2.46 AV5, 20 November 2026): Phase 6's provisional package *the model's open terms*, which changes PHY-23's terms.

**Placed** (§8.2.49 AY6, 22 November 2026): Phase 6, the model's open terms.

**Placed** (§8.2.50 AZ4, 22 November 2026): Phase 6's equations package, the model's open terms.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's equations package, the model's open terms.

### REV-258: The 200 ms redraw, measured on a GPU, and the front end's share fixed

AG7 had WP5.19 measure the 200 ms redraw line (WB-23) on the author's machine with a GPU, and fix a miss by the front
end there. WP5.19's item 11 wrote `.claude/scripts/gui/redraw.cjs`, which clicks a residue's charged atoms on the
charge map 20 times and times the markers' paint and Mol*'s second frame. Headless on the container's software GL,
on 2WCD at 1440 × 900, it measured:

- the markers' paint, 297 ms median and 380 ms p95;
- Mol*'s second frame, 745 / 827 ms;
- Mol*'s own share, 434 / 487 ms.

Over five picks, the server took 167 / 243 ms of the markers' paint. Each pick keys the study's walk three or four
times, at about 45 ms each:

- `study_tools.py`'s `on_point` and `select` each call `StudyModel.charges()`, and `plane_url` calls `artefacts()`,
  outside `builds.keyed_once`;
- `pages.py`'s `study(name)` builds a new `StudyModel` per request, so `/api/study/{name}/charge/plane` keys it again.

The author did not run the GPU measurement, and proposed moving this kind of optimisation to a dedicated performance
package (§8.2.42 AR7).

**Deferred** to WP5.24, the performance package, placed after the Analysis suite (§8.2.42 AR7; §8.2.43 AS2). It
measures the line with `redraw.cjs --headed` on a GPU, holds one keyed walk per pick, the route reusing the pane's
read, and profiles any miss with `--trace`. The Phase 5 plan's criterion 6 goes with it.

**Re-placed** (§8.2.46 AV4, 20 November 2026): WP5.24, after the tree of results and the layers, whose views it times.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's performance package, WP5.24 until then, with the 200 ms measure and the author's session on a GPU; it times the restructured views.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the performance package.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the performance package.

### REV-261: What the Study suite's final review left open

WP5.19's final render (392 shots; no page error and no contrast, non-text or target finding) was reviewed by the
`gui-reviewer` (9 major, 15 minor, 7 doubts; none blocking) and by `impeccable`'s critique (26/40, up from the first
draft's 23/40). Item 17 fixed:

- Overview's *Set by*: the study, the model file that sets the value, or *default*; the whole case shown in place of
  the set values; the case's keys in ink, not the green of a passed state;
- Study setup's *Outputs*, a study's own key, counted and listed with the changes;
- Exposed values' view: *Model's value*, as Study setup names it, in the pane's figures; no unit written for a ratio;
  why its list is empty when the model's file forms no case; the select's prompt;
- the sweep's points: each point's state in the queue, its wave counted from 1, its stages in words; *Run sweep*'s
  reason when it is off; the adder's prompts;
- the run's rungs as a list in the pane, every column shown; no empty plot frame; *Run study*'s notice naming Runs;
  "no solve" for a record's threads where the run stopped before its solve;
- the conservation legs: each number unbroken, as a power of ten with the minus sign, the place under the leg;
- the charged tube's two atoms: a structure of fewer than two chains is not cut, and is framed to its width;
- the correction models' whole names in Electrolyte (REV-255's fix, lost at item 15);
- each part of a switch with the controls' edge; the group box on the panel, so its even rows' shading shows; a solid
  with no value saying *not set*; *One subunit* filled when pressed.

The charge screen's points go to REV-259's round. These stay, for WP5.26's pass over every suite:

- **The convergence plot.** One label meets the first marker, the x ticks step by 11 and the top decades crowd. Round
  2's collect moved its legend, which took a third of the view, below the plot, and with that width each band
  from rung 4 on carries its number ([round 2](../design/reviews/2026-11-18-study-2.md)). The plot frame's labels
  and keys go with REV-245's, in `plane.js`.
- **Numbers in words and units.** Overview's physics table writes the unit in the label (*Bias, V* with 0.05), not
  50 mV; the sweep's values keep the hyphen-minus; a concentration's exposed range reads *any* where the schema
  refuses a negative value (WB-21).
- **Repeated words.** Every Study tool opens with the study's name and its pairing, above the picker that names it
  again; on a long name three lines. Exposed values' *Modified only* means "named or ranged", a second sense.
- **Layout.** The group box spans the label column where other boxes start at the value column, its marks inside it
  at the right; the sweep pane has three left edges; the *Go to* button cuts "in Conditions" to an ellipsis; with no
  project, Study setup's *Values* and *Variables* stand empty; New study's dialog uses floating labels where the pane
  uses labels at the left; mermaid's graph keeps its own face (WB-21).
- **Guards.** The axis's and an exposed value's × act at one click with no undo (WB-32), and *Create study* is
  enabled with an empty name.
- **Status colour.** A picked queue line draws its ✓ in the accent, not the state's colour; a field hint that names a
  blocking switch in Equations is grey (WB-42).

**Open**: WP5.26.

*The charge screen's points settled in WP5.20* ([the record](../design/reviews/2026-11-19-meso.md)): the key stands above a drawing it would cover,
its bar's ends apart; each charge unit as the panes write it, with no field identifier; a worst plane within its
tolerance dashed in the muted grey; the chip naming what it links; the pick keyed as its rings; Mol*'s mark kept;
*One subunit* framed on its chain. The points above stay for WP5.26.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-262: An exposed value's first name, and Exposed values' list as Study setup draws it

An exposed value's name is an identifier (`[A-Za-z][A-Za-z0-9_]*`, §5.3.1's NOTE on model files): the library's
lists name them after their leaves, `size_scale`, `concentration`, `bias`, and Study setup and Sweep show that name.
The critique asks for the field's label, *Size scale*, which the rule refuses. Two questions for the author:

1. An exposed value's name when first exposed: its leaf as now, with the panes showing the field's label beside a
   name left as the leaf; a name of words, which changes the rule; or asked for when the value is exposed.
2. Exposed values' view: the table it draws now, or Study setup's rows read-only, as WB-48's "the list as the Study
  suite shows it" may mean; with that, whether a value's name, *From* and *To* boxes become one box as WB-47's
  materials did.

**Open**: a question for the author, at WP5.26's round.

**Placed** (§8.2.46 AV2, 20 November 2026): put to the author at WP5.26's round.

**Moved** (§8.2.47 AW1, 21 November 2026): put to the author at the round of Phase 6's polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass's round.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass's round.

### REV-263: What code review 060 of the Study suite left open

[Code review 060](../code_reviews/CODE_REVIEW_060.md) fixed fourteen of its twenty findings, and one stands as D7 rules it. These stay:

- **A variable's unit.** Study setup's *New variable* takes a name and a value or an expression, and no unit, so every
  variable defined in the pane is dimensionless; one used at a field with a unit, as `boundary_conditions.bias_V`, is
  refused. A unit box, or a unit read from the typed text, is a control of the pane's design (finding 11).
- **The exclusion offset at load.** `check_exclusion_offset` runs in `resolve`, as a supplied outline's spacing is read
  there; the derived outline's half, which needs only `geometry.density.grid_spacing_nm`, left `check_document` with
  it. `Case.load` and the case editor's `commit` now accept an offset of at most `2 h_c` that they refused, and the
  refusal comes at resolve, as `Project.problems` and a build do (finding 12).
- **Sweep's plan, built twice.** `show_axes` and `sweep_view` each build the plan, resolving every point, and its
  forecast, keying every member's walk, on the event loop, and again at each move of the queue. A cache keyed on the
  sweep, study and model files would go stale as the store fills, which the forecast reads (finding 13).
- **Run records read each second.** Charge on the mesh's refresh signature calls `StudyModel.charge_record`, which
  stats and reads every run record of the study (finding 14).
- **The residue lookup's loop.** `ResidueCharges.at` calls `volume_density` once per near atom; the kernel is
  elementwise, but its signature takes floats (finding 15).

**Open**, ruled by the author on 18 November 2026 at `/np-ship wp 5.19`: all five go to WP5.26, the unit box as a
choice for its design round. None gives a wrong number; the offset is still refused before any build.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass; the unit box at its round.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then; the unit box at its round.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-265: A free list of the structure's layers in Meso's Mol* view

At WP5.20's round the author asked for display options in Meso's Mol* view: "having some display options like
molecular surface, sticks, spheres, etc. would be good. In cartoon mode, selecting a residue could change the style of
the side-chain to sticks or spheres for example." Of a picked residue, offered ball and stick, spheres or Mol*'s outline,
the author asked to "Solve this in a holistic way, offering the ability to change/configure the representations in a
flexible way", and of two designs chose "A free list of layers" ([the record](../design/reviews/2026-11-19-meso.md); WB-49). Each layer chooses
what it draws (everything, a chain, the charged residues, the residues the tool is about, a residue by name), its style
(Mol*'s cartoon, backbone, putty, ball and stick, spheres or surface, as MolViewSpec names them), its colour and its
opacity; the residues the tool is about are Charge map's picked residue with its copies, Density's named residues and
Outline's moved ones. The option put it at about three agent hours, as a package of its own. WP5.20 builds its first
layer: each Meso tool's *Structure* switch.

**Open**, ruled by the author on 19 November 2026: a package of its own, placed at the phase's next amendment; whether
Molecular's View takes the same list is decided there.

**Placed** (§8.2.46 AV3, 20 November 2026): WP5.23, after the tree of results and before the performance package. Molecular's View and Prepare take the same list.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's layers, WP5.23 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the structure's layers.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the structure's layers.

### REV-266: What the Meso suite's round left open

WP5.20's round ([the record](../design/reviews/2026-11-19-meso.md)) and its review left these, beside REV-265:

- **Outline's keyboard path.** The author kept Outline without a vertex list, so a vertex is picked only by a click on
  the picture, and live link 2's vertex table is not drawn (QR-16; FR-33; the review's F6 and F7). With WP5.26's
  keyboard pass over the canvas (REV-245).
- **The overlay's key and fields.** The scene has no key for the overlay's positive and negative surfaces, and its two
  level fields stand at different places, one label wrapping (Q5).
- **Mol* while a build runs.** Mol* is blank while a build runs, though the structure is stored (F13).
- **The conservation checks below the fold.** On 2WCD the checks stand below the pane's fold in every shot, under the
  residues, the view and the overlay (the review's route). With REV-245's pane layout.
- **The map's default share.** At the 99th percentile the 2WCD lattice still reads mostly as its middle colour with
  specks of charge: 90 % of its charged cells are under 31 C m⁻², a tenth of the clip (the final review's D1; the
  critique's first P1). A lower default share, or a floor on a charged cell's drawn size, is the author's call at
  WP5.26's round; *Map range* reaches either now.
- **The pane's scroll.** The picked residue, the strip and the link scroll out of the pane while the overlay is set
  (the critique's second P1): a pinned line naming the pick, and the lists scrolling on their own, with REV-245's
  pane layout.
- **The critique's polish.** Mol*'s toolbar covers a quarter of its 168 px; the residue buttons' edge on dark is
  `--line`, not `--control-edge`; the view's notes stand small at its foot; "kernel widths", "Kernel sharpness" and
  "Deployed on the mesh" link to no glossary entry (WB-25); stage 4's gate writes "contour gate, loop topology",
  with REV-242's pass over the stages' errors (the final review's F8).
- **A residue its first unit lacks.** Stage 1 accepts a chain holding part of the residues, and a residue is listed by
  its first unit's chain (`plot/data.py:ResidueCopies.group`), so one missing from that chain is named by a key none
  of its atoms carries: GLU 12 of chains B and C is listed as `A:12`. Its charge per copy, its copies and Mol*'s marks
  are right; only the name is wrong (the ship's physics read). A residue is to be named by its first present copy,
  alike in `ResidueCharges`, `ResidueAtoms` and `DensityAtoms`, whose keys the pane links.
- **The overlay with One subunit.** A scene of one subunit has no cut, so the overlay draws the whole ring's charge
  about the one chain shown (CODE_REVIEW_063). Whether One subunit shows the ring's charge, said in the pane, or no
  overlay, is a design question for WP5.26's round.
- **Density's list before the charge is built, under `as_loaded`.** Where stage 2 smears stage 1's atoms, a walk to
  stage 3 builds no protonation table, so the nearest residues are listed without names and a pick marks nothing
  until the charge is built (CODE_REVIEW_063). Mol* is blank there too, as it reads that table.

**Open**: WP5.26.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass; the map's default share and *One subunit*'s overlay at its round. A residue named by its first present copy is a library step of that package.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then; the map's default share and *One subunit*'s overlay at its round.
Outline's keyboard pick ships as a gap at v0.6, noted beside QR-16 (AW8); a vertex moved by typed values stands for
the Qt shell's drag until the pass (AW7).

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-267: What the Analysis suite's first review left open

WP5.21's review of its round's render (Item 12: the GUI reviewer's findings and the critique) fixed the computed
slope, the 3D bar's clipped minus, the typed probe, link 3's chip, the map's range and its 99th-percentile opening,
the pair's scale centred on zero over the fluid, each run's recorded numbers, the controls that do nothing in 3D,
Runs' clipped *Result*, the legends' dashes, the colour direction (WB-39) and the pane's scroll. At the round
(20 November 2026, WB-50) item 14 built the 3D view's range, framing and background, the map's outline, the
mirrored pair, *Solve again* and the rungs' table (the review's 10, 25 and 28). The tiles' layout, the probes'
place, the quantities shown and their order, and the charts' library (the review's 3, 16, 20 and 21; the critique's
5 and 15) went to REV-268's tree of results; the words to REV-269. These stay, WP5.26's:
- **Words and type.** "Changed" names the count and the run's deviations (17); the map's axes and the quantities
  are in the number face, minus signs are hyphens, a bias breaks from its unit, the Run select clips the bias (18).
- **Charts**, unless REV-268's library settles them: the convergence chart labels no rung 1 to 3, 5 or 8 and mixes
  10⁵, 0.01 and 10⁻¹¹ on its log axis (22; the critique's 14); a fresh model's flat factors are not drawn and its
  square-root ticks are not round (23); the series share the info and warn hues (the critique's 16).
- **The cut's line.** It is placed by a click and moved by typed values, not dragged (live link 3; added at the
  seventh amendment's review, 21 November 2026, where the design document cited REV-238 for it).
- **The no-run states.** The pointer to Study's Runs is no link (REV-269 words it), the refused state does not say
  Continuum's problem stops the study (26), and the empty state draws an empty box (27).
- **Frames.** A tile's frames nest three deep, a map's key stands on the data (the critique's 11, 12), and *Axes*
  does not say an axis was set (the critique's 13).
- **The final review's (item 14).** The renderer's *Open Controls* strip covers the positive half of the 3D view's
  colour bar, which has no 3:1 outline and serif numbers; the dark theme's 3D background is the renderer's grey
  (about `#595959`), not the canvas token; the 3D frame fits the close-up's diagonal, so the half at r < 0 is
  empty; Runs' rung table shows four of its seven columns in the pane, scrolling for the rest, and its notes repeat
  the columns; a current under 1 nA reads "0.04799 nA", not 47.99 pA (WB-21); "The map and the cut span" stays in
  3D; *Switch* in the glossary is a setting away from its default.
- **The ship's review (round 2's render, `ship-74fca57`).**
  - Runs' table of recorded runs clips its *Convergence* column at the tile's edge, as the rung table does.
  - The Quantities tile drops trailing zeros at four figures: "0.048 nA" stands beside "0.04799 nA", so two values
    of one precision look unequal.
  - A study with one bias draws its I–V point on an x axis that uPlot widens to 50–51 mV and ticks between. The
    note says to sweep the bias; the first review's 15 asked for no invented ticks.
  - The 3D bar's numerals on the dark grey are about 3:1 if black, unmeasured inside the renderer's frame.
  - *Difference* loses the pore at zero, its commonest value. The scale's middle colour stands 1.36:1 against the
    canvas where no fluid is (1.20:1 dark), under 1.4.11's 3:1. Hatch the region without fluid, or open
    *Difference* with *Outline* on; WB-50 did not rule the outline's default.
  - Overview's case listing colours its keys with a highlighter's green, not a token's, which reads as `--ok`. Rung
    notes write "3.13e-13" and "1e-06", not 3.13 × 10⁻¹³ (WB-21).
- **Doubts to check.** The I–V joins every run of a study, which may differ in more than the bias; Electrolyte's
  viscosity runs flat at 2.0, the plot's top, a clamp or a clip; the uncharged state shows a failed queue entry
  beside "no run yet"; figure export (FR-28) has no later-phase banner.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass; a chart's point that the library WP5.22 chooses settles falls to WP5.22.

WB-57 (21 November 2026) chose Plotly for every chart and every (r, z) view, `webgui` leaving: the **Charts** points
(the convergence chart's rungs and mixed powers, the square-root ticks, the series' hues), the 3D view's points of
item 14 and the one-bias I–V axis fall to WP5.22, which redraws each of those views.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then; the points that fell to WP5.22 go with its tree of results.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-268: Analysis as an editable tree of results, and the charts' library

At WP5.21's round the author asked for Analysis to be reorganised: "a lot of screen real-estate is being given to the
\"Results\" explorer tool settings. This should be more efficiently organized. Perhaps a good way would be to organize
the different views into an customizable editable tree, like it is done in COMSOL. Plots and graphs would be generated
using different plotting tools (surface, scatters, etc) based on existing/newly defined variables/constants. This will
likely need a new grilling and a dedicated WP." The probes are to stand "in a pane of their own, like in COMSOL", the
quantities shown are to be chosen, and uPlot (AU1) is to be revisited: "it seem to be rather limiting in
capabilities". Asked, the author placed it in "a new package, before speed" and chose to "decide with the tree"
which library draws the plots (WB-51).

What the round decides: the tree's nodes (a run or a comparison as data; groups of plots; probes; the quantities
shown; the cut), what a plot tool takes (a surface, contours, arrows, a line along a cut, a scatter, the I–V), how a
variable or constant is newly defined and where it is computed (in the library, never in the shell: QR-13), how the
tree is saved in the project, how it meets the link rulings (WB-06), and the library every plot uses: NiceGUI ships
Plotly (MIT) and ECharts (Apache-2.0), so either adds no dependency, and Plotly also draws (r, z) maps and contours.
The review's 3 (the tiles' layout), 16 (the quantities' order and words), 20 and 21 (the legend's "—", the shown run's
dot) and the critique's 5 and 15 are its.

The critique of round 2's render, at WP5.21's ship, adds five points for the round:
- frame a map on its data, r from 0 to the pore's reach, at equal aspect: the explorer's and *Side by side*'s r runs
  from −17 to 26 nm for data from 0 to 9 nm, and *Difference*'s from −25 to 35 nm;
- put the key and the note in the column that frees;
- draw *Side by side* as two columns of one tile: today the second run starts below the fold;
- take *Mirrored* as the model for every two-run view;
- name a run by sight, such as "+50 mV, ASP21N", not by eight hex digits.

Round 2's collect, on 20 November 2026 (WB-53), adds two points for the round:
- a true 3D view, the (r, z) field turned about the axis and cut open, as COMSOL's Revolution 2D draws it, is one of
  the plot types to put to the author. Asked, the author chose "Mesh now, 3D in tree": the view WP5.21 drew in 3D
  is the field on the solve's flat mesh, now named *Mesh*, and the library the round chooses draws the true one;
- the charts stand above the numbers ("Put graph at the top, values below.").

**Open**, ruled by the author on 20 November 2026: `/np-gui grill` on the tree with the author, then `/np-plan amend 5`
places its package after WP5.21 and before WP5.24. WP5.21 ships its tiles and uPlot as they are.

**Placed** (§8.2.46 AV4, 20 November 2026): WP5.22, the tree of results, opened by its design round (`/np-gui grill`), before the layers and the performance package (WB-51).

**Ruled** at the design round, 21 November 2026 (WB-54 to WB-63; `docs/design/reviews/2026-11-21-tree.md`): COMSOL's
branches, a comparison a Data node; one plot group or two side by side, the settings under the tree; every plot type on
the round's board P1, streamlines later; Plotly for every chart and every (r, z) view, uPlot, the canvas and `webgui`
leaving, all in WP5.22; a library list of variables and typed expressions, evaluated by the library; the tables as
bottom-panel tabs, the quantities checked and ordered; one `results.yaml` per project; *Shown run* taking an opened run
and following the newest; default plot groups from what the run provides; *Mirrored* first, and a run labelled by the
user or else named by what differs. The critique's five points are answered: the map framed at equal aspect with its
key beside it, *Side by side* kept as a view, *Mirrored* first, a run named by sight. Open until WP5.22 builds them.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's tree of results, WP5.22 until then, built on the restructured view area and results side; its round's rulings WB-54 to WB-63 stand but for the three the verdicts reopen (REV-273).

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the tree of results.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the tree of results.

### REV-269: The workbench's wording

At WP5.21's round the author asked to remove a way of wording "throughout the package": "\"Its rungs\" --> \"The
rungs\" … (other example: \"What the model shows.\", \"Study's Runs starts one\"). Let's discuss how." Labels name a
thing by its owner ("Its value", "Its mean about the axis"), headings are clauses ("What the map draws", "How the rows
make points"), and a pointer names a place in the possessive. Asked how, the author chose "Examples first" (WB-52):
sixteen strings across the suites, before and after, and a draft rule of five points were published for verdicts at
`https://claude.ai/artifact/Aa7jSmQKSrY6enQPZnMACy` on 20 November 2026. The author took the rule and each of the
sixteen: the rule stands in the design document's *Look and feel* (WB-52), and WP5.21's item 14 applied the sixteen
(*Rungs*, *Physics model*, *Boundary conditions*, *Value*, *Variable*, *Combine rows as*, Meso's
select named by its visible *Structure* (WB-49; WCAG 2.5.3), *Azimuthal mean*, and the pointers in Analysis as links to Study).

**Open**, ruled by the author on 20 November 2026: WP5.26 sweeps every other screen's text by the rule, with a check
that flags the patterns.

The ship's review of round 2's render found one of the sixteen false as it stands, for the sweep to put to the
author. Runs' "Nothing is queued. Click Run study to start a run." counts this study's entries alone, while the
status bar counts the whole queue. With another study's run queued, the two disagree; "No run of this study is
queued" would hold. Convergence's empty line repeats the sentence above a list of recorded runs, where "Pick a
recorded run to see its convergence" would say what to do. Units are written three ways: "Colours from (V)", "Bias,
V", and a bare "M" after a field in Setup.

**Placed** (§8.2.46 AV2, 20 November 2026): WP5.26, the polish pass, sweeps every other screen's text by the rule, with its check.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's polish pass, WP5.26 until then.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the polish pass.

### REV-270: A map reads its field linearly on each cell split in four

The physics review at WP5.21's ship (doubt 4): `post/fields.py:field_at` reads a field at a point linearly on the four
triangles of its P2 cell's split (D1), from the nodal values. A P2 field is quadratic in its cell, and a logarithmic
branch's concentration is the exponential of one, so a map, a cut and a probe read the solved field within the
split's interpolation error, `O(h²)` of its second derivative, exactly only at the nodes. On one run this is drawing.
On a difference of two runs on two meshes the errors do not cancel, and within a double layer, where the
concentration's curvature is largest, they can exceed the physical difference near the wall.

The remedy: find the point's parent cell as now, then evaluate the cell's six P2 basis functions there (straight-sided
cells, as the mesh is, make its barycentric coordinates the parent's), of the solver's variable: of `ln c` for a
logarithmic branch, exponentiated after. A map then reads the solved field itself at every point.

**Accepted**, ruled by the author on 20 November 2026 at WP5.21's ship: with REV-268's package, the tree of results,
which reworks the explorer's sampling, so the fix lands once. It would move earlier if runs on different meshes were
to be compared near the pore wall before that package ships.

**Placed** (§8.2.46 AV4, 20 November 2026): WP5.22, the tree of results.

**Moved** (§8.2.47 AW1, 21 November 2026): Phase 6's tree of results, WP5.22 until then; the survey's step R3 carries the read by the cell's own basis.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the tree of results.

**Moved** (§8.2.50 AZ2, 22 November 2026): the read by the cell's own basis is that of Phase 6's fields package, which rebuilds the reader and writes the fields file that its exports package exports; values read between nodes change at v0.7. Phase 7's tree of results keeps the explorer's own rework.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 7's fields package, for the read by the cell's own basis; Phase 8, the tree of results, for the explorer's rework.

### REV-272: Phase 5 closes early; Phase 6 opens with its scope, a cleanup and the foundations

The author asked, collecting the tree round's verdicts, whether the system is robust and extensible or a patchwork,
and when to refactor. Two read-only surveys answered ([architecture survey](architecture-survey.md), dated at
`8f4b09a`). The library's pipeline is sound: its stages, artefacts, store, layering and model and output registries.
Its results side is not: a run has seven representations and its `run.json` no typed model; the shell writes the
fields file; units are tabled four times; `post/` is helpers per screen; `Project` is 1,522 lines; a physics switch
touches about ten files. The shell's spine stops where the tree, the editor-like views and the properties pane land:
four fixed view slots, one state for every browser tab, polling, five form implementations, and numbers computed in
the shell against QR-13.

The record and the instructions are heavy, in words by `wc -w` at `8f4b09a`: the specification's text 141,436 and its
history 55,838 in 48 files; `decisions.md` 70,481; this register 48,572; the design document 16,184; the Phase 5
record 15,317; the `np-*` skills 12,073 in 19 files; `CLAUDE.md` 2,189. A work package's plan grew from about 2,900
words (WP5.05 to WP5.08) to about 4,900 (WP5.16 to WP5.21).

**Accepted**, ruled by the author on 21 November 2026:

- the restructure opens Phase 6, and Phase 5 closes as soon as it can, its remaining packages reviewed so that nothing
  is built twice;
- Phase 6 opens with a round that re-aligns its scope, then a general cleanup that removes conflicting and outdated
  decisions from the record and reduces the instruction files to their essentials, then the foundations;
- the library's deeper cleanup (`Project` split, one registry shape with switches as data, the force terms shared with
  the weak form) is one of Phase 6's first packages, which moves H5's MOD-08 from after v1.0;
- the boards' style is a Phase 6 package.

**To place** at `/np-plan amend 5`, which puts each move to the author. The proposal: Phase 5 keeps Qt's removal with
its capability check (criterion 3; M3), the application guide's minimum for the browser workbench, and the close.
WP5.22 (the tree), WP5.23 (the layers), WP5.24 (performance and criterion 6), WP5.25 (the refusals, with the library's
error base), WP5.26 (the polish pass) and WP5.27's route and new models move to Phase 6, each after the foundations
that would otherwise rebuild it; QR-10's observation (criterion 5) moves with the route. REV-271 is answered by the
same amendment. Then `/np-plan project` re-aligns Phase 6's scope, Z6's speed-up first included.

**Placed** (§8.2.47 AW1 to AW8, 21 November 2026), as proposed but for the trial: Phase 5 keeps WP5.27, Qt's removal
with a short guide (AW3), and WP5.28, the close, under their numbers (AW4); the tree of results, the layers, the
performance package, the refusals, the polish pass and the guided route with new models are Phase 6's provisional
packages, named by scope (AW1); QR-10's trial waits for a v1.0 release candidate (AW2); REV-271's target is restated at
the cleanup (AW5). At the amendment's review a typed vertex move was ruled to stand for the Qt shell's drag (AW7), and
v0.6 to ship with QR-16's keyboard gaps noted (AW8).

**Proposed for Phase 6's scope round**, by the author on 21 November 2026, each to be put to the author there. Until
that round rules, the models of `CLAUDE.md` and §8.2.38 AN8 stand.

1. **Measure the cleanup.** Set a limit on what a package session reads before it starts, and check it with `usage.py`
   before and after. Target the records more than the instruction files: `decisions.md`, this register, the
   specification's history and a plan's length are the large numbers above; the `np-*` skills and `CLAUDE.md` are the
   small ones.
2. **Start the cleanup with an audit.** The `claude-api` skill's `prompt-audit` command finds instructions a repository
   has outgrown or that contradict each other, and reports each with its file and line and a proposed diff. Run it
   over `CLAUDE.md` and `.claude/`.
3. **Order the foundations.** The library's come before the workbench's. The style is built into the workbench's shared
   parts (the form builder, the tree, the view area), not laid over today's widgets.
4. **Reorder Phase 6's existing packages.** The round revisits Z6's rule that the speed-up goes first. REV-224 and
   REV-257 join the library cleanup that makes the force code share the weak form's terms (the survey's step R9).
5. **Models by session type.** Ruling rounds, the scope round and the cleanup: Fable 5.2 at high effort, where a wrong
   call costs most. Implementation packages: Opus 5.5 at high effort, set explicitly because its default is medium.
   Mechanical or survey sub-agents: Sonnet 5.5. Fable's price is twice Opus's for input and output ($8 and $40 against
   $4 and $20 per million tokens), but a cached read costs the same, $0.20 per million, and cached reads dominate
   these sessions: the tree round used 87 M cached tokens and 0.32 M of output, about $24 on Opus against $30 on
   Fable before cache writes. A session is expected to cost a quarter to a half more, not double. Anthropic notes that
   over-prescriptive prompts lower Fable 5.2's output quality, one more reason for the cleanup to come first. The
   prices, the default effort and the `prompt-audit` command were checked against the `claude-api` skill's tables,
   cached on 3 November 2026.

**Ruled** (§8.2.49, 22 November 2026), at `/np-plan project`, the scope round. The work after v0.6 is three phases:
Phase 6, the cleanup and the library's foundations (v0.7); Phase 7, the workbench rebuilt (v0.8); and validation,
which the tool phases now precede as Phase 11 (v0.12) (AY1, AY2). The five proposals: 1 and 2, the cleanup is measured by
a reading limit taken from a baseline and opens with the audit (AY8); 3, the library's foundations are a phase before the
workbench's, and the style is built into Phase 7's shared parts (AY1); 4, the speed-up closes Phase 6, and REV-224 and
REV-257 join the equations package there (AY3, AY6); 5, Fable 5.2 runs the ruling rounds, the cleanup and each package's
plan and ship, and Opus 5.5 implements (AY7). This row stays `accepted` until Phase 6's cleanup and the two phases'
foundations land.

**Placed** (§8.2.50 AZ4, 22 November 2026): the cleanup is WP6.02 and WP6.03; the library's foundations follow, the restructure before the equations, in about ten packages (§8.2.51 BA4).

**The records cut** (WP6.02, 22 November 2026), in words by `wc -w` under `LC_ALL=C.UTF-8`, at `09b0d16` and
`f8f4248`: this register 61,248 to 20,690, its 220 closed items moved to [the archive](review-archive.md) (40,745);
`decisions.md` 75,431 to 25,751, its 1,079 closed rows on a second page (49,886); the Phase 6 plan 2,005 to 1,842;
`CLAUDE.md` 2,330 to 2,349. The baseline gave a fresh implementing window a median of 8,095 words of project text
read before its first edit, and the limit is 6,500 from WP6.03's merge (§8.2.50 AZ13).

**The instructions cut** (WP6.03, 23 November 2026), in words by `wc -w` under `LC_ALL=C.UTF-8`, at `e11ef54` and
`20bb8b4`. What an implementing session reads first: `CLAUDE.md` 2,349 to 1,505; `.claude/workflow/core.md` 1,366 to
899; `np-implement/wp.md` 1,276 to 739; `np-implement/SKILL.md` 103, unchanged; `current.md` 695, no longer read at
the start. Together 5,789 to 3,246. The finishing rules are read when they apply: `.claude/workflow/finish.md` 349
and `np-implement/finish.md` 682. Review 078 then cut `CLAUDE.md` to 1,497, under the plan's target of 1,500. The
29 Markdown files of `.claude/skills/`, `workflow/`, `rules/` and `agents/` hold 18,329 to 17,288. The limit is 8,000 words with the plan read whole (§8.2.50 AZ18), and a new session on the
cut read 7,186 before its first edit
([the Outcome](../plans/phase-6/wp6.03-the-cleanup-instructions-copilot-host.md#implementation-details)).

**Placed** (§8.2.53 BC7, 24 November 2026): WP6.02 and WP6.03, the cleanup, and the packages of the library's foundations, Phase 7 (§8.2.51 BA4); Phase 8, the workbench's foundations and the style.

### REV-273: The tree round's verdicts reopen where the settings stand, the views shown and the runs in Data

The verdicts on the tree round's boards ([the record](../design/reviews/2026-11-21-tree.md), *The verdicts*) keep
WB-54's branches, WB-56's plot types and WB-57's library, and reopen four points:

1. **Every run in Data** (T1's note): Analysis reaches all of a project's runs in a general way, a comparison one case
   of it; WB-54's Data and WB-61's single *Shown run* are reread. Proposed: Data lists every run by study, as COMSOL's
   datasets; a plot group names one run or more, two giving the three two-run views; *Shown run* stays one entry that
   follows the newest.
2. **An editor-like view area** (T2's note): splits resized in either direction, tabs of plot groups in each, the
   active one outlined. It replaces WB-55's one or two views, and is the frame's, for every suite (WB-13's docking).
3. **A properties pane of its own** (T1's worry, T3's note): the settings leave WB-55's stack under the tree. Proposed:
   tree, properties and view side by side, as COMSOL's Model Builder, Settings and Graphics, the properties about a
   fifth of the width.
4. **The render's size** (today's explorer's note): renders take the real estate of a 2560 × 1440 screen and are
   stored smaller. Proposed: 2560 × 1440 CSS pixels drawn at a 0.75 device scale (1920 × 1080 files), full-size crops
   of the panes so a reviewer reads 12 px text, and one 1440 × 900 shot per screen as the small-window check.

**Accepted** (§8.2.48 AX2, 22 November 2026): the author ruled at WP5.28's plan that the four points are Phase 6's
tree of results', put to the author at that package's design round, on boards drawn for the restructured frame
(REV-272). They would be ruled earlier if Phase 6's scope round needs the layout to size the foundations.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the tree of results.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the tree of results.

### REV-274: Five details the Qt panels show are carried to Phase 7

WP5.27's plan checked rows Q01 to Q41 of the Qt shell against the browser shell's code
([the plan](../plans/phase-5/wp5.27-qts-removal-and-the-short-guide.md), D1). Beside the two rows it builds (AW9, AW10)
and the deviations it corrects (its D4), five details of the Qt panels have no place in the browser:

1. **Protonation's frames** (Q27). `gui/web/molview.py:titration_states` gives the states of the first frame alone,
   and no row for a PQR without PROPKA's groups; the chain differences and the record's source and variant are not
   shown. `gui/charge.py:ProtonationView.frame` holds each frame's rows and stays for it. *Phase 7: the structure's
   layers.*
2. **The failing place of *Measure*** (Q18). The Outline lists each failed criterion; `gui/assess.py`'s
   `location_nm` is read by nothing, so the place is not marked. *Phase 7: the polish pass.*
3. **The dielectric on the mesh** (Q29). Charge map draws the deployed charge alone: `ChargeRequest.quantity` is
   never χ, and the dielectric's source and the materials are not shown. *Phase 7: the structure's layers.*
4. **The conservation view's figures** (Q30). The legs and the three charges are shown; the solid share, the charge
   per material, the axis guard's deficit and the boundary ring are not. *Phase 7: the polish pass.*
5. **A stage's record, in part** (Q13, Q14, Q21, Q22, Q26). Not shown: the alignment's point group as found, its axis
   and superposition; the density's grid record; the region's assembly record; the mesh's wall-size statistics and
   the places of its worst elements as figures; a stage's stored hash in the tool list. *Phase 7: the polish pass.*

Every number is in the run's record and on the command line.

**Accepted** (the author, 21 November 2026, §8.2.47 AW11): carried, and the Qt shell leaves without them.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, the structure's layers and the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, the structure's layers and the polish pass.

### REV-275: What WP5.27's screen review left open

`/np-ship wp 5.27` rendered the workbench at the PR's head and reviewed the three screens the package changed: the
queue's stage and rung with the run's log, Study setup's *More values*, and the results' deviations. The review
and its critique ([code review 069](../code_reviews/CODE_REVIEW_069.md) records the code findings) found no blocking
point. The ship fixed four: the deviations say "Unknown" where the manifest does not count them, the Log tab opens
on its newest line and follows a reader at its end, the queue line joins its stage with a dash rather than a second
colon, and a study's own value names its default. These stay open:

1. **A study's own value, by its path** (*More values*). It is labelled by its path's last part, typed as text, and
   the linear solver's registered words are not offered; *More values* lists every unfielded path in one picker.
   AW10 puts labelled fields with Phase 6's forms.
2. **The deviations' place** (the results explorer). The list stands at the foot of the quantities tile, below the
   fold, in hint text; nothing near the run says a deviation exists. Phase 6's tree of results (REV-268) redraws the
   tile.
3. **The log's reading** (the bottom panel). No filter by run, no time, and rows about 36 px apart against WB-18's
   30 px; the status line does not carry the running stage.
4. **The field viewer's colour bar** (explorer on the mesh; comparison on the mesh). Its low end and label lie under
   the renderer's controls strip, with no outline (WB-26). Older than this package; the fix is the host page's
   settings, as CON-09 requires.
5. **Wording and display, older than this package.** Two "done" queue entries read the same; the queued toast is not
   a link (WB-52, rule 4); "The study's own" and the placeholder "its value" (WB-52); the Rungs and Recorded runs
   columns clip without a sign; a current shown as 0.04799 nA, not 47.99 pA (WB-21); Runs says "Nothing is queued"
   twice beside "Queue: 2 done".
6. **The render's gaps.** No shot shows the deviations tile, with a deviation or with none; the light on-mesh shot
   shows the map; three dark shots are not taken (`shell-study-tube-running`, `-tube-log`, `-more-solver`); the
   mesh shots record no viewer readiness.

*Recommendation:* Phase 6's polish pass for 3 to 6, its forms for 1 (AW10), its tree of results for 2.

**Accepted** (the author, 21 November 2026): Phase 6 takes them as recommended; Phase 5 closes without them.

**Placed** (§8.2.49 AY1, 22 November 2026): Phase 7, its forms, the tree of results and the polish pass.

**Placed** (§8.2.53 BC7, 24 November 2026): Phase 8, its forms, the tree of results and the polish pass.

### REV-276: The radius set's notice names the removed bundle notice

`data/radii/pdb2pqr_charmm.yaml` carries PDB2PQR's copyright notice and says the licence's full text "is in
packaging/LICENSES-BUNDLE.md", which WP5.27 removed; the text is now in `src/nanopnp/THIRD-PARTY-LICENSES.md`, which
the wheel carries. The file's sha256 is part of every density's provenance (`density/radii.py:radius_set_digest`), so
editing the notice changes every stored density's key. Code review 069's finding 9.

*Recommendation:* repoint the notice when the radius set next changes for a reason of its own.

**Accepted** (the author, 21 November 2026): repointed at the radius set's next change.

### REV-278: `/np-plan project` as written cannot hold the rescoping round

Found by [review 073](../code_reviews/CODE_REVIEW_073.md) of the Phase 6 plan. §8.2.50 AZ7 holds the rescoping round
at `/np-plan project` after WP6.03 merges, with every requirement of §3, each tool and phase of §8.1 and v1.0's
content open. `.claude/skills/np-plan/project.md` plans "the phases after the phase in flight", reads §3's Release
column alone, "decides only what spans phases" (§8.2.16 R5) and changes the phase in flight only through
`/np-plan amend`. A session that follows it as written reads no requirement and repeats §8.2.49's re-ordering.

*Recommendation:* WP6.03, which changes the instructions, lets `project.md` hold a rescoping round. The round reads
§3's requirements, WP6.02's Outcome, the architecture survey and Phase 5's measured cost. It may open any requirement,
tool or phase, and AZ1 to AZ6 with them. It names `/np-plan amend 6` as the step that plans what it leaves of Phase 6.

**Proposed** (review 073, 22 November 2026): WP6.03, the cleanup's instructions; the author's approval of the Phase 6
plan accepts the placement.

**Fixed** (WP6.03, 23 November 2026): `.claude/skills/np-plan/project.md` gains *A rescoping round*. When a ruling
opens the project's scope, the round also reads §3's requirements, §8.1's tools and phases, OPN-08, the last
cleanup's Outcome, the architecture survey and the last closed phase's measured cost. It may open any requirement,
tool or phase with the rulings that ruling names, and it changes the phase in flight only by naming
`/np-plan amend <n>`.

### REV-279: At a ragged rim the channel's axis can lock about 0.6° off, as rounding decides

Found by WP6.01's dispatched [run 851](https://github.com/willemsk/nanopnp/actions/runs/45035649973), the Windows leg's
failure at result 620: `test_ver48_the_channel_axis_gates_fire` read the axis of the 8-fold test wall, tilted 12°
about x, as 11.38°. `structure/cavity.py:channel_axis` iterates a line through each plane's centre, and a plane's
centre is the mean of its widest enclosed spaces within 1 pm of each other. At a ragged rim those are n equal spaces
off the axis; a line a little off the axis breaks their tie, the mean of the few kept leans the way of the tilt, and
the iteration holds a second fixed point (WP5.16 recorded the weakness, [knowledge 04/15](../../knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md)).
On Linux a relative change of 1e-14 in the atoms' positions gives 11.381°, 11.446° or 11.780° for 3 of 8 draws, so
which fixed point a platform reaches is decided by rounding. Without the rim the axis reads 12.0000° in 19 of 19
draws. The three locked readings are 0.22° to 0.62° off, so a real pore whose rim no atom lines on the axis's side
may be given an axis up to about 0.01 rad off. The recovery test's walls, tilted 8° and 35°, keep the ragged rim and
read the axis within 1e-6 rad on the three platforms today; rounding could lock them too until the method is fixed.

*Recommendation:* make a plane's centre robust to a broken tie at a ragged rim, for instance by taking every
enclosed space a symmetry image of the widest, or by leaving out of the fit a plane whose tie splits, and re-measure
2WCD's axis (VER-48).

**Accepted** (the author, 22 November 2026, at WP6.01's implementation): the gate test tilts a wall without the
ragged rim, its precision kept; the method's fix waits for the rescoping round after WP6.03 (§8.2.50 AZ7), which
places it.

**Placed** (§8.2.51 BA8, 23 November 2026): a small package of Phase 6, firm. From v0.7 a structure with a ragged rim may be given an axis up to about 0.6° different.

**Numbered** (§8.2.52 BB1, 23 November 2026; §8.2.54 BD1, 24 November 2026): WP6.06, in build order after the orchestrator's package, which carries it (§8.2.53 BC3, BC10). Its plan is written after the author's ruling round on the ground-up review's proposals, which ruled no proposal on how a pore's axis is found (§8.2.53).

**Fixed** (WP6.06, 25 November 2026): the cause was not the tie this item names, and the bound was not 0.6°. Where the
atoms of a rim lie exactly in one plane, many tetrahedra there fix no centre, and `structure/cavity.py:_voids` dropped
the Voronoi edge of each face beside one; the rim's last plane then held no candidate on the axis, and the first,
tilted cut took one of the spaces beside it. On walls tilted 12°, 17 of 24 draws of the C7 and C8 walls locked, up to
0.84°, and one further draw read 1.05°. An edge now runs on past such a tetrahedron as it does past the hull, a
candidate is kept only where its clearance is its nearest atom's distance, and a triangulation Qhull refuses for
precision is joggled once (§8.2.55 BE4). None of 261 trial draws locks, 2WCD's axis moves by no bit, its limits stay
(BE1), and a channel case's stored first stage runs again once (BE2). The gate test tilts the wall with its rim again
(VER-48). A lumen with atoms on its axis still reads 7° to 8° off, with the straightness warning (§8.2.39 AO4;
[knowledge 04/15](../../knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md)).

### REV-280: The ground-up review's proposals wait for the author's rulings

Left open by WP6.04 (§8.2.51 BA13). [The ground-up review](ground-up-review.md) holds 25 differences between today's program and a design from nothing,
`GU-01` to `GU-25`, each with a verdict, and a card for each change, drop and add, in twelve groups. Nothing changes
until the author has ruled. The proposals for Phase 6 are: QR-11 dropped (GU-02); the two switches tried before a
package changes the workflow, with a target for the author's touches (GU-03, GU-04); a verification ledger (GU-06);
four clauses reworded and four spent sections of the workbench design removed (GU-07); a mesh-error estimate where
the answer is exact (GU-08); one comparison with the paper at the phase's close (GU-09, which asks BA3 again); and
the composed kernel's target stated, the names the workbench reads fixed, and numbers stored for the switches off
their default (GU-01). The other proposals name a later phase. [The challenge](ground-up-review/challenge.md) holds
each objection and its answer; an objection not met stands on its row.

*Recommendation:* rule groups 1 to 6 at the round, and leave groups 7 to 10 to the rounds of their phases.
`/np-plan amend 6` then plans what the rulings leave of Phase 6 (BA4, BA11).

**Ruled** (§8.2.53, 24 November 2026): the author ruled each of the 25 proposals or carried it with its owner, BC1 to BC24. The kernel is built in Phase 6; Phase 6 is split, so that the library's foundations are Phase 7 and the workbench's rebuild, with the composer's tool, Phase 8.

### REV-281: What a direct solve of the model costs at a million unknowns is not measured

Left open by WP6.04; a question only a trial settles (BA13). Two surveys of
[today's alternatives](ground-up-review/technologies.md) timed stand-in matrices on a shared container and disagree:
50 s to factor 653,000 unknowns in one, 21 s and 6.2 GB for 1.16 million in the other, with times that varied tenfold
between identical runs. Neither matrix is the model's. The engine's code takes PARDISO from pip's `mkl` on Windows and
Linux x86-64; that was read and not run. The answer decides QR-07's number (GU-07) and whether PARDISO is worth
offering as an option that a user registers (CON-08).

*Recommendation:* Phase 6's speed-up package factors the model's own Jacobian at 10⁶ unknowns with UMFPACK and with
PARDISO, on a named machine, and records seconds and gigabytes.

**Placed** (§8.2.53, 24 November 2026): Phase 7's speed-up, which also gives QR-07 its seconds and gigabytes (BC12).

### REV-282: Whether compiled weak forms and a threaded assembly cut the corrections' cost is not tried

Left open by WP6.04; a question only a trial settles (BA13). At 16,444 elements the full model takes 761 s on four
cores, 62 % of it the Jacobian's assembly on one thread, and the corrections make a Newton step 13 times dearer
(REV-156); on 392 elements the factor is six ([the evidence](ground-up-review/evidence.md)). The weak forms of a solve
are evaluated as uncompiled expression trees: `Compile(` appears once in `src/nanopnp`, in `validation/mms.py`. No
file enters the engine's `TaskManager`.

*Recommendation:* Phase 6's speed-up package tries both on REV-156's case before it sets its thresholds.

**Placed** (§8.2.53, 24 November 2026): Phase 7's speed-up, before it sets its thresholds.

### REV-283: Whether the corrections can switch on at the target concentration is not tried

Left open by WP6.04; a question only a trial settles (BA13). `solve/continuation.py:default_ladder` builds the state
at 0.05 M, switches the corrections and the steric term on, and then ramps the salt in four rungs, so six rungs carry
the corrections. All three blind designs step adaptively (GU-22). If the corrections can switch on at the target
concentration over FR-17's envelope, the salt ramp runs in the classical model. The physics reviewer names what could
make it fail: it is the largest jump of the coefficients (by PHY-12, the fluid's relative permittivity is 77.6 at
0.05 M and 51 at 3 M), and a classical state at high salt may pass the packing limit near a charged wall, where the
steric rung is refused (PHY-05, PHY-06). A new path ends at another iterate inside Newton's floor, so VER-62's
stored numbers would be re-pinned. The same runs can compare the log branch with primitive unknowns (GU-23), which
design C names among its least sure choices.

*Recommendation:* Phase 6's speed-up package runs the trial at the corners of FR-17's envelope and keeps NUM-18's
ladder unless every corner converges.

**Ruled** (§8.2.53 BC24, 24 November 2026): Phase 7's speed-up tries it. Its plan registers the pass marks before any run: every corner of FR-17's envelope converges, and no quantity of VER-62's walks moves beyond Newton's stopping tolerance. A full pass adopts the path and re-pins VER-62 with no further ruling; on any miss NUM-18 stands.

### REV-284: Whether Plotly pans a field map of 100,000 cells smoothly is not tried

Left open by WP6.04; a question only a trial settles (BA13). The workbench draws its charts with Plotly, and two
blind designs draw fields with vtk.js or a renderer of their own. The walk keeps today's choice (its row *The shell's
reading of artefacts*) without a measurement of a production-sized field map.

*Recommendation:* Phase 7's design study measures it with REV-287's trial.

**Placed** (§8.2.53 BC13, 24 November 2026): Phase 8's first package, the kit's trial.

### REV-285: Whether ParaView shows a second-order field without resampling is not tried

Left open by WP6.04; a question only a trial settles (BA13). IF-07 writes fields as XDMF with HDF5 at the exact
second-order node set. Design A writes HDF5 in the VTKHDF layout, whose specification calls itself incomplete. The
walk keeps IF-07 and cannot say whether ParaView shows either file's second-order field as it is.

*Recommendation:* the package of Phase 6 that argues the exports opens one field of each kind in ParaView.

**Placed** (§8.2.53, 24 November 2026): Phase 7's tolerances and exports package.

### REV-286: Whether Netgen meshes a wall layer at the Debye length is not tried

Left open by WP6.04; a question only a trial settles (BA13). NUM-30 sets the first wall layer at
min(0.05 nm, λ_D/5), and FR-11 allows structured boundary layers after version 1. The walk keeps Gmsh as an optional
backend because its size fields are the fallback if Netgen cannot mesh such a layer; knowledge 07/01 records that
Netgen's 2D boundary layers are immature.

*Recommendation:* the round names the package; GU-08's mesh ladder meets the question first.

**Placed** (§8.2.53 BC9, 24 November 2026): Phase 7's mesh-error package, whose ladder of finer meshes meets the question first.

### REV-287: Whether NiceGUI carries the workbench's hardest view and QR-16 is not tried

Left open by WP6.04; a question only a trial settles (BA13). ADR-004 chose NiceGUI on a spike of one screen, which
measured lines, a redraw, URL states, keyboard use, the install and the licence, and neither the ceiling of a design
nor accessibility. No blind design chose the kit: two chose a TypeScript application and one trame (GU-21). The
second challenger showed that measuring after the first rebuilt suite is the order of a sunk cost.

*Recommendation:* Phase 7's design study, in the second lane, builds the workbench's hardest view in the kit and
audits it against QR-16 before the rebuild starts.

**Ruled** (§8.2.53 BC13, 24 November 2026): Phase 8's first package builds the hardest view in the kit and audits it against QR-16, on pass marks `/np-plan phase 8` registers first; the rebuild starts after the author has seen the result. It runs in no second lane.

### REV-288: Nothing names the model of a carried package's main session

Left open by WP6.05; review 086's finding 5. Under `/np-carry` the main session calls the `code-review` skill for
the plan's review and for the ship's, and the review's agent takes the session's model: review 086's agent ran on
its session's Fable 5.2 with no model named. §8.4.5 puts a plan's review on Fable 5.2 and a plan names the model
that ships, but neither `np-carry/SKILL.md` nor §8.4.5 says which model the author starts the main session on. A
main session started on Opus 5.5 reviews the plan on Opus 5.5, and nothing reports it.

*Recommendation:* start every carried package on Fable 5.2, the model of `/np-plan`, of its review and of the
default ship; both reviews then run on it, whatever a plan names for the ship.

**Ruled** (the author, 24 November 2026): left open. The author decides it at the round after WP6.09, with
WP6.06's and WP6.08's measured lines (§8.2.53 BC10); until then the reviews of a carried package run on the model
its session was started on, which `usage.py`'s line names with its tokens.

**Fixed** (WP6.07, 25 November 2026): the author ruled the main session's model at WP6.07's plan, Sonnet 5.5 at
medium effort, which `np-carry/SKILL.md` names (§8.2.56 BF1), and the ship's review is `np-reviewer`, whose own file
fixes it on Opus 5.5 at high effort, whatever the session runs on (BF4). A plan has no review run (BF3).

### REV-289: The four helper agents of WP6.07 are not probed

Left open by WP6.07's item 1. Its plan probes `np-planner`, `np-builder`, `np-shipper` and `np-reviewer` with a
one-line task each: the tools each lists, the model and effort it runs at, and a start context under 30k tokens.
The session that wrote them cannot start them: an agent file is loaded when a session starts
([knowledge 07/26](../../knowledge/07-software-stack/26-what-a-claude-code-helper-can-do.md)). Until the probe, a
tool missing from a list, or an effort the front matter does not set, shows only when a helper fails.

*Recommendation:* WP6.08's `/np-carry` probes the four before its first helper and records the numbers in the
note.
**Fixed** (WP6.07, 25 November 2026): probed in the next session. Each of the four runs on the model and effort of
its file and starts at 12.6k to 12.8k tokens, beside 73k to 76k for a `general-purpose` helper; the numbers are in
[knowledge 07/26](../../knowledge/07-software-stack/26-what-a-claude-code-helper-can-do.md).


### REV-290: The builder and the planner agents list no GitHub tool

Left by WP6.07's review ([CODE_REVIEW_090](../code_reviews/CODE_REVIEW_090.md)). `np-builder` finds, opens and
updates the package's PR, and `np-planner` opens the plan's PR, but neither `.claude/agents/np-builder.md` nor
`np-planner.md` lists a GitHub tool, and `gh` is not logged in on the cloud host. Under `/np-carry` either helper
fails at its PR step. The reviewer's edit of the tool lists was refused by the permission check.

*Recommendation:* add `mcp__github__list_pull_requests`, `mcp__github__pull_request_read`,
`mcp__github__create_pull_request` and `mcp__github__update_pull_request` to both files, before WP6.08's carry.

**Fixed** (WP6.07, 25 November 2026, `ac4fb37`): `np-builder.md` and `np-planner.md` list the four PR tools.

### REV-291: A red CI that is neither a test nor a gate has no owner

Left by WP6.07's review ([CODE_REVIEW_090](../code_reviews/CODE_REVIEW_090.md)). §8.2.56 BF1's consequence sends
every red CI but lint, format or a flaky runner to Opus; `np-ship/wp.md` §5 and `np-shipper.md` send only a test or
a numerical gate to `np-builder` and bar the ship from any code fix. A `ruff`, `docs`, stale-lock or `mypy` failure
then belongs to no one.

*Recommendation:* follow BF1's consequence: the ship runs `ruff format` and `ruff check --fix` and reruns a flaky
runner once; every other failure goes to `np-builder`.

**Fixed** (WP6.07, 25 November 2026, `ac4fb37` and `5806145`): the author ruled for BF1's consequence. The ship
fixes only format and lint, with `ruff format` and `ruff check --fix`, and reruns a flaky runner once; every other
red CI goes to `np-builder` with its classified log. `np-shipper.md`, `np-builder.md`, `np-ship/wp.md` §5, §8.4.4,
§8.4.5 and `CLAUDE.md` say so.

### REV-292: The lean carry's tag number conflicts with §8.4.1

Left by the lean carry's review ([CODE_REVIEW_090](../code_reviews/CODE_REVIEW_090.md)), when the package was
numbered WP6.09 and the guard numbers WP6.07. From Phase 5, §8.4.1 numbers a package's alpha tag by its place in its
phase, so the lean carry, ninth, takes `v0.7.0-alpha.9`; its plan and `CHANGELOG.md` give `v0.7.0-alpha.7`, the
guard numbers' tag, so that versions on `main` keep rising when the guard numbers merge after it. §8.4.1 asks for
both, and they cannot both hold.

*Recommendation:* a ruling before the tag: either alpha numbers follow the merge order, amending §8.4.1 and
`CONTRIBUTING.md`, or the lean carry takes `alpha.9` and the guard numbers, merged after it, take none.
`/np-ship`'s *After the merge* waits for it.

**Fixed** (WP6.07, 25 November 2026, `f9f4554`): the author renumbered the record (§8.2.56 BF10). As §8.2.54 BD1
has it, the packages are numbered in build order: the lean carry is WP6.07 and takes `v0.7.0-alpha.7`, the guard
numbers are WP6.08 and the kernel's design WP6.09. §8.4.1 is unchanged.

### REV-293: Hand-off notes enter the plans index

Left by WP6.07's review ([CODE_REVIEW_090](../code_reviews/CODE_REVIEW_090.md)). `index_records.py` lists every
Markdown file under `docs/plans/phase-<p>/`, so a hand-off note shows in the plans index as "no status line", and
each hand-off rewrites the index.

*Recommendation:* `index_records.py` skips `*-handoff.md`.

**Fixed** (WP6.07, 25 November 2026, `5806145`): `index_records.py` skips `*-handoff.md` under `docs/plans/`.

### REV-294: The BF10 entry of holds-now names §8.4.1, which BF10 leaves unchanged

Left by WP6.07's review of its pulled-in findings ([CODE_REVIEW_091](../code_reviews/CODE_REVIEW_091.md)), a doubt.
`specification/history/holds-now.yaml` gives BF10 as holding in "the Phase 6 plan; the WP6.07 plan; §8.4.1", but
BF10's own row says §8.4.1 is unchanged: a reader of the entry looks for an amendment that is not there.

*Recommendation:* change the entry to `'the Phase 6 plan; the WP6.07 plan; §8.4.1, unchanged'`, or drop §8.4.1.

### REV-295: A pull request's duplicates check goes stale when main moves

Left by `/np-chore`'s review ([CODE_REVIEW_092](../code_reviews/CODE_REVIEW_092.md)), finding 9. CI's `docs` job runs
`duplicates.py` on a pull request merged with `main` as it was when the run started; GitHub does not rerun it when
`main` moves, so a number two pull requests share is caught on `main` after the merge. Where `main` moved before its land,
the skill rebases on it and runs the check again on the rebased tree (§8.2.57 BG5), which covers a chore, not a package.

*Recommendation:* the author sets "Require branches to be up to date before merging" on `main`'s protection, a
repository setting that no commit can make.

### REV-296: A failed land of a chore is fixed by the session, a red CI by np-builder

Left by the review of `/np-chore`'s ruled doubts ([CODE_REVIEW_093](../code_reviews/CODE_REVIEW_093.md)), a doubt. A red
CI's failure other than format and lint goes to a fresh `np-builder` (§8.2.57 BG3), but a failed land runs the same
`mypy` and tests and the session fixes it itself, on Sonnet 5.5 at medium effort where the chore touches no `src/` or
`tests/`. The ruling covered only a red CI.

*Recommendation:* a land failure other than format and lint follows the red CI's rule.

**Fixed** (`/np-chore`, 26 November 2026, with §8.2.58 BH1): a small finding, so the skill is corrected
and no row stays open. Of a failed land, as of a red CI, the session fixes only format and lint and a fresh
`np-builder` every other failure; §8.4.4 says the same.

### REV-297: The chore's worktree refusal names a branch pattern that package branches lack

Left by the same review, a doubt. The skill refuses where `git worktree list` shows a worktree on a `claude/np-carry-*`
or package branch, but a package branch has no name pattern: the core finds it from its pull request's title.

*Recommendation:* refuse on any other worktree whose branch holds commits past `origin/main`.

**Fixed** (`/np-chore`, 26 November 2026, with §8.2.58 BH1): a small finding, so the skill is corrected
and no row stays open. It refuses on any other worktree whose branch holds commits past `origin/main`; §8.4.4 says the
same.

### REV-298: The log branch has no case key and no line in the manifest

Left by WP6.08's plan ([D4](../plans/phase-6/wp6.08-the-guard-numbers.md)). NUM-02 provides the log-variable branch
"behind a flag". The flag is `physics/models.py:CoupledModel.log_variables`, which only
`models.create(..., log_variables=True)` sets: `io/case.py:Physics` and `pipeline/case.py:_model_options` hold no key
for it, so no case file reaches the branch. A run that takes it, through a resolved case whose `model_options` carries
the option, keys its solution apart and writes `log_variables: true` in the stored state's descriptor, but
`CoupledModel._deviations` omits it and the manifest names it nowhere (FR-25). Measured on example 02's ePNP-NS case,
the branch moves the current by 6.5e-6 relative. WP6.08 changes no schema and no physics, so its `guard-log` walk
enters at the resolved case and asserts the descriptor.

*Recommendation:* WP6.09's design, which makes a switch data, says whether the branch becomes a case key recorded as
a deviation, or stays a library option that the manifest still names.

**Proposed** (WP6.09, 26 November 2026; [the kernel's design](../design/kernel.md), *What the author rules*, 5): a case
key recorded as a deviation, a switch record that excludes PHY-23's switch. The round on the design rules it.

### REV-299: A rebase merge rewrites the shas that a package's ticks and Outcome name

Left by `/np-chore`'s review, [CODE_REVIEW_096](../code_reviews/CODE_REVIEW_096.md). A package's ticks and the plan's
Outcome name the branch's commits (WP6.08: `cdb67aa`, `645bc83`, the reviewed head `17e3111`, the fix `3f88e59`).
GitHub's rebase merge rewrites each, so those shas are not on `main`. The core (*Gate and push*, step 7) says the next
commit corrects the ticks a rewrite moved, and a merge is such a rewrite. The ship's final commit now brings the
documents to their merged state before the merge, so either a commit follows the merge, or the ticks name commits
that `main` lacks.

*Recommendation:* the core says a tick or an Outcome sha names the branch's commit, which the PR's
`refs/pull/<n>/head` keeps reachable, and that a merge's rewrite is not corrected. The other route is a merge that
keeps the shas, which changes how the author merges.

### REV-300: The stabilisation's wind leaves out PHY-23's decrement

Left by WP6.09's prototype ([the kernel's design](../design/kernel.md), *One expression and its three readers*).
`physics/stabilisation.py:advective_velocity` sums the migration, the steric part and the advection into `b~_i`, and
leaves out the drift of PHY-23's dielectric decrement, which `species_flux` keeps in the weak form's bracket. Under
`dielectric_gradient_forces` with a stabilised mode, the streamline and crosswind parameters and the approximate
residual of NUM-14 therefore read a drift that differs from the flux the form integrates. NUM-12's NOTE writes the
wind as `b_i = z_i μ_i ∇φ̃ + D_i β_i − Pe u`, without the decrement, and no clause says whether that holds under
PHY-23: NUM-14's reference settings were recorded for a model without the decrement, and no stored walk takes the
switch and a stabilised mode together. The prototype reproduced today's operator only by marking the decrement's
drift as one the stabilisation does not read.

*Recommendation:* keep it out, as today, and say so in NUM-12's NOTE, at the round on the kernel's design; reading it
is a re-pin of the stabilised modes under PHY-23, by ruling (§8.2.7 G10).

### REV-301: Three messages in mesh/ cite CON-04 for the half-plane where CON-01 is meant

Left by `/np-ship`'s review of WP6.09, [CODE_REVIEW_097](../code_reviews/CODE_REVIEW_097.md). The refusals of a
three-dimensional mesh at `src/nanopnp/mesh/adapter.py:386` and `:471`, and the one at `src/nanopnp/mesh/quality.py:200`,
name CON-04 (azimuthal averaging of a Cₙ structure) where CON-01 (2D-axisymmetric, steady state) states the
restriction. The citations predate WP6.09, which changes no code.

*Recommendation:* change the three identifiers to CON-01 in the next package or chore that edits `mesh/`; no behaviour
moves.
