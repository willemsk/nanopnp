# Code review 102: the chore that makes the slow tests opt-in by --slow

2026-11-27 · branch `ccr-a5409d84-cca31n`, head `05a4211` on base `f562214` · scope: two commits, 12 files, +75 and
−41, read from `git diff f562214...05a4211`, against the chore's statement (no plan), §7.6, §8.4.4, §8.2.56 BF11,
§8.2.36 AL17, review 101, `gate.sh`, `ci.yml`, the `tier12` action, the `justfile` and the tier conftests ·
reviewer: `np-reviewer`, Opus 5.5 at high effort, with four hunt findings · status: completed.

Probes: one default `--collect-only` (1978/2098, as the statement says, no warning); `--collect-only` of five named
`slow` files serially; `pytest tests/tier2/test_sweep_throughput.py -n 2 -q` before and after the fix; xdist's
`plugin.py` and `remote.py` for what a worker's output and warnings reach. No other suite run. Line numbers are the
reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `tests/conftest.py:118-122` | Axis 1, hunt finding 4's fix. The line on a named file's deselected `slow` tests goes through the worker's `terminalreporter`, whose output never reaches the console under `-n`, the parallel run CLAUDE.md, the gate and CI use: `-n 2` on a named `slow` file printed only "no tests ran". Confirmed | Fixed: a `PytestWarning`, which xdist forwards; shown serially and under `-n 2` |
| 2 | Medium | `.claude/workflow/helper.md:33-35` | Axis 1, a workflow change the statement does not say. "Nor one with `--slow` or `--nightly`" forbids the table's own `RUN` row (line 12): `pytest --nightly`, and "a `slow` test the plan names", which now runs only under `--slow`. It brings back review 101's finding 1. Confirmed | Fixed: the ban stays on a marker selection and the carried tests; a `RUN` names its tests by file or node id, with `--slow` for a `slow` one |
| 3 | Low | `.github/workflows/ci.yml:450` | Axis 2, §7.6's Nightly and release rows ("3"). `-m tier3` replaced `addopts` and so selected a `slow` Tier 3 test; the new conftest drops it silently. No Tier 3 test carries `slow` today, so the selection is unchanged. Doubt | Fixed: the job passes `--slow` |
| 4 | Low | `CLAUDE.md:37`, `CONTRIBUTING.md:33`, `.claude/skills/steward/SKILL.md:98` | Axis 1. "`--slow` adds the `slow` tests, whatever `-m` says" reads as the flag overriding `-m`, which it does not: `--slow -m tier1` adds no Tier 2 `slow` test. Confirmed | Fixed in `CONTRIBUTING.md` and the steward skill ("which no `-m` selects without it"). Left to the author for `CLAUDE.md`, which a reviewer does not edit on a delegated instruction: write "Adds the `nightly` walks / the `slow` tests, which no `-m` selects without the flag" |
| 5 | Low | `knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md:52-55` | Axis 1, §8.2.36 AL17. The paragraph restates §7.6's rule without citing it, and says `-m tier2` "times what the gate runs", whose Tier 1 it leaves out. Confirmed | Fixed: it cites §7.6 and says the Tier 2 part |

The pass fixed findings 1 to 5 in `3edf111`, but `CLAUDE.md`'s line of finding 4, which is left to the author.

The hunt's findings, each fixed in `05a4211`:

| Hunt | Outcome |
|---|---|
| 1. `CONTRIBUTING.md:33` taught the old selection | Fixed in `05a4211`; its wording is finding 4 |
| 2. `helper.md`, the steward skill and knowledge note 03 named the old selection | Fixed in `05a4211`; the `helper.md` edit opened finding 2, fixed in `3edf111` |
| 3. Note 12's untraced timing claim | Fixed in `05a4211`: no timing remains; finding 5 completes the citation |
| 4. A named `slow` test was deselected silently | Fixed in `05a4211` serially only; finding 1 completes it under `-n` |

## Checked and found true

- **Every route selects what it did.** `gate.sh`'s commit mode (`-m "tier1 and not slow"`), push mode (the
  `addopts` selection) and prose-only mode (`-m records`); `ci.yml`'s two shards (`-m "$SHARD and not slow"`) and
  the nightly Tier 1 job on 3.11 to 3.13; the `tier12` action's two calls (`--slow -m "(tier1 or tier2) and slow"`,
  which keeps every `slow` test, those marked `nightly` too, and then `--nightly`, which now drops the `slow` ones
  as `and not slow` did); the `justfile`'s `test` and `test-parallel`. The `and not slow` left in place is
  redundant and harmless.
- **The hook.** It is `trylast`, so it sees what `-m` kept; the rule that a `slow` test is `--slow`'s alone and a
  named file exempts only a `nightly` one matches §7.6's new sentence and the statement. `LONG_MARKERS`' timeout
  is applied after the deselection, to the kept items, as before.
- **The specification.** §7.6's NOTE and its Nightly and release rows change in the same commit as the behaviour;
  no ruling moves. No permission line is added.
- **History.** `docs/project/decisions-closed.md` WP50 D3 and WP29 D14 name `-m slow` as dated register rows and
  stay.

## Not assessed

- The CI jobs themselves; the action's change is read, not run.
- Under `-n`, each worker emits the warning once, so the summary lists it once per worker.
