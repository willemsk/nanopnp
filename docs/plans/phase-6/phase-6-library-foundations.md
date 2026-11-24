# Phase 6 (Cleanup and the library's foundations): a library the workbench and the tools can build on

**Status: in progress. Delivered: WP6.01, WP6.02, WP6.03, WP6.04. Amended 23 November 2026 (§8.2.51; §8.2.52): WP6.05, the axis fix, is planned; the rest is provisional until the author rules on the ground-up review (REV-280). Release: v0.7 (`v0.7.0`).**

## In brief

**What changes.** The next package reviews the program from the ground up: how would it be built if we started over
today? It designs for the whole program, built and planned, and takes only the paper's physics as given. It changes no
code. Its report holds the design it would choose, and each difference from today's program marked keep, change now,
change later or drop, with its gain, risk and cost. You then rule on each proposal. Then comes a small fix for the
pore's axis, which rounding can lock 0.6 degrees off at a ragged rim. The rest waits for your rulings: about ten
packages that restructure the library, close the gaps in the flow equations, add exports and speed up the solve.

**Cost.** The review: about 10 sessions, 7 to 13 agent hours and 16 times you act. Your ruling round: 2 sessions and 3.
The axis fix: 4 sessions, 2 to 4 hours and 6. The rest, if the review changes nothing: 50 sessions, 45 to 90 hours
and 80.

**What could go wrong.** The review could reason from the program as it is and find it sound: its plan says how it
guards against that, and a report proposing nothing would show it. It could propose more than one round can rule:
each proposal carries its cost, so you can rank them. The axis fault stays until you have ruled; it is recorded.

**Your call.** Settled on 23 November 2026: your rulings come before the axis fix, and the review designs for the whole
plan. Still yours: the rulings on the review's proposals. *Recommendation:* read the report's table of differences
first.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, and the rulings are §8.2.49 (AY1 to AY8), §8.2.50 (AZ1 to
AZ21), §8.2.51 (BA1 to BA15) and §8.2.52 (BB1 to BB6; BB3 to BB6 ruled at WP6.04's plan). The text each amendment replaced is in
[the record](phase-6-record.md).

Phase 6 answers one question: **can the library be made one sound base, without moving a number, before the workbench
is rebuilt and three tools are built on it?** Its gate is §8.1's. Since the rescoping round it asks a second one first:
**given what the program is now, how would it be built if it were started over?** (BA10) Only WP6.04 and WP6.05 are
firm (BA8, BA11); the [architecture survey](../../project/architecture-survey.md) shapes the rest.

True of the codebase today:

- **A pore's axis found from its channel can lock off the true one.** `structure/cavity.py` `channel_axis` holds a
  second fixed point at a ragged rim, up to about 0.6° off, and rounding decides which one it reaches (REV-279).
  `structure/stage.py` `align` takes that axis only under C1 or `axis: cavity`, and `structure/orient.py`
  `_channel_line` where no covariance axis stands apart; every walk of VER-62 takes the ring's.
- **A run's record is an untyped dict.** `pipeline/run.py` `RunResult.write` writes `run.json`; 13 sites parse it raw.
- **A field carries neither its order nor its log branch.** `post/fields.py` `field_at` reads P2 values linearly;
  `gui/render.py` `render_fields` writes the fields file.
- **The shell computes numbers at 12 sites**, among them `gui/render.py` `render_charge_elements`.
- **A switch is code.** `physics/models.py` `SWITCHES` is a closed tuple; `post/forces.py` `_domain_force` assembles
  again the terms of `physics/flow.py`.
- **69 error classes share no base** (`core/errors.py` `classify`).

Risks: none is retired; the equations package mitigates **RSK-15** (AY6).

Excluded: any change of code, and any trial of a design, in WP6.04 (BA13); §5.4.1's interface, Phase 8's round (AZ1);
the workbench's foundations and the suites' words, Phase 7; the analyte forces, Phase 11, and the validation runs,
Phase 12 (BA5); the structure pipeline's loose ends, Phase 9; a converter for v0.6 runs (AZ5); a linear-solver swap
(Z6); a comparison with the published results (BA3).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| The ground-up review | WP6.04, delivered: a report and no code; everything open but §4's physics | The survey took every constraint as given; after the restructure the answer could no longer shape it (BA10 to BA13) |
| What the review designs for | The whole of §3, what is built and what is planned up to v0.13 | The tools stay before validation, so the design must carry them (BA1; BB2) |
| Order | The review, the author's rulings, a further amendment, the axis fix, then what that amendment plans | A proposal on how an axis is found is ruled before the fix is built (BA11; BB1) |
| Order of the provisional content | The error base, the restructure, the equations, the exports, the rewording, the speed-up, the close | A step that moves no number is reviewed alone (AY3, AY4; AZ4; BA4) |
| Field reading | By the cell's own P2 basis, in the fields package | v0.7's exports hold the solved field (AZ2) |
| Refusals | The base first; the words after the restructure | No refusal is written twice (AZ3) |
| Old runs | Refused by schema, never converted | AZ5; F4 |
| Speed | No fixed target; thresholds registered in the speed-up's plan | AZ6; M2, Z6 |
| Restructuring beyond a plan | Allowed while the push gate passes; never in WP6.04 | BA7, BA13, BA14 |

## Conventions established by earlier phases

- **A VER-62 miss is reverted, or re-pinned by ruling** (G10); **a moved edge edits `modularity-layering.yaml`**
  (VER-61).
- **A deviation from the validated model is a switch, default off** (`.claude/rules/physics-numerics.md`).
- **The schema and `nanopnp.PUBLIC` may change until v1.0**, each break in `CHANGELOG.md` (F4).
- **A cost is fixed after it is measured** (M2). **An open item is a `REV-nn` row** (H12).

## Work packages

WP6.04 takes `v0.7.0-alpha.4` and WP6.05 `v0.7.0-alpha.5`; the close takes `v0.7.0` alone (§8.4.1).

### WP6.01 — The Windows leg (REV-277; AY4)

*Delivered 22 November 2026.* [The plan](wp6.01-the-windows-leg.md). Live: AZ8's ship rule; REV-279 is WP6.05's.

### WP6.02 — The cleanup: measure, audit, records (REV-271, REV-272; AY8; AZ9 to AZ17)

*Delivered 22 November 2026.* [The plan](wp6.02-the-cleanup-measure-audit-records.md). Live: the limit of AZ13 and AZ18, which binds a session's first window (AZ15); its Outcome's outdated list.

### WP6.03 — The cleanup: instructions, the Copilot host retired (AY5; AZ18 to AZ21; REV-166 to REV-168, REV-278)

*Delivered 23 November 2026.* [The plan](wp6.03-the-cleanup-instructions-copilot-host.md). Live: the 8,000 words of AZ18 bind every `/np-implement` session's first window (§8.4.4), measured at 7,186; each plan proposes its two models (AZ20, AZ21); the tag `copilot-host` is pushed (AZ19).

### WP6.04 — The ground-up review (BA10 to BA13; BB2 to BB6)

*Delivered 24 November 2026.* [The plan](wp6.04-the-ground-up-review.md). Live: each verdict of the report is a
proposal until the ruling round (BA11, BA13); REV-280 holds the proposals and REV-281 to REV-287 seven questions
for a trial; AZ1 to AZ6 and BA1 to BA9 hold until the round rules (BA4).

### The ruling round on the review (BA11, BA13)

After WP6.04 merges, at `/np-plan project`, since a proposal may move a requirement or a phase. The author rules each
proposal; a declined one leaves Phase 6 as BA4 has it. `/np-plan amend 6` then confirms WP6.05's entry on the phase as
the round leaves it, and numbers what is left. About 2 sessions and 3 touches.

### WP6.05 — The channel's axis at a ragged rim (REV-279; VER-48; BA8; BB1)

*Firm; planned after the ruling round and its amendment (BB1).* It makes a plane's centre robust to a broken tie at a
ragged rim, and measures 2WCD's channel axis again. From v0.7 a structure with a ragged rim may be given an axis up to
about 0.6° different from v0.6's, the third exception to AY1's rule that Phase 6 changes no number a user sees (BA8);
`CHANGELOG.md` says so. VER-48's gate test tilts the wall with the ragged rim again; the perturbed draws read
`cavity.channel_axis` itself, since the gate's refusal prints 0.01°. The oracle is the axis the test wall is built
about. §5.2's NOTE on stage 1 takes the new method and 2WCD's numbers. No Tier 3 leg. About 4 sessions, 2 to 4 agent
hours and 6 touches. Its plan settles open decision 11.

### Provisional (BA4; BA11)

Each waits on the author's rulings on the review. None is planned or numbered before the amendment that follows them.
The round's input, in order:

| Package | Scope |
|---|---|
| The error base | One base for every library error, carrying its case path and file |
| The run record and the quantity catalogue | A typed run record with one reader; one catalogue of quantities and units |
| The fields | Fields with their order, read by the cell's own basis, written by the library; a package of its own |
| The definitions and the results file | The definitions' evaluator on arrays; the results file and its facade |
| The shell's numbers | The numbers the shell computes, moved into the library |
| The library's shape | `Project` split; stages take their upstream; one registry shape, switches as data; the dead code |
| The model's open terms | Each measured first; forces share the weak form's terms; a package of its own |
| The tolerances and the exports | The tolerances argued; the field and region exports |
| The refusals reworded | The stages' diagnostics and the command line's messages |
| The speed-up | Each cost against a threshold registered first |
| The close | The report and `v0.7.0`; `/np-ship phase 6` ships it |

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | §8.2.50's seven rulings | **Settled by the author, 22 November 2026** (AZ1 to AZ7) |
| 2 | The reading limit; what may leave the history; the baseline's transcripts | **Settled by the author, 22 and 23 November 2026** (AZ9 to AZ12, AZ14, AZ15, AZ18; §8.4.4) |
| 3 | The Copilot tag's name | **Settled by the author, 23 November 2026**: the git tag `copilot-host` (AZ19) |
| 4 | Whether a pull request's CI runs the Windows leg | **Settled by the author, 22 November 2026**: no; the three platforms at the close alone (AZ8) |
| 5 | The project's scope, and Phase 6's packages with it | **Settled by the author, 23 November 2026** (BA1 to BA15) |
| 6 | What AM2's "moves one of them" means, and the drift that stops the re-pin | **Author**, at the equations package's plan, before any measurement |
| 7 | A run above order 2; the speed-up's thresholds; the names after `Project` splits | Their packages' plans |
| 8 | What comes first after the review; what the review designs for | **Settled by the author, 23 November 2026** (BB1, BB2) |
| 9 | How the review guards against reasoning from the program as it is; where its report lives; its two models | **Settled by the author, 23 November 2026**: blind designs from the program's purpose, then rule by rule; the project's pages; Fable 5.2, then Opus 5.5 (BB3 to BB5) |
| 10 | The review's proposals, which may reopen any ruling | **Author**, at `/np-plan project` after WP6.04 (BA13) |
| 11 | What §5.2's two limits become if the fix moves 2WCD's measured axis (REV-239) | **Author**, at WP6.05's plan, before the fix is measured |
| 12 | The provisional packages' numbers and grouping | `/np-plan amend 6`, after the round on the review (BA4) |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| Rulings on the ground-up review's proposals | The round after WP6.04 | WP6.05's plan stays unwritten and the rest provisional (BA11; BB1) |
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
| WP6.05 | 1 | VER-48 |
| The provisional packages | — | Set by the `/np-plan amend 6` after the round |

**The phase is complete when** (§8.1's gate; criteria 2 and 5 rest on provisional packages and stand as BA4 keeps them
until the round on the review rules):

1. **Tiers 1 and 2 pass on Linux, macOS and Windows**, on the close's own full run. No waiver (AY4); a miss is fixed.
2. **VER-62 is unmoved at 10⁻⁸** by every package but the equations'. Prediction: round-off alone; WP6.05 moves none,
   since no walk takes the channel's axis. A miss is reverted (G10). The equations package re-pins once, within the
   bound open decision 6 sets; beyond it the package stops.
3. **VER-61 and VER-65 hold.** A cycle or a new backend subpackage goes to the author (H6).
4. **A fresh package session starts under the reading limit** (`usage.py`). A miss continues the cleanup; the limit is
   re-ruled only before a measurement.
5. **Each cost the speed-up names is measured against its registered threshold**, and each one over it is fixed or
   carried. No factor is predicted (AZ6). **FR-28 has its test.**
6. **Each row the phase owns is `fixed` or ruled** (AM4).
7. **Each proposal of the ground-up review is ruled by the author or carried with its owner** (BA13); the round's
   record names each. The phase does not close on one neither ruled nor carried.
8. **The wall with a ragged rim recovers its known axis to VER-48's 10⁻⁶ rad** on every perturbed draw, and on the three
   platforms at the close. Today 3 of 8 draws lock 0.22° to 0.62° off (REV-279); prediction: none locks. A draw that
   still locks is investigated, and the tolerance stands. **2WCD's channel axis is measured again** against its
   0.0073 nm. Prediction: unmoved within VER-48's 10⁻⁴ nm if none of 2WCD's planes holds a split tie, which WP6.05's
   plan measures first. A move, of it or of the farthest centre's 0.0148 nm, amends VER-48 and §5.2's NOTE in the
   fix's commit and goes to the author with the two limits (open decision 11).

## End-of-phase report

The close fills it. It reports, each with the command or test that logs it:

- the three platforms' Tier 1 and Tier 2 counts and times, from the close's full run;
- VER-62's largest relative drift per walk and platform, and the equations package's re-pin, old against new;
- the reading baseline and a fresh session's reading against the limit (`usage.py`);
- the ground-up review's proposals by ruling: kept, changed now, changed later, dropped;
- the ragged-rim wall's axis over its perturbed draws, and 2WCD's channel axis against 0.0073 nm (WP6.05);
- the tube's solve time, with its assembly, factorisation and residual shares, before and after the speed-up, and each
  threshold with its measured cost (stabilisation mode named);
- the word counts of the records the cleanup cut, before and after;
- the review register's counts by status, and `holds-now.yaml`'s `open:` lines;
- the push gate's and CI's times;
- the phase's measured cost in sessions, agent hours and touches against this plan's estimate.
