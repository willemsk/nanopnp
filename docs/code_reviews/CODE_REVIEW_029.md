# Code review 029: WP5.04, the charge mutator's library step

Reviewed head `234b2c8128a35c6b8b722164ffb7b612e1f5621f` against base `2923c4694ff7bc5f38f261f366e8457c82f11c6b`
(PR 153). Status: completed. Static review at `xhigh`. Fourteen findings; twelve fixed, two recorded.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `pipeline/run.py` | `PROTONATION_RECORD_KEYS` filters the protonation summary into the manifest and did not list `variant_of`, so `charge.protonation.variant_of` never reached a manifest (§5.3.3, §5.3.1 NOTE on `charge.edits`). | Fixed: the key is listed; a run without edits carries no `variant_of`, so its manifest does not move. |
| 2 | `charge/protonation.py` | The summary's `q_net_e` and `q_net_residual_e` came from `_assemble`, before `apply_edits`, so a `charge_change_e` variant recorded its parent's `Q_net` in the summary and in the manifest's `charge.protonation`. | Fixed: both are recomputed from the edited table. |
| 3 | `pipeline/checks.py` | The one-edit-per-kind and state-beside-charge refusals compared the raw `residue` string, so `ASP 21` and `ASP 021` passed as two residues: two radius scales multiplied, and two opposed pins ran a full protonation before failing as "the pin takes no effect in this PDB2PQR". | Fixed: compared on `ChargeEdit.residue_parts`; §5.3.1's NOTE says so. |
| 4 | `geometry/contour.py` | Stage 4's probe-radius profile reads the aligned ensemble's unscaled radii, so a `radius_scale` variant's contour is gated against the parent's atoms and can be refused. | Recorded, REV-184. |
| 5 | `density/stage.py` | Under `protonated` stage 2 keys on the whole protonation hash, so a charge-only edit re-deposits and remeshes to the same map. | Recorded, REV-185. |
| 6 | `charge/protonation.py` | A state edit naming a residue a chain lacks, or holds under another parent, ran the pinned protonation (about a minute per frame) before `apply_edits` refused it. | Fixed: `charge/edits.py:check_targets` refuses it on the parent's frames first. |
| 7 | `pipeline/checks.py` | A `residue` named by a protonation-variant name (`HSD 292`, `ASH 21`) passed the case and was refused only after the protonation, as "the residue is HIS, not HSD". | Fixed: refused at the case naming the parent, through `charge/edits.py:variant_parent`, so `pipeline` gains no edge to `structure` (VER-61); §5.3.1's NOTE says so. |
| 8 | `io/case.py` | `ChargeEdit`'s refusal of an entry with no edit read "sets none of of state, …". | Fixed. |
| 9 | `structure/protonated.py` | `radius_scales` rebuilt every atom's parent name once per radius edit. | Fixed: built once, and not at all without a radius edit. |
| 10 | `charge/protonation.py` | `_NEUTRAL_HYDROGEN` restated the protons of `density/radii.py`'s acid patches. | Fixed: the pin gate reads `ACID_PATCHES`, now public. `STATE_RESIDUES` in `pipeline/checks.py` stays, as the checks do not import the stage. |
| 11 | `charge/protonation.py` | The summary carried `edits` twice, at its top and in `variant_of`. | Fixed: `variant_of` holds them. |
| 12 | `pipeline/checks.py` | `TitratableGroups` was imported inside `_check_edits`; `.claude/rules/python.md` defers only costly or optional packages. | Fixed: imported at the top; no cycle. |
| 13 | `charge/edits.py`, `structure/protonated.py` | Two new docstrings carried `FR-38` (CLAUDE.md, *Prose in code*), and the module docstring named the groups alone. | Fixed. |
| 14 | `charge/edits.py` | `POSITION_TOLERANCE_NM`'s docstring gave the table's rounding as 1e-4 Å; it is 0.001 Å, 1e-4 nm. | Fixed. |

Not findings: `radius[atoms][mine] *= …` writes through, as `frame_slice` returns a slice and the first index is a
view; the frame key's `pins` and the artefact key's `edits` overlap by design (D6); `expected_charge_e` and
`unapplied` keep PROPKA's expectation after a charge edit, which the specification does not ask to move; the
monkeypatch of `apply_pka_values` is per process, and no thread of the package runs a protonation beside another
(the charge tab's pool only loads views).

Checked on the fixes: `ruff check`, `ruff format --check`, `mypy src/`, and Tier 1 without
`tests/tier1/test_gui_widgets.py` (1479 passed, 8 skipped).

Not assessed: the pins against a live PDB2PQR other than 3.8.0; the VER-62 walks, which `/np-ship` gates (the fixes
move no unedited key or summary value they compare).

## Decided in the `/np-ship` session: the physics review

The `physics-reviewer` pass over the same head (`234b2c8`) found five problems. The review above also found and fixed three of them: `variant_of` missing from the manifest, the stale `Q_net`, and the zero-padded residue numbers. The session fixed the other two:

- **The HIS and ARG groups held PROPKA's interaction atoms, not its charge centres.** AG9 puts the change on the charge-centre atoms. PROPKA 3.5.1's `group.py` centres HIS on its five ring atoms and ARG on CZ. `data/charge/titratable_groups.yaml` now lists those atoms. `test_fr38_the_titratable_groups_are_propkas` now reads each group class's `set_center` call. Before, it checked only the anchors, which is why it let the error through.
- **A charge edit left `unapplied` and `expected_charge_e` as they were before the edit.** A pin already clears its residue's expectation, because the case set the state. `apply_edits` now does the same for a charge edit and recomputes `unapplied`, and the summary's `unapplied` is rebuilt from the edited table.

Not taken up:

- **No `Q_net` integer gate after an edit (low).** The result is an integer by construction, and the error is about 1e-16.
- **Memory of `difference()` (low, not measured).**
- **The radius scale below about 0.89 and the spacing gate (info).** This is REV-182, already open.
