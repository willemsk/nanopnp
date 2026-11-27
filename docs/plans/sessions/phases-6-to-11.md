# Phases 6 to 12: the input to each phase's round

**Status: input note, written 22 November 2026 at `/np-plan project` (§8.2.49), Phase 6's section planned the same day (§8.2.50), rescoped 23 November 2026 (§8.2.51), and written again on 24 November 2026 after the rulings on the ground-up review (§8.2.53), Phase 6's packages numbered the same day (§8.2.54), and Phase 6's section amended on 27 November 2026 after the rulings on the kernel's design (§8.2.62); each `/np-plan phase <n>` reads its
section, numbers and orders its packages, may regroup them (§8.2.46 AV5) and estimates the phase again.**

Planning, not requirements: `SPECIFICATION.md` governs. §8.1 holds each phase's deliverable, gate and estimate, §2.7
its release, and `docs/project/review-findings.md` each open item's owner. This note only gathers them by phase. A
package below is provisional and named by its scope. The file keeps its first name; Phase 12 is in it since §8.2.51.

## Phase 6 — the cleanup and the kernel (`v0.7`)

**In flight** ([the plan](../phase-6/phase-6-library-foundations.md)); WP6.01 to WP6.09 are delivered, and the
author has ruled the ground-up review's proposals (§8.2.53) and the kernel's design (§8.2.62). The plan holds what
follows, in this order (BC3; BL9), numbered as the packages are built (§8.2.54 BD1).

| Package | Its items |
|---|---|
| The orchestrator, first, WP6.05 (BC10, BC15; BD2 to BD6) | `/np-carry wp <n>` starts one session that carries a package: the plan, the fixes after its review, each stretch of the implementation and the ship each run in a helper with an empty context. The plan found that the commit gate runs inside a helper, and that a helper can neither start its own nor ask the author, so the main session does both (BD2). The reading limit binds every helper that implements (BD3). The package counts how many of the last 100 pushes that ran tests a safe path rule for the browser tests would have skipped, and applies the rule above a third (BD4). §8.3, §8.4.4, §8.4.5 and §7.6 change with it |
| The channel axis's fault, firm, WP6.06 (BA8; BB1) | REV-279: a plane's centre made robust to a broken tie at a ragged rim; 2WCD's axis measured again (VER-48). It runs under the orchestrator and is measured; the target for the author's touches is set from the first two packages carried, this one and WP6.08 |
| The guard numbers, WP6.08 (BC3; BI1, BI2) | Reference numbers stored for six settings off their default: PHY-23's terms, the log branch, NUM-14's mode, SUPG, and a constant density and no inertia with the flow solved. Its plan checked that none of VER-62's walks takes one; the numbers are held on Linux |
| The kernel's design, WP6.09 (BC2) | A design page and a throwaway prototype: the term, a correction as a shared coefficient, the rule that binds terms (PHY-08), each flux integrated once, the nine names the workbench reads, how an installed package registers. The prototype holds example 01's walk to 10⁻⁸ or the miss goes to the author. It prices the benchmark on a coarse 3D mesh (BC5). The author rules the design; it rewrites ADR-005, §5.4 and §5.5 |
| The kernel, WP6.10 to WP6.12 (BC1, BC4; BL1 to BL3, BL5 to BL7) | FR-40's library half as §5.4.4 states it, the more modular structure before a held number: the composition, with no term naming the backend (MOD-10) and the wind reading every drift (REV-300); switches as data, the log branch a case key (REV-298), and the forces' share of the terms; a model as a list of terms. WP6.12 holds all seven walks of VER-62 and the guard numbers within 10⁻⁸ of their pins before it merges, a walk the kernel moved re-pinned once explained |
| The 3D benchmarks, WP6.13 to WP6.15 (BL4) | VER-13 on a 3D mesh; the pore's 3D mesh, its direct solve measured first against marks registered before any run; VER-17 on a 3D mesh, potential and ions, and the flow in 3D priced by a trial |
| The installed packages, WP6.16 (BC5; BL8, BL9) | A term, a correction, a shape or a solver found in any installed package through one registrar and named in the manifest; a term with no analytic case marked unverified; REV-67; QR-14 and §5.5 |
| The close | The end-of-phase report; `v0.7.0` |

## Phase 7 — the library's foundations (`v0.8`)

The content §8.2.51 BA4 kept, less what the kernel takes, with what §8.2.53 adds (BC7). About fourteen packages, in
this order as the round's input:

| Package | Its items |
|---|---|
| The error base (AZ3) | One base for every library error, carrying its case path and file; REV-242's fourth point; the kernel's refusals with the rest |
| The run record and the quantity catalogue | The [architecture survey](../../project/architecture-survey.md)'s steps R1 and R2 (AZ5) |
| The fields | Step R3: fields with their order, read by the cell's own basis, written by the library (REV-270; AZ2). It moves the values read between nodes, so it stays a package of its own |
| The definitions and the results file | Steps R4 and R5: the definitions' evaluator on arrays, the results file and its facade |
| The shell's numbers into the library | The survey's workbench step 2 (QR-13; VER-60) |
| The library's shape | Steps R6 to R8 and R10: `Project` split, no stage building its upstream stages, one registry shape (MOD-08), the dead code |
| The model's open terms (AY6) | Written as terms of the kernel: REV-223, REV-224, REV-257, REV-255's equations, REV-230; the one re-pin of VER-62. A package of its own |
| The tolerances argued and the exports (AY6) | REV-182, REV-225, REV-232; FR-28: REV-41's region export, REV-45; one field of each kind opened in ParaView (REV-285) |
| The verification ledger (BC9) | FR-45: a page generated from the tests, each term and correction against its analytic case and measured error; a term with no case marked unverified |
| The mesh-error estimate (BC9) | FR-46: a ladder of finer meshes, the observed order and an error bar, on the exact benchmarks and the idealised pore; four meshes or a safety factor; whether Netgen meshes a wall layer at the Debye length (REV-286) |
| Unequal reservoirs (BC21) | FR-48: a bulk concentration for each reservoir and the reversal potential, default off; its physics written into §4 first, the boundary conditions ruled by the author at its plan; an analytic benchmark of Tier 2 |
| Python 3.12 (BC22) | The minimum raised, Pint's pin released, QR-09, §2.5 and §8.4.2 amended, the break listed |
| The refusals reworded (AZ3) | FR-35's NOTE; REV-254 |
| The speed-up, last (AY3; BC24) | REV-60, REV-156, REV-171; the assembly first (Z6), each cost against a registered threshold (M2; AZ6); the direct solve at 10⁶ unknowns with UMFPACK and PARDISO, which sets QR-07's numbers (REV-281; BC12); compiled forms and a threaded assembly (REV-282); the trial of a continuation path that switches the corrections on at the target, with the log branch compared, adopted on a full pass of marks registered first (REV-283) |
| The close (BC8) | The frozen ClyA case of example 05 and a current–voltage sweep set beside the published values, in bands, gating nothing; the end-of-phase report; `v0.8.0` |

## Phase 8 — the workbench rebuilt, with the composer's tool (`v0.9`)

Confirmed in full (BA2), a phase later (BC7), with the composer's tool (BC6).

| Package | Its items |
|---|---|
| The kit's trial, first (BC13) | The workbench's hardest view built in NiceGUI and audited against QR-16, on pass marks the round registers first; whether Plotly pans a field map of 10⁵ cells (REV-284, REV-287). The rebuild starts after the author has seen the result; on a miss the author rules the kit |
| The workbench's foundations | The survey's workbench steps 1, 3 to 6 and 8 to 11: test probes, a state and link bus per browser client, view hosts with Plotly, one form, the workspace, the views moved suite by suite, the style in the shared parts; REV-275's forms |
| The tree of results | FR-32's tree; WB-54 to WB-63; REV-268, REV-270's explorer rework, REV-273 (its four points at the design round; AX2), REV-275 |
| The structure's layers | WB-49; REV-240's variation view, REV-243, REV-265, REV-274 |
| The performance package | WB-23's 200 ms measure on the author's GPU; REV-258 |
| The polish pass | QR-16's keyboard pass; WB-52; REV-235 to REV-237, REV-241, REV-245, REV-254's suite words, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269, REV-274, REV-275 |
| The guided route and new models | FR-36; REV-240's safeguards, REV-241's PQR, REV-242's first two points, REV-249; the full guide (AW3) |
| The composer's tool (BC6) | FR-40's tool over the kernel, in the Physics suite, with room for equations the user writes later (S3); not estimated |
| The close | `v0.9.0` |

## Phases 9 and 10 — the tools (`v0.10`, `v0.11`)

Both before validation, confirmed (BA1). Each is a library capability with its own Tier 1 and Tier 2 tests before
the workbench surfaces it (§8.2.17 S4, S5). Its round sets its gate and its estimate.

| Phase | Its items |
|---|---|
| 9, the structural mutator | FR-41, with a dependency vetted at its round; REV-149, REV-238; the structure pipeline's loose ends (AY6): REV-151, REV-180, REV-181, REV-186; fractional protonation, FR-43, from the author's customised PDB2PQR, its physics written into §4 first (REV-183; BA9); the sensitivity of a quantity to each atomic charge, FR-47, by one adjoint solve, about one package at the shell rate (BC17) |
| 10, the 2D sketcher | FR-42; REV-244. Its round first puts to the author whether registered parametric shapes (a cone, an hourglass, a given surface charge) come before the sketcher, take its place until version 1, or are not added (BC14; GU-11) |

## Phase 11 — the analyte forces (`v0.12`)

A phase of its own (BA5): the rigid body of revolution on the pore's axis (FR-21) and `F^em`, `F^hd` and `ΔU` over a
series of positions, with the ionic current at each beside the open pore's (FR-22; BC18), a library capability first,
with VER-19 to VER-22 and VAL-11. Its round sets its gate and its estimate, decides whether the workbench surfaces it,
and asks for the PlyAB model files (OPN-03), without which VAL-12 to VAL-14 stay unmet. RSK-04 is its risk.

## Phase 12 — validation and release (`v0.13`)

The validation runs (REV-46, REV-61, REV-64); V&V in CI (REV-91); Tier 3 against the published results (VAL-16,
VAL-17), with AM2's measurement of the three gaps, E1's carried numbers and E4's decision on NUM-07; Tier 4 (VAL-07 to
VAL-10); each run classed against the validated range (FR-49; BC19); the tutorials, the JOSS paper, the DOI archive
and PyPI (QR-15). It builds no new physics (BA5). The gated comparison with the published results is its own; one
recorded comparison precedes it at Phase 7's close (BC8). Its close defines v1.0 (OPN-08; BA6), of which one part is
fixed: from v1.0 the case file and the run record are converted (BC20).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| A ruling if the 3D direct solve misses its marks; the ruling on the flow in 3D (BL4) | WP6.15; after WP6.15's trial | WP6.15 waits and WP6.16 is built meanwhile; the flow in 3D is not built |
| The paper's figure data (D6) | Phase 7's close, for the recorded comparison | The table holds the values the paper states in its text, and no curve |
| The boundary conditions of unequal reservoirs | The plan of Phase 7's reservoirs package | The package waits; §4 is not amended on a guess |
| A session on a machine with a GPU | Phase 8's performance package | The headless numbers stand and the measure is carried |
| Verdicts at each design round (AJ8), and on the kit's trial | Phase 8 and each tool phase | The package waits |
| The customised PDB2PQR (REV-183) | `/np-plan phase 9` | That round moves FR-43's package to after version 1 (BA9) |
| The PlyAB model files (OPN-03) | `/np-plan phase 11` | The forces rest on Tiers 1 and 2; VAL-12 to VAL-14 stay unmet |
| A second pore's structure and published conductances, if any (BC19) | `/np-plan phase 12` | Validation stays on ClyA |
| The paper's figure data and the ensemble archive under `NANOPNP_REFERENCE_DATA`, on the nightly runner too (D6; E1) | Phase 12 | The gated legs cannot run and the phase does not close |
| v1.0's content and gate (OPN-08) | Phase 12's close (BA6) | v1.0 waits |
| QR-10's observer | v1.0's release candidate (AW2) | No trial; v1.0 waits |
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |

## Open decisions

| Decision | Owner |
|---|---|
| The kernel's design, its packages and their numbers, and the benchmarks in 3D | Settled by the author, 27 November 2026 (§8.2.62 BL1 to BL9) |
| Whether the flow in 3D is built | The author, after WP6.15's trial, on its price (BL4) |
| Whether the push gate chooses the browser tests by path | WP6.05, by its count (BC15) |
| The target for the author's touches a package | Settled by the author, 27 November 2026: none (BL10) |
| What the reading limit counts once an orchestrator carries a package | Settled by the author, 24 November 2026: every helper that implements (BD3) |
| Phase 7's packages, their numbers and grouping | `/np-plan phase 7` (BA4; BC7) |
| What AM2's "moves one of them" means, and the drift that stops the re-pin | The author, at the plan of Phase 7's equations package, before any measurement |
| A run above order 2; the speed-up's thresholds; the names after `Project` splits | Their packages' plans, in Phase 7 |
| The pass marks of the continuation trial | The plan of Phase 7's speed-up, before any run (BC24) |
| The pass marks of the kit's trial, and the kit on a miss | `/np-plan phase 8`, then the author (BC13) |
| Whether parametric shapes come before the sketcher or in its place | The author, at `/np-plan phase 10` (BC14) |
| Whether VAL-12 to VAL-14 are Phase 11's, if the PlyAB files arrive (§7.5) | `/np-plan phase 11` (review 079, finding 6) |
| Each tool phase's and the analyte phase's gate, estimate and dependencies | Its round |
| v1.0's content and gate, but for the files' conversion (OPN-08; BC20) | The author, at Phase 12's close (BA6) |
