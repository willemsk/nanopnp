# Phase 6 (Cleanup and the kernel): a physics model composed of registered terms, on records a session can read

**Status: in progress. Delivered: WP6.01, WP6.02, WP6.03, WP6.04. Amended 24 November 2026 (§8.2.53; §8.2.54): WP6.05 to WP6.08 are planned by scope and numbered in build order; the kernel's packages, the installed packages and the close are provisional until the author rules the kernel's design. Release: v0.7 (`v0.7.0`).**

## In brief

**What changes.** First comes a package that changes how a package is carried: one session that you start hands the
plan, its review, the building and the shipping to fresh helpers, and comes to you only for rulings, the plan's
approval and the merge. It is tried on the next two packages: the fix for the pore's axis, which rounding can lock
0.6 degrees off, and stored reference numbers for the model's optional switches. Then a design package writes how the physics will be rebuilt from small
registered terms, with a throwaway prototype. You rule that design; only then are the kernel's packages planned.
Packages are numbered in the order they are built.

**Cost.** About 43 sessions, 26 to 49 agent hours and 66 times you act, at the rates of before the new way of
carrying a package. Your ruling round on the design adds about 2 sessions and 3.

**What could go wrong.** The helpers may be unable to run the commit checks or to ask you a question: the first
package tests that first, and falls back to separate sessions. The prototype may miss the stored numbers: that comes
to you before any kernel package is planned. The kernel is checked in full only at its last package, so a moved
result may be found late; the nightly run would show it. Its size is a draft count that the review found low.

**Your call.** Do you approve this amendment, by merging its pull request? Yours later: the kernel's design,
and the target for how often a package needs you. *Recommendation:* approve; it departs from none of your rulings.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, and the rulings are §8.2.49 (AY1 to AY8), §8.2.50 (AZ1 to
AZ21), §8.2.51 (BA1 to BA15), §8.2.52 (BB1 to BB7), §8.2.53 (BC1 to BC24) and §8.2.54 (BD1). The text each amendment
replaced is in [the record](phase-6-record.md). This file keeps its first name: the library's foundations are Phase 7
since BC7, and [the input note](../sessions/phases-6-to-11.md) holds them.

Phase 6 answers one question: **can the physics be rebuilt from registered terms, without moving a number, before the
library's foundations and the workbench are built on it?** Its gate is §8.1's. Its earlier question, how the program
would be built if it were started over (BA10), is answered by [the ground-up review](../../project/ground-up-review.md)
and ruled (§8.2.53).

True of the codebase today:

- **A pore's axis found from its channel can lock off the true one.** `structure/cavity.py` `channel_axis` holds a
  second fixed point at a ragged rim, up to about 0.6° off, and rounding decides which one it reaches (REV-279).
  `structure/stage.py` `align` takes that axis only under C1 or `axis: cavity`, and `structure/orient.py`
  `_channel_line` where no covariance axis stands apart; every walk of VER-62 takes the ring's.
- **A model is assembled in one class.** `physics/models.py` `CoupledModel` assembles the weak forms of the modules
  beside it, and `physics/terms.py` holds a `Term` for each, for display alone (GU-01).
- **A switch is code.** `physics/models.py` `SWITCHES` is a closed tuple; `post/forces.py` `_domain_force` assembles
  again the terms of `physics/flow.py`.
- **Nothing finds a registration in an installed package** when the command line or the workbench starts (REV-67).
- **VER-62's stored numbers cover the default switches alone.** The round took this from the review and did not check
  it at its source (§8.2.53); WP6.07 checks it first.
- **A package takes at least four sessions the author starts** and about eight touches (§8.3); the browser tests take
  468 s of the push gate's 539 s (BC15).

Risks: none is retired.

Excluded: the error base, the results side, the library's shape but for "switches as data", the model's open terms,
the exports, the refusals reworded and the speed-up, all Phase 7 (BC3, BC7); the workbench's rebuild and the
composer's tool, Phase 8 (BC6); the benchmark on a coarse 3D mesh, until WP6.08 has priced it and the author has
ruled (BC5); any code of WP6.08's prototype in the tree it merges (BC2); a converter for v0.6 runs (AZ5; BC20); a
linear-solver swap (Z6); a comparison with the published results (BA3; BC8 records one at Phase 7's close).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| The ground-up review | WP6.04, delivered and ruled: a report and no code; everything open but §4's physics | BA10 to BA13; §8.2.53 |
| Order | The orchestrator, the axis fix, the guard numbers, the kernel's design, the author's ruling on it, the kernel, the installed packages, the close | The kernel is checked against numbers that nothing else has moved (BC3; BC10) |
| Numbers | In the order the packages are built; each tag by its number | Tags rise along the history (BD1; §8.4.1) |
| How a package is carried | From WP6.06 by the orchestrator: one session, a fresh helper for each step; the three commands stay as the way back | A fresh helper for each stretch is today's checkpoint without the compaction (BC10) |
| The kernel's design | A package of its own with a throwaway prototype; ruled by the author at a further amendment, before any kernel package is planned | The composition is a design problem, not a refactor (BC2) |
| The kernel's check | Each kernel package on the per-push selection; all seven walks and the guard numbers at the last | BC4; BA14 |
| Terms from outside | N1 admits a term within electrolyte transport; an installed package's term is found after the kernel | The kernel fixes the public names, so they break once (BC5) |
| Old runs | Refused by schema, never converted before v1.0 | AZ5; F4; BC20 |
| Restructuring beyond a plan | Allowed while the push gate passes | BA7, BA14 |

## Conventions established by earlier phases

- **A VER-62 miss is reverted, or re-pinned by ruling** (G10); **a moved edge edits `modularity-layering.yaml`**
  (VER-61).
- **A deviation from the validated model is a switch, default off** (`.claude/rules/physics-numerics.md`).
- **The schema and `nanopnp.PUBLIC` may change until v1.0**, each break in `CHANGELOG.md` (F4).
- **A cost is fixed after it is measured** (M2). **An open item is a `REV-nn` row** (H12).


## Work packages

WP6.05 to WP6.08 take `v0.7.0-alpha.5` to `v0.7.0-alpha.8`, each by its number; the close takes `v0.7.0` alone
(§8.4.1; BD1).

### WP6.01 — The Windows leg (REV-277; AY4)

*Delivered 22 November 2026.* [The plan](wp6.01-the-windows-leg.md). Live: AZ8's ship rule; REV-279 is WP6.06's.

### WP6.02 — The cleanup: measure, audit, records (REV-271, REV-272; AY8; AZ9 to AZ17)

*Delivered 22 November 2026.* [The plan](wp6.02-the-cleanup-measure-audit-records.md). Live: the limit of AZ13 and AZ18, which binds a session's first window (AZ15); its Outcome's outdated list.

### WP6.03 — The cleanup: instructions, the Copilot host retired (AY5; AZ18 to AZ21; REV-166 to REV-168, REV-278)

*Delivered 23 November 2026.* [The plan](wp6.03-the-cleanup-instructions-copilot-host.md). Live: the 8,000 words of AZ18 bind every `/np-implement` session's first window (§8.4.4), measured at 7,186; each plan proposes its two models (AZ20, AZ21); the tag `copilot-host` is pushed (AZ19).


### WP6.04 — The ground-up review (BA10 to BA13; BB2 to BB7)

*Delivered 24 November 2026.* [The plan](wp6.04-the-ground-up-review.md). Live: each of its 25 proposals is ruled or
carried with its owner (§8.2.53; REV-280); REV-281 to REV-287, seven questions for a trial, are Phase 7's and
Phase 8's.

### WP6.05 — The orchestrator (BC10, BC15)

*Planned by scope; next.* One session that the author starts carries a package. It reads the position and the brief,
hands the plan, the plan's review, each stretch of the implementation between two checkpoints and the ship to a
sub-agent with an empty context, and brings the author the rulings, the plan's approval and the merge. The plan and
the commits carry the state. The three commands stay as the way back, each plan still proposes its two models (AZ20,
AZ21), and a ruling round stays a session of its own.

The package first checks three facts that the round did not verify: that the commit gate runs inside a sub-agent,
that a sub-agent can start its own, and that it can put a question to the author. If one fails it builds separate
sessions that the orchestrator starts. It also counts how many of the last 100 pushes a safe path rule for the
browser tests would have skipped, and applies the rule if they are more than a third; a pull request's CI still runs
every browser test. §8.4.4 and §8.4.5 change with it, and §7.6 with the gate if the count passes. The package itself
runs under the three commands. Its plan settles open decision 17. About 5 sessions, 3 to 6 agent hours and 8 touches.

### WP6.06 — The channel's axis at a ragged rim (REV-279; VER-48; BA8; BB1)

*Firm; planned after WP6.05 merges, since the orchestrator carries it (BC10).* It makes a plane's centre robust to a
broken tie at a ragged rim, and measures 2WCD's channel axis again. From v0.7 a structure with a ragged rim may be
given an axis up to about 0.6° different from v0.6's, the one number a user sees that Phase 6 changes (BA8);
`CHANGELOG.md` says so. VER-48's gate test tilts the wall with the ragged rim again; the perturbed draws read
`cavity.channel_axis` itself, since the gate's refusal prints 0.01°. The oracle is the axis the test wall is built
about. §5.2's NOTE on stage 1 takes the new method and 2WCD's numbers. No Tier 3 leg. It is the first package the
orchestrator carries, and its sessions, agent hours and touches are measured for open decision 14. About 4 sessions,
2 to 4 agent hours and 6 touches, at the rates of before the orchestrator. Its plan settles open decision 11.

### WP6.07 — The guard numbers (BC3)

*Planned by scope.* Reference numbers stored for the switches off their default: PHY-23's terms, the log branch and
NUM-14's mode. The package first checks that VER-62's walks cover the default switches alone; where a walk already
covers one of the three, it stores only what is missing and says so. Each number is stored as VER-62's are, to be
reproduced to 10⁻⁸ relative, and names its stabilisation mode. It changes no physics and no number a user sees. Its
plan settles open decision 18; this plan's input is that the nightly run holds the guard numbers, as it holds
VER-62's other walks (BA14). It is the second package the orchestrator carries, and is measured as WP6.06 is. About 3
sessions, 2 to 3 agent hours and 4 touches.

### WP6.08 — The kernel's design (BC2, BC5)

*Planned by scope.* A design page and a throwaway prototype. The page states the term, a correction as a coefficient
that terms share, the rule that binds terms (PHY-08), each flux integrated once, the nine names of `physics/` that
the workbench reads, and how an installed package registers. The prototype rebuilds the simplest model from terms,
and the package reports whether example 01's walk of VER-62 holds to 10⁻⁸; the tree it merges holds none of the
prototype's code. It proposes the kernel's packages, their number and order, and the kernel's own Tier 1 and Tier 2
tests (FR-40), and it prices the benchmark that solves VER-13 or VER-17 on a coarse 3D mesh (BC5). §5.4.1's interface
is its subject too (MOD-10; AZ1). The page is a proposal until the round below; ADR-005, §5.4 and §5.5 are rewritten
at the ruling, not in this package. About 5 sessions, 3 to 6 agent hours and 8 touches.

### The ruling round on the kernel's design (BC2)

After WP6.08 merges, at `/np-plan amend 6`, in a session of its own (BC10). The author rules the design; a prototype
that missed 10⁻⁸ is put first, before any kernel package is planned. The round also rules the 3D benchmark on its
price (BC5), sets the target for a package's touches from WP6.06's and WP6.07's measured lines (BC10), and numbers
the kernel's packages from WP6.09, then the installed packages and the close. About 2 sessions and 3 touches.

### Provisional (BC1, BC4, BC5)

None is planned or numbered before the round on the design. Its input, in order:

| Package | Scope |
|---|---|
| The kernel | FR-40's library half, in about four packages until the design sets the number: a physics model composed of registered terms in `physics/`, FR-20's interface as the composition, §5.4.1's interface (MOD-10), switches as data, and the forces sharing the weak form's terms. The shell reads a moved name of `physics/` at its new place, and no screen changes. Each package is pushed on the per-push selection; the last reproduces all seven walks of VER-62 and the guard numbers to 10⁻⁸ before it merges (BC4). About 20 sessions, 12 to 24 agent hours and 32 touches |
| The installed packages | A term, a correction, a shape or a solver that an installed package declares, found by the command line and the workbench and named in the manifest with its package and version; a term with no analytic case marked unverified; which registering names are public (REV-67); QR-14 and §5.5. About 3 sessions, 2 to 3 agent hours and 4 touches |
| The close | The end-of-phase report, the three platforms' full run and `v0.7.0`; `/np-ship phase 6` ships it. About 3 sessions, 2 to 3 agent hours and 4 touches |

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | §8.2.50's seven rulings | **Settled by the author, 22 November 2026** (AZ1 to AZ7) |
| 2 | The reading limit; what may leave the history; the baseline's transcripts | **Settled by the author, 22 and 23 November 2026** (AZ9 to AZ12, AZ14, AZ15, AZ18; §8.4.4) |
| 3 | The Copilot tag's name | **Settled by the author, 23 November 2026**: the git tag `copilot-host` (AZ19) |
| 4 | Whether a pull request's CI runs the Windows leg | **Settled by the author, 22 November 2026**: no; the three platforms at the close alone (AZ8) |
| 5 | The project's scope, and Phase 6's packages with it | **Settled by the author, 23 November 2026** (BA1 to BA15) |
| 6 | What AM2's "moves one of them" means, and the drift that stops the re-pin | **Moved to Phase 7** with the equations package (BC7); the input note carries it |
| 7 | A run above order 2; the speed-up's thresholds; the names after `Project` splits | **Moved to Phase 7** with their packages (BC7); the input note carries them |
| 8 | What comes first after the review; what the review designs for | **Settled by the author, 23 November 2026** (BB1, BB2) |
| 9 | How the review guards against reasoning from the program as it is; where its report lives; its two models | **Settled by the author, 23 November 2026**: blind designs from the program's purpose, then rule by rule; the project's pages; Fable 5.2 writes and ships (BB3 to BB5, BB7) |
| 10 | The review's proposals | **Settled by the author, 24 November 2026** (BC1 to BC24) |
| 11 | What §5.2's two limits become if the fix moves 2WCD's measured axis (REV-239) | **Author**, at WP6.06's plan, before the fix is measured |
| 12 | The numbers of the packages after the review | **Settled by the author, 24 November 2026**: in build order, WP6.05 to WP6.08 (BD1); the rest from WP6.09, at the round on the design |
| 13 | The kernel's design; the number and order of its packages; whether the benchmark on a coarse 3D mesh is built, on its price | **Author**, at `/np-plan amend 6` after WP6.08 (BC2, BC5) |
| 14 | The target for the author's touches a package | **Author**, at that round, from WP6.06's and WP6.07's measured lines (BC10) |
| 15 | Whether the helpers run inside one session or as separate sessions | WP6.05, by its three checks (BC10) |
| 16 | Whether the push gate chooses the browser tests by path | WP6.05, by its count (BC15) |
| 17 | What the reading limit counts once an orchestrator carries a package: its own first window, each helper's, or both | **Author**, at WP6.05's plan, before any measurement (AZ18; criterion 4) |
| 18 | Which walk carries each switch off its default; the identifier the guard numbers take in §7; whether the nightly run holds them | WP6.07's plan (BC3) |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| The ruling on what the reading limit counts under the orchestrator | WP6.05's plan | The plan waits; nothing is measured against a limit not yet ruled |
| The ruling on §5.2's two limits, if the fix moves 2WCD's axis | WP6.06's plan | The fix is not measured (open decision 11) |
| The ruling on the kernel's design, and on the 3D benchmark at its price | The round after WP6.08 | No kernel package is planned (BC2) |
| The target for a package's touches | The round after WP6.08 | The packages are reported with their touches and no target (BC10) |
| Merges; tags a session cannot push | Each package | The session dispatches `tag.yml` and prints the commands |

## Verification

```bash
.claude/hooks/gate.sh run
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

| Package | Tier | Identifiers |
|---|---|---|
| WP6.01 | 1, 2 | The failing test, on the three platforms |
| WP6.02, WP6.03 | none kept | VER-45; `clause.py` resolves each identifier WP6.02's plan lists |
| WP6.04 | none | No test: review checks that its diff holds no `src/`, `tests/`, case schema or public name, and that the report holds what BA13 lists |
| WP6.05 | none | No test in §8.2.13 N1's scope: review checks the record of the three facts, the count behind the path rule, and that a pull request's CI still runs every browser test |
| WP6.06 | 1 | VER-48 |
| WP6.07 | 2 | VER-62's walks, with the switches off their default; the identifier is open decision 18 |
| WP6.08 | none kept | Example 01's walk of VER-62 on the prototype, reported; review checks that the merged tree holds none of the prototype's code |
| The provisional packages | 1, 2 | FR-40's tests, which the design names; VER-62 and the guard numbers; VER-12 to VER-22, VER-31, VER-42, VER-77; set by the `/np-plan amend 6` after WP6.08 |

**The phase is complete when** (§8.1's gate; criteria 3 and 6 rest on provisional packages, and the round on the
design restates them with their tests):

1. **Tiers 1 and 2 pass on Linux, macOS and Windows**, on the close's own full run. No waiver (AY4); a miss is fixed.
2. **VER-62 is unmoved at 10⁻⁸** by every package: on a push the two walks it selects, on the nightly run the other
   five (BA14). Prediction: round-off alone. WP6.05 changes no `src/`; WP6.06 moves none, since no walk takes the
   channel's axis; WP6.07 adds numbers and moves none; WP6.08 merges no code of its prototype. A miss is reverted, or
   re-pinned only by ruling (G10).
3. **The kernel's last package reproduces all seven walks of VER-62 and the guard numbers to 10⁻⁸ before it merges,
   and VER-12 to VER-22, VER-31, VER-42 and VER-77 pass unchanged** (BC4). The tolerance is VER-62's own. Prediction:
   it holds where each flux is integrated once, since a flux integrated term by term moves its quadrature (the
   physics reviewer, at BC2); the prototype's walk of example 01 is the first measurement. A miss is investigated and
   fixed, or reverted, and re-pinned only by ruling (G10).
4. **A fresh package session starts under the reading limit** of 8,000 words (`usage.py`; AZ18), counted as open
   decision 17 rules. A miss continues the cleanup; the limit is re-ruled only before a measurement.
5. **The kernel's design is ruled by the author before its packages are planned**, and its prototype holds example
   01's walk to 10⁻⁸ or the miss is put to the author (BC2). The round's record shows both.
6. **The kernel's own Tier 1 and Tier 2 tests pass** (FR-40; BC1), **and a term that an installed package registers
   is found by the command line and the workbench and named in the manifest, with its test** (BC5).
7. **VER-61 and VER-65 hold.** A cycle or a new backend subpackage goes to the author (H6).
8. **Each row the phase owns is `fixed` or ruled** (AM4): REV-279, REV-67 and MOD-10.
9. **Each proposal of the ground-up review is ruled by the author or carried with its owner** (BA13). Met: §8.2.53
   names each.
10. **The wall with a ragged rim recovers its known axis to VER-48's 10⁻⁶ rad** on every perturbed draw, and on the
    three platforms at the close. Today 3 of 8 draws lock 0.22° to 0.62° off (REV-279); prediction: none locks. A
    draw that still locks is investigated, and the tolerance stands. **2WCD's channel axis is measured again**
    against its 0.0073 nm. Prediction: unmoved within VER-48's 10⁻⁴ nm if none of 2WCD's planes holds a split tie,
    which WP6.06's plan measures first. A move, of it or of the farthest centre's 0.0148 nm, amends VER-48 and §5.2's
    NOTE in the fix's commit and goes to the author with the two limits (open decision 11).
11. **The orchestrator's three facts are checked and recorded, and its first two packages, WP6.06 and WP6.07, are
    reported with their sessions, agent hours and touches** (BC10). A fact that fails builds separate sessions; a
    package the orchestrator cannot carry goes back to the three commands, and its report says why.
12. **The guard numbers are stored for PHY-23's terms, the log branch and NUM-14's mode**, after the check that
    VER-62's walks cover the default switches alone (BC3). Prediction: the check confirms it. If a walk already
    covers a switch off its default, WP6.07 stores only what is missing.

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
