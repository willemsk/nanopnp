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
property tests, analytic benchmarks, the COMSOL comparison (nightly, recorded, not gated), and
experimental reproduction (before a release).

## Build this documentation

```bash
uv sync --group docs
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
