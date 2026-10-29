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
documentation does not give, and `low` for friction. **Status** is `open` until the second amendment
rules it.

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
| UT-01 | docs | medium | open | | No documented way to visually inspect a generated mesh from the CLI |
| UT-02 | cli | medium | open | | Geometric and meshing parameters conflated in `mesh cylinder`; undocumented parameter discovery and lack of separate geometry inspection |
| UT-03 | cli | medium | open | | `nanopnp inspect` default output dumps raw manifest, unusable for targeted queries (e.g. deviations) |
| UT-04 | cli | medium | open | | No CLI command to export or plot field heatmaps (potential, concentrations, velocity) from a run |
| UT-05 | docs | low | open | | Unclear motivation and user use-case for the `reproduce` command |
| UT-06 | docs | low | open | | Redundant charge definition in `field.yaml` and undocumented grid `shape` |
| UT-07 | cli | low | open | | `nanopnp run` lacks progress feedback or live status during long solves |
| UT-08 | docs | low | open | | Inconsistent case naming in session 03 (`coarse.case.yaml` vs `wall-100.msh`) |
| UT-09 | numerics | medium | open | | Severe runtime scaling on moderate meshes (~16k elements) due to serial UMFPACK and multi-rung ladder |

## UT-01 · No documented way to visually inspect a generated mesh from the CLI

**Area:** `docs`. **Severity:** `medium`. **Session:** `01-command-line`.

### Command and output

```console
$ nanopnp mesh cylinder --out pore.msh
mesh      pore.msh
hash      11ec286086b6c9a55a358301e3bc5daf5022400d7e4e6019aee9efd2b915b9de
elements  392 (215 vertices)
quality   min SICN 0.720, min gamma 0.677
domains   electrolyte, trans, membrane, cis
groups    {default: interface}
```

### Context and expectation

After generating a mesh with `nanopnp mesh cylinder`, a modeler's natural first instinct is to visually inspect the resulting geometry, boundary groups, and mesh resolution. 

However:
1. The CLI provides no command or flag to display or export a plot of the mesh (e.g., `nanopnp plot pore.msh` or `nanopnp mesh view`).
2. Neither `01-command-line/README.md` nor the user guide ([docs/guide/meshes.md](../guide/meshes.md)) mentions how a user can view `.msh` files.

Viewing currently requires either:
- An external mesh viewer (e.g. opening `pore.msh` in the standalone Gmsh GUI).
- A custom Python script using `nanopnp.mesh.ingest` and `nanopnp.plot.panels.plot_mesh`.
- Waiting until notebook-based sessions or running the desktop GUI (`nanopnp-gui`).

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

When asked to mesh a cylinder in Session 01, a user immediately asks how to specify geometric parameters (pore diameter, length, reservoir dimensions) vs. mesh discretization settings (element size, grading).

Two distinct issues emerge:
1. **Discoverability:** The session documentation and getting-started guide give `nanopnp mesh cylinder --out pore.msh` without mentioning that geometry and mesh parameters are configurable via flags, nor directing the user to `--help`.
2. **Conflation of Geometry and Meshing:** In FEA modeling, CAD/geometry definition is logically distinct from discretization/meshing. While `nanopnp` separates them for protein structures (Stage 5 `region` CAD assembly vs Stage 6 `mesh`), for idealized pores the two are bundled together in a one-shot `mesh cylinder` command. The user expects:
   - A way to define or generate a geometry object first (with diameter, length, reservoir size) that can be inspected.
   - A subsequent mesh step that accepts the geometry and handles discretization parameters (wall grading, refinement, maximum element size).

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

In Session 01 and Session 02, the user is instructed to run `nanopnp inspect <run-dir>` to verify run configuration, settings, and especially deviations from the validated model (e.g., verifying that `run-classical` lists each `none` correction as a deviation while `run-epnpns` lists none).

However, user feedback reveals that `nanopnp inspect` is currently ineffective for this workflow:
> *"Using `inspect` (even with the `--json` flag) as a user is rather pointless unless you know exactly what you are looking for. There is just too much information dumped into the console."*

Key problems:
1. **Information overload:** By default, `inspect <dir>` defaults to dumping `manifest.json`. The manifest is an exhaustive provenance record containing full case text, environment details, compiler versions, and stage hashes. Dumping this (even pretty-printed with `--json`) forces the user to manually scroll through hundreds of lines of JSON.
2. **Lack of a concise summary view:** A user typically inspects a run to answer high-level questions: *What model ran? Did it converge? What are the key quantities? Were there any deviations from the validated model?*
3. **Missing targeted query flags:** There is no way to ask for specific sections, such as `nanopnp inspect run-classical --deviations` or `--quantities`.
4. **No run comparison:** To compare `run-epnpns` against `run-classical`, the user must inspect both independently and mentally diff hundreds of lines of JSON output. A dedicated `nanopnp diff <run1> <run2>` or `nanopnp inspect --diff` would directly show the physical differences (e.g. `none` corrections, shift in transport numbers from 0.542 to 0.556).


## UT-04 · No CLI command to export or plot field heatmaps (potential, concentrations, velocity) from a run

**Area:** `cli`. **Severity:** `medium`. **Session:** `01-command-line`.

### Context and expectation

After running a continuum solve with `nanopnp run pore.case.yaml`, the command-line interface only outputs scalar summary metrics (total current, conductance, transport numbers, and route agreement).

However, a nanopore modeler's primary expectation after a 2D-axisymmetric solve is to visualize spatial field distributions:
- Electrostatic potential $\phi(r, z)$ heatmap across the pore and reservoirs.
- Ion concentration distributions $c_i(r, z)$ ($Na^+$, $Cl^-$) showing accumulation, depletion, and double-layer structure.
- Fluid velocity field $\mathbf{u}(r, z)$ and electro-osmotic flow streamlines.
- Current density and ionic flux vectors.

Currently:
1. `nanopnp` has rich internal plotting infrastructure in `nanopnp.plot` (e.g., `solve_figure` and `plot_field`), but this is only accessible programmatically via Python (`result.figure("solve")`) or within GUI/notebook environments.
2. The CLI provides no command (such as `nanopnp plot run-pore` or `nanopnp run ... --plot-fields`) to save these figures (e.g. as PNG or PDF) directly from a run directory.
3. Session 01 ("The command line: from a case file to a reproduced current") ends without providing or suggesting any way to view the physical field solutions.

## UT-05 · Unclear motivation and user use-case for the `reproduce` command

**Area:** `docs`. **Severity:** `low`. **Session:** `01-command-line`.

### Context and expectation

In Session 01 step 5, the user is instructed to run `nanopnp reproduce run-pore`. The documentation explains that it "solves the archived case again, from nothing, and compares what it recorded".

From an end-user perspective, this raises immediate confusion:
- The finite-element solve and Newton continuation are deterministic on a given machine, so running the exact same case again in the same directory naturally returns the exact same numbers.
- A user naturally wonders: *Why does this command exist? Under what circumstances would a run NOT reproduce?*

The documentation does not explain the primary use cases:
1. **Third-party / Peer review verification:** A collaborator or reviewer receives the run directory (`manifest.json`, `case.yaml`, input files) on a different OS/hardware/architecture (e.g. macOS ARM64 vs Linux x86_64, or different BLAS/LAPACK builds) and verifies that the published numbers reproduce within numerical solver tolerance ($10^{-6}$).
2. **Input drift / tampering detection:** If an external input file (such as `pore.msh` or a PDB file) was modified on disk after the run, `reproduce` catches cryptographic hash mismatches against the manifest.
3. **Bypassing the cache:** Normal `nanopnp run` calls hit the cache (`store/`). `reproduce` forces a cold re-solve into an isolated temporary store to ensure the stored result is genuine and independent of continuation warm-starts or cache pollution.
4. **Library & environment upgrade verification:** Detecting whether upgrading dependencies (NGSolve, Python, NumPy) perturbed numerical results.

## UT-06 · Redundant charge definition in `field.yaml` and undocumented grid `shape`

**Area:** `docs`. **Severity:** `low`. **Session:** `02-physics`.

### Context and expectation

In Session 02 ("Then try"), the user is asked to flip the sign of the charge ring in `ring.field.yaml` and re-run.

The user encountered two points of friction:
1. **Redundant charge declaration:** The charge magnitude and sign are specified in two distinct places:
   ```yaml
   q_net_e: -6.0
   form:
     name: gaussian_ring
     parameters: {centre_r_nm: 2.6, centre_z_nm: 0.0, width_nm: 0.4, charge_e: -6.0}
   ```
   If a user flips only `parameters.charge_e` and leaves `q_net_e`, stage 7 aborts on the `PHY-19` charge conservation gate because the declared net charge does not match the integrated charge. Having duplicated truth in the document is unintuitive.
2. **Undocumented grid parameters:** The document specifies:
   ```yaml
   origin_nm: [0.0, -4.0]
   spacing_nm: [0.01, 0.01]
   shape: [501, 801]
   ```
   The meaning of `shape` is neither explained in the file comments nor in the session documentation. In fact, `shape: [N_r, N_z]` represents the discrete lattice dimensions in cylindrical coordinates $(r, z)$, spanning $r \in [0, 5]\text{ nm}$ ($501 \times 0.01$) and $z \in [-4, 4]\text{ nm}$ ($801 \times 0.01$).

## UT-07 · `nanopnp run` lacks progress feedback or live status during long solves

**Area:** `cli`. **Severity:** `low`. **Session:** `03-numerics`.

### Context and expectation

When executing `nanopnp run <case>`, solving the continuation ladder and Newton iterations can take anywhere from tens of seconds to several minutes.

During this period:
1. The CLI provides zero progress updates on stdout or stderr by default. The process sits completely silent until the entire pipeline has finished and results are written.
2. Users have no indication of whether the solver is making progress through continuation rungs, stuck in heavily damped Newton steps, or hanging.
3. Although `run_case` in the core pipeline accepts a `progress: Progress | None` callback, the CLI `_run` handler does not connect it to any terminal progress bar, spinner, or rung ticker.
4. While passing `-v` (INFO level) logs continuation rungs to stderr, and `--log-file <path>` allows tailing a log, these flags are not mentioned in the session tutorials or getting-started guide, and log output to stderr is mixed with other diagnostic messages rather than providing clean progress reporting.

## UT-08 · Inconsistent case naming in session 03 (`coarse.case.yaml` vs `wall-100.msh`)

**Area:** `docs`. **Severity:** `low`. **Session:** `03-numerics`.

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

## UT-09 · Severe runtime scaling on moderate meshes (~16k elements) due to serial UMFPACK and multi-rung ladder

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

When testing domain-wide refinement with `--maxh-nm 0.175`, the mesh contains 16,562 triangular elements. While this is a modest mesh count in continuum modeling (which COMSOL solves in a few seconds), the solve in `nanopnp` exceeded 5 minutes without completing.

Root causes in `nanopnp`:
1. **Coupled DOF explosion:** 2D axisymmetric ePNP-NS solves 6 coupled fields ($\phi$, $c_{\mathrm{Na}^+}$, $c_{\mathrm{Cl}^-}$, $u_r$, $u_z$, $p$) using $P_2/P_1$ Taylor-Hood elements. On 16,562 elements, the number of coupled degrees of freedom reaches $\approx 1.5 \times 10^5$.
2. **Serial direct solver bottleneck (`NUM-21`):** The default sparse direct solver in the pip wheel is SuiteSparse `umfpack` (NGSolve lacks built-in parallel PARDISO/MUMPS in its wheels). As benchmarked in `SPECIFICATION.md §6.4`, a single UMFPACK factorization at $1.5 \times 10^5$ DOFs takes $\approx 4.4\text{ s}$ on a modern CPU. Unlike COMSOL, which uses multi-threaded Intel MKL PARDISO across all cores, UMFPACK is strictly single-threaded.
3. **Full continuation ladder execution:** The default continuation strategy (`default_ladder`) runs 7–8 distinct rungs (PB-linear $\to$ PB $\to$ equilibrium PNP $\to$ bias ramp $\to$ Navier-Stokes flow $\to$ non-steric corrections $\to$ steric corrections), taking 35–50 total Newton iterations.
4. **No Jacobian reuse:** At $\approx 4.5\text{ s}$ per factorization plus matrix assembly and damping checks, 50 Newton iterations require $\approx 250 - 350\text{ s}$ (> 5 minutes). COMSOL mitigates this through parallel direct solvers and holding the Jacobian constant across iterations (modified Newton).

Suggested remedies:
- Allow configurable continuation strategies (e.g. bypassing intermediate PB/ramp rungs for simple uncharged cases).
- Support modified Newton steps (freezing the LU factorization across iterations when convergence is rapid).
- Explore multi-threaded or iterative linear solver backends where available.









