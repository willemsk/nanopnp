# Code review: nanopnp user-facing commands

2026-10-10 · commit `997ef37` (`feat/wp42-verification-checks`) · scope: CLI and GUI user-facing entry points (`nanopnp`, `nanopnp-gui`, `nanopnp-probe`; 1.8k lines in `src/nanopnp/cli/`, execution paths across pipeline, mesh, sweep, validate and env) · focus: user-facing command ergonomics, failure modes, exit codes and contracts

## Scope and method

The user-facing surface is three console scripts defined in `pyproject.toml`:

| Script | Entry point |
|---|---|
| `nanopnp` | [`nanopnp.cli:main`](file:///home/willemsk/repos_local/nanopnp/src/nanopnp/cli/__init__.py) |
| `nanopnp-gui` | `nanopnp.gui.app:main` |
| `nanopnp-probe` | `nanopnp.gui.probe:main` |

`nanopnp` subcommands: `run`, `stage`, `inspect`, `reproduce`, `mesh {cylinder,reference}`, `sweep {plan,run,collect}`, `validate {case,export-grid,case-hash,ingest-golden,export-golden,compare,report}`, `env`, plus global options `--version` and `--env`.

The review exercised `--help` on all entry points, executed the quick-start workflow (`examples/01-quickstart`) end to end, exercised negative test paths, and ran parameter sweeps from `examples/03-iv-sweep`. Exit code classification adheres to `core/errors.py`: 0 ok, 1 unexpected, 2 usage, 3 case, 4 gate, 5 convergence, 130 cancelled.

**Not exercised:**
- `validate ingest-golden`, `export-golden`, `compare` and `report` beyond missing-file error paths (require archived reference/golden data);
- `mesh reference`;
- `stage --export` formats other than `.msh`;
- `reproduce` on an intentionally mismatched run, and `--strict-environment`;
- Interactive GUI operation (checked `--help` and invocation flags only).

## Summary

The core command-line workflow is robust, deterministic, and well-structured. Meshing and solving complete rapidly with clear per-stage timings, artefact hashes, and valid route agreements. Run reproduction and caching work as designed, and error messages identify specific invalid leaves or missing pipeline stages without exposing tracebacks by default.

The main findings concern exit code propagation under `--traceback`, validation coverage for referenced input paths, and CLI option validation guards.

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 2 |
| Low | 5 |
| Info | 2 |

## Findings at a glance

| ID | Sev | Category | Location | Finding |
|---|---|---|---|---|
| CR-1 | medium | correctness | `src/nanopnp/cli/__init__.py:1291-1297` | `--traceback` bypasses exception classification and exits 1 instead of domain exit codes |
| CR-2 | medium | correctness | `src/nanopnp/pipeline/checks.py`, `src/nanopnp/cli/__init__.py` | `validate case` reports valid for a case whose input files do not exist |
| CR-3 | low | ergonomics | `src/nanopnp/cli/__init__.py:540-565` | `sweep run` silently ignores `--wave` when `--index` is given, and accepts `--workers 0` |
| CR-4 | low | ergonomics | `src/nanopnp/cli/__init__.py:1240-1285` | Global flags (`-v`, `--traceback`, etc.) rejected before subcommands |
| CR-5 | low | ergonomics | `src/nanopnp/cli/__init__.py` | Internal type name `_positive_nm` leaks into argparse error messages |
| CR-6 | low | ergonomics | `src/nanopnp/cli/__init__.py` | `run` summary displays raw unrounded floats, dict reprs, and signed negative zeros (`-0.0`) |
| CR-7 | low | docs | `docs/guide/running.md` | Multithreading defaults saturate available cores without documentation or `--threads` flag |
| CR-8 | info | design | `src/nanopnp/cli/__init__.py`, `src/nanopnp/io/store.py` | Store root and relative mesh paths resolve relative to CWD rather than case directory |
| CR-9 | info | ergonomics | `src/nanopnp/cli/__init__.py` | `nanopnp` without arguments exits 0; `--env` flag lacks `--json` support |

---

## Detailed findings

### 1. `--traceback` changes the exit code (CR-1, Medium)
- **Location:** `src/nanopnp/cli/__init__.py:1291-1297`
- **Impact:** `nanopnp run nomesh.case.yaml` exits **3** (case error). With `--traceback`, it exits **1** (unexpected error). Because `if args.traceback: raise` re-raises before `classify(error)` runs, Python uncaught exception handling defaults to exit status 1. Automation scripts or SLURM job array wrappers branching on codes 3, 4, or 5 break when debug tracebacks are enabled.
- **Fix:** Format/print the traceback to stderr, then `return classify(error)`.

### 2. `validate case` reports "valid" for missing input paths (CR-2, Medium)
- **Location:** `src/nanopnp/pipeline/checks.py`, `src/nanopnp/cli/__init__.py`
- **Impact:** `nanopnp validate case` asserts case structure and model compatibility but does not verify existence of referenced input files (`inputs.mesh.path`, `inputs.pqr`, etc.). A case with `inputs.mesh.path: missing.msh` passes validation with code 0 ("valid"), but subsequently fails in `nanopnp run` with exit code 3. Conversely, `sweep plan` does check mesh existence.
- **Fix:** Either check referenced file existence in `validate case` (or add a `--check-files` option), or explicitly clarify in command help and documentation that `validate case` verifies document schema and resolution semantics only.

### 3. Conflicting and degenerate sweep options accepted (CR-3, Low)
- **Location:** `src/nanopnp/cli/__init__.py:540-565`
- **Impact:**
  - `sweep run --index 0 --wave 0` runs only index 0, silently ignoring `--wave`. They should be mutually exclusive.
  - `sweep run --workers 0` is accepted without validation rather than rejected as an invalid positive integer.
- **Fix:** Mark `--index` and `--wave` mutually exclusive on the parser, and validate that `workers >= 1`.

### 4. Global flags rejected before subcommand (CR-4, Low)
- **Location:** `src/nanopnp/cli/__init__.py:1240-1285`
- **Impact:** `nanopnp -v env` fails with `unrecognized arguments: -v` (exit 2). Common flags (`-v`, `--traceback`, `--log-file`) are defined solely on child subcommands rather than on the root parser or parent parser.
- **Fix:** Use a shared parent parser inherited by both root and subcommands, or parse known global options at the top level.

### 5. Internal type names leak into argument error messages (CR-5, Low)
- **Location:** `src/nanopnp/cli/__init__.py`
- **Impact:** `mesh cylinder --pore-radius-nm abc` outputs `invalid _positive_nm value: 'abc'`. While negative values produce clean errors (`'-1' is not a positive length in nm`), non-numeric inputs expose the internal helper function name `_positive_nm`.
- **Fix:** Set descriptive `__name__ = "positive float"` or catch `ValueError` to raise `argparse.ArgumentTypeError`.

### 6. Summary block displays raw formatting and negative zero (CR-6, Low)
- **Location:** `src/nanopnp/cli/__init__.py`
- **Impact:** The CLI outputs raw representations such as `stabilisation_currents_A {'Na+': 0.0, 'Cl-': -0.0}` and unrounded floats (`indicator_band_nm [-2.4, 2.400000000000001]`). Full precision is preserved in `run.json`; human-readable console output benefits from rounded notation and normalization of `-0.0`.
- **Fix:** Format dictionary values cleanly and normalize floating negative zero before printing.

### 7. Core saturation without CLI concurrency control (CR-7, Low)
- **Location:** `docs/guide/running.md`, `src/nanopnp/cli/__init__.py`
- **Impact:** A 15 s solve consumes >2m40s of CPU across all available host cores by default via NGSolve/OpenMP. While expected for standalone runs, running under shared nodes or container allocations risks oversubscription.
- **Fix:** Document `OMP_NUM_THREADS` expectations in user guide, and consider adding an explicit `--threads` argument to `run`.

### 8. Working-directory-relative path defaults (CR-8, Info)
- **Location:** `src/nanopnp/cli/__init__.py`, `src/nanopnp/io/store.py`
- **Impact:** The artefact store defaults to `./nanopnp-store`, meaning invocations from different directories create fragmented stores and miss existing cache keys. Relative paths in `inputs.mesh.path` also resolve relative to CWD rather than the case file location.
- **Fix:** Retain documented conventions; ensure warnings or clear paths are printed by `nanopnp env`.

### 9. Subcommand ergonomics (CR-9, Info)
- **Location:** `src/nanopnp/cli/__init__.py`
- **Impact:** Bare `nanopnp` exits 0 after printing help (standard, though exit 2 is sometimes preferred for non-interactive scripting). `--env` flag does not support `--json` output unlike the `env` subcommand.
