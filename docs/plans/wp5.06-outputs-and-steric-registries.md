# WP5.06 — Outputs and steric models as registries

**Status: planned, not started.** Planned 4 November 2026, on `main` after WP5.05's merge (`b5284c1`). It inherits
§8.2.18 T4, §8.2.28 AD3 and AD5, and AH1, ruled at this plan (§8.2.32).

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** The quantities a run can report, and the ways of modelling how crowded ions push each other apart,
become lists that grow by adding one entry, not by editing the case file's format, the extraction step or a physics
model. A new quantity states what it needs of a model, such as solving ion transport or flow, and every model that
meets the need offers it. The step that pulls numbers out of a solution gets one entry point, and four modules share one
check that a named boundary exists. Nothing a user runs today changes: every number and every stored key stays as it is.

**Cost.** About a week. No run gets slower.

**What could go wrong.** A reshuffled extraction could change a reported number or a key; the recorded keys of every
shipped model and the gated example numbers are checked unchanged, to round-off. The two current routes could stop
being compared; the existing checks that compare them on every run stay and must pass unchanged. A second crowding model
could share a key with the validated one; a test requires its key to differ.

**Your call.** None open. You ruled at this plan that a quantity states what it needs of a model, and a model offers
every quantity whose need it meets.

## Execution brief

**Scope.** MOD-09: the outputs registry and the steric-model registry; AD5: one QoI extraction interface and one
boundary-existence check. **Depends on:** WP5.05, merged. **Requirements:** MOD-09; FR-23, QR-04, NUM-24 to NUM-26,
NUM-28; FR-25, FR-27, IF-03; PHY-05, PHY-22; §5.4.3, §5.5; VER-56, VER-61, VER-62, VER-24, VER-71. **Constrained by:**
REV-67 (registering functions stay internal), REV-171 (the cost items stay in Phase 6), VER-56 (no layer reads a
model's name). **Implementing session:** Sonnet, high effort. Tag `v0.6.0-alpha.6`.

**Amended in this commit (AH1):** §5.4.3's NOTE on what a model declares, §5.3.1's NOTE on `outputs:`, VER-56.
**Amended when it lands:** §5.5's registry sentence and a NOTE on the steric model (item 7); MOD-09 `fixed`; REV-171's
seam part recorded as done.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Outputs registry | `post/outputs.py` holds the registry: `register_output(name, *, needs, extract, parameters, export, refusal)`, `registered_outputs()`, `output(name)`, `provided(declaration)`. The six shipped words register there. `io/case.py:OUTPUTS` and the schema's check go; `pipeline/checks.py:check_document` refuses an unregistered word with today's text, and `registry_options("outputs")` reads the registry. The functions stay out of `PUBLIC` | MOD-09, T4; §5.5's rule for `physics.model`; REV-67 |
| D2 Who provides an output | An output's `needs` is a subset of `{"transport", "flow"}`. Transport is `declaration.transport`; flow is `True in declaration.switches["flow"]`. `ModelDeclaration.quantities` goes; `_check_outputs` reads `provided(declaration)`. The shipped lists come out equal to today's | AH1; VER-56 |
| D3 One extraction interface | `post/outputs.py:Extraction` carries the solution, measures, mesh data, the cis-referenced bias, the band, the one `qoi.extract` result (the NUM-26 check inside it, as today) and the merged key parameters. Stage 11 builds it once and calls each selected output's `extract`. Key parameters come from each output's `parameters` and reach `QoIArtefact` as `output_parameters`, which replaces `extension_shell_nm`. Stage 12 exports the outputs marked `export` | AD5; FR-23, QR-04; the stage-11 key's parameters stay the same dictionary |
| D4 Steric registry | `physics/steric.py`: `register_steric_model(name, form)`, `registered_steric_models()`, `steric_form(name)`. A form is `(variables, coefficients, species) -> β̃_i`; `borukhov` wraps `nernst_planck.steric_flux` unchanged. `none` is the off value, offered beside the registry as a correction's `none` is. `Steric.model` becomes `str`, checked in `check_document`. `CorrectionSwitches.steric` becomes the name (`"none"` by default). `species_flux` and `TransportState` take `steric: StericForm | None`; a model's `steric` stays a bool, and `steric_form` is new | MOD-09; PHY-05 is `borukhov`; PHY-22 |
| D5 Keys | No key moves. The electrolyte provenance keeps `"steric"` as a bool, and adds `"steric_model"` only for a name other than `none` and `borukhov`. A model's deviations gain the steric path for such a name too. The schema identifier stays: the documents accepted with the shipped registries are the same set | VER-62 at zero drift; VER-56's `SOLVE_HASHES` and `RUNG_HASHES`; the precedent of `wall_charge_C_m2` in `io/resolved.py:provenance` |
| D6 One boundary check | `numerics/measures.py` gains `has_boundary(mesh, pattern)` and `require_boundary(mesh, pattern, *, error=ValueError)`, by `Mask().NumSet()`, with today's message. The wall distance, the indicator, the reaction flux and the force extension call them, each passing its own exception class. `check_force_surface`, which reads `MeshData`, and the reaction flux's free-DOF check stay | AD5; the existing refusal tests hold their types and text |

### Grounding

**D1.**
- `io/case.py:OUTPUTS` (six words) is read by `CaseDocument._check_installed` and `pipeline/checks.py:registry_options`.
  No test imports it.
- `pipeline/checks.py:check_document` already refuses unregistered `physics.model`, mesher, stabilisation and solver,
  rendered as a document-level schema refusal. `pipeline/case.py:load_case`, `loads_case`, `resolve` and
  `api/case.py:Case.loads`/`with_` call it. So the outputs check keeps its coverage.
- `pipeline/checks.py:options_at` returns `registry_options` where the field has no `Literal`. `cli/reference.py`
  renders the case reference from it.
- `validation/modularity.py:EXTENSION_POINTS` lists `outputs` and `steric models` as `branch` rows homed in `io/case.py`.
  Its `call:` mode reads a registration's first argument as a string constant.
- `sweep/plan.py:RECTIFICATION` strips `rectification` from a member's outputs, as §5.3.1's NOTE requires. It stays.

**D2.**
- `physics/models.py:ModelDeclaration.quantities` is read only by `pipeline/checks.py:_check_outputs`. The coupled
  declaration lists five words, `pnp` three, the electrostatic models none; `fields` is admitted for every model by name.
- `_COUPLED.switches["flow"]` is `(False, True)`; `pnp` and the electrostatic models declare `(False,)`.
  `_COUPLED.transport` is True for `epnp-ns`, `pnp-ns` and `pnp`, False otherwise.
- `tests/tier1/test_model_interface.py:forwarding_model` registers `declaration("pnp")`, unaffected.

**D3.**
- `post/stage.py:QoIStage._prepare` computes the shell when `analyte_force` is selected and the band when the
  declaration has transport. `_check_selection` refuses `rectification`. `_selected` filters
  `QuantitiesOfInterest.summary()` by an always-set and per-word keys. `run` adds `analyte_force` and
  `extension_shell_nm` through `_force`.
- `io/artefact.py:QoIArtefact` puts `extension_shell_nm` into `parameters` only when given. Only `post/stage.py` passes
  it. The artefact hash is schema, parameters and inputs; the summary is not hashed.
- `post/qoi.py:extract` runs both current routes and the per-species check whenever the bias is non-zero. Stage 11
  always calls it for a transport model.
- `ReportStage._exports` returns `("fields",)` when selected.

**D4.**
- `nernst_planck.py:species_flux(..., steric: bool = True)` and `stabilisation.py:advective_velocity` (through
  `TransportState.steric: bool = True`) are the two places `steric_flux` enters a flux.
- `physics/models.py` passes `steric=self.steric` in the residual (`species_flux`), in `transport_states` and in
  `species_fluxes`; `post/qoi.py:indicator_currents` passes `steric=model.steric`.
- `materials/electrolyte.py:CorrectionSwitches.steric: bool`; `for_model` sets True; `without("steric")` sets False
  (used by `solve/continuation.py` for rung 7). `pipeline/case.py:_switches` sets `model != "none"`.
- Tests that pass a bool: `test_nernst_planck.py` (two calls), `test_stabilisation.py:_state`,
  `test_physics_models.py`, `tier2/test_mms.py`, `tier2/test_stabilised_mode.py` (`replace(..., steric=True)`),
  `test_case_schema.py` (asserts `switches.steric is True/False`). `model.steric is True` asserts stay valid.
- `tests/tier1/test_case_leaves.py:SOLVE_PROBES` expects `("none", "borukhov")` at the steric path.

**D5.**
- `materials/electrolyte.py:Electrolyte.provenance` records `"steric": self.switches.steric`; `identity` feeds
  `io/resolved.py:provenance["electrolyte"]`, inside the solve key. `materials/stage.py` writes the same bool into its
  summary. `physics/models.py:provenance` records `switches.steric`; `_deviations` adds
  `electrolyte.corrections.steric.model` when it is off.
- `solve/state.py:OPERATOR_KEYS` compares `model.switches.steric` and `model.materials` on restore, so a name in
  `materials` is compared too.

**D6.**
- `physics/distance.py:wall_distance` checks by `Mask().NumSet()`, raising `ValueError`; `mollify`'s free-DOF check stays.
- `post/indicator.py` checks by integrated length (`_boundary_length`) in `axial_indicator`'s guard and in
  `check_indicator`, raising `IndicatorError`.
- `post/reaction_flux.py:boundary_reaction_flux` checks the field's DOFs on the boundary, raising `ValueError`.
- `post/forces.py:check_extension` (`ExtensionError`) and `_boundary_region` (`ValueError`) check by length and keep
  using the length to normalise.
- Tests: `test_wall_distance.py`, `test_indicator.py`, `test_forces.py` match "no boundary matching" and the class.

### Implementation details

**Item 1 (D4, D5).** In `nernst_planck.py`:
`StericForm: TypeAlias = Callable[[ConcentrationVariables, NondimensionalCoefficients, str], Expression]` and
`borukhov_flux(variables, coefficients, species)`, returning `steric_flux(variables,
packing_coefficients=coefficients.packing_coefficients, volume_ratio=coefficients.steric_volume_ratio(species))`.
`species_flux` and `advective_velocity` call `steric(variables, coefficients, species)` when it is not None.
`physics/steric.py` keeps `_REGISTRY: dict[str, StericForm]`, refuses a duplicate and the name `none`, and runs
`register_steric_model("borukhov", borukhov_flux)` at module level. `steric_form(name)` raises `KeyError` naming the
registered models. In `materials/electrolyte.py`, `VALIDATED_STERIC_MODEL = "borukhov"`, `steric: str = "none"`,
`for_model` sets it, `without` sets `"none"`, and the provenance is
`"steric": self.switches.steric != "none"` plus the conditional `"steric_model"`; `materials/stage.py` writes the same
bool. The model's `steric` is `self.electrolyte.switches.steric != "none"`; `steric_form` is None when off, else
`steric_form(name)`; add it to `TransportModel`. `check_document` refuses a name outside `("none",
*registered_steric_models())`, listing them; `registry_options` returns that tuple at the steric path.

**Item 4 (D1, D2).** `post/outputs.py`:

```python
Need: TypeAlias = Literal["transport", "flow"]
Extractor: TypeAlias = Callable[["Extraction"], Mapping[str, Canonicalisable]]
KeyParameters: TypeAlias = Callable[
    [MeshData, Mapping[str, Canonicalisable]], Mapping[str, Canonicalisable]
]


@dataclass(frozen=True)
class Output:
    name: str
    needs: frozenset[Need]
    extract: Extractor | None = None  # stage 11
    parameters: KeyParameters | None = None  # stage-11 key parameters, at key time
    export: bool = False  # stage 12
    refusal: str | None = None  # refused at one operating point, with this reason
```

`provided(declaration)` returns the sorted names whose needs the declaration meets. The shipped entries: `current`
picks `current_A`, `currents_A`, `conductance_S`; `transport_numbers` picks `transport_number`, `currents_A`; `eof_rate`
picks `eof_m3_s` (each from `extraction.quantities.summary()`, needs transport, `eof_rate` also flow); `rectification`
needs transport and carries `_check_selection`'s text as `refusal`; `analyte_force` needs transport and flow, its
`parameters` return `{"extension_shell_nm": list(shell)}` through `_shell`, and its `extract` returns `{"analyte_force": …, "extension_shell_nm": …}` as `_force` does;
`fields` needs nothing and sets `export`. `_check_outputs` keeps its refusal, reworded to "provides". `SelectionError`, `extension_shell`, `_shell`, `EXTENSION_INNER` and `EXTENSION_OUTER` move from `post/stage.py` to
`post/outputs.py`, since the stage imports the registry; `post/stage.py` imports them back and keeps them in `__all__`,
where `test_qoi_stage.py` imports them.

**Item 5 (D3).** `Extraction` fields: `solution`, `measures`, `data`, `bias_V`, `band_nm`, `quantities`,
`parameters`. `QoIArtefact(..., output_parameters=None)` updates `parameters` after `check_routes`, so the dictionary
equals today's. The summary is `indicator_band_nm`, the always-set of `_selected`, then each selected output's
`extract`, in `outputs` order.

**Item 2 (D6).** Replace each listed check by `require_boundary(..., error=<the class it raised>)` or, for the guard in
`axial_indicator`, `has_boundary`. Keep `_boundary_length` where a length normalises a mean square. In
`boundary_reaction_flux`, call `require_boundary` first, then keep the DOF test, refusing a boundary with no DOFs of the
field as "carries no degrees of freedom of this field".

### Work items

- [ ] 1. `physics/steric.py`, `physics/nernst_planck.py`, `physics/stabilisation.py`, `physics/models.py`,
  `materials/electrolyte.py`, `materials/stage.py`, `pipeline/case.py`, `io/case.py:Steric`, `pipeline/checks.py`,
  `post/qoi.py`; the bool-passing tests of D4's grounding (D4, D5). Done when rows 3 and 4, `test_model_interface.py`,
  `test_case_leaves.py` and `uv run pytest -m tier1` pass. **Executor:** main.
- [ ] 2. `numerics/measures.py:has_boundary`, `require_boundary`; the four call sites (D6). Done when
  `test_wall_distance.py`, `test_indicator.py`, `test_forces.py` and `test_qoi_stage.py` pass unchanged.
  **Executor:** `general-purpose` on Sonnet.
- [ ] 3. Compaction checkpoint. **Executor:** main.
- [ ] 4. `post/outputs.py`; `ModelDeclaration.quantities` removed; `_check_outputs`, `check_document`,
  `registry_options`; `io/case.py:OUTPUTS` removed (D1, D2). Done when row 2 passes. **Executor:** main.
- [ ] 5. `post/stage.py`, `io/artefact.py:QoIArtefact` (D3). Done when row 1 and `test_qoi_stage.py` pass.
  **Executor:** main.
- [ ] 6. `validation/modularity.py:EXTENSION_POINTS`: both rows `registry`, homed in `post/outputs.py`
  (`call:register_output`) and `physics/steric.py` (`call:register_steric_model`); `docs/project/modularity-layering.yaml`
  unchanged unless VER-61 measures a new edge. Done when `test_layering.py` and `test_backend_guard.py` pass.
  **Executor:** `general-purpose` on Haiku.
- [ ] 7. §5.5's registry sentence and a NOTE: `borukhov` is PHY-05 and the validated default, `none` sets `β_i = 0`,
  another registered name is a deviation whose name enters the solve key (D4, D5); FR-23's and §6.7's pointers if they
  name the old list; MOD-09 `fixed` in `modularity-findings.md` and `modularity.md`; REV-171's seam part done;
  `CHANGELOG.md` (`ModelDeclaration.quantities` removed, F4). Done when the code and review say so, and the strict
  documentation build passes. **Executor:** main.
- [ ] 8. `.claude/hooks/gate.sh run`: the VER-62 walks unmoved, no re-pin. **Executor:** main.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_qoi_stage.py::test_mod09_an_output_registered_at_run_time_is_extracted_with_no_schema_edit` | 1 | MOD-09, FR-23 | A fixture registers `probe` (needs transport, extracts `{"probe_A": 2 * current_A}`) and removes it after. `solved.inputs("current, probe")` loads; stage 11's `probe_A` equals `2 * current_A` exactly; its key differs from `[current]`'s. Once removed, `solved.case("current, probe")` is refused naming `probe` and the registered outputs | `uv run pytest tests/tier1/test_qoi_stage.py -k mod09` |
| `tests/tier1/test_model_interface.py::test_ver56_each_model_provides_the_outputs_its_declaration_needs` | 1 | VER-56, AH1 | `provided(declaration(m))`: `epnp-ns`, `pnp-ns` the six words; `pnp` `current`, `fields`, `rectification`, `transport_numbers`; `pb`, `pb-linear`, `poisson` `fields`. With `probe` (needs transport) registered: in `pnp`'s list, and a `pb` case asking it refused naming `pb` | `uv run pytest tests/tier1/test_model_interface.py -k provides` |
| `tests/tier1/test_nernst_planck.py::test_phy05_a_registered_steric_form_enters_the_bracket_with_borukhovs_sign` | 1 | PHY-05, MOD-09 | `steric_form("borukhov")` gives `steric_flux`'s values exactly at `SAMPLE`. A registered `doubled` form: `flux(doubled) − flux(borukhov)` equals `flux(borukhov) − flux(None)` at `SAMPLE`, 1e-12 relative, both components | `uv run pytest tests/tier1/test_nernst_planck.py -k registered` |
| `tests/tier1/test_model_interface.py::test_ver56_a_registered_steric_model_moves_the_solve_key` | 1 | FR-27, FR-25 | The `epnp-ns` quick-start variant naming a registered copy of `borukhov`: its `solve_provenance` differs from the variant's only at `electrolyte.steric_model`, which names it | `uv run pytest tests/tier1/test_model_interface.py -k steric` |
| `test_ver56_the_stage_ten_key_of_each_model_is_the_one_main_recorded` and the `RUNG_HASHES` test | 1 | VER-56, VER-62 | Unchanged goldens | `uv run pytest tests/tier1/test_model_interface.py` |
| `tests/tier2/test_current_routes.py`, `tests/tier2/test_force_routes.py` | 2 | FR-23, QR-04, NUM-26, NUM-28 | Unchanged tolerances | `uv run pytest tests/tier2/test_current_routes.py tests/tier2/test_force_routes.py` |
| The VER-62 walks | 2 | VER-62 | Unmoved at 10⁻⁸, no re-pin | `.claude/hooks/gate.sh run` |

### Out of scope

- A second steric model itself: none ships; one would be a deviation verified against COMSOL first.
- Generalising the sweep's collection of `rectification`: §5.3.1's NOTE names it; it stays in `sweep/plan.py`.
- `MOD-18`'s Geometry views and how the Study suite offers outputs: WP5.11 (T4).
- The coefficient caching and the other cost items: REV-171, Phase 6.
- Making the registering functions public: REV-67, the composer phase.

### Open questions

None. The author ruled AH1 at this plan.
