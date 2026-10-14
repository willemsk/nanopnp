---
type: Library Behaviour
title: 5. GUI and packaging
---

## 5. GUI and packaging

| Tool | Licence | Note |
|---|---|---|
| **PySide6** 6.11.1 | LGPL-3 OR GPL-2 OR GPL-3 | **Use this.** LGPL option means no licence conflict |
| PyQt6 | **GPL-3 only** | Avoid unless the project is GPL |
| `PySide6.QtWebEngineWidgets.QWebEngineView` | — | Hosts NGSolve webgui **[tested]**. The earlier "imports cleanly" held on a machine with the GL libraries present; see the caveat below, which is a property of the machine and not of the wheel |
| PyInstaller | — | **Chosen** for the bundle, one-dir (ADR-004, amended 20 September 2026). `collect_all` over `ngsolve`, `netgen` and `ngsolve_openblas`, plus the `netgen-occt` libraries collected by hand (below); `upx=False`, which mangles Qt WebEngine's helper executable |
| briefcase / conda-constructor | — | The other two candidates; not used |

### PySide6 imports are a system-library question, not a wheel question **[tested]** {#pyside6-imports-are-a-system-library-question-not-a-wheel-question}

Measured 20 September 2026, PySide6 6.11.2, in the Linux development container:

```
from PySide6 import QtWidgets            -> ImportError: libEGL.so.1: cannot open shared object file
from PySide6 import QtWebEngineWidgets   -> ImportError: libEGL.so.1: cannot open shared object file
```

`QtWidgets` itself, not only WebEngine. The wheel installs perfectly and `import PySide6` succeeds;
a GL-dependent payload then dlopens and fails. This is the same failure class the gmsh wheel has
(`OSError: libGLU.so.1`, handled at `tests/tier1/test_mesh_quality.py`), which is why the skip idiom
for either is `except (ImportError, OSError)` and never `pytest.importorskip`.

Consequence for testing a GUI: anything that must run on the push gate has to be Qt-free. Widget
construction belongs on the `windows-latest` and `macos-latest` matrix jobs, where Qt's platform
plugin works unaided and `QT_QPA_PLATFORM=offscreen` is all that is needed. Installing system
packages on a Linux gate job to work around this buys Linux coverage at the price of a portability
promise per runner image.

### A missing `libEGL.so.1` can be shimmed for local work, never for the gate **[tested]** {#a-missing-libeglso1-can-be-shimmed-for-local-work-never-for-the-gate}

Measured 20 September 2026. The pre-installed Playwright Chromium carries a real
`libEGL.so`, and symlinking it as `libEGL.so.1` (with `libGLESv2.so` as `libGLESv2.so.2`) into a
scratch directory on `LD_LIBRARY_PATH` makes `from PySide6 import QtWidgets` succeed, a
`QApplication` construct under `QT_QPA_PLATFORM=offscreen`, and the whole Qt widget suite run.
Useful for checking widget code that would otherwise ship having never been executed.

It is **not** a way to get Linux widget coverage on the push gate. It depends on a browser bundle
that has nothing to do with this project, and CON-07's posture is that nothing on the user path
needs a build or an install step. Widget coverage belongs on `windows-latest` and `macos-latest`,
where Qt's platform plugin works unaided.

### `QWebEngineView` loads a webgui document with no GPU at all **[tested]** {#qwebengineview-loads-a-webgui-document-with-no-gpu-at-all}

Measured 20 September 2026, PySide6 6.11.2, Linux, no display and no GPU, with
`QT_QPA_PLATFORM=offscreen` and `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --no-sandbox`. Qt logs

```
QRhiGles2: Failed to create temporary context
Failed to create RHI for backend: OpenGL
```

and then reaches `loadFinished(True)` anyway. So a headless packaging check *can* wait for the
document load rather than merely constructing the view.

What it does not establish is that the scene **rendered**. `WebGLScene.GenerateHTML()` emits a
document that fetches its renderer from `https://cdn.jsdelivr.net/npm/webgui@<version>/dist/webgui.js`,
so on a machine with no network the page loads and the console says `webgui is not defined`.
`loadFinished` is a statement about the document, not about the picture.

### A webgui scene is JSON, costs ~200–320 B per element, and needs no Jupyter **[tested]** {#a-webgui-scene-is-json-costs-200320-b-per-element-and-needs-no-jupyter}

Measured 21 September 2026, P2 `GridFunction` on a unit-square mesh,
`Draw(gf, mesh, order=k, show=False).GetData()` then `json.dumps`:

| elements | order | `GetData` | JSON | per element |
|---|---|---|---|---|
| 224 | 1 | 3.0 ms | 0.045 MB | 202 B |
| 224 | 2 | 2.3 ms | 0.075 MB | 334 B |
| 2,550 | 1 | 15.7 ms | 0.496 MB | 194 B |
| 2,550 | 2 | 25.4 ms | 0.825 MB | 324 B |
| 16,036 | 1 | 157.9 ms | 3.094 MB | 193 B |
| 16,036 | 2 | 142.6 ms | 5.153 MB | 321 B |

Linear in elements to within 5 %. Extrapolated to the 120,917-triangle reference mesh that is
**23.3 MB at order 1 and 38.8 MB at order 2**, built in roughly 1.2 s. A scene of a production mesh
is therefore a file, not a queue payload and not a `setHtml` argument — `QWebEngineView.setHtml`
percent-encodes into a data URL.

`GetData()` runs headlessly and **without `anywidget`**: `netgen.webgui` defines `WebGuiWidget`
inside a `try: import anywidget` and falls back to a stub with the same constructor
(`netgen/webgui.py:423–435`), so `WebGLScene.__init__` succeeds with no Jupyter stack present.
The returned dict is plain numbers and base64 strings, so it crosses a process boundary and
serialises without help.

### `netgen.webgui.GenerateHTML` ignores its `template` argument **[verified]** {#netgenwebguigeneratehtml-ignores-its-template-argument}

Read from the installed source, 21 September 2026:

```text
def GenerateHTML(data, filename=None, template=None):
    if template is None:
        template = _html_template
    ...
    html = _html_template.replace('{render}', jscode)
```

`template` is assigned and never read; the substitution is always into the module global. So a
caller cannot redirect the renderer `<script src=…>` by passing a template, and anything that
needs a different renderer source has to build the host document itself. The document is four lines
plus the render data, so that is cheap — but it is not optional.

The renderer itself is npm `webgui`, `"license": "LGPL-2.1-or-later"` (npm registry metadata,
**[verified]**). Its tarball for 0.2.39 is 503,052 B, and its published `dist.integrity` is
`sha512-yDd6YR7E…Zubqw==`. The 1,206,946 B figure npm reports is the *unpacked* tarball. The file a
page loads, `package/dist/webgui.js`, is **779,484 B**: a minified IIFE that defines the global
`webgui`.

That build **bundles two further works**: three.js r152 (MIT, which keeps its `@license` banner)
and dat.gui 0.7 (Apache-2.0, which keeps no banner). The tarball also carries `src/*.ts`, the
shaders and the vite configuration, so it is the corresponding source of the LGPL part as it
stands. **[tested]**, 22 September 2026.

`cdn.jsdelivr.net` answers this development container's proxy with 403, but
**`registry.npmjs.org` does not**. The tarball downloads here, and its SHA-512 matches the
published integrity exactly. That is how it is vendored: `third_party/webgui-0.2.39.tgz`, with
`webgui.js` shipped from it under `nanopnp/gui/assets/webgui/`.

Loaded from there as a `file:` URL by a host document that is itself a `file:` URL in another
directory, it reaches the page in Qt WebEngine 6.11.2. `renderer_loaded` is true offline, both in
the frozen probe bundle and in a plain `QWebEngineView`. With no GPU, `new webgui.Scene()` then
throws `TypeError: Cannot read properties of null (reading 'getExtension')`: WebGL has no
context, which is a property of the machine and not of the renderer.

### A webgui scene draws on a material *region*, not only on a whole mesh **[tested]** {#a-webgui-scene-draws-on-a-material-region-not-only-on-a-whole-mesh}

Measured 21 September 2026 on a restored four-material ePNP-NS solution, 124 triangles.
`Draw(cf, mesh.Materials("electrolyte|cis|trans"), show=False, order=2).GetData()` succeeds and
returns a smaller scene than the whole-mesh draw of the same field (30.5 kB against 43.1 kB here),
because it carries only the retained elements.

That matters for honesty rather than for size. A field declared on the fluid alone evaluates to
zero inside the membrane, and a whole-mesh draw of a concentration therefore paints a zero *inside
a wall* that a reader cannot distinguish from a converged depletion — which is the same trap
`post/export.py` documents for the IF-07 export, and it is avoided the same way.

The same call draws a **two-component vector** field without special handling: all five fields of
the `epnp-ns` family (the potential, two concentrations, the velocity and the pressure) produce a
scene from one code path, the vector one costing about 1.5x the scalars.

### A fixed colour range needs the scene's keys and the viewer's own settings **[verified]** {#a-fixed-colour-range-needs-the-scenes-keys-and-the-viewers-own-settings}

webgui 0.2.39 has one colour map per scene, and by default it autoscales to the sampled
`funcmin`/`funcmax`, which `Draw(...).GetData()` returns. A diverging map centred on zero, or χ on
[0, 1], needs that range fixed, and the scene keys alone do not fix it. `funcmin`, `funcmax` and
`autoscale: false` in the scene set the defaults. The viewer then reads `gui_settings`, maps its
`autoscale`, `colormap_min` and `colormap_max` onto its `Colormap` settings, and autoscales again
unless `gui_settings.autoscale` is false too. So `gui/render.py` writes all five. Read from the
shipped `webgui.js` and from the scenes the render child writes, 2 October 2026 (WP31 D8). The
fixed range has not been watched drawing in a browser here, because this container has no GPU for
WebGL.

### `QWebEngineView` can be constructed in this container with the Playwright GL shim **[tested]** {#qwebengineview-can-be-constructed-in-this-container-with-the-playwright-gl-shim}

Measured 21 September 2026. With `libEGL.so.1` and `libGLESv2.so.2` symlinked from
`/opt/pw-browsers/chromium-*/chrome-linux/` onto `LD_LIBRARY_PATH`, and
`QT_QPA_PLATFORM=offscreen`, both `from PySide6 import QtWidgets` and
`from PySide6.QtWebEngineWidgets import QWebEngineView` succeed and the whole Tier-1 widget suite
runs — including a `QPainter` repaint into a `QPixmap` and a `QWebEngineView` construction.

This is the §5 shim recorded above, used for the purpose that section already states: checking
widget code that would otherwise ship having never been executed. It stays off the push gate, where
widget coverage remains `windows-latest` and `macos-latest`.

### SIGTERM stops a child busy inside netgen in milliseconds **[tested]** {#sigterm-stops-a-child-busy-inside-netgen-in-milliseconds}

Neither netgen nor NGSolve installs a SIGTERM handler, so the signal's default action ends a
`spawn` child at once even while it is inside compiled meshing code; only a Python-level handler
would defer it until the interpreter is re-entered. Measured: a child in `GenerateMesh(maxh=0.002)`
joined **14 ms** after `terminate()`, exit code −15. `RenderProcess.terminate`'s synchronous join
therefore does not stall the Qt thread, and it is what keeps two render children of one run from
sweeping each other's files. (Codebase review of 2026-09-28.)

### A PyInstaller bundle carries neither OCCT nor OpenBLAS unless told to **[tested]** {#a-pyinstaller-bundle-carries-neither-occt-nor-openblas-unless-told-to}

Measured 22 September 2026: PyInstaller 6.22.3, contrib hooks 2026.7, NGSolve and Netgen
6.2.2606, `netgen-occt` 7.8.1, `ngsolve-openblas` 0.3.33. The Windows build log and a Linux
rebuild of the same recipe in this container agree.

**OCCT.** `import netgen` runs `netgen.load_occ_libs()`, which does three things in order:

1. calls `importlib.metadata.metadata("netgen-occt")`;
2. builds a stem-to-path map from `metadata.files("netgen-occt")`;
3. `ctypes.CDLL`s 28 `TK*` libraries in dependency order, starting with `lib_paths["tkernel"]`.

The `netgen-occt` wheel installs those libraries **outside site-packages**, through its `.data/data`
scheme: `bin/TK*.dll` at the environment root on Windows, and `lib/libTK*.so.7.8.1` on Linux. So
its RECORD names them `../../bin/TKernel.dll`, relative to the dist-info's parent. A one-dir
bundle then fails twice, independently:

- **PyInstaller does not find the libraries.** The build log carries `Library not found: could not
  resolve 'TKernel.dll', dependency of ...\netgen\nglib.dll` for every one of them. `collect_all`
  cannot help, because they belong to no importable package.
- **PyInstaller does collect the dist-info.** So `metadata()` succeeds, and the
  `PackageNotFoundError` no-op branch is not taken. But since Python 3.12, `Distribution.files`
  filters its result through `skip_missing_files`, and from `_internal/` every `../../` entry
  points outside the bundle. The map comes back **empty**, and the first lookup raises
  `KeyError: 'tkernel'`. That is the exact failure of the gated `bundle` job, before any Qt is
  touched.

**The fix makes netgen's own loader work unchanged** (`packaging/nanopnp-probe.spec`):

- collect the existing `netgen-occt` files that match its filter (`*libTK*` or `*.dll`) into the
  bundle root;
- replace the collected dist-info with one whose RECORD names them by bare file name.

**OpenBLAS.** `ngsolve/__init__.py` imports `ngsolve_openblas` and preloads the libraries it
ships as package data. Static analysis collects the module but not the libraries, so the frozen
`import ngsolve` fails with `libopenblas.so.0: cannot open shared object file`.
`collect_all("ngsolve_openblas")` carries them. There is no macOS wheel, and `ngsolve` does not
import it there.

With both fixes, the probe bundle built here runs `--selftest` to completion on Linux under the §5
GL shim. The unresolved-library warnings that remain in the build log are `libopenblas.so.0` and
the optional CUDA libraries of `_ngscuda.so`. The first is satisfied at run time by the preload;
the second is never loaded unless a CUDA solver is asked for.

### The geometry payloads bundle through `collect_all`; Gmsh's library does not **[tested]** {#the-geometry-payloads-bundle-through-collect_all-gmshs-library-does-not}

Measured 29 September 2026 on a Linux rebuild of the probe recipe in this container (WP24 D16, D17):
PyInstaller 6.22.3, MDAnalysis 2.10.0, gemmi 0.7.5, scikit-image 0.26.0, Shapely 2.1.2 with GEOS
3.13.1, and Gmsh 4.15.2. The Windows bundle is the gated `bundle` job's to confirm; nothing here
was measured on Windows.

**MDAnalysis, gemmi, scikit-image and Shapely need nothing but `collect_all`.** It carries
Shapely's GEOS pair from `shapely.libs/`, and the frozen `--selftest` exercises all four. Their
footprint in `_internal/` is:

| Payload | Size |
|---|---|
| MDAnalysis | 45 MB |
| scikit-image | 30 MB |
| gemmi | 6.8 MB |
| Shapely | 5.0 MB, plus 5.6 MB of GEOS |

**Gmsh repeats the OCCT problem, differently.** The wheel installs `gmsh.py` in site-packages and
`libgmsh.so.4.15` in `lib/` at the environment root; on Windows it is `Lib/gmsh-4.15.dll`.
`gmsh.py` does not use metadata to find it. Instead it tries a fixed list of paths relative to its
own `__file__`, and then `ctypes.util.find_library`. The first path is the module's own directory,
which for a PYZ module in a one-dir bundle is `_internal/`. So the library goes to the bundle root,
and Gmsh then loads unchanged. The library is 89 MB.

**`import gmsh` succeeds without its library.** With `libgmsh.so.4.15` removed from the built
bundle, the import prints a warning listing the paths it searched and returns. The first call then
raises `AttributeError: ...: undefined symbol: gmshInitialize`. A probe that only imported Gmsh
would pass on a bundle that cannot mesh. This is why the probe exercises each payload once, and it
is RSK-13's failure in its plainest form.

The whole bundle is 1.3 GB, 501 MB of it PySide6, and builds in 74 s. The five exercises take
0.46 s together, unfrozen. One detail of the exercise: `skimage.measure.find_contours` needs an
ndarray and raises `AttributeError: 'list' object has no attribute 'shape'` on a nested list. The
probe therefore builds its 3 × 3 input with `skimage.morphology.disk(1)`, so that it imports no
undeclared NumPy.

### PDB2PQR and PROPKA bundle through `collect_all`, and fail inside PDB2PQR's run **[tested]** {#pdb2pqr-and-propka-bundle-through-collect_all-and-fail-inside-pdb2pqrs-run}

Measured 2 October 2026 on a Linux rebuild of the probe recipe in this container (WP31 D14, D15),
with PyInstaller 6.22.3, PDB2PQR 3.7.1 and PROPKA 3.5.1. As with the geometry payloads, Windows
is the `bundle` job's to confirm.

**Both are pure Python, and both find their data through `Path(__file__).parent`.** For PDB2PQR
that is `pdb2pqr/dat/`, the force-field and naming files. For PROPKA it is `propka.cfg` and
`protein_bonds.json`. `collect_all` puts both trees beside the modules in `_internal/`. The frozen
`--selftest` then protonates `GLU 18`–`LEU 26` of 2WCD chain A to +0 e at pH 2 and −3 e at pH 8,
the unfrozen values. The cost to the bundle is small:

| Payload | Size in `_internal/` |
|---|---|
| PDB2PQR | 1.1 MB, of which `dat/` is 0.50 MB |
| PROPKA | 0.34 MB, as 26 source files and its two data files |
| GridDataFormats | 0.12 MB, as source files |

The whole bundle is 1.23 GB and builds in 2 min 25 s from clean. The exercise takes 0.82 s unfrozen
in a fresh process, and 0.23 s once warm.

**A missing data file surfaces out of PDB2PQR's run.** With `propka.cfg` removed from the built
bundle, the run raises `FileNotFoundError` naming the file. With `pdb2pqr/dat/` removed, it raises
a bare `AssertionError` from `pdb2pqr.io.test_for_file` (`assert dirpath_dat.is_dir()`). Both come
out of `pdb2pqr.main.run_pdb2pqr`, so a probe that named the failing call would name PDB2PQR for
PROPKA's missing file. The probe names the library whose code is in the traceback instead. PDB2PQR
calls PROPKA and PROPKA never calls back, so a traceback that enters PROPKA's directory is PROPKA's
failure. Rebuilt and rerun, the bundle without `propka.cfg` fails naming `propka`.

**`module_collection_mode="py"` puts the modules on disk.** With it set for `propka`, `MDAnalysis`
and `gridData`, each package's modules are in `_internal/` as `.py` files. MDAnalysis keeps its
compiled extensions beside them, at the same 45.7 MB. A traceback through them then carries real
file paths, which is what lets the probe tell PROPKA's failure from PDB2PQR's.

**Without a titration method, the pH reaches nothing.** With `--with-ph` and
`--titration-state-method` removed, PDB2PQR runs cleanly and gives equal charges at pH 2 and pH 8
(section 3). So the probe compares the two charges, and fails naming PROPKA when they are equal.

In this container the frozen `--selftest` stops at Gmsh, because `libGLU.so.1` is not installed.
The figures above come from a local build whose selftest left Gmsh out. That edit was never
committed.

### The geometry tab's view-models stay under the schema's cost **[tested]** {#the-geometry-tabs-view-models-stay-under-the-schemas-cost}

Measured 29 September 2026, best of three fresh processes, warm cache:

| Module | Cost |
|---|---|
| `nanopnp.gui.geometry` | 157 ms |
| `nanopnp.gui.assess` | 52 ms |
| `nanopnp.gui.run_model` | 200 ms, the comparison |

Neither of the two new modules brings in PySide6, NGSolve, Netgen, NumPy, MDAnalysis,
scikit-image, Shapely or Gmsh. `nanopnp.gui.assess` imports `geometry.contour`, and with it
scikit-image, only inside the spawned child. A drag on the editor canvas can be driven offscreen by
sending `QMouseEvent`s through `QApplication.sendEvent`: press, move, release. That is how
`test_gui_widgets.py` asserts it.

### `nanopnp.io.case` pulls in neither NGSolve nor NumPy, and costs 250–350 ms **[tested]** {#nanopnpiocase-pulls-in-neither-ngsolve-nor-numpy-and-costs-250350-ms}

Measured 20 September 2026 on the development interpreter (3.12). After `import nanopnp.io.case`,
`"ngsolve" in sys.modules` and `"numpy" in sys.modules` are both `False`. The cost is pydantic and
PyYAML building the `nanopnp/case/v1` model tree, paid once.

So a caller can enumerate, display and validate an entire case document without the solver — which
is what lets a schema-generated editor stay near the CLI's 56 ms stage-introspection budget in
spirit, with NGSolve imported only in whatever process actually solves. `io/case.py` imports only
`core` at run time: the registry checks that need `materials` and `physics` live in
`pipeline/checks.py`. After `import nanopnp.io.case` the only `nanopnp` subpackages in
`sys.modules` are `core` and `io` **[tested]**, 6 October 2026. `import nanopnp.pipeline.case`,
which `load_case` and `resolve` come from, also loads `charge`, `density`, `geometry`, `materials`,
`mesh`, `numerics` and `physics`, and still leaves `ngsolve` and `numpy` out of `sys.modules`; that
holds because those modules defer their own NGSolve and NumPy imports.

**Re-measured 20 September 2026 on an idle container: 349 ms cold (no `__pycache__`), 253 ms warm**,
against the 622 ms first recorded the same day. Neither cache state reproduces 622 ms here, so that
figure was taken under load or by a different method. **Treat the absolute number as
machine-dependent and the ratio as the fact**: importing the case schema costs roughly what one
NGSolve import (~370 ms) costs, and the load-bearing half — neither `ngsolve` nor `numpy` in
`sys.modules` afterwards — is re-confirmed and is not a timing claim at all.

### The desktop shell's view-model layer costs what the schema costs **[tested]** {#the-desktop-shells-view-model-layer-costs-what-the-schema-costs}

Measured 20 September 2026, best of three on an idle container, warm cache:

| Module | Cost | What it pulls in |
|---|---|---|
| `nanopnp.io.case` | 253 ms | pydantic and PyYAML building the `nanopnp/case/v1` model tree |
| `nanopnp.gui.case_model` | 251 ms | the above, and about a millisecond of its own |
| `nanopnp.gui.run_model` | 273 ms | the above, plus `io/manifest.py` and `pipeline/run.py` |
| `nanopnp.gui.solver` | 73 ms | `core/errors.py` and `multiprocessing`; everything else is deferred into the child |
| `nanopnp.gui.probe` | 59 ms | `core/paths.py` only — every payload is deferred |
| `nanopnp.cli` | 62 ms | the comparison, and the budget the deferred-import rule protects |

After importing all three view-models, **none** of `PySide6`, `PyQt5`, `PyQt6`, `ngsolve`, `netgen`
or `numpy` is in `sys.modules` — asserted in a subprocess by
`tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve`. The
editor therefore enumerates and validates the whole schema at the cost of the schema, and a shell
that is only browsing a case never pays for a solver or a toolkit.

---

