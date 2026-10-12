# nanopnp knowledge base — index

Local domain knowledge for `nanopnp`, a reimplementation of the ePNP-NS framework for biological
nanopores (Willems et al., *Nanoscale* **12**, 16775–16795, 2020).

**Agents read from here rather than searching the web.** Everything below was extracted from
primary sources (the thesis LaTeX, the paper's ESI, library documentation) and cross-checked.
Several widely-copied web summaries of this model are wrong; this records what is true, including
where the sources contradict themselves.

---

## Files

| File | Read it when |
|---|---|
| **`01-physics-epnpns.md`** | **First for physics work.** The normative equations, corrections, parameters and errata; read the governing sections before implementing, testing or reviewing model behaviour. Workflow-only and mechanical tasks need not load it. |
| `02-electrokinetics-background.md` | Underlying theory: double layers, Poisson–Boltzmann, electro-osmosis, selectivity, rectification. |
| `03-nanopore-biology.md` | Domain grounding: the pores, ClyA, electrophysiology, glossary. |
| `04-clya-geometry-and-charge.md` | The structure → geometry → mesh and charge pipelines; numeric validation targets. |
| `05-analyte-and-forces.md` | Embedded analyte bodies and forces. A continuum reference exists: the PlyAB work (Angew. Chem. 2022), §10. |
| `06-numerics-fem.md` | Weak forms, solvers, continuation, QoI extraction. |
| `07-software-stack.md` | Library versions, licences, why a dependency was chosen or rejected. |
| `08-validation-benchmarks.md` | Writing tests or interpreting a validation failure. |
| `09-comsol-reference-settings.md` | The original COMSOL mesh, solver and stabilisation settings, from the 5.4 model report. Read it before assuming our discretisation matches theirs: **their stabilisation was ON** in transport and flow. |
| `../data/corrections/willems2020_nacl.yaml` | The fitted correction parameters, transcribed and verified. |

---

## The five things most likely to trip you up

Stated in `.claude/rules/physics-numerics.md`; derived here.

1. **The wall function is `1 − exp(−6.2(d + 0.01))`**: plus, and 6.2 nm⁻¹ (ESI `0.62e1`). → `01-physics-epnpns.md` §8.
2. **The steric flux sign:** `β_i` enters the bracket with `+`, and the bracket is negated. → `01` §2.2.
3. **No dielectric-gradient body force** in the published model (`f = ρ_ion E` only); adding one is a
   deviation. → `01` §2.3.
4. **Einstein holds only at infinite dilution:** `D_i/μ_i` drifts to 1.2–1.7 × `kT/e` between 0.15
   and 3 M, so Poisson–Boltzmann is a distinct model, not PNP at V = 0. → `02-electrokinetics-background.md`.
5. **`1/r` terms return NaN at integration order 2.** → `06-numerics-fem.md` §2.2.

---

## Conventions used throughout

- Plain-text notation, not LaTeX macros: `phi`, `c_i`, `eps_r`, `nabla`.
- `⟨c⟩` is `(1/n)Σc_i`, not the ionic strength, and `d` is the distance to the nearest pore
  boundary (`.claude/rules/physics-numerics.md`).
- Correction functions take dimensionless `c̄ = ⟨c⟩/(1 M)` and `d̄ = d/(1 nm)`.
- Claims verified by running code are marked **[tested]**; claims verified by arithmetic are marked
  **[verified]**. Anything unverified says so.

---

## Provenance and how to extend this

Primary sources: the thesis LaTeX (CC-BY-4.0, `github.com/willemsk/phdthesis-text`), the paper
(DOI `10.1039/D0NR03114C`), its bioRxiv preprint (`10.1101/2020.01.08.897819`), the ESI
(`rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf`) and the reference structure PDB **2WCD**
(ClyA dodecamer), variant **ClyA-AS**.

**When you learn something durable, write it here:** a discrepancy between sources, a library
behaviour found by testing, a numerical result that took effort to establish. Mark it **[tested]**
or **[verified]** and cite its source. **Do not record** status, task lists or scope opinions;
those belong in the specification.

---

## Author rulings (2026-08) — these override the sources

Given directly by the author; where they conflict with a printed source, **these win**.

| # | Question | Ruling |
|---|---|---|
| 1 | D/μ wall coefficient `P₁` | **6.2 nm⁻¹.** Table 5.2 is correct; the running-text value and the 0.62 correction are wrong. |
| 2 | Permittivity fit parameters | **Gavish (30.08, 11.5) govern**, as the model file records; the printed 42.12 cap is stale, the correct cap is 42.67 (`SPECIFICATION.md` §4.6 erratum 6; `09` §D3). |
| 3 | Meaning of `⟨c⟩` | **Configurable, default eq. 5.3**, `(1/n)Σcᵢ`; ionic strength is a named option. |
| 4 | Analyte boundary conditions | **No-flux, no-slip, dielectric jump:** a hard dielectric body, like the pore wall. |
| 5 | `ε_protein` | **A calibration parameter, not a constant.** Default 20 for ePNP-NS; in the case file, reported as fitted. APBS's 10 belongs to that workflow. |
| 6 | Pore-averaging convention | **True volume average, with the `2πr` Jacobian**; the omission is a transcription issue. Published pore averages are usable as regression targets. |
| 7 | Radial potential at 0.15 M (−14/−47 vs −29/−57 mV) | **Unresolved**; excluded from regression targets. |
| 8 | Net charge (−72.9 / −72 / −60 e) | **Different constructs**; a run records which construct and PDB it started from. −72.9 and −72 are one construct: `rhoq_pore` integrates to −72 e, and −72.9 is COMSOL's mesh-quadrature aliasing. → `04` §3.2. |
| 9 | Analyte force chain | **Forces + PMF** (`ΔU = −∫F dz`); Brownian dynamics out of scope. |
| 10 | PlyAB as a second reference case | **Yes, after v1.0.** |
| 11 | Density-map radii and atoms | **CHARMM Rmin/2** from PDB2PQR's `CHARMM.DAT`; the map used the **full-atom** MD trajectory, hydrogens included. → `SPECIFICATION.md` §5.3.1 NOTE on `geometry.density`; `04` §1.1. |
| 12 | Axial offset G9 | **0 in the MD frame** (centred on the bilayer's middle). → `04` §8 G9. |
| 13 | `⟨c⟩` inside a solid | **Has no meaning: ions do not exist there.** `ε_r,f(⟨c⟩)` is evaluated only in the fluid; water off the fluid is ion-free, `ε_r,f⁰`. → `SPECIFICATION.md` §4.4 NOTE, §5.3.1 NOTE on `exclusion`; `06` §8.1. |
| 14 | The reference polygon and VAL-05 | The 185-vertex table used **`pqr2grid`'s radial binning at L = 15 nm**; the **hand edit moved vertices**. → `SPECIFICATION.md` §7.4 NOTE on VAL-05; `04` §1.2, §1.4. |

## Still open

1. **Radial potential at 0.15 M** — ruling 7 above. → `04-clya-geometry-and-charge.md`.
2. **ClyA-AS mutation list:** 8 mutations relative to *S. typhi* wild type, or 27 relative to the
   *E. coli* 2WCD structure; a pipeline records which it applied to which PDB (ruling 8).
   → `03-nanopore-biology.md`.
3. **PlyAB SI details** (analyte `ε_r`, mesh strategy, barriers, EOF velocities): the author holds
   the model. → `05-analyte-and-forces.md` §10.

