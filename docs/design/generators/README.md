# Design generators

The scripts that write the choice panels (`../choices/`) and the whole-workbench mockups (`../mockups/`), and the
private verdict galleries that publish them (WP5.01 items 10 and 12). The committed HTML is their output; edit
here and rebuild rather than editing the pages by hand. The tree round's boards (`../concepts/tree/`, WP5.22) are
written by hand over `tree/extract.py`'s data, 2WCD's solved fields read through the library. Run each from its own
directory:

| Step | Command |
|---|---|
| Choice panels | `cd choices && uv run python build.py` |
| Mockups | `cd mockups && uv run python build.py` (reuses `../choices/` for the shapes and the frame parts); it rebuilds mockup A, the one chosen, and leaves B as the author marked it in round 1 |
| The tree round's data (WP5.22) | `cd tree && uv run python extract.py <analysis project> ../../concepts/tree/data.js`, the project being the one `render_shell.py --only analysis` builds in its cache (`cache/analysis-<key>/`) |
| Render manifest | `uv run python manifest.py <mockups, choices or tree> <render dir>`, then `node .claude/scripts/gui/shoot.cjs <render dir>/manifest.json <render dir>` as `/np-gui render` says |
| Gallery | `cd gallery/<choices or mockups> && python3 build.py <render dir>`, then publish its `index.html` with the files `files.json` lists, to the URL in `url` |
| The tree round's gallery (WP5.22) | Render the boards (`manifest.py tree`, then `shoot.cjs`; `data.js` is committed, so no solve), then `uv run python .claude/scripts/gui/digest.py build gallery/tree/picks.json <render dir>/index.json <out>` and publish its `index.html` with the boards under `live/tree/` and `tokens.css`, to the URL in `gallery/tree/url`. Today's explorer pick needs an `analysis` render of the shell as well. `gallery/tree/` also keeps the round's agenda and the GUI review's and the critique's unedited replies on render `tree-6186208` |

`shapes.py` draws the (r, z) outlines, the half-disc reservoir and a graded mesh, not to scale; the mesh is seeded,
so a rebuild changes no page. `findings.json` holds what each gallery card says of the review.
