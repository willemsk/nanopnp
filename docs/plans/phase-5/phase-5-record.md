# Phase 5 plan: the record

The text that amendments replaced in [the Phase 5 plan](phase-5-workbench.md), copied verbatim, one
dated section per amendment (§8.2.16 R4). Read it on demand; the plan states what holds now.

**Status: a record of replaced text, last added to on 21 November 2026 (§8.2.47); it states nothing that holds now.**

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

The second amendment, after WP5.02 merged: the shell cut one package per suite after the frame (WP5.08 and WP5.16 to WP5.28), the
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
the shell's packages renumbered WP5.09 and WP5.15 to WP5.28 (AJ1 to AJ10). The plan's status read:

> **Status: in progress; WP5.01 to WP5.07 merged; WP5.08 delivered, awaiting its merge; the shell packages WP5.16 to WP5.28 planned.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended the same day (S21 to

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
> ### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)
>
> Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
> either lacks the point (AG6). Then the results explorer and its tiles: a field drawn by `webgui` when its tile opens it,
> its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut. Probes and cuts are linked to their
> field, and a run to its result (FR-33). Comparison shows two runs side by side on one scale or as their difference.
> Q37 to Q41 move here. Tag `v0.6.0-alpha.21`.
>
> ### WP5.27 — The guided route, Qt's removal and documentation increment 5 (FR-36; REV-134; S13, S17)
>
> The guided route over the suites (FR-36). Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt
> widgets, the bundle and the packaging probe leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55,
> VER-60, CON-08, CON-09, CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1).
> The application guide is rewritten against the browser workflow with the rendered screens (§8.1's increment 5). Tag
> `v0.6.0-alpha.27`.
>
> ### WP5.28 — The close
>
> It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
> bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report, the changelog
> and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

Open decision 7, the GPU row of *What the author supplies*, and the verification rows read:

> | 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Settled by the author, 3 November 2026** (§8.2.31 AG1 to AG7): one package per suite after the frame, WP5.08 and WP5.16 to WP5.28; WP5.07 for the sweep's variables and forecast; the difference field in v0.6 |
> | A machine with a GPU, in a local session | WP5.19 | The 200 ms line stays unmeasured; a `REV-nn` row carries it to the close |
> | WP5.16, Molecular | 1, 2 | REV-121's cavity axis against a known axis (VER-48); VER-78 |
> | WP5.17, Continuum | 1, 2 | VER-55 as restated; VER-62's mesh hash unmoved by REV-170; VER-78 |
> | WP5.19, Study | 1 | VER-44 and VER-60 as restated; VER-78; the 200 ms measure (criterion 6) |
> | WP5.21, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; VER-78 |
> | WP5.27, route and Qt's removal; WP5.28, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; VER-78 |

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

> **Status: in progress; WP5.01 to WP5.08 merged; WP5.09, the physics model, delivered, awaiting its merge; the shell packages WP5.15 to WP5.28 planned.**

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

## Amended 9 November 2026 (§8.2.37 AM13 to AM16)

At WP5.12's plan, the author ruled that the sodium cap's test is tightened (AM13), that three ideas move to an open
item (AM14), and that the site's register links wait for WP5.27 (AM15); at its review, that the source checklist has
six rows (AM16). The *In brief* read: "Eight audit findings to check against the source papers, from a checklist."
The *What the author supplies* row read:

> | The eight-row checklist against the ESI and the COMSOL report (AL20) | WP5.12 | Each finding stays `unchecked`, a `REV-nn` row carried to the close |

WP5.12's entry read:

> The findings filed under `knowledge/` and `docs/`. The five concepts that state a method or rule wrongly are rewritten,
> AUD-339 first (AL15); `knowledge/01`'s overview says it backs §4 and §4 governs (AL16); the redundancy rows, the §6 and
> §4 mirrors in `knowledge/06` and `knowledge/01` first, each concept pointing at its clause (AL17); the sediment rows
> (AL18); each of the fifteen unsourced `[verified]` claims footnoted, marked "by arithmetic" or demoted (AL19); the guide
> says protonation runs before the density (AL13). The author receives an eight-row checklist of the findings that rest on
> the ESI or the COMSOL report and confirms or dismisses each (AL20). A finding left open becomes a `REV-nn` row. No test.
> Tag `v0.6.0-alpha.12`.

Its *Verification* row read:

> | WP5.12, the knowledge base | none kept | VER-45; `.claude/scripts/audit/markers.py` names no missing test; each `[verified]` claim names its source |

WP5.27's entry ended: "The application guide is rewritten against the browser workflow with the rendered screens
(§8.1's increment 5). Tag `v0.6.0-alpha.27`."

## Amended 9 November 2026 (§8.2.37 AM18)

After the plan's review, the author ruled that the implementing session asks the six checklist findings in one round and lands the confirmed
edits in WP5.12 (AM18). The *In brief* read: "Six audit findings to check against the source papers, from a checklist."
WP5.12's entry ended: "The author receives the six findings that rest on the ESI or the COMSOL report as a checklist and confirms or dismisses each (AL20; AM16); a finding left open becomes a `REV-nn` row. Tag `v0.6.0-alpha.12`." The *What the author supplies* row read:

> | The six-row checklist against the ESI and the COMSOL report (AL20; REV-227) | WP5.12 | Each finding stays `unchecked` in REV-227, carried to the close |

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

### WP5.11 — The specification's text and the agent instructions (§8.2.36 AL8 to AL12, AL14, AL16 to AL18, AL21; §8.2.37 AM1 to AM9)

**Delivered 9 November 2026** ([the plan](wp5.11-the-specifications-text-and-the-agent-instructions.md)). The 148
findings of CODE_REVIEW_039's lists and AUD-67 are fixed, with REV-216 and REV-222. §5.1's diagram draws the stage
registry's edges from stage 9; §5.2's stage cells name each stage and its requirement (AL10). §5.3.1's example is a
structure case and a supplied-mesh case, each validated; its stage behaviour moves to §5.2, the project to §5.3.5
(AL11, AL17). CON-05, CON-06, §5.4.1 and ADR-001 state the single NGSolve route (AL9, AL12); twelve passages of §4
and §6 follow the tested code (AM1); NUM-04 and NUM-28 carry REV-223 and REV-224's NOTEs (AM2). SHALLs 526 to 517,
each traced. The agent instructions state each procedure once; `.claude/workflow/author.md` holds the In brief and
the author's choices (AM9). The merged entries above keep their title, merged line and live constraints (AL18). Live
constraints: AL16 to AL18 and AL21 continue in WP5.12; REV-223 to REV-225 are Phase 6's. Tag `v0.6.0-alpha.11`.

The status line's dates:

> WP5.01 amended the same day (S21 to
S23); the library packages ordered on 1 November 2026 (§8.2.28 AD1 to AD5; [the record](phase-5-record.md)); WP5.02
planned and delivered on 2 November 2026 (§8.2.30 AF1 to AF4); the shell packages, the sweep's design round and
REV-136's cut line ruled on 3 November 2026 (§8.2.31 AG1 to AG7); WP5.05's overrides and model sweep ruled the same day (AG12,
AG13); what an output needs of a model ruled at WP5.06's plan on 4 November 2026 (§8.2.32 AH1); a user's colour themes ruled at WP5.08's plan on 5 November 2026 (§8.2.33 AI1); after the verdicts on WP5.08's frame, the frame's components, the physics model, the design loop and the packages WP5.09 and WP5.15 to WP5.28 ruled the same day (§8.2.34 AJ1 to AJ10); WP5.09's open points ruled at its plan on 6 November 2026 (§8.2.35 AK1 to AK3); the written knowledge's follow-up, the architecture clean-ups and the packages renumbered on 8 November 2026 (§8.2.36 AL1 to AL27); how the plans are filed and WP5.10's model ruled at its plan the same day (AL28, AL29); WP5.11's meaning changes, its open gaps and REV-222 ruled at its plan on 9 November 2026 (§8.2.37 AM1 to AM9); the cost's units ruled at its review the same day (AM10 to AM12)

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

## Amended 10 November 2026 (§8.2.38 AN3 to AN7)

At WP5.15's plan the author ruled the settings list, the store's clean-up in WP5.15, the compute settings in WP5.19 and a run's rebuild after a full clean-up in WP5.21; at the plan's review, the store's lock and the suite shortcuts (AN6, AN7). The three entries read:

> ### WP5.15 — The frame on Quasar's components (FR-31, FR-34; WB-33, WB-36 to WB-38; REV-203, REV-204, REV-207, REV-208, REV-210 to REV-214; §8.2.34 AJ1, AJ6 to AJ9)
>
> The frame rebuilt from the components NiceGUI ships through Quasar (AJ1): the application layout, the activity bar and
> the project rail as drawers, the bottom panel as the footer, the rail a tree with the project's name at its head and in
> the tab's title, the icon font, suites as sub-pages that keep the 3D view, and the tokens fed into Quasar's colour
> variables. Five suites in their *Build* and *Use* groups, Physics empty until WP5.18. The palette opens as one input and
> lists matches by title and keyword, one row active and moved by the arrow keys, a command that cannot run disabled with
> its reason (REV-208, REV-211). The settings are one declared list with a user and a project scope, a page with a
> searchable section list beside the panel, a *Modified only* filter, and REV-204's guards (AJ9; REV-212); the plan
> surveys how COMSOL, ParaView, ChimeraX and VS Code arrange their preferences, compute and network included, and puts the
> list to the author. The changed count opens the dense table grouped by model and study (AJ7; REV-214). The frame's
> landmarks, headings, live regions and splitter keys (REV-203's frame part), REV-207's efficiencies, and REV-210's icons,
> headings, dialogs and render states. A 2WCD render state, walked once and cached (AJ8). In `np-gui`, `impeccable`'s
> critique joins the review, its quality floor is read before a screen is built, and a design file derived from
> `tokens.css` is generated (AJ6). VER-78 over the new states. Tag `v0.6.0-alpha.15`.

> ### WP5.19 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; REV-205, REV-206, REV-209, REV-215; AG7)
>
> The prototype round on 2WCD settles the charge screen's design with its function (AJ8; REV-215). Overview of the three
> models; Study setup with each model's exposed values first and *More values* (AJ5) over the overrides of WP5.05; Sweep,
> with variables and the forecast's warning of WP5.07; Charge on the mesh, a residue and the charge map linked both ways,
> with its colour bar, axes and dark map (FR-33; REV-205, REV-209); Runs, a run's convergence unfolded in the queue, its
> record written into the project (REV-206). `upto` on reproduce (REV-41). The 200 ms redraw is measured on the author's
> machine with a GPU (AG7; criterion 6). Q24 to Q26 and Q28 to Q36 move here; VER-44 and VER-60 as restated. Tag
> `v0.6.0-alpha.19`.

> ### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)
>
> Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
> either lacks the point (AG6). Then, after the prototype round on 2WCD (AJ8), the results explorer and its tiles: a field
> drawn by `webgui` when its tile opens it, its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut.
> Probes and cuts are linked to their field, and a run to its result (FR-33). Comparison shows two runs side by side on
> one scale or as their difference. Q37 to Q41 move here. Tag `v0.6.0-alpha.21`.

## Amended 11 November 2026 (§8.2.39 AO1 to AO3)

At WP5.16's plan the author ruled that a pore's axis is found whatever the pore, chain groups and `axis: cavity`
included, all in WP5.16 (AO1); that the Prepare tool draws the axis and the membrane from typed values (AO2); and that
a variant is linked to its parent by default, with a full copy offered (AO3). The entry read:

> ### WP5.16 — The Molecular suite (FR-37, FR-38; REV-121; REV-41's `prepare`)
>
> Library steps first: stage 1's axis estimated from the channel cavity for a single-chain or mixed-chain pore, gated like
> the permutation axis, with §5.3.1 and VER-48 (REV-121; §8.2.24 Z5); a `prepare` command over `orient_pore` (REV-41);
> each atom's effective radius and residue index held by `ProtonationTable`, so the density reads scaled radii from one
> place (REV-218; CODE_REVIEW_036 candidate 4, D4.1, D4.2, C4.1, C4.2; AL22), VER-62 unmoved.
> Then the tools, opening with their prototype round on 2WCD (AJ8): Prepare structure, Ensemble, Protonation, Charge edit
> (FR-38's control over WP5.04's step) and View, the molecule drawn by Mol*, the molecular model's exposed values
> declared (AJ5). Q09, Q13 and Q27 move here. Tag `v0.6.0-alpha.16`.

## Amended 12 November 2026 (§8.2.40 AP1 to AP4)

At WP5.17's plan the author ruled that a supplied outline beside a structure runs with the structure's charge (AP1),
that a continuum model is built alone over a molecular model chosen in its pane (AP2), and that every part of a
generated mesh can be typed (AP3), each typed size a base the size scale multiplies (AP4). The entry read:

> ### WP5.17 — The Continuum suite (REV-170, REV-39; FR-33's geometry link)
>
> Library step first: one stage-5 region interface with an adapter per kind, the cylinder's two classes merged and the
> wall sizing moved into `mesh/` (REV-170; AD4; CODE_REVIEW_036 candidate 3, D3.1 to D3.4, C3.1, C3.2; AL22), MOD-03's
> edge gone from `modularity-layering.yaml` (VER-61), VER-62's mesh hash unmoved or the move ruled and re-pinned (G10, I4).
> Then, after the prototype round on 2WCD (AJ8), Protein geometry, Contour (on any profile, extracted or supplied, REV-39;
> its check off the interface's thread, asking before an edit is discarded, as T1 carries REV-56), Region, and Mesh with
> its quality selection; a geometry and its parameters linked both ways (FR-33). Q10 to Q12 and Q14 to Q23 move here;
> VER-55 as restated. Tag `v0.6.0-alpha.17`.

Its row of *Verification* read:

> | WP5.17, Continuum | 1, 2 | VER-55 as restated; VER-62's mesh hash unmoved by REV-170; MOD-03's edge gone (VER-61); VER-78 |

## Amended 13 November 2026 (§8.2.41 AQ1, AQ2)

At WP5.18's plan the author ruled that each Physics tool shows its physics model inside a study picked in the pane
(AQ1), and that choosing another registered model sets the switches it honours and removes the values it refuses
(AQ2). The entry read:

> ### WP5.18 — The Physics suite (FR-31; WB-34, WB-35; §8.2.34 AJ2 to AJ5)
>
> After the prototype round on example 01's NaCl case, NaCl being the only electrolyte a shipped correction file covers (AJ8): Equations, the registered model with its switches, element orders and
> stabilisation, and the composer's place with its later-phase banner (AJ4; FR-40 stays its phase); Electrolyte, the
> ions, the concentration, the parameter set and the corrections; Conditions, each boundary role's condition, the bias,
> the ground, the walls and the solid permittivities, a role picked in the (r, z) view of the open study's geometry or in
> the list; Exposed values, the physics model's declaration (AJ5). The guided route's salt step lands here. Tag
> `v0.6.0-alpha.18`.

## Amended 16 November 2026 (§8.2.42 AR3 to AR5)

At WP5.19's plan the author ruled that a solve's thread count is recorded and keys no result (AR3), that the package
adds *New study* and the study drawn as a graph (AR4), and that the charge check's reach against a shifted outline is
measured and stated rather than guarded by a new refusal (AR5). The entry read:

> ### WP5.19 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; REV-205, REV-206, REV-209, REV-215; AG7)
>
> The prototype round on 2WCD settles the charge screen's design with its function (AJ8; REV-215). Overview of the three
> models; Study setup with each model's exposed values first and *More values* (AJ5) over the overrides of WP5.05; Sweep,
> with variables and the forecast's warning of WP5.07; Charge on the mesh, a residue and the charge map linked both ways,
> with its colour bar, axes and dark map (FR-33; REV-205, REV-209); Runs, a run's convergence unfolded in the queue, its
> record written into the project (REV-206), and the Compute settings, solves at once and threads per solve, each run's
> record stating its thread count (AN1, AN4). `upto` on reproduce (REV-41). The 200 ms redraw is measured on the author's
> machine with a GPU (AG7; criterion 6). Q24 to Q26 and Q28 to Q36 move here; VER-44 and VER-60 as restated. Tag
> `v0.6.0-alpha.19`.

Its row of *Verification* read:

> | WP5.19, Study | 1 | VER-44 and VER-60 as restated; VER-78; the 200 ms measure (criterion 6) |

## Amended 18 November 2026 (§8.2.43 AS1 to AS4)

The fifth `/np-plan amend 5`, after WP5.19's merge, placed the two packages that §8.2.42 AR7 and AR8 had ruled: the
meso suite between Molecular and Continuum is WP5.20, the next package (AS1), and the performance package is WP5.22,
after the Analysis suite (AS2). The suite's name waits for its round (AS3). The planned packages were renumbered, the
Analysis suite from WP5.20 to WP5.21, the guided route from WP5.21 to WP5.23 and the close from WP5.22 to WP5.24, each
tag with its number, and every reference in the tree was rewritten, this record included, but for the sentences that
describe the 8 November renumbering (AS4). The text below is quoted in the new numbering. The plan's status read:

> **Status: in progress; WP5.01 to WP5.18 merged (`v0.6.0-alpha.18`); WP5.19, the Study suite, delivered for review, then WP5.21, WP5.27 and the close.** Written 24 October 2026, during Phase 4 (§8.2.17); amended since by the rounds the [history index](../../../specification/history/index.md) lists. Release: **v0.6** (`v0.6.0`).

The In brief read:

> ## In brief
>
> **What changes.** The program gains a browser workbench, combining molecular viewers and continuum modelling
> suites. Six library steps came first: protonation shapes the pore, a residue's charge can be edited, a project
> reuses named models, the outputs form a list that can grow, a case gains variables with units, and physics becomes a
> reusable model. Next, three packages correct the project's written knowledge where an audit found
> it adrift, and two tidy the library's insides without moving a result. Then the screens: the frame, rebuilt on
> ready-made parts, and five suites, three that build models and two that use them. Last come the guided route, the old desktop shell's removal, and the guide.
>
> **Cost.** Eleven packages remain: about 70 sessions, 60 to 120 hours of agent work and 110 times you act.
>
> **What could go wrong.** A formula could carry a wrong unit; each is checked against its field's and refused on a
> mismatch. A tidying could move a stored result; each checks every stored fingerprint, and a move is undone. The molecule
> viewer may redraw slower than 200 ms; it is timed on a computer with a graphics card, and if the viewer itself is the
> cost, the line applies to the workbench's own share.
>
> **Your call.** Whether to
> adopt either measuring tool the tools package tries, on its report. Six audit findings to check against the source
> papers, asked in one round during the knowledge package. The colleague who tries the workbench, named by the close.

WP5.19's live constraints began:

> Live constraints: AR7 moves the 200 ms line to a performance package (REV-258); AR8 puts Charge on the mesh in a
> bridge suite with its own package (REV-259). A recorded run picked in Runs is WP5.21's (REV-260); the review's polish
> is WP5.26's (REV-261); an exposed value's first name is the author's (REV-262). D12 goes to the author at `/np-ship`.

WP5.27's entry began:

> The guided route over the five suites (FR-36), with the keyboard pass over every canvas action (REV-203's remainder;

The GPU row of *What the author supplies* read:

> | A machine with a GPU, in a local session | A performance package (§8.2.42 AR7) | The 200 ms line stays unmeasured; REV-258 carries it to the close |

Criterion 6 read:

> 6. **The redraw is measured** on the author's machine with a GPU, in a performance package (§8.2.42 AR7; REV-258), not
>    WP5.19: a residue selected on the charge map
>    redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
>    whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
>    binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

## Amended 19 November 2026 (§8.2.44 AT1, AT2)

At WP5.20's plan the author ruled that the Outline tool marks the atoms an edit moves across the outline, each way
(AT1), and that REV-240's overlay is drafted for the suite's round and built in WP5.20 if kept (AT2). The entry read:

> ### WP5.20 — The meso suite (FR-31, FR-33; WB-43, WB-44; REV-259; REV-244's suite; §8.2.42 AR8; §8.2.43 AS1, AS3)
>
> A suite that builds, between Molecular and Continuum: the molecule reduced to the axisymmetric model, named at its round
> (AS3). Library steps first, as the shell computes nothing (VER-60): a point on the charge map names each residue once,
> its chains' copies on a C<sub>n</sub> structure together (REV-259's physics point), and the atoms an edited outline
> cuts, read in stage 1's frame and reduced to (r, z). Then, after the prototype round on 2WCD (AJ8), which takes
> REV-259's questions, the suite's name and REV-244's radius against z and vertex list: *Density*, stages 2 and 3, the
> grid, the kernel and the reduced map; *Outline*, stage 4's outline, created and edited, its saved edit a continuum
> model holding the outline (AP1), the two from Continuum › Pore geometry; *Charge map*, stage 7's charge on the mesh and
> its conservation checks, from Study › Charge on the mesh. Each pairs Mol*, side on and cut at the axis with *One
> subunit* (WB-44), with the (r, z) view, linked both ways: a residue finds its patch, a point its residue, an edited
> outline the atoms it cuts (FR-33). Its values stay the continuum model's `geometry` section over a molecular model picked
> in the pane; it adds no kind of model (AR8). Continuum keeps Region, Mesh and Exposed values; Study keeps Overview, Study
> setup, Sweep and Runs. FR-31's suites, §2's v0.6 row, §8.1's Phase 5 deliverable, WB-34 and WB-41 are amended
> (AR8). What names the tools' old places follows them: VER-78's suites in (a) and `/study/charge` in (m), the
> capability list's rows for Q14 to Q20 and Q24 to Q30, and `redraw.cjs`'s address. Q14 to Q20 and Q28 to Q30 move
> here; VER-60 as restated. Tag `v0.6.0-alpha.20`.

## Amended 19 November 2026, at WP5.20's plan's review (§8.2.44 AT3, AT4)

At the plan's review the author ruled that the study graph's charge node opens Charge map on the continuum model built
alone (AT3), which leaves the entry's text as it was, and that the overlay is drawn on a 0.2 nm grid with each atom's
charge spread over at least 0.4 nm (AT4). The entry's heading ended "§8.2.44 AT1, AT2)", and its library step read:

> and the deposit's charge on a 3D grid with
> its mean about the axis, for REV-240's overlay (AT2).

## Amended 19 November 2026, at WP5.21's plan (§8.2.45 AU1 to AU3)

At WP5.21's plan the author ruled that every plot is drawn by a borrowed chart library whose axes the user sets (AU1),
that any Matplotlib colour map is offered per map (AU2), and that Comparison's pair is two maps on one grid, switched
to two 3D field views on one range (AU3). The plan also took REV-260 and AN5's rebuild, which their rows placed in
WP5.21. The entry read:

> ### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)
>
> Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
> either lacks the point (AG6). Then, after the prototype round on 2WCD (AJ8), the results explorer and its tiles: a field
> drawn by `webgui` when its tile opens it, its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut.
> Probes and cuts are linked to their field, and a run to its result (FR-33). Comparison shows two runs side by side on
> one scale or as their difference. A run whose solution the store's clean-up removed rebuilds it when viewed (AN5). Q37 to Q41 move here. Tag `v0.6.0-alpha.21`.

## Amended 20 November 2026 (§8.2.46 AV1 to AV6)

The sixth `/np-plan amend 5`, after WP5.21's merge, gave every open review item a package. The tree of results that
WB-51 ruled before the performance package is WP5.22; the free list of layers is WP5.23, in every Mol* view, with
Prepare's typed view and an ensemble's variation colour (AV3); the library's refusals are WP5.25 (AV1); and the guided
route's package is split into a polish pass, WP5.26, and the route with new models, WP5.27 (AV2). The planned packages
were renumbered, the performance package from WP5.22 to WP5.24, the guided route from WP5.23 to WP5.27 and the close
from WP5.24 to WP5.28, each tag with its number, and every reference in the tree was rewritten, this record included,
but for the sentences that describe the 8 November and 18 November renumberings (AV4). An item owned by a later phase
names a provisional package (AV5), and the Copilot host's checks are its session plan's (AV6). The text below is quoted
in the new numbering. The plan's status read:

> **Status: in progress; WP5.01 to WP5.20 merged (`v0.6.0-alpha.19`, WP5.20's `v0.6.0-alpha.20` to be pushed); WP5.21, the Analysis suite, delivered (its pull request open); then a package for REV-268's tree of results, WP5.24, WP5.27 and the close.**

The In brief read:

> ## In brief
>
> **What changes.** The program gains a browser workbench, combining molecular viewers and continuum modelling
> suites. Six library steps came first, then three packages that corrected the written knowledge and two that tidied the
> library's insides. Then the screens: the frame, rebuilt on ready-made parts, and six suites, four that build models and two that use them. The sixth, added now, sits between the
> molecule and the continuum: it shows how the molecule becomes the pore's shape and charge, each picture beside the
> molecule. A performance package then times the screens on a graphics card. Last come the guided route, the old desktop
> shell's removal, and the guide.
>
> **Cost.** Five packages remain: about 19 sessions, 23 to 41 hours of agent work and 54 times you act, from the four
> suites measured, and one session of yours on a computer with a graphics card.
>
> **What could go wrong.** Moving three tools into the new suite could move a stored result; each move checks every
> stored fingerprint, and a move is undone. The molecule viewer may redraw slower than 200 ms; it is timed on a computer
> with a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.
>
> **Your call.** The new suite's name, at its design round. Recommendation: Meso, your word, naming a scale as its
> neighbours do. Whether to adopt either measuring tool the tools package tried; it recommends neither. The colleague who
> tries the workbench, named by the close.

WP5.21's entry ended:

> library chosen again, is a package before WP5.24 (REV-268), and the wording rule the author took is applied to sixteen strings, WP5.26 sweeping the rest (REV-269).

The route's and the close's entries read:

> ### WP5.27 — The guided route, Qt's removal and documentation increment 5 (FR-36; REV-134; S13, S17)
>
> The guided route over the six suites (FR-36), with the keyboard pass over every canvas action (REV-203's remainder;
> QR-16). Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt widgets, the bundle and the
> packaging probe leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55, VER-60, CON-08, CON-09,
> CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1). The application guide is
> rewritten against the browser workflow with the rendered screens (§8.1's increment 5), and the site's register pages
> link the plans and reviews it leaves out (REV-228; AM15). Tag `v0.6.0-alpha.27`.
>
> ### WP5.28 — The close
>
> It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
> bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report, the changelog
> and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

Open decision 15 read:

> | 15 | The meso suite's name: *Meso*, *Reduction*, *Bridge* or another | **Author**, at WP5.20's round (§8.2.43 AS3) |

The verdicts' row of *What the author supplies* read:

> | Verdicts on each suite's prototype round, on 2WCD or, for Physics, example 01 | WP5.16 to WP5.21 | The suite is built on the prototype's design as it stands, and the verdicts move to its screen review |

The live constraints that named an open item's owner read, for WP5.12:

> Live constraints: REV-228 is WP5.27's; REV-229 is after v1.0; REV-230 waits for the next change to the correction
> file; REV-231 and REV-232 are open.

For WP5.16:

> Live constraints: REV-240 carries an ensemble's variation view, colour maps beyond the two directions and one rule
> for safeguards; REV-235's and REV-237's other points wait for a later suite's round; the charge screen's redesign is
> WP5.19's (REV-209, REV-215); handles dragged in the 3D view are WP5.26's or later (REV-238).

For WP5.17:

> Live constraints: REV-244 carries a suite between Molecular and Continuum, the CAD tooling with the sketcher and
> subdivisions of a part for meshing; handles dragged on the canvas are WP5.26's; REV-242's other points wait for the
> new-model action and a pass over the stages' errors.

For WP5.18, in part:

> REV-255's pane layout; REV-253's tunable plots are the analysis suite's; REV-254's words, REV-255's (r, z) view and
> the boundaries picked for the wall distance are WP5.26's.

For WP5.20:

> Live constraints: a free list of the structure's layers is a package of its own, placed by the author (REV-265); the
> round's polish, Outline's keyboard path and the map's default share are WP5.26's (REV-266).

## 20 November 2026: the delivered entries WP5.12 to WP5.21 leave the plan (§8.2.36 AL18; CODE_REVIEW_066)

The plan keeps each delivered entry's title, merged line and live constraints, as it did for WP5.01 to WP5.11 on
9 November; the narratives follow verbatim, each package's scope as planned, then what it delivered.

### WP5.12 — The knowledge base and the guide (§8.2.36 AL13, AL15 to AL21; §8.2.37 AM13 to AM18)

**Merged 10 November 2026** ([the plan](wp5.12-the-knowledge-base-and-the-guide.md)); tag `v0.6.0-alpha.12`. 163 of CODE_REVIEW_039's findings fixed, filed under `knowledge/`, `docs/` and four `src/` modules: the
knowledge base states what was measured and verified, each `[verified]` claim names its source (AL19), and each rule
is stated once, in its clause (AL15 to AL18); `knowledge/01` backs §4, which governs (AL16); the guide states that
protonation runs before stage 2 (AL13); the sodium cap's test is tightened (AM13); REV-226's citations follow §5.2.
The author answered the six findings that rest on the ESI or the COMSOL report, and each edit landed (REV-227; AL20,
AM16, AM18). 517 SHALLs kept.

### WP5.13 — Case and model files (REV-217, REV-219; CODE_REVIEW_036 candidates 1 and 5; §8.2.36 AL22, AL23)

One reader pair, `read_case` and `read_case_text` in `io/models.py`, resolves `variables:` and `models:`, and `io/case.py`
keeps `validate_mapping` (D1.1; AL23, with §5.3.1 amended); `load_case` and `loads_case` stay the registry-checked seams
(D1.2); `substitute` takes `base` and applies swaps, variables, edits and rebasing in one pass, so `Case.with_` calls it
once (D1.3); input-file discovery, rebasing and rewriting live once in `io/case_paths.py` (D1.4); the `io` case modules
import one way (D1.5). `ModelFile` carries its validated body through a public `read_model_file` (D5.1); the case's
split into model layers moves into `io/models.py` and `mapping_changes` ignores metadata keys, so `api/project.py` parses
no model file again (D5.2). The designs and corrections C0 to C1.5 and C5.1 bind, re-read against WP5.09's code. VER-62
unmoved; no new layering edge (VER-61, VER-72). Tag `v0.6.0-alpha.13`.

**Merged 10 November 2026** ([the plan](wp5.13-case-and-model-files.md)); tag `v0.6.0-alpha.13`.
REV-217 and REV-219 fixed. One reader pair resolves `models:` and `variables:` (FR-39; AL23, §5.3.1 amended);
`substitute` rebases relative input paths beside the case in every branch, a model swap's included, so `Case.with_`
substitutes once (FR-25); `io/case_paths.py` holds the one input-path seam (FR-32); `ModelFile.body` carries the
checked body, `split_case_layers` serves the project's import, and `mapping_changes` skips metadata (FR-34). The
two substitution refusals say to write `models:` or `variables:` in the case file. Four tests added; the push gate
passed with the VER-62 walks unmoved and no new layering edge (VER-61, VER-72).

### WP5.14 — Sweep planning and the walk's keying (REV-221, REV-220; CODE_REVIEW_036 candidates 2 and 6; §8.2.36 AL22)

`build_plan` takes the base case in memory, and `plan_sweep` writes its two files once, with no staging directory
(D2.1); the resolved members are fields keyed on the directory they were resolved beside, so a moved plan never serves
stale ones (D2.2; REV-221, REV-199's regression); a member is reused where the plan holds it, and a pooled worker
resolves only its point and parent (D2.3); `Session._walk` and `Session._member` stay (D2.4). `_Walk` gains `keyed` and
`stored`, which `stored_upstream` and the forecast's walk share with the run, never building a workspace to key (D6.1);
`pipeline/forecast.py` moves into `pipeline/run.py` (D6.2). The designs and corrections C2.1 to C2.4 and C6.1 bind.
VER-62 unmoved; VER-64's forecast agrees with the walk. Tag `v0.6.0-alpha.14`.

**Merged 10 November 2026** ([the plan](wp5.14-sweep-planning-and-the-walks-keying.md)); tag `v0.6.0-alpha.14`. REV-220 and REV-221 fixed. `_Walk.keyed` and `_Walk.stored` key a stage and read the store for the run,
`stored_upstream` and the forecast, which moved into `pipeline/run.py`; `stored_upstream` keys a session's own stages
(FR-27, VER-64). A plan holds its members keyed on their directory and resolves them again where it moves;
`plan_sweep` plans in memory and writes its files once; a point and its parent are taken where the plan holds them
(FR-39, §5.3.4 amended). A three-point sweep resolves its members six times, where the plan counted thirteen. Three tests added and one extended;
the push gate and example 03 passed with the VER-62 walks unmoved and no new layering edge (VER-61, VER-72).

### WP5.15 — The frame on Quasar's components (FR-27, FR-31, FR-34; WB-33, WB-36 to WB-38; REV-203, REV-204, REV-207, REV-208, REV-210 to REV-214; §8.2.34 AJ1, AJ6 to AJ9; §8.2.38 AN2, AN3, AN5 to AN7)

The frame rebuilt from the components NiceGUI ships through Quasar (AJ1): the application layout, the activity bar and
the project rail as drawers, the bottom panel as the footer, the rail a tree with the project's name at its head and in
the tab's title, the icon font, suites as sub-pages that keep the 3D view, and the tokens fed into Quasar's colour
variables. Five suites in their *Build* and *Use* groups, their shortcuts following the bar (AN7), Physics empty until WP5.18. The
palette opens as one input and lists matches by title and keyword, one row active and moved by the arrow keys, a command that cannot run disabled with
its reason (REV-208, REV-211). The settings are one declared list with a user and a project scope, a page with a
searchable section list beside the panel, a *Modified only* filter, and REV-204's guards (AJ9; REV-212). The list is
AN3's, a registry that a later package or a plugin extends (AN2). The store gains its size cap and two clean-up
actions, one for what no run uses and one for every result, each entry removed whole and none while a run in any program holds the store (AN5, AN6; §5.3.2's NOTE). The changed count opens the dense table grouped by model and study (AJ7; REV-214). The frame's
landmarks, headings, live regions and splitter keys (REV-203's frame part), REV-207's efficiencies, and REV-210's icons,
headings, dialogs and render states. A 2WCD render state, walked once and cached (AJ8). In `np-gui`, `impeccable`'s
critique joins the review, its quality floor is read before a screen is built, and a design file derived from
`tokens.css` is generated (AJ6). VER-78 over the new states. Tag `v0.6.0-alpha.15`.

**Delivered 10 November 2026** ([the plan](wp5.15-the-frame-on-quasars-components.md)); merged 11 November 2026 as
`v0.6.0-alpha.15`. REV-203's frame part, REV-204, REV-207, REV-208 and REV-210 to REV-214 fixed. The frame is Quasar's layout with
sub-pages and one Mol* host (VER-78 (m)); five suites in two groups, Alt+Shift+1 to 5 following the bar (AN7); the rail
a tree headed by the project's name; the palette Quasar's searchable select over each command and setting; the
settings one registry with a user and a project scope and a page at `/settings` (VER-78 (j) to (l); §5.3.5's NOTE); the
changed values one dense table with units (FR-34). The store marks reads, evicts the least recently read outside a
kept set, caps itself and refuses a clean-up while a walk in any program holds its lock (FR-27, §5.3.2's NOTE; VER-62
unmoved). The render set adds a cached 2WCD project and REV-210's states; `np-gui` runs `impeccable`'s critique and
derives `DESIGN.md` (AJ6).

### WP5.16 — The Molecular suite (FR-37, FR-38; REV-121; REV-41's `prepare`; REV-218; §8.2.39 AO1 to AO3)

Library steps first: stage 1's axis found whatever the pore, from the ring of chains or of chain groups (`A+B,C+D,…`)
under C2 and above and from the channel's empty space under C1, `axis: cavity` asking for the channel's axis on any
pore and `axis: z` checked against whichever axis applies, with §5.2, §5.3.1 and VER-48 (REV-121; §8.2.24 Z5; AO1); a
`prepare` command over `orient_pore`, which also takes a typed axis (REV-41); each atom's effective radius and residue
index held by `ProtonationTable`, so the density reads scaled radii from one place (REV-218; CODE_REVIEW_036 candidate
4, D4.1, D4.2, C4.1, C4.2; AL22), VER-62 unmoved; a model built alone, keyed as a study's walk keys it; and a molecular
model's variant, linked to its parent by default or a full copy (AO3). Then the tools, opening with their prototype
round on 2WCD (AJ8): Prepare structure, the axis and the membrane drawn from typed values (AO2), Ensemble, Protonation,
Charge edit (FR-38's control over WP5.04's step) and View, the molecule drawn by Mol*, the molecular model's exposed
values declared (AJ5). Q09, Q13 and Q27 move here. Tag `v0.6.0-alpha.16`.

**Delivered 11 November 2026** ([the plan](wp5.16-the-molecular-suite.md)); merged 12 November 2026 as
`v0.6.0-alpha.16`. REV-121, REV-218,
REV-231, REV-234 and REV-239 fixed; REV-41's `prepare` landed, its `upto` still WP5.19's. Stage 1 finds a pore's axis
from its ring of chains or chain groups, or from the channel's empty space, and checks `axis: z` against it (VER-48;
§5.2, §5.3.1); `nanopnp prepare` and `orient_pore` take a typed axis and write a record; atom radii and residue
indices are held in one place (VER-62 unmoved). A model is built alone with a study's keys, and a molecular model's
variant is linked to its parent or a full copy (FR-38, FR-39; §5.3.1). The five tools stand at `/molecular/<tool>`
beside the one 3D view, drawn from MolViewSpec scenes (VER-78 (a), (m), (n)). At the prototype round the author
ruled, and the package built: a pane left of its view on every screen, positive charge blue with a setting, the
settings as a window over the tool, the folded bar as icons with state, and the channel's straightness limit a warning
(§8.2.39 AO4; WB-39).

### WP5.17 — The Continuum suite (REV-170, REV-39; FR-33's geometry link; §8.2.40 AP1 to AP4)

Library steps first: one stage-5 region interface with an adapter per kind, the cylinder's two classes merged and the
wall sizing moved into `mesh/` (REV-170; AD4; CODE_REVIEW_036 candidate 3, D3.1 to D3.4, C3.1, C3.2; AL22), MOD-03's
edge gone from `modularity-layering.yaml` (VER-61), VER-62's mesh hash unmoved or the move ruled and re-pinned (G10, I4);
a supplied outline beside a structure run with the charge deposited from its protonation, stages 2 to 4 skipped (AP1);
a continuum model built alone over a molecular model chosen in its pane and 0.15 M NaCl (AP2); and every part of a
generated mesh typed, each size a base the size scale multiplies (AP3, AP4). Then, after the prototype round on 2WCD
(AJ8), Protein geometry, Contour (on any profile, extracted or supplied, REV-39; its check off the interface's thread,
asking before an edit is discarded, as T1 carries REV-56; its saved edit a continuum model holding the outline), Region,
and Mesh with its quality selection, each drawn in an (r, z) view; a geometry and its parameters linked both ways
(FR-33). Q10 to Q12 and Q14 to Q23 move here; VER-55 as restated. Tag `v0.6.0-alpha.17`.

**Delivered 12 November 2026** ([the plan](wp5.17-the-continuum-suite.md)); merged 13 November 2026 as
`v0.6.0-alpha.17`. REV-170 and REV-39 fixed, REV-56's
workbench part done, REV-242's keying measured and cached. Stage 5's two kinds of region share `RegionOutlines` and the
`Stage5Region` protocol, the cylinder is `CylinderPore` alone and the wall is sized in `mesh/`, MOD-03's edge gone and
VER-62 unmoved (VER-61). A supplied outline runs beside its structure's charge (AP1; VER-55), a continuum model builds
alone over a chosen molecular model at 0.15 M NaCl (AP2; FR-39), and the generated mesh's parts take typed sizes (AP3,
AP4; VER-53). After the prototype round on 2WCD the author merged Contour into *Pore geometry*, had Region draw and pick
each domain, and chose a tree of the mesh's parts (WB-41); the three tools stand at `/continuum/<tool>` beside one (r, z)
canvas, a geometry and its parameters linked both ways (FR-33; VER-78).

### WP5.18 — The Physics suite (FR-31; WB-34, WB-35; §8.2.34 AJ2 to AJ5; §8.2.41 AQ1, AQ2)

After the prototype round on example 01's NaCl case, NaCl being the only electrolyte a shipped correction file covers (AJ8): Equations, the registered model with its switches, element orders and
stabilisation, and the composer's place with its later-phase banner (AJ4; FR-40 stays its phase), a change of model
setting the switches it honours and removing the values it refuses, with a note and *Undo* (AQ2); Electrolyte, the ions,
the concentration, the parameter set and the corrections; Conditions, each boundary role's condition, the bias, the
ground, the walls and the solid permittivities, a role picked in the (r, z) view or in the list; Exposed values, the
physics model's declaration (AJ5). Each tool shows its model inside a study picked in the pane, the study's own physics
values left out, or over the project's continuum model where it holds no study (AQ1). The guided route's salt step
lands here. Tag `v0.6.0-alpha.18`.

**Delivered 16 November 2026** ([the plan](wp5.18-the-physics-suite.md)). Each registered model states its terms in
LaTeX, from the PHY or NUM clause each comes from, and `role_conditions` each boundary's conditions with either side
grounded (VER-56; PHY-09). `Project.physics_case` shows a physics model inside a study (AQ1), `choose_physics` sets a
model's switches with an undo (AQ2), and `set_exposed` names and ranges an entry (FR-39). After the prototype round on
example 01 ([the record](../../design/reviews/2026-11-16-physics.md); AJ8) the four tools stand at `/physics/<tool>`:
Equations drawn by KaTeX (vendored, its digests checked as Mol*'s; CON-09), Electrolyte's two graphs with the driver
on a square-root axis, Conditions over stage 5's region with the mesh on request, and Exposed values (FR-31; VER-78).
The library's refusals follow ASD-STE100 (FR-35's NOTE), and the status colours gain blue for information (WB-42).

### WP5.19 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; REV-205, REV-206, REV-209, REV-215, REV-247; AG7; AP5; §8.2.42 AR3 to AR5)

The prototype round on 2WCD settles the charge screen's design with its function (AJ8; REV-215). Overview of the three
models; Study setup with each model's exposed values first and *More values* (AJ5) over the overrides of WP5.05, as a
form and as a graph, and *New study*, pairing three of the project's models (AR4); Sweep, with variables and the
forecast's warning of WP5.07; Charge on the mesh, a residue and the charge map linked both ways, with its colour bar,
axes and dark map (FR-33; REV-205, REV-209); Runs, a run's convergence unfolded in the queue, its record written into
the project (REV-206), and the Compute settings, solves at once and threads per solve, each run's record stating its
thread count, which keys no result (AN1, AN4; AR3). `upto` on reproduce (REV-41). A supplied outline's exclusion shell
takes the outline's own spacing (AP5); the charge check's reach against a shifted outline is measured and stated
(REV-247; AR5). The 200 ms redraw is timed headless by `redraw.cjs`; its GPU measurement and the front end's fix move to
WP5.24, the performance package (AR7; criterion 6; REV-258). Q24 to Q26 and Q28
to Q36 move here; VER-44 and VER-60 as restated. Tag `v0.6.0-alpha.19`.

**Delivered 18 November 2026** ([the plan](wp5.19-the-study-suite.md)); merged 18 November 2026 as
`v0.6.0-alpha.19`. `Project.new_study`, `set_study_value`,
`set_variable` and `study_values` set a study, its exposed values first (FR-39 (a); AG12). A sweep pairs a bias set
through a variable by its resolved value (VER-36). A run states its thread count, which keys nothing (FR-25; AR3).
`reproduce --upto` stops at a stage (QR-08; VER-35). A supplied outline shells at its own spacing, held between
0.025 and 0.05 nm (VER-59; AP5, AR6, D12). The charge check's reach against a shifted outline is measured (AP1; AR5).
After the round on 2WCD ([the record](../../design/reviews/2026-11-18-study.md); WB-43 to WB-48), the five Study tools
stand at `/study/<tool>`: Overview, Study setup with its graph and *New study*, Sweep in two modes, Charge on the mesh
linking a residue and the map both ways (FR-33; VER-60), and Runs drawing a run's convergence (VER-44). Every Build
suite has Exposed values (VER-78).

### WP5.20 — The meso suite (FR-31, FR-33; WB-43, WB-44; REV-259; REV-244's suite; REV-240's overlay; §8.2.42 AR8; §8.2.43 AS1, AS3; §8.2.44 AT1 to AT4)

A suite that builds, between Molecular and Continuum: the molecule reduced to the axisymmetric model, named at its round
(AS3). Library steps first, as the shell computes nothing (VER-60): a point on the charge map names each residue once,
its chains' copies on a C<sub>n</sub> structure together (REV-259's physics point); the atoms an edit moves across
the outline, each way, read in stage 1's frame and reduced to (r, z) (AT1); and the deposit's charge on a 3D grid with
its mean about the axis, smoothed to 0.4 nm for the picture, for REV-240's overlay (AT2, AT4). Then, after the prototype round on 2WCD (AJ8), which takes
REV-259's questions, the suite's name and REV-244's radius against z and vertex list: *Density*, stages 2 and 3, the
grid, the kernel and the reduced map; *Outline*, stage 4's outline, created and edited, its saved edit a continuum
model holding the outline (AP1), the two from Continuum › Pore geometry; *Charge map*, stage 7's charge on the mesh and
its conservation checks, from Study › Charge on the mesh, with REV-240's overlay drafted for the round and built if
kept: the charge in 3D and its mean about the axis, each as isosurfaces over the structure (AT2). Each pairs Mol*, side on and cut at the axis with *One
subunit* (WB-44), with the (r, z) view, linked both ways: a residue finds its patch, a point its residue, an edited
outline the atoms it moves (FR-33; AT1). Its values stay the continuum model's `geometry` section over a molecular model picked
in the pane; it adds no kind of model (AR8). Continuum keeps Region, Mesh and Exposed values; Study keeps Overview, Study
setup, Sweep and Runs. FR-31's suites, §2's v0.6 row, §8.1's Phase 5 deliverable, WB-34 and WB-41 are amended
(AR8). What names the tools' old places follows them: VER-78's suites in (a) and `/study/charge` in (m), the
capability list's rows for Q14 to Q20 and Q24 to Q30, and `redraw.cjs`'s address. Q14 to Q20 and Q28 to Q30 move
here; VER-60 as restated. Tag `v0.6.0-alpha.20`.

**Delivered 19 November 2026** ([the plan](wp5.20-the-meso-suite.md)); merged 19 November 2026. Meso, the second Build suite, holds Density,
Outline and Charge map at `/meso/<tool>`, each Mol* side on and cut at the axis beside the (r, z) view (FR-31; WB-43,
WB-44; VER-78). A point of the charge map names a residue once, its copies together, and a point of the density the
residues whose atoms reach it first (`ResidueCharges`, `DensityAtoms`; VER-60; AT1). An edited outline lists and marks
the residues it moves into the water and into the protein (`ResidueAtoms.moved`; AT1). The charge map is the continuum
model's own walk to stage 7 (`Project.charge_case`; FR-27). The charge in 3D and its mean about the axis are drawn over
the molecule, smoothed to 0.4 nm (`charge_volumes`; AT2, AT4). After the round on 2WCD ([the
record](../../design/reviews/2026-11-19-meso.md); WB-49) the map's scale opens on the 99th percentile of the charge's
size, through a dark middle on the dark theme, and each tool sets how Mol* draws the structure.

### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30, REV-253, REV-260; AG6; AN5; §8.2.45 AU1 to AU3)

Library steps first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
either lacks the point (AG6); a comparison as a project item; a run whose solution the store's clean-up removed,
rebuilt on request and checked against its record (AN5); each rung's reporting and tolerance kept with its Newton
history, so a recorded run's convergence is drawn in Runs (REV-260). Every plot moves to uPlot, vendored, its axes set
by the user (AU1; REV-253), and any Matplotlib colour map is offered per map (AU2). Then, after the prototype round on
2WCD (AJ8), the results explorer and its tiles: a field drawn as a map with its axial cut and probes, or on its mesh by
`webgui` when its tile opens it, its scene written once (REV-28, REV-30); the I–V; the quantities. Probes and cuts are
linked to their field, and a run to its result (FR-33). Comparison shows two runs side by side on one scale, as maps or
switched to the mesh, or as their difference (AU3). Q37 to Q41 move here. Tag `v0.6.0-alpha.21`.

**Delivered 20 November 2026** ([the plan](wp5.21-the-analysis-suite.md)); merged 20 November 2026. Analysis, the sixth suite, holds the results
explorer and Comparison at `/analysis/<tool>` (FR-31; VER-78 (a), (o)). The explorer draws a run's field as a map on the
pore's close-up, its scale on the 99th percentile, with a cut and probes linked to it, an outline, or in 3D on its mesh
on the map's range, framed on the pore; its I–V and recorded quantities (Q37 to Q41; FR-33; VER-44). Comparisons are
project items, drawn as their difference, side by side, mirrored or in 3D (FR-32; AG6; AU3). Every plot is a uPlot
chart whose axes the user sets, any Matplotlib map per map (AU1, AU2; REV-253). A cleaned run is solved again and
checked (AN5); a solve records its fields' norms, which a reproduction compares (QR-08; REV-264). After the round on
2WCD ([the record](../../design/reviews/2026-11-20-analysis.md); WB-50 to WB-52) a tree of results, with the chart
library chosen again, is WP5.22 (REV-268), and the wording rule the author took is applied to sixteen strings, WP5.26
sweeping the rest (REV-269).

## Amended 21 November 2026 (§8.2.47 AW1 to AW6)

The seventh `/np-plan amend 5`, after WP5.22's design round and its verdicts, placed the early close the author ruled
that day (REV-272). Phase 5 keeps WP5.27, cut to Qt's removal with a short guide (AW3), and WP5.28, the close, under
their numbers (AW4). The tree of results (WP5.22), the layers (WP5.23), the performance package (WP5.24), the library's
refusals (WP5.25), the polish pass (WP5.26) and WP5.27's guided route with new models moved to Phase 6, named there by
scope (AW1); those numbers are retired, and the text below keeps them. QR-10's trial was postponed to a v1.0 release
candidate (AW2), so criterion 5, open decision 8 and the colleague's supply row left the plan; criterion 6 and the
GPU's supply row moved with the performance package. The plan kept its length, its word target restated at Phase 6's
cleanup (AW5; REV-271), and open decision 14 closed with neither tool adopted (AW6). The plan's status read:

> **Status: in progress; WP5.01 to WP5.21 merged (`v0.6.0-alpha.19`; WP5.20's and WP5.21's tags, `v0.6.0-alpha.20` and `v0.6.0-alpha.21`, to be pushed); next WP5.22, the tree of results, its design round held on 21 November (WB-54 to WB-63); then WP5.23 the layers, WP5.24 performance, WP5.25 the refusals, WP5.26 the polish pass, WP5.27 the route and WP5.28 the close.** Written 24 October 2026, during Phase 4 (§8.2.17); amended since by the rounds the [history index](../../../specification/history/index.md) lists. Release: **v0.6** (`v0.6.0`).

The In brief read:

> ## In brief
>
> **What changes.** The program gains a browser workbench of molecular and continuum suites. Library steps came first,
> then the frame and six suites, four that build models and two that use them. Every point the reviews left open now has
> a package. Seven remain: results arranged as an editable tree, as COMSOL arranges them; a free list of display layers in every molecule view; the screens' speed, timed on a
> graphics card; every library message written plainly, leading to its field; a polish pass over every
> suite's open points, its words and its keyboard use; the guided route, with models created in the workbench, the old
> desktop shell's removal and the guide; and the close.
>
> **Cost.** Seven packages: about 36 sessions, 44 to 73 hours of agent work and 70 times you act, from the suites
> measured, and one session of yours on a computer with a graphics card.
>
> **What could go wrong.** A rewritten message could lose the value or the remedy it names; each keeps the rule, the
> value, the case path and the remedy, and no stored result moves. The molecule viewer may redraw slower than 200 ms; it
> is timed on a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.
>
> **Your call.** How are results arranged, and which chart library draws them? *Recommendation:* settle both at the
> tree's design round, on drawn screens, as each suite was. Who tries the workbench unaided? *Recommendation:* name the
> colleague before the close, which records the trial. When do the Copilot app's checks run? *Recommendation:* before
> the close; otherwise it carries them on.

*Context*'s question and gate read:

> Phase 5 answers one question: **can a nanopore experimentalist with no Python run a case unaided in a
> workbench that a method developer also wants to use?** Its gate is §8.1's, as S13 states it.

The *Design decisions* rows read:

> | The join between the scales | A meso suite between Molecular and Continuum holding Density, Outline and Charge map, built next; the 200 ms line in a performance package after Analysis | Each suite follows one scale; one pass measures the finished views (AR7, AR8; §8.2.43 AS1, AS2) |
> | The last packages | The tree of results, then the layers in every Mol* view, before the performance package; then the library's refusals, a polish pass over every suite, and the route with new models, Qt's removal and the guide | The performance package times the finished views; each pull request reviews one kind of change; every open item names a package (WB-51; §8.2.46 AV1 to AV5) |

The entries of the planned packages read:

> ### WP5.22 — The tree of results (FR-32, FR-33; WB-51, WB-53; REV-268, REV-270; §8.2.46 AV4)
>
> Its design round comes first: `/np-gui grill` puts the tree to the author on 2WCD (§8.4.4), with REV-268's questions: the
> tree's nodes (a run or a comparison as data, groups of plots, probes in a pane of their own, the quantities shown, the
> cut), the plot types a group takes (a surface, contours, arrows, a line along a cut, a scatter, the I–V, WB-53's true
> 3D view), how a variable or a constant is defined and where the library computes it (QR-13), how the tree is saved
> in the project (FR-32), how it meets the link rulings (WB-06), and the chart library every plot uses, chosen again
> (AU1; NiceGUI ships Plotly and ECharts). Library steps first: a field read at a point by its cell's own P2 basis, of
> `ln c` on a logarithmic branch, so a map, a cut and a probe read the solved field (REV-270); then what the round
> rules. Then the tree replaces the explorer's tiles, with REV-268's review points: the tiles' layout, the quantities'
> order and words, a run named by sight, a map framed on its data at equal aspect, *Mirrored* the model of a two-run
> view. Tag `v0.6.0-alpha.22`.
>
> The round ran on 21 November 2026 ([the record](../../design/reviews/2026-11-21-tree.md); WB-54 to WB-63): COMSOL's
> branches, a comparison a Data node of one `results.yaml` per project; one plot group or two side by side; every plot
> type of the round's board P1; Plotly for every chart and every (r, z) view, in this package, so Meso's, Continuum's
> and Physics' views move here with a round of verdicts, and uPlot, the canvas and `webgui` leave (CON-09's `webgui`
> sentence with it); definitions from a library list or typed, evaluated by the library; the tables in the bottom panel;
> *Shown run* following the newest; default plot groups; *Mirrored* first; a run labelled or named by what differs.
>
> ### WP5.23 — The structure's layers in every Mol* view (FR-31, FR-33; WB-49; REV-265, REV-243, REV-240; §8.2.46 AV3)
>
> A free list of layers draws the structure in Molecular's View and Prepare and in Meso's Density, Outline and Charge
> map. Each layer chooses what it draws (everything, a chain, the charged residues, the residues the tool is about, a
> residue by name), its style (MolViewSpec's cartoon, backbone, putty, ball and stick, spheres or surface), its colour
> and its opacity; the residues a tool is about are Charge map's pick with its copies, Density's named residues and
> Outline's moved ones (WB-49). Library step first: each residue's variation over an ensemble's aligned frames, a colour
> a layer can take (REV-240; QR-13). Prepare's view draws a typed tilt, azimuth, flip and centre before *Save prepared
> structure* (REV-243; AO2). A round of verdicts on 2WCD (§8.4.4); Mol* ships unmodified (CON-09). Tag
> `v0.6.0-alpha.23`.
>
> ### WP5.24 — The performance package (WB-23; REV-258; §8.2.31 AG7; §8.2.42 AR7; §8.2.43 AS2)
>
> First, `redraw.cjs` gains the timing of the tree of results' field and plot views beside its charge-map picks. Then, in a local
> session of the author's, on a machine with a GPU, `redraw.cjs --headed` times on 2WCD a residue picked on the meso
> suite's charge map redrawing the whole picture (WB-23; criterion 6), with WP5.23's layers, and the tree's views. The front end's share is then
> fixed, one keyed walk per pick first, the route reusing the pane's read (REV-258), and timed again; each miss left is
> profiled with `--trace`. Where the renderer's own repaint is the cost, the line binds the front end's share and the
> renderer's time is recorded (AG7). No stored key moves (VER-62). Tag `v0.6.0-alpha.24`.
>
> ### WP5.25 — The library's refusals (FR-35's NOTE; QR-12; REV-254, REV-242; §8.2.46 AV1)
>
> Every refusal and diagnostic left in `mesh/`, `geometry/`, `charge/`, `density/`, `structure/`, `numerics/`, `solve/`,
> `post/`, `sweep/`, `physics/`, `materials/`, `symmetry/`, `core/` and `api/` beyond `project.py`, and the command line's
> messages, follow FR-35's NOTE: the rule, the value, the case path and the
> remedy, in ASD-STE100. A refusal carries its case path and its file as fields, so `gui/web/tools.py:_plain`,
> `api/project.py:_error_path` and `gui/web/physics_tools.py:problem_path` read the fields, and a refusal opens its field
> by its path, never by its words (REV-242's fourth point). The suites' own words go to WP5.26's sweep. No number and no
> stored key moves (VER-62). Tag `v0.6.0-alpha.25`.
>
> ### WP5.26 — The polish pass: every suite's open points, the words and the keyboard (QR-16; WB-52; REV-203's remainder; REV-235 to REV-237, REV-241, REV-245, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269; §8.2.46 AV2)
>
> A round on 2WCD opens it (§8.4.4), with the choices the rows leave to the author: an exposed value's first name and its
> list (REV-262), a variable's unit box (REV-263), the charge map's default share and *One subunit*'s overlay (REV-266),
> the project dialogs, the settings' rows and spacing, the menus, the palette's look, and the Glossary as a help page
> from one source (REV-235 to REV-237). Then every suite's open review points: the panes' layout, the canvases' labels
> and keys, colours, numbers and units (REV-241, REV-245, REV-255's view and its region, REV-261, REV-266, REV-267), the
> Study suite's efficiencies (REV-263), and Region's domains read from the region artefact's faces, not cut in the shell
> (REV-245; VER-60), library step first. The keyboard pass over every canvas action, with handles dragged on the (r, z)
> canvas and Outline's vertex path (REV-203's remainder, REV-236, REV-266; QR-16). The wording rule swept over every
> screen, with a check that flags its patterns (REV-269; WB-52), and the suites' own words under FR-35's NOTE (REV-254).
> Tag `v0.6.0-alpha.26`.
>
> ### WP5.27 — The guided route, new models, Qt's removal and documentation increment 5 (FR-36; REV-134, REV-228, REV-240, REV-241, REV-242, REV-249; S13, S17; §8.2.46 AV2)
>
> Library step first: a new model of each kind from the project tree, a molecular model's first structure written as one
> block, a new physics model's corrections, and what an import makes of a full copy's parent (REV-242's first two points,
> REV-249, each put to the author at the plan); a PQR model opened as a structure (REV-241). An action that deletes asks a
> second step (REV-240's safeguards; WB-32). Then the guided route over the six suites from an empty project (FR-36).
> Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt widgets, the bundle and the packaging probe
> leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55, VER-60, CON-08, CON-09, CON-11, ADR-004's
> packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1). The application guide is rewritten
> against the browser workflow with the rendered screens (§8.1's increment 5), and the site's register pages link the
> plans and reviews it leaves out (REV-228; AM15). Tag `v0.6.0-alpha.27`.
>
> ### WP5.28 — The close
>
> It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
> bundle are gone with the capability list covered, orders the tool phases (S7), carries any Copilot check not yet run
> (REV-166 to REV-168; AV6), hands the open items' provisional Phase 6 packages to `/np-plan phase 6` (AV5), and writes
> the report, the changelog and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

*Open decisions* read:

> ## Open decisions
>
> | # | Decision | Owner and status |
> |---|---|---|
> | 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |
> | 8 | Who observes QR-10 | **Author**, by the close (S24) |
> | 14 | Whether xenon or import-linter is adopted | **Author**, on WP5.10's report (AL7, AL27), [delivered](../../../knowledge/07-software-stack/25-complexity-and-import-contract-tools.md): it recommends neither |
> | 16 | The tree of results: its nodes, its plot types and its chart library | **Settled** at WP5.22's design round, 21 November 2026 (WB-54 to WB-63) |
> | 17 | An exposed value's first name, a variable's unit box, the charge map's default share | **Author**, at WP5.26's round (REV-262, REV-263, REV-266) |
> | 18 | A new physics model's corrections, and what an import makes of a full copy's parent | **Author**, at WP5.27's plan (REV-242, REV-249) |
>
> Settled rows: see §8.2.17 to §8.2.46 and [the record](phase-5-record.md); decision 15, the meso suite's name, kept as
> *Meso* at WP5.20's round ([the record](../../design/reviews/2026-11-19-meso.md); AS3).

*What the author supplies* read:

> ## What the author supplies
>
> | Item | Needed by | If it does not arrive |
> |---|---|---|
> | Verdicts at each design round: each suite's prototype on 2WCD or, for Physics, example 01; the tree of results; the layers; the polish pass | WP5.16 to WP5.23, WP5.26 | The package is built on the drafts as they stand, and the verdicts move to its screen review |
> | A machine with a GPU, in a local session | WP5.24 (§8.2.42 AR7; §8.2.43 AS2) | The 200 ms line stays unmeasured; REV-258 carries it to the close |
> | A local Claude Code session | WP5.02 onward | Work continues headless, on renders |
> | Verdicts on the six findings against the ESI and the COMSOL report, asked in one round at WP5.12's item 11 (AL20; AM18; REV-227) | WP5.12 | A finding not yet checked stays `unchecked` in REV-227, carried to the close |
> | The verdict on xenon and import-linter (AL27) | After WP5.10 | Neither is added; the layering test stays the guard |
> | An experimentalist new to nanopnp | The close | QR-10 is waived and carried (S13) |
> | A session in the Copilot app on a WSL host (REV-166 to REV-168) | Before the close (§8.2.46 AV6) | The close carries the three checks to Phase 6; the gate is run by hand on Copilot meanwhile |
> | Merges; tags a session cannot push | Each package | The session prints the commands |

The *Verification* rows of the planned packages read:

> | WP5.22, the tree of results | 1 | A field read at a point by its cell's P2 basis: exact on a quadratic field, a logarithmic branch read as `exp` of the solved `ln c` (REV-270); the tree saved with the project and read back (FR-32); VER-78 |
> | WP5.23, the layers | 1 | A residue's variation over aligned frames against a hand-computed set; Mol* unmodified (CON-09); VER-78 over each Mol* view's layers |
> | WP5.24, performance | 1 | VER-62 and VER-78 unmoved by the pick path's fix; criterion 6, timed by `redraw.cjs --headed` on a GPU |
> | WP5.25, the refusals | 1 | VER-62 unmoved; a mesh gate's refusal, raised in a Tier 1 test, carries its case path and file as fields (a numerical gate, N1); VER-78's `refused` state holds a refusal WP5.25 rewrites and opens its field by that path; `_plain`, `_error_path` and `problem_path` read the fields, not the words, checked at review (N3) |
> | WP5.26, the polish pass | 1 | VER-60 as restated, Region's domains read from the artefact; QR-16's keyboard path over each canvas; the wording check (REV-269); VER-78 |
> | WP5.27, route and Qt's removal; WP5.28, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; a new model of each kind resolves and keys as an imported one (FR-32); VER-78 |

Criteria 5 and 6 read:

> 5. **QR-10 is observed**: the colleague installs, loads a structure, accepts defaults and obtains a
>    conductance and a field picture unaided. Predicted: met, with findings. A miss is waived and
>    carried (S13).
> 6. **The redraw is measured** on the author's machine with a GPU, in WP5.24, the performance package (§8.2.42 AR7;
>    §8.2.43 AS2; REV-258): a residue selected on the meso suite's charge map redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
>    whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
>    binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

The *End-of-phase report* read:

> The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
> against the browser shell; VER-78's screen and state counts; the time from a click to a redrawn
> view on the reference charged case and the install's time on a clean machine, each re-run by the
> command WP5.02 names; and the tool phases' order.

## Amended 21 November 2026, at WP5.27's plan (§8.2.47 AW9 to AW11)

WP5.27's plan checked rows Q01 to Q41 against the browser shell's code and put what it found to the author. The package
gains run progress and the run log (AW9), *More values* over every setting without a field (AW10) and the contributed
deviations (FR-25); five details are carried by REV-274 (AW11). Its entry read:

> ### WP5.27 — Qt's removal and the short guide (REV-134, REV-228; S13, S17; §8.2.47 AW1, AW3)
>
> Every row Q01 to Q41 is checked present in the browser workbench as it stands (criterion 3; the design document's
> *Tabs or areas*, whose rows Q37 to Q41 name WP5.21's explorer until the tree, and Q16 a vertex moved by typed values, AW7);
> a miss keeps Qt. Then PySide6, the Qt widgets, the bundle and the packaging probe leave, with `gui/app.py`,
> `case_model.py`, `scene.py`, the `nanopnp-gui` script and the
> Qt-only halves of `gui/geometry.py` and `gui/charge.py`, the halves the browser shell imports staying (the
> [survey](../../project/architecture-survey.md)'s inventory); its plan rules on `io/manifest.py`'s `PySide6` row. The server gains the self-test the restated clauses ask
> in the probe's place, which the code lacks today, run by CI on the three platforms (VER-43, VER-44, VER-55; ADR-004's
> packaging NOTE; RSK-13); and the restated NOTEs of IF-09, P3, QR-10, VER-43,
> VER-44, VER-55, VER-60, CON-08, CON-09, CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5).
> REV-134 closes (U1). The guide's desktop pages leave, and a short application guide says how to start the workbench and
> what each of the six suites does, with about one rendered screen a suite (AW3; §8.1's increment 5); the site's register
> pages link the plans and reviews (REV-228; AM15). No number and no stored key moves (VER-62). Tag `v0.6.0-alpha.27`.

Criterion 3 read:

> 3. **Every Qt shell capability is in the browser shell**, checked against WP5.01's list before Qt
>    leaves. A miss keeps Qt.

