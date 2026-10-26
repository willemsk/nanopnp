"""Wrap choice-panel bodies into the committed pages of docs/design/choices/."""

import re
from pathlib import Path

import shapes as S

OUT = Path(__file__).resolve().parents[2] / "choices"

GRADS = """
    <linearGradient id="g-seq" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#440154"/><stop offset=".25" stop-color="#3b528b"/><stop offset=".5" stop-color="#21918c"/><stop offset=".75" stop-color="#5ec962"/><stop offset="1" stop-color="#fde725"/>
    </linearGradient>
    <linearGradient id="g-seq2" x1="0" y1="1" x2=".3" y2="0">
      <stop offset="0" stop-color="#440154"/><stop offset=".3" stop-color="#3b528b"/><stop offset=".55" stop-color="#21918c"/><stop offset=".8" stop-color="#5ec962"/><stop offset="1" stop-color="#fde725"/>
    </linearGradient>
    <radialGradient id="g-diff" cx=".35" cy=".55" r=".55">
      <stop offset="0" stop-color="#b2182b"/><stop offset=".35" stop-color="#f4a582"/><stop offset=".7" stop-color="#f7f7f7"/><stop offset="1" stop-color="#d1e5f0"/>
    </radialGradient>
    <clipPath id="disc"><path d="{arc} Z"/></clipPath>
    <symbol id="pore-rz" viewBox="0 0 180 300">{res}{mem}{prot}{axis}</symbol>
    <symbol id="protein-rz" viewBox="0 0 180 300">{prot}{axis}</symbol>
    <symbol id="pore-3d" viewBox="0 0 300 300">
      <ellipse cx="150" cy="70" rx="120" ry="36" fill="#7b8494"/>
      <path d="M30 70 Q30 120 90 150 L100 262 Q150 282 200 262 L210 150 Q270 120 270 70 Q270 106 150 106 Q30 106 30 70Z" fill="#5c6474"/>
      <path d="M70 92 Q72 125 108 150 L114 262" stroke="#9aa3b2" stroke-width="2" fill="none"/>
      <path d="M150 106 L150 276" stroke="#9aa3b2" stroke-width="2" fill="none"/>
      <path d="M230 92 Q228 125 192 150 L186 262" stroke="#9aa3b2" stroke-width="2" fill="none"/>
      <ellipse cx="150" cy="70" rx="58" ry="16" fill="#0d0f13" stroke="#9aa3b2"/>
      <circle cx="118" cy="190" r="5" fill="#ef6f6c"/><circle cx="182" cy="200" r="5" fill="#ef6f6c"/>
      <circle cx="132" cy="122" r="5" fill="#6fa8ff"/><circle cx="170" cy="230" r="5" fill="#6fa8ff"/>
    </symbol>""".format(arc=S.ARC, res=S.RESERVOIR, mem=S.MEMBRANE, prot=S.PROTEIN, axis=S.AXIS)

MESH = f"""
    <symbol id="mesh-rz" viewBox="0 0 180 300"><path d="{S.TRIS}" fill="none" stroke="currentColor" stroke-opacity=".45" stroke-width=".5"/>{S.MEMBRANE}{S.PROTEIN}{S.RESERVOIR}{S.AXIS}</symbol>"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="choices.css">
</head>
<body>
"""

UNITS = r"(?<=[\dx]) (nm|Å|nS|nA|mV|V|M|s|min|e|m³/s|m²/s)(?![\w])"


def finish(html):
    """Grid tracks that never blow out; a narrow no-break space before a unit (WB-21); minus signs."""
    html = re.sub(r"grid-template-columns:[^;\"]*", lambda m: re.sub(r"(?<![\w(,])1fr", "minmax(0,1fr)", m.group(0)), html)
    html = re.sub(UNITS, " \\1", html)
    html = html.replace("x.xx °", "x.xx°").replace(">-x", ">−x").replace(" -x.xx", " −x.xx")
    return html


def page(stem, title, choices, nxt=None, prev=None):
    """Write one page; choices is a list of (cid, question, {a: (take, body), b: (take, body)})."""
    body = []
    for i, (cid, question, variants) in enumerate(choices):
        for v in ("a", "b"):
            take, inner = variants[v]
            sid = f"{cid.lower()}-{v}"
            other = f"{cid.lower()}-{'b' if v == 'a' else 'a'}"
            if v == "a":
                nav_next = f'<a href="#{other}">Variant B</a>'
            elif i + 1 < len(choices):
                n = choices[i + 1][0]
                nav_next = f'<a href="#{n.lower()}-a">Next: {n}</a>'
            elif nxt:
                nav_next = f'<a href="{nxt[0]}">Next: {nxt[1]}</a>'
            else:
                nav_next = ""
            if v == "b":
                nav_back = f'<a href="#{other}">Variant A</a>'
            elif i > 0:
                nav_back = f'<a href="#{choices[i - 1][0].lower()}-b">Back: {choices[i - 1][0]}</a>'
            elif prev:
                nav_back = f'<a href="{prev[0]}">Back: {prev[1]}</a>'
            else:
                nav_back = ""
            body.append(f"""
<section data-screen="{sid}" id="{sid}" aria-labelledby="{sid}-h">
  <header class="cap"><span class="cid">{cid}</span><h1 id="{sid}-h">{question}</h1><span class="take">{take}</span><span class="var" role="img" aria-label="Variant {v.upper()}">{v.upper()}</span></header>
  <div class="stage">
{inner.strip()}
  </div>
  <nav class="foot" aria-label="Choices">{nav_back}<a href="index.html">All choices</a><span class="sp"></span>{nav_next}</nav>
</section>
""")
    text = "".join(body)
    defs = GRADS + (MESH if "#mesh-rz" in text else "")
    html = HEAD.format(title=title) + f'<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>{defs}\n</defs></svg>' + text + "</body>\n</html>\n"
    (OUT / f"{stem}.html").write_text(finish(html))
    return [(cid, q, {v: t for v, (t, _) in vs.items()}) for cid, q, vs in choices]
