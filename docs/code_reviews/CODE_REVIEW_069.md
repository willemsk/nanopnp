# Code review 069: WP5.27, Qt's removal and the short guide

2026-11-21 · pull request 200, branch `ccr-867a032b-mcjt88` at `e378143` on `main` · scope: the pull request's 104
files, read from `gh pr diff 200`; the checkout is the pull request's head. Code read in place: `gui/web/selftest.py`,
`cli/workbench.py`, `gui/web/analysis.py`, `gui/web/analysis_tools.py`, `gui/web/runs.py`, `gui/web/queue.py`,
`gui/web/frame.py`, `gui/web/server.py`, `gui/web/study_tools.py`, `gui/run_model.py`, `gui/render.py`,
`io/manifest.py`, `core/paths.py`, `cli/common.py`, `docs/scripts/generate.py`, `gate.sh`, `ci.yml`, the `tier12`
action and the tests the diff changes · level: xhigh as called, with `--fix` · status: completed.

Static review: no `gate.sh`, no `--nightly` and no benchmark. Four read-only measurements were run: the paths *More
values* offers before and after; the renderer exercise with `http_proxy` set and `no_proxy` unset, before and after
the fix; `nanopnp gui --selftest --json` and `--port`; and a hidden Netgen. After the fixes, `ruff check`,
`ruff format --check`, `mypy src/`, `tests/tier1/test_gui_selftest.py` and FR-25's test in `test_analysis.py` pass.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `src/nanopnp/gui/web/selftest.py`, `_exercise_renderer` | The self-test's opener keeps urllib's default `ProxyHandler`, so an `http_proxy` without a `no_proxy` entry for 127.0.0.1 (or a Windows system proxy) receives the request for the child's loopback port. Measured: with `http_proxy=http://127.0.0.1:9` and `no_proxy` unset, the self-test fails `payload 'ngsolve.webgui' failed: URLError: Connection refused` on a sound installation | Fixed: the opener is built with `ProxyHandler({})`; the same run then passes |
| 2 | Important | `src/nanopnp/gui/web/selftest.py`, `_ready_address` | `SERVER_TIMEOUT_S` is checked only between lines: `child.stdout.readline()` blocks, so a server child that hangs before printing its ready line hangs the self-test, the gate's `run` and CI's leg until the job's own timeout, instead of failing at 60 s naming the server | Fixed: a daemon thread reads the child's output into a queue, and the deadline bounds each wait |
| 3 | Important | `src/nanopnp/gui/web/analysis.py`, `AnalysisModel.deviations` | A run whose `manifest.json` is missing or unreadable, or carries no `deviations` group, returns `[]`, and the results explorer then says "None: every switch holds its validated default." The new docstring and the changelog promise "None" only where the manifest counts none, and the removed `run_outcome` refused exactly this case, because it credits the run's numbers to the validated model (FR-25) | Fixed: such a run, or one whose manifest carries no integer `count`, lists one line, `analysis.py:UNKNOWN_DEVIATIONS`; FR-25's test gains the case |
| 4 | Important | `docs/guide/workbench.md`, *Install*; `README.md`, the extras table | The guide says to install "the `gui` extra alone" and then run the self-test, and the README's `gui` row says the self-test checks an installation. With `gui` alone the self-test fails at its third exercise, `payload 'MDAnalysis' failed: ModuleNotFoundError`: MDAnalysis, gemmi, scikit-image, Shapely and PDB2PQR are the `structure` extra, and only Gmsh is skipped when absent | Fixed: both name the `gui` and `structure` extras |
| 5 | Nit | `src/nanopnp/cli/workbench.py`, `_gui` | `nanopnp gui --selftest --json` prints plain lines, though `--json` promises JSON on stdout, and `--port` is accepted and ignored | Fixed: the CLI writes the report through `_emit`, as JSON under `--json`, and refuses `--port` with the project, `--state` and `--dev` |
| 6 | Nit | `src/nanopnp/gui/web/selftest.py`, `_exercise_mesh` | A missing or broken Netgen fails naming `ngsolve`, though `netgen` is a declared payload and ADR-004's NOTE says the self-test fails "naming the payload" | Fixed: Netgen is imported first and fails naming `netgen`; a hidden NGSolve still fails naming `ngsolve` |
| 7 | Nit | `src/nanopnp/THIRD-PARTY-LICENSES.md`, *Your rights under the LGPL components* | "`nanopnp gui --selftest` compares it with the shipped one and says so if it differs": the self-test compares the served bytes with the file at that same path, so a replaced `webgui.js` passes unremarked | Fixed: the notice says the self-test checks that the server serves that file, byte for byte |
| 8 | Nit | `src/nanopnp/THIRD-PARTY-LICENSES.md`, *Checking an installation* | "exercises each compiled payload above once": UMFPACK, OpenBLAS, h5py and the rest of the table are not exercised; the sentence's own list is what runs | Fixed: "exercises these compiled payloads once" |
| 9 | Nit | `data/radii/pdb2pqr_charmm.yaml`, `source.notice` | The PDB2PQR notice says the licence's full text "is in packaging/LICENSES-BUNDLE.md", which this diff deletes; the text is now in `THIRD-PARTY-LICENSES.md` | Skipped: the file carries none of the diff's lines, and the notice is part of the radii document |
| 10 | Nit | `src/nanopnp/gui/web/runs.py`, `_queued`'s `poll` | Every line of every run's log, each frame's progress among them, now joins the queue's log, which grows without bound; each line bumps `Queue.moved`, and `watch_queue` then rebuilds every label of the log. A sweep over an ensemble writes thousands of labels per redraw | Skipped: AW9 asks for the run's lines; a bound or an incremental redraw is a design choice |
| 11 | Nit | `src/nanopnp/core/paths.py`, `LICENCE_NOTICE`; `gui/web/selftest.py` | The removed probe refused to start without its licence notice. Now nothing checks that an installed wheel carries `THIRD-PARTY-LICENSES.md`: `nanopnp --env` prints the path whether or not the file exists, and the CON-11 tests read the source tree | Skipped: adding the check to the self-test widens ADR-004's NOTE, which is the author's |
| 12 | Nit | `knowledge/07-software-stack/05-gui-and-packaging.md`, the netgen loader fix | Names `packaging/nanopnp-probe.spec` as where the fix lives; the file is deleted | Fixed: the path is marked removed at WP5.27 and kept in git history |
| 13 | Nit | `src/nanopnp/gui/web/selftest.py`, `_exercise_skimage` | The comment still says "the probe" | Fixed: "the self-test" |
| 14 | Nit | `docs/scripts/generate.py`, `rewrite_links` over `REGISTERS` | The copied registers' links to pages that are on the site but not copied, such as `review-items.md`'s link to `architecture-survey.md`, are sent to GitHub rather than to the site's page | Skipped: the rewrite serves every copied page, and changing it moves links on the specification and knowledge pages |
| 15 | Nit | `CLAUDE.md`, *The gate before a push* | `gate.sh run` now runs `nanopnp gui --selftest` after the per-push selection, and the list of what `run` runs does not say so | Skipped: an edit to `CLAUDE.md` is the author's |
| 16 | Nit | Commits `d293aa7`, `a8b05fd`, `9fe04ea` against `70d266a` | `CLAUDE.md`: "A change to specified behaviour changes the specification in the same commit." The self-test, the Qt removal and `--env`'s licence line landed before the commit that made VER-43, IF-09, CON-11 and the other NOTEs their clauses | Skipped: fixing it rewrites the branch's history; the NOTEs had stated the text in advance |

Checked and found true: the checkout is the pull request's head, so every file read carries the diff's lines; no
module, test, script or workflow imports a removed name (`gui.app`, `gui.probe`, `gui.widgets`, `case_model`,
`scene`, `render_mesh`, `MeshRequest`, `run_outcome`, `build_offer`, `charge_stages`, the Qt halves of
`gui/geometry.py`); `RunControl.start`'s removal leaves `Entry.run` the model `RunControl.poll` fills, so the queue line
reads the live run; the run's `failed (…)` and `cancelled:` lines replace the dropped diagnosis line; `Rung.index` and
`Rung.total` exist and `rung` clears on each `Stage`; *More values* gains eleven paths and loses the six list members,
and `models` is a header key; `_deviations_payload` writes `count`, `switches` and `contributed`; the server answers
`/api/health` and its `Guard` accepts the cookie urllib's jar returns; `PayloadError` is `EXIT_CASE`; hatchling packs
`THIRD-PARTY-LICENSES.md` from `src/nanopnp/`; no on-site page links to the four registers' excluded sources; the
CI self-test steps run after a passing pytest step only; `release.yml` names no `bundle` job.

Sixteen findings: four important and twelve nits. Nine fixed, seven skipped. No fix changes a ruling of the author.

## Dispositions at `/np-ship`

Each applied fix was read as a diff in the shipping session and kept. Of the seven skipped, decided there:

- **9**: left open as REV-276. The radius set's sha256 is part of every density's provenance, so the notice is
  repointed when the file next changes for a reason of its own.
- **10**: fixed. The Log tab appends the lines it has not shown instead of rebuilding every label, and keeps its
  newest line in view while its reader is at the end (`frame.py:log_rows`, `pin_log`). AW9's copy of every line stays.
- **11**: fixed. `selftest.py:notice_line` fails the self-test naming `THIRD-PARTY-LICENSES.md` where an installation
  lacks it, and CON-11's NOTE says so; `test_con11_an_installation_without_its_licence_notice_fails_the_selftest`.
  The now unused `selftest.main` is removed.
- **14**: fixed. `generate.py:_served` keeps a link to a file the site serves (any of `docs/` outside `mkdocs.yml`'s
  `exclude_docs`) on the site; the strict build and `links.py` (1871 links, none broken) pass.
- **15**: fixed. `CLAUDE.md` says the push gate ends with the self-test.
- **16**: declined. The plan sequenced the clauses as item 9, and each restated text stood in its clause's NOTE,
  marked as landing with WP5.27, from the design document's commit on; no commit ran behaviour the specification
  did not state.

The screen review of the same head (the `gui-reviewer` agent and the impeccable critique, over the render of
`e378143`) added four fixes: the Log tab opens on its newest line; the queue line joins the stage with a dash, not a
second colon; a study's own value names its default ("The study's own. The default is umfpack."); and finding 3's
unknown case. What it left open is REV-275.
