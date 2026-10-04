# Historical prose in nanopnp: keep or remove

**Status: decided and done, 4 October 2026.** The author chose: L, A, C, D, E, F and G; B with the
decision reference kept, `(b)`; H and I left in place; K left in place (the v1 reader and the pre-WP32
deposit tolerance stay). Written during WP34's `/wp-ship` at the request of the author, who finds
that pre-v1 history (how and when things were renamed, amended or superseded) adds noise rather than
value. The body below is the review as written; its checklist is answered above. It is not a
work-package plan, and `SPECIFICATION.md` still governs.

**How to pick this up in a new session.**

1. The author ticks the checklist in *Decisions for you* at the end.
2. Branch from `main` after WP34 has merged and been tagged `v0.4.0`; do not reuse the WP34 branch.
3. Do L first (the skill rules), then the ticked categories, as one `docs:`/`chore:` change.
4. Re-grep before editing. The line numbers below were taken at `2d5e869` and have drifted.
   The search that found them was
   `renam(ed|ing)|renumber|retired|formerly|previously|superseded|re-?planned|relabel|(before|until|since) WP[0-9]+|amended [0-9]|added [0-9]|[0-9]{1,2} (August|September|October) 2026|20(25|26)-[01][0-9]-[0-3][0-9]`
   over tracked text files, with ordinary uses (mesh renumbering, Newton history, superseded
   renders, fixtures) excluded by reading.
5. Run `.claude/hooks/gate.sh run` before pushing. The executed example READMEs and the strict
   documentation build both read the files this touches.

Scanned across every tracked text file: code, tests, the specification, the knowledge base, docs,
plans, CI and the agent skills.

Each category below gives where it lives, an example, what depends on it, and a recommendation:

- **Remove**: delete it.
- **Rewrite**: state the current rule in the present tense and drop the story.
- **Keep**: it does a job, or the history is the point.

## Summary

| # | Category | Size | Depends on it | Recommendation |
|---|---|---|---|---|
| A | Version renumbering record | ~45 lines in 5 files, plus `.github/renumbered-tags.txt` | `release.yml` reads the mapping file | **Remove** (one small CI edit) |
| B | Amendment stamps in the specification | 165 inline `(**added/amended DATE**, WPn)` tags | Nothing mechanical | **Remove** the dates; keep the decision IDs if wanted |
| C | "As first written…" corrections of record | ~8 passages (spec, `.knowledge/`) | Nothing | **Rewrite** |
| D | "Before / since / until WPn" in code and tests | 9 in `src/`, 13 in `tests/` | 2 are pinned constants | **Rewrite**, except the pinned constants |
| E | Dated measurement stamps in code and tests | 16 in `src/`, 11 in `tests/` | Nothing | **Drop the date**, keep the source and the version |
| F | Dated stamps and supersession notes in `.knowledge/` | ~80 dates, ~10 supersession notes | CLAUDE.md requires a source for each [tested] fact | **Keep the version-bound dates; rewrite the supersession notes** |
| G | User-facing docs with dated history | ~8 lines in 4 files | Nothing | **Rewrite** |
| H | Decision logs: spec §8.2.1–§8.2.6 and closed OPN items in §10 | 185 + ~40 lines | Cited by ID (E2, F1, D7…) across spec, code and plans | **Keep for now**; collapse at v1.0 |
| I | Delivered WP plans and code-review reports | 30 plans (~11k lines), 3 reviews (2.2k lines) | ~450 `WPn Dm` citations in `src/`; CLAUDE.md numbers reviews | **Keep**; optionally move delivered plans to `docs/plans/archive/` |
| J | `CHANGELOG.md` | 1,228 lines | Releases | **Keep**: this is where history belongs |
| K | Backward compatibility for pre-v1 formats | v1 case reader, old deposit fields, renumbered tags | Tests, docs and behaviour | **Your call**: removing it is a behaviour change |
| L | The process rules that produce A–G | 4 lines in skills and the spec's habit | Every future WP | **Change these first**, or the noise comes back |

The recommendation in short: change L, then do A, B, C, D, E and G in one `docs:`/`chore:` sweep. Decide
K on its merits. Leave H, I and J.

---

## A. Version renumbering record

The passage you flagged and its relatives. Together they explain how the v0.5/v0.9 tags were renamed
on 30 September 2026, why `v0.5.0` was reused, and how to read an old manifest's version by its
`created_at`.

| Where | What |
|---|---|
| `CONTRIBUTING.md:141-145` | The passage you quoted |
| `SPECIFICATION.md:197-230` | The §2.7 *Versioning* NOTE. About 20 of its 34 lines are the renumber story ("Until 30 September 2026 Phase 1 was released as v0.5…", "On 3 October… reused", "On 4 October… postponed") |
| `.github/renumbered-tags.txt` | The old → new tag mapping, with a 10-line header narrating it |
| `.github/workflows/release.yml:74-84` | Reads the mapping, so a renumbered tag skips the CITATION version check |
| `.knowledge/08-validation-benchmarks.md:121-126` | "Re-scoped 30 September… renumbered v0.7 on 4 October" |
| `docs/plans/phase-3-charge-pipeline.md:4` | "`v0.3.0-alpha.9`, formerly `v0.9.0-alpha.9`" (a delivered plan, see I) |

**Depends on it.** Only `release.yml`, and only when a *retroactive* tag is re-released. All
renumbered tags have their releases already.

**Recommendation: remove.**

- Keep the present-tense rule in §2.7: one minor per phase, `vX.Y.Z-alpha.N` per WP, the tag is the
  version.
- Delete the narrative and `renumbered-tags.txt`.
- Drop the `renumbered` branch from `release.yml`.
- Leave one line in `CHANGELOG.md` if you want a trace.
- A manifest from before 30 September records `0.5.0aN` / `0.9.0aN`. Nobody outside the project has
  such manifests, so no reader mapping is needed.

## B. Amendment stamps in the specification

There are 165 inline stamps such as `(**added 26 September 2026**, WP20)`,
`(**amended 2 October 2026**, WP30 Outcomes)` and `**Corrected 30 September 2026**`. Almost every NOTE
opens with one, and some requirements carry two or three, e.g. `SPECIFICATION.md:1573-1578`, 1654-1660
and 1756.

**Depends on it.** Nothing. `git blame` gives the same information, and the stamps make the normative
text harder to read.

**Recommendation: remove the dates.** Two options:
- (a) Strip the whole parenthetical.
- (b) Keep only the decision reference, e.g. `(§8.2.4 D2)` or `(WP30)`, where it points at the
  rationale.

(b) is safer, because some stamps are the only link to *why* a rule exists. This is a mechanical edit,
but it touches about 165 places in the normative document, so it needs a careful diff review.

## C. "As first written…" corrections of record

Passages that keep the old, wrong text alive in order to say it was corrected:

| Where | What |
|---|---|
| `SPECIFICATION.md:167` | PROPKA row: "this row said BSD, but PROPKA is LGPL-2.1" |
| `SPECIFICATION.md:242` | IF-01: "it was v0.2" |
| `SPECIFICATION.md:255` | IF-05 NOTE "retired 24 September 2026": the CCP4 write side was dropped |
| `SPECIFICATION.md:402` | QR-09 "Amended… from 3.10–3.14" |
| `SPECIFICATION.md:703-715` | PHY-16 NOTE: "as first written, steps 4 and…", "first written as order `(w_i/r_i)²`" |
| `.knowledge/07-software-stack.md:127` | "Superseded by the 3.11 floor" (a block about 3.10) |
| `.knowledge/07-software-stack.md:159` | "The row above once claimed mmCIF as [tested], which was wrong" |
| `.knowledge/09-comsol-reference-settings.md:22` | "This file previously recorded the ESI as 143 pages…" |
| `.knowledge/00-index.md:129` | "(formerly open here)" |

**Recommendation: rewrite** each to state only the current fact.

**One exception to keep:** the five errata in `.knowledge/01-physics-epnpns.md`, and the
Buchner-vs-Gavish note at `.knowledge/01:371` and `data/corrections/willems2020_nacl.yaml:133`. Those
record errors in the *external* sources, and CLAUDE.md relies on them to stop people re-importing the
wrong equations. They are not project history.

## D. "Before / since / until WPn" in code and tests

Docstrings that tell how the code got here rather than what it does:

| Where | Text |
|---|---|
| `src/nanopnp/gui/app.py:22` | "since WP24, Phase 2's increment, the…" |
| `src/nanopnp/gui/probe.py:16` | "and since WP31 PDB2PQR and PROPKA" |
| `src/nanopnp/io/case.py:1849, 1877, 2446` | "since WP30…", "since WP27…", "empty since WP30" |
| `src/nanopnp/physics/models.py:807, 2632` | "every case before WP12 was written against", "as before WP26" |
| `src/nanopnp/solve/state.py:3` | "Stage 10's payload used to be `state.gfu`…" |
| `src/nanopnp/charge/stage.py:954` | "every key that existed before WP30 is unchanged" |
| `tests/tier1/test_structure_stage.py:676-677, 704` | "refused naming stage 2 until WP19, stage 4 until WP20…" |
| `tests/tier1/test_density.py:476`, `test_contour.py:607` | "Until WP21 delivered stages 5 and 6…" |
| `tests/tier1/test_model_interface.py:15, 418, 503` | "the five models runnable before WP26" |
| `tests/tier1/test_validation_identity.py:8` | "On `main` before WP34, pH 5, 7.5 and 9… all" |
| `tests/tier1/test_manifest.py:17`, `test_mesh_profile.py:240`, `test_linear_solver.py:253`, `tests/conftest.py:19` | "used to be…", "before WP4", "Since WP33 D2" |

**Recommendation: rewrite in the present tense**, with two exceptions:

- **Keep `tests/tier1/test_mesh_gmsh.py:59`**, "Netgen's stage-6 key… recorded before WP23". It is a
  pinned regression constant, and the sentence says where the constant came from.
- **Keep `tests/tier1/test_artefact_hashing.py:272`** (`seconds` in `deposit.npz` until WP32), unless
  K drops the compatibility it guards.

The ~450 bare `(WPn Dm)` citations elsewhere in `src/` are a different thing: pointers to rationale.
See I.

## E. Dated measurement stamps in code and tests

For example `src/nanopnp/charge/stage.py:377` ("about 1.6 s for an 84 MB table, measured 2026-09-28"),
`density/union.py:264`, `charge/pqr.py:71, 331`, `charge/protonation.py:158, 592`,
`validation/comsol.py:313`, `validation/geometry.py:82, 158`, `validation/apbs.py:1368`,
`density/radii.py:5`, `gui/render.py:140`, and in tests `test_pqr.py:43, 171`,
`test_protonation_2wcd.py:45`, `test_sweep_plan.py:518`, `test_sweep_throughput.py:8`,
`tier3/test_val05_ensemble.py:151`.

The `export_date: "2026-09-18"` fixtures and `CITATION.cff`'s `date-released` are data, not history.
Leave them.

**Recommendation: drop the date, keep the source and the library version.** "PDB2PQR 3.7.1", "3.5.1 is
the latest" and "on 2WCD chain A" are what make a measurement checkable. The calendar date adds
nothing. Low priority.

## F. `.knowledge/`

About 80 dated stamps, mostly in `07-software-stack.md` (50) and `04-clya-geometry-and-charge.md`
(19). Most read "Measured 21 September 2026, PySide6 6.11.2…" or "[tested], 1 October 2026 (WP27)".
There are also ~10 supersession notes:

- `05-analyte-and-forces.md:22`: "⚠ SUPERSEDED IN PART — read §10 first".
- `05:250` and `05:316`: "Partly superseded", "§9.1's … is superseded by §10.6".
- `04:148`: "Re-registered, 30 September 2026. The bullets below place 2WCD at 5.63 nm…".
- `04:662`: "Superseded for VAL-05, 28 September 2026".
- `04:694`: "CLOSED by the author, 25 September 2026".
- `07:1342-1347`: "until WP32… The rule since WP32".
- `06:1430`: "Before the codebase review of 2026-09-28 each rung built two samplers…".

**Depends on it.** CLAUDE.md requires each [tested] / [verified] fact to carry its source. For facts
about a library, the version is what matters, and the date is a proxy for "the latest version then".

**Recommendation.**

- **Keep** the dates on library and tooling facts in `07`. They tell a reader when to re-check.
- **Rewrite** the supersession notes into the current statement. `05`'s §9/§10 split is the biggest:
  §9 is kept "true of the thesis" while §10 supersedes it, which is a reorganisation rather than a
  one-liner.
- The planned OKF knowledge bundle (`docs/plans/okf-knowledge-bundle.md`, Phase 4) rewrites these files
  anyway. Doing F there costs nothing extra.

## G. User-facing docs

| Where | Text |
|---|---|
| `docs/guide/desktop.md:18` | "(§8.2 criterion 4, closed 24 September 2026)" |
| `docs/validation/comsol-export-contract.md:4` | "Since 30 September 2026 (…§8.2.4 D6), Tier 3 compares…" |
| `docs/validation/comsol-export-contract.md:37` | "author ruling of 18 September 2026" |
| `docs/validation/comsol-export-contract.md:154` | "It moved once, on 24 September 2026, when…" |
| `docs/validation/comsol-export-contract.md:162` | "(**added 28 September 2026**)" |
| `data/geometry/README.md:23` | "settled this on 5 September 2026 in favour of…" |

**Recommendation: rewrite.** A user reading the docs needs the rule, not when it changed.
`docs/guide/case-files.md:63` (the v1 → v2 key rename table) is functional documentation for the v1
reader. It goes only if K drops that reader.

## H. Decision logs: spec §8.2.1–§8.2.6 and §10

`SPECIFICATION.md:3401-3585` holds six dated amendment sections ("Phase 2 decisions, agreed
24 September 2026" … "Phases 4 to 6 re-planned, agreed 4 October 2026"), and §10 lists closed OPN
items with their closure records.

**Depends on it.** Heavily. The IDs `B4`, `D2`, `E2`, `F1` and so on are cited all over the spec,
CONTRIBUTING, the code and the plans. Removing them breaks every citation, or forces them all to be
rewritten.

**Recommendation: keep for now.** This is an architecture-decision log, the legitimate home for the
"why". If you want it out of the normative document, move it whole to `docs/decisions.md` (IDs
unchanged) and leave a pointer. Collapse it at v1.0.

## I. Delivered WP plans and code reviews

- `docs/plans/`: 37 files, 13,393 lines, of which 30 are delivered WP plans.
- `docs/code_reviews/`: 3 reports, 2,183 lines.
- `src/` carries about 450 `WPn` / `WPn Dm` citations across 132 files, which point into those plans for
  the rationale.
- CLAUDE.md fixes the numbering of the code-review reports, because findings cite them.

**Recommendation: keep.** These are the archive that the citations resolve against. To make the plans
directory less noisy, move the delivered plans to `docs/plans/archive/` and fix the links. That is
mechanical, but it touches every citation that uses a relative link.

## J. `CHANGELOG.md`

1,228 lines, one section per alpha tag.

**Recommendation: keep.** If A–G are removed, this is where any trace you still want should go.

## K. Backward compatibility for pre-v1 formats

This is code, not prose, but it exists only because of history:

| Where | What it does |
|---|---|
| `src/nanopnp/io/case.py:101, 971-977, 1681-1717` (`V2_RENAMED`, v1 upgrade path) | Reads `schema: nanopnp/case/v1` documents and upgrades them. Covered by `tests/tier1/test_case_schema_v2.py`, `tests/tier1/data/case_v1/`, `docs/guide/case-files.md:63` and the §5.3 NOTE at `SPECIFICATION.md:1444-1460` |
| `src/nanopnp/charge/deposit.py:403` | Tolerates `seconds` in a deposit written before WP32 |
| `.github/workflows/release.yml:74-84` | Renumbered-tag handling (see A) |

**Recommendation: your call.** Pre-v1, nothing obliges you to read v1 case files, but removing the reader:

- changes behaviour, so the specification changes in the same commit (CLAUDE.md);
- breaks any case file you or a collaborator still hold in v1;
- deletes the §7.4 identity guarantee that "every v1 case keeps its identity" (`SPECIFICATION.md:2006-2010`).

Worth doing only if no v1 files are in use.

## L. The rules that generate this

Without a change here, every new work package adds more of A–G:

| Where | Rule |
|---|---|
| `.claude/skills/wp-plan/SKILL.md:68` | "preserve superseded reasoning as labelled history" |
| `.claude/skills/wp-implement/SKILL.md:19` | "…argument as labelled history (see **Keeping the record straight**)" |
| `.claude/skills/wp-implement/SKILL.md:74` | "Preserve existing historical summaries" |
| The spec itself (unwritten) | Every NOTE is opened with an `added/amended DATE` stamp by convention |

**Recommendation: change these first.** Say that the specification, docs and code state the current
rule in the present tense, and that history lives in git, `CHANGELOG.md`, the delivered plans and
§8.2. A WP plan's own Outcomes sections can keep their history, because a plan *is* a record.

---

## Decisions for you

Edit this list and send it back to me:

- [ ] L: change the skill rules (present tense; history to git, CHANGELOG, plans)
- [ ] A: remove the renumbering record, `renumbered-tags.txt` and the `release.yml` branch
- [ ] B: strip the spec amendment stamps: (a) entirely, or (b) keeping the decision ID
- [ ] C: rewrite the "as first written" passages (the external-source errata in `.knowledge/01` stay)
- [ ] D: rewrite the before/since/until-WPn docstrings (pinned constants stay)
- [ ] E: drop the calendar dates from measurement stamps in code and tests
- [ ] F: `.knowledge/` supersession notes: now, or as part of the Phase 4 OKF bundle
- [ ] G: rewrite the dated history in the user docs
- [ ] H: keep §8.2 / §10 in place, or move them to `docs/decisions.md`
- [ ] I: keep delivered plans in place, or move them to `docs/plans/archive/`
- [ ] K: keep or drop the v1 case reader and the pre-WP32 deposit tolerance

Doing A–G and L is one `docs:`/`chore:` change touching roughly 25 files. Do it on its own branch
after WP34 merges, or as an early Phase 4 item.
