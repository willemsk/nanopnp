---
findings:
  prefix: MOD
  status: open
  areas: [stages, coupling, extension, surface]
---

# Modularity findings

The findings log of the [modularity report](modularity.md) (§8.2.7 G1, G4). Each row is one
finding; its section in the report gives what was measured, the consequence, the recommendation
and whether a fix is visible to users. The author ruled `MOD-01` to `MOD-17` on 5 October 2026 and `MOD-18` on 6 October (§8.2.8), and a row moves to `fixed` in the commit
that fixes it.

**Status** is `open` until ruled; then `accepted` (to be fixed in this phase), `fixed` (the ruling
links the plan that fixed it), or `deferred`, `post-1.0` or `declined` (the ruling names the §8.2
row). **Severity** is `high` for a SHALL the code does not meet, `medium` for a property held only
by convention or an extension needing an edit outside its home, and `low` for size or tidiness.
`tests/tier1/test_findings_logs.py` checks every row (VER-63), and once the header says `closed` it
refuses any row that is not terminal.

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
| MOD-01 | stages | high | fixed | [WP36](../plans/wp36-stage-protocol-and-walk.md) | [Two stages have no key, and the protocol declares none](modularity.md#mod-01-two-stages-have-no-key-and-the-protocol-declares-none) |
| MOD-02 | stages | medium | fixed | [WP36](../plans/wp36-stage-protocol-and-walk.md) | [The walk holds what the stages should declare](modularity.md#mod-02-the-walk-holds-what-the-stages-should-declare) |
| MOD-03 | coupling | medium | accepted | §8.2.8 H6 | [Ten subpackages form one import cycle](modularity.md#mod-03-ten-subpackages-form-one-import-cycle) |
| MOD-04 | coupling | medium | accepted | §8.2.8 H6 | [io is both the base layer and the assembler](modularity.md#mod-04-io-is-both-the-base-layer-and-the-assembler) |
| MOD-05 | coupling | low | fixed | [WP37](../plans/wp37-cycle-cuts-exit-codes-backend-guard.md) | [The exit-code table lives in the shell and the library imports it](modularity.md#mod-05-the-exit-code-table-lives-in-the-shell-and-the-library-imports-it) |
| MOD-06 | extension | medium | accepted | §8.2.8 H7 | [The mesher is a branch, not a registry](modularity.md#mod-06-the-mesher-is-a-branch-not-a-registry) |
| MOD-07 | extension | medium | accepted | §8.2.8 H7 | [The linear solver is a branch, and the schema reads its list](modularity.md#mod-07-the-linear-solver-is-a-branch-and-the-schema-reads-its-list) |
| MOD-08 | extension | low | post-1.0 | §8.2.8 H5 | [Five registries in four shapes](modularity.md#mod-08-five-registries-in-four-shapes) |
| MOD-09 | extension | low | deferred | §8.2.8 H4 | [Outputs and steric models are closed enumerations in the assembler](modularity.md#mod-09-outputs-and-steric-models-are-closed-enumerations-in-the-assembler) |
| MOD-10 | extension | high | deferred | §8.2.8 H3 | [The backend interface of section 5.4.1 does not exist](modularity.md#mod-10-the-backend-interface-of-section-541-does-not-exist) |
| MOD-11 | surface | low | accepted | §8.2.8 H2 | [with_section and register are outside PUBLIC](modularity.md#mod-11-with_section-and-register-are-outside-public) |
| MOD-12 | surface | low | fixed | [WP36](../plans/wp36-stage-protocol-and-walk.md) | [PUBLIC is mirrored by hand for the type checker](modularity.md#mod-12-public-is-mirrored-by-hand-for-the-type-checker) |
| MOD-13 | surface | low | accepted | §8.2.8 H1 | [Three modules and two functions are past review size](modularity.md#mod-13-three-modules-and-two-functions-are-past-review-size) |
| MOD-14 | surface | medium | accepted | §8.2.8 H1 | [Refusals name releases that have shipped](modularity.md#mod-14-refusals-name-releases-that-have-shipped) |
| MOD-15 | coupling | low | accepted | §8.2.8 H1 | [core reaches upward, once by an annotation and into ten subpackages by the registry](modularity.md#mod-15-core-reaches-upward-once-by-an-annotation-and-into-ten-subpackages-by-the-registry) |
| MOD-16 | extension | medium | accepted | §8.2.8 H7 | [The stabilisation registry is closed by a Literal in the schema](modularity.md#mod-16-the-stabilisation-registry-is-closed-by-a-literal-in-the-schema) |
| MOD-17 | extension | low | post-1.0 | §8.2.8 H5 | [The validated correction set is a default in eight signatures](modularity.md#mod-17-the-validated-correction-set-is-a-default-in-eight-signatures) |
| MOD-18 | extension | low | deferred | §8.2.8 H10 | [The Geometry tab has a view only for the stages it knows](modularity.md#mod-18-the-geometry-tab-has-a-view-only-for-the-stages-it-knows) |
