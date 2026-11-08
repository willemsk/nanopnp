# Workflow hosts

The skills name Claude Code's tools; Claude Code needs no map. Another host reads its map first:

- GitHub Copilot app: [hosts/copilot.md](hosts/copilot.md)

Antigravity has no map. `.agents/` is a legacy adapter kept for it. `.agents/hooks.json` wires its
hooks through the `antigravity` dialect of `.agents/hooks/adapter.sh`, the adapter's default, and
`.agents/skills.json` points it at `.claude/skills`. It has not been verified live.

A new host adds one map here and, for its hooks, a dialect in `.agents/hooks/adapter.sh`.
A tool its map does not cover: stop and hand off to Claude Code.
