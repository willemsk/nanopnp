# Code review: willemsk/nanopnp: Phase 2 work packages

2026-09-29 · commit `7b35183` (`ccr-edee6716-ywr441`) · scope: the Phase 2 work packages WP17–WP24 (stages 1–6, case schema v2, the Gmsh backend, the VAL-05 harness, the Geometry tab; 21.1k lines in 35 files; tests read for context only) · focus: all five categories at equal weight

## Summary

The Phase 2 code is in good shape where wrong answers are most plausible. The reviewers re-derived and ran the stage-1 frame and Cₙ-axis sign conventions, the union-density stencil arithmetic, the annular weights, the OpenDX/CCP4 axis order, marching-squares coordinate placement, every FR-08 gate criterion (all NaN-safe), the stage 4–6 cache keys against the inputs each stage reads, the VAL-05 ε_G formula and registration sign, and Gmsh session teardown on error. No finding changes a published number, and none is critical.

The defects sit at process and record boundaries:
- **A child that dies silently locks the desktop shell (CR-1).** Every child seam trusts the child to post a terminal event, and nothing in the parent handles death by signal.
- **A truncated walk overwrites the run record of the full walk (CR-2).** `run --upto` and the new **Build geometry** button share one run directory with the full run of the same case.
- **A window rule that depends on the sign of a float32 rounding error (CR-3).**

The systemic pattern is identities built from something weaker than the thing they identify: the run directory (from name and case hash, not the walk), the sweep plan (from path strings, not file contents) and a plan file's recorded ids (trusted, not re-derived).

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 10 |

## Findings at a glance

| ID | Sev | Category | Location | Finding |
|---|---|---|---|---|
| CR-1 | High | concurrency / error handling | `gui/run_model.py:350-354`, `gui/widgets/geometry.py:595,641,966` | A build or run child that dies without reporting leaves both tabs locked in "running" until restart |
| CR-2 | Medium | correctness (FR-25, QR-08) | `io/run.py:973-983`, `io/store.py:75-79` | A truncated walk (`--upto`, **Build geometry**) overwrites the run record of the full run of the same case |
| CR-3 | Medium | correctness | `structure/read.py:565-568` | The `last_ns` window drops the boundary frame on DCDs whose float32 timestep rounds up |
| CR-4 | Low | correctness | `geometry/region.py:305-325`, `mesh/profile.py:374-382` | Stage 5 refuses a valid profile whose edge lies flat on a bilayer plane, in two of four orientations |
| CR-5 | Low | correctness (FR-25) | `sweep/plan.py:311-344,751` | The plan's base-case gate hashes path strings, not the files they name |
| CR-6 | Low | error handling | `sweep/plan.py:889-932` | `read_plan` trusts the recorded point ids and hash, so an edited plan runs other points under the old identities |
| CR-7 | Low | error handling | `gui/widgets/geometry.py:670-731`, `gui/assess.py:401-415`, `gui/render.py:716-730` | The assess and render helper children can die without an answer, and the tab shows "measuring" or "drawing" for ever |
| CR-8 | Low | efficiency (memory) | `density/union.py:188-192` | `canonical_grid` copies the float32 ensemble to float64 plus a radius array: 2.7× the ensemble, against a stated one-slab contract |
| CR-9 | Low | correctness | `structure/ensemble.py:177-191` | `AlignedEnsemble.export` writes chain `X` and a blank segid whenever a chain key is longer than one character |
| CR-10 | Low | concurrency | `io/run.py:1019-1022` | `run_case` reads the case file twice, so the manifest can embed text other than the case that ran |
| CR-11 | Low | error handling | `mesh/profile.py:496-500` | `inputs.profile.path` without a `.yaml`/`.yml` suffix is read as a fixture name |
| CR-12 | Low | security | `gui/probe.py:339-347` | The packaging probe writes to a predictable shared path in the system temp directory |
| CR-13 | Low | efficiency | `structure/stage.py:100` | The stage-1 key includes `structure.source.variant`, a label documented as "recorded", so relabelling re-aligns the ensemble |

## Findings

### CR-1 · A build or run child that dies without reporting leaves the tabs locked

**Severity:** High · **Category:** concurrency / error handling · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/gui/run_model.py:350-354`; `src/nanopnp/gui/widgets/geometry.py:595, 641-643, 964-976`

**Build geometry** runs stages 1–6 in a spawned child that imports OpenCASCADE, Netgen and MDAnalysis and can run the mesher on the 2WCD or ClyA-AS ensembles. If the child is SIGKILLed or crashes (the OOM killer, a segfault in a compiled library), it never posts `Finished`, `Failed` or `Cancelled`. `RunControl.poll` never looks at `process.running` or `exit_code`, so the model stays `idle` or `running` and `settled` never becomes true. The Geometry tab's `_settled` flag is the only thing that re-enables **Build geometry** and **Load structure…**, and **Cancel** only sets an event nobody reads. Nothing reports the crash, and the only recovery is to restart the app. The Run tab drives the same `RunControl`, so a solve killed by the OOM killer has the same outcome. `SolverProcess.exit_code` even documents that "a child that died without reporting one has no diagnosis to give", but nothing acts on it.

Reproduced: a `RunControl` was started, its child SIGKILLed, and after polling the state was `alive False exitcode -9 state idle settled False`. With the patch below the same script ends in `state failed settled True`.

```python
def poll(self) -> RunModel:
    """Drain the child's events into the model and return it."""
    if self.process is not None:
        self.model.consume(self.process.drain())
    return self.model
```

**Suggested fix** (applies to `git apply --check`; the repo's `uv run pytest tests/tier1` passed 1273/1273 with it applied). Liveness is read before the queue, so a child that posts its last event and exits between the two reads is not called silent:

```diff
diff --git a/src/nanopnp/gui/run_model.py b/src/nanopnp/gui/run_model.py
index 6ea8127..27295ef 100644
--- a/src/nanopnp/gui/run_model.py
+++ b/src/nanopnp/gui/run_model.py
@@ -40,7 +40,7 @@ from dataclasses import dataclass, field
 from pathlib import Path
 from typing import TYPE_CHECKING, Any, Literal, TypeAlias
 
-from nanopnp.cli.errors import EXIT_OK
+from nanopnp.cli.errors import EXIT_OK, EXIT_UNEXPECTED
 from nanopnp.gui.convergence import ConvergenceModel
 from nanopnp.gui.solver import (
     Cancelled,
@@ -350,7 +350,24 @@ class RunControl:
     def poll(self) -> RunModel:
         """Drain the child's events into the model and return it."""
         if self.process is not None:
+            # Liveness before the queue, so that a child which posts its last event and
+            # exits between the two reads is not mistaken for a silent one.
+            alive = self.process.running
             self.model.consume(self.process.drain())
+            if not alive and not self.model.settled:
+                self.model.consume(
+                    (
+                        Failed(
+                            exit_code=EXIT_UNEXPECTED,
+                            error="ChildExited",
+                            message=(
+                                f"the run process exited with status {self.process.exit_code} "
+                                "without reporting a result (killed, out of memory, or a fault "
+                                "in a compiled library)"
+                            ),
+                        ),
+                    )
+                )
         return self.model
 
     def cancel(self) -> None:
```

A regression test would start a `RunControl` on a case, kill the child, and assert `poll().state == "failed"` with the exit status in the diagnosis.

### CR-2 · A truncated walk overwrites the run record of the full run

**Severity:** Medium · **Category:** correctness (FR-25, QR-08) · **Confidence:** high (reproduced through the CLI and through `run_case`)
**Location:** `src/nanopnp/io/run.py:973-983`; `src/nanopnp/io/store.py:75-79`; callers `gui/widgets/geometry.py:575`, `gui/solver.py:426`, `nanopnp run --upto`

The run directory is `runs/<name>-<short(case_hash)>` whatever `upto` is. If a case has been run in full and is then built with `upto` (the **Build geometry** button, or `nanopnp run --upto mesh`), the partial `manifest.json`, `case.yaml` and `run.json` replace the full ones in place. After that `nanopnp reproduce <run dir>` fails with "records no quantities", the run view shows no numbers, and the manifest of the earlier result no longer describes it (§5.3.3). The artefacts stay in the store by hash, so a full re-run (all cached) restores the record. Until then the earlier result cannot be read through its directory.

Reproduced: on one store, `--upto region`, `--upto mesh` and `--upto region` on a supplied-profile ClyA case all wrote to the same directory `runs/u4case-3fd246c9fcce`, and `run.json`'s stage list went `[case, region]`, `[case, mesh, region]`, `[case, region]`. With the patch the truncated walks land in `u4case-upto-region-…` and `u4case-upto-case-…`. WP24 D3 says only that "the CLI's `run --upto` already writes a truncated walk"; it does not discuss sharing the directory.

```python
    result = RunResult(
        directory=walk.store.run_directory(document.name, manifest.case_hash),
```

**Suggested fix:** give a truncated walk its own directory. A complete walk keeps its name, so no published path moves.

```diff
diff --git a/src/nanopnp/io/run.py b/src/nanopnp/io/run.py
index 88ee793..2b79463 100644
--- a/src/nanopnp/io/run.py
+++ b/src/nanopnp/io/run.py
@@ -971,8 +971,11 @@ def _walk(
     report(progress, 1.0, f"{len(stages)} stages complete")
 
     manifest = _manifest(walk, case_text=case_text, case_path=case_path)
+    # A truncated walk is another record of the same case; it must not replace the
+    # run record a complete walk wrote, because QR-08 reproduces from that one.
+    label = document.name if stages[-1] == PIPELINE[-1] else f"{document.name}-upto-{stages[-1]}"
     result = RunResult(
-        directory=walk.store.run_directory(document.name, manifest.case_hash),
+        directory=walk.store.run_directory(label, manifest.case_hash),
         manifest=manifest,
         artefacts=dict(walk.artefacts),
         stages=tuple(walk.records),
```

`Finished.directory` already carries the path, so the GUI's `_built` and the render child follow whichever directory was used. A regression test would run a case in full, then with `upto`, and assert the full run's `run.json` still holds its `quantities`.

### CR-3 · The `last_ns` window drops the boundary frame on DCDs whose float32 timestep rounds up

**Severity:** Medium · **Category:** correctness · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/structure/read.py:565-568`

WP18 settles that the window is inclusive (`wp18-structure-ingestion.md:200`: at 5 ps per frame, `last_ns: 1` takes frames 799–999). A DCD stores its timestep as a float32 in AKMA units, and MDAnalysis reads 1 ps back as `dt = 1.0000000328 ps`. Over N frames the boundary frame then misses `start` by about `N·dt·3.3e-8`, which is 3.3e-9 ns at 100 frames. That is larger than the code's slack of `1e-9·max(1, t_last)` ns, which its comment says exists for exactly this round-off.

Reproduced on 1001-frame DCDs written through MDAnalysis. `last_ns` of 10 %, 25 % and 50 % of the run selected 100, 250 and 500 frames at dt = 1, 2 and 0.5 ps, but 101, 251 and 501 at dt = 10, 20 and 2.5 ps (the float32 error has the other sign). The inclusive rule expects 101, 251 and 501 every time. Which ensemble a case gets therefore depends on the sign of a float32 rounding error. With `count` also given, the smaller window can wrongly refuse an admissible count or change the stride `⌊N/count⌋`. `tests/tier1/test_structure_stage.py:259` tests only exact float64 times.

```python
        start = times_ns[-1] - last_ns
        # A relative slack for the round-off of times accumulated as frame * dt.
        slack = 1e-9 * max(1.0, abs(times_ns[-1]))
        window = [index for index in window if times_ns[index] >= start - slack]
```

**Suggested fix:** add a thousandth of a frame interval, which can never admit a neighbouring frame. With it the six timesteps above all give 101, 251 and 501.

```diff
diff --git a/src/nanopnp/structure/read.py b/src/nanopnp/structure/read.py
index 498ce2e..01d7baf 100644
--- a/src/nanopnp/structure/read.py
+++ b/src/nanopnp/structure/read.py
@@ -563,8 +563,10 @@ def select_frames(
                 "window would be the whole trajectory in silence (section 5.3.1 NOTE)"
             )
         start = times_ns[-1] - last_ns
-        # A relative slack for the round-off of times accumulated as frame * dt.
-        slack = 1e-9 * max(1.0, abs(times_ns[-1]))
+        # A slack for the round-off of times accumulated as frame * dt, where dt may be a
+        # float32 (a DCD stores its timestep so): a thousandth of an interval never admits
+        # a neighbouring frame, and covers the drift of ~1.6e4 frames of float32 error.
+        slack = 1e-9 * max(1.0, abs(times_ns[-1])) + 1e-3 * interval_ns
         window = [index for index in window if times_ns[index] >= start - slack]
     if count is not None:
         if count > len(window):
```

The test that would catch it is the experiment above, as a parametrised Tier 1 test over six DCD timesteps, asserting the frame count is independent of the timestep.

### CR-4 · Stage 5 refuses a valid profile whose edge lies flat on a bilayer plane

**Severity:** Low · **Category:** correctness · **Confidence:** high (reproduced; the fix was checked on all four orientations)
**Location:** `src/nanopnp/geometry/region.py:305-325` (used by `:992` and checked at `:920-939`); root cause is the half-open rule in `src/nanopnp/mesh/profile.py:374-382`

`plane_crossings` counts an edge only if `lower <= z < upper`, so a horizontal edge exactly on `z = ±t/2` is dropped. Of its two neighbours only the one leaving the plane upwards is counted, so `r₂` becomes whichever end of the flat edge that neighbour starts from, and `check_junction` aborts with an offset equal to the edge's length. Round numbers make the tie easy to hit: the default `t/2` is 1.4, and the reference fixture already has a vertex at `(4.88, +1.4)`.

For `[(2,-3),(2,5),(3,5),(3,1.4),(5,1.4),(5,-3)]` with a 30 nm reservoir, before the patch the result is `RegionGateError … the membrane's innermost radius 5.000000000 nm on the cis plane, +2.000e+00 nm from r2 = 3.000000000 nm`. The mirrored trans-plane case fails the same way, and the other two orientations pass. Raising the flat edge by 1e-7 nm makes the same geometry pass with `junction_nm = {'trans': 5.0, 'cis': 5.0}`. Severity is Low because the refusal is loud and only an exact tie triggers it; stage-4 profiles have float vertices, and supplied or hand-edited profiles are gated only on validity. The §5.2.1 NOTE defines `[r₁, r₂]` as "the profile's two smallest crossings", so the code follows the spec's words while the junction criterion in the same NOTE contradicts them on flat edges. Amend the NOTE in the same commit.

```python
    return crossings[0], crossings[1]
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/geometry/region.py b/src/nanopnp/geometry/region.py
index 733a476..48670cb 100644
--- a/src/nanopnp/geometry/region.py
+++ b/src/nanopnp/geometry/region.py
@@ -322,7 +322,23 @@ def lumen_interval(points: np.ndarray, z_nm: float, *, centre_z_nm: float) -> tu
             f"with the profile spanning z = [{lower:.4f}, {upper:.4f}] nm in the model frame "
             f"after geometry.membrane.centre_z_nm = {centre_z_nm:g} nm",
         )
-    return crossings[0], crossings[1]
+    import numpy as np
+
+    # The half-open test counts one end of an edge lying on the plane; the body's
+    # section runs on along it, and the membrane meets the body at the far end.
+    following = np.roll(points, -1, axis=0)
+    flat = [
+        (min(a[0], b[0]), max(a[0], b[0]))
+        for a, b in zip(points, following, strict=True)
+        if a[1] == z_nm and b[1] == z_nm
+    ]
+    r2, grown = crossings[1], True
+    while grown:
+        grown = False
+        for low, high in flat:
+            if low <= r2 < high:
+                r2, grown = float(high), True
+    return crossings[0], r2
 
 
 def _point_segment_distance(p: np.ndarray, s0: np.ndarray, s1: np.ndarray) -> np.ndarray:
```

The test that would catch it is `derive_region` on the four flush profiles above, asserting the junctions `5/5`, `3/6`, `5/3` and `5/5`.

### CR-5 · The sweep plan's base-case gate hashes path strings, not the files they name

**Severity:** Low · **Category:** correctness (FR-25) · **Confidence:** high on the mechanism (reproduced by the reviewer, code read by me); Low because the path semantics are documented and every member's manifest records the input hashes it actually read
**Location:** `src/nanopnp/sweep/plan.py:311-344` (gate), `:751` (`base_hash=CaseArtefact(base).hash`)

`CaseArtefact` hashes the validated dump, which carries `inputs.mesh.path`, `inputs.profile.path`, `structure.source.path` and `inputs.charge.path` as strings. It does not carry the bytes of those files, and paths resolve against the process working directory (`sweep/run.py:25` documents that on purpose). `base_case()`'s docstring calls this check "the one way this design can produce a whole dataset of plausible wrong answers". A job array dispatched from another working directory or machine, or a referenced file edited between `sweep plan` and dispatch, passes the gate. Every member then solves a mesh or field the plan never enumerated, under the plan's point identities, and the plan-time NUM-34 gate ran on the old file. The reviewer confirmed this by rewriting `pore.msh` and calling `base_case()` from another directory: both calls passed.

**Suggested fix (design change):** at plan time resolve every input file each point names (`inputs.{mesh,profile,charge,eps_r}.path`, `structure.source.path`, `structure.ensemble.trajectory`) to an absolute path, record its `file_hash` in the plan and in `SweepPlan.hash` beside `base_case`, and re-check both in `base_case()`/`case()` with the same `SweepPlanError`, naming the path and both digests.

### CR-6 · `read_plan` trusts the recorded point ids and hash

**Severity:** Low · **Category:** error handling · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/sweep/plan.py:889-932`

`plan.json` records `"hash"` and each point's `"id"` (the content hash of its assignments, which keys the dataset), and `read_plan` checks neither. If an assignment is changed in the file (a hand edit, or a merge of two plans), the new value runs and its row is keyed under the old id. The reviewer set point 1's `bias_V` to 0.3: `read_plan` accepted it, the point kept the id of the −0.1 V point, `plan.case(1)` solved 0.3 V, and the recomputed hash was `83a65d8e…` against the recorded `210a9b58…`. The file is a local trust boundary, hence Low.

```python
    return SweepPlan(
        name=str(raw["name"]),
        base_path=Path(str(base["path"])),
```

**Suggested fix:** re-derive each point id and the plan hash on read.

```diff
diff --git a/src/nanopnp/sweep/plan.py b/src/nanopnp/sweep/plan.py
index 5dd5838..69f83a4 100644
--- a/src/nanopnp/sweep/plan.py
+++ b/src/nanopnp/sweep/plan.py
@@ -918,7 +918,7 @@ def read_plan(path: Path) -> SweepPlan:
         )
         for entry in raw["points"]
     )
-    return SweepPlan(
+    plan = SweepPlan(
         name=str(raw["name"]),
         base_path=Path(str(base["path"])),
         base_hash=str(base["hash"]),
@@ -930,6 +930,20 @@ def read_plan(path: Path) -> SweepPlan:
         wall_distance=dict(raw["wall_distance"]),
         workers=None if raw.get("workers") is None else int(raw["workers"]),
     )
+    # The file carries its own identities; a hand edit or a merge of two plans would
+    # otherwise run other operating points under the recorded point ids (QR-12).
+    for point in plan.points:
+        if short(content_hash(POINT_SCHEMA, dict(point.assignments)), ID_LENGTH) != point.point_id:
+            raise SweepPlanError(
+                f"{path}: point {point.index} is recorded as {point.point_id!r} but its "
+                "assignments hash to another identity; the plan was edited, re-plan it"
+            )
+    if plan.hash != raw["hash"]:
+        raise SweepPlanError(
+            f"{path}: records hash {raw['hash']} but its contents hash to {plan.hash}; "
+            "the plan was edited, re-plan it"
+        )
+    return plan
 
 
 def plan_from_document(path: Path, *, check_meshes: bool = True) -> SweepPlan:
```

### CR-7 · The assess and render helper children can die without an answer

**Severity:** Low (reviewer: Medium; adjusted, since the buttons do re-enable and only the message is missing) · **Category:** error handling · **Confidence:** high (traced by reading; not run)
**Location:** `src/nanopnp/gui/widgets/geometry.py:670-712` and `714-731`; `src/nanopnp/gui/assess.py:401-415`; `src/nanopnp/gui/render.py:716-730`

The assess child loads the whole ensemble and runs `probe_radius_profile`, so it can be OOM-killed. The render child runs NGSolve `Draw` on a mesh of about 120k triangles and can crash. If either dies before its `put`, `finished` is true and `events` is empty. The tab drops the process and re-enables its buttons, but the status line keeps saying "measuring the section 5.2.1 criteria …" (assess), or the mesh pane shows "stage 6: drawing the mesh…" for ever (render), and there is no log line. The children's own `except BaseException` handlers do post an error for Python exceptions. The gap is only death by signal or hard fault.

```python
finished = not self._assess.running
events = self._assess.drain()
...
if finished:
    self._assess.join(0.0)
    self._assess = None
```

**Suggested fix (design change):** a naive "finished and no events in this drain" test would false-alarm, because the last event can arrive in an earlier tick while the child is still exiting. Give `AssessProcess` and `RenderProcess` an `answered` flag that `drain()` sets once it has returned any event. When `finished and not answered`, log an error and show "the measuring process exited without an answer (killed or crashed)" or, for render, set `_mesh_problem` to say the same.

### CR-8 · `canonical_grid` copies the float32 ensemble to float64

**Severity:** Low · **Category:** efficiency (memory) · **Confidence:** high (measured by the reviewer with `tracemalloc`; I reran the density tests with the patch)
**Location:** `src/nanopnp/density/union.py:188-192`, called from `src/nanopnp/density/stage.py:141`

`AlignedEnsemble.read` returns float32 positions, so `np.asarray(..., float64)` is a full 2× copy and `np.hypot` adds a `(frames, atoms)` float64 array. For a 120 MB float32 ensemble (100 frames × 10⁵ atoms) `canonical_grid` peaked at 320 MB extra; at 10³ frames × 10⁵ atoms that is 3.2 GB transient beside a 1.2 GB ensemble. The module docstring says stage-2 memory is "the float32 map plus one float64 slab and one frame's node indices, whatever the frame count". This is the stage-2 analogue of CODE_REVIEW_002 CR-15, which fixed stage 1 only. `deposit` already converts one frame at a time, so the copy exists only for a maximum and two extrema.

```python
    positions = np.asarray(positions_nm, dtype=np.float64)
    radius = float(np.max(np.hypot(positions[..., 0], positions[..., 1])))
```

**Suggested fix:** take the extrema one frame at a time. The grid is unchanged, because the same maxima are taken.

```diff
diff --git a/src/nanopnp/density/union.py b/src/nanopnp/density/union.py
index 3a079e5..32f3064 100644
--- a/src/nanopnp/density/union.py
+++ b/src/nanopnp/density/union.py
@@ -187,11 +187,17 @@ def canonical_grid(
 
     h = float(spacing_nm)
     reach = float(np.max(cutoff_nm(widths_nm)))
-    positions = np.asarray(positions_nm, dtype=np.float64)
-    radius = float(np.max(np.hypot(positions[..., 0], positions[..., 1])))
+    # One frame at a time: the ensemble is float32 and a float64 copy of it, plus a
+    # (frames, atoms) radius array, is 2.7x its size (the module's memory contract).
+    radius, z_min, z_max = 0.0, math.inf, -math.inf
+    for frame in positions_nm:
+        xyz = np.asarray(frame, dtype=np.float64)
+        radius = max(radius, float(np.max(np.hypot(xyz[:, 0], xyz[:, 1]))))
+        z_min = min(z_min, float(xyz[:, 2].min()))
+        z_max = max(z_max, float(xyz[:, 2].max()))
     half_width = math.ceil((radius + reach) / h) + 1
-    z_low = math.floor((float(np.min(positions[..., 2])) - reach) / h) - 1
-    z_high = math.ceil((float(np.max(positions[..., 2])) + reach) / h) + 1
+    z_low = math.floor((z_min - reach) / h) - 1
+    z_high = math.ceil((z_max + reach) / h) + 1
     return DensityGrid(spacing_nm=h, half_width=half_width, z_first=z_low, nz=z_high - z_low + 1)
 
 
```

### CR-9 · `AlignedEnsemble.export` loses chain identity for chain keys longer than one character

**Severity:** Low · **Category:** correctness (export data loss) · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/structure/ensemble.py:177-191`

Stage 1 keys chains by segid wherever the chain column is blank (`read.py:_chain_keys`), so keys like the CHARMM-GUI `PROA`…`PROL` are admitted, as are two-character mmCIF `auth_asym_id`s. On export the chain IDs are set to those keys and the segid is forced blank. MDAnalysis's PDB writer cannot fit a multi-character chain ID, so it writes `X` under the `warnings.simplefilter("ignore")` at line 200. I exported a 2-chain ensemble keyed `PROA`/`PROB` and every ATOM record came out as chain `X`. A viewer then shows one chain, and feeding the export back to stage 1 fails the `C{n} expects n chains` refusal. The docstring promises an export "for a molecular viewer or another tool". `test_ver48_artefact_round_trip_and_export` uses 2WCD, whose keys are single letters.

```python
        universe.add_TopologyAttr("chainIDs", self.chain.tolist())
        ...
        universe.add_TopologyAttr("segids", [""])
```

**Suggested fix (prose):** build one segment per chain key (`n_segments=len(chains)`, with `residue_segindex` from each residue's chain) and set `segids` to the chain keys. Set `chainIDs` to the keys only when every key is one character, and blank otherwise. `_chain_keys` then reads the segid back, and the PDB's four-column segID field holds `PROA`.

### CR-10 · `run_case` reads the case file twice

**Severity:** Low · **Category:** concurrency (check-then-act on a file) · **Confidence:** medium (by reading; the race window was not reproduced)
**Location:** `src/nanopnp/io/run.py:1019-1022`

`load_case` reads and validates the file once, and the second `read_text` reads it again. If the file is saved between the two (the GUI case editor saving while its Run child starts), the manifest pairs the hash of the case that ran with the text of a different one. `case.yaml` in the run directory is written from that text and QR-08's reproduction re-runs it. Nothing in `manifest.build` checks that the text hashes to `case_hash`. The docstring of `run_case` itself says the function exists so the read "happens once".

```python
    return run_document(
        load_case(source),
        case_text=source.read_text(encoding="utf-8"),
```

**Suggested fix:** read once and validate the text with `loads_case`, which `load_case` is defined through.

```diff
diff --git a/src/nanopnp/io/run.py b/src/nanopnp/io/run.py
index 88ee793..5a71d80 100644
--- a/src/nanopnp/io/run.py
+++ b/src/nanopnp/io/run.py
@@ -49,7 +49,7 @@ from nanopnp.core.stages import (
     report,
 )
 from nanopnp.io.artefact import Artefact, CaseArtefact, StageInputs
-from nanopnp.io.case import load_case, resolve
+from nanopnp.io.case import loads_case, resolve
 from nanopnp.io.manifest import Manifest, build
 from nanopnp.io.store import Store, atomic_write_bytes
 
@@ -1017,9 +1017,10 @@ def run_case(
         As :func:`run_document` documents them.
     """
     source = Path(path)
+    text = source.read_text(encoding="utf-8")
     return run_document(
-        load_case(source),
-        case_text=source.read_text(encoding="utf-8"),
+        loads_case(text, source=str(source)),
+        case_text=text,
         case_path=source,
         store=store,
         upto=upto,
```

### CR-11 · `inputs.profile.path` without a YAML suffix is read as a fixture name

**Severity:** Low · **Category:** error handling · **Confidence:** high (traced through the code; not run)
**Location:** `src/nanopnp/mesh/profile.py:496-500`, reached from `src/nanopnp/geometry/region.py:1015` and `:1093`

For a case with `inputs.profile: {path: edits/pore.profile}` (or `.YAML`, or no suffix), stage 5 calls `load_profile(Path)`, and the suffix test sends it to `profile_file(str(name))`, which resolves `GEOMETRY_DIR / "edits/pore.profile.yaml"`. The user is told "no geometry profile 'edits/pore.profile' in <package data dir>", naming the wrong directory for a file that exists. An absolute `/x/pore` reads `/x/pore.yaml`, and `path: clya_reference_profile` silently loads the shipped fixture instead of a file in the working directory. `_check_profile` (`io/case.py:2205-2250`) checks neither the suffix nor existence. The GUI always writes `.yaml`, so only hand-written cases are affected.

```python
    path = (
        Path(name_or_path)
        if Path(name_or_path).suffix in {".yaml", ".yml"}
        else profile_file(str(name_or_path))
    )
```

**Suggested fix:** a `Path` is always a path; only a `str` can be a fixture name.

```diff
diff --git a/src/nanopnp/mesh/profile.py b/src/nanopnp/mesh/profile.py
index 25870b2..f0f97fa 100644
--- a/src/nanopnp/mesh/profile.py
+++ b/src/nanopnp/mesh/profile.py
@@ -495,7 +495,7 @@ def load_profile(name_or_path: str | Path) -> PoreProfile:
     """
     path = (
         Path(name_or_path)
-        if Path(name_or_path).suffix in {".yaml", ".yml"}
+        if isinstance(name_or_path, Path) or Path(name_or_path).suffix in {".yaml", ".yml"}
         else profile_file(str(name_or_path))
     )
     with path.open(encoding="utf-8") as handle:
```

### CR-12 · The packaging probe writes to a predictable shared temp path

**Severity:** Low · **Category:** security (insecure temp file) · **Confidence:** medium (reasoned; only local users can exploit it)
**Location:** `src/nanopnp/gui/probe.py:339-347`

`Path(tempfile.gettempdir()) / "nanopnp-probe"` is created with `exist_ok=True` and no ownership check. On a shared Linux host another local user can pre-create the directory, or a symlink `scene.html` pointing at a file the victim owns, which the probe then overwrites. If the attacker owns the directory they can substitute their own page, which the web view loads with a `file:` origin. `exercise_payloads`, the other writer in the module, already uses `TemporaryDirectory`.

**Suggested fix:**

```diff
diff --git a/src/nanopnp/gui/probe.py b/src/nanopnp/gui/probe.py
index 3b89672..18b6eec 100644
--- a/src/nanopnp/gui/probe.py
+++ b/src/nanopnp/gui/probe.py
@@ -336,8 +336,8 @@ def scene_document() -> Path:
 
     mesh = ngsolve.Mesh(unit_square.GenerateMesh(maxh=0.3))
     scene = Draw(mesh, show=False)
-    directory = Path(tempfile.gettempdir()) / "nanopnp-probe"
-    directory.mkdir(parents=True, exist_ok=True)
+    # Owner-only and unpredictable: never a name another local user can pre-create.
+    directory = Path(tempfile.mkdtemp(prefix="nanopnp-probe-"))
     document = directory / "scene.html"
     document.write_text(
         host_document(
```

### CR-13 · The stage-1 key includes the `variant` label

**Severity:** Low · **Category:** efficiency · **Confidence:** medium (read by me: `structure_parameters` starts from `spec.model_dump`, which includes `source.variant`; not run)
**Location:** `src/nanopnp/structure/stage.py:100`, `src/nanopnp/io/case.py:248`

`structure.source.variant` is documented as "a label for the prepared structure, recorded (OPN-04)", but it is part of the stage-1 key, and stages 2 to 6 and the solve are keyed through it. Relabelling a structure therefore re-aligns the whole ensemble, re-runs stages 2–6, and in a sweep makes the `structure` barrier a cold climb, although no payload changes. **Suggested fix (prose):** drop `variant` from the key's parameters and record it in the artefact summary, so it still reaches the manifest.

## Systemic observations

- **Identities weaker than what they identify.** CR-2 (run directory), CR-5 (plan identity over path strings) and CR-6 (recorded ids trusted on read) are one pattern. A guard test that walks every place an identity or a directory name is derived and asserts that a change to any input the run reads changes it would catch the class.
- **Every child seam trusts the child to post a terminal event** (CR-1, CR-7). CR-1's patch covers the run child, which serves both the Run tab and the Geometry tab's build. The assess and render helpers need the `answered` flag of CR-7.
- **Memory that scales with the whole ensemble** (CR-8, and CR-15 in CODE_REVIEW_002). The remaining candidates are in the leads below. A stage-level memory test on a synthetic 10³-frame ensemble, asserting the peak stays under 1.5× the float32 ensemble, would hold the docstring's contract.

## Method and coverage

- **Orchestrator and reviewers.** The orchestrator was `claude-sonnet-5-5`; the skill recommends Fable. Four reviewers, models chosen by failure mode per `.claude/model-policy.md`:

| Unit | Scope | Lines | Model | Why |
|---|---|---:|---|---|
| U1 | `structure/*`, `density/*`, `symmetry/*`, `data/radii` (stages 1–3, WP18–19) | 4.4k | Opus | numerical code; a bug gives a plausible wrong number |
| U2 | `geometry/{contour,region,probe}`, `mesh/{profile,generate,sizing,gmsh_backend,adapter,ingest}`, `validation/geometry` (stages 4–6, WP20–23) | 7.8k | Opus | silently wrong geometry, mesh or gate |
| U3 | `io/case`, `io/run`, `core/stages`, `sweep/plan` (WP17, WP21 D15, WP24 seams) | 5.2k | Opus | cache keys and provenance |
| U4 | `gui/{geometry,widgets/geometry,assess,render,probe,run_model,solver}` (WP24) | 4.7k | Sonnet | a shell; failures are loud |

- **Verification.** 13 reviewer findings → 12 distinct after merging U3-1 with U4-2 (the same defect), 12 reported plus one from a cross-unit lead I verified (CR-13). 0 rejected outright. Adjusted: CR-4 (Medium → Low), CR-5 (Medium → Low), CR-6 kept Low, CR-7 (Medium → Low). Every cited line was opened. 9 of the 13 have real patches, all made as `git diff` in the scratch copy: 9/9 pass `git apply --check` against the untouched repo, and the nine apply together. With all nine applied in the scratch copy, `ruff check .`, `ruff format --check .` and `mypy --strict src/` are clean, and `pytest tests/tier1 -n 4 --dist loadfile` passes 1273/1273. `tests/tier1/test_gui_widgets.py`, Tier 2 and the docs build were not run. CR-5, CR-7, CR-9 and CR-13 have prose fixes.
- **Executed.** Yes. I reproduced CR-1 (SIGKILLed child), CR-2 (run-directory reuse), CR-3 (six DCD timesteps), CR-4 (flush-edge profiles) and CR-9 (export) in the scratch environment, and re-ran each fix. CR-6, CR-8 and CR-5 were reproduced or measured by the reviewers, and I read the code. CR-7, CR-10, CR-11, CR-12 and CR-13 were confirmed by reading only.
- **Patch files.** In `<scratchpad>/patches/`: one file per finding, plus `ALL_confirmed_fixes.patch`. Nothing in the repository was modified or staged.
- **Not reviewed.** Phase 1 code that Phase 2 did not touch (`physics/`, `solve/`, `post/`, `materials/`, `charge/`, and `sweep/{run,collect,document}`, read for context only). `gui/widgets/{run_control,viewer,result}.py`, which no reviewer read. The vendored `gui/assets/webgui`. Tier 3 and the VAL-05 ensemble leg, which need `$NANOPNP_REFERENCE_DATA`. Tests were read for context and not reviewed.

## Considered and rejected

- **"The generated-mesh recipe keys on λ_D even when the 0.05 nm ceiling governs, so a concentration sweep below 1.474 M re-meshes identical meshes"** (U2 lead, U3 lead) → deliberate, WP21 D10 and D15; the barrier keeps warm starts for ordinary salt sweeps, and an identical mesh is reproduced by content hash.
- **"`refuse_walk` does not exist"** (U3) → retired on purpose in WP21 ("`refuse_walk` is removed"). The Phase 2 plan's earlier paragraphs describe it as the mechanism that WP20/21 lift.
- **"Every stage-1 key and run hashes the whole trajectory two to four times"** (U1, U3 leads) → SHA-256 runs at GB/s against minutes of alignment, so it is not material at the ensemble sizes in scope.
- **"Stages create a `store_root()/tmp/<stage>-*` directory when no workspace is given and never remove it"** (U1 lead) → `io/run.py` always passes a scratch workspace and removes it. The fallback is reached only by direct API callers.
- **`except BaseException` in the assess, render and solver children** (U4) → they report to the parent before exiting, so they do not swallow. CR-1 and CR-7 concern only death by signal.
- **`_session` calls `gmsh.logger.start()`/`stop()` and so stops a caller's logger** (U2 lead) → real when reproduced, but no caller in the repo holds a gmsh logger. Latent, not reported.
- **The Gmsh recipe omits the pinned options and `_SAMPLING_MARGIN`** (U2 lead) → these are constants of the code, and the WP23 plan (D10) treats an edit as a new `GMSH_FIELD_RULES` identifier. Not a defect unless the policy is dropped.
- **`wall_h_nm: true` coerced to 1.0 nm by pydantic lax mode** (U3 lead) → plausible, and cheap to close with `strict` on those two fields, but not reproduced. Left as a lead.

## Leads not investigated

- A supplied `inputs.charge` or `inputs.eps_r` field beside a `structure:` case with `centre_z_nm ≠ 0` is accepted, and the specification does not say which frame the field is in. This is a specification gap rather than a demonstrated defect.
- Concurrent job-array members generate and `put` the same stage 1–6 keys at the same time. Whether that is safe depends on how atomic `Store.put` is.
- `gui/widgets/geometry.py`: the O(n²) `_check_simple` re-runs on the Qt thread on every `_show_row` (0.63 s at 600 vertices). **Seed from refusal** and a rebuild drop unsaved edits without confirmation.
- `structure/read.py`: a zero-frame trajectory raises a bare `IndexError`. Two C-alpha with the same `(resid, icode)` in one chain silently overwrite each other in `per_chain`. `frame_times` decodes every frame only to read the time. There is no PBC or RMSD gate on a frame whose chain is split across the periodic box.
- `symmetry/reduce.py:269-273`: every harmonic multiplies and projects all cells although only bins with `K_j ≥ k` are kept, up to about 2× wasted work; correct.
- `validation/geometry.py:638-647`: `attribute_to_construction` given a `strict=False` comparison raises `MissingPlaneError` instead of the intended "comparisons don't match" error. The in-repo callers pass strict comparisons.
- `mesh/generate.py:154-171`: `wall_statistics` would raise a bare `ValueError` on a mesh with no `wall` segment. Stage 5's plane-crossing gate appears to make that unreachable.
- No `multiprocessing.freeze_support()` exists in `src/`. It becomes real when the shell is bundled and spawns children on Windows.
