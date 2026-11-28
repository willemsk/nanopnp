# Phase 6 (Cleanup and the kernel): a physics model composed of registered terms, on records a session can read

**Status: in progress. Delivered: WP6.01, WP6.02, WP6.03, WP6.04, WP6.05, WP6.06, WP6.07, WP6.08, WP6.09, WP6.10, WP6.11. Amended 27 November 2026 (§8.2.62): the author ruled the kernel's design; WP6.12 to WP6.16 and the close by scope. This amendment was written by Fable 5.2 at high effort. Release: v0.7 (`v0.7.0`).**

## In brief

**What changes.** You ruled the kernel's design. The model's equations are rebuilt from small registered pieces, and
where a cleaner structure and an old number disagree, the structure wins. Three packages build it; a term names
neither the finite-element library nor two dimensions. Then three packages solve two benchmarks on a 3D mesh, the
charged cylinder and the uncharged pore's conductance, and price the flow in 3D. Last, an installed package adds a
term through one registrar. A case file can ask for the log branch, and the optional stabilisation steers by every
drift.

**Cost.** About 24 sessions, 20 to 37 agent hours and 38 times you act, for the seven packages and the close; the
three packages carried so far took one session each. The 3D pore's machine time is not measured yet.

**What could go wrong.** A lost term could hide behind a re-pinned number, so a package that moves one shows that the
old value returns when its one change is undone, and lists old and new in the pull request you merge. The 3D pore's
solve may not fit a machine: it is measured first against marks set beforehand, and a miss comes to you. The layer
that hides the library is tested in 3D, not against a second library.

**Your call.** Do you approve this amendment, by merging its pull request? Yours later: the 3D solve if it misses its
marks, and whether the flow in 3D is built, on its price. *Recommendation:* approve; it records your ten rulings and
departs from none.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, and the rulings are §8.2.49 to §8.2.63 (AY to BM). The
text each amendment replaced is in [the record](phase-6-record.md). This file keeps its first name: the library's
foundations are Phase 7 (BC7), in [the input note](../sessions/phases-6-to-11.md).

Phase 6 answers one question: **can the physics be rebuilt from registered terms, in the most modular structure,
before the library's foundations and the workbench are built on it?** Its gate is §8.1's.
§5.4.4 states [the kernel's design](../../design/kernel.md) as ruled.

True of the codebase today:

- **A model is assembled in one class.** `physics/models.py` `CoupledModel.residual_form` assembles the weak forms,
  and `physics/terms.py` holds a `Term` for each, for display alone (GU-01).
- **A switch is code, and the log branch has no case key.** `physics/models.py` `SWITCHES` is a closed tuple that
  `io/defaults.py` `SWITCH_PATHS` repeats; only `models.create(..., log_variables=True)` reaches NUM-02's branch
  (REV-298).
- **A drift and a force are written three times.** The ionic force is in `physics/flow.py`
  `electrical_body_force`, `CoupledModel._flow_state` and `post/forces.py` `_integrands`;
  `physics/stabilisation.py` `advective_velocity` writes the drifts again and leaves out PHY-23's decrement
  (REV-300).
- **Two dimensions are written into the forms.** `ngs.Id(2)` in `stabilisation.py` and `post/forces.py`, the axis
  as `ngs.y` in `post/indicator.py`; `mesh/adapter.py` `from_ngsolve` refuses a 3D mesh, and
  `numerics/measures.py` `Measures.volume` has no rule for tetrahedra and falls back without a word.
- **Nothing finds a registration in an installed package** (REV-67); `core/public.py` `PUBLIC` holds
  `register_model` and `registered_models` alone.
- **Thirteen walks are stored** (VER-62's seven, VER-80's six). None takes PHY-23's switch with a stabilised mode,
  and none holds a cell Péclet number.

Risks: none is retired; WP6.14's measure is a first datum for RSK-17.

Excluded: the library's foundations, Phase 7 (BC7); the workbench's rebuild and the composer's tool, Phase 8 (BC6);
a case file in 3D, and the flow, the forces and the corrections solved in 3D (N4; BL4 prices the flow); a comparison
with the published results (BC8).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Order | The kernel, the 3D benchmarks, the installed packages, the close | 3D exercises the interface before it is public (BD1; BL9) |
| The kernel | Five registered pieces, the more modular structure before a held number, in three packages | The fourth package held no code (BL1, BL3) |
| A moved number | Re-pinned in its package once explained, in WP6.10 to WP6.12 alone | Undoing the one change tells a cleaner integral from a lost term (BL2) |
| The backend | No term names it | The more general line, and 3D tests its geometry (BL6) |
| 3D | Two benchmarks, and the flow priced | CON-01 becomes a test that can fail (BL4) |
| The carry | By the orchestrator, with no touches target | Each package reports its count (BC10; BL10) |

## Conventions established by earlier phases

- **A VER-62 miss is reverted, or re-pinned by ruling** (G10), which for the kernel's packages is taken in advance
  (BL2); **a moved edge edits `modularity-layering.yaml`** (VER-61).
- **A deviation from the validated model is a switch, default off** (`.claude/rules/physics-numerics.md`).
- **The schema and `nanopnp.PUBLIC` may change until v1.0**, each break in `CHANGELOG.md` (F4).
- **A cost is fixed after it is measured** (M2). **An open item is a `REV-nn` row** (H12).

## Work packages

WP6.10 to WP6.16 take `v0.7.0-alpha.10` to `v0.7.0-alpha.16`; the close takes `v0.7.0` alone (§8.4.1; BD1). A
package's plan claims its proposed clause, numbered on from VER-80.

### WP6.01 to WP6.11 — delivered

| Package | Live |
|---|---|
| [WP6.01](wp6.01-the-windows-leg.md), the Windows leg (REV-277; AY4), 22 November 2026 | AZ8's ship rule |
| [WP6.02](wp6.02-the-cleanup-measure-audit-records.md), the cleanup's measure and records (AZ9 to AZ17), 22 November 2026 | The reading limit binds a session's first window (AZ15) |
| [WP6.03](wp6.03-the-cleanup-instructions-copilot-host.md), the instructions (AZ18 to AZ21), 23 November 2026 | The limit is 8,000 words |
| [WP6.04](wp6.04-the-ground-up-review.md), the ground-up review (BA10 to BA13), 24 November 2026 | Its proposals are ruled or carried (§8.2.53) |
| [WP6.05](wp6.05-the-orchestrator.md), the orchestrator (BC10, BC15; BD2 to BD6), 24 November 2026 | `/np-carry wp <n>` carries a package; the limit binds every helper that implements (BD3) |
| [WP6.06](wp6.06-the-channel-axis-at-a-ragged-rim.md), the channel's axis at a ragged rim (REV-279; VER-48; BA8; BB1), 25 November 2026 | The axis may differ by about 1° from v0.6's; a change that moves it bumps `channel_axis_revision` (BE2) |
| [WP6.07](wp6.07-the-lean-carry.md), the lean carry (BF1 to BF11), 26 November 2026 | A helper commits and the main session lands (BF11) |
| [WP6.08](wp6.08-the-guard-numbers.md), the guard numbers (BC3; BI1, BI2; VER-80), 26 November 2026 | Six guard walks held at 10⁻⁸, nightly, in the reference environment alone |
| [WP6.09](wp6.09-the-kernels-design.md), the kernel's design (BC2, BC5; BJ1 to BJ3), 26 November 2026 | The prototype's branch, `prototype/wp6.09-kernel` at `1b5f5e3`, stays until WP6.12 merges (BJ3) |
| [WP6.10](wp6.10-the-composition.md), the composition (FR-40; §5.4.4; BL1, BL5, BL6; REV-300; VER-81), 27 November 2026 | No term names the backend, its module on `term_modules:` (VER-65); `CoupledModel.terms_in_force()` decides from the switch records since WP6.11; PHY-23 under a stabilised mode assembles fifty times slower (REV-302) |
| [WP6.11](wp6.11-switches-as-data-and-the-forces.md), switches as data and the forces (FR-40; FR-25; NUM-02; BL7; BM1 to BM3; REV-298; VER-82), 28 November 2026 | Readers take `io/switches.py`'s records; `numerics.log_variables` is a deviation the ladder refuses (BM2); `CoupledModel` holds the three coupled models until WP6.12 |

### WP6.12 — A model as a list of terms, and the full check (BC1, BC4; BL2, BL3; MOD-10)

*Planned by scope.* `pnp`, `pnp-ns` and `epnp-ns` as registered lists; `poisson`, `pb` and `pb-linear` composed;
the declaration's terms derived; `physics/models.py` split, the shell following a moved name. It is the kernel's last package: criterion 3's check runs before it merges, and MOD-10 closes. About 3
sessions, 3 to 5 agent hours and 5 touches.

### WP6.13 — VER-13 on a 3D mesh (CON-01; BL4)

*Planned by scope.* A planar 3D symmetry in `Measures`, with rules for tetrahedra, and the axisymmetric measure
refused on a 3D mesh. The benchmark meshes its cylinder in its own fixture and checks criterion 13.
Proposed VER-83, Tier 2: Debye–Hückel in a cylinder on a 3D mesh. About 3 sessions, 2 to 4 agent hours and 5 touches.

### WP6.14 — The pore's 3D mesh, its solve measured first (BL4; REV-301)

*Planned by scope.* First, a bounded measure of the direct solve of VER-17's three fields at the coarsest size,
260,406 unknowns: its peak memory and its time, against marks the plan registers before any run. A miss goes to the
author. Then a 3D path in the mesher for an idealised pore, with its quality gates, reached by a benchmark alone;
REV-301's three citations with it. About 3 sessions, 3 to 5 agent hours and 5 touches.

### WP6.15 — VER-17 on a 3D mesh, and the flow in 3D priced (BL4)

*Planned by scope.* The indicator current along a 3D axis, and VER-17's conductance on WP6.14's mesh with the
potential and the ions (criterion 14). Then a bounded trial prices the flow in 3D on a branch that is never merged,
as BJ3 has it. Proposed VER-84, Tier 2: the access conductance on a 3D mesh. About 3 sessions, 3 to 6 agent hours and 5
touches.

### WP6.16 — The installed packages (BC5; BL8; REV-67; QR-14)

*Planned by scope.* §5.5's NOTE built: one registrar, a failed extension refused, each registration named in the
manifest, a term with no analytic case marked unverified. `register_model` and `registered_models` leave
`nanopnp.PUBLIC` (F4); QR-14 is amended, and the reference of registered terms written. Proposed VER-85, Tier 2: a term
from an installed package. About 3 sessions, 2 to 3 agent hours and 4 touches.

### The close

The end-of-phase report, the three platforms' full run and `v0.7.0`; `/np-ship phase 6` ships it. About 3 sessions,
2 to 3 agent hours and 4 touches.

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 to 14, 17, 18 | The cleanup, the review, the numbering, the guard numbers, the main session's model | **Settled**, 22 to 26 November 2026; the record holds the rows. 6 and 7 moved to Phase 7 (BC7) |
| 15, 16 | The touches target; the kernel's design, its packages, the 3D benchmark | **Settled by the author, 27 November 2026**: no target (BL10); BL1 to BL9 |
| 19 | The slots' cut, each slot's rule, and the names of the context's operators | **Settled**, WP6.10's plan (D2, D3) |
| 20 | The path of the log branch's case key; where the records live for `io/` (VER-61) | **Settled**, WP6.11's plan: `numerics.log_variables` (BM1); `io/switches.py` (D1) |
| 21 | The floor of VER-13's observed order on a 3D mesh, and its three sizes | WP6.13's plan, argued before any run |
| 22 | The marks of the 3D direct solve, on CI's runners: peak memory and time; the benchmark's marker | WP6.14's plan, before any run; a miss is the author's |
| 23 | Whether the flow in 3D is built | **Author**, after WP6.15's trial, on its price |
| 24 | Whether a script may take the registrar | WP6.16's plan |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |
| A ruling, if WP6.14's measure misses its marks | WP6.15 | WP6.15 waits, and WP6.16 is built meanwhile (BL9) |
| The ruling on the flow in 3D | After WP6.15 | It is not built; the price stays in WP6.15's record |
| The prototype's branch deleted | After WP6.12 merges (BJ3) | It stays on `origin` |

## Verification

```bash
.claude/hooks/gate.sh run
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP6.05, WP6.09 | none kept | Outside N1's scope, or the prototype's runs (BJ1) |
| WP6.06 | 1 | VER-48 |
| WP6.08 | 2 | VER-80 |
| WP6.10 | 1, 2 | VER-81; VER-65; VER-14 to VER-18, VER-42, VER-77; VER-62's and VER-80's thirteen walks |
| WP6.11 | 1, 2 | VER-82; VER-22; VER-80's dielectric and log guards |
| WP6.12 | 1, 2 | VER-56 and QR-14's one class restated; VER-12, VER-13, VER-31; criterion 3's full check |
| WP6.13 | 2 | VER-83, proposed |
| WP6.14 | 1 | VER-10, restated for a 3D mesh |
| WP6.15 | 2 | VER-84, proposed |
| WP6.16 | 2 | VER-85, proposed, its fixture distribution found by a fresh process |

**The phase is complete when** (§8.1's gate):

1. **Tiers 1 and 2 pass on Linux, macOS and Windows**, on the close's own full run. No waiver (AY4); a miss is fixed.
2. **VER-62 is unmoved at 10⁻⁸** by every package but the kernel's: on a push its two walks, on the nightly run the
   other five (BA14). A miss is reverted, or re-pinned only by ruling (G10).
3. **WP6.12 holds all seven walks and the guard numbers (VER-80) within 10⁻⁸ of their pins before it merges, and
   VER-12 to VER-22, VER-31, VER-42 and VER-77 pass unchanged** (BC4). A walk that the kernel's structure moved is
   re-pinned in its package on VER-62's three conditions, the pull request listing old and new (BL2).
   Prediction: round-off alone where a slot is today's integral (the prototype: at most 2.9 × 10⁻¹²); a slot cut
   otherwise may move a walk by its quadrature error. A move that fails one of the three stops the package for the
   author; any other miss is fixed or reverted.
   Met by WP6.10 for the coupled models: the thirteen walks at most 2.898 × 10⁻¹² (`2wcd-charged`), none re-pinned.
4. **A fresh package session starts under the reading limit** of 8,000 words (AZ18; BD3). A miss continues the
   cleanup.
5. **The author rules the kernel's design before its packages are planned** (BC2). Met by §8.2.62.
6. **The kernel's own Tier 1 tests pass** (FR-40; §5.4.4), **and a term an installed package registers is found by
   the command line and the workbench and named in the manifest, with its test** (BC5; WP6.16).
7. **VER-61 and VER-65 hold**, VER-65 with the rule that no module holding a term imports the backend (BL6). A
   cycle or a new backend subpackage goes to the author (H6).
8. **Each row the phase owns is `fixed` or ruled** (AM4): REV-279, REV-67, REV-298, REV-300, REV-301, MOD-10.
9. **Each proposal of the ground-up review is ruled or carried with its owner** (BA13). Met by §8.2.53.
10. **The wall with a ragged rim recovers its axis to VER-48's 10⁻⁶ rad.** Met on Linux by WP6.06; the close
    repeats it on the three platforms.
11. **Each carried package is reported with its sessions, agent hours and touches** (BC10; BL10).
12. **The guard numbers are stored** (BC3; VER-80). Met by WP6.08.
13. **VER-13 on a 3D mesh converges at its order** (CON-01; BL4): on three meshes, each half the size of the last,
    the error against the closed form falls at an observed order above a floor that WP6.13's plan argues before
    any run. Prediction: order 3, for elements of order 2 on a curved mesh; the trial measured 3.8 × 10⁻³ at size
    0.4. A miss is investigated, and the floor stands.
14. **VER-17 on a 3D mesh holds VER-17's 2 %**, with the potential and the ions (BL4), after WP6.14's measure of
    the direct solve meets the marks its plan registered. A measure that misses goes to the author: a coarser
    mesh, another solver, or the benchmark stops at its mesh. A conductance outside 2 % is investigated, on a finer
    mesh where the measure allows; the tolerance stands.
15. **The flow in 3D is priced** by WP6.15's trial, in §8.3's units with its numbers; the author rules on it.

## End-of-phase report

The close fills it. It reports, each with the command or test that logs it:

- the three platforms' Tier 1 and Tier 2 counts and times, from the close's full run;
- VER-62's largest relative drift per walk and platform, and the guard numbers' per switch, at WP6.12
  (stabilisation mode named); each walk a kernel package re-pinned, with its old and new values and the cause;
- the prototype's drift on each of the thirteen stored walks, and the design as ruled;
- the kernel's terms with the test each has, and each term an installed package registered in the close's run;
- the 3D benchmarks: each mesh with its element count and error, the observed order, the pore's conductance
  against the closed form, the direct solve's peak memory and time, and the price of the flow in 3D;
- the reading baseline and a fresh session's reading against the limit (`usage.py`);
- the ground-up review's proposals by ruling: kept, changed now, changed later, dropped;
- the ragged-rim wall's axis over its perturbed draws, and 2WCD's channel axis against 0.0073 nm (WP6.06);
- the orchestrator's three facts, each package it carried with its sessions, agent hours and touches against the
  packages before it, and the count behind the browser tests' path rule;
- the word counts of the records the cleanup cut, before and after;
- the review register's counts by status, and `holds-now.yaml`'s `open:` lines;
- the push gate's and CI's times;
- the phase's measured cost in sessions, agent hours and touches against this plan's estimate.
