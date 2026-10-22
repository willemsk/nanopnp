# WP53 — The workflow: three commands with levels, and a current checkout

PR: [#124](https://github.com/willemsk/nanopnp/pull/124), branch ccr-a62c64fc-ixc0r7

**Status: planned, not started.** Written 22 October 2026; grounded in the code at `e4b52bc`
(§8.2.15 Q1). Inherits WP52 as merged and the Phase 4 amendment (§8.2.16 R5 to R7, R11, R12).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** The four working instructions a session follows to plan a phase, plan a package,
build it and ship it become three commands, plan, implement and ship, each told what level it works
at: the whole project, a phase, an amendment or one package. Each loads a short shared part and the
part for its level. The commands carry a short project prefix, because the plain
word plan is already taken by the tool itself outside a terminal. The script that starts every
session brings the author's main copy of the code up to date when that is safe, and says so when it
is not, so a session no longer works from instructions months old.

**Cost.** One pull request, one session. Nothing a user of the program runs changes.

**What could go wrong.** A rule could be lost when the instructions are cut and moved: a script lists
every old sentence missing from the new text, and each is accounted for before the merge. The start
script could change the author's copy unexpectedly: it only ever moves a clean main copy forward, and
it is tried against ten prepared copies. The new commands could fail in practice: the next package is
the first planned, built and shipped with them.

**Your call.** Should the old command names be kept as aliases for a while? *Recommendation:* no;
each listed command costs every session a little reading, and a mistyped old name fails at once.

## Execution brief

Scope: the Phase 4 plan's WP53 (§8.2.16 R5 to R7), named by R12. No identifier is claimed and no
test is kept (N1); WP54's sessions are the live check. Pointers: R3, R4, R6, R11; §8.4.1, §8.4.4,
§8.4.5. Implemented by a Sonnet 5.5 session at high effort, through the old `/wp-implement` and
`/wp-ship`, since the new commands exist only once this package merges.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Names, routing, aliases | `/np-plan <project \| phase n \| amend n \| wp n>`, `/np-implement [wp n]`, `/np-ship [wp n \| phase n]`. Each `.claude/skills/np-<verb>/SKILL.md`, at most 150 words, reads `.claude/workflow/core.md`, then the level file beside it. With no argument, `/np-implement` and `/np-ship` take the package `current.md` names for that step, and ask if it names none or several. A missing or unknown level prints the usage and stops. **No aliases**: the four old skill directories are deleted; records keep the old names | R5, R12. Every session reads each listed skill's description; an old name fails visibly |
| D2 | What the core and the levels hold | `core.md`, at most 900 words: reading order; the branch rule; normativity and where a change of behaviour lands; models and executors; the records table; the In brief template; gate and push; the PR contract (lookup, title, body, the `PR:` line); report and stop. Levels: `np-plan/{wp,phase,amend,project}.md`, `np-plan/rulings.md` (read by `phase`, `amend` and `project`), `np-implement/wp.md`, `np-ship/{wp,phase}.md`. **Text moves verbatim** from the old skills; a sentence is edited only for a name, a path, a section reference, or R3, R4, R12. One invocation loads at most 2,200 words (router, core, level, `rulings.md` where read); the new files total at most 7,000 | R5. Moving, not retyping, makes D6's check possible |
| D3 | Rulings and plan amendments | `rulings.md` holds the ruling round (old `phase-plan` Turn 1, steps 4 and 5) and three rules. A round's table is a new `specification/history/<kk>-<slug>.md`, listed in `history/index.md` with a `* <id> - <where it holds now>` line per ruling; each ruling amends its clause in the same commit, or is restated in §8.4 when it sets a standing process rule with no clause (R3). A ruling taken at a package's plan on a record's date is a row added to that record, marked *Added <date>, at WP<n>'s plan.*, and a superseded ruling gains only a pointer in its first cell (R11, R12). A phase plan's entry is rewritten to its current scope with no `Amended` blockquote, and the amendment's text is appended to `docs/plans/phase-<n>-record.md` as `## Amended <date> (§8.2.<k> <ids>)`; a missing record is created with `phase-4-record.md`'s header (R4) | R3, R4 |
| D4 | The new levels | `/np-plan project` runs the ruling round on §8.1's rows and the later phases, then amends §8.1, §3's Release column, §2.7's Versioning NOTE, §8.3 and the later plans where they move, in one commit `docs: re-plan the project (§8.2.<k>)`. `/np-ship phase n` resolves the phase's close package from the phase plan, runs `np-ship/wp.md` on its PR, and before the review confirms the close's items (*Implementation details*); after the merge it pushes the annotated release tag if access allows, else prints the commands. Release tag alone (§8.4.1) | R5; `CONTRIBUTING.md` |
| D5 | The hook (R7) | Before the sync, `.claude/hooks/session-start.sh` finds the primary checkout through `git rev-parse --git-common-dir` and fetches `origin main`. On `main`, clean, with `HEAD` an ancestor of `origin/main`: `git merge --ff-only origin/main` (the two halves of `git pull --ff-only`), reported. On `main` but dirty or diverged, and on another branch or a detached `HEAD` that lacks `origin/main`: a warning, no write. A checkout that contains `origin/main` is silent. A failed fetch warns once. Nothing fails the session | R7; the Phase 4 plan leaves these cases to this plan. Warning an up-to-date branch would fire in every hosted session |
| D6 | Checks | No kept test (N1). Three one-off checks, outputs in the Outcome: `rules.py` lists each sentence of the four old skills that no new file contains, and each is accounted for as edited or dropped, with a reason; `hook-check.sh` runs ten prepared repositories through the hook; a grep finds the old names only in records. D2's word counts | WP52's R10 pattern, with no waiver |

### Grounding

**D1.**

- `/plan` is a built-in command that enters plan mode. A project skill of the same name replaces a
  built-in only in a local terminal session (Claude Code docs, *Resolve skills that share a name*). No
  built-in or bundled `/np-*` exists.
- A skill reads its arguments as `$ARGUMENTS`, `$0`, `$1`. `${CLAUDE_SKILL_DIR}` is the directory of
  its `SKILL.md`. A router names a level file as `${CLAUDE_SKILL_DIR}/wp.md`, and the core as
  `${CLAUDE_SKILL_DIR}/../../workflow/core.md`. In a desktop-app worktree session, skills and hooks
  are read from the main checkout. Repository-relative paths would then read the worktree's copies,
  possibly at another version.
- `.agents/skills.json` points Antigravity at `.claude/skills`, where `${…}` is not substituted. The
  router therefore also says "the `wp.md` beside this file".
- Skill edits on disk are picked up within a session, `SKILL.md` text included. A fast-forward made
  by the hook therefore reaches the session that ran it.
- The old skills are `.claude/skills/{phase-plan,wp-plan,wp-implement,wp-ship}/SKILL.md`, at 1,907,
  1,628, 1,187 and 1,505 words: 6,227 in all. `steward` (1,603) and `.claude/agents/` stay.

**D2.**

- Cross-references to rewrite: `wp-plan` and `wp-implement` cite "`wp-ship` §3" for the PR contract,
  and `wp-implement` cites "`wp-ship` §0" for the `PR:` line. `CLAUDE.md` cites "`wp-ship` §4". All
  become the core's *PR contract* or `np-ship/wp.md`'s *Review pass*.
- Shared text today: the In brief template (in `wp-plan` and `phase-plan`, restated in
  `wp-implement`), gate-and-push (all four), the branch rule (three), the PR contract (three) and the
  records table (`wp-implement`). Each is written once, in the core.
- R6's worker pattern is already in `wp-plan` (*Work items*) and `wp-implement` (*Sub-agent items*):
  R11 landed it. It moves verbatim to `np-plan/wp.md` and `np-implement/wp.md`.

**D3.**

- *Changing the specification* in `SPECIFICATION.md` states the history-file rule. The record form is
  the front matter `type: Ruling Record`, `title`, `description`, then `#### 8.2.<k> <title>`, as in
  `specification/history/16-…`.
- `history/index.md` lists each record as `* [title](file) - description`, then one
  `* <id> - <home>` line per ruling. The site's navigation is generated from the index (REV-124).
- `docs/plans/phase-4-record.md` opens with a title, a paragraph and `---`; nothing is yet appended
  but this plan's R12 section.
- The old `phase-plan` writes "a §8.2.x subsection" and `> **Amended**` blockquotes. Both rules are
  replaced.

**D4.**

- The close's items are in the Phase 4 plan, *The close package*, and in the old `phase-plan`,
  *Breaking the phase into packages*. Tags are annotated (`git tag -a`, `git push origin <tag>`). A
  hosted session's clone is shallow, with no tags in reach.

**D5.**

- `session-start.sh` sets `root=${CLAUDE_PROJECT_DIR:-…}` and `cd`s there, runs `uv sync` under
  `set -e` only when `CLAUDE_CODE_REMOTE=true`, then `set +e`, the Gmsh probe and the summary. Its last
  line names the old workflow. `.agents/hooks/adapter.sh session-start` runs the same script.
- In a desktop-app worktree session, `${CLAUDE_PROJECT_DIR}` is the main checkout. A `claude
  --worktree` session can start in a linked worktree, so the primary checkout is the parent of
  `git rev-parse --path-format=absolute --git-common-dir` (git 2.31 or later; here 2.43).
- A hosted session's clone is shallow and on its own branch, forked from `main` at start. Ancestry
  (`git merge-base --is-ancestor`) still decides there; counts are quoted only off a shallow clone,
  as the hook's position line already does.
- `timeout` is not on macOS by default. The hook already tests `command -v timeout`.

**D6.**

- Live mentions of the old names, outside records: `CLAUDE.md` (*Testing*, *Implementation
  workflow*), §8.4.3 and §8.4.4, `steward` (*Bounded wakes*), `.github/pull_request_template.md`,
  `docs/project/review-findings.md` (its opening paragraph), `docs/project/modularity.md`
  (paragraph 1), `wp55-user-testing-protocol.md`, the Phase 4 plan, `current.md` and the hook.
- Records keep them: `specification/history/`, delivered plans, `phase-4-record.md`,
  `docs/code_reviews/`, `docs/superpowers/`, `review-items.md`, the REV-87 row and
  `knowledge/07-software-stack/15-…` (a source footnote).
- `.claude/hooks/session-start.sh` is not prose for `.github/scripts/prose-only.sh`, so the push gate
  runs in full.

### Implementation details

`<base>` is `e4b52bc`. Scripts live in the scratchpad, `<scratch>`. They use the standard library
and run as `uv run --no-project python`.

**Item 1, `rules.py <base> [--self]`.** *Old*: the four old `SKILL.md`s read with `git show <base>:…`.
*New*: `.claude/workflow/core.md` and `.claude/skills/np-*/*.md`, or with `--self`, the old files
again. For each file:

- drop the front matter;
- split it into blocks (paragraph, list item, table row, heading, fenced block);
- strip the list markers, `#`s and table pipes;
- collapse whitespace.

On *old* only, apply in this order: `/phase-plan amend`→`/np-plan amend`, `/phase-plan`→`/np-plan
phase`, `/wp-plan`→`/np-plan wp`, `/wp-implement`→`/np-implement`, `/wp-ship`→`/np-ship`, then
bare `phase-plan`→`np-plan`, `wp-plan`→`np-plan`, `wp-implement`→`np-implement`,
`wp-ship`→`np-ship`. Split each old block into sentences at whitespace after `.`, `?` or `!` and
before a capital, `` ` ``, `*` or `(`. A sentence is found if it is a substring of the new text, its
blocks joined by single spaces. Print each missing sentence with its old file, then `missing: N`.
Exit 0. `--self` must print `missing: 0`.

**Item 3, `np-ship/phase.md`'s close checks**, before the review: every other package of the phase
merged; each *Open decisions* row resolved or carried; each findings log's header `closed` and every
`REV-nn` row the phase owns `fixed`; the end-of-phase numbers re-run on this tree; `CHANGELOG.md`'s
`[X.Y.0]` section; `CITATION.cff`'s `version` and `date-released`; `current.md` pointing at the next
phase. Then the tag: `git tag -a vX.Y.0 <merge sha> -m "vX.Y.0"` and `git push origin vX.Y.0`.

**Item 5, `hook-check.sh <hook>`.** Make a bare `origin`, seed `main` with two commits, then clone.
Run the hook as `CLAUDE_PROJECT_DIR=<dir> bash <hook> </dev/null`, unset `CLAUDE_CODE_REMOTE`.
Assert exit 0, the expected line and `HEAD` before and after, one line each:

1. `main` clean, two behind: fast-forwarded, `HEAD` = `origin/main`.
2. `main` dirty, behind: warning, unchanged.
3. `main` diverged: warning, unchanged.
4. `main` current: no line.
5. A branch containing `origin/main`: no line.
6. A branch behind: warning.
7. A detached `HEAD` behind: warning.
8. `origin` pointing at a missing path: the fetch warning, within 5 s.
9. `CLAUDE_PROJECT_DIR` a linked worktree, the primary on clean `main`, behind: primary
   fast-forwarded, worktree unchanged.
10. A `--depth 1` clone, `main` behind: fast-forwarded.

**Item 6, the pointer edits.**

- `CLAUDE.md`:
  - *Testing*: `/wp-ship` → `/np-ship`.
  - *Implementation workflow*: the table's rows become `0 | /np-plan project`, `/np-plan phase <n>`,
    `/np-plan amend <n>`; `1 | /np-plan wp <n>`; `2 | /np-implement [wp <n>]`;
    `3–4 | /np-ship [wp <n>]`; and a new row `close | /np-ship phase <n>` ("Ships the close package
    and tags the release").
  - The next sentence becomes: "Step 2 does not chain into 3: `/np-ship` starts in a fresh session
    (`np-ship/wp.md`, *Review pass*). Plans before WP53 name these `/phase-plan`, `/wp-plan`,
    `/wp-implement` and `/wp-ship`."
- `steward/SKILL.md`, `.github/pull_request_template.md`, the opening paragraph of
  `review-findings.md`, `modularity.md` paragraph 1, `wp55-user-testing-protocol.md`, and the Phase 4
  plan's status line and *Context*: substitute by item 1's map.

### Work items

`main` is the Sonnet 5.5 session. A sub-agent item goes to `general-purpose` on Haiku, with the item
and its *Implementation details*; `main` re-runs its check.

- [x] 1. `<scratch>/rules.py` (D6); no commit. Done when `--self` prints `missing: 0`. **Executor:**
  `general-purpose`, Haiku.
- [x] 277b468 2. `.claude/workflow/core.md` and `.claude/skills/np-plan/` (`SKILL.md`, `rulings.md`, `wp.md`,
  `phase.md`, `amend.md`, `project.md`) (D1 to D4). Done when the code and review say so.
  **Executor:** `main`: normative process text.
- [ ] 3. `.claude/skills/np-implement/` and `np-ship/` (`SKILL.md`, `wp.md`; `np-ship/phase.md`); the
  four old skill directories deleted (D1, D2, D4). Done when `rules.py <base>` runs and each missing
  sentence is accounted for in the Outcome. **Executor:** `main`.

  > **Outcome — 43 of the old skills' sentences are not carried verbatim, each by design.**
  > `rules.py e4b52bc` on item 3's tree printed `missing: 43` (`--self`: 0). Grouped by reason:
  >
  > - *Written once in the core* (16). The branch rule (`phase-plan` precondition 1, `wp-plan`
  >   Finishing 2); gate and push (`wp-plan` Finishing 2's other two sentences, `phase-plan`
  >   Finishing 2, `wp-implement` Finishing, `wp-ship` §1's "Also confirm: `git status` clean" and
  >   §2's `git push`); the PR lookup, creation contract and body (`wp-ship` §3's three); the PR
  >   body's In brief (`wp-implement`'s two sentences, restating the template); the `PR:` line
  >   (`wp-plan` Finishing 3, and `wp-implement`'s, which cited "`wp-ship` §0"); `phase-plan`'s
  >   shorter "The plan points into it and never restates it.", which the core's normativity
  >   paragraph contains. `wp-plan`'s "A plan-only change runs ruff and the tests" is replaced by
  >   the core's sentence on what a Markdown-only change runs.
  > - *A section reference* (10). "the template below" in both plans' In brief rows (now "the core's
  >   template"); "the lookup and title/body contract of `wp-ship` §3" (`wp-plan`, `wp-implement`)
  >   and "the `wp-plan` template" (`phase-plan` Finishing 3), now the core's; "this skill's *How
  >   the work lands*" (now "this file's"); *Amending a phase* in `phase-plan`'s intro and
  >   precondition 2 (now `amend.md`); the amendment's "as in Turn 1 steps 4–5" and "as in
  >   *Finishing*" (now `rulings.md` and `phase.md`'s *Finishing*).
  > - *R3: a ruling round is a history record, not a §8.2.x subsection* (8). `phase-plan`'s
  >   deliverables sentence; "this skill decides" (now "this level"); its collect step 2, which
  >   read every §8.2.x section (now §8.4 and the history index); "A ruling that changes a clause
  >   … the §8.2.x row names the clause" (now in `rulings.md`, naming the ruling's row); the three
  >   sentences of *What to write*'s §8.2.x paragraph (now `rulings.md`'s *Where the rulings are
  >   written*); the amendment's "New rulings get a new §8.2.x subsection".
  > - *R4: a plan states its current scope* (1). "An amended package entry gains a `> **Amended**`
  >   blockquote …; the original paragraph stays", replaced by the rewrite and the record.
  > - *D1's levels* (5). `wp-ship` §0's "The argument is a PR number or a WP number" and "For a WP
  >   number, list open PRs …" (now `wp <n>`, or the package `current.md` names); the amendment
  >   section's heading, its first sentence, naming `/phase-plan amend`, and "The same two turns
  >   apply." (now `amend.md`'s opening, naming `/np-plan amend <n>` and `phase.md`).
  > - *Dropped* (3). `phase-plan`'s *Rules the plan must respect* heading and its sentence: the
  >   rules files are read at its step 2 and the normativity rules are the core's.
  >   `wp-implement`'s "Check the branch.", a heading word for the core's branch rule.
  >
  > Word counts on this tree: core 799, routers 101 to 137, and 7,208 words in all. Invocations:
  > `np-plan wp` 2,351, `phase` 2,729, `amend` 1,791, `project` 1,931; `np-implement` 1,687;
  > `np-ship wp` 2,200, `phase` 2,455. The total and four invocations exceed D2's caps; item 9
  > reports the final figures.
- [ ] 4. Compaction checkpoint; the prompt carries the scratch path. **Executor:** `main`.
- [ ] 5. `.claude/hooks/session-start.sh`: the fast-forward and warnings, and the workflow line
  (D5); `<scratch>/hook-check.sh`. Done when its ten cases pass and `bash -n` is clean.
  **Executor:** `main`.
- [ ] 6. The pointer edits of *Implementation details*. Done when the code and review say so.
  **Executor:** `general-purpose`, Haiku.
- [ ] 7. §8.4.3 and §8.4.4 name the new commands; `history/index.md` sets R5 and R12 to §8.4.4 and
  R7 to `.claude/hooks/session-start.sh`; the Phase 4 plan's delivered summary; `current.md`;
  `CHANGELOG.md`'s `0.5.0-alpha.19` section. Done when the code and review say so. **Executor:**
  `main`.
- [ ] 8. Compaction checkpoint. **Executor:** `main`.
- [ ] 9. D6's checks and word counts on the final tree, into the Outcome. Done when each passes.
  **Executor:** `main`.

### Verification

No kept test (N1). One-off checks, run in the pull request:

| Check | Oracle | Command | On a miss |
|---|---|---|---|
| Rules kept | Each sentence `rules.py` prints is in the Outcome as edited (its new file) or dropped (why) | `uv run --no-project python <scratch>/rules.py e4b52bc` | Restored, or accounted for |
| Hook | Cases 1 to 10, each with its expected line and `HEAD` | `bash <scratch>/hook-check.sh .claude/hooks/session-start.sh` | Fixed |
| Names | `grep -rnE '\b(phase-plan\|wp-plan\|wp-implement\|wp-ship)\b' --exclude-dir=.git --exclude-dir=.venv .` hits only the records of *Grounding* D6 and this plan | as written | The live mention is repointed |
| Caps | D2: router ≤ 150, core ≤ 900, invocation ≤ 2,200, total ≤ 7,000 words, by `wc -w` | `wc -w .claude/workflow/core.md .claude/skills/np-*/*.md` | Cut, or reported |
| VER-45 | Strict build | `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | Fixed |
| Gate | Push gate | `.claude/hooks/gate.sh run` | Fixed |

### Out of scope

- In a desktop-app session the hook's summary names the main checkout's branch, not the
  worktree's: not R7's.
- `steward` and the agents, beyond one name; the knowledge base (R9).

### Open questions

The aliases (In brief): the plan follows the recommendation unless ruled otherwise.
