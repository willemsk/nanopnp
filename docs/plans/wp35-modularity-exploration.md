# WP35 — The modularity exploration: report, findings log, guard and golden

**Status: delivered, 5 October 2026.** Written 5 October 2026, on `main` at `e63a32e`, after Phase 3
closed as `v0.4.0`. WP35 inherits everything the [current brief](current.md) lists as not to be
re-decided. In particular it inherits:

- the stage registry of `core/stages.py`, with `register`, `create` and the VER-25 introspection
  rule;
- the walk of `io/run.py`;
- the VER-56 source walk of `tests/tier1/test_model_interface.py`, whose detector self-test is the
  pattern for VER-61's;
- the §7.6 NOTE's four levers (WP33). VER-62 attaches to existing walks by sharing their work.

This is the first work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md).
`SPECIFICATION.md` governs, and the identifiers below are pointers into it. The author's rulings
behind it are §8.2.6 F3 and §8.2.7 G1, G4 and G10, and they are not re-argued here. **No spec
amendment** is made in this commit. VER-61, VER-62 and VER-63 are claimed, with their rows in
§7.2 and §7.3, by `/wp-implement`, in the commit that implements them. **One correction to the
phase plan, made in this commit:** example 05's solve is `slow` (recorded, not gated), so it cannot
feed a gated golden. VER-62's walks are the gated ones listed in D11.

## Execution brief

### Scope

WP35 measures the architecture against FR-27, FR-16, FR-20, QR-13 and QR-14, and against ADR-002
and ADR-005. It reports what it finds as numbered findings and **changes no behaviour** (G1). It
delivers five things:

- **a measurement module**, `validation/modularity.py`, whose output the report's numbers cite;
- **the report**, `docs/project/modularity.md`, with its findings log
  `docs/project/modularity-findings.md` (`MOD-nn`, header `open`);
- **VER-61**, a Tier-1 guard that pins the subpackage import relation the report records;
- **VER-62**, a number-stability golden recorded on a tree that is computationally `v0.4.0`, and
  asserted at 10⁻⁸ relative inside the gated walks that already compute those numbers;
- **VER-63**, a Tier-1 check of every findings log under `docs/`.

The package ends when the PR merges. The author then rules each `MOD-nn` through
`/phase-plan amend 4`.

### Pointers

| Need | Read |
|---|---|
| What is measured | §5.1, §5.4.1–§5.5, ADR-002, ADR-005; FR-16, FR-20, FR-27, QR-13, QR-14, IF-01 |
| The stage protocol and the walk | `core/stages.py` `Stage` (303), `register` (357), `_register_builtins` (466); `io/run.py` `PIPELINE`, `PAYLOAD_FREE`, `STRUCTURE_STAGES`, `WORKSPACE_STAGES`, `STORE_STAGES`, `selected_stages` |
| The AST patterns | `tests/tier1/test_model_interface.py` `model_dispatch` and its self-test; `tests/tier1/test_gui_probe.py` `_runtime_imports` |
| The golden's walks | `tests/tier2/test_examples_0{1,2,3,7}_*.py` (`ran`-style module fixtures); `tests/tier2/test_pipeline_2wcd.py:153`; `tests/tier2/test_exclusion_2wcd_walk.py:83` |
| The golden's platform rule | `.knowledge/07` §5 (netgen meshes are not bit-reproducible across platforms) and `.knowledge/06` §8.1 |
| Prose-only | `.github/scripts/prose-only.sh`; `tests/tier1/test_workflow_hooks.py` |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Where the measurements live | `src/nanopnp/validation/modularity.py`, standard library only (`ast`, `pathlib`) plus the YAML reader the package already uses. `docs/scripts/generate.py` renders its output to `docs/_generated/project/modularity-measurements.md`. There is no new CLI subcommand | One walker serves the guard, the report and the generator, so they cannot drift. It is under `mypy --strict`. No test imports `docs/scripts/`. Generated pages are built, never committed (VER-45) |
| D2 | How the code is read | By AST only. No measurement imports an implementation module, and stage conformance reads each registry target's class from its source | It runs in the docs job without extras, and the import-cost rule is not exercised by measuring it |
| D3 | The nodes of the relation | The 16 subpackages, plus `nanopnp` for `__init__.py` | The survey: there is no other top-level module |
| D4 | An edge's kinds | `top` is module scope outside `TYPE_CHECKING`, `deferred` is inside a function, and `typing` is inside `if TYPE_CHECKING:`. `string` is a non-docstring constant naming an existing `nanopnp` module, `module` or `module:attr`, which catches the stage registry, `PUBLIC`, `import_module` in `mesh/generate.py`, and the class names of `cli/errors.py` | [Design §1](#1-the-import-relation). A deferral or an annotation still couples two layers, and breaking a cycle by moving an import into a function hides it |
| D5 | What VER-61 pins | Two relations, each in both directions. One is the **static** relation, the union of `top`, `deferred` and `typing`. The other is the **string** relation. Kinds are reported and not pinned. The module-level graph of `top` edges is also asserted acyclic | A refactor that moves an import between scopes is not a layering change. VER-25 and VER-45 already gate the import cost |
| D6 | The accepted relation | `docs/project/modularity-layering.yaml` holds one entry per subpackage edge, `{from, to, relation, finding}`, where `finding` is a `MOD-nn` or `null`. At WP35 it records the status quo. A failure names the edge, the first module and the line that make it, and the file to edit | It is data, not code. It is YAML, so it is not prose. The report renders it, and later packages shrink it in the commit that removes an edge (Phase 4 plan) |
| D7 | The report's numbers | Each finding quotes its numbers "at `<commit>`" and names the `modularity.py` function that measures them. The live numbers are the generated page. VER-61 asserts that the YAML equals the live relation, so the matrix the report renders is a tested number | G1: a number that cannot be rerun is an adjective. A dated finding stays true after a refactor changes the live page |
| D8 | What the module measures | (a) The import relation, its strongly connected components (SCCs) for `top`, for runtime (`top` ∪ `deferred`), static, and static ∪ `string`, with the edges that close each cycle. (b) Stage conformance: per registered target, whether `key`, `describe` and `run` are defined and how `run` is signed, and the stage sets hard-coded in `io/run.py`. (c) Extension points: each registry (stages, corrections, physics models, stabilisation, charge forms) and each branch (mesher, linear solver, the `OUTPUTS` and `STERIC_MODELS` enumerations, `materials/forms.FORMS`), with its home, its members, and the modules outside its home that spell a member as a literal. `none` is excluded, because every switch takes it. (d) QR-13: the modules importing `ngsolve` or `netgen`, per subpackage, and whether the §5.4.1 interface exists. (e) Surface: `PUBLIC`, its hand-kept `TYPE_CHECKING` mirror, `with_section` and `core.stages.register`. (f) Size: lines per module and the longest functions. (g) Version literals (`v0.N`) in non-docstring strings | Phase 4 plan, WP35's four areas; G1's three named measurements. (c)'s literal count is the measurable form of "requires only one class or one file" (QR-14) |
| D9 | A finding's form | A `### MOD-nn — <title>` section in the report, with fields *Measured* (number, commit, function), *Consequence*, *Recommendation* and *User-visible*. The recommendation is one of: fix in Phase 4, defer to Phase 5, defer to Phase 6, post-1.0, or amend the specification. *User-visible* is no, or names what breaks (API, CLI or schema; F4, G6). Severity is **high** for a SHALL the code does not meet, **medium** for a property held only by convention or an extension needing an edit outside its home, and **low** for size or tidiness | Phase 4 plan, WP35. The severities make the log's column a definition and not a mood |
| D10 | The seed findings | [Design §4](#4-seed-findings) lists 14 measured candidates. The implementer may merge, split or add, but may not drop one without saying why in an Outcome | The phase predicts 10–25. Listing them now keeps the scope a decision, not a discovery |
| D11 | VER-62's walks | Seven walks, which are every gated walk that computes a current: example 01; example 02's two cases; example 03's charged sweep; example 07; the 2WCD charged walk (`test_pipeline_2wcd.py:153`); and the 2WCD walk with the shell and derived `χ` (`test_exclusion_2wcd_walk.py:83`). Example 05 is `slow` and is not included | Correction to the phase plan. Between them the walks cover corrections on and off, the sweep runner, protonation, deposition, and WP30's switches. Each adds no solve |
| D12 | VER-62's quantities | Per walk, every scalar of `current_A`, `currents_A[*]`, `conductance_S`, `transport_number` and `eof_m3_s` that the walk produces, plus, for the two charged 2WCD walks, `q_mesh_e`. A difference or an error estimate (`route_agreement`) and a quantity recorded as zero are refused at recording. Each value is read from a JSON record, or from a CSV that round-trips `float64`, checked at recording | [Design §2](#2-the-golden-tolerance-and-keying). Relative drift of a difference amplifies round-off by the inverse of its size |
| D13 | VER-62's keying and file (amended after review) | `tests/tier2/data/number_stability.json`, schema `nanopnp/golden/stability/v2`, read and compared by `nanopnp.validation.stability`. Each walk holds its recorded meshes by content hash, each with its values and the environments (`<sys.platform>-<machine>/<NumPy SIMD level>`) that deployed it, plus a reference mesh and a derived mesh-moved tolerance. On a recorded mesh, `abs(x - g) <= 1e-8 * abs(g)`. On an unseen mesh, the same test against the reference mesh at the mesh-moved tolerance: 10 times the largest relative spread between the walk's meshes, at least 10⁻⁸, refused above 10⁻³, and none while one mesh is recorded. In the reference environment `linux-x86_64/X86_V3`, which CI and the gate pin with `NPY_DISABLE_CPU_FEATURES`, an unseen mesh fails. The same-mesh tolerance does not move | First recorded keyed by `<sys.platform>-<machine>`, mesh hash asserted exactly. CI's first run showed NumPy's SIMD dispatch moving the three PDB-derived meshes within that key, by 2.6 × 10⁻⁵ in the shell walk's current (`.knowledge/06` §8.1.5), so a platform key cannot promise one mesh. The author ruled, 5 October 2026, that the mesh hash classifies rather than asserts: round-off holds where the mesh is the same, a measured discretisation spread where it is not. [Design §2](#2-the-golden-tolerance-and-keying) |
| D14 | Recording | `NANOPNP_RECORD_STABILITY=<dir>` makes each assertion write `<dir>/<walk>.json` and pass. It is refused when `CI` is set. `tests/tier2/data/merge_number_stability.py` folds them in mesh by mesh (`fold`), re-deriving each walk's mesh-moved tolerance. A walk that cannot be held prints the record to fold. The reference environment is recorded locally. A mesh a CI leg deploys comes from its printed record, folded with `--entry` as a reviewed change | A gate can never record through itself. The amended D13 adds one CI change, the dispatch pin |
| D15 | "On `v0.4.0`'s tree" | Before recording, an AST comparison with docstrings stripped shows that every file of `src/`, `data/` and `examples/` at `v0.4.0` equals WP35's tree (the survey: `v0.4.0..e63a32e` touched docstrings and comments only). The result goes in an Outcome | G10. It records the golden without a worktree of a commit that has no hook to record from |
| D16 | Drift visibility | Each VER-62 assertion attaches `(walk, quantity, relative drift)` through `record_property`. A `pytest_terminal_summary` in `tests/conftest.py` prints the largest drift per walk, which works under xdist | The spread on each CI leg has to be read from somewhere. The end-of-phase report takes these numbers from here (Phase 4 plan) |
| D17 | Log format (VER-63) | A log is any `docs/**/*findings.md`. It carries YAML front matter `findings: {prefix, status: open\|closed, areas: [...]}`, and the check requires the front matter and the file name to go together, in both directions. Its table is `ID \| Area \| Severity \| Status \| Ruling \| Finding`. [Design §3](#3-the-findings-log) defines the statuses and the resolution of a ruling pointer | G4. The front matter makes the header machine-read |
| D18 | MOD areas | `stages`, `coupling`, `extension`, `surface` | The phase plan's four areas |
| D19 | Prose-only | `prose-only.sh` treats `*findings.md` as not prose, with a case in `test_workflow_hooks.py` | VER-63 reads these files. Without this, a ruling edit to a log would skip the test that checks it |
| D20 | Release | `CHANGELOG.md` `[0.5.0-alpha.1]`. After merge the author or session tags `v0.5.0-alpha.1` (G11). No `v0.5.0-*` tag exists locally or on `origin` (checked 5 October 2026) | §2.7; F2's stray tag is already gone |

> **Outcome — the measurement module and the relation (D1–D8).** `validation/modularity.py` reads
> the tree by AST and names the modules it reads by path, never as a dotted `nanopnp` name: an
> early draft spelt `"nanopnp.core.stages"` and so added six `string` edges `validation → …` of its
> own, and VER-61 now asserts that the measuring modules add none. At `97f2b3d`: 806 import edges
> (460 `top`, 112 `deferred`, 132 `typing`, 102 `string`), 101 static and 27 string subpackage edges,
> and a `top` SCC of exactly the ten members seed 3 predicted. The module-level `top` graph is
> acyclic. The corrections registry's members are the YAML stems under `data/corrections/` (D8 c),
> because `materials/models.py` registers only `none` in code. A measurement of `97f2b3d` and of
> WP35's tree differs in the size table, where `render_measurements` itself enters the top ten, and
> by one `string` import edge (807 edges, 103 `string`): `cli/errors.py`'s `EXCLUDED` naming
> `LogFormatError`, which adds no subpackage edge.
>
> **Outcome — the findings (D9, D10).** All 14 seeds are MOD-01 to MOD-14, in the seed order. None
> was dropped or merged. Three were added by measurement: MOD-15 (`core/stages.py:44`, `core`'s one
> upward `TYPE_CHECKING` import, which puts `core` in the static cycle), MOD-16 (the stabilisation
> registry closed by `Literal["none", "supg", "reference"]` at `io/case.py:662`), and MOD-17
> (`willems2020_nacl` as a default in eight signatures). The YAML annotates each edge pointing up the
> report's stated layer order with its finding. The order is the report's reading, not a rule.
> `nanopnp.validation.findings:LogFormatError` joined `cli/errors.py`'s `EXCLUDED`, with its reason,
> because VER-32's enumeration requires every public exception to be classified or excluded.
>
> **Outcome — D15, the tree computes as `v0.4.0`.** Every file of `src/`, `data/` and `examples/`
> at `v0.4.0` was compared with WP35's tree, by bytes and then, for Python, by AST with every bare
> string statement removed. 167 files are common: 150 are byte-identical, 16 Python modules differ
> in docstrings or comments only, and `data/geometry/README.md` differs as prose. The only additions
> are `validation/modularity.py` and `validation/findings.py`, which no walk imports, and the
> `LogFormatError` entry in `cli/errors.py`'s `EXCLUDED`, which no walk reads.
>
> **Outcome — D13, D14 and Design §2, the golden on Linux.** Recorded under
> `pytest -n auto --dist loadfile` (6 min, 24 tests), then asserted serially (9.9 min): the largest
> relative drift of every walk is **0**, and every mesh hash equal (`.knowledge/06` §8.1.5). The
> 2WCD walks record no `transport_number` or `eof_m3_s`, because their case asks for `current`
> only and has no flow: D12's "every scalar the walk produces". Example 03 holds 20 values, five per
> member, named `point-<index>.`. The other keys come from the PR's first CI run, as D14 expects.
>
> **Outcome — D13 amended, the golden keyed by mesh.** CI's first run deployed different meshes for
> the three PDB-derived walks under the same `linux-x86_64` key (`.knowledge/06` §8.1.5), and the
> author ruled that the mesh hash classifies rather than asserts (Design §2). The golden is now
> `nanopnp/golden/stability/v2`, read by `nanopnp.validation.stability`. It was rebuilt from three
> recordings of the same tree: the original one on an AVX-512 machine (labelled `X86_V4`, its exact
> top level not recorded), and two on an AVX2 machine at `X86_V3`, the reference environment, and
> at `X86_V2`. The last two agree bit for bit. Derived mesh-moved tolerances: the shell walk
> **5.2 × 10⁻⁴** (spread 5.2 × 10⁻⁵, `Cl⁻`); 2WCD charged and example 07 **10⁻⁸** (their meshes moved,
> their numbers by ≤ 2.4 × 10⁻¹⁴); examples 01–03 **none**, since every recording deployed one mesh.
> CI and the gate cap NumPy's dispatch at `X86_V3`. Windows and macOS legs that deploy an unseen
> mesh print a record to fold in, as D14 expects.

### Work items

1. **`validation/modularity.py`**, with D1–D5 and D8. Read [Design §1](#1-the-import-relation)
   first. Its public functions are `import_edges(root, sources=None)`, `subpackage_relation`,
   `components`, `stage_conformance`, `extension_points`, `backend_imports`, `sizes`,
   `version_literals`, `accepted_relation(path)`, `compare(measured, accepted)` and
   `render_measurements()`. `sources` lets a test substitute one module's text.
2. **`docs/project/modularity-layering.yaml`**: the status quo, generated once by the module and
   then hand-annotated with `finding`.
3. **VER-61**, `tests/tier1/test_layering.py`.
4. **The report and the log.** `docs/project/modularity.md` and `modularity-findings.md`, with D9,
   D10, D17 and D18. Add them to the `mkdocs.yml` nav and `docs/project/index.md`, and add the
   generated measurements page to both. `generate.py` calls `render_measurements()`.
5. **VER-63**: `validation/findings.py` (`parse_log`, `check_log`, and counts by area, severity
   and status, for the end-of-phase report) and `tests/tier1/test_findings_logs.py`.
   `prose-only.sh` (D19).
6. **VER-62.** Read [Design §2](#2-the-golden-tolerance-and-keying) first. Add a
   `number_stability` fixture to `tests/conftest.py` with D13, D14 and D16. A walk whose result
   is module-shared gets a new `test_ver62_<walk>_holds_the_number_stability_golden`. The two
   2WCD walks, whose `RunResult` is local, get the assertion inside the existing test. Then the
   golden file, the merge script, and the Tier-1 check of the file.
7. **Record** (D14, D15) on Linux, push, and commit the other keys from CI's printed entries.
8. **The `contributing.md` note**: a removed or added edge edits the YAML in the same commit, and
   a golden miss is investigated and then reverted or ruled and re-pinned (G10). Write the
   `CHANGELOG.md` section, the spec rows of VER-61, VER-62 and VER-63, and the Appendix A
   coverage note.

### Verification

| Test | Tier | Identifier | Assertion and oracle |
|---|---|---|---|
| `tests/tier1/test_layering.py` | 1 | VER-61 | The live static and string relations equal the YAML in both directions. The `top` module graph is acyclic. **Detector:** an `import nanopnp.gui` substituted into `core/constants.py` fails, naming `core → gui`, the module and the line. A YAML edge with no import behind it fails as removed. A synthetic three-module package is classified edge by edge into the four kinds, including `TYPE_CHECKING` and a deferred import. The SCCs of a constructed graph are as computed by hand |
| `tests/tier1/test_findings_logs.py` | 1 | VER-63 | Every real log passes. Constructed bad logs are each refused, naming the row: wrong column count, a bad or duplicate id, a wrong prefix, an unknown area, severity or status, an unresolvable or wrongly kinded ruling, a non-`—` ruling on `open`, a non-terminal row under `closed`, and front matter without the file name or the reverse |
| `tests/tier1/test_number_stability_file.py` | 1 | VER-62 | The schema is valid. Every walk in the file is asserted by exactly one test (a source walk of `tests/tier2` for `number_stability("<walk>"`). No value is zero. Every key has every walk |
| The seven walk tests (D11) | 2, `extended` | VER-62 | The mesh hash is exact, and every value is within 10⁻⁸ relative of its key's entry. Tolerance: G10, argued in Design §2 and measured per leg (D16) |
| `test_workflow_hooks.py` | 1 | — | `docs/x/findings.md` is not prose, and `docs/x/notes.md` is |
| Docs build | — | VER-45 | The report, the log and the generated page build under `--strict`, and each log row's link to its finding's anchor resolves |

Commands: the gate, then `.claude/hooks/gate.sh run`, then the documentation build (Phase 4 plan,
*Verification*).

### Out of scope

- **Any refactor, any change of a refusal text, and any `PUBLIC` change** (G1). These are rulings
  on `MOD-nn` and belong to the refactor packages (`/phase-plan amend 4`).
- QR-13's interface itself, and NUM-07 (Phase 6).
- The user-testing log. VER-63 already covers it by D17, and the protocol package writes it.

### Open questions

None blocking. D13's per-leg fallback and D14's expected-red first CI run are close calls, made
so that no workflow file changes. The author may prefer an `upload-artifact` step instead.

The brief runs to about 1,750 words, over its 1,200 target. It carries three verifiers and a
report, and each needs its format fixed before code is written.

## Design

### 1. The import relation

A source file `src/nanopnp/<p>/…` belongs to node `p`, and `src/nanopnp/__init__.py` belongs to
node `nanopnp`. The survey found no relative imports, so a target is the absolute dotted name. Even
so, `ImportFrom` with `level > 0` is resolved against the file's package, so that a future relative
import is not lost. For `from nanopnp.x import y`, the target module is `nanopnp.x.y` if that is a
module, and `nanopnp.x` otherwise. Both map to node `x`. Self-edges are dropped. The kinds are as
follows:

- An import whose nearest enclosing scope is a `FunctionDef` or `AsyncFunctionDef` is `deferred`.
- An import under `if TYPE_CHECKING:` or `if typing.TYPE_CHECKING:` is `typing`.
- Any other import, including one inside a module-level `try`, is `top`.
- A `Constant` string that is not a docstring and matches `^nanopnp(\.\w+)+(:[\w.]+)?$` is a
  `string` edge, when its module part resolves to a file or package.

The `top` module graph uses modules, not nodes, because Python can resolve a cycle between
subpackages but not, without care, one between modules.

SCCs are computed by Tarjan's algorithm, iterative so that depth cannot reach the recursion
limit. For each SCC the module lists its internal edges with the number of import statements that
carry each, lightest first, so that a finding can name a cheap cut. A minimum feedback arc set is
NP-hard, and the report names candidate cuts, never an optimum.

### 2. The golden: tolerance and keying

**Why 10⁻⁸ should hold within a key.** On one mesh and one library build, a refactor changes at
most the order of floating-point operations:

- assembly order perturbs the matrix entries at about `n·ε ≈ 10⁻¹⁵`;
- Newton stops where the undamped update is small, and its convergence is quadratic, so the final
  iterate sits at about the square of the last tested update from the discrete root, and well
  inside VER-35's 10⁻⁶;
- two runs that differ by round-off converge to the same root, so they differ by about the effective
  condition number of the scaled system times `ε`.

A quantity of interest is a smooth functional, an integral, and in practice moves far less than the
forward-error bound. The phase predicts below 10⁻¹⁰, and 10⁻⁸ is two orders inside VER-35 (G10).

**The failure mode that would break it.** A convergence test that straddles its threshold adds or
drops one Newton step. That moves a quantity by up to the size of that last step. If it is seen, it
is a finding about the convergence test, and never a reason to loosen 10⁻⁸.

**Why the key is per platform** (superseded by the amended D13, below). Netgen's advancing front decides on floating-point comparisons
that the compiler controls: 8141 against 8147 triangles on one geometry (`.knowledge/07` §5). Every
walk here meshes with netgen, so the values are per build, and the mesh content hash is asserted
first. Within the Ubuntu key, the legs run Python 3.11 to 3.14, and `uv.lock` resolves numpy 2.4.6
for one range and 2.5.2 for the other. If those legs disagree beyond 10⁻⁸, D13 splits the key by
Python minor, and the measured spread goes in an Outcome. A future `uv.lock` bump or a change of
runner image that moves a value is a G10 miss like any other: it is investigated, ruled, and
re-pinned in the same commit, with the drift stated.

**Why the mesh classifies rather than asserts (the amended D13).** A platform key cannot promise
one mesh: within `linux-x86_64`, NumPy's runtime SIMD dispatch moves the three PDB-derived meshes
(`.knowledge/06` §8.1.5), and adding the dispatch level to the key would only split it again
whenever the hosted fleet, the runner image or NumPy moved. The golden instead asks each run the
question its mesh can answer. On a recorded mesh, whether a change moved a number, at 10⁻⁸ as
argued above. On an unseen mesh, whether the answer is still right, at a tolerance derived from
what moving the mesh is measured to do: ten times the largest spread between the walk's recorded
meshes, under a 10⁻³ ceiling. The ceiling is a tenth of the ±1 % conductance floor that no geometry
comparison of this model resolves below (`.knowledge/04`). The reference environment keeps G10 at
full strength for a change that moves the mesh itself: CI and the gate cap NumPy's dispatch at
`X86_V3`, so every x86-64 Linux leg deploys the reference mesh, and there an unseen mesh fails.
A walk with one recorded mesh has no measured spread, so on an unseen mesh it fails, printing the
record whose fold supplies the spread. The rule is §7.6's NOTE on goldens, so a later golden
reuses `nanopnp.validation.stability` rather than re-arguing it.

**Measuring.** Before the recording is committed, the 2WCD walks run twice on Linux, serially and
under `-n auto`. The repeat spread is recorded. The CI legs' spread is read from D16's summary on
the PR, and both go in the Outcome as the argument G10 asks for.

### 3. The findings log

The front matter:

```yaml
---
findings:
  prefix: MOD
  status: open        # open | closed
  areas: [stages, coupling, extension, surface]
---
```

The first table after the front matter is the log. Its rows follow these rules:

- **ID** matches `^<prefix>-\d{2,}$` and is unique.
- **Area** is one of the declared areas.
- **Severity** is `high`, `medium` or `low`, as defined in D9.
- **Status** is one of the following:
  - `open`, which means unruled, and its ruling is `—`;
  - `accepted`, which means ruled to be fixed in this phase but not yet fixed, and needs a §8.2
    row;
  - `fixed`, which needs a link to an existing `docs/plans/*.md`;
  - `deferred`, `post-1.0` or `declined`, each of which needs a §8.2 row.
- **Terminal** statuses are `fixed`, `deferred`, `post-1.0` and `declined`. Under `status: closed`,
  any other status is refused.
- **A §8.2 row** is written `§8.2.N Xk`. It resolves when `SPECIFICATION.md` has a heading
  `#### 8.2.N` whose section contains a table row whose first cell is `Xk`.
- **Finding** links to its section in the report, and the strict build checks the anchor.

### 4. Seed findings

Each line gives the area, the expected severity, and what was measured at `e63a32e` by the survey.
The module re-measures each one.

1. *stages, high.* `Stage` lacks `key()`. `MaterialsStage` and `CaseStage` have none, and
   `validation/comsol.py:439` and `gui/assess.py:337` call it under `type: ignore` (FR-27).
2. *stages, medium.* The walk owns knowledge that belongs to the stages: `PIPELINE`,
   `PAYLOAD_FREE`, `STRUCTURE_STAGES`, `WORKSPACE_STAGES`, `STORE_STAGES`, and the drop rules of
   `selected_stages`.
3. *coupling, medium.* The subpackage SCC (expected ten members), with its cheapest cuts. Among
   them are `mesh/distance.py → physics, solve` and `materials/fields.py → charge`.
4. *coupling, medium.* `io` is both the base layer and the assembler (`io/case.py` imports
   `charge`, `materials`, `physics` and `solve`).
5. *coupling, low.* `cli/errors.py` is imported upward by `sweep`, `gui` and `validation`.
6. *extension, medium.* The mesher is a branch (`mesh/generate.py:323`), not a registry (ADR-002).
7. *extension, medium.* The linear solver is a branch (`solve/linear.py:152`), and
   `AVAILABLE_SOLVERS` is read by `io/case.py`.
8. *extension, low.* There are five registries of four shapes: stages, corrections, physics
   models, stabilisation and charge forms.
9. *extension, low.* `OUTPUTS`, `STERIC_MODELS` and `materials/forms.FORMS` are closed
   enumerations in the assembler.
10. *extension, high.* QR-13 and §5.4.1: no backend interface exists. `physics/` calls `ngs.*`
    directly, and 33 modules in 11 subpackages import NGSolve or Netgen. Its recommendation must
    weigh implementing §5.4.1 against amending it.
11. *surface, low.* `with_section` and `core.stages.register` are outside `PUBLIC` (WP34 D9).
12. *surface, low.* `nanopnp/__init__.py` mirrors `PUBLIC` in a `TYPE_CHECKING` block by hand.
13. *surface, low.* `cli/__init__.py` is 1,266 lines, and `build_parser` is 216. Other large
    modules are `io/case.py` (3,160) and `physics/models.py` (2,660).
14. *surface, medium.* Refusals are stale: `io/case.py` `_require_runnable` says "v0.4" and "v0.2"
    and "not delivered in this release", the last under an empty, dead `_UNCONSUMED_INPUTS`.
    These are user-visible texts.
