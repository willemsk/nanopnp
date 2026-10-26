"""01-molecular: Prepare (MO1 B), Ensemble and View (E7), Protonation (MO3 B), Charge edit (MO2 B)."""

from mk import cbar, f, reset, ro, route, spot, view3d, window

PAGE = "01-molecular.html"

AXIS = ('<line x1="150" y1="14" x2="150" y2="292" style="stroke:var(--accent)" stroke-width="2" stroke-dasharray="6 4"/>'
        '<rect x="40" y="214" width="220" height="26" fill="none" style="stroke:var(--warn)" stroke-width="2"/>')
HANDLES = ('<circle cx="150" cy="18" r="7" style="fill:var(--accent)"/><path d="M143 30 L150 18 L157 30" fill="none" style="stroke:var(--canvas-3d-ink)" stroke-width="2"/>'
           '<rect x="252" y="221" width="14" height="12" rx="2" style="fill:var(--warn)"/><rect x="34" y="221" width="14" height="12" rx="2" style="fill:var(--warn)"/>')
PICK = '<circle cx="118" cy="190" r="10" fill="none" style="stroke:var(--accent)" stroke-width="3"/>'
LEGEND = '<div class="over card" style="right:8px;bottom:8px;padding:6px 8px;gap:2px;font-size:var(--text-xs)"><span><span style="display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;color:#0d0f13;font-weight:700;margin-right:4px;background:#ef6f6c" aria-hidden="true">−</span>negative residue</span><span><span style="display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;color:#0d0f13;font-weight:700;margin-right:4px;background:#6fa8ff" aria-hidden="true">+</span>positive residue</span></div>'
VIEWBAR = LEGEND + """<div class="over toolbar" style="left:8px;top:8px">
  <button class="btn small" type="button">Reset view</button><button class="btn small" type="button" aria-pressed="false">Clip</button>
  <span class="chip" style="background:var(--panel)">Linked: residue and charge map</span></div>"""


def prepare():
    card = f"""<div class="over card" style="left:12px;top:52px;width:300px">
  <b>Prepare</b>
  <div class="row"><span class="muted">Structure</span><span class="num">2wcd.cif</span><button class="btn small" type="button">Open structure…</button></div>
  <div class="row"><span class="muted">Chains</span><button class="chip" type="button" aria-pressed="true">A–L, 12</button></div>
  {spot("prepare", '<div class="row"><label for="mp-tl" class="muted">Axis tilt</label><input id="mp-tl" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">°</span><button class="btn small" type="button">Estimate</button></div>')}
  <div class="row"><label for="mp-z" class="muted">Membrane centre, z</label><input id="mp-z" class="num" type="text" value="x.xx" style="width:4rem"><span class="unit">nm</span></div>
  <div class="row"><span class="muted">Thickness</span><span class="num">x.xx nm</span><span class="muted">set in Continuum, Region</span></div>
  <div class="row"><button class="btn small" type="button">Flip</button><button class="btn primary small" type="button">Save prepared structure</button></div>
  <div class="verdict"><span class="ok">Orientation gate passed</span><button class="btn small" type="button" aria-expanded="false">Checks</button></div>
  <span class="muted" style="font-size:var(--text-xs)">Drag the axis by its top handle, the membrane by its ends; or type the values.</span>
</div>"""
    body = f'<div class="viewwrap">{view3d(over=AXIS + HANDLES, cards=VIEWBAR + card)}</div>'
    return window(PAGE, "molecular", "Prepare structure", body, "minmax(0,1fr)", item="2WCD, pH 7.5")


FRAMES = [(1, "xx", "x.xx"), (2, "xx", "x.xx"), (3, "xx", "x.xx"), (4, "xx", "x.xx")]


def ensemble():
    rows = "".join(f'<tr{" aria-current=\"true\"" if i == 1 else ""}><td class="num">{n}</td><td class="num">{q} e</td><td class="num">{r} ns</td><td><label class="row"><input type="checkbox" checked><span class="vh">Use frame {n}</span></label></td></tr>' for i, (n, q, r) in enumerate(FRAMES))
    body = f"""<div class="settings"><h2>Ensemble · 2WCD</h2>
  <div class="field"><label for="me-src">Source</label><div class="v"><select id="me-src"><option>Trajectory, x frames</option><option>The structure alone</option></select></div></div>
  {f("me-st", "Stride", "x")}
  <h3>Frames</h3>
  <table><thead><tr><th>Frame</th><th>Q<sub>net</sub></th><th>Time</th><th>Use</th></tr></thead><tbody>{rows}</tbody></table>
  <span class="muted">Q<sub>net</sub> is an integer per frame. The density is averaged over the frames used.</span>
  <div class="row"><button class="btn primary" type="button">Build ensemble</button><span class="ok">built</span></div>
</div>
<div class="viewwrap" style="grid-template-rows:minmax(0,1fr) auto">{view3d(over='<g opacity=".35"><use href="#pore-3d" transform="translate(4 2)"/></g>', cards=VIEWBAR)}
  <div class="row"><label for="me-fr" class="muted">Frame</label><input id="me-fr" type="range" min="1" max="4" value="2"><span class="num">2 of x</span><label class="row"><input type="checkbox"> Overlay the frames</label></div></div>"""
    return window(PAGE, "molecular", "Ensemble", body, "320px minmax(0,1fr)", item="2WCD, pH 7.5")


SEQ = list("MTSIFAESTVQKDGLPGTNIFKKALSDYLEAGVNDPAEVVKTASTWVDKLHAEAEKLLSEASRLATQKAGELMTSIFAESTVQKDGLPGTNIFKKAL")
SEQ[63] = "D"
SIGN = {"D": ("neg", "−"), "E": ("neg", "−"), "K": ("pos", "+"), "R": ("pos", "+")}


def strip():
    cells = []
    for i, c in enumerate(SEQ):
        cls, sg = SIGN.get(c, ("", ""))
        if i == 63 and not route():
            cls, sg = "", "0"
        pressed = ' aria-pressed="true"' if i == 63 else ""
        cells.append(f'<button type="button" class="{cls}"{pressed} aria-label="{c}{i + 1}{", charge " + sg if sg else ""}"><span class="sg" aria-hidden="true">{sg}</span>{c}</button>')
    return '<div class="strip" role="group" aria-label="Chain A, placeholder sequence">' + "".join(cells) + "</div>"


QNET = '<span class="row"><span class="muted">Q<sub>net</sub></span><span class="num">xx e per frame, frame 1 of x</span></span>'
WARN = '<span class="row"><span class="warn">x PROPKA warnings</span><button class="btn small" type="button">Show</button></span>'


def protonation():
    state = ('<span class="muted">0 off default · at pH 7.5, from PROPKA</span>' if route() else
             '<span class="chg">1 off default</span><span class="muted">selected: ASP 64, ASH, 0 · pKa x.x</span>')
    ph = spot("ph", '<span class="row"><label for="mo-ph" class="muted">pH</label><input id="mo-ph" class="num" type="text" value="7.5" style="width:4rem"><button class="btn primary small" type="button">Build molecular model</button></span>', inline=True)
    body = f"""<div class="viewwrap" style="grid-template-rows:minmax(0,1fr) auto">{view3d(over=PICK, cards=VIEWBAR)}
<div class="card" style="min-width:0">
  <div class="row"><b>Protonation · chain A</b>{state}<span style="margin-left:auto"></span>{ph}</div>
  {strip()}
  <div class="row muted" style="font-size:var(--text-xs)"><span>− negative</span><span>+ positive</span><span>0 changed to neutral</span><span>placeholder sequence; scroll for the rest</span><span style="margin-left:auto"></span>{QNET}{WARN}</div>
</div></div>"""
    return window(PAGE, "molecular", "Protonation", body, "minmax(0,1fr)", item="2WCD, pH 7.5" if route() else "2WCD, ASP 64 neutral")


def charge():
    pop = f"""<div class="over card" role="dialog" aria-label="ASP 64" style="left:56%;top:46%;width:290px">
  <b>ASP 64 · on all 12 chains</b><span class="muted">pKa x.x · default at pH 7.5: ASP, −1</span>
  <fieldset style="border:0;padding:0;margin:0;display:grid;gap:4px"><legend class="h">Protonation state</legend>
    <label class="row"><input type="radio" name="mc-s"> ASP, −1 (default)</label>
    <label class="row"><input type="radio" name="mc-s" checked> ASH, 0 <span class="chg">changed</span></label></fieldset>
  <div class="row"><button class="btn primary small" type="button">Save as variant…</button>{reset("ASP 64 state")}</div>
  <span class="muted" style="font-size:var(--text-xs)">Saved as a charge variant of 2WCD, pH 7.5, shown as its difference from the parent. The state applies to the residue on every chain: the model is C12-averaged.</span>
  <div class="row"><span class="muted">Then</span><a class="btn small" href="06-study.html#st-sweep">Run beside the parent…</a><a class="btn small" href="05-results.html#a-compare-side">Compare with the parent…</a></div>
</div>
<div class="over toolbar" style="left:8px;bottom:8px"><button class="btn small" type="button" style="background:var(--panel)">Pick from a list</button><span class="later" style="background:var(--panel)"><b>Structural mutator</b>: replacing a side chain</span></div>"""
    body = f'<div class="viewwrap">{view3d(over=PICK, cards=VIEWBAR + pop)}</div>'
    return window(PAGE, "molecular", "Charge edit", body, "minmax(0,1fr)", item="2WCD, pH 7.5")


def view():
    body = f"""<div class="settings"><h2>View</h2>
  <div class="field"><label for="mv-r">Representation</label><div class="v"><select id="mv-r"><option>Surface</option><option>Cartoon</option><option>Atoms</option></select></div></div>
  <div class="field"><label for="mv-c">Colour by</label><div class="v"><select id="mv-c"><option>Charge</option><option>Chain</option><option>Changed from default</option></select></div></div>
  <label class="row"><input type="checkbox" checked> Show the membrane slab</label>
  <label class="row"><input type="checkbox"> Clip at the axis</label>
  <h3>Select</h3>
  <div class="row"><label for="mv-s" class="muted">Find</label><input id="mv-s" type="text" placeholder="residue or number" style="width:10rem"></div>
  <table><thead><tr><th>Residue</th><th>Chains</th><th>Charge, e</th></tr></thead><tbody>
  <tr aria-current="true"><td>ASP 64</td><td>A–L</td><td class="num">0 <span class="chg">changed</span></td></tr>
  <tr><td>ASP xx</td><td>A–L</td><td class="num">−1</td></tr><tr><td>LYS xx</td><td>A–L</td><td class="num">+1</td></tr></tbody></table>
  <span class="muted">A residue picked here or on the view selects its charge in Study's charge map until unlinked.</span>
</div>
<div class="viewwrap">{view3d(over=PICK, cards=VIEWBAR + '<div class="over" style="right:8px;top:8px">' + cbar("Charge, e", kind="div", ticks=("−1", "0", "+1")) + '</div>')}</div>"""
    return window(PAGE, "molecular", "View", body, "320px minmax(0,1fr)", item="2WCD, ASP 64 neutral")


SCREENS = [("m-prepare", "Molecular · Prepare structure", prepare), ("m-ensemble", "Molecular · Ensemble", ensemble),
           ("m-protonation", "Molecular · Protonation", protonation), ("m-charge", "Molecular · Charge edit", charge),
           ("m-view", "Molecular · View", view)]
