# WP32 — Documentation increment 3: the charge pipeline and example 07

**Status: planned, not started.** Written 3 October 2026, after WP31 merged on `main` (`35524c1`,
to be tagged `v0.4.0-alpha.6`). Stage 7 produces a charge from a structure, gates it and records it
(WP27, WP28), with the two FR-15 switches beside it (WP30), and the desktop shell shows all of it
(WP31). The only prose on it is the Charge panel of `guide/desktop.md`. `guide/fields.md` and
`guide/case-files.md` still describe the charge pipeline as a future release. WP32 inherits:

- the VER-46 executor (`nanopnp.validation.examples`), with its three tags (WP16 D8, WP25 D10);
- the generated references (VER-45, WP16 D5);
- `--export` for `protonation` (`.pqr`) and `charge` (`.yaml`, `.dx`, `.mrc`, `.ccp4`) (WP27 D16,
  WP28 D11);
- example 06's `prepare.py`, the preparation made without nanopnp (WP25 D4).

This is a work package of the [Phase 3 plan](phase-3-charge-pipeline.md) §WP32, and it discharges
phase criterion 7. `SPECIFICATION.md` governs, and every identifier below is a pointer into it.
Where this plan and the specification disagree, this plan is wrong. **Spec amendments, made in this
commit:**

- **VER-46** gains the charge pipeline's oracles (D7);
- **VER-60** gains the rule for an integer or optional bounded number (D12);
- Appendix A maps FR-12 to FR-15 to VER-46.

## Execution brief

### Scope

Four deliverables, in this order.

1. **One executor seam.** `copy_example` mirrors a sibling example that a command names by `../`,
   so example 07 runs example 06's `prepare.py` instead of copying it (D5).
2. **Example `07-pdb-to-charged-run`**, which runs from the vendored 2WCD entry to a charged
   ePNP-NS solve, exports the PQR and the charge, feeds the PQR back, and turns both FR-15 switches
   on. Its refused block re-supplies the exported charge as a field, which stage 7's
   quadrature-agreement gate refuses. VER-46 executes it at Tier 2.
3. **One guide page, `guide/charge.md`**, with the edits that link it in. Four existing pages
   still say the charge pipeline is a future release, and those edits fix them.
4. **Two WP31 carry-overs** in the desktop shell (D12, D13).

Discharges QR-15 in part (Phase 3's documentation increment) and phase criterion 7. Touches IF-02,
IF-05, FR-12 to FR-15, FR-20, FR-23, FR-25, FR-27, IF-09 and QR-12. **The brief is about 2,000
words, over its 1,200 target.** The example's mesh size, its oracles, its refusal and the executor
seam each change what a verified contract means, so each needs its own decision.

### Requirement and section pointers

| Need | Read |
|---|---|
| The increment | `SPECIFICATION.md` §8.1 documentation table (Phase 3 row); §3.3 QR-15 NOTE; phase criterion 7 |
| Stage contracts to document | §5.2 stage 7 and its design note; PHY-16 to PHY-20 and their NOTEs; §4.4 NOTEs on the producer path and the derived solid fraction; §5.2.1 NOTE on the ion-exclusion shell; §5.3.1 NOTEs on `charge.ph`…, `charge.smearing`, the v2 keys that change a number, and `inputs:`; §5.4.3 NOTE |
| Executed examples | VER-46; `validation/examples.py`; `tests/tier1/test_examples_plan.py`; `tests/tier2/test_examples_0*.py`; WP25 D3–D10 and Outcomes |
| The conservation report's keys | `charge/fields.py` `DepositConservation.summary`; `tests/tier2/test_pipeline_2wcd.py` |
| Exports | `cli/export.py`; `charge/protonation.py` `export_pqr`; `charge/stage.py` `export_charge` |
| The carry-overs | `gui/case_model.py` `_kind`; `gui/widgets/case_editor.py` `_build`; `gui/widgets/charge.py`; `gui/app.py` `build_charge`; WP31 D2, D12 |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Guide page | **`guide/charge.md`**, *From a structure to a charge*. It covers stage 7's two halves. **Protonation:** `charge.ph`, `forcefield`, `titration`, one run per frame, chains kept, unapplied states and per-chain differences recorded, `inputs.pqr` and the `.pqr` export. **Deposition:** `charge.smearing`, the export lattice and the element-wise deposit, and why a deposited charge is not interpolated. **The conservation report:** where it is (`inspect`, `stage charge --json`), what each leg and the per-plane check compare, and exit 4. **The two FR-15 switches**, and **which models take a charge**, read from their declarations. Nav: after *From a structure to a mesh*, before *Charge and permittivity fields* | The §8.1 row names protonation, force field, smearing and the conservation report. The phase plan adds the switches and the model interface. One page follows the order the stage runs in |
| D2 | What the guide may state | WP25 D2's rule. It says what each step does and which key steers it. Formulas, thresholds and tolerances are linked in the rendered specification, and a specification constant is quoted only beside its link. **No measured number appears**, `Q_net` of 2WCD included: the example asserts properties, not −60 e | VER-46's last sentence |
| D3 | Edits to existing pages | `fields.md` becomes the supplied-field page. Its intro links `charge.md`, and its conservation section says which checks differ on the deposited path. `case-files.md` rewrites the stale `inputs.pqr` and `charge` rows. `provenance.md`'s charge group adds the protonation record, `Q_net`, the variant and the report, and its deviations add the `charge.*` switches. `concepts.md`, `geometry.md` (the shell at stage 5), `desktop.md` and `guide/index.md` link the page. `project/physics-models.md` gains one line pointing a model author at the deposit | Each is a sentence that is false today, or a missing link |
| D4 | Example 07's commands | `run` block: `python ../06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb` → `nanopnp run 2wcd.case.yaml --store store --run-dir run` → `inspect run` → `stage protonation 2wcd.case.yaml --store store --export 2wcd.pqr` → `stage charge 2wcd.case.yaml --store store --export charge.field.yaml` → `run from-pqr.case.yaml --store store --run-dir run-pqr --upto charge` → `run switches.case.yaml --store store --run-dir run-switches --upto charge` → `inspect run-switches`. Then a `refused` block, run after it: `nanopnp run resupplied.case.yaml --store store --run-dir run-resupplied --upto charge` (D8) | One solve. The substitution, the switches and the refusal stop at stage 7, which is where they differ. Prototyped ([Design §1](#1-the-example-prototyped)) |
| D5 | Preparation | Reused, not copied. `copy_example` resolves every word that starts with `../` against the example directory. When it lands inside the repository, it mirrors that word's parent directory under the copy, filtered by `examples/.gitignore` and `*.msh`, as it does for `../../` today | One preparation script, so the two examples cannot drift apart. The filter keeps a sibling's generated files out of the copy |
| D6 | The cases | `2wcd.case.yaml` is example 06's case with an explicit `charge: {ph: 7.5, forcefield: CHARMM, titration: propka}`, all at their defaults, plus `numerics.mesh.size_scale: 4` and `outputs: [current, transport_numbers]`. `from-pqr` adds `inputs.pqr: {path: 2wcd.pqr, format: pqr}` and drops `charge:`, because the PQR replaces the step its protonation keys configure. `switches` sets `exclusion_offset_nm: 0.25` and `dielectric_transition_nm: 0.15`, which are WP30's 2WCD values. `resupplied` adds `inputs.charge: {path: charge.field.yaml, format: field1}` and drops `charge:`. The continuation ladder stays at its default: without it the solve fails the positivity gate ([Design §1](#1-the-example-prototyped)) | **Close call: `size_scale` 4.** At the default sizes the validated solve had not finished after 27 min on one core ([Design §1](#1-the-example-prototyped)), which would make the example `slow`, recorded and not gated. At 4 it solves in 220 s, and the example fits Tier 2. `size_scale` is a discretisation choice, not a deviation (§5.3.1 NOTE). The README says the mesh is coarse for runtime and that `t₊`'s magnitude is not a prediction, as example 02 does. The explicit `charge:` block shows the keys a user will edit. It is the validated default, so the deviations list stays empty |
| D7 | Example 07's oracles | (a) `run` walks every `PIPELINE` stage, its manifest keys each one, and it lists no deviation. The charge group's `source` is `deposited` and its protonation `source` is `pdb2pqr`. (b) **`Q_net` is the integer the PQR sums to.** The charge column of `2wcd.pqr`, parsed by the test independently of nanopnp, sums to within 10⁻⁶ of an integer, and the manifest's `q_net_e` equals that sum to 10⁻⁶. (c) The conservation report is in the manifest, and its producer and consumer legs and its two worst planes are each below their recorded tolerance. (d) **The negatively charged lumen is cation-selective:** `transport_number` > ½ at 0.15 M and +50 mV, and the FR-23 routes agree within `ROUTE_AGREEMENT_TOLERANCE`. (e) `run-pqr`'s protonation record has `source: inputs.pqr` and `2wcd.pqr` is among its hashed files. Its atom table (positions, charges, radii, names) equals `run`'s exactly, and so does every array of its deposit and its lattice except `seconds`, under a different charge key. (f) `run-switches` lists exactly `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` as deviations, and its mesh carries an `exclusion` material. Its charge passes the same gates, and its region and mesh keys differ from `run`'s. (g) `charge.field.yaml` is a `nanopnp/field/v1` areal charge density whose declared `q_net_e` equals the manifest's. (h) The refused block exits 4, and its stderr names the quadrature-agreement check and the supplied field | Each fails loudly on a specific error. A flipped sign or a lost charge puts `t₊` at or below the uncharged pore's, which is near the infinite-dilution 0.396 ([Design §1](#1-the-example-prototyped)). (b) catches a lost frame or a lost residue. (c) passes by construction, because stage 7 would have exited 4. It is asserted because it is what the guide tells a user to read. (e) shows that the deposit depends only on the atom table, and not on PROPKA's group table, which a PQR does not carry. (h) is VAL-15's aliasing shown to a user. (f) is FR-25 on the new switches. **Rejected:** comparing `t₊` against the published 0.82, which is a different structure on a finer mesh. It is VAL-16's job at v1.0. Also rejected: comparing whole stage-7 artefacts or their bytes. The deposit's payload and summary both record wall-clock seconds (WP31's live item), so two identical deposits never share bytes |
| D8 | The exported field fed back through `inputs.charge` | **A `refused` block.** On the example's mesh, stage 7 refuses the re-supplied lattice with exit 4, at the quadrature-agreement check, before the conservation legs. The README says why: the lattice's structure is below element scale, so sampling it at quadrature points aliases, which is what the deposit avoids. It quotes no number. The guide says the same, and says the export is for other tools and for a finer mesh ([Design §2](#2-the-deposited-charge-fed-back-as-a-supplied-field)) | Run, not assumed (WP25 D12). VAL-15 and the §4.4 NOTE are the reason the deposit exists, and a user who exports the charge will try exactly this |
| D9 | Tier and budget | `tests/tier2/test_examples_07_pdb_to_charged_run.py`, not `slow`, with a per-command timeout of 1,800 s. **Target ≤ 480 s serial from a cold store**, against about 420 s prototyped, of which the solve is 220 s and the cold protonation about 100 s. The measured figure is recorded as an Outcome. Over the target, the remedy is a coarser `size_scale`, never a weaker model, fewer corrections or no ladder | It would be the suite's longest Tier 2 file. Under `--dist loadfile` it runs beside the others, inside the gate's 25-minute budget. The test cannot seed the session's protonated store, because the example's preparation is not the fixture's |
| D10 | Generated references | No edit. VER-45's walk already lists `charge.*` with the `Literal` option sets, and the `--export` suffixes in the CLI reference | WP16 D5. The phase plan's "pick up the new option sets" is already true, and the test proves it |
| D11 | Public surface | Unchanged. Example 07 is CLI only | WP25 D11 |
| D12 | WP31 carry-over: the bounded number | `_kind` returns `bounded` only for a field that admits no `None`. An `int` field with both bounds becomes a `QSpinBox` with step 1, and a `float` field a `QDoubleSpinBox` with `SPIN_DECIMALS`. A field that admits `None`, bounded or not, stays a numeric entry, where an empty line is `None` | The WP31 review finding. A spin box cannot say "unset", and three decimals misrepresent an integer. Today `charge.ph` is the only field with both bounds, so nothing a user sees changes. The rule is what a later bounded field would meet |
| D13 | WP31 carry-over: `ChargeWidget.build` | **Deleted.** The window builds the charge through the Geometry tab and calls `follow`, and nothing calls `build` | Dead code that duplicates `MainWindow.build_charge`'s walk is a second path that is never tested. `ChargeWidget` is not in `nanopnp.PUBLIC`, and its interface is the shell's own |
| D14 | Housekeeping | `examples/.gitignore` gains `2wcd.pqr`, `charge.field.yaml` and `charge.field.npz`, the names the prototype wrote. `docs/examples/index.md` says seven examples. `mkdocs.yml` gains the guide page and example 07. `CHANGELOG.md` gains `0.4.0-alpha.7`, and the README's v0.4 row loses "planned" | A pattern such as `*.yaml` would hide case files |

### Work items

1. **`validation/examples.py`** (D5): the `../` mirroring. Extend `tests/tier1/test_examples_plan.py`
   to seven examples, and give the mirroring a scratch example that names a sibling.
2. **`examples/07-pdb-to-charged-run/`** (D4, D6): `README.md`, `2wcd.case.yaml`,
   `from-pqr.case.yaml`, `switches.case.yaml` and `resupplied.case.yaml`. Read [Design §1](#1-the-example-prototyped) first.
3. **`tests/tier2/test_examples_07_pdb_to_charged_run.py`** (D7, D9).
4. **The guide** (D1–D3, D8): `docs/guide/charge.md` and the edits of D3. Then `mkdocs.yml`,
   `docs/examples/index.md`, `examples/.gitignore`, `CHANGELOG.md` and the README (D14).
5. **The shell** (D12, D13): `gui/case_model.py`, `gui/widgets/case_editor.py` and
   `gui/widgets/charge.py`, with their tests.
6. **Records**: VER-46, VER-60 and Appendix A as amended here, the phase plan's WP32 entry,
   `current.md`, and the Outcomes here.

### Verification

| Test | Tier | Identifiers | Assertion / oracle | Tolerance |
|---|---|---|---|---|
| `tests/tier1/test_examples_plan.py` | 1 | VER-46 | Seven examples. Tags ⊂ {run, plan, refused}. A scratch example whose command names `../sibling/script.py` gets that sibling mirrored without its gitignored files, and `../../` still mirrors a repository directory | exact |
| `tests/tier2/test_examples_07_pdb_to_charged_run.py` | 2 | VER-46, FR-12–FR-15, FR-23, FR-25, FR-27, IF-05, QR-12, VAL-15 | D7 (a)–(h). The run block first, then the refused block. Block durations and stage times are logged | (b) 10⁻⁶ e; (c) each check's own recorded tolerance; (d) `ROUTE_AGREEMENT_TOLERANCE`; the rest exact |
| `tests/tier1/test_gui_viewmodels.py` (extend) | 1 | VER-60, VER-43 | `_kind` on synthetic references: `float` [0, 14] gives `bounded`, `int` [1, 9] gives `bounded` with integral steps, `float | None` [0, 14] gives `number`. The walk of the real schema still matches every bounded field's spin range to its bounds in both directions | exact |
| `tests/tier1/test_gui_widgets.py` (extend; run serially in CI) | 1 | VER-60 | An `int` bounded state builds a `QSpinBox` and a `float` one builds a `QDoubleSpinBox`. `ChargeWidget` has no `build` attribute, and *Build charge* still runs through `MainWindow.build_charge` | exact |
| `test_doc_reference.py`, `test_public_api.py` | 1 | VER-45 | Unchanged and green | — |
| CI `docs` job | — | VER-45 | `mkdocs build --strict`, with every new anchor resolving | — |

Commands: the full gate (`.claude/hooks/gate.sh run`);
`OMP_NUM_THREADS=1 uv run pytest tests/tier2/test_examples_07_pdb_to_charged_run.py -v --durations=0 --log-cli-level=INFO`;
`uv run pytest tests/tier1/test_gui_widgets.py -v`;
`uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`.

### Out of scope

| Item | Owner |
|---|---|
| Example 07 at the default mesh sizes, or on the 50-frame ensemble | Not owned. The ensemble lives under `$NANOPNP_REFERENCE_DATA`, which a test may not assume. A default-size run would be `slow` and recorded, and adds no oracle |
| `t₊` against the published table | VAL-16, v1.0 (§8.2.4 D6) |
| The Phase 3 end-of-phase report and the `v0.4.0` tag | The phase close, after WP32 merges, as Phase 2's was |
| The identity of a deposited charge in a golden | OPN-07 |
| An option set for `inputs.<name>.format` in the generated reference | Not specified. The format is checked when the case loads |
| The webgui colour range not yet watched drawing (WP31's live item) | No owner. Not a documentation claim |

### Open questions

None blocking. D6's `size_scale` 4 is the close call, and it is flagged to the author in the
hand-off.

## Design

### 1. The example, prototyped

Run by hand on 3 October 2026, at `35524c1`, with `--all-extras`, one core, and
`OMP_NUM_THREADS=1` **[tested]**. The directory was a copy of example 06.

- `prepare.py` takes 14.6 s, cold, including `uv run`'s start-up.
- A structure case with no `--upto`, at the default sizes, under the validated model, walks stages 1 to
  6, protonates (one frame, 54,084 atoms with hydrogens, 12 chains, `Q_net` −60 e, no per-chain
  difference) and deposits within 2 min 50 s of a cold start. The `epnp-ns` solve with the default
  ladder had not finished 27 min later, at 1.9 GB RSS, and was stopped.
- A structure case may carry `inputs.pqr`: the loader accepts it, because the structure is still
  upstream of the geometry chain.
- At `size_scale` 4, with stages 1–5 and the protonation cached: 6,223 elements, mesh 1.4 s, stage 7
  4.7 s, solve 220 s on the default ladder, QoI 2.1 s; 3 min 50 s for the command. `Q_net` is −60 e
  to 10⁻¹⁴. The producer and consumer legs are 1.6 × 10⁻¹⁴ and 1.5 × 10⁻¹⁴, and the worst planes
  are 1.1 × 10⁻¹³ on the lattice and 2.6 × 10⁻⁴ on the mesh, all against 10⁻³. **`t₊` = 0.543**,
  and the FR-23 routes agree to 2.6 × 10⁻⁴. The deviations list is empty.
- The same case with `continuation: none` fails the positivity gate after 2 min 20 s
  (Cl⁻ = −0.197 at r = 2.11 nm, z = 0.37 nm) and exits 4. The ladder stays.
- The PQR export takes 2 s and holds 54,084 atoms. Its charge column sums to −60.0000000000. The
  charge export takes 1 s and writes `charge.field.yaml` with `charge.field.npz` beside it.
- `inputs.pqr` beside `structure:` walks to `charge` in 11 s. The protonation stage still runs,
  reading the file (`source: inputs.pqr`). Its atom table equals the PDB2PQR run's exactly, and it
  lacks only PROPKA's 1,092 titratable groups. Every array of the deposit is equal except `seconds`
  and the NaN `uncovered_at_nm`.
- Both switches on walk to `charge` in 12 s: a 14,252-element mesh with an `exclusion` material,
  and three deviations. Those are the two `charge.*` switches and the contributed shell.

**`t₊` margin.** 0.543 clears ½ by 0.043. An uncharged pore is expected near the
infinite-dilution value `D_Na⁰/(D_Na⁰ + D_Cl⁰)` = 1.334/(1.334 + 2.032) = 0.396, from the shipped
parameter file **[verified]**. That pore was not run. A flipped charge lands below it, so either
failure misses ½ by about 0.1 or more. The run is deterministic to solver tolerance, far below the
margin. The magnitude is below the published 0.82 at +50 mV and 0.15 M. That is expected, from a
mesh four times coarser than the validated one with the EDL under-resolved, −60 e against −72 e,
and the deposited 2WCD frame against the MD ensemble. None of it is the example's claim, and
VAL-16 measures it at v1.0. Two levers are rejected as oracle tuning: a lower concentration, which
would widen the margin, and a finer mesh, which the runtime forbids. The example keeps the phase
plan's 0.15 M.

### 2. The deposited charge fed back as a supplied field

The exported lattice, supplied through `inputs.charge` on the same `size_scale` 4 mesh, is refused
with exit 4 by the quadrature-agreement check. Between the assembly order and three orders above
it, the charge integral moves by 0.689 of `Q_net`, against the 10⁻⁴ allowed **[tested]**. The
lattice is at 0.005 nm, and its structure is below the element scale, which is the §4.4 NOTE's
aliasing (VAL-15). The deposit integrates each atom's kernel over the elements and is exact by
construction. The guide therefore says the `.yaml` export is for another tool, or for a mesh fine
enough to resolve it, and that within nanopnp the charge is re-deposited from the PQR.
