# The chart library

`uPlot.iife.min.js` and `uPlot.min.css` draw the time-series and line charts the workbench shows, so a chart draws on
a machine with no network. They are redistributed **unmodified** and are loaded at run time as separate files.
Nothing in nanopnp is linked against them, and the nanopnp library remains BSD-3-Clause
(`SPECIFICATION.md` CON-09; ADR-004's NOTE, the front end, v0.6).

| | |
|---|---|
| Package | npm `uplot` 1.6.32 (MIT, `LICENSE.uplot`) |
| Tarball | <https://registry.npmjs.org/uplot/-/uplot-1.6.32.tgz> |
| Integrity | `sha512-KIMVnG68zvu5XXUbC4LQEPnhwOxBuLyW1AHtpm6IKTXImkbLgkMy+jabjLgSLMasNuGGzQm/ep3tOkyTxpiQIw==` (npm `dist.integrity`) |
| `uPlot.iife.min.js` | `package/dist/uPlot.iife.min.js` of that tarball, byte for byte; sha256 `19c8d4c6ad88929a79f4ae49d6f7161566dfd0ba3d15cc495e974f787eb78f1f` |
| `uPlot.min.css` | `package/dist/uPlot.min.css`, byte for byte; sha256 `df630c6a8d6f8eeaff264b50f73ce5b114f646ffd9a0bb74f049b0a00135fa04` |

## Refreshing it

1. Download the new tarball and check its SHA-512 against the registry's `dist.integrity`.
2. Copy `uPlot.iife.min.js`, `uPlot.min.css` and `package/LICENSE` (as `LICENSE.uplot`) here.
3. Update the table above. The Tier-1 test `test_con09_the_vendored_libraries_are_unmodified` fails until the
   recorded sha256 values match the files.
