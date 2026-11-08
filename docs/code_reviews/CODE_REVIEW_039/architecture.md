# CODE_REVIEW_039: the architecture as the tree states it

Written by `.claude/scripts/audit/architecture.py` at `c1f60ca` from `src/nanopnp/` through `nanopnp.validation.modularity`, from the stage registry of `core/stages.py` and from §5.1's module table. 191 modules, 63,024 lines, 1214 module-to-module imports, 133 static subpackage edges and 25 string edges. Nodes are in the layer order of the measuring module, lowest first; `nanopnp` is the package's own `__init__` and `case.py`.

## Summary

| Subpackage | Modules | Lines | Public names | Stages | Static edges out | Static edges in | String edges out |
|---|---|---|---|---|---|---|---|
| `core` | 9 | 1,535 | 104 | — | 1 | 20 | 18 |
| `io` | 13 | 5,298 | 230 | — | 4 | 19 | 0 |
| `structure` | 7 | 1,898 | 71 | 1 structure | 2 | 8 | 0 |
| `density` | 6 | 1,537 | 55 | 2 density | 3 | 8 | 0 |
| `symmetry` | 4 | 445 | 15 | 3 symmetry | 3 | 3 | 0 |
| `geometry` | 8 | 2,924 | 110 | 4 contour, 5 region | 6 | 7 | 0 |
| `mesh` | 12 | 3,411 | 128 | 6 mesh | 3 | 11 | 0 |
| `numerics` | 6 | 1,272 | 54 | — | 1 | 9 | 0 |
| `charge` | 9 | 5,856 | 181 | 7 charge, 7 protonation | 7 | 7 | 0 |
| `materials` | 7 | 1,314 | 56 | 8 materials | 2 | 8 | 0 |
| `physics` | 11 | 3,631 | 109 | — | 5 | 6 | 0 |
| `solve` | 4 | 1,887 | 49 | 10 solve | 7 | 6 | 0 |
| `post` | 8 | 2,774 | 89 | 11 qoi, 12 report | 8 | 5 | 0 |
| `plot` | 4 | 1,822 | 74 | — | 11 | 2 | 0 |
| `pipeline` | 6 | 2,943 | 41 | 9 case | 10 | 6 | 0 |
| `sweep` | 6 | 1,562 | 38 | — | 8 | 2 | 0 |
| `api` | 6 | 2,353 | 30 | — | 9 | 4 | 0 |
| `validation` | 18 | 8,539 | 336 | — | 12 | 2 | 0 |
| `cli` | 11 | 2,852 | 28 | — | 11 | 0 | 7 |
| `gui` | 34 | 9,050 | 248 | — | 14 | 0 | 0 |
| `nanopnp` | 2 | 121 | 0 | — | 6 | 0 | 0 |

## Each subpackage

### `core`

Static imports out: `io` (2). Static imports in: `api` (9), `charge` (21), `cli` (26), `density` (9), `geometry` (12), `gui` (16), `io` (14), `materials` (9), `mesh` (16), `nanopnp` (8), `numerics` (6), `physics` (13), `pipeline` (9), `plot` (2), `post` (9), `solve` (9), `structure` (6), `sweep` (5), `symmetry` (4), `validation` (14). String references out: `api` (7), `charge` (6), `density` (4), `geometry` (5), `gui` (1), `io` (11), `materials` (1), `mesh` (8), `numerics` (2), `physics` (5), `pipeline` (4), `plot` (12), `post` (8), `solve` (4), `structure` (6), `sweep` (2), `symmetry` (1), `validation` (14).

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `core/__init__.py` | 1 | — | Units, constants, validation, provenance, caching and logging. |
| `core/constants.py` | 26 | `ELEMENTARY_CHARGE`, `BOLTZMANN`, `AVOGADRO`, `FARADAY`, `GAS_CONSTANT`, `VACUUM_PERMITTIVITY`, `REFERENCE_TEMPERATURE_K`, `thermal_voltage` | Physical constants in SI units, and the derived thermal voltage. |
| `core/errors.py` | 183 | `EXIT_OK`, `EXIT_UNEXPECTED`, `EXIT_USAGE`, `EXIT_CASE`, `EXIT_GATE`, `EXIT_CONVERGENCE`, `EXIT_CANCELLED`, `EXIT_MEANINGS` and 3 more | The exception to exit-code table, and the classifier over it. |
| `core/hashing.py` | 142 | `Canonicalisable`, `JSONValue`, `HASH_PREFIX`, `SHORT_LENGTH`, `CanonicalisationError`, `canonical`, `decode_floats`, `content_hash` and 2 more | Canonical serialisation and the content hashes every artefact is keyed on. |
| `core/paths.py` | 201 | `PACKAGE_ROOT`, `DATA_DIR`, `CORRECTIONS_DIR`, `GEOMETRY_DIR`, `RADII_DIR`, `CHARGE_DIR`, `STRUCTURES_DIR`, `available_corrections` and 20 more | Filesystem locations of packaged data and of the result store. |
| `core/public.py` | 35 | `PUBLIC` | The public surface and package version. |
| `core/scaling.py` | 217 | `NM_PER_M`, `MOL_PER_M3_PER_MOL_PER_L`, `REFERENCE_DIFFUSIVITY_M2_S`, `REFERENCE_VISCOSITY_PA_S`, `REFERENCE_PERMITTIVITY`, `debye_length_nm`, `Scales` | Nondimensionalisation of the coupled system. |
| `core/stages.py` | 707 | `StageName`, `StageNameLiteral`, `StageIdentifier`, `StageOption`, `Cancelled`, `Progress`, `StageHook`, `SolveHook` and 22 more | The stage protocol, and the registry that introspects stages without importing them. |
| `core/typing.py` | 23 | `Numeric`, `Expression`, `IntegralTerm`, `AssembledForm`, `Mesh`, `Shape`, `FESpace`, `GridFunction` and 1 more | Type aliases for values that cross the numeric/symbolic boundary. |

### `io`

Static imports out: `core` (14), `materials` (3), `numerics` (1), `physics` (1). Static imports in: `api` (19), `charge` (15), `cli` (26), `core` (2), `density` (5), `geometry` (13), `gui` (36), `materials` (2), `mesh` (13), `nanopnp` (3), `physics` (2), `pipeline` (18), `plot` (4), `post` (7), `solve` (5), `structure` (9), `sweep` (11), `symmetry` (5), `validation` (18). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `io/__init__.py` | 1 | — | Case-file schema, result store, provenance manifests. |
| `io/artefact.py` | 541 | `CASE_SCHEMA`, `STRUCTURE_SCHEMA`, `DENSITY_SCHEMA`, `REDUCED_SCHEMA`, `PROFILE_ARTEFACT_SCHEMA`, `REGION_SCHEMA`, `MATERIALS_SCHEMA`, `MESH_ARTEFACT_SCHEMA` and 28 more | Content-addressed stage artefacts (SPECIFICATION.md section 5.3.2). |
| `io/case.py` | 852 | `SCHEMA`, `RETIRED_SCHEMAS`, `FieldType`, `FieldValue`, `CORRECTION_PROPERTIES`, `CaseValidationError`, `UnsupportedCaseSection`, `SuppliedArtefact` and 43 more | The ``nanopnp/case/v0.6`` case-file schema: its shape, its diagnostics, reading and writing. |
| `io/case_paths.py` | 697 | `D`, `UnknownCasePathError`, `FieldReference`, `field_at`, `SEQUENCE_INDEX`, `case_fields`, `case_json_schema`, `schema_leaves` and 14 more | Dotted case-file paths: the schema's fields, reading, checking and substituting. |
| `io/defaults.py` | 320 | `SwitchValue`, `SWITCH_PATHS`, `MODEL_SWITCH_PATHS`, `CONFIGURATION_PATHS`, `VALIDATED_DEFAULT_CASE`, `Deviation`, `ContributedDeviation`, `UnknownSwitchPathError` and 5 more | The validated default configuration, and what it means to deviate from it. |
| `io/manifest.py` | 530 | `MANIFEST_SCHEMA`, `MANIFEST_FILENAME`, `CASE_FILENAME`, `RUN_SCHEMA`, `RUN_RECORD_FILENAME`, `DEVIATIONS_GROUP`, `GROUPS`, `DISTRIBUTIONS` and 11 more | The provenance manifest of SPECIFICATION.md section 5.3.3 (FR-25, IF-08). |
| `io/models.py` | 888 | `MOLECULAR_SCHEMA`, `CONTINUUM_SCHEMA`, `PHYSICS_SCHEMA`, `ModelKind`, `Kind`, `MODEL_KINDS`, `SCHEMAS`, `OWNERS` and 17 more | Named molecular, continuum and physics models: their files, their merge under a study. |
| `io/project.py` | 214 | `PROJECT_SCHEMA`, `PROJECT_FILENAME`, `ITEM_NAME`, `ItemKind`, `ITEM_KINDS`, `FOLDERS`, `INPUTS_FOLDER`, `RUNS_FOLDER` and 17 more | The workbench project file and the paths an item of a project names (FR-32). |
| `io/resolved.py` | 209 | `SOLVE_IRRELEVANT_PROVENANCE`, `SOLVE_ALGORITHM_REVISION`, `ResolvedStructure`, `ResolvedEdit`, `ResolvedProtonation`, `ResolvedCase`, `parse_chains`, `contour_spacing_nm` | The resolved case: the objects a run is made of, as every stage reads them. |
| `io/store.py` | 314 | `logger`, `META`, `FANOUT`, `STALE_STAGING_SECONDS`, `AUXILIARY_SCHEMAS`, `StoreError`, `StaleEntry`, `Store` and 1 more | The content-addressed artefact store (SPECIFICATION.md section 5.3.2). |
| `io/variables.py` | 670 | `FUNCTIONS`, `MAX_EXPRESSION_LENGTH`, `SUFFIX_UNITS`, `DIMENSIONLESS`, `Number`, `Quantity`, `Registry`, `Variable` and 5 more | Case variables: named values with units and formulas of them, resolved to numbers. |
| `io/vocabulary.py` | 13 | `POTENTIAL`, `VELOCITY`, `VELOCITY_AXIS`, `PRESSURE`, `PRESSURE_MEAN` | The field names every layer shares: the solved fields a mesh, a model and an export name. |
| `io/workspace.py` | 49 | `MissingWorkspaceError`, `WorkspaceInUseError`, `require_workspace`, `scratch_directory` | The scratch directory a stage writes its payload into (SPECIFICATION.md section 5.3.2). |

### `structure`

Stages: 1 `structure` (`nanopnp.structure.stage:StructureStage`).

Static imports out: `core` (6), `io` (9). Static imports in: `api` (1), `charge` (6), `cli` (1), `density` (6), `geometry` (3), `gui` (2), `nanopnp` (1), `plot` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `structure/__init__.py` | 20 | — | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection, and structure preparation. |
| `structure/axis.py` | 361 | `SPACING_FRACTION`, `ANGLE_TOLERANCE_DEG`, `ORIENTATION_LIMIT_DEG`, `DISPLACEMENT_BUDGET_NM`, `SymmetryGateError`, `RigidFit`, `kabsch`, `rotation_axis` and 15 more | The Cₙ axis by chain-permutation superposition, its gates and the model frame (FR-01, FR-02). |
| `structure/ensemble.py` | 186 | `PAYLOAD_NAME`, `ATOM_FIELDS`, `CHAIN_CHARACTERS`, `ORIENTATION_RULE`, `EnsembleFormatError`, `chain_characters`, `AlignedEnsemble` | The aligned-ensemble payload of stage 1: coordinates, atom table and axis header. |
| `structure/orient.py` | 226 | `logger`, `DEGENERACY`, `END_FRACTION`, `OFF_AXIS_WARNING_NM`, `orient_pore`, `prepared_pore` | Structure preparation: the pore axis onto z, the named end *cis*, a centroid placed (FR-37). |
| `structure/protonated.py` | 220 | `PAYLOAD_NAME`, `PARENT_PAYLOAD_NAME`, `PARENT_RESIDUE`, `ProtonationTableError`, `RadiusEdit`, `radius_scales`, `residue_radius_scales`, `parent_residue` and 1 more | The protonation artefact's payload: every frame's atoms, charges, radii and states. |
| `structure/read.py` | 556 | `logger`, `ANGSTROM_NM`, `PS_NS`, `STRUCTURE_SUFFIXES`, `TRAJECTORY_FORMATS`, `HISTIDINES`, `WRAP_BOUND_NM`, `COVERAGE_FRACTION` and 13 more | Reading a structure and its ensemble into one MDAnalysis universe (IF-04, FR-03). |
| `structure/stage.py` | 329 | `logger`, `structure_parameters`, `Alignment`, `align`, `StructureStage` | Stage 1: structure ingestion, alignment and the Cₙ axis (FR-01 to FR-03). |

### `density`

Stages: 2 `density` (`nanopnp.density.stage:DensityStage`).

Static imports out: `core` (9), `io` (5), `structure` (6). Static imports in: `charge` (7), `cli` (1), `geometry` (1), `gui` (2), `pipeline` (1), `plot` (3), `symmetry` (4), `validation` (3). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `density/__init__.py` | 1 | — | Gaussian smearing to a grid, ensemble averaging, grid IO. |
| `density/grid.py` | 502 | `GRID_SCHEMA`, `GridFormat`, `NATIVE_FORMAT`, `NM2_TO_M2`, `UNIFORM_TOL_NM`, `GridFormatError`, `RingMaximum`, `RadialGrid` and 9 more | Gridded (r, z) fields: the container, its formats and its interpolant. |
| `density/map.py` | 184 | `PAYLOAD_NAME`, `ANGSTROM_PER_NM`, `GRID_SPACING_RANGE_NM`, `SPACING_TOLERANCE_NM`, `LATTICE_TOLERANCE_NM`, `DensityMap` | The stage-2 payload: the ensemble-mean density map and its npz, OpenDX and CCP4 IO. |
| `density/radii.py` | 278 | `RADII_SCHEMA`, `KERNEL_RADII`, `ANGSTROM_TO_NM`, `WILDCARD`, `DensityInputError`, `RadiusSource`, `RadiusRules`, `RadiusSet` and 5 more | The stage-2 radius set: CHARMM van der Waals radii by residue and atom. |
| `density/stage.py` | 238 | `logger`, `density_parameters`, `atoms_key`, `DensityStage` | Stage 2 of section 5.2: the density map (FR-04, IF-05). |
| `density/union.py` | 334 | `Frames`, `Widths`, `EPSILON`, `LOG_FLOOR`, `CUTOFF_FACTOR`, `GATE_TOLERANCE`, `SLAB_CELLS`, `BATCH_TERMS` and 7 more | Stage 2's field: the ensemble mean of per-frame probabilistic-union densities (FR-04). |

### `symmetry`

Stages: 3 `symmetry` (`nanopnp.symmetry.stage:SymmetryStage`).

Static imports out: `core` (4), `density` (4), `io` (5). Static imports in: `geometry` (2), `gui` (4), `plot` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `symmetry/__init__.py` | 1 | — | C_n averaging, azimuthal reduction to (r, z), variance diagnostics. |
| `symmetry/annular.py` | 112 | `disc_overlap`, `AnnularWeights`, `annular_weights` | Exact cell-annulus overlap weights for the (r, z) binning of stage 3. |
| `symmetry/reduce.py` | 234 | `PAYLOAD_NAME`, `DETREND`, `HARMONICS`, `SLAB_PLANES`, `QUANTITIES`, `ReducedMap`, `harmonic_counts`, `unresolved_radius_nm` and 1 more | Stage 3's computation: the (r, z) mean and the azimuthal variances. |
| `symmetry/stage.py` | 98 | `logger`, `reduction_parameters`, `SymmetryStage` | Stage 3 of section 5.2: symmetry reduction to (r, z). |

### `geometry`

Stages: 4 `contour` (`nanopnp.geometry.contour:ContourStage`); 5 `region` (`nanopnp.geometry.region:RegionStage`).

Static imports out: `core` (12), `density` (1), `io` (13), `mesh` (1), `structure` (3), `symmetry` (2). Static imports in: `charge` (3), `cli` (3), `gui` (7), `mesh` (11), `plot` (5), `post` (2), `validation` (7). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `geometry/__init__.py` | 1 | — | Contour extraction, polyline conditioning, CAD assembly, analyte bodies. |
| `geometry/analyte.py` | 265 | `ANALYTE_DOMAIN`, `ANALYTE_BOUNDARY`, `NM3_PER_M3`, `AnalyteGeometryError`, `AnalyteBody`, `SphereBody`, `SpheroidBody`, `AnalyteInBoxGeometry` and 1 more | Rigid analyte bodies of revolution and the geometries that embed them (FR-21). |
| `geometry/contour.py` | 894 | `logger`, `CONNECTIVITY`, `CLOSING_SPACINGS`, `QUAD_SEGS`, `RESAMPLE_SPACINGS`, `TAUBIN_LAMBDA`, `TAUBIN_MU`, `TAUBIN_PASSES` and 28 more | Stage 4: contour extraction, conditioning and its gate (FR-07, FR-08). |
| `geometry/pore.py` | 141 | `MOUTH`, `CylinderPore`, `IdealisedRegionRecord` | An idealised cylindrical pore: its faces, edge names and stage-5 region record (FR-09). |
| `geometry/probe.py` | 56 | `CHUNK_ELEMENTS`, `probe_radius_profile` | The probe-radius profile that stage 4's radius band is gated against. |
| `geometry/profile.py` | 375 | `PROFILE_SCHEMA`, `PAYLOAD_NAME`, `REFERENCE_SOURCES`, `PIPELINE_SOURCE`, `HAND_EDIT_SOURCE`, `MEASUREMENT_TOL`, `ProfileProvenance`, `PoreProfile` and 10 more | The pore profile fixture: a closed ``(r, z)`` polygon, validated at the boundary. |
| `geometry/region.py` | 1186 | `logger`, `CHORD_DIVISIONS`, `JUNCTION_CLEARANCE_NM`, `MEMBRANE_OVERSHOOT`, `KEY_CONSTANTS`, `PAYLOAD_NAME`, `DOMAINS`, `EXCLUSION` and 33 more | Stage 5: CAD assembly of a pore profile into the tagged region (FR-09). |
| `geometry/tolerance.py` | 6 | `TOL_NM` | The geometric tolerance the analytic geometries and the analyte share. |

### `mesh`

Stages: 6 `mesh` (`nanopnp.mesh.ingest:MeshStage`).

Static imports out: `core` (16), `geometry` (11), `io` (13). Static imports in: `api` (1), `charge` (2), `cli` (4), `geometry` (1), `gui` (2), `physics` (1), `pipeline` (4), `plot` (5), `post` (7), `solve` (3), `sweep` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `mesh/__init__.py` | 1 | — | Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates. |
| `mesh/adapter.py` | 655 | `MESH_SCHEMA`, `TOL_NM`, `FORMATS`, `MeshFormatError`, `MeshDataError`, `detect_format`, `MeshData`, `read` and 4 more | One in-memory mesh, and every way in and out of it (IF-06, section 5.1). |
| `mesh/defaults.py` | 20 | `DEFAULT_PORE_RADIUS_NM`, `DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM`, `DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM`, `DEFAULT_MAXH_NM`, `DEFAULT_WALL_H_NM`, `DEFAULT_CYLINDER_WALL_H_NM` | Canonical sizing and mesh defaults for domain geometries and CLI meshers. |
| `mesh/generate.py` | 288 | `logger`, `COMMON_RECIPE_KEYS`, `MESH_FILENAME`, `WallSizeGateError`, `WallStatistics`, `wall_statistics`, `check_wall_size`, `sizing_parameters` and 4 more | Stage 6's generator: the stage-5 region meshed under the section 5.2.2 size fields (FR-10). |
| `mesh/gmsh_backend.py` | 396 | `logger`, `GmshMeshingError`, `GmshInitialisationError`, `version`, `size_targets`, `short_curve_sources`, `mesh_region` | The optional Gmsh backend of ADR-002: stage 5's region meshed with the ``gmsh`` API. |
| `mesh/idealised.py` | 82 | `IDEALISED_OPTIMISATION_STEPS`, `idealised_parameters`, `generate_idealised`, `mesh_idealised`, `write_gated_msh` | Stage 6 for an idealised pore, and the gated .msh writer behind the mesh command. |
| `mesh/ingest.py` | 758 | `logger`, `MATERIAL_VOCABULARY`, `BOUNDARY_VOCABULARY`, `VOCABULARY`, `FLUID_MATERIALS`, `SOLID_MATERIALS`, `MeshVocabularyError`, `Requirement` and 12 more | Stage 6 of section 5.2: reading a supplied mesh, tagging it, gating it (IF-06, QR-12). |
| `mesh/meshers.py` | 194 | `GMSH_EXTRA`, `Mesher`, `mesh_shape`, `NetgenMesher`, `GmshMesher`, `MesherBuilder`, `register_mesher`, `registered_meshers` and 1 more | The mesher registry and the Mesher protocol (FR-10, QR-14; §5.5). |
| `mesh/primitives.py` | 262 | `CoupledBoundaries`, `DEFAULT_BOUNDARIES`, `PERMITTIVITY_EXEMPT`, `ELECTROLYTE_DOMAINS`, `SlabGeometry`, `CylinderGeometry`, `AxialSlabGeometry`, `CylindricalPoreGeometry` | Analytic benchmark and spike geometries in the (r, z) half-plane. |
| `mesh/quality.py` | 201 | `QUALITY_FLOOR`, `MeshQualityError`, `QualityReport`, `element_quality`, `inverted_elements`, `check_quality`, `check_radii` | Element quality gates: SICN, gamma, and the sign of the Jacobian (VER-10, QR-12). |
| `mesh/reference.py` | 190 | `REFERENCE_PROFILE`, `RESERVOIR_RADIUS_NM`, `MEMBRANE_THICKNESS_NM`, `MEMBRANE_INNER_TRANS_NM`, `MEMBRANE_INNER_CIS_NM`, `WALL_MAXH_NM`, `JunctionReport`, `ReferenceGeometry` and 1 more | The ClyA reference geometry, assembled from a supplied pore profile (FR-09). |
| `mesh/sizing.py` | 364 | `logger`, `WALL_CEILING_NM`, `DEBYE_FRACTION`, `WALL_MEAN_BOUND`, `WALL_MAX_BOUND`, `GATE_CONSTANTS`, `GRADING`, `OPTIMISATION_STEPS` and 25 more | The size fields of section 5.2.2, and the wall target NUM-30 resolves to (FR-10). |

### `numerics`

Static imports out: `core` (6). Static imports in: `charge` (5), `gui` (2), `io` (1), `physics` (15), `pipeline` (2), `post` (7), `solve` (8), `sweep` (1), `validation` (1). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `numerics/__init__.py` | 1 | — | Solver kernel: linear solvers, damped Newton, solver gates, axisymmetric measure. |
| `numerics/defaults.py` | 14 | `DEFAULT_NONLINEAR_RTOL`, `DEFAULT_NONLINEAR_MAX_ITER` | Canonical solver defaults read outside the case schema (the damped-Newton settings). |
| `numerics/gates.py` | 508 | `logger`, `ION_DIAMETER_NM`, `WATER_DIAMETER_NM`, `PACKING_LIMIT`, `INTERIOR_OFFSET`, `PACKING_WARNING`, `GateViolationError`, `FieldSampler` and 13 more | Solver gates asserted at every nonlinear iterate (NUM-17, PHY-06, QR-12). |
| `numerics/linear.py` | 206 | `DEFAULT_SOLVER`, `LinearSolver`, `UmfpackSolver`, `SuperluSolver`, `SolverBuilder`, `register_solver`, `registered_solvers`, `create_solver` and 7 more | Direct linear solves (NUM-10, NUM-21). |
| `numerics/measures.py` | 202 | `Symmetry`, `SINGULAR_MIN_ORDER`, `NGSOLVE_INTEGRATE_ORDER`, `has_boundary`, `require_boundary`, `Measures`, `AXISYMMETRIC`, `PLANAR` and 1 more | Integration measures for the (r, z) half-plane (NUM-04, NUM-07). |
| `numerics/newton.py` | 341 | `logger`, `NewtonSettings`, `DEFAULT_SETTINGS`, `NewtonStep`, `NewtonResult`, `NewtonDivergenceError`, `damped_newton` | Monolithic damped Newton for the coupled system (NUM-16, NUM-17). |

### `charge`

Stages: 7 `charge` (`nanopnp.charge.stage:FieldStage`); 7 `protonation` (`nanopnp.charge.protonation:ProtonationStage`).

Static imports out: `core` (21), `density` (7), `geometry` (3), `io` (15), `mesh` (2), `numerics` (5), `structure` (6). Static imports in: `cli` (3), `gui` (11), `pipeline` (2), `plot` (3), `post` (2), `solve` (2), `validation` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `charge/__init__.py` | 1 | — | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric. |
| `charge/deposit.py` | 561 | `logger`, `GEOMETRY_SCHEMA`, `DEPOSIT_PAYLOAD`, `UNCOVERED_TOL`, `SOLID_SHARE_MIN`, `BARYCENTRIC_TOL`, `LOCATE_CHUNK`, `NM_TO_M` and 13 more | PHY-16 step 6: the lattice deposited on the deployed mesh by ``r``-weighted L2 projection. |
| `charge/dielectric.py` | 487 | `SOLID_FRACTION`, `SOLID_MEAN_FLOOR`, `FLUID_MEAN_CEILING`, `EXCLUSION_MEAN_CEILING`, `EXCLUSION_MATERIAL`, `DERIVED_SOURCE`, `TRANSITION_ID`, `LATTICE_DIVISIONS` and 16 more | The dielectric field: a solid fraction, supplied or derived, for the blend to drive. |
| `charge/edits.py` | 299 | `CHARGE_TOLERANCE_E`, `RADIUS_TOLERANCE_NM`, `POSITION_TOLERANCE_NM`, `EditError`, `TitratableGroups`, `variant_parent`, `edit_records`, `check_targets` and 2 more | Charge edits: PROPKA's titratable groups, an edited table, and its difference from its parent. |
| `charge/fields.py` | 1082 | `FIELD_SCHEMA`, `FIELD_FORMAT`, `Quantity`, `QUANTITIES`, `CANONICAL_UNITS`, `REFUSED_QUANTITIES`, `CHARGE_QUANTITIES`, `DEFAULT_AXIS_CUTOFF_NM` and 32 more | Supplied fixed-charge and solid-fraction fields, and the conservation gate. |
| `charge/kernel.py` | 482 | `logger`, `KERNEL_ID`, `LATTICE_RECORD`, `PATCH_HALF_WIDTHS`, `TILE_NM`, `PLANE_COUNT`, `NM_TO_M`, `SourceAtoms` and 10 more | PHY-16 steps 4-6 on the export lattice: the closed-form azimuthal kernel, summed. |
| `charge/pqr.py` | 396 | `PATCH_RESIDUES`, `MAX_COORDINATE_A`, `MIN_COORDINATE_A`, `PQRError`, `is_hydrogen`, `PQRFrame`, `parse_pqr`, `read_pqr` and 3 more | The PQR file: one reader and one writer for both of stage 7's protonation routes. |
| `charge/protonation.py` | 1456 | `logger`, `FIXED_FLAGS`, `REGISTRATION_TOLERANCE_A`, `COORDINATE_DECIMALS`, `Q_NET_TOLERANCE_E`, `MINIMUM_CALPHA`, `RADIUS_SET`, `ACID_GROUPS` and 14 more | Stage 7, first half: protonation, partial charges and radii per frame (FR-12). |
| `charge/stage.py` | 1092 | `logger`, `CHARGE_PAYLOAD`, `CHARGE_DOCUMENT_PAYLOAD`, `LATTICE_PAYLOAD`, `CHARGE_DOCUMENT`, `CHARGE_GRID_FILE`, `DEPOSIT_FILE`, `EPS_R_PAYLOAD` and 27 more | Stage 7 of §5.2: the fixed-charge and dielectric fields (FR-13, FR-14, FR-27, IF-01). |

### `materials`

Stages: 8 `materials` (`nanopnp.materials.stage:MaterialsStage`).

Static imports out: `core` (9), `io` (2). Static imports in: `api` (1), `io` (3), `physics` (4), `pipeline` (3), `plot` (2), `solve` (2), `sweep` (1), `validation` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `materials/__init__.py` | 1 | — | Electrolyte models and the pluggable correction registry. |
| `materials/corrections.py` | 204 | `SCHEMA`, `NON_COEFFICIENT_KEYS`, `FitBlock`, `PropertyBlock`, `DiffusivityBlock`, `MobilityBlock`, `ViscosityBlock`, `DensityBlock` and 7 more | Loading and validation of ePNP-NS correction parameter files. |
| `materials/electrolyte.py` | 439 | `logger`, `CONCENTRATION_FLOOR_M`, `MOLAR_PER_SI`, `CorrectionChoice`, `NO_STERIC_MODEL`, `VALIDATED_STERIC_MODEL`, `CorrectionSwitches`, `IonSpecies` and 2 more | The electrolyte: reference properties, correction switches and the driver field. |
| `materials/fields.py` | 77 | `blend`, `nearest_solid_permittivity` | The dielectric blend and the nearest-solid permittivity field (section 4.4). |
| `materials/forms.py` | 213 | `MathOps`, `NumpyOps`, `NGSolveOps`, `NUMPY_OPS`, `NGSOLVE_OPS`, `langevin`, `inverse_poly_half`, `poly_jones_dole` and 8 more | The empirical correction forms of PHY-11, written once. |
| `materials/models.py` | 297 | `PropertyKind`, `SPECIES_PROPERTIES`, `CorrectionModel`, `NoCorrection`, `FittedCorrection`, `ModelBuilder`, `register`, `registered_models` and 4 more | The correction-model registry (FR-16, ADR-005, section 5.4.2). |
| `materials/stage.py` | 83 | `MaterialsStage` | Stage 8 of section 5.2: the resolved material coefficient set (IF-01, FR-27). |

### `physics`

Static imports out: `core` (13), `io` (2), `materials` (4), `mesh` (1), `numerics` (15). Static imports in: `io` (1), `nanopnp` (5), `pipeline` (3), `post` (10), `solve` (7), `validation` (6). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `physics/__init__.py` | 1 | — | Weak forms: Poisson, Nernst-Planck, Navier-Stokes; the wall-distance field. |
| `physics/coefficients.py` | 193 | `MESH_LENGTH_UNIT_NM`, `SATURATED_WALL_DISTANCE_NM`, `mesh_unit_scales`, `NondimensionalCoefficients`, `species_concentrations_SI` | Material coefficients of the coupled system, in the NUM-09 variables. |
| `physics/distance.py` | 126 | `DEFAULT_MAX_DISTANCE_NM`, `DEFAULT_DIFFUSION_LENGTH_NM`, `wall_distance`, `mollify`, `gradient_jump` | The wall-distance field (PHY-02, NUM-31). |
| `physics/flow.py` | 157 | `strain_rate`, `axisymmetric_divergence`, `viscous_operator`, `pressure_term`, `continuity_term`, `inertia_term`, `electrical_body_force`, `permittivity_gradient` and 1 more | The flow equations, axisymmetric (PHY-07, PHY-08, NUM-04, NUM-05). |
| `physics/models.py` | 1933 | `logger`, `ElementKind`, `SWITCHES`, `COEFFICIENTS`, `DIRICHLET_BULK`, `LADDER_STRATEGY`, `LADDER_TARGETS`, `equal_order_stabilisations` and 28 more | The physics-model registry (PHY-21, PHY-22, FR-20, section 5.4.3). |
| `physics/nernst_planck.py` | 201 | `ConcentrationVariables`, `packing_fraction`, `steric_flux`, `StericForm`, `borukhov_flux`, `excess_potential_gradient`, `species_flux`, `nernst_planck_residual` | The size-modified Nernst-Planck equations (PHY-04, PHY-05, NUM-02, NUM-04). |
| `physics/pb.py` | 161 | `logger`, `ELECTROLYTE_PERMITTIVITY`, `linear_pb_operator`, `nonlinear_pb_residual`, `solve_pb_recorded` | Poisson-Boltzmann, linear and nonlinear (PHY-21, PHY-24, FR-19). |
| `physics/poisson.py` | 77 | `poisson_operator`, `charge_source`, `surface_charge_term`, `surface_charge_region` | The axisymmetric Poisson operator (PHY-03, NUM-04). |
| `physics/spaces.py` | 27 | `set_boundary_values` | Writing essential data into a finite-element function. |
| `physics/stabilisation.py` | 716 | `STREAMLINE_CUTOFF`, `CROSSWIND_COEFFICIENT`, `GRAD_DIV_COEFFICIENT`, `SHAKIB_CONVECTIVE`, `SHAKIB_VISCOUS`, `STREAMLINE_BONUS_ORDER`, `CROSSWIND_BONUS_ORDER`, `FLOW_BONUS_ORDER` and 24 more | The residual stabilisation registry and its terms (NUM-11, NUM-14, NUM-15). |
| `physics/steric.py` | 39 | `OFF`, `register_steric_model`, `registered_steric_models`, `steric_form` | The registry of steric models: the form of the flux ``beta~_i`` (PHY-05, PHY-22). |

### `solve`

Stages: 10 `solve` (`nanopnp.solve.stage:SolveStage`).

Static imports out: `charge` (2), `core` (9), `io` (5), `materials` (2), `mesh` (3), `numerics` (8), `physics` (7). Static imports in: `api` (1), `gui` (2), `plot` (1), `post` (3), `sweep` (1), `validation` (1). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `solve/__init__.py` | 1 | — | Continuation ladder, warm start, the solve stage. |
| `solve/continuation.py` | 779 | `logger`, `BIAS_ONSET_V`, `FINE_BIAS_STEP_V`, `COARSE_BIAS_STEP_V`, `ELECTRODES`, `LADDER_START_CONCENTRATION_M`, `TransferError`, `Rung` and 10 more | The NUM-18 continuation ladder and the warm start between its rungs. |
| `solve/stage.py` | 377 | `logger`, `LOAD_FRACTION`, `SolveStage` | Stage 10 of section 5.2: the solve (IF-01, FR-25, FR-27). |
| `solve/state.py` | 730 | `STATE_KEY`, `STATE_FILENAME`, `NEWTON_HISTORY_KEY`, `NEWTON_HISTORY_FILENAME`, `DESCRIPTOR_ENTRY`, `WALL_DISTANCE_ENTRY`, `FIELD_PREFIX`, `SOLVE_ONLY_KEYWORDS` and 20 more | Persisting a converged state and restoring or gating it as a warm start (FR-27, QR-08). |

### `post`

Stages: 11 `qoi` (`nanopnp.post.stage:QoIStage`); 12 `report` (`nanopnp.post.stage:ReportStage`).

Static imports out: `charge` (2), `core` (9), `geometry` (2), `io` (7), `mesh` (7), `numerics` (7), `physics` (10), `solve` (3). Static imports in: `gui` (2), `pipeline` (2), `plot` (4), `sweep` (1), `validation` (2). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `post/__init__.py` | 1 | — | QoI extraction: current, transport number, EOF, rectification, forces. |
| `post/export.py` | 556 | `logger`, `EXPORT_SCHEMA`, `OMEGA_STEM`, `OMEGA_W_STEM`, `FIXED_CHARGE_ATTRIBUTE`, `MATERIAL_ID`, `WALL_DISTANCE`, `P2Nodes` and 15 more | IF-07 field export: XDMF with HDF5 heavy data at the P2 node set. |
| `post/forces.py` | 841 | `logger`, `FORCE_ROUTE_TOLERANCE_N`, `ExtensionError`, `ForceDisagreementError`, `ForceSurfaceError`, `axial_extension`, `check_extension`, `maxwell_stress` and 12 more | The axial force on an embedded analyte by three routes (NUM-28, NUM-29). |
| `post/indicator.py` | 133 | `logger`, `IndicatorError`, `smoothstep`, `lumen_band`, `axial_indicator`, `check_indicator` | The domain indicator psi of the NUM-24 current form. |
| `post/outputs.py` | 241 | `EXTENSION_INNER`, `EXTENSION_OUTER`, `Need`, `Extractor`, `KeyParameters`, `SelectionError`, `Extraction`, `Output` and 5 more | The outputs registry: what a run can report, and what each quantity needs of a model (MOD-09). |
| `post/qoi.py` | 507 | `logger`, `TWO_PI`, `ROUTE_AGREEMENT_TOLERANCE`, `RouteDisagreementError`, `indicator_currents`, `stabilisation_currents`, `indicator_eof`, `reaction_flux_currents` and 11 more | Quantities of interest: current, transport number, EOF, rectification (FR-23). |
| `post/reaction_flux.py` | 84 | `boundary_indicator`, `boundary_reaction_flux` | The variational reaction flux (NUM-25). |
| `post/stage.py` | 411 | `logger`, `MEMBRANE_MATERIAL`, `BAND_FRACTION`, `membrane_band`, `QoIStage`, `ReportStage` | Stages 11 and 12 of section 5.2: the quantities of interest, and the report. |

### `plot`

Static imports out: `charge` (3), `core` (2), `density` (3), `geometry` (5), `io` (4), `materials` (2), `mesh` (5), `post` (4), `solve` (1), `structure` (2), `symmetry` (2). Static imports in: `api` (2), `pipeline` (5). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `plot/__init__.py` | 55 | `figure` | Figures of the pipeline's artefacts, drawn from the stored results alone. |
| `plot/data.py` | 816 | `SICN_FLOOR`, `MAX_ATOMS_DRAWN`, `Display`, `DISPLAY`, `axis_label`, `atoms_r_z_m`, `structure_atoms`, `axial_section` and 41 more | Arrays for every figure, read from stored artefacts in SI and the model frame; no drawing. |
| `plot/figures.py` | 454 | `NM`, `text_figure`, `structure_figure`, `density_figure`, `symmetry_figure`, `contour_figure`, `region_figure`, `mesh_figure` and 7 more | One figure per stage artefact, and the sweep's, each built without pyplot. |
| `plot/panels.py` | 497 | `VIEW_NM`, `STREAM_GRID`, `plot_field`, `plot_mesh`, `plot_axial_cutline`, `plot_radial_cutline`, `plot_iv`, `mark_constriction` and 1 more | One panel per view of a solved run, each drawn on a given Axes or a new figure of its own. |

### `pipeline`

Stages: 9 `case` (`nanopnp.pipeline.case:CaseStage`).

Static imports out: `charge` (2), `core` (9), `density` (1), `io` (18), `materials` (3), `mesh` (4), `numerics` (2), `physics` (3), `plot` (5), `post` (2). Static imports in: `api` (14), `cli` (2), `gui` (15), `nanopnp` (1), `sweep` (4), `validation` (4). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `pipeline/__init__.py` | 1 | — | The assembler: case resolution against the registries, the walk, reproduction (§5.1). |
| `pipeline/case.py` | 387 | `load_case`, `loads_case`, `resolve`, `CaseStage` | Loading a case and resolving it to the objects a run is made of. |
| `pipeline/checks.py` | 1074 | `registry_options`, `check_document`, `element_orders`, `options_at`, `PROFILE_KEYS`, `SMEARING_KEYS`, `PROTONATION_KEYS`, `check_species` and 4 more | The case checks that need the installed registries or this release, beyond the schema. |
| `pipeline/extension.py` | 127 | `code_digest`, `FunctionStage` | A stage of one's own: a Python function keyed by its code and the artefacts it reads. |
| `pipeline/forecast.py` | 124 | `FORECAST_SCHEMA`, `Identity`, `keyed_walk` | The keyed walk: every stage's identity for a case, without running a stage. |
| `pipeline/run.py` | 1230 | `logger`, `WORKSPACE_DIRNAME`, `MissingUpstreamError`, `UnknownStageError`, `StageRecord`, `RunResult`, `RecordedRun`, `read_run` and 12 more | The pipeline driver: one case file to one run directory (FR-27, QR-08, IF-01). |

### `sweep`

Static imports out: `core` (5), `io` (11), `materials` (1), `mesh` (2), `numerics` (1), `pipeline` (4), `post` (1), `solve` (1). Static imports in: `api` (5), `cli` (13). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `sweep/__init__.py` | 1 | — | Parameter sweeps, job-array dispatch and result collection (FR-24, SPECIFICATION.md §5.3.4). |
| `sweep/collect.py` | 325 | `logger`, `DATASET_FILENAME`, `DATASET_CSV`, `CSV_NOTE`, `SweepCollectionError`, `read_members`, `collect`, `read_dataset` and 2 more | Collection of the members' records into one dataset, and the rectification (FR-24, FR-23). |
| `sweep/document.py` | 194 | `SCHEMA`, `Assignment`, `Axis`, `SweepDocument`, `loads_sweep`, `load_sweep`, `merged` | The nanopnp/sweep/v0.5 specification document (FR-24, IF-03, §5.3.4). |
| `sweep/forecast.py` | 120 | `Forecast`, `forecast` | What a sweep rebuilds, forecast from the plan before any member runs. |
| `sweep/plan.py` | 804 | `logger`, `PLAN_FILENAME`, `POINT_SCHEMA`, `ID_LENGTH`, `RECTIFICATION`, `WARM_START_BARRIERS`, `SweepPlanError`, `Point` and 6 more | The sweep plan: the points, the warm-start forest, and every check made before a solve. |
| `sweep/run.py` | 118 | `MEMBERS_DIRNAME`, `THREAD_VARIABLES`, `pin_threads`, `MemberResult`, `member_from_row` | A sweep member's record: its dataset row and its file in the sweep directory. |

### `api`

Static imports out: `core` (9), `io` (19), `materials` (1), `mesh` (1), `pipeline` (14), `plot` (2), `solve` (1), `structure` (1), `sweep` (5). Static imports in: `cli` (23), `gui` (8), `nanopnp` (5), `validation` (6). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `api/__init__.py` | 1 | — | The Python interface: a Case to build and edit, and a Session to run it. |
| `api/case.py` | 410 | `DEFAULT_OUTPUTS`, `CaseSource`, `Case` | The case document as a Python object: read, edited by copy, and built from presets. |
| `api/project.py` | 709 | `ProjectError`, `Problem`, `Project` | A workbench project: a plain folder of models, studies, inputs, runs and results (FR-32). |
| `api/reproduce.py` | 369 | `logger`, `DEFAULT_TOLERANCE`, `InputMovedError`, `ReproductionError`, `Drift`, `EnvironmentDrift`, `Reproduction`, `compare` and 4 more | QR-08 made executable: re-run an archived run directory and compare its numbers. |
| `api/session.py` | 364 | `StageInfo`, `CaseCheck`, `Session` | The Session: the one object that runs a case, for the command line, the shells and Python. |
| `api/sweep.py` | 500 | `logger`, `BASE_FILENAME`, `SWEEP_FILENAME`, `SweepResult`, `Sweep`, `sweep`, `plan_sweep`, `run_point` and 1 more | A one-axis sweep of a case held in Python, and the executor that runs a planned sweep. |

### `validation`

Static imports out: `api` (6), `charge` (2), `core` (14), `density` (3), `geometry` (7), `io` (18), `materials` (2), `numerics` (1), `physics` (6), `pipeline` (4), `post` (2), `solve` (1). Static imports in: `cli` (25), `gui` (1). String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `validation/__init__.py` | 1 | — | Benchmarks, MMS, COMSOL comparison harness, regression fixtures. |
| `validation/apbs.py` | 1446 | `logger`, `APBS_GROUP`, `REQUIRE_APBS`, `NM_TO_ANGSTROM`, `SPACING_NM`, `DIME`, `NLEV`, `CHARGE_MARGIN_NM` and 57 more | VAL-06: our Poisson solve against APBS's, on maps of the same problem. |
| `validation/attribution.py` | 604 | `ATTRIBUTION_SCHEMA`, `IDENTITY_TOLERANCE`, `Verdict`, `LadderError`, `Rung`, `LADDER`, `DELTA_LABELS`, `RungOutcome` and 6 more | The attribution ladder: which part of a discrepancy could be a defect (VAL-01, VAL-04). |
| `validation/case_leaves.py` | 378 | `KINDS`, `Leaf`, `unclassified`, `LEAVES` | Classification of every case schema leaf by what reads it (VER-71). |
| `validation/charge.py` | 192 | `NM_TO_M`, `ALIGNMENT_TOL`, `PlaneDifference`, `AreaComparison`, `reference_construction`, `compare_areal` | The deposited fixed charge against the reference's own table (VAL-15 at Tier 3). |
| `validation/charged_tube.py` | 122 | `write_parallelogram_profile`, `CHARGED_TUBE_ATOMS`, `CHARGED_TUBE_RADIUS_A`, `CHARGED_TUBE_SECOND_FRAME_E`, `write_charged_tube`, `write_dielectric_tube` | The two-atom charged tube: the case the workbench's fixture states and the tests walk. |
| `validation/compare.py` | 398 | `PRESSURE_FIELD`, `VELOCITY_COMPONENTS`, `COMPARED_QUANTITIES`, `FieldComparison`, `QoIComparison`, `probe_domains`, `sample_on_probe`, `compare_fields` and 5 more | VAL-01 and VAL-02: what a solution and a golden differ by, and where. |
| `validation/comsol.py` | 777 | `GOLDEN_SCHEMA`, `MANIFEST_NAME`, `ARCHIVE_NAME`, `ARCHIVE_MANIFEST_NAME`, `Refinement`, `GoldenSource`, `SignReference`, `POTENTIAL_UNIT` and 24 more | The ``nanopnp/golden/v0.5`` archive: a COMSOL export turned into evidence (VAL-03). |
| `validation/costs.py` | 614 | `logger`, `A1_THRESHOLD_GB`, `A8_THRESHOLD`, `A16_THRESHOLD`, `A1_FRAME_COUNTS`, `A1_PROJECTED_FRAMES`, `STAGE_TOTAL_TOLERANCE`, `THREAD_VARIABLES` and 21 more | The cost study: three suspected costs measured against thresholds fixed before measuring. |
| `validation/examples.py` | 216 | `logger`, `TAGGED_BLOCK`, `CONSOLE_FENCE`, `PROGRAMS`, `EXPECTED_EXIT`, `UP`, `GENERATED`, `ExampleCommandError` and 5 more | Execute the worked examples' documented commands, verbatim (VER-46). |
| `validation/findings.py` | 105 | `REPOSITORY`, `COLUMNS`, `FRONT_MATTER`, `Row`, `FindingsLog`, `LogFormatError`, `front_matter`, `parse_log` | Read the findings logs under ``docs/``, for the layering guard (VER-61). |
| `validation/geometry.py` | 612 | `logger`, `Leg`, `PLANE_SPACING_NM`, `TIP_BAND_NM`, `CONSTRICTION_WINDOW_NM`, `Z_MD_NM`, `Z_MD_TOLERANCE_NM`, `REGISTRATION_RESIDUES` and 24 more | VAL-05: a generated pore polygon against the delivered reference polygon. |
| `validation/mms.py` | 440 | `Symbolic`, `RADIAL`, `AXIAL`, `ConstantCoefficients`, `constant_coefficients`, `ManufacturedSolution`, `to_coefficient_function`, `weighted_l2_error` and 1 more | Manufactured solutions for the coupled axisymmetric system (VER-18). |
| `validation/modularity.py` | 1683 | `PACKAGE`, `LAYERING`, `ROOT_NODE`, `ROOT_MODULES`, `KINDS`, `STATIC_KINDS`, `RELATIONS`, `MODULE_STRING` and 63 more | Measure the package's structure from its source, for the modularity report. |
| `validation/okf.py` | 59 | `REPOSITORY`, `INDEX_ENTRY`, `navigation`, `splice_navigation` | Build the documentation navigation of an OKF bundle from its index pages. |
| `validation/probe.py` | 415 | `PROBE_SCHEMA`, `DEFAULT_MARGIN_NM`, `COMSOL_LENGTH_SCALE_M`, `ProbeGridError`, `ProbePatch`, `ProbeDocument`, `loads_probe`, `load_probe` and 1 more | The ``nanopnp/probe/v0.5`` comparison surface: where Tier 3 samples both solutions. |
| `validation/runs.py` | 180 | `SOLVE_STAGE`, `RunError`, `ReopenedRun`, `reopen` | Reopening a finished run for the Tier-3 comparison, without re-solving it. |
| `validation/stability.py` | 297 | `SCHEMA`, `SAME_MESH_TOLERANCE`, `SAFETY_FACTOR`, `CEILING`, `REFERENCE_ENVIRONMENT`, `MeshEntry`, `WalkGolden`, `StabilityGolden` and 9 more | The number-stability golden: one walk's numbers against the meshes they were recorded on. |

### `cli`

Static imports out: `api` (23), `charge` (3), `core` (26), `density` (1), `geometry` (3), `io` (26), `mesh` (4), `pipeline` (2), `structure` (1), `sweep` (13), `validation` (25). Static imports in: none. String references out: `api` (4), `core` (1), `gui` (1), `io` (2), `physics` (1), `pipeline` (1), `structure` (1).

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `cli/__init__.py` | 70 | `main` | Command-line entry points (IF-02). |
| `cli/building.py` | 191 | `register` | The geometry and mesh commands. |
| `cli/common.py` | 170 | — | Helpers shared by the command modules of the command line. |
| `cli/export.py` | 127 | `EXPORTS`, `refusal`, `export_artefact` | ``nanopnp stage <name> <case> --export PATH``: a stored artefact in its interchange format. |
| `cli/parser.py` | 53 | `build_parser` | The argument parser, assembled from the command modules. |
| `cli/reading.py` | 341 | `SECTIONS`, `DATASET_QUANTITIES`, `format_value`, `stage_line`, `run_lines`, `section_lines`, `dataset_lines`, `artefact_lines` and 1 more | Text readings of a run, a sweep dataset and a stored artefact, for `nanopnp inspect`. |
| `cli/reference.py` | 404 | `USAGE_WIDTH`, `API_SECTIONS`, `render_case_reference`, `FIELD_MODELS`, `render_field_reference`, `command_parsers`, `render_cli_reference`, `render_exit_codes` and 1 more | Renderers for the generated reference pages of the user documentation. |
| `cli/running.py` | 507 | `register` | The run, stage, inspect, plot and reproduce commands. |
| `cli/sweeping.py` | 220 | `register` | The sweep command: plan, run and collect. |
| `cli/validating.py` | 458 | `register` | The validate command: case checks and the COMSOL comparison harness. |
| `cli/workbench.py` | 311 | `register` | The gui, project, store and env commands. |

### `gui`

Static imports out: `api` (8), `charge` (11), `core` (16), `density` (2), `geometry` (7), `io` (36), `mesh` (2), `numerics` (2), `pipeline` (15), `post` (2), `solve` (2), `structure` (2), `symmetry` (4), `validation` (1). Static imports in: none. String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `gui/__init__.py` | 1 | — | Desktop application (PySide6 shell over the stage objects, ADR-004). |
| `gui/app.py` | 217 | `logger`, `PLOT_INTERVAL_MS`, `MainWindow`, `main` | The desktop shell (IF-09): a window over the view-models, and nothing more. |
| `gui/assess.py` | 326 | `logger`, `Record`, `Refusal`, `Assessment`, `Seed`, `AssessRequest`, `Assessed`, `Seeded` and 6 more | The contour editor's measuring side: one spawned process, the §5.2.1 criteria, plain data. |
| `gui/case_model.py` | 308 | `FieldKind`, `Absent`, `ABSENT`, `FieldState`, `CaseEditor` | The case editor's view-model: a case file, its fields, and what may be typed into them. |
| `gui/charge.py` | 576 | `CHARGE_STAGES`, `BUILD_UPTO`, `MAX_PIXELS`, `BuildOffer`, `build_offer`, `charge_stages`, `block_size`, `ChargeMap` and 10 more | The charge tab's view-model: stage 7 as it lands, its pictures, and its records. |
| `gui/convergence.py` | 297 | `Series`, `RESIDUAL`, `UPDATE`, `ConvergenceState`, `MAX_POINTS_PER_BAND`, `Step`, `Band`, `ConvergenceModel` | The convergence plot's view-model: what the ladder did, and what may be claimed of it. |
| `gui/geometry.py` | 838 | `GEOMETRY_STAGES`, `BUILD_UPTO`, `STAGE_1_FRAME`, `MODEL_FRAME`, `StageStatus`, `StageRow`, `planned_stages`, `can_build` and 19 more | The geometry tab's view-model: stages 1-6 as they land, their pictures, the contour editor. |
| `gui/probe.py` | 465 | `logger`, `PAYLOADS`, `LICENCE_NOTICE_FILENAME`, `SELFTEST_TIMEOUT_MS`, `licence_notice`, `PayloadError`, `FRAGMENT`, `FRAGMENT_Q_NET_E` and 6 more | The packaging probe: the binary payloads of RSK-13, in one process. |
| `gui/render.py` | 678 | `logger`, `RENDERER_VERSION`, `RENDERER_INTEGRITY`, `RENDERER_DIRECTORY`, `RENDERER_SOURCE`, `VIEWER_DIRNAME`, `MESH_SCENE_STEM`, `ChargeQuantity` and 20 more | The field viewer's render side: one spawned process, one scene, written as a file. |
| `gui/run_model.py` | 257 | `RunState`, `RecordValue`, `RunOutcome`, `run_outcome`, `RunModel`, `RunControl` | Run control: the state machine over a background solve, and what it read back. |
| `gui/scene.py` | 165 | `SceneState`, `SceneModel` | The field viewer's view-model: which field, which file, and whether it drew. |
| `gui/solver.py` | 365 | `logger`, `RunRequest`, `Started`, `Stage`, `Produced`, `Rung`, `Iteration`, `Progress` and 11 more | The bridge between the shell and a solve: one spawned process, plain data both ways. |
| `gui/web/__init__.py` | 1 | — | The browser workbench: a local server and its screens (ADR-004; needs the ``gui`` extra). |
| `gui/web/assets.py` | 15 | `ASSETS`, `TOKENS` | Where the workbench's static files are: the assets folder and the design tokens. |
| `gui/web/commands.py` | 114 | `MENUS`, `Command`, `COMMANDS`, `PALETTE_ALSO`, `BROWSER_KEPT`, `command`, `bindings`, `chords` and 1 more | The workbench's command registry: one list for the menus, the palette and the shortcuts. |
| `gui/web/frame.py` | 520 | `KINDS`, `PANELS`, `RAIL_FOLDED_PERCENT`, `RAIL_LIMITS`, `BOTTOM_LIMITS`, `GLOSSARY`, `listed_changes`, `frame` | The workbench's frame: title bar, activity bar, project rail, bottom panel and their commands. |
| `gui/web/link.py` | 196 | `STRIP_MIN_CHARGE_E`, `REACH_WIDTHS`, `residue_key`, `Extent`, `png`, `Link` | The link between a residue on the molecule and its charge on the (r, z) map, and back. |
| `gui/web/overlay.py` | 208 | `SYSTEM`, `FOLLOW`, `DENSITIES`, `SPACINGS`, `BACKGROUNDS`, `Overlay` | The settings overlay: theme, density, spacing, the 3D view's background and the key bindings. |
| `gui/web/pages.py` | 212 | `MAP_WIDTH_PX`, `BLANK`, `STYLESHEETS`, `install` | The workbench's pages, written in NiceGUI over the server's FastAPI app. |
| `gui/web/queue.py` | 53 | `Status`, `Entry`, `Queue` | The workbench's run queue and log, kept by the server for the bottom panel. |
| `gui/web/screens.py` | 109 | `Screen`, `Suite`, `SUITES`, `FRAME_CONTROLS`, `SCREENS`, `screen` | The workbench's screen registry: each screen's path and the controls it declares. |
| `gui/web/server.py` | 362 | `HOST`, `READY`, `COOKIE`, `track`, `Guard`, `build_app`, `ANNOUNCE_WAIT_S`, `dev_app` and 2 more | The workbench's local server: loopback only, one ready line, a token, stops with its input. |
| `gui/web/settings.py` | 57 | `SETTINGS_FILENAME`, `logger`, `Settings`, `write_atomically`, `load`, `save` | The user's workbench settings: theme, density, spacing, viewer background and key bindings. |
| `gui/web/shell.py` | 30 | `Shell` | What the workbench's pages share: the project or case now open, and the user's settings. |
| `gui/web/states.py` | 121 | `STATES`, `NO_STRUCTURE_CHARGE`, `Workbench`, `boot_case`, `boot_project`, `boot` | The fixture states ``nanopnp gui --state`` boots, and the walk of a case into a state. |
| `gui/web/theme.py` | 177 | `THEME_SCHEMA`, `THEMES_FOLDER`, `NAME`, `HEX`, `TOKEN_NAME`, `logger`, `Theme`, `shipped` and 7 more | The workbench's themes: the two shipped with the tokens, and the user's own. |
| `gui/widgets/__init__.py` | 21 | — | The Qt half of the shell: widgets over the view-models, and no logic of its own. |
| `gui/widgets/case_editor.py` | 264 | `SPIN_DECIMALS`, `SPIN_INT_RANGE`, `CaseEditorWidget` | The case form, built from the schema at run time (IF-09). |
| `gui/widgets/charge.py` | 638 | `logger`, `POLL_INTERVAL_MS`, `PANES`, `ChargeCanvas`, `ChargeWidget` | The Charge tab: stage 7 as it lands, its pictures and its records. |
| `gui/widgets/convergence.py` | 180 | `MARGIN`, `ConvergencePlot`, `ConvergenceWidget` | The live convergence panel: two hand-stroked polylines, banded by rung. |
| `gui/widgets/geometry.py` | 937 | `logger`, `POLL_INTERVAL_MS`, `Point`, `GeometryCanvas`, `GeometryWidget` | The Geometry tab: stages 1 to 6 as they land, and a hand edit of the contour. |
| `gui/widgets/result.py` | 68 | `ResultWidget` | The result panel: the scalars, and the deviations they were produced under. |
| `gui/widgets/run_control.py` | 113 | `POLL_INTERVAL_MS`, `RunControlWidget` | The run panel: start, cancel, progress and the log, over the run-control view-model. |
| `gui/widgets/viewer.py` | 161 | `POLL_INTERVAL_MS`, `ViewerWidget` | The field viewer: a web view over a scene file, and a probe that says whether it drew. |

### `nanopnp`

Static imports out: `api` (5), `core` (8), `io` (3), `physics` (5), `pipeline` (1), `structure` (1). Static imports in: none. String references out: none.

| Module | Lines | Public names | First docstring line |
|---|---|---|---|
| `__init__.py` | 46 | — | nanopnp: continuum simulation of biological nanopores with the ePNP-NS framework. |
| `case.py` | 75 | — | The case and its blocks: build a case in Python, or read one from a file. |

## §5.1's module table against the tree

§5.1 lists 20 modules; the tree has 20 subpackages.

In the tree and not in §5.1's table: none.
In §5.1's table and not in the tree: none.

| Module | §5.1 says | The package docstring says | Modules |
|---|---|---|---|
| `core/` | Units, constants, validation, provenance, caching, logging | Units, constants, validation, provenance, caching and logging. | 9 |
| `io/` | Case-file schema, artefact and resolved-case types, the solution-field vocabulary, result store, provenance manifests: the base every stage imports, importing only `core` at run time (`MOD-04`; WP38) | Case-file schema, result store, provenance manifests. | 13 |
| `structure/` | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection, and structure preparation. | 7 |
| `density/` | Gaussian smearing to grid, ensemble averaging, grid IO | Gaussian smearing to a grid, ensemble averaging, grid IO. | 6 |
| `symmetry/` | Cₙ averaging, azimuthal reduction to (r, z), variance diagnostics | C_n averaging, azimuthal reduction to (r, z), variance diagnostics. | 4 |
| `geometry/` | Contour extraction, polyline conditioning, CAD assembly, analyte bodies | Contour extraction, polyline conditioning, CAD assembly, analyte bodies. | 8 |
| `mesh/` | Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates | Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates. | 12 |
| `numerics/` | Linear-solver adapters, damped Newton, the state and increment gates, the axisymmetric measure (§8.2.8 H11) | Solver kernel: linear solvers, damped Newton, solver gates, axisymmetric measure. | 6 |
| `charge/` | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric. | 9 |
| `materials/` | Electrolyte models and the pluggable correction registry | Electrolyte models and the pluggable correction registry. | 7 |
| `physics/` | Weak forms: Poisson, Nernst–Planck, Navier–Stokes; the wall-distance field | Weak forms: Poisson, Nernst-Planck, Navier-Stokes; the wall-distance field. | 11 |
| `solve/` | Continuation ladder, warm start, the solve stage | Continuation ladder, warm start, the solve stage. | 4 |
| `post/` | QoI extraction: current, transport number, EOF, rectification, forces | QoI extraction: current, transport number, EOF, rectification, forces. | 8 |
| `plot/` | Figures of every stage's artefact and of a sweep, drawn from the stored results alone with Matplotlib (the `plot` extra); imports no backend (§8.2.14 P3) | Figures of the pipeline's artefacts, drawn from the stored results alone. | 4 |
| `pipeline/` | Case resolution and the checks against the registries, the pipeline walk: the assembler, which imports the stages (`MOD-04`; WP38) | The assembler: case resolution against the registries, the walk, reproduction (§5.1). | 6 |
| `sweep/` | Sweep documents, planning and result collection; the members run through the `Session` (`api/`) | Parameter sweeps, job-array dispatch and result collection (FR-24, SPECIFICATION.md §5.3.4). | 6 |
| `api/` | The Python interface: the `Case`, the `Session` that runs, sweeps and reopens it, and reproduction; the command line, the shell and the sweep runner run through it, above `sweep/` (IF-01; §8.2.23 Y4) | The Python interface: a Case to build and edit, and a Session to run it. | 6 |
| `validation/` | Benchmarks, MMS, COMSOL comparison harness, regression fixtures | Benchmarks, MMS, COMSOL comparison harness, regression fixtures. | 18 |
| `cli/` | Command-line entry points | Command-line entry points (IF-02). | 11 |
| `gui/` | Desktop application | Desktop application (PySide6 shell over the stage objects, ADR-004). | 34 |
