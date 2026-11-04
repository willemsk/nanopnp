---
type: Ruling Record
title: "8.2.32 WP5.06's plan: what an output needs of a model, agreed 4 November 2026"
description: "Records the author's ruling at WP5.06's plan: a registered output states what it needs of a model's declaration, a model provides every output whose need its declaration meets, and the declaration's own list of quantities goes, so one registration reaches every capable model."
---

#### 8.2.32 WP5.06's plan: what an output needs of a model, agreed 4 November 2026

Ruling by the author on 4 November 2026, at `/np-plan wp 5.06`, after WP5.05's merge. MOD-09 brings the outputs into a
registry (§8.2.18 T4), so a new quantity of interest needs no edit of the case schema. The survey found a second
closed list behind it: §5.4.3's declaration names the quantities each model provides, so a quantity registered from
outside the package could still not be asked of a shipped model without editing that model. One question was put
through `AskUserQuestion` with three options: the output states its need, the model's list stays the only authority,
or both. The author took the recommendation. The letter series continues at AH.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AH1 | **An output states what it needs of a model, and a model provides every output whose need its declaration meets.** The needs are read from the declaration, never from a model's name (VER-56): *transport*, that the model solves ionic transport, and *flow*, that it honours `physics.flow: true`. `current`, `transport_numbers` and `rectification` need transport; `eof_rate` and `analyte_force` need transport and flow; `fields` needs nothing. The declaration's list of quantities goes | The shipped models provide exactly what they declared before: `epnp-ns` and `pnp-ns` the six words, `pnp` four, the electrostatic models `fields` alone. A quantity registered from outside the package reaches every model that meets its need, and no model's code is edited for it. A model cannot decline an output its declaration meets | §5.4.3's NOTE on what a model declares, §5.3.1's NOTE on `outputs:` and VER-56, in this commit; the registry itself, §5.5: open: WP5.06 |
