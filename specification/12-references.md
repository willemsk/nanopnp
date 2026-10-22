---
type: Specification
title: "12. References"
description: "Lists the normative sources, numerical methods, software and standards cited by the specification."
---

## 12. References

### 12.1 Normative sources

- Willems K., Ruić D., Lucas F.L.R., Barman U., Verellen N., Hofkens J., Maglia G., Van Dorpe P.
  *Accurate modeling of a biological nanopore with an extended continuum framework.*
  **Nanoscale 12, 16775–16795 (2020).** DOI [10.1039/D0NR03114C](https://pubs.rsc.org/en/content/articlelanding/2020/nr/d0nr03114c)
- Preprint (open access): bioRxiv [10.1101/2020.01.08.897819](https://www.biorxiv.org/content/10.1101/2020.01.08.897819v1.full)
- ESI with COMSOL implementation detail, correction coefficients pp. 4–5:
  [d0nr03114c1.pdf](https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf)
- Willems K., PhD thesis (CC-BY-4.0), chs. 5–6:
  [github.com/willemsk/phdthesis-text](https://github.com/willemsk/phdthesis-text) ·
  arXiv mirror [2103.05043](https://arxiv.org/abs/2103.05043)
- COMSOL model report `npgrid_clya_v8_NaCl_report.mph` (COMSOL 5.4 build 388, 22 May 2020),
  162 pages; Appendix B.
- Mueller M., Grauschopf U., Maier T., Glockshuber R., Ban N. *The structure of a cytolytic
  α-helical toxin pore reveals its assembly mechanism.* **Nature 459, 726 (2009)**;
  [PDB 2WCD](https://www.rcsb.org/structure/2WCD)
- Huang G., Willems K., Bartelds M., van Dorpe P., Soskine M., Maglia G., *Nano Lett.* **20**,
  3819–3827 (2020) (PlyAB electro-osmotic vortices); *ACS Nano* **13**, 9980 (2019)
  ([protein trapping in ClyA](https://pmc.ncbi.nlm.nih.gov/articles/PMC6764111));
  *Angew. Chem. Int. Ed.* 2022, DOI [10.1002/anie.202206227](https://doi.org/10.1002/anie.202206227)
  (PlyAB force and PMF computation)
- Li L., Li C., Zhang Z., Alexov E. *On the dielectric "constant" of proteins: smooth dielectric
  function for macromolecular modeling and its implementation in DelPhi.* **J. Chem. Theory
  Comput. 9, 2126–2136 (2013).**

### 12.2 Numerical methods

- Mitscha-Baude G., Buttinger-Kreuzhuber A., Tulzer G., Heitzinger C. *Adaptive and iterative
  methods for simulations of nanopores with the PNP–Stokes equations.* **J. Comput. Phys. 338,
  452 (2017).** [arXiv:1608.05313](https://arxiv.org/abs/1608.05313) · code:
  [mitschabaude/nanopores](https://github.com/mitschabaude/nanopores) (MIT)
- Metti M.S., Xu J., Liu C. *Energetically stable discretizations for charge transport and
  electrokinetic models.* **J. Comput. Phys. 306, 1 (2016).**
- Chaudhry J.H., Comer J., Aksimentiev A., Olson L.N. *A stabilized finite element method for
  modified Poisson–Nernst–Planck equations…* **Commun. Comput. Phys. 15, 93 (2014).**
  [PMC3867981](https://pmc.ncbi.nlm.nih.gov/articles/PMC3867981/)
- Hughes T.J.R., Engel G., Mazzei L., Larson M.G. *The continuous Galerkin method is locally
  conservative.* **J. Comput. Phys. 163, 467 (2000).**
- Becker R., Rannacher R. *An optimal control approach to a posteriori error estimation in finite
  element methods.* **Acta Numerica 10, 1–102 (2001).**
- Bank R.E., Rose D.J. **Numer. Math. 37, 279 (1981)** (damped Newton);
  Kelley C.T., Keyes D.E. **SIAM J. Numer. Anal. 35, 508 (1998)** (pseudo-transient continuation)
- Bazant M.Z., Chu K.T., Bayly B.J. **SIAM J. Appl. Math. 65, 1463 (2005)** (1D PNP limiting
  current)
- Rice C.L., Whitehead R. **J. Phys. Chem. 69, 4017 (1965)** (capillary electro-osmosis);
  Hall J.E. **J. Gen. Physiol. 66, 531 (1975)** (access resistance)

### 12.3 Software

- [NGSolve/Netgen](https://ngsolve.org/) (LGPL-2.1) ·
  [ngsPETSc](https://joss.theoj.org/papers/10.21105/joss.07359) ·
  [DOLFINx](https://github.com/FEniCS/dolfinx) (LGPL-3) ·
  [EchemFEM](https://github.com/LLNL/echemfem) (MIT) · [Gmsh](https://gmsh.info) (GPLv2+)
- [MDAnalysis](https://docs.mdanalysis.org/) (LGPLv3) ·
  [GridDataFormats](https://github.com/MDAnalysis/GridDataFormats) ·
  [mdahole2](https://github.com/MDAnalysis/mdahole2)
- [PDB2PQR](https://github.com/Electrostatics/pdb2pqr) (BSD) ·
  [PROPKA3](https://github.com/jensengroup/propka) ·
  [APBS](https://github.com/Electrostatics/apbs) (BSD-3)
- [scikit-image](https://scikit-image.org/) · [Shapely](https://shapely.readthedocs.io/) ·
  [meshio](https://pypi.org/project/meshio/)

### 12.4 Standards

- ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements
  engineering.* Structure of §§1–3.
- IEEE 1016-2009, *IEEE Standard for Information Technology — Systems Design — Software Design
  Descriptions.* Structure of §5.
- IEEE 1012-2016, *IEEE Standard for System, Software, and Hardware Verification and Validation.*
  Structure of §7.
- IETF RFC 2119, *Key words for use in RFCs to Indicate Requirement Levels.* §1.5.

---

