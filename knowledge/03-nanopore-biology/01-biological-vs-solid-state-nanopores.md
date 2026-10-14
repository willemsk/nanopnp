---
type: Domain
title: 1. Biological vs solid-state nanopores
description: How biological and solid-state nanopores differ.
tags:
- biology
- domain
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 1. Biological vs solid-state nanopores

A nanopore is a 1–100 nm aperture in an otherwise impermeable membrane, forming the only liquid connection
between two electrolyte reservoirs (`cis` and `trans`) [§`sec:np:types`]. Two families:

| | Biological (BNP) | Solid-state (SSNP) |
|---|---|---|
| Material | protein (or DNA origami) | Si3N4, SiO2, Al2O3, HfO2, graphene, MoS2, glass |
| Membrane | lipid bilayer (~2.8 nm) | dielectric film, 5–50 nm |
| Fabrication | **bottom-up** self-assembly; the protein inserts itself | **top-down**: ion/e-beam drilling, lithography, dielectric breakdown |
| Reproducibility | atomically identical copies | shape varies pore to pore; Si3N4 pores "drift" by etching |
| Tunability | site-directed mutagenesis, atomic precision | coatings, size control, but destructive fabrication |
| Robustness | bilayer fragile; hours of lifetime; stochastic insertion | chemically/mechanically robust; sticky surfaces cause clogging |
| Noise | superior signal-to-noise | worse |

Atomic-precision mutability plus exact structural reproducibility is why BNPs are the target of this
codebase — and also why *predictive* modelling pays off: a mutation changes the fixed charge map, and nothing
else.

Most BNPs are repurposed **pore-forming toxins (PFTs)** — water-soluble proteins secreted by pathogens that
oligomerise on target membranes and punch holes in them [§`sec:np:types`]. Classes: **α-PFTs**, whose
transmembrane domain (TMD) is a barrel of amphipathic α-helices with tilted sidewalls (ClyA, FraC), and
**β-PFTs**, whose TMD is an amphipathic β-barrel, usually a near-perfect cylinder (αHL, aerolysin, PlyAB).
In every case the channel interior is hydrophilic and the exterior surface hydrophobic. Non-toxin channels
(MspA, CsgG, FhuA, OmpF, OmpG), engineered motors (Φ29 packaging motor) and DNA-origami pores are also used.

Terminology: **monomer** = water-soluble form; **protomer** = the same chain in the assembled pore. Pore
formation involves large conformational changes (ClyA's αA1 helix moves ~14 nm) and takes ~5 ms (αHL) to
minutes (ClyA).

