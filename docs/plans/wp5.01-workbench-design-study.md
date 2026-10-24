# WP5.01 — The workbench design study: the Qt shell critiqued, the jobs drawn, the requirements written

**Status: planned, not started.** Written 24 October 2026; grounded in the code at `e78b6aa`
(§8.2.15 Q1). Inherits the Phase 5 plan and §8.2.17 S1 to S20; runs in the second lane beside
Phase 4 (S1, S15).

The [Phase 5 plan](phase-5-workbench.md) owns the phase. `SPECIFICATION.md` governs; where this plan
and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** Nothing a user runs. You see every screen of today's desktop program as pictures
on a private web page and mark each one keep, drop or change. Your three to five everyday jobs are
then drawn as clickable mock screens of the new workbench, which you try and comment on. From your
verdicts comes one design document for the whole workbench, and the requirements it settles enter
the specification, marked for the release that builds them, so that nothing the current release
promises changes before that release ships.

**Cost.** One to two weeks, mostly waiting for your comments; about four working sessions.

**What could go wrong.** The pictures could miss a screen: each tab and sub-view is listed from the
code, and a missing one is named. The mock screens could promise a tool the program cannot yet
support: each later tool is marked as its own later phase. Design work could pull effort from
Phase 4: it changes no code and waits whenever Phase 4 needs the session.

**Your call.**
1. Which three to five jobs should the mock screens show? *Recommendation:* name them when the
   pictures arrive; without them the study drafts five and asks.
2. Who is the colleague who will try the workbench at the end? *Recommendation:* name them now, so
   the final trial can be booked.
3. Should the design document be public on the documentation site? *Recommendation:* yes; it is the
   project's statement of intent and costs nothing to show.

## Execution brief

Scope: the Phase 5 plan's WP5.01 (F5; S2 to S7, S11, S12, S17), its open decisions 3 and 4.
Prose, mock-up pages and the specification only: no `src/`, `tests/`, case schema or public API
(S1). Discharges no `VER-`/`VAL-`; restates IF-09, VER-43, VER-44, VER-55, VER-60, CON-09's PySide6
clause, ADR-004's packaging NOTE, RSK-13, P3 and QR-10, and adds functional requirements from FR-31
(F5). Depends on nothing unmerged. Implemented by a Sonnet 5.5 session at high effort; Opus only
after Sonnet fails on an item (§8.4.5). The author's comments gate items 4 and 6.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Picturing today's shell | Example 07's `2wcd.case.yaml`, driven through `MainWindow` offscreen, in three states: opened, after *Build charge*, after *Run*; plus one refused field. Every tab and sub-view of *Grounding D1* is grabbed with `QWidget.grab()`; each WebEngine view is replaced by a screenshot of the HTML document the render child wrote, taken by Node Playwright. The scripts stay in the scratchpad, uncommitted; the design document records the commit they ran at | One real case reaches all seven tabs; offscreen WebEngine draws nothing (WP16 D14), and the shell's own host page renders headless (*Grounding D1*). The Qt shell leaves in Phase 5, so a capture tool would be dead code |
| D2 | The critique and the capability list | One private Artifact page: each screen with its picture, what it does, and a keep, drop or change verdict with a note, saved through the page's shared store and read back with `ArtifactData`. The **Qt capability list** (one row per control and view that does something) is committed as a section of the design document, the list S13's gate checks before Qt leaves | Verdicts must reach the session without retyping (S9); the gate's list must live in the repository, not on a private page |
| D3 | The jobs and the mockups | The author's three to five jobs; without them by item 4, five drafted from P1 to P3 (QR-10's guided run, a salt and voltage sweep, a charge-level mutation, a hand-edited profile, two runs compared) and confirmed. Each job is a clickable plain HTML page, no framework, fixtures as inline data, under `docs/design/mockups/`, published together as one Artifact. A screen of a later tool phase carries a "later phase" banner and no working control | Plain HTML presumes nothing of WP5.02's framework spike (S8); the banner keeps v0.6's scope visible (S7; RSK-15) |
| D4 | The design document | `docs/design/workbench.md`, in the site's *Project* section; the mockups excluded from the site. Sections in *Implementation details*. It settles P3's open question for the shell: the browser shell's pictures come from `plot/data.py`, whose duplicates in `gui/` retire with Qt | F5; S2 to S7, S11, S12; Phase 5 open decision 4 |
| D5 | Requirements into the specification | Each restated clause gets a `NOTE (the browser shell, v0.6)` paragraph after its table or section, holding the full new text; the old text keeps gating the Qt shell and the NOTE replaces it in the package that removes Qt. IF-09 joins the restated set: it names "a desktop graphical interface". New requirements are `FR-31` onward in §3's functional table, Release `v0.6` or the tool phase's name (`composer phase`, `structural-mutator phase`, `sketcher phase`), each with an Appendix A row `None yet; <owner>`. No `VER-` is added (VER-77 is WP5.02's) | S17; F5; S3 to S5. A NOTE leaves v0.5's text intact whatever the merge order |
| D6 | The inherited rows | The design document proposes a ruling for each of REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114 and `MOD-09`, `MOD-13`'s command-line part and `MOD-18`. The author rules through `AskUserQuestion`; the round is written as `specification/history/18-…` (§8.2.18, letters from T) by `np-plan/rulings.md`, each row then `fixed`, `deferred` with an owner, or `wontfix` | Phase 5 open decision 3; §8.4.6 |

### Grounding

**D1.**

- `gui/app.py:MainWindow.__init__` adds seven tabs: Case, Geometry, Charge, Run, Convergence,
  Result, Fields. `build_charge` walks to `charge.BUILD_UPTO` on the Geometry tab's control;
  `start_run` runs the saved case; `_show_result` fills Result and Fields once the run settles.
- `gui/widgets/geometry.py:GeometryWidget` has a stage list (`QListWidget`) beside a
  `QStackedWidget` holding a canvas and a `QWebEngineView` (the mesh), and the buttons *Load
  structure…*, *Build geometry*, *Cancel*, *Measure criteria*, *Seed from refusal*, *Delete vertex*,
  *Undo*, *Redo*, *Save edit* and a quantity combo. Its stages come from
  `gui/geometry.py:planned_stages`.
- `gui/widgets/charge.py:PANES` is *Protonation*, *Charge map*, *Deployed field*, *Conservation*;
  the deployed field is a `QWebEngineView`. `widgets/viewer.py:ViewerWidget` (Fields) is a field
  combo over a `QWebEngineView`.
- `docs/scripts/capture_gui.py` grabs Case, Run and Convergence of example 01 with
  `window.grab()`, under `QT_QPA_PLATFORM=offscreen`; its docstring records that offscreen WebEngine
  draws nothing to grab. It reaches private members (`window._run.settled`).
- In this container `from PySide6 import QtWidgets` fails: `libEGL.so.1` is missing. The shim of
  `knowledge/07-software-stack/05-gui-and-packaging.md` (*A missing libEGL.so.1 can be shimmed…*)
  now fails at `/opt/pw-browsers/chromium-1243/chrome-linux64/` with `undefined symbol:
  eglQueryString`. `apt-get install libegl1 libgl1 libxkbcommon0 libnss3 libxcomposite1 libxdamage1
  libxrandr2 libxtst6 libxkbfile1 libasound2t64` makes `QtWidgets` import and a `QWebEngineView`
  construct offscreen (verified 24 October 2026).
- `gui/render.py:_write_scene` writes `<run>/viewer/<stem>.json` and `<stem>.html`, the page from
  `host_document(scene, renderer=RENDERER_SOURCE, title=…)`, which loads the shipped
  `gui/assets/webgui/webgui.js` by `file://` URI. `render_mesh`, `render` and `render_charge` are
  its three writers (mesh, field, charge or χ).
- Playwright is not in the `uv` environment; Node's `require('playwright')` is. Launched with
  `--enable-unsafe-swiftshader`, its Chromium renders a `host_document` page of a unit-square
  scene: WebGL2, colour bar, mesh (verified 24 October 2026).
- Example 07: `python ../06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz
  2wcd-prepared.pdb`, then `2wcd.case.yaml`; about five minutes, the `structure` extra.

**D2.**

- The Artifact tool's shared store needs the `db` capability, declared on publish after loading
  the `artifact-capabilities` skill; `ArtifactData` reads it as the author. Artifact pages are
  private by default (S9).

**D3.**

- `mesh/primitives.py` has three parametric geometries; `inputs.profile` and `inputs.pqr` take a
  hand-edited contour and PQR; `physics/models.py` registers six models. No residue mutation and no
  free-form (r, z) domain exist (Phase 5 plan, *Context*).
- No live link exists today: the Charge tab's protonation table and charge map do not select each
  other; no field probe or cut is in `gui/`; `post/export.py:sample_at` samples a field at points.

**D4.**

- `mkdocs.yml` sets `validation.nav.omitted_files: warn`, so under `--strict` a page outside `nav`
  fails the build (`knowledge/07-software-stack/13-…`). `exclude_docs` already lists `plans/`,
  `code_reviews/`, `superpowers/`, `scripts/`, `overrides/`.
- `plot/data.py` has `density_section`, `contour_polygon_m`, `mesh_of`, `protonation_charges`,
  `charge_grids`, `newton_history`, `solution_fields`, `sweep_curves`; `gui/geometry.py` keeps its
  own `density_section`, `reduced_image`, `ImageModel`. No `gui/` module imports `nanopnp.plot`.

**D5.**

- §3's functional table has a Release column (`specification/03-requirements.md`, FR-01 to
  FR-30); the interface, quality and constraint tables do not. P3 is row 3 of the persona table in
  `specification/02-product-overview.md`.
- Highest on `main`: FR-30, QR-15, CON-14, IF-09, VER-76, RSK-19. CON-09's text already says its
  PySide6 clause lapses with the Qt shell.
- NOTE paragraphs follow tables elsewhere (`NOTE (FR-19, FR-20):` after §8.1's GUI table).

**D6.**

- The fourteen REV rows are `deferred` in `docs/project/review-findings.md`, each with a section in
  `review-items.md`; `MOD-09`, `-13`, `-18` are in `docs/project/modularity-findings.md`. The highest
  history record is `17-…` (§8.2.17, letters to S20).

**Records.**

- `.github/scripts/prose-only.sh` treats only `*.md` as prose: the mockups' HTML and `mkdocs.yml`
  run the full gate.
- `CHANGELOG.md` has no `## [Unreleased]` section today; S19 puts this package's entry there.

### Implementation details

**Item 1.** `<s>` is the scratchpad. Install item D1's apt list. `<s>/capture.py` (run as `uv run
python`, `QT_QPA_PLATFORM=offscreen`, `QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --no-sandbox"`):
copy example 07 with `validation.examples.copy_example`, run `prepare.py`, open
`2wcd.case.yaml` in `MainWindow` with a scratch store, size 1280 × 860. State *opened*: grab each
tab. Set a bounded field out of range and grab the Case tab's refusal. Call `build_charge`, loop
the Qt event loop until the Charge tab's status settles (timeout 900 s), then grab each Geometry
stage view and each Charge pane. Call `start_run`, wait for `settled`, grab Run, Convergence and
Result. Collect every `viewer/*.html` the render child wrote. `<s>/shot.js`: open each with
`file://`, viewport 1280 × 860, wait 3 s, screenshot; log console errors. Name pictures
`<state>-<tab>[-<view>].png`.

**Item 2.** Load `artifact-design` and `artifact-capabilities`. One card per picture: the picture,
two lines on what it shows, the capability rows it carries, three verdict buttons and a note
field, saved per screen id. The capability list (Markdown table: tab, control or view, what it
does, clause) goes into `docs/design/workbench.md` under *Today's shell*, with the capture commit.

**Item 3.** In `05-gui-and-packaging.md`, mark the shim section superseded at chromium-1243, with
the symbol error, and add a section: the apt list makes PySide6 and `QWebEngineView` work offscreen;
Node Playwright renders a `host_document` page headless with SwiftShader. Mark each `[verified]`
with a footnote to this plan; add a `knowledge/log.md` line.

**Item 5.** One HTML file per job, `docs/design/mockups/<nn>-<job>.html`, plus `index.html`
linking them; shared CSS inline. A persistent tab bar (Project, Structure, Geometry, Charge,
Physics, Mesh, Run, Results, Compare, or as the critique moves it); each job a numbered route of
screens with *next* and *back*. Add `design/mockups/` to `exclude_docs`. Publish with `files`.

**Item 7.** `workbench.md` sections, in order: *Purpose and users* (P1 to P3); *Today's shell* (the
capability list and the verdicts); *The jobs* (one paragraph each, its mockup); *Tabs*; *Tools*
(each with its live view, S6); *The four live links*; *The project folder* (layout, the project
file's fields, the export; S11); *Install and start* (S12); *The guided route* (QR-10); *Later
tools* (composer with S3's room for equations, structural mutator, sketcher); *The shell's reading
of artefacts* (D4); *Restated clauses*; *Inherited rows* (D6); *Glossary*. Add `Workbench design:
design/workbench.md` to *Project* in `mkdocs.yml`.

**Item 8.** NOTE form: `NOTE (the browser shell, v0.6). When the package that removes the Qt shell
lands, <ID> reads: "<text>". Until then the text above gates the Qt shell (§8.2.17 S17).` FR row
form: `| **FR-31** | SHALL … | v0.6 |`.

**Item 10.** `CHANGELOG.md`: add `## [Unreleased]` above `## [0.5.0-alpha.19]` with `WP5.01: …`
and an *Added* list; the link footer already has `[Unreleased]`. `current.md`: only the Phase 5 line.

### Work items

- [ ] 1. Capture today's shell (D1): pictures of every tab and sub-view of *Grounding D1* in three
  states and one refusal, in the scratchpad; done when each listed view has a picture or a stated
  reason. **Executor:** main.
- [ ] 2. The critique page and the capability list (D2): `docs/design/workbench.md`'s *Today's
  shell*; done when the code and review say so and the page is published. **Executor:** main.
- [ ] 3. `knowledge/07-software-stack/05-gui-and-packaging.md`, `knowledge/log.md` (D1); done when the
  code and review say so. **Executor:** `general-purpose` on Haiku.
- [ ] 4. Compaction checkpoint: wait for the verdicts and the jobs. **Executor:** main.
- [ ] 5. Read the verdicts with `ArtifactData`; the mockups in `docs/design/mockups/`, `mkdocs.yml`'s
  `exclude_docs` (D3); done when published and the strict build passes. **Executor:** main.
- [ ] 6. Compaction checkpoint: wait for the comments on the mockups. **Executor:** main.
- [ ] 7. `docs/design/workbench.md` complete, `mkdocs.yml`'s nav (D4); done when the strict build
  passes. **Executor:** main.
- [ ] 8. The specification (D5): NOTEs in `specification/02-product-overview.md`,
  `03-requirements.md`, `05-software-design/06-architecture-decisions.md`,
  `07-verification/02-tier-1.md`, `09-risks.md`; FR rows; `a-traceability-matrix.md`; done when
  `uv run .claude/scripts/duplicates.py` and the strict build pass. **Executor:** main.
- [ ] 9. The inherited rows (D6): the round, `specification/history/18-…`, its index lines, the REV
  and MOD rows; done when the code and review say so. **Executor:** main.
- [ ] 10. `CHANGELOG.md` and `docs/plans/current.md` (S19); done when the code and review say
  so. **Executor:** `general-purpose` on Haiku.

### Verification

No test is kept: the package changes no code (§8.2.13 N1). The checks are the strict documentation
build (VER-45) and `.claude/hooks/gate.sh run`, as the Phase 5 plan's *Verification* gives them, and
`uv run .claude/scripts/duplicates.py`. Review checks D5's restatements against the clauses they
replace, and that each new FR row is in Appendix A.

### Out of scope

- The framework, the server library and ADR-004's choice: WP5.02 (S8).
- The project file's schema identifier and code: the shell packages (G6).
- `CONTRIBUTING.md`'s visual-feedback loop: WP5.02 (S9).
- Retiring the guide's Qt pictures: documentation increment 5.

### Open questions

1. The jobs and the colleague: asked in item 2's report; D3 holds the fallback.
2. If WP54 merges first with new FR rows or a history record 18, `/np-ship` renumbers this
   package's (§8.4.4).
