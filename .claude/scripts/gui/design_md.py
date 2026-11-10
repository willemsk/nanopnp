"""Write DESIGN.md from docs/design/tokens.css for the impeccable plugin's checks (§8.2.34 AJ6).

    uv run python .claude/scripts/gui/design_md.py [--check]

`--check` writes nothing and exits 1 if DESIGN.md differs from what this script would write.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOKENS = ROOT / "docs" / "design" / "tokens.css"
OUT = ROOT / "DESIGN.md"

DECL = re.compile(r"^\s*(--[\w-]+):\s*([^;]+);\s*(?:/\*\s*(.*?)\s*\*/)?\s*$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# The opening line of each block whose declarations are read.
BLOCKS = {
    "light": ":root {",
    "compact": ':root[data-density="compact"] {',
    "dark": ':root[data-theme="dark"] {',
}


def parse_block(lines: list[str], opener: str) -> dict[str, tuple[str, str]]:
    """Return name -> (value, trailing comment) for the block that opens with `opener`."""
    found: dict[str, tuple[str, str]] = {}
    inside = False
    for line in lines:
        if not inside:
            inside = line.strip() == opener
            continue
        if line.strip() == "}":
            break
        match = DECL.match(line)
        if match:
            found[match.group(1)] = (match.group(2).strip(), match.group(3) or "")
    return found


def px(value: str) -> str:
    """Return a rem value in pixels, or the value unchanged."""
    match = re.fullmatch(r"([\d.]+)rem", value)
    if not match:
        return value
    return f"{float(match.group(1)) * 16:g}px"


def build(css: str) -> str:
    """Return the text of DESIGN.md for the given tokens.css text."""
    lines = css.splitlines()
    light = parse_block(lines, BLOCKS["light"])
    compact = parse_block(lines, BLOCKS["compact"])
    dark = parse_block(lines, BLOCKS["dark"])

    colours = {n[2:]: v for n, (v, _) in light.items() if HEX.match(v)}
    sizes = {n[7:]: px(v) for n, (v, _) in light.items() if n.startswith("--text-")}
    ui_font = light["--font-ui"][0]
    num_font = light["--font-num"][0]

    out: list[str] = [
        "---",
        "name: nanopnp workbench",
        "description: Derived design tokens of the nanopnp workbench (light theme).",
        "colors:",
    ]
    out += [f'  {name}: "{value}"' for name, value in colours.items()]
    out += [
        "typography:",
        "  body:",
        f"    fontFamily: '{ui_font}'",
        f'    fontSize: "{sizes["md"]}"',
    ]
    out += ["  number:", f"    fontFamily: '{num_font}'", f'    fontSize: "{sizes["md"]}"']
    out += ["rounded:", f'  md: "{light["--radius"][0]}"', f'  compact: "{compact["--radius"][0]}"']
    out += [
        "spacing:",
        f'  gap: "{px(light["--gap"][0])}"',
        f'  pad: "{px(light["--pad"][0])}"',
        f'  row: "{px(light["--row"][0])}"',
    ]
    out += ["---", ""]

    out += [
        "<!-- DERIVED FILE. Generated from docs/design/tokens.css by",
        "     .claude/scripts/gui/design_md.py. Do not edit by hand:",
        "     change tokens.css and run the script again. -->",
        "",
        "# Design System: nanopnp workbench",
        "",
        "## Overview",
        "",
        "This file is derived. It exists so the `impeccable:impeccable` plugin's checks",
        "can read the tokens (§8.2.34 AJ6). It is not the authority.",
        "",
        "- `docs/design/workbench.md` and `docs/design/tokens.css` are the authority",
        "  on the workbench's design.",
        "- The rulings (§8.2, the WB register in `docs/design/workbench.md`) win over",
        "  the plugin's rules. Inter is the ruled typeface (WB-21: one sans shipped with",
        "  the application, numbers in a monospace with tabular figures). A plugin",
        "  finding against Inter, or against any other ruling, is answered by citing",
        "  the ruling.",
        "",
        "Light is the default theme. Dark applies under `prefers-color-scheme: dark`",
        'or `data-theme="dark"`.',
        "",
        "## Colors",
        "",
        "Light values are in the frontmatter. A token with no dark value keeps its light value.",
        "",
        "| Token | Light | Dark | Role |",
        "|---|---|---|---|",
    ]
    for name, (value, comment) in light.items():
        if not HEX.match(value):
            continue
        dark_value = dark.get(name, ("", ""))[0] or "same"
        role = comment.replace("|", "/")
        out.append(f"| `{name}` | `{value}` | `{dark_value}` | {role} |")

    out += [
        "",
        "One accent (`--accent`) marks selection, the primary action, focus and links",
        "(WB-20). Semantic colours are always paired with a glyph and a word.",
        "",
        "## Typography",
        "",
        f"**UI font:** `{ui_font}`",
        "",
        f"**Number font:** `{num_font}`",
        "",
        "| Step | Size |",
        "|---|---|",
    ]
    out += [f"| `{name}` | {value} |" for name, value in sizes.items()]
    out += [
        "",
        f"At compact density the body size is {px(compact['--text-md'][0])}.",
        "",
        "## Layout",
        "",
        "| Token | Default | Compact |",
        "|---|---|---|",
    ]
    for name in ("--row", "--gap", "--pad", "--radius"):
        out.append(f"| `{name}` | {px(light[name][0])} | {px(compact[name][0])} |")
    out += [
        f"| `--target-min` | {light['--target-min'][0]} | same |",
        "",
        "Spacing is a user setting beside density (WB-31).",
        "",
        "## Shapes",
        "",
        f"Corners are {light['--radius'][0]} by default and",
        f"{compact['--radius'][0]} at compact density.",
        "",
        "## Motion",
        "",
        f"`--motion-fast` {light['--motion-fast'][0]},",
        f"`--motion-base` {light['--motion-base'][0]},",
        f"easing `{light['--ease'][0]}`. Motion is functional only, under 200 ms,",
        "and none under reduced motion (WB-23).",
        "",
        "## Focus",
        "",
        f"A {light['--focus-width'][0]} ring offset by {light['--focus-offset'][0]},",
        "in `--focus` (WB-24).",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    """Write DESIGN.md, or with `--check` compare it."""
    text = build(TOKENS.read_text(encoding="utf-8"))
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            sys.stderr.write("DESIGN.md is stale: run .claude/scripts/gui/design_md.py\n")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
