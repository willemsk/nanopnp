# Worked examples

Five examples, each a directory under `examples/` in the repository with a README, the case and
sweep files it runs, and any script. The pages below are those READMEs, verbatim. Every command in a
README's tagged blocks is **executed by a test**, word for word, from a copy of the directory, and
each example asserts a property of the model rather than a transcribed number (VER-46).

| Example | For | Shows |
|---|---|---|
| [01 Quick start](../_generated/examples/01-quickstart.md) | anyone new | mesh, run, inspect and reproduce one case |
| [02 A charged pore](../_generated/examples/02-charged-pore.md) | P2 | a supplied fixed-charge field; ePNP-NS against classical PNP-NS; deviations |
| [03 An I–V sweep](../_generated/examples/03-iv-sweep.md) | P2 | sweeps, waves, rectification, and a symmetric control |
| [04 The Python API](../_generated/examples/04-python-api.md) | P1 | the public API, hand substitution, and reading exported fields |
| [05 The ClyA reference](../_generated/examples/05-clya-reference.md) | P1, P2 | the reference geometry, a frozen validation case, and a SLURM submission |

Examples 01–04 run on an idealised cylindrical pore and take seconds to a minute each. Example 05's
solve takes tens of minutes on the reference mesh, so its test is recorded rather than gated. Its planning
step runs on every push.

To run one, copy its directory and run its commands from inside it. Case paths resolve against the
working directory.

!!! note "No number here is a prediction"
    The idealised pore's meshes are the smallest the solver accepts, chosen to be quick, not
    converged. The examples show how nanopnp is driven and what it guarantees. They do not show
    validated values of the current. Those come from the reference geometry, at converged
    resolution, compared against the reference model and experiment (§7.4, §7.5).
