# 01 · Quick start: mesh, run, inspect, reproduce

**For:** anyone new to nanopnp; the collaborating computational scientist (P2) who runs
case files from the command line.
**Runtime:** well under a minute. **Needs:** nanopnp installed (the getting-started page of the documentation).
**Exercises:** IF-02, IF-06, FR-23, FR-25, QR-08.

An uncharged cylindrical pore through a membrane, in 0.1 M NaCl at +50 mV, solved with the
validated ePNP-NS model: every correction of the model on, at its published parameters. You
generate the mesh, run the case, read the run back and check that it reproduces.

Run every command from this directory. `inputs.mesh.path` in the case file resolves against the
working directory, not against the case file. In a development checkout, put `uv run` in front
of each command.

## The commands

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out pore.msh
$ nanopnp run quickstart.case.yaml --store store --run-dir run
$ nanopnp inspect run
$ nanopnp reproduce run
```

1. **`nanopnp mesh cylinder`** writes an idealised pore as a Gmsh MSH 4.1 file. It gates the
   mesh on element quality before writing it, and prints the mesh's content hash and the
   `inputs.mesh.groups` block a case needs to read it. The defaults are the smallest mesh the
   solver's wall-distance gate accepts with the wall corrections on, so the run is quick. They
   are not converged. `nanopnp mesh cylinder --help` lists the geometry flags.
2. **`nanopnp run`** walks the pipeline: case, mesh, materials, solve, quantities, report. It
   prints one line per stage with its artefact hash, then the quantities of interest. Every
   artefact goes into `store/`, keyed by its content hash, and the run directory `run/` gets
   three files: `manifest.json`, the provenance record; `case.yaml`, the case verbatim; and
   `run.json`, the run record.
3. **`nanopnp inspect run`** reads the manifest back: input hashes, library versions, the mesh
   and its quality, the solver settings, the stabilisation mode, and the deviations from the
   validated model. This case has none.
4. **`nanopnp reproduce run`** solves the archived case again, in a throwaway store so nothing
   is served from cache, and compares every recorded scalar. It exits `0` only if all of them
   agree to the tolerance. Differences in library, interpreter or platform are reported, not
   failed, unless you pass `--strict-environment`.

## What the test asserts

`tests/tier2/test_examples_01_quickstart.py` runs the four commands above, verbatim, from a copy
of this directory. It checks properties of the model rather than transcribed numbers
(SPECIFICATION.md VER-46):

- every command exits `0`, so the reproduction agreed;
- the two current-extraction routes of FR-23 agree to the tolerance the solver itself gates on;
- the manifest records no deviation from the validated model.

## Next

- [02](../02-charged-pore/README.md) adds a fixed charge and compares against classical PNP-NS.
- The case file is documented field by field in the case-file reference of the documentation.
