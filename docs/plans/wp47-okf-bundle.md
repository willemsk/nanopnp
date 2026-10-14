# WP47 — The knowledge base as an OKF bundle

**Status: planned, not started**, 14 October 2026. Inherits WP46 as delivered (the tree it is written
against), WP45's prose rule (§8.2.11 L4) and the input note `okf-knowledge-bundle.md` (K1 to K11).

The Phase 4 plan owns the phase ([phase plan](phase-4-polish-and-user-testing.md), *OKF bundle and
checks*). `SPECIFICATION.md` governs; identifiers are pointers. The author's rulings of today on the
note's open questions 3 to 7 are written into §8.2.7 (G12) and VER-68 into Appendix A, in this plan's
commit.

## In brief

The reference notes that every session reads first are ten long files. This package cuts them into
about a hundred and ten short pages, one idea each, in a folder per file, and gives every page a small
header saying what kind of page it is and where its claims come from. Every pointer to the notes, in
the code, plans and history, is rewritten to the new address.

**What changes.** A new automatic check refuses a page with a broken header, a pointer to nothing, a
claim that names a test that does not exist, and a trust list that disagrees with the claims. Claims
that no test yet backs are marked as waiting, in a list that may only shrink; the next package
empties it.

**Cost.** About ten commits, mostly mechanical moves checked by machine; a day or two of machine time.

**What could go wrong.** A pointer could reach the wrong page; the check proves it resolves, not that it is right, so ambiguous pointers are listed for a person to rule on. A sentence could be lost in the cut; the words are compared before and after. The log could go stale; nothing can check that.

**Your call.** Your four rulings are written in. For the log, I read "transfer current history" as
the dated events the notes already record, with git keeping every earlier edit. *Recommendation:*
keep that reading; a copy of the whole git history would only duplicate it.

## Execution brief

Scope: the bundle, the citation rewrite, VER-68 with G3's ratchet, the documentation build. Depends on
WP46 as delivered. Amended here: §8.2.6 F6 ("collected"), §8.2.7 G12, Appendix A VER-68, and at item 9
the §11 NOTE. The detail behind D1 to D6 is in [the converter rules](okf-converter-rules.md), a
companion the plan's length cap keeps outside it. Models (`CLAUDE.md`): Sonnet by default; scripts, not
models, move text in items 2 to 5; one Haiku worker per file for item 6's headers; the parent commits;
Opus only after Sonnet fails.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Layout | `.knowledge/index.md` (root; `okf_version: "0.2"`) and a directory per file, `NN-slug/`, with its own `index.md`. One concept per `##`, named `NN-heading-slug.md`; `###` and deeper stay headings. The text before a file's first `##` is `00-overview.md`. `00-index.md` goes: its traps, conventions, provenance, rulings and open items become concepts under `00-orientation/`. A heading carrying a marker gets an explicit `{#id}` | K1, K2; G12. All prose is in a concept with a header. Markers in headings would change anchors at item 6 and again in WP48 |
| D2 Header | `type` from a closed list committed in the check, `title`, `description`, `tags`, `sources` (ids `thesis`, `paper`, `esi`, `comsol-report`, footnoted where a sentence already names one), `generated.by: claude-code/<installed nanopnp version>`, never a model identifier, and `verified` | K9, K10; G12. Rule 6 refuses a footnote that is no source id |
| D3 Ledger | A bare `[tested]` becomes `[tested: pending]` or, where the named test exists, `[tested: tests/…]`; an executable `[verified]` becomes pending, a source reading stays `[verified]` with a footnote. `.knowledge/pending.yaml` counts both kinds per concept and must equal the files; the ceiling is a constant in the test, set at item 6. A concept's `verified` set is defined in the rules. `tested_with` is checked, carried by no concept until WP48 | K5 to K8; G3, G8 |
| D4 Citations | A one-off converter, not committed, rewrites every form in the rules (section, line, label, named section, whole file, link, URL) to a bundle path, and lists what it cannot place for Sonnet or the author; none is guessed. History is rewritten too | K3, K4. A wrong target passes the check |
| D5 Check | `nanopnp.validation.okf` reads files and syntax trees and imports no checked module; its slug function is tested against the docs build's. `tests/tier1/test_okf_bundle.py` is VER-68. A word-for-word comparison of the joined bodies against the ten old files runs once at item 2, its result in the commit message | F6; VER-68 |
| D6 Site and gate | `generate.py` recurses; `mkdocs.yml` gets `not_in_nav` and one entry; `prose-only.sh` treats `.knowledge/` and any Markdown containing `.knowledge/` as not prose; `log.md` holds one dated entry per event the notes already record | G12; the review of this plan |

### Work items

- [x] a0cf1a4 1. `src/nanopnp/validation/okf.py`, `tests/tier1/test_okf_bundle.py`, `.github/scripts/prose-only.sh`, `tests/tier1/test_workflow_hooks.py` (D5, D6): the check on constructed bundles, and the prose rule with a case each; done when those rows pass.
- [ ] 2. `.knowledge/` (D1): move the ten files into the bundle, bodies unchanged, a placeholder header and explicit ids; done when the word-for-word comparison is clean.
- [ ] 3. `.knowledge/` (D4): rewrite the citations between concepts; done when the checker, run by hand through `uv run`, resolves each and the unplaced list is empty by ruling.
- [ ] 4. every tracked file outside `.knowledge/`, `docs/plans/`, `docs/code_reviews/` and `CHANGELOG.md` (D4): the same; done by the same hand run.
- [ ] 5. `docs/plans/`, `docs/code_reviews/`, released `CHANGELOG.md` sections (D4, K4); adds `test_ver68_repository_citations_all_resolve`; done when it and `test_plan_shape.py` pass.

*Compaction checkpoint: after item 5; resume from this plan and `git log`.*

- [ ] 6. `.knowledge/` (D2, D3): real headers, markers, footnotes, `verified` sets, `pending.yaml`, the ceiling, the counts in an Outcome; done when the ledger rows pass.
- [ ] 7. `.knowledge/index.md`, `00-orientation/`, `log.md` (D1, D6); adds `test_ver68_the_bundle_conforms`; done when it passes.
- [ ] 8. `docs/scripts/generate.py`, `mkdocs.yml` (D6); done when `uv run docs/scripts/generate.py && uv run mkdocs build --strict` passes.
- [ ] 9. `CLAUDE.md`, `.claude/skills/`, `.claude/rules/`, `README.md`, `SPECIFICATION.md` §11: the new first read, the maintenance rule (a durable fact is a concept with a log line), the pending figure; done when VER-68 and the build pass.

*Compaction checkpoint: after item 9; then the push gate and `/wp-implement`'s PR.*

### Verification

Tier 1; command `uv run pytest tests/tier1/test_okf_bundle.py tests/tier1/test_workflow_hooks.py`, then
`.claude/hooks/gate.sh run`. Each refusal has its own otherwise valid constructed bundle.

| Test | Identifiers | Oracle |
|---|---|---|
| `test_ver68_` `concept_without_type_or_frontmatter`, `type_outside_the_list`, `undeclared_okf_version`, `root_index_missing_a_directory`, `directory_index_missing_a_concept`, `log_out_of_form` `_is_refused` | VER-68 (1) | Each names its file; a valid bundle gives no finding |
| `…citation_to_missing_concept_or_heading_is_refused`, `…legacy_section_form_is_refused`, `…slug_matches_the_docs_build` | VER-68 (2) | Each failure named; the slug on punctuation, accents and a repeat equals `markdown`'s when importable; a placeholder in a code span passes |
| `…tested_marker_naming_no_test_is_refused`, `…bare_tested_marker_is_refused`, `…class_test_name_resolves` | VER-68 (3) | Absent name and bare marker at their lines; `pending` and `Class::test` accepted |
| `…verified_set_must_equal_inline_tests_arithmetic_and_ruling` | VER-68 (4) | An extra and a missing entry each fail |
| `…tested_with_older_than_lock_is_refused` | VER-68 (5) | Older fails, equal passes, an absent package is named |
| `…footnote_without_source_is_refused` | VER-68 (6) | Unknown label fails |
| `…pending_count_must_equal_the_committed_list`, `…ceiling` | VER-68, G3 | One more or fewer fails; above the ceiling fails |
| `…repository_citations_all_resolve`, `…the_bundle_conforms` | VER-68 | The real tree: no finding |
| `test_prose_only_` cases for `.knowledge/x.md`, a `CHANGELOG.md` and `README.md` containing a citation, one without | — | Not prose, not prose, prose |
| VER-45 | docs | `--strict` passes; no code path changes, VER-62 untouched |

### Out of scope

The backfill and `tested_with` (WP48); the protocol (WP49); rewriting any claim's content.

### Open questions

None blocking. The `log.md` reading (In brief) defaults to the dated events unless ruled.
