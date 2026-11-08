# WP5.10 — The written knowledge's tools and rules

**Status: planned, not started.** 8 November 2026, at `da395a7`. Inherits §8.2.36 AL3 to AL7, AL14, AL24
and AL27, AL28 and AL29 ruled at this plan, CODE_REVIEW_039's sections 5 to 7 and its prototypes in
`.claude/scripts/audit/`.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md), entry WP5.10. `SPECIFICATION.md`
governs; an identifier here is a pointer, never a restatement. Where the two disagree, this plan is
wrong.

## In brief

**What changes.** The project's written record learns to keep itself level with the code. Every decision
taken, about twelve hundred and fifty, becomes one searchable page on the documentation site, rebuilt by
a script, and a check refuses a commit that leaves it out of date. A second page describes the program's
parts as they stand, rebuilt with every site build, and a check keeps the design's list of parts equal
to the code's. Every plan moves once into a folder for its phase, every link to it rewritten, and later
plans are written there, so no move breaks a link again. A linter learns to flag new functions that grow
too tangled or take too many settings. The release notes' Phase 5 entries move under the headings the
release workflow reads. A short report says what two further measuring tools would add.

**Cost.** About four days, the main work on the more capable model, at twice the price. No result
changes.

**What could go wrong.** The move could break a link; a link check over every file, run on every
push, and the strict site build would fail. The decisions page could drift; the new check refuses
the commit. The linter's limits could flag existing code; each of the 26 functions over them today is
marked as known and listed, so only new code is held to them.

**Your call.** Nothing before the work starts: you ruled the choices, and the rest have one sound
answer each. After it, whether to adopt either measuring tool, on the report.
*Recommendation:* read the report first; it names what each would catch that the current checks miss.

## Execution brief

**Scope.** AL3 to AL7 with AL28, AL14's check and entries, and AL27's trial; CODE_REVIEW_039's AUD-382 and
AUD-251, marked in its register (section 11). **Depends on** WP5.09, merged (`v0.6.0-alpha.9`).
**Pointers:** §5.1; §7.1's test-scope NOTE; §7.2 (VER-79, new); §7.6; §8.4.1; §8.4.4; §8.4.5;
Appendix A; open decision 14. **Implementing session:** Opus, high effort (AL29); sub-agents as each item
names. Eight decisions: one per ruling's deliverable.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1. The decisions register | `.claude/scripts/decisions.py`, promoted from the prototype, writes `docs/project/decisions.md`, committed and in the site's Project section. Rows: each history ruling, plan `Dn` row, `REV`, `MOD`, `OPN` and `WB` row, knowledge-base ruling and *Not to be re-decided* bullet; no Outcome, mark, *Your call*, checklist or review-sentence rows. Appendix D's eight columns; *Where* a path with no line number; dates in ISO form; rows by date, undated last, then source; counts by source and decider on top; cells plain text. A history ruling's *holds now* is read from `specification/history/holds-now.yaml`, the index's list moved there; the index's section becomes a pointer. `--check` compares and writes nothing | Ruled by the author (AL3; section 6's proposal). Decided by the plan: a generated page cannot carry hand-written entries, so they move to one file beside the records; a line number would rewrite the page at every unrelated edit |
| D2. The guards | VER-79, new in §7.2, in `tests/tier1/test_written_architecture.py`: §5.1's module rows equal the subpackages; the page equals what the script renders; the YAML's keys equal the ruling letters, both ways. §7.1's NOTE lists VER-79 among the architecture guards; Appendix A says it leaves the count unchanged. `gate.sh` runs `decisions.py --check` at every commit and push, prose-only included, and CI's `docs` job does too, with `links.py` (§7.6's every-push row) | Ruled by the author (AL3, AL6). Decided by the plan: every source is Markdown, which the gate otherwise only lints, so a plan commit would leave the page stale |
| D3. The architecture page | `docs/scripts/architecture.py`, promoted, renders it; `generate.py` writes `_generated/project/architecture.md` beside the measurements, never committed; the Project navigation and `docs/project/index.md` list it. No commit hash: the page is the tree the site was built from. §5.1 gains a NOTE naming the page and VER-79; its responsibility column stays the author's | Ruled by the author (AL6; section 7's proposal) |
| D4. Plans by phase | A plan is written in `docs/plans/phase-<n>/` from the commit that adds it, a standalone brief or review in `docs/plans/sessions/`; `current.md` and `index.md` stay at the top; a phase close moves nothing. `audit/migrate_plans_archive.py`, rewritten and not kept, moves the other 81 files once, by phase membership. It rewrites every relative link into or out of a moved file and every written `docs/plans/<name>`, in every tracked text file, records included, and nothing else. `links.py`, promoted, checks every tracked Markdown file. The plan readers recurse; the skills' path templates name the folder | Ruled by the author (AL5 as amended by AL28). Decided by the plan: membership by phase, since status lines are stale (wp42, wp43) |
| D5. Indexes and the commands' rule | `.claude/scripts/index_records.py`, promoted, lists `docs/plans/`'s top level, then one section per folder. The core's *Gate and push* runs `index_records.py` and `decisions.py` before each commit and commits what they write; §8.4.4 states it; `rulings.md` names the YAML. §8.4.5 and `CLAUDE.md` list six kept scripts | Ruled by the author (AL3, AL4). Decided by the plan: every level reads the core, so one step serves all three commands |
| D6. Function complexity | Ruff selects `C901` at `max-complexity = 15` and `PLR0913` at `max-args = 8`; `tests/*` ignores both. The 27 offences on 25 definitions in `src/` and one in `.claude/scripts/audit/` carry a `noqa` on the reported line; none is refactored | Ruled by the author (AL7). Decided by the plan, from the sample: the defaults (10, 5) flag 139 offences, these limits 29, one of them a test |
| D7. The changelog | `/np-ship`'s preflight greps `## [X.Y.Z-alpha.N]` as `tag.yml` does. WP5.02 to WP5.09's paragraphs move under `## [0.6.0-alpha.N] - <tag date>`, WP5.01's into `[0.6.0-alpha.2]`; `## [Unreleased]` stays, empty. This package's entry is `[0.6.0-alpha.10]` | Ruled by the author (AL14); WP5.01's place is §8.4.1's |
| D8. The trial | xenon and import-linter run from ephemeral environments as `survey.sh` runs them, import-linter's layers contract in `LAYER_ORDER` (AL8), with and without `TYPE_CHECKING` imports. A concept, `knowledge/07-software-stack/25-complexity-and-import-contract-tools.md`, states what each adds over D6 and `test_layering.py`, and recommends; neither enters `pyproject.toml` | Ruled by the author (AL7, AL27); adoption is open decision 14. Decided by the plan: a measurement's home is a concept (AL17) |

### Grounding

**D1.**
- `.claude/scripts/audit/decisions.py:main` writes 1,170 rows at `da395a7`: 309 history, 474 plan
  `Dn`, 222 `REV`, 38 `WB`, 18 `MOD`, 14 knowledge-base, 12 bullets, 9 `OPN`, and 74 evidence rows
  (25 *Your call*, 24 Outcome, 13 marks, 11 checklist items, 1 review sentence). D1 keeps 1,096,
  about 1,250 with every `Dn` row.
- `history()` reads `specification/history/index.md`'s `* <id> - <entry>` lines (`HOLDS`), the
  section *Where each ruling holds now* from line 51 to the end: 309 entries, one per ruling, none
  missing.
- The prototype's `D_ROW` takes only `| D1 |`: of 632 plan rows that open `| D<n>`, it misses 158,
  every plan from wp41 on and all of Phase 5's, which write `| D1 <name> |` or, as this plan does,
  `| D1. <name> |`, and wp42's `| D14b |`. The 474 above is the narrow count.
- `plans()` globs `docs/plans/*.md`, skipping only `current.md`; `where` is `path:line`;
  `registers()`, `workbench()`, `orientation()`, `current()` and `open_items()` read
  `docs/project/{review,modularity}-findings.md`, `docs/design/workbench.md`,
  `knowledge/00-orientation/05-*.md`, `current.md` and `specification/10-open-items.md`.
- The prototype's cells hold 244 Markdown links, 22 HTML-like tags (`<li>`, `<n>`) and 113 code spans
  left open by clipping; on the site each breaks the table or the strict build.
- `mkdocs.yml` sets `validation.nav.omitted_files: warn`, so under `--strict` the page must be in the
  navigation. `generate.py:_copies` copies only `*.md` from `specification/`, so the YAML is not
  published. PyYAML is a runtime dependency.
- The index's list is named by `SPECIFICATION.md` (two lines: the history bullet and the map's),
  `specification/index.md`'s History entry, §11's table row and `np-plan/rulings.md`'s *Where the rulings are
  written*; `core.md`'s *Records* row says a ruling round writes "its lines in `history/index.md`", and
  `rulings.md` step 2 and `project.md` step 1 read the index for the rulings that bind. `clause.py` reads
  ruling rows, not the list.

**D2.**
- `.github/scripts/prose-only.sh` calls every `*.md` outside `packaging/`, `src/`, `data/` and
  `examples/` prose. `gate.sh` then sets `docs_only` and runs ruff alone; CI's `changes` job sets
  `code=false` and skips the tests. The `docs` job runs on every push with
  `uv sync --no-default-groups --group docs`: no pytest, the project and PyYAML installed.
- §5.1's table rows match `^\|\s*`([a-z_]+)/`\s*\|` (the prototype's `TABLE_ROW`): 20 rows, equal to
  `{node_of(m.name) for m in parse_package()} - {"nanopnp"}`; the `nanopnp` node is `__init__.py`
  and `case.py`.
- The highest identifier is VER-78. Tests reach the repository through
  `nanopnp.validation.findings.REPOSITORY` (`test_layering.py`); none loads a script by path, so the
  guard loads `decisions.py` and `docs/scripts/architecture.py` with
  `importlib.util.spec_from_file_location` and reads §5.1 with the latter's `TABLE_ROW`.

**D3.**
- `.claude/scripts/audit/architecture.py:render` imports `LAYER_ORDER`, `STATIC_KINDS`, `Module`,
  `import_edges`, `node_of`, `parse_package` and `subpackage_relation` from
  `nanopnp.validation.modularity`, all present; it reads `core/stages.py` by its syntax tree and §5.1's
  table by `TABLE_ROW`; `--at` shells to `git rev-parse`.
- `docs/scripts/generate.py:main` writes `project/modularity-measurements.md` from its `rendered`
  map. It runs as a script, so `docs/scripts/` is on `sys.path`.

**D4.**
- Of 83 files in `docs/plans/`, 81 move: `phase-0/` 4 (`phase-0-spike`, `phase-0-consolidation`,
  `wp5-*`, `wp6-*`); `phase-1/` 11 (its plan, `wp7` to `wp16`); `phase-2/` 10 (its plan, `wp17` to
  `wp25`); `phase-3/` 10 (its plan, `wp26` to `wp34`); `phase-4/` 28 (its plan, `phase-4-record`,
  `wp35` to `wp60`); `phase-5/` 12 (its plan, its record, `wp5.01` to `wp5.10`); `sessions/` 6
  (`copilot-host`, `history-prose-review`, `kb-audit-brief`, `notebooks-review-for-wp54`,
  `okf-converter-rules`, `okf-knowledge-bundle`). `current.md` and `index.md` stay.
- `migrate_plans_archive.py:_moved` picks by status line: it would miss `wp42` and `wp43`; it rewrites
  links only in live files and never a moved file's own.
- At `1c4d463`, 300 relative links change: 243 into moved files, 51 out of them, 6 between folders
  (`docs/plans/` 141, `docs/project/` 137, `CHANGELOG.md` 20, `docs/user-testing/` 2). 2,735 written
  `docs/plans/<name>` paths change (`docs/code_reviews/` 2,604, JSON and TSV included; `knowledge/`
  64, `CHANGELOG.md` 27, `docs/plans/` 22, `specification/` 10, `.claude/` 5, `docs/user-testing/` 2,
  `docs/project/` 1). No reference-style or HTML link, and no `plans/<name>` without `docs/`.
- The layout is named by `np-plan/wp.md` (`docs/plans/wp<n>-<slug>.md`), `np-plan/phase.md` (three
  `docs/plans/phase-<n>-…` templates), `rulings.md` (`docs/plans/phase-<n>-record.md`),
  `np-ship/phase.md` step 1, `core.md`'s *Records* row and §8.4.4's naming bullet; `session-start.sh`
  names only `current.md`.
- Two live skills name a moved plan bare: `np-plan/phase.md` (`phase-3-charge-pipeline.md`) and
  `rulings.md` (`phase-4-record.md`).
- `audit/links.py` reads `scope.py`'s files and reports 58 broken without `docs/_generated/` and 2
  after `generate.py`: `CODE_REVIEW_013.md:31` and `wp52-specification-and-plans-split.md:175`.
  `scope.py:_own_output` leaves out `docs/code_reviews/CODE_REVIEW_039/`, whose `decisions.md` holds 984
  relative links copied from other folders, all broken; `git ls-files '*.md'` includes it.
- `duplicates.py:main` globs `docs/plans/wp*.md`; `audit/scope.py`'s `RECORD_GLOBS` has
  `docs/plans/*.md`. CI's `docs` job runs `generate.py`, so `links.py` runs after it
  there.

> **Outcome — 2,697 written paths, not 2,735; 300 links as counted.** The 18 paths after `0ff2d619:`
> in six `knowledge/` concepts (`git show` and `resource: git:` pins) name a file at that revision,
> where it keeps its old path, so the script leaves a path after `<commit>:` alone; the other 20 are
> `CHANGELOG.md`'s root-relative links, counted twice above and rewritten once as links. The dry run
> on the tree before the move printed 81 files, 300 links and 2,697 paths, folder by folder as
> above. `links.py` finds 1,419 relative links, none broken outside its two `KNOWN`.

**D5.**
- `audit/index_records.py:render` globs `<folder>/*.md` and footers its own audit path. The core's
  *Gate and push* is read by every level of the three commands. §8.4.5 and `CLAUDE.md` *Models* list
  three kept scripts.

**D6.**
- `pyproject.toml`'s `select` has neither `C901` nor `PL`. Offences at `da395a7`: `C901` at 10, 15 and
  20: 32, 11, 4; `PLR0913` at 5, 6 and 8: 107, 43, 18. Ruff reports both on the definition's name
  line, and `RUF100` refuses an unused `noqa`. `same_tree.py` counts `noqa` as a directive, so it cannot
  certify this diff.

**D7.**
- `tag.yml` greps `## [${TAG#v}]` in `CHANGELOG.md` at the commit. `## [Unreleased]` holds nine
  paragraphs, WP5.01 to WP5.09, above `## [0.5.0] - 2026-11-02`; tags `v0.6.0-alpha.2` to `.9` are on
  origin. `np-ship/wp.md` §1 says only "has the package's section".

**D8.**
- `survey.sh` runs `uvx xenon src/nanopnp --max-absolute C --max-modules B --max-average A` and
  `uv run --with import-linter lint-imports --config <ini> --no-cache`; its contract in
  `modularity.md`'s order broke. import-linter 2.15 lists layers highest first, `|` for independent
  siblings, and a top-level `exclude_type_checking_imports`. This session's harness refused `uvx`; the
  implementer asks the author if it is refused again.

### Implementation details

**Item 1.** In `pyproject.toml`: append `"C901"` and `"PLR0913"` to `select`; add
`[tool.ruff.lint.mccabe] max-complexity = 15` and `[tool.ruff.lint.pylint] max-args = 8`; extend the
`"tests/*"` per-file ignore with `"C901", "PLR0913"`. Append `  # noqa: <codes>` to the name line of:
`C901` on `cli/running.py` `_inspect`, `_plot`; `gui/web/pages.py` `install`; `io/variables.py`
`_admit`; `pipeline/checks.py` `require_runnable`; `pipeline/run.py` `selected_stages`;
`structure/read.py` `select`; `.claude/scripts/audit/inventory.py` `main`. `PLR0913` on `api/case.py`
`cylinder`, `from_structure`; `api/session.py` `_walk`; `density/union.py` `_accumulate`;
`io/manifest.py` `build`; `physics/models.py` `residual_form` and its three `solve`; `physics/pb.py`
`solve_pb_recorded`; `pipeline/run.py` `_resolve_stage`, `_walk`, `run_document`; `post/forces.py`
`axial_extension`, `extract`; `post/qoi.py` `extract`. Both (`# noqa: C901, PLR0913`) on
`numerics/newton.py` `damped_newton` and `solve/continuation.py` `default_ladder`. Paths are under
`src/nanopnp/`.

**Item 2.** `migrate_plans_archive.py`, in place: build `moved: {old: new}` from a table (WP 1–6 →
0, 7–16 → 1, 17–25 → 2, 26–34 → 3, 35–60 → 4, read by `^wp(\d+)-`; `wp5.<nn>` → 5; a phase plan or
record by its number; the six names → `sessions`). `--dry-run` prints the counts and writes nothing.
For each file of `git ls-files` that decodes as UTF-8, with `new_self = moved.get(f, f)`: in a `*.md`
file, for each link of `links.py`'s `LINK` whose target has no scheme and no leading `#`, resolve it
against `f`'s old directory, map it through `moved`, and write it relative to `new_self`'s directory,
anchor kept; leave it untouched when neither end moved. Mask code for links only, as `generate.py`
does. Then, in every such file, inside code too, replace `docs/plans/<name>` for each moved name with
its new path. Write every file, then `git mv`; print the counts. The dry run's counts equal Grounding
D4's, each difference traced to a commit since `1c4d463`. `links.py`, promoted, sets
`ROOT = Path(__file__).resolve().parents[2]`, imports nothing from `audit/`, reads `git ls-files
'*.md'` less `CODE_REVIEW_039/`'s attachments, and passes the two broken links of today, named in a
`KNOWN` set at their new paths. Then: `duplicates.py` to `rglob("wp*.md")`; `scope.py` to
`docs/plans/**/*.md`; the two bare names and each template of Grounding D4 to `phase-<n>/`; §8.4.4's
naming bullet to `docs/plans/phase-5/wp5.01-<slug>.md`, and a bullet: "A plan is written in its
phase's folder, `docs/plans/phase-<n>/`, from the commit that adds it, and a standalone brief or review
in `docs/plans/sessions/`; `current.md` and `index.md` stay at the top, and a phase close moves
nothing. (§8.2.36 AL5, AL28)" This plan moves too; read it from `docs/plans/phase-5/`.

**Item 3.** `index_records.py`: the plans index lists `current.md`, then one section per folder,
`## Phase 5` down to `## Phase 0`, then `## Sessions`, each linking `<folder>/<name>`, each section's
count equal to its folder's files; its footer names `.claude/scripts/index_records.py`.

**Item 5.** The YAML: one `<letter>: '<entry>'` line per ruling, in index order, written once by
`yaml.safe_dump(..., sort_keys=False, allow_unicode=True, width=10**6)` from the index's list, under
a two-line comment saying what it is and that `decisions.py` reads it. The index's section becomes:
"Where each ruling holds now is the *Holds now* column of the
`[decisions register](../../docs/project/decisions.md)`, read from `holds-now.yaml` beside this file."
`core.md`'s *Records* row, `rulings.md` step 2 and `project.md` step 1 name the YAML in place of the
index's list. `plans()` reads `docs/plans/**/*.md`, skipping `index.md` and `current.md`; `D_ROW`
becomes `^\|\s*\*{0,2}(D\d+[a-z]?)\b\.?[^|]*\|(.*)$`, so `| D1 |`, `| D14b |`, `| D1 <name> |` and `| D1. <name> |` all
count. The page: a title, a sentence naming the script and the command that rewrites it, the two count
lines, then `| Source | Decided by | Where | Date | Package | What was decided | Holds now | Status |`.
A cell: links reduced to their text, `<` and `>` as `&lt;` and `&gt;` outside code spans (masked as
`generate.py` masks them), `|` as `\|`, whitespace
collapsed, clipped at 220 characters (160 for *Holds now*) with a backtick appended when an odd number
remain. Dates: `8 November 2026` → `2026-11-08`, `August 2026` → `2026-08`. Rows sort by (ISO date,
undated as `9999`; the source kinds in D1's order; path; reading order). `--check` exits 1, printing
the first differing line and the command; the default writes. The guard and `--check` share
`render() -> str`, `holds_now() -> dict[str, str]` and `ruling_letters() -> list[str]`. Under
`--strict` the page needs `- Decisions register: project/decisions.md` after *Review findings* in
`mkdocs.yml`, and a row in `docs/project/index.md`, in this item. Count checks: the history rows
equal the YAML's entries (311 with AL29); the plan rows equal
`git grep -hE '^\| *\**D[0-9]' -- 'docs/plans/**/*.md' | wc -l` (632 now).

**Item 6.** In `generate.py`, `from architecture import render as render_architecture`, and
`"project/architecture.md": render_architecture()` in `rendered`. `render()` takes no argument and
reads no git, and it sets `ROOT` as item 2 says, without `scope` or `sys.path`; its title becomes `# Architecture` and its first sentence names
`docs/scripts/architecture.py`, not the audit. Navigation: `- Architecture: _generated/project/architecture.md` after
*Modularity measurements*, and a row in `docs/project/index.md`. Its module table has 20 rows.

**Item 7.** VER-79's row: "The written architecture and decisions | §5.1's `name/` rows equal the
subpackages of `src/nanopnp` in both directions; `docs/project/decisions.md` equals what
`.claude/scripts/decisions.py` renders from the tree; and the keys of
`specification/history/holds-now.yaml` equal the ruling letters of `specification/history/` in both
directions (§5.1; §8.4.4; §8.2.36 AL3, AL6)". §5.1's NOTE: "NOTE (the module table; §8.2.36 AL6):
the site's *Architecture* page is generated from the tree at each build. VER-79 holds this table's
module rows equal to the subpackages; the responsibilities are written here." §8.4.4 gains: "A commit
that adds or changes a decision re-runs `.claude/scripts/decisions.py`, and one that adds a plan or a
review re-runs `index_records.py`; the gate refuses a decisions page that differs from the tree.
(§8.2.36 AL3, AL4)" In `gate.sh`, after `ruff format --check`:
`check "decisions page" uv run .claude/scripts/decisions.py --check`; in `ci.yml`'s `docs` job,
before `generate.py`: `- run: uv run --no-sync .claude/scripts/decisions.py --check`, and after it
`- run: uv run --no-sync .claude/scripts/links.py`; §7.6's every-push row names both.

**Item 9.** `git fetch origin 'refs/tags/v0.6.0-alpha.*:refs/tags/v0.6.0-alpha.*'`; each date is
`git log -1 --format=%cs v0.6.0-alpha.N`. Move each paragraph unchanged, newest first. The preflight
line: "`CHANGELOG.md` has `## [X.Y.Z-alpha.N]` for the package's tag, the heading `tag.yml` greps
(`grep -qF '## [X.Y.Z-alpha.N]' CHANGELOG.md`)." §8.4.1's second bullet gains, before its sources:
"Its `CHANGELOG.md` section is headed `## [X.Y.Z-alpha.N]`, the line `tag.yml` reads and
`/np-ship`'s preflight checks."

**Item 10.** The import-linter ini: `root_package = nanopnp`, one `layers` contract listing
`LAYER_ORDER` highest first without `nanopnp`; run it as is, then with
`exclude_type_checking_imports = True`. xenon as `survey.sh` runs it, then at `--max-absolute C`.
Record each command, its result and the commit.

### Work items

- [x] 037f14b 1. `pyproject.toml`; the 26 `noqa` lines (D6); done when `uv run ruff check .` passes and the
  diff adds those 26 comments and nothing else. **Executor:** `general-purpose` on Haiku
- [x] 64f5d43 2. `git mv` of `audit/links.py` to `.claude/scripts/links.py`; `migrate_plans_archive.py`
  rewritten and run; `duplicates.py`, `audit/scope.py`, the skills' paths; §8.4.4 (D4); done when the
  dry run's counts match Grounding D4's, `links.py` names nothing outside `KNOWN`, `duplicates.py`
  passes and the strict build passes. **Executor:** main
- [ ] 3. `git mv` of `audit/index_records.py`; folder sections; the three indexes rewritten (D5); done
  when each section's count equals its folder's. **Executor:** `general-purpose` on Sonnet
- [ ] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `git mv` of `audit/decisions.py`; `holds-now.yaml`; the index's pointer; `docs/project/decisions.md`;
  the pointers in `SPECIFICATION.md`, `specification/index.md` and §11; `rulings.md`, `core.md`,
  `project.md`; the page's navigation (D1, D5); done
  when `--check` passes, item 5's counts hold and the strict build passes. **Executor:** main
- [ ] 6. `git mv` of `audit/architecture.py` to `docs/scripts/architecture.py`; `generate.py`, `mkdocs.yml`,
  `docs/project/index.md` (D3); done when the strict build shows the page with 20 module rows.
  **Executor:** `general-purpose` on Sonnet
- [ ] 7. `tests/tier1/test_written_architecture.py`; §7.1, §7.2, §7.6, Appendix A; `gate.sh`, `ci.yml`;
  the core's *Gate and push*; §8.4.4; §5.1's NOTE (D2, D3, D5); done when VER-79's tests pass.
  **Executor:** main
- [ ] 8. Compaction checkpoint. **Executor:** main
- [ ] 9. `CHANGELOG.md`'s nine paragraphs; `np-ship/wp.md` §1; §8.4.1 (D7); done when each of
  `0.6.0-alpha.2` to `.9` greps and the paragraphs are byte-identical. **Executor:** main
- [ ] 10. The trial and `knowledge/07-software-stack/25-complexity-and-import-contract-tools.md`, its
  index and `knowledge/log.md` (D8); done when the code and review say so. **Executor:** main
- [ ] 11. §8.4.5, `CLAUDE.md` (six scripts; the gate's prose check; VER-79 in *Testing*'s guards);
  `holds-now.yaml` for AL3 to AL7, AL14, AL24, AL27 and AL28; AUD-382 and AUD-251 in
  `raw/dispositions.tsv` and `raw/commits.tsv`, `register.py` and `maps.py` re-run; done when no YAML
  entry names WP5.10 as open. **Executor:** main
- [ ] 12. The Outcome, `current.md`, `CHANGELOG.md`'s `[0.6.0-alpha.10]`; done when the code and
  review say so. **Executor:** main

### Verification

| Test | Tier | Identifier | Oracle | Tolerance |
|---|---|---|---|---|
| `test_ver79_section_5_1_module_rows_equal_the_subpackages`: no subpackage without a row, no row without a subpackage, and the text with its `plot/` row deleted lacks `plot` | 1 | VER-79 | The tree's subpackages | Exact; one assertion each |
| `test_ver79_the_decisions_page_equals_what_the_script_renders`; the message names the first differing line and the command | 1 | VER-79 | `decisions.render()` | Exact |
| `test_ver79_every_ruling_has_one_holds_now_entry`: no ruling without an entry, no entry without a ruling | 1 | VER-79 | The ruling letters of `specification/history/` | Exact; one assertion each |

Command: `uv run pytest tests/tier1/test_written_architecture.py`. Out of scope, checked by the code
and review: the strict build, `links.py`, `duplicates.py`, `ruff check`, the gate's prose path.

### Out of scope

- WP5.11: §5.1's words (AUD-100, AUD-307), `modularity.md` (AL8), the changelog rule's restatements
  (AUD-279), `CLAUDE.md`'s §4 line (AL16). WP5.12: the knowledge base.
- Adopting xenon or import-linter: the author, open decision 14. Refactoring D6's 25 definitions.
- The audit's other scripts stay for WP5.11 and WP5.12.

### Open questions

None blocks the work. Open decision 14 waits for item 10's report.
