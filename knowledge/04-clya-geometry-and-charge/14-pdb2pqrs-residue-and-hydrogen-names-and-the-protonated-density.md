---
type: Test Evidence
title: "PDB2PQR's residue and hydrogen names, and the protonated density"
description: Which residue name PDB2PQR writes for a protonated side chain, which radius each atom takes from the CHARMM set, and why the protonated density needs the state patch.
tags:
- clya
- charge
- test-evidence
sources:
- id: wp5.03-plan
  resource: docs/plans/phase-5/wp5.03-protonation-before-the-density.md
  title: WP5.03 plan, Grounding
generated:
  by: claude-code/0.6.0-alpha.3
  at: '2026-11-03T00:00:00Z'
verified:
- by: process:tests/tier1/test_density.py::test_ver49_protonated_radii_are_pdb2pqr_charmm_radii
  at: '2026-11-03T00:00:00Z'
---

## PDB2PQR's residue and hydrogen names, and the protonated density

Stage 2 smears the atoms of the protonation table when `geometry.density.atoms` is `protonated`
(PHY-16; §5.3.1 NOTE on `geometry.density`). Each atom's radius must be the one PDB2PQR itself wrote.

* **Residue names do not tell the state.** Under `--ff=CHARMM`, PDB2PQR writes a histidine as `HSD`,
  `HSE` or `HSP`, an aspartate holding `HD2` as `ASPP`, and a terminus with an `NTER` or `CTER` patch.
  Its N-terminal GLU 18 on the 2WCD fragment at pH 2 is protonated and written `GLU`, holding `HE2`
  with `OE2` at 1.77 Å. A lookup by residue name alone gives `OE2` the neutral glutamate's 1.70 Å and
  leaves `GLU HE2` without a radius. **[tested: tests/tier1/test_density.py::test_ver49_protonated_radii_are_pdb2pqr_charmm_radii]**
* **The state patches carry the radius.** `ASPP` and `GLUP` in `data/radii/pdb2pqr_charmm.yaml` set `OD2`
  and `OE2` to 1.77 Å and the acid hydrogen to 0.2245 Å. Taking each atom from its residue's state patch
  (the table's tautomer for HIS, `ASPP` for an ASP holding `HD2`, `GLUP` for a GLU holding `HE2`) and
  from the parent residue otherwise, every atom of the fragment resolves, at pH 2 and at pH 8, to the
  radius in the PQR to 10⁻¹² nm. **[tested: tests/tier1/test_density.py::test_ver49_protonated_radii_are_pdb2pqr_charmm_radii]**
* **Another force field writes other hydrogen names.** PDB2PQR 3.8 under `--ff=SWANSON` writes AMBER
  hydrogen names (`H`, `HB3`, `H1`) that the CHARMM set does not hold: fourteen atoms of the fragment are
  unresolved and every heavy radius differs from CHARMM's. `PEOEPB` failed on the fragment **[verified][^wp503-plan]**. The protonated
  density is therefore refused beside a produced protonation under a `charge.forcefield` other than `CHARMM`.

[^wp503-plan]: `docs/plans/phase-5/wp5.03-protonation-before-the-density.md`, Grounding for D2 (PDB2PQR 3.8 under `--ff=SWANSON` and `PEOEPB` on `data/structures/2wcd-a-18-26.pdb`).
