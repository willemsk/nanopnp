# Workflow hosts

The shared contract is `.claude/workflow/core.md`. Use the host identity supplied by the session
or the application, not a single environment variable, to select one mapping:

- [Claude Code](hosts/claude-code.md)
- [GitHub Copilot app](hosts/copilot.md)

Before using a skill or steward, read the core's *Host coordination* and the selected mapping. If
the host cannot be identified, stop and ask; do not assume that another host's safety or tools
apply. A capability's status does not replace its mapping's prerequisites, evidence or failure
instructions.

| Seam | Claude Code | Copilot app |
|---|---|---|
| Questions and agents | Supported | Supported, with host-specific call shapes |
| Review | Supported | Partial: high-confidence bugs only; standards and specification are not assessed |
| CI | Supported where subscription and scheduling exist; otherwise hand off | Partial: checkpoint and hand off |
| Safety hooks | Supported by the shared configuration; live regression remains REV-168 | Partial: both probe sources observed; write-tool paths unverified (REV-166); gate manually |
| Session operations | Supported where the named tools exist | Partial: checkpoint hand-off; some app behaviour is unverified (REV-167) |
| GUI | Supported where artifact tools exist | Render and review supported; publish and collect unavailable; grill cannot complete |

If a needed capability is unavailable or unverified, use the mapping's hand-off or stop rule.
