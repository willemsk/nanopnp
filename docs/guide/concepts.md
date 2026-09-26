# Concepts

nanopnp turns one **case file** into one **run**, by walking a pipeline of **stages**. Each stage
emits a typed, content-hashed **artefact** into a **store**, and every run writes a **manifest**
that records how it was produced.

## The case file

A case is one YAML document, `schema: nanopnp/case/v2`, and it is the whole run specification
(IF-03): the mesh and fields it reads, the electrolyte, the boundary conditions, the physics model
and its switches, the numerics, and the quantities to report. Nothing that changes a number can be
set anywhere else. No command-line flag reaches the physics (the IF-02 configuration NOTE), so the
case file and the manifest cannot disagree about what was solved. See [Case files](case-files.md).

## Stages

The pipeline is twelve numbered stages (SPECIFICATION.md §5.2). Stages 1–5 build geometry from a
protein structure, and are the v0.9 geometry pipeline. In v0.5 the mesh and the fields are supplied
through the case's `inputs:` block, and a run walks these:

| # | Stage | Produces |
|---|---|---|
| 9 | case | the validated, resolved case |
| 6 | mesh | the ingested, gated mesh |
| 7 | charge | the fixed-charge and dielectric fields, deployed on the mesh and gated (only if the case supplies one) |
| 8 | materials | the electrolyte's correction functions |
| 10 | solve | the converged solution, reached by the continuation ladder |
| 11 | qoi | the quantities of interest |
| 12 | report | the exported fields, if asked for |

Stages 1 to 4 are the first of the geometry pipeline to arrive. For a case carrying a
`structure:` section, stage 1, `structure`, reads a PDB or mmCIF file and an optional trajectory,
superposes the frames, finds the Cₙ axis and puts it on z at r = 0. Stage 2, `density`, deposits
each frame's atoms as a density map on a 3D grid and averages the frames. Stage 3, `symmetry`,
reduces that map to (r, z) and reports how far it is from Cₙ-symmetric. Stage 4, `contour`, draws
the pore wall as the map's isolevel contour, conditions it, and gates it against the radius of
the largest sphere on the axis that clears every atom. Its output is a pore profile, the same kind
of document as the reference fixture. `nanopnp run case.yaml --upto contour` runs all four. A full
walk of such a case is refused, naming stage 5, until CAD assembly is delivered.

`nanopnp stage --list` prints the registry. Every stage is independently invocable, cancellable
and introspectable (FR-27). `nanopnp stage <name> case.yaml` runs the pipeline up to that stage and
prints its artefact.

## Artefacts and the store

An artefact is a stage's output: its payload files, the parameters that produced it, and a summary.
Its **hash** is taken over the payload and the parameters, never over file paths or timestamps, and
that hash is the cache key. Each stage's key is computed from its inputs' keys *before* it runs. A
second run that shares a stage's inputs is served from the store without recomputing it, and a run
that changes an input recomputes exactly the stages downstream of it. [Example
04](../_generated/examples/04-python-api.md) shows this happening.

An artefact may be edited by hand (FR-27). The edit is detected on load, because its hash no longer
matches, and the manifest records it as a substituted input rather than refusing it.

## The run directory and the manifest

A run writes three files: `case.yaml`, the case verbatim; `run.json`, the run record of stages,
hashes and quantities; and `manifest.json`, the provenance record (FR-25). The manifest records the
input hashes, the environment, the mesh and its quality, the charge, the materials, the solver
settings, the stabilisation mode, and every switch set away from the validated model. See
[Provenance and deviations](provenance.md).

## Gates

Wherever a number could go quietly wrong, nanopnp checks it and aborts the run instead of reporting
it (QR-12). Examples: element quality, a vertex at negative radius, charge conservation of a
supplied field, concentration positivity at every Newton iterate, the packing fraction, and the
agreement of the two current-extraction routes. A gate failure exits with code `4` and names the
gate, the offending quantity, and where it was. See [Running and exit codes](running.md).
