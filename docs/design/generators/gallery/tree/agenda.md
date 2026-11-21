# The tree of results: the round's assumptions and agenda (WP5.22, REV-268)

Inputs read: REV-268 (and the critique's five points, WB-53's two), REV-267's chart points, REV-270,
WB-05 to WB-07, WB-17 (COMSOL's plot settings in Analysis), WB-32 (no hidden state), WB-36 (the
rail), WB-50 to WB-53, the Analysis rounds' verdicts (2026-11-20, rounds 1 and 2), P1 to P3, S2,
S6 (FR-33), FR-32's project folder, AU1 (uPlot), REV-137 (one renderer per kind of picture),
RSK-15 and QR-13 (the shell computes no number), FR-28 (figure export, v0.7).

## Assumptions the inputs leave open

1. Whether the data a plot draws is a branch of its own (COMSOL's datasets: a run, a sweep, a
   comparison, a cut, a revolution) or a property of each plot, with one run shown for all.
2. Whether Comparison stays a tool beside the tree, or becomes a kind of data in it.
3. Where the tree and a node's settings stand: the tree in the tool list's place, the node's
   settings under it or beside it; and how many plot groups are drawn at once.
4. Which plot types v0.6 offers, each needing a library function Tiers 1 and 2 verify (RSK-15).
5. Which chart library draws them, whether it also takes the (r, z) maps from the hand canvas and
   uPlot's plots elsewhere (Electrolyte, Runs), and whether its own image export is shown before
   FR-28 (v0.7).
6. How a variable or constant is written, and where it is computed: in `post/`, at the sampled
   points (QR-13; REV-270), never in the browser.
7. Where the probes, the cut's values and the quantities stand ("a pane of their own, like in
   COMSOL"), and how the quantities shown are chosen and ordered.
8. How the tree is saved in the project (FR-32): one file, or one file per plot group; what
   happens to `comparisons/*.yaml`.
9. How the links meet the tree (WB-06; FR-33): a click on a map moves a probe or a cut node; a
   run's *Result* opens which node.
10. A new run's tree: what is drawn before the user builds anything (COMSOL's default plots), for
    P3.
11. Two runs in one view (Mirrored as the model) and a run's name by sight ("+50 mV, ASP21N").

## Agenda, the points that change others first

| # | Point | Feeds |
|---|---|---|
| 1 | The tree's branches: data as a branch, or one shown run; Comparison folded in or kept | 2 to 11 |
| 2 | Where the tree and the settings stand; plot groups shown one at a time or several | 7 |
| 3 | The plot types v0.6 offers | 5, the package's library steps |
| 4 | The chart library, and its reach (maps, other suites, export) | REV-267's chart points, WP5.24 |
| 5 | Variables and constants: how written, where computed | the library step |
| 6 | Probes, cut values and quantities: their pane; choosing and ordering the quantities | — |
| 7 | Saving: the tree's file(s); comparisons' files | FR-32 |
| 8 | The links in the tree | FR-33 |
| 9 | The default tree a run opens with | P3's route (WP5.27) |
| 10 | Two runs in one view; a run's name by sight | — |
