"""00-guided-route: QR-10's guided run threaded through the suites, the window dimmed around the next step (GR1 B; WB-08)."""

import s_analysis
import s_continuum
import s_molecular
import s_study
from mk import CTX

STEPS = [
    ("prepare", "Load and prepare 2WCD", "2WCD is open. Estimate the pore's axis, check it on the view, and save the prepared structure. The chains and the membrane's place keep their defaults.", s_molecular.prepare, "left:calc(100% + 16px);top:-8px"),
    ("ph", "Molecular model, with the defaults", "The protonation at pH 7.5, from PROPKA, nothing changed. Build the molecular model: the ensemble, the protonation and the charges.", s_molecular.protonation, "right:0;bottom:calc(100% + 16px)"),
    ("mesh", "Continuum model, with the defaults", "The geometry and the region are built from the molecular model with their defaults. Build the mesh at the reference size, the validated one.", s_continuum.size, "left:calc(100% + 24px);top:-8px"),
    ("salt", "Set the salt", "The bulk NaCl concentration in both reservoirs, in M. There is no default: Next refuses an empty or out-of-range value here, naming the range.", s_continuum.electrolyte, "right:calc(100% + 24px);top:-8px"),
    ("bias", "Set the bias", "The voltage on the trans side, the cis side grounded. The study overrides the continuum model's default, marked with an outlined diamond. The salt stays as set.", s_study.form, "left:calc(100% + 24px);top:-8px"),
    ("run", "Pair the models in a study and run", "The study pairs the two models, assembles the charge on the mesh, then solves at each bias.", s_study.form, "left:0;top:calc(100% + 16px)"),
    ("follow", "Follow the run", {"a": "The run unfolds in the queue, wherever you are: each rung, the test that ended it and the residual. You may go on working.",
                                  "b": "The run's own page: each rung, the test that ended it and the residual. You may go on working; the queue keeps it."},
     s_study.runs, {"a": "left:0;bottom:calc(100% + 12px)", "b": "left:0;top:calc(100% + 12px)"}),
    ("conductance", "Read the conductance", "The run is done. The conductance is the current over the bias at this run; the transport number and the EOF rate beside it.", s_analysis.explorer, "right:calc(100% + 16px);top:-8px"),
]


def card(i, title, text):
    n = len(STEPS)
    back = f'<a class="btn small" href="#r-{STEPS[i - 1][0]}">Back</a>' if i else '<button class="btn small" type="button" disabled>Back</button>'
    nxt = f'<a class="btn primary small" href="#r-{STEPS[i + 1][0]}">Next</a>' if i + 1 < n else '<a class="btn primary small" href="05-results.html#a-explorer">Finish</a>'
    return f"""<span class="h">Guided run · step {i + 1} of {n}</span><b>{title}</b><span>{text}</span>
<div class="row">{back}{nxt}<a class="btn small" href="index.html">Leave the route</a></div>"""


def build_screens():
    out = []
    for i, (key, title, text, fn, style) in enumerate(STEPS):
        def make(key=key, title=title, text=text, fn=fn, style=style, i=i):
            v = CTX["v"]
            CTX.update(spot=key, coach=card(i, title, text[v] if isinstance(text, dict) else text),
                       coach_style=style[v] if isinstance(style, dict) else style)
            try:
                return fn()
            finally:
                CTX.update(spot=None, coach="", coach_style="")
        out.append((f"r-{key}", f"Guided run · {i + 1}. {title}", make))
    return out
