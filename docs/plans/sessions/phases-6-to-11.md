# Phases 6 to 12: the input to each phase's round

**Status: input note, written 22 November 2026 at `/np-plan project` (§8.2.49), Phase 6's section planned the same day (§8.2.50), rescoped 23 November 2026 (§8.2.51); each `/np-plan phase <n>` reads its
section, numbers and orders its packages, may regroup them (§8.2.46 AV5) and estimates the phase again.**

Planning, not requirements: `SPECIFICATION.md` governs. §8.1 holds each phase's deliverable, gate and estimate, §2.7
its release, and `docs/project/review-findings.md` each open item's owner. This note only gathers them by phase. A
package below is provisional and named by its scope. The file keeps its first name; Phase 12 is in it since §8.2.51.

## Phase 6 — the cleanup and the library's foundations (`v0.7`)

**Planned, 22 November 2026** ([the plan](../phase-6/phase-6-library-foundations.md); §8.2.50); WP6.01 to WP6.03 are
delivered. **Rescoped, 23 November 2026** (§8.2.51), and **amended** the same day (§8.2.52): WP6.04 is the ground-up review and
WP6.05 the axis package, both firm; the rest is provisional and named by its scope. The package numbers of §8.2.50 AZ4
from WP6.04 no longer hold; the `/np-plan amend 6` after the round on the review numbers what is left.

| Package | Its items |
|---|---|
| The ground-up review, next, WP6.04 (BA10 to BA13; BB2 to BB5; [its plan](../phase-6/wp6.04-the-ground-up-review.md)) | Given what the program is now, how would it be built if it were started over? Its design covers the whole of §3, what is built and what is planned up to v0.13 (BB2). Open: the code's structure, every technology, the constraints of §3.4, the decisions of §5.6, the numerical methods of §6, the requirements and exclusions of §3, the process of §8.4 and every ruling behind them. Given: the physics of §4 alone. A report and no code: the design it would choose, each difference from the program marked keep, change now, change later, drop or add, each change with its gain, risk and cost. Then a ruling round at `/np-plan project` |
| The channel axis's fault, firm, WP6.05 (BA8; BB1) | REV-279: a plane's centre made robust to a broken tie at a ragged rim; 2WCD's axis measured again (VER-48). After the author's ruling round on the review and the amendment that follows it (BB1) |

Provisional until the author has ruled on the review's proposals (BA4, BA11), about ten packages, in this order as
the round's input:

| Package | Its items |
|---|---|
| The error base (AZ3) | One base for every library error, carrying its case path and file; REV-242's fourth point |
| The run record and the quantity catalogue | The [architecture survey](../../project/architecture-survey.md)'s steps R1 and R2 (AZ5) |
| The fields | Step R3: fields with their order, read by the cell's own basis, written by the library (REV-270; AZ2). It moves the values read between nodes, so it stays a package of its own |
| The definitions and the results file | Steps R4 and R5: the definitions' evaluator on arrays, the results file and its facade |
| The shell's numbers into the library | The survey's workbench step 2 (QR-13; VER-60) |
| The library's shape | Steps R6 to R8 and R10: `Project` split, no stage building its upstream stages, one registry shape with switches as data (MOD-08), the dead code |
| The model's open terms (AY6) | Step R9, the force terms shared with the weak form; REV-223, REV-224, REV-257, REV-255's equations, REV-230; the one re-pin of VER-62. A package of its own |
| The tolerances argued and the exports (AY6) | REV-182, REV-225, REV-232; FR-28: REV-41's region export, REV-45 |
| The refusals reworded (AZ3) | FR-35's NOTE; REV-254 |
| The speed-up, last (AY3) | REV-60, REV-156, REV-171; the assembly first (Z6), each cost against a registered threshold (M2; AZ6) |
| The close | The end-of-phase report; `v0.7.0` |

## Phase 7 — the workbench rebuilt (`v0.8`)

Confirmed in full (BA2).

| Package | Its items |
|---|---|
| The workbench's foundations | The survey's workbench steps 1, 3 to 6 and 8 to 11: test probes, a state and link bus per browser client, view hosts with Plotly, one form, the workspace, the views moved suite by suite, the style in the shared parts; REV-275's forms |
| The tree of results | FR-32's tree; WB-54 to WB-63; REV-268, REV-270's explorer rework (its read by the cell's own basis is Phase 6's; §8.2.50 AZ2), REV-273 (its four points at the design round; AX2), REV-275 |
| The structure's layers | WB-49; REV-240's variation view, REV-243, REV-265, REV-274 |
| The performance package | WB-23's 200 ms measure on the author's GPU; REV-258 |
| The polish pass | QR-16's keyboard pass; WB-52; REV-235 to REV-237, REV-241, REV-245, REV-254's suite words, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269, REV-274, REV-275 |
| The guided route and new models | FR-36; REV-240's safeguards, REV-241's PQR, REV-242's first two points, REV-249; the full guide (AW3) |
| The close | `v0.8.0` |

## Phases 8 to 10 — the tools (`v0.9`, `v0.10`, `v0.11`)

All three before validation, confirmed (BA1). Each is a library capability with its own Tier 1 and Tier 2 tests before
the workbench surfaces it (§8.2.17 S3 to S5). Its round sets its gate and its estimate.

| Phase | Its items |
|---|---|
| 8, the physics composer | FR-40; REV-67; MOD-11; §5.4.1's backend interface and the size of `physics/models.py`, decided at its round (MOD-10, MOD-13; §8.2.50 AZ1) |
| 9, the structural mutator | FR-41, with a dependency vetted at its round; REV-149, REV-238; the structure pipeline's loose ends (AY6): REV-151, REV-180, REV-181, REV-186; fractional protonation, FR-43, from the author's customised PDB2PQR, its physics written into §4 first (REV-183; BA9) |
| 10, the 2D sketcher | FR-42; REV-244 |

## Phase 11 — the analyte forces (`v0.12`)

A phase of its own (BA5): the rigid body of revolution on the pore's axis (FR-21) and `F^em`, `F^hd` and `ΔU` over a
series of positions (FR-22), a library capability first, with VER-19 to VER-22 and VAL-11. Its round sets its gate and
its estimate, decides whether the workbench surfaces it, and asks for the PlyAB model files (OPN-03), without which
VAL-12 to VAL-14 stay unmet. RSK-04 is its risk.

## Phase 12 — validation and release (`v0.13`)

The validation runs (REV-46, REV-61, REV-64); V&V in CI (REV-91); Tier 3 against the published results (VAL-16,
VAL-17), with AM2's measurement of the three gaps, E1's carried numbers and E4's decision on NUM-07; Tier 4 (VAL-07 to
VAL-10); the tutorials, the JOSS paper, the DOI archive and PyPI (QR-15). It builds no new physics (BA5), and it holds
the first comparison with the published results (BA3). Its close defines v1.0 (OPN-08; BA6).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Rulings on the ground-up review's proposals | Phase 6, after WP6.04 | The rest of Phase 6 stays provisional |
| A session on a machine with a GPU | Phase 7's performance package | The headless numbers stand and the measure is carried |
| Verdicts at each design round (AJ8) | Phase 7 and each tool phase | The package waits |
| The customised PDB2PQR (REV-183) | `/np-plan phase 9` | That round moves FR-43's package to after version 1 (BA9) |
| The PlyAB model files (OPN-03) | `/np-plan phase 11` | The forces rest on Tiers 1 and 2; VAL-12 to VAL-14 stay unmet |
| The paper's figure data and the ensemble archive under `NANOPNP_REFERENCE_DATA`, on the nightly runner too (D6; E1) | Phase 12 | The gated legs cannot run and the phase does not close |
| v1.0's content and gate (OPN-08) | Phase 12's close (BA6) | v1.0 waits |
| QR-10's observer | v1.0's release candidate (AW2) | No trial; v1.0 waits |
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |

## Open decisions

| Decision | Owner |
|---|---|
| The ground-up review's proposals, which may reopen any ruling of §8.2.51 | The author, at `/np-plan project` after WP6.04 (BA11, BA13) |
| Phase 6's provisional packages, their numbers and grouping | `/np-plan amend 6`, after that round (BA4, BA11) |
| The numbers WP6.05 to WP6.17 that `holds-now.yaml`, the review register and the Phase 6 plan gave | Settled, §8.2.52: the axis package is WP6.05, and each provisional package is named by its scope until it is numbered (review 079, finding 11) |
| Whether VAL-12 to VAL-14 are Phase 11's, if the PlyAB files arrive (§7.5) | `/np-plan phase 11` (review 079, finding 6) |
| Each tool phase's and the analyte phase's gate, estimate and dependencies | Its round |
| Whether §5.4.1's backend interface and the rest of MOD-13 are decided with the library's shape | Settled, §8.2.50 AZ1: `/np-plan phase 8` |
| v1.0's content and gate (OPN-08) | The author, at Phase 12's close (BA6) |
