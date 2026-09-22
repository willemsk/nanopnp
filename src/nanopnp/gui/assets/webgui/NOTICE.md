# The field viewer's renderer

`webgui.js` is the renderer the desktop shell's field viewer loads, so a field draws on a machine
with no network. It is redistributed **unmodified** and is loaded at run time as a separate file.
Nothing in nanopnp is linked against it, and the nanopnp library remains BSD-3-Clause
(`SPECIFICATION.md` CON-09).

| | |
|---|---|
| Package | npm `webgui` 0.2.39, the version `netgen.webgui` in NGSolve 6.2.2606 pins |
| Tarball | <https://registry.npmjs.org/webgui/-/webgui-0.2.39.tgz> |
| Integrity | `sha512-yDd6YR7EjHGfeUC+rbn6/WvTWWkwJSU1KcsqWYzP5qJyN3IN9ax2vuUROvn8epKRKtuerLJ2qTSPp8A1yZubqw==` (npm `dist.integrity`) |
| This file | `package/dist/webgui.js` of that tarball, byte for byte |

## Licences

The file is a build that bundles three works:

| Work | Copyright | Licence | Text |
|---|---|---|---|
| webgui | its authors, of the NGSolve project | LGPL-2.1-or-later | `LICENSE.webgui` |
| three.js r152 | 2010–2023 three.js authors | MIT | `LICENSE.three` |
| dat.gui 0.7 | 2011 Data Arts Team, Google Creative Lab | Apache-2.0 | `LICENSE.dat-gui` |

## Corresponding source

The npm tarball named above is the corresponding source of webgui. It carries `src/*.ts`, the
shaders, `package.json`, `vite.config.mjs` and `build_shaders.js` beside the built file. It is kept
verbatim in nanopnp's repository and source distribution as `third_party/webgui-0.2.39.tgz`, at
<https://github.com/willemsk/nanopnp>. You may replace `webgui.js` with any build of your own; the
viewer loads whatever file is at this path.

## Refreshing it

When an NGSolve upgrade moves the version `netgen/webgui.py` pins, follow these steps. The Tier-1
test `test_ver44_vendored_renderer_matches_npm_integrity` fails until all of them are done.

1. Download the new tarball from the npm registry.
2. Check its SHA-512 against the `dist.integrity` the registry publishes for that version.
3. Replace `third_party/webgui-<version>.tgz`.
4. Copy `package/dist/webgui.js` and `package/LICENSE` (as `LICENSE.webgui`) here.
5. Update `RENDERER_VERSION` and `RENDERER_INTEGRITY` in `nanopnp/gui/render.py`, and the table
   above.
6. Recheck which three.js and dat.gui versions the build bundles.
