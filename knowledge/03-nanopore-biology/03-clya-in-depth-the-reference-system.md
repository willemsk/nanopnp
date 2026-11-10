---
type: Domain
title: 3. ClyA in depth — the reference system
description: ClyA, the reference system, and the ClyA-AS variant series.
tags:
- biology
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 3. ClyA in depth — the reference system

ClyA is the pore the ePNP-NS framework was validated against. It is a large α-PFT from *S. enterica* / *E.
coli* (also called HlyE), whose dodecameric pore structure Mueller et al. resolved in 2009 (2WCD)
[§`sec:np:clya`] **[verified][^thesis]**.

- **Quaternary structure:** 12 identical protomers in a ring → **C12 symmetry**. The pore walls facing the
  solvent are a bundle of four tightly packed α-helices per protomer; the TMD is an iris-like arrangement of
  the amphipathic N-terminal α-helices. ~2400 Å² buried, 25 H-bonds and 13 salt bridges per protomer–protomer
  interface **[verified][^thesis]**. C12 is what licenses the **2D-axisymmetric reduction** of the full 3D structure used in the
  simulations [transport.tex] **[verified][^thesis]**.
- **Geometry:** two stacked hollow cylinders — a wide **cis lumen** and a narrow **trans constriction**. Two
  slightly different dimension sets appear in the thesis and both are correct in context:

  | | cis lumen ⌀ | lumen height | trans constriction ⌀ | constriction height | total length |
  |---|---|---|---|---|---|
  | Structural (§`sec:np:clya`) | 5.5 nm | 10 nm | 3.6 nm | 4 nm | 14 nm (11 nm outer ⌀) **[verified][^thesis]** |
  | Simulation model (transport.tex) | 6 nm | 10 nm | 3.3 nm | 4 nm | 14 nm **[verified][^thesis]** |

  Use the **simulation values** when reproducing published results; the geometry actually used comes from the
  25% contour of a radially averaged atomic density map — see `knowledge/04-clya-geometry-and-charge/index.md` for the exact
  axial extents, charge clusters and bias sign convention.
- **Charge:** ClyA carries about **−60 e at pH 7.5** (`nanopores.tex`), most of it lining the interior **[verified][^thesis]**. The ClyA-AS
  model of the validation integrates to −72 e (−72.9 e on the COMSOL mesh; ruling 8,
  `knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md`). Consequences: negative potential
  throughout lumen and constriction, **cation selectivity**, a positively charged EDL, and therefore a strong
  EOF that can capture proteins against the electric field. The constriction is the most negative region and
  stays so even at 2.5 M, where the rest of the pore screens to ~0 kT/e.
- **Sidedness:** `cis` is the reservoir the pore is added to and is grounded; `trans` carries the bias. ClyA's
  wide lumen is on the cis side, the constriction on the trans side.

### ClyA-AS and the variant series

**ClyA-AS** is a directed-evolution variant of *S. typhi* wild-type ClyA selected for improved
electrophysiological stability (Soskine 2013). It is the variant used in essentially all the experimental
work and in the ePNP-NS validation — **not** wild type. Watch out for two different mutation lists:

- `myglossary.tex` defines ClyA-AS relative to ***S. typhi* wild type**: C87A, L99Q, E103G, F166Y, I203V,
  C285S, K294R, H307Y (8 mutations) **[verified][^thesis]**.
- `electrostatics.tex` §`sec:elec:methods:molec` lists **27** mutations (Q8K, N15S, Q38K, A57E, T67V, C87A,
  A90V, A95S, L99Q, E103G, K118R, L119I, I124V, T125K, V136T, F166Y, K172R, V185I, K212N, K214R, S217T,
  T224S, N227A, T244A, E276G, C285S, K290Q) — these convert the ***E. coli*** crystal structure (2WCD) into
  *S. typhi* ClyA-AS. They cover five of the eight AS mutations (K294R lies in the unresolved 293–303
  stretch; H307Y is past it; I203V is absent, unexplained), and they contain Q8K, which ClyA-RR₅₆K adds
  again on the ClyA-AS background **[verified][^thesis]**.

That inconsistency is open (OPN-04). **Any structure-preparation pipeline must record which list it
applied and to which PDB.** Also note the model adds a residue: 2WCD lacks residues 1–7 and 293–303 per
chain, and a single negatively charged Glu7 was added back at the trans entry because that region matters
electrostatically.

Engineered variants (all on the ClyA-AS background), used to make ClyA translocate DNA at physiological salt:
**ClyA-R** (S110R, cis entry), **ClyA-RR** (S110R/D64R, mid-lumen), **ClyA-RR₅₆** (S110R/Q56R),
**ClyA-RR₅₆K** (S110R/Q56R/Q8K, constriction). Of >20 variants tested experimentally, only **ClyA-RR**
translocated dsDNA at 0.15 M, and only from cis — D64R is a charge *reversal* (+2 e) that flips the mid-lumen
potential from −0.32 to +0.20 kT/e, while Q56R (+1 e) only slows the rise.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.
