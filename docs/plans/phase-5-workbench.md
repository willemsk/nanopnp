# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: in progress; WP5.01 to WP5.08 merged; the physics model's library step WP5.09 and the shell packages WP5.10 to WP5.17 planned.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended the same day (S21 to
S23); the library packages ordered on 1 November 2026 (§8.2.28 AD1 to AD5; [the record](phase-5-record.md)); WP5.02
planned and delivered on 2 November 2026 (§8.2.30 AF1 to AF4); the shell packages, the sweep's design round and
REV-136's cut line ruled on 3 November 2026 (§8.2.31 AG1 to AG7); WP5.05's overrides and model sweep ruled the same day (AG12,
AG13); what an output needs of a model ruled at WP5.06's plan on 4 November 2026 (§8.2.32 AH1); a user's colour themes ruled at WP5.08's plan on 5 November 2026 (§8.2.33 AI1); after the verdicts on WP5.08's frame, the frame's components, the physics model, the design loop and the packages WP5.09 to WP5.17 ruled the same day (§8.2.34 AJ1 to AJ10); WP5.09's open points ruled at its plan on 6 November 2026 (§8.2.35 AK1 to AK3). Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a browser workbench, combining molecular viewers and continuum modelling
suites. Six library steps come first: protonation feeds the shape of the pore, a residue's charge can be changed, a
project names and reuses its models, the reported quantities become a list that can grow, a case gains variables with
units, and the physics (equations, salt, voltages) becomes a reusable model of its own. Then the screens: the frame,
rebuilt on ready-made parts after the first look, then five suites, three that build models and two that use them,
each designed on a working prototype with a real pore before it is built. Last come the guided route, the old desktop
shell's removal, and the guide.

**Cost.** About seven weeks for the library steps and thirteen to sixteen for the screens: five to six months
part-time. Units bring one new library.

**What could go wrong.** Protonation before the shape moves the pore's geometry; the reference cases keep the old way
behind a switch, and the number checks would show any move. A formula could carry a wrong unit; each is checked
against its field's and refused on a mismatch. The molecule viewer may redraw slower than 200 ms; it is timed on a
computer with a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.

**Your call.** Which settings exist beyond the four agreed sections, after the frame package's research. The colleague
who tries the workbench is named by the close, as ruled.

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
| Front end | NiceGUI over FastAPI; Mol* draws the molecule | The spike's evidence (S8; AF4) |
| The shell's slicing | The physics model's library step; the frame rebuilt on Quasar's components; then one package per suite in the route's order | The case settles before a screen is built on it; each pull request reviews one suite's screens (AG1; AJ1, AJ10) |
| The sweep | Variables as values or expressions, units through `pint`, keyed by the values they resolve to; rebuilds forecast as a warning | The author's design round (AG2 to AG5) |
| The cut line | FR-31 to FR-39 and the comparison's difference field in v0.6; the rest later, as tagged | REV-136 (AG6) |
| Working loop | Artifact mockups; a live local loop; `/np-gui` renders, reviews and collects verdicts; each suite prototyped on 2WCD before it is built; `impeccable` a tool inside `np-gui` | Both see and control it (S9, S22; AJ6, AJ8) |
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

**Merged** ([the plan](wp5.02-framework-spike.md); [the report](../design/spike/report.md)), delivered 2 November 2026. The hard
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
§5.3.3 are amended; the Charge edit tool is WP5.11's (AJ10). Tagged `v0.6.0-alpha.4`.

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
WP5.14's (AJ10). REV-139 `fixed`. Tier 1 holds the evidence. Tag `v0.6.0-alpha.7`.

### WP5.08 — The frame and the project folder (FR-31, FR-32, FR-34, FR-35; REV-32, REV-52; MOD-13; §8.2.33 AI1, AI9 to AI14)

**Merged 5 November 2026** ([the plan](wp5.08-the-frame-and-the-project-folder.md)). `api.Project` keeps a plain folder
(`nanopnp/project/v0.6`, no physics): a case imports split into its two models and its study, named model files and inputs
brought along, copied or linked, and computes with every key but the first unchanged (AI9 to AI11); it exports as readable
files, and `Store.stale` lists an older release's entries (REV-32). `ContributesDeviations` joins the optional members the
walk tests by `isinstance` (REV-52; VER-64). `cli/` is split per command family, and `nanopnp gui` takes a project and
walks nothing (MOD-13). The frame is a command registry feeding the menus, the palette and rebindable shortcuts, the four
suites, the queue, the changed and problems lists, and settings with the user's themes (AI1, AI12); VER-78 loads ten
screens in four states, projects now, and drives them. Live constraints: a user's theme is not contrast-checked; a user's
project has an empty charge screen until WP5.14; the frame is rebuilt in WP5.10 (AJ1); the 3D background is the `--canvas-3d` token. REV-32, REV-52 `fixed`. Tag
`v0.6.0-alpha.8`.

### WP5.09 — The physics model (FR-32, FR-39; WB-34, WB-35; §8.2.34 AJ2, AJ3, AJ5)

Library step, no screens. A third kind of model, `nanopnp/physics-model/v0.6`, named by `models.physics`: the ownership
table of §5.3.1's `models:` NOTE gives it `physics` (the registered model, its switches and the solid permittivities),
`electrolyte`, `boundary_conditions`, `numerics.elements` and `numerics.stabilisation`, and leaves the continuum model the
geometry, the region and the mesh; the study keeps the Newton, continuation and linear-solver settings (AJ3). AJ3 places
neither `numerics.wall_distance`, the wall-distance field the corrections read, nor the coupling of `numerics.mesh`'s
`wall_h_nm: auto` to the electrolyte's Debye length; the author ruled both at the package's plan: the physics model
owns the wall-distance field, and a continuum model's mesh follows the paired physics model's concentration unless
`wall_for_concentration_M` pins it (§8.2.35 AK1, AK2). A case
imports split into three models and a study, a project gains `models/physics/`, a sweep may range over
`models.physics`, and the manifest records the physics model (FR-32, FR-39; §5.3.2, §5.3.3). Every model declares the
values it exposes, each with its name, case path, unit, range and default (AJ5): a default list per kind, which a model
file's `exposes:` replaces (AK3). A study resolves to the case it resolved to before: VER-62's
keys unmoved, and a case naming no model unchanged. Tag `v0.6.0-alpha.9`.

### WP5.10 — The frame on Quasar's components (FR-31, FR-34; WB-33, WB-36 to WB-38; REV-203, REV-204, REV-207, REV-208, REV-210 to REV-214; §8.2.34 AJ1, AJ6 to AJ9)

The frame rebuilt from the components NiceGUI ships through Quasar (AJ1): the application layout, the activity bar and
the project rail as drawers, the bottom panel as the footer, the rail a tree with the project's name at its head and in
the tab's title, the icon font, suites as sub-pages that keep the 3D view, and the tokens fed into Quasar's colour
variables. Five suites in their *Build* and *Use* groups, Physics empty until WP5.13. The palette opens as one input and
lists matches by title and keyword, one row active and moved by the arrow keys, a command that cannot run disabled with
its reason (REV-208, REV-211). The settings are one declared list with a user and a project scope, a page with a
searchable section list beside the panel, a *Modified only* filter, and REV-204's guards (AJ9; REV-212); the plan
surveys how COMSOL, ParaView, ChimeraX and VS Code arrange their preferences, compute and network included, and puts the
list to the author. The changed count opens the dense table grouped by model and study (AJ7; REV-214). The frame's
landmarks, headings, live regions and splitter keys (REV-203's frame part), REV-207's efficiencies, and REV-210's icons,
headings, dialogs and render states. A 2WCD render state, walked once and cached (AJ8). In `np-gui`, `impeccable`'s
critique joins the review, its quality floor is read before a screen is built, and a design file derived from
`tokens.css` is generated (AJ6). VER-78 over the new states. Tag `v0.6.0-alpha.10`.

### WP5.11 — The Molecular suite (FR-37, FR-38; REV-121; REV-41's `prepare`)

Library step first: stage 1's axis estimated from the channel cavity for a single-chain or mixed-chain pore, gated like
the permutation axis, with §5.3.1 and VER-48 (REV-121; §8.2.24 Z5); a `prepare` command over `orient_pore` (REV-41).
Then the tools, opening with their prototype round on 2WCD (AJ8): Prepare structure, Ensemble, Protonation, Charge edit
(FR-38's control over WP5.04's step) and View, the molecule drawn by Mol*, the molecular model's exposed values
declared (AJ5). Q09, Q13 and Q27 move here. Tag `v0.6.0-alpha.11`.

### WP5.12 — The Continuum suite (REV-170, REV-39; FR-33's geometry link)

Library step first: one stage-5 region interface with an adapter per kind, the cylinder's two classes merged and the
wall sizing moved into `mesh/` (REV-170; AD4), VER-62's mesh hash unmoved or the move ruled and re-pinned (G10, I4).
Then, after the prototype round on 2WCD (AJ8), Protein geometry, Contour (on any profile, extracted or supplied, REV-39;
its check off the interface's thread, asking before an edit is discarded, as T1 carries REV-56), Region, and Mesh with
its quality selection; a geometry and its parameters linked both ways (FR-33). Q10 to Q12 and Q14 to Q23 move here;
VER-55 as restated. Tag `v0.6.0-alpha.12`.

### WP5.13 — The Physics suite (FR-31; WB-34, WB-35; §8.2.34 AJ2 to AJ5)

After the prototype round on example 01's NaCl case, NaCl being the only electrolyte a shipped correction file covers (AJ8): Equations, the registered model with its switches, element orders and
stabilisation, and the composer's place with its later-phase banner (AJ4; FR-40 stays its phase); Electrolyte, the
ions, the concentration, the parameter set and the corrections; Conditions, each boundary role's condition, the bias,
the ground, the walls and the solid permittivities, a role picked in the (r, z) view of the open study's geometry or in
the list; Exposed values, the physics model's declaration (AJ5). The guided route's salt step lands here. Tag
`v0.6.0-alpha.13`.

### WP5.14 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; REV-205, REV-206, REV-209, REV-215; AG7)

The prototype round on 2WCD settles the charge screen's design with its function (AJ8; REV-215). Overview of the three
models; Study setup with each model's exposed values first and *More values* (AJ5) over the overrides of WP5.05; Sweep,
with variables and the forecast's warning of WP5.07; Charge on the mesh, a residue and the charge map linked both ways,
with its colour bar, axes and dark map (FR-33; REV-205, REV-209); Runs, a run's convergence unfolded in the queue, its
record written into the project (REV-206). `upto` on reproduce (REV-41). The 200 ms redraw is measured on the author's
machine with a GPU (AG7; criterion 6). Q24 to Q26 and Q28 to Q36 move here; VER-44 and VER-60 as restated. Tag
`v0.6.0-alpha.14`.

### WP5.15 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)

Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
either lacks the point (AG6). Then, after the prototype round on 2WCD (AJ8), the results explorer and its tiles: a field
drawn by `webgui` when its tile opens it, its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut.
Probes and cuts are linked to their field, and a run to its result (FR-33). Comparison shows two runs side by side on
one scale or as their difference. Q37 to Q41 move here. Tag `v0.6.0-alpha.15`.

### WP5.16 — The guided route, Qt's removal and documentation increment 5 (FR-36; REV-134; S13, S17)

The guided route over the five suites (FR-36), with the keyboard pass over every canvas action (REV-203's remainder;
QR-16). Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt widgets, the bundle and the
packaging probe leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55, VER-60, CON-08, CON-09,
CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1). The application guide is
rewritten against the browser workflow with the rendered screens (§8.1's increment 5). Tag `v0.6.0-alpha.16`.

### WP5.17 — The close

It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report, the changelog
and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | The scope, the overlap, the slicing, the loop, the document, the install, the gate, the package names | **Settled by the author, 24 October 2026** (S1 to S20) |
| 2 | The front-end framework and server library | **Author**, from WP5.02's evidence (S8) |
| 3 | The inherited rows: REV-20, -28, -30, -31, -32, -39, -41, -45, -52, -56, -62, -65, -67, -114; `MOD-09`, `MOD-13`'s command-line part, `MOD-18` (H4, H10) | **Settled by the author, 27 October 2026** (§8.2.18 T1 to T5): MOD-09 brought into v0.6, the rest as WP5.01 proposed; `/np-plan amend 5` carries the owners |
| 4 | Whether the shell reads `plot/data.py` and retires its own plots | **Settled by WP5.01**: it does, and `gui/`'s duplicates retire with Qt (`docs/design/workbench.md`, *The shell's reading of artefacts*) |
| 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |
| 6 | Which packages the first `/np-plan amend 5` plans, and their order | **Settled by the author, 1 November 2026** (§8.2.28 AD1 to AD5): the four library packages WP5.03 to WP5.06, after the spike; REV-170 with the Geometry tool, REV-121 with structure preparation |
| 7 | The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate | **Settled by the author, 3 November 2026** (§8.2.31 AG1 to AG7): one package per suite after the frame; WP5.07 for the sweep's variables and forecast; the difference field in v0.6. The sequence is now AJ10's |
| 8 | Who observes QR-10 | **Author**, by the close (S24) |
| 9 | The frame's components, the suites that build and use models, the physics model and its exposed values, `impeccable`'s role, the changed list, the design loop, the settings and the sequence (REV-211 to REV-215) | **Settled by the author, 5 November 2026** (§8.2.34 AJ1 to AJ10) |
| 10 | Which settings exist beyond the four sections, compute and network among them | **Author**, at WP5.10's plan, from its survey of comparable tools (AJ9) |
| 11 | Where a model's exposed values are declared: the model file, or a default list per kind | **Settled by the author, 6 November 2026** (§8.2.35 AK3): a default list per kind, which a model file may replace |
| 12 | Which model owns `numerics.wall_distance`, and how a continuum model's Debye-sized wall mesh reads the physics model's concentration, or pins its own (`wall_for_concentration_M`) | **Settled by the author, 6 November 2026** (§8.2.35 AK1, AK2): the physics model; the mesh follows the paired salt unless pinned |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Comments on the screens and mockups | WP5.01 | WP5.01 waits |
| Answers in the design round on organisation and look (S21) | WP5.01 | WP5.01 waits |
| The workbench's areas | WP5.01's start | **Supplied 24 October 2026** (S24) |
| The framework ruling | WP5.02's end | **Supplied 2 November 2026** (AF4) |
| The answers to the sweep's design round and the cut line | The second `/np-plan amend 5` | **Supplied 3 November 2026** (AG1 to AG7) |
| Verdicts on each suite's prototype round on 2WCD | WP5.11 to WP5.15 | The suite is built on the prototype's design as it stands, and the verdicts move to its screen review |
| A machine with a GPU, in a local session | WP5.14 | The 200 ms line stays unmeasured; a `REV-nn` row carries it to the close |
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
| WP5.03, protonation before the density | 1, 2 | U2's Tier 1 test; VER-49's radii; VER-62: example 07 re-pinned, every other walk unmoved (AG8) |
| WP5.04, the mutator's library step | 1 | FR-38's Tier 1 tests: a pin, a charge change and a radius scale change that residue alone; no key moves without edits (VER-62) |
| WP5.05, named models | 1, 2 | FR-39's reuse and rebuild-only-what-moved, the overrides recorded, the sweep over models; the schema's identifier (G6) |
| WP5.06, the registries | 1, 2 | MOD-09; AH1's provided outputs equal the old lists; FR-23 and QR-04's route cross-check unchanged; VER-56's keys and VER-62 unmoved |
| WP5.07, variables and the forecast | 1 | FR-39: the whitelist, the dimension check, unchanged keys without variables (VER-62), the forecast against the walk |
| WP5.08, the frame | 1 | VER-78's frame states; the project folder's export read back; REV-52's protocol members |
| WP5.09, the physics model | 1, 2 | FR-39: a study resolves and keys as before with three models (VER-62 unmoved); a case imports into three models and a study; every case leaf has one owner; a sweep over `models.physics` |
| WP5.10, the frame | 1 | VER-78's frame states over the fixture cases (the 2WCD state is the render set's, walked and cached by `/np-gui`, not a Tier 1 walk); a setting declared once reaches the page, its search, the palette and its file |
| WP5.11, Molecular | 1, 2 | REV-121's cavity axis against a known axis (VER-48); VER-78 |
| WP5.12, Continuum | 1, 2 | VER-55 as restated; VER-62's mesh hash unmoved by REV-170; VER-78 |
| WP5.13, Physics | 1 | A physics model edited in the suite resolves to the case it shows; VER-78 |
| WP5.14, Study | 1 | VER-44 and VER-60 as restated; VER-78; the 200 ms measure (criterion 6) |
| WP5.15, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; VER-78 |
| WP5.16, route and Qt's removal; WP5.17, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; VER-78 |

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
6. **The redraw is measured** on the author's machine with a GPU, in WP5.14: a residue selected on the charge map
   redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
   whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
   binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

## End-of-phase report

The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
against the browser shell; VER-78's screen and state counts; the time from a click to a redrawn
view on the reference charged case and the install's time on a clean machine, each re-run by the
command WP5.02 names; and the tool phases' order.
