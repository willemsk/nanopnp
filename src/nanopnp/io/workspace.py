"""The scratch directory a stage writes its payload into (SPECIFICATION.md section 5.3.2)."""

from __future__ import annotations

from pathlib import Path

__all__ = ["MissingWorkspaceError", "WorkspaceInUseError", "require_workspace", "scratch_directory"]

_MAX_NAMED = 5


class MissingWorkspaceError(ValueError):
    """A stage that writes a payload was run without the workspace to write it in."""


class WorkspaceInUseError(ValueError):
    """A stage was about to write into a workspace that already holds files."""


def require_workspace(workspace: Path | None, stage: str) -> Path:
    """Return ``workspace``; MissingWorkspaceError if the stage was given none."""
    if workspace is None:
        raise MissingWorkspaceError(
            f"The {stage} stage writes a payload and has no workspace. Construct it with "
            "workspace=<directory>, the scratch folder that it writes into. The store root is "
            "not a scratch folder that a stage can pick for itself."
        )
    return workspace


def scratch_directory(workspace: Path | None, stage: str, *, overwrite: bool = False) -> Path:
    """Return ``workspace``, created, for ``stage`` to write into.

    Raises MissingWorkspaceError if the stage was given none, and WorkspaceInUseError if the
    workspace already holds files and ``overwrite`` is false.
    """
    directory = require_workspace(workspace, stage)
    if not overwrite and directory.is_dir():
        held = sorted(entry.name for entry in directory.iterdir() if entry.is_file())
        if held:
            named = ", ".join(held[:_MAX_NAMED]) + (", ..." if len(held) > _MAX_NAMED else "")
            raise WorkspaceInUseError(
                f"The {stage} stage writes into {directory}, and that folder holds {named}. A "
                "second run overwrites a payload that an earlier artefact points at. Give the "
                "stage an empty workspace. Or construct it with overwrite_workspace=True to "
                "replace those files."
            )
    directory.mkdir(parents=True, exist_ok=True)
    return directory
