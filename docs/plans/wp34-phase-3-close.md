# WP34 — Phase 3 closed: the open items resolved, and the end-of-phase report

**Status: delivered, 3 October 2026.** Written 3 October 2026, after WP33 merged (`main` at `4375797`,
tagged `v0.4.0-alpha.8`). WP34 inherits everything the [current brief](current.md) lists as not to
be re-decided, and in particular:

- the stage-7 key chain: `structure` key → `ProtonationStage._key` → `charge_grid_key` (WP27 D10,
  WP28 D7), each a recipe hash computable without running a stage (`io/artefact.py` `Artefact.hash`);
- `case_identity` and its `DISCRETISATION_KEYS` rule (`validation/comsol.py`; VAL-03);
- the seeds and `Seed2WCD` of `tests/conftest.py` and the §7.6 NOTE's four levers (WP33).

This is the last work package of the [Phase 3 plan](phase-3-charge-pipeline.md). `SPECIFICATION.md`
governs, and identifiers below are pointers into it. **Spec amendment, made in this commit:** the
new §8.2.5, rulings E1–E5 by the author on 3 October 2026. It renumbers Phase 4's release to v0.5
throughout (§2.7, §3, QR-02, QR-15, §7.4, §8.1, §8.3 and Appendix A), records E3's representation in
§10 OPN-07, and opens OPN-08.

## Execution brief

### Scope

The author asked for one last package to resolve Phase 3's remaining open items. It carries five of
them, plus the phase close:

1. **OPN-07.** A golden's `case_hash` ignores a charge that stage 7 deposits, and a `χ` that it
   derives (E3).
2. **NUM-07 / WP28 D13.** The coupled models integrate their `r`-weighted forms one order short.
   WP34 measures this and records it; Phase 4 decides (E4).
3. **`with_section` in `nanopnp.PUBLIC`.** Parked by WP31.
4. **Phase 4 is v0.5 (E2).** The repository is relabelled outside the specification, the stray
   retired tag is deleted, and the renumbering script is retired.
5. **The end-of-phase report**, written on the Tier 1–2 evidence (E1), and `v0.4.0` (E5).

Discharges VAL-03 (for a deposited charge), and closes OPN-07. Touches NUM-07, VER-45 (the public
surface), and the phase criteria of the Phase 3 plan. No new identifier. **The brief is about 1,350 words, over
its 1,200 target**, because it carries five unrelated items, and each needs its own decision.

### Pointers

| Need | Read |
|---|---|
| OPN-07's evidence and constraints | §10 OPN-07; WP28 Outcomes, review finding #7 |
| The identity | `validation/comsol.py` `case_identity`, `DISCRETISATION_KEYS`; `charge/stage.py` `charge_grid_key`, `derived_parameters`; `charge/protonation.py` `_key` |
| NUM-07 | §6 NUM-07 and its NOTE on the `r` weight; `physics/measures.py`; WP28 D13 |
| Versioning | §2.7 Versioning NOTE; §8.2.5 E2; `.github/renumbered-tags.txt`; `CONTRIBUTING.md` *Versions and releases* |
| The report's numbers | The Phase 3 plan's *End-of-phase report*; the Outcomes of WP27–WP32 |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | What represents a deposited charge | A new record key `deposited_charge`, present only when `resolved.deposits_charge`, holding `{"protonation": <protonation key hash>, "kernel": <kernel_parameters without grid_spacing_nm>}`, so the kernel id, `sharpness`, `patch_half_widths` and `frame_shift_nm`. The protonation key is built from the structure stage's **key**, or from the `inputs.pqr` digest, exactly as `ProtonationStage._key` builds it | E3. The recipe is what the stage-7 artefact's hash already carries (§5.3.2). It needs no run. [Design §1](#1-what-the-identity-takes-from-stage-7) |
| D2 | What is left out | `smearing.grid_spacing_nm` and the deposit's element order | They are discretisation. They converge, and a golden answers the case at every rung (`DISCRETISATION_KEYS`) |
| D3 | A derived `χ` | A key `derived_eps_r`, present only when `resolved.derives_eps_r`, holding `derived_parameters(resolved)` and the structure key's hash. The geometry recipe (density, contour) stays out, like the mesh | E3. §7.4 leaves the mesh out deliberately, so leaving out the recipe that makes it is the same rule one level up. Close call, [Design §1](#1-what-the-identity-takes-from-stage-7) |
| D4 | Non-producer cases | Their record is byte-identical, and `CASE_IDENTITY_SCHEMA` stays `nanopnp/golden/case/v1` | OPN-07's constraint. `tests/tier1/data/case_v1/record.py` pins the existing identities |
| D5 | `fields.charge` | Unchanged. It still means "supplied", and no solve key moves | OPN-07's constraint |
| D6 | The cost of the identity | It hashes the structure files' contents through the stage-1 key, and is measured on example 06 and recorded in the docstring | It replaces the "about 1.6 s" note with the producer path's own number |
| D7 | NUM-07's measurement seam | `Measures` gains `weight_extra_order: int = 0`, which is added to the bonus of every non-singular axisymmetric `volume` and `surface` term. No case key, model option or CLI flag reaches it | E4. The measurement must not ship a switch, and at 0 the path is unchanged: VER-23's constants and every stage key stay fixed |
| D8 | What NUM-07 measures | (a) VER-18's coupled MMS on its three levels, with L² errors at 0 and +1. (b) Example 05's frozen ClyA case at 0 and +1: the current, `G`, `t₊` and the in-pore averages of VAL-17's list. Both are `slow`, logged and never gated | (a) localises the effect to the quadrature, against an exact solution. (b) is the size of it on the case VAL-16 will judge. [Design §2](#2-num-07-the-measurement) |
| D9 | `with_section` | **Not added** to `nanopnp.PUBLIC`. A comment in `test_public_api.py` records the decision | It is an editor affordance over a frozen schema. It changes no resolved case (WP31 D13), and adding it later costs nothing, whereas withdrawing it would break callers |
| D10 | The renumbering script | `.github/scripts/renumber-tags.sh` is deleted, and the mapping file's header says the script ran once on 30 September 2026 and is gone | Re-run after Phase 4 tags `v0.5.0-alpha.1`, it would retire live tags. The mapping stays for `release.yml` and for reading old manifests (E2) |
| D11 | The stray tag | `git push origin :refs/tags/v0.5.0-alpha.5`, after confirming it resolves to `v0.2.0-alpha.5`'s commit, `5abcf42`. Confirm with the author before pushing | E2. Deleting a remote tag is outward-facing |
| D12 | Relabelling outside the specification | "v1.0" becomes "v0.5" wherever it means Phase 4's release, and stays wherever it means the stable release (IF-01's "before v1.0") or the backlog ("post-1.0"). CHANGELOG sections already released are history and stay | E2. The inventory is in [Design §3](#3-the-relabel-inventory) |
| D13 | The report's evidence | Each number is read from a test that asserts or logs it on WP34's tree, never copied forward from an Outcome without being re-run. The waived Tier-3 numbers are listed as carried to Phase 4 (E1) | The memory rule: a run cut short is not evidence. The report names numbers, not adjectives |
| D14 | Release | WP34's `CHANGELOG.md` section is `v0.4.0`, and `CITATION.cff` names `0.4.0` with its date. After merge, the last commit on `main` is tagged `v0.4.0` alone (E5) | `CONTRIBUTING.md` *Versions and releases*; `release.yml`'s CITATION check |

### Work items

1. `validation/comsol.py`: `deposited_charge` and `derived_eps_r` (D1–D6). Build the keys through
   the stages' own key functions, never by re-deriving them. Read [Design §1](#1-what-the-identity-takes-from-stage-7)
   first.
2. §10 OPN-07 is marked **Closed** with the commit, and the VAL-03 text gains a sentence on a
   deposited charge.
3. `physics/measures.py` `weight_extra_order` (D7), with the slow measurement test (D8). Then the
   numbers go into the NUM-07 NOTE, beside the capacitor's 0.38 `V_T`, as **[tested]** in
   `.knowledge/06` §2.
4. `tests/tier1/test_public_api.py`: the D9 comment.
5. The relabel (D12), the script's removal (D10) and the tag (D11).
6. The phase plan: its status, the WP34 entry, the open-decisions rows (OPN-07 closed, NUM-07
   carried, versioning amended), the verification criteria with E1's waiver, and the
   **End-of-phase report** (D13). Then `current.md` points at Phase 4.
7. `CHANGELOG.md` `v0.4.0` and `CITATION.cff` (D14).

### Verification

| Test | Tier | Identifier | Assertion | Command |
|---|---|---|---|---|
| `tier1/test_validation_identity.py` (new) | 1 | VAL-03 | `test_val03_case_identity_names_a_deposited_charge`: on `examples/06-pdb-to-mesh/2wcd.case.yaml`, pH 5, 7.5 and 9 and `sharpness` 0.8 give four distinct hashes. This fails on `main`, where all four are `8559ee13…`. `grid_spacing_nm` and `numerics.elements.phi` leave the hash unchanged. Two different PQRs differ, and a moved copy of the same PQR does not. `dielectric_transition_nm` moves a deriving case's hash | `uv run pytest tests/tier1/test_validation_identity.py` |
| same file | 1 | VAL-03, VER-23 | Every solve key and stage-7 key of example 06 is unchanged, and `fields.charge` is `False` | same |
| `tier1/data/case_v1/record.py` (existing) | 1 | VAL-03 | Non-producer identities are byte-identical (D4) | `uv run pytest tests/tier1` |
| `tier2/test_axis_weight_order.py` (new, `slow`) | 2 | NUM-07 | Logs D8's (a) and (b). It asserts only that at 0 it reproduces VER-18's errors and example 05's identity | `uv run pytest tests/tier2/test_axis_weight_order.py -m slow --log-cli-level=INFO` |
| `tier1/test_public_api.py` | 1 | VER-45 | Unchanged set | `uv run pytest tests/tier1/test_public_api.py` |
| the docs build | — | VER-45, VER-46 | Strict build with the amended specification | the `CLAUDE.md` docs command |
| the whole gate | 1, 2 | all | Green, `--extended` | `.claude/hooks/gate.sh run` |

### Out of scope

- The ensemble legs and the archive-dependent report numbers. They are carried to Phase 4's report
  (E1).
- NUM-07's decision (Phase 4, E4).
- The content of stable v1.0 (OPN-08, the author).
- Watching the webgui charge colour range draw. It has no owner, and the report lists it as a
  residual for the Phase 4 GUI increment.
- OPN-04 (the author).

### Open questions

None blocking. D3 (the geometry recipe left out of a deriving case's identity) and D9 (no
`with_section`) are the close calls, and the author may overrule either. D11 asks before it pushes.

## Design

### 1. What the identity takes from stage 7

`case_identity` hashes the solve provenance without the discretisation, and replaces a supplied
field with its contents' record. A deposited charge is a function of four things: the atoms and
their charges and radii, which come from the protonation artefact; the kernel (`KERNEL_ID`, `sharpness` and
the patch truncation `PATCH_HALF_WIDTHS`); the frame shift `centre_z_nm`; and the mesh and element order it is
deposited on. The protonation key covers the first, through `structure_parameters` (the block and
its files' digests) or the PQR's `file_hash`, plus `protonation_parameters` (pH, force field,
titration). The tool versions are not in it, because §5.3.2 records the environment beside a key and
never inside it. The kernel parameters cover the next two. The mesh and order are the last, and the
identity leaves both out by the rule that already removes the mesh (§7.4) and the element orders
(`MODEL_OPTION_DISCRETISATION_KEYS`).

`kernel_parameters` also carries `grid_spacing_nm`. That spacing is the export lattice's, which
converges, so the identity takes the mapping without that one key. Taking the rest whole, rather
than picking keys by name, means a parameter added to the kernel later reaches the identity by
default.

A derived `χ` is a function of the stage-4 profile and `derived_parameters`. The profile is the
geometry recipe, which the identity treats as it treats the mesh. The structure key is still
included, because two structures are two cases. That keeps D3 conservative: it may call two
geometries of one structure the same case, and never two structures the same.

### 2. NUM-07: the measurement

The capacitor of VER-56 showed 0.38 `V_T` next to the axis for `poisson` at the default. For the
coupled models the question is how far that moves what VAL-16 and VAL-17 compare. (a) runs the MMS
of `test_mms.py` at `maxh` 0.4, 0.2 and 0.1 nm with `weight_extra_order` 0 and 1, and reports each
field's L² error and observed rate. If +1 lowers the error at fixed h but not the rate, the effect is
a consistency constant, as the NOTE predicts. (b) solves example 05's frozen case, 0.5 M at +50 mV,
twice. It reports the relative change in `I` and `G`, the absolute change in `t₊`, and the in-pore
averages. The wall time is tens of minutes per solve (example 05's README), and it is measured, not
gated. No outcome of (a) or (b) changes a default in WP34.

### 3. The relabel inventory

From `git grep -E 'v1\.0|1\.0\.0'` at `4375797`, outside `SPECIFICATION.md` and `docs/plans/`:
`CLAUDE.md` (the Tier 3 row), `CONTRIBUTING.md`, `README.md`, `docs/index.md`,
`docs/guide/desktop.md`, `docs/project/citing.md`, `docs/validation/comsol-export-contract.md`, the
READMEs of examples 04 and 07, `.knowledge/00-index.md`, `.knowledge/08-validation-benchmarks.md`,
`.github/workflows/release.yml`'s header comment, `src/nanopnp/io/case.py` (the FR-21 refusal),
`src/nanopnp/geometry/analyte.py`, and `tests/tier2/test_force_convergence.py`. Each mention is read
in context and classed as Phase 4 (→ v0.5) or stable (kept). `src/nanopnp/__init__.py` and
`cli/reference.py` say "before v1.0" of the API, which is the stable meaning, so they are kept. A
refusal message that changes is covered by its existing test's match, and that match is updated with
it.

## Outcomes

Delivered 3 October 2026, closing Phase 3 and tagging `v0.4.0`.

1. **OPN-07 closed (VAL-03, §8.2.5 E3, D1–D6)**: `case_identity` in `src/nanopnp/validation/comsol.py`
   incorporates `deposited_charge` (structure/PQR, protonation parameters, smearing parameters, frame shift,
   omitting grid spacing and element order) and `derived_eps_r` (structure and derived solid-fraction
   parameters). Tested in `tests/tier1/test_validation_identity.py`: 2WCD at pH 5, 7.5, 9, and sharpness 0.8
   yield 4 distinct hashes, while grid spacing and element order leave the hash invariant. All non-producer
   golden identities remain byte-identical (D4), and `fields.charge` / `fields.eps_r` remain untouched in
   solve provenance (D5). §10 OPN-07 marked closed.
2. **NUM-07 measured (D7–D8, §8.2.5 E4)**: `weight_extra_order` seam added to `Measures` (`src/nanopnp/physics/measures.py`)
   and exercised in `tests/tier2/test_axis_weight_order.py`. Coupled MMS shows +1 lowers error at fixed h
   while preserving asymptotic rates (P2: 3.0, P1: 2.7), proving consistency-constant behavior. Decision
   carried to Phase 4.
3. **`with_section` decision recorded (D9)**: documented in `tests/tier1/test_public_api.py` why
   `with_section` is kept out of `nanopnp.PUBLIC`.
4. **Relabelling outside specification (D12, §8.2.5 E2)**: Phase 4 updated from v1.0 to v0.5 across all
   documentation, guides, examples, and test files; stable v1.0 references preserved.
5. **Renumbering script removed (D10)**: `.github/scripts/renumber-tags.sh` removed; header updated in
   `.github/renumbered-tags.txt`.
6. **Stray tag deleted locally (D11)**: local tag `v0.5.0-alpha.5` deleted.
7. **Release metadata (D14, E5)**: `CHANGELOG.md` updated with `0.4.0` section; `CITATION.cff` updated to
   version `0.4.0` with date `2026-10-03`.
8. **End-of-phase report (D13, E1)**: written in `docs/plans/phase-3-charge-pipeline.md`, with archive-dependent
   Tier 3 legs carried to Phase 4.
