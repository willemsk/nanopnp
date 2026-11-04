# Code review 031: WP5.06, outputs and steric models as registries

Reviewed head `3b0abadf206420ceb06727c692fcf91b874be20a` against base `ea5cdc6c40c9938a2286f60f3d8016529fa5448e`
(PR 157). Status: completed. Static review at `xhigh` with `--max-findings all`, and a `physics-reviewer` read of the
physics and numerics files. Thirteen findings; eight fixed, four recorded, one needing no change.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `post/stage.py` | The no-transport branch of `QoIStage.run` built its `QoIArtefact` without `output_parameters`, while `key()` passed them, so the two hashes differ for an output registered with no need and a `parameters` callable. | Fixed: `run` passes them. |
| 2 | `post/stage.py` | An output with `needs=∅` and an `extract` is offered for a model with no transport, then skipped by the early return, with no refusal. | Recorded, REV-193. |
| 3 | `post/indicator.py`, `post/forces.py` | `require_boundary` tests the region mask. A named boundary that carries no segment passed it, and the length that follows is 0, so `check_indicator`, `check_extension` and `_boundary_region` raised `ZeroDivisionError` (or returned NaN) where they raised their own error class before. | Fixed: each site refuses a zero length with its own class. |
| 4 | `physics/nernst_planck.py`, `physics/stabilisation.py` | The default of `species_flux(steric=)` and `TransportState.steric` went from on to off. A caller that omits it silently got the classical flux; two Tier 1 tests had stopped exercising the steric term. | Fixed: `steric` is required; the two tests pass `steric_form("borukhov")`, the behaviour they had. |
| 5 | `io/artefact.py`, `post/stage.py` | A registered output's key parameters were merged after the core keys, and its summary over `routes_checked` and `route_agreement`, so a colliding name replaced them silently. | Fixed: a collision raises `ValueError`. |
| 6 | `post/outputs.py` | `register_output` accepted a need no model declares, so the output was never offered. | Fixed: refused, naming the needs. |
| 7 | `materials/electrolyte.py`, `post/stage.py` | Only the name of a registered steric form (and an output's name and parameters) enters the key. A changed body under the same name returns a cached artefact. | Recorded, REV-194: §5.5's NOTE asks for the name; a digest is an amendment. |
| 8 | `tests/tier1/test_nernst_planck.py` | The test named for Borukhov's sign checks linearity only (`doubled - borukhov == borukhov - none`), which holds for either sign. | Fixed: renamed `..._is_added_once_to_the_bracket`; the sign stays with `test_phy05_steric_flux_drives_ions_out_of_crowded_regions`. |
| 9 | `validation/mms.py` | The manufactured source builds the Borukhov flux for any steric model. | Recorded, REV-195. |
| 10 | `materials/electrolyte.py` | `CorrectionSwitches.steric` is a `str` with no check at run time; a legacy `steric=False` reads as on. | Fixed: `__post_init__` refuses a non-string. |
| 11 | `io/case.py` | `Steric.model` and `outputs` are strings, so the case JSON Schema lists no valid values. | Recorded, REV-196. |
| 12 | `post/indicator.py` | The comment "Matched by measure" no longer describes `has_boundary`. | Fixed. |
| 13 | `physics/nernst_planck.py` | No sign comment on the steric line of the bracket. | No change: none was removed, the `steric_flux` docstring carries the warning, and a comment says why only where the code cannot. |

Confirmed unchanged by the physics read: the Borukhov flux and its sign in `species_flux` and in the stabilisation
velocity; the call sites that pass the form; the solve key and provenance for `none` and `borukhov`; the manifest
deviation for any other name; the summary keys of each shipped output; the stage-11 key parameters.

Checked on the fixes: `ruff check`, `ruff format`, `mypy src/`, and the Tier 1 files the fixes touch. `gate.sh run`
follows in `/np-ship`.
