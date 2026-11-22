# Phase 6 (Cleanup and the library's foundations): a library the workbench and the tools can build on

**Status: in progress. Delivered: WP6.01, WP6.02. WP6.01 to WP6.03 as planned on 22 November 2026; then a rescoping round; WP6.04 to WP6.18 provisional until it rules (§8.2.50). Release: v0.7 (`v0.7.0`).**

## In brief

**What changes.** Three packages are fixed now. The Windows test run is repaired. Then the project's records and
instructions are cut down to a measured reading limit, and the second host is retired. After them comes the open-minded
rescoping you asked for: one round with every requirement, tool and phase on the table, and the content of version 1
with them. Fifteen more packages are drafted and wait for that round, which may
confirm, change or drop them. As drafted they restructure the library in small steps that leave every stored number as
it is, close the known gaps in the flow equations, add field exports and make the solve faster; a project made with
version 0.6 then opens without its finished runs.

**Cost.** The three packages: about 15 sessions, 9 to 18 hours of agent work and 24 times you act. The rescoping round:
about 2 sessions and 3. The fifteen drafted packages, if confirmed: 75 sessions, 45 to 90 hours and 120.

**What could go wrong.** The cleanup could delete a ruling that still binds: you ruled that nothing leaves the
history. The rescoping could be read from stale records: it waits for the cleanup. A drafted package could be started
before the round: none has a plan until the round rules.

**Your call.** Settled on 22 November 2026, with the reading limit and the length of a phase plan inside the cleanup.
Still yours: the rescoping itself. *Recommendation:* bring to the round what you would keep, cut and add, so it
starts from your view and not from the records.

## Context

`SPECIFICATION.md` governs; identifiers here are pointers, and the rulings are §8.2.49 (AY1 to AY8) and §8.2.50 (AZ1
to AZ17; AZ8 ruled at WP6.01's plan, AZ13 and AZ14 at WP6.02's item 5, AZ15 to AZ17 at its review).

Phase 6 answers one question: **can the library be made one sound base, without moving a number, before the workbench
is rebuilt and three tools are built on it?** Its gate is §8.1's. Only WP6.01 to WP6.03 are fixed (AZ7); the
[architecture survey](../../project/architecture-survey.md) shapes the rest.

True of the codebase today:

- **The Windows leg is red.** `ci.yml`'s `platforms` job has not finished on Windows since 10 November.
- **A run's record is an untyped dict.** `pipeline/run.py` `RunResult.write` writes `run.json`; 13 sites parse it raw.
- **A field carries neither its order nor its log branch.** `post/fields.py` `field_at` reads P2 values linearly;
  `gui/render.py` `render_fields` writes the fields file.
- **The shell computes numbers at 12 sites**, among them `gui/render.py` `render_charge_elements`.
- **A switch is code.** `physics/models.py` `SWITCHES` is a closed tuple; `post/forces.py` `_domain_force` assembles
  again the terms of `physics/flow.py`.
- **69 error classes share no base** (`core/errors.py` `classify`).

Risks: none is retired; WP6.13 mitigates **RSK-15** (AY6).

Excluded: §5.4.1's interface, Phase 8's round (AZ1); the workbench's foundations and the suites' words, Phase 7; the
validation runs, Phase 11 (AY6); the structure pipeline's loose ends, Phase 9; a converter for v0.6 runs (AZ5); a
linear-solver swap (Z6).

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Rescoping | `/np-plan project` after WP6.03; `/np-plan amend 6` then plans the rest | It reads cleaned-up records; nothing is built for a scope that may be dropped (AZ7) |
| Order, as drafted | Windows, cleanup, restructure, equations, exports, rewording, speed-up, close | A step that moves no number is reviewed alone (AY3, AY4; AZ4) |
| Field reading | By the cell's own P2 basis, in WP6.07 | v0.7's exports hold the solved field (AZ2) |
| Refusals | The base first; the words after the restructure | No refusal is written twice (AZ3) |
| Old runs | Refused by schema, never converted | AZ5; F4 |
| Speed | No fixed target; thresholds registered in WP6.17's plan | AZ6; M2, Z6 |

## Conventions established by earlier phases

- **A VER-62 miss is reverted, or re-pinned by ruling** (G10); **a moved edge edits `modularity-layering.yaml`**
  (VER-61).
- **A deviation from the validated model is a switch, default off** (`.claude/rules/physics-numerics.md`).
- **The schema and `nanopnp.PUBLIC` may change until v1.0**, each break in `CHANGELOG.md` (F4).
- **A cost is fixed after it is measured** (M2). **An open item is a `REV-nn` row** (H12).

## Work packages

WP6.02 takes `v0.7.0-alpha.2`; the close takes `v0.7.0` alone (§8.4.1). Each is about 5 sessions, 3 to 6 agent hours
and 8 touches (§8.3).

### WP6.01 — The Windows leg (REV-277; AY4)

*Delivered 22 November 2026.* [The plan](wp6.01-the-windows-leg.md). Live: AZ8's ship rule; REV-279 waits for the rescoping round.

### WP6.02 — The cleanup: measure, audit, records (REV-271, REV-272; AY8; AZ9 to AZ17)

*Delivered 22 November 2026.* [The plan](wp6.02-the-cleanup-measure-audit-records.md). Live: AZ13's limit, which binds a session's first window (AZ15), from WP6.03's merge; its Outcome's outdated list.

### WP6.03 — The cleanup: instructions, the Copilot host retired (AY5; REV-166 to REV-168, REV-278)

The audit's changes to the instructions; the host's files and rules removed, findable by the author's tag. Done when a
fresh package session starts under the limit, which then stands in §8.4.4.

### The rescoping round (AZ7)

After WP6.03 merges. Open: every requirement of §3, each tool and phase of §8.1, and v1.0's content (OPN-08). It reads
the cleaned-up records, WP6.02's Outcome, the survey and Phase 5's measured cost, and confirms or reopens AZ1 to AZ6.

### Provisional (AZ4; AZ7)

Each waits on the rescoping round; none is planned before it.

| Package | Scope |
|---|---|
| WP6.04 | One base for every library error, carrying its case path and file |
| WP6.05 | A typed run record with one reader |
| WP6.06 | One catalogue of quantities and units |
| WP6.07 | Fields with their order, read by the cell's own basis, written by the library |
| WP6.08 | The definitions' evaluator on arrays |
| WP6.09 | The results file and its facade |
| WP6.10 | The shell's numbers into the library |
| WP6.11 | `Project` split; stages take their upstream |
| WP6.12 | One registry shape, switches as data, the dead code |
| WP6.13 | The model's open terms, each measured first; forces share the weak form's terms |
| WP6.14 | The tolerances argued |
| WP6.15 | The exports |
| WP6.16 | The refusals reworded |
| WP6.17 | The speed-up |
| WP6.18 | The close: the report and `v0.7.0`; `/np-ship phase 6` ships it |

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| 1 | This round's seven rulings | **Settled by the author, 22 November 2026** (AZ1 to AZ7) |
| 2 | The reading limit; what may leave the history; the baseline's transcripts | **Settled by the author, 22 November 2026**: project text in words, six recent packages, nothing leaves, closed items archived (AZ9 to AZ12). The limit's number and the phase plan's word target: **settled by the author, 22 November 2026**, inside WP6.02 from the baseline: 6,500 words, 2,500 for a phase plan (AZ13, AZ14). At WP6.02's review: the limit binds the first window of an `/np-implement` session (AZ15) |
| 3 | The Copilot tag's name | **Author** confirms at WP6.03's plan (AY5) |
| 4 | Whether a pull request's CI runs the Windows leg | **Settled by the author, 22 November 2026**: no; the three platforms at the close alone (AZ8) |
| 5 | The project's scope, and WP6.04 to WP6.18 with it | **Author**, at the rescoping round (AZ7) |
| 6 | What AM2's "moves one of them" means, and the drift that stops the re-pin | **Author**, at WP6.13's plan, before any measurement |
| 7 | A run above order 2; the speed-up's thresholds; the names after `Project` splits | Their packages' plans |

## What the author supplies

| Item | Needed by | If it does not arrive |
|---|---|---|
| The tag on the last commit that holds the Copilot host | WP6.03 | The session prints the command and the hash |
| What to keep, cut and add | The rescoping round | The round proposes from the records |
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
| WP6.04 to WP6.18 | — | Set by `/np-plan amend 6` |

**The phase is complete when** (§8.1's gate; criteria 2, 3 and 5 are the rescoping round's to confirm):

1. **Tiers 1 and 2 pass on Linux, macOS and Windows**, on the close's own full run. No waiver (AY4); a miss is fixed.
2. **VER-62 is unmoved at 10⁻⁸** by every package but the equations'. Prediction: round-off alone. A miss is reverted
   (G10). The equations package re-pins once, within the bound open decision 6 sets; beyond it the package stops.
3. **VER-61 and VER-65 hold.** A cycle or a new backend subpackage goes to the author (H6).
4. **A fresh package session starts under the reading limit** (`usage.py`). A miss continues the cleanup; the limit is
   re-ruled only before a measurement.
5. **Each cost the speed-up names is measured against its registered threshold**, and each one over it is fixed or
   carried. No factor is predicted (AZ6). **FR-28 has its test.**
6. **Each row the phase owns is `fixed` or ruled** (AM4).

## End-of-phase report

The close fills it. It reports, each with the command or test that logs it:

- the three platforms' Tier 1 and Tier 2 counts and times, from the close's full run;
- VER-62's largest relative drift per walk and platform, and WP6.13's re-pin, old against new;
- the reading baseline and a fresh session's reading against the limit (`usage.py`);
- the tube's solve time, with its assembly, factorisation and residual shares, before and after WP6.17, and each
  threshold with its measured cost (stabilisation mode named);
- the word counts of the records the cleanup cut, before and after;
- the review register's counts by status, and `holds-now.yaml`'s `open:` lines;
- the push gate's and CI's times;
- the phase's measured cost in sessions, agent hours and touches against this plan's estimate.
