# 04 · The Python interface, in a notebook, with a step of your own

**Area:** `api`. **Time:** twenty to forty minutes. **Needs:** the `notebook` extra, as the protocol installs it.

## The task

You want to drive the program from Python rather than from the command line. Run a case with
progress reports and stop another, read the result, put your own mesh in the place of the case's,
edit the case, and add a stage of your own to the pipeline.

## You start with

- `notebook.py`: a [marimo](https://marimo.io) notebook that does each of these on a charged pore in
  0.1 M NaCl, keeping what it computes in `store/` beside it, which it empties each time it starts.
- `selectivity.py`: a stage of your own. It reads the quantities of interest and says which ion
  carries more than half of the current.
- `ring.field.yaml`: the fixed charge, a ring of negative charge inside the membrane.

Work in this directory.

## Steps

Open the notebook and read it cell by cell:

```console
$ marimo edit notebook.py
```

Its cells run on their own as well. This runs every cell in turn, which is what the nightly test does:

<!-- example: run -->
```console
$ python notebook.py
```

1. A run is stopped as its solve is about to start.
2. The same case runs with progress reports, and its result is read back: the current, the fields
   and which stages were computed.
3. A finer mesh is put in the place of the case's own, and the stages that depend on it are walked.
4. A `charge:` section is added to the case, and it is run again.
5. `selectivity.py` is registered as a stage and walked.

## What to expect

- The run that was stopped stored no solve: in the run after it, the solve is computed, not stored.
- Putting in the finer mesh changes the mesh stage's key and leaves the materials stage's key where
  it was.
- Adding the `charge:` section changes no solve key: the solve is taken from the store, and what
  reads the case afterwards is computed again.
- The stage you added comes after the report, and the transport number in its verdict is the one the
  result reports.

If what you see differs, that is a finding.

## Then try

Change `selectivity.py` so that the stage reads the solve instead of the quantities of interest.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.
