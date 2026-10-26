"""06-study: the Study suite (WB-29): the case overview (E4), the study as a form and as a graph (RE1), a sweep over
components (E6), the charge on the mesh beside the molecule (RE5 B), a run followed (RE2), the changed list (FR6), the tree (FR3 B)."""

from mk import CTX, S, cbar, reset, route, spot, view3d, viewrz, window

PAGE = "06-study.html"
ITEM = "I–V, NaCl"

MODELS = """<div class="field"><label for="{p}-m">Molecular model</label><div class="v"><select id="{p}-m"><option>2WCD, pH 7.5</option><option>2WCD, ASP 64 neutral</option></select><span class="ok">built</span></div></div>
<div class="field"><label for="{p}-c">Continuum model</label><div class="v"><select id="{p}-c"><option>ClyA pore, reference mesh</option></select><span class="ok">built</span></div></div>"""
SWEEP = '<div class="field"><label for="{p}-sw">Sweep over</label><div class="v"><select id="{p}-sw"><option>Bias</option><option>Molecular models</option><option>Continuum models</option><option>Bias and molecular models</option></select></div></div>'


def switch(current):
    form = "#st-form"
    graph = "#st-graph"
    return (f'<div class="tabs" role="tablist" aria-label="Show the study as"><a role="tab" href="{form}" aria-selected="{str(current == "form").lower()}">Form</a>'
            f'<a role="tab" href="{graph}" aria-selected="{str(current == "graph").lower()}">Graph</a></div>')


NACL = f'<div class="field"><span class="k ovr">NaCl</span><span class="v num">x.xx M <button class="btn small" type="button">Edit</button>{reset("NaCl override")}</span></div>'


def overrides(p):
    bias = spot("bias", f'<div class="field"><span class="k ovr">Bias</span><span class="v num">−x.xx to +x.xx V, n steps <button class="btn small" type="button">Edit</button>{reset("bias override")}</span></div>')
    return f"""<h3>Overrides of the continuum model's defaults</h3>
  {bias}
  {"" if route() else NACL}
  <button class="btn small" type="button" style="justify-self:start">Add an override…</button>"""


RUN = '<div class="row"><button class="btn primary" type="button">Run study</button><span class="muted">queues the charge on the mesh, then the solves</span></div>'


def study_runs():
    """The study's runs beside its settings, each opening its result (S6: a run and its result)."""
    if route() in ("prepare", "ph", "mesh", "salt", "bias", "run"):
        return '<div class="settings" style="border-right:0"><h2>Runs of this study</h2><span class="muted">None yet: run the study to queue them.</span></div>'
    rows = [("1 of n", "ok", "done"), ("2 of n", "ok", "done"), ("3 of n", "warn", "running"), ("4 of n", "", "queued")]
    trs = "".join(f'<tr><td class="num">bias x.xx V, {n}</td><td><span class="{c or "muted"}">{w}</span></td><td>{"<a class=\"btn small\" href=\"05-results.html#a-explorer\">Open result</a>" if c == "ok" else ""}</td></tr>' for n, c, w in rows)
    return f'<div class="settings" style="border-right:0"><h2>Runs of this study</h2><table><tbody>{trs}</tbody></table></div>'


def form_body():
    return f"""<div class="settings"><div class="row"><h2>Study · I–V, NaCl</h2><span style="margin-left:auto"></span>{switch("form")}</div>
  {MODELS.format(p="sf")}
  {SWEEP.format(p="sf")}
  {overrides("sf")}
  <h3>Outputs</h3>
  <div class="row"><label class="row"><input type="checkbox" checked> Current</label><label class="row"><input type="checkbox" checked> Transport numbers</label><label class="row"><input type="checkbox"> EOF rate</label></div>
  {spot("run", RUN)}
</div>
{study_runs()}"""


def form():
    return window(PAGE, "study", "Study setup", form_body(), "minmax(0,1.4fr) minmax(0,1fr)", item=ITEM)


NODE = "background:var(--panel);border:1px solid var(--control-edge);border-radius:var(--radius);padding:6px 8px;display:grid;gap:2px;font-size:var(--text-sm);text-align:left;font-family:inherit;color:var(--ink);align-self:center"


def edge(d):
    """An edge stretching with its grid cell, its arrowhead a glyph at the cell's right edge."""
    return (f'<div style="position:relative;height:100%"><svg viewBox="0 0 100 100" preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true">'
            f'<path d="{d}" fill="none" style="stroke:var(--muted)" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>'
            '<span aria-hidden="true" style="position:absolute;right:-3px;top:50%;transform:translateY(-52%);color:var(--muted);font-size:11px;line-height:1">▶</span></div>')


def graph():
    body = f"""<div class="viewwrap" style="grid-template-rows:auto minmax(0,1fr)">
  <div class="row"><h2 style="margin:0;font-size:var(--text-lg)">Study · I–V, NaCl</h2><span style="margin-left:auto"></span>{switch("graph")}</div>
  <div class="bg" style="display:grid;grid-template-columns:minmax(0,1.2fr) 48px minmax(0,1fr) 40px minmax(0,1fr) 40px minmax(0,1fr);grid-template-rows:1fr 1fr;padding:24px 16px;border:1px solid var(--line);border-radius:var(--radius);min-height:360px" role="group" aria-label="Study graph: two models feed the charge on the mesh, then the solve, then the results">
  <button type="button" style="{NODE};grid-column:1;grid-row:1"><b>Molecular model</b><span>2WCD, pH 7.5</span><span class="ok">built</span></button>
  <button type="button" style="{NODE};grid-column:1;grid-row:2"><b>Continuum model</b><span>ClyA pore, reference mesh</span><span class="ok">built</span></button>
  <div style="grid-column:2;grid-row:1/3">{edge("M0 25 C 50 25, 50 50, 96 50 M0 75 C 50 75, 50 50, 96 50")}</div>
  <button type="button" style="{NODE};grid-column:3;grid-row:1/3"><b>Charge on the mesh</b><span class="muted">stage 7</span></button>
  <div style="grid-column:4;grid-row:1/3">{edge("M0 50 L 96 50")}</div>
  <button type="button" aria-pressed="true" style="{NODE};grid-column:5;grid-row:1/3;box-shadow:0 0 0 2px var(--accent)"><b>Solve</b><span class="ovr">2 overrides</span><span class="muted">sweep: bias</span></button>
  <div style="grid-column:6;grid-row:1/3">{edge("M0 50 L 96 50")}</div>
  <button type="button" style="{NODE};grid-column:7;grid-row:1/3"><b>Results</b><span class="muted">current, transport numbers</span></button>
  </div>
</div>
<div class="settings" style="border-right:0;border-left:1px solid var(--line)"><h2>Solve</h2>
  {SWEEP.format(p="sg")}
  {overrides("sg")}
  {RUN}
  <span class="muted">Select a node to set it here. The graph and the form are two views of one study.</span>
</div>"""
    return window(PAGE, "study", "Study setup", body, "minmax(0,1fr) 340px", item=ITEM)


YAML = """schema: nanopnp/case/v0.5
name: i-v-nacl
structure:
  source: {path: 2wcd-prepared.pdb}
  symmetry: {point_group: C12}
geometry:
  contour: {isolevel: x.xx}   # ◆ changed
  membrane: {thickness_nm: 2.8, centre_z_nm: x.xx}
  reservoir: {radius_nm: 250.0}
charge: {ph: 7.5, titration: propka}
electrolyte:
  concentration_M: x.xx    # ◇ override
  parameters: willems2020_nacl
boundary_conditions: {bias_V: x.xx, ground: cis}
physics: {model: epnp-ns}"""


def overview_left():
    card = "border:1px solid var(--line);border-radius:var(--radius);padding:8px;display:grid;gap:4px;align-content:start"
    return f"""<div class="settings"><h2>Overview · I–V, NaCl</h2>
  <span class="muted">What this study is made of, and what it resolves to.</span>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
    <div style="{card}"><span class="h">Molecular model</span><b>2WCD, pH 7.5</b><span class="ok">built</span><span class="muted">Prepare, ensemble, protonation</span><a class="btn small" href="01-molecular.html#m-prepare" style="justify-self:start">Open in Molecular</a></div>
    <div style="{card}"><span class="h">Continuum model</span><b>ClyA pore, reference mesh</b><span class="ok">built</span><span class="muted">Geometry, region, mesh, physics defaults</span><a class="btn small" href="02-geometry.html#g-geometry" style="justify-self:start">Open in Continuum</a></div>
  </div>
  <h3>The study</h3>
  <div class="field"><span class="k">Sweep</span><span class="v">bias, n steps</span></div>
  <div class="field"><span class="k ovr">Overrides</span><span class="v">bias, NaCl</span></div>
  <div class="field"><span class="k chg">Changed</span><span class="v">2 values from their defaults <a class="btn small" href="#st-changes">Show</a></span></div>
  <div class="field"><span class="k">Runs</span><span class="v"><span class="warn">x of n running</span></span></div>
</div>"""


def overview_right():
    return f"""<div class="settings" style="border-right:0"><h2>Resolved case file</h2>
  <span class="muted">One complete case file, written with each run's manifest; the command line runs it as it is.</span>
  <pre class="yaml" tabindex="0" aria-label="Resolved case file">{YAML}</pre>
</div>"""


def overview_body():
    return overview_left() + overview_right()


def overview():
    return window(PAGE, "study", "Overview", overview_body(), "minmax(0,1fr) minmax(0,1fr)", item=ITEM)


def sweep():
    cell = {"ok": '<span class="ok">done</span>', "warn": '<span class="warn">running</span>', "q": '<span class="muted">queued</span>'}
    rows = [("2WCD, pH 7.5", ["ok", "ok", "warn", "q"], ""),
            ("2WCD, ASP 64 neutral", ["ok", "ok", "q", "q"], '<a class="btn small" href="05-results.html#a-compare-side">Compare with the parent</a>')]
    head = "".join("<th>x.xx V</th>" for _ in range(4))
    body_rows = "".join(f"<tr><td>{m}</td>{''.join(f'<td>{cell[c]}</td>' for c in cs)}<td>{cmp}</td></tr>" for m, cs, cmp in rows)
    body = f"""<div class="settings"><h2>Sweep · over components</h2>
  {SWEEP.format(p="sw").replace("<option>Bias and molecular models</option>", "<option selected>Bias and molecular models</option>")}
  <h3>Molecular models</h3>
  <label class="row"><input type="checkbox" checked> 2WCD, pH 7.5</label>
  <label class="row"><input type="checkbox" checked> 2WCD, ASP 64 neutral <span class="muted">charge variant</span></label>
  <label class="row"><input type="checkbox"> 2WCD, pH 5.0</label>
  <h3>Bias</h3>
  <div class="field"><span class="k ovr">Bias</span><span class="v num">−x.xx to +x.xx V, n steps <a class="btn small" href="#st-form">Edit in the setup</a></span></div>
  <span class="muted">The continuum model is shared: each molecular model is assembled on the same mesh, without rebuilding it.</span>
  <div class="row"><button class="btn primary" type="button">Run the sweep</button><span class="muted">2 × n runs</span></div>
</div>
<div class="settings" style="border-right:0"><h2>Runs of the sweep</h2>
  <table class="matrix"><thead><tr><th>Molecular model</th>{head}<th></th></tr></thead><tbody>{body_rows}</tbody></table>
  <span class="muted">Each cell is a run in the queue; a done cell opens its result in Analysis. A variant's row compares it with its parent at each bias both have.</span>
</div>"""
    return window(PAGE, "study", "Sweep", body, "380px minmax(0,1fr)", item=ITEM)


PICK = '<circle cx="118" cy="190" r="10" fill="none" style="stroke:var(--accent)" stroke-width="3"/>'
RHO = cbar("Charge density, e/nm³", kind="div", ticks=("−x", "0", "+x"))
RHO_RAW = (f'<polygon points="{S.pts(S.PROT)}" fill="url(#g-diff)" stroke="currentColor"/>'
           f'<polygon points="{S.pts(S.MEM)}" fill="none" stroke="currentColor" stroke-opacity=".7"/>{S.RESERVOIR}{S.AXIS}')


def charge():
    body = f"""<div class="viewwrap" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-template-rows:auto minmax(0,1fr) auto">
  <div class="row" style="grid-column:1/-1"><h2 style="margin:0;font-size:var(--text-lg)">Charge on the mesh · 2WCD, pH 7.5 on the reference mesh</h2></div>
  {view3d(over=PICK, label="3D view of the molecule, ASP 64 selected")}
  {viewrz(raw=RHO_RAW, cards=f'<div class="corner">{RHO}</div><div class="over cl" style="left:8px;bottom:6px">Schematic. The charge is a volume charge inside the protein.</div>', inside='<span class="lbl over" style="left:30%;top:56%;background:var(--canvas-plot)">◉ ASP 64</span>', label="Deployed charge density in (r, z), ASP 64 selected")}
  <div class="verdict" style="grid-column:1/-1"><b>Conservation on the mesh</b><span class="ok">total within 10⁻³ of Q<sub>net</sub></span><span class="ok">per z-slice, passed</span><span class="muted">Selecting in either view selects in the other.</span></div>
</div>"""
    return window(PAGE, "study", "Charge on the mesh", body, "minmax(0,1fr)", item=ITEM)


def conv_plot(height):
    """The convergence plot: residual and relative update per Newton step, log scale, banded by rung (Q35)."""
    bands = "".join(f'<rect x="{x}" y="0" width="{w}" height="100" style="fill:var(--line)" opacity="{o}"/>' for x, w, o in ((0, 30, .5), (60, 30, .5)))
    return f"""<div style="display:grid;grid-template-columns:auto minmax(0,1fr);grid-template-rows:minmax(0,1fr) auto;min-height:0;height:{height}">
<span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Residual and update, log</span>
<svg viewBox="0 0 120 100" preserveAspectRatio="none" width="100%" height="100%" role="img" aria-label="Residual and relative update per Newton step on a log scale, banded by rung">{bands}
<polyline points="0,10 10,30 20,55 30,80 32,20 42,45 52,70 60,85 62,25 72,50 82,72" fill="none" style="stroke:var(--accent)" stroke-width="2" vector-effect="non-scaling-stroke"/>
<polyline points="0,20 10,40 20,62 30,88 32,30 42,52 52,76 60,90 62,35 72,58 82,80" fill="none" style="stroke:var(--warn)" stroke-width="1.5" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>
<line x1="0" y1="92" x2="120" y2="92" style="stroke:var(--err)" stroke-dasharray="2 2" vector-effect="non-scaling-stroke"/></svg>
<span></span><span class="cl row" style="justify-content:space-between"><span>Newton step; rungs shaded</span><span><span style="color:var(--accent)">━</span> residual <span style="color:var(--warn)">┅</span> relative update <span style="color:var(--err)">┄</span> tolerance</span></span></div>"""


RUNGS = """<table><thead><tr><th>Rung</th><th>Steps</th><th>Ended by</th><th>Last value</th><th>Tolerance</th><th>Smallest damping</th></tr></thead><tbody>
  <tr><td class="num">x</td><td class="num">x</td><td>residual</td><td class="num">x.x e−x</td><td class="num">x.x e−x</td><td class="num">x.xx</td></tr>
  <tr><td class="num">x</td><td class="num">x</td><td>relative update</td><td class="num">x.x e−x</td><td class="num">x.x e−x</td><td class="num">x.xx</td></tr>
  <tr aria-current="true"><td class="num">x</td><td class="num">x</td><td class="warn">running</td><td class="num">x.x e−x</td><td class="num">x.x e−x</td><td class="num">x.xx</td></tr></tbody></table>"""
FAILED = '<div class="qrow" style="grid-template-columns:1.4rem 1fr auto auto"><span class="err" aria-hidden="true"></span><span>Study · I–V, NaCl · bias x.xx V, 6 of n · stopped at rung x: damping below x.xx</span><span class="err">failed</span><button class="btn small" type="button">Open log</button></div>'


def detail():
    """A run unfolded in the queue (RE2 A), with its convergence (Q35, Q36)."""
    status = spot("follow", '<div class="row"><b>Study · I–V, NaCl · bias x.xx V, x of n</b><span class="warn">running: rung x of N</span><button class="btn small" type="button">Cancel</button><button class="btn small" type="button">Open log</button></div>')
    return f"""<div style="display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:12px;padding:8px">
<div class="stack" style="gap:6px">{status}{RUNGS}</div>{conv_plot("190px")}</div>
<div class="qrow" style="grid-template-columns:1.4rem 1fr auto auto"><span class="ok" aria-hidden="true"></span><span>Study · I–V, NaCl · bias x.xx V, 2 of n</span><span class="ok">done</span><a class="btn small" href="05-results.html#a-explorer">Open result</a></div>
{FAILED}"""


def runs():
    if CTX["v"] == "a":
        return window(PAGE, "study", "Study setup", form_body(), "minmax(0,1.4fr) minmax(0,1fr)", item=ITEM,
                      panel_state="open", run_detail=detail())
    status = spot("follow", '<div class="row"><span class="warn">running: rung x of N</span><span class="muted">elapsed x min</span><span style="margin-left:auto"></span><button class="btn" type="button">Cancel</button></div>')
    body = f"""<div class="settings" style="border-right:0"><h2>Run · I–V, NaCl · bias x.xx V, x of n</h2>
  {status}
  <div style="display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:12px">{RUNGS}{conv_plot("220px")}</div>
  <h3>Log</h3>
  <pre class="yaml" tabindex="0" aria-label="Log">rung x: Newton x, residual x.x e−x, damping x.xx
rung x: Newton x, residual x.x e−x, damping x.xx</pre>
  <h3>Other runs of this study</h3>
  <table><tbody><tr><td>bias x.xx V, 1 of n</td><td class="ok">done</td><td><a class="btn small" href="05-results.html#a-explorer">Open result</a></td></tr>
  <tr><td>bias x.xx V, 2 of n</td><td class="ok">done</td><td><a class="btn small" href="05-results.html#a-explorer">Open result</a></td></tr>
  <tr><td>bias x.xx V, 6 of n</td><td class="err">failed: damping below x.xx at rung x</td><td><button class="btn small" type="button">Open log</button></td></tr>
  <tr><td>bias x.xx V, 4 of n</td><td class="muted">queued</td><td></td></tr></tbody></table>
</div>"""
    return window(PAGE, "study", "Runs", body, "minmax(0,1fr)", item=ITEM)


GROUPS = [("Continuum model · ClyA pore, reference mesh", [("Contour isolevel", "chg", "x.xx", "0.25"), ("Pore boundary maximum size", "chg", "x.xx nm", "x.xx nm")]),
          ("Study · I–V, NaCl, overriding the continuum model", [("Bias", "ovr", "−x.xx to +x.xx V", "x.xx V"), ("NaCl", "ovr", "x.xx M", "none")])]


def change_table():
    out = []
    first = True
    for g, rows in GROUPS:
        out.append(f'<tr><th colspan="4" scope="colgroup">{g}</th></tr>')
        for w, c, v, d in rows:
            cur = ' aria-current="true"' if first else ""
            first = False
            out.append(f'<tr{cur}><td>{w}</td><td class="num"><span class="{c}">{v}</span></td><td class="num muted">{d}</td><td><button class="btn small" type="button" aria-label="Reset {w}">Reset</button></td></tr>')
    return f'<table><thead><tr><th>Value</th><th>Now</th><th>Default</th><th></th></tr></thead><tbody>{"".join(out)}</tbody></table>'


LEGEND = '<span class="muted"><span class="chg">changed</span> from a default; <span class="ovr">override</span> by the study. The molecular model, 2WCD, pH 7.5, has none.</span>'


def changes():
    if CTX["v"] == "a":
        pop = f"""<div class="card" role="dialog" aria-label="Values changed from their defaults" style="position:absolute;top:40px;right:12px;width:580px;z-index:5;box-shadow:0 6px 20px rgb(0 0 0 / .25)">
  <div class="row"><h2 class="h" style="margin:0">2 changed from their defaults, 2 overrides</h2><span style="margin-left:auto"></span><a class="btn small" href="#st-overview">Close</a></div>{change_table()}{LEGEND}
  <button class="btn small" type="button" style="justify-self:start">Go to the selected value</button></div>"""
        return window(PAGE, "study", "Overview", overview_body(), "minmax(0,1fr) minmax(0,1fr)", item=ITEM, overlay=pop, changed_open=True)
    body = f"""{overview_left()}
<aside class="settings" style="border-right:0;border-left:1px solid var(--line)" aria-label="Changes"><div class="row"><h2>Changes</h2><span style="margin-left:auto"></span><a class="btn small" href="#st-overview">Close</a></div>
  <h3>The open study, by model</h3>{change_table()}{LEGEND}
  <h3>Variants in the library, against their parents</h3>
  <table><tbody><tr><td>2WCD, ASP 64 neutral</td><td>ASP 64 state</td><td class="num">ASH, 0</td><td class="num muted">parent: ASP, −1</td></tr></tbody></table>
</aside>"""
    return window(PAGE, "study", "Overview", body, "minmax(0,1fr) 540px", item=ITEM, changed_open=True)


TREE = """<nav class="rail" aria-label="Project" style="padding:6px">
  <div class="row"><b>Project</b><span style="margin-left:auto"></span><a class="btn small" href="#st-overview">Fold to the rail</a></div>
  <ul class="tree">
    <li><span class="grp">Library</span><ul>
      <li><span class="muted">Molecular models</span><ul><li><a href="01-molecular.html#m-prepare">2WCD, pH 7.5 <span class="ok">built</span></a></li><li><a href="01-molecular.html#m-charge">2WCD, ASP 64 neutral <span class="muted">variant</span></a></li></ul></li>
      <li><span class="muted">Continuum models</span><ul><li><a href="02-geometry.html#g-geometry">ClyA pore, reference mesh <span class="ok">built</span></a></li></ul></li></ul></li>
    <li><span class="grp">Studies</span><ul><li><a href="#st-overview" aria-current="true">I–V, NaCl <span class="warn">running</span></a></li><li><a href="#st-sweep">Sweep over models</a></li></ul></li>
    <li><span class="grp">Comparisons</span><ul><li><a href="05-results.html#a-compare-side">Parent and ASP 64 neutral</a></li></ul></li>
  </ul></nav>"""


def tree():
    return window(PAGE, "study", "Overview", overview_body(), "minmax(0,1fr) minmax(0,1fr)", item=ITEM, rail_html=TREE, rail_w="300px")


SCREENS = [("st-overview", "Study · Overview of the case", overview), ("st-form", "Study · Study setup, as a form", form),
           ("st-graph", "Study · Study setup, as a graph", graph), ("st-sweep", "Study · A sweep over components", sweep),
           ("st-charge", "Study · Charge on the mesh", charge), ("st-runs", "Study · A run followed", runs),
           ("st-changes", "Study · The changed values", changes), ("st-tree", "Study · The project tree unfolded", tree)]


def screens():
    """Mockup B opens the study on its graph (RE1)."""
    if CTX["v"] == "b":
        s = list(SCREENS)
        s[1], s[2] = s[2], s[1]
        return s
    return SCREENS
