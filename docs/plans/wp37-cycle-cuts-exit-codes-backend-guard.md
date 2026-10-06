# WP37 — The cycle cuts outside `io`, the exit codes, and the backend guard

**Status: delivered, 6 October 2026.** Written 6 October 2026 on `ccr-60ae37bd-edif2r` at `a346419`, after
WP36 merged. It inherits everything the [current brief](current.md) lists as not to be re-decided,
and in particular:

- WP36's stage protocol and walk (a new stage declares its facts and defines `key`; a test that
  registers a stage restores the registry);
- VER-61's recorded layering and VER-62's golden, which it must keep green.

This is the third work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md). It works
toward `MOD-03`, fixes `MOD-05`, and builds the guard that H3 gives `MOD-10` (§8.2.8 H1, H3, H6, H8,
H11). `SPECIFICATION.md` governs, and the identifiers below are pointers into it. **This commit
amends the specification**:

- §8.2.8 gains H11, the author's ruling on this plan's two scope questions;
- §5.1 gains `numerics/`, and the physics and solve rows shrink to match;
- `CLAUDE.md`'s structure list follows §5.1.

VER-65's row, VER-61's added clause and Appendix A's QR-13 entry are claimed by `/wp-implement`, in
the commit that implements them.

## Execution brief

This brief runs to about 1,600 words, over the 1,200-word target. Each of the eight cuts needs a
decision that names its home and keeps the arithmetic fixed. Splitting the cuts across two
packages would leave VER-61's ratchet half-recorded in between.

### Scope

The measurement in *Design* §1 changed this package's edge list. The phase plan names nine
single-import edges from `MOD-03`'s table, and that list does not reach H6's target. Six of the
nine already point down the accepted order. With all nine cut and `io` split, a `top` cycle of five
subpackages remains: `geometry ↔ mesh` and `physics ↔ solve`. The author ruled (H11):

- the cuts are the `top` edges that point **up** the order, outside `io`;
- the solver kernel becomes a subpackage of its own, `numerics/`, placed after `mesh`.

One PR delivers four things:

- **The cuts (`MOD-03`, outside `io`).** Eight moves, D3 to D10. Afterwards the only `top` edges
  pointing up the order are the `X → io` edges WP38 cuts, and `cli → nanopnp` (D11).
- **`MOD-05`.** The exit classification and codes move to `core/errors.py`, and `cli/errors.py`
  re-exports them. The codes do not change (VER-47).
- **VER-65.** The backend guard of H3.
- **VER-61's ratchet.** A recorded list of upward `top` edges, so a cut cannot come back while
  WP38 and WP39 finish the target.

**Break** (F4; `CHANGELOG.md`): none to `PUBLIC`, which names no moved module. The internal moves
are listed for anyone who imported them (IF-01): eleven modules, D3 to D9.

Pointers:

- §5.1, §5.4.1 NOTE, §8.2.8 H3, H6, H11; QR-13, IF-01, IF-02;
- VER-47, VER-61, VER-62, VER-63, VER-25 (introspection imports no solver);
- the [report](../project/modularity.md)'s `MOD-03`, `MOD-05` and `MOD-10`.

No `OPN-` is open here. The phase plan's open decision on the wall-distance solve's home closes
in D4.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Which edges are cut | Every `top` edge that points up H11's order, unless its target is `io` (WP38's) or it is `cli → nanopnp` (D11). The named downward edges stay: `charge → mesh` (`deployed_mesh`, WP21), `geometry → density` and `physics → mesh`. `materials → charge`, `→ density` and `→ mesh` go anyway, as by-products of D5 and D6 | H11(a). H6's target is acyclicity in the accepted order, so an edge that points down it needs no cut. *Design* §1 |
| D2 | The order | `core`, `structure`, `density`, `symmetry`, `geometry`, `mesh`, **`numerics`**, `charge`, `materials`, `physics`, `solve`, `post`, `io`, `sweep`, `validation`, `cli`, `gui`, `nanopnp`. The YAML header carries it | H11(b). `numerics` imports only `core`, and its lowest consumer after the moves is `charge` |
| D3 | `numerics/` | `solve/gates.py`, `solve/linear.py`, `solve/newton.py` and `physics/measures.py` move to `numerics/` under the same file names, unchanged. `physics/coefficients.py` and `physics/models.py` then import downward. `solve/` keeps `continuation`, `state` and `stage` | H11(b). The four import only `core` and each other (*Design* §1). The kernel is a lower layer whether or not Phase 6 separates forms from solves (`MOD-10`, `MOD-13`), so it is the stable cut. WP39's linear-solver registry lands in `numerics/linear.py` |
| D4 | The wall-distance solve | `mesh/distance.py` becomes `physics/distance.py` | PHY-02 defines `d`, and `physics/coefficients.py` consumes it. From `physics`, both of its imports (`numerics.measures`, `numerics.linear`) point down. Its consumers, `post/forces.py` and `solve/state.py`, sit above it, and `materials/` does not import it, so the corrections import nothing upward (phase plan) |
| D5 | `charge → materials` | Every name of `materials/fields.py` except `blend` and `nearest_solid_permittivity` (with their private helpers) moves to a new `charge/dielectric.py`: the χ field, its derivation, `water_facing`, `MaterialMean`, the summaries and their constants. `materials/fields.py` keeps the ε evaluation | §5.1 already gives `charge/` "dielectric". Stage 7 produces χ (WP30), and physics consumes ε. The moved half is the only user of `charge.fields`, `density.grid` and `signed_area` (*Design* §2) |
| D6 | `geometry → mesh` | `mesh/profile.py` becomes `geometry/profile.py`, and `TOL_NM` moves into it. `mesh/primitives.py` imports `TOL_NM` from there. `geometry/analyte.py` imports `CylindricalPoreGeometry` under `TYPE_CHECKING`, because it is only a field annotation of a frozen dataclass | The profile module imports only `core` and is a polygon, which is FR-08's subject. A cut is a runtime dependency removed. An annotation-only import is that; a deferral into a function is not (D12) |
| D7 | `mesh → materials` | `resolve_wall_size(document, *, permittivity_0)` and `case_debye_length_nm(document, *, permittivity_0)`. `mesh/ingest.py` and `mesh/generate.py` pass `resolved.electrolyte.permittivity_0`. `sweep/plan.py` passes `load_corrections(member.electrolyte.parameters).solvent.permittivity.eps_r0` (a new downward edge, `sweep → materials`) | The same file and the same field as today (`io/case.py` builds the electrolyte from `document.electrolyte.parameters`), so the arithmetic is unchanged |
| D8 | `mesh → physics` via `mesh/ingest.py:79` | `ResolvedCase.model_declaration()` returns `declaration(self.model)`, beside `physics_model()`. `CoupledBoundaries`, `DEFAULT_BOUNDARIES`, `POTENTIAL`, `VELOCITY` and `VELOCITY_AXIS` move to `mesh/primitives.py`, which already owns the boundary vocabulary. `physics/models.py` imports them, so `physics.models.X` still resolves | `DEFAULT_BOUNDARIES` is documented as "the boundary vocabulary of the analytic pore geometry of `mesh/primitives`". The registry lookup goes through `io`, as `physics_model()` already does. WP38 places both methods (handoff) |
| D9 | `MOD-05` | `cli/errors.py`'s contents move whole to `core/errors.py`. `cli/errors.py` re-exports them with `__all__`. `sweep`, `validation` and `gui` import `core.errors`. The table's strings for classes D3 moves are renamed, and no code or class changes | The phase plan. `test_cli.py`'s two-way check catches a stale string. `core` gains the table's string edges, `core → gui` among them, each annotated `MOD-05` |
| D10 | Shims | None at an old path | A shim keeps two homes, and some shims keep the very edge (IF-01: internal paths are not API) |
| D11 | `cli → nanopnp` | Left, and reported to WP39 | `from nanopnp import __version__` and `PUBLIC` read the facade. The edge points up the order but closes no cycle |
| D12 | What counts as a cut | A runtime dependency removed: a definition moved, an argument passed, or an annotation-only import put under `TYPE_CHECKING`. Moving a runtime import into a function is refused by review | `CLAUDE.md`'s import rule. The report's "static relation is reported and not targeted" does not license deferral |
| D13 | VER-65's record | A `backend:` list in `modularity-layering.yaml` of the 12 subpackages that import `ngsolve` or `netgen` in any of the four kinds. That is the 11 at `97f2b3d` plus `numerics` (H11). `backend_imports` gains each import's path, line and kind. The guard compares both ways, naming the module and line of a gain, and naming the subpackage of a loss until the record shrinks | H3. One file holds the layering the guard sits beside. The `sources=` seam lets the oracle substitute a file without touching the tree |
| D14 | VER-61's ratchet | An `upward:` list in the YAML of the `top` edges that point up D2's order, asserted equal both ways. After WP37 it holds the nine `X → io` edges and `cli → nanopnp` | VER-61 pins the static relation, which an annotation-only cut leaves unchanged, so nothing would catch that import returning to module scope. WP38 shrinks the list, and WP39 empties it and adds H6's acyclicity |
| D15 | Numbers and keys | Zero drift: VER-62 at 10⁻⁸, and no artefact key changes. A key that moves, because some key hashes a module path, is an Outcome to report, not a value to re-pin | The moves change no arithmetic. VER-62 G10 |
| D16 | The findings log | `MOD-05` becomes `fixed`, its ruling linking this plan. `MOD-03` stays `accepted`, because WP38 finishes it. `MOD-10` stays `deferred`: VER-65 is H3's guard, not the interface | VER-63 |
| D17 | Release | `v0.5.0-alpha.3`, with a `CHANGELOG.md` section of that name, listing the moves | §2.7; G11 |

### Work items

In dependency order. Each move is one commit that edits `modularity-layering.yaml` (VER-61)
and updates every import, `monkeypatch`/`mock.patch` string, docstring cross-reference, test and
`.knowledge/06` path it touches. Mechanical (Sonnet; `.claude/model-policy.md`), except D5's split,
which needs a reading of WP30's χ code (Opus).

1. `numerics/` (D3): new `__init__.py`; move the four modules; update the exit table's strings.
2. `physics/distance.py` (D4).
3. `geometry/profile.py` and `TOL_NM`; the analyte annotation (D6).
4. `charge/dielectric.py` (D5).
5. `mesh/sizing.py`'s `permittivity_0` (D7).
6. `mesh/ingest.py`: `model_declaration()` and the vocabulary (D8).
7. `core/errors.py` (D9).
8. `validation/modularity.py`: `backend_imports` with lines and kinds; readers for `backend:` and
   `upward:`; the order constant (D2, D13, D14).
9. Tests, the specification rows (VER-65; VER-61's clause; Appendix A for QR-13 and VER-61), the
   findings log, `CHANGELOG.md`, and the phase plan's Outcome.

> **Outcome — the moves landed as one commit.** Each move touches files another touches
> (`physics/models.py`, `io/case.py`, `core/errors.py`'s strings), and VER-61 pins the YAML both
> ways, so a commit per move would need a relation regenerated for a tree no one gates. The code,
> the YAML, the tests and the specification rows land together; the records follow.
>
> **Outcome — measured after the moves.** `upward_edges(import_edges())` is exactly the nine
> `X → io` edges and `cli → nanopnp`, and with the edges out of `io` removed `components` finds
> none: *Design* §1's prediction holds on the real tree. The `edges:` list lost 26 rows and gained
> 14: each consumer's `→ numerics`, `sweep → materials` (D7), and `core → gui`, `→ numerics`,
> `→ sweep`, `→ validation` as string edges of the exit table, annotated `MOD-05` (D9).
>
> **Outcome — D8, the field names.** `mypy --strict` does not let a module re-export a name it only
> imports, so `io/fields.py`, `post/qoi.py`, `post/forces.py`, `validation/apbs.py`,
> `validation/compare.py` and `validation/mms.py` import `POTENTIAL` and `VELOCITY` from
> `mesh.primitives`. `physics.models` keeps `CoupledBoundaries`, `DEFAULT_BOUNDARIES` and
> `VELOCITY_AXIS` in its `__all__`, as before.
>
> **Outcome — D13, the string kind.** A backend string must name a submodule or an attribute
> (`"ngsolve.webgui"`): a bare `"netgen"` is also the mesher's name in the case schema, and counting
> it would have added `io`'s schema and `mesh/adapter.py`'s format table for no coupling. One string
> reference exists, `gui/probe.py:85`; the live set is the twelve D13 predicts.
>
> **Outcome — D7's oracle.** `test_ver53_the_mesher_and_the_sweep_plan_size_the_wall_at_one_eps_r0`
> resolves each of the 15 shipped case files and asserts `resolved.electrolyte.permittivity_0` equals
> the parameter file's `eps_r0` exactly, and the two wall sizes are equal.

> **Outcome — the shipping review, ruled 6 October 2026 (§8.2.8 H12).** `/code-review xhigh` on
> PR #80 raised 13 findings; eight were applied in `5559c7e`. Of the five left, the author ruled:
> `TOL_NM` moves to an import-free `geometry/tolerance.py`, since D6's home loaded pydantic and
> yaml (REV-01; `mesh.primitives` 179 ms → 62 ms); D9's re-export is removed, `core/errors.py`
> being the table's one home as D10 asks (REV-02); the split field vocabulary goes to WP38
> (REV-03); D12 becomes a test, a `deferred_upward:` ratchet holding `gui → nanopnp` (REV-04);
> and D11's `cli → nanopnp`, with `gui → nanopnp`, cites REV-05 for WP39. The rows are in
> [the review register](../project/review-findings.md).

> **Outcome — D15 held.** The seven VER-62 walks pass at 10⁻⁸ against the recorded golden on
> `2400c1b`, in `.claude/hooks/gate.sh run` (extended selection, the GUI test serially), and no
> artefact key moved. The strict documentation build passes.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_backend_guard.py` (new) | 1 | VER-65, QR-13 | The live set equals `backend:`. With `import ngsolve` substituted into a `structure/` module through `sources=`, the guard fails naming `structure`, the module and line 1. With `density/grid.py`'s import removed, it fails naming `density` as lost. Each of the four kinds is caught in a synthetic package |
| `tests/tier1/test_layering.py` | 1 | VER-61 | The YAML equals the relation after every move. The `upward:` list equals the measured upward `top` edges both ways. A `top` import of `mesh.primitives` substituted into `geometry/analyte.py` fails naming `geometry → mesh` |
| `tests/tier1/test_cli.py`, `test_sweep_cli.py` | 1 | VER-47, IF-02 | The exit table is unchanged code for code, and every exception class is classified or excluded |
| The seven VER-62 walks (`test_examples_01`/`02`/`03`/`07`, `test_pipeline_2wcd.py`, `test_exclusion_2wcd_walk.py`; `extended`) | 2 | VER-62 | Zero drift at 10⁻⁸ on the recorded meshes |
| `tests/tier1/test_findings_logs.py` | 1 | VER-63 | `MOD-05` `fixed` with a plan link |
| `tests/tier1/test_mesh_sizing.py` | 1 | §5.3.1 NOTE on `numerics.mesh` | The `auto` wall size of every shipped case, and of a sweep plan's members, equals the value before the move (D7) |

Command: `.claude/hooks/gate.sh run`, then the documentation build of `CLAUDE.md`'s table (VER-45).

### Out of scope

- `io`'s edges and the base/assembler split, including where `physics_model()` and
  `model_declaration()` live: WP38.
- H6's acyclicity assertion, the measured target, and `cli → nanopnp`: WP39.
- Separating forms from solves in `physics/models.py`: Phase 6 (`MOD-10`, `MOD-13`).

### Open questions

None. H11 settled both scope questions on 6 October 2026.

## Design

### 1. The measurement behind the edge list

At `a346419`, `subpackage_relation(import_edges(), kinds=("top",))` has one strongly connected
component of the ten `MOD-03` names. The simulation, in the session's scratchpad and repeatable
from `validation.modularity`, removes:

- the nine named edges;
- `mesh/distance.py`'s two imports;
- every edge out of `io`.

That still leaves `{charge, geometry, mesh, physics, solve}`:

| Edge | Imports that carry it | Direction in D2 |
|---|---|---|
| `geometry → mesh` | `analyte.py:52`, `contour.py:72`, `region.py:70`, `region.py:71` | up |
| `mesh → geometry` | `generate.py:44`, `ingest.py:71`, `reference.py:72` | down |
| `physics → solve` | `coefficients.py:39`, `models.py:88/95/96`, `pb.py:36–38` | up |
| `solve → physics` | 8 imports, from `continuation`, `stage` and `state` | down |
| `mesh → physics` | `ingest.py:79` (`physics.models`) | up |
| `charge → materials` | `charge/stage.py:107`, `:118` | up |

The second simulation remaps the four kernel modules into `numerics`, `mesh.distance` to `physics`
and `mesh.profile` to `geometry`. It also drops the imports D5 to D8 remove. In that relation the
only upward `top` edges are the nine into `io` and `cli → nanopnp`. With the edges out of `io`
removed as well, no component of more than one subpackage remains. WP39 measures the target on
the real tree. The prediction is that it is met, with D11 left for WP39 to place.

`solve/gates.py`, `linear.py` and `newton.py` import `nanopnp.core.{constants, scaling, typing}`
and each other, and nothing else from the package. `physics/measures.py` imports only
`core.typing`. Each defers `ngsolve` to inside its functions, so `numerics` joins VER-65's set.

### 2. Splitting `materials/fields.py`

Its users are:

- `charge/stage.py`, which takes the χ machinery (`DERIVED_CONSTANTS`, `DERIVED_SOURCE`,
  `DerivedSolidFraction`, `MaterialMean`, `SolidFractionField`, `derive_solid_fraction`,
  `derived_summary`, `load_solid_fraction`, `water_facing`, `summary`);
- `physics/models.py`, which takes `blend` and `nearest_solid_permittivity`;
- `gui/render.py`, which takes `SOLID_FRACTION`.

`blend` and `nearest_solid_permittivity` (lines 371–476) use none of `charge.fields`,
`density.grid` or `signed_area`. The split therefore removes `materials → charge`,
`materials → density` and `materials → mesh` together, and leaves `charge → materials` with no
import behind it. `TRANSITION_ID` and `DERIVED_CONSTANTS` move unchanged, so the derived χ
artefact's key does not move (D15).
