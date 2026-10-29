---
findings:
  prefix: UT
  status: open
  areas: [install, cli, api, physics, numerics, docs]
---

# User-testing findings

The log of the sessions of [protocol.md](protocol.md). Each row is one finding, added as it happens;
the command and its output go in a section of its own below the table. The author rules the rows at
the second `/np-plan amend 4` (§8.2.7 G7).

**Severity** is `high` for a wrong or unusable result, `medium` for a task that needs knowledge the
documentation does not give, and `low` for friction. **Status** is `open` until the author rules it;
then `accepted` (fixed by the package its ruling names), `deferred` (carried by the `REV-nn` row its
ruling names) or `fixed`. The first round was ruled on 29 October 2026, at WP56's plan (§8.2.21).

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
| UT-01 | cli | low | accepted | §8.2.21 W3, WP56 | [No CLI command to visually inspect a generated mesh](#ut-01-no-cli-command-to-visually-inspect-a-generated-mesh) |
| UT-02 | cli | medium | accepted | §8.2.21 W5, W6, WP56 | [Geometric and meshing parameters conflated in `mesh cylinder`; undocumented parameter discovery and lack of separate geometry inspection](#ut-02-geometric-and-meshing-parameters-conflated-in-mesh-cylinder-undocumented-parameter-discovery-and-lack-of-separate-geometry-inspection) |
| UT-03 | cli | medium | accepted | §8.2.21 W2, WP56 | [`nanopnp inspect` default output dumps raw manifest, unusable for targeted queries (e.g. deviations)](#ut-03-nanopnp-inspect-default-output-dumps-raw-manifest-unusable-for-targeted-queries-eg-deviations) |
| UT-04 | cli | low | accepted | §8.2.21 W3, WP56 | [No CLI command to plot field heatmaps from a completed run directory](#ut-04-no-cli-command-to-plot-field-heatmaps-from-a-completed-run-directory) |
| UT-05 | docs | low | accepted | §8.2.21 W6, WP56 | [Unclear motivation and user use-case for the `reproduce` command](#ut-05-unclear-motivation-and-user-use-case-for-the-reproduce-command) |
| UT-06 | docs | medium | accepted | §8.2.21 W5, W6, WP56 | [Dual charge declaration in `field.yaml` triggers `PHY-19` gate abort when flipping sign, and undocumented grid `shape`](#ut-06-dual-charge-declaration-in-fieldyaml-triggers-phy-19-gate-abort-when-flipping-sign-and-undocumented-grid-shape) |
| UT-07 | cli | low | accepted | §8.2.21 W4, WP56 | [`nanopnp run` lacks progress feedback or live status during long solves](#ut-07-nanopnp-run-lacks-progress-feedback-or-live-status-during-long-solves) |
| UT-08 | docs | low | accepted | §8.2.21 W6, WP56 | [Inconsistent case naming in session 03 (`coarse.case.yaml` vs `wall-100.msh`)](#ut-08-inconsistent-case-naming-in-session-03-coarsecaseyaml-vs-wall-100msh) |
| UT-09 | numerics | medium | deferred | §8.2.21 W8, REV-156 | [Severe runtime scaling on moderate meshes (~16k elements) due to serial UMFPACK and 15-rung continuation ladder](#ut-09-severe-runtime-scaling-on-moderate-meshes-16k-elements-due-to-serial-umfpack-and-15-rung-continuation-ladder) |
| UT-10 | api | medium | accepted | §8.2.21 W4, W7, WP57 | [Python API exposes internal pipeline plumbing (`run_document`, `with_section`, `StageDescription`; `MOD-11`, `REV-145`)](#ut-10-python-api-exposes-internal-pipeline-plumbing-run_document-with_section-stagedescription-mod-11-rev-145) |
| UT-11 | docs | low | accepted | §8.2.21 W6, WP56 | [Undocumented thread-pinning behaviour in `sweep run` causes oversubscription concerns](#ut-11-undocumented-thread-pinning-behaviour-in-sweep-run-causes-oversubscription-concerns) |
| UT-12 | cli | medium | accepted | §8.2.21 W2, WP56 | [`nanopnp inspect` on a sweep dataset dumps raw JSON instead of tabular results and rectification ratios](#ut-12-nanopnp-inspect-on-a-sweep-dataset-dumps-raw-json-instead-of-tabular-results-and-rectification-ratios) |

## UT-01 · No CLI command to visually inspect a generated mesh

**Area:** `cli`. **Severity:** `low`. **Session:** `01-command-line`.

### Command and output

```console
$ nanopnp mesh cylinder --out pore.msh
mesh      pore.msh
hash      11ec286086b6c9a55a358301e3bc5daf5022400d7e4e6019aee9efd2b915b9de
elements  392 (215 vertices)
quality   min SICN 0.720, min gamma 0.677
domains   electrolyte, trans, membrane, cis
groups    {default: interface}

inputs:
  mesh:
    path: pore.msh
    format: msh41
    groups: {default: interface}
```

### Context and expectation

After generating a mesh with `nanopnp mesh cylinder`, a modeller's natural first instinct is to visually inspect the resulting geometry, boundary groups, and mesh resolution.

However:
1. The CLI provides no command or flag to display or export a plot of the mesh (e.g. `nanopnp plot pore.msh` or `nanopnp mesh view`). Standalone CLI figure export is specified under `FR-28` (`v0.7`, Phase 6).
2. Neither `01-command-line/README.md` nor the user guide ([docs/guide/meshes.md](../guide/meshes.md)) mentions how a user can view `.msh` files.

Viewing currently requires either:
- An external mesh viewer (e.g. opening `pore.msh` in the standalone Gmsh GUI).
- Using the Python API (`Case.load("pore.case.yaml").figure("mesh")` or `result.figure("mesh")` per `FR-30` when the optional `plot` extra is installed).
- Waiting until notebook-based sessions or the Phase 5 workbench (`§8.2.6 F5`, `§8.2.17`).

## UT-02 · Geometric and meshing parameters conflated in `mesh cylinder`; undocumented parameter discovery and lack of separate geometry inspection

**Area:** `cli`. **Severity:** `medium`. **Session:** `01-command-line`.

### Command and output

```console
$ nanopnp mesh cylinder --help
usage: nanopnp mesh cylinder [-h] [--json] [-v] [--log-file LOG_FILE]
                             [--traceback] [--pore-radius-nm PORE_RADIUS_NM]
                             [--membrane-thickness-nm MEMBRANE_THICKNESS_NM]
                             [--reservoir-radius-nm RESERVOIR_RADIUS_NM]
                             [--maxh-nm MAXH_NM] [--wall-h-nm WALL_H_NM]
                             --out OUT

options:
  --pore-radius-nm PORE_RADIUS_NM
                        lumen radius (default 2)
  --membrane-thickness-nm MEMBRANE_THICKNESS_NM
                        membrane thickness, the lumen's length (default 6)
  --reservoir-radius-nm RESERVOIR_RADIUS_NM
                        radius of each quarter-disc reservoir (default 10)
  --maxh-nm MAXH_NM     global maximum element size (default 4)
  --wall-h-nm WALL_H_NM
                        element size on the pore wall (default 0.35)
  --out OUT             the .msh file to write
```

### Context and expectation

When asked to mesh a cylinder in Session 01, a user immediately asks how to specify geometric parameters (pore diameter, length, reservoir dimensions) versus mesh discretisation settings (element size, grading).

Two distinct issues emerge:
1. **Discoverability:** While the user guide ([docs/guide/meshes.md](../guide/meshes.md)) documents `--pore-radius-nm`, `--membrane-thickness-nm`, `--reservoir-radius-nm`, `--maxh-nm`, and `--wall-h-nm`, neither `01-command-line/README.md` nor [docs/getting-started.md](../getting-started.md) mentions that geometry and mesh parameters are configurable via flags or directs the user to `--help` / `docs/guide/meshes.md`.
2. **Conflation of Geometry and Meshing (`IF-02`):** In FEA modelling, CAD/geometry definition is logically distinct from discretisation/meshing. While `nanopnp` separates them for protein structures (Stage 5 `region` CAD assembly vs Stage 6 `mesh` under `FR-10`), `nanopnp mesh cylinder` is designed under the `IF-02` generators NOTE as a standalone one-shot `.msh` input generator so idealised pores bypass the 6-stage structural pipeline (see also `REV-41`, ruled in `§8.2.18 T3`, and `REV-154`, where a supplied `.msh` ignores `numerics.mesh.wall_h_nm`). From a modeller's perspective, bundling geometry and meshing into a single CLI generator obscures:
   - How to define or inspect an idealised geometry object (diameter, length, reservoir size) independently of its mesh.
   - How `numerics.mesh.*` settings in `case.yaml` interact with (or are ignored by) a pre-generated `.msh` file supplied via `inputs.mesh.path`.

## UT-03 · `nanopnp inspect` default output dumps raw manifest, unusable for targeted queries (e.g. deviations)

**Area:** `cli`. **Severity:** `medium`. **Sessions:** `01-command-line`, `02-physics`.

### Command and output

```console
$ nanopnp inspect run-classical
run-classical/manifest.json
case                 {"hash": "...", "text": "...\n..."}
corrections          {...}
deviations           {"contributed": [], "count": 6, "switches": ["electrolyte.corrections.density: none", "electrolyte.corrections.diffusivity: none", "electrolyte.corrections.mobility: none", "electrolyte.corrections.permittivity: none", "electrolyte.corrections.steric: none", "electrolyte.corrections.viscosity: none"]}
environment          {...}
...
```

### Context and expectation

In Session 01 and Session 02, the user is instructed to run `nanopnp inspect <run-dir>` to verify run configuration, settings, and especially deviations from the validated model (e.g. verifying that `run-classical` lists each `none` correction as a deviation while `run-epnpns` lists none).

However, user feedback reveals that `nanopnp inspect` is currently ineffective for this workflow:
> *"Using `inspect` (even with the `--json` flag) as a user is rather pointless unless you know exactly what you are looking for. There is just too much information dumped into the console."*

Key problems:
1. **Information overload:** By default, `inspect <dir>` dumps `manifest.json`. The manifest is an exhaustive provenance record containing full case text, environment details, compiler versions, and stage hashes. Dumping this (even pretty-printed with `--json`) forces the user to manually scroll through hundreds of lines of JSON.
2. **Lack of a concise summary view:** A user typically inspects a run to answer high-level questions: *What model ran? Did it converge? What are the key quantities? Were there any deviations from the validated model?*
3. **Missing targeted query flags:** There is no way to ask for specific sections, such as `nanopnp inspect run-classical --deviations` or `--quantities`.
4. **No CLI run comparison (`FR-34`, `REV-136`):** To compare `run-epnpns` against `run-classical`, the user must inspect both independently and mentally diff hundreds of lines of JSON output. While multi-run comparison in the workbench is specified under `FR-34` (`v0.6`, Phase 5; see also `REV-136`, `§8.2.19 U3`), a CLI comparison mode (`nanopnp diff <run1> <run2>` or `nanopnp inspect --diff`) would directly show physical differences (e.g. `none` corrections, shift in transport numbers from 0.542 to 0.556).

## UT-04 · No CLI command to plot field heatmaps from a completed run directory

**Area:** `cli`. **Severity:** `low`. **Session:** `01-command-line`.

### Command and output

```console
$ nanopnp run pore.case.yaml --store store --run-dir run-pore
run      run-pore
record   run-pore/run.json
stage  9 case        computed 39ec1d528088    0.004 s
stage  6 mesh        computed e3e74ab44e4f    0.108 s
stage  8 materials   computed 2bb45a9694a4    0.003 s
stage 10 solve       computed 05434b9dd120   13.727 s
stage 11 qoi         computed 3e70bb198a1d    0.146 s
stage 12 report      computed 2fdd8a0b32dd    0.003 s
bias_V               0.05
clamp_activations    0
conductance_S        1.32456e-09
current_A            6.62279e-11
currents_A           {'Cl-': 4.07319e-11, 'Na+': 2.54961e-11}
eof_m3_s             2.28666e-23
indicator_band_nm    [-2.4, 2.4]
route_agreement      {'indicator_A': 6.62279e-11, 'reaction_A': 6.62283e-11, 'relative_difference': 5.94158e-06}
routes_checked       True
stabilisation_currents_A {'Cl-': 0.0, 'Na+': 0.0}
transport_number     0.384975
two_pi_included      True
```

### Context and expectation

After running a continuum solve with `nanopnp run pore.case.yaml`, the command-line interface only outputs scalar summary metrics (total current, conductance, transport numbers, and route agreement).

However, a nanopore modeller often wants to visualise spatial field distributions after a 2D-axisymmetric solve:
- Electrostatic potential $\phi(r, z)$ heatmap across the pore and reservoirs.
- Ion concentration distributions $c_i(r, z)$ ($\mathrm{Na}^+$, $\mathrm{Cl}^-$) showing accumulation, depletion, and double-layer structure.
- Fluid velocity field $\mathbf{u}(r, z)$ and electro-osmotic flow streamlines.
- Current density and ionic flux vectors.

Currently:
1. Adding `fields` to `outputs:` in the case YAML (`outputs: [summary, fields]`) exports `fields_omega.xdmf`/`.h5` and `fields_omega_w.xdmf`/`.h5` for external visualisation (`IF-07`), and `nanopnp.plot` provides `result.figure("solve")` in Python/notebooks (`FR-30`, requiring the optional `plot` extra per `CON-07` and `QR-09`).
2. However, the CLI provides no command (such as `nanopnp plot run-pore` or `nanopnp export`) to render or export figures from a completed run directory (`FR-28` is scheduled for `v0.7` in Phase 6 and was excluded from Phase 4 in `docs/plans/phase-4-polish-and-user-testing.md`, while interactive field visualisation is scheduled for Phase 5 under `§8.2.6 F5`).
3. Session 01 ("The command line: from a case file to a reproduced current") does not mention `outputs: [fields]` (`IF-07`) or how to view spatial solutions in Python/notebooks (`FR-30`).

## UT-05 · Unclear motivation and user use-case for the `reproduce` command

**Area:** `docs`. **Severity:** `low`. **Session:** `01-command-line`.

### Command and output

```console
$ nanopnp reproduce run-pore
directory run-pore
manifest  de4e18e30e5e4c8ea4e89b7ee5777bb490a67071aebaecfb972cb49299ca723c
compared  12 quantities at rtol 1e-06
worst     0.000e+00
result    reproduced
```

### Context and expectation

In Session 01 step 5, the user is instructed to run `nanopnp reproduce run-pore`. The documentation explains that it "solves the archived case again, from nothing, and compares what it recorded".

From an end-user perspective, this raises immediate confusion:
- The finite-element solve and Newton continuation are deterministic on a given machine, so running the exact same case again in the same directory naturally returns the exact same numbers.
- A user naturally wonders: *Why does this command exist? Under what circumstances would a run NOT reproduce?*

The documentation does not explain the primary use cases (`FR-26`, `QR-08`):
1. **Third-party / Peer review verification:** A collaborator or reviewer receives the run directory (`manifest.json`, `case.yaml`, input files) on a different OS/hardware/architecture (e.g. macOS ARM64 vs Linux x86_64, or different BLAS/LAPACK builds) and verifies that the published numbers reproduce within numerical solver tolerance ($10^{-6}$).
2. **Input drift / tampering detection:** If an external input file (such as `pore.msh` or a PDB file) was modified on disk after the run, `reproduce` catches cryptographic hash mismatches against the manifest.
3. **Bypassing the cache:** Normal `nanopnp run` calls hit the cache (`store/`). `reproduce` forces a cold re-solve into an isolated temporary store to ensure the stored result is genuine and independent of continuation warm-starts or cache pollution.
4. **Library & environment upgrade verification:** Detecting whether upgrading dependencies (NGSolve, Python, NumPy) perturbed numerical results.

## UT-06 · Dual charge declaration in `field.yaml` triggers `PHY-19` gate abort when flipping sign, and undocumented grid `shape`

**Area:** `docs`. **Severity:** `medium`. **Session:** `02-physics`.

### Command and output

```console
$ sed 's/charge_e: -6.0/charge_e: 6.0/' ring.field.yaml > ring-pos.field.yaml
$ sed 's/ring.field.yaml/ring-pos.field.yaml/' epnpns.case.yaml > pos.case.yaml
$ nanopnp run pos.case.yaml --store store --run-dir run-pos
nanopnp run: the supplied field does not carry the charge it declares (producer leg, QR-03): its grid integrates to 6 e against a declared q_net_e of -6, a relative error of 2 against 0.001. This leg is the producer's: smearing, projection and the annular volumes
```

### Context and expectation

In Session 02 ("Then try"), the user is asked to flip the sign of the charge ring in `ring.field.yaml` and re-run.

The user encountered two points of friction:
1. **Dual charge declaration (`PHY-19`):** In `ring.field.yaml`, the charge magnitude and sign appear in two places:
   ```yaml
   q_net_e: -6.0
   provenance: {source: analytic}
   form:
     name: gaussian_ring
     parameters: {centre_r_nm: 2.6, centre_z_nm: 0.0, width_nm: 0.4, charge_e: -6.0}
   ```
   Under `PHY-19` (`SPECIFICATION.md` §4.4) and `QR-03`, `q_net_e` is the independent producer-leg conservation checksum (comparing the planar integral of the grid against the declared net charge, while omitting `q_net_e` skips the producer leg and runs only the consumer leg). However, neither `02-physics/README.md` nor the user guide explains that flipping `form.parameters.charge_e` requires also flipping (or omitting) `q_net_e`, causing Stage 7 (`charge`) to abort with exit code `4`.
2. **Undocumented grid parameters:** Under `form:`, the document specifies:
   ```yaml
   form:
     name: gaussian_ring
     parameters: {centre_r_nm: 2.6, centre_z_nm: 0.0, width_nm: 0.4, charge_e: -6.0}
     origin_nm: [0.0, -4.0]
     spacing_nm: [0.01, 0.01]
     shape: [501, 801]
   ```
   The meaning of `shape` is neither explained in the file comments nor in the session documentation. In fact, `shape: [N_r, N_z]` represents the discrete lattice dimensions in cylindrical coordinates $(r, z)$, spanning $r \in [0, 5]\text{ nm}$ ($501 \times 0.01\text{ nm}$) and $z \in [-4, 4]\text{ nm}$ ($801 \times 0.01\text{ nm}$).

## UT-07 · `nanopnp run` lacks progress feedback or live status during long solves

**Area:** `cli`. **Severity:** `low`. **Session:** `03-numerics`.

### Command and output

```console
$ nanopnp run wall-0175.case.yaml --store store --run-dir run-wall-0175
# No terminal output for ~28 s while solving all 15 continuation rungs; then prints:
run      run-wall-0175
record   run-wall-0175/run.json
stage  9 case        computed ...
...
```

### Context and expectation

When executing `nanopnp run <case>`, solving the continuation ladder and Newton iterations can take anywhere from tens of seconds to several minutes.

During this period:
1. The CLI provides zero progress updates on stdout or stderr by default. The process sits completely silent until the entire pipeline has finished and results are written.
2. Users have no indication of whether the solver is making progress through continuation rungs, stuck in heavily damped Newton steps, or hanging.
3. Although `run_case` and `run_document` in the core pipeline accept `progress: Progress | None` and `on_stage` / `on_solve` callbacks, the CLI `_run` handler does not connect them to any terminal progress bar, spinner, or rung ticker.
4. While passing `-v` (INFO level) logs continuation rungs to stderr, and `--log-file <path>` allows tailing a log, these flags are not mentioned in the session tutorials or getting-started guide, and log output to stderr is mixed with other diagnostic messages rather than providing clean progress reporting.

## UT-08 · Inconsistent case naming in session 03 (`coarse.case.yaml` vs `wall-100.msh`)

**Area:** `docs`. **Severity:** `low`. **Session:** `03-numerics`.

### Command and output

```console
$ nanopnp mesh cylinder --wall-h-nm 1.0 --out wall-100.msh
mesh      wall-100.msh
hash      9e249ce1c06efc9c3ac187291b696fba0cd3c297089829303ba37b14113bf4ea
elements  124 (75 vertices)
quality   min SICN 0.714, min gamma 0.686
domains   electrolyte, trans, membrane, cis
groups    {default: interface}

inputs:
  mesh:
    path: wall-100.msh
    format: msh41
    groups: {default: interface}
$ nanopnp run coarse.case.yaml --store store --run-dir run-coarse
nanopnp run: wall-distance admissibility gate failed: min d = -0.940116 at r = 3.56907e-05 nm, z = -2.23131 nm; NUM-34 requires min d >= -0.001 nm wherever a wall correction is active, and 9.748% of the 595 fluid samples are negative. The ion wall function's root is at d = -0.01 nm, so a field this far below zero reverses the sign of the diffusivity and mobility rather than attenuating them: refine the mesh at the wall (numerics.mesh.wall_h_nm), do not widen this gate
```

### Context and expectation

In Session 03, the mesh files written by the user are systematically named by wall size:
- `wall-035.msh`
- `wall-025.msh`
- `wall-0175.msh`
- `wall-100.msh`

The case files for the first three follow the same naming scheme (`wall-035.case.yaml`, `wall-025.case.yaml`, `wall-0175.case.yaml`). However, the case file for `wall-100.msh` is named `coarse.case.yaml`.

This naming divergence creates minor friction and confusion:
1. It breaks the parallel correspondence between case files and mesh files.
2. Naming it `wall-100.case.yaml` (or providing an explicit note explaining why it is singled out as `coarse`) would maintain consistency.
3. Note also that the `NUM-34` refusal message above instructs the user to adjust `numerics.mesh.wall_h_nm`, which a supplied `.msh` file (`inputs.mesh.path`) ignores; that diagnostic defect is tracked as `REV-154`.

## UT-09 · Severe runtime scaling on moderate meshes (~16k elements) due to serial UMFPACK and 15-rung continuation ladder

**Area:** `numerics`. **Severity:** `medium`. **Session:** `03-numerics`.

### Command and output

```console
$ nanopnp mesh cylinder --maxh-nm 0.175 --out wall-0175-maxh.msh
mesh      wall-0175-maxh.msh
elements  16562 (8471 vertices)
...
$ nanopnp run wall-0175-maxh.case.yaml
# Exceeded 5 minutes without completion; killed by user
```

### Context and expectation

When testing domain-wide refinement with `--maxh-nm 0.175`, the mesh contains 16,562 triangular elements. While this is a modest mesh count in continuum modelling (which COMSOL solves in a few seconds), the solve in `nanopnp` exceeded 5 minutes without completing.

Root causes in `nanopnp`:
1. **Coupled DOF count on fluid/solid spaces (`NUM-01`):** In `build_spaces` (`src/nanopnp/solve/state.py`), Stages 1–2 (`pb-linear`, `pb`) assemble scalar $P_2$ potential $\phi$ on $\Omega$; Stages 3 and 5 (`pnp`, 6 rungs) assemble $\phi$ on $\Omega$ plus $c_{\mathrm{Na}^+}$, $c_{\mathrm{Cl}^-}$ restricted to the fluid domain $\Omega_w$; and Stages 6–9 (`pnps`, 7 rungs) add $P_2/P_1$ Taylor-Hood velocity $\mathbf{u} = (u_r, u_z)$ and pressure $p$ on $\Omega_w$, reaching $\approx 1.4 \times 10^5$ coupled DOFs on a 16,562-element mesh.
2. **Serial direct solver bottleneck (`NUM-21`):** The default sparse direct solver in the pip wheel is SuiteSparse `umfpack` (NGSolve lacks built-in parallel PARDISO/MUMPS in its wheels; `CON-11`, `§8.2.12 M1`, `REV-115`). As benchmarked in `SPECIFICATION.md §6.6`, a single UMFPACK factorisation at $1.43 \times 10^5$ DOFs takes $\approx 4.4\text{ s}$ on a modern CPU. Unlike COMSOL, which uses multi-threaded Intel MKL PARDISO across all cores, UMFPACK is strictly single-threaded.
3. **15-rung continuation ladder (`NUM-18`):** Because `default_ladder` (`src/nanopnp/solve/continuation.py`) builds Stages 1–8 at `LADDER_START_CONCENTRATION_M = 0.05` M and ramps bias in `FINE_BIAS_STEP_V = 0.01` V increments, running `wall-0175-maxh.case.yaml` (`concentration_M: 0.1`, `bias_V: 0.05`, uncharged) executes **15 rungs** (1 linear + 14 nonlinear): `1-pb-linear`, `2-pb`, `3-equilibrium-pnp`, five `5-ramp-bias` rungs (`+10 mV` to `+50 mV`), `6-flow`, `7-corrections`, `8-steric` at `0.05 M`, and four Stage 9 salt-sweep rungs (`9-salt-0.05946M` to `9-salt-0.1M`). Across the 7 full coupled `pnps` rungs (Stages 6–9) and 6 `pnp` rungs (Stages 3 and 5), the solve performs 35–50 Newton steps.
4. **Repeated symbolic analysis and no Jacobian reuse (`REV-60`):** Every Newton step re-runs both symbolic and numeric UMFPACK factorisation (`REV-60`, deferred to Phase 6 under `§8.2.9 I3`), without holding the Jacobian across rapidly converging steps (modified Newton).

Suggested remedies to evaluate within specification constraints:
- Document `numerics.continuation: none` (which `NUM-18` provides for single-rung solves) or evaluate whether `NUM-18`'s fixed ladder needs the 4-rung Stage 9 salt detour from `0.05 M` to `0.1 M` when the pore carries zero fixed and surface charge.
- Address `REV-60` (reusing UMFPACK symbolic factorisation across Newton steps) or support modified Newton steps (reusing numeric LU factorisations when residual reduction is rapid).
- Evaluate iterative/preconditioned linear solvers where `NUM-22` (post-1.0) applies.

## UT-10 · Python API exposes internal pipeline plumbing (`run_document`, `with_section`, `StageDescription`; `MOD-11`, `REV-145`)

**Area:** `api`. **Severity:** `medium`. **Session:** `04-python-api`.

### Command and output

```console
$ python notebook.py
```

Relevant excerpt from `docs/user-testing/sessions/04-python-api/notebook.py`:
```python
from nanopnp import CancelFlag, Cancelled, Case, Store, dumps_case, run_document
from nanopnp.core.stages import StageDescription, register, walk_order
from nanopnp.io.case_paths import with_section

...
result = run_document(
    case.document,
    case_text=dumps_case(case.document),
    store=case.store,
    progress=lambda fraction, message: reports.append((fraction, message)),
    write=False,
)
...
swapped = case.with_(**{"inputs.mesh.path": finer["inputs.mesh.path"]})
edited = with_section(case.document, "charge")
```

### Context and expectation

In Session 04, the user walks through driving `nanopnp` via Python in `notebook.py` (stopping a run, progress reporting, swapping a mesh, editing sections, and adding a custom stage). Per `SPECIFICATION.md` §8.2.8 H2 and `docs/plans/wp55-user-testing-protocol.md` (D2), Session 04 was specifically designed to test `with_section` and `core.stages.register` to inform the author's ruling on **`MOD-11`** (`with_section and register are outside PUBLIC`) and **`REV-145`** (`No case builders by section before Phase 5`, deferred to Phase 5 with `MOD-11` under `§8.2.20 V3`).

User feedback summarises the core design friction:
> *"This example seems to do what it is supposed to do, but the current implementation of the API is anything but intuitive... most sections (basically all except 02) which I either do not readily understand by reading the code, or which seem very convoluted. Like the code was forced into an API role rather than native to it."*

Specific points of friction where internal implementation details leak into the public API:

1. **Missing execution-control forwarding on `Case.run` (`run_document` fallback):**
   ```python
   result = run_document(
       case.document,
       case_text=dumps_case(case.document),
       store=case.store,
       cancel=flag,
       write=False,
   )
   ```
   While `Case.run(self, *, upto=None, only=False, **edits)` already exists in `src/nanopnp/pipeline/handle.py`, it does not accept or forward `progress`, `cancel`, `on_stage`, or `on_solve` to `run_document`. Consequently, a caller needing progress reporting or cancellation must extract `case.document`, manually re-serialise it with `dumps_case(case.document)`, pass `store=case.store`, and pass `write=False`, instead of calling:
   ```python
   result = case.run(cancel=flag, progress=...)
   ```

2. **Case manipulation for ambiguous leaf names and sections (`MOD-11`, `REV-145`):**
   ```python
   swapped = case.with_(**{"inputs.mesh.path": finer["inputs.mesh.path"]})
   edited = with_section(case.document, "charge")
   ```
   While `Case.with_` (`field_path` in `src/nanopnp/pipeline/handle.py`) resolves unambiguous leaf field names directly as keyword arguments (e.g. `case.with_(bias_V=-0.05, concentration_M=0.1)`), leaf names that appear in multiple sections (such as `path` across `inputs.mesh.path`, `inputs.charge.path`, `inputs.eps_r.path`, and `structure.source.path`) require `**{"inputs.mesh.path": ...}` dictionary unpacking, and adding a section requires importing `with_section` from `nanopnp.io.case_paths` to mutate the raw `case.document` dict (`MOD-11`). Users expect first-class section/input builders on `Case` (e.g. `case.with_mesh(...)` or `case.with_charge(...)`, tracked in `REV-145`).

3. **High barrier to custom stage extension (`StageDescription`, `MOD-11`):**
   Registering a custom stage requires importing `StageDescription` and `register` from `nanopnp.core.stages` (`MOD-11`) and constructing a `StageDescription` with 12 low-level fields (`number=13`, `takes_workspace=False`, `takes_store=False`, `key_is_artefact=False`, `weight=0.01`, `needs_section=None`, etc.) plus a string import path `"selectivity:SelectivityStage"`.
   Furthermore, the stage class itself (`selectivity.py`) requires manually calculating content hashes and constructing low-level `Artefact` objects rather than implementing a high-level function `run(inputs) -> output`.

Conclusion: These findings directly inform the author's `/np-plan amend 4` ruling on `MOD-11` (§8.2.8 H2) and `REV-145` (§8.2.20 V3), as well as forwarding `progress`/`cancel` on `Case.run`.

## UT-11 · Undocumented thread-pinning behaviour in `sweep run` causes oversubscription concerns

**Area:** `docs`. **Severity:** `low`. **Session:** `05-sweep`.

### Command and output

```console
$ nanopnp sweep run --help
usage: nanopnp sweep run [-h] [--json] [-v] [--log-file LOG_FILE]
                         [--traceback] [--store STORE] [--index INDEX |
                         --wave WAVE] [--workers WORKERS] [--fail-fast]
                         [--csv]
                         plan
...
  --workers WORKERS    independent worker processes; defaults to the sweep
                       document's workers:, or 1
```

### Context and expectation

When running parallel parameter sweeps with `nanopnp sweep run --workers N`, users are concerned about thread oversubscription (e.g. whether each worker process will spawn $M$ BLAS/OpenMP threads, leading to $N \times M$ contending threads that thrash CPU cores).

In the implementation (`src/nanopnp/sweep/run.py`):
1. `sweep run` initialises its process pool using `pin_threads()`.
2. This automatically sets `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and `MKL_NUM_THREADS=1` in each spawned worker before any compute or linear algebra libraries are imported.
3. Thus, each worker process consumes 1 core, preventing oversubscription.

However:
- Neither `nanopnp sweep run --help` nor the documentation explains this thread-pinning behaviour.
- While `nanopnp run` accepts a `--threads <N>` argument for single runs, `sweep run` does not mention threading, leaving users unsure how resource allocation and core pinning are managed.

## UT-12 · `nanopnp inspect` on a sweep dataset dumps raw JSON instead of tabular results and rectification ratios

**Area:** `cli`. **Severity:** `medium`. **Session:** `05-sweep`.

### Command and output

```console
$ nanopnp inspect iv-grid/dataset.json
iv-grid/dataset.json
counts               {"ok": 8}
exit_classes         {"0": 8}
iterations           232
plan                 "..."
points               8
rectification        [{"bias_V": 0.05, "forward": 1, "forward_id": "pt-0001", "rectification": 0.909523, "reverse": 2, "reverse_id": "pt-0002"}, {"bias_V": 0.1, "forward": 0, "forward_id": "pt-0000", "rectification": 0.838462, "reverse": 3, "reverse_id": "pt-0003"}, {"bias_V": 0.05, "forward": 5, "forward_id": "pt-0005", "rectification": 0.993617, "reverse": 6, "reverse_id": "pt-0006"}, {"bias_V": 0.1, "forward": 4, "forward_id": "pt-0004", "rectification": 0.988846, "reverse": 7, "reverse_id": "pt-0007"}]
rectification_notes  []
rows                 [{"assignments": {"electrolyte.concentration_M": 0.1, "operating_conditions.bias_V": 0.1}, ...}]
schema               "nanopnp/sweep-dataset/v0.5"
seconds              ...
uncached             8
warnings             []
```

### Context and expectation

In Session 05 step 4, the user is instructed to run `nanopnp inspect iv-grid/dataset.json`. The documentation promises: *"inspect reads the dataset: its points, and the rectification ratio of each opposite pair."*

User reaction:
> *"The run seems to have worked, but I am not digging through the JSON output to find the relevant data..."*

Why this failed:
1. `nanopnp inspect` treats `dataset.json` as an arbitrary JSON file, printing top-level keys followed by unformatted, serialised JSON blobs (`json.dumps(value)`).
2. The user is presented with a screenful of stringified lists containing 8 point dictionaries (`rows`), assignments, manifests, and `rectification` objects without listing which salt concentration each `rectification` entry belongs to unless the user cross-references `forward_id`/`reverse_id` against `rows`.
3. While the `--csv` flag generated `iv-grid/dataset.csv`, the session documentation directs users to `inspect dataset.json` without mentioning how to view the CSV or providing a tabular summary.
4. An end user inspecting a sweep dataset expects an ASCII table showing the parameter grid, currents, and the computed rectification ratios ($|I(+V)/I(-V)|$), rather than being forced to parse raw JSON.
