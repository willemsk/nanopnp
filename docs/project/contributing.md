# Contributing

The full guide is [`CONTRIBUTING.md`](https://github.com/willemsk/nanopnp/blob/main/CONTRIBUTING.md)
in the repository. This page is the short version.

nanopnp is a scientific package, and the one thing it must not do is return a plausible wrong
number. **A finding is worth more than a fix.** If a benchmark disagrees with a known answer, or
the two current-extraction routes disagree with each other, open a *Verification finding* issue.

## Set up, the gate, the documentation and what a change carries

[`CONTRIBUTING.md`](https://github.com/willemsk/nanopnp/blob/main/CONTRIBUTING.md) holds the set-up,
the push gate (`.claude/hooks/gate.sh run`), the documentation build and what a change carries. In
short: `SPECIFICATION.md` is normative, a change names the identifier it discharges, and a tolerance
is never loosened to let a number pass.

## The two guards

The layering and the numbers are held by two guards (§8.2.7 G1, G10):

- **The layering (VER-61).** `docs/project/modularity-layering.yaml` lists every import edge
  between subpackages, as the [modularity report](modularity.md) records it. A commit that adds or
  removes an edge edits that file in the same commit, naming the `MOD-nn` finding the edge bears
  on. `tests/tier1/test_layering.py` names the module and the line of an edge the file lacks.
- **The number-stability golden (VER-62).** Seven gated walks assert their currents, conductances,
  transport numbers, electro-osmotic flow and deposited charge against
  `tests/tier2/data/number_stability.json`, keyed by the deployed mesh's content hash. On a mesh
  the golden holds they hold 10⁻⁸ relative. On a mesh it does not hold they hold the walk's
  mesh-moved tolerance, derived from the spread between its recorded meshes and capped at 10⁻³,
  except on the reference environment (`linux-x86_64/X86_V3`, which CI and the commit gate pin
  with `NPY_DISABLE_CPU_FEATURES`), where an unseen mesh fails. A miss is investigated, never
  re-pinned to pass. Either the change is reverted, or it is ruled a deliberate fix: that commit
  amends the clause the fix changes and re-pins the golden, stating the drift. Re-pin by recording
  with `NANOPNP_RECORD_STABILITY=<dir>` and folding the files in with
  `uv run tests/tier2/data/merge_number_stability.py <dir> --replace`. A leg that deploys a new
  mesh prints a record; folding it in with `--entry` widens that walk's tolerance, so it is a
  reviewed change, stated in the PR.
