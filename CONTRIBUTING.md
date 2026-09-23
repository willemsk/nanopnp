# Contributing to nanopnp

Thank you for looking. `nanopnp` is pre-alpha and single-maintainer, and it is a *scientific*
package: the thing it must not do is return a plausible wrong number. Most of what follows exists to
make that failure mode hard, and it applies to a one-line fix as much as to a new solver stage.

By contributing you agree that your contribution is licensed under the BSD-3-Clause terms in
[`LICENSE`](LICENSE).

## Before you write code

- **Open an issue first** for anything that touches physics, numerics, the specification, or the
  shape of a public interface. The design is written down before it is implemented (see
  `docs/plans/`), and a PR that arrives ahead of that conversation is likely to be asking for a
  decision that has already been taken and recorded.
- **Go straight to a PR** for the small and self-evident: a typo, a docstring, a type annotation, a
  packaging or CI fix, a test that covers an existing requirement more tightly.

Two issue forms are provided. Use **Verification finding** when the software disagrees with a *known
answer* — an analytic benchmark outside tolerance, two extraction routes that do not agree, a
convergence rate that fell. Use **Bug report** for crashes, hangs and results that cannot be
reproduced. A verification finding is the more valuable of the two: it is evidence, and it is worth
more than a green test suite.

## Setting up

[`uv`](https://docs.astral.sh/uv/) owns the environment. There is no `pip`, no manual `activate`,
and no bare `python`.

```bash
uv sync --all-extras     # create or refresh .venv from uv.lock
uv run pytest            # tiers 1 and 2 — the default selection
```

A VS Code Dev Container and a GitHub Codespace configuration are in [`.devcontainer/`](.devcontainer)
if you would rather not install anything locally.

## The gate

Everything must pass before a commit:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

CI runs the same four stages on Python 3.12, plus the test suite on 3.10–3.14 on Linux and on 3.12
on Windows and macOS, and the strict documentation build on every push, prose-only ones included. `uv.lock` is committed and CI resolves nothing: if you edit `pyproject.toml`,
run `uv lock` in the same commit.

## The documentation

The site is MkDocs with Material and mkdocstrings. Build it as CI does:

```bash
uv sync --all-extras --group docs   # exact: without --all-extras it uninstalls the extras
uv run docs/scripts/generate.py     # the generated references and verbatim model pages
uv run mkdocs build --strict        # fails on any broken link or cross-reference
```

The case-file, command-line, exit-code and API references are rendered from the code, and the
specification and the knowledge base are copied in verbatim. None of it is committed; do not edit
it by hand. A worked example's tagged commands are executed by a test, word for word, and no number
may appear in the documentation as a result unless an example asserts it (VER-46).

## What a change has to carry

`SPECIFICATION.md` is normative. Requirements (`FR-`, `QR-`, `CON-`), physics (`PHY-`), numerics
(`NUM-`) and verification (`VER-`, `VAL-`) are identified there, and:

- **Name the identifier your change discharges** — in the commit body, in the PR, and in the test
  name (`test_ver03_ion_wall_function_check_values`). Appendix A traceability is then mechanical.
- **Changing specified behaviour means changing the specification in the same commit**, with the
  argument, not diverging from it quietly.
- **A tolerance is never slackened to accommodate a number.** Either the number is wrong, or the
  specified reference was the wrong quantity — and if it is the latter, say so in those terms. §7.3's
  Henry-versus-Smoluchowski amendment is the worked precedent, and it took a derivation.
- **No test is skipped, `xfail`ed or deleted to make a PR pass.** A failing analytic benchmark
  localises an error to a single term; that is the whole point of it.
- **Deviations from the validated model go behind a flag, default off**, and are recorded in the
  provenance manifest (FR-25). The published agreement with experiment was obtained with a specific
  set of terms.

Tests live in `tests/tier{1,2,3,4}/`; the directory decides the tier marker. Tiers 1 and 2 gate every
push. Tests must not reach the network and must not need a COMSOL licence.

## Physics

Read [`.knowledge/00-index.md`](.knowledge/00-index.md) before changing anything physical. It is the
normative reference for the model and documents five errata in the published sources, with the
arithmetic.

**Do not source the model equations, the correction functions or their parameters from the web.**
Several widely-copied summaries of this framework are wrong, and where the printed sources, author
recollection and the COMSOL model report disagree, the model report governs.

Fitted parameters are data, not code: they live in `data/corrections/*.yaml`, and adding an
electrolyte should never require touching solver code.

## Constraints a PR will be rejected for

- `gmsh` on the default import path (GPLv2+, optional backend only — CON-10), or any dependency on
  Triangle, MeshPy or TetGen (CON-12).
- PyQt anywhere; the GUI is PySide6 (CON-09).
- Anything on the end-user path that needs a C++ compiler, a source build or a JIT toolchain
  (CON-07). This constraint is why NGSolve was chosen over DOLFINx.
- Correction coefficients, `ε_protein`, or any fitted parameter hard-coded in Python.
- COMSOL import or export, transient solves, 3D, or off-axis analytes — out of scope for v1 (§3.5),
  though the architecture must not preclude them.
- `import *`, `print()` outside the CLI's own output, or `os.path`.

## Style

`from __future__ import annotations` at the top of every module; type hints on every signature
(`mypy --strict` runs over `src/`); NumPy-style docstrings; SI internally with units in the name at
the boundary (`radius_nm`, `bias_V`); British spelling in prose and identifiers, matching the
specification; `pathlib`, f-strings, `logging`; pydantic models at every serialisation boundary. Cite
the source of every physical constant and fit coefficient in a comment.

Commits are conventional — `feat:`, `fix:`, `test:`, `docs:`, `chore:` — with the requirement
identifier in the body.

[`CLAUDE.md`](CLAUDE.md) carries the same conventions in the form coding agents read, and is the
faster orientation if you are about to make a substantial change.

## Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
