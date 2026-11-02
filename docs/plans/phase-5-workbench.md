# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: in progress; WP5.01 and WP5.02 delivered, the library packages WP5.03 to WP5.06 planned after
it.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended the same day (S21 to S23); the library
packages ordered on 1 November 2026 (§8.2.28 AD1 to AD5; [the record](phase-5-record.md)); WP5.02 planned and delivered on 2 November
2026 (§8.2.30 AF1 to AF4). The shell packages, the
sweep's design round and the estimate wait for a second `/np-plan amend 5` after WP5.02's framework ruling (AD1); the
close is last. Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a workbench in the web browser, combining molecular viewers
and continuum modelling suites. Each step of the work gets a tab, its tools linked both ways to live
pictures. The design is done. After the current release, one hard screen is built two ways to choose
the technology. Then four library steps come before any screen: protonation feeds the shape of the
pore, a residue's charge can be changed, a project can name and reuse its models, and the quantities
a run reports become a list that can grow. The screens are planned once the technology is chosen.

**Cost.** The spike takes about two weeks and each library step about one, so roughly six weeks
before the first screen. The screens are priced when they are planned.

**What could go wrong.** Protonation before the shape moves the pore's geometry for structure
cases; the reference cases keep the old way behind a switch, so their numbers do not move, and the
number checks would show it if they did. The scope could pull effort from validation, so each new
tool after this phase is its own phase.

**Your call.** Who is the lab colleague who will try the workbench unaided at the end?
*Recommendation:* name them before the shell packages are planned, so the final test can be scheduled.

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
REV-137, REV-138, REV-141 and REV-143 for WP5.02 (U5, U7); for `/np-plan amend 5`, the library capabilities of REV-136
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

### WP5.02 — The spike and the visual-feedback workflow (S8 to S10; §8.2.30 AF1 to AF4)

**Delivered** ([the plan](wp5.02-framework-spike.md); [the report](../design/spike/report.md)), 2 November 2026. The hard
screen, a residue and its charge on the pore map, was built twice over one FastAPI server and measured; both passed the
pre-set tests (front end 26 ms p95 for NiceGUI, 22 ms for React; install 86 MiB against 12 MiB), and the author ruled
**NiceGUI** (AF4; ADR-004's NOTE, the front end). The spikes left the tree. Landed in `src/nanopnp/gui/web/`: the
server and its contract (loopback, one ready line, a launch token, stops with its input; ADR-004's NOTE), `nanopnp gui`
with `--state` and `--dev`, the screen registry (`home`, `st-charge`), the states `empty`, `charged-tube` and
`refused`, Mol* vendored unmodified. VER-78 passes in Chromium; `gate.sh run` and CI's tier-1 leg require the browser.
`/np-gui render shell` and the `nontext` measure ran; REV-137, REV-138, REV-141 and REV-143 are `fixed`. Live
constraints: the 200 ms line is unmeasured for the whole picture (Mol* alone takes about 800 ms on software GL; measure
on a GPU in the package that builds the first Study screen); a screen is ready only after Mol* has drawn; the lock holds
a uv override for docutils and pdb2pqr 3.7.1 (REV-175); the study's mockups fail the non-text measure (REV-176).
Tag `v0.6.0-alpha.2` (S19).

Each library package lands its capability with its Tier 1 and 2 tests before any screen surfaces it (§8.1; RSK-15;
§8.2.17 S7), and each is planned by `/np-plan wp` after WP5.02 (AD2, AD3). None changes `src/` before `v0.5.0` (S1).

### WP5.03 — Protonation before the density (§8.2.19 U2; REV-135)

Stage 2 smears the protonated frames, so a protonation state moves the density, the contour and the mesh; smearing the
hydrogens as loaded becomes a switch away from the validated default, set by the reference-reproduction cases. It
amends PHY-16, FR-04 and §5.2's stage 2 and 7 rows, writing the NOTE beside PHY-16 step 3 into their text. Tier 1: a
changed protonation state moves the density. The VAL-03 golden and the Tier 3 cases carry the switch, so their numbers
do not move; VER-62 holds at zero drift. A miss is investigated, then reverted or ruled and re-pinned (G10, I4). Tag
`v0.6.0-alpha.3`.

### WP5.04 — The charge mutator's library step (FR-38; §8.2.17 S4; §8.2.19 U6)

A `charge/` function that sets a titratable residue's protonation state, or a residue's charge or radius, at stage 7's
PQR step on every chain, saved as a variant of its molecular model and recorded as its difference from its parent.
After WP5.03, so a variant moves the geometry too. Tier 1: the projected charge changes by that residue's alone. Tag
`v0.6.0-alpha.4`.

### WP5.05 — Named models and study overrides in the case (WB-11; FR-39; REV-62)

A case references named molecular and continuum models and resolves into one complete case file; a study overrides
any of its continuum model's physics defaults; a built model is reused by every study that names it, rebuilding only
the stages a changed value moves. A case-schema change, under the release's identifier (G6). It owns REV-62, a mesh
named by store key (§8.2.18 T2). It builds on WP59's public `Case` and `Session` route (§8.2.27 AC1). Tag
`v0.6.0-alpha.5`.

### WP5.06 — Outputs and steric models as registries (MOD-09; §8.2.18 T4; §8.2.28 AD5)

The outputs and the steric models become registries, so a new quantity of interest needs no edit of the case schema
(a case-schema change). With them, the review's QoI seam (CODE_REVIEW_024 candidate 5): one extraction interface and
one boundary-existence check shared by `physics/distance.py` and the three `post/` modules. The indicator and reaction
routes keep their cross-check (FR-23, QR-04). Before the Study suite offers outputs (T4). Tag `v0.6.0-alpha.6`.

### The shell (provisional, planned after WP5.02)

The workbench's frame, its four suites over today's capabilities and the four live views, the charge mutator's
control, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. A second
`/np-plan amend 5`, after WP5.02's framework ruling, plans them, runs the sweep's design round (REV-139, U4), rules
REV-136's v0.6 cut line (U3) and carries T2's rows to their packages. Placed now: **REV-170**, the stage-5 region
interface, lands in the package that builds the Continuum suite's Geometry tool, library step first, VER-62's mesh
hash checked there (§8.2.28 AD4); **REV-121**, stage 1's axis for a single-chain or mixed-chain pore, lands in the
package that surfaces structure preparation, with §5.3.1 and VER-48 (§8.2.24 Z5).

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
| 6 | Which packages the first `/np-plan amend 5` plans, and their order | **Settled by the author, 1 November 2026** (§8.2.28 AD1 to AD5): the four library packages WP5.03 to WP5.06, after the spike; REV-170 with the Geometry tool, REV-121 with structure preparation |
| 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Author**, at the second `/np-plan amend 5`, after WP5.02 (AD1) |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Comments on the screens and mockups | WP5.01 | WP5.01 waits |
| Answers in the design round on organisation and look (S21) | WP5.01 | WP5.01 waits |
| The workbench's areas | WP5.01's start | **Supplied 24 October 2026** (S24) |
| The framework ruling | WP5.02's end | The shell packages wait |
| The answers to the sweep's design round and the cut line | The second `/np-plan amend 5` | The shell packages wait |
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
| WP5.02 | 1 | VER-78 (proposed) |
| WP5.03, protonation before the density | 1, 2 | U2's Tier 1 test; VAL-03's golden and VER-62 unmoved |
| WP5.04, the mutator's library step | 1 | FR-38's Tier 1 test: the projected charge changes by the residue's alone |
| WP5.05, named models | 1, 2 | FR-39's reuse and rebuild-only-what-moved; the schema's identifier (G6) |
| WP5.06, the registries | 1, 2 | MOD-09; FR-23 and QR-04's route cross-check unchanged |
| Shell, close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as restated; WP5.01's requirements; VER-78; the mutator's Tier 1 test |

**The phase is complete when:**

1. **Tiers 1 and 2 pass**, per push and nightly. No waiver.
2. **The restated gating clauses and VER-78 pass** on every fixture state. A miss is fixed; a
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
against the browser shell; VER-78's screen and state counts; the time from a click to a redrawn
view on the reference charged case and the install's time on a clean machine, each re-run by the
command WP5.02 names; and the tool phases' order.
