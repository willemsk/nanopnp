# WP34 — Phase 3 closed: the open items resolved, and the end-of-phase report

**Status: planned, not started.** Written 3 October 2026, amended 4 October 2026, after WP33 merged (`main` at `4375797`,
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
§10 OPN-07, and opens OPN-08. **Second amendment, 4 October 2026, made in the commit amending this
plan:** the new §8.2.6, rulings F1–F5 by the author. The validation phase is postponed to v0.7 as
Phase 6, and two phases are inserted before it: Phase 4, polish and user testing (v0.5), opened by
an exploration of the architecture's modularity, and Phase 5, the graphical interface (v0.6), opened
by a design and requirements document, mockups and a visual-feedback workflow. The case schema and
the public API may change until v1.0 (F4). The amendment rewrites §2.7, IF-01 and its NOTE, the
Release column of FR-21, FR-22 and FR-28, QR-02, QR-15, §7.4, VAL-16, VAL-17, §8.1, §8.3, RSK-15,
OPN-08 and Appendix A. WP34 carries F1–F5 into the repository with E2 (D12, D15).

## Execution brief

### Scope

The author asked for one last package to resolve Phase 3's remaining open items. It carries five of
them, plus the phase close:

1. **OPN-07.** A golden's `case_hash` ignores a charge that stage 7 deposits, and a `χ` that it
   derives (E3).
2. **NUM-07 / WP28 D13.** The coupled models integrate their `r`-weighted forms one order short.
   WP34 measures this and records it; Phase 6, the validation phase, decides (E4, F1).
3. **`with_section` in `nanopnp.PUBLIC`.** Parked by WP31.
4. **The phases re-planned (E2, F1–F5).** The validation release is v0.7 and Phase 6, after Phase
   4 (polish and user testing, v0.5) and Phase 5 (graphical interface, v0.6). The repository is
   relabelled outside the specification, the stray retired tag is deleted, and the renumbering
   script is retired. Phases 4 and 5 are not planned here (D15).
5. **The end-of-phase report**, written on the Tier 1–2 evidence (E1), and `v0.4.0` (E5).

Discharges VAL-03 (for a deposited charge), and closes OPN-07. Touches NUM-07, VER-45 (the public
surface), and the phase criteria of the Phase 3 plan. No new identifier. **The brief is about 1,550 words, over
its 1,200 target**, because it carries five unrelated items, each needing its own decision, and the
4 October re-plan.

### Pointers

| Need | Read |
|---|---|
| OPN-07's evidence and constraints | §10 OPN-07; WP28 Outcomes, review finding #7 |
| The identity | `validation/comsol.py` `case_identity`, `DISCRETISATION_KEYS`; `charge/stage.py` `charge_grid_key`, `derived_parameters`; `charge/protonation.py` `_key` |
| NUM-07 | §6 NUM-07 and its NOTE on the `r` weight; `physics/measures.py`; WP28 D13 |
| Versioning and the re-plan | §2.7 and its Versioning NOTE; §8.2.5 E2; §8.2.6 F1–F5; §8.1; `.github/renumbered-tags.txt`; `CONTRIBUTING.md` *Versions and releases* |
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
| D9 | `with_section` | **Not added** to `nanopnp.PUBLIC`. A comment in `test_public_api.py` records the decision, and that Phase 4's API pass reviews it with the rest of the public surface (F3, F4) | It is an editor affordance. It changes no resolved case (WP31 D13), and adding it later costs nothing. Withdrawing it is no longer forbidden before v1.0 (F4), but it would still break callers, so the pass that reviews the whole surface decides, not WP34 |
| D10 | The renumbering script | `.github/scripts/renumber-tags.sh` is deleted, and the mapping file's header says the script ran once on 30 September 2026 and is gone, and that the `v0.5.0` names are now the polish phase's (F2) | Re-run after Phase 4 tags `v0.5.0-alpha.1`, it would retire live tags. The mapping stays for `release.yml` and for reading old manifests (E2, F2) |
| D11 | The stray tag | `git push origin :refs/tags/v0.5.0-alpha.5`, after confirming it resolves to `v0.2.0-alpha.5`'s commit, `5abcf42`. Confirm with the author before pushing | E2, F2. Deleting a remote tag is outward-facing |
| D12 | Relabelling outside the specification | "v1.0" becomes "v0.7" wherever it means the validation release, and "Phase 4" becomes "Phase 6" wherever it means the validation phase. "v1.0" stays wherever it means the stable release (IF-01's "before v1.0") or the backlog ("post-1.0"). The phase-to-version lists in `CONTRIBUTING.md` and the `CHANGELOG.md` preamble name all seven phases. A claim that the schema is frozen or the API stable before v1.0 is corrected to F4. CHANGELOG sections already released, and delivered plans, are history and stay | E2, F1, F4. The inventory is in [Design §3](#3-the-relabel-inventory) |
| D13 | The report's evidence | Each number is read from a test that asserts or logs it on WP34's tree, never copied forward from an Outcome without being re-run. The waived Tier-3 numbers are listed as carried to Phase 4 (E1) | The memory rule: a run cut short is not evidence. The report names numbers, not adjectives |
| D15 | Phases 4 and 5 | **Not planned in WP34.** `current.md` points at `/wp-plan phase-4` after `v0.4.0`, and the Phase 4 plan's first package is the modularity exploration, whose report precedes the user-testing protocol (F3). Phase 5's design document, mockups and visual-feedback workflow are planned by `/wp-plan phase-5` once v0.5 is released (F5) | F3 makes the modularity report the input to the rest of Phase 4's planning, so planning that phase inside a closing package would decide its work packages before their evidence exists |
| D14 | Release | WP34's `CHANGELOG.md` section is `v0.4.0`, and `CITATION.cff` names `0.4.0` with its date. After merge, the last commit on `main` is tagged `v0.4.0` alone (E5) | `CONTRIBUTING.md` *Versions and releases*; `release.yml`'s CITATION check |

> **Outcome — the identity, D1–D6** (4 October 2026). `validation/comsol.py` `_stage7_recipe`
> builds `deposited_charge` and `derived_eps_r` through `create("structure").key` and
> `create("protonation").key`, so the structure key's own `structure_parameters` and
> `ProtonationStage._key` decide what they hold, and through `charge_grid_key` for the kernel
> minus `KERNEL_DISCRETISATION_KEYS = {"grid_spacing_nm"}`. A `structure:` case now needs the
> `structure` extra and its files on disk to have an identity, which stage 1 needs anyway, and is
> refused with stage 1's `MissingExtraError` otherwise. D6: 12 ms per call on the 9.2 MB deposited
> 2WCD, an upper bound for example 06's prepared chains A–L, plus 0.7 s on the first call to import
> stage 1 and MDAnalysis. `test_case_schema_v2.py`'s v1 stand-in gains `deposits_charge` and
> `derives_eps_r` as `False`, which v1 could not be otherwise; the corpus's recorded identities are
> unchanged (D4). [`test_validation_identity.py`](../../tests/tier1/test_validation_identity.py)
> fails two of its four tests with `comsol.py` reverted.
>
> **Outcome — D7, the seam.** `Measures.weight_extra_order` is added in `Measures._form_bonus`,
> used by `volume` and `surface` only, so `integrate`, `bonus_order`, `integration_order` and
> singular terms are untouched and a negative value is refused. `poisson`'s own
> `RADIAL_WEIGHT_ORDER` stacks with it. The localising test is Tier 2,
> `test_num07_weight_extra_order_closes_the_r_weight_deficit` in `test_axis_quadrature.py`: the
> weighted P2 stiffness of `u = z²` on an axis-touching mesh is 1.0 × 10⁻⁶ short at 0 and exact to
> 3 × 10⁻¹⁵ at +1.
>
> **Outcome — D8, measured** (4 October 2026). The numbers are in the NUM-07 NOTE and
> `.knowledge/06` §2.2. (a) +1 leaves every rate of VER-18 unchanged and lowers the error at fixed
> `h`, most for the concentrations: at 0.1 nm, ×0.42 for `c_Cl−` and ×0.77 for `c_Na+`. (b) On
> example 05 the states differ by 4.9 × 10⁻⁷, and no compared number moves by more than
> 7.6 × 10⁻⁸ relative (the EOF; `I`, `G` and `t₊` by 10⁻¹⁰ or less). Two changes to the test as
> planned. **A third route was needed:** changes that small are also what a seam that never reached
> the solve would give, so the test now evaluates each state in both forms and asserts that each is a
> root of its own (`|R|` about 2 × 10⁻¹¹) and not of the other's (7.3 × 10⁻⁴). **`nanopnp mesh`
> called in-process** runs `logging.basicConfig(force=True)`, which silenced the first run's log;
> the test now restores the root handlers and writes every number to a JSON file. The first run's
> numbers were read back from its stores with the test's own helpers, and the full test was re-run
> as amended. In-pore here is the element-centroid lumen between `z` = −1.85 and 12.25 nm. The
> peak radially averaged *equilibrium* potential needs a 0 V solve and is not measured. Each solve
> took about 30 minutes on two threads.

> **Outcome — D9 to D12.** D9's comment is in `test_public_api.py`, the set unchanged. D10: the
> script is deleted and the mapping's header rewritten; `release.yml` matches the first column
> only, so the reused `v0.5.0` names in the second are never waived. **D11 is done, by the author.** The tag resolved to `5abcf42` as expected, and the author
> approved the deletion. This session's git proxy refused the push (`unexpected disconnect`, twice),
> because it admits the branch push only, so the author ran `git push origin
> :refs/tags/v0.5.0-alpha.5` on 4 October 2026; `git ls-remote --tags origin` lists no `v0.5.0`
> name since. D12 as inventoried, with three readings: the README's release table
> keeps a v1.0 row for the stable release beside the new v0.5–v0.7 rows; FR-11's "after v1.0" in
> the `boundary_layer` refusal is the backlog and stays; and `.knowledge/00` ruling 10 (PlyAB after
> v1.0) is OPN-03's post-release generalisation and stays. No refusal test matched "v1.0".

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
   carried to Phase 6, versioning and the phases amended), the verification criteria with E1's
   waiver, and the **End-of-phase report** (D13), whose carried items name Phase 6. Then
   `current.md` points at Phase 4, the polish phase, and `/wp-plan phase-4` (D15).
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
- NUM-07's decision (Phase 6, E4, F1).
- Planning Phases 4 and 5 (D15).
- The content of stable v1.0 (OPN-08, the author).
- Watching the webgui charge colour range draw. It has no owner, and the report lists it as an
  input to the Phase 5 design document (F5), which is where the visual-feedback workflow that can
  watch it is built.
- OPN-04 (the author).

### Open questions

None blocking. D3 (the geometry recipe left out of a deriving case's identity) and D9 (no
`with_section`) are the close calls, and the author may overrule either. D11 asks before it pushes.
The 4 October re-plan was settled with the author before this amendment (§8.2.6): the phases
renumbered so that the minor version names the phase, breaking changes allowed until v1.0, the v1.5
row folded into Phase 5, and Phase 4's user testing run by the author in scripted sessions.

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
in context and classed as the validation release (→ v0.7) or stable (kept). `src/nanopnp/__init__.py` and
`cli/reference.py` say "before v1.0" of the API, which is the stable meaning, so they are kept. A
refusal message that changes is covered by its existing test's match, and that match is updated with
it.

The re-plan of §8.2.6 adds three kinds of mention. "Phase 4" meaning the validation phase, from
`git grep 'Phase 4'` outside `SPECIFICATION.md` and the delivered plans: the phase-to-version lists of
`CONTRIBUTING.md` *Versions and releases* and the `CHANGELOG.md` preamble, and the Tier 3 comment
in `.github/workflows/ci.yml`. Each becomes Phase 6, and the two lists name Phases 4 to 6 with their
versions. The release table of `README.md` gains the v0.5 and v0.6 rows, and its v1.0 row becomes
v0.7 and Phase 6. `git grep -i 'frozen\|stable from'` at `8f46ae7` finds no live claim that the
schema is frozen or the API stable before v1.0 outside `current.md`, which this amendment corrects,
and the README's "frozen case schema" describes what v0.2 shipped, so it stays. The desktop guide's
"Installers for all three platforms come after v1.0" stays, because F5 keeps the installers
post-1.0.
