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

Scope: the bundle, the citation rewrite, the F6 check as VER-68 with G3's ratchet, the documentation
build. Not the backfill (WP48). Depends on WP46 as delivered. Clauses amended here: §8.2.7 G12,
Appendix A VER-68, and at item 9 the §11 NOTE. Models (`CLAUDE.md`): Sonnet throughout; Haiku for items
2 to 5; Opus only after Sonnet fails on an item.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Layout | `.knowledge/index.md` (root; `okf_version: "0.2"`, lists every directory) and a directory per file, `NN-slug/`, with its own `index.md` listing its concepts. One concept file per `##`, named `NN-heading-slug.md` by the section number, unnumbered sections taking the next numbers; `###` and deeper stay headings inside it. The text before a file's first `##` is `00-overview.md`, type Overview. `00-index.md` goes: its table is the listing, and its traps, conventions, provenance, author rulings and still-open items become concepts under `00-orientation/` | K1, K2; G12. A sentence outside a concept escapes every check, so one rule holds: all prose is in a concept with a header |
| D2 Header | `type` (a closed list committed in the check: Overview, Orientation, Physics, Erratum, Author Ruling, Numerics, Library Behaviour, Benchmark, Reference Settings, Background, Biology, Geometry and Charge, Test Evidence), `title`, `description`, `tags`, `sources`, `generated` (`by: claude-code/<version read from the installed distribution>`, never a model identifier), `verified`. `sources` carry stable ids `thesis`, `paper`, `esi`, `comsol-report`, cited by footnote only where the sentence already names the source; no attribution is invented | K9, K10; G12. Rule 6 refuses a footnote that is no `sources[].id` |
| D3 Ledger | A bare `[tested]` becomes `[tested: pending]`, a bare `[verified]` stays with its footnote under `process:arithmetic`; the four claims that name a test become `[tested: tests/…::test_…]`. `.knowledge/pending.yaml` counts pending claims per concept; the check demands equality with the files and a total no larger than the figure recorded at this package's close. `tested_with` is checked against `uv.lock` but no concept carries it yet: it is WP48's, set when its test passes | K5 to K8; G3, G8. A count per concept survives edits that move a sentence |
| D4 Citations | A one-off converter, not committed, rewrites each `.knowledge/0N §x` form (also `section x`, and the `§x` between notes) to a bundle path, and a `###` or deeper address to the concept plus that heading's slug. Citations in released `CHANGELOG.md` sections, delivered plans and code reviews are rewritten too. The converter lists each address it cannot place, and none is guessed; the check then proves every path and heading exists | K3, K4. A wrong target is worse than a failing check |
| D5 Check | `nanopnp.validation.okf` reads the bundle from the files, imports no checked module, and `tests/tier1/test_okf_bundle.py` is VER-68. A test named in a claim is found by reading `test_*.py` under `tests/` as syntax trees, as VER-72 reads the source; the F6 wording "collected" is amended to that. A word-for-word comparison of every concept body, joined, against the ten old files, is run once at item 2 and its result recorded in the commit message | F6; VER-68. Reading trees avoids importing the stack on every commit |
| D6 Site and gate | `docs/scripts/generate.py` recurses over the bundle; `mkdocs.yml` carries one Knowledge entry and the generated `index.md` lists every page from the bundle's indexes; headers are page metadata. `prose-only.sh` stops treating `.knowledge/` as prose, so an edit there runs the check. `log.md` follows OKF's form, one dated entry per event the notes already record (the August 2026 verification, the author's rulings, the errata), the rest in git | K1; G12 for `log.md`. The change to `prose-only.sh` stops a knowledge-only edit skipping VER-68 |

### Work items

- [ ] 1. `src/nanopnp/validation/okf.py`, `tests/tier1/test_okf_bundle.py` (D5): the check, each refusal shown on a constructed bundle (D2, D3); done when the *Verification* rows on constructed bundles pass.
- [ ] 2. `.knowledge/` (D1): move the ten files into the bundle, bodies unchanged, a placeholder header on each concept; done when the word-for-word comparison is clean and the layout test passes.
- [ ] 3. `.knowledge/` (D4): rewrite the citations between concepts; done when each resolves and the converter's unplaced list is empty by ruling.
- [ ] 4. `src/`, `tests/`, `.claude/`, `.github/`, `docs/` outside `plans/`, `examples/`, `data/`, `CLAUDE.md`, `SPECIFICATION.md` (D4): rewrite those citations; done when the repository-wide resolution test passes.
- [ ] 5. `docs/plans/`, `docs/code_reviews/`, `CHANGELOG.md` released sections (D4, K4): rewrite the history; done when the same test passes and `test_plan_shape.py` still passes.

*Compaction checkpoint: after item 5; resume from this plan and `git log`.*

- [ ] 6. `.knowledge/` (D2, D3): real headers, `[tested: pending]` and `[verified]` markers, footnotes where a source is named, each concept's `verified` list, `.knowledge/pending.yaml`; done when the real-bundle test passes.
- [ ] 7. `.knowledge/index.md`, `.knowledge/00-orientation/`, `.knowledge/log.md` (D1, D6); done when every directory index lists its concepts and the check passes.
- [ ] 8. `docs/scripts/generate.py`, `mkdocs.yml`, `.github/scripts/prose-only.sh` (D6); done when `uv run docs/scripts/generate.py && uv run mkdocs build --strict` passes and a knowledge-only path is not prose.
- [ ] 9. `CLAUDE.md`, `.claude/skills/`, `.claude/rules/`, `SPECIFICATION.md` §11 NOTE and the §11 table: the new first read, the maintenance rule (a durable fact is a concept, with a log line), the pending figure; done when VER-68 and the docs build pass.

*Compaction checkpoint: after item 9; then the push gate and `/wp-implement`'s PR.*

### Verification

Tier 1; command `uv run pytest tests/tier1/test_okf_bundle.py`, then `.claude/hooks/gate.sh run`. Each
refusal has its own otherwise valid constructed bundle.

| Test | Identifiers | Oracle and tolerance |
|---|---|---|
| `test_ver68_concept_without_type_or_frontmatter_is_refused`, `…_type_outside_the_list_is_refused`, `…_reserved_files_out_of_form_are_refused`, `…_undeclared_okf_version_is_refused` | VER-68 (1) | Each names its file; a valid bundle gives no finding |
| `test_ver68_citation_to_missing_concept_or_heading_is_refused` | VER-68 (2) | Both failures named; the slug rule equals the one the docs build uses, on a heading with punctuation |
| `test_ver68_tested_marker_naming_no_test_is_refused`, `…_bare_tested_marker_is_refused` | VER-68 (3) | A name absent from the trees, and a bare marker, each at its line; `pending` is accepted |
| `test_ver68_verified_list_must_equal_inline_tests` | VER-68 (4) | An extra and a missing entry each fail |
| `test_ver68_tested_with_older_than_lock_is_refused` | VER-68 (5) | Older fails, equal passes, an absent package is named |
| `test_ver68_footnote_without_source_is_refused` | VER-68 (6) | Unknown label fails, known passes |
| `test_ver68_pending_count_must_equal_the_committed_list` and `…_ceiling` | VER-68, G3 | One more or one fewer fails; a total above the ceiling fails |
| `test_ver68_repository_citations_all_resolve` | VER-68 (2) | Every `.knowledge/` address in the tracked files resolves; zero legacy `§` forms remain |
| `test_ver68_the_bundle_conforms` | VER-68 | The real bundle: no finding |
| VER-45 | docs | The documentation build passes `--strict`; VER-62 is not touched, no code path changes |

### Out of scope

The backfill and `tested_with` (WP48, which empties `pending.yaml`); the protocol (WP49);
rewriting any claim's content.

### Open questions

None blocking. The `log.md` reading (In brief) defaults to the dated events unless ruled.
