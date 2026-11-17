---
type: Test Evidence
title: "The charge check's reach against a shifted outline of 2WCD"
description: The deposit's solid share of 2WCD's built outline supplied beside its structure and shifted along z, which shifts stage 5 and the deposit's gates refuse, and how far a frame error passes.
tags:
- clya
- charge
- test-evidence
sources:
- id: wp5.19-plan
  resource: docs/plans/phase-5/wp5.19-the-study-suite.md
  title: WP5.19 plan, the Outcome under item 4
generated:
  by: claude-code/0.6.0-alpha.18
---

# The charge check's reach against a shifted outline of 2WCD

A supplied outline beside its structure runs with the structure's charge (§8.2.40 AP1). Stage 5 reads the outline
in stage 1's frame, and the deposit refuses a charge less than half of whose `Σ|q_i|` has its atom centres in solid
materials (PHY-16). REV-247 asked how far an outline drawn in another frame gets past these two checks. The author
ruled that the specification states the measured reach and adds no refusal (§8.2.42 AR5).

The case is example 07's `2wcd.case.yaml` (chains A–L prepared by example 06's `prepare.py`, the membrane 2.8 nm thick
centred at z = 0, the mesh at `size_scale: 4`). Its stage-4 outline (161 vertices, 0.0726 nm apart at the closest,
spanning z = −1.79 to 12.37 nm) is shifted along z by d, written as a profile, and supplied as `inputs.profile` beside
the structure; each case is walked to `charge`. **[verified][^wp519]**

| d (nm) | Outcome | Solid share of `Σ\|q_i\|` |
|---|---|---|
| 0 | passes | 0.979 |
| −0.5 | passes | 0.921 |
| −1 | stage 5 refuses: the membrane splits into two faces | — |
| −2 | passes | 0.735 |
| −3 | passes | 0.619 |
| −4 | passes | 0.541 |
| −5 | the deposit refuses | 0.479 |
| −8 | the deposit refuses | 0.272 |
| +1, +2, +3, +5, +8 | stage 5 refuses: no crossing of the membrane's lower face | — |

- Toward *cis* (+z), stage 5's junction gate refuses any shift that lifts the outline's foot above the membrane's lower
  face at z = −1.4 nm, so every shift above 0.39 nm. **[verified][^wp519]**
- Toward *trans* (−z), an outline shifted by up to 4 nm passes both checks with its charge displaced, the share falling
  from 0.979 to 0.541; the deposit's gate refuses from between 4 and 5 nm on. A shift of 1 nm is refused by stage 5 for
  its junction, not for its frame: the junction's geometry, not a frame check, sets it. **[verified][^wp519]**
- So the deposit's gate catches a gross frame error, such as an outline drawn in a frame several nanometres off; a frame
  error of a few nanometres toward *trans* passes. The Contour tool's saved edit is in stage 1's frame by construction.

[^wp519]: `docs/plans/phase-5/wp5.19-the-study-suite.md`, the Outcome under item 4 (measured on 17 November 2026 at
    `51f8a8f` with the shell off; each outline's provenance recomputed from its shifted vertices).
