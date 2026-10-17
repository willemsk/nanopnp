---
type: Library Behaviour
title: 3. Charge and electrostatics
description: The charge and electrostatics tools PDB2PQR, PROPKA and APBS, as the
  pipeline drives them.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_apbs_input_cleanup_and_250_bytes_per_node
  at: '2026-10-16T00:00:00Z'
sources:
- id: wp17-plan
  resource: docs/plans/wp17-packaging-and-ci.md
  title: WP17 packaging and CI plan (PyPI wheel metadata)
- id: wp27-plan
  resource: docs/plans/wp27-protonation-stage.md
  title: WP27 protonation stage plan, Design §1 (PDB2PQR 3.7.1 source)
tested_with:
  pdb2pqr: 3.7.1
  propka: 3.5.1
  apbs-binary: 3.4.1.1
  numpy: 2.5.2
  scipy: 1.18.0
---

## 3. Charge and electrostatics

| Tool | Version | Licence | Notes |
|---|---|---|---|
| **PDB2PQR** | 3.7.1 (Dec 2024) | BSD-3 | Python API `pdb2pqr.main`. Produces protonated structure **+ per-atom partial charges + radii** |
| PROPKA3 | 3.5.1 | LGPL-2.1 | pKa only; shipped as a PDB2PQR dependency |
| **APBS** | 3.4.1 | BSD-3 | Poisson–Boltzmann cross-check. Driven by input files; read `.dx` with `gridData`. `apbs-binary` pip wrapper exists |
| pKAI / pKa-ANI / PypKa | — | MIT / — / LGPL-3 + proprietary DelPhi | ML or PB pKa. Not integrated with PDB2PQR |

**Verified CLI facts [tested: pending]:** `--ff`, `--ffout`, `--with-ph`, `--titration-state-method`,
`--drop-water`, `--keep-chain` all exist; `CHARMM`, `AMBER`, `PARSE` are valid force fields.
**`--titration-state-method` accepts `propka` ONLY** — `pkaani` is rejected by argparse. ML pKa
predictors must be run separately and their states applied by hand.

PDB2PQR ignores PROPKA's `chains` option (relevant for homo-oligomeric pores) but *does* log a
warning — surface it rather than swallowing it.

**Package facts, read from PyPI's metadata on 30 September 2026 [verified]:**[^wp17-plan] `pdb2pqr` 3.7.1 is
BSD-3, a pure-Python wheel, and requires Python ≥ 3.11, < 4. `propka` 3.5.1 is **LGPL-2.1** by its
licence field and classifier, and is a pure-Python wheel. `SPECIFICATION.md` §2.6 called it BSD
until that day. There is no `apbs` package on PyPI. `apbs-binary` 3.4.1.1 packages the BSD-3 APBS
under Apache-2.0 and ships wheels for manylinux_2_28 x86_64, macOS 10.15 x86_64 and macOS 12
arm64, **none for Windows**. So VAL-06 can run on the Linux and macOS CI legs only (§8.2.4 D3).

APBS keywords for the cross-check: `chgm` ∈ {spl0, spl2, **spl4**} (spl4 = quintic B-spline,
least grid-sensitive); `srfm` ∈ {mol, **smol**, spl2, spl4}. Note `spl2`/`spl4` surfaces "may
produce unphysical results at non-zero ionic strengths" — run the cross-check at **zero** ionic
strength, which also isolates charge-projection error from model differences.

### PDB2PQR 3.7.1 and PROPKA 3.5.1 as a per-frame driver **[tested: pending]**, 1 October 2026 {#pdb2pqr-371-and-propka-351-as-a-per-frame-driver-1-october-2026}

Measured in this container while planning WP27, with `--ff=CHARMM --ffout=CHARMM --with-ph=7.5
--titration-state-method=propka --drop-water --keep-chain` unless stated. Inputs were cut from the
vendored `tests/data/structures/2wcd.pdb.gz` (chains A–L, 26,844 heavy atoms, no hydrogens, crystal
frame).

- **Python API.** `pdb2pqr.main.run_pdb2pqr(args)` runs in-process and returns
  `(missed_residues, pka_df, biomolecule)`. It always writes the PQR to the output path in `args`,
  and it does not set up logging. `pka_df` is a list of dicts with `res_name`, `res_num`,
  `ins_code`, `chain_id`, `group_label`, `group_type` and `pKa`. Atoms carry `ffcharge` and
  `radius`. `io.get_pdb_file` **fetches from rcsb.org when the input path is not a file**, so a
  driver must pass a path that exists. A multi-MODEL input is read to its first model only.
- **Cost.** The 2WCD dodecamer takes 63.7 s with PROPKA and 11.5 s without it. Chain A alone with
  PROPKA takes 1.6 s, so the cost of PROPKA on the assembly is superlinear in its size. A nine-residue
  fragment takes 0.1 s. Plan for about a minute per frame of a ClyA ensemble, 50 minutes for 50 frames.
- **Q_net.** 2WCD at pH 7.5 gives −60 e, −5 e on every chain, with no residue whose charge
  differs between chains. ClyA-AS is −72 e (`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md`). OPN-04 lists 27
  mutations between the 2WCD sequence and ClyA-AS; whether they account for the −1 e per chain is
  not checked.
- **States that CHARMM cannot hold.** `Biomolecule.apply_pka_values` logs a tuple warning and keeps
  the standard state for `CYS⁻`, `LYS⁰`, `TYR⁻` and `ARG⁰` under CHARMM. On 2WCD that is
  `('CYS 285 A', 'negative')` in every chain (pKa 6.25). Terminal pKas are **never applied**,
  under any force field: the dictionary is filtered by `group_label.startswith(res_name)`, which
  drops the `N+` and `C-` groups, so the terminal branches are dead. PROPKA puts the N-terminus of
  `LYS 8` at pKa 7.48–7.50 across the chains (7.49 in chain A, below pH 7.5), and PDB2PQR keeps it
  charged without a warning. Derive
  unapplied states from `pka_df` and the applied charges, not from the log.
- **Changeable states under CHARMM** are `ASP`/`ASH`, `GLU`/`GLH` and `HIS`/`HIP`. On the fragment
  `GLU 18`–`LEU 26` of chain A, PROPKA at pH 2 gives +0 e, and at pH 8 −3 e. Without a titration
  method, `--with-ph` changes nothing: pH 3 and pH 9 give identical charges.
- **Histidine names pin the state.** With hydrogens stripped, a residue named `HSD` or `HSE` keeps
  that tautomer and is not titrated by PROPKA. `HSE` with its hydrogens present makes PDB2PQR give
  up with a `RuntimeError`. `HIS` is titrated. A driver must therefore strip hydrogens and rename
  protonation variants to their parent before calling PDB2PQR.
- **Output naming.** `--ffout=CHARMM` writes terminal-patch atoms under the residue name `TER`
  (`N TER A 8`, `OT1 TER A 292`). It renames `ILE CD1` to `CD` and the C-terminal `O` and `OXT` to
  `OT1` and `OT2`, and it writes histidines as `HIS` whatever their tautomer. PDB2PQR 2.1.1 had kept
  the real residue name (`GLU HT1`) and `HSE`. Identify a residue by chain, number and insertion code.
- **Coordinates move by relabelling, and flipped groups move a little.** PDB2PQR renames heavy
  atoms in place (`ILE CD1` to `CD`, the C-terminal `O` to `OT1`) and adds 12 terminal `OXT`, as
  `OT2`, by repair. Hydrogen-bond optimisation flips `ASN`/`GLN` amides and `HIS` rings through
  180° about the bond to the group, which is not symmetric about it, so a flipped atom does **not**
  land on its partner's position: on the 2WCD dodecamer in the crystal frame, 140 heavy atoms (the
  `OD1`/`ND2` of 22 asparagines, the `OE1`/`NE2` of 46 glutamines, one histidine's `ND1`, `CD2`,
  `CE1`, `NE2`) lie 0.13–0.15 Å (amides) and 0.19–0.40 Å (the ring) from every input heavy atom, and
  no other heavy atom moves. On the prepared dodecamer of the tests it is 138, worst 0.397 Å. Match
  heavy atoms by position within a residue, never by name, and leave the flippable atoms out of any
  tight positional criterion **[tested: pending]**, 1 October 2026 (WP27; this bullet first said the 140
  carried another atom's position exactly).
- **Fused columns.** The PQR is written in PDB fixed columns, so a coordinate at or below −100 Å
  runs into its neighbour (`-37.705-115.041`). `pdb2pqr.io.read_pqr` splits on whitespace and
  cannot read PDB2PQR's own output in that case.
- **Four-character residue names and patched residues.** `Atom.get_common_string_rep` writes a
  four-character residue name (`ASPP`, `GLUP`) from column 17, the PDB alternate-location column,
  and a shorter one from column 18; a four-character atom field then runs into it (`OD2ASPP`). A
  residue patched to a protonation variant is written with its backbone under the parent and its
  side chain under the variant: `ASP 21` of the fragment `GLU 18`–`LEU 26` at pH 2 carries both `ASP`
  and `ASPP`. A reader that takes columns 18–21 reads `SPP` **[tested: pending]**, 1 October 2026 (WP27).
- **Disulfides, waters, `HETATM` and the C-terminal carboxyl.** Under `--ffout=CHARMM` a
  disulfide-bonded cysteine's `CB` and `SG` are written `1CB` and `1SG` under the patch residue
  `DISU` (`1CBDISU A 285`), its other atoms under `CYS`; under `SWANSON` and `PEOEPB` the whole
  residue is `CYX`. A reader naming residues by their atoms must treat `DISU` as it treats `TER`
  **[tested: pending]**, 1 October 2026, `CYS 285` of 2WCD chain A bonded to a mirrored copy (WP27 review).
  `--drop-water` drops only `HOH` and `WAT` (`aa.WAT.water_residue_names`), and a water kept under
  CHARMM is `TP3M`. `HETATM` with a five-digit serial is written with nothing between them
  (`HETATM12345`, `get_common_string_rep`) **[verified][^wp27-plan]**, read from the 3.7.1 source. PROPKA types
  the C-terminus `COO`, as it does a side-chain carboxyl, and only its label says `C-`: a C-terminal
  `ASP` or `GLU` carries two `COO` groups (`ASP  21 A`, `C-   21 A`) **[tested: pending]**, 1 October 2026.
- **`run_pdb2pqr`'s first return is missing atoms**, not residues: the atoms
  `Biomolecule.apply_force_field` could not parameterise, which the PQR leaves out. An atom
  written with no charge gets `0.0000` (`get_pqr_string`) **[verified][^wp27-plan]**, read from the 3.7.1
  source, 1 October 2026.
- **PROPKA 3.5.1 fails on Python 3.14.** `Parameters.parse_line` dispatches on
  `self.__annotations__`, and under PEP 649/749 annotations are a class attribute only: on an
  instance the lookup raises `AttributeError: 'Parameters' object has no attribute '__annotations__'`
  on the parameter file's first line, so every titrated PDB2PQR run fails (CI, Python 3.14.7;
  reproduced on 3.14.0rc2). Assigning `Parameters.__annotations__` does not help, because the type's
  descriptor stores it where instance lookup does not look. A `__getattr__` on the class answering
  that one name from `type(self).__annotations__` does, and the dispatch is unchanged: the fragment
  `GLU 18`–`LEU 26` at pH 2 gives byte-identical PQRs and equal pKas on 3.12 and on 3.14 with it.
  3.5.1 is the latest release (PyPI, 1 October 2026). `charge/protonation.py`'s
  `restore_propka_annotations` installs it only where the instance lacks the attribute
  **[tested: pending]**, 1 October 2026 (WP27).
- **The stage's cost.** Protonating the prepared 2WCD dodecamer through the `protonation` stage
  takes 97.4 s and 0.44 GB peak RSS for one cold frame, in a fresh process; with the frame cached
  the stage's own work (reading the PQR, registering it, tabulating the states, checking the radii)
  is 3.4 s. PDB2PQR alone on the crystal-frame dodecamer took 98 s in the same container that
  day, against the 63.7 s above: the difference is the machine, not the stage. On that frame PROPKA puts the `LYS 8` N+ pKa at 7.481–7.499 in every chain, so all twelve
  N-termini are unapplied at pH 7.5, and it warns `Missing atoms or failed protonation for HIS 292
  A`; `Q_net` is −60 e **[tested]**, 1 October 2026 (WP27, `tests/tier2/test_protonation_2wcd.py`).
- **Zero radii.** On chain A, `AMBER` gives 53 charged atoms radius 0, `PARSE` 93, and `TYL06`
  2269. `CHARMM`, `PEOEPB` and `SWANSON` give none. Every force field gives −5 e on chain A, and
  every printed charge has at most four decimals.
- **Logging.** The loggers are `PDB2PQR3.7.1` (`pdb2pqr.main.VERSION`), `pdb2pqr.*` and
  `propka.*`. PROPKA's full report is logged at INFO, about 400 kB for the dodecamer. Importing
  `pdb2pqr` calls `logging.captureWarnings(True)`.

### APBS 3.4.1 driven by maps **[tested: pending]**, 1 October 2026 {#apbs-341-driven-by-maps-1-october-2026}

Measured in this container while planning WP29 (VAL-06), with `apbs-binary` 3.4.1.1 installed into
a scratch environment. Lengths in the deck and the maps are in Å, and the potential is in `kT/e` at
the deck's `temp`.

- **The package.** The Linux wheel is tagged `py3-none-manylinux_2_28_x86_64`, so one wheel serves
  every Python. It holds a static `apbs` (banner `APBS 3.4.1`, built 29 April 2022) and the tools,
  33 MB in all. On macOS arm64 the binary needs `DYLD_LIBRARY_PATH` set to the package's `lib/`.
  `apbs_binary.run_apbs` and `popen_apbs` set it, and they take `subprocess.run` and `Popen`
  arguments.
- **A molecule is mandatory.** A deck with every input supplied as a map, but no `mol`, stops with
  `PBEparm_check: MOL not set!`. A one-atom, zero-charge PQR placed outside the box satisfies it.
- **`READ charge` is in e Å⁻³.** A unit Gaussian sampled at the nodes is reported as `Charge map
  integral = 1.00e+00 e`. With `usemap charge`, `chgm` has no effect on the map.
- **The three `READ diel` maps are staggered.** The x-map's origin is the grid's plus `h/2` in x,
  and likewise for y and z. APBS samples each at the edge midpoints. An x-map on the node grid
  aborts with `Vpmg_fillco: Off dielXMap at: (x,y,z) = …` and `VASSERT: ASSERTION FAILURE` at
  `vpmg.c:4191`.
- **No kappa map at zero ionic strength.** A deck with no `ion` line and no `kappa` map runs.
- **`bcfl map` exists.** It needs `usemap pot`, takes the face values of the potential map, and warns
  `External energies are not used in BCFL_MAP calculations`.
- **Accuracy on closed forms.** All runs use `bcfl map` from the exact potential.
  - **A unit Gaussian** (`w` = 0.1 nm) in uniform ε, point-sampled, has a maximum interior error of
    0.32, 0.079 and 0.020 `kT/e` at `h` = 0.0625, 0.031 and 0.016 nm. That is second order.
  - **A Gaussian ring in a dielectric sphere** has radius 1 nm, height 0.5 nm and `w` = 0.1 nm. The
    sphere has `a` = 2 nm and ε 20, in water at 78.15. The charge map is hat-weighted from an
    (r, z) lattice and conserves to 10⁻¹⁶. The table gives the maximum fluid error, at least
    0.2 nm outside the sphere, relative to the fluid's maximum |φ|.

    | `h` (nm) | Point-sampled diel | Harmonic mean (8 per edge) |
    |---|---|---|
    | 0.2 | 0.53 % | 0.27 % |
    | 0.1 | 0.25 % | 0.14 % |
    | 0.05 | 0.11 % | 0.043 % |

    Point sampling is first order. Inside the sphere the harmonic mean's rms error falls by 4 per
    halving. Averaging arithmetically across each edge's dual face before the harmonic mean is
    *worse* than the harmonic mean alone: 0.42 % and 0.25 % at 0.2 and 0.1 nm.
  - **Node-centred values declared at the staggered origin** give 2.05 % max and 0.53 % rms on the
    fluid at 0.1 nm. That is wrong, but within a loose gate, so it is caught against the closed
    form and not by a two-solver comparison.
- **Cost.**

  | Grid | Wall-clock | Peak RSS |
  |---|---|---|
  | 65³ | 1 s | 0.11 GB |
  | 129³ | 11 s | 0.52 GB |
  | 193³ | 44 s | 1.9 GB |

  This is about 250 B per node.
  The maps APBS reads are about 0.6 GB of text at 193³, which `run_apbs` deletes once read **[tested: tests/tier1/test_knowledge_arithmetic.py::test_apbs_input_cleanup_and_250_bytes_per_node]**.
- **Case identity cost** (`validation/comsol.py`): hashing the 84 MB reference charge table takes about 1.6 s;
  hashing the 9.2 MB deposited 2WCD structure files takes 12 ms, plus 0.7 s on the first import of stage 1 and
  MDAnalysis **[tested: pending]**.
- **Self-refinement on 2WCD.** The problem is `poisson` on the protonated, prepared 2WCD at the
  default mesh (44,987 elements), with both electrodes grounded. The box is 19.2 nm, with the faces
  from our own `P2` solution. The probes are 555,535 fluid nodes of the 0.2 nm grid, at least 0.3 nm
  from every solid. On them, max |φ| is 19.3 `V_T` (0.50 V) and the rms is 7.2 `V_T`.

  | Difference | max | rms | axis, 93 nodes |
  |---|---|---|---|
  | APBS 0.1 nm against 0.2 nm | 0.189 `V_T` (0.98 %) | 0.17 % | 0.57 % |
  | Our `P3` against `P2` | 0.047 `V_T` (0.24 %) | 0.01 % | 0.013 % |

  APBS's maximum lies in the lumen. At 0.5 nm from the solids it is 0.77 %. The difference between
  the two solvers was not formed; VAL-06's tolerance was stated first (`SPECIFICATION.md` §7.4
  NOTE on VAL-06).

### APBS in the VAL-06 driver **[tested: pending]**, 1 October 2026 {#apbs-in-the-val-06-driver-1-october-2026}

Measured while implementing WP29 (`src/nanopnp/validation/apbs.py`), in this container with 24
cores, on `apbs-binary` 3.4.1.1 from the `apbs` dependency group.

- **APBS's log reports its own memory**: `Final memory usage: … MB total, X MB high water`. The
  child's `ru_maxrss` from `wait4` is not that number on Linux. It is a high-water mark kept across
  `execve`, so it includes the pages of the Python process that forked it. Under pytest it read
  1.42 GB for a 97³ run whose own high water was 0.24 GB. The driver reads the log.
- **At `h` = 0.1 nm, "e per node" and "e per Å³" are the same number**, because a cell is 1 Å³. A
  charge map left undivided by `h³` is therefore invisible at 0.1 nm. It shows at 0.2 nm as a factor
  of 8, so the ring checks that broken construction on the nested grid.
- **APBS writes an OpenDX header's `origin` and `delta` at `%12.6e`**, seven significant figures,
  whatever precision the input maps carried. A 33³ grid at 0.1234567891 nm comes back at
  0.1234568 nm, so a check that the output matches the problem's grid must allow about 5 × 10⁻⁷
  relative (the driver allows 10⁻⁶, and 10⁻⁴ `h` on the origin). Found by the WP29 review.
- **The ring in a grounded dielectric sphere** (`r_b` 1 nm, `z_b` 0.5 nm, `w` 0.1 nm, `a` 2 nm, ε 20
  in `ε_r,f⁰`, `R` 20 nm), with the faces from the series, 65³ at 0.1 nm and about 18,000 fluid
  probes. APBS is within 0.13 % max, 0.027 % rms and 0.13 % on the axis of the series. Our `P2`
  deposit and solve (53,009 elements, 0.05 nm inside 6 nm) is within 0.010 %, 0.016 % and 0.010 %.
  The broken constructions, against half the tolerance (1.5 %, 0.5 %, 0.75 %):

  | Construction | max | rms | axis |
  |---|---|---|---|
  | No `1/h³`, on the 0.2 nm grid | 364 % | 208 % | 341 % |
  | `2πr` dropped from the lattice mass | 44 % | 25 % | 41 % |
  | Charge point-sampled, `w` = 0.0112 nm | 409 % | 234 % | 384 % |
  | Node-centred diel declared staggered | 1.98 % | 0.59 % | 1.67 % |
  | `temp` 310 K against 298.15 K | 1.96 % | 1.13 % | 1.99 % |
  | Charge 0.5 nm off in z | 31 % | 11 % | 29 % |
  | `bcfl zero` | 54 % | 74 % | 54 % |
  | Charge zeroed | 52 % | 30 % | 49 % |

  The temperature row is half of the 3.8 % that the ratio 310/298.15 predicts, because the faces
  hold our potential and only the charge's part of the interior scales.
- **The gated leg on 2WCD.** This is the protonated, prepared dodecamer at the default sizes
  (44,985 elements), solved with `poisson` and both electrodes grounded. The box is 193³ at 0.1 nm
  from (−9.6, −9.6, −4.35) nm, with 569,541 probes and 93 on the axis. The refinement estimates
  and the agreement are in `SPECIFICATION.md` §7.4 (the NOTE on VAL-06): 0.41 %, 0.10 % and
  0.23 %, inside a budget of 1.20 %, 0.18 % and 0.59 %. The largest difference, 0.080 `kT/e`
  where ours is −17.8, lies at r = 1.80 nm, z = 0.25 nm, beside the constriction.
- **APBS's order on 2WCD.** A focused 193³ grid at 0.05 nm on the axis takes its faces from the
  0.1 nm solution, interpolated trilinearly, and the charge inside it, clipped. Over 34,637 probes,
  `|φ(0.1) − φ(0.2)|` is 0.184 and `|φ(0.05) − φ(0.1)|` is 0.059 `kT/e` at most. That is an order of
  1.64 in max and 1.61 in rms, so the 0.1-against-0.2 nm difference bounds APBS's error at 0.1 nm.
- **The recorded leg on 2WCD.** APBS takes `spl4` and `smol` (`srad` 1.4 Å, `swin` 0.3 Å, `pdie`
  20) from the same PQR in the model frame. 2,651,142 edges in our membrane are set to 3.2. The
  comparison is over the 454,325 probes whose ring lies inside the box, at 24 angles. The ring means
  differ from ours by 15.7 % max, 6.7 % rms and 13.6 % on the axis. APBS at the nodes differs by
  77 % max, near atoms. The spread around a ring reaches 46 % of `max|φ|`, at 4.1 % rms.
- **Cost on 2WCD.** The `P2` walk takes 15 s and the `P3` walk 8 s, with stages 1–3 and the
  protonation seeded. The raster of 2.7 M cells takes 10 s and the maps 3 s. APBS takes 29 s at
  193³ (1.83 GB high water) and 3.3 s at 97³ (0.24 GB). The test process peaks at 1.38 GB. Writing
  one 193³ OpenDX map takes 3.5 s and 126 MB, and GridDataFormats reads it back in 2.4 s. The
  module, with the recorded leg and the focus under `-m slow`, takes 5 minutes.

---

[^wp17-plan]: `docs/plans/wp17-packaging-and-ci.md` and `uv.lock` (PyPI metadata for `pdb2pqr` 3.7.1 and `propka` 3.5.1).
[^wp27-plan]: `docs/plans/wp27-protonation-stage.md`, Design §1 (`pdb2pqr` 3.7.1 `get_common_string_rep` and `get_pqr_string`).
