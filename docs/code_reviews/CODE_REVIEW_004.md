# Adversarial review: PR #91 (WP42, head `34700ee`)

## Intent
WP42 delivers the verification checks. VER-70 makes gate comparisons NaN-safe. VER-71 classifies all 105 case leaves and refuses non-default values a model never reads. The case schema moves to `nanopnp/case/v0.5` and v1/v2 are retired. Records, fixtures and docs follow.

## Reviewers
- Reviewer A, `pro`: 3 findings (plan completeness, stale spec text, lost tests).
- Reviewer B, `flash`: 7 findings (NaN lint, `_check_unread`, taxonomy).
- Reviewer C, `inherit` (Sonnet 5.5): 8 findings (test quality). Its first run failed on a quota error and was rerun.

Claims marked **[verified]** were reproduced by the lead against the code at `34700ee`.

## Act on

### 1. The PR body's numbers do not match the code. [verified]
Recomputed from `LEAVES` and `declaration(m).unread`:

| Claim | PR body | Actual |
|---|---|---|
| `solve` / `solver` / `post` / `fixed` / `checked` | 27 / 7 / 3 / 8 / 7 | 33 / 4 / 1 / 12 / 2 |
| unread `pnp` / `pb` / `pb-linear` / `poisson` | 4 / 26 / 28 / 29 | 8 / 22 / 24 / 25 |
| `stage`, `provenance`, `epnp-ns`, `pnp-ns` | 50, 3, 0, 19 | match |

The totals (105) agree, so the classification is fine and only the stated distribution is wrong. The "Measured" section is the record a reviewer trusts, so it needs correcting.

### 2. `SPECIFICATION.md` still specifies the retired v1 upgrade. [A, verified]
`SPECIFICATION.md:1434-1445` says a `nanopnp/case/v1` document "SHALL be read as its upgrade". Appendix B3 (line 3518) and G6 (line 3598, "A document of any earlier identifier is read as its upgrade") also describe upgrade reading, while line 1884 says v1 and v2 are retired. `docs/validation/comsol-export-contract.md:155` cites a `v1` golden. The code is right and the text is stale.

### 3. `nan_permissive_gates` never reports a stale exemption for a missing file. [B, verified]
An exemption for a nonexistent file returns `stale == ()`. Keys are matched only per file found on disk. Track matched keys globally and report `set(exempt) - matched`, with a test.

### 4. Value-range and deviation tests were dropped with `test_case_schema_v2.py`. [A, C]
The constraints are still live in `src/nanopnp/io/case.py:438-460` and `:598`. `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` take `ge=0.0, allow_inf_nan=False`. `numerics.mesh.size_scale` takes `gt=0.0, allow_inf_nan=False`. The deleted negative and infinite cases were their only tests. The lead's grep found no tier1 test passing a negative or infinite value to these keys. Two tier1 assertions are also gone: `deviations()` for a non-zero `exclusion_offset_nm` and `dielectric_transition_nm` (with `validated == 0.0`), and `()` for an absent `charge:` block. Tier2 covers only the non-zero side and is not the fast gate. C also lists `test_ver47_every_new_input_is_read_by_the_stage_that_consumes_it` (`inputs.pqr` gives `resolved.pqr is not None` and `resolved.protonates`), which has no replacement. The lead's grep found no `.protonates` assertion in tier1. Add one parametrised test for `-0.1`, `inf` and `nan` on the three keys, and one deviations test.

### 5. `test_ver71_stage_leaves_move_their_consumers_key` can pass vacuously. [C, verified]
`tests/tier1/test_case_leaves.py:1018` reads `except (CaseValidationError, UnsupportedCaseSection, Exception): pass`. `AssertionError` is an `Exception`, so the mesh-key assertion can never fail. C reports the `charge` and `eps_r` loop has no assertion at all (I confirmed only the mesh block). The `live_pdb` and `refused` dicts are hand-written, so a new stage leaf is not required to be probed. The plan says "each stage leaf moves its consumer's key". Drive the test from `LEAVES` (`kind == "stage"`, `.consumer`), assert the probe lists are complete, and drop the broad `except`.

### 6. "Bit-identical before/after" for `SOLVE_HASHES` is enforced by no test. [C]
Four of five hashes in `tests/tier1/test_model_interface.py:87-93` were re-recorded. The only guard compares against the new values, and the proof lives in the commit body of `075696e`. The docstring still says "on ``main``". The same file also weakened `test_ver56_pnp_ns_beside_corrections_it_overrides_runs_and_restores` from a bit-for-bit equality to `rel=1e-12` between a ladder and a single rung, which are different solves. Add a tier1 test using `test_case_leaves.fingerprint` with `_check_unread` patched out, and fix the docstring.

## Consider

### 7. `test_ver71_the_linear_solver_reaches_every_model` accepts any exception naming the probe. [C]
`pytest.raises(Exception, match=probe_solver)` passes on an unrelated "unknown solver 'ver71-probe'" error. Have the probe record the call and assert on that.

### 8. The lint treats any `not`, and any `or` with one guard, as safe. [B]
`not (a <= t or b <= t)` is NaN-permissive for `a`. `not isfinite(x) or y > t` masks `y`. Neither pattern exists in the tree today.

### 9. `_find_if_nodes` descends into nested functions. [B]
It credits a nested function's `if` to the outer function, while `_raises_or_appends_gate` stops at nested defs (D1). No nested case exists today.

### 10. `test_ver71_applied_parts_branches` tests internals. [C]
It monkeypatches the private `materials_models._document` and asserts on `applied_parts`. It also has no VER/PHY tag and defines `T` and `replace` inline. PHY-22 behaviour is covered elsewhere.

## Noted
- `_is_gate_name` sees only bare names, so `raise errors.XError` is invisible. [A]
- `_is_nan_guard` misses `from math import isnan`. [B]
- `inputs.{mesh,charge,eps_r}.artefact` are `fixed` while `inputs.{profile,pqr}.artefact` are `stage`. [B]
- `conftest.py` has session fixtures that only return constants (`reference_triangles`, `d10_figures`, `exclusion_2wcd`) and a type-ignored `as_yaml` lambda. D13 asked for fixtures, so this follows the plan. [C]
- The edited case-text builders (`corrections_block`, `pnp_base`, `test_case_schema.py:377-455`) call `str.replace` with no assertion that the block was found. [C]
- `test_validation_identity.py` pins the structure key by its first 8 hex characters. [C]
- The D13 "rendered case text byte-identical" claim is a commit-body claim only, and the case name changed from `shell-run` to `run-probe`. [C]

## Dismissed
- `_check_unread` could crash on an absent parent block via `UnknownCasePathError`. [B] No leaf in any model's `unread` set sits under an optional block today. Revisit when one does.
- `from conftest import` under `TYPE_CHECKING` as a branch problem. [C] It exists in 16 files on main and 16 now. The branch added none.
- The lost solid-permittivity cross-check tests. [A] They tested v1-to-v2 upgrade behaviour, which was retired.
- The null `physics:` block case from `v1-null-physics`. [A] It tested the v1 upgrade. C did not check whether a v0.5 `physics: null` document is still tested.
- The "5 lines lost" in `test_nan_gates.py`. [C] They are the five `xfail(strict=True, reason="planned: WP42 D1/D2")` decorators. Every assertion remains, except that the `SYNTHETIC` literal's safe-forms oracle was not read.
- A's "critical" severity on the spec text. Downgraded: the code is right and the text is stale.

## Agreement map
A and B did not overlap. A covered plan completeness and records, and B covered the source. A and C agree on the lost coverage (item 4), and the lead's grep supports the value-range part. Item 5 was raised by C alone, and I confirmed the `except Exception` line. A, B and C found no defect in the 38 rewritten comparisons, the removal of `carry_upgrade` and `upgraded_from`, the D8 gating, the D11 and D12 pins, or the `conftest.py` fixture state. C did not read the `SYNTHETIC` literal in `test_nan_gates.py`, and A and B did not review it.

## Not changed
No code was edited. This is a review, per the interrogate contract.
