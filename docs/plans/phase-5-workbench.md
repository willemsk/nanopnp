# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: planned, not started.** Written 24 October 2026, while Phase 4 was in progress (§8.2.17).
Planned: WP57, which may run beside Phase 4 (S1), and WP58, after `v0.5.0`. Provisional until
`/np-plan amend 5`: the shell packages from WP59. The close is last. Estimate: set by that amendment
(S14). Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a workbench in the web browser, in the spirit of molecular
viewers and continuum modelling suites combined. Each step of the work gets its own tab, and its
tools are linked both ways to live pictures. This phase designs the whole workbench, then builds its
frame over what the program already does, plus a first mutation tool that changes a residue's charge.
Three larger tools follow in phases of their own: a physics builder, a 3D side-chain mutator and a
drawing tool for pore shapes. The design work can start now; building waits for the current phase's
release.

**Cost.** The two design packages take about two to four weeks. The amendment after them prices
the rest.

**What could go wrong.** The scope is large and could pull effort away from validation. Each new
tool is therefore its own phase, ordered against validation later. The technology could prove a poor
fit; it is chosen by building one hard screen two ways and measuring both.

**Your call.** Who is the lab colleague who will try the workbench unaided at the end, and when are
they free? *Recommendation:* name them during the design study, so the final test can be scheduled.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, never restatements, and the rulings
behind this plan are §8.2.17 (S1 to S15), not re-argued here.

Phase 5 answers one question: **can a nanopore experimentalist with no Python run a case unaided in a
workbench that a method developer also wants to use?** Its gate is §8.1's, as S13 states it.

True of the codebase today:

- **The view-models are already Qt-free.** Only `gui/app.py`, `gui/probe.py` and the seven
  modules of `gui/widgets/` import PySide6; `case_model.py`, `run_model.py` and the rest do not.
- **A solve already runs in a spawned process with a plain-data event stream.** `gui/solver.py`
  `SolverProcess` streams stage, rung and iteration events to `Finished`, `Failed` or `Cancelled`,
  with an `EventCancel` flag; a server can relay it.
- **The field viewer is `webgui.js` in Qt WebEngine.** `gui/render.py` `renderer_source` loads the
  pinned build from `gui/assets/webgui/` unmodified (CON-09, VER-44).
- **The figures have a data layer.** `plot/data.py` turns artefacts into arrays, which a browser
  front end could read in place of the shell's own plots (§8.2.14 P3).
- **The tools' foundations exist only in part.** `mesh/primitives.py` has `SlabGeometry`,
  `CylinderGeometry` and `CylindricalPoreGeometry`. `inputs.profile` and `inputs.pqr` carry a
  hand-edited contour and a hand-edited PQR. `physics/models.py` `register_model` holds six models.
  The library has no residue mutation and no free-form (r, z) domain.

Risks: **RSK-15** is live at High severity (S7). **RSK-13** is re-scoped by the design document
(M3, S12).

Excluded: the physics composer, the structural mutator and the 2D sketcher, each a later phase
(S7); user-authored equations, with no phase (S3); a remote or multi-user server (S12); installers
and in-application tutorials, post-1.0 (F5); 3D solves and off-axis analytes (N4, N5).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Overlap | Only WP57 before `v0.5.0` | The API may still move (S1, S15) |
| The GUI | A tabbed workbench for P1 to P3, tools linked to live views | The author's brief (S2, S6) |
| v0.6's scope | The whole design; the shell over today's capabilities; the charge-level mutator | Validation is not held behind new tools (S4, S7) |
| Physics editor | Composition from registered blocks; room for equations later | QR-13, VER-60 (S3) |
| Front end | WP58's spike decides | Evidence (S8) |
| Working loop | Artifact mockups; a live local loop in the browser pane | Both see and control it (S9) |
| Screen checks | Fixture states, headless renders; no pixel gate | Runner-independent (S10) |
| Document | A plain project folder; a readable export | No opaque archive (S11) |
| Install, compute | One `uv` command, `nanopnp gui`; local solves over a network API | Remote later (S12) |

## Conventions established by earlier phases

- **The shell holds no physics**; every number comes from an artefact (VER-60; F5).
- **The case document is the unit of reproducibility** (IF-03; FR-25).
- **The renderer loads unmodified as a separate file**, or is not used (CON-09; M3).
- **No compiler on the end-user path** (CON-07); `gmsh` stays optional (CON-10).
- **At most two lanes run** (§8.4.4).

## Work packages

### WP57 — Discovery and the design and requirements document (F5; S2 to S7, S11, S12)

Prose and Artifact pages only (S1). It publishes today's Qt shell, rendered offscreen, as an
Artifact page for the author's keep, kill or change per screen; draws the author's three to five
jobs as clickable Artifact mockups, revised from comments; and writes `docs/design/workbench.md`:
tabs, tools, the four live views, the project folder, the guided QR-10 route, the workbench's
glossary, and the three later tools with S3's room for equations. Each settled requirement enters
the specification as an identifier tagged v0.6 or for its tool phase (F5), and VER-43, VER-44,
VER-55, VER-60, ADR-004's packaging NOTE, CON-09's PySide6 clause, RSK-13, P3 and QR-10 are
restated for the browser shell (M3, S2, S12). It proposes a ruling on each inherited row.

Tests: none kept; the strict documentation build (VER-45). Tag: none if it merges before `v0.5.0`,
otherwise `v0.6.0-alpha.1` (§8.4.1).

### WP58 — The spike and the visual-feedback workflow (S8 to S10)

After `v0.5.0`. One hard screen, the residue and charge-map link with a sketcher stub, is built
outside the shipped package twice, Python-first and as a Python server with a TypeScript
application, measuring code size, click-to-redraw time and headless drivability. The author rules,
recorded in ADR-004. Then, in the chosen stack: named fixture states, a render-every-screen command,
and the local live loop, written into `CONTRIBUTING.md` and §8.4.4.
Proposed: **VER-77**, every fixture state loads every screen with its declared controls and no
browser-console error; oracle, the screen registry.

### WP59 onward — The shell (provisional)

The workbench's frame, its tabs over today's capabilities and the four live views, the charge-level
mutator, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. They wait
on WP57's requirements and WP58's framework ruling; `/np-plan amend 5` numbers and plans them.

### The close package (last)

It resolves or carries each open decision, records the QR-10 observation, confirms Qt and the
bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report,
the `CHANGELOG.md` section and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | The scope, the overlap, the slicing, the loop, the document, the install and the gate | **Settled by the author, 24 October 2026** (S1 to S15) |
| 2 | The front-end framework and server library | **Author**, from WP58's evidence (S8) |
| 3 | The inherited rows: REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114; `MOD-09`, `MOD-13`'s command-line part, `MOD-18` (H4, H10) | **WP57** proposes, the author rules |
| 4 | Whether the shell reads `plot/data.py` and retires its own plots | **WP57** (P3) |
| 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Comments on the Qt shell's screens and the mockups | WP57 | WP57 waits; no session substitutes |
| Three to five concrete jobs | WP57's start | WP57 drafts from P1 to P3 and asks |
| The framework ruling | WP58's end | The shell packages wait |
| A local Claude Code session for the live loop | WP58 onward | Work continues headless; the author sees renders only |
| A nanopore experimentalist new to nanopnp | The close | QR-10 is waived and carried (S13) |
| The merges, and the tags if a session cannot push them | Each package | The session prints the commands |

## Verification

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
.claude/hooks/gate.sh run
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP57 | none kept | VER-45 |
| WP58 | 1 | VER-77 (proposed) |
| Shell, close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as restated; WP57's requirements; VER-77 |

**The phase is complete when:**

1. **Tiers 1 and 2 pass, per push and nightly.** No waiver.
2. **The shell's gating clauses pass as WP57 restates them**, and VER-77 passes on every fixture
   state. A miss is fixed; a re-argued clause is a spec amendment.
3. **Every capability of the Qt shell is present in the browser shell**, checked at review against
   WP57's capability list before Qt leaves. A miss keeps Qt.
4. **Each v0.6 requirement has its test or review check.** A miss is fixed, or deferred by the
   author's ruling as a `REV-nn` row.
5. **QR-10 is observed**: the colleague installs, loads a structure, accepts defaults and obtains a
   conductance and a field picture unaided. Predicted: met, with findings. A miss is waived and
   carried into the first tool phase by the author's ruling (S13).

## End-of-phase report

The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
against the browser shell; VER-77's screen and state counts; the time from a click to a redrawn
view on the reference charged case, from WP58's measure; the install's time on a clean machine; and
the tool phases' order.
