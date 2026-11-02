---
type: Ruling Record
title: "8.2.30 WP5.02's plan: the spike's candidates and the desktop wrapper, agreed 2 November 2026"
description: "Records the author's rulings at WP5.02's plan: the workbench keeps a desktop wrapper such as Electron possible and the spike measures it; the two candidates are NiceGUI and a React application over one FastAPI server; the spike's code leaves the tree once the framework is ruled, its report kept; and, added at the spike's ruling, the workbench's front end is NiceGUI."
---

#### 8.2.30 WP5.02's plan: the spike's candidates and the desktop wrapper, agreed 2 November 2026

Rulings by the author on 2 November 2026, at `/np-plan wp 5.02`, after `v0.5.0`. The author gave a note with the
command, in their words: "I want to have the option to package the app as a desktop application using a framework like
electron in the future." Four questions were put through `AskUserQuestion` in one call. The author took the
recommendation on each. The letter series continues at AF.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AF1 | **The workbench keeps a desktop wrapper possible, and WP5.02 measures it.** A wrapper such as Electron is not built in v0.6: installers stay after 1.0 (§8.2.6 F5; §8.2.17 S12). Nothing in the shell rules one out. The front end reaches its server only through relative URLs. It fetches nothing from a network at run time. A file or folder is chosen through the server, not by a browser upload. `nanopnp gui --no-browser --port 0` starts the server on the loopback interface, writes one ready line naming its address to standard output, and stops its builds and their child processes when its standard input closes or it is signalled. The spike opens each candidate in a minimal Electron window and reports whether the hard screen's link works there | A wrapper later spawns the same server and loads the address it prints. The server's contract is fixed in WP5.02, before any screen depends on it. Electron is a development tool of the spike only and never reaches the wheel or the gate | ADR-004's NOTE (the desktop wrapper), in this commit; the Phase 5 plan's WP5.02 entry, in this commit |
| AF2 | **The spike's two candidates are NiceGUI, Python-first, and a React application built by Vite in TypeScript.** Both run over one FastAPI server that holds the fixture and the link, so the comparison measures the front end alone. Both draw the molecule with Mol*; fields stay with `webgui` | S8's two families, each represented by its strongest member for this screen. NiceGUI runs on FastAPI and ships its Vue layer prebuilt (CON-07). React has the widest set of docking, Electron and Mol* examples | WP5.02's plan, in this commit |
| AF3 | **Once the framework is ruled, both spikes leave the tree and the report stays.** `docs/design/spike/report.md` keeps the numbers and links the commit that held both candidates. The chosen stack's code lands in `src/` in the same PR | The evidence can be rebuilt from history, and the tree carries no dead code | WP5.02's plan, in this commit |

Added 2 November 2026, at WP5.02's item 5, after the spike's six measures (`docs/design/spike/report.md`). One question was put through `AskUserQuestion` with the report's decision table. The author took the recommendation.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AF4 | **The workbench's front end is NiceGUI, written in Python over the FastAPI server.** Both candidates passed every pre-set test: the link in both directions, four states by URL, permissive licences, and an Electron window. NiceGUI is 169 hand-written lines against React's 246, needs no build step in the gate or CI, and keeps the workbench in one language. It adds 86 MiB and 49 packages to an install where React adds 12 MiB and 14. The front end's own redraw is 26 ms p95 for it and 22 ms for React. Whether the whole picture meets WB-23's 200 ms is not measured: Mol* alone needs about 800 ms to repaint a selection on this container's software GL | Mol* serves the molecule as its unmodified standalone bundle, a separate file (CON-09); `webgui` serves meshes and fields; (r, z) maps and plots are drawn on a canvas from `plot/data.py`. JavaScript is the bridge to those renderers and nothing else. The 200 ms line is measured on a machine with a GPU in the package that builds the first Study screen. Python calls that start the viewer pass a long timeout, and a screen's `data-screen-ready` means Mol* has built | ADR-004's NOTE (the front end, v0.6), in this commit; the Phase 5 plan's WP5.02 entry, in this commit |
