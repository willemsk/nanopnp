# Phase 5 (Graphical interface): a molecular and continuum workbench in the browser

**Status: delivered, 22 November 2026; closes at the merge and the `v0.6.0` tag. WP5.01 to WP5.21 and WP5.27 merged (`v0.6.0-alpha.21`, `v0.6.0-alpha.27`), and WP5.28, the close, delivered; closed early (REV-272; §8.2.47). The tree of results, the layers, the performance package, the refusals, the polish pass and the guided route are Phase 6's.** Written 24 October 2026, during Phase 4 (§8.2.17); amended since by the rounds the [history index](../../../specification/history/index.md) lists. Release: **v0.6** (`v0.6.0`).

## In brief

**What changes.** The program has a browser workbench of six suites, four that build models and two that use them. A
survey of the code found that the next features (results as an editable tree, views that split, a settings pane, the
finer look) would be one-off work on today's foundations. You ruled that the next phase opens with a restructure and
that this phase closes early. Its last two packages are delivered: the old desktop shell's removal, after a check that
the browser workbench covers its 41 capabilities, with a short guide; and the close. Five packages and the guided
route move to the next phase, after its foundations.

**Cost.** Two packages: about 12 sessions, 12 to 24 hours of agent work and 20 times you act. The seven planned before
were about 36 sessions, 44 to 73 hours and 70.

**What could go wrong.** The browser workbench could lack something the desktop shell does; the check runs first, and a
miss keeps the desktop shell. The removal could break a part the two shells share; the screen tests load every screen
in every state. This release has a short guide and no guided route, so a new user is not yet led through a first run;
the trial with a colleague waits for the release candidate of version 1.

**Your call.** Settled on 22 November 2026: the order of the later tool phases is set at the next phase's scope round,
which plans the phases again. The Copilot app's checks were not run and are carried to the next phase; so is the
Windows test run, which fails, as you ruled.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, never restatements, and the rulings
behind this plan are §8.2.17 (S1 to S20), not re-argued here.

Phase 5 answers one question: **can a nanopore experimentalist with no Python run a case unaided in a
workbench that a method developer also wants to use?** Its gate is §8.1's, as S13 states it and AW2 amends it: the
phase closes early (REV-272), and the trial that answers the question is held on v1.0's release candidate.

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

Excluded: the six packages its seventh amendment moved to Phase 6 and QR-10's trial (§8.2.47 AW1, AW2; *Moved to
Phase 6* below); the composer, the structural mutator and the sketcher, later phases (S7), with the open items that name
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
| The join between the scales | A meso suite between Molecular and Continuum holding Density, Outline and Charge map, built next; the 200 ms line in a performance package after Analysis, Phase 6's since AW1 | Each suite follows one scale; one pass measures the finished views (AR7, AR8; §8.2.43 AS1, AS2) |
| The last packages | Qt's removal with a short guide, then the close, under their numbers; the tree of results, the layers, the performance package, the refusals, the polish pass and the guided route with new models move to Phase 6, after its foundations | Each moved package draws on a part the restructure replaces, so nothing is built twice (REV-272; §8.2.47 AW1, AW3, AW4) |
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

A live-constraints line below that names WP5.22 to WP5.26, or WP5.27 for the route, new models or the safeguards, names
a package moved to Phase 6 (*Moved to Phase 6*; §8.2.47 AW1, AW4).

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

**Merged 19 November 2026** ([the plan](wp5.20-the-meso-suite.md)); tag `v0.6.0-alpha.20`.

Live constraints: a free list of the structure's layers is WP5.23 (REV-265; AV3); the round's polish, Outline's
keyboard path and the map's default share are WP5.26's (REV-266).

### WP5.21 — The Analysis suite (FR-32's comparisons; FR-33; REV-28, REV-30, REV-253, REV-260; AG6; AN5; §8.2.45 AU1 to AU3)

**Merged 20 November 2026** ([the plan](wp5.21-the-analysis-suite.md)); tag `v0.6.0-alpha.21`.

Live constraints: REV-267's points are WP5.26's; a field read at a point by its cell's own basis is WP5.22's (REV-270).

### Moved to Phase 6 (§8.2.47 AW1, AW4)

Phase 6's provisional packages, named by scope (AV5); its scope round numbers and orders them after the foundations
(REV-272). Their entries as planned are in [the record](phase-5-record.md). The numbers are retired.

| Was | Phase 6's package | Its items |
|---|---|---|
| WP5.22 | The tree of results | FR-32's tree; WB-54 to WB-63; REV-268, REV-270, REV-273 |
| WP5.23 | The structure's layers | WB-49; REV-265, REV-243, REV-240's variation view |
| WP5.24 | The performance package | WB-23's 200 ms measure on the author's GPU (AR7, AS2); REV-258 |
| WP5.25 | The library's refusals | FR-35's NOTE; REV-254, REV-242's fourth point |
| WP5.26 | The polish pass | QR-16's keyboard pass; WB-52; REV-235 to REV-237, REV-241, REV-245, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269; the former open decision 17 |
| WP5.27's first part | The guided route and new models | FR-36; REV-240's safeguards, REV-241's PQR, REV-242's first two points, REV-249; the former open decision 18; the full guide (AW3) |

### WP5.27 — Qt's removal and the short guide (REV-134, REV-228; S13, S17; §8.2.47 AW1, AW3, AW9 to AW11)

**Merged 22 November 2026** ([the plan](wp5.27-qts-removal-and-the-short-guide.md)); tag `v0.6.0-alpha.27`.

The capability check found every row Q01 to Q41 in the workbench: 31 present, Q16 as ruled, nine carried by REV-274,
none missing ([the record](../../design/reviews/2026-11-21-qt-capabilities.md); AW7, AW11). Before it, a running run
names its stage and rung and writes its log (AW9), *More values* reaches every unfielded setting (AW10), and the
explorer lists contributed deviations (FR-25). PySide6, the Qt widgets, the bundle and the probe are removed; the
server's self-test, `nanopnp gui --selftest`, runs on each Tier 1 leg (VER-43, VER-44, VER-55, VER-60; RSK-13);
`THIRD-PARTY-LICENSES.md` travels in the wheel and `nanopnp --env` states UMFPACK's GPL-2+ (CON-11). The restated
NOTEs are their clauses (S17; T5). The guide's workbench page and the registers' copied links close REV-134 and
REV-228. No golden or stored key moves.

Live constraints: REV-274's five details and QR-16's gaps are Phase 6's.

### WP5.28 — The close (§8.2.47 AW1, AW2; §8.2.48 AX1 to AX3)

**Delivered 22 November 2026** ([the plan](wp5.28-the-close.md)); its last commit takes `v0.6.0` alone after the
merge (§8.4.1).

The 49 rulings a delivered package landed hold their clause or read `spent`; T3 and AW1 keep what waits, and AC3 its
clause alone. REV-166 to REV-168 were not run and are carried to Phase 6's scope round (AV6); no review row is `open`,
and each that waits names its owner (AX2). The [end-of-phase report](#end-of-phase-report), measured on the close's own
tree, finds criteria 1 and 2 met on Linux and macOS, 3 met, 4 met in part (QR-16), 5 and 6 not this phase's. Run 837's
Windows leg failed one test and met its 40-minute limit; `main`'s has not finished since 10 November; the author
released with the gap (§8.2.48 AX3; REV-277). `CHANGELOG.md`'s `[0.6.0]` gathers the 23 packages and each break since
`v0.5.0` with its migration; `CITATION.cff`, the README, the site's banner and the install page name `v0.6.0` and the
workbench; §8.1's Phase 5 gate reads "Closed with v0.6.0".

Live constraints: the six moved packages, REV-272's proposals, the tool phases' order and REV-277 are Phase 6's scope
round's (AW1, AX1, AX3).

## Open decisions

None is open. Settled rows: see §8.2.17 to §8.2.48 and [the record](phase-5-record.md). Decision 5, the order of the
tool phases, is set at Phase 6's scope round (§8.2.48 AX1). Decision 8, who observes QR-10, waits for
v1.0's release candidate (AW2); decision 14 closed with neither xenon nor import-linter adopted (AW6); decisions 17 and
18 moved to Phase 6 with the polish pass and the new models (AW1).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| A local Claude Code session | WP5.02 onward | Work continues headless, on renders |
| Verdicts on the six findings against the ESI and the COMSOL report, asked in one round at WP5.12's item 11 (AL20; AM18; REV-227) | WP5.12 | A finding not yet checked stays `unchecked` in REV-227, carried to the close |
| A session in the Copilot app on a WSL host (REV-166 to REV-168) | Before the close (§8.2.46 AV6) | Not run: the close carried the three checks to Phase 6's scope round (WP5.28); the gate is run by hand on Copilot meanwhile |
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
| WP5.19, Study | 1, 2 | VER-44 and VER-60 as restated; FR-39's study and its sweep; VER-36's pair by resolved bias; VER-35 to a stage; VER-59's supplied spacing; a run's thread count keying nothing (VER-62); VER-78; the 200 ms measure, Phase 6's since AW1 (REV-258) |
| WP5.20, the meso suite | 1, 2 | VER-60 as restated: a point names a residue once on a C<sub>n</sub> structure, an edit names the atoms it moves; the overlay's mean about the axis is the 3D charge's; VER-62 unmoved by the moved tools; VER-78 as amended, each moved tool's page at its new address |
| WP5.21, Analysis | 1 | AG6's difference: exact for a linear field, zero for identical runs; a comparison item and a cleaned run rebuilt (FR-32, AN5); a recorded run's convergence as the live one (VER-44); uPlot unmodified (CON-09); VER-78 |
| WP5.27, Qt's removal; WP5.28, the close | 1, 2 | VER-43, VER-44, VER-55, VER-60 as their clauses, the server's self-test failing on a payload that does not load; the capability list, Q01 to Q41, checked at review against the rendered screens (N3), run progress and *More values* with it; a contributed deviation listed (FR-25); VER-78 over every screen and state after the shared modules split; VER-62 unmoved; VER-45's strict build over the short guide |

**The phase is complete when:**

1. **Tiers 1 and 2 pass**, per push and nightly. No waiver but one: the Windows leg's failure is carried to Phase 6
   (§8.2.48 AX3; REV-277).
2. **The restated gating clauses and VER-78 pass** on every fixture state. A miss is fixed; a
   re-argued clause is a spec amendment.
3. **Every Qt shell capability is in the browser shell**, checked against WP5.01's list before Qt
   leaves. A miss keeps Qt. Row Q16 is the typed move (AW7), and five details are carried by REV-274 (AW11).
4. **Each v0.6 requirement has its test or review check.** A miss is fixed, or deferred as a
   `REV-nn` row. QR-16 is met in part: its keyboard gaps ship noted beside it (AW8).
5. **QR-10's trial is not this phase's**: it is held on v1.0's release candidate (§8.2.47 AW2).
6. **The redraw's 200 ms measure is not this phase's**: it moved with the performance package to Phase 6
   (§8.2.47 AW1; REV-258).

## End-of-phase report

Measured on WP5.28's own tree, 22 November 2026: `13f72c3` for the push gate and the dispatched CI run,
[run 837](https://github.com/willemsk/nanopnp/actions/runs/45000286438), whose `src/`, `tests/` and `data/` are those of
the final tree. Nothing is copied from an Outcome. Every number names its command or its run.

- **The Qt shell's capabilities** (`grep -o "| \(present\|carried\)[^|]*|"` over
  [the capability record](../../design/reviews/2026-11-21-qt-capabilities.md)). 41 rows, Q01 to Q41: 31 `present`,
  1 `present as ruled (AW7)` (Q16, the typed vertex move), 9 `carried` by REV-274 (points 1 to 4 one each, point 5
  five), none missing. Qt is gone: `git grep -il "pyside6\|pyinstaller"` outside `docs/`, `specification/`,
  `knowledge/` and `CHANGELOG.md` prints `.gitignore` (the Python template's comment) and
  `tests/tier1/test_gui_viewmodels.py` (VER-43's guard), nothing else.
- **The screens** (VER-78). `SCREENS` holds 32 screens and `STATES` 4 (`empty`, `charged-tube`, `uncharged`,
  `refused`); `tests/tier1/test_gui_screens.py` collects 149 tests, 128 of them the screen-by-state grid. All 149
  passed in Chromium on Linux with `NANOPNP_REQUIRE_BROWSER=1` (`pytest tests/tier1/test_gui_screens.py -n auto`,
  468 s on four CPUs), as they do in the push gate, which requires the browser. Run 837's legs install no Chromium and
  skip 142 of them, the only skips in those legs: VER-78 runs on Linux alone (Appendix A's CON-13 row). The pull
  request's `tests (tier1)` job is read at `/np-ship`.
- **Number stability** (VER-62; run 837, mode `main`). The per-push selection walks examples 01 and 02 (ePNP-NS), and
  each leg prints the largest relative drift:

  | Platform | Mode | Example 01 | Example 02, ePNP-NS | Tests |
  |---|---|---|---|---|
  | linux-x86_64/X86_V3 | same mesh, against 10⁻⁸ | 7.2 × 10⁻¹⁴ (`eof_m3_s`) | 1.1 × 10⁻¹⁶ (`currents_A[Cl-]`) | 1,812 passed, 142 skipped, 492 s |
  | darwin-arm64/ASIMDDP | mesh moved, against ≤ 10⁻³ | 1.5 × 10⁻¹³ (`eof_m3_s`) | 1.1 × 10⁻¹⁵ (`eof_m3_s`) | 1,812 passed, 142 skipped, 611 s |
  | win32-AMD64 | — | not reached | not reached | 1 failed, then stalled at 99 %; cancelled at its 40-minute limit |

  Prediction: zero drift beyond round-off. Met. The Linux and macOS legs' `nanopnp gui --selftest` exercised NGSolve
  and Netgen 6.2.2606, `ngsolve.webgui`'s renderer (779,484 bytes), MDAnalysis, gemmi, scikit-image, Shapely, Gmsh
  4.15.2 and PDB2PQR 3.8.0 with PROPKA 3.5.1, and found the licence notice (VER-43, VER-44, VER-55, VER-60; CON-11).
  The Windows leg failed one test and did not finish, so its self-test, the step after the tests, never ran
  (REV-277); it has not finished on any push or nightly run with tests since 10 November (run 733), unseen
  because a pull request's CI tests on Linux alone. The author ruled to release and carry it (§8.2.48 AX3).
- **The suite** (`uv run pytest --collect-only -q`). 2,068 tests in all; 1,954 collected by default, 114 deselected:
  94 as `nightly` or `slow`, and Tier 3's 20. `-m tier1` selects 1,758, `-m tier2` 220. The push gate passed
  (`gate.sh run`, 539 s on `13f72c3`, four CPUs).
- **The redraw, headless** (`node .claude/scripts/gui/redraw.cjs <address> --json` on the 2WCD project that
  `render_shell.py --only 2wcd` caches, continuum `2wcd-charged`, 20 picks after 3 warm-up, 1440 × 900; the page got
  SwiftShader's software Vulkan). Median and p95 in ms:

  | Measure | Median | p95 |
  |---|---|---|
  | The markers' paint | 314.6 | 513.8 |
  | — the server's handling (release to `nano.plane`) | 188.2 | 381.0 |
  | — the drawing's fetch | 64.6 | 83.6 |
  | — the canvas's paint | 58.4 | 67.8 |
  | The whole repaint (Mol*'s second frame) | 1,285.6 | 1,517.5 |
  | — Mol*'s own share | 946.5 | 1,047.8 |

  Both miss the 200 ms line, as predicted: WP5.19 measured the markers' paint at 297 / 380 ms on the same software GL.
  The server's handling is the largest part of the markers' paint, and Mol* without a GPU most of the whole repaint.
  Not fixed: the GPU measure is Phase 6's performance package (AW1; REV-258).
- **The fresh install** (`uv build --wheel`; `uv venv --python 3.14`; `uv pip install "<wheel>[structure,gui]"`). The
  wheel is 3.1 MB (3,115,574 bytes). The install took 5.3 s cold (`--no-cache`) and 3.9 s warm, into fresh
  environments of 763 MB each (`du -sh`). The installed `nanopnp gui --selftest` exits 0 in 6.2 s; Gmsh, not in those
  extras, is skipped as the optional mesher (CON-10).
- **The requirements** (D4's script over Appendix A). The rows of FR-31 to FR-35, FR-37 to FR-39, IF-09, CON-09,
  CON-11 and QR-16 name 17 test files and 13 test names; every one resolves under `tests/`. IF-09 and CON-09 name
  VER-43, VER-44, VER-55, VER-60 and VER-78, each with its tests in `tests/tier1/` (VER-55 and VER-60 also in
  `tests/tier2/`). No name is stale; Appendix A is unchanged. The parts verified at review and their records:
  FR-31's place of a value or a problem, WP5.20's ([the Meso round](../../design/reviews/2026-11-19-meso.md));
  FR-33's Continuum picks, WP5.17's final render ([the Continuum round](../../design/reviews/2026-11-12-continuum.md)
  and the package's Outcome), its residue picks, WP5.19's ([the Study round, 2](../../design/reviews/2026-11-18-study-2.md)),
  and its edit's residues, WP5.20's (the Meso round); FR-37's Prepare tool and FR-38's Charge edit tool, WP5.16's
  ([the Molecular round, 2](../../design/reviews/2026-11-12-molecular.md)); FR-39's study values and sweep modes,
  WP5.19's (the Study round, 2); QR-16, each workbench package's render review against the shipped themes, with the
  keyboard gaps of its NOTE (REV-236, REV-245, REV-266). FR-32 is checked less its tree (v0.7).
- **The registers.** `docs/project/review-findings.md`: 276 rows, none `open`: `fixed` 207, `accepted` 38,
  `deferred` 17, `declined` 7, `wontfix` 4, `post-1.0` 3; REV-277, raised by this report, makes 277 and 39 `accepted`. Every `accepted` or `deferred` row names its owner (item 2's
  owner script prints nothing). REV-166 to REV-168 were not run and are carried (D1). `holds-now.yaml`: the 49 rulings
  a delivered package landed keep their clause or read `spent`; T3 and AW1 keep what waits, and AC3 its clause alone
  (REV-170 is `fixed`); 22 lines hold
  `open:` (`grep -c`): the 19 that name Phase 6, v1.0 or the Copilot session, T3, AW1 and the header's comment. AX3, ruled at
  this package, adds a 23rd.
- **The development loop** (`<git dir>/nanopnp-gate.log`; run 837's job timings). The commit hook took 162 s on item
  1's commit (a YAML file, the full hook) and under 1 s on item 2's (prose alone); the push gate 539 s, against 243 s
  at Phase 4's close: VER-78's 149 Chromium tests take 468 s alone on four CPUs. Run 837's critical path, Windows aside: 10 min 58 s
  (first job start 07:53:52 to macOS's end 08:04:50); the Windows leg ran to its 40-minute limit.

### Verdicts

| # | Verdict | Evidence |
|---|---|---|
| 1 | **Met on Linux and macOS; carried on Windows** | The push gate passed (539 s); run 837 passed on Linux and macOS; its Windows leg failed one test and stalled, as on `main` since 10 November; the author ruled the waiver (§8.2.48 AX3; REV-277) |
| 2 | **Met on Linux and macOS** | VER-43, VER-44, VER-55 and VER-60 passed in run 837's Linux and macOS legs with the self-test; VER-78's 149 tests passed in Chromium on Linux, in every state |
| 3 | **Met** | 41 of 41 capability rows: 31 present, Q16 as ruled (AW7), nine carried by REV-274 (AW11); no Qt module, bundle or probe is left |
| 4 | **Met in part** | Every v0.6 requirement has its test or its review record, and every named test resolves; QR-16 ships with the keyboard gaps of its NOTE (AW8) |
| 5 | **Not this phase's** | QR-10's trial waits for v1.0's release candidate (AW2) |
| 6 | **Not this phase's** | Measured headless: 314.6 ms median for the markers' paint against 200 ms; the GPU measure is Phase 6's (AW1; REV-258) |

### Handed to Phase 6's scope round

The round orders the later tool phases (AX1), then Phase 6's packages after its cleanup and foundations (REV-272). It
receives:

- **The six moved packages** (AW1; *Moved to Phase 6* above): the tree of results, the structure's layers, the
  performance package, the library's refusals, the polish pass, and the guided route and new models.
- **REV-272's five proposals**: measure the cleanup, start it with an audit, order the foundations, reorder Phase 6's
  existing packages (Z6's speed-up first revisited), and models by session type.
- **The Copilot app's checks**, REV-166 to REV-168 (AV6), carried by this package.
- **The Windows test leg** (REV-277; AX3), failing since 10 November.
- **The open items** (`accepted` and `deferred` rows), by the package their ruling names (AV5):

  | Package | Rows |
  |---|---|
  | The tree of results | REV-268, REV-270, REV-273, REV-275 |
  | The structure's layers | REV-240, REV-243, REV-265, REV-274 |
  | The performance package | REV-258 |
  | The library's refusals | REV-242, REV-254 |
  | The polish pass | REV-235 to REV-237, REV-241, REV-245, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269, REV-274, REV-275 |
  | The guided route and new models | REV-240, REV-241, REV-242, REV-249 |
  | The cleanup | REV-271 |
  | The scope round | REV-272 |
  | The exports | REV-41, REV-45 |
  | The validation runs | REV-46, REV-61, REV-64 |
  | The speed-up | REV-60, REV-156, REV-171 |
  | V&V in CI | REV-91, REV-277 |
  | The structure pipeline | REV-151, REV-180, REV-181, REV-186 |
  | The tolerances argued | REV-182, REV-225, REV-232 |
  | The model's open terms | REV-223, REV-224, REV-230, REV-255, REV-257 |
  | The forms | REV-275 |
  | The Copilot host's session | REV-166 to REV-168 |
  | A tool's phase | REV-67 (the composer), REV-149 and REV-238 (the structural mutator), REV-244 (the sketcher) |
  | FR-43's package | REV-183 |
  | The radius set's next change | REV-276 |
