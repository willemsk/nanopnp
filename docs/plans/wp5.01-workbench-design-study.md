# WP5.01 — The workbench design study: GUI tools, the Qt shell critiqued, a design round, the areas drawn, the requirements written

**Status: in progress; items 1 to 9 done; next, the mockups of the areas.** Written 24 October 2026; grounded in the code at `e78b6aa`
(§8.2.15 Q1). Amended the same day for the author's rulings S21 to S24: the design round on the
workbench's organisation and look and feel, the GUI development tools, and the workbench's areas. Inherits the Phase 5
plan and §8.2.17 S1 to S24; runs in the second lane beside Phase 4 (S1, S15). By S23 this plan
exceeds §8.4.4's word caps; its six-decision cap holds.

The [Phase 5 plan](phase-5-workbench.md) owns the phase. `SPECIFICATION.md` governs; where this plan
and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** No program changes. The project first gains tools for GUI work: a command that
pictures every screen without a display, a reviewer that checks the pictures, and a private page
where you mark each one keep, drop or change. You judge today's program screen by screen. Then a
design conversation: three or four ways of organising the workbench, not only one tab per step, are
sketched side by side, and you are questioned until the organisation and the look and feel are
settled. The five areas you named, from the molecular viewer to the results analyser, are then
drawn as clickable mock screens in that design; a public design document and its requirements follow.

**Cost.** Two to three weeks, mostly waiting for you; about six sessions, including two or three
conversations of up to an hour.

**What could go wrong.** A screen could be missed: each is listed from the code and counted. The
sketches could favour one design: each draws the same job, with its weaknesses beside it. Mock
screens could promise a tool not yet built: each later tool carries a "later phase" banner. Phase 4
keeps priority: this work waits whenever Phase 4 needs the session.

**Your call.** Nothing now: each design question is put to you in the conversation, and the
colleague who tries the workbench is named before the phase closes.

## Execution brief

Scope: the Phase 5 plan's WP5.01 as amended (F5; S2 to S7, S11, S12, S17, S21, S22, S24), its open
decisions 3 and 4. Prose, mockups, the specification and tools under `.claude/` only: no `src/`,
`tests/`, case schema or public API (S1). Discharges no `VER-`/`VAL-`; restates IF-09, VER-43,
VER-44, VER-55, VER-60, CON-09's PySide6 clause, ADR-004's packaging NOTE, RSK-13, P3 and QR-10,
and adds requirements from FR-31 and QR-16 (F5). Amends §8.4.4, §8.4.5 and `CLAUDE.md` with the
tools (S22). Depends on nothing unmerged.

Implemented by a Sonnet 5.5 session at high effort; Opus only after Sonnet fails on an item
(§8.4.5). Items 7 and 8 are conversations with the author and need the author present; items 6 and
11 wait for the author's verdicts. The package is the tools' first user: every picture, review and
verdict after item 4 goes through `/np-gui`.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Today's shell: pictures, critique, capability list | Example 07's `2wcd.case.yaml` driven through `MainWindow` offscreen in three states (opened, after *Build charge*, after *Run*) and one refused field; every tab and sub-view of *Grounding D1* grabbed with `QWidget.grab()`, and each WebEngine view replaced by a screenshot of the HTML document the render child wrote. Rendered by `/np-gui render qt`, reviewed by `/np-gui review`, published for verdicts by `/np-gui publish`. The **Qt capability list** (one row per control or view that does something) is committed in `docs/design/workbench.md`, the list S13's gate checks before Qt leaves | One real case reaches all seven tabs; offscreen WebEngine draws nothing (WP16 D14), while the shell's own host page renders headless (*Grounding D1*). The gate's list must live in the repository, not on a private page |
| D2 | The design round on organisation and look and feel | Three steps, by `/np-gui grill`. **Diverge**: four low-fidelity, greyscale concept boards, each placing the author's areas (S24) and drawing the same two jobs through them (QR-10's guided run on 2WCD; a charge-level mutation compared with its parent) under one organising principle: C1 *model builder* (a case tree of stages, a settings pane, one graphics window, as in COMSOL); C2 *molecular workspace* (a central canvas always visible, docked tool panels, a command line, as in PyMOL or ChimeraX); C3 *project and runs* (a browser of structures, cases, runs and comparisons opening each item as a document, as in an IDE); C4 *guided routes* (one route per job, step by step, over any of the others). Each board lists its strengths and weaknesses per persona and job. **Grill**: the organisation agenda, then, after a style tile of three visual directions, the look-and-feel agenda (*Implementation details*), at most four questions per call, each with options, consequences and a recommendation first, every answer tested by walking a job through it. **Record**: each ruling in the author's words as a `WB-nn` row of the design document's decision log; the chosen direction's tokens as `docs/design/tokens.css` | S21: "not just stage by stage". Boards drawn without style keep the organisation judged apart from colour; one job across all boards makes them comparable; the grilling settles each point rather than leaving a mood |
| D3 | The areas, the mockups and the design document | The author's areas (S24): the **molecular viewer and editor**, the **geometry builder**, the **mesh builder**, the **physics assigner** and the **results analyser**, and any the round adds. Each area is a clickable plain-HTML page under `docs/design/mockups/` showing one working session in it, in the ruled organisation and with `tokens.css`, no framework, fixtures as inline data; v0.6's controls work, and each part of a later tool phase (the structural editor, the sketcher, the composer; *Grounding D3*) carries a "later phase" banner and no working control. One more page threads QR-10's guided run through the areas. One revision after the author's comments. `docs/design/workbench.md` is public, in the site's *Project* section (S24); `docs/design/{concepts,style,mockups,reviews}/` are excluded from the site. It settles Phase 5 open decision 4: the browser shell's pictures come from `plot/data.py`, whose duplicates in `gui/` retire with Qt | The author named the areas (S24); plain HTML presumes nothing of WP5.02's framework (S8); the banner keeps v0.6's scope visible (S7; RSK-15); F5; S2 to S7, S11, S12 |
| D4 | The GUI development tools | A skill `/np-gui <render \| review \| publish \| collect \| grill>` (`.claude/skills/np-gui/`, a router and one file per level); two scripts, `.claude/scripts/gui/shoot.cjs` (Node, Playwright) and `.claude/scripts/gui/capture_qt.py` (the Qt shell, removed with it); a read-only agent `.claude/agents/gui-reviewer.md` on Sonnet. `/np-implement` renders and reads each screen an item changes before committing it; `/np-ship` reviews and publishes the screens of a package that changes any, and collects the verdicts before the merge. WP5.02 adds the `shell` target (fixture states, S10) and the local live loop (S9). Specified in *Implementation details* | S22. Pictures, a check that reads them, and verdicts that reach the session without retyping are the loop every later GUI package repeats; built first, so this package uses them |
| D5 | Requirements into the specification | Each restated clause gets a `NOTE (the browser shell, v0.6)` paragraph after its table or section, holding the full new text; the old text keeps gating the Qt shell and the NOTE replaces it in the package that removes Qt. IF-09 joins the restated set: it names "a desktop graphical interface". New functional requirements are `FR-31` onward in §3's table, Release `v0.6` or the tool phase's name (`composer phase`, `structural-mutator phase`, `sketcher phase`); a quality ruling of the round (accessibility, responsiveness) is `QR-16` onward. Each has an Appendix A row `None yet; <owner>`. A `WB-nn` ruling that departs from S2's "distinct tabs for each part of the workflow" amends §8.1's Phase 5 row in the same commit (S21). No `VER-` is added (VER-77 is WP5.02's) | S17; F5; S3 to S5. A NOTE leaves v0.5's text intact whatever the merge order |
| D6 | The inherited rows | The design document proposes a ruling for each of REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114 and `MOD-09`, `MOD-13`'s command-line part and `MOD-18`. The author rules through `AskUserQuestion`; the round is written as `specification/history/18-…` (§8.2.18, letters from T) by `np-plan/rulings.md`, each row then `fixed`, `deferred` with an owner, or `wontfix` | Phase 5 open decision 3; §8.4.6 |

### Grounding

**D1.**

- `gui/app.py:MainWindow.__init__` adds seven tabs: Case, Geometry, Charge, Run, Convergence,
  Result, Fields. `build_charge` walks to `gui/charge.py:BUILD_UPTO` on the Geometry tab's control;
  `start_run` runs the saved case; `_show_result` fills Result and Fields once the run settles.
- `gui/widgets/geometry.py:GeometryWidget` has a stage list (`self._list`, a `QListWidget`) beside
  a `QStackedWidget` (`self._pictures`) holding a canvas and a `QWebEngineView` (the mesh), and the
  buttons *Load structure…*, *Build geometry*, *Cancel*, *Measure criteria*, *Seed from refusal*,
  *Delete vertex*, *Undo*, *Redo*, *Save edit* and a quantity combo. Its stages come from
  `gui/geometry.py:planned_stages`.
- `gui/widgets/charge.py:PANES` is *Protonation*, *Charge map*, *Deployed field*, *Conservation*,
  tabs of `self._panes`; the deployed field is a `QWebEngineView`. `widgets/viewer.py:ViewerWidget`
  (Fields) is a field combo over a `QWebEngineView`.
- `docs/scripts/capture_gui.py` grabs Case, Run and Convergence of example 01 with
  `window.grab()`, under `QT_QPA_PLATFORM=offscreen`, waiting on `window._run.settled` through a
  `QEventLoop`; its docstring records that offscreen WebEngine draws nothing to grab. It stays: it
  serves the user guide until documentation increment 5.
- In this container `from PySide6 import QtWidgets` fails: `libEGL.so.1` is missing. The shim of
  `knowledge/07-software-stack/05-gui-and-packaging.md` (*A missing libEGL.so.1 can be shimmed…*)
  now fails at `/opt/pw-browsers/chromium-1243/chrome-linux64/` with `undefined symbol:
  eglQueryString`. `apt-get install -y --no-install-recommends libegl1 libgl1 libxkbcommon0 libnss3
  libxcomposite1 libxdamage1 libxrandr2 libxtst6 libxkbfile1 libasound2t64` makes `QtWidgets` import
  and a `QWebEngineView` construct offscreen (verified 24 October 2026).
- `gui/render.py:_write_scene` writes `<run>/viewer/<stem>.json` and `<stem>.html`, the page from
  `host_document(scene, renderer=RENDERER_SOURCE, title=…)`, which loads the shipped
  `gui/assets/webgui/webgui.js` by `file://` URI. `render_mesh`, `render` and `render_charge` are
  its three writers (mesh, field, charge or χ).
- Example 07: `python ../06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz
  2wcd-prepared.pdb`, then `2wcd.case.yaml`; about five minutes, the `structure` extra.
  `validation/examples.py:copy_example` copies an example's inputs into a scratch directory.

**D2.**

- `AskUserQuestion` takes one to four questions per call, two to four options each, and a
  recommended option first; the author can always answer "Other" in free text (`np-plan/rulings.md`
  applies the same form to rulings).
- No live link exists today: the Charge tab's protonation table and charge map do not select each
  other; no field probe or cut is in `gui/`; `post/export.py:sample_at` samples a field at points.
- The charge map already uses a diverging table centred at zero (VER-60).

**D3.**

- What each area can draw on at v0.6, by case section (`io/case.py`): the molecular viewer,
  `Structure` (source, `Frames`, `Ensemble`, `SymmetrySpec`) and stage 7's protonation and PQR
  (`Charge`, `inputs.pqr`), editing charges only (S4); the geometry builder, `Geometry`
  (`MembraneSpec`, `ReservoirSpec`, `AnalyteSpec`), `DensitySpec`, `ContourSpec` and `inputs.profile`;
  the mesh builder, `MeshSpec` (`backend`, `size_scale`, …), `ElementsSpec` and stage 6's quality
  report; the physics assigner, `PhysicsSpec`, `ElectrolyteSpec` with `CorrectionsSpec`,
  `BoundaryConditions` and `WallSpec`, choosing among registered models only (S3); the results
  analyser, the run record, `outputs`, the fields and sweeps. Later phases: side-chain replacement
  (S4), the (r, z) sketcher (S5), model composition (S3).
- `mesh/primitives.py` has three parametric geometries; `inputs.profile` and `inputs.pqr` take a
  hand-edited contour and PQR; `physics/models.py` registers six models. No residue mutation and no
  free-form (r, z) domain exist (Phase 5 plan, *Context*).
- `mkdocs.yml` sets `validation.nav.omitted_files: warn`, so under `--strict` a Markdown page outside
  `nav` fails the build (`knowledge/07-software-stack/13-…`). `exclude_docs` lists `plans/`,
  `code_reviews/`, `superpowers/`, `scripts/`, `overrides/`.
- `plot/data.py` has `density_section`, `contour_polygon_m`, `mesh_of`, `protonation_charges`,
  `charge_grids`, `newton_history`, `solution_fields`, `sweep_curves`; `gui/geometry.py` keeps its
  own `density_section`, `reduced_image`, `ImageModel`. No `gui/` module imports `nanopnp.plot`.

**D4.**

- Playwright 1.63.0 is installed for Node 22 globally (`/opt/node22/lib/node_modules/playwright`),
  found through `NODE_PATH=/usr/local/lib/node_modules_global`. `NODE_PATH` serves `require` only,
  so the script is CommonJS (`.cjs`). It is not in the `uv` environment. Launched with
  `--enable-unsafe-swiftshader`, its Chromium renders a `host_document` page of a unit-square scene:
  WebGL2, colour bar, mesh (verified 24 October 2026). No accessibility library (`axe-core`) is
  installed.
- Skills are `.claude/skills/<name>/SKILL.md` with front matter `name`, `description`,
  `argument-hint`; a router reads `${CLAUDE_SKILL_DIR}/<level>.md` and names the file "beside this
  one" as well, for `.agents/skills.json`, which points Antigravity at `.claude/skills` and does not
  substitute `${…}` (`np-plan/SKILL.md`; WP53 D1).
- Agents are `.claude/agents/<name>.md` with front matter `name`, `description`, `model`, `tools`
  and optionally `effort`, `omitClaudeMd`; `physics-reviewer` (Opus, Read, Grep, Glob, high effort)
  is the read-only model. `Read` returns a PNG as an image.
- The Artifact tool publishes an HTML page with `files` (supporting files such as `tokens.css`) and
  `capabilities`; a shared store needs the `db` capability, declared after loading the
  `artifact-capabilities` skill; `ArtifactData` reads it as the author. Pages are private by default
  (S9). A page is written after loading the `artifact-design` skill.
- §8.4.4's first bullet lists three workflow commands with no aliases; §8.4.5 says two agents are
  kept. `CLAUDE.md`'s *Models* paragraph names "the `physics-reviewer` and `ci-log-classifier`
  sub-agents". `np-ship/wp.md` §4 runs the test-scope read and `physics-reviewer` before the review
  skill; `np-implement/wp.md` *How the work lands* commits one item at a time.
- `.github/scripts/prose-only.sh` treats only `*.md` as prose, so the scripts, the HTML and
  `mkdocs.yml` run the full gate; ruff checks `.claude/scripts/**/*.py`, mypy only `src/`, and
  `.claude/rules/python.md` covers `.claude/scripts/**/*.py`.

**D5.**

- §3's functional table has a Release column (`specification/03-requirements.md`, FR-01 to
  FR-30); the interface, quality and constraint tables do not. P3 is row 3 of the persona table in
  `specification/02-product-overview.md`.
- Highest on `main`: FR-30, QR-15, CON-14, IF-09, VER-76, RSK-19. CON-09's text already says its
  PySide6 clause lapses with the Qt shell.
- NOTE paragraphs follow tables elsewhere (`NOTE (FR-19, FR-20):` after §8.1's GUI table).
- §8.1's GUI-increment table, row 5, says "a tab for each part of the workflow".

**D6.**

- The fourteen REV rows are `deferred` in `docs/project/review-findings.md`, each with a section in
  `review-items.md`; `MOD-09`, `-13`, `-18` are in `docs/project/modularity-findings.md`. The highest
  history record is `17-…` (§8.2.17, letters to S23).

**Records.**

- `CHANGELOG.md` has no `## [Unreleased]` section today; its link footer has an `[Unreleased]`
  link. S19 puts this package's entry there.

### Implementation details

`<s>` is the scratchpad; `<r>` a render directory `<s>/gui-render/<target>-<short sha>/`.

**Item 1, `shoot.cjs`.** `node .claude/scripts/gui/shoot.cjs <manifest.json> <out-dir>`. The
manifest is a JSON list of `{id, url, viewport: [w, h], scheme: "light"|"dark", wait_ms, expand}`;
`url` is a `file://` path or an `http://` address. `expand`, if set, is a CSS selector: the page is
shot once per matching element's `data-screen` value, after setting `location.hash` to it, with id
`<id>-<screen>`. Launch Chromium with `--enable-unsafe-swiftshader`, `colorScheme` from `scheme`.
For each shot record console errors and page errors, and run an in-page check: every visible
element with own text whose contrast against its first opaque ancestor background is below 4.5:1
(3:1 at 24 px, or 18.66 px bold), and every visible `a`, `button`, `input`, `select`, `[role=button]`
smaller than 24 × 24 CSS px (WCAG 2.2 1.4.3, 2.5.8), each with a selector and the measured value.
Write `<out>/<id>.png` and `<out>/index.json` (`{id, file, url, viewport, scheme, console,
page_errors, contrast, targets}` per shot). Exit 0, or 2 if a page failed to load. Self-check: the
unit-square `host_document` page shoots with no page error.

**Item 1, `capture_qt.py`.** `uv run python .claude/scripts/gui/capture_qt.py <out-dir>`, following
`.claude/rules/python.md` (logging, `pathlib`, type hints). It sets `QT_QPA_PLATFORM=offscreen` and
`QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --no-sandbox"` before importing PySide6, copies example
07 into a scratch directory with `copy_example`, runs `prepare.py`, and opens `2wcd.case.yaml` in
`MainWindow` with a scratch store, sized 1280 × 860. State `opened`: each tab. State `refused`: a
bounded field of the Case tab set out of range, its refusal shown. State `built`: `build_charge`,
the Qt event loop run until the Charge tab's status settles (timeout 900 s), then each row of the
Geometry stage list selected and grabbed, and each Charge pane. State `run`: `start_run`, wait for
`settled` (timeout 900 s), then Run, Convergence, Result and Fields. Grabs are
`<state>-<tab>[-<view>].png`. It then writes `<out>/webgui-manifest.json`, one entry per
`viewer/*.html` under the scratch directory, for `shoot.cjs`, and `<out>/qt-index.json`, one entry
per grab, listing which grabs show an empty WebEngine view and the HTML shot that stands for it.

**Item 2, the skill.** `SKILL.md`: name `np-gui`; description "Render, review and publish GUI
screens and mockups for the author's verdicts, collect them, or run a design round with the author.
Use when a change touches a screen, a mockup or the workbench design, or on /np-gui."; argument hint
`<render | review | publish | collect | grill> [target|topic|url]`. Usage line on a missing or unknown
level, as `np-plan`'s router. Levels:

- `render.md`: targets `qt` (the apt list of *Grounding D1*, `capture_qt.py`, then `shoot.cjs` on its
  WebGL manifest), `mockups` (every `docs/design/{concepts,style,mockups}/*.html`, at 1440 × 900 and
  1280 × 800, light and dark, `expand: "[data-screen]"`), and `shell`, which says "added by
  WP5.02" until then. Output `<r>`. Then read the PNGs the change touched, and report console
  errors, page errors and failed checks; a page error stops the caller.
- `review.md`: give the `gui-reviewer` agent `<r>`, the design document, the job or screens in
  question, and the diff if any; write its findings to `<r>/review.md`; the caller decides each.
- `publish.md`: load `artifact-design` and `artifact-capabilities`; one gallery page per topic, a
  card per shot (picture, id, state, two lines on what it shows, the reviewer's findings for it), a
  verdict control (`keep`, `drop`, `change`; for a mockup `fine`, `change`) and a note, saved in a
  `verdicts` collection keyed by shot id; republish to the same URL for a new round. Print the URL;
  `/np-ship` puts it in the PR body.
- `collect.md`: read `verdicts` with `ArtifactData`; write `docs/design/reviews/<yyyy-mm-dd>-<topic>.md`
  as `| Shot | Verdict | Note | Reviewer finding | Disposition |`. A `drop` or `change` is acted on in
  the package, or becomes a `REV-nn` row (§8.4.6).
- `grill.md`: the method of D2 and its agendas, below. Prepare: read the inputs (verdicts, areas, P1
  to P3, S2, S6, the design document so far) and write the assumptions they leave. Diverge: publish
  the boards. Grill: one agenda point at a time, at most four questions per call, recommendation
  first; challenge an answer that contradicts an earlier one or a clause; walk one job through each
  answer ("where does the user click to change the salt, and what redraws?"). Stop when every point
  has a ruling or an explicit deferral with its owner. Record: `WB-nn` rows
  `| # | Question | Ruling (author's words) | Consequence |`; play the summary back and ask for its
  confirmation. A ruling that changes a clause amends it (D5).

**The organisation agenda.** (1) The organising principle, primary and secondary: stage, object,
project, job, or a hybrid of the boards; how the author's areas (S24) sit in it. (2) What is always on screen: the pore picture, the case
tree, run status, the log, provenance. (3) One case open at a time or several, and how two are
compared. (4) Where the live views live: one central canvas switching layers (structure, density,
contour, mesh, charge, fields) or a canvas per tool; how a selection travels between linked views
(S6). (5) Tools as docked panels, modal editors or tabs. (6) Expert and guided use: one interface with
a guided overlay (QR-10), or two modes; how defaults are shown. (7) Commands: menus, toolbar, a
command palette, the keyboard; whether P1 gets a Python console over the public API, which holds no
physics (S3). (8) Runs and the store: how runs, cached stages, sweeps and results are browsed; what
*Run* means when stages are cached. (9) Refusals: where a refusal shows, naming its rule. (10) Switches away from the validated default (FR-25): how they stay visible. (11) Layout:
fixed or arranged by the user, saved with the project (S11).

**The look-and-feel agenda**, after the style tile (three directions: *instrument*, dense and dark
as an engineering suite; *notebook*, light and explanatory; *molecular*, a dark canvas with light
panels; each with a token set, a type scale and samples: a number with its unit, a stage status, a
refusal, a colour bar). (1) References the author likes or dislikes, and why. (2) Density. (3) Theme
and default. (4) Accent and semantic colours; field colour maps, perceptually uniform and readable
with colour-blindness, diverging about zero for charge. (5) Typography; how numbers and units read.
(6) Icons with text, or text only. (7) Motion. (8) The accessibility target (WCAG 2.2 AA proposed)
and keyboard operation. (9) The tone of text and the glossary for P3. Tokens: CSS custom properties
on `:root`, redefined under `prefers-color-scheme: dark`, in `docs/design/tokens.css`.

**The agent, `gui-reviewer.md`.** Model `sonnet`, tools `Read, Grep, Glob`, effort `high`. It is
given a render directory, the design document and the screens in question. It reads each PNG and
`index.json`, and the mockup HTML where present. It reports findings, each with the shot id, the
region, a severity (`blocking`, `major`, `minor`), the rule broken and a proposed change, from: the
design document's organisation, decision log, tokens and glossary; the job's route (can it be
finished from these screens?); Nielsen's ten usability heuristics; WCAG 2.2 AA, with the measured
contrast and targets of `index.json` taken as evidence; S6's links where a screen should carry one;
VER-60 and RSK-15 (a number shown that no artefact supplies, or a control for a capability Tiers 1
and 2 do not verify without its "later phase" banner); CON-09's renderer clause. It separates a
confirmed finding from a doubt, says what it could not check, never edits a file and never softens a
finding.

**Item 2, the clauses and hooks.** §8.4.4, after the first bullet: "Beside them, `/np-gui <render |
review | publish | collect | grill>` renders screens and mockups headless, has them reviewed,
publishes them for the author's verdicts, collects the verdicts and runs a design round. A package
that changes a screen uses it. (§8.2.17 S21, S22; `.claude/skills/np-gui/`)". §8.4.5: "Three agents
are kept: the physics reviewer and the GUI reviewer, both read-only, and the CI-log classifier."
`CLAUDE.md`'s *Models*: the three agents, and a sentence after the workflow table naming `/np-gui`.
`np-implement/wp.md`, *How the work lands*: "An item that changes a screen (`src/nanopnp/gui/`, the
front end, `docs/design/`) runs `/np-gui render <target>` and reads each changed screen before its
commit; a page error or a failed check stops the item." `np-ship/wp.md` §4, before the review skill:
"A PR that changes a screen runs `/np-gui review` and `/np-gui publish`, links the gallery under
**Verification**, and runs `/np-gui collect` before the merge."

**Item 3.** In `05-gui-and-packaging.md`, mark the shim section superseded at chromium-1243, with the
symbol error, and add a section: the apt list makes PySide6 and `QWebEngineView` work offscreen; Node
Playwright, CommonJS through `NODE_PATH`, renders a `host_document` page headless with SwiftShader.
Mark each `[verified]` with a footnote to this plan; add a `knowledge/log.md` line.

**Item 7, the concept boards.** `docs/design/concepts/c<n>-<name>.html`, one per concept, and
`index.html` beside them: greyscale, system font, boxes and labels only, each job's screens as
`<section data-screen>`; the strengths and weaknesses as a side note per persona. Published as one
gallery by `/np-gui publish`, with the verdict `prefer`, `borrow`, `reject`.

**Item 10, the mockups.** One file per area, `docs/design/mockups/<nn>-<area>.html`
(`01-molecular`, `02-geometry`, `03-mesh`, `04-physics`, `05-results`, then any the round adds),
`00-guided-route.html` and `index.html`; `<link rel="stylesheet" href="../tokens.css">`; screens as `<section data-screen>`,
moved between by *next* and *back* links to `#<id>`; the frame (navigation, persistent views) as the
round ruled it. Published with `files` carrying `tokens.css`. Add `design/concepts/`,
`design/style/`, `design/mockups/` and `design/reviews/` to `exclude_docs`; the design document names
them by path in backticks, not by link.

**Item 12, `workbench.md`'s sections**, in order: *Purpose and users* (P1 to P3); *Today's shell*
(the capability list and the verdicts); *The areas* (S24); *Organisation* (the principle, the frame, what
is always on screen); *Look and feel* (the direction, the tokens, the accessibility target);
*Tabs or areas*; *Tools* (each with its live view, S6); *The four live links*; *The project folder*
(layout, the project file's fields, the export; S11); *Install and start* (S12); *The guided route*
(QR-10); *Later tools* (the composer with S3's room for equations, the structural mutator, the
sketcher); *The shell's reading of artefacts* (D3); *Restated clauses*; *Inherited rows* (D6);
*Decision log* (`WB-nn`); *Glossary*. Add `Workbench design: design/workbench.md` to *Project* in
`mkdocs.yml`.

**Item 13.** NOTE form: `NOTE (the browser shell, v0.6). When the package that removes the Qt shell
lands, <ID> reads: "<text>". Until then the text above gates the Qt shell (§8.2.17 S17).` FR row
form: `| **FR-31** | SHALL … | v0.6 |`; QR row form: `| **QR-16** | … | <class> |`.

**Item 15.** `CHANGELOG.md`: add `## [Unreleased]` above `## [0.5.0-alpha.19]` with `WP5.01: …`
and an *Added* list (the tools, the design document); `current.md`: only the Phase 5 line.

### Work items

- [x] 147baa2 1. `.claude/scripts/gui/shoot.cjs` and `.claude/scripts/gui/capture_qt.py` (D1, D4); done when
  the self-check passes and `capture_qt.py` writes every grab of *Grounding D1*'s list, or names the
  one it could not reach. **Executor:** main.

  > **Outcome — 22 grabs, none missed; three HTML stand-ins.** Seven tabs opened, one refusal, six
  > Geometry rows and four Charge panes built, four tabs after the run; about eight minutes. The
  > case's one `bounded` field, `charge.ph`, is a spin box clamped to its range, so the refusal is
  > `numerics.mesh.size_scale = -2`, refused at commit; a negative concentration is accepted at
  > commit and refused only at the build. Offscreen, the shell replaces each web view with its own
  > "did not draw" diagnostic (`getExtension` of a null WebGL context), so a grab maps to its HTML
  > shot by the document the view loaded.
- [x] a543bb2 2. `.claude/skills/np-gui/` (router and five levels), `.claude/agents/gui-reviewer.md`, §8.4.4,
  §8.4.5, `CLAUDE.md`, `np-implement/wp.md`, `np-ship/wp.md` (D4; S22); done when the code and
  review say so. **Executor:** main.
- [x] a9ca3d3 3. `knowledge/07-software-stack/05-gui-and-packaging.md`, `knowledge/log.md` (D1, D4); done
  when the code and review say so. **Executor:** `general-purpose` on Haiku.
- [x] f31cd3c 4. Compaction checkpoint: the tools exist. **Executor:** main.
- [x] a610700 5. `/np-gui render qt`, `review`, `publish`: the critique; the capability list in
  `docs/design/workbench.md`'s *Today's shell* (D1); done when published, and the grab count in
  `qt-index.json` equals the views of *Grounding D1*. **Executor:** main.

  > **Outcome — 41 capabilities, 50 findings, the gallery published.** The render at `f31cd3c` took
  > 22 grabs and 3 HTML stand-ins, none missed, none with a page error; after the run it takes the
  > four tabs a run fills, as *Implementation details* says, not all seven. The capability list
  > holds Q01 to Q41. The reviewer's two blocking findings are the Result tab's float wrapper,
  > a v0.5 defect recorded as REV-134, and the field view's opening camera. `workbench.md` joins
  > *Project* in `mkdocs.yml` now, not at item 12: under `--strict` a page outside `nav` fails.
- [x] efdf5b4 6. Wait checkpoint: the verdicts. **Executor:** main.
- [x] 65d1d7a 7. `/np-gui collect`; the concept boards, rendered, reviewed and published; `/np-gui grill
  organisation` with the author; the `WB-nn` rows (D2); done when every organisation agenda point has
  a ruling or a deferral. **Executor:** main.

  > **Outcome — sixteen rulings, WB-01 to WB-16; suites in a project.** The author marked all 22 Qt
  > screens (20 *change*, 2 *keep*, none dropped; `docs/design/reviews/2026-10-25-qt-shell.md`) and
  > ruled the organisation in conversation rather than marking the four boards: three suites,
  > *Molecular*, *Continuum* and *Analysis*, in a project with a run queue, and a library of molecular
  > and continuum models paired in studies (WB-11, WB-16). WB-14 brings structure preparation into
  > Phase 5, library first, against S4's consequence; with WB-02 it amends §8.1's Phase 5 rows. The
  > board review's 19 findings, none blocking, go to the mockups or to REV-136 (the library
  > capabilities the rulings need) and REV-137 (the renderer); the Qt verdicts raise REV-135. All four
  > `design/` folders join `exclude_docs` now, not at item 10: under `--strict` the review records
  > would otherwise fail the build.
- [x] 74d3062 8. The style tile in `docs/design/style/`; `/np-gui grill look-and-feel`; `docs/design/tokens.css`;
  the `WB-nn` rows (D2); done when every look-and-feel agenda point has a ruling or a deferral.
  **Executor:** main.

  > **Outcome — twelve rulings, WB-17 to WB-28; `tokens.css`.** The style tile drew three directions,
  > light and dark; the author ruled each of the nine points in conversation and marked no direction:
  > each suite borrows its reference tool's idiom under one harmonised token set, medium density with
  > a compact option, both themes following the system, user-chosen colour maps with viridis and a
  > zero-centred diverging map as defaults, and WCAG 2.2 AA including non-text contrast (WB-24). The
  > tile's review (16 findings, none blocking) shaped the tokens: a control edge at 3:1, a focus ring,
  > a changed-from-default colour apart from the accent, outlined colour bars; the rest go to the
  > mockups, and the checker's missing non-text measure is REV-138. The plan's agenda cited VER-67 for
  > refusals; VER-67 is withdrawn, so point 9 and WB-12 name no identifier.
- [x] 9. Compaction checkpoint: the round is recorded. **Executor:** main.
- [ ] 10. The mockups of the areas and the guided route in `docs/design/mockups/`, rendered, reviewed and published;
  `mkdocs.yml`'s `exclude_docs` (D3); done when no blocking reviewer finding is open and the strict
  build passes. **Executor:** main.
- [ ] 11. Wait checkpoint: the comments on the mockups. **Executor:** main.
- [ ] 12. `/np-gui collect`; one revision of the mockups; `docs/design/workbench.md` complete;
  `mkdocs.yml`'s nav (D3); done when the strict build passes. **Executor:** main.
- [ ] 13. The specification (D5): NOTEs in `specification/02-product-overview.md`,
  `03-requirements.md`, `05-software-design/06-architecture-decisions.md`,
  `07-verification/02-tier-1.md`, `09-risks.md`; FR and QR rows; `a-traceability-matrix.md`; §8.1
  where a `WB-nn` ruling moves it; done when `uv run .claude/scripts/duplicates.py` and the strict
  build pass. **Executor:** main.
- [ ] 14. The inherited rows (D6): the round, `specification/history/18-…`, its index lines, the
  REV and MOD rows; done when the code and review say so. **Executor:** main.
- [ ] 15. `CHANGELOG.md` and `docs/plans/current.md` (S19); done when the code and review say so.
  **Executor:** `general-purpose` on Haiku.

### Verification

No test is kept: the package changes no program code, and the tools are outside the test scope
(§8.2.13 N1). The checks:

| Check | Oracle | Command |
|---|---|---|
| D1's "every tab and sub-view" | `qt-index.json`'s grabs against *Grounding D1*: the seven tabs in `opened` and `run`, each Geometry stage row and each Charge pane in `built`, the refusal, and an HTML shot for each empty WebEngine view (Geometry mesh, Charge deployed field, Fields) | `/np-gui render qt` |
| The shooter loads a WebGL page | The unit-square `host_document` page: no page error, `index.json` written | `node .claude/scripts/gui/shoot.cjs` |
| D2's "every agenda point" | Each of the eleven and nine points has a `WB-nn` row or a deferral with its owner | Review |
| Mockups | No page error; no blocking `gui-reviewer` finding open; contrast and target checks recorded | `/np-gui render mockups`, `/np-gui review` |
| Documents | The strict documentation build (VER-45), `uv run .claude/scripts/duplicates.py`, the push gate | as the Phase 5 plan's *Verification* |

Review checks D5's restatements against the clauses they replace, that each new FR and QR row is
in Appendix A, and that S22's clause edits match *Implementation details*.

### Out of scope

- The framework, the server library and ADR-004's choice: WP5.02 (S8).
- The `shell` render target, fixture states and the local live loop: WP5.02 (S9, S10).
- The project file's schema identifier and code: the shell packages (G6).
- Retiring the guide's Qt pictures and `docs/scripts/capture_gui.py`: documentation increment 5.

### Open questions

1. Answered 24 October 2026 (S24): the areas; the design document public; the colleague later, by
   the close (Phase 5 plan, *What the author supplies*).
2. If WP54 merges first with new FR or QR rows, or a history record 18, `/np-ship` renumbers this
   package's (§8.4.4).
