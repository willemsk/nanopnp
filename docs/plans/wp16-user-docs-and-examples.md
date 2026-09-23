# WP16 — User documentation and worked examples

**Status: planned, not started.** Written 23 September 2026, after WP15 completed IF-09. The solver
core, the case file, the CLI, sweeps, provenance and the desktop shell are all delivered, but a
user has nothing to read. The README still says the solver is not implemented. There is no
documentation tooling and no `examples/` directory. `nanopnp/__init__.py` exports only
`__version__`, although IF-01 promises a stable API from v0.5. Every checked-in case points at
`docs/sweeps/clya-reference.msh`, which is not in the repository and can be produced only with a
Python one-liner. WP16 inherits the `case_fields` schema walk (WP14), the IF-02 exit-code
enumeration (WP10) and the spawned-process shell (WP14–15).

This package belongs to [Phase 1, solver core](phase-1-solver-core.md) §WP16. `SPECIFICATION.md`
governs, and every identifier below is a pointer into it. Where this plan and the specification
disagree, this plan is wrong. **Spec amendments, made in this commit:**
- §8.1 gains a **documentation track** with a per-phase increment table;
- a **QR-15 NOTE** says QR-15 is delivered incrementally;
- an **IF-01 NOTE** defines the public surface;
- an **IF-02 NOTE** covers generators, together with the `mesh` subcommand;
- **VER-32** is extended, and **VER-45** and **VER-46** are added to §7.2;
- §7.6 gains a docs-build row;
- Appendix A maps QR-15, IF-01 and IF-02.

## Execution brief

### Scope

Three deliverables, in this order.
1. **Two small code seams:** the `nanopnp mesh {cylinder,reference}` subcommand, and a lazy public
   surface on `nanopnp`.
2. **The site:** MkDocs + Material + mkdocstrings, a user guide for all three personas of §2.4,
   generated references, and the specification and knowledge base rendered verbatim as the model
   documentation. It is built strictly in CI and hosted on Read the Docs.
3. **Five worked examples**, each executed by a test.

Discharges QR-15 in part (the documentation half, from v0.5), and touches IF-01, IF-02, IF-03,
FR-23, FR-24, FR-25 and FR-27. **The brief exceeds its 1,200-word target, at about 1,700.** Fourteen
decisions settle what is public, what is executed and what the docs may claim as a number; the
package still verifies inside one PR.

### Requirement and section pointers

| Need | Read |
|---|---|
| Documentation track, QR-15 NOTE | `SPECIFICATION.md` §8.1, §3.3 |
| Public surface, generators | §3.1 IF-01 and IF-02 NOTEs; VER-32, VER-45, VER-46 in §7.2 |
| Case schema and its walk | §5.3.1; `io/case.py` `case_fields`, `field_at`, `options_at`; VER-43 |
| Meshes | §5.2.2; `mesh/primitives.py` `CylindricalPoreGeometry`; `mesh/reference.py` `ReferenceGeometry.from_fixture().generate()`; `mesh/adapter.py` `from_ngsolve`, `write_msh41`; `mesh/ingest.py` vocabulary |
| Fields for a charged example | §5.3.1 `inputs.charge` NOTE; `charge/fields.py` forms `uniform`, `gaussian_ring`, `slab` |
| Tooling status | `.knowledge/07-software-stack.md` §13 |
| Import budget | `.knowledge/07-software-stack.md` §9 and the `io.case` note in §5 |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Generator | `mkdocs<2`, `mkdocs-material`, `mkdocstrings[python]`, with `mkdocs.yml` restricted to what Zensical reads: no `hooks:`, and no plugin without a Zensical shim | Author ruling. Material is in maintenance mode and does not support MkDocs 2; Zensical lacks cross-references (`.knowledge/07` §13). **Migration trigger:** Zensical supports mkdocstrings cross-references |
| D2 | Hosting | Read the Docs, from `.readthedocs.yaml`, installing from `uv.lock` (verify the current RTD uv recipe via Context7). The site banner reads *pre-alpha, v0.5 scope* | Author ruling |
| D3 | Site layout | `docs_dir: docs`, excluding `plans/`. Nav: Home · Getting started · User guide · Examples · Reference · Model · Project | Plans are not user material (CLAUDE.md) |
| D4 | Model pages | A pre-build step copies `SPECIFICATION.md` and `.knowledge/*.md` into a gitignored `docs/_generated/`, rewriting relative links; the strict build proves every link resolves. One orientation page maps each case-file switch to its §4/§6 identifier and **restates no equation** | Author ruling. Restated summaries of this model drift and get copied wrong (CLAUDE.md) |
| D5 | Generated references | Pure renderers in `src/nanopnp/cli/reference.py` build the case-file reference from `case_fields()`, the CLI reference from `build_parser()`, and the exit codes from `cli/errors.py` `EXIT_CODES`. `docs/scripts/generate.py` (run with `uv run`) writes them, with D4's copies, to `docs/_generated/`. Nothing generated is committed | Drift is impossible; generated pages are portable to Zensical (D1); the renderers are testable at Tier 1 (VER-45) |
| D6 | Public surface | `nanopnp.__all__` re-exports lazily through PEP 562 `__getattr__`, with `TYPE_CHECKING` imports for mypy. **Starting set** (the implementation confirms it): `run_case`, `run_document`, `RunResult` (`io.run`); `load_case`, `loads_case`, `dump_case`, `dumps_case`, `resolve`, `CaseDocument` (`io.case`); `Store` (`io.store`); `plan_from_document` (`sweep.plan`); `run_plan` (`sweep.run`); `Stage`, `Progress`, `CancelToken`, `CancelFlag`, `Cancelled`, `StageHook`, `SolveHook` (`core.stages`); `__version__`. mkdocstrings documents exactly this set | IF-01 NOTE. An eager import breaks the ~70 ms CLI budget |
| D7 | `nanopnp mesh` | `cylinder` takes `--pore-radius-nm`, `--membrane-thickness-nm`, `--reservoir-radius-nm`, `--maxh-nm`, `--wall-h-nm` and `--out`, with defaults set to the 392-element mesh of `test_sweep_throughput.py`. `reference` takes `--out` only. Both run the VER-10 gate, write MSH 4.1, and print the mesh hash and the `inputs.mesh.groups` map (JSON under `--json`). Netgen is imported in the handler, and a gate failure writes no file | IF-02 generators NOTE; VER-32. Removes the Python step for P2 and P3 |
| D8 | Executed commands | An example README marks runnable steps with a `console` fence preceded by `<!-- example: run -->`. The VER-46 test copies the example directory to `tmp_path` and runs those lines, verbatim, in a subprocess with `cwd` set to the copy. No shell scripts | The commands shown are the commands tested, and the Windows leg can run them. Case paths resolve against the CWD (`docs/sweeps/README.md`), so every README says to run from its own directory |
| D9 | Oracles | Only the model-property oracles of VER-46. **No number appears in prose as a result unless an example asserts it** | Assert, don't hope; a transcribed number is a plausible wrong answer once the code moves |
| D10 | Examples | See the table below; each README states its persona, runtime, oracle and the identifiers it exercises | Author ruling: all four sets |
| D11 | Tiers and budget | 01–04 go in `tests/tier2/test_examples.py`, with a **≤ 2 min serial** target, measured and recorded as an Outcome. 05's solve is `slow`, while its `sweep plan --no-mesh-check` and its SLURM template's rendering run at Tier 1 | The push gate stays at minutes |
| D12 | Dependencies | `[dependency-groups] docs = ["mkdocs>=1.6,<2", "mkdocs-material", "mkdocstrings[python]"]`, not a default group. `[project.optional-dependencies] examples = ["matplotlib"]`. Then `uv lock`. Examples always write CSV and plot only when `matplotlib` imports | CON-07: nothing new on the end-user path. CI's `--all-extras` exercises the plots |
| D13 | CI and prose rule | A new `docs` job in `ci.yml` (`uv sync --group docs`, generate, `mkdocs build --strict`) runs on **every** push, including prose-only ones. `.github/scripts/prose-only.sh` treats `examples/*` as non-prose, and `.claude/hooks/gate.sh` inherits that | The tests read the example READMEs (VER-46), and the strict build (VER-45) must see prose edits |
| D14 | GUI guide | `docs/scripts/capture_gui.py` grabs the editor, run and convergence panels under `QT_QPA_PLATFORM=offscreen` into `docs/guide/img/`; the PNGs are committed and no test looks at pixels. The WebEngine viewer is described in text. The guide says v0.5 GUI use is the development install (`uv run nanopnp-gui`) until §8.2 criterion 4's double-click and the post-1.0 installers exist | Author ruling; honest about criterion 4 and RSK-13 |

**Examples** (`examples/NN-slug/`: `README.md`, cases, sweeps, optional `.py`):

| Example | Persona | Content | Oracle (VER-46) |
|---|---|---|---|
| `01-quickstart` | P2 | `nanopnp mesh cylinder` → `run` → `inspect` → `reproduce`, on an uncharged pore | exit 0; `reproduce` passes (QR-08); FR-23 routes agree |
| `02-charged-pore` | P2 | A `field1` header over `slab` or `gaussian_ring` with a declared `Q_net`; ePNP-NS against every correction `none` | cation transport number > ½; the classical manifest lists each `none` under deviations (FR-25) |
| `03-iv-sweep` | P2 | Charge on one side only, a small ± bias sweep, `sweep plan` / `run --workers 2 --csv` / `collect`, `plot_iv.py` | uncharged control rectifies to 1 within solver tolerance; the charged pore's CSV is complete and every member exits 0 |
| `04-python-api` | P1 | `tour.py`: mesh through the API, `loads_case`, `run_case(upto=…)`, inspect and substitute an artefact (FR-27), read the IF-07 XDMF, plot | substituted input moves the downstream hash; field names match IF-07 |
| `05-clya-reference` | P1/P2 | `nanopnp mesh reference`; one frozen case from `docs/validation/cases/`; a SLURM job-array template over `sweep plan`'s wave ranges for `docs/sweeps/phase1-reference.sweep.yaml` | `slow`: the solve exits 0 and the FR-23 routes agree. Tier 1: the plan enumerates 3,675 points in 42 waves |

### Work items

1. `cli/__init__.py`: the `mesh` subparser and its handler; `--help` must not import netgen.
2. `src/nanopnp/__init__.py`: lazy `__getattr__`, `__all__` and `__dir__` (D6).
3. `src/nanopnp/cli/reference.py`: the three renderers (D5).
4. `pyproject.toml` (D12), then `uv lock`; `mkdocs.yml`; `docs/scripts/generate.py`; `.gitignore` gets `docs/_generated/` and `site/`; `.readthedocs.yaml`; the `ci.yml` `docs` job; `prose-only.sh` (D13).
5. Pages: `docs/index.md`, `getting-started.md`, `guide/` (concepts: case → stages → artefacts → store → manifest; case files; meshes and group mapping; fields; running and exit codes; sweeps and HPC; outputs and QoIs; provenance and deviations; stabilisation modes; desktop shell), `reference/` (stubs over `_generated`, API, correction data files), `model/index.md` (D4), and `project/` (contributing, citing, the licence including the CON-11 bundle note).
6. `examples/01`–`05` and `tests/tier2/test_examples.py`, plus the Tier-1 parts in `tests/tier1/test_examples_plan.py`.
7. `docs/scripts/capture_gui.py` and the images (D14).
8. `README.md`: a truthful status, a link to the site, and example 01 as the quick start. `CONTRIBUTING.md` and the CLAUDE.md commands table: the docs build.

### Verification

| Test | Tier | Identifiers | Assertion |
|---|---|---|---|
| `tests/tier1/test_cli.py` (extend) | 1 | VER-32, IF-02 | `mesh cylinder` output ingests through the VER-27 gate with the printed groups; the printed hash equals the ingested mesh hash; a gate failure exits 4 and leaves no file; `--help` imports no netgen |
| `tests/tier1/test_public_api.py` | 1 | VER-45, IF-01 | `__all__` equals the documented set, both directions; each name is its module's object; a fresh `import nanopnp` leaves `ngsolve`, `netgen` and `numpy` out of `sys.modules` |
| `tests/tier1/test_doc_reference.py` | 1 | VER-45, IF-02, IF-03 | The case reference covers exactly the `case_fields()` paths, both directions; the CLI reference covers every subparser; the exit table equals `EXIT_CODES` |
| `tests/tier1/test_examples_plan.py` | 1 | VER-46, FR-24 | Example 05's `sweep plan --no-mesh-check` enumerates 3,675 points in 42 waves; every example README has at least one tagged block |
| `tests/tier2/test_examples.py` | 2 (05: `slow`) | VER-46, FR-23, FR-25, QR-08 | The per-example oracles in the table above |
| CI `docs` job | — | VER-45, §7.6 | `mkdocs build --strict` exits 0 |

Commands: the full gate (`.claude/hooks/gate.sh run`);
`uv sync --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`; and
`uv run pytest tests/tier2/test_examples.py -v --durations=0` for the D11 budget.

### Out of scope

- The JOSS paper, the DOI release and a PyPI publish: Phase 4 (QR-15).
- In-app tutorials and installers: post-1.0.
- Generating a mesh from the GUI: the Phase 2 GUI increment.
- A changelog.
- The Zensical migration: D1's trigger.
- **A correction file for a new electrolyte.** It would invent fitted parameters. The guide documents the schema against `willems2020_nacl` only.

### Open questions

Neither blocks implementation.
1. **The author creates the RTD project** and connects the repository. The slug defaults to `nanopnp`.
2. The Windows bundle exposes no `nanopnp mesh`. It stays a Phase 2 GUI item unless the author
   rules otherwise.

## Design

### Why the examples assert properties, not numbers

A worked example that prints "I = 1.23 nA" invites the reader to treat that number as validated,
and it goes stale silently the first time a default moves. Every VER-46 oracle is a property the
model must have whatever the mesh:
- **Symmetric uncharged pore, rectification 1.** The problem is invariant under `z → −z` with the
  bias reversed. The bias-reversed current is therefore `I(−V) = −I(V)`, so `|I(+V)/I(−V)| = 1`, up
  to the solver tolerance and the mesh asymmetry. The generator's mesh is mirror-symmetric only if
  its geometry is centred; the implementation asserts that, or sets the tolerance from the measured
  mesh asymmetry and records it.
- **Counter-ion selectivity.** A negative fixed charge enriches cations in the double layer, so the
  cation transport number `t₊ > t₋`. With `t₊ + t₋ = 1`, that means `t₊ > ½`.
- **Deviations.** These are recorded by the WP7 diff against the validated default, which the
  classical configuration departs from on every correction (PHY-21).

Each of these fails loudly on a sign error and says nothing false when a default changes.
