# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: in progress; WP5.01 to WP5.19 merged (`v0.6.0-alpha.19`); WP5.20, the meso suite, next, then WP5.21 to WP5.23 and the close.** Written 24 October 2026, during Phase 4 (§8.2.17); amended since by the rounds the [history index](../../../specification/history/index.md) lists. Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program gains a browser workbench, combining molecular viewers and continuum modelling
suites. Six library steps came first, then three packages that corrected the written knowledge and two that tidied the
library's insides. Then the screens: the frame, rebuilt on ready-made parts, and six suites, four that build models and two that use them. The sixth, added now, sits between the
molecule and the continuum: it shows how the molecule becomes the pore's shape and charge, each picture beside the
molecule. A performance package then times the screens on a graphics card. Last come the guided route, the old desktop
shell's removal, and the guide.

**Cost.** Five packages remain: about 19 sessions, 23 to 41 hours of agent work and 54 times you act, from the four
suites measured, and one session of yours on a computer with a graphics card.

**What could go wrong.** Moving three tools into the new suite could move a stored result; each move checks every
stored fingerprint, and a move is undone. The molecule viewer may redraw slower than 200 ms; it is timed on a computer
with a graphics card, and if the viewer itself is the cost, the line applies to the workbench's own share.

**Your call.** The new suite's name, at its design round. Recommendation: Meso, your word, naming a scale as its
neighbours do. Whether to adopt either measuring tool the tools package tried; it recommends neither. The colleague who
tries the workbench, named by the close.

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
| The join between the scales | A meso suite between Molecular and Continuum holding Density, Outline and Charge map, built next; the 200 ms line in a performance package after Analysis | Each suite follows one scale; one pass measures the finished views (AR7, AR8; §8.2.43 AS1, AS2) |
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

**Merged 10 November 2026** ([the plan](wp5.12-the-knowledge-base-and-the-guide.md)); tag `v0.6.0-alpha.12`. 163 of CODE_REVIEW_039's findings fixed, filed under `knowledge/`, `docs/` and four `src/` modules: the
knowledge base states what was measured and verified, each `[verified]` claim names its source (AL19), and each rule
is stated once, in its clause (AL15 to AL18); `knowledge/01` backs §4, which governs (AL16); the guide states that
protonation runs before stage 2 (AL13); the sodium cap's test is tightened (AM13); REV-226's citations follow §5.2.
The author answered the six findings that rest on the ESI or the COMSOL report, and each edit landed (REV-227; AL20,
AM16, AM18). 517 SHALLs kept.

Live constraints: REV-228 is WP5.23's; REV-229 is after v1.0; REV-230 waits for the next change to the correction
file; REV-231 and REV-232 are open.

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

Live constraints: AL22 continues in WP5.14, WP5.16 and WP5.17; `ModelFile.body` is the suites' read of a model file
from WP5.15 on.

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

Live constraints: AL22 continues in WP5.16 and WP5.17; a sweep planned in Python resolves each member once to plan it
and once beside its stored files, until a package re-keys them (this plan's *Out of scope*).

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

Live constraints: the compute settings are WP5.19's (AN1, AN4); a cleaned run's solution is rebuilt on viewing in
WP5.21 (AN5); each suite's field marks and *Modified only* filters are its own package's; the keyboard pass over the
canvases is WP5.23's (QR-16).

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

Live constraints: REV-240 carries an ensemble's variation view, colour maps beyond the two directions and one rule
for safeguards; REV-235's and REV-237's other points wait for a later suite's round; the charge screen's redesign is
WP5.19's (REV-209, REV-215); handles dragged in the 3D view are WP5.23's or later (REV-238). A molecular tool's page
is `gui/web/tools.py`'s pattern for the other suites: `screens.Tool`, a pane of `Field` rows, `MolecularModel`'s
build and states.

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

Live constraints: REV-244 carries a suite between Molecular and Continuum, the CAD tooling with the sketcher and
subdivisions of a part for meshing; handles dragged on the canvas are WP5.23's; REV-242's other points wait for the
new-model action and a pass over the stages' errors. A Continuum tool's page is `continuum_tools.py`'s pane over
`BuiltModel`, its drawing `plane.py`'s layers.

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

Live constraints: REV-250 asks whether PHY-23 states the dielectric force under a solid fraction and without the flow.
REV-251 (the walk a project opens with) and REV-252 (where Molecular and Continuum expose a value) are WP5.19's, with
REV-255's pane layout; REV-253's tunable plots are the analysis suite's; REV-254's words, REV-255's (r, z) view and
the boundaries picked for the wall distance are WP5.23's. A Physics tool's page is `physics_tools.py`'s pane over
`PhysicsModel`, its drawing `plane.py:physics_plane`.

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
WP5.22, the performance package (AR7; criterion 6; REV-258). Q24 to Q26 and Q28
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

Live constraints: AR7 moves the 200 ms line to WP5.22, the performance package (REV-258); AR8 puts Charge on the
mesh in the meso suite, WP5.20 (REV-259). A recorded run picked in Runs is WP5.21's (REV-260); the review's polish
is WP5.23's (REV-261); an exposed value's first name is the author's (REV-262). D12 goes to the author at `/np-ship`.

### WP5.20 — The meso suite (FR-31, FR-33; WB-43, WB-44; REV-259; REV-244's suite; §8.2.42 AR8; §8.2.43 AS1, AS3)

A suite that builds, between Molecular and Continuum: the molecule reduced to the axisymmetric model, named at its round
(AS3). Library steps first, as the shell computes nothing (VER-60): a point on the charge map names each residue once,
its chains' copies on a C<sub>n</sub> structure together (REV-259's physics point), and the atoms an edited outline
cuts, read in stage 1's frame and reduced to (r, z). Then, after the prototype round on 2WCD (AJ8), which takes
REV-259's questions, the suite's name and REV-244's radius against z and vertex list: *Density*, stages 2 and 3, the
grid, the kernel and the reduced map; *Outline*, stage 4's outline, created and edited, its saved edit a continuum
model holding the outline (AP1), the two from Continuum › Pore geometry; *Charge map*, stage 7's charge on the mesh and
its conservation checks, from Study › Charge on the mesh. Each pairs Mol*, side on and cut at the axis with *One
subunit* (WB-44), with the (r, z) view, linked both ways: a residue finds its patch, a point its residue, an edited
outline the atoms it cuts (FR-33). Its values stay the continuum model's `geometry` section over a molecular model picked
in the pane; it adds no kind of model (AR8). Continuum keeps Region, Mesh and Exposed values; Study keeps Overview, Study
setup, Sweep and Runs. FR-31's suites, §2's v0.6 row, §8.1's Phase 5 deliverable, WB-34 and WB-41 are amended
(AR8). What names the tools' old places follows them: VER-78's suites in (a) and `/study/charge` in (m), the
capability list's rows for Q14 to Q20 and Q24 to Q30, and `redraw.cjs`'s address. Q14 to Q20 and Q28 to Q30 move
here; VER-60 as restated. Tag `v0.6.0-alpha.20`.

### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30; AG6)

Library step first: the difference of two runs' fields over the overlap of their fluid domains, in `post/`, masked where
either lacks the point (AG6). Then, after the prototype round on 2WCD (AJ8), the results explorer and its tiles: a field
drawn by `webgui` when its tile opens it, its scene written once (REV-28, REV-30); the I–V; the quantities; an axial cut.
Probes and cuts are linked to their field, and a run to its result (FR-33). Comparison shows two runs side by side on
one scale or as their difference. A run whose solution the store's clean-up removed rebuilds it when viewed (AN5). Q37 to Q41 move here. Tag `v0.6.0-alpha.21`.

### WP5.22 — The performance package (WB-23; REV-258; §8.2.31 AG7; §8.2.42 AR7; §8.2.43 AS2)

First, `redraw.cjs` gains the timing of Analysis's field and plot views beside its charge-map picks. Then, in a local
session of the author's, on a machine with a GPU, `redraw.cjs --headed` times on 2WCD a residue picked on the meso
suite's charge map redrawing the whole picture (WB-23; criterion 6), and Analysis's views. The front end's share is then
fixed, one keyed walk per pick first, the route reusing the pane's read (REV-258), and timed again; each miss left is
profiled with `--trace`. Where the renderer's own repaint is the cost, the line binds the front end's share and the
renderer's time is recorded (AG7). No stored key moves (VER-62). Tag `v0.6.0-alpha.22`.

### WP5.23 — The guided route, Qt's removal and documentation increment 5 (FR-36; REV-134; S13, S17)

The guided route over the six suites (FR-36), with the keyboard pass over every canvas action (REV-203's remainder;
QR-16). Every row Q01 to Q41 is checked present (criterion 3); then PySide6, the Qt widgets, the bundle and the
packaging probe leave, and the restated NOTEs of IF-09, P3, QR-10, VER-43, VER-44, VER-55, VER-60, CON-08, CON-09,
CON-11, ADR-004's packaging NOTE and RSK-13 become their clauses (S17; T5). REV-134 closes (U1). The application guide is
rewritten against the browser workflow with the rendered screens (§8.1's increment 5), and the site's register pages
link the plans and reviews it leaves out (REV-228; AM15). Tag `v0.6.0-alpha.23`.

### WP5.24 — The close

It resolves or carries each open decision, records QR-10 with the colleague named by then (S24), confirms Qt and the
bundle are gone with the capability list covered, orders the tool phases (S7), and writes the report, the changelog
and `CITATION.cff`. Its last commit takes `v0.6.0` alone (§8.4.1).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 5 | The order of the tool phases against Phase 6 | **Author**, at the close (S7) |
| 8 | Who observes QR-10 | **Author**, by the close (S24) |
| 14 | Whether xenon or import-linter is adopted | **Author**, on WP5.10's report (AL7, AL27), [delivered](../../../knowledge/07-software-stack/25-complexity-and-import-contract-tools.md): it recommends neither |
| 15 | The meso suite's name: *Meso*, *Reduction*, *Bridge* or another | **Author**, at WP5.20's round (§8.2.43 AS3) |

Settled rows: see §8.2.17 to §8.2.43 and [the record](phase-5-record.md).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Verdicts on each suite's prototype round, on 2WCD or, for Physics, example 01 | WP5.16 to WP5.21 | The suite is built on the prototype's design as it stands, and the verdicts move to its screen review |
| A machine with a GPU, in a local session | WP5.22 (§8.2.42 AR7; §8.2.43 AS2) | The 200 ms line stays unmeasured; REV-258 carries it to the close |
| A local Claude Code session | WP5.02 onward | Work continues headless, on renders |
| Verdicts on the six findings against the ESI and the COMSOL report, asked in one round at WP5.12's item 11 (AL20; AM18; REV-227) | WP5.12 | A finding not yet checked stays `unchecked` in REV-227, carried to the close |
| The verdict on xenon and import-linter (AL27) | After WP5.10 | Neither is added; the layering test stays the guard |
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
| WP5.20, the meso suite | 1, 2 | VER-60 as restated: a point names a residue once on a C<sub>n</sub> structure, an edited outline names the atoms it cuts; VER-62 unmoved by the moved tools; VER-78 as amended, each moved tool's page at its new address |
| WP5.21, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; VER-78 |
| WP5.22, performance | 1 | VER-62 and VER-78 unmoved by the pick path's fix; criterion 6, timed by `redraw.cjs --headed` on a GPU |
| WP5.23, route and Qt's removal; WP5.24, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses; the capability list; VER-78 |

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
6. **The redraw is measured** on the author's machine with a GPU, in WP5.22, the performance package (§8.2.42 AR7;
   §8.2.43 AS2; REV-258): a residue selected on the meso suite's charge map redraws the whole picture within 200 ms (WB-23). Predicted: the front end's share met (26 ms p95 in the spike), the
   whole picture unknown. On a miss the redraw is profiled; where the renderer's own repaint is the cost, the line
   binds the front end's share and the renderer's time is recorded; a miss by the front end is fixed (§8.2.31 AG7).

## End-of-phase report

The close reports: the QR-10 observation, its findings and their rulings; the Qt capability list
against the browser shell; VER-78's screen and state counts; the time from a click to a redrawn
view on the reference charged case and the install's time on a clean machine, each re-run by the
command WP5.02 names; and the tool phases' order.
