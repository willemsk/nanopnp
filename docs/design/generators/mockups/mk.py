"""The frame of the whole-workbench mockups: title bar, activity bar, project rail, tool list, bottom panel (WB-01 to WB-03, WB-29; FR1 to FR6)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "choices"))

import shapes as S  # noqa: E402
from parts import badge, cbar, reset  # noqa: E402,F401

CTX = {"v": "a", "spot": None, "coach": "", "coach_style": ""}

# The guided route starts from a clean project: a tool shows a status only once its step is done (GR1 B; WB-08).
_MOL = {"Prepare structure", "Ensemble", "Protonation"}
_CON = {"Protein geometry", "Contour", "Region"}
DONE = {"prepare": set(), "ph": {"Prepare structure"}, "mesh": _MOL | _CON, "salt": _MOL | _CON | {"Mesh"},
        "bias": _MOL | _CON | {"Mesh", "Physics defaults"}, "run": _MOL | _CON | {"Mesh", "Physics defaults"},
        "follow": _MOL | _CON | {"Mesh", "Physics defaults"}, "conductance": _MOL | _CON | {"Mesh", "Physics defaults", "Study setup", "Runs"}}


def route():
    """The route step being drawn, or None."""
    return CTX["spot"]

SUITES = [("molecular", "Molecular", "⬡", "01-molecular.html"), ("continuum", "Continuum", "△", "02-geometry.html"),
          ("study", "Study", "⧉", "06-study.html"), ("analysis", "Analysis", "∿", "05-results.html")]

# Each suite's tools: (name, page#screen, status class, status word, problem count).
TOOLS = {
    "molecular": [("Prepare structure", "01-molecular.html#m-prepare", "ok", "saved", 0),
                  ("Ensemble", "01-molecular.html#m-ensemble", "ok", "built", 0),
                  ("Protonation", "01-molecular.html#m-protonation", "ok", "built", 0),
                  ("Charge edit", "01-molecular.html#m-charge", "", "", 0),
                  ("View", "01-molecular.html#m-view", "", "", 0)],
    "continuum": [("Protein geometry", "02-geometry.html#g-geometry", "ok", "gate passed", 0),
                  ("Contour", "02-geometry.html#g-contour", "ok", "gate passed", 0),
                  ("Region", "02-geometry.html#g-region", "ok", "built", 0),
                  ("Mesh", "03-mesh.html#s-size", "ok", "gate passed", 0),
                  ("Physics defaults", "04-physics.html#p-boundaries", "", "", 0)],
    "study": [("Overview", "06-study.html#st-overview", "", "", 0),
              ("Study setup", "06-study.html#st-form", "warn", "running", 0),
              ("Sweep", "06-study.html#st-sweep", "", "", 0),
              ("Charge on the mesh", "06-study.html#st-charge", "ok", "passed", 0),
              ("Runs", "06-study.html#st-runs", "warn", "1 running", 0)],
    "analysis": [("Results explorer", "05-results.html#a-explorer", "", "", 0),
                 ("Comparison", "05-results.html#a-compare-side", "", "", 0)],
}


def here(link, page):
    """A link relative to the page it is drawn on: same-page targets keep only their hash."""
    p, _, h = link.partition("#")
    return f"#{h}" if p == page and h else link


def titlebar(page, changed_open=False):
    """The title bar: the application, its menus, the project, the changed count and the palette."""
    menus = "".join(f'<button type="button" aria-haspopup="menu">{m}</button>' for m in ("File", "Edit", "View", "Run", "Help"))
    target = "06-study.html#st-changes"
    exp = "true" if changed_open else "false"
    n = 0 if route() else 2
    chip = (f'<a class="chip" href="{here(target, page)}" aria-expanded="{exp}" aria-label="{n} values changed from their defaults and 2 study overrides: show the list"><span class="chg">{n} changed</span> <span class="ovr">2</span></a>'
            if n else '<span class="chip" aria-label="No value changed from its default">0 changed</span>')
    return f"""<header class="titlebar"><span class="app">nanopnp</span><nav class="menus" aria-label="Menus">{menus}</nav>
<span class="muted" aria-hidden="true">·</span><span class="proj">ClyA study</span><span class="sp"></span>
{chip}
<button class="btn small" type="button">Commands <span class="muted num">Ctrl K</span></button></header>"""


def activity(current, page, problems=None):
    out = []
    for key, name, ico, link in SUITES:
        cur = ' aria-current="page"' if key == current else ""
        n = (problems or {}).get(key, 0)
        b = badge(n) if n else ""
        out.append(f'<a href="{here(link, page)}"{cur}><span class="ico" aria-hidden="true">{ico}</span>{name}{b}</a>')
    return f'<nav class="activity" aria-label="Suites">{"".join(out)}</nav>'


def rail(page, item):
    """The project rail: the open item and the groups, unfolding into the tree (FR3 B)."""
    return f"""<nav class="rail" aria-label="Project">
  <span class="grp">Open</span>
  <ul class="tools"><li><a href="#" aria-current="true">{item}</a></li></ul>
  <span class="grp">Project</span>
  <ul class="tools">
    <li><a href="{here('06-study.html#st-tree', page)}" aria-expanded="false">Library <span class="st muted">3</span></a></li>
    <li><a href="{here('06-study.html#st-tree', page)}" aria-expanded="false">Studies <span class="st muted">2</span></a></li>
    <li><a href="{here('06-study.html#st-tree', page)}" aria-expanded="false">Comparisons <span class="st muted">1</span></a></li>
  </ul>
  <a class="btn small" href="{here('06-study.html#st-tree', page)}" aria-keyshortcuts="Control+Shift+E" title="Ctrl Shift E" style="justify-self:start;margin:6px 4px">Unfold the tree</a>
</nav>"""


def tools(suite, current, page, fail=None):
    rows = []
    for name, link, cls, word, n in TOOLS[suite]:
        if name == "Runs" and CTX["v"] == "a":
            continue
        if name == "Study setup" and CTX["v"] == "b":
            link = "06-study.html#st-graph"
        if name == "Comparison" and CTX["v"] == "b":
            link = "05-results.html#a-compare-diff"
        if route():
            done = name in DONE[route()]
            if name == "Study setup" and route() == "follow":
                cls, word = "warn", "running"
            elif name == "Runs" and route() == "follow":
                cls, word = "warn", "1 running"
            elif done:
                cls, word = "ok", {"Prepare structure": "saved", "Physics defaults": "set", "Study setup": "done", "Runs": "done"}.get(name, "built")
            else:
                cls, word = "", ""
        if fail and name == fail[0]:
            cls, word, n = "err", fail[1], 1
        cur = ' aria-current="true"' if name == current else ""
        st = f'<span class="st {cls}">{word}</span>' if word else ""
        b = " " + badge(n) if n else ""
        rows.append(f'<li><a href="{here(link, page)}"{cur}>{name}{b}{st}</a></li>')
    title = dict((k, n) for k, n, _, _ in SUITES)[suite]
    return f'<div class="pane"><h2>{title} tools</h2><ul class="tools" aria-label="{title} tools">{"".join(rows)}</ul></div>'


QROWS = """<div class="qrow"><span class="ok" aria-hidden="true"></span><span>Continuum model · ClyA pore, reference mesh</span><span class="ok">built</span><span class="muted num">x.x s</span></div>
<div class="qrow"><span class="warn" aria-hidden="true"></span><span>Study · I–V, NaCl · bias x.xx V, x of n · rung 7 of N</span><span class="warn">running</span><button class="btn small" type="button">Cancel</button></div>
<div class="qrow"><span class="muted" aria-hidden="true">…</span><span>Molecular model · 2WCD, ASP 64 neutral</span><span class="muted">queued</span><button class="btn small" type="button">Remove</button></div>"""


def panel(state="folded", run_detail=""):
    """The bottom panel (FR2 A): queue and log, the console a later phase; folded to one line by default."""
    if state == "folded" and route():
        word = {"follow": '<span class="warn">I–V, NaCl: rung x of N</span>', "conductance": '<span class="ok">I–V, NaCl: done</span>'}.get(route(), '<span class="muted">empty</span>')
        return f"""<div class="panel"><div class="qrow" style="grid-template-columns:auto 1fr auto"><b>Queue</b>{word}<button class="btn small" type="button" aria-expanded="false">Show queue</button></div></div>"""
    if state == "folded":
        return """<div class="panel"><div class="qrow" style="grid-template-columns:auto 1fr auto auto"><b>Queue</b><span class="muted">1 running · 1 queued · 1 built</span><span class="warn">I–V, NaCl: rung 7 of N</span><button class="btn small" type="button" aria-expanded="false">Show queue</button></div></div>"""
    tabs = '<div class="tabs" role="tablist" aria-label="Bottom panel"><button type="button" role="tab" aria-selected="true">Queue 3</button><button type="button" role="tab" aria-selected="false">Log</button></div>'
    return f"""<div class="panel"><div class="ptabs">{tabs}<span class="later"><b>Console</b></span><span style="margin-left:auto"></span><button class="btn small" type="button" aria-expanded="true">Fold</button></div>
<div class="queue">{run_detail or QROWS}</div></div>"""


def mockbar(v, page, sid, title, idx, n, prev, nxt):
    other = "b" if v == "a" else "a"
    p = f'<a href="{prev[0]}">Back: {prev[1]}</a>' if prev else ""
    x = f'<a href="{nxt[0]}">Next: {nxt[1]}</a>' if nxt else ""
    return f"""<nav class="mock" aria-label="Mockup"><span class="tag" role="img" aria-label="Mockup {v.upper()}">{v.upper()}</span><span><b>{title}</b> <span class="muted">· screen {idx} of {n}</span></span>
<span class="sp"></span>{p}<a href="index.html">All screens</a><a href="../{other}/{page}#{sid}">Same screen in {other.upper()}</a>{x}</nav>"""


def spot(key, html, inline=False):
    """The guided route lifts one part of a screen above the dimmed window, with its card beside it (GR1 B)."""
    if CTX["spot"] != key:
        return html
    tag = "span" if inline else "div"
    return f'<{tag} class="spot" style="display:{"inline-block" if inline else "block"}">{html}<div class="coach" role="dialog" aria-modal="true" aria-label="Guided run" style="{CTX["coach_style"]}">{CTX["coach"]}</div></{tag}>'


def window(page, suite, tool, body, cols, item="ClyA study", panel_state="folded", run_detail="", overlay="",
           changed_open=False, fail=None, rail_html=None, tools_html=None, problems=None, rail_w="184px"):
    """One screen's workbench: activity bar, rail, tool list, then the body's columns, then the bottom panel."""
    routed = CTX["spot"] is not None
    inert = " inert" if routed else ""
    t = tools_html if tools_html is not None else tools(suite, tool, page, fail)
    r = rail_html if rail_html is not None else rail(page, item)
    dim = '<div class="dim" aria-hidden="true"></div>' if routed else ""
    return f"""<div{inert}>{titlebar(page, changed_open)}</div>
<div class="main" style="grid-template-columns:72px {rail_w} 184px {cols}">
<div{inert} style="display:grid;min-height:0">{activity(suite, page, problems)}</div>
<div{inert} style="display:grid;min-height:0">{r}</div>
<div{inert} style="display:grid;min-height:0">{t}</div>
{body}
</div>
<div{"" if route() == "follow" else inert}>{panel(panel_state, run_detail)}</div>
{overlay}{dim}"""


def f(fid, label, value, unit="", mark="", width=""):
    u = f'<span class="unit">{unit}</span>' if unit else ""
    w = f' style="width:{width}"' if width else ""
    return f'<div class="field"><label for="{fid}">{label}</label><div class="v"><input id="{fid}" class="num" type="text" value="{value}"{w}>{u}{mark}</div></div>'


def ro(label, value):
    return f'<div class="field"><span class="k">{label}</span><span class="v">{value}</span></div>'


def pct(x, y):
    return f"left:{x / 180 * 100:.1f}%;top:{y / 300 * 100:.1f}%"


def view3d(over="", inside="", cards="", label="3D view of the pore", style=""):
    """Molecular's 3D view, always near-black (WB-26); cards sit on the view, inside sits in the drawing's own square."""
    svg = f'<svg viewBox="0 0 300 300" width="100%" height="100%"><use href="#pore-3d"/>{over}</svg>'
    return f'<div class="c3d" style="position:relative;{style}" role="img" aria-label="{label}"><div class="vb" style="aspect-ratio:1 / 1">{svg}{inside}</div>{cards}</div>'


def viewrz(over="", inside="", cards="", sym="pore-rz", label="(r, z) view, not to scale", style="", raw=None):
    """A Continuum (r, z) view on the theme's canvas (WB-26)."""
    content = raw if raw is not None else f'<use href="#{sym}"/>'
    svg = f'<svg viewBox="0 0 180 300" width="100%" height="100%" style="color:var(--canvas-plot-ink)">{content}{over}</svg>'
    return f'<div class="cplot" style="position:relative;{style}" role="img" aria-label="{label}"><div class="vb" style="aspect-ratio:180 / 300">{svg}{inside}</div>{cards}</div>'


def fieldmap(grad="g-seq", membrane=True, over="", inside="", cards="", style="", label="Field map in (r, z)"):
    mem = f'<polygon points="{S.pts(S.MEM)}" fill="#c9ced8" stroke="#16181d"/>' if membrane else ""
    raw = (f'<rect x="20" y="10" width="140" height="280" fill="url(#{grad})" clip-path="url(#disc)"/>'
           f'<polygon points="{S.pts(S.PROT)}" fill="#9aa3b2" stroke="#16181d"/>{mem}{S.RESERVOIR}{S.AXIS}')
    note = '<div class="over cl" style="left:6px;bottom:4px;background:var(--canvas-plot);padding:0 3px">Schematic</div>'
    return viewrz(over=over, inside=inside, cards=cards + note, raw=raw, label=label, style=style)


NOT_TO_SCALE = '<div class="over cl" style="left:8px;bottom:6px">Not to scale: the reservoir is about a hundred times the pore.</div>'
