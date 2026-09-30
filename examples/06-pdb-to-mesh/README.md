# 06 · From a PDB entry to a mesh

**For:** anyone bringing their own pore structure: the method developer (P1) or the collaborating
computational scientist (P2) who has a PDB entry and wants a mesh from it.
**Runtime:** about a minute. **Needs:** nanopnp with the `structure` extra, as the
getting-started page of the documentation installs it.
**Exercises:** IF-02, IF-04, IF-05, FR-01 to FR-10, FR-27, QR-12.

The cytolysin A pore (ClyA), as deposited in the Protein Data Bank (entry 2WCD), taken through
the geometry pipeline: structure, density, symmetry, contour, region and mesh. The run stops at
the mesh, so nothing is solved. Along the way you export what the stages store, in formats other
tools read, and feed the pore profile back in as an input.

Run every command from this directory. Paths in the case files resolve against the working
directory, not against the case file. In a development checkout, put `uv run` in front of each
command.

## The deposited entry is refused

<!-- example: refused -->
```console
$ nanopnp stage structure deposited.case.yaml --store store
```

`deposited.case.yaml` points stage 1 at the entry exactly as deposited, chains A to L. Stage 1
finds the pore axis itself, by superposing the twelve chains on one another. It then refuses the
file: the axis is more than 10° from the file's z. The command exits `4`, the class of a gate that
stopped the run, and names the gate, the angle and the limit.

The limit is there because stage 1 uses the file's +z to tell the two ends of the pore apart.
It must point from the *trans* side to the *cis* side. A file tilted this far says nothing
reliable about which end is which, so nanopnp does not guess. Stage 1 never re-orients a
structure, because that would be a silent decision about the biology. Preparing the file is your
job.

## Prepare it, then walk the pipeline

<!-- example: run -->
```console
$ python prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb
$ nanopnp run 2wcd.case.yaml --store store --run-dir run --upto mesh
$ nanopnp stage structure 2wcd.case.yaml --store store --export aligned.pdb
$ nanopnp stage structure aligned.case.yaml --store store
$ nanopnp stage density 2wcd.case.yaml --store store --export density.mrc
$ nanopnp stage symmetry 2wcd.case.yaml --store store --json
$ nanopnp stage contour 2wcd.case.yaml --store store --export contour.profile.yaml
$ nanopnp run from-profile.case.yaml --store store --run-dir run-profile --upto mesh
$ nanopnp inspect run-profile
```

1. **`python prepare.py`** is one way of preparing the entry, and it uses no nanopnp code. It
   keeps chains A to L, protein only. It estimates the pore axis from the shape of the C-alpha
   cloud, points +z at the wide cap of ClyA, which faces *cis*, and turns the axis onto z. It
   then places the C-alpha centroid of residues 8 to 292 at z = 5.655 nm. That puts the bilayer
   centre at z = 0, so the case keeps `geometry.membrane.centre_z_nm` at its default. The
   script's docstring says why each step is enough.
2. **`nanopnp run … --upto mesh`** walks stages 1 to 6 and stops. Stage 1 finds the exact axis
   and aligns the structure. Stage 2 smears its atoms into a 3D density map. Stage 3 averages
   the map about the axis to an (r, z) map. Stage 4 draws the pore's outline from it. Stage 5
   places the membrane and reservoirs around that outline, and stage 6 meshes the result. Every
   stage is gated, every artefact goes into `store/`, and `run/manifest.json` records each one.
3. **`stage structure … --export aligned.pdb`** writes stage 1's aligned structure as a PDB,
   with `aligned.dcd` beside it holding every frame. The stage is served from the store, so
   nothing is recomputed. Open the PDB in a molecular viewer to see the frame nanopnp works in.
4. **`stage structure aligned.case.yaml`** reads that export back with `symmetry.axis: z`,
   which takes the file's z axis as the pore axis instead of finding it. Stage 1 still checks the
   claim against the axis it detects, and accepts it.
5. **`stage density … --export density.mrc`** writes the density map as CCP4/MRC, in
   ångströms, the unit viewers expect. Load it over `aligned.pdb` and the map sits on the
   atoms. `.dx`, `.ccp4` and `.map` work too, and `.npz` gives nanopnp's own format.
6. **`stage symmetry … --json`** prints stage 3's summary. It records where the 12-fold average
   varies most around the axis, and where the part of that variation which is not 12-fold is
   largest. A structure that is not the symmetric assembly it claims to be shows up here.
7. **`stage contour … --export contour.profile.yaml`** copies stage 4's profile out of the store,
   byte for byte. It is a `nanopnp/profile/v1` document, with `source: pipeline` in its
   provenance.
8. **`run from-profile.case.yaml`** supplies that document through `inputs.profile`. Stages 1
   to 4 do not run, and stage 5 starts from the file. The mesh is the same mesh, with the same
   content hash, but it is filed under a different key, because it came from a different input.
9. **`inspect run-profile`** reads that run's manifest back. Its `inputs.files` records the
   profile by its hash, and no stage 1 to 4 artefact appears.

The four case files differ only in `structure:` or `inputs.profile`, and in their names. They share
one electrolyte on purpose: the automatic wall element size of the mesh reads the Debye length,
so a different concentration can give a different mesh.

## What the test asserts

`tests/tier2/test_examples_06_pdb_to_mesh.py` runs both blocks above, verbatim, from a copy of
this directory. It checks properties rather than transcribed numbers (SPECIFICATION.md VER-46):

- the deposited entry is refused by the orientation gate, with an angle above its limit;
- the prepared entry passes every gate of stages 1 to 6, and the manifest records exactly the
  case and those six artefacts;
- the aligned export passes stage 1 under `symmetry.axis: z`;
- `density.mrc`, read in ångströms as a viewer reads it, contains every heavy atom of
  `aligned.pdb`, and reads at least the smallest value one atom's Gaussian can give at the grid
  node nearest its centre;
- `contour.profile.yaml` is the stored document, byte for byte, and loads as a pipeline profile;
- the profile run moves the region and mesh keys, keeps the mesh content hash, and records no
  stage 1 to 4 artefact.

## Next

- *Structures and trajectories* and *From a structure to a mesh*, in the documentation's user
  guide, cover every key these cases use, trajectories, and editing a profile by hand.
- [01](../01-quickstart/README.md) solves a case on a mesh supplied as a file.
