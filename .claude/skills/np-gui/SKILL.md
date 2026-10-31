---
name: np-gui
description: Render, review and publish GUI screens and mockups for the author's verdicts, collect them, or run a design round with the author. Use when a change touches a screen, a mockup or the workbench design, or on /np-gui.
argument-hint: <render | review | publish | collect | grill> [target|topic|url]
---

# GUI: `$ARGUMENTS`

If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}` appears literally, the arguments are the text after the
command and the directory is `.claude/skills/np-gui/` (`.claude/workflow/hosts.md`). `publish` and
`collect` need Claude Code's artifact tools: on another host, stop and say so.

1. The first argument is the level, the second its target, topic or URL. A missing or unknown level:
   print `Usage: /np-gui <render | review | publish | collect | grill> [target|topic|url]` and stop.
2. Read the level's file beside this one: `${CLAUDE_SKILL_DIR}/<level>.md`, one of `render.md`,
   `review.md`, `publish.md`, `collect.md` and `grill.md`.
3. Follow the level's file. `<s>` is the session's scratchpad; `<r>` a render directory
   `<s>/gui-render/<target>-<short sha>/`. The design document is `docs/design/workbench.md`
   (§8.2.17 S21, S22).
