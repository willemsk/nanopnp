# WP6.08 — The guard numbers

**Status: draft, awaiting the author's rulings on D1 and D2.** Drafted 26 November 2026 on Fable 5.2 at high effort,
grounded in the code at `f571e72`. Inherits §8.2.53 BC3 and BC4, §8.2.51 BA14, §8.2.13 N1 and N4, §8.2.7 G10 and
VER-62's mechanism. Its last commit on `main` takes `v0.7.0-alpha.8` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.08 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## Execution brief

Scope: the Phase 6 plan's WP6.08 entry (BC3) and its open decision 14. The package adds stored numbers for the model's
settings off their validated default, and the tests that hold them. It changes no code under `src/` and no physics.
It depends on nothing unmerged. It claims VER-80, a new clause of §7.3, and touches PHY-23, NUM-02, NUM-11 and NUM-14
through it.

### Decisions

A row marked **the author's** is drafted and not ruled; the build does not start before it is.

| Decision | Choice | Why/source |
|---|---|---|
| **D1 What is stored** | *Drafted:* six walks, one setting off its default each: `guard-dielectric` (PHY-23), `guard-log` (NUM-02's log branch), `guard-reference` (NUM-14), and, beyond the phase entry, `guard-supg` (NUM-11's flag), `guard-constant-density` (`physics.variable_density: false`) and `guard-no-inertia` (`physics.inertia: false`), the last two with the flow solved | BC3 names the first three. The check of VER-62's walks finds the other three uncovered too, and no Tier 1 or Tier 2 test solves the flow with either flow switch off (*Grounding*). Widening is **the author's** |
| **D2 Where they are held** | *Drafted:* in the reference environment alone, `linux-x86_64/X86_V3`; elsewhere each guard test skips before its walk, naming the environment | A guard asks whether a change moved a number, which one environment answers; a session records on Linux only, and VER-62's seven walks still ask every platform. The other choice holds them on three platforms by VER-62's rule, after a nightly run that fails once. A trade of coverage against a follow-up: **the author's** |
| **D3 One pore, one edit a walk** | Each walk is `examples/02-charged-pore/epnpns.case.yaml` with one setting changed, on the mesh `example-02-epnpns` already pins. A setting the NUM-18 ladder refuses takes `numerics.continuation: none` beside it; the two stabilisation modes keep the ladder | One edit localises a miss to one term (§7.1). Every walk converges; a single rung equals the ladder to 4e-16 (*Grounding*). Decided by the plan |
| **D4 The log branch enters at the resolved case** | `guard-log` hands `run_document` a resolved case whose `model_options` carries `log_variables: True`. No case key is added. That the branch has no case key and no line in the manifest becomes a `REV` row, owned by WP6.09's design | No case file reaches the branch today, and the phase entry changes no physics and no schema. Decided by the plan |
| **D5 VER-62's mechanism, a clause of its own** | VER-80. The walks are folded into `tests/tier2/data/number_stability.json` under names that begin `guard-`, asserted through the `number_stability` fixture at 10⁻⁸ relative on the recorded mesh, and carry `nightly`. A later change to one is a re-pin by ruling | Open decision 14 leaves the identifier to this plan; §7.6's NOTE names the mechanism as the one a later golden reuses; the same file keeps the Tier 1 file checks and the fold tool as they are. Nightly: N4, BA14 and the phase entry. G10 |
| **D6 What a walk stores, and what it asserts first** | VER-62's five quantities; the two stabilised walks add the stabilisation's current for each species. Before its numbers, each test asserts on the stored state's descriptor that the solved model carried the walk's setting and its stabilisation mode | The stabilisation's current is the number NUM-14's mode exists to measure. A walk that solved the default model would store the default's numbers and guard nothing; the descriptor is written from the model that solved. It is also how each number stands "with its stabilisation mode" (the phase entry), the file's schema holding none. Decided by the plan |
| **D7 Recorded once, and repeated** | The numbers are recorded under the push gate's SIMD cap, on this package's tree, after VER-62's seven walks pass on it. The walks then run again against the file, and the largest drift of each is reported | The phase entry; G10's "a figure the package argues from a measured rerun". Decided by the plan |

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
  skips first. `validation/stability.py:environment` returns the string to test.
- Example 02's mesh is `10eb4a47…` on `darwin-arm64/ASIMDDP` and `137ec9d0…` on `win32-AMD64/X86_V3` (the file's
  `example-02-epnpns`); a record for either comes only from a run there.

**D3**

- `pipeline/checks.py:_check_ladder_can_honour` refuses a case that sets `flow`, `variable_density` or `inertia`
  false, or `dielectric_gradient_forces` true, beside the ladder, and names `numerics.continuation: none`.
  `solve/state.py:ladder` then returns `single_rung`, whose model is `case_model(resolved)`; under the ladder it
  passes `resolved.stabilisation` to `default_ladder`, so a mode runs on the ladder.
- `api/case.py:Case.with_` takes a mapping of dotted paths and returns an edited copy that keeps the base directory,
  so `inputs.charge.path: ring.field.yaml` still resolves beside the example. Run here:
  `Case.load(<epnpns.case.yaml>).with_({"numerics.continuation": "none", "physics.inertia": False})`, then
  `Session(store, workspace=<dir>, write=False).run(case)`, gives `result.quantities` and
  `result.manifest.geometry_and_mesh["content_hash"]`, and writes nothing beside the example.
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
  workspace=<dir>, write=False, resolved=<it>)`.
- `CoupledModel.__post_init__` refuses the branch beside `dielectric_gradient_forces`, so the two are two walks.
- `solve/stage.py:SolveStage` keys the solution by `resolved.solve_provenance`, which holds `model_options`: the
  log walk's artefact is not the primitive one's. `CoupledModel._deviations` omits the branch, and the manifest's
  document names `log_variables` nowhere.

**D5**

- `tests/conftest.py:NumberStability.__call__` compares with `STABILITY_GOLDEN`; under
  `NANOPNP_RECORD_STABILITY=<dir>` it writes `<dir>/<walk>.json` instead and asserts nothing; under `CI` it refuses
  to record. `tests/tier2/data/merge_number_stability.py <dir>` folds every record of the directory.
- `tests/tier1/test_number_stability_file.py:_asserted_walks` counts the calls `number_stability("<literal>", …)` in
  `tests/tier2/test_*.py` and wants each walk of the file once: a guard walk is one test function with its name
  written out, never a parametrised name.
- `validation/stability.py:MeshEntry` forbids a key other than `values` and `seen_on`: the file holds no mode.
- VER-79 is the highest `VER-` identifier in `specification/`.

**D6**

- `tests/conftest.py:stability_values` reads `STABILITY_QUANTITIES` and merges `extra`.
  `result.quantities["stabilisation_currents_A"]` maps each species to a float: exactly zero under `none`, which
  `fold` refuses, and −3.0e-13 A (Cl⁻) and −7.0e-13 A (Na⁺) under `reference`.
- `numpy.load(result.artefacts["solve"].payload[STATE_KEY])[DESCRIPTOR_ENTRY]`, both names of `solve/state.py`, is
  JSON whose `model` holds `switches` (`flow`, `variable_density_flow`, `inertia`, `dielectric_gradient_forces`,
  `log_variables`) and `stabilisation`, written from the solved model's `provenance`. Read here on the log walk
  (`log_variables: true`) and on the inertia walk (`inertia: false`).

**D7**

- `guard-dielectric` repeats bit for bit, and `guard-log` to one unit in the last place, between
  `linux-x86_64/X86_V3` on one thread and `linux-x86_64/AVX512_SPR` on four, on the same mesh.
- The six walks take about 270 s on one core, so a helper runs them in two calls: `-k dielectric`, then the rest.
