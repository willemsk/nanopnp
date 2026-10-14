"""VER-35, QR-12: the reproduction check names a moved input by its path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.pipeline.reproduce import (
    InputMovedError,
    check_inputs,
)

# On Windows the path separator supplies the backslash ``repr`` would double; on
# POSIX a backslash in the file name does, and is a legal name there.
AWKWARD_NAME = "mesh.vol" if os.name == "nt" else "back\\slash.vol"


def _manifest(path: Path, *, sha256: str) -> dict[str, Canonicalisable]:
    return {"inputs": {"files": {"mesh": {"path": str(path), "sha256": sha256}}}}


def test_ver35_a_moved_input_is_named_by_its_path_not_its_repr(tmp_path: Path) -> None:
    mesh = tmp_path / AWKWARD_NAME
    mesh.write_bytes(b"original\n")
    manifest = _manifest(mesh, sha256=file_hash(mesh))
    mesh.write_bytes(b"edited\n")

    with pytest.raises(InputMovedError) as moved:
        check_inputs(manifest, where=tmp_path)

    assert str(mesh) in str(moved.value)
    assert "sha256" in str(moved.value)


def test_ver35_an_absent_input_is_named_by_its_path_not_its_repr(tmp_path: Path) -> None:
    mesh = tmp_path / AWKWARD_NAME
    mesh.write_bytes(b"original\n")
    manifest = _manifest(mesh, sha256=file_hash(mesh))
    mesh.unlink()

    with pytest.raises(InputMovedError) as moved:
        check_inputs(manifest, where=tmp_path)

    assert str(mesh) in str(moved.value)
    assert "is gone" in str(moved.value)
