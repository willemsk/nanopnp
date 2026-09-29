# WP25 — Documentation increment 2: the geometry pipeline and example 06

**Status: delivered, 29 September 2026.** Written 29 September 2026, after WP24 merged (to be tagged
`v0.9.0-alpha.8`). Stages 1–6 exist, run from the CLI and the Geometry tab, and are gated. But the
only prose on them is two paragraphs in `docs/guide/concepts.md`, and no example reaches them. WP25
inherits the VER-46 executor (`nanopnp.validation.examples`, WP16 D8), the generated references
(VER-45, WP16 D5), `with_profile` and the hand-edit route (WP24 D5–D7), and the prepared-2WCD
recipe of `tests/conftest.py` (WP18 D16 Outcome).

This package belongs to [Phase 2, the geometry pipeline](phase-2-geometry-pipeline.md) §WP25, and
discharges phase criterion 5. `SPECIFICATION.md` governs, and every identifier below is a pointer
into it. Where this plan and the specification disagree, this plan is wrong. **Spec amendments,
made in this commit:**

- §8.2.2 gains **B10**, the author's ruling on the map's length unit;
- a new **IF-05 NOTE** gives the length units at the interchange boundary;
- a new **IF-02 NOTE** covers exporting a stored artefact;
- **VER-32**, **VER-46** and **VER-49** are amended;
- Appendix A maps IF-05 to VER-32 and VER-46.

## Execution brief

### Scope

Three deliverables, in this order.

1. **Two code seams.** `nanopnp stage <name> <case> --export PATH` writes a stored artefact in its
   interchange format. This closes the export command that WP18 and WP19 deferred to WP24, and that
   WP24 did not ship. The 3D density map is then written in ångströms (B10).
2. **Two guide pages**, `guide/structures.md` (stage 1) and `guide/geometry.md` (stages 2–6, hand
   edits, exports). They come with the edits that link them in.
3. **Example `06-pdb-to-mesh`**, running from the vendored 2WCD entry to a gated mesh. It is
   executed by VER-46, and its first step shows stage 1 refusing the deposited frame.

Discharges QR-15 in part (Phase 2's documentation increment) and phase criterion 5. Touches IF-02,
IF-04, IF-05, FR-01 to FR-10, FR-27 and QR-12. **The brief is about 1,900 words, over its 1,200
target.** The export command, the unit ruling and the executor's refusal tag each change a
verified contract, so each needs its own decision.

### Requirement and section pointers

| Need | Read |
|---|---|
| The increment | `SPECIFICATION.md` §8.1 documentation table (Phase 2 row); §3.3 QR-15 NOTE |
| Stage contracts to document | §5.2 stages 1–6 and design notes; §5.2.1; §5.2.2; §5.3.1 NOTEs on `structure:`, `geometry.density`, `geometry.contour`, `numerics.mesh`, `inputs:` |
| Executed examples | VER-46; `validation/examples.py`; `tests/tier2/test_examples_0*.py`; `tests/tier1/test_examples_plan.py`; WP16 D8–D11 and Outcomes |
| CLI surface | §3.1 IF-02 NOTEs; VER-32; `cli/__init__.py` `_stage`, `build_parser`; `cli/errors.py` |
| Exporters | `structure/ensemble.py` `AlignedEnsemble.export`; `density/map.py` `export`/`read`; VER-49 |
| Registration and the 2WCD frame | §7.4 NOTE on VAL-05; `.knowledge/04` §1.1, §1.4, §2.1; `tests/conftest.py` `_prepared_rotation` |
| Hand edits | §5.3.1 NOTE on `geometry.contour`; §8.2.2 B9; `io/case.py` `with_profile`; `docs/guide/desktop.md` |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Guide pages | **`guide/structures.md`**, *Structures and trajectories*, covers stage 1: the file contract, chains, selection, ensembles and frames, the axis and its gates, and why preparation is the user's. **`guide/geometry.md`**, *From a structure to a mesh*, covers stages 2–6: the case keys, the variance output, the contour gate, the registration by `centre_z_nm`, the mesher, hand edits and exports. Nav follows *Meshes*. `concepts.md` loses its "first to arrive" wording and links both. `case-files.md`, `meshes.md` and `desktop.md` link them | The §8.1 row names five topics. Stage 1's contract is the densest, and it is where a user first fails |
| D2 | What the guide may state | It says what each stage does and which key steers it. It links the rendered §5.2, §5.2.1 and §5.3.1 NOTEs for formulas and thresholds, and quotes a specification constant only beside that link. **No measured number appears**: `.knowledge/04` §1.3–§1.4 are linked, not transcribed | VER-46's last sentence. WP16 D4: restated summaries drift |
| D3 | Example 06's steps | Refused: `nanopnp stage structure deposited.case.yaml`. Then run: `python prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb` → `nanopnp run 2wcd.case.yaml --store store --run-dir run --upto mesh` → `stage structure … --export aligned.pdb` → `stage structure aligned.case.yaml` (`axis: z`) → `stage density … --export density.mrc` → `stage symmetry … --json` → `stage contour … --export contour.profile.yaml` → `run from-profile.case.yaml --store store --run-dir run-profile --upto mesh` → `inspect run-profile`. The four cases differ only in `structure:` or `inputs.profile` | Every step was prototyped on 29 September 2026 ([Design §3](#3-the-example-prototyped)). Identical electrolytes, because `auto`'s wall size reads the concentration |
| D4 | Preparation | `prepare.py` uses MDAnalysis and NumPy, and imports nothing from nanopnp. It takes chains A–L, protein. **The axis is the eigenvector of the Cα covariance's distinct eigenvalue**; the script refuses when no eigenvalue is distinct. **The sign puts the wide end, the ClyA cap, at +z (*cis*)**. The Cα centroid of residues 8–292 goes to `(0, 0, 5.63)` nm, so the bilayer centre is z = 0 and the case takes the default `centre_z_nm` | Preparation is outside the pipeline (§5.3.1 NOTE on `structure:`), so it must not borrow stage 1's code. The estimate needs only the 10° gate, and stage 1 then finds the exact axis. The registration is VAL-05's (`Z_MD`, §7.4 NOTE). [Design §1](#1-a-preparation-that-needs-no-nanopnp) |
| D5 | Showing the refusal | A README block tagged `<!-- example: refused -->`: every command in it SHALL exit 4, the gate class. The README says the deposited axis is "more than 10° from z", and prints no measured angle | The gate that makes preparation necessary is the lesson; a README that skipped it would teach a work-around |
| D6 | `--export` | On `nanopnp stage <name> <case>`, it runs the walk (cached as usual) and writes the named artefact. The suffix chooses the format: structure `.pdb` (a DCD of every frame is written beside it); density `.npz`, `.dx`, `.ccp4`, `.mrc`, `.map`; symmetry `.npz`; contour `.yaml`, the stored `profile/v1` document byte for byte; mesh `.msh`, the stored MSH 4.1 byte for byte. Any other stage or suffix is a usage error (exit 2), naming the accepted ones, **before** anything runs. The file is written beside its destination and renamed into place. No key moves | An output location, which the IF-02 configuration NOTE permits. Byte-for-byte copies keep the hash a user sees equal to the store's. The atomic write is WP16 D7's rule |
| D7 | Map length unit (**B10**, author ruling, 29 September 2026) | `DensityMap.export` writes origin and spacing in **Å** to OpenDX and CCP4/MRC. `DensityMap.read` converts them back to nm and snaps the origin to the spacing's lattice, which VER-49 already requires. `.npz` stays in nm. `RadialGrid` and `field1` grids stay in nm, as their headers declare | CCP4/MRC define the cell in Å, and viewers read OpenDX in Å. The PDB export is in Å by its format. An nm map overlays its own structure at a tenth of its size |
| D8 | Example 06's oracles | (a) The refusal names the orientation gate, with an angle above 10°. (b) The walk exits 0 through every gate, and the manifest's `artefacts` are exactly case and stages 1–6, with the structure file in `files`. (c) The aligned export passes stage 1 under `axis: z`. (d) `density.mrc`, read in Å as a viewer reads it, boxes every heavy atom of `aligned.pdb`, and its nearest node to each reads at least `exp(−(√3h/2)²/(σR_min)²)` ([Design §2](#2-the-overlay-oracle)). (e) `contour.profile.yaml` equals the stored document byte for byte, and loads with `source: pipeline`. (f) The profile case moves the region and mesh keys, keeps the mesh content hash, and records no stage 1–4 artefact | Each is a property that fails loudly on a frame, unit or substitution error. **Rejected:** the phase plan's "reduced map invariant under the Cₙ rotation", which the harmonic-basis average makes true by construction, so it cannot fail (VER-50 holds that reduction). Also rejected: `reproduce`, which solves the whole case |
| D9 | Tier and budget | `tests/tier2/test_examples_06_pdb_to_mesh.py`, not `slow`. The target is ≤ 90 s serial; the prototype measured about 60 s. It is recorded as an Outcome | One file under `--dist loadfile` adds at most its own wall time to the gate |
| D10 | Executor | `run_tagged` takes the expected exit from the tag: `run` and `plan` expect 0, `refused` expects 4 (`EXIT_GATE` from `cli/errors.py`). A mismatch names both codes. `copy_example` mirrors the `../../` arguments of **every** tagged block. The Tier-1 tag set becomes {`run`, `plan`, `refused`}, and six examples | VER-46 amended. The deposited case's path is mirrored by `prepare.py`'s argument |
| D11 | Public surface | Unchanged. Example 06 is CLI plus a script, and `with_profile` and `ArtefactHook` stay out of `nanopnp.PUBLIC` | **Close call.** WP24 deferred `with_profile`, and the CLI user writes the derived case by hand, as its docstring says. A hook without an API example would be a name nobody is shown |
| D12 | Hand edits in the guide | Two routes are documented: the Geometry tab, and a `profile/v1` document supplied through `inputs.profile`. What the loader does to an exported pipeline profile whose vertices were edited by hand is **run and quoted, not assumed** | WP24 D5: the loader re-checks recorded measurements. The guide must say what actually happens |
| D13 | Generated references | No edit. VER-45's walks already cover `structure.*` and `geometry.*`, and `--export` appears in the CLI reference | WP16 D5 |
| D14 | Housekeeping | `docs/examples/index.md` says six examples, and `mkdocs.yml` gains the three pages. `examples/.gitignore` names `2wcd-prepared.pdb`, `aligned.pdb`, `aligned.dcd`, `density.mrc` and `contour.profile.yaml`. `CHANGELOG.md` gains `0.9.0-alpha.9` | A pattern such as `*.yaml` would hide case files |

> **Outcome — D6: the exporters live in `cli/export.py`.** The suffix table and the payload
> keys are data there, so `stage --help` and the refusal import no stage module, and
> `test_ver32_stage_export_help_imports_no_stage_module` holds that. A structure is staged as a
> directory beside the destination and renamed DCD first, so a PDB on disk always has its
> trajectory. `--list` with `--export` is a usage error.
>
> **Outcome — D7: `.map` never read back.** GridDataFormats guesses its *reader* from the
> extension and has none for `.map`, so `DensityMap.read` failed on a file `export` had just
> written. It now names the reader from the writer's table, and VER-49 covers `.map`
> (`.knowledge/07` §2).
>
> **Outcome — D3: every command passes `--store store`.** Without it, the refusal wrote the
> process-default `nanopnp-store/` into the example directory. The cases also carry the validated
> `corrections:` block, because the schema's defaults are `none` and a case without it lists six
> deviations.
>
> **Outcome — D8 (d): the bound's `R_min` is taken over the heavy atoms present.** Filtering the
> radius table by names not starting with `H` admitted NAD's hydrogens (`NH2T`, 0.2245 Å) and made
> the bound 0.013, which any map passes. Over the 26,844 heavy atoms of the aligned export,
> through the set's own lookup, `R_min` is 0.170 nm and the bound, with √3 × the PDB's 5e-5 nm
> rounding added to the reach, is 0.9275. The lowest nearest-node value measured is 0.9767. The
> test asserts the bound exceeds 0.9, so it cannot go vacuous again. Run by hand, the oracle rejects
> a map read as nm (every atom outside the box), fully transposed (89 % of atoms below the bound)
> and x/y-swapped (57 %) **[tested]**.
>
> **Outcome — D12: a text-edited pipeline profile is refused until its measurements are
> re-derived.** One vertex of the exported 2WCD profile moved by 0.05 nm: `nanopnp run` exits 3,
> naming `provenance.signed_area_nm2` and both values. With `vertex_count`,
> `min_vertex_spacing_nm`, `min_feature_size_nm` and `signed_area_nm2` re-derived it runs, to a new
> region and mesh. The loader checks neither `source` nor `sha256`, so the guide tells a user to set
> `source: hand-edit` and to prefer the Geometry tab, which does both **[tested]**.
>
> **Outcome — D9: 55 s, inside the 90 s target.** The refused block took 2.4 s and the run block
> 51.8 s, serial, on the development machine (WSL2, 29 September 2026), with `OMP_NUM_THREADS=1`.
> Cold `run --upto mesh`: structure 1.4 s, density 17.2 s, symmetry 7.1 s, contour 0.3 s, region
> 0.4 s, mesh 6.8 s; the profile run 8.0 s. Nothing is solved, so no stabilisation mode applies.
>
> **Outcome — D14: the getting-started page named two extras.** The README's "as the
> getting-started page installs it" was untrue for `structure`, so that page now lists all four.

### Work items

1. **`density/map.py`** (D7): convert to Å in `export` and back in `read`, and amend the VER-49
   round-trip test, which reads the raw header through GridDataFormats. Read D7 and the new IF-05
   NOTE first.
2. **`cli/__init__.py`** (D6): the `--export` flag, validated before the walk; one exporter per
   stage, with the atomic write. Add the VER-32 tests. `--help` still imports no stage module.
3. **`validation/examples.py`** (D10): expected exit by tag, and mirroring over every tag. Add the
   Tier-1 executor test.
4. **`examples/06-pdb-to-mesh/`** (D3–D5, D8): `README.md`, `prepare.py`, and four cases
   (`deposited`, `2wcd`, `aligned`, `from-profile`). Read [Design §1](#1-a-preparation-that-needs-no-nanopnp) first.
5. **The tests**: `tests/tier2/test_examples_06_pdb_to_mesh.py`, and
   `tests/tier1/test_examples_plan.py` for six examples and three tags.
6. **The guide** (D1, D2, D12): the two pages, and edits to `concepts.md`, `case-files.md`,
   `meshes.md`, `desktop.md`, `examples/index.md` and `mkdocs.yml`. Then `examples/.gitignore`,
   `CHANGELOG.md`, and the README's status line.
7. **Records**: the phase plan's WP25 entry, `current.md`, and the Outcomes here.

### Verification

| Test | Tier | Identifiers | Assertion / oracle | Tolerance |
|---|---|---|---|---|
| `tests/tier1/test_density.py` (the VER-49 round trip, amended) | 1 | VER-49, IF-05 | The raw header of `.dx` and `.mrc`, read directly by GridDataFormats, holds delta = 10h and origin = 10 × `origin_nm`. `read` returns origin, spacing and shape exactly. An off-lattice file is refused | exact after lattice snap; values within each format's precision |
| `tests/tier1/test_cli.py` (extend) | 1 | VER-32, IF-02, IF-05, FR-27 | Each `--export` pair, on the synthetic C12 tube (stages 1–4) and on the small parallelogram case of `test_mesh_generate.py` (mesh, `size_scale` 20). The contour and mesh files equal the store's bytes. The PDB and DCD reload with the artefact's coordinates. A wrong stage or suffix exits 2 before any stage runs, and leaves no file. No artefact key moves | exact, and PDB precision 5e-5 nm |
| `tests/tier1/test_examples_plan.py` | 1 | VER-46 | Six examples; tags ⊂ {run, plan, refused}. A `refused` command exiting 0, or `run` exiting 4, fails naming both codes (a scratch example running `python -c`) | exact |
| `tests/tier2/test_examples_06_pdb_to_mesh.py` | 2 | VER-46, FR-01–FR-10, FR-27, IF-05, QR-12 | D8 (a)–(f); durations logged | (d) bound computed from the shipped radius set; the rest exact |
| `test_doc_reference.py`, `test_public_api.py` | 1 | VER-45 | Unchanged, and green | — |
| CI `docs` job | — | VER-45 | `mkdocs build --strict` | — |

Commands: the full gate (`.claude/hooks/gate.sh run`);
`uv run pytest tests/tier2/test_examples_06_pdb_to_mesh.py -v --durations=0 --log-cli-level=INFO`;
`uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`.

### Out of scope

- **A trajectory example.** The ensemble lives under `$NANOPNP_REFERENCE_DATA`, which a test may not
  assume. The guide documents the keys and points at the Tier-3 case (`tests/tier3/conftest.py`).
- **`nanopnp prepare`.** Preparation stays outside the pipeline (§5.3.1 NOTE on `structure:`).
- **`reproduce --upto`, and a region export.** Neither is needed by the example.
- **Å for the 2D field grids.** Their headers declare nm, and a change is a Phase 3 decision with the
  charge grids.
- **The charge pipeline's documentation:** Phase 3's increment.
- **The Phase 2 end-of-phase report and the `v0.9.0` tag.** Both wait for criterion 3.

### Open questions

None blocking. B10 was ruled by the author before this commit.

## Outcomes

Delivered 29 September 2026. Every work item is done and none is deferred. The inline Outcomes
above correct D3, D6–D9, D12 and D14.

| Identifier | Test | Result |
|---|---|---|
| VER-49, IF-05 | `tests/tier1/test_density.py::test_ver49_map_round_trip_and_export` | the raw `.dx`, `.ccp4`, `.mrc` and `.map` headers hold 10 × the nm origin and spacing; the grid comes back exactly |
| VER-32, IF-02, IF-05, FR-27 | `tests/tier1/test_cli.py`, the five `test_ver32_stage_export_*` tests | every pair written; profile and mesh equal the store's bytes; PDB within 5e-5 + 1e-6 nm; refusals exit 2 with an empty store and no file; a failed write leaves nothing |
| VER-46 | `tests/tier1/test_examples_plan.py` | six examples; tags {run, plan, refused}; a mismatch names both codes |
| VER-46, FR-01–FR-10, IF-05, QR-12 | `tests/tier2/test_examples_06_pdb_to_mesh.py` | D8 (a)–(f) pass, 55 s |
| VER-45 | `test_doc_reference.py`, `test_public_api.py`, `mkdocs build --strict` | unchanged and green; every new anchor resolves |

## Design

### 1. A preparation that needs no nanopnp

For a Cₙ assembly with n ≥ 3, the Cα covariance commutes with the rotation by 2π/n about the
axis. So it is isotropic in the plane normal to the axis: two eigenvalues are equal, and the axis
is the eigenvector of the third. On the deposited 2WCD (chains A–L, residues all), the eigenvalues
are 7.94, 8.09 and 14.16 nm². That eigenvector lies **0.096°** from stage 1's permutation axis,
which is itself 22.92° from the file's z **[tested]**, 29 September 2026. Real chains fluctuate,
which is why the specification forbids this estimate as *the* axis (the §5.2 stage-1 note). But
preparation needs only the 10° gate, and stage 1 then finds the exact axis.

The sign follows `_prepared_rotation`. Along +a, the top fifth's mean Cα radius is 3.42 nm and the
bottom fifth's is 4.28 nm, so the wide cap is at −a; the script flips it to +z. The rotation takes
the signed axis to z by Rodrigues' formula about `a × ẑ`. Translation then puts the Cα centroid of
residues 8–292 at `(0, 0, Z_MD)`, where `Z_MD` = 5.63 nm (`.knowledge/04` §1.1). Stage 1 keeps
`z = â·x` with its axis through that centroid, so the registration survives the 0.096° residual
tilt to within `5.63 (1 − cos 0.096°)` ≈ 8e-6 nm.

### 2. The overlay oracle

In one frame, the map at an atom's centre is 1. At a grid node a distance `d` away it is at least
`g = exp(−d²/(σR)²)`. The nearest node lies within `d ≤ √3h/2` = 0.0433 nm at h = 0.05 nm. At
σ = 0.93, and taking R ≥ 0.170 nm for heavy atoms (the CHARMM oxygen Rmin/2; the test takes the
minimum over the shipped radius set), `σR` ≥ 0.158 nm. So `g` ≥ exp(−0.0751) = 0.928 **[verified]**.
2WCD has one model, so the frame mean is that frame. A map written in nm, or with its axes in the
wrong order, puts atoms at 5 nm outside a box about 0.6 nm across, and the box assertion fails
before the bound is read.

### 3. The example, prototyped

Run by hand in a scratch directory on 29 September 2026, at `b81c7ba`, with `--all-extras`
**[tested]**:

- `prepare.py` takes 2.8 s.
- The deposited case is refused by the orientation gate at 22.92°, with exit 4.
- `run --upto mesh` takes 35 s cold: structure 1.5 s, density 17.3 s, symmetry 7.1 s, contour
  0.3 s, region 0.5 s, mesh 7.6 s.
- The aligned export passes stage 1 under `axis: z`.
- The stage-4 document copied from the store and supplied through `inputs.profile` meshes in 8.6 s.
  Its region and mesh keys differ from the structure run's, and its mesh content hash is
  identical.

The copy was taken from the path `stage contour --json` prints; D6's `--export` replaces it.
