---
type: Specification
title: "5.2 Pipeline stages"
description: "Each stage's inputs, outputs, tools and gate; contour conditioning (§5.2.1), meshing and its size fields (§5.2.2), the embedded analyte (§5.2.3)."
---

### 5.2 Pipeline stages

| # | Stage | Inputs | Outputs | Tools | Validation gate |
|---|---|---|---|---|---|
| 1 | Structure ingestion and alignment (`structure`; FR-01 to FR-03) | PDB/mmCIF, optional trajectory, expected point group | Aligned ensemble; Cₙ axis on z at r = 0 | MDAnalysis 2.10+ (LGPLv3) for PDB and every trajectory format; gemmi 0.7+ (MPL-2.0) for mmCIF, which MDAnalysis 2.10 does not read; the Kabsch rotation for superposition, cross-checked against MDAnalysis `rotation_matrix` | Oligomeric state matches (ClyA 12, αHL 7, MspA 8); abort on missing chains (FR-03) |
| 2 | Density map (`density`; FR-04) | Aligned ensemble, or stage 7's protonation artefact under `geometry.density.atoms: protonated` (the default); grid spacing, kernel | 3D density map | Vectorised numpy Gaussian deposition over a spherical stencil truncated at 10⁻⁶, per-atom width σR_i from the CHARMM radius set of the NOTE on stage 2 below, multiplied under `protonated` by the table's `charge.edits` radius scales, and keyed on the protonation key with its charge edits dropped (§5.3.1 NOTE on `charge.edits`), sharpness 0.93; the atoms are the protonated frames, hydrogens included, or the atoms as stage 1 loaded them under `as_loaded` (PHY-16); `gridData` IO. MDAnalysis `DensityAnalysis` is histogram-only and is not used (WP19) | Grid spacing 0.25–0.5 Å (FR-04); every atom has a radius; the map is finite and within [0, 1] |
| 3 | Symmetry reduction to (r, z) (`symmetry`; FR-05, FR-06) | 3D map, n | (r, z) map; residual azimuthal variance, Cₙ-averaged and raw | numpy and `scipy.sparse`; exact cell–annulus overlap weights; the Cₙ average in the angular harmonic basis (WP19) | Variance emitted with the geometry (FR-06, CON-04); annular weights summing to the exact annulus areas. The radius profile against the probe-radius profile is stage 4's gate (§5.2.1, §8.2.2 B5) |
| 4 | Contour extraction and conditioning (`contour`; FR-07, FR-08) | Stage 3's (r, z) mean; the aligned ensemble and its radius set, for the probe-radius profile, scaled under `geometry.density.atoms: protonated` by the `charge.edits` radius scales as stage 2's radii are (§5.3.1 NOTE on `charge.edits`); isolevel, smoothing and simplification tolerance | Closed conditioned polyline, a `nanopnp/profile/v0.5` document | scikit-image, Shapely (both BSD-3) and numpy, per §5.2.1 (WP20) | §5.2.1 (FR-08) |
| 5 | CAD assembly (`region`; FR-09) | Stage 4's polyline or a supplied `inputs.profile`, membrane specification with its `centre_z_nm` shift, reservoir radius, optional analyte | Fragmented (r, z) region, domains and boundaries tagged, as a declarative region record | `netgen.occ` (LGPL-2.1, OpenCASCADE, in-process). The optional Gmsh backend meshes this region at stage 6 and assembles none of its own (WP23 D1) | All bodies fragmented and imprinted, interfaces conformal, no gap or overlap at the membrane-to-pore junction, each domain one face, the membrane's inner edge strictly inside the body (FR-09, WP21; §5.2.1 NOTE on the membrane junction on any profile) |
| 6 | Meshing (`mesh`; FR-10) | Fragmented region, size fields; or a stage-6 mesh artefact named by its store hash in `inputs.mesh.artefact`, which the stage reads from the store and returns as its own artefact (REV-62; WP5.05) | Graded triangular mesh | Netgen (LGPL-2.1) default, Gmsh (GPLv2+) optional, behind the mesh adapter | §5.2.2 (FR-10, QR-12): the VER-10 and VER-27 gates, as on an ingested mesh, and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` (WP21); a hash the store does not hold is refused naming the hash and the store's root. The COMSOL comparison, which keys a case without a store, refuses such a case naming the hash, and compares a finished run of it instead (REV-188) |
| 7 | Protonation (`protonation`; FR-12, FR-38) | Stage 1's aligned ensemble, pH, force field, titration method, `charge.edits`; or a supplied `inputs.pqr` | Per-frame atom table in stage 1's frame (identity, coordinates, charge, radius), `Q_net` and every titratable residue's state per frame | PDB2PQR 3.8+ (BSD-3) driving PROPKA 3 (LGPL-2.1), one call per frame with the flags of PHY-16 step 3 (WP27); a pinned state is held through `Biomolecule.apply_pka_values` (the NOTE on `charge.edits` below) | Every atom carries a charge and a radius, and every charged atom a positive radius; `Q_net` an integer to 10⁻⁶ e on every frame; a pinned residue holds its state on every chain and frame; a supplied frame registered to its stage-1 frame to 0.01 Å (the NOTE on reading a supplied PQR below) |
| 7 | Charge assembly (`charge`; FR-13 to FR-15) | The protonation artefact, **and the deployed mesh** (its gate is evaluated there, PHY-19); on the consumer path, a supplied field document instead | ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface | The closed-form azimuthal kernel deposited on the deployed mesh (PHY-16, §8.2.4 D2); APBS 3.4.1 (BSD-3) cross-check through the test-only `apbs-binary` package; settings per PHY-16 | Charge conservation to 10⁻³ of Q_net on the deployed FE mesh, plus the per-z-slice cumulative check (FR-14, QR-03, PHY-19) |
| 8 | Materials (`materials`; FR-16) | Electrolyte specification, correction model names, coefficient files | D_i, μ_i, η, ϱ, ε_r as fields in ⟨c⟩ and d | Correction registry, `data/corrections/willems2020_nacl.yaml` | Conformance values of §4.3 reproduced; clamps above 5.3 M logged with location and species (PHY-13) |
| 9 | Case assembly (`case`; FR-26) | The case file | Resolved, validated case document, read by every other stage | `io/` schema validator, `physics/` model registry | Schema 'nanopnp/case/v0.6' validates, unknown keys rejected with a diagnostic naming the key (IF-03); round trip semantically identical (FR-26) |
| 10 | Solve (`solve`; FR-17) | Resolved case, mesh, charge and dielectric fields, materials; continuation ladder, optional warm start | Converged fields, iteration history | NGSolve 6.2.2606+ (LGPL-2.1), damped Newton; UMFPACK (GPL-2+) or scipy SuperLU (BSD) (CON-08) | No negative concentration at any nonlinear iterate; ladder completed to the target rung (FR-17); §6.5, §6.6 govern |
| 11 | QoI extraction (`qoi`; FR-22, FR-23) | Converged fields | I, t₊, RR, EOF rate, F^em(z), F^hd(z), ΔU(z) | Domain/indicator form and variational reaction flux, both implemented | The two routes agree within the stated tolerance, checked in CI (FR-23, QR-04); §6.7 governs |
| 12 | Reporting and export (`report`; FR-25, FR-28) | Results, artefact hashes, environment | XDMF/HDF5 field export (when `outputs:` asks for `fields`), run record, case file, manifest | `post/`, `io/` | Manifest complete and sufficient to reconstruct the run (FR-25, QR-08) |

Figures are drawn by `plot/` from stored artefacts; they are not a stage output.

Design notes, recorded where an implementer would otherwise choose wrongly.

| Stage | Note |
|---|---|
| 1 | The Cₙ axis comes from chain-permutation superposition: superpose chain A onto chain B, take the rotation's eigenvector of eigenvalue 1 (FR-02). Principal axes are unusable because they drift between frames. Over the 98 frames of the ClyA-AS ensemble, the largest-variance axis of the Cα set moved by up to 1.54° (rms 0.66°), while the chain-permutation axis moved by at most 0.010°. The cause is not degeneracy: the axial eigenvalue is well separated (1432 Å² against 801 and 881 Å² on the first frame). It is the chains' asymmetric fluctuation, which the permutation fit averages out by construction (measured; WP18 plan, Design §4). Stage 1 is specified in full in the NOTE on stage 1 below and the §5.3.1 NOTE on `structure:`. |
| 2 | Histogram plus uniform `gaussian_filter` is rejected: van der Waals-weighted smearing preserves the exclusion surface, uniform post-smoothing rounds the constriction. The grid is not coarsened, the *trans* constriction being about 3.3 nm across with a contour position that moves measurably with resolution. |
| 3 | The rule is the NOTE on stage 3 below. Exact overlap weights put about 6 cells in an annulus of width h at r = h, and about 630 at r = 5 nm, per slice at h = 0.05 nm. The harmonic-basis average is exact and costs one deposition, where depositing n rotated copies costs n, and rotating the voxel map by interpolation smooths it, lowering the peak Cₙ variance of a C12 ring by 3–6 %. A 1° axis error adds about 0.2 nm of apparent radius to a 3.3 nm constriction. |
| 3, 5 | The bilayer is absent from the density map. It is defined analytically in (r, z) over the hydrophobic belt and fragmented against the pore contour. |
| 5 | Reference geometry: reservoir half-disc R = 250 nm, membrane thickness 2.8 nm, `z_cis` = 12.25 nm, `z_trans` = −1.85 nm. The membrane is a quadrilateral, not a rectangle: vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm, inner edge slanted to meet the pore's outer surface. Code assuming a rectangle leaves a wedge of gap or overlap at the junction. CadQuery and build123d are 3D-solid-centric and unused; pythonocc serves BRep edge cases only. |
| 7 | Stage 7 is two registered stages, `protonation` and then `charge`, sharing the number so that stages 8 to 12, which this specification, the CLI's output and every recorded manifest cite by number, do not move (WP27). The registry lists stages by number and then in registration order. A run walks `protonation` after `structure` and before `density`, so that stage 2 smears the protonated atoms (PHY-16; §8.2.19 U2), and `charge` after `mesh`. `protonation` runs when stage 2 reads it (`geometry.density.atoms: protonated`, the default on a case with `structure:`), when stage 7's deposition reads it, or when it is the walk's target; a walk truncated at the mesh therefore protonates, and protonating an ensemble costs about a minute per frame of a ClyA dodecamer (WP27 plan, *Design* §1). Under `atoms: as_loaded` a walk to stage 2 does not protonate. With `charge.edits` the stage writes the edited table and, beside it, its parent, the unedited table, and records the variant (§5.3.1 NOTE on `charge.edits`); a charge or radius edit reuses the parent's stored frames, and a state edit protonates the frames again with the residue pinned. The protonation runs when the case has something to protonate (`structure:` or `inputs.pqr`, and no `inputs.charge`) and its model declares a fixed charge (§5.4.3), or when the density needs it, and is otherwise recorded as not run with the reason. `charge` runs when the model declares a fixed charge. A consumer of a deposited charge reads it from stage 7's artefact and from nowhere else (WP28). With a non-zero `charge.dielectric_transition_nm` the `charge` half also runs, reading stage 5's record, to derive `χ` (§4.4 NOTE on the derived solid fraction), whether or not it deposits a charge; the solve reads that `χ` from stage 7's artefact likewise (WP30). |

NOTE (stage 1, ingestion and alignment; `structure:`, FR-01 to FR-03): every selected atom SHALL
carry its element in the file, in the PDB element columns or the mmCIF `type_symbol`, and a file
that leaves one blank SHALL be refused naming the atom: a guessed element is how a Cα becomes
calcium. A selection carrying alternate locations SHALL be refused naming the first, because
choosing between them is structure preparation, which the pipeline does not do. A trajectory that
does not hold the structure's atoms, and an mmCIF model that does not list model 1's atoms in model
1's order, SHALL be refused naming the file.

A chain is identified by its chain identifier, or by its segment identifier where the chain column
is blank. The selected chains SHALL number exactly `n`, and a listed chain that is absent SHALL be
named (FR-03). Each chain SHALL carry at least half the Cα atoms of the most complete chain. Chains
SHALL agree in residue name at every residue number they share, with the histidine protonation
variants read as one name. A failure of either SHALL be refused naming the chain. Where
`source.chains` lists groups, a group is one unit of the ring: the groups SHALL number `n`, the two
rules above hold between the chains at one position of their groups, and a unit's Cα are those its
chains share with the chains at their positions, joined in the listed order, so a ring of unlike
chains such as PlyAB's pairs is superposed unit on unit (§8.2.39 AO1).

A `frames.last_ns` exceeding the recorded span by more than one frame interval SHALL be refused
naming the span and the interval. A file written without a timestep reads as 1 ps or 0 ps per
frame, and without this refusal it would yield the whole trajectory in silence. A `frames.count`
exceeding the window SHALL be refused naming both. The selected frame indices and their times are
recorded as read. Every selected frame is superposed on the Cα set of the earliest selected frame
(FR-01). A trajectory holding no frame SHALL be refused naming the file, and two Cα atoms at one
residue number and insertion code of one chain SHALL be refused naming the chain and the residue,
since one would silently replace the other. A chain split across the periodic box SHALL be refused
naming the chain, the residue pair, the frame and the distance: in any selected frame, two Cα of one
chain at consecutive residue numbers, neither with an insertion code, lie more than 1.0 nm apart,
where a peptide-bonded pair lies 0.38 nm apart and a wrapped one is a box length apart (QR-12).

`symmetry.axis: auto` takes the Cₙ axis from the ensemble-mean Cα structure by chain-permutation
superposition (FR-02). The chains are ordered by azimuth, and the whole assembly is superposed on
itself with each chain mapped to its neighbour. The axis is that rotation's eigenvector of
eigenvalue 1, through the Cα centroid. It SHALL refuse the point group, naming the measured
quantity, when the chains' azimuths are not spaced 360°/n to within a quarter of that spacing, or
when the rotation angle differs from 360°/n by more than 1°. It SHALL refuse `C1`, which has no
permutation to superpose.

The axis carries no sign of its own. It is signed to agree with the file's +z. A detected axis more
than 10° from the file's z SHALL be refused, naming the angle, because such a frame does not name an
end. Under `symmetry.axis: z`, where `n ≥ 2`, the axis SHALL be refused when its lateral displacement
from the detected axis exceeds 0.01 nm anywhere over the Cα axial extent, naming the tilt, the
offset and the displacement. The detected axis it is measured against passes the spacing, angle and
orientation refusals above first.

The aligned frame puts the axis on z at r = 0 and keeps the file's axial coordinate, `z = â · x`, so
stage 5 applies `geometry.membrane.centre_z_nm` in the frame it is written in. The four thresholds
above are constants of the code and never case keys. Their derivation and the margins measured on
the author's aligned copy of 2WCD, on 6MRT and on the ClyA-AS ensemble are in the WP18 plan, Design
§2–§4. The wwPDB entry 2WCD as deposited is not such a file: its asymmetric unit holds two
dodecamers, chains A–L and M–X, in the crystal frame, with the pore axis 22.9° from z and +z towards
*trans*, so it SHALL be refused by the 10° rule like any other file. Its chains A–L are the author's
copy moved rigidly (RMSD 1e-4 nm), and moving them is structure preparation.

NOTE (stage 2, the kernel, the radius set and the union; `geometry.density`, FR-04): `kernel: gaussian_vdw` takes each atom's width as `σ R_i`, with σ the `sharpness`. R_i is the
atom's CHARMM van der Waals radius (Rmin/2) by residue and atom name, from the radius set of
PDB2PQR's `CHARMM.DAT`, held as data under `data/radii/`. This is an **author ruling**: it is the set carried by the per-frame PQR files of the reference ensemble
(`knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md#11-the-authors-md-archive-measured`). The histidine names `HID`, `HIE` and `HIP` read as CHARMM's `HSD`, `HSE`
and `HSP`. `HIS` resolves only where every one of those three that names the atom gives the same
radius. `ILE CD1` reads as `CD`, `OXT` as `OT2`,
and terminal atoms resolve through the patch residues. An atom the set does not name SHALL be
refused, naming its chain, residue number, residue and atom. There is no fallback by element: a
guessed radius is a plausible wrong geometry. Which atoms are deposited, hydrogens included, is
`structure.source.selection`'s to decide, and the count of each element is recorded.

Each frame's density is the probabilistic union `ρ_f = 1 − Π_i (1 − g_i)` over that frame's atoms,
with `g_i = exp(−d_i²/(σR_i)²)`. A term is kept where `g_i ≥ 10⁻⁶`. The ensemble map is the mean
of the per-frame maps, not a union over frames. Grid nodes lie at integer multiples of the spacing
in the stage-1 frame, so the axis is a column of nodes. The grid is square in (x, y) about the
axis and holds every kept term with one cell to spare. The map SHALL be finite and within [0, 1],
or the run aborts naming the voxel (QR-12).

NOTE (stage 3, binning and the Cₙ average; `geometry.density`, FR-05, FR-06): stage 3 bins the map in (r, z) at `r_j = j·h`, each bin being the annulus of half-width h/2 about
r_j. Its weights are the exact areas of overlap between each grid cell and each annulus, so an
annulus's weights sum to its exact area, and each nonzero cell's to the cell's area. No bin is
interpolated. FR-05's average over the n rotated copies SHALL be taken in the angular harmonic
basis. There a rotation by α multiplies the m-th coefficient by `e^{−imα}`, so the average keeps
exactly the harmonics with m ≡ 0 (mod n). The averaged map's azimuthal mean is then the map's own,
and its azimuthal variance is `2Σ_{k≥1}|c_{kn}|²`. Both are computed from the unrotated map, with
neither rotated deposition nor interpolation. That variance is FR-06's residual azimuthal variance.
It SHALL be computed after the binned mean profile, interpolated at each cell's own radius, is
subtracted, because otherwise the radial gradient across a bin reads as azimuthal variation. It
uses only harmonics below the ring's sampling limit `π r_j/h`. Below `r = n h/π` no harmonic is
resolved, and the artefact records that radius and each bin's harmonic count rather than
presenting a measured zero. The variance of the map without the Cₙ average is reported beside it,
and their difference is the part of the azimuthal variation that is not Cₙ-symmetric. Neither is
gated: RSK-07 makes the variance a validity criterion to be documented, and no threshold is
specified. The derivations and measurements are in the WP19 plan, Design §1–§4.

NOTE (stage 7, protonation as run; PHY-16 step 3): PDB2PQR SHALL be run
once per selected frame (§8.2.4 D4) on that frame's heavy atoms, with every hydrogen and every water
removed (PDB2PQR's `--drop-water` drops only `HOH` and `WAT`, observed on 3.7.1) and every protonation-variant residue name (`HSD`, `HSE`, `HSP`, `HID`, `HIE`, `HIP`, `ASH`, `ASPP`,
`GLH`, `GLUP`, `LYN`, `LSN`, `CYM`, `TYM`, `ARN`) written as its titratable parent, so that the
states are PROPKA's at the case's pH and not the source file's. The disulfide name `CYX`, which
PDB2PQR writes under `SWANSON` and `PEOEPB`, is read as `CYS` the same way: without it every disulfide-bonded cysteine named a residue the ensemble does
not hold. PDB2PQR treats `HSD` and
`HSE` as fixed residues that PROPKA does not titrate, and refuses `HSE` with its hydrogens present,
so a CHARMM-named MD frame passed through verbatim would pin every histidine (observed on 3.7.1). The reference passed
its frames verbatim to PDB2PQR 2.1.1, and its PQRs keep `HSE`; the difference is measured at Tier 3
rather than reproduced. Under CHARMM, PDB2PQR cannot represent a neutral terminus, `CYS⁻`, `LYS⁰`,
`TYR⁻` or `ARG⁰`, and keeps the standard state where PROPKA prefers one of these; it never applies
PROPKA's terminal pKa at all. Every such residue SHALL be recorded per frame as an unapplied state,
derived by comparing each residue's applied charge with the sum of PROPKA's group states at the pH,
never parsed from log text. On 2WCD at pH 7.5 these are `CYS 285` (pKa 6.25) in every chain, and
the N-terminus of `LYS 8` wherever its pKa, 7.48 to 7.50 across the chains, falls below the pH. They are the validated model's states, so they are recorded and
not gated. The protonation states of the chains of a homo-oligomer are not symmetrised: a residue
whose charge differs between chains of identical sequence is recorded as a per-chain diagnostic.

NOTE (stage 7, `charge.edits`; PHY-16 step 3, FR-38): a `state` edit pins a titratable residue's state during
PDB2PQR's call instead of leaving it to PROPKA's pKa at the pH. PDB2PQR 3.8 applies the state patch
`ASH`, `GLH` or `HIP` to each residue whose pKa passes the pH, through
`Biomolecule.apply_pka_values`; the stage wraps that call, drops each pinned residue's pKa from the
dictionary it receives, so the residue keeps the force field's standard state, and applies the patch
itself for `neutral` ASP, `neutral` GLU and `charged` HIS. Renaming the input residue cannot pin the
charged state, since PDB2PQR titrates an input named `ASP`, and drops that residue's PROPKA row. After
assembly a gate SHALL refuse a frame whose pinned residue does not hold its state, naming frame,
chain and residue. A pinned residue is never recorded as an unapplied state. PDB2PQR's hydrogen
optimisation can reposition a neighbour's hydrogens or carboxyl oxygens when a state changes (GLU 18
beside ASP 21 on the 2WCD fragment at pH 2), so the variant's record lists a residue whose positions
move, with its charges unchanged. A charge or radius edit acts on the assembled table, after the
states and the radius comparison, and so on every residue alike.

NOTE (stage 7, protonation before the density; PHY-16, §8.2.19 U2; §8.2.31 AG8). Step 3's protonation runs on the
aligned ensemble before stage 2, and stage 2 smears the protonated frames: PDB2PQR's atoms, hydrogens
included, at the positions it wrote, each with the radius the §5.3.1 NOTE on `geometry.density` takes
for it. A protonation state or a charge-level variant therefore moves the density, the contour and the
mesh as well as the charge. That is the validated default, `geometry.density.atoms: protonated`.
Smearing the atoms as loaded, as the reference did from its MD frames, is the switch away from it,
`atoms: as_loaded`; the manifest records it (FR-25), and the reference-reproduction cases set it (VAL-03's
golden, VAL-05, VAL-06 and the Tier 3 cases), as do the walks `2wcd-charged` and `2wcd-shell` of VER-62.
Worked example 07's VER-62 walk is re-pinned on the mesh the default deploys (§8.2.7 G10). A walk
truncated at the mesh protonates, about a minute per frame of a ClyA dodecamer. A changed
protonation state moves the density (Tier 1).

NOTE (stage 7, reading a supplied PQR; `inputs.pqr`): ATOM and HETATM records are read by
the PDB columns through the coordinates and then by the two whitespace-separated numbers after
them, which is the layout PDB2PQR writes, whose coordinate fields may run together; a line those
columns do not read is read as whitespace-separated fields, and a line read both ways with
different values is refused naming its line number. A whitespace field that cannot be an atom
name, a residue name or a chain (more than four, four and one characters) does not read the line:
PDB2PQR writes a four-character residue name from the alternate-location column and runs a
four-character atom field into it (`OD2ASPP`, measured), which the columns
read. A record type run into a five-digit serial (`HETATM12345`, PDB2PQR's own layout) is split
before the fields are read. A residue is identified by chain, number and insertion code, and its
name is the one its atoms carry other than PDB2PQR's CHARMM patch names `TER` and `DISU` (a
disulfide-bonded cysteine's `CB` and `SG`, written `1CB` and `1SG`), or, where its atoms carry a parent and one of its
protonation variants, the variant: PDB2PQR writes a patched residue's backbone under the parent and
its side chain under the variant (`ASP` and `ASPP` in one residue).
Each frame is registered to its stage-1 frame by superposing its Cα atoms on the ensemble's, residue for residue,
after which every heavy atom of the ensemble SHALL lie within 0.01 Å of a distinct heavy atom of the
same residue of the PQR, other than the atoms PDB2PQR's hydrogen-bond optimisation may flip: the
amide `OD1` and `ND2` of asparagine, `OE1` and `NE2` of glutamine, and the ring `ND1`, `CD2`,
`CE1` and `NE2` of histidine. A flip turns the group through 180° about the bond to it, and the
group is not symmetric about that bond, so a flipped atom lands 0.13–0.40 Å from every atom it was
given (138 heavy atoms of the prepared 2WCD, measured; the criterion is not over every heavy atom, because a flip does not exchange positions exactly and
such a criterion would refuse PDB2PQR's own output); they are not compared, their worst distance is recorded,
and the rest of each residue fixes where it is. A flip moves atoms and never removes them or changes their
element, so a residue of these three whose PQR holds fewer heavy atoms of an element than the
ensemble's is refused, or a PQR missing a flippable atom would register. 0.01 Å is about ten times the rounding of a PQR's coordinate columns
and a hundredth of the shortest bond between heavy atoms, so a frame count that differs, a residue
the two do not share, or a frame whose atoms have moved is refused naming the frame. Heavy atoms the PQR adds, as PDB2PQR
adds a missing terminal oxygen, are counted, not refused; hydrogens are not compared. The
registered coordinates are what the artefact carries, so a PQR written in another frame, as the
reference's MD-frame PQRs are, lands in stage 1's. A frame whose heavy atoms already meet the
criterion where they stand is not moved, so the stage's own export reads back exactly.

#### 5.2.1 Contour conditioning and its gate

Pipeline (WP20):

1. `find_contours` (sub-pixel marching squares, diagonal neighbours above the level joined) runs
   on stage 3's mean at the isolevel, default 0.25. Each point is placed by the grid's own axes,
   so bin j sits at its centre `r_j = j·h`.
2. The closed contours are assembled into the region above the isolevel. A contour left open at the
   grid's edge is refused.
3. The region is closed, then opened, by a disc of radius 2h, with h the density grid spacing.
   Every hole left is filled and recorded, and exactly one component is admitted.
4. The loop is resampled at uniform arc length h/2 and smoothed by Taubin λ|μ, which preserves the
   area where Laplacian and Chaikin smoothing shrink it.
5. Shapely `simplify` (Douglas–Peucker, topology preserved) runs at `simplify_tol_nm`, default
   0.02 nm, which must be below h.
6. Vertices are removed until no edge is shorter than `h_c`.
7. An optional periodic B-spline fit is not implemented.

The constants are recorded in the WP20 plan, D4–D9. They key the stage-4 artefact and are not case
keys.

| Gate criterion | Threshold |
|---|---|
| `LinearRing.is_valid`, `is_simple` | both true |
| Minimum vertex spacing | ≥ `h_c` |
| Minimum local feature size, measured two edges either side of each vertex | > 2 `h_c` |
| Loop topology | one component after the closing and opening, with no contour open at the grid's edge, holes filled and recorded, and the loop clear of the axis by `h_c` |
| Radius profile | `−h_c ≤ r_c(z) − R_p(z) ≤ 1.5 nm` on every mid-plane between z nodes that crosses the loop. `r_c` is the loop's innermost crossing, and `R_p` the frame-mean radius of the largest sphere centred on the axis that clears every atom's radius in the aligned structure. HOLE is an optional cross-check (§8.2.2 B5) |

Rationale (feature size): near-tangential self-approaches at the constriction generate slivers the
mesher cannot repair.

NOTE (the contour's size target, WP20): `h_c`, the "target element
size" of the criteria above, is the density grid spacing h, 0.05 nm by default. It is not the
stage-6 wall size. NUM-30's `λ_D/5` is 0.27 nm at 0.05 M: read as the target, it would make the
contour depend on the electrolyte concentration, and at 0.05 M erase the lumen's corrugation.
Step 3's radius is set by the margin the feature-size criterion needs. Simplification moves each
wall by up to its tolerance, so the gap left by a closing of radius δ stays above `2h_c` only if
`δ > h + simplify_tol_nm`, and 2h meets that for every admitted tolerance. The gaps and fins it
removes, under 0.2 nm at the default grid, admit no water molecule and are thinner than one heavy
atom. Step 3 automates the "manual removal of overlapping and superfluous vertices" that the source
work records. On the ClyA-AS ensemble, a closing of radius h leaves a groove that fails the
criterion at 0.058 nm, and 2h passes it at 0.229 nm (WP20 plan, Design §2 and §4).

NOTE (the radius band, WP20): the lower bound is geometric. Inside
the axis-centred sphere every atom is at least its own radius away, so the 25 % contour of the
azimuthal mean can enter that sphere by at most a fraction of an atom's width. The upper bound is a
gross-error check on the lumen's corrugation. The margins `r_c − R_p` measured on 2WCD (chains A–L)
and on the ClyA-AS ensemble are in
[`knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md` §1.3](../../knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md#13-stage-4-on-real-and-synthetic-inputs-measured).
The band does not detect a radial scale error of a few per cent; VAL-05 does (WP20 plan, Design §5).

The reference pore boundary is published in the COMSOL model report as a closed 190-vertex polygon
(r ≈ 1.65–5.66 nm, z from −1.85 to 12.25 nm). The author's delivered tabulation of that boundary
SHALL be shipped as the regression fixture (§7.2), so solver work proceeds on the reference polygon
without the contour pipeline. The table is held in
the repository as `data/geometry/clya_as_radial_geometry.csv`, supplied by the reference model's
author: 185 `r,z` pairs in nm tracing a simple closed loop, r ∈ [1.65, 5.66], z ∈ [−1.85, 12.25],
enclosing 26.4939 nm².

NOTE (the membrane junction): the membrane's slanted inner edge, (2, −1.4) → (3.5, +1.4), lies
strictly **inside** the pore body along its whole length. At z = −1.4 the pore spans
r ∈ [1.725, 2.7524] and the edge enters at 2.0 — 0.275 nm clear of the lumen wall and 0.752 nm clear
of the outer surface; at z = +1.4 the pore spans r ∈ [2.96, 4.88] and the edge leaves at 3.5, with
0.540 and 1.380 nm of clearance. The assembled membrane is therefore the quadrilateral **minus** the
pore body, and it meets the pore on the pore's own outer surface, not on the drawn edge. The slant is
necessary rather than cosmetic: the lumen wall passes through (2.0, 0) exactly and has opened to
r = 2.96 by z = +1.4, so a vertical inner edge at r = 2 would place membrane material inside the
electrolyte for every z > 0. The cap's underside is re-entrant, so the membrane also fills a cleft
beneath it and its boundary is not monotone in z; it remains one connected domain, which is what
makes the reported domain count come out at three — pore body, membrane, and a single electrolyte,
the lumen joining the two reservoirs.

NOTE (the membrane junction on any profile, stage 5, FR-09; WP21): the
profile is first moved into the model frame, `z ← z − geometry.membrane.centre_z_nm`. On each plane
`z = ±t/2` the **lumen-adjacent body interval** `[r₁, r₂]` is bounded by the profile's two
smallest crossings of that plane, an edge crossing it when `lower ≤ z < upper`. Where an edge of
the profile lies exactly on the plane, `r₂` runs on to that edge's far end, because the body's
section continues along it and the membrane meets the body there. The inner edge of the membrane quadrilateral is the chord from
the lower plane's interval to the upper plane's that has the largest minimum distance to the
profile. It is searched on the 63 × 63 interior points `r₁ + (r₂ − r₁)k/64` of the two intervals.
Any chord with its ends in those intervals that lies inside the body yields the same region: a
fluid pocket between two such chords would be enclosed by them, by the body and by the plane
segments between their ends, which are body too, while the complement of a simple polygon is
connected. The widest-margin chord is taken because it is the choice furthest from failure. The
chord between the intervals' mid-points is **not** admissible in general. On the delivered fixture
it runs from (2.2387, −1.4) to (3.92, +1.4) and crosses the cleft under the cap between
(3.070, −0.016) and (3.235, 0.260), which splits the electrolyte in two. On the fixture the
widest-margin chord is (1.982, 3.470) nm, with a clearance of 0.236 nm. A plane
that crosses the profile more than twice always splits a domain, and the one-face criterion below
refuses it. The gap between the first two body intervals on the plane is a segment of fluid
bounded by body at both ends. The body arms on either side of it join above the plane or below
it, because the profile is one simple polygon. If they join above, the fluid over the gap is
enclosed by body and the gap, and is a second electrolyte face. If they join below, the pocket
under the gap is enclosed alike: bilayer where it lies in the slab, a second membrane face, and
electrolyte where it reaches past the other plane (WP21 Outcomes, [verified]). Stage 5 SHALL abort,
naming the criterion, the measured value, the threshold and the (r, z), on any of these:

- a plane crossing the profile fewer than twice, with the profile's model-frame z extent and
  `centre_z_nm` named;
- a best chord closer than 0.01 nm to the profile, so that the membrane is not representable as a
  quadrilateral with a slanted inner edge;
- a domain assembled as other than one face, with each face's centroid and area named;
- a profile vertex not strictly inside the reservoir disc;
- a membrane whose innermost radius on either plane differs from that plane's `r₂` by more than
  the fragmentation tolerance.

The last criterion is VER-28's junction measure, made generic. The shipped reference geometry keeps
its drawn corners (2.0, 3.5), and its mesh is unchanged. The fixture assembled with either chord
meshes to one connectivity, with vertices within 4.2 × 10⁻⁹ nm (WP21 plan, Design §1).

NOTE (the ion-exclusion shell, stage 5, FR-15, PHY-20; WP30): a non-zero
`charge.exclusion_offset_nm`, `a`, makes stage 5 build the exclusion contour from the model-frame
profile `P`, with `h_c` as in the NOTE on the contour's size target:

1. `O` is the dilation of `P` by `a`, with round joins at 8 segments per quarter circle (WP20 D5).
2. `O` is closed by a disc of radius `2h_c`, as in step 3 of §5.2.1 and for the same reason.
3. Every hole of `O` is filled and recorded with its centroid and area. A hole is fluid enclosed by
   the shell, which no ion can reach.
4. `O`'s ring is resampled at uniform arc length `L/⌊L/(1.05 h_c)⌋`, and step 6 of §5.2.1 runs on
   it (see below).
5. §5.2.1's validity, simplicity and spacing criteria are applied to that ring, together with its
   clearance of `h_c` from the axis.

The shell is `O − P − M` and the electrolyte is `D − M − O`, where `M` is the membrane quadrilateral
and `D` is the reservoir disc. The membrane, its chord and its junction are unchanged. The shell
SHALL be one face. It runs from the membrane's upper face round the cap, down the lumen, and round
the *trans* end to the membrane's lower face. Its outer surface, against the electrolyte, is `wall`.
The no-slip surface, the no-flux surface and the PHY-02 distance source therefore move there, with
no change to `numerics.wall_distance.sources`. The shell's seams with the protein and with the
membrane are `interface`. The outer surface lies at most `max(h_c²/a, a/100)` inside the exact
offset (0.01 nm at `a` = 0.25 nm), and stage 5 gates that on every edge of the ring. Away from the
closing and the filled holes it never lies more than 10⁻⁶ nm outside the exact offset (WP30 plan,
*Design* §2). The `exclusion` domain is meshed at the wall size. On netgen, each `wall` edge of the
shell, of length `L`, is cut into `n = ⌈L/(1.1 h_wall)⌉` equal segments by a size of `L/n` where
`n > 1`, and keeps `h_wall` where `n = 1`; Gmsh needs no such rule (see below).

Step 4's resampling keeps every chord between `h_c` and `1.15 h_c`, so step 6 removes nothing and the
surface lies at most 0.62 of the bound inside the offset; netgen's rounding of an edge's segment count
is why stage 6 divides the shell's `wall` edges. The argument and its measurements:
`knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md` §2.2.

Stage 5 SHALL abort, naming the criterion, the value, the threshold and the (r, z), on any of these:

- an offset that comes within `h_c` of the axis and so closes the constriction, naming the z
  interval and the body's least radius over it;
- an offset vertex that is not strictly inside the reservoir disc;
- an edge of the outer surface closer to the body than `a − max(h_c²/a, a/100)`, naming its
  midpoint;
- a domain assembled as other than one face.

`0 < a ≤ 2h_c` SHALL be refused naming both keys. The shell is a face of width `a`, and §5.2.1's
feature-size criterion admits nothing narrower than `2h_c`. The construction reads Shapely, which
is in the `structure` extra. Without the extra, the case SHALL be refused naming the extra and the
key. The record carries the offset loop, so stage 6 rebuilds the region without Shapely. With
`a = 0` none of this NOTE runs, and the record, its key and the mesh are those of §5.2.1.

NOTE (vertex counts): the delivered 185-vertex table is the geometry of record (OPN-05); it assembles
to 190 vertices and 192 boundaries. The model report's 190, 196 and 198 are COMSOL's counts after its
import conditioning (§2.2's Geometry vertices row).

NOTE (what `nanopnp.mesh.reference` assembles): 193 vertices and 195 edges, three more of each than
the count above, and both deviations are deliberate. Two come from breaking the side on `r = 0` into
three collinear segments at the pore's axial extent: OCC keeps collinear segments as separate edges,
the pore polygon never touches the axis, and this is therefore the only way §5.2.2's 0.075 nm
"symmetry axis inside pore" can be applied as a size field at all. The third is the seam OCC places
at parameter zero on a closed circle, at (250, 0), which survives the clip to `r ≥ 0` and halves
`membrane_outer` into two arcs meeting there — a closed circle has a seam somewhere, and this one
costs one vertex element on the reservoir rim. The named edges are then 186 around the pore
(151 `wall`, 35 `interface`), 3 `axis`, 2 `membrane`, 2 `membrane_outer`, and one each of `cis` and
`trans`. VER-28 asserts these counts.

NOTE (the conditioning gate and a supplied fixture): the gate above applies to contours the FR-08
pipeline *produces*. The delivered reference polygon does not meet two of its criteria at the
reference wall size of 0.05 nm — minimum vertex spacing 0.0361 nm, with 10 of its 185 edges shorter
than that wall size, and minimum local feature size 0.0806 nm against a 0.1 nm threshold — and yet
it is what the reference mesh of §5.2.2 was built from, at that wall size, reaching minimum element
quality 0.6378. A supplied profile fixture is therefore NOT gated on those two criteria. It is gated
on validity, simplicity and loop topology, and its measured spacing and feature size are recorded in
its provenance block, so that a mesh size chosen against it can be checked rather than assumed.

#### 5.2.2 Meshing

The mesh resolves a Debye length of 0.18–1.4 nm against a 250 nm reservoir, a scale span of 10³,
without degenerate elements at the pore, membrane and reservoir triple junctions or at r = 0.
Near-wall target h₁ ≈ λ_D/5 (about 0.04 nm at 3 M), grading to 5–10 nm in the far reservoir,
expected size 5 × 10⁴ to 2 × 10⁵ cells.

Isotropic graded refinement is the default strategy (FR-10). The reference model reached the
published results with free triangular meshing, no boundary layers anywhere in the sequence, and
isotropic grading to 0.05 nm at the pore wall.

| Region | Max element | Min element | Curvature factor | Growth rate |
|---|---|---|---|---|
| Global ("Finer" preset) | 10 nm | 0.001 nm | 0.25 | 1.05 |
| Pore boundary | 0.05 nm | 0.001 nm | 0.25 | 1.05 |
| Pore domain ("Extremely fine") | 0.1 nm | 0.004 nm | 0.2 | — |
| Reservoir domain | 2.8 nm | 0.04 nm | — | 1.04 |
| Reservoir outer boundary | 5 nm | 0.025 nm | — | 1.25 |
| Symmetry axis inside pore | 0.075 nm | 0.04 nm | — | — |

That mesh has 120,917 triangles, 1,879 edge elements and 196 vertex elements, minimum element
quality 0.6378, average 0.9765, which set the target (the table's and these counts' home:
`knowledge/09-comsol-reference-settings/02-mesh-27.md` A.1, A.2). Quality gate, enforced in code: minimum
SICN/gamma > 0.3, the mesher's own optimisation pass (netgen's `optsteps2d` 5, Gmsh's
`Mesh.Smoothing` 5; WP23 D5), worst element and its location
reported, run aborted on failure (QR-12).

NOTE (SICN and gamma): these are two distinct measures and both SHALL be gated. For a straight-sided
triangle, SICN is the signed inverse condition number of the Jacobian taken relative to the unit
equilateral element and gamma is the normalised inradius-to-circumradius ratio `2 r_in / R_circ`;
both equal 1 on the equilateral element and both are scale-invariant. They are not interchangeable:
on the isoceles family over a unit base, `SICN = 0.3` occurs at `gamma = 0.1298` and `gamma = 0.3` at
`SICN = 0.4687`, a factor of 1.6208 in element height (0.215508/0.132966), so a single
"SICN/gamma > 0.3" reading admits
two different meshes. Gamma is unsigned — an inverted equilateral element scores `gamma = 1` and
`SICN = −1` — so gamma alone cannot detect inversion, and `SICN ≤ 0` SHALL be reported as its own
failure ("inverted element") rather than folded into the quality gate. Under the axisymmetric
`r`-weighted forms an inverted element contributes negative volume and nothing else raises.

Anisotropic boundary layers are an optional element-count optimisation (FR-11, post-1.0), not a
dependency of the default path.

| Route | Mechanism and status |
|---|---|
| Geometric, in project code | Offset the conditioned contour inward by a geometric progression (Shapely `buffer(-d)` or `offset_curve`), mesh the strips as structured quads, let the unstructured mesher fill the interior; growth ratio 1.15–1.2 over about 15 layers. Preferred, deterministic. The legacy `parallel_offset` still works in Shapely 2.1.2 but is retained only for backwards compatibility and uses different sign and segment conventions |
| Mesher-native, Netgen | `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`, binding C++ `GenerateBoundaryLayer2`. Best-effort: an unresolved August 2024 NGSolve forum report has it failing to fill a zone adjacent to the new advancing front. The 3D `Mesh.BoundaryLayer` now unconditionally raises "Call syntax has changed! Pass a list of BoundaryLayerParameters to the GenerateMesh call instead" |
| Mesher-native, Gmsh | `BoundaryLayer`, `Distance`/`Threshold`, `Min`/`Restrict` size-field algebra, `Fan` points, quads-in-BL. Best-in-class, available only on the optional GPLv2+ backend |

Excluded components (CON-12): MeshPy, maintained at 2026.1 but wrapping Triangle, whose licence
permits distribution as part of a commercial system "ONLY BY DIRECT ARRANGEMENT WITH THE AUTHOR";
TetGen 1.5 (AGPLv3); pygmsh (2022-01) and pygalmesh (2022-09), both stale. The `gmsh` API is called
directly.

NOTE (the Gmsh backend's size field; FR-10, CON-10; WP23): the Gmsh
backend meshes the region stage 5 assembled, never one of its own. It applies the table above
through the classification netgen's sizes use. Gmsh has nothing like netgen's built-in restriction
of the element size by edge length and by the proximity of close edges. It does not grade outwards
from a domain's size either. Given the table alone it clears the quality gate on the reference
fixture at a minimum gamma of 0.3143 and fails it at `size_scale` 2 and 4 (WP23 plan, Design §2).
The backend therefore states those restrictions as size fields. Each is graded outwards as
`h + 0.2 d`, 0.2 being the constant netgen is given as its grading:

- every sized boundary (`wall`, the reservoir arc, the axis inside the pore) is a source at its
  size;
- the boundary of every sized domain is a source at the domain's size, the domain being held to
  that size inside;
- each vertex whose shortest incident curve is shorter than the smallest target of its incident
  curves is a source at that curve's length;
- the membrane is a sized domain at its own thickness, not multiplied by `size_scale`, because it is
  a feature of the geometry and not an entry of the table.

None of these touches a netgen mesh, which already meets them. On the fixture, the WP22 frozen case
gives conductances 1.25e-4 apart on the two backends' meshes at `size_scale` 2. Refining netgen to
`size_scale` 1 moves its own value by 2.0e-4 (WP23 plan, Design §4).

NOTE (an idealised pore's size field; FR-10, VER-62; §8.2.22 X1, X4; WP57): the table above sizes
a structure's region, whose protein and lumen it was set on. An idealised pore (§5.3.1, `geometry.pore`)
has neither, and stage 6 meshes it with netgen alone under two sizes: `numerics.mesh.maxh_nm`
(§5.2.2's global 10 nm where it is none) as the global maximum and the resolved wall size on `wall`,
each times `size_scale`, at netgen's grading 0.2 and three optimisation passes (`optsteps2d` 3),
with no other size and no other pass. That is the recipe of the earlier cylinder generator: on the
examples' pore (`radius_nm` 2, `thickness_nm` 6, `radius_nm` 10 for the reservoir, `maxh_nm` 4,
`wall_h_nm` 0.35) it gives the 392-element mesh VER-62's walks were recorded on, bit for bit, while
five passes keep the 392 elements and move every vertex (WP57 plan, Grounding). The quality gate
and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` apply as on any generated mesh; that
mesh's wall segments measure 1.071 × the target on average and 1.139 × at most. `nanopnp mesh` meshes
a geometry file by the same recipe (IF-02's generators NOTE), its `--maxh-nm` and `--wall-h-nm`
in the place of the two keys.

#### 5.2.3 Embedded analyte

| Approach | Verdict |
|---|---|
| Body-fitted remeshing per axial position: for each z_a, rebuild the (r, z) geometry with the analyte subtracted and remesh | Specified. In 2D a remesh takes seconds and the positions are embarrassingly parallel |
| ALE or moving mesh | Rejected: needed only for transient trajectories, and with analyte diameter comparable to pore diameter, distortion at the constriction forces a remesh regardless |
| Fictitious domain, immersed boundary or level set | Rejected: a diffuse interface cannot carry a sharp dielectric jump, zero ion flux and no-slip without degrading Debye-layer accuracy |

The analyte is a hard dielectric body with no ion flux, no-slip and a dielectric jump, as at the
pore wall (FR-21). Both charge models ship as named options, a surface charge density and a smeared
volumetric charge, sharing the smearing machinery of §4.4.
