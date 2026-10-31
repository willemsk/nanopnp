# WP58 — Documentation increment 4: the guide current, plainer and free of stale text

**Status: planned, not started.** Written 31 October 2026, grounded in the code and the prose at
`6111f46` (§8.2.15 Q1). Inherits §8.2.24 Z1 to Z4, §8.2.21 W1 to W6 and the test scope (§8.2.13
N1, N3). Tag `v0.5.0-alpha.24`. The [Phase 4 plan](phase-4-polish-and-user-testing.md)'s WP58
entry sets this scope; `SPECIFICATION.md` governs, and where it and this plan disagree this plan
is wrong.

## In brief

The program changed a great deal this phase and the written guide did not keep up. Some of what it
tells a reader is now untrue: the banner on every page describes a scope two releases old, and
four places say a calculation reads its input files relative to wherever you happen to be standing,
which it no longer does — it reads them beside the case file. Two new commands reach no reader, and
nothing covers driving the program from Python or lists the notebooks.

**What changes.** Every untrue statement in the guide, the examples and the front page is corrected
or removed. Two new pages: one on driving the program from Python, from building a calculation to
drawing its figures, and one listing the notebooks with the command that opens each. A few
paragraphs in a voice unlike the guide's are rewritten in it. The program is untouched, so no
result and no recorded number moves.

**Cost.** About a week, with nothing added to the checks before each push.

**What could go wrong.** A new page could gain a snippet that does not run, since no check
executes the guide's code; every snippet is run by hand once and recorded. The sweep could miss a
statement; what it cannot fix becomes a tracked item.

**Your call.** Nothing waits on you. One question is at the end for your awareness: whether the
site's banner should stop saying *pre-alpha* now. *Recommendation:* at the validated release
instead.

## Execution brief

Scope: §8.1's Phase 4 documentation increment; §8.2.24 Z1 to Z4; §8.2.21 W1 to W6; UT-02, UT-05,
UT-06, UT-08, UT-09, UT-11. Depends on WP57, merged at `8a3488c`. It claims no identifier and
writes no test. **Implementing session: Sonnet, medium effort**; an item judging what is stale or
normative stays in the main session.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 Scope, and the guarantee that no number moves** | Prose and navigation only: `README.md`; `mkdocs.yml`'s hand-written *User guide* block; under `docs/`, `overrides/main.html`, `index.md`, `getting-started.md`, `guide/` with the two new pages, `examples/index.md`, `reference/index.md`, `project/{index,modularity-findings,review-findings}.md` and `user-testing/findings.md`; `examples/*/README.md`; `notebooks/*/README.md`. No file under `src/`, `tests/` or `data/`, no `*.case.yaml` or `*.msh`, no line in a tagged block | §8.2.24 Z4: every case hash, every documented number and VER-62's golden stand, and VER-46 walks the examples unchanged |
| **D2 The Python interface page** | A hand-written `docs/guide/python.md`, label *The Python interface*, before *Desktop shell*, one section per job in *Implementation details*' order. It shows only keys of `nanopnp.PUBLIC`, names no private module and no `Case.run`, and links the API reference and example 04 rather than repeating either. **Each snippet is run once before the commit and its command and exit status recorded in the Outcome** | UT-10; §8.2.23 Y1 to Y10; §8.2.24 Z2. No test executes guide code, and a docs-code test is outside the test scope (N1) |
| **D3 The notebooks page** | A `docs/guide/notebooks.md`, label *Notebooks*, after D2's page: a table of the six, each with one sentence on what it shows, the two commands that run and open it, and an absolute GitHub link to its README. **No export step enters `docs/scripts/generate.py`** | §8.2.24 Z2: listed, not rendered. `notebooks/` is outside `docs_dir`, so a relative link would fail the build |
| **D4 One bounded pass for currency and for plainness** | It reads **live prose** — what a reader is asked to believe today — and leaves the recorded text of a finding, an Outcome, a ruling or a changelog entry, which record what was true then. Currency is the six mechanical checks of *Implementation details*; plainness only where a page leaves the guide's voice, each departure named there. **What it cannot fix becomes a `REV-nn` row** | §8.2.24 Z3 spends the migration page's effort here. A mechanical check is reviewable where taste is not; §8.4.6 and H12 own what is open |
| **D5 Which numbers a page may carry** | The running page answers UT-09 and UT-11 **with no new number of its own**: the solve's cost as an order of magnitude, a pointer to `docs/project/cost-study.json`, and the thread pinning as a rule, not a timing | VER-46: no number appears in the user documentation as a result unless an example asserts it, and REV-116 has WP59 re-run the cost record |
| **D6 The release-scope prose: delivered, not released** | Every scope statement is brought to what this tree delivers and names the release as **v0.5, not yet tagged**: `README.md`'s v0.5 roadmap row reads `in progress`, and `docs/index.md` and `docs/overrides/main.html` give the v0.5 scope, release pending. The `[0.5.0]` section, the `released` row and `CITATION.cff` are **WP59's** | §8.2.24 Z1: `v0.5.0` sits on the close's commit (§8.4.1); a page claiming an absent tag is this package's own staleness |

### Grounding

Facts at `6111f46`.

**D1.**

- `docs/scripts/generate.py:_copies` copies `SPECIFICATION.md`, `CHANGELOG.md`, `knowledge/`,
  `specification/` and each `examples/NN-slug/README.md` into `docs/_generated/`, and
  `nanopnp.cli.reference` renders the five reference pages. WP58 adds nothing to it: the two new
  pages are hand-written under `docs/guide/`.
- `mkdocs.yml` carries the specification and knowledge navigation between generated
  `BEGIN`/`END` markers spliced by `nanopnp.validation.okf.splice_navigation`; the *User guide*
  block above them is hand-written, and that is where D2's and D3's entries go.
- `mkdocs.yml`'s `exclude_docs` drops `plans/`, `user-testing/`, `code_reviews/`, `overrides/` and
  the design subdirectories, so `docs/user-testing/findings.md` and `docs/overrides/main.html` are
  documentation sources that are not pages: an edit to either needs no navigation change, and
  neither can break a link.
- VER-46 executes the tagged console blocks of `examples/*/README.md`; VER-69 those of
  `docs/user-testing/sessions/*/README.md`. Both read the blocks verbatim, so D1's tagged-block
  guarantee is what keeps the package off the gate's clock.

**D2.**

- `src/nanopnp/core/public.py:PUBLIC` holds the nineteen names `nanopnp` re-exports: `Case`,
  `Session`, `RunResult`, `SweepResult`, `Artefact`, `Store`, `orient_pore`; the three model
  protocol names with `register_model` and `registered_models`; and the seven control types of
  `core.stages` (`Progress`, `CancelToken`, `CancelFlag`, `Cancelled`, and the three hooks).
  `reproduce` is **not** among them, so the page's "reopen a recorded run" is
  `nanopnp.api.session:Session.open`, which reads a run directory's artefacts back from the store.
- `nanopnp.api.case:Case` subclasses `CaseDocument` and offers `load`, `loads`, `dump`, `dumps`,
  `__getitem__`, `with_`, and the two factories `cylinder` and `from_structure`.
- `nanopnp.api.session:Session.__init__` takes `store`, `write`, `workspace`,
  `overwrite_workspace`; `run` takes `upto`, `only`, `progress`, `cancel`, `on_stage`, `on_solve`,
  `on_artefact`; `stages` returns `StageInfo` rows; `register_stage` adds a function whose
  parameters name the stages it reads; `sweep` takes `axis`, `values`, `origin`, `workers`,
  `check_meshes` and refuses `workers > 1` beside a stage of one's own.
- `nanopnp.pipeline.run:RunResult` carries `directory`, `manifest`, `artefacts`, `stages`, `store`,
  `resolved`, the properties `quantities`, `current_nA`, `conductance_nS`, `fields`, `files`, and
  the drawing methods `figure`, `plot_field`, `plot_cutline`, `field_choices`, `quantity_rows`.
  `nanopnp.api.sweep:SweepResult` carries `rows`, `plot_iv` and `figure`.
- `examples/04-python-api/README.md` and its `tour.py` already execute four jobs: introspecting the
  stages, running with a progress callback, `with_` and `upto`, and reading the IF-07 export back.
  They cover neither `register_stage`, nor `sweep`, nor the drawing methods, nor `open`. The page
  carries the narrative and links the example for the runnable tour.
- `docs/index.md`'s *Where to start* row "Script it from Python" points at example 04 and the API
  reference; it gains the new page.

**D3.**

- `notebooks/` holds six directories, each a `README.md` and a `notebook.py`:
  `01-geometry`, `02-charge`, `03-solve`, `04-sweep`, `05-cylinder`, `06-2wcd`. Each README's
  tagged block is `$ python notebook.py` and each then gives `$ marimo edit notebook.py` to work in
  it; each names the `notebook` extra and the shared store `notebooks/.store`, overridden by
  `$NANOPNP_STORE`. The one-sentence summaries come from each README's first paragraph.
- `pyproject.toml` defines `notebook = ["nanopnp[plot]", "marimo>=0.25.2"]`, so the page's extra is
  `notebook`, not `plot`.

**D4 — what the checks find today.**

- **The site banner is two releases stale.** `docs/overrides/main.html` reads "Pre-alpha, v0.3
  scope … the charge pipeline is not [delivered]", on every page of the site; v0.4 shipped it.
- **Path resolution is stated backwards in four places.** `src/nanopnp/cli/__init__.py` resolves a
  case with `base = Path(args.case).resolve().parent`, and §5.3.1's NOTE on a relative path makes
  every `inputs.*.path`, `structure.source.path`, `structure.ensemble.trajectory` and correction
  file read beside the case file, an edited copy and a sweep member included. Against that:
  `docs/guide/case-files.md`'s section *Paths in a case resolve against the working directory*
  (heading and body, including its claim that a path set by `Case.with_` is read against the working
  directory and its reference to a `Case.run` that no longer exists); `docs/guide/running.md`'s
  *Store and file resolution* paragraph; `docs/guide/sweeps.md`'s sentence on the members' case
  paths; and `docs/examples/index.md`'s closing "Case paths resolve against the working directory".
  No page links the heading's anchor, so the heading can change.
- **Two commands reach no reader.** `nanopnp --help` lists `plot`, and `nanopnp run --help` lists
  `--progress | --no-progress`; neither appears anywhere in `docs/` outside the generated
  reference. `docs/guide/running.md`'s command table has no `plot` row, and
  `docs/guide/outputs.md` has no figures section.
- **The three logs rest on a withdrawn check.** `docs/project/modularity-findings.md`,
  `docs/project/review-findings.md` and `docs/user-testing/findings.md` each say
  `tests/tier1/test_findings_logs.py` checks every row (VER-63). That file is absent from
  `tests/tier1/`, and §7.2 reads "**VER-63** | Withdrawn". The modularity log's next clause — that
  a `closed` header refuses a row that is not terminal — rests on the same absent test, and WP59
  sets that header, so the sentence has to say that review checks it.
- **The review register's area list is short by two.** Its front matter reads
  `areas: [coupling, performance, verification, documentation, physics, numerics, interface,
  process]`, while its rows use `provenance` twice (REV-158, REV-161) and `tooling` once.
- **The reference index claims a test that is gone.** `docs/reference/index.md` ends "A Tier-1 test
  asserts each generated page against its source in both directions"; no test imports
  `nanopnp.cli.reference`, and VER-45's row has the generated references "verified at review"
  (§8.2.13 N3).
- **The extras are listed short in two places.** `pyproject.toml` defines `structure`, `gui`,
  `gmsh`, `plot`, `notebook` and `examples`. `docs/getting-started.md` says "Four optional extras"
  and lists four; `README.md`'s extras table lists four. Both omit `plot` and `notebook`.
- **Example 01 is three commands, not four.** `examples/01-quickstart/README.md`'s tagged block is
  `run`, `inspect`, `reproduce`, the case declaring its own pore since WP57; its own title still
  reads "mesh, run, inspect, reproduce", `docs/getting-started.md` says "four commands: generate a
  mesh, run a case, inspect the run, and reproduce it", and `docs/examples/index.md`'s row 01 reads
  "mesh, run, inspect and reproduce one case".
- **Release scope.** `docs/index.md`'s warning is headed "Pre-alpha: the v0.4 scope"; `README.md`'s
  status paragraph ends at "(Phase 3, v0.4)" and its roadmap row for v0.5 reads `planned`.
- **The project index omits three of its own pages.** `docs/project/index.md`'s table lists ten
  pages; `mkdocs.yml`'s *Project* block also carries *Review register*, *Review findings* and
  *Workbench design*, which the table does not name.
- **The register's items keep their own history.** `docs/project/review-items.md` holds superseded
  `**Open**:` lines under resolved items, two of which name "WP58" meaning Phase 5's WP5.02
  (REV-129, REV-132), and quotes `nanopnp mesh cylinder` four times as the command a finding was
  found with. These are the record of a finding, not live prose, and D4 leaves them.

**D5.**

- UT-09 measured 761 s on a 16 562-element cylinder, 62 % assembly and 24 % factorisation;
  REV-156 holds it and §8.2.24 Z6 sends it to Phase 6. REV-116 has WP59 re-run
  `python -m nanopnp.validation.costs all` and replace `docs/project/cost-study.json`.
- `nanopnp run --help` gives `--threads`; W6 put the one-thread-per-worker rule in
  `sweep run`'s own help, and `docs/guide/running.md`'s last bullet states it already.

**D6.**

- `README.md`'s roadmap table marks v0.1 to v0.4 `released` with their changelog links and v0.5
  onward `planned`; `CHANGELOG.md` has no `[0.5.0]` section, and `current.md` records
  `v0.5.0-alpha.23` as still the author's to push.

### Implementation details

**The six currency checks.** Over D1's files: (1) each `nanopnp` command and flag a page names
appears in `nanopnp --help` and in that command's own `--help`; (2) each Python name is a key of
`nanopnp.PUBLIC`; (3) each test file a page names exists under `tests/`; (4) no `VER-`/`VAL-` a page
names reads `Withdrawn` in §7.2 or §7.3; (5) each extra a page lists appears in `pyproject.toml`'s
`[project.optional-dependencies]`, and any counting word agrees; (6) each statement on path
resolution or release scope agrees with §5.3.1's NOTE on a relative path and with §2.7. The guide's
voice, for the plainness pass: present tense, one idea a sentence, the thing itself as the subject,
and none of *via*, *e.g.*, *Alternatively*, *configurable* or *utilise*. No page outside the named
departures is rewritten, and no heading is renamed without its navigation and cross-link edits.

**The two new pages.** Both are hand-written Markdown under `docs/guide/`, each opening with a
one-sentence statement of what it is for and a link to the generated reference beside it. Add each
to `mkdocs.yml`'s hand-written *User guide* block and to `docs/guide/index.md`'s table in the same
commit, then run the strict build; the build is the only check either page has.

`docs/guide/python.md`, in order: **Build a case** — `Case.cylinder(...)`,
`Case.from_structure(...)`, `Case.load(path)` and `Case.loads(text)`, and `case.with_(...)` as a
copy, noting that a relative path is read beside the case file and that an edit is made absolute
against it. **Run it** — `Session(store).run(case)`, with `upto=`, `only=`, `progress=`,
`cancel=CancelFlag()` and the three hooks named as what they report, not as inputs. **Read the
result** — `result.quantities`, `current_nA`, `conductance_nS`, `result.manifest`, `result.files`.
**Draw its figures** — `result.figure(stage)`, `result.plot_field(quantity, zoom_nm="lumen")`,
`result.plot_cutline(...)`, `result.field_choices()`, and the `plot` extra. **Sweep** —
`session.sweep(case, axis="bias_V", values=[...])`, then `swept.rows`, `swept.plot_iv()`.
**A stage of one's own** — `session.register_stage(function)`, its parameters named for the stages it
reads, keyed by its code. **Reopen a recorded run** — `session.open(directory)`. Close with a line
pointing at example 04 for the runnable tour and at the API reference for every name.

Prove the snippets: from a copy of `examples/01-quickstart/`, in a scratch directory with its own
store, run each one with `uv run python`, and paste the commands and exit statuses into the item's
Outcome annotation. Then check every name on the page against
`uv run python -c "from nanopnp.core.public import PUBLIC; print(sorted(PUBLIC))"`.

`docs/guide/notebooks.md`: one short paragraph — the notebooks are interactive marimo documents in
`notebooks/`, they need the `notebook` extra, they share the store `notebooks/.store` unless
`$NANOPNP_STORE` names another, and they are not rendered on this site — then the table of six, in
directory order, each row linking
`https://github.com/willemsk/nanopnp/blob/main/notebooks/<directory>/README.md`. Draw each sentence
from the README's first paragraph and shorten it; quote no number from a README.

**The currency pass.** Work the grounding list above, file by file. Three edits need care:

- `docs/guide/case-files.md`: the heading becomes a statement of the rule as it is (a case's paths
  are read beside the case file); the body loses the working-directory claim and the `Case.run`
  sentence, and says that a path an edit sets is made absolute against the same directory.
  `docs/guide/sweeps.md` and `docs/examples/index.md` follow in the same commit, so no two pages
  disagree mid-branch.
- The three findings logs: replace "`tests/tier1/test_findings_logs.py` checks every row (VER-63)"
  with the fact — each row is read at review (§8.2.13 N3) — and in `modularity-findings.md` make the
  closing clause say that a `closed` header is checked at review too. Add `provenance` and `tooling`
  to `review-findings.md`'s `areas`.
- `docs/reference/index.md`: drop the closing paragraph's claim of a test and say that the pages are
  generated from the live objects at build time and read at review (VER-45).
- `docs/project/index.md`: add the three pages its table omits.

**The plainness pass.** Exactly three pieces of `docs/guide/running.md`, added by WP56 and written
in another voice: *Store and file resolution*, *Multithreading and CPU concurrency* and its bullet
list. Rewrite them as the rest of the page reads: the store's default and its two overrides in one
sentence; the thread rule as `--threads`, the environment variables it sets, and that a sweep pins
each worker to one thread; the cost as D5 has it. Nothing else on the page moves. If a sixth check
turns up a departure on another page, name it in the Outcome before rewriting it.

**UT-02, UT-05, UT-08.** `docs/getting-started.md` and `docs/guide/meshes.md` each gain one
sentence pointing at `nanopnp geometry cylinder --help` and `nanopnp mesh --help` for the flags, the
geometry ones apart from the mesh ones. `docs/guide/provenance.md`'s *Reproducing a run* gains the
causes of a run that does not reproduce, as `nanopnp reproduce --help` already states them.
Across the pass, use one name for one thing: `nanopnp env` for the command and `--env` named once as
its alias, and a case file named for what it sets.

### Work items

Each item is outside the test scope: done when the strict build passes and the review says so
(N1, N3).

- [ ] 1. The currency pass over `README.md`, `docs/{index,getting-started}.md`,
  `docs/overrides/main.html`, `docs/guide/{case-files,sweeps,meshes,running,outputs}.md` and the
  index pages of `docs/examples/` and `docs/reference/`: every statement the six checks find, plus
  the `plot` row and `--progress` in the running page's table and a figures section in
  `docs/guide/outputs.md` (D1, D4, D5). **Executor:** main
- [ ] 2. `docs/project/` and `docs/user-testing/findings.md`: the withdrawn-check sentences
  replaced, the modularity log's closure clause rested on review, `provenance` and `tooling` added
  to the register, the section index completed (D4). **Executor:** main
- [ ] 3. `docs/guide/running.md`: the three WP56 sections in the guide's voice, the cost a
  magnitude and the thread rule a rule (D4, D5). **Executor:** main
- [ ] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `docs/guide/python.md`, its `mkdocs.yml` entry, its guide-index row and `docs/index.md`'s
  *Script it from Python* row (D2); done also when every snippet has been run and recorded and
  every name checked against `nanopnp.PUBLIC`. **Executor:** main
- [ ] 6. `docs/guide/notebooks.md`, its `mkdocs.yml` entry and its guide-index row (D3); done also
  when each of the six links resolves. **Executor:** `general-purpose`, Sonnet
- [ ] 7. `docs/getting-started.md` and `docs/guide/{meshes,provenance}.md`: the help pointers, the
  causes of a run that does not reproduce, the naming consistent (D4). **Executor:** main
- [ ] 8. `examples/*/README.md` and `docs/examples/index.md`: prose, titles and index rows, no
  tagged block and no number touched (D1, D4). **Executor:** `general-purpose` on Sonnet
- [ ] 9. Compaction checkpoint. **Executor:** main
- [ ] 10. The release-scope prose at v0.5 (D6); a `REV-nn` row with its `review-items.md` section
  for anything unfixed; `CHANGELOG.md`'s `[Unreleased]` entry; `current.md`'s position line; done
  also when `duplicates.py` and `.claude/hooks/gate.sh run` pass. **Executor:** main

### Verification

No test is written or kept: the package changes prose alone (§7.1; §8.2.13 N1, N3).

| Check | Tier | Identifier | Oracle | Command |
|---|---|---|---|---|
| The site builds strictly | 1 | VER-45 | a broken link or anchor fails it | `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` |
| Every example's tagged commands still run unchanged | 2 | VER-46 | each exits `0`, or `4` in a refusal block | `.claude/hooks/gate.sh run`; `uv run pytest --nightly -m tier2` |
| No number, case file or tagged block moved | — | — | the diff | `git diff --name-only origin/main...HEAD`; `git diff origin/main...HEAD -- examples/ notebooks/ docs/user-testing/` |
| Every name, command and flag shown exists | — | — | `PUBLIC`, the parser | `uv run python -c "from nanopnp.core.public import PUBLIC; print(sorted(PUBLIC))"`; `uv run nanopnp --help` |

### Out of scope

| Deferred | Owner |
|---|---|
| The `[0.5.0]` changelog section with every break and its migration, `CITATION.cff`, the `released` row | WP59 (Z1) |
| Both logs set `closed`, every row terminal, the report's numbers and cost record re-run (REV-116) | WP59 |
| Rendering or exporting the notebooks, and any new figure | Z2 |
| A migration page | Z3 |
| Any `src/` change the pass would like, a `nanopnp env` alias cleanup | a later package, by a `REV-nn` |
| REV-121, stage 1's axis; REV-156, the solve's cost | Phases 5 and 6 (Z5, Z6) |

### Open questions

Neither blocks implementation.

1. **The banner.** `docs/overrides/main.html` and `docs/index.md` both say *pre-alpha*; this
   package corrects their scope and keeps the word. *Recommendation:* keep it until v0.7, nothing
   before it being compared against the paper.
2. **How wide the examples' revision reads.** D1 holds it to prose, titles and the index rows.
   *Recommendation:* enough; a narrative rewrite re-pins nothing but costs a careful reading of
   every tagged block.
