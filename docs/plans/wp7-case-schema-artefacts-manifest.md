# WP7 — Case-file schema, artefacts, and the provenance manifest

**Status: planned, not started.** Written 3 September 2026, the first package of Phase 1, after the
phase plan merged in PR #16. It inherits from Phase 0 a verified solver and *no serialisation layer
whatsoever*: `src/nanopnp/io/` is a one-line docstring, `core/` has `constants.py`, `paths.py`,
`scaling.py` and `typing.py` and nothing else, and `hashlib`, `json` and `dataclasses.asdict` appear
nowhere in `src/`. Every file this package touches is new.

This is the implementation plan for WP7 of `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md`
remains normative: where this file and the specification disagree, the specification governs and this
file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

Phase 0 proved the physics against closed forms. It did so from Python: every test constructs an
`Electrolyte`, a `CoupledModel` and a `Rung` ladder by hand. Nothing in the package can read a case,
write a result, or say what produced a number. WP7 is the package that makes a run an *object* rather
than a script, and everything after it — the CLI (WP10), the sweep runner (WP11), the Tier-3 harness
(WP13) and the GUI (WP14) — consumes what it defines. The phase plan puts it first for that reason.

Three facts about the code today shape the design, and all three were established by reading it
rather than assumed.

- **The provenance material already exists, scattered.** Eleven objects expose a `.provenance`
  property or a `.summary()` method — `Scales`, `Electrolyte`, both `CorrectionModel`
  implementations, both `PhysicsModel` implementations, `NondimensionalCoefficients`,
  `NewtonResult`, `RungResult`, `LadderResult`, `RouteAgreement`, `QuantitiesOfInterest`,
  `ForceComponents`, `ForceAgreement`, `AnalyteForces` — plus `continuation.mesh_report`. WP7 does
  not invent provenance; it assembles these into the eight field groups of §5.3.3 and finds what is
  missing.
- **The one manifest field group that is already computed is already wrong.**
  `CoupledModel._deviations()` (`src/nanopnp/physics/models.py:553`) enumerates five switches by
  hand. It omits every *correction* switch: a case with `corrections.viscosity.model: none` runs
  classical viscosity and reports **no deviation**, though PHY-22 lists `viscosity_correction` as
  defaulting to on. This is precisely the failure mode the phase plan predicted for a hand-written
  enumeration, present in the tree today, and §Design says how WP7 removes the category.
- **`CorrectionSwitches`'s field defaults are the classical model, not the validated one**
  (`materials/electrolyte.py:60`, all-off, with `for_model` building ePNP-NS). So the tempting
  implementation of the Deviations group — pydantic's `model_dump(exclude_defaults=True)` — is not
  merely fragile here, it is *inverted*: it would report the validated ePNP-NS configuration as nine
  deviations and classical PNP-NS as none.

The package delivers `core/hashing.py`, `core/stages.py`, `io/case.py`, `io/defaults.py`,
`io/artefact.py`, `io/store.py`, `io/manifest.py`, three concrete stages, and four amendments to
§5.3.1 without which the case file cannot express a Phase-1 run at all. It discharges **IF-03,
IF-08, FR-25, FR-26, FR-27, VER-09** and begins **IF-01**. No new dependency: `pydantic 2.13`,
`pyyaml`, `meshio` and `h5py` are already core dependencies.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Where the hash is taken | Over the **validated pydantic dump**, never over parsed YAML and never over file bytes | YAML gives `1` an `int` and `1.0` a `float`; validation coerces both to the same field. Key order, comments, quoting and anchors all vanish in the same step. Hashing after validation is what *makes* FR-26 true rather than something FR-26 must be defended against separately |
| Float encoding | `float.hex()`, with `−0.0` normalised to `0.0` before encoding | `float.hex()` is the IEEE-754 bit pattern by definition, so it is exact and independent of the repr algorithm; `repr` is round-trip exact but its formatting is a CPython implementation detail. `(-0.0).hex()` is `'-0x0.0p+0'` and `(0.0).hex()` is `'0x0.0p+0'` **[tested]** — two spellings of a bias that resolve to the same run, so the sign of zero is normalised out |
| Arrays and files | An array hashes as `dtype`, `shape` and the sha256 of its C-contiguous bytes; an input *file* hashes by content, never by its path | A path in the hash makes a case unreproducible on another machine and makes a moved file a changed input. The path is recorded in the manifest, where it belongs, and the content is what the cache keys on |
| Sets, `None`, `NaN` | `set` is rejected outright; `None` encodes as a tagged null; `NaN` hashes equal to itself | A set of mixed types has no canonical order, so accepting one would make the hash depend on insertion. `NaN` never reaches a hash from a valid case — the schema rejects it — and equal-hashing is the right behaviour if one ever does |
| Hash presentation | Full sha256 (64 hex) is the key; the first 12 hex is the display and directory-fan-out prefix | 48 bits over the §8.3 datum of 3,675 solves at ~6 artefacts each (n ≈ 2.2 × 10⁴) gives a collision probability n²/2N ≈ 4.86 × 10⁸ / 5.63 × 10¹⁴ ≈ **8.6 × 10⁻⁷**. Adequate for a label; the store never keys on it |
| Where the schema lives | `io/case.py`, mirroring §5.3.1 verbatim, `extra="forbid"` on every model, `schema:` string checked *before* structural validation | Copies `materials/corrections.py` exactly, including the ordering: a file written to a future schema must fail naming the schema it claims, not with a wall of field errors against a shape it never claimed |
| The IF-03 diagnostic | A `CaseValidationError` wrapping pydantic's `ValidationError`, rendering one line per error as `<dotted.path>: <what>`, with `unknown key` for `extra_forbidden` and a `difflib` suggestion | **[tested]** pydantic 2.13 reports `type='extra_forbidden'`, `loc=('corrections','diffusivty')`, `msg='Extra inputs are not permitted'`. The `loc` carries the key; the message does not. IF-03 requires the key be named, so the wrapper is load-bearing, not cosmetic |
| Externally supplied mesh and fields | A new top-level `inputs:` block in the case file, naming supplied upstream artefacts by stage — **not** new alternatives inside `geometry:` and `charge:` | FR-27 already grants that any artefact may be "substituted by hand". An externally supplied mesh *is* a hand-substituted stage-6 artefact, so Phase 1's whole premise needs one general construct rather than a variant of each pipeline section. A stage whose output is supplied does not run, and neither does anything upstream of it — which is exactly how Phase 1 runs without Phases 2–3. §5.3.1 amendment A |
| Round-trip semantics | Equality of the **case artefact's content hash** across write → read, plus equality of `ResolvedCase.provenance` | A text comparison passes files that resolve differently and fails files that resolve identically. Naming the hash rather than the provenance dict makes the test one line and makes VER-09 the same assertion the cache already depends on |
| The Deviations group | A structural diff against an explicit `VALIDATED_DEFAULT_CASE` in `io/defaults.py`, over an enumerated `SWITCH_PATHS` set, with a Tier-1 test asserting every switch-typed field in the schema tree appears in that set | Field defaults cannot serve (see §Context: they are classical, not validated). The enumeration is the thing that rots, so the test enumerates the *schema* and fails when a switch is added without a validated default. That is the only mechanism that makes "every switch" true a year from now |
| `CoupledModel._deviations` | Kept, narrowed to the model's own switches, and **cross-checked** by a Tier-1 test against the `io/defaults.py` diff on the same case | `physics/` must not import `io/` (§5.4.1: IO and provenance are `core/` and `io/`, not the backend layer). Two computations that must agree, with a test that says so, beats one that silently under-reports |
| Artefact representation | A frozen dataclass with `schema`, `parameters`, `inputs`, `payload`, `summary`; pydantic stays at the file boundary | CLAUDE.md's rule is pydantic *at* serialisation boundaries. Artefacts carry `GridFunction`s and arrays and are not serialisation boundaries — their `meta.json` is |
| Hand substitution | Payload hashes are **recomputed on load and never trusted from `meta.json`**; a mismatch is recorded as `hand_substituted: true` in the manifest rather than aborted | §5.3.2 says a hand-substituted artefact registers as a changed input, and FR-27 says artefacts may be edited by hand. Aborting would forbid what FR-27 grants. The cost is that a corrupted file reads as a deliberate substitution — the manifest records it either way, which is the honest outcome |
| Manifest format | JSON, with the case file embedded verbatim as a string alongside its hash | The canonical JSON encoder is needed for the hash anyway. Re-emitting the case as YAML would let the manifest's case and the manifest's case-hash disagree |
| Concurrent writes | Write to a temporary file in the destination directory, then `os.replace` | Atomic on POSIX and Windows, and the store is content-addressed, so the race writes identical bytes. A job array (WP11) hits this on day one |
| The environment probe | `importlib.metadata.version` over an explicit distribution list derived from §2.6, `None` where not installed | `importlib.metadata` reads metadata without importing. Importing `ngsolve` to read its version would cost ~370 ms in every CLI, GUI and sweep-worker process and violates the deferred-import rule for no gain |
| Correction-file version | The Materials group records the **sha256 of the resolved `data/corrections/*.yaml`** beside its name | FR-25 asks for "version of each parameter data file" and `CorrectionDocument` carries no version field. The content hash is the version, and resolving it through `core.paths.correction_file` needs no change in `materials/` |
| Stage registry | Name → `"module:attribute"` **string** plus its `describe()` metadata, resolved by `importlib.import_module` only when the stage is run | FR-27's introspection is what the deferred-import rule exists to protect: `nanopnp stage --list` and the GUI's stage browser must not import the physics. Holding the metadata in the registry entry means introspection never touches the module |
| Cancellation | Cooperative, via a `CancelToken` the stage checks between rungs and inside the `damped_newton` callback, raising `Cancelled` | **No change to `solve/`**: `damped_newton` already takes `callback: Callable[[NewtonStep], None]` and calls it unguarded at `newton.py:372`, so a callback that raises propagates out of the solve. A cancel that interrupts a UMFPACK factorisation would need a subprocess and a signal; the GUI has one above this layer anyway (ADR-004) |
| Which stages WP7 implements | Three — `materials`, `case`, `solve` — the last over a *constructed* `CylindricalPoreGeometry` mesh | A protocol with no implementation cannot be verified, and "a package that cannot be verified by the end of its own PR is two packages". These three need no mesh ingestion, so WP7 stands alone. WP10 keeps QR-08 and the CLI; WP7's Tier-2 test asserts cache identity, not full QoI reproduction |
| Store root | `NANOPNP_STORE`, else `./nanopnp-store`, resolved by a new `core.paths.store_root()` | `core/paths.py` already owns "where things are" and `nanopnp --env` already reports it |

## Design

### Canonicalisation, written out

`core/hashing.py` defines one function and everything else follows from it.

```
canonical(obj) -> bytes         # UTF-8 JSON, sort_keys, separators=(",",":"), ensure_ascii
  dict   -> keys sorted, keys must be str
  list   -> order preserved (order is meaning)
  tuple  -> encoded as list
  set    -> rejected: ValueError naming the offending path
  bool   -> JSON true/false          (checked before int; bool is an int in Python)
  int    -> JSON integer, exact
  float  -> {"__f__": (0.0 if x == 0.0 else x).hex()}
  str    -> JSON string
  None   -> null
  Path   -> rejected: hash the file's content, not its name
  ndarray-> {"__a__": {"dtype": str(a.dtype), "shape": [...],
                       "bytes": sha256(np.ascontiguousarray(a).tobytes()).hexdigest()}}

content_hash(schema, parameters, inputs) -> str
  = sha256( b"nanopnp/hash/v1\0" + schema.encode() + b"\0"
            + canonical(parameters) + b"\0"
            + canonical({name: hash for name, hash in sorted(inputs.items())}) ).hexdigest()

file_hash(path) -> str          # sha256 over the bytes, 1 MiB chunks
```

Three properties follow, and each is a test. The hash is **stable across processes and platforms**,
because nothing in the encoding depends on dict insertion order, `repr` formatting, memory layout or
the filesystem. It **changes under any change to payload or parameters**, because every leaf reaches
the digest. And a **changed input hash changes the output hash**, because input hashes are inside the
digest — which is what makes §5.3.2's "a hand-substituted artefact registers as a changed input"
true by construction rather than by a check somebody must remember to run.

`0.1` encodes as `0x1.999999999999ap-4`; `1e-9` and `0.000000001` encode identically **[tested]**;
`-0.0` and `0.0` encode identically after the normalisation above, which without it they do not.

### Round-trip semantics, stated as an equality

FR-26 and VER-09 are one assertion:

```
c1 = load_case(p)                 # p written by hand
dump_case(c1, q)
c2 = load_case(q)
assert CaseArtefact(c1).hash == CaseArtefact(c2).hash
assert resolve(c1).provenance == resolve(c2).provenance
```

and its negative half, `pytest.raises(CaseValidationError, match=r"electrolyte\.corrections\.diffusivty")`.

The first line is the load-bearing one: because the hash is taken over the validated dump, the
equality holds through comment loss, key reordering, `1` versus `1.0`, flow versus block style and
quoting changes, and fails on any change that would resolve to a different run. The second line is
weaker — two cases can share a provenance dict and differ in a field nothing records — so both are
asserted, not one.

### Why the Deviations group cannot be a default-diff

§5.3.3 requires "every switch set away from the validated default"; §4.5 (PHY-22) fixes what those
defaults are. The nine switches PHY-22 tabulates, plus the three the specification sets elsewhere:

| Switch path in `nanopnp/case/v1` | Validated default | Source |
|---|---|---|
| `physics.model` | `epnp-ns` | PHY-21 |
| `electrolyte.corrections.{diffusivity,mobility,viscosity,permittivity,density}` | on, `willems2020_nacl`, concentration and wall both on | PHY-22 |
| `electrolyte.corrections.steric` | on | PHY-22 |
| `physics.variable_density_flow` | on | PHY-22 |
| `physics.inertia` | on | PHY-22 |
| `physics.dielectric_gradient_forces` | **off** | PHY-22, PHY-23 |
| `numerics.stabilisation` | `none` | NUM-11, §6.4 |
| `numerics.wall_distance.include_analyte` | **off** | PHY-02, WP6 |
| `numerics.linear.solver` | `umfpack` | CON-11 as amended, §6.6 |

`CorrectionSwitches()` constructs all five corrections *off* and `steric` false, so the pydantic field
defaults for the corrections block are the classical model. A `model_dump(exclude_defaults=True)`
diff would therefore report the validated configuration as nine deviations and classical PNP-NS as
none — exactly backwards. `io/defaults.py` holds `VALIDATED_DEFAULT_CASE`, a `CaseDocument` instance
encoding the table above, and

```
deviations(case) -> tuple[Deviation, ...]      # (path, validated_default, value), sorted by path
```

walks `SWITCH_PATHS` and compares. What keeps the table honest is not the walk but the test:
`test_manifest.py` enumerates every field in the schema tree whose annotation is `bool`, a `Literal`,
or a `CorrectionChoice`, and asserts each appears in `SWITCH_PATHS`. Adding a switch in WP12 or WP14
without giving it a validated default fails Tier 1 rather than silently vanishing from the manifest.

### The eight groups, and where each comes from

§5.3.3's groups, mapped onto what exists. A group no stage contributed is written as
`{"status": "not run", "reason": ...}` and never omitted — absence and "did not apply" are different
facts, and `test_manifest.py` asserts all eight keys are present.

| Group | Source in WP7 | Gaps closed later |
|---|---|---|
| Inputs | `file_hash` of every input file; `.hash` of every upstream artefact | — |
| Environment | `importlib.metadata` over the §2.6 distribution list, plus `platform` and `sys.version` | — |
| Geometry and mesh | `continuation.mesh_report(mesh)` — elements, vertices, materials, boundaries | quality statistics and size-field settings: WP8 |
| Charge | not run in WP7 | WP9 |
| Materials | `Electrolyte.provenance`, plus the sha256 of each resolved correction file; clamp activations from `post.report_clamp_activations` | — |
| Solver | `LadderResult.summary()` (rungs, stages, seconds, iterations, minimum damping) and `NewtonSettings` | — |
| Stabilisation | `CoupledModel.provenance["stabilisation"]` | the `reference` mode itself: WP12 |
| Deviations | `io/defaults.deviations(case)` | — |

The distribution names differ from the import names and are worth writing down once:
`ngsolve`, `numpy`, `scipy`, `PyYAML`, `pydantic`, `meshio`, `h5py`, `sympy`, and, when installed,
`MDAnalysis`, `GridDataFormats`, `scikit-image`, `shapely`, `pdb2pqr`, `PySide6`, `gmsh`.

### The stage protocol

```python
class Cancelled(RuntimeError): ...


class Progress(Protocol):
    def __call__(self, fraction: float, message: str) -> None: ...


class CancelToken(Protocol):
    def cancelled(self) -> bool: ...


class Stage(Protocol):
    name: str

    def describe(self) -> StageDescription: ...
    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> Artefact: ...
```

`fraction` is monotone in [0, 1]; for the solve stage it is the rung index over the ladder's nine
stages (NUM-18), refined within a rung by Newton iteration over `max_iterations`. Cancellation is
checked between rungs and inside the `damped_newton` callback, which is the finest granularity that
costs nothing: `newton.py:372` calls the callback unguarded, so raising `Cancelled` there unwinds the
solve without a single line changing in `solve/`.

Caching is the store's, not the stage's: `store.get_or_compute(artefact_key, thunk)` looks the hash
up, returns the stored artefact on a hit, and runs the thunk on a miss. A stage stays a pure function
of its inputs, which is what makes it independently invocable (FR-27) and what makes the Tier-2 cache
test meaningful.

### Store layout

```
<root>/artefacts/<schema-slug>/<hash[:2]>/<hash>/meta.json
                                              /payload.<ext>          # zero or more
<root>/runs/<case-name>-<hash[:12]>/manifest.json
                                   /case.yaml
                                   /qoi.json
```

`meta.json` carries the schema, the parameters, the input hashes, the payload files with their own
hashes, the recorded artefact hash and `created_at`. **`created_at` is outside the digest**: a
timestamp in the hash would make every run a cache miss, which is the whole point of the cache
inverted.

## Work items

| File | Delivers | Identifiers |
|---|---|---|
| `core/hashing.py` | `canonical`, `content_hash`, `file_hash`, `short` | §5.3.2 |
| `core/stages.py` | `Stage`, `StageDescription`, `Progress`, `CancelToken`, `Cancelled`; the lazy name → `"module:attribute"` registry with `register`/`registered_stages`/`create` | FR-27, IF-01 |
| `core/paths.py` (edit) | `store_root()` | — |
| `io/case.py` | `CaseDocument` and its nested models over §5.3.1 as amended; `load_case`, `dump_case`, `CaseValidationError`; `resolve() -> ResolvedCase`; `UnsupportedCaseSection` for the sections Phases 2–3 own, naming the section and the release | IF-03, FR-26, VER-09 |
| `io/defaults.py` | `VALIDATED_DEFAULT_CASE`, `SWITCH_PATHS`, `Deviation`, `deviations()` | FR-25, §4.5 |
| `io/artefact.py` | `Artefact` base and `CaseArtefact`, `MaterialsArtefact`, `SolutionArtefact` | FR-27, §5.3.2 |
| `io/store.py` | `Store` with `put`, `get`, `get_or_compute`, atomic replace, recomputed payload hashes and `hand_substituted` detection | §5.3.2, FR-27 |
| `io/manifest.py` | `Manifest`, `environment()`, the eight-group assembly, `write()` | FR-25, IF-08, §5.3.3 |
| `materials/stage.py` | `MaterialsStage` — §5.2 stage 8, electrolyte specification → resolved coefficient set | IF-01 |
| `solve/stage.py` | `SolveStage` — §5.2 stage 10 over a supplied mesh, driving `default_ladder` and `run_ladder` with progress and cancellation | IF-01, FR-27 |
| `physics/models.py` (edit) | `_deviations` narrowed to the model's own switches, with the docstring pointing at `io/defaults.py` as the manifest's authority | FR-25 |

`io/case.py` is the file the rest of the phase is written against, so the schema is **frozen at the
end of this package**: from here a change to it is a schema version, not an edit.

## Specification changes in this commit

Four amendments and two NOTEs. §5.3.1's example cannot express a Phase-1 run without the first
three, and the fourth removes a reading that silently deletes a boundary condition.

- **A. §5.3.1 gains a top-level `inputs:` block**, naming supplied upstream artefacts by stage —
  `mesh: {path, format, groups: {...}}`, `charge: {...}`, `eps_r: {...}` — with a NOTE recording
  that this is FR-27's hand substitution applied at stage granularity, that a stage whose output is
  supplied does not run, and that nothing upstream of it runs either. Without it the case file has
  no way to name the externally supplied mesh that §8.1 makes Phase 1's whole premise, and §5.2's
  stage-9 input list ("Mesh, charge and dielectric fields, …") has no counterpart in the schema.
- **B. §5.3.1 gains a `physics:` block** — `{model: epnp-ns, flow, variable_density, inertia,
  dielectric_gradient_forces}`. PHY-21 requires the physics model be "selectable by name in the case
  file" and the §5.3.1 example has nowhere to name it.
- **C. §5.3.1's `numerics:` gains `stabilisation: none|reference`.** §5.3.3 requires the manifest to
  record the stabilisation mode and NUM-11 fixes its default; the case file currently cannot set it,
  so WP12's mode would have no way in.
- **D. §5.3.1's `boundary_conditions.walls` values become `{ion_flux: no_flux, slip: no_slip}`**,
  from `{ion_flux: none, slip: none}`. Under the `r`-weighted forms the *natural* condition is the
  free one, so reading `slip: none` as "no slip condition applied" removes no-slip and reads as
  correct while doing the opposite. The schema admits `no_slip | navier | free` and
  `no_flux | prescribed`.
- **E. NOTE under FR-26 / VER-09**: round-trip identity is asserted on the content hash of the
  validated case document and on the resolved provenance, never on the YAML text.
- **F. NOTE under §5.3.2**: the canonicalisation above — validated dump, `float.hex()` with `−0.0`
  normalised, arrays by dtype/shape/content, input files by content and never by path, `created_at`
  outside the digest — and that a stored hash is a cross-check recomputed on load, a mismatch being
  recorded as a hand substitution rather than an abort.

Appendix A rows for IF-01, IF-08, FR-25, FR-26, FR-27 and QR-08 currently read "None yet"; they are
updated by `/wp-implement` in the commit that lands the tests, not here.

Outside the specification, `.knowledge/07-software-stack.md` §6 still advises "Default the bundle to
scipy SuperLU (BSD) and make UMFPACK opt-in" — a scope opinion superseded by the CON-11 amendment of
2 September and by the §6.6 measurement. It is corrected to record the measured fact (SuperLU was
OOM-killed on the reference-sized factorisation) and to drop the recommendation, which does not
belong in `.knowledge/` in any case.

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_case_schema.py` | 1 | VER-09, IF-03, FR-26 | Write → read → resolve yields an identical case hash and identical resolved provenance; an unknown key raises `CaseValidationError` whose message contains the dotted path `electrolyte.corrections.diffusivty` and a suggestion; a future `schema:` fails naming the schema found, before any field error; a Phase-2 section raises `UnsupportedCaseSection` naming the section and the release |
| `tests/tier1/test_artefact_hashing.py` | 1 | FR-27, §5.3.2 | The hash of a fixed document is a stated constant, computed in a subprocess with `PYTHONHASHSEED` varied; every leaf change moves it; `1` and `1.0`, `-0.0` and `0.0`, and reordered keys do not; a `set` is rejected naming its path; a changed input hash changes the output hash; editing a payload file on disk makes the artefact load as `hand_substituted` with the new content hash |
| `tests/tier1/test_manifest.py` | 1 | FR-25, IF-08, §5.3.3 | All eight §5.3.3 groups are present, a group that did not run carrying a reason; `corrections.viscosity.model: none` appears under Deviations (it does not today); the schema-enumeration test fails when a switch-typed field is absent from `SWITCH_PATHS`; `CoupledModel._deviations()` agrees with `io/defaults.deviations()` on the model's own switches; the environment group is populated without `ngsolve` being imported (asserted on `sys.modules`) |
| `tests/tier1/test_stages.py` | 1 | FR-27, IF-01 | `describe()` on every registered stage without importing its module (`sys.modules` again); progress is monotone in [0, 1] and ends at 1; a `CancelToken` that turns true mid-ladder raises `Cancelled` and leaves no partial artefact in the store |
| `tests/tier2/test_artefact_cache.py` | 2 | §5.3.2, QR-08 (partial) | A small `CylindricalPoreGeometry` case solved twice: the second run is a store hit, returns the identical artefact hash and does not re-enter Newton; changing `bias_V` misses; a manifest written from the run names every input hash it consumed |

Tolerances: none of these is numeric. Hashing is exact by construction, and that is the point —
every assertion above is an equality or an exception, so a failure localises to one function. The
one measured quantity in the package is the collision probability of the display prefix, computed in
§Decisions and not tested.

Gate before commit, unchanged:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

## Out of scope

- **Mesh ingestion, tagging and the quality gate** — WP8. `SolveStage` here runs on a mesh built by
  `mesh/primitives.py`; the `inputs.mesh` block is defined and *validated* by this package's schema
  and consumed by the next.
- **External charge and dielectric fields** — WP9. `inputs.charge` and `inputs.eps_r` validate here
  and resolve there.
- **The CLI, XDMF/HDF5 field output and the QR-08 reproducibility test** — WP10. WP7 leaves the
  artefacts and the manifest; it adds no subcommand.
- **Sweeps, warm-start ordering and the index file** — WP11, which is why `Store` has
  `get_or_compute` and atomic writes but no scheduler.
- **The `reference` stabilisation mode** — WP12. `SUPPORTED_STABILISATIONS` stays
  `frozenset({"none"})`, and the schema accepts `reference` only once that changes.
- **Warm-start serialisation of the coefficient vector** — WP10. Phase 0 established that a
  converged solution carries the residual form and the discrete wall-distance field it was assembled
  with; serialising it needs both, and getting that wrong yields a *different operator*, not a slow
  start. It is a package's worth of care, not a corner of this one.

## Open questions

None blocking. Two rulings would be useful before `/wp-implement`, and the plan assumes an answer to
each so that neither stops the work:

1. **Store root.** Assumed `NANOPNP_STORE`, else `./nanopnp-store` in the working directory. A
   platform cache directory (`platformdirs`) would be tidier for the GUI but adds a dependency and
   makes a run's outputs hard to find, so the visible default is assumed.
2. **Whether `inputs:` should also accept an artefact hash** rather than a path, so a case can name
   an artefact already in the store. Assumed **yes**, as `mesh: {artefact: <hash>}` alternative to
   `mesh: {path: ...}`, because WP11's sweeps will otherwise re-hash the same mesh file per point.
   It costs one union member in the schema now and cannot be added after the freeze.
