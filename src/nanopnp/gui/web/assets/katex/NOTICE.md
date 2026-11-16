# The equation renderer

`katex.min.js`, `katex.min.css` and the WOFF2 fonts in `fonts/` draw the equations the Physics suite shows, so an
equation draws on a machine with no network (WB-42). They are redistributed **unmodified** and are loaded at run time
as separate files. Nothing in nanopnp is linked against them, and the nanopnp library remains BSD-3-Clause
(`SPECIFICATION.md` CON-09; ADR-004's NOTE, the front end, v0.6).

| | |
|---|---|
| Package | npm `katex` 0.19.1 (MIT, `LICENSE.katex`) |
| Tarball | <https://registry.npmjs.org/katex/-/katex-0.19.1.tgz> |
| Integrity | `sha512-jG8uKntjSEcm2EpQOh0XturpPuuC9r3Sq5HLHdsFdWZT27E672SF19QEi+of0/YeOy15lDgRhKvr5614uRrEfA==` (npm `dist.integrity`) |
| `katex.min.js` | `package/dist/katex.min.js` of that tarball, byte for byte; sha256 `fa140498b8cfc8302cbe5e7cb1bdbc1f952bc38b3fa258ede09e73edbf9a74bc` |
| `katex.min.css` | `package/dist/katex.min.css`, byte for byte; sha256 `00e0b094171b07f58422075f469b4feac2b2f7bce1aeec943c08da4d697f4dcf` |

The fonts are the tarball's `package/dist/fonts/*.woff2`, byte for byte. The stylesheet also names WOFF and TrueType
copies, which a browser reads only where it cannot read WOFF2, so they are not copied. Each font's sha256:

| Font | sha256 |
|---|---|
| `KaTeX_AMS-Regular.woff2` | `0cdd387c9590a1a9f9794560022dbb59654a7d86f187aa0c81495ad42d3a7308` |
| `KaTeX_Caligraphic-Bold.woff2` | `de7701e42cf1f4cf0b766c03fb27977207eee2f4fd5d76fa82188406da43ea4c` |
| `KaTeX_Caligraphic-Regular.woff2` | `5d53e70ad607c2352162dec9e0923fb54ecdafaccbf604cd8dcf7d00facb989b` |
| `KaTeX_Fraktur-Bold.woff2` | `74444efd593c005e3f4573b44524704c0af0a937fe911cca9e94068d0d140d3f` |
| `KaTeX_Fraktur-Regular.woff2` | `51814d270d06ff0255dba0799994fa4d8c84d11f09951d47595f4abb1f3602dc` |
| `KaTeX_Main-Bold.woff2` | `0f60d1b897938ec918c8ce073092411baf9438f6739465693ff18b0f9d20b021` |
| `KaTeX_Main-BoldItalic.woff2` | `99cd42a3c072d918f2f44984a807cf7aa16e13545fd0875fc07c6c65f99e715b` |
| `KaTeX_Main-Italic.woff2` | `97479ca6cce906abc961ecac96faa5f9ca2e61b8e7670d475826bcdee9a7c267` |
| `KaTeX_Main-Regular.woff2` | `c2342cd8b869e01752a9321dc17213fc40d4d04c79688c1d43f2cf316abd7866` |
| `KaTeX_Math-BoldItalic.woff2` | `dc47344dbb6cb5b655c8460d561f4df5f501b90c804ad3c6cec65fe322351ab1` |
| `KaTeX_Math-Italic.woff2` | `7af58c5ec8f132a2ddde9027c6d7814decce4d3b822a11192a42a20e2e973264` |
| `KaTeX_SansSerif-Bold.woff2` | `e99ae51144bf1232efcc1bfe5add36262c6866b0faab24fa75740e1b98577a62` |
| `KaTeX_SansSerif-Italic.woff2` | `00b26ac825e2095056396e0553b8ac26d3f8ad158c3826e28b4c45b385c4714a` |
| `KaTeX_SansSerif-Regular.woff2` | `68e8c73ef42afd3ccec58bf0fba302cce448938e7fc020a5e31f8a952eee1342` |
| `KaTeX_Script-Regular.woff2` | `036d4e95149b69ff9bcc0cd55771efeb25ffa3947293e69acd78d5ac328c684b` |
| `KaTeX_Size1-Regular.woff2` | `6b47c40166b6dbe21a5dfca7718413f2147fd2399be1ba605d8ad39cedf25dfe` |
| `KaTeX_Size2-Regular.woff2` | `d04c54219f9eaec6d4d4fd42dfb28785975a4794d6b2fc71e566b9cd6db842dd` |
| `KaTeX_Size3-Regular.woff2` | `73d591271b1604960cb10bb90fee021670af7297017e0e98480b332d11f51995` |
| `KaTeX_Size4-Regular.woff2` | `a4af7d414440a1c1790825cfb700cf9cf43b0f2c4b04f0ebc523011ad9853ec0` |
| `KaTeX_Typewriter-Regular.woff2` | `71d517d67827787cfabdf186914cc3358eda539e37931941f2b2fd4a21f68c0b` |

## Refreshing it

1. Download the new tarball and check its SHA-512 against the registry's `dist.integrity`.
2. Copy `katex.min.js`, `katex.min.css`, `fonts/*.woff2` and `package/LICENSE` (as `LICENSE.katex`) here.
3. Update the tables above. The Tier-1 test `test_con09_the_vendored_libraries_are_unmodified` fails until the
   recorded sha256 values match the files.
