# Phase 5 plan: the record

The text that amendments replaced in [the Phase 5 plan](phase-5-workbench.md), copied verbatim, one
dated section per amendment (§8.2.16 R4). Read it on demand; the plan states what holds now.

---

## 24 October 2026: WP5.01 gains the design round and the GUI development tools (§8.2.17 S21 to S23)

While WP5.01 was planned, the author ruled that it also holds an interactive design round on the
workbench's organisation and its look and feel (S21), and builds the workflow for developing the GUI
(S22); its plan may exceed the word caps (S23). Replaced text follows.

The *Design decisions* rows:

| The GUI | A tabbed workbench for P1 to P3, tools linked to live views | The author's brief (S2, S6) |
| Working loop | Artifact mockups; a live local loop | Both see and control it (S9) |

The scope of WP5.01 — Discovery and the design and requirements document (F5; S2 to S7, S11, S12):

Prose and Artifact pages only (S1). It publishes today's Qt shell, rendered offscreen, for the
author's keep, kill or change per screen; draws the author's three to five jobs as clickable
mockups; and writes `docs/design/workbench.md`: tabs, tools, the four live views, the project
folder, the guided QR-10 route, a glossary, and the three later tools with S3's room for equations.
Each settled requirement enters the specification tagged v0.6 or for its tool phase (F5). VER-43,
VER-44, VER-55, VER-60, ADR-004's packaging NOTE, CON-09's PySide6 clause, RSK-13, P3 and QR-10 are
restated for the browser shell (M3, S2, S12), each beside its clause and replacing it only at
`v0.6.0` (S17). It proposes a ruling on each inherited row.

---

## 24 October 2026: the author's areas supplied (§8.2.17 S24)

The author named the workbench's areas and made the design document public. Replaced text in
*What the author supplies*:

| Three to five concrete jobs | WP5.01's start | WP5.01 drafts from P1 to P3 and asks |

## 1 November 2026: the library packages ordered (§8.2.28 AD1 to AD5)

The first `/np-plan amend 5` planned WP5.03 to WP5.06 after the spike and placed REV-170 and REV-121; the shell packages wait for a second amendment after WP5.02. The replaced text read:

The status paragraph:

> **Status: in progress; WP5.01 delivered (awaiting `/np-ship`), WP5.02 after `v0.5.0`.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended
> the same day (S21 to S23; [the record](phase-5-record.md)). Planned:
> WP5.01, beside Phase 4 (S1), and WP5.02, after `v0.5.0`. The shell packages from WP5.03 and their
> estimate wait for `/np-plan amend 5` (S14); the close is last. Release: **v0.6** (`v0.6.0`).

The In brief:

> ## In brief
>
> **What changes.** The program gains a workbench in the web browser, combining molecular viewers
> and continuum modelling suites. Each step of the work gets a tab, its tools linked both ways to live
> pictures. This phase designs the whole workbench, then builds its frame over what the program
> already does, plus a tool that changes a residue's charge. A physics builder, a 3D side-chain
> mutator and a pore-shape drawing tool follow in phases of their own. Design can start now; building
> waits for the current phase's release.
>
> **Cost.** The two design packages take about two to four weeks. The amendment after them prices
> the rest.
>
> **What could go wrong.** The scope could pull effort from validation, so each new tool is its own
> phase, ordered against validation later. The technology could fit poorly, so one hard screen is
> built two ways and both are measured.
>
> **Your call.** Who is the lab colleague who will try the workbench unaided at the end?
> *Recommendation:* name them during the design study, so the final test can be scheduled.

The shell's entry:

> ### WP5.03 onward — The shell (provisional)
>
> The workbench's frame, its four suites over today's capabilities and the four live views, the charge-level
> mutator, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. Before
> the mutator, a library package moves protonation before the density, the protonated density the
> validated default (REV-135; §8.2.19 U2). The amendment also runs the sweep's design round (REV-139,
> U4) and orders REV-136's capabilities (U3). The mutator lands library first: a `charge/` function that sets a residue's charge state, with a Tier 1
> test that the projected charge changes by that residue's alone, before its shell control (§8.1;
> RSK-15). They wait on WP5.01's requirements and WP5.02's framework ruling; `/np-plan amend 5` plans
> them from WP5.03.

## Amended 2 November 2026 (§8.2.30 AF1 to AF3)

WP5.02's plan named the candidates, added the desktop-wrapper probe and the server's contract (AF1), and ruled that the
spikes leave the tree after the ruling (AF3). The entry read:

> ### WP5.02 — The spike and the visual-feedback workflow (S8 to S10)
>
> After `v0.5.0`. One hard screen, the residue and charge-map link with a sketcher stub, is built
> twice outside the package, Python-first and as a Python server with a TypeScript application,
> measuring code size, click-to-redraw time and headless drivability; the author rules in ADR-004.
> Then, in the chosen stack: fixture states, a render-every-screen command and the local live loop,
> written into `CONTRIBUTING.md` and §8.4.4.
> Proposed: **VER-78**, every fixture state loads every screen with its declared controls and no
> browser-console error; oracle, the screen registry. It names the commands that log the
> end-of-phase numbers: click-to-redraw time and the clean-environment install time. Tag
> `v0.6.0-alpha.2` (S19). It also owns REV-137 (the renderer for each view, the explorer's controls
> against `webgui`), REV-138 (non-text contrast in `/np-gui render`) and REV-141 (CON-08 and CON-11
> restated beside ADR-004) (§8.2.19 U5), and REV-143 (the light theme's control edge on a selected row,
> with REV-138) (U7).

## Amended 3 November 2026 (§8.2.31 AG1 to AG7)

The second amendment, after WP5.02 merged: the shell cut one package per suite after the frame (WP5.08 and WP5.16 to WP5.22), the
sweep's variables and forecast as WP5.07, the comparison's difference field in v0.6, and criterion 6 on the 200 ms
redraw. Replaced text follows.

The status line:

**Status: in progress; WP5.01 and WP5.02 delivered, the library packages WP5.03 to WP5.06 planned after
it.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended the same day (S21 to S23); the library
packages ordered on 1 November 2026 (§8.2.28 AD1 to AD5; [the record](phase-5-record.md)); WP5.02 planned and delivered on 2 November
2026 (§8.2.30 AF1 to AF4). The shell packages, the
sweep's design round and the estimate wait for a second `/np-plan amend 5` after WP5.02's framework ruling (AD1); the
close is last. Release: **v0.6** (`v0.6.0`).

The *In brief*:

**In brief**

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

The *Design decisions* row:

| Front end | WP5.02's spike decides | Evidence (S8) |

WP5.01's status:

**Delivered** ([the plan](wp5.01-workbench-design-study.md)), 27 October 2026, awaiting `/np-ship`.

WP5.02's status:

**Delivered** ([the plan](wp5.02-framework-spike.md); [the report](../../design/spike/report.md)), 2 November 2026.

The paragraph after WP5.02:

Tag `v0.6.0-alpha.2` (S19).

Each library package lands its capability with its Tier 1 and 2 tests before any screen surfaces it (§8.1; RSK-15;
§8.2.17 S7), and each is planned by `/np-plan wp` after WP5.02 (AD2, AD3). None changes `src/` before `v0.5.0` (S1).

The shell and the close:

**The shell (provisional, planned after WP5.02)**

The workbench's frame, its four suites over today's capabilities and the four live views, the charge mutator's
control, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. A second
`/np-plan amend 5`, after WP5.02's framework ruling, plans them, runs the sweep's design round (REV-139, U4), rules
REV-136's v0.6 cut line (U3) and carries T2's rows to their packages. Placed now: **REV-170**, the stage-5 region
interface, lands in the package that builds the Continuum suite's Geometry tool, library step first, VER-62's mesh
hash checked there (§8.2.28 AD4); **REV-121**, stage 1's axis for a single-chain or mixed-chain pore, lands in the
package that surfaces structure preparation, with §5.3.1 and VER-48 (§8.2.24 Z5).

**The close package (last)**

It resolves or carries each open decision, records QR-10, confirms Qt and the bundle are gone with
the capability list covered, orders the tool phases (S7), and writes the report, the changelog and
`CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

Open decision 7:

| 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Author**, at the second `/np-plan amend 5`, after WP5.02 (AD1) |

*What the author supplies*, the framework ruling:

| The framework ruling | WP5.02's end | The shell packages wait |

*What the author supplies*, the sweep's answers:

| The answers to the sweep's design round and the cut line | The second `/np-plan amend 5` | The shell packages wait |

The *Verification* row:

| Shell, close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as restated; WP5.01's requirements; VER-78; the mutator's Tier 1 test |

## Amended 3 November 2026 (§8.2.31 AG8)

At WP5.03's plan the author ruled that examples 06 and 07 take the protonated density and that example 07's VER-62
walk is re-pinned; the package also moves the case schema to `nanopnp/case/v0.6`. WP5.03's entry read:

> **WP5.03 — Protonation before the density (§8.2.19 U2; REV-135)**
>
> Stage 2 smears the protonated frames, so a protonation state moves the density, the contour and the mesh; smearing the
> hydrogens as loaded becomes a switch away from the validated default, set by the reference-reproduction cases. It
> amends PHY-16, FR-04 and §5.2's stage 2 and 7 rows, writing the NOTE beside PHY-16 step 3 into their text. Tier 1: a
> changed protonation state moves the density. The VAL-03 golden and the Tier 3 cases carry the switch, so their numbers
> do not move; VER-62 holds at zero drift. A miss is investigated, then reverted or ruled and re-pinned (G10, I4). Tag
> `v0.6.0-alpha.3`.

Verification's WP5.03 row read: U2's Tier 1 test; VAL-03's golden and VER-62 unmoved.

## Amended 3 November 2026 (§8.2.31 AG9 to AG11)

At WP5.04's plan the author ruled where a charge edit goes (AG9), what a radius edit is (AG10) and how a variant is
recorded (AG11). WP5.04's entry read:

> **WP5.04 — The charge mutator's library step (FR-38; §8.2.17 S4; §8.2.19 U6)**
>
> A `charge/` function that sets a titratable residue's protonation state, or a residue's charge or radius, at stage 7's
> PQR step on every chain, saved as a variant of its molecular model and recorded as its difference from its parent.
> After WP5.03, so a variant moves the geometry too. Tier 1: the projected charge changes by that residue's alone. Tag
> `v0.6.0-alpha.4`.

Verification's WP5.04 row read: FR-38's Tier 1 test: the projected charge changes by the residue's alone.

## Amended 3 November 2026 (§8.2.31 AG12, AG13)

At WP5.05's plan the author ruled that a study may override any value of the models it names (AG12) and that the sweep
over the library's models is WP5.05's (AG13). WP5.05's entry read:

> **WP5.05 — Named models and study overrides in the case (WB-11; FR-39; REV-62)**
>
> A case references named molecular and continuum models and resolves into one complete case file; a study overrides
> any of its continuum model's physics defaults; a built model is reused by every study that names it, rebuilding only
> the stages a changed value moves. A case-schema change, under the release's identifier (G6). It owns REV-62, a mesh
> named by store key (§8.2.18 T2). It builds on WP59's public `Case` and `Session` route (§8.2.27 AC1). Tag
> `v0.6.0-alpha.5`.

Verification's WP5.05 row read: FR-39's reuse and rebuild-only-what-moved; the schema's identifier (G6).

## Amended 4 November 2026 (§8.2.32 AH1)

At WP5.06's plan the author ruled that an output states what it needs of a model's declaration, and a model provides
every output whose need it meets (AH1). WP5.06's entry read:

> **WP5.06 — Outputs and steric models as registries (MOD-09; §8.2.18 T4; §8.2.28 AD5)**
>
> The outputs and the steric models become registries, so a new quantity of interest needs no edit of the case schema
> (a case-schema change). With them, the review's QoI seam (CODE_REVIEW_024 candidate 5): one extraction interface and
> one boundary-existence check shared by `physics/distance.py` and the three `post/` modules. The indicator and reaction
> routes keep their cross-check (FR-23, QR-04). Before the Study suite offers outputs (T4). Tag `v0.6.0-alpha.6`.

Verification's WP5.06 row read: MOD-09; FR-23 and QR-04's route cross-check unchanged.

## Amended 5 November 2026 (§8.2.33 AI1)

At WP5.08's plan the author ruled that the settings offer a theme selector and a colour modifier, a user's theme setting
its own contrast (AI1). WP5.08's entry read:

> **WP5.08 — The frame and the project folder (FR-31, FR-32, FR-34, FR-35; REV-32, REV-52; MOD-13)**
>
> Library step first: the project folder of `docs/design/workbench.md` (*The project folder*), its project file holding no
> physics, its export as readable files, and the store's entries of an older schema listed and removed on request
> (REV-32); `deviations` and `SolveReporting` join the stage protocol as optional members (REV-52), so the changed count and
> the queue read every stage. Then the frame in NiceGUI: the title bar with the menus, the command palette, the shortcuts
> and the changed count with its list (FR-34); the activity bar of the four suites; the project rail; the bottom panel
> with the run queue and the log; the problems list (FR-35); the theme, the density and the user's settings (WB-18,
> WB-19, WB-30, WB-31). `nanopnp gui [<project>]` opens a project, and `cli/__init__.py` is split as it changes (MOD-13's
> command-line part). Q01 to Q08 move here. VER-78 gains the frame's states. Tag `v0.6.0-alpha.8`.

## Amended 5 November 2026 (§8.2.33 AI9 to AI14)

At WP5.08's plan the author ruled its own choices, asked by AI7's standard: inputs copied or linked (AI10), the model
files a case names imported (AI11) and every shortcut rebindable (AI12). WP5.08's entry read:

> **WP5.08 — The frame and the project folder (FR-31, FR-32, FR-34, FR-35; REV-32, REV-52; MOD-13; §8.2.33 AI1)**
>
> [The plan](wp5.08-the-frame-and-the-project-folder.md). Library step first: the project folder of `docs/design/workbench.md`
> (*The project folder*), its project file holding no physics, a case file imported into it as its two models and its
> study, its export as readable files, and the store's entries of an older schema listed and removed on request (REV-32);
> `deviations` and `SolveReporting` join the stage protocol as optional members (REV-52), so the changed count and the
> queue read every stage. Then the frame in NiceGUI: the title bar with the menus, the command palette, the shortcuts
> and the changed count with its list (FR-34); the activity bar of the four suites; the project rail; the bottom panel
> with the run queue and the log; the problems list (FR-35); the theme, the density and the user's settings (WB-18,
> WB-19, WB-30, WB-31), with a theme selector and a colour modifier over the shipped themes and the user's own, a user's
> theme setting its own contrast (AI1). `nanopnp gui [<project>]` opens a project, and `cli/__init__.py` is split as it
> changes (MOD-13's command-line part). Q01 to Q08 move here. VER-78 gains the frame's states. Tag `v0.6.0-alpha.8`.

## Amended 5 November 2026 (§8.2.34 AJ1 to AJ10)

After the author's verdicts on WP5.08's frame, the third `/np-plan amend 5` ruled the frame rebuilt on Quasar's
components, physics a third reusable model with a Physics suite of its own, the values each model exposes, `impeccable`
inside `np-gui`, the changed table, each suite designed on a prototype over 2WCD, the settings as one declared list, and
the shell's packages renumbered WP5.09 and WP5.15 to WP5.22 (AJ1 to AJ10). The plan's status read:

> **Status: in progress; WP5.01 to WP5.07 merged; WP5.08 delivered, awaiting its merge; the shell packages WP5.16 to WP5.22 planned.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended the same day (S21 to

The design decisions' rows read:

> | The shell's slicing | A frame package, then one package per suite in the route's order | Each pull request reviews one suite's screens (AG1) |
> | Working loop | Artifact mockups; a live local loop; `/np-gui` renders, reviews and collects verdicts | Both see and control it (S9, S22) |

The shell's package entries read:

> ### WP5.16 — The Molecular suite (FR-37, FR-38; REV-121; REV-41's `prepare`)
>
> Library step first: stage 1's axis estimated from the channel cavity for a single-chain or mixed-chain pore, gated like
> the permutation axis, with §5.3.1 and VER-48 (REV-121; §8.2.24 Z5); a `prepare` command over `orient_pore` (REV-41).
> Then the tools Prepare structure, Ensemble, Protonation, Charge edit (FR-38's control over WP5.04's step) and View, the
> molecule drawn by Mol*. Q09, Q13 and Q27 move here. Tag `v0.6.0-alpha.9`.
>
> ### WP5.17 — The Continuum suite (REV-170, REV-39; FR-33's geometry link)
>
> Library step first: one stage-5 region interface with an adapter per kind, the cylinder's two classes merged and the
> wall sizing moved into `mesh/` (REV-170; AD4), VER-62's mesh hash unmoved or the move ruled and re-pinned (G10, I4).
> Then Protein geometry, Contour (on any profile, extracted or supplied, REV-39; its check off the interface's thread,
> asking before an edit is discarded, as T1 carries REV-56), Region, Mesh with its quality selection, and Physics
> defaults; a geometry and its parameters linked both ways (FR-33). Q10 to Q12 and Q14 to Q23 move here; VER-55 as
> restated. Tag `v0.6.0-alpha.17`.
>
> ### WP5.19 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; AG7)
>
> Overview; Study setup with the overrides of WP5.05; Sweep, with variables and the forecast's warning of WP5.07; Charge
> on the mesh, a residue and the charge map linked both ways (FR-33; the spike's hard screen); Runs, a run's convergence
> unfolded in the queue. `upto` on reproduce (REV-41). The 200 ms redraw is measured on the author's machine with a GPU
> (AG7; criterion 6). Q24 to Q26 and Q28 to Q36 move here; VER-44 and VER-60 as restated. Tag `v0.6.0-alpha.19`.
>
> ### WP5.20 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)
>
> Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
> either lacks the point (AG6). Then the results explorer and its tiles: a field drawn by `webgui` when its tile opens it,
> its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut. Probes and cuts are linked to their
> field, and a run to its result (FR-33). Comparison shows two runs side by side on one scale or as their difference.
> Q37 to Q41 move here. Tag `v0.6.0-alpha.20`.
>
> ### WP5.21 — The guided route, Qt's removal and documentation increment 5 (FR-36; REV-134; S13, S17)
>
> The guided route over the suites (FR-36). Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt
> widgets, the bundle and the packaging probe leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55,
> VER-60, CON-08, CON-09, CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1).
> The application guide is rewritten against the browser workflow with the rendered screens (§8.1's increment 5). Tag
> `v0.6.0-alpha.21`.
>
> ### WP5.22 — The close
>
> It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
> bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report, the changelog
> and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

Open decision 7, the GPU row of *What the author supplies*, and the verification rows read:

> | 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Settled by the author, 3 November 2026** (§8.2.31 AG1 to AG7): one package per suite after the frame, WP5.08 and WP5.16 to WP5.22; WP5.07 for the sweep's variables and forecast; the difference field in v0.6 |
> | A machine with a GPU, in a local session | WP5.19 | The 200 ms line stays unmeasured; a `REV-nn` row carries it to the close |
> | WP5.16, Molecular | 1, 2 | REV-121's cavity axis against a known axis (VER-48); VER-78 |
> | WP5.17, Continuum | 1, 2 | VER-55 as restated; VER-62's mesh hash unmoved by REV-170; VER-78 |
> | WP5.19, Study | 1 | VER-44 and VER-60 as restated; VER-78; the 200 ms measure (criterion 6) |
> | WP5.20, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; VER-78 |
> | WP5.21, route and Qt's removal; WP5.22, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; VER-78 |

Criterion 6 read:

> 6. **The redraw is measured** on the author's machine with a GPU, in WP5.19: a residue selected on the charge map
>    redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
>    whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
>    binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

## Amended 8 November 2026 (§8.2.36 AL22 to AL27)

The fourth amendment, after WP5.09's merge: CODE_REVIEW_039's follow-up became three packages, WP5.10 to WP5.12, and four
of CODE_REVIEW_036's six clean-ups two packages, WP5.13 and WP5.14, all before the frame; the radii clean-up (REV-218)
opens the Molecular suite and the region seam (REV-170) stays the Continuum suite's (AL22, AL24, AL25). The planned
packages were renumbered from WP5.10 to WP5.17 to WP5.15 to WP5.22, each tag with its number, and every reference in the
tree, this record included, was rewritten to the new numbers, those made under the 3 November numbering mapped through
both renumberings (AL26). The text below is quoted in the new numbering. The plan's status read:

> **Status: in progress; WP5.01 to WP5.08 merged; WP5.09, the physics model, delivered, awaiting its merge; the shell packages WP5.15 to WP5.22 planned.**

The In brief read:

> ## In brief
>
> **What changes.** The program gains a browser workbench, combining molecular viewers and continuum modelling
> suites. Six library steps come first: protonation feeds the shape of the pore, a residue's charge can be changed, a
> project names and reuses its models, the reported quantities become a list that can grow, a case gains variables with
> units, and the physics (equations, salt, voltages) becomes a reusable model of its own. Then the screens: the frame,
> rebuilt on ready-made parts after the first look, then five suites, three that build models and two that use them,
> each designed on a working prototype with a real pore before it is built. Last come the guided route, the old desktop
> shell's removal, and the guide.
>
> **Cost.** About seven weeks for the library steps and thirteen to sixteen for the screens: five to six months
> part-time. Units bring one new library.
>
> **What could go wrong.** Protonation before the shape moves the pore's geometry; the reference cases keep the old way
> behind a switch, and the number checks would show any move. A formula could carry a wrong unit; each is checked
> against its field's and refused on a mismatch. The molecule viewer may redraw slower than 200 ms; it is timed on a
> computer with a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.
>
> **Your call.** Which settings exist beyond the four agreed sections, after the frame package's research. The colleague
> who tries the workbench is named by the close, as ruled.

WP5.09's entry opened and ended:

> **Delivered 8 November 2026** ([the plan](wp5.09-the-physics-model.md)). A third model kind,
>
> …
>
> the Study suite's list WP5.19's; REV-217 to REV-221 land next. Tag `v0.6.0-alpha.9`.

WP5.16's library step read:

> Library step first: stage 1's axis estimated from the channel cavity for a single-chain or mixed-chain pore, gated like
> the permutation axis, with §5.3.1 and VER-48 (REV-121; §8.2.24 Z5); a `prepare` command over `orient_pore` (REV-41).

WP5.17's library step ended:

> wall sizing moved into `mesh/` (REV-170; AD4), VER-62's mesh hash unmoved or the move ruled and re-pinned (G10, I4).

Two rows of *Verification* read:

> | WP5.16, Molecular | 1, 2 | REV-121's cavity axis against a known axis (VER-48); VER-78 |
> | WP5.17, Continuum | 1, 2 | VER-55 as restated; VER-62's mesh hash unmoved by REV-170; VER-78 |

## Amended 8 November 2026 (§8.2.36 AL28)

At WP5.10's plan, the author ruled that each plan is written in its phase's folder from the start, so that WP5.10's
move is the only one (AL28). WP5.10's entry read:

> The delivered plans archived by phase, the finished briefs and
> reviews under `archive/sessions/`, every link and written path rewritten, records included, and `/np-ship phase` moving a
> closing phase (AL5).

## Amended 9 November 2026 (§8.2.37 AM9)

At WP5.11's plan, the author ruled that WP5.11 also takes REV-222's four items (AM9), and the meaning changes AM1 to AM7
the entry now names. WP5.11's entry opened and ended:

> The findings filed under `specification/`, `.claude/`, `docs/plans/` and the root files. CON-05 and §2 name the mean
>
> …
>
> delivered narratives in this plan among them (AL17, AL18; REV-216). No test. Tag `v0.6.0-alpha.11`.

Its *Verification* row read:

> | WP5.11, the specification's text | none kept | VER-45; `clause.py` resolves every identifier; no SHALL, tolerance or default moves but AL9's wording |

## Amended 9 November 2026 (§8.2.37 AM12)

At WP5.11's plan review, the author ruled that the work's cost is stated in sessions, agent hours and the author's
touches, measured from each session's transcript (AM10, AM11), and that the live estimates are restated in them
(AM12). The In brief's cost line read:

> **Cost.** About seven weeks for the library steps, three and a half for the written knowledge and the tidying, and
> thirteen to sixteen for the screens: about six months part-time.

---

## 9 November 2026: the delivered entries leave the plan (§8.2.36 AL18; AUD-244)

The plan keeps each delivered entry's title, merged line and live constraints; the narratives follow verbatim, then the status line's dates, the settled rows of *Open decisions* and the supplied rows of *What the author supplies*.

### WP5.01 — Discovery and the design and requirements document (F5; S2 to S7, S11, S12)

**Merged** ([the plan](wp5.01-workbench-design-study.md)), delivered 27 October 2026.
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

**Merged** ([the plan](wp5.02-framework-spike.md); [the report](../../design/spike/report.md)), delivered 2 November 2026. The hard
screen, a residue and its charge on the pore map, was built twice over one FastAPI server and measured; both passed the
pre-set tests (front end 26 ms p95 for NiceGUI, 22 ms for React; install 86 MiB against 12 MiB), and the author ruled
**NiceGUI** (AF4; ADR-004's NOTE, the front end). The spikes left the tree. Landed in `src/nanopnp/gui/web/`: the
server and its contract (loopback, one ready line, a launch token, stops with its input; ADR-004's NOTE), `nanopnp gui`
with `--state` and `--dev`, the screen registry (`home`, `st-charge`), the states `empty`, `charged-tube`, `uncharged` and
`refused`, Mol* vendored unmodified. VER-78 passes in Chromium; `gate.sh run` and CI's tier-1 leg require the browser.
`/np-gui render shell` and the `nontext` measure ran; REV-137, REV-138, REV-141 and REV-143 are `fixed`. Live
constraints: the 200 ms line is unmeasured for the whole picture (Mol* alone takes about 800 ms on software GL; measure
on a GPU in the package that builds the first Study screen); a screen is ready only after Mol* has drawn; the lock holds
pdb2pqr is at 3.8 and the lock needs no override (REV-175); the study's mockups fail the non-text measure and stay as dated evidence (REV-176).
Tagged `v0.6.0-alpha.2` (S19).

Each library package lands its capability with its Tier 1 and 2 tests before any screen surfaces it (§8.1; RSK-15;
§8.2.17 S7), and each is planned by `/np-plan wp` (AD2, AD3; AG2). A shell package whose capability is not yet in the
library opens with that library step, tested, before its screens (AG1).

### WP5.03 — Protonation before the density (§8.2.19 U2; REV-135)

**Merged** ([the plan](wp5.03-protonation-before-the-density.md)), delivered 3 November 2026. Stage 7's `protonation` walks
after `structure` and before `density`, and stage 2 smears the protonated atoms of every frame, each with its CHARMM
radius through its residue's state patch, so a protonation state moves the density, the contour and the mesh.
`geometry.density.atoms: as_loaded` is the reference's way, a switch the manifest lists; the stage-2 key under it is
unchanged. The case schema is `nanopnp/case/v0.6`, and v0.5 is refused with its migration. `protonated` beside a
force field other than CHARMM is refused. PHY-16, FR-04, §5.2 and §5.3.1 are amended. Example 07 is re-pinned
(conductance 0.9734 → 0.9598 nS, −1.40 %; 6223 → 6059 elements); the 2WCD walks, VAL-05/06 and Tier 3 set
`as_loaded` and did not move. REV-135 is `fixed`; REV-180 (SWANSON and PEOEPB names) is deferred. Live constraint: only
the `X86_V3` and `AVX512_SPR` meshes of example 07 are folded. Tagged `v0.6.0-alpha.3`.

### WP5.04 — The charge mutator's library step (FR-38; §8.2.17 S4; §8.2.19 U6; §8.2.31 AG9 to AG11)

**Merged 3 November 2026** ([the plan](wp5.04-the-charge-mutators-library-step.md)). A case's `charge.edits` pin a
titratable residue's protonation state, change its net charge by an integer placed on its titratable group (AG9), or
scale its atom radii (AG10), at stage 7's `protonation` step on every chain and frame. The variant artefact carries its
parent table, and its record names the parent and every residue that differs; no edit is a deviation (AG11). Under the
protonated density a state or radius edit moves the wall too. Tier 1: a pin, a charge change and a radius scale each
change that residue alone; a case without edits keeps every key. A state is pinned by wrapping PDB2PQR's
`apply_pka_values`, and a gate refuses a frame that does not hold it. A charge or radius edit reuses the parent's
stored frames; a state edit protonates again. Live constraints: a pin can reposition a neighbour's hydrogens and
carboxyl oxygens through PDB2PQR's optimisation, so the variant's record lists such residues and tests match atoms by
identity; a radius scale below 1 can breach the kernel-spacing gate (REV-182). FR-38, PHY-16's NOTE, §5.2, §5.3.1 and
§5.3.3 are amended; the Charge edit tool is WP5.16's (AJ10). Tagged `v0.6.0-alpha.4`.

### WP5.05 — Named models and study overrides in the case (WB-11; FR-39; REV-62; §8.2.31 AG12, AG13)

**Merged 3 November 2026** ([the plan](wp5.05-named-models-and-study-overrides.md)). A case names a molecular and a
continuum model, each a file of its own schema (`nanopnp/molecular-model/v0.6`, `nanopnp/continuum-model/v0.6`) holding
only the keys its kind owns (`io/models.py:OWNERS`), and resolves into one complete case. A study overrides any value of
the models it names, each override recorded beside the model's value in the manifest (AG12); a study keys and equals its
resolved case, so it rebuilds only the stages an override moves. A sweep axis may range over the models (AG13); each
model is its own warm-start root. `inputs.mesh.artefact` names a stored mesh by its 64-character hash, and the mesh stage
takes the store (REV-62 `fixed`; REV-186 keeps a stored mesh beside a `structure:` refused). FR-39, IF-03, FR-25, FR-27,
§5.2, §5.3, §5.3.1, §5.3.3 and the design document's WB-16 are amended. Live constraints: `models` is outside every
dump and hash, so a plain reader refuses a case that names it; read it with `Case.load` or `load_case`. Tier 1 and Tier 2
tests cover the identity, the overrides, the sweep and the reuse. Tag `v0.6.0-alpha.5`.

### WP5.06 — Outputs and steric models as registries (MOD-09; §8.2.18 T4; §8.2.28 AD5; §8.2.32 AH1)

**Merged 4 November 2026** ([the plan](wp5.06-outputs-and-steric-registries.md)). The outputs (`post/outputs.py`) and
the steric models (`physics/steric.py`) are registries: a new quantity or crowding form is one registration, with no edit of
the case schema, stage 11 or a physics model. An output states what it needs of a declaration, transport or flow, and a
model provides every output whose need it meets (AH1), so `ModelDeclaration.quantities` and `io/case.py:OUTPUTS` are gone
and the shipped models provide what they did. Stage 11 builds one `Extraction` and calls each selected output, and
`QoIArtefact` takes `output_parameters`; `numerics/measures.py:require_boundary` is the one boundary-existence check
(AD5). A steric name other than `borukhov` enters the solve key as `electrolyte.steric_model`; no shipped key, golden or
case document moves (VER-56, VER-62). MOD-09 is `fixed`; REV-171's cost items stay in Phase 6. Live constraints: the
registering functions stay out of `PUBLIC` (REV-67). Tier 1 holds the evidence. Tag `v0.6.0-alpha.6`.

### WP5.07 — Variables and the rebuild forecast (FR-39; §8.2.19 U4; §8.2.31 AG2 to AG5; REV-139)

**Merged 4 November 2026** ([the plan](wp5.07-variables-and-the-rebuild-forecast.md)). A case defines `variables:`, each
a value with its unit or an expression of others. `io/variables.py` parses it from Python's syntax tree against a whitelist,
so no code runs, and converts through `pint` (`>=0.25.3,<0.26`, imported on first use) exactly, in fractions; a field's
unit is its name's suffix, and another dimension is refused at the field (AG2, AG3). A case resolves to numbers before any
stage is keyed, so `2*a` keys as its value and a case without variables keeps every key (AG4; VER-62 unmoved). A sweep axis
over `variables.<name>` moves every field the variable reaches. `sweep.forecast.forecast` and `Sweep.forecast()` key each
point's stages without running one and warn which stages an axis rebuilds and how many builds precede the solves (AG5;
VER-64); `sweep plan` prints it. Live constraints: the manifest gains `variables` only when a case has some; a
`Forecastable` stage hashes its own `forecast_parameters`; REV-197 (rectification over a bias set through a variable) is
WP5.19's (AJ10). REV-139 `fixed`. Tier 1 holds the evidence. Tag `v0.6.0-alpha.7`.

### WP5.08 — The frame and the project folder (FR-31, FR-32, FR-34, FR-35; REV-32, REV-52; MOD-13; §8.2.33 AI1, AI9 to AI14)

**Merged 5 November 2026** ([the plan](wp5.08-the-frame-and-the-project-folder.md)). `api.Project` keeps a plain folder
(`nanopnp/project/v0.6`, no physics): a case imports split into its two models and its study, named model files and inputs
brought along, copied or linked, and computes with every key but the first unchanged (AI9 to AI11); it exports as readable
files, and `Store.stale` lists an older release's entries (REV-32). `ContributesDeviations` joins the optional members the
walk tests by `isinstance` (REV-52; VER-64). `cli/` is split per command family, and `nanopnp gui` takes a project and
walks nothing (MOD-13). The frame is a command registry feeding the menus, the palette and rebindable shortcuts, the four
suites, the queue, the changed and problems lists, and settings with the user's themes (AI1, AI12); VER-78 loads ten
screens in four states, projects now, and drives them. Live constraints: a user's theme is not contrast-checked; a user's
project has an empty charge screen until WP5.19; the frame is rebuilt in WP5.15 (AJ1); the 3D background is the `--canvas-3d` token. REV-32, REV-52 `fixed`. Tag
`v0.6.0-alpha.8`.

### WP5.09 — The physics model (FR-32, FR-39; WB-34, WB-35; §8.2.34 AJ2, AJ3, AJ5)

**Merged 8 November 2026** ([the plan](wp5.09-the-physics-model.md)). A third model kind,
`nanopnp/physics-model/v0.6`, named by `models.physics`, owns `physics`, `electrolyte`, `boundary_conditions`,
`numerics.elements`, `numerics.stabilisation` and `numerics.wall_distance` (AJ3, AK1); the merge reads molecular,
continuum, then physics, and a continuum file holding a physics key is refused naming the physics model, with no
migration. Each model carries its exposed values, a default list per kind that a file's `exposes:` replaces, which
keys nothing (AJ5, AK3). A continuum model's `wall_h_nm: auto` follows the paired physics salt, pinned by
`wall_for_concentration_M` (AK2). A case imports into three models and a study, a sweep ranges over `models.physics`,
the manifest records the file, and the frame's rail lists physics models (FR-32, FR-39, FR-25). VER-62 unmoved
(at most 6.9 × 10⁻¹⁴). Live constraints: the Physics suite and its *Exposed values* tool are WP5.15 and WP5.18's,
the Study suite's list WP5.19's; REV-217 and REV-219 land in WP5.13, REV-220 and REV-221 in WP5.14, REV-218 in WP5.16
(AL22). Tagged `v0.6.0-alpha.9`.

### WP5.10 — The written knowledge's tools and rules (CODE_REVIEW_039; §8.2.36 AL3 to AL7, AL14, AL24, AL27, AL28)

**Delivered 9 November 2026** ([the plan](wp5.10-the-written-knowledges-tools-and-rules.md)). `docs/project/decisions.md`,
written by `.claude/scripts/decisions.py` from the records, lists 1,259 decisions with where each holds now; the
history index's list moved to `specification/history/holds-now.yaml` (AL3). The site's *Architecture* page is generated
(AL6). VER-79 checks §5.1's module rows against the subpackages, the page against the script and the YAML against the
ruling letters; the commit hook, the push gate and CI run `decisions.py --check`, and CI runs `links.py`. The core's
*Gate and push* re-runs `decisions.py` and `index_records.py` (AL4). Every plan sits in `docs/plans/phase-<n>/` or
`sessions/` (AL5, AL28). Ruff selects `C901` at 15 and `PLR0913` at 8, with 26 definitions under `noqa` (AL7). The
changelog's Phase 5 entries sit under their versions (AL14). The trial recommends neither xenon nor import-linter
([the concept](../../../knowledge/07-software-stack/25-complexity-and-import-contract-tools.md); AL27). Added by the
author the same day (D9 to D11): a `justfile`, run with `uv run just`; two switches,
`NANOPNP_AUTO_CHECKPOINT` and `NANOPNP_AUTO_SHIP`, under which a pause goes on and `.claude/hooks/checkpoint.sh`
carries its prompt across the next compaction (§8.4.4); and `/np-implement`'s task list, rebuilt from the ticks. Live
constraints: a commit that adds a decision re-runs `decisions.py`; open decision 14 is the author's. AUD-251 and
AUD-382 `fixed`. Tag `v0.6.0-alpha.10`.

The status line's dates:

> WP5.01 amended the same day (S21 to
S23); the library packages ordered on 1 November 2026 (§8.2.28 AD1 to AD5; [the record](phase-5-record.md)); WP5.02
planned and delivered on 2 November 2026 (§8.2.30 AF1 to AF4); the shell packages, the sweep's design round and
REV-136's cut line ruled on 3 November 2026 (§8.2.31 AG1 to AG7); WP5.05's overrides and model sweep ruled the same day (AG12,
AG13); what an output needs of a model ruled at WP5.06's plan on 4 November 2026 (§8.2.32 AH1); a user's colour themes ruled at WP5.08's plan on 5 November 2026 (§8.2.33 AI1); after the verdicts on WP5.08's frame, the frame's components, the physics model, the design loop and the packages WP5.09 and WP5.15 to WP5.22 ruled the same day (§8.2.34 AJ1 to AJ10); WP5.09's open points ruled at its plan on 6 November 2026 (§8.2.35 AK1 to AK3); the written knowledge's follow-up, the architecture clean-ups and the packages renumbered on 8 November 2026 (§8.2.36 AL1 to AL27); how the plans are filed and WP5.10's model ruled at its plan the same day (AL28, AL29); WP5.11's meaning changes, its open gaps and REV-222 ruled at its plan on 9 November 2026 (§8.2.37 AM1 to AM9); the cost's units ruled at its review the same day (AM10 to AM12)

The settled rows of *Open decisions*:

| # | Decision | Owner and status |
|---|---|---|
| 1 | The scope, the overlap, the slicing, the loop, the document, the install, the gate, the package names | **Settled by the author, 24 October 2026** (S1 to S20) |
| 2 | The front-end framework and server library | **Author**, from WP5.02's evidence (S8) |
| 3 | The inherited rows: REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114; `MOD-09`, `MOD-13`'s command-line part, `MOD-18` (H4, H10) | **Settled by the author, 27 October 2026** (§8.2.18 T1 to T5): MOD-09 brought into v0.6, the rest as WP5.01 proposed; `/np-plan amend 5` carries the owners |
| 4 | Whether the shell reads `plot/data.py` and retires its own plots | **Settled by WP5.01**: it does, and `gui/`'s duplicates retire with Qt (`docs/design/workbench.md`, *The shell's reading of artefacts*) |
| 6 | Which packages the first `/np-plan amend 5` plans, and their order | **Settled by the author, 1 November 2026** (§8.2.28 AD1 to AD5): the four library packages WP5.03 to WP5.06, after the spike; REV-170 with the Geometry tool, REV-121 with structure preparation |
| 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Settled by the author, 3 November 2026** (§8.2.31 AG1 to AG7): one package per suite after the frame; WP5.07 for the sweep's variables and forecast; the difference field in v0.6. The sequence is now AJ10's |
| 9 | The frame's components, the suites that build and use models, the physics model and its exposed values, `impeccable`'s role, the changed list, the design loop, the settings and the sequence (REV-211 to REV-215) | **Settled by the author, 5 November 2026** (§8.2.34 AJ1 to AJ10) |
| 11 | Where a model's exposed values are declared: the model file, or a default list per kind | **Settled by the author, 6 November 2026** (§8.2.35 AK3): a default list per kind, which a model file may replace |
| 12 | Which model owns `numerics.wall_distance`, and how a continuum model's Debye-sized wall mesh reads the physics model's concentration, or pins its own (`wall_for_concentration_M`) | **Settled by the author, 6 November 2026** (§8.2.35 AK1, AK2): the physics model; the mesh follows the paired salt unless pinned |
| 13 | The written knowledge's follow-up, where the six architecture clean-ups land, the order, the numbering and the measuring tools' trial (CODE_REVIEW_039; CODE_REVIEW_036) | **Settled by the author, 8 November 2026** (§8.2.36 AL1 to AL27) |

The supplied rows of *What the author supplies*:

| Item | Needed by | If it does not arrive |
|---|---|---|
| The workbench's areas | WP5.01's start | **Supplied 24 October 2026** (S24) |
| The framework ruling | WP5.02's end | **Supplied 2 November 2026** (AF4) |
| The answers to the sweep's design round and the cut line | The second `/np-plan amend 5` | **Supplied 3 November 2026** (AG1 to AG7) |
| Comments on the screens and mockups | WP5.01 | WP5.01 waits |
| Answers in the design round on organisation and look (S21) | WP5.01 | WP5.01 waits |
