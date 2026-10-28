"""Filesystem locations of packaged data and of the result store."""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_PACKAGED_DATA = _PACKAGE_ROOT / "data"
_REPO_DATA = _PACKAGE_ROOT.parents[1] / "data"
_REPO_TEST_STRUCTURES = _PACKAGE_ROOT.parents[1] / "tests" / "data" / "structures"

PACKAGE_ROOT: Path = _PACKAGE_ROOT

DATA_DIR: Path = _PACKAGED_DATA if _PACKAGED_DATA.is_dir() else _REPO_DATA

CORRECTIONS_DIR: Path = DATA_DIR / "corrections"


GEOMETRY_DIR: Path = DATA_DIR / "geometry"


RADII_DIR: Path = DATA_DIR / "radii"


STRUCTURES_DIR: Path = DATA_DIR / "structures"


def available_corrections() -> tuple[str, ...]:
    """Return the names of every installed correction parameter file, sorted."""
    if not CORRECTIONS_DIR.is_dir():
        return ()
    return tuple(sorted(path.stem for path in CORRECTIONS_DIR.glob("*.yaml")))


def correction_file(name: str) -> Path:
    """Return the path of an installed correction ``<name>.yaml``; FileNotFoundError if absent."""
    path = CORRECTIONS_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no correction file {name!r} in {CORRECTIONS_DIR}")
    return path


def profile_file(name: str) -> Path:
    """Return the path of a named pore-profile fixture; FileNotFoundError if not installed."""
    path = GEOMETRY_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no geometry profile {name!r} in {GEOMETRY_DIR}")
    return path


def radii_file(name: str) -> Path:
    """Return the path of a named radius set; FileNotFoundError if not installed."""
    path = RADII_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no radius set {name!r} in {RADII_DIR}")
    return path


def structure_file(name: str) -> Path:
    """Return the path of a named structure file; FileNotFoundError if none is installed.

    ``name`` is a file name, such as ``2wcd.pdb.gz``, or a bare stem read as ``<stem>.pdb``.
    In a development checkout, ``tests/data/structures/`` is searched after the packaged ones.
    """
    # The name as given first, so a stem with a dot in it is still read as a stem.
    file_names = (name, f"{name}.pdb")
    places = [STRUCTURES_DIR]
    if _REPO_DATA.is_dir() and _REPO_TEST_STRUCTURES.is_dir():
        places.append(_REPO_TEST_STRUCTURES)
    for place in places:
        for file_name in file_names:
            if (place / file_name).is_file():
                return place / file_name
    searched = ", ".join(str(place) for place in places)
    raise FileNotFoundError(f"no structure file {name!r} (or {file_names[1]!r}) in {searched}")


STORE_ROOT_VARIABLE = "NANOPNP_STORE"

DEFAULT_STORE_DIRNAME = "nanopnp-store"


def store_root() -> Path:
    """Return the artefact store root: ``$NANOPNP_STORE``, else ``./nanopnp-store``."""
    configured = os.environ.get(STORE_ROOT_VARIABLE)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / DEFAULT_STORE_DIRNAME).resolve()


REFERENCE_DATA_VARIABLE = "NANOPNP_REFERENCE_DATA"


def reference_data_root() -> Path | None:
    """Return the reference-data directory named by ``$NANOPNP_REFERENCE_DATA``, or None."""
    configured = os.environ.get(REFERENCE_DATA_VARIABLE)
    if not configured:
        return None
    root = Path(configured).expanduser().resolve()
    return root if root.is_dir() else None


def reference_file(name: str) -> Path | None:
    """Return an archived reference file by name, or None if the archive is absent."""
    root = reference_data_root()
    if root is None:
        return None
    path = root / name
    return path if path.is_file() else None
