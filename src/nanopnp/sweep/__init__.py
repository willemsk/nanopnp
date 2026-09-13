"""Parameter sweeps, job-array dispatch, result collection (FR-24, SPECIFICATION.md §5.3.4).

A sweep is a set of runs, not a pipeline stage: it produces no field, and a stage
keyed on thousands of upstream artefacts has no meaningful key and no meaningful
progress fraction. So this package is a driver over :mod:`nanopnp.io.run`,
registered in no stage registry, in four modules:

- :mod:`~nanopnp.sweep.document` — the ``nanopnp/sweep/v1`` specification: a base
  case and axes of dotted-path assignments.
- :mod:`~nanopnp.sweep.plan` — the points, the warm-start forest, and everything
  checked before a solve.
- :mod:`~nanopnp.sweep.run` — one member, one wave, or a whole plan across
  independent workers.
- :mod:`~nanopnp.sweep.collect` — the members' records into one dataset, and the
  rectification.

Nothing here is imported at module scope by the CLI: ``import nanopnp.cli`` stays
at the ~70 ms the deferred-import rule protects, and a job-array member pays the
NGSolve import once rather than the whole package's.
"""
