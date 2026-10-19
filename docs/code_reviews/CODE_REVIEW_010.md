# Code review: nanopnp, whole repository

19 October 2026 · commit `28551bd` (`claude/beautiful-hamilton-hk738l`) · scope: `src/nanopnp/` except
`gui/` · focus: correctness, simplicity

## Summary

The numerical core is in good shape. Six reviewers read 44k lines in full. They checked the signs, the 2π
and r-Jacobian factors, quadrature orders, the NaN behaviour of every gate, the cache keys and the
warm-start logic, and found no wrong answer in physics/, solve/, post/, charge/, density/ or symmetry/.
The gates are written NaN-closed (`not x <= tol`) throughout. The defects sit at the edges:

- **Schema fields with no constraint.** `physics.solid_permittivities` accepts any key, so a fluid key
  silently replaces ε_r,f(⟨c⟩) in the electrolyte (CR-1). `numerics.nonlinear.rtol` accepts NaN
  (CR-4).
- **Run directory line endings.** `case.yaml` is rewritten with the platform's line endings, so
  `reproduce` refuses a CRLF case file run on Linux, or an LF one run on Windows (CR-2).
- **A SHALL with no production caller.** The NUM-10 row scaling is implemented and tested but never
  called (CR-3).

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 8 |

## Resolution

Resolved on the same branch after the review, with the author's rulings of 19 October 2026.

| ID | Outcome |
|---|---|
| CR-1 | Fixed. Values are finite and positive in the schema. Case resolution refuses a fluid key or a name outside the material vocabulary, with a suggestion; ingest keeps the fluid refusal as a backstop. Vocabulary solids absent from the mesh stay allowed (ruling). Tested in `tests/tier1/test_solid_permittivity_keys.py`. |
| CR-2 | Fixed. `case.yaml` is the source bytes, verbatim; tested for CRLF and LF in `tests/tier1/test_case_bytes_round_trip.py`. |
| CR-3 | Resolved by amending NUM-10 (ruling): the direct solvers' own row scaling discharges it. The three unused helpers and their tests are deleted. |
| CR-4 | Fixed: `max_iter ≥ 1`, `0 < rtol < 1`, finite. |
| CR-5 | Fixed in `to_ngsolve`, which builds every edge directed with the lowest-material adjacent triangle on its left, so the normal no longer follows the source's segment order. `MeshData` and its hash are unchanged: orientation is now derived from the triangles, so two meshes differing only in it build the same NGSolve mesh. Hashing it would have moved every recorded mesh hash and forced a re-pin of the number-stability golden. Tested in `tests/tier1/test_mesh_adapter.py`. |
| CR-6 | Declined, on the pass that shipped it. The model clamps the driver of the clipped concentrations (`average_concentration`, then the second clip in `CorrectionModel.evaluate`), so counting the unclipped mean logs a clamp the fits never see: 7 M and 4 M give 5.5 M against the 4.65 M they evaluate. The count stays on the clipped driver, as WP41 D7 says ("under `average` it never fires"); a test pins it. |
| CR-7 | Fixed. |
| CR-8 | Declined. A gate inside `geometry/` is a new upward `geometry → mesh` edge, which VER-61 refuses, and moving both classes into `mesh/` costs more than a low finding is worth. The only callers are Tier 2 benchmarks that compare with analytic values, so a degraded mesh fails there. |
| CR-9 | Fixed. |
| CR-10 | Fixed. Zero-golden quantities are reported as "golden is zero; relative error undefined", with our value, by `validate compare` and in the attribution report. |
| CR-11 | Fixed. `solve_pb` is removed and callers use `solve_pb_recorded(...)[0]`. |

Also resolved:

- **Simplifications.** The trapezium weights are shared, the solid-fraction checks share a mixin, the
  descriptor key-set check is one helper, and ingest uses the quality report it already gets.
- **Log-branch export.** `export_fields` now writes c, not ln c, in the NUM-02 log branch. It was
  latent, and a test now covers it.
- **Mollification (ruling).** PHY-02 and NUM-31 now state that the validated field is the unsmoothed
  C⁰ field, and that C¹ mollification is a deviation, off by default.
- **Run directory (ruling).** Its name hashes the case hash together with every recorded input file's
  sha256 (§5.3.3).
- **Case hash in the QoI and report keys.** Kept as is. Over-keying costs cache hits but can never
  serve a wrong artefact, whereas narrowing the key risks one that misses an input.
- **Rules wording.** `.claude/rules/physics-numerics.md` now states NUM-16's disjunctive test.

## Findings at a glance

| ID | Sev | Category | Location | Finding |
|---|---|---|---|---|
| CR-1 | High | correctness | `io/case.py:402`, `mesh/ingest.py:355` | A fluid key in `solid_permittivities` replaces the electrolyte's ε silently |
| CR-2 | Medium | correctness | `io/manifest.py:291-294`, `pipeline/run.py:808` | The copied `case.yaml` changes line endings, so `reproduce` refuses the run |
| CR-3 | Medium | correctness | `numerics/linear.py:209-246` | NUM-10 field-wise row scaling is never applied |
| CR-4 | Low | correctness | `io/case.py:431-432` | `rtol` accepts NaN, ≤ 0 or ≥ 1; `max_iter: 0` exits 1, not 3 |
| CR-5 | Low | correctness | `mesh/adapter.py:479`, `:257` | Edge orientation is kept for the normal but dropped from the mesh hash |
| CR-6 | Low | correctness | `materials/electrolyte.py:350-357` | The correction-driver clamp count can never fire |
| CR-7 | Low | correctness | `mesh/gmsh_backend.py:98-110` | A borrowed Gmsh session is left with `General.Terminal = 0` |
| CR-8 | Low | correctness | `geometry/analyte.py:212-218`, `:259-265` | The analyte benchmark meshes skip the quality gate |
| CR-9 | Low | correctness | `validation/compare.py:331` | `max_abs_rel` reports 0 against an all-zero reference |
| CR-10 | Low | correctness | `validation/compare.py:231-236` | A golden quantity of exactly 0 is reported as "not carried" |
| CR-11 | Low | simplicity | `physics/pb.py:100-145` | `solve_pb` copies `solve_pb_recorded`'s 13-parameter signature |


## Findings

### CR-1 · A fluid key in `physics.solid_permittivities` replaces the electrolyte's permittivity without a word

**Severity:** high · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/io/case.py:402`; consumed at `src/nanopnp/physics/models.py:481-484`. The only
check, `src/nanopnp/mesh/ingest.py:355-401`, looks for missing entries, never extra ones.

**How it goes wrong:**

- **Fluid key.** `solid_permittivities: {membrane: 3.2, electrolyte: 5}` passes `load_case`, `resolve`
  and ingest. `MaterialCF({**water_off_fluid, **named}, default=fluid_permittivity)` then gives the
  `electrolyte` domain the constant 5 in place of ε_r,f(⟨c⟩). The reviewer's run on a two-domain mesh
  measured the fluid value falling from 1.0 to 0.064.
- **Spread to stage 7.** The same keys reach stage 7's `solids` (`charge/stage.py:847`), so the fluid
  domain is also treated as a solid there.
- **No record.** Poisson is solved with the wrong ε in the pore, a plausible current comes out, and the
  manifest lists no deviation.
- **Bad values.** Negative, zero and NaN values are accepted too.

```python
# io/case.py:402
    solid_permittivities: dict[str, float] = Field(default_factory=dict)
# physics/models.py:481-484
    named = {material: value / permittivity_0 for material, value in solid_permittivities.items()}
    water_off_fluid = dict.fromkeys(sorted(off_fluid - set(named)), ion_free)
    sharp: Expression = mesh.MaterialCF({**water_off_fluid, **named}, default=fluid_permittivity)
```

**Suggested fix:** finite positive values in the schema, and a refusal of fluid keys at ingest.

```diff
diff --git a/src/nanopnp/io/case.py b/src/nanopnp/io/case.py
--- a/src/nanopnp/io/case.py
+++ b/src/nanopnp/io/case.py
@@ -6,7 +6,7 @@ import difflib
 import itertools
 from collections.abc import Mapping, Sequence
 from pathlib import Path
-from typing import Any, Literal, TypeAlias, get_args
+from typing import Annotated, Any, Literal, TypeAlias, get_args
 
 import yaml
 from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
@@ -399,7 +399,9 @@ class PhysicsSpec(_Strict):
     variable_density: bool = True
     inertia: bool = True
     dielectric_gradient_forces: bool = False
-    solid_permittivities: dict[str, float] = Field(default_factory=dict)
+    solid_permittivities: dict[str, Annotated[float, Field(gt=0.0, allow_inf_nan=False)]] = Field(
+        default_factory=dict
+    )
 
 
 class ElementsSpec(_Strict):
diff --git a/src/nanopnp/mesh/ingest.py b/src/nanopnp/mesh/ingest.py
--- a/src/nanopnp/mesh/ingest.py
+++ b/src/nanopnp/mesh/ingest.py
@@ -374,6 +374,15 @@ def check_solid_permittivities(
     MeshVocabularyError
         Naming every solid material with no entry, or the model and its solid domains.
     """
+    fluid = sorted(name for name in solid_permittivities if name in FLUID_MATERIALS)
+    if fluid:
+        raise MeshVocabularyError(
+            f"{where}: physics.solid_permittivities names the fluid "
+            f"{'domains' if len(fluid) > 1 else 'domain'} "
+            f"{', '.join(repr(name) for name in fluid)}. "
+            "A constant there replaces the concentration-dependent eps_r,f in the electrolyte "
+            "with nothing to say so (PHY-03, PHY-20)"
+        )
     if not solids:
         present = sorted(name for name in data.materials if name not in FLUID_MATERIALS)
         if present:
```

The patch leaves one gap: a misspelt key (`protien: 20`) is still recorded and never applied. Refusing
keys that name no material on the mesh would close it. That needs a ruling on whether a case may name an
optional solid, such as `analyte`, that a mesh lacks. A Tier 1 test of the refusal would catch a
regression.

### CR-2 · The run directory's `case.yaml` changes line endings, so `reproduce` refuses the run

**Severity:** medium · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/pipeline/run.py:808`, `src/nanopnp/io/manifest.py:291-294`,
`src/nanopnp/pipeline/reproduce.py:188-208`

**How it goes wrong:**

- `input_files["case"]` records the sha256 of the source file's raw bytes.
- `read_text` turns CRLF into LF, and `Manifest.write` then writes `\n → os.linesep`. The copy matches
  the recorded hash only when the source already used the platform's convention.
- So a CRLF case run on Linux, or an LF case run on Windows, gets `InputMovedError: the 'case' input
  … has moved` (exit 4) from `nanopnp reproduce`, although nothing moved (QR-08, VER-35).
- The existing comment covers the Windows-and-CRLF combination only.

```python
    text = source.read_text(encoding="utf-8")                      # run.py:808
        text = self.case_text.replace("\n", os.linesep)           # manifest.py:293
        atomic_write_bytes(directory / CASE_FILENAME, text.encode("utf-8"))
```

**Suggested fix:** keep the bytes verbatim from end to end. Sweep members (`case_path=None`, text from
`dumps_case`) are unaffected: they record no case file hash, and the text check reads both sides the same
way.

```diff
diff --git a/src/nanopnp/io/manifest.py b/src/nanopnp/io/manifest.py
--- a/src/nanopnp/io/manifest.py
+++ b/src/nanopnp/io/manifest.py
@@ -3,7 +3,6 @@
 from __future__ import annotations
 
 import json
-import os
 import platform
 import sys
 from dataclasses import dataclass, field
@@ -288,10 +287,8 @@ class Manifest:
         """Write the manifest and case file into a run directory; return the manifest path."""
         directory.mkdir(parents=True, exist_ok=True)
         # Atomic: job-array members sharing a case write one run directory.
-        # Platform line endings, as text mode wrote them: the case hash is of the source file,
-        # CRLF on Windows, so an LF copy there fails ``reproduce`` (QR-08).
-        text = self.case_text.replace("\n", os.linesep)
-        atomic_write_bytes(directory / CASE_FILENAME, text.encode("utf-8"))
+        # Verbatim: the recorded case sha256 is of the source file's bytes (QR-08).
+        atomic_write_bytes(directory / CASE_FILENAME, self.case_text.encode("utf-8"))
         path = directory / MANIFEST_FILENAME
         atomic_write_bytes(path, canonical(self.document()) + b"\n")
         return path
diff --git a/src/nanopnp/pipeline/reproduce.py b/src/nanopnp/pipeline/reproduce.py
--- a/src/nanopnp/pipeline/reproduce.py
+++ b/src/nanopnp/pipeline/reproduce.py
@@ -303,7 +303,9 @@ def reproduce(
     if not case_path.is_file():
         raise ReproductionError(f"{case_path} is not there; this is not a run directory")
     embedded = manifest.get("case")
-    if isinstance(embedded, dict) and case_path.read_text(encoding="utf-8") != embedded.get("text"):
+    if isinstance(embedded, dict) and case_path.read_bytes().decode("utf-8") != embedded.get(
+        "text"
+    ):
         raise ReproductionError(
             f"{case_path} differs from the case text embedded in {manifest_path}. They are written "
             "from one string, so one of them has been edited since the run"
diff --git a/src/nanopnp/pipeline/run.py b/src/nanopnp/pipeline/run.py
--- a/src/nanopnp/pipeline/run.py
+++ b/src/nanopnp/pipeline/run.py
@@ -805,7 +805,7 @@ def run_case(
 ) -> RunResult:
     """Load a case file and run it; the keywords are those of :func:`run_document`."""
     source = Path(path)
-    text = source.read_text(encoding="utf-8")
+    text = source.read_bytes().decode("utf-8")
     return run_document(
         loads_case(text, source=str(source)),
         case_text=text,
```

A Tier 1 test would catch a regression: write a CRLF case, run `Manifest.write` and then `check_inputs`.

### CR-3 · NUM-10 field-wise row scaling is implemented, tested and never called

**Severity:** medium · **Category:** correctness (a SHALL left undischarged) · **Confidence:** high
**Location:** `src/nanopnp/numerics/linear.py:209-246`

**How it goes wrong:**

- NUM-10 (SPECIFICATION.md:2523) says row scaling "SHALL be applied … so that all diagonal Jacobian
  blocks have O(1) norm".
- `diagonal_block_norms`, `field_row_scaling` and `report_block_scaling` have no caller in `src/`; only
  `tests/tier1/test_linear_solver.py` calls them.
- `UmfpackSolver.solve` factorises the unscaled matrix. The block-spread warning therefore never fires
  on a real solve, including the 1/λ̃² ≈ 130 Poisson block that the knowledge base records.
- The Tier 1 tests give the impression that the requirement holds.
- A pivoted direct solve normally still gives an accurate step, so this is a requirement gap and a
  missing diagnostic, not a wrong current.

```python
def field_row_scaling(matrix: Expression, space: FESpace) -> dict[str, float]:
    """Return the reciprocal diagonal-block norms as row scaling factors."""
    return {
        name: (1.0 / norm if norm > 0.0 else 1.0)
        for name, norm in diagonal_block_norms(matrix, space).items()
    }
```

**Suggested fix (a decision for the author):** either wire it in or amend the requirement.

- **Wire it in.** Call `report_block_scaling(form.mat, space)` on the first linearisation of each rung
  in `damped_newton`, and apply `field_row_scaling` to the matrix and the right-hand side in
  `solve_correction`.
- **Amend NUM-10.** Say that UMFPACK's internal scaling discharges it, and delete the three helpers and
  their tests (about 40 + 80 lines).

### CR-4 · `numerics.nonlinear.rtol` is unconstrained; `max_iter: 0` exits as "unexpected"

**Severity:** low · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/io/case.py:431-432`

**How it goes wrong:**

- **NaN.** `rtol: .nan` resolves. `relative_update <= nan` is always false, so the NUM-16 update test
  can never pass. Every rung then runs to `max_iter` and is reported as a divergence that the case
  caused.
- **Out of range.** `rtol: -1` and `rtol: 0.5` also resolve.
- **`max_iter: 0`.** It reaches `NewtonSettings.__post_init__` as a bare `ValueError`, which exits 1
  rather than the case class 3.

```diff
diff --git a/src/nanopnp/io/case.py b/src/nanopnp/io/case.py
--- a/src/nanopnp/io/case.py
+++ b/src/nanopnp/io/case.py
@@ -428,8 +428,8 @@ class NonlinearSpec(_Strict):
 
     strategy: Literal["newton", "hybrid"] = "newton"
     damping: Literal["residual", "backtracking"] = "residual"
-    max_iter: int = 100
-    rtol: float = 1.0e-6
+    max_iter: int = Field(default=100, ge=1)
+    rtol: float = Field(default=1.0e-6, gt=0.0, lt=1.0, allow_inf_nan=False)
 
 
 class LinearSpec(_Strict):
```

### CR-5 · Boundary-edge orientation sets the NGSolve normal, and the mesh hash drops it

**Severity:** low (the reviewer said medium; adjusted) · **Category:** correctness · **Confidence:**
medium
**Location:** `src/nanopnp/mesh/adapter.py:479-480`; `canonical()` at `adapter.py:257`

**How it goes wrong:**

- `to_ngsolve` adds each `Element1D` in the vertex order the source mesh gave it, and NGSolve's
  `specialcf.normal` follows that order. The reviewer's run showed that one reversed segment flips the
  normal on that segment.
- A supplied Gmsh mesh orients each line by its curve's drawing direction. An analyte boundary can
  therefore mix orientations.
- `_oriented_normal` (`post/forces.py:633`) fixes one global sign, so the traction on the reversed
  elements is integrated with the wrong sign.
- `canonical()` sorts each edge, so two meshes that differ only in orientation share one content hash.

**Why low:** `extract(check_routes=True)`, the default, cross-checks the traction route against the
orientation-free reaction route. A partly cancelled traction raises `ForceDisagreementError`, so the
error is silent only with `check_routes=False`, which is a recorded deviation.

**Suggested fix (prose):** orient every boundary edge with its adjacent triangle on the left in
`MeshData.__post_init__`. Orient interior seams against a fixed side, such as the lower material index.
Then keep the orientation in `canonical()` rather than `np.sort`.

### CR-6 · The correction-driver clamp count can never fire

**Severity:** low · **Category:** correctness (dead diagnostic) · **Confidence:** high (run)
**Location:** `src/nanopnp/materials/electrolyte.py:350-357`, with `263-271`

**How it goes wrong:**

- `average_concentration` clips each species to `[1e-6, validity_M[1]]` before averaging, so its mean
  never exceeds `limit`.
- `driver_count` is therefore always 0 for `driver="average"`, and for `ionic_strength` with
  monovalent ions.
- The species clamps are still logged (PHY-13), so nothing goes unrecorded; the driver branch is
  unreachable.

```python
        driver_count = log_clamp_activations(
            self.average_concentration(samples),
```

**Suggested fix (prose):** count the driver on the unclipped concentrations, using the same mean
without `ops.clip`. Or keep the driver line only for `ionic_strength` with multivalent species, the only
case in which the second clamp in `FittedCorrection.evaluate` can bind.

### CR-7 · A borrowed Gmsh session is left with `General.Terminal = 0`

**Severity:** low · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/mesh/gmsh_backend.py:98-110`

**How it goes wrong:** `_options` contains `General.Terminal`. `saved.update(...)` on line 110 runs after
line 101 has already set it to 0, which overwrites the saved original. On exit the caller's session is
"restored" to 0. The reviewer reproduced it: set 1, run `_session`, and it reads back 0.

```diff
diff --git a/src/nanopnp/mesh/gmsh_backend.py b/src/nanopnp/mesh/gmsh_backend.py
--- a/src/nanopnp/mesh/gmsh_backend.py
+++ b/src/nanopnp/mesh/gmsh_backend.py
@@ -107,7 +107,9 @@ def _session(options: Mapping[str, float]) -> Iterator[None]:
         else:
             previous_model = gmsh.model.getCurrent()
             undo.append(lambda: gmsh.model.setCurrent(previous_model))
-            saved.update({name: gmsh.option.getNumber(name) for name in options})
+            saved.update(
+                {name: gmsh.option.getNumber(name) for name in options if name not in saved}
+            )
         for name, value in options.items():
             gmsh.option.setNumber(name, value)
         gmsh.model.add(f"nanopnp-region-{next(_MODEL_IDS)}")
```

### CR-8 · The analyte benchmark geometries mesh without the quality gate

**Severity:** low · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/geometry/analyte.py:212-218` and `259-265`

**How it goes wrong:** every primitive in `mesh/primitives.py` returns `_gated(..., check=check_quality)`
(min SICN/gamma > 0.3). `AnalyteInBoxGeometry.generate` and `PoreWithAnalyte.generate` return
`ngs.Mesh(geometry.GenerateMesh(...))` ungated. Their only callers are the Tier 2 force benchmarks, which
compare against analytic values, so a sliver would show up as a failing benchmark rather than a gate
naming the element.

**Suggested fix (prose):** add a `check_quality: bool = True` argument to both `generate` methods and
run `check_quality(from_ngsolve(mesh), where=...)` before returning, as `_gated` does.

### CR-9 · `field_error` reports `max_abs_rel = 0.0` against an all-zero reference

**Severity:** low · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/validation/compare.py:331`

**How it goes wrong:** with a zero golden field and a nonzero one of ours, `rel_L2_r` and `rel_l2` are
`inf` (from `_relative`), but `max_abs_rel` is `0.0`. `validate compare` prints `max 0.0000e+00` beside
an infinite L2. Nothing gates on `max_abs_rel`, so the error is in what is reported, not in a verdict.

```diff
diff --git a/src/nanopnp/validation/compare.py b/src/nanopnp/validation/compare.py
--- a/src/nanopnp/validation/compare.py
+++ b/src/nanopnp/validation/compare.py
@@ -328,7 +328,11 @@ def field_error(
         points=int(keep.sum()),
         rel_L2_r=_relative(difference, reference, radial),
         rel_l2=_relative(difference, reference, None),
-        max_abs_rel=float(np.max(np.abs(difference)) / scale) if scale > 0.0 else 0.0,
+        max_abs_rel=(
+            float(np.max(np.abs(difference)) / scale)
+            if scale > 0.0
+            else (float("inf") if np.any(difference) else 0.0)
+        ),
         max_at_nm=(float(location[0]), float(location[1])),
         gauge_removed=gauge,
     )
```

### CR-10 · A golden quantity of exactly zero disappears from the comparison record

**Severity:** low · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/validation/compare.py:231-236`; `validation/attribution.py:527-529`

**How it goes wrong:**

- The skip is deliberate, for zero-bias round-off. Its reporting is the problem.
- `attribute()` lists the quantity under "Not compared", whose text reads "the golden does not carry
  these". That is false: the golden carries 0.
- `unavailable_quantities()` does not list it at all.
- An absolute discrepancy (for example, our 1e-9 A against a golden 0 A) is lost with no record.

**Suggested fix (prose):** collect zero-reference quantities separately, for example as
`zero_reference_quantities` or as a `QoIComparison` with `relative = nan` and the absolute difference.
Report them as "golden is zero; relative error undefined", with the absolute difference.

### CR-11 · `solve_pb` copies `solve_pb_recorded`'s whole signature to drop one return value

**Severity:** low · **Category:** simplicity · **Confidence:** high
**Location:** `src/nanopnp/physics/pb.py:100-145`

**Why it matters:** 46 lines repeat 13 parameters and their defaults, and the body is only
`solve_pb_recorded(...)[0]`. A new parameter or a changed default has to be edited twice, or `solve_pb`
drifts from it without notice. No `src/` caller uses `solve_pb`; three test files do.

**Suggested fix (prose):** drop `solve_pb` and have the three tests call `solve_pb_recorded(...)[0]`.

## Systemic observations

- **Free-form schema fields bypass the checks layer.** `pipeline/checks.py` guards values consistently
  with `not 0 < x < inf`. The pydantic fields it does not visit (`solid_permittivities`, `rtol`) have no
  constraint at all (CR-1, CR-4). One sweep would settle it: give every free-form `float` in `io/case.py`
  a `Field` constraint or name the check that covers it.
- **Diagnostics that exist and are tested but have no production caller** (CR-3, CR-6). A test of a
  helper does not show that the pipeline uses it. Where a helper discharges a requirement, the test
  should go through the production path.
- **Degenerate references in reported metrics** (CR-9, CR-10). The gates handle zero and NaN well, but
  the numbers printed beside them do not.

## Also noted outside the focus

None at high or critical severity. These small simplifications fell below the bar:

- **Duplicated trapezoid weights.** `charge/kernel.py:219-222` duplicates
  `density/grid.py:155-167`'s trapezoid weights. The producer-leg gate would catch drift between them.
- **Duplicated range checks.** `charge/dielectric.py` repeats `check_range`, `material_means` and
  `check_materials` on two classes, about 20 lines.
- **Quality computed twice.** `mesh/ingest.py:497-498` computes the quality report twice per ingest.
- **Duplicated key-set check.** `solve/state.py` duplicates the descriptor key-set check in `_gate`
  and `_gate_space`.

## Questions for the author (cross-unit leads, unresolved)

- **Mollified distance field.** No production caller passes `smoothing_length_nm`
  (`physics/distance.py:74-76`), so the C¹ mollification pass that PHY-02 and NUM-31 describe never
  runs. The reviewer measured a normalised gradient jump of 0.494 across element edges. Should the
  unsmoothed Varadhan field count as meeting "mollified to C¹"?
- **Run directory overwrite.** The run directory is `runs/<name>-<short(case_hash)>`, and the case hash
  does not cover input file contents. Re-running after regenerating `pore.msh` at the same path
  overwrites the earlier run's manifest. Is that intended? (`pipeline/run.py:777`)
- **Case hash and cache keys.** The case hash covers `name` and file paths, so renaming a case or
  moving its mesh re-keys stages 11 and 12 (`io/artefact.py:418`). This costs cache hits, not
  correctness.

## Method and coverage

- **Orchestrator:** Opus 5.5 (Fable is recommended for this skill). **Reviewers:** six, all on Opus;
  each unit's code can return a plausible wrong answer. **Patch generation:** Haiku (high effort), at
  the user's request.

| Unit | Scope | Lines | Model | Why |
|---|---|---:|---|---|
| A | physics, numerics, materials | 6.1k | Opus | weak forms and corrections |
| B | solve, post, sweep | 5.7k | Opus | convergence, QoI, warm start |
| C | charge, density, symmetry | 7.1k | Opus | charge conservation, units |
| D | geometry, mesh, structure | 7.2k | Opus | mesh gates, broad excepts |
| E | io, pipeline, core, cli | 8.0k | Opus | hashing, cache keys, provenance |
| F | validation | 8.3k | Opus | a bug here lets a wrong result pass its test |

- **Verification:** 13 reviewer findings in, 11 reported (2 adjusted: CR-5 from medium to low, and
  CR-3 framed as a requirement gap), and 2 moved to "Also noted" as below the simplicity bar. Every
  cited line was opened.
- **Patches:**
  - Five patches (CR-1, CR-2, CR-4, CR-7, CR-9) pass `git apply --check` singly and together against
    `28551bd`.
  - With all five applied: `ruff check` and `ruff format --check` are clean, `mypy src/` is clean
    (145 files), and Tier 1 passes (1,399 passed; `test_gui_widgets.py` excluded, as it runs serially).
  - Tier 2 and the push gate were not run.
- **Executed:** reviewers confirmed CR-1, CR-2, CR-4, CR-5, CR-6, CR-7, CR-9 and CR-10 by short runs in a
  scratch copy. CR-3 and CR-8 were confirmed by searching for callers.
- **Not reviewed:** `src/nanopnp/gui/` (6.8k lines, a thin shell holding no physics; skipped for
  budget); the vendored `gui/assets/webgui/`; tests (read for context only); `data/`, `docs/`.

## Considered and rejected

- **Asymmetric-salt ionic strength** (`mesh/sizing.py:120`, one `concentration_M` for every species):
  unreachable. The only shipped parameter file is `willems2020_nacl`.
- **Log-variable concentration export** (`post/export.py:275-283` writes `w·c0` in the NUM-02 log
  branch): unreachable, since no case path sets `log_variables`. If the branch is exposed, use
  `solution.concentration(species)`.
- **Newton convergence written as OR, not AND** (`numerics/newton.py:292-294`): NUM-16 makes the update
  test and the residual test disjunctive, and bars forced steps from the update test. The code matches
  the specification; the "AND" wording in `.claude/rules/physics-numerics.md` is looser than NUM-16.
- **The `except Exception` hotspots** (`mesh/adapter.py:329,408`, `mesh/gmsh_backend.py:90,386`,
  `solve/continuation.py:433`, `sweep/run.py:164,196`, `numerics/linear.py:252`): each re-raises a typed
  error with its cause, records a failed member with its exit code, or is the normal path for a
  non-product space. None turns a failure into a plausible default.
- **`contextlib.suppress`** at `charge/protonation.py:411` and `validation/costs.py:386`: the first only
  affects collecting PDB2PQR's log messages, and the second is a stdout scan whose failure is loud
  downstream.
- **`PackingFractionGate` falls back to 0.5 nm** (`numerics/gates.py:236`): its only caller supplies
  every species.
- **`worst_plane` returns NaN for an empty plane list** (`charge/fields.py:614`): no caller passes an
  empty list.
