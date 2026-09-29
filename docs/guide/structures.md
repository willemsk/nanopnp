# Structures and trajectories

Stage 1, `structure`, is where a protein enters nanopnp. It reads a structure file and, optionally,
a trajectory. It checks that the file holds the symmetric assembly the case says it does, finds
the pore axis, and aligns everything so that the axis lies on z at r = 0. Everything downstream
works in that frame. The contract is the §5.3.1 NOTE on `structure:` in the
[specification](../_generated/model/specification.md#531-case-file); this page says what it means
in practice.

A case with a `structure:` section walks the whole pipeline, from stage 1 to the mesh and on to
the solve. See [From a structure to a mesh](geometry.md) for stages 2 to 6, and
[example 06](../_generated/examples/06-pdb-to-mesh.md) for a PDB entry taken all the way to a mesh.
Stages 1 to 4 need the `structure` extra, which installs MDAnalysis, gemmi and the other
libraries they read and draw with.

```yaml
structure:
  source:
    path: 2wcd-prepared.pdb
    chains: A,B,C,D,E,F,G,H,I,J,K,L    # or: all
    selection: protein                 # an MDAnalysis selection
  symmetry: {point_group: C12}         # axis: auto, the default
```

## The file

`structure.source.path` names a PDB or mmCIF file, optionally gzipped (`.pdb`, `.ent`, `.cif`,
`.mmcif`). MDAnalysis reads PDB and gemmi reads mmCIF. The path resolves against the working
directory, like every path in a case.

`source.selection` is an MDAnalysis selection string, `protein` by default. The density map is
built from exactly the atoms it selects, so it decides what counts as the pore: whether hydrogens
are deposited, whether a bound ligand is part of the wall. A selection MDAnalysis cannot parse is
refused, naming the key.

Two things are refused rather than guessed:

- **An atom without an element.** Every selected atom must carry its element in the file, in the
  PDB element columns or the mmCIF `type_symbol`. A guessed element is how a C-alpha becomes
  calcium, and the radius the density map gives it would then be wrong.
- **Alternate locations.** Choosing between them is structure preparation, so a selection that
  carries any is refused, naming the first.

## Chains

A chain is its chain identifier, or its segment identifier where the chain column is blank.
`source.chains` is `all`, or a comma-separated list such as `A,B,C`. The selected chains must
number exactly the n of `symmetry.point_group`, which is written `C<n>`: ClyA is `C12`,
α-hemolysin `C7`, MspA `C8`. A listed chain that is absent is named. Each chain must carry at least
half the C-alpha atoms of the most complete one, and the chains must agree in residue name at
every residue number they share, with the histidine protonation variants read as one name. A file
that fails any of these is not the assembly the case describes, and it is refused naming the
chain.

## Ensembles and frames

Without a trajectory, the ensemble is the models of the structure file: one frame for most
crystal structures, several for an NMR entry. With one, it is the trajectory's frames:

```yaml
structure:
  source: {path: system.pdb, selection: protein}
  ensemble:
    trajectory: production.dcd       # DCD, XTC, TRR or NetCDF
    frames: {last_ns: 5, count: 50}
  symmetry: {point_group: C12}
```

The trajectory must hold the structure's atoms, or it is refused naming the file. `frames.last_ns` keeps the frames
within that many nanoseconds of the last, by the times the file records. `frames.count` then keeps
that many frames at a uniform stride, ending on the last frame. Both are optional. Every selected
frame is superposed on the C-alpha atoms of the earliest one, and the frame indices and times are
recorded as they were read.

!!! warning "A trajectory written without a timestep"
    Some writers leave the timestep out, and the file then reads as 1 ps or 0 ps per frame.
    `last_ns: 5` on such a file would quietly keep every frame, so a value longer than the recorded
    span, plus one frame interval, is refused naming both. Check the times your trajectory
    records before relying on `last_ns`, or select frames by `count` alone.

The Tier-3 test of the reference ensemble, in `tests/tier3/conftest.py` of the repository, is a
worked case of an MD trajectory selected this way. Its data is not distributed with nanopnp.

## The axis

`symmetry.axis: auto`, the default, finds the pore axis by superposing the assembly on itself with
each chain mapped onto its neighbour. The axis of that rotation is the pore axis. This is used
rather than the principal axes of the atoms because it averages out the chains' uneven
fluctuations, so it barely moves from frame to frame, where the principal axes drift.

The rotation is gated. It is refused, naming the measured quantity, when the chains' azimuths are
not evenly spaced to within a quarter of 360°/n, or when its angle differs from 360°/n by more than
1°. `C1` has no rotation to find, so it is refused with `axis: auto`. The thresholds are constants
of the code, not case keys, and the specification's NOTE gives them with their derivation.

**The axis has no direction of its own, so the file supplies one.** The axis is signed to agree
with the file's +z, and the file's +z must point from the *trans* side of the membrane to the
*cis* side. A detected axis more than 10° from the file's z is refused, naming the angle, because
a frame that far off says nothing reliable about which end is which. A crystal structure in its
deposited frame is often refused here. [Example 06](../_generated/examples/06-pdb-to-mesh.md)
starts with exactly that refusal.

`symmetry.axis: z` takes the file's z axis through its origin as the pore axis, for a file that is
already aligned. It is still checked: where n ≥ 2, stage 1 detects the axis as above, and refuses
`z` if it strays from the detected axis by more than 0.01 nm anywhere along the C-alpha extent,
naming the tilt, the offset and the displacement.

## The frame stage 1 produces

The aligned frame puts the axis on z at r = 0. It keeps the file's own axial coordinate, so a
height read off your structure file is the same height in nanopnp. The first chain in file order
lies on +x and the others follow counter-clockwise. This is the frame of stages 1 to 4, and of
every profile document they produce.

The membrane is not placed here. `geometry.membrane.centre_z_nm` is the bilayer's centre on that
axial coordinate, and stage 5 subtracts it, so the model frame has the bilayer centred at z = 0.
See [From a structure to a mesh](geometry.md#registering-the-membrane).

## Preparing a structure is your job

nanopnp never re-orients, completes or repairs a structure. Each of those is a decision about the
biology, and a pipeline that made one silently would be making it for you. Before stage 1, a
structure should:

- hold one assembly, with the chains you want and nothing else selected;
- have its missing residues or loops completed where they line the pore, with a tool of your
  choice such as PDBFixer or Modeller;
- carry an element on every atom and no alternate locations;
- have its pore axis within 10° of z, with +z pointing to *cis*.

`examples/06-pdb-to-mesh/prepare.py` is one way of doing the last step, with MDAnalysis and
NumPy alone. It uses no nanopnp code, because preparation is outside the pipeline.

## Reading the result

`nanopnp stage structure case.yaml` runs stage 1 and prints its artefact. The summary records the
source and trajectory digests, the selection, the chains in cyclic order, the frames, the
superposition RMSD, the axis in the file's frame and the rotation that took it to z, and every gate
measurement beside its threshold.

```console
$ nanopnp stage structure case.yaml --store store --export aligned.pdb
```

`--export aligned.pdb` also writes the aligned ensemble as a PDB of its first frame, with
`aligned.dcd` beside it holding every frame, both in ångströms. Open them in a molecular viewer to
see the frame nanopnp works in. A case that points at the exported PDB can use `axis: z`. The
[Desktop shell](desktop.md)'s Geometry tab shows the same record.
