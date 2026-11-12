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

**`shell`**, the browser workbench: `uv run python .claude/scripts/gui/render_shell.py [--only <group> ...] <r>`.
It writes `<r>/manifest.json`, runs `shoot.cjs` over it and stops its servers. Every shot is light and dark
(`[1280, 800]`), and each waits for the screen's `data-screen-ready`, as the workbench sets it once Mol* has
drawn. Six groups, all by default:

- `states`: each screen of `nanopnp.gui.web.screens.SCREENS` in each state of `nanopnp.gui.web.states.STATES`
  (`shell-<state>-<screen>-<scheme>`).
- `2wcd`: each screen of a project holding example 07's 2WCD dodecamer, which `server --project` walks to its
  charge (`shell-2wcd-<screen>-<scheme>`). The script keeps it in `cache/2wcd-<12 hex of sha256(case,
  structure)>/` beside `<r>`: the prepared PDB, the case and the project, built in a temporary sibling and
  renamed. It prints on stderr whether it built or reused the cache. The first walk fills the project's store,
  so the second render reads the charge from it and the 2WCD part takes under half the time. Give every render
  one parent folder to share it.
- `extra`: the states of REV-210 on the charged fixture (`shell-extra-<name>-<scheme>`): the New, Open, Import
  and Export dialogs, the File, View and Help menus, a folded rail, the Queue and Log tabs, the settings'
  Colours section, the 3D background setting, a key being captured, a typed palette query, the Glossary and
  About. A manifest entry's `click` lists selectors that `shoot.cjs` clicks in order once the page is ready.
- `compact`: molecular, settings and changes under a second config folder (`NANOPNP_CONFIG`, `<r>/config`) that
  holds `workbench.yaml` with compact density and tight spacing, and a theme of the user's own
  (`shell-compact-<screen>-<scheme>`). The theme is dark, so its light shots are dark too.
- `molecular`: the Molecular tools on a project holding only the cached 2WCD molecular model, its store empty
  (`shell-molecular-<name>-<scheme>`): `refused`, Prepare after a build of a structure moved off z under
  `axis: z`, and `building`, Protonation shot while its build runs. The built tools are the `2wcd` group's
  `m-<tool>` shots and the empty ones the `states` group's. The `2wcd` group also opens the windows over a
  tool (`PROJECT_EXTRAS`): *Open structure…*, the titratable groups, the warnings and the settings, the mesh
  coloured by SICN with its last bar picked, the mesh's protein part picked, Region's
  membrane picked, and last an unsaved edit of Pore geometry's outline, which the server then holds.
- `continuum`: the Continuum tools on a project holding the cached 2WCD molecular and continuum models, its store
  empty (`shell-continuum-<name>-<scheme>`): `refused`, Pore geometry blocked by stage 4 at an isolevel of 0.9, and
  `building`, Pore geometry shot while its build runs. The built tools are the `2wcd` group's `c-<tool>`
  shots.

Needs Playwright through `NODE_PATH` and the `gui` extra. All six groups, 250 shots, take about seven minutes
on four cores once the 2WCD cache exists (seventeen when each shot ran alone, each in a browser context of its
own); the first render also builds that cache. The servers start together. `shoot.cjs` runs the shots of one server in order, since a server's
state carries from shot to shot, and the servers side by side on `NANOPNP_SHOOT_JOBS` workers (default: the
CPUs less one, at most 3). Each worker keeps one page, navigated again for each shot, so Chromium compiles
Mol* and Quasar once. More workers than that starve the software-GL pages: a menu then opens after the shot's
wait, and the shot differs. A shot waits for its `wait_ms`, then for any animation or change still going, at
most two seconds more. The longest chain, `extra`, takes about a minute alone.

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
