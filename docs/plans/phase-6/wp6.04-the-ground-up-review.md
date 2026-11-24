# WP6.04 — The ground-up review

**Status: delivered, 24 November 2026.** Written 23 November 2026, grounded in the tree at `efda55e`.
Inherits §8.2.51 BA7 and BA10 to BA13, §8.2.52 BB1 to BB6 (BB3 to BB6 ruled at this plan), §8.4.4's sentence on a
study package and the test scope (§8.2.13 N1, N3). Its last commit on `main` takes `v0.7.0-alpha.4` (§8.4.1).

**Delivered.** One report, `docs/project/ground-up-review.md` (5,499 words), and eight appendices under
`docs/project/ground-up-review/`: the author's interview and the method, three blind designs with their unblinding,
the evidence, today's alternatives, a walk of 259 rows (209 keep, 22 change now, 16 change later, one drop, 9 add,
2 not added) and the challenge with each answer. The report holds 25 differences, `GU-01` to `GU-25`, in twelve
groups. The package claims no identifier, writes no test and changes no `src/`, `tests/`, `data/` or `examples/`:
item 15's check prints nothing. Open: REV-280, the proposals, and REV-281 to REV-287, seven questions for a trial,
each owned by the ruling round. Live for later packages: every verdict is a proposal until `/np-plan project` rules
(BA11, BA13); AZ1 to AZ6 and BA1 to BA9 hold until then (BA4); the `GU-` numbers are the draft's, which
`challenge.md` cites.

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.04 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** Nothing in the program. You get one report on the project's pages: what the program should become, the
design a start-over would choose, and every difference from today's program marked keep, change now, change later, drop
or add, with its gain, risk and cost. So that the review does not argue for the program as it is, it runs in a fixed
order. You are interviewed first, until your picture of the program's future is complete. Three designers who have never
seen the code or the requirement list then each say what the program should become and design it, from the paper's
physics, the users and your answers. Only then do they read today's requirements and judge them. A reviewer who knows
the program walks every requirement, constraint, method and process rule, looks up today's alternatives and measures the
program. Two challengers attack the draft, one for today's program, one against.

**Cost.** About ten sessions, seven to thirteen agent hours and sixteen times you act, more if the interview runs
long.

**What could go wrong.** A designer could peek at the program: every file it opened is listed, and a design that
peeked is redone. The review could still find the program sound: each row then shows how many blind designers chose
the same unprompted. It could propose more than one round can rule: the proposals come ranked and grouped.

**Your call.** Settled today: the guard, the interview, the report's place, and that Fable writes it; on 24 November,
that Fable also checks it. Inside the package: the interview. After it: your rulings on its proposals.
*Recommendation:* answer in your own words; the designers read them unedited.

## Execution brief

Scope: the phase plan's WP6.04 entry; BA10 to BA13; BB2 to BB6. It depends on nothing unmerged. It claims no
identifier and writes no test (N1): it changes no `src/`, `tests/`, `data/`, `examples/`, case schema or public name.
**Implementing session: Fable 5.2, high effort. Ship: Fable 5.2, high effort, in the implementing session after its
compaction** (BB5, as BB7 amends it; §8.4.5). The report and its appendices are `docs/project/ground-up-review.md` and
`docs/project/ground-up-review/`, called *the report* and *the appendices* below.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The order is the guard** | Five steps, each committed before the next reads anything: the author's view, by an interview that ends when the author calls the picture complete; three blind designs; their unblinding; the walk with the evidence; the challenge. Until item 4's commit the main session reads no `src/`, no §5 or §6, no survey and no modularity report | Ruled by the author, §8.2.52 BB3: "Purpose first, then rule by rule"; the interview, BB6 |
| **D2 The blind designers** | Three `Plan` agents, which start without `CLAUDE.md`: A on Fable 5.2 with no lead user, B on Fable 5.2 leading with the laboratory (P3), C on Opus 5.5 leading with the method developer (P1). Each reads only the purpose pack, a folder outside the tree, and writes what the program should become, then its design. A design whose transcript shows a path or address outside the pack is discarded and redone once by a new agent; a second peek is kept, marked not blind and left out of the guard's counts | Ruled by the author, BB3; the agent type, the lenses and the check decided by the plan |
| **D3 The unblinding** | Each designer then reads §2.6, §2.7, §3 and §5.6 and marks each requirement, constraint, exclusion and decision keep, change or drop, and names what the list lacks | Ruled by the author, BB3 |
| **D4 The walk** | The main session gives one row to each item BA12 opens: its best alternative, what A, B and C chose, a verdict and a reason. A missing capability is a row marked add. The reason behind a ruling or a knowledge note is evidence, not authority | Ruled by the author, BB3; BA12; the rows' list decided by the plan |
| **D5 Evidence and alternatives** | The program is measured where it cost: size, the files a package touched, open items by area, run times, the records' weight; each number with its command, no script committed. Six Sonnet agents look up today's alternatives by area; the main session checks at its source each fact a proposal rests on | The phase entry ("may run the program and measure it"); the core, *Models and executors*; decided by the plan |
| **D6 The report** | About 5,000 words, at most 5,500, in the sections *Implementation details* fixes. Its design is the main session's own, argued from the three designs, the walk and the evidence. Each difference is a row `GU-nn` with a verdict: keep, change now (in Phase 6), change later (a named phase), drop or add. A keep says whether a start-over would choose it too. A change, drop or add has a card: today, start over, gain, risk, cost at §8.3's measured rates, the clause or ruling it moves and what it depends on. A changed numerical method names the benchmarks argued again and VER-62's re-pin. The proposals are grouped in at most twelve groups for the round, those that change others first | Ruled by the author, BB4; BA13; the form decided by the plan |
| **D7 The challenge** | Two Sonnet agents read the draft: one argues that each change costs more than it gains, one that each keep is habit. The physics reviewer reads each proposal on a numerical method. Their reports are kept unedited; an objection not met is shown on its row | Decided by the plan; §8.4.5 |
| **D8 Records** | Open: REV-280, the proposals waiting for their rulings, and one row for each question only a trial could settle, each owned by the round. `CHANGELOG.md` gains `## [0.7.0-alpha.4]`. A fact that contradicts a knowledge note corrects the note | BA13; §8.4.6; decided by the plan |

### Grounding

**D1**

- `usage.py --reading` binds the first window at 8,000 words (§8.4.4; AZ18). The standing instructions hold 3,238
  (`CHANGELOG.md`, 0.7.0-alpha.3) and this plan about 3,400. Item 1 therefore makes its `Write` before it reads
  anything else.
- What the main session must not read before item 4's commit: `src/`, `specification/05-software-design/`,
  `specification/06-numerics.md`, `docs/project/architecture-survey.md`, `docs/project/modularity*.md`,
  `docs/_generated/`, `docs/design/workbench.md`. `CLAUDE.md` loads at the session's start and names the subpackages;
  the report says so under its method.
- `AskUserQuestion` takes up to four questions a call, each with two to four options and a free-text answer it adds
  itself. The turn does not end, so item 1's unpushed commit meets no stop hook. `.claude/workflow/author.md`'s form
  is for a choice: an interview's options carry no preview and no recommendation.
- The session's own transcript is `~/.claude/projects/-home-user-nanopnp/$CLAUDE_CODE_SESSION_ID.jsonl`, in the
  form D2 gives for an agent's.

**D2**

- The `Plan` agent type has every tool but `Agent`, `Edit`, `Write` and `NotebookEdit`, and the documentation says it
  starts without the `CLAUDE.md` files and the git status; a `general-purpose` agent receives them. It returns its
  design as its last message.
- The Agent tool's `model` takes `fable` and `opus` over the type's own.
- An agent's transcript is
  `~/.claude/projects/-home-user-nanopnp/$CLAUDE_CODE_SESSION_ID/subagents/agent-<id>.jsonl`. Each tool call is a
  block `{"type": "tool_use", "name", "input"}` in an event's `message.content`; read on 23 November 2026 from this
  session's own agent, whose eight calls it listed with their inputs.
- An agent's working directory is the repository (each event's `cwd`), so a check of named paths alone misses four
  calls: a `Grep` or `Glob` with no `path`, which searches the tree; a relative path; a `WebSearch`, which has a query
  and no address; and a tool beyond `Read`, `Grep`, `Glob`, `Bash`, `WebSearch` and `WebFetch`. The pack's own path
  holds `-home-user-nanopnp`.
- Corrected at item 3: two tools beyond the six open no file and no address, and each designer calls both.
  `ToolSearch` loads the web tools, which the `Plan` type holds deferred; `SubagentHandback` returns the design. A
  `Bash` command with no path can also be a word count of the designer's own draft. Such a call is listed and read,
  and is no peek.
- §8.4.5 puts a scoped item on Sonnet; BB3 excepts this package's blind designers, and §8.4.5 says so.
- Implementation words (`ngsolve`, a `.py` path, a package number), counted by `grep -ciE`:
  `knowledge/02-electrokinetics-background/` 0 in 3,430 words; `knowledge/03-nanopore-biology/` 0 in 3,360;
  `specification/b-comsol-settings.md` 0; `specification/04-physics.md` 8 lines; `knowledge/01-physics-epnpns/` 22
  and `knowledge/05-analyte-and-forces/` 30, so both stay out of the pack.
- Corrected at item 3: one of §4's eight lines names the engine, "NGSolve's own estimate for the source", and a
  first run of the three designers, all of whom chose it, was set aside for that and for a line of §1.3's closing
  paragraph the cut had left. The pack's copy of §4 reads "The engine's own estimate" and differs in nothing else.
  §4 also prescribes PDB2PQR with PROPKA (PHY-16) and names `io/defaults.py`; both stay and are marked prompted.
- `specification/02-product-overview.md` holds §2.1 to §2.5 (context, the reference model, S1 to S4, P1 to P3, the
  operating environment), then §2.6, the dependencies, and §2.7, the releases. `specification/01-introduction.md`
  holds §1.1 to §1.3 (purpose, scope, definitions), then §1.4 to §1.6.
- These sources name today's choices: Python (§1.1, §2.5), a 2D-axisymmetric finite-element mesh and the pipeline's
  steps (§1.2), a YAML case file (§1.3), the browser workbench (P3, §2.5) and a sparse direct solve (§2.5). §1.3's
  closing paragraph lists the workbench's terms and links `docs/design/workbench.md`.
- The repository is public; a designer's brief forbids it on disk and online.

**D3**

- `SendMessage` continues an agent by its id with its context; it is a deferred tool (`ToolSearch`,
  `select:SendMessage`).
- §3 is `specification/03-requirements.md`, 6,425 words: IF-01 to IF-09, FR-01 to FR-44, QR-01 to QR-16, CON-01 to
  CON-14, N1 to N7. §5.6 is `specification/05-software-design/06-architecture-decisions.md`, 1,910 words, ADR-001 to
  ADR-005.

**D4**

- Beside D3's rows: NUM-01 to NUM-34 (`specification/06-numerics.md`); the ten files of
  `specification/05-software-design/` but §5.6; §7.1, §7.2 to §7.5 one row a tier, §7.6, VER-61, VER-62 and VER-65;
  §8.4's 41 bullets (4, 5, 2, 21, 4 and 5 in §8.4.1 to §8.4.6); §2.7's rows from v0.7; BA1 to BA15 and BB1 to BB6;
  §2.6's 12 rows; the 17 sections of `docs/design/workbench.md`, which holds 63 `WB-` rows. About 245 rows.
- Corrected at items 9 and 10: the walk holds 259 rows, with 11 rows for what the lists lack.
- `uv run .claude/scripts/clause.py <ID>` prints a clause with the rulings behind it.

**D5**

- Today: 80,973 lines of Python in the 20 subpackages of `src/nanopnp/`, `gui/` 21,422 and `validation/` 8,560, with
  15,296 lines of JavaScript and CSS; Tier 1 has 115 test files and 32,563 lines, Tier 2 60 and 12,025.
- Corrected at item 6: 11,802 of those 15,296 lines are bundles shipped unmodified (Mol\*, NGSolve's `webgui`, KaTeX,
  uPlot); the workbench's own are 1,700 of JavaScript and 1,794 of CSS. `v0.6.0-alpha.1` does not exist, so the
  first range starts at `v0.5.0`.
- The clone is shallow, 50 commits: history needs `git fetch --unshallow origin` and `git fetch --tags origin`. A
  package is the range between two `-alpha.N` tags (§8.4.1).
- The register's rows are `| REV-n | Area | Severity | Status | Ruling | Finding |`, 59 in
  `docs/project/review-findings.md` and the closed ones in `review-archive.md`.
- `uv run nanopnp run <case>` runs a case; `NANOPNP_STORE` names the store, so a new folder gives a run with no cache
  hit. The container has no `/usr/bin/time`; bash's `time` gives the wall time. The cases:
  `examples/01-quickstart/quickstart.case.yaml`, `examples/02-charged-pore/epnpns.case.yaml`.
- `docs/project/cost-study.json` holds stage timings of the `2wcd` and `quickstart` walks at `db952e3`. The phase
  plan's *True of the codebase today* and Phase 5's end-of-phase report hold the gate's 539 s, the 763 MB install and
  the redraw times; cite them, do not measure again.
- Web search is allowed for libraries and never for the model's equations (`CLAUDE.md`).

**D6**

- `mkdocs.yml` sets `validation.nav.omitted_files: warn`, and the build is strict: each page under `docs/` is in the
  navigation or under `exclude_docs`. The *Project* section is written by hand; `docs/project/index.md` lists its
  pages in a table. The architecture survey is the precedent for both.
- `docs/plans/` and `docs/code_reviews/` are excluded: the strict build passes a link into either and reports it at
  `INFO`, and the link is dead on the site. `.claude/scripts/links.py` checks every relative link.
- §8.3's measured rates: a text or clean-up package 5 sessions, 3 to 6 agent hours and 8 touches; a shell package 6,
  6 to 12 and 10.
- G1 to G12 are rulings of §8.2.7, so the rows take `GU-`, which no register uses.

**D7**

- `.claude/agents/physics-reviewer.md` is read-only and on Opus (§8.4.5).

**D8**

- The highest review item is REV-279; REV-280 is free. The statuses and the row form are in the head of
  `docs/project/review-findings.md`; a row has a section `### REV-n: <title>` in `review-items.md`.
- Corrected at item 15: item 14 added a seventh trial question, so the rows are REV-280 to REV-287. No checked fact
  contradicts a knowledge note: knowledge 07/01 says that the wheels hold no PARDISO, which stands, and it gains the
  route through pip's `mkl` that item 7 read.
- `CHANGELOG.md`'s newest section is `## [0.7.0-alpha.3]`, under `## [Unreleased]`.

### Implementation details

**Item 1.** Before any other read, `Write` the report with its status line and these headings: *In brief*; *The
question, and what is given*; *What the program should become*; *The design a start-over would choose*; *The
differences*; *The proposals, grouped for the rulings*; *What the guard showed*; *What stays open*; *How it was made*.
Write the eight appendices with a title and one line each: `method.md`, `design-a.md`, `design-b.md`, `design-c.md`,
`evidence.md`, `technologies.md`, `walk.md`, `challenge.md`. In `mkdocs.yml`, after the architecture survey's line:

```yaml
      - Ground-up review: project/ground-up-review.md
      - "Ground-up review, appendices":
          - How it was made: project/ground-up-review/method.md
```

and one titled line for each other appendix. Add the report's row to `docs/project/index.md`. Run `uv run just docs`.

**Item 2.** An interview, in `AskUserQuestion` rounds of at most three open questions. An option is a suggestion, named
so, in a user's terms; the free-text field takes the author's words. The picture has eight points: what the program
becomes in three years, and for whom; what would not be built again, or differently, and why; what a start-over must not
lose; its users in rank order, and what each must be able to do; how success would be seen; what it must never become;
what is fixed from outside (licence, platforms, install, the author's time); which goal wins when two pull apart. Round
1 asks the first three. Each later round asks what an answer left vague, where two pull apart, and the points still
open; a ticked suggestion alone is asked why. The interview ends only when the author calls a summary of at most 400
words complete. Write each round and the summary, unedited, into `method.md`.

**Item 3.** Build the pack in the session's scratchpad, `<scratch>/pack/`: §1.1 to §1.3, less §1.3's closing paragraph,
and §2.1 to §2.5 cut by their headings into `purpose.md`; `specification/04-physics.md`, less the engine's name;
`specification/b-comsol-settings.md`; the two knowledge folders of D2; the interview as `author.md`. Record each
file's word count in `method.md`. Launch the three `Plan` agents in one message, each with the same brief but its lens.
A has none. B: "Design first for the experimental laboratory, P3 of `purpose.md`." C: "Design first for the method
developer, P1 of `purpose.md`."

> You design a program from nothing. Read only the files under `<pack>`, and give each search that path. Open no other
> file on this machine and no page of the project `nanopnp`. The physics in `04-physics.md` is given; a file, library or
> method that the texts name is today's choice and binds nothing. You may look up libraries; never search for the
> model's equations. [Lens.] Write at most 3,000 words, with no link, under these headings: 1 What the program should
> become, for whom, its capabilities in rank order, and what it leaves out. 2 The architecture: components, data,
> boundaries. 3 The technologies, each with its runner-up and the reason: the simulation engine and discretisation;
> geometry and mesh; linear and nonlinear solution; structure and charge preparation; the front end and visualisation;
> storage, file formats and the record of a run; distribution to the three kinds of user; many runs at once. 4 The
> numerical method and how its results are trusted. 5 How it is developed: process, tests, records. 6 The three choices
> you are least sure of.

For each agent, list the `tool_use` inputs of its transcript. A `Read`, `Grep`, `Glob` or `Bash` input that names a
path outside `<pack>`, a query or an address holding `nanopnp`, or one of the four calls D2's grounding lists that
could reach the tree, discards the design; D2's grounding names the calls that cannot. Write each design unedited into its file, and the brief, the lens, the model and the list's
result into `method.md`.

**Item 4.** Continue each agent: it now reads `specification/02-product-overview.md` from §2.6,
`specification/03-requirements.md` and `specification/05-software-design/06-architecture-decisions.md`. It returns,
in at most 1,500 words, one table per group (IF, FR, QR, CON, N1 to N7, ADR) with keep, change or drop and one line
each, then what the lists lack. If an agent cannot be continued, a new `Plan` agent on its model gets its design and
the texts. Append each answer unedited to its design's file. List each agent's calls again: it reads those three
files alone. List this session's own calls up to here the same way, and write into `method.md` that none names D1's
paths.

**Item 6.** `evidence.md`, each number under its command: lines by subpackage; for each package since
`v0.6.0-alpha.1`, the files and the subpackages its tag range changed under `src/` (`git diff --name-only`); the
register's rows by area and severity; both example cases timed with bash's `time`, one thread, a new
`NANOPNP_STORE`, each with the stabilisation mode its manifest records; `wc -w` of the specification, the history and
the plans beside the lines of code; §8.3's measured rates.

**Item 7.** Six `general-purpose` agents on Sonnet at high effort, one per area: the simulation engine; geometry and
mesh; linear and nonlinear solvers; the front end and visualisation; storage, formats and many-run dispatch;
structure and charge preparation with distribution. Candidates: today's choice, each one a blind design names, and
the agent's own. Each returns one table: licence; wheels for Windows, macOS and Linux on Python 3.11 to 3.14 without
a compiler; what the area needs (for the engine: axisymmetric weak forms, second-order and Taylor–Hood elements, a
symbolic Jacobian, a direct sparse solve at 10⁶ unknowns); the last release; what it lacks; the source of each cell.
Write them into `technologies.md`.

**Items 9 and 10.** `walk.md`, one table per group:
`| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |`. A, B and C hold `=`, `≠` or `–`
(silent). Item 9: IF, FR, QR, CON, N1 to N7, §2.6, §2.7 and the rulings BA1 to BB6. Item 10: ADR, §5, NUM, §7, §8.4 and
the workbench design.

**Item 12.** Fill the report. *The differences* is one table, `| GU | Difference | Verdict | Gain | Cost | Moves |`,
ranked by gain over cost; the cards follow under *The proposals*. *What the guard showed* is a table of the technologies
and the methods against A, B and C; a choice the pack names (D2's grounding) is marked prompted. Link only the
appendices and pages the site publishes; name a clause, a plan or a review in code spans.

**Item 14.** Give each challenger the report, `walk.md` and `evidence.md`. Write the three reports unedited into
`challenge.md`, then answer each objection in the report: the row changed, or the objection shown on it.

**Item 15.** Check `git diff --name-only origin/main...HEAD -- src tests data examples` prints nothing.

### Work items

- [x] 9e27418 1. The report's skeleton, its appendices, `mkdocs.yml` and `docs/project/index.md` (D6); done when
  `uv run just docs` passes. **Executor:** main
- [x] 2085983 2. The author's view, in `method.md` (D1); done when the author has called the summary complete. **Executor:**
  main
- [x] 3547056, ea377ff 3. The pack and the three blind designs, in `design-a.md` to `design-c.md` and `method.md`
  (D2); done when each transcript's list holds no path outside the pack. **Executor:** main, with `Plan` agents on
  Fable 5.2 and Opus 5.5
- [x] c1781b1 4. The unblinding, appended to the three designs (D3); done when each holds its tables and both lists are
  clean. **Executor:** main, with the same agents
- [x] 5. Compaction checkpoint. **Executor:** main
- [x] 0ca2ef0 6. `evidence.md` (D5); done when each number names its command. **Executor:** main
- [x] 1307b9e 7. `technologies.md` (D5); done when each cell names its source.
  **Executor:** main, with `general-purpose` agents on Sonnet, high effort
- [x] 8. Compaction checkpoint. **Executor:** main
- [x] 2b6db6d 9. The walk of the requirements, the releases and the rulings, in `walk.md` (D4). **Executor:** main
- [x] af8ee8c 10. The walk of the design, the methods, the verification, the process and the workbench (D4).
  **Executor:** main
- [x] 11. Compaction checkpoint. **Executor:** main
- [x] d5ebeb0 12. The report: the design, the differences and the proposals (D5, D6); done when each fact a card rests on is
  checked at its source. **Executor:** main
- [x] 13. Compaction checkpoint. **Executor:** main
- [x] 8937edb 14. The challenge, in `challenge.md`, and the report answered (D7). **Executor:** main, with two
  `general-purpose` agents on Sonnet and the physics reviewer
- [x] 3f56656 15. The records: REV-280 and its like, `CHANGELOG.md`, the knowledge notes corrected (D8); the no-code check.
  **Executor:** main

> **Outcome — the challenge moved the lead proposal.** The draft of item 12 built the composed kernel in Phase 6
> and asked for seven more packages. Item 14's three reports showed that the workbench reads the model through nine
> names, that shared coefficients and bound terms make the composition a design round's work, and that VER-62
> guards the default switches alone. The report now keeps the kernel in Phase 8 (AZ1) and asks for about three
> packages. Eleven verdicts of the walk changed; `challenge.md` holds each objection and its answer.

> **Outcome — the first run of the designers was set aside.** One line of the pack's §4 named the engine; the pack
> was corrected and three new agents designed again (`method.md`, *The first run, set aside*).

Items 2 to 4, 6, 7, 9, 10, 12, 14 and 15 are outside the test scope: done when the code and review say so, and
`uv run just docs` passes.

### Verification

No test (N1; the phase plan's verification row). Review checks, each by its command or its file:

- the no-code check of item 15 prints nothing, and `nanopnp.PUBLIC` and the case schema are unchanged with it;
- the commits of items 2, 3 and 4 precede item 6's (`git log`);
- `method.md` holds the interview's rounds and summary, each designer's brief, model and lists of calls, and the main
  session's list up to item 4's commit, which names none of D1's paths;
- the report holds what BA13 lists: the design, each difference with its verdict, and for each change its gain, risk,
  cost and the clause or ruling it moves; each changed numerical method names its benchmarks (VER-62; G10);
- each `walk.md` group holds every identifier of its range;
- the report holds at most 5,500 words (`wc -w`) and its proposals at most twelve groups;
- `uv run just docs` and the push gate pass.

### Out of scope

- Any change of code and any trial of a design (BA13): a question only a trial settles is a `REV` row for the round.
- The rulings on the proposals: `/np-plan project` (BA11, BA13). The re-plan they cause: `/np-plan amend 6`.
- The physics of §4 (BA12). A comparison with the published results (BA3).

### Open questions

None blocks the implementation. The interview is item 2's.
