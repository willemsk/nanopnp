---
type: Domain
title: 5. Single-channel electrophysiology
description: "How a single-channel conductance is measured in a planar bilayer, and resistive-pulse sensing."
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

## 5. Single-channel electrophysiology

How a conductance is actually measured [transport.tex §"Recording of single-channel current-voltage curves"]:
a **black lipid bilayer** is formed across a ~100 µm aperture in a Teflon film separating two buffered
compartments (hexadecane/pentane pre-treatment, DPhPC in pentane, bilayer formed by lowering and raising the
buffer level) **[verified][^thesis]**. A trace of purified oligomer is added to the **grounded cis** reservoir and inserts
spontaneously — stochastically in time and place, the practical reason single-channel work is tedious **[verified][^thesis]**.
Current is recorded with a patch-clamp amplifier (AxoPatch 200B + Digidata 1440A, Clampex) at 10 kHz with a
2 kHz low-pass filter, ~25 °C, in NaCl buffered with 10 mM MOPS at pH 7.5 **[verified][^thesis]**.

Key observables [§"Ionic current spectroscopy", `fig:nanopores_concept`]:

- **Open-pore current `I_open`** — the steady baseline with no analyte in the pore. **Open-pore conductance**
  `G = I/V_bias`; a typical BNP (⌀3 nm, 10 nm long, 0.15 M KCl) is ~1 nS, so 100 mV gives ~100 pA ≈ 6×10⁸
  ions/s **[verified][^thesis]**. FraC comparison at +50 mV, 1 M NaCl: WtFraC 1.91 ± 0.17 nS, ReFraC 1.19 ± 0.12 nS — a single charge
  reversal at the constriction changes G by 38% **[verified][^arith-fracG]**.
- **I–V curve** — current versus applied bias, swept with a pulse protocol. Nonlinearity/asymmetry is
  rectification (see `knowledge/02-electrokinetics-background/07-ionic-current-rectification.md`). ePNP-NS was validated against I–V curves over −200…+200 mV and 0.05–3 M NaCl [`transport.tex`] **[verified][^thesis]**.
- **Current blockade** — an analyte entering the pore transiently reduces the current to a **blocked-pore**
  level. Typical residual currents are **10–95% of `I_open`**; **dwell times** 10 µs–100 ms for DNA/protein
  translocation, seconds to minutes for trapped proteins **[verified][^thesis]**. The **fractional residual current** (blocked/open)
  is the standard reported quantity, and its constancy with voltage is evidence a protein stays folded [§`sec:np:confinement`] **[verified][^thesis]**.
- **Inter-event time** ∝ 1/analyte concentration; blockade depth and duration encode analyte size, shape and
  charge **[verified][^thesis]**. Bandwidth is 1–50 kHz typically (1 MHz demonstrated), limited by signal-to-noise, not electronics —
  flicker, shot, thermal, dielectric and capacitive noise all contribute **[verified][^thesis]**.

**Resistive-pulse sensing** is the name of this principle: the pore's ~1 GΩ resistance dwarfs the reservoirs'
~10 Ω, so the entire applied potential drops across (and just around) the pore, giving fields of 10⁶–10⁷ V/m
[epnpns.tex] **[verified][^thesis]**. That field drives ions (the open-pore current) and water (EOF), and drags analytes in; each
passage produces one pulse **[verified][^thesis]**. Because a pore's interior fits only one molecule at a time, it is intrinsically
single-molecule.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.
[^arith-fracG]: Inputs: WtFraC G = 1.91 nS and ReFraC G = 1.19 nS at +50 mV in 1 M NaCl (thesis, `electrostatics.tex`, the subsection "WtFraC and ReFraC: minor mutations with a major impact"). Formula: (1.91 − 1.19)/1.91 = 0.377, so 37.7 %, which rounds to the note's 38 %.
