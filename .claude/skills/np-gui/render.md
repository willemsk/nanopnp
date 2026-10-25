# Render screens headless

`/np-gui render <qt | mockups | shell>` writes PNGs and an `index.json` into `<r>`, then reads them.

## Targets

**`qt`**, today's shell (removed with it):

1. Install the system libraries Qt needs offscreen, once per container:
   `apt-get install -y --no-install-recommends libegl1 libgl1 libxkbcommon0 libnss3 libxcomposite1
   libxdamage1 libxrandr2 libxtst6 libxkbfile1 libasound2t64`
   (`knowledge/07-software-stack/05-gui-and-packaging.md`).
2. `uv run python .claude/scripts/gui/capture_qt.py <r>` in the background, about ten minutes: it
   writes `<state>-<tab>[-<view>].png`, `qt-index.json` and `webgui-manifest.json`. A `missed` entry
   in `qt-index.json` is a view it could not reach; report each.
3. `node .claude/scripts/gui/shoot.cjs <r>/webgui-manifest.json <r>/html`: the HTML documents the
   render children wrote, standing for the web views that draw nothing offscreen.

**`mockups`**, every `docs/design/{concepts,style,choices,mockups}/**/*.html`. Write `<r>/manifest.json`, four
entries per page: viewports `[1440, 900]` and `[1280, 800]`, schemes `light` and `dark`, `wait_ms:
300`, `expand: "[data-screen]"`, id `<dir>-<stem>-<w>-<scheme>`, `url` the page's `file://` URI. A
choice panel is a fragment, small enough to judge on a phone: two entries, `[960, 640]`, light and dark.
Then `node .claude/scripts/gui/shoot.cjs <r>/manifest.json <r>`.

**`shell`**: added by WP5.02; until then say so and stop.

`shoot.cjs` finds Playwright through `NODE_PATH`; `node .claude/scripts/gui/shoot.cjs --self-check
<s>/selfcheck` checks the browser renders a WebGL page.

## Read and report

1. Read the PNGs the change touched (`Read` shows an image), and each one named in a finding.
2. From `index.json`, report per shot: `page_errors`, `console`, each `contrast` entry (selector,
   ratio against 4.5 or 3) and each `targets` entry (selector, size against 24 × 24 CSS px; an
   `inline` link is excepted by WCAG 2.2 2.5.8 and noted, not failed).
3. A page error, or a page that did not load (exit 2), stops the caller: the item does not commit.
   A failed contrast or target check stops it too, unless the item records why the check is wrong.
