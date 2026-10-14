"""The scratch directory a stage writes its payload into (SPECIFICATION.md section 5.3.2)."""

from __future__ import annotations

from pathlib import Path

__all__ = ["MissingWorkspaceError", "scratch_directory"]


class MissingWorkspaceError(ValueError):
    """A stage that writes a payload was run without the workspace to write it in."""


def scratch_directory(workspace: Path | None, stage: str) -> Path:
    """Return ``workspace``, created; MissingWorkspaceError if the stage was given none."""
    if workspace is None:
        raise MissingWorkspaceError(
            f"the {stage} stage writes a payload and was given no workspace: construct it with "
            "workspace=<directory>, the scratch folder it writes into. The store root is not a "
            "scratch folder a stage may pick for itself"
        )
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace
