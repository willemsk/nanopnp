---
type: Library Behaviour
title: 11. A stage's workspace falls back to the process store root, not the run's
  store
description: A stage's workspace falls back to the process store root, not the run's
  store.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  netgen-mesher: 6.2.2606
---

## 11. A stage's workspace falls back to the process store root, not the run's store **[tested: pending]** {#11-a-stages-workspace-falls-back-to-the-process-store-root-not-the-runs-store}

`mesh/ingest.py`, `charge/stage.py`, `solve/stage.py` and `post/stage.py` each fall back to
`store_root() / "tmp"` plus a `mkdtemp` when constructed without a workspace — and `store_root()`
is `$NANOPNP_STORE` or `./nanopnp-store`, the *process* default, never the `Store` the caller
handed the run. Running the test suite from a checkout therefore left a `nanopnp-store/tmp/mesh-*`
behind while every artefact lived in a `tmp_path` store.

`pipeline.run.run_case` now names a fresh workspace under the store in use when the caller gives none.
Fresh per run and not a fixed `tmp/mesh`: two runs into one store hold different meshes, and a
deterministic name has the second overwrite a file the first's artefact still points at.

