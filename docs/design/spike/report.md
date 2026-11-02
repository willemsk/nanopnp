# The framework spike: one hard screen, built two ways

WP5.02, 2 November 2026, on `v0.5.0`. The screen is *Charge on the mesh* for 2WCD (example 07, 53,760
partial-charge atoms in 3,420 residues of 12 chains): picking a residue of the molecule shows its
atoms on the pore's charge map, and picking a point on the map selects the residue that contributes
most there. Both candidates draw the molecule with Mol* (MIT) and the map as a raster from
`gui/charge.py:charge_image`, and both call the same FastAPI server and data (`spikes/wp5.02/server/`,
`fixture/`). Only the front end differs (§8.2.30 AF2). The code leaves the tree with the framework's ruling (AF3); the commit that last held it is
named at the foot of this report, and its `spikes/wp5.02/measure/` rebuilds every number.

- **NiceGUI** (Python-first): `ngui/main.py` plus a 54-line Mol* bridge in JavaScript.
- **React** (TypeScript, Vite): `react/src/*.tsx`, built into `react/dist/`.

**Where the numbers come from.** One container, 4 cores, no GPU. Chromium draws WebGL with SwiftShader
(software). Timings are medians and p95 of 20 picks each way after one warm-up, 1.5 s apart.

## The six measures

| # | Measure | NiceGUI | React | Command |
|---|---|---|---|---|
| 1 | Hand-written lines (non-blank, non-comment; server excluded) | **169**: 115 Python, 54 JavaScript | **246**: 123 TSX, 56 TS, 15 HTML, 16 CSS, 17 JSON, 19 Python | `python3 measure/size.py` |
| 2a | Click to the map's markers in the page, median / p95 (ms), residue to map | 21.9 / 25.8 | 14.1 / 16.2 | `node measure/redraw.cjs <url>` |
| 2b | The same, map to residue | 19.3 / 26.3 | 16.2 / 22.0 | as above |
| 2c | Click to the second painted frame, median / p95 (ms), residue to map | 839 / 876 | 831 / 857 | as above |
| 2c | The same, map to residue | 838 / 890 | 834 / 899 | as above |
| 2d | Mol* repaint of one selection, no front end in the loop (ms) | about 800 | about 800 | `node measure/molstar-alone.cjs <url>` |
| 3 | States reached by URL with no human step, each with every declared control, no page error | 4 of 4 (`?residue=`, `?linked=0`, `?tab=sketcher`); ready in 6.5, 10.2, 6.4, 1.6 s | 4 of 4; ready in 6.2, 9.5, 5.9, 0.9 s | `node measure/drive.cjs <url>` |
| 3 | A strip button is reached by Tab and chosen by Enter | yes | yes | `node measure/keyboard.cjs <url>` |
| 4 | Added to a fresh venv (14 against 49 distributions); cold, warm install | 85.7 MiB; 2.0 s, 0.24 s | 11.9 MiB; 1.3 s, 0.33 s | `measure/install.sh` |
| 4 | The build a user never runs | none | `npm ci` 10.6 s, `vite build` 1.4 s; `dist/` 160 KiB; `node_modules` 223 MiB (developers and CI only) | as above |
| 5 | Licences of the front end's runtime dependencies | **pass** (below) | **pass** (below) | `node measure/licences.cjs react react-dom molstar` |
| 6 | Opened in an Electron 33 window under Xvfb: residue to map, map to residue, 0 page errors | **works** | **works** | `xvfb-run node measure/electron.cjs <nicegui|react>` |

Both candidates also ship the same unmodified Mol* bundle, `molstar.js` (5.27 MB) and `molstar.css`
(73 KB), as separate files (CON-09's separate-file rule for a renderer).

### What the numbers say

- **The 200 ms line (WB-23) cannot be judged by 2c in this container, and 2d says why.** Mol* alone
  needs about 800 ms to repaint a selection on software GL, so both candidates sit at 830 to 900 ms
  for the second painted frame whatever they do. The front end's own share, 2a and 2b, is 14 to 26 ms
  for both, under the line. A GPU run was not possible here, so whether the whole picture meets 200 ms is
  **not measured**.
- **Speed does not separate the candidates.** React is about 8 ms quicker on the strip direction
  (median 14 against 22 ms); NiceGUI's pick goes over the WebSocket to Python in the same process, React's
  over an HTTP call.
- **Size and weight separate them.** NiceGUI is a third smaller in hand-written lines (169 against 246),
  and the whole of it is in one language except the 54-line Mol* bridge. React needs a build step and Node
  in the gate and in CI, and adds 12 MiB to an install. NiceGUI adds 86 MiB and 49 packages, among them
  `aiohttp`, `orjson` and `docutils`.
- **The desktop window is not a differentiator.** Both candidates work in the same 22-line wrapper
  (`electron/main.cjs`: spawn, read the ready line, `loadURL`). Closing the window closed the server's
  standard input, and no server process was left (`ps` showed none).

### Licences (measure 5)

CON-09's NOTE for v0.6 asks a front-end dependency to be permissive, or LGPL or MPL-2.0 used unmodified as a
separate file.

- **React.** `react`, `react-dom` and `scheduler` are MIT. Mol*'s dependency closure is 199 packages:
  188 MIT, 5 ISC, 3 Apache-2.0, 1 BSD-3-Clause, 1 0BSD and 1 Python-2.0 (`argparse`). No copyleft.
- **NiceGUI.** The JavaScript it serves is Vue 3.5 and Quasar (MIT), Tailwind 4 (MIT), socket.io (MIT)
  and DOMPurify (Apache-2.0 or MPL-2.0). Its Python closure is MIT, BSD, Apache-2.0 and PSF, with three MPL-2.0 packages (`bidict`,
  `certifi`, `orjson`, each used unmodified as a separate package). `docutils` lists GPL among its
  classifiers: its one GPL-3 file is `tools/editors/emacs/rst.el`, which the wheel does not contain.
- Neither candidate fails measure 5.

## What the build taught

1. **Mol* is the cost of this screen, not the framework.** A zoom to a residue on software GL drops the page
   to 2 frames per second for as long as it lasts, so the spike selects and does not move the camera.
   A real GPU does not have this limit; the screen's design must not depend on one, and a `--no-gpu`
   rendering mode for Mol* is worth a line in the workbench's requirements.
2. **A screen is ready when Mol* has built, not when it has loaded.** The first version set `ready` after the
   structure loaded. A click arriving while Mol* was still building was lost in both candidates. Both now
   wait for Mol*'s state to go idle and for one drawn frame. The workbench's `data-screen-ready` (WP5.02
   item 8) has to mean this.
3. **NiceGUI's `ui.run_javascript` times out after one second** unless told otherwise. Mol*'s start takes
   longer, so the first version never reached the code after it. Any Python call that starts the viewer
   passes a long timeout.
4. **The Mol* standalone bundle serves both.** The plan's table has React importing Mol* through npm. The
   spike used the standalone bundle in both so that the viewer is the same file, and typed it `any` in the
   React code. A real React build would import Mol*'s modules, which adds to its size but gives the TypeScript
   types. This favours React in the line count and does not change the ruling's weight.
5. **The sketcher stub costs the same in both.** A canvas and a banner; the real sketcher is a later phase.
6. **Directory name.** The NiceGUI candidate lives in `ngui/`, not `nicegui/` as the plan has it: a directory
   `nicegui/` beside the code shadows the package of that name.

## The decision

|  | NiceGUI | React |
|---|---|---|
| Language of the workbench | Python, with a JavaScript bridge for Mol* and `webgui` | TypeScript, plus the server's Python |
| Build step in the gate and CI | none | `npm ci && npm run build`, Node in CI |
| Added to the install | 86 MiB, 49 packages | 12 MiB, 14 packages |
| Redraw, front end only (p95) | 26 ms | 22 ms |
| Desktop window | works | works |
| Licence | passes | passes |
| Second language to keep | no (one small bridge) | yes (the whole front end) |

Both candidates meet every pre-set test the spike has, so the ruling turns on what each costs to keep: one
language and no build step against a smaller install and the widest set of web components. The plan's
recommendation, stated before the numbers were in, was Python-first if it met the redraw time and wrapped
in a desktop window. On the measures that could be run here it does both.

## The ruling

The author chose **NiceGUI** on 2 November 2026 (§8.2.30 AF4; ADR-004's NOTE, the front end, v0.6). The
NiceGUI candidate's page, bridge and server wiring are the model for the code that lands in `src/`.
