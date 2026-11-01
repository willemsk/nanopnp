# Code review 023: WP58, documentation increment 4

Reviewed: PR 146, base `4df8d2108683274b8acb4a7b9be1370d08aa0e34`, head `ec51b447adaf275b06c08e5c255a3f8ea4b124b8`.
Level: xhigh. Status: completed. The diff is prose and navigation only (no `src/`, `tests/`, `data/`, case file or mesh).

Every claim of `docs/guide/python.md`, `notebooks.md`, `outputs.md`, `running.md` and `getting-started.md` was checked
against `src/` (hook signatures, `Session` options, `Case` constructors, `RunResult` properties, the `plot`, `env` and
`--progress` flags, the extras in `pyproject.toml`, the public-name count, the stage list and which stages have figures).
All held.

## Findings

1. **Stale path rule in `docs/sweeps/README.md`** (documentation). The page said `inputs.mesh.path` resolves against
   the process working directory because the sweep runner never changes directory. `sweep plan` resolves each member
   beside the base case file (`src/nanopnp/sweep/plan.py`, `beside=base_path.parent`), the rule WP58 corrected
   everywhere else. Fixed: the sentence now states the rule and points to REV-169.
2. **REV-169 undercounts its cases** (documentation). The five `docs/validation/cases/clya-*.case.yaml` files carry the
   same mesh path and the same header comment as `phase1-reference.case.yaml`, and `docs/scripts/capture_gui.py:56`
   states the same stale rule. Fixed: the REV-169 section lists them. The case files stay untouched (D1).
3. **Run-on line in `docs/guide/python.md`** (simplification). One sentence of the Sweep section ran to 150
   characters beside a wrapped paragraph. Fixed: rewrapped.

No finding concerns correctness of a snippet, a command or a number.
