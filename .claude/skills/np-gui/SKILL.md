---
name: np-gui
description: Render, review and publish GUI screens and mockups for the author's verdicts, collect them, or run a design round with the author. Use when a change touches a screen, a mockup or the workbench design, or on /np-gui.
argument-hint: <render | review | publish | collect | grill> [target|topic|url]
---

# GUI: `$ARGUMENTS`

1. The first argument is the level, the second its target, topic or URL. A missing or unknown level:
   print `Usage: /np-gui <render | review | publish | collect | grill> [target|topic|url]` and stop.
2. Read the level's file beside this one: `${CLAUDE_SKILL_DIR}/<level>.md`, one of `render.md`,
   `review.md`, `publish.md`, `collect.md` and `grill.md`.
3. Follow the level's file. `<s>` is the session's scratchpad; `<r>` a render directory
   `<s>/gui-render/<target>-<short sha>/`. The design document is `docs/design/workbench.md`
   (§8.2.17 S21, S22).
4. Before you build or change a screen, read the craft floor of the `impeccable:impeccable` skill, where
   the host has it; skip it otherwise. The plugin is a tool, never the authority (§8.2.34 AJ6).
   `DESIGN.md` at the root is derived from `docs/design/tokens.css`: after a change to the tokens, run
   `uv run python .claude/scripts/gui/design_md.py` and commit the result.
