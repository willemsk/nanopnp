---
type: Test Evidence
title: 'Tier-1 test evidence: import costs, trajectory precision and the gate''s pipefail
  trap (WP45 item 24)'
---

## Tier-1 test evidence: import costs, trajectory precision and the gate's pipefail trap (WP45 item 24)

- **[tested]** Import costs under `python -X importtime`, measured for VER-72: `scipy.sparse` ~260 ms, `meshio` ~170 ms, `h5py` ~140–180 ms (`ngsolve` ~370 ms and `numpy` ~67 ms are recorded above). These are why the deferred-import rule names them. Source: `tests/tier1/test_source_conventions.py`.
- **[verified]** NumPy and the BLAS behind it read the thread variables when they are imported and size their pool then, so setting them afterwards has no effect. A forked worker inherits a parent that has already imported NumPy; the sweep pool therefore uses `spawn`, which is also the only start method Windows has. Source: `tests/tier1/test_sweep_cli.py` (`test_ver38_the_thread_pinning_is_set_before_numpy_is_imported`).
- **[tested]** A DCD stores its timestep as a float32: 1 ps reads back as 1.0000000328 ps and 10 ps as 9.99999996 ps, so times accumulated as `frame · dt` drift in opposite directions. The `last_ns` window is therefore taken per frame, and the frame exactly `last_ns` before the last one is always inside. Source: `tests/tier1/test_structure_stage.py` (`test_ver48_the_last_ns_window_does_not_depend_on_the_float32_timestep`).
- **[tested]** TRR stores float32 nanometres, so the ångström-to-nanometre conversion costs up to two float32 ulps at 13 nm (`2 × 2⁻²³ × 13 nm = 3.1 × 10⁻⁶ nm`); XTC quantises to 0.001 nm and rounds by half of that, plus float32 round-off. Source: `tests/tier1/test_structure_stage.py`.
- **[verified]** `grep -q` exits at the first match; under `pipefail` the writer's SIGPIPE once made a tracked Gmsh change read as a miss in the hook's Gmsh requirement check. Source: `tests/tier1/test_workflow_hooks.py` (`test_gate_hook_requires_gmsh_for_a_tracked_change_beside_an_untracked_file`).

