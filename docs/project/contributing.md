# Contributing

The full guide is [`CONTRIBUTING.md`](https://github.com/willemsk/nanopnp/blob/main/CONTRIBUTING.md)
in the repository. This page is the short version.

nanopnp is a scientific package, and the one thing it must not do is return a plausible wrong
number. **A finding is worth more than a fix.** If a benchmark disagrees with a known answer, or
the two current-extraction routes disagree with each other, open a *Verification finding* issue.

## Set up and run the gate

```bash
git clone https://github.com/willemsk/nanopnp && cd nanopnp
uv sync --all-extras
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

`uv run pytest` runs tiers 1 and 2, the push gate. The tiers are the four levels of §7: unit and
property tests; analytic benchmarks, with VAL-05's leg on the vendored 2WCD; the COMSOL comparison
and VAL-05's leg on the author's ClyA-AS ensemble, which is the Phase 2 gate (nightly, recorded, not
gated); and experimental reproduction (before a release). VAL-05 compares the geometry pipeline's
pore polygon with the reference one (§7.4 NOTE on VAL-05).

## Build this documentation

```bash
uv sync --all-extras --group docs   # exact: without --all-extras it uninstalls the extras
uv run docs/scripts/generate.py
uv run mkdocs build --strict
```

`generate.py` renders the reference pages from the code, and copies the specification, the knowledge
base and the examples' READMEs verbatim. None of that is committed. The strict build fails on any
broken link or cross-reference, and CI runs it on every push, prose-only ones included. `uv run
mkdocs serve` previews the site locally.

## What a change carries

`SPECIFICATION.md` is normative. Name the identifier a change discharges in the commit, the pull
request, and the test's name. Changing specified behaviour means changing the specification in the
same commit. A tolerance is never loosened to let a number pass. A documented example is executed by
a test, and a number in the documentation must be one a test asserts.

Two guards hold the architecture and the numbers still while Phase 4 refactors (§8.2.7 G1, G10):

- **The layering (VER-61).** `docs/project/modularity-layering.yaml` lists every import edge
  between subpackages, as the [modularity report](modularity.md) records it. A commit that adds or
  removes an edge edits that file in the same commit, naming the `MOD-nn` finding the edge bears
  on. `tests/tier1/test_layering.py` names the module and the line of an edge the file lacks.
- **The number-stability golden (VER-62).** Seven gated walks assert their currents, conductances,
  transport numbers, electro-osmotic flow and deposited charge at 10⁻⁸ relative against
  `tests/tier2/data/number_stability.json`, keyed per platform, with the deployed mesh's hash
  asserted first. A miss is investigated, never re-pinned to pass. Either the change is reverted,
  or it is ruled a deliberate fix: that commit amends the clause the fix changes and re-pins the
  golden, stating the drift. Re-pin by recording with `NANOPNP_RECORD_STABILITY=<dir>` and folding
  the files in with `uv run tests/tier2/data/merge_number_stability.py <dir> --replace`.
