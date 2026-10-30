# Code review 021 — WP57, an idealised pore as geometry and the Python interface on a Case and a Session

Reviewed from `/np-ship wp 57` on 30 October 2026. Pull request
[#139](https://github.com/willemsk/nanopnp/pull/139).

- Reviewed revision: head `16efc65ed65b054c8e636209d30f34b46afe281f`, base
  `ba7a8a546cd99f75a4b640c1be7e33ce30dd66a1`.
- Passes: `/code-review xhigh --fix 139` (static, whole diff) and the `physics-reviewer` agent on
  the physics and numerics paths of the same diff.
- Findings: 14 from the static pass, 6 from the physics pass. Seven of the static findings were
  fixed by the pass and confirmed here; three more were fixed in this session; two of the physics
  findings were fixed here. Eight items are left open as `REV-158` to `REV-165`.

Tier 1 was green at every step (1456 passed, 1 skipped). No tolerance was slackened and no test
weakened; the two tests deleted before the review were deleted for being outside the test scope
(§8.2.13 N1), recorded in the pull request's **Verification**.

## Test scope, read before the review (§8.2.13 N1, N5)

Two added tests were outside the scope and were deleted in `16efc65`:

- `tests/tier1/test_session.py`, the figure accessors' refusal on a run short of the solve — figure
  wiring, not a numerical or physical gate, and the accessors keep their cover in
  `tests/tier1/test_figures.py`.
- `tests/tier1/test_cli.py`, the reference preset's refusal of a size flag — command-line wiring and
  message wording.

Everything else the package adds is physics, numerics, a core mechanism (content hashing and cache
keys, case resolution, the stage walk, warm start, the manifest's deviations), an architecture guard
or an entry point's smoke test. `tests/tier1/test_stages.py`'s function-stage test and
`tests/tier1/test_case_leaves.py`'s wall-charge rows key artefacts and are in scope on that ground.

## Fixed by the review pass, confirmed here

Each was read as a diff against the specification and the plan before it was kept.

| What | Where | Confirmed against |
|---|---|---|
| `sweep_isolevels` loaded each isolevel copy with the scratch directory as its base, so a relative input path of the case was read beside a directory holding no input | `validation/geometry.py` | §5.3.1's relative-path NOTE (§8.2.23 D12); the fix anchors the copies to the original case |
| `reopen` resolved with no base although the same commit added `recorded_base` and `open_run` uses it | `validation/runs.py` | The same NOTE; `open_run` is the oracle |
| `register_stage` implemented two of the four refusals §5.5's NOTE lists; a name outside `[a-z][a-z0-9_-]*` and a keyword-only or variadic parameter were accepted | `api/session.py` | §5.5's stage-of-one's-own NOTE names all four refusals verbatim, so the fix is what the specification already required |
| `recorded_base`'s lookup was written twice, once in `pipeline/run.py` and once as `_recorded_directory` | `pipeline/run.py`, `api/reproduce.py` | QR-13's one-place rule; `recorded_base` now takes the Inputs group and the reproduction delegates |
| `stage --list` built its JSON from `registered_stages()` and its text from `Session().stages`, two sources for one listing, and constructed a default `Store` to format text | `cli/__init__.py` | The command's own contract, answered from the registry alone |
| `Session.stages` documented "in pipeline order" where `registered_stages()` orders by stage number, which puts `case` tenth | `api/session.py` | `walk_order()` against `registered_stages()`; the docstring now says what the code does |
| `register_stage` deferred an import of `nanopnp.core.stages`, from which the module already imports at the top | `api/session.py` | `.claude/rules/python.md`, *Imports at the top of the module*; VER-72 (a) |
| `check_force_surface` walked every triangle in Python, three edges each, and unpacked a one-element tuple when a surface edge belonged to no element, raising `ValueError` where the docstring promises `ForceSurfaceError` | `post/forces.py` | NUM-29's NOTE; the gate's behaviour on a well-formed mesh is unchanged, verified by `tests/tier1/test_forces.py` and the real analyte mesh |

## Fixed in this session

- **The `poisson` model's surface-charge term carried no `r`-weight quadrature order** while the same
  method's stiffness and volumetric source both carry `RADIAL_WEIGHT_ORDER`
  (`physics/models.py:1512`). NGSolve estimates an integrand's order from its proxies and does not
  see the `r` weight, which is the stated reason the model adds that order (NUM-07's NOTE). The term
  is of degree 3 in `r` at P2 for the same reason as the source. Fixed, and NUM-07's NOTE and
  `docs/project/physics-models.md` now name the surface term beside the other two, in the same
  commit. The segment rule at the default order is exact to degree 3, so no number moves at P2 —
  confirmed by `tests/tier2/test_wall_surface_charge.py`, whose Gauss balance still holds at
  `rel=1e-3` — and the model is consistent at a higher element order.
- **A surface charge applied to a boundary that matches nothing was not refused** on the coupled and
  `poisson` models (`physics/models.py:895`, `:1516`), where `physics/pb.py` already refused it and
  said why: the term vanishes and the solve converges on the uncharged answer, which is the
  plausible-wrong-answer mode QR-12 and NUM-06 forbid. Unreachable from a case file — `checks.py`
  and stage 6's vocabulary guarantee `wall` — but these models are public and
  `surface_charge_boundary` is a free string. The guard is now one function,
  `physics/poisson.surface_charge_region`, used by all four sites, so `pb.py`'s copy is gone.
- **`untagged_commands` did not recognise a `uv run` prefix**, so an untested command written the way
  every example README tells the reader to write it escaped the VER-46 completeness check
  (`validation/examples.py`). The prefix is now dropped before the program is read. No README
  carried such a command, so the widened gate is green on the tree as it stands; the helper's unit
  test covers the new form.
- **A test helper named `charge_per_length_C_m` returned C m⁻³ · nm², not C m⁻¹**, with the
  conversion supplied 14 lines later (`tests/tier2/test_wall_surface_charge.py`). The helper now
  returns what its name says and the outer factor is `1e-9`; the assertion is unchanged and still
  passes.
- **An architecture decision record still described the stage interface through `run_case`**, which
  this package removes (`specification/05-software-design/06-architecture-decisions.md`). The
  historical assessment now names the walk.

## Left open

| Item | What |
|---|---|
| REV-158 | A correction file named by path puts its absolute path in the stage-8 and stage-10 keys |
| REV-159 | Three in-memory routes read a relative path against the working directory, not beside the case |
| REV-160 | `StageInputs.options` is unreachable, so three QoI settings and their deviation are dead |
| REV-161 | The manifest records a null hash for a correction file it cannot find |
| REV-162 | The wall surface charge's sign is written at four sites; Grahame's σ and the σ scale twice each |
| REV-163 | `check_force_surface` refuses a legitimate body straddling the lumen and reservoir seam |
| REV-164 | `default_ladder` accepts a ζ-Dirichlet wall and a σ_s wall together with no diagnostic |
| REV-165 | The Gauss-balance test's own quadrature error is not bounded against the physics bound it resolves |

Each has its row in [review-findings.md](../project/review-findings.md) and its section in
[review-items.md](../project/review-items.md). REV-158, REV-159 and REV-160 need a ruling from the
author and are `open`; the rest carry a recommendation.

## What the review could not assess

- The physics pass had no shell, so every statement it makes about what a quadrature rule integrates
  exactly is a deduction from `knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md`, not a
  measurement. The one consequence that mattered — that the added order moves no number at P2 — was
  measured here by running the Tier 2 surface-charge tests before and after.
- Whether netgen emits one segment per interior named edge, so the `wall` surface term is assembled
  once and not twice. The Gauss balance would fail by a factor of two if it were double-counted,
  which is indirect evidence only.
- The nightly walks, the notebooks and the sessions. They were run by hand for the implementation and
  are recorded in the pull request's **Measured**; this review ran no walk.
