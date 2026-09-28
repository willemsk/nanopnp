# Code review: nanopnp

2026-09-27 · commit `d2fc2e3` (main) · scope: whole repository (`src/`, repo scripts, hooks and
examples; vendored `gui/assets/webgui` excluded) · focus: correctness and efficiency (other
categories reported only at high or critical severity)

## Summary

The core numerics check out. The reviewers re-derived the scaling, the sign conventions, the wall
functions, the correction forms and the `1/r` integration orders, and found them consistent
with `.knowledge/01`. The serious problems sit at the edges of the pipeline. The worst are two case
fields, `electrolyte.temperature_K` and `boundary_conditions.walls`, that are validated, hashed
and recorded in the manifest but never reach the solver. A 310 K case, or a case asking for a
slip wall, gets a plausible wrong answer and a manifest that claims otherwise. There are two
recurring patterns behind most of the other findings. Gates written as `x > tol` pass NaN
silently, and inputs that change a result are sometimes missing from what is checked or hashed.

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 4 |
| Medium | 8 |
| Low | 5 |

## Findings at a glance

| ID | Sev | Category | Location | Finding |
|---|---|---|---|---|
| CR-1 | high | correctness | `src/nanopnp/io/case.py:2402` | The case's `temperature_K` never reaches the physics |
| CR-2 | high | correctness | `src/nanopnp/io/case.py:511-513` | Non-default wall conditions are accepted and recorded but never applied |
| CR-3 | high | correctness | `src/nanopnp/post/stage.py:450-456` | `ground: trans` gives a negative conductance and an inverted rectification ratio |
| CR-4 | high | correctness | `src/nanopnp/mesh/adapter.py:505-509` | The MSH reader silently drops quads and other non-triangle cells |
| CR-5 | medium | correctness | `src/nanopnp/post/qoi.py:504-520` | The NUM-26 route-agreement gate passes when the reaction route is NaN |
| CR-6 | medium | correctness | `src/nanopnp/charge/fields.py:256-257` | A NaN or inf `q_net_e` switches off three of the five conservation gates |
| CR-7 | medium | correctness | `src/nanopnp/io/reproduce.py:198-201` | `reproduce` counts a number that became NaN as reproduced |
| CR-8 | medium | correctness | `src/nanopnp/post/qoi.py:739-744` | Every zero-bias case crashes stage 11, whatever `outputs:` asks for |
| CR-9 | medium | correctness | `src/nanopnp/validation/compare.py:333-336` | The VAL-01 mask gate compares a margin-shrunk mask with the golden's raw mask |
| CR-10 | medium | correctness | `src/nanopnp/materials/stage.py:78-81` | The stage-8 key hashes only the reference file, not every file the corrections read |
| CR-11 | medium | correctness | `src/nanopnp/physics/coefficients.py:271-282` | `permittivity_sensitivity` raises `AttributeError` when the permittivity correction is off |
| CR-12 | medium | efficiency | `src/nanopnp/io/run.py:131-153` | Per-run scratch directories under the store are never removed |
| CR-13 | low | correctness | `src/nanopnp/solve/newton.py:348-352` | A NaN trial residual counts as an unforced step, so update-only convergence can fire |
| CR-14 | low | correctness | `.claude/hooks/gate.sh:66-81` | The commit gate tests the hook's cwd, not the tree `git -C` commits into |
| CR-15 | low | correctness | `src/nanopnp/materials/models.py:291-294` | Name-keyed cache serves stale fit coefficients after a correction file is edited |
| CR-16 | low | correctness | `src/nanopnp/density/grid.py:446-448` | The truncation gate treats the `r = 0` axis column as a cut edge |
| CR-17 | low | efficiency | `src/nanopnp/gui/render.py:401-419` | A Python loop re-implements `BitArray.NumSet()` on every render |

## Findings

### CR-1 · The case's `temperature_K` never reaches the physics

**Severity:** high · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/io/case.py:2398-2438`, `src/nanopnp/materials/electrolyte.py:330`,
`src/nanopnp/solve/state.py:437`, `src/nanopnp/solve/continuation.py:947`

`Electrolyte.from_parameter_file` always takes its temperature from the YAML file (298.15 K for
`willems2020_nacl`), and `resolve()` never compares that with the case's
`electrolyte.temperature_K`. Take a case at 310 K:

- Every scale, including `V_T` and `mu_i^0`, is built at 298.15 K.
- The manifest, the stage-8 key and mesh sizing all record 310 K.
- On the single-rung path (`continuation: none`), the Dirichlet value is `bias / V_T(310 K)`, so
  the model sees 3.8 % less bias than intended, and the conductance is then divided by the full
  bias.
- On the ladder, the case is silently solved at 298.15 K.

`temperature_K` is sweepable (`sweep/plan.py:456`). This is a plausible wrong number with a
manifest that says otherwise. Two reviewers found it independently, from opposite sides of the
boundary (U1 and U2).

```python
# materials/electrolyte.py:330
        temperature_K = document.temperature_K
# solve/state.py:437
    thermal_V = thermal_voltage(resolved.temperature_K)
```

**Suggested fix:** refuse the mismatch in `resolve()` until temperature is threaded through, since
the fits are temperature-specific anyway. The same patch also refuses the unapplied wall
conditions of CR-2:

```diff
diff --git a/src/nanopnp/io/case.py b/src/nanopnp/io/case.py
index c02727d..e0ddb67 100644
--- a/src/nanopnp/io/case.py
+++ b/src/nanopnp/io/case.py
@@ -2402,6 +2402,24 @@ def resolve(document: CaseDocument) -> ResolvedCase:
         driver=document.electrolyte.driver,
     )
     _check_species(document, electrolyte)
+    if document.electrolyte.temperature_K != electrolyte.temperature_K:
+        # Every reference property, every scale and V_T come from the parameter
+        # file; a case at another temperature would be solved at the file's while
+        # its manifest records the case's.
+        raise CaseValidationError(
+            f"electrolyte.temperature_K is {document.electrolyte.temperature_K} K, but "
+            f"{document.electrolyte.parameters!r} is fitted at {electrolyte.temperature_K} K "
+            "and the solve takes every material property and V_T from the file; set "
+            f"temperature_K: {electrolyte.temperature_K} or supply a parameter file fitted "
+            "at the temperature you want"
+        )
+    walls = document.boundary_conditions.walls
+    if walls.slip != "no_slip" or walls.ion_flux != "no_flux":
+        raise CaseValidationError(
+            f"boundary_conditions.walls asks for slip: {walls.slip} and ion_flux: "
+            f"{walls.ion_flux}; this release applies no-slip and no-flux only, and a "
+            "condition that is recorded but not applied would be a plausible wrong answer"
+        )
 
     elements = document.numerics.elements
     order = _order(elements.phi, "phi")
```

A regression test: `resolve()` on a case with `temperature_K: 310` raises `CaseValidationError`.

---

### CR-2 · Non-default wall conditions are accepted and recorded but never applied

**Severity:** high · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/io/case.py:511-513`

`boundary_conditions.walls.slip` (`navier`, `free`) and `walls.ion_flux: prescribed` pass the
schema. They are also written into the solve provenance (`case.py:1798`). But nothing outside
`io/case.py` reads them: a grep for `walls`, `slip` or `ion_flux` finds no consumer. A case
asking for a free-slip wall is solved with no-slip. The `WallSpec` docstring itself says the
values "name the condition applied", which is exactly what the manifest then misreports.

```python
    ion_flux: Literal["no_flux", "prescribed"] = "no_flux"
    slip: Literal["no_slip", "navier", "free"] = "no_slip"
```

**Suggested fix:** the `walls` refusal in CR-1's patch. When slip conditions are implemented,
lift the refusal in the same commit.

---

### CR-3 · `ground: trans` gives a negative conductance and an inverted rectification ratio

**Severity:** high · **Category:** correctness · **Confidence:** medium
**Location:** `src/nanopnp/post/stage.py:450-456` (with `post/qoi.py:482-492, 808-819`)

The solve puts the bias on the non-grounded electrode:
`{resolved.ground: 0.0, driven: bias/V_T}`. The current indicator always references cis,
though. With `ground: trans`, cis sits at `+V`, the measured current comes out negative, and so
does `G = I/V`. That contradicts NUM-27's "G > 0 at either sign". `rectification()` treats
`bias_V > 0` as forward, so RR comes out as its reciprocal. `ground` is a schema value and a
sweep axis (`sweep/plan.py:130`), and nothing in `post/`, `validation/` or `sweep/` reads it.

```python
        quantities = qoi_post.extract(
            solution,
            measures,
            indicator,
            bias_V=prepared.resolved.bias_V,
            check_routes=prepared.check_routes,
        )
```

**Suggested fix:** pass the bias as seen from the cis reference. The alternative is to refuse
`ground: trans` in stage 11 and name the convention.

```diff
diff --git a/src/nanopnp/post/stage.py b/src/nanopnp/post/stage.py
index a251f2a..c2b07ad 100644
--- a/src/nanopnp/post/stage.py
+++ b/src/nanopnp/post/stage.py
@@ -451,7 +451,11 @@ class QoIStage:
             solution,
             measures,
             indicator,
-            bias_V=prepared.resolved.bias_V,
+            # NUM-27's G = I/V > 0 is stated with cis grounded. With trans grounded
+            # the bias sits on cis, and the +z current responds to its negative.
+            bias_V=prepared.resolved.bias_V
+            if prepared.resolved.ground == "cis"
+            else -prepared.resolved.bias_V,
             check_routes=prepared.check_routes,
         )
 
```

Verify with the same case at `ground: cis` and `ground: trans`: G should agree in sign and value.

---

### CR-4 · The MSH reader silently drops quads and other non-triangle cells

**Severity:** high · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/mesh/adapter.py:505-509`

A supplied gmsh mesh with a boundary-layer row of `quad` cells, which is common gmsh output with
recombination on, loses those cells with only a debug log. The `wall` line elements survive, but
they now hang on vertices no triangle uses. The real fluid edge, one row in from the wall, gets
the natural (free) condition. `check_names`, `check_quality` and `check_radii` all pass, so the
solve runs with no-slip and the wall-distance sources on detached vertices. `from_ngsolve`
already refuses non-triangles (line 595), so the two readers disagree.

```python
    for position, block in enumerate(mesh.cells):
        if block.type not in blocks:
            _LOGGER.debug("ignoring %d %s cells in %s", len(block.data), block.type, path.name)
            continue
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/mesh/adapter.py b/src/nanopnp/mesh/adapter.py
index 178a3f5..4c376d0 100644
--- a/src/nanopnp/mesh/adapter.py
+++ b/src/nanopnp/mesh/adapter.py
@@ -504,9 +504,16 @@ def _read_meshio(path: Path) -> MeshData:
     physical = mesh.cell_data.get("gmsh:physical")
     blocks: dict[str, dict[int, list[np.ndarray]]] = {"triangle": {}, "line": {}}
     for position, block in enumerate(mesh.cells):
-        if block.type not in blocks:
+        if block.type == "vertex":
+            # Physical points: nothing is posed on them, and gmsh writes them freely.
             _LOGGER.debug("ignoring %d %s cells in %s", len(block.data), block.type, path.name)
             continue
+        if block.type not in blocks:
+            raise MeshFormatError(
+                f"{path}: carries {len(block.data)} {block.type!r} cells; nanopnp solves on "
+                "straight-sided triangles bounded by line segments (NUM-01), and dropping "
+                "these cells would leave a hole whose edge carries no boundary condition"
+            )
         connectivity = np.asarray(block.data, dtype=np.int64)
         tags = (
             np.asarray(physical[position], dtype=np.int64)
```

---

### CR-5 · The NUM-26 route-agreement gate passes when the reaction route is NaN

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/post/qoi.py:504-520` and `570-577`

`boundary_reaction_flux` returns `float(InnerProduct(...))` with no finiteness check. If that
value is NaN:

- `max(finite, nan)` is the finite value.
- `relative_difference` is NaN.
- `nan > tolerance` is False, so the QR-04 oracle reports `routes_checked: True` having compared
  against nothing. The per-species check fails the same way.

`ForceAgreement.check` uses NaN-safe `<=`, so the two modules are inconsistent.

```python
        scale = max(abs(self.indicator_A), abs(self.reaction_A))
        if scale == 0.0:
            return 0.0
        return abs(self.indicator_A - self.reaction_A) / scale
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/post/qoi.py b/src/nanopnp/post/qoi.py
index c9e9970..3ff9481 100644
--- a/src/nanopnp/post/qoi.py
+++ b/src/nanopnp/post/qoi.py
@@ -502,6 +502,9 @@ class RouteAgreement:
     @property
     def relative_difference(self) -> float:
         """``|I_psi - I_reaction|`` over the larger magnitude, or 0 if both vanish."""
+        if not (math.isfinite(self.indicator_A) and math.isfinite(self.reaction_A)):
+            # A non-finite route has agreed with nothing; ``nan > tol`` is False.
+            return math.inf
         scale = max(abs(self.indicator_A), abs(self.reaction_A))
         if scale == 0.0:
             return 0.0
@@ -573,7 +576,7 @@ def _check_species_routes(
     for species, value in indicator.items():
         other = reaction[species]
         difference = abs(value - other) / scale
-        if difference > tolerance:
+        if not difference <= tolerance:
             raise RouteDisagreementError(
                 f"the two current routes disagree on {species!r}: the NUM-24 indicator gives "
                 f"{value:.6e} A and the NUM-25 reaction flux {other:.6e} A, a difference of "
```

---

### CR-6 · A NaN or inf `q_net_e` switches off three of the five conservation gates

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/charge/fields.py:256-257` (consequences at 735-737, 912, 931, 959)

Pydantic accepts `q_net_e: .nan` by default, and a `yaml.safe_dump` of a NumPy NaN produces
exactly that. The effects:

- `reference_C` becomes NaN, which skips the zero-reference refusal.
- The quadrature, producer and per-plane errors are all NaN, so every `> tol` test passes.
- The manifest records `relative_error: nan` for three legs.

The same `gate_fields` runs again in the solve, and it passes there as well.

```python
    axis_cutoff_nm: float = DEFAULT_AXIS_CUTOFF_NM
    q_net_e: float | None = None
```

**Suggested fix:** refuse non-finite values at the schema:

```diff
diff --git a/src/nanopnp/charge/fields.py b/src/nanopnp/charge/fields.py
index f45272b..53e7b49 100644
--- a/src/nanopnp/charge/fields.py
+++ b/src/nanopnp/charge/fields.py
@@ -253,8 +253,8 @@ class FieldDocument(_Strict):
     data: DataSpec | None = None
     form: FormSpec | None = None
     grid: GridSpec | None = None
-    axis_cutoff_nm: float = DEFAULT_AXIS_CUTOFF_NM
-    q_net_e: float | None = None
+    axis_cutoff_nm: float = Field(default=DEFAULT_AXIS_CUTOFF_NM, allow_inf_nan=False)
+    q_net_e: float | None = Field(default=None, allow_inf_nan=False)
 
     @model_validator(mode="after")
     def _check(self) -> FieldDocument:
```

---

### CR-7 · `reproduce` counts a number that became NaN as reproduced

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/io/reproduce.py:198-201`, used at `243-246`

If either the recorded or the reproduced quantity is NaN, `_relative` returns NaN. `nan >
tolerance` is False, so the quantity never enters `drifts`, and `nanopnp reproduce` declares the
run reproduced. QR-08's check fails open on exactly the case it most needs to catch.

```python
    difference = abs(reproduced - recorded)
    return difference / abs(recorded) if recorded != 0.0 else difference
```

**Suggested fix:** NaN on one side only is a drift. NaN on both sides reproduces:

```diff
diff --git a/src/nanopnp/io/reproduce.py b/src/nanopnp/io/reproduce.py
index d12d8f2..d386474 100644
--- a/src/nanopnp/io/reproduce.py
+++ b/src/nanopnp/io/reproduce.py
@@ -32,6 +32,7 @@ from __future__ import annotations
 
 import json
 import logging
+import math
 import tempfile
 from dataclasses import dataclass
 from pathlib import Path
@@ -197,6 +198,12 @@ def _flatten(value: Canonicalisable, prefix: str = "") -> dict[str, Canonicalisa
 
 def _relative(recorded: float, reproduced: float) -> float:
     """Return the relative difference, falling back to the absolute one at zero."""
+    if math.isnan(recorded) != math.isnan(reproduced):
+        # A number that became NaN, or stopped being one, has not reproduced;
+        # ``nan > tolerance`` is False, so it must not reach that test as NaN.
+        return math.inf
+    if math.isnan(recorded):
+        return 0.0
     difference = abs(reproduced - recorded)
     return difference / abs(recorded) if recorded != 0.0 else difference
 
```

---

### CR-8 · Every zero-bias case crashes stage 11, whatever `outputs:` asks for

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/post/qoi.py:739-744` (raises at `482-492`); called from `post/stage.py:450`

`extract()` always computes the conductance, and `conductance()` raises at `bias_V == 0`. So an
equilibrium point, or the 0 V member of an I–V sweep, fails even when it asks only for
`eof_rate`. The transport number just before it is a ratio of round-off anyway.

```python
        transport_number=transport_number(currents, cations),
        conductance_S=conductance(current, bias_V),
```

**Suggested fix:** make both optional at zero bias. `summary` and `compare_quantities` already
handle `None`:

```diff
diff --git a/src/nanopnp/post/qoi.py b/src/nanopnp/post/qoi.py
index c9e9970..822d4d8 100644
--- a/src/nanopnp/post/qoi.py
+++ b/src/nanopnp/post/qoi.py
@@ -595,8 +595,8 @@ class QuantitiesOfInterest:
     bias_V: float
     currents_A: Mapping[str, float]
     current_A: float
-    transport_number: float
-    conductance_S: float
+    transport_number: float | None
+    conductance_S: float | None
     eof_m3_s: float | None
     agreement: RouteAgreement | None
     stabilisation_currents_A: Mapping[str, float] | None = None
@@ -739,8 +739,9 @@ def extract(
         bias_V=bias_V,
         currents_A=currents,
         current_A=current,
-        transport_number=transport_number(currents, cations),
-        conductance_S=conductance(current, bias_V),
+        # Both are ratios to a current that is round-off at zero bias.
+        transport_number=None if bias_V == 0.0 else transport_number(currents, cations),
+        conductance_S=None if bias_V == 0.0 else conductance(current, bias_V),
         eof_m3_s=indicator_eof(solution, measures, indicator) if model.flow else None,
         agreement=agreement,
         stabilisation_currents_A=stabilisation,
```

Check that the `QoI` consumers in `sweep/collect.py` and the CLI table print `None` rather than
failing on it.

---

### CR-9 · The VAL-01 mask gate compares a margin-shrunk mask with the golden's raw mask

**Severity:** medium · **Category:** correctness · **Confidence:** medium
**Location:** `src/nanopnp/validation/compare.py:333-336`; `src/nanopnp/validation/probe.py:477-488`

`grid.masks` drops points within `margin_nm` of an interface. The reference grid drops 29 such
points for `c`. `golden.defined(field)` is simply the golden's non-NaN set, and neither
`ingest_golden` nor `docs/validation/comsol-export-contract.md` applies or asks for that margin.
A COMSOL grid export has values at those points. `check_mask_agreement` therefore raises
`ProbeGridError` ("a real difference between this geometry and the one the export was made
from") on every real concentration comparison. Self-goldens pass only because they inherit our
own mask. The confidence is medium because it rests on what a real COMSOL export contains at
points next to an interface.

```python
        keep = np.asarray(grid.masks[field], dtype=bool)
        check_mask_agreement(field, keep, golden.defined(field), grid)
```

**Suggested fix (design):** carry the bare mask on `ProbeGrid` alongside the margin mask. Then
gate agreement as "the golden is defined at every kept point and NaN at every point the bare
test excludes", leaving the margin band out of both the gate and the norms.

---

### CR-10 · The stage-8 key hashes only the reference file, not every file the corrections read

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/materials/stage.py:78-81`

`electrolyte.parameters` and `electrolyte.corrections.<prop>.model` can name different files, and
`_file_backed_builder` reads fit coefficients from the file named by the correction model.
Only `parameter_file` is hashed, though, and `FittedCorrection.provenance` records names rather
than coefficients. So editing a second installed correction file leaves the materials key
unchanged, and the store serves a stale result. It is latent today, with one file shipped, but
FR-16 makes adding a file the intended way to support a new electrolyte.

```python
        digest = file_hash(correction_file(parameter_file)) if parameter_file else ""
```

**Suggested fix (design):** hash the set of distinct files every non-`none` correction resolves
through, together with `parameter_file`. Keep the single-file digest byte-identical so the VER-47
recorded key doesn't move. The reviewer's draft patch relied on an `Electrolyte` attribute that I
could not confirm, so it isn't included here.

---

### CR-11 · `permittivity_sensitivity` raises `AttributeError` when the permittivity correction is off

**Severity:** medium · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/physics/coefficients.py:271-282`

`NoCorrection.evaluate` returns the float `1.0`. So does `FittedCorrection.evaluate` when the
concentration part is off, because permittivity has no wall form. `relative_permittivity()`
therefore returns a float, and `.Diff(...)` fails. The trigger is `dielectric_gradient_forces:
true` with `continuation: none` and the permittivity correction set to `none`, an ordinary
PHY-22 ablation. The docstring promises "identically zero" here. Instead the residual assembly
aborts with a message that names neither the switch nor the correction.

```python
        return self.relative_permittivity().Diff(self.concentrations[species])
```

**Suggested fix:** it returns a CF, because `_sensitivity_gradient` differentiates the result
again.

```diff
diff --git a/src/nanopnp/physics/coefficients.py b/src/nanopnp/physics/coefficients.py
index e26c59b..a9b0bf6 100644
--- a/src/nanopnp/physics/coefficients.py
+++ b/src/nanopnp/physics/coefficients.py
@@ -279,7 +279,15 @@ class NondimensionalCoefficients:
         Only used when ``dielectric_gradient_forces`` is enabled, which is a
         deviation from the validated model (PHY-08, PHY-23).
         """
-        return self.relative_permittivity().Diff(self.concentrations[species])
+        import ngsolve as ngs
+
+        permittivity = self.relative_permittivity()
+        if not isinstance(permittivity, ngs.CoefficientFunction):
+            # ``none``, or the concentration part switched off: the factor is the
+            # float 1.0, and its sensitivity is identically zero. A CF, because
+            # the caller differentiates the result again.
+            return ngs.CF(0.0)
+        return permittivity.Diff(self.concentrations[species])
 
     @property
     def provenance(self) -> Mapping[str, Any]:
```

---

### CR-12 · Per-run scratch directories under the store are never removed

**Severity:** medium · **Category:** efficiency · **Confidence:** high
**Location:** `src/nanopnp/io/run.py:131-153`, with the same `mkdtemp` fallback in eight stage modules

Every run makes `<store>/tmp/run-*` with `mkdtemp`, and nothing ever deletes it. `Store.put`
copies the payloads, so each generated mesh, field export and solution sits on disk twice. On the
3,675-point envelope sweep this is unbounded growth on the same filesystem as the store.

```python
    root = store.root / WORKSPACE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=root))
```

**Suggested fix (design):** remove `walk.scratch` in a `finally` once the last workspace stage's
payload is in the store. Alternatively, have `Store.put` move rather than copy files that already
sit under `<store>/tmp`. Apply the same fix to the per-stage fallbacks.

---

### CR-13 · A NaN trial residual counts as an unforced step, so update-only convergence can fire

**Severity:** low · **Category:** correctness · **Confidence:** medium
**Location:** `src/nanopnp/solve/newton.py:348-352`, `396`

At minimum damping, `forced = nan >= current` is False. `current` then becomes NaN, every later
step is also "unforced", and convergence can be declared from the relative update alone while
`result.residual` is NaN. The positivity gate catches NaN concentrations afterwards. A NaN
residual with a finite, positive state is not caught.

```python
                forced = trial_residual >= current
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/solve/newton.py b/src/nanopnp/solve/newton.py
index 0c0f110..a245d22 100644
--- a/src/nanopnp/solve/newton.py
+++ b/src/nanopnp/solve/newton.py
@@ -347,7 +347,8 @@ def damped_newton(
 
             trial_residual = residual_norm()
             if trial_residual < current or at_minimum:
-                forced = trial_residual >= current
+                # ``not <``, not ``>=``: a NaN trial residual is a forced step.
+                forced = not trial_residual < current
                 break
             damping = max(settings.minimum_damping, damping * settings.recovery_damping)
 
```

---

### CR-14 · The commit gate tests the hook's cwd, not the tree `git -C` commits into

**Severity:** low · **Category:** correctness · **Confidence:** high
**Location:** `.claude/hooks/gate.sh:66-81`

The detection regex deliberately recognises `git -C /repo commit`, but `root` comes from a bare
`git rev-parse --show-toplevel` in the hook's own cwd. A session whose cwd is outside the
checkout, committing into nanopnp with `-C`, fails the `pyproject.toml` check and `exit 0`s
ungated. The reverse case gates the wrong tree. It is narrow in practice, because sessions
usually sit in the repo.

**Suggested fix:** resolve the root from the `-C` or `--work-tree` value inside the matched
prefix. I tested the parsing below against `git -C /x commit -m "… -C /bad …"`, a plain
`git commit` and `--work-tree`.

```diff
diff --git a/.claude/hooks/gate.sh b/.claude/hooks/gate.sh
index 404fdfd..dcf582c 100755
--- a/.claude/hooks/gate.sh
+++ b/.claude/hooks/gate.sh
@@ -42,6 +42,7 @@ set -uo pipefail
 
 mode=hook
 [[ ${1:-} == run ]] && mode=run
+target_dir=.
 
 if [[ $mode == hook ]]; then
     payload=$(cat)
@@ -68,6 +69,12 @@ if [[ $mode == hook ]]; then
     # --no-verify / -n count only as options of that commit: quoted strings
     # are removed first, so `-m "document --no-verify"` is still gated.
     args=${BASH_REMATCH[${#BASH_REMATCH[@]} - 1]}
+    # The tree being committed is the one -C / --work-tree names, not this
+    # hook's cwd; gate that one.
+    prefix=${BASH_REMATCH[0]%%commit*}
+    if [[ $prefix =~ (-C|--work-tree)[[:space:]]+([^[:space:]]+) ]]; then
+        target_dir=${BASH_REMATCH[2]}
+    fi
     args=$(printf '%s' "$args" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")
     set -f
     for token in $args; do
@@ -76,7 +83,7 @@ if [[ $mode == hook ]]; then
     set +f
 fi
 
-root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
+root=$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null) || exit 0
 cd "$root" || exit 0
 [[ -f pyproject.toml && -d src/nanopnp ]] || exit 0
 
```

---

### CR-15 · Name-keyed cache serves stale fit coefficients after a correction file is edited

**Severity:** low · **Category:** correctness · **Confidence:** high
**Location:** `src/nanopnp/materials/models.py:291-294`

In a long-lived process (the GUI, or an in-process sweep), an edited `data/corrections/*.yaml`
changes the stage-8 hash, and the reference values are re-read through the text-keyed cache. The
fit coefficients still come from this name-keyed `@cache`. The result mixes new reference values
with old fits, and it is stored under the new key. `load_corrections` already caches the
expensive parse by file text, so dropping this cache costs only a Pydantic validation.

**Suggested fix:**

```diff
diff --git a/src/nanopnp/materials/models.py b/src/nanopnp/materials/models.py
index 02c691f..e730c4d 100644
--- a/src/nanopnp/materials/models.py
+++ b/src/nanopnp/materials/models.py
@@ -18,7 +18,6 @@ from __future__ import annotations
 
 from collections.abc import Callable, Mapping
 from dataclasses import dataclass, field
-from functools import cache
 from typing import Literal, Protocol, TypeAlias
 
 from nanopnp.core.paths import available_corrections
@@ -288,9 +287,13 @@ def _build_none(
     return NoCorrection(property_kind=property_kind, species=species)
 
 
-@cache
 def _document(model_name: str) -> CorrectionDocument:
-    """Return the validated parameter file, read once per model name."""
+    """Return the validated parameter file as it is on disk now.
+
+    Not cached by name: ``load_corrections`` already caches the parse by file
+    text, and a name-keyed cache would serve stale coefficients after an edit
+    the stage-8 hash has already seen.
+    """
     return load_corrections(model_name)
 
 
```

---

### CR-16 · The truncation gate treats the `r = 0` axis column as a cut edge

**Severity:** low · **Category:** correctness · **Confidence:** medium
**Location:** `src/nanopnp/density/grid.py:446-448`

A supplied field with its origin at `r = 0` and charge on the axis puts its maximum in the "boundary
ring", so `check_conservation` aborts with "the supplied grid is truncated". Nothing is discarded
there, because no mesh point lies at `r < 0`. The result is a loud but wrong refusal that
blames the wrong thing.

**Suggested fix:**

```diff
diff --git a/src/nanopnp/density/grid.py b/src/nanopnp/density/grid.py
index 93c40ea..6b35a61 100644
--- a/src/nanopnp/density/grid.py
+++ b/src/nanopnp/density/grid.py
@@ -445,7 +445,11 @@ class RadialGrid:
 
         ring = np.zeros_like(self.values, dtype=bool)
         ring[0, :] = ring[-1, :] = True
-        ring[:, 0] = ring[:, -1] = True
+        ring[:, -1] = True
+        # The r = 0 column is the axis, not a cut edge: no mesh point lies at
+        # r < 0, so the padding there discards nothing.
+        if self.origin_nm[0] > 0.0:
+            ring[:, 0] = True
         magnitude = np.where(ring, np.abs(self.values), -1.0)
         i_z, i_r = np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
         return RingMaximum(
```

---

### CR-17 · A Python loop re-implements `BitArray.NumSet()` on every render

**Severity:** low · **Category:** efficiency · **Confidence:** high
**Location:** `src/nanopnp/gui/render.py:401-419`

`_element_count` loops over every volume element in Python, which is about 121k on the reference
mesh, on each field render. Every other module counts the same mask with `.NumSet()`.

**Suggested fix:**

```diff
diff --git a/src/nanopnp/gui/render.py b/src/nanopnp/gui/render.py
index d7554e0..040dbe1 100644
--- a/src/nanopnp/gui/render.py
+++ b/src/nanopnp/gui/render.py
@@ -411,12 +411,9 @@ def _element_count(mesh: Mesh, domain: str | None) -> int:
     :func:`nanopnp.io.fields.p2_nodes` counts the same restriction for the
     IF-07 export, so the picture and the file agree about what was drawn.
     """
-    import ngsolve as ngs
-
     if domain is None:
         return int(mesh.ne)
-    keep = mesh.Materials(domain).Mask()
-    return sum(1 for element in mesh.Elements(ngs.VOL) if keep[element.index])
+    return int(mesh.Materials(domain).Mask().NumSet())
 
 
 def _replace(path: Path, text: str) -> None:
```

## Systemic observations

- **NaN-permissive gates.** CR-5, CR-6, CR-7 and CR-13 are the same bug: a check written as
  `value > tol` or `>=` that NaN passes. The reviewers found more instances in
  `solve/gates.py:372, 417, 542` (`PackingFractionGate`, `PotentialIncrementGate`,
  `WallDistanceGate`), in `mesh/profile.py:126-138` (NaN vertices) and in unchecked
  `RadialGrid` values. `PositivityGate` already uses the right form, `not value > 0`. One
  project rule would close all of these, with a lint-style test that greps gate modules for bare
  `>`/`<` against a tolerance: write every gate so that NaN fails it, or check `isfinite` at the
  boundary.
- **Fields that are recorded but not applied.** CR-1 and CR-2 both come from case fields that are
  hashed into provenance without reaching the operator. A tier-1 test would catch the next one:
  walk every `CaseDocument` leaf and assert that it either changes the assembled forms or is on
  an explicit "provenance-only" list.
- **Atomic writes only in the store.** `store._atomic_write_bytes` exists, but member records,
  manifests, run records and the plan are written in place with `write_bytes` into directories a
  job array writes concurrently. See the note below.

## Also noted outside the focus

Medium severity in a non-focused category, so listed rather than ranked:

- **Concurrency:** `sweep/run.py:164-169`. Member records are written non-atomically, and
  `read_members` treats a torn record as fatal. A tested patch writes to a random-suffixed temp
  file and renames it (`atomic-member.patch`). The same applies to `Manifest.write` and
  `RunResult.write`.
- **Concurrency:** `gui/render.py:609-625`. `terminate()` waits 1 s and never escalates, so an
  old render child stuck in a long NGSolve call can outlive it and race the new one in `viewer/`.
  A tested patch adds `kill()` after the join (`render-kill.patch`).
- **Correctness (example script):** `examples/05-clya-reference/render_slurm.py:69`. The sweep
  name is the only unquoted value in the generated SBATCH script (`slurm-name.patch`).

## Method and coverage

- **Orchestrator:** Opus 5.5. Fable, the recommended orchestrator, was unavailable in this
  session. **Reviewers:** 5 (3 Opus, 2 Sonnet), following the repo's `.claude/model-policy.md`.
- **Units:**

  | Unit | Scope | Lines | Model | Why this model |
  |---|---|---:|---|---|
  | U1 | `physics/`, `materials/` | 6,421 | Opus | weak forms, repo policy |
  | U2 | `solve/`, `post/`, `validation/` | 11,328 | Opus | QoI and gates, silent numerical errors |
  | U3 | `structure/` `density/` `symmetry/` `geometry/` `mesh/` `charge/` | 12,265 | Opus | geometry errors give plausible wrong numbers |
  | U4 | `io/`, `sweep/`, `core/` | 10,090 | Sonnet | schema and IO plumbing |
  | U5 | `gui/`, `cli/`, hooks, docs scripts, examples | 6,825 | Sonnet | thin shells, loud failures |

- **Verification:** the orchestrator re-read the cited code for every finding. 19 reviewer
  findings and 5 cross-unit leads went in, and 17 findings came out:
  - 2 came from cross-unit leads (CR-1, CR-2).
  - 1 pair was merged (U1's lead and U2-1).
  - 4 were re-graded down from high, and 1 had its patch replaced by a prose fix.
  - 3 were moved to "outside the focus".

  No finding was rejected outright. All 16 patches pass `git apply --check` against `d2fc2e3`,
  and all apply together cleanly. `ruff check` and `ruff format --check` pass on the patched
  files.
- **Not executed:** there was no project environment, so no finding was reproduced by running
  the code. CR-3, CR-9 and CR-13 in particular rest on reading.
- **Not reviewed:** `src/nanopnp/gui/assets/webgui/` (vendored, it has its own licence), `tests/`
  (read only for context), `docs/` prose and `data/*.yaml` values.

## Considered and rejected

None outright. Adjusted claims:

- **U4-2** (non-atomic member write): high → medium. A torn record makes collection fail loudly,
  and re-running the member fixes it.
- **U5-1** (gate `-C`): high → low. It needs a session whose cwd is outside the repo.
- **U5-2** (render terminate): high → medium, because the viewer is display-only and never
  hashed.
- **U4-1** (reproduce NaN): high → medium, because upstream gates normally stop a NaN before it
  is recorded.
- **U1-2's patch** used an `Electrolyte` attribute I could not confirm, so it became a prose fix
  (CR-10).
