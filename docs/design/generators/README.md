# Design generators

The scripts that write the choice panels (`../choices/`) and the whole-workbench mockups (`../mockups/`), and the
private verdict galleries that publish them (WP5.01 items 10 and 12). The committed HTML is their output; edit
here and rebuild rather than editing the pages by hand. Run each from its own directory:

| Step | Command |
|---|---|
| Choice panels | `cd choices && uv run python build.py` |
| Mockups | `cd mockups && uv run python build.py` (reuses `../choices/` for the shapes and the frame parts); it rebuilds mockup A, the one chosen, and leaves B as the author marked it in round 1 |
| Render manifest | `uv run python manifest.py <mockups or choices> <render dir>`, then `node .claude/scripts/gui/shoot.cjs <render dir>/manifest.json <render dir>` as `/np-gui render` says |
| Gallery | `cd gallery/<choices or mockups> && python3 build.py <render dir>`, then publish its `index.html` with the files `files.json` lists, to the URL in `url` |

`shapes.py` draws the (r, z) outlines, the half-disc reservoir and a graded mesh, not to scale; the mesh is seeded,
so a rebuild changes no page. `findings.json` holds what each gallery card says of the review.
