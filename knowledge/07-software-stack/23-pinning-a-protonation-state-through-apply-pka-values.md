---
type: Library Behaviour
title: "23. Pinning a protonation state through PDB2PQR's apply_pka_values (WP5.04)"
description: How to hold a residue in a chosen protonation state during PDB2PQR 3.8's call, why renaming the input cannot do it, and what the pin moves besides the residue.
tags:
- software
- library-behaviour
- charge
sources:
- id: wp5.04-plan
  resource: docs/plans/wp5.04-the-charge-mutators-library-step.md
  title: WP5.04 plan, Grounding for D2
generated:
  by: claude-code/0.6.0-alpha.4
  at: '2026-11-03T00:00:00Z'
tested_with:
  pdb2pqr: 3.8.0
  propka: 3.5.1
verified:
- by: process:tests/tier1/test_protonation.py::test_fr38_a_pinned_state_holds_and_changes_that_residue_alone
  at: '2026-11-03T00:00:00Z'
---

## 23. Pinning a protonation state through PDB2PQR's `apply_pka_values` (WP5.04)

PDB2PQR 3.8.0's `main.non_trivial` hands PROPKA's pKa values to
`Biomolecule.apply_pka_values(forcefield, ph, {pka_key(name, number, chain, icode): pKa})`. The method pops
each residue's key and applies the state patch `ASH`, `GLH` or `HIP` where the pKa passes the pH. A residue
whose key is absent keeps the force field's standard state.

- **Pin by dropping the key.** Wrapping `apply_pka_values`, removing the pinned residue's `pka_key` from the
  dictionary, calling the original, and then applying the wanted patch with `apply_patch` holds the residue in
  either state while PROPKA's other rows stay whole. At pH 7.5 a held-out ASP 21 patched `ASH` is neutral
  (`HD2`); at pH 2 a held-out ASP 21 stays charged (−1) where PROPKA protonates it.
  **[tested: tests/tier1/test_protonation.py::test_fr38_a_pinned_state_holds_and_changes_that_residue_alone]**
- **Renaming the input cannot pin the charged state.** PDB2PQR titrates an input residue named `ASP`, and a
  residue named `ASH` is a fixed residue that PROPKA does not titrate, so its row leaves the pKa table.
- **The key names the residue, not the number.** On chain A, HIS 292 also carries a `C-` pKa row with the same number, so the pin matches the
  residue name as well.
- **Under CHARMM only ASP, GLU and HIS can be pinned.** PDB2PQR warns and keeps the standard state for `CYS⁻`,
  `LYS⁰`, `TYR⁻` and `ARG⁰`.
- **A pin can move a neighbour.** PDB2PQR's hydrogen optimisation re-solves the hydrogen network when a state
  changes, so a neighbouring carboxyl (GLU 18 beside ASP 21 on the 2WCD fragment at pH 2) can flip its `HE2` and
  oxygens with every charge by name unchanged. Compare a variant with its parent by atom identity, not by
  position in the table.
- **The names the pin and the charge edit rely on exist in the installed libraries.** The patches, `pka_key`,
  `apply_pka_values` and PROPKA's charge-centre atoms are checked on each upgrade.
  **[tested: tests/tier1/test_library_behaviour.py::test_fr38_the_titratable_groups_are_propkas]**

The pipeline's use is PHY-16 step 3's NOTE on `charge.edits`.
