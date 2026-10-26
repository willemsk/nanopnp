"""05-results and 06-guided-route: studies, runs, the explorer, comparisons, the deployed charge (WB-04, WB-06, WB-11, WB-23), the route (WB-08)."""

from parts import c3d, cbar, crz, field, queue, suite_tabs, titlebar, tools

G = "display:grid;grid-template-columns:{cols};min-height:0"


def frame(tool, body, cols="180px 1fr", suite="Analysis", fresh=False):
    return f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs(suite))}
<div style="{G.format(cols=cols)}">
  <div class="pane"><h2>{suite} tools</h2>{tools(suite.lower(), tool, fresh=fresh)}</div>
  {body}
</div>
{queue()}
</div>"""


SWEEP = '<div class="field"><label for="{p}-sw">Sweep over</label><div class="v"><select id="{p}-sw"><option>Bias</option><option>Molecular models</option><option>Continuum models</option></select></div></div>'

re1a = frame("Study", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto;max-width:600px"><h2>Study · I–V, NaCl</h2>
  <div class="field"><label for="r1a-m">Molecular model</label><div class="v"><select id="r1a-m"><option>2WCD, pH 7.5</option><option>2WCD, ASP 64 neutral</option></select></div></div>
  <div class="field"><label for="r1a-c">Continuum model</label><div class="v"><select id="r1a-c"><option>ClyA pore, reference mesh</option></select></div></div>
  {SWEEP.format(p="r1a")}
  <hr><span class="h">Overrides of the continuum model's defaults</span>
  <div class="field"><span class="k ovr">Bias</span><span class="v num">−x.xx to +x.xx V, n steps <button class="btn small" type="button">Edit</button></span></div>
  <div class="field"><span class="k ovr">NaCl</span><span class="v num">x.xx M <button class="btn small" type="button">Edit</button></span></div>
  <button class="btn small" type="button" style="justify-self:start">Add an override…</button>
  <hr><div class="row"><button class="btn primary" type="button">Run study</button><span class="muted">queues the charge on the mesh, then the solves</span></div>
</div>""")

NODE = "position:absolute;background:var(--panel);border:1px solid var(--control-edge);border-radius:var(--radius);padding:6px 8px;display:grid;gap:2px;font-size:var(--text-sm);text-align:left;font-family:inherit;color:var(--ink)"
re1b = frame("Study", f"""<div style="display:grid;grid-template-columns:1fr 270px;min-height:0">
<div class="bg focus-ring" style="position:relative;margin:4px;min-height:340px" role="group" aria-label="Study graph">
  <svg width="100%" height="100%" style="position:absolute;inset:0" aria-hidden="true"><g style="stroke:var(--control-edge)" stroke-width="1.5" fill="none">
    <path d="M170 65 C 185 65, 175 140, 190 140"/><path d="M170 225 C 185 225, 175 150, 190 150"/><path d="M310 145 L 330 145"/><path d="M385 175 L 385 220"/></g></svg>
  <button type="button" style="{NODE};left:20px;top:40px;width:150px"><b>Molecular model</b><span>2WCD, pH 7.5</span></button>
  <button type="button" style="{NODE};left:20px;top:200px;width:150px"><b>Continuum model</b><span>ClyA pore, reference mesh</span></button>
  <button type="button" style="{NODE};left:190px;top:120px;width:120px"><b>Charge on the mesh</b><span class="muted">stage 7</span></button>
  <button type="button" aria-pressed="true" style="{NODE};left:330px;top:120px;width:110px;box-shadow:0 0 0 2px var(--accent)"><b>Solve</b><span class="ovr">2 overrides</span></button>
  <button type="button" style="{NODE};left:330px;top:220px;width:110px"><b>Results</b></button>
</div>
<div class="pane stack"><h2>Solve</h2>
  {SWEEP.format(p="r1b")}
  <div class="field"><span class="k ovr">Bias</span><span class="v num">−x.xx to +x.xx V</span></div>
  <div class="field"><span class="k ovr">NaCl</span><span class="v num">x.xx M</span></div>
  <button class="btn primary" type="button" style="justify-self:start">Run study</button></div>
</div>""")

SPARK = '<svg viewBox="0 0 120 28" width="120" height="28" role="img" aria-label="Residual falling over the iterations"><polyline points="0,4 15,8 30,7 45,13 60,15 75,19 90,22 105,24 120,26" fill="none" style="stroke:var(--accent)" stroke-width="2"/></svg>'

re2a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="180px 1fr")}"><div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>{crz(sym="mesh-rz")}</div>
<div class="queue focus-ring" style="margin:4px">
  <div class="qrow" style="grid-template-columns:1.4rem 1fr auto auto"><span class="warn" aria-hidden="true"></span><b>Study · I–V, NaCl</b><span class="warn">running</span><button class="btn small" type="button" aria-expanded="true">Fold</button></div>
  <div style="display:grid;grid-template-columns:repeat(4,auto) 1fr;gap:4px 18px;padding:6px 8px 8px 30px;align-items:center">
    <span class="muted">Bias</span><span class="muted">Ladder</span><span class="muted">Damping</span><span class="muted">Residual</span><span></span>
    <span class="num">x.xx V, x of n</span><span class="num">rung 7 of N</span><span class="num">x.xx</span>{SPARK}<span class="row" style="justify-content:flex-end"><button class="btn small" type="button">Open log</button><button class="btn small" type="button">Cancel</button></span>
  </div>
</div>
</div>"""

re2b = frame("Study", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Run · I–V, NaCl · bias x.xx V, x of n</h2>
  <div class="row"><span class="warn">running: rung 7 of N</span><span class="muted">elapsed x min</span><span style="margin-left:auto"></span><button class="btn" type="button">Cancel</button></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <table><thead><tr><th>Rung</th><th>Newton</th><th>Damping</th><th></th></tr></thead><tbody>
      <tr><td class="num">x</td><td class="num">x</td><td class="num">x.xx</td><td class="ok">done</td></tr>
      <tr><td class="num">x</td><td class="num">x</td><td class="num">x.xx</td><td class="ok">done</td></tr>
      <tr aria-current="true"><td class="num">7</td><td class="num">x</td><td class="num">x.xx</td><td class="warn">running</td></tr>
      <tr><td class="num">x</td><td></td><td></td><td class="muted">to do</td></tr></tbody></table>
    <div class="stack"><span class="h">Residual</span><svg viewBox="0 0 120 28" width="100%" height="90" preserveAspectRatio="none" role="img" aria-label="Residual falling"><polyline points="0,4 15,8 30,7 45,13 60,15 75,19 90,22 105,24 120,26" fill="none" style="stroke:var(--accent)" stroke-width="1.5"/></svg></div>
  </div>
  <span class="h">Log</span>
  <pre class="num" style="margin:0;padding:6px;background:var(--bg);border:1px solid var(--line);border-radius:var(--radius);font-size:var(--text-xs);white-space:pre-wrap">rung 7: Newton x, residual x.xx e−x, damping x.xx
rung 7: Newton x, residual x.xx e−x, damping x.xx</pre>
</div>""")

BIAS = '<div class="row"><label for="{p}-b" class="muted">Bias</label><select id="{p}-b"><option>x.xx V, x of n</option></select></div>'
QOI = """<div class="row" style="gap:6px">{}</div>""".format("".join(
    f'<div style="border:1px solid var(--line);border-radius:var(--radius);padding:4px 10px;background:var(--panel)"><span class="h">{k}</span><div class="num" style="font-size:var(--text-xl)">{v}</div></div>'
    for k, v in [("Conductance", "x.xx nS"), ("Transport number", "x.xx"), ("EOF rate", "x.xx m³/s")]))
POT = cbar("Potential, mV")

re3a = frame("Results explorer", f"""<div class="focus-ring" style="display:grid;grid-template-columns:1fr 240px;grid-template-rows:auto 1fr;min-height:0;gap:6px;padding:6px;margin:4px">
  <div style="grid-column:1/-1" class="row">{QOI}<span style="margin-left:auto"></span>{BIAS.format(p="r3a")}</div>
  {field(corner=f'{POT}', style="position:relative")}
  <div class="pane stack" style="border:1px solid var(--line);border-radius:var(--radius)"><h2>Plot</h2>
    <div class="field" style="grid-template-columns:5rem 1fr"><label for="r3a-q">Quantity</label><select id="r3a-q"><option>Potential</option></select></div>
    <div class="field" style="grid-template-columns:5rem 1fr"><label for="r3a-c">Map</label><select id="r3a-c"><option>viridis</option><option>cividis</option></select></div>
    <span class="h">Probes and cuts</span><ul class="tools"><li><button type="button">Axial cut, r = 0</button></li><li><button type="button">Probe at the constriction</button></li></ul>
    <button class="btn small" type="button" style="justify-self:start">Add a cut…</button></div>
</div>""")

TILE = "border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:6px;display:grid;grid-template-rows:auto 1fr;min-height:0"
IV = ('<div style="display:grid;grid-template-columns:auto 1fr;grid-template-rows:1fr auto;min-height:0"><span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Current, nA</span>'
      '<svg viewBox="0 0 200 120" width="100%" height="100%" preserveAspectRatio="none" role="img" aria-label="Current against bias"><line x1="0" y1="60" x2="200" y2="60" stroke="currentColor" stroke-opacity=".5"/><line x1="100" y1="0" x2="100" y2="120" stroke="currentColor" stroke-opacity=".5"/><polyline points="5,105 50,85 80,68 100,60 120,50 150,32 195,12" fill="none" style="stroke:var(--accent)" stroke-width="2"/></svg>'
      '<span></span><span class="cl" style="text-align:center">Bias, V</span></div>')
OPT = '<button class="btn small" type="button" style="margin-left:auto" aria-label="{} tile options">⋯</button>'
re3b = frame("Results explorer", f"""<div class="focus-ring" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto 1fr 1fr;gap:6px;padding:6px;min-height:0;margin:4px">
  <div style="grid-column:1/-1" class="row"><b>I–V, NaCl</b><span style="margin-left:auto"></span>{BIAS.format(p="r3b")}</div>
  <div style="{TILE}"><div class="row"><b>Potential</b>{OPT.format("Potential")}</div>{field(style="position:relative", corner=f'{POT}')}</div>
  <div style="{TILE}"><div class="row"><b>Current against bias</b>{OPT.format("Current")}</div>{IV}</div>
  <div style="{TILE}"><div class="row"><b>Quantities</b>{OPT.format("Quantities")}</div><table><tbody><tr><td>Conductance</td><td class="num">x.xx nS</td></tr><tr><td>Transport number</td><td class="num">x.xx</td></tr><tr><td>EOF rate</td><td class="num">x.xx m³/s</td></tr></tbody></table></div>
  <div style="{TILE}"><div class="row"><b>Probes and cuts</b>{OPT.format("Probes")}</div><ul class="tools"><li><button type="button">Axial cut, r = 0</button></li><li><button type="button">Probe at the constriction</button></li></ul></div>
</div>""")

DIFF = cbar("Variant − parent, mV", kind="div", ticks=("−x", "0", "+x"))
SHARED = cbar("Potential, mV, shared", ticks=("x.xx", "x.xx"))
re4a = frame("Comparison", f"""<div class="focus-ring" style="margin:4px;padding:6px;display:grid;grid-template-rows:auto 1fr auto;gap:6px;min-height:0">
  <div class="row"><b>Parent and ASP 64 neutral</b><span class="muted">one colour scale</span><span style="margin-left:auto"></span>
    <div class="tabs" role="tablist" aria-label="Show"><button type="button" role="tab" aria-selected="true">Side by side</button><button type="button" role="tab" aria-selected="false">Difference</button></div></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;min-height:0">
    <div style="display:grid;grid-template-rows:auto 1fr;min-height:0"><span>Parent · <span class="num">x.xx nS</span></span>{field(style="position:relative")}</div>
    <div style="display:grid;grid-template-rows:auto 1fr;min-height:0"><span>ASP 64 neutral · <span class="num">x.xx nS</span> <span class="chg">1 change</span></span>{field(grad="g-seq2", style="position:relative")}</div>
  </div>
  {SHARED}
</div>""")

re4b = frame("Comparison", f"""<div class="focus-ring" style="margin:4px;padding:6px;display:grid;grid-template-columns:1fr 210px;gap:8px;min-height:0">
  <div style="display:grid;grid-template-rows:auto 1fr;min-height:0"><div class="row"><b>ASP 64 neutral − parent</b><span class="muted">conductance x.xx nS against x.xx nS</span></div>{field(grad="g-diff", style="position:relative", corner=f'{DIFF}')}</div>
  <div class="stack"><span class="h">Parent</span><div style="height:130px;display:grid">{field(style="position:relative")}</div><span class="h">ASP 64 neutral</span><div style="height:130px;display:grid">{field(grad="g-seq2", style="position:relative")}</div>{SHARED}<span class="muted">Select either to show it large.</span></div>
</div>""")

RHO = cbar("Charge density, e/nm³", kind="div", ticks=("−x", "0", "+x"))
LEGS = '<div class="stack" style="gap:2px"><span class="h">Conservation on the mesh</span><span class="ok">total, within 10⁻³ of Q<sub>net</sub></span><span class="ok">per z-slice, passed</span></div>'
re5a = frame("Study", f"""<div style="display:grid;grid-template-columns:1fr 260px;min-height:0">
  {field(grad="g-diff", style="position:relative", corner=f'{RHO}', extra=f'<span class="lbl over" style="left:30%;top:56%;background:var(--canvas-plot);color:var(--canvas-plot-ink)">◉ ASP 64</span>')}
  <div class="pane stack focus-ring" style="margin:4px"><h2>Charge on the mesh · I–V, NaCl</h2>{LEGS}
    <span class="muted">Select a spot to show its residues in Molecular, linked (WB-06).</span><button class="btn small" type="button" style="justify-self:start">Show in Molecular</button></div>
</div>""")

re5b = frame("Study", f"""<div class="focus-ring" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr auto;gap:6px;min-height:0;margin:4px;padding:4px">
  {c3d(over='<circle cx="118" cy="190" r="10" fill="none" style="stroke:var(--accent)" stroke-width="3"/>', style="position:relative")}
  {field(grad="g-diff", style="position:relative", corner=f'{RHO}', extra=f'<span class="lbl over" style="left:30%;top:56%;background:var(--canvas-plot);color:var(--canvas-plot-ink)">◉ ASP 64</span>')}
  <div style="grid-column:1/-1" class="row">{LEGS.replace('class="stack"', 'class="row"')}<span class="muted">Selecting in either view selects in the other.</span></div>
</div>""")

GR_STEPS = [("Load and prepare 2WCD", "done"), ("Molecular model, with the defaults", "done"), ("Continuum model, with the defaults", "done"),
            ("Set the salt", "now"), ("Set the bias", ""), ("Pair the models in a study and run", ""), ("Read the conductance", "")]
EXPLAIN = "The bulk NaCl concentration in both reservoirs, in M. There is no default."


def rail():
    out = []
    for i, (s, w) in enumerate(GR_STEPS):
        now = w == "now"
        cur = ' aria-current="step"' if now else ""
        st = '<span class="ok">done</span>' if w == "done" else ('<b style="color:var(--accent)">now</b>' if now else "")
        bg = "background:var(--sel);box-shadow:inset 3px 0 0 var(--accent);" if now else ""
        extra = f'<div class="muted" style="font-size:var(--text-sm);padding:0 6px 4px 22px">{EXPLAIN}</div>' if now else ""
        out.append(f'<li{cur} style="border-radius:var(--radius);{bg}"><div style="display:flex;gap:6px;align-items:center;min-height:28px;padding:0 6px"><span class="num muted">{i + 1}</span>{s}<span style="margin-left:auto">{st}</span></div>{extra}</li>')
    return '<ol style="list-style:none;margin:0;padding:0">' + "".join(out) + "</ol>"


PH_ROWS = """<div class="field"{inert}><label for="{p}-e">Electrolyte</label><div class="v"><select id="{p}-e"><option>NaCl</option></select></div></div>
  <div class="field" style="{ring}"><label for="{p}-c">Concentration</label><div class="v"><input id="{p}-c" class="num" type="text" placeholder="set"><span class="unit">M</span></div></div>
  <div class="field"{inert}><span class="k">pH</span><span class="v num">7.5 <span class="muted">default</span></span></div>"""

gr1a = frame("Physics defaults", f"""<div class="pane stack"><h2>Physics defaults · electrolyte</h2>{PH_ROWS.format(p="g1a", inert="", ring="outline:2px solid var(--accent);outline-offset:2px;border-radius:var(--radius)")}</div>
<aside class="pane stack focus-ring" style="margin:4px" aria-label="Route"><h2>Guided run · step 4 of 7</h2>{rail()}
  <div class="row"><button class="btn small" type="button">Back</button><button class="btn primary small" type="button">Next</button><button class="btn small" type="button">Leave the route</button></div></aside>""",
             cols="180px 1fr 300px", suite="Continuum", fresh=True)

gr1b = f"""<div class="win" style="grid-template-rows:auto 1fr auto;position:relative">
<div inert>{titlebar(suite_tabs("Continuum"))}</div>
<div style="{G.format(cols="180px 1fr")}">
  <div class="pane" inert><h2>Continuum tools</h2>{tools("continuum", "Physics defaults", fresh=True)}</div>
  <div class="pane stack"><h2 inert>Physics defaults · electrolyte</h2>{PH_ROWS.format(p="g1b", inert=" inert", ring="position:relative;z-index:2;background:var(--panel);outline:2px solid var(--accent);outline-offset:4px;border-radius:var(--radius)")}
  <div class="focus-ring" role="dialog" aria-modal="true" aria-label="Guided run, step 4 of 7" style="position:relative;z-index:3;width:320px;margin-left:8.5rem;background:var(--panel);border:1px solid var(--control-edge);border-radius:var(--radius);padding:10px;display:grid;gap:6px">
    <span class="h">Guided run · step 4 of 7</span><b>Set the salt</b><span>{EXPLAIN}</span>
    <div class="row"><button class="btn small" type="button">Back</button><button class="btn primary small" type="button">Next</button><button class="btn small" type="button">Leave the route</button></div></div>
  </div>
</div>
<div inert>{queue()}</div>
<div aria-hidden="true" style="position:absolute;inset:0;background:rgb(0 0 0 / .4);z-index:1;pointer-events:none"></div>
</div>"""

RESULTS = [
    ("RE1", "How a study pairs its models (WB-11, WB-16)", {
        "a": ("A form: two models, what to sweep, then the overrides", re1a),
        "b": ("A graph of models, charge and solve; a node's settings beside", re1b)}),
    ("RE2", "Where a run in progress is followed (WB-23)", {
        "a": ("Unfolded in the queue, wherever you are", re2a),
        "b": ("Its own page, with the ladder and the log", re2b)}),
    ("RE3", "How the results explorer is laid out", {
        "a": ("One large field, the quantities above, plot settings beside", re3a),
        "b": ("Tiles you arrange: fields, curves, tables, probes", re3b)}),
    ("RE4", "How a comparison is shown (WB-04)", {
        "a": ("Side by side on one scale, the difference a switch away", re4a),
        "b": ("The difference large, the two runs small beside it", re4b)}),
    ("RE5", "Where the charge on the mesh is seen (WB-06)", {
        "a": ("In the study, linked to Molecular's view in its own suite", re5a),
        "b": ("In the study, beside a 3D view of the molecule, both linked", re5b)}),
]
ROUTE = [
    ("GR1", "How the guided route shows the next step (WB-08)", {
        "a": ("A checklist beside the tools; the next field outlined", gr1a),
        "b": ("The screen dimmed around the next field, a card beside it", gr1b)}),
]
