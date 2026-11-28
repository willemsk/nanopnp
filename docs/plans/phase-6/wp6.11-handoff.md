# WP6.11 hand-off

## Step

Implement, at the compaction checkpoint: items 1 to 3 are done and ticked; item 4, the forces, is next.

## Done

- `cd0d299` `feat: the switch records, every list of switches derived` (item 1).
- `0dd7ec9` `feat: numerics.log_variables, the log branch's case key` (item 2).
- This commit: `docs: WP6.11 hand-off, implement`, ticking items 2 and 3 and correcting item 1's tick.

## Measured

- `CaseArtefact(VALIDATED_DEFAULT_CASE).hash` on the unedited tree, `9ca84ad`:
  `fddada5f03d5e951e54a95804e19f2006f056412c4b4a7d9ae86d08d9fed071c`; unchanged after items 1 and 2, and pinned in
  `tests/tier1/test_switches.py` as `DEFAULT_CASE_HASH`.
- Item 1's done-criterion files: 172 passed in 14.7 s (`-n auto`). Item 2's: 181 passed, 142 skipped (no browser
  for Playwright here) in 28 s. The commit hook's Tier 1: 1,650 passed in 121 s.
- `tests/tier1/test_model_interface.py`'s `SOLVE_HASHES` and `RUNG_HASHES` hold unchanged.

## Decided

- A conflict's refusal at the case check is one generic message from the record: `<path> is true, but <other> is
  false. <why>. <remedy>`, the remedy from `declared.switches` as before; an exclusion reads `<path> is true, and so
  is <other>`. The model's refusal is `"; ".join(str(conflict))`, `Conflict.__str__` being
  `<switch> <kind> <other>: <why>`. The log record's `why` holds "NUM-02 log branch", which
  `test_physics_models.py` matches.
- The ladder's refusal names the paths of `away(...)` and lists every record's default.
- `dumps_case` writes the full dump, so a written case and the manifest's `case_text` now hold
  `log_variables: false`; only the artefact's parameters and `model_options` drop it (D6). That broke
  `tests/tier1/test_variables.py::test_ver62_a_case_without_variables_writes_what_it_did`, a substring check for
  "variables"; it now asserts the top-level key of the parsed YAML. Not a weakened test: the key is what it guards.
- D10's refusal sits at the head of `pipeline/checks.py:_check_outputs`, after the ladder check, and has no test: a
  refusal that is not a numerical gate (§8.2.13 N1).
- The PHY-23 state test of `test_switches.py` builds `test_kernel.py`'s smooth state on a coarser cylinder
  (`maxh_nm=0.8`).
- Records left for item 6: `CHANGELOG.md` (the new key; `physics.models.SWITCHES` removed; `Term`'s `switches` field
  now a property), Appendix A's FR-40 row (VER-82), and `docs/design/kernel.md`'s switch table, which predates
  `Variable density` under `flow` and the exclusion's move to the log record.

## Open

None.

## Next

Item 4 of `docs/plans/phase-6/wp6.11-switches-as-data-and-the-forces.md`. `post/forces.py`, `physics/flow.py` and
`physics/coupled.py` are unedited, so the tree at `HEAD` is the unedited one for the forces. First action: write the
script its *Implementation details* describe to `"$(git rev-parse --git-dir)/wp6.11/forces.py"` and run it before
any edit of item 4:

```bash
mkdir -p "$(git rev-parse --git-dir)/wp6.11"
uv run python "$(git rev-parse --git-dir)/wp6.11/forces.py" --store "$(git rev-parse --git-dir)/wp6.11/forces.json"
```

The log variant now builds with `CoupledModel(log_variables=True, ...)` and the permittivity model `none`, as the plan
says.
