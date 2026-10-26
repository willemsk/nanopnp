"""02-geometry, 03-mesh, 04-physics: the Continuum suite's tools (WB-15, WB-16)."""

import math

import shapes as S
from parts import cbar, crz, field, queue, reset, suite_tabs, titlebar, tools

G = "display:grid;grid-template-columns:{cols};min-height:0"


def frame(tool, body, cols="180px 340px 1fr"):
    return f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Continuum"))}
<div style="{G.format(cols=cols)}">
  <div class="pane"><h2>Continuum tools</h2>{tools("continuum", tool)}</div>
  {body}
</div>
{queue()}
</div>"""


def f(fid, label, value, unit="", mark=""):
    u = f'<span class="unit">{unit}</span>' if unit else ""
    return f'<div class="field"><label for="{fid}">{label}</label><div class="v"><input id="{fid}" class="num" type="text" value="{value}">{u}{mark}</div></div>'


def pct(x, y):
    return f"left:{x / 180 * 100:.1f}%;top:{y / 300 * 100:.1f}%"


CONTOUR = (f'<polygon points="{S.pts(S.PROT)}" fill="none" style="stroke:var(--accent)" stroke-width="2"/>'
           f'<polygon points="{S.PROBE}" fill="none" style="stroke:var(--warn)" stroke-width="1.5" stroke-dasharray="3 2"/>')


def thumb(kind):
    inner = {
        "density": '<rect x="20" y="10" width="140" height="280" fill="url(#g-seq2)" clip-path="url(#disc)"/>',
        "symmetry": '<rect x="20" y="10" width="140" height="280" fill="url(#g-seq)" clip-path="url(#disc)"/>' + S.AXIS,
        "contour": f'<polygon points="{S.pts(S.PROT)}" fill="none" style="stroke:var(--accent)" stroke-width="4"/>' + S.AXIS,
    }[kind]
    return f'<div class="cplot" style="width:48px;height:80px;flex:none" role="img" aria-label="{kind} preview"><svg viewBox="0 0 180 300" width="100%" height="100%" style="color:var(--canvas-plot-ink)">{inner}</svg></div>'


def step(kind, title, status, body):
    return f'<div class="row" style="align-items:flex-start;flex-wrap:nowrap">{thumb(kind)}<div class="stack" style="gap:2px;min-width:0"><b>{title} {status}</b>{body}</div></div>'


ISO = f("g1x", "Isolevel", "x.xx", "", f'<span class="chg">changed</span>')

ge1a = frame("Protein geometry", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Protein geometry · from 2WCD, pH 7.5</h2>
  <span class="muted">Stage 1, alignment, is done in Molecular, Prepare.</span>
  {step("density", "Stage 2 · density", '<span class="ok">built</span>', f("g1a-h", "Grid spacing", "x.xx", "Å"))}
  {step("symmetry", "Stage 3 · symmetry to (r, z)", '<span class="ok">built</span>', '<span class="muted">C12; azimuthal variance, peak x.xx</span>')}
  {step("contour", "Stage 4 · contour", '<span class="ok">gate passed</span>', ISO.replace("g1x", "g1a-i") + f("g1a-s", "Simplification", "x.xx", "nm"))}
  <div class="row"><button class="btn primary" type="button">Build geometry</button>{reset("isolevel")}</div>
</div>
{crz(sym="protein-rz", over=CONTOUR, style="position:relative")}""")

ge1b = frame("Protein geometry", f"""<div class="pane stack" style="overflow:auto"><h2>Protein geometry · from 2WCD, pH 7.5</h2>
  <span class="muted">Stage 1, alignment, is done in Molecular, Prepare.</span>
  <details open><summary><b>Density</b>, stage 2 <span class="ok">built</span></summary>{f("g1b-h", "Grid spacing", "x.xx", "Å")}</details>
  <details><summary><b>Symmetry to (r, z)</b>, stage 3 <span class="ok">built</span></summary></details>
  <details open><summary><b>Contour</b>, stage 4 <span class="ok">gate passed</span></summary>{ISO.replace("g1x", "g1b-i")}{f("g1b-s", "Simplification", "x.xx", "nm")}</details>
  <div class="row"><button class="btn primary" type="button">Build geometry</button>{reset("isolevel")}</div>
</div>
<div style="display:grid;grid-template-rows:auto 1fr;min-height:0">
  <div class="row focus-ring" style="margin:4px;padding:4px" role="group" aria-label="Layers">
    <span class="muted">Show</span>
    <label class="chip"><input type="checkbox" checked> Density map</label>
    <label class="chip"><input type="checkbox"> Azimuthal variance</label>
    <label class="chip"><input type="checkbox" checked> Contour</label>
    <label class="chip"><input type="checkbox" checked> Probe-radius profile</label>
  </div>
  {field(membrane=False, grad="g-seq2", style="position:relative", corner=f'{cbar("Density, 0 to 1", ticks=("0", "1"))}')}
</div>""")

T0, T1 = S.MEM_TOP, S.MEM_BOT
RX, RY = S.AX + S.R * math.cos(math.radians(-35)), S.CZ + S.R * math.sin(math.radians(-35))
DIMS = (f'<g style="stroke:var(--accent)" stroke-width="1.5"><line x1="128" y1="{T0:.1f}" x2="128" y2="{T1:.1f}"/><line x1="123" y1="{T0:.1f}" x2="133" y2="{T0:.1f}"/><line x1="123" y1="{T1:.1f}" x2="133" y2="{T1:.1f}"/>'
        f'<line x1="{S.AX}" y1="{S.CZ}" x2="{RX:.1f}" y2="{RY:.1f}" stroke-dasharray="4 3"/></g>')
NOTE = '<div class="over cl" style="left:2%;bottom:1%">Not to scale: the reservoir is about a hundred times the pore.</div>'
CENTRE_RO = '<span class="muted">Membrane centre, z: <span class="num">x.xx nm</span>, set in Molecular, Prepare</span>'

ge2a = frame("Region", f"""<div class="pane stack" style="overflow:auto"><h2>Region: membrane and reservoir</h2>
  <span class="muted">Edit the dimensions on the drawing.</span>{CENTRE_RO}
  <div class="later"><b>Sketcher</b>: drawing a pore by hand</div>
</div>
{crz(over=DIMS, style="position:relative", extra=f'''
<div class="over focus-ring" style="{pct(134, T0 - 4)};background:var(--canvas-plot);padding:2px"><label class="cl" for="g2a-t" style="display:block">Thickness</label><span class="row"><input id="g2a-t" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">nm</span></span></div>
<div class="over" style="{pct(40, 30)};background:var(--canvas-plot);padding:2px"><label class="cl" for="g2a-r" style="display:block">Reservoir radius</label><span class="row"><input id="g2a-r" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">nm</span></span></div>
{NOTE}''')}""", cols="180px 230px 1fr")

LEAD = (f'<g style="stroke:var(--accent)" stroke-width="1"><line x1="128" y1="{T0:.1f}" x2="128" y2="{T1:.1f}"/>'
        f'<line x1="{S.AX}" y1="{S.CZ}" x2="{RX:.1f}" y2="{RY:.1f}" stroke-dasharray="4 3"/></g>')

ge2b = frame("Region", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Region: membrane and reservoir</h2>
  {f("g2b-t", "a Thickness", "x.xx", "nm")}{f("g2b-r", "b Reservoir radius", "x.xx", "nm")}{CENTRE_RO}
  <button class="btn primary" type="button" style="justify-self:start">Build region</button>
  <div class="later"><b>Sketcher</b>: drawing a pore by hand</div>
</div>
{crz(over=LEAD, style="position:relative", extra=f'<span class="lbl over" style="{pct(132, (T0 + T1) / 2 - 6)}"><b>a</b></span><span class="lbl over" style="{pct(70, 104)}"><b>b</b></span>{NOTE}')}""")

HMAX = max(S.HIST)


def bars(selected=(3, 4, 5)):
    out = []
    for i, n in enumerate(S.HIST):
        lo, hi = i / 10, (i + 1) / 10
        if not n:
            out.append('<span style="width:24px" aria-hidden="true"></span>')
            continue
        h = max(24, round(126 * math.sqrt(n / HMAX)))
        pr = "true" if i in selected else "false"
        out.append(f'<button type="button" aria-pressed="{pr}" style="height:{h}px" aria-label="SICN {lo:.1f} to {hi:.1f}: {n} elements"></button>')
    return f'<div class="bars" role="group" aria-label="Histogram of SICN, square-root scale">{"".join(out)}<span class="gate" style="left:{3 * 26}px" aria-hidden="true"></span></div>'


MEASURE = '<div class="row"><label for="{p}-q" class="muted">Measure</label><select id="{p}-q"><option>SICN</option><option>Gamma</option></select></div>'
GATE = '<span class="ok">Quality gate passed: every element above 0.3 in SICN and gamma, none inverted</span>'
WORST = f'<path d="{S.WORST}" style="fill:var(--accent);stroke:var(--ink)" stroke-width=".8"/>'
WX, WY = S.WORST_POS

me1a = frame("Mesh", f"""<div class="pane stack focus-ring" style="margin:4px"><h2>Mesh · size</h2>
  <label for="m1a-r">Size scale <span class="num muted">1.0, the reference</span></label>
  <input id="m1a-r" type="range" min="0" max="4" value="2">
  <div class="row muted" style="justify-content:space-between;width:12rem;font-size:var(--text-xs)"><span>finer</span><span>reference</span><span>coarser</span></div>
  <div class="field"><span class="k">Wall layer</span><span class="v">auto, from the Debye length</span></div>
  <span class="muted">Only the reference is validated; a coarser scale may fail the quality gate.</span>
  <div class="row"><button class="btn primary" type="button">Build mesh</button><button class="btn" type="button">Edit sizes…</button></div>
  <div class="field"><span class="k">Last build</span><span class="v"><span class="ok">gate passed</span> <span class="num">x.x k elements</span></span></div>
</div>
{crz(sym="mesh-rz", style="position:relative")}""")

SIZES = [("Global", "x.xx", "x.xx", "x.xx", False), ("Pore boundary", "x.xx", "x.xx", "x.xx", True),
         ("Pore domain", "x.xx", "x.xx", "x.xx", False), ("Reservoir domain", "x.xx", "x.xx", "x.xx", False),
         ("Reservoir outer boundary", "x.xx", "x.xx", "—", False), ("Axis", "x.xx", "x.xx", "—", False)]


def size_rows():
    out = []
    for name, mx, mn, gr, chg in SIZES:
        cur = ' aria-current="true"' if chg else ""
        mark = f'<span class="chg">changed</span> {reset(name + " maximum size")}' if chg else ""
        out.append(f'<tr{cur}><td>{name}</td><td><input class="num" type="text" value="{mx}" aria-label="{name} maximum size, nm" style="width:3.6rem"></td>'
                   f'<td><input class="num" type="text" value="{mn}" aria-label="{name} minimum size, nm" style="width:3.6rem"></td><td class="num">{gr}</td><td>{mark}</td></tr>')
    return "".join(out)


me1b = frame("Mesh", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Mesh · sizes</h2>
  <table><thead><tr><th>Part</th><th>Max, nm</th><th>Min, nm</th><th>Growth</th><th></th></tr></thead><tbody>{size_rows()}</tbody></table>
  <span class="muted">The membrane is sized at its own thickness.</span>
  <div class="row"><button class="btn primary" type="button">Build mesh</button><span class="ok">last build: gate passed</span></div>
</div>
{crz(sym="mesh-rz", style="position:relative")}""", cols="180px 430px 1fr")

me2a = frame("Mesh", f"""<div class="pane stack focus-ring" style="margin:4px"><h2>Mesh · quality</h2>
  {MEASURE.format(p="m2a")}
  {bars()}
  <div class="row num cl" style="justify-content:space-between;width:258px"><span>0</span><span>0.3 gate</span><span>1</span></div>
  <span class="muted">Select bars to mark their elements in the view. Selected: the <span class="num">xx</span> elements from 0.3 to 0.6.</span>
  {GATE}
</div>
{crz(sym="mesh-rz", over=WORST, style="position:relative", extra=f'<span class="lbl over" style="{pct(WX - 60, WY + 12)};background:var(--canvas-plot);color:var(--canvas-plot-ink)">◉ selected elements</span>')}""")

COL_SVG = f'<svg viewBox="0 0 180 300" width="100%" height="100%" style="color:var(--canvas-plot-ink)">{S.COLOURED}<use href="#pore-rz"/>{WORST.replace("var(--accent)", "none")}</svg>'
me2b = frame("Mesh", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Mesh · quality</h2>
  {MEASURE.format(p="m2b").replace("Measure", "Colour by")}
  <label for="m2b-t" class="muted">Outline elements below <span class="num">0.50</span></label><input id="m2b-t" type="range" min="30" max="100" value="50">
  <table><thead><tr><th>Worst</th><th>SICN</th><th>Where</th></tr></thead><tbody>
  <tr aria-current="true"><td class="num">1</td><td class="num">x.xx</td><td>membrane and reservoir corner</td></tr>
  <tr><td class="num">2</td><td class="num">x.xx</td><td>membrane and reservoir corner</td></tr>
  <tr><td class="num">3</td><td class="num">x.xx</td><td>reservoir arc</td></tr></tbody></table>
  {GATE}
</div>
<div class="cplot" style="position:relative" role="img" aria-label="Mesh coloured by SICN"><div class="vb" style="aspect-ratio:180 / 300">{COL_SVG}</div><div class="corner">{cbar("SICN", ticks=("0.3", "1"))}</div></div>""")

BND = [("Cis reservoir boundary", "Ground, bulk concentration"), ("Trans reservoir boundary", "Bias, bulk concentration"),
       ("Protein surface", "No flux, no slip"), ("Membrane surface", "No flux, no slip"), ("Axis", "Symmetry")]


def bnd_rows():
    out = []
    for i, (name, cond) in enumerate(BND):
        cur = ' aria-current="true"' if i == 2 else ""
        out.append(f'<tr{cur}><td>{name}</td><td><select aria-label="Condition on {name}"><option>{cond}</option></select></td></tr>')
    return "".join(out)


HILITE = f'<polygon points="{S.pts(S.PROT)}" fill="none" style="stroke:var(--accent)" stroke-width="3"/>'
SIDES = f'<span class="lbl over" style="{pct(150, 40)}">cis</span><span class="lbl over" style="{pct(150, 250)}">trans</span>'
CHARGE_NOTE = '<span class="muted">The protein\'s fixed charge is a volume charge from the molecular model, assembled on the mesh in the study.</span>'

ph1a = frame("Physics defaults", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Physics defaults · boundaries</h2>
  <table><thead><tr><th>Boundary</th><th>Condition</th></tr></thead><tbody>{bnd_rows()}</tbody></table>
  {CHARGE_NOTE}<span class="muted">Selecting a row highlights the boundary. A study may override any condition.</span>
</div>
{crz(over=HILITE, style="position:relative", extra=SIDES)}""", cols="180px 380px 1fr")

ph1b = frame("Physics defaults", f"""{crz(over=HILITE, style="position:relative", extra=SIDES + f'<span class="lbl over" style="{pct(60, 75)};background:var(--canvas-plot);color:var(--canvas-plot-ink)">◉ protein surface</span>')}
<div class="pane stack focus-ring" style="margin:4px"><h2>Protein surface</h2>
  <div class="field"><label for="p1b-c">Condition</label><div class="v"><select id="p1b-c"><option>No flux, no slip</option></select></div></div>
  {CHARGE_NOTE}
  <hr><span class="h">All boundaries</span>
  <ul class="tools"><li><button type="button">Cis reservoir boundary</button></li><li><button type="button">Trans reservoir boundary</button></li><li><button type="button" aria-current="true">Protein surface</button></li><li><button type="button">Membrane surface</button></li><li><button type="button">Axis</button></li></ul>
</div>""", cols="180px 1fr 320px")

MODEL = '<div class="field"><label for="{p}-m">Model</label><div class="v"><select id="{p}-m"><option>ePNP-NS</option><option>PNP-NS</option><option>PNP</option><option>PB</option></select></div></div>'
CORR = '<div class="field"><span class="k">Corrections</span><span class="v">as validated <button class="btn small" type="button">Show the list</button></span></div>'
COMPOSER = '<div class="later"><b>Composer</b>: a model of your own equations</div>'

ph2a = frame("Physics defaults", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Physics defaults · electrolyte</h2>
  {MODEL.format(p="p2a")}
  <div class="field"><label for="p2a-e">Electrolyte</label><div class="v"><select id="p2a-e"><option>NaCl</option></select></div></div>
  <div class="field"><label for="p2a-c">Concentration</label><div class="v"><input id="p2a-c" class="num" type="text" value="" placeholder="set" aria-describedby="p2a-n"><span class="unit">M</span></div></div>
  <div class="muted" id="p2a-n">No default: set the salt here or in the study.</div>
  {CORR}{COMPOSER}
</div>
{crz(style="position:relative")}""")

ph2b = frame("Physics defaults", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Physics defaults · species</h2>
  {MODEL.format(p="p2b")}
  <div class="field"><label for="p2b-c">NaCl, bulk</label><div class="v"><input id="p2b-c" class="num" type="text" placeholder="set"><span class="unit">M</span></div></div>
  <table><thead><tr><th>Ion</th><th>z</th><th>Bulk, M</th><th>D, 10⁻⁹ m²/s</th></tr></thead><tbody>
  <tr><td>Na⁺</td><td class="num">+1</td><td class="muted">as the salt</td><td class="num">x.xx</td></tr>
  <tr><td>Cl⁻</td><td class="num">−1</td><td class="muted">as the salt</td><td class="num">x.xx</td></tr></tbody></table>
  <span class="muted">The bulk is electroneutral; D at infinite dilution, scaled by the corrections.</span>
  {CORR}{COMPOSER}
</div>
{crz(style="position:relative")}""")

GEOMETRY = [
    ("GE1", "How the protein geometry tool is laid out (WB-15)", {
        "a": ("Steps by stage, each with a thumbnail and its gate", ge1a),
        "b": ("Folding sections, one large view with layer switches", ge1b)}),
    ("GE2", "How the region is dimensioned", {
        "a": ("Dimensions edited on the drawing, as in AutoCAD", ge2a),
        "b": ("A form, its fields lettered on the drawing", ge2b)}),
]
MESH = [
    ("ME1", "How the mesh size is set", {
        "a": ("One size scale around the validated reference", me1a),
        "b": ("The size table: each part's maximum, minimum and growth", me1b)}),
    ("ME2", "How the mesh quality is inspected", {
        "a": ("A histogram of SICN or gamma, its bars selecting elements", me2a),
        "b": ("The mesh coloured by the measure, the worst elements listed", me2b)}),
]
PHYSICS = [
    ("PH1", "How conditions are put on boundaries (WB-16)", {
        "a": ("A list of the boundaries, a condition each", ph1a),
        "b": ("Pick a boundary in the view; its properties beside", ph1b)}),
    ("PH2", "How the electrolyte is set", {
        "a": ("A salt from the registry and one concentration", ph2a),
        "b": ("A table of the ions under one salt concentration", ph2b)}),
]
