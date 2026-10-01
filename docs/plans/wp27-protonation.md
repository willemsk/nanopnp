# WP27 — Protonation: the PDB2PQR driver and the PQR artefact (FR-12)

**Status: delivered, 1 October 2026.** Planned 1 October 2026, on `main` at `6a9478b` (WP26 merged, to be
tagged `v0.4.0-alpha.1`). The second package of Phase 3. It inherits stage 1's `AlignedEnsemble`
and frame (WP18 D16), the CHARMM radius set of `data/radii/` (WP19), the supply chains of
`io/case.py` and the frozen schema v2 (§8.2.2 B3), and the stage registry and walk of `core/stages.py`
and `io/run.py`. Nothing in it touches a weak form.

This plan belongs to [Phase 3](phase-3-charge-pipeline.md). `SPECIFICATION.md` governs; identifiers
here are pointers into it. The spec amendments this package needs are made in this plan's commit:
the §5.2 rows for stage 7 and the design note on its number, the PHY-16 NOTE on protonation as run,
the §5.3.1 NOTE on the protonation keys, the `inputs.pqr` paragraph of the §5.3.1 NOTE on `inputs:`
(§8.2.4 D4 assigns it here), the §5.3.2 artefact row and the IF-02 export NOTE. The PDB2PQR facts
they rest on are in `.knowledge/07` §3, *PDB2PQR 3.7.1 and PROPKA 3.5.1 as a per-frame driver*.

## Execution brief

**Scope.** A registered `protonation` stage runs PDB2PQR with PROPKA on every frame of stage 1's
ensemble, or reads a supplied `inputs.pqr`, and emits a per-frame atom table with charges, radii,
`Q_net` and residue states (FR-12; adds to FR-27, IF-03, QR-12). The `charge:` section and
`inputs.pqr` become runnable. Nothing consumes the artefact yet: stage 7's deposition is WP28.
The brief runs past its 1,200-word target because the supplied path carries gates of its own
(D9, D12) that cannot be deferred without leaving `inputs.pqr` unchecked.

**Read first.** PHY-16 and its step-3 NOTE; §5.2 stage 7; the §5.3.1 NOTEs on `inputs:` and the
protonation keys; `.knowledge/07` §3.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Stage number | `protonation` is stage **7**, sharing it with `charge`, registered first; the registry sorts by number, then registration order | Renumbering would move stages 8–12 in the spec and every manifest. §5.2 note |
| D2 | Walk position | `PIPELINE`: after `mesh`, before `charge` | `upto="mesh"` (the GUI's build) must never protonate. The walk stays a prefix: declared inputs are incomplete (`solve` omits `charge`) |
| D3 | Walk selection | Until WP28, `protonation` runs only as an explicit target (`upto`, `nanopnp stage protonation`) of a case with `structure:` or `inputs.pqr`, and is otherwise recorded not run | A stage nothing reads is not run (stage 7's rule); spares every `structure:` walk a minute per frame |
| D4 | Imports | `charge/pqr.py` (reader, writer) and `charge/protonation.py` (stage, driver). `pdb2pqr` is imported inside the driver; the registry entry has no `extra`; a driver run without it raises `MissingExtraError` naming `structure` before the first frame | `inputs.pqr` needs no extra (`CLAUDE.md`'s optional-extra exception). Amends the phase plan |
| D5 | What PDB2PQR is given | Per frame, a heavy-atom PDB from our own fixed-column writer: Å to 0.001, hydrogens dropped, the protonation-variant names of the PHY-16 NOTE written as their parent, each stage-1 chain key mapped to one character (more than 62 chains refused) | PHY-16 step-3 NOTE; *Design* §1. Our bytes, not MDAnalysis's, because their digest keys the frame (D10) |
| D6 | The call | `run_pdb2pqr` in-process with PHY-16 step 3's flags at `charge.ph` and `charge.forcefield` (`--ff` = `--ffout`); `titration: none` passes neither `--titration-state-method` nor `--with-ph`. The PQR it writes is read back through `charge/pqr.py` | One reader for both supply routes, so produced and supplied artefacts are the same object |
| D7 | Logs | During the call the `PDB2PQR<version>`, `pdb2pqr` and `propka` loggers are raised to WARNING; warnings go to the summary with counts and are re-logged once each | PROPKA logs ~400 kB at INFO; surface, never swallow |
| D8 | Residue states | Per frame and residue: applied charge, histidine tautomer from `HD1`/`HE2`, PROPKA pKa per group, **unapplied** where the applied charge differs from Σ PROPKA group states at the pH (*Design* §2). A residue whose charge differs between chains of identical sequence is listed per frame. Recorded, not gated | PHY-16 step-3 NOTE; §8.2.4 D4. Terminal pKas are never applied, so the log cannot be the source |
| D9 | Gates (QR-12) | Per frame: a residue PDB2PQR missed; an atom without charge or radius; a charged atom with radius ≤ 0; `\|Q_net − round(Q_net)\| > 10⁻⁶` e. Each names the frame and residue or atom. `ProtonationError` → exit 4. A malformed or mismatched PQR → `PQRError` → exit 3 | VER-57; PHY-16 step 4 needs `w_i > 0` |
| D10 | Keys and per-frame cache | Stage key: schema `nanopnp/protonation/v1`, parameters (pH, force field, titration, argument list, normalisation table), input the stage-1 key. Each frame also stored as `nanopnp/protonation-frame/v1`, keyed on the frame PDB's digest and the same parameters. The stage takes `store=`; `io/run.py` gains `STORE_STAGES`, asserted against constructors as `WORKSPACE_STAGES` is | Phase decision: cached per frame. Versions recorded beside the key (§5.3.2) |
| D11 | Payload | `protonation.npz`: atom arrays concatenated over frames with `frame_offsets` (frames differ in hydrogen count); `positions_nm`, `charge_e`, `radius_nm` float64; identity strings; a residue table and `(frames, residues)` arrays for charge, tautomer, unapplied state; group pKas | Hydrogens per frame vary with state. float64 keeps the PQR round trip exact |
| D12 | Supplied PQR | Reader, registration to the ensemble at 0.01 Å, and refusals exactly as the §5.3.1 NOTE on `inputs:`; arithmetic in *Design* §3 | §8.2.4 D4 |
| D13 | Schema | `ph`: [0, 14], finite. `forcefield`: `Literal["CHARMM", "PEOEPB", "SWANSON"]`, asserted ⊆ PDB2PQR's set in Tier 1. `titration` and `forcefield` move to `SWITCH_PATHS` (defaults `propka`, `CHARMM`); `charge.titration` leaves `CONFIGURATION_PATHS`. Refusals per the §5.3.1 NOTEs. `charge` leaves `_PIPELINE_SECTIONS`, `pqr` leaves `_UNCONSUMED_INPUTS`; `ResolvedCase` gains the PQR and the protonation keys | §5.3.1 NOTE on the protonation keys; zero radii measured |
| D14 | Radii | With CHARMM the stage compares each PQR atom's radius with `RadiusSet.radius_A` for its residue (histidine by tautomer, termini by patch) and records counts and the worst difference. Tier 2 asserts none on 2WCD | Phase decision on radii: a disagreement is a defect to find |
| D15 | Cancellation | Checked, and progress reported, between frames; a frame runs to completion (≈64 s on 2WCD); frames run serially | Cooperative tokens; the GUI's walk is a terminable child |
| D16 | Manifest, export | A `PROTONATION_RECORD_KEYS` record feeds the *Charge* group (`Q_net`, force field, pH, titration); `propka` joins `DISTRIBUTIONS`; `--export X.pqr` per the IF-02 NOTE | §5.3.3; FR-27 |
| D17 | Tier 2 cost | The prepared 2WCD dodecamer is protonated with PROPKA once per session (≈64 s), through the stage API rather than a walk, in a `protonated_2wcd` fixture under the `prepared_2wcd` lock, for WP28 and WP29 to reuse | The gate's 2WCD charge needs PROPKA anyway |

### Outcomes

> **Outcome — D12 and *Design* §1 corrected: a flip moves atoms, it does not exchange them.** The
> plan matched heavy atoms by position on the premise that PDB2PQR's amide and ring flips leave 140
> heavy atoms of 2WCD exactly on another atom's position. Measured on the dodecamer, they land
> 0.13–0.15 Å (`ASN`/`GLN` amides) and 0.19–0.40 Å (one `HIS` ring) from every heavy atom they were
> given; no other heavy atom moves. The 0.01 Å criterion over every heavy atom would have refused
> PDB2PQR's own output and our own export. The flippable atoms (`ASN OD1 ND2`, `GLN OE1 NE2`,
> `HIS ND1 CD2 CE1 NE2`) are now left out of the criterion, counted and their worst distance
> recorded; the rest of each residue fixes the frame. Amended in the §5.3.1 NOTE on `inputs:` and
> `.knowledge/07` §3. On the prepared dodecamer: 138 flipped, worst 0.397 Å, worst compared residual
> 0.00085 Å.

> **Outcome — two PDB2PQR layout facts the reader's own cross-check found.** On the fragment at
> pH 2, PDB2PQR writes `ASPP` from column 17, fuses a four-character atom field into it
> (`OD2ASPP`), and writes a patched residue's backbone as `ASP` and its side chain as `ASPP`. The
> columns-against-fields cross-check refused the first two rather than misreading them: a residue
> name is now read from column 17 where that column is not blank, a whitespace field longer than a
> name can be does not read the line, and a parent beside one of its variants names the residue
> by the variant. Amended in the §5.3.1 NOTE on `inputs:`; tested in `tests/tier1/test_pqr.py`.

> **Outcome — the self-check D6 did not ask for.** The produced route runs the supplied route's
> registration on PDB2PQR's PQR against the frame it was given, without moving it, and refuses a
> frame whose residues or heavy atoms PDB2PQR did not keep. It is the gate that fires on dropped
> atoms (`tests/tier1/test_protonation.py`).

> **Outcome — D13 widened.** Beside `inputs.pqr` the protonation keys were refused set away from
> their defaults; they now are also beside `inputs.charge`, and where the case has neither
> `structure:` nor `inputs.pqr`, by the same rule. `charge.smearing`, `exclusion_offset_nm` and
> `dielectric_transition_nm` raise `UnsupportedCaseSection` naming WP28 or WP30. Amended in the
> §5.3.1 NOTE on `inputs:`.

> **Outcome — measurements.** Prepared 2WCD dodecamer at pH 7.5, CHARMM, PROPKA, PDB2PQR 3.7.1,
> PROPKA 3.5.1: `Q_net` −60 e, −5 e on every chain, pinned as the Tier-2 golden; 54,084 atoms
> compared with the stage-2 table, none differing; 12 `OT2` added; `CYS 285` unapplied in every
> chain; the `LYS 8` N+ pKa 7.481–7.499, below 7.5 in every chain, so every N-terminus is
> unapplied. One cold frame costs **97.4 s and 0.44 GB** peak RSS in a fresh process (`-m slow`);
> the stage's own work with the frame cached is 3.4 s, and PDB2PQR alone on the crystal frame took
> 98 s in the same container that day, against the 63.7 s measured while planning, so D17's
> fixture costs about 100 s of the push gate rather than 64 s. `Q_net` is recorded as an integer per
> frame, with its residual beside it (an exact `fsum` of four-decimal charges leaves ~1e-16 e).

> **Outcome — Tier 3 not run.** The archived PQRs are not under `$NANOPNP_REFERENCE_DATA` here.
> `tests/tier3/test_protonation_archive.py` was dry-run against the 2WCD export as a stand-in
> archive, so its reading, chain pairing and registration legs are exercised; its numbers are the
> nightly's to record.

### Work items

1. `charge/pqr.py`: frames, reader (fixed columns, whitespace fallback, cross-check, `TER`
   names), writer. Read *Design* §1 first.
2. `core/stages.py`: register `protonation` (D1), registration-order sort.
3. `charge/protonation.py`: PDB writer and normalisation (D5), driver (D6, D7), states (D8, *Design*
   §2), gates (D9), keys and frame cache (D10), payload (D11), registration (D12, *Design* §3),
   radii (D14),
   export (D16).
4. `io/case.py`, `io/defaults.py`: D13 and the §5.3.1 refusals.
5. `io/run.py`, `io/manifest.py`: `PIPELINE`, `selected_stages` (D3), `_WEIGHTS`, `STORE_STAGES`,
   the `pqr` role in `input_files`, D16. `cli/errors.py` (D9); the CLI export.
6. Tests below; `tests/conftest.py` gains `protonated_2wcd` and a fragment cutter over the vendored
   2WCD (no new vendored file).
7. `SPECIFICATION.md`: the VER-57 row and Appendix A (FR-12, IF-03, FR-27, QR-12 → VER-57).
   `CHANGELOG.md` under `v0.4.0-alpha.2`. Any documented `stage --list` output. No public name is
   added; the stage is reached through the registry.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance |
|---|---|---|---|
| `tests/tier1/test_pqr.py` | 1 | VER-57, IF-03 | Fixed columns, fused coordinates, whitespace PQR, a line read two ways differently (refused, line named), `TER` names, `MODEL` frames, a residue set differing between models (frame named). Writer → reader is exact |
| `tests/tier1/test_protonation.py` | 1 | VER-57, FR-12, QR-12 | On fragments of 2WCD chain A: charges equal `CHARMM.DAT`, parsed independently, to 10⁻⁶ e, and `Q_net` the hand count; `none` at pH 3 and 9 identical; PROPKA at pH 2 and 8 changes `GLU 18`, `ASP 21`, `ASP 25`; `HSE`-named `HIS 292`, with or without hydrogens, equals `HIS`-named; the N-terminus at pH 9 is unapplied. Each D9 gate, and each mismatched `inputs.pqr` (frame count, residue, another frame), names its frame. A moved PQR registers to 0.01 Å; the export re-supplied is bitwise the payload. One changed frame of two re-protonates one. With `pdb2pqr` blocked, `structure:` is refused naming the extra and `inputs.pqr` runs |
| `test_stages.py`, `test_run.py`, `test_case_schema_v2.py`, `test_manifest.py`, `test_cli.py` | 1 | VER-25, VER-32, VER-47, VER-24 | Listing imports no `pdb2pqr` or `propka`; registry order; D3 and its refusal; each D13 refusal names its keys; switches classified; other export suffixes refused |
| `tests/tier2/test_protonation_2wcd.py` | 2 | VER-57, FR-12 | Prepared 2WCD at pH 7.5: `Q_net` integral and equal to its golden (−60 e measured in the crystal frame, re-measured once in stage 1's and pinned; the failure names the PDB2PQR and PROPKA versions); every heavy atom's radius equals the CHARMM table's; 12 repaired `OXT`; `CYS 285` unapplied in every chain, and the `LYS 8` N-terminus where its pKa (7.48–7.50) is below 7.5; export → `inputs.pqr` beside `structure:` gives the payload |
| `tests/tier3/test_protonation_archive.py` | 3, recorded | VER-57 | DCD frames 48–97 through the driver against archived PQRs 50–99: per-residue charge and tautomer agreement, `Q_net` per frame against −72 e. The archived PQRs through `inputs.pqr`, registered: worst residual. Skips without `prod5_protein_aligned_100ps_NN.pdb.pqr` |
| `-m slow` | — | — | Wall-clock and peak memory per frame |

`uv run pytest tests/tier1/test_pqr.py tests/tier1/test_protonation.py tests/tier2/test_protonation_2wcd.py -v`,
then the full gate.

### Out of scope

Deposition, `charge.smearing`, the default walk and the `centre_z_nm` shift into the mesh's frame
(WP28); APBS (WP29); `χ` and the exclusion shell (WP30); the GUI and bundling PDB2PQR's data files
(WP31, RSK-13); the user guide (WP32); frames in parallel (no owner; the cost is measured);
structure preparation, ML pKa and charge regulation (phase exclusions).

### Open questions

None blocking. Close calls the author may overrule without disturbing the rest: D5's renaming of
`HSE` to `HIS`, which lets PROPKA titrate a histidine the reference pinned; D13's three force fields;
D3's target-only walk; D4's deferred import; D17's 64 s in the push gate. **The author** extracts
the archived PQRs under `$NANOPNP_REFERENCE_DATA` for Tier 3.

## Design

### 1. PDB2PQR as measured

`.knowledge/07` §3 records the measurements this plan rests on. The decisions they force are:
residue identity by chain, number and insertion code, because `--ffout=CHARMM` writes `TER`
(D11, the reader); heavy-atom matching by position, because amide and ring flips relabel 140 heavy
atoms of 2WCD (D12); hydrogens stripped and variants renamed, because `HSD`/`HSE` pin the state and
`HSE` with hydrogens fails (D5); an explicit input path, because a missing one is fetched from rcsb.org
(D6); unapplied states derived from data (D8, §2); the force-field set (D13).

### 2. Unapplied states [verified]

For each PROPKA group with pKa `p` at the case's pH, the preferred charge is: acids (`COO` of
`ASP`/`GLU`, `C-`, `CYS`, `TYR`) `−1` if `pH ≥ p`, else `0`; bases (`HIS`, `LYS`, `ARG`, `N+`) `+1` if
`pH < p`, else `0`. These are the comparisons `Biomolecule.apply_pka_values` makes. A residue's
expected charge is the sum over its groups, terminal groups included, and its applied charge is
Σ atomic charges, an integer to 10⁻⁶. Unapplied means the two differ. On 2WCD at pH 7.5:
`CYS 285`, `p = 6.25 ≤ 7.5`, expects −1, applied 0. `LYS 8` in chain A: `N+` at 7.49 expects 0 and
the side chain (pKa 10.75) expects +1, total +1, applied +2. Across the chains the `N+` pKa is
7.48–7.50 as printed, so whether the N-terminus is unapplied varies by chain, and the per-chain
diagnostic will show it: the comparison uses the unrounded pKa from `pka_df`. Neither appears as a PDB2PQR warning except the
cysteine's. Group types other than these eight are recorded and not compared.

### 3. Registration [verified]

A PQR coordinate printed to 0.001 Å is off by at most 0.0005 Å per component, 0.00087 Å in norm.
Stage 1 stores float32 nm, whose spacing at 15 nm is 9.5 × 10⁻⁷ nm (9.5 × 10⁻⁶ Å). The tolerance is
0.01 Å, about ten times their sum. The shortest heavy-atom bond is 1.23 Å (C=O), so at most one PQR
heavy atom lies within 0.01 Å of any point, and matching within a residue by nearest neighbour is
unambiguous. The archive's frames lie 0.095–0.219 nm RMSD from frame 0 (`.knowledge/04` §1.1),
a hundred times the tolerance. Consecutive frames are not measured; Tier 3 records the smallest
heavy-atom RMSD between neighbouring frames as the margin by which a frame offset by one is refused.
The fit
is Kabsch over Cα, one per residue in both, at least three. A frame whose heavy atoms already
satisfy the criterion is not moved (§5.3.1 NOTE), so the stage's export round-trips bitwise.
