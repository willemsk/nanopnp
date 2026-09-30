"""``nanopnp stage <name> <case> --export PATH``: a stored artefact in its interchange format.

The §3.1 IF-02 export NOTE. The suffix of ``PATH`` chooses the format, and the
table below is the whole of what is written:

- ``structure``: ``.pdb``, the aligned ensemble's first frame, with a ``.dcd`` of
  every frame beside it (IF-04), both in ångströms by their formats;
- ``density``: ``.npz``, the stored map; or OpenDX and CCP4/MRC, in ångströms
  (IF-05, §8.2.2 B10);
- ``symmetry``: ``.npz``, the stored reduction;
- ``contour``: ``.yaml``, the stored ``nanopnp/profile/v1`` document;
- ``mesh``: ``.msh``, the stored MSH 4.1 file (IF-06).

**A native payload is copied byte for byte**, so that the file a user holds has the
hash the store records, and a profile exported here and supplied through
``inputs.profile`` is the document stage 4 wrote.

**The path is an output location and nothing else**, so the configuration NOTE of
§3.1 is not breached and no artefact key depends on it. A stage or a suffix this
does not write is refused before anything runs (:func:`refusal`), and a file is
written beside its destination and renamed into place, so a failure leaves none
(WP16 D7's rule, as ``nanopnp mesh`` applies it). A structure's PDB and DCD are
replaced as a pair: a failure leaves the files that were there before.

Nothing here imports a stage module at module scope: the table is read by
``--help`` and by the refusal, both of which must stay as cheap as ``--list``.
"""

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
}
"""The suffixes each stage exports to, in the order the refusal names them."""

_PAYLOAD: Mapping[str, str] = {
    "structure": "ensemble",
    "density": "density",
    "symmetry": "reduced",
    "contour": "profile",
    "mesh": "mesh",
}
"""Each exporting stage's payload key (the stages' ``PAYLOAD_NAME``), held as data here
so that the refusal and ``--help`` import no stage module."""


def refusal(stage: str, path: Path) -> str | None:
    """Return why ``--export path`` cannot be written for ``stage``, or ``None`` if it can.

    Checked before the walk: the message is a usage error, and the stage
    behind it may take a minute to run.
    """
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
    """Write ``artefact``'s payload to ``path`` in the format its suffix names.

    ``path`` has passed :func:`refusal`. Returns every file written: two for a
    structure, the PDB and then its DCD, and one otherwise.
    """
    source = Path(artefact.payload[_PAYLOAD[stage]])
    suffix = path.suffix.lower()
    if stage == "structure":
        return _export_structure(source, path)
    if stage == "density" and suffix != ".npz":
        from nanopnp.density.map import DensityMap

        density = DensityMap.read(source)
        return (_staged(path, density.export),)
    return (_staged(path, lambda partial: Path(shutil.copyfile(source, partial))),)


def _partial(path: Path) -> Path:
    """Return a staging name beside ``path``, keeping its suffix, which names the format.

    The process id keeps two exports aimed at one destination from sharing a
    staging file.
    """
    return path.with_name(f".{path.stem}.{os.getpid()}.partial{path.suffix}")


def _staged(path: Path, write: Callable[[Path], Path]) -> Path:
    """Write through ``write`` to a staging file beside ``path``, then rename it into place."""
    partial = _partial(path)
    try:
        write(partial)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def _export_structure(source: Path, path: Path) -> tuple[Path, Path]:
    """Write the ensemble as ``path`` (PDB, first frame) and its DCD, as one pair.

    Both are written into a staging directory beside ``path``. They are then
    renamed into place by :func:`_replace_pair`, which leaves either the new pair
    or whatever was there before, never a PDB beside another export's DCD.
    """
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
    """Rename each ``(new, destination)`` into place, all or none.

    Whatever sits at a destination is first moved into ``previous``, the last
    destination first, so the PDB leaves before its DCD and no stale PDB can end
    up beside a new DCD. A failure part-way removes the new files already placed
    and moves the previous ones back, the first destination first, so a PDB is
    only restored once its DCD is. The previous files are discarded with the
    staging directory on success.
    """
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
