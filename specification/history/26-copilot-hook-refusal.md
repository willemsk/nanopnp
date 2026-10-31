---
type: Ruling Record
title: "8.2.26 Copilot hook refusal, agreed 31 October 2026"
description: "Records the author's amendment to the Copilot hook refusal after a live WSL-host probe."
---

#### 8.2.26 Copilot hook refusal, agreed 31 October 2026

The REV-166 probe found that a Copilot `PreToolUse` hook exiting 2 blocked the command but reported
only `hook exited with code 2`, while an exit-0 structured denial blocked it and reported the
reason. Asked whether to amend AA5 to use the observed exit-0 denial on Copilot while retaining
exit 2 on Claude Code, the author selected “Amend the rule for Copilot”.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AB1 | **On Copilot, a hook refuses with an exit-0 structured denial; on Claude Code, it retains exit 2.** | The agent receives the reason on the probed Copilot shell path. A failure to produce the denial still exits non-zero. The other Copilot hook sources remain to be checked under REV-166. | §8.4.2, in this change; amends AA5 |
