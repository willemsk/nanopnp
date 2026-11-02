# The molecule viewer

`molstar.js` and `molstar.css` are the viewer the workbench's screens load, so a molecule draws on a
machine with no network. They are redistributed **unmodified** and are loaded at run time as separate
files. Nothing in nanopnp is linked against them, and the nanopnp library remains BSD-3-Clause
(`SPECIFICATION.md` CON-09; ADR-004's NOTE, the front end, v0.6).

| | |
|---|---|
| Package | npm `molstar` 5.13.1 (MIT, `LICENSE.molstar`) |
| Tarball | <https://registry.npmjs.org/molstar/-/molstar-5.13.1.tgz> |
| Integrity | `sha512-iExD98bJN2P4JK6+pVMwdJlPePldBH8oNT0pZhs8ucxOp086NU2b/gThKwYMC3SWkdmv++a1g4fGwKfu4Glx1w==` (npm `dist.integrity`) |
| `molstar.js` | `package/build/viewer/molstar.js` of that tarball, byte for byte; sha256 `4fc6493c2471db8834dcc391151b344d7017e4eb8a4eb76c152be5f9dbd23874` |
| `molstar.css` | `package/build/viewer/molstar.css`, byte for byte; sha256 `22fbf73b75c11ef57687d08437c95dbfe8430ea895264f6da2b9b01e28bacc49` |

The build bundles Mol*'s own npm dependencies, which are permissively licensed (rxjs, io-ts, tslib,
immutable and mutative among them). The bundle holds no GPL text and no x264. The tarball carries the
corresponding source; it is not copied here, because the licence does not ask for it. You may replace the
two files with any build of your own; the screens load whatever is at these paths.

## Refreshing it

1. Download the new tarball and check its SHA-512 against the registry's `dist.integrity`.
2. Copy the two files and `package/LICENSE` (as `LICENSE.molstar`) here.
3. Update the table above. The Tier-1 test `test_con09_the_vendored_molstar_is_unmodified` fails until
   the recorded sha256 values match the files.
