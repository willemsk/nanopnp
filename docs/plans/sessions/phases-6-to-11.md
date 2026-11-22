# Phases 6 to 11: the input to each phase's round

**Status: input note, written 22 November 2026 at `/np-plan project` (§8.2.49); each `/np-plan phase <n>` reads its
section, numbers and orders its packages, may regroup them (§8.2.46 AV5) and estimates the phase again.**

Planning, not requirements: `SPECIFICATION.md` governs. §8.1 holds each phase's deliverable, gate and estimate, §2.7
its release, and `docs/project/review-findings.md` each open item's owner. This note only gathers them by phase. A
package below is provisional and named by its scope.

## Phase 6 — the cleanup and the library's foundations (`v0.7`)

In the order the rulings fix; the rest is the round's.

| Package | Its items |
|---|---|
| The Windows leg, first (AY4) | REV-277: name the failing test and the stall, fix them; `/np-ship` stops while a platform leg of the last full run is red |
| The cleanup (REV-272; AY5, AY8) | A baseline with `usage.py`, the `claude-api` skill's `prompt-audit`, a reading limit put to the author, the records before the instructions; the Copilot host retired, with its tag; REV-166 to REV-168, REV-271. On Fable 5.2 whole (AY7) |
| The library's results side | The [architecture survey](../../project/architecture-survey.md)'s steps R1 to R5: a typed run record, one quantity catalogue, fields with their order, the definitions' evaluator, the results file and its facade |
| The shell's numbers into the library | The survey's workbench step 2 (QR-13; VER-60) |
| The library's shape | Steps R6 to R8 and R10: `Project` split, no stage building its upstream stages, one registry shape with switches as data (MOD-08), the dead code |
| The model's open terms (AY6) | Step R9, the force terms shared with the weak form; REV-223, REV-224, REV-257, REV-255's equations, REV-230; the one re-pin of VER-62 |
| The tolerances argued (AY6) | REV-182, REV-225, REV-232 |
| The exports (AY6) | FR-28: REV-41's region export, REV-45 |
| The library's refusals | The error base; FR-35's NOTE; REV-254, REV-242's fourth point |
| The speed-up, last (AY3) | REV-60, REV-156, REV-171; the assembly first (Z6), each cost against a registered threshold (M2) |
| The close | The end-of-phase report; `v0.7.0` |

## Phase 7 — the workbench rebuilt (`v0.8`)

| Package | Its items |
|---|---|
| The workbench's foundations | The survey's workbench steps 1, 3 to 6 and 8 to 11: test probes, a state and link bus per browser client, view hosts with Plotly, one form, the workspace, the views moved suite by suite, the style in the shared parts; REV-275's forms |
| The tree of results | FR-32's tree; WB-54 to WB-63; REV-268, REV-270, REV-273 (its four points at the design round; AX2), REV-275 |
| The structure's layers | WB-49; REV-240's variation view, REV-243, REV-265, REV-274 |
| The performance package | WB-23's 200 ms measure on the author's GPU; REV-258 |
| The polish pass | QR-16's keyboard pass; WB-52; REV-235 to REV-237, REV-241, REV-245, REV-254's suite words, REV-255, REV-261 to REV-263, REV-266, REV-267, REV-269, REV-274, REV-275 |
| The guided route and new models | FR-36; REV-240's safeguards, REV-241's PQR, REV-242's first two points, REV-249; the full guide (AW3) |
| The close | `v0.8.0` |

## Phases 8 to 10 — the tools (`v0.9`, `v0.10`, `v0.11`)

Each is a library capability with its own Tier 1 and Tier 2 tests before the workbench surfaces it (§8.2.17 S3 to S5).
Its round sets its gate and its estimate.

| Phase | Its items |
|---|---|
| 8, the physics composer | FR-40; REV-67; MOD-11 |
| 9, the structural mutator | FR-41, with a dependency vetted at its round; REV-149, REV-238; the structure pipeline's loose ends (AY6): REV-151, REV-180, REV-181, REV-186 |
| 10, the 2D sketcher | FR-42; REV-244 |

FR-43's package (REV-183) keeps "a later phase".

## Phase 11 — validation and release (`v0.12`)

The validation runs (REV-46, REV-61, REV-64); V&V in CI (REV-91); the analyte forces (FR-21, FR-22); Tier 3 against
the published results (VAL-16, VAL-17), with AM2's measurement of the three gaps, E1's carried numbers and E4's
decision on NUM-07; Tier 4 (VAL-07 to VAL-10); the tutorials, the JOSS paper, the DOI archive and PyPI (QR-15).

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| The reading limit, ruled from the baseline; what may leave the rulings' history | Phase 6's cleanup, at its plan | The cleanup proposes and waits; nothing is deleted on a guess |
| The tag on the last commit that holds the Copilot host | Phase 6's cleanup | The session prints the command; the commit's hash is in the cleanup's Outcome |
| A session on a machine with a GPU | Phase 7's performance package | The headless numbers stand and the measure is carried |
| Verdicts at each design round (AJ8) | Phase 7 and each tool phase | The package waits |
| The paper's figure data and the ensemble archive under `NANOPNP_REFERENCE_DATA`, on the nightly runner too (D6; E1) | Phase 11 | The gated legs cannot run and the phase does not close |
| QR-10's observer | v1.0's release candidate (AW2) | No trial; v1.0 waits |
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |

## Open decisions

| Decision | Owner |
|---|---|
| Phase 6's packages, their numbers and order | `/np-plan phase 6` |
| Each tool phase's gate, estimate and dependencies | Its round |
| Whether the library's refusals and REV-270's library part stay where this note puts them | `/np-plan phase 6` |
| v1.0's content and gate (OPN-08) | The author, at Phase 11's close at the latest |
