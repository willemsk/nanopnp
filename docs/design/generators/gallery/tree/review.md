## Review of the REV-268 / WP5.22 tree-round boards (render tree-6186208)

I read all 24 PNGs, `index.json`, `change.diff`, the six board HTML files and `draw.js`. I also read parts of `data.js`, `generators/tree/extract.py`, `workbench.md` (WB-01 to WB-53, the frame, the live links and the artefact rule), REV-268, S6 and S7, and NiceGUI 3.18's bundled package metadata. I edited no file.

### Bottom line
- **Screen space (WB-51):** T2 answers the author's complaint best. T1 comes close behind. T3 does not answer it.
- **The job:** no board can finish it as drawn. T2 cannot show a Na+ value at a probe at all.
- **Boards that would mislead the author's choice:**
  - Every map now drops φ inside the protein and membrane, and its colour range changes from today's ±155 mV to ±63 mV. Nothing on any board says so.
  - P1's Difference plot is a number the browser computes, which no artefact supplies.
  - L2 is configured worse than L1 in ways that are not ECharts' fault.

### The job, board by board
Job: "open the latest run of the 2WCD study, place a probe at the constriction, read Na+ there, compare with the ASP-neutral variant along the axis, read the current against bias."

One break is common to all three boards. No board marks which run is the latest: no date, no order. Runs are named "+50 mV · run 394c…", which still uses the hex name REV-268's critique point 5 asked to drop. Step 1 therefore depends on knowledge the screen does not give.

**T1** (about 7 to 8 clicks, partly inferred):
1. Data › Shown run. The run select is not drawn.
2. Graphics head **• Probe**, then a click on the map. The constriction is not marked. At 1440 the map is about 14.6 px/nm, so a click cannot place a probe to 0.01 nm. Whether the r and z cells of the Probes table can be typed in is not shown.
3. Bottom panel › Probes › c Na+ (mM) gives P1 = 165.0. This works. It holds only if P1 at (0, 0) is the constriction, and the board does not say so.
4. Plot groups › Along the axis, then its data set to "ASP neutral vs charged" and its expression set to Na+. Neither setting is drawn. At 1280×800 this node has scrolled out of the tree.
5. Plot groups › Current against bias. Only one plot group is drawn at a time, so the cut and the I–V are never seen together.

**T2:**
1. The Shown run select at the head of the pane.
2. **• Probe**, then a click on the map.
3. **Breaks.** No probe values appear anywhere. The bottom panel has only Queue and Log, Probes is a folded branch "2", and the map shows φ.
4. The Along the axis tile already shows both runs, but for φ. Selecting its node and changing the expression takes 2 clicks. Where its second run is set is not shown.
5. The I–V tile is already on screen: 0 clicks.

**T3:**
1. Rail › Studies › 2wcd › Runs, then pick a run. It is ambiguous whether the Results node's "+50 mV" or Surface's own Run field governs which run is shown.
2. **• Probe**, then a click. The map draws neither the existing probes nor the cut.
3. Bottom panel › Probes tab (1 click). The table itself is not shown.
4. **Breaks.** The rail item "charged-against-neutral" has no children, and nothing shows how a two-run axial line is made.
5. Rail › Results › Current against bias (1 click).

### Confirmed findings: all three organisation boards (T1 to T3)
1. **Major. Boards misrepresent the map (WB-53 "map drawn over the whole domain"; WB-49/50 percentile).**
   - `extract.py:_grid` now masks φ to the fluid's cells. φ inside the protein and membrane is not drawn, and "Range from the 99th percentile" reads −63.0 … 63.0 mV, where today's explorer gives ±0.155 V over all values (`gui/web/analysis.py:_scale`).
   - The diff also opens one-signed fields on their 1st to 99th percentile (`spread`). The shipped explorer uses min to max (`_scale` line 353), and no ruling sets this.
   - Only P1's uncommitted working-tree caption says "φ in the fluid". The render is of 6186208 and does not carry it.
   - Proposed change: put both rules to the author as options, or revert them. Label the boards "φ in the fluid".
2. **Major. S6 link 4 / WB-06 missing.** None of the boards has *Open in Runs*, or says that a point of the I–V opens its run. Today's explorer has *Open in Runs*.
   - Proposed change: draw it in each option's graphics head.
3. **Minor. The Unit setting is not honoured (Nielsen 4, consistency).** Unit reads "mV" and Range reads "−63.0 … 63.0 mV", while the colour bar and the axial plot read "potential φ (V)", ±0.06.
   - Proposed change: draw in the unit the setting names.
4. **Minor. Numbers break WB-21.** "current 0.04799 nA" and "currents (Na+) 0.02602 nA" should read 47.99 pA and 26.02 pA. The I–V axis ticks (0.05, −0.15 nA) have the same problem. The strings come from `quantity_rows`, so the shipped explorer shares the defect.
5. **Minor. The colour bars drop the clipping cue.** They read ±0.06 with no ≤ or ≥ at the ends and no "beyond, the end colours" note, although the range clips at the 99th percentile (WB-49).
6. **Minor. Reflected maps are unlabelled.** On T1, T2 and T3 the left half reflects the same run (`reflect: true`) and carries no "reflected" label. P1 uses the same layout for *Mirrored*, with neutral on the left, so a user doing the job's step 4 can read the left half as the ASP-neutral run.
   - Proposed change: label the left half "reflected", or grey it.
7. **Minor. Settings boxes truncate:**
   - T2: "Diverging, positive blu", "◆ Bias swee…".
   - T3: "Diverging, positive", "+50 mV · run 394c".
   - T1 at 1440: the "Charged against neutral" row is cut in half under the settings, with no scroll cue.
8. **Minor. Hand-typed chrome numbers disagree with the project.**
   - "◆ 3 changed" on the boards against "4 changed" in today's explorer.
   - T3 names the study "2wcd", where `data.js` and today's rail say "2wcd-charged".
   - The probe markers are hard-coded in `draw.js` at r = 0.02 and (1.2, 3). They are not read from `TREE.probes`, which puts P1 at r = 0.00.
9. **Minor. Contrast not measured and legibility poor.** The P1 and P2 labels are SVG text in the accent colour over the map and the contours. `index.json` lists them as `unmeasured` ("svg text"). At 1440 they are hard to read.

### T1 (COMSOL's branches)
- **Major. The frame changes without saying so (`workbench.md` *The frame*, WB-02/WB-45).** The bottom panel, defined as the queue and the log folded to one line, becomes about 150 px of Probes, Quantities and Cut values tables. That takes height from the graphics. Either the caption says it amends the frame, or the tables move.
- **Major (for the job). One plot group at a time.** Today the tiles show the field and the I–V together. In T1 the user must remember values across switches (Nielsen 6, recognition rather than recall).
- **Minor (WB-07).** The tool list disappears. Comparison folds into Data, which amends WB-07 for Analysis. Fine if the author rules on it; the caption half-says it.
- **Minor.** The R, S, C and 3 glyphs on the Data nodes are unexplained (Nielsen 6). The **✕** in "Linked: probes and cut ✕" is the only Unlink control and carries no label (WB-22).
- **What works:**
  - WB-06/S6 link 3 is drawn: the probes and cut on the map, the chip with Unlink, and the probe rows below.
  - Probes have a pane of their own (WB-51). Quantities read "6 of 15 shown", which `data.js` confirms with 15 quantities.
  - Charts sit above the numbers (WB-53).

### T2 (one shown run, tiles)
- **Major. Overloads the changed-from-default mark (WB-28).** The filled ◆, in the same teal as "◆ 3 changed", means "pinned to its own run" in T2. WB-28 reserves the filled diamond for a changed value and keeps it off the accent.
  - Proposed change: use a pin glyph.
- **Major. The caption misstates the option's mechanism.** "The pinned groups stand as tiles" is wrong. Only Current against bias is pinned. Tiles 1 and 2 follow the shown run, and the tile count is set by shown or hidden groups ("3 of 5 plot groups shown").
- **Major. Hidden state and missing probe rows (WB-32; WB-51; S6 link 3).**
  - Along the axis draws "φ, two runs", but no node or setting shows where the second run comes from. This also contradicts the caption's "Comparison stays a tool of its own".
  - No probe rows and no quantities appear anywhere, which breaks the job's step 3 and WB-51's "quantities shown chosen".
  - The map tile carries no linked chip and no Unlink (WB-06).
- **Major (WB-07).** "Comparison stays a tool of its own", but no tool list is drawn, so there is no route to it.
- **Minor (WB-53 order).** The tiles run field, cut, then I–V. WB-53 orders them field, I–V, then cut.
- **Doubt.** One Shown run select silently changes every unpinned group. That is a wide-reach control WB-32 wants guarded.

### T3 (one project tree)
- **Major. The rail has a dual role (WB-36; WB-39's folded rail).** Analysis depends on the rail being unfolded to 260 px. Folded, as WB-36 and WB-39 allow, Analysis keeps a settings column and no way to pick a node. The board does not show the folded state, and the plot nodes would also clutter the rail in every other suite.
- **Major. S6 link 3 missing.** The map draws neither the probes ("Probes 2") nor the cut, and has no linked chip.
- **Major (job step 4).** The comparison is a rail leaf with no plot groups, and how it reaches an axial line is undrawn.
- **Minor.**
  - CSS uppercase turns "(r, z)" into "SURFACE · POTENTIAL (R, Z)".
  - The quantities table spans the full width, value column at about x = 1160, so the eye travels far (Gestalt proximity).
  - "Quantities 6" here against "6 of 15" in T1 and T2.

### P1 (plot types)
- **Major. A number no artefact supplies (design doc's artefact rule; QR-13).** *Difference* is computed in the browser by `draw.difference()`, which its own comment calls "a board's stand-in for the library's difference". The board does not say so. WP5.21's Comparison already has a library difference to read.
- **Major. *Contours* cannot be read.** It draws coloured lines with no colour key and no labels (`showscale:false`, no `contourLabels`), on a narrow strip from r = 0 to 8 nm. It is not a fair picture of the plot type.
  - Proposed change: add labels or a key.
- **Minor.**
  - *Arrows* has no magnitude key; arrows are normalised to the largest speed.
  - *Revolution*: the 3D z title renders reversed ("(ɯu) z") and the top tick "20" is clipped.
  - The 3D range is computed from `T.revolved`, not from the map. WB-50 says the 3D view opens on the map's colour range: L2 reads ±0.061 against the map's ±0.063.
  - Data series use the semantic `--info` and `--warn` colours, overloading WB-42's status colours.
  - Units are mol/m³ here and mM in T1.
  - "Export … FR-28, v0.7": FR-28 says figures are FR-44's, which is v0.5 and command-line only.
- **RSK-15 doubt (T1, T2).** *Definitions* ("ρ_e = F·(c_Na − c_Cl)", "|u|", with ＋) does not say whether expressions are typed, which would need an evaluator no tier verifies, like the composer's typed equations, or picked from a library registry. The library has no such function yet. REV-268 requires "in the library, never in the shell". Put this to the author explicitly.

### L1 / L2 (chart libraries)
- **Major. L2 is shown at a disadvantage L1 does not share, which misleads the library choice:**
  - Its log cut axis is left at the default 10 to 1000, against L1's fitted 55 to 230, so the two-run difference looks flattened. ECharts takes min and max on a log axis.
  - Its I–V has no ring on the shown run; L1's has one.
  - Its map draws no fill for the solids. On light, white beside the #f7f7f7 middle, and on dark, background beside the #20232a middle, the protein and membrane cannot be told from fluid near 0 V. "Lacks" does not list this, and I believe a second heatmap series or visualMap could draw it (doubt).
- **Minor. L2's version and licence claims disagree with NiceGUI.** NiceGUI 3.18 ships echarts-gl **2.1.0** (`nicegui/elements/echart/package-lock.json`), not the 2.0.9 the board loads from the CDN. The same lock records its licence as **MIT**, not BSD-3-Clause (doubt: npm metadata). ECharts 6.1.0 and Plotly 3.1.1 are confirmed (`plotly/dist/index.js`).
- **Minor (L1).**
  - The Plotly 3D faces are shaded by lighting, so fluid near 0 V reads grey against a white bar middle.
  - The map's colour bar sits about 200 px from the map (proximity).
- **WCAG evidence (all from Plotly's own mode bar, as you noted).**
  - Targets measure 24 × 22 on every Plotly board, under 2.5.8's 24 × 24 minimum. Doubt: 24 px centre spacing in a row may pass under the spacing exception.
  - The dark focus ring measures 1.29:1 (#000000 on #1c2027) against the 3:1 that 1.4.11 and WB-24 require. This is confirmed on every dark Plotly board.
  - L2's `targets`, `nontext` and `unmeasured` are all empty. ECharts draws to canvas, so nothing was measured; it did not pass. The boards are not comparable on accessibility, and ECharts' keyboard access is untested.
- **CON-09.** No breach. Plotly (MIT), ECharts (Apache-2.0) and echarts-gl are permissive and shipped inside NiceGUI. The renderer table and REV-137's one-renderer rule must change: P1 keeps webgui for *Mesh* while Plotly would draw the maps, and the canvas map renderer would retire. The boards do not say so.

### WB-51 (screen space at 1440)
| | Left of the plots | Plot area | Bottom panel | Plots on screen |
|---|---|---|---|---|
| Today | about 66% of 1280 | | | |
| T1 | about 396 px | about 1044 px | about 150 px used | one |
| T2 | about 386 px | about 1054 px | folded | three |
| T3 | about 596 px (rail 260 + settings 270) | about 844 px | about 160 px | one |

T3's settings column is half empty. T2 is best on screen space and chart count. Its cost is the missing probe and quantity tables, the second run's hidden source and the ◆ clash.

### What I could not check
- Text contrast is unchecked: `contrast` is empty on every shot, Plotly text is `unmeasured` and ECharts canvas text is not listed at all.
- The boards' own controls (`.btn` spans, tree rows) are not buttons, so their targets and focus were not measured.
- The physics values (165 mM, 0.96 nS) can't be judged against a reference.
- The bundle sizes (4.8 MB, 1.1 + 0.6 MB) are unchecked.
- I ran no git, so I could not confirm that the working-tree edit to `p1-plot-types.html` line 28 ("φ in the fluid") is uncommitted. The render predates it either way.
- Whether a Plotly mode bar button has an accessible name is unchecked.

### Files
- `/home/user/nanopnp/docs/design/concepts/tree/draw.js`: `difference()` line 285; `spread` line 33; the hard-coded probes line 102; `findIndex(... === 50)` line 141.
- `/home/user/nanopnp/docs/design/generators/tree/extract.py`: the fluid mask, lines 54 to 57.
- `/home/user/nanopnp/docs/design/concepts/tree/t1-comsol-branches.html`, `t2-shown-run.html`, `t3-project-tree.html`, `p1-plot-types.html`, `l1-plotly.html`, `l2-echarts.html`
- `/home/user/nanopnp/src/nanopnp/gui/web/analysis.py`: `_scale`, lines 335 to 353.
- `/home/user/nanopnp/.venv/lib/python3.14/site-packages/nicegui/elements/echart/package-lock.json`: lines 924 to 946.
- `/tmp/claude-0/-home-user-nanopnp/10245948-6d00-57fa-97d4-4cba3d4aeeb3/scratchpad/gui-render/tree-6186208/index.json`
