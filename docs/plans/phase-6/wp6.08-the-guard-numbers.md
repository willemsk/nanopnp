# WP6.08 — The guard numbers

**Status: in progress; item 1 done, item 2's run next.** Written 26 November 2026 on Fable 5.2 at high effort, grounded in the code at
`f571e72`. Inherits §8.2.53 BC3 and BC4, the rulings of this plan (§8.2.59 BI1, BI2), §8.2.51 BA14, §8.2.13 N1 and
N4, §8.2.7 G10 and VER-62's mechanism. Its last commit on `main` takes `v0.7.0-alpha.8` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.08 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** Nothing a user runs. Before the core of the physics is rebuilt, the program gains stored
reference numbers for six optional settings of the model that no stored number covers today: the extra dielectric
forces, the other form of the ion equations, the two stabilised modes, and the flow at constant density and without
inertia. Each is the charged pore of the second worked example with that one setting changed. Every night the six are
computed again, and the run fails if one has moved by more than one part in a hundred million: a rebuilt core that
changes an optional path is caught.

**Cost.** About 3 sessions, 2 to 3 agent hours and 4 times you act; the plan took half an agent hour and three of
those times. The nightly run grows by about five minutes on Linux.

**What could go wrong.** The numbers record what the program computes today, not that it is right: a fault already
there is stored with them. They are checked on Linux alone, so a change that moves an optional setting only on macOS
or Windows goes unseen. Without inertia the numbers lie so close to the default's that they show a broken path but
not an ignored setting. The other form of the ion equations is reached from Python alone, and a run that takes it
does not say so in its record: an open item for the design package.

**Your call.** Settled today: all six settings are stored, and the numbers are held on Linux alone. Still yours:
approve this plan. *Recommendation:* approve; it changes no physics and no file a user writes.

## Execution brief

Scope: the Phase 6 plan's WP6.08 entry (BC3; BI1, BI2). The package adds stored numbers for six of the model's
settings off their validated default, and the tests that hold them. It changes no code under `src/` and no physics.
It depends on nothing unmerged. It claims VER-80, a new clause of §7.3 that item 1 writes with its test, and touches
PHY-23, NUM-02, NUM-11 and NUM-14 through it. No `OPN-` is open in this area.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 What is stored** | Six walks, one setting off its default each: `guard-dielectric` (PHY-23), `guard-log` (NUM-02's log branch), `guard-reference` (NUM-14), `guard-supg` (NUM-11's flag), `guard-constant-density` (`physics.variable_density: false`) and `guard-no-inertia` (`physics.inertia: false`), the last two with the flow solved | BC3 names the first three. None of VER-62's walks takes any of the six, and no Tier 1 or Tier 2 test solves the flow with either flow switch off (*Grounding*). Ruled by the author: all six (BI1) |
| **D2 Where they are held** | In the reference environment alone, `linux-x86_64/X86_V3`; elsewhere each guard test skips before its walk, naming the environment | A guard asks whether a change moved a number, which one environment answers (§7.6's NOTE on a golden on more than one platform); VER-62's seven walks still ask every platform. Ruled by the author: Linux only (BI2) |
| **D3 One pore, one edit a walk** | Each walk is `examples/02-charged-pore/epnpns.case.yaml` with one setting changed, on the mesh `example-02-epnpns` already pins. A setting the NUM-18 ladder refuses takes `numerics.continuation: none` beside it; the two stabilisation modes keep the ladder | One edit localises a miss to one term (§7.1). Every walk converges; a single rung equals the ladder to 4e-16 (*Grounding*). Decided by the plan |
| **D4 The log branch enters at the resolved case** | `guard-log` hands `run_document` a resolved case whose `model_options` carries `log_variables: True`. No case key is added. That the branch has no case key and no line in the manifest is REV-298, which WP6.09's design takes up | No case file reaches the branch today, and the phase entry changes no physics and no schema. Decided by the plan |
| **D5 VER-62's mechanism, a clause of its own** | VER-80. The walks are folded into `tests/tier2/data/number_stability.json` under names that begin `guard-`, asserted through the `number_stability` fixture at 10⁻⁸ relative on the recorded mesh, and carry `nightly`. A later change to one is a re-pin by ruling | Open decision 14 leaves the identifier to this plan; §7.6's NOTE names the mechanism as the one a later golden reuses; the same file keeps the Tier 1 file checks and the fold tool as they are. Nightly: N4, BA14 and the phase entry. G10. Decided by the plan |
| **D6 What a walk stores, and what it asserts first** | VER-62's five quantities; the two stabilised walks add the stabilisation's current for each species. Before its numbers, each test asserts on the stored state's descriptor that the solved model carried the walk's one setting, every other switch at its default, and the walk's stabilisation mode | The stabilisation's current is the number that a stabilised mode adds. A walk that solved the default model would store the default's numbers and guard nothing; the descriptor is written from the model that solved. It is also how each number stands "with its stabilisation mode" (the phase entry), the file's schema holding none. Decided by the plan |
| **D7 Recorded once, then run with VER-62** | The numbers are recorded under the push gate's SIMD cap, on this package's tree. One run of the committed tree then takes VER-62's seven walks and the six guard walks: it shows that VER-62 passes on the tree the numbers come from, and gives each guard walk's largest drift on a repeat. A miss of VER-62 voids the record and stops the package | The phase entry; G10's "a figure the package argues from a measured rerun". The package changes no `src/`, so one run after the record serves both. Decided by the plan |

### Grounding

Measured at `f571e72` on Linux, one thread, under `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`
(`.claude/hooks/gate.sh`), which is `linux-x86_64/X86_V3`. A *shift* is the relative difference from the default
walk's value on the same mesh.

**D1**

- VER-62's walks at source. Five take no key of `physics/models.py:SWITCHES` off its default, with
  `stabilisation: none` and the ladder: `examples/01-quickstart/quickstart.case.yaml`,
  `examples/02-charged-pore/epnpns.case.yaml` and `classical.case.yaml` (every correction `none`),
  `examples/03-iv-sweep/charged.case.yaml` and `examples/07-pdb-to-charged-run/2wcd.case.yaml`. Two take the flow
  off: `SOLVE_CASE` of `tests/tier2/test_pipeline_2wcd.py` and of `tests/tier2/test_exclusion_2wcd_walk.py` set
  `physics.model: pnp`, `flow`, `variable_density` and `inertia` false, and `continuation: none`. So the review's
  claim holds for the three settings BC3 names, none of which a walk takes, and not to the letter.
- No test of `tests/tier1` or `tests/tier2` solves with `inertia` or `variable_density` false while the flow is on;
  the cases of `tests/tier3/test_val06_archive.py` and `test_charge_archive.py` do, and Tier 3 is not gated.
- Example 02's ePNP-NS case with one edit, on mesh `546c34f4…`:

  | Edit | Path | Seconds | Shift of `current_A` | of `eof_m3_s` |
  |---|---|---|---|---|
  | none (the default walk) | ladder | 23 | 0 | 0 |
  | `numerics.continuation: none` | single rung | 10 | 0 | 1.8e-16 |
  | `physics.dielectric_gradient_forces: true` | single rung | 114 | 1.1e-3 | 2.7e-3 |
  | the log branch (D4) | single rung, 38 iterations | 25 | 6.5e-6 | 7.5e-6 |
  | `numerics.stabilisation: reference` | ladder | 69 | 6.7e-3 | 1.7e-2 |
  | `numerics.stabilisation: supg` | ladder | 34 | 6.9e-3 | 8.9e-3 |
  | `physics.variable_density: false` | single rung | 9 | 3.7e-8 | 2.8e-8 |
  | `physics.inertia: false` | single rung | 9 | 3.4e-12 | 4.8e-9 |

  `guard-no-inertia`'s numbers therefore lie within 10⁻⁸ of the default's: the walk shows a broken path, not an
  ignored switch. `guard-constant-density` shows both, by a factor of about three.

**D2**

- `validation/stability.py:compare` returns a failure for a mesh the walk does not hold where the environment is not
  `REFERENCE_ENVIRONMENT` and the walk has one recorded mesh. `.github/workflows/ci.yml`'s `platforms` job runs the
  `nightly` tests on Linux, macOS and Windows each night, so a guard recorded on Linux alone fails there unless it
  skips first. `validation/stability.py:environment` returns the string to test; `ci.yml` sets the gate's cap, so
  CI's Linux leg is the reference environment.
- `tests/conftest.py`'s selection runs a `nightly` test whose file is named, without `--nightly`.

**D3**

- `pipeline/checks.py:_check_ladder_can_honour` refuses a case that sets `flow`, `variable_density` or `inertia`
  false, or `dielectric_gradient_forces` true, beside the ladder, and names `numerics.continuation: none`.
  `solve/state.py:ladder` then returns `single_rung`, whose model is `case_model(resolved)`; under the ladder it
  passes `resolved.stabilisation` to `default_ladder`, so a mode runs on the ladder.
- `api/case.py:Case.with_` takes a mapping of dotted paths and returns an edited copy that keeps the base directory,
  so `inputs.charge.path: ring.field.yaml` still resolves beside the example. Run here:
  `Case.load(<epnpns.case.yaml>).with_({"numerics.continuation": "none", "physics.inertia": False})`, then
  `Session(store, workspace=<dir>, write=False).run(case)`, gives `result.quantities` and
  `result.manifest.geometry_and_mesh["content_hash"]`, and writes nothing beside the example. `Case`, `Session` and
  `Store` are names of `nanopnp`.
- `io/workspace.py:scratch_directory` raises `WorkspaceInUseError` where the solve stage's folder holds an earlier
  run's files: each walk takes a workspace of its own, its test's `tmp_path`.
- The reference mesh of `example-02-epnpns` is
  `546c34f4fb4b625162ad2aeb2893b1ba6e221a5d40c868f615c6048e1731c631`; every walk above deploys it. With one `Store`
  for the module, the walks after the first take `region`, `mesh`, `charge` and `materials` from it.
- `reference` as a single rung differs from the ladder by 1.4e-13.

**D4**

- `io/case.py:Physics` and `pipeline/case.py:_model_options` hold no key for the branch.
  `physics/models.py:CoupledModel.log_variables` is set only through `models.create(..., log_variables=True)`, as
  `tests/tier2/test_pnp_benchmarks.py` does on VER-16's slab, at 3 %.
- `pipeline/run.py:run_document` takes `resolved=`, and `_given` refuses one whose `document` is not the document
  passed. `single_rung` builds `create(resolved.model, **resolved.model_options)`, and
  `physics/models.py:_build_epnp_ns` passes the option to `CoupledModel`. `default_ladder` builds its own models and
  would drop it, so the walk is a single rung. Run here: `resolved = pipeline.case.resolve(case, base=case.source.base)`;
  `dataclasses.replace(resolved, model_options={**resolved.model_options, "log_variables": True})`;
  `run_document(case, case_text=case.source.text, case_path=case.source.path, base=case.source.base, store=store,
  workspace=<dir>, write=False, resolved=<it>)`. It returns the `RunResult` that `Session.run` returns.
- `CoupledModel.__post_init__` refuses the branch beside `dielectric_gradient_forces`, so the two are two walks.
- `solve/stage.py:SolveStage` keys the solution by `resolved.solve_provenance`, which holds `model_options`: the
  log walk's artefact is not the primitive one's. `CoupledModel._deviations` omits the branch: the log walk's
  descriptor reads `deviations_from_validated_default: []`, and the manifest names `log_variables` nowhere.

**D5**

- `tests/conftest.py:NumberStability.__call__` compares with `STABILITY_GOLDEN`; under
  `NANOPNP_RECORD_STABILITY=<dir>` it writes `<dir>/<walk>.json` instead and asserts nothing; under `CI` it refuses
  to record. `tests/tier2/data/merge_number_stability.py <dir>` folds every record of the directory.
- `tests/tier1/test_number_stability_file.py:_asserted_walks` counts the calls `number_stability("<literal>", …)` in
  `tests/tier2/test_*.py`, and `test_ver62_every_golden_walk_is_asserted_by_exactly_one_test` wants the file's walks
  and the asserted ones equal: a guard walk is one test function with its name written out, never a parametrised
  name, and the guard file and its six records are one commit, which the commit hook's Tier 1 run would otherwise
  refuse.
- `validation/stability.py:MeshEntry` forbids a key other than `values` and `seen_on`: the file holds no mode.
- VER-79 is the highest `VER-` identifier in `specification/`. No test reads §7.3's rows.

**D6**

- `tests/conftest.py:stability_values` reads `STABILITY_QUANTITIES` and merges `extra`.
  `result.quantities["stabilisation_currents_A"]` maps each species to a float: zero under `none`, which
  `fold` refuses; −3.002e-13 A (Cl⁻) and −7.013e-13 A (Na⁺) under `reference`; −3.001e-13 A and −7.009e-13 A under
  `supg`.
- `numpy.load(result.artefacts["solve"].payload[STATE_KEY])[DESCRIPTOR_ENTRY]`, both names of `solve/state.py`, is
  JSON whose `model` holds `switches` (`flow`, `variable_density_flow`, `inertia`, `dielectric_gradient_forces`,
  `log_variables`, and `steric` and `pressure_constraint`, which no walk asserts) and `stabilisation`, written from
  `CoupledModel.provenance`. Read here: the log walk gives `log_variables: true` and `stabilisation: "none"`, the
  two stabilised walks `"supg"` and `"reference"` with every switch at its default.

**D7**

- `guard-dielectric` repeats bit for bit, and `guard-log` to one unit in the last place, between
  `linux-x86_64/X86_V3` on one thread and `linux-x86_64/AVX512_SPR` on four, on the same mesh.
- The six walks take about 270 s on one core, so a helper records them in two calls: `-k dielectric`, then the rest.
- `tests/conftest.py:pytest_terminal_summary` prints, under `number stability on <environment>`, each walk's mode
  and largest relative drift. The seven walks' time is not measured here: their run is a `RUN` hand-back.

### Implementation details

**Item 1, the test file.** `tests/tier2/test_guard_numbers.py`, with `pytestmark = pytest.mark.nightly` and a
docstring that names VER-80.

- Constants: `CASE`, the example's case file from the repository root; `SINGLE_RUNG = {"numerics.continuation":
  "none"}`; `DEFAULT = {"flow": True, "variable_density_flow": True, "inertia": True, "dielectric_gradient_forces":
  False, "log_variables": False}`.
- One autouse fixture: where `stability.environment() != stability.REFERENCE_ENVIRONMENT`, it calls `pytest.skip`
  with a message that names both (D2).
- A module-scoped `store` fixture: `Store(tmp_path_factory.mktemp("guard-store"))`.
- `_run(store, workspace, edits)`: D3's two calls. `_run_log(store, workspace)`: D4's three, on
  `Case.load(CASE).with_(SINGLE_RUNG)`.
- `_solved(result)`: the descriptor's `model`, read as *Grounding* D6 has it.
- Each test: run; assert `{name: model["switches"][name] for name in DEFAULT} == {**DEFAULT, **changed}`; assert
  `model["stabilisation"] == mode`; then `number_stability("<walk>", <mesh hash>, result.quantities, extra)`, the
  walk's name a literal. `extra` is `{f"stabilisation_currents_A[{species}]": value}` over both species on the two
  stabilised walks, and absent on the others.

| Walk | Test | Edits | `changed` | `mode` |
|---|---|---|---|---|
| `guard-dielectric` | `test_ver80_dielectric_gradient_forces_hold_their_numbers` | `SINGLE_RUNG`, `physics.dielectric_gradient_forces: True` | `dielectric_gradient_forces: True` | `none` |
| `guard-log` | `test_ver80_the_log_branch_holds_its_numbers` | `SINGLE_RUNG`, then D4 | `log_variables: True` | `none` |
| `guard-reference` | `test_ver80_the_reference_stabilisation_holds_its_numbers` | `numerics.stabilisation: reference` | none | `reference` |
| `guard-supg` | `test_ver80_supg_holds_its_numbers` | `numerics.stabilisation: supg` | none | `supg` |
| `guard-constant-density` | `test_ver80_a_constant_density_flow_holds_its_numbers` | `SINGLE_RUNG`, `physics.variable_density: False` | `variable_density_flow: False` | `none` |
| `guard-no-inertia` | `test_ver80_a_flow_without_inertia_holds_its_numbers` | `SINGLE_RUNG`, `physics.inertia: False` | `inertia: False` | `none` |

**Item 1, the record.** With `CI` unset and `<dir>` a new directory outside the tree:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
NANOPNP_RECORD_STABILITY=<dir> uv run pytest tests/tier2/test_guard_numbers.py -q -k dielectric
NANOPNP_RECORD_STABILITY=<dir> uv run pytest tests/tier2/test_guard_numbers.py -q -k "not dielectric"
uv run python tests/tier2/data/merge_number_stability.py <dir>
uv run pytest tests/tier2/test_guard_numbers.py -q -k "density or inertia"
```

Each call stays under four minutes. Check before the commit: `<dir>` holds six records, each with the mesh hash of
*Grounding* D3 and `linux-x86_64/X86_V3`; the diff of `number_stability.json` adds six walks and moves no other
line. A walk on another mesh, or a moved line, stops the item.

**Item 1, the clauses.**

- `specification/07-verification/03-tier-2.md`: the opening paragraph's list of converged-solve clauses gains
  VER-80. A row after VER-77, in the table's five columns. *Name:* the guard numbers. *Oracle:* the quantities that
  six walks compute, each example 02's ePNP-NS case with one setting off its validated default, named as D1 names
  them with their clauses, recorded on WP6.08's tree in VER-62's file, on the mesh `example-02-epnpns` pins, in the
  reference environment (§8.2.53 BC3; §8.2.59 BI1, BI2). *Acceptance:* each walk first asserts D6's two facts on
  the stored state's descriptor; then VER-62's five quantities, and on the two stabilised walks each species'
  stabilisation current, each within 10⁻⁸ relative of its recorded value, under VER-62's Tier 1 file checks; outside
  the reference environment the test skips before its walk; a regression reference with no independent oracle,
  whose miss is reverted, or re-pinned by ruling (G10). *Test file:* the guard file.
- `specification/07-verification/06-continuous-integration.md`, the NOTE on the per-push selection: the walks
  that carry `nightly` gain "or a guard walk of VER-80".
- `specification/a-traceability-matrix.md`, the closing paragraph: VER-80 verifies Phase 6's gate (§8.1; BC3, BC4),
  not a requirement of §3, and leaves the count unchanged.
- `CHANGELOG.md`: `## [0.7.0-alpha.8]` under `## [Unreleased]`, in WP6.07's shape; nothing changes for a user.

**Item 2, the run.** The hand-back's command, its log under the git directory:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" \
uv run pytest -q -rsfE -n auto --dist loadfile \
  tests/tier2/test_examples_01_quickstart.py tests/tier2/test_examples_02_classical.py \
  tests/tier2/test_examples_02_epnpns.py tests/tier2/test_examples_03_iv_sweep.py \
  tests/tier2/test_examples_07_pdb_to_charged_run.py tests/tier2/test_pipeline_2wcd.py \
  tests/tier2/test_exclusion_2wcd_walk.py tests/tier2/test_guard_numbers.py \
  > "$(git rev-parse --git-dir)/wp608-walks.log" 2>&1
```

Done when the log shows no failure and no skip, and its `number stability` section lists thirteen walks. A failed
or skipped walk of VER-62 is handed back `BLOCKED`; a guard walk that drifts beyond 10⁻⁸ is investigated, never
re-recorded to fit.

**Item 3, the records.**

- `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md`: a section with *Grounding* D1's table
  and its two conclusions, marked `[tested: …]` with the guard tests; the directory's `index.md` line and
  `knowledge/log.md`.
- `specification/history/holds-now.yaml`: BI1 `'VER-80; the Phase 6 plan'`; BI2 `'VER-80; §7.6''s NOTE on the
  per-push selection'`; BC3 loses its `open:` part.
- This plan: the status line and a `**Delivered.**` paragraph, and under item 2 an Outcome with each of the thirteen
  walks' largest drift, its mode and the stabilisation mode of each guard walk.
- The Phase 6 plan's WP6.08 entry, delivered; `docs/plans/current.md`.

### Work items

- [x] cdb67aa 1. `tests/tier2/test_guard_numbers.py`, `tests/tier2/data/number_stability.json`,
  `specification/07-verification/03-tier-2.md`, `specification/07-verification/06-continuous-integration.md`,
  `specification/a-traceability-matrix.md`, `CHANGELOG.md`: the six guard tests, their numbers recorded and folded
  in, VER-80 and the nightly NOTE (D1 to D7); done when `tests/tier1/test_number_stability_file.py` passes and the
  guard file's `-k "density or inertia"` passes against the folded file. **Executor:** main
- [ ] 2. The run of D7, a `RUN` hand-back with no commit, and the checkpoint: a fresh helper reads its log; done
  when the log lists thirteen walks with no failure and no skip. **Executor:** main, the run by the main session
- [ ] 3. `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md`, `knowledge/06-numerics-fem/index.md`,
  `knowledge/log.md`, `specification/history/holds-now.yaml`, this plan, the Phase 6 plan, `docs/plans/current.md`:
  the records, with each walk's drift (D7); done when the code and review say so. **Executor:** main

### Verification

| Test | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `test_guard_numbers.py`, the six tests of *Implementation details*, each on a case built with `Case.with_` from the example's file and run on the module's `Store` in its own `tmp_path` | 2, `nightly` | VER-80; PHY-23, NUM-02, NUM-11, NUM-14 | First the descriptor of the stored state, two assertions a walk: the five switches equal the default with the walk's one change, and the stabilisation mode is the walk's. Then the walk's recorded values on mesh `546c34f4…`: VER-62's five quantities, and both species' stabilisation current on the two stabilised walks | 10⁻⁸ relative, VER-62's same-mesh tolerance (§7.6's NOTE; G10); the descriptor exact | `uv run pytest tests/tier2/test_guard_numbers.py -q`, under the cap |
| `tests/tier1/test_number_stability_file.py`, unchanged | 1 | VER-62, VER-80 | Each `guard-` walk is asserted by exactly one test, holds no zero, and has its reference mesh from the reference environment | exact | `uv run pytest tests/tier1/test_number_stability_file.py -q` |
| VER-62's seven walks, unchanged (D7) | 2 | VER-62 | The file as it stands. Prediction: each on its recorded mesh at round-off, the package changing no `src/` | VER-62 | item 2's run |

D2's skip is one autouse fixture, read at review (N3).

### Out of scope

- The log branch's case key and its line in the manifest: REV-298, WP6.09's design.
- The kernel's check against these numbers: the kernel's last package (BC4).
- Guard numbers on macOS and Windows: ruled out (BI2); a later ruling of the author reopens it.
- Settings combined, and the corrections' own switches: WP6.09's design names what its packages need beyond the six.
- An independent oracle for a guard walk: none is sought; the two flow switches have Tier 3's archive cases, ungated.

### Open questions

None. BI1 and BI2 settle D1 and D2, and with D5 the Phase 6 plan's open decision 14.
