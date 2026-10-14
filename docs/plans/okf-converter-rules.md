# WP47 — converter, ledger and gate rules

**Status: planned, 14 October 2026.** The detail behind D1 to D6 of [WP47](wp47-okf-bundle.md),
written after an independent review of that plan. It is not a plan and not normative:
`SPECIFICATION.md` (G12, VER-68) governs, and where this note and the plan disagree the plan governs.
It is held outside the plan because VER-72 (g) caps the plan's length.

## 1. Anchors

A heading that carries a marker (`### 2.3 … **[tested]**`; 60 of them today, in files 04, 06, 07 and
08) gets an explicit id, `{#slug}`, in item 2, computed from the heading text without the marker. The
`attr_list` extension is on. A citation's anchor is the explicit id when one exists, otherwise the
slug of the heading text. The slug function is the table-of-contents one: NFKD, ASCII-fold, drop
characters other than word characters, spaces and hyphens, hyphenate spaces, and suffix `_1`, `_2`
for a repeat. It is reimplemented in `okf.py`, since `markdown` is only in the docs group, and a test
compares it with `markdown.extensions.toc.slugify` when that is importable. The input note's example
`#22-quadrature` is wrong: the heading reads *2.2 Quadrature — verified experimentally*.

## 2. Citation forms the converter handles

| Form | Rewritten to |
|---|---|
| `knowledge/0N §x`, `knowledge/0N section x`, `knowledge/0N-slug.md §x`, `§x` between notes | The concept holding section x, plus the slug of the deepest heading that exists; a third-level address with no heading goes to the concept |
| Line reference, `knowledge/0N-slug.md:LINE` | The concept holding that line of the old file, no line number; a line past the end of the file is listed |
| Label, `knowledge/0N LABEL` | The heading whose text carries the label; listed if none or several |
| Named section, "Tier-3 evidence" | The concept whose title matches; listed if several |
| Whole file, `knowledge/0N.`, `knowledge/0N-slug.md is normative` | The directory's `index.md`; bare `knowledge/` the root `index.md` |
| Relative Markdown link, `../../knowledge/0N-slug.md#x` | The relative path of the concept, with its anchor |
| The GitHub URL in `.github/ISSUE_TEMPLATE/config.yml` | The blob URL of `knowledge/index.md` |
| Placeholders, `knowledge/0N §x` (a letter, not a digit) | Left alone; the check ignores a placeholder in a code span or the constructed bundles of its own tests |

Everything the converter cannot place is written to a list for Sonnet or the author. Nothing is
guessed. A wrong target passes the check, which proves existence and not intent, so the list is read
by a person before item 3 is committed.

## 3. The ledger

- A concept's `verified` set is exactly: one `process:<test node id>` per distinct inline test, plus
  `process:arithmetic` if it holds a `[verified]` claim, plus `human:willemsk` if its type is Author
  Ruling. The check demands equality.
- A test node id is `tests/tier1/test_x.py::test_name` or `…::Class::test_name`, resolved from the
  syntax trees of `test_*.py`. A parameter id is not part of it.
- `[tested, verified]` becomes `[tested: …]`; tested subsumes verified.
- A `[verified]` claim whose arithmetic can be executed becomes `[tested: pending]` (G8). One that is a
  reading of a source or a conversion of a printed figure stays `[verified]` and needs a footnote to
  one of the four sources; where the sentence names none, it is counted as `verified_unsourced`.
- `knowledge/pending.yaml` holds, per concept path, `tested_pending` and `verified_unsourced`. The
  check demands equality with the files. Its ceiling is a constant in `test_okf_bundle.py`, set at
  item 6 to the total measured then, and lowered by edit as WP48 backs claims. About 180 lines of the
  notes already name a test; where the named test exists in the trees the claim becomes
  `[tested: tests/…]`, otherwise pending. The counts are stated in item 6's Outcome.
- `generated.by` is `claude-code/<the installed nanopnp version>` (K9; the version is a git tag, §2.7).
  A model identifier (`claude-opus…`, `claude-sonnet…`, `claude-haiku…`, `claude-fable…`) is refused.
- Version comparison for `tested_with` parses dotted integers; `packaging` is not a dependency.

## 4. Gate and CI

- `.github/scripts/prose-only.sh` treats a path as not prose if it is under `knowledge/`, or is
  Markdown whose text contains `knowledge/` (read if the file exists; a deleted path stays prose).
  A prose-only edit that adds a bad citation therefore runs VER-68, in the commit hook and in CI's
  `changes` job. A case for each goes into `tests/tier1/test_workflow_hooks.py`.
- Item order and the commit hook: a commit touching only Markdown runs ruff alone unless the rule
  above applies, so the real-repository tests are added when they can pass, and the Markdown-only
  items are checked by running the checker through `uv run` by hand.
- `mkdocs.yml` has `validation.nav.omitted_files: warn`, which `--strict` makes an error. Item 8 adds
  `not_in_nav: _generated/model/knowledge/` so the pages the generated index lists need no entry.
- `log.md`: OKF's reserved-file text is read from the canonical repository at item 7 and governs. Until
  then the form is `# Log` then `## YYYY-MM-DD` entries, newest first, each non-empty.
- A new `src/nanopnp/validation/okf.py` imports only the standard library and `yaml`, so
  `modularity-layering.yaml` gains no edge; VER-72 and VER-75 apply to it.
