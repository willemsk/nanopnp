# Code review: PR 123, WP52's specification and plans split

22 October 2026 · `a201d92..8d7f7ad` (`claude/brave-thompson-e3mlxz`) · scope: the pull request's diff ·
focus: correctness, convention · effort: xhigh, with `--fix` · status: completed

## Summary

The review found one high-severity defect: the site served the bundle's index in place of
`SPECIFICATION.md`, because both pages took the same URL and MkDocs overwrote one with the other
without a warning, so the strict build passed. `clause.py` truncated a section that runs past the end
of its file (§5.3, §8.2), and it never resolved `PHY-nn` or `NUM-nn`, which the new map sends readers
to it for. The rest are gaps in the documents and small cleanups. Eleven findings are fixed in the
working tree, uncommitted; four are left to `/wp-ship` and the author.

After the fixes, at `8d7f7ad` plus the working tree: R10 (a) `missing: 0`; R10 (b) over the same 268
identifiers, `differing: 0`, plus 58 `PHY-nn` and `NUM-nn` identifiers newly resolved; the strict
documentation build passes (202 pages); `ruff check`, `ruff format --check` and `mypy --strict` pass
on both changed scripts. No test was added or run, and the push gate was not run.

| Severity | Count |
|---|---:|
| High | 1 |
| Medium | 4 |
| Low | 10 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `docs/scripts/generate.py` `_copies`; `mkdocs.yml` | `model/specification.md` and `model/specification/index.md` are both served at `_generated/model/specification/`. MkDocs checks for colliding output paths only within one directory, so it gave no warning. The bundle's index, written second, replaced the entry point, and every link to "the specification" (`docs/model/index.md`, the guide) showed the bundle's index instead. Reproduced on MkDocs 1.6.1. | Fixed: the bundle's root index is copied to `model/specification/contents.md`, and the navigation entry points there. Both pages now render. |
| 2 | `docs/scripts/generate.py` `rewrite_links` | A link whose label is an inline code span, such as ``[`specification/`](specification/index.md)``, was never rewritten, because code spans were split out before the link pattern ran. The three in `SPECIFICATION.md` resolved only because the copy mirrors the source tree. Finding 1's fix showed the gap (strict build: target not found). | Fixed: code spans are masked, not split, so a code label stays inside its link. Over every copied page, the only output that changes is that one link. |
| 3 | `.claude/scripts/clause.py` `_definitions` | A section that continued into later files was cut at the end of its own file. `§5.3` lost §5.3.2 to §5.3.4, and `§8.2` printed the stub and the Phase 0 criteria but not §8.2.1 to §8.2.16. Before the split, both printed the whole section. | Fixed: a section that reaches the end of its file continues into the following files while their first heading is deeper. `§5.3` now prints the same 722 non-blank lines as at the base; `§8.2` prints those plus the stub. |
| 4 | `.claude/scripts/clause.py` `_definitions` | `**PHY-nn.**` and `**NUM-nn.**` definitions are paragraphs, not headings or table rows, so `clause.py PHY-11` exited 1 with "no definition". The new entry point lists `PHY-nn` and `NUM-nn` in its identifier map and sends readers to `clause.py`. The gap predates this PR, in the function it rewrote. | Fixed: a line starting `**<id>.**` defines the identifier, up to the next heading, NOTE or definition paragraph. All 24 `PHY-` and 34 `NUM-` identifiers resolve. |
| 5 | `.claude/skills/phase-plan/SKILL.md`; `docs/plans/current.md` | Until WP53, the skills still write a ruling into `SPECIFICATION.md` §8.2. That file is now the map: `clause.py` does not search it, and a new `history/` file is not in the static navigation. The interim rule (a new `history/` file, rules into §8.4) was stated only in the WP52 plan's *Out of scope* and the PR body, and no session reads either. | Fixed in part: `current.md`, which every planning session reads, now states the interim rule. The skills are WP53's (§8.2.16 R5). |
| 6 | `mkdocs.yml` (altitude) | The specification's navigation is listed by hand, 52 pages, while the knowledge base's is generated from its index pages. Any page added to `specification/` fails the strict build until someone lists it by hand. Under the interim rule, every amendment adds one. | Not fixed: plan D5 chose a static listing so that `src/` stays untouched. Suggested later fix: generate this navigation the way `okf.navigation` generates the knowledge base's, with the title and log as parameters. |
| 7 | `.claude/scripts/clause.py` `clause` | Each identifier re-read and re-split every bundle file; the old script read the file once in `main`. | Fixed: `main` reads the bundle once and passes it to `clause`. |
| 8 | `specification/08-implementation-plan/04-development-process.md` §8.4.4 | "One work package makes one pull request, green on Tiers 1 and 2 before the next package starts … a fresh session" cited only L7, which says neither. R3 says §8.4 restates rulings and adds none. | Fixed: the sources are now L7, R5 (separate sessions) and `CLAUDE.md` (one PR, green before the next). The §8.4 preamble allows a file as a source. |
| 9 | `docs/plans/current.md` | Cited §8.4.4 for "`/plan`, `/implement`, `/ship` with levels are WP53's, and WP54's scope is open". §8.4.4 says neither; the history index marks R5 and R8 `open`. | Fixed: cites §8.2.16 R5 and R8, both open. |
| 10 | `specification/index.md` | The root index listed every subsection file but not the three directory indexes. §7's introduction, the normative split between verification (VER) and validation (VAL), was reachable only from the navigation and the map. | Fixed: entries for §5, §7 and §8 added. |
| 11 | `specification/history/index.md` | "`clause.py <ruling>` prints a ruling's row after its clause". With a ruling as argument, the script prints the row as the definition, and no clause. | Fixed: it now says the script prints a clause and, after it, every ruling row that names it. |
| 12 | `.claude/scripts/clause.py` | Two tests for "this file is history": `startswith("history/")` in the sort key and `"history" in parts` in `clause`. | Fixed: one `_in_history`. |
| 13 | `src/nanopnp/validation/modularity.py` `requirement_releases` | The docstring says the argument is "The text of `SPECIFICATION.md`". The FR rows are now in `specification/03-requirements.md`, so the text of the entry point returns `{}` without error. The function has no caller. | Not fixed: R2 keeps `src/` untouched in WP52. For `/wp-ship` to record or fix. |
| 14 | `CLAUDE.md` | R2 lists `CLAUDE.md` as changed in WP52, but only identifier citations changed. *Before doing anything* still says `SPECIFICATION.md` is normative, without the bundle, and *Project structure* does not list `specification/`. | Not fixed: a review pass does not edit `CLAUDE.md` on an agent's instruction. For `/wp-ship` or the author. |
| 15 | `specification/**/*.md`; §8.4's front matter | 42 sliced files end in a blank line before the final newline, against the plan's "one final newline". §8.4's description is 27 words, against the 25-word cap. Cosmetic: R10 drops blank lines. | Not fixed: whitespace churn over 42 verbatim slices. |

## Verified and found clean

- `phase-4-record.md` is the base plan verbatim under its header (`diff` empty).
- The navigation lists exactly the 52 files of `specification/`.
- The guide's repointed anchors resolve under the strict build's anchor validation.
- No repository file links to an anchor in the old `SPECIFICATION.md`, and no code reads its text.
- §8.4's rules were checked against E5, G7, G11, H12, J5, J6, J9, L2 to L4, L6, L7, L9, L10, N1, N4,
  N5, Q1 and R3 to R11. Apart from finding 8, each rule restates its ruling.

## Not run

The push gate, the test suites and `--nightly` (the review pass's instructions). `/wp-ship` gates
the fixes.

## Disposition (`/wp-ship`)

All eleven applied fixes were read and accepted. Of the four left open: `CLAUDE.md` now names the
bundle and `specification/`; `requirement_releases`' docstring names `specification/03-requirements.md`;
the trailing blank lines of 41 sliced files and §8.4's 27-word description are trimmed. The
hand-listed navigation is REV-124, open.
