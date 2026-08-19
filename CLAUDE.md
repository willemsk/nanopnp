# nanopnp — agent instructions

Open-source Python reimplementation of the **ePNP-NS** continuum framework for simulating
biological nanopores (Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a COMSOL
workflow. 2D-axisymmetric steady state first; structure → mesh → solve → analyse as one pipeline.

## Before doing anything

**Read `.knowledge/00-index.md`.** It indexes a local knowledge base covering the physics,
numerics, biology and tooling of this project, extracted from primary sources and numerically
verified.

**Do not search the web for the model equations, the correction functions, or their parameters.**
Several widely-copied summaries of this model are wrong. `.knowledge/01-physics-epnpns.md` is the
normative reference and documents five errata in the original sources, with the arithmetic.

Web search *is* appropriate for: current library versions and APIs (prefer the Context7 MCP for
library docs), and literature published after the knowledge base was written.

## Ground rules

- **The corrections are data, not code.** Parameters live in `data/corrections/*.yaml`. Adding an
  electrolyte should never require touching solver code.
- **Classical PNP-NS is a configuration, not a branch.** Every correction is independently
  switchable; that is what makes ablation studies and differential testing possible.
- **Deviations from the validated model go behind a flag, default off.** The published agreement
  with experiment was obtained with a specific set of terms. Anything extra — the
  dielectric-gradient body force, a mollified distance field, an added mobility correction — is
  opt-in and must be verified against COMSOL before it becomes default.
- **Assert, don't hope.** Charge conservation, packing fraction < 1, concentration positivity every
  Newton step, integration order ≥ 3 on `1/r` forms, mesh quality gates. Fail loudly with a
  location; never return a plausible wrong answer.
- **Never compute the ionic current from a cross-section integral of the CG flux.** Use the
  domain/indicator form or the variational reaction flux. See `.knowledge/06-numerics-fem.md` §7.

## When you learn something durable

Write it into the relevant `.knowledge/` file, marked **[tested]** (verified by running code) or
**[verified]** (verified by arithmetic), with its source. A fact re-derived twice should have been
written down the first time.

Keep project status, task lists and scope opinions out of `.knowledge/` — those belong in the
specification.
