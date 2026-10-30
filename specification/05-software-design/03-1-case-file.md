---
type: Specification
title: "5.3 Data design"
description: "Specifies the case file as one declarative YAML document, the unit of reproducibility from which everything else is derived."
---

### 5.3 Data design

#### 5.3.1 Case file

One declarative YAML document is the unit of reproducibility (IF-03). Everything else is derived.

```yaml
schema: nanopnp/case/v0.5
name: clya-wt-1M-100mV

inputs:                             # optional; supplied artefacts, §5.3.2
  mesh: {path: clya.msh, format: msh41,
         groups: {lumen: electrolyte, upper: cis, lower: trans,
                  clya: protein, bilayer: membrane,
                  pore_wall: wall, outer_rim: membrane_outer,
                  symmetry_axis: axis}}
  charge: {path: clya_charge.yaml, format: field1}
  eps_r:  {path: clya_solid_fraction.yaml, format: field1}
  # profile: {path: clya_profile.yaml, format: profile1}   # stage 4, nanopnp/profile/v1
  # pqr:     {path: clya.pqr, format: pqr}                 # stage 7's PDB2PQR step

structure:
  source: {path: 2WCD.pdb, variant: ClyA-AS, chains: all, selection: protein}
  ensemble: {trajectory: eq.xtc, frames: {last_ns: 5, count: 50}}
  symmetry: {point_group: C12, axis: auto}

geometry:
  density:  {grid_spacing_nm: 0.05, kernel: gaussian_vdw, sharpness: 0.93}   # 0.5 Å, as the paper
  contour:  {isolevel: 0.25, smoothing: taubin, simplify_tol_nm: 0.02}
  membrane: {thickness_nm: 2.8, centre_z_nm: 0.0}   # centre in the structure's frame, along the axis
  reservoir: {radius_nm: 250}
  analyte:  {shape: prolate_spheroid, a_nm: 2.0, b_nm: 3.0, z_nm: 6.0, charge_e: -8}

charge:
  ph: 7.5
  forcefield: CHARMM
  titration: propka
  smearing: {sharpness: 0.5, grid_spacing_nm: 0.005, axis_cutoff_nm: 0.01}
  exclusion_offset_nm: 0.0           # FR-15, PHY-20; 0 is the validated model, no exclusion shell
  dielectric_transition_nm: 0.0      # PHY-20 NOTE; 0 is the sharp indicator of the validated model

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  temperature_K: 298.15
  parameters: willems2020_nacl      # reference D_i^0, eta^0, rho^0, eps_r,f^0, a_i, a_0
  driver: average                   # PHY-01; `ionic_strength` is a deviation
  corrections:                      # the pluggable registry, §5.5
    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}
    mobility:     {model: willems2020_nacl, wall: true, concentration: true}
    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}
    permittivity: {model: willems2020_nacl}
    density:      {model: willems2020_nacl}
    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}

boundary_conditions:
  bias_V: 0.100
  ground: cis
  walls: {ion_flux: no_flux, slip: no_slip}

physics:                            # the named model of PHY-21
  model: epnp-ns
  flow: true
  variable_density: true
  inertia: true                      # PHY-22; the reference model retained it
  dielectric_gradient_forces: false  # PHY-23; off in the validated model
  solid_permittivities: {protein: 20.0, membrane: 3.2}   # PHY-20; the only place they are set

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  mesh: {backend: netgen, wall_h_nm: auto, size_scale: 1.0, boundary_layer: false}
  # wall_for_concentration_M: 3.0   # optional: size `auto` at this salt's Debye length (§8.2.14 P10)
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}   # NUM-16
  continuation: default_ladder
  stabilisation: none                # NUM-11; `supg` is its flag, `reference` matches §6.4
  wall_distance: {sources: wall, max_distance_nm: 3.0}                         # PHY-02
  linear: {solver: umfpack}          # see §6.6; MUMPS requires a source build

outputs: [current, transport_numbers, rectification, eof_rate, analyte_force, fields]
```

NOTE (`nanopnp/case/v0.5`, and schema history; §8.2.2 B3, §8.2.7 G6): the
schema moved from `nanopnp/case/v1` to carry every key Phases 2 and 3 needed. Against v1 it **adds**
`inputs.profile`, `inputs.pqr`, `structure.source.selection`, `geometry.membrane.centre_z_nm`,
`charge.exclusion_offset_nm`, `charge.dielectric_transition_nm` and `numerics.mesh.size_scale`;
**renames** `structure.source.pdb` to `structure.source.path`, since IF-04 reads mmCIF as well; and
**removes** `charge.eps_protein` and `geometry.membrane.eps_r`, whose values
`physics.solid_permittivities` already carries. A permittivity set in two places is a calibration
parameter (PHY-20) with two sources of truth, and a default of 20 or 3.2 written in code would be a
fitted parameter hard-coded in Python; the author ruled that the map is the one
place they are set. The added keys default to the validated configuration.
In v0.5, every case document must declare schema `nanopnp/case/v0.5` exactly, and any
other schema identifier is refused naming the expected schema and the declared identifier before
any structural validation (§5.4.1). The earlier pre-release identifiers `nanopnp/case/v1` and
`nanopnp/case/v2` are retired.

NOTE (the added keys that change a number): `charge.exclusion_offset_nm`
and `charge.dielectric_transition_nm` are the fitted exclusion offset of FR-15 and the width of
PHY-20's transition to `ε_w`. Both SHALL be non-negative, and both are switches whose validated
default is `0`: the validated model has no exclusion shell and a sharp material permittivity (PHY-20
NOTEs). A non-zero value is therefore a deviation that the FR-25 manifest records. When the
`charge:` block is absent, each reads as its validated default. Both are built from the stage-4
profile (§5.2.1 NOTE on the ion-exclusion shell; §4.4 NOTE on the derived solid fraction), so
either set away from `0` beside `inputs.mesh`, or in a case carrying neither `structure:` nor
`inputs.profile`, is a knob with no effect and SHALL be refused naming both keys. A non-zero
`dielectric_transition_nm` beside `inputs.eps_r` supplies one quantity twice and SHALL be refused
naming both. Each is refused below its resolution limit as its NOTE says, and a model that declares
no solid fraction refuses the transition as it refuses `inputs.eps_r` (§5.4.3) (WP30). `numerics.mesh.size_scale`, default
`1`, SHALL multiply every element-size target of §5.2.2 and NUM-30, the resolved `wall_h_nm`
included. It exists so that a mesh-convergence study (RSK-09, §6.8) is a sweep over a case-file
field (FR-24) rather than a code edit. It is a discretisation choice recorded with the mesh, not a
deviation. With a supplied `inputs.mesh` a value other than `1` would be a knob with no effect, so
it SHALL be refused.

NOTE (`charge.ph`, `charge.forcefield`, `charge.titration`; the `protonation` stage, PHY-16 step 3,
FR-12; WP27): `ph` is a number in [0, 14], the range PDB2PQR accepts.
`titration` is `propka` or `none`; `none` runs PDB2PQR without a titration method, so every
residue keeps the force field's standard state and the pH reaches no calculation. A `ph` set away
from its default beside `titration: none` is therefore a knob with no effect and SHALL be refused
naming both keys, as `numerics.mesh.size_scale` is beside `inputs.mesh`. `forcefield` is one of
`CHARMM`, `PEOEPB` and `SWANSON`, and is passed to PDB2PQR as both `--ff` and `--ffout`. PDB2PQR 3.7
also ships `AMBER`, `PARSE` and `TYL06`, but each gives charged atoms a zero radius (53, 93 and 2269
of them on one chain of 2WCD, measured), and PHY-16 step 4's kernel width
`w_i = 0.5 R_i` is then zero, so they are refused naming the atom count rather than admitted to
fail at deposition; the stage refuses a charged atom with a radius that is not positive from any
source, `inputs.pqr` included, naming the frame and the atom. The schema had admitted any string
here, but no case carrying `charge:` was runnable before this package, so narrowing the value set
breaks no document that ran. `titration` and `forcefield` are switches whose validated defaults
are `propka` and `CHARMM` (PHY-16 step 3); any other value is a deviation that the FR-25 manifest
records. `ph` is a condition of the experiment, as `concentration_M` is, and not a deviation. The
case's `structure.source.variant` is recorded beside `Q_net`, which it is the provenance of
(OPN-04). `charge.exclusion_offset_nm` is read by stage 5 and `charge.dielectric_transition_nm`
by stage 7 (WP30; see the NOTE on the v2 keys that change a number,
which says when each is refused). `charge.smearing` is read
by stage 7's deposition (WP28; see the NOTE on `charge.smearing`).

NOTE (`charge.smearing`, PHY-16 steps 4–6, PHY-18; WP28): `sharpness`
is the `0.5` of PHY-16 step 4's `w_i = 0.5 R_i`. It is a switch whose validated default is `0.5`,
and any other value is a deviation that the FR-25 manifest records. `grid_spacing_nm` is the
spacing of the export lattice, on which the kernel is summed and the deposit's integrals are taken.
It is a discretisation choice recorded with the artefact, as `numerics.mesh.size_scale` is, and not
a deviation. A spacing above half the smallest kernel width of a charged atom SHALL be refused naming
that atom (PHY-16 NOTE on the deposition). `axis_cutoff_nm` set away from its default SHALL be
refused naming PHY-18 on every path. The deposited kernel is regular on the axis and takes no
guard, and a supplied field declares its own guard in its header (§5.3.1 NOTE on `inputs.charge`),
so the key would change nothing. The exported field declares the default `0.01 nm` for a later
re-read. As with the protonation keys, `charge.smearing` set away from its defaults beside
`inputs.charge`, or in a case carrying neither `structure:` nor `inputs.pqr`, configures a step
that does not run and SHALL be refused naming both keys.

NOTE (`inputs:`, FR-27): the optional top-level `inputs:` block is hand substitution (FR-27) applied
at stage granularity. Each key names a stage output supplied from outside — a mesh, a charge field,
a dielectric field — by path and format. A stage whose output is supplied does not run, and neither
does anything upstream of it; the substituted file is hashed by content and enters the FR-25
manifest as an input like any other. Releases before v0.3 accept an externally generated mesh
this way, which is what makes the solver core testable ahead of the meshing pipeline (§8.1).
`inputs.profile` supplies stage 4's conditioned polyline as a `nanopnp/profile/v1` document
(`format: profile1`), which is how a hand-edited contour enters a run (§8.1, GUI increment 2), and
`inputs.pqr` supplies the per-atom charges and radii of stage 7's PDB2PQR step (`format: pqr`). The
two chains are structure → density → profile → mesh and structure → PQR → charge field, and the
dielectric field comes from the density (FR-15). Supplying an artefact together with one downstream
of it on the same chain SHALL be refused, naming both. The upstream one would be hashed into the
manifest as an input to a run that never read it, and the same holds of every key: each key of
`inputs:` SHALL be read by the stage that consumes it, so that no file is hashed into the manifest
as an input to a run that never read it (FR-25, VER-47).
A supplied artefact is read by `path`. `artefact:`, a store hash, on `inputs.mesh`, `inputs.charge` or
`inputs.eps_r` SHALL be refused as an unsupported section when the case is resolved, naming the key:
no release schedules the store form of the two fields, and the mesh's is REV-62, deferred to
Phase 5 (§8.2.9 I3) (WP40).
A supplied `inputs.charge` or `inputs.eps_r` is in the model frame, beside a moved structure as
anywhere else (the NOTE on `inputs.charge`, `inputs.eps_r`; WP41).
`inputs.profile` is consumed by stage 5 (WP21). It is named by `path`
with `format: profile1`, and `artefact:` or `groups` beside it is refused. The profile is
hashed by the canonical digest of its validated payload. `structure:` beside it is refused naming
both, by the upstream rule, and so are `geometry.density` and `geometry.contour` where either is
set away from its default; `geometry.membrane` and `geometry.reservoir` are read. A section set to
its defaults is not refused, because a case dumped from its resolved document writes every section
out, and FR-26 requires that dump to load back (WP21).

`inputs.pqr` is consumed by the `protonation` stage, the first half of stage 7 (WP27, §8.2.4 D4). It is named by `path` with `format: pqr`, and `artefact:` or `groups`
beside it is refused. The file is a PQR of one frame, or one `MODEL` per frame; every frame SHALL
hold the same residues, and every atom a charge and a radius. ATOM and HETATM records are read by
the PDB columns through the coordinates and then by the two whitespace-separated numbers after
them, which is the layout PDB2PQR writes, whose coordinate fields may run together; a line those
columns do not read is read as whitespace-separated fields, and a line read both ways with
different values is refused naming its line number. A whitespace field that cannot be an atom
name, a residue name or a chain (more than four, four and one characters) does not read the line:
PDB2PQR writes a four-character residue name from the alternate-location column and runs a
four-character atom field into it (`OD2ASPP`, measured, WP27), which the columns
read. A record type run into a five-digit serial (`HETATM12345`, PDB2PQR's own layout) is split
before the fields are read. A residue is identified by chain, number and insertion code, and its
name is the one its atoms carry other than PDB2PQR's CHARMM patch names `TER` and `DISU` (a
disulfide-bonded cysteine's `CB` and `SG`, written `1CB` and `1SG`; WP27
review), or, where its atoms carry a parent and one of its
protonation variants, the variant: PDB2PQR writes a patched residue's backbone under the parent and
its side chain under the variant (`ASP` and `ASPP` in one residue). Unlike
`inputs.profile`, `inputs.pqr` stands beside `structure:`, because stage 1 still runs for the
geometry chain: there the PQR SHALL hold exactly the ensemble's frames, in order, and each frame is
registered to its stage-1 frame by superposing its Cα atoms on the ensemble's, residue for residue,
after which every heavy atom of the ensemble SHALL lie within 0.01 Å of a distinct heavy atom of the
same residue of the PQR, other than the atoms PDB2PQR's hydrogen-bond optimisation may flip: the
amide `OD1` and `ND2` of asparagine, `OE1` and `NE2` of glutamine, and the ring `ND1`, `CD2`,
`CE1` and `NE2` of histidine. A flip turns the group through 180° about the bond to it, and the
group is not symmetric about that bond, so a flipped atom lands 0.13–0.40 Å from every atom it was
given (138 heavy atoms of the prepared 2WCD, measured, WP27; the criterion is not over every heavy atom, because a flip does not exchange positions exactly and
such a criterion would refuse PDB2PQR's own output); they are not compared, their worst distance is recorded,
and the rest of each residue fixes where it is. A flip moves atoms and never removes them or changes their
element, so a residue of these three whose PQR holds fewer heavy atoms of an element than the
ensemble's is refused (WP27 review: without it a PQR missing a flippable atom registered). 0.01 Å is about ten times the rounding of a PQR's coordinate columns
and a hundredth of the shortest bond between heavy atoms, so a frame count that differs, a residue
the two do not share, or a frame whose atoms have moved is refused naming the frame. Heavy atoms the PQR adds, as PDB2PQR
adds a missing terminal oxygen, are counted, not refused; hydrogens are not compared. The
registered coordinates are what the artefact carries, so a PQR written in another frame, as the
reference's MD-frame PQRs are, lands in stage 1's. A frame whose heavy atoms already meet the
criterion where they stand is not moved, so the stage's own export reads back exactly. Without
`structure:` the coordinates are taken to be in stage 1's frame already, which is the frame the
stage exports. Beside `inputs.pqr`,
`charge.ph`, `charge.forcefield` and `charge.titration` configure a step that does not run, so any
of them set away from its default SHALL be refused naming both keys, as `geometry.density` is beside
`inputs.profile`. The same holds beside `inputs.charge`, which supplies the field stage 7 would
make of a protonation, and in a case carrying neither `structure:` nor `inputs.pqr`, which has
nothing to protonate (WP27).

NOTE (`structure:`, stage 1, FR-01 to FR-03, IF-04; WP18):
`source.path` names a PDB or mmCIF file, optionally gzipped. MDAnalysis reads PDB and gemmi reads
mmCIF. `source.selection` is an MDAnalysis selection applied to the file, and one MDAnalysis cannot
parse SHALL be refused naming the key. The selected atoms are those of the selection in the chains
`source.chains` lists. Every selected atom SHALL
carry its element in the file, in the PDB element columns or the mmCIF `type_symbol`, and a file
that leaves one blank SHALL be refused naming the atom: a guessed element is how a Cα becomes
calcium. A selection carrying alternate locations SHALL be refused naming the first, because
choosing between them is structure preparation, which the pipeline does not do. A trajectory that
does not hold the structure's atoms, and an mmCIF model that does not list model 1's atoms in model
1's order, SHALL be refused naming the file (WP18 review).

A chain is identified by its chain identifier, or by its segment identifier where the chain column
is blank. `source.chains` is `all` or a comma-separated list of chain identifiers, such as
`A,B,C`, which SHALL number `n` (a string, so the key's type is unchanged: WP18). `symmetry.point_group` is `C<n>`
with `n ≥ 1`, and any other group SHALL be refused naming the accepted form. The selected chains
SHALL number exactly `n`, and a listed chain that is absent SHALL be named (FR-03). Each chain SHALL
carry at least half the Cα atoms of the most complete chain. Chains SHALL agree in residue name at
every residue number they share, with the histidine protonation variants read as one name. A
failure of either SHALL be refused naming the chain.

The ensemble is the frames of `ensemble.trajectory` when one is given, and otherwise the models of
the source file. `frames.last_ns` keeps the frames within that many nanoseconds of the last one, by
the times the file records. A value exceeding the recorded span by more than one frame interval
SHALL be refused naming the span and the interval. A file written without a timestep reads as 1 ps
or 0 ps per frame, and without this refusal it would yield the whole trajectory in silence.
`frames.count` keeps `count` frames at the uniform stride `⌊N/count⌋`, ending on the last frame of
the window of `N` frames. A count exceeding the window SHALL be refused naming both. The selected
frame indices and their times are recorded as read. Every selected frame is superposed on the Cα
set of the earliest selected frame (FR-01). A trajectory holding no frame SHALL be refused naming
the file, and two Cα atoms at one residue number and insertion code of one chain SHALL be refused
naming the chain and the residue, since one would silently replace the other. A chain split across
the periodic box SHALL be refused naming the chain, the residue pair, the frame and the distance: in
any selected frame, two Cα of one chain at consecutive residue numbers, neither with an insertion
code, lie more than 1.0 nm apart, where a peptide-bonded pair lies 0.38 nm apart and a wrapped one
is a box length apart (QR-12; REV-19, REV-57; WP46).

`symmetry.axis: auto` takes the Cₙ axis from the ensemble-mean Cα structure by chain-permutation
superposition (FR-02). The chains are ordered by azimuth, and the whole assembly is superposed on
itself with each chain mapped to its neighbour. The axis is that rotation's eigenvector of
eigenvalue 1, through the Cα centroid. It SHALL refuse the point group, naming the measured
quantity, when the chains' azimuths are not spaced 360°/n to within a quarter of that spacing, or
when the rotation angle differs from 360°/n by more than 1°. It SHALL refuse `C1`, which has no
permutation to superpose.

The axis carries no sign of its own. It is signed to agree with the file's +z, so the structure
file SHALL point +z from the *trans* side to the *cis* side. A detected axis more than 10° from the
file's z SHALL be refused, naming the angle, because such a frame does not name an end.
`symmetry.axis: z` takes the file's z axis through its origin. Where `n ≥ 2`, it SHALL be refused
when its lateral displacement from the detected axis exceeds 0.01 nm anywhere over the Cα axial
extent, naming the tilt, the offset and the displacement. The detected axis it is measured
against passes the spacing, angle and orientation refusals above first.

The aligned frame puts the axis on z at r = 0 and keeps the file's axial coordinate, `z = â · x`. So
`geometry.membrane.centre_z_nm` is read in the frame it is written in, and stage 5 applies that
shift. The four thresholds above are constants of the code and never case keys. Their derivation
and the margins measured on the author's aligned copy of 2WCD, on 6MRT and on the ClyA-AS ensemble
are in the WP18 plan, Design §2–§4. The wwPDB entry 2WCD as deposited is not such a file: its
asymmetric unit holds two dodecamers, chains A–L and M–X, in the crystal frame, with the pore axis
22.9° from z and +z towards *trans*, so it SHALL be refused by the 10° rule like any other file. Its
chains A–L are the author's copy moved rigidly (RMSD 1e-4 nm), and moving them is structure
preparation (WP18 Outcomes).
Until stage 2 is delivered, a walk that extends past stage 1 on a case carrying `structure:` SHALL be
refused as an unsupported section naming stage 2. Once stages 2 and 3 are delivered, and until
stage 4 is, a walk that extends past stage 3 SHALL be refused in the same way, naming stage 4
(WP19). Once stage 4 is delivered, and until stage 5 is, a walk that
extends past stage 4 SHALL be refused naming stage 5 (WP20). With
stages 5 and 6 delivered, a walk runs the whole pipeline and no stage is refused on this ground
(WP21). Stage 1
alone runs through the stage command (IF-02). A case carrying `structure:` and `inputs.mesh` SHALL be refused naming both: a stage whose
output is supplied does not run, and neither does anything upstream of it (the `inputs:` NOTE), so
the structure would be recorded as an input to a run that never read it (WP18).

NOTE (`geometry.density`, stages 2 and 3, FR-04 to FR-06, CON-04, IF-05; WP19): the `geometry:` block is read on a case carrying `structure:`. Beside `inputs.mesh`
it SHALL be refused naming both, by the upstream rule of the `inputs:` NOTE. `grid_spacing_nm`
SHALL lie in [0.025, 0.05] nm (FR-04) and `sharpness` SHALL be finite and positive, and each is refused naming
its value rather than narrowed in the schema.

NOTE (`geometry.pore`, an idealised pore, IF-02, FR-09, FR-10; §8.2.22 X1): a case without
`structure:`, `inputs.profile` or `inputs.mesh` MAY declare an idealised pore,
`geometry.pore: {shape: cylinder, radius_nm}`, the membrane's thickness and the reservoir's radius
read from `geometry.membrane` and `geometry.reservoir`. Stage 5 builds the region from it: the lumen
surface `r = R`, `|z| < h/2` with `h` the membrane's thickness, is named `wall`, PHY-02's distance source set and the surface PHY-09's
`σ_s` is set on, and the membrane's cis and trans faces are excluded from it, as the bilayer's are in
the reference model. Each reservoir is the quarter disc of radius `geometry.reservoir.radius_nm`
centred on its mouth, the lumen is the domain `electrolyte` and the reservoirs are `cis` and
`trans`, and the two mouths are `interface`. Stage 6 meshes it under `numerics.mesh` and its gates,
with the size field of the §5.2.2 NOTE on an idealised pore; stages 1 to 4 and the charge stages do not run unless `inputs.charge`
supplies a field. `geometry.pore` beside `structure:`, `inputs.profile` or `inputs.mesh` SHALL be
refused naming both, and `radius_nm` not below `geometry.reservoir.radius_nm` SHALL be refused
naming both values. The solid around the lumen is the `membrane` domain, so a case declaring
`geometry.pore` SHALL set `physics.solid_permittivities.membrane` and is refused naming the key
otherwise, rather than taking ion-free water as an unlisted solid does; `geometry.membrane.thickness_nm`
defaults to the bilayer's 2.8 nm, so a solid-state pore sets it. Beside `geometry.pore`, keys that
only a structure's stages read are refused naming each: `geometry.membrane.centre_z_nm` away from 0,
which is a position in a structure's frame, and `geometry.density` or `geometry.contour` away from
their defaults; so is `numerics.mesh.backend` other than `netgen`, since the Gmsh backend's size
field is posed on a structure's region (WP57). `boundary_conditions.wall_charge_C_m2`
(PHY-09) and `numerics.mesh.maxh_nm` are read only beside `geometry.pore`, and each is refused
elsewhere naming the key.

`kernel: gaussian_vdw` takes each atom's width as `σ R_i`, with σ the `sharpness`. R_i is the
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

Stage 3 bins the map in (r, z) at `r_j = j·h`, each bin being the annulus of half-width h/2 about
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

NOTE (`geometry.contour`, stage 4, FR-07, FR-08; WP20): `isolevel`
SHALL be finite and lie in (0, 1). `simplify_tol_nm` SHALL be finite, positive and below the
density grid spacing h, because a larger tolerance discards resolved geometry and breaks the margin
of the §5.2.1 NOTE on the contour's size target. Each is refused naming its value, and the second
names h as well. `smoothing` is `taubin` or `none`. No other contour parameter and no gate
threshold is a case key: they are the constants of §5.2.1, and they key the stage-4 artefact.
Stage 4 emits a `nanopnp/profile/v1` document with `provenance.source: pipeline`, and its `sha256`
is the digest of the stage-3 payload it was drawn from. The loop runs clockwise from its lowest
vertex and stays in the stage-1 frame, so stage 5 applies `geometry.membrane.centre_z_nm` to it
exactly as to a supplied profile. The document read back through `inputs.profile` is a supplied
profile (the §5.2.1 NOTE on a supplied fixture). The conditioning and gate records belong to the
stage-4 artefact, not to the document, so a hand edit cannot carry a stale one.
A hand edit written by the desktop shell (§8.1, GUI increment 2) is a `nanopnp/profile/v1`
document with `provenance.source: hand-edit`, which is never a reference source. Its `sha256` is the
canonical digest of the profile it was edited from, or, where it was started from a loop stage 4's
gate refused (§8.2.2 B9), the digest of the stage-3 payload that loop was drawn from, as stage 4
records it. Its measurements are re-derived from its own vertices. It enters a run only through
`inputs.profile`, and is gated as a supplied profile (WP24 D5).

NOTE (`inputs.charge`, `inputs.eps_r`, IF-05, IF-03): a supplied field is named by a
pydantic-validated header document, `schema: nanopnp/field/v1`, which carries the `quantity`, its
units, the grid descriptor (origin, spacing, shape), the axis cutoff of PHY-18 (default 0.01 nm),
the declared `Q_net` where the producer knows one, the provenance of the file, and the data file it
refers to. `format: field1` names that document; the *data* format is read from it, `.npz` on the
default path, OpenDX or CCP4 through GridDataFormats, which SHALL remain optional, and
`comsolgrid` — the reference model's own `%Grid`/`%Data` interpolation table, in metres, **read
only**, since it is an input to the reference rather than an output of ours and writing it would
invite a round trip that is not one. A grid axis SHALL be uniform to round-off or the file SHALL
be refused naming the axis: the interpolant of PHY-19 takes a box and a shape, so a non-uniform
axis would otherwise be resampled onto a uniform one in silence. A header
document SHALL reject an unknown key naming the key, as every other schema in §5.3 does. `quantity`
is one of `areal_charge_density` (the reference's `rhoq_pore`, C m⁻²), `volume_charge_density`
(C m⁻³) or `solid_fraction` (dimensionless), and the `1/(2πr)` projection and the axis guard of
PHY-16 step 6 SHALL be applied to `areal_charge_density` **only** — applying them twice, or not at
all, is invisible in the conservation check of PHY-19, for the reason given there. The interpolant
SHALL be zero outside the grid box rather than continued by its edge value, and a grid whose
boundary values are not negligible against its interior SHALL be refused rather than truncated
silently. An `inputs.eps_r` field SHALL supply a solid fraction, not an absolute `ε_r`: see §4.4.
A supplied field is in the **model frame**, the frame of the mesh the solve runs on, and SHALL be
applied at that mesh's coordinates without a shift. For a case that generates its mesh, that frame
is stage 1's moved by stage 5's `z ← z − geometry.membrane.centre_z_nm`, the frame stage 7 deposits
and exports in; beside a supplied mesh it is that mesh's own. The header MAY declare the frame it
was written in as `model_frame_centre_z_nm`, the `centre_z_nm` of the case it belongs to, and stage
7's export SHALL declare it. Beside a case that generates its mesh, a declared value other than the
case's `geometry.membrane.centre_z_nm` SHALL be refused, naming both values and the offset every
feature would be applied at (QR-12). A header that declares none is read in the model frame, as
before the key existed, so no document that ran is refused (WP41 D1, REV-06).

NOTE (`inputs.mesh.groups`, IF-06, QR-12): the mapping reads **file group name → vocabulary name**.
The key is the physical-group name the mesh file carries; the value is the name the solver selects
on. Several file groups MAY map to one vocabulary name — a CAD export routinely splits one physical
wall into several curves — and the reverse is not expressible, which is why the direction is this
way round. The vocabulary is fixed and carries no aliases: materials `electrolyte`, `cis`, `trans`,
`protein`, `membrane`, `analyte`, `exclusion`; boundaries `axis`, `wall`, `membrane`,
`membrane_outer`, `cis`, `trans`, `analyte`, `interface`. `protein` is the pore's dielectric body (§2.2), a solid domain
Poisson is solved on and Nernst–Planck and the flow are not; `pore` is deliberately **not** a name,
because it reads as both that body and the lumen fluid, and a mesh that uses it SHALL disambiguate
through the mapping. `interface` is the interior fluid-to-fluid seam a fragmented region carries —
the pore-mouth interfaces the reservoir-to-lumen split leaves behind — and, in a region stage 5
generates, every solid-to-solid seam: the protein against the membrane and, with an exclusion
shell, the shell against the protein and the membrane (WP30). **Nothing
selects on it**;
it is in the vocabulary because every group must be claimed by some name, and calling an interior
seam `wall` would put it in the PHY-02 distance source set and impose no-slip across the middle of
the electrolyte. `exclusion` is the ion-exclusion region of FR-15 — the shell between the dielectric
contour and the exclusion contour, offset outward by the hydrated-ion radius. It is a solid for
Nernst–Planck and for the flow, so the no-slip surface sits at the outer edge of the shell, which is
the conventional hydrodynamic shear plane; it is **water** for Poisson, so
`physics.solid_permittivities` SHALL NOT require an entry for it and SHALL NOT abort on its absence.
Ions do not exist in it, so `⟨c⟩` has no meaning there (author ruling 13, §4.4 NOTE) and the water
is ion-free: the shell SHALL take `ε_r,f⁰` exactly, never `ε_r,f(⟨c⟩)` evaluated where the
concentrations are undefined. The resulting step at the shear plane is the salt correction of the
fluid side, which the shell by construction does not carry.
ePNP-NS carries no explicit Stern layer, so a mesh presenting this material is a deviation from the
validated model and SHALL be recorded as one in the run provenance (FR-25), even though no case-file
switch selects it. Ingestion SHALL abort when any group in the file is left unclaimed by the mapping,
or when any name the resolved run selects on — the boundary-condition names,
`numerics.wall_distance.sources` and the fluid material set — is supplied by no group, and the
diagnostic SHALL name both lists (QR-12). A mapping whose keys are all vocabulary names while its
values are not is almost certainly written backwards, and the diagnostic SHALL say so rather than
reporting every group unclaimed.

NOTE (a group that claims itself, IF-06): a group whose own name is already a vocabulary name needs
no entry in the mapping, and is claimed by that fact. The failure the gate exists to catch is a name
the solver does *not* speak reaching a solve unnoticed, and a name it does speak is not one of
those; requiring `wall: wall` of a mesh this implementation generated would be ceremony that a
reader learns to write without reading. Which names the run selects on is derived from the resolved
case — the model's boundary vocabulary, both electrodes, the species, the fluid material set and
`numerics.wall_distance.sources` — and never from a constant list, so the diagnostic is exactly
true of the run that produced it: *this run will select on this name, and no group supplies it*. A
selection pattern that is not a flat `a|b|c` alternation of literal names SHALL be refused rather
than parsed heuristically, since a requirement derived from a mis-parsed pattern is a gate that can
only pass.

NOTE (a solid without a permittivity, PHY-03, QR-12): `physics.solid_permittivities` is a map from
material name to relative permittivity, defaulting to empty; PHY-20 gives ε_r = 3.2 for the membrane
and 20 for the protein and the analyte, and it is not defaulted because the mesh decides which
solids exist. It is the one member of `physics:` that is not a switch, and `pb` and `pb-linear`
carry no solids, so a non-empty map beside one of them SHALL be refused as §5.3.1's other
inapplicable switches are; each value SHALL be finite and positive, and each key SHALL name a solid
material of the vocabulary, because a key naming a fluid domain (`electrolyte`, `cis`, `trans`) would
replace ε_r,f(⟨c⟩) in the electrolyte and a name outside the vocabulary would be recorded and never
applied, so case resolution refuses both naming the key (a vocabulary solid the mesh lacks is allowed);
`poisson` carries them as the coupled models do (WP26: the refusal covered all three electrostatic models, which left none of them runnable
on any mesh with a membrane). On an **ingested** mesh, a material that is
neither in the fluid set nor named in `physics.solid_permittivities` SHALL abort the run, naming the
material; for a model that carries no solids the abort SHALL say that the model cannot be posed on
a mesh with a solid domain, rather than ask for an entry the case would then refuse. Poisson is
solved over the whole domain, so the alternative is the electrolyte's ε_r about
24 times too large in a solid — a plausible wrong answer with no solver diagnostic. Meshes built in
process by the benchmark geometries keep the warning they have today; the difference is that an
ingested mesh's material names were not written by this codebase. A mesh stage 6 generates from a
profile is gated as an ingested one is: its `protein` is a structure's body, not a benchmark's, and
the same wrong answer follows from a missing entry (WP21). Rationale: boundary conditions are selected by name and the natural condition under the
`r`-weighted forms is the *free* one (§6.2, NUM-06), so an unmapped wall becomes an open boundary,
the solve converges, and the current is wrong with no residual, no gate and no diagnostic.

NOTE (`geometry.membrane`, `geometry.reservoir`, `numerics.mesh`; stages 5 and 6, FR-09, FR-10,
NUM-30; WP21): `membrane.thickness_nm`, `reservoir.radius_nm` and an
explicit `wall_h_nm` SHALL each be finite and positive, and each is refused naming its value.
Stage 5 applies `membrane.centre_z_nm` as `z ← z − centre_z_nm` and gates the junction as the
§5.2.1 NOTE on the membrane junction on any profile says. `wall_h_nm: auto` resolves to
`size_scale × min(0.05 nm, λ_D/5)`. λ_D is §6.3's `√(ε₀ ε_r,f⁰ RT / (2F² I))`, with `ε_r,f⁰`
from `electrolyte.parameters`, the case's temperature and the ionic strength I of the bulk species.
The 0.05 nm ceiling is §5.2.2's pore-boundary maximum, which the validated reference applied at
every concentration. It governs below 1.474 M, and above that NUM-30's target is finer and governs.
`ε_r,f⁰` is used rather than the concentration-corrected permittivity, so the mesh does not move
when the permittivity correction is switched. An explicit value is used as written, times
`size_scale`. `wall_for_concentration_M`, default none, takes λ_D at that concentration instead of
the case's own for `auto`, so every salt at or above it shares one mesh (§8.2.14 P10). It SHALL be
positive and finite, and is refused beside an explicit `wall_h_nm`, which it would not move. The
manifest records the run's own λ_D and NUM-30 ratio beside the design concentration and the λ_D it
sized the wall at. A resolved wall size coarser than λ_D/5 is logged and recorded in the manifest, not
refused: it is a discretisation choice, and a mesh-convergence study needs coarse meshes. §5.2.2's
other sizes are each multiplied by `size_scale`. After meshing, the mean length of the `wall`
boundary segments SHALL NOT exceed 1.15 × the resolved wall size, and the longest SHALL NOT exceed
2.0 ×, or the run aborts naming the statistic, the segment and its midpoint (QR-12). Netgen treats
the size as a target, and 1.045–1.078 and 1.25–1.62 are the measured means and maxima (WP21 plan,
Design §3). `backend: gmsh` meshes the stage-5 region with the optional backend of ADR-002, under
the §5.2.2 NOTE on its size field, and passes the same three gates. It needs the `gmsh` extra.
Without it, stage 6 refuses the run, naming the extra and the import error, whether that error is a
missing module, a native library the wheel could not load, or a library that loads and then fails
to initialise (CON-10; REV-37). The resolved case is not refused: `backend` is checked only against
the registered meshers, `netgen` and `gmsh` as shipped (§5.5). A generated mesh's key records the backend and that backend's own settings, and the Gmsh
version is recorded beside the key (WP23 D8, D9). The key's wall entry is the resolved wall size,
its source and `size_scale`, never λ_D: λ_D moves the mesh only through the wall size, so below
the 1.4741 M at which the ceiling binds a salt sweep meshes once. λ_D stays in the manifest's
sizing record beside the key (REV-16; WP46).
`maxh_nm`, default none, is the global element size of an idealised pore, finite and positive
and refused naming its value otherwise; none takes §5.2.2's global 10 nm. It is multiplied by
`size_scale` as the wall size is, and it enters the stage-6 key (the §5.2.2 NOTE on an idealised
pore).
`boundary_layer: true` is refused naming FR-11. `geometry.analyte` on a generated mesh is refused naming FR-21.
Beside `inputs.mesh`, any `numerics.mesh` key away from its default is refused naming it, because
nothing meshes and the key would change nothing.

NOTE (`electrolyte.parameters`, `electrolyte.driver`): `parameters` names the correction file the
*reference* properties are read from — `D_i^0`, `η^0`, `ϱ^0`, `ε_r,f^0` and the steric diameters
`a_i`, `a_0` — and is separate from the per-property correction models because a classical PNP-NS
run turns every correction to `none` and still needs those values. Steric diameters given under
`corrections.steric` SHALL be checked against that file and SHALL NOT override it: they are fitted
parameters of the correction set (FR-16), and a case file that could override them silently would
be a second source of truth for a physical constant. `driver` selects the argument the
concentration corrections are evaluated at: `average`, `⟨c⟩ = (1/n)Σc_i` (PHY-01), or
`ionic_strength`, which is a deviation from the validated model and is recorded as one.
`electrolyte.temperature_K` is checked against that file the same way and SHALL be refused naming
both values when it differs: every reference property, every scale and `V_T` are taken from the
file, whose fits are temperature-specific, so a case at another temperature would be solved at the
file's while its manifest recorded the case's (code review CR-1).

NOTE (a correction file outside the package, FR-16, FR-25; §8.2.22 X6, REV-122): `electrolyte.parameters`
and each `electrolyte.corrections.*.model` MAY name a file by a path, relative to the case file or
absolute, as well as by the name of an installed file. A file read by path is not pinned by the
package's version, so its content hash SHALL enter the stage-8 key and the FR-25 manifest, and the
file SHALL be listed as a deviation from the validated default; an edit of the file then misses the
cache rather than serving a stale result. A name ending in `.yaml` is a path; any other is an
installed file's name. A relative path is taken against the directory of the case file the run read,
or the working directory for a case held in memory; the manifest records the file among the run's
inputs by its absolute path and hash, and a reproduction takes a relative path against the
directory the original case was read from, so that it reads the file the run read (QR-08).

NOTE (`numerics.nonlinear`): the values shown are the NUM-16 reference settings — the monolithic
damped Newton of the reference model, 100 iterations, relative tolerance 10⁻⁶, tested on the
residual and on the relative update alike. `strategy: hybrid` and `damping: backtracking` select
the NUM-20 fallbacks, which no release schedules, so a case selecting either SHALL be refused as an
unsupported section naming NUM-20 and its fallback (WP40).

NOTE (`numerics.elements`, NUM-03): `phi` and `c_i` carry one element order; `u` is independent of
them and `p` is independent of both, so the reference implementation's own discretisation —
quadratic `phi` and `c_i` with linear `u` and `p` — is expressible. An order for `u` at or below
the order of `p` SHALL be refused unless `numerics.stabilisation` selects a mode supplying the flow
stabilisation of §6.4.2, and the refusal SHALL name both the inf-sup condition and the mode that
would permit the pair. The refusal is made when the case is loaded, so `nanopnp validate case`
and the desktop shell's commit make it with the same text as a run. All three orders are recorded
in the run provenance record (NUM-03).

NOTE (`numerics.stabilisation`, and the compatibility rule for the case schema): the value set is
the registered modes, shipped as `none | supg | reference`; a mode registered at run time widens it
(§5.5; §8.2.8 H7). `none` is the validated default and the production policy of NUM-11;
`supg` is NUM-11's flag, the streamline term alone; `reference` is the mode of NUM-14, streamline
and crosswind on the transport operator together with the flow stabilisation of §6.4.2, and is the
only shipped value permitting an equal-order velocity–pressure pair; a registered mode permits
one by declaring it (`permits_equal_order`). More generally: **widening the accepted
value set of an existing key is compatible and SHALL NOT move the schema version, because every
document that validated before still validates; adding, removing, renaming or narrowing a key SHALL
move it.** The mode a run actually solved is in its FR-25 manifest, so no artefact of an earlier
revision becomes ambiguous under a widening. From Phase 4 the identifier that a move takes names
the release that ships it (§8.2.7 G6): the first move inside v0.5 makes the schema
`nanopnp/case/v0.5`, a move inside v0.6 makes it `nanopnp/case/v0.6`, and the stable schema of v1.0
is `nanopnp/case/v1.0`, which is distinct from the retired `nanopnp/case/v1`. A release whose
packages move nothing keeps the identifier it inherited. Between that release's work packages, the
schema under its identifier may change again without a new identifier, because a pre-release makes
no compatibility promise. The manifest of every run records the package version (FR-25), and that
version settles which revision the run read. The identifier is fixed when `vX.Y.0` is
tagged. In v0.5, every case document must declare schema `nanopnp/case/v0.5` exactly, and any
other schema identifier is refused naming the expected schema and the declared identifier before
any structural validation. The earlier identifiers `nanopnp/case/v1` and `nanopnp/case/v2` are retired.

NOTE (`numerics.wall_distance`): `sources` is the boundary-name pattern the PHY-02 distance field
`d` is measured from, and its validated default is the pore wall alone. PHY-02 excludes the
membrane from the source set deliberately, so widening `sources` is a deviation from the validated
model and SHALL be recorded in the run provenance (FR-25). `max_distance_nm` is the saturation
distance beyond which the wall functions are 1 to within round-off. A value other than the
validated 3.0 nm SHALL be recorded as a deviation for the same reason: below about 1 nm the ion
wall function no longer reaches 1 inside the cap, which changes the model. A value that is not
finite and positive SHALL be refused by `resolve()`, naming the key (codebase review CR-4).

NOTE (`walls`): the wall values name the condition applied, not its absence. `ion_flux` takes
`no_flux | prescribed` and `slip` takes `no_slip | navier | free`. Under the `r`-weighted forms of
§6.2 the natural condition is the free one, so a value reading as "none applied" would silently
remove no-slip while appearing to be the validated default. The forms pose `no_flux` and `no_slip`
only, so every other value SHALL be refused by name until the condition is implemented, and the
refusal lifted in the same commit that implements it: a condition recorded in the manifest but not
applied would be a plausible wrong answer (code review CR-2).

NOTE (`outputs:`): the list selects what the run produces, and each word is refused rather than
silently ignored where it cannot be met. `current`, `transport_numbers` and `eof_rate` select scalar
quantities of interest (§6.7). Each model declares the quantities it provides (§5.4.3), and a word
the named model does not declare SHALL be refused when the case is resolved, naming the model and
the quantities it declares, rather than when stage 11 reaches it (WP26); the electrostatic models declare none, so a case naming one of them writes `outputs: []` or
`outputs: [fields]`. `fields` gates the IF-07 field export, which is off unless asked for:
the export is of order ten megabytes per solve and an envelope sweep of thousands of points would
otherwise write tens of gigabytes nobody requested. `analyte_force` requires the mesh to carry an
`analyte` material, and a case asking for it on a mesh without one SHALL abort naming the missing
material (QR-12). `rectification` is a two-point quantity, `I(+V)/I(−V)`; a case asking for it at a
single operating point SHALL be refused naming it as such, because the second bias can only come
from a sweep (FR-24) and inventing one would report a ratio the run did not measure. A sweep
(§5.3.4) SHALL therefore strip `rectification` from each member's `outputs:` and produce it in
collection, from pairs of members whose case-file assignments are equal except at
`boundary_conditions.bias_V` and whose two biases are exactly opposite. Exactly, not approximately:
a tolerance on the pairing would report the ratio of two unrelated operating points as a
rectification. A sweep asking for `rectification` whose axes produce no such pair SHALL be refused
when the plan is built, naming the axis, rather than collecting a column of absent values (QR-12).
