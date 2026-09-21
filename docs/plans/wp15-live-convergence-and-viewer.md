# WP15 — Live convergence and the field viewer

**Status: delivered, 21 September 2026.** Written 21 September 2026, after WP14 delivered the packaging
probe, the schema-generated case editor, run control over a spawned solver process and the result
panel. WP15 inherits four things from it: the `RunEvent` union as the channel, the Qt-free
view-model discipline, a `MainWindow` laid out to take further tabs, and the probe's answer to the
bundling question the viewer is built on.

This package belongs to [Phase 1, solver core](phase-1-solver-core.md) §WP15. `SPECIFICATION.md`
governs; every identifier below is a pointer into it, not a restatement of it. Where this plan and
the specification disagree, this plan is the thing that is wrong. One amendment is needed and is
made in the same commit: **VER-44** is added to §7.2, and Appendix A maps **IF-09** and **QR-11**
onto VER-43 and VER-44 together.

## Execution brief

### Scope

Three deliverables, in this order.

**The structural hook, first.** `solve/stage.py` already builds `on_rung(index, rung)` and
`on_step(step: NewtonStep)`, and the residual reaches the caller **only inside a `:.3e` string**.
A convergence plot's whole subject is six or more orders of magnitude of that number. WP15 adds a
structural hook that forwards the rung and the step as data and **must not** parse the progress
caption (WP14 §Design 2; the clause VER-43 already carries for stage transitions).

**Then the live convergence plot**, fed from that hook across the process boundary and drawn from a
Qt-free view-model that owns the log mapping, the per-rung banding and the axis ranges.

**Then the field viewer**: `ngsolve.webgui` in a `QWebEngineView`, bound to a real solution
restored from a finished run.

Completes **IF-09** and discharges **QR-11**; with WP14 it meets the GUI half of Phase-1
criterion 5. Touches **FR-27**, **QR-12**, **NUM-16**, **NUM-18**, **CON-09**, **CON-11**, **§5.3.2**.

**This brief exceeds the 1,200-word target, at about 2,500.** Fifteen decisions is what three
deliverables over one process boundary cost, and eleven of them settle a correctness, licensing or
honesty-of-display question that implementation would otherwise re-decide. The package is not split
because the plot and the viewer share the render-side discipline and both are verifiable inside one
PR, which is the test §Scope of one work package sets. Nothing required was cut to meet the count;
the measurements the decisions rest on are in §Design, outside the budget.

### Requirement and section pointers

| Need | Read |
|---|---|
| What the interface must cover | `SPECIFICATION.md` IF-09, QR-10, QR-11, ADR-004, §8.1's GUI-increment table, §8.2 criterion 5 |
| What VER-43 already asserts, and what VER-44 adds | `SPECIFICATION.md` §7.2 VER-43; this plan's §Spec and plan amendments |
| The convergence criterion the plot may and may not claim | `SPECIFICATION.md` NUM-16 and its NOTE, NUM-18; `CLAUDE.md` *Numerics rules* |
| The seam and the discipline inherited | `wp14-gui-shell-packaging-probe.md` §Design 2 and §Design 4 and their Outcomes |
| The shell as delivered | `src/nanopnp/gui/` — `solver.py`, `run_model.py`, `case_model.py`, `widgets/`, `app.py`, `probe.py` |
| The plumbing to extend | `src/nanopnp/core/stages.py` (`Progress`, `CancelToken`, `StageHook`, `Stage`); `io/run.py` (`run_case`, `run_document`, `_resolve_stage`); `solve/stage.py` (`_instrumented`); `solve/newton.py` (`NewtonStep`, `damped_newton`); `solve/continuation.py` (`Rung`, `run_ladder`) |
| How a finished run becomes a live `GridFunction` again | `src/nanopnp/solve/state.py` module docstring and `restore()` |
| The field vocabulary and the §6.3 scaling the viewer must reuse | `src/nanopnp/io/fields.py` (`attribute_name`, the scale table) |
| Licence and packaging constraints | `SPECIFICATION.md` CON-07, CON-09, CON-11, CON-13, ADR-004; `.knowledge/07-software-stack.md` §5 and §6; `packaging/LICENSES-BUNDLE.md` |

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | How a Newton step reaches the shell | One protocol, `SolveHook`, in `core/stages.py`, with two methods — `rung(name, stage, index, total, reporting, tolerance)` and `step(iteration, residual, update, damping, trials, forced)` — threaded as a single optional `on_solve` keyword through `run_case` → `run_document` → the solve stage. Plain scalars only, so `core/stages.py` imports nothing from `solve/` | `StageHook`'s own rationale one level down; WP14 §Design 2. Two methods rather than two parameters keeps the threading to one object, and `rung` always precedes the steps it scopes |

> **Outcome — `rung` carries two arguments this table did not settle, and both are load-bearing.**
> `reporting` because D3 turned out to be wrong (see its own Outcome): the silence of a rung has two
> causes and is identical from the far side, and only `_instrumented` — where the callback is or is
> not injected — can tell them apart, so the distinction travels as data from the same test that
> makes it (`solve/stage.py`, `reporting = tuple(isinstance(rung.model, CoupledModel) ...)`).
> `tolerance` because D6's annotation is measured against NUM-16's relative tolerance, and the
> alternative was for `gui/convergence.py` to import `solve.newton` for a default the run may not be
> using — which would have cost the Qt-free view-model layer its NGSolve-free guarantee for a
> number the solver already holds. Both are asserted in `tests/tier1/test_solve_hook.py`.
| D2 | How that hook reaches `SolveStage` without widening the twelve-stage `Stage.run` | A `runtime_checkable` capability protocol `SolveReporting` with `with_solve_hook(hook) -> Stage`; `_resolve_stage` rebinds the stage only when it satisfies the protocol. The hook is **not an input**: the artefact key is computed from the unbound stage before rebinding, and a watched run must land on the same cache entry as an unwatched one | A Newton hook is solve-specific; eleven stages should not grow a keyword they ignore. Hash invariance is asserted, not assumed (§5.3.2) |
| D3 | The rungs that emit no steps | Both `rung` and `step` cross the boundary. The plot's x-axis is **the ladder**, one labelled band per rung; a rung that emitted no step is an empty labelled band reading that it is not a Newton solve, never a line interpolated across the gap | `on_step` is injected only when `isinstance(rung.model, CoupledModel)` (`solve/stage.py:454`), so NUM-18 rungs 1–2 are silent by construction |

> **Outcome — "it is not a Newton solve" is false for three rungs in twelve, and the band says which
> silence it is.** Measured on the default ladder of an `epnp-ns` case at 0.1 M and 20 mV: of its
> twelve rungs, **two** take no callback (`1-pb-linear`, `2-pb`) and **three** are coupled rungs that
> reported nothing because `damped_newton` found the transferred residual already at or below
> `max(rtol·initial, atol)` and returned before its first step — `3-equilibrium-pnp`,
> `7-corrections`, `8-steric`, each recording `iterations: 0`. That is the NUM-16 warm-start case,
> not a missing record, and annotating it "not a Newton solve" would state something about the
> solve that is not true. So `rung` carries `reporting` and `Band.note()` has two empty-band
> branches. The rest of D3 stands: the axis is the ladder, one polyline per band, never across one.
> Recorded in `.knowledge/06-numerics-fem.md` §5.1 **[tested]**; VER-44 amended in the same commit.
| D4 | A solve served from the store | Emits no rungs and no steps. The panel says *that*, by name, rather than showing an empty plot | `walk.store.get_or_compute`; assert, don't hope. An empty plot would read as instant convergence |
| D5 | `NewtonStep` gains `update` | Yes — the relative update norm on the **undamped** direction, already computed at `newton.py:308` and already half the NUM-16 criterion. A residual-only plot shows six orders of a number that is not the test the solver converged on | NUM-16 NOTE; `CLAUDE.md` *Numerics rules*. `NewtonResult.summary()` does not serialise `history`, so no manifest key, run-record field or artefact hash moves — asserted in both directions |
| D6 | What the plot may claim | **No convergence threshold line.** The criterion is per rung and is *either* the residual test *or* the update test; one drawn line would claim a criterion the solver does not use. Each band is annotated with which test closed it, and NUM-16 forced steps are marked | NUM-16 |

> **Outcome — "which test closed it" is not knowable, and the band claims only what it can prove.**
> The two tests are not exclusive and `damped_newton` short-circuits on the residual one, so "which
> closed it" would require the entry residual, which is unknown when the rung is announced. What is
> provable from the step record and the rung's own tolerance is the *exclusion*: a forced last step
> is barred from the update test by NUM-16, and a last relative update above the tolerance fails it —
> either way the residual test is the only one that can have ended the rung. Otherwise the band
> reports the update test as met, without claiming the residual test was not. `Band.closed_on()`,
> asserted in all three branches in `tests/tier1/test_gui_viewmodels.py`. VER-44 amended to match.
| D7 | How the plot is drawn | Hand-stroked `QPainter` polylines in a plain `QWidget`. No new dependency and no PySide6-Addons payload for PyInstaller to find; the log mapping, decimation, banding and tick selection live in the Qt-free view-model and are asserted on the push gate, where `PySide6.QtWidgets` does not import at all | WP14 §Design 4 Outcome; CON-07, ADR-004's one-dir bundle |
| D8 | What the field viewer consumes | The **live `GridFunction`**, rebuilt by `solve.state.restore()` from a finished run's `state.npz` in a **separate spawned render process** — not the IF-07 XDMF export, and not a scene made at the tail of the solve child | webgui wants a live `GridFunction` and the XDMF pair is a P2 node set for a reader. `restore` is a gate, never an adaptation, so the scene is the operator that was actually solved. A run from an earlier session then renders by the same path, at no extra code |
| D9 | How the scene crosses the boundary | As a **file**. The render child writes the scene JSON and its host document; the parent loads it with `QUrl.fromLocalFile`. Never through the queue, never through `setHtml` | Measured: 193 B/element at order 1, 321 B/element at order 2 → **23–39 MB** on the 120,917-element reference mesh (§Design 1) |

> **Outcome — two files, one field's pair kept.** The document *embeds* the scene rather than
> fetching the JSON as a subresource: whether Chromium lets a `file://` document load a `file://`
> script is a policy question that cannot be settled on a machine where Qt WebEngine cannot be
> constructed at all, and a document that silently failed to load its data is precisely the blank
> panel QR-12 is written against. That costs two copies, so the child removes the previous field's
> pair when it renders another — bounding a run directory at one scene rather than five, and making
> a field switch a re-render of about a second at reference size rather than tens of megabytes kept.
> Collapsing the two into one subresource load is a one-line change for whoever can watch a picture
> draw. Asserted in `tests/tier1/test_gui_render.py`; `setHtml` is asserted *never called* in
> `tests/tier1/test_gui_widgets.py` by replacing the method with one that fails the test.
| D10 | Where those files live | `viewer/` inside the run directory, never registered as an artefact and never hashed. It is a display artefact, and §5.3.2's "a cancelled run writes no artefact" must keep meaning what it says | §5.3.2 |
| D11 | Field names and units | The render child enumerates the model's components and names them with `io/fields.attribute_name()` under the same §6.3 scale table the XDMF export uses. No field name, unit or model name is written in `gui/` | The `VOCABULARY` guard in `tests/tier1/test_gui_viewmodels.py`; one scaling, never a second |

> **Outcome — and on the field's own *region*, not the whole mesh.** `Draw(cf, mesh.Materials(...))`
> works and returns a smaller scene **[tested]**, which matters for honesty rather than size: a field
> declared on the fluid evaluates to zero inside the membrane, so a whole-mesh draw of a
> concentration paints a zero *inside a wall* that a reader cannot distinguish from a converged
> depletion — the same trap `io/fields.py` documents for the export, avoided the same way. All five
> fields of the family draw from one code path, the two-component velocity included. The `VOCABULARY`
> guard is extended with `phi_V`, `u_m_s`, `p_Pa` and `mol_m3`.
| D12 | Whether the picture drew | `loadFinished` is a statement about the document. After it, the widget runs one `runJavaScript` readiness probe; if the renderer global is absent or the scene did not initialise, the panel is replaced by a diagnostic naming the renderer source it tried | QR-12; `.knowledge/07` §5 records `loadFinished(True)` with `webgui is not defined` |
| D13 | Where the renderer JavaScript comes from | **Open, OQ-1.** Recommended: ship `webgui@0.2.39/dist/webgui.js` as package data, so a bundle draws offline. Until that ruling, the CDN URL `netgen.webgui` already hard-codes, with D12's probe and the limitation recorded. The source is one constant behind one function either way | npm `webgui@0.2.39` is **LGPL-2.1-or-later**, 1,206,946 B unpacked (§Design 2). Vendoring redistributes it, which is a CON-09 change and the author's call |
| D14 | Not `netgen.webgui.GenerateHTML` | We build the host document ourselves from `WebGLScene.GetData()`. `GenerateHTML(data, filename, template)` takes a `template`, assigns it, and then substitutes into `_html_template` regardless — the argument is dead | `netgen/webgui.py:830–837`, read (§Design 2) |
| D15 | Scope of the picture | Steady state, the meshed (r, z) half-plane exactly as computed, one field at a time. No mirroring, no deformation warp, no streamlines | N3, N4; §6.3. Mirroring is a picture of something the solve never discretised |

### Work items

In dependency order. Read the Design section named before touching the item.

| # | Item | Files | Identifiers | Design |
|---|---|---|---|---|
| 1 | `NewtonStep` gains `update`, populated from the existing `relative_update` | `solve/newton.py` | NUM-16, D5 | 4 |
| 2 | `SolveHook` and `SolveReporting` protocols | `core/stages.py` | FR-27, D1, D2 | 3 |
| 3 | `on_solve` threaded through `run_case`, `run_document` and `_resolve_stage`, rebinding only a `SolveReporting` stage, after the key is taken | `io/run.py` | FR-27, §5.3.2, D2 | 3 |
| 4 | `SolveStage.with_solve_hook`; `_instrumented`'s `on_rung`/`on_step` also call it, leaving every progress message byte-identical | `solve/stage.py` | FR-27, D1, D3 | 3 |
| 5 | `Rung` and `Iteration` variants on `RunEvent`, a `QueueSolve` adapter, `_worker` passing it | `gui/solver.py` | IF-09, VER-44 | 3 |
| 6 | `RunModel` branches for the two new variants | `gui/run_model.py` | IF-09 | — |
| 7 | `ConvergenceModel`: bands, series, decimation, axis ranges, silent-rung and cache-hit states. Qt-free, NGSolve-free | `gui/convergence.py` | VER-44, D3, D4, D6 | 4 |
| 8 | The render child: restore, enumerate fields, build the scene and the host document, write `viewer/` | `gui/render.py` | VER-44, D8–D11, D14 | 1, 2 |
| 9 | `SceneModel`: the field list, the current selection, the scene path, the failure states. Qt-free, NGSolve-free | `gui/scene.py` | VER-44, D11 | 2 |
| 10 | The `QPainter` plot widget | `gui/widgets/convergence.py` | QR-11, D7 | 4 |
| 11 | The `QWebEngineView` viewer widget, its field selector and the D12 readiness probe | `gui/widgets/viewer.py` | QR-11, D9, D12 | 2 |
| 12 | Two further tabs on `MainWindow` | `gui/app.py` | QR-11 | — |
| 13 | VER-44 in §7.2 and the Appendix A rows for IF-09 and QR-11 | `SPECIFICATION.md` | IF-09, QR-11 | — |
| 14 | The §Design measurements into `.knowledge/07-software-stack.md` §5 | `.knowledge/` | — | 1, 2 |
| 15 | *Conditional on OQ-1*: the renderer asset, its wheel inclusion, its `LICENSES-BUNDLE.md` line, the CON-09 amendment, and its entry in the probe's `PAYLOADS` | `pyproject.toml`, `packaging/`, `SPECIFICATION.md`, `gui/probe.py` | CON-09, CON-11, RSK-13 | 2 |

> **Outcome — items 13 and 14 were delivered with the plan; item 15 is deferred, twice over.**
> §7.2's VER-44 and the Appendix A rows for IF-09 and QR-11 landed in the plan commit (`f4fecdb`),
> as did §Design 1's and §Design 2's measurements in `.knowledge/07` §5; the implementation commit
> **amends** VER-44 for what D3 and D6 turned out to be, and adds two further findings to the
> knowledge base. Item 15 is not done: OQ-1 has had no ruling, and it could not be implemented in
> this session even under a "yes", because `cdn.jsdelivr.net` answers the development container's
> proxy with 403 and the file cannot be fetched to be vendored (§Design 2 predicted exactly this).
> The renderer source stays one constant behind `renderer_source()`, the probe's `PAYLOADS` is
> untouched, and no CON-09 amendment is made. What the deferral costs is recorded under OQ-1 below.

### Verification

Every row runs under `uv run pytest` unless stated. Tier 1 throughout: nothing here is an analytic
benchmark, and the one number that must be right is asserted against the solver's own record.

| Test file | Tier | Identifiers | Assertion and oracle |
|---|---|---|---|
| `tests/tier1/test_newton.py` | 1 | NUM-16, VER-44 | `NewtonStep.update` equals `‖δu‖ / max(‖u‖, reference_norm)` on the undamped direction for every recorded step, and `NewtonResult.summary()` gains no key — so no manifest, run record or artefact hash moves. Oracle: the norms recomputed in the test from the same direction vector; exact equality |
| `tests/tier1/test_solve_hook.py` (new) | 1 | FR-27, §5.3.2, VER-44 | The hook sees every rung of the ladder, in order, with its NUM-18 stage number; steps arrive inside the rung that scopes them; a non-`CoupledModel` rung yields a `rung` call and no `step` calls; **the artefact hash is identical with the hook and without it**, and a second run served from the store emits nothing at all. Oracle: `LadderResult.rungs` and the store's hit counter |
| `tests/tier1/test_gui_solver_process.py` | 1 | VER-44, FR-27, IF-09 | A real spawned run yields `Rung` and `Iteration` events; every residual is a `float`, not a string; the last `Iteration.residual` of the final rung **equals** that rung's `newton["residual"]` in the run record exactly. This is what makes the plot's numbers the solver's numbers rather than a parse of a caption |
| `tests/tier1/test_gui_viewmodels.py` | 1 | VER-44, IF-09 | `ConvergenceModel` bands the ladder, marks a silent rung as not-a-Newton-solve, keeps the iteration index monotone within a band, and names the cache-hit state distinctly from the no-data state; `SceneModel` offers only the field names the render child reported; `gui/convergence.py` and `gui/scene.py` import neither PySide6 nor NGSolve, asserted on `sys.modules` in a fresh subprocess; the `VOCABULARY` guard is extended to field and unit names |
| `tests/tier1/test_gui_render.py` (new) | 1 | VER-44, D8–D11, D14 | The render child restores a finished run and writes a scene whose JSON round-trips; its field list equals `attribute_name()` over the model's components; the host document references the configured renderer source and carries no second rendering path; a run directory with no `state.npz`, and a `state.npz` that fails the `restore` gate, each produce a named diagnostic rather than an empty scene (QR-12) |
| `tests/tier1/test_gui_widgets.py` | 1 | VER-44, QR-11, CON-09 | The plot widget paints a real `ConvergenceModel` without raising under `QT_QPA_PLATFORM=offscreen`; the viewer widget loads a **file URL** and `setHtml` is never called; the D12 probe reports a missing renderer as a diagnostic. Skipped on `(ImportError, OSError)`, so measured on `windows-latest` and `macos-latest` |
| `tests/tier1/test_gui_probe.py` | 1 | RSK-13, CON-11 | Unchanged, plus — under OQ-1 yes — the renderer asset is named in `PAYLOADS` and travels with the bundle |
| Gate | — | — | `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest` |

Runtime budget: WP14 measured the whole Tier-1 GUI suite at 4.0 s, of which 2.9 s is real spawned
runs. `test_gui_render.py` adds one `restore` plus one `GetData` on a small mesh — under 0.2 s at
the sizes §Design 1 measures. If the suite passes ~8 s, the render test takes the same case fixture
the solver-process test already builds rather than a second one.

> **Outcome — two oracles are better than the ones this table named, and one row moved file.**
>
> - `NewtonStep.update` is asserted against the **accepted states**, not against a direction vector
>   read back: the loop takes `x_k = x_{k-1} − λ·P·δu`, so the full direction is recoverable from
>   two iterates and the damping factor, and nothing in that reconstruction passes through the
>   quantity under test. It agrees to the last bit on every step, and the test also asserts that the
>   recorded value is *not* the damped one — which on this problem's opening steps differs by the
>   factor 0.2 and would otherwise pass every other assertion.
> - The spawned-run row compares against the **manifest's** solver group, not the run record: the
>   run record carries artefact hashes and quantities, and the per-rung `newton` block lives in
>   `manifest.json`. Floats there are hex-encoded, so the test decodes with
>   `core.hashing.decode_floats` and compares exactly.
> - `tests/tier1/test_solve_hook.py` additionally asserts that **only** stage 10 satisfies
>   `SolveReporting`, in both directions, which is the mechanical form of D2's argument.
>
> **Measured, 21 September 2026.** The whole Tier-1 GUI and hook set —
> `test_gui_viewmodels.py`, `test_gui_solver_process.py`, `test_gui_render.py`,
> `test_gui_probe.py`, `test_solve_hook.py` — runs in **6.4 s** on an unloaded container, of which
> the two real spawned runs and the render fixture's solve are about 5 s. `test_gui_widgets.py`
> skips on the push gate; under the `.knowledge/07` §5 GL shim all 13 of its cases pass, in 0.6 s
> warm and 6.6 s on a cold Qt WebEngine start — including the `QPainter` repaint into a `QPixmap`
> and the `QWebEngineView` construction. Scene sizes on the 124-triangle test
> mesh: 43.1 kB for a whole-domain field at order 2, 30.5 kB for a fluid-restricted one, 63 kB for
> the velocity — 347 B/element, consistent with §Design 1's 321 B/element at order 2. One render,
> including the `restore`, is 0.46 s on that mesh.

### Out of scope

| Deferred | Owner |
|---|---|
| Opening an arbitrary stored run in the viewer, rather than the one just run | Phase 4's result browser (§8.1). D8 makes it a file-chooser away |
| A scene updated live during the solve | Nothing asks for it; the state is only meaningful converged, and §Design 1's payload forbids a per-iteration scene |
| Figure export from either panel | Phase 4 |
| Mirroring the half-plane, deformation warps, streamlines | D15 |
| Reading the IF-07 XDMF export back into the shell | Not needed once D8 stands; ParaView is the reader that export is for |
| Any Linux desktop Qt assertion | CON-13's recorded exclusion: the push gate installs no system packages |

### Open questions

**OQ-1 — may the renderer be redistributed?** The `webgui` JavaScript is **LGPL-2.1-or-later**
(1,206,946 B unpacked for the npm package). Shipping it as package data is what makes a
double-clicked bundle draw a field with no network, which is what QR-10 will eventually ask for.
It costs: a line in CON-09's LGPL list, a line in `packaging/LICENSES-BUNDLE.md`, ~1 MB of
third-party minified JavaScript committed to a BSD-3 repository, and a refresh procedure that
records the version and its hash. **Recommendation: yes.** If the ruling is no or does not arrive,
WP15 ships D13's CDN default with D12's probe and records the limitation; the CON-09 amendment is
then not made. *This does not block implementation* — the renderer source is one constant.

> **Outcome — still open, and it outlived the package.** No ruling arrived, and the fallback is what
> shipped: `RENDERER_SOURCE` is the CDN address `netgen.webgui`'s own template pins, read through
> `renderer_source()`, with D12's probe naming it in every diagnostic. Note that a "yes" would not
> have been implementable from this session either — `cdn.jsdelivr.net` returns 403 through the
> development container's proxy, so the file has to be fetched elsewhere and checked against the
> integrity hash npm publishes. **What the deferral costs**: a double-clicked bundle on a machine
> with no route to the CDN shows the viewer's diagnostic instead of a field. Nothing else in WP15
> depends on it, and closing it is work item 15 plus one constant.

**OQ-2 — is a solve served from the store worth a panel of its own?** D4 requires the cache-hit
state to be named. Whether the panel should also offer to re-run with the store bypassed is a
workflow question, not a correctness one. Default: no, state it and stop.

> **Outcome — the default stands.** `ConvergenceModel.state` carries `served` as a state of its own
> and `summary` says the solve climbed no ladder and took no Newton step. No re-run control is
> offered. `tests/tier1/test_solve_hook.py` establishes the premise the state rests on: a solve
> answered from the store emits no rung and no step at all.

## Spec and plan amendments

Made in this commit:

- **§7.2 gains VER-44**, "Live convergence monitoring and field visualisation": the rung and the
  Newton step reach the shell through a structural hook carrying the residual and the undamped
  relative update as numbers, never recovered from a progress caption; the hook changes no artefact
  hash, asserted by running the same case watched and unwatched; a rung whose model takes no Newton
  callback yields a rung record and no steps, and the plot shows it as such rather than
  interpolating across it; a solve served from the store is named as such rather than drawn as an
  empty plot; the plot draws no convergence threshold, the criterion of NUM-16 being per rung and
  disjunctive; the field viewer renders a solution restored by the stage-10 gate rather than an
  export, its field names and units come from the IF-07 attribute vocabulary rather than from
  `gui/`, the scene reaches the view through a file rather than a data URL, and a document that
  loaded without its renderer is reported as a diagnostic naming the renderer source rather than
  shown as a blank panel (IF-09, QR-11, FR-27, NUM-16, NUM-18, QR-12).
- **Appendix A**: IF-09 → VER-43, VER-44; QR-11 → VER-43, VER-44.

Conditional on OQ-1, and made in the implementation commit if the ruling is yes: **CON-09** gains
the `webgui` JavaScript to its list of acceptable LGPL dependencies, with the note that it is
redistributed as a separate, replaceable file.

VER-43 is not touched. `docs/plans/current.md` is updated in this commit.

## Design

### 1. The scene payload, measured

`ngsolve.webgui` produces its scene as a plain dict of numbers and base64 strings, and that dict is
what has to reach the view. Measured here, 21 September 2026, NGSolve 6.2.26xx, P2 `GridFunction`
on a unit-square mesh, `Draw(gf, mesh, order=k, show=False).GetData()` then `json.dumps` **[tested]**:

| elements | order | `GetData` | JSON | per element |
|---|---|---|---|---|
| 224 | 1 | 3.0 ms | 0.045 MB | 202 B |
| 224 | 2 | 2.3 ms | 0.075 MB | 334 B |
| 2,550 | 1 | 15.7 ms | 0.496 MB | 194 B |
| 2,550 | 2 | 25.4 ms | 0.825 MB | 324 B |
| 16,036 | 1 | 157.9 ms | 3.094 MB | 193 B |
| 16,036 | 2 | 142.6 ms | 5.153 MB | 321 B |

Linear in elements to within 5 %. The reference-geometry mesh is 120,917 triangles (§8.1's
end-of-phase report), so a scene of it is **23.3 MB at order 1 and 38.8 MB at order 2**, built in
roughly 1.2 s.

Three consequences, and they are D9, D10 and the "no live scene" deferral together. A 23–39 MB
payload does not belong on a `multiprocessing.Queue` beside events polled every 100 ms. It does not
belong in `QWebEngineView.setHtml`, which percent-encodes its argument into a data URL — Qt
documents a ceiling on that and the exact figure is **unverified here**, doc.qt.io being unreachable
from this container, but the measurement above decides the question without it. And it is not
something to rebuild per Newton iteration. A file written once by the process that already holds the
`GridFunction`, loaded by `QUrl.fromLocalFile`, costs one write and one read of a number the machine
has to move either way.

The same measurement establishes the enabling fact: `GetData()` runs **headlessly and without
`anywidget`**. `netgen.webgui` defines `WebGuiWidget` inside a `try: import anywidget` and falls
back to a stub with the same constructor (`netgen/webgui.py:423–435`), so `WebGLScene.__init__`
succeeds with no Jupyter stack present. Nothing about the render child needs a display.

### 2. The renderer, and the document we have to write ourselves

Two facts about `netgen.webgui`, both read from the installed source, 21 September 2026 **[verified]**.

**The host document fetches its renderer from a CDN.** `_html_template` (`netgen/webgui.py:792–824`)
carries `<script src="https://cdn.jsdelivr.net/npm/webgui@0.2.39/dist/webgui.js">`. WP14 already
recorded the consequence: the page reaches `loadFinished(True)` and the console says
`webgui is not defined` (`.knowledge/07` §5). That is why D12 exists whichever way OQ-1 goes — a
blank panel that reports success is exactly the failure QR-12 is written against.

**`GenerateHTML`'s `template` argument is dead.**

```text
def GenerateHTML(data, filename=None, template=None):
    if template is None:
        template = _html_template
    ...
    html = _html_template.replace('{render}', jscode)
```

`template` is assigned and never read; the substitution is into the module global. So a caller
cannot redirect the renderer by passing a template, and D14 follows: we build the document. It is
small — a `<script>` with the renderer source, `var render_data = <json>`, and the four lines of
`scene.init(...)` the template already uses. One rendering path, ours, with the renderer source as
its single variable.

**The licence.** `registry.npmjs.org/webgui/0.2.39` gives `"license": "LGPL-2.1-or-later"` and
`unpackedSize: 1206946` **[verified]**. That is the whole of OQ-1: redistributing it is permitted
and is consistent with CON-09's existing treatment of LGPL dependencies — a standalone `.js` file is
about as replaceable as a dependency gets — but it is a new redistributed work in a BSD-3 repository
and the author should say so rather than find it. Note that `cdn.jsdelivr.net` is **blocked from
this development container** (the proxy returns 403), so the file must be fetched by whoever
implements OQ-1, against the integrity hash npm publishes.

### 3. Threading one hook to one stage without widening eleven others

`Stage.run(inputs, *, progress=None, cancel=None)` is the protocol all twelve stages satisfy.
`progress` and `cancel` are there because they are universal. A Newton-step hook is not: it is
meaningful to exactly one stage, and adding it to the protocol would put a parameter into eleven
signatures that can only ever be ignored. `on_stage` avoided this by belonging to the *walker*, not
to a stage; the Newton step cannot, because `SolveStage` is what emits it.

So the hook is delivered by capability:

```python
@runtime_checkable
class SolveReporting(Protocol):
    def with_solve_hook(self, hook: SolveHook) -> Stage: ...
```

and `_resolve_stage` rebinds only a stage that satisfies it. `with_solve_hook` returns a copy; the
hook is a field the stage carries, not a parameter every stage declares.

> **Outcome — `SolveStage` is a plain class with an `__init__`, not a frozen dataclass.** The
> conclusion is unchanged and the copy is explicit: `with_solve_hook` calls the constructor with
> this stage's workspace, warm start and cold reason plus the hook. `solve_hook` is a keyword-only
> constructor argument like the other three, and reaches neither `solve_provenance` nor `key`.

The hash argument is the part worth stating. `run_document` already computes the key from the
stage *before* `_resolve_stage` runs:

```python
artefact = _resolve_stage(walk, stage, name, inputs, _probe(stage, inputs), ...)
```

Rebinding after that point cannot move the key, and the hook must not be reachable from
`_probe` — a callback is not an input, and a run watched from the GUI must land on the same store
entry as the same run from the command line. That is not an argument, it is a test: the same case
run with and without `on_solve`, asserting one hash and one store hit.

`SolveHook` itself stays in `core/stages.py` and takes plain scalars for the same reason `StageHook`
does: `core/stages.py` is on the CLI's import path, and importing `solve.newton` to name a dataclass
would cost the CLI its 70 ms budget for a type it never constructs.

### 4. What the plot is allowed to claim

The plot shows two series per band: `log₁₀` of the residual after the step, and `log₁₀` of the
relative update on the undamped direction. The second is D5's reason for existing. NUM-16's NOTE is
explicit that convergence is declared on **either**

- `current ≤ target`, the residual relative to the residual on entry, or
- `relative_update ≤ rtol` on the *undamped* direction, and never on a forced step,

and `damped_newton` implements exactly that (`newton.py:377`). A plot of the residual alone would
show a rung converging while its curve was still flat — the warm-start case the NOTE was written
about, where the entry residual is already at its floor and six further orders are not available.
The update series is the one that moves. It costs nothing: `relative_update` is computed at
`newton.py:308`, in scope where the `NewtonStep` is built ten lines later.

For the same reason there is **no threshold line** (D6). A single horizontal rule would have to be
drawn at one of two criteria, on an axis whose zero is per-rung, and a reader would take it for the
thing the solver tested. What the panel can say honestly is per band: which test closed the rung,
how many trials the last step took, the minimum damping used, and whether any step was forced under
NUM-16. All of it is already on `NewtonStep` or derivable from the band.

The ladder is the x-axis, not a running iteration count (D3). NUM-18's rungs 1 and 2 are
electrostatic, their models are not `CoupledModel`, and `_instrumented` injects `callback` only when
they are (`solve/stage.py:454`). A plot with a continuous x would show those rungs as a gap and
could offer no reason for it; a plot banded by rung shows them as what they are — rungs that ran,
converged, and keep no Newton record because they are not Newton solves. The band is drawn and
labelled; the series inside it is empty and says so.

The cache hit (D4) is the same discipline once more. `get_or_compute` may return without solving,
in which case no rung and no step is ever emitted. An empty plot would read as a solve that
converged instantly. The model carries a distinct state for it and the panel names it.
