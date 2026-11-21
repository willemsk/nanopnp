⚠️ DEGRADED: single-context (no sub-agent tool here). The 1440 renders were read; no browser overlay, no snapshot, repository unedited.

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Status | 3 | Shown-run head and chips are clear |
| 2 | Real world | 3 | "the library" in L1's LACKS can be read two ways |
| 3 | Control | n/a | Not drawn |
| 4 | Consistency | 2 | ◆ has two meanings; mV against V |
| 5 | Error prevention | 2 | A collapsed node hides a changed value |
| 6 | Recognition | 2 | T3 nests results four levels deep |
| 7 | Flexibility | 3 | Tiles, probes, cut |
| 8 | Minimalist | 3 | T1/T3 colour bar sits 250–350 px from its map |
| 9 | Recovery | n/a | Not drawn |
| 10 | Help | 3 | Captions state each model |
| **Total** | | **21/32** | **Acceptable** |

**Specificity:** made for this product: real 2WCD fields, positive blue (WB-39), dark middle (WB-49), the accent edge, Inter (WB-21). **Detector:** 65 findings, 55 advisory and 10 warnings (flat type hierarchy; h1→h3 skips in L1, L2, P1). 12px and 12.5px are token steps, so false positives. The 4px radii are real drift. It caught none of the issues below.

**Working:** every board uses one solved dataset. L1/L2's licence/size/draws/lacks strip makes the libraries comparable. A ring marks the shown run on the I–V.

**Priority issues**

1. **[P1] T2's pin is WB-28's changed mark.** `.node .pin` is a filled ◆ in `--changed`, so "Current against bias" reads as changed. "Pinned" also means two things: pinned to a run, and "pinned groups stand as tiles", but tiles 1–2 are not pinned. *Fix:* the pin gets its own glyph and one meaning.
2. **[P1] Uneven staging favours T2.** T2 draws three plots, T1 and T3 one each. T3's map has no probes or cut. T2 hides the bottom panel, so its probe values (WB-51) never show. T2's axis tile overlays ASP-neutral, but its caption says "Comparison stays a tool of its own". *Fix:* the same map options and bottom panel on all three; name T2's second run's source.
3. **[P1] L2 compares settings, not libraries.** Its log axis runs 10–1000 and flattens the cut (Plotly's runs about 55–230). It shows "−19.71/19.71" end labels and axes through zero. It has no shown-run ring (draw.js 140–146 against 258–259). With no outline or solid fill, membrane and protein merge with zero-potential fluid, worst in dark; LACKS omits this. *Fix:* match L1's bounds, ring and outline, or list each gap. Plotly also has a margin fault: "current (nA)" hits the −0.05 tick (L1, T2).
4. **[P2] Units contradict on every T board.** The settings and probes say mV; the colour bar and the axis plot say V. WB-20 says a map carries its unit.
5. **[P2] P1 has misreadings.** The pressure tick "0.8M" reads as molar. The point graph is drawn in `--warn`, a status colour that is ASP-neutral in the next plot. Contours is a half-domain sliver; Scatter and Mesh are text only.

**Personas.** Alex: T1 compares groups only by clicking. Sam: L2 dark loses the geometry.

**Minor.** Trees and tables clip rows mid-glyph.

**Questions**
1. Give T1–T3 the same content before the author picks? (Yes / Note it in the digest)
2. L2: redraw it to match, or list each gap? (Redraw / List)

A newer Impeccable (v4.10.0) is available. Update now? It runs `npx impeccable update`.
