# WP31 — GUI increment 3: the charge pipeline surfaced

**Status: planned, not started.** Written 2 October 2026, after WP30 merged on `main` (`11bc2c8`,
to be tagged `v0.4.0-alpha.5`). This package inherits the desktop shell of WP14, WP15 and WP24:

- the spawned child, its `RunEvent` queue and `RunRequest.upto`;
- `StageHook`, `SolveHook` and `ArtefactHook`, none of which is an input;
- the Qt-free view-models, asserted on `sys.modules` in a fresh process;
- `ImageModel` and the hand-stroked `QPainter` canvas (WP24 D11, D13);
- the render child, which writes a webgui scene under the run's `viewer/` (WP15 D8–D10, WP24 D12);
- the probe bundle, its `PAYLOADS`, its exercises and its CON-11 notice (WP24 D16, D17).

It also inherits what Phase 3 produced:

- `protonation`'s `nanopnp/protonation/v1` artefact, with its per-frame table (WP27);
- stage 7's `nanopnp/fields/v1` artefact, which holds the export lattice, the element-wise deposit
  and its conservation report (WP28);
- the derived `χ` and the `exclusion` shell (WP30).

This is a work package of the [Phase 3 plan](phase-3-charge-pipeline.md). `SPECIFICATION.md`
governs. Where this file and the specification disagree, the specification is right and this file
is wrong. Identifiers here are pointers, never restatements. This plan's commit amends the
ADR-004 packaging NOTE (D15). Everything else in the specification changes with the code.

## Execution brief

### Scope

The §8.1 GUI increment for Phase 3, which is phase criterion 6:

- set the pH and the force field from the case editor;
- build stages 1–7 from the shell;
- show the charge, both as the export lattice and as the deployed field, with `χ` beside it;
- show the protonation table per frame;
- show the conservation report, with its legs and its worst plane;
- make the bundle carry PDB2PQR and PROPKA, and have `--selftest` protonate a peptide (RSK-13).

The package adds **VER-60**. It touches:

- the interface: IF-09, QR-10, QR-11 and FR-27;
- the charge stages' records: FR-12, FR-14, FR-15 and PHY-19;
- packaging and licensing: CON-09, CON-11 and RSK-13;
- the shell's scope: RSK-15.

No weak form, gate, tolerance, stage key or case key changes. No physics enters the shell: every
number the views show is read from a stage's own artefact.

**This brief runs to about 1,900 words, over its 1,200-word target.** There are two reasons.
A charge picture can be drawn in a way that looks right and is wrong in sign, frame or integral,
which is RSK-15's failure in its worst form. And the payload set is the RSK-13 surface itself. The
package is not split, because the views share one seam (D1). Without the bundle, criterion 6 is
not met.

### Pointers

- **Normative:**
  - IF-09, QR-10, QR-11, FR-27, ADR-004 and its packaging NOTE;
  - CON-09 and CON-11;
  - §5.2 stage 7, PHY-16 to PHY-20, and the §4.4 NOTEs on the producer path's conservation report
    and on the derived solid fraction;
  - the §5.3.1 NOTE on the protonation keys;
  - §8.1 (the GUI increments);
  - VER-29, VER-43, VER-44, VER-55, VER-57 and VER-59.
- **Amended in this commit:** the ADR-004 packaging NOTE. It now says that a pure-Python LGPL payload
  is collected as source files, and names PDB2PQR and PROPKA (D15).
- **Amended with the code:**
  - the VER-60 row in §7.2;
  - Appendix A, where IF-09, QR-11, FR-27, CON-09 and CON-11 gain VER-60;
  - the recount line.
- **Read first:**
  - [WP24](wp24-gui-geometry-pipeline.md) D1, D4, D11–D13 and D17, and their Outcomes;
  - [WP28](wp28-charge-deposition.md) D9 and its Outcomes;
  - [WP30](wp30-dielectric-and-exclusion.md) D3's Outcome;
  - `.knowledge/07` §3 (PDB2PQR as a driver) and §5 (bundling).

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | How the charge artefacts reach the shell | No new hook or event. `ArtefactHook` already fires for `protonation` and `charge`, and `Produced` carries their schema and hash. The new tab reads `Store(store).get(schema, hash)`. The lattice and the deposit are payloads of stage 7's `fields/v1` artefact. The internal `charge-grid` and `protonation-frame` caches are never read | WP24 D1. WP28 D9 says consumers read the charge only from stage 7's artefact |
| D2 | Building the charge | **Build charge** runs `upto="charge"` through the same spawned child and cancel token as *Build geometry*. It is offered when `"charge" in selected_stages(resolved, None)`, and otherwise it is disabled, with the reason. The Geometry tab still receives the `Produced` events for stages 1–6 | `selected_stages` is public so that the shell does not restate its rule (WP24). A case that does not walk stage 7 has nothing to show |
| D3 | Layout | A seventh tab, **Charge**, after Geometry. It holds a stage list (`protonation`, `charge`) and four panes: **Protonation**, **Charge map**, **Deployed field** and **Conservation**. A case that supplies `inputs.charge` has no protonation pane. A case with neither a supplied `χ` nor a derived one says that its dielectric is the material split | A thin increment (RSK-15). The Geometry tab's `GEOMETRY_STAGES` filter and its `load_view` refusal stay as they are |
| D4 | The frame | Every charge view draws in the **model frame**, and its caption says so. The lattice, the atoms, the deposit and the planes are all in that frame (PHY-16 NOTE on the deposition) | WP24 D4. A picture in the wrong frame is the plausible wrong picture |
| D5 | What the charge map shows | The lattice as stored: the areal density `σ = 2πr ρ`, in C m⁻². Its quantity name and unit come from the `nanopnp/field/v1` vocabulary (`charge/fields.py` `QUANTITIES`, `CANONICAL_UNITS`). The volume density is shown by the deployed-field pane (D7) | `σ` is the charge per unit (r, z) area, so this picture shows where the charge lies in the meridional plane. A picture of `ρ` would overweight the axis by `1/r`. VER-44 requires names and units from the data, never from `gui/` |
| D6 | Reducing the lattice for display | Block means over `k × k` nodes, weighted by the trapezoid weights: `σ̄_p = Σ w_n σ_n / Σ w_n`. `k` is the smallest integer that leaves at most 1,024 pixels along either axis. Pixels follow WP24's convention: centred on the block's nodes, with the edges half a spacing beyond the first and last node. The view reports `Σ_p σ̄_p A_p`, with `A_p = Σ w_n`, beside `Q_net` | Decimation would alias a field that changes sign every 0.035 nm. That is VAL-15's failure, transplanted into the display. The block mean keeps every block's charge, so the integral of the picture is the producer leg's integral exactly. [Design §1](#1-the-picture-keeps-the-charge) |
| D7 | The deployed field | The render child gains a charge request. It draws, on the deployed mesh, the coefficient the solve reads: `charge/stage.py`'s `fixed_charge_density` for `ρ`, and the stage-7 `χ` through the route the permittivity form takes. The name is the IF-07 `rho_fixed_C_m3`. The scene goes to `viewer/charge.{json,html}` or `viewer/chi.{json,html}`. It is never an artefact | One renderer path (WP24 D12). Drawing the solve's own coefficient makes the oracle the conserved charge (Verification) |
| D8 | Colour | `ρ` and `σ` use a diverging table whose centre is zero. The limits are `±L`, where `L` is the largest magnitude drawn, and `L` is printed. `χ` uses the sequential table on [0, 1], fixed. Webgui's autoscale is off for all three | A sign must read as a sign. A scale that moved its zero would make a neutral region look charged |
| D9 | The worst plane | The charge map marks the recorded `mesh_worst_plane_z_nm` and `grid_worst_plane_z_nm` as horizontal lines at those z. On a consumer-path report it marks `worst_plane_z_nm` | Read from the report, never recomputed. Phase criterion 6 names the worst plane |
| D10 | The conservation pane | A Qt-free `ConservationView` is built from `summary["charge"]["conservation"]`, in both its forms (deposited, supplied). For each leg it shows the value, the tolerance and their ratio, all from the record. A leg recorded as not run is shown as not run, with its reason, never as 0. It also shows `q_net_e`, `q_grid_e`, `q_mesh_e`, the quadrature agreement, the axis guard deficit, the boundary ring, and the deposit's `material_charge_e` and solid share | The stage aborts on a failed gate (QR-12), so a stored report always passed, and what it can still show is the margin. Tolerances from the record keep `gui/` free of `CONSERVATION_TOL` |
| D11 | The protonation pane | A frame selector, with `Q_net` per frame. A table of the titratable residues, meaning those with a PROPKA group: chain, number, name, applied charge, pKa, expected charge at the pH, and an *unapplied* flag. It is read from `ProtonationTable` and cross-checked against the summary's `unapplied`. Below it: `chain_differences`, `warnings` with their counts, and `variant` beside `Q_net` (OPN-04). A supplied PQR shows its charges, with pKa reported as *not run* | The §5.3.1 and PHY-16 NOTEs: the unapplied states and the per-chain differences are recorded diagnostics, never symmetrised, so the table shows them as recorded. The arrays are read off the Qt thread (WP24 D11) |
| D12 | pH and force field in the editor | Generated from the schema. A number field whose schema declares both `ge` and `le` becomes a spin box with that range, taken from the field's metadata. It writes only on a user edit, so display rounding never rewrites a loaded value. `charge.forcefield` and `charge.titration` stay combo boxes over their `Literal`s. The shell holds no cross-field rule: `ph` beside `titration: none` is refused by the loader, with its own text | VER-43: no value set and no bound is written in `gui/`. The knob-with-no-effect refusal is the loader's (§5.3.1 NOTE) |
| D13 | An absent `charge:` section | `io/case.py` gains `NEUTRAL_SECTIONS`, the optional top-level sections whose empty mapping resolves exactly as their absence, and `with_section(document, name)`. The set holds `charge`, and `geometry` only if the test shows it qualifies. The editor offers **Add section** for those alone, and writes an empty mapping. Nothing else in the shell creates a section | Without this the pH selector is greyed out on every structure case that does not already have the block, which defeats QR-10. Resolution already reads `Charge()` when the block is absent (`_resolve_protonation`). A block whose presence changes the physics, such as `geometry.analyte`, must never be added from a default. [Design §2](#2-a-section-that-means-nothing-when-empty) |
| D14 | The probe's new payloads | `PAYLOADS` gains `pdb2pqr` and `propka`. The exercise protonates `GLU 18`–`LEU 26` of 2WCD chain A, shipped as `data/structures/2wcd-a-18-26.pdb`, through `charge/protonation.py`'s `run_pdb2pqr`. Settings are `Charge()`'s defaults with only `ph` set, at pH 2 and at pH 8. It requires `Q_net` = 0 e and −3 e, each an integer to 10⁻⁶. A failed PDB2PQR run, or charges with no atoms, names `pdb2pqr`. Equal charges at the two pH values name `propka` | `.knowledge/07` §3 measured both values on this fragment. The pH dependence is what proves that PROPKA and its `propka.cfg` were loaded. Without a titration method, pH 2 and pH 8 give the same charges. Going through the driver also exercises `restore_propka_annotations`. The file exists, so PDB2PQR cannot fetch from rcsb.org |
| D15 | Collecting them | `collect_all("pdb2pqr")` and `collect_all("propka")` carry `pdb2pqr/dat/` and `propka.cfg` beside their modules. Both libraries find their data through `Path(__file__).parent`. **Every pure-Python LGPL payload** is collected as source (`module_collection_mode="py"`): PROPKA, MDAnalysis and GridDataFormats. `LICENSES-BUNDLE.md` gains PDB2PQR (BSD-3), with its notice, and PROPKA (LGPL-2.1), and its "Your rights" section names the source-collected packages | ADR-004 meets the LGPL by keeping replaceable files, and a module inside the PYZ archive is not one. PROPKA is the first LGPL payload that is pure Python, and the same argument covers the two already carried. The ADR-004 NOTE is amended in this commit |
| D16 | The vocabulary check | `test_if09_no_option_list_is_written_in_the_shell` matches `"propka"` and `'propka'` as string literals only, and gains `CHARMM`, `PEOEPB` and `SWANSON`. The `PAYLOADS` tuple is exempt, by AST, because its entries are module names, and the import walk already checks them | A module name is not a case value. WP24 narrowed `hand-edit` in the same way. The probe writes no titration or force-field literal (D14) |
| D17 | The shell | The **Mesh** view already colours by material, so the `exclusion` shell shows as its own material. VER-60 asserts that it is listed. There is no new geometry view | WP30's out-of-scope row. Material-generic drawing is WP24 D12 |

### Work items

In dependency order.

1. `io/case.py`: `NEUTRAL_SECTIONS` and `with_section` (D13).
2. `charge/stage.py`, `materials/fields.py`: the public readers the views need, if missing. These
   are the lattice as a `RadialGrid` with its trapezoid weights, and `χ` on a given mesh. They are
   read from the artefact only, and add no new computation (D1, D7).
3. `gui/charge.py` (Qt-free): `ChargeStages`, `charge_image` (D5, D6, D8, D9), `ConservationView`
   (D10) and `ProtonationView` (D11). `ImageModel` gains a palette choice (D8). NumPy is imported
   inside functions only (`CLAUDE.md`).
4. `gui/case_model.py`: the bounded-number kind and **Add section** (D12, D13).
5. `gui/render.py`: the charge request (D7, D8).
6. `gui/widgets/charge.py`, `widgets/case_editor.py`, and `app.py`'s seventh tab (D2, D3).
7. `gui/probe.py`, `core/paths.py` (`structure_file`), `data/structures/2wcd-a-18-26.pdb`,
   `packaging/nanopnp-probe.spec` and `packaging/LICENSES-BUNDLE.md` (D14, D15). Measure what each
   payload adds to the bundle. `.knowledge/07` §5 gains what is learned, marked **[tested]**.
8. `docs/guide/desktop.md`: the Charge tab, and "seven panels". `CHANGELOG.md` under
   `v0.4.0-alpha.6`. The specification rows listed under [Pointers](#pointers).

### Verification

**VER-60**, *Charge pipeline surfaced in the desktop shell*, is proposed here and written into §7.2
with the code. Tests are named `test_ver60_*`.

| Test file | Tier | Asserts |
|---|---|---|
| `tier1/test_artefact_hook.py` (extend) | 1 | On a cheap charged case, the hook fires for `protonation` and then `charge`, after their store entries exist. A re-run reports both `cached=True`. Watched and unwatched walks give one run record and one set of store entries. The cheap case is the synthetic tube of WP24's Tier-1 test, through `inputs.profile`, with an `inputs.pqr` of two opposite charges inside the body |
| `tier1/test_gui_solver_process.py` (extend) | 1 | A spawned `upto="charge"` walk of that case emits `Produced` for `region`, `mesh`, `protonation` and `charge`, in that order, then `Finished`. Cancelled, it writes no artefact (D2) |
| `tier1/test_gui_charge.py` | 1 | Seven checks: <ul><li>**Orientation and sign.** The positive atom's pixel holds the image's maximum and the negative atom's its minimum, each in the pixel whose centre is nearest its model-frame (r, z). The top row is the largest z, and r increases to the right.</li><li>**The integral.** `Σ σ̄_p A_p` equals the record's `q_grid_e`, in coulombs, to 10⁻¹² relative, at `k` = 1 and at a forced `k` = 7 with a partial last block (D6, Design §1).</li><li>**Colour.** Zero maps to the centre of the diverging table, and `L` is the largest magnitude drawn.</li><li>**Worst plane.** The marker row contains the recorded z (D9).</li><li>**Conservation view.** Every number equals the record's. A record with a doubled tolerance shows the doubled tolerance. A supplied-field record whose producer leg is not run shows *not run* and its reason (D10).</li><li>**Protonation view.** On a two-MODEL `inputs.pqr` whose frames differ, the selector switches the charges and `Q_net` (D11).</li><li>**Shell.** A generated shell's mesh lists `exclusion` among its materials (D17)</li></ul> |
| `tier1/test_gui_charge_protonation.py` | 1 | `GLU 18`–`LEU 26` of chain A through the `protonation` stage at pH 2 and pH 8. The view's `Q_net` is 0 e and −3 e. Each frame's applied charges sum to its `Q_net`. The pKa column equals the artefact's `group_pka`. The rows flagged *unapplied* are the summary's `unapplied`. Needs the `structure` extra, and is skipped visibly without it |
| `tier1/test_gui_render.py` (extend) | 1 | The charge request writes `viewer/charge.*` and never an artefact. `∫ ρ 2πr dA` of the drawn coefficient, at the solve's order, equals the record's `q_mesh_e` to 10⁻¹² relative. With `δ` > 0, the `χ` scene's mean over `protein` equals the record's `material_means` (D7) |
| `tier1/test_case_fields.py` (extend) | 1 | `NEUTRAL_SECTIONS` in both directions. For each listed section, the resolved case and stage 1–10 keys are the same as without it. Every optional section not listed either fails to validate empty or resolves differently. `with_section` refuses a section that is not listed (D13, Design §2) |
| `tier1/test_gui_viewmodels.py` (extend) | 1 | The fresh-process check adds `gui.charge`, and adds `pdb2pqr` and `propka` to the modules that must be absent. Each bounded number's spin range equals its schema bounds, in both directions. The vocabulary check is as in D16 |
| `tier1/test_gui_probe.py` (extend) | 1 | `PAYLOADS` and the probe's imports agree, `pdb2pqr` and `propka` included. The notice has a row for each payload. The unfrozen exercise reports 0 e and −3 e. With PDB2PQR's data lookup stubbed to raise, the exercise fails naming `pdb2pqr`. With the titration arguments removed, it fails naming `propka` |
| `tier1/test_gui_widgets.py` (extend) | 1 | Seven tabs. A loaded pH of 7.25 is shown and not rewritten. **Add section** creates `charge:` and enables the pH. Windows and macOS in CI; locally under the §5 GL shim |
| `tier2/test_charge_2wcd.py` (extend) | 2 | Reuses the module's `deposited` fixture, so no second deposit is made. On 2WCD, the picture's integral is −60 e to 10⁻¹² relative. The protonation view shows −60 e and no chain difference, and its unapplied rows are `CYS 285` in every chain plus the recorded `LYS 8` N-termini. The conservation view equals the record |
| CI `bundle` | — | The frozen `--selftest` exercises every payload, PDB2PQR and PROPKA included, on `windows-latest` (D14, D15) |

```bash
uv run pytest tests/tier1/test_gui_charge.py tests/tier1/test_gui_charge_protonation.py tests/tier1/test_gui_probe.py tests/tier1/test_gui_viewmodels.py -v
uv run pytest tests/tier2/test_charge_2wcd.py -v
.claude/hooks/gate.sh run
```

### Out of scope

| Item | Owner |
|---|---|
| A `χ` export as a `field1` document (WP30's deferral) | No owner. The viewer reads the artefact (D1). Re-read, it would be refused (WP30 D3) |
| Shipping the shell, not the probe, as the bundle's executable | Phase 4 GUI increment, with QR-10 |
| A 3D molecular view, editing a PQR, or overriding a protonation state | Not in §8.1's increment (RSK-15). Structure preparation is a phase exclusion |
| The guide to protonation, smearing and the switches, and example 07 | WP32 |
| The identity of a deposited charge or a derived `χ` in a golden | OPN-07 |
| `with_section` in `nanopnp.PUBLIC` | A later decision in `test_public_api.py` |

### Open questions

None blocking. D15 widens source collection to MDAnalysis and GridDataFormats. That is a licensing
judgement the author may overrule. The narrower fallback is PROPKA alone, which changes no other
decision.

## Design

### 1. The picture keeps the charge

The lattice is indexed `[i_z, i_r]` with spacing `h`. Its trapezoid weight is
`w_n = h² · a_i · a_j`, where `a` is ½ at each end of an axis and 1 elsewhere. The producer leg's
integral is `Q_grid = Σ_n w_n σ_n` (§4.4 NOTE on the producer path's conservation report). Partition
the nodes into blocks `p` of at most `k × k` nodes, and set

```
σ̄_p = Σ_{n∈p} w_n σ_n / A_p,   A_p = Σ_{n∈p} w_n.
```

Then `Σ_p σ̄_p A_p = Σ_n w_n σ_n = Q_grid` exactly, whatever `k` is and however the last block is
cut, so the picture carries the same charge as the record, to round-off. Strided sampling,
`σ̄_p = σ_{n₀(p)}`, has no such property. On a field whose sign changes every 0.035 nm, its blocks
would alias exactly as VAL-15's quadrature did. The pixel is drawn centred on the mean coordinate of
its nodes, and its width is `k h`. At `k = 1` that is WP24's convention, and `A_p` is `h²` away
from the edges. The drawn area of an edge pixel exceeds `A_p`. That is a display convention and
never enters the integral, which uses `A_p`. Units: `σ` is in C m⁻² and `w_n` in m², so the
integral is in C, and is divided by `e` to compare with `q_grid_e`.

### 2. A section that means nothing when empty

`charge:` absent and `charge: {}` both resolve through `Charge()`. `_resolve_protonation` and the
stage-5 and stage-7 readers all write `document.charge or Charge()`. `_check_charge` returns early
on `None`, and otherwise refuses only keys set away from their defaults, so `{}` is refused nowhere
that absence is accepted. The case hash still moves, because it is taken over the document's text,
as it does for any edit. That is why the test asserts that the resolved case and the stage 1–10
keys are equal, and does not assert the case hash. The rule is a set kept in `io/case.py` and
checked in both directions, not a general one. `CaseDocument` has three optional sections:
`structure`, `geometry` and `charge`. `structure:` cannot be empty, because it needs its point
group, so it is out of the set by failing to validate. Whether `geometry: {}` resolves as its
absence is for the test to establish, not for this plan to assume. Deeper down, presence is the
physics: an `analyte:` placed from defaults would put a body in the pore, which is why a
nested block is never added from a default either. A section joins the set only when the test
shows its empty form resolving as its absence.
