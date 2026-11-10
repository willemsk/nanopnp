---
type: Library Behaviour
title: 11. A stage never picks its own workspace
description: A stage built without a workspace is refused; the run driver makes a fresh scratch under the store in use.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  netgen-mesher: 6.2.2606
verified:
- by: process:tests/tier1/test_stage_workspace.py::test_ver25_no_workspace_stage_picks_a_scratch_directory_of_its_own
  at: '2026-10-16T00:00:00Z'
---

## 11. A stage never picks its own workspace **[tested: tests/tier1/test_stage_workspace.py::test_ver25_no_workspace_stage_picks_a_scratch_directory_of_its_own]** {#11-a-stages-workspace-falls-back-to-the-process-store-root-not-the-runs-store}

A stage built without a workspace raises `MissingWorkspaceError`
(`io/workspace.py`, `scratch_directory`); none falls back to the process's store root or a `mkdtemp`
of its own. The run driver makes a fresh scratch under the store in use (`pipeline/run.py`,
`_scratch`), so two runs into one store never share a file: a deterministic name would have the
second overwrite a file the first's artefact still points at.
