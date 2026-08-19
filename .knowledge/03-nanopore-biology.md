# Nanopore biology and electrophysiology — what the model is a model *of*

**Status:** background. Source: CC-BY-4.0 thesis `willemsk/phdthesis-text`,
`chapters/nanopores/nanopores.tex` (ch. 2), with structural/experimental details from
`chapters/electrostatics/electrostatics.tex` (ch. 4), `chapters/transport/transport.tex` (ch. 6) and
`myglossary.tex`. Items marked **[std]** are general background the thesis does *not* state.

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

## 2. The pores that appear in this work

| Pore | Class | Oligomer | Mass | Overall shape | Interior | Charge / selectivity | PDB |
|---|---|---|---|---|---|---|---|
| **αHL** (α-hemolysin, *S. aureus*) | β-PFT | **7** (>90% heptamer) | 232 kDa | mushroom, 11 nm tall × 10 nm wide; 4 nm β-barrel stem | cis vestibule 3.5 nm entry × 5 nm; 6 nm long × 2 nm channel; **1.6 nm constriction** (Glu111/Lys147) | balanced; slightly **anion**-selective | 7AHL (pore), 4YHD (monomer, 33 kDa) |
| **ClyA** (cytolysin A, *E. coli* / *S. typhi*) | α-PFT | **12** (also 13, 14) | 408 kDa | cylinder, 14 nm tall × 11 nm outer | cis lumen ⌀5.5 nm × 10 nm; trans constriction ⌀3.6 nm × 4 nm | **−60 e** at pH 7.5, mostly on interior walls; **cation**-selective | 2WCD (E. coli 12-mer), 6MRT (Peng 2019), 1QOY (monomer, 34 kDa) |
| **FraC** (fragaceatoxin C, *A. fragacea*) | α-PFT | **8** (also 7, 6) | 176 kDa | funnel, 7 nm tall; outer ⌀11 nm (cis) / 3.5 nm (trans) | ⌀6 nm cis → **1.6 nm trans constriction** | negative interior, esp. constriction; **cation**-selective | 4TSY (with 3 sphingomyelins/protomer), 3VWI (monomer, 20 kDa) |
| **PlyAB** (pleurotolysin AB, *P. ostreatus*) | β-PFT, MACPF | **13** subunits, each (PlyA)₂·PlyB → 39 chains | 1067 kDa | mushroom, 13 nm tall; head ⌀22 nm, stem ⌀9 nm | cis entry ⌀10.5 nm → **5.5 nm constriction** at 3 nm depth → lumen ⌀7.2 nm × 10 nm | predominantly negative | 4V2T (Cα only), 4OEB/4OEJ (monomers) |
| **MspA** (*M. smegmatis* porin A) | β-barrel porin | octameric **[std]** | — | — | narrow constriction **[std]** | — | — |
| **Aerolysin** (AeL, *A. hydrophila*) | β-PFT | heptameric **[std]** | — | — | — | — | — |
| **CsgG** (*E. coli*) | β-barrel | — | — | — | — | — | — |

The thesis gives no dimensions for MspA, aerolysin or CsgG; it cites MspA and CsgG as the pores behind
commercial DNA sequencing. Sub-stoichiometries matter: FraC 8/7/6-mers have constrictions of 1.6 / 1.1 /
0.84 nm; ClyA Type I/II/III (12/13/14-mer) have 3.3–4.0 / 3.7–4.4 / 4.2–5.2 nm; PlyAB is 75% 13-mer.
**Any simulation must state which oligomer it models.**

## 3. ClyA in depth — the reference system

ClyA is the pore the ePNP-NS framework was validated against. It is a large α-PFT from *S. enterica* / *E.
coli* (also called HlyE), first crystallised by Mueller et al. 2009 [§`sec:np:clya`].

- **Quaternary structure:** 12 identical protomers in a ring → **C12 symmetry**. The pore walls facing the
  solvent are a bundle of four tightly packed α-helices per protomer; the TMD is an iris-like arrangement of
  the amphipathic N-terminal α-helices. ~2400 Å² buried, 25 H-bonds and 13 salt bridges per protomer–protomer
  interface. C12 is what licenses the **2D-axisymmetric reduction** of the full 3D structure used in the
  simulations [transport.tex].
- **Geometry:** two stacked hollow cylinders — a wide **cis lumen** and a narrow **trans constriction**. Two
  slightly different dimension sets appear in the thesis and both are correct in context:

  | | cis lumen ⌀ | lumen height | trans constriction ⌀ | constriction height | total length |
  |---|---|---|---|---|---|
  | Structural (§`sec:np:clya`) | 5.5 nm | 10 nm | 3.6 nm | 4 nm | 14 nm (11 nm outer ⌀) |
  | Simulation model (transport.tex) | 6 nm | 10 nm | 3.3 nm | 4 nm | 14 nm |

  Use the **simulation values** when reproducing published results; the geometry actually used comes from the
  25% contour of a radially averaged atomic density map — see `04-clya-geometry-and-charge.md` for the exact
  axial extents, charge clusters and bias sign convention.
- **Charge:** net **−60 e at pH 7.5**, most of it lining the interior. Consequences: negative potential
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
  C285S, K294R, H307Y (8 mutations).
- `electrostatics.tex` §`sec:elec:methods:molec` lists **27** mutations (Q8K, N15S, Q38K, A57E, T67V, C87A,
  A90V, A95S, L99Q, E103G, K118R, L119I, I124V, T125K, V136T, F166Y, K172R, V185I, K212N, K214R, S217T,
  T224S, N227A, T244A, E276G, C285S, K290Q) — these convert the ***E. coli*** crystal structure (2WCD) into
  *S. typhi* ClyA-AS, so they include the interspecies sequence differences as well as the AS mutations.

Both are correct for their starting point. **Any structure-preparation pipeline must record which one it
applied and to which PDB.** Also note the model adds a residue: 2WCD lacks residues 1–7 and 293–303 per
chain, and a single negatively charged Glu7 was added back at the trans entry because that region matters
electrostatically.

Engineered variants (all on the ClyA-AS background), used to make ClyA translocate DNA at physiological salt:
**ClyA-R** (S110R, cis entry), **ClyA-RR** (S110R/D64R, mid-lumen), **ClyA-RR₅₆** (S110R/Q56R),
**ClyA-RR₅₆K** (S110R/Q56R/Q8K, constriction). Of >20 variants tested experimentally, only **ClyA-RR**
translocated dsDNA at 0.15 M, and only from cis — D64R is a charge *reversal* (+2 e) that flips the mid-lumen
potential from −0.32 to +0.20 kT/e, while Q56R (+1 e) only slows the rise.

## 4. The lipid bilayer

Experiments and simulations use **DPhPC** (1,2-diphytanoyl-*sn*-glycero-3-phosphocholine), a branched-chain
lipid chosen for stable, low-noise planar bilayers. Modelling parameters:

| Property | Value | Where |
|---|---|---|
| Thickness | **2.8 nm** | ePNP-NS model (01 §2.4); consistent with FraC's 3.5 nm TMD helices spanning it |
| Relative permittivity | **3.2** (Gramse 2013) | ePNP-NS |
| — in the APBS work | 2 | electrostatics.tex `tab:pdb2pqr_apbs_parameters` |
| APBS slab thickness | 27 Å, with a conical hole | `draw_membrane2` |

Electrostatically the bilayer is an **uncharged, ion-impermeable, low-permittivity dielectric slab** — very
different from the surrounding `eps_r ≈ 78` electrolyte, and it measurably reshapes the potential. APBS does
not support membranes natively; the external `draw_membrane2` tool patches them into the permittivity,
ion-accessibility and charge grids at a large I/O cost (5 grids >2 GiB per run; 20 → 200 min). The thesis
therefore included the bilayer only for the ~20 pore-only potential maps and omitted it for the >500 energy
calculations, having checked it does not change the qualitative conclusions.

## 5. Single-channel electrophysiology

How a conductance is actually measured [transport.tex §"Recording of single-channel current-voltage curves"]:
a **black lipid bilayer** is formed across a ~100 µm aperture in a Teflon film separating two buffered
compartments (hexadecane/pentane pre-treatment, DPhPC in pentane, bilayer formed by lowering and raising the
buffer level). A trace of purified oligomer is added to the **grounded cis** reservoir and inserts
spontaneously — stochastically in time and place, the practical reason single-channel work is tedious.
Current is recorded with a patch-clamp amplifier (AxoPatch 200B + Digidata 1440A, Clampex) at 10 kHz with a
2 kHz low-pass filter, ~25 °C, in NaCl buffered with 10 mM MOPS at pH 7.5.

Key observables [§"Ionic current spectroscopy", `fig:nanopores_concept`]:

- **Open-pore current `I_open`** — the steady baseline with no analyte in the pore. **Open-pore conductance**
  `G = I/V_bias`; a typical BNP (⌀3 nm, 10 nm long, 0.15 M KCl) is ~1 nS, so 100 mV gives ~100 pA ≈ 6×10⁸
  ions/s. FraC comparison at +50 mV, 1 M NaCl: WtFraC 1.91 ± 0.17 nS, ReFraC 1.19 ± 0.12 nS — a single charge
  reversal at the constriction changes G by 38%.
- **I–V curve** — current versus applied bias, swept with a pulse protocol. Nonlinearity/asymmetry is
  rectification (see 02 §7). ePNP-NS was validated against I–V curves over −200…+200 mV and 0.05–3 M NaCl.
- **Current blockade** — an analyte entering the pore transiently reduces the current to a **blocked-pore**
  level. Typical residual currents are **10–95% of `I_open`**; **dwell times** 10 µs–100 ms for DNA/protein
  translocation, seconds to minutes for trapped proteins. The **fractional residual current** (blocked/open)
  is the standard reported quantity, and its constancy with voltage is evidence a protein stays folded.
- **Inter-event time** ∝ 1/analyte concentration; blockade depth and duration encode analyte size, shape and
  charge. Bandwidth is 1–50 kHz typically (1 MHz demonstrated), limited by signal-to-noise, not electronics —
  flicker, shot, thermal, dielectric and capacitive noise all contribute.

**Resistive-pulse sensing** is the name of this principle: the pore's ~1 GΩ resistance dwarfs the reservoirs'
~10 Ω, so the entire applied potential drops across (and just around) the pore, giving fields of 10⁶–10⁷ V/m
[epnpns.tex]. That field drives ions (the open-pore current) and water (EOF), and drags analytes in; each
passage produces one pulse. Because a pore's interior fits only one molecule at a time, it is intrinsically
single-molecule.

## 6. What nanopores are used for

DNA sequencing (the field's original driver, commercialised by Oxford Nanopore — the MinION runs 512 pores for
30 Gbp of real-time data, using MspA/CsgG-derived pores); proteomics and protein analysis; protein sequencing
(FraC for peptides and amino acids); single-molecule enzymology (enzymes tethered to or trapped inside ClyA);
metabolomics and biomarker detection. Large pores (ClyA, PlyAB) exist to hold *whole folded proteins* — the
average eukaryotic protein is ~50 kDa and >5 nm across, so most legacy pores (1–2 nm) are far too small.

## 7. Why accurate modelling matters for pore engineering

The measured blockade depends jointly on pore, analyte, and conditions (ionic strength, pH, bias), making
signals "notoriously difficult to predict and interpret unambiguously" [§"Ionic current spectroscopy"].
Engineering campaigns are correspondingly expensive: Franceschini et al. built and screened >20 ClyA variants
to find the single one that translocates dsDNA at physiological salt. A model that predicts conductance,
selectivity and EOF direction from a mutated structure turns that search into a computation. The thesis's
own worked examples: PB potential maps explained why ReFraC (one D10R mutation) reverses selectivity, EOF
direction and DNA-translocation ability relative to WtFraC; why PlyAB-R's opposed cis/trans charges suppress
EOF and change protein capture; and why ClyA-RR alone works at 0.15 M. Unmodified continuum transport theory
is quantitatively poor for ionic currents — which is exactly the gap ePNP-NS closes.

## 8. Glossary

| Term | Meaning |
|---|---|
| **BNP / SSNP** | biological / solid-state nanopore |
| **PFT** | pore-forming toxin; α- or β-, after the TMD fold |
| **TMD** | transmembrane domain |
| **monomer / protomer** | soluble form / same chain in the assembled pore |
| **cis / trans** | reservoirs; cis is grounded and receives the protein, trans carries the bias |
| **lumen** | the wide interior chamber of a pore |
| **constriction** | narrowest point; usually dominates conductance and selectivity |
| **vestibule** | αHL's cis chamber |
| **open pore current `I_open`** | baseline current with no analyte |
| **blockade / residual current** | current while an analyte occupies the pore, usually as a fraction of `I_open` |
| **dwell time** | duration of one blockade |
| **translocation** | analyte passes through, cis → trans |
| **resistive-pulse sensing** | detection by transient conductance changes |
| **I–V curve** | current vs applied bias |
| **ICR** | ionic current rectification, `G(+V)/G(-V)` |
| **EDL / EOF / EP / EO / DEP** | electrical double layer / electro-osmotic flow / electrophoretic / electro-osmotic / dielectrophoretic |
| **GHK** | Goldman–Hodgkin–Katz equation, converts reversal potential to permeability ratio |
| **transport number `t_i`** | fraction of current carried by species i |
| **DPhPC** | 1,2-diphytanoyl-*sn*-glycero-3-phosphocholine, the bilayer lipid |
| **MOPS** | 4-morpholinepropanesulfonic acid, the buffer |
| **SM** | sphingomyelin; a structural component of the FraC pore |
| **MACPF** | membrane attack complex/perforin-like fold (PlyB) |
| **PDB / PQR** | structure file / structure + per-atom charge and radius |
| **PDB2PQR, PROPKA, DelPhiPKa** | assign protonation states and pKa values |
| **APBS** | Adaptive Poisson-Boltzmann Solver |
| **CHARMM36 / PARSE** | force fields supplying partial charges and radii |
| **VMD / NAMD** | molecular visualisation / MD engine |
| **cryo-EM, MDFF** | electron microscopy, MD flexible fitting into an EM map |
| **ssDNA / dsDNA / bp** | single-/double-stranded DNA / base pair |
| **ClyA-AS** | stabilised ClyA variant used throughout; **not** wild type |
| **WtFraC / ReFraC** | wild-type FraC / D10R-K159E charge-reversal variant |
| **PlyAB-E2 / -R** | stabilised PlyAB variants; -R has a reversed-charge constriction |
