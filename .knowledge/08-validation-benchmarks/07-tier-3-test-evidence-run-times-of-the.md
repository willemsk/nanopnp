---
type: Test Evidence
title: 'Tier-3 test evidence: run times of the archive and seed fixtures (WP45 item
  27)'
---

## Tier-3 test evidence: run times of the archive and seed fixtures (WP45 item 27)

- **[tested]** Depositing the ClyA-AS ensemble's stages 1 to 3 costs about 16 minutes on the author's machine, which is why the tier's session deposits them once. Source: `tests/tier3/conftest.py` (module docstring at `3782c43`, before WP45); `docs/plans/wp22-val05-reference-geometry.md`.
- **[tested]** The VAL-06 archive leg takes about 75 minutes, most of it the 100 APBS runs at 193³. Source: `tests/tier3/test_val06_archive.py` (module docstring at `3782c43`, before WP45); `docs/plans/wp29-val06-apbs.md`.
- **[tested]** PROPKA protonation of the prepared 2WCD takes about a minute, a charged walk through stage 7 about two seconds, and the ClyA reference mesh about 7 s. Source: `tests/conftest.py` (`protonated_2wcd`, `write_charged_tube`, `clya_reference_mesh`).
- **[verified]** A self-golden is made from the last rung, `E_3`, so `Delta_resid` = `E_3` − `E_3` is exactly zero by construction; made from any other rung, the one delta that §7.4's targets apply to would be an unpredicted number. Source: `tests/tier3/test_comsol_comparison.py` (`test_val01_full_ladder_against_a_self_golden`).
- **[tested]** The default-size 0.15 M mesh of the prepared 2WCD takes about 8 s, and it is the mesh the charge, VAL-06, pipeline and VAL-05 modules all walk to. Source: `tests/conftest.py` (`seeded_2wcd`).
- **[tested]** The COMSOL golden is read from `$NANOPNP_REFERENCE_DATA/comsol/<case>/<refinement>/golden.npz`, the layout `docs/validation/comsol-export-contract.md` asks the author for. Source: `tests/tier3/test_comsol_comparison.py` (module docstring at `3782c43`, before WP45).
