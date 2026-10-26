"""05-results: the Analysis suite: the explorer as tiles (RE3 B), a comparison with a switch between its two modes (RE4)."""

from mk import CTX, cbar, fieldmap, spot, window

PAGE = "05-results.html"
TILE = "border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:6px;display:grid;grid-template-rows:auto minmax(0,1fr);min-height:0;gap:4px"
OPT = '<button class="btn small" type="button" style="margin-left:auto" aria-label="{} tile options">⋯</button>'
IV = ('<div style="display:grid;grid-template-columns:auto minmax(0,1fr);grid-template-rows:minmax(0,1fr) auto;min-height:0"><span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Current, nA</span>'
      '<svg viewBox="0 0 200 120" width="100%" height="100%" preserveAspectRatio="none" role="img" aria-label="Current against bias"><line x1="0" y1="60" x2="200" y2="60" stroke="currentColor" stroke-opacity=".5"/><line x1="100" y1="0" x2="100" y2="120" stroke="currentColor" stroke-opacity=".5"/>'
      '<polyline points="5,105 50,85 80,68 100,60 120,50 150,32 195,12" fill="none" style="stroke:var(--accent)" stroke-width="2"/><circle cx="150" cy="32" r="4" style="fill:var(--accent)"/></svg>'
      '<span></span><span class="cl" style="text-align:center">Bias, V</span></div>')
AXIAL = ('<div style="display:grid;grid-template-columns:auto minmax(0,1fr);grid-template-rows:minmax(0,1fr) auto;min-height:0"><span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Potential, mV</span>'
         '<svg viewBox="0 0 200 120" width="100%" height="100%" preserveAspectRatio="none" role="img" aria-label="Potential along the axis"><line x1="0" y1="110" x2="200" y2="110" stroke="currentColor" stroke-opacity=".5"/>'
         '<polyline points="0,20 50,22 80,40 110,85 140,96 200,98" fill="none" style="stroke:var(--accent)" stroke-width="2"/></svg>'
         '<span></span><span class="cl" style="text-align:center">z, nm</span></div>')
POT = cbar("Potential, mV")


def explorer():
    qoi = spot("conductance", '<table><tbody><tr><td>Conductance</td><td class="num">x.xx nS</td></tr><tr><td>Transport number</td><td class="num">x.xx</td></tr><tr><td>EOF rate</td><td class="num">x.xx m³/s</td></tr></tbody></table>')
    body = f"""<div class="viewwrap" style="grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);grid-template-rows:auto minmax(0,1.3fr) minmax(0,1fr)">
  <div style="grid-column:1/-1" class="toolbar"><h2 style="margin:0;font-size:var(--text-lg)">I–V, NaCl</h2><span class="muted">2WCD, pH 7.5 on the reference mesh</span><span style="margin-left:auto"></span>
    <label for="ae-b" class="muted">Bias</label><select id="ae-b"><option>x.xx V, x of n</option></select><button class="btn small" type="button">Add a tile…</button><span class="later" style="padding:2px 6px"><b>Figure export</b></span></div>
  <div style="{TILE};grid-row:span 2;grid-template-rows:auto minmax(0,1fr) auto"><div class="row"><b>Potential</b><select aria-label="Quantity"><option>Potential</option><option>Concentration, Na⁺</option><option>Velocity</option></select><select aria-label="Colour map"><option>viridis</option><option>cividis</option></select>{OPT.format("Potential")}</div>
    {fieldmap(over='<line x1="20" y1="10" x2="20" y2="290" style="stroke:var(--accent)" stroke-width="3"/><circle cx="33" cy="190" r="4" style="fill:var(--panel);stroke:var(--accent)" stroke-width="2"/>', cards=f'<div class="corner">{POT}</div>', label="Potential in (r, z), the axial cut and a probe marked")}
    <div class="row"><span class="chip">Linked: field and its probes and cuts</span><button class="btn small" type="button">Unlink</button></div></div>
  <div style="{TILE}"><div class="row"><b>Current against bias</b>{OPT.format("Current")}</div>{IV}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;min-height:0">
    <div style="{TILE}"><div class="row"><b>Quantities</b>{OPT.format("Quantities")}</div>{qoi}</div>
    <div style="{TILE}"><div class="row"><b>Axial cut, r = 0</b>{OPT.format("Axial cut")}</div>{AXIAL}</div>
  </div>
</div>"""
    return window(PAGE, "analysis", "Results explorer", body, "minmax(0,1fr)", item="I–V, NaCl · run x of n")


SWITCH = ('<div class="tabs" role="tablist" aria-label="Show"><a role="tab" href="#a-compare-side" aria-selected="{s}">Side by side</a>'
          '<a role="tab" href="#a-compare-diff" aria-selected="{d}">Difference</a></div>')
DIFF = cbar("Variant − parent, mV", kind="div", ticks=("−x", "0", "+x"))
SHARED = cbar("Potential, mV, shared", ticks=("x.xx", "x.xx"))
HEAD = """<div class="stack" style="gap:6px"><div class="row"><h2 style="margin:0;font-size:var(--text-lg)">Parent and ASP 64 neutral</h2><span class="muted">one colour scale</span><span style="margin-left:auto"></span>{}</div>
<div class="toolbar"><label class="muted" for="{p}-1">Run</label><select id="{p}-1"><option>I–V, NaCl · 2WCD, pH 7.5</option></select><label class="muted" for="{p}-2">against</label><select id="{p}-2"><option>I–V, NaCl · 2WCD, ASP 64 neutral</option></select>
<label class="muted" for="{p}-b">Bias</label><select id="{p}-b"><option>x.xx V, x of n</option></select><label class="muted" for="{p}-q">Quantity</label><select id="{p}-q"><option>Potential</option></select><button class="btn small" type="button">New comparison…</button></div></div>"""


def compare_side():
    body = f"""<div class="viewwrap" style="grid-template-rows:auto minmax(0,1fr) auto">
  {HEAD.format(SWITCH.format(s="true", d="false"), p="cs")}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;min-height:0">
    <div style="{TILE}"><span>Parent · <span class="num">x.xx nS</span></span>{fieldmap()}</div>
    <div style="{TILE}"><span>ASP 64 neutral · <span class="num">x.xx nS</span> <span class="chg">1 change</span></span>{fieldmap(grad="g-seq2")}</div>
  </div>
  {SHARED}
</div>"""
    return window(PAGE, "analysis", "Comparison", body, "minmax(0,1fr)", item="Parent and ASP 64 neutral")


def compare_diff():
    body = f"""<div class="viewwrap" style="grid-template-rows:auto minmax(0,1fr)">
  {HEAD.format(SWITCH.format(s="false", d="true"), p="cd")}
  <div style="display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:8px;min-height:0">
    <div style="{TILE}"><span><b>ASP 64 neutral − parent</b> <span class="muted">conductance x.xx nS against x.xx nS</span></span>{fieldmap(grad="g-diff", cards=f'<div class="corner">{DIFF}</div>')}</div>
    <div class="stack" style="align-content:start"><span class="h">Parent</span><div style="height:170px;display:grid">{fieldmap()}</div>
      <span class="h">ASP 64 neutral</span><div style="height:170px;display:grid">{fieldmap(grad="g-seq2")}</div>{SHARED}
      <a class="btn small" href="#a-compare-side" style="justify-self:start">Show both large</a></div>
  </div>
</div>"""
    return window(PAGE, "analysis", "Comparison", body, "minmax(0,1fr)", item="Parent and ASP 64 neutral")


SCREENS = [("a-explorer", "Analysis · Results explorer", explorer), ("a-compare-side", "Analysis · Comparison, side by side", compare_side),
           ("a-compare-diff", "Analysis · Comparison, the difference", compare_diff)]


def screens():
    """Mockup B opens the comparison on the difference (RE4)."""
    if CTX["v"] == "b":
        return [SCREENS[0], SCREENS[2], SCREENS[1]]
    return SCREENS
