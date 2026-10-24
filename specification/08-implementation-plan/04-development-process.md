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
  tag if its GitHub access allows it; otherwise it prints the commands and the author pushes them.
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

* The workflow is three commands with levels: `/np-plan <project | phase n | amend n | wp n>`,
  `/np-implement [wp n]` and `/np-ship [wp n | phase n]`, with no aliases. Each routes to a shared
  core and the file of its level. (§8.2.16 R5, R12; `.claude/workflow/core.md`)
* From Phase 5, a work package is named `WP<phase>.<nn>`, numbered from 01 within its phase
  (`WP5.01`): its plan is `docs/plans/wp5.01-<slug>.md`, its pull request `feat: WP5.01 — …`, and the
  commands take `wp 5.01`. Phase 4 keeps its flat numbers to its close. (§8.2.17 S16)
* One work package makes one pull request, green on Tiers 1 and 2 before the next package of its lane
  starts. `/np-implement` stops at the pull request; `/np-ship` starts in a fresh session that did
  not make its decisions. (§8.2.11 L7; §8.2.16 R5; `CLAUDE.md`)
* At most two lanes are in flight. The current phase runs one package at a time; the second lane is
  the next phase's design study, which changes no `src/`, `tests/`, case schema or public API before
  the current phase's release. A clause that the study restates before that release is added beside
  the clause, tagged for the study's release, and replaces it only when that release ships. While two
  pull requests are open, `/np-implement` and `/np-ship` take `wp <n>`, `docs/plans/current.md` holds
  one position line per lane, and each package edits only its own. The pull request that merges
  second renumbers every new item of every numbered register (`REV-nn` rows, requirement identifiers
  of every prefix, history records with their §8.2 number and ruling letters, code-review reports),
  each kind in order from one above the highest on `main`, with every reference to them. `/np-ship`
  runs `.claude/scripts/duplicates.py` after merging `main`, and the author merges a second-lane pull
  request only after `/np-ship` has run on it against the current `main`. (§8.2.17 S1, S15 to S18,
  S20)
* A phase plan, a work-package plan and a work-package pull request open with `## In brief`, at most
  250 words and readable without code or identifiers. It says what changes and why, what it costs,
  what could go wrong and how it would be noticed. Its *Your call* gives each decision that waits for
  the author, with a recommendation. (§8.2.10 J9)
* A work-package plan is grounded in the code. Its `### Grounding` records, by symbol, what the code
  does today, the call path of the change, the shape of what it reads and writes, every variant of its
  input, the registry and layering rows it adds, and how each test gets the object it checks. The plan
  holds at most 3,500 words outside its Outcome annotations, and 1,500 of them outside its Grounding
  and its `### Implementation details`. The details hold at most 1,000 words and give a smaller model
  the exact steps. The plan has at most six decisions and no `## Design` heading. (§8.2.15 Q1;
  §8.2.16 R11)
* Each work item names its executor: the main session, or a sub-agent by type and model. The plan
  names the implementing session's model and effort. One commit per work item, ticked
  `[x] <short sha>`. (§8.2.11 L7; §8.2.16 R11)
* A compaction checkpoint is a work item. The session ticks it, gates and pushes, prints a `/compact`
  prompt that names the next item and the values it needs, and ends its turn. (§8.2.11 L7; §8.2.16 R11)
* A phase plan states each package's current scope. The text of each amendment goes to the phase's
  record, read on demand. (§8.2.16 R4)
* Every ruling lands in a current clause. One with no clause to amend is written here once, pointing
  to its ruling. (§8.2.16 R3)

#### 8.4.5 Agents and models

* Implementation runs on Haiku for an easy mechanical item and on Sonnet by default, and moves to
  Opus only after Sonnet has failed on the item. (§8.2.11 L6)
* Two agents are kept: the physics reviewer, read-only, and the CI-log classifier. The script
  `.claude/scripts/clause.py` prints a clause by identifier. (§8.2.11 L6, L9; §8.2.16 R6)
* A batch of independent, mechanical items, such as a sweep over many files, a rename or a per-module
  pass, goes item by item to a new Haiku or Sonnet sub-agent given the item and the clauses it cites.
  The main session keeps the plan and the git log and re-runs the item's check before the next. Items
  coupled by design stay in the main session. (§8.2.16 R6, R11)

#### 8.4.6 Open items and review

* An open item of an implementation or a review, such as a finding not fixed, a deferral or a question
  for the author, is a `REV-nn` row in `docs/project/review-findings.md` with a section in
  `docs/project/review-items.md`, added in the commit that leaves it open. The commit that resolves it
  sets it `fixed`. A pull request body is never its only record. (§8.2.8 H12)
* Findings of a user-testing session come only from the author's sessions. An agent may dry-run a
  script to debug it and records no finding. (§8.2.7 G7; §8.2.13 N4)
* Review reports go to `docs/code_reviews/CODE_REVIEW_NNN.md`, numbered one above the highest present.
  (`CLAUDE.md`)
