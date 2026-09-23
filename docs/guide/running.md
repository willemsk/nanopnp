# Running and exit codes

## The commands

| Command | Does |
|---|---|
| `nanopnp run case.yaml` | Walks the pipeline for one case and writes a run directory |
| `nanopnp stage <name> case.yaml` | Runs up to one stage and prints its artefact; `--only` refuses to compute anything upstream |
| `nanopnp stage --list` | Lists the stages, without importing any of them |
| `nanopnp inspect <path>` | Reads a run directory, a stored artefact or a record back |
| `nanopnp reproduce <run>` | Re-solves an archived run in a fresh store and compares every scalar (QR-08) |
| `nanopnp mesh cylinder\|reference` | Writes a gated mesh ([Meshes](meshes.md)) |
| `nanopnp sweep plan\|run\|collect` | Plans, dispatches and collects a sweep ([Sweeps](sweeps.md)) |
| `nanopnp validate …` | The Tier-3 COMSOL comparison harness |
| `nanopnp env` | Reports the version, the data locations and the store |

Every option is in the generated [command-line reference](../_generated/reference/cli.md).

**No flag changes what is solved.** Flags choose where output goes (`--store`, `--run-dir`), which
stages run (`--upto`, `--only`), and how much is logged. Every quantity that changes a number lives
in the case file, so the manifest records one source of truth.

## Output streams

**Standard output carries only the command's result**, as aligned text or, with `--json`, as one
JSON document you can parse. Log records and diagnostics go to standard error. `-v` logs at INFO,
including each continuation rung and Newton's progress; `-vv` logs at DEBUG. `--log-file` also writes
the log to a file.

A failure prints its diagnostic without a traceback. For a gate abort, the diagnostic *is* the
message: which gate, what value, where (QR-12). `--traceback` prints the traceback too. It is the
thing to attach to a bug report for an exit code `1`.

## Exit codes

The exit status is a contract (the IF-02 exit-code NOTE): a job array branches on it, and a member
that *failed* must be told apart from one that was *refused*.

| Code | Meaning | What to do |
|---|---|---|
| `0` | success | |
| `1` | unexpected failure | a bug: re-run with `--traceback` and report it |
| `2` | usage error | fix the command line |
| `3` | the case was refused | fix the case file; a retry fails identically |
| `4` | a numerical gate aborted | read the diagnostic: refine the mesh, fix the field, or change the operating point |
| `5` | Newton or the continuation ladder did not converge | a harder operating point; approach it from a converged neighbour (a sweep does this for you) |
| `130` | cancelled | |

Which exception maps to which code is in the generated [exit-code
reference](../_generated/reference/exit-codes.md).

## Continuation

A hard operating point, such as high salt, high bias or strong charge, is not solved cold. With
`numerics.continuation: default_ladder`, the solve climbs the fixed ladder of NUM-18. It starts from
Poisson–Boltzmann and equilibrium PNP, ramps the fixed charge and then the bias, switches on the flow,
then the corrections, then the steric flux, and finally sweeps the salt to its target. Each rung
starts from the last converged state, and every rung is recorded. `-v` shows them. Because the ladder
is a fixed path, a case that switches the flow or its terms off is refused under it: use
`numerics.continuation: none` for such an ablation (the NUM-18 NOTE). A sweep continues the same way
across its points: each member starts from a converged neighbour.
