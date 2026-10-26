"""Shared fragments of the choice panels: the project tree, tool lists, the queue, canvases."""

import shapes as S

PROJECT = """<ul class="tree" aria-label="Project">
  <li><span class="grp">Library</span>
    <ul>
      <li><span class="muted">Molecular models</span>
        <ul><li><button type="button" aria-current="{m}">2WCD, pH 7.5 <span class="ok">built</span></button></li>
            <li><button type="button">2WCD, ASP 64 neutral <span class="muted">charge variant</span></button></li></ul></li>
      <li><span class="muted">Continuum models</span>
        <ul><li><button type="button" aria-current="{c}">ClyA pore, reference mesh <span class="ok">built</span></button></li></ul></li>
    </ul></li>
  <li><span class="grp">Studies</span>
    <ul><li><button type="button" aria-current="{s}">I–V, NaCl <span class="warn">running</span></button></li></ul></li>
  <li><span class="grp">Comparisons</span>
    <ul><li><button type="button">Parent and ASP 64 neutral</button></li></ul></li>
</ul>"""


def project(sel="m"):
    """The project browser, with one item selected."""
    return PROJECT.format(m="true" if sel == "m" else "false", c="true" if sel == "c" else "false",
                          s="true" if sel == "s" else "false")


TOOLS = {
    "molecular": [("Prepare structure", "ok", "built"), ("Ensemble", "ok", "built"), ("Protonation", "ok", "built"),
                  ("Charge edit", "", ""), ("View", "", "")],
    "continuum": [("Protein geometry", "ok", "built"), ("Region", "ok", "built"), ("Mesh", "warn", "stale"),
                  ("Physics defaults", "", "")],
    "analysis": [("Study", "warn", "running"), ("Results explorer", "", ""), ("Comparison", "", ""),
                 ("Probes and cuts", "", "")],
}


def tools(suite, current, fresh=False):
    """A suite's tool list with the current tool marked; fresh shows every Continuum tool built."""
    rows = []
    for name, cls, word in TOOLS[suite]:
        if fresh and cls == "warn" and suite == "continuum":
            cls, word = "ok", "built"
        cur = ' aria-current="true"' if name == current else ""
        st = f'<span class="st {cls}">{word}</span>' if word else ""
        rows.append(f'<li><button type="button"{cur}>{name}{st}</button></li>')
    return '<ul class="tools" aria-label="Tools">' + "".join(rows) + "</ul>"


QROWS = """<div class="qrow"><span class="ok" aria-hidden="true"></span><span>Continuum model · ClyA pore, reference mesh</span><span class="ok">built</span><span class="muted num">x.x s</span></div>
<div class="qrow"><span class="warn" aria-hidden="true"></span><span>Study · I–V, NaCl · bias x.xx V, rung 7 of N</span><span class="warn">running</span><button class="btn small" type="button">Cancel</button></div>
<div class="qrow"><span class="muted" aria-hidden="true">…</span><span>Molecular model · 2WCD, ASP 64 neutral</span><span class="muted">queued</span><button class="btn small" type="button">Remove</button></div>"""


def queue(expanded=False):
    """The run queue strip, always on screen (WB-03)."""
    if not expanded:
        return """<div class="queue"><div class="qrow" style="grid-template-columns:auto 1fr auto auto"><b>Queue</b><span class="muted">1 running · 1 queued · 1 built</span><span class="warn">I–V, NaCl: rung 7 of N</span><button class="btn small" type="button" aria-expanded="false">Show queue</button></div></div>"""
    return f'<div class="queue">{QROWS}</div>'


def _vb(ratio, svg, extra):
    return f'<div class="vb" style="aspect-ratio:{ratio}">{svg}{extra}</div>'


def c3d(extra="", style="", over=""):
    """The Molecular suite's 3D view, on near-black (WB-26); extra is placed in the view's own square."""
    svg = f'<svg viewBox="0 0 300 300" width="100%" height="100%"><use href="#pore-3d"/>{over}</svg>'
    return f'<div class="c3d" style="{style}" role="img" aria-label="3D view of the pore">{_vb("1 / 1", svg, extra)}</div>'


def crz(extra="", style="", sym="pore-rz", over=""):
    """A Continuum (r, z) view, on the theme's canvas (WB-26); not to scale."""
    svg = f'<svg viewBox="0 0 180 300" width="100%" height="100%" style="color:var(--canvas-plot-ink)"><use href="#{sym}"/>{over}</svg>'
    return f'<div class="cplot" style="{style}" role="img" aria-label="(r, z) view, not to scale">{_vb("180 / 300", svg, extra)}</div>'


def field(style="", grad="g-seq", extra="", membrane=True, corner=""):
    """A field map in (r, z), viridis by default (WB-20), inside the half-disc reservoir."""
    mem = f'<polygon points="{S.pts(S.MEM)}" fill="#c9ced8" stroke="#16181d"/>' if membrane else ""
    svg = f"""<svg viewBox="0 0 180 300" width="100%" height="100%" style="color:var(--canvas-plot-ink)">
<rect x="20" y="10" width="140" height="280" fill="url(#{grad})" clip-path="url(#disc)"/>
<polygon points="{S.pts(S.PROT)}" fill="#9aa3b2" stroke="#16181d"/>{mem}{S.RESERVOIR}{S.AXIS}</svg>"""
    c = f'<div class="corner">{corner}</div>' if corner else ""
    return f'<div class="cplot" style="{style}" role="img" aria-label="Field map in (r, z)">{_vb("180 / 300", svg, extra)}{c}</div>'


def cbar(label, kind="seq", ticks=("x.xx", "x.xx")):
    """An outlined colour bar with its quantity, unit and end values (WB-26)."""
    t = "".join(f"<span>{x}</span>" for x in ticks)
    return f'<div class="cbox"><span class="cl">{label}</span><div class="cbar {kind}"></div><div class="row num cl" style="justify-content:space-between">{t}</div></div>'


def titlebar(inner, project_name="ClyA study"):
    """The frame's title bar: project, then what the variant puts there, the changed count and the palette."""
    return f"""<div class="titlebar"><span class="proj">{project_name}</span>{inner}<span class="sp"></span>
<button class="chip" type="button" aria-label="x values changed from their defaults: show the list"><span class="chg">x changed</span></button>
<button class="btn small" type="button">Commands <span class="muted num">Ctrl K</span></button></div>"""


def badge(n, what="problem"):
    return f'<span class="badge"><span aria-hidden="true">{n}</span><span class="vh">{n} {what}{"s" if n != 1 else ""}</span></span>'


def suite_tabs(current="Molecular", focus=False, badges=None):
    """The suites as tabs (FR1 A)."""
    badges = badges or {}
    out = []
    for s in ("Molecular", "Continuum", "Analysis"):
        sel = "true" if s == current else "false"
        b = " " + badge(badges[s]) if s in badges else ""
        out.append(f'<button type="button" role="tab" aria-selected="{sel}">{s}{b}</button>')
    ring = " focus-ring" if focus else ""
    return f'<div class="tabs{ring}" role="tablist" aria-label="Suites">{"".join(out)}</div>'


def reset(what):
    """The per-field reset beside a changed mark (WB-28)."""
    return f'<button class="btn small" type="button" aria-label="Reset {what} to its default">Reset</button>'
