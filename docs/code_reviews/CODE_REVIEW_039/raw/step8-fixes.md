# Step 8: the safe fixes, as verified and worded by the orchestrating session

Each line is one edit, verified against the tree at a5039af (the files are unchanged at b602e60). Apply, one `docs:` commit per category (the finding ids in the body), `chore:` for the scripts. Records are not touched. Paths are repository-relative; `07/` is `knowledge/07-software-stack/`.

## scripts (chore) — ORC-01

- `.claude/scripts/clause.py:27` `RULING_ROW = re.compile(r"^\|\s*([A-Z]+\d+)\s*\|")` → `re.compile(r"^\|\s*([A-Z]+\d+)\b[^|]*\|")`; `:28` `SUPERSEDED_ROW` likewise tolerates `[^|]*` before the closing bar; `_first_cell` (`:42-44`) returns the first whitespace-separated token of the cell after stripping `*`. Re-run `raw/clause-check.log`'s loop: the ten letters must resolve, and P2 prints two definitions.
- `.claude/scripts/duplicates.py:24` the same `RULING_ROW`.
- No test covers either script (`grep -rl clause tests/` is empty), so no test changes.

## stale-paths — ORC-02, ORC-03, SPB-46 (+KPH-17, KST-20 row), KGE-13, KST-17, CLD-21

- `specification/11-companion-knowledge-base.md:9` "as `nanopnp-kb/`" → "as `knowledge/`".
- `specification/11-companion-knowledge-base.md:17` row → "| `knowledge/log.md` | The dated log of the notes |".
- `knowledge/01-physics-epnpns/09-source-files.md:18` "Cloned locally at `thesis/` from `github.com/willemsk/phdthesis-text` (CC-BY-4.0):" → "The thesis source, `github.com/willemsk/phdthesis-text` (CC-BY-4.0), is not in this repository; clone it beside the checkout to read it:" (check the sentence that follows still reads).
- `07/07-local-assets.md:21` the `thesis/` row: say the clone is outside the tree (same wording).
- `knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md:26,29` "`tests/conftest.py` (`write_charged_tube`)" → "`src/nanopnp/validation/charged_tube.py` (`write_charged_tube`)"; ":29" `CHARGED_TUBE_ATOMS` likewise (`charged_tube.py:53,72`).
- `07/05-gui-and-packaging.md:69` "handled at `tests/tier1/test_mesh_quality.py`" → "handled by `import_gmsh` in `tests/conftest.py`" (`tests/conftest.py:94`).
- `.claude/hooks/session-start.sh:13` "(.claude/workflow/hosts.md)" → "(.claude/workflow/hosts/copilot.md)" (`copilot.md:21` holds the `additionalContext` form).

## stale-names — ORC-15, SPA-03, SPD-10, SPC-06, SPB-33, KPH-18, KPH-42, KNU-18, KST-02, KST-03, KST-04

- `docs/project/physics-models.md:28` delete the `quantities` row.
- `specification/03-requirements.md:185-186` FR-18: `ePNP-NS`, `PNP-NS`, `PNP`, `Poisson` → `epnp-ns`, `pnp-ns`, `pnp`, `poisson` (both mentions of `PNP-NS`/`ePNP-NS` in the row); FR-19: `PB`, `PB-linear` → `pb`, `pb-linear`. Registered names: `src/nanopnp/physics/models.py:1870-1924`.
- `specification/07-verification/02-tier-1.md:41` VER-47 title "Case schema v0.5 and the supported interpreter range" → "Case schema v0.6 and …".
- `nanopnp/profile/v1` → `nanopnp/profile/v0.5`; `nanopnp/field/v1` → `nanopnp/field/v0.5`; `nanopnp/sweep/v1` → `nanopnp/sweep/v0.5` in `specification/05-software-design/02-pipeline-stages.md:14`, `03-1-case-file.md:33,204,548,554,562`, `03-4-sweeps.md:11,61`, `specification/03-requirements.md:104`, `specification/07-verification/02-tier-1.md:54` (VER-60). Code: `io/artefact.py:32,54`, `charge/fields.py:32`.
- `specification/04-physics.md:524` "case schema v2 has no key" → "the case schema (`nanopnp/case/v0.6`) has no key".
- `knowledge/02-electrokinetics-background/00-overview.md:21-22` "(ch. 4)" → "(ch. 3)", "(ch. 2" → "(ch. 1"; `knowledge/03-nanopore-biology/00-overview.md:20-21` the same two; `knowledge/01-physics-epnpns/09-source-files.md:26` "background electrostatics/electrokinetics" → "the APBS electrostatics results (ch. 3)". Verified: `thesis.tex:292-305` includes nanopores, aims, electrostatics, trapping, epnpns, transport, conclusion in that order.
- `knowledge/03-nanopore-biology/07-why-accurate-modelling-matters-for-pore.md:24` "(one D10R mutation)" → "(D10R/K159E)". Verified: `electrostatics.tex:291,963`.
- `knowledge/06-numerics-fem/04-stabilisation.md:122` `stabilisation_current_A` → `stabilisation_currents_A` (`src/nanopnp/post/qoi.py:370`).
- `07/03-charge-and-electrostatics.md:46` `pdb2pqr: 3.7.1` → `3.8.0` (tested_with); `:57` "| **PDB2PQR** | 3.7.1 (Dec 2024) |" → "3.8.0"; `07/08-python-version-floor-the-310-target-is.md:21` tested_with `pdb2pqr: 3.7.1` → `3.8.0`. `uv.lock:2744-2745`. Leave `:70-71`, `:82` and `07/08:36` (dated statements about 3.7.1).
- `07/05-gui-and-packaging.md:52` "**PySide6** 6.11.1" → "6.11.2" (`uv.lock:3245-3246`).
- `07/05-gui-and-packaging.md:396,421` `nanopnp/case/v1` → `nanopnp/case/v0.6`; `07/15-an-npz-is-reproducible-bytes-only-if.md:42-43` after "`nanopnp/charge-grid/v2`" add " (now `nanopnp/fields/v0.5` and `nanopnp/charge-grid/v0.5`, §8.2.7 G6)".

## stale-counts — SPA-01, SPD-03, SPD-04, SPB-45, KNU-05, KNU-25, KST-19, DOC-04, CLD-17

- `specification/index.md:27` "§8.2.1 to §8.2.29" → "§8.2.1 to §8.2.35".
- `specification/08-implementation-plan/index.md:6` "§8.2.1 to §8.2.33" → "§8.2.1 to §8.2.35".
- `specification/a-traceability-matrix.md:99` "57 of the 67 requirements in §3 have a specified activity; 10 are recorded" → "66 of the 83 requirements in §3 have a specified activity; 17 are recorded" (83 `**ID**` rows in §3; 17 "None yet" rows in the matrix).
- `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md:28` "All four were found" → "All five were found" (E1 to E5).
- `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md:169` "Nineteen ways" → "Twenty numbered ways, and one more below them," (20 `**n.**` paragraphs in 167-368 and the unnumbered trap at 349).
- `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md:168` "five hundred times" → "four hundred times" (0.40 / 1e-3).
- `07/13-documentation-tooling-mkdocs-material.md:45` "the twenty public names of `nanopnp.__all__`" → "the twenty names of `nanopnp.PUBLIC`" (`PUBLIC` has 20; `__all__` adds `__version__`).
- `docs/model/index.md:15-16` "§4.6 record five errata in the original sources" → "§4.6 record the errata in the original sources (six rows in §4.6, grouped as five in the knowledge file)".
- `README.md:44` "nineteen stable names" → "twenty stable names".

## citations — ORC-08, SPC-09, SPC-10, SPB-32, CLD-05, CLD-08, CLD-10

- `specification/05-software-design/03-2-artefacts.md:79` "(§8.2.9 G6)" → "(§8.2.7 G6)".
- `specification/05-software-design/03-1-case-file.md:109` delete "(§5.4.1)" (§5.4.1 says nothing of schemas).
- `specification/05-software-design/03-1-case-file.md:149` "the NOTE on the v2 keys that change a number" → "the NOTE on the added keys that change a number" (its title at :113).
- `specification/04-physics.md:553` "(PHY-13; VER-71)" → "(PHY-01; VER-71)" (PHY-01 defines `⟨c⟩` and the ionic-strength option; PHY-13 is the 5.3 M cap).
- `.claude/skills/np-plan/phase.md:133-134` and `.claude/skills/np-plan/wp.md:105`: replace the "§8.2.13 N3" citation for the word caps and the six-decision guideline with "§8.2.11 L7" (phase plan's 1,500 words) and "§8.2.15 Q1; §8.2.16 R11; §8.2.33 AI15" (WP caps and the guideline). Read the two sentences whole before editing.
- `.claude/skills/np-gui/grill.md:50` "the personas P1 to P3, S2 and S6" → "the personas P1 to P3 (§2.4) and the rulings §8.2.17 S2 and S6".
- `.claude/agents/gui-reviewer.md:23-24` "- VER-60 and RSK-15: a number shown that no artefact supplies, or a control for a capability Tiers 1 and 2 do not verify that lacks its \"later phase\" banner;" → "- RSK-15 and the design document's rules (`docs/design/workbench.md`: a number no artefact supplies is not shown; the later-phase banner of §8.2.17 S7): a number shown that no artefact supplies, or a control for a capability Tiers 1 and 2 do not verify that lacks its \"later phase\" banner;".

## pointers — ORC-12, SPC-25, SPB-41, CLD-25

- `SPECIFICATION.md:27` after "each labelled with its file and lines" add "; `--no-history` prints the clause and its NOTEs alone".
- `specification/05-software-design/03-4-sweeps.md:55` "the workspace-locality NOTE above" → "the workspace-locality NOTE of §5.3.2"; `:62` "the canonical serialisation above" → "the canonical serialisation of §5.3.2".
- `specification/04-physics.md:397,524` "(author ruling 13)" → "(author ruling 13, `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`)" (once per line).
- `.claude/skills/np-ship/wp.md:134` "(§7.4)" → "(step 4 of *7. After the merge*, below)"; `:138` "(§7)" → "(*7. After the merge*, below)".

## present-tense — ORC-04, ORC-09, SPD-16, KST-08, KST-11, CLD-19, CLD-20

- `docs/project/review-items.md:7` "[the findings log](review-findings.md), which VER-63 checks; this page says what each one is." → "[the findings log](review-findings.md), read at review (§8.2.13 N3); this page says what each one is."
- `07/08-python-version-floor-the-310-target-is.md:85` "pass under `--extended`:" → "passed under `--extended` (now `--nightly`):".
- `specification/09-risks.md:23` "the gated `bundle` job re-detects it on every push" → "the gated `bundle` job re-detects it on every push to `main`, nightly and on a full run (`ci.yml`: not for a pull request)".
- `knowledge/08-validation-benchmarks/05-continuous-integration.md:18` "| 3 | nightly + pre-release | must pass |" → "| 3 | nightly | recorded, not gated (§7.6) |". Row 4 stays (SPD-06 is the author's).
- `knowledge/08-validation-benchmarks/00-overview.md:15` "Tiers 1–2 run on every commit" → "Tiers 1–2 run on every push"; `:17` "where marked `[verified]`" → "where marked `[tested: …]` or `[verified]`".
- `.claude/hooks/gate.sh:9-10` "then every Tier 1 test without the `nightly` marker" → "then every Tier 1 test without `slow` or `nightly`"; `:16` "with the Gmsh and APBS requirements set" → "with the Gmsh, APBS and browser requirements set".

## dead-tests — ORC-05

- `07/20-tier-1-test-evidence-import-costs.md:37` after "(`test_gate_hook_requires_gmsh_for_a_tracked_change_beside_an_untracked_file`)" add ", deleted by the test scope (WP50, §8.2.13 N1)".
- `07/17-tier-1-test-evidence-the-viewer-and-the.md:19` after "(`test_ver44_only_one_fields_scene_is_kept`)" add ", deleted by the test scope (WP50, §8.2.13 N1)".
- `07/12-the-suites-blas-threads-buy-nothing.md:67` after "`test_ver44_the_shipped_renderer_reaches_a_document_with_no_network`" add " (since deleted by the test scope, WP50)".

## front-matter — ORC-06

- Add `- by: process:<node>` with `at: '2026-11-08T00:00:00Z'` under `verified:` in `07/01-fem-backend-ngsolvenetgen.md` (`tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts`), `07/03-charge-and-electrostatics.md` (`tests/tier1/test_pqr.py::test_ver57_pdb2pqr_38_terminal_patches_name_no_residue`), `07/05-gui-and-packaging.md` (`tests/tier1/test_gui_screens.py::test_ver78_a_rebound_shortcut_runs_its_command_and_the_old_chord_nothing`), `07/23-pinning-a-protonation-state-through-apply-pka-values.md` (`tests/tier1/test_library_behaviour.py::test_fr38_the_titratable_groups_are_propkas`). All five ran and passed on this tree on 8 November 2026 (`test_ver78` with `NANOPNP_REQUIRE_BROWSER=1`).
- `07/24-pint-with-a-fraction-registry-exact-units.md`: put `**[tested: tests/tier1/test_variables.py::test_fr39_a_conversion_of_the_same_dimension_is_exact]**` on the body sentence that says a conversion of the same dimension is exact (find it with `grep -n exact`).
- `07/16-ngsolves-bundled-stubs-cannot-type-check-so-the.md:16` delete the empty `verified:` key.

## after the fixes

- `uv run .claude/scripts/audit/links.py --anchors`, `uv run .claude/scripts/audit/markers.py`, `uv run .claude/scripts/clause.py P4 W4 W7 X5 Z1 AC3 AC4 AE5 AG1 AI13 --no-history | head`, `uv run .claude/scripts/duplicates.py`, the strict build. Save each to `raw/` with the commit named.
- Fill `raw/commits.tsv` (category → sha), run `register.py`, then the gate and the push (CLAUDE.md), then the PR.
