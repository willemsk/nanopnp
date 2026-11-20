# Code review 063: WP5.20, the meso suite

2026-11-19 · PR #192, branch `claude/beautiful-hawking-sqa62e`, head `7917a64` on base `016bd9c` · scope: the PR's 51
files, the source and tests read in full through six angles (line by line with each touched function, removed
behaviour, callers and callees, Python and JavaScript pitfalls, wrappers, the conventions of `CLAUDE.md` and
`.claude/rules/python.md`) and a sweep for gaps: `plot/data.py` (`ResidueCopies`, `ResidueCharges`, `ResidueAtoms`,
`DensityAtoms`, `inside_outline`, `colour_scale`, `ChargeVolumes`, `charge_volumes`), `api/project.py`
(`charge_case`, `kept_artefacts`, `_built_stages`), `gui/charge.py`, `gui/geometry.py` (`_DIVERGING_DARK`,
`ProfileEditor`), `gui/web/meso.py`, `meso_tools.py`, `pages.py`, `plane.py`, `molview.py`, `frame.py`, `builds.py`,
`screens.py`, `tools.py`, `states.py`, `study.py`, `study_tools.py`, `continuum_tools.py`, `assets/plane.js`,
`assets/bridge.js`, `validation/apbs.py:dx_text`, and `tests/tier1/test_meso.py`, `test_meso_charge.py`,
`test_project.py` and `test_gui_screens.py` · level: xhigh, with `--fix` · status: completed.

Static review: no benchmark, sweep, `gate.sh` or `pytest --nightly` ran during it. `ruff`, `mypy src/` and the three
test files the fixes touch (13 tests) ran after the fixes; `/np-ship` gates them.

The `physics-reviewer`'s read of the same diff, before this review, is recorded in the PR's Verification and fixed in
`7917a64`.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `gui/web/meso_tools.py:383`; `plane.py:_edited` | A loop traced by *Seed from the map* cannot be saved as it is: item 12 gated *Save edit…*, the state line and the canvas's keying on `can_undo`, which a seed lacks until a vertex moves; with stage 4's outline built, the seed is also titled as it | Fixed: `ProfileEditor.changed`, true for a seed or after an edit, at the three places |
| 2 | Important | `gui/web/meso_tools.py:toggle_overlay` | The overlay's peaks and levels are computed once per pane: after the charge is rebuilt, the new volume is drawn at the old level, and can vanish | Fixed: `held_overlay` clears the overlay, peaks and levels when the charge's hash changes |
| 3 | Important | `gui/web/meso.py:volume_text` | `volume_text` read the stored stages again after the seconds-long first compute: a build ending meanwhile filed the old volume's text under the new hashes, or raised | Fixed: `_volumes` reads the stages once and keys the table, the volumes and their text from that read |
| 4 | Nit | `gui/web/molview.py:overlaid` | With *One subunit* the scene has no cut, so the overlay draws the whole ring's charge about the one chain shown | Skipped, a design question: REV-266, for WP5.26's round |
| 5 | Nit | `gui/web/meso_tools.py:group` | Under `geometry.density.atoms: as_loaded`, a walk to stage 3 builds no protonation table: Density's nearest residues are listed without names, and a pick marks nothing, until the charge is built | Skipped: naming them from `DensityAtoms` is wider than the diff; REV-266 |
| 6 | Nit | `gui/web/meso_tools.py:632` | The strip's sign, `{charge_e:+.0f}`, writes a listed residue of 0.5 e as "+0" | Fixed: a tenth kept where the charge is not near a whole one |
| 7 | Nit | `gui/web/states.py:_charge_map` | A study whose continuum model draws its own pore booted with a failed "to charge" entry in the queue | Fixed: the charge case is formed before the entry, and a refused one walks nothing |
| 8 | Nit | `gui/web/tools.py:_MINUS` | A refusal card turned a path's hyphen into a minus, `inputs/-1.pdb` reading `inputs/−1.pdb` | Fixed: a hyphen after a slash, a backslash or a hyphen is kept |
| 9 | Nit | `plot/data.py:ResidueCopies` | "(FR-03)" in a docstring, against `.claude/rules/python.md`: requirement identifiers live in test names and commit messages | Fixed: dropped |
| 10 | Nit | `tests/tier1/test_project.py`, `test_meso.py` | Imports inside test functions, against `.claude/rules/python.md`'s imports at the top of the module | Fixed: moved to the top |

Ten findings, eight fixed, two skipped into REV-266. None changes an author's ruling. Finding 1 narrows item 12's
answer to the round's F8 to the edits it meant: an edit of a stored outline still waits for a change before it is
saved.
