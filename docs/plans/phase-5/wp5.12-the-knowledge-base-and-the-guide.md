# WP5.12 — The knowledge base and the guide

**Status: planned, not started.** Planned 9 November 2026, at `f8960d1`. Inherits §8.2.36 AL13 and AL15 to AL21, §8.2.37
AM13 to AM18 ruled at this plan and its review, CODE_REVIEW_039's register and its scripts in `.claude/scripts/audit/`, and
REV-226.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md), entry WP5.12. `SPECIFICATION.md` governs; an
identifier here is a pointer, never a restatement. Where the two disagree, this plan is wrong.

## In brief

**What changes.** The project's knowledge base and its user guide are corrected where the audit found them
adrift: about 160 passages. Five notes that state a method or a rule wrongly are rewritten, first one that
described a forbidden charge construction. Where a note repeats the
specification's equations or rules, it now points to them, so each rule is stated once. History and superseded
measurements leave the notes. Every claim marked as checked names its source; claims copied from the thesis
are checked against it or marked unverified. The guide says protonation runs before the density map and names
the features added since the last release. As you ruled, one physics test is tightened, three
ideas become an open item, and the site's dead register links wait for the guide package.

**Cost.** About three sessions and two to four hours of agent work, on the stronger model as you ruled; you act
about six times.

**What could go wrong.** A rewrite could change a statement's physics unnoticed: the physics reviewer reads those
edits, and the specification's requirements are counted before and after. A move could break a link or drop a
number: the link check, the strict site build and the claim-marker check would show it. Some refusal messages
change their wording: the unit tests run on that commit.

**Your call.** Six findings rest on the paper's supplementary information or the COMSOL model report, which the
agents cannot open: the session asks you all six in one round, with the section to look up; have
both to hand. Is the reviewed plan ready to approve? *Recommendation:* yes; you ruled each choice
that changes a meaning.

## Execution brief

**Scope.** The 164 findings of CODE_REVIEW_039 still `your call` at `f8960d1`, under AL13, AL15 to AL21 and AM13 to
AM18; REV-226; the register's states. **Depends on** WP5.11, merged (PR #173); WP5.13 follows in this lane.
**Pointers:** §4.6, §5.2, §6, §7.2 (VER-03, VER-54), §8.4.6, Appendix B; `knowledge/00-orientation/03` and `04`.
**Implementing session:** Opus at high effort, the main session only (AM17); the marker sweeps on Sonnet sub-agents, the heading levels on Haiku; the `physics-reviewer` reads items 2 and 3 before each commits. **Tests:**
one Tier 1 test is tightened (AM13); every other item is done when the code and review say so, with D9's counts.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1. The set | The 164 findings `your call` at `f8960d1`. All stand; AUD-07, 167, 235, 248, 300 and 308 in part, and only their remainder lands. One item per directory group (Grounding D1); in each, AL15's rewrite first (AUD-339, 356, 152, 281, 285), then AL17's §4 and §6 mirrors, then the rest | Ruled by the author (AL15, AL17, AL24). Decided by the plan: the grouping |
| D2. Meaning | An edit lands without asking when it makes the text agree with the code, a test, a clause, a ruling or the source it cites; removes history, a spent statement or a duplicate; or adds a pointer, title, description or marker. AM13 to AM15 are the meaning changes. Any other change to a SHALL, a number the code or a test reads, or a decision stops the item and goes to the author. Where a finding's edit conflicts with a ruling or offers two, Grounding D2 picks | Ruled by the author (AL21; AM13 to AM15). Decided by the plan: the test of meaning, as WP5.11's D2 |
| D3. Paths and data | No file is deleted, renamed or moved, and no anchor a link names changes (an explicit `{#id}` stays); a concept that would go is rewritten or reduced to a pointer. Nothing under `data/` changes: AUD-341's comment in the correction file waits as REV-230 | Decided by the plan: records link to concepts by path; the correction file's bytes key stage 8 (VER-62) |
| D4. Markers | A thesis transcription takes `[verified][^thesis]`, its `.tex` locator kept inline, only where the thesis clone supports it; otherwise it says "(unverified)". A `[tested:]` marker stays on the sentence its test asserts; a measured number the test does not assert takes `[verified]` with its record's footnote. `markers.py` skips code spans; each of AL19's fifteen gets its footnote, "by arithmetic" with its source, or plain text | Ruled by the author (AL19). Decided by the plan: `knowledge/00-orientation/03` and `04` |
| D5. The source checklist | Six rows, the findings that rest on the ESI or the COMSOL report (AUD-136, 225, 286, 327, 343, 346): REV-227, whose section is the checklist. Item 13 (AM18's item 11, renumbered when the checkpoints were added) asks the author all six in one round; a confirmed row's edit lands there; a row not yet checked stays in REV-227 to the phase close. AUD-226 and AUD-326 rest on git history: the session fetches it and records whether each hash resolves | Ruled by the author (AL20; AM16, six rows; AM18, one round at item 11, now 13) |
| D6. Code and tests | REV-226: a citation changes where its rule moved to §5.2's NOTEs on stages 1 and 2. AUD-216 and AUD-351 repoint two comments. AM13's target. Nothing else under `src/` or `tests/` | Ruled by the author (REV-226's acceptance; AM13) |
| D7. Open items | REV-226 `fixed`. New, each section at item 9's `###`: REV-227 (D5), `fixed` once each row has a verdict, else `open`; REV-228, the site links, `accepted`, WP5.21 (AM15); REV-229, the three ideas, `post-1.0` (AM14); REV-230, the correction file's comment, `open` until a package that changes that file is named | Ruled by the author (AM14, AM15). Decided by the plan: REV-230 |
| D8. The records | One commit per item, its AUD ids in the body. Item 15 adds one `wp512-<category>` disposition per finding and one commit row per category, re-runs `register.py` and `maps.py`, sets `holds-now.yaml`, re-runs `decisions.py`. Changelog `[0.6.0-alpha.12]` | Decided by the plan: as WP5.11's D6 |
| D9. The counts | 517 SHALLs before item 2 and after item 9. `markers.py`: no missing test, no unfootnoted claim, no `verified:` difference. `links.py --anchors`, `duplicates.py`, `decisions.py --check`, the strict build; `same_tree.py` at item 11 | Decided by the plan: a silent failure gets a count |

Nine decisions: three repeat WP5.11's; the markers, the checklist and the code are new.

### Grounding

**D1.**
- `docs/code_reviews/CODE_REVIEW_039/findings.md` (at `20fb8bc`): 164 `your call`. *Where* gives `a5039af`'s lines;
  locate by the quoted evidence. Surveyed at `f8960d1`: all stand. In part: AUD-07 (D4's fifteen); AUD-167 (04/10
  says "planar estimate", still "error at the gate"); AUD-235 (the `quantities` row is gone; the snippets are
  unmarked and differ from `physics/models.py`); AUD-248 (REV-170 has its design line; REV-217 to 221 have "Placed"
  and still "Open, to land after WP5.09"); AUD-300 (the yaml and `~/repos/pqr2grid` rows remain); AUD-308 (07/01
  "remarkably stable", 07/02 "GPL-ish", 07/04's MeshPy line and "mangled").
- Item 1: AUD-07. Item 2: AUD-73, 86, 90, 91, 95, 329, 331 to 333, 335 to 337, 339 to 341, 347 to 350, 352 to 355.
  Item 3: AUD-61 to 64, 94, 194 to 197, 199 to 202, 206, 210, 212 to 215, 217, 219 to 224, 227 to 229. Item 5:
  AUD-152 to 163, 166 to 193. Item 6: AUD-281, 285, 289, 290, 293, 294, 298, 300 to 303, 305 to 317, 319 to 323,
  325. Item 7: AUD-356 to 368, 370 to 372, 387. Item 9: AUD-14, 230 to 232, 234 to 236, 240 to 243, 248 to 250,
  384 to 386. Item 11: AUD-216, 351. Item 13: AUD-225, 286, 327, 343, 346.

**D2.**
- AL17 over a proposal: AUD-215's table stays in `06-linear-solvers.md` §6.1, which NUM-21's NOTE cites since WP5.11;
  the `09` `USE_*` repeat goes. AUD-168: §5.2's radius-band NOTE keeps its rule and points to `04/01`'s margins (2WCD
  +0.062 to +0.908 nm, the ensemble +0.170 to +0.916, against the NOTE's prototype +0.061/+0.908 and +0.173/+0.869).
  AUD-86, 340: the concept's errata renumber to §4.6's rows E1 to E6, E5 added; §4.6's Evidence cells link them.
- Numbers: AUD-73 `D_Na = 8.11 × 10⁻¹⁰` in §4.6 row 4 and the concept (`Electrolyte.diffusivity("Na+", 5.3, 50.0)` is
  8.1134e-10); AM13 also moves VER-03's row in `specification/07-verification/02-tier-1.md` and
  `knowledge/08-validation-benchmarks/01-…`'s `[tested:]` line, which both state `8.13 × 10⁻¹⁰` as the oracle, to
  `8.113 × 10⁻¹⁰`; AUD-341 "eq. 5.23" in §4.6 row 1 and the concept; AUD-302 VER-54's "1.25e-4", as
  `tests/tier2/test_mesh_backends.py`'s comment. Two figures that disagree (AUD-301): the one a test asserts, else
  the newest dated record's, labelled with its run.
- D3's rewrites: AUD-300 makes `07/07` the external sources and where they live (the thesis clone, the paper, the
  ESI, the author's COMSOL report, `pqr2grid` by pointer, AUD-290's COMSOL row); the yaml row goes. AUD-325 adds
  pointers. AUD-224 and 350 reduce `06/12` to a pointer. AUD-185's table moves into `05/13`, AUD-323's import
  sections into `07/09`, AUD-349's bullets into `08/02` §2.5.
- AUD-173: each `§n` becomes a relative link. AUD-199: reading order, every `{#…}` kept. AUD-200: retitled. AUD-249:
  only the level of the 110 `## REV-nn:` headings changes, to `###`, so no slug moves; `efficiency` joins the
  header's areas.
- AUD-368 and 371: the mutation list's inconsistency is stated as OPN-04's, which is open. AUD-357 and 192: the ideas
  go to REV-229; `02-09` becomes "Quantities the thesis computes", citing FR-23 and PHY-21. AUD-364's unsourced
  0.91 goes. AUD-14: REV-228, no edit. AUD-160: the frame as the WP20 plan states it; if it states none, the
  sentence drops the frame and says the test asserts bracketing only.

**D3.**
- `materials/stage.py` puts `file_hash(correction_source(...))`, the sha256 of the file's bytes, in stage 8's inputs.
- `knowledge/log.md` links concepts by path (`07/07` at line 117). `generate.py` writes the knowledge navigation from
  the front-matter titles, so a retitle rewrites `mkdocs.yml`.

**D4.**
- `markers.py` matches raw lines. Its 21 unfootnoted hits are AL19's fifteen (`04/13`:29; `07/02`:123; `07/03`:73,
  232; `07/04`:105; `07/05`:167, 193, 206, 246, 336; `07/08`:33, 64; `07/20`:37; `07/25`:95, a footnote carrying the
  marker; `08/07`:37) and six in code spans (`00/03`:19, `00/04`:32, `08/00`:17, `09/05`:31, `log.md`:44, 59).
  `log.md`:44 is its one missing test. `04/02`'s `verified:` lacks three `test_exclusion_shell.py` tests.
- `github.com/willemsk/phdthesis-text` is public and reachable (HEAD `43d0f0f`). The readers' claim tables
  (`raw/reader-kge.md`, `reader-kph.md`) give a verdict and line per claim.

**D5.**
- The readers' `unchecked` rows: KST-06 (AUD-286), KST-07 (AUD-287, a duplicate of AUD-136, whose inactive values
  WP5.11 marked), KST-47 (AUD-327), KPH-16 (AUD-343), KPH-19 (AUD-346), KNU-32 (AUD-225), KNU-33 (AUD-226) and KST-46
  (AUD-326), the last two dismissed on a shallow clone. Section 3's list (AUD-316, 371, 372) names rows that rest on
  neither source; they land in items 6 and 7.
- A REV row is `| REV-nn | area | severity | status | source | [title](review-items.md#anchor) |`, with its section;
  the highest is REV-226. Dispositions take `fix:<category>`, `your call` or `dismissed`, with a note.

**D6.**
- §5.3.1's NOTEs on `structure:` and `geometry.density` point stage 1's refusals and thresholds, and stage 2's radius
  set and union, to §5.2's NOTEs "stage 1, ingestion and alignment" and "stage 2, the kernel, the radius set and the
  union"; their other rules stay. Citing files: `structure/axis.py`, `structure/read.py`, `density/union.py`,
  `density/radii.py` and two `io/defaults.py` `CONFIGURATION_PATHS` reasons.
- `same_tree.py` drops docstrings and comments only, so a changed message or reason is a code difference. REV-226's
  acceptance expects `same_tree.py` to confirm a prose-only change, which it cannot for a string literal: item 11
  checks the message files by `git diff` instead, and its PR body says so. No code reads the reasons; no test matches
  the changed text.
- `test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit` asserts `8.13e-10` at `rel=3e-3`.

### Implementation details

Scratch directory `$S`: the session's scratchpad.

**Item 1.** In `markers.py`, blank each inline code span (`` `[^`\n]*` ``) and each line inside a fenced block before
matching `TESTED`, `VERIFIED` and `FOOTREF`, keeping line numbers. Then each of the fifteen takes the footnote of its
section (07/05's headings `[^wp14-plan]` or `[^wp15-plan]`, 07/08:33 and :64 `[^wp17-plan]`), "by arithmetic" with
its source, or plain text. `07/25`: the marker moves from the footnote to the three sentences citing `[^run]`.

**Item 2.** First count: `for f in SPECIFICATION.md specification/*.md specification/0*/*.md; do echo "$f $(grep -o SHALL "$f" | wc -l)"; done > $S/shall-before.txt`.
AUD-339 by its proposed edit, then AUD-90's overview text (AL16), then AUD-331 to 333 as pointers that keep headings
2.1 to 2.4, §3.0 and ε_r,f⁰ = 78.15. §4.6's Evidence cell n gives its arithmetic up for
`[En](../knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md#8-errata-in-the-source-with-the-arithmetic)`;
row 4 keeps its cap values, `D_Na` = 8.11 × 10⁻¹⁰ (AM13). AM13: the assertion reads
`pytest.approx(8.113e-10, rel=1e-3)`, and VER-03's row and `08/01`'s line read `8.113 × 10⁻¹⁰`. A moved fact keeps its marker and adds a `knowledge/log.md` line, here and at
items 3 to 7. Before the commit: `physics-reviewer` on `git diff`, then fix what it reports.

**Items 5 and 7, the marker sweeps.** `git clone --depth 1 https://github.com/willemsk/phdthesis-text $S/thesis`.
The sub-agent brief: for each thesis citation (04's `T`/`TA`/`E Lnnn`, 05's and 02's `.tex` labels, 03's labels),
read the cited lines; supported, the claim gains `[verified][^thesis]`; not found, "(unverified)"; the PlyAB SI and
`[std]` items, "(unverified)". Each file defines `[^thesis]` once, naming the clone's commit and the `T`, `TA`, `E`
files, and lists `thesis` under `sources:`. It returns the claims it marked "(unverified)". Main reads the diff.

**Item 9.** AUD-230 by its proposed edit, with `atoms: protonated` in stage 2's key line. Haiku:
`sed -i -E 's/^## (REV-[0-9]+:)/### \1/' docs/project/review-items.md`; done when `grep -c '^## REV-'` is 0 and
`links.py --anchors` reports what it did before.

**Item 11.** For each citation, grep the rule's sentence in §5.2 and §5.3.1 and cite the NOTE that holds it:
"section 5.2 NOTE on stage 1" or "on stage 2". Then `uv run .claude/scripts/same_tree.py HEAD`: it lists the files
whose messages or reasons changed, and no comment-only file; `git diff -U0 -- src/` shows only those citations.

**Item 13.** REV-227's section is a table `| Finding | The claim | What the audit found | Source to look up | Verdict |`,
one row each for AUD-136, 225, 286, 327, 343 and 346, the source section taken from the finding and `09/01`'s page
map. Then the round (AM18), as `.claude/workflow/author.md` says: two `AskUserQuestion` calls of three questions.
Each question gives the claim, what the audit found, the source section and the proposed edit; its options are
*Confirmed* (the edit lands), *Dismissed* (the text stays; for AUD-136, WP5.11's "(inactive)" marking is reverted)
and *Not checked yet*, none marked recommended, since the source decides. AUD-343 asks instead which source ruling
1's "running text" means: the ESI's `0.62e1`, the thesis's 6.2 nm⁻¹, or not checked yet; the finding's wording
follows the answer. The confirmed edits land in item 13's commit; the Verdict column records each answer and its
date. Then `git fetch --unshallow origin` and `git cat-file -e <hash>` for each hash
AUD-226 and AUD-326 name; their disposition notes record the result.

**Item 15.** A disposition: `KPH-12<TAB>fix:wp512-knowledge-01<TAB>WP5.12 item 2 (§8.2.36 AL15)<TAB>`. Categories:
1 `wp512-markers`, 2 `wp512-knowledge-01`, 3 `wp512-knowledge-06`, 5 `wp512-knowledge-04-05`, 6
`wp512-knowledge-07-09`, 7 `wp512-knowledge-00-03`, 9 `wp512-docs`, 11 `wp512-src`, 13 `wp512-checklist`. Item
13's rows take `fix:wp512-checklist` or `dismissed`, the verdict in the note; a row not yet checked, and AUD-14, stay
`your call`, the note naming REV-227 or REV-228. Then `register.py --at HEAD` and `maps.py HEAD`. `holds-now.yaml`:
AL13 the guide's three pages; AL15, AL18 and AL21 spent; AL16 `CLAUDE.md` and `01/00`; AL17 `00-orientation/04`,
which item 7 gives the rule; AL19 `00-orientation/03`; AL20, AM16 and AM18 `spent`, or `open: REV-227` while a row waits; AM13 §4.6, VER-03;
AM14 REV-229.

### Work items

- [x] c45fe94 1. `.claude/scripts/audit/markers.py`, the fifteen claims, `04/02`'s front matter (D4): AUD-07, AL19; done when
  `markers.py` lists no missing test, no unfootnoted claim and no `verified:` difference. **Executor:** main
- [x] 1d038bc 2. `knowledge/01-physics-epnpns/`, §4.6, VER-03's row, `knowledge/08-validation-benchmarks/01-…` and `02-…`
  §2.5, `tests/tier1/test_corrections.py` (D1, D2, D6): AUD-339 first, AL16, AL17's §4 mirrors, AM13; done when the test
  passes, §4's SHALLs are unchanged and the `physics-reviewer` reports nothing open. **Executor:** main
- [x] a6bad31 3. `knowledge/06-numerics-fem/` (D1, D2): AL17's §6 mirrors first; done when the code, review and the
  `physics-reviewer` say so. **Executor:** main
- [x] 4. Compaction checkpoint. **Executor:** main
- [x] b73667f 5. `knowledge/04-…`, `knowledge/05-…`, §5.2's radius-band NOTE (D1 to D4): AUD-152 first; done when the code
  and review say so and `markers.py` is clean. **Executor:** main; AUD-187 and 188's markers on `general-purpose`,
  Sonnet
- [x] 3905c6d 6. `knowledge/07-…`, `08-…`, `09-…`, VER-54 (D1 to D3): AUD-281 and 285 first; done when the code and review
  say so. **Executor:** main
- [x] 8b36b21 7. `knowledge/00-…`, `02-…`, `03-…`, `knowledge/index.md` (D1, D2, D4): AUD-356 first, AM14's text, AL17's rule
  in `00-orientation/04`, AUD-387 by its second option; done when `markers.py` is clean. **Executor:** main; AUD-365
  and 370's markers on `general-purpose`, Sonnet
- [x] 8. Compaction checkpoint. **Executor:** main
- [ ] 9. `docs/` (D1, D2): AUD-230 first (AL13); done when the strict build passes and D9's SHALL count is 517.
  **Executor:** main; AUD-249's levels on `general-purpose`, Haiku
- [ ] 10. Compaction checkpoint. **Executor:** main
- [ ] 11. `src/` (D6): REV-226, AUD-216, AUD-351; done when `same_tree.py` lists only the message files and the
  commit's gate passes. **Executor:** main
- [ ] 12. Compaction checkpoint. **Executor:** main
- [ ] 13. The source checklist (D5): REV-227 and its section, the author's round on the six (AM18), the confirmed
  edits, the two git rows; done when each row records its verdict or "not checked yet". **Executor:** main
- [ ] 14. Compaction checkpoint. **Executor:** main
- [ ] 15. The records (D7, D8): REV-226 `fixed`, REV-227 to REV-230, the register, `holds-now.yaml`, `decisions.py`,
  `CHANGELOG.md`; done when each finding reads `fixed` or names its REV row and `decisions.py --check` passes.
  **Executor:** main
- [ ] 16. Compaction checkpoint. **Executor:** main
- [ ] 17. The Outcome, both Status lines, `current.md`, the PR body; done when the code and review say so.
  **Executor:** main

The checkpoints 10, 12, 14 and 16 were added after item 8, at the author's request: one after each remaining item, the
last item followed by *Finishing*'s pause. Items 9 to 13 became 9, 11, 13, 15 and 17.

### Verification

| Test | Tier | Identifiers | Oracle | Tolerance | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit` | 1 | VER-03; PHY-12, PHY-13 | 8.113 × 10⁻¹⁰ m² s⁻¹, the governing coefficients' cap, VER-03's row | relative 10⁻³, its neighbours' (AM13) | `uv run pytest tests/tier1/test_corrections.py` |

No other test is in scope (§8.2.13 N1). The checks, at items 1, 2, 7, 9 and 12 and before the push:

```bash
uv run .claude/scripts/audit/markers.py
uv run .claude/scripts/links.py --anchors
uv run .claude/scripts/duplicates.py
uv run .claude/scripts/decisions.py --check
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

with D9's SHALL count and item 11's `same_tree.py`.

### Out of scope

- REV-227's verdicts, the author's; REV-228, WP5.21; REV-229, after v1.0; REV-230, the next change to the correction
  file.
- WP5.13: §5.3.1's `models:` and `variables:` NOTEs (AL23). Any change under `data/`, and under `src/` or `tests/`
  beyond D6.

### Open questions

None blocks the work. REV-227's verdicts come when the author has read the sources; the package does not wait.
