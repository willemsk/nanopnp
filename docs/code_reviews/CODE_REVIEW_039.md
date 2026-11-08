# Code review 039: the written knowledge audit

2026-11-08 · branch `ccr-ffafd419-mwhw6f` from `main` at `a5039af`; the fixes are the ten commits `808ca66` to `4061c40` · scope: the specification bundle (`SPECIFICATION.md`, `specification/`), `knowledge/`, the docs tree, `.claude/`, the root entry points; the records (`specification/history/`, `docs/plans/`, `docs/code_reviews/`, `docs/design/reviews/`, `docs/design/spike/`, `docs/superpowers/`, `docs/user-testing/`, `CHANGELOG.md`) for reachability only · focus: accuracy, clarity, efficiency, redundancy and organisation of the written knowledge, on the paths an agent session and the author read · status: completed; 48 findings fixed, 317 put to the author, 22 dismissed

Brief: `docs/plans/kb-audit-brief.md`. The brief names the report 037; 037 and 038 were taken when this session started, so this report is 039 throughout. Every count below names the commit it was measured on; `a5039af` is the audited tree, `86e647b` the tree after the fixes. Attachments, beside this file under `CODE_REVIEW_039/`: `findings.md` (every finding, by axis, with its state), `redundancy-map.md`, `sediment.md`, `decisions.md` and `decisions.json` (the decisions register prototype), `architecture.md` (the architecture as the tree states it), and `raw/` (the baseline, the ten readers' returns, the sixteen task walks, the classification tables, the survey and the re-run checks).

## 1. Summary

The project's written knowledge was read whole: 420 files, about 795,000 words, around 1.33 million tokens at `a5039af`, of which the specification, the knowledge base, the docs site, the agent instructions and the root files are live text and the rest is record. Ten readers each took a directory, sixteen task walks followed the reading paths a session actually takes, and eleven mechanical probes checked every link, path, identifier, version, test name and claim marker.

The text is in good order where it matters most: every requirement identifier resolves, every ruling row is reachable, no register shares a number, the physics concepts agree with §4, and the readers found no SHALL that contradicts the code. What they found is drift: 177 accuracy findings, most of them a count, a name, a path or a tense that a later package made false; 48 redundancy findings where one meaning lives in two or three files; 34 places where measurements and resolved history sit on a live reading path; and a handful of organisation defects, the largest being that `clause.py` could not find eleven rulings and did not print a clause's own NOTEs.

Forty-eight findings were fixed here, each a change a reader can verify from the finding's evidence and none a change of meaning: the two scripts now read every ruling row; eleven stale paths, names and versions, nine counts, seven citations, four pointers and seven tenses are current; three dead test references say the test was deleted; six concepts' headers match their claims; and three record folders have an index. The strict build, the link check, the marker check and the clause check over 282 identifiers pass on the result.

Everything else waits for the author: 317 findings in `findings.md`, each with its proposed edit; the redundancy map and the sediment list, worth about 22,500 tokens of live text if adopted whole; two rehearsed moves with a script each, one recommended (name each NOTE's clause) and one not (archive the delivered plans, which breaks 74 record links and the build); a prototype decisions register of 1,142 decisions with its home and maintenance rule to choose; and an architecture page with the same two questions. Section 9 lists the decisions in the order to take them.

## 2. Baseline

Measured by `.claude/scripts/audit/inventory.py` and `paths.py` (tokens are characters divided by four); the full tables are `raw/inventory.md` and `raw/paths.md` (at `a5039af`) and `raw/after/inventory.md` and `raw/after/paths.md` (at `86e647b`).

| Measure | At `a5039af` | At `86e647b` |
|---|---|---|
| Files in scope | 420 | 423 (the three indexes) |
| Words, all | 795,324 | 798,906 |
| Tokens, all | 1,329,427 | 1,336,822 |
| of which `docs/plans/` (records) | 592,830 | 595,443 |
| of which `specification/` without `history/` | 125,259 | 125,335 |
| of which `knowledge/` | 173,711 | 174,000 |
| Files no other Markdown links to or names | 15 | 2 (`docs/plans/index.md`, `docs/code_reviews/index.md`) |
| Relative links / broken | 1,284 / 2 | 1,411 / 2 (both in records) |
| `[tested:]` markers / naming no test | 448 / 0 | 450 / 0 |
| `[verified]` markers / with no footnote | 123 / 20 | 123 / 20 (ORC-07, your call) |
| `clause.py` over Appendix A and the history letters | 10 misses | 0 misses over 282 identifiers |

The reading paths barely move, because the fixes add precision rather than remove text; the savings are the author's calls in sections 4 and 9.

| Path | Words → words | Tokens → tokens |
|---|---|---|
| The always-loaded set (`CLAUDE.md`, `SPECIFICATION.md`, `current.md`, `core.md`, the two rules files) | 5,995 → 6,003 | 10,640 → 10,655 |
| `/np-plan wp n` | 4,277 → 4,275 | 6,449 → 6,446 |
| `/np-ship wp n` | 3,249 → 3,264 | 4,923 → 4,943 |
| Implement or change a pipeline stage (§3.2, §5.2, §5.3.2) | 12,185 → 12,185 | 18,349 → 18,350 |
| Change the case file (§5.3.1, §5.3.3, Appendix A) | 6,154 → 6,156 | 9,939 → 9,964 |
| Touch the physics or a correction (§4, `knowledge/01`, §6) | 18,213 → 18,231 | 27,652 → 27,707 |
| Touch the numerics, solver or mesh (§6, §7.3) | 10,218 → 10,218 | 15,125 → 15,125 |
| A decision and its reason: which ruling set the plan word cap | 11,320 → 11,328 | about 17,500 → 17,500 |
| A measured number and its derivation: the Tier 2 tolerance on the current | 14,721 → 14,732 | 24,736 → 24,756 |

The biggest single saving on offer is `clause.py --no-history`, now named in `SPECIFICATION.md`: a one-clause read of `VER-62` drops from about 3,300 words to the clause and its NOTEs.

## 3. Findings by axis

Every finding has one `AUD-nn` number, assigned by `.claude/scripts/audit/register.py` in the order ORC (the orchestrator's own), SPA, SPB, SPC, SPD (the specification readers), KGE, KNU, DOC, CLD, KST, KPH (the knowledge, docs and `.claude/` readers) and WLK (the task walks), and one state: `fixed <sha>`, `your call` or `dismissed <reason>`. The full table in the brief's schema is `findings.md`; its *Source to AUD map* gives each reader's number beside the `AUD` one.

| Axis | High | Medium | Low | Live | Fixed here |
|---|---|---|---|---|---|
| Accuracy | 13 | 79 | 85 | 177 | 44 |
| Clarity | 0 | 26 | 45 | 71 | 3 |
| Efficiency | 1 | 16 | 17 | 34 | 1 |
| Redundancy | 0 | 17 | 31 | 48 | 0 |
| Organisation | 1 | 21 | 13 | 35 | 1 |
| All | 15 | 159 | 191 | 365 | 48 (+22 dismissed = 387 raised) |

The fifteen high-severity findings, each a line here and a full row in `findings.md`:

| ID | Where | Defect, in one sentence | State |
|---|---|---|---|
| AUD-20 (SPA-05) | CON-05; §2's product overview | CON-05 says the concentration-dependent parameters use the local ionic strength; the normative driver is the mean concentration `⟨c⟩` (PHY-01), the ionic strength a named option. | your call |
| AUD-48 (SPB-01) | §6's 33 NOTEs, §4's 16 NOTEs, `clause.py` | `clause.py` attaches a NOTE to the identifiers the NOTE names, and 32 of 33 §6 NOTEs and 10 of 16 §4 NOTEs do not name the clause they follow, so `clause.py NUM-16` leaves out NUM-16's own NOTEs. | your call; the move is rehearsed (section 5, P3) |
| AUD-96 (SPC-01) | §5.1's diagram, §5.2's stage-9 row | The design puts case assembly after mesh, charge and materials; in the code stage 9 runs first and every stage consumes its output. | your call |
| AUD-101 (SPC-06) | §5.2, §5.3.1, §5.3.4 | The text gave the profile, field and sweep schemas as `v1`; the code, the data and the guide use `v0.5`. | fixed `2bf8825` |
| AUD-106 (SPC-11) | §5.3.1's worked example | The one worked case file is refused when validated: it supplies `inputs.mesh` beside `structure:` and puts an analyte on a generated mesh. | your call |
| AUD-107 (SPC-12) | §5.4.1, ADR-001 | The text says the weak forms are written against a thin internal interface; §8.2.8 H3 ruled they are written once against NGSolve and the interface is the shape a second backend would take. | your call |
| AUD-152 (KGE-01) | `knowledge/04`, gap G7 | G7 says "trust the table" for the 0.15 M radial-potential row that ruling 7 and OPN-01 exclude from regression targets. | your call |
| AUD-230 (DOC-01) | `docs/guide/charge.md`, `geometry.md`, `concepts.md` | The guide says protonation runs after stage 6; since WP5.03 it runs before stage 2, and a pH change moves the density, the contour and the mesh. | your call |
| AUD-251 (CLD-01) | `np-ship/wp.md`, `np-implement/wp.md` | The preflight check does not name the changelog heading `tag.yml` greps, so eight Phase 5 packages shipped with their entries under `## [Unreleased]`, which the tag workflow would refuse. | your call |
| AUD-281 (KST-01) | `knowledge/07/11` | The concept says four stage modules fall back to a temporary workspace; no stage does, a missing workspace raises. | your call |
| AUD-285 (KST-05) | `knowledge/09/05` row 5 | "Our BL mesh is a deliberate deviation; keep it": the default mesh has no boundary layers. | your call |
| AUD-288 (KST-08) | `knowledge/08/05` | The CI table said Tier 3 is "nightly + pre-release, must pass"; §7.6 says recorded, not gated. | fixed `81c913a` (row 3; row 4 is the author's, SPD-06) |
| AUD-312 (KST-32) | `knowledge/07/08` | About 560 of 744 words analyse a Python 3.10 target the project dropped. | your call |
| AUD-339 (KPH-12) | `knowledge/01/05` | The concept presents the reference's per-atom `(r, z)` Gaussian as the method, which PHY-17 forbids; nanopnp smears in 3D with a closed-form azimuthal mean. | your call |
| AUD-356 (KPH-29) | `knowledge/02/09` | The current is defined as the cross-section integral of the flux, the route the rules forbid for the CG flux. | your call |

Eight findings rest on the ESI or the COMSOL model report, which this session could not open; the thesis was the only primary source reachable. They are marked `unchecked` in their state and are the author's to confirm (AUD-316, 343, 346, 371, 372 and three KST rows; the list is in `findings.md`).

## 4. The redundancy map and the sediment list

**The redundancy map** (`redundancy-map.md`, 48 rows at `86e647b`, drawn by `.claude/scripts/audit/maps.py` from the register) lists each meaning that has more than one home, its homes, and the home the finding proposes. The pattern is one: the specification states a rule, and a knowledge concept restates it in full instead of pointing at it. The largest clusters are the §6 numerics (NUM-02, NUM-04 to NUM-07, NUM-09, NUM-16 to NUM-21, NUM-23 to NUM-25, NUM-30 to NUM-33) mirrored in `knowledge/06` (AUD-61 to 64, 209, 213 to 215, 219); the §4 physics (PHY-03 to PHY-15, PHY-21) mirrored in `knowledge/01` (AUD-331 to 333, 340); the charge pipeline transcribed in three knowledge files (AUD-182); the backend assessment in both ADR-001 and `knowledge/07/01` (AUD-318); and the process rules carried in `CLAUDE.md`, `CONTRIBUTING.md`, the skills and §8.4 (AUD-264, 279, 280). The proposed rule, which the author would ratify, is the one the map applies throughout: a rule's home is the specification clause, a measurement's home is the knowledge concept, and the other file points.

**The sediment list** (`sediment.md`, 34 rows) is the efficiency axis ordered by the token delta each finding states; the stated deltas sum to about 22,500 tokens. The ten largest: §5.3.1's NOTEs that carry design rationale and history (AUD-113, about 4,700 tokens off *Change the case file*); the Phase 5 plan's delivered narratives (AUD-244, about 2,400 per read, the lane's file); four generations of suite timings in `knowledge/07/12` (AUD-314, about 1,600); the "Source:" tails that repeat a `[tested:]` marker's test (AUD-317, about 1,470; AUD-222, up to 1,000); the §6 NOTEs' WP measurements and ruling citations (AUD-60, about 1,200); `review.md` read on every `/np-plan` call for its 110-word pause (AUD-278, about 1,130); §5.2's derivations (AUD-119, about 1,050); PHY-16's PDB2PQR tool behaviour (AUD-82, about 1,000); the test-evidence bullets that repeat their concept (AUD-221, about 900); and the forward-looking Qt NOTE in §7.2 (AUD-143, about 900). Each row names the record it would move to or says it goes.

## 5. Organisation

Three structural proposals were carried through to a script; two were rehearsed on a scratch branch (`raw/after/migrate-*.log`) and not applied. The other organisation findings (35 live, in `findings.md`) are edits within a file: the §5.3.1 NOTEs re-homed (AUD-114, 117, 118), `knowledge/06/09`'s section numbers put in reading order and its title widened (AUD-199, 200), the test-evidence concepts gathered or pointed at (AUD-325), the workbench design document given a status line that separates live design from record (AUD-243), and a *Where to start* row for the workbench (AUD-38).

**P1. Indexes for the record folders** (applied, `4061c40`; AUD-10). `docs/plans/`, `docs/code_reviews/` and `docs/design/reviews/` had no index, and thirteen records could be reached only by listing a directory. `.claude/scripts/audit/index_records.py` writes `index.md` in each folder, one line per file with the file's own status line (81 plans, 39 reviews, 6 design reviews at `4061c40`). It breaks nothing: the folders are excluded from the site, no path rule names an `index.md`, `duplicates.py` matches `wp*.md` and `CODE_REVIEW_*` alone, and the link check is unchanged (1,411 links, the same 2 broken in records). What it leaves open is the rule that keeps an index level with its folder: nothing re-runs the script today, so the next plan or review makes it stale. Your call (section 9, item 4).

**P2. Move the delivered plans to `docs/plans/archive/`** (rehearsed, not recommended). History-prose-review item I allows it. `.claude/scripts/audit/migrate_plans_archive.py` moves every `wp*.md` or `phase-*.md` whose status line begins *delivered* or *closed* (65 of 82 files), rewrites the 115 links to them in the six live files and the index (`current.md` 2, `phase-5-workbench.md` 8, `review-findings.md` 73, `review-items.md` 18, `modularity-findings.md` 13, `modularity.md` 1), and widens `duplicates.py`'s plan glob. It cannot rewrite a record, so 74 links in 8 records break (`phase-4-record.md` 45, `CHANGELOG.md` 17, `phase-1-solver-core.md` 4, `phase-5-record.md` 3, `docs/user-testing/findings.md` 2, three plans 1 each), and `generate.py` refuses the changelog's first broken link, so the strict build fails (`raw/after/migrate-plans-archive.log`). `clause.py` and `duplicates.py` are unaffected. The move is viable only if the author allows the 17 `CHANGELOG.md` links and the 57 plan-record links to be rewritten, which the records rule forbids; the recommendation is to leave the plans where the citations resolve and let P1's index carry the status.

**P3. Name each NOTE's clause in its label** (rehearsed, recommended; AUD-48). `.claude/scripts/audit/migrate_note_labels.py` finds, in §4 and §6, every NOTE that does not name the clause it follows and puts that identifier first in its label: `NOTE:` becomes `NOTE (NUM-08):`, `NOTE (sign):` becomes `NOTE (NUM-24, sign):`, `NOTE on the relative tolerance.` becomes `NOTE (NUM-16, on the relative tolerance).`. Forty NOTEs change (8 in §4, 32 in §6), one line each; the NOTE text is otherwise untouched, the SHALL counts are unchanged (75 and 91), and the files gain 8 and 32 words. After it, `clause.py` prints 131 NOTEs over the 58 PHY and NUM identifiers where it printed 91 (NUM-16 1 → 3, NUM-24 1 → 4, NUM-28 3 → 7, PHY-20 7 → 10), every identifier still resolves, the link check, `duplicates.py` and the strict build pass (`raw/after/migrate-note-labels.log`). It breaks nothing but the habit; it is a specification edit, so it is the author's to run.

**Not proposed.** A merge of the two glossaries (AUD-372), a split of `knowledge/06/09` (AUD-200) and a move of `knowledge/06/12`'s one bullet to the physics directory (AUD-224) are each one finding with its own edit, cheaper by hand than by script. No folder is proposed for retirement: every folder in scope is cited.

## 6. The decisions register

**The prototype.** `.claude/scripts/audit/decisions.py` reads every source of the brief's Appendix D and writes `decisions.md` and `decisions.json`: 1,142 rows at `a5039af`. By source: 474 plan decision rows (`| Dn |`), 282 history rulings, 222 `REV` rows, 38 `WB` rows, 25 *Your call* paragraphs, 24 Outcome annotations, 18 `MOD` rows, 14 knowledge-base rulings, 13 `(author)` or `(my call)` marks, 11 *Decisions for you* items, 11 *Not to be re-decided* bullets, 9 `OPN` rows and 1 code-review sentence. By decider: 446 by the author, 655 the session's own call, 36 put to the author, 5 open. Status: 468 are delivered plan decisions, 212 in force, 174 fixed, 52 spent, 39 open, 34 deferred, 19 superseded, 7 declined. With no stated home: 201, of which 120 are plan decision rows whose "where it holds now" nobody wrote down, 10 are history-prose-review items and 10 the knowledge base's 2026-08 rulings. The tree's Markdown cites a plan decision as `WPn Dm` 855 times in 63 files (122 of them inside the plans); the 82 citations on live paths all resolve (`raw/probes.md`).

**The proposal**, each line a `your call`:

- *Home*: one generated page, `docs/project/decisions.md`, written by the script from the tree, as `modularity-measurements.md` is, with the sources left where they are. A hand-kept register would be a fourteenth copy; a generated one is a view.
- *Shape*: Appendix D's columns as the prototype has them (source identifier; decided by; where; date; package; what was decided; where it holds now; status), sorted by date then source, with the counts by source and decider at the top.
- *What counts*: a ruling row, a plan's `Dn` row, a `REV`, `MOD`, `OPN` or `WB` row's ruling, a knowledge-base ruling and a *Not to be re-decided* bullet. An Outcome annotation, an `(author)` mark and a *Your call* paragraph are evidence for a row's date and decider, not rows of their own: the prototype shows they add 62 rows and no decision the other sources lack.
- *Relation to the history index's "Where each ruling holds now"*: fold. That list (282 entries, 4,025 words) is the register's *where it holds now* column for one source; generating it from the register, or replacing it with a link to the page filtered to history rulings, removes the hand-kept copy and answers WLK-10, the walk that scanned the whole list to learn which ruling set the plan word cap.
- *The one rule*: `/np-plan` re-runs `decisions.py` in the commit that writes a ruling record or a `Dn` table, and `/np-ship` re-runs it in the commit that closes a package; a Tier 1 guard like `test_layering.py`'s asserts the page equals the tree. Alternatively the docs job regenerates it on every build and nothing is committed.

## 7. The architecture

**The documents.** §5.1's module table names the 20 subpackages the tree has and no other, and the one-line docstrings agree with it (`architecture.md`, section *§5.1's module table against the tree*, at `c1f60ca`); the drift is in the words: `gui/` is "Desktop application" in both while the shipped shell is NiceGUI in the browser (AUD-307, CLD and KST), `sweep/`'s docstring speaks of job arrays, and the table omits the top-level `case.py` and the `__init__` surface (AUD-100). The diagram and the stage-9 row misplace case assembly (AUD-96). §5.4.1 and ADR-001 still describe the thin backend interface H3 ruled unbuilt (AUD-107, 21, 108), ADR-002 folds the optional boundary layers into the default path (AUD-109), ADR-004 argues for a shell it later withdraws (AUD-110), and `docs/project/modularity.md` states its numbers at `97f2b3d` in the present tense and gives a layer order that differs from `modularity-layering.yaml`'s and the code's (AUD-237, 238). The `MOD-nn` rulings stand (§8.2.8); nothing here reopens one.

**The survey** (`raw/survey/`, run by `.claude/scripts/audit/survey.sh` at `a5039af` from scratch environments; registry facts from PyPI on 8 November 2026). None was adopted. What `nanopnp.validation.modularity` already measures: the import relation by kind, the layer order and its upward edges, the components, the stage conformance, the extension points, the backend reach, the public surface and the sizes; `test_layering.py` holds the relation to `modularity-layering.yaml`.

| Package | Measures | Adds over `nanopnp.validation.modularity` | Licence | Publisher; releases; latest | CON-07 (dev install) | Run here |
|---|---|---|---|---|---|---|
| import-linter | Import contracts (layers, forbidden, independence) as configuration | A readable contract and a one-line CI check; the relation itself is already measured | BSD-2 | D. Seddon; 52; 2.16, 2026-11-06 | Pure Python over grimp's wheel; no compiler | Contract in `modularity.md`'s order: **broken** (`core → io`, `io → materials`, …), because that order differs from the YAML's and the code's (AUD-238) |
| grimp | The import graph as an API | Nothing the module lacks; a second graph | BSD-2 | D. Seddon; 54; 3.19, 2026-11-06 | Rust extension, prebuilt wheels | 191 modules, 922 imports; one shortest chain `physics → mesh` (`physics.models → mesh.primitives`) |
| tach | Module boundaries as `tach.toml`, with a sync | A boundary file and `tach check`; overlaps the YAML | MIT | gauge-sh; 109; 0.35.3, 2026-10-06 | Rust, prebuilt wheels | Synced a config with no dependencies; "no first-party imports found" from a symlinked root: not usable without the tree in place |
| pydeps | Module dependency graphs as images or JSON | Pictures; the JSON duplicates the measured relation | BSD-2 | B. Pettersen; 125; 3.0.9, 2026-10-01 | Pure Python; Graphviz for images | JSON of 191 modules' bacon-1 imports |
| deptry | Declared against used third-party dependencies | A check the lock does not make: unused, missing and transitive dependencies | MIT | F. Maas, M. Kniewallner; 85; 0.25.1, 2026-03-18 | Rust, prebuilt wheels | Scanned 191 files; assumed module names for every dependency (no environment) |
| radon, xenon | Cyclomatic complexity, maintainability index; xenon gates thresholds | Function complexity, which nothing in the tree measures | MIT | M. Lacchia; 55 and 23; 6.0.1 (2023) and 0.9.3 (2024) | Pure Python | MI rank C for `protonation.py`, `gui/widgets/geometry.py`, `pipeline/checks.py`, `validation/modularity.py`, `physics/models.py`, `io/models.py`; xenon: 20 blocks at rank D or E |
| wily | Complexity and MI over git history | The trend, if the history were deep (a shallow clone gave 3 revisions) | Apache-2 | A. Shaw; 50; 1.25.0, 2023-10-11 | Pure Python | MI ranking at `e32521f`; no history on the hosted clone |
| lizard | Function length, cyclomatic complexity and parameters | Same axis as radon, with length and parameter counts | MIT | T. Yin; 134; 1.25.1, 2026-11-07 | Pure Python | 14 functions over CCN 15, the largest `charge/protonation.py:_assemble` (CCN 39, 104 NLOC) and `structure/read.py:select` (CCN 38) |
| interrogate | Docstring coverage | A count the ruff `D` rules already enforce for `src/` | MIT | L. Root; 16; 1.7.0, 2024-04-07 | Pure Python | Per-file coverage table; private functions counted, which the project's rule excludes |
| vulture | Unused code | Dead names; five hits, all `exclude`/`include` or `mtime_ns` unpackings | MIT | J. Seipp; 56; 2.16, 2026-03-25 | Pure Python | 5 findings at 100 % confidence |
| pylint (design checkers) | Too many arguments, attributes, branches | The `R09xx` family; ruff's `PLR` covers most of it | GPL-2 | PyCQA; 219; 4.1.3, 2026-10-11 | Pure Python | `too-many-arguments` on the force routines and others |
| ruff rule families not enabled | `TRY`, `PLC0415`, `PLR2004`, `PLR0913`, `S`, `FBT`, `C901`, `ARG`, `T201`, `PERF`, `A` | Already installed; `C901` (25 hits) and `PLR0913` (92) would be the complexity gate without a new dependency | MIT | Astral; 431; 0.17.4, 2026-11-05 | Rust, prebuilt wheels; already a dependency | 2,121 hits across 32 rules; 952 `TRY003`, 690 `PLC0415` (the deferred imports VER-72 allows) |
| mypy `--html-report`, `--linecount-report` | Typed line coverage | Nothing: `--strict` already passes; 63,024 lines typed | MIT | python/mypy; 143; 2.4.1, 2026-10-28 | Already a dependency | 191 files, no issues; report generated |
| pyreverse (pylint) | Class and package diagrams | Pictures | GPL-2 | PyCQA | Pure Python; Graphviz for images | "191 modules, 942 imports"; the dot files land in the working directory (deleted) |
| code2flow | Call graphs | Pictures of calls within one subpackage | MIT | S. Rogowski; 8; 2.5.1, 2023-01-08 | Pure Python; Graphviz | `solve/`: 4 files processed |
| pyan3 | Call graphs | As code2flow | GPL-2 | J. Jeronen; 23; 2.9.0, 2026-10-06 | Pure Python | `solve/`: a dot graph; root inference warning |
| sourcery | Refactoring suggestions | Opinion | Proprietary | Sourcery AI; 23; 1.46.0 | Binary; account token | not run: proprietary, needs an account token |

Recommended, at most two, neither adopted here: **import-linter**, because it states the layer rule as a contract a reader can check without opening the measuring module, once the author settles which order is the rule (the report's or the YAML's, AUD-238); and **xenon** (or ruff's `C901` and `PLR0913`, which cost no dependency), because function complexity is the one axis the tree does not measure and the sample names twenty blocks a reviewer would want to know about. Both are pure or prebuilt and fit the dev group under CON-07.

**The prototype page.** `.claude/scripts/audit/architecture.py` writes `architecture.md` from the source, read-only: 191 modules, 63,024 lines, 1,214 module-to-module imports, 133 static subpackage edges and 25 string edges at `c1f60ca`; per subpackage its modules with lines, public names and first docstring line, the pipeline stages it registers (from `core/stages.py`: stage 9 in `pipeline/`, 1 to 8 and 10 to 12 where §5.2 puts them, two stages numbered 7 in `charge/`), its static edges in and out and its string references; then the diff of §5.1's table against the tree.

**The proposal**, each a `your call`: its home is a page the site generates beside `modularity-measurements.md`, from a script moved to `docs/scripts/` and run by `generate.py`, so that the page is always the tree's; and the rule that keeps §5.1 level with it is a Tier 1 guard in the architecture family (CON-12, VER-61, VER-65) that the set of `` `name/` `` rows in §5.1's table equals the set of subpackages, with the responsibility column left to the author. The alternative is the kept script and no guard, which is how the page would drift as §5.1's words have.

## 8. Fixed in this pull request

One `docs:` commit per category, the finding identifiers in each body, `chore:` for the scripts; each fix preserves meaning and is verifiable from the finding's evidence. The map category to commit is `raw/commits.tsv`; the checks re-run after the fixes are under `raw/after/`.

| Commit | Category | Findings |
|---|---|---|
| `808ca66` | scripts (chore) | AUD-01 (ORC-01): `clause.py` and `duplicates.py` read a ruling letter as the first cell's first token, so the eleven annotated rows resolve |
| `7f27f1f` | stale paths | AUD-02 (ORC-02), AUD-03 (ORC-03), AUD-93 (SPB-46), AUD-164 (KGE-13), AUD-297 (KST-17), AUD-271 (CLD-21) |
| `2bf8825` | stale names | AUD-15 (ORC-15), AUD-18 (SPA-03), AUD-133 (SPD-10), AUD-101 (SPC-06), AUD-80 (SPB-33), AUD-345 (KPH-18), AUD-369 (KPH-42), AUD-211 (KNU-18), AUD-282 (KST-02), AUD-283 (KST-03), AUD-284 (KST-04) |
| `210a591` | stale counts | AUD-16 (SPA-01), AUD-126 (SPD-03), AUD-127 (SPD-04), AUD-92 (SPB-45), AUD-198 (KNU-05), AUD-218 (KNU-25), AUD-299 (KST-19), AUD-233 (DOC-04), AUD-267 (CLD-17) |
| `0b26b9f` | citations | AUD-08 (ORC-08), AUD-104 (SPC-09), AUD-105 (SPC-10), AUD-79 (SPB-32), AUD-255 (CLD-05), AUD-258 (CLD-08), AUD-260 (CLD-10) |
| `d9c3eb5` | pointers | AUD-12 (ORC-12), AUD-120 (SPC-25), AUD-88 (SPB-41), AUD-275 (CLD-25) |
| `160cdb0` | dead tests | AUD-05 (ORC-05) |
| `65af23a` | front matter | AUD-06 (ORC-06) |
| `81c913a` | present tense | AUD-04 (ORC-04), AUD-09 (ORC-09), AUD-139 (SPD-16), AUD-288 (KST-08), AUD-291 (KST-11), AUD-269 (CLD-19), AUD-270 (CLD-20) |
| `4061c40` | indexes | AUD-10 (ORC-10) |

Of the 48, two are in the specification's normative text and change no requirement: FR-18 and FR-19 now list the registered model names in the case file's spelling (`epnp-ns`, `pnp-ns`, `pnp`, `poisson`, `pb`, `pb-linear`; the SHALL is the same), and VER-47's title says the v0.6 schema its text already checks. The rest are paths, counts, citations, pointers, tenses and the knowledge base's headers. No record was edited, no test was added or changed, nothing under `src/` changed, no dependency was added.

## 9. Your call

In the order to take them; each line stands alone, for the follow-up package to transcribe into a history record.

1. **Name each NOTE's clause** (AUD-48; section 5, P3). Run `uv run .claude/scripts/audit/migrate_note_labels.py` and commit. Recommended: forty label edits, no meaning changed, and `clause.py` then prints a clause with all of its NOTEs; the evidence is `raw/after/migrate-note-labels.log`.
2. **Fix the two script behaviours that remain** (AUD-11, AUD-13). `clause.py` ends a NOTE at its first blank line, so a NOTE whose equation stands in a fenced block prints cut mid-sentence; recommended: let a NOTE run to the next heading, NOTE or clause. §8.4.5 names one kept script where `CLAUDE.md` names three; recommended: §8.4.5 names all three, since it is the home of the rule.
3. **The decisions register's home and rule** (section 6). Recommended: a generated `docs/project/decisions.md`, the history index's *Where each ruling holds now* folded into it, `/np-plan` and `/np-ship` re-running the script in the commits that add a decision, and a Tier 1 guard that the page equals the tree.
4. **The index maintenance rule** (section 5, P1). The three indexes exist; nothing re-runs `index_records.py`. Recommended: `/np-plan wp` and `/np-ship` run it in the commit that adds a plan or a review, as they run `duplicates.py`; or, if that is one rule too many, delete the three indexes and let the directory listing serve.
5. **Do not archive the delivered plans** (section 5, P2). Recommended: leave them; the move breaks 74 record links and the strict build, and the index now carries each plan's status.
6. **The architecture page's home and rule** (section 7). Recommended: generate it on the site beside the modularity measurements, and guard §5.1's rows against the tree's subpackages at Tier 1.
7. **Adopt a complexity measure, or none** (section 7). Recommended: enable ruff's `C901` and `PLR0913` with thresholds set from the sample before adding a package; import-linter only after the layer order is settled (next item).
8. **Settle the layer order** (AUD-238, AUD-237). `docs/project/modularity.md` and `modularity-layering.yaml` give different orders, and the report's numbers are dated `97f2b3d` in the present tense. Recommended: the YAML's and the code's order is the rule; the report says its numbers are a record and points to the live page.
9. **CON-05's driver** (AUD-20). The clause says ionic strength; PHY-01 says the mean concentration. Recommended: CON-05 reads "one local mean concentration `⟨c⟩` (PHY-01)"; a wording fix of a normative clause, so yours.
10. **§5.1's diagram and the stage-9 row** (AUD-96, AUD-99, AUD-374). Recommended: redraw with stage 9 first and feeding every stage, give each stage row its registry name, and distinguish the two stages numbered 7.
11. **§5.3.1's worked example** (AUD-106). Recommended: comment out the lines that make it refused, as the example's `profile` and `pqr` lines already are, so a reader can copy it.
12. **§5.4.1 and ADR-001 on the thin interface** (AUD-107, 21, 108). Recommended: state H3's ruling, that the weak forms are written once against NGSolve and the interface is the shape a second backend would take.
13. **The guide's protonation order** (AUD-230). Recommended: say protonation runs before the density and that a pH change re-runs the density, the contour and the mesh, as WP5.03 made it.
14. **The changelog heading check in `/np-ship`** (AUD-251, 279). Recommended: the preflight names the `## [X.Y.Z-alpha.N]` heading `tag.yml` greps, and the five restatements of the changelog rule point at `CONTRIBUTING.md`; whether the eight Phase 5 entries under `## [Unreleased]` are moved is a changelog edit, a record, and so also yours.
15. **Five knowledge concepts that state a method or a rule wrongly** (AUD-281, 285, 339, 356, 152). Recommended: rewrite each as its finding proposes; AUD-339 matters most, because `knowledge/01` calls itself authoritative and describes the kernel PHY-17 forbids.
16. **The knowledge base's claim of authority** (AUD-90, 328). `knowledge/01/00` says it is the single source of truth for the equations; §4 is normative. Recommended: the overview says it backs §4 and §4 governs.
17. **The redundancy map as a rule** (section 4). Recommended: ratify "a rule's home is its clause, a measurement's home is its concept, the other points", and let the follow-up package apply the 48 rows, the §6 and §4 mirrors in `knowledge/06` and `knowledge/01` first.
18. **The sediment list** (section 4). Recommended: approve the 34 moves and deletions as listed, about 22,500 tokens off live paths; the two largest (AUD-113, the §5.3.1 NOTEs, and AUD-244, the Phase 5 plan's narratives) are the lane's files and wait for its pause.
19. **Fifteen `[verified]` claims with no footnote** (AUD-07). Recommended: each gets its footnote or is demoted to plain text, by `knowledge/00-orientation/04`.
20. **The eight `unchecked` findings** that rest on the ESI or the COMSOL report (section 3). Recommended: confirm or dismiss each against the source this session could not open.
21. **The remaining 250 medium and low findings** in `findings.md`, each with its proposed edit. Recommended: the follow-up package takes them directory by directory, in the register's order, applying each as the author marks it.

## 10. Dismissed

Twenty-two findings and thirty-one mechanical hits were dismissed; each keeps its number and its reason in `findings.md`, section *Dismissed*.

| Kind | Count | Reason |
|---|---|---|
| Duplicate of another finding | 18 | Two readers saw one defect (for example SPD-01 is ORC-02 and ORC-03; KPH-01 is SPB-43; KST-15 is ORC-06); the kept finding carries the extra location |
| A ruling in force | 1 | SPD-15 would trim the closed `OPN` rows, which history-prose-review H keeps until v1.0 |
| The hosted environment, not the tree | 2 | KNU-33 and KST-46: `git show <hash>` footnotes resolve in a full clone; the hosted clone is shallow (50 commits) |
| Partly fixed, the rest the author's | 1 | KST-24: its 07/08 line is ORC-09, fixed; its other passages state the renaming and the removal |
| Mechanical hits (probe false positives, records' own text, forms the convention describes, pre-existing environment warnings) | 31 | `raw/own-dismissals.md`: the `WP46`/`WP59` decision rows the probe misread (fixed in `probes.py`), the versions the shallow clone cannot see as tags, the closed `REV` items' measured paragraphs, the `VER-72` guard still in force, the `[tested: <test>]` form in the convention and the log, and the like |

## 11. How to pick this up in a new session

**The state.** This file; `CODE_REVIEW_039/findings.md` (every finding and its state), `redundancy-map.md`, `sediment.md`, `decisions.md`, `architecture.md`; `CODE_REVIEW_039/raw/`: `inventory.md`, `paths.md`, `links.md`, `probes.md`, `markers.md`, the clause-check and duplicates logs and the strict-build log at `a5039af`; `reader-{spa,spb,spc,spd,kge,knu,doc,cld,kst,kph}.md` (the ten readers' returns, verbatim), `walks-*.md` (the sixteen task walks), `own-findings.md` (ORC and WLK), `own-dismissals.md`, `dispositions.tsv` (each reader finding's state), `commits.tsv` (category to commit), `step8-fixes.md` (the edit list as applied), `survey/` (the package survey), and `after/` (every check re-run at `81c913a` or `86e647b`, and the two rehearsal logs).

**The scripts**, all under `.claude/scripts/audit/`, each deterministic and read-only unless it says otherwise, run as `uv run .claude/scripts/audit/<name>.py`: `scope.py` (the file sets), `inventory.py`, `paths.py`, `links.py --anchors`, `probes.py`, `markers.py`, `decisions.py` (writes `decisions.md`), `architecture.py --at <sha>` (writes `architecture.md`), `register.py --at <sha>` (writes `findings.md` from `raw/`), `maps.py <sha>` (writes the map and the list from `findings.md`), `index_records.py` (writes the three indexes), `migrate_plans_archive.py [--dry-run]` and `migrate_note_labels.py [--dry-run]` (the two moves; run them on a scratch branch), and `survey.sh` (the package survey, from scratch environments). The ten letters `clause.py` could not find are checked by the loop in `raw/after/clause-check.log`.

**To act on a decision.** Mark the finding's row in `raw/dispositions.tsv` (`fix:<category>`, `your call` or `dismissed <reason>`), apply the edit the finding proposes, add the commit to `raw/commits.tsv`, and re-run `register.py` and `maps.py` so `findings.md` carries the state. The follow-up package, if the author opens one, transcribes section 9 into a dated history record and takes the findings directory by directory.

**What this session could not do.** Open the ESI or the COMSOL model report (eight findings are `unchecked`); resolve `git show <hash>` footnotes on a shallow clone (two dismissals); edit a record, change a specification's meaning, move a file, or add a test or a dependency (none was done).
