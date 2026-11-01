# The Python interface

The Python interface builds a case, runs it, reads the result and draws its figures, in the same
store and with the same manifest as the command line. Every name on this page is exported by
`nanopnp`, and the [API reference](../_generated/reference/api.md) lists each of them with its
parameters. [Example 04](../_generated/examples/04-python-api.md) is the runnable tour.

The snippets run from a directory that holds a copy of `examples/01-quickstart/quickstart.case.yaml`.

## Build a case

A `Case` is a validated case document. Read one from a file or from text, or build a cylindrical
pore from its three sizes:

```python
from nanopnp import Case

case = Case.load("quickstart.case.yaml")
same = Case.loads(open("quickstart.case.yaml").read(), base=".")
small = Case.cylinder(concentration_M=0.1, bias_V=0.05, pore_radius_nm=2.0)
```

`Case.from_structure("2wcd-a-18-26.pdb", point_group="C12", concentration_M=0.1, bias_V=0.05)`
builds the case of a protein pore from a structure file, or from the name of a shipped structure,
whose pore axis is `z`; `orient=` takes the keywords of `orient_pore` for one that is not
([Structures and trajectories](structures.md)).

`case["boundary_conditions.bias_V"]` reads a field by its dotted path, and `case.electrolyte` reads
a section as an attribute. A case is never edited in place. `with_` returns a copy with some fields
set, and refuses a value the schema refuses:

```python
higher = case.with_(bias_V=0.1)
saltier = case.with_({"electrolyte.concentration_M": 0.2})
```

A field is named by its dotted path or by the leaf name it ends in; a mapping names a path that is
not a Python identifier. The copy keeps no file of its own, so a run of it records the case as text.
A path in a case file is read beside that file ([Case files](case-files.md)); a path that an edit
sets is made absolute against the same directory. `case.dumps()` writes the case back as text.

## Run it

A `Session` runs cases into one store. Without an argument it uses the default store of
`nanopnp env`; a directory names another:

```python
from nanopnp import Session

session = Session("store")
result = session.run(case)
```

The first run of a case solves it. A second run of the same case, in the same store, serves every
stage from the store.

`run` takes five options that choose what is walked and reported, none of which changes what is
solved:

| Option | Does |
|---|---|
| `upto="mesh"` | Stops after that stage, having run the stages it reads |
| `only=True` | Takes every upstream stage from the store, and refuses naming one that is absent |
| `progress=f` | Calls `f(fraction, message)` with a fraction that only rises, from 0 to 1 |
| `cancel=flag` | Stops at the next check when `flag.cancelled()` turns true; no run directory is written |
| `on_stage`, `on_solve`, `on_artefact` | Report; they never decide |

A `CancelFlag` is a flag to set from another thread, and a stopped run raises `Cancelled`:

```python
from nanopnp import CancelFlag

flag = CancelFlag()
result = session.run(
    case,
    progress=lambda fraction, message: print(f"{fraction:4.0%} {message}"),
    cancel=flag,
    on_stage=lambda name, index, total: print(f"stage {index + 1} of {total}: {name}"),
    on_artefact=lambda name, schema, hash, cached: print(name, hash[:8], cached),
)
```

`on_stage` is called before each stage with its name and its place in the walk. `on_artefact` is
called after each stage with the artefact's hash and whether the store already held it. `on_solve`
takes an object with three methods, `rung`, `step` and `rung_solved`, which report each rung of the
continuation ladder and each accepted Newton step. `session.stages` lists the stages without
running one: their number, name, the artefacts they read and the schema they write.

## Read the result

A `RunResult` holds the run directory, the manifest, each stage's artefact and the quantities the
case asked for:

```python
print(result.directory)
print(result.current_nA, result.conductance_nS)
print(result.quantities["transport_number"])
print(result.manifest.case_hash[:12])
print(result.files)
```

`result.quantities` is the whole mapping that `nanopnp inspect` prints, in SI; `current_nA` and
`conductance_nS` are the two most asked for, in nanoamperes and nanosiemens, and are `None` when the
case asks for none; a run stopped with `upto=` before the quantities has no quantities, and the two
properties raise `KeyError`. `result.artefacts["mesh"]` is the artefact of a stage, `result.stages`
its records in walk order (name, hash, whether it was cached, seconds), and `result.files` the files
that the file-writing stages exported ([Outputs and quantities](outputs.md)). `result.manifest` is
the record that `nanopnp reproduce` reads ([Provenance and deviations](provenance.md)).

## Draw its figures

Drawing needs the `plot` extra (`nanopnp[plot]`). Every stage with a figure draws it:

```python
figure = result.figure("mesh")
figure.savefig("mesh.png")
```

`result.field_choices()` maps each solved field's label to the name that the field plots take:

```python
axes = result.plot_field("potential", zoom_nm="lumen")
axes.figure.savefig("potential.png")

axes = result.plot_cutline("potential", along="z", at_nm=0.0)
axes.figure.savefig("cutline.png")
```

`plot_field` draws one field over (r, z); `zoom_nm="lumen"` closes in on the pore, a pair of
(r, |z|) limits in nanometres chooses another window, and `relative=True` draws a concentration
against the bulk on a logarithmic scale. `plot_cutline` draws a field along `z` at a radius or along
`r` at a height. Both return Matplotlib axes, so a figure can be placed in a panel of one's own with
`ax=`. The same figures from a terminal are `nanopnp plot`
([Outputs and quantities](outputs.md#figures)).

## Sweep

`session.sweep` plans, runs and collects a sweep over one field, into the session's store:

```python
swept = session.sweep(case, axis="bias_V", values=[0.05, 0.1, 0.15])
print(len(swept.rows), swept.rows[1]["quantities"]["current_A"])
swept.plot_iv().figure.savefig("iv.png")
```

A point warm-starts from its parent, a point one step nearer the origin, as the command-line sweep
does, and `origin=` chooses the origin by its index in `values`. `workers=` spreads the points of a
wave over processes, each pinned to one thread ([Sweeps and HPC](sweeps.md)). Each row holds the
point's assignments, its status and exit class, its quantities, and the directory of its run. `plot_iv` draws the current against the bias with the
rectification and the conductance, and refuses a sweep that is not over the bias.

## A stage of one's own

A function that reads the artefacts of earlier stages is a stage of its own. Each parameter is named
for the stage it reads, and the function returns a mapping:

```python
from nanopnp import Artefact


def pore_current(qoi: Artefact) -> dict[str, float]:
    return {"current_pA": 1e12 * qoi.summary["current_A"]}


session.register_stage(pore_current)
again = session.run(case)
print(again.artefacts["pore_current"].summary)
```

The stage runs after the stages of the pipeline and is stored like them. Its key is the hashes of
the artefacts it reads and the function's code, so an edited function is computed again and an
unedited one is served from the store. What the function reads besides its parameters, a global or a
file, is not part of the key. Only the session that registered the stage walks it, and a sweep with
`workers` above 1 refuses to start while the session holds one, because the other processes do not
hold it.

## Reopen a recorded run

`session.open` reads a run directory back into a `RunResult`, with its artefacts from the store:

```python
reopened = session.open(result.directory)
print(reopened.current_nA == result.current_nA)
```

The store must hold the run's artefacts. To compare the run with a fresh solve, use
`nanopnp reproduce`, which re-solves in a store of its own.
