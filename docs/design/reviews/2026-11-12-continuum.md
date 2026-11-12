# The Continuum suite's drafts on 2WCD: the author's verdicts, round 1

WP5.17's prototype round (§8.2.34 AJ8): the four Continuum tools drafted on the 2WCD dodecamer and the fixtures, from
the render `shell-45d3f65-r4` of the tree committed as `641feae`, 58 Continuum shots of its 206, light and dark, built, blocked by stage 4,
building, refused and empty. They were published as a digest of 14 picks at
`https://claude.ai/artifact/BPJ8ojhCzRkresApCL5qht`, and the verdicts were collected on 12 November 2026.

The author marked all 14 picks: 8 `keep`, 6 `change`, no `drop`. No keep carries a note. Three questions were the
author's to decide and were asked at the collect (below): whether Contour merges into the protein's geometry tool, how
far Region's editing goes now, and how the mesh's part sizes are laid out, which the author sent to a brainstorm of
drawn layouts and then chose the tree of the mesh's parts (below, *The size layouts*). WP5.17's item 12 builds the changes; the notes that ask for a discussion
are REV-244. *Stands for* counts the shots a pick's verdict covers (`digest.json` beside the page lists them).
*Reviewer finding* names the finding, `F1` to `F25`, of the GUI review of the drafts at `45d3f65`. Notes are the
author's words.

| Pick | Stands for | Verdict | Note | Reviewer finding | Disposition |
|---|---|---|---|---|---|
| `shell-2wcd-c-geometry-light` | 4 | change | "- Add color bar and units - Add keys to the layers - The tools look too much like the card now ... Maybe a more subtle approach with the Just the tool name on the left + status symbols/dots on the right? When selected, it should have a different background shading." | F1, F2 | Item 12: the map has a colour bar naming its quantity and unit; a key names each layer drawn, with its line. As the note asks (WB-41), the tool list loses its cards in both suites. A tool is a row with its name on the left and its state's glyph on the right, the state's word in the row's name and tooltip. The selected tool takes the selection's shading, and a building stage's thin bar runs along its row's foot |
| `shell-2wcd-c-contour-light` | 2 | change | "Can this not be merged with protein geometry? Now that I see the division, perhaps the charge map and contour building need to go to their own suite that sits in between molecular and continuum. I would like to add this as a follow-up for more in-depth discussion." | F4 | Ruled (below): Contour merges into *Pore geometry*, which shows the maps, stages 2 to 4's values and the outline, and whose *Edit outline* opens the editor in its pane; its readout carries stage 4's verdict. REV-244: a suite between Molecular and Continuum for the charge map and the outline's building, for the discussion the note asks. With it go the radius against z and the vertex list that the design row drew (F4) |
| `shell-2wcd-c-contour-edit-light` | 2 | keep | — | F5, F20 | — |
| `shell-2wcd-c-region-light` | 2 | change | "This looks great, though I think it should be expanded to allows visualisation and editing of ALL regions, including membrane and reservoirs. It should include some limited CAD tooling as well (ideally we import this from an existing package). The final geometry should also not show the membrane lines extending into the pore domain, and allow each domain to be selected separately." | F16, F18 | Ruled (below): the domains now, the CAD tooling later. Item 12: Region draws each domain as its own shape: the protein, the membrane, and the electrolyte of the pore and of the reservoirs. The membrane stops at the protein's outline, so no membrane line crosses the pore. A click on a domain selects and outlines it and brings its values to the pane's head (the membrane its thickness and centre, the reservoir its radius). REV-244: limited CAD tooling, from an existing package where one fits, with the sketcher (FR-42) |
| `shell-2wcd-c-mesh-light` | 1 | change | ""the table's" is a bit strange, where are those values? Perhaps it would be better if those size nodes are in a drop-down menu or tree hierarchy, where clicking on one allows one to change the settings for that node? Let's brainstorm further on this." | F8, F19 | Answered: "the table's" is §5.2.2's size table, whose row a blank part takes; every layout drawn writes the row's value as the blank field's hint and the size used beside it. Ruled (below): a brainstorm first; three layouts were drawn and published (*The size layouts*), and the author preferred the tree, which item 12 builds. The *Sizes used* block goes |
| `shell-2wcd-c-mesh-sicn-light` | 2 | change | "The histogram as it is plotted now is not very informative. Maybe it needs some relevant figures of merit like thresholds etc. Would be useful as well if clicking on the bar of histogram highlights the elements in that bin on the screen." | F8 | Item 12: the quality view opens on the gate's verdict and limits (SICN and gamma above 0.3, the least of each); the histogram gets its axis, each bar's count, the 0.3 floor marked and the bars in the view's palette. A bar clicked fills its elements in the view and dims the rest. The draft outlined them, which the still shot did not show |
| `shell-2wcd-c-mesh-dark` | 1 | keep | — | F6 | — |
| `shell-continuum-refused-light` | 2 | keep | — | F9, F10, F11 | — |
| `shell-continuum-building-light` | 2 | keep | — | F22 | — |
| `shell-refused-c-region-light` | 10 | keep | — | F12 | The card asked whether the field a refused file names should stay editable. Kept as built, as in Molecular: a file that forms no case disables the pane, and the field is fixed in the file or reset. F12 is closed |
| `shell-empty-c-geometry-light` | 10 | keep | — | F23 | — |
| `shell-charged-tube-c-geometry-light` | 12 | change | "Maybe this should be more general "Pore geometry"?" | F13, F14 | Ruled (below): the merged tool is *Pore geometry*. Item 12: for a model that supplies its outline, Pore geometry draws that outline and edits it, its stage 2 to 4 values are read-only, and its row says the outline is supplied (F13, F14) |
| `shell-charged-tube-c-region-light` | 4 | keep | — | — | — |
| `shell-charged-tube-c-mesh-light` | 4 | keep | — | — | — |

## The questions asked at the collect

- **Contour and the protein's geometry.** Both build stages 2 to 4 and draw the same outline; WB-15 had folded them
  into one tool. Offered merging them as *Pore geometry*, keeping two tools with the first renamed, or waiting for the
  discussion on a suite between Molecular and Continuum, the author chose "Merge as Pore geometry" (WB-41).
- **Region's editing.** The membrane's and the reservoir's values are typed in the pane and on the drawing; drawing
  the (r, z) domain by hand is the sketcher, FR-42, a phase after Phase 5. Offered each domain drawn and selectable now
  with the CAD tooling left to the sketcher, the same with a survey of CAD packages now, or a design round first, the
  author chose "Domains now, CAD later" (WB-41; REV-244).
- **The mesh's part sizes.** Offered a tree of the mesh's parts now, refined later, the values written as each blank
  field's hint, or drawn layouts first, the author chose "Brainstorm first" (WB-41).

## REV-235's and REV-237's points

The Continuum screens open no project dialog, settings row, menu, Glossary or log of their own, so none of REV-235's
remaining points was put at this round; they wait for the Physics suite's round (WP5.18). Of REV-237's, a changed
value opens the tool that sets it at its field (`?field=`), which the Continuum tools now can, and item 12 builds it
for them. The list of one line per changed value, which WP5.16's collect set beside the changed table for this round,
is built in item 12 and shown at its final render. The palette's look and the help page stay open.

## The size layouts

Three layouts of the Mesh tool's sizes, drawn over the live 2WCD Mesh page at size scale 4 with nothing typed (the
pane's size fields swapped for each layout in the browser; the view drawn by material with the selected part in its
colour and the rest grey), light and dark: six shots in `<s>/sizes-proto/shots/`. Each lists the domains as the view's
legend names them (protein, electrolyte, membrane), the boundaries (the wall, the outer boundary, the axis in the
pore) and the global size, each with the size used and where it comes from: the table, `auto` for the wall, the global
size for the membrane. They were published at `https://claude.ai/artifact/Thfn4DykmSfimP6iEG5J1W` for `prefer`,
`borrow` or `reject`.

- **A. A tree of the mesh's parts**: Domains and Boundaries, then Global; a click selects a part, draws it and opens
  its one field below, the table's value as the blank's hint.
- **B. A drop-down of parts**: one *Part* menu listing every part with its size used, and the chosen part's field.
- **C. One table**: a row per part with its base field and the size used; the row under the pointer or the focus is
  drawn.

The author marked all three on 12 November 2026: A `prefer`, B and C `reject`.

| Layout | Stands for | Verdict | Note | Disposition |
|---|---|---|---|---|
| `sizes-tree-light` | 2 | prefer | "I like this because it is also extensible. We may need a way as well to create subdivisions in boundaries and domains for meshing purposes as well." | Item 12 builds the tree in the Mesh tool (WB-41). REV-244: subdivisions of a domain or a boundary for meshing, refinement regions that the design document puts in the Mesh builder's later column (FR-11), each a child of its part in the tree |
| `sizes-dropdown-light` | 2 | reject | — | — |
| `sizes-table-light` | 2 | reject | — | — |
