# Phase 3 (Charge pipeline): from a structure to a charged run

**Status: in progress. WP26 delivered, 30 September 2026; WP27 delivered, 1 October 2026 ([plan](wp27-protonation.md)); WP28 delivered, 1 October 2026 ([plan](wp28-charge-deposition.md)); WP29–WP32 planned.** Written 30 September 2026, after Phase 2 (WP17–WP25) delivered
the geometry pipeline (`main` at `v0.3.0-alpha.9`, formerly `v0.9.0-alpha.9`). Phase 2's
end-of-phase report and its release, `v0.3.0`, wait for one Tier-3 run on the author's archive
(criterion 3, VAL-05's ensemble leg). WP26 may start before that report merges, because nothing in
it depends on the Phase 2 verdict, but **v0.4.0 is not tagged before v0.3.0**.

This is the delivery plan for Phase 3 of `SPECIFICATION.md` §8.1, released as **v0.4** (§2.7, as
renumbered by §8.2.4 D1). The specification is normative. Where this file and the specification
disagree, the specification governs and this file is wrong. Requirement identifiers here are
pointers into it, never restatements of it. The author's rulings behind this plan are recorded in
§8.2.4 (D1–D5), and they are not re-argued here.

## Context

Phase 2 answered whether the geometry can be produced from a structure, reproducibly and without
hand-editing. Phase 3 answers the last question the source work leaves: **can the fixed charge and
the dielectric be produced from the same structure, conserved to QR-03's 10⁻³ on the mesh the solver
actually uses, so that one case file runs from a PDB entry to a charged conductance?** That is what
v0.4 means by running "the paper's pipeline end to end" (§2.7). Whether the result
reproduces the published numbers is measured at v1.0 (VAL-16, VAL-17; §8.2.4 D6).

The gate of §8.1 is **VER-01, VER-02 and VAL-06**. The first two are conservation on the deployed
mesh, as a total and per z-slice (FR-14, PHY-19). The third is the Poisson solution against APBS on
the same structure. Two more requirements are assigned to this phase: FR-15, the dielectric field
and the ion-exclusion surface from the same density, and FR-20, the physics-model interface
(§8.2.2 B7). The GUI and documentation tracks each take their third increment (§8.1).

Five things are true of the codebase today and shape every package below.

- **Stage 7 is consumer-only.** `charge/stage.py`'s `FieldStage` reads a supplied `nanopnp/field/v1`
  document through `inputs.charge` or `inputs.eps_r` and gates it (VER-29, VER-30). No code builds
  a charge from atoms. The whole `charge:` block and `inputs.pqr` are refused, in
  `_require_runnable` and `_UNCONSUMED_INPUTS` in `io/case.py`.
- **A `structure:` case solves uncharged today.** `io/run.py` `selected_stages` drops stage 7 when
  no field is supplied, and the manifest records the fields as not run. That is honest, but it is
  not the validated model. After WP28 a `structure:` case walks through the producer by default.
- **The consumer path aliases** (VAL-15, the §4.4 NOTE, `.knowledge/04` §3.2). The delivered ClyA
  table is conserved to 4.7 × 10⁻¹² by its producer, but its integral on our reference mesh is off
  by 9.9 × 10⁻³. That does not converge in h or in quadrature order, because the field's structure is
  below element scale. The §4.4 NOTE names the remedy: deposit onto the finite-element space.
- **The physics-model interface exists, but dispatch around it does not use it.** `physics/models.py`
  has a `PhysicsModel` protocol and a registry. `io/case.py`, `solve/`, `post/`, `mesh/ingest.py` and
  `gui/render.py` branch on `COUPLED_MODELS`, on model names or on `isinstance(..., CoupledModel)`.
  The electrostatic models refuse solid domains and supplied fields (`_check_physics_switches`), and
  that blocks VAL-06, which needs `poisson` on the pore with its fixed charge and dielectric.
- **Everything the producer needs is installed.** `pdb2pqr` 3.7.1 is in the `structure` extra and
  the lock, and it brings `propka` 3.5.1. `symmetry/annular.py` holds the exact annular overlap
  weights, `density/radii.py` the CHARMM radius set, and the closed-form azimuthal Gaussian is
  already VER-50's oracle.

Risks this phase is scheduled to retire. **RSK-08** is charge non-conservation through smearing and
the `1/r` projection, retired by D2's construction and the VER-01 and VER-02 gates on the deployed
mesh. **RSK-15** stays live, because GUI increment 3 surfaces the charge and adds no physics. RSK-13
reopens narrowly, because the bundle gains PDB2PQR's data files.

Deliberately excluded: structure *preparation* (mutations, missing residues, PDBFixer), as in
Phase 2, with OPN-04 staying the author's; ML pKa predictors (PDB2PQR's `--titration-state-method`
accepts `propka` only, `.knowledge/07` §3); charge regulation (post-1.0); the analyte's charge
(FR-21, v1.0); Tier 4 (Phase 4).

## Design decisions

Settled before the first package is planned. Each package's own `/wp-plan` decides the rest in its
decisions table.

| Decision | Choice | Why |
|---|---|---|
| Order of evidence | Every step is verified on a closed form before 2WCD, and on 2WCD before the ensemble, as in Phase 2 | §7.1: an analytic test localises an error to one step |
| The kernel (§8.2.4 D2) | Each atom's normalised 3D Cartesian Gaussian, `w_i = 0.5 R_i`, is averaged over the azimuth **in closed form**, `exp(−((r − r_i)² + (z − z_i)²)/w²) · Ĩ₀(2 r r_i/w²)` with `Ĩ₀(x) = e⁻ˣ I₀(x)`. The Cₙ average is contained in the azimuthal mean. No 3D voxel grid is built | The closed form is the exact limit of PHY-16 steps 4–5 as the grid spacing goes to zero. Run literally at 0.005 nm, those steps cost about 10¹³ voxel updates for the 50-frame ClyA ensemble. PHY-17 is kept: the smearing is 3D, so the kernel does not leak across `r = 0`, and `Ĩ₀` is regular there |
| Where the charge lives (§8.2.4 D2) | Deposited onto a discontinuous, element-wise field on the **deployed mesh**, by r-weighted L² projection. Each atom's element integrals are renormalised to `q_i e` (PHY-18's second option), so the total is conserved by construction. The same sum, sampled as the areal density `2πr ρ` on a 0.005 nm (r, z) grid, is the stage's export (IF-05) and the producer leg's grid | The §4.4 NOTE's remedy. Sampling an interpolant at quadrature points aliases (VAL-15). An element-wise field is a coefficient like any supplied one, so no weak form changes (QR-13). The polynomial order is WP28's, decided against VER-58's closed form |
| What the conservation gates then mean | VER-01's total is exact by construction, so it guards the renormalisation. The discriminating checks are VER-02's per-slice cumulative against the PQR sorted by z, under the §4.4 NOTE's Lipschitz ramp, and VER-58's potential against a closed form. The producer leg is the grid's planar integral against `Q_net` | A gate that passes by construction must be shown to fail on a broken construction: each is fed a deliberately wrong deposition in Tier 1 |
| Protonation (§8.2.4 D4) | PDB2PQR 3.7+ with PROPKA, with the flags of PHY-16 step 3, is run **on every selected frame**, as the reference did, and cached per frame. The chain identifiers are kept, and per-chain differences in protonation state are recorded as a diagnostic, never symmetrised | The archive's 99 PQRs are one per frame. Averaging over frames is then the same operation for charges as for the density |
| The PQR artefact and `inputs.pqr` (§8.2.4 D4) | Protonation is its own registered stage, `protonation`, which emits the per-frame atom table with charges and radii and `Q_net` per frame. `inputs.pqr` substitutes for it with a single-frame PQR or a multi-MODEL PQR, one MODEL per frame, with `format: pqr`. The value set widens and no key is added. How §5.2 numbers the new stage is WP27's decision | FR-27: independently invocable, cached and substitutable. Schema v2 is frozen, and B3 says a later need widens a value set rather than adding a key |
| Radii | The PQR's radius column sets the charge kernel (PHY-16 step 4). The density kernel keeps the CHARMM table of `data/radii/` (WP19). WP27 asserts that the two agree on every heavy atom of 2WCD, and records any difference | PHY-16 names the PQR's `R_i`. The CHARMM table is transcribed from the same `CHARMM.DAT`, so a disagreement is a defect to find, not to average |
| Dielectric and exclusion (§8.2.4 D5) | With both keys at 0, the default, the dielectric is the mesh's material split, which is the validated model. A non-zero `dielectric_transition_nm` builds `χ` from the stage-3 mean. A non-zero `exclusion_offset_nm` makes stage 5 offset the body contour outward and mesh the shell as `exclusion`. Both are deviations, recorded under FR-25 | FR-15 and the PHY-20 NOTEs. The mesh vocabulary and VER-30 already define `exclusion`, so what is new is producing it |
| APBS (§8.2.4 D3) | `apbs-binary` (3.4.1.1; wheels for Linux x86_64 and macOS, none for Windows) goes in a test-only dependency group, never an extra. It is required on the CI legs where its wheel exists and skipped visibly on Windows | A test-only binary is not on the end-user path (CON-07). A skip is not evidence, so the Linux and macOS legs must run it (the WP23 D11 rule) |
| VAL-06's two legs (§8.2.4 D3) | **Gated:** APBS solves Poisson at zero ionic strength on our assembled charge and `χ`, revolved into 3D maps and read with `READ charge` and `READ diel`, so the comparison isolates our axisymmetric FE solve. **Recorded:** APBS from the PQR with its own `spl4` charge and `smol` surface, which measures the azimuthal averaging (CON-04) | Zero ionic strength follows `.knowledge/07` §3, where the `spl2`/`spl4` surfaces are unreliable at finite ionic strength. The tolerance and the treatment of APBS's box boundary are WP29's, argued from the two discretisations |
| The electrostatic models on the pore | `poisson` accepts solid materials, `physics.solid_permittivities`, a fixed charge and `χ`, which it needs for VAL-06. `pb` and `pb-linear` stay as they are. The change is made through the FR-20 interface, as a declared capability rather than a new branch | §5.5 names `poisson` the APBS cross-check target. PHY-24 is untouched |
| FR-20 first | The interface package comes first. Every model declares its field set, material and boundary vocabulary, the inputs it accepts (fixed charge, `χ`, solids) and its solve strategy. The `COUPLED_MODELS` and `isinstance` branches outside `physics/` read those declarations instead | It is cheapest while there are six models and no producer. It also unblocks `poisson` for VAL-06 without a seventh special case |
| The phase gate's input | VER-01, VER-02 and VAL-06 are gated on 2WCD at Tier 2. The ensemble runs the same checks at Tier 3, recorded, together with the end-to-end charged comparison against the reference | Unlike VAL-05, these are properties of the implementation rather than reproductions of the reference, so the public structure is enough to gate them. Reproducing the paper's numbers is Phase 4: at Tier 3 against the published results (VAL-16, VAL-17; §8.2.4 D6) and at Tier 4 against experiment |
| Optional dependencies | PDB2PQR and PROPKA stay in the `structure` extra, imported inside the protonation driver, so that `inputs.pqr` runs without the extra (**amended by WP27 D4**; the stage is reached only through the lazy registry). `scipy.special` supplies `Ĩ₀` (`i0e`) | The `CLAUDE.md` import rule, and VER-25 introspection. The supplied-field path keeps working without the extra |
| Units at the interchange boundary | The (r, z) charge grids stay in nm, as their `field1` header declares (the IF-05 NOTE leaves this decision to Phase 3). No 3D charge map is written | A 2D (r, z) grid overlays no molecular viewer, so B10's argument for ångströms does not apply |

## Conventions established by Phases 1 and 2

Inherited, and not re-decided by any package below.

- **The case document is the unit of reproducibility.** No stage reads YAML, unknown keys are
  refused naming the key, and schema v2 is frozen: a need widens a value set (IF-03; §8.2.2 B3).
- **Every switch is classified** in `SWITCH_PATHS` or `CONFIGURATION_PATHS`, in both directions
  (VER-24). `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` are already switches
  with a validated default of 0.
- **Artefact keys are canonical hashes over validated payloads** (§5.3.2). A generated artefact is
  keyed on its recipe, and its content hash is recorded beside the key. The environment is recorded
  beside a key, never in it.
- **A stage is introspectable without importing its implementation** (VER-25), cancellable, and
  reports progress. A missing extra is a named `MissingExtraError` when the stage is created.
- **Consumers read a generated mesh only through `deployed_mesh`** (WP21 D12). A charge is
  deposited on the mesh the solve uses, never on one regenerated for the purpose.
- **Supply chains are exclusive** (the §5.3.1 NOTE on `inputs:`). Structure → PQR → charge field is
  one chain, and supplying an artefact with one downstream of it on the same chain is refused naming
  both.
- **A documented command is executed verbatim by VER-46**, and a number in the documentation is a
  result only if a test asserts it. An example's tag names its exit.
- **The desktop shell holds no physics.** View-models import no Qt, `ArtefactHook` keys nothing,
  and a new compiled or data-bearing payload is declared in `PAYLOADS` and exercised by `--selftest`.
- **2WCD is prepared through `prepared_2wcd`** in tests, and the ensemble is DCD frames 48–97.

## Work packages

Each package gets its own `/wp-plan <n>` with a decisions table before implementation, and is green
on tiers 1 and 2 before the next starts. The verification identifiers from VER-56 on are
**proposed** here. Each package claims its identifiers and adds its Appendix A rows when it
implements them. Tags are `v0.4.0-alpha.N`.

### WP26 — The physics-model interface (FR-20)

The §5.4.3 interface is made the only route from the rest of the code to a model. A model declares
its field set, its material and boundary vocabulary, which supplied inputs it accepts (fixed charge,
`χ`, solid materials), its QoI set and its default solve strategy. `io/case.py`'s validation,
`mesh/ingest.py`'s required names, `solve/`, `post/` and `gui/render.py` read those declarations in
place of `COUPLED_MODELS`, model names and `isinstance(..., CoupledModel)`. `poisson` declares
solids, a fixed charge and `χ`, which VAL-06 needs. A developer page documents the interface.
Discharges FR-20 and QR-14 (the physics-model half). Adds **VER-56**: a model defined as one class in
the test tree, registered at run time, runs from a case file through solve and QoI with no edit
outside that class. The six shipped models give the same stage-10 keys and the same scalars as
before. No module outside `physics/` names a model, which is asserted by walking the source. A
`poisson` case with solids and a fixed charge solves, and `pb` beside a fixed charge is still refused
(PHY-24).

> **Delivered, 30 September 2026** ([plan](wp26-physics-model-interface.md), to be tagged
> `v0.4.0-alpha.1`). `register_model` pairs each model with a `ModelDeclaration`, and case
> validation, the mesh gate, the solve, stage 11, the export and the GUI read it; `COUPLED_MODELS`
> and every `isinstance` on a model class are gone. `poisson` (`PoissonModel`) runs from a case
> file with solids, `inputs.charge` and `inputs.eps_r`, which WP28 and WP29 build on; `pb` and
> `pb-linear` run on a solid-free mesh with the case's `λ_D`. Discharges FR-20 and QR-14's model
> half; adds VER-56 (`tests/tier1/test_model_interface.py`, `tests/tier2/test_poisson_layers.py`).
> The five older models' stage-10 keys, both ladders' rung models and the coupled scalars are
> unchanged. **Live for later packages:** `poisson` assembles one extra quadrature order for the
> `r` weight and the coupled models do not (NUM-07 NOTE on the `r` weight, open); WP28 produces a
> charge only for a model declaring `fixed_charge`.

### WP27 — Protonation: the PDB2PQR driver and the PQR artefact (FR-12)

The `protonation` stage writes each selected frame of the stage-1 ensemble as a PDB in the stage-1
frame, then runs PDB2PQR through its Python API with PHY-16 step 3's flags at `charge.ph` and
`charge.forcefield`. It emits a per-frame atom table (identity, coordinates, charge, radius) with
`Q_net` per frame and the protonation state of every titratable residue. It is cached per frame,
and the PROPKA warnings about homo-oligomer chains are surfaced rather than swallowed
(`.knowledge/07` §3). `inputs.pqr` is lifted from `_UNCONSUMED_INPUTS` and reads a single- or
multi-MODEL PQR (§8.2.4 D4). `charge.forcefield` becomes an option set, validated against what
PDB2PQR accepts. `charge.titration: none` keeps the force field's standard states. Discharges FR-12,
and adds to IF-03, FR-27 and QR-12. Adds **VER-57**: on small peptides, the charges and `Q_net` are
the force field's own, to 10⁻⁶ e; `Q_net` is an integer to 10⁻⁶ on every frame; `titration: none`
at two pH values gives identical charges, and PROPKA at a pH across a residue's pKa changes that
residue; a multi-MODEL PQR round-trips; a frame count or atom-table mismatch between `inputs.pqr` and
the ensemble is refused naming the frame; the PQR radii agree with the CHARMM table on every heavy
atom of 2WCD (Tier 2); the stage is listed without importing PDB2PQR. **Tier 3, recorded:** DCD
frames 48–97 through our driver against the author's archived PQRs 50–99, as per-residue state
agreement and `Q_net` per frame, against the −72 e of `.knowledge/04` §3.1.

> **Delivered, 1 October 2026** ([plan](wp27-protonation.md), to be tagged `v0.4.0-alpha.2`). The
> `protonation` stage (stage 7, before `charge`) drives PDB2PQR and PROPKA per frame, cached per
> frame, or reads and registers `inputs.pqr`; it records unapplied states from PROPKA's groups and
> exports a PQR that reads back bit for bit. Discharges FR-12; adds to IF-03, FR-27 and QR-12;
> adds VER-57 (`tests/tier1/test_pqr.py`, `test_protonation.py`, `tests/tier2/test_protonation_2wcd.py`,
> `tests/tier3/test_protonation_archive.py`, not yet run). **Live for later packages:** a walk runs
> the stage only when it names it until WP28 reads the artefact (D3); `charge.smearing` is refused
> naming WP28 and the exclusion keys naming WP30; flippable atoms are outside the 0.01 Å
> registration (§5.3.1 NOTE); `protonated_2wcd` costs about 100 s of the push gate.

### WP28 — Fixed-charge deposition on the deployed mesh and its gates (FR-13, FR-14)

Stage 7 becomes a producer. It sums the D2 kernel over atoms and frames, deposits the sum onto the
deployed mesh by per-atom-renormalised L² projection, and writes the 0.005 nm areal grid as the
export and the producer leg. The existing gates (VER-29) apply unchanged to a produced field: the
producer and consumer legs, the quadrature agreement and the per-plane ramped cumulative.
`charge.smearing` keys are consumed, and WP28 decides whether `axis_cutoff_nm` applies on the
producer path or is refused away from its default. `selected_stages` runs protonation and stage 7
for a `structure:` or `inputs.pqr` case. `_PIPELINE_SECTIONS` lifts `charge:`. PHY-16 to PHY-19 as
amended by D2. Discharges FR-13, FR-14 and QR-03 (the producer path), and retires RSK-08. Adds
**VER-01 and VER-02** in full, and **VER-58**: the kernel integrates to `q_i` under `2πr dr dz` to
10⁻¹², is regular on the axis, and matches a brute-force 3D deposition binned by
`symmetry/annular.py` in the limit of fine spacing. The on-axis potential of one smeared atom at
`(r_i, z_i)` in a uniform dielectric is exactly `q erf(ρ/w)/(4πε ρ)`, with
`ρ = √(r_i² + (z − z_i)²)`, which is Tier 2's closed form for deposition and solve together, and the
rate is measured. A deposition missing the renormalisation, or one with a wrong Jacobian, fails
VER-01 or VER-02 respectively. On 2WCD at Tier 2, both legs and every plane pass at 10⁻³, and a
charged walk solves. **Tier 3, recorded:** the archived PQRs deposited and compared with the
delivered `rhoq_pore` table (the planar integral, and the field difference attributed to G4's
`r_i` against `r`).

> **Planned, 1 October 2026** ([plan](wp28-charge-deposition.md)). Two refinements of the text
> above, both amended in the specification in the plan's commit. The consumer leg on a deposited
> field integrates the deployed element-wise field, not the lattice's interpolant, which is what
> removes VAL-15's aliasing, so "the existing gates apply unchanged" holds for their order and
> tolerances but not for what the consumer leg integrates. The per-plane reference is the source
> atoms in closed form, under a Gaussian-smoothed step of 0.5 nm, rather than the lattice under the
> consumer path's 0.2 nm ramp (§4.4 NOTE on the producer path). The deposit is element-wise of the
> potential's order (D3), and `axis_cutoff_nm` is refused away from its default (D10).

> **Delivered, 1 October 2026** ([plan](wp28-charge-deposition.md), to be tagged
> `v0.4.0-alpha.3`). Stage 7 sums PHY-16 step 5's kernel on the 0.005 nm export lattice, cached as
> `nanopnp/charge-grid/v1`. It deposits the sum on the deployed mesh as element-wise `P_k` of the
> potential's order and gates both legs and 12 planes against the atoms. A `structure:` or
> `inputs.pqr` case solves charged. Discharges FR-13, FR-14 and QR-03's producer path; retires
> RSK-08; adds VER-01 and VER-02 in full, and VER-58 (`tests/tier1/test_charge_kernel.py`,
> `test_charge_deposit.py`, `tests/tier2/test_charge_potential.py`, `test_charge_2wcd.py`,
> `tests/tier3/test_charge_archive.py`, not yet run). 2WCD deposits with five orders to spare.
> **Live for later packages:** the coupled models are one quadrature order short on a deposited
> source (D13, open); consumers read the charge only from stage 7's artefact (D9);
> `inputs.mesh: artefact:` is still refused; `seeded_protonated_2wcd` seeds a charged walk's store.

### WP29 — VAL-06: Poisson against APBS (the phase gate)

The `apbs-binary` test group, a driver in `nanopnp.validation` that revolves our assembled charge and
`χ` onto APBS's 3D grid, writes the input deck (zero ionic strength, `chgm spl4`, focusing, and a
boundary treatment WP29 decides), runs APBS, and samples both potentials on a common probe set. The
gated leg compares like with like, per D3. The recorded leg compares APBS's own model of the same PQR
with ours. The tolerance is argued from the two discretisation errors, each measured by refinement,
and is stated before the comparison is run. Discharges VAL-06, and adds to FR-12, FR-13 and FR-15.
Tier 2 on 2WCD and on a synthetic charged ring with a known potential. It is required on Linux and
macOS and skips visibly on Windows. The ensemble leg is at Tier 3, recorded.

### WP30 — The dielectric field and the ion-exclusion shell (FR-15)

A non-zero `charge.dielectric_transition_nm` builds `χ` from the stage-3 mean across the stage-4
isolevel, producing a field the VER-30 blend already consumes. A non-zero `charge.exclusion_offset_nm`
makes stage 5 offset the stage-4 body outward and fragment the shell as material `exclusion`, which
the junction and VER-52 gates admit and stage 6 meshes. The `wall` then moves to the shell's outer
surface, and the distance field follows it (PHY-02). Both are deviations, recorded under FR-25, and
both default to off. Discharges FR-15, and adds to FR-09, FR-10 and PHY-20. Adds **VER-59**: with
both keys at 0, the region, mesh and stage-10 keys are unchanged; a transition width `δ` gives a `χ`
whose 0.5-level lies on the contour and whose width is `δ` to a stated tolerance; the shell's inner
and outer surfaces are `exclusion_offset_nm` apart, measured on the mesh; VER-31's Stern benchmark is
reproduced through a generated shell; a shell that would close the constriction is refused naming
the z where it does.

### WP31 — GUI increment 3: the charge pipeline surfaced

The §8.1 increment: a pH selector and a force-field choice, both generated from the schema, a charge
map viewer (the areal grid and the deployed field), a protonation table per frame, and the
conservation report with its legs and its worst plane. `ArtefactHook` reports the new artefacts. The
bundle carries PDB2PQR and PROPKA with their data files, and `--selftest` protonates a peptide
(RSK-13). No physics enters the shell (RSK-15). Adds **VER-60**, extending VER-43, VER-44 and
VER-55 to the charge views, with the view-models importing no Qt.

### WP32 — Documentation increment 3

The §8.1 increment: a guide to protonation, force fields, smearing, the conservation report,
the dielectric and exclusion switches and the physics-model interface, and example
`07-pdb-to-charged-run`, from the prepared 2WCD to a charged solve, executed verbatim by VER-46. The
oracle is a model property rather than a transcribed number: for example, the conservation report's
legs pass, `Q_net` is the integer the PQR sums to, and the negatively charged lumen is
cation-selective (`t₊ > 0.5`) at 0.15 M. The generated references pick up the new option sets
without a documentation edit (VER-45).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| Versioning | The scheme, and whether the existing tags move | **Settled by the author, 30 September 2026** (§8.2.4 D1): phase = minor, and the existing tags are re-created under their new names through `.github/scripts/renumber-tags.sh` |
| Kernel and deposition | Literal PHY-16, or the closed form deposited on the mesh | **Settled by the author, 30 September 2026** (§8.2.4 D2). PHY-16 to PHY-18 are amended in this plan's commit |
| APBS | How VAL-06 runs | **Settled by the author, 30 September 2026** (§8.2.4 D3): `apbs-binary` in CI, a gated like-for-like leg and a recorded leg |
| Protonation of an ensemble | Per frame or once, and the form of `inputs.pqr` | **Settled by the author, 30 September 2026** (§8.2.4 D4): per frame, with a single- or multi-MODEL PQR |
| Exclusion shell | In Phase 3 or deferred | **Settled by the author, 30 September 2026** (§8.2.4 D5): in Phase 3, as WP30 |
| VAL-06 tolerance | The agreement required of the gated leg | WP29, argued and stated before the first comparison, and put to the author with the argument |
| Stage numbering | Where `protonation` sits in §5.2's numbered table | **Settled by [WP27](wp27-protonation.md) D1**: it shares number 7 with `charge` and runs before it, so stages 8–12 keep their numbers (§5.2 design note) |
| `axis_cutoff_nm` on the producer path | Applied for parity, or refused away from its default | **Settled by [WP28](wp28-charge-deposition.md) D10**: refused away from its default on every path, naming PHY-18 (§5.3.1 NOTE on `charge.smearing`) |
| OPN-04 | Which mutation list produced the ClyA-AS structure | **Author, open.** Needed for the provenance of `Q_net`, not for any gate. WP27 records `structure.source.variant` beside `Q_net` |

## Verification

Every package leaves `uv run pytest` green before the next starts (tiers 1 and 2), and the push gate
is unchanged:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier3 -v                       # the ensemble legs: recorded, skip without the archive
uv run pytest -m slow --log-cli-level=INFO      # protonation and deposition budgets, measured
```

| Package | Tier | Identifiers |
|---|---|---|
| WP26 | 1, 2 | VER-56 |
| WP27 | 1, 2, 3 (recorded) | VER-57 |
| WP28 | 1, 2, 3 (recorded) | VER-01, VER-02, VER-58, VER-29 (on a produced field) |
| WP29 | 2, 3 (recorded) | VAL-06 |
| WP30 | 1, 2 | VER-59, VER-30, VER-31 |
| WP31 | 1 | VER-60 |
| WP32 | 1, 2 | VER-45, VER-46 |

The phase is complete when:

1. **Tiers 1 and 2 pass**, including every earlier phase's gate.
2. **VER-01 and VER-02 pass on the deployed mesh** for 2WCD at Tier 2, with the legs and the worst
   plane in the manifest, and on the ensemble at Tier 3, recorded.
3. **VAL-06's gated leg passes** within the tolerance WP29 states.
4. **A case with `structure:` and no `inputs.mesh` or `inputs.charge` runs from the CLI to a
   charged solve**, and its manifest records every stage's artefact hash, `Q_net` and the
   conservation report.
5. **FR-20 holds:** a model added as one class runs with no other edit (VER-56).
6. **The GUI increment** sets the pH and force field, shows the charge and the conservation report,
   and the bundle self-tests with PDB2PQR in it.
7. **Example 07** runs verbatim from a PDB entry to a charged run.

## End-of-phase report

To be written at the end of the phase, naming numbers rather than adjectives:

- VER-01 and VER-02 on 2WCD and on the ensemble: the producer and consumer legs, the quadrature
  agreement and the worst plane, beside VAL-15's 9.9 × 10⁻³ from the delivered table on the same
  mesh.
- `Q_net`: 2WCD at pH 7.5, and the ensemble per frame (mean and spread), against −72 e. Protonation
  agreement with the author's archived PQRs, per residue.
- Our deposition from the archived PQRs against the delivered `rhoq_pore` table: the planar integral,
  and the field difference with its attribution (G4).
- VAL-06: the gated leg's agreement and tolerance, and the recorded leg's difference, which is the
  size of the azimuthal averaging.
- The end-to-end charged case, one frozen case on the pipeline's mesh and charge against the
  reference mesh and the delivered table: conductance and `t₊`, with the difference split between
  geometry (VAL-05's ε_G) and charge. It is the first measurement of VAL-16's recorded leg, and
  gates nothing before v1.0.
- VER-58's convergence rate, and the element order WP28 chose.
- Wall-clock and peak memory for protonation and deposition, per frame and for the ensemble.
- FR-20: the files a new model touched (the target is one).
- Whether the desktop bundle builds and self-tests with PDB2PQR in it.
