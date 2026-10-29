# 02 · The physics: the model's corrections and the salt

**Area:** `physics`. **Time:** twenty to forty minutes.

## The task

Your pore carries a fixed negative charge, which is what lets a pore choose between ions. Solve
it with the full model and as classical PNP-NS, and then in a ten-times saltier electrolyte. Find
out what the corrections change, and what the salt changes.

## You start with

- `ring.field.yaml`: the fixed charge, a ring of negative charge inside the membrane at mid-length,
  just behind the pore wall.
- `epnpns.case.yaml`: the pore with that charge in 0.1 M NaCl at a positive bias, with the validated
  model: every correction on.
- `classical.case.yaml`: the same case with every correction set to its `none` model.
- `epnpns-1M.case.yaml`: the validated case in 1 M NaCl.

Work in this directory. `inputs.mesh.path` in the case files resolves against the working directory.

## Steps

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out pore.msh
$ nanopnp run epnpns.case.yaml --store store --run-dir run-epnpns
$ nanopnp run classical.case.yaml --store store --run-dir run-classical
$ nanopnp run epnpns-1M.case.yaml --store store --run-dir run-epnpns-1M
$ nanopnp inspect run-classical
```

1. `mesh cylinder` writes the geometry; the three runs share it.
2. The first run is the validated model at 0.1 M.
3. The second differs from the first only in `electrolyte.corrections`.
4. The third differs from the first only in `electrolyte.concentration_M`.
5. `inspect` reads the classical run back. Read the others the same way.

The runs print the cation transport number, the share of the current the cations carry.

## What to expect

- At 0.1 M the cations carry more than half of the current under both models: a negative fixed
  charge draws cations into the pore.
- The classical run lists each `none` correction as a deviation from the validated model; the
  validated runs list none.
- At 1 M the cation share falls towards that of an uncharged pore: the larger salt screens the
  fixed charge.

If what you see differs, that is a finding.

## Then try

Flip the sign of the ring, in a copy of the field file, and run it at 0.1 M.
The pore should now favour the other ion.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.
