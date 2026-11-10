---
name: nanopnp workbench
description: Derived design tokens of the nanopnp workbench (light theme).
colors:
  bg: "#f6f7f9"
  panel: "#ffffff"
  sel: "#ece7ff"
  line: "#d9dce3"
  control-edge: "#7c8290"
  ink: "#16181d"
  muted: "#4f5563"
  accent: "#5b3fd6"
  accent-ink: "#ffffff"
  focus: "#5b3fd6"
  ok: "#1b7043"
  warn: "#8a5200"
  err: "#b4231a"
  changed: "#0f6b75"
  canvas-3d: "#0d0f13"
  canvas-3d-ink: "#e8eaef"
  canvas-plot: "#ffffff"
  canvas-plot-ink: "#16181d"
typography:
  body:
    fontFamily: '"Inter", system-ui, "Segoe UI", Roboto, sans-serif'
    fontSize: "13.5px"
  number:
    fontFamily: '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace'
    fontSize: "13.5px"
rounded:
  md: "6px"
  compact: "3px"
spacing:
  gap: "6px"
  pad: "8px"
  row: "30px"
---

<!-- DERIVED FILE. Generated from docs/design/tokens.css by
     .claude/scripts/gui/design_md.py. Do not edit by hand:
     change tokens.css and run the script again. -->

# Design System: nanopnp workbench

## Overview

This file is derived. It exists so the `impeccable:impeccable` plugin's checks
can read the tokens (§8.2.34 AJ6). It is not the authority.

- `docs/design/workbench.md` and `docs/design/tokens.css` are the authority
  on the workbench's design.
- The rulings (§8.2, the WB register in `docs/design/workbench.md`) win over
  the plugin's rules. Inter is the ruled typeface (WB-21: one sans shipped with
  the application, numbers in a monospace with tabular figures). A plugin
  finding against Inter, or against any other ruling, is answered by citing
  the ruling.

Light is the default theme. Dark applies under `prefers-color-scheme: dark`
or `data-theme="dark"`.

## Colors

Light values are in the frontmatter. A token with no dark value keeps its light value.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--bg` | `#f6f7f9` | `#14171c` | the frame behind panels |
| `--panel` | `#ffffff` | `#1c2027` | panels, cards, menus |
| `--sel` | `#ece7ff` | `#2e2752` | a selected row or tab, always with a marker (--accent edge or weight) |
| `--line` | `#d9dce3` | `#2f3440` | dividers only; never the edge of a control |
| `--control-edge` | `#7c8290` | `#6f7685` | inputs, secondary buttons, toggles: 3.9:1 on --panel, 3.6:1 on --bg, 3.2:1 on --sel |
| `--ink` | `#16181d` | `#e8eaef` | 17.8:1 on --panel |
| `--muted` | `#4f5563` | `#a9afbd` | 7.5:1 on --panel; secondary text, units |
| `--accent` | `#5b3fd6` | `#b4a2ff` | 6.7:1 on --panel |
| `--accent-ink` | `#ffffff` | `#1a1240` | text on --accent, 6.7:1 |
| `--focus` | `#5b3fd6` | `#b4a2ff` | focus ring, 5.6:1 on --sel |
| `--ok` | `#1b7043` | `#79d6a0` | built, passed  ✓; 5.1:1 on --sel |
| `--warn` | `#8a5200` | `#f2bd5e` | stale, a warning  ● |
| `--err` | `#b4231a` | `#ff8b80` | refused, failed  ✕ |
| `--changed` | `#0f6b75` | `#5fd0d9` | a value changed from its default  ◆; an override, outlined ◇ (WB-28) |
| `--canvas-3d` | `#0d0f13` | `same` |  |
| `--canvas-3d-ink` | `#e8eaef` | `same` |  |
| `--canvas-plot` | `#ffffff` | `#1c2027` |  |
| `--canvas-plot-ink` | `#16181d` | `#e8eaef` |  |

One accent (`--accent`) marks selection, the primary action, focus and links
(WB-20). Semantic colours are always paired with a glyph and a word.

## Typography

**UI font:** `"Inter", system-ui, "Segoe UI", Roboto, sans-serif`

**Number font:** `"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace`

| Step | Size |
|---|---|
| `xs` | 12px |
| `sm` | 13px |
| `md` | 13.5px |
| `lg` | 16px |
| `xl` | 22px |
| `2xl` | 28px |

At compact density the body size is 12.5px.

## Layout

| Token | Default | Compact |
|---|---|---|
| `--row` | 30px | 26px |
| `--gap` | 6px | 4px |
| `--pad` | 8px | 6px |
| `--radius` | 6px | 3px |
| `--target-min` | 24px | same |

Spacing is a user setting beside density (WB-31).

## Shapes

Corners are 6px by default and
3px at compact density.

## Motion

`--motion-fast` 120ms,
`--motion-base` 180ms,
easing `cubic-bezier(0.2, 0, 0, 1)`. Motion is functional only, under 200 ms,
and none under reduced motion (WB-23).

## Focus

A 2px ring offset by 2px,
in `--focus` (WB-24).
