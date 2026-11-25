---
type: Process
title: "8.4 Development process"
description: "States the rules in force on versions, the loop, the test scope, plans, agents and models, and open items, each with its ruling."
---

### 8.4 Development process

These are the author's rulings that are in force, set a standing rule and have no clause of their
own, restated in the present tense. Each rule ends in its sources: the ruling in
[the history](../history/index.md), read on demand, or the file that carries the rule. A ruling that
amends a clause lives in that clause. From §8.2.16 R3 on, a ruling with no clause to amend is written
here once.

#### 8.4.1 Versions and releases

* A version is a git tag, never a number in `pyproject.toml` or in the package. The procedure is
  `CONTRIBUTING.md`, *Versions and releases*. (§2.7; §8.2.4 D1)
* Each merged work package takes `vX.Y.Z-alpha.N` on its last commit on `main`. The session pushes the
  tag if its GitHub access allows it; a cloud session's does not, so after the merge `/np-ship`
  dispatches `.github/workflows/tag.yml`, which pushes the tag and starts the release with the full
  matrix. `/np-ship` ends with the full commands either way. Its `CHANGELOG.md` section is headed
  `## [X.Y.Z-alpha.N]`, the line `tag.yml` reads and `/np-ship`'s preflight checks. (§8.2.33 AI5,
  AI8; §8.2.36 AL14)
  From Phase 5, N is the package's number within its phase: WP5.02 takes `v0.6.0-alpha.2`. (§8.2.7
  G11; §8.2.17 S19)
* A phase's close package takes the release tag alone, with no alpha tag on the same commit; Phase 4's
  is `v0.5.0`. (§8.2.5 E5; §8.2.7 G11)
* A package merged before its previous phase's release takes no alpha tag, so versions on `main` only
  increase. Its `CHANGELOG.md` entry goes under `## [Unreleased]` at the top of the file, and the next
  tagged package of its phase moves it into its own section. (§8.2.17 S15, S19)

#### 8.4.2 The loop

* Before a push, `.claude/hooks/gate.sh run` passes on the tree being pushed. The session starts it in
  the background and waits for it in the same turn, and the push guard refuses a tree it has not
  passed. A pass of the commit hook never stands in for it. (§7.6; §8.2.11 L2, L3)
* The gate refuses with its reason on standard error and one JSON object carrying the deny
  top-level and as `hookSpecificOutput`, exit 0; failing to print it exits 2. Once a
  clone sets `core.hooksPath .githooks`, git's `pre-push` (`gate.sh check-push`) also refuses a push
  whose tree has no `push` stamp. (§8.2.25 AA5; §8.2.26 AB1)
* The session-start hook fetches `origin/main` into the primary checkout and fast-forwards a clean
  `main` that is behind it. In any other state it writes nothing and prints a warning. A failed fetch
  or a failed `uv sync` is a warning and never fails the session. (§8.2.16 R7;
  `.claude/hooks/session-start.sh`)
* Python 3.14 is the development and continuous-integration default and 3.11 the minimum. Lazy imports
  (PEP 810) are not adopted. (§8.2.10 J5, J6; OPN-09)
* In-code prose follows one rule: a docstring on every public function, class and method of `src/`
  (a dunder method counts as public), a one-line docstring on every module, none on a test or private
  code, and a comment only where the code cannot say why it is so and for the source of a physical
  constant. (§8.2.11 L4, L10; `.claude/rules/python.md`)

#### 8.4.3 The test scope

The scope itself, with the tolerance rule, is the NOTE of [7.1](../07-verification/01-strategy.md)
(§8.2.13 N1, N3). The process around it:

* A test's name or first line says which silent failure it catches. The implementer writes each test
  with its work item; a plan commits none and lists only in-scope tests. (§8.2.13 N1, N5; §8.2.11 L7)
* `/np-ship` reads the pull request's added and changed tests against the scope before the review
  and deletes each one outside it, in its own `test: drop tests outside the test scope` commit. A
  review finding is never closed by an off-category test. No test checks this rule. (§8.2.13 N5)

#### 8.4.4 Plans and the workflow

* The workflow is three commands with levels: `/np-plan <project | phase n | amend n | wp n> [review]`,
  `/np-implement [wp n]` and `/np-ship [wp n | phase n]`, with no aliases. Each routes to a shared
  core and the file of its level. (§8.2.16 R5, R12; `.claude/workflow/core.md`)
* Beside them, `/np-carry wp <n>` carries one package in one session the author starts, on Sonnet
  5.5 at medium effort, and resumes it in a new one. It hands each step to a fresh helper with an
  empty context, the project agent of its role (§8.4.5): the plan in two helpers, one that surveys,
  grounds and asks and one that writes, checks and commits it; each stretch of the implementation
  up to a checkpoint; and the ship. A helper ends with one `HANDBACK` block, and the hand-back ends
  it: it first commits a hand-off note of at most 600 words, and the answer starts a fresh helper of
  the same agent that reads the note; no helper is resumed (`.claude/workflow/helper.md`). The main
  session asks the author, passing the questions and the answers on unchanged, starts the review and
  the agents a helper asks for, holds the pull request's subscription and check-in, and measures. A
  helper keeps the task list, which the two share, and commits, gates and pushes; the main session
  commits and edits nothing. The stage is read from the branch's commit subjects, the plan's ticks
  and the note, so the three commands stay the way back. A phase, an amendment or a ruling round is
  not carried. (§8.2.53 BC10; §8.2.54 BD2, BD6; §8.2.56 BF1, BF2; `.claude/skills/np-carry/`)
* A pull request's CI tests on Linux, and a package's `/np-ship` reads no platform leg. `/np-ship phase`
  dispatches `ci.yml` on the close's head and stops while a `platforms` leg on ubuntu, macOS or Windows is
  not `success`. (§7.6; §8.2.49 AY4; §8.2.50 AZ8; `.claude/skills/np-ship/phase.md`)
* Beside them, `/np-gui <render | review | publish | collect | grill>` renders screens and mockups
  headless, has them reviewed, publishes them for the author's verdicts, collects the verdicts and
  runs a design round. A render goes to the author as a digest of at most 20 picks, each standing
  for a group of near-identical shots and saying why it was picked and what to look for; the verdict
  on a pick holds for its group (the author, at WP5.15's collect). A package that changes a screen uses it. Its `shell` target renders the browser
  workbench in every fixture state, and `nanopnp gui --dev` is the local live loop: it serves the
  workbench and restarts on a change to its source (`CONTRIBUTING.md`). A suite's package opens with its
  tools prototyped over 2WCD's artefacts (Physics, which has no molecule, over example 01's NaCl case) and rendered in their states for the author's verdicts and a
  design round, then builds them. From WP5.15, `impeccable`, where the host has it, is a tool inside this workflow:
  its critique a second opinion beside the GUI reviewer's, its quality floor read before a screen is
  built; the design document and the tokens stay the authority, and the author's rulings win over its
  rules. (§8.2.17 S21, S22; §8.2.30 AF4; §8.2.34 AJ6, AJ8; `.claude/skills/np-gui/`)
* The workflow runs on Claude Code alone, and `.claude/` is its single source. (§8.2.49 AY5)
* From Phase 5, a work package is named `WP<phase>.<nn>`, numbered from 01 within its phase
  (`WP5.01`): its plan is `docs/plans/phase-5/wp5.01-<slug>.md`, its pull request `feat: WP5.01 — …`,
  and the commands take `wp 5.01`. Phase 4 keeps its flat numbers to its close. (§8.2.17 S16)
* A plan is written in its phase's folder, `docs/plans/phase-<n>/`, from the commit that adds it, and
  a standalone brief or review in `docs/plans/sessions/`; `current.md` and `index.md` stay at the
  top, and a phase close moves nothing. (§8.2.36 AL5, AL28)
* A commit that adds or changes a decision re-runs `.claude/scripts/decisions.py`, and one that adds
  a plan or a review re-runs `index_records.py`; the gate refuses a decisions page that differs from
  the tree. (§8.2.36 AL3, AL4)
* One work package makes one pull request, green on Tiers 1 and 2 before the next package of its lane
  starts. `/np-implement` stops at the pull request and pauses for a compaction; `/np-ship` then runs
  in a fresh session, or in the implementing session where that runs on the ship's model. Its review
  is one pass by `np-reviewer` (§8.4.5), which fixes and commits each finding it confirms; a finding
  it leaves to the author is an open `REV` row, the pull request merges as reviewed, and a finding
  the author pulls in is fixed and its diff alone reviewed at medium effort. Of a red CI the ship
  fixes only format and lint, with `ruff format` and `ruff check --fix`, and reruns a flaky runner
  once; `np-builder` fixes every other failure. (§8.2.11 L7; §8.2.16 R5; §8.2.33 AI4; §8.2.56 BF1,
  BF4, BF5, BF8; `.claude/workflow/finish.md`)
* `just land` runs the push's mechanics in one command: the registers and their commit, the
  documentation build where a source changed, the rebase, the push gate and the push with retries
  (`.claude/scripts/land.sh`; `.claude/workflow/core.md`, *Gate and push*). (§8.2.56 BF1)
* An implementing session may restructure any code it works with, beyond what its plan names, as long
  as every test of the push gate passes: Tiers 1 and 2 as a push selects them, without the `nightly`
  and `slow` tests (§7.6), with the number-stability golden's per-push walks (VER-62), the layering
  guard (VER-61) and the backend guard (VER-65). The nightly run holds the other walks. A change of specified behaviour still edits
  its clause, and a break of the public surface or the case schema is still listed in `CHANGELOG.md`
  with its migration. The pull request names the restructure. A study package that its plan says
  changes no code changes none. (§8.2.51 BA7, BA13, BA14; `.claude/rules/python.md`)
* At most two lanes are in flight. The current phase runs one package at a time; the second lane is
  the next phase's design study, which changes no `src/`, `tests/`, case schema or public API before
  the current phase's release. A clause that the study restates before that release is added beside
  the clause, tagged for the study's release, and replaces it only when that release ships, or, for a
  clause gating code that the study's phase removes, in the package that removes it. While two
  pull requests are open, `/np-implement` and `/np-ship` take `wp <n>`, `docs/plans/current.md` holds
  one position line per lane, and each package edits only its own. The pull request that merges
  second renumbers every new item of every numbered register (`REV-nn` rows, requirement identifiers
  of every prefix, history records with their §8.2 number and ruling letters, code-review reports),
  each kind in order from one above the highest on `main`, with every reference to them. `/np-ship`
  runs `.claude/scripts/duplicates.py` after merging `main`, and the author merges a second-lane pull
  request only after `/np-ship` has run on it against the current `main`. (§8.2.17 S1, S15 to S18,
  S20; §8.2.18 T5)
* A phase plan, a work-package plan and a work-package pull request open with `## In brief`, about
  250 words, up to 10% over, and readable without code or identifiers. It says what changes and why, what it costs,
  what could go wrong and how it would be noticed. Its *Your call* gives each decision that waits for
  the author, with a recommendation. The work's cost is in §8.3's units, sessions, agent hours and the
  author's touches, from measured comparable packages; a cost to a user of the program, such as
  speed or a dependency, is in its own. (§8.2.10 J9; §8.2.37 AM10; `.claude/workflow/author.md`)
* A work-package plan is grounded in the code. Its `### Grounding` records, by symbol, what the code
  does today, the call path of the change, the shape of what it reads and writes, every variant of its
  input, the registry and layering rows it adds, and how each test gets the object it checks. The plan
  holds 3,500 words outside its Outcome annotations, and 1,500 of them outside its Grounding and its
  `### Implementation details`. The details hold 1,000 words and give a smaller model the exact steps.
  Each count may run up to 10% over; beyond that the plan is trimmed or split. About six decisions is a
  guideline, not a cap: a package that needs more holds them, and its plan's report says why. The plan
  has no `## Design` heading; `.claude/skills/np-plan/wp.md` holds the template. (§8.2.15 Q1;
  §8.2.16 R11; §8.2.33 AI15) WP57's plan is exempt: it has no
  word or decision cap, and keeps its compaction checkpoints (§8.2.23 Y11). WP5.08's plan holds the
  words its seven decisions need (§8.2.33 AI11).
* Each work item names its executor: the main session, or a sub-agent by type and model. The plan's
  status line names the model and effort that wrote it; the models of the build and the ship are
  the agents' (§8.4.5). One commit per work item, ticked `[x] <short sha>`. (§8.2.11 L7; §8.2.16 R11;
  §8.2.56 BF1, BF9)
* Each level of `/np-plan` first asks the author which model plans: Fable 5.2 at high effort, or Opus
  5.5 at `xhigh` when Fable's quota is spent. It pushes its plan, opens its pull request, reports and
  pauses for a compaction. `/np-plan <level> [n] review` then reviews the plan, fixes or records each
  finding, gates and pushes again, and ends with a summary for the person who approves the plan,
  written for a reader who does not code. A work-package plan's review is a fixed self-check, which
  its writer also runs before the commit; another level's is `/code-review medium --fix`. (§8.2.33
  AI2, AI3; §8.2.56 BF3, BF9; `.claude/skills/np-plan/review.md`)
* A choice put to the author carries what a reader who does not code needs to judge it: what is
  decided and why it is open, and for each option what the user gets, what it costs, how hard it is
  to undo and what it touches, with the recommendation's reason and what would change it. A
  work-package plan puts to the author each decision that changes what a user sees or does, fills a
  gap in the design or the phase entry, moves the package's scope, deletes or moves a user's data, or
  trades time against quality. (§8.2.33 AI6, AI7; `.claude/workflow/author.md`)
* A compaction checkpoint is a work item. The session ticks it, gates and pushes, prints a `/compact`
  prompt that names the next item and the values it needs, and ends its turn. When the author sets
  `NANOPNP_AUTO_CHECKPOINT=1`, the session goes on instead, and the hooks give the prompt to the
  compaction that comes when the context fills; `NANOPNP_AUTO_SHIP=1` does the same for the pause
  before `/np-ship`, where the session runs on the ship's model. Where it does not, the session
  pauses and its prompt names the model to switch to. Under `/np-carry`, a checkpoint or a pause
  ends a helper instead, and the next step goes to a new one. (§8.2.11 L7; §8.2.16 R11; §8.2.53
  BC10; §8.2.56 BF1; the WP5.10 plan, D10)
* A phase plan states each package's current scope. The text of each amendment goes to the phase's
  record, read on demand. (§8.2.16 R4)
* A phase plan holds 2,500 words, up to 10% over, without its end-of-phase report; review checks it.
  When a package is delivered its entry becomes one line: the date, the link to its plan and the
  constraints live for later packages. Its delivered summary goes under its own plan's Status line.
  (§8.2.47 AW5; §8.2.50 AZ14)
* Every ruling lands in a current clause. One with no clause to amend is written here once, pointing
  to its ruling. (§8.2.16 R3)
* No ruling leaves the history: a spent or superseded ruling stays in its dated record.
  `clause.py` prints one that only names the identifier asked for as one line, its `holds-now.yaml`
  entry and its first bold phrase, and `--all` prints it in full. (§8.2.50 AZ11)
* The first window of an `/np-implement` session reads at most 8,000 words of
  project text before its first edit: the instruction files, the records and `CLAUDE.md`, as
  `usage.py --reading` counts them (§8.4.5). The number holds the standing instructions, the largest
  plan this section allows, which the session reads whole, and room for the clauses the plan cites.
  A session's first window is the one no message precedes.
  A later window, after a compaction or not, and the plan and ship windows are reported beside it,
  not limited. Under `/np-carry`, nothing precedes a helper, so every helper that implements is
  bound by the same limit; the main session's reading is reported, not limited. (§8.2.49 AY8;
  §8.2.50 AZ9, AZ13, AZ15, AZ18; §8.2.54 BD3)

#### 8.4.5 Agents and models

* The model follows the role, fixed in the role's agent file, not proposed by a plan. Each level of
  `/np-plan` and its review run on Fable 5.2 at high effort, or on Opus 5.5 at `xhigh` where the
  author picks it when asked at the plan's start, for when Fable's quota is spent. Opus 5.5 at high
  effort builds and reviews; Sonnet 5.5 at medium effort ships and runs `/np-carry`'s main session.
  Of a red CI the ship fixes only format and lint and reruns a flaky runner once; every other failure,
  the docs, a stale lock, `mypy`, a test or a numerical gate, goes to Opus with its classified log. Each session and
  agent names its effort, because Opus 5.5's default is medium. The author picks the model when a
  session starts, and a pause's prompt names the next step's. A scoped item, one that a sub-agent
  takes whole with its checks, runs on Sonnet 5.5 at high effort; WP6.04's three blind designers are
  excepted and run on Fable 5.2 and Opus 5.5, as its plan names them. Haiku 5.5 takes only
  mechanical, repetitive work that is fully specified and whose expected context stays under 100,000
  tokens. An item a sub-agent fails goes to a new worker once, then to the next model. (§8.2.11 L6;
  §8.2.38 AN8; §8.2.49 AY7; §8.2.52 BB3; §8.2.56 BF1, BF9)
* A helper of `/np-carry` is a project agent: `np-planner` for the plan, `np-builder` for each
  stretch and a red CI's fix, `np-shipper` for the ship, each with its model, effort and tool list in
  its front matter, so the main session passes neither model nor effort, but Opus at `xhigh` for a
  plan the author put on it. The review is `np-reviewer`, on Opus 5.5 at high effort: one pass over
  standards, the specification and the physics and numerics, which fixes and commits what it
  confirms, and reviews a pulled-in finding's diff at medium. A helper can start no agent and ask the
  author nothing, so the main session does both for it; it keeps the task list, commits under the
  commit gate, runs the push gate and pushes. An agent file is loaded when a session starts. The note
  `knowledge/07-software-stack/26-what-a-claude-code-helper-can-do.md` holds what was measured, and
  on which version of Claude Code. (§8.2.54 BD2; §8.2.56 BF1, BF2, BF4, BF6, BF8)
* Seven agents are kept: the three helpers and the reviewer above; the physics reviewer and the GUI
  reviewer, both read-only and on Opus at high effort (§8.2.38 AN9); and the CI-log classifier, on
  Haiku. A plugin of the author's account is the author's to disable: a project's settings do not
  reach it, and a helper's tool list keeps its tools out (§8.2.56 BF6).
  Nine scripts are kept in `.claude/scripts/`,
  beside `/np-gui`'s own in `.claude/scripts/gui/`: `clause.py` prints a clause by identifier,
  `duplicates.py` names a number that two items of one register share (§8.4.4), `same_tree.py`
  checks that changed Python files differ only in prose (§8.2.11 L5), `decisions.py` writes the
  decisions register and with `--check` compares it, `index_records.py` writes the indexes of the
  plans and reviews (§8.4.4), `links.py` checks every relative link of the tracked Markdown
  (§7.6), `archive_items.py` moves the closed review items to their archive (§8.4.6), `land.sh` runs
  `just land` (§8.4.4), and
  `usage.py` measures a session in §8.3's units, with its tokens by model, from its Claude Code
  transcript. It takes the agent hours from the main transcript and its sub-agents' as one
  timeline and names the count of sub-agents; the sessions and touches stay the main transcript's.
  With `--reading` it gives, for each window an `/np-` command opens, in the session's transcript
  and in each sub-agent's, the words of project text read before the first edit, and with
  `--pages` it reads them from the session service's pages of past sessions. A file counts when
  it is read, or printed by a command that only prints files. Only a call of an edit tool ends the
  count; a change a shell command makes does not, so a session measured against the limit makes
  its first change with an edit tool.
  (§8.2.11 L6, L9; §8.2.16 R6; §8.2.17 S22; §8.2.36 AL3, AL4, AL28; §8.2.37 AM11; §8.2.50 AZ9,
  AZ10, AZ12, AZ16, AZ17; §8.2.54 BD3)
* Each level of `/np-plan`, `/np-implement` and `/np-ship` ends its report with `usage.py`'s line for
  the level. The pull request's **Measured** section keeps one line per level, and `/np-ship` sums
  them into the plan's Outcome beside its estimate. (§8.2.37 AM11)
* A batch of independent, mechanical items, such as a sweep over many files, a rename or a per-module
  pass, goes item by item to a new sub-agent, on Sonnet or, as the first bullet allows, Haiku, given the item
  and the clauses it cites.
  The main session keeps the plan and the git log and re-runs the item's check before the next. Items
  coupled by design stay in the main session. (§8.2.16 R6, R11)

#### 8.4.6 Open items and review

* An open item of an implementation or a review, such as a finding not fixed, a deferral or a question
  for the author, is a `REV-nn` row in `docs/project/review-findings.md` with a section in
  `docs/project/review-items.md`, added in the commit that leaves it open. The commit that resolves it
  sets it `fixed`. A pull request body is never its only record. (§8.2.8 H12)
* A `fixed`, `declined` or `wontfix` row moves, with its section, to `docs/project/review-archive.md`
  at the close of the phase that closed it: `/np-ship phase` runs `.claude/scripts/archive_items.py`,
  which rewrites every link to it. The register keeps the rows that are open or owned by a later
  package, and no `REV` number is reused. (§8.2.50 AZ12)
* A phase closes when each row it owns is `fixed`, or ruled `accepted` with its later package,
  `deferred`, `post-1.0`, `declined` or `wontfix`. A phase's own findings log then closes;
  `docs/project/review-findings.md` stays open. `/np-ship phase` checks it. (§8.2.37 AM4)
* Findings of a user-testing session come only from the author's sessions. An agent may dry-run a
  script to debug it and records no finding. (§8.2.7 G7; §8.2.13 N4)
* Review reports go to `docs/code_reviews/CODE_REVIEW_NNN.md`, numbered one above the highest present.
  (`CLAUDE.md`)
