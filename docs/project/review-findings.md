---
findings:
  prefix: REV
  status: open
  areas: [coupling, performance, verification, documentation, physics, numerics, interface, process]
---

# Review findings

The log of [the review register](review-items.md) (§8.2.8 H12): every item a work package's
implementation or review left open, until it is resolved. `/wp-implement` and `/wp-ship` add a row
in the commit that leaves an item open, and the commit that resolves it sets the row `fixed`, its
ruling linking the plan that fixed it.

**Status** is `open` until the author rules; then `accepted` (owned by a named later package),
`fixed`, or `deferred`, `post-1.0` or `declined` (the ruling names the §8.2 row). **Severity** is
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
| REV-14 | numerics | low | accepted | §8.2.9 I2 | [A radial grid's .npz does not round-trip its spacing exactly](review-items.md#rev-14-a-radial-grids-npz-does-not-round-trip-its-spacing-exactly) |
| REV-15 | interface | low | accepted | §8.2.9 I2 | [Example 05 quotes #SBATCH directives as shell words](review-items.md#rev-15-example-05-quotes-sbatch-directives-as-shell-words) |
| REV-16 | performance | low | accepted | §8.2.9 I2 | [A salt sweep regenerates an identical mesh at each concentration](review-items.md#rev-16-a-salt-sweep-regenerates-an-identical-mesh-at-each-concentration) |
| REV-17 | numerics | low | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [A warm start is gated on free prose in the stabilisation provenance](review-items.md#rev-17-a-warm-start-is-gated-on-free-prose-in-the-stabilisation-provenance) |
| REV-18 | interface | low | accepted | §8.2.9 I2 | [Concurrent sweep members may write the same store key](review-items.md#rev-18-concurrent-sweep-members-may-write-the-same-store-key) |
| REV-19 | interface | low | accepted | §8.2.9 I2 | [A zero-frame trajectory raises a bare IndexError](review-items.md#rev-19-a-zero-frame-trajectory-raises-a-bare-indexerror) |
| REV-20 | process | low | deferred | §8.2.8 H12 | [The desktop shell has no multiprocessing.freeze_support](review-items.md#rev-20-the-desktop-shell-has-no-multiprocessingfreeze_support) |
| REV-21 | process | low | declined | §8.2.8 H12 | [numerics/linear.py imports scipy inside its functions](review-items.md#rev-21-numericslinearpy-imports-scipy-inside-its-functions) |
| REV-22 | process | low | declined | §8.2.8 H12 | [write_dx formats with %](review-items.md#rev-22-write_dx-formats-with) |
| REV-23 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The corrections test bounds both ions by one range](review-items.md#rev-23-the-corrections-test-bounds-both-ions-by-one-range) |
| REV-24 | process | low | accepted | §8.2.9 I2 | [Sampler construction may still be duplicated](review-items.md#rev-24-sampler-construction-may-still-be-duplicated) |
| REV-25 | interface | low | accepted | §8.2.9 I2 | [A post stage run without a solve writes scratch to the default store](review-items.md#rev-25-a-post-stage-run-without-a-solve-writes-scratch-to-the-default-store) |
| REV-26 | interface | low | fixed | [WP41](../plans/wp41-accuracy-fixes.md) | [stabilisation_parameters returns an empty mapping off the coupled model](review-items.md#rev-26-stabilisation_parameters-returns-an-empty-mapping-off-the-coupled-model) |
| REV-27 | interface | low | fixed | [WP38](../plans/wp38-io-split.md) | [The inf-sup check ran at resolve, not at validation](review-items.md#rev-27-the-inf-sup-check-ran-at-resolve-not-at-validation) |
| REV-28 | performance | low | deferred | §8.2.9 I3 | [The viewer renders every finished run eagerly](review-items.md#rev-28-the-viewer-renders-every-finished-run-eagerly) |
| REV-29 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The cylindrical-pore fixture is copied into four test modules](review-items.md#rev-29-the-cylindrical-pore-fixture-is-copied-into-four-test-modules) |
| REV-30 | performance | low | deferred | §8.2.9 I3 | [The viewer's scene is written twice](review-items.md#rev-30-the-viewers-scene-is-written-twice) |
| REV-31 | documentation | low | deferred | §8.2.9 I3 | [The bundle's size is not recorded](review-items.md#rev-31-the-bundles-size-is-not-recorded) |
| REV-32 | interface | low | deferred | §8.2.9 I3 | [Old store entries are neither migrated nor removed](review-items.md#rev-32-old-store-entries-are-neither-migrated-nor-removed) |
| REV-33 | interface | low | declined | §8.2.9 I3 | [writable_formats assumes the extra's floor](review-items.md#rev-33-writable_formats-assumes-the-extras-floor) |
| REV-34 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [Two reference tests duplicate the frozen case](review-items.md#rev-34-two-reference-tests-duplicate-the-frozen-case) |
| REV-35 | performance | low | post-1.0 | §8.2.9 I3 | [_second_crossings loops in Python](review-items.md#rev-35-_second_crossings-loops-in-python) |
| REV-36 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [The gmsh session stops a caller's logger](review-items.md#rev-36-the-gmsh-session-stops-a-callers-logger) |
| REV-37 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [A broken gmsh wheel is not a refusal](review-items.md#rev-37-a-broken-gmsh-wheel-is-not-a-refusal) |
| REV-38 | interface | low | fixed | [WP39](../plans/wp39-backend-registries.md) | [gmsh.model.remove() can mask the error it follows](review-items.md#rev-38-gmshmodelremove-can-mask-the-error-it-follows) |
| REV-39 | interface | low | deferred | §8.2.9 I3 | [A case supplying inputs.profile gets no contour editor](review-items.md#rev-39-a-case-supplying-inputsprofile-gets-no-contour-editor) |
| REV-40 | interface | low | accepted | §8.2.9 I2 | [DensityMap.read accepts a file written in nm](review-items.md#rev-40-densitymapread-accepts-a-file-written-in-nm) |
| REV-41 | interface | low | deferred | §8.2.9 I3 | [No prepare command, upto on reproduce, or region export](review-items.md#rev-41-no-prepare-command-upto-on-reproduce-or-region-export) |
| REV-42 | interface | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [pnp carries inert flow keys](review-items.md#rev-42-pnp-carries-inert-flow-keys) |
| REV-43 | process | low | accepted | §8.2.9 I2 | [chain_characters duplicates the export's mapping](review-items.md#rev-43-chain_characters-duplicates-the-exports-mapping) |
| REV-44 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The Stern-layer test re-solves the drawn slab](review-items.md#rev-44-the-stern-layer-test-re-solves-the-drawn-slab) |
| REV-45 | interface | low | deferred | §8.2.9 I3 | [The derived χ field has no export](review-items.md#rev-45-the-derived-field-has-no-export) |
| REV-46 | verification | low | deferred | §8.2.9 I3 | [Example 07 is not run at default sizes or on the ensemble](review-items.md#rev-46-example-07-is-not-run-at-default-sizes-or-on-the-ensemble) |
| REV-47 | process | low | accepted | §8.2.9 I3 | [The test-duration targets are missed](review-items.md#rev-47-the-test-duration-targets-are-missed) |
| REV-48 | verification | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [The 2WCD walk test copies its constants](review-items.md#rev-48-the-2wcd-walk-test-copies-its-constants) |
| REV-49 | process | low | accepted | §8.2.9 I2 | [AXISYMMETRIC is replaced repeatedly](review-items.md#rev-49-axisymmetric-is-replaced-repeatedly) |
| REV-50 | process | low | accepted | §8.2.9 I2 | [_inner_wall_nm re-implements innermost_crossings](review-items.md#rev-50-_inner_wall_nm-re-implements-innermost_crossings) |
| REV-51 | performance | low | accepted | §8.2.9 I2 | [A redundant reopen and resolve in WP34's walk](review-items.md#rev-51-a-redundant-reopen-and-resolve-in-wp34s-walk) |
| REV-52 | interface | low | deferred | §8.2.9 I3 | [deviations and SolveReporting are off the stage protocol](review-items.md#rev-52-deviations-and-solvereporting-are-off-the-stage-protocol) |
| REV-53 | interface | low | declined | §8.2.9 I3 | [Some walk rules stay as case logic](review-items.md#rev-53-some-walk-rules-stay-as-case-logic) |
| REV-54 | verification | low | fixed | [WP38](../plans/wp38-io-split.md) | [The MOD-12 check compared names, not modules](review-items.md#rev-54-the-mod-12-check-compared-names-not-modules) |
| REV-55 | interface | low | accepted | §8.2.9 I2 | [Per-stage mkdtemp fallbacks](review-items.md#rev-55-per-stage-mkdtemp-fallbacks) |
| REV-56 | performance | low | deferred | §8.2.9 I3 | [The geometry editor's simplicity check runs on the Qt thread](review-items.md#rev-56-the-geometry-editors-simplicity-check-runs-on-the-qt-thread) |
| REV-57 | performance | low | accepted | §8.2.9 I2 | [frame_times decodes every frame](review-items.md#rev-57-frame_times-decodes-every-frame) |
| REV-58 | performance | low | post-1.0 | §8.2.9 I3 | [The azimuthal reduction projects cells it then drops](review-items.md#rev-58-the-azimuthal-reduction-projects-cells-it-then-drops) |
| REV-59 | interface | low | accepted | §8.2.9 I2 | [attribute_to_construction raises the wrong error on a lax comparison](review-items.md#rev-59-attribute_to_construction-raises-the-wrong-error-on-a-lax-comparison) |
| REV-60 | performance | low | deferred | §8.2.9 I3 | [UMFPACK repeats its symbolic analysis every Newton step](review-items.md#rev-60-umfpack-repeats-its-symbolic-analysis-every-newton-step) |
| REV-61 | interface | low | deferred | §8.2.9 I3 | [No B-spline fit or HOLE cross-check of the contour](review-items.md#rev-61-no-b-spline-fit-or-hole-cross-check-of-the-contour) |
| REV-62 | interface | low | deferred | §8.2.9 I3 | [A mesh named by store key is refused](review-items.md#rev-62-a-mesh-named-by-store-key-is-refused) |
| REV-63 | performance | low | fixed | [WP38](../plans/wp38-io-split.md) | [The protonation stage walked through meshing](review-items.md#rev-63-the-protonation-stage-walked-through-meshing) |
| REV-64 | verification | low | deferred | §8.2.9 I3 | [A sweep's plan-time NUM-34 gate skips generated meshes](review-items.md#rev-64-a-sweeps-plan-time-num-34-gate-skips-generated-meshes) |
| REV-65 | interface | low | deferred | §8.2.9 I3 | [The Windows bundle exposes no mesh command](review-items.md#rev-65-the-windows-bundle-exposes-no-mesh-command) |
| REV-66 | interface | low | fixed | [WP42](../plans/wp42-verification-checks.md) | [A model without flow is refused on its element pair before its flow switch](review-items.md#rev-66-a-model-without-flow-is-refused-on-its-element-pair-before-its-flow-switch) |
| REV-67 | interface | low | deferred | §8.2.8 H2 | [Public registration functions for backend registries (MOD-11)](review-items.md#rev-67-public-registration-functions-for-backend-registries-mod-11) |
| REV-68 | verification | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [The spec still promises a refusal that D8 removed](review-items.md#rev-68-the-spec-still-promises-a-refusal-that-d8-removed) |
| REV-69 | verification | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [VER-67 defers its refusal texts to a plan](review-items.md#rev-69-ver-67-defers-its-refusal-texts-to-a-plan) |
| REV-70 | interface | low | fixed | [WP40](../plans/wp40-stale-refusals.md) | [WP40 D5 and D8 go beyond MOD-14's letter](review-items.md#rev-70-wp40-d5-and-d8-go-beyond-mod-14s-letter) |
| REV-71 | verification | medium | open | — | [Stage 10's cache key does not move when the solver's algorithm does](review-items.md#rev-71-stage-10s-cache-key-does-not-move-when-the-solvers-algorithm-does) |
| REV-72 | coupling | low | open | — | [A supplied field's rule order travels beside its source as a second argument](review-items.md#rev-72-a-supplied-fields-rule-order-travels-beside-its-source-as-a-second-argument) |
| REV-73 | physics | low | open | — | [Cross-leaf inertness is not checked](review-items.md#rev-73-cross-leaf-inertness-is-not-checked) |
