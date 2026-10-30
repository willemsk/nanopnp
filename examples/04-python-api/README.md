# 04 · The Python API: run, inspect, substitute, read back

**For:** the method developer (P1) who scripts nanopnp rather than calling the CLI.
**Runtime:** well under a minute. **Needs:** nanopnp installed, with the `examples` extra for the plot.
**Exercises:** IF-01, IF-07, FR-25, FR-27.

`tour.py` drives the pipeline through the stable public API, the names you import from `nanopnp`
itself, and nothing else. Every other module is internal before v1.0. The tour does four things
the command line cannot:

1. **Introspects the stages.** `Session().stages` describes every stage (its number, inputs,
   outputs and artefact schema) without importing its implementation or the solver.
2. **Runs a case with a progress callback.** `Session(store).run(Case.load(path), progress=...)`
   returns a `RunResult` holding every stage's artefact, the manifest and the run directory. Pass
   `cancel=CancelFlag()` and call `.cancel()` from another thread to stop it between stages or
   between Newton steps. A cancelled stage writes nothing.
3. **Changes an input by hand (FR-27).** `case.with_(maxh_nm=2.0)` is the same case with a finer
   element size, and a second case takes the generated mesh as a file in the place of the pore
   that made it. Each is walked to the mesh and to the materials with `session.run(..., upto=...)`.
   A walk runs its target's inputs alone, so no walk solves. Every stage's key is the hash of what
   it reads, so the finer size moves the mesh artefact's key. The materials artefact's key does
   not, because materials never read the mesh. A byte-identical copy of the mesh under another
   name keeps the same key: a mesh is identified by its content, not its path.
4. **Reads the exported fields back (IF-07).** With `fields` among the case's `outputs`, the report
   stage writes XDMF files with HDF5 heavy data: `fields_omega` over the whole domain and
   `fields_omega_w` over the fluid alone. They hold SI values at the P2 nodes, with each unit in the
   attribute's name (`phi_V`, `c_Na+_mol_m3`, `u_m_s`, `p_Pa`). The tour reads them with meshio,
   writes the potential to `fields.csv`, and plots it when matplotlib is installed. ParaView opens
   the same files.

Run every command from this directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python tour.py
```

The tour writes `tour.json`, the stage hashes of the three cases (`finer`, `supplied`, `renamed`)
and the field names it saw, for the test to read.

## What the test asserts

`tests/tier2/test_examples_04_python_api.py` runs the commands above, verbatim, from a copy of this
directory, and checks:

- a finer element size moves the mesh artefact's key, and leaves the materials artefact's key where
  it was;
- supplying the generated mesh as a file, then a byte-identical copy of it under another name,
  moves neither the mesh nor the materials artefact's key;
- the exported fields carry exactly the attribute names the IF-07 vocabulary defines for this
  model's fields: the potential, each species' concentration, the velocity and the pressure.

## Next

The API reference in the documentation lists every public name with its full docstring.
