# 01 · The command line: from a case file to a reproduced current

**Area:** `cli`. **Time:** twenty to forty minutes.

## The task

You model a membrane pore and have a case file for it. Check the case, solve it, read back what was solved and with which settings, and show that someone else can
reproduce your current.

## You start with

- `pore.case.yaml`: an uncharged cylindrical pore through a membrane, in 0.1 M NaCl at a positive
  bias, with the model's corrections on.

Work in this directory. The case declares the pore's geometry, which the run meshes.

## Steps

<!-- example: run -->
```console
$ nanopnp validate case pore.case.yaml
$ nanopnp run pore.case.yaml --store store --run-dir run-pore
$ nanopnp inspect run-pore
$ nanopnp plot run-pore solve --out fields.png
$ nanopnp reproduce run-pore
```

1. `validate case` checks the case file without solving.
2. `run` meshes the pore, walks the pipeline, keeps every artefact in `store/` and writes a run
   directory.
3. `inspect` reads the run directory back.
4. `plot` draws the solved fields and the solver's convergence to `fields.png`.
5. `reproduce` solves the archived case again, from nothing, and compares what it recorded.

## What to expect

- The two ways the program extracts the current agree.
- The run lists no deviation from the validated model.
- `reproduce` agrees with the original run.
- Reversing the bias reverses the current and leaves its magnitude where it was, to within the
  accuracy of the mesh: an uncharged pore is its own mirror image.

If what you see differs, that is a finding.

## Then try

Reverse the bias in a copy of the case and run it.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.
