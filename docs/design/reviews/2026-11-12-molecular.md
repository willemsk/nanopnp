# The Molecular suite, finished: the author's verdicts, round 2

WP5.16's five Molecular tools as they went to `/np-ship`, built to round 1's verdicts: the render at `41abc6c`, with
its 2WCD screens again at `ac4be57` (`shell-r3` to `shell-r7`), 202 shots, light and dark. They were published as
round 2 of the digest at `https://claude.ai/artifact/HRDfKwmg4WRYnowGuVB51g`, 19 picks, and the verdicts were
collected on 12 November 2026.

The author marked all 19 picks: 12 `keep`, 7 `change`, no `drop`. Four of the keeps carry a note, three of which ask
for something. Five questions were the author's to decide and were asked at the collect (below): the word for a build
a check stops, what a suite's icon opens, how Prepare shows the membrane, which file picker *Open structure…* gets,
and when REV-242's two points are settled. The changes are built in WP5.16 before its merge; the view that follows
the typed orientation is REV-243, ruled for before Phase 5 closes; the notes for later rounds are in REV-237 and
REV-240. *Stands for* counts the shots a pick's verdict covers (`digest.json` beside the page lists them).
*Reviewer finding* names the point of REV-241, the final GUI review of the tools at `def8265`, that the pick bears on.
Notes are the author's words.

| Pick | Stands for | Verdict | Note | Reviewer finding | Disposition |
|---|---|---|---|---|---|
| `shell-2wcd-m-prepare-light` | 2 | change | "- The main "Prepare structure" title seems very large. - The "Ensemble", "Protonation", etc card in the tool settings seem redundant though, as the seems info in the tool selection bar? I do like the style of the card more. - Chains: is that a text field, or a drop-down where one can select the chains? - Membrane: Is what is shown now the centre of the membrane? Perhaps we can put upper+lower leaflet, and make sure this is synced somehow with the continuum membrane position/thickness? - For REV-241. I think you mean to say that the view is only updated once save is clicked? Instant feedback would indeed be a nice feature, let's mark it as a QoL to be included before the end of the phase. - For the toolbar in the 3D viewer: the orange or yellow labels have very poor contrast." | REV-241 (the view and the typed values) | A tool's title is 22 px, below a page's 28 px. The stage cards are merged into the tool list, each tool a card in their style (below, the building card). Answered: Chains was a text field; it is now a pick among the file's chains, A to L on 2WCD, which also takes a typed group such as `A+B`; none picked is all. Answered: the plane drawn was z = 0, where the registration residues' centre is placed, not the membrane. Ruled (below): Prepare draws the two leaflets of the study that names the model, from its continuum model, names the study, and warns where the prepared residues sit off the membrane's centre. Answered: yes, the view changes at *Save prepared structure*; REV-243 carries the view that follows the typed values, before Phase 5 closes. The viewer's own buttons take the panel's fill and the text ink: they were Mol*'s light skin, half transparent over the canvas |
| `shell-2wcd-m-ensemble-light` | 2 | keep | — | — | — |
| `shell-2wcd-m-protonation-light` | 2 | keep | — | — | — |
| `shell-2wcd-m-edit-light` | 2 | keep | — | — | — |
| `shell-2wcd-m-view-dark` | 2 | keep | — | — | — |
| `shell-2wcd-m-protonation-states-light` | 1 | keep | — | REV-241 (the paging) | Kept as built, 15 rows a page; the point is closed |
| `shell-2wcd-m-protonation-states-dark` | 1 | keep | — | — | — |
| `shell-2wcd-m-protonation-warnings-light` | 2 | keep | — | REV-241 (the warnings' grouping) | Kept as built, grouped by message; the point is closed |
| `shell-2wcd-m-prepare-open-light` | 2 | change | "I would like to add the browse button still here. I would also serve as a good learning to begin work on file interactions for other parts of the program as well." | REV-241 (*Open structure…*) | Ruled (below): both pickers. *Browse…* opens the system's own file picker, filtered to structure files, and the file is copied into the project's inputs and used. The workbench's own browser, which returns a path, comes with the project dialogs that need one (REV-235) |
| `shell-molecular-refused-light` | 2 | keep | "Looks good. I am not convinced of the "refused" and "refusal" terminology though, as it sounds forced. The phrasing "Named by the refusal above." is also strange, maybe something like "See ..."  What alternatives to" (the note ends there) | — | Ruled (below): *blocked*. The state's word, the card's title ("Ensemble blocked by the axis check"), the problems list and the glossary say blocked; the field it names reads "See the message above." |
| `shell-molecular-building-light` | 2 | change | "Like mentioned in the first shot, I think the step cards should just be merged in with the tool menu items, including the progress bar." | — | Each tool in the list is a card with its stage's state: the left edge in the state's colour, the word under the name, and the thin moving bar along the foot while the stage builds. The pane's stage bar is gone |
| `shell-empty-m-prepare-light` | 10 | keep | "The empty 3D view seems fine to me. I don't think users would expect anything else? The only thing I can think of is drawing the membrane already, but not sure if that adds value." | REV-241 (the empty view) | The empty view stays, and the point is closed. With no structure there is nothing to place a membrane against, so none is drawn |
| `shell-charged-tube-m-view-light` | 30 | change | "Draw them here too. As a user, if I open a PQR file I would expect to see atoms at the very least!" | REV-241 (a PQR model in View) | View draws a PQR model's atoms, as spheres by default, coloured by their residue's net charge from the file's own charges, with the colour bar; its look controls are enabled. The point is fixed |
| `shell-extra-rail-folded-light` | 2 | change | "I am not convinced of the overview page with the links, though I also don't really know what else could be there. Perhaps we need to do some research on similar programs for inspiration? The suite icons are not centered, which looks a bit off." | REV-241 (the suite's page) | Answered: COMSOL's Model Builder, VS Code and JetBrains have no such page; a node or an icon opens a working view. Ruled (below): a suite's icon opens the tool last used in it. The folded icons sat at the top of their buttons, pushed up by the hidden name's line, and 1.5 px right of centre by the open suite's edge; both are centred |
| `shell-2wcd-m-view-settings-light` | 18 | change | "Looking better. This will still need polishing to improve layout and spacing tightness. I would suggest having a look at the settings pane of Claude Code as an example. A few details already: - The sub-titles like "Theme", "Density", etc are indented, which is not needed. - The toggles such as "Medium/Compact" etc. can be placed at the right-hand side of the subtitle + description. This will bring more structure and space efficiency." | REV-241 (the window over the view) | A setting's title and description stand flush on the left, the changed mark and *Reset to default* after the title; its control stands on the right, without a label repeating the title. The theme's and the keys' blocks stay under their text. The spacing pass with Claude Code's pane as the model is REV-237 |
| `shell-2wcd-st-charge-light` | 10 | keep | "This still looks quite strange, but let's revisit it later. Similar to the ensemble stage, perhaps we can think of creating an "overlay" view between the 3D structure, full 3D charge map, and the 2D-axisymmetric one (reduced, but then resolved again to make it pseudo-3D). To be thought about and discussed later." | REV-241 (the charge screen) | REV-240 carries the overlay of the structure, the 3D charge map and the (r, z) map turned back into 3D, for the discussion, with WP5.19's charge screen |
| `shell-2wcd-changes-light` | 12 | keep | ""Reset" could look more like a button." | — | *Reset* is an outlined button |
| `shell-2wcd-molecular-light` | 12 | change | "Same comment holds as in frame 14." | REV-241 (the suite's page) | As the folded bar's: the suite's icon opens the tool last used in it, Prepare the first time, and `/molecular` shows that tool; the page of links is gone |
| `shell-2wcd-study-light` | 88 | keep | — | — | — |

`shell-charged-tube-m-view-light` stands for the tool pages of the three states whose molecular model reads a PQR;
`shell-2wcd-study-light` for every shot that no other pick covers.

## The questions asked at the collect

- **The word for a build a check stops.** "Refused" was WB-20's and WB-12's word. Offered *blocked*, *check
  failed*, *failed* or keeping it, the author chose "Blocked" (WB-40).
- **What a suite's icon opens.** Offered the last tool, a summary page of the tools' states, or research for
  WP5.17's round, the author chose "The last tool" (WB-40).
- **The membrane in Prepare.** The membrane's centre and thickness belong to the continuum model. Offered drawing
  the study's leaflets from it, giving Prepare fields that write the continuum model, or leaving both to WP5.17's
  membrane tool, the author chose "Draw the study's leaflets" (WB-40).
- **The file picker.** A browser page cannot hand the workbench a file's path. Offered the workbench's own browser,
  the system's picker with an upload, or both, the author chose "Both": the system's picker for *Open structure…*
  now, the workbench's browser with the project dialogs (WB-40; REV-235).
- **REV-242's two points** (a model without a `structure:` block, an imported full copy's `variant_of`). The author
  chose "With the new-model action": both are settled by the later suite that adds it.
