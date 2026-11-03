# Code review 028: WP5.03, protonation before the density

Reviewed head `162dbc0036c80178d386b394d5858f61552f4c96` against base `f1e54f077c90d6cbd3a64def78fb98e589a371fc`
(PR 151). Status: completed. Static review at `xhigh`, with a `physics-reviewer` read of the density and
protonation changes. Seven findings; four fixed, three recorded.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `density/radii.py` | A disulfide-bonded cysteine (`1CB`, `1SG`, `2SG`, `2CB` under `DISU`) has no radius by its parent name, so the default path refused any structure holding one. | Fixed: the `DISU` entries are looked up for a `CYS`. A Tier 1 case covers it. |
| 2 | `pipeline/checks.py`, §5.3.1 | Beside `inputs.charge` the protonation now runs for the density, yet `charge.ph`, `charge.forcefield` and `charge.titration` were refused as configuring a step that does not run; the specification said both. | Fixed: refused only under `as_loaded`; the NOTE is amended in the same commit. |
| 3 | `density/radii.py` | A state-patch radius of zero skipped the positive-radius guard that the parent lookup has. | Fixed. |
| 4 | `density/union.py` | `deposit` did not check that each frame has as many positions as widths. | Fixed. |
| 5 | `density/stage.py` | Docstring of `density_parameters` carried history. | Fixed. |
| 6 | `density/stage.py` | The header counts frame 0 only and reads an element from a name's first letter. | Recorded, REV-181. |
| 7 | `density/radii.py`, `union.py` | A polar hydrogen's kernel is narrower than the grid spacing. | Recorded, REV-182. |

Not findings: the default's conflict with `.claude/rules/physics-numerics.md` is the author's ruling (§8.2.19 U2,
§8.2.31 AG8); the density key hashes the whole protonation artefact, so it can miss a cache but never hit a wrong
one; `ProtonationTableError` is not a base of `PQRError`, as the plan had it, and no caller catches `PQRError` on a
table read.

Not assessed: the diff's `as_loaded` key against v0.5's byte for byte (no test pins a v0.5 hash); the PDB2PQR 3.8
naming of a proton on `OD1` or `OE1`, which stage 2 would refuse loudly.
