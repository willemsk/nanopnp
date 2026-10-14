# WP45 — The prose strip

**Status: planned, not started**, 13 October 2026. Inherits WP44's loop and the prose rule it wrote
(§8.2.11 L4); the trial of a fresh worker per item (L9). Tag `v0.5.0-alpha.11`.

The Phase 4 plan owns the phase ([phase plan](phase-4-polish-and-user-testing.md), *WP45*).
`SPECIFICATION.md` governs; identifiers are pointers. This plan follows L7: under 1,500 words, six
decisions, no per-item design, no planned tests.

## In brief

A third of the program's source and a fifth of its tests are explanation rather than code. This
package cuts that to what the written rule allows, without changing a single instruction the
computer runs, and proves so by machine for every file.

**What changes.** Files get shorter and easier to scan. Explanations a reader needs stay where the
rules keep them: on the parts other people call, in the specification and in the knowledge base.
A fact found nowhere else is moved there, not deleted. A new check stops the prose growing back.

**Cost.** About twenty-eight small steps, each handed to a fresh helper so the main session stays
small; roughly a day of machine time, mostly the automatic checks after each step. You compare
this package's cost with the last one's and decide whether later packages work this way.

**What could go wrong.** A helper could drop a source for a physical constant or a fact recorded
nowhere else; the review and your read of the change would show it. A helper could change code; the
machine check refuses that step, which is then redone. The shares could stay above the predicted
targets; the close reports them by area and you rule.

**Your call.** About four hundred tests name their requirement only in their explanation. Keep that
name as a one-line note above each test now, and rename the tests in a later package? *Recommendation:*
yes, since renaming changes code, which this package proves it never does.

## Execution brief

Scope: L4's rule applied to `src/` and `tests/`, L5, L9's trial, VER-75. Depends on WP44 as merged.
Clauses: §8.2.11 L4, L5, L9; VER-72 (h); VER-75 (added in this commit); VER-45; `.claude/rules/python.md`.
Baseline, measured 13 October on `main`: prose is 33.0 % of the physical lines of `src/nanopnp`
(22,685 of 68,770) and 18.8 % of `tests/` (10,890 of 57,828); 407 of 1,704 tests carry an identifier only
in their docstring.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Tree check | `.claude/scripts/same_tree.py <ref> [paths]` compares every changed `.py` file with its version at `<ref>`: `ast.dump` without attributes, after deleting every bare string-constant statement, every `pass` and every bare `...`, must be equal; and the multiset of directive comments (`# type:`, `# noqa`, `# pragma`, `# fmt:`, `# mypy:`, `# ruff:`, `#!`, coding line) must be unchanged. A deleted, added or renamed file fails | L5. Comments are invisible to the syntax tree; directives are code |
| D2 What stays in `src/` | A condensed docstring (summary line, NumPy-style parameters only where name and type do not say, no derivation or history) on every function, class and method with no leading underscore on it or an enclosing class; the first pass (items 2 to 19) kept only `PUBLIC` names and is redone as items 19a to 19f. A one-line docstring on every module; `cli/__init__.py`'s line stays its parser description. A comment only for a reason the code cannot show or the source of a constant (`python.md`). A derivation, measured number or rationale found in neither the specification nor `.knowledge/` moves to the `.knowledge/` file of its area, with the module as source, or stays as a why-comment of at most two lines; it is never deleted unrecorded | L4; `python.md`. `__doc__` is read only there (surveyed) |
| D3 What stays in `tests/` | A one-line module docstring; none on a test, class, fixture or helper. Where an identifier lives only in a test's docstring, a one-line comment naming only the identifiers stays above the test; renaming is not done here (author's call) | L4; tree equality forbids renames |
| D4 VER-75 | Appendix A gains VER-75 in this commit: (a) in `src/nanopnp` a function or class docstring only where D2 allows, in `tests/` none, and every module docstring one line; (b) the share of physical lines that are docstring or non-directive comment lines, at most the value measured at the close plus 1 point, for `src/nanopnp` and for `tests/`, the ceilings recorded in the test. A docstring added to a private function fails (a), naming file, line and name; a toy tree over its ceiling fails (b) | L5; the phase plan's oracle. A single docstring cannot move a share a point, hence (a) |
| D5 Workers | Each strip item goes to a fresh `general-purpose` sub-agent: Sonnet for `src/`, Haiku for `tests/`, given the item, D1 to D3, `python.md` and the clauses it cites, not this conversation. It edits, runs `ruff format`, `ruff check`, `mypy src/` and `same_tree.py HEAD`, commits through the normal hook (`docs: strip the prose of <path>`), and reports the commit, its checks and its share in at most five lines. The main session keeps only this plan and `git log`, re-runs `same_tree.py HEAD~1` on the commit, then ticks. A failing commit is reverted and redone once on the same model, then on Opus | L5, L9 |
| D6 Order and split | Core first, `tests/` last, the large test tiers split alphabetically so a worker reads under about 10,000 lines; each item one commit. VER-45's strict build runs at the close. Prediction: `src/` at most 10 %, `tests/` at most 3 % | Phase plan. A miss is reported by subpackage and the author rules (L5) |

### Work items

Every strip item: done when `same_tree.py HEAD~1` passes on its commit and the commit hook passed.

- [x] 1. `.claude/scripts/same_tree.py` (D1) and `tests/tier1/test_same_tree.py`; done when the test passes and fails on each case of *Verification*.
- [x] 2. `src/nanopnp/core/` with `src/nanopnp/__init__.py`.
- [x] 3. `src/nanopnp/io/`.
- [x] 4. `src/nanopnp/numerics/`.
- [x] 5. `src/nanopnp/materials/`.
- [x] 6. `src/nanopnp/physics/`.
- [x] 7. `src/nanopnp/solve/`.
- [x] 8. `src/nanopnp/post/`.

*Compaction checkpoint: after item 8; resume from this plan and `git log`.*

- [x] 9. `src/nanopnp/mesh/`.
- [x] 10. `src/nanopnp/geometry/`.
- [x] 11. `src/nanopnp/structure/`.
- [x] 12. `src/nanopnp/density/`.
- [x] 13. `src/nanopnp/symmetry/`.
- [x] 14. `src/nanopnp/charge/`.
- [x] 15. `src/nanopnp/pipeline/`.
- [x] 16. `src/nanopnp/sweep/`.
- [x] 17. `src/nanopnp/cli/`.
- [x] 18. `src/nanopnp/validation/`.
- [x] 19. `src/nanopnp/gui/`.

- [x] 19a. Restore condensed public docstrings in `core`, `io`, `numerics`, `materials`, `physics`, `solve`, `post` (Haiku; old text from `3782c43`).
- [x] 19b. The same in `mesh`, `geometry`, `structure`, `density`, `symmetry`.
- [x] 19c. The same in `charge`, `pipeline`, `sweep`, `cli`.
- [x] 19d. The same in `validation` (part 1: files a to m).
- [x] 19e. The same in `validation` (part 2: the rest).
- [x] 19f. The same in `gui`.

*Compaction checkpoint: after item 19f.*

- [x] 20. `tests/tier1/test_[a-c]*.py`.
- [x] 21. `tests/tier1/test_[d-g]*.py`.
- [x] 22. `tests/tier1/test_[h-m]*.py`.
- [x] 23. `tests/tier1/test_[n-r]*.py`.
- [ ] 24. `tests/tier1/test_[s-z]*.py` and `tests/tier1/conftest.py`.
- [ ] 25. `tests/tier2/test_[a-l]*.py`.
- [ ] 26. `tests/tier2/` remainder, with `tests/tier2/data/`.
- [ ] 27. `tests/conftest.py`, `tests/tier3/`, `tests/tier4/`.

*Compaction checkpoint: after item 27.*

- [ ] 28. VER-75 in `tests/tier1/test_prose_share.py` (D4), ceilings from the tree as it stands; run VER-45's documentation build. Record under Outcomes the shares by subpackage against the prediction, the number of workers, redos and escalations, and the moves into `.knowledge/`; mark the plan delivered, update `current.md`, the Phase 4 plan and `CHANGELOG.md`. Done when `.claude/hooks/gate.sh run` passes.

### Verification

| Test | Tier | Identifiers | Oracle | Command |
|---|---|---|---|---|
| `test_same_tree.py` | 1 | L5 | Passes on a removed docstring, a docstring-only body replaced by `...`, and a rewrapped comment; fails, naming the file, on a changed statement, a removed `# pragma: no cover`, a removed `# type: ignore`, a removed `# noqa`, a deleted file and a renamed function | `uv run pytest tests/tier1/test_same_tree.py` |
| `test_prose_share.py` | 1 | VER-75 (a), (b) | Tree passes; a docstring added to a private function, to a test, and a two-line module docstring each fail naming file, line and name; a toy tree over its ceiling fails naming the share | `uv run pytest tests/tier1/test_prose_share.py` |
| `test_public_docstrings.py` | 1 | VER-72 (h) | Unchanged, passes after every item | the commit hook |
| Strict documentation build | — | VER-45 | Builds with no warning | `CLAUDE.md` *Commands* |
| Whole suite | 1, 2 | VER-62 unchanged | Every test unchanged in assertion | `.claude/hooks/gate.sh run` |

### Out of scope

Renaming tests to carry their identifiers (author's call; a later package by ruling). Prose in
`docs/`, `.knowledge/` and the skills. Any change of behaviour, test assertion or name. Whether
`wp-implement` adopts the worker pattern: the author's ruling after comparing costs (L9).

### Open questions

None blocking. The *Your call* above has a default, D3.
