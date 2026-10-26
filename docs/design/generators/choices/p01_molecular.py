"""01-molecular: the Prepare tool (WB-14), the charge edit, the protonation overview."""

from parts import c3d, queue, reset, suite_tabs, titlebar, tools

G = "display:grid;grid-template-columns:{cols};min-height:0"


def frame(tool, body, cols="180px 330px 1fr"):
    return f"""<div class="win" style="grid-template-rows:auto 1fr auto">
{titlebar(suite_tabs("Molecular"))}
<div style="{G.format(cols=cols)}">
  <div class="pane"><h2>Molecular tools</h2>{tools("molecular", tool)}</div>
  {body}
</div>
{queue()}
</div>"""


AXIS = ('<line x1="150" y1="14" x2="150" y2="292" style="stroke:var(--accent)" stroke-width="2" stroke-dasharray="6 4"/>'
        '<rect x="40" y="214" width="220" height="26" fill="none" style="stroke:var(--warn)" stroke-width="2"/>')
HANDLES = ('<circle cx="150" cy="18" r="7" style="fill:var(--accent)"/><path d="M143 30 L150 18 L157 30" fill="none" style="stroke:var(--canvas-3d-ink)" stroke-width="2"/>'
           '<rect x="252" y="221" width="14" height="12" rx="2" style="fill:var(--warn)"/><rect x="34" y="221" width="14" height="12" rx="2" style="fill:var(--warn)"/>')

mo1a = frame("Prepare structure", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Prepare structure · 2WCD</h2>
  <ol class="stack" style="margin:0;padding-left:18px">
    <li><b>Chains</b> <span class="ok">12 of 12 chosen</span><div class="row" style="margin-top:4px">
      <label class="row"><input type="checkbox" checked> A–L</label><button class="btn small" type="button">Choose…</button></div></li>
    <li><b>Axis</b> <span class="ok">estimated</span><div class="field"><label for="m1a-tl">Tilt from z</label><div class="v"><input id="m1a-tl" class="num" type="text" value="x.xx"><span class="unit">°</span></div></div>
      <div class="row"><button class="btn small" type="button">Estimate again</button><button class="btn small" type="button">Set in the view</button></div></li>
    <li><b>Flip</b><div class="row" style="margin-top:4px"><label class="row"><input type="radio" name="m1a-f" checked> Cap on the cis side</label><label class="row"><input type="radio" name="m1a-f"> Flipped</label></div></li>
    <li><b>Membrane place</b><div class="field"><label for="m1a-z">Centre, z</label><div class="v"><input id="m1a-z" class="num" type="text" value="x.xx"><span class="unit">nm</span></div></div>
      <span class="muted">Thickness is set in Continuum, Region.</span></li>
  </ol>
  <div class="row"><button class="btn primary" type="button">Save molecular model</button></div>
</div>
{c3d(over=AXIS, style="position:relative")}""")

mo1b = frame("Prepare structure", c3d(over=AXIS + HANDLES, style="position:relative", extra="""
<div class="over focus-ring" style="left:-30%;top:4%;width:280px;background:var(--panel);color:var(--ink);border-radius:var(--radius);padding:8px;display:grid;gap:6px">
  <b>Prepare · 2WCD</b>
  <div class="row"><span class="muted">Chains</span><button class="chip" type="button" aria-pressed="true">A–L, 12</button></div>
  <div class="row"><label for="m1b-tl" class="muted">Axis tilt</label><input id="m1b-tl" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">°</span><button class="btn small" type="button">Estimate</button></div>
  <div class="row"><label for="m1b-z" class="muted">Membrane centre, z</label><input id="m1b-z" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">nm</span></div>
  <div class="row"><button class="btn small" type="button">Flip</button><button class="btn primary small" type="button">Save model</button></div>
  <span class="muted" style="font-size:var(--text-xs)">Drag the axis by its top handle, the membrane by its ends; or type the values.</span>
</div>"""), cols="180px 1fr")

RES = [("ASP 64", "ASP, −1", ["ASP, −1 (default)", "ASH, 0"], "ASH, 0", "0", "x.x"),
       ("ASP xx", "ASP, −1", ["ASP, −1 (default)", "ASH, 0"], None, "−1", "x.x"),
       ("GLU xx", "GLU, −1", ["GLU, −1 (default)", "GLH, 0"], None, "−1", "x.x"),
       ("HIS xx", "HIE, 0", ["HID, 0", "HIE, 0 (default)", "HIP, +1"], None, "0", "x.x")]


def res_rows():
    out = []
    for i, (name, dflt, opts, chosen, q, pka) in enumerate(RES):
        cur = ' aria-current="true"' if i == 0 else ""
        options = "".join(f"<option{' selected' if chosen and o.startswith(chosen) else ''}>{o}</option>" for o in opts)
        mark = f'<span class="chg">changed</span> {reset(name + " state")}' if chosen else ""
        out.append(f'<tr{cur}><td>{name}</td><td class="num">{pka}</td><td><select aria-label="State of {name}">{options}</select> {mark}</td><td class="num">{q}</td></tr>')
    return "".join(out)


mo2a = frame("Charge edit", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Charge edit · a charge-level variant</h2>
  <div class="row"><label for="m2a-s" class="muted">Find</label><input id="m2a-s" type="text" placeholder="residue or number" style="width:9rem"><span class="muted">at pH 7.5, on all 12 chains</span></div>
  <table><thead><tr><th>Residue</th><th>pKa</th><th>State</th><th>Charge, e</th></tr></thead><tbody>{res_rows()}</tbody></table>
  <div class="row"><button class="btn primary" type="button">Save as variant…</button><span class="muted">its parent: 2WCD, pH 7.5</span></div>
  <div class="later"><b>Structural mutator</b>: replacing a side chain</div>
</div>
{c3d(over='<circle cx="118" cy="190" r="10" fill="none" style="stroke:var(--accent)" stroke-width="3"/>', style="position:relative")}""", cols="180px 380px 1fr")

mo2b = frame("Charge edit", c3d(over='<circle cx="118" cy="190" r="10" fill="none" style="stroke:var(--accent)" stroke-width="3"/>', style="position:relative", extra=f"""
<div class="over focus-ring" role="dialog" aria-label="ASP 64" style="left:46%;top:50%;width:270px;background:var(--panel);color:var(--ink);border-radius:var(--radius);padding:8px;display:grid;gap:6px">
  <b>ASP 64 · on all 12 chains</b><span class="muted">pKa x.x · default at pH 7.5: ASP, −1</span>
  <fieldset style="border:0;padding:0;margin:0;display:grid;gap:4px"><legend class="h">Protonation state</legend>
    <label class="row"><input type="radio" name="m2b"> ASP, −1 (default)</label>
    <label class="row"><input type="radio" name="m2b" checked> ASH, 0 <span class="chg">changed</span></label></fieldset>
  <div class="row"><button class="btn primary small" type="button">Save as variant…</button>{reset("ASP 64 state")}</div>
</div>
<div class="over" style="left:2%;bottom:3%;display:flex;gap:6px"><button class="btn small" type="button">Pick from a list</button><span class="later" style="background:var(--panel)"><b>Structural mutator</b></span></div>"""), cols="180px 1fr")

SEQ = list("MTSIFAESTVQKDGLPGTNIFKKALSDYLEAGVNDPAEVVKTASTWVDKLHAEAEKLLSEASRLATQKAGEL")
SEQ[63] = "D"
SIGN = {"D": ("neg", "−"), "E": ("neg", "−"), "K": ("pos", "+"), "R": ("pos", "+")}


def strip():
    cells = []
    for i, c in enumerate(SEQ):
        cls, sg = SIGN.get(c, ("", ""))
        if i == 63:
            cls, sg = "", "0"
        pressed = ' aria-pressed="true"' if i == 63 else ""
        cells.append(f'<button type="button" class="{cls}"{pressed} aria-label="{c}{i + 1}{", charge " + sg if sg else ""}"><span class="sg" aria-hidden="true">{sg}</span>{c}</button>')
    return '<div class="strip" role="group" aria-label="Chain A, placeholder sequence">' + "".join(cells) + "</div>"


QNET = '<div class="field"><span class="k">Q<sub>net</sub></span><span class="v num">xx e per frame, frame 1 of x</span></div>'
WARN = '<div class="row"><span class="warn">x PROPKA warnings</span><button class="btn small" type="button">Show</button></div>'

mo3a = frame("Protonation", f"""<div class="pane stack focus-ring" style="margin:4px;overflow:auto"><h2>Protonation · pH 7.5</h2>
  <div class="field"><label for="m3a-ph">pH</label><div class="v"><input id="m3a-ph" class="num" type="text" value="7.5"></div></div>
  <table><thead><tr><th>Type</th><th>Count</th><th>Charge, e</th><th>Off default</th></tr></thead><tbody>
  <tr aria-current="true"><td>ASP</td><td class="num">xx</td><td class="num">−1</td><td><span class="chg">1</span></td></tr>
  <tr><td>GLU</td><td class="num">xx</td><td class="num">−1</td><td class="muted">0</td></tr>
  <tr><td>HIS</td><td class="num">xx</td><td class="num">0 or +1</td><td class="muted">0</td></tr>
  <tr><td>LYS</td><td class="num">xx</td><td class="num">+1</td><td class="muted">0</td></tr>
  <tr><td>ARG</td><td class="num">xx</td><td class="num">+1</td><td class="muted">0</td></tr>
  </tbody></table>
  {QNET}{WARN}
</div>
{c3d(style="position:relative")}""")

mo3b = frame("Protonation", f"""<div style="display:grid;grid-template-rows:1fr auto;min-height:0">
{c3d(style="position:relative")}
<div class="focus-ring" style="margin:4px;padding:6px;background:var(--panel);display:grid;gap:4px;min-width:0">
  <div class="row"><b>Chain A</b><span class="chg">1 off default</span><span class="muted">selected: ASP 64, ASH, 0 · pKa x.x</span>
    <span style="margin-left:auto" class="row"><label for="m3b-ph" class="muted">pH</label><input id="m3b-ph" class="num" type="text" value="7.5" style="width:4rem"></span></div>
  {strip()}
  <div class="row muted" style="font-size:var(--text-xs)"><span>− negative</span><span>+ positive</span><span>0 changed to neutral</span><span>placeholder sequence; scroll for the rest</span><span style="margin-left:auto"></span>{QNET.replace('class="field"', 'class="row"')}{WARN}</div>
</div></div>""", cols="180px 1fr")

CHOICES = [
    ("MO1", "How the Prepare tool is driven (WB-14)", {
        "a": ("A numbered form beside the view: chains, axis, flip, membrane place", mo1a),
        "b": ("Handles on the 3D view, with a card of the same values", mo1b)}),
    ("MO2", "How a charge-level edit is made", {
        "a": ("A residue table with a state per row", mo2a),
        "b": ("Pick on the 3D view; a pop-over offers the allowed states", mo2b)}),
    ("MO3", "How the protonation is overviewed", {
        "a": ("A table by residue type, with counts off default", mo3a),
        "b": ("A sequence strip under the view, coloured and signed by charge", mo3b)}),
]
