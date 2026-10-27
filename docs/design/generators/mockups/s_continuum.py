"""02-geometry, 03-mesh, 04-physics: the Continuum suite (WB-15, WB-16; GE1 B, GE2 both, E3, ME1 and ME2 both, PH1 B, PH2 B)."""

import math

from mk import NOT_TO_SCALE, S, cbar, f, fieldmap, pct, reset, ro, route, spot, viewrz, window

ITEM = "ClyA pore, reference mesh"
CONTOUR = (
    f'<polygon points="{S.pts(S.PROT)}" fill="none" style="stroke:var(--accent)" stroke-width="2"/>'
    f'<polygon points="{S.PROBE}" fill="none" style="stroke:var(--warn)" stroke-width="1.5" stroke-dasharray="3 2"/>'
)
ISO_ROW = (
    '<div class="row" style="padding-left:8.5rem"><span class="chg">changed</span><span class="muted">default <span class="num">0.25</span></span>'
    + reset("isolevel")
    + "</div>"
)
SOURCE = '<span class="muted">From the molecular model 2WCD, pH 7.5. Stage 1, alignment, is done in Molecular, Prepare.</span>'


def geometry():
    body = f"""<div class="settings"><h2>Protein geometry</h2>{SOURCE}
  <details open><summary><b>Density</b>, stage 2 <span class="ok">built</span></summary>
    {f("cg-h", "Grid spacing", "0.05", "nm")}<div class="field"><label for="cg-k">Kernel</label><div class="v"><select id="cg-k"><option>Gaussian, van der Waals</option></select></div></div></details>
  <details><summary><b>Symmetry to (r, z)</b>, stage 3 <span class="ok">built</span></summary>{ro("Point group", "C12")}</details>
  <details open><summary><b>Contour</b>, stage 4 <span class="ok">gate passed</span></summary>
    {f("cg-i", "Isolevel", "x.xx")}{ISO_ROW}<a class="btn small" href="#g-contour" style="justify-self:start">Edit the contour…</a></details>
  <div class="row"><button class="btn primary" type="button">Build geometry</button></div>
</div>
<div class="viewwrap" style="grid-template-rows:auto minmax(0,1fr)">
  <div class="toolbar" role="group" aria-label="Layers"><span class="muted">Show</span>
    <label class="chip"><input type="checkbox" checked> Density map</label><label class="chip"><input type="checkbox"> Azimuthal variance</label>
    <label class="chip"><input type="checkbox" checked> Contour</label><label class="chip"><input type="checkbox" checked> Probe-radius profile</label></div>
  {fieldmap(grad="g-seq2", membrane=False, over=CONTOUR, cards=f'<div class="corner">{cbar("Density, 0 to 1", ticks=("0", "1"))}</div>')}
</div>"""
    return window(
        "02-geometry.html", "continuum", "Protein geometry", body, "340px minmax(0,1fr)", item=ITEM
    )


VERTS = "".join(
    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" style="fill:var(--panel);stroke:var(--accent)" stroke-width="1.5"/>'
    for x, y in S.PROT
)
SELV = f'<circle cx="{S.PROT[5][0]:.1f}" cy="{S.PROT[5][1]:.1f}" r="4.5" fill="none" style="stroke:var(--ink)" stroke-width="1.5"/>'
PROFILE = """<svg viewBox="0 0 200 110" width="100%" height="100%" preserveAspectRatio="none" role="img" aria-label="Pore radius against z: the contour and the probe-radius profile">
<line x1="20" y1="95" x2="195" y2="95" stroke="currentColor" stroke-opacity=".5"/><line x1="20" y1="5" x2="20" y2="95" stroke="currentColor" stroke-opacity=".5"/>
<polyline points="20,30 50,32 80,60 110,72 140,74 170,73 195,72" fill="none" style="stroke:var(--accent)" stroke-width="2"/>
<polyline points="20,36 50,38 80,64 110,77 140,79 170,78 195,77" fill="none" style="stroke:var(--warn)" stroke-width="1.5" stroke-dasharray="4 3"/></svg>"""


EDITBAR = """<div class="over card" style="left:8px;top:8px;right:8px;padding:6px;gap:4px">
  <div class="toolbar"><button class="btn small" type="button">Undo</button><button class="btn small" type="button">Redo</button><button class="btn small" type="button">Delete vertex</button>
    <button class="btn small" type="button">Measure criteria</button><span class="chip"><span style="color:var(--accent)">━</span> contour</span><span class="chip"><span style="color:var(--warn)">┅</span> probe-radius profile</span></div>
  <span class="muted" style="font-size:var(--text-xs)">Drag a vertex to move it; double-click an edge to insert one; Delete removes the selected one, never below three.</span></div>"""


def contour():
    rows = "".join(
        f'<tr{' aria-current="true"' if i == 5 else ""}><td class="num">{i + 1}</td><td class="num">x.xx</td><td class="num">x.xx</td></tr>'
        for i in range(8)
    )
    body = f"""<div class="settings"><h2>Contour · stage 4</h2>{SOURCE}
  {f("cc-i", "Isolevel", "x.xx")}{ISO_ROW}
  <div class="field"><label for="cc-s">Smoothing</label><div class="v"><select id="cc-s"><option>Taubin</option><option>None</option></select></div></div>
  {f("cc-t", "Simplification", "0.02", "nm")}
  <div class="verdict"><span class="ok">Gate passed: the radius follows the probe-radius profile within x.xx nm</span><button class="btn small" type="button" aria-expanded="false">Checks</button></div>
  <div class="tile" style="height:190px"><b>Radius against z</b><div style="display:grid;grid-template-columns:auto minmax(0,1fr);grid-template-rows:minmax(0,1fr) auto;min-height:0"><span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Radius, nm</span>{PROFILE}<span></span><span class="cl" style="text-align:center">z, nm</span></div></div>
  <h3>Vertices · x after simplification</h3>
  <table><thead><tr><th>#</th><th>r, nm</th><th>z, nm</th></tr></thead><tbody>{rows}</tbody></table>
  <div class="row"><button class="btn" type="button">Seed from refusal</button><button class="btn primary" type="button">Save edit…</button></div>
  <span class="muted">Saving writes the edited profile and a derived continuum model; this one is unchanged.</span>
  <div class="later"><b>Sketcher</b>: drawing a pore by hand</div>
</div>
<div class="viewwrap">
  {viewrz(sym="protein-rz", over=CONTOUR + VERTS + SELV, cards=EDITBAR)}
</div>"""
    return window(
        "02-geometry.html", "continuum", "Contour", body, "340px minmax(0,1fr)", item=ITEM
    )


T0, T1 = S.MEM_TOP, S.MEM_BOT
RX, RY = S.AX + S.R * math.cos(math.radians(75)), S.CZ + S.R * math.sin(math.radians(75))
DIMS = (
    f'<g style="stroke:var(--accent)" stroke-width="1.5"><line x1="128" y1="{T0:.1f}" x2="128" y2="{T1:.1f}"/><line x1="123" y1="{T0:.1f}" x2="133" y2="{T0:.1f}"/><line x1="123" y1="{T1:.1f}" x2="133" y2="{T1:.1f}"/>'
    f'<line x1="{S.AX}" y1="{S.CZ}" x2="{RX:.1f}" y2="{RY:.1f}" stroke-dasharray="4 3"/></g>'
)
CENTRE_RO = ro(
    "Membrane centre, z",
    '<span class="num">x.xx nm</span> <span class="muted">set in Molecular, Prepare</span>',
)


def region_body(refused=False):
    if refused:
        t = """<div class="field"><label for="cr-t">a Thickness</label><div class="v"><input id="cr-t" class="num refused" type="text" value="x.xx" aria-invalid="true" aria-describedby="cr-m"><span class="unit">nm</span></div></div>
  <div class="msg" id="cr-m">✕ x.xx nm is outside x.xx to x.xx nm. Enter a thickness in that range. <span class="num">geometry.membrane.thickness_nm</span></div>"""
        tin = '<input id="cr-dt" class="num refused" type="text" value="x.xx" style="width:4rem" aria-invalid="true" aria-label="a Thickness, on the drawing">'
    else:
        t = f("cr-t", "a Thickness", "2.8", "nm")
        tin = '<input id="cr-dt" class="num" type="text" value="2.8" style="width:4rem" aria-label="a Thickness, on the drawing">'
    on_drawing = f'''<div class="over" style="{pct(134, T0 - 4)};background:var(--canvas-plot);padding:2px"><span class="cl" style="display:block"><b>a</b> Thickness</span><span class="row">{tin}<span class="unit">nm</span></span></div>
<div class="over" style="{pct(44, 236)};background:var(--canvas-plot);padding:2px"><span class="cl" style="display:block"><b>b</b> Reservoir radius, from the axis</span><span class="row"><input class="num" type="text" value="250" style="width:4rem" aria-label="b Reservoir radius, on the drawing"><span class="unit">nm</span></span></div>'''
    return f"""<div class="settings"><h2>Region: membrane and reservoir</h2>
  {t}{f("cr-r", "b Reservoir radius", "250", "nm")}{CENTRE_RO}
  <span class="muted">Each value can be typed here or on the drawing; both show the same value.</span>
  <div class="row">{'<button class="btn primary" type="button" disabled aria-describedby="cr-m">Build region</button><span class="muted">clear the refusal first</span>' if refused else '<button class="btn primary" type="button">Build region</button><span class="ok">built</span>'}</div>
  <div class="later"><b>Sketcher</b>: drawing a pore by hand</div>
</div>
<div class="viewwrap">{viewrz(over=DIMS, inside=on_drawing, cards=NOT_TO_SCALE)}</div>"""


def region():
    return window(
        "02-geometry.html", "continuum", "Region", region_body(), "320px minmax(0,1fr)", item=ITEM
    )


PROBLEMS = """<div class="qrow" style="grid-template-columns:1.4rem 1fr auto"><span class="err" aria-hidden="true"></span><span><b>Region · membrane thickness</b>: x.xx nm is outside x.xx to x.xx nm; enter a thickness in that range. <span class="num muted">geometry.membrane.thickness_nm</span></span><a class="btn small" href="#g-problems">Go to field</a></div>"""


def problems():
    pop = f"""<div class="card" role="dialog" aria-label="Problems" style="position:absolute;top:40px;right:12px;width:440px;z-index:5;box-shadow:0 6px 20px rgb(0 0 0 / .25)">
  <h2 class="h">1 problem in Continuum</h2>{PROBLEMS}</div>"""
    return window(
        "02-geometry.html",
        "continuum",
        "Region",
        region_body(refused=True),
        "320px minmax(0,1fr)",
        item=ITEM,
        overlay=pop,
        fail=("Region", "refused"),
        problems={"continuum": 1},
    )


GEOMETRY = [
    ("g-geometry", "Continuum · Protein geometry", geometry),
    ("g-contour", "Continuum · Contour", contour),
    ("g-region", "Continuum · Region", region),
    ("g-problems", "Continuum · Region, a refused value", problems),
]

# Mesh -----------------------------------------------------------------------------------------------------------

SIZES = [
    ("Global", "x.xx", "x.xx", "x.xx", False),
    ("Pore boundary", "x.xx", "x.xx", "x.xx", True),
    ("Pore domain", "x.xx", "x.xx", "x.xx", False),
    ("Reservoir domain", "x.xx", "x.xx", "x.xx", False),
    ("Reservoir outer boundary", "x.xx", "x.xx", "—", False),
    ("Axis", "x.xx", "x.xx", "—", False),
]


def size_rows():
    out = []
    for name, mx, mn, gr, chg in SIZES:
        chg = chg and not route()
        cur = ' aria-current="true"' if chg else ""
        mark = (
            f'<span class="chg">changed</span> {reset(name + " maximum size")}'
            if chg
            else '<span class="muted">from the scale</span>'
        )
        out.append(
            f'<tr{cur}><td>{name}</td><td><input class="num" type="text" value="{mx}" aria-label="{name} maximum size, nm" style="width:3.6rem"></td>'
            f'<td><input class="num" type="text" value="{mn}" aria-label="{name} minimum size, nm" style="width:3.6rem"></td><td class="num">{gr}</td><td>{mark}</td></tr>'
        )
    return "".join(out)


BUILD = '<div class="row"><button class="btn primary" type="button">Build mesh</button><span class="muted">x.x k elements</span></div>'
GATE = '<div class="verdict"><span class="ok">Quality gate passed: every element above 0.3 in SICN and gamma, none inverted</span><a class="btn small" href="#s-quality">Inspect quality</a></div>'


def size():
    body = f"""<div class="settings"><h2>Mesh · sizes</h2>
  <div class="field"><label for="ms-m">Mesher</label><div class="v"><select id="ms-m"><option>Netgen (default)</option><option>Gmsh (optional, its own licence)</option></select></div></div>
  <fieldset style="border:0;padding:0;margin:0;display:grid;gap:2px"><legend class="h">Elements</legend>
    <label class="row"><input type="radio" name="ms-e" checked> Free triangles, as validated</label>
    <div class="later"><b>Boundary layers</b> at the wall</div></fieldset>
  <h3>Size scale</h3>
  <div class="row"><input id="ms-r" type="range" min="0" max="4" value="2" aria-label="Size scale"><input class="num" type="text" value="1.00" style="width:4rem" aria-label="Size scale, typed"><span class="muted">1.00, the reference</span></div>
  <span class="muted">The scale multiplies every part's sizes. Only the reference is validated; a coarser scale may fail the quality gate.</span>
  {spot("mesh", BUILD)}{'<div class="verdict"><span class="muted">Not built yet</span></div>' if route() else GATE}
  <details open><summary><b>Per part</b>, a typed size overriding the scale</summary>
  <table><thead><tr><th>Part</th><th>Max, nm</th><th>Min, nm</th><th>Growth</th><th></th></tr></thead><tbody>{size_rows()}</tbody></table>
  <span class="muted">The membrane is sized at its own thickness.</span></details>
  <div class="later"><b>Refinement regions</b> drawn by hand, each with its own sizes</div>
</div>
<div class="viewwrap">{viewrz(sym="pore-rz" if route() else "mesh-rz", cards=NOT_TO_SCALE)}</div>"""
    return window("03-mesh.html", "continuum", "Mesh", body, "520px minmax(0,1fr)", item=ITEM)


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
        out.append(
            f'<button type="button" aria-pressed="{pr}" style="height:{h}px" aria-label="SICN {lo:.1f} to {hi:.1f}: {n} elements"></button>'
        )
    return f'<div class="bars" role="group" aria-label="Histogram of SICN, square-root scale">{"".join(out)}<span class="gate" style="left:{3 * 26}px" aria-hidden="true"></span></div>'


WORST = f'<path d="{S.WORST}" fill="none" stroke="#ffffff" stroke-width="3"/><path d="{S.WORST}" fill="none" stroke="#16181d" stroke-width="1.5"/>'
COLOURED = f'{S.COLOURED}<use href="#pore-rz"/>'


def quality():
    body = f"""<div class="settings"><h2>Mesh · quality</h2>
  <div class="row"><label for="mq-q" class="muted">Measure</label><select id="mq-q"><option>SICN</option><option>Gamma</option></select></div>
  <h3>Histogram · select bars to outline their elements</h3>
  <div style="display:grid;grid-template-columns:auto 1fr;gap:4px;align-items:end"><span class="cl" style="writing-mode:vertical-rl;transform:rotate(180deg)">Elements, √ scale</span>{bars()}</div>
  <div class="row num cl" style="justify-content:space-between;width:258px"><span>0</span><span>0.3 gate</span><span>1</span></div>
  <span class="muted">Selected: the <span class="num">xx</span> elements from 0.3 to 0.6, outlined in the view.</span>
  <h3>Worst elements</h3>
  <table><thead><tr><th>#</th><th>SICN</th><th>Where</th></tr></thead><tbody>
  <tr aria-current="true"><td class="num">1</td><td class="num">x.xx</td><td>membrane and reservoir corner</td></tr>
  <tr><td class="num">2</td><td class="num">x.xx</td><td>membrane and reservoir corner</td></tr>
  <tr><td class="num">3</td><td class="num">x.xx</td><td>reservoir arc</td></tr></tbody></table>
  <div class="verdict"><span class="ok">Quality gate passed: every element above 0.3 in SICN and gamma, none inverted</span></div>
</div>
<div class="viewwrap" style="grid-template-rows:auto minmax(0,1fr)">
  <div class="toolbar"><span class="muted">Colour the mesh by</span><div class="tabs" role="tablist" aria-label="Colour the mesh by"><button type="button" role="tab" aria-selected="true">SICN</button><button type="button" role="tab" aria-selected="false">Gamma</button><button type="button" role="tab" aria-selected="false">None</button></div></div>
  {viewrz(raw=COLOURED, over=WORST, label="Mesh coloured by SICN, the selected elements outlined", cards=f'<div class="corner">{cbar("SICN", ticks=("0.3", "1"))}</div>' + NOT_TO_SCALE)}
</div>"""
    return window("03-mesh.html", "continuum", "Mesh", body, "340px minmax(0,1fr)", item=ITEM)


MESH = [
    ("s-size", "Continuum · Mesh, sizes", size),
    ("s-quality", "Continuum · Mesh, quality", quality),
]

# Physics ----------------------------------------------------------------------------------------------------------

HILITE = (
    f'<polygon points="{S.pts(S.PROT)}" fill="none" style="stroke:var(--accent)" stroke-width="3"/>'
)
SIDES = f'<span class="lbl over" style="{pct(150, 40)}">cis</span><span class="lbl over" style="{pct(150, 250)}">trans</span>'
CHARGE_NOTE = '<span class="muted">The protein\'s fixed charge is a volume charge from the molecular model, assembled on the mesh in the study.</span>'
PTABS = '<div class="tabs" role="tablist" aria-label="Physics defaults"><a role="tab" href="{b}" aria-selected="{x}">Boundaries</a><a role="tab" href="{e}" aria-selected="{y}">Model and electrolyte</a></div>'


def boundaries():
    body = f"""<div class="settings">{PTABS.format(b="#p-boundaries", e="#p-electrolyte", x="true", y="false")}
  <h2>Protein surface</h2>
  <div class="field"><label for="pb-c">Condition</label><div class="v"><select id="pb-c"><option>No flux, no slip</option></select></div></div>
  {CHARGE_NOTE}
  <h3>All boundaries · pick in the view or here</h3>
  <table><thead><tr><th>Boundary</th><th>Condition</th></tr></thead><tbody>
  <tr><td>Cis reservoir boundary</td><td>Ground, bulk concentration</td></tr>
  <tr><td>Trans reservoir boundary</td><td>Bias, bulk concentration</td></tr>
  <tr aria-current="true"><td>Protein surface</td><td>No flux, no slip</td></tr>
  <tr><td>Membrane surface</td><td>No flux, no slip</td></tr>
  <tr><td>Axis</td><td>Symmetry</td></tr></tbody></table>
  <span class="muted">These are the continuum model's defaults; a study may override any of them.</span>
</div>
<div class="viewwrap">{viewrz(over=HILITE, inside=SIDES + f'<span class="lbl over" style="{pct(60, 75)}">◉ protein surface</span>', cards=NOT_TO_SCALE)}</div>"""
    return window(
        "04-physics.html", "continuum", "Physics defaults", body, "380px minmax(0,1fr)", item=ITEM
    )


MODEL = '<div class="field"><label for="pe-m">Model</label><div class="v"><select id="pe-m"><option>ePNP-NS</option><option>PNP-NS</option><option>PNP</option><option>PB</option></select></div></div>'


def electrolyte():
    salt = spot(
        "salt",
        '<div class="field"><label for="pe-c">NaCl, bulk</label><div class="v"><input id="pe-c" class="num" type="text" placeholder="set" aria-describedby="pe-n"><span class="unit">M</span></div></div>',
    )
    body = f"""<div class="settings">{PTABS.format(b="#p-boundaries", e="#p-electrolyte", x="false", y="true")}
  <h2>Model and electrolyte</h2>
  {MODEL}
  {salt}
  <span class="muted" id="pe-n">No default: set the salt here or as a study's override.</span>
  <table><thead><tr><th>Ion</th><th>z</th><th>Bulk, M</th><th>D, 10⁻⁹ m²/s</th></tr></thead><tbody>
  <tr><td>Na⁺</td><td class="num">+1</td><td class="muted">as the salt</td><td class="num">x.xx</td></tr>
  <tr><td>Cl⁻</td><td class="num">−1</td><td class="muted">as the salt</td><td class="num">x.xx</td></tr></tbody></table>
  <span class="muted">The bulk is electroneutral; D at infinite dilution, scaled by the corrections.</span>
  <div class="field"><span class="k">Corrections</span><span class="v">as validated, willems2020_nacl <button class="btn small" type="button">Show the list</button></span></div>
  <div class="field"><span class="k">Permittivity</span><span class="v num">protein x.x, membrane x.x</span></div>
  <div class="later"><b>Composer</b>: a model of your own equations</div>
</div>
<div class="viewwrap">{viewrz(inside=SIDES, cards=NOT_TO_SCALE)}</div>"""
    return window(
        "04-physics.html", "continuum", "Physics defaults", body, "380px minmax(0,1fr)", item=ITEM
    )


PHYSICS = [
    ("p-boundaries", "Continuum · Physics defaults, boundaries", boundaries),
    ("p-electrolyte", "Continuum · Physics defaults, model and electrolyte", electrolyte),
]
