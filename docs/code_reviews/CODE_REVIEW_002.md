# Code review: willemsk/nanopnp

2026-09-28 · commit `abe328a` (`claude/exciting-dijkstra-3gjuts`) · scope: `src/nanopnp/` (111 files, 46.3k lines; tests read for context only) · focus: correctness, efficiency

> **Status (2026-09-28, follow-up commit on the same branch):** CR-1 is fixed, by the design in its
> fix section (`io.run.stored_upstream`). The eight patches below (CR-3, CR-4, CR-5, CR-7, CR-9,
> CR-10, CR-11 and the golden-hash one) are applied. Regression tests cover CR-1
> (`tests/tier2/test_sweep_generated_mesh.py`), CR-4 and CR-9 (`tests/tier1/test_manifest.py`) and
> CR-5 (`tests/tier1/test_comparison_norms.py`); each new test fails on `abe328a`. CR-2 is fixed
> in a further commit under author ruling 13 (`⟨c⟩` has no meaning inside a solid): ion-free
> `ε_r,f⁰` off the fluid, the nearest solid's `ε_p` where `χ` reaches into it, three VER-30 tests.
> CR-6, CR-8 and CR-12 to CR-15 are fixed in a third commit. CR-6, CR-12, CR-13 and CR-14 each have
> a test that fails before the fix. CR-8 has a slab-thickness equivalence test, and CR-8 and CR-15
> were measured bit-identical against the old code. CR-6 follows the fix section; `golden_grid` is
> removed. CR-8 slices each atom's stencil to the slab: 27–30 s → 19–20 s at h = 0.025 nm and
> parity at 0.05 nm on 3,000 synthetic atoms. Bounding the `bincount` range was measured and left out,
> because its gain is within run-to-run noise at 0.025 nm and it costs up to 25 % at 0.05 nm. CR-12
> adds the stage-7 field record to the identity only where a field is supplied, so no published
> `case_hash` moves. CR-13 keys stage 7 on the element order and, with a dielectric field, the solid
> names (author's choice over rebuilding the manifest from the solve). CR-14 takes the review's fix
> alone, by the author's choice: stage 12 reads once, and the stage-11 restore still reads its own.
> CR-15 fills one preallocated array and transforms in place: bit-identical, with peak traced memory
> 3.4× → 2.0× the float64 ensemble. No finding is open.

## Summary

The codebase is in good shape where it is most often wrong elsewhere. Every solver gate, Newton test and current cross-check the reviewers traced is NaN-safe and aborts rather than logs. The signs of every weak-form term were re-derived and hold. Every correction switched to `none` reduces exactly to classical PNP-NS.

The defects found sit at the edges:
- **A promised speed-up that silently does nothing (CR-1).** Sweep warm starts never happen for generated-mesh cases, so every member climbs the full continuation ladder.
- **Two opt-in physics paths that evaluate ε_r,f where ⟨c⟩ does not exist (CR-2).** The ion-exclusion shell and the smoothed χ blend both get the infinite-dilution 78.15 instead of ε_r,f(⟨c⟩).
- **A hot-path cost (CR-3).** Gate sample points are rebuilt and re-located about twice per rung.
- **A validation harness that can report agreement over nothing (CR-5)**, plus two smaller biases in the attribution ladder.

The systemic pattern is values that are validated, or at least accepted, but never used or recorded (CR-4, CR-10 to CR-13), and coefficients evaluated outside the domain their inputs are defined on.

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 3 |
| Medium | 5 |
| Low | 7 |

## Findings at a glance

| ID | Sev | Category | Location | Finding |
|---|---|---|---|---|
| CR-1 | High | correctness / efficiency | `sweep/run.py:196-204` | Sweep warm start never happens for a generated-mesh case; every member solves cold |
| CR-2 | High | correctness (physics) | `physics/models.py:846-882` | Exclusion shell and χ blend use infinite-dilution ε_r = 78.15, and χ is ignored inside the fluid |
| CR-3 | High | efficiency | `solve/gates.py:163-224`, 6 call sites | `FieldSampler` rebuilt and re-located ~2× per rung + 3× per solve (~36 s per rung at 145k elements) |
| CR-4 | Medium | correctness (FR-25) | `io/defaults.py:75-82`, `io/case.py:591-601` | `wall_distance.max_distance_nm` is never recorded as a deviation and accepts 0, negative and NaN |
| CR-5 | Medium | correctness (validation) | `validation/compare.py:482-506`, `validation/probe.py:584-594` | A field comparison over zero points reports exact agreement; `_inside` turns any error into "outside" |
| CR-6 | Medium | correctness (validation) | `validation/attribution.py:593-603`, `cli/__init__.py:881` | Δ_ref and E_k are taken over different point sets, biasing the verdict to "reference-limited" |
| CR-7 | Medium | correctness (validation) | `validation/attribution.py:96, 434-436` | Absolute 1e-14 identity tolerance aborts the attribution report on correct input when E_k ≳ 10 |
| CR-8 | Medium | efficiency | `density/union.py:259-270, 354-373` | `deposit` evaluates each atom's full stencil in every slab it reaches (6.8× redundant at h = 0.025 nm) |
| CR-9 | Low | correctness | `io/case.py:2456-2461`, `core/scaling.py:108,163` | NaN, infinite or non-positive `concentration_M` and non-finite `bias_V` pass `resolve()` and the sweep plan |
| CR-10 | Low | correctness (FR-25) | `io/manifest.py:207-217` | Manifest hashes only the reference correction file, not every file the models read |
| CR-11 | Low | correctness | `materials/corrections.py:121-140`, `materials/models.py:345-350` | A per-species `fw` in a correction file validates and is silently ignored |
| CR-12 | Low | correctness (validation) | `validation/comsol.py:273-285`, `io/case.py:1821-1824` | Golden `case_identity` ignores the contents of supplied charge / ε_r fields |
| CR-13 | Low | correctness (FR-25) | `charge/stage.py:128-148, 437-440` | Stage-7 key omits element order and solid set; a cached conservation record from another order reaches the manifest |
| CR-14 | Low | efficiency | `solve/state.py:1063-1065`, `post/stage.py:436,658,721-726` | `restore` re-reads and re-gates supplied fields at stages 11 and 12; stage 12 reads the charge once more |
| CR-15 | Low | efficiency (memory) | `structure/read.py:601-612`, `structure/stage.py:242` | Stage 1 peaks at 3× a float64 copy of the ensemble to write a 0.5× float32 payload |

## Findings

### CR-1 · Sweep warm start never happens for a generated-mesh case

**Severity:** High · **Category:** correctness / efficiency (FR-24) · **Confidence:** high (the reviewer ran it; I traced it)
**Location:** `src/nanopnp/sweep/run.py:196-204` → `src/nanopnp/solve/stage.py:265-269` → `src/nanopnp/mesh/ingest.py:759-766`

`_parent_artefact` computes the parent's solve key from a bare case, with no upstream artefacts. For any case that generates its mesh (`inputs.profile` or `structure:` with no `inputs.mesh`), `SolveStage._prepare` calls `deployed_mesh(resolved, None)`. That raises `KeyError("... generates its mesh, and this stage was handed no stage-6 mesh artefact ...")`. The broad `except Exception` turns the error into a cold start with a logged reason.

The consequences:
- Every non-root member of a generated-mesh sweep climbs the full NUM-18 ladder (tens of rungs) instead of solving one warm rung.
- The WP21 D15 barrier logic in `sweep/plan.py`, which exists so that "ordinary salt sweeps keep their warm starts" on a generated mesh (`docs/plans/wp21-cad-assembly-and-meshing.md:86`), is moot.
- For supplied-mesh sweeps the same call costs a mesh ingest and gate per member just to compute a hash.

The only warm-path test (`tests/tier2/test_sweep.py`) uses a supplied `.vol` mesh, so it cannot see this.

```python
    parent = plan.point(point.parent)
    try:
        key = SolveStage().key(StageInputs(case=plan.case(point.parent, base=base)))
    except Exception as error:
        # A parent whose key cannot even be computed is a parent this member
        # cannot warm-start from, and that is a fallback rather than a failure:
        ...
        return None, f"the parent's artefact key could not be computed: {error}"
```

**Suggested fix (design):**
1. Build the parent key from the parent's own upstream artefacts, which the store already holds. For example, walk the parent case through `materials` with `only=True` and `write=False`, then call `SolveStage().key(StageInputs(case=parent, upstream=walk.artefacts))`. A generated mesh's key is its recipe, so this is cheap.
2. A simpler alternative is to read the parent member's recorded `solution` hash from `members/{parent:06d}.json`.
3. Either way, narrow the `except` to the one expected cause (the parent not having run yet, `MissingUpstreamError`), so that a genuine defect is not turned into a quiet cold start.

**Test that would catch it:** a Tier-2 two-point sweep on a generated mesh (`inputs.profile`) asserting that member 1 records `warm_start` rather than a cold reason.

### CR-2 · ε_r,f(⟨c⟩) is evaluated where ⟨c⟩ does not exist: the exclusion shell and the χ blend get the infinite-dilution permittivity

**Severity:** High (both paths are opt-in and recorded as deviations; within them the number is silently wrong) · **Category:** correctness (physics, PHY-20, §4.4 NOTE, §5.3.1 NOTE) · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/physics/models.py:846-882`, via `materials/fields.py:264-289`

`fluid_permittivity = coefficients.relative_permittivity()` is built from concentration functions that are `definedon` the fluid. Off the fluid they evaluate to 0, `average_concentration` clamps that to 1e-6 M, and ε_r,f comes out at its infinite-dilution value, 78.15, whatever the salt. This expression is then used off the fluid in two places.

1. **Ion-exclusion shell (FR-15, `charge.exclusion_offset_nm > 0`).**
   - `exclusion` is `PERMITTIVITY_EXEMPT` and falls through to `MaterialCF(default=fluid_permittivity)`.
   - `mesh/primitives.py:55-64` and `mesh/ingest.py:107-115` say it must take the electrolyte's ε_r, because any other value "would put a dielectric jump at the shear plane".
   - Reproduced (unit A `probe8.py`: `pnp` model, permittivity correction on, 3 M, `SlabGeometry(width_nm=5, exclusion_nm=0.3)`): ε_r = **78.150** in the shell against **51.09** in the electrolyte beside it. The Stern capacitance ε/λ_S is 53 % high at 3 M, and the error grows with salt.
   - VER-31 exercises the shell with Poisson–Boltzmann only, so no test sees it.
2. **Supplied solid fraction χ (`inputs.eps_r`).** The §4.4 NOTE requires ε_r = χ·ε_p + (1 − χ)·ε_r,f(⟨c⟩), and the whole stated reason for a χ field is that the transition goes to the *corrected* ε_w. The code gets it wrong on both sides of the boundary:
   - **In fluid materials** the "solid" branch is the `MaterialCF` default, which is ε_f itself. Any χ > 0 there is discarded. The 1–2 Å transition does reach into the fluid: `FLUID_MEAN_CEILING` admits a fluid mean χ of up to 0.1.
   - **Inside solids** the fluid branch is the 78.15 value, not ε_r,f(⟨c⟩).
   - Reproduced (unit A `probe7.py`, 3 M, membrane ε_p = 3.2) with a uniform χ, as a mechanism check:

     | χ | fluid (spec) | membrane (spec) |
     |---|---|---|
     | 0.3 | 51.09 (36.72) | 55.67 (36.72) |
     | 0.9 | 51.09 (7.99) | 10.70 (7.99) |

   - `test_ver30_the_blend_is_a_convex_combination_of_the_two_branches` passes, because it checks only fluid points, where all three evaluations equal ε_f.

The Maxwell-stress and post-processing routes (`post/forces.py:986`, `post/stage.py:674`) call `model.permittivity(...)` and inherit this.

```python
        fluid_permittivity = coefficients.relative_permittivity()
        ...
        if not self.solid_permittivities:
            solids: Expression = fluid_permittivity
        else:
            reference = self.electrolyte.permittivity_0
            solids = mesh.MaterialCF(
                {material: value / reference for material, value in self.solid_permittivities.items()},
                default=fluid_permittivity,
            )
        if solid_fraction is None:
            return solids
        return blend(solid_fraction, solids, fluid_permittivity)
```

**Suggested fix (needs a specification decision first; no patch offered):** ε_r,f needs a ⟨c⟩ that exists off the fluid. The options, which the §4.4 and §5.3.1 NOTEs should settle in the same commit, are:
- evaluate the fluid branch off-fluid at the bulk ⟨c⟩ (simple, but still a small jump at the shear plane);
- extend ⟨c⟩ into the shell from the adjacent fluid.

Separately, give the solid branch a value inside fluid materials (the protein's ε_p where χ > 0), or gate `max χ == 0`, not just its mean, on every fluid-branch material. Add VER-30 assertions at points with 0 < χ < 1 on each side of the boundary, and a VER-31-style check of the shell with the permittivity correction on.

### CR-3 · `FieldSampler` is rebuilt and re-located about twice per rung and three more times per solve

**Severity:** High · **Category:** efficiency · **Confidence:** high (measured)
**Location:** `src/nanopnp/solve/gates.py:163-224`. The call sites are `physics/models.py:1233,1245` (per rung), `solve/state.py:384` (NUM-34), `solve/continuation.py:730` (Péclet), `post/qoi.py:842` (clamp report) and `physics/pb.py:368`.

`FieldSampler` caches its points and their mesh location on the instance, but every call site constructs a new one. The fluid sampler builds its point list in a Python loop over elements, then locates every point by a mesh search.

Re-measured on a 144,628-element mesh with the repo's `.venv` (`review/B/sampler_time.py`):

| Sampler | Points | Build | Locate | Evaluate one field |
|---|---:|---:|---:|---:|
| Fluid-restricted | 1,012,396 | 2.7 s | 21.7 s | — |
| Whole mesh | 434,885 | 2.9 s | 9.4 s | 0.23 s |

`CoupledModel.gates` builds both samplers on every rung, which is about 36 s of set-up per rung against roughly 200 s of Newton at the reference mesh. The mesh is fixed for the whole run (NUM-19), so the points never change. A warm sweep member pays for about five samplers; a full ~20-rung ladder pays several minutes.

```text
        fluid_sampler = FieldSampler(
            mesh, coordinates=measures.coordinate_names, materials=self.fluid
        )
        ...
        potential_sampler = FieldSampler(mesh, coordinates=measures.coordinate_names)
```

**Suggested fix (applied and tested):** share one sampler per mesh and material set. The reviewer's `WeakKeyDictionary` proposal does not work, because NGSolve's `Mesh` is unhashable (checked). The patch keeps the cache on the mesh object instead. I checked that the mesh ↔ sampler reference cycle is garbage-collected, so the cache dies with its mesh. `model.fluid` defaults to `ELECTROLYTE_DOMAINS`, so the rung, NUM-34, Péclet and clamp samplers all share one entry.

```diff
diff --git a/src/nanopnp/physics/models.py b/src/nanopnp/physics/models.py
index 797a91b..537579a 100644
--- a/src/nanopnp/physics/models.py
+++ b/src/nanopnp/physics/models.py
@@ -1230,7 +1230,7 @@ class CoupledModel:
             in :meth:`solve`.
         """
         fields = self._split(list(state.components))
-        fluid_sampler = FieldSampler(
+        fluid_sampler = FieldSampler.shared(
             mesh, coordinates=measures.coordinate_names, materials=self.fluid
         )
         variables = self.concentration_variables(fields)
@@ -1242,7 +1242,7 @@ class CoupledModel:
         ]
         if increment is None:
             return state_gates, []
-        potential_sampler = FieldSampler(mesh, coordinates=measures.coordinate_names)
+        potential_sampler = FieldSampler.shared(mesh, coordinates=measures.coordinate_names)
         potential_increment = self._split(list(increment.components))[POTENTIAL]
         return state_gates, [PotentialIncrementGate(potential_sampler, potential_increment)]
 
diff --git a/src/nanopnp/physics/pb.py b/src/nanopnp/physics/pb.py
index 14830ff..e79d43c 100644
--- a/src/nanopnp/physics/pb.py
+++ b/src/nanopnp/physics/pb.py
@@ -365,7 +365,7 @@ def solve_pb_recorded(
         residual += term
 
     increment = ngs.GridFunction(space, name="delta_phi_tilde")
-    sampler = FieldSampler(mesh, coordinates=measures.coordinate_names)
+    sampler = FieldSampler.shared(mesh, coordinates=measures.coordinate_names)
     result = damped_newton(
         residual,
         potential,
diff --git a/src/nanopnp/post/qoi.py b/src/nanopnp/post/qoi.py
index 4986492..2f34a78 100644
--- a/src/nanopnp/post/qoi.py
+++ b/src/nanopnp/post/qoi.py
@@ -839,7 +839,7 @@ def report_clamp_activations(solution: ModelSolution, measures: Measures) -> int
         solution stayed inside the fit range.
     """
     model = _coupled(solution)
-    sampler = FieldSampler(
+    sampler = FieldSampler.shared(
         solution.space.mesh, coordinates=measures.coordinate_names, materials=model.fluid
     )
     variables = model.concentration_variables(_functions(solution))
diff --git a/src/nanopnp/solve/continuation.py b/src/nanopnp/solve/continuation.py
index f454598..35529b7 100644
--- a/src/nanopnp/solve/continuation.py
+++ b/src/nanopnp/solve/continuation.py
@@ -727,7 +727,7 @@ def _report_peclet(solution: ModelSolution, measures: Measures) -> PecletMeasure
     if not isinstance(model, CoupledModel):
         return None
     return PecletDiagnostic(
-        FieldSampler(
+        FieldSampler.shared(
             solution.space.mesh,
             coordinates=measures.coordinate_names,
             materials=model.fluid,
diff --git a/src/nanopnp/solve/gates.py b/src/nanopnp/solve/gates.py
index ff45d31..4dc8e08 100644
--- a/src/nanopnp/solve/gates.py
+++ b/src/nanopnp/solve/gates.py
@@ -129,6 +129,10 @@ class GateViolationError(RuntimeError):
         super().__init__(f"{gate} gate failed: {quantity} = {value:.6g}{where}{clause}")
 
 
+_SAMPLER_CACHE = "_nanopnp_field_samplers"
+"""Attribute on an NGSolve mesh holding :meth:`FieldSampler.shared`'s cache."""
+
+
 @dataclass
 class FieldSampler:
     """Evaluates coefficient functions at the P2 nodal set of a mesh.
@@ -153,6 +157,34 @@ class FieldSampler:
     _points: np.ndarray | None = field(default=None, init=False, repr=False, compare=False)
     _located: Expression | None = field(default=None, init=False, repr=False, compare=False)
 
+    @classmethod
+    def shared(
+        cls,
+        mesh: Mesh,
+        *,
+        coordinates: tuple[str, str] = ("r", "z"),
+        materials: str | None = None,
+    ) -> FieldSampler:
+        """Return the one sampler of this mesh and material set, built on first use.
+
+        Building the point set and locating it costs seconds per sampler at the
+        reference mesh size, against a fraction of a second to evaluate on it,
+        and the rung gates, NUM-34, the Peclet report and the clamp report each
+        want the same points on the same fixed mesh. Kept on the mesh itself, so
+        the cache dies with the mesh rather than keeping it alive.
+        """
+        cache: dict[tuple[tuple[str, str], str | None], FieldSampler] | None = getattr(
+            mesh, _SAMPLER_CACHE, None
+        )
+        if cache is None:
+            cache = {}
+            setattr(mesh, _SAMPLER_CACHE, cache)
+        key = (coordinates, materials)
+        found = cache.get(key)
+        if found is None:
+            found = cache[key] = cls(mesh, coordinates=coordinates, materials=materials)
+        return found
+
     @property
     def points(self) -> np.ndarray:
         """Return the sample points as an ``(n, 2)`` array, computed once."""
diff --git a/src/nanopnp/solve/state.py b/src/nanopnp/solve/state.py
index 4b0706a..b29765a 100644
--- a/src/nanopnp/solve/state.py
+++ b/src/nanopnp/solve/state.py
@@ -381,7 +381,7 @@ def check_wall_distance(
     """
     if not reads_wall(resolved.electrolyte):
         return None
-    sampler = FieldSampler(mesh, coordinates=coordinates, materials=ELECTROLYTE_DOMAINS)
+    sampler = FieldSampler.shared(mesh, coordinates=coordinates, materials=ELECTROLYTE_DOMAINS)
     return WallDistanceGate(sampler, distance).checked()
 
 
```

The restricted sampler also keeps duplicate points on purpose (1.01 M points for 145k elements, so each stays inside its own element). A further gain is available: every sample point is defined by its element and a fixed reference coordinate, so the `MeshPoint` array can be built directly with no search. Unit B prototyped this at 0.27 s against 22.7 s, matching positions to 1e-16 (`review/B/direct.py`). It is not included here because it depends on NGSolve's `MeshPoint` dtype layout.

### CR-4 · `numerics.wall_distance.max_distance_nm` is never recorded as a deviation, and accepts 0, negative and NaN

**Severity:** Medium · **Category:** correctness (FR-25, PHY-02) · **Confidence:** high (run)
**Location:** `src/nanopnp/io/defaults.py:75-82`; `src/nanopnp/io/case.py:591-601`

The spec defines `max_distance_nm` as the saturation distance beyond which the wall functions are 1 to round-off (§5.3.1 NOTE). `mesh/distance.py` caps `d` at it:
- At a cap of 0.3 nm, f_ion = 1 − exp(−6.2 · 0.31) ≈ 0.85 across the whole pore.
- At a cap of 0, d ≡ 0 and the diffusivity factor is about 0.06 everywhere. The NUM-34 gate still passes, because d is not negative.

The path is missing from `SWITCH_PATHS`, so `deviations()` returns `[]` for any cap, even though the `SwitchValue` docstring names `max_distance_nm` as a switch. Nothing refuses a cap that is not finite and positive. I checked the patched tree: 3.0 records no deviation, 0.3 records `numerics.wall_distance.max_distance_nm`, and NaN is refused naming the key.

```python
    "numerics.wall_distance.sources",
    "numerics.linear.solver",
)
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/io/defaults.py b/src/nanopnp/io/defaults.py
index 8218a6b..758ae8a 100644
--- a/src/nanopnp/io/defaults.py
+++ b/src/nanopnp/io/defaults.py
@@ -78,6 +78,9 @@ SWITCH_PATHS: tuple[str, ...] = (
     "numerics.nonlinear.strategy",
     "numerics.nonlinear.damping",
     "numerics.wall_distance.sources",
+    # PHY-02: the saturation distance. A float, classified by hand as the charge
+    # offsets above are: below ~1 nm the wall functions no longer reach 1.
+    "numerics.wall_distance.max_distance_nm",
     "numerics.linear.solver",
 )
 """Every switch with a validated default, by dotted path into the case document."""
```

The refusal is in the CR-9 patch (`_check_operating_point`). It is a check in `resolve()`, not a schema narrowing, per the §5.3.1 compatibility rule.

### CR-5 · A field comparison over zero probe points reports exact agreement

**Severity:** Medium · **Category:** correctness (validation, QR-12) · **Confidence:** high (run by the reviewer; code traced)
**Location:** `src/nanopnp/validation/compare.py:482-506, 530-547`; `src/nanopnp/validation/probe.py:584-594`

`field_error` with an all-false `keep` returns `points=0, rel_L2_r=0.0, rel_l2=0.0, max_abs_rel=0.0`, which reads as perfect agreement. Nothing checks for a non-empty mask: not `on_mesh`, `compare_fields`, `field_error` or `reference_error`. The mask gate compares two empty masks as equal.

`_inside` makes empty masks easy to get: both of its `except Exception` clauses turn *any* evaluation failure into "outside". That covers an NGSolve API change or a coefficient that cannot be evaluated, not just a point outside the mesh. A self-golden built by the same code is then all-NaN, and the Tier-2 round trip reports 0.0 on every field. A COMSOL golden would fail the mask gate instead, so the vacuous pass is specific to self-goldens. That is exactly the harness's own regression test.

```python
    scale = float(np.max(np.abs(reference))) if reference.size else 0.0
    ...
        max_abs_rel=float(np.max(np.abs(difference)) / scale) if scale > 0.0 else 0.0,
...
        except Exception:  # NGSolve raises a bare NgException for a point it cannot find
            ...
                except Exception:  # outside the mesh is outside every material
                    continue
```

**Suggested fix:** refuse an empty mask, and narrow the catch to NGSolve's "not in mesh" `NgException`. I confirmed that both the batch and single-point lookups raise `netgen.meshing.NgException("Meshpoint ... not in mesh!")`.

```diff
diff --git a/src/nanopnp/validation/compare.py b/src/nanopnp/validation/compare.py
index 6caddde..8653657 100644
--- a/src/nanopnp/validation/compare.py
+++ b/src/nanopnp/validation/compare.py
@@ -479,6 +479,11 @@ def field_error(
     """
     import numpy as np
 
+    if not bool(np.any(keep)):
+        raise ProbeGridError(
+            f"field {field!r}: the mask retains no probe point, so there is nothing to compare. "
+            "A norm over no points is 0 and would read as exact agreement (QR-12)"
+        )
     points = np.asarray(grid.points_nm, dtype=np.float64)[keep]
     radial = np.asarray(grid.weights_nm2, dtype=np.float64)[keep] * points[:, 0]
     mine, reference = ours[keep], theirs[keep]
diff --git a/src/nanopnp/validation/probe.py b/src/nanopnp/validation/probe.py
index 97891d4..6d6c1f7 100644
--- a/src/nanopnp/validation/probe.py
+++ b/src/nanopnp/validation/probe.py
@@ -580,15 +580,20 @@ class ProbeGrid:
         nothing.
         """
         import numpy as np
+        from netgen.meshing import NgException
 
         try:
             sampled = np.asarray(indicator(mesh(points[:, 0], points[:, 1])), dtype=np.float64)
-        except Exception:  # NGSolve raises a bare NgException for a point it cannot find
+        except NgException:  # NGSolve raises a bare NgException for a point it cannot find
             values = np.zeros(points.shape[0], dtype=np.float64)
             for index, (r_nm, z_nm) in enumerate(points):
                 try:
                     values[index] = float(indicator(mesh(r_nm, z_nm)))
-                except Exception:  # outside the mesh is outside every material
-                    continue
+                except NgException as error:
+                    # Outside the mesh is outside every material; any other
+                    # failure is a defect, and reading it as "outside" would
+                    # empty the mask and report agreement over nothing.
+                    if "not in mesh" not in str(error):
+                        raise
             sampled = values
         return sampled.reshape(points.shape[0]) > 0.5
```

### CR-6 · Δ_ref and E_k are measured over different point sets

**Severity:** Medium · **Category:** correctness (validation, VAL-04) · **Confidence:** medium (mechanism traced; the size of the bias was not measured)
**Location:** `src/nanopnp/validation/attribution.py:593-603`; caller `src/nanopnp/cli/__init__.py:881`

The two errors the verdict compares are taken over different points:
- **E_k** comes from `compare_fields` over `grid.masks[field]`. That is the margin-eroded mask, which drops the 0.05 nm band next to every fluid/solid interface.
- **Δ_ref** uses `fine.defined(name)`, the golden's whole defined set, band included. COMSOL exports values in that band (`probe.py:450-463`).

The CLI passes `golden_grid(...)`, whose masks are all true, so the band is never removed from Δ_ref. For `c_i`, velocity and pressure, Δ_ref therefore includes the near-wall points where the two discretisations disagree most, and E_k excludes them. `verdict()` compares `residual < reference_error`, so the report reads "reference-limited" too readily, although the docstring says the two are "two of one quantity". The potential has no band and is unaffected.

```python
    for name in sorted(set(coarse.values) & set(fine.values)):
        keep = fine.defined(name)
        check_mask_agreement(name, keep, coarse.defined(name), grid)
        comparison = field_error(
            name,
            np.asarray(coarse.values[name], dtype=np.float64),
            np.asarray(fine.values[name], dtype=np.float64),
            grid,
            keep,
        )
```

**Suggested fix (prose):** take Δ_ref over `fine.defined(name) & grid.masks[name]`, and have `_validate_report` pass one rung's mesh-bound grid (`_probe_grid(document, resolved)`) rather than `golden_grid`. The reviewer's one-file diff is a no-op on its own, because `golden_grid`'s masks are all true. Both halves have to change together.

### CR-7 · The ladder's identity check uses an absolute tolerance and aborts on correct input

**Severity:** Medium · **Category:** correctness (a crash on valid data) · **Confidence:** high (reproduced)
**Location:** `src/nanopnp/validation/attribution.py:96-102, 434-436`

`IDENTITY_TOLERANCE = 1e-14` is absolute. Its docstring assumes the E_k are "of order one", but an E_k is a relative error, and it exceeds 10 wherever the golden is small but non-zero (a near-zero current at low bias, an EOF rate). The round-off of the telescoped sum grows with |E|.

Reproduced with the real `Attribution` class and 100k random draws:

| Range of E_k | Failure rate |
|---|---:|
| [0, 2] | 0 |
| [10, 100] | 2.7 % |
| [100, 1000] | 16.1 % |

A failure raises a `LadderError` that blames "a defect in how they were formed" and aborts the whole report. (The reviewer's specific example tuple does not reproduce: its residual is −3.6e-15. The statistical claim does.)

```python
        for entry in self.attributions:
            residual = entry.identity_residual()
            if not math.isfinite(residual) or abs(residual) > tolerance:
```

**Suggested fix:**

```diff
diff --git a/src/nanopnp/validation/attribution.py b/src/nanopnp/validation/attribution.py
index 265867f..096785b 100644
--- a/src/nanopnp/validation/attribution.py
+++ b/src/nanopnp/validation/attribution.py
@@ -94,11 +94,13 @@ ATTRIBUTION_SCHEMA = "nanopnp/attribution/v1"
 """Schema identifier of the report, and the separator of its content hash."""
 
 IDENTITY_TOLERANCE = 1e-14
-"""Absolute tolerance on the telescoped sum.
+"""Tolerance on the telescoped sum, relative to ``max(1, |E_k|)``.
 
 The identity is exact in real arithmetic, so what is left is the round-off of
-four additions of numbers of order one: about 1e-16. Asserting at 1e-14 leaves
-two orders of headroom and still fails on any real slip in forming the deltas.
+four additions: about 1e-16 of the largest ``E_k``. Asserting at 1e-14 of that
+leaves two orders of headroom and still fails on any real slip in forming the
+deltas. Not absolute: an ``E_k`` is a relative error, which exceeds 10 wherever
+the golden is small, and an absolute 1e-14 then fails on correct input.
 """
 
 Verdict = Literal["reference-limited", "attributed", "reference-unbounded"]
@@ -433,7 +435,10 @@ class AttributionReport:
         """
         for entry in self.attributions:
             residual = entry.identity_residual()
-            if not math.isfinite(residual) or abs(residual) > tolerance:
+            # Relative to the largest E_k: an E_k is a relative error and is not
+            # bounded by 1, and the round-off of the telescoped sum grows with it.
+            scale = max(1.0, *(abs(value) for value in entry.errors))
+            if not math.isfinite(residual) or abs(residual) > tolerance * scale:
                 raise LadderError(
                     f"the ladder identity fails for {entry.kind} {entry.key!r}: "
                     f"delta_total + delta_transport + delta_flow + delta_pair - delta_resid = "
```

### CR-8 · `deposit` evaluates each atom's whole stencil again in every z-slab it reaches

**Severity:** Medium (only at fine grid spacing) · **Category:** efficiency · **Confidence:** high (measured by the reviewer; structure confirmed)
**Location:** `src/nanopnp/density/union.py:259-270` (`_accumulate`), `:325, 354-373` (`deposit`)

A slab is `SLAB_CELLS // n²` planes thick. At h = 0.025 nm, which FR-04 admits, a ClyA-sized grid gives slabs 10 planes thick, while a heavy atom's stencil is 59 planes deep. Each atom therefore reaches about 7 slabs, and in each one the full product `g` over roughly 1.1e5 offsets is computed before the `plane` filter discards most of it.

Measured by unit D on 3,000 synthetic atoms:

| Spacing | Stencil terms evaluated vs needed | Time now | Time with in-slab slicing |
|---|---:|---:|---:|
| h = 0.025 nm | 6.8× | 41.1 s | 25.6 s (bit-identical map) |
| h = 0.05 nm (default) | 1.73× | 3.1 s | 2.8 s |

At h = 0.025 this is roughly 2 h of a ~5 h stage-2 run on the reference ensemble.

```text
    g = (
        factors[0][:, stencil.ox + m]
        * factors[1][:, stencil.oy + m]
        * factors[2][:, stencil.oz + m]
    )
    plane = node[atoms, 2][:, None] + stencil.oz[None, :]
    keep = (g >= EPSILON) & (plane >= first) & (plane < last)
```

**Suggested fix (design):**
- `stencil.oz` is sorted ascending (the `indexing="ij"` meshgrid), so each atom's in-slab offsets are one contiguous slice, `[searchsorted(oz, first − node_z), searchsorted(oz, last − node_z))`. Gather `g` only over those slices, using `np.repeat` for the indices.
- Bound each batch's `bincount` range as well. Its output currently spans the whole batch index range, a median of 3.7e6 entries for 1.5e5 kept terms.

### CR-9 · Non-finite or non-positive `concentration_M` and non-finite `bias_V` pass `resolve()` and the sweep plan

**Severity:** Low · **Category:** correctness · **Confidence:** high (run)
**Location:** `src/nanopnp/io/case.py:2456-2461`; `src/nanopnp/core/scaling.py:108, 163`

`resolve()` accepts `concentration_M` of NaN, inf or −0.5, and a non-finite bias. `sweep/plan.py` resolves every point at plan time so that an inadmissible one fails "in seconds rather than at hour twenty-two", but these points pass. The failure then surfaces per member: `Scales.__post_init__` catches a value ≤ 0, but a NaN reaches Newton, because the `value <= 0.0` guards are False for NaN.

**Suggested fix (also carries CR-4's refusal):**

```diff
diff --git a/src/nanopnp/core/scaling.py b/src/nanopnp/core/scaling.py
index b8a4818..14680d6 100644
--- a/src/nanopnp/core/scaling.py
+++ b/src/nanopnp/core/scaling.py
@@ -105,7 +105,7 @@ def debye_length_nm(
     ValueError
         If the concentration is not positive.
     """
-    if concentration_M <= 0.0:
+    if not concentration_M > 0.0:  # NaN fails too
         raise ValueError(f"concentration must be positive, got {concentration_M} M")
     permittivity = VACUUM_PERMITTIVITY * relative_permittivity
     concentration_mol_m3 = concentration_M * MOL_PER_M3_PER_MOL_PER_L
@@ -160,7 +160,7 @@ class Scales:
             "relative_permittivity",
         ):
             value = getattr(self, name)
-            if value <= 0.0:
+            if not value > 0.0:  # NaN fails too
                 raise ValueError(f"scale {name} must be positive, got {value}")
 
     # -- primitive scales ------------------------------------------------
diff --git a/src/nanopnp/io/case.py b/src/nanopnp/io/case.py
index 03bb086..e8d6558 100644
--- a/src/nanopnp/io/case.py
+++ b/src/nanopnp/io/case.py
@@ -2387,6 +2387,29 @@ def _model_options(
     return options
 
 
+def _check_operating_point(document: CaseDocument) -> None:
+    """Refuse a concentration, bias or distance cap no solve could use.
+
+    Written so that NaN fails every test: ``nan <= 0`` is False, and a sweep
+    plan resolves every point precisely so that an inadmissible one fails at
+    plan time rather than after a ladder of non-converging Newton.
+    """
+    concentration = document.electrolyte.concentration_M
+    if not (math.isfinite(concentration) and concentration > 0.0):
+        raise CaseValidationError(
+            f"electrolyte.concentration_M is {concentration!r}; it must be finite and positive"
+        )
+    bias = document.boundary_conditions.bias_V
+    if not math.isfinite(bias):
+        raise CaseValidationError(f"boundary_conditions.bias_V is {bias!r}; it must be finite")
+    cap = document.numerics.wall_distance.max_distance_nm
+    if not (math.isfinite(cap) and cap > 0.0):
+        raise CaseValidationError(
+            f"numerics.wall_distance.max_distance_nm is {cap!r}; the PHY-02 saturation distance "
+            "must be finite and positive, or the wall functions are evaluated at a capped d"
+        )
+
+
 def resolve(document: CaseDocument) -> ResolvedCase:
     """Turn a validated case document into the objects the solver takes.
 
@@ -2424,6 +2447,7 @@ def resolve(document: CaseDocument) -> ResolvedCase:
         driver=document.electrolyte.driver,
     )
     _check_species(document, electrolyte)
+    _check_operating_point(document)
 
     elements = document.numerics.elements
     order = _order(elements.phi, "phi")
```

### CR-10 · The manifest hashes only the reference correction file

**Severity:** Low (latent: only `willems2020_nacl.yaml` ships) · **Category:** correctness (FR-25, §5.3.3) · **Confidence:** high
**Location:** `src/nanopnp/io/manifest.py:207-217`

A correction model may name a file other than `electrolyte.parameters`, and its fit coefficients are then read from that file. `MaterialsStage.run` keys every such file (`materials/stage.py:82-87`), so the cache is right. The manifest's `parameter_file_hashes` lists only the reference file, though, so the version of the second file is absent. FR-16 makes a new electrolyte a data-only change, which is exactly when this bites.

**Suggested fix:**

```diff
diff --git a/src/nanopnp/io/manifest.py b/src/nanopnp/io/manifest.py
index 78bb115..4be947e 100644
--- a/src/nanopnp/io/manifest.py
+++ b/src/nanopnp/io/manifest.py
@@ -34,7 +34,7 @@ from importlib import metadata
 from typing import TYPE_CHECKING
 
 from nanopnp.core.hashing import Canonicalisable, canonical, content_hash, file_hash
-from nanopnp.core.paths import correction_file
+from nanopnp.core.paths import available_corrections, correction_file
 from nanopnp.io.artefact import timestamp
 from nanopnp.io.defaults import ContributedDeviation, Deviation, deviations
 from nanopnp.io.store import atomic_write_bytes
@@ -206,14 +206,18 @@ def materials_group(
     """
     provenance = dict(electrolyte.provenance)
     name = str(provenance.get("parameter_file", "") or "")
+    # Every file the models read, as MaterialsStage keys them: a correction model
+    # may name a file other than the reference one, and read its fit from there.
+    named = {model.name for model in electrolyte.corrections.values()}
+    read = sorted(({name} if name else set()) | (named & set(available_corrections())))
     files: dict[str, Canonicalisable] = {}
-    if name:
+    for each in read:
         try:
-            path = correction_file(name)
+            path = correction_file(each)
         except FileNotFoundError:
-            files[name] = None
+            files[each] = None
         else:
-            files[name] = file_hash(path)
+            files[each] = file_hash(path)
     provenance["parameter_file_hashes"] = files
     provenance["clamp_activations"] = (
         clamp_activations
```

### CR-11 · A per-species `fw` in a correction file validates and is silently ignored

**Severity:** Low · **Category:** correctness (accepted but never applied) · **Confidence:** high (run by the reviewer)
**Location:** `src/nanopnp/materials/corrections.py:110-140`; `src/nanopnp/materials/models.py:345-350`

`DiffusivityBlock` and `MobilityBlock` inherit `fw` from `PropertyBlock`. The builder reads the file's shared `ion_wall_function` for species properties and never reads their own `fw`. The class docstring says "`fw` is absent on those", but nothing enforces it. A file carrying `species.Na+.diffusivity.fw` loads, and its fit is dropped without a word.

**Suggested fix (the shipped NaCl file and the 59 materials tests pass with it):**

```diff
diff --git a/src/nanopnp/materials/corrections.py b/src/nanopnp/materials/corrections.py
index 8b32f81..2bb4393 100644
--- a/src/nanopnp/materials/corrections.py
+++ b/src/nanopnp/materials/corrections.py
@@ -123,13 +123,27 @@ class PropertyBlock(_Strict):
     cap_above_validity: float | None = None
 
 
-class DiffusivityBlock(PropertyBlock):
+class _IonPropertyBlock(PropertyBlock):
+    """An ion property: its wall fit is the file's shared ``ion_wall_function``."""
+
+    @model_validator(mode="after")
+    def _no_own_wall_fit(self) -> _IonPropertyBlock:
+        """Refuse a per-species ``fw``, which the builder never reads (PHY-11)."""
+        if self.fw is not None:
+            raise ValueError(
+                "an ion diffusivity or mobility takes the file's ion_wall_function; a "
+                "per-species fw here would be accepted and never applied"
+            )
+        return self
+
+
+class DiffusivityBlock(_IonPropertyBlock):
     """One species' diffusivity: ``D0`` at infinite dilution and its fit."""
 
     D0: float
 
 
-class MobilityBlock(PropertyBlock):
+class MobilityBlock(_IonPropertyBlock):
     """One species' mobility: the tabulated ``mu0`` (a regression target) and fit.
 
     ``mu0`` is not read by the solver — PHY-14 derives the mobility from ``D0`` —
```

### CR-12 · The golden `case_identity` ignores the contents of supplied fields

**Severity:** Low (latent: the five frozen ClyA cases supply no field) · **Category:** correctness (validation) · **Confidence:** medium
**Location:** `src/nanopnp/validation/comsol.py:273-285`, with its data from `src/nanopnp/io/case.py:1821-1824`

`solve_provenance` records only *whether* a charge or ε_r field was supplied. The solve key is safe, because the stage-7 artefact hashes the contents. `case_identity`, however, is built from `solve_provenance` alone, so two cases differing only in their charge table (another protonation state, another PDB) share a `case_hash`, and `Golden.check_case` accepts the wrong golden.

**Suggested fix (prose):** add the stage-7 grid digests, or `file_hash` of each field's data, to the identity record. This changes the published `case_hash`, so the export contract changes in the same commit.

### CR-13 · The stage-7 key omits the element order and the solid set its gates use

**Severity:** Low · **Category:** correctness (FR-25 provenance) · **Confidence:** medium (traced)
**Location:** `src/nanopnp/charge/stage.py:128-148, 417-440`; `io/run.py:711`

The `FieldsArtefact` key is the field contents plus the mesh hash, and the mesh key carries no element order. Its summary, however, holds conservation integrals taken at `model_options.order` and χ means classified by `physics.solid_permittivities`. Two cases differing only in `order` share the artefact, so the second run's manifest Charge group records conservation measured at the first run's quadrature. The physics is still gated correctly, because `solve/stage.py:351` re-runs `gate_fields` at its own order; only the record is stale.

**Suggested fix (prose):** add `{"element_order": order, "solids": sorted(solid_permittivities)}` to the stage-7 parameters, or take the manifest's Charge group from the solve's own gated `ResolvedFields.summary()`.

### CR-14 · `restore` re-reads and re-gates the supplied fields at stages 11 and 12

**Severity:** Low (adjusted from medium) · **Category:** efficiency · **Confidence:** high
**Location:** `src/nanopnp/solve/state.py:1063-1065`; `src/nanopnp/post/stage.py:436-438, 658-660, 721-726`

Stage 10 parses and gates a supplied charge or ε_r table once. `restore` parses and gates it again for stage 11, and again for stage 12 when `fields` is requested, and `_fixed_charge` then parses it once more.

The reviewer costed this from the comment at `charge/fields.py:386` ("parsing the 77 MB reference table ... costs a minute"). That comment is stale: an 84 MB `%Grid` table parses in **1.6 s** (re-measured). So this is seconds per run, plus the conservation integrals, not minutes.

**Suggested fix (prose):** give `restore` an optional `fields: ResolvedFields | None` to use in place of the read-and-gate, and take `_fixed_charge` from the fields the restore already holds. Also correct the stale comment.

### CR-15 · Stage 1 peaks at 3× a float64 copy of the ensemble

**Severity:** Low · **Category:** efficiency (memory) · **Confidence:** high (pattern measured with tracemalloc; not measured on a real ensemble)
**Location:** `src/nanopnp/structure/read.py:601-612`; `src/nanopnp/structure/stage.py:242`

`positions_nm` holds a per-frame list and its `np.stack` copy at the same time, and `align` then allocates `positions - foot` and the matmul result beside `positions`. At 10⁵ atoms × 10³ frames that is about 7.2 GB peak to write a 1.2 GB float32 payload. At the reference ensemble size (about 55k atoms with hydrogens, 50 frames) it is only about 200 MB, so this matters only for long trajectories.

**Suggested fix (prose; the reviewer's diff was not applied here):** preallocate the `(frames, atoms, 3)` array in `positions_nm` and fill it per frame with `np.multiply(..., out=...)`. Transform in place after `rmsd` and `drift` have read `positions`, frame by frame. First confirm that no caller relies on `positions` staying untransformed.

## Systemic observations

- **Coefficients evaluated outside the domain of their inputs (CR-2).** The concentrations are `definedon` the fluid, and anything built from them and evaluated elsewhere silently reads 0, which is then clamped. One guard would catch the class: a Tier-1 assertion that `relative_permittivity()` evaluated at a point of every non-fluid material either equals ε_p or is refused.
- **Accepted, validated or computed, but not recorded or not applied (CR-4, CR-10, CR-11, CR-12, CR-13).** The Tier-1 switch-enumeration test walks only bool and Literal fields, so float-valued switches rely on hand classification. A second enumeration over float fields, each classified as switch or configuration with a reason, would stop the next one.
- **The validation harness can pass vacuously (CR-5, CR-6, CR-7).** Its gates are strict about NaN, but not about emptiness, about comparing like with like, or about scale. Each norm should assert that it covers at least one point, and each pair of numbers compared in a verdict should come from one function over one mask.
- **Per-call reconstruction of fixed-mesh data (CR-3, CR-14; also the triple mesh ingest noted by unit B).** Anything derived from a fixed mesh is rebuilt at every consumer. A per-mesh cache, of the kind the CR-3 patch adds, is the general remedy.
- **Stale cost comments.** `charge/fields.py:386` ("costs a minute") is off by about 40×, and it led a reviewer to a wrong severity. Timing claims in comments should cite a measurement or be removed.

## Also noted outside the focus

- **Golden integrity check skipped when `golden_hash` is missing** (`validation/comsol.py:821-822, 959-964`; error handling, low). The legacy allowance protects nothing: no golden manifest is committed, and `ingest_golden` always writes the key. Patch: `cr-golden-hash-required.patch`, included below.
- **A NaN in a supplied grid is reported under the wrong gate and location** (`density/grid.py:206-214`; error handling, low). It is accepted at load, then reported as "the supplied grid is truncated" at an unrelated (r, z). No wrong number gets through. Fix: refuse non-finite values in `RadialGrid.from_axes`, naming the first one.
- **A supplied field's data table is not a recorded input file** when its header declares no `sha256` (`io/run.py:558-581`; low). A changed table still shows through the stage-7 artefact hash, but `reproduce` cannot name it as a moved input.
- **The Péclet diagnostic reports −1 ("below threshold") for all-NaN samples** (`solve/gates.py:705-757`; low). It is a diagnostic by design (NUM-12), and the state gates already abort on a NaN state.
- **`sweep/run.py:247-251`** runs `plan.base_case()`, `plan.case()` and the parent's `store.get` outside the member's `try`. A `StoreError` there aborts the whole local sweep rather than failing one member (error handling, low).

## Leads not settled

- **The conservation gate and the Poisson source use different quadratures for an areal charge field** (`charge/fields.py:644-663` against `physics/models.py:1015`). The gate integrates with `singular=True`, while `charge_source(fixed_charge, ...)` assembles without it. On a synthetic alternating field, unit A measured 1e-5 to 1e-3 relative difference. Whether this exceeds QR-03 on the aliased ClyA table (`.knowledge/06` §8.1.1) needs that table, which is not in the repository. Units A and D raised this independently.
- **Newton's relative-update test takes one ℓ2 norm over all fields** (`solve/newton.py:326-328`). With `a = 1 nm`, ũ ~ 1e-3, so the velocity and pressure blocks may be only about 1e-3 relatively converged when the test passes. The code matches NUM-16 as written, so this is a specification question for EOF and hydrodynamic-force accuracy.
- **UMFPACK redoes its symbolic analysis on every Newton iteration** (`solve/linear.py:155`). The saving from reusing it is unmeasured.

## Method and coverage

**Orchestrator:** the main session, on Opus (the skill recommends Fable). **Reviewers:** six in parallel, with models chosen by the repo's `.claude/model-policy.md` (plausible-wrong-number code on Opus, loud failures on Sonnet).

| Unit | Scope | Lines | Model | Why |
|---|---|---:|---|---|
| A | `physics/`, `materials/`, correction YAML | 6.4k | Opus | Weak forms and signs; a mistake is a plausible wrong number |
| B | `solve/`, `post/` | 7.6k | Opus | Newton, gates, current extraction |
| C | `io/`, `core/`, `sweep/` | 10.1k | Opus | Hashing, cache keys, provenance |
| D | `structure/`, `density/`, `symmetry/`, `geometry/`, `charge/` | 8.0k | Opus | Numerical pipelines, conservation |
| E | `mesh/`, `validation/` | 8.1k | Opus | Comparison harness can pass for the wrong reason |
| F | `cli/`, `gui/`, `__init__` | 6.0k | Sonnet | Thin shells; failures are loud |

**Verification:**
- 20 reviewer findings in: 16 became the 15 reported findings (A-1 and A-2 merged into CR-2), 2 moved to "Also noted" as outside the focus (E-5, D-3), and 2 were rejected (F-1, E-6). Five reported findings were adjusted: CR-3 (the suggested cache does not work), CR-6 (fix), CR-7 (example), CR-14 and CR-15 (severity). Every cited location was opened and read.
- **Executed:**
  - CR-2 (both paths), CR-3 (timing), CR-7 (statistics) and CR-14 (parse timing) were reproduced by running code in the repo's `.venv`.
  - CR-4 and CR-9 were checked on the patched tree.
  - F-1 was refuted by timing SIGTERM on a child busy inside netgen meshing.
  - CR-1 was reproduced by the reviewer and traced here, not re-run.
- **Patches:** 8 patch files, all generated with `git diff` from real edits in a scratch clone. Each passes `git apply --check` against untouched `abe328a`, and all eight apply together to a fresh clone, byte-identical to the tested tree. On the patched tree:
  - `ruff check`, `ruff format --check` and `mypy --strict` are clean on the 15 touched files;
  - **Tier 1: 1188 passed, 1 skipped** (`-n auto --dist loadfile`; `test_gui_widgets.py` excluded, as CI runs it separately);
  - **Tier 2: 160 passed, 1 skipped** (32 min, `-n auto --dist loadfile`). The CR-11 patch was written while this run was in progress, so it was covered by its own targeted Tier-1 run (59 passed, 1 skipped) rather than by this one.
- **Not reviewed:** `tests/` (read for context only), `docs/`, `examples/`, `packaging/`, `.github/` and `data/` other than `data/corrections/`. No part of `src/` was skipped.
- **Not executed:** Tier 3 (it needs COMSOL goldens, which are not in the repo); CR-8 and CR-15 (reviewer measurements, not re-run); the "Leads not settled" section.

Each patch is inlined in full under its finding; the golden-hash patch, outside the focus, is at the end.

## Considered and rejected

- **F-1: "`RenderProcess.terminate()` blocks the UI thread for up to ~2 s"** (`gui/widgets/viewer.py:125-130`). The synchronous join is deliberate, and documented as what stops two render children sweeping each other's files out of `viewer/`; the proposed background-thread fix reintroduces that race. The ~2 s premise is also wrong. SIGTERM's default action kills the process even inside compiled code, and neither netgen nor ngsolve installs a SIGTERM handler. Measured: a child busy in `GenerateMesh` exits in **14 ms**, with exit code −15.
- **E-6: "stage-6 workspaces under `store/tmp` are never removed, leaking a mesh per sweep member."** Every pipeline run, sweep members included, hands stages a per-run scratch directory from `io/run.py:_scratch`, which `run_document` removes at `io/run.py:832-837` whether the run succeeds or fails. The `mkdtemp` fallback fires only when a stage is invoked on its own.
- **B-2's original cost claim (about a minute per extra parse, about 17 h per 1000-member sweep).** It rested on a stale comment; the real cost is about 1.6 s (see CR-14).
- **The reviewer's CR-3 proposal of a `weakref.WeakKeyDictionary` keyed by mesh.** `ngsolve.comp.Mesh` is unhashable (`TypeError`), so a cache on the mesh object is used instead.
- **E-3's quoted failing tuple `(15.05, 88.30, 61.30, 27.99)`.** Its residual is −3.6e-15, under the tolerance; the defect stands on the statistics instead.

## Patch: golden hash required (outside focus)

```diff
diff --git a/src/nanopnp/validation/comsol.py b/src/nanopnp/validation/comsol.py
index e4a7888..30d92b6 100644
--- a/src/nanopnp/validation/comsol.py
+++ b/src/nanopnp/validation/comsol.py
@@ -819,7 +819,13 @@ def load_golden(path: str | Path) -> Golden:
             "a disagreement means one of them was replaced on its own"
         )
     digest = _golden_hash(manifest, values)
-    if recorded is not None and recorded != digest:
+    if recorded is None:
+        raise GoldenError(
+            f"{manifest_path.name} records no golden_hash. ingest_golden always writes one, so a "
+            "manifest without it was edited by hand, and an archive it vouches for cannot be "
+            "checked against it"
+        )
+    if recorded != digest:
         raise GoldenError(
             f"{archive} and {manifest_path.name} hash to {digest} and the manifest records "
             f"{recorded}. The two are written together by ingest_golden over the same bytes, so "
@@ -950,8 +956,7 @@ def _read_archive_manifest(path: Path) -> tuple[GoldenManifest, str | None]:
 
     The hash comes back rather than being discarded, because a recorded digest
     nothing ever compares against is a checksum that cannot fail;
-    :func:`load_golden` is where it is checked. ``None`` only for a manifest
-    written before the key existed.
+    :func:`load_golden` is where it is checked, and refuses ``None``.
     """
     decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
     if not isinstance(decoded, dict):
```
