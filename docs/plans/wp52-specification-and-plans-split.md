# WP52 — The documents: the specification and the plans split

PR: [#121](https://github.com/willemsk/nanopnp/pull/121), branch claude/wp52-documents

**Status: planned, not started.** Written 22 October 2026; grounded in the code at `0329cde`
(§8.2.15 Q1). Inherits WP51 as shipped and the Phase 4 amendment (§8.2.16 R1 to R10).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** The specification, one 80,000-word file today, becomes a folder with one file
per section. Its 16,000 words of dated rulings move into a history folder that is read only when
the reason behind a ruling is wanted. The rulings still in force, but with no section of their own,
are written out once as a short list of the rules of the development process. The top-level file
becomes a map from each section and identifier to the file that holds it. A session reads a page
of map and the sections it needs. The Phase 4 plan is cut to
what holds today, its full text kept as a record.

**Cost.** One pull request, one or two sessions.

**What could go wrong.** A clause could be lost or altered in the move: a script checks that
every old line is still present, and another that every identifier still prints the same text.
A link on the documentation site could break: the strict build fails on it. The rules list could
say more than the rulings did: review reads it against them, helped by an index of where each
ruling now lives.

**Your call.** Should the Phase 4 plan's record be a verbatim copy of the plan as it stands, rather
than only its amendment notes cut out one by one? *Recommendation:* the copy; nothing can be
lost, and nobody reads it by default.

## Execution brief

Scope: the Phase 4 plan's WP52, plus two workflow changes the author asked for, already
committed: the planning skills' PR step (`f90e3d4`) and R11. No identifier is
claimed and no test is kept (N1). Pointers: §8.2.16 R2 to R4, R9 to R11; §11; VER-45. Implemented by
a Sonnet 5.5 session at high effort; each item names its executor (R6, R11).

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | File boundaries | One file per `##` section. §5, §7 and §8 are directories split at `###`, and §5.3 is further split at `####` (four files). Layout in *Grounding* D1. **The split is made by a one-off script that slices the old file at its heading lines; no line of the old text is retyped or reflowed.** A `---` rule before a `##` heading stays at the end of the preceding file | R2. §5.3.1 alone is 7,467 words. Retyping is where text gets lost |
| D2 | What moves to history | All of `### 8.2`: its Phase 0 criteria and §8.2.1 to §8.2.16, one file each, verbatim. Nothing outside §8.2 moves. The withdrawn `VER-` and retired `RSK-` rows are already R2's one-line entries; ADRs are records. Current §8.2 becomes a stub headed `### 8.2 Rulings by date`, linking the history. `history/index.md` gives each ruling's home now: a clause, a §8.4 rule, `superseded by <id>`, or `spent` (a one-time act) | R2, R3. The index makes R3's section reviewable against the tables |
| D3 | The rules in force | A new `### 8.4 Development process` in `08-implementation-plan/04-development-process.md`, at most 1,500 words. Subsections 8.4.1 to 8.4.6: versions and releases; the loop; the test scope; plans and the workflow; agents and models; open items and review. Each rule is a bullet ending in its sources. **A ruling is restated only if** it is in force, sets a standing rule rather than a one-time act, and no current clause already carries it. No rule is a table row (`clause.py` would read a letter-number first cell as a ruling). `CLAUDE.md` and `.claude/rules/python.md` cite `§8.4.k` beside each ruling identifier they name | R3: a restatement, no new rule. A new §8.4 renumbers nothing |
| D4 | Entry point and `type` vocabulary | `SPECIFICATION.md` keeps its title block, its first 14 lines unchanged, then adds: how to read (current by default, `history/` on demand, `clause.py`), a section-to-file table, and an identifier-prefix-to-file table. Each non-index file opens with front matter `type`, `title` and `description`. The `type` is one of `Specification`, `Process` (§8.4 only) or `Ruling Record` (history). `specification/index.md` declares `okf_version: "0.2"` and lists the files in the OKF form `* [title](path) - description` | R2. A small closed list, as in `knowledge/` |
| D5 | Tooling | `clause.py` reads the bundle, not `SPECIFICATION.md`. It searches the current files before `history/` and, within each, in path order with `index.md` first. A ruling is a ruling-shaped row in a `history/` file. It prints **every** definition, first-found first, each labelled with its file and line range. `generate.py` copies the bundle beside the entry point. `mkdocs.yml` lists every bundle page statically. The guide's anchored links are repointed | R2. Printing every definition fixes `N1` and `P1`, which resolve today to the §3.5 and §2.4 rows only. R10 compares the first definition, which is unchanged |
| D6 | The Phase 4 plan | `phase-4-record.md` is a verbatim copy of the plan at the base, under a three-line header; later amendments append dated sections to it. The plan is rewritten to its current scope: WP35 to WP51 as one table (package, plan link, tag), and WP52 to the close, the open decisions, the supplies and the criteria with every amendment folded in and no `Amended` blockquote. Under 6,000 words (criterion 14) | R4; a copy cannot lose a line |

### Grounding

**D1, D2.** `SPECIFICATION.md` has 4,186 lines and 80,367 words; `### 8.2` to `### 8.3` has 15,936
words. The layout under `specification/`, with each file's opening heading line:

- `index.md`; `01-introduction.md` (`## 1.`), `02-product-overview.md`, `03-requirements.md`,
  `04-physics.md`, `06-numerics.md`, `09-risks.md`, `10-open-items.md`,
  `11-companion-knowledge-base.md`, `12-references.md`, `a-traceability-matrix.md`,
  `b-comsol-settings.md`.
- `05-software-design/`: `index.md` (`## 5.`), `01-architectural-overview.md`,
  `02-pipeline-stages.md`, `03-1-case-file.md` (from `### 5.3 Data design` through §5.3.1),
  `03-2-artefacts.md`, `03-3-provenance-manifest.md`, `03-4-sweeps.md`,
  `04-component-design.md`, `05-extension-points.md`, `06-architecture-decisions.md`.
- `07-verification/`: `index.md` (`## 7.`, its intro), `01-strategy.md`, `02-tier-1.md`,
  `03-tier-2.md`, `04-tier-3.md`, `05-tier-4.md` (§7.5 with `### 7.5.1`), `06-continuous-integration.md`.
- `08-implementation-plan/`: `index.md` (`## 8.`), `01-phases-and-gates.md`, `02-rulings.md`
  (the stub), `03-effort-estimate.md`, `04-development-process.md` (new).
- `history/`: `index.md`, `00-phase-0-exit-criteria.md` (from `### 8.2 Phase 0 exit criteria`),
  `01-…md` to `16-…md`, each slugged from its `#### 8.2.k` heading.
- The front matter's `---` delimiters precede the file's first line; any `---` rule that ended a
  slice stays at its end.

**D2, D3.** The ruling rows are 119 identifiers over letters A to R. Their *Clause changed*
column reads `None` or names only files outside the specification for, among others: B1, D5, E5,
G1, G3, G5, G7 to G9, G11, H1, H4 to H8, H10, I2, I3, J5, J9, J12, L4, L6 to L8, M1, M5, N5, N7,
P2, P6, P7, Q1, R3 to R7 and R9. These are the candidates for §8.4; the rule in D3 decides each.
Superseded rows say so in their first cells (J2, J3, J7, J8, J11, P1).

**D4.** `knowledge/index.md` is the model: front matter `okf_version: "0.2"`, then
`* [Title](dir/index.md) - description` lines. `knowledge/` has no Markdown link into the
specification, only plain-text mentions (51), so R9 leaves it unchanged. The 306 plain-text mentions
of `SPECIFICATION.md §x` across the repository stay true through the entry point's map.

**D5.**

- `.claude/scripts/clause.py`: the `SPECIFICATION` constant becomes the bundle root
  (`parents[2] / "specification"`). `_definition`, `_notes` and `_rulings` run per file over an
  ordered list; `_rulings` keeps `RULING_ROW` but bounds it to `history/` files, not to a `### 8.2`
  range. The labels become `--- definition (specification/<path>:<start>-<end>) ---`. Sort key:
  the relative POSIX path with `index.md` replaced by `!index.md`, with current files before `history/`.
  `SPECIFICATION.md` itself is not searched.
- Today `clause.py` resolves every Appendix A identifier (149) and every ruling identifier (118 at
  `0329cde`, 119 with R11), with no miss. First cells `S1`–`S4`, `P1`–`P3` (§2.4) and `N1`–`N7` (§3.5)
  precede §8.2, so today `clause.py N1` prints the exclusion row.
- `docs/scripts/generate.py:_copies` maps `ROOT / "SPECIFICATION.md"` to
  `model/specification.md`; add each `specification/**/*.md` at
  `model/specification/<relative path>`. `rewrite_links` already redirects links between copied
  pages. The module docstring's "The model" bullet names the bundle.
- `mkdocs.yml`: `validation.links.anchors` and `nav.omitted_files` are `warn` under `--strict`, so
  a broken anchor or an unlisted page fails VER-45. The nav entry
  `Specification: _generated/model/specification.md` becomes a section listing the entry point,
  every bundle page and a `History` subsection. `okf.navigation` is not reused: it hard-codes
  the knowledge base's title and `log.md`, and `src/` stays untouched.
- The anchored links into `_generated/model/specification.md#…` are in `docs/guide/charge.md`
  (`#44-…`, `#531-…`), `docs/guide/geometry.md` (`#521-…` twice, `#522-…` twice, `#531-…`) and
  `docs/guide/structures.md` (`#531-…`). Each is repointed to its section file, keeping the anchor.
  Unanchored links to the entry point (`docs/model/index.md`, `README.md`, `CHANGELOG.md`,
  `docs/project/physics-models.md`) stay.
- No code reads the specification's text. `validation/modularity.py:requirement_releases` takes the
  text as an argument and has no caller. The comments naming a `SPECIFICATION.md` section in `src/`,
  `tests/` and `.github/` stay true.
- `clause.py`, `generate.py` and `mkdocs.yml` are not prose (`.github/scripts/prose-only.sh`).
  The push gate therefore runs in full, even though `src/` and `tests/` are untouched.

**D6.** The Phase 4 plan is 16,580 words with 30 `Amended` blockquotes. Its *Open decisions*
(1,509 words) and *Verification* (1,482) are the largest current sections. Criterion 14 predicts the
current scope under 6,000.

### Implementation details

For the items a sub-agent executes. `<scratch>` is the session's scratchpad. `<base>` is the branch
head when item 1 starts, saved in `<scratch>/base`. If that file is lost, `<base>` is the parent of
item 2's commit. Scripts use the standard library only and run as `uv run --no-project python`.

**Item 1, the check scripts.**

- `lines.py <base>`: *old* is `git show <base>:SPECIFICATION.md`; *new* is `SPECIFICATION.md`
  plus every `specification/**/*.md` in the working tree. Right-strip every line and drop the blank
  ones. Print each line of `Counter(old) - Counter(new)` with its first old line number, then
  `missing: N`. Exit 1 when N > 0.
- `ids.py <base>`: `git worktree add --detach <scratch>/base-tree <base>`, unless it exists.
  - Identifiers, read from the base text: every `\b(FR|QR|CON|PHY|NUM|VER|VAL|IF|RSK|OPN|ADR)-\d+\b`
    between `## Appendix A` and `## Appendix B`; and every first cell matching
    `^\|\s*\**([A-Z]\d+)\**\s*\|` between `### 8.2 ` and `### 8.3`.
  - For each identifier, run `uv run .claude/scripts/clause.py <id>` with the base tree, then the
    working tree, as the working directory. From each output take the text between the first line
    starting `--- definition` and the next line starting `--- ` or `=== `, or the end.
  - Print each identifier whose texts differ, or that either run fails to resolve. Then print
    `identifiers: N, differing: M`, remove the worktree, and exit 1 when M > 0.
- Before item 2, both scripts must report 0 on the unchanged tree, over 149 + 119 identifiers.
  The item makes no commit.

**Item 2, the slicing script** `<scratch>/split.py`, run once from the repository root.

- It reads `git show <base>:SPECIFICATION.md`. Each cut is the one line that starts with a prefix
  below; the script asserts that each prefix matches exactly one line. A slice runs from its cut to
  the line before the next cut.
- Files are under `specification/`:
  - `## 1. ` `01-introduction.md`; `## 2. ` `02-product-overview.md`; `## 3. ` `03-requirements.md`;
    `## 4. ` `04-physics.md`.
  - `## 5. ` `05-software-design/index.md`; `### 5.1 ` `…/01-architectural-overview.md`;
    `### 5.2 ` `…/02-pipeline-stages.md`; `### 5.3 ` `…/03-1-case-file.md`; `#### 5.3.2 `
    `…/03-2-artefacts.md`; `#### 5.3.3 ` `…/03-3-provenance-manifest.md`; `#### 5.3.4 `
    `…/03-4-sweeps.md`; `### 5.4 ` `…/04-component-design.md`; `### 5.5 ` `…/05-extension-points.md`;
    `### 5.6 ` `…/06-architecture-decisions.md`.
  - `## 6. ` `06-numerics.md`.
  - `## 7. ` `07-verification/index.md`; `### 7.1 ` to `### 7.6 ` give `01-strategy.md`, `02-tier-1.md`,
    `03-tier-2.md`, `04-tier-3.md`, `05-tier-4.md` and `06-continuous-integration.md`. `### 7.5.1` is
    not a cut.
  - `## 8. ` `08-implementation-plan/index.md`; `### 8.1 ` `…/01-phases-and-gates.md`; `### 8.2 `
    `history/00-phase-0-exit-criteria.md`.
  - `#### 8.2.<k> ` gives `history/<kk>-<slug>.md` for k = 1 to 16. The slug is the heading after its
    number, lower-cased, with each run of other characters made `-`, and cut to 50 characters.
  - `### 8.3 ` `08-implementation-plan/03-effort-estimate.md`; `## 9. ` `09-risks.md`; `## 10. `
    `10-open-items.md`; `## 11. ` `11-companion-knowledge-base.md`; `## 12. ` `12-references.md`;
    `## Appendix A.` `a-traceability-matrix.md`; `## Appendix B.` `b-comsol-settings.md`.
- Every file except an `index.md` opens with this block, then a blank line, then its slice:

  ```
  ---
  type: Specification            # Ruling Record under history/
  title: "<its first heading, without the #s>"
  description: "<one sentence, at most 25 words, on what the file specifies>"
  ---
  ```

  The script writes `TODO` for the description. The executor then fills each one from the file's
  first paragraph, and changes no other line.
- `08-implementation-plan/02-rulings.md` gets the block (title `8.2 Rulings by date`), then
  `### 8.2 Rulings by date`, a blank line, and: "The Phase 0 exit criteria and the author's dated
  rulings, §8.2.1 to §8.2.16, are the [history](../history/index.md), read on demand. The rules in
  force that have no clause of their own are §8.4."
- `SPECIFICATION.md` is cut to the lines before `## 1. Introduction`. Files are UTF-8, with `\n`
  endings and one final newline.

**Item 7, the site.**

- `docs/scripts/generate.py:_copies`: after the knowledge loop, add the same loop over
  `ROOT / "specification"`, with destination `OUTPUT / "model" / "specification" / <relative path>`.
  The docstring's model bullet names `SPECIFICATION.md`, the `specification/` bundle and `knowledge/`.
- `mkdocs.yml`: the line `      - Specification: _generated/model/specification.md` becomes a
  `Specification:` section:
  - the entry point, then `specification/index.md`;
  - one `"<title>": <path>` entry per file, in `clause.py`'s order;
  - each of the three directories and `history/` as a nested section that opens with its `index.md`.

  Paths are `_generated/model/specification/<relative path>`. The knowledge markers stay untouched.
- Guide links, each keeping its anchor and taking the prefix `../_generated/model/specification/`:
  - `#44-…` goes to `04-physics.md`;
  - `#531-case-file` goes to `05-software-design/03-1-case-file.md`;
  - `#521-…` and `#522-…` go to `05-software-design/02-pipeline-stages.md`.

  Links without an anchor stay.

### Work items

`main` is the Sonnet 5.5 session. A sub-agent item goes to `general-purpose` on Haiku, with the item
and its *Implementation details*, and `main` re-runs its check.

- [x] no commit. 1. The R10 check scripts in `<scratch>`, self-tested (D5); no commit. **Executor:**
  `general-purpose`, Haiku.
- [x] 24cea0e. 2. `specification/` sliced, front matter filled, `SPECIFICATION.md` cut (D1, D2, D4). Done
  when `lines.py` reports 0. **Executor:** `general-purpose`, Haiku.
- [x] eed4f2e. 3. `SPECIFICATION.md` completed as the entry point; `specification/index.md`,
  `history/index.md` and the directory indexes written; §11's table gains the three (D2, D4). Done
  when the code and review say so. **Executor:** `main`.
- [x] 5a542d7. 4. `.claude/scripts/clause.py` reads the bundle (D5). Done when `ids.py` reports 0.
  **Executor:** `main`.
- [x] checkpoint. 5. Compaction checkpoint; the prompt carries `<base>`. **Executor:** `main`.
- [x] a33baa3. 6. `04-development-process.md` (D3); `history/index.md`'s *where it holds now* for all 119
  rulings; `CLAUDE.md` and `.claude/rules/python.md` cite §8.4. Done when the code and review say so.
  **Executor:** `main`: judgement on normative text.
- [x] d648802. 7. `docs/scripts/generate.py`, `mkdocs.yml` and the guide's links (D5). Done when VER-45's build
  passes. **Executor:** `general-purpose`, Haiku.
- [x] 8. `docs/plans/phase-4-record.md`, the Phase 4 plan rewritten (D6), `current.md`,
  `CHANGELOG.md`'s `0.5.0-alpha.18` section. Done when the code and review say so. **Executor:** `main`.
- [ ] 9. Compaction checkpoint. **Executor:** `main`.
- [ ] 10. Both R10 checks re-run on the final tree, their output and `<base>` into the Outcome, with
  criterion 14's word counts (current files, `history/`, §8.4, the Phase 4 plan). Done when they
  pass. **Executor:** `main`.

### Verification

No kept test (N1). The checks are one-off scripts in the scratchpad, run in the pull request (R10):

| Check | Oracle | Command | On a miss |
|---|---|---|---|
| R10 (a), lines | For every non-blank, right-stripped line of `git show <base>:SPECIFICATION.md`: its count across `SPECIFICATION.md` plus `specification/**/*.md` is at least its old count (a `Counter` difference) | `uv run --no-project python <scratch>/lines.py <base>` | A missing line is restored. Any line edited on purpose is listed in the Outcome with its reason; the target is none, since §11 gains rows and edits none |
| R10 (b), identifiers | For each identifier of base Appendix A (149) and each base ruling (119): the base `clause.py`, run in a `git worktree` of `<base>`, and the new `clause.py` print the same text in their **first** `definition` block, labels excluded | `uv run --no-project python <scratch>/ids.py <base>` | The bundle or the script is fixed; no waiver |
| VER-45 | Strict build | `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | Fixed before the merge |
| Gate | Full push gate | `.claude/hooks/gate.sh run` | Fixed |

### Out of scope

- Rewriting the skills to the new layout, beyond the PR step and R11, including where `/phase-plan` writes a ruling and R3's rule
  that every ruling also lands in a current clause: WP53. Until it merges, an amendment writes its
  table into a new `history/` file, and its rules into §8.4.
- Splitting `knowledge/` (R9); rewording any clause.

### Open questions

The verbatim record (In brief): the plan follows the recommendation unless ruled otherwise.
