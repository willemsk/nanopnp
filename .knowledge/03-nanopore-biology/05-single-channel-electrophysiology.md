---
type: Domain
title: 5. Single-channel electrophysiology
---

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
  rectification (see `.knowledge/02-electrokinetics-background/07-ionic-current-rectification.md`). ePNP-NS was validated against I–V curves over −200…+200 mV and 0.05–3 M NaCl.
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

