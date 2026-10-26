"""00-frame: the suite switcher, the queue, the project browser, the problems list."""

from parts import QROWS, badge, c3d, crz, project, queue, suite_tabs, titlebar, tools

G = "display:grid;grid-template-columns:{cols};min-height:0"

fr1a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Molecular", focus=True))}
<div style="{G.format(cols="210px 200px 1fr")}">
  <div class="pane bg">{project("m")}</div>
  <div class="pane"><h2>Molecular tools</h2>{tools("molecular", "Protonation")}</div>
  {c3d()}
</div>
{queue()}
</div>"""

fr1b = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar("")}
<div style="{G.format(cols="72px 210px 200px 1fr")}">
  <nav class="activity focus-ring" aria-label="Suites">
    <a href="#fr1-b" aria-current="page"><span class="ico" aria-hidden="true">⬡</span>Molecular</a>
    <a href="#fr1-b"><span class="ico" aria-hidden="true">△</span>Continuum</a>
    <a href="#fr1-b"><span class="ico" aria-hidden="true">∿</span>Analysis</a>
  </nav>
  <div class="pane bg">{project("m")}</div>
  <div class="pane"><h2>Molecular tools</h2>{tools("molecular", "Protonation")}</div>
  {c3d()}
</div>
{queue()}
</div>"""

PANEL_TABS = """<div class="row" style="border-bottom:1px solid var(--line);gap:0">
  <div class="tabs" role="tablist" aria-label="{label}">{tabs}</div>
  <span class="later" style="padding:2px 6px;margin-left:6px"><b>Console</b></span>{tail}</div>"""


def panel_tabs(selected, label="Bottom panel", tail=""):
    tabs = "".join(f'<button type="button" role="tab" aria-selected="{"true" if t.startswith(selected) else "false"}">{t}</button>'
                   for t in ("Queue 3", "Problems 2", "Log"))
    return PANEL_TABS.format(label=label, tabs=tabs, tail=tail)


fr2a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="210px 200px 1fr")}">
  <div class="pane bg">{project("c")}</div>
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  {crz(sym="mesh-rz")}
</div>
<div class="focus-ring" style="margin:4px">
  {panel_tabs("Queue", tail='<span style="margin-left:auto"></span><button class="btn small" type="button">Fold</button>')}
  {queue(expanded=True)}
</div>
</div>"""

fr2b = f"""<div class="win" style="grid-template-rows:auto 1fr">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 190px 1fr 300px")}">
  <div class="pane bg">{project("c")}</div>
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  {crz(sym="mesh-rz")}
  <aside class="pane focus-ring stack" aria-label="Run queue" style="margin:4px;align-content:start">
    {panel_tabs("Queue", label="Side panel")}
    <div class="stack" style="gap:4px"><b>Study · I–V, NaCl</b><span class="warn">running: bias x.xx V, rung 7 of N</span><div class="row"><button class="btn small" type="button">Open log</button><button class="btn small" type="button">Cancel</button></div></div>
    <hr>
    <div class="stack" style="gap:2px"><span>Molecular model · ASP 64 neutral</span><span class="muted">queued</span></div>
    <hr>
    <div class="stack" style="gap:2px"><span>Continuum model · reference mesh</span><span class="ok">built in x.x s</span></div>
  </aside>
</div>
</div>"""

fr3a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="250px 200px 1fr")}">
  <div class="pane bg focus-ring" style="margin:4px">{project("c")}</div>
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Region")}</div>
  {crz()}
</div>
{queue()}
</div>"""

RAIL = """<nav class="pane bg focus-ring stack" aria-label="Project" style="margin:4px;padding:6px 4px;gap:2px">
  <ul class="tools">
    <li><button type="button" aria-expanded="false">Library <span class="st muted">3</span></button></li>
    <li><button type="button" aria-current="true">· ClyA pore, reference mesh</button></li>
    <li><button type="button" aria-expanded="false">Studies <span class="st muted">1</span></button></li>
    <li><button type="button" aria-expanded="false">Comparisons <span class="st muted">1</span></button></li>
  </ul>
  <button class="btn small" type="button" style="justify-self:start">Unfold the tree <span class="muted num">Ctrl Shift E</span></button>
</nav>"""

fr3b = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 200px 1fr")}">
  {RAIL}
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Region")}</div>
  {crz()}
</div>
{queue()}
</div>"""

PROBLEMS = """<div class="qrow" style="grid-template-columns:1.4rem 1fr auto"><span class="err" aria-hidden="true"></span><span><b>Region · membrane thickness</b>: x.xx nm is outside x.xx to x.xx nm; enter a thickness in that range. <span class="num muted">geometry.membrane.thickness_nm</span></span><button class="btn small" type="button">Go to field</button></div>
<div class="qrow" style="grid-template-columns:1.4rem 1fr auto"><span class="err" aria-hidden="true"></span><span><b>Prepare · axis</b>: the estimated axis is x.xx° from the chains' symmetry axis, over the x.xx° gate; set the axis in the view.</span><button class="btn small" type="button">Go to tool</button></div>"""

REFUSED = """<div class="field"><label for="{p}-t">Membrane thickness</label><div class="v"><input id="{p}-t" class="num refused" type="text" value="x.xx" aria-invalid="true" aria-describedby="{p}-m"><span class="unit">nm</span></div></div>
    <div class="msg" id="{p}-m">✕ x.xx nm is outside x.xx to x.xx nm. Enter a thickness in that range.</div>
    <div class="field"><label for="{p}-r">Reservoir radius</label><div class="v"><input id="{p}-r" class="num" type="text" value="x.xx"><span class="unit">nm</span></div></div>"""

fr4a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 280px 1fr")}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Region")}</div>
  <div class="pane stack"><h2>Region</h2>{REFUSED.format(p="f4a")}</div>
  {crz()}
</div>
<div class="focus-ring" style="margin:4px">
  {panel_tabs("Problems")}
  <div class="queue">{PROBLEMS}</div>
</div>
</div>"""

fr4b = f"""<div class="win" style="grid-template-rows:auto 1fr auto;position:relative">
{titlebar(suite_tabs("Continuum", badges={"Continuum": 1, "Molecular": 1}).replace('aria-label="Suites">', 'aria-label="Suites">'))}
<div style="{G.format(cols="230px 280px 1fr")}">
  <div class="pane"><h2>Continuum tools</h2><ul class="tools" aria-label="Tools">
    <li><button type="button">Protein geometry<span class="st ok">built</span></button></li>
    <li><button type="button" aria-current="true">Region {badge(1)}<span class="st err">refused</span></button></li>
    <li><button type="button">Mesh<span class="st warn">stale</span></button></li>
    <li><button type="button">Physics defaults</button></li></ul></div>
  <div class="pane stack"><h2>Region</h2>{REFUSED.format(p="f4b")}</div>
  {crz()}
</div>
{queue()}
<div class="focus-ring" role="dialog" aria-label="Problems" style="position:absolute;top:40px;right:12px;width:400px;background:var(--panel);border:1px solid var(--control-edge);border-radius:var(--radius);padding:8px;box-shadow:0 6px 20px rgb(0 0 0 / .25)">
  <h2 class="h">2 problems, from the Continuum and Molecular counts</h2>
  <div>{PROBLEMS}</div>
</div>
</div>"""

CHOICES = [
    ("FR1", "Where the suites are switched", {
        "a": ("Tabs in the title bar, as COMSOL's and AutoCAD's ribbon tabs", fr1a),
        "b": ("An activity bar down the left edge, as in VS Code", fr1b)}),
    ("FR2", "Where the run queue sits", {
        "a": ("A bottom panel that folds to one line, beside Problems and Log", fr2a),
        "b": ("A right-hand column, always open, with Problems and Log as its tabs", fr2b)}),
    ("FR3", "How the project browser shows, always on screen (WB-03)", {
        "a": ("A full tree on the left", fr3a),
        "b": ("A narrow rail of the open item and the top-level groups, unfolding into the tree", fr3b)}),
    ("FR4", "Where the problems list lives (WB-12)", {
        "a": ("A tab of the panel that holds the queue (FR2 A or B)", fr4a),
        "b": ("A count on each suite and tool, opening a pop-over", fr4b)}),
]

GATES = [("Stage 1 · alignment", "ok", "axis drift x.xx°, chains matched"), ("Stage 4 · contour", "ok", "radius against probe-radius profile"),
         ("Stage 6 · mesh", "ok", "SICN and gamma above 0.3"), ("Stage 7 · charge on the mesh", "warn", "per z-slice check pending")]

fr5a = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 320px 1fr")}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  <div class="pane stack focus-ring" style="margin:4px"><h2>Mesh</h2>
    <div class="row"><span class="ok">Quality gate passed</span><button class="btn small" type="button" aria-expanded="true">Details</button></div>
    <table><thead><tr><th>Check</th><th>Value</th><th>Limit</th></tr></thead><tbody>
    <tr><td>Worst SICN</td><td class="num">x.xx</td><td class="num">above 0.3</td></tr>
    <tr><td>Worst gamma</td><td class="num">x.xx</td><td class="num">above 0.3</td></tr>
    <tr><td>Wall size</td><td class="num">x.xx nm</td><td class="num">at most x.xx nm</td></tr></tbody></table>
    <span class="muted">Each tool shows its own verdict, with its checks one click away.</span>
  </div>
  {crz(sym="mesh-rz")}
</div>
{queue()}
</div>"""

fr5b = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 1fr")}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  <div class="pane stack focus-ring" style="margin:4px"><h2>Checks · ClyA study</h2>
    <table><thead><tr><th>Stage</th><th>Verdict</th><th>What was checked</th><th></th></tr></thead><tbody>
    {"".join(f'<tr><td>{s}</td><td><span class="{c}">{"passed" if c == "ok" else "pending"}</span></td><td>{w}</td><td><button class="btn small" type="button">Open</button></td></tr>' for s, c, w in GATES)}
    </tbody></table>
    <span class="muted">One list of every gate in the project, by stage, opened from the title bar.</span>
  </div>
</div>
{queue()}
</div>"""

CHANGES = [("Molecular · ASP 64 state", "ASH, 0", "ASP, −1"), ("Continuum · contour isolevel", "x.xx", "x.xx"), ("Continuum · pore boundary maximum size", "x.xx nm", "x.xx nm")]


def change_rows():
    return "".join(f'<tr><td>{w}</td><td class="num"><span class="chg">{v}</span></td><td class="num muted">{d}</td><td><button class="btn small" type="button" aria-label="Reset {w}">Reset</button></td></tr>' for w, v, d in CHANGES)


fr6a = f"""<div class="win" style="grid-template-rows:auto 1fr auto;position:relative">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 1fr")}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  {crz(sym="mesh-rz")}
</div>
{queue()}
<div class="focus-ring" role="dialog" aria-label="Values changed from their defaults" style="position:absolute;top:40px;right:12px;width:520px;background:var(--panel);border:1px solid var(--control-edge);border-radius:var(--radius);padding:8px;box-shadow:0 6px 20px rgb(0 0 0 / .25);display:grid;gap:6px">
  <h2 class="h">x changed from their defaults</h2>
  <table><thead><tr><th>Where</th><th>Value</th><th>Default</th><th></th></tr></thead><tbody>{change_rows()}</tbody></table>
  <button class="btn small" type="button" style="justify-self:start">Go to the selected value</button>
</div>
</div>"""

fr6b = f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols="200px 1fr 420px")}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", "Mesh")}</div>
  {crz(sym="mesh-rz")}
  <aside class="pane stack focus-ring" style="margin:4px" aria-label="Changes"><h2>Changes · grouped by model</h2>
    <span class="h">2WCD, ASP 64 neutral, against its parent</span>
    <table><tbody>{change_rows()}</tbody></table>
    <span class="muted">A side panel that stays open while you work, listing every value changed from its default and each model's difference from its parent.</span>
  </aside>
</div>
{queue()}
</div>"""

CHOICES += [
    ("FR5", "How the gates and their verdicts are shown", {
        "a": ("A verdict on each tool, its checks one click away", fr5a),
        "b": ("One list of every gate in the project, by stage", fr5b)}),
    ("FR6", "What the changed count opens (WB-28)", {
        "a": ("A pop-over list with each default and a reset", fr6a),
        "b": ("A side panel, grouped by model, with the parent's difference", fr6b)}),
]
