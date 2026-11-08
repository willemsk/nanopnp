# Render screens headless

`/np-gui render <qt | mockups | shell>` writes PNGs and an `index.json` into `<r>`, then reads them.

## Targets

**`qt`**, the Qt shell (removed in WP5.21):

1. Install the system libraries Qt needs offscreen, once per container:
   `apt-get install -y --no-install-recommends libegl1 libgl1 libxkbcommon0 libnss3 libxcomposite1
   libxdamage1 libxrandr2 libxtst6 libxkbfile1 libasound2t64`
   (`knowledge/07-software-stack/05-gui-and-packaging.md`).
2. `uv run python .claude/scripts/gui/capture_qt.py <r>` in the background, about ten minutes: it
   writes `<state>-<tab>[-<view>].png`, `qt-index.json` and `webgui-manifest.json`. A `missed` entry
   in `qt-index.json` is a view it could not reach; report each.
3. `node .claude/scripts/gui/shoot.cjs <r>/webgui-manifest.json <r>/html`: the HTML documents the
   render children wrote, standing for the web views that draw nothing offscreen.

**`mockups`**, every `docs/design/{concepts,style,choices,mockups}/**/*.html`. Write `<r>/manifest.json`
with four entries per page:

- viewports `[1440, 900]` and `[1280, 800]`, schemes `light` and `dark`;
- `wait_ms: 300` and `expand: "[data-screen]"`;
- id `<path>-<w>-<scheme>`. `<path>` is the page's path under `docs/design/` without `.html`, with `/`
  written `-` (`mockups-a-01-molecular`);
- `url`, the page's `file://` URI.

A choice panel is a fragment, small enough to judge on a phone. It gets two entries, `[960, 640]`,
light and dark. Then run `node .claude/scripts/gui/shoot.cjs <r>/manifest.json <r>`.

**`shell`**, the browser workbench: `uv run python .claude/scripts/gui/render_shell.py <r>`. It starts
`nanopnp gui --no-browser --state <name>` for each state of `nanopnp.gui.web.states.STATES`, writes
`<r>/manifest.json` with an entry for each screen of `nanopnp.gui.web.screens.SCREENS` in each state, light
and dark (`[1280, 800]`; id `shell-<state>-<screen>-<scheme>`), runs `shoot.cjs` over it and stops the
servers. Each entry waits for the screen's `data-screen-ready`, as the workbench sets it once Mol* has
drawn. Needs Playwright through `NODE_PATH` and the `gui` extra. The first run in a container takes a few
minutes: the states walk their cases.

`shoot.cjs` finds Playwright through `NODE_PATH`; `node .claude/scripts/gui/shoot.cjs --self-check
<s>/selfcheck` checks the browser renders a WebGL page.

## Read and report

1. Read the PNGs the change touched (`Read` shows an image), and each one named in a finding.
2. From `index.json`, report per shot:
   - `page_errors` and `console`;
   - a `viewer` whose `ready` is false. That is a host document whose scene did not draw. Give its
     `error`;
   - each `contrast` entry: selector, and ratio against 4.5 or 3;
   - each `nontext` entry (WCAG 2.2 1.4.11): the kind (a control's `edge` or `fill`, a `focus ring`, a
     `selected edge` or `selected fill`, whichever reads better, a `selected, no marker` item, a `colour
     bar` end), selector, and ratio against 3. A control with neither edge nor fill is identified by
     its text and is not measured; a selected item (`aria-selected`, `aria-pressed`, `aria-current`) with
     neither is a finding;
   - each `targets` entry: selector, and size against 24 × 24 CSS px. An `inline` link is excepted by
     WCAG 2.2 2.5.8: note it, do not fail it;
   - the `unmeasured` text (SVG labels, faded text), as not checked.
3. A page error, a scene that did not draw, or a page that did not load (exit 2) stops the caller. The
   item does not commit. A failed contrast, non-text or target check stops it too, unless the item records why
   the check is wrong.
