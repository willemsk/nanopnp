# Claim markers of `knowledge/` reconciled

`[tested:]` markers: 448. `[verified]` markers: 123.

## `[tested:]` markers whose test does not exist (1)

- `knowledge/log.md:38` unparseable marker `…`

## Files whose `verified:` list differs from the tests their markers name (6)

- `knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md`: in `verified:` only: —; in markers only: ['tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts']
- `knowledge/07-software-stack/03-charge-and-electrostatics.md`: in `verified:` only: —; in markers only: ['tests/tier1/test_pqr.py::test_ver57_pdb2pqr_38_terminal_patches_name_no_residue']
- `knowledge/07-software-stack/05-gui-and-packaging.md`: in `verified:` only: —; in markers only: ['tests/tier1/test_gui_screens.py::test_ver78_a_rebound_shortcut_runs_its_command_and_the_old_chord_nothing']
- `knowledge/07-software-stack/23-pinning-a-protonation-state-through-apply-pka-values.md`: in `verified:` only: —; in markers only: ['tests/tier1/test_library_behaviour.py::test_fr38_the_titratable_groups_are_propkas']
- `knowledge/07-software-stack/24-pint-with-a-fraction-registry-exact-units.md`: in `verified:` only: ['tests/tier1/test_variables.py::test_fr39_a_conversion_of_the_same_dimension_is_exact']; in markers only: —
- `knowledge/log.md`: in `verified:` only: —; in markers only: ['…']

## `[verified]` claims with no footnote reference on their line (20)

- `knowledge/00-orientation/03-conventions-used-throughout.md:19`: a claim verified by arithmetic or by reading a source is marked `[verified]`
- `knowledge/00-orientation/04-provenance-and-how-to-extend-this.md:32`: Mark each claim `[tested: <test>]` or `[verified]` with a footnote to its source, and keep the header's
- `knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md:29`: - **[verified]** The charged tube's two atoms sit 0.75 Å in Gaussian width (`w` = 0.075 nm), so an areal peak lies `w²/2r` < 0.001 nm off its atom at `r` ≥ 3.25
- `knowledge/07-software-stack/02-structure-trajectory-and-density.md:123`: **The 3.11 floor makes this moot [verified].** With `requires-python = ">=3.11"` and
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:71`: BSD-3, a pure-Python wheel, and requires Python ≥ 3.11, < 4. 3.7.1 pins `docutils==0.17.1`, which NiceGUI 3 cannot take; 3.8.0 (Python ≥ 3.10) has no `docutils`
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:230`: The maps APBS reads are about 0.6 GB of text at 193³, which `run_apbs` deletes once read **[verified]**.
- `knowledge/07-software-stack/04-geometry-meshing-and-io.md:105`: **meshio 5.3.5's MSH 4.1 writer gets entity bookkeeping wrong in two ways, both silent [verified].**
- `knowledge/07-software-stack/05-gui-and-packaging.md:165`: ### `netgen.webgui.GenerateHTML` ignores its `template` argument **[verified]** {#netgenwebguigeneratehtml-ignores-its-template-argument}
- `knowledge/07-software-stack/05-gui-and-packaging.md:191`: stands. **[verified]**, 22 September 2026.
- `knowledge/07-software-stack/05-gui-and-packaging.md:204`: ### A webgui scene draws on a material *region*, not only on a whole mesh **[verified]** {#a-webgui-scene-draws-on-a-material-region-not-only-on-a-whole-mesh}
- `knowledge/07-software-stack/05-gui-and-packaging.md:244`: ### SIGTERM stops a child busy inside netgen in milliseconds **[verified]** {#sigterm-stops-a-child-busy-inside-netgen-in-milliseconds}
- `knowledge/07-software-stack/05-gui-and-packaging.md:334`: ### PDB2PQR and PROPKA bundle through `collect_all`, and fail inside PDB2PQR's run **[verified]** {#pdb2pqr-and-propka-bundle-through-collect_all-and-fail-insid
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:33`: **Resolved, 24 September 2026 [verified]: the floor is now 3.11** (§8.2.2 B4, WP17). With
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:64`: **[verified]**. Nothing in the current dependency set contradicts CON-07.
- `knowledge/07-software-stack/20-tier-1-test-evidence-import-costs.md:37`: - **[verified]** `grep -q` exits at the first match; under `pipefail` the writer's SIGPIPE once made a tracked Gmsh change read as a miss in the hook's Gmsh req
- `knowledge/08-validation-benchmarks/00-overview.md:17`: was checked numerically where marked `[verified]`.
- `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md:37`: - **[verified]** The COMSOL golden is read from `$NANOPNP_REFERENCE_DATA/comsol/<case>/<refinement>/golden.npz`, the layout `docs/validation/comsol-export-contr
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:31`: | 2 | `knowledge/06-numerics-fem/05-nonlinear-solution.md`: "PARDISO direct + Newton with a lower-bounded variable damping factor", unverified provenance | **Co
- `knowledge/log.md:38`: * **Update**: Retargeted the `[tested: …]` markers that named a test deleted by the test scope (WP50, §8.2.13 N3): 31 markers became `[verified]` on their sourc
- `knowledge/log.md:53`: * **Update**: Replaced every executable `[verified]` arithmetic and closed-form claim across the bundle with Tier-1 test evidence (`tests/tier1/test_knowledge_a

## `[verified]` claims by the source their footnotes name

- plan or review: 70
- COMSOL report: 17
- specification: 9
- ESI: 6
- code or test: 5
- thesis: 1

- `knowledge/00-orientation/07-glossary.md:27` `[^spec]` → specification: * **rung**. A single discrete sub-problem solved within the NUM-18 continuation ladder. The ladder numbers its rungs 1 t
- `knowledge/00-orientation/07-glossary.md:83` `[^spec]` → specification: * **steric flux (PHY-05)**. The ion-crowding term beta_i added to the Nernst-Planck flux bracket. It is species-dependen
- `knowledge/00-orientation/07-glossary.md:85` `[^spec]` → specification: * **concentration-dependent permittivity (PHY-11)**. The fall of the solvent relative permittivity with local salt conce
- `knowledge/00-orientation/07-glossary.md:89` `[^spec]` → specification: * **access conductance trap**. A common literature error that substitutes pore radius for diameter in Hall access conduc
- `knowledge/00-orientation/07-glossary.md:127` `[^spec]` → specification: * **cylindrical hoop strain (NUM-05)**. The geometric viscous stress term 2 eta u_r v_r / r^2 of the cylindrical strong 
- `knowledge/00-orientation/07-glossary.md:129` `[^spec]` → specification: * **dual-route agreement (NUM-26, QR-04)**. The requirement that total current computed via cross-sectional indicator in
- `knowledge/00-orientation/07-glossary.md:141` `[^code]` → code or test: * **the walk**. The canonical pipeline that executes simulation workflows over the thirteen registered stages, minus tho
- `knowledge/00-orientation/07-glossary.md:153` `[^spec]` → specification: * **refusal vs failure**. Exit codes are a contract (IF-02). A refusal is a clean, diagnostic abort: exit code 3 for a c
- `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md:80` `[^comsol-report]` → COMSOL report: model file. The difference is ~1 % in `ε_r` at saturation and negligible below ~1 M **[tested: tests/tier1/test_knowledg
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:88` `[^thesis]` → thesis: **Which radii.** The thesis says only "Van der Waals radius". The author ruled on 25 September 2026 that R_i is the CHAR
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:107` `[^wp18-plan]` → plan or review: ### 1.1 The author's MD archive, measured [verified][^wp18-plan] {#11-the-authors-md-archive-measured}
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:117` `[^wp18-plan]` → plan or review: | `prod5_trajectory_last_10ns.7z` | **99 PQR files**, `prod5_protein_aligned_100ps_NN.pdb.pqr` with NN = 01–99, written 
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:120` `[^wp18-plan]` → plan or review: | The deposited 2WCD | **Not the author's `2wcd.pdb`.** The wwPDB entry's asymmetric unit holds two dodecamers, chains A
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:122` `[^wp18-plan]` → plan or review: | Stage 1 on the archive | All 98 frames, superposed on frame 0 over every Cα (0.095–0.219 nm RMSD to it), 12 chains × 2
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:125` `[^wp20-plan]` → plan or review: ### 1.2 The author's contour script, read [verified][^wp20-plan] {#12-the-authors-contour-script-read}
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:146` `[^wp20-plan]` → plan or review: in the index-to-radius map, not in the binning **[tested: tests/tier1/test_val05_geometry.py::test_val05_the_attribution
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:170` `[^wp20-plan]` → plan or review: ### 1.3 Stage 4 on real and synthetic inputs, measured **[tested: tests/tier2/test_contour_2wcd.py::test_ver51_2wcd_cont
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:204` `[^wp20-plan]` → plan or review: ensemble, a few seconds, batched per frame and bounded by `CHUNK_ELEMENTS` (32 MB of float64) **[tested: tests/tier1/tes
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:207` `[^wp22-plan]` → plan or review: ### 1.4 2WCD against the reference polygon, and the isolevel lever **[tested: tests/tier2/test_val05_2wcd.py::test_val05
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:218` `[^wp22-plan]` → plan or review: > diagnostic and is never used **[tested: tests/tier2/test_val05_2wcd.py::test_val05_2wcd_against_the_reference_polygon]
- `knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md:273` `[^wp22-plan]` → plan or review: ### 1.5 The ensemble against the reference polygon [verified][^wp22-plan] {#15-the-ensemble-against-the-reference-polygo
- `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md:85` `[^wp21-plan]` → plan or review: complement of a simple polygon is connected. **[verified][^wp21-plan]**
- `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md:91` `[^wp21-plan]` → plan or review: `r₄`" cannot be tested on a four-crossing body: no such body assembles. **[verified][^wp21-plan]** by the
- `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md:96` `[^wp30-plan]` → plan or review: ### 2.2 The ion-exclusion shell and the derived `χ` on 2WCD, measured **[tested: tests/tier2/test_exclusion_2wcd.py::tes
- `knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md:67` `[^wp28-plan]` → plan or review: ### 3.1 The delivered table, measured [verified][^wp28-plan] {#31-the-delivered-table-measured}
- `knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md:96` `[^wp28-plan]` → plan or review: ### 3.2 The reference's 1.25 % is the *consumer's*, and it is aliasing [verified][^wp28-plan] {#32-the-references-125-is
- `knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md:164` `[^wp28-plan]` → plan or review: Measured implementing it (WP28, 1 October 2026) **[tested: tests/tier1/test_charge_deposit.py::test_ver01_truncated_patc
- `knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md:32` `[^wp18-plan]` → plan or review: `dt=100`. **CLOSED [verified][^wp18-plan], §1.1:** the DCD frames are the PQRs at 100 ps, in time order. The final
- `knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md:49` `[^wp28-plan]` → plan or review: - **G5 — CLOSED [verified][^wp28-plan], §3.1.** The file stores the sum *without* `e`, in `e/m^2`: its planar
- `knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md:76` `[^wp28-plan]` → plan or review: - **G10 — CLOSED [verified][^wp28-plan], §3.1.** `r` in [0, 7] nm, `z` in [-3.5, 13.5] nm at 0.005 nm:
- `knowledge/04-clya-geometry-and-charge/12-tier-2-test-evidence-quadrature-gates.md:39` `[^charge-conservation-3782c43]` → plan or review: - **[verified][^charge-conservation-3782c43]** On the structured under-resolving mesh family of QR-03's agreement gate t
- `knowledge/04-clya-geometry-and-charge/12-tier-2-test-evidence-quadrature-gates.md:40` `[^charge-conservation-3782c43]` → plan or review: - **[verified][^charge-conservation-3782c43]** An unstructured netgen `maxh = 0.2 nm` mesh of the same geometry gave 2.3
- `knowledge/04-clya-geometry-and-charge/12-tier-2-test-evidence-quadrature-gates.md:45` `[^exclusion-stern-3782c43]` → plan or review: - **[verified][^exclusion-stern-3782c43]** With the bilayer (`ε = 3.2` on the body's outer side) on the analysis plane, 
- `knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md:26` `[^wp31-plan]` → plan or review: - **[verified][^wp31-plan]** The deployed charged-tube field's worst-plane error against the 1e-3 quadrature gate of PHY
- `knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md:26` `[^wp31-plan]` → plan or review: - **[verified][^wp31-plan]** The deployed charged-tube field's worst-plane error against the 1e-3 quadrature gate of PHY
- `knowledge/05-analyte-and-forces/13-tier-2-test-evidence-electro-osmosis.md:40` `[^electrophoretic-mobility-3782c43]` → plan or review: - **[verified][^electrophoretic-mobility-3782c43]** The far field of the force-free pair is uniform to `O((a/R)³)`, beca
- `knowledge/06-numerics-fem/04-stabilisation.md:250` `[^fb4f9ae]` → code or test: Most of that assembly cost is the **manufactured source**, not the streamline term itself **[verified][^fb4f9ae]**.
- `knowledge/06-numerics-fem/04-stabilisation.md:260` `[^fb4f9ae]` → code or test: **The cost is the source's *representation*, and it is removed in the harness.** **[tested: tests/tier2/test_stabilised_
- `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md:79` `[^specification]` → specification: **The sign is the one that references the current to the grounded cis electrode. [verified][^specification]**
- `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md:271` `[^specification]` → specification: **NUM-28 prints only the first term, and the second is not zero in this model. [verified][^specification]**
- `knowledge/06-numerics-fem/08-mesh-resolution-and-adaptivity.md:47` `[^esi]` → ESI: refinement strategy, no tolerances, no convergence study. **[verified][^esi]** by grep over
- `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md:245` `[^wp3-singular-system]` → plan or review: **[verified][^wp3-singular-system]** The current scalar-Poisson reproduction separately checks
- `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md:647` `[^wp11-sweep-timings]` → plan or review: - **Parallel efficiency on four cores: 1.00, 0.76, 0.50 at N = 1, 2, 4. [verified][^wp11-sweep-timings]** 25 points in
- `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md:657` `[^wp11-sweep-timings]` → plan or review: `efficiency(4)` from 0.75 to **0.29**. **[verified][^wp11-sweep-timings]**
- `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md:745` `[^wp45-validation-strip]` → plan or review: ### 8.5.2 Small facts recorded from the `validation/` prose strip **[verified][^wp45-validation-strip]** {#852-small-fac
- `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md:49` `[^factorisation-doc-3782c43]` → plan or review: - **[verified][^factorisation-doc-3782c43]** The reservoir-cap Dirichlet constraints of the five-field block system remo
- `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md:53` `[^envelope-doc-3782c43]` → plan or review: - **[tested: tests/tier2/test_envelope.py::test_82_bias_walk_emits_waypoints_verbatim]** Recording the envelope on the w
- `knowledge/06-numerics-fem/17-tier-3-test-evidence-the-mesh-geometry.md:25` `[^conftest-3782c43]` → plan or review: - **[verified][^conftest-3782c43]** NGSolve's pickle round-trips a mesh's vertices to the bit, whereas its `.vol` text m
- `knowledge/07-software-stack/02-structure-trajectory-and-density.md:106` `[^wp17-plan]` → plan or review: **GridDataFormats before 1.2 has no MRC writer [verified][^wp17-plan].**
- `knowledge/07-software-stack/02-structure-trajectory-and-density.md:132` `[^wp18-plan]` → plan or review: **Why principal axes fail on ClyA: they drift, but not from degeneracy [verified][^wp18-plan].** Measured on
- `knowledge/07-software-stack/02-structure-trajectory-and-density.md:207` `[^wp19-plan]` → plan or review: **Density deposition and the (r, z) reduction, measured [verified][^wp19-plan].** Measured on 25 September 2026
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:70` `[^wp17-plan]` → plan or review: **Package facts, read from PyPI's metadata on 30 September 2026 [verified]:**[^wp17-plan] `pdb2pqr` 3.7.1 is
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:148` `[^wp27-plan]` → plan or review: (`HETATM12345`, `get_common_string_rep`) **[verified][^wp27-plan]**, read from the 3.7.1 source. PROPKA types
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:153` `[^wp27-plan]` → plan or review: written with no charge gets `0.0000` (`get_pqr_string`) **[verified][^wp27-plan]**, read from the 3.7.1
- `knowledge/07-software-stack/03-charge-and-electrostatics.md:233` `[^case-identity-record]` → plan or review: MDAnalysis **[verified][^case-identity-record]**. These are historical measurements, not performance guarantees.
- `knowledge/07-software-stack/04-geometry-meshing-and-io.md:232` `[^wp23-plan]` → plan or review: - **On `ubuntu-latest`, four packages make it import [verified][^wp23-plan].** GitHub's image lacks
- `knowledge/07-software-stack/05-gui-and-packaging.md:54` `[^wp14-plan]` → plan or review: | `PySide6.QtWebEngineWidgets.QWebEngineView` | — | Hosts NGSolve webgui **[verified][^wp14-plan]**. The earlier "import
- `knowledge/07-software-stack/05-gui-and-packaging.md:58` `[^wp14-plan]` → plan or review: ### PySide6 imports are a system-library question, not a wheel question **[verified][^wp14-plan]** {#pyside6-imports-are
- `knowledge/07-software-stack/05-gui-and-packaging.md:78` `[^wp14-plan]` → plan or review: ### A missing `libEGL.so.1` can be shimmed for local work, never for the gate **[verified][^wp14-plan]** {#a-missing-lib
- `knowledge/07-software-stack/05-gui-and-packaging.md:95` `[^wp501-plan]` → plan or review: ### Offscreen Qt runs with system libraries, and headless Playwright draws a host document **[verified][^wp501-plan]** {
- `knowledge/07-software-stack/05-gui-and-packaging.md:122` `[^wp14-plan]` → plan or review: ### `QWebEngineView` loads a webgui document with no GPU at all **[verified][^wp14-plan]** {#qwebengineview-loads-a-webg
- `knowledge/07-software-stack/05-gui-and-packaging.md:183` `[^wp15-plan]` → plan or review: **[verified][^wp15-plan]**). Its tarball for 0.2.39 is 503,052 B, and its published `dist.integrity` is
- `knowledge/07-software-stack/05-gui-and-packaging.md:220` `[^wp31-plan]` → plan or review: ### A fixed colour range needs the scene's keys and the viewer's own settings **[verified][^wp31-plan]** {#a-fixed-colou
- `knowledge/07-software-stack/05-gui-and-packaging.md:232` `[^wp15-plan]` → plan or review: ### `QWebEngineView` can be constructed in this container with the Playwright GL shim **[verified][^wp15-plan]** {#qwebe
- `knowledge/07-software-stack/05-gui-and-packaging.md:253` `[^wp15-plan]` → plan or review: ### A PyInstaller bundle carries neither OCCT nor OpenBLAS unless told to **[verified][^wp15-plan]** {#a-pyinstaller-bun
- `knowledge/07-software-stack/05-gui-and-packaging.md:376` `[^wp24-plan]` → plan or review: ### The geometry tab's view-models stay under the schema's cost **[verified][^wp24-plan]** {#the-geometry-tabs-view-mode
- `knowledge/07-software-stack/05-gui-and-packaging.md:434` `[^wp502-report]` → plan or review: ### A NiceGUI screen is ready when Mol* has built and drawn once, and a click before then is lost **[verified][^wp502-re
- `knowledge/07-software-stack/05-gui-and-packaging.md:461` `[^wp508-plan]` → plan or review: ### Quasar paints its tab panels, cards and menus white whatever the theme **[verified][^wp508-plan]** {#quasar-paints-i
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:40` `[^wp17-plan]` → plan or review: Resolved with `uv 0.12.5`, August 2026, against live PyPI **[verified][^wp17-plan]**.
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:44` `[^wp17-plan]` → plan or review: win_amd64** — fifteen wheels, no gaps **[verified][^wp17-plan]**.
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:66` `[^wp17-plan]` → plan or review: **The local gate cannot see a 3.10 floor break; only the CI matrix can [verified][^wp17-plan].** The gate of
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:74` `[^wp17-plan]` → plan or review: `Module "datetime" has no attribute "UTC"  [attr-defined]` on a two-line file **[verified][^wp17-plan]** — but it
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:77` `[^wp17-plan]` → plan or review: Python 3.12 and greater  [syntax]` before reaching project code **[verified][^wp17-plan]**. So the guard is the
- `knowledge/07-software-stack/08-python-version-floor-the-310-target-is.md:81` `[^wp43-plan]` → plan or review: **The development interpreter is 3.14, and it computes VER-62's numbers as 3.12 does [verified][^wp43-plan].**
- `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md:33` `[^wp33-plan]` → plan or review: ## 12. The suite's BLAS threads buy nothing; parallelism has to come from workers **[verified][^wp33-plan]** {#12-the-su
- `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md:97` `[^wp33-plan]` → plan or review: - **Where the suite's time goes** **[verified][^wp33-plan]**, after WP33. The 54 `extended` tests are the
- `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md:109` `[^wp44-plan]` → plan or review: ### 12.1 Test-impact selection was built, measured and removed **[verified][^wp44-plan]** {#121-test-impact-selection-wa
- `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md:128` `[^wp43-plan]` → plan or review: ### 12.2 Where the time goes on 3.14, and coverage's `sysmon` core **[verified][^wp43-plan]** {#122-where-the-time-goes-
- `knowledge/07-software-stack/15-an-npz-is-reproducible-bytes-only-if.md:40` `[^wp32-plan]` → plan or review: **Removing the time is a schema change, not just a code change [verified][^wp32-plan].** A store hit serves the
- `knowledge/07-software-stack/20-tier-1-test-evidence-import-costs.md:33` `[^importtime-3782c43]` → plan or review: - **[verified][^importtime-3782c43]** Import costs under `python -X importtime`, measured for VER-72: `scipy.sparse` ~26
- `knowledge/07-software-stack/21-tier-2-test-evidence-budgets-timings.md:37` `[^example05-3782c43]` → plan or review: - **[verified][^example05-3782c43]** Example 05's frozen solve on the ClyA reference mesh took 2,512 s on one core (WP16
- `knowledge/07-software-stack/21-tier-2-test-evidence-budgets-timings.md:40` `[^example07-3782c43]` → plan or review: - **[verified][^example07-3782c43]** Example 07's ePNP-NS solve at `size_scale` 4 (chosen for runtime) takes a few minut
- `knowledge/07-software-stack/22-tier-2-test-evidence-analytic.md:127` `[^pnp-benchmarks-3782c43]` → plan or review: - **[verified][^pnp-benchmarks-3782c43]** At `δ` = 10⁻³ and classical PNP, the current over the closed form is 1.138 at 
- `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md:32` `[^wp22-d12]` → plan or review: - **[verified][^wp22-d12]** Depositing the ClyA-AS ensemble's stages 1 to 3 costs about 16 minutes on the author's machi
- `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md:33` `[^wp29-design5]` → plan or review: - **[verified][^wp29-design5]** The VAL-06 archive leg takes about 75 minutes, most of it the 100 APBS runs at 193³. Sou
- `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md:34` `[^conftest-timings-3782c43]` → code or test: - **[verified][^conftest-timings-3782c43]** PROPKA protonation of the prepared 2WCD takes about a minute, a charged walk
- `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md:36` `[^conftest-timings-3782c43]` → code or test: - **[verified][^conftest-timings-3782c43]** The default-size 0.15 M mesh of the prepared 2WCD takes about 8 s, and it is
- `knowledge/09-comsol-reference-settings/00-overview.md:47` `[^comsol-report]` → COMSOL report: **Pagination.** The document runs to p. 162; 143 is the ToC page number of §5 *Results*. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/02-mesh-27.md:65` `[^comsol-report]` → COMSOL report: therefore **not applicable**, not merely absent. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/03-solver-3-4.md:71` `[^comsol-report]` → COMSOL report: **Fully coupled. No segregated solver, no segregation groups.** **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/03-solver-3-4.md:87` `[^comsol-report]` → COMSOL report: **variable with a lower bound of 0.01**, started at 0.2. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:64` `[^comsol-report]` → COMSOL report: but unused. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:103` `[^comsol-report]` → COMSOL report: KB convention for `d`. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:128` `[^comsol-report]` → COMSOL report: **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:145` `[^comsol-report]` → COMSOL report: concentration**, confirming ruling 3 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`. **[verif
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:223` `[^comsol-report]` → COMSOL report: weak form, so results are unaffected. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:246` `[^comsol-report]` → COMSOL report: | Dielectric-gradient force | **Absent** — confirms trap 3 of `knowledge/00-orientation/02-the-five-things-most-likely-t
- `knowledge/09-comsol-reference-settings/04-physics-settings.md:282` `[^comsol-report]` → COMSOL report: **NOT IN REPORT**. **[verified][^comsol-report]**
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:32` `[^comsol-report]` → COMSOL report; `[^esi]` → ESI: | 3 | ruling 2 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: permittivity fit = authors' Bu
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:36` `[^comsol-report]` → COMSOL report; `[^esi]` → ESI: | 7 | trap 1 of `knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`: wall function `1 − exp(−6.2(d 
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:37` `[^comsol-report]` → COMSOL report; `[^esi]` → ESI: | 8 | trap 3 of `knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`: no dielectric-gradient body fo
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:38` `[^comsol-report]` → COMSOL report; `[^esi]` → ESI: | 9 | ruling 3 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: `⟨c⟩` = arithmetic mean of ion
- `knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md:39` `[^comsol-report]` → COMSOL report; `[^esi]` → ESI: | 10 | ruling 5 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: `ε_protein` = 20 | `epsr_nano
