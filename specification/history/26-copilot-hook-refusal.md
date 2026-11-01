---
type: Ruling Record
title: "8.2.26 The hook refusal, agreed 1 November 2026"
description: "Records the author's ruling that a hook refuses with an exit-0 structured denial on both hosts, replacing the exit-code switch on a host variable."
---

#### 8.2.26 The hook refusal, agreed 1 November 2026

The REV-166 probe found that Copilot shows a hook's reason only for an exit-0 structured denial, and that Claude Code 2.1.314 blocked the same denial, carrying the deny top-level and as `hookSpecificOutput`, with its reason. Keying the exit code on `COPILOT_CLI` failed when a Claude Code session inherited the variable. The author re-ruled AB1 on 1 November 2026.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AB1 | **On both hosts a hook refuses with an exit-0 structured denial carrying the deny top-level and as `hookSpecificOutput`; it exits 2 only if it cannot print it.** | No host variable selects the protocol. | §8.4.2, in this change; amends AA5 |
