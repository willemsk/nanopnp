# WP39 — The backend registries

**Status: planned, not started.** Written 6 October 2026 on `ccr-ecd28ca7-5baf25` at `ae463d9`,
after WP38 merged, to be tagged `v0.5.0-alpha.4`. It inherits everything the
[current brief](current.md) lists as not to be re-decided, and in particular:

- WP36's stage protocol and walk, and WP38's split: `io` is the base, `pipeline/` the assembler,
  and `pipeline/checks.py` makes the registry checks of a document (WP38 D7);
- WP37's ratchets: `upward:` and `deferred_upward:` only shrink, `backend:` grows only by ruling,
  and a cut removes a dependency rather than deferring it (WP37 D12);
- VER-61's recorded layering, VER-62's golden and every stored artefact key, which it keeps.

This is the fifth work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md). It fixes
`MOD-06`, `MOD-07` and `MOD-16`, measures H6's target and resolves REV-05, REV-36, REV-37 and
REV-38 (§8.2.8 H5 to H7, H11, H12; §8.2.9 I3). `SPECIFICATION.md` governs, and the identifiers below
are pointers into it. **This commit amends the specification**: QR-14 and §5.5 gain the backend
registries, the §5.3.1 NOTE on `numerics.stabilisation` states the value set as the registered
modes, and the NOTE on `numerics.mesh` adds a library that fails to initialise to stage 6's
refusal. VER-66's row, VER-61's acyclicity clause and Appendix A's QR-14 pointer are claimed by
`/wp-implement` in the commit that implements them, as WP38's rows were.

## Execution brief

The brief runs to about 2,000 words, over the 1,200-word target. Each registry needs its dispatch
point and its key identity fixed (D2 to D5), and two decisions guard against a plausible wrong
answer: VER-24 losing three switches when their `Literal` goes (D8), and NUM-21's forbidden
solver becoming registrable (D3). The four review items are small, but each needs its oracle
stated. Splitting them off would leave REV-05's emptying of the ratchet and H6's assertion in
different PRs.

### Scope

H7 turns the three backend choices into registries. `numerics.stabilisation` already has one
(`physics/stabilisation.py`), which the schema's `Literal` closes (`MOD-16`). The linear solver is a
frozenset and a branch in `numerics/linear.py` (`MOD-07`). The mesher is a `Literal` and three
branches in `mesh/generate.py` (`MOD-06`). WP38 has already moved the schema's import of the
solver set into `pipeline/checks.py`, so H7's "the schema stops importing `solve.linear`" holds
on `ae463d9`. What is left is the registries themselves and their checks.

One PR delivers:

- **Three registries** (D1 to D5) and the three keys as strings checked against them (D6, D7);
- **H6 measured** (D10): on `ae463d9` the `top` relation has no component of more than one
  subpackage, and its only upward edges are `cli → nanopnp` (`top`) and `gui → nanopnp`
  (`deferred`). REV-05 (D9) removes both;
- **REV-36, REV-37 and REV-38** in the Gmsh session (D11).

**Breaks** (F4; `CHANGELOG.md`):

- The JSON schema of `numerics.mesh.backend`, `numerics.linear.solver` and
  `numerics.stabilisation` loses its enumeration. Every document that validated still validates,
  so the schema identifier stays (§5.3.1 NOTE; H7).
- An unregistered value of the three keys is refused by `check_document`, in the text of D7,
  where the schema's `Literal` refused it before.
- `numerics.linear.AVAILABLE_SOLVERS` and `mesh.generate.gmsh_backend` are gone (internal, IF-01).

Pointers:

- §5.1, §5.3.1 (the NOTEs on `numerics.mesh` and `numerics.stabilisation`), §5.5, §6.6;
- QR-11, QR-13, QR-14, CON-10, NUM-11, NUM-21, IF-01, IF-03, FR-25, FR-27; ADR-002;
- VER-24, VER-43, VER-45, VER-54, VER-61, VER-62, VER-63, VER-65, VER-66 (proposed);
- §8.2.8 H5, H6, H7, H11, H12; §8.2.9 I3;
- the [report](../project/modularity.md)'s `MOD-06`, `MOD-07` and `MOD-16`, and the
  [register](../project/review-items.md)'s REV-05, REV-36, REV-37 and REV-38.

No `OPN-` is open here. The phase plan's open decision on the coupling target is measured by D10.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | The shape | Each registry copies `physics/stabilisation.py`'s: `register…(name, builder)` with a zero-argument builder, a sorted `registered_…()`, and `create…(name)`, which raises `KeyError` naming the registered names. A duplicate name is refused with `ValueError`. Built-in entries are registered by module-level calls with a literal name. Stabilisation keeps its names. The new ones are `register_solver`, `registered_solvers`, `create_solver` and `register_mesher`, `registered_meshers`, `create_mesher` | H5: a registry H7 adds follows the nearest shape and adds none. The literal calls are what `extension_points` reads (`call:`) |
| D2 | The mesher | A new `mesh/meshers.py` holds a `Mesher` protocol and the registry. A `Mesher` has `name`, `settings(*, exclusion: bool)` (the backend's own entries of the stage-6 recipe) and `mesh(record, wall_h_nm, sizes) -> (MeshData, version)`. The `netgen` and `gmsh` entries take today's two branches verbatim, together with `mesh_shape`, `gmsh_backend` (made private) and its refusal. `generate.mesh_region` and `sizing_parameters` call `create_mesher(backend)` and keep the common recipe entries. `mesh/reference.py` imports `mesh_shape` from its new home. `generate` imports `meshers`, never the reverse | The recipe branches as well as the meshing (*Design* §2), so one object must own both or the key and the mesh can disagree. A module of its own keeps the module graph acyclic (VER-61) |
| D3 | The linear solver | `numerics/linear.py` holds a `LinearSolver` protocol, with `name` and `solve(matrix, rhs, correction, freedofs)`, and the registry. `umfpack` and `superlu` take the two branches of `solve_correction` verbatim, and `solve_correction` becomes `create_solver(solver).solve(…)`. `check_solver` stays the refusing lookup: a registered name passes, an unregistered name of `_REJECTED` is refused with its NUM-21 reason, and anything else is refused listing `registered_solvers()`. Registering `sparsecholesky` is refused, naming NUM-21. `pardiso` and `mumps` may be registered | H11 places it here. NUM-21: "`sparsecholesky` SHALL NOT be used", while its table names MUMPS for a source build, which a registration must be able to reach |
| D4 | The stabilisation mode | The registry is unchanged. The schema field becomes `str` (D6). `inf_sup_problem` already reads each mode's `permits_equal_order` | `MOD-16`'s recommendation |
| D5 | Registering Gmsh | The `gmsh` entry imports nothing at registration and nothing at `settings`; `mesh` imports `nanopnp.mesh.gmsh_backend` when it is called. A missing extra is still `MissingExtraError` at stage 6, never at load or resolve | CON-10, H7, WP23 D9 |
| D6 | The schema | `MeshSpec.backend`, `LinearSpec.solver` and `NumericsSpec.stabilisation` become `str`, defaults unchanged. Each description says the value is checked against its registry. `io/` imports no registry | H7; WP38 D2 |
| D7 | The checks | `pipeline.checks.check_document` gains `numerics.mesh.backend` against `registered_meshers()`: "numerics.mesh.backend {v!r} is not a registered mesher; the meshers are …". The stabilisation text is unchanged. The solver text is unchanged for a name `_REJECTED` does not hold, and gives NUM-21's reason for one it does. `registry_options` gains `numerics.mesh.backend` and reads `registered_solvers()`. A structural refusal still comes first (WP38's Outcome on D7) | IF-03: a refusal names what is admitted. QR-11: the editor reads the same function |
| D8 | VER-24 | `SWITCH_PATHS` and `CONFIGURATION_PATHS` are unchanged. `test_manifest.py`'s `_is_switch` also counts a `str` field that `registry_options` governs, and a test asserts that the three paths are detected | Today the predicate finds the three by their `Literal`. Without D8 the walk would stop seeing them, and a later switch of the same shape would go unclassified: a manifest that omits a deviation |
| D9 | REV-05 | A new `core/public.py` holds `__version__` (read from the distribution, as now) and `PUBLIC`. The facade imports both at module scope, keeps the `TYPE_CHECKING` mirror, `__getattr__` and `__dir__`, and `nanopnp.PUBLIC is nanopnp.core.public.PUBLIC`. `cli/__init__.py`, `cli/reference.py` and `gui/probe.py` import from `nanopnp.core.public`. `validation.modularity.surface` reads `PUBLIC` from its new home. `upward:` and `deferred_upward:` become empty, and the string relation moves from `nanopnp → *` to `core → *` (`core → physics` is new) | `core` already holds the two other string tables naming modules above it: the stage registry and the exit table. A version lookup in `cli` would give the version two homes |
| D10 | H6 | VER-61 gains a direct assertion: the `top` relation's `components` include none of more than one subpackage. It does not rest on the empty `upward:` list, which a ruling could refill. Oracle: a module-scope `import nanopnp.mesh.primitives` in `geometry/analyte.py` fails naming the component `{geometry, mesh}`. The static relation's component of ten subpackages, from annotation imports, is reported and not targeted (criterion 3) | H6, measured on `ae463d9` (*Design* §1). The phase plan's prediction holds |
| D11 | REV-36 to REV-38 | In `gmsh_backend._session`: (a) a borrowed session's logger is neither started nor stopped, and its messages are left to the caller; (b) a failure of `gmsh.initialize` raises the backend's own initialisation error, which the `gmsh` entry turns into `MissingExtraError` naming the extra, beside the missing module and the `OSError`; (c) every cleanup step runs. If an error is already propagating, a cleanup failure is logged at WARNING and added to it with `add_note`. Otherwise the first cleanup failure is raised after the remaining steps have run | The register's three items. (b) puts the extra's refusal in one place (D2). (c) means a finalise is never skipped, so no session leaks |
| D12 | Public registration | The six new functions are internal, as `physics.stabilisation.register` is. Whether they join `PUBLIC` is `MOD-11`'s question, which waits for the sessions (H2). `/wp-implement` adds a REV row naming them for that ruling | Adding them is additive, either way |
| D13 | Numbers and keys | Zero drift: VER-62 at 10⁻⁸, and no artefact key moves. The netgen and gmsh recipes are the same dictionaries, and the solver and mode names are unchanged | *Design* §2. A moved key is an Outcome to explain, not a value to re-pin (G10) |
| D14 | Records | `MOD-06`, `MOD-07` and `MOD-16` become `fixed` in the findings log, and REV-05, REV-36, REV-37 and REV-38 in the register. `extension_points` reads the mesher and the linear solver as registries (`mesh/meshers.py`, `call:register_mesher`; `numerics/linear.py`, `call:register_solver`). The YAML's header loses its "WP39 removes" sentence | VER-63; H12 |
| D15 | Release | `v0.5.0-alpha.5`, with a `CHANGELOG.md` section listing D6's and D7's breaks and the moves of D2 and D9 | §2.7; G11 |

### Work items

In dependency order. The import rewrites and test renames are mechanical and run on Sonnet
(`.claude/model-policy.md`). D3, D7, D8 and D11 run on Opus, because each can turn a refusal or a
check into a silent pass.

1. `numerics/linear.py`'s registry, `check_solver` and `solve_correction` (D1, D3).
2. `mesh/meshers.py`, and `generate.py`, `reference.py` and `ingest.py` re-pointed (D2, D5).
   Read *Design* §2 first.
3. `gmsh_backend._session` (D11). Read *Design* §3 first.
4. The schema fields (D6); `check_document` and `registry_options` (D7); the switch predicate (D8).
5. `core/public.py`, the facade, `cli`, `gui/probe.py` and `modularity.surface` (D9).
6. `validation/modularity.py`'s `EXTENSION_POINTS` (D14), the YAML (`edges:`, both upward lists,
   header), and the acyclicity test (D10).
7. The tests, VER-66's row and VER-61's clause, Appendix A's QR-14 pointer, the findings log and
   the register, `.knowledge/07`'s Gmsh session facts, `CHANGELOG.md`, and the phase plan's
   Outcome.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_backend_registries.py` (new) | 1 | VER-66, QR-14, IF-03, QR-11 | A stub mesher, solver and mode, registered in the test and removed after it. Each named in a case validates through `loads_case`, `check_document` and `nanopnp validate case`, and the editor offers it. On the quick-start pore of VER-56's test, a `pnp` run naming a solver that forwards to `umfpack` and a mode that forwards to `none` equals the plain run's state bitwise, and both stubs record calls. The VER-52 fixture through `inputs.profile`, walked to `mesh` with a mesher forwarding to netgen, gives netgen's vertices and triangles exactly and a recipe naming the stub. An unregistered name of each key is refused naming the registered ones, in the same text on the command line and in the editor. In a fresh process, `registered_meshers()` contains `gmsh` with neither `gmsh`, `nanopnp.mesh.gmsh_backend`, `netgen` nor `ngsolve` in `sys.modules` |
| `tests/tier1/test_linear_solver.py` | 1 | NUM-21, CON-11 | `register_solver("sparsecholesky", …)` is refused naming NUM-21. `mumps`, unregistered, is refused with its reason, at `check_solver` and at `check_document`. A duplicate is refused. SuperLU still agrees with UMFPACK |
| `tests/tier1/test_mesh_gmsh.py`, `tests/tier2/test_mesh_backends.py` | 1, 2 | VER-54, CON-10 | (a) A caller's started logger still holds its own message after a borrowed mesh. (b) `gmsh.initialize` patched to raise gives `MissingExtraError` naming `gmsh` and the error. (c) `gmsh.model.remove` patched to raise inside a failing mesh leaves the meshing error propagating, carrying the cleanup failure as a note. In a successful mesh it raises, and the session is still finalised. The existing VER-54 keys, gates and refusals are unchanged |
| `tests/tier1/test_manifest.py` | 1 | VER-24, FR-25 | The three paths are switch-typed under D8, and the classification sets are unchanged |
| `tests/tier1/test_layering.py` | 1 | VER-61 | The YAML equals the relation. Both upward lists are empty. D10's assertion and its oracle hold |
| `tests/tier1/test_public_api.py` | 1 | IF-01, VER-45 | `PUBLIC` is read from `core/public.py`. `nanopnp.PUBLIC` and `nanopnp.__version__` are that module's. Every mirrored name's module equals `PUBLIC`'s |
| `tests/tier1/test_gui_viewmodels.py` | 1 | VER-43 | The editor's options for the three paths equal the live registries, `numerics.mesh.backend` included |
| `tests/tier1/test_modularity_measurements.py` | 1 | VER-61 | `extension_points` lists the mesher and the linear solver as registries, at their homes |
| `tests/tier1/test_backend_guard.py` | 1 | VER-65 | `backend:` is unchanged at eleven. `meshers.py` is in `mesh`, which is already recorded |
| `tests/tier1/test_findings_logs.py` | 1 | VER-63 | D14's rows are `fixed`, each linking this plan |
| The VER-62 walks and key goldens (`extended`) | 2 | VER-62, VER-54 | Zero drift at 10⁻⁸. Netgen's and Gmsh's stage-6 keys are unchanged |

Command: `.claude/hooks/gate.sh run`, then the documentation build of `CLAUDE.md`'s table (VER-45).
The generated case-file reference keeps listing the three keys' values, read through `options_at`.

### Out of scope

- One registry shape for all five, and the repeated defaults: post-1.0 (`MOD-08`, `MOD-17`; H5).
- The `outputs` and steric-model enumerations: Phase 5 (`MOD-09`; H4).
- `mesh/adapter.py`'s format table. `"gmsh"` and `"netgen"` there name file formats (IF-06), not
  meshers.
- `PUBLIC`'s registration names: `MOD-11`, after the sessions (D12).
- The stale release strings: WP40 (`MOD-14`). The refusals written here name requirements only.
- The static relation's component: reported, not targeted (criterion 3).

### Open questions

None blocking. D12 records a question for `MOD-11`'s ruling.

## Design

### 1. H6 on `ae463d9`

Measured with `nanopnp.validation.modularity` on the merged tree, the `top` relation has no
strongly connected component of more than one subpackage. Its upward edges are `cli → nanopnp`
(`cli/__init__.py`, `from nanopnp import __version__`; `cli/reference.py`, `from nanopnp import
PUBLIC`). The one deferred upward edge is `gui → nanopnp` (`gui/probe.py:441`). With D9 all three
read `core`, so both lists are empty. Then every `top` edge points down a total order, and the
relation is acyclic by construction. D10 asserts this directly, so a ruling that later records
an upward edge cannot reopen a cycle unseen. Neither the registries nor D9 add an upward `top`
edge. `pipeline → mesh` and `pipeline → numerics` already exist, and `core → physics` is a string
edge.

### 2. Why the mesher's object owns its recipe

`sizing_parameters` builds the stage-6 recipe that keys a generated mesh. It branches on the
backend twice: `gmsh` adds `{"gmsh": {algorithm, smoothing, fields}}`, while `netgen` adds
`optsteps2d` and, with an exclusion shell, `exclusion_wall`. `mesh_region` branches a third time to
mesh. If the registry dispatched the meshing and left the recipe branching on a name, a registered
mesher would be keyed with netgen's settings and meshed with its own: two different meshes under
one key. `Mesher.settings(exclusion=…)` returns exactly the backend-specific entries, and
`sizing_parameters` merges them with the common `backend`, `wall`, `table`, `grading`, `gate` and
`exclusion` entries. The canonical encoding sorts keys (`core/hashing.py`, `sort_keys=True`), so
the merge order does not reach the key. Each built-in entry returns today's dictionary, and both
stage-6 keys stay as they are.

### 3. The Gmsh session's cleanup

Today `_session` has two nested `finally` blocks: `logger.get` and `model.remove` in the inner,
and `logger.stop`, the option restore and `finalize` in the outer. A raise in `model.remove`
replaces the error in flight (REV-38) and skips the outer block's remaining steps when it raises
there too. D11 (c) runs each step in turn and collects its failure. If an error is propagating,
each failure becomes a WARNING and a note on that error. If not, the first failure is raised once
every step has run. In a borrowed session, (a) leaves out the logger's `start`, `get` and `stop`:
`stop` clears a log the caller owns, and with the terminal off no message reaches the standard
output that IF-02 reserves. `GmshMeshingError`'s log tail still reads `gmsh.logger.get()`, which
in a borrowed session is the caller's log.
