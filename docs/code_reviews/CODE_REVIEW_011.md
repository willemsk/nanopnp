# Code review: PR 111, the CODE_REVIEW_010 resolutions

19 October 2026 · `28551bd..7988eae` (`claude/beautiful-hamilton-hk738l`) · scope: the pull request's diff ·
focus: correctness, convention

## Summary

The review found no high-severity defect. It found one orientation gap, one sibling of a fixed bug, three
untested fixes and a set of specification and convention gaps. A second reader (the physics reviewer)
checked the force-traction normal, the log-branch export, the permittivity gate and the PHY-13 count.
`/wp-ship` adjudicated every finding below; one fix of the review pass was reverted.

| Severity | Count |
|---|---:|
| High | 0 |
| Medium | 2 |
| Low | 11 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `mesh/adapter.py` `oriented_edges` | The seam orientation ranked materials by table index, but `canonical()` sorts the table by name, so two meshes of one content hash could build different NGSolve meshes and flip the normal on a seam. | Fixed: materials ranked by name; `test_a_seam_normal_does_not_flip_with_the_order_of_the_material_table`. |
| 2 | `validation/compare.py` `sample_on_probe`; `gui/render.py` | The log branch (NUM-02) was sampled and drawn as ln c scaled as c, the bug `export_fields` had. Latent: no case path sets `log_variables`. | Fixed: `post.export.logarithmic_fields` is used by the export, the probe sampling and the GUI scene. |
| 3 | `materials/electrolyte.py` (CR-6) | The review pass proposed counting the driver clamp on the unclipped mean. | **Reverted.** The fits evaluate the clipped driver, so the unclipped count logs a clamp that never happens (7 M and 4 M: 5.5 M against 4.65 M) and inflates the manifest's `clamp_activations`. A test now pins the clipped count. CODE_REVIEW_010 CR-6 is recorded as declined. |
| 4 | `pipeline/checks.py` | The "did you mean" hint for a solid-permittivity key could name a fluid domain the next check refuses. | Fixed: the hint draws from the solid vocabulary only. |
| 5 | `SPECIFICATION.md`, `knowledge/` | VER-06 and three normative notes still told the reader to mollify the wall distance or scale the blocks field-wise. | Fixed: VER-06 reworded, "superseded" pointers added, one `knowledge/log.md` line. |
| 6 | `SPECIFICATION.md` | The new `solid_permittivities` and `numerics.nonlinear` gates were not in the specification. | Fixed: the `solid_permittivities` NOTE and NUM-16 state them. |
| 7 | `charge/dielectric.py`, `solve/state.py`, `io/manifest.py` | Docstrings on private code and an identifier in a comment. | Fixed (`.claude/rules/python.md`). |
| 8 | `tests/tier1/test_solid_permittivity_keys.py` | Tests named `test_ver03_*`; the requirement is PHY-03. | Fixed: renamed `test_phy03_*`. |
| 9 | `docs/project/review-findings.md` | CR-8 (declined) had no `REV-nn` row. | Fixed: REV-119. |
| 10 | `validation/attribution.py`, `cli`, `tests/tier3` | `zero_reference` was filled by each caller, and the Tier 3 harness did not fill it. | Fixed: `zero_reference_quantities` returns the name-to-value mapping; the harness passes it. |
| 11 | `mesh/ingest.py`, `pipeline/checks.py` | The fluid-key refusal text was written twice. | Fixed: one `fluid_permittivity_refusal`. |
| 12 | `tests/tier1/test_case_schema_v05.py` | The CR-4 bounds (`rtol`, `max_iter`) were untested. | Fixed: four values added to the value-range refusal test. |
| 13 | `knowledge/06-numerics-fem/09-…` | `specialcf.normal` follows the order an `Element1D` was added in; not recorded. | Not done: the entry needs a `[tested:]` marker and a header edit; left to the author. |

## Found by the physics reviewer, outside the diff

- **Normal consistency (REV-120, open).** "Lowest material by name on the left" is consistent along a
  force surface only if the neighbouring pair of materials is the same all along it. The built-in analyte
  geometry refuses a body that crosses a pore mouth, and `analyte` sorts before every fluid domain, so
  the built-in path is safe. A supplied mesh with a body of another name touching two fluid domains is
  not stopped. Not widened into this package; put to the author.
- **Low, not acted on.** `io/case.py` accepts any permittivity above 0, including values below 1;
  `models.create(...)` called directly bypasses the fluid-key check (case resolution runs it first).

## Verified and found clean

- `_run_key` reads the structure `input_group` writes; no other code derives a run directory from the case hash.
- `Manifest.write` keeps the source bytes; `reproduce` reads the same bytes.
- The CCW half-edge logic of `oriented_edges` is correct, and `int64` indices rule out key overflow.
- No reference to the removed NUM-10 helpers remains in `src/` or `tests/`.
- The log-branch export test would fail without the change, and its expected value is dimensionally consistent.
