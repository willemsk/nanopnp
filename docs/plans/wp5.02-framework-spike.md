# WP5.02 — The framework spike and the visual-feedback workflow

**Status: in progress, items 1 to 5 done, 2 November 2026.** 2 November 2026, on `v0.5.0`. It inherits WP5.01's design
(`docs/design/workbench.md`), its `/np-gui` loop and REV-137, REV-138, REV-141 and REV-143.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** The workbench's technology is chosen on evidence. One hard screen, where picking
a residue of the molecule lights up its charge on the pore map and back, is built two ways: all in
Python, and as a web application in TypeScript. Both are timed, sized, driven by a robot, installed
fresh, and opened inside a desktop window, so that a desktop app stays possible later. The author
picks one. The chosen way then gets the server, the screens' test states, a screenshot command for
every screen and a live editing loop. A check proves that every screen loads in every test state
without errors.

**Cost.** About two weeks: a week for the two builds and their numbers, and a week for the chosen
stack's groundwork. The desktop-window check adds about a day.

**What could go wrong.** The two builds could be measured unfairly. Both use one server and one
data set, so only the front end differs. A TypeScript win adds a build step that the release and
the checks must run. The checks would fail if the built files were missing. A local server could be
reached by other web pages. It answers only to the address and secret it prints.

**Your call.** Which stack does the workbench use? *Recommendation:* decide from the report's
numbers. Python-first if it meets the redraw time and wraps in a desktop window, because one
language is cheaper to keep.

## Execution brief

**Scope.** The spike of S8 under `spikes/wp5.02/`. The author's ruling, recorded in ADR-004. The
spikes removed (AF3). Then, in the chosen stack: the server and its contract (ADR-004's NOTE, the
desktop wrapper), the screen registry, the fixture states, VER-78, `/np-gui render shell`, the
live loop, and the four REV rows. **Depends on:** `v0.5.0` (merged and tagged). **Requirements:** S8
to S10, S12, AF1 to AF3; IF-09's and ADR-004's NOTEs; CON-07, CON-08, CON-09, CON-11; QR-16; FR-33
(the spike's link only). **Implementing session:** Sonnet, high effort. Tag `v0.6.0-alpha.2`.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The spike's layout | `spikes/wp5.02/`: `server/` (one FastAPI app, shared), `nicegui/`, `react/` (Vite, TypeScript, React), `fixture/`, `measure/`, `electron/`. Both candidates draw the molecule with Mol*, the charge map as a raster from `gui/charge.py:charge_image`, and the sketcher stub as an (r, z) canvas with a later-phase banner. NiceGUI calls the server's Python functions in-process; React calls its JSON routes | AF2; S8. One server and one data set make the measured difference the front end's |
| D2 The fixture and the link | The full 2WCD of example 07, walked to `charge` once and written to `fixture/out/` (ignored by git). Residue to map: the residue's charged atoms' (r, z) markers. Map to residue: residues ranked by the summed `kernel.py:volume_density` of their charged atoms at the point. This is the spike's display aid and not the library's link | Real scale is what makes the screen hard. FR-33's library link belongs to the package that builds the Study suite's *Charge on the mesh* |
| D3 The measures and the ruling | Six measures per candidate: (1) code size; (2) click-to-redraw, median and p95 of 20 picks each way, line p95 ≤ 200 ms; (3) headless drivability, every state reached by URL and checked with no human step; (4) the install, clean venv time and added size; (5) every front-end runtime dependency's licence under CON-09's NOTE; (6) the Electron window, link working or not. A fail on (5) disqualifies. The report is `docs/design/spike/report.md`, published as an Artifact. The author rules through `AskUserQuestion`. The ruling is a row of the history and a NOTE beside ADR-004 | S8; AF1; WB-23's 200 ms. The author weighs the numbers, and no score is pre-set |
| D4 The server and `nanopnp gui` | `src/nanopnp/gui/web/server.py` keeps ADR-004's NOTE (the desktop wrapper). `cli` adds `gui`, dispatching by the module name `nanopnp.gui.web.server`, a `string` edge `cli -> gui`. The `gui` extra gains `fastapi` and `uvicorn` (and `nicegui` if chosen) beside PySide6, which leaves with Qt. `nanopnp-gui` stays the Qt shell | AF1; S12. `gui` sits above `cli` in the layer order, so an import would be an upward edge (VER-61) |
| D5 Screens, states, VER-78, the loops | `gui/web/screens.py`: `Screen(id, path, controls)`, with `home` and `st-charge` registered. `gui/web/states.py`: `empty`, `charged-tube` and `refused`, booted by `nanopnp gui --state <name>`. **VER-78**: every state loads every screen with its declared `data-control`s and no console error, and the server keeps its contract. Python Playwright in the dev group. `/np-gui render shell` through `.claude/scripts/gui/render_shell.py`. The live loop is `nanopnp gui --dev` | S9; S10; the phase plan's VER-78 |
| D6 The four rows | REV-137: a renderer table in `workbench.md` (Mol* for the molecule; `webgui` for meshes and fields; canvas for (r, z) maps and plots from `plot/data.py`) and the explorer's four controls checked against `webgui`. REV-138: `shoot.cjs` measures non-text contrast. REV-143: `--control-edge` `#7c8290`, mockups re-rendered. REV-141: CON-08 and CON-11 NOTEs | §8.2.19 U5, U7 |

### Grounding

**D1, D2**
- `charge/kernel.py:source_atoms(table, *, sharpness, shift_z_nm)` returns `SourceAtoms` in the model frame. Its `r_nm`, `z_nm`, `width_nm`, `weight_e` and `atom` (row into the table) cover the charged atoms only. `SourceAtoms.table` holds `chain`, `resname`, `resid`, `icode`.
- `charge/kernel.py:volume_density(r_nm, z_nm, r_i, z_i, width_nm)` is one atom's axisymmetric kernel. `SourceAtoms.label(row)` names an atom's residue.
- `charge/stage.py:frame_shift_nm(resolved)` is the membrane centre on a generated mesh. `stored_lattice(artefact)` gives `StoredLattice.grid` (`RadialGrid`, `r_nm`, `z_nm`, `values`).
- `gui/charge.py:charge_image(lattice, *, block=None)` returns `ChargeMap`: `image`, `limit`, a diverging range centred on zero (VER-60). `load_protonation` reads `ProtonationTable.read(Path(artefact.payload["protonation"]))`.
- `examples/07-pdb-to-charged-run/README.md` prepares with `../06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz` and then runs `2wcd.case.yaml`, about five minutes on one core with the `structure` extra.
- The mapping's `sharpness` is `resolved.smearing.sharpness` (`pipeline/case.py:resolve`).
- Mol* is MIT. Its `Viewer.create(target, options)`, `plugin.behaviors.interaction.click` and `plugin.managers.structure.focus.setFromLoci(loci)` serve both directions. NiceGUI 3.13 is MIT and runs on FastAPI (`ui.run_with(app)`, `ui.run(show=False, reload=…)`).

**D3**
- The container has Node 22.23.4, global Playwright 1.63.0, Chromium at `/opt/pw-browsers/chromium-1243/`, and `Xvfb`/`xvfb-run`. Electron is not installed.
- Playwright drives Electron through `_electron.launch`. It needs a display on Linux, hence `xvfb-run`.
- `.claude/scripts/gui/shoot.cjs` takes a manifest of `{id, url, viewport, scheme, wait_ms, expand}` and writes `index.json` with `page_errors`, `console`, `contrast` and `targets`.

**D4**
- `docs/project/modularity-layering.yaml`: the order puts `cli` below `gui`, and no `cli -> gui` edge exists. Its header requires an upward edge to name a finding. `tests/tier1/test_layering.py` checks that every named finding exists.
- `pyproject.toml`: the `gui` extra is `["PySide6>=6.7"]`. `[project.scripts]` has `nanopnp`, `nanopnp-gui` and `nanopnp-probe`. The wheel is `packages = ["src/nanopnp"]` with a `force-include` table.
- `cli/__init__.py` builds subparsers with `subparsers.add_parser`. It has no `gui`.
- `core/errors.py` names `nanopnp.gui.probe:PayloadError` by string. That is the precedent for a string edge.
- `gui/solver.py:SolverProcess` spawns its child with `spawn`, and `cancel()` stops it. A stdin-closed shutdown calls it for each live process.

**D5**
- `tests/conftest.py:write_charged_tube` and its constants (`CHARGED_TUBE_ATOMS`, `CHARGED_TUBE_RADIUS_A`, `write_parallelogram_profile`) build a two-atom case. `tests/tier1/test_gui_charge.py` walks it to `charge` in a module fixture.
- `.claude/hooks/gate.sh` exports `NANOPNP_REQUIRE_GMSH` and `NANOPNP_REQUIRE_APBS` in `run`. `.github/workflows/ci.yml` installs no Node and no browser.
- `.claude/skills/np-gui/render.md`'s `shell` target says "added by WP5.02".

**D6**
- `docs/design/tokens.css` sets light `--control-edge: #868c99` (2.80:1 on `--sel` `#ece7ff`, REV-143).
- `numerics/linear.py:DEFAULT_SOLVER = "umfpack"` through NGSolve's wheel. `knowledge/06-numerics-fem/06-linear-solvers.md` gives "Desktop / pip wheel: umfpack or scipy superlu".
- `knowledge/07-software-stack/05-gui-and-packaging.md` *A fixed colour range needs the scene's keys* is the colour-range fact for REV-137.

### Implementation details

**Item 1.** `spikes/wp5.02/fixture/build.py` (run by `uv run python`) prepares 2WCD as example 07 does into
`fixture/out/`, then `Session(Store(out/"store")).run(Case.load(case), upto="charge")`. It writes:

- `structure.pdb`, the prepared file;
- `lattice.npz` (`r_nm`, `z_nm`, `values`);
- `map.png` with `extent.json` from `charge_image` (its `image`, `limit`);
- `atoms.npz`: `source_atoms` arrays, plus `key` (`"<chain>:<resid><icode>"`) per row, plus `shift_z_nm`.

`server/link.py`:

- `residue_markers(key) -> list[(r_nm, z_nm, q_e)]`;
- `residues_at(r_nm, z_nm, n=5)`. It sums `weight_e·volume_density` per key over atoms within `4·width_nm` and ranks by magnitude.

`server/app.py` routes:

- `GET /api/structure`;
- `GET /api/map` and `GET /api/map/extent`;
- `GET /api/residue/{key}`;
- `GET /api/point?r_nm=&z_nm=`.

**Items 2 and 3.** Each candidate gives the same page:

- Mol* on the left, with a residue strip below it (keyboard-selectable, QR-16);
- the map on the right, with markers;
- a chip "Linked · Unlink";
- the sketcher stub tab;
- `tokens.css` for theming.

Instrumentation is the same in both. After a link update has painted (`requestAnimationFrame` twice), the page
increments `document.body.dataset.drawn`, and sets `data-screen-ready` once loaded. Every control carries `data-control`.

**Item 4.** `measure/size.py` counts non-blank, non-comment lines of hand-written source per candidate. It excludes
lockfiles, `node_modules` and build output.

`measure/redraw.cjs` (Node Playwright, headless) clicks 20 residues in the strip and 20 map points after one warm-up.
It times from dispatch to the change of `data-drawn`.

`measure/install.sh` builds each candidate's wheel and installs it into a fresh `uv venv`. It records `time` and
`du -sh` of the added packages.

`electron/` holds `package.json` (electron, as a devDependency) and `main.cjs`. `main.cjs` spawns
`<candidate's start command> --no-browser --port 0`, reads the line `nanopnp-gui ready <url>`, and calls
`loadURL(url)`. On `will-quit` it closes the child's stdin. `measure/electron.cjs` launches it under `xvfb-run` and
performs one pick each way.

**Item 5.** The report has one table of the six measures × two candidates, each with its command. Publish it with
`/np-gui publish`, and ask the author one `AskUserQuestion`: NiceGUI, React, or neither with a note.

Record the ruling:

- if on 2 November 2026, as row AF4 of record 30 (*Added …, at WP5.02's ruling*); otherwise as a new record 31 (`.claude/skills/np-plan/rulings.md`);
- as `NOTE (the front end, v0.6)` after ADR-004's desktop-wrapper NOTE, naming the stack and the renderers.

**Item 7.** `server.py:main(argv)` uses argparse with `[case] --state NAME --port INT=0 --no-browser --dev`. It:

- binds `127.0.0.1`;
- makes `token = secrets.token_urlsafe(32)`;
- prints `nanopnp-gui ready http://127.0.0.1:<port>/?token=<token>` and flushes;
- opens the browser unless `--no-browser`;
- runs a thread that reads `sys.stdin` to EOF and then shuts down;
- handles SIGINT and SIGTERM the same way.

Middleware:

- a `Host` other than `127.0.0.1:<port>` or `localhost:<port>` gets 403;
- `?token=` correct sets an `HttpOnly`, `SameSite=Strict` cookie `nanopnp_token`;
- neither the token nor the cookie gets 403.

The `cli` subcommand `gui` passes the arguments through `importlib.import_module("nanopnp.gui.web.server").main`.

Record the edge: `{from: cli, to: gui, relation: string, finding: REV-174}`. REV-174 is a new `fixed` row, "The
command line names the workbench's server by string".

A missing `fastapi` is refused, naming the `gui` extra.

| | NiceGUI | React |
|---|---|---|
| Front end | `gui/web/pages.py`, `ui.run_with(app)` | `frontend/` (Vite); `npm run build` → `src/nanopnp/gui/web/static/` (git-ignored; `[tool.hatch.build] artifacts`) |
| Mol*, `webgui` | Served as unmodified files under `gui/web/assets/`, each with its licence | npm imports; `webgui.js` stays the separate file it is |
| Gate, CI | No build step | `gate.sh run` and CI's Tier 1 job run `npm ci && npm run build` (CI: `actions/setup-node`) |
| `--dev` | `reload=True` | Vite dev server on 5173, with `/api` proxied to `--port 8765` |

**Item 8.** `states.py` moves `write_charged_tube`, `write_parallelogram_profile` and their constants out of
`tests/conftest.py`, which then imports them. There is one copy. The states are:

- `charged-tube`: walks `upto="charge"`;
- `refused`: the same case with `concentration_M: -1.0`;
- `empty`: no case.

`st-charge` is the spike's screen. `home` lists the states' case and its stages. The test sets
`NANOPNP_REQUIRE_BROWSER=1` in `gate.sh run`, takes `NANOPNP_CHROMIUM` as Playwright's `executable_path`, and
otherwise skips.

**Item 9.** `checkPage` gains `nontext`. For each `input, select, textarea, button, [role=switch]` it compares border
or outline to the surface behind. After `focus()` it compares the focus ring. For `[aria-selected=true]` it compares
fill to the surface. For each `[data-colorbar]` it compares both end colours. Each needs at least 3. The text goes into
`render.md`'s report list.

**Item 10.** The NOTEs (the browser shell, v0.6) are:

- **CON-08:** "the installed workbench SHALL use UMFPACK, as NGSolve's wheel provides it, or scipy SuperLU";
- **CON-11:** the core stays BSD-3 and depends on no UMFPACK of its own; an installed workbench defaults to NGSolve's UMFPACK, SuperLU selectable; `nanopnp --env` states the combination's GPL-2+ obligation.

### Work items

- [x] e95880a 1. `spikes/wp5.02/{fixture,server}/`, plus a `.gitignore` for `fixture/out/` (D1, D2); done when the four routes answer on the fixture. **Executor:** main
- [x] f1445e7 2. `spikes/wp5.02/nicegui/` (D1); done when both link directions and the stub work by mouse and keyboard. **Executor:** main
- [x] 13cecfd 3. `spikes/wp5.02/react/` (D1); done as item 2. **Executor:** main
- [x] 8554b1f 4. `spikes/wp5.02/{measure,electron}/` and the six measures run (D3); done when every cell of the report's table has a number or a verdict. **Executor:** main
- [ ] 5. `docs/design/spike/report.md`, published; the ruling; the history row and the ADR-004 NOTE (D3); done when the author has ruled. **Executor:** main
- [ ] 6. Compaction checkpoint. **Executor:** main
- [ ] 7. Delete `spikes/` (AF3), with the report linking the last commit that held them; `gui/web/server.py`, the `cli` subcommand, the extra, the layering row and REV-174 (D4); done when VER-61 passes and `nanopnp gui --no-browser --port 0` prints its ready line. **Executor:** main
- [ ] 8. `gui/web/{screens,states}.py`, `st-charge` and `home` in the chosen stack, `tests/tier1/test_gui_screens.py`, VER-78 in §7.2 and Appendix A, `gate.sh`, `ci.yml` (D5); done when VER-78 passes. **Executor:** main
- [ ] 9. `/np-gui render shell` (`render.md`, `render_shell.py`), `nontext` in `shoot.cjs`, the token, the mockups re-rendered, the live loop in `CONTRIBUTING.md` and §8.4.4 (D5, D6); done when `render shell` reports no failure on every state. **Executor:** main
- [ ] 10. The REV-137 table in `workbench.md`; the CON-08 and CON-11 NOTEs; REV-137, -138, -141 and -143 set `fixed`; QR-16's Appendix A row (D6); done when the code and review say so. **Executor:** general-purpose on Sonnet
- [ ] 11. `CHANGELOG.md` under `## [Unreleased]`, `current.md`, and the phase plan's WP5.02 entry delivered. **Executor:** main

> **Outcome — items 1 to 5.** The fixture is 53,760 charged atoms in 3,420 residues; the shared server
> answers its routes. The author ruled NiceGUI (§8.2.30 AF4; ADR-004's NOTE, the front end, v0.6). Evidence:
> [the report](../design/spike/report.md). Where the build differed from the plan: the NiceGUI directory is
> `ngui/`, since `nicegui/` shadows the package; both candidates use Mol*'s standalone bundle, not an npm
> import; the 200 ms line holds for the front end (26 ms p95) and is unmeasured for the whole picture, because
> Mol* alone needs about 800 ms on this container's software GL. Carried to item 8: `data-screen-ready` means
> Mol* has built and drawn once; calls that start the viewer pass a long timeout; a selection moves no camera.

### Verification

| Test | Tier | Identifier | Oracle | Tolerance | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_gui_screens.py::test_ver78_every_state_loads_every_screen_with_its_controls` | 1 | VER-78 | The screen registry: for each state × screen, `data-screen-ready` set, each declared control visible, no `console.error` and no page error, and no request to another origin (each a separate assertion) | Exact | `uv run pytest tests/tier1/test_gui_screens.py` |
| `…::test_ver78_the_server_keeps_its_contract` | 1 | VER-78; ADR-004's NOTE | The ready line matches its pattern; the server binds only 127.0.0.1; a foreign `Host` gets 403; no token and no cookie gets 403; the token sets the cookie; closing stdin ends the server and its solver children within 10 s; SIGTERM does the same | Exact | as above |
| `tests/tier1/test_layering.py` | 1 | VER-61 | `cli -> gui` recorded as `string` with REV-174 | Exact | `uv run pytest -m tier1` |

The spike's six measures are evidence and not tests. Choosing a file through the server is reviewed when a screen
first offers one.

### Out of scope

- FR-33's library link function: the package that builds *Charge on the mesh*.
- The project folder (FR-32), the frame and the four suites: the shell packages (second `/np-plan amend 5`).
- An Electron or other desktop build, installers and signing: after 1.0 (F5; AF1).
- Qt's removal and the restated clauses replacing their originals: the shell's last package.
- The sweep's design round (REV-139): the second amendment.

### Open questions

The framework, at item 5, is the author's call. Nothing blocks the start.
