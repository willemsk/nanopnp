# Phase 6 (Cleanup and the kernel): a physics model composed of registered terms, on records a session can read

**Status: in progress. Delivered: WP6.01, WP6.02, WP6.03, WP6.04, WP6.05, WP6.06. Amended 24 November 2026 (§8.2.53; §8.2.54): WP6.06 to WP6.08 are planned by scope and numbered in build order; the kernel's packages, the installed packages and the close are provisional until the author rules the kernel's design. Release: v0.7 (`v0.7.0`).**

## In brief

**What changes.** First comes a package that changes how a package is carried: one session that you start hands the
plan, its review, the building and the shipping to fresh helpers, and comes to you only for rulings, the plan's
approval and the merge. It is tried on the next two packages: the fix for the pore's axis, which rounding could lock
about one degree off, and stored reference numbers for the model's optional switches. Then a design package writes how the physics will be rebuilt from small
registered terms, with a throwaway prototype. You rule that design; only then are the kernel's packages planned.
Packages are numbered in the order they are built.

**Cost.** About 43 sessions, 26 to 49 agent hours and 66 times you act, at today's rates. Your ruling round on the
design adds about 2 sessions and 3.

**What could go wrong.** A helper cannot ask you a question or start its own helper, so the session you start does
both; the next two packages show whether that holds. The prototype may miss the stored numbers: that comes
to you before any kernel package is planned. The kernel is checked in full only at its last package, so a moved
result may be found late; the nightly run would show it. Its size is a draft count that the review found low.

**Your call.** Do you approve this amendment, by merging its pull request? Yours later: the kernel's design,
and the target for how often a package needs you. *Recommendation:* approve; it departs from none of your rulings.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, and the rulings are §8.2.49 to §8.2.55 (AY to BE). The
text each amendment replaced is in [the record](phase-6-record.md). This file keeps its first name: the library's
foundations are Phase 7 (BC7), in [the input note](../sessions/phases-6-to-11.md).

Phase 6 answers one question: **can the physics be rebuilt from registered terms, without moving a number, before the
library's foundations and the workbench are built on it?** Its gate is §8.1's.
[The ground-up review](../../project/ground-up-review.md) is delivered and ruled (§8.2.53).

True of the codebase today:

- **A pore's axis found from its channel holds at a flat rim** (WP6.06; REV-279 fixed). `structure/stage.py` `align`
  takes that axis only under C1 or `axis: cavity`; every walk of VER-62 takes the ring's.
- **A model is assembled in one class.** `physics/models.py` `CoupledModel` assembles the weak forms, and
  `physics/terms.py` holds a `Term` for each, for display alone (GU-01).
- **A switch is code.** `physics/models.py` `SWITCHES` is a closed tuple; `post/forces.py` `_domain_force` assembles
  again the terms of `physics/flow.py`.
- **Nothing finds a registration in an installed package** when the command line or the workbench starts (REV-67).
- **VER-62's stored numbers cover the default switches alone**: the review's claim, not checked at its source
  (§8.2.53); WP6.07 checks it first.
- **A package takes at least four sessions the author starts** (§8.3) and about eight touches (BC10). The browser
  tests take 468 s of the push gate's 539 s (BC15).

Risks: none is retired.

Excluded: the library's foundations but for "switches as data", Phase 7 (BC3, BC7); the workbench's rebuild and the composer's tool,
Phase 8 (BC6); the benchmark on a coarse 3D mesh, until WP6.08 prices it and the author rules (BC5); a comparison with the published results (BC8 records one at Phase 7's close).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Order and numbers | The orchestrator, the axis fix, the guard numbers, the kernel's design, the author's ruling, the kernel, the installed packages, the close; numbered as built | The kernel is checked against numbers nothing else has moved (BC3; BC10; BD1) |
| How a package is carried | From WP6.06 by the orchestrator; the three commands stay | A fresh helper is the checkpoint without the compaction (BC10) |
| The kernel's design | A package of its own with a throwaway prototype, ruled before any kernel package is planned | The composition is a design problem, not a refactor (BC2) |

## Conventions established by earlier phases

- **A VER-62 miss is reverted, or re-pinned by ruling** (G10); **a moved edge edits `modularity-layering.yaml`**
  (VER-61).
- **A deviation from the validated model is a switch, default off** (`.claude/rules/physics-numerics.md`).
- **The schema and `nanopnp.PUBLIC` may change until v1.0**, each break in `CHANGELOG.md` (F4).
- **A cost is fixed after it is measured** (M2). **An open item is a `REV-nn` row** (H12).

## Work packages

WP6.05 to WP6.08 take `v0.7.0-alpha.5` to `v0.7.0-alpha.8`; the close takes `v0.7.0` alone (§8.4.1; BD1).

### WP6.01 to WP6.04 — delivered

| Package | Live |
|---|---|
| [WP6.01](wp6.01-the-windows-leg.md), the Windows leg (REV-277; AY4), 22 November 2026 | AZ8's ship rule |
| [WP6.02](wp6.02-the-cleanup-measure-audit-records.md), the cleanup's measure and records (AZ9 to AZ17), 22 November 2026 | The reading limit binds a session's first window (AZ15) |
| [WP6.03](wp6.03-the-cleanup-instructions-copilot-host.md), the instructions (AZ18 to AZ21), 23 November 2026 | The limit is 8,000 words, measured at 7,186; each plan proposes its two models |
| [WP6.04](wp6.04-the-ground-up-review.md), the ground-up review (BA10 to BA13), 24 November 2026 | Its 25 proposals are ruled or carried (§8.2.53); REV-281 to REV-287 are Phase 7's and Phase 8's |

### WP6.05 — The orchestrator (BC10, BC15; BD2 to BD6)

*Delivered 24 November 2026.* [The plan](wp6.05-the-orchestrator.md). Live: `/np-carry wp <n>` carries WP6.06 and
WP6.07, which are measured (BC10); the reading limit binds every helper that implements (BD3); the browser-path
count missed, 32 < 34, so the push gate keeps the browser tests (BC15 spent).

### WP6.06 — The channel's axis at a ragged rim (REV-279; VER-48; BA8; BB1)

*Delivered 25 November 2026.* [The plan](wp6.06-the-channel-axis-at-a-ragged-rim.md). Live: a channel's axis
no longer locks at a flat rim, and may differ by up to about 1° from v0.6's (BA8); a change that moves it bumps
stage 1's `channel_axis_revision` (BE2); the two limits stay (BE1); an axis found from joggled input is warned of
(BE6); a lumen with atoms on its axis is warned of (AO4).

### WP6.09 — The lean carry (BF1 to BF8)

*Planned 25 November 2026* ([the plan](wp6.09-the-lean-carry.md)); built before WP6.07, so that WP6.07 is the first
package carried the lean way and measures it (BF7). After WP6.06's post-mortem: Fable 5.2 only plans, Sonnet 5.5
runs the carry and ships, Opus 5.5 builds, reviews once and takes a red CI; a helper that waits hands off to a fresh
one through a note; the plan checks itself; a finding left to the author is an open item by default; each helper
lists its tools; the mechanics are `just land`. It changes no code under `src/`. About 1 session, 2 to 3 agent hours
and 2 touches.

### WP6.07 — The guard numbers (BC3)

*Planned by scope.* Reference numbers for the switches off their default: PHY-23's terms, the log branch and NUM-14's
mode. It first checks that VER-62's walks cover the default switches alone, and stores only what is missing. The numbers are recorded once, on this package's tree, on which VER-62 passes and which
no kernel package has touched. They are a regression reference with no independent oracle, reproduced to 10⁻⁸
relative as VER-62's are, each with its stabilisation mode; a later change to one is a re-pin by ruling (G10). It
changes no physics. Its plan settles open decision 14; this plan's input is that the nightly run holds them (BA14). About 3 sessions, 2 to 3 agent hours
and 4 touches.

### WP6.08 — The kernel's design (BC2, BC5)

*Planned by scope.* A design page and a throwaway prototype. The page states the term, a correction as a coefficient
that terms share, the rule that binds terms (PHY-08), each flux integrated once, the nine names of `physics/` the
workbench reads, how an installed package registers, and §5.4.1's interface (MOD-10; AZ1). The prototype rebuilds the
simplest model from terms. The package reports whether example 01's walk of VER-62 holds to 10⁻⁸, with the commit
that holds the prototype, the command and the stabilisation mode, so the run can be repeated; the tree it merges
holds none of the prototype's code. It proposes the kernel's packages and their Tier 1 and Tier 2
tests (FR-40), and prices the benchmark that solves VER-13 or VER-17 on a coarse 3D mesh (BC5). The page is a
proposal until the round below, which rewrites ADR-005, §5.4 and §5.5. About 5 sessions, 3 to 6 agent hours and 8
touches.

### The ruling round on the kernel's design (BC2)

After WP6.08 merges, at `/np-plan amend 6` (BC10). The author rules the design, a prototype that missed 10⁻⁸ first,
and the 3D benchmark on its price (BC5), and sets the touches target; the round numbers what follows from WP6.09. About 2 sessions and 3 touches.

### Provisional (BC1, BC4, BC5)

Input to that round, in order; none is numbered before it:

| Package | Scope |
|---|---|
| The kernel | FR-40's library half, in about four packages until the design sets the number: FR-20's interface as the composition, §5.4.1's interface (MOD-10), switches as data, the forces sharing the weak form's terms. The shell follows a moved name; no screen changes. About 20 sessions, 12 to 24 agent hours and 32 touches |
| The installed packages | A term, a correction, a shape or a solver that an installed package declares, found at start-up and named in the manifest; a term with no analytic case marked unverified; the public registering names (REV-67); QR-14 and §5.5. About 3 sessions, 2 to 3 agent hours and 4 touches |
| The close | The end-of-phase report, the three platforms' full run and `v0.7.0`; `/np-ship phase 6` ships it. About 3 sessions, 2 to 3 agent hours and 4 touches |

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 to 5, 8 to 10 | The cleanup's limits, the Copilot tag, the Windows leg, the project's scope, the review and its proposals | **Settled by the author, 22 to 24 November 2026** (AZ, BA, BB, BC); the record holds the rows |
| 6, 7 | AM2's drift bound; a run above order 2; the speed-up's thresholds; the names after `Project` splits | **Moved to Phase 7** (BC7); the input note carries them |
| 11 | What §5.2's two limits become if the fix moves 2WCD's measured axis (REV-239) | **Settled by the author, 25 November 2026**, at WP6.06's plan, before the fix was measured: the limits stay (BE1) |
| 12 | The numbers of the packages after the review | **Settled by the author, 24 November 2026**: in build order (BD1) |
| 13, 17 | What the reading limit counts under the orchestrator; helpers or separate sessions | **Settled by the author, 24 November 2026**: every helper that implements; helpers (BD2, BD3). The browser tests' rule is not built: WP6.05's count missed, 32 < 34 (BD4; BC15 spent) |
| 14 | Which walk carries each switch off its default; the guard numbers' identifier in §7; whether the nightly run holds them | WP6.07's plan (BC3) |
| 15 | The target for the author's touches a package | **Author**, at the round after WP6.08, from WP6.06's and WP6.07's measured lines (BC10) |
| 16 | The kernel's design; the number and order of its packages; whether the 3D benchmark is built, on its price | **Author**, at the round after WP6.08 (BC2, BC5) |
| 18 | The model a carried package's main session is started on, which both of its reviews take (REV-288) | **Author**, at the round after WP6.08, with WP6.06's and WP6.07's measured lines; left open by the author, 24 November 2026 |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| The kernel's design ruled; the 3D benchmark; the touches target | The round after WP6.08 | No kernel package is planned (BC2) |
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |

## Verification

```bash
.claude/hooks/gate.sh run
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP6.05 | none | Outside N1's scope. Review: the record of the three facts and of the count; CI still runs every browser test |
| WP6.06 | 1 | VER-48 |
| WP6.07 | 2 | VER-62's walks with the switches off their default; the identifier is open decision 14 |
| WP6.08 | none kept | Example 01's walk of VER-62 on the prototype, reported with its commit and command |
| The provisional packages | 1, 2 | FR-40's tests, which the design names; criterion 3's; set at the round after WP6.08 |

**The phase is complete when** (§8.1's gate; that round restates criteria 3 and 6 with their tests):

1. **Tiers 1 and 2 pass on Linux, macOS and Windows**, on the close's own full run. No waiver (AY4); a miss is fixed.
2. **VER-62 is unmoved at 10⁻⁸** by every package: on a push its two walks, on the nightly run the other five (BA14).
   Prediction: round-off alone: WP6.05 changes no `src/`, no walk takes the channel's axis, WP6.07 only adds
   numbers, WP6.08 merges no prototype. A miss is reverted, or re-pinned only by ruling (G10).
3. **The kernel's last package reproduces all seven walks and the guard numbers to 10⁻⁸ before it merges, and
   VER-12 to VER-22, VER-31, VER-42 and VER-77 pass unchanged** (BC4). Prediction: it holds where each flux is
   integrated once (the physics reviewer, at BC2). A miss is fixed or
   reverted, and re-pinned only by ruling (G10).
4. **A fresh package session starts under the reading limit** of 8,000 words (`usage.py`; AZ18), by every helper
   that implements (BD3). A miss continues the cleanup.
5. **The author rules the kernel's design before its packages are planned**; the prototype holds example 01's walk
   to 10⁻⁸, or the miss is put to the author (BC2).
6. **The kernel's own Tier 1 and Tier 2 tests pass** (FR-40), **and a term an installed package registers is found
   by the command line and the workbench and named in the manifest, with its test** (BC5).
7. **VER-61 and VER-65 hold.** A cycle or a new backend subpackage goes to the author (H6).
8. **Each row the phase owns is `fixed` or ruled** (AM4): REV-279, REV-67, MOD-10.
9. **Each proposal of the ground-up review is ruled or carried with its owner** (BA13). Met by §8.2.53.
10. **The wall with a ragged rim recovers its known axis to VER-48's 10⁻⁶ rad** on every perturbed draw, and on the
    three platforms at the close. Today 3 of 8 draws lock 0.22° to 0.62° off, and 17 of the 24 of WP6.06's plan up
    to 0.84°; prediction: none locks. A draw that
    still locks is investigated, and the tolerance stands. **2WCD's channel axis is measured again** against its
    0.0073 nm. Prediction: unmoved within VER-48's 10⁻⁴ nm if none of its planes holds a split tie, which WP6.06's
    plan measures first. A move, of it or of the farthest centre's 0.0148 nm, amends VER-48 and §5.2's NOTE in the
    fix's commit and is reported; the limits stay, and the package stops for the author only if 2WCD would pass one
    (BE1).
11. **The orchestrator's three facts are recorded, and WP6.06 and WP6.07 are reported with their sessions, agent
    hours and touches** (BC10; BD2). A package it cannot carry goes back to the three commands.
12. **The guard numbers are stored** after the check of VER-62's coverage (BC3). Prediction: the walks cover the
    default switches alone; if not, WP6.07 stores only what is missing.

## End-of-phase report

The close fills it. It reports, each with the command or test that logs it:

- the three platforms' Tier 1 and Tier 2 counts and times, from the close's full run;
- VER-62's largest relative drift per walk and platform, and the guard numbers' per switch, at the kernel's last
  package (stabilisation mode named);
- the prototype's drift on example 01's walk, and the design as ruled;
- the kernel's terms with the test each has, and each term an installed package registered in the close's run;
- the reading baseline and a fresh session's reading against the limit (`usage.py`);
- the ground-up review's proposals by ruling: kept, changed now, changed later, dropped;
- the ragged-rim wall's axis over its perturbed draws, and 2WCD's channel axis against 0.0073 nm (WP6.06);
- the orchestrator's three facts, each package it carried with its sessions, agent hours and touches against the
  packages before it, and the count behind the browser tests' path rule;
- the word counts of the records the cleanup cut, before and after;
- the review register's counts by status, and `holds-now.yaml`'s `open:` lines;
- the push gate's and CI's times;
- the phase's measured cost in sessions, agent hours and touches against this plan's estimate.
