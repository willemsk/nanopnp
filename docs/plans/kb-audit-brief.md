# Audit nanopnp's written knowledge

**Status: brief, not started.** Written 8 November 2026 from a survey of the tree at `1e7fa2e` and
four rounds of the author's decisions, recorded under *Terms already settled* below. It is the whole
prompt of one standalone Fable 5.1 session: open a fresh session on this repository and tell it
`Read docs/plans/kb-audit-brief.md and carry it out`. It is not a work-package plan, and
`SPECIFICATION.md` governs. The report's number, 037, is one above the highest present on the day
this was written; if that number is taken when the session starts, it takes the next free one and
uses it throughout.

You are auditing the documents that nanopnp's agent sessions and its site readers work from: the
specification bundle, the knowledge base, the docs tree, the agent-facing files under `.claude/`,
and the root files that point into them. The audit finds where these documents are wrong, unclear,
costly to read, say one thing in two places, or put what matters where nobody reaches it; fixes
what is provably safe to fix; and puts every other change to the author with the evidence. The
meaning of the specification is the author's and does not move in this audit.

## Terms already settled with the author

Do not re-ask these; work within them.

- **Framing.** A standalone session outside the work-package numbering, as
  `docs/plans/history-prose-review.md` was. One `docs:` pull request carries the mechanical fixes
  and the report. The author's rulings on the report's checklist become a dated history record and
  a follow-up package applies them; neither is your job.
- **Output.** The report is `docs/code_reviews/CODE_REVIEW_037.md`, its attachments under
  `docs/code_reviews/CODE_REVIEW_037/`, its scripts under `.claude/scripts/audit/`. You apply
  only mechanical, meaning-preserving fixes. Every deletion, merge, move, or rewrite of a sentence
  that carries a rule waits for the author.
- **Records** (delivered plans, phase records, code reviews, `specification/history/`, design
  reviews, user-testing sessions, `CHANGELOG.md`) keep their prose byte for byte. Their
  reachability and organisation are in scope: folders, indexes, naming, what is visible from where.
- **Structural moves** are proposals, each with a migration script you have run on a scratch
  branch and verified, never applied.
- **The decisions register** is a prototype, generated from the existing text and attached to
  the report, with its home, shape and maintenance rule put to the author. It is not live.
- **The architecture** gets an assessment, a survey of existing packages that track or assess code
  quality and architecture, and a read-only prototype only for what no package gives.
- **No token budget.** You report tokens saved per reading path for each proposal; the author
  chooses the cuts.
- **Accuracy** reaches the thesis source for every `[verified]` claim that cites it. The paper's
  ESI and the COMSOL model report are not reachable; a claim resting on them is `unchecked`.
- **Readers.** Fresh Fable sub-agents do the reading sweeps and task walks, one per directory;
  Haiku or Sonnet sub-agents run the mechanical probes. You orchestrate, read the cross-cutting
  documents yourself, and re-run a sample of every sub-agent's verdicts before you use them.

## Read first, in this order

1. `CLAUDE.md`, `SPECIFICATION.md`, `knowledge/index.md`, every file of `knowledge/00-orientation/`,
   `specification/08-implementation-plan/04-development-process.md` (§8.4), `docs/plans/current.md`,
   `.claude/workflow/core.md`.
2. `.claude/rules/physics-numerics.md` and `.claude/rules/python.md`. A session that writes Markdown
   and scripts reads them explicitly.
3. How the documents got their shape, so that you neither re-propose what was ruled out nor
   re-argue what was ruled: `specification/history/16-phase-4-amended-the-specification-and-the-workflow.md`
   (R2 to R4, R9, R10), `specification/history/13-phase-4-amended-the-test-scope-agreed-18-october-2.md`
   (N1, N3), `docs/plans/history-prose-review.md` (the author's decisions A to L on historical
   prose), and *Not to be re-decided* in `docs/plans/current.md`.
4. `docs/project/modularity.md` and `src/nanopnp/validation/modularity.py`'s docstrings: what the
   tree already measures about its own architecture.

## Who reads these documents

- **Agent sessions, first.** Every session loads `CLAUDE.md`, `SPECIFICATION.md`,
  `docs/plans/current.md`, `.claude/workflow/core.md` and the rules files before any task, about
  8,000 tokens, then the skill of its command and the files that the task's row of
  `SPECIFICATION.md` *Where to start, by task* names. A session pays for every word on that path,
  every turn, and acts on what the words say.
- **People on the documentation site, second.** `mkdocs` renders `specification/` and `knowledge/`
  verbatim under *Model* (`docs/scripts/generate.py`); `docs/guide/`, `docs/project/` and the rest of
  the site are written for them. `docs/plans/` and `docs/code_reviews/` are not on the site.
- **The author**, who reads plans, reports and registers to rule, and who finds five things hard to
  reach today: a decision and its reason; the current state of the work; which rule governs a given
  action; a measured number or tolerance and its derivation; the current code architecture. The task
  walks of step 4 target these five first.

## Scope

**Live documents**, audited on all five axes:

- `SPECIFICATION.md` and every file of `specification/` outside `history/`.
- `knowledge/`, every file, `log.md` and each `index.md` included.
- `docs/index.md`, `docs/getting-started.md`, `docs/guide/`, `docs/model/`, `docs/reference/`,
  `docs/examples/index.md`, `docs/project/` (its pages, and the prose and headers of the registers;
  the rows of a register are records), `docs/design/workbench.md`, `docs/design/tokens.css`'s
  comments if any, `docs/plans/current.md`, `docs/plans/phase-5-workbench.md`.
- `.claude/`: `workflow/`, `skills/`, `agents/`, `rules/`, the docstrings of `scripts/*.py` and
  the comments of `hooks/*.sh`. The skills' behaviour is set by rulings (§8.4.4, §8.4.5): a change
  to what a command does is a proposal; a stale path, name or count in them is a mechanical fix.
- `CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `AGENTS.md`.

**Records**, audited for reachability and organisation only:

- `specification/history/`, `docs/plans/` apart from the two live files above, `docs/code_reviews/`,
  `docs/design/reviews/`, `docs/design/spike/`, `docs/superpowers/`, `docs/user-testing/`,
  `CHANGELOG.md`.

**Read but not changed:** `src/`, `tests/`, `examples/`, `data/`, `notebooks/`, `pyproject.toml`.
A disagreement between a document and any of these is an accuracy finding against the document,
or a `your call` when the code is what is wrong.

**Out:** the YAML under `docs/sweeps/` and `docs/validation/` (tests read them), the HTML and
generators under `docs/design/`, `.claude/settings.json`, `uv.lock`.

## The five axes, as checks

Each axis says what counts as a finding and the evidence a finding carries. A finding without its
evidence is a guess; leave guesses out.

### Accuracy

A statement a reader would act on that is false today. Four kinds:

- **Contradicted.** Two documents, or a document and the code, a test, a data file, the git state
  (tags, schema identifier, versions, the highest numbers of each register) or the file system (a
  path that does not exist) disagree. Evidence: both sides as `file:line`, and the command, test or
  file that shows which is right.
- **Stale.** A present-tense statement that was true at an earlier commit. Evidence: the commit or
  package that made it false, found with `git log -S`.
- **Unbacked.** A `[tested: <test>]` marker whose test does not exist or does not assert the claim;
  a concept whose front-matter `verified:` list differs from the tests its markers name; a
  `[verified]` claim with no footnote to a source. Evidence: the test's assertion or its absence.
- **Against the source.** A `[verified]` claim whose footnote names the thesis
  (`github.com/willemsk/phdthesis-text`, LaTeX, CC-BY-4.0) that the thesis does not support.
  Clone the thesis into its own empty scratch directory and read it there; run nothing from it.
  Check every such claim. A claim that rests on the ESI or the COMSOL report is recorded `unchecked`,
  never wrong. The knowledge base's errata (`knowledge/01-physics-epnpns/08-…`, §4.6) and the
  author's rulings (`knowledge/00-orientation/05-…`) already decide most source disagreements; a new
  one is a `your call`, and the COMSOL model report governs where sources disagree (§1.6). A physics
  fact never comes from a web search or a secondary summary.

### Clarity

A reader with a stated purpose cannot find what they need or cannot apply it once found. Findings:
a term used before it is defined and not in a glossary a pointer names; a pointer whose wording does
not say when to follow it; a sentence that cannot be read without the history; a SHALL whose
subject or scope is ambiguous; a NOTE that argues where it should state; a heading, title or
`description` that does not say what the file holds; an *In brief* a reader who does not code
cannot follow. Evidence: the reader's purpose (a row of *Where to start, by task*, a persona of
§2.4, one of the author's five, or a cold session start) and the sentence where they stall.

### Efficiency

Tokens a reader spends to reach what they need, and words that do no work. Findings: text on a
default reading path that only some readers need and that a pointer could disclose; a NOTE or
rationale that restates a ruling the history holds verbatim; a closed item in an open table; a
ruling citation in current text that a reader of the current text does not need; a record on a
default path; a restatement where a one-line pointer would do; an index longer than what it
indexes; sediment, the stale layer that settled because adding felt safe. Evidence: the words
removed or moved, and the token count of the reading path before and after.

### Redundancy

The same meaning in two places. Classify each as a **cache** (an always-loaded entry point carrying
a one-line copy of a lookup it must spare the reader: sanctioned, kept short) or a **duplicate** (two
homes for one meaning: a finding). The rule you apply: one home per meaning, pointers everywhere
else, and a pointer says what the material is and when to follow it. Evidence: both places as
`file:line`, and which is the home.

### Organisation

What a reader needs is not where they look, or is in a place that nothing points to. Findings: a
record that no index lists; a folder that holds two kinds of thing with nothing to tell them apart
(`docs/plans/` holds 80 files: package plans of two numbering schemes, phase plans, phase records
and dated notes, with no index; `docs/code_reviews/` holds 36 numbered reports with no index and
no column that says which package or branch each reviewed); a folder whose contents belong with
another's; a document whose status (live, record, superseded) is not stated in its first lines;
a decision, a measured number or a rule that is recorded only inside a record. Evidence: the
reader's purpose, where they looked, and where the material is.

## Procedure

### Delegation

Brief every sub-agent with Appendix F's template, filled in for its directory. A reader sub-agent
returns findings in the schema and nothing else; a probe sub-agent returns the hit list of one
probe. Save every return to `docs/code_reviews/CODE_REVIEW_037/raw/` before you read it, and
re-run a sample of each return's verdicts yourself before you use it. Keep the cross-cutting
documents for yourself: `CLAUDE.md`, `SPECIFICATION.md`, §8.4, `knowledge/index.md`,
`knowledge/00-orientation/`, §11, `docs/plans/current.md`, `specification/history/index.md`,
`.claude/workflow/core.md`.

### Step 0: set up

Work on the session's branch from current `main`. Create the scratch directories: one for the
thesis clone, one for sub-agent returns, one for measurements. Record the commit you start from;
every count in the report names it.

*Done when* the branch, the directories and the commit are recorded at the top of the report file.

### Step 1: baseline

Build the inventory: every file in scope with its path, words, live or record, OKF `type`, whether
the site navigation lists it, whether any index lists it, and whether a `src/` or `tests/` file
cites its path (26 `knowledge/` paths are cited from 41 code files; a moved file breaks them).
Measure the reading paths in words and tokens: the always-loaded set; each skill's load; each row
of *Where to start, by task*; each of the author's five hard-to-reach things, as the path a reader
walks today. Run the checks that need no judgement and keep their output: the strict site build
(`uv run docs/scripts/generate.py && uv run mkdocs build --strict`), a relative-link check over
every Markdown file in scope, `uv run .claude/scripts/clause.py` over every identifier of Appendix A
and every ruling letter of `history/index.md`, the `[tested:]` and `verified:` reconciliation, and
every probe of Appendix C.

*Done when* the inventory lists every file in scope, each reading path has a token count, and
every check has an output file under `CODE_REVIEW_037/raw/`.

### Step 2: mechanical sweep

Turn every hit of step 1 into a finding or dismiss it with a reason. Add the probes you devise as
you read: a version, schema identifier, command name, public name, count or path that the tree no
longer has.

*Done when* every hit is in exactly one of: a finding, or a dismissal with its reason.

### Step 3: reading sweep

A Fable sub-agent per directory reads every live document whole, on all five axes, one finding
per defect, and gives every record a reachability verdict. For each `index.md` and each OKF front
matter, the reader checks that the description says what the file holds and that the list matches
the directory. For `.claude/`, the reader also checks each skill against the §8.4.4 and §8.4.5
rules it implements and names each divergence.

*Done when* every live file has a verdict (clean, or its findings), every record has a
reachability verdict, and you have re-read a sample of each directory's verdicts.

### Step 4: task walks

Walk each reading path as its reader would, in a fresh sub-agent that holds only what the path
gives it: every row of *Where to start, by task*; a cold session start with `CLAUDE.md` alone; each
of the author's five hard-to-reach things, as a concrete question (which ruling set the plan word
cap and why; what is merged and what is next; which rule governs a push from a Copilot host; what
the Tier 2 tolerance on the current is and where it was derived; which subpackage owns the wall
distance and what imports it); the three personas of §2.4 arriving at `docs/index.md`; a site
reader opening *Model*. Record each stall (where the walk opened a file the path did not name, or
read history to understand current text, or gave up) and the token count of the walk.

*Done when* each walk has a transcript with its stalls and its cost, saved under `raw/`.

### Step 5: the decisions register prototype

Write `.claude/scripts/audit/decisions.py`: a deterministic, re-runnable script that reads every
source of Appendix D and emits one row per decision in Appendix D's columns, as Markdown and as
JSON. Run it; attach the output as `CODE_REVIEW_037/decisions.md`. From the output, write the
proposal: the register's home, its shape, what counts as a decision, how it relates to
`specification/history/index.md`'s *Where each ruling holds now* (fold, link or replace), and the
one rule that keeps it current (which command appends, at which step). Each is a `your call`.

*Done when* the script runs clean from `uv run`, its output is attached, every source of Appendix D
is read by it, and the proposal names its `your call` items.

### Step 6: the architecture

First audit the architecture documents on the five axes: §5.1, §5.4, §5.5, §5.6,
`docs/project/modularity.md` and `modularity-findings.md`, `modularity-layering.yaml`'s comments,
`docs/guide/concepts.md`, the API reference, and `CODE_REVIEW_036`'s reachability.

Then survey existing packages that track or assess code quality and architecture before writing
anything: Appendix E lists candidates; add what you find. For each, record what it measures, what
it would add over `nanopnp.validation.modularity`, its licence, whether it fits the dev group under
CON-07, and its authenticity (publisher, repository, release history). Adopt none; recommend at
most two, with the command that would run each and a sample of its output on this tree, run from a
scratch environment.

Then write `.claude/scripts/audit/architecture.py` for what no package gives: per subpackage, its
modules with their one-line docstrings, public names, lines, the stages they implement, and the
measured edges in and out; and a diff of §5.1's module table against the tree. Read-only; it
changes nothing under `src/`. Attach its output as `CODE_REVIEW_037/architecture.md`. Put to the
author its home (a page the site generates, or a kept script), and the rule that keeps §5.1 level
with it.

*Done when* the survey table has a row per candidate with every column filled or `not run` with
the reason, the script runs clean and its output is attached, and the proposal names its `your call`
items.

### Step 7: cross-cutting analysis and structural proposals

From the findings, draw the redundancy map (each meaning, its homes, the proposed home), the
sediment list (text to move to a record or to delete, with the token delta), and the structural
proposals: an index, a merge, a split, a move, a folder retired. For each proposal, name what it
breaks: links (573 point into `docs/plans/` from 58 files), the 26 cited paths, the site
navigation, `clause.py`'s resolution, `duplicates.py`'s registers, the path rules in §8.4.4 and
`.claude/skills/np-plan/wp.md`, a ruling in force. A proposal that reopens a ruling says which one
and why the ruling's reason no longer holds.

For each move, write `.claude/scripts/audit/migrate_<name>.py`: it performs the move and rewrites
every link and path rule. Run it on a scratch branch, verify with the link check, `clause.py`,
`duplicates.py` and the strict build, record the result in the proposal, and delete the scratch
branch. The script is committed; the move is not.

*Done when* every finding of severity medium or high is in the map, the list or a proposal, or
stands alone with its own proposed edit, and every move proposal has a script with a recorded
verification.

### Step 8: apply the safe fixes

Apply only a fix that preserves meaning and that a reader can verify from the finding's evidence:
a broken link; a stale fact with a verifiable current value (a count, a path, a name, a version, a
highest number); a dead `[tested:]` marker retargeted or demoted by the rule of §8.2.13 N3; an index
or front matter brought level with its directory; an index file that lists what a folder holds,
one line each with the file's own status line, where the folder has none; a typo; a present-tense
sentence that a dated event made false. Everything else waits for the author. `docs/plans/current.md`'s
position lines and *In brief* are the lane's; touch nothing there but a broken pointer. A durable
fact you establish on the way goes into `knowledge/` as a concept with a line in `knowledge/log.md`,
by `knowledge/00-orientation/04-…`, in its own commit.

One `docs:` commit per category of fix, the finding identifiers in the body; `chore:` for the
scripts. Records stay byte for byte. Before the push, the gate as `CLAUDE.md` states it: start
`.claude/hooks/gate.sh run` in the background, wait for it in the same turn, push when its log ends
in `exit 0`. A commit that adds a `.py` is not prose-only, so the full gate runs; your scripts pass
`ruff check` and `ruff format`. Then open the pull request: the author asked for it. Its title is
`docs: audit of the written knowledge (CODE_REVIEW_037)`; its body links the report and lists the
fixed findings by identifier; mirror the repository's pull-request template if one exists.

*Done when* the gate's log ends in `exit 0`, the strict build passes, the push is made and the pull
request is open.

### Step 9: the report

Write `docs/code_reviews/CODE_REVIEW_037.md` in the house shape: a title line
`# Code review 037: the written knowledge audit`, then date · commit · scope · focus · status, then:

1. **Summary**: ten lines a reader who does not code can follow: what was read, what was found, what
   was fixed, what waits.
2. **Baseline**: the inventory's totals and the reading-path costs, before and after the fixes.
3. **Findings by axis**, ranked by severity within each, in the schema.
4. **The redundancy map** and **the sediment list**.
5. **Organisation**: each structural proposal with its script, its blast radius and its verification.
6. **The decisions register**: the prototype's link, what it found (how many decisions, by whom,
   how many with no stated home), and the proposal.
7. **The architecture**: the survey table, the prototype's link, and the proposal.
8. **Fixed in this pull request**: a table of finding identifier to commit.
9. **Your call**: a checklist, one line per decision the author must take, each with your
   recommendation and the reason, written for a reader who does not code, in the order you would
   take them. The follow-up package transcribes this list into a history record, so each line stands
   alone.
10. **Dismissed**: a table of hit to reason.
11. **How to pick this up in a new session**: which files hold the state, how to re-run each script,
    and what the follow-up package applies first.

*Done when* every finding is in exactly one state (`fixed <sha>`, `your call`, `dismissed <reason>`),
the checklist covers every `your call`, and the report and its attachments are committed and
pushed.

## Finding schema

One row per finding, `AUD-nn` numbered in order of discovery:

| Column | Holds |
|---|---|
| ID | `AUD-nn` |
| Axis | accuracy, clarity, efficiency, redundancy, organisation |
| Severity | `high`: a reader acting on the text does the wrong thing. `medium`: a reader stalls, reads more than the task needs, or cannot reach what they need. `low`: tidiness |
| Where | `file:lines`, every place involved |
| Defect | One sentence, present tense |
| Evidence | The command, test, commit, walk transcript, or the two quoted sentences |
| Proposed edit | The replacement text, or the move, or the deletion |
| Saves | Words and tokens, off which reading path |
| Breaks | Links, cited paths, navigation, `clause.py`, `duplicates.py`, a path rule, a ruling: or none |
| Status | `fixed <sha>`, `your call`, `dismissed <reason>` |

## Constraints

- The specification's meaning is the author's: no SHALL, tolerance, default or scope changes; no
  identifier renumbered, reused or removed; a withdrawn row stays (§7.2).
- A record stays verbatim (§8.2.16 R2; history-prose-review H, I). Its reachability may change.
- A skill's behaviour is a ruling (§8.4.4, §8.4.5): propose, and fix only what is stale in it.
- Physics comes from `knowledge/01-physics-epnpns/` and §4; the thesis is a primary source; a web
  summary never is.
- Current text is present tense, British spelling, identifiers as pointers, dates only in
  `specification/history/`, `knowledge/log.md` and `CHANGELOG.md` (history-prose-review B to G).
- No test is added or changed (§8.2.13 N3); nothing under `src/` changes; no dependency is added.
- A file move is a proposal with a script, never an applied fix.
- Your scripts are deterministic: the same tree gives the same output, and each says at its top what
  it reads and what it writes.
- Every count in the report names the commit it was measured on.

## Resuming after a compaction

The state is the report file, the inventory and the returns under `CODE_REVIEW_037/raw/`. On
resuming, re-read the report's status table, the last step's *Done when*, and the list of
sub-agents whose returns are saved; continue from the first step whose criterion is not met.

---

## Appendix A: measured baseline, 8 November 2026, at `1e7fa2e`

| What | Measure |
|---|---|
| `specification/` (71 files; 36 are history) | 122,000 words, of which history 47,000 |
| `knowledge/` (137 files) | 91,000 words |
| `docs/` Markdown (168 files) | 510,000 words: `docs/plans/` 353,000 (80 files, no index), `docs/code_reviews/` 65,000 (36 files, no index), `docs/project/` 42,000, `docs/design/` 21,000, `docs/guide/` 15,000 |
| `.claude/` Markdown (26 files) | 15,300 words: `np-plan` 5,200, `np-ship` 2,000, `steward` 1,700, `core.md` 1,500, `copilot.md` 1,200 |
| Always loaded: `CLAUDE.md`, `SPECIFICATION.md`, `current.md`, `core.md`, the two rules files | 6,100 words |
| *Touch the physics* path: §4, `knowledge/01-…`, §6 | 17,600 words |
| *Change the case file* path: §5.3.1, §5.3.3, Appendix A | 14,300 words |
| `history/index.md` *Where each ruling holds now* | 282 entries |
| Decisions: D-rows in plans / ruling rows in history / REV / MOD / WB / KB rulings / *Your call* sections | 624 in 55 plans / 271 / 221 / 18 / 38 / 14 / 34 |
| `[tested:]` / `[verified]` markers in `knowledge/` | 448 / 123 |
| `knowledge/` files whose `generated.at` is the backfill stamp `2026-10-14` | 121 of 137 |
| Paths into `docs/plans/` from outside it / files citing `docs/code_reviews/` | 573 from 58 files / 40 files |
| `knowledge/` paths cited from `src/` and `tests/` | 26 paths from 41 files |
| Relative links in scope / broken | 1,256 / 7 |

## Appendix B: seeds

Findings to confirm, not conclusions. Start from them.

- §11 says the knowledge base ships as `nanopnp-kb/` and lists `knowledge/pending.yaml`; neither
  exists (WP50, §8.2.13 N3). `specification/index.md` says the history runs to §8.2.29; it runs to
  §8.2.35.
- §10 keeps four closed `OPN-` rows (02, 05, 06, 07) in the open-items table, one of them 600 words.
- Seven relative links are broken: `docs/plans/wp19…`, `wp52…` (three), `wp53…`, `CODE_REVIEW_005`,
  `CODE_REVIEW_013`. The strict build does not see them because those folders are not on the site.
- Two glossaries: `knowledge/00-orientation/07-glossary.md` (2,400 words, project shorthands) and
  `knowledge/03-nanopore-biology/08-glossary.md` (biology). Three lists of the knowledge base's
  notes: `knowledge/index.md`, `knowledge/00-orientation/01-files.md`, §11's table.
- The rules of process are stated in `CLAUDE.md`, §8.4, `.claude/workflow/core.md` and the skills;
  decide the home and which lines are a sanctioned cache.
- Appendix B of the specification condenses `knowledge/09-comsol-reference-settings/`;
  `docs/project/contributing.md` condenses `CONTRIBUTING.md`; `knowledge/00-orientation/05-…`
  restates rulings that §4 and §4.6 carry.
- `docs/superpowers/specs/` holds two executed design notes (WP50, WP54) under a folder named for a
  tool; `docs/plans/okf-knowledge-bundle.md` and `okf-converter-rules.md` are inputs to WP47 and
  WP48, both delivered; `copilot-host.md`, `history-prose-review.md` and
  `notebooks-review-for-wp54.md` are dated notes beside package plans.
- `specification/03-requirements.md` carries 56 ruling citations; `05-software-design/03-1-case-file.md`
  carries 28 NOTEs in 11,300 words; `06-numerics.md` 33 NOTEs. Measure how much of each a reader of
  the current clause needs.
- The retired names `load_case`, `run_case`, `/phase-plan`, `/wp-plan` and the schema
  `nanopnp/case/v0.5` appear in 5 current specification files and 1 knowledge file.
- `docs/project/modularity.md` quotes numbers frozen at `97f2b3d` while the site renders live ones;
  state which a reader should trust and where.
- `CODE_REVIEW_036` settled six architectural changes with the author; nothing outside the review
  and five REV rows says so.

## Appendix C: stale-reference probes

Run each over every file in scope and read each hit: `nanopnp-kb`, `pending.yaml`,
`nanopnp/case/v0\.[0-5]`, `load_case|run_case|\bresolve\(`, `/phase-plan|/wp-plan|/wp-implement|/wp-ship`,
`PyQt`, `coverage|diff-cover|pytest-cov`, `§8\.2\.(2[0-9]|3[0-9])` (does the cited ruling exist?),
`WP[0-9.]+ D[0-9]+` (does the plan's decision exist?), `v0\.[0-9]\.[0-9]` (is the version a tag?),
`--extended|no_cover|test_plan_shape`, `tests/tier[0-9]/[a-z_]+\.py` (does the file exist?),
`CODE_REVIEW_0[0-9]+` (does the report exist?), `REV-[0-9]+|MOD-[0-9]+|OPN-[0-9]+` (does the row
exist, and does the cited status match the register?), `VER-[0-9]+|VAL-[0-9]+` (does `clause.py`
resolve it, and is it withdrawn?).

## Appendix D: the decisions register's sources and columns

Sources, each read by `decisions.py`:

- `specification/history/*.md`: every ruling row (a letter-number first cell), with its record's
  date, and `index.md`'s *Where each ruling holds now* entry.
- `docs/plans/*.md`: every `| Dn |` row of a Decisions table; every `**Your call**` paragraph and
  *Decisions for you* checklist; every `(author)` and `(my call)` mark; every Outcome annotation
  that records a choice.
- `docs/project/review-findings.md` and `modularity-findings.md`: every row's ruling column.
- `docs/design/workbench.md`: every `WB-nn`.
- `knowledge/00-orientation/05-…`: the fourteen rulings.
- `docs/code_reviews/*.md`: every sentence that records a ruling by the author.
- `docs/plans/current.md`: *Not to be re-decided*.
- `specification/10-open-items.md`: every `OPN-` row.

Columns: source identifier; decided by (`author`; `session, put to the author`; `session, own
call`); where (`file:line`); date; package; what was decided (one sentence, quoted or near-verbatim);
where it holds now (a clause, a §8.4 rule, a file, `superseded by <id>`, `spent`, `open`, or
`unstated`); status.

## Appendix E: packages to survey for the architecture

Candidates, to confirm and extend: `import-linter`, `grimp`, `tach`, `pydeps`, `deptry`,
`radon` and `xenon`, `wily`, `lizard`, `interrogate`, `vulture`, `pylint`'s design checkers,
`ruff`'s rule families not yet enabled in `pyproject.toml`, `mypy --html-report`'s coverage,
`pyreverse`, `code2flow`, `pyan3`, `sourcery`. For each: what it measures; what it adds over
`nanopnp.validation.modularity`; licence; publisher, repository and release history; whether a
dev-group install needs a compiler or a JIT (CON-07); the command; a sample of its output on this
tree from a scratch environment, or `not run` with the reason.

## Appendix F: the sub-agent brief

Fill in and send as the whole prompt of each sub-agent:

```
You are one reader in an audit of nanopnp's written knowledge. Read every file under <DIRECTORY>
whole, in path order. The repository's rules are CLAUDE.md, .claude/rules/physics-numerics.md and
.claude/rules/python.md; read them first. SPECIFICATION.md is normative and its meaning is the
author's: you change nothing; you report.

Audit each live file on five axes, one finding per defect, in this schema: <SCHEMA>. The axes:
<AXES, verbatim from the audit prompt>. For each record (<LIST>), report reachability only: is it
listed by an index, does its first line state its status, is it off every default reading path.

Evidence rules: every finding names file:lines on every side; a contradiction quotes both sides
and names the command, test, commit or file that decides it; a stale statement names the commit
that made it false (git log -S); a token saving names the reading path. A finding you cannot
evidence is left out. Use British spelling and the present tense.

Return a Markdown table in the schema, then a list of the files you judged clean, then a list of
the facts you established that the knowledge base should hold. Nothing else.
```

For a task walk, replace the second and third paragraphs with: the reader's purpose as one
question, the starting file, and the rule that the walker opens only files the current text points
to, records every file opened with its word count, records every stall, and stops when the question
is answered or after twelve files.
