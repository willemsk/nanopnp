# WP6.02 — The cleanup: the reading measured, the instructions audited, the records cut

**Status: delivered, 22 November 2026.** Written 22 November 2026, grounded in the code at `eacad07`. Inherits §8.2.47 AW5,
§8.2.49 AY5, AY7 and AY8, §8.2.50 AZ4, AZ7 and AZ9 to AZ12 (ruled at this plan), REV-271, REV-272 and the test scope
(§8.2.13 N1, N3). It starts after WP6.01 merges; its last commit on `main` takes `v0.7.0-alpha.2` (§8.4.1).

**Delivered.** `usage.py --reading` counts the project text a window reads before its first edit; the
[baseline](../sessions/reading-baseline.md) of twelve sessions gives a fresh `/np-implement` window a median of 8,095
words. The [audit](../sessions/instructions-audit.md) found no stale fact and three findings that matter (F1 to F3), its
diff WP6.03's. The author set the limit at 6,500 words from WP6.03's merge (AZ13, against the recommended 5,500) and a
phase plan at 2,500 (AZ14; REV-271 fixed). `clause.py` prints a spent ruling as one line (AZ11). `archive_items.py`
moved 220 closed review items to the archive, and `decisions.py` writes the closed decisions to a second page
(AZ12): the register fell from 61,248 to 20,690 words, `decisions.md` from 75,431 to 25,751. At the review the author
ruled that the limit binds only a session's first window (AZ15, against the recommendation), that a combined
command's print counts (AZ16) and that only an edit tool ends the count (AZ17). Live: AZ13's limit as AZ15 to AZ17
count it; the Outcome's outdated list for WP6.03 and the rescoping round.

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.02 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** A session reports how much of the project's own text it read before its first edit, and the last
six packages are measured too, so the cleanup has a number to beat. The instruction files get an audit that
lists each outdated or contradicting instruction with a proposed change; the changes are the next package's. Then the
records are cut to what binds. The review register keeps its 60 live items, and the 218 closed ones move to an
archive. The decisions page shows about 490 decisions that bind now, and a second page lists the rest. Nothing leaves
the record of your rulings; a lookup stops printing spent ones in full. It ends with a list of what it found
outdated, for the rescoping round.

**Cost.** About six sessions, four to seven hours of agent work and twelve times you act, four of them today's
answers. A user of the program sees no change.

**What could go wrong.** The session service could stop serving an old session: the baseline names it and uses the
rest. A link to a moved item could break: every moved link is checked, down to its heading. The baseline could show
that the records are a small part of what a session reads, as today's one measurement does: 16,000 words of project
text inside about 180,000 tokens. You then set the limit knowing it.

**Your call.** Settled today: what the limit counts, its baseline, the history and the closed items. Inside the
package, after the baseline: what number is the limit, and how long may a phase plan be? *Recommendation:* decide
both from the baseline's table.

## Execution brief

Scope: the Phase 6 plan's WP6.02 entry; AY8; AZ9 to AZ12; REV-271. It depends on WP6.01's merge, and merges `main`
before item 1. It claims no new identifier and writes no test: the scripts are workflow tools outside the test scope
(N1), and the kept tests of VER-61 and VER-79 stay green. **Implementing session: Fable 5.2, high effort** (§8.4.5;
AY7). APIs: the standard library and PyYAML; the session service's `list_events`, whose page form item 2 reads before
it relies on it.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The measure** | `usage.py --reading` prints, for each window that an `/np-` command opens, the words of project text read before the first `Edit`, `Write` or `NotebookEdit`: instructions, records and `CLAUDE.md`. Beside them it prints the words of code and of command output, the tokens at the window's start and at that edit, and the ten largest files. A window is fresh when no message precedes it, or its start holds under half the tokens of the message before it. The limit binds a fresh `/np-implement` window | Ruled by the author, §8.2.50 AZ9; the window kind and "fresh" decided by the plan, confirmed at D4 |
| **D2 The baseline** | Sub-agents page the events of the twelve sessions of WP5.19, WP5.20, WP5.21, WP5.27, WP5.28 and WP6.01 with `list_events`; `usage.py --reading --pages` reads the pages through the sub-agents' transcripts. The pages stay on the session's machine, outside the tree. `docs/plans/sessions/reading-baseline.md` holds the table. A session not served is named and left out | Ruled by the author, §8.2.50 AZ10 |
| **D3 The audit** | The `claude-api` skill's `prompt-audit`, over `CLAUDE.md` and `.claude/`, run as its guide says. Its report, with the proposed diff, is `docs/plans/sessions/instructions-audit.md`. This package applies no hunk | AY8; the phase entry gives the changes to WP6.03; decided by the plan |
| **D4 The stop** | Item 5 puts two questions to the author with the baseline's table: the limit's number, and a phase plan's word target. It records the answers as AZ13 and AZ14, or the next free pair, writes both into §8.4.4, and sets REV-271 `fixed` | AY8 ("proposes a limit to the author from it"); AW5; decided by the plan |
| **D5 The history** | No row leaves a record. `clause.py` prints a ruling that only names the identifier, and that `holds-now.yaml` gives as `spent` or `superseded by`, as one line; `--all` prints it in full. An `open:` entry whose owner no longer exists is restated where a later ruling names the new owner, and listed under D7 otherwise | Ruled by the author, §8.2.50 AZ11; the `open:` pass decided by the plan |
| **D6 Closed items** | A kept script, `archive_items.py`, moves each `fixed`, `declined` or `wontfix` row with its section to `docs/project/review-archive.md` and rewrites every link to it. `decisions.py` writes the rows that bind to `decisions.md` and the rest to `decisions-closed.md`. A phase's close runs the mover | Ruled by the author, §8.2.50 AZ12; the script and the close's step decided by the plan |
| **D7 The outdated list** | The plan's Outcome lists, in at most 400 words, each decision, owner or instruction found outdated and not fixed here, with its file and the step that takes it: WP6.03 or the rescoping round. It gives the baseline's tokens at a session's start and names what loads them | The phase entry; AZ7; decided by the plan |
| **D8 The records** | §8.4.4 to §8.4.6 and `CLAUDE.md`'s list of scripts say what each script does, in its item's commit. `CHANGELOG.md` gains `## [0.7.0-alpha.2]`. REV-272's section gains the cut's word counts | The core, *Normativity*; §8.4.1; decided by the plan |

### Grounding

**D1**

- `.claude/scripts/usage.py:_transcript` finds the JSONL of `$CLAUDE_CODE_SESSION_ID`; `_events` loads it; `_typed`
  tells a prompt the author typed; `_start` opens one window, at the last prompt that holds `/np-`; `measure` counts
  tokens once per `message.id`. None reads a tool call's input or result. The mode adds a function and leaves
  `measure` and the `Measured (…)` line as they are.
- A local event is `{"type": "assistant", "message": {"id", "model", "content": [...], "usage": {...}}}`. `usage`
  holds `input_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens`. A tool call is a content block
  `{"type": "tool_use", "id", "name", "input"}`. Its result is a block `{"type": "tool_result", "tool_use_id",
  "content"}` of a `user` event; `content` is a string, or a list of `{"type": "text", "text"}`.
- `Read`'s input has `file_path`, `Bash`'s has `command`, `Grep`'s has an optional `path`.
- A `Read` result starts each line with its number and a tab. Counted as it is, it adds a word per line.
- The typed prompt holds `<command-name>/np-…</command-name>` and the arguments alone. The skill's text is the next
  `user` event, with `isMeta` true, which `_typed` refuses; its text starts `Base directory for this skill:`. A
  `Skill` call's text arrives the same way.
- `CLAUDE.md` and a path-scoped rule arrive as attachments, which no tool result shows. `CLAUDE.md` holds 2,220 words;
  the two rules hold 715, which the measure does not see.
- A prototype on this plan's session gave 93,575 tokens at the start. Before the first edit it gave 5,497 words of
  instructions, 8,327 of records and 13,325 of command output, inside 182,043 tokens of growth; one loaded skill was
  about 80,000 of them.

**D2**

- A cloud session's transcript goes with its machine (AM11). `mcp__claude-code-remote__list_sessions` lists sessions
  by title, such as `NP plan WP 5.27` and `NP-implement WP 5.27`; a plan's review and a package's ship are later
  windows of those sessions.
- `list_events` pages one session, newest first. With `kinds: ["assistant", "user"]` and `limit: 100`, the next call
  takes `before_id` set to the page's `first_id`; the last page has no `has_more`. `limit` counts events before the
  filter. A probe of a 20-minute session took 5 calls for 374 events.
- A page event is `{"created_at", "assistant": {"internal_anthropic_catchall": {"message", "parent_tool_use_id",
  "session_id", "timestamp"}}}`, or the same under `"user"`; `message` has the local form. One API message is one
  event per content block, each with the same `usage`. A sub-agent's event has a `parent_tool_use_id`.
- A small page comes inline, in the calling agent's transcript, `<project>/<session>/subagents/*.jsonl`, which
  `measure` already globs. A page over the inline limit is not in it: the tool result names a file,
  `<project>/<session>/tool-results/mcp-claude-code-remote-list_events-*.txt`, which opens with an
  `<other-session …>` notice before the JSON `{"ccr": {"data": [...], "has_more", "first_id", "last_id"}}`.
- The probe's page events show no `isMeta`. Whether a page marks a skill's text is read at item 2, step 1.
- The probe saw no marker of a compaction; D1's "fresh" needs none.

**D3**

- The skill's `shared/prompt-audit.md` sets the steps: the scope and target model stated, the inventory, `git blame`
  for provenance, the pattern scan, a report ordered by confidence, and a proposed diff with one finding per hunk at
  high or medium confidence. Each finding has a location, the evidence quoted, the pattern, why it is obsolete, a
  confidence and an action. The guide does not read `.claude/settings*.json`, and applies no edit unasked.
- Target models: Fable 5.2 for `CLAUDE.md`, the rules, the core and the `np-plan` and `np-ship` skills; Opus 5.5
  for `np-implement`; for each agent file, the model it pins.
- `docs/plans/sessions/` holds standalone briefs (AL5); `index_records.py` indexes it.

**D4**

- `.claude/skills/np-plan/phase.md` says "Target 1,500 words, without the report"; §8.4.4 gives a phase plan no
  number. The Phase 6 plan holds 1,877 words; the Phase 5 plan held 8,206 at its largest (REV-271).
- Record 50 of the history holds AZ1 to AZ12; `np-plan/rulings.md` gives the form of an added row.

**D5**

- `clause.py:clause` prints the definitions and NOTEs, then each history row that matches the identifier, labelled
  `ruling [superseded]` when `SUPERSEDED_ROW` matches its first cell. It reads no `holds-now.yaml`.
- `holds-now.yaml` has 409 entries: 62 start `spent`, 18 start `superseded by`, 34 hold `open:`. AA6 and AV6 are both
  `superseded by AY5`, and `clause.py AY5` prints both in full today.
- `test_ver79_every_ruling_has_one_holds_now_entry` keeps one entry per ruling.

**D6**

- `docs/project/review-findings.md` opens with the front matter `findings:` (`prefix: REV`, `status: open`,
  `areas`), then one table `ID | Area | Severity | Status | Ruling | Finding`. Of its 278 rows, 207 are `fixed`, 7
  `declined`, 4 `wontfix`, 39 `accepted`, 17 `deferred`, 3 `post-1.0` and 1 `open`. Each *Finding* cell links
  `review-items.md#rev-<n>-<slug>`.
- `review-items.md` has `## Items`, then one section per item, headed `### REV-<n> — <title>` or
  `### REV-<n>: <title>`, and one in-page `(#rev-…)` link.
- The log's readers: `decisions.py:registers`, a tuple of two file names; `duplicates.py:main`, under `"review
  finding"`; `tests/tier1/test_layering.py:test_ver61_every_annotated_edge_names_a_finding_of_the_log`, the same
  tuple through `nanopnp.validation.findings.parse_log`; `docs/scripts/generate.py:REGISTERS`; and `mkdocs.yml`'s
  `exclude_docs` and its *Project* navigation, both written by hand.
- `parse_log` needs the front matter's three keys and the header row, and reads the first table.
- 605 links name `review-items.md#rev-`, in 8 Markdown files; 278 are the log's own. 222 more are in
  `docs/code_reviews/CODE_REVIEW_039/decisions.json`, which `links.py` does not read. `links.py` checks an anchor
  only with `--anchors`, which the gate and CI do not pass.
- `decisions.py:render` writes one page of 1,556 rows, and `main` writes or checks `PAGE`. The statuses are:
  delivered plan 749, in force 334, fixed 221, in the design document 63, spent 62, accepted 39, superseded 18,
  deferred 18, plan in flight 13, open 11, in force (cache) 7, declined 7, wontfix 5, post-1.0 5, closed 4.
- `test_ver79_the_decisions_page_equals_what_the_script_renders` calls `main(["--check"])`.
- `.claude/skills/np-ship/phase.md`, step 3, checks the status of each row a phase owns (AM4).

**D7**

- `.claude/scripts/audit/` holds ten scripts that `CLAUDE.md`, the skills, the core and `justfile` do not name.
- WP6.04 to WP6.18 are provisional (AZ7) and remain valid owners until the rescoping round.

### Implementation details

**Item 1 (D1).** `usage.py --reading [--transcript <jsonl>] [--pages <jsonl> ...] [--json]`. It is refused with
`--since` or `--all`; with no transcript it prints `Reading: not measured` and exits 0.

1. Normalise. A local event is used as it is. A page event becomes `{"type", "message", "_t", "session"}`, with
   `isMeta` where the page gives it, and is dropped when its `parent_tool_use_id` is set. Events are grouped by
   session.
2. Windows. Each typed prompt whose text holds `/np-` opens one, which ends at the next. A `user` event whose text
   starts `Base directory for this skill:` opens none, with or without `isMeta`. The window's name is the command
   and its arguments' first two words.
3. A message's tokens are the sum of the three `usage` fields of Grounding D1, taken once per `message.id`.
4. The first edit is the first `tool_use` named `Edit`, `Write` or `NotebookEdit`. A window with none ends at its last
   message and prints `no edit`.
5. The class of a result follows its call:
   - `Read`, `Grep` with a `path`, and `Bash` whose command is `cat`, `head`, `tail` or `sed -n` on one file, by
     the path. One that ends `.py` or `.sh` is code. Else one that holds `/.claude/` or ends `CLAUDE.md` is
     instructions.
     Else one that holds `/docs/`, `/specification/` or `/knowledge/`, or is named `SPECIFICATION.md`, `CHANGELOG.md`,
     `CONTRIBUTING.md` or `README.md`, is records. Else one that holds `/src/`, `/tests/`, `/examples/` or `/data/`
     is code. Any other is commands.
   - `Bash` whose command holds `clause.py` is records, under the name `clause.py`.
   - Every other call is commands. The window's own prompt is instructions. So is a skill's text (Grounding D1)
     whose base directory holds `/.claude/`; any other skill's text is commands.
6. Words are `len(text.split())`, after `re.sub(r"(?m)^\s*\d+\t", "", text)` on a `Read` result.
7. Project text is instructions, records and the words of the tree's `CLAUDE.md`.
8. The line: `Reading (np-implement wp 6.02, fresh): 14,200 words of project text before the first edit
   (instructions 6,100; records 5,880; CLAUDE.md 2,220); code 3,100; commands 9,400; 97,000 tokens at the start,
   158,000 at the edit; largest: <path> 3,400, …`. `--json` gives the same fields per window.

> **Outcome — the measure reads several printed files of one class.** Step 5's `Bash` rule takes a command whose
> segments are `cat`, `head`, `tail` or `sed -n` on files, with `cd` and `echo` between them, and classes it by the
> files when they share a class: a session reads two instructions with one `cat … && cat …` as often as one. Any
> other mix, a pipe or a redirection, stays commands. The self-check on this session's window: 92,784 tokens at the
> start and 183,755 at its last message equal the `usage` sums of `msg_011ChJVzYNNa4zcCV6NgpAuN` and
> `msg_011ChJWCFVhfiV47orh6jMTu`; a whole-file `Read` of the Phase 6 plan gave 2,005 words, as `wc -w` does under
> `LC_ALL=C.UTF-8` (the C locale's `wc` gives 2,001, as it splits no non-ASCII space).

The self-check, recorded in the item's Outcome: for the implementing session, the two token numbers equal the `usage`
sums of the two messages the script names, and the words it gives one whole-file `Read` of a record equal
`wc -w` of that file.

**Item 2 (D2).**

1. In the main session, call `list_sessions` and pick the twelve by title and date. Call `list_events` once and read,
   in this session's transcript, how a saved page and an inline page appear, and how a page gives a command's prompt
   and its skill's text. Write the page reader to those two forms; for a saved page it opens the file the result
   names.
2. Start one sub-agent per session, at most four at once. Its whole brief: the session's id; call `list_events` with
   `kinds: ["assistant", "user"]` and `limit: 100`; repeat with `before_id` set to the last page's `first_id` until
   `has_more` is absent; open no page; report the number of calls.
3. Run `uv run .claude/scripts/usage.py --reading --pages <the sub-agents' transcripts> --json`.
4. Write `reading-baseline.md`. One row per window: package, command, fresh or not, project text with its three
   parts, code, commands, and the two token numbers. Then, for the fresh `/np-implement` windows: the median and the
   range of project text, and each file among the ten largest in at least half of them, with its words. It holds no
   session id and no transcript text. `uv run .claude/scripts/index_records.py` lists it, and item 3's report.

> **Outcome — a page holds no prompt, so a paged window opens at the session's start and after each compaction.**
> The probe of step 1 showed that a page starts at the session's first assistant message: the typed prompt and the
> skill's text are not in it, and the compaction summary is. `--pages` therefore opens a window at the session's
> start and at each `This session is being continued` event; the baseline reads each window's command from the level
> file it reads. A path outside the tree (a saved tool result) counts as commands, and `.cjs`, `.js`, `.html` and
> `.css` as code. The service served all twelve sessions in 299 calls. [The baseline](../sessions/reading-baseline.md):
> 18 fresh `/np-implement` windows, a median of 8,095 words of project text (5,478 to 12,464), 78 % of it in files
> this cleanup can shorten.

> **Outcome — the audit finds three things that matter and no stale fact.** [The report](../sessions/instructions-audit.md)
> checked every path, recipe, flag and heading the 31 files name and found none stale, and no pressure language.
> Its findings: `CLAUDE.md`'s *Models* omits AY7's cleanup exception, so this package's implementing session started
> on Opus 5.5 (F1); a ship in the implementing session runs on the implementer's model (F2, the author's); and the
> instructions say nothing on who owns the code while the Phase 6 plan records repeated code (F3, the author's).

**Item 5 (D4).** Two questions, as `.claude/workflow/author.md` says, each with the baseline's median and range.

- The limit: 50 %, 65 % and 80 % of the median project text of the fresh `/np-implement` windows, rounded to 500
  words. Recommend 65 %. Recommend 80 % instead when the files this cleanup can shorten (`CLAUDE.md`, `.claude/`,
  `current.md`, the package's plan and §8.4) hold under 35 % of that median, and say so. The question names the window
  kind the number binds.
- A phase plan's target: 1,500 words, with the plan cut now; 2,500, with a delivered package's entry one line; or
  4,000. Recommend 2,500.

Then write rows AZ13 and AZ14 into record 50, with their `holds-now.yaml` entries; §8.4.4's bullets for the limit
(what it counts, what it binds, its number) and for the target; `np-plan/phase.md`'s target line; the Phase 6 plan's
open decision 2; and REV-271 `fixed`. Run `decisions.py`.

> **Outcome — the limit is 6,500 words, against the recommendation; a phase plan 2,500.** The author chose 80 % of
> the 8,095-word median over the recommended 65 % (5,500), and confirmed the window kind, a fresh `/np-implement`
> window (AZ13); a phase plan holds 2,500 words with a delivered entry one line (AZ14, as recommended). The one-line
> rule moved `np-implement/wp.md`'s delivered summary to the package's own plan, and WP6.01's entry was cut so in the
> same commit. §8.4.4 states the limit from WP6.03's merge, which its done-criterion checks.

**Item 6 (D5).** In `clause.py:clause`, for a history row that is not a definition, read its ruling's entry in
`holds-now.yaml`. If the entry starts `spent` or `superseded by` and `--all` is not given, write
`--- ruling [<entry>] (<file>:<line>) ---`, then the row's identifier with its first bold phrase. For the survey, a
sub-agent lists each `open:` entry, and each `accepted`, `deferred`, `post-1.0` and `open` row, with the owner it
names and whether the Phase 6 plan or `docs/plans/sessions/phases-6-to-11.md` still has that owner. The main session
reads the list before it changes an entry.

**Item 7 (D6).** `archive_items.py` takes no argument.

1. A row is closed when its status in `review-findings.md` is `fixed`, `declined` or `wontfix`.
2. `review-archive.md` holds the log's front matter with `status: closed`; `# Review archive`; one paragraph; the
   table's header and the closed rows in number order, each *Finding* link made in-page; `## Items`; and the closed
   sections in number order. A later run merges into what is there.
3. The closed rows and sections leave the two register files.
4. In every tracked Markdown file, and in `CODE_REVIEW_039/decisions.json`, a link to `review-items.md#rev-<n>-…`
   of a moved `n` becomes the same link into `review-archive.md`, relative to the linking file. An in-page link
   between a moved and a kept section gains the file name.
5. By hand, in the same commit: `decisions.py:registers`, `duplicates.py:main` and the VER-61 test also read
   `review-archive.md`; `generate.py:REGISTERS`, `exclude_docs` and the navigation gain it; `np-ship/phase.md`'s
   step 3 runs the script after its check; §8.4.6, §8.4.5 and `CLAUDE.md` name the eighth script.
6. `uv run .claude/scripts/links.py --anchors` names no anchor of `review-items.md` or `review-archive.md`.

**Item 8 (D6).** In `decisions.py`, `CLOSED` is `{"delivered plan", "fixed", "spent", "superseded", "declined",
"wontfix", "closed"}`. `decisions.md` keeps its header and its counts of all rows, adds the number of closed rows
with a link to the second page, and lists the rows that bind. `decisions-closed.md` has a one-line header and the
closed rows. `main` writes or checks both. The navigation gains `Decisions register, closed`.

> **Outcome — what the cleanup found outdated and left, each with its file and the step that takes it.**
>
> - **An owner that names no package.** REV-183 (`docs/project/review-findings.md`) is deferred to "FR-43's
>   package"; FR-43 says "a later phase", and neither the Phase 6 plan nor `docs/plans/sessions/phases-6-to-11.md`
>   names one. The rescoping round.
> - **Scripts no instruction names.** `.claude/scripts/audit/` (ten files, which
>   `knowledge/07-software-stack/25-complexity-and-import-contract-tools.md` still cites) and `.claude/scripts/gui/`
>   (five, which `np-gui` runs) are outside the eight kept scripts of `CLAUDE.md` and §8.4.5 (audit F6). WP6.03:
>   list, keep or delete.
> - **The cleanup's model** (audit F1). `CLAUDE.md`'s *Models* and `.claude/skills/np-plan/wp.md` put
>   `/np-implement` on Opus 5.5 and omit AY7's exception, so this package's implementing session ran on Opus 5.5.
>   WP6.03, the audit's hunks 1 and 2; until then the author starts WP6.03 on Fable 5.2 by hand.
> - **A ship on the implementer's model** (audit F2). `CLAUDE.md`, `.claude/workflow/core.md`, `np-ship/wp.md` and
>   `np-implement/wp.md` let `/np-ship` run in the implementing session, and `NANOPNP_AUTO_SHIP` chains into it,
>   against AY7. The author's call, at WP6.03.
> - **Who owns the code** (audit F3). No instruction says whether a package may improve the structure it touches,
>   while the Phase 6 plan records repeated code. The author's call, at the rescoping round, before WP6.04.
> - **The audit's other hunks** (F4, F7, F8): a dated observation in `np-ship/wp.md`, the Copilot host (AY5), and a
>   glob in `.claude/rules/python.md` that matches no file. WP6.03.
> - **The tokens at a session's start.** A window opens at 92,000 to 98,000 tokens before it reads anything
>   ([the baseline](../sessions/reading-baseline.md)). The app loads them: its system prompt, the tools' schemas, the
>   skills' listing and the instructions of every enabled plug-in's servers, and `CLAUDE.md` (2,349 words, about
>   3,000 tokens). The plug-ins are the author's settings; reported only.
>
> The cut, in words (`wc -w` under `LC_ALL=C.UTF-8`, at `09b0d16` and `f8f4248`): the review register 61,248 to
> 20,690, its archive 40,745; `decisions.md` 75,431 to 25,751, its closed page 49,886; the Phase 6 plan 2,005 to
> 1,842; `CLAUDE.md` 2,330 to 2,349. The baseline's fresh windows read a median of 469 words of the register, so the
> cut shortens what a search or a link lands on more than the measured reading; the limit is checked at WP6.03's merge.

> **Outcome — the review ([code review 076](../../code_reviews/CODE_REVIEW_076.md)).** 26 findings; 23 fixed, 21 by
> the review and two after it (a plan's status is read from its Status phrase, with WP42's stale line corrected; the
> measure takes a session's checkout from its own events). The other three were the author's, on what the limit
> counts: §8.2.50 AZ15 (only a session's first window is bound, so D1's "fresh" and its test of tokens are gone),
> AZ16 (a file that a combined command prints counts) and AZ17 (only an edit tool ends the count). By the fuller
> count this package's own first window read 21,611 words where the narrower rule gave 11,649; the baseline is not
> counted again, and AZ13 lets the author rule the number again before WP6.03 measures. `links.py --anchors` now
> checks in-page links, and `archive_items.py` refuses to run where it would drop a row.
>
> **Measured cost** beside the In brief's estimate (about six sessions, four to seven agent hours, twelve touches):
> four sessions, 1.6 agent hours and 8 touches at this commit (`/np-implement` 3, 1.0 and 6; `/np-ship` so far 1,
> 0.6 and 2). The plan's own sessions are not in the pull request's lines.

### Work items

- [x] 2120ab9 1. `.claude/scripts/usage.py`, the reading measure (D1); §8.4.5's and `CLAUDE.md`'s lines for the script (D8).
  Done when the code and review say so and the self-check holds. **Executor:** main
- [x] c0c5d4c 2. The baseline, `docs/plans/sessions/reading-baseline.md` (D2). Done when its table holds each window, or
  names the session not served. **Executor:** main; the paging by `general-purpose` sub-agents on Sonnet, high effort
- [x] b755810 3. The audit, `docs/plans/sessions/instructions-audit.md` (D3). Done when the report gives each finding its six
  fields, and the proposed diff. **Executor:** main
- [x] 4. Compaction checkpoint. **Executor:** main
- [x] 7e2cf8d 5. The stop: the two questions, rulings AZ13 and AZ14, §8.4.4, `np-plan/phase.md`, REV-271 (D4). Done when the
  author has ruled and `decisions.py --check` passes. **Executor:** main
- [x] 0fd7ff5 6. `.claude/scripts/clause.py`, the stale owners of `holds-now.yaml`, §8.4.4 (D5). Done when `clause.py AY5`
  prints AA6 and AV6 as a label and one line each, `--all` prints them in full, and VER-79's tests pass. **Executor:** main; the
  survey by a `general-purpose` sub-agent on Sonnet, high effort
- [x] 4cb13f0 7. `.claude/scripts/archive_items.py`, `docs/project/review-archive.md`, the readers and the links (D6). Done
  when the tests of VER-61 and VER-79 pass, `duplicates.py` passes, and `links.py --anchors` names neither register
  file. **Executor:** main
- [x] d3fd23d 8. `decisions.py`'s two pages (D6). Done when VER-79's tests and the strict documentation build pass.
  **Executor:** main
- [x] 9. Compaction checkpoint. **Executor:** main
- [x] e509ff0 10. The Outcome's outdated list (D7); REV-272's counts and `CHANGELOG.md` (D8). Done when the code and review
  say so. **Executor:** main

### Verification

| Check | Tier | Identifiers | Oracle | Command |
|---|---|---|---|---|
| `tests/tier1/test_written_architecture.py`, kept and unchanged | 1 | VER-79 | Both decisions pages equal what the script renders; each ruling has one `holds-now.yaml` entry | `uv run pytest tests/tier1/test_written_architecture.py` |
| `tests/tier1/test_layering.py`, kept; its tuple of logs gains the archive | 1 | VER-61 | Every annotated edge names a finding of a log or of the archive | `uv run pytest tests/tier1/test_layering.py` |
| The documentation build | none | VER-45 | The strict build passes with the two new pages | `CLAUDE.md`, *Commands* |
| The plan's identifiers | none | none | `clause.py` resolves AW5, AY5, AY7, AY8, AZ4, AZ7, AZ9 to AZ12, AM4, AM11, AL5, N1, N3, VER-45, VER-61 and VER-79 | `uv run .claude/scripts/clause.py <ID>` |

No test is added. Items 1 to 3, 5, 6 and 10 are outside the test scope, and their done-criteria stand in the items.

### Out of scope

- The audit's changes to the instructions, the Copilot host's removal and `/np-plan project`'s rewrite (REV-278):
  WP6.03.
- A fresh session under the limit: WP6.03's done-criterion. This package reports its cut against the limit.
- What the outdated list names, and `.claude/scripts/audit/`: WP6.03 or the rescoping round, as the list says.
- The tokens that the app and its plug-ins load at a session's start: the author's settings; reported only.

### Open questions

None blocks. The limit's number and a phase plan's word target are item 5's.
