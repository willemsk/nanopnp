# nanopnp knowledge base — index

Local domain knowledge for the `nanopnp` project: an open-source Python reimplementation of the
ePNP-NS continuum framework for simulating biological nanopores (Willems et al., *Nanoscale*
**12**, 16775–16795, 2020).

**Purpose: agents working on this codebase should read from here rather than searching the web.**
Everything below was extracted from primary sources — the CC-BY-4.0 thesis LaTeX, the paper's ESI,
and library documentation — and numerically cross-checked. Several widely-copied web summaries of
this model are wrong; this knowledge base records what is actually true, including where the
original sources contradict themselves.

---

## Files

| File | Read it when |
|---|---|
| **`01-physics-epnpns.md`** | **First for physics work.** Read the governing sections and relevant errata before implementing, testing or reviewing model behaviour. The normative equations, corrections and parameters; do not re-derive them from elsewhere. Workflow-only and mechanical tasks do not require loading this file. |
| `02-electrokinetics-background.md` | You need the underlying theory: double layers, Poisson–Boltzmann, electro-osmosis, selectivity, rectification, access resistance. |
| `03-nanopore-biology.md` | You need domain grounding: what these pores are, ClyA specifically, electrophysiology, glossary of terms and acronyms. |
| `04-clya-geometry-and-charge.md` | You are working on the structure → geometry → mesh or charge pipelines, or you need numeric validation targets. |
| `05-analyte-and-forces.md` | You are working on embedded analyte bodies or force computation. A continuum reference DOES exist: the PlyAB haemoglobin work (Angew. Chem. 2022) — see §10 of that file. |
| `06-numerics-fem.md` | You are writing or changing weak forms, solvers, continuation, or QoI extraction. |
| `07-software-stack.md` | You need library versions, licences, or the reason a particular dependency was chosen or rejected. |
| `08-validation-benchmarks.md` | You are writing tests or interpreting a validation failure. |
| `09-comsol-reference-settings.md` | You want the original COMSOL mesh/solver/stabilisation settings. **Mined in full from the COMSOL 5.4 model report.** Read it before assuming our discretisation matches theirs — **their stabilisation was ON** in both transport and flow. |
| `../data/corrections/willems2020_nacl.yaml` | The fitted correction parameters, transcribed and verified. |

---

## The five things most likely to trip you up

1. **The wall function is `1 − exp(−6.2(d + 0.01))`** — plus, not minus, and 6.2 nm⁻¹. The ESI
   writes the coefficient as `0.62e1`, which is where both the "62" and "0.62" misreadings come
   from. Verified against the thesis's own check values `f(0) = 0.06`, `f(0.75) = 0.99`, and
   against the model expression `1 - exp(-0.62e1*(wdf.dwd + 0.01))`. → `01-physics-epnpns.md` §8.

2. **The steric flux sign.** `β_i` enters the flux bracket with a `+`, and the bracket is negated.
   A flipped sign drives ions *into* crowded regions, pushes the packing fraction to 1, and
   diverges. → `01-physics-epnpns.md` §2.2.

3. **There is no dielectric-gradient body force in the published model.** Despite `ε_r` varying
   with concentration, the momentum equation uses `f = ρ_ion E` only. Adding
   `−½|∇φ|²∇ε` (or its Nernst–Planck counterpart) is a *deviation from the validated model*.
   → `01-physics-epnpns.md` §2.3.

4. **The Einstein relation holds only at infinite dilution.** The model sets
   `l0 = e²N_A/(k_B T)·D0` and `mu = l0·L(c)·f^w(d)/F²`, so `μ_i = D_i⁰·L_i^c(c)·f^w(d)/(RT)`:
   Nernst–Einstein by construction at `c → 0`, but `D` and `μ` then carry **different**
   concentration corrections (`cdf.D_*` vs `cdf.L_*`), and `D_i/μ_i` drifts to 1.2–1.7 × `kT/e`
   between 0.15 and 3 M. Consequence: the zero-bias limit of ePNP-NS is not a Boltzmann
   distribution, so Poisson–Boltzmann is a distinct model, not "the PNP solver at V = 0".
   → `02-electrokinetics-background.md`.

5. **`1/r` terms return NaN at integration order 2.** NGSolve's order-2 triangle rule samples
   `r = 0` exactly on axis-touching elements. Assert order ≥ 3 on every form containing `1/r`.
   → `06-numerics-fem.md` §2.2.

---

## Conventions used throughout

- Plain-text notation, not LaTeX macros: `phi`, `c_i`, `eps_r`, `nabla`.
- `⟨c⟩` is the **average ion concentration** `(1/n)Σc_i`, not the ionic strength. They coincide
  for a symmetric 1:1 salt and diverge otherwise.
- `d` is the distance to the **nearest pore boundary**; the membrane is deliberately excluded.
- Concentrations in the correction functions are dimensionless: `c̄ = ⟨c⟩/(1 M)`, `d̄ = d/(1 nm)`.
- Claims verified by running code are marked **[tested]**; claims verified by arithmetic are marked
  **[verified]**. Anything unverified says so.

---

## Provenance and how to extend this

Primary sources, all local or open:

| Source | Where |
|---|---|
| Thesis LaTeX (CC-BY-4.0) | `thesis/` ← `github.com/willemsk/phdthesis-text` |
| Paper | *Nanoscale* **12**, 16775–16795 (2020), DOI `10.1039/D0NR03114C` |
| Open preprint | bioRxiv `10.1101/2020.01.08.897819` |
| ESI (COMSOL implementation) | `rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf` |
| Reference structure | PDB **2WCD** (ClyA dodecamer), variant **ClyA-AS** |

**When you learn something durable, write it here.** Specifically: any further discrepancy found
between sources, any library behaviour discovered by testing, any numerical result that took
effort to establish. Mark it **[tested]** or **[verified]** and cite where it came from. The value
of this knowledge base is that it accumulates; a fact re-derived twice is a fact that should have
been written down the first time.

**Do not record**: transient project status, task lists, or opinions about scope. Those belong in
the specification, not here.

---

## Author rulings (2026-08) — these override the sources

Answers given directly by the author. Where they conflict with a printed source, **these win**.

| # | Question | Ruling |
|---|---|---|
| 1 | D/μ wall coefficient `P₁` | **6.2 nm⁻¹.** Table 5.2 is correct; the running-text value and an earlier verbal correction to 0.62 are both wrong. |
| 2 | Permittivity fit parameters | **Settled by the model file: Gavish (30.08, 11.5) govern.** The model parameter table and solver log both record `epsr_ms = 30.08`, `epsr_alpha = 11.5`. The thesis text was right; the printed 42.12 cap is stale (it matches the unused Buchner fit). Correct cap 42.67. An earlier verbal recollection favouring the Buchner fit is superseded by the model file (`SPECIFICATION.md` §4.6 erratum 6). |
| 3 | Meaning of `⟨c⟩` | **Configurable, defaulting to eq. 5.3** — the average ion concentration `(1/n)Σcᵢ`. Ionic strength available as a named option. |
| 4 | Analyte boundary conditions | **Confirmed: no-flux, no-slip, dielectric jump.** The analyte is a hard dielectric body, impermeable to ions and water, like the pore wall. |
| 5 | `ε_protein` | **A calibration parameter, not a constant.** Default 20 for ePNP-NS; surfaced in the case file and reported in every output as fitted rather than physical. The APBS value of 10 belongs to that workflow. |
| 6 | Pore-averaging convention | **True volume average — the `2πr` Jacobian was included.** The apparent omission is a transcription issue in the thesis text. Published pore averages are directly usable as regression targets. |
| 7 | Radial potential at 0.15 M (−14/−47 vs −29/−57 mV) | **Unresolved** — author to check. Excluded from regression targets until settled. |
| 8 | Net charge (−72.9 / −72 / −60 e) | **Different constructs.** Each figure is right for its own construct; any structure-prep run must record which construct and which PDB it started from. **Narrowed by measurement, 2026-09-06: the −72.9 / −72 pair is one construct measured two ways, not two constructs.** The delivered `rhoq_pore` table integrates to the *integer* −72 e to 4.7e-12, so −72.9 is the same charge after COMSOL's own mesh quadrature of it — a consumer-side aliasing error of +1.25 %, reproduced here at −0.99 % by the same route. → `04-clya-geometry-and-charge.md` §3.2. The ruling stands for −60 e. |
| 9 | Analyte force chain | Reproduce **forces + PMF** (`ΔU = −∫F dz`). Brownian dynamics stays out of scope. |
| 10 | PlyAB as a second reference case | **Yes, but after v1.0** — the first post-release generalisation test. |

## Still open

1. **Radial potential at 0.15 M** — ruling 7 above. → `04-clya-geometry-and-charge.md`.
2. **ClyA-AS mutation list.** Defined as 8 mutations relative to *S. typhi* wild type in the
   glossary and 27 relative to the *E. coli* 2WCD structure elsewhere. Both are internally
   correct; any structure-prep pipeline must record which it applied to which PDB. Related to
   ruling 8. → `03-nanopore-biology.md`.
3. **The contour script** — the author needs to locate it. Plan around the from-scratch pipeline
   and treat it as upside. → `SPECIFICATION.md` §8.4.
4. **PlyAB SI details** — analyte `ε_r`, per-position mesh strategy, barrier heights in kT, EOF
   velocities. Unreachable from this environment; the author holds the model.
   → `05-analyte-and-forces.md` §10.

The permittivity fit parameters (formerly open here) are **settled**: the model used Gavish
(30.08, 11.5), which govern; ruling 2 above and `SPECIFICATION.md` §4.6 erratum 6 record the
arithmetic. → `09-comsol-reference-settings.md` §D3.
