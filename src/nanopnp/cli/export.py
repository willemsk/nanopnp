"""``nanopnp stage <name> <case> --export PATH``: a stored artefact in its interchange format."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.artefact import Artefact

__all__ = ["EXPORTS", "export_artefact", "refusal"]

EXPORTS: Mapping[str, tuple[str, ...]] = {
    "structure": (".pdb",),
    "density": (".npz", ".dx", ".ccp4", ".mrc", ".map"),
    "symmetry": (".npz",),
    "contour": (".yaml",),
    "mesh": (".msh",),
    "protonation": (".pqr",),
    "charge": (".yaml", ".dx", ".mrc", ".ccp4"),
}

# Held as data so that the refusal and --help import no stage module.
_PAYLOAD: Mapping[str, str] = {
    "structure": "ensemble",
    "density": "density",
    "symmetry": "reduced",
    "contour": "profile",
    "mesh": "mesh",
    "protonation": "protonation",
    "charge": "charge",
}


def refusal(stage: str, path: Path) -> str | None:
    accepted = EXPORTS.get(stage)
    if accepted is None:
        return (
            f"stage {stage!r} has no export; --export writes the artefact of {', '.join(EXPORTS)}"
        )
    if path.suffix.lower() not in accepted:
        return (
            f"--export {path}: stage {stage!r} writes {', '.join(accepted)}, and "
            f"{path.suffix or 'no suffix'} is not one of them"
        )
    if not path.name or path.is_dir():
        return f"--export {path} is a directory; name the file to write"
    if not path.parent.is_dir():
        return f"--export {path}: the directory {path.parent} does not exist"
    return None


def export_artefact(stage: str, artefact: Artefact, path: Path) -> tuple[Path, ...]:
    if stage == "charge":
        from nanopnp.charge.stage import export_charge

        return export_charge(artefact, path)
    source = Path(artefact.payload[_PAYLOAD[stage]])
    suffix = path.suffix.lower()
    if stage == "structure":
        return _export_structure(source, path)
    if stage == "protonation":
        from nanopnp.charge.protonation import export_pqr

        return (_staged(path, lambda partial: export_pqr(source, partial)),)
    if stage == "density" and suffix != ".npz":
        from nanopnp.density.map import DensityMap

        density = DensityMap.read(source)
        return (_staged(path, density.export),)
    return (_staged(path, lambda partial: Path(shutil.copyfile(source, partial))),)


def _partial(path: Path) -> Path:
    return path.with_name(f".{path.stem}.{os.getpid()}.partial{path.suffix}")


def _staged(path: Path, write: Callable[[Path], Path]) -> Path:
    partial = _partial(path)
    try:
        write(partial)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def _export_structure(source: Path, path: Path) -> tuple[Path, Path]:
    from nanopnp.structure.ensemble import AlignedEnsemble

    ensemble = AlignedEnsemble.read(source)
    trajectory = path.with_suffix(".dcd")
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}.", suffix=".partial", dir=path.parent))
    try:
        pdb, dcd = ensemble.export(staging, stem=path.stem)
        _replace_pair(((dcd, trajectory), (pdb, path)), staging / "previous")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return path, trajectory


def _replace_pair(moves: tuple[tuple[Path, Path], ...], previous: Path) -> None:
    # Old files move aside last-first and back first-first: no stale PDB beside a new DCD.
    previous.mkdir()
    set_aside: list[tuple[Path, Path]] = []
    placed: list[Path] = []
    try:
        for index, (_, destination) in reversed(list(enumerate(moves))):
            if destination.exists():
                kept = previous / f"{index}{destination.suffix}"
                destination.replace(kept)
                set_aside.append((kept, destination))
        for new, destination in moves:
            new.replace(destination)
            placed.append(destination)
    except BaseException:
        for destination in placed:
            destination.unlink(missing_ok=True)
        for kept, destination in reversed(set_aside):
            kept.replace(destination)
        raise
