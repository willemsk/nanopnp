---
findings:
  prefix: MOD
  status: open
  areas: [stages, coupling, extension, surface]
---

# Modularity findings

The findings log of the [modularity report](modularity.md) (§8.2.7 G1, G4). Each row is one
finding; its section in the report gives what was measured, the consequence, the recommendation
and whether a fix is visible to users. The author rules every row through `/phase-plan amend 4`.

**Status** is `open` until ruled; then `accepted` (to be fixed in this phase), `fixed` (the ruling
links the plan that fixed it), or `deferred`, `post-1.0` or `declined` (the ruling names the §8.2
row). **Severity** is `high` for a SHALL the code does not meet, `medium` for a property held only
by convention or an extension needing an edit outside its home, and `low` for size or tidiness.
`tests/tier1/test_findings_logs.py` checks every row (VER-63), and once the header says `closed` it
refuses any row that is not terminal.

| ID | Area | Severity | Status | Ruling | Finding |
|---|---|---|---|---|---|
| MOD-01 | stages | high | open | — | [Two stages have no key, and the protocol declares none](modularity.md#mod-01-two-stages-have-no-key-and-the-protocol-declares-none) |
| MOD-02 | stages | medium | open | — | [The walk holds what the stages should declare](modularity.md#mod-02-the-walk-holds-what-the-stages-should-declare) |
| MOD-03 | coupling | medium | open | — | [Ten subpackages form one import cycle](modularity.md#mod-03-ten-subpackages-form-one-import-cycle) |
| MOD-04 | coupling | medium | open | — | [io is both the base layer and the assembler](modularity.md#mod-04-io-is-both-the-base-layer-and-the-assembler) |
| MOD-05 | coupling | low | open | — | [The exit-code table lives in the shell and the library imports it](modularity.md#mod-05-the-exit-code-table-lives-in-the-shell-and-the-library-imports-it) |
| MOD-06 | extension | medium | open | — | [The mesher is a branch, not a registry](modularity.md#mod-06-the-mesher-is-a-branch-not-a-registry) |
| MOD-07 | extension | medium | open | — | [The linear solver is a branch, and the schema reads its list](modularity.md#mod-07-the-linear-solver-is-a-branch-and-the-schema-reads-its-list) |
| MOD-08 | extension | low | open | — | [Five registries in four shapes](modularity.md#mod-08-five-registries-in-four-shapes) |
| MOD-09 | extension | low | open | — | [Outputs and steric models are closed enumerations in the assembler](modularity.md#mod-09-outputs-and-steric-models-are-closed-enumerations-in-the-assembler) |
| MOD-10 | extension | high | open | — | [The backend interface of section 5.4.1 does not exist](modularity.md#mod-10-the-backend-interface-of-section-541-does-not-exist) |
| MOD-11 | surface | low | open | — | [with_section and register are outside PUBLIC](modularity.md#mod-11-with_section-and-register-are-outside-public) |
| MOD-12 | surface | low | open | — | [PUBLIC is mirrored by hand for the type checker](modularity.md#mod-12-public-is-mirrored-by-hand-for-the-type-checker) |
| MOD-13 | surface | low | open | — | [Three modules and two functions are past review size](modularity.md#mod-13-three-modules-and-two-functions-are-past-review-size) |
| MOD-14 | surface | medium | open | — | [Refusals name releases that have shipped](modularity.md#mod-14-refusals-name-releases-that-have-shipped) |
| MOD-15 | coupling | low | open | — | [core reaches upward, once by an annotation and into ten subpackages by the registry](modularity.md#mod-15-core-reaches-upward-once-by-an-annotation-and-into-ten-subpackages-by-the-registry) |
| MOD-16 | extension | medium | open | — | [The stabilisation registry is closed by a Literal in the schema](modularity.md#mod-16-the-stabilisation-registry-is-closed-by-a-literal-in-the-schema) |
| MOD-17 | extension | low | open | — | [The validated correction set is a default in eight signatures](modularity.md#mod-17-the-validated-correction-set-is-a-default-in-eight-signatures) |
