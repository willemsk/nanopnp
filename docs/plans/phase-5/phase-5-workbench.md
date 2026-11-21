# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: in progress; WP5.01 to WP5.21 merged (`v0.6.0-alpha.19`; WP5.20's and WP5.21's tags, `v0.6.0-alpha.20` and `v0.6.0-alpha.21`, to be pushed); next WP5.22, the tree of results, its design round held on 21 November (WB-54 to WB-63); then WP5.23 the layers, WP5.24 performance, WP5.25 the refusals, WP5.26 the polish pass, WP5.27 the route and WP5.28 the close.** Written 24 October 2026, during Phase 4 (§8.2.17); amended since by the rounds the [history index](../../../specification/history/index.md) lists. Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a browser workbench of molecular and continuum suites. Library steps came first,
then the frame and six suites, four that build models and two that use them. Every point the reviews left open now has
a package. Seven remain: results arranged as an editable tree, as COMSOL arranges them; a free list of display layers in every molecule view; the screens' speed, timed on a
graphics card; every library message written plainly, leading to its field; a polish pass over every
suite's open points, its words and its keyboard use; the guided route, with models created in the workbench, the old
desktop shell's removal and the guide; and the close.

**Cost.** Seven packages: about 36 sessions, 44 to 73 hours of agent work and 70 times you act, from the suites
measured, and one session of yours on a computer with a graphics card.

**What could go wrong.** A rewritten message could lose the value or the remedy it names; each keeps the rule, the
value, the case path and the remedy, and no stored result moves. The molecule viewer may redraw slower than 200 ms; it
is timed on a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.

**Your call.** How are results arranged, and which chart library draws them? *Recommendation:* settle both at the
tree's design round, on drawn screens, as each suite was. Who tries the workbench unaided? *Recommendation:* name the
colleague before the close, which records the trial. When do the Copilot app's checks run? *Recommendation:* before
the close; otherwise it carries them on.

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
- **The tools' foundations are partial.** `mesh/primitives.py` has four geometries; `inputs.profile`
  and `inputs.pqr` take a hand-edited contour and PQR; `physics/models.py` registers six models. The
  library has no residue mutation and no free-form (r, z) domain.

Risks: **RSK-15**, live and High (S7); **RSK-13**, re-scoped by the design document (M3, S12).

Excluded: the composer, the structural mutator and the sketcher, later phases (S7), with the open items that name
them, and the open items that name a provisional Phase 6 package (§8.2.46 AV5); user-authored
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
| The join between the scales | A meso suite between Molecular and Continuum holding Density, Outline and Charge map, built next; the 200 ms line in a performance package after Analysis | Each suite follows one scale; one pass measures the finished views (AR7, AR8; §8.2.43 AS1, AS2) |
| The last packages | The tree of results, then the layers in every Mol* view, before the performance package; then the library's refusals, a polish pass over every suite, and the route with new models, Qt's removal and the guide | The performance package times the finished views; each pull request reviews one kind of change; every open item names a package (WB-51; §8.2.46 AV1 to AV5) |
| Before the frame | Three packages for the written knowledge (tools, the specification, the knowledge base), then four of the six architecture clean-ups in two packages; the other two open the Molecular and Continuum suites | The audit's references are exact now; a change that must move nothing reviews best alone; the suites build on settled seams (AL22, AL24, AL25) |
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

**Merged 27 October 2026** ([the plan](wp5.01-workbench-design-study.md)); no tag.

Live constraints: REV-134 closes with Qt (U1).

### WP5.02 — The spike and the visual-feedback workflow (S8 to S10; §8.2.30 AF1 to AF4)

**Merged 2 November 2026** ([the plan](wp5.02-framework-spike.md)); tag `v0.6.0-alpha.2`.

Live constraints: The 200 ms line is unmeasured for the whole picture (Mol* alone takes about 800 ms on software GL); measure it on a GPU in the package that builds the first Study screen (WP5.19). A screen is ready only after Mol* has drawn. pdb2pqr is at 3.8 and the lock needs no override (REV-175). The study mockups fail the non-text measure and stay as dated evidence (REV-176). A shell package whose capability is not yet in the library opens with that library step, tested, before its screens (AG1).

### WP5.03 — Protonation before the density (§8.2.19 U2; REV-135)

**Merged 3 November 2026** ([the plan](wp5.03-protonation-before-the-density.md)); tag `v0.6.0-alpha.3`.

Live constraints: Only the `X86_V3` and `AVX512_SPR` meshes of example 07 are folded.

### WP5.04 — The charge mutator's library step (FR-38; §8.2.17 S4; §8.2.19 U6; §8.2.31 AG9 to AG11)

**Merged 3 November 2026** ([the plan](wp5.04-the-charge-mutators-library-step.md)); tag `v0.6.0-alpha.4`.

Live constraints: A pin can reposition a neighbour's hydrogens and carboxyl oxygens through PDB2PQR's optimisation, so the variant's record lists such residues and tests match atoms by identity. A radius scale below 1 can breach the kernel-spacing gate (REV-182). The Charge edit tool is WP5.16's (AJ10).

### WP5.05 — Named models and study overrides in the case (WB-11; FR-39; REV-62; §8.2.31 AG12, AG13)

**Merged 3 November 2026** ([the plan](wp5.05-named-models-and-study-overrides.md)); tag `v0.6.0-alpha.5`.

Live constraints: `models` is outside every dump and hash, so a plain reader refuses a case that names it; read it with `Case.load` or `load_case`.

### WP5.06 — Outputs and steric models as registries (MOD-09; §8.2.18 T4; §8.2.28 AD5; §8.2.32 AH1)

**Merged 4 November 2026** ([the plan](wp5.06-outputs-and-steric-registries.md)); tag `v0.6.0-alpha.6`.

Live constraints: The registering functions stay out of `PUBLIC` (REV-67). REV-171's cost items stay in Phase 6.

### WP5.07 — Variables and the rebuild forecast (FR-39; §8.2.19 U4; §8.2.31 AG2 to AG5; REV-139)

**Merged 4 November 2026** ([the plan](wp5.07-variables-and-the-rebuild-forecast.md)); tag `v0.6.0-alpha.7`.

Live constraints: The manifest gains `variables` only when a case has some. A `Forecastable` stage hashes its own `forecast_parameters`. REV-197 (rectification over a bias set through a variable) is WP5.19's (AJ10).

### WP5.08 — The frame and the project folder (FR-31, FR-32, FR-34, FR-35; REV-32, REV-52; MOD-13; §8.2.33 AI1, AI9 to AI14)

**Merged 5 November 2026** ([the plan](wp5.08-the-frame-and-the-project-folder.md)); tag `v0.6.0-alpha.8`.

Live constraints: A user's theme is not contrast-checked. A user's project has an empty charge screen until WP5.19. The frame is rebuilt in WP5.15 (AJ1). The 3D background is the `--canvas-3d` token.

### WP5.09 — The physics model (FR-32, FR-39; WB-34, WB-35; §8.2.34 AJ2, AJ3, AJ5)

**Merged 8 November 2026** ([the plan](wp5.09-the-physics-model.md)); tag `v0.6.0-alpha.9`.

Live constraints: The Physics suite and its *Exposed values* tool are WP5.15 and WP5.18's, the Study suite's list WP5.19's. REV-217 and REV-219 land in WP5.13, REV-220 and REV-221 in WP5.14, REV-218 in WP5.16 (AL22).

### WP5.10 — The written knowledge's tools and rules (CODE_REVIEW_039; §8.2.36 AL3 to AL7, AL14, AL24, AL27, AL28)

**Merged 9 November 2026** ([the plan](wp5.10-the-written-knowledges-tools-and-rules.md)); tag `v0.6.0-alpha.10`.

Live constraints: A commit that adds a decision re-runs `decisions.py`. Open decision 14 (xenon or import-linter) is the author's and stays in *Open decisions*.

### WP5.11 — The specification's text and the agent instructions (§8.2.36 AL8 to AL12, AL14, AL16 to AL18, AL21; §8.2.37 AM1 to AM9)

**Merged 9 November 2026** ([the plan](wp5.11-the-specifications-text-and-the-agent-instructions.md)); tag `v0.6.0-alpha.11`.

Live constraints: AL16 to AL18 and AL21 continue in WP5.12; REV-223 to REV-225 are Phase 6's.

### WP5.12 — The knowledge base and the guide (§8.2.36 AL13, AL15 to AL21; §8.2.37 AM13 to AM18)

**Merged 10 November 2026** ([the plan](wp5.12-the-knowledge-base-and-the-guide.md)); tag `v0.6.0-alpha.12`.

Live constraints: REV-228 is WP5.27's; REV-229 is after v1.0; REV-230 and REV-232 are Phase 6's, the model's open
terms and the tolerances argued (AV5).

### WP5.13 — Case and model files (REV-217, REV-219; CODE_REVIEW_036 candidates 1 and 5; §8.2.36 AL22, AL23)

**Merged 10 November 2026** ([the plan](wp5.13-case-and-model-files.md)); tag `v0.6.0-alpha.13`.

Live constraints: AL22 continues in WP5.14, WP5.16 and WP5.17; `ModelFile.body` is the suites' read of a model file
from WP5.15 on.

### WP5.14 — Sweep planning and the walk's keying (REV-221, REV-220; CODE_REVIEW_036 candidates 2 and 6; §8.2.36 AL22)

**Merged 10 November 2026** ([the plan](wp5.14-sweep-planning-and-the-walks-keying.md)); tag `v0.6.0-alpha.14`.

Live constraints: AL22 continues in WP5.16 and WP5.17; a sweep planned in Python resolves each member once to plan it
and once beside its stored files, until a package re-keys them (this plan's *Out of scope*).

### WP5.15 — The frame on Quasar's components (FR-27, FR-31, FR-34; WB-33, WB-36 to WB-38; REV-203, REV-204, REV-207, REV-208, REV-210 to REV-214; §8.2.34 AJ1, AJ6 to AJ9; §8.2.38 AN2, AN3, AN5 to AN7)

**Merged 11 November 2026** ([the plan](wp5.15-the-frame-on-quasars-components.md)); tag `v0.6.0-alpha.15`.

Live constraints: the compute settings are WP5.19's (AN1, AN4); a cleaned run's solution is rebuilt on viewing in
WP5.21 (AN5); each suite's field marks and *Modified only* filters are its own package's; the keyboard pass over the
canvases is WP5.26's (QR-16).

### WP5.16 — The Molecular suite (FR-37, FR-38; REV-121; REV-41's `prepare`; REV-218; §8.2.39 AO1 to AO3)

**Merged 12 November 2026** ([the plan](wp5.16-the-molecular-suite.md)); tag `v0.6.0-alpha.16`.

Live constraints: REV-240's variation view is WP5.23's and its safeguards WP5.27's; Prepare's view of the typed
orientation is WP5.23's (REV-243); REV-235's and REV-237's other points are WP5.26's; handles dragged in the 3D view
are the structural mutator's phase's (REV-238; AV5). A molecular tool's page
is `gui/web/tools.py`'s pattern for the other suites: `screens.Tool`, a pane of `Field` rows, `MolecularModel`'s
build and states.

### WP5.17 — The Continuum suite (REV-170, REV-39; FR-33's geometry link; §8.2.40 AP1 to AP4)

**Merged 13 November 2026** ([the plan](wp5.17-the-continuum-suite.md)); tag `v0.6.0-alpha.17`.

Live constraints: REV-244's CAD tooling and a part's subdivisions are the sketcher's phase's (AV5); handles dragged
on the canvas are WP5.26's; REV-242's new models are WP5.27's and its refusal's field WP5.25's. A Continuum tool's page is `continuum_tools.py`'s pane over
`BuiltModel`, its drawing `plane.py`'s layers.

### WP5.18 — The Physics suite (FR-31; WB-34, WB-35; §8.2.34 AJ2 to AJ5; §8.2.41 AQ1, AQ2)

**Merged** ([the plan](wp5.18-the-physics-suite.md)), delivered 16 November 2026; tag `v0.6.0-alpha.18`.

Live constraints: REV-250 asks whether PHY-23 states the dielectric force under a solid fraction and without the flow.
REV-251 (the walk a project opens with) and REV-252 (where Molecular and Continuum expose a value) are WP5.19's, with
REV-255's pane layout; REV-253's tunable plots are the analysis suite's; REV-254's words are WP5.25's, REV-255's (r, z)
view and the boundaries picked for the wall distance WP5.26's, and REV-257 Phase 6's (AV5). A Physics tool's page is `physics_tools.py`'s pane over
`PhysicsModel`, its drawing `plane.py:physics_plane`.

### WP5.19 — The Study suite (FR-39; FR-33's residue link; REV-41's `upto`; REV-205, REV-206, REV-209, REV-215, REV-247; AG7; AP5; §8.2.42 AR3 to AR5)

**Merged 18 November 2026** ([the plan](wp5.19-the-study-suite.md)); tag `v0.6.0-alpha.19`.

Live constraints: AR7 moves the 200 ms line to WP5.24, the performance package (REV-258); AR8 puts Charge on the
mesh in the meso suite, WP5.20 (REV-259). A recorded run picked in Runs is WP5.21's (REV-260); the review's polish
is WP5.26's (REV-261); an exposed value's first name is the author's, at WP5.26's round (REV-262). D12 goes to the author at `/np-ship`.

### WP5.20 — The meso suite (FR-31, FR-33; WB-43, WB-44; REV-259; REV-244's suite; REV-240's overlay; §8.2.42 AR8; §8.2.43 AS1, AS3; §8.2.44 AT1 to AT4)

**Merged 19 November 2026** ([the plan](wp5.20-the-meso-suite.md)); tag `v0.6.0-alpha.20`, to be pushed.

Live constraints: a free list of the structure's layers is WP5.23 (REV-265; AV3); the round's polish, Outline's
keyboard path and the map's default share are WP5.26's (REV-266).

### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30, REV-253, REV-260; AG6; AN5; §8.2.45 AU1 to AU3)

**Merged 20 November 2026** ([the plan](wp5.21-the-analysis-suite.md)); tag `v0.6.0-alpha.21`, to be pushed.

Live constraints: REV-267's points are WP5.26's; a field read at a point by its cell's own basis is WP5.22's (REV-270).

### WP5.22 — The tree of results (FR-32, FR-33; WB-51, WB-53; REV-268, REV-270; §8.2.46 AV4)

Its design round comes first: `/np-gui grill` puts the tree to the author on 2WCD (§8.4.4), with REV-268's questions: the
tree's nodes (a run or a comparison as data, groups of plots, probes in a pane of their own, the quantities shown, the
cut), the plot types a group takes (a surface, contours, arrows, a line along a cut, a scatter, the I–V, WB-53's true
3D view), how a variable or a constant is defined and where the library computes it (QR-13), how the tree is saved
in the project (FR-32), how it meets the link rulings (WB-06), and the chart library every plot uses, chosen again
(AU1; NiceGUI ships Plotly and ECharts). Library steps first: a field read at a point by its cell's own P2 basis, of
`ln c` on a logarithmic branch, so a map, a cut and a probe read the solved field (REV-270); then what the round
rules. Then the tree replaces the explorer's tiles, with REV-268's review points: the tiles' layout, the quantities'
order and words, a run named by sight, a map framed on its data at equal aspect, *Mirrored* the model of a two-run
view. Tag `v0.6.0-alpha.22`.

The round ran on 21 November 2026 ([the record](../../design/reviews/2026-11-21-tree.md); WB-54 to WB-63): COMSOL's
branches, a comparison a Data node of one `results.yaml` per project; one plot group or two side by side; every plot
type of the round's board P1; Plotly for every chart and every (r, z) view, in this package, so Meso's, Continuum's
and Physics' views move here with a round of verdicts, and uPlot, the canvas and `webgui` leave (CON-09's `webgui`
sentence with it); definitions from a library list or typed, evaluated by the library; the tables in the bottom panel;
*Shown run* following the newest; default plot groups; *Mirrored* first; a run labelled or named by what differs.

### WP5.23 — The structure's layers in every Mol* view (FR-31, FR-33; WB-49; REV-265, REV-243, REV-240; §8.2.46 AV3)

A free list of layers draws the structure in Molecular's View and Prepare and in Meso's Density, Outline and Charge
map. Each layer chooses what it draws (everything, a chain, the charged residues, the residues the tool is about, a
residue by name), its style (MolViewSpec's cartoon, backbone, putty, ball and stick, spheres or surface), its colour
and its opacity; the residues a tool is about are Charge map's pick with its copies, Density's named residues and
Outline's moved ones (WB-49). Library step first: each residue's variation over an ensemble's aligned frames, a colour
a layer can take (REV-240; QR-13). Prepare's view draws a typed tilt, azimuth, flip and centre before *Save prepared
structure* (REV-243; AO2). A round of verdicts on 2WCD (§8.4.4); Mol* ships unmodified (CON-09). Tag
`v0.6.0-alpha.23`.

### WP5.24 — The performance package (WB-23; REV-258; §8.2.31 AG7; §8.2.42 AR7; §8.2.43 AS2)

First, `redraw.cjs` gains the timing of the tree of results' field and plot views beside its charge-map picks. Then, in a local
session of the author's, on a machine with a GPU, `redraw.cjs --headed` times on 2WCD a residue picked on the meso
suite's charge map redrawing the whole picture (WB-23; criterion 6), with WP5.23's layers, and the tree's views. The front end's share is then
fixed, one keyed walk per pick first, the route reusing the pane's read (REV-258), and timed again; each miss left is
profiled with `--trace`. Where the renderer's own repaint is the cost, the line binds the front end's share and the
renderer's time is recorded (AG7). No stored key moves (VER-62). Tag `v0.6.0-alpha.24`.

### WP5.25 — The library's refusals (FR-35's NOTE; QR-12; REV-254, REV-242; §8.2.46 AV1)

Every refusal and diagnostic left in `mesh/`, `geometry/`, `charge/`, `density/`, `structure/`, `numerics/`, `solve/`,
`post/`, `sweep/`, `physics/`, `materials/`, `symmetry/`, `core/` and `api/` beyond `project.py`, and the command line's
messages, follow FR-35's NOTE: the rule, the value, the case path and the
remedy, in ASD-STE100. A refusal carries its case path and its file as fields, so `gui/web/tools.py:_plain`,
`api/project.py:_error_path` and `gui/web/physics_tools.py:problem_path` read the fields, and a refusal opens its field
by its path, never by its words (REV-242's fourth point). The suites' own words go to WP5.26's sweep. No number and no
stored key moves (VER-62). Tag `v0.6.0-alpha.25`.

### WP5.26 — The polish pass: every suite's open points, the words and the keyboard (QR-16; WB-52; REV-203's remainder; REV-235 to REV-237, REV-241, REV-245, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269; §8.2.46 AV2)

A round on 2WCD opens it (§8.4.4), with the choices the rows leave to the author: an exposed value's first name and its
list (REV-262), a variable's unit box (REV-263), the charge map's default share and *One subunit*'s overlay (REV-266),
the project dialogs, the settings' rows and spacing, the menus, the palette's look, and the Glossary as a help page
from one source (REV-235 to REV-237). Then every suite's open review points: the panes' layout, the canvases' labels
and keys, colours, numbers and units (REV-241, REV-245, REV-255's view and its region, REV-261, REV-266, REV-267), the
Study suite's efficiencies (REV-263), and Region's domains read from the region artefact's faces, not cut in the shell
(REV-245; VER-60), library step first. The keyboard pass over every canvas action, with handles dragged on the (r, z)
canvas and Outline's vertex path (REV-203's remainder, REV-236, REV-266; QR-16). The wording rule swept over every
screen, with a check that flags its patterns (REV-269; WB-52), and the suites' own words under FR-35's NOTE (REV-254).
Tag `v0.6.0-alpha.26`.

### WP5.27 — The guided route, new models, Qt's removal and documentation increment 5 (FR-36; REV-134, REV-228, REV-240, REV-241, REV-242, REV-249; S13, S17; §8.2.46 AV2)

Library step first: a new model of each kind from the project tree, a molecular model's first structure written as one
block, a new physics model's corrections, and what an import makes of a full copy's parent (REV-242's first two points,
REV-249, each put to the author at the plan); a PQR model opened as a structure (REV-241). An action that deletes asks a
second step (REV-240's safeguards; WB-32). Then the guided route over the six suites from an empty project (FR-36).
Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt widgets, the bundle and the packaging probe
leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55, VER-60, CON-08, CON-09, CON-11, ADR-004's
packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1). The application guide is rewritten
against the browser workflow with the rendered screens (§8.1's increment 5), and the site's register pages link the
plans and reviews it leaves out (REV-228; AM15). Tag `v0.6.0-alpha.27`.

### WP5.28 — The close

It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
bundle are gone with the capability list covered, orders the tool phases (S7), carries any Copilot check not yet run
(REV-166 to REV-168; AV6), hands the open items' provisional Phase 6 packages to `/np-plan phase 6` (AV5), and writes
the report, the changelog and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |
| 8 | Who observes QR-10 | **Author**, by the close (S24) |
| 14 | Whether xenon or import-linter is adopted | **Author**, on WP5.10's report (AL7, AL27), [delivered](../../../knowledge/07-software-stack/25-complexity-and-import-contract-tools.md): it recommends neither |
| 16 | The tree of results: its nodes, its plot types and its chart library | **Settled** at WP5.22's design round, 21 November 2026 (WB-54 to WB-63) |
| 17 | An exposed value's first name, a variable's unit box, the charge map's default share | **Author**, at WP5.26's round (REV-262, REV-263, REV-266) |
| 18 | A new physics model's corrections, and what an import makes of a full copy's parent | **Author**, at WP5.27's plan (REV-242, REV-249) |

Settled rows: see §8.2.17 to §8.2.46 and [the record](phase-5-record.md); decision 15, the meso suite's name, kept as
*Meso* at WP5.20's round ([the record](../../design/reviews/2026-11-19-meso.md); AS3).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Verdicts at each design round: each suite's prototype on 2WCD or, for Physics, example 01; the tree of results; the layers; the polish pass | WP5.16 to WP5.23, WP5.26 | The package is built on the drafts as they stand, and the verdicts move to its screen review |
| A machine with a GPU, in a local session | WP5.24 (§8.2.42 AR7; §8.2.43 AS2) | The 200 ms line stays unmeasured; REV-258 carries it to the close |
| A local Claude Code session | WP5.02 onward | Work continues headless, on renders |
| Verdicts on the six findings against the ESI and the COMSOL report, asked in one round at WP5.12's item 11 (AL20; AM18; REV-227) | WP5.12 | A finding not yet checked stays `unchecked` in REV-227, carried to the close |
| The verdict on xenon and import-linter (AL27) | After WP5.10 | Neither is added; the layering test stays the guard |
| An experimentalist new to nanopnp | The close | QR-10 is waived and carried (S13) |
| A session in the Copilot app on a WSL host (REV-166 to REV-168) | Before the close (§8.2.46 AV6) | The close carries the three checks to Phase 6; the gate is run by hand on Copilot meanwhile |
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
| WP5.10, the tools | 1 | The decisions page and §5.1's module rows equal the tree (the two new guards); ruff's `C901` and `PLR0913`; the strict build and `links.py` after the archive move; `duplicates.py` |
| WP5.11, the specification's text | none kept | VER-45; `clause.py` resolves every identifier; no SHALL, tolerance or default moves but those AL9, AL12 and §8.2.37 AM1 to AM5 rule |
| WP5.12, the knowledge base | 1 | VER-03's sodium cap at 10⁻³ (AM13); VER-45; `.claude/scripts/audit/markers.py` names no missing test; each `[verified]` claim names its source; 517 SHALLs unchanged |
| WP5.13, case and model files | 1, 2 | VER-62 unmoved; VER-61 and VER-72 with no new edge; FR-39's study, model and variable tests through the one reader |
| WP5.14, sweeps and keying | 1, 2 | VER-62 unmoved; VER-64's forecast against the walk; a planned sweep resolves each member once (REV-221) |
| WP5.15, the frame | 1 | VER-78's frame states over the fixture cases (the 2WCD state is the render set's, walked and cached by `/np-gui`, not a Tier 1 walk); a setting declared once reaches the page, its search, the palette and its file; a cleaned store rebuilds what it removed and never reads half an entry (FR-27) |
| WP5.16, Molecular | 1, 2 | The channel's axis and the chain groups' ring axis against a known axis, and their gates (VER-48); a model built alone keys as a study's walk does; a linked variant follows its parent; VER-62 unmoved by REV-218; VER-78 |
| WP5.17, Continuum | 1, 2 | VER-55 as restated, an unedited outline beside its structure depositing the same charge (AP1); VER-62's mesh hash unmoved by REV-170 and by untyped part sizes; MOD-03's edge gone (VER-61); a continuum model built alone keys as a study at its salt (FR-39); typed part sizes key as the table (VER-53); VER-78 |
| WP5.18, Physics | 1 | A physics model edited in the suite resolves to the case it shows; VER-78 |
| WP5.19, Study | 1, 2 | VER-44 and VER-60 as restated; FR-39's study and its sweep; VER-36's pair by resolved bias; VER-35 to a stage; VER-59's supplied spacing; a run's thread count keying nothing (VER-62); VER-78; the 200 ms measure (criterion 6) |
| WP5.20, the meso suite | 1, 2 | VER-60 as restated: a point names a residue once on a C<sub>n</sub> structure, an edit names the atoms it moves; the overlay's mean about the axis is the 3D charge's; VER-62 unmoved by the moved tools; VER-78 as amended, each moved tool's page at its new address |
| WP5.21, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; a comparison item and a cleaned run rebuilt (FR-32, AN5); a recorded run's convergence as the live one (VER-44); uPlot unmodified (CON-09); VER-78 |
| WP5.22, the tree of results | 1 | A field read at a point by its cell's P2 basis: exact on a quadratic field, a logarithmic branch read as `exp` of the solved `ln c` (REV-270); the tree saved with the project and read back (FR-32); VER-78 |
| WP5.23, the layers | 1 | A residue's variation over aligned frames against a hand-computed set; Mol* unmodified (CON-09); VER-78 over each Mol* view's layers |
| WP5.24, performance | 1 | VER-62 and VER-78 unmoved by the pick path's fix; criterion 6, timed by `redraw.cjs --headed` on a GPU |
| WP5.25, the refusals | 1 | VER-62 unmoved; a mesh gate's refusal, raised in a Tier 1 test, carries its case path and file as fields (a numerical gate, N1); VER-78's `refused` state holds a refusal WP5.25 rewrites and opens its field by that path; `_plain`, `_error_path` and `problem_path` read the fields, not the words, checked at review (N3) |
| WP5.26, the polish pass | 1 | VER-60 as restated, Region's domains read from the artefact; QR-16's keyboard path over each canvas; the wording check (REV-269); VER-78 |
| WP5.27, route and Qt's removal; WP5.28, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; a new model of each kind resolves and keys as an imported one (FR-32); VER-78 |

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
6. **The redraw is measured** on the author's machine with a GPU, in WP5.24, the performance package (§8.2.42 AR7;
   §8.2.43 AS2; REV-258): a residue selected on the meso suite's charge map redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
   whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
   binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

## End-of-phase report

The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
against the browser shell; VER-78's screen and state counts; the time from a click to a redrawn
view on the reference charged case and the install's time on a clean machine, each re-run by the
command WP5.02 names; and the tool phases' order.
