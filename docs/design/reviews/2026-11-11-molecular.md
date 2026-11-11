# The Molecular suite's drafts on 2WCD: the author's verdicts, round 1

WP5.16's prototype round (§8.2.34 AJ8): the five Molecular tools drafted on the 2WCD dodecamer, from the render
`shell-d5995eb` at `d5995eb`, 154 shots, light and dark, in five states with a build refused and a build running.
They were published as a digest of 14 picks at `https://claude.ai/artifact/HRDfKwmg4WRYnowGuVB51g`. The verdicts
were collected on 11 November 2026.

The author marked all 14 picks: 6 `keep`, 8 `change`, no `drop`. Four of the keeps carry a note that asks for
something. Three questions were the author's to decide and were asked at the collect (below): how far the charge
colours switch, what the channel's straightness limit does, and what the folded bar shows. WP5.16's finishing item
(item 11) acts on the tools' notes; the notes on screens of other packages, and the three that the author marked
for more discussion, are REV-240, with REV-234, REV-235 and REV-237 brought up to date. *Stands for* counts the
shots a pick's verdict covers (`digest.json` beside the page lists them). *Reviewer finding* names the finding,
`F1` to `F25`, of the GUI review of the drafts at `a6b9ae5`. Notes are the author's words.

| Pick | Stands for | Verdict | Note | Reviewer finding | Disposition |
|---|---|---|---|---|---|
| `shell-2wcd-m-prepare-light` | 2 | keep | "- Pane on the left is OK, but color contrast is poor. - Point group: sure. Where else can it be placed? - Main button: Can we not have both side-by-side? General remark: buttons and fields look somewhat space-inefficient." | F1, F7, F8, F25 | Item 11: the pane's labels and read-outs in the text ink, not the quiet one, and the drafted controls live, no longer greyed; *Save prepared structure* and *Build ensemble* side by side; the fields and buttons in Quasar's dense form, a label beside a short field. Answered: the point group is a value of the structure, so the other place for it is the model's own header; it stays in Prepare, beside the axis it rules |
| `shell-2wcd-m-ensemble-light` | 2 | keep | "Maybe for an ensemble we can think of 3 different "views": - single frame - selected/all together - a "B-factor" heatmap structure that represents the variation. These are just what pop into my head at the moment, maybe needs a bit more discussion and research." | F9 | Item 11: one frame, or the frames overlaid. REV-240: the variation drawn on the structure, for the discussion the note asks for |
| `shell-2wcd-m-protonation-light` | 2 | change | "- Colormap: in biochemistry, blue is positive and red is negative. Of course, perhaps we can built-in support for custom colormaps - Counts and warnings: perhaps clicking on them could yield a pop-up to view the counts/warnings and act on them if meaningful?" | F10, F12, F17 | Ruled (below): positive is blue and negative red on every charge and potential display, with a setting for the direction. Item 11: the switch and the setting; each count opens a window that lists its residues or warnings, a row selecting its residue. REV-240: maps beyond the two directions (WB-20's "user-chosen maps") |
| `shell-2wcd-m-edit-light` | 2 | keep | "Main button: same as for the other, why not both side-by-side?" | F13 | Item 11: *Save as variant…* and *Build* side by side |
| `shell-2wcd-m-view-dark` | 2 | change | "I guess the build button has no real function here?" | F11 | Item 11: View has no build button; it shows what is built and names the tool that builds what is missing |
| `shell-molecular-refused-light` | 2 | change | "Maybe the refusal could be a more defined "card" or "button" tooltip with minimal info always visible, and full info when you hover over it? Or maybe even "Resolve"/"Ignore" buttons?" | F16 | Item 11: a refusal is a card with the gate's name and the measured value always shown, the full text unfolded on demand (a click or the keyboard, since a hover alone fails WB-24), and a *Go to field* button. Answered: a gate cannot be ignored, so the card offers no *Ignore*; a warning, such as the straightness one ruled below, is the card's quieter form with *Dismiss* |
| `shell-molecular-building-light` | 2 | change | "Stage + progress. Maybe a nice bar at the top with blocks per stage, and a progress bar below for the running step? Think about a few options to make it look more professional and sleek. Perhaps cancel should indeed be a bit different so you are not inclined to push it by accident. How do other GUIs handle this kind of situation? Maybe the progress bar could be in the Main button, and the cancel button a smaller one next to it? Finally, does pressing cancel result in direct stop, or is there a second pop up safeguard? Not sure this cancel needs that per se, but it is good to think about such safeguards in general for the program (kind of like the danger zone in GitHub)." | F18, F19 | Item 11: a bar of one block per stage at the pane's head, each with its state's glyph and word (WB-20), and under it a thin bar for the running stage, moving without a percentage where the walk reports none (WB-23); while a build runs the main button is disabled and reads the stage, and a small quiet *Cancel* stands beside it. Answered: VS Code, JetBrains and COMSOL stop a run at once from a small secondary control and keep what finished; a build here does the same, since each finished stage is already in the store and a cancelled one costs only its own time. REV-240: one rule for the safeguards of actions that lose work (deleting a model, clearing the store), for the author |
| `shell-empty-m-prepare-light` | 10 | keep | — | F24 | — |
| `shell-charged-tube-m-prepare-light` | 30 | keep | "This is fine for now. I don't immediately see a better option." | — | — |
| `shell-2wcd-st-charge-light` | 10 | change | "Pane to the left. Consistency is key. I don't think the current implementation of this tool is very scalable or intuitive. It just looks like a list of residues. What does clicking on one do? Let's think about a more streamlined version." | — | Ruled: every tool's pane is on the left of its view. Item 11 moves the charge screen's view to the right of its pane (REV-234). Answered: a click on a residue selects it in the 3D view and shows its row; nothing else. REV-234 carries the streamlined charge tool to WP5.19, whose screen it is |
| `shell-2wcd-molecular-light` | 10 | change | — | F1 | Item 11: the tool list stands beside every tool's pane, each tool with its state, as the card proposed; the suite's page stays as the list alone |
| `shell-2wcd-changes-light` | 10 | change | "Let's also try a shorter list version. The current table still takes up a lot of real-estate. How do other GUIs handle this typically?" | — | Answered: VS Code lists the modified settings as the settings list filtered by `@modified`, one line each; JetBrains marks a changed value in its place and filters with *Show modified only*; COMSOL has no list. Item 11 gives each pane its marks and *Modified only*. REV-237: a one-line-per-value list to set beside the table at the next round |
| `shell-2wcd-settings-light` | 10 | change | "Window over the tool. When working, I don't want to navigate away from the tool to change a setting." | — | Ruled: the settings open as a window over the tool. Item 11 |
| `shell-2wcd-study-light` | 154 | keep | — | — | — |

`shell-charged-tube-m-prepare-light` stands for the tool pages of the three states whose molecular model reads
a PQR; `shell-2wcd-study-light` for every shot, as the frame's round left the other screens.

## The questions asked at the collect

- **How far the charge colours switch.** The 3D view and every 2D map of charge and potential drew negative blue
  and positive red. The author: "Everywhere, and choosable". Positive is blue and negative red in the 3D view, on the
  charge map and in the potential figures, and a setting picks the direction.
- **The channel's straightness limit** (REV-239). It rests on 2WCD alone, and a monomeric pore is likely to exceed
  it. The author: "Warn, do not refuse". Above the limit the build goes on and reports the measured value
  (§8.2.39 AO4).
- **The folded bar** (REV-237). The author chose icons with state: folded, the bar is a strip of the suites'
  icons, the open one marked, a dot on a suite with a problem or a running build, each named on hover and focus.
