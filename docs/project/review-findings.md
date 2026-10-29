---
findings:
  prefix: REV
  status: open
  areas: [coupling, performance, verification, documentation, physics, numerics, interface, process]
---

# Review findings

The log of [the review register](review-items.md) (§8.2.8 H12): every item a work package's
implementation or review left open, until it is resolved. `/np-implement` and `/np-ship` add a row
in the commit that leaves an item open, and the commit that resolves it sets the row `fixed`, its
ruling linking the plan that fixed it.

**Status** is `open` until the author rules; then `accepted` (owned by a named later package),
`fixed`, or `deferred`, `post-1.0`, `declined` or `wontfix` (the ruling names the §8.2 row; `wontfix`
for a row whose code or bundle leaves before it is fixed). **Severity** is
`high` for a SHALL the code does not meet, `medium` for a property held only by convention, and
`low` for size or tidiness. `tests/tier1/test_findings_logs.py` checks every row (VER-63). The log
is a rolling register, and its header stays `open`.

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
| REV-01 | performance | low | fixed | [WP37](../plans/wp37-cycle-cuts-exit-codes-backend-guard.md) | [TOL_NM's home loaded pydantic and yaml](review-items.md#rev-01-tol_nms-home-loaded-pydantic-and-yaml) |
| REV-02 | coupling | low | fixed | [WP37](../plans/wp37-cycle-cuts-exit-codes-backend-guard.md) | [cli/errors.py was a re-export nothing imported](review-items.md#rev-02-clierrorspy-was-a-re-export-nothing-imported) |
| REV-03 | coupling | low | fixed | [WP38](../plans/wp38-io-split.md) | [The solution-field names lived in two layers](review-items.md#rev-03-the-solution-field-names-lived-in-two-layers) |
| REV-04 | verification | medium | fixed | [WP37](../plans/wp37-cycle-cuts-exit-codes-backend-guard.md) | [VER-61's ratchet did not see an import moved into a function](review-items.md#rev-04-ver-61s-ratchet-did-not-see-an-import-moved-into-a-function) |
| REV-05 | coupling | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [The shells read the nanopnp facade](review-items.md#rev-05-the-shells-read-the-nanopnp-facade) |
| REV-06 | physics | medium | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [A supplied charge or permittivity field has no stated frame beside a moved structure](review-items.md#rev-06-a-supplied-charge-or-permittivity-field-has-no-stated-frame-beside-a-moved-structure) |
| REV-07 | numerics | medium | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [The conservation gate and the Poisson source integrate an areal charge differently](review-items.md#rev-07-the-conservation-gate-and-the-poisson-source-integrate-an-areal-charge-differently) |
| REV-08 | numerics | medium | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [Newton's update test takes one norm over every field](review-items.md#rev-08-newtons-update-test-takes-one-norm-over-every-field) |
| REV-09 | physics | medium | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [A driver clamp under the ionic-strength driver is never logged](review-items.md#rev-09-a-driver-clamp-under-the-ionic-strength-driver-is-never-logged) |
| REV-10 | verification | medium | fixed | [WP37](../plans/wp37-cycle-cuts-exit-codes-backend-guard.md) | [The prose rule let a ruling or a report heading change without VER-63](review-items.md#rev-10-the-prose-rule-let-a-ruling-or-a-report-heading-change-without-ver-63) |
| REV-11 | verification | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [No check catches a NaN-permissive gate comparison](review-items.md#rev-11-no-check-catches-a-nan-permissive-gate-comparison) |
| REV-12 | verification | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [No test shows every case leaf changes the forms or is provenance-only](review-items.md#rev-12-no-test-shows-every-case-leaf-changes-the-forms-or-is-provenance-only) |
| REV-13 | verification | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [Example 06's key test cannot see a stage-7 key change](review-items.md#rev-13-example-06s-key-test-cannot-see-a-stage-7-key-change) |
| REV-14 | numerics | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A radial grid's .npz does not round-trip its spacing exactly](review-items.md#rev-14-a-radial-grids-npz-does-not-round-trip-its-spacing-exactly) |
| REV-15 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [Example 05 quotes #SBATCH directives as shell words](review-items.md#rev-15-example-05-quotes-sbatch-directives-as-shell-words) |
| REV-16 | performance | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A salt sweep regenerates an identical mesh at each concentration](review-items.md#rev-16-a-salt-sweep-regenerates-an-identical-mesh-at-each-concentration) |
| REV-17 | numerics | low | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [A warm start is gated on free prose in the stabilisation provenance](review-items.md#rev-17-a-warm-start-is-gated-on-free-prose-in-the-stabilisation-provenance) |
| REV-18 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [Concurrent sweep members may write the same store key](review-items.md#rev-18-concurrent-sweep-members-may-write-the-same-store-key) |
| REV-19 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A zero-frame trajectory raises a bare IndexError](review-items.md#rev-19-a-zero-frame-trajectory-raises-a-bare-indexerror) |
| REV-20 | process | low | wontfix | §8.2.18 T1 | [The desktop shell has no multiprocessing.freeze_support](review-items.md#rev-20-the-desktop-shell-has-no-multiprocessingfreeze_support) |
| REV-21 | process | low | declined | §8.2.8 H12 | [numerics/linear.py imports scipy inside its functions](review-items.md#rev-21-numericslinearpy-imports-scipy-inside-its-functions) |
| REV-22 | process | low | declined | §8.2.8 H12 | [write_dx formats with %](review-items.md#rev-22-write_dx-formats-with) |
| REV-23 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The corrections test bounds both ions by one range](review-items.md#rev-23-the-corrections-test-bounds-both-ions-by-one-range) |
| REV-24 | process | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [Sampler construction may still be duplicated](review-items.md#rev-24-sampler-construction-may-still-be-duplicated) |
| REV-25 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A post stage run without a solve writes scratch to the default store](review-items.md#rev-25-a-post-stage-run-without-a-solve-writes-scratch-to-the-default-store) |
| REV-26 | interface | low | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [stabilisation_parameters returns an empty mapping off the coupled model](review-items.md#rev-26-stabilisation_parameters-returns-an-empty-mapping-off-the-coupled-model) |
| REV-27 | interface | low | fixed | [WP38](../plans/wp38-io-split.md) | [The inf-sup check ran at resolve, not at validation](review-items.md#rev-27-the-inf-sup-check-ran-at-resolve-not-at-validation) |
| REV-28 | performance | low | deferred | §8.2.18 T2 | [The viewer renders every finished run eagerly](review-items.md#rev-28-the-viewer-renders-every-finished-run-eagerly) |
| REV-29 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The cylindrical-pore fixture is copied into four test modules](review-items.md#rev-29-the-cylindrical-pore-fixture-is-copied-into-four-test-modules) |
| REV-30 | performance | low | deferred | §8.2.18 T2 | [The viewer's scene is written twice](review-items.md#rev-30-the-viewers-scene-is-written-twice) |
| REV-31 | documentation | low | wontfix | §8.2.18 T1 | [The bundle's size is not recorded](review-items.md#rev-31-the-bundles-size-is-not-recorded) |
| REV-32 | interface | low | deferred | §8.2.18 T2 | [Old store entries are neither migrated nor removed](review-items.md#rev-32-old-store-entries-are-neither-migrated-nor-removed) |
| REV-33 | interface | low | declined | §8.2.9 I3 | [writable_formats assumes the extra's floor](review-items.md#rev-33-writable_formats-assumes-the-extras-floor) |
| REV-34 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [Two reference tests duplicate the frozen case](review-items.md#rev-34-two-reference-tests-duplicate-the-frozen-case) |
| REV-35 | performance | low | post-1.0 | §8.2.9 I3 | [_second_crossings loops in Python](review-items.md#rev-35-_second_crossings-loops-in-python) |
| REV-36 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [The gmsh session stops a caller's logger](review-items.md#rev-36-the-gmsh-session-stops-a-callers-logger) |
| REV-37 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [A broken gmsh wheel is not a refusal](review-items.md#rev-37-a-broken-gmsh-wheel-is-not-a-refusal) |
| REV-38 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [gmsh.model.remove() can mask the error it follows](review-items.md#rev-38-gmshmodelremove-can-mask-the-error-it-follows) |
| REV-39 | interface | low | deferred | §8.2.18 T2 | [A case supplying inputs.profile gets no contour editor](review-items.md#rev-39-a-case-supplying-inputsprofile-gets-no-contour-editor) |
| REV-40 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [DensityMap.read accepts a file written in nm](review-items.md#rev-40-densitymapread-accepts-a-file-written-in-nm) |
| REV-41 | interface | low | deferred | §8.2.18 T3 | [No prepare command, upto on reproduce, or region export](review-items.md#rev-41-no-prepare-command-upto-on-reproduce-or-region-export) |
| REV-42 | interface | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [pnp carries inert flow keys](review-items.md#rev-42-pnp-carries-inert-flow-keys) |
| REV-43 | process | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [chain_characters duplicates the export's mapping](review-items.md#rev-43-chain_characters-duplicates-the-exports-mapping) |
| REV-44 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The Stern-layer test re-solves the drawn slab](review-items.md#rev-44-the-stern-layer-test-re-solves-the-drawn-slab) |
| REV-45 | interface | low | deferred | §8.2.18 T3 | [The derived χ field has no export](review-items.md#rev-45-the-derived-field-has-no-export) |
| REV-46 | verification | low | deferred | §8.2.9 I3 | [Example 07 is not run at default sizes or on the ensemble](review-items.md#rev-46-example-07-is-not-run-at-default-sizes-or-on-the-ensemble) |
| REV-47 | process | low | accepted | §8.2.9 I3 | [The test-duration targets are missed](review-items.md#rev-47-the-test-duration-targets-are-missed) |
| REV-48 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The 2WCD walk test copies its constants](review-items.md#rev-48-the-2wcd-walk-test-copies-its-constants) |
| REV-49 | process | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [AXISYMMETRIC is replaced repeatedly](review-items.md#rev-49-axisymmetric-is-replaced-repeatedly) |
| REV-50 | process | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [_inner_wall_nm re-implements innermost_crossings](review-items.md#rev-50-_inner_wall_nm-re-implements-innermost_crossings) |
| REV-51 | performance | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A redundant reopen and resolve in WP34's walk](review-items.md#rev-51-a-redundant-reopen-and-resolve-in-wp34s-walk) |
| REV-52 | interface | low | deferred | §8.2.18 T2 | [deviations and SolveReporting are off the stage protocol](review-items.md#rev-52-deviations-and-solvereporting-are-off-the-stage-protocol) |
| REV-53 | interface | low | declined | §8.2.9 I3 | [Some walk rules stay as case logic](review-items.md#rev-53-some-walk-rules-stay-as-case-logic) |
| REV-54 | verification | low | fixed | [WP38](../plans/wp38-io-split.md) | [The MOD-12 check compared names, not modules](review-items.md#rev-54-the-mod-12-check-compared-names-not-modules) |
| REV-55 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [Per-stage mkdtemp fallbacks](review-items.md#rev-55-per-stage-mkdtemp-fallbacks) |
| REV-56 | performance | low | wontfix | §8.2.18 T1 | [The geometry editor's simplicity check runs on the Qt thread](review-items.md#rev-56-the-geometry-editors-simplicity-check-runs-on-the-qt-thread) |
| REV-57 | performance | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [frame_times decodes every frame](review-items.md#rev-57-frame_times-decodes-every-frame) |
| REV-58 | performance | low | post-1.0 | §8.2.9 I3 | [The azimuthal reduction projects cells it then drops](review-items.md#rev-58-the-azimuthal-reduction-projects-cells-it-then-drops) |
| REV-59 | interface | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [attribute_to_construction raises the wrong error on a lax comparison](review-items.md#rev-59-attribute_to_construction-raises-the-wrong-error-on-a-lax-comparison) |
| REV-60 | performance | low | deferred | §8.2.9 I3 | [UMFPACK repeats its symbolic analysis every Newton step](review-items.md#rev-60-umfpack-repeats-its-symbolic-analysis-every-newton-step) |
| REV-61 | interface | low | deferred | §8.2.9 I3 | [No B-spline fit or HOLE cross-check of the contour](review-items.md#rev-61-no-b-spline-fit-or-hole-cross-check-of-the-contour) |
| REV-62 | interface | low | deferred | §8.2.18 T2 | [A mesh named by store key is refused](review-items.md#rev-62-a-mesh-named-by-store-key-is-refused) |
| REV-63 | performance | low | fixed | [WP38](../plans/wp38-io-split.md) | [The protonation stage walked through meshing](review-items.md#rev-63-the-protonation-stage-walked-through-meshing) |
| REV-64 | verification | low | deferred | §8.2.9 I3 | [A sweep's plan-time NUM-34 gate skips generated meshes](review-items.md#rev-64-a-sweeps-plan-time-num-34-gate-skips-generated-meshes) |
| REV-65 | interface | low | wontfix | §8.2.18 T1 | [The Windows bundle exposes no mesh command](review-items.md#rev-65-the-windows-bundle-exposes-no-mesh-command) |
| REV-66 | interface | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [A model without flow is refused on its element pair before its flow switch](review-items.md#rev-66-a-model-without-flow-is-refused-on-its-element-pair-before-its-flow-switch) |
| REV-67 | interface | low | deferred | §8.2.18 T3 | [Public registration functions for backend registries (MOD-11)](review-items.md#rev-67-public-registration-functions-for-backend-registries-mod-11) |
| REV-68 | verification | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [The spec still promises a refusal that D8 removed](review-items.md#rev-68-the-spec-still-promises-a-refusal-that-d8-removed) |
| REV-69 | verification | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [VER-67 defers its refusal texts to a plan](review-items.md#rev-69-ver-67-defers-its-refusal-texts-to-a-plan) |
| REV-70 | interface | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [WP40 D5 and D8 go beyond MOD-14's letter](review-items.md#rev-70-wp40-d5-and-d8-go-beyond-mod-14s-letter) |
| REV-71 | verification | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [Stage 10's cache key does not move when the solver's algorithm does](review-items.md#rev-71-stage-10s-cache-key-does-not-move-when-the-solvers-algorithm-does) |
| REV-72 | coupling | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [A supplied field's rule order travels beside its source as a second argument](review-items.md#rev-72-a-supplied-fields-rule-order-travels-beside-its-source-as-a-second-argument) |
| REV-73 | physics | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [Cross-leaf inertness is not checked](review-items.md#rev-73-cross-leaf-inertness-is-not-checked) |
| REV-74 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [An untested raise in the force extension carries a coverage pragma](review-items.md#rev-74-an-untested-raise-in-the-force-extension-carries-a-coverage-pragma) |
| REV-75 | coupling | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The two defaults modules duplicate the specs' defaults](review-items.md#rev-75-the-two-defaults-modules-duplicate-the-specs-defaults) |
| REV-76 | verification | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [`ModelDeclaration.unread` paths are not validated against the schema](review-items.md#rev-76-modeldeclarationunread-paths-are-not-validated-against-the-schema) |
| REV-77 | process | medium | fixed | [WP42](../plans/wp42-verification-checks.md) | [Pinning every artefact schema at v0.5 removes the cache-bust a payload change needs](review-items.md#rev-77-pinning-every-artefact-schema-at-v05-removes-the-cache-bust-a-payload-change-needs) |
| REV-78 | interface | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The threads flag re-lists the thread variables and writes the environment for good](review-items.md#rev-78-the-threads-flag-re-lists-the-thread-variables-and-writes-the-environment-for-good) |
| REV-79 | numerics | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The exclusion shell raises a bare ValueError for a NaN ring coordinate](review-items.md#rev-79-the-exclusion-shell-raises-a-bare-valueerror-for-a-nan-ring-coordinate) |
| REV-80 | performance | medium | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [A source change selects every process-starting test file, so the commit hook misses its 60 s budget](review-items.md#rev-80-a-source-change-selects-every-process-starting-test-file-so-the-commit-hook-misses-its-60-s-budget) |
| REV-81 | performance | low | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [Most past commits would fall back to the development selection](review-items.md#rev-81-most-past-commits-would-fall-back-to-the-development-selection) |
| REV-82 | performance | medium | fixed | [WP43](../plans/wp43-development-loop.md) | [The push gate takes over 9 minutes against its 5-minute budget](review-items.md#rev-82-the-push-gate-takes-over-9-minutes-against-its-5-minute-budget) |
| REV-83 | performance | low | fixed | [WP43](../plans/wp43-development-loop.md) | [The longest-first test order is inert under xdist file scheduling](review-items.md#rev-83-the-longest-first-test-order-is-inert-under-xdist-file-scheduling) |
| REV-84 | verification | medium | fixed | [WP43](../plans/wp43-development-loop.md) | [A Markdown file that a WP43 test reads is classed as prose, so its test does not run on a change to it](review-items.md#rev-84-a-markdown-file-that-a-wp43-test-reads-is-classed-as-prose-so-its-test-does-not-run-on-a-change-to-it) |
| REV-85 | process | low | fixed | [WP43](../plans/wp43-development-loop.md) | [tests/impact.py uses os.path against the coding conventions](review-items.md#rev-85-testsimpactpy-uses-ospath-against-the-coding-conventions) |
| REV-86 | process | low | fixed | [WP43](../plans/wp43-development-loop.md) | [ci.yml repeats the steps of the platforms job in the full-matrix job](review-items.md#rev-86-ciyml-repeats-the-steps-of-the-platforms-job-in-the-full-matrix-job) |
| REV-87 | process | low | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [The plan word cap counts the Outcome that /wp-implement appends](review-items.md#rev-87-the-plan-word-cap-counts-the-outcome-that-wp-implement-appends) |
| REV-88 | verification | medium | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [No check remains that the public API carries its docstrings](review-items.md#rev-88-no-check-remains-that-the-public-api-carries-its-docstrings) |
| REV-89 | verification | low | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [The shard partition test ignores collection errors and recollects the tree on every commit](review-items.md#rev-89-the-shard-partition-test-ignores-collection-errors-and-recollects-the-tree-on-every-commit) |
| REV-90 | documentation | low | fixed | [WP44](../plans/wp44-simplify-the-loop.md) | [VER-72 (d) and the planned-xfail logic guard a marker the workflow no longer writes](review-items.md#rev-90-ver-72-d-and-the-planned-xfail-logic-guard-a-marker-the-workflow-no-longer-writes) |
| REV-91 | documentation | low | deferred | §8.2.11 L10 | [About 400 tests name their requirement only in a comment](review-items.md#rev-91-about-400-tests-name-their-requirement-only-in-a-comment) |
| REV-92 | documentation | low | declined | §8.2.11 L10 | [src prose share is 10.6 %, above the 10 % prediction](review-items.md#rev-92-src-prose-share-is-106-above-the-10-prediction) |
| REV-93 | documentation | low | fixed | [WP45](../plans/wp45-prose-strip.md) | [VER-75 (a) says leading underscore; dunder methods count as public](review-items.md#rev-93-ver-75-a-says-leading-underscore-dunder-methods-count-as-public) |
| REV-94 | documentation | low | fixed | [WP45](../plans/wp45-prose-strip.md) | [47 public functions and methods carry no docstring, and nothing checks them](review-items.md#rev-94-47-public-functions-and-methods-carry-no-docstring-and-nothing-checks-them) |
| REV-95 | verification | low | fixed | [WP45](../plans/wp45-prose-strip.md) | [VER-75 (a) states a check on derivations and history that no test makes](review-items.md#rev-95-ver-75-a-states-a-check-on-derivations-and-history-that-no-test-makes) |
| REV-96 | documentation | low | fixed | [WP45](../plans/wp45-prose-strip.md) | [About 157 prose lines in src and tests still carry identifiers or plan history](review-items.md#rev-96-about-157-prose-lines-in-src-and-tests-still-carry-identifiers-or-plan-history) |
| REV-97 | verification | low | fixed | [WP45](../plans/wp45-prose-strip.md) | [A directive comment is defined twice, differently](review-items.md#rev-97-a-directive-comment-is-defined-twice-differently) |
| REV-98 | interface | medium | fixed | [WP46](../plans/wp46-small-fixes.md) | [The scratch directory is the workspace itself, where the specification says fresh per run](review-items.md#rev-98-the-scratch-directory-is-the-workspace-itself-where-the-specification-says-fresh-per-run) |
| REV-99 | coupling | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A put killed before the rename leaves a hidden staging directory nothing reclaims](review-items.md#rev-99-a-put-killed-before-the-rename-leaves-a-hidden-staging-directory-nothing-reclaims) |
| REV-100 | performance | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A put copies and hashes a payload before learning the key is already stored](review-items.md#rev-100-a-put-copies-and-hashes-a-payload-before-learning-the-key-is-already-stored) |
| REV-101 | numerics | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [A pre-WP46 charge-grid npz in a store is served under an unchanged key](review-items.md#rev-101-a-pre-wp46-charge-grid-npz-in-a-store-is-served-under-an-unchanged-key) |
| REV-102 | coupling | low | fixed | [WP46](../plans/wp46-small-fixes.md) | [frame_times reads a private MDAnalysis attribute](review-items.md#rev-102-frame_times-reads-a-private-mdanalysis-attribute) |
| REV-103 | verification | low | fixed | [WP48](../plans/wp48-okf-backfill.md) | [A verified-only claim outside the test-evidence concepts is not yet classed as executable arithmetic or a source reading](review-items.md#rev-103-a-verified-only-claim-outside-the-test-evidence-concepts-is-not-yet-classed-as-executable-arithmetic-or-a-source-reading) |
| REV-104 | verification | low | fixed | [WP47](../plans/wp47-okf-bundle.md) | [A correction file keeps a dead citation to the removed flat knowledge file](review-items.md#rev-104-a-correction-file-keeps-a-dead-citation-to-the-removed-flat-knowledge-file) |
| REV-105 | documentation | low | fixed | [WP47](../plans/wp47-okf-bundle.md) | [SPECIFICATION G12 (7) says the navigation is generated from the index files; the build has one static entry](review-items.md#rev-105-specification-g12-7-says-the-navigation-is-generated-from-the-index-files-the-build-has-one-static-entry) |
| REV-106 | verification | low | fixed | [WP47](../plans/wp47-okf-bundle.md) | [The heading-slug function differs from the table-of-contents slugger for emphasis, entities and images](review-items.md#rev-106-the-heading-slug-function-differs-from-the-table-of-contents-slugger-for-emphasis-entities-and-images) |
| REV-107 | documentation | low | fixed | [WP47](../plans/wp47-okf-bundle.md) | [About 40 log entries are fragments](review-items.md#rev-107-about-40-log-entries-are-fragments) |
| REV-108 | verification | medium | fixed | [WP48 plan amendment](../plans/wp48-okf-backfill.md) | [WP48 omitted sourced arithmetic from its audit](review-items.md#rev-108-wp48-omitted-sourced-arithmetic-from-its-audit) |
| REV-109 | verification | medium | fixed | [WP48 plan amendment](../plans/wp48-okf-backfill.md) | [WP48 omitted version metadata coverage and refusal checks](review-items.md#rev-109-wp48-omitted-version-metadata-coverage-and-refusal-checks) |
| REV-110 | verification | medium | fixed | [WP48 plan amendment](../plans/wp48-okf-backfill.md) | [WP48 lacked an evidence route for historical numerical experiments](review-items.md#rev-110-wp48-lacked-an-evidence-route-for-historical-numerical-experiments) |
| REV-111 | verification | low | open | — | [The no-MPI-symbols claim is backed only by the lock file](review-items.md#rev-111-the-no-mpi-symbols-claim-is-backed-only-by-the-lock-file) |
| REV-112 | performance | low | fixed | [WP49 plan](../plans/wp49-cost-study.md) | [Three suspected costs were never measured](review-items.md#rev-112-three-suspected-costs-were-never-measured) |
| REV-113 | interface | low | fixed | [WP49 plan](../plans/wp49-cost-study.md) | [The case schema has no JSON Schema export](review-items.md#rev-113-the-case-schema-has-no-json-schema-export) |
| REV-114 | interface | medium | fixed | §8.2.18 T5 | [The shell moves from Qt to a browser](review-items.md#rev-114-the-shell-moves-from-qt-to-a-browser) |
| REV-115 | process | low | declined | §8.2.12 M1 | [The architecture review's already-met claims](review-items.md#rev-115-the-architecture-reviews-already-met-claims) |
| REV-116 | verification | low | open | — | [The cost record predates the harness fixes](review-items.md#rev-116-the-cost-record-predates-the-harness-fixes) |
| REV-117 | process | low | fixed | — | [Tooling left without tests by the test scope](review-items.md#rev-117-tooling-left-without-tests-by-the-test-scope) |
| REV-118 | verification | medium | fixed | §8.2.13 N1 | [Gate and mechanism tests the pruning removed](review-items.md#rev-118-gate-and-mechanism-tests-the-pruning-removed) |
| REV-119 | verification | low | declined | [CODE_REVIEW_010](../code_reviews/CODE_REVIEW_010.md) | [The analyte benchmark meshes skip the quality gate](review-items.md#rev-119-the-analyte-benchmark-meshes-skip-the-quality-gate) |
| REV-120 | physics | medium | open | — | [The force-traction normal needs one material on the left along the whole surface](review-items.md#rev-120-the-force-traction-normal-needs-one-material-on-the-left-along-the-whole-surface) |
| REV-121 | interface | low | open | — | [Stage 1 checks no axis for a monomeric or hetero-oligomeric pore](review-items.md#rev-121-stage-1-checks-no-axis-for-a-monomeric-or-hetero-oligomeric-pore) |
| REV-122 | interface | low | open | — | [A case cannot load a correction file from outside the installed package](review-items.md#rev-122-a-case-cannot-load-a-correction-file-from-outside-the-installed-package) |
| REV-123 | interface | low | fixed | §8.2.14 P6 | [The library has no plotting helpers or notebook display](review-items.md#rev-123-the-library-has-no-plotting-helpers-or-notebook-display) |
| REV-124 | tooling | low | fixed | [CODE_REVIEW_013](../code_reviews/CODE_REVIEW_013.md) | [The specification's site navigation is listed by hand](review-items.md#rev-124-the-specifications-site-navigation-is-listed-by-hand) |
| REV-125 | process | low | fixed | [WP53](../plans/wp53-workflow-commands.md) | [The workflow files exceed the plan's word caps](review-items.md#rev-125-the-workflow-files-exceed-the-plans-word-caps) |
| REV-126 | process | medium | fixed | §8.2.17 S16 | [Package numbers can collide between the two lanes](review-items.md#rev-126-package-numbers-can-collide-between-the-two-lanes) |
| REV-127 | process | medium | fixed | §8.2.17 S17 | [WP57 may restate the Qt shell's gating clauses before v0.5.0](review-items.md#rev-127-wp57-may-restate-the-qt-shells-gating-clauses-before-v050) |
| REV-128 | process | low | fixed | §8.2.17 S18 | [The renumbering list leaves out other identifier kinds and the ruling letters](review-items.md#rev-128-the-renumbering-list-leaves-out-other-identifier-kinds-and-the-ruling-letters) |
| REV-129 | process | low | fixed | §8.2.17 S19 | [WP58's tag and the place of a held changelog entry are undefined](review-items.md#rev-129-wp58s-tag-and-the-place-of-a-held-changelog-entry-are-undefined) |
| REV-130 | process | medium | fixed | §8.2.17 S20 | [Nothing checks that identifiers stay unique after both lanes merge](review-items.md#rev-130-nothing-checks-that-identifiers-stay-unique-after-both-lanes-merge) |
| REV-131 | verification | medium | fixed | [Phase 5 plan](../plans/phase-5-workbench.md) | [The charge-level mutator has no library step or tier row](review-items.md#rev-131-the-charge-level-mutator-has-no-library-step-or-tier-row) |
| REV-132 | process | low | fixed | [Phase 5 plan](../plans/phase-5-workbench.md) | [The Phase 5 end-of-phase report names no source for its numbers](review-items.md#rev-132-the-phase-5-end-of-phase-report-names-no-source-for-its-numbers) |
| REV-133 | process | low | fixed | [CODE_REVIEW_015](../code_reviews/CODE_REVIEW_015.md) | [The Phase 5 plan and the core exceed their word caps](review-items.md#rev-133-the-phase-5-plan-and-the-core-exceed-their-word-caps) |
| REV-134 | interface | medium | deferred | §8.2.19 U1 | [The Qt shell's Result tab prints the stored float wrapper, not the number](review-items.md#rev-134-the-qt-shells-result-tab-prints-the-stored-float-wrapper-not-the-number) |
| REV-135 | physics | medium | accepted | §8.2.19 U2 | [The density does not see the protonation chosen at the charge stage](review-items.md#rev-135-the-density-does-not-see-the-protonation-chosen-at-the-charge-stage) |
| REV-136 | coupling | medium | accepted | §8.2.19 U3 | [The organisation round's rulings need library capabilities v0.5 lacks](review-items.md#rev-136-the-organisation-rounds-rulings-need-library-capabilities-v05-lacks) |
| REV-137 | interface | medium | accepted | §8.2.19 U5 | [No renderer is chosen for the molecule in 3D or for the explorer's controls](review-items.md#rev-137-no-renderer-is-chosen-for-the-molecule-in-3d-or-for-the-explorers-controls) |
| REV-138 | verification | medium | accepted | §8.2.19 U5 | [The render check measures text contrast but not the contrast of controls and graphics](review-items.md#rev-138-the-render-check-measures-text-contrast-but-not-the-contrast-of-controls-and-graphics) |
| REV-139 | interface | medium | accepted | §8.2.19 U4 | [The sweep needs a design round: any value, user-defined variables, rebuilds detected](review-items.md#rev-139-the-sweep-needs-a-design-round-any-value-user-defined-variables-rebuilds-detected) |
| REV-140 | interface | low | fixed | §8.2.18 T6, T7 | [Two of the author's marks on the mockups ask what is not yet said](review-items.md#rev-140-two-of-the-authors-marks-on-the-mockups-ask-what-is-not-yet-said) |
| REV-141 | coupling | medium | accepted | §8.2.19 U5 | [CON-08 and CON-11 name a bundle and a desktop path the browser shell removes](review-items.md#rev-141-con-08-and-con-11-name-a-bundle-and-a-desktop-path-the-browser-shell-removes) |
| REV-142 | interface | medium | fixed | §8.2.19 U6 | [FR-38 drops the charge and radius edits of the charge-level mutator](review-items.md#rev-142-fr-38-drops-the-charge-and-radius-edits-of-the-charge-level-mutator) |
| REV-143 | interface | low | accepted | §8.2.19 U7 | [The light theme's control edge is under 3:1 on a selected row](review-items.md#rev-143-the-light-themes-control-edge-is-under-31-on-a-selected-row) |
| REV-144 | interface | low | deferred | §8.2.20 V3 | [Case.cylinder takes a charge field, not a uniform wall surface charge](review-items.md#rev-144-casecylinder-takes-a-charge-field-not-a-uniform-wall-surface-charge) |
| REV-145 | interface | low | deferred | §8.2.20 V3 | [No case builders by section before Phase 5](review-items.md#rev-145-no-case-builders-by-section-before-phase-5) |
| REV-146 | numerics | high | fixed | §8.2.20 V9 | [The cylinder's default wall size is coarser than NUM-30's first layer](review-items.md#rev-146-the-cylinders-default-wall-size-is-coarser-than-num-30s-first-layer) |
| REV-147 | interface | low | fixed | §8.2.20 V16 | [The lumen window is fixed, not read from the region](review-items.md#rev-147-the-lumen-window-is-fixed-not-read-from-the-region) |
| REV-148 | physics | low | fixed | §8.2.20 V16 | [A concentration panel's bulk is the case's salt for every species](review-items.md#rev-148-a-concentration-panels-bulk-is-the-cases-salt-for-every-species) |
| REV-149 | interface | low | deferred | §8.2.20 V13 | [Notebook 01 prepares a structure but does not change its residues](review-items.md#rev-149-notebook-01-prepares-a-structure-but-does-not-change-its-residues) |
| REV-150 | numerics | medium | fixed | §8.2.20 V14 | [`wall_h_nm="debye"` is not capped at NUM-30's 0.05 nm ceiling](review-items.md#rev-150-wall_h_nmdebye-is-not-capped-at-num-30s-005-nm-ceiling) |
| REV-151 | physics | low | deferred | §8.2.20 V15 | [`orient_pore` centres laterally on the registration residues, not on the pore axis](review-items.md#rev-151-orient_pore-centres-laterally-on-the-registration-residues-not-on-the-pore-axis) |
| REV-152 | interface | low | fixed | §8.2.20 V17 | [WP54 review items: cache key, restores, duplicated helpers, edge cases](review-items.md#rev-152-wp54-review-items-cache-key-restores-duplicated-helpers-edge-cases) |
| REV-153 | interface | low | open | — | [Latent gaps the second WP54 review left: the bulk's source, the Debye length twice, two hand-kept lists](review-items.md#rev-153-latent-gaps-the-second-wp54-review-left-the-bulks-source-the-debye-length-twice-two-hand-kept-lists) |
| REV-154 | numerics | low | open | — | [NUM-34's refusal names a setting that a supplied mesh ignores](review-items.md#rev-154-num-34s-refusal-names-a-setting-that-a-supplied-mesh-ignores) |
