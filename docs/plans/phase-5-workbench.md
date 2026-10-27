# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: in progress; WP5.01 delivered (awaiting `/np-ship`), WP5.02 after `v0.5.0`.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended
the same day (S21 to S23; [the record](phase-5-record.md)). Planned:
WP5.01, beside Phase 4 (S1), and WP5.02, after `v0.5.0`. The shell packages from WP5.03 and their
estimate wait for `/np-plan amend 5` (S14); the close is last. Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a workbench in the web browser, combining molecular viewers
and continuum modelling suites. Each step of the work gets a tab, its tools linked both ways to live
pictures. This phase designs the whole workbench, then builds its frame over what the program
already does, plus a tool that changes a residue's charge. A physics builder, a 3D side-chain
mutator and a pore-shape drawing tool follow in phases of their own. Design can start now; building
waits for the current phase's release.

**Cost.** The two design packages take about two to four weeks. The amendment after them prices
the rest.

**What could go wrong.** The scope could pull effort from validation, so each new tool is its own
phase, ordered against validation later. The technology could fit poorly, so one hard screen is
built two ways and both are measured.

**Your call.** Who is the lab colleague who will try the workbench unaided at the end?
*Recommendation:* name them during the design study, so the final test can be scheduled.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, never restatements, and the rulings
behind this plan are §8.2.17 (S1 to S20), not re-argued here.

Phase 5 answers one question: **can a nanopore experimentalist with no Python run a case unaided in a
workbench that a method developer also wants to use?** Its gate is §8.1's, as S13 states it.

True of the codebase today:

- **The view-models are Qt-free.** Only `gui/app.py`, `gui/probe.py` and `gui/widgets/` import
  PySide6.
- **A solve runs in a spawned process with a plain-data event stream** (`gui/solver.py`
  `SolverProcess`, ending in `Finished`, `Failed` or `Cancelled`, cancelled by `EventCancel`); a
  server can relay it.
- **The field viewer is the pinned `webgui.js`**, loaded unmodified by `gui/render.py` (CON-09,
  VER-44).
- **`plot/data.py` turns artefacts into arrays** a browser front end could read (§8.2.14 P3).
- **The tools' foundations are partial.** `mesh/primitives.py` has three geometries; `inputs.profile`
  and `inputs.pqr` take a hand-edited contour and PQR; `physics/models.py` registers six models. The
  library has no residue mutation and no free-form (r, z) domain.

Risks: **RSK-15**, live and High (S7); **RSK-13**, re-scoped by the design document (M3, S12).

Excluded: the composer, the structural mutator and the sketcher, later phases (S7); user-authored
equations (S3); a remote server (S12); installers and tutorials, post-1.0 (F5); 3D and off-axis
analytes (N4, N5).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Overlap | Only WP5.01 before `v0.5.0` | The API may still move (S1, S15) |
| The GUI | A workbench for P1 to P3, tools linked to live views; its organisation and look ruled in WP5.01's design round | The author's brief (S2, S6, S21) |
| v0.6's scope | The whole design; the shell over today's capabilities; the charge mutator | Validation waits on no new tool (S4, S7) |
| Physics editor | Composition from registered blocks; room for equations later | QR-13, VER-60 (S3) |
| Front end | WP5.02's spike decides | Evidence (S8) |
| Working loop | Artifact mockups; a live local loop; `/np-gui` renders, reviews and collects verdicts | Both see and control it (S9, S22) |
| Screen checks | Fixture states, headless renders; no pixel gate | Runner-independent (S10) |
| Document | A plain project folder; a readable export | No opaque archive (S11) |
| Install, compute | One `uv` command, `nanopnp gui`; local solves over a network API | Remote later (S12) |

## Conventions established by earlier phases

- **The shell holds no physics**; every number comes from an artefact (VER-60; F5).
- **The case document is the unit of reproducibility** (IF-03, FR-25).
- **The renderer loads unmodified as a separate file**, or is not used (CON-09; M3).
- **No compiler on the end-user path** (CON-07); `gmsh` stays optional (CON-10).

## Work packages

### WP5.01 — Discovery and the design and requirements document (F5; S2 to S7, S11, S12)

**Delivered** ([the plan](wp5.01-workbench-design-study.md)), 27 October 2026, awaiting `/np-ship`.
It built `/np-gui`, the `gui-reviewer` agent and the render scripts, and used them on every round. The
Qt shell's 41 capabilities are listed and critiqued (REV-134). The design round ruled "suites in a
project", later four suites with Study the fourth (WB-01 to WB-29), and a look and feel whose tokens are
`docs/design/tokens.css` as the default theme. Twenty-one choices were picked, and mockup A was chosen
and revised; `docs/design/workbench.md` holds the whole design. The specification gains FR-31 to FR-43
and QR-16, and the browser shell's restatements as NOTEs (S17). The inherited rows are ruled in
§8.2.18, MOD-09 brought into v0.6, and the rows it left open in §8.2.19. **Live for later packages:**
REV-137, REV-138 and REV-141 for WP5.02 (U5); for `/np-plan amend 5`, the library capabilities of REV-136
(U3) and MOD-09 (T4) before their screens, protonation before the density (REV-135, U2) and the sweep's
design round (REV-139, U4); REV-134 closes with Qt (U1); open decisions 3 and 4 settled.

*As planned:* prose, mockups, the specification and the GUI development tools under `.claude/` (S1, S22). It
first builds `/np-gui` and the `gui-reviewer` agent, and uses them: it publishes today's Qt shell,
rendered offscreen, for the author's keep, drop or change per screen; runs an interactive design
round, a brainstorm over several organising principles and then a grilling, on how the workbench is
organised beyond one tab per stage and how it looks and feels (S21); draws the author's three to
five jobs as clickable mockups in the ruled organisation and style; and writes
`docs/design/workbench.md`: the organisation, the look and feel, tabs, tools, the four live views,
the project folder, the guided QR-10 route, a glossary, and the three later tools with S3's room for
equations. Each settled requirement enters the specification tagged v0.6 or for its tool phase (F5).
IF-09, VER-43, VER-44, VER-55, VER-60, ADR-004's packaging NOTE, CON-09's PySide6 clause, RSK-13, P3
and QR-10 are restated for the browser shell (M3, S2, S12), each beside its clause and replacing it
only at `v0.6.0` (S17). It proposes a ruling on each inherited row.

Tests: none kept; the strict documentation build (VER-45). Tag: none if it merges before `v0.5.0`,
its entry under `## [Unreleased]`; otherwise `v0.6.0-alpha.1` (§8.4.1).

### WP5.02 — The spike and the visual-feedback workflow (S8 to S10)

After `v0.5.0`. One hard screen, the residue and charge-map link with a sketcher stub, is built
twice outside the package, Python-first and as a Python server with a TypeScript application,
measuring code size, click-to-redraw time and headless drivability; the author rules in ADR-004.
Then, in the chosen stack: fixture states, a render-every-screen command and the local live loop,
written into `CONTRIBUTING.md` and §8.4.4.
Proposed: **VER-77**, every fixture state loads every screen with its declared controls and no
browser-console error; oracle, the screen registry. It names the commands that log the
end-of-phase numbers: click-to-redraw time and the clean-environment install time. Tag
`v0.6.0-alpha.2` (S19). It also owns REV-137 (the renderer for each view, the explorer's controls
against `webgui`), REV-138 (non-text contrast in `/np-gui render`) and REV-141 (CON-08 and CON-11
restated beside ADR-004) (§8.2.19 U5).

### WP5.03 onward — The shell (provisional)

The workbench's frame, its tabs over today's capabilities and the four live views, the charge-level
mutator, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. Before
the mutator, a library package moves protonation before the density, the protonated density the
validated default (REV-135; §8.2.19 U2). The amendment also runs the sweep's design round (REV-139,
U4) and orders REV-136's capabilities (U3). The mutator lands library first: a `charge/` function that sets a residue's charge state, with a Tier 1
test that the projected charge changes by that residue's alone, before its shell control (§8.1;
RSK-15). They wait on WP5.01's requirements and WP5.02's framework ruling; `/np-plan amend 5` plans
them from WP5.03.

### The close package (last)

It resolves or carries each open decision, records QR-10, confirms Qt and the bundle are gone with
the capability list covered, orders the tool phases (S7), and writes the report, the changelog and
`CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | The scope, the overlap, the slicing, the loop, the document, the install, the gate, the package names | **Settled by the author, 24 October 2026** (S1 to S20) |
| 2 | The front-end framework and server library | **Author**, from WP5.02's evidence (S8) |
| 3 | The inherited rows: REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114; `MOD-09`, `MOD-13`'s command-line part, `MOD-18` (H4, H10) | **Settled by the author, 27 October 2026** (§8.2.18 T1 to T5): MOD-09 brought into v0.6, the rest as WP5.01 proposed; `/np-plan amend 5` carries the owners |
| 4 | Whether the shell reads `plot/data.py` and retires its own plots | **Settled by WP5.01**: it does, and `gui/`'s duplicates retire with Qt (`docs/design/workbench.md`, *The shell's reading of artefacts*) |
| 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Comments on the screens and mockups | WP5.01 | WP5.01 waits |
| Answers in the design round on organisation and look (S21) | WP5.01 | WP5.01 waits |
| The workbench's areas | WP5.01's start | **Supplied 24 October 2026** (S24) |
| The framework ruling | WP5.02's end | The shell packages wait |
| A local Claude Code session | WP5.02 onward | Work continues headless, on renders |
| An experimentalist new to nanopnp | The close | QR-10 is waived and carried (S13) |
| Merges; tags a session cannot push | Each package | The session prints the commands |

## Verification

```bash
.claude/hooks/gate.sh run
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP5.01 | none kept | VER-45 |
| WP5.02 | 1 | VER-77 (proposed) |
| Shell, close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as restated; WP5.01's requirements; VER-77; the mutator's Tier 1 test |

**The phase is complete when:**

1. **Tiers 1 and 2 pass**, per push and nightly. No waiver.
2. **The restated gating clauses and VER-77 pass** on every fixture state. A miss is fixed; a
   re-argued clause is a spec amendment.
3. **Every Qt shell capability is in the browser shell**, checked against WP5.01's list before Qt
   leaves. A miss keeps Qt.
4. **Each v0.6 requirement has its test or review check.** A miss is fixed, or deferred as a
   `REV-nn` row.
5. **QR-10 is observed**: the colleague installs, loads a structure, accepts defaults and obtains a
   conductance and a field picture unaided. Predicted: met, with findings. A miss is waived and
   carried (S13).

## End-of-phase report

The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
against the browser shell; VER-77's screen and state counts; the time from a click to a redrawn
view on the reference charged case and the install's time on a clean machine, each re-run by the
command WP5.02 names; and the tool phases' order.
